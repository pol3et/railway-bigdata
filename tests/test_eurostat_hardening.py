"""Regression tests for the Eurostat Bronze fetcher hardening.

Covers two documented live-run failures:
  * RemoteDisconnected on the TOC fetch -> session must carry a UA + retries.
  * 404s from enqueuing non-dataset TOC rows -> discovery must skip folder/table.
"""
import pytest
import requests

from railway_lakehouse.bronze.sources import eurostat

pytestmark = pytest.mark.unit


class _Response:
    def __init__(self, content: bytes, status_code: int = 200, content_type: str = "text/plain"):
        self.content = content
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}

    @property
    def text(self):
        return self.content.decode("utf-8")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"HTTP {self.status_code}")


class _RecordingLander:
    def __init__(self):
        self.landed = []

    def land(self, artifact):
        self.landed.append(artifact)
        return f"bronze/{artifact.source}/{artifact.dataset_id}/{artifact.filename}"


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


def test_discover_eu_datasets_spans_themes_and_skips_out_of_scope():
    toc_text = "\n".join([
        'GDP and main components\t"nama_10_gdp"\t"dataset"',
        'Population on 1 January\t"demo_pjan"\t"dataset"',
        'Life satisfaction\t"ilc_pw01"\t"dataset"',
        'Rail passengers\t"rail_pa_total"\t"dataset"',
        'Road safety victims\t"tran_sf_roadus"\t"dataset"',
        'Crime statistics\t"crim_off_cat"\t"dataset"',
        'A folder\t"some_folder"\t"folder"',          # skipped: folder
        'Aggregated table\t"t_nama_agg"\t"table"',     # skipped: t_ + table
        'Fishery production\t"fish_aq"\t"dataset"',     # out of scope theme
    ])
    got = eurostat.discover_eu_datasets(toc_text)
    assert got == [
        "crim_off_cat", "demo_pjan", "ilc_pw01",
        "nama_10_gdp", "rail_pa_total", "tran_sf_roadus",
    ]
    assert "fish_aq" not in got and "some_folder" not in got


def test_discover_eu_datasets_excludes_regional_keeps_country_totals():
    toc_text = "\n".join([
        'GDP\t"nama_10_gdp"\t"dataset"',              # national -> keep
        'GDP by NUTS2 region\t"nama_10r_2gdp"\t"dataset"',  # regional -> drop
        'Population\t"demo_pjan"\t"dataset"',          # national -> keep
        'Population by region\t"demo_r_pjangrp3"\t"dataset"',  # regional -> drop
        'Rail passengers\t"rail_pa_total"\t"dataset"', # national -> keep
        'Regional rail goods\t"tran_r_rago"\t"dataset"',    # regional -> drop
        'Metro GDP\t"met_10r_3gdp"\t"dataset"',        # metro -> drop
        'Urban-rural\t"urt_pjanaggr3"\t"dataset"',     # typology -> drop
    ])
    got = eurostat.discover_eu_datasets(toc_text)
    assert got == ["demo_pjan", "nama_10_gdp", "rail_pa_total"]
    for regional in ("nama_10r_2gdp", "demo_r_pjangrp3", "tran_r_rago",
                     "met_10r_3gdp", "urt_pjanaggr3"):
        assert regional not in got


def test_discover_eu_datasets_keeps_annual_skips_sub_annual():
    toc_text = "\n".join([
        'GDP annual\t"nama_10_gdp"\t"dataset"',          # keep
        'GDP quarterly\t"namq_10_gdp"\t"dataset"',        # drop (namq_ family)
        'BoP annual\t"bop_c6_a"\t"dataset"',              # keep
        'BoP quarterly\t"bop_c6_q"\t"dataset"',           # drop (_q)
        'BoP monthly\t"bop_c6_m"\t"dataset"',             # drop (_m)
        'Industrial production monthly\t"sts_inpr_m"\t"dataset"',  # drop (_m)
        'Interest rates daily\t"irt_st_d"\t"dataset"',    # drop (_d)
        'Population\t"demo_pjan"\t"dataset"',             # keep
    ])
    got = eurostat.discover_eu_datasets(toc_text)
    assert got == ["bop_c6_a", "demo_pjan", "nama_10_gdp"]
    for sub in ("namq_10_gdp", "bop_c6_q", "bop_c6_m", "sts_inpr_m", "irt_st_d"):
        assert sub not in got


