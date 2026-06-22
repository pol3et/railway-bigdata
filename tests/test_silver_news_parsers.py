import pytest

from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.news.rss import parse_rss_xml, rss_records_to_news_features

pytestmark = pytest.mark.unit


def test_parse_rss_xml_returns_article_records():
    xml = """
    <rss>
      <channel>
        <item>
          <title>Rail investment</title>
          <link>https://example.com/article</link>
          <pubDate>2026-06-22</pubDate>
          <description>Railway expansion announced.</description>
        </item>
      </channel>
    </rss>
    """

    records = parse_rss_xml(xml, source="hu_telex")

    assert len(records) == 1
    article = records[0]
    assert article.source == "hu_telex"
    assert article.title == "Rail investment"
    assert article.url == "https://example.com/article"
    assert article.published_date == "2026-06-22"
    assert article.body == "Railway expansion announced."


def test_rss_records_to_news_features_uses_existing_extraction(monkeypatch):
    xml = """
    <rss>
      <channel>
        <item>
          <title>Rail investment</title>
          <link>https://example.com/article</link>
          <pubDate>2026-06-22</pubDate>
          <description>Railway expansion announced.</description>
        </item>
      </channel>
    </rss>
    """

    records = parse_rss_xml(xml, source="hu_telex")

    def fake_generate_json(prompt, *, schema=None, system=None):
        assert "Article title: Rail investment" in prompt
        assert "Railway expansion announced." in prompt
        return {
            "is_rail_related": True,
            "country": "HU",
            "event_type": "investment",
            "operators": [],
            "rail_lines": [],
            "monetary_amount_eur": None,
            "monetary_raw": None,
            "summary_en": "Railway expansion was announced.",
            "sentiment": "positive",
            "language": "en",
            "confidence": 0.9,
        }

    monkeypatch.setattr(news_extract, "generate_json", fake_generate_json)

    features = rss_records_to_news_features(records)

    assert len(features) == 1
    feature = features[0]
    assert feature.source == "hu_telex"
    assert feature.url == "https://example.com/article"
    assert feature.country == "HU"
    assert feature.event_type == "investment"
    assert feature.summary_en == "Railway expansion was announced."
