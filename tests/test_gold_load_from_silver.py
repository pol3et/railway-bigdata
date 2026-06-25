import json
from pathlib import Path

import pandas as pd
import pytest

from railway_lakehouse.gold import run as gold_run
from railway_lakehouse.silver import persist
from railway_lakehouse.silver.stats import load as stats_load
from railway_lakehouse.silver.stats import merge as stats_merge

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent / "fixtures" / "bronze"


def test_gold_cli_loads_persisted_silver_and_writes_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(stats_merge, "CROSSWALK_PATH", str(tmp_path / "crosswalk.json"))
    silver_root = tmp_path / "silver"
    out_path = tmp_path / "gold" / "railway_ml.parquet"
    counts_path = tmp_path / "gold" / "counts.json"

    stats_long = stats_load.build_silver_stats(FIXTURES, use_llm=False)
    persist.persist_silver(stats_long, [], silver_root, ingest_date="2026-06-23")

    returned = gold_run.main(
        [
            "--silver-root",
            str(silver_root),
            "--out",
            str(out_path),
            "--counts-out",
            str(counts_path),
            "--ingest-date",
            "2026-06-23",
        ]
    )

    assert returned == str(out_path)
    assert out_path.exists()
    gold = pd.read_parquet(out_path)
    assert len(gold) >= 1
    assert "rail_passenger_km" in gold.columns

    assert counts_path.exists()
    counts = json.loads(counts_path.read_text(encoding="utf-8"))
    assert counts["path"] == out_path.as_posix()
    assert counts["rows"] == len(gold)
    assert counts["columns"] == len(gold.columns)
    assert counts["column_names"] == [str(column) for column in gold.columns]
    assert counts["geo_level_counts"] == {"country": 4}
    assert counts["contains_AT"] is True
    assert counts["contains_HU"] is True


def test_gold_cli_loads_persisted_wide_news_columns(tmp_path):
    silver_root = tmp_path / "silver"
    out_path = tmp_path / "gold" / "railway_ml.parquet"
    counts_path = tmp_path / "gold" / "counts.json"
    stats_long = pd.DataFrame(columns=persist.STAT_FACT_COLUMNS)
    news_rows = [
        {
            "article_id": "n1",
            "source": "gdelt",
            "url": "https://example.test/n1",
            "published_date": "2020-01-15",
            "language": "hu",
            "is_rail_related": True,
            "country": "HU",
            "event_type": "investment",
            "operators": ["MÁV"],
            "rail_lines": ["M1", "M2"],
            "monetary_amount_eur": 100.0,
            "sentiment": "positive",
            "confidence": 0.9,
            "gkg_tone": 1.5,
            "gkg_themes": "TRANSPORT;RAIL",
            "gkg_organizations": "MAV",
        }
    ]
    persist.persist_silver(stats_long, news_rows, silver_root, ingest_date="2026-06-25")

    returned = gold_run.main(
        [
            "--silver-root",
            str(silver_root),
            "--out",
            str(out_path),
            "--counts-out",
            str(counts_path),
            "--ingest-date",
            "2026-06-25",
        ]
    )

    assert returned == str(out_path)
    gold = pd.read_parquet(out_path)
    row = gold.iloc[0]
    assert row["geo"] == "HU"
    assert row["news_language_hu"] == 1
    assert row["news_confidence_mean"] == pytest.approx(0.9)
    assert row["news_n_rail_lines_unique"] == 2
    assert row["news_rail_lines_list"] == "M1,M2"
    assert row["news_gkg_tone_mean"] == pytest.approx(1.5)
