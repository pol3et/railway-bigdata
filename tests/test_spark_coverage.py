"""Spark-backed checks for the GAP-009 coverage evidence job."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

pyspark = pytest.importorskip("pyspark")

from railway_lakehouse.spark_jobs import coverage

pytestmark = pytest.mark.spark


def _write_gold(path: Path) -> None:
    df = pd.DataFrame(
        [
            {
                "geo": "AT",
                "year": 2020,
                "rail_freight_tonne_km": 100.0,
                "rail_network_length_km": 5000.0,
            },
            {
                "geo": "AT",
                "year": 2021,
                "rail_freight_tonne_km": None,
                "rail_network_length_km": 5010.0,
            },
            {
                "geo": "HU",
                "year": 2021,
                "rail_freight_tonne_km": 80.0,
                "rail_network_length_km": None,
            },
        ]
    )
    df.to_parquet(path, index=False)


def _part_files(path: Path) -> list[Path]:
    return sorted(path.rglob("part-*.parquet"))


def test_main_reads_gold_and_writes_manifest_and_spark_parquet(tmp_path: Path):
    input_path = tmp_path / "gold.parquet"
    out_dir = tmp_path / "evidence" / "spark"
    _write_gold(input_path)

    rc = coverage.main(
        [
            "--input",
            input_path.as_posix(),
            "--out",
            out_dir.as_posix(),
            "--master",
            "local[1]",
        ]
    )

    assert rc == 0

    output_path = out_dir / "coverage_by_geo_year"
    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert output_path.is_dir()
    assert (output_path / "_SUCCESS").is_file()
    assert _part_files(output_path)

    assert manifest["status"] == "passed"
    assert manifest["spark_version"]
    assert manifest["input_rows"] == 3
    assert manifest["input_columns"] == 4
    assert manifest["input_column_names"] == [
        "geo",
        "year",
        "rail_freight_tonne_km",
        "rail_network_length_km",
    ]
    assert manifest["output_rows"] == 3
    assert manifest["output_columns"] == 5
    assert manifest["output_path"] == output_path.as_posix()
    assert "_SUCCESS" in manifest["files_written"]
    assert manifest["partitions_written"] >= 1
    assert manifest["duration_seconds"] >= 0
    assert manifest["evidence_path"] == manifest_path.as_posix()


def test_run_coverage_fails_loudly_for_missing_and_empty_input(tmp_path: Path):
    spark = coverage.build_session("local[1]")
    try:
        missing_path = tmp_path / "missing.parquet"
        with pytest.raises(FileNotFoundError, match="run the Gold pipeline first"):
            coverage.run_coverage(spark, missing_path, tmp_path / "missing-evidence")

        empty_path = tmp_path / "empty.parquet"
        pd.DataFrame(
            columns=[
                "geo",
                "year",
                "rail_freight_tonne_km",
                "rail_network_length_km",
            ]
        ).to_parquet(empty_path, index=False)

        with pytest.raises(ValueError, match="0 rows"):
            coverage.run_coverage(spark, empty_path, tmp_path / "empty-evidence")
    finally:
        spark.stop()
