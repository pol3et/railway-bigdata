"""
UIC (International Union of Railways) Bronze fetcher.

UIC maintains railway statistics through RAILISA (uic-stats.uic.org). The
interactive CSV/Excel download and REST surfaces require annual access or
authentication, so this fetcher lands only the current public statistical
publications that can be addressed without credentials.

Contract identical to the other stats fetchers: each publication is the atomic
raw unit and is landed unchanged. Cross-country reconciliation, HU/AT
extraction, and PDF/XLS parsing remain Silver concerns.
"""
import logging
from dataclasses import dataclass

import requests

from ..lander import RawArtifact

logger = logging.getLogger("bronze.sources.uic")

HTTP_TIMEOUT = 90
PDF_MAGIC = b"%PDF-"
RAILISA_ACCESS_NOTE = (
    "RAILISA bulk CSV/Excel downloads and REST API access require annual "
    "access/subscription or authentication; this Bronze source lands only "
    "public free publication PDFs."
)


@dataclass(frozen=True)
class UicResource:
    """A public UIC statistical publication to land verbatim."""

    dataset_id: str
    url: str
    filename: str
    title: str
    publication_year: int
    feature_hint: str
    expected_format: str = "pdf"
    access_level: str = "public_free_pdf"


UIC_PUBLIC_RESOURCES = [
    UicResource(
        dataset_id="uic_traffic_trends_2024",
        url="https://uic-stats.uic.org/resources/help_resource/?id=12",
        filename="uic_traffic_trends_2024.pdf",
        title="Traffic Trends Among UIC Member Companies in 2024",
        publication_year=2024,
        feature_hint="rail_passenger_km, rail_freight_tonne_km, regional trend context",
    ),
    UicResource(
        dataset_id="uic_railway_statistics_synopsis_2025",
        url="https://uic-stats.uic.org/resources/help_resource/?id=14",
        filename="uic_railway_statistics_synopsis_2025.pdf",
        title="Railway Statistics Synopsis - Edition 2025",
        publication_year=2025,
        feature_hint=(
            "rail_network_length_km, rail_electrified_km, rail_passenger_km, "
            "rail_freight_tonne_km, rail_rolling_stock, rail_employees"
        ),
    ),
]

# Backward-compatible name for docs/tests that refer to generic UIC resources.
UIC_RESOURCES = UIC_PUBLIC_RESOURCES


def looks_like_pdf(content: bytes | None) -> bool:
    """Return true when bytes look like a PDF document."""

    return bool(content and content.startswith(PDF_MAGIC))


def is_valid_resource_response(status: int, content: bytes | None, expected_format: str) -> bool:
    """A landable UIC resource response for the configured public format."""

    if status != 200 or not content:
        return False
    if expected_format == "pdf":
        return looks_like_pdf(content)
    return False


def _get_resource(session: requests.Session, resource: UicResource) -> requests.Response | None:
    try:
        response = session.get(
            resource.url,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": "railway-lakehouse-bronze/1.0"},
        )
    except requests.RequestException as e:
        logger.warning("UIC fetch failed for %s (%s): %s", resource.dataset_id, resource.url, e)
        return None

    if is_valid_resource_response(response.status_code, response.content, resource.expected_format):
        return response

    logger.warning(
        "UIC %s -> HTTP %s, %d bytes, %s=%s; skipping",
        resource.dataset_id,
        response.status_code,
        len(response.content or b""),
        resource.expected_format,
        looks_like_pdf(response.content) if resource.expected_format == "pdf" else "unsupported",
    )
    return None


def ingest(lander, session: requests.Session | None = None) -> int:
    """Land each configured public UIC statistics resource verbatim."""

    session = session or requests.Session()
    landed = 0
    for resource in UIC_PUBLIC_RESOURCES:
        response = _get_resource(session, resource)
        if response is None:
            continue
        lander.land(
            RawArtifact(
                domain="stats",
                source="uic",
                dataset_id=resource.dataset_id,
                filename=resource.filename,
                content=response.content,
                source_url=resource.url,
                content_type=response.headers.get("Content-Type", "application/pdf"),
                http_status=response.status_code,
                extra={
                    "agency": "UIC",
                    "scope": "international",
                    "publication_title": resource.title,
                    "publication_year": resource.publication_year,
                    "feature_hint": resource.feature_hint,
                    "source_format": resource.expected_format,
                    "access_level": resource.access_level,
                    "discovery": "railisa_public_resource",
                    "railisa_access_note": RAILISA_ACCESS_NOTE,
                },
            )
        )
        landed += 1
    logger.info("UIC: landed %d/%d configured public resources", landed, len(UIC_PUBLIC_RESOURCES))
    return landed
