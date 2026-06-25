"""
Silver news feature extraction.

GAP-050 turns the old per-row prompt call into a small extraction runner:
cache-skip first, sequential batch processing for the single local Ollama,
bounded retries, typed failures, optional model lifecycle hooks, and a run
manifest. `generate_json` remains the mocked seam; CI never needs Ollama.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .. import config
from ..ollama_client import generate_json
from ..schema import NewsFeature, validate_news_feature
from ..config import NEWS_EVENT_TYPES, KNOWN_OPERATORS
from .cache import (
    CacheBackend,
    NoOpCache,
    extract_cache_key,
    gdelt_passthrough_cache_key,
    model_digest_key,
)
from .failures import ExtractionFailure, utc_now

logger = logging.getLogger("silver.news.extract")

PROMPT_VERSION = config.NEWS_EXTRACTION_PROMPT_VERSION
GDELT_PASSTHROUGH_DIGEST = "gdelt_gkg_passthrough"

_SYSTEM = (
    "You are a precise railway-news information extraction engine for Hungary "
    "and Austria. Extract only facts that are stated in the provided title and "
    "text. Output only the JSON object requested by the schema. Do not infer "
    "sentiment, language, operators, or rail lines; deterministic downstream "
    "passes own those fields."
)

_FEW_SHOT_EXAMPLES = [
    {
        "language": "hu",
        "input": "MAV 12 milliard forintos palyafelujitast jelentett be.",
        "output": {
            "is_rail_related": True,
            "country": "HU",
            "event_type": "investment",
            "monetary_amount_eur": None,
            "monetary_raw": "12 milliard forint",
            "summary_en": "MAV announced a railway track renewal funded in Hungarian forints.",
            "confidence": 0.84,
        },
    },
    {
        "language": "de",
        "input": "Nach einem Oberleitungsschaden fallen OBB-Zuege aus.",
        "output": {
            "is_rail_related": True,
            "country": "AT",
            "event_type": "service_change",
            "monetary_amount_eur": None,
            "monetary_raw": None,
            "summary_en": "OBB train services were cancelled after overhead line damage.",
            "confidence": 0.86,
        },
    },
    {
        "language": "en",
        "input": "A cafe opened near Bahnhofstrasse with no rail service change.",
        "output": {
            "is_rail_related": False,
            "country": "other",
            "event_type": "other",
            "monetary_amount_eur": None,
            "monetary_raw": None,
            "summary_en": "The story is about a cafe and not rail transport.",
            "confidence": 0.9,
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
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
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
        "confidence",
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
        "- Do not output sentiment, language, operators, or rail_lines.\n\n"
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


def _is_snippet_article(article: dict) -> bool:
    source = str(article.get("source") or "").lower()
    body = str(article.get("body") or "")
    return source == "gdelt" or len(body) < 700


def _call_llm_once(article: dict, digest: str) -> tuple[Optional[NewsFeature], Optional[ExtractionFailure]]:
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
    return feature, None


def _extract_uncached_with_retries(
    article: dict,
    digest: str,
    *,
    max_attempts: int,
    retry_backoff_seconds: float,
) -> tuple[Optional[NewsFeature], Optional[ExtractionFailure], int]:
    max_attempts = _resolve_max_attempts(max_attempts)
    last_failure = None
    for attempt in range(1, max_attempts + 1):
        feature, failure = _call_llm_once(article, digest)
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
    cache_key = gdelt_passthrough_cache_key(gkg)
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


def run_extraction_pipeline(
    articles: list,
    *,
    cache: CacheBackend = None,
    manifest_path=None,
    warm_up: bool = True,
    unload_after: bool = False,
    lifecycle: OllamaLifecycle | None = None,
    max_attempts: int | None = None,
    retry_backoff_seconds: float | None = None,
) -> ExtractionRunResult:
    """Run a cached, observable extraction pass over a batch of articles."""
    articles = [_article_to_dict(article) for article in articles]
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


def extract_batch(articles: list, *, cache: CacheBackend = None) -> tuple[list, list]:
    result = run_extraction_pipeline(
        articles,
        cache=cache or NoOpCache(),
        warm_up=False,
        max_attempts=config.NEWS_EXTRACTION_MAX_ATTEMPTS,
        retry_backoff_seconds=config.NEWS_EXTRACTION_RETRY_BACKOFF_SECONDS,
    )
    return result.features, result.failures


def article_records_to_news_features(records: list) -> list:
    articles = [
        r.to_row() if hasattr(r, "to_row") else dict(r)
        for r in records
    ]
    successes, failures = extract_batch(articles)
    if failures:
        logger.warning("article_records_to_news_features dropped %d failed articles", len(failures))
    return successes
