import hashlib


def article_record_id(
    url: str | None,
    *,
    source: str,
    title: str,
    published_date: str | None,
    body: str | None,
    index: int,
) -> str:
    normalized_url = (url or "").strip()
    if normalized_url:
        return normalized_url

    key = "|".join(
        [
            source,
            title or "",
            published_date or "",
            body or "",
            str(index),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()
