"""Content-hash cache for expensive Silver news extraction passes."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol

from .. import config
from ..schema import NewsFeature, news_feature_from_row


def _article_value(article, name: str):
    if hasattr(article, name):
        return getattr(article, name)
    if isinstance(article, dict):
        return article.get(name)
    return None


def _first_article_value(article, *names: str):
    for name in names:
        value = _article_value(article, name)
        if value is not None:
            return value
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def extract_cache_key(article) -> str:
    """Return a content-sensitive SHA-256 key for an ArticleRecord-like object.

    The key includes article lineage plus mutable content fields. If a URL or
    text body changes, the extraction is treated as new work and misses cache.
    """
    payload = {
        "article_id": _article_value(article, "article_id") or "",
        "title": _article_value(article, "title") or "",
        "body": _article_value(article, "body") or "",
        "url": _article_value(article, "url") or "",
        "published_date": _article_value(article, "published_date") or "",
    }
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def gdelt_passthrough_cache_key(gkg) -> str:
    """Return a cache key for deterministic GDELT GKG passthrough features.

    Unlike LLM extraction, the passthrough output depends on GKG annotation
    fields as well as article identity. Include every field used to populate
    ``NewsFeature`` so corrected/enriched GKG rows miss cache.
    """
    payload = {
        "article_id": _first_article_value(gkg, "article_id", "document_identifier") or "",
        "title": _article_value(gkg, "title") or "",
        "body": _article_value(gkg, "body") or "",
        "url": _article_value(gkg, "url") or "",
        "published_date": _first_article_value(gkg, "published_date", "date") or "",
        "language": _article_value(gkg, "language"),
        "source_country": _first_article_value(gkg, "sourcecountry", "source_country"),
        "gkg_tone": _first_article_value(gkg, "gkg_tone", "tone"),
        "gkg_themes": _first_article_value(gkg, "gkg_themes", "themes"),
        "gkg_persons": _first_article_value(gkg, "gkg_persons", "persons"),
        "gkg_organizations": _first_article_value(gkg, "gkg_organizations", "organizations"),
        "gkg_locations": _first_article_value(gkg, "gkg_locations", "locations"),
        "gkg_emotions": _first_article_value(gkg, "gkg_emotions", "emotions"),
    }
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def model_digest_key() -> str:
    """Hash the current extraction model/config/prompt identity.

    This is a cache invalidation key, not a cryptographic digest of model
    weights. It deliberately reads ``OLLAMA_MODEL`` from the environment at call
    time so changing model tags invalidates cached LLM extractions.
    """
    from . import extract, sentiment_encoder

    payload = {
        "ollama_model": os.environ.get("OLLAMA_MODEL", config.OLLAMA_MODEL),
        "sentiment_model": sentiment_encoder.MODEL_NAME,
        "sentiment_model_revision": sentiment_encoder.MODEL_REVISION,
        "ollama_timeout": config.OLLAMA_TIMEOUT,
        "ollama_num_ctx": config.OLLAMA_NUM_CTX,
        "ollama_num_batch": config.OLLAMA_NUM_BATCH,
        "ollama_num_predict": config.OLLAMA_NUM_PREDICT,
        "ollama_keep_alive": config.OLLAMA_KEEP_ALIVE,
        "ollama_think": config.OLLAMA_THINK,
        "prompt_version": config.NEWS_EXTRACTION_PROMPT_VERSION,
        "temperature": 0,
        "system": extract._SYSTEM,
        "json_schema": extract._JSON_SCHEMA,
        "few_shot_examples": extract._FEW_SHOT_EXAMPLES,
    }
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class CacheBackend(Protocol):
    def get(self, cache_key: str, model_digest: str) -> Optional[NewsFeature]:
        ...

    def put(self, cache_key: str, model_digest: str, feature: NewsFeature) -> None:
        ...

    def cache_stats(self) -> dict:
        ...


class NoOpCache:
    """CacheBackend that always misses and stores nothing."""

    def __init__(self):
        self._hits = 0
        self._misses = 0

    def get(self, cache_key: str, model_digest: str) -> Optional[NewsFeature]:
        self._misses += 1
        return None

    def put(self, cache_key: str, model_digest: str, feature: NewsFeature) -> None:
        return None

    def cache_stats(self) -> dict:
        return {"hits": self._hits, "misses": self._misses, "cached_count": 0}


class FileSystemCache:
    """File-per-article JSON cache grouped by model digest."""

    def __init__(self, root=None):
        self.root = Path(root or config.NEWS_EXTRACTION_CACHE_ROOT)
        self._hits = 0
        self._misses = 0

    def get(self, cache_key: str, model_digest: str) -> Optional[NewsFeature]:
        path = self._entry_path(cache_key, model_digest)
        if not path.exists():
            self._misses += 1
            self._record_event(model_digest, "miss", cache_key)
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"corrupt news extraction cache entry: {path}") from exc
        self._hits += 1
        self._record_event(model_digest, "hit", cache_key)
        return news_feature_from_row(payload)

    def put(self, cache_key: str, model_digest: str, feature: NewsFeature) -> None:
        path = self._entry_path(cache_key, model_digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            feature.to_row(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        path.write_text(payload + "\n", encoding="utf-8")
        self._refresh_manifest(model_digest)

    def cache_stats(self) -> dict:
        cached_count = 0
        if self.root.exists():
            cached_count = len([p for p in self.root.glob("*/*.json") if p.name != "_manifest.json"])
        return {
            "hits": self._hits,
            "misses": self._misses,
            "cached_count": cached_count,
            "root": self.root.as_posix(),
        }

    def _entry_path(self, cache_key: str, model_digest: str) -> Path:
        return self.root / model_digest / f"{cache_key}.json"

    def _manifest_path(self, model_digest: str) -> Path:
        return self.root / model_digest / "_manifest.json"

    def _load_manifest(self, model_digest: str) -> dict:
        path = self._manifest_path(model_digest)
        if not path.exists():
            return {
                "model_digest": model_digest,
                "cached_count": 0,
                "hits": 0,
                "misses": 0,
                "last_update": None,
                "events": [],
            }
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"corrupt news extraction cache manifest: {path}") from exc

    def _write_manifest(self, model_digest: str, manifest: dict) -> None:
        path = self._manifest_path(model_digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest["model_digest"] = model_digest
        manifest["cached_count"] = len(
            [p for p in path.parent.glob("*.json") if p.name != "_manifest.json"]
        )
        manifest["last_update"] = _utc_now()
        manifest["events"] = manifest.get("events", [])[-100:]
        path.write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def _record_event(self, model_digest: str, kind: str, cache_key: str) -> None:
        manifest = self._load_manifest(model_digest)
        counter = "misses" if kind == "miss" else "hits"
        manifest[counter] = int(manifest.get(counter, 0)) + 1
        events = manifest.get("events", [])
        events.append({"ts": _utc_now(), "event": kind, "cache_key": cache_key[:16]})
        manifest["events"] = events[-100:]
        self._write_manifest(model_digest, manifest)

    def _refresh_manifest(self, model_digest: str) -> None:
        manifest = self._load_manifest(model_digest)
        self._write_manifest(model_digest, manifest)
