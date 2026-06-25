from pathlib import Path

import pandas as pd
import pytest

from railway_lakehouse.silver.stats import load as stats_load
from railway_lakehouse.silver.stats import merge as stats_merge


LONG_COLS = [
    "geo",
    "year",
    "value",
    "unit",
    "source_dataset",
    "source_column",
    "source_system",
]


def _ods_bytes(path: Path, rows: list[list[object]]) -> bytes:
    pd.DataFrame(rows).to_excel(path, header=False, index=False, engine="odf")
    return path.read_bytes()


def _rolling_stock_ods(path: Path) -> bytes:
    title = "Lokomotivbestände zum Stichtag 31. Dezember 2023 und 2024"
    return _ods_bytes(
        path,
        [
            [title, "", ""],
            ["Lokomotiven", "", ""],
            ["Antriebsart", 2023, 2024],
            ["Diesel", 325, 328],
            ["Insgesamt", 1193, 1275],
            ["Spurweite", 2023, 2024],
            ["Regelspur", 1157, 1240],
            ["Insgesamt", 1193, 1275],
        ],
    )


def _freight_ods(path: Path) -> bytes:
    title = "Schienengüterverkehr nach Verkehrsbereich auf dem österreichischen Schienenverkehrsnetz"
    return _ods_bytes(
        path,
        [
            [title, "", "", ""],
            ["Einheit", "Verkehrsbereich", "", ""],
            ["", "Inlandverkehr", "Transit", "Insgesamt"],
            ["Berichtsjahr 2025", "", "", ""],
            ["Tonnen", 28480747, 29984563, 96161650],
            ["1 000 tkm Inland", 4459575, 8421301, 21535754],
            ["Berichtsjahr 20241", "", "", ""],
            ["Tonnen", 27512786, 29201352, 94417959],
            ["1 000 tkm Inland", 4246908, 7888870, 20995136],
        ],
    )


@pytest.mark.unit
def test_load_stataustria_frame_returns_empty_for_empty_or_non_ods_bytes():
    for raw in (b"", b"not a zip"):
        frame = stats_load.load_stataustria_frame(raw, "test_id")

        assert list(frame.columns) == LONG_COLS
        assert frame.empty


@pytest.mark.unit
def test_load_stataustria_frame_reads_rolling_stock_year_columns(tmp_path):
    title = "Lokomotivbestände zum Stichtag 31. Dezember 2023 und 2024"
    raw = _rolling_stock_ods(tmp_path / "locomotives.ods")

    frame = stats_load.load_stataustria_frame(raw, "stat_at_rail_locomotives")

    assert list(frame.columns) == LONG_COLS
    assert not frame.empty
    assert set(frame["geo"]) == {"AT"}
    assert set(frame["source_system"]) == {"statistik_austria"}
    assert set(frame["source_dataset"]) == {"stat_at_rail_locomotives"}
    assert {2023, 2024}.issubset(set(frame["year"].astype(int)))
    assert set(frame["unit"]) == {"count"}

    label = f"{title} - Lokomotiven - Antriebsart - Insgesamt"
    row = frame[
        (frame["source_column"] == label)
        & (frame["year"] == 2024)
    ].iloc[0]
    assert row["value"] == 1275


@pytest.mark.unit
def test_load_stataustria_frame_reads_freight_report_year_totals_and_units(tmp_path):
    raw = _freight_ods(tmp_path / "freight.ods")

    frame = stats_load.load_stataustria_frame(raw, "stat_at_rail_freight")

    assert not frame.empty
    assert {2024, 2025}.issubset(set(frame["year"].astype(int)))
    assert {"Tonnen", "1 000 tkm Inland"}.issubset(set(frame["unit"]))

    tonnes = frame[
        frame["source_column"].str.contains("Transportaufkommen", regex=False)
        & (frame["year"] == 2024)
    ].iloc[0]
    assert tonnes["value"] == 94417959
    assert tonnes["unit"] == "Tonnen"

    tonne_km = frame[
        frame["source_column"].str.contains("Transportleistung", regex=False)
        & (frame["year"] == 2025)
    ].iloc[0]
    assert tonne_km["value"] == 21535754
    assert tonne_km["unit"] == "1 000 tkm Inland"


@pytest.mark.unit
def test_build_crosswalk_maps_stataustria_german_labels_without_llm(tmp_path, monkeypatch):
    monkeypatch.setattr(stats_merge, "CROSSWALK_PATH", str(tmp_path / "crosswalk_cache.json"))
    raw = _freight_ods(tmp_path / "freight.ods")
    frame = stats_load.load_stataustria_frame(raw, "stat_at_rail_freight")

    labels = sorted(frame["source_column"].unique())
    sources = {label: "statistik_austria" for label in labels}
    crosswalk = stats_merge.build_crosswalk(labels, sources=sources, use_llm=False)

    freight_tonnes = [
        label for label in labels
        if "Transportaufkommen" in label
    ]
    freight_tonne_km = [
        label for label in labels
        if "Transportleistung" in label
    ]
    assert freight_tonnes
    assert freight_tonne_km
    assert all(crosswalk[label] == "rail_freight_tonnes" for label in freight_tonnes)
    assert all(crosswalk[label] == "rail_freight_tonne_km" for label in freight_tonne_km)


@pytest.mark.integration
def test_frames_from_bronze_routes_stataustria_ods(tmp_path):
    bronze_dir = (
        tmp_path
        / "stats"
        / "statistik_austria"
        / "stat_at_rail_locomotives"
        / "ingest_date=2026-06-25"
    )
    bronze_dir.mkdir(parents=True)
    bronze_dir.joinpath("locomotives.ods").write_bytes(_rolling_stock_ods(tmp_path / "locomotives.ods"))

    frames = stats_load.frames_from_bronze(tmp_path)

    assert len(frames) == 1
    frame = frames[0]
    assert set(frame["source_system"]) == {"statistik_austria"}
    assert set(frame["source_dataset"]) == {"stat_at_rail_locomotives"}
    assert set(frame["geo"]) == {"AT"}
