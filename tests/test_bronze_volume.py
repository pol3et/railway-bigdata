import gzip
import json

import pytest

from scripts import bronze_volume

pytestmark = pytest.mark.unit


def _write(path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_measure_missing_root_returns_zero_report(tmp_path):
    report = bronze_volume.measure(tmp_path / "does-not-exist")

    assert report["sources"] == {}
    assert report["total"]["datasets"] == 0
    assert report["total"]["artifacts"] == 0
    assert report["total"]["observations"] == 0
    assert report["total"]["skipped_artifacts"] == 0


def test_measure_counts_tsv_and_worldbank_json(tmp_path):
    root = tmp_path / "bronze"
    _write(
        root / "stats/eurostat/rail_pa_total/ingest_date=2026-06-24/rail_pa_total.tsv.gz",
        gzip.compress(b"freq,unit,geo\\TIME_PERIOD\t2020\t2021\nA,MIO_PKM,HU\t1\t2\n"),
    )
    _write(
        root / "stats/worldbank/NY.GDP.MKTP.CD/ingest_date=2026-06-24/NY.GDP.MKTP.CD.json",
        json.dumps([{"page": 1}, [{"date": "2021"}, {"date": "2020"}]]).encode("utf-8"),
    )

    report = bronze_volume.measure(root)

    assert report["sources"]["eurostat"]["datasets"] == 1
    assert report["sources"]["eurostat"]["data_rows"] == 1
    assert report["sources"]["eurostat"]["observations"] == 2
    assert report["sources"]["worldbank"]["datasets"] == 1
    assert report["sources"]["worldbank"]["observations"] == 2
    assert report["total"]["datasets"] == 2


def test_measure_records_skipped_artifacts(tmp_path):
    root = tmp_path / "bronze"
    _write(
        root / "stats/eurostat/huge/ingest_date=2026-06-24/huge.tsv",
        b"freq,unit,geo\\TIME_PERIOD\t2021\nA,NR,HU\t1\n",
    )

    report = bronze_volume.measure(root, max_file_bytes=1)

    assert report["sources"]["eurostat"]["skipped_artifacts"] == 1
    assert report["total"]["skipped_artifacts"] == 1
    assert report["total"]["artifacts"] == 0
