"""Regression tests for the Eurostat Bronze fetcher hardening.

Covers two documented live-run failures:
  * RemoteDisconnected on the TOC fetch -> session must carry a UA + retries.
  * 404s from enqueuing non-dataset TOC rows -> discovery must skip folder/table.
"""
import requests

from railway_lakehouse.bronze.sources import eurostat


def test_build_session_sets_user_agent_and_is_idempotent():
    s = eurostat.build_session()
    assert "User-Agent" in s.headers
    assert "railway-bigdata" in s.headers["User-Agent"]
    # retry adapter mounted for https
    adapter = s.get_adapter("https://ec.europa.eu")
    assert adapter.max_retries.total and adapter.max_retries.total >= 3
    # idempotent: re-hardening the same session keeps a single mount marker
    again = eurostat.build_session(s)
    assert again is s
    assert getattr(s, "_railway_retry_mounted", False) is True


def test_build_session_respects_caller_user_agent():
    s = requests.Session()
    s.headers["User-Agent"] = "caller/9.9"
    out = eurostat.build_session(s)
    assert out.headers["User-Agent"] == "caller/9.9"


def test_discover_skips_folder_and_table_type_rows():
    # real-TOC shape: title \t code \t type \t ...
    toc_text = "\n".join(
        [
            'Railway passenger transport\t"rail_pa_total"\t"dataset"\t"2024"',
            'Rail freight\t"rail_go_total"\t"dataset"\t"2024"',
            'Rail network by NUTS 2 region\t"tgs00113"\t"table"\t"2024"',
            'Railway transport (folder)\t"rail"\t"folder"\t""',
        ]
    )
    assert eurostat.discover_rail_datasets(toc_text) == [
        "rail_go_total",
        "rail_pa_total",
    ]


def test_discover_two_column_sample_still_works_without_type_column():
    # backward compatibility with the existing 2-column characterization inputs
    toc_text = "\n".join(
        [
            "Railway passenger transport\trail_passengers",
            "Road trailer registrations\ttran_trailer_demo",
            "Aggregate railway table\tt_rail_table",
        ]
    )
    assert eurostat.discover_rail_datasets(toc_text) == ["rail_passengers"]
