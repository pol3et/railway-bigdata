import io
import zipfile

import pytest

from railway_lakehouse.silver.schema import ArticleRecord, GKGRecord
from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.news.gkg_parser import (
    gkg_record_id,
    match_gkg_to_article,
    parse_gkg_csv,
    parse_gkg_csv_zip,
)


def _gkg21_row(
    *,
    record_id="gkg-1",
    url="https://example.test/hu",
    date="20260625010101",
    themes="PUBLIC_TRANSPORT;RAIL_INCIDENT;",
    v2themes="PUBLIC_TRANSPORT,101;RAIL_INCIDENT,140;",
    locations="1#Hungary#HU#HU##47.0#19.0#-1;",
    v2locations="1#Budapest, Hungary#HU#HU##47.5#19.0#3054643#42;",
    persons="Janos",
    v2persons="Janos,44;",
    organizations="MAV",
    v2organizations="MAV,52;",
    tone="5.5,1.0,2.0,0,0,100",
):
    fields = [""] * 27
    fields[0] = record_id
    fields[1] = date
    fields[2] = "1"
    fields[3] = "example.test"
    fields[4] = url
    fields[7] = themes
    fields[8] = v2themes
    fields[9] = locations
    fields[10] = v2locations
    fields[11] = persons
    fields[12] = v2persons
    fields[13] = organizations
    fields[14] = v2organizations
    fields[15] = tone
    fields[17] = "wc:100,c1.1:2"
    return "\t".join(fields)


def _gkg10_row(
    *,
    date="20140102",
    urls="https://example.test/at;https://mirror.test/at",
    tone="-3.0,1.0,4.0,0,0",
    themes="PUBLIC_TRANSPORT;STRIKE;",
    locations="1#Austria#AU#AU##48.2#16.3#-1;",
    persons="Erika Mustermann;",
    organizations="OBB;Westbahn;",
):
    fields = [""] * 21
    fields[0] = date
    fields[1] = "1"
    fields[13] = "example.test"
    fields[14] = urls
    fields[15] = tone
    fields[17] = themes
    fields[18] = locations
    fields[19] = persons
    fields[20] = organizations
    return "\t".join(fields)


@pytest.mark.unit
def test_parse_gkg_csv_returns_gkg_records():
    rows = [
        _gkg21_row(record_id="gkg-hu", tone="5.5,1,2,0,0,100"),
        _gkg21_row(
            record_id="gkg-at",
            url="https://example.test/at",
            themes="PUBLIC_TRANSPORT;",
            v2themes="PUBLIC_TRANSPORT,33;",
            locations="1#Austria#AU#AU##48.2#16.3#-1;",
            v2locations="1#Vienna, Austria#AU#AU##48.2#16.3#2761369#77;",
            organizations="OBB;",
            v2organizations="OBB,12;",
            tone="-3.0,1,4,0,0,80",
        ),
        _gkg21_row(
            record_id="gkg-other",
            url="https://example.test/other",
            themes="TAX_FNCACT;",
            v2themes="TAX_FNCACT,9;",
            locations="1#Slovakia#LO#LO##48.7#19.7#-1;",
            v2locations="1#Slovakia#LO#LO##48.7#19.7#-1#12;",
            organizations="Other Org;",
            v2organizations="Other Org,15;",
            tone="0,0,0,0,0,10",
        ),
    ]

    records = parse_gkg_csv("\n".join(rows))

    assert [record.gkg_id for record in records] == ["gkg-hu", "gkg-at", "gkg-other"]
    assert records[0].gkg_date == "20260625010101"
    assert records[0].document_identifier == "https://example.test/hu"
    assert records[0].gkg_tone == 5.5
    assert records[1].gkg_tone == -3.0
    assert records[2].gkg_tone == 0.0
    assert records[0].gkg_themes == "PUBLIC_TRANSPORT;RAIL_INCIDENT"
    assert records[0].gkg_locations.startswith("1#Budapest, Hungary#HU")


