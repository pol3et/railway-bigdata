"""
Gold orchestrator — turn Silver outputs into the ML-ready Parquet dataset.

    python -m railway_lakehouse.gold.run --out gold/railway_ml.parquet

Expects the Silver stage to have produced:
  * a stats long table (StatFact rows), and
  * news feature rows (NewsFeature),
which you load from your Silver storage and pass to build_gold(). The wiring
points below are where you read Silver from MinIO/Parquet.
"""
import sys
import argparse
import logging

from .build import build_gold, write_parquet

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("gold.run")


def build_from_silver(stats_long, news_rows, out_path: str,
                      year_min=None, year_max=None) -> str:
    """Pure entry point: Silver frames -> Gold parquet. Importable + testable."""
    gold = build_gold(stats_long, news_rows, year_min=year_min, year_max=year_max)
    if gold.empty:
        logger.warning("Gold table is empty — check Silver inputs.")
    return write_parquet(gold, out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="gold/railway_ml.parquet")
    ap.add_argument("--year-min", type=int, default=None)
    ap.add_argument("--year-max", type=int, default=None)
    ap.parse_args()
    logger.info("gold.run: load Silver stats_long + news_rows from your storage, "
                "then call build_from_silver(...). Wire MinIO/Parquet reads here.")


if __name__ == "__main__":
    main()
