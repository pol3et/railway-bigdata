from io import BytesIO

import pandas as pd
import pytest

from railway_lakehouse.silver.stats import load as stats_load
from railway_lakehouse.silver.stats import merge as stats_merge

pytestmark = pytest.mark.unit


def _escape_pdf_text(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _minimal_table_pdf(rows: list[list[str]]) -> bytes:
    """Build a tiny line-drawn PDF table that pdfplumber can extract."""
    x0, y0 = 40, 760
    col_widths = [75, 95, 210, 120, 120]
    row_height = 30

    xs = [x0]
    for width in col_widths:
        xs.append(xs[-1] + width)
    ys = [y0 - (row_height * idx) for idx in range(len(rows) + 1)]

    ops = ["0.5 w"]
    for x in xs:
        ops.append(f"{x} {ys[0]} m {x} {ys[-1]} l S")
    for y in ys:
        ops.append(f"{xs[0]} {y} m {xs[-1]} {y} l S")
    ops.append("/F1 8 Tf")
    for row_idx, row in enumerate(rows):
        y = y0 - (row_idx + 0.65) * row_height
        for col_idx, text in enumerate(row):
            if not text:
                continue
            x = xs[col_idx] + 3
            ops.append(f"BT 1 0 0 1 {x:.1f} {y:.1f} Tm ({_escape_pdf_text(text)}) Tj ET")

    content = "\n".join(ops).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 700 800] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
    ]

    out = BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj_num, obj in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(f"{obj_num} 0 obj\n".encode("ascii"))
        out.write(obj)
        out.write(b"\nendobj\n")

    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return out.getvalue()


def _uic_like_pdf() -> bytes:
    return _minimal_table_pdf([
        [
            "Country Code",
            "Railway company",
            "Length of lines worked at end of year Total",
            "Passenger.kilometres",
            "Tonne.kilometres",
        ],
        ["HU", "MAV (2024)", "6 876", "11 298", ""],
        ["AT", "OBB (2024)", "5 018", "12 756", "19 635,0"],
    ])


def test_load_uic_frame_extracts_pdfplumber_table_rows():
    frame = stats_load.load_uic_frame(_uic_like_pdf(), "uic_synopsis")

    assert list(frame.columns) == [
        "geo",
        "year",
        "value",
        "unit",
        "source_dataset",
        "source_column",
        "source_system",
    ]
    assert set(frame["source_system"]) == {"uic"}
    assert set(frame["source_dataset"]) == {"uic_synopsis"}

    hu_network = frame[
        (frame["geo"] == "HU")
        & (frame["year"] == 2024)
        & (frame["source_column"] == "Length of lines worked at end of year - Total")
    ].iloc[0]
    assert hu_network["value"] == 6876.0
    assert hu_network["unit"] == "kilometres"

    at_freight = frame[
        (frame["geo"] == "AT")
        & (frame["year"] == 2024)
        & (frame["source_column"] == "Tonne.kilometres")
    ].iloc[0]
    assert at_freight["value"] == 19635.0
    assert at_freight["unit"] == "millions"


