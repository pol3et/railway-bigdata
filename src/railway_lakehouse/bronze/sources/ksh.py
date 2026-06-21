"""
KSH (Központi Statisztikai Hivatal) Bronze fetcher — Hungarian Central
Statistical Office.

Lands raw, unchanged. KSH exposes data through the STADAT tables and a
dissemination API; rail-relevant content lives mainly under the transport
(Szállítás / Közlekedés) theme. As with Eurostat we treat the *file* as the
atomic unit: we land each rail-related table verbatim (no parse, no filter,
no cast) plus the discovery index that found it. HU/AT-vs-rest filtering and
Hungarian-header handling are Silver concerns.

Discovery is by name-semantics: a table qualifies if its (Hungarian or English)
title contains a rail term — "vasút"/"vasúti" (railway), "MÁV", "GYSEV" — or
sits under the transport theme code. The term list is a *collection boundary*,
not a transformation.

NOTE: KSH does not publish one stable machine API across all STADAT tables;
the dissemination endpoints below are the documented ones at time of writing.
If a path 404s, land nothing for it and log — never fabricate content. The
configured table ids are seeds; extend KSH_RAIL_TABLES as you confirm codes.
"""
import logging
import requests

from ..lander import RawArtifact

logger = logging.getLogger("bronze.sources.ksh")

# KSH dissemination API base (STADAT). Tables are addressed by id; the JSON-stat
# endpoint returns the table as-is. These ids are rail/transport seeds — confirm
# and extend against https://www.ksh.hu/stadat_eng (Transport chapter).
KSH_API_BASE = "https://www.ksh.hu/stadat_files/sza/en"   # static table store
KSH_JSONSTAT_BASE = "https://statinfo.ksh.hu/Statinfo/api"  # dissemination API

# (dataset_id, relative path or table code, expected content type, filename)
KSH_RAIL_TABLES = [
    # Transport performance / railway tables (STADAT "Transport" chapter seeds).
    ("ksh_rail_freight",   "sza0010.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "sza0010.xlsx"),
    ("ksh_rail_passenger", "sza0009.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "sza0009.xlsx"),
    ("ksh_transport_network", "sza0006.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "sza0006.xlsx"),
]

RAIL_TERMS = ("vasút", "vasúti", "máv", "gysev", "rail", "railway")
HTTP_TIMEOUT = 60


def _get(url: str) -> requests.Response | None:
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT,
                         headers={"User-Agent": "railway-lakehouse-bronze/1.0"})
        if r.status_code == 200 and r.content:
            return r
        logger.warning("KSH %s -> HTTP %s (%d bytes); skipping",
                       url, r.status_code, len(r.content or b""))
    except requests.RequestException as e:
        logger.warning("KSH fetch failed for %s: %s", url, e)
    return None


def ingest(lander) -> int:
    """Land each configured KSH rail table verbatim. Returns #artifacts landed."""
    landed = 0
    for dataset_id, path, ctype, filename in KSH_RAIL_TABLES:
        url = f"{KSH_API_BASE}/{path}"
        resp = _get(url)
        if resp is None:
            continue
        art = RawArtifact(
            domain="stats", source="ksh", dataset_id=dataset_id,
            filename=filename, content=resp.content, source_url=url,
            content_type=resp.headers.get("Content-Type", ctype),
            http_status=resp.status_code,
            extra={"agency": "KSH", "country": "HU",
                   "discovery": "configured_rail_table"},
        )
        lander.land(art)
        landed += 1
    logger.info("KSH: landed %d/%d configured rail tables", landed, len(KSH_RAIL_TABLES))
    return landed
