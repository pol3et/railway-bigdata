"""Validate report deliverables against committed evidence artifacts.

This unit test intentionally reads first-class committed deliverables under
`output/report/`, `output/presentation/`, and `output/evidence/`. It does not
read coursework data, start services, or depend on live Bronze raw files; the
JSON evidence artifacts are the contract the final course report must cite.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT = REPO_ROOT / "output/report/REPORT.md"
PRESENTATION = REPO_ROOT / "output/presentation/PRESENTATION.md"
EVIDENCE_PATH_RE = re.compile(r"output/evidence/[^\s\)\]\"`]+")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _evidence_paths(*texts: str) -> set[str]:
    return {match.rstrip(".,;:") for text in texts for match in EVIDENCE_PATH_RE.findall(text)}


def _load_json(path: str) -> dict[str, Any]:
    with (REPO_ROOT / path).open(encoding="utf-8") as handle:
        return json.load(handle)


def _json_value_token(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _claim_token(key: str, value: Any) -> str:
    return f"{key}={_json_value_token(value)}"


def _headline_claim_tokens() -> list[str]:
    counts = _load_json("output/evidence/inventory-live-2026-06-23/counts.json")
    samples = _load_json("output/evidence/inventory-live-2026-06-23/inventory_samples.json")
    inventory_manifest = _load_json("output/evidence/inventory-live-2026-06-23/manifest.json")
    minio_manifest = _load_json("output/evidence/minio-smoke/manifest.json")
    first_gold_counts = _load_json("output/evidence/first-real-gold-local-stats-v2/counts.json")
    spark_manifest = _load_json("output/evidence/spark/manifest.json")

    worldbank_summary = next(
        source for source in inventory_manifest["sources"] if source["source"] == "worldbank"
    )
    eurostat_summary = next(
        source for source in inventory_manifest["sources"] if source["source"] == "eurostat"
    )
    at_1995 = samples["gold"]["sample_AT"][0]
    hu_1995 = samples["gold"]["sample_HU"][0]

    return [
        _claim_token("rows", counts["rows"]),
        _claim_token("columns", counts["columns"]),
        _claim_token("geos_count", counts["geos_count"]),
        _claim_token("year_min", counts["year_min"]),
        _claim_token("year_max", counts["year_max"]),
        _claim_token("at_rows", counts["at_rows"]),
        _claim_token("hu_rows", counts["hu_rows"]),
        _claim_token("rail_freight_tonne_km", at_1995["rail_freight_tonne_km"]),
        _claim_token("rail_network_length_km", at_1995["rail_network_length_km"]),
        _claim_token("rail_freight_tonne_km", hu_1995["rail_freight_tonne_km"]),
        _claim_token("rail_network_length_km", hu_1995["rail_network_length_km"]),
        _claim_token("silver_stats.reloaded_rows", samples["silver_stats"]["reloaded_rows"]),
        _claim_token("worldbank.status", worldbank_summary["status"]),
        _claim_token("worldbank.artifact_count", worldbank_summary["artifact_count"]),
        _claim_token("worldbank.byte_count", worldbank_summary["byte_count"]),
        _claim_token("eurostat.status", eurostat_summary["status"]),
        _claim_token("minio.status", minio_manifest["status"]),
        _claim_token("roundtrip_ok", minio_manifest["roundtrip_ok"]),
        _claim_token("bytes_written", minio_manifest["bytes_written"]),
        _claim_token("bytes_read", minio_manifest["bytes_read"]),
        _claim_token("first_gold.rows", first_gold_counts["rows"]),
        _claim_token("first_gold.columns", first_gold_counts["columns"]),
        _claim_token("first_gold.geos_count", first_gold_counts["geos_count"]),
        _claim_token("spark.status", spark_manifest["status"]),
        _claim_token("spark_version", spark_manifest["spark_version"]),
        _claim_token("java_version", spark_manifest["java_version"]),
        _claim_token("input_rows", spark_manifest["input_rows"]),
        _claim_token("input_columns", spark_manifest["input_columns"]),
        _claim_token("output_rows", spark_manifest["output_rows"]),
        _claim_token("output_columns", spark_manifest["output_columns"]),
        _claim_token("partitions_written", spark_manifest["partitions_written"]),
    ]


def _assert_claim_tokens_in_texts(text_by_name: dict[str, str]) -> None:
    claim_tokens = _headline_claim_tokens()
    missing = {
        name: [token for token in claim_tokens if token not in text]
        for name, text in text_by_name.items()
    }
    assert missing == {name: [] for name in text_by_name}


def test_report_and_presentation_exist() -> None:
    assert REPORT.exists()
    assert PRESENTATION.exists()


def test_all_cited_evidence_paths_exist() -> None:
    report_text = _read_text(REPORT)
    presentation_text = _read_text(PRESENTATION)

    missing = [
        path
        for path in sorted(_evidence_paths(report_text, presentation_text))
        if not (REPO_ROOT / path).exists()
    ]

    assert missing == []


def test_report_and_presentation_headline_claims_match_evidence_json() -> None:
    report_text = _read_text(REPORT)
    presentation_text = _read_text(PRESENTATION)

    _assert_claim_tokens_in_texts(
        {
            "REPORT.md": report_text,
            "PRESENTATION.md": presentation_text,
        }
    )
