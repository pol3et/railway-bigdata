import dataclasses

import pandas as pd
import pytest

from railway_lakehouse.silver.news.gdelt import parse_gdelt_artlist_json
from railway_lakehouse.silver.news.rss import parse_rss_xml
from railway_lakehouse.silver.schema import ArticleRecord, NewsFeature
from railway_lakehouse.silver.stats.load import (
    _LONG_COLS,
    load_eurostat_frame,
    load_ksh_frame,
    load_uic_frame,
    load_worldbank_frame,
)

pytestmark = pytest.mark.unit


def test_parser_functions_are_importable():
    assert callable(parse_rss_xml)
    assert callable(parse_gdelt_artlist_json)
    assert callable(load_worldbank_frame)
    assert callable(load_eurostat_frame)
    assert callable(load_ksh_frame)
    assert callable(load_uic_frame)


def test_news_parser_return_contracts():
    rss_records = parse_rss_xml(
        """
        <rss><channel><item>
          <title>Rail item</title>
          <link>https://example.test/rss</link>
          <pubDate>2024-06-22</pubDate>
          <description>Body.</description>
        </item></channel></rss>
        """,
        source="rss",
    )
    gdelt_records = parse_gdelt_artlist_json(
        """
        {"articles": [{
          "title": "Rail item",
          "url": "https://example.test/gdelt",
          "seendate": "20240622T120000Z",
          "snippet": "Body."
        }]}
        """
    )

    assert all(isinstance(record, ArticleRecord) for record in rss_records)
    assert all(isinstance(record, ArticleRecord) for record in gdelt_records)


def test_stats_loader_return_contracts():
    worldbank = load_worldbank_frame(
        b'[{"total": 1}, [{"countryiso3code": "HUN", "date": "2021", "value": 1}]]',
        "IS.RRS.PASG.KM",
    )
    eurostat = load_eurostat_frame(
        b"freq,unit,geo\\TIME_PERIOD\t2021\nA,MIO_PKM,HU\t1\n",
        "rail_pa_total",
    )

    for frame in [
        worldbank,
        eurostat,
        load_ksh_frame(b"not-xlsx", "broken"),
        load_uic_frame(b"not-pdf", "broken"),
    ]:
        assert isinstance(frame, pd.DataFrame)
        assert list(frame.columns) == _LONG_COLS


def test_dataclass_schema_field_counts_are_stable():
    assert dataclasses.is_dataclass(ArticleRecord)
    assert dataclasses.is_dataclass(NewsFeature)
    assert len(ArticleRecord.__dataclass_fields__) == 6
    assert len(NewsFeature.__dataclass_fields__) == 43
