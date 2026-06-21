import json
from datetime import datetime, timezone

import pytest

from railway_lakehouse.bronze.lander import RawArtifact
from railway_lakehouse.bronze.live_check import (
    LocalBronzeLander,
    SourceResult,
    run_live_check,
    write_manifest,
)


pytestmark = pytest.mark.unit


FIXED_NOW = datetime(2026, 6, 21, 12, 30, tzinfo=timezone.utc)


def test_local_lander_writes_raw_file_and_metadata_in_bronze_layout(tmp_path):
    lander = LocalBronzeLander(tmp_path / "evidence", run_id="run-001", clock=lambda: FIXED_NOW)
    artifact = RawArtifact(
        domain="news",
        source="rss",
        dataset_id="hu_telex",
        filename="hu_telex.xml",
        content=b"<rss>raw</rss>",
        source_url="https://example.test/rss",
        content_type="application/rss+xml",
        http_status=200,
        extra={"geo": "HU"},
    )

    record = lander.land(artifact)

    raw_path = tmp_path / "evidence" / "bronze" / "news" / "rss" / "hu_telex" / "ingest_date=2026-06-21" / "hu_telex.xml"
    meta_path = tmp_path / "evidence" / "bronze" / "news" / "rss" / "hu_telex" / "ingest_date=2026-06-21" / "hu_telex.xml.meta.json"
    assert raw_path.read_bytes() == b"<rss>raw</rss>"

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["source_system"] == "rss"
    assert meta["domain"] == "news"
    assert meta["dataset_id"] == "hu_telex"
    assert meta["source_url"] == "https://example.test/rss"
    assert meta["original_filename"] == "hu_telex.xml"
    assert meta["content_type"] == "application/rss+xml"
    assert meta["http_status"] == 200
    assert meta["byte_size"] == len(b"<rss>raw</rss>")
    assert meta["ingest_run_id"] == "run-001"
    assert meta["extra"] == {"geo": "HU"}

    assert record["path"].endswith("bronze/news/rss/hu_telex/ingest_date=2026-06-21/hu_telex.xml")
    assert record["meta_path"].endswith("bronze/news/rss/hu_telex/ingest_date=2026-06-21/hu_telex.xml.meta.json")
    assert record["bytes"] == len(b"<rss>raw</rss>")
    assert record["http_status"] == 200


def test_write_manifest_records_source_status_artifacts_and_failures(tmp_path):
    artifact = {
        "source": "rss",
        "domain": "news",
        "dataset_id": "hu_telex",
        "path": "output/evidence/live-bronze/bronze/news/rss/hu_telex/ingest_date=2026-06-21/hu_telex.xml",
        "meta_path": "output/evidence/live-bronze/bronze/news/rss/hu_telex/ingest_date=2026-06-21/hu_telex.xml.meta.json",
        "bytes": 10,
        "http_status": 200,
    }
    results = [
        SourceResult(
            source="rss",
            status="passed",
            artifact_count=1,
            byte_count=10,
            http_statuses=[200],
            failures=[],
        ),
        SourceResult(
            source="ksh",
            status="failed",
            artifact_count=0,
            byte_count=0,
            http_statuses=[404],
            failures=[{"dataset_id": "ksh_rail_freight", "http_status": 404, "error": "empty or non-200 response"}],
        ),
    ]

    manifest_path = write_manifest(
        tmp_path,
        run_id="live-check-20260621-123000",
        run_timestamp=FIXED_NOW,
        source_results=results,
        artifacts=[artifact],
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == "live-check-20260621-123000"
    assert manifest["timestamp_utc"] == "2026-06-21T12:30:00+00:00"
    assert manifest["artifact_count"] == 1
    assert manifest["byte_count"] == 10
    assert manifest["sources"][0]["source"] == "rss"
    assert manifest["sources"][0]["status"] == "passed"
    assert manifest["sources"][1]["failures"][0]["http_status"] == 404
    assert manifest["artifacts"] == [artifact]


def test_run_live_check_passes_bounded_limit_to_each_selected_collector(tmp_path):
    calls = []

    def fake_collector(*, lander, max_artifacts, timeout_seconds):
        calls.append((max_artifacts, timeout_seconds))
        for idx in range(max_artifacts + 1):
            if idx >= max_artifacts:
                break
            lander.land(
                RawArtifact(
                    domain="news",
                    source="rss",
                    dataset_id=f"feed_{idx}",
                    filename=f"feed_{idx}.xml",
                    content=f"raw-{idx}".encode(),
                    source_url=f"https://example.test/{idx}",
                    http_status=200,
                )
            )
        return SourceResult(
            source="rss",
            status="passed",
            artifact_count=max_artifacts,
            byte_count=sum(len(f"raw-{idx}".encode()) for idx in range(max_artifacts)),
            http_statuses=[200],
            failures=[],
        )

    manifest_path = run_live_check(
        sources=["rss"],
        out=tmp_path,
        max_artifacts=2,
        timeout_seconds=3,
        collectors={"rss": fake_collector},
        clock=lambda: FIXED_NOW,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert calls == [(2, 3)]
    assert manifest["artifact_count"] == 2
    assert len(manifest["artifacts"]) == 2
