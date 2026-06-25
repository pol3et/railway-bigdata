import json
from pathlib import Path

import pandas as pd
import pytest

from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.news.rss import parse_rss_xml
from railway_lakehouse.silver.schema import NewsFeature
from railway_lakehouse.silver.stats import load as stats_load

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "silver"
COVERAGE_JSON = ROOT / "docs" / "PARSER_FIELD_COVERAGE.json"


def test_parser_field_coverage_matrix():
    matrix = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    sources = {entry["source"]: entry for entry in matrix["sources"]}

    assert {"RSS", "GDELT DOC", "World Bank", "Eurostat", "KSH", "UIC"}.issubset(sources)
    for source, entry in sorted(sources.items()):
        assert entry["available_fields"]
        if source != "Statistik Austria":
            assert entry["extracted_fields"]
        assert "notes" in entry
        print(
            source,
            "captured=" + ",".join(entry["extracted_fields"]),
            "dropped=" + ",".join(entry["dropped_or_future"]),
        )


def test_rss_news_feature_schema_complete(monkeypatch):
    xml_text = (FIXTURES / "news" / "rss_real_example.xml").read_text(encoding="utf-8")
    records = parse_rss_xml(xml_text, source="rss_fixture")[:1]

    def fake_generate_json(prompt, *, schema=None, system=None):
        return {
            "is_rail_related": True,
            "country": "HU",
            "event_type": "investment",
            "monetary_amount_eur": None,
            "monetary_raw": None,
            "summary_en": "Railway item.",
            "confidence": 0.9,
        }

    monkeypatch.setattr(news_extract, "generate_json", fake_generate_json)
    features = news_extract.article_records_to_news_features(records)

    assert len(features) == 1
    assert set(features[0].to_row()) == set(NewsFeature.__dataclass_fields__)


def test_gdelt_passthrough_fields_available():
    feature = news_extract.gdelt_passthrough(
        article_id="gkg-1",
        url="https://example.test/gkg",
        published_date="20240622T120000Z",
        gkg_tone=-2.5,
        gkg_themes="WB_133_TRANSPORT",
        gkg_locations="Hungary",
        gkg_persons="Jane Example",
        gkg_organizations="MAV",
        gkg_emotions="c1.3:2",
    )

    assert feature.gkg_tone == -2.5
    assert feature.gkg_themes == "WB_133_TRANSPORT"
    assert feature.gkg_locations == "Hungary"
    assert feature.gkg_persons == "Jane Example"
    assert feature.gkg_organizations == "MAV"
    assert feature.gkg_emotions == "c1.3:2"
    assert feature.gkg_tone_source == "gdelt_gkg"


def test_worldbank_long_format_schema_matches():
    raw = (FIXTURES / "stats" / "worldbank_real_example.json").read_bytes()
    frame = stats_load.load_worldbank_frame(raw, "IS.RRS.PASG.KM")

    assert list(frame.columns) == stats_load._LONG_COLS
    assert set(frame["source_system"]) == {"worldbank"}
    assert frame["geo"].isin(["HU", "AT"]).all()


def test_eurostat_geo_coverage_is_explicit():
    raw = (FIXTURES / "stats" / "eurostat_real_example.tsv").read_bytes()
    frame = stats_load.load_eurostat_frame(raw, "rail_pa_total")

    country_geos = frame[frame["geo"].str.fullmatch(r"[A-Z]{2}")]
    aggregate_geos = frame[~frame["geo"].str.fullmatch(r"[A-Z]{2}")]

    assert {"HU", "AT"}.issubset(set(country_geos["geo"]))
    assert set(aggregate_geos["geo"]) == {"EU27_2020"}


def test_ksh_year_detection_is_robust():
    assert stats_load._coerce_ksh_year("2024") == 2024
    assert stats_load._coerce_ksh_year("2024.0") == 2024
    assert stats_load._coerce_ksh_year("FY2024") is None
    assert stats_load._coerce_ksh_year("1899") is None
    assert stats_load._coerce_ksh_year("2101") is None

    df = pd.DataFrame(
        [
            ["", "Indicator", "Unit", 2020, 2021],
            ["", "Total length of railway lines operated", "km", 7670, 7690],
            ["", "Length of electrified railway lines", "km", 3190, 3210],
        ]
    )
    assert stats_load._ksh_label_column(df, 0, [3, 4]) == 1


def test_uic_table_detection_uses_keyword_hints():
    synopsis_table = [
        [
            "Country Code",
            "Railway company",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Revenue rail traffic",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Country",
        ],
        ["AT", "OBB (2024)", "", "", "5018", "", "3768"],
    ]
    compact_table = [
        [
            "Country Code",
            "Railway company",
            "Length of lines worked at end of year Total",
            "Passenger.kilometres",
        ],
        ["HU", "MAV (2024)", "6876", "11298"],
    ]
    traffic_trends_table = [
        ["Traffic trends", "Passenger traffic", "Freight traffic"],
        ["2024", "100", "200"],
    ]

    synopsis = stats_load._uic_table_specs(synopsis_table)
    compact = stats_load._uic_table_specs(compact_table)

    assert synopsis is not None
    assert 4 in synopsis[0]
    assert compact is not None
    assert compact[0][2][0] == "Length of lines worked at end of year - Total"
    assert stats_load._uic_table_specs(traffic_trends_table) is None
