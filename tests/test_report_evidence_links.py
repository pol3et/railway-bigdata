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


def _assert_values_in_report(report_text: str, values: list[Any]) -> None:
    missing = [_json_value_token(value) for value in values if _json_value_token(value) not in report_text]
    assert missing == []


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


def test_report_headline_numbers_match_evidence_json() -> None:
    report_text = _read_text(REPORT)
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

    headline_values = [
        counts["rows"],
        counts["columns"],
        counts["geos_count"],
        counts["year_min"],
        counts["year_max"],
        counts["at_rows"],
        counts["hu_rows"],
        *counts["column_names"],
        samples["gold"]["rows"],
        samples["gold"]["geos"],
        samples["silver_stats"]["reloaded_rows"],
        at_1995["geo"],
        at_1995["year"],
        at_1995["rail_freight_tonne_km"],
        at_1995["rail_network_length_km"],
        hu_1995["geo"],
        hu_1995["year"],
        hu_1995["rail_freight_tonne_km"],
        hu_1995["rail_network_length_km"],
        worldbank_summary["status"],
        worldbank_summary["artifact_count"],
        worldbank_summary["byte_count"],
        eurostat_summary["status"],
        minio_manifest["status"],
        minio_manifest["roundtrip_ok"],
        *minio_manifest["buckets"],
        minio_manifest["bytes_written"],
        minio_manifest["bytes_read"],
        first_gold_counts["rows"],
        first_gold_counts["columns"],
        first_gold_counts["geos_count"],
        spark_manifest["status"],
        spark_manifest["spark_version"],
        spark_manifest["java_version"],
        spark_manifest["input_rows"],
        spark_manifest["input_columns"],
        spark_manifest["output_rows"],
        spark_manifest["output_columns"],
        spark_manifest["partitions_written"],
    ]

    _assert_values_in_report(report_text, headline_values)
