import hashlib

import pytest

from railway_lakehouse.bronze.lander import RawArtifact, build_meta_dict
from railway_lakehouse.bronze.sources.eurostat import discover_rail_datasets
from railway_lakehouse.bronze.sources.gdelt import build_query
from railway_lakehouse.bronze.sources.worldbank import (
    KNOWN_RAIL_INDICATORS,
    discover_rail_indicators,
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
