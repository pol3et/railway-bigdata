"""Deterministic Silver news language identification.

Uses `lingua-language-detector==2.2.0`, the Rust-backed Python package from
https://github.com/pemistahl/lingua-py. The detector is intentionally restricted
to the project languages EN/DE/HU so short railway titles are classified within
the supported downstream model routes.

Model identity digest:
`842c69ce2d0dc5f8d07240361f974969cd09915a53b8eb137a9a731ffc3df738`
for `lingua-language-detector==2.2.0|languages=en,de,hu`.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from lingua import Language, LanguageDetectorBuilder

LANGUAGE_ID_PACKAGE = "lingua-language-detector"
LANGUAGE_ID_VERSION = "2.2.0"
LANGUAGE_ID_LANGUAGES = ("en", "de", "hu")
LANGUAGE_ID_MODEL_DIGEST = "842c69ce2d0dc5f8d07240361f974969cd09915a53b8eb137a9a731ffc3df738"

_LINGUA_LANGUAGES = (
    Language.ENGLISH,
    Language.GERMAN,
    Language.HUNGARIAN,
)


@lru_cache(maxsize=1)
def _detector():
    return LanguageDetectorBuilder.from_languages(*_LINGUA_LANGUAGES).build()


def _normalize_text(text: str | None) -> str:
    return " ".join(str(text or "").split())


@lru_cache(maxsize=4096)
def _identify_normalized(text: str) -> Optional[str]:
    language = _detector().detect_language_of(text)
    if language is None:
        return None
    code = getattr(language.iso_code_639_1, "name", "")
    return code.lower() if code else None


def identify_language(text: str | None) -> Optional[str]:
    """Return a lowercase ISO 639-1 language code for text, or None.

    This function is deterministic and never calls an LLM or external service.
    Results are memoized per normalized text for the current Python process.
    """
    normalized = _normalize_text(text)
    if not normalized:
        return None
    return _identify_normalized(normalized)
