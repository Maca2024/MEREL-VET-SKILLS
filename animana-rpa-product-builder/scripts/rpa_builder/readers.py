"""
Source-file readers. Each reader accepts either .csv or .xlsx and detects the
format from content (header signature), not the file extension, per spec.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

# Header names that must ALL be present to confidently identify the Animana
# product export (subset -- the real export always has these + more).
PRODUCT_EXPORT_SIGNATURE = {
    "id", "productgroep", "naam", "verkoopprijs", "kostprijs", "actief", "barcode",
}
# Contacts/clients export signature.
CONTACTS_SIGNATURE = {"clientId", "bedrijfsnaam", "leverancier"}


@dataclass
class ProductRow:
    values: dict  # raw source column name -> raw string value
    source_row_number: int  # 1-based, header excluded (row 1 in the CSV = source_row_number 1)


@dataclass
class ParseResult:
    rows: list
    malformed_rows: list = field(default_factory=list)  # list of (row_number, reason)
    source_row_count: int = 0  # every source record we identified: parsed + malformed


# A single record may be spread over several physical lines when a field
# contains a line break. Bound how far we look ahead so a corrupt file cannot
# make us glue unrelated products together.
MAX_JOINED_LINES = 5


def _is_xlsx(path: Path) -> bool:
    """Detect the format from content, not the extension, per spec: an xlsx is
    a zip and starts with the PK signature."""
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return True
    if suffix == ".csv":
        return False
    with open(path, "rb") as fh:
        return fh.read(2) == b"PK"


def _read_tabular_rows(path: Path):
    """Yield (header: list[str], rows: list[list[str]]) for a .csv or .xlsx file,
    regardless of the file's actual extension."""
    return _read_xlsx_rows(path) if _is_xlsx(path) else _read_csv_rows(path)


def _read_csv_rows(path: Path):
    header, numbered, _malformed = _read_numbered_csv_rows(path)
    return header, [fields for _line_no, fields in numbered]


def _read_numbered_csv_rows(path: Path):
    """Parse a CSV into (header, [(source_line_number, fields)], [(line, reason)]).

    A plain csv.reader over the whole file is not safe here. Animana exports
    regularly reach us after a round-trip through Excel in a semicolon locale,
    which rewrites a line as one quoted cell holding the entire original
    comma-record, doubles the quotes inside it, and appends empty
    semicolon-columns. Feeding that to csv.reader leaves the quote state open
    across line boundaries, so whole blocks of the file get swallowed into a
    single record and disappear without ever being counted as malformed.
    We therefore parse line by line, join lines only when that yields a
    well-formed record, and unwrap the Excel cell when we find one.
    """
    with open(path, encoding="utf-8-sig", newline="") as fh:
        text = fh.read()
    lines = text.replace("\r\n", "\n").split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return [], [], []

    header, trailer = _parse_header_line(lines[0])
    ncols = len(header)
    numbered: list[tuple[int, list[str]]] = []
    malformed: list[tuple[int, str]] = []

    i = 1
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        row, used = None, 1
        for span in range(1, min(MAX_JOINED_LINES, len(lines) - i) + 1):
            row = _try_span(lines[i:i + span], ncols, trailer)
            if row is not None:
                used = span
                break
        if row is None:
            malformed.append(
                (i + 1, f"expected {ncols} columns, got {_field_count(lines[i])}")
            )
        else:
            if trailer and row and row[-1].endswith(trailer):
                # Excel's empty trailing columns end up glued to the last real
                # value on every unquoted line, exactly as on the header.
                row[-1] = row[-1][:-len(trailer)]
            numbered.append((i + 1, row))
        i += used
    return header, numbered, malformed


def _try_span(chunk: list[str], ncols: int, trailer: str) -> list[str] | None:
    """Try to read `chunk` as exactly one record, both as it stands and -- when
    the file carries the Excel artefact -- with each line individually
    un-Excel'd first. Excel wraps line by line, so a record split over two
    lines gets a wrapper on each half; joining the raw lines then leaves the
    quotes unbalanced and only unwrapping first recovers the record."""
    candidates = ["\n".join(chunk)]
    if trailer:
        candidates.append("\n".join(_unexcel_line(line, trailer) for line in chunk))
    for buf in candidates:
        row = _try_record(buf, ncols)
        if row is not None:
            return row
    return None


def _unexcel_line(raw: str, trailer: str) -> str:
    """Strip the empty columns Excel appended and, if the line is one quoted
    cell holding the whole original record, unwrap it."""
    line = raw[:-len(trailer)] if raw.endswith(trailer) else raw
    if len(line) >= 2 and line.startswith('"') and line.endswith('"'):
        return line[1:-1].replace('""', '"')
    return line


def _try_record(buf: str, ncols: int) -> list[str] | None:
    """Return the fields of `buf` if it is exactly one record of `ncols`
    fields, else None. Handles the Excel round-trip wrapper."""
    try:
        records = list(csv.reader(io.StringIO(buf)))
    except csv.Error:
        return None
    if len(records) != 1:
        return None
    row = records[0]
    if len(row) == ncols:
        return row
    if len(row) == 1:
        # The whole original record sits inside one quoted Excel cell, trailed
        # by the empty columns Excel appended as `;;;;;;;;;;`.
        try:
            inner = list(csv.reader(io.StringIO(row[0].rstrip(";"))))
        except csv.Error:
            return None
        if len(inner) == 1 and len(inner[0]) == ncols:
            return inner[0]
    return None


