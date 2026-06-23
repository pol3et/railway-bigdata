import xml.etree.ElementTree as ET

from ..schema import ArticleRecord
from .extract import article_records_to_news_features
from .records import article_record_id


def parse_rss_xml(xml_text: str, source: str) -> list[ArticleRecord]:
    root = ET.fromstring(xml_text)

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
