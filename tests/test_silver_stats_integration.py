"""
GAP-006 (Silver Stats / World Bank + Eurostat slice) integration test.

Reads real Bronze *fixture files* end-to-end and asserts the unified StatFact
table: provenance is preserved, numbers are passed through verbatim (no LLM
rewriting), unmapped labels stay visible in the crosswalk cache (and are
dropped, not guessed), and the Silver output is persisted to Parquet.

Run with:  python -m pytest -q -m integration
"""
from pathlib import Path

import pandas as pd
import pytest

from railway_lakehouse.silver.stats import load as stats_load
from railway_lakehouse.silver.stats import merge as stats_merge

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent / "fixtures" / "bronze"


def test_build_silver_stats_from_bronze_fixtures(tmp_path, monkeypatch):
    # isolate the reviewable crosswalk cache so we can assert on it
    cache_path = tmp_path / "crosswalk_cache.json"
    monkeypatch.setattr(stats_merge, "CROSSWALK_PATH", str(cache_path))

    out = tmp_path / "silver" / "stats.parquet"
    unified = stats_load.build_silver_stats(FIXTURES, use_llm=False, out=out)

    # schema is the StatFact long contract
    assert list(unified.columns) == [
        "geo", "year", "feature", "value", "unit",
        "source_system", "source_dataset", "source_column",
    ]

    # both sources landed, each tagged with its own provenance
    assert set(unified["source_system"]) == {"worldbank", "eurostat"}

    # World Bank passenger-km mapped + value passed through verbatim
    wb = unified[(unified["source_system"] == "worldbank")
                 & (unified["geo"] == "HU") & (unified["year"] == 2021)].iloc[0]
    assert wb["feature"] == "rail_passenger_km"
    assert wb["value"] == 5435.389
    assert wb["source_dataset"] == "IS.RRS.PASG.KM"

    at_wb = unified[(unified["source_system"] == "worldbank")
                    & (unified["geo"] == "AT") & (unified["year"] == 2021)].iloc[0]
    assert at_wb["feature"] == "rail_passenger_km"
    assert at_wb["value"] == 13127.0
    assert "AU" not in set(unified["geo"])

    # Eurostat passengers mapped + flag-stripped numeric
    es = unified[(unified["source_system"] == "eurostat")
                 & (unified["geo"] == "HU") & (unified["year"] == 2020)].iloc[0]
    assert es["feature"] == "rail_passengers"
    assert es["value"] == 100

    # the broad CO2 indicator is UNMAPPED: visible in the cache, absent from output
    import json
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    co2_label = next(k for k in cache if "Carbon dioxide" in k)
    assert cache[co2_label] == "unmapped"
    assert "EN.GHG.CO2.TR.MT.CE.AR5" not in set(unified["source_dataset"])

    # Silver output persisted and round-trips
    assert out.exists()
    assert len(pd.read_parquet(out)) == len(unified)
    assert len(unified) >= 3
