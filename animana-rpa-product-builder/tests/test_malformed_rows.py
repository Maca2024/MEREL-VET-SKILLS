"""Malformed source rows (wrong column count) must be detected and skipped
-- and, crucially, must NOT silently shift the rows that follow them (i.e.
a well-formed row after a dropped row must still land with its own values,
not with the previous row's leftover position/values)."""
from __future__ import annotations

import csv

from conftest import (
    DEV_FIXTURES_DIR,
    load_sheet1_rows,
    run_cli,
    write_minimal_productgroups,
)


def test_real_fixture_malformed_rows_are_skipped_and_reported(tmp_path):
    """export_product_dev.csv is known (independently re-verified below) to
    contain exactly 2 malformed rows at source rows 74 and 180 (39 fields
    instead of the header's 38)."""
    path = DEV_FIXTURES_DIR / "export_product_dev.csv"
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    header, data = rows[0], rows[1:]
    ncols = len(header)
    malformed_source_rows = [i + 2 for i, r in enumerate(data) if len(r) != ncols]  # +2: 1-based, header excluded

    out = tmp_path / "out"
    out.mkdir()
    result = run_cli(
        out,
        product_export=path,
        productgroups=DEV_FIXTURES_DIR / "productgroups.xlsx",
    )
    assert result.returncode == 0, result.stdout + result.stderr

    assert f"Malformed/unparseable source rows skipped ({len(malformed_source_rows)}):" in result.stdout
    for row_number in malformed_source_rows:
        assert f"source row {row_number}:" in result.stdout

    malformed_csv = out / f"RPA Test Kliniek Dev {_datum_from_stdout(result.stdout)} malformed-rows.csv"
    assert malformed_csv.exists()
    with open(malformed_csv, encoding="utf-8") as fh:
        written = list(csv.DictReader(fh))
    assert [int(r["source_row_number"]) for r in written] == malformed_source_rows
    for r in written:
        assert f"expected {ncols} columns" in r["reason"]


def test_malformed_row_does_not_shift_following_good_rows(tmp_path):
    """Fully synthetic, controlled: row 2 is malformed (one extra field),
    rows 1 and 3 are good. The 'compleet' output must contain exactly the 2
    good rows, in their own right -- row 3's data must not get attributed to
    row 2's position, and vice versa.

    This deliberately tiny file drops 1 of 3 rows (33%), which trips the
    completeness gate (see test_excel_roundtrip_export.py), so it runs with
    --allow-partial: the subject here is row alignment, not the gate."""
    header = ["id", "productgroep", "naam", "verkoopprijs", "kostprijs", "actief", "barcode"]
    src = tmp_path / "product_export.csv"
    with open(src, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerow(["1", "GroepA", "First Good Product", "10.00", "5.00", "true", "1"])
        w.writerow(["2", "GroepA", "Malformed Product", "20.00", "10.00", "true", "2", "EXTRA_FIELD"])
        w.writerow(["3", "GroepA", "Third Good Product", "30.00", "15.00", "true", "3"])

    productgroups = write_minimal_productgroups(tmp_path / "productgroups.xlsx", ["GroepA"])

    out = tmp_path / "out"
    out.mkdir()
    result = run_cli(out, product_export=src, productgroups=productgroups, allow_partial=True)
    assert result.returncode == 0, result.stdout + result.stderr

    assert "Malformed/unparseable source rows skipped (1):" in result.stdout
    assert "source row 3: expected 7 columns, got 8" in result.stdout  # source_row_number is 1-based incl. header offset

    compleet = next(p for p in out.iterdir() if p.suffix == ".xlsx" and "compleet" in p.name)
    rows = load_sheet1_rows(compleet)
    data_rows = rows[1:]

    assert len(data_rows) == 2
    naam_col = 1  # column B = 'naam'
    assert data_rows[0][naam_col] == "First Good Product"
    assert data_rows[1][naam_col] == "Third Good Product"


def _datum_from_stdout(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("DATUM: "):
            return line.split()[1]
    raise AssertionError("no DATUM line in stdout")
