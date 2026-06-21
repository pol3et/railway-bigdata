import hashlib
import json

import pytest

from railway_lakehouse.bronze.lander import RawArtifact, build_meta_dict
from railway_lakehouse.bronze.sources.eurostat import discover_rail_datasets
from railway_lakehouse.bronze.sources.gdelt import build_query
from railway_lakehouse.bronze.sources import worldbank
from railway_lakehouse.bronze.sources.worldbank import (
    CONFIRMED_RAIL_INDICATORS,
    KNOWN_RAIL_INDICATORS,
    discover_rail_indicators,
    is_error_payload,
    series_has_observations,
)


pytestmark = pytest.mark.unit


def test_build_meta_dict_records_size_checksum_and_run_id():
    artifact = RawArtifact(
        domain="stats",
        source="eurostat",
        dataset_id="rail_demo",
        filename="rail_demo.tsv.gz",
        content=b"rail-bytes",
        source_url="https://example.test/rail_demo.tsv.gz",
    )

    meta = build_meta_dict(artifact, "run-001")

    assert meta == {
        "source_system": "eurostat",
        "dataset_id": "rail_demo",
        "byte_size": len(b"rail-bytes"),
        "sha256": hashlib.sha256(b"rail-bytes").hexdigest(),
        "ingest_run_id": "run-001",
    }


def test_discover_rail_datasets_keeps_rail_codes_and_excludes_false_positives():
    toc_text = "\n".join(
        [
            "Railway passenger transport\trail_passengers",
            "Regional rail transport\ttran_r_rail_demo",
            "Transport safety railway accidents\ttran_sf_accidents",
            "Road trailer registrations\ttran_trailer_demo",
            "Aggregate railway table\tt_rail_table",
            "Air transport\tavia_demo",
        ]
    )

    assert discover_rail_datasets(toc_text) == [
        "rail_passengers",
        "tran_r_rail_demo",
        "tran_sf_accidents",
    ]


def test_discover_rail_indicators_unions_catalogue_hits_with_known_fallbacks():
    catalogue = [
        {"page": 1},
        [
            {"id": "IS.RRS.EXTRA", "name": "Rail infrastructure", "sourceNote": ""},
            {"id": "ROAD.ONLY", "name": "Road infrastructure", "sourceNote": ""},
        ],
    ]

    ids = discover_rail_indicators(catalogue)

    assert "IS.RRS.EXTRA" in ids
    assert "ROAD.ONLY" not in ids
    for known in KNOWN_RAIL_INDICATORS:
        assert known in ids


def test_discover_rail_indicators_returns_known_fallbacks_when_catalogue_empty():
    assert discover_rail_indicators([]) == KNOWN_RAIL_INDICATORS


def test_gdelt_query_includes_rail_terms_and_country_restriction():
    query = build_query("HU")

    assert query.startswith("(")
    assert "sourcecountry:HU" in query
    assert "railway" in query
    assert "train" in query
    assert "Bahn" in query
    assert "MAV" in query


# --- World Bank: discovery precision + response validation -------------------


def test_discover_rail_indicators_ignores_substring_false_positives():
    # "trail", "trailer", "curtail" all contain "rail" as a substring but are
    # not rail indicators; word-anchored matching must reject them.
    catalogue = [
        {"page": 1},
        [
            {"id": "GOOD.RAIL", "name": "Railway freight volume", "sourceNote": ""},
            {"id": "BAD.TRAILER", "name": "Trailer registrations", "sourceNote": ""},
            {"id": "BAD.TRAIL", "name": "Forest trail length", "sourceNote": ""},
            {"id": "BAD.CURTAIL", "name": "Subsidies curtailed", "sourceNote": ""},
        ],
    ]

    ids = discover_rail_indicators(catalogue)

    assert "GOOD.RAIL" in ids
    assert "BAD.TRAILER" not in ids
    assert "BAD.TRAIL" not in ids
    assert "BAD.CURTAIL" not in ids


