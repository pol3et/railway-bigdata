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
import requests

from ..lander import RawLander, RawArtifact
from ..config import NATIONAL_SCOPE, RAIL_TERMS

logger = logging.getLogger("bronze.gdelt")

DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


def build_query(geo: str) -> str:
    """Pure: OR all multilingual rail terms, restrict to a source country."""
    terms = RAIL_TERMS["en"] + RAIL_TERMS["hu"] + RAIL_TERMS["de"]
    # GDELT quotes multi-word/diacritic terms; single tokens are fine bare.
    or_block = " OR ".join(sorted(set(terms)))
    return f"({or_block}) sourcecountry:{geo}"


def ingest(lander: RawLander, session: requests.Session | None = None,
           timespan: str = "1w") -> list[str]:
    session = session or requests.Session()
    landed = []
    for geo in NATIONAL_SCOPE:
        params = {
            "query": build_query(geo),
            "mode": "ArtList",
            "format": "json",
            "timespan": timespan,
            "maxrecords": 250,
            "sort": "datedesc",
        }
        try:
            r = session.get(DOC_API, params=params, timeout=60)
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
