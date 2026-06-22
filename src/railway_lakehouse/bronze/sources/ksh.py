"""
KSH (Kozponti Statisztikai Hivatal) Bronze fetcher - Hungarian Central
Statistical Office.

Lands raw, unchanged. KSH publishes each STADAT table as a static XLSX under a
stable per-table URL:

    https://www.ksh.hu/stadat_files/sza/en/<code>.xlsx

As with Eurostat, the file is the atomic unit: each rail-related table is
landed verbatim with provenance. HU-only scope and Hungarian-header handling
remain Silver concerns.

The seed list is curated by STADAT code, not by blind keyword discovery. The
transport chapter mixes road, water, air, and rail in adjacent codes, so a code
must be checked against its published title before it is trusted.
"""
import io
import logging
import zipfile
from dataclasses import dataclass

import requests

from ..lander import RawArtifact

logger = logging.getLogger("bronze.sources.ksh")

KSH_API_BASE = "https://www.ksh.hu/stadat_files/sza/en"
HTTP_TIMEOUT = 60

# XLSX is a ZIP container. HTML error pages or empty HTTP-200 bodies will not
# have this header or the workbook members checked below.
XLSX_MAGIC = b"PK\x03\x04"
XLSX_REQUIRED_MEMBERS = ("[Content_Types].xml", "_rels/.rels")


@dataclass(frozen=True)
class KshTable:
    """A confirmed KSH STADAT table to land verbatim."""

    dataset_id: str
    code: str
    title: str
    feature_hint: str

    @property
    def url(self) -> str:
        return f"{KSH_API_BASE}/{self.code}.xlsx"

    @property
    def filename(self) -> str:
        return f"{self.code}.xlsx"


# Rail or rail-bearing annual STADAT tables verified against the published
# English STADAT title.
KSH_RAIL_TABLES = [
    KshTable(
        "ksh_rail_freight",
        "sza0009",
        "Rail goods transport by direction of traffic",
        "rail_freight_tonnes, rail_freight_tonne_km",
    ),
    KshTable(
        "ksh_rail_passenger",
        "sza0016",
        "Interurban passenger transport by mode of transport",
        "rail_passengers, rail_passenger_km (the train column)",
    ),
    KshTable(
        "ksh_rail_rolling_stock",
        "sza0028",
        "Rolling stock of public railways",
        "rail_rolling_stock",
    ),
    KshTable(
        "ksh_rail_network",
        "sza0030",
        "Road and rail network",
        "rail_network_length_km, rail_electrified_km",
    ),
    KshTable(
        "ksh_rail_lines_regional",
        "sza0041",
        "Length of railway lines by county and region",
        "rail_network_length_km (regional breakdown)",
    ),
    KshTable(
        "ksh_rail_narrow_gauge",
        "sza0071",
        "Narrow gauge railway lines",
        "rail_network_length_km, rail_passengers (narrow gauge)",
    ),
]

# Audit trail of codes removed in the 2026-06-22 correction.
KSH_RETIRED_SEEDS = {
    "sza0010": (
        "was ksh_rail_freight -> actually Inland waterway transport of goods "
        "by insignia of vessel (not rail)"
    ),
    "sza0006": (
        "was ksh_transport_network -> actually National road goods transport "
        "by sector classification (not rail)"
    ),
    "sza0009_passenger": (
        "sza0009 was mislabelled ksh_rail_passenger; it is rail goods and is "
        "now ksh_rail_freight"
    ),
}


def looks_like_xlsx(content: bytes | None) -> bool:
    """Return true when bytes look like an XLSX workbook container."""

    if not content or content[:4] != XLSX_MAGIC:
        return False

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as workbook:
            if workbook.testzip() is not None:
                return False
            members = set(workbook.namelist())
    except zipfile.BadZipFile:
        return False

    return all(member in members for member in XLSX_REQUIRED_MEMBERS) and any(
        member.startswith("xl/") for member in members
    )


def is_valid_table_response(status: int, content: bytes | None) -> bool:
    """A landable KSH response: HTTP 200 with non-empty XLSX bytes."""

    return status == 200 and looks_like_xlsx(content)


def ingest(lander, session: requests.Session | None = None) -> int:
    """Land each confirmed KSH rail table verbatim. Returns artifact count."""

    session = session or requests.Session()
    landed = 0
    for table in KSH_RAIL_TABLES:
        try:
            response = session.get(
                table.url,
                timeout=HTTP_TIMEOUT,
                headers={"User-Agent": "railway-lakehouse-bronze/1.0"},
            )
        except requests.RequestException as exc:
            logger.warning("KSH fetch failed for %s (%s): %s", table.code, table.dataset_id, exc)
            continue

        if not is_valid_table_response(response.status_code, response.content):
            logger.warning(
                "KSH %s (%s) -> HTTP %s, %d bytes, xlsx=%s; skipping",
                table.code,
                table.dataset_id,
                response.status_code,
                len(response.content or b""),
                looks_like_xlsx(response.content),
            )
            continue

        lander.land(
            RawArtifact(
                domain="stats",
                source="ksh",
                dataset_id=table.dataset_id,
                filename=table.filename,
                content=response.content,
                source_url=table.url,
                content_type=response.headers.get(
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                http_status=response.status_code,
                extra={
                    "agency": "KSH",
                    "country": "HU",
                    "stadat_code": table.code,
                    "stadat_title": table.title,
                    "feature_hint": table.feature_hint,
                    "discovery": "curated_rail_table",
                },
            )
        )
        landed += 1

    logger.info("KSH: landed %d/%d confirmed rail tables", landed, len(KSH_RAIL_TABLES))
    return landed
