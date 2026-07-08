"""Regression test for a RALF-review finding: build_rpa_products.main() built
both the 'compleet' and 'actief' sheets by passing the SAME mutable `flags`
list into workbook.build_sheet1_xml() twice. Since every active row is also
present in the 'compleet' set, a numeric-target field that fails float()
parsing (e.g. kostprijs='NOT_A_NUMBER') got appended to `flags` once per
build call -- i.e. TWICE for any row that is active -- inflating the report's
flag count and duplicating rows in the flagged-values.csv companion file.
Fixed by passing a throwaway list to the second (active-only) build call."""
from __future__ import annotations

import csv

from conftest import run_cli, write_minimal_productgroups


def test_active_row_numeric_fallback_flagged_exactly_once(tmp_path):
    header = ["id", "productgroep", "naam", "verkoopprijs", "kostprijs", "actief", "barcode"]
    src = tmp_path / "product_export.csv"
    with open(src, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        # active (actief=true) row with a non-numeric value in a NUMERIC_TARGET_FIELDS
        # column -- lands in BOTH the compleet and actief outputs.
        w.writerow(["1", "GroepA", "Bad Price Product", "10.00", "NOT_A_NUMBER", "true", "1"])

    productgroups = write_minimal_productgroups(tmp_path / "productgroups.xlsx", ["GroepA"])
    out = tmp_path / "out"
    out.mkdir()
    result = run_cli(out, product_export=src, productgroups=productgroups)
    assert result.returncode == 0, result.stdout + result.stderr

    assert "Unresolved/invalid values flagged for manual review (1):" in result.stdout
    assert result.stdout.count("kostprijs='NOT_A_NUMBER'") == 1

    flagged_csv = out / f"RPA Test Kliniek Dev {_datum_from_stdout(result.stdout)} flagged-values.csv"
    assert flagged_csv.exists()
    with open(flagged_csv, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1, rows
    assert rows[0]["field"] == "kostprijs"
    assert rows[0]["raw_value"] == "NOT_A_NUMBER"


def _datum_from_stdout(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("DATUM: "):
            return line.split()[1]
    raise AssertionError("no DATUM line in stdout")
