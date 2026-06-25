import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest


pytestmark = pytest.mark.integration
FIXTURE_BRONZE = Path(__file__).parent / "fixtures" / "bronze"


def test_pipeline_bronze_readers_load_local_fixtures():
    import railway_lakehouse.pipeline as pipeline

    reader = SimpleNamespace(bronze_root=FIXTURE_BRONZE)

    tables = pipeline._read_bronze_eurostat(reader)
    articles = pipeline._read_bronze_news(reader, limit=1)

    assert list(tables) == ["rail_passengers_demo"]
    assert list(tables["rail_passengers_demo"].columns) == [
        "Rail passengers total",
        "2020",
        "2021",
    ]
    assert articles == [
        {
            "article_id": "https://example.test/rail-investment",
            "source": "gdelt",
            "url": "https://example.test/rail-investment",
            "title": "RailCargo investment announced",
            "body": "RailCargo announced a rail investment.",
            "published_date": "2020-04-01",
        }
    ]

def test_pipeline_stats_reader_loads_eurostat_and_worldbank_fixtures():
    import railway_lakehouse.pipeline as pipeline

    reader = SimpleNamespace(bronze_root=FIXTURE_BRONZE)

    frames = pipeline._read_bronze_stats_frames(reader)

    assert {frame["source_system"].iloc[0] for frame in frames if not frame.empty} >= {
        "eurostat",
        "worldbank",
    }

def test_pipeline_news_reader_honors_zero_limit():
    import railway_lakehouse.pipeline as pipeline

    reader = SimpleNamespace(bronze_root=FIXTURE_BRONZE)

    assert pipeline._read_bronze_news(reader, limit=0) == []


def test_pipeline_news_reader_loads_rss_xml_fixtures():
    import railway_lakehouse.pipeline as pipeline

    reader = SimpleNamespace(bronze_root=FIXTURE_BRONZE)

    articles = pipeline._read_bronze_news(reader, limit=2)

    assert {
        "article_id": "https://example.test/rss-rail-upgrade",
        "source": "rss",
        "url": "https://example.test/rss-rail-upgrade",
        "title": "RSS rail upgrade announced",
        "body": "Full RSS article text about a railway upgrade.",
        "published_date": "2026-06-22",
    } in articles


def test_pipeline_fixture_e2e_reads_bronze_and_writes_gold(
    tmp_path,
    monkeypatch,
):
    import railway_lakehouse.pipeline as pipeline

    out_path = tmp_path / "gold" / "railway_ml.parquet"
    crosswalk_path = tmp_path / "crosswalk.json"
    counts_path = tmp_path / "gold" / "counts.json"
    monkeypatch.setattr(pipeline, "health_check", lambda: True)

    def fake_generate_json(prompt, *, schema=None, system=None):
        if prompt == 'Return {"ok": true}.':
            return {"ok": True}
        assert "RailCargo investment announced" in prompt
        assert schema is not None
        assert system is not None
        return {
            "is_rail_related": True,
            "country": "HU",
            "event_type": "investment",
            "operators": ["RailCargo"],
            "rail_lines": [],
            "monetary_amount_eur": 1000,
            "summary_en": "A railway investment was announced.",
            "sentiment": "positive",
            "language": "en",
            "confidence": 0.9,
        }

    monkeypatch.setattr(pipeline.news_extract, "generate_json", fake_generate_json)

    returned = pipeline.main(
        [
            "--bronze-root",
            str(FIXTURE_BRONZE),
            "--news",
            "1",
            "--out",
            str(out_path),
            "--crosswalk-path",
            str(crosswalk_path),
            "--news-cache-root",
            str(tmp_path / ".news_extraction_cache"),
            "--news-artifact-root",
            str(tmp_path / "output" / "silver"),
            "--counts-out",
            str(counts_path),
        ]
    )

    assert returned == str(out_path)
    assert crosswalk_path.exists()
    assert counts_path.exists()
    gold = pd.read_parquet(out_path)
    counts = json.loads(counts_path.read_text(encoding="utf-8"))
    assert counts["path"] == out_path.as_posix()
    assert counts["rows"] == len(gold)
    assert counts["columns"] == len(gold.columns)
    assert counts["contains_AT"] is True
    assert counts["contains_HU"] is True
    assert set(gold["geo"]) == {"AT", "HU"}
    hu_2020 = gold[(gold["geo"] == "HU") & (gold["year"] == 2020)].iloc[0]
    at_2020 = gold[(gold["geo"] == "AT") & (gold["year"] == 2020)].iloc[0]
    assert hu_2020["rail_passengers"] == 100
    assert hu_2020["news_article_count"] == 1
    assert hu_2020["news_n_investment"] == 1
    assert hu_2020["news_total_investment_eur"] == 1000
    assert at_2020["news_article_count"] == 0


