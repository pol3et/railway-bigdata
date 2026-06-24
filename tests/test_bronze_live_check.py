import io
import json
import zipfile
from datetime import datetime, timezone

import pytest

from railway_lakehouse.bronze.lander import RawArtifact
from railway_lakehouse.bronze import live_check
from railway_lakehouse.bronze.sources import eurostat
from railway_lakehouse.bronze.live_check import (
    collect_eurostat,
    collect_ksh,
    collect_rss,
    collect_uic,
    collect_worldbank,
    LocalBronzeLander,
    SourceResult,
    run_live_check,
    write_manifest,
)

pytestmark = pytest.mark.unit


FIXED_NOW = datetime(2026, 6, 21, 12, 30, tzinfo=timezone.utc)


def _xlsx_bytes():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("_rels/.rels", "<Relationships/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")
    return buffer.getvalue()


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


def test_run_live_check_uses_run_subdirectory_when_output_already_has_evidence(tmp_path):
    out = tmp_path / "evidence"
    out.mkdir()
    (out / "manifest.json").write_text("{}", encoding="utf-8")

    def fake_collector(*, lander, max_artifacts, timeout_seconds):
        lander.land(
            RawArtifact(
                domain="news",
                source="rss",
                dataset_id="feed",
                filename="feed.xml",
                content=b"raw",
                source_url="https://example.test/feed",
                http_status=200,
            )
        )
        return SourceResult(source="rss", status="passed", artifact_count=1, byte_count=3)

    manifest_path = run_live_check(
        sources=["rss"],
        out=out,
        collectors={"rss": fake_collector},
        clock=lambda: FIXED_NOW,
    )

    assert manifest_path == out / "live-check-20260621-123000" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["artifacts"][0]["path"].endswith(
        "live-check-20260621-123000/bronze/news/rss/feed/ingest_date=2026-06-21/feed.xml"
    )


def test_run_live_check_validates_all_sources_before_writing(tmp_path):
    calls = []

    def fake_collector(*, lander, max_artifacts, timeout_seconds):
        calls.append("called")
        lander.land(
            RawArtifact(
                domain="news",
                source="rss",
                dataset_id="feed",
                filename="feed.xml",
                content=b"raw",
                source_url="https://example.test/feed",
                http_status=200,
            )
        )
        return SourceResult(source="rss", status="passed", artifact_count=1, byte_count=3)

    with pytest.raises(ValueError, match="unsupported source"):
        run_live_check(
            sources=["rss", "bogus"],
            out=tmp_path,
            collectors={"rss": fake_collector},
            clock=lambda: FIXED_NOW,
        )

    assert calls == []
    assert not (tmp_path / "bronze").exists()
    assert not (tmp_path / "manifest.json").exists()

def test_collect_eurostat_pulls_curated_allowlist(monkeypatch, tmp_path):
    # Collection is driven by the curated allowlist, NOT by broad TOC discovery:
    # a curated dataset lands even though the TOC does not list it, and a random
    # in-TOC dataset that is not on the allowlist is never fetched.
    tsv = b"freq,unit,geo\\TIME_PERIOD\t2020\nA,MIO_TKM,HU\t100\n"
    curated_code = eurostat.EUROSTAT_CURATED_DATASETS[0]  # e.g. rail_pa_total

    class Response:
        def __init__(self, status_code, content, content_type="text/plain"):
            self.status_code = status_code
            self.content = content
            self.headers = {"Content-Type": content_type}

        @property
        def text(self):
            return self.content.decode("utf-8")

    class Session:
        def get(self, url, timeout, headers):
            if "catalogue/toc" in url:
                return Response(200, b'Some unrelated dataset\t"xyz_demo"\t"dataset"\n')
            # serve a valid TSV for any dataset that is actually requested
            return Response(200, tsv, "text/tab-separated-values")

    monkeypatch.setattr(live_check.requests, "Session", Session)
    lander = LocalBronzeLander(tmp_path, run_id="run-001", clock=lambda: FIXED_NOW)

    result = collect_eurostat(
        lander=lander,
        max_artifacts=len(eurostat.EUROSTAT_CURATED_DATASETS),
        timeout_seconds=3,
    )

    landed = {artifact["dataset_id"] for artifact in lander.artifacts}
    assert result.status == "passed"
    assert "_catalogue_toc" in landed
    assert curated_code in landed       # curated allowlist drove the fetch
    assert "xyz_demo" not in landed     # in TOC but not on the allowlist
    assert (
        tmp_path
        / "bronze"
        / "stats"
        / "eurostat"
        / curated_code
        / "ingest_date=2026-06-21"
        / f"{curated_code}.tsv.gz"
    ).exists()


