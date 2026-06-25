import json

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from railway_lakehouse.silver import persist
from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.news.cache import (
    FileSystemCache,
    extract_cache_key,
    model_digest_key,
)
from railway_lakehouse.silver.schema import ArticleRecord, NewsFeature, validate_news_feature

pytestmark = pytest.mark.unit

OLD_NEWS_FIELDS = [
    "article_id",
    "source",
    "url",
    "published_date",
    "language",
    "is_rail_related",
    "country",
    "event_type",
    "operators",
    "rail_lines",
    "monetary_amount_eur",
    "monetary_raw",
    "summary_en",
    "sentiment",
    "confidence",
]

WIDE_NEWS_FIELDS = [
    "language_detected_code",
    "language_confidence",
    "sentiment_label",
    "sentiment_score",
    "sentiment_confidence",
    "is_rail_related_confidence",
    "event_type_confidence",
    "summary_en_source",
    "operators_ner_model",
    "operators_confidence",
    "rail_lines_ner_model",
    "rail_lines_confidence",
    "monetary_raw_parsed_eur",
    "monetary_confidence",
    "gkg_themes",
    "gkg_persons",
    "gkg_organizations",
    "gkg_locations",
    "gkg_tone",
    "gkg_emotions",
    "gkg_tone_source",
    "text_embedding_model",
    "text_embedding",
    "cluster_id",
    "cross_lingual_dedup_id",
    "extraction_timestamp_utc",
    "extraction_model_digest",
    "confidence_schema_version",
    "is_duplicate",
]


def _feature(**overrides):
    data = {
        "article_id": "a1",
        "source": "rss",
        "url": "https://example.test/a1",
        "published_date": "2026-06-22",
        "language": "hu",
        "is_rail_related": True,
        "country": "HU",
        "event_type": "investment",
        "operators": ["MÁV"],
        "rail_lines": ["Budapest-Wien"],
        "monetary_amount_eur": 12.5,
        "monetary_raw": "12.5 EUR",
        "summary_en": "Railway investment was announced.",
        "sentiment": "positive",
        "confidence": 0.9,
    }
    data.update(overrides)
    return NewsFeature(**data)


def _valid_raw():
    return {
        "is_rail_related": True,
        "country": "HU",
        "event_type": "investment",
        "operators": ["MÁV"],
        "rail_lines": ["Line 1"],
        "monetary_amount_eur": None,
        "monetary_raw": None,
        "summary_en": "Railway investment was announced.",
        "sentiment": "positive",
        "language": "hu",
        "confidence": 0.8,
    }


def test_news_feature_wide_schema_is_backward_compatible():
    fields = list(NewsFeature.__dataclass_fields__)

    assert fields[: len(OLD_NEWS_FIELDS)] == OLD_NEWS_FIELDS
    assert len(fields) >= 28
    for field in WIDE_NEWS_FIELDS:
        assert field in fields

    legacy = NewsFeature(
        article_id="legacy",
        source="rss",
        url="https://example.test/legacy",
        published_date="2026-06-22",
        language="hu",
        is_rail_related=True,
        country="HU",
        event_type="investment",
    )
    row = legacy.to_row()
    assert row["language_detected_code"] is None
    assert row["gkg_themes"] is None
    assert row["text_embedding"] is None
    assert row["confidence_schema_version"] == "1.0"
    assert row["is_duplicate"] is None

    wide = _feature(language_detected_code="hu", sentiment_score=0.6)
    assert wide.confidence_schema_version == "1.0"
    assert wide.to_row()["sentiment_score"] == 0.6


