import hashlib
import io
import json
import zipfile

import pytest

from railway_lakehouse.bronze.lander import RawArtifact, build_meta_dict
from railway_lakehouse.bronze.sources import ksh
from railway_lakehouse.bronze.sources.eurostat import discover_rail_datasets
from railway_lakehouse.bronze.sources.gdelt import build_query
from railway_lakehouse.bronze.sources import worldbank
from railway_lakehouse.bronze.sources.rss_media import _all_feeds

from railway_lakehouse.bronze.sources.ksh import (
    KSH_RAIL_TABLES,
    KSH_RETIRED_SEEDS,
    is_valid_table_response,
    looks_like_xlsx,
)
from railway_lakehouse.bronze.sources.worldbank import (
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


def test_discover_rail_datasets_strips_quoted_dataset_codes():
    toc_text = "\n".join(
        [
            'Railway passenger transport\t"rail_pa_typepas"',
            "Rail freight transport\t'rail_go_typeall'",
        ]
    )

    assert discover_rail_datasets(toc_text) == ["rail_go_typeall", "rail_pa_typepas"]


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


# --- KSH: curated STADAT seeds + XLSX validation -----------------------------

def _zip_bytes(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, body in members.items():
            archive.writestr(name, body)
    return buffer.getvalue()


_XLSX_BYTES = _zip_bytes(
    {
        "[Content_Types].xml": "<Types/>",
        "_rels/.rels": "<Relationships/>",
        "xl/workbook.xml": "<workbook/>",
    }
)
_ZIP_WITHOUT_WORKBOOK = _zip_bytes({"readme.txt": "not an XLSX workbook"})


def test_looks_like_xlsx_accepts_workbook_container_rejects_html_empty_and_fake_zip():
    assert looks_like_xlsx(_XLSX_BYTES) is True
    assert looks_like_xlsx(b"<!DOCTYPE html><html>error</html>") is False
    assert looks_like_xlsx(b"PK\x03\x04not a real zip") is False
    assert looks_like_xlsx(_ZIP_WITHOUT_WORKBOOK) is False
    assert looks_like_xlsx(b"") is False
    assert looks_like_xlsx(None) is False


def test_is_valid_table_response_requires_200_and_xlsx_bytes():
    assert is_valid_table_response(200, _XLSX_BYTES) is True
    assert is_valid_table_response(404, _XLSX_BYTES) is False
    assert is_valid_table_response(200, b"") is False
    assert is_valid_table_response(200, b"<html>") is False


def test_curated_tables_exclude_retired_mislabelled_codes():
    active_codes = {table.code for table in KSH_RAIL_TABLES}

    assert "sza0010" not in active_codes
    assert "sza0006" not in active_codes
    assert "sza0010" in KSH_RETIRED_SEEDS
    assert "sza0006" in KSH_RETIRED_SEEDS

    freight = next(table for table in KSH_RAIL_TABLES if table.code == "sza0009")
    assert freight.dataset_id == "ksh_rail_freight"


class _FakeXlsxResponse:
    def __init__(self, content, status=200, content_type="application/octet-stream"):
        self.content = content
        self.status_code = status
        self.headers = {"Content-Type": content_type}


class _FakeKshSession:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, timeout=None, headers=None):
        self.calls.append(url)
        for code, response in self.routes.items():
            if code in url:
                return response
        raise AssertionError(f"unexpected url: {url}")


def test_ksh_ingest_lands_valid_xlsx_and_skips_404_and_empty_200():
    broken = {
        "sza0016": _FakeXlsxResponse(b"", status=404),
        "sza0030": _FakeXlsxResponse(b"<html>error</html>", status=200, content_type="text/html"),
    }
    routes = {
        table.code: broken.get(table.code, _FakeXlsxResponse(_XLSX_BYTES))
        for table in KSH_RAIL_TABLES
    }
    session = _FakeKshSession(routes)
    lander = _RecordingLander()

    count = ksh.ingest(lander, session=session)

    landed_ids = {artifact.dataset_id for artifact in lander.landed}
    assert count == len(KSH_RAIL_TABLES) - 2
    assert "ksh_rail_freight" in landed_ids
    assert "ksh_rail_passenger" not in landed_ids
    assert "ksh_rail_network" not in landed_ids

    freight = next(artifact for artifact in lander.landed if artifact.dataset_id == "ksh_rail_freight")
    assert freight.extra["stadat_code"] == "sza0009"
    assert freight.extra["discovery"] == "curated_rail_table"
    assert freight.filename == "sza0009.xlsx"


def test_rss_feed_registry_includes_hu_and_at_feeds():
    feeds = _all_feeds()
    feed_ids = {feed_id for feed_id, _url, _geo in feeds}
    geos = {geo for _feed_id, _url, geo in feeds}

    assert "HU" in geos
    assert "AT" in geos
    assert "hu_telex" in feed_ids
    assert "at_orf" in feed_ids
    assert all(url.startswith("https://") for _feed_id, url, _geo in feeds)
