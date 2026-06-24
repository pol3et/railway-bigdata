"""
Load Bronze stats *bytes* into Silver long frames, then merge to StatFact.

This is the deterministic Bronze->Silver glue for the World Bank + Eurostat
slice (GAP-006). The numeric parsing is PURE pandas — an LLM never touches the
numbers (it is only ever used, elsewhere, for the cached HU/DE column
crosswalk). Each loader returns the long contract expected by
`stats.merge.merge_sources`, plus a `source_system` column:

    geo, year, value, unit, source_dataset, source_column, source_system

Bronze layout consumed (same as the RawLander wrote it):

    <root>/stats/worldbank/<indicator>/ingest_date=YYYY-MM-DD/<indicator>.json
    <root>/stats/eurostat/<dataset_id>/ingest_date=YYYY-MM-DD/<file>.tsv[.gz]
"""
import gzip
import io
import json
import logging
from pathlib import Path
import re
import zipfile


import pandas as pd

from . import merge as stats_merge
from .merge import read_eurostat_tsv, read_worldbank_json, read_tabular_long

logger = logging.getLogger("silver.stats.load")

_GZIP_MAGIC = b"\x1f\x8b"
_LONG_COLS = ["geo", "year", "value", "unit",
              "source_dataset", "source_column", "source_system"]
_KSH_TIDY_COLS = ["label", "year", "value", "unit"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=_LONG_COLS)


def _empty_ksh_tidy() -> pd.DataFrame:
    return pd.DataFrame(columns=_KSH_TIDY_COLS)


def load_worldbank_frame(raw: bytes, dataset_id: str) -> pd.DataFrame:
    """World Bank Bronze file is JSON ``[meta, records]``. Melt the records to a
    long frame tagged ``source_system='worldbank'``. An error envelope
    (``[{"message": ...}]``) or a no-data body (``[meta, null]``) yields an empty
    frame — never a fabricated row."""
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("worldbank %s: non-JSON payload; skipping", dataset_id)
        return _empty()
    records = payload[1] if isinstance(payload, list) and len(payload) > 1 else None
    if not isinstance(records, list) or not records:
        logger.warning("worldbank %s: no time-series records; skipping", dataset_id)
        return _empty()
    frame = read_worldbank_json(records, dataset_id)
    if frame.empty:
        return _empty()
    frame["source_system"] = "worldbank"
    return frame


def load_eurostat_frame(raw: bytes, dataset_id: str) -> pd.DataFrame:
    """Eurostat Bronze file is a TSV, optionally gzipped (the SDMX API serves
    ``.tsv.gz``). Decompress if needed, melt wide years to long, tag
    ``source_system='eurostat'``."""
    if raw[:2] == _GZIP_MAGIC:
        raw = gzip.decompress(raw)
    df = pd.read_csv(io.BytesIO(raw), sep="\t", dtype=str)
    if df.empty:
        return _empty()
    frame = read_eurostat_tsv(df, dataset_id)
    frame["source_system"] = "eurostat"
    return frame

def _coerce_ksh_year(value) -> int | None:
    """Return a 4-digit year from an XLSX header cell, or None."""
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if text.isdigit() and len(text) == 4:
        year = int(text)
        if 1900 <= year <= 2100:
            return year
    return None


def _clean_ksh_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _ksh_is_blank(value) -> bool:
    return _clean_ksh_text(value) == ""


def _ksh_title_unit(df: pd.DataFrame) -> str:
    for _, row in df.head(5).iterrows():
        text = " ".join(_clean_ksh_text(value) for value in row if not _ksh_is_blank(value))
        match = re.search(r"\[([^\]]+)\]", text)
        if match:
            return match.group(1).strip()
    return "ksh_native"


def _ksh_label_column(df: pd.DataFrame, header_row: int, year_cols: list[int]) -> int | None:
    """Pick the text column that names the indicator rows.

    KSH STADAT files may contain title rows/blank columns before the actual
    table. We therefore avoid hardcoding column 0 and choose the non-year column
    before the first year with the most text values below the header.
    """
    first_year_col = min(year_cols)
    candidates = [
        c for c in range(first_year_col)
        if c in df.columns and _clean_ksh_text(df.at[header_row, c]).lower() not in {"unit", "units"}
    ]
    if not candidates:
        return None

    best_col = None
    best_score = -1
    body = df.iloc[header_row + 1:]

    for col in candidates:
        values = body[col].dropna().astype(str).str.strip()
        score = values.ne("").sum()
        if score > best_score:
            best_col = col
            best_score = int(score)

    return best_col if best_score > 0 else None


