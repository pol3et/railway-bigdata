"""Unit tests for the Silver persistence contract (canonical Parquet paths)."""
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from railway_lakehouse.silver import persist
from railway_lakehouse.silver.schema import NewsFeature

pytestmark = pytest.mark.unit


def _stats_df():
    return pd.DataFrame([
        {"geo": "HU", "year": 2021, "feature": "rail_passenger_km", "value": 5435.389,
         "unit": "worldbank_native", "source_system": "worldbank",
         "source_dataset": "IS.RRS.PASG.KM", "source_column": "Railways, passengers..."},
        {"geo": "AT", "year": 2020, "feature": "rail_passengers", "value": 200.0,
         "unit": "eurostat_native", "source_system": "eurostat",
         "source_dataset": "rail_demo", "source_column": "Rail passengers total"},
    ])


def test_silver_table_path_is_canonical():
    p = persist.silver_table_path("silver", "stats", "stat_fact", "2026-06-23")
    assert p.as_posix().endswith("silver/stats/stat_fact/ingest_date=2026-06-23/stat_fact.parquet")


def test_persist_and_load_stats_round_trip(tmp_path):
    persist.persist_stats(_stats_df(), tmp_path, ingest_date="2026-06-23")
    loaded = persist.load_stats(tmp_path)
    assert list(loaded.columns) == persist.STAT_FACT_COLUMNS
    assert len(loaded) == 2
    hu = loaded[loaded["geo"] == "HU"].iloc[0]
    assert hu["value"] == 5435.389 and hu["feature"] == "rail_passenger_km"


def test_persist_news_preserves_list_fields(tmp_path):
    rows = [NewsFeature(article_id="a1", source="rss", url="http://x/1",
                        published_date="2026-01-01", language="hu",
                        is_rail_related=True, country="HU", event_type="investment",
                        operators=["MÁV"], rail_lines=["Budapest-Wien"],
                        sentiment="positive", confidence=0.9)]
    persist.persist_news(rows, tmp_path, ingest_date="2026-06-23")
    loaded = persist.load_news(tmp_path)
    assert list(loaded.columns) == persist.NEWS_FEATURE_COLUMNS
    assert loaded.iloc[0]["article_id"] == "a1"
    assert list(loaded.iloc[0]["operators"]) == ["MÁV"]


def test_persist_news_empty_writes_valid_parquet(tmp_path):
    path = persist.persist_news([], tmp_path, ingest_date="2026-06-23")
    loaded = persist.load_news(tmp_path)
    assert list(loaded.columns) == persist.NEWS_FEATURE_COLUMNS
    assert len(loaded) == 0
    schema = pq.read_schema(path)
    assert schema.field("article_id").type == pa.string()
    assert schema.field("is_rail_related").type == pa.bool_()
    assert schema.field("operators").type == pa.list_(pa.string())
    assert schema.field("confidence").type == pa.float64()


def test_load_stats_reads_latest_partition(tmp_path):
    persist.persist_stats(_stats_df().head(1), tmp_path, ingest_date="2026-06-22")
    persist.persist_stats(_stats_df(), tmp_path, ingest_date="2026-06-23")
    assert len(persist.load_stats(tmp_path)) == 2          # latest date wins
