"""Deterministic sentiment encoder for Silver news rows.

The module is safe to import without transformers or model weights installed.
The Hugging Face pipeline is loaded lazily on first encode/health_check call.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

logger = logging.getLogger("silver.news.sentiment_encoder")

MODEL_NAME = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
MODEL_REVISION = "f2f1202b1bdeb07342385c3f807f9c07cd8f5cf8"
DEVICE = -1
MODEL_MAX_LENGTH = 512
LABELS = {"negative", "neutral", "positive"}
LABEL_ID_MAP = {"label_0": "negative", "label_1": "neutral", "label_2": "positive"}

_instance: Optional["SentimentEncoder"] = None


class SentimentEncoder:
    """Small wrapper around a pinned Hugging Face sentiment pipeline."""

    def __init__(self, pipeline_factory: Optional[Callable] = None):
        self._pipeline_factory = pipeline_factory
        self._pipeline = None
        self._load_failed = False

    def encode(self, text: str) -> Optional[dict]:
        """Return ``{"label": <sentiment>, "score": <softmax>}`` or ``None``."""
        if not str(text or "").strip():
            return None
        pipe = self._ensure_pipeline()
        if pipe is None:
            return None
        try:
            raw = pipe(str(text), truncation=True, max_length=MODEL_MAX_LENGTH)
            item = self._first_result(raw)
            if item is None:
                return None
            label = _normalize_label(item.get("label"))
            score = _score(item.get("score"))
            if label is None or score is None:
                return None
            return {"label": label, "score": score}
        except Exception as exc:  # pragma: no cover - exact HF failures vary by install
            logger.warning("sentiment inference failed: %s", exc)
            return None

    def health_check(self) -> bool:
        """Return True when the pinned pipeline can be loaded."""
        return self._ensure_pipeline() is not None

    def _ensure_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        if self._load_failed:
            return None
        try:
            factory = self._pipeline_factory or _default_pipeline_factory()
            if factory is None:
                self._load_failed = True
                return None
            self._pipeline = factory(
                "sentiment-analysis",
                model=MODEL_NAME,
                tokenizer=MODEL_NAME,
                revision=MODEL_REVISION,
                device=DEVICE,
            )
            return self._pipeline
        except Exception as exc:
            self._load_failed = True
            logger.warning("sentiment encoder unavailable: %s", exc)
            return None

    @staticmethod
    def _first_result(raw):
        if isinstance(raw, dict):
            return raw
        if not isinstance(raw, list) or not raw:
            return None
        first = raw[0]
        if isinstance(first, list):
            if not first:
                return None
            return max(first, key=lambda item: _score(item.get("score")) or -1.0)
        return first if isinstance(first, dict) else None


def get_encoder() -> SentimentEncoder:
    """Return the process-local sentiment encoder singleton."""
    global _instance
    if _instance is None:
        _instance = SentimentEncoder()
    return _instance


def health_check() -> bool:
    """Module-level health check mirroring the Ollama client surface."""
    return get_encoder().health_check()


def _default_pipeline_factory():
    try:
        from transformers import pipeline
        from transformers.utils import is_tf_available, is_torch_available
    except Exception as exc:
        logger.debug("transformers unavailable for sentiment encoder: %s", exc)
        return None
    if not (is_torch_available() or is_tf_available()):
        logger.debug("transformers installed without a torch/tensorflow backend")
        return None
    return pipeline


def _normalize_label(label) -> Optional[str]:
    text = str(label or "").strip().lower()
    if not text:
        return None
    text = LABEL_ID_MAP.get(text, text)
    return text if text in LABELS else None


def _score(value) -> Optional[float]:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0.0 or score > 1.0:
        return None
    return score
