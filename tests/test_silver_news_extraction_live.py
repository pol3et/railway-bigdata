import logging

import pytest

from railway_lakehouse.silver.config import NEWS_EVENT_TYPES
from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.ollama_client import health_check
from railway_lakehouse.silver.schema import NewsFeature


pytestmark = pytest.mark.live

logger = logging.getLogger(__name__)


def test_extract_article_live_real_rss_sample():
    """Live smoke test for the real Ollama -> NewsFeature path."""
    if not health_check():
        pytest.skip("Ollama qwen3:4b server not reachable")

    feature = news_extract.extract_article(
        article_id="gap033-live-smoke-001",
        source="rss_test",
        url="https://example.com/gap033-live-smoke",
        title="Hungarian railway track modernization announced",
        body=(
            "MAV, Hungary's national railway operator, announced a railway "
            "track modernization plan for the Budapest-Debrecen corridor. "
            "The article says the project includes rail service reliability "
            "upgrades, safety work, and cross-border corridor coordination "
            "with Austrian railway partners."
        ),
        published_date="2026-06-25",
    )

    assert feature is not None, "Extraction should succeed for a clear rail article"
    assert isinstance(feature, NewsFeature)
    assert feature.article_id == "gap033-live-smoke-001"
    assert feature.source == "rss_test"
    assert feature.url == "https://example.com/gap033-live-smoke"

    assert feature.is_rail_related is True
    assert feature.event_type in NEWS_EVENT_TYPES
    assert feature.country in ("HU", "AT", "other", None)
    assert feature.summary_en is not None
    assert len(feature.summary_en.strip()) > 5
    assert feature.confidence is None or 0.0 <= feature.confidence <= 1.0
    assert isinstance(feature.operators, list)
    assert isinstance(feature.rail_lines, list)

    logger.info("Extracted live NewsFeature: %s", feature)
