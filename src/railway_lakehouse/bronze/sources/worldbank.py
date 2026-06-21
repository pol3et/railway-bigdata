"""
World Bank Bronze fetcher.

Same enumerate-by-name idea against the World Bank indicator catalogue:
page through /v2/indicator, keep any whose name/note mentions rail, then
land the full time series (all countries, all years) as RAW JSON.

We request all countries deliberately -- the dataset is landed whole and
unchanged; the HU/AT focus is applied later in Silver. World Bank reaches
back to 1960, which helps cover Hungary in the pre-EU 1980s.
"""
import logging
import requests

from ..lander import RawLander, RawArtifact

logger = logging.getLogger("bronze.worldbank")

CATALOGUE_URL = "https://api.worldbank.org/v2/indicator?format=json&per_page=20000"
SERIES_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/{indicator}"
    "?format=json&per_page=20000"
)

# Known rail indicator family, used as a fallback if catalogue discovery is
# throttled. Discovery (below) is the primary path.
KNOWN_RAIL_INDICATORS = ["IS.RRS.TOTL.KM", "IS.RRS.GOOD.MT.K6", "IS.RRS.PASG.KM"]


def discover_rail_indicators(catalogue_json: list) -> list[str]:
    """Pure: extract indicator ids whose name/sourceNote mentions rail.

    catalogue_json is the parsed World Bank response: [meta, [indicators...]].
    """
    if not catalogue_json or len(catalogue_json) < 2 or not catalogue_json[1]:
        return list(KNOWN_RAIL_INDICATORS)
    ids = []
    for ind in catalogue_json[1]:
        text = f"{ind.get('name','')} {ind.get('sourceNote','')}".lower()
        if "rail" in text:
            ids.append(ind["id"])
    # union with the known family so we never regress
    return sorted(set(ids) | set(KNOWN_RAIL_INDICATORS))


def ingest(lander: RawLander, session: requests.Session | None = None) -> list[str]:
    session = session or requests.Session()

    # 1) land + parse the indicator catalogue
    cat = session.get(CATALOGUE_URL, timeout=120)
    cat.raise_for_status()
    lander.land(RawArtifact(
        domain="stats", source="worldbank", dataset_id="_catalogue_indicators",
        filename="indicators.json", content=cat.content,
        source_url=CATALOGUE_URL, content_type="application/json",
        http_status=cat.status_code,
    ))
    try:
        indicators = discover_rail_indicators(cat.json())
    except Exception:                                   # noqa: BLE001
        indicators = list(KNOWN_RAIL_INDICATORS)
    logger.info("World Bank: %d rail indicators to pull.", len(indicators))

    # 2) land each indicator's full series as raw JSON
    landed = []
    for ind in indicators:
        url = SERIES_URL.format(indicator=ind)
        try:
            r = session.get(url, timeout=120)
            if r.status_code != 200 or not r.content:
                logger.warning("Skipping %s (HTTP %s)", ind, r.status_code)
                continue
            path = lander.land(RawArtifact(
                domain="stats", source="worldbank", dataset_id=ind,
                filename=f"{ind}.json", content=r.content, source_url=url,
                content_type="application/json", http_status=r.status_code,
            ))
            landed.append(path)
        except Exception as exc:                        # noqa: BLE001
            logger.error("World Bank fetch failed for %s: %s", ind, exc)
    logger.info("World Bank: landed %d/%d indicators.", len(landed), len(indicators))
    return landed
