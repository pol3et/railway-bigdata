"""
Silver news feature extraction.

For each rail article (RSS full text, or a GDELT article record), produce one
structured NewsFeature row via Ollama with JSON-constrained output, validated
against schema.py. Articles may be Hungarian, German, or English — the prompt
asks for an English summary and English-normalized fields regardless.

Hybrid note (see SILVER_DESIGN.md): GDELT GKG already provides themes, tone,
locations, persons, and organizations. `gdelt_passthrough()` lifts those into a
partial NewsFeature WITHOUT calling the LLM; `extract_article()` is reserved for
RSS/full-text where no structured annotation exists, or to enrich.
"""
import logging
from typing import Optional
from urllib.parse import urlparse

from ..ollama_client import generate_json
from ..schema import NewsFeature, validate_news_feature
from ..config import NEWS_EVENT_TYPES, KNOWN_OPERATORS
from .cache import CacheBackend, NoOpCache, extract_cache_key, model_digest_key
from .failures import ExtractionFailure, utc_now

logger = logging.getLogger("silver.news.extract")

GDELT_PASSTHROUGH_DIGEST = "gdelt_gkg_passthrough"

_SYSTEM = (
    "You are a precise information-extraction engine for railway news in Hungary "
    "and Austria. You read an article (which may be in Hungarian, German, or "
    "English) and output ONLY a JSON object with the requested fields. Do not "
    "invent facts: if a field is not stated, use null (or false for booleans). "
    "Summaries and all categorical values must be in English."
)

_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "is_rail_related": {"type": "boolean"},
        "country": {"type": "string", "enum": ["HU", "AT", "other"]},
        "event_type": {"type": "string", "enum": NEWS_EVENT_TYPES},
        "operators": {"type": "array", "items": {"type": "string"}},
        "rail_lines": {"type": "array", "items": {"type": "string"}},
        "monetary_amount_eur": {"type": ["number", "null"]},
        "monetary_raw": {"type": ["string", "null"]},
        "summary_en": {"type": "string"},
        "sentiment": {"type": "string", "enum": ["negative", "neutral", "positive"]},
        "language": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["is_rail_related", "event_type", "summary_en"],
}


def _build_prompt(title: str, body: str) -> str:
    ev = ", ".join(NEWS_EVENT_TYPES)
    ops = ", ".join(KNOWN_OPERATORS)
    body = (body or "")[:6000]
    return (
        f"Article title: {title}\n\nArticle text:\n{body}\n\n"
        "Extract these fields as JSON:\n"
        "- is_rail_related (bool): is this genuinely about rail transport?\n"
        "- country: HU, AT, or other\n"
        f"- event_type: one of [{ev}]\n"
        f"- operators: subset of [{ops}] mentioned\n"
        "- rail_lines: list of any line/route/station names mentioned\n"
        "- monetary_amount_eur: number in EUR if a monetary figure is given, else null\n"
        "- monetary_raw: the original money string (e.g. '12 milliard forint'), else null\n"
        "- summary_en: a 1-2 sentence English summary\n"
        "- sentiment: negative, neutral, or positive (toward the rail system)\n"
        "- language: ISO 639-1 code of the article\n"
        "- confidence: 0..1, your confidence in this extraction\n"
        "Output ONLY the JSON object."
    )


def _article_to_dict(article) -> dict:
    return article.to_row() if hasattr(article, "to_row") else dict(article)


def _require_valid_article(article: dict) -> None:
    if not str(article.get("article_id") or "").strip():
        raise ValueError("missing article_id")
    if not str(article.get("title") or "").strip():
        raise ValueError("missing title")
    url = str(article.get("url") or "").strip()
    if url:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("malformed url")


def _failure(article: dict, reason: str, model_digest: str) -> ExtractionFailure:
    return ExtractionFailure(
        article_id=str(article.get("article_id") or ""),
        source=str(article.get("source") or ""),
        url=str(article.get("url") or ""),
        title=str(article.get("title") or ""),
        published_date=article.get("published_date"),
        reason=reason,
        timestamp_utc=utc_now(),
        model_digest=model_digest,
    )


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_value_by_key_presence(mapping: dict, *keys: str):
    for key in keys:
        if key in mapping:
            return mapping.get(key)
    return None


def _tone_to_sentiment(gkg_tone: Optional[float]) -> Optional[str]:
    if gkg_tone is None:
        return None
    return "positive" if gkg_tone > 1 else "negative" if gkg_tone < -1 else "neutral"


def _country_from_gkg(gkg: dict) -> Optional[str]:
    source_country = str(gkg.get("sourcecountry") or gkg.get("source_country") or "").upper()
    if source_country in {"HU", "HUN"}:
        return "HU"
    if source_country in {"AT", "AUT"}:
        return "AT"
    locations = str(gkg.get("gkg_locations") or gkg.get("locations") or "")
    if "Hungary" in locations:
        return "HU"
    if "Austria" in locations:
        return "AT"
    return None


