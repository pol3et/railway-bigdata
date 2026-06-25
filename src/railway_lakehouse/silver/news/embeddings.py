"""Sentence embeddings and deterministic near-duplicate grouping for Silver news."""
from __future__ import annotations

import hashlib
import logging
import math
import time
from functools import lru_cache
from typing import Any

import numpy as np

from .. import config

logger = logging.getLogger("silver.news.embeddings")

DEFAULT_EMBEDDING_MODEL = config.NEWS_EMBEDDING_MODEL
DEFAULT_DEDUP_THRESHOLD = 0.95


@lru_cache(maxsize=4)
def load_embedding_model(model_name: str = DEFAULT_EMBEDDING_MODEL):
    """Load and cache a SentenceTransformer embedding model."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def embed_text(text: str | None, model) -> list[float] | None:
    """Encode one article text into a normalized Python float list."""
    if text is None:
        return None
    text = str(text).strip()
    if not text:
        return None
    encoded_text = text if text.startswith(("query: ", "passage: ")) else f"passage: {text}"
    embedding = model.encode(
        encoded_text,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    arr = np.asarray(embedding, dtype=np.float32)
    if arr.ndim == 2:
        arr = arr[0]
    if arr.ndim != 1 or arr.size == 0:
        return None
    return [float(value) for value in arr.tolist()]


def compute_embeddings(
    news_rows: list,
    *,
    use_model: bool = True,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> list:
    """Populate missing ``text_embedding`` values on NewsFeature-like rows."""
    rows = list(news_rows or [])
    if not rows:
        return rows
    missing = [row for row in rows if not _has_embedding(_get(row, "text_embedding"))]
    if not missing:
        logger.info("news embeddings: processed=0 skipped_existing=%d", len(rows))
        return rows
    if not use_model:
        logger.info("news embeddings skipped: use_model=false rows=%d", len(missing))
        return rows

    started = time.perf_counter()
    try:
        model = load_embedding_model(model_name)
    except Exception as exc:
        logger.warning("news embeddings skipped: %s", exc)
        return rows

    processed = 0
    for row in missing:
        text = _embedding_text(row)
        try:
            vector = embed_text(text, model)
        except Exception as exc:
            logger.warning("news embedding skipped for %s: %s", _article_id(row), exc)
            continue
        if vector is None:
            continue
        _set(row, "text_embedding", vector)
        _set(row, "text_embedding_model", model_name)
        processed += 1
    logger.info(
        "news embeddings: processed=%d skipped_existing=%d model_load_seconds=%.3f",
        processed,
        len(rows) - len(missing),
        time.perf_counter() - started,
    )
    return rows


def cluster_near_duplicates(
    news_rows: list,
    *,
    threshold: float = DEFAULT_DEDUP_THRESHOLD,
) -> list:
    """Assign deterministic cross-lingual dedup groups from existing embeddings."""
    rows = list(news_rows or [])
    usable = []
    for row in rows:
        vector = _clean_embedding(_get(row, "text_embedding"))
        if vector is not None:
            usable.append((_article_id(row), row, vector))
        else:
            _set(row, "cross_lingual_dedup_id", None)
            _set(row, "is_duplicate", None)

    if len(usable) < 2:
        for _, row, _ in usable:
            _set(row, "cross_lingual_dedup_id", None)
            _set(row, "is_duplicate", False)
        logger.warning("news dedup skipped: no usable embeddings or fewer than two usable embeddings")
        return rows

    dims = {len(vector) for _, _, vector in usable}
    if len(dims) != 1:
        logger.warning("news dedup skipped: embedding dimensions differ")
        for row in rows:
            _set(row, "cross_lingual_dedup_id", None)
            _set(row, "is_duplicate", None)
        return rows

    usable.sort(key=lambda item: item[0])
    parent = {article_id: article_id for article_id, _, _ in usable}

    for left_index, (left_id, _, left_vector) in enumerate(usable):
        for right_id, _, right_vector in usable[left_index + 1:]:
            if _cosine_similarity(left_vector, right_vector) >= threshold:
                _union(parent, left_id, right_id)

    groups: dict[str, list[tuple[str, Any]]] = {}
    for article_id, row, _ in usable:
        groups.setdefault(_find(parent, article_id), []).append((article_id, row))

    for members in groups.values():
        members.sort(key=lambda item: item[0])
        if len(members) == 1:
            _, row = members[0]
            _set(row, "cross_lingual_dedup_id", None)
            _set(row, "is_duplicate", False)
            continue
        ids = [article_id for article_id, _ in members]
        group_id = "dedup_" + hashlib.sha256("|".join(ids).encode("utf-8")).hexdigest()[:16]
        canonical = ids[0]
        for article_id, row in members:
            _set(row, "cross_lingual_dedup_id", group_id)
            _set(row, "is_duplicate", article_id != canonical)
    return rows


def _embedding_text(row) -> str | None:
    for key in ("summary_en", "title", "body", "article_id"):
        value = _get(row, key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _has_embedding(value) -> bool:
    return isinstance(value, (list, tuple, np.ndarray)) and len(value) > 0


def _clean_embedding(value) -> list[float] | None:
    if not _has_embedding(value):
        return None
    out = []
    for item in value:
        try:
            out.append(float(item))
        except (TypeError, ValueError):
            return None
    if not out or not any(abs(value) > 0 for value in out):
        return None
    return out


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _article_id(row) -> str:
    return str(_get(row, "article_id") or "")


def _get(row, key: str):
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def _set(row, key: str, value) -> None:
    if isinstance(row, dict):
        row[key] = value
    else:
        setattr(row, key, value)


def _find(parent: dict[str, str], item: str) -> str:
    while parent[item] != item:
        parent[item] = parent[parent[item]]
        item = parent[item]
    return item


def _union(parent: dict[str, str], left: str, right: str) -> None:
    left_root = _find(parent, left)
    right_root = _find(parent, right)
    if left_root == right_root:
        return
    if left_root < right_root:
        parent[right_root] = left_root
    else:
        parent[left_root] = right_root