def test_is_error_payload_detects_worldbank_error_envelope():
    # Exact shape observed live for an archived id (BM.GSR.TRAN.CD), which the
    # API returns with HTTP 200, not 404.
    err = [
        {
            "message": [
                {
                    "id": "175",
                    "key": "Invalid format",
                    "value": "The indicator was not found. It may have been "
                    "deleted or archived.",
                }
            ]
        }
    ]

    assert is_error_payload(err) is True
    assert series_has_observations(err) is False


def test_series_has_observations_accepts_real_time_series():
    # Shape observed live for IS.RRS.PASG.KM (Hungary). Recent years are null
    # but older years carry values -- a null value is still a real observation.
    series = [
        {"page": 1, "pages": 14, "per_page": 5, "total": 66},
        [
            {"indicator": {"id": "IS.RRS.PASG.KM"}, "country": {"id": "HU"},
             "date": "2022", "value": None},
            {"indicator": {"id": "IS.RRS.PASG.KM"}, "country": {"id": "HU"},
             "date": "2021", "value": 5435.389},
        ],
    ]

    assert series_has_observations(series) is True


def test_series_has_observations_rejects_empty_and_malformed_bodies():
    assert series_has_observations([{"total": 0}, None]) is False          # no data
    assert series_has_observations([{"total": 0}, []]) is False            # empty rows
    assert series_has_observations([{"page": 1}]) is False                 # truncated
    assert series_has_observations(None) is False                          # garbage


# --- World Bank: mocked-HTTP ingest contract --------------------------------


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.content = b"" if payload is None else json.dumps(payload).encode()

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"HTTP {self.status_code}")


class _FakeSession:
    """Routes by substring of the requested URL."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append(url)
        for key, resp in self.routes.items():
            if key in url:
                return resp
        raise AssertionError(f"unexpected url: {url}")


class _RecordingLander:
    def __init__(self):
        self.landed = []

    def land(self, artifact):
        self.landed.append(artifact)
        return (
            f"bronze/{artifact.domain}/{artifact.source}/"
            f"{artifact.dataset_id}/{artifact.filename}"
        )


def _valid_series(indicator):
    return [
        {"page": 1, "pages": 1, "per_page": 5, "total": 2},
        [
            {"indicator": {"id": indicator}, "country": {"id": "HU"},
             "date": "2021", "value": 1.0},
            {"indicator": {"id": indicator}, "country": {"id": "HU"},
             "date": "2020", "value": 2.0},
        ],
    ]


_ERROR_PAYLOAD = [
    {"message": [{"id": "175", "key": "Invalid format",
                  "value": "The indicator was not found."}]}
]


def test_ingest_skips_error_payloads_and_lands_real_series():
    # Empty catalogue -> discovery falls back to the confirmed allowlist, so we
    # know exactly which three series get requested.
    routes = {
        "v2/indicator?": _FakeResponse([{"page": 1}, []]),  # catalogue
        "IS.RRS.TOTL.KM": _FakeResponse(_ERROR_PAYLOAD),    # 200 + error body
        "IS.RRS.GOOD.MT.K6": _FakeResponse(_valid_series("IS.RRS.GOOD.MT.K6")),
        "IS.RRS.PASG.KM": _FakeResponse(_valid_series("IS.RRS.PASG.KM")),
    }
    session = _FakeSession(routes)
    lander = _RecordingLander()

    paths = worldbank.ingest(lander, session=session)

    landed_ids = {a.dataset_id for a in lander.landed}
    # catalogue is always landed; the error-payload indicator must NOT be
    assert "_catalogue_indicators" in landed_ids
    assert "IS.RRS.TOTL.KM" not in landed_ids
    assert landed_ids >= {"IS.RRS.GOOD.MT.K6", "IS.RRS.PASG.KM"}
    # returned paths cover only the real series (not the catalogue)
    assert len(paths) == 2
    assert all("IS.RRS.TOTL.KM" not in p for p in paths)
