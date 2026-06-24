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
    assert counts["contains_AT"] is True
    assert counts["contains_HU"] is True
