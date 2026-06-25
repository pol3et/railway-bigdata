"""Spark-backed checks for the correlation and regional analysis jobs."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

pyspark = pytest.importorskip("pyspark")

from railway_lakehouse.spark_jobs import correlations, regional

pytestmark = pytest.mark.spark


def _skip_if_missing_windows_hadoop_native() -> None:
    if sys.platform != "win32":
        return

    if not os.environ.get("JAVA_HOME"):
        pytest.skip("Spark on Windows requires JAVA_HOME to point at JDK 17 or 21")

    hadoop_home = os.environ.get("HADOOP_HOME")
    if not hadoop_home:
        pytest.skip(
            "Spark Parquet writes on Windows require HADOOP_HOME with "
            "bin/winutils.exe"
        )

    winutils = Path(hadoop_home) / "bin" / "winutils.exe"
    if not winutils.is_file():
        pytest.skip(
            "Spark Parquet writes on Windows require a usable Hadoop native "
            f"helper at {winutils}"
        )


def _write_analysis_gold(path: Path) -> None:
    rows: list[dict[str, object]] = []
    for geo, base_invest, base_network in (
        ("AT", 1000.0, 5000.0),
        ("HU", 700.0, 7600.0),
    ):
        for offset, year in enumerate(range(2020, 2025)):
            invest = base_invest + offset * 80.0
            network = base_network + offset * 20.0
            rows.append(
                {
                    "geo": geo,
                    "geo_level": "country",
                    "year": year,
                    "rail_investment": invest,
                    "rail_investment_pps": invest * 1.2,
                    "population_total": 5_000_000.0 + offset * 1000.0,
                    "gdp_current_meur": 100_000.0 + offset * 2500.0,
                    "rail_network_length_km": network,
                    "rail_electrified_km": network * 0.6,
                    "life_satisfaction": 6.0 + offset * 0.2,
                }
            )

    for country, regions in (
        ("AT", ("AT11", "AT12", "AT13")),
        ("HU", ("HU11", "HU12", "HU13")),
    ):
        for offset, year in enumerate(range(2020, 2025)):
            for region_index, region_code in enumerate(regions):
                network = 100.0 + region_index * 30.0 + offset * 2.0
                rows.append(
                    {
                        "geo": region_code,
                        "geo_level": "region",
                        "year": year,
                        "rail_investment": None,
                        "rail_investment_pps": None,
                        "population_total": None,
                        "gdp_current_meur": None,
                        "rail_network_length_km": network,
                        "rail_electrified_km": network * (0.45 + region_index * 0.1),
                        "life_satisfaction": None,
                    }
                )

    pd.DataFrame(rows).to_parquet(path, index=False)


def test_correlations_default_input_fails_before_passing_on_missing_targets(tmp_path: Path):
    if sys.platform == "win32" and not os.environ.get("JAVA_HOME"):
        pytest.skip("Spark on Windows requires JAVA_HOME to point at JDK 17 or 21")
    spark = correlations.build_session("local[1]")
    try:
        with pytest.raises(ValueError, match="No investment target columns"):
            correlations.run_correlations(
                spark,
                correlations.DEFAULT_INPUT,
                tmp_path / "corr-default",
                min_obs=2,
            )
    finally:
        spark.stop()


def test_regional_default_input_fails_before_passing_on_missing_columns(tmp_path: Path):
    if sys.platform == "win32" and not os.environ.get("JAVA_HOME"):
        pytest.skip("Spark on Windows requires JAVA_HOME to point at JDK 17 or 21")
    spark = regional.build_session("local[1]")
    try:
        with pytest.raises(ValueError, match="missing required regional columns"):
            regional.run_regional(
                spark,
                regional.DEFAULT_INPUT,
                tmp_path / "regional-default",
                min_regions=2,
            )
    finally:
        spark.stop()


def test_correlations_writes_mode_specific_outputs(tmp_path: Path):
    _skip_if_missing_windows_hadoop_native()
    input_path = tmp_path / "gold.parquet"
    out_dir = tmp_path / "correlations"
    _write_analysis_gold(input_path)

    spark = correlations.build_session("local[1]")
    try:
        levels = correlations.run_correlations(
            spark,
            input_path,
            out_dir,
            min_obs=2,
            by_country=True,
        )
        panel = correlations.run_correlations(
            spark,
            input_path,
            out_dir,
            min_obs=2,
            panel=True,
            by_country=True,
        )
    finally:
        spark.stop()

    assert levels["status"] == "passed"
    assert panel["status"] == "passed"
    assert levels["output_path"].endswith("correlations_by_country_levels")
    assert panel["output_path"].endswith("correlations_by_country_panel")
    assert levels["output_path"] != panel["output_path"]
    assert (out_dir / "correlations_by_country_levels" / "_SUCCESS").is_file()
    assert (out_dir / "correlations_by_country_panel" / "_SUCCESS").is_file()

    rows = pd.read_csv(out_dir / "correlations_by_country_levels.csv")
    assert set(rows["geo"]) == {"AT", "HU"}
    assert rows["n"].min() >= 2


def test_regional_writes_non_empty_manifest_and_outputs(tmp_path: Path):
    _skip_if_missing_windows_hadoop_native()
    input_path = tmp_path / "gold.parquet"
    out_dir = tmp_path / "regional"
    _write_analysis_gold(input_path)

    spark = regional.build_session("local[1]")
    try:
        manifest = regional.run_regional(
            spark,
            input_path,
            out_dir,
            min_regions=2,
        )
    finally:
        spark.stop()

    assert manifest["status"] == "passed"
    assert manifest["region_rows"] == 30
    assert manifest["nuts2_regions"] == 6
    assert manifest["investment_vs_disparity"]["n"] >= 4
    assert (out_dir / "descriptives" / "_SUCCESS").is_file()
    assert (out_dir / "inequality" / "_SUCCESS").is_file()

    persisted_manifest = json.loads((out_dir / "manifest.json").read_text())
    assert persisted_manifest["outputs"]["descriptives_csv"] == (
        out_dir / "regional_descriptives.csv"
    ).as_posix()
