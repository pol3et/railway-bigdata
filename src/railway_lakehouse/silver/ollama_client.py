"""
Thin Ollama client for the Silver layer.

Ollama runs locally (default http://localhost:11434). We use it for exactly two
bounded jobs (see SILVER_DESIGN.md): a one-off column->English crosswalk for the
HU/DE statistical headers, and per-article feature extraction from news text.
We never push numeric table rows through it.

Design choices that matter for a data pipeline:
  * deterministic decoding (temperature=0) so re-runs are reproducible;
  * JSON-constrained output (format="json", or a JSON schema on newer Ollama);
  * bounded retries with backoff; a failed call returns None, never a guess;
  * the caller validates every payload against a schema (schema.py) — the LLM
    output is treated as untrusted until validated.
"""
import json
import time
import logging
from typing import Any

import requests

from .config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_NUM_RETRIES

logger = logging.getLogger("silver.ollama")


def generate_json(prompt: str, *, model: str | None = None,
                  schema: dict | None = None, system: str | None = None,
                  temperature: float = 0.0) -> dict | list | None:
    """Call Ollama /api/generate in JSON mode and return the parsed object.

    Returns None on transport failure or unparseable output (caller decides what
    to do — we never fabricate a result). `schema`, if given, is passed as the
    `format` field (structured outputs on Ollama >= 0.5); otherwise format="json".
    """
    url = f"{OLLAMA_HOST}/api/generate"
    payload: dict[str, Any] = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": schema if schema else "json",
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system

    last_err = None
    for attempt in range(1, OLLAMA_NUM_RETRIES + 1):
        try:
            r = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}"
                logger.warning("Ollama %s (attempt %d/%d)", last_err, attempt, OLLAMA_NUM_RETRIES)
                time.sleep(min(2 ** attempt, 10)); continue
            body = r.json()
            text = body.get("response", "")
            return _parse_json_loose(text)
        except requests.RequestException as e:
            last_err = str(e)
            logger.warning("Ollama call failed (attempt %d/%d): %s", attempt, OLLAMA_NUM_RETRIES, e)
            time.sleep(min(2 ** attempt, 10))
    logger.error("Ollama generate_json giving up after %d attempts: %s",
                 OLLAMA_NUM_RETRIES, last_err)
    return None


def _parse_json_loose(text: str) -> dict | list | None:
    """Parse model output as JSON, tolerating code fences / leading prose."""
    if not text:
        return None
    text = text.strip()
    # strip ```json ... ``` fences if present
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    # try direct, then the first {...} or [...] block
    for candidate in (text, _first_braced(text)):
        if candidate is None:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    logger.warning("Ollama output was not valid JSON: %.120s", text)
    return None


def _first_braced(text: str) -> str | None:
    for open_c, close_c in (("{", "}"), ("[", "]")):
        i = text.find(open_c); j = text.rfind(close_c)
        if 0 <= i < j:
            return text[i:j + 1]
    return None


def health_check() -> bool:
    """True if the Ollama server is reachable and the model is available."""
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        if r.status_code != 200:
            return False
        names = {m.get("name", "").split(":")[0] for m in r.json().get("models", [])}
        return OLLAMA_MODEL.split(":")[0] in names
    except requests.RequestException:
        return False
