"""Eurostat Silver reader: dataset-aware feature extraction on the REAL coded
TSV format (headers like ``freq,unit,geo\\TIME_PERIOD`` with the measure in the
unit code). Breakdown datasets keep only the relevant rows (TOTAL / KIL) instead
of summing detail+total, which would double count.
"""
import pandas as pd
import pytest

from railway_lakehouse.silver.stats import merge as stats_merge

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _isolate_crosswalk_cache(tmp_path, monkeypatch):
    """build_crosswalk() persists its cache to CROSSWALK_PATH; redirect it to a
    tmp file so these tests never read or write the real silver/crosswalk_cache.json."""
    monkeypatch.setattr(stats_merge, "CROSSWALK_PATH",
                        str(tmp_path / "crosswalk_cache.json"))


def _feature(df, geo, year):
    cw = stats_merge.build_crosswalk(sorted(df["source_column"].unique()), use_llm=False)
    df = df.copy()
    df["feature"] = df["source_column"].map(cw)
    row = df[(df["geo"] == geo) & (df["year"] == year)].iloc[0]
    return row["feature"], row["value"]


# --- simple national datasets (no breakdown) via the generic unit map --------
def test_passenger_km_and_passengers_from_national_total():
    raw = pd.DataFrame({
        "freq,unit,geo\\TIME_PERIOD": ["A,MIO_PKM,HU", "A,THS_PAS,HU"],
        "2021": ["110.5 e", "150000"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "rail_pa_total")
    feats = {stats_merge.build_crosswalk([s], use_llm=False)[s] for s in long["source_column"]}
    assert feats == {"rail_passenger_km", "rail_passengers"}


def test_simple_enp_dataset_uses_generic_unit_map():
    raw = pd.DataFrame({"freq,unit,geo\\TIME_PERIOD": ["A,KM,HU"], "2021": ["7587"]})
    long = stats_merge.read_eurostat_tsv(raw, "enps_rail_if")
    assert _feature(long, "HU", 2021)[0] == "rail_network_length_km"


# --- NEW features from breakdown datasets, filtered to TOTAL/KIL -------------
def test_electrified_km_keeps_only_power_total():
    raw = pd.DataFrame({
        "freq,unit,power,geo\\TIME_PERIOD": ["A,KM,TOTAL,HU", "A,KM,AC25000,HU", "A,KM,DC3000,HU"],
        "2021": ["3000", "2000", "1000"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "rail_if_electri")
    feat, val = _feature(long, "HU", 2021)
    assert feat == "rail_electrified_km"
    assert val == 3000  # only the TOTAL row, not 3000+2000+1000


def test_fatalities_keeps_killed_total_rows():
    raw = pd.DataFrame({
        "freq,unit,accident,victim,pers_cat,geo\\TIME_PERIOD": [
            "A,NR,TOTAL,KIL,TOTAL,HU",   # the one we want
            "A,NR,TOTAL,INJ,TOTAL,HU",   # injured -> excluded
            "A,NR,COLLIS,KIL,TOTAL,HU",  # sub-accident -> excluded
        ],
        "2021": ["7", "30", "3"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "rail_ac_catvict")
    feat, val = _feature(long, "HU", 2021)
    assert feat == "rail_fatalities"
    assert val == 7


def test_investment_sums_infrastructure_and_rolling_stock_capex():
    raw = pd.DataFrame({
        "freq,unit,expend,geo\\TIME_PERIOD": [
            "A,MIO_EUR,INF_INV,HU", "A,MIO_EUR,RSTK_INV,HU",
            "A,MIO_EUR,INF_MNT,HU",  # maintenance -> excluded
        ],
        "2021": ["800", "200", "500"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "rail_ec_expend")
    feat, val = _feature(long, "HU", 2021)
    assert feat == "rail_investment"
    assert val == 1000  # 800 + 200, maintenance excluded


def test_locomotives_keep_loc_total_motorisation():
    raw = pd.DataFrame({
        "freq,vehicle,mot_nrg,unit,geo\\TIME_PERIOD": [
            "A,LOC,TOTAL,NR,HU", "A,LOC,ELC,NR,HU", "A,RCA,TOTAL,NR,HU"],
        "2021": ["400", "250", "120"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "rail_eq_locon")
    feat, val = _feature(long, "HU", 2021)
    assert feat == "rail_locomotives"
    assert val == 400


# --- safety: unregistered breakdown datasets are skipped, not summed --------
def test_unregistered_breakdown_dataset_is_skipped():
    raw = pd.DataFrame({
        "freq,unit,vehicle,geo\\TIME_PERIOD": ["A,NR,LOC,HU", "A,NR,WAG,HU"],
        "2021": ["100", "250"],
    })
    out = stats_merge.read_eurostat_tsv(raw, "enps_rail_eq")
    assert out.empty


# --- guards ------------------------------------------------------------------
def test_sub_annual_only_dataset_returns_empty_not_crash():
    raw = pd.DataFrame({
        "freq,unit,geo\\TIME_PERIOD": ["M,MIO_PKM,HU"],
        "2020-M01": ["10"], "2020-M02": ["12"],
    })
    out = stats_merge.read_eurostat_tsv(raw, "rail_pa_monthly")
    assert list(out.columns) == ["geo", "year", "value", "unit", "source_dataset", "source_column"]
    assert out.empty


def test_legacy_english_label_header_still_supported():
    raw = pd.DataFrame({
        "Rail passengers total": ["A,NR,HU", "A,NR,AT"],
        "2020": ["100 b", "200"],
    })
    long = stats_merge.read_eurostat_tsv(raw, "rail_demo")
    assert _feature(long, "HU", 2020)[0] == "rail_passengers"
