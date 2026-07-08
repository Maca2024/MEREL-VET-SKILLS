"""Scaling test: a synthetic product-export with >500 rows (above the
template's 448 pre-built data-row capacity) must still produce correct row
counts, and the structural bits (column widths, dimension, autoFilter, and
-- since we exceed the template's row cap -- the bumped data-validation
<xm:sqref> ranges) must reflect the actual output size."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
from make_scaling_fixture import HEADER, generate  # noqa: E402

from conftest import load_sheet1_rows, read_zip_part, run_cli, write_minimal_productgroups, xx

N_ROWS = 550
SHEET1_PATH = "xl/worksheets/sheet1.xml"


def test_scaling_fixture_generator_produces_requested_row_count(tmp_path):
    path = generate(tmp_path / "scaling_product_export.csv", n_rows=N_ROWS)
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    assert len(lines) == N_ROWS + 1  # header + N_ROWS data rows


def test_builder_handles_550_rows_correctly(tmp_path):
    src = generate(tmp_path / "scaling_product_export.csv", n_rows=N_ROWS)
    productgroups = write_minimal_productgroups(
        tmp_path / "productgroups.xlsx", [f"Groep {i}" for i in range(12)]
    )
    out = tmp_path / "out"
    out.mkdir()

    result = run_cli(out, product_export=src, productgroups=productgroups)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"Rows read from product export: {N_ROWS}" in result.stdout
    assert f"Rows written to 'compleet' file: {N_ROWS}  [MATCH]" in result.stdout
    assert "Malformed/unparseable source rows skipped" not in result.stdout

    compleet = next(p for p in out.iterdir() if p.suffix == ".xlsx" and "compleet" in p.name)
    actief = next(p for p in out.iterdir() if p.suffix == ".xlsx" and "actief" in p.name)

    # --- row counts, independently recomputed from the generator's own logic ---
    rows = load_sheet1_rows(compleet)
    assert len(rows) - 1 == N_ROWS  # minus header

    actief_idx = HEADER.index("actief")
    with open(src, encoding="utf-8") as fh:
        import csv
        data = list(csv.reader(fh))[1:]
    expected_active = sum(1 for r in data if r[actief_idx] == "true")

    active_rows = load_sheet1_rows(actief)
    assert len(active_rows) - 1 == expected_active

    # --- structural bits at scale ------------------------------------------
    last_row = N_ROWS + 1  # +1 header
    sheet1_xml = read_zip_part(compleet, SHEET1_PATH)

    dim_m = re.search(r'<dimension ref="([^"]*)"/>', sheet1_xml)
    assert dim_m.group(1) == f"A1:AT{last_row}"

    filter_m = re.search(r'<autoFilter ref="([^"]*)"', sheet1_xml)
    assert filter_m.group(1) == f"A1:AT{last_row}"

    cols_m = re.search(r"<cols>(.*?)</cols>", sheet1_xml, re.DOTALL)
    assert cols_m.group(1) == '<col min="1" max="46" width="20" customWidth="1"/>'

    # --- row-cap bump: N_ROWS+1 (551) exceeds the template's 449-row cap,
    # so every validation <xm:sqref> that referenced row 449 must now
    # reference last_row instead, and NOTHING should still say 449.
    assert last_row > xx.TEMPLATE_ROW_CAP
    sqrefs = re.findall(r"<xm:sqref>(.*?)</xm:sqref>", sheet1_xml, re.DOTALL)
    assert sqrefs, "expected at least one data-validation sqref block in the template"
    joined = " ".join(sqrefs)
    assert f"{xx.TEMPLATE_ROW_CAP}" not in joined, "validation range still references the old 449 cap"
    assert str(last_row) in joined, "validation range was not bumped to the new row count"

    # --- every actual data row landed on the right physical row (not off-by-one) ---
    body_rows = re.findall(r'<row r="(\d+)"', sheet1_xml)
    assert [int(r) for r in body_rows] == list(range(1, last_row + 1))
