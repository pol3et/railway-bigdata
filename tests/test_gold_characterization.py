import pandas as pd
import pytest

from railway_lakehouse.gold import build as gold_build


pytestmark = pytest.mark.unit


def _stats_rows():
    return pd.DataFrame(
        [
            {
                "geo": "HU",
                "year": 2020,
                "feature": "rail_passengers",
                "value": 10.0,
                "unit": "native",
                "source_system": "worldbank",
                "source_dataset": "wb",
                "source_column": "Passengers",
            },
            {
                "geo": "HU",
                "year": 2020,
                "feature": "rail_passengers",
                "value": 20.0,
                "unit": "native",
                "source_system": "eurostat",
                "source_dataset": "estat",
                "source_column": "Passengers",
            },
            {
                "geo": "AT",
                "year": 2020,
                "feature": "rail_passengers",
                "value": 30.0,
                "unit": "native",
                "source_system": "eurostat",
                "source_dataset": "estat",
                "source_column": "Passengers",
            },
        ]
    )


def test_resolve_stat_conflicts_honors_source_priority():
    resolved = gold_build.resolve_stat_conflicts(_stats_rows())

    hu = resolved[(resolved["geo"] == "HU") & (resolved["year"] == 2020)].iloc[0]
    assert hu["source_system"] == "eurostat"
    assert hu["value"] == 20.0


def test_pivot_stats_produces_geo_year_rows():
    wide = gold_build.pivot_stats(_stats_rows())

    assert list(wide.columns) == ["geo", "year", "rail_passengers"]
    assert set(wide["geo"]) == {"HU", "AT"}
    assert wide.loc[wide["geo"] == "HU", "rail_passengers"].iloc[0] == 20.0


def test_aggregate_news_counts_events_sentiment_money_and_operators():
    rows = [
        {
            "article_id": "n1",
            "country": "HU",
            "published_date": "2020-04-01",
            "is_rail_related": True,
            "event_type": "investment",
            "operators": ["RailCargo"],
            "sentiment": "positive",
            "monetary_amount_eur": 100.0,
        },
        {
            "article_id": "n2",
            "country": "HU",
            "published_date": "2020-05-01",
            "is_rail_related": True,
            "event_type": "accident",
            "operators": ["other"],
            "sentiment": "negative",
            "monetary_amount_eur": None,
        },
        {
            "article_id": "n3",
            "country": "AT",
            "published_date": "2020-06-01",
            "is_rail_related": False,
            "event_type": "policy",
            "operators": [],
            "sentiment": "neutral",
            "monetary_amount_eur": 50.0,
        },
    ]

    agg = gold_build.aggregate_news(rows)

    assert len(agg) == 1
    row = agg.iloc[0]
    assert row["geo"] == "HU"
    assert row["year"] == 2020
    assert row["news_article_count"] == 2
    assert row["news_n_investment"] == 1
    assert row["news_n_accident"] == 1
    assert row["news_total_investment_eur"] == 100.0
    assert row["news_share_negative"] == 0.5
    assert row["news_op_RailCargo"] == 1


def test_build_gold_fills_count_like_news_columns_with_zero():
    news_rows = [
        {
            "article_id": "n1",
            "country": "HU",
            "published_date": "2020-04-01",
            "is_rail_related": True,
            "event_type": "investment",
            "operators": ["RailCargo"],
            "sentiment": "positive",
            "monetary_amount_eur": 100.0,
        }
    ]

    gold = gold_build.build_gold(_stats_rows(), news_rows)
    at = gold[gold["geo"] == "AT"].iloc[0]

    assert at["news_article_count"] == 0
    assert at["news_n_investment"] == 0
    assert pd.isna(at["news_sentiment_mean"])


def test_write_parquet_writes_round_trippable_file(tmp_path):
    df = pd.DataFrame(
        [
            {"geo": "HU", "year": 2020, "rail_passengers": 20.0},
            {"geo": "AT", "year": 2020, "rail_passengers": 30.0},
        ]
    )
    path = tmp_path / "gold.parquet"

    returned = gold_build.write_parquet(df, str(path))

    assert returned == str(path)
    assert path.exists()
    loaded = pd.read_parquet(path)
    pd.testing.assert_frame_equal(loaded, df)