@pytest.mark.unit
def test_parse_gkg_csv_handles_utf8_and_special_chars():
    row = _gkg21_row(
        record_id="gkg-utf8",
        persons="Janos;",
        v2persons="Árvíztűrő Tükörfúrógép,44;",
        organizations="MÁV-Hungarian Railways;",
        v2organizations="MÁV-Hungarian Railways,52;ÖBB,61;",
    )

    [record] = parse_gkg_csv(row)

    assert record.gkg_persons == "Árvíztűrő Tükörfúrógép"
    assert record.gkg_organizations == "MÁV-Hungarian Railways;ÖBB"


@pytest.mark.unit
def test_parse_gkg_csv_accepts_gkg_1_daily_rows():
    [record] = parse_gkg_csv(_gkg10_row())

    assert record.gkg_date == "20140102"
    assert record.document_identifier == "https://example.test/at;https://mirror.test/at"
    assert record.gkg_tone == -3.0
    assert record.gkg_themes == "PUBLIC_TRANSPORT;STRIKE"
    assert record.gkg_organizations == "OBB;Westbahn"


@pytest.mark.unit
def test_parse_gkg_csv_skips_malformed_rows(caplog):
    text = "\n".join(
        [
            _gkg21_row(record_id="good"),
            "too\tshort",
            _gkg21_row(record_id="missing-tone", tone=""),
        ]
    )

    records = parse_gkg_csv(text)

    assert [record.gkg_id for record in records] == ["good", "missing-tone"]
    assert records[1].gkg_tone is None
    assert "skipping malformed GKG row" in caplog.text


@pytest.mark.unit
def test_parse_gkg_csv_zip_unzips_and_parses():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("20260625.gkg.csv", _gkg21_row(record_id="zip-gkg"))

    records = parse_gkg_csv_zip(buffer.getvalue(), date_str="20260625")

    assert len(records) == 1
    assert records[0].gkg_id == "zip-gkg"


@pytest.mark.unit
def test_parse_gkg_csv_zip_handles_bad_zip(caplog):
    records = parse_gkg_csv_zip(b"not a zip", date_str="20260625")

    assert records == []
    assert "failed to read GKG zip" in caplog.text


@pytest.mark.unit
def test_gkg_record_id_uses_existing_id_or_stable_hash():
    assert gkg_record_id({"GKGRECORDID": "gkg-123", "DATE": "20260625"}) == "gkg-123"

    first = gkg_record_id({"DATE": "20260625", "DocumentIdentifier": "https://example.test/a"})
    second = gkg_record_id({"DocumentIdentifier": "https://example.test/a", "DATE": "20260625"})

    assert len(first) == 64
    assert first == second


@pytest.mark.unit
def test_match_gkg_to_article_matches_document_identifier_urls():
    record = GKGRecord(
        gkg_id="gkg-url",
        document_identifier="https://example.test/a;http://example.test/b/",
    )

    assert match_gkg_to_article(record, "https://example.test/a")
    assert match_gkg_to_article(record, "http://example.test/b")
    assert not match_gkg_to_article(record, "https://example.test/c")


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tone", "expected"),
    [(5.0, "positive"), (-3.0, "negative"), (0.0, "neutral"), (None, None)],
)
def test_gdelt_passthrough_maps_gkg_tone_to_sentiment(tone, expected):
    feature = news_extract.gdelt_passthrough(
        article_id="g-tone",
        url="https://example.test/tone",
        published_date="2026-06-25",
        gkg_tone=tone,
        gkg_themes="PUBLIC_TRANSPORT",
        gkg_locations="Hungary",
    )

    assert feature.sentiment == expected
    assert feature.sentiment_label == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("locations", "expected"),
    [
        ("Hungary;Budapest", "HU"),
        ("1#Budapest, Hungary#HU#HU##47.5#19.0#3054643#42;", "HU"),
        ("Austria;Vienna", "AT"),
        ("1#Vienna, Austria#AU#AU##48.2#16.3#2761369#77;", "AT"),
        ("Slovakia;Bratislava", None),
    ],
)
def test_gdelt_passthrough_extracts_country_from_locations(locations, expected):
    feature = news_extract.gdelt_passthrough(
        article_id="g-country",
        url="https://example.test/country",
        published_date="2026-06-25",
        gkg_tone=0.0,
        gkg_themes="PUBLIC_TRANSPORT",
        gkg_locations=locations,
    )

    assert feature.country == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("themes", "expected"),
    [
        ("RAIL_INCIDENT;PUBLIC_TRANSPORT", "accident"),
        ("LABOR_STRIKE;PUBLIC_TRANSPORT", "strike"),
        ("TRANSPORT_INFRASTRUCTURE;ECON_INVESTMENT", "investment"),
        ("PUBLIC_TRANSPORT", "service_change"),
        ("999;UNKNOWN_THEME", "other"),
    ],
)
def test_gdelt_passthrough_infers_event_type_from_themes(themes, expected):
    feature = news_extract.gdelt_passthrough(
        article_id="g-theme",
        url="https://example.test/theme",
        published_date="2026-06-25",
        gkg_tone=0.0,
        gkg_themes=themes,
        gkg_locations="Hungary",
    )

    assert feature.event_type == expected


