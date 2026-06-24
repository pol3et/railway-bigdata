"""Deterministic coverage for the live MinIO/S3 stats read-back branch."""
import json
from types import SimpleNamespace

import fsspec
import pytest

from railway_lakehouse.bronze.config import BRONZE_BUCKET
from railway_lakehouse import pipeline

pytestmark = pytest.mark.integration


def _write(fs, path: str, data: bytes) -> None:
    fs.makedirs(path.rsplit("/", 1)[0], exist_ok=True)
    with fs.open(path, "wb") as fh:
        fh.write(data)


def test_live_stats_frames_include_worldbank_from_s3_branch():
    fs = fsspec.filesystem("memory")
    fs.store.clear()
    eurostat_path = (
        f"{BRONZE_BUCKET}/stats/eurostat/rail_pa_total/"
        "ingest_date=2026-06-24/rail_pa_total.tsv"
    )
    worldbank_path = (
        f"{BRONZE_BUCKET}/stats/worldbank/NY.GDP.MKTP.CD/"
        "ingest_date=2026-06-24/NY.GDP.MKTP.CD.json"
    )
    catalogue_path = (
        f"{BRONZE_BUCKET}/stats/worldbank/_catalogue_indicators/"
        "ingest_date=2026-06-24/indicators.json"
    )
    _write(fs, eurostat_path, b"freq,unit,geo\\TIME_PERIOD\t2021\nA,MIO_PKM,HU\t12.5\n")
    _write(
        fs,
        worldbank_path,
        json.dumps(
            [
                {"page": 1, "pages": 1, "per_page": 1, "total": 1},
                [
                    {
                        "countryiso3code": "HUN",
                        "country": {"id": "HU"},
                        "date": "2021",
                        "value": 181000.0,
                        "indicator": {
                            "id": "NY.GDP.MKTP.CD",
                            "value": "GDP (current US$)",
                        },
                    }
                ],
            ]
        ).encode("utf-8"),
    )
    _write(fs, catalogue_path, b'[{"page":1}, []]')

    frames = pipeline._read_bronze_stats_frames(SimpleNamespace(s3=fs))

    by_source = {
        source: frame for frame in frames
        if not frame.empty for source in [frame["source_system"].iloc[0]]
    }
    assert set(by_source) == {"eurostat", "worldbank"}
    wb = by_source["worldbank"].iloc[0]
    assert wb["geo"] == "HU"
    assert wb["year"] == 2021
    assert wb["value"] == 181000.0
    assert wb["source_column"] == "gdp_current_usd"
