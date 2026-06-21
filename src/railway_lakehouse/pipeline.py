"""
End-to-end driver: Bronze -> Silver -> Gold for a bounded demo run
(100 news articles + the Eurostat rail datasets) producing the ML-ready Parquet.

This is the orchestration skeleton. The three I/O points marked `# WIRE:` are
where you read/write MinIO; everything between them is the tested logic.

Run inside your Docker stack (needs network for Eurostat/GDELT and a running
Ollama for news extraction):

    python -m railway_lakehouse.pipeline --news 100 --out gold/railway_ml.parquet
"""
import argparse
import logging

import pandas as pd

# Bronze (your existing package + the new fetchers)
from railway_lakehouse.bronze.lander import RawLander
from railway_lakehouse.bronze.sources import eurostat
from railway_lakehouse.bronze.sources import past_recordings

# Silver
from railway_lakehouse.silver.stats import merge as stats_merge
from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.ollama_client import health_check

# Gold
from railway_lakehouse.gold.run import build_from_silver

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger("pipeline")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--news", type=int, default=100, help="target number of articles")
    ap.add_argument("--out", default="gold/railway_ml.parquet")
    args = ap.parse_args()

    # ---------------- BRONZE ----------------
    log.info("BRONZE: landing Eurostat rail datasets + %d news articles", args.news)
    lander = RawLander()
    eurostat.ingest(lander)                                   # all rail TSVs, raw
    past_recordings.ingest(lander, target_articles=args.news) # ~N articles, raw JSON

    # ---------------- SILVER (stats) ----------------
    # WIRE: read the raw Eurostat TSVs you just landed back from MinIO.
    raw_eurostat_tables = _read_bronze_eurostat(lander)       # -> {dataset_id: DataFrame}
    frames = []
    for dataset_id, df in raw_eurostat_tables.items():
        long = stats_merge.read_eurostat_tsv(df, dataset_id)
        long["source_system"] = "eurostat"
        frames.append(long)
    log.info("SILVER stats: %d source frames", len(frames))

    # crosswalk (Eurostat maps by rule; LLM only if reachable, only for HU/DE)
    labels = sorted({l for fr in frames for l in fr["source_column"].astype(str)})
    crosswalk = stats_merge.build_crosswalk(labels, use_llm=health_check())
    stats_long = stats_merge.merge_sources(frames, crosswalk)

    # ---------------- SILVER (news) ----------------
    # WIRE: read the raw article records you landed; shape into dicts.
    articles = _read_bronze_news(lander, limit=args.news)     # -> list[dict]
    if health_check():
        news_rows = news_extract.extract_batch(articles)      # Ollama -> NewsFeature
    else:
        log.warning("Ollama unreachable; skipping news extraction.")
        news_rows = []

    # ---------------- GOLD ----------------
    out = build_from_silver(stats_long, news_rows, args.out)
    log.info("DONE -> %s", out)


# --- WIRE points (replace these stubs with your s3fs reads) ------------------
def _read_bronze_eurostat(lander) -> dict:
    """Return {dataset_id: raw DataFrame} read from the Bronze eurostat partition.
    Replace with s3fs: list bronze/stats/eurostat/*/ingest_date=*/*.tsv.gz, read
    each with pd.read_csv(sep='\\t')."""
    raise NotImplementedError("wire MinIO read of bronze/stats/eurostat/*")


def _read_bronze_news(lander, limit: int) -> list:
    """Return up to `limit` article dicts {article_id, source, url, title, body,
    published_date} read from bronze/news/*. For GDELT JSON pages, iterate the
    'articles' arrays; for RSS, parse the landed feed entries."""
    raise NotImplementedError("wire MinIO read of bronze/news/*")


if __name__ == "__main__":
    main()
