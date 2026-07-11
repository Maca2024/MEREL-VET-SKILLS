"""An Animana export that has been opened and re-saved in Excel with a
semicolon list separator reaches us mangled: every line gains a run of empty
`;` columns, and any line containing a comma-in-quotes, a quote or a line break
is rewritten as ONE quoted cell holding the whole original comma-record, with
its inner quotes doubled.

Feeding that to a plain csv.reader leaves the quote state open across line
boundaries, so entire blocks of the file are swallowed into a single record and
vanish -- not even counted as malformed. That is exactly what happened on the
first real client run (Wagenrenk, 9 jul 2026): 4519 source rows in, 2225 rows
out, and the workbook was still labelled 'compleet'.

These tests pin down both halves of the fix: the reader must recover the rows,
and the CLI must refuse to label a partial catalogue 'compleet'.
"""
from __future__ import annotations

import csv

from conftest import (
    DEV_FIXTURES_DIR,
    run_cli,
    write_minimal_productgroups,
)

from rpa_builder import readers

HEADER = ["id", "productgroep", "naam", "verkoopprijs", "kostprijs", "actief", "barcode"]
TRAILER = ";" * 10  # the empty columns Excel appends


def _excel_line(line: str) -> str:
    """Reproduce what Excel does to ONE physical line of a comma-CSV when it
    re-saves it with a semicolon list separator."""
    if any(ch in line for ch in ('"', ";")):
        line = '"' + line.replace('"', '""') + '"'
    return line + TRAILER


def _excel_lines(record: str) -> list[str]:
    """Excel wraps line by line, so a record whose field holds a line break
    gets its own wrapper on each half -- which is why the two halves cannot be
    glued back together before they are each unwrapped."""
    return [_excel_line(part) for part in record.split("\n")]


def _write_mangled_export(path, records: list[str]) -> None:
    lines = _excel_lines(",".join(HEADER))
    for record in records:
        lines.extend(_excel_lines(record))
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")


CLEAN = "1,GroepA,Gewoon Product,10.00,5.00,true,111"
QUOTED = '2,GroepA,"Vacutainer 10ml, p.e. 100st",20.00,10.00,true,222'
MULTILINE = '3,GroepA,"Product met\nregelafbreking",30.00,15.00,true,333'
BROKEN = "4,GroepA,Te veel velden,40.00,20.00,true,444,EXTRA"


def test_excel_roundtrip_rows_are_all_recovered(tmp_path):
    src = tmp_path / "export_product.csv"
    _write_mangled_export(src, [CLEAN, QUOTED, MULTILINE])

    result = readers.read_product_export(src)

    assert result.malformed_rows == []
    assert [r.values["id"] for r in result.rows] == ["1", "2", "3"]
    assert result.rows[1].values["naam"] == "Vacutainer 10ml, p.e. 100st"
    assert result.rows[2].values["naam"] == "Product met\nregelafbreking"


def test_excel_trailer_does_not_pollute_the_last_column(tmp_path):
    """The `;;;;;;;;;;` Excel appends lands on the last header name and on the
    last value of every unquoted line -- silently unnaming a real column."""
    src = tmp_path / "export_product.csv"
    _write_mangled_export(src, [CLEAN, QUOTED])

    result = readers.read_product_export(src)

    assert "barcode" in result.rows[0].values  # not 'barcode;;;;;;;;;;'
    assert result.rows[0].values["barcode"] == "111"
    assert result.rows[1].values["barcode"] == "222"


def test_unparseable_rows_are_reported_not_swallowed(tmp_path):
    src = tmp_path / "export_product.csv"
    _write_mangled_export(src, [CLEAN, BROKEN, QUOTED])

    result = readers.read_product_export(src)

    assert [r.values["id"] for r in result.rows] == ["1", "2"]
    assert [line for line, _reason in result.malformed_rows] == [3]
    assert "expected 7 columns" in result.malformed_rows[0][1]
    assert result.source_row_count == 3  # 2 parsed + 1 malformed, nothing lost


def test_cli_refuses_to_label_a_partial_catalogue_compleet(tmp_path):
    src = tmp_path / "export_product.csv"
    _write_mangled_export(src, [CLEAN, BROKEN, QUOTED])  # 1 of 3 = 33% dropped
    productgroups = write_minimal_productgroups(tmp_path / "productgroups.xlsx", ["GroepA"])
    out = tmp_path / "out"
    out.mkdir()

    result = run_cli(out, product_export=src, productgroups=productgroups)

    assert result.returncode == 3, result.stdout + result.stderr
    assert "could not be parsed" in result.stdout
    assert result.xlsx_files() == []  # nothing labelled 'compleet' was written
    assert any(p.name.endswith("malformed-rows.csv") for p in result.output_files())


def test_allow_partial_overrides_the_gate(tmp_path):
    src = tmp_path / "export_product.csv"
    _write_mangled_export(src, [CLEAN, BROKEN, QUOTED])
    productgroups = write_minimal_productgroups(tmp_path / "productgroups.xlsx", ["GroepA"])
    out = tmp_path / "out"
    out.mkdir()

    result = run_cli(out, product_export=src, productgroups=productgroups, allow_partial=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(result.xlsx_files()) == 2


def test_clean_export_is_parsed_exactly_as_before(tmp_path):
    """The repair must not change how a well-formed export is read: the dev
    fixture has no Excel artefact, so the row count must still match a plain
    csv.reader over the same file."""
    path = DEV_FIXTURES_DIR / "export_product_dev.csv"
    with open(path, encoding="utf-8-sig", newline="") as fh:
        baseline = list(csv.reader(fh))
    ncols = len(baseline[0])
    expected_good = sum(1 for r in baseline[1:] if len(r) == ncols)

    result = readers.read_product_export(path)

    assert len(result.rows) == expected_good
    assert len(result.malformed_rows) == len(baseline) - 1 - expected_good
