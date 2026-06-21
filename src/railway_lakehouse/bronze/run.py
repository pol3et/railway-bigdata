"""
Bronze orchestrator.

Two cadences, matching the requirements:
  * stats  -> yearly  (Eurostat + World Bank; national agencies plug in here)
  * news   -> weekly  (GDELT + RSS)

Usage:
    python -m railway_lakehouse.bronze.run stats     # one-off stats pull
    python -m railway_lakehouse.bronze.run news      # one-off news pull
    python -m railway_lakehouse.bronze.run all       # both, once
    python -m railway_lakehouse.bronze.run schedule  # run continuously
"""
import sys
import time
import logging

import schedule

from .lander import RawLander
from .sources import eurostat, worldbank, gdelt, rss_media

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("bronze.run")


def run_stats() -> None:
    logger.info("=== Bronze STATS batch ===")
    lander = RawLander()
    eurostat.ingest(lander)
    worldbank.ingest(lander)
    # GAP-005: national agencies are present but not scheduled yet.
    logger.info("=== STATS batch complete ===")


def run_news() -> None:
    logger.info("=== Bronze NEWS batch ===")
    lander = RawLander()
    gdelt.ingest(lander, timespan="1w")
    rss_media.ingest(lander)
    logger.info("=== NEWS batch complete ===")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "stats":
        run_stats()
    elif mode == "news":
        run_news()
    elif mode == "all":
        run_stats()
        run_news()
    elif mode == "schedule":
        run_stats()
        run_news()
        schedule.every().sunday.at("02:00").do(run_news)          # weekly
        schedule.every(365).days.at("03:00").do(run_stats)        # yearly
        logger.info("Scheduler started (news weekly, stats yearly).")
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