def extract_article_cached(article, cache: CacheBackend = None) -> Optional[NewsFeature]:
    """Extract a NewsFeature with content-hash + model-digest cache replay."""
    article = _article_to_dict(article)
    _require_valid_article(article)
    cache = cache or NoOpCache()
    digest = model_digest_key()
    cache_key = extract_cache_key(article)
    cached = cache.get(cache_key, digest)
    if cached is not None:
        return cached

    raw = generate_json(
        _build_prompt(str(article.get("title") or ""), str(article.get("body") or "")),
        schema=_JSON_SCHEMA,
        system=_SYSTEM,
    )
    if raw is None or not isinstance(raw, dict):
        logger.warning("extraction failed for %s", article.get("article_id"))
        return None
    raw.setdefault("extraction_timestamp_utc", utc_now())
    raw["extraction_model_digest"] = digest
    raw.setdefault("summary_en_source", "ollama")
    feature = validate_news_feature(
        raw,
        article_id=str(article.get("article_id") or ""),
        source=str(article.get("source") or "rss"),
        url=str(article.get("url") or ""),
        published_date=article.get("published_date"),
        event_types=NEWS_EVENT_TYPES,
        operators_allowed=KNOWN_OPERATORS,
    )
    cache.put(cache_key, digest, feature)
    return feature


def extract_article(*, article_id: str, source: str, url: str,
                    title: str, body: str,
                    published_date: Optional[str] = None,
                    cache: CacheBackend = None) -> Optional[NewsFeature]:
    article = {
        "article_id": article_id,
        "source": source,
        "url": url,
        "title": title,
        "body": body,
        "published_date": published_date,
    }
    try:
        return extract_article_cached(article, cache or NoOpCache())
    except ValueError as exc:
        logger.warning("extraction failed for %s: %s", article_id, exc)
        return None


def gdelt_passthrough(*, article_id: str, url: str, published_date: Optional[str],
                      gkg_tone: Optional[float], gkg_themes: Optional[str],
                      gkg_locations: Optional[str]) -> NewsFeature:
    return gdelt_passthrough_cached(
        {
            "article_id": article_id,
            "url": url,
            "published_date": published_date,
            "gkg_tone": gkg_tone,
            "gkg_themes": gkg_themes,
            "gkg_locations": gkg_locations,
        },
        NoOpCache(),
    )


def gdelt_passthrough_cached(gkg: dict, cache: CacheBackend = None) -> NewsFeature:
    """Lift existing GDELT GKG annotations without an LLM call."""
    cache = cache or NoOpCache()
    article = {
        "article_id": gkg.get("article_id") or gkg.get("document_identifier") or "",
        "title": gkg.get("title") or "",
        "body": gkg.get("body") or "",
        "url": gkg.get("url") or "",
        "published_date": gkg.get("published_date") or gkg.get("date"),
    }
    cache_key = extract_cache_key(article)
    cached = cache.get(cache_key, GDELT_PASSTHROUGH_DIGEST)
    if cached is not None:
        return cached
    tone = _float_or_none(_first_value_by_key_presence(gkg, "gkg_tone", "tone"))
    sentiment = _tone_to_sentiment(tone)
    feature = NewsFeature(
        article_id=str(article["article_id"]),
        source="gdelt",
        url=str(article["url"] or ""),
        published_date=article["published_date"],
        language=gkg.get("language"),
        is_rail_related=True,
        country=_country_from_gkg(gkg),
        event_type="other",
        operators=[],
        rail_lines=[],
        summary_en=None,
        sentiment=sentiment,
        confidence=None,
        sentiment_label=sentiment,
        gkg_themes=gkg.get("gkg_themes") or gkg.get("themes"),
        gkg_persons=gkg.get("gkg_persons") or gkg.get("persons"),
        gkg_organizations=gkg.get("gkg_organizations") or gkg.get("organizations"),
        gkg_locations=gkg.get("gkg_locations") or gkg.get("locations"),
        gkg_tone=tone,
        gkg_emotions=gkg.get("gkg_emotions") or gkg.get("emotions"),
        gkg_tone_source="gdelt_gkg",
        extraction_timestamp_utc=utc_now(),
        extraction_model_digest=GDELT_PASSTHROUGH_DIGEST,
    )
    cache.put(cache_key, GDELT_PASSTHROUGH_DIGEST, feature)
    return feature


def _has_gkg_fields(article: dict) -> bool:
    return any(str(key).startswith("gkg_") for key in article) or "tone" in article


def extract_batch(articles: list, *, cache: CacheBackend = None) -> tuple[list, list]:
    out = []
    failures = []
    cache = cache or NoOpCache()
    for raw_article in articles:
        article = _article_to_dict(raw_article)
        digest = GDELT_PASSTHROUGH_DIGEST if _has_gkg_fields(article) else model_digest_key()
        try:
            if str(article.get("source") or "").lower() == "gdelt" and _has_gkg_fields(article):
                nf = gdelt_passthrough_cached(article, cache)
            else:
                nf = extract_article_cached(article, cache)
            if nf is None:
                raise ValueError("model returned no valid JSON object")
            out.append(nf)
        except RuntimeError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            failure = _failure(article, str(exc), digest)
            failures.append(failure)
            logger.warning("news extraction failed for %s: %s", failure.article_id, failure.reason)
        except Exception as exc:
            failure = _failure(article, f"{type(exc).__name__}: {exc}", digest)
            failures.append(failure)
            logger.warning("news extraction failed for %s: %s", failure.article_id, failure.reason)
    logger.info("extracted %d/%d articles (%d failures)", len(out), len(articles), len(failures))
    return out, failures


def article_records_to_news_features(records: list) -> list:
    articles = [
        r.to_row() if hasattr(r, "to_row") else dict(r)
        for r in records
    ]
    successes, failures = extract_batch(articles)
    if failures:
        logger.warning("article_records_to_news_features dropped %d failed articles", len(failures))
    return successes
