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
    <root>/stats/ksh/<table>/ingest_date=YYYY-MM-DD/<file>.xlsx
    <root>/stats/uic/<publication>/ingest_date=YYYY-MM-DD/<file>.pdf
    <root>/stats/statistik_austria/<dataset_id>/ingest_date=YYYY-MM-DD/<file>.ods
"""
import gzip
import io
import json
import logging
from datetime import datetime, timezone
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
_UIC_STAGING_COLS = [
    "table_name",
    "dataset_id",
    "table_id",
    "table_idx",
    "row_type",
    "row_idx",
    "parse_status",
    "geo",
    "year",
    "source_dataset",
    "source_system",
    "raw_geo_cell",
    "raw_year_cell",
    "raw_value_cells",
    "text_chunk",
    "created_at",
]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=_LONG_COLS)


def _empty_ksh_tidy() -> pd.DataFrame:
    return pd.DataFrame(columns=_KSH_TIDY_COLS)


def _empty_uic_staging() -> pd.DataFrame:
    return pd.DataFrame(columns=_UIC_STAGING_COLS)


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


_UIC_COUNTRY_CODE_ROWS = [
    ("AE", "ARE", ("united arab emirates",)),
    ("AL", "ALB", ("albania",)),
    ("AM", "ARM", ("armenia",)),
    ("AR", "ARG", ("argentina",)),
    ("AT", "AUT", ("austria",)),
    ("AU", "AUS", ("australia",)),
    ("AZ", "AZE", ("azerbaijan",)),
    ("BA", "BIH", ("bosnia and herzegovina", "bosnia-herzegovina")),
    ("BD", "BGD", ("bangladesh",)),
    ("BE", "BEL", ("belgium",)),
    ("BF", "BFA", ("burkina faso",)),
    ("BG", "BGR", ("bulgaria",)),
    ("BR", "BRA", ("brazil",)),
    ("BW", "BWA", ("botswana",)),
    ("BY", "BLR", ("belarus",)),
    ("CA", "CAN", ("canada",)),
    ("CD", "COD", ("congo, democratic republic of the", "democratic republic of the congo")),
    ("CH", "CHE", ("switzerland",)),
    ("CI", "CIV", ("cote d'ivoire", "côte d'ivoire", "ivory coast")),
    ("CL", "CHL", ("chile",)),
    ("CM", "CMR", ("cameroon",)),
    ("CN", "CHN", ("china",)),
    ("CY", "CYP", ("cyprus",)),
    ("CZ", "CZE", ("czechia", "czech republic")),
    ("DE", "DEU", ("germany",)),
    ("DK", "DNK", ("denmark",)),
    ("DZ", "DZA", ("algeria",)),
    ("EE", "EST", ("estonia",)),
    ("EG", "EGY", ("egypt",)),
    ("ES", "ESP", ("spain",)),
    ("ET", "ETH", ("ethiopia",)),
    ("FI", "FIN", ("finland",)),
    ("FR", "FRA", ("france",)),
    ("GA", "GAB", ("gabon",)),
    ("GB", "GBR", ("united kingdom", "great britain", "uk")),
    ("GE", "GEO", ("georgia",)),
    ("GR", "GRC", ("greece",)),
    ("HR", "HRV", ("croatia",)),
    ("HU", "HUN", ("hungary",)),
    ("ID", "IDN", ("indonesia",)),
    ("IE", "IRL", ("ireland",)),
    ("IL", "ISR", ("israel",)),
    ("IN", "IND", ("india",)),
    ("IR", "IRN", ("iran", "iran, islamic republic of")),
    ("IT", "ITA", ("italy",)),
    ("JO", "JOR", ("jordan",)),
    ("JP", "JPN", ("japan",)),
    ("KE", "KEN", ("kenya",)),
    ("KG", "KGZ", ("kyrgyzstan",)),
    ("KZ", "KAZ", ("kazakhstan",)),
    ("KR", "KOR", ("korea, republic of", "south korea", "korea")),
    ("LT", "LTU", ("lithuania",)),
    ("LU", "LUX", ("luxembourg",)),
    ("LV", "LVA", ("latvia",)),
    ("MA", "MAR", ("morocco",)),
    ("MD", "MDA", ("moldova", "republic of moldova")),
    ("ME", "MNE", ("montenegro",)),
    ("MG", "MDG", ("madagascar",)),
    ("MK", "MKD", ("north macedonia", "macedonia")),
    ("MN", "MNG", ("mongolia",)),
    ("MR", "MRT", ("mauritania",)),
    ("MT", "MLT", ("malta",)),
    ("MX", "MEX", ("mexico",)),
    ("MY", "MYS", ("malaysia",)),
    ("NL", "NLD", ("netherlands",)),
    ("NO", "NOR", ("norway",)),
    ("PL", "POL", ("poland",)),
    ("PH", "PHL", ("philippines",)),
    ("PK", "PAK", ("pakistan",)),
    ("PT", "PRT", ("portugal",)),
    ("RO", "ROU", ("romania",)),
    ("RS", "SRB", ("serbia",)),
    ("RU", "RUS", ("russian federation", "russia")),
    ("SA", "SAU", ("saudi arabia",)),
    ("SD", "SDN", ("sudan",)),
    ("SE", "SWE", ("sweden",)),
    ("SI", "SVN", ("slovenia",)),
    ("SK", "SVK", ("slovakia", "slovak republic")),
    ("TJ", "TJK", ("tajikistan",)),
    ("TM", "TKM", ("turkmenistan",)),
    ("TN", "TUN", ("tunisia",)),
    ("TR", "TUR", ("turkiye", "turkey")),
    ("TW", "TWN", ("taiwan", "taiwan, province of china")),
    ("TZ", "TZA", ("tanzania", "tanzania, united republic of")),
    ("UA", "UKR", ("ukraine",)),
    ("UY", "URY", ("uruguay",)),
    ("US", "USA", ("united states", "united states of america")),
    ("UZ", "UZB", ("uzbekistan",)),
    ("VN", "VNM", ("viet nam", "vietnam")),
    ("ZM", "ZMB", ("zambia",)),
    ("ZW", "ZWE", ("zimbabwe",)),
    ("ZA", "ZAF", ("south africa",)),
]
_UIC_GEO_CODES = {iso2: iso2 for iso2, _, _ in _UIC_COUNTRY_CODE_ROWS}
_UIC_GEO_CODES.update({iso3: iso2 for iso2, iso3, _ in _UIC_COUNTRY_CODE_ROWS})
_UIC_GEO_CODES["UK"] = "GB"
_UIC_GEO_CODES["CN-TW"] = "TW"


def _stataustria_title(df: pd.DataFrame) -> str:
    for _, row in df.head(5).iterrows():
        text = _clean_ksh_text(row.get(0))
        if text and not text.lower().startswith(("einheit", "q:")):
            return text
    return "Statistik Austria rail statistics"


def _stataustria_single_cell_text(row: pd.Series) -> str:
    values = [
        _clean_ksh_text(value)
        for value in row.tolist()
        if not _ksh_is_blank(value)
    ]
    return values[0] if len(values) == 1 else ""


def _stataustria_immediate_section(df: pd.DataFrame, header_row: int) -> str:
    if header_row <= 0:
        return ""
    text = _stataustria_single_cell_text(df.iloc[header_row - 1])
    if not text or text.lower().startswith("q:"):
        return ""
    return text


def _stataustria_year_header_rows(df: pd.DataFrame) -> list[tuple[int, dict[int, int]]]:
    headers = []
    for idx, row in df.head(40).iterrows():
        found = {}
        for col, cell in row.items():
            year = _coerce_ksh_year(cell)
            if year is not None:
                found[col] = year
        if len(found) >= 2:
            headers.append((int(idx), found))
    return headers


def _stataustria_year_from_text(value) -> int | None:
    text = _clean_ksh_text(value)
    match = re.search(r"(19\d{2}|20\d{2})", text)
    return int(match.group(1)) if match else None


def _stataustria_total_column(df: pd.DataFrame) -> int | None:
    for _, row in df.head(10).iterrows():
        for col, cell in row.items():
            if _clean_ksh_text(cell).lower() == "insgesamt":
                return int(col)
    return None


def _stataustria_normalize_number(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value

    text = _clean_ksh_text(value)
    text = text.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    if text in {"", "-", ".", ".."}:
        return None
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"[-+]?\d{1,3}(?:\.\d{3})+", text):
        text = text.replace(".", "")
    return text


def _stataustria_metric_context(metric: str) -> str:
    low = metric.lower()
    if "tkm" in low or "tonnenkilometer" in low:
        return "Transportleistung"
    if "tonnen" in low:
        return "Transportaufkommen"
    return metric


def _stataustria_unit_for_label(label: str) -> str:
    low = label.lower()
    if "tkm" in low or "tonnenkilometer" in low:
        return "1 000 tkm Inland" if "1 000" in low else "tonne-km"
    if "tonnen" in low or "nutzlast" in low:
        return "Tonnen"
    return "count"


def _stataustria_tidy_from_report_year_rows(df: pd.DataFrame, title: str) -> pd.DataFrame:
    total_col = _stataustria_total_column(df)
    if total_col is None:
        return _empty_ksh_tidy()

    rows = []
    current_year = None
    for _, row in df.iterrows():
        first_cell = _clean_ksh_text(row.get(0))
        year = _stataustria_year_from_text(first_cell)
        if first_cell.lower().startswith("berichtsjahr") and year is not None:
            current_year = year
            continue
        if current_year is None or not first_cell or first_cell.lower().startswith("q:"):
            continue

        value = _stataustria_normalize_number(row.get(total_col))
        if value is None:
            continue
        metric_context = _stataustria_metric_context(first_cell)
        label = f"{title} - {metric_context} - {first_cell} - Insgesamt"
        rows.append({
            "label": label,
            "year": current_year,
            "value": value,
            "unit": first_cell,
        })

    return pd.DataFrame(rows, columns=_KSH_TIDY_COLS)


def _stataustria_join_label(parts: list[str]) -> str:
    clean_parts = []
    for part in parts:
        text = _clean_ksh_text(part).strip(" -")
        if text and (not clean_parts or clean_parts[-1] != text):
            clean_parts.append(text)
    return " - ".join(clean_parts)


def _stataustria_tidy_from_year_header_tables(df: pd.DataFrame, title: str) -> pd.DataFrame:
    headers = _stataustria_year_header_rows(df)
    if not headers:
        return _empty_ksh_tidy()

    rows = []
    for idx, (header_row, year_map) in enumerate(headers):
        label_col = _ksh_label_column(df, header_row, list(year_map))
        if label_col is None:
            continue
        header_label = _clean_ksh_text(df.at[header_row, label_col])
        section = _stataustria_immediate_section(df, header_row)
        end_row = headers[idx + 1][0] if idx + 1 < len(headers) else len(df)

        current_section = ""
        for _, row in df.iloc[header_row + 1:end_row].iterrows():
            raw_label = _clean_ksh_text(row.get(label_col))
            if not raw_label:
                continue
            if raw_label.lower().startswith("q:"):
                break

            values = [row.get(col) for col in year_map]
            if all(_ksh_is_blank(value) for value in values):
                current_section = raw_label
                continue
            if all(_stataustria_normalize_number(value) is None for value in values):
                continue

            label = _stataustria_join_label([
                title,
                section,
                current_section,
                header_label,
                raw_label,
            ])
            unit = _stataustria_unit_for_label(label)
            for col, year in year_map.items():
                value = _stataustria_normalize_number(row.get(col))
                if value is None:
                    continue
                rows.append({
                    "label": label,
                    "year": year,
                    "value": value,
                    "unit": unit,
                })

    return pd.DataFrame(rows, columns=_KSH_TIDY_COLS)


def _stataustria_tidy_from_ods(raw: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(raw), sheet_name=0, header=None,
                       dtype=object, engine="odf")
    if df.empty:
        return _empty_ksh_tidy()

    title = _stataustria_title(df)
    frames = [
        _stataustria_tidy_from_report_year_rows(df, title),
        _stataustria_tidy_from_year_header_tables(df, title),
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return _empty_ksh_tidy()
    return pd.concat(frames, ignore_index=True)


def load_stataustria_frame(raw: bytes, dataset_id: str) -> pd.DataFrame:
    """Read Statistik Austria rail ODS bytes into the Silver long stats contract.

    Statistik Austria rail ODS files are Austria-only, so geo is fixed to AT.
    Numeric cells are parsed deterministically through pandas/read_tabular_long;
    no LLM is used for values.
    """
    try:
        if not raw or not zipfile.is_zipfile(io.BytesIO(raw)):
            logger.warning("stataustria %s: non-ODS payload; skipping", dataset_id)
            return _empty()

        tidy = _stataustria_tidy_from_ods(raw)
        if tidy.empty:
            logger.warning("stataustria %s: no tidy year/value rows; skipping", dataset_id)
            return _empty()

        frame = read_tabular_long(
            tidy,
            dataset_id,
            geo="AT",
            label_col="label",
            year_col="year",
            value_col="value",
            unit="stataustria_native",
        )
        frame["unit"] = tidy["unit"].astype(str).to_numpy()
        frame = frame.dropna(subset=["year", "value"])
        if frame.empty:
            return _empty()
        frame["source_system"] = "statistik_austria"
        return frame[_LONG_COLS]
    except Exception as exc:
        logger.warning("stataustria %s: ODS parse failed: %s", dataset_id, exc)
        return _empty()

_UIC_COUNTRIES = {
    name: iso2
    for iso2, _, names in _UIC_COUNTRY_CODE_ROWS
    for name in names
}
_UIC_SYNOPSIS_FIXED_COLUMNS = {
    2: ("Average staff strength", "thousands"),
    4: ("Length of lines worked at end of year - Total", "kilometres"),
    6: ("Length of lines worked at end of year - electrified lines", "kilometres"),
    7: ("Locomotives including Light Rail Motor-tractors", "count"),
    10: ("Railway's wagons", "count"),
    13: ("Passengers carried", "millions"),
    15: ("Passenger.kilometres", "millions"),
    17: ("Tonnes carried", "millions"),
    19: ("Tonne.kilometres", "millions"),
}


def _looks_like_pdf(raw: bytes) -> bool:
    return bool(raw and raw[:5] == b"%PDF-")


def _clean_uic_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).replace("\u202f", " ").replace("\xa0", " ").split())


def _normalize_uic_text(value) -> str:
    return _clean_uic_text(value).lower()


def _parse_uic_number(text: str) -> float | None:
    cleaned = _clean_uic_text(text)
    if not cleaned or cleaned.lower() in {"na", "n/a", "-", "none"}:
        return None
    match = re.search(r"[-+]?\d[\d\s.,]*", cleaned)
    if not match:
        return None
    token = match.group(0).replace(" ", "")
    if "," in token:
        token = token.replace(".", "").replace(",", ".")
    try:
        return float(token)
    except ValueError:
        return None


def _uic_geo_from_cells(code_cell, country_cell=None) -> str | None:
    raw_code = _clean_uic_text(code_cell)
    if raw_code and raw_code == raw_code.upper():
        code = raw_code.upper()
        if code in _UIC_GEO_CODES:
            return _UIC_GEO_CODES[code]

    country = _normalize_uic_text(country_cell)
    return _UIC_COUNTRIES.get(country)


def _uic_year_from_company(value) -> int | None:
    text = _clean_uic_text(value)
    match = re.search(r"\((19\d{2}|20\d{2})\)", text) or re.search(r"\b(19\d{2}|20\d{2})\b", text)
    return int(match.group(1)) if match else None


def _uic_compact_column_specs(header: list) -> dict[int, tuple[str, str]]:
    specs = {}
    for idx, cell in enumerate(header):
        text = _normalize_uic_text(cell)
        if not text:
            continue
        if "length of lines worked" in text and "total" in text:
            specs[idx] = ("Length of lines worked at end of year - Total", "kilometres")
        elif "electrified" in text and "line" in text:
            specs[idx] = ("Length of lines worked at end of year - electrified lines", "kilometres")
        elif "passenger.kilometres" in text or "passenger kilometres" in text:
            specs[idx] = ("Passenger.kilometres", "millions")
        elif "tonne.kilometres" in text or "tonne kilometres" in text:
            specs[idx] = ("Tonne.kilometres", "millions")
        elif "passengers carried" in text:
            specs[idx] = ("Passengers carried", "millions")
        elif "tonnes carried" in text:
            specs[idx] = ("Tonnes carried", "millions")
        elif "average staff" in text:
            specs[idx] = ("Average staff strength", "thousands")
    return specs


def _uic_first_data_row(table: list[list]) -> int:
    for idx, row in enumerate(table):
        if not row:
            continue
        code_cell = row[0] if len(row) > 0 else None
        country_cell = row[21] if len(row) > 21 else None
        if _uic_geo_from_cells(code_cell, country_cell):
            return idx
    return 0


def _uic_table_specs(table: list[list]) -> tuple[dict[int, tuple[str, str]], int] | None:
    header_text = " ".join(_normalize_uic_text(cell) for row in table[:14] for cell in row)
    widest_row = max((len(row) for row in table), default=0)
    if widest_row >= 20 and "country code" in header_text and "railway company" in header_text:
        if "revenue rail traffic" in header_text:
            return dict(_UIC_SYNOPSIS_FIXED_COLUMNS), _uic_first_data_row(table)

    for idx, row in enumerate(table[:10]):
        row_text = " ".join(_normalize_uic_text(cell) for cell in row)
        if "country code" not in row_text or "railway company" not in row_text:
            continue
        specs = _uic_compact_column_specs(row)
        if specs:
            return specs, idx + 1
    return None


def _extract_uic_pdf_text_and_tables(raw: bytes) -> tuple[str, list[list[list]]]:
    import pdfplumber

    text_chunks = []
    tables = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            text_chunks.append(page.extract_text() or "")
            tables.extend(page.extract_tables() or [])
    return "\n".join(text_chunks), tables


def _uic_now(created_at: str | None = None) -> str:
    return created_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _uic_raw_cell(value) -> str:
    return _clean_uic_text(value)


def _uic_raw_value_cells(row: list, specs: dict[int, tuple[str, str]] | None = None) -> list[str]:
    if specs:
        return [_uic_raw_cell(row[idx]) for idx in specs if idx < len(row)]
    return [_uic_raw_cell(cell) for cell in row]


def _uic_staging_record(
    dataset_id: str,
    table_idx: int,
    row_type: str,
    row_idx: int,
    parse_status: str,
    *,
    geo: str | None = None,
    year: int | None = None,
    raw_geo_cell: str = "",
    raw_year_cell: str = "",
    raw_value_cells: list[str] | None = None,
    text_chunk: str = "",
    created_at: str | None = None,
) -> dict:
    return {
        "table_name": "uic_staging",
        "dataset_id": dataset_id,
        "table_id": f"{dataset_id}_{table_idx}_{row_type}",
        "table_idx": table_idx,
        "row_type": row_type,
        "row_idx": row_idx,
        "parse_status": parse_status,
        "geo": geo,
        "year": year,
        "source_dataset": dataset_id,
        "source_system": "uic",
        "raw_geo_cell": raw_geo_cell,
        "raw_year_cell": raw_year_cell,
        "raw_value_cells": raw_value_cells or [],
        "text_chunk": text_chunk,
        "created_at": _uic_now(created_at),
    }


def _uic_rows_from_tables_golden(tables: list[list[list]], dataset_id: str) -> pd.DataFrame:
    rows = []
    for table in tables:
        if not table:
            continue
        table_meta = _uic_table_specs(table)
        if table_meta is None:
            continue
        specs, data_start = table_meta
        current_geo = None
        for row in table[data_start:]:
            if not row or len(row) < 2:
                continue

            code_cell = row[0] if len(row) > 0 else None
            country_cell = row[21] if len(row) > 21 else None
            code_text = _clean_uic_text(code_cell)
            if code_text:
                current_geo = _uic_geo_from_cells(code_cell, country_cell)

            geo = current_geo
            if geo is None:
                continue

            year = _uic_year_from_company(row[1])
            if year is None:
                continue

            for col_idx, (label, unit) in specs.items():
                if col_idx >= len(row):
                    continue
                value = _parse_uic_number(row[col_idx])
                if value is None:
                    continue
                rows.append({
                    "geo": geo,
                    "year": year,
                    "value": value,
                    "unit": unit,
                    "source_dataset": dataset_id,
                    "source_column": label,
                    "source_system": "uic",
                })

    return pd.DataFrame(rows, columns=_LONG_COLS)


def _uic_rows_from_tables_staging(
    tables: list[list[list]],
    dataset_id: str,
    *,
    created_at: str | None = None,
) -> pd.DataFrame:
    rows = []
    for table_idx, table in enumerate(tables):
        if not table:
            continue

        table_meta = _uic_table_specs(table)
        if table_meta is None:
            for row_idx, row in enumerate(table):
                row = row or []
                row_type = "header" if row_idx == 0 else "data_row"
                rows.append(_uic_staging_record(
                    dataset_id,
                    table_idx,
                    row_type,
                    row_idx,
                    "table_mismatch",
                    raw_geo_cell=_uic_raw_cell(row[0]) if len(row) > 0 else "",
                    raw_year_cell=_uic_raw_cell(row[1]) if len(row) > 1 else "",
                    raw_value_cells=_uic_raw_value_cells(row),
                    created_at=created_at,
                ))
            continue

        specs, data_start = table_meta
        current_geo = None
        for row_idx, row in enumerate(table):
            row = row or []
            row_type = "header" if row_idx < data_start else "data_row"
            code_cell = row[0] if len(row) > 0 else None
            country_cell = row[21] if len(row) > 21 else None
            raw_geo_cell = _uic_raw_cell(code_cell)
            raw_year_cell = _uic_raw_cell(row[1]) if len(row) > 1 else ""
            raw_value_cells = _uic_raw_value_cells(row, specs)

            if row_type == "header":
                rows.append(_uic_staging_record(
                    dataset_id,
                    table_idx,
                    row_type,
                    row_idx,
                    "success",
                    raw_geo_cell=raw_geo_cell,
                    raw_year_cell=raw_year_cell,
                    raw_value_cells=raw_value_cells,
                    created_at=created_at,
                ))
                continue

            if raw_geo_cell:
                current_geo = _uic_geo_from_cells(code_cell, country_cell)
            geo = current_geo
            year = _uic_year_from_company(row[1]) if len(row) > 1 else None
            values = [
                _parse_uic_number(row[col_idx])
                for col_idx in specs
                if col_idx < len(row)
            ]

            if geo is None:
                parse_status = "geo_unmapped"
            elif year is None:
                parse_status = "year_missing"
            elif not any(value is not None for value in values):
                parse_status = "value_unparseable"
            else:
                parse_status = "success"

            rows.append(_uic_staging_record(
                dataset_id,
                table_idx,
                row_type,
                row_idx,
                parse_status,
                geo=geo,
                year=year,
                raw_geo_cell=raw_geo_cell,
                raw_year_cell=raw_year_cell,
                raw_value_cells=raw_value_cells,
                created_at=created_at,
            ))

    return pd.DataFrame(rows, columns=_UIC_STAGING_COLS)


def _uic_text_chunks_staging(text: str, dataset_id: str, *, created_at: str | None = None) -> pd.DataFrame:
    rows = []
    chunks = [_clean_uic_text(line) for line in str(text or "").splitlines()]
    for idx, chunk in enumerate(c for c in chunks if c):
        rows.append(_uic_staging_record(
            dataset_id,
            -1,
            "text_chunk",
            idx,
            "text_only",
            text_chunk=chunk,
            created_at=created_at,
        ))
    return pd.DataFrame(rows, columns=_UIC_STAGING_COLS)


def _uic_rows_from_tables(tables: list[list[list]], dataset_id: str) -> pd.DataFrame:
    return _uic_rows_from_tables_golden(tables, dataset_id)


def load_uic_frame(raw: bytes, dataset_id: str) -> pd.DataFrame:
    """Read UIC public PDF tables into the Silver long stats contract."""
    try:
        if not _looks_like_pdf(raw):
            logger.warning("uic %s: non-PDF payload; skipping", dataset_id)
            return _empty()

        text, tables = _extract_uic_pdf_text_and_tables(raw)
        if not text.strip() and not tables:
            logger.warning("uic %s: no extractable PDF text or tables; skipping", dataset_id)
            return _empty()

        frame = _uic_rows_from_tables_golden(tables, dataset_id)
        if frame.empty:
            logger.info("uic %s: no parseable UIC table rows; skipping", dataset_id)
            return _empty()

        frame = frame.dropna(subset=["year", "value"])
        if frame.empty:
            return _empty()
        return frame[_LONG_COLS]
    except Exception as exc:
        logger.warning("uic %s: PDF parse failed: %s", dataset_id, exc)
        return _empty()


def load_uic_staging_frame(raw: bytes, dataset_id: str, *, created_at: str | None = None) -> pd.DataFrame:
    """Read UIC PDF bytes into the audit staging contract.

    This captures table rows regardless of whether they become StatFact rows and
    also stages non-empty extracted text lines for text-only reports.
    """
    try:
        if not _looks_like_pdf(raw):
            logger.warning("uic %s: non-PDF payload; no staging rows", dataset_id)
            return _empty_uic_staging()

        text, tables = _extract_uic_pdf_text_and_tables(raw)
        parts = [
            _uic_rows_from_tables_staging(tables, dataset_id, created_at=created_at),
            _uic_text_chunks_staging(text, dataset_id, created_at=created_at),
        ]
        parts = [part for part in parts if not part.empty]
        if not parts:
            return _empty_uic_staging()
        return pd.concat(parts, ignore_index=True).reindex(columns=_UIC_STAGING_COLS)
    except Exception as exc:
        logger.warning("uic %s: PDF staging parse failed: %s", dataset_id, exc)
        return _empty_uic_staging()


# source -> (loader, accepted data-file suffixes); "_"-prefixed datasets
# (e.g. _catalogue_*) are skipped.
_SOURCES = {
    "worldbank": (load_worldbank_frame, (".json",)),
    "eurostat": (load_eurostat_frame, (".tsv", ".tsv.gz", ".gz")),
    "ksh": (load_ksh_frame, (".xlsx",)),
    "uic": (load_uic_frame, (".pdf",)),
    "statistik_austria": (load_stataustria_frame, (".ods",)),
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


def collect_uic_staging_from_bronze(root, *, created_at: str | None = None) -> pd.DataFrame:
    """Walk Bronze UIC PDFs and return the combined staging frame."""
    root = Path(root)
    frames = []
    base = root / "stats" / "uic"
    if not base.is_dir():
        return _empty_uic_staging()
    for ds_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        if ds_dir.name.startswith("_"):
            continue
        latest = _latest_partition(ds_dir)
        if latest is None:
            continue
        for f in sorted(latest.iterdir()):
            if f.name.endswith(".meta.json") or not f.name.endswith(".pdf"):
                continue
            frame = load_uic_staging_frame(f.read_bytes(), ds_dir.name, created_at=created_at)
            if not frame.empty:
                frames.append(frame)
    if not frames:
        return _empty_uic_staging()
    return pd.concat(frames, ignore_index=True).reindex(columns=_UIC_STAGING_COLS)


def build_silver_stats(
    root,
    *,
    use_llm: bool = False,
    out=None,
    uic_staging_root=None,
    ingest_date: str | None = None,
) -> pd.DataFrame:
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
    if uic_staging_root is not None:
        from .. import persist

        staging = collect_uic_staging_from_bronze(root)
        persist.persist_uic_staging(staging, uic_staging_root, ingest_date=ingest_date)
    return unified