def test_validate_news_feature_coerces_wide_fields():
    raw = _valid_raw() | {
        "language_detected_code": "ZZ",
        "language_confidence": 2.0,
        "sentiment_label": "bad",
        "sentiment_score": -2.5,
        "sentiment_confidence": -1.0,
        "is_rail_related_confidence": "0.75",
        "event_type_confidence": 1.8,
        "operators_confidence": 0.25,
        "rail_lines_confidence": "bad",
        "monetary_raw_parsed_eur": "42.5",
        "monetary_confidence": 1.2,
        "gkg_themes": "",
        "gkg_persons": " ",
        "gkg_organizations": "RailCargo",
        "gkg_locations": "",
        "gkg_tone": 150,
        "gkg_emotions": "",
        "gkg_tone_source": "unknown",
        "text_embedding": ["1.0", 2],
        "is_duplicate": "true",
    }

    feature = validate_news_feature(
        raw,
        article_id="a1",
        source="rss",
        url="https://example.test/a1",
        published_date="2026-06-22",
        event_types=["investment", "other"],
        operators_allowed=["MÁV", "other"],
    )

    assert feature.language_detected_code is None
    assert feature.language_confidence == 1.0
    assert feature.sentiment_label is None
    assert feature.sentiment_score == -1.0
    assert feature.sentiment_confidence == 0.0
    assert feature.is_rail_related_confidence == 0.75
    assert feature.event_type_confidence == 1.0
    assert feature.operators_confidence == 0.25
    assert feature.rail_lines_confidence is None
    assert feature.monetary_raw_parsed_eur == 42.5
    assert feature.monetary_confidence == 1.0
    assert feature.gkg_themes is None
    assert feature.gkg_persons is None
    assert feature.gkg_organizations == "RailCargo"
    assert feature.gkg_locations is None
    assert feature.gkg_tone == 100.0
    assert feature.gkg_emotions is None
    assert feature.gkg_tone_source is None
    assert feature.text_embedding == [1.0, 2.0]
    assert feature.is_duplicate is True

    valid_language = validate_news_feature(
        _valid_raw() | {"language_detected_code": "EN"},
        article_id="a2",
        source="rss",
        url="https://example.test/a2",
        published_date="2026-06-22",
        event_types=["investment", "other"],
        operators_allowed=["MÁV", "other"],
    )
    assert valid_language.language_detected_code == "en"


def test_extract_cache_key_is_deterministic_and_content_sensitive():
    article = ArticleRecord(
        article_id="a1",
        source="rss",
        title="Rail upgrade",
        url="https://example.test/a1",
        published_date="2026-06-22",
        body="Body",
    )

    key_a = extract_cache_key(article)
    key_b = extract_cache_key(article.to_row())
    changed = extract_cache_key(article.to_row() | {"title": "Rail upgrade changed"})

    assert key_a == key_b
    assert len(key_a) == 64
    assert changed != key_a


