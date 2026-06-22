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
Pick with --engine; default 'doc_api'. Both stop at --target-articles and
the CLI also applies --max-pages as a safety bound.

Safe default usage:
    python -m railway_lakehouse.bronze.sources.past_recordings --dry-run
    python -m railway_lakehouse.bronze.sources.past_recordings --max-pages 3
    python -m railway_lakehouse.bronze.sources.past_recordings --target-articles 100000 --max-pages 0
    python -m railway_lakehouse.bronze.sources.past_recordings --engine master_v1 \
        --start 1990-01-01 --end 2014-12-31 --max-pages 30
"""
import sys
import json
import time
import logging
import argparse
import datetime as dt
from collections.abc import Callable

import requests

from ..lander import RawArtifact, RawLander
from ..config import NATIONAL_SCOPE
from .gdelt_common import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_SLEEP_SECONDS,
    DOC_API,
    DOC_API_MAX_RECORDS,
    REQUEST_HEADERS,
    bounded_max_records,
    get_with_rate_limit_retries,
)

logger = logging.getLogger("bronze.sources.past_recordings")

# Multilingual rail terms — MUST match gdelt.py so history == live collection.
RAIL_TERMS = ['rail', 'railway', 'vasút', 'MÁV', 'GYSEV', 'Bahn', 'ÖBB', 'Eisenbahn']
GKG_MASTERLIST = "http://data.gdeltproject.org/gkg/index.html"   # 1.0 GKG daily files
HTTP_TIMEOUT = 120
DEFAULT_TARGET = 50_000
PAGE_SIZE = DOC_API_MAX_RECORDS
DEFAULT_MAX_PAGES = 1
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


def backfill_doc_api(
    lander: RawLander,
    start: dt.date,
    end: dt.date,
    target: int,
    *,
    max_pages: int | None = DEFAULT_MAX_PAGES,
    session: requests.Session | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_sleep_seconds: float = DEFAULT_RETRY_SLEEP_SECONDS,
    sleep: Callable[[float], object] = time.sleep,
    dry_run: bool = False,
) -> int:
    """Paginate DOC 2.0 ArtList over [start,end]; land each raw JSON page.
    Returns approximate number of article records landed (page_count*page_size
    lower-bounded by actual returned sizes)."""
    query = _build_query()
    session = session or requests.Session()
    max_pages = _normalize_optional_limit(max_pages)
    got = 0
    pages_attempted = 0
    for w_start, w_end in _month_windows(start, end):
        if got >= target or _limit_reached(pages_attempted, max_pages):
            break
        pages_attempted += 1
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": bounded_max_records(PAGE_SIZE),
            "startdatetime": w_start.strftime("%Y%m%d000000"),
            "enddatetime": w_end.strftime("%Y%m%d000000"),
            "sort": "datedesc",
        }
        if dry_run:
            logger.info("DRY RUN DOC API %s..%s params=%s", w_start, w_end, params)
            continue
        try:
            r = get_with_rate_limit_retries(
                session.get,
                DOC_API,
                params=params,
                timeout=HTTP_TIMEOUT,
                headers=REQUEST_HEADERS,
                max_retries=max_retries,
                retry_sleep_seconds=retry_sleep_seconds,
                sleep=sleep,
            )
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
        if got < target and not _limit_reached(pages_attempted, max_pages):
            sleep(SLEEP_BETWEEN)
    logger.info("DOC API backfill done: ~%d article records landed", got)
    return got


def backfill_master_v1(
    lander: RawLander,
    start: dt.date,
    end: dt.date,
    target: int,
    *,
    max_pages: int | None = DEFAULT_MAX_PAGES,
    session: requests.Session | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_sleep_seconds: float = DEFAULT_RETRY_SLEEP_SECONDS,
    sleep: Callable[[float], object] = time.sleep,
    dry_run: bool = False,
) -> int:
    """Deep history (1979-2016): land raw GDELT 1.0 GKG daily CSV.zip files
    verbatim. We do not parse them — Silver filters to rail/HU/AT. 'target' here
    bounds the number of daily files (each holds many thousands of records)."""
    session = session or requests.Session()
    max_pages = _normalize_optional_limit(max_pages)
    landed_files = 0
    pages_attempted = 0
    day = start
    while day < end and landed_files < target:
        if _limit_reached(pages_attempted, max_pages):
            break
        pages_attempted += 1
        # GDELT 1.0 GKG daily file naming: YYYYMMDD.gkg.csv.zip
        fname = f"{day:%Y%m%d}.gkg.csv.zip"
        url = f"http://data.gdeltproject.org/gkg/{fname}"
        if dry_run:
            logger.info("DRY RUN GKG v1 %s", url)
            day += dt.timedelta(days=1)
            continue
        try:
            r = get_with_rate_limit_retries(
                session.get,
                url,
                timeout=HTTP_TIMEOUT,
                headers=REQUEST_HEADERS,
                max_retries=max_retries,
                retry_sleep_seconds=retry_sleep_seconds,
                sleep=sleep,
            )
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
        if landed_files < target and not _limit_reached(pages_attempted, max_pages):
            sleep(SLEEP_BETWEEN)
    logger.info("GKG v1 backfill done: %d daily files landed", landed_files)
    return landed_files


def ingest(
    lander: RawLander,
    target_articles: int = DEFAULT_TARGET,
    engine: str = "doc_api",
    start: dt.date | None = None,
    end: dt.date | None = None,
    max_pages: int | None = DEFAULT_MAX_PAGES,
    dry_run: bool = False,
    session: requests.Session | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_sleep_seconds: float = DEFAULT_RETRY_SLEEP_SECONDS,
    sleep: Callable[[float], object] = time.sleep,
) -> int:
    """Entry point used by run.py or the CLI. Defaults: DOC API, 50k articles,
    last ~10y window (DOC 2.0 coverage). For deep history use engine='master_v1'."""
    if max_pages is None:
        max_pages = DEFAULT_MAX_PAGES
    if engine == "master_v1":
        start = start or dt.date(1990, 1, 1)
        end = end or dt.date(2015, 1, 1)
        return backfill_master_v1(
            lander,
            start,
            end,
            target_articles,
            max_pages=max_pages,
            session=session,
            max_retries=max_retries,
            retry_sleep_seconds=retry_sleep_seconds,
            sleep=sleep,
            dry_run=dry_run,
        )
    # doc_api default
    end = end or dt.date.today()
    start = start or (end - dt.timedelta(days=365 * 10))
    return backfill_doc_api(
        lander,
        start,
        end,
        target_articles,
        max_pages=max_pages,
        session=session,
        max_retries=max_retries,
        retry_sleep_seconds=retry_sleep_seconds,
        sleep=sleep,
        dry_run=dry_run,
    )


def _normalize_optional_limit(value: int | None) -> int | None:
    if value is None or value == 0:
        return None
    if value < 0:
        raise ValueError("limit must be non-negative")
    return value


def _limit_reached(count: int, limit: int | None) -> bool:
    return limit is not None and count >= limit


def _parse_args(argv):
    p = argparse.ArgumentParser(description="Initial historical GDELT news backfill.")
    p.add_argument("--target-articles", type=int, default=DEFAULT_TARGET,
                   help=f"stop after ~this many article records (default {DEFAULT_TARGET})")
    p.add_argument("--engine", choices=["doc_api", "master_v1"], default="doc_api")
    p.add_argument("--start", type=lambda s: dt.date.fromisoformat(s), default=None)
    p.add_argument("--end", type=lambda s: dt.date.fromisoformat(s), default=None)
    p.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="maximum DOC pages or GKG daily file attempts; use 0 for unbounded",
    )
    p.add_argument("--dry-run", action="store_true", help="log planned requests without fetching or landing")
    return p.parse_args(argv)


def main(argv=None):
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    a = _parse_args(argv if argv is not None else sys.argv[1:])
    lander = RawLander()
    n = ingest(lander, target_articles=a.target_articles, engine=a.engine,
               start=a.start, end=a.end, max_pages=a.max_pages, dry_run=a.dry_run)
    logger.info("past_recordings complete: ~%d records/files landed via %s", n, a.engine)


if __name__ == "__main__":
    main()
