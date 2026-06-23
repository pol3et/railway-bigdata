"""
Silver statistics merge — deterministic, with an LLM-assisted column crosswalk.

Pipeline (see SILVER_DESIGN.md for why it is split this way):
  1. readers melt each raw source into a long frame of
     (geo, year, value, unit, source_system, source_dataset, source_column).
     This is PURE pandas — no LLM ever touches the numbers.
  2. build_crosswalk() maps each distinct source_column -> a canonical English
     feature key (config.CANONICAL_FEATURES). Eurostat labels are already English
     so they map by rule; only HU (KSH) / DE (Statistik Austria) labels are sent
     to Ollama, and the result is CACHED to crosswalk_cache.json for review.
  3. apply_crosswalk() + concat() produce the single unified table with English
     feature labels. Unmapped columns are dropped (logged), not guessed.

The merge target is LONG format (one row per geo-year-feature); Gold pivots it
to a country-year feature matrix. Long-format merge avoids the wide-schema
alignment problem entirely.
"""
import json
import logging
import os
from typing import Optional

import pandas as pd

from ..config import CANONICAL_FEATURES, CROSSWALK_PATH
from ..ollama_client import generate_json
from ..schema import StatFact

logger = logging.getLogger("silver.stats.merge")

CANON_KEYS = list(CANONICAL_FEATURES.keys())
_WORLD_BANK_ISO3_TO_GEO = {
    "HUN": "HU",
    "AUT": "AT",
    "CZE": "CZ",
}


def _worldbank_geo(record: dict) -> str:
    iso3 = str(record.get("countryiso3code") or "").upper()
    if iso3 in _WORLD_BANK_ISO3_TO_GEO:
        return _WORLD_BANK_ISO3_TO_GEO[iso3]

    country = record.get("country")
    if isinstance(country, dict):
        iso2 = str(country.get("id") or "").upper()
        if iso2:
            return iso2

    return iso3[:2]


# --------------------------------------------------------------------------
# 1) deterministic readers: raw source frame -> long frame. (Stubs show the
#    contract; real bodies parse the Bronze bytes for each source.)
#    Each returns columns: geo, year, value, unit, source_dataset, source_column
# --------------------------------------------------------------------------
def read_eurostat_tsv(df: pd.DataFrame, dataset_id: str) -> pd.DataFrame:
    """Eurostat TSV is wide (years as columns, dims in the first column).
    Melt to long; Eurostat dimension labels are already English."""
    id_col = df.columns[0]
    year_cols = [c for c in df.columns if str(c).strip().isdigit()]
    long = df.melt(id_vars=[id_col], value_vars=year_cols,
                   var_name="year", value_name="value_raw")
    long["geo"] = long[id_col].astype(str).str.extract(r",([A-Z]{2})$")[0]
    long["year"] = pd.to_numeric(long["year"], errors="coerce").astype("Int64")
    # Eurostat values can carry flags ("1234 b"): keep numeric part only.
    long["value"] = pd.to_numeric(
        long["value_raw"].astype(str).str.extract(r"([-\d.]+)")[0], errors="coerce")
    long["unit"] = "eurostat_native"
    long["source_column"] = id_col            # the dimension string (English)
    long["source_dataset"] = dataset_id
    return long[["geo", "year", "value", "unit", "source_dataset", "source_column"]]


def read_worldbank_json(records: list, dataset_id: str) -> pd.DataFrame:
    rows = []
    for r in records or []:
        rows.append({"geo": _worldbank_geo(r),
                     "year": pd.to_numeric(r.get("date"), errors="coerce"),
                     "value": r.get("value"),
                     "unit": "worldbank_native",
                     "source_dataset": dataset_id,
                     "source_column": (r.get("indicator") or {}).get("value", dataset_id)})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["year"] = df["year"].astype("Int64")
    return df


def read_tabular_long(df: pd.DataFrame, dataset_id: str, *, geo: str,
                      label_col: str, year_col: str, value_col: str,
                      unit: str) -> pd.DataFrame:
    """Generic reader for KSH/Statistik Austria/UIC once their raw file is parsed
    into a tidy (label, year, value) frame. `label_col` holds the NATIVE-language
    feature label that the crosswalk will translate/normalize."""
    out = pd.DataFrame({
        "geo": geo,
        "year": pd.to_numeric(df[year_col], errors="coerce").astype("Int64"),
        "value": pd.to_numeric(df[value_col], errors="coerce"),
        "unit": unit,
        "source_dataset": dataset_id,
        "source_column": df[label_col].astype(str),
    })
    return out


