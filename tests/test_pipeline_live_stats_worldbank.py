from __future__ import annotations

import json
import logging
from types import SimpleNamespace

import fsspec
import pytest

from railway_lakehouse import pipeline


pytestmark = pytest.mark.integration


def _memory_lander():
    fs = fsspec.filesystem("memory")
    fs.store.clear()
    return SimpleNamespace(s3=fs)


def _seed_eurostat(fs) -> None:
    dataset_id = "rail_test"
    base = f"bronze/stats/eurostat/{dataset_id}/ingest_date=2026-06-23"
    fs.pipe(f"{base}/{dataset_id}.tsv", b"metric\t2024\nlegacy,HU\t7\n")
    fs.pipe(f"{base}/{dataset_id}.meta.json", b"{}")


def _seed_worldbank(fs) -> None:
    dataset_id = "IS.RRS.TOTL.KM"
    base = f"bronze/stats/worldbank/{dataset_id}/ingest_date=2026-06-23"
    payload = [
        {"page": 1, "pages": 1, "per_page": 2, "total": 2},
        [
            {
                "countryiso3code": "HUN",
                "country": {"id": "HU", "value": "Hungary"},
                "date": "2023",
                "value": 789.12,
                "indicator": {"id": dataset_id, "value": "Rail lines"},
            },
            {
                "countryiso3code": "AUT",
                "country": {"id": "AT", "value": "Austria"},
                "date": "2023",
                "value": 456.78,
                "indicator": {"id": dataset_id, "value": "Rail lines"},
            },
        ],
    ]
    fs.pipe(f"{base}/{dataset_id}.json", json.dumps(payload).encode("utf-8"))
    fs.pipe(f"{base}/{dataset_id}.meta.json", b"{}")
    fs.pipe(
        "bronze/stats/worldbank/_catalogue/ingest_date=2026-06-23/_catalogue.json",
        json.dumps(payload).encode("utf-8"),
    )


def test_live_stats_frames_include_worldbank_and_eurostat_from_memory_s3():
    lander = _memory_lander()
    _seed_eurostat(lander.s3)
    _seed_worldbank(lander.s3)

    frames = pipeline._read_bronze_stats_frames(lander)

    assert any((frame["source_system"] == "eurostat").any() for frame in frames)
    worldbank_frames = [
        frame for frame in frames if (frame["source_system"] == "worldbank").any()
    ]
    assert len(worldbank_frames) == 1
    worldbank = worldbank_frames[0]
    assert set(worldbank["geo"]) == {"HU", "AT"}
    assert dict(zip(worldbank["geo"], worldbank["value"])) == {
        "HU": 789.12,
        "AT": 456.78,
    }
    assert set(worldbank["source_dataset"]) == {"IS.RRS.TOTL.KM"}


def test_live_stats_frames_warn_when_worldbank_absent(caplog):
    lander = _memory_lander()
    _seed_eurostat(lander.s3)

    with caplog.at_level(logging.WARNING, logger=pipeline.__name__):
        frames = pipeline._read_bronze_stats_frames(lander)

    assert any((frame["source_system"] == "eurostat").any() for frame in frames)
    assert "live stats read produced 0 World Bank frames" in caplog.text
