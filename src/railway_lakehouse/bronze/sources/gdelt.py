"""
GDELT Bronze fetcher (news -- broad coverage path).

GDELT already monitors thousands of outlets per country in 100+ languages
and machine-translates them, so a sourcecountry-restricted rail query is the
widest practical net for "all popular media in HU/AT". We OR together rail
terms across EN/HU/DE to maximise recall on a sparse topic, restrict to the
source country, and land the raw JSON article lists unchanged.

Weekly run uses the GDELT 2.0 DOC API (realtime, last 5 years). The deep
1979->2014 backfill comes from GDELT 1.0 yearly files via a separate one-off
job (not included here) -- different schema, handled at Silver.
"""
import logging
import time
from collections.abc import Callable

import requests

from ..lander import RawLander, RawArtifact
from ..config import NATIONAL_SCOPE, RAIL_TERMS
from .gdelt_common import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_SLEEP_SECONDS,
    DOC_API,
    DOC_API_MAX_RECORDS,
    REQUEST_HEADERS,
    bounded_max_records,
    get_with_rate_limit_retries,
)

logger = logging.getLogger("bronze.gdelt")


def build_query(geo: str) -> str:
    """Pure: OR all multilingual rail terms, restrict to a source country."""
    terms = RAIL_TERMS["en"] + RAIL_TERMS["hu"] + RAIL_TERMS["de"]
    # GDELT quotes multi-word/diacritic terms; single tokens are fine bare.
    or_block = " OR ".join(sorted(set(terms)))
    return f"({or_block}) sourcecountry:{geo}"


def build_doc_params(
    geo: str,
    *,
    timespan: str = "1w",
    max_records: int = DOC_API_MAX_RECORDS,
) -> dict:
    return {
        "query": build_query(geo),
        "mode": "ArtList",
        "format": "json",
        "timespan": timespan,
        "maxrecords": bounded_max_records(max_records),
        "sort": "datedesc",
    }


def ingest(
    lander: RawLander,
    session: requests.Session | None = None,
    timespan: str = "1w",
    max_records: int = DOC_API_MAX_RECORDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_sleep_seconds: float = DEFAULT_RETRY_SLEEP_SECONDS,
    sleep: Callable[[float], object] = time.sleep,
) -> list[str]:
    session = session or requests.Session()
    landed = []
    for geo in NATIONAL_SCOPE:
        params = build_doc_params(geo, timespan=timespan, max_records=max_records)
        try:
            r = get_with_rate_limit_retries(
                session.get,
                DOC_API,
                params=params,
                timeout=60,
                headers=REQUEST_HEADERS,
                max_retries=max_retries,
                retry_sleep_seconds=retry_sleep_seconds,
                sleep=sleep,
            )
            if r.status_code != 200 or not r.content:
                logger.warning("GDELT %s: HTTP %s", geo, r.status_code)
                continue
            ts = params["timespan"]
            path = lander.land(RawArtifact(
                domain="news", source="gdelt", dataset_id=geo,
                filename=f"gdelt_doc_{geo}_{ts}.json", content=r.content,
                source_url=r.url, content_type="application/json",
                http_status=r.status_code,
                extra={"query": params["query"], "timespan": ts},
            ))
            landed.append(path)
        except Exception as exc:                        # noqa: BLE001
            logger.error("GDELT fetch failed for %s: %s", geo, exc)
    logger.info("GDELT: landed %d country pulls.", len(landed))
    return landed
