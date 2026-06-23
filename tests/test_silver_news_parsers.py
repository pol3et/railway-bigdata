import pytest

from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.news.gdelt import parse_gdelt_artlist_json
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


def test_parse_rss_xml_prefers_full_content_over_description():
    xml = """
    <rss xmlns:content="http://purl.org/rss/1.0/modules/content/">
      <channel>
        <item>
          <title>Rail upgrade</title>
          <link>https://example.com/article</link>
          <pubDate>2026-06-22</pubDate>
          <description>Short teaser.</description>
          <content:encoded>Full article text about a railway upgrade.</content:encoded>
        </item>
      </channel>
    </rss>
    """

    records = parse_rss_xml(xml, source="hu_telex")

    assert records[0].body == "Full article text about a railway upgrade."


def test_parse_rss_xml_assigns_unique_ids_without_urls():
    xml = """
    <rss>
      <channel>
        <item>
          <title>First rail item</title>
          <pubDate>2026-06-22</pubDate>
          <description>First body.</description>
        </item>
        <item>
          <title>Second rail item</title>
          <pubDate>2026-06-22</pubDate>
          <description>Second body.</description>
        </item>
      </channel>
    </rss>
    """

    records = parse_rss_xml(xml, source="hu_telex")
    reparsed = parse_rss_xml(xml, source="hu_telex")

    assert records[0].article_id
    assert records[1].article_id
    assert records[0].article_id != records[1].article_id
    assert [r.article_id for r in records] == [r.article_id for r in reparsed]


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


def test_article_records_to_news_features_supports_gdelt_records(monkeypatch):
    payload = """
    {
      "articles": [
        {
          "title": "Rail disruption in Austria",
          "url": "https://example.com/gdelt-article",
          "seendate": "20260622T120000Z",
          "snippet": "Rail services were disrupted."
        }
      ]
    }
    """
    records = parse_gdelt_artlist_json(payload)

    def fake_generate_json(prompt, *, schema=None, system=None):
        assert "Article title: Rail disruption in Austria" in prompt
        assert "Rail services were disrupted." in prompt
        return {
            "is_rail_related": True,
            "country": "AT",
            "event_type": "delay",
            "operators": [],
            "rail_lines": [],
            "monetary_amount_eur": None,
            "monetary_raw": None,
            "summary_en": "Rail services were disrupted.",
            "sentiment": "negative",
            "language": "en",
            "confidence": 0.8,
        }

    monkeypatch.setattr(news_extract, "generate_json", fake_generate_json)

    features = news_extract.article_records_to_news_features(records)

    assert len(features) == 1
    feature = features[0]
    assert feature.source == "gdelt"
    assert feature.country == "AT"
    assert feature.event_type == "delay"


def test_parse_gdelt_artlist_json_returns_article_records():
    payload = """
    {
      "articles": [
        {
          "title": "Rail disruption in Austria",
          "url": "https://example.com/gdelt-article",
          "seendate": "20260622T120000Z",
          "snippet": "Rail services were disrupted."
        }
      ]
    }
    """

    records = parse_gdelt_artlist_json(payload)

    assert len(records) == 1
    article = records[0]
    assert article.source == "gdelt"
    assert article.title == "Rail disruption in Austria"
    assert article.url == "https://example.com/gdelt-article"
    assert article.published_date == "20260622T120000Z"
    assert article.body == "Rail services were disrupted."


def test_parse_gdelt_artlist_json_assigns_unique_ids_without_urls():
    payload = """
    {
      "articles": [
        {
          "title": "First rail item",
          "seendate": "20260622T120000Z",
          "snippet": "First body."
        },
        {
          "title": "Second rail item",
          "seendate": "20260622T120000Z",
          "snippet": "Second body."
        }
      ]
    }
    """

    records = parse_gdelt_artlist_json(payload)
    reparsed = parse_gdelt_artlist_json(payload)

    assert records[0].article_id
    assert records[1].article_id
    assert records[0].article_id != records[1].article_id
    assert [r.article_id for r in records] == [r.article_id for r in reparsed]
