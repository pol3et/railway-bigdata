"""Deterministic GDELT GKG CSV.zip parser for transient Silver passthrough."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import zipfile
from collections.abc import Mapping

from ..schema import GKGRecord

logger = logging.getLogger("silver.news.gkg_parser")


def parse_gkg_csv(csv_text: str) -> list[GKGRecord]:
    """Parse one unzipped GDELT GKG tab-delimited CSV payload."""
    records: list[GKGRecord] = []
    reader = csv.reader(io.StringIO(csv_text), delimiter="\t")
    for line_number, fields in enumerate(reader, start=1):
        if not fields or not any(field.strip() for field in fields):
            continue
        try:
            if _is_gkg_2x(fields):
                records.append(_parse_gkg_2x(fields))
            elif _is_gkg_1x(fields):
                records.append(_parse_gkg_1x(fields))
            else:
                logger.warning(
                    "skipping malformed GKG row %d: expected GKG 1.0/2.x "
                    "tab-delimited columns, got %d",
                    line_number,
                    len(fields),
                )
        except (IndexError, ValueError) as exc:
            logger.warning("skipping malformed GKG row %d: %s", line_number, exc)
    return records


def parse_gkg_csv_zip(zip_bytes: bytes, date_str: str) -> list[GKGRecord]:
    """Unzip a daily GKG CSV.zip and parse its first CSV member."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            csv_names = [
                name for name in archive.namelist()
                if not name.endswith("/") and name.lower().endswith(".csv")
            ]
            if not csv_names:
                logger.warning("failed to read GKG zip %s: no CSV member", date_str)
                return []
            data = archive.read(csv_names[0])
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        logger.warning("failed to read GKG zip %s: %s", date_str, exc)
        return []
    text = data.decode("utf-8", errors="replace")
    return parse_gkg_csv(text)


def gkg_record_id(gkg_row: Mapping) -> str:
    """Return a stable GKG id, hashing key fields when no source id exists."""
    existing = _first_mapping_value(
        gkg_row,
        "GKGRECORDID",
        "gkg_id",
        "GKGRecordID",
        "record_id",
    )
    if existing:
        return str(existing)
    payload = {
        "date": _first_mapping_value(gkg_row, "DATE", "Date", "gkg_date", "V2.1DATE"),
        "document_identifier": _first_mapping_value(
            gkg_row,
            "DocumentIdentifier",
            "V2DOCUMENTIDENTIFIER",
            "SOURCEURLS",
            "document_identifier",
        ),
        "themes": _first_mapping_value(gkg_row, "Themes", "THEMES", "gkg_themes"),
        "tone": _first_mapping_value(gkg_row, "Tone", "TONE", "gkg_tone"),
        "locations": _first_mapping_value(gkg_row, "Locations", "LOCATIONS", "gkg_locations"),
    }
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def match_gkg_to_article(gkg_record: GKGRecord, article_url: str) -> bool:
    """Best-effort exact URL match against a GKG document/source URL field."""
    target = _normalize_url(article_url)
    if not target or not gkg_record.document_identifier:
        return False
    for candidate in _split_document_identifiers(gkg_record.document_identifier):
        if _normalize_url(candidate) == target:
            return True
    return False


def _is_gkg_2x(fields: list[str]) -> bool:
    return len(fields) >= 16 and _digits_len(fields[1]) >= 8


def _is_gkg_1x(fields: list[str]) -> bool:
    return len(fields) >= 21 and _digits_len(fields[0]) == 8


def _parse_gkg_2x(fields: list[str]) -> GKGRecord:
    tone, emotions = _parse_tone_and_emotions(fields[15])
    row = {
        "GKGRECORDID": _clean(fields[0]),
        "V2.1DATE": _clean(fields[1]),
        "DocumentIdentifier": _clean(fields[4]),
        "Themes": fields[8] or fields[7],
        "Tone": fields[15],
        "Locations": fields[10] or fields[9],
    }
    return GKGRecord(
        gkg_id=_clean(fields[0]) or gkg_record_id(row),
        gkg_date=_clean(fields[1]),
        document_identifier=_clean(fields[4]),
        source_common_name=_clean(fields[3]),
        gkg_themes=_normalize_enhanced_semicolon(fields[8]) or _normalize_semicolon(fields[7]),
        gkg_tone=tone,
        gkg_persons=_normalize_enhanced_semicolon(fields[12]) or _normalize_semicolon(fields[11]),
        gkg_organizations=(
            _normalize_enhanced_semicolon(fields[14]) or _normalize_semicolon(fields[13])
        ),
        gkg_locations=_clean_semicolon(fields[10]) or _clean_semicolon(fields[9]),
        gkg_emotions=emotions,
    )


def _parse_gkg_1x(fields: list[str]) -> GKGRecord:
    tone, emotions = _parse_tone_and_emotions(fields[15])
    row = {
        "DATE": _clean(fields[0]),
        "SOURCEURLS": _clean(fields[14]),
        "Themes": fields[17],
        "Tone": fields[15],
        "Locations": fields[18],
    }
    return GKGRecord(
        gkg_id=gkg_record_id(row),
        gkg_date=_clean(fields[0]),
        document_identifier=_clean_semicolon(fields[14]),
        source_common_name=_clean_semicolon(fields[13]),
        gkg_themes=_normalize_semicolon(fields[17]),
        gkg_tone=tone,
        gkg_persons=_normalize_semicolon(fields[19]),
        gkg_organizations=_normalize_semicolon(fields[20]),
        gkg_locations=_clean_semicolon(fields[18]),
        gkg_emotions=emotions,
    )


def _parse_tone_and_emotions(value: str) -> tuple[float | None, str | None]:
    parts = [part.strip() for part in str(value or "").split(",")]
    tone = _float_or_none(parts[0]) if parts and parts[0] else None
    emotions = ",".join(part for part in parts[1:] if part)
    return tone, emotions or None


def _normalize_enhanced_semicolon(value: str) -> str | None:
    entries = []
    for entry in _split_semicolon(value):
        entries.append(re.sub(r",\d+$", "", entry).strip())
    return _join_entries(entries)


def _normalize_semicolon(value: str) -> str | None:
    return _join_entries(_split_semicolon(value))


def _clean_semicolon(value: str) -> str | None:
    return _join_entries(_split_semicolon(value))


def _split_semicolon(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def _join_entries(entries: list[str]) -> str | None:
    cleaned = [entry for entry in entries if entry]
    return ";".join(cleaned) if cleaned else None


def _split_document_identifiers(value: str) -> list[str]:
    return [item for item in re.split(r"[;\s|]+", value or "") if item]


def _normalize_url(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.rstrip("/").lower()


def _first_mapping_value(mapping: Mapping, *keys: str):
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    lowered = {str(key).lower(): value for key, value in mapping.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def _digits_len(value: str) -> int:
    return len(str(value or "").strip()) if str(value or "").strip().isdigit() else 0


def _clean(value: str) -> str | None:
    text = str(value or "").strip()
    return text or None


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
