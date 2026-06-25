from pathlib import Path

import pandas as pd
import pytest

from railway_lakehouse.silver.news.gdelt import parse_gdelt_artlist_json
from railway_lakehouse.silver.news.rss import parse_rss_xml
from railway_lakehouse.silver.stats import load as stats_load

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent / "fixtures" / "silver"


def _sorted_long(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.sort_values(["geo", "year", "source_dataset", "source_column", "unit"])
        .reset_index(drop=True)
    )


def test_parse_rss_xml_golden_fixture():
    xml_text = (FIXTURES / "news" / "rss_real_example.xml").read_text(encoding="utf-8")

    records = parse_rss_xml(xml_text, source="rss_fixture")

    assert len(records) == 3
    assert len({record.article_id for record in records}) == 3
    assert all(record.source == "rss_fixture" for record in records)
    assert all(record.title for record in records)
    assert all(record.published_date for record in records)
    assert records[0].body.startswith("Full article text")
    assert "Short teaser" not in records[0].body
    assert records[1].body.startswith("Night train rolling stock")
    assert any(record.url == "" for record in records)


def test_parse_gdelt_artlist_json_golden_fixture(caplog):
    json_text = (FIXTURES / "news" / "gdelt_real_example.json").read_text(encoding="utf-8")

    caplog.set_level("WARNING")
    records = parse_gdelt_artlist_json(json_text)

    assert len(records) == 4
    assert len({record.article_id for record in records}) == 4
    assert all(record.source == "gdelt" for record in records)
    assert all(record.title for record in records)
    assert all(record.published_date for record in records)
    assert all(record.body for record in records)
    assert any(record.url.startswith("https://m.example.test/") for record in records)
    assert "dropped 2 malformed articles" in caplog.text


def test_load_worldbank_frame_golden_fixture():
    raw = (FIXTURES / "stats" / "worldbank_real_example.json").read_bytes()

    frame = stats_load.load_worldbank_frame(raw, "IS.RRS.PASG.KM")

    assert list(frame.columns) == stats_load._LONG_COLS
    assert len(frame) == 3
    assert {"HU", "AT"}.issubset(set(frame["geo"]))
    assert set(frame["source_system"]) == {"worldbank"}
    assert set(frame["source_dataset"]) == {"IS.RRS.PASG.KM"}
    assert set(frame["source_column"]) == {"rail_passenger_km"}
    assert frame["year"].dropna().astype(int).isin([2021, 2022]).all()
    assert pd.to_numeric(frame["value"], errors="coerce").notna().sum() == 2


def test_load_eurostat_frame_golden_fixture_matches_gzip_variant():
    raw = (FIXTURES / "stats" / "eurostat_real_example.tsv").read_bytes()
    gz_raw = (FIXTURES / "stats" / "eurostat_real_example.tsv.gz").read_bytes()

    frame = stats_load.load_eurostat_frame(raw, "rail_pa_total")
    gz_frame = stats_load.load_eurostat_frame(gz_raw, "rail_pa_total")

    assert list(frame.columns) == stats_load._LONG_COLS
    assert len(frame) == 10
    assert {"HU", "AT", "EU27_2020"}.issubset(set(frame["geo"]))
    assert {"rail_passenger_km", "rail_passengers"} == set(frame["source_column"])
    assert set(frame["unit"]) == {"MIO_PKM", "THS_PAS"}
    assert set(frame["source_system"]) == {"eurostat"}
    pd.testing.assert_frame_equal(_sorted_long(frame), _sorted_long(gz_frame))
    hu_2020 = frame[
        (frame["geo"] == "HU")
        & (frame["year"] == 2020)
        & (frame["source_column"] == "rail_passenger_km")
    ].iloc[0]
    assert hu_2020["value"] == 14988


def test_load_ksh_frame_golden_fixture():
    raw = (FIXTURES / "stats" / "ksh_real_example.xlsx").read_bytes()

    frame = stats_load.load_ksh_frame(raw, "ksh_real_example")

    assert list(frame.columns) == stats_load._LONG_COLS
    assert len(frame) == 6
    assert set(frame["geo"]) == {"HU"}
    assert set(frame["source_system"]) == {"ksh"}
    assert set(frame["year"].astype(int)) == {2020, 2021}
    assert "Total length of railway lines operated" in set(frame["source_column"])
    assert "Length of electrified railway lines" in set(frame["source_column"])
    assert set(frame["unit"]) == {"kilometres", "persons"}


def test_load_uic_frame_golden_fixture():
    raw = (FIXTURES / "stats" / "uic_real_synopsis.pdf").read_bytes()

    frame = stats_load.load_uic_frame(raw, "uic_real_synopsis")

    assert list(frame.columns) == stats_load._LONG_COLS
    assert not frame.empty
    assert {"HU", "AT"}.issubset(set(frame["geo"]))
    assert set(frame["source_system"]) == {"uic"}
    assert set(frame["year"].astype(int)) == {2024}
    assert {
        "Length of lines worked at end of year - Total",
        "Passenger.kilometres",
        "Tonne.kilometres",
    }.issubset(set(frame["source_column"]))
    hu_network = frame[
        (frame["geo"] == "HU")
        & (frame["source_column"] == "Length of lines worked at end of year - Total")
    ].iloc[0]
    assert hu_network["value"] == 6876.0
