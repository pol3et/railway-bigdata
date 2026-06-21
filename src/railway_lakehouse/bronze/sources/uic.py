"""
UIC (International Union of Railways) Bronze fetcher.

UIC maintains railway statistics through its statistics portal
(uic-stats.uic.org) and publishes datasets/leaflets. Unlike Eurostat there is
no single open JSON-stat API across every series, so this fetcher lands the
file resources we can address verbatim: the published statistics
files/exports for the countries in scope.

Contract identical to the other stats fetchers: the file is the atomic unit,
landed unchanged; cross-country reconciliation and HU/AT extraction are Silver
concerns. UIC is the one source that is *natively* cross-country, so we do NOT
restrict it to HU/AT at Bronze — we land the whole release and let Silver slice.

NOTE: UIC resource URLs change with each release. The seeds below are the
documented statistics exports; confirm against https://uic-stats.uic.org and
extend UIC_RESOURCES. Never fabricate content: 404 -> log and skip.
"""
import logging
import requests

from ..lander import RawArtifact

logger = logging.getLogger("bronze.sources.uic")

UIC_STATS_BASE = "https://uic-stats.uic.org/select"   # data-export endpoint
UIC_FILES_BASE = "https://uic.org/IMG/xls"            # published leaflet/xls store

# (dataset_id, url, filename, content_type) — railway statistics exports.
# These are seeds for the key UIC series (infrastructure, traffic, rolling stock).
UIC_RESOURCES = [
    ("uic_railway_statistics_synopsis",
     "https://uic.org/IMG/xls/uic_railway_statistics_synopsis.xls",
     "uic_railway_statistics_synopsis.xls",
     "application/vnd.ms-excel"),
    ("uic_passenger_traffic",
     "https://uic.org/IMG/xls/passenger_traffic.xls",
     "uic_passenger_traffic.xls",
     "application/vnd.ms-excel"),
    ("uic_freight_traffic",
     "https://uic.org/IMG/xls/freight_traffic.xls",
     "uic_freight_traffic.xls",
     "application/vnd.ms-excel"),
]

HTTP_TIMEOUT = 90


def _get(url: str) -> requests.Response | None:
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT,
                         headers={"User-Agent": "railway-lakehouse-bronze/1.0"})
        if r.status_code == 200 and r.content:
            return r
        logger.warning("UIC %s -> HTTP %s (%d bytes); skipping",
                       url, r.status_code, len(r.content or b""))
    except requests.RequestException as e:
        logger.warning("UIC fetch failed for %s: %s", url, e)
    return None


def ingest(lander) -> int:
    """Land each configured UIC statistics resource verbatim (all countries)."""
    landed = 0
    for dataset_id, url, filename, ctype in UIC_RESOURCES:
        resp = _get(url)
        if resp is None:
            continue
        lander.land(RawArtifact(
            domain="stats", source="uic", dataset_id=dataset_id,
            filename=filename, content=resp.content, source_url=url,
            content_type=resp.headers.get("Content-Type", ctype),
            http_status=resp.status_code,
            extra={"agency": "UIC", "scope": "international",
                   "note": "cross-country; not HU/AT-filtered at Bronze"},
        ))
        landed += 1
    logger.info("UIC: landed %d/%d configured resources", landed, len(UIC_RESOURCES))
    return landed