def test_pipeline_news_extraction_uses_filesystem_cache_between_runs(
    tmp_path,
    monkeypatch,
):
    import railway_lakehouse.pipeline as pipeline
    from railway_lakehouse.silver.news.cache import model_digest_key

    out_path = tmp_path / "gold" / "railway_ml.parquet"
    cache_root = tmp_path / ".news_extraction_cache"
    crosswalk_path = tmp_path / "crosswalk.json"
    calls = {"count": 0}

    monkeypatch.setattr(pipeline, "health_check", lambda: True)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")

    class FakeLifecycle:
        def warm_up(self):
            return {"status": "ok", "latency_seconds": 0.0}

    monkeypatch.setattr(pipeline.news_extract, "OllamaLifecycle", lambda: FakeLifecycle())

    def fake_generate_json(prompt, *, schema=None, system=None):
        calls["count"] += 1
        return {
            "is_rail_related": True,
            "country": "HU",
            "event_type": "investment",
            "operators": ["RailCargo"],
            "rail_lines": [],
            "monetary_amount_eur": 1000,
            "summary_en": "A railway investment was announced.",
            "sentiment": "positive",
            "language": "en",
            "confidence": 0.9,
        }

    monkeypatch.setattr(pipeline.news_extract, "generate_json", fake_generate_json)

    pipeline.run_pipeline(
        bronze_root=str(FIXTURE_BRONZE),
        news=2,
        out=str(out_path),
        crosswalk_path=str(crosswalk_path),
        news_cache_root=str(cache_root),
        news_artifact_root=str(tmp_path / "output" / "silver"),
    )
    first_call_count = calls["count"]

    pipeline.run_pipeline(
        bronze_root=str(FIXTURE_BRONZE),
        news=2,
        out=str(out_path),
        crosswalk_path=str(crosswalk_path),
        news_cache_root=str(cache_root),
        news_artifact_root=str(tmp_path / "output" / "silver"),
    )

    manifest = json.loads(
        (cache_root / model_digest_key() / "_manifest.json").read_text(encoding="utf-8")
    )
    assert first_call_count > 0
    assert calls["count"] == first_call_count
    assert manifest["hits"] >= first_call_count


