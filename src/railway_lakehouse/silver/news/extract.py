"""
Silver news feature extraction.

GAP-050 turns the old per-row prompt call into a small extraction runner:
cache-skip first, deterministic language identification, sequential batch
processing for the single local Ollama, bounded retries, typed failures,
optional model lifecycle hooks, and a run manifest. `generate_json` remains
the mocked seam; CI never needs Ollama.
GAP-034 keeps sentiment out of the LLM path and fills it with a pinned,
deterministic XLM-R encoder post-pass when that local model is available.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
import unicodedata
from dataclasses import dataclass, replace
from importlib.util import find_spec
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .. import config
from ..language_id import LANGUAGE_ID_MODEL_DIGEST, identify_language
from ..ollama_client import generate_json
from ..schema import GKGRecord, ISO_639_1_CODES, NewsFeature, validate_news_feature
from ..config import NEWS_EVENT_TYPES, KNOWN_OPERATORS
from .cache import (
    CacheBackend,
    NoOpCache,
    extract_cache_key,
    gdelt_passthrough_cache_key,
    model_digest_key,
)
from .embeddings import cluster_near_duplicates, compute_embeddings
from .failures import ExtractionFailure, utc_now
from . import sentiment_encoder
from .gkg_parser import match_gkg_to_article

logger = logging.getLogger("silver.news.extract")

PROMPT_VERSION = config.NEWS_EXTRACTION_PROMPT_VERSION
GDELT_PASSTHROUGH_DIGEST = f"gdelt_gkg_passthrough_{LANGUAGE_ID_MODEL_DIGEST[:12]}"
_SENTIMENT_SIGN = {"negative": -1.0, "neutral": 0.0, "positive": 1.0}
_LLM_SENTIMENT_FIELDS = {
    "sentiment",
    "sentiment_label",
    "sentiment_score",
    "sentiment_confidence",
    "confidence",
}

_SYSTEM = (
    "You are a precise railway-news information extraction engine for Hungary "
    "and Austria. Extract only facts that are stated in the provided title and "
    "text. Output only the JSON object requested by the schema. Do not infer "
    "sentiment, operators, or rail lines; deterministic downstream "
    "passes own those fields."
)

_FEW_SHOT_EXAMPLES = [
    {
        "input": "MAV 12 milliard forintos palyafelujitast jelentett be.",
        "output": {
            "is_rail_related": True,
            "country": "HU",
            "event_type": "investment",
            "monetary_amount_eur": None,
            "monetary_raw": "12 milliard forint",
            "summary_en": "MAV announced a railway track renewal funded in Hungarian forints.",
        },
    },
    {
        "input": "Nach einem Oberleitungsschaden fallen OBB-Zuege aus.",
        "output": {
            "is_rail_related": True,
            "country": "AT",
            "event_type": "service_change",
            "monetary_amount_eur": None,
            "monetary_raw": None,
            "summary_en": "OBB train services were cancelled after overhead line damage.",
        },
    },
    {
        "input": "A cafe opened near Bahnhofstrasse with no rail service change.",
        "output": {
            "is_rail_related": False,
            "country": "other",
            "event_type": "other",
            "monetary_amount_eur": None,
            "monetary_raw": None,
            "summary_en": "The story is about a cafe and not rail transport.",
        },
    },
]

_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_rail_related": {"type": "boolean"},
        "country": {"type": "string", "enum": ["HU", "AT", "other"]},
        "event_type": {"type": "string", "enum": NEWS_EVENT_TYPES},
        "monetary_amount_eur": {"type": ["number", "null"]},
        "monetary_raw": {"type": ["string", "null"]},
        "summary_en": {"type": "string"},
        "is_rail_related_confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "event_type_confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "monetary_confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
    },
    "required": [
        "is_rail_related",
        "country",
        "event_type",
        "monetary_amount_eur",
        "monetary_raw",
        "summary_en",
    ],
}


@dataclass
class _ArticleOutcome:
    feature: Optional[NewsFeature]
    failure: Optional[ExtractionFailure]
    cache_hit: bool = False
    cache_write: bool = False
    llm_attempted: bool = False
    llm_attempts: int = 0
    retry_attempts: int = 0
    latency_seconds: float = 0.0
    gdelt_passthrough: bool = False


@dataclass
class ExtractionRunResult:
    features: list[NewsFeature]
    failures: list[ExtractionFailure]
    manifest: dict


class OllamaLifecycle:
    """Optional live-run lifecycle hooks; disabled/mocked in CI."""

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("OLLAMA_MODEL", config.OLLAMA_MODEL)

    def warm_up(self) -> dict:
        started = time.perf_counter()
        raw = generate_json(
            "Return {\"ok\": true}.",
            schema={
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
            },
            system="You are a JSON warm-up probe.",
        )
        return {
            "status": "ok" if isinstance(raw, dict) else "failed",
            "latency_seconds": round(time.perf_counter() - started, 3),
        }

    def stop_model(self) -> dict:
        exe = shutil.which("ollama")
        if not exe:
            return {"status": "not_checked", "reason": "ollama executable not found"}
        completed = subprocess.run(
            [exe, "stop", self.model],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return {
            "status": "ok" if completed.returncode == 0 else "failed",
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }

    def vram_status(self) -> dict:
        exe = shutil.which("nvidia-smi")
        if not exe:
            return {"status": "not_checked", "reason": "nvidia-smi not found"}
        completed = subprocess.run(
            [
                exe,
                "--query-compute-apps=pid,process_name,used_gpu_memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        return {
            "status": "ok" if completed.returncode == 0 else "failed",
            "active_compute_processes": lines,
        }


def _build_prompt(
    title: str,
    body: str,
    *,
    source: str = "rss",
    url: str = "",
    is_snippet: bool = False,
) -> str:
    ev = ", ".join(NEWS_EVENT_TYPES)
    trust = "snippet_only" if is_snippet else "full_text_or_rss_description"
    body = (body or "")[:6000]
    examples = json.dumps(_FEW_SHOT_EXAMPLES, ensure_ascii=False, indent=2)
    return (
        f"Prompt version: {config.NEWS_EXTRACTION_PROMPT_VERSION}\n"
        f"Source: {source or 'unknown'}\n"
        f"URL: {url or 'unknown'}\n"
        f"Input trust: {trust}\n\n"
        f"Article title: {title}\n\n"
        f"Article text:\n{body}\n\n"
        "Task: extract the narrow LLM-owned railway-news fields.\n"
        "Rules:\n"
        "- Use only the title/text above. If the text is snippet_only, lower confidence and avoid article-wide claims.\n"
        "- Use country HU for Hungary, AT for Austria, other otherwise.\n"
        f"- event_type must be exactly one of: {ev}.\n"
        "- monetary_raw is the original money phrase with currency when stated; otherwise null.\n"
        "- monetary_amount_eur is only for amounts explicitly stated in EUR or with an explicit EUR equivalent. Do not do FX conversion.\n"
        "- summary_en is one short English sentence.\n"
        "- Do not output sentiment, operators, or rail_lines.\n\n"
        "Few-shot examples (synthetic, held out from any golden test set):\n"
        f"{examples}\n\n"
        "Return only the JSON object."
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


def _raw_to_text(raw) -> Optional[str]:
    if raw is None:
        return None
    try:
        return json.dumps(raw, ensure_ascii=False)
    except TypeError:
        return str(raw)


def _resolve_max_attempts(max_attempts: int | None) -> int:
    attempts = config.NEWS_EXTRACTION_MAX_ATTEMPTS if max_attempts is None else int(max_attempts)
    if attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    return attempts


def _failure(article: dict, reason: str, model_digest: str, raw=None) -> ExtractionFailure:
    return ExtractionFailure(
        article_id=str(article.get("article_id") or ""),
        source=str(article.get("source") or ""),
        url=str(article.get("url") or ""),
        title=str(article.get("title") or ""),
        published_date=article.get("published_date"),
        reason=reason,
        timestamp_utc=utc_now(),
        model_digest=model_digest,
        raw=_raw_to_text(raw),
    )


def _validated_language_code(value) -> Optional[str]:
    text = str(value or "").strip().lower()
    return text if text in ISO_639_1_CODES else None


def _article_language(article: dict) -> Optional[str]:
    title = str(article.get("title") or "")
    body = str(article.get("body") or "")
    return identify_language(f"{title} {body}")


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


def _strip_llm_sentiment(raw: dict) -> dict:
    """Remove legacy fields the LLM no longer owns."""
    return {key: value for key, value in raw.items() if key not in _LLM_SENTIMENT_FIELDS}


def _signed_sentiment_score(label: str, confidence: float) -> float:
    return _SENTIMENT_SIGN[label] * confidence


def _add_sentiment_and_confidence(
    feature: NewsFeature,
    *,
    title: str,
    body: str,
) -> NewsFeature:
    encoded = sentiment_encoder.get_encoder().encode(f"{title}\n\n{body or ''}")
    if encoded is None:
        return feature
    label = encoded["label"]
    confidence = float(encoded["score"])
    return replace(
        feature,
        sentiment=label,
        confidence=confidence,
        sentiment_label=label,
        sentiment_score=_signed_sentiment_score(label, confidence),
        sentiment_confidence=confidence,
    )


def _country_from_gkg(gkg: dict) -> Optional[str]:
    source_country = str(gkg.get("sourcecountry") or gkg.get("source_country") or "").upper()
    if source_country in {"HU", "HUN"}:
        return "HU"
    if source_country in {"AT", "AUT", "AU"}:
        return "AT"
    locations = str(gkg.get("gkg_locations") or gkg.get("locations") or "")
    for segment in [item.strip() for item in locations.split(";") if item.strip()]:
        parts = segment.split("#")
        text = " ".join(parts).casefold()
        country_code = parts[2].upper() if len(parts) > 2 else ""
        if country_code in {"HU", "HUN"} or "hungary" in text or "hungarian" in text:
            return "HU"
        if country_code in {"AT", "AUT", "AU"} or "austria" in text or "austrian" in text:
            return "AT"
    return None


_GKG_EVENT_THEME_RULES = (
    ("accident", ("RAIL_INCIDENT", "DERAIL", "ACCIDENT", "DISASTER")),
    ("strike", ("LABOR_STRIKE", "STRIKE", "PROTEST")),
    ("investment", ("ECON_INVESTMENT", "INVESTMENT", "INFRASTRUCTURE")),
    ("delay", ("DELAY", "DISRUPTION", "CANCEL")),
    ("service_change", ("PUBLIC_TRANSPORT", "RAIL_TRANSPORT", "TRANSPORT")),
)

_OPERATOR_ALIASES = {
    "MÁV": ("MÁV", "MAV", "Hungarian Railways"),
    "GYSEV": ("GYSEV", "Raaberbahn"),
    "ÖBB": ("ÖBB", "OBB", "OEBB"),
    "Westbahn": ("Westbahn",),
    "RailCargo": ("RailCargo", "Rail Cargo"),
}


def _event_type_from_gkg_themes(themes: Optional[str]) -> str:
    normalized = _normalize_search_text(themes or "")
    if not normalized:
        return "other"
    for event_type, needles in _GKG_EVENT_THEME_RULES:
        if event_type not in NEWS_EVENT_TYPES:
            continue
        if any(_normalize_search_text(needle) in normalized for needle in needles):
            return event_type
    return "other"


def _operators_from_gkg(gkg: dict) -> list[str]:
    haystack = _normalize_search_text(
        " ".join(
            str(gkg.get(key) or "")
            for key in (
                "gkg_organizations",
                "organizations",
                "gkg_persons",
                "persons",
            )
        )
    )
    operators = []
    for operator in KNOWN_OPERATORS:
        if operator == "other":
            continue
        aliases = _OPERATOR_ALIASES.get(operator, (operator,))
        if any(_normalize_search_text(alias) in haystack for alias in aliases):
            operators.append(operator)
    return operators


def _normalize_search_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value))
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return ascii_text.casefold()


def _is_snippet_article(article: dict) -> bool:
    source = str(article.get("source") or "").lower()
    body = str(article.get("body") or "")
    return source == "gdelt" or len(body) < 700


def _call_llm_once(
    article: dict,
    digest: str,
    *,
    language: Optional[str],
) -> tuple[Optional[NewsFeature], Optional[ExtractionFailure]]:
    try:
        raw = generate_json(
            _build_prompt(
                str(article.get("title") or ""),
                str(article.get("body") or ""),
                source=str(article.get("source") or "rss"),
                url=str(article.get("url") or ""),
                is_snippet=_is_snippet_article(article),
            ),
            schema=_JSON_SCHEMA,
            system=_SYSTEM,
        )
    except Exception as exc:
        return None, _failure(article, f"{type(exc).__name__}: {exc}", digest)

    if raw is None or not isinstance(raw, dict):
        return None, _failure(article, "model returned no valid JSON object", digest, raw)

    raw = _strip_llm_sentiment(raw)
    raw.setdefault("extraction_timestamp_utc", utc_now())
    raw["extraction_model_digest"] = digest
    raw.setdefault("summary_en_source", "ollama")
    feature = validate_news_feature(
        raw,
        article_id=str(article.get("article_id") or ""),
        source=str(article.get("source") or "rss"),
        url=str(article.get("url") or ""),
        published_date=article.get("published_date"),
        language=language,
        event_types=NEWS_EVENT_TYPES,
        operators_allowed=KNOWN_OPERATORS,
    )
    feature = _add_sentiment_and_confidence(
        feature,
        title=str(article.get("title") or ""),
        body=str(article.get("body") or ""),
    )
    return feature, None


def _extract_uncached_with_retries(
    article: dict,
    digest: str,
    *,
    language: Optional[str],
    max_attempts: int,
    retry_backoff_seconds: float,
) -> tuple[Optional[NewsFeature], Optional[ExtractionFailure], int]:
    max_attempts = _resolve_max_attempts(max_attempts)
    last_failure = None
    for attempt in range(1, max_attempts + 1):
        feature, failure = _call_llm_once(article, digest, language=language)
        if feature is not None:
            return feature, None, attempt
        last_failure = failure
        if attempt < max_attempts and retry_backoff_seconds > 0:
            time.sleep(retry_backoff_seconds * attempt)
    return None, last_failure, max_attempts


def _extract_article_cached_outcome(
    article: dict,
    cache: CacheBackend,
    *,
    max_attempts: int,
    retry_backoff_seconds: float,
) -> _ArticleOutcome:
    started = time.perf_counter()
    digest = model_digest_key()
    max_attempts = _resolve_max_attempts(max_attempts)
    try:
        _require_valid_article(article)
    except ValueError as exc:
        return _ArticleOutcome(
            feature=None,
            failure=_failure(article, str(exc), digest),
            latency_seconds=round(time.perf_counter() - started, 3),
        )

    language = _article_language(article)
    cache_key = extract_cache_key(article)
    cached = cache.get(cache_key, digest)
    if cached is not None:
        return _ArticleOutcome(
            feature=cached,
            failure=None,
            cache_hit=True,
            latency_seconds=round(time.perf_counter() - started, 3),
        )

    feature, failure, attempts = _extract_uncached_with_retries(
        article,
        digest,
        language=language,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    if feature is None:
        return _ArticleOutcome(
            feature=None,
            failure=failure,
            llm_attempted=True,
            llm_attempts=attempts,
            retry_attempts=max(0, attempts - 1),
            latency_seconds=round(time.perf_counter() - started, 3),
        )

    cache.put(cache_key, digest, feature)
    return _ArticleOutcome(
        feature=feature,
        failure=None,
        cache_write=True,
        llm_attempted=True,
        llm_attempts=attempts,
        retry_attempts=max(0, attempts - 1),
        latency_seconds=round(time.perf_counter() - started, 3),
    )


def extract_article_cached(article, cache: CacheBackend = None) -> Optional[NewsFeature]:
    """Extract a NewsFeature with content-hash + model-digest cache replay."""
    outcome = _extract_article_cached_outcome(
        _article_to_dict(article),
        cache or NoOpCache(),
        max_attempts=config.NEWS_EXTRACTION_MAX_ATTEMPTS,
        retry_backoff_seconds=config.NEWS_EXTRACTION_RETRY_BACKOFF_SECONDS,
    )
    if outcome.failure:
        logger.warning("extraction failed for %s: %s", outcome.failure.article_id, outcome.failure.reason)
    return outcome.feature


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
    return extract_article_cached(article, cache or NoOpCache())


def _gkg_record_to_passthrough_dict(gkg_record: GKGRecord) -> dict:
    return {
        "gkg_id": gkg_record.gkg_id,
        "date": gkg_record.gkg_date,
        "document_identifier": gkg_record.document_identifier,
        "url": gkg_record.document_identifier,
        "source_common_name": gkg_record.source_common_name,
        "gkg_tone": gkg_record.gkg_tone,
        "gkg_themes": gkg_record.gkg_themes,
        "gkg_persons": gkg_record.gkg_persons,
        "gkg_organizations": gkg_record.gkg_organizations,
        "gkg_locations": gkg_record.gkg_locations,
        "gkg_emotions": gkg_record.gkg_emotions,
    }


def gdelt_passthrough(*, article_id: str, url: str, published_date: Optional[str],
                      gkg_tone: Optional[float] = None,
                      gkg_themes: Optional[str] = None,
                      gkg_locations: Optional[str] = None,
                      gkg_persons: Optional[str] = None,
                      gkg_organizations: Optional[str] = None,
                      gkg_emotions: Optional[str] = None,
                      title: str = "",
                      body: str = "",
                      language: Optional[str] = None,
                      gkg_record: Optional[GKGRecord] = None) -> NewsFeature:
    gkg = _gkg_record_to_passthrough_dict(gkg_record) if gkg_record is not None else {}
    gkg.update(
        {
            "article_id": article_id,
            "url": url,
            "published_date": published_date,
            "title": title,
            "body": body,
            "language": language,
        }
    )
    for key, value in {
        "gkg_tone": gkg_tone,
        "gkg_themes": gkg_themes,
        "gkg_locations": gkg_locations,
        "gkg_persons": gkg_persons,
        "gkg_organizations": gkg_organizations,
        "gkg_emotions": gkg_emotions,
    }.items():
        if value is not None:
            gkg[key] = value
    return gdelt_passthrough_cached(gkg, NoOpCache())


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
    cache_key = gdelt_passthrough_cache_key(gkg)
    cached = cache.get(cache_key, GDELT_PASSTHROUGH_DIGEST)
    if cached is not None:
        return cached
    tone = _float_or_none(_first_value_by_key_presence(gkg, "gkg_tone", "tone"))
    sentiment = _tone_to_sentiment(tone)
    language = _article_language(article) or _validated_language_code(gkg.get("language"))
    feature = NewsFeature(
        article_id=str(article["article_id"]),
        source="gdelt",
        url=str(article["url"] or ""),
        published_date=article["published_date"],
        language=language,
        is_rail_related=True,
        country=_country_from_gkg(gkg),
        event_type=_event_type_from_gkg_themes(
            gkg.get("gkg_themes") or gkg.get("themes")
        ),
        operators=_operators_from_gkg(gkg),
        rail_lines=[],
        summary_en=None,
        sentiment=sentiment,
        confidence=None,
        sentiment_label=sentiment,
        language_detected_code=language,
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


def _merge_gkg_record(article: dict, gkg_record: GKGRecord) -> dict:
    merged = dict(article)
    gkg = _gkg_record_to_passthrough_dict(gkg_record)
    merged.update({key: value for key, value in gkg.items() if value is not None})
    merged["article_id"] = article.get("article_id")
    merged["source"] = article.get("source")
    merged["title"] = article.get("title")
    merged["body"] = article.get("body")
    merged["url"] = article.get("url") or gkg_record.document_identifier or ""
    merged["published_date"] = article.get("published_date") or gkg_record.gkg_date
    return merged


def _find_matching_gkg_record(article: dict, gkg_records: list[GKGRecord]) -> Optional[GKGRecord]:
    article_id = str(article.get("article_id") or "")
    article_url = str(article.get("url") or "")
    for record in gkg_records:
        if article_id and article_id in {record.gkg_id, record.document_identifier}:
            return record
        if article_url and match_gkg_to_article(record, article_url):
            return record
    return None


def _enrich_articles_with_gkg_records(
    articles: list[dict],
    gkg_records: Optional[list[GKGRecord]],
) -> list[dict]:
    if not gkg_records:
        return articles
    enriched = []
    for article in articles:
        if str(article.get("source") or "").lower() == "gdelt":
            match = _find_matching_gkg_record(article, gkg_records)
            if match is not None:
                logger.info(
                    "GDELT article %s using GKG passthrough record %s",
                    article.get("article_id"),
                    match.gkg_id,
                )
                enriched.append(_merge_gkg_record(article, match))
                continue
        logger.info(
            "article %s using LLM extraction path",
            article.get("article_id"),
        )
        enriched.append(article)
    return enriched


def _effective_concurrency() -> int:
    requested = max(1, int(config.NEWS_EXTRACTION_CONCURRENCY))
    server_parallel = int(os.environ.get("OLLAMA_NUM_PARALLEL", "1") or "1")
    return max(1, min(requested, server_parallel))


def _new_manifest(total: int, model_digest: str) -> dict:
    return {
        "run_started_utc": utc_now(),
        "run_finished_utc": None,
        "duration_seconds": None,
        "status": "running",
        "prompt_version": config.NEWS_EXTRACTION_PROMPT_VERSION,
        "model_digest": model_digest,
        "ollama_model": os.environ.get("OLLAMA_MODEL", config.OLLAMA_MODEL),
        "settings": {
            "num_ctx": config.OLLAMA_NUM_CTX,
            "num_batch": config.OLLAMA_NUM_BATCH,
            "num_predict": config.OLLAMA_NUM_PREDICT,
            "think": config.OLLAMA_THINK,
            "keep_alive": config.OLLAMA_KEEP_ALIVE,
            "concurrency": _effective_concurrency(),
        },
        "counts": {
            "received": total,
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_writes": 0,
            "llm_attempted": 0,
            "llm_attempts": 0,
            "retry_attempts": 0,
            "gdelt_passthrough": 0,
        },
        "latency_seconds": {
            "total_llm": 0.0,
            "max_article": 0.0,
        },
        "failure_rate": 0.0,
        "lifecycle": {},
        "cache_stats": {},
    }


def _write_manifest(path, manifest: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _embedding_model_available() -> bool:
    try:
        return find_spec("sentence_transformers") is not None
    except (ImportError, ValueError):
        return False


def _has_text_embedding(row: NewsFeature) -> bool:
    embedding = getattr(row, "text_embedding", None)
    return isinstance(embedding, (list, tuple)) and len(embedding) > 0


def run_extraction_pipeline(
    articles: list,
    *,
    cache: CacheBackend = None,
    manifest_path=None,
    gkg_records: Optional[list[GKGRecord]] = None,
    warm_up: bool = True,
    unload_after: bool = False,
    lifecycle: OllamaLifecycle | None = None,
    max_attempts: int | None = None,
    retry_backoff_seconds: float | None = None,
) -> ExtractionRunResult:
    """Run a cached, observable extraction pass over a batch of articles."""
    articles = [_article_to_dict(article) for article in articles]
    articles = _enrich_articles_with_gkg_records(articles, gkg_records)
    cache = cache or NoOpCache()
    max_attempts = _resolve_max_attempts(max_attempts)
    retry_backoff_seconds = (
        config.NEWS_EXTRACTION_RETRY_BACKOFF_SECONDS
        if retry_backoff_seconds is None
        else retry_backoff_seconds
    )
    lifecycle = lifecycle or OllamaLifecycle()
    model_digest = model_digest_key()
    manifest = _new_manifest(len(articles), model_digest)
    manifest["settings"]["max_attempts"] = max_attempts
    successes: list[NewsFeature] = []
    failures: list[ExtractionFailure] = []
    started = time.perf_counter()

    if warm_up:
        manifest["lifecycle"]["warm_up"] = lifecycle.warm_up()

    for raw_article in articles:
        article = _article_to_dict(raw_article)
        digest = GDELT_PASSTHROUGH_DIGEST if _has_gkg_fields(article) else model_digest
        try:
            if str(article.get("source") or "").lower() == "gdelt" and _has_gkg_fields(article):
                before = time.perf_counter()
                nf = gdelt_passthrough_cached(article, cache)
                outcome = _ArticleOutcome(
                    feature=nf,
                    failure=None,
                    gdelt_passthrough=True,
                    latency_seconds=round(time.perf_counter() - before, 3),
                )
            else:
                outcome = _extract_article_cached_outcome(
                    article,
                    cache,
                    max_attempts=max_attempts,
                    retry_backoff_seconds=retry_backoff_seconds,
                )
            manifest["counts"]["processed"] += 1
            manifest["latency_seconds"]["max_article"] = max(
                manifest["latency_seconds"]["max_article"],
                outcome.latency_seconds,
            )
            if outcome.cache_hit:
                manifest["counts"]["cache_hits"] += 1
            elif outcome.llm_attempted:
                manifest["counts"]["cache_misses"] += 1
            if outcome.cache_write:
                manifest["counts"]["cache_writes"] += 1
            if outcome.llm_attempted:
                manifest["counts"]["llm_attempted"] += 1
                manifest["counts"]["llm_attempts"] += outcome.llm_attempts
                manifest["counts"]["retry_attempts"] += outcome.retry_attempts
                manifest["latency_seconds"]["total_llm"] += outcome.latency_seconds
            if outcome.gdelt_passthrough:
                manifest["counts"]["gdelt_passthrough"] += 1
            if outcome.feature is not None:
                successes.append(outcome.feature)
                manifest["counts"]["succeeded"] += 1
            elif outcome.failure is not None:
                failures.append(outcome.failure)
                manifest["counts"]["failed"] += 1
                logger.warning(
                    "news extraction failed for %s: %s",
                    outcome.failure.article_id,
                    outcome.failure.reason,
                )
        except RuntimeError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            failure = _failure(article, str(exc), digest)
            failures.append(failure)
            manifest["counts"]["processed"] += 1
            manifest["counts"]["failed"] += 1
            logger.warning("news extraction failed for %s: %s", failure.article_id, failure.reason)
        except Exception as exc:
            failure = _failure(article, f"{type(exc).__name__}: {exc}", digest)
            failures.append(failure)
            manifest["counts"]["processed"] += 1
            manifest["counts"]["failed"] += 1
            logger.warning("news extraction failed for %s: %s", failure.article_id, failure.reason)

    if unload_after:
        manifest["lifecycle"]["stop_model"] = lifecycle.stop_model()
        manifest["lifecycle"]["vram_status_after_stop"] = lifecycle.vram_status()

    successes = compute_embeddings(successes, use_model=_embedding_model_available())
    if any(_has_text_embedding(feature) for feature in successes):
        cluster_near_duplicates(successes)
    _refresh_embedded_cache(articles, successes, cache, model_digest)

    manifest["run_finished_utc"] = utc_now()
    manifest["duration_seconds"] = round(time.perf_counter() - started, 3)
    manifest["latency_seconds"]["total_llm"] = round(manifest["latency_seconds"]["total_llm"], 3)
    manifest["failure_rate"] = (
        round(manifest["counts"]["failed"] / manifest["counts"]["processed"], 6)
        if manifest["counts"]["processed"]
        else 0.0
    )
    manifest["cache_stats"] = cache.cache_stats()
    manifest["status"] = "passed" if not failures else "completed_with_failures"
    if manifest_path is not None:
        _write_manifest(manifest_path, manifest)

    logger.info(
        "extracted %d/%d articles (%d failures, %d cache hits)",
        len(successes),
        len(articles),
        len(failures),
        manifest["counts"]["cache_hits"],
    )
    return ExtractionRunResult(successes, failures, manifest)


def _refresh_embedded_cache(
    articles: list[dict],
    features: list[NewsFeature],
    cache: CacheBackend,
    model_digest: str,
) -> None:
    """Rewrite cache entries after optional embedding enrichment."""
    by_id = {feature.article_id: feature for feature in features}
    for article in articles:
        article_id = str(article.get("article_id") or article.get("document_identifier") or "")
        feature = by_id.get(article_id)
        if feature is None:
            continue
        if str(article.get("source") or "").lower() == "gdelt" and _has_gkg_fields(article):
            cache.put(gdelt_passthrough_cache_key(article), GDELT_PASSTHROUGH_DIGEST, feature)
        else:
            cache.put(extract_cache_key(article), model_digest, feature)


def extract_batch(articles: list, *, cache: CacheBackend = None) -> tuple[list, list]:
    result = run_extraction_pipeline(
        articles,
        cache=cache or NoOpCache(),
        warm_up=False,
        max_attempts=config.NEWS_EXTRACTION_MAX_ATTEMPTS,
        retry_backoff_seconds=config.NEWS_EXTRACTION_RETRY_BACKOFF_SECONDS,
    )
    return result.features, result.failures


def article_records_to_news_features(
    records: list,
    *,
    gkg_records: Optional[list[GKGRecord]] = None,
) -> list:
    articles = [
        r.to_row() if hasattr(r, "to_row") else dict(r)
        for r in records
    ]
    articles = _enrich_articles_with_gkg_records(articles, gkg_records)
    successes, failures = extract_batch(articles)
    if failures:
        logger.warning("article_records_to_news_features dropped %d failed articles", len(failures))
    return successes
