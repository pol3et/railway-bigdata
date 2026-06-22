"""
Statistik Austria Bronze fetcher — Austrian federal statistics.

Lands raw, unchanged. German-header handling and geo filtering are Silver's
job; here a resource file is the atomic unit, landed verbatim.

2026-06-22 refresh — what was wrong and what is true
----------------------------------------------------
The previous configuration produced "HTTP 200 / 0 bytes" for two reasons:

  1. Wrong API shape. The OGD JSON API is addressed by a QUERY parameter:
         https://data.statistik.gv.at/ogd/json?dataset=<OGD_ID>      (correct)
     not by a path segment (.../ogd/json/<OGD_ID>), which the portal answers
     with HTTP 200 and an EMPTY body. So a status-code check is not enough — an
     empty 200 must count as failure (see is_valid_artifact_response).
  2. Fictional ids. `OGD_verkehr_ein_VERK_1` / `OGD_verkehr_gut_GUET_1` do not
     exist in the OGD catalogue.

Crucially, Statistik Austria's OGD JSON/CSV portal has **no rail dataset**.
The full catalogue (~315 datasets, checked 2026-06-22) carries only road
(`OGD_gvk_*`), inland-waterway (`OGD_gvd_*`) and road-accident
(`OGDEXT_UNFALLSRV_*`) transport data. Rail open data is published elsewhere:

  * statistik.at file downloads (.ods), e.g. Schienengüterverkehr — these are
    the openly fetchable rail artifacts and are what we land below;
  * STATcube "opendatabase" (ids `desgv_daten_international`, `desgv_daten`)
    which requires an interactive login, so it is NOT usable by an unattended
    Bronze collector (documented, not seeded).

The OGD JSON/CSV helpers below are kept (with the corrected query-param shape)
so that if Statistik Austria ever publishes a rail OGD dataset it can be added
to STAT_RESOURCES with kind="ogd_json"/"ogd_csv" and works immediately.
"""
import logging
from dataclasses import dataclass

import requests

from ..lander import RawArtifact

logger = logging.getLogger("bronze.sources.statistik_austria")

# OGD JSON/CSV API (correct shapes). Kept for future rail OGD datasets.
STAT_OGD_JSON = "https://data.statistik.gv.at/ogd/json"   # ?dataset=<OGD_ID>
STAT_OGD_DATA = "https://data.statistik.gv.at/data"        # /<OGD_ID>.csv

HTTP_TIMEOUT = 60
RAIL_TERMS = ("bahn", "schiene", "schienen", "öbb", "oebb", "eisenbahn", "rail")


@dataclass(frozen=True)
class StatResource:
    """One openly-fetchable Statistik Austria rail resource, landed verbatim."""
    dataset_id: str
    url: str
    filename: str
    content_type: str
    kind: str           # "ods" | "ogd_json" | "ogd_csv"
    note: str = ""


def ogd_json_url(ogd_id: str) -> str:
    """Correct OGD JSON metadata URL (query param, not path segment)."""
    return f"{STAT_OGD_JSON}?dataset={ogd_id}"


def ogd_csv_url(ogd_id: str) -> str:
    """Correct OGD primary-CSV URL for a dataset id."""
    return f"{STAT_OGD_DATA}/{ogd_id}.csv"


