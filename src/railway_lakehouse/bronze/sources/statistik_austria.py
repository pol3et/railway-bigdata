"""
Statistik Austria Bronze fetcher — Austrian federal statistics.

Lands raw, unchanged. Statistik Austria publishes open data through its
OGD (Open Government Data) portal and an OGD JSON API (data.statistik.gv.at),
where each dataset has a stable id and a machine-readable JSON-stat payload
plus CSV resources. Rail-relevant datasets live under transport (Verkehr).

Same contract as the other stats fetchers: the dataset file is the atomic
unit, landed verbatim; German-header handling and geo filtering are Silver's
job. Discovery is by name-semantics — "Bahn", "Schiene"/"Schienen", "ÖBB",
"Eisenbahn" — used purely as a collection boundary.

NOTE: OGD dataset ids must be confirmed against
https://data.statistik.gv.at (Verkehr theme). The ids below are rail/transport
seeds; extend STAT_RAIL_DATASETS as you verify them. Never fabricate content:
if an id 404s, log and skip.
"""
import logging
import requests

from ..lander import RawArtifact

logger = logging.getLogger("bronze.sources.statistik_austria")

# OGD JSON API. A dataset is addressed as {BASE}/{dataset_id}; the portal also
# serves CSV resources under a documents path. We land the JSON-stat dataset
# verbatim (and, if present, its CSV resource).
STAT_OGD_BASE = "https://data.statistik.gv.at/ogd/json"
STAT_OGD_DOCS = "https://data.statistik.gv.at/data"

# (dataset_id, ogd_id, filename) — rail/transport seeds (Verkehr).
STAT_RAIL_DATASETS = [
    ("stat_at_rail_transport", "OGD_verkehr_ein_VERK_1", "OGD_verkehr_ein_VERK_1.json"),
    ("stat_at_rail_freight",   "OGD_verkehr_gut_GUET_1", "OGD_verkehr_gut_GUET_1.json"),
]

RAIL_TERMS = ("bahn", "schiene", "schienen", "öbb", "oebb", "eisenbahn", "rail")
HTTP_TIMEOUT = 60


def _get(url: str) -> requests.Response | None:
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT,
                         headers={"User-Agent": "railway-lakehouse-bronze/1.0"})
        if r.status_code == 200 and r.content:
            return r
        logger.warning("StatAustria %s -> HTTP %s (%d bytes); skipping",
                       url, r.status_code, len(r.content or b""))
    except requests.RequestException as e:
        logger.warning("StatAustria fetch failed for %s: %s", url, e)
    return None


def ingest(lander) -> int:
    """Land each configured Statistik Austria rail dataset (JSON + CSV if any)."""
    landed = 0
    for dataset_id, ogd_id, filename in STAT_RAIL_DATASETS:
        # 1) JSON-stat dataset
        json_url = f"{STAT_OGD_BASE}/{ogd_id}"
        resp = _get(json_url)
        if resp is not None:
            lander.land(RawArtifact(
                domain="stats", source="statistik_austria", dataset_id=dataset_id,
                filename=filename, content=resp.content, source_url=json_url,
                content_type=resp.headers.get("Content-Type", "application/json"),
                http_status=resp.status_code,
                extra={"agency": "Statistik Austria", "country": "AT",
                       "ogd_id": ogd_id, "resource": "jsonstat"},
            ))
            landed += 1
        # 2) CSV resource (verbatim) if the portal serves one for this id
        csv_url = f"{STAT_OGD_DOCS}/{ogd_id}.csv"
        csv_resp = _get(csv_url)
        if csv_resp is not None:
            lander.land(RawArtifact(
                domain="stats", source="statistik_austria",
                dataset_id=dataset_id, filename=f"{ogd_id}.csv",
                content=csv_resp.content, source_url=csv_url,
                content_type=csv_resp.headers.get("Content-Type", "text/csv"),
                http_status=csv_resp.status_code,
                extra={"agency": "Statistik Austria", "country": "AT",
                       "ogd_id": ogd_id, "resource": "csv"},
            ))
            landed += 1
    logger.info("Statistik Austria: landed %d artifacts across %d datasets",
                landed, len(STAT_RAIL_DATASETS))
    return landed
