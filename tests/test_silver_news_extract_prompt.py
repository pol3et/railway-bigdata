import json

import pytest

from railway_lakehouse.silver import config
from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.news.cache import FileSystemCache, model_digest_key
from railway_lakehouse.silver.schema import validate_news_feature

pytestmark = pytest.mark.unit


def _article(**overrides):
    data = {
        "article_id": "a1",
        "source": "rss",
        "title": "MAV rail investment",
        "url": "https://example.test/a1",
        "body": "MAV announced a 12 million EUR railway upgrade in Budapest.",
        "published_date": "2026-06-25",
    }
    data.update(overrides)
    return data


def _valid_raw(**overrides):
    data = {
        "is_rail_related": True,
        "country": "HU",
        "event_type": "investment",
        "monetary_amount_eur": 12_000_000,
        "monetary_raw": "12 million EUR",
        "summary_en": "MAV announced a railway upgrade in Budapest.",
        "confidence": 0.88,
    }
    data.update(overrides)
    return data


def test_prompt_builder_uses_narrow_schema_and_snippet_trust():
    prompt = news_extract._build_prompt(
        "MAV fejlesztes",
        "A MAV vasuti fejlesztest jelentett be.",
        source="gdelt",
        is_snippet=True,
    )
    properties = news_extract._JSON_SCHEMA["properties"]

    assert "Article title: MAV fejlesztes" in prompt
    assert "Input trust: snippet_only" in prompt
    assert "Few-shot examples" in prompt
    assert news_extract.PROMPT_VERSION == config.NEWS_EXTRACTION_PROMPT_VERSION
    assert {
        "is_rail_related",
        "country",
        "event_type",
        "summary_en",
        "monetary_raw",
        "monetary_amount_eur",
    }.issubset(properties)
    for llm_out_of_scope in ("sentiment", "language", "operators", "rail_lines", "confidence"):
        assert llm_out_of_scope not in properties
        assert f"- {llm_out_of_scope}" not in prompt


def test_prompt_version_changes_model_digest(monkeypatch):
    monkeypatch.setattr(config, "NEWS_EXTRACTION_PROMPT_VERSION", "gap050-test-a")
    digest_a = model_digest_key()

    monkeypatch.setattr(config, "NEWS_EXTRACTION_PROMPT_VERSION", "gap050-test-b")
    digest_b = model_digest_key()

    assert len(digest_a) == 64
    assert len(digest_b) == 64
    assert digest_a != digest_b


def test_run_extraction_pipeline_retries_and_writes_manifest(monkeypatch, tmp_path):
    calls = []

    def fake_generate_json(prompt, *, schema=None, system=None):
        calls.append({"prompt": prompt, "schema": schema, "system": system})
        if len(calls) == 1:
            return None
        return _valid_raw()

    monkeypatch.setattr(news_extract, "generate_json", fake_generate_json)

    result = news_extract.run_extraction_pipeline(
        [_article()],
        cache=FileSystemCache(tmp_path / ".news_extraction_cache"),
        manifest_path=tmp_path / "manifest.json",
        warm_up=False,
        max_attempts=2,
        retry_backoff_seconds=0,
    )

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert len(calls) == 2
    assert len(result.features) == 1
    assert result.failures == []
    assert result.features[0].extraction_model_digest == manifest["model_digest"]
    assert manifest["prompt_version"] == config.NEWS_EXTRACTION_PROMPT_VERSION
    assert manifest["counts"]["processed"] == 1
    assert manifest["counts"]["llm_attempted"] == 1
    assert manifest["counts"]["retry_attempts"] == 1
    assert manifest["counts"]["failed"] == 0


def test_run_extraction_pipeline_records_raw_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(
        news_extract,
        "generate_json",
        lambda *args, **kwargs: ["not", "an", "object"],
    )

    result = news_extract.run_extraction_pipeline(
        [_article(article_id="bad-json")],
        cache=FileSystemCache(tmp_path / ".news_extraction_cache"),
        warm_up=False,
        max_attempts=1,
        retry_backoff_seconds=0,
    )

    assert result.features == []
    assert len(result.failures) == 1
    failure = result.failures[0]
    assert failure.article_id == "bad-json"
    assert "valid JSON object" in failure.reason
    assert failure.raw == '["not", "an", "object"]'


def test_run_extraction_pipeline_rejects_zero_max_attempts(monkeypatch, tmp_path):
    monkeypatch.setattr(news_extract, "generate_json", lambda *args, **kwargs: _valid_raw())

    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        news_extract.run_extraction_pipeline(
            [_article(article_id="zero-attempts")],
            cache=FileSystemCache(tmp_path / ".news_extraction_cache"),
            warm_up=False,
            max_attempts=0,
            retry_backoff_seconds=0,
        )


def test_validate_news_feature_still_coerces_adversarial_narrow_output():
    feature = validate_news_feature(
        {
            "is_rail_related": True,
            "country": "XX",
            "event_type": "invented",
            "summary_en": "",
            "monetary_amount_eur": "not-money",
            "monetary_raw": "",
            "confidence": 4.0,
        },
        article_id="a1",
        source="rss",
        url="https://example.test/a1",
        published_date="2026-06-25",
        event_types=["investment", "other"],
        operators_allowed=["MAV", "other"],
    )

    assert feature.country is None
    assert feature.event_type == "other"
    assert feature.summary_en is None
    assert feature.monetary_amount_eur is None
    assert feature.monetary_raw is None
    assert feature.confidence == 1.0