def test_pipeline_preserves_gdelt_gkg_fields_for_passthrough(
    tmp_path,
    monkeypatch,
):
    import railway_lakehouse.pipeline as pipeline
    from railway_lakehouse.silver import persist
    from railway_lakehouse.silver.news import extract as news_extract
    from railway_lakehouse.silver.news.cache import FileSystemCache

    bronze_root = tmp_path / "bronze"
    gdelt_path = (
        bronze_root
        / "news"
        / "gdelt"
        / "HU"
        / "ingest_date=2026-06-25"
        / "gdelt_gkg.json"
    )
    gdelt_path.parent.mkdir(parents=True)
    gdelt_path.write_text(
        json.dumps(
            {
                "articles": [
                    {
                        "url": "https://example.test/gdelt-gkg",
                        "title": "Rail strike update",
                        "description": "Rail service update.",
                        "seendate": "20260625000000",
                        "language": "eng",
                        "sourcecountry": "HU",
                        "gkg_tone": 0,
                        "gkg_themes": "TRANSPORT;RAIL",
                        "gkg_persons": "Person A",
                        "gkg_organizations": "MAV",
                        "gkg_locations": "Hungary",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        news_extract,
        "generate_json",
        lambda *args, **kwargs: pytest.fail("GDELT GKG passthrough must not call Ollama"),
    )

    articles = pipeline._read_bronze_news(SimpleNamespace(bronze_root=bronze_root), limit=1)
    successes, failures = news_extract.extract_batch(
        articles,
        cache=FileSystemCache(tmp_path / ".news_extraction_cache"),
    )
    persist.persist_news(successes, tmp_path / "silver", ingest_date="2026-06-25")
    loaded = persist.load_news(tmp_path / "silver", ingest_date="2026-06-25")

    assert not failures
    assert articles[0]["gkg_tone"] == 0
    assert loaded.iloc[0]["extraction_model_digest"] == "gdelt_gkg_passthrough"
    assert loaded.iloc[0]["gkg_tone"] == 0.0
    assert loaded.iloc[0]["sentiment"] == "neutral"
    assert loaded.iloc[0]["gkg_themes"] == "TRANSPORT;RAIL"


def test_pipeline_news_entrypoint_writes_gap050_manifest_and_failure_sidecar(
    tmp_path,
    monkeypatch,
):
    import railway_lakehouse.pipeline as pipeline
    from railway_lakehouse.silver.news import extract as news_extract

    bronze_root = tmp_path / "bronze"
    news_path = (
        bronze_root
        / "news"
        / "rss"
        / "fixture"
        / "ingest_date=2026-06-25"
        / "articles.json"
    )
    news_path.parent.mkdir(parents=True)
    news_path.write_text(
        json.dumps(
            {
                "articles": [
                    {
                        "article_id": "pipeline-ok",
                        "url": "https://example.test/pipeline-ok",
                        "title": "Rail upgrade",
                        "body": "Railway expansion announced.",
                        "published_date": "2026-06-25",
                    },
                    {
                        "article_id": "pipeline-missing-title",
                        "url": "https://example.test/pipeline-missing-title",
                        "title": "",
                        "body": "Body",
                        "published_date": "2026-06-25",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    class FakeLifecycle:
        warmups = 0

        def warm_up(self):
            self.warmups += 1
            return {"status": "ok", "latency_seconds": 0.0}

    lifecycle = FakeLifecycle()
    artifact_root = tmp_path / "output" / "silver"

    monkeypatch.setattr(pipeline, "health_check", lambda: True)
    monkeypatch.setattr(news_extract, "OllamaLifecycle", lambda: lifecycle)
    monkeypatch.setattr(
        news_extract,
        "generate_json",
        lambda *args, **kwargs: {
            "is_rail_related": True,
            "country": "HU",
            "event_type": "investment",
            "operators": [],
            "rail_lines": [],
            "summary_en": "Railway expansion was announced.",
            "sentiment": "neutral",
            "language": "en",
            "confidence": 0.9,
        },
    )

    pipeline.run_pipeline(
        bronze_root=str(bronze_root),
        news=2,
        out=str(tmp_path / "gold" / "railway_ml.parquet"),
        news_cache_root=str(tmp_path / ".news_extraction_cache"),
        news_artifact_root=str(artifact_root),
        news_ingest_date="2026-06-25",
    )

    manifest_path = (
        artifact_root
        / "news"
        / "news_extraction_runs"
        / "ingest_date=2026-06-25"
        / "manifest.json"
    )
    failure_path = (
        artifact_root
        / "news"
        / "news_extraction_failures"
        / "ingest_date=2026-06-25"
        / "failures.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sidecar = json.loads(failure_path.read_text(encoding="utf-8"))

    assert lifecycle.warmups == 1
    assert manifest["counts"]["processed"] == 2
    assert manifest["counts"]["succeeded"] == 1
    assert manifest["counts"]["failed"] == 1
    assert sidecar["failure_count"] == 1
    assert sidecar["failures"][0]["article_id"] == "pipeline-missing-title"


def test_pipeline_missing_bronze_root_raises_before_gold_write(tmp_path):
    import railway_lakehouse.pipeline as pipeline

    missing_root = tmp_path / "does-not-exist" / "bronze"
    out_path = tmp_path / "gold" / "railway_ml.parquet"

    with pytest.raises(
        FileNotFoundError,
        match=r"--bronze-root.*does-not-exist/bronze.*live_check",
    ):
        pipeline.run_pipeline(
            bronze_root=str(missing_root),
            news=0,
            out=str(out_path),
            skip_news_extraction=True,
        )

    assert not out_path.exists()


def test_pipeline_empty_local_bronze_root_raises_before_gold_write(tmp_path):
    import railway_lakehouse.pipeline as pipeline

    bronze_root = tmp_path / "empty" / "bronze"
    bronze_root.mkdir(parents=True)
    out_path = tmp_path / "gold" / "railway_ml.parquet"

    with pytest.raises(
        ValueError,
        match=r"No local Bronze stats frames or news articles.*--bronze-root.*live_check",
    ):
        pipeline.run_pipeline(
            bronze_root=str(bronze_root),
            news=0,
            out=str(out_path),
            skip_news_extraction=True,
        )

    assert not out_path.exists()


def test_live_check_nesting_contract_means_parent_bronze_is_absent(tmp_path):
    from railway_lakehouse.bronze.lander import RawArtifact
    from railway_lakehouse.bronze.live_check import SourceResult, run_live_check

    out = tmp_path / "local-stats-bronze"
    out.mkdir()
    (out / "manifest.json").write_text("{}", encoding="utf-8")
    fixed_now = datetime(2026, 6, 21, 12, 30, tzinfo=timezone.utc)

    def fake_collector(*, lander, max_artifacts, timeout_seconds):
        content = b'[{"page": 1}, []]'
        lander.land(
            RawArtifact(
                domain="stats",
                source="worldbank",
                dataset_id="IS.RRS.TOTL.KM",
                filename="IS.RRS.TOTL.KM.json",
                content=content,
                source_url="https://example.test/worldbank",
                content_type="application/json",
                http_status=200,
            )
        )
        return SourceResult(
            source="worldbank",
            status="passed",
            artifact_count=1,
            byte_count=len(content),
        )

    manifest_path = run_live_check(
        sources=["worldbank"],
        out=out,
        max_artifacts=1,
        timeout_seconds=60,
        collectors={"worldbank": fake_collector},
        clock=lambda: fixed_now,
    )

    run_dir = out / "live-check-20260621-123000"
    assert manifest_path == run_dir / "manifest.json"
    assert not (out / "bronze").exists()
    assert (
        run_dir
        / "bronze"
        / "stats"
        / "worldbank"
        / "IS.RRS.TOTL.KM"
        / "ingest_date=2026-06-21"
        / "IS.RRS.TOTL.KM.json"
    ).exists()


def test_pipeline_article_normalization_handles_missing_body_dates_and_fallback_ids():
    import railway_lakehouse.pipeline as pipeline

    article = pipeline._normalize_article(
        {"title": "Only a title", "published_date": "April 1, 2020"},
        source="rss",
        path=Path("news") / "rss" / "demo.json",
        index=2,
    )

    assert article == {
        "article_id": "news/rss/demo.json#2",
        "source": "rss",
        "url": "",
        "title": "Only a title",
        "body": "",
        "published_date": "2020-04-01",
    }


def test_pipeline_bronze_path_errors_include_context():
    import railway_lakehouse.pipeline as pipeline

    with pytest.raises(ValueError, match="stats dataset id"):
        pipeline._dataset_id_from_path(Path("stats") / "eurostat", "eurostat")
