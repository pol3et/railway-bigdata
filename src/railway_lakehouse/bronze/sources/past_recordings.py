"""
past_recordings.py — initial historical NEWS backfill (one-off).

The regular `gdelt.py` fetcher pulls a rolling recent window (weekly cadence).
This module does the *initial* deep-history load: it walks GDELT back across
the historical range and lands raw article records until a target article
count is reached (default 50,000). Run it ONCE to seed Bronze with history;
the weekly job keeps it current thereafter.

Contract (true Bronze): every GDELT response page is landed verbatim as raw
bytes with a .meta.json sidecar; we do NOT parse article text or dedup here
(Silver's job). The rail-topic query + country restriction is the collection
boundary, identical to gdelt.py, so history and live use the same definition.

Coverage note: GDELT 2.0 (the DOC 2.0 API used here) covers 2017-present with
rich query support; GDELT 1.0 covers 1979-2016 but only via the raw event/GKG
CSV master-file lists, not the DOC API. This module therefore has two engines:
  * doc_api   — paginated DOC 2.0 ArtList queries (rich, recent history)
  * master_v1 — fetch GDELT 1.0/GKG master file list and land the raw daily
                CSV.zip files (deep history 1979-2016), unparsed
Pick with --engine; default 'doc_api'. Both stop at --target-articles.

Usage:
    python -m railway_lakehouse.bronze.sources.past_recordings
    python -m railway_lakehouse.bronze.sources.past_recordings --target-articles 100000
    python -m railway_lakehouse.bronze.sources.past_recordings --engine master_v1 \
        --start 1990-01-01 --end 2014-12-31
"""
import sys
import json
import time
import logging
import argparse
import datetime as dt

import requests

from ..lander import RawArtifact, RawLander
from ..config import NATIONAL_SCOPE

logger = logging.getLogger("bronze.sources.past_recordings")

# Multilingual rail terms — MUST match gdelt.py so history == live collection.
RAIL_TERMS = ['rail', 'railway', 'vasút', 'MÁV', 'GYSEV', 'Bahn', 'ÖBB', 'Eisenbahn']
DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
GKG_MASTERLIST = "http://data.gdeltproject.org/gkg/index.html"   # 1.0 GKG daily files
HTTP_TIMEOUT = 120
DEFAULT_TARGET = 50_000
PAGE_SIZE = 250                 # DOC API max records per call
SLEEP_BETWEEN = 1.0             # be polite to the public API


def _build_query() -> str:
    terms = " OR ".join(f'"{t}"' if " " in t else t for t in RAIL_TERMS)
    countries = " OR ".join(f"sourcecountry:{c}" for c in NATIONAL_SCOPE)
    return f"({terms}) ({countries})"


def _month_windows(start: dt.date, end: dt.date):
    """Yield (start,end) month-sized windows; GDELT caps results per query, so
    we page by month to walk the whole range without missing dense periods."""
    cur = start
    while cur < end:
        nxt = (cur.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        yield cur, min(nxt, end)
        cur = nxt


def backfill_doc_api(lander: RawLander, start: dt.date, end: dt.date,
                     target: int) -> int:
    """Paginate DOC 2.0 ArtList over [start,end]; land each raw JSON page.
    Returns approximate number of article records landed (page_count*page_size
    lower-bounded by actual returned sizes)."""
    query = _build_query()
    got = 0
    for w_start, w_end in _month_windows(start, end):
        if got >= target:
            break
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": PAGE_SIZE,
            "startdatetime": w_start.strftime("%Y%m%d000000"),
            "enddatetime": w_end.strftime("%Y%m%d000000"),
            "sort": "datedesc",
        }
        try:
            r = requests.get(DOC_API, params=params, timeout=HTTP_TIMEOUT,
                             headers={"User-Agent": "railway-lakehouse-bronze/1.0"})
        except requests.RequestException as e:
            logger.warning("DOC API failed for %s..%s: %s", w_start, w_end, e)
            continue
        if r.status_code != 200 or not r.content:
            logger.warning("DOC API %s..%s -> HTTP %s", w_start, w_end, r.status_code)
            continue
        # count articles in this page (raw JSON, parsed only to count — landed verbatim)
        n_page = 0
        try:
            n_page = len(json.loads(r.content).get("articles", []))
        except Exception:
            n_page = 0
        # land the raw page verbatim regardless of parse success
        lander.land(RawArtifact(
            domain="news", source="gdelt_history", dataset_id="doc_artlist",
            filename=f"gdelt_{w_start:%Y%m}.json",
            content=r.content, source_url=r.url,
            content_type="application/json", http_status=r.status_code,
            extra={"engine": "doc_api", "window_start": str(w_start),
                   "window_end": str(w_end), "articles_in_page": n_page},
        ))
        got += n_page if n_page else PAGE_SIZE  # lower-bound when count unknown
        logger.info("DOC API %s..%s: +%d (total ~%d / %d)",
                    w_start, w_end, n_page, got, target)
        time.sleep(SLEEP_BETWEEN)
    logger.info("DOC API backfill done: ~%d article records landed", got)
    return got


