"""barcode values must always be written as text, preserving leading zeros
-- never coerced to an Excel number (which would silently drop the leading
zero and/or the whole value if openpyxl/Excel then treats it as a float).
A synthetic fixture with a deliberately leading-zero barcode proves this;
we don't just trust that the real dev fixture happens to contain one."""
from __future__ import annotations

import csv

from conftest import (
    load_sheet1_rows,
    read_zip_part,
    run_cli,
    write_minimal_productgroups,
    xx,
)
from rpa_builder.mapping import FORCE_TEXT_TARGET_FIELDS, RPA_COL

BARCODE_COL = RPA_COL["barcode"]
SHEET1_PATH = "xl/worksheets/sheet1.xml"


def test_barcode_is_declared_a_force_text_target_field():
    # Guards the business rule itself, not just the ETL output -- if someone
    # ever removes 'barcode' from FORCE_TEXT_TARGET_FIELDS, this must fail
    # loudly rather than let numeric_cell() silently start writing floats.
    assert "barcode" in FORCE_TEXT_TARGET_FIELDS


def test_leading_zero_barcode_survives_round_trip(tmp_path):
    header = ["id", "productgroep", "naam", "verkoopprijs", "kostprijs", "actief", "barcode"]
    src = tmp_path / "product_export.csv"
    leading_zero_barcode = "00841234567"
    with open(src, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerow(["1", "GroepA", "Barcode product", "10.00", "5.00", "true", leading_zero_barcode])

    productgroups = write_minimal_productgroups(tmp_path / "productgroups.xlsx", ["GroepA"])
    out = tmp_path / "out"
    out.mkdir()
    result = run_cli(out, product_export=src, productgroups=productgroups)
    assert result.returncode == 0, result.stdout + result.stderr

    compleet = next(p for p in out.iterdir() if p.suffix == ".xlsx" and "compleet" in p.name)

    # 1) via openpyxl: the value must come back as the exact original string
    rows = load_sheet1_rows(compleet)
    written_value = rows[1][BARCODE_COL]
    assert isinstance(written_value, str), f"barcode came back as {type(written_value)}, not str -- leading zero lost"
    assert written_value == leading_zero_barcode

    # 2) via raw XML: the cell must be an inline string (t="inlineStr"), never
    # a bare numeric <v> cell (which is how a leading zero would silently vanish)
    sheet1_xml = read_zip_part(compleet, SHEET1_PATH)
    rows_xml = xx._parse_rows(sheet1_xml)
    _full, body = rows_xml[2]  # row 2 = first (and only) data row
    cell_by_col = {c: frag for c, _s, frag in xx._iter_cells(body)}
    barcode_letter = xx.col_letter(BARCODE_COL + 1)
    barcode_frag = cell_by_col[barcode_letter]
    assert 't="inlineStr"' in barcode_frag, barcode_frag
    assert f"<t>{leading_zero_barcode}</t>" in barcode_frag or f'<t xml:space="preserve">{leading_zero_barcode}</t>' in barcode_frag


def test_barcode_column_never_uses_numeric_cell_even_though_it_looks_numeric():
    """Direct check of the numeric/force-text letter sets computed in
    workbook.py: barcode's column letter must be excluded from NUMERIC
    treatment regardless of what NUMERIC_TARGET_FIELDS contains."""
    from rpa_builder import workbook

    barcode_letter = xx.col_letter(BARCODE_COL + 1)
    assert barcode_letter in workbook.FORCE_TEXT_LETTERS
    # _build_row_xml's own guard: `col in NUMERIC_LETTERS and col not in FORCE_TEXT_LETTERS`
    would_be_treated_numeric = barcode_letter in workbook.NUMERIC_LETTERS and barcode_letter not in workbook.FORCE_TEXT_LETTERS
    assert would_be_treated_numeric is False
