"""
Low-level, template-structure-aware XML surgery on the bundled RPA template.

WHY NOT OPENPYXL FOR WRITING: the template's dropdown lists are wired via
Excel's *extended* (x14/extLst) data-validation format. openpyxl's writer does
not round-trip that extension -- loading the workbook with openpyxl and saving
it again silently DROPS every dropdown in the file (openpyxl even warns about
this: "Data Validation extension is not supported and will be removed"). Since
"all validations/formatting preserved, opens without repair prompt" is a hard
acceptance criterion, this module edits the worksheet XML directly inside the
.xlsx zip and never round-trips the document through openpyxl's writer.
Styles.xml, sharedStrings.xml and the extLst validation block are copied
byte-for-byte and never touched (except, only if the product count exceeds the
template's 448 pre-built rows, a targeted substring bump of the row-range caps
inside <xm:sqref> -- see `bump_validation_row_cap`).
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

SHEET1_PATH = "xl/worksheets/sheet1.xml"  # 'RPA Products edit'
SHEET2_PATH = "xl/worksheets/sheet2.xml"  # 'dropdowns'
TEMPLATE_ROW_CAP = 449  # last pre-styled row baked into the template (row 1 = header)

_ROW_RE = re.compile(r'<row r="(\d+)"[^>]*>(.*?)</row>', re.DOTALL)
_CELL_RE = re.compile(r'<c r="([A-Z]+)(\d+)"((?:[^>/]*?))(?:/>|>(.*?)</c>)', re.DOTALL)


def col_letter(n: int) -> str:
    """1-based column index -> Excel column letter (1 -> A, 46 -> AT)."""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def _parse_rows(sheet_xml: str) -> dict:
    """row_number -> (full_row_text_incl_tags, inner_body)"""
    out = {}
    for m in _ROW_RE.finditer(sheet_xml):
        out[int(m.group(1))] = (m.group(0), m.group(2))
    return out


def _iter_cells(row_body: str):
    """Yield (col_letter, style_attr_or_None, cell_xml_fragment) for every <c>
    in a row body, in document order."""
    for m in _CELL_RE.finditer(row_body):
        col, _rownum, attrs, _inner = m.groups()
        style_m = re.search(r'\bs="(\d+)"', attrs)
        style = style_m.group(1) if style_m else None
        yield col, style, m.group(0)


def escape_xml_text(value: str) -> str:
    return escape(value)


def inline_str_cell(col: str, row: int, style: str | None, value: str) -> str:
    s_attr = f' s="{style}"' if style else ""
    preserve = ' xml:space="preserve"' if value != value.strip() else ""
    return f'<c r="{col}{row}"{s_attr} t="inlineStr"><is><t{preserve}>{escape_xml_text(value)}</t></is></c>'


def numeric_cell(col: str, row: int, style: str | None, value: str) -> str:
    s_attr = f' s="{style}"' if style else ""
    return f'<c r="{col}{row}"{s_attr}><v>{value}</v></c>'


def empty_cell(col: str, row: int, style: str | None) -> str:
    s_attr = f' s="{style}"' if style else ""
    return f'<c r="{col}{row}"{s_attr}/>'


_SI_RE = re.compile(r"<si>(.*?)</si>", re.DOTALL)
_T_RE = re.compile(r"<t[^>]*>(.*?)</t>", re.DOTALL)


def _load_shared_strings(z: zipfile.ZipFile) -> list:
    """Read-only text lookup used ONLY to approximate autofit column widths
    for the dropdowns sheet -- never used to write cells (all new/rewritten
    cells use inlineStr, never shared-string indices)."""
    try:
        data = z.read("xl/sharedStrings.xml").decode("utf-8")
    except KeyError:
        return []
    out = []
    for si_body in _SI_RE.findall(data):
        out.append("".join(_T_RE.findall(si_body)))
    return out


def cell_display_text(cell_xml: str, shared_strings: list) -> str:
    """Best-effort plain-text length source for width autosizing."""
    if cell_xml is None:
        return ""
    is_m = re.search(r"<is>(.*?)</is>", cell_xml, re.DOTALL)
    if is_m:
        t = _T_RE.search(is_m.group(1))
        return t.group(1) if t else ""
    if 't="s"' in cell_xml:
        v = re.search(r"<v>(\d+)</v>", cell_xml)
        if v:
            idx = int(v.group(1))
            if 0 <= idx < len(shared_strings):
                return shared_strings[idx]
        return ""
    v = re.search(r"<v>([^<]*)</v>", cell_xml)
    return v.group(1) if v else ""


def set_dimension(sheet_xml: str, ref: str) -> str:
    return re.sub(r'<dimension ref="[^"]*"/>', f'<dimension ref="{ref}"/>', sheet_xml)


def autosize_dropdowns_cols(sheet_xml: str, template: "TemplateXml", account_lists: dict) -> str:
    """Recomputes <cols> widths for the dropdowns sheet: the 19 content
    columns are autosized to their longest populated value (header included);
    spacer columns (the blank divider columns between them) keep the
    template's original narrow width untouched."""
    from .mapping import ACCOUNT_BOUND_DROPDOWN_COLUMNS, FIXED_DROPDOWN_COLUMNS

    content_cols = set(FIXED_DROPDOWN_COLUMNS) | set(ACCOUNT_BOUND_DROPDOWN_COLUMNS) | {
        "S", "U", "W", "AE", "AG", "AI", "AK"
    }
    header_texts = {}
    for c, _s, frag in _iter_cells(template.dropdowns_row1_full):
        header_texts[c] = cell_display_text(frag, template.shared_strings)

    orig_cols_m = re.search(r"<cols>(.*?)</cols>", sheet_xml, re.DOTALL)
    orig_col_widths = {}
    if orig_cols_m:
        for m in re.finditer(r'<col min="(\d+)" max="(\d+)" width="([\d.]+)"', orig_cols_m.group(1)):
            for idx in range(int(m.group(1)), int(m.group(2)) + 1):
                orig_col_widths[idx] = m.group(3)

    col_entries = []
    for idx in range(1, 38):  # A..AK
        letter = col_letter(idx)
        if letter in content_cols:
            values = [header_texts.get(letter, "")]
            if letter in FIXED_DROPDOWN_COLUMNS:
                for r in range(2, template.dropdowns_max_template_row + 1):
                    frag = template.fixed_column_cell(letter, r)
                    if frag:
                        values.append(cell_display_text(frag, template.shared_strings))
            elif letter in ACCOUNT_BOUND_DROPDOWN_COLUMNS:
                values.extend(account_lists.get(letter, []))
            width = autosize_width(values)
            col_entries.append(f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>')
        elif idx in orig_col_widths:
            col_entries.append(
                f'<col min="{idx}" max="{idx}" width="{orig_col_widths[idx]}" customWidth="1"/>'
            )
    new_cols = "<cols>" + "".join(col_entries) + "</cols>"
    return re.sub(r"<cols>.*?</cols>", new_cols, sheet_xml, flags=re.DOTALL)


class TemplateXml:
    """Loads the three text parts of the template we need to edit, keeping
    every other zip member (styles.xml, sharedStrings.xml, theme, etc.)
    completely untouched."""

    def __init__(self, template_path: Path):
        self.template_path = template_path
        with zipfile.ZipFile(template_path) as z:
            self.sheet1_xml = z.read(SHEET1_PATH).decode("utf-8")
            self.sheet2_xml = z.read(SHEET2_PATH).decode("utf-8")
            self._all_names = z.namelist()
            self.shared_strings = _load_shared_strings(z)

        rows1 = _parse_rows(self.sheet1_xml)
        self.sheet1_row1_full = rows1[1][0]  # verbatim, incl. <row> tag
        row2_cells = list(_iter_cells(rows1[2][1]))
        # column order + per-column style id, as baked into the template's
        # first pre-styled data row -- this is the "row template" reused for
        # every generated product row, regardless of row count.
        self.sheet1_style_vector = [(col, style) for col, style, _ in row2_cells]

        rows2 = _parse_rows(self.sheet2_xml)
        self.dropdowns_row1_full = rows2[1][0]  # verbatim, incl. <row> tag
        self.dropdowns_rows = {rn: body for rn, (_full, body) in rows2.items()}
        self.dropdowns_max_template_row = max(self.dropdowns_rows)

        from .mapping import FIXED_DROPDOWN_COLUMNS  # local import, avoids a cycle
        self.fixed_column_extents = {col: 1 for col in FIXED_DROPDOWN_COLUMNS}
        for rn, body in self.dropdowns_rows.items():
            if rn == 1:
                continue
            for col, _style, _frag in _iter_cells(body):
                if col in self.fixed_column_extents:
                    self.fixed_column_extents[col] = max(self.fixed_column_extents[col], rn)

    def account_column_style(self, col: str) -> str | None:
        """Style id used by an account-bound dropdown column's data rows in
        the template (row 2), or None if the template leaves it unstyled."""
        row2_cells = dict((c, s) for c, s, _ in _iter_cells(self.dropdowns_rows[2]))
        return row2_cells.get(col)

    def fixed_column_cell(self, col: str, row: int) -> str | None:
        """Verbatim (byte-identical) XML fragment for a FIXED dropdown
        column's cell at a given row, or None if the template has no value
        there. Copying this string unchanged is what makes the fixed columns
        byte-identical to the template in the output."""
        body = self.dropdowns_rows.get(row)
        if body is None:
            return None
        for c, _style, frag in _iter_cells(body):
            if c == col:
                return frag
        return None

    def build_zip(self, out_path: Path, new_sheet1_xml: str, new_sheet2_xml: str) -> None:
        """Write a full .xlsx by copying every zip member from the template
        verbatim except the two worksheet XML parts, which are replaced."""
        with zipfile.ZipFile(self.template_path) as src, \
                zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in src.infolist():
                data = src.read(item.filename)
                if item.filename == SHEET1_PATH:
                    data = new_sheet1_xml.encode("utf-8")
                elif item.filename == SHEET2_PATH:
                    data = new_sheet2_xml.encode("utf-8")
                dst.writestr(item, data)


_SHEET_DATA_RE = re.compile(r"<sheetData>.*?</sheetData>", re.DOTALL)


def replace_sheet_data(sheet_xml: str, new_rows_xml: str) -> str:
    """Swaps the entire <sheetData>...</sheetData> block for freshly built
    row XML (a concatenation of <row>...</row> strings, no wrapper needed)."""
    return _SHEET_DATA_RE.sub(f"<sheetData>{new_rows_xml}</sheetData>", sheet_xml)


def bump_validation_row_cap(sheet1_xml: str, new_max_row: int) -> str:
    """Only called when product rows exceed the template's pre-built capacity
    (448 data rows). Widens every `<xm:sqref>...449</xm:sqref>` row-range
    upper bound from 449 to new_max_row, touching nothing else in the
    extLst data-validation block."""
    if new_max_row <= TEMPLATE_ROW_CAP:
        return sheet1_xml

    def _bump(m: re.Match) -> str:
        inner = m.group(1)
        # Match a standalone "449" token (a column-letter run immediately
        # before it, no digit before/after) -- e.g. "A2:A449" or "...AM449".
        bumped = re.sub(rf"(?<!\d){TEMPLATE_ROW_CAP}\b", str(new_max_row), inner)
        return f"<xm:sqref>{bumped}</xm:sqref>"

    return re.sub(r"<xm:sqref>(.*?)</xm:sqref>", _bump, sheet1_xml, flags=re.DOTALL)


def replace_sheet1_structural_bits(sheet1_xml: str, final_data_row_count: int) -> str:
    """Rewrites <cols> (uniform width 20), <dimension>, and <autoFilter> ref
    to match the actual output row count. Leaves everything else (including
    the extLst validation block) untouched, except the row-cap bump above."""
    last_row = final_data_row_count + 1  # +1 for header
    new_cols = '<cols><col min="1" max="46" width="20" customWidth="1"/></cols>'
    xml_out = re.sub(r"<cols>.*?</cols>", new_cols, sheet1_xml, flags=re.DOTALL)
    xml_out = re.sub(
        r'<dimension ref="[^"]*"/>', f'<dimension ref="A1:AT{last_row}"/>', xml_out
    )
    xml_out = re.sub(
        r'(<autoFilter ref=")[^"]*(")', rf"\g<1>A1:AT{last_row}\g<2>", xml_out
    )
    return xml_out


def autosize_width(values: list) -> float:
    """Rough Excel-autofit approximation: character count + padding, clamped
    to a sane range. Cosmetic only -- not required to be pixel-exact."""
    max_len = max((len(v) for v in values if v), default=8)
    return float(min(80, max(8, max_len + 2)))
