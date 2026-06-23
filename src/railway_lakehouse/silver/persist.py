"""
Persist Silver outputs to canonical Parquet paths (GAP-006).

This freezes the Silver persistence contract so Gold (and Spark) read from a
documented, stable location instead of in-memory frames. Layout mirrors Bronze
(partitioned by ``ingest_date``) so re-runs accumulate auditable history:

    <silver_root>/stats/stat_fact/ingest_date=YYYY-MM-DD/stat_fact.parquet
    <silver_root>/news/news_feature/ingest_date=YYYY-MM-DD/news_feature.parquet

``<silver_root>`` is the local Silver tree for fixtures, or the ``SILVER_BUCKET``
prefix when wired to MinIO/s3fs (same pattern as the Bronze RawLander).

Schemas are the dataclasses in ``schema.py`` — column order is derived from them
so the persisted files can never silently drift from the contract:
  * stats -> StatFact   (geo, year, feature, value, unit, source_system,
                         source_dataset, source_column)
  * news  -> NewsFeature (article_id, source, url, ... sentiment, confidence)
"""
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .schema import StatFact, NewsFeature

logger = logging.getLogger("silver.persist")

STATS_DOMAIN, STATS_TABLE = "stats", "stat_fact"
NEWS_DOMAIN, NEWS_TABLE = "news", "news_feature"

STAT_FACT_COLUMNS = list(StatFact.__dataclass_fields__)
NEWS_FEATURE_COLUMNS = list(NewsFeature.__dataclass_fields__)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def silver_table_path(root, domain: str, table: str, ingest_date: str) -> Path:
    """Canonical parquet path for a Silver table partition."""
    return (Path(root) / domain / table /
            f"ingest_date={ingest_date}" / f"{table}.parquet")


def _latest_path(root, domain: str, table: str) -> "Path | None":
    base = Path(root) / domain / table
    parts = sorted(p for p in base.glob("ingest_date=*") if p.is_dir()) if base.is_dir() else []
    if not parts:
        return None
    return parts[-1] / f"{table}.parquet"


# --------------------------------------------------------------------------
# write
# --------------------------------------------------------------------------
def persist_stats(stats_long: pd.DataFrame, root, *, ingest_date: str = None) -> Path:
    """Write the unified StatFact long table to its canonical partition.
    Columns are reindexed to the contract order; returns the file path."""
    ingest_date = ingest_date or _today()
    df = (stats_long if stats_long is not None else pd.DataFrame()).reindex(
        columns=STAT_FACT_COLUMNS)
    path = silver_table_path(root, STATS_DOMAIN, STATS_TABLE, ingest_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    logger.info("persisted Silver stats: %s (%d rows)", path, len(df))
    return path


def persist_news(news_rows, root, *, ingest_date: str = None) -> Path:
    """Write NewsFeature rows (NewsFeature objects OR dicts) to canonical Parquet.
    An empty list still writes a valid, schema-shaped (0-row) file so Gold always
    has a deterministic input."""
    ingest_date = ingest_date or _today()
    rows = []
    for r in news_rows or []:
        rows.append(r.to_row() if hasattr(r, "to_row") else dict(r))
    df = pd.DataFrame(rows).reindex(columns=NEWS_FEATURE_COLUMNS)
    path = silver_table_path(root, NEWS_DOMAIN, NEWS_TABLE, ingest_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    logger.info("persisted Silver news: %s (%d rows)", path, len(df))
    return path


def persist_silver(stats_long, news_rows, root, *, ingest_date: str = None) -> dict:
    """Persist both Silver tables in one call; returns {'stats': path, 'news': path}."""
    ingest_date = ingest_date or _today()
    return {
        "stats": persist_stats(stats_long, root, ingest_date=ingest_date),
        "news": persist_news(news_rows, root, ingest_date=ingest_date),
    }


# --------------------------------------------------------------------------
# read (what Gold loads)
# --------------------------------------------------------------------------
def load_stats(root, *, ingest_date: str = None) -> pd.DataFrame:
    """Load the persisted StatFact table (latest partition unless a date given)."""
    path = (silver_table_path(root, STATS_DOMAIN, STATS_TABLE, ingest_date)
            if ingest_date else _latest_path(root, STATS_DOMAIN, STATS_TABLE))
    if not path or not Path(path).exists():
        return pd.DataFrame(columns=STAT_FACT_COLUMNS)
    return pd.read_parquet(path)


def load_news(root, *, ingest_date: str = None) -> pd.DataFrame:
    """Load the persisted NewsFeature table (latest partition unless a date given)."""
    path = (silver_table_path(root, NEWS_DOMAIN, NEWS_TABLE, ingest_date)
            if ingest_date else _latest_path(root, NEWS_DOMAIN, NEWS_TABLE))
    if not path or not Path(path).exists():
        return pd.DataFrame(columns=NEWS_FEATURE_COLUMNS)
    return pd.read_parquet(path)
