"""
Gold orchestrator - turn persisted Silver outputs into the ML-ready Parquet dataset.

    python -m railway_lakehouse.gold.run \
        --silver-root output/evidence/silver \
        --out output/evidence/gold/railway_ml.parquet \
        --counts-out output/evidence/gold/counts.json

Expects the Silver stage to have produced:
  * a stats long table (StatFact rows), and
  * news feature rows (NewsFeature),
under the frozen local Silver Parquet contract documented in DATA_CONTRACTS.md.
"""
import argparse
import logging

from railway_lakehouse.silver import persist

from .build import build_gold, write_gold_counts, write_parquet

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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--silver-root",
        required=True,
        help=(
            "local Silver tree containing stats/stat_fact and news/news_feature "
            "parquet partitions"
        ),
    )
    ap.add_argument("--out", default="output/evidence/gold/railway_ml.parquet")
    ap.add_argument(
        "--counts-out",
        default="output/evidence/gold/counts.json",
        help="write a JSON row/column summary for the generated Gold Parquet",
    )
    ap.add_argument(
        "--ingest-date",
        default=None,
        help="load this Silver ingest_date partition; defaults to latest partition",
    )
    ap.add_argument("--year-min", type=int, default=None)
    ap.add_argument("--year-max", type=int, default=None)
    args = ap.parse_args(argv)

    stats_long = persist.load_stats(args.silver_root, ingest_date=args.ingest_date)
    news_df = persist.load_news(args.silver_root, ingest_date=args.ingest_date)
    logger.info(
        "Silver loaded from %s (stats rows=%d, news rows=%d)",
        args.silver_root,
        len(stats_long),
        len(news_df),
    )

    out_path = build_from_silver(
        stats_long,
        news_df.to_dict("records"),
        args.out,
        year_min=args.year_min,
        year_max=args.year_max,
    )
    if args.counts_out:
        counts_path = write_gold_counts(out_path, args.counts_out)
        logger.info("GOLD counts -> %s", counts_path)
    logger.info("DONE -> %s", out_path)
    return out_path


if __name__ == "__main__":
    main()
