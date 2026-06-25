from importlib import metadata
from pathlib import Path
import tomllib

import pytest

from railway_lakehouse.silver.language_id import identify_language
from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.news.cache import NoOpCache
from railway_lakehouse.silver.schema import validate_news_feature

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]


def _raw_feature(**overrides):
    data = {
        "is_rail_related": True,
        "country": "HU",
        "event_type": "investment",
        "monetary_amount_eur": None,
        "monetary_raw": None,
        "summary_en": "Railway investment was announced.",
        "confidence": 0.9,
    }
    data.update(overrides)
    return data


def test_identify_language_detects_hungarian_german_and_english():
    assert identify_language("Vasúti bővítés Magyarországon") == "hu"
    assert identify_language("Bahnausbau in Österreich") == "de"
    assert identify_language("Railway expansion in Austria") == "en"


def test_identify_language_returns_none_for_empty_or_none_text():
    assert identify_language("") is None
    assert identify_language("   \n\t  ") is None
    assert identify_language(None) is None


def test_extract_article_sets_deterministic_language_without_prompting_llm(monkeypatch):
    calls = []

    def fake_generate_json(prompt, *, schema=None, system=None):
        calls.append({"prompt": prompt, "schema": schema, "system": system})
        assert "language" not in (schema or {}).get("properties", {})
        assert '"language"' not in prompt
        return _raw_feature(country="HU")

    monkeypatch.setattr(news_extract, "generate_json", fake_generate_json)

    feature = news_extract.extract_article(
        article_id="hu-article",
        source="rss",
        url="https://example.test/hu-article",
        title="Vasúti bővítés Magyarországon",
        body="A MÁV új vasúti fejlesztést jelentett be Budapesten.",
        published_date="2026-06-25",
    )

    assert len(calls) == 1
    assert feature.language == "hu"
    assert feature.language_detected_code == "hu"


def test_extract_article_succeeds_when_language_identifier_returns_none(monkeypatch):
    monkeypatch.setattr(news_extract, "identify_language", lambda text: None)
    monkeypatch.setattr(news_extract, "generate_json", lambda *args, **kwargs: _raw_feature())

    feature = news_extract.extract_article(
        article_id="unknown-language",
        source="rss",
        url="https://example.test/unknown-language",
        title="12345",
        body="67890",
        published_date="2026-06-25",
    )

    assert feature.language is None
    assert feature.language_detected_code is None


def test_gdelt_passthrough_sets_deterministic_language_without_llm(monkeypatch):
    monkeypatch.setattr(
        news_extract,
        "generate_json",
        lambda *args, **kwargs: pytest.fail("GDELT passthrough must not call Ollama"),
    )

    feature = news_extract.gdelt_passthrough_cached(
        {
            "article_id": "gdelt-de",
            "url": "https://example.test/gdelt-de",
            "published_date": "2026-06-25",
            "title": "Bahnausbau in Österreich",
            "body": "Die ÖBB kündigt neue Investitionen in die Bahn an.",
            "gkg_tone": 0,
            "gkg_themes": "RAIL;TRANSPORT",
            "gkg_locations": "Austria",
        },
        NoOpCache(),
    )

    assert feature.language == "de"
    assert feature.language_detected_code == "de"


def test_validate_news_feature_prioritizes_explicit_language_over_raw_output():
    feature = validate_news_feature(
        _raw_feature(language="en", language_detected_code="en"),
        article_id="a1",
        source="rss",
        url="https://example.test/a1",
        published_date="2026-06-25",
        language="hu",
        event_types=["investment", "other"],
        operators_allowed=["MAV", "other"],
    )

    assert feature.language == "hu"
    assert feature.language_detected_code == "hu"


def test_lingua_dependency_matches_project_pin():
    with (ROOT / "pyproject.toml").open("rb") as fh:
        dependencies = tomllib.load(fh)["project"]["dependencies"]

    pin = next(
        dependency
        for dependency in dependencies
        if dependency.startswith("lingua-language-detector==")
    )
    expected_version = pin.split("==", 1)[1]

    assert metadata.version("lingua-language-detector") == expected_version
