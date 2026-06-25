import json

import pytest

from railway_lakehouse.gold.build import build_gold
from railway_lakehouse.silver.stats import load as stats_load
from railway_lakehouse.silver.stats import merge as stats_merge


def _worldbank_payload(indicator_id: str, indicator_name: str, rows: list[tuple[str, int, float]]) -> bytes:
    records = [
        {
            "indicator": {"id": indicator_id, "value": indicator_name},
            "countryiso3code": iso3,
            "date": str(year),
            "value": value,
            "unit": "",
            "obs_status": "",
            "decimal": 2,
        }
        for iso3, year, value in rows
    ]
    return json.dumps([{"page": 1, "total": len(records)}, records]).encode()


def _macro_payloads() -> dict[str, bytes]:
    return {
        "IS.VEH.PCAR.P3": _worldbank_payload(
            "IS.VEH.PCAR.P3",
            "Passenger cars (per 1,000 people)",
            [("AUT", 2021, 566.2), ("HUN", 2021, 404.8)],
        ),
        "PA.NUS.PPP": _worldbank_payload(
            "PA.NUS.PPP",
            "PPP conversion factor, GDP (LCU per international $)",
            [("AUT", 2021, 0.7573), ("HUN", 2021, 142.6637)],
        ),
    }


@pytest.fixture(autouse=True)
def _isolate_crosswalk_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(stats_merge, "CROSSWALK_PATH", str(tmp_path / "crosswalk_cache.json"))


@pytest.mark.unit
def test_worldbank_macro_indicators_crosswalk_to_canonical_features():
    frames = [
        stats_load.load_worldbank_frame(payload, indicator_id)
        for indicator_id, payload in _macro_payloads().items()
    ]
    labels = sorted({label for frame in frames for label in frame["source_column"].astype(str)})
    sources = {label: "worldbank" for label in labels}
    crosswalk = stats_merge.build_crosswalk(labels, sources=sources, use_llm=False)

    unified = stats_merge.merge_sources(frames, crosswalk)

    assert set(unified["feature"]) == {"cars_per_1000", "ppp_conversion_factor"}
    cars_at = unified[
        (unified["feature"] == "cars_per_1000")
        & (unified["geo"] == "AT")
        & (unified["year"] == 2021)
    ].iloc[0]
    ppp_hu = unified[
        (unified["feature"] == "ppp_conversion_factor")
        & (unified["geo"] == "HU")
        & (unified["year"] == 2021)
    ].iloc[0]
    assert cars_at["value"] == 566.2
    assert ppp_hu["value"] == 142.6637
    assert set(unified["source_system"]) == {"worldbank"}


@pytest.mark.integration
def test_worldbank_macro_indicators_reach_gold_from_tmp_bronze(tmp_path):
    bronze = tmp_path / "bronze"
    for indicator_id, payload in _macro_payloads().items():
        dataset_dir = bronze / "stats" / "worldbank" / indicator_id / "ingest_date=2026-06-25"
        dataset_dir.mkdir(parents=True)
        (dataset_dir / f"{indicator_id}.json").write_bytes(payload)

    silver = stats_load.build_silver_stats(bronze, use_llm=False)
    gold = build_gold(silver, [])

    assert {"cars_per_1000", "ppp_conversion_factor"} <= set(gold.columns)
    at = gold[(gold["geo"] == "AT") & (gold["year"] == 2021)].iloc[0]
    hu = gold[(gold["geo"] == "HU") & (gold["year"] == 2021)].iloc[0]
    assert at["cars_per_1000"] == 566.2
    assert at["ppp_conversion_factor"] == 0.7573
    assert hu["cars_per_1000"] == 404.8
    assert hu["ppp_conversion_factor"] == 142.6637