@pytest.mark.unit
def test_gdelt_passthrough_populates_operators_from_gkg():
    feature = news_extract.gdelt_passthrough(
        article_id="g-operator",
        url="https://example.test/operator",
        published_date="2026-06-25",
        gkg_record=GKGRecord(
            gkg_id="gkg-operator",
            gkg_tone=2.5,
            gkg_themes="PUBLIC_TRANSPORT",
            gkg_locations="Hungary",
            gkg_organizations="MÁV-Hungarian Railways;Other Org;ÖBB",
        ),
    )

    assert feature.operators == ["MÁV", "ÖBB"]
    assert feature.gkg_organizations == "MÁV-Hungarian Railways;Other Org;ÖBB"


@pytest.mark.unit
def test_gdelt_passthrough_accepts_gkg_record_and_preserves_legacy_fields():
    record = GKGRecord(
        gkg_id="gkg-record",
        gkg_date="20260625",
        document_identifier="https://example.test/gkg-record",
        gkg_themes="RAIL_INCIDENT",
        gkg_tone=-4.0,
        gkg_locations="Austria",
        gkg_persons="Person A",
        gkg_organizations="ÖBB",
    )

    feature = news_extract.gdelt_passthrough(
        article_id="article-gkg-record",
        url="https://example.test/gkg-record",
        published_date="2026-06-25",
        gkg_record=record,
    )

    assert feature.article_id == "article-gkg-record"
    assert feature.sentiment == "negative"
    assert feature.country == "AT"
    assert feature.event_type == "accident"
    assert feature.operators == ["ÖBB"]
    assert feature.gkg_persons == "Person A"


@pytest.mark.unit
@pytest.mark.integration
def test_article_records_to_news_features_uses_gkg_passthrough(monkeypatch):
    monkeypatch.setattr(
        news_extract,
        "generate_json",
        lambda *args, **kwargs: pytest.fail("GKG-matched GDELT article must not call Ollama"),
    )
    article = ArticleRecord(
        article_id="article-gkg",
        source="gdelt",
        title="Rail service disruption",
        url="https://example.test/gkg",
        published_date="2026-06-25",
        body="Snippet",
    )
    gkg = GKGRecord(
        gkg_id="gkg-match",
        gkg_date="20260625010101",
        document_identifier="https://example.test/gkg",
        gkg_themes="PUBLIC_TRANSPORT;RAIL_INCIDENT",
        gkg_tone=4.0,
        gkg_locations="1#Budapest, Hungary#HU#HU##47.5#19.0#3054643#42;",
        gkg_organizations="MÁV-Hungarian Railways",
    )

    [feature] = news_extract.article_records_to_news_features([article], gkg_records=[gkg])

    assert feature.article_id == "article-gkg"
    assert feature.source == "gdelt"
    assert feature.sentiment == "positive"
    assert feature.country == "HU"
    assert feature.event_type == "accident"
    assert feature.operators == ["MÁV"]
    assert feature.gkg_tone_source == "gdelt_gkg"
