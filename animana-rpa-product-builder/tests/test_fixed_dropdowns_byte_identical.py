"""The 7 fixed dropdown columns on the 'dropdowns' sheet (G/I/K/O/Q/AA/AC --
eenheden/btw/optie/kanalisatie/actie/aanklikken/herinnertype) must be
byte-identical to the template both before and after a run: these are
client-independent, pre-baked Excel dropdown lists that the tool must never
rewrite -- only the 5 account-bound columns (A/C/E/M/Y) get rebuilt."""
from __future__ import annotations

from conftest import TEMPLATE_PATH, read_zip_part, run_full_dev_fixtures, xx

FIXED_COLUMNS = ["G", "I", "K", "O", "Q", "AA", "AC"]
SHEET2_PATH = "xl/worksheets/sheet2.xml"


def _fixed_column_cells(sheet2_xml: str) -> dict:
    """col -> {row_number: cell_xml_fragment_or_None} for every row present
    in the sheet, restricted to the 7 fixed columns."""
    rows = xx._parse_rows(sheet2_xml)
    out = {col: {} for col in FIXED_COLUMNS}
    for row_number, (_full, body) in rows.items():
        cells_by_col = {c: frag for c, _s, frag in xx._iter_cells(body)}
        for col in FIXED_COLUMNS:
            out[col][row_number] = cells_by_col.get(col)
    return out


def test_template_fixed_columns_captured_before_run():
    """Sanity: the template itself actually has non-trivial content in all 7
    fixed columns (extent > 1), otherwise this test would trivially pass."""
    template = xx.TemplateXml(TEMPLATE_PATH)
    for col in FIXED_COLUMNS:
        assert template.fixed_column_extents[col] > 1, (
            f"template column {col} has no data rows -- byte-identical check would be vacuous"
        )


def test_fixed_dropdown_columns_are_byte_identical_after_run(tmp_path):
    template_xml = read_zip_part(TEMPLATE_PATH, SHEET2_PATH)
    template = xx.TemplateXml(TEMPLATE_PATH)
    template_cells = _fixed_column_cells(template_xml)

    result = run_full_dev_fixtures(tmp_path / "out")
    assert result.returncode == 0, result.stdout + result.stderr

    assert "Fixed dropdown columns (G/I/K/O/Q/AA/AC): confirmed byte-identical to template." in result.stdout

    for xlsx_path in result.xlsx_files():
        out_xml = read_zip_part(xlsx_path, SHEET2_PATH)
        out_cells = _fixed_column_cells(out_xml)
        for col in FIXED_COLUMNS:
            extent = template.fixed_column_extents[col]
            for row_number in range(1, extent + 1):
                template_frag = template_cells[col].get(row_number)
                out_frag = out_cells[col].get(row_number)
                assert out_frag == template_frag, (
                    f"{xlsx_path.name}: column {col} row {row_number} differs from template\n"
                    f"  template: {template_frag!r}\n  output:   {out_frag!r}"
                )