def test_uic_parser_reads_real_synopsis_page_four_table_shape():
    table = [
        [
            "Country\nCode",
            "Railway\ncompany",
            "Average staff\nstrength",
            None,
            "Length of lines worked at end of year",
            None,
            None,
            "Stock at end of year",
            None,
            None,
            None,
            "Train performance",
            None,
            "Revenue rail traffic (3)",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "Country",
            "Surface\narea km2 (1)",
            "Population\n(1)",
            "Population\ndensity",
        ],
        [
            None,
            None,
            None,
            None,
            "Total",
            "of which double\ntrack or more",
            "of which elec-\ntrified lines",
            "Locomotives\nincluding Light\nRail Motor-\ntractors",
            "Railcars and\nMultiple\nUnits",
            "Coaches & trailers (2)",
            "Railway's\nwagons",
            "Train\nkilometres",
            "Gross train tonne.\nkilometres",
            "Passenger",
            None,
            None,
            None,
            "Freight",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "Passengers carried",
            None,
            "Passenger.kilometres",
            None,
            "Tonnes carried",
            None,
            "Tonne.kilometres",
            None,
            None,
            None,
            None,
            None,
        ],
        [
            "AT",
            "GKB (2020)",
            "0,4",
            "",
            "91",
            "0",
            "",
            "11",
            "13",
            "15",
            "",
            "2",
            "211",
            "3,9",
            "",
            "91",
            "",
            "0,1",
            "",
            "3,7",
            "",
            "Austria",
            "83,9",
            "9,1",
            "108,9",
        ],
        [
            None,
            "OBB (2024)",
            "45,6",
            "4,5",
            "5 018",
            "2 261",
            "3 768",
            "1 071",
            "605",
            "3 558",
            "16 366",
            "na",
            "na",
            "298,6",
            "7,8",
            "12 756",
            "1,4",
            "57,0",
            "1,9",
            "19 635,0",
            "7,8",
            None,
            None,
            None,
            None,
        ],
        [
            "HU",
            "FOX (2021)",
            "0,1",
            "",
            "",
            "",
            "",
            "7",
            "0",
            "",
            "0",
            "0,6",
            "532,5",
            "",
            "",
            "",
            "",
            "1,2",
            "",
            "532,4",
            "",
            "Hungary",
            "93,0",
            "9,6",
            "103,1",
        ],
        [
            None,
            "MAV (2024)",
            "35,3",
            "-2,5",
            "6 876",
            "1 239",
            "2 864",
            "815",
            "521",
            "2 425",
            "",
            "92,4",
            "22 310,0",
            "243,8",
            "59,5",
            "11 298",
            "40,3",
            "",
            "",
            "",
            "",
            None,
            None,
            None,
            None,
        ],
    ]

    frame = stats_load._uic_rows_from_tables([table], "uic_synopsis")

    assert not frame.empty
    assert set(frame["geo"]) == {"AT", "HU"}
    assert (
        frame[
            (frame["geo"] == "AT")
            & (frame["year"] == 2024)
            & (frame["source_column"] == "Passenger.kilometres")
        ].iloc[0]["value"]
        == 12756.0
    )
    assert (
        frame[
            (frame["geo"] == "HU")
            & (frame["year"] == 2024)
            & (frame["source_column"] == "Length of lines worked at end of year - Total")
        ].iloc[0]["value"]
        == 6876.0
    )


def test_uic_number_parser_handles_decimal_comma_and_grouped_values():
    assert stats_load._parse_uic_number("1,5") == 1.5
    assert stats_load._parse_uic_number("12,34") == 12.34
    assert stats_load._parse_uic_number("1 234,5") == 1234.5
    assert stats_load._parse_uic_number("12 756") == 12756.0


def test_uic_table_parser_does_not_treat_preposition_at_as_austria():
    table = [
        [
            "Country Code",
            "Railway company",
            "Length of lines worked at end of year Total",
            "Passenger.kilometres",
            "Tonne.kilometres",
        ],
        ["at", "Narrative (2024)", "10", "20", "30"],
    ]

    frame = stats_load._uic_rows_from_tables([table], "uic_synopsis")

    assert frame.empty


def test_load_uic_frame_returns_empty_for_non_pdf_bytes():
    frame = stats_load.load_uic_frame(b"<html>not pdf</html>", "broken")
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


def test_build_silver_stats_maps_uic_pdf_from_bronze(tmp_path, monkeypatch):
    monkeypatch.setattr(stats_merge, "CROSSWALK_PATH", str(tmp_path / "crosswalk_cache.json"))
    bronze_dir = tmp_path / "stats" / "uic" / "uic_synopsis" / "ingest_date=2026-06-24"
    bronze_dir.mkdir(parents=True)
    bronze_dir.joinpath("uic_synopsis.pdf").write_bytes(_uic_like_pdf())

    unified = stats_load.build_silver_stats(tmp_path, use_llm=False)

    assert {"rail_network_length_km", "rail_passenger_km", "rail_freight_tonne_km"}.issubset(
        set(unified["feature"])
    )
    assert set(unified["source_system"]) == {"uic"}
    row = unified[
        (unified["geo"] == "HU")
        & (unified["year"] == 2024)
        & (unified["feature"] == "rail_network_length_km")
    ].iloc[0]
    assert row["value"] == 6876.0
    assert row["source_column"] == "Length of lines worked at end of year - Total"

    cache = pd.read_json(tmp_path / "crosswalk_cache.json", typ="series").to_dict()
    assert cache["Length of lines worked at end of year - Total"] == "rail_network_length_km"