def test_collect_worldbank_lands_valid_series(monkeypatch, tmp_path):
    class Response:
        def __init__(self, payload, status_code=200):
            self.status_code = status_code
            self._payload = payload
            self.content = json.dumps(payload).encode("utf-8")
            self.headers = {"Content-Type": "application/json"}

        def json(self):
            return self._payload

    valid_series = [
        {"page": 1, "total": 1},
        [
            {
                "indicator": {
                    "id": "IS.RRS.TOTL.KM",
                    "value": "Rail lines (total route-km)",
                },
                "countryiso3code": "HUN",
                "date": "2021",
                "value": 7891,
            }
        ],
    ]

    class Session:
        def get(self, url, timeout, headers):
            if "v2/indicator?" in url:
                return Response([{"page": 1}, []])
            if "IS.RRS.TOTL.KM" in url:
                return Response(valid_series)
            raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(live_check.requests, "Session", Session)
    lander = LocalBronzeLander(tmp_path, run_id="run-001", clock=lambda: FIXED_NOW)

    result = collect_worldbank(lander=lander, max_artifacts=1, timeout_seconds=3)

    assert result.status == "passed"
    assert {artifact["dataset_id"] for artifact in lander.artifacts} == {
        "_catalogue_indicators",
        "IS.RRS.TOTL.KM",
    }
    assert (
        tmp_path
        / "bronze"
        / "stats"
        / "worldbank"
        / "IS.RRS.TOTL.KM"
        / "ingest_date=2026-06-21"
        / "IS.RRS.TOTL.KM.json"
    ).exists()

def test_collect_rss_lands_successes_and_records_failures(monkeypatch, tmp_path):
    class Response:
        def __init__(self, status_code, content):
            self.status_code = status_code
            self.content = content
            self.headers = {"Content-Type": "application/rss+xml"}

    class Session:
        def get(self, url, timeout, headers):
            if url.endswith("/ok"):
                return Response(200, b"<rss>ok</rss>")
            return Response(404, b"")

    monkeypatch.setattr(live_check.rss_media, "_all_feeds", lambda: [("ok_feed", "https://example.test/ok", "HU"), ("bad_feed", "https://example.test/bad", "HU")])
    monkeypatch.setattr(live_check.requests, "Session", Session)
    lander = LocalBronzeLander(tmp_path, run_id="run-001", clock=lambda: FIXED_NOW)

    result = collect_rss(lander=lander, max_artifacts=2, timeout_seconds=3)

    assert result.status == "partial"
    assert result.artifact_count == 1
    assert result.http_statuses == [200, 404]
    assert result.failures[0]["dataset_id"] == "bad_feed"
    assert lander.artifacts[0]["dataset_id"] == "ok_feed"


def test_collect_ksh_lands_successes_and_records_failures(monkeypatch, tmp_path):
    class Response:
        def __init__(self, status_code, content):
            self.status_code = status_code
            self.content = content
            self.headers = {"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

    def fake_get(url, timeout, headers):
        if url.endswith("ok.xlsx"):
            return Response(200, _xlsx_bytes())
        return Response(200, b"")

    monkeypatch.setattr(
        live_check.ksh,
        "KSH_RAIL_TABLES",
        [
            live_check.ksh.KshTable("ok_table", "ok", "OK rail table", "rail_feature"),
            live_check.ksh.KshTable("empty_table", "empty", "Empty rail table", "rail_feature"),
        ],
    )
    monkeypatch.setattr(live_check.requests, "get", fake_get)
    lander = LocalBronzeLander(tmp_path, run_id="run-001", clock=lambda: FIXED_NOW)

    result = collect_ksh(lander=lander, max_artifacts=2, timeout_seconds=3)

    assert result.status == "partial"
    assert result.artifact_count == 1
    assert result.http_statuses == [200, 200]
    assert result.failures[0]["dataset_id"] == "empty_table"
    assert lander.artifacts[0]["dataset_id"] == "ok_table"


def test_collect_uic_lands_successes_and_records_failures(monkeypatch, tmp_path):
    class Response:
        def __init__(self, status_code, content, content_type="application/pdf"):
            self.status_code = status_code
            self.content = content
            self.headers = {"Content-Type": content_type}

    resources = [
        live_check.uic.UicResource(
            dataset_id="ok_publication",
            url="https://uic-stats.uic.org/resources/help_resource/?id=ok",
            filename="ok_publication.pdf",
            title="OK publication",
            publication_year=2025,
            feature_hint="rail_network_length_km",
        ),
        live_check.uic.UicResource(
            dataset_id="html_publication",
            url="https://uic-stats.uic.org/resources/help_resource/?id=html",
            filename="html_publication.pdf",
            title="HTML publication",
            publication_year=2025,
            feature_hint="rail_passenger_km",
        ),
    ]

    def fake_get(url, timeout, headers):
        if url.endswith("id=ok"):
            return Response(200, b"%PDF-1.7\nok")
        return Response(200, b"<html>not a pdf</html>", content_type="text/html")

    monkeypatch.setattr(live_check.uic, "UIC_PUBLIC_RESOURCES", resources)
    monkeypatch.setattr(live_check.requests, "get", fake_get)
    lander = LocalBronzeLander(tmp_path, run_id="run-001", clock=lambda: FIXED_NOW)

    result = collect_uic(lander=lander, max_artifacts=2, timeout_seconds=3)

    assert result.status == "partial"
    assert result.artifact_count == 1
    assert result.http_statuses == [200, 200]
    assert result.failures[0]["dataset_id"] == "html_publication"
    assert result.failures[0]["error"] == "non-200, empty, or non-pdf response"
    assert lander.artifacts[0]["dataset_id"] == "ok_publication"


def test_main_returns_nonzero_when_any_selected_source_fails(monkeypatch, tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "artifact_count": 0,
                "byte_count": 0,
                "sources": [{"source": "rss", "status": "failed", "artifact_count": 0, "failures": [{"error": "boom"}]}],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(live_check, "run_live_check", lambda **kwargs: manifest_path)

    assert live_check.main(["--sources", "rss"]) == 1
