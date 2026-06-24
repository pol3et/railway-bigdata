"""Silver rules for the non-rail curated datasets (economy / population /
quality of life / modal split). Verifies dataset-aware extraction with the real
coded dimensions, including the key case where two features share a unit but
differ by another dimension (gov debt vs deficit, GVA vs compensation)."""
import pandas as pd
import pytest

from railway_lakehouse.silver.stats import merge as stats_merge
from railway_lakehouse.silver.config import CANONICAL_FEATURES

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _isolate_crosswalk_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(stats_merge, "CROSSWALK_PATH", str(tmp_path / "crosswalk_cache.json"))


def _features(long):
    cw = stats_merge.build_crosswalk(sorted(long["source_column"].unique()), use_llm=False)
    out = long.copy()
    out["feature"] = out["source_column"].map(cw)
    return out


def _val(long, feature, geo, year):
    f = _features(long)
    row = f[(f["feature"] == feature) & (f["geo"] == geo) & (f["year"] == year)].iloc[0]
    return row["value"]


def test_gdp_level_and_growth_from_one_dataset():
    raw = pd.DataFrame({
        "freq,unit,na_item,geo\\TIME_PERIOD": [
            "A,CP_MEUR,B1GQ,HU", "A,CLV_PCH_PRE,B1GQ,HU",
            "A,CP_MEUR,P3,HU",            # consumption, not GDP -> ignored
        ],
        "2021": ["150000", "7.1", "90000"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "nama_10_gdp")
    assert _val(long, "gdp_current_meur", "HU", 2021) == 150000
    assert _val(long, "gdp_growth_pct", "HU", 2021) == 7.1


def test_gov_debt_and_deficit_share_unit_differ_by_na_item():
    # the case the old unit-only format could not express
    raw = pd.DataFrame({
        "freq,unit,sector,na_item,geo\\TIME_PERIOD": [
            "A,PC_GDP,S13,GD,HU", "A,PC_GDP,S13,B9,HU",
            "A,MIO_EUR,S13,GD,HU",        # wrong unit -> ignored
            "A,PC_GDP,S1311,GD,HU",       # wrong sector -> ignored
        ],
        "2021": ["76.5", "-7.1", "120000", "70.0"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "gov_10dd_edpt1")
    assert _val(long, "gov_debt_pct_gdp", "HU", 2021) == 76.5
    assert _val(long, "gov_deficit_pct_gdp", "HU", 2021) == -7.1


def test_population_total_keeps_total_age_both_sexes():
    raw = pd.DataFrame({
        "freq,unit,age,sex,geo\\TIME_PERIOD": [
            "A,NR,TOTAL,T,HU", "A,NR,TOTAL,F,HU", "A,NR,Y25,T,HU"],
        "2021": ["9700000", "5000000", "120000"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "demo_pjan")
    assert _val(long, "population_total", "HU", 2021) == 9700000


def test_demo_gind_maps_indicators_without_unit_dim():
    raw = pd.DataFrame({
        "freq,indic_de,geo\\TIME_PERIOD": [
            "A,GROWRT,HU", "A,GBIRTHRT,HU", "A,GDEATHRT,HU", "A,JAN,HU"],
        "2021": ["-2.5", "9.1", "13.5", "9700000"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "demo_gind")
    assert _val(long, "pop_growth_rate", "HU", 2021) == -2.5
    assert _val(long, "birth_rate", "HU", 2021) == 9.1
    assert _val(long, "death_rate", "HU", 2021) == 13.5


def test_life_satisfaction_keeps_total_education_all_adults():
    raw = pd.DataFrame({
        "freq,statinfo,unit,isced11,life_sat,sex,age,geo\\TIME_PERIOD": [
            "A,AVG,RTG,TOTAL,LIFE,T,Y_GE16,HU",
            "A,AVG,RTG,ED0-2,LIFE,T,Y_GE16,HU",     # sub-education -> ignored
            "A,AVG,RTG,TOTAL,LIFE,F,Y_GE16,HU",     # female only -> ignored
        ],
        "2018": ["5.6", "5.1", "5.7"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "ilc_pw01")
    assert _val(long, "life_satisfaction", "HU", 2018) == 5.6


def test_modal_split_rail_share():
    fr = stats_merge.read_eurostat_tsv(pd.DataFrame({
        "freq,unit,tra_mode,geo\\TIME_PERIOD": ["A,PC,RAIL,HU", "A,PC,ROAD,HU"],
        "2021": ["19.2", "70.1"]}), "tran_hv_frmod")
    assert _val(fr, "freight_modal_split_rail_pct", "HU", 2021) == 19.2


def test_worldbank_indicator_code_maps_to_feature():
    recs = [{"countryiso3code": "HUN", "date": "2021", "value": 181000.0,
             "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP (current US$)"}}]
    long = stats_merge.read_worldbank_json(recs, "NY.GDP.MKTP.CD")
    assert long["source_column"].iloc[0] == "gdp_current_usd"


def test_worldbank_feature_map_only_emits_canonical_keys():
    assert set(stats_merge._WB_INDICATOR_FEATURE.values()) <= set(CANONICAL_FEATURES)


def test_unknown_worldbank_indicator_stays_unmapped_even_with_transport_label():
    recs = [{"countryiso3code": "HUN", "date": "2021", "value": 1.0,
             "indicator": {"id": "IS.AIR.PSGR", "value": "Air transport, passengers carried"}}]
    long = stats_merge.read_worldbank_json(recs, "IS.AIR.PSGR")
    assert long["source_column"].iloc[0] == "worldbank_unmapped:IS.AIR.PSGR"
    cw = stats_merge.build_crosswalk(["worldbank_unmapped:IS.AIR.PSGR"], use_llm=False)
    assert cw["worldbank_unmapped:IS.AIR.PSGR"] == "unmapped"


def test_rail_traffic_aggregates_keep_total_breakdowns():
    trainmv = stats_merge.read_eurostat_tsv(pd.DataFrame({
        "freq,unit,train,geo\\TIME_PERIOD": ["A,THS_TRKM,TOTAL,HU", "A,THS_TRKM,TRN_GD,HU"],
        "2021": ["95000", "40000"]}), "rail_tf_trainmv")
    assert _val(trainmv, "rail_train_km", "HU", 2021) == 95000

    haul = stats_merge.read_eurostat_tsv(pd.DataFrame({
        "freq,train,vehicle,mot_nrg,unit,geo\\TIME_PERIOD": [
            "A,TOTAL,TOTAL,TOTAL,MIO_GTKM,HU", "A,TRN_GD,LOC,DIE,MIO_GTKM,HU"],
        "2021": ["12000", "3000"]}), "rail_tf_haulmov")
    assert _val(haul, "rail_gross_tonne_km", "HU", 2021) == 12000


def test_regional_rail_network_from_tran_r_net():
    raw = pd.DataFrame({
        "freq,tra_infr,unit,geo\\TIME_PERIOD": [
            "A,RL,KM,AT11", "A,RL_ELC,KM,AT11", "A,RD_OTH,KM,AT11",  # region
            "A,RL,KM_TKM2,AT11",                                     # wrong unit
        ],
        "2021": ["500", "300", "9999", "0.1"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "tran_r_net")
    assert _val(long, "rail_network_length_km", "AT11", 2021) == 500
    assert _val(long, "rail_electrified_km", "AT11", 2021) == 300


def test_geo_level_classification_in_gold():
    from railway_lakehouse.gold.build import build_gold
    stats = pd.DataFrame({
        "geo": ["AT", "AT11", "EU27_2020", "EU", "1A", "Z4"],
        "year": [2021] * 6,
        "feature": ["rail_network_length_km"] * 6,
        "value": [5000.0, 500.0, 200000.0, 210000.0, 1.0, 2.0],
        "unit": ["KM"] * 6,
        "source_system": ["eurostat"] * 6,
        "source_dataset": ["x"] * 6,
        "source_column": ["rail_network_length_km"] * 6,
    })
    gold = build_gold(stats, [])
    levels = dict(zip(gold["geo"], gold["geo_level"]))
    assert levels == {
        "AT": "country",
        "AT11": "region",
        "EU27_2020": "aggregate",
        "EU": "aggregate",
        "1A": "aggregate",
        "Z4": "aggregate",
    }
