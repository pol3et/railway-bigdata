import math

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
    assert row["news_sentiment_mean"] == 0.0
    assert row["news_share_negative"] == 0.5
    assert row["news_op_RailCargo"] == 1


def test_aggregate_news_prefers_encoder_sentiment_score_over_label_map():
    rows = [
        {
            "article_id": "n1",
            "country": "HU",
            "published_date": "2020-04-01",
            "is_rail_related": True,
            "event_type": "investment",
            "operators": [],
            "sentiment": "positive",
            "sentiment_score": 0.25,
            "monetary_amount_eur": None,
        },
        {
            "article_id": "n2",
            "country": "HU",
            "published_date": "2020-05-01",
            "is_rail_related": True,
            "event_type": "delay",
            "operators": [],
            "sentiment": "negative",
            "sentiment_score": -0.95,
            "monetary_amount_eur": None,
        },
    ]

    agg = gold_build.aggregate_news(rows)

    assert agg.iloc[0]["news_sentiment_mean"] == pytest.approx(-0.35)


def test_aggregate_news_emits_language_confidence_rail_lines_rollups():
    """Widened Gold news aggregation includes language, confidence, rail-line, and GKG rollups."""
    rows = [
        {
            "article_id": "n1",
            "country": "HU",
            "published_date": "2020-01-15",
            "is_rail_related": True,
            "event_type": "investment",
            "operators": ["MÁV"],
            "sentiment": "positive",
            "monetary_amount_eur": 100.0,
            "language": "hu",
            "confidence": 0.95,
            "rail_lines": ["M1", "M2"],
            "gkg_tone": 2.5,
            "gkg_themes": "TRANSPORT;RAIL",
            "gkg_persons": "Person A",
            "gkg_organizations": "MAV",
            "gkg_locations": "Hungary",
        },
        {
            "article_id": "n2",
            "country": "HU",
            "published_date": "2020-01-20",
            "is_rail_related": True,
            "event_type": "accident",
            "operators": ["ÖBB"],
            "sentiment": "negative",
            "monetary_amount_eur": None,
            "language": "de",
            "confidence": 0.72,
            "rail_lines": ["M1"],
            "gkg_tone": -1.0,
            "gkg_themes": "LABOR_STRIKE;RAIL",
            "gkg_organizations": "OBB",
            "gkg_locations": "Austria",
        },
        {
            "article_id": "n3",
            "country": "HU",
            "published_date": "2020-02-01",
            "is_rail_related": True,
            "event_type": "policy",
            "operators": [],
            "sentiment": "neutral",
            "monetary_amount_eur": 50.0,
            "language": "hu",
            "confidence": None,
            "rail_lines": [],
        },
    ]

    agg = gold_build.aggregate_news(rows, granularity="year")

    assert len(agg) == 1
    row = agg.iloc[0]
    assert row["geo"] == "HU"
    assert row["year"] == 2020
    assert row["news_article_count"] == 3
    assert row["news_n_investment"] == 1
    assert row["news_n_accident"] == 1
    assert row["news_n_policy"] == 1
    assert row["news_op_MÁV"] == 1
    assert row["news_op_ÖBB"] == 1

    assert "news_language_hu" in agg.columns
    assert "news_language_de" in agg.columns
    assert "news_language_cs" in agg.columns
    assert "news_language_cz" not in agg.columns
    assert row["news_language_hu"] == 2
    assert row["news_language_de"] == 1
    assert row["news_language_en"] == 0
    assert row["news_language_primary"] == "hu"
    expected_entropy = -((2 / 3) * math.log(2 / 3) + (1 / 3) * math.log(1 / 3))
    assert row["news_language_entropy"] == pytest.approx(expected_entropy)

    assert row["news_confidence_mean"] == pytest.approx((0.95 + 0.72) / 2)
    assert row["news_confidence_min"] == pytest.approx(0.72)
    assert row["news_confidence_max"] == pytest.approx(0.95)
    assert row["news_confidence_bin_low"] == 0
    assert row["news_confidence_bin_medium"] == 0
    assert row["news_confidence_bin_high"] == 2

    assert row["news_n_rail_lines_unique"] == 2
    assert row["news_rail_lines_list"] == "M1,M2"
    assert "news_rail_lines_M1" not in agg.columns

    assert row["news_gkg_tone_mean"] == pytest.approx(0.75)
    assert row["news_n_gkg_themes_unique"] == 3
    assert row["news_gkg_themes_list"] == "LABOR_STRIKE,RAIL,TRANSPORT"
    assert row["news_n_gkg_organizations_unique"] == 2