def backfill_master_v1(lander: RawLander, start: dt.date, end: dt.date,
                       target: int) -> int:
    """Deep history (1979-2016): land raw GDELT 1.0 GKG daily CSV.zip files
    verbatim. We do not parse them — Silver filters to rail/HU/AT. 'target' here
    bounds the number of daily files (each holds many thousands of records)."""
    landed_files = 0
    day = start
    while day < end and landed_files < target:
        # GDELT 1.0 GKG daily file naming: YYYYMMDD.gkg.csv.zip
        fname = f"{day:%Y%m%d}.gkg.csv.zip"
        url = f"http://data.gdeltproject.org/gkg/{fname}"
        try:
            r = requests.get(url, timeout=HTTP_TIMEOUT,
                             headers={"User-Agent": "railway-lakehouse-bronze/1.0"})
        except requests.RequestException as e:
            logger.warning("GKG v1 %s failed: %s", url, e)
            day += dt.timedelta(days=1); continue
        if r.status_code == 200 and r.content:
            lander.land(RawArtifact(
                domain="news", source="gdelt_history", dataset_id="gkg_v1_daily",
                filename=fname, content=r.content, source_url=url,
                content_type="application/zip", http_status=200,
                extra={"engine": "master_v1", "date": str(day)},
            ))
            landed_files += 1
            logger.info("GKG v1: landed %s (%d files)", fname, landed_files)
        day += dt.timedelta(days=1)
        time.sleep(SLEEP_BETWEEN)
    logger.info("GKG v1 backfill done: %d daily files landed", landed_files)
    return landed_files


def ingest(lander: RawLander, target_articles: int = DEFAULT_TARGET,
           engine: str = "doc_api", start: dt.date | None = None,
           end: dt.date | None = None) -> int:
    """Entry point used by run.py or the CLI. Defaults: DOC API, 50k articles,
    last ~10y window (DOC 2.0 coverage). For deep history use engine='master_v1'."""
    if engine == "master_v1":
        start = start or dt.date(1990, 1, 1)
        end = end or dt.date(2015, 1, 1)
        return backfill_master_v1(lander, start, end, target_articles)
    # doc_api default
    end = end or dt.date.today()
    start = start or (end - dt.timedelta(days=365 * 10))
    return backfill_doc_api(lander, start, end, target_articles)


def _parse_args(argv):
    p = argparse.ArgumentParser(description="Initial historical GDELT news backfill.")
    p.add_argument("--target-articles", type=int, default=DEFAULT_TARGET,
                   help=f"stop after ~this many article records (default {DEFAULT_TARGET})")
    p.add_argument("--engine", choices=["doc_api", "master_v1"], default="doc_api")
    p.add_argument("--start", type=lambda s: dt.date.fromisoformat(s), default=None)
    p.add_argument("--end", type=lambda s: dt.date.fromisoformat(s), default=None)
    return p.parse_args(argv)


def main(argv=None):
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    a = _parse_args(argv if argv is not None else sys.argv[1:])
    lander = RawLander()
    n = ingest(lander, target_articles=a.target_articles, engine=a.engine,
               start=a.start, end=a.end)
    logger.info("past_recordings complete: ~%d records/files landed via %s", n, a.engine)


if __name__ == "__main__":
    main()
