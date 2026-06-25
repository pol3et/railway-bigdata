import pytest

from railway_lakehouse.gold.build import aggregate_news
from railway_lakehouse.silver.news.gdelt import parse_gdelt_artlist_json
from railway_lakehouse.silver.news.rss import parse_rss_xml

pytestmark = pytest.mark.unit


def _news_row(article_id: str, published_date: str | None, *, country: str = "HU") -> dict:
    return {
        "article_id": article_id,
        "source": "rss",
        "url": f"https://example.test/{article_id}",
        "published_date": published_date,
        "language": "en",
        "is_rail_related": True,
        "country": country,
        "event_type": "investment",
        "operators": [],
        "rail_lines": [],
        "monetary_amount_eur": None,
        "monetary_raw": None,
        "summary_en": "Railway item.",
        "sentiment": "neutral",
        "confidence": 0.9,
    }


def test_gold_news_date_parsing_handles_mixed_formats(caplog):
    rows = [
        _news_row("iso-date", "2024-06-22", country="HU"),
        _news_row("gdelt-compact-t", "20240623T101500Z", country="HU"),
        _news_row("gdelt-compact", "20240624101500", country="AT"),
        _news_row("rfc-822", "Mon, 24 Jun 2024 10:30:00 +0000", country="AT"),
        _news_row("bad-date", "not-a-date", country="HU"),
        _news_row("missing-date", None, country="HU"),
    ]

    caplog.set_level("WARNING")
    frame = aggregate_news(rows)

    assert int(frame["news_article_count"].sum()) == 4
    assert set(frame["year"].astype(int)) == {2024}
    assert "failed to parse 1 published_date values" in caplog.text


def test_parse_rss_xml_skips_malformed_feeds(caplog):
    valid_xml = """
    <rss><channel><item>
      <title>Valid rail item</title>
      <link>https://example.test/valid</link>
      <pubDate>2024-06-22</pubDate>
      <description>Valid body.</description>
    </item></channel></rss>
    """
    malformed_xml = "<rss><channel><item><title>Bad feed</title>"

    caplog.set_level("WARNING")
    assert len(parse_rss_xml(valid_xml, source="valid_feed")) == 1
    assert parse_rss_xml(malformed_xml, source="bad_feed") == []
    assert "bad_feed" in caplog.text
    assert "malformed RSS XML" in caplog.text


def test_parse_gdelt_artlist_json_skips_malformed_payload(caplog):
    caplog.set_level("WARNING")

    records = parse_gdelt_artlist_json("{not-json", source="gdelt")

    assert records == []
    assert "malformed GDELT JSON" in caplog.text


def test_aggregate_news_handles_dict_with_missing_optional_fields(caplog):
    rows = [
        {
            "article_id": "partial",
            "source": "rss",
            "url": "https://example.test/partial",
            "published_date": "2024-06-22",
            "language": "en",
            "is_rail_related": True,
            "country": "HU",
            "event_type": "investment",
            "rail_lines": [],
            "monetary_raw": None,
            "summary_en": "Railway item.",
            "sentiment": "positive",
        }
    ]

    caplog.set_level("INFO")
    frame = aggregate_news(rows)

    assert frame.loc[0, "geo"] == "HU"
    assert frame.loc[0, "news_article_count"] == 1
    assert frame.loc[0, "news_total_investment_eur"] == 0
    assert "defaulted missing optional news fields" in caplog.text
