import json

from ..schema import ArticleRecord
from .records import article_record_id


def parse_gdelt_artlist_json(
    json_text: str,
    source: str = "gdelt",
) -> list[ArticleRecord]:
    payload = json.loads(json_text)

    articles = payload.get("articles") or []

    records = []

    for index, article in enumerate(articles):
        title = article.get("title") or ""
        url = article.get("url") or article.get("url_mobile") or ""

        published_date = (
            article.get("seendate")
            or article.get("publishedDate")
            or article.get("datetime")
        )

        body = (
            article.get("snippet")
            or article.get("summary")
            or article.get("description")
            or title
        )

        article_id = article_record_id(
            url,
            source=source,
            title=title,
            published_date=published_date,
            body=body,
            index=index,
        )

        records.append(
            ArticleRecord(
                article_id=article_id,
                source=source,
                title=title,
                url=url,
                published_date=published_date,
                body=body,
            )
        )

    return records
