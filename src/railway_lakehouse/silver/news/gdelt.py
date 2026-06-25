import json
import logging

from ..schema import ArticleRecord
from .records import article_record_id

logger = logging.getLogger("silver.news.gdelt")


def parse_gdelt_artlist_json(
    json_text: str,
    source: str = "gdelt",
) -> list[ArticleRecord]:
    try:
        payload = json.loads(json_text)
    except (TypeError, ValueError) as exc:
        logger.warning("%s: malformed GDELT JSON; skipping payload: %s", source, exc)
        return []

    if not isinstance(payload, dict):
        logger.warning("%s: GDELT payload is not an object; skipping", source)
        return []

    articles = payload.get("articles") or []
    if not isinstance(articles, list):
        logger.warning("%s: GDELT articles field is not a list; skipping", source)
        return []

    records = []
    dropped = 0

    for index, article in enumerate(articles):
        if not isinstance(article, dict):
            dropped += 1
            continue
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

        if not title or not (url or body):
            dropped += 1
            continue

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

    if dropped:
        logger.warning("%s: dropped %d malformed articles from GDELT ArtList", source, dropped)

    return records