def _ksh_unit_column(df: pd.DataFrame, header_row: int, label_col: int, year_cols: list[int]) -> int | None:
    first_year_col = min(year_cols)
    for col in range(first_year_col):
        if col == label_col or col not in df.columns:
            continue
        if _clean_ksh_text(df.at[header_row, col]).lower() in {"unit", "units"}:
            return col
    return None


def _ksh_year_header(df: pd.DataFrame) -> tuple[int, dict[int, int]] | None:
    for idx, row in df.head(40).iterrows():
        found = {}
        for col, cell in row.items():
            year = _coerce_ksh_year(cell)
            if year is not None:
                found[col] = year
        if found:
            return int(idx), found
    return None


def _ksh_period_year_header(df: pd.DataFrame) -> tuple[int, int] | None:
    for idx, row in df.head(40).iterrows():
        for col, cell in row.items():
            text = _clean_ksh_text(cell).lower()
            if ("period" in text and "year" in text) or text == "year":
                feature_cols = [
                    c for c in df.columns
                    if c != col and not _ksh_is_blank(row.get(c))
                ]
                if feature_cols:
                    return int(idx), int(col)
    return None


def _ksh_tidy_from_period_year_table(
    df: pd.DataFrame,
    header_row: int,
    year_col: int,
    default_unit: str,
) -> pd.DataFrame:
    header = df.iloc[header_row]
    feature_cols = {
        col: _clean_ksh_text(header.get(col))
        for col in df.columns
        if col != year_col and not _ksh_is_blank(header.get(col))
    }
    rows = []
    for _, row in df.iloc[header_row + 1:].iterrows():
        year = _coerce_ksh_year(row.get(year_col))
        if year is None:
            continue
        for col, label in feature_cols.items():
            value = row.get(col)
            if _ksh_is_blank(value):
                continue
            rows.append({"label": label, "year": year, "value": value, "unit": default_unit})
    return pd.DataFrame(rows, columns=_KSH_TIDY_COLS)


def _ksh_is_regional_year_table(df: pd.DataFrame, header_row: int) -> bool:
    values = {
        _clean_ksh_text(value).lower()
        for value in df.iloc[header_row].tolist()
        if not _ksh_is_blank(value)
    }
    return "territorial unit denomination" in values


def _ksh_tidy_from_regional_year_table(
    df: pd.DataFrame,
    header_row: int,
    year_map: dict[int, int],
    default_unit: str,
) -> pd.DataFrame:
    indicator = ""
    for _, row in df.iloc[header_row + 1:].iterrows():
        first_cell = _clean_ksh_text(row.get(0))
        if first_cell:
            indicator = first_cell
            break
    if not indicator:
        return _empty_ksh_tidy()

    rows = []
    for _, row in df.iloc[header_row + 1:].iterrows():
        if _clean_ksh_text(row.get(0)).lower() != "country, total":
            continue
        for col, year in year_map.items():
            value = row.get(col)
            if _ksh_is_blank(value):
                continue
            rows.append({"label": indicator, "year": year, "value": value, "unit": default_unit})
        break
    return pd.DataFrame(rows, columns=_KSH_TIDY_COLS)


def _ksh_tidy_from_year_header_table(
    df: pd.DataFrame,
    header_row: int,
    year_map: dict[int, int],
    default_unit: str,
) -> pd.DataFrame:
    label_col = _ksh_label_column(df, header_row, list(year_map))
    if label_col is None:
        return _empty_ksh_tidy()

    unit_col = _ksh_unit_column(df, header_row, label_col, list(year_map))
    rows = []
    current_section = ""
    for _, row in df.iloc[header_row + 1:].iterrows():
        label = _clean_ksh_text(row.get(label_col))
        if not label:
            continue

        values = [row.get(col) for col in year_map]
        if all(_ksh_is_blank(value) for value in values):
            current_section = label
            continue

        effective_label = f"{current_section} - {label}" if current_section else label
        unit = _clean_ksh_text(row.get(unit_col)) if unit_col is not None else ""
        unit = unit or default_unit
        for col, year in year_map.items():
            value = row.get(col)
            if _ksh_is_blank(value):
                continue
            rows.append({"label": effective_label, "year": year, "value": value, "unit": unit})

    return pd.DataFrame(rows, columns=_KSH_TIDY_COLS)