# --------------------------------------------------------------------------
# 2) LLM-assisted, cached crosswalk: source_column -> canonical feature key
# --------------------------------------------------------------------------
def _load_cache() -> dict:
    if os.path.exists(CROSSWALK_PATH):
        try:
            return json.load(open(CROSSWALK_PATH, encoding="utf-8"))
        except Exception:
            logger.warning("crosswalk cache unreadable; starting fresh")
    return {}


def _save_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(CROSSWALK_PATH) or ".", exist_ok=True)
    json.dump(cache, open(CROSSWALK_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def _map_label_via_llm(label: str) -> Optional[str]:
    keys = "\n".join(f"- {k}: {v}" for k, v in CANONICAL_FEATURES.items())
    prompt = (
        "Map the railway statistics column label below to exactly ONE canonical "
        "feature key from the list, or \"unmapped\" if none fits. The label may be "
        "in Hungarian or German.\n\n"
        f"Label: {label!r}\n\nCanonical keys:\n{keys}\n\n"
        'Respond as JSON: {"key": "<one key or unmapped>", "confidence": 0..1}'
    )
    res = generate_json(prompt)
    if not isinstance(res, dict):
        return None
    key = res.get("key")
    return key if key in CANON_KEYS else ("unmapped" if key == "unmapped" else None)


# English-by-rule mapping for Eurostat dimension strings (no LLM needed).
# _EUROSTAT_RULES = [
#     ("freight", "rail_freight_tonnes"), ("goods", "rail_freight_tonnes"),
#     ("tonne-km", "rail_freight_tonne_km"), ("passenger-km", "rail_passenger_km"),
#     ("passenger", "rail_passengers"), ("network", "rail_network_length_km"),
#     ("electrified", "rail_electrified_km"), ("accident", "rail_accidents"),
#     ("victim", "rail_fatalities"), ("killed", "rail_fatalities"),
#     ("investment", "rail_investment"), ("rolling stock", "rail_rolling_stock"),
#     ("employ", "rail_employees"),
# ]


_ENGLISH_LABEL_RULES = [
    ("rail lines", "rail_network_length_km"),
    ("route-km", "rail_network_length_km"),
    ("network", "rail_network_length_km"),
    ("electrified", "rail_electrified_km"),

    ("tonne-km", "rail_freight_tonne_km"),
    ("ton-km", "rail_freight_tonne_km"),
    ("freight", "rail_freight_tonnes"),
    ("goods", "rail_freight_tonnes"),

    ("passenger-km", "rail_passenger_km"),
    ("passengers carried", "rail_passenger_km"),
    ("passenger", "rail_passengers"),

    ("accident", "rail_accidents"),
    ("victim", "rail_fatalities"),
    ("killed", "rail_fatalities"),
    ("investment", "rail_investment"),
    ("rolling stock", "rail_rolling_stock"),
    ("employ", "rail_employees"),
]

def _map_label_by_rule(label: str) -> Optional[str]:
    low = label.lower()
    for needle, key in _ENGLISH_LABEL_RULES:
        if needle in low:
            return key
    return None


def build_crosswalk(labels: list, *, sources: Optional[dict] = None,
                    use_llm: bool = True) -> dict:
    """labels: distinct source_column strings. sources: optional {label: system}
    so Eurostat/English labels skip the LLM. Returns {label: canonical_key|unmapped}
    and caches it for review."""
    cache = _load_cache()
    sources = sources or {}
    for label in labels:
        if label in cache:
            continue
        # rule-first (covers all English Eurostat labels for free)
        key = _map_label_by_rule(label)
        if key is None and use_llm and sources.get(label) in (None, "ksh", "statistik_austria", "uic"):
            key = _map_label_via_llm(label)
        cache[label] = key or "unmapped"
    _save_cache(cache)
    n_map = sum(1 for v in cache.values() if v != "unmapped")
    logger.info("crosswalk: %d/%d labels mapped (%d unmapped)",
                n_map, len(cache), len(cache) - n_map)
    return cache


# --------------------------------------------------------------------------
# 3) apply + concat -> one unified StatFact table
# --------------------------------------------------------------------------
def merge_sources(frames: list, crosswalk: dict) -> pd.DataFrame:
    """frames: list of long frames with (geo, year, value, unit, source_dataset,
    source_column) and a `source_system` column. Applies the crosswalk, drops
    unmapped, returns the unified StatFact dataframe."""
    if not frames:
        return pd.DataFrame(columns=[f.name for f in StatFact.__dataclass_fields__.values()])
    df = pd.concat(frames, ignore_index=True)
    df["feature"] = df["source_column"].map(lambda s: crosswalk.get(s, "unmapped"))
    before = len(df)
    df = df[df["feature"] != "unmapped"].copy()
    logger.info("merge: kept %d/%d rows after crosswalk", len(df), before)
    cols = ["geo", "year", "feature", "value", "unit", "source_system",
            "source_dataset", "source_column"]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df[cols].reset_index(drop=True)
