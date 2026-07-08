"""
Source-file readers. Each reader accepts either .csv or .xlsx and detects the
format from content (header signature), not the file extension, per spec.
"""
from __future__ import annotations

import csv
import io
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


def _read_tabular_rows(path: Path):
    """Yield (header: list[str], rows: list[list[str]]) for a .csv or .xlsx file,
    regardless of the file's actual extension -- we sniff by trying CSV first
    (a valid xlsx is a zip and will fail to decode as text/CSV), then xlsx."""
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return _read_xlsx_rows(path)
    if suffix == ".csv":
        return _read_csv_rows(path)
    # Unknown extension: try xlsx (zip signature) first, else csv.
    with open(path, "rb") as fh:
        magic = fh.read(2)
    if magic == b"PK":
        return _read_xlsx_rows(path)
    return _read_csv_rows(path)


def _read_csv_rows(path: Path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


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
    header, raw_rows = _read_tabular_rows(path)
    if not PRODUCT_EXPORT_SIGNATURE.issubset(set(header)):
        raise ValueError(
            f"{path.name} does not look like an Animana product export "
            f"(missing required columns: {PRODUCT_EXPORT_SIGNATURE - set(header)})"
        )
    ncols = len(header)
    rows: list[ProductRow] = []
    malformed: list[tuple[int, str]] = []
    for i, raw in enumerate(raw_rows, start=1):
        if len(raw) != ncols:
            malformed.append((i + 1, f"expected {ncols} columns, got {len(raw)}"))
            continue
        rows.append(ProductRow(values=dict(zip(header, raw)), source_row_number=i + 1))
    return ParseResult(rows=rows, malformed_rows=malformed)


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


def classify_copy_paste_file(path: Path) -> str:
    """Distinguish a 'toeslagen' (1 price column) vs 'margeregels' (2 price
    columns) copy-paste file by counting tab-separated fields per data line
    (content-based, not filename-based) -- majority vote across non-empty
    lines. Returns 'toeslagen' or 'margeregels'."""
    field_counts = []
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            field_counts.append(len(line.split("\t")))
    if not field_counts:
        return "toeslagen"
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