def test_aggregate_news_sub_annual_granularity_year_month():
    """Optional year-month granularity emits per-(geo, year, month) rows."""
    rows = [
        {
            "article_id": "n1",
            "country": "HU",
            "published_date": "2020-01-15",
            "is_rail_related": True,
            "event_type": "investment",
            "operators": ["MÁV"],
            "sentiment": "positive",
            "monetary_amount_eur": 100.0,
            "language": "hu",
            "confidence": 0.95,
            "rail_lines": [],
        },
        {
            "article_id": "n2",
            "country": "HU",
            "published_date": "2020-02-20",
            "is_rail_related": True,
            "event_type": "accident",
            "operators": [],
            "sentiment": "negative",
            "monetary_amount_eur": None,
            "language": "de",
            "confidence": 0.72,
            "rail_lines": [],
        },
    ]

    agg = gold_build.aggregate_news(rows, granularity="year-month")

    assert len(agg) == 2
    jan_row = agg[agg["month"] == 1].iloc[0]
    assert jan_row["geo"] == "HU"
    assert jan_row["year"] == 2020
    assert jan_row["month"] == 1
    assert jan_row["news_article_count"] == 1
    assert jan_row["news_language_hu"] == 1
    assert jan_row["news_language_de"] == 0

    feb_row = agg[agg["month"] == 2].iloc[0]
    assert feb_row["geo"] == "HU"
    assert feb_row["year"] == 2020
    assert feb_row["month"] == 2
    assert feb_row["news_article_count"] == 1
    assert feb_row["news_language_hu"] == 0
    assert feb_row["news_language_de"] == 1


def test_aggregate_news_schema_is_deterministic_for_disjoint_batches():
    """Canonical language, event, operator, and count columns do not vary by batch."""
    batch_a = [
        {
            "article_id": "a1",
            "country": "HU",
            "published_date": "2020-01-01",
            "is_rail_related": True,
            "event_type": "investment",
            "operators": ["MÁV"],
            "sentiment": "positive",
            "monetary_amount_eur": 10.0,
            "language": "hu",
            "confidence": 0.9,
            "rail_lines": ["M1"],
        }
    ]
    batch_b = [
        {
            "article_id": "b1",
            "country": "HU",
            "published_date": "2020-01-01",
            "is_rail_related": True,
            "event_type": "accident",
            "operators": ["ÖBB"],
            "sentiment": "negative",
            "monetary_amount_eur": None,
            "language": "de",
            "confidence": 0.6,
            "rail_lines": ["M3"],
        }
    ]

    agg_a = gold_build.aggregate_news(batch_a)
    agg_b = gold_build.aggregate_news(batch_b)

    assert set(agg_a.columns) == set(agg_b.columns)
    for column in (
        "news_language_hu",
        "news_language_de",
        "news_language_en",
        "news_language_cs",
        "news_confidence_bin_low",
        "news_confidence_bin_medium",
        "news_confidence_bin_high",
        "news_n_investment",
        "news_n_accident",
        "news_op_MÁV",
        "news_op_ÖBB",
        "news_n_rail_lines_unique",
        "news_rail_lines_list",
    ):
        assert column in agg_a.columns


def test_aggregate_news_handles_missing_optional_dict_fields_and_mixed_dates():
    rows = [
        {
            "article_id": "n1",
            "country": "HU",
            "published_date": "2020-01-01",
            "is_rail_related": True,
            "event_type": "investment",
        },
        {
            "article_id": "n2",
            "country": "HU",
            "published_date": "Wed, 01 Jan 2020 12:34:56 GMT",
            "is_rail_related": True,
            "event_type": "accident",
        },
        {
            "article_id": "n3",
            "country": "HU",
            "published_date": "20200101123000",
            "is_rail_related": True,
            "event_type": "policy",
        },
    ]

    agg = gold_build.aggregate_news(rows)

    row = agg.iloc[0]
    assert row["news_article_count"] == 3
    assert row["news_n_investment"] == 1
    assert row["news_n_accident"] == 1
    assert row["news_n_policy"] == 1
    assert row["news_n_rail_lines_unique"] == 0
    assert row["news_rail_lines_list"] == ""


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
