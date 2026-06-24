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
# Eurostat encodes the measured quantity in the `unit` dimension CODE, not in an
# English label (the live API returns coded headers like `freq,unit,geo`). Map the
# unit code to an English phrase the crosswalk rules already understand.
# Generic unit -> English label, used ONLY for simple national datasets that
# have no breakdown dimensions (just freq, unit, geo). Ambiguous count units
# like NR are intentionally absent here; those are handled per-dataset below.
_EUROSTAT_UNIT_LABEL = {
    "MIO_TKM": "freight tonne-km", "THS_TKM": "freight tonne-km", "TKM": "freight tonne-km",
    "MIO_PKM": "passenger-km", "THS_PKM": "passenger-km", "PKM": "passenger-km",
    "PAS": "passengers", "THS_PAS": "passengers", "MIO_PAS": "passengers", "THS": "passengers",
    "KM": "rail network km",
    "T": "freight tonnes", "THS_T": "freight tonnes", "MIO_T": "freight tonnes",
}

# Dataset-aware rules for the rich Eurostat datasets that DO carry breakdown
# dimensions. `filters` keeps only the relevant rows (mostly the "TOTAL" code,
# or specific codes such as victim=KIL for fatalities), avoiding the double
# counting that naive summing of detail+total rows would cause. `unit_feature`
# maps the remaining unit code straight to a canonical feature key. Any leftover
# rows for the same (geo, year, feature) are summed (e.g. expend INF_INV +
# RSTK_INV -> total investment).
_EUROSTAT_DATASET_RULES = {
    # passengers / freight (national totals, no breakdown)
    "rail_pa_total": {"unit_feature": {"MIO_PKM": "rail_passenger_km", "THS_PAS": "rail_passengers"}},
    "rail_go_total": {"unit_feature": {"MIO_TKM": "rail_freight_tonne_km", "THS_T": "rail_freight_tonnes"}},
    "rail_pa_typepas": {"filters": {"tra_cov": {"TOTAL"}},
                        "unit_feature": {"MIO_PKM": "rail_passenger_km", "THS_PAS": "rail_passengers"}},
    "rail_pa_nbpass": {"filters": {"tra_cov": {"TOTAL"}}, "unit_feature": {"PAS": "rail_passengers"}},
    # infrastructure
    "rail_if_line_tr": {"filters": {"tra_infr": {"TOTAL"}, "n_tracks": {"TOTAL"}},
                        "unit_feature": {"KM": "rail_network_length_km"}},
    "rail_if_tracks": {"filters": {"tra_infr": {"TOTAL"}}, "unit_feature": {"KM": "rail_track_length_km"}},
    "rail_if_electri": {"filters": {"power": {"TOTAL"}}, "unit_feature": {"KM": "rail_electrified_km"}},
    # economics
    "rail_ec_emplo_a": {"filters": {"rail_act": {"TOTAL"}}, "unit_feature": {"NR": "rail_employees"}},
    "rail_ec_expend": {"filters": {"expend": {"INF_INV", "RSTK_INV"}},
                       "unit_feature": {"MIO_EUR": "rail_investment"}},
    # rolling stock
    "rail_eq_locon": {"filters": {"vehicle": {"LOC"}, "mot_nrg": {"TOTAL"}},
                      "unit_feature": {"NR": "rail_locomotives"}},
    "rail_eq_wagon": {"filters": {"vehicle": {"WAG"}}, "unit_feature": {"NR": "rail_wagons"}},
    # safety
    "rail_ac_catnmbr": {"filters": {"accident": {"TOTAL"}}, "unit_feature": {"NR": "rail_accidents"}},
    "rail_ac_catvict": {"filters": {"accident": {"TOTAL"}, "victim": {"KIL"}, "pers_cat": {"TOTAL"}},
                        "unit_feature": {"NR": "rail_fatalities"}},
    "tran_sf_railac": {"filters": {"accident": {"TOTAL"}}, "unit_feature": {"NR": "rail_accidents"}},
    "tran_sf_railvi": {"filters": {"accident": {"TOTAL"}, "victim": {"KIL"}, "pers_cat": {"TOTAL"}},
                       "unit_feature": {"NR": "rail_fatalities"}},
}


def _parse_eurostat_value(series: pd.Series) -> pd.Series:
    # values may carry flags ("1234 b", "726 e") or be ":"/"@C" (missing) -> NaN.
    # Capture the numeric token including any thousands separators, then strip the
    # commas so a grouped value like "1,234" parses to 1234 rather than 1.
    nums = (series.astype(str).str.extract(r"([-\d.,]+)")[0]
            .str.replace(",", "", regex=False))
    return pd.to_numeric(nums, errors="coerce")


