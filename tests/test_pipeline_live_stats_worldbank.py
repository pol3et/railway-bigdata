"""Deterministic coverage for the live MinIO/S3 stats read-back branch."""
from __future__ import annotations

import json
import logging
from types import SimpleNamespace

import fsspec
import pytest

from railway_lakehouse import pipeline
from railway_lakehouse.bronze.config import BRONZE_BUCKET


pytestmark = pytest.mark.integration


def _memory_lander():
    fs = fsspec.filesystem("memory")
    fs.store.clear()
    return SimpleNamespace(s3=fs)


def _write(fs, path: str, data: bytes) -> None:
    fs.makedirs(path.rsplit("/", 1)[0], exist_ok=True)
    with fs.open(path, "wb") as fh:
        fh.write(data)


def _seed_eurostat(fs) -> None:
    dataset_id = "rail_pa_total"
    base = f"{BRONZE_BUCKET}/stats/eurostat/{dataset_id}/ingest_date=2026-06-24"
    _write(
        fs,
        f"{base}/{dataset_id}.tsv",
        b"freq,unit,geo\\TIME_PERIOD\t2021\nA,MIO_PKM,HU\t12.5\n",
    )
    _write(fs, f"{base}/{dataset_id}.meta.json", b"{}")


def _seed_worldbank(fs, dataset_id: str = "IS.RRS.TOTL.KM") -> None:
    base = f"{BRONZE_BUCKET}/stats/worldbank/{dataset_id}/ingest_date=2026-06-24"
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
    _write(fs, f"{base}/{dataset_id}.json", json.dumps(payload).encode("utf-8"))
    _write(fs, f"{base}/{dataset_id}.meta.json", b"{}")
    _write(
        fs,
        f"{BRONZE_BUCKET}/stats/worldbank/_catalogue_indicators/"
        "ingest_date=2026-06-24/indicators.json",
        b'[{"page":1}, []]',
    )


def test_live_stats_frames_include_worldbank_and_eurostat_from_memory_s3():
    lander = _memory_lander()
    _seed_eurostat(lander.s3)
    _seed_worldbank(lander.s3)

    frames = pipeline._read_bronze_stats_frames(lander)

    by_source = {
        source: frame for frame in frames
        if not frame.empty for source in [frame["source_system"].iloc[0]]
    }
    assert set(by_source) == {"eurostat", "worldbank"}
    worldbank = by_source["worldbank"]
    assert set(worldbank["geo"]) == {"HU", "AT"}
    assert dict(zip(worldbank["geo"], worldbank["value"], strict=False)) == {
        "HU": 789.12,
        "AT": 456.78,
    }
    assert set(worldbank["source_dataset"]) == {"IS.RRS.TOTL.KM"}
    assert set(worldbank["source_column"]) == {"rail_network_length_km"}


def test_live_stats_frames_warn_when_worldbank_absent(caplog):
    lander = _memory_lander()
    _seed_eurostat(lander.s3)

    with caplog.at_level(logging.WARNING, logger=pipeline.__name__):
        frames = pipeline._read_bronze_stats_frames(lander)

    assert any((frame["source_system"] == "eurostat").any() for frame in frames)
    assert "live stats read produced 0 World Bank frames" in caplog.text