def _parse_header_line(line: str) -> tuple[list[str], str]:
    """Return (header, trailer). The Excel round-trip glues its empty trailing
    columns onto the last header name ("... concentratie;;;;;;;;;;"), which
    silently unnames a real column for every row in the file. Seeing that run of
    semicolons on the header is what tells us the rest of the file carries it
    too, and exactly how long it is; `trailer` is "" for a clean export, which
    keeps every Excel-specific repair below switched off."""
    row = _split_line(line)
    if len(row) == 1 and row[0]:
        unwrapped = _split_line(row[0].rstrip(";"))
        if len(unwrapped) > 1:
            row = unwrapped
    if not row:
        return row, ""
    match = re.search(r";+$", row[-1])
    if not match or not row[-1][: match.start()]:
        return row, ""
    row[-1] = row[-1][: match.start()]
    return row, match.group(0)


def _split_line(line: str) -> list[str]:
    try:
        return next(csv.reader([line]))
    except (csv.Error, StopIteration):
        return []


def _field_count(line: str) -> int:
    return len(_split_line(line))


def _read_xlsx_rows(path: Path, sheet_name: str | None = None):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    try:
        header = list(next(it))
    except StopIteration:
        return [], []
    header = ["" if h is None else str(h) for h in header]
    rows = []
    for r in it:
        rows.append(["" if v is None else str(v) for v in r])
    wb.close()
    return header, rows


def sniff_role(path: Path) -> str | None:
    """Best-effort content-based classification, used only by the optional
    auto-detect convenience mode. Returns one of: 'product_export',
    'contacts', 'productgroups', 'letters', or None if unrecognized."""
    try:
        header, rows = _read_tabular_rows(path)
    except Exception:
        return None
    header_set = set(header)
    if PRODUCT_EXPORT_SIGNATURE.issubset(header_set):
        return "product_export"
    if CONTACTS_SIGNATURE.issubset(header_set):
        return "contacts"
    if header_set == {"naam", "producten", "margeregel", "prijsgroep"}:
        return "productgroups"
    if header_set == {"naam", "context"}:
        return "letters"
    return None


def read_product_export(path: Path) -> ParseResult:
    if _is_xlsx(path):
        header, raw_rows = _read_xlsx_rows(path)
        numbered = [(i + 2, raw) for i, raw in enumerate(raw_rows)]
        malformed: list[tuple[int, str]] = []
    else:
        header, numbered, malformed = _read_numbered_csv_rows(path)
    if not PRODUCT_EXPORT_SIGNATURE.issubset(set(header)):
        raise ValueError(
            f"{path.name} does not look like an Animana product export "
            f"(missing required columns: {PRODUCT_EXPORT_SIGNATURE - set(header)})"
        )
    ncols = len(header)
    rows: list[ProductRow] = []
    for line_no, raw in numbered:
        if len(raw) != ncols:
            malformed.append((line_no, f"expected {ncols} columns, got {len(raw)}"))
            continue
        rows.append(ProductRow(values=dict(zip(header, raw)), source_row_number=line_no))
    malformed.sort(key=lambda item: item[0])
    return ParseResult(
        rows=rows,
        malformed_rows=malformed,
        source_row_count=len(rows) + len(malformed),
    )


def read_productgroups(path: Path) -> list[str]:
    header, rows = _read_tabular_rows(path)
    if "naam" not in header:
        raise ValueError(f"{path.name}: expected a 'naam' column for productgroups")
    idx = header.index("naam")
    return _dedupe_nonempty(r[idx] for r in rows if idx < len(r))


def read_letters(path: Path) -> list[str]:
    header, rows = _read_tabular_rows(path)
    if "naam" not in header:
        raise ValueError(f"{path.name}: expected a 'naam' column for letters export")
    idx = header.index("naam")
    return _dedupe_nonempty(r[idx] for r in rows if idx < len(r))


def read_contact_suppliers(path: Path) -> list[str]:
    header, rows = _read_tabular_rows(path)
    missing = CONTACTS_SIGNATURE - set(header)
    if missing:
        raise ValueError(f"{path.name}: missing expected contacts columns {missing}")
    lev_idx = header.index("leverancier")
    naam_idx = header.index("bedrijfsnaam")
    out = []
    for r in rows:
        if lev_idx < len(r) and naam_idx < len(r) and r[lev_idx] == "true":
            out.append(r[naam_idx])
    return _dedupe_nonempty(out)


def read_copy_paste_list(path: Path) -> list[str]:
    """Tab-separated, no header. Use only the first tab-field per line
    (name), stripping amounts/euro signs/tabs. Shared by the toeslagen and
    margeregels copy-paste files -- they differ only in trailing price
    column count, which we don't care about here."""
    names = []
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            first_field = line.split("\t", 1)[0].strip()
            if first_field:
                names.append(first_field)
    return _dedupe_nonempty(names)


def classify_copy_paste_file(path: Path) -> str | None:
    """Distinguish a 'toeslagen' (1 price column) vs 'margeregels' (2 price
    columns) copy-paste file by counting tab-separated fields per data line
    (content-based, not filename-based) -- majority vote across non-empty
    lines. Returns 'toeslagen', 'margeregels', or None when the file does not
    look like a genuine tab-separated copy-paste export at all (e.g. a plain
    prose README/LEESMIJ file) -- a stray .txt file in --input-dir must never
    be silently swept into the toeslagen/margeregels dropdown."""
    field_counts = []
    tab_lines = 0
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            field_counts.append(len(line.split("\t")))
            if "\t" in line:
                tab_lines += 1
    if not field_counts:
        return None
    if tab_lines / len(field_counts) < 0.5:
        return None
    avg = sum(field_counts) / len(field_counts)
    # toeslagen lines: name + 1 amount (+ trailing empty) => ~3 fields
    # margeregels lines: name + 2 amounts (+ trailing empty) => ~4 fields
    return "margeregels" if avg >= 3.5 else "toeslagen"


def _dedupe_nonempty(values) -> list[str]:
    seen = set()
    out = []
    for v in values:
        v = (v or "").strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out