def test_model_digest_key_includes_current_ollama_model(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    digest_a = model_digest_key()
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:7b")
    digest_b = model_digest_key()

    assert len(digest_a) == 64
    assert digest_a != digest_b


def test_filesystem_cache_round_trips_feature_and_manifest(tmp_path):
    cache = FileSystemCache(tmp_path / ".news_extraction_cache")
    feature = _feature(
        extraction_model_digest="digest-a",
        language_detected_code="hu",
        text_embedding=[1.0, 2.5],
    )

    assert cache.get("cache-key", "digest-a") is None
    cache.put("cache-key", "digest-a", feature)
    loaded = cache.get("cache-key", "digest-a")

    assert loaded.to_row() == feature.to_row()
    manifest_path = tmp_path / ".news_extraction_cache" / "digest-a" / "_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["model_digest"] == "digest-a"
    assert manifest["cached_count"] == 1
    assert manifest["hits"] == 1
    assert manifest["misses"] == 1
    assert cache.cache_stats()["hits"] == 1


def test_extract_article_cached_uses_cache_and_model_digest(monkeypatch, tmp_path):
    cache = FileSystemCache(tmp_path / ".news_extraction_cache")
    article = ArticleRecord(
        article_id="a1",
        source="rss",
        title="Rail upgrade",
        url="https://example.test/a1",
        published_date="2026-06-22",
        body="Railway expansion announced.",
    )
    calls = {"count": 0}

    def fake_generate_json(prompt, *, schema=None, system=None):
        calls["count"] += 1
        assert "Article title: Rail upgrade" in prompt
        return _valid_raw()

    monkeypatch.setattr(news_extract, "generate_json", fake_generate_json)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")

    first = news_extract.extract_article_cached(article, cache)
    second = news_extract.extract_article_cached(article, cache)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:7b")
    third = news_extract.extract_article_cached(article, cache)

    assert first.to_row() == second.to_row()
    assert first.extraction_model_digest == second.extraction_model_digest
    assert third.extraction_model_digest != first.extraction_model_digest
    assert calls["count"] == 2


def test_gdelt_passthrough_cached_populates_gkg_without_llm(monkeypatch, tmp_path):
    cache = FileSystemCache(tmp_path / ".news_extraction_cache")
    monkeypatch.setattr(
        news_extract,
        "generate_json",
        lambda *args, **kwargs: pytest.fail("GDELT passthrough must not call Ollama"),
    )

    feature = news_extract.gdelt_passthrough_cached(
        {
            "article_id": "g1",
            "url": "https://example.test/g1",
            "published_date": "2026-06-22",
            "gkg_tone": 2.5,
            "gkg_themes": "ECON_TRADE_AGREEMENT;LABOR_STRIKE",
            "gkg_persons": "Person A",
            "gkg_organizations": "RailCargo",
            "gkg_locations": "Austria",
            "gkg_emotions": "FEAR",
        },
        cache,
    )
    cached = news_extract.gdelt_passthrough_cached(
        {
            "article_id": "g1",
            "url": "https://example.test/g1",
            "published_date": "2026-06-22",
            "gkg_tone": 2.5,
            "gkg_themes": "ECON_TRADE_AGREEMENT;LABOR_STRIKE",
            "gkg_persons": "Person A",
            "gkg_organizations": "RailCargo",
            "gkg_locations": "Austria",
            "gkg_emotions": "FEAR",
        },
        cache,
    )

    assert cached.to_row() == feature.to_row()
    assert feature.source == "gdelt"
    assert feature.country == "AT"
    assert feature.sentiment == "positive"
    assert feature.sentiment_label == "positive"
    assert feature.gkg_themes == "ECON_TRADE_AGREEMENT;LABOR_STRIKE"
    assert feature.gkg_tone_source == "gdelt_gkg"
    assert feature.extraction_model_digest == news_extract.GDELT_PASSTHROUGH_DIGEST


def test_gdelt_passthrough_preserves_zero_tone(monkeypatch, tmp_path):
    cache = FileSystemCache(tmp_path / ".news_extraction_cache")
    monkeypatch.setattr(
        news_extract,
        "generate_json",
        lambda *args, **kwargs: pytest.fail("GDELT passthrough must not call Ollama"),
    )

    feature = news_extract.gdelt_passthrough_cached(
        {
            "article_id": "g-zero",
            "url": "https://example.test/g-zero",
            "published_date": "2026-06-22",
            "gkg_tone": 0,
            "tone": 9.0,
            "gkg_themes": "RAIL",
        },
        cache,
    )

    assert feature.gkg_tone == 0.0
    assert feature.sentiment == "neutral"
    assert feature.sentiment_label == "neutral"


def test_gdelt_passthrough_cache_key_includes_gkg_annotations(tmp_path):
    cache = FileSystemCache(tmp_path / ".news_extraction_cache")
    base = {
        "article_id": "gdelt-cache-key",
        "source": "gdelt",
        "url": "https://example.test/gdelt-cache-key",
        "title": "Rail update",
        "body": "Rail service update.",
        "published_date": "2026-06-25",
        "language": "eng",
        "sourcecountry": "HU",
        "gkg_tone": 2.5,
        "gkg_themes": "TRANSPORT;RAIL",
        "gkg_persons": "Person A",
        "gkg_organizations": "MAV",
        "gkg_locations": "Hungary",
        "gkg_emotions": "JOY",
    }

    first = news_extract.gdelt_passthrough_cached(base, cache)
    second = news_extract.gdelt_passthrough_cached(
        {
            **base,
            "gkg_tone": -4.0,
            "gkg_themes": "TRANSPORT;RAIL;LABOR_STRIKE",
        },
        cache,
    )

    assert first.gkg_tone == 2.5
    assert first.gkg_themes == "TRANSPORT;RAIL"
    assert second.gkg_tone == -4.0
    assert second.sentiment == "negative"
    assert second.gkg_themes == "TRANSPORT;RAIL;LABOR_STRIKE"


def test_extract_batch_returns_successes_and_failures(monkeypatch, tmp_path, caplog):
    cache = FileSystemCache(tmp_path / ".news_extraction_cache")
    monkeypatch.setattr(news_extract, "generate_json", lambda *args, **kwargs: _valid_raw())
    embedding_calls = {"rows": 0}

    def fake_compute_embeddings(rows, *, use_model=True):
        embedding_calls["rows"] += len(rows)
        return rows

    monkeypatch.setattr(news_extract, "compute_embeddings", fake_compute_embeddings)

    successes, failures = news_extract.extract_batch(
        [
            {
                "article_id": "ok",
                "source": "rss",
                "title": "Rail upgrade",
                "url": "https://example.test/ok",
                "body": "Body",
                "published_date": "2026-06-22",
            },
            {
                "article_id": "missing-title",
                "source": "rss",
                "title": "",
                "url": "https://example.test/missing",
                "body": "Body",
                "published_date": "2026-06-22",
            },
            {
                "article_id": "bad-url",
                "source": "rss",
                "title": "Rail upgrade",
                "url": "not a url",
                "body": "Body",
                "published_date": "2026-06-22",
            },
        ],
        cache=cache,
    )

    assert len(successes) == 1
    assert len(failures) == 2
    assert {failure.article_id for failure in failures} == {"missing-title", "bad-url"}
    assert "news extraction failed" in caplog.text
    assert embedding_calls["rows"] == 1


def test_news_feature_wide_parquet_round_trip(tmp_path):
    feature = _feature(
        language_detected_code="hu",
        language_confidence=0.98,
        sentiment_label="positive",
        sentiment_score=0.6,
        sentiment_confidence=0.88,
        gkg_themes="RAIL;ECON",
        gkg_tone=2.0,
        text_embedding_model="multilingual_e5_base",
        text_embedding=[0.1, 0.2, 0.3],
        cluster_id="cluster_001",
        cross_lingual_dedup_id="dedup_001",
        is_duplicate=True,
        extraction_timestamp_utc="2026-06-25T00:00:00Z",
        extraction_model_digest="digest-a",
    )

    path = persist.persist_news([feature], tmp_path, ingest_date="2026-06-25")
    loaded = persist.load_news(tmp_path, ingest_date="2026-06-25")
    schema = pq.read_schema(path)

    assert list(loaded.columns) == persist.NEWS_FEATURE_COLUMNS
    assert set(WIDE_NEWS_FIELDS).issubset(schema.names)
    assert schema.field("text_embedding").type == pa.list_(pa.float32())
    assert schema.field("is_duplicate").type == pa.bool_()
    row = loaded.iloc[0]
    assert row["article_id"] == feature.article_id
    assert row["language_detected_code"] == "hu"
    assert row["gkg_themes"] == "RAIL;ECON"
    assert list(row["text_embedding"]) == pytest.approx([0.1, 0.2, 0.3])
    assert bool(row["is_duplicate"]) is True


def test_load_news_backfills_wide_columns_for_legacy_parquet(tmp_path):
    root = tmp_path / "silver"
    path = persist.silver_table_path(root, "news", "news_feature", "2026-06-24")
    path.parent.mkdir(parents=True, exist_ok=True)
    legacy = pd.DataFrame([_feature().to_row()]).reindex(columns=OLD_NEWS_FIELDS)
    pq.write_table(pa.Table.from_pandas(legacy, preserve_index=False), path)

    loaded = persist.load_news(root, ingest_date="2026-06-24")

    assert list(loaded.columns) == persist.NEWS_FEATURE_COLUMNS
    assert loaded.iloc[0]["article_id"] == "a1"
    assert pd.isna(loaded.iloc[0]["language_detected_code"])
    assert loaded.iloc[0]["confidence_schema_version"] == "1.0"
    assert pd.isna(loaded.iloc[0]["is_duplicate"])
