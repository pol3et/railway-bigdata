"""
GAP-006 integration: full persisted Bronze -> Silver -> (load) -> Gold chain.

Reads Bronze stat fixtures, builds the unified StatFact table, PERSISTS it to the
canonical Silver Parquet path, RELOADS it from disk, and feeds the reloaded
frame to Gold. Proves Gold can run off persisted Silver outputs (no in-memory
hand-off), which is the GAP-006 -> GAP-007 contract.

Run with:  python -m pytest -q -m integration
"""
from pathlib import Path

import pandas as pd
import pytest

from railway_lakehouse.silver.stats import load as stats_load
from railway_lakehouse.silver.stats import merge as stats_merge
from railway_lakehouse.silver import persist
from railway_lakehouse.gold.run import build_from_silver

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent / "fixtures" / "bronze"


def test_persisted_silver_feeds_gold(tmp_path, monkeypatch):
    monkeypatch.setattr(stats_merge, "CROSSWALK_PATH", str(tmp_path / "crosswalk.json"))
    silver_root = tmp_path / "silver"

    # Bronze -> Silver stats (deterministic), then persist + persist empty news
    stats_long = stats_load.build_silver_stats(FIXTURES, use_llm=False)
    paths = persist.persist_silver(stats_long, [], silver_root, ingest_date="2026-06-23")
    assert paths["stats"].exists() and paths["news"].exists()

    # reload purely from disk — Gold must not depend on the in-memory frame
    reloaded = persist.load_stats(silver_root)
    assert list(reloaded.columns) == persist.STAT_FACT_COLUMNS
    assert len(reloaded) == len(stats_long) and len(reloaded) >= 3
    news = persist.load_news(silver_root)            # valid 0-row table
    assert list(news.columns) == persist.NEWS_FEATURE_COLUMNS

    # persisted Silver -> Gold parquet
    gold_out = tmp_path / "gold" / "railway_ml.parquet"
    build_from_silver(reloaded, news.to_dict("records"), str(gold_out))
    assert gold_out.exists()
    gold = pd.read_parquet(gold_out)
    assert len(gold) >= 1
    assert {"geo", "year"}.issubset(gold.columns)
    # the World Bank passenger-km feature survived the full persisted chain
    assert "rail_passenger_km" in gold.columns