def read_eurostat_tsv(df: pd.DataFrame, dataset_id: str) -> pd.DataFrame:
    """Eurostat TSV is wide (years as columns, dims packed in the first column).

    Feature extraction is dataset-aware:
      * datasets in ``_EUROSTAT_DATASET_RULES`` get precise per-dimension filters
        (e.g. keep only TOTAL rows) so breakdown detail is not double counted;
      * other CODED datasets with NO breakdown dims (just freq, unit, geo) use the
        generic unit->label map;
      * CODED datasets with unmapped breakdown dims are skipped (noise / risk of
        double counting);
      * a legacy English-label header is still supported for older fixtures.
    """
    cols = ["geo", "year", "value", "unit", "source_dataset", "source_column"]
    id_col = df.columns[0]
    year_cols = [c for c in df.columns if str(c).strip().isdigit()]
    if not year_cols:
        return pd.DataFrame(columns=cols)
    dim_names = [d.strip().lower() for d in str(id_col).split("\\")[0].split(",")]
    coded = "geo" in dim_names

    long = df.melt(id_vars=[id_col], value_vars=year_cols,
                   var_name="year", value_name="value_raw")
    if long.empty:
        return pd.DataFrame(columns=cols)
    long["year"] = pd.to_numeric(long["year"], errors="coerce").astype("Int64")
    long["value"] = _parse_eurostat_value(long["value_raw"])
    long["source_dataset"] = dataset_id

    if coded:
        dims = long[id_col].astype(str).str.split(",", expand=True)
        if dims.shape[1] == 0:
            return pd.DataFrame(columns=cols)
        ncols = min(dims.shape[1], len(dim_names))
        dims = dims.iloc[:, :ncols]
        dims.columns = dim_names[:ncols]
        for c in dims.columns:
            dims[c] = dims[c].astype(str).str.strip()
        long["geo"] = (dims["geo"] if "geo" in dims.columns
                       else dims.iloc[:, -1])
        long["unit"] = (dims["unit"] if "unit" in dims.columns
                        else pd.Series("", index=long.index))
        extra = [d for d in dims.columns if d not in ("freq", "unit", "geo")]

        rule = _EUROSTAT_DATASET_RULES.get(dataset_id)
        if rule is not None:
            mask = pd.Series(True, index=long.index)
            for dim, allowed in rule.get("filters", {}).items():
                if dim in dims.columns:
                    mask &= dims[dim].isin(allowed)
            long = long[mask]
            uf = rule["unit_feature"]
            long = long.assign(source_column=long["unit"].map(uf))
            long = long[long["source_column"].notna()]
        elif not extra:
            long = long.assign(
                source_column=long["unit"].map(
                    lambda u: _EUROSTAT_UNIT_LABEL.get(u)))
            long = long[long["source_column"].notna()]
        else:
            # breakdown dataset with no rule -> skip rather than risk bad totals
            return pd.DataFrame(columns=cols)

        if long.empty:
            return pd.DataFrame(columns=cols)
        out = (long.groupby(["geo", "year", "unit", "source_dataset",
                             "source_column"], dropna=False, as_index=False)
                   ["value"].sum(min_count=1))
        return out[cols]

    # legacy English-label header: the column header itself is the label
    long["geo"] = long[id_col].astype(str).str.extract(r",([A-Z]{2})$")[0]
    long["unit"] = "eurostat_native"
    long["source_column"] = id_col
    return long[cols]


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
    ("electrified railway", "rail_electrified_km"),
    ("electrified rail", "rail_electrified_km"),
    ("rail lines", "rail_network_length_km"),
    ("railway lines", "rail_network_length_km"),
    ("railway operated", "rail_network_length_km"),
    ("standard gauge railways", "rail_network_length_km"),
    ("route-km", "rail_network_length_km"),
    ("network", "rail_network_length_km"),

    ("passenger carriages", "rail_rolling_stock"),
    ("freight wagons", "rail_rolling_stock"),
    ("locomotive", "rail_rolling_stock"),
    ("wagon", "rail_rolling_stock"),

    ("tonne-kilometres", "rail_freight_tonne_km"),
    ("ton-kilometres", "rail_freight_tonne_km"),
    ("tonne-km", "rail_freight_tonne_km"),
    ("ton-km", "rail_freight_tonne_km"),
    ("freight", "rail_freight_tonnes"),
    ("goods", "rail_freight_tonnes"),

    ("passenger kilometres", "rail_passenger_km"),
    ("passenger-km", "rail_passenger_km"),
    ("passengers carried", "rail_passengers"),
    ("number of passengers", "rail_passengers"),
    ("passenger", "rail_passengers"),

    ("accident", "rail_accidents"),
    ("victim", "rail_fatalities"),
    ("killed", "rail_fatalities"),
    ("investment", "rail_investment"),
    ("rolling stock", "rail_rolling_stock"),
    ("employ", "rail_employees"),
]

def _map_label_by_rule(label: str) -> Optional[str]:
    if label in CANON_KEYS:          # reader may emit a canonical key directly
        return label
    low = label.lower()
    candidates = [low.rsplit(" - ", 1)[-1], low] if " - " in low else [low]
    for candidate in candidates:
        if "road network" in candidate and "rail" not in candidate:
            return None
        for needle, key in _ENGLISH_LABEL_RULES:
            if needle in candidate:
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