# Openly fetchable rail resources, verified live 2026-06-22.
# NOTE: statistik.at embeds the reporting year in the .ods filename; bump it
# when the next annual file is published (see STATcube/auth note in the header).
_ODS = "application/vnd.oasis.opendocument.spreadsheet"
STAT_RAIL_RESOURCES = [
    StatResource(
        dataset_id="stat_at_rail_freight",
        url="https://www.statistik.at/fileadmin/pages/86/"
            "Schienengueterverkehr_nach_Verkehrsbereich_2025.ods",
        filename="Schienengueterverkehr_nach_Verkehrsbereich_2025.ods",
        content_type=_ODS, kind="ods",
        note="Rail freight by transport segment (Verkehrsbereich); "
             "Schienenverkehrsstatistik. 2025: 96.2 Mt, 21.5 bn tonne-km. "
             "-> rail_freight_tonnes, rail_freight_tonne_km",
    ),
    # Rolling stock (Schienenfahrzeuge), 4 files; total fleet 2024 = 20,863.
    StatResource(
        dataset_id="stat_at_rail_locomotives",
        url="https://www.statistik.at/fileadmin/pages/79/"
            "Lokomotivbestaende_2023_und_2024.ods",
        filename="Lokomotivbestaende_2023_und_2024.ods",
        content_type=_ODS, kind="ods",
        note="Locomotive stock -> rail_rolling_stock (locomotives).",
    ),
    StatResource(
        dataset_id="stat_at_rail_railcars",
        url="https://www.statistik.at/fileadmin/pages/79/"
            "Schienentriebfahrzeugbestaende_2023_und_2024.ods",
        filename="Schienentriebfahrzeugbestaende_2023_und_2024.ods",
        content_type=_ODS, kind="ods",
        note="Railcars / multiple units -> rail_rolling_stock (railcars).",
    ),
    StatResource(
        dataset_id="stat_at_rail_freight_wagons",
        url="https://www.statistik.at/fileadmin/pages/79/"
            "Schienengueterwaegenbestaende_2023_und_2024.ods",
        filename="Schienengueterwaegenbestaende_2023_und_2024.ods",
        content_type=_ODS, kind="ods",
        note="Freight wagon stock -> rail_rolling_stock (freight wagons).",
    ),
    StatResource(
        dataset_id="stat_at_rail_passenger_carriages",
        url="https://www.statistik.at/fileadmin/pages/79/"
            "Personenwaegenbestaende_2023_und_2024.ods",
        filename="Personenwaegenbestaende_2023_und_2024.ods",
        content_type=_ODS, kind="ods",
        note="Passenger carriage stock -> rail_rolling_stock (carriages).",
    ),
]

# Known rail data that exists but is NOT unattended-fetchable; recorded so the
# limitation is auditable rather than retried blindly.
STAT_RAIL_ACCESS_NOTES = {
    "statcube_rail_freight": "STATcube opendatabase id 'desgv_daten_international' "
                             "(and historical 'desgv_daten') — requires login.",
    "rail_passenger": "Personenverkehr Schiene is published only as STATcube "
                      "tables/PDF (no .ods/OGD download); 2024 = 351.4M passengers. "
                      "Use Eurostat for rail_passengers / rail_passenger_km (AT).",
    "rail_network_length": "Rail network length (track-km, electrified) is not an "
                           "openly fetchable file; only in the Verkehrsstatistik "
                           "PDF. Use Eurostat for rail_network_length_km (AT).",
    "ogd_portal": "data.statistik.gv.at OGD has no rail dataset (full catalogue "
                  "checked 2026-06-22): only road (gvk_*), inland-waterway "
                  "(gvd_*) and road accidents.",
}


def is_valid_artifact_response(status: int, content: bytes | None) -> bool:
    """A landable response: HTTP 200 with a non-empty body.

    The headline failure this guards against is the portal answering HTTP 200
    with ZERO bytes (wrong URL shape / missing dataset). An empty 200 is a
    failure, never a success.
    """
    return status == 200 and bool(content)


def ingest(lander, session: requests.Session | None = None) -> int:
    """Land each confirmed Statistik Austria rail resource verbatim."""
    session = session or requests.Session()
    landed = 0
    for res in STAT_RAIL_RESOURCES:
        try:
            r = session.get(
                res.url, timeout=HTTP_TIMEOUT,
                headers={"User-Agent": "railway-lakehouse-bronze/1.0"},
            )
        except requests.RequestException as e:
            logger.warning("StatAustria fetch failed for %s (%s): %s",
                           res.dataset_id, res.url, e)
            continue

        if not is_valid_artifact_response(r.status_code, r.content):
            logger.warning(
                "StatAustria %s -> HTTP %s, %d bytes; skipping (empty/!=200)",
                res.dataset_id, r.status_code, len(r.content or b""))
            continue

        lander.land(RawArtifact(
            domain="stats", source="statistik_austria", dataset_id=res.dataset_id,
            filename=res.filename, content=r.content, source_url=res.url,
            content_type=r.headers.get("Content-Type", res.content_type),
            http_status=r.status_code,
            extra={"agency": "Statistik Austria", "country": "AT",
                   "resource_kind": res.kind, "note": res.note},
        ))
        landed += 1
    logger.info("Statistik Austria: landed %d/%d rail resources",
                landed, len(STAT_RAIL_RESOURCES))
    return landed
