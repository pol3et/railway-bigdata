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


def test_pipeline_news_reader_honors_zero_limit():
    import railway_lakehouse.pipeline as pipeline

    reader = SimpleNamespace(bronze_root=FIXTURE_BRONZE)

    assert pipeline._read_bronze_news(reader, limit=0) == []


def test_pipeline_fixture_e2e_reads_bronze_and_writes_gold(
    tmp_path,
    monkeypatch,
):
    import railway_lakehouse.pipeline as pipeline

    out_path = tmp_path / "gold" / "railway_ml.parquet"
    crosswalk_path = tmp_path / "crosswalk.json"
    monkeypatch.setattr(pipeline, "health_check", lambda: True)

    def fake_generate_json(prompt, *, schema=None, system=None):
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
        ]
    )

    assert returned == str(out_path)
    assert crosswalk_path.exists()
    gold = pd.read_parquet(out_path)
    assert set(gold["geo"]) == {"AT", "HU"}
    hu_2020 = gold[(gold["geo"] == "HU") & (gold["year"] == 2020)].iloc[0]
    at_2020 = gold[(gold["geo"] == "AT") & (gold["year"] == 2020)].iloc[0]
    assert hu_2020["rail_passengers"] == 100
    assert hu_2020["news_article_count"] == 1
    assert hu_2020["news_n_investment"] == 1
    assert hu_2020["news_total_investment_eur"] == 1000
    assert at_2020["news_article_count"] == 0


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
