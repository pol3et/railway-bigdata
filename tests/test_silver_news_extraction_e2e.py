from pathlib import Path

import pytest

from railway_lakehouse.silver import persist
from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.news.cache import FileSystemCache
from railway_lakehouse.silver.news.gdelt import parse_gdelt_artlist_json
from railway_lakehouse.silver.news.rss import parse_rss_xml

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent / "fixtures" / "bronze" / "news"


def _raw_feature():
    return {
        "is_rail_related": True,
        "country": "HU",
        "event_type": "investment",
        "operators": ["RailCargo"],
        "rail_lines": [],
        "monetary_amount_eur": None,
        "monetary_raw": None,
        "summary_en": "Railway investment was announced.",
        "sentiment": "positive",
        "language": "en",
        "confidence": 0.9,
    }


def _fixture_records():
    rss_xml = (
        FIXTURES
        / "rss"
        / "hu_telex"
        / "ingest_date=2026-06-22"
        / "hu_telex.xml"
    ).read_text(encoding="utf-8")
    gdelt_json = (
        FIXTURES
        / "gdelt"
        / "HU"
        / "ingest_date=2026-06-22"
        / "gdelt_doc_HU_1w.json"
    ).read_text(encoding="utf-8")
    return parse_rss_xml(rss_xml, source="hu_telex") + parse_gdelt_artlist_json(gdelt_json)


def test_fixture_news_cached_extraction_persist_reload(monkeypatch, tmp_path):
    records = _fixture_records()
    cache = FileSystemCache(tmp_path / ".news_extraction_cache")
    silver_root = tmp_path / "silver"
    calls = {"count": 0}

    def fake_generate_json(prompt, *, schema=None, system=None):
        calls["count"] += 1
        return _raw_feature()

    monkeypatch.setattr(news_extract, "generate_json", fake_generate_json)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")

    first_successes, first_failures = news_extract.extract_batch(
        [record.to_row() for record in records],
        cache=cache,
    )
    persist.persist_news(first_successes, silver_root, ingest_date="2026-06-22")
    first_loaded = persist.load_news(silver_root, ingest_date="2026-06-22")

    assert calls["count"] == len(records)
    assert not first_failures
    assert len(first_loaded) == len(records)
    assert set(persist.NEWS_FEATURE_COLUMNS).issubset(first_loaded.columns)
    assert first_loaded["extraction_model_digest"].notna().all()

    second_successes, second_failures = news_extract.extract_batch(
        [record.to_row() for record in records],
        cache=cache,
    )
    assert calls["count"] == len(records)
    assert not second_failures
    assert [row.to_row() for row in second_successes] == [
        row.to_row() for row in first_successes
    ]

    new_article = {
        "article_id": "new-article",
        "source": "rss",
        "title": "New rail upgrade",
        "url": "https://example.test/new-rail-upgrade",
        "body": "A new rail upgrade was announced.",
        "published_date": "2026-06-23",
    }
    third_successes, third_failures = news_extract.extract_batch(
        [records[0].to_row(), new_article],
        cache=cache,
    )
    persist.persist_news(third_successes, silver_root, ingest_date="2026-06-23")
    third_loaded = persist.load_news(silver_root, ingest_date="2026-06-23")

    assert calls["count"] == len(records) + 1
    assert not third_failures
    assert len(third_loaded) == 2

    _, failures = news_extract.extract_batch(
        [
            {
                "article_id": "bad-url",
                "source": "rss",
                "title": "Malformed source",
                "url": "not a url",
                "body": "Body",
                "published_date": "2026-06-23",
            }
        ],
        cache=cache,
    )
    failure_path = persist.persist_news_failures(
        failures,
        silver_root,
        ingest_date="2026-06-23",
    )

    assert failures
    assert failure_path.name == "failures.json"
    assert failure_path.exists()
