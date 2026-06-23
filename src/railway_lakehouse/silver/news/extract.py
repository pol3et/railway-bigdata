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

from ..ollama_client import generate_json
from ..schema import NewsFeature, validate_news_feature
from ..config import NEWS_EVENT_TYPES, KNOWN_OPERATORS

logger = logging.getLogger("silver.news.extract")

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


def extract_article(*, article_id: str, source: str, url: str,
                    title: str, body: str,
                    published_date: Optional[str] = None) -> Optional[NewsFeature]:
    raw = generate_json(_build_prompt(title, body), schema=_JSON_SCHEMA, system=_SYSTEM)
    if raw is None or not isinstance(raw, dict):
        logger.warning("extraction failed for %s", article_id)
        return None
    return validate_news_feature(
        raw, article_id=article_id, source=source, url=url,
        published_date=published_date, event_types=NEWS_EVENT_TYPES,
        operators_allowed=KNOWN_OPERATORS,
    )


def gdelt_passthrough(*, article_id: str, url: str, published_date: Optional[str],
                      gkg_tone: Optional[float], gkg_themes: Optional[str],
                      gkg_locations: Optional[str]) -> NewsFeature:
    sentiment = None
    if gkg_tone is not None:
        sentiment = "positive" if gkg_tone > 1 else "negative" if gkg_tone < -1 else "neutral"
    country = None
    loc = (gkg_locations or "")
    if "Hungary" in loc: country = "HU"
    elif "Austria" in loc: country = "AT"
    return NewsFeature(
        article_id=article_id, source="gdelt", url=url, published_date=published_date,
        language=None, is_rail_related=True, country=country, event_type="other",
        operators=[], rail_lines=[], summary_en=None, sentiment=sentiment, confidence=None,
    )


def extract_batch(articles: list) -> list:
    out = []
    for a in articles:
        nf = extract_article(
            article_id=a["article_id"], source=a.get("source", "rss"),
            url=a.get("url", ""), title=a.get("title", ""), body=a.get("body", ""),
            published_date=a.get("published_date"))
        if nf is not None:
            out.append(nf)
    logger.info("extracted %d/%d articles", len(out), len(articles))
    return out


def article_records_to_news_features(records: list) -> list:
    articles = [
        r.to_row() if hasattr(r, "to_row") else dict(r)
        for r in records
    ]
    return extract_batch(articles)
