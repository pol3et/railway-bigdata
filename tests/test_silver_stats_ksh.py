from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from railway_lakehouse.silver.stats import load as stats_load
from railway_lakehouse.silver.stats import merge as stats_merge

pytestmark = pytest.mark.unit


def _xlsx_bytes(path: Path) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "STADAT"

    # Title / note rows imitate real STADAT noise before the data table.
    ws["A1"] = "KSH STADAT railway table"
    ws["A2"] = "Downloaded from the English KSH endpoint"

    # Actual header row: the reader must find years here.
    ws["A4"] = "Indicator"
    ws["B4"] = "Unit"
    ws["C4"] = 2020
    ws["D4"] = 2021

    ws["A5"] = "Rail lines (total route-km)"
    ws["B5"] = "km"
    ws["C5"] = 7891.0
    ws["D5"] = 7869.0

    ws["A6"] = "Rail passengers"
    ws["B6"] = "thousand persons"
    ws["C6"] = 120.0
    ws["D6"] = 150.0

    ws["A7"] = "Road network"
    ws["B7"] = "km"
    ws["C7"] = 31000.0
    ws["D7"] = 32000.0

    wb.save(path)
    return path.read_bytes()


def test_load_ksh_frame_reads_xlsx_to_long_contract(tmp_path):
    raw = _xlsx_bytes(tmp_path / "sza0030.xlsx")

    frame = stats_load.load_ksh_frame(raw, "ksh_rail_network")

    assert list(frame.columns) == [
        "geo",
        "year",
        "value",
        "unit",
        "source_dataset",
        "source_column",
        "source_system",
    ]
    assert not frame.empty
    assert set(frame["geo"]) == {"HU"}
    assert set(frame["source_system"]) == {"ksh"}
    assert set(frame["unit"]) == {"ksh_native"}
    assert set(frame["source_dataset"]) == {"ksh_rail_network"}

    row = frame[
        (frame["source_column"] == "Rail lines (total route-km)")
        & (frame["year"] == 2021)
    ].iloc[0]
    assert row["value"] == 7869.0


def test_load_ksh_frame_returns_empty_for_non_xlsx_bytes():
    frame = stats_load.load_ksh_frame(b"<html>not an excel file</html>", "broken")
    assert list(frame.columns) == [
        "geo",
        "year",
        "value",
        "unit",
        "source_dataset",
        "source_column",
        "source_system",
    ]
    assert frame.empty


def test_frames_from_bronze_picks_up_latest_ksh_partition(tmp_path):
    older = tmp_path / "stats" / "ksh" / "ksh_rail_network" / "ingest_date=2026-06-22"
    newer = tmp_path / "stats" / "ksh" / "ksh_rail_network" / "ingest_date=2026-06-23"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)

    older.joinpath("sza0030.xlsx").write_bytes(_xlsx_bytes(tmp_path / "older.xlsx"))
    newer.joinpath("sza0030.xlsx").write_bytes(_xlsx_bytes(tmp_path / "newer.xlsx"))

    frames = stats_load.frames_from_bronze(tmp_path)

    assert len(frames) == 1
    frame = frames[0]
    assert set(frame["source_system"]) == {"ksh"}
    assert set(frame["source_dataset"]) == {"ksh_rail_network"}


def test_build_silver_stats_maps_known_ksh_label_and_drops_unmapped(tmp_path, monkeypatch):
    monkeypatch.setattr(stats_merge, "CROSSWALK_PATH", str(tmp_path / "crosswalk_cache.json"))

    bronze_dir = tmp_path / "stats" / "ksh" / "ksh_rail_network" / "ingest_date=2026-06-23"
    bronze_dir.mkdir(parents=True)
    bronze_dir.joinpath("sza0030.xlsx").write_bytes(_xlsx_bytes(tmp_path / "sza0030.xlsx"))

    unified = stats_load.build_silver_stats(tmp_path, use_llm=False)

    assert not unified.empty
    assert "rail_network_length_km" in set(unified["feature"])

    row = unified[
        (unified["feature"] == "rail_network_length_km")
        & (unified["geo"] == "HU")
        & (unified["year"] == 2021)
    ].iloc[0]
    assert row["value"] == 7869.0

    cache = pd.read_json(tmp_path / "crosswalk_cache.json", typ="series").to_dict()
    assert cache["Rail lines (total route-km)"] == "rail_network_length_km"

    cache = pd.read_json(tmp_path / "crosswalk_cache.json", typ="series").to_dict()
    assert cache["Rail lines (total route-km)"] == "rail_network_length_km"