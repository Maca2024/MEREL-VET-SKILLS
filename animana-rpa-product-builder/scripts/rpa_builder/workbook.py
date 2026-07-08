"""Orchestrates the ETL: maps parsed source rows onto the RPA template's
column layout and drives the xlsx_xml surgery to produce the two output
files. This module owns the business mapping; xlsx_xml.py stays generic."""
from __future__ import annotations

from dataclasses import dataclass

from . import xlsx_xml as xx
from .mapping import (
    ACCOUNT_BOUND_DROPDOWN_COLUMNS,
    ACCOUNT_DROPDOWN_CAPACITY,
    DIRECT_FIELD_MAP,
    FIXED_DROPDOWN_COLUMNS,
    FORCE_TEXT_TARGET_FIELDS,
    NUMERIC_TARGET_FIELDS,
    RPA_COL,
)
from .normalize import normalize_kanalisatie, validate_actie, validate_leverancier
from .readers import ProductRow

# Precompute target-field -> column-letter and the letter-keyed type sets once.
_FIELD_TO_LETTER = {f: xx.col_letter(RPA_COL[f] + 1) for f in RPA_COL}
_LETTER_TO_FIELD = {v: k for k, v in _FIELD_TO_LETTER.items()}
NUMERIC_LETTERS = {_FIELD_TO_LETTER[f] for f in NUMERIC_TARGET_FIELDS}
FORCE_TEXT_LETTERS = {_FIELD_TO_LETTER[f] for f in FORCE_TEXT_TARGET_FIELDS}
ACTIE_LETTER = _FIELD_TO_LETTER["actie"]
KANALISATIE_LETTER = _FIELD_TO_LETTER["kanalisatie"]
LEVERANCIER_LETTER = _FIELD_TO_LETTER["leverancier"]


@dataclass
class InvalidValueFlag:
    source_row_number: int
    product_naam: str
    field: str
    raw_value: str
    reason: str


@dataclass
class MappedRow:
    source_row_number: int
    col_values: dict  # col_letter -> str value ('' means blank cell)
    actief_raw: str


def map_product_rows(rows: list[ProductRow], rebuilt_suppliers: list) -> tuple:
    """Returns (mapped_rows: list[MappedRow], flags: list[InvalidValueFlag])."""
    flags: list[InvalidValueFlag] = []
    mapped: list[MappedRow] = []
    supplier_set = rebuilt_suppliers  # already deduped list; membership check below

    for row in rows:
        values = row.values
        naam = values.get("naam", "")
        col_values: dict[str, str] = {}

        for source_field, target_field in DIRECT_FIELD_MAP.items():
            raw = values.get(source_field, "")
            letter = _FIELD_TO_LETTER[target_field]

            if letter == KANALISATIE_LETTER:
                normalized, confident = normalize_kanalisatie(raw)
                if raw.strip() and not confident:
                    flags.append(InvalidValueFlag(
                        row.source_row_number, naam, "kanalisatie", raw,
                        "not confidently mappable to udd/uda/ura/vrij -- passed through unchanged",
                    ))
                col_values[letter] = normalized
                continue

            if letter == ACTIE_LETTER:
                if raw.strip() and not validate_actie(raw):
                    flags.append(InvalidValueFlag(
                        row.source_row_number, naam, "actie", raw,
                        "does not match fixed actie dropdown values (euthanasia/castration)",
                    ))
                col_values[letter] = raw
                continue

            if letter == LEVERANCIER_LETTER:
                if raw.strip() and not validate_leverancier(raw, supplier_set):
                    flags.append(InvalidValueFlag(
                        row.source_row_number, naam, "leverancier", raw,
                        "not found in this run's rebuilt leveranciers dropdown list",
                    ))
                col_values[letter] = raw
                continue

            col_values[letter] = raw

        mapped.append(MappedRow(
            source_row_number=row.source_row_number,
            col_values=col_values,
            actief_raw=values.get("actief", ""),
        ))

    return mapped, flags


def is_active(actief_raw: str) -> bool:
    v = (actief_raw or "").strip()
    return v == "" or v == "true"


def _build_row_xml(template: xx.TemplateXml, row_number: int, col_values: dict,
                    numeric_fallback_flags: list, source_row_number: int, naam: str) -> str:
    cells = []
    for col, style in template.sheet1_style_vector:
        val = col_values.get(col, "")
        if val is None or val == "":
            cells.append(xx.empty_cell(col, row_number, style))
            continue
        if col in NUMERIC_LETTERS and col not in FORCE_TEXT_LETTERS:
            try:
                float(val)
                cells.append(xx.numeric_cell(col, row_number, style, val))
                continue
            except ValueError:
                numeric_fallback_flags.append(InvalidValueFlag(
                    source_row_number, naam, _LETTER_TO_FIELD.get(col, col), val,
                    "expected a numeric value, wrote as text instead",
                ))
        cells.append(xx.inline_str_cell(col, row_number, style, val))
    return f'<row r="{row_number}" spans="1:46">' + "".join(cells) + "</row>"


def build_sheet1_xml(template: xx.TemplateXml, mapped_rows: list, flags: list) -> str:
    row_strings = [template.sheet1_row1_full]
    for i, mrow in enumerate(mapped_rows, start=2):
        naam = mrow.col_values.get(_FIELD_TO_LETTER["naam"], "")
        row_strings.append(_build_row_xml(template, i, mrow.col_values, flags,
                                           mrow.source_row_number, naam))
    data_row_count = len(mapped_rows)
    xml_out = xx.replace_sheet_data(template.sheet1_xml, "".join(row_strings))
    xml_out = xx.replace_sheet1_structural_bits(xml_out, data_row_count)
    xml_out = xx.bump_validation_row_cap(xml_out, data_row_count + 1)
    return xml_out


def build_sheet2_xml(template: xx.TemplateXml, account_lists: dict,
                      capacity_warnings: list) -> str:
    """account_lists: column_letter -> list[str] (already deduped) for the 5
    account-bound columns. Fixed columns are copied byte-identical from the
    template; cleared columns get no data rows (header label untouched)."""
    styles = {col: template.account_column_style(col) for col in ACCOUNT_BOUND_DROPDOWN_COLUMNS}

    for col, values in account_lists.items():
        cap = ACCOUNT_DROPDOWN_CAPACITY[col]
        if len(values) > cap:
            capacity_warnings.append(
                f"dropdown column {col} ({ACCOUNT_BOUND_DROPDOWN_COLUMNS[col]}): "
                f"{len(values)} values exceed the template's pre-provisioned "
                f"capacity of {cap} -- values beyond the capacity are written "
                f"to the sheet but will NOT show a dropdown arrow in Excel."
            )

    max_row = 1
    for col in FIXED_DROPDOWN_COLUMNS:
        max_row = max(max_row, template.fixed_column_extents.get(col, 1))
    for col, values in account_lists.items():
        max_row = max(max_row, len(values) + 1)

    row_strings = [template.dropdowns_row1_full]
    for r in range(2, max_row + 1):
        cells = []
        # column order must be ascending for a well-formed sheet
        for col in ["A", "C", "E", "G", "I", "K", "M", "O", "Q", "Y", "AA", "AC"]:
            if col in FIXED_DROPDOWN_COLUMNS:
                frag = template.fixed_column_cell(col, r)
                if frag:
                    cells.append((xx.col_index(col), frag))
            elif col in ACCOUNT_BOUND_DROPDOWN_COLUMNS:
                values = account_lists.get(col, [])
                idx = r - 2
                if idx < len(values):
                    cells.append((xx.col_index(col), xx.inline_str_cell(
                        col, r, styles.get(col), values[idx])))
            # CLEARED_DROPDOWN_COLUMNS (S/U/W/AE/AG/AI/AK): never emitted for r>=2
        cells.sort(key=lambda t: t[0])
        row_strings.append(f'<row r="{r}" spans="1:37">' + "".join(c for _, c in cells) + "</row>")

    xml_out = xx.replace_sheet_data(template.sheet2_xml, "".join(row_strings))
    xml_out = xx.set_dimension(xml_out, f"A1:AK{max_row}")
    xml_out = xx.autosize_dropdowns_cols(xml_out, template, account_lists)
    return xml_out
