import datetime as dt

import pytest

from railway_lakehouse.bronze.sources import gdelt, past_recordings


pytestmark = pytest.mark.unit


class _GdeltResponse:
    def __init__(self, status_code, content=b'{"articles":[]}', headers=None, url="https://api.gdeltproject.org/test"):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.url = url


class _GdeltSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout, "headers": headers})
        if not self.responses:
            raise AssertionError("unexpected GDELT request")
        response = self.responses.pop(0)
        response.url = f"{url}?call={len(self.calls)}"
        return response


class _RecordingLander:
    def __init__(self):
        self.landed = []

    def land(self, artifact):
        self.landed.append(artifact)
        return (
            f"bronze/{artifact.domain}/{artifact.source}/"
            f"{artifact.dataset_id}/{artifact.filename}"
        )


def test_gdelt_ingest_retries_429_and_lands_raw_success(monkeypatch):
    monkeypatch.setattr(gdelt, "NATIONAL_SCOPE", ["HU"])
    session = _GdeltSession(
        [
            _GdeltResponse(429, b"rate limited", headers={"Retry-After": "0.25"}),
            _GdeltResponse(200, b'{"articles":[{"title":"rail"}]}'),
        ]
    )
    lander = _RecordingLander()
    sleeps = []

    paths = gdelt.ingest(
        lander,
        session=session,
        timespan="1d",
        max_retries=1,
        retry_sleep_seconds=0.1,
        sleep=sleeps.append,
    )

    assert sleeps == [0.25]
    assert len(session.calls) == 2
    assert all(call["params"]["maxrecords"] == gdelt.DOC_API_MAX_RECORDS for call in session.calls)
    assert session.calls[0]["headers"]["User-Agent"].startswith("railway-lakehouse")
    assert paths == ["bronze/news/gdelt/HU/gdelt_doc_HU_1d.json"]
    artifact = lander.landed[0]
    assert artifact.content == b'{"articles":[{"title":"rail"}]}'
    assert artifact.extra["timespan"] == "1d"


def test_gdelt_ingest_stops_after_retry_limit_without_landing(monkeypatch):
    monkeypatch.setattr(gdelt, "NATIONAL_SCOPE", ["HU"])
    session = _GdeltSession([_GdeltResponse(429, b"first"), _GdeltResponse(429, b"second")])
    lander = _RecordingLander()
    sleeps = []

    paths = gdelt.ingest(
        lander,
        session=session,
        max_retries=1,
        retry_sleep_seconds=0.1,
        sleep=sleeps.append,
    )

    assert paths == []
    assert lander.landed == []
    assert len(session.calls) == 2
    assert sleeps == [0.1]


def test_past_recordings_doc_api_honors_max_pages_and_retries_429():
    session = _GdeltSession(
        [
            _GdeltResponse(429, b"rate limited", headers={"Retry-After": "0.2"}),
            _GdeltResponse(200, b'{"articles":[{"url":"https://example.test/rail"}]}'),
            _GdeltResponse(200, b'{"articles":[{"url":"https://example.test/second"}]}'),
        ]
    )
    lander = _RecordingLander()
    sleeps = []

    got = past_recordings.backfill_doc_api(
        lander,
        start=dt.date(2024, 1, 1),
        end=dt.date(2024, 4, 1),
        target=10,
        max_pages=1,
        session=session,
        max_retries=1,
        retry_sleep_seconds=0.1,
        sleep=sleeps.append,
    )

    assert got == 1
    assert sleeps == [0.2]
    assert len(session.calls) == 2
    assert session.calls[0]["params"]["maxrecords"] == gdelt.DOC_API_MAX_RECORDS
    assert len(lander.landed) == 1
    assert lander.landed[0].content == b'{"articles":[{"url":"https://example.test/rail"}]}'
    assert lander.landed[0].extra["window_start"] == "2024-01-01"


def test_past_recordings_doc_api_dry_run_makes_no_requests_or_landing():
    session = _GdeltSession([])
    lander = _RecordingLander()

    got = past_recordings.backfill_doc_api(
        lander,
        start=dt.date(2024, 1, 1),
        end=dt.date(2024, 4, 1),
        target=10,
        max_pages=2,
        session=session,
        dry_run=True,
    )

    assert got == 0
    assert session.calls == []
    assert lander.landed == []


def test_past_recordings_ingest_defaults_to_one_history_page():
    session = _GdeltSession([_GdeltResponse(429, b"rate limited")])
    lander = _RecordingLander()

    got = past_recordings.ingest(
        lander,
        start=dt.date(2024, 1, 1),
        end=dt.date(2024, 4, 1),
        target_articles=10,
        session=session,
        max_retries=0,
    )

    assert got == 0
    assert len(session.calls) == 1
    assert lander.landed == []


def test_past_recordings_cli_defaults_to_one_history_page_and_accepts_dry_run():
    args = past_recordings._parse_args(["--dry-run"])

    assert args.dry_run is True
    assert args.max_pages == 1
