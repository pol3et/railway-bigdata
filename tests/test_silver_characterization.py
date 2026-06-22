import pandas as pd
import pytest

from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver import ollama_client
from railway_lakehouse.silver.schema import validate_news_feature
from railway_lakehouse.silver.stats import merge as stats_merge


pytestmark = pytest.mark.unit


def test_read_eurostat_tsv_melts_year_columns_and_extracts_numeric_values():
    raw = pd.DataFrame(
        {
            "freq,unit,geo": ["A,KM,HU", "A,KM,AT"],
            "2020": ["123 b", ":"],
            "2021": ["456.5", "7"],
        }
    )

    long = stats_merge.read_eurostat_tsv(raw, "rail_demo")

    assert set(long.columns) == {
        "geo",
        "year",
        "value",
        "unit",
        "source_dataset",
        "source_column",
    }
    hu_2020 = long[(long["geo"] == "HU") & (long["year"] == 2020)].iloc[0]
    at_2020 = long[(long["geo"] == "AT") & (long["year"] == 2020)].iloc[0]
    assert hu_2020["value"] == 123
    assert pd.isna(at_2020["value"])
    assert hu_2020["source_dataset"] == "rail_demo"


def test_build_crosswalk_maps_english_labels_by_rule_without_llm(tmp_path, monkeypatch):
    monkeypatch.setattr(stats_merge, "CROSSWALK_PATH", str(tmp_path / "crosswalk.json"))

    crosswalk = stats_merge.build_crosswalk(
        ["Rail passengers total", "Unrelated metric"],
        use_llm=False,
    )

    assert crosswalk["Rail passengers total"] == "rail_passengers"
    assert crosswalk["Unrelated metric"] == "unmapped"
    assert (tmp_path / "crosswalk.json").exists()


def test_merge_sources_drops_unmapped_rows_and_keeps_provenance():
    frame = pd.DataFrame(
        [
            {
                "geo": "HU",
                "year": 2020,
                "value": 10.0,
                "unit": "native",
                "source_system": "eurostat",
                "source_dataset": "rail_demo",
                "source_column": "Rail passengers total",
            },
            {
                "geo": "HU",
                "year": 2020,
                "value": 99.0,
                "unit": "native",
                "source_system": "eurostat",
                "source_dataset": "rail_demo",
                "source_column": "Unknown label",
            },
        ]
    )

    merged = stats_merge.merge_sources(
        [frame],
        {
            "Rail passengers total": "rail_passengers",
            "Unknown label": "unmapped",
        },
    )

    assert len(merged) == 1
    row = merged.iloc[0]
    assert row["feature"] == "rail_passengers"
    assert row["source_system"] == "eurostat"
    assert row["source_dataset"] == "rail_demo"
    assert row["source_column"] == "Rail passengers total"


def test_validate_news_feature_coerces_invalid_model_output_safely():
    feature = validate_news_feature(
        {
            "event_type": "invented",
            "operators": ["unknown-operator"],
            "rail_lines": "Line 1",
            "country": "XX",
            "sentiment": "uncertain",
            "confidence": "2.5",
            "is_rail_related": False,
        },
        article_id="a1",
        source="rss",
        url="https://example.test/article",
        published_date="2020-01-02",
        event_types=["investment", "other"],
        operators_allowed=["RailCargo", "other"],
    )

    assert feature.event_type == "other"
    assert feature.operators == ["other"]
    assert feature.rail_lines == ["Line 1"]
    assert feature.country is None
    assert feature.sentiment is None
    assert feature.confidence == 1.0
    assert feature.is_rail_related is False


def test_extract_article_uses_mocked_ollama_output(monkeypatch):
    def fake_generate_json(prompt, *, schema=None, system=None):
        assert "Article title: New rail investment" in prompt
        assert schema is not None
        assert system is not None
        return {
            "is_rail_related": True,
            "country": "AT",
            "event_type": "investment",
            "operators": ["RailCargo"],
            "rail_lines": ["Line 2"],
            "monetary_amount_eur": 1200,
            "summary_en": "A rail investment was announced.",
            "sentiment": "positive",
            "language": "en",
            "confidence": 0.8,
        }

    monkeypatch.setattr(news_extract, "generate_json", fake_generate_json)

    feature = news_extract.extract_article(
        article_id="a2",
        source="rss",
        url="https://example.test/article-2",
        title="New rail investment",
        body="Rail investment body.",
        published_date="2021-03-04",
    )

    assert feature is not None
    assert feature.article_id == "a2"
    assert feature.country == "AT"
    assert feature.event_type == "investment"
    assert feature.operators == ["RailCargo"]
    assert feature.confidence == 0.8


def test_ollama_json_call_uses_chat_schema_and_disables_thinking(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"message": {"content": "{\"ok\": true}"}}

    def fake_post(url, *, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    monkeypatch.setattr(ollama_client.requests, "post", fake_post)
    monkeypatch.setattr(ollama_client, "OLLAMA_MODEL", "qwen3.5:9b-q8_0")
    monkeypatch.setattr(ollama_client, "OLLAMA_THINK", False)

    result = ollama_client.generate_json("Return JSON.", schema=schema, system="Extract only.")

    assert result == {"ok": True}
    assert calls[0]["url"].endswith("/api/chat")
    payload = calls[0]["json"]
    assert payload["model"] == "qwen3.5:9b-q8_0"
    assert payload["messages"] == [
        {"role": "system", "content": "Extract only."},
        {"role": "user", "content": "Return JSON."},
    ]
    assert payload["format"] == schema
    assert payload["think"] is False
    assert payload["options"]["temperature"] == 0.0
    assert payload["options"]["num_ctx"] == ollama_client.OLLAMA_NUM_CTX
    assert payload["options"]["num_predict"] == ollama_client.OLLAMA_NUM_PREDICT


def test_ollama_health_check_requires_exact_tag_for_tagged_model(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"models": [{"name": "qwen3.5:9b-q4_K_M"}]}

    monkeypatch.setattr(ollama_client, "OLLAMA_MODEL", "qwen3.5:9b-q8_0")
    monkeypatch.setattr(ollama_client.requests, "get", lambda *args, **kwargs: FakeResponse())

    assert ollama_client.health_check() is False
