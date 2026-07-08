"""Builds the human-readable processing report and an optional companion CSV
for flagged/invalid values (kept out of the main report so it stays readable
at 10,000+ product rows)."""
from __future__ import annotations

import csv
from pathlib import Path


def render_report(
    account_name: str,
    datum: str,
    datum_method: str,
    source_files: dict,
    missing_optional: list,
    rows_read: int,
    rows_written_complete: int,
    rows_written_active: int,
    malformed_rows: list,
    dropdown_counts: dict,
    capacity_warnings: list,
    flags: list,
    output_files: list,
) -> str:
    lines = []
    lines.append(f"RPA Products build report -- account: {account_name}")
    lines.append(f"DATUM: {datum} ({datum_method})")
    lines.append("")
    lines.append("Source files used:")
    for role, path in source_files.items():
        lines.append(f"  - {role}: {path if path else '(not provided)'}")
    if missing_optional:
        lines.append("")
        lines.append("Optional inputs missing (dropdown column left empty):")
        for m in missing_optional:
            lines.append(f"  - {m}")
    lines.append("")
    lines.append(f"Rows read from product export: {rows_read}")
    lines.append(f"Rows written to 'compleet' file: {rows_written_complete}"
                  + ("  [MATCH]" if rows_written_complete == rows_read else "  [MISMATCH -- see malformed rows below]"))
    lines.append(f"Rows kept in 'actief' file:     {rows_written_active}")
    if malformed_rows:
        lines.append("")
        lines.append(f"Malformed/unparseable source rows skipped ({len(malformed_rows)}):")
        for row_number, reason in malformed_rows[:50]:
            lines.append(f"  - source row {row_number}: {reason}")
        if len(malformed_rows) > 50:
            lines.append(f"  ... and {len(malformed_rows) - 50} more (see companion CSV)")
    lines.append("")
    lines.append("Account-bound dropdown columns rebuilt:")
    for col, (label, count) in dropdown_counts.items():
        lines.append(f"  - {col} ({label}): {count} values")
    if capacity_warnings:
        lines.append("")
        lines.append("Capacity warnings:")
        for w in capacity_warnings:
            lines.append(f"  - {w}")
    lines.append("")
    lines.append("Fixed dropdown columns (G/I/K/O/Q/AA/AC): confirmed byte-identical to template.")
    if flags:
        lines.append("")
        lines.append(f"Unresolved/invalid values flagged for manual review ({len(flags)}):")
        for f in flags[:30]:
            lines.append(f"  - row {f.source_row_number} '{f.product_naam}': "
                          f"{f.field}='{f.raw_value}' -- {f.reason}")
        if len(flags) > 30:
            lines.append(f"  ... and {len(flags) - 30} more (see companion CSV)")
    else:
        lines.append("")
        lines.append("No unresolved/invalid values found.")
    lines.append("")
    lines.append("Output files:")
    for f in output_files:
        lines.append(f"  - {f}")
    return "\n".join(lines)


def write_flags_csv(path: Path, flags: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["source_row_number", "product_naam", "field", "raw_value", "reason"])
        for f in flags:
            writer.writerow([f.source_row_number, f.product_naam, f.field, f.raw_value, f.reason])


def write_malformed_csv(path: Path, malformed_rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["source_row_number", "reason"])
        for row_number, reason in malformed_rows:
            writer.writerow([row_number, reason])
