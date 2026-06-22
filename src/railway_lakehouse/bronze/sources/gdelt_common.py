"""Shared GDELT request helpers for Bronze collectors."""

from __future__ import annotations

import email.utils
import time
from collections.abc import Callable
from datetime import datetime, timezone

import requests

DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
DOC_API_MAX_RECORDS = 200
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_SLEEP_SECONDS = 1.0
HTTP_TOO_MANY_REQUESTS = 429
USER_AGENT = "railway-lakehouse-bronze/1.0"
REQUEST_HEADERS = {"User-Agent": USER_AGENT}

Sleep = Callable[[float], object]


def bounded_max_records(max_records: int) -> int:
    if max_records < 1:
        raise ValueError("max_records must be at least 1")
    return min(max_records, DOC_API_MAX_RECORDS)


def get_with_rate_limit_retries(
    get: Callable[..., requests.Response],
    url: str,
    *,
    params: dict | None = None,
    timeout: int,
    headers: dict | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_sleep_seconds: float = DEFAULT_RETRY_SLEEP_SECONDS,
    sleep: Sleep = time.sleep,
) -> requests.Response:
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")
    if retry_sleep_seconds < 0:
        raise ValueError("retry_sleep_seconds must be non-negative")

    response = None
    for attempt in range(max_retries + 1):
        response = get(url, params=params, timeout=timeout, headers=headers or REQUEST_HEADERS)
        if response.status_code != HTTP_TOO_MANY_REQUESTS or attempt == max_retries:
            return response
        sleep(_retry_delay_seconds(response, attempt, retry_sleep_seconds))

    return response


def _retry_delay_seconds(
    response: requests.Response,
    attempt: int,
    retry_sleep_seconds: float,
) -> float:
    retry_after = _parse_retry_after(response.headers.get("Retry-After"))
    if retry_after is not None:
        return retry_after
    return retry_sleep_seconds * (2 ** attempt)


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        seconds = None
    if seconds is not None and seconds >= 0:
        return seconds

    try:
        retry_at = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max((retry_at - datetime.now(timezone.utc)).total_seconds(), 0.0)
