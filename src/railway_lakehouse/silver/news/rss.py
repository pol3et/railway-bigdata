import logging
import xml.etree.ElementTree as ET

from ..schema import ArticleRecord
from .extract import article_records_to_news_features
from .records import article_record_id

logger = logging.getLogger("silver.news.rss")


def parse_rss_xml(xml_text: str, source: str) -> list[ArticleRecord]:
    """Parse one RSS feed into ArticleRecord rows.

    Malformed feeds are skipped and logged so one bad feed cannot abort a
    multi-feed batch. ElementTree parses whole XML documents, so partial item
    recovery is not attempted after a document-level ParseError.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("rss %s: malformed RSS XML; skipping feed: %s", source, exc)
        return []

    records = []

    for index, item in enumerate(root.findall(".//item")):
        title = item.findtext("title") or ""
        url = item.findtext("link") or ""
        published = item.findtext("pubDate")

        body = (
            item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
            or item.findtext("description")
            or ""
        )

        article_id = article_record_id(
            url,
            source=source,
            title=title,
            published_date=published,
            body=body,
            index=index,
        )

        records.append(
            ArticleRecord(
                article_id=article_id,
                source=source,
                title=title,
                url=url,
                published_date=published,
                body=body,
            )
        )

    return records


def rss_records_to_news_features(records):
    return article_records_to_news_features(records)