def _ksh_tidy_from_excel(raw: bytes) -> pd.DataFrame:
    """Extract a tidy label/year/value frame from KSH XLSX bytes.

    The reader searches for a header row containing 4-digit years, then melts
    the year columns into long rows. Unexpected layouts return an empty frame
    instead of fabricating data.
    """
    df = pd.read_excel(io.BytesIO(raw), sheet_name=0, header=None,
                       dtype=object, engine="openpyxl")
    if df.empty:
        return _empty_ksh_tidy()

    default_unit = _ksh_title_unit(df)
    period_header = _ksh_period_year_header(df)
    if period_header is not None:
        return _ksh_tidy_from_period_year_table(df, *period_header, default_unit)

    year_header = _ksh_year_header(df)
    if year_header is None:
        return _empty_ksh_tidy()

    header_row, year_map = year_header
    if _ksh_is_regional_year_table(df, header_row):
        return _ksh_tidy_from_regional_year_table(df, header_row, year_map, default_unit)
    return _ksh_tidy_from_year_header_table(df, header_row, year_map, default_unit)


def load_ksh_frame(raw: bytes, dataset_id: str) -> pd.DataFrame:
    """Read KSH STADAT XLSX bytes into the Silver long stats contract.

    KSH contributes Hungary-only national statistics, so geo is fixed to HU.
    The numeric cells are parsed deterministically through read_tabular_long;
    no LLM is used for numbers.
    """
    try:
        if not raw or not zipfile.is_zipfile(io.BytesIO(raw)):
            logger.warning("ksh %s: non-XLSX payload; skipping", dataset_id)
            return _empty()

        tidy = _ksh_tidy_from_excel(raw)
        if tidy.empty:
            logger.warning("ksh %s: no tidy year/value rows; skipping", dataset_id)
            return _empty()

        frame = read_tabular_long(
            tidy,
            dataset_id,
            geo="HU",
            label_col="label",
            year_col="year",
            value_col="value",
            unit="ksh_native",
        )
        frame["unit"] = tidy["unit"].astype(str).to_numpy()
        frame = frame.dropna(subset=["year", "value"])
        if frame.empty:
            return _empty()
        frame["source_system"] = "ksh"
        return frame[_LONG_COLS]
    except Exception as exc:
        logger.warning("ksh %s: XLSX parse failed: %s", dataset_id, exc)
        return _empty()


# source -> (loader, accepted data-file suffixes); "_"-prefixed datasets
# (e.g. _catalogue_*) are skipped.
_SOURCES = {
    "worldbank": (load_worldbank_frame, (".json",)),
    "eurostat": (load_eurostat_frame, (".tsv", ".tsv.gz", ".gz")),
    "ksh": (load_ksh_frame, (".xlsx",)),
}

def _latest_partition(dataset_dir: Path):
    parts = sorted(p for p in dataset_dir.glob("ingest_date=*") if p.is_dir())
    return parts[-1] if parts else None


def frames_from_bronze(root) -> list:
    """Walk a Bronze tree and return one long frame per (source, dataset),
    reading only the latest ``ingest_date=`` partition of each dataset."""
    root = Path(root)
    frames = []
    for source, (loader, suffixes) in _SOURCES.items():
        base = root / "stats" / source
        if not base.is_dir():
            continue
        for ds_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            if ds_dir.name.startswith("_"):       # skip _catalogue_* etc.
                continue
            latest = _latest_partition(ds_dir)
            if latest is None:
                continue
            for f in sorted(latest.iterdir()):
                if f.name.endswith(".meta.json"):
                    continue
                if not any(f.name.endswith(s) for s in suffixes):
                    continue
                frame = loader(f.read_bytes(), ds_dir.name)
                if not frame.empty:
                    frames.append(frame)
    logger.info("loaded %d non-empty stats frames from %s", len(frames), root)
    return frames


def build_silver_stats(root, *, use_llm: bool = False, out=None) -> pd.DataFrame:
    """End-to-end WB+Eurostat Bronze -> unified StatFact long table.

    Deterministic by default (``use_llm=False``): English Eurostat/WB labels map
    by rule, unmapped labels are recorded in the crosswalk cache and dropped
    (never guessed). If ``out`` is given, the table is persisted to Parquet."""
    frames = frames_from_bronze(root)
    labels, sources = [], {}
    for fr in frames:
        for lbl in fr["source_column"].astype(str).unique():
            labels.append(lbl)
            sources[lbl] = fr["source_system"].iloc[0] if "source_system" in fr else None
    crosswalk = stats_merge.build_crosswalk(sorted(set(labels)), sources=sources,
                                            use_llm=use_llm)
    unified = stats_merge.merge_sources(frames, crosswalk)
    if out is not None:
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        unified.to_parquet(out, index=False)
        logger.info("silver stats persisted: %s (%d rows)", out, len(unified))
    return unified