def test_discover_transport_datasets_keeps_rail_tran_drops_excluded():
    toc_text = "\n".join([
        'Rail passengers\t"rail_pa_total"\t"dataset"',     # keep (rail)
        'Modal split\t"tran_hv_frmod"\t"dataset"',         # keep (tran_)
        'Regional rail goods\t"tran_r_rago"\t"dataset"',   # keep (regional kept)
        'Rail safety\t"tran_sf_railac"\t"dataset"',        # keep (rail safety)
        'Air passengers\t"avia_paoc"\t"dataset"',          # drop (aviation)
        'Aviation safety\t"tran_sf_aviaac"\t"dataset"',    # drop (tran_sf_avia)
        'Maritime safety\t"tran_sf_marac"\t"dataset"',     # drop (tran_sf_mar)
        'Road safety\t"tran_sf_roadus"\t"dataset"',        # drop (tran_sf_road)
        'Maritime goods\t"mar_go_qm"\t"dataset"',          # drop (maritime)
        'Road goods\t"road_go_ta_tott"\t"dataset"',        # drop (road)
    ])
    got = eurostat.discover_transport_datasets(toc_text)
    assert got == [
        "rail_pa_total", "tran_hv_frmod", "tran_r_rago", "tran_sf_railac",
    ]
    for dropped in ("avia_paoc", "tran_sf_aviaac", "tran_sf_marac",
                    "tran_sf_roadus", "mar_go_qm", "road_go_ta_tott"):
        assert dropped not in got


def test_discovery_rejects_path_unsafe_dataset_ids():
    toc_text = "\n".join([
        'Rail passengers\t"rail_pa_total"\t"dataset"',
        'Bad rail dataset\t"../rail_escape"\t"dataset"',
        'Bad transport dataset\t"tran_bad/name"\t"dataset"',
    ])

    assert eurostat.discover_transport_datasets(toc_text) == ["rail_pa_total"]
    assert eurostat.datasets_for_collection(toc_text)[0] == "rail_pa_total"


def test_ingest_uses_curated_allowlist_plus_transport_toc():
    tsv = b"freq,unit,geo\\TIME_PERIOD\t2021\nA,MIO_PKM,HU\t1\n"

    class Session:
        def get(self, url, timeout):
            if "catalogue/toc" in url:
                return _Response(
                    b'Modal split\t"tran_hv_frmod"\t"dataset"\n'
                    b'Unrelated demo\t"xyz_demo"\t"dataset"\n'
                )
            return _Response(tsv, content_type="text/tab-separated-values")

    lander = _RecordingLander()

    eurostat.ingest(lander, session=Session())

    landed_ids = {artifact.dataset_id for artifact in lander.landed}
    assert "_catalogue_toc" in landed_ids
    assert "nama_10_gdp" in landed_ids
    assert "tran_hv_frmod" in landed_ids
    assert "xyz_demo" not in landed_ids


def test_ingest_skips_oversized_dataset_response(monkeypatch):
    monkeypatch.setattr(eurostat, "MAX_DATASET_BYTES", 5)

    class Session:
        def get(self, url, timeout):
            if "catalogue/toc" in url:
                return _Response(b'Modal split\t"tran_hv_frmod"\t"dataset"\n')
            return _Response(b"too-large", content_type="text/tab-separated-values")

    lander = _RecordingLander()

    eurostat.ingest(lander, session=Session())

    landed_ids = {artifact.dataset_id for artifact in lander.landed}
    assert landed_ids == {"_catalogue_toc"}
