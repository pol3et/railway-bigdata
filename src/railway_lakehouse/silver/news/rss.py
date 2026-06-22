import hashlib
import xml.etree.ElementTree as ET

from ..schema import ArticleRecord
from .extract import extract_batch


def parse_rss_xml(xml_text: str, source: str) -> list[ArticleRecord]:
    root = ET.fromstring(xml_text)

    records = []

    for item in root.findall(".//item"):
        title = item.findtext("title") or ""
        url = item.findtext("link") or ""
        published = item.findtext("pubDate")

        body = (
            item.findtext("description")
            or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
            or ""
        )

        article_id = hashlib.sha1(url.encode("utf-8")).hexdigest()

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
    articles = [
        {
            "article_id": r.article_id,
            "source": r.source,
            "url": r.url,
            "title": r.title,
            "body": r.body,
            "published_date": r.published_date,
        }
        for r in records
    ]

    return extract_batch(articles)
