"""
Persist Silver outputs to canonical Parquet paths (GAP-006).

This freezes the Silver persistence contract so Gold (and Spark) read from a
documented, stable location instead of in-memory frames. Layout mirrors Bronze
(partitioned by ``ingest_date``) with one replaceable daily snapshot:

    <silver_root>/stats/stat_fact/ingest_date=YYYY-MM-DD/stat_fact.parquet
    <silver_root>/news/news_feature/ingest_date=YYYY-MM-DD/news_feature.parquet

``<silver_root>`` is a local filesystem Silver tree for fixtures and local
evidence. MinIO/s3fs persistence is intentionally left to the storage wiring
task.

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
import pyarrow as pa
import pyarrow.parquet as pq

from .news.failures import persist_news_failures as _persist_news_failures_json
from .schema import NewsFeature, StatFact

logger = logging.getLogger("silver.persist")

STATS_DOMAIN, STATS_TABLE = "stats", "stat_fact"
NEWS_DOMAIN, NEWS_TABLE = "news", "news_feature"

STAT_FACT_COLUMNS = list(StatFact.__dataclass_fields__)
NEWS_FEATURE_COLUMNS = list(NewsFeature.__dataclass_fields__)

STAT_FACT_ARROW_SCHEMA = pa.schema([
    ("geo", pa.string()),
    ("year", pa.int64()),
    ("feature", pa.string()),
    ("value", pa.float64()),
    ("unit", pa.string()),
    ("source_system", pa.string()),
    ("source_dataset", pa.string()),
    ("source_column", pa.string()),
])

NEWS_FEATURE_ARROW_SCHEMA = pa.schema([
    ("article_id", pa.string()),
    ("source", pa.string()),
    ("url", pa.string()),
    ("published_date", pa.string()),
    ("language", pa.string()),
    ("is_rail_related", pa.bool_()),
    ("country", pa.string()),
    ("event_type", pa.string()),
    ("operators", pa.list_(pa.string())),
    ("rail_lines", pa.list_(pa.string())),
    ("monetary_amount_eur", pa.float64()),
    ("monetary_raw", pa.string()),
    ("summary_en", pa.string()),
    ("sentiment", pa.string()),
    ("confidence", pa.float64()),
    ("language_detected_code", pa.string()),
    ("language_confidence", pa.float64()),
    ("sentiment_label", pa.string()),
    ("sentiment_score", pa.float64()),
    ("sentiment_confidence", pa.float64()),
    ("is_rail_related_confidence", pa.float64()),
    ("event_type_confidence", pa.float64()),
    ("summary_en_source", pa.string()),
    ("operators_ner_model", pa.string()),
    ("operators_confidence", pa.float64()),
    ("rail_lines_ner_model", pa.string()),
    ("rail_lines_confidence", pa.float64()),
    ("monetary_raw_parsed_eur", pa.float64()),
    ("monetary_confidence", pa.float64()),
    ("gkg_themes", pa.string()),
    ("gkg_persons", pa.string()),
    ("gkg_organizations", pa.string()),
    ("gkg_locations", pa.string()),
    ("gkg_tone", pa.float64()),
    ("gkg_emotions", pa.string()),
    ("gkg_tone_source", pa.string()),
    ("text_embedding_model", pa.string()),
    ("text_embedding", pa.list_(pa.float64())),
    ("cluster_id", pa.string()),
    ("cross_lingual_dedup_id", pa.string()),
    ("extraction_timestamp_utc", pa.string()),
    ("extraction_model_digest", pa.string()),
    ("confidence_schema_version", pa.string()),
])


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
def _as_string_list(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    if pd.isna(value):
        return None
    return [str(value)]


def _as_float_list(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            try:
                out.append(float(item))
            except (TypeError, ValueError):
                return None
        return out
    if pd.isna(value):
        return None
    return None


def _stats_frame(stats_long: pd.DataFrame) -> pd.DataFrame:
    df = (stats_long if stats_long is not None else pd.DataFrame()).reindex(
        columns=STAT_FACT_COLUMNS)
    for column in ("geo", "feature", "unit", "source_system", "source_dataset", "source_column"):
        df[column] = df[column].astype("string")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["value"] = pd.to_numeric(df["value"], errors="coerce").astype("Float64")
    return df


def _news_frame(news_rows) -> pd.DataFrame:
    rows = []
    for r in news_rows or []:
        rows.append(r.to_row() if hasattr(r, "to_row") else dict(r))
    df = pd.DataFrame(rows).reindex(columns=NEWS_FEATURE_COLUMNS)
    for column in (
        "article_id", "source", "url", "published_date", "language",
        "country", "event_type", "monetary_raw", "summary_en", "sentiment",
        "language_detected_code", "sentiment_label", "summary_en_source",
        "operators_ner_model", "rail_lines_ner_model", "gkg_themes",
        "gkg_persons", "gkg_organizations", "gkg_locations", "gkg_emotions",
        "gkg_tone_source", "text_embedding_model", "cluster_id",
        "cross_lingual_dedup_id", "extraction_timestamp_utc",
        "extraction_model_digest", "confidence_schema_version",
    ):
        df[column] = df[column].astype("string")
    df["confidence_schema_version"] = df["confidence_schema_version"].fillna("1.0")
    df["is_rail_related"] = df["is_rail_related"].astype("boolean")
    for column in ("operators", "rail_lines"):
        df[column] = df[column].map(_as_string_list).astype("object")
    df["text_embedding"] = df["text_embedding"].map(_as_float_list).astype("object")
    for column in (
        "monetary_amount_eur", "confidence", "language_confidence",
        "sentiment_score", "sentiment_confidence", "is_rail_related_confidence",
        "event_type_confidence", "operators_confidence", "rail_lines_confidence",
        "monetary_raw_parsed_eur", "monetary_confidence", "gkg_tone",
    ):
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Float64")
    return df


def _write_parquet(df: pd.DataFrame, path: Path, schema: pa.Schema) -> None:
    table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
    pq.write_table(table, path)


def persist_stats(stats_long: pd.DataFrame, root, *, ingest_date: str = None) -> Path:
    """Write the unified StatFact long table to its canonical partition.
    Columns are reindexed to the contract order; returns the file path."""
    ingest_date = ingest_date or _today()
    df = _stats_frame(stats_long)
    path = silver_table_path(root, STATS_DOMAIN, STATS_TABLE, ingest_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_parquet(df, path, STAT_FACT_ARROW_SCHEMA)
    logger.info("persisted Silver stats: %s (%d rows)", path, len(df))
    return path


def persist_news(news_rows, root, *, ingest_date: str = None) -> Path:
    """Write NewsFeature rows (NewsFeature objects OR dicts) to canonical Parquet.
    An empty list still writes a valid, schema-shaped (0-row) file so Gold always
    has a deterministic input."""
    ingest_date = ingest_date or _today()
    df = _news_frame(news_rows)
    path = silver_table_path(root, NEWS_DOMAIN, NEWS_TABLE, ingest_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_parquet(df, path, NEWS_FEATURE_ARROW_SCHEMA)
    logger.info("persisted Silver news: %s (%d rows)", path, len(df))
    return path


def persist_news_failures(failures, root, *, ingest_date: str = None) -> Path:
    """Write extraction failures as a JSON sidecar, not a Parquet table."""
    ingest_date = ingest_date or _today()
    path = _persist_news_failures_json(failures, root, ingest_date)
    logger.warning("persisted Silver news extraction failures: %s (%d rows)", path, len(failures or []))
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
    df = pd.read_parquet(path).reindex(columns=NEWS_FEATURE_COLUMNS)
    if "confidence_schema_version" in df:
        df["confidence_schema_version"] = df["confidence_schema_version"].fillna("1.0")
    return df
