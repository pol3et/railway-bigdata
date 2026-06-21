"""
RSS Bronze fetcher (news -- "don't miss anything" path).

GDELT is broad but not exhaustive, so we *also* poll the outlets directly.
Because rail items are sparse and you don't want to miss any, we land the
WHOLE feed unchanged on every poll -- no rail keyword filter at Bronze. The
rail filtering happens in Silver. Re-polls accumulate under ingest_date, so
items that scroll off a feed between polls are still captured historically.
"""
import logging
import requests

from ..lander import RawLander, RawArtifact
from ..config import MEDIA_FEEDS, OFFICIAL_FEEDS

logger = logging.getLogger("bronze.rss")


def _all_feeds() -> list[tuple[str, str, str]]:
    """Flatten config into (geo_outlet_id, url, geo) tuples."""
    out = []
    for registry in (MEDIA_FEEDS, OFFICIAL_FEEDS):
        for geo, outlets in registry.items():
            for name, url in outlets.items():
                out.append((f"{geo.lower()}_{name}", url, geo))
    return out


def ingest(lander: RawLander, session: requests.Session | None = None) -> list[str]:
    session = session or requests.Session()
    landed = []
    for outlet_id, url, geo in _all_feeds():
        try:
            r = session.get(url, timeout=45, headers={"User-Agent": "bronze-ingest/1.0"})
            if r.status_code != 200 or not r.content:
                logger.warning("RSS %s: HTTP %s", outlet_id, r.status_code)
                continue
            path = lander.land(RawArtifact(
                domain="news", source="rss", dataset_id=outlet_id,
                filename=f"{outlet_id}.xml", content=r.content, source_url=url,
                content_type=r.headers.get("Content-Type", "application/rss+xml"),
                http_status=r.status_code, extra={"geo": geo},
            ))
            landed.append(path)
        except Exception as exc:                        # noqa: BLE001
            logger.error("RSS fetch failed for %s (%s): %s", outlet_id, url, exc)
    logger.info("RSS: landed %d/%d feeds.", len(landed), len(_all_feeds()))
    return landed
