#!/usr/bin/env python3
"""
Animana -> RPA Products workbook builder.

Deterministic ETL, no AI judgment: reads one account's Animana product export
plus a few supporting exports/copy-paste lists, and fills the fixed RPA
Products template with them. See references/field_mapping.md and
references/template_layout.md (in the skill directory) for the full spec.

Usage:
  python build_rpa_products.py \\
      --product-export "export_product.csv" \\
      --productgroups "productgroups.xlsx" \\
      --account-name "Kliniek Voorbeeld" \\
      --output-dir "./output" \\
      [--contacts "export_client.csv"] \\
      [--letters "export.xlsx"] \\
      [--toeslagen "toeslagen.txt"] \\
      [--margeregels "margeregels.txt"] \\
      [--template "assets/RPA_Products_template.xlsx"]

Or point at a folder and let the script classify files by content:
  python build_rpa_products.py --input-dir "./client-exports" \\
      --account-name "Kliniek Voorbeeld" --output-dir "./output"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rpa_builder import readers, report, workbook
from rpa_builder import xlsx_xml as xx
from rpa_builder.dateutil_ import derive_datum
from rpa_builder.mapping import ACCOUNT_BOUND_DROPDOWN_COLUMNS

DEFAULT_TEMPLATE = Path(__file__).parent.parent / "assets" / "RPA_Products_template.xlsx"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--product-export", type=Path)
    p.add_argument("--productgroups", type=Path)
    p.add_argument("--contacts", type=Path)
    p.add_argument("--letters", type=Path)
    p.add_argument("--toeslagen", type=Path)
    p.add_argument("--margeregels", type=Path)
    p.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    p.add_argument("--input-dir", type=Path, help="auto-classify files in this folder for any --* input not given explicitly")
    p.add_argument("--account-name", required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def autodetect_inputs(args: argparse.Namespace) -> None:
    if not args.input_dir:
        return
    for path in sorted(args.input_dir.iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".txt":
            if args.toeslagen and args.margeregels:
                continue
            kind = readers.classify_copy_paste_file(path)
            if kind == "toeslagen" and not args.toeslagen:
                args.toeslagen = path
            elif kind == "margeregels" and not args.margeregels:
                args.margeregels = path
            continue
        if suffix not in (".csv", ".xlsx"):
            continue
        role = readers.sniff_role(path)
        if role == "product_export" and not args.product_export:
            args.product_export = path
        elif role == "contacts" and not args.contacts:
            args.contacts = path
        elif role == "productgroups" and not args.productgroups:
            args.productgroups = path
        elif role == "letters" and not args.letters:
            args.letters = path


def unique_output_path(directory: Path, filename: str) -> Path:
    """Never overwrites a prior run's output -- appends ' (2)', ' (3)', ... on
    collision instead."""
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem, suffix = filename.rsplit(".", 1)
    n = 2
    while True:
        candidate = directory / f"{stem} ({n}).{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def main() -> int:
    args = parse_args()
    autodetect_inputs(args)

    missing_required = []
    if not args.product_export or not args.product_export.exists():
        missing_required.append("product export (--product-export)")
    if not args.productgroups or not args.productgroups.exists():
        missing_required.append("product groups export (--productgroups)")
    if not args.template.exists():
        missing_required.append(f"template asset ({args.template})")
    if missing_required:
        print("ERROR: missing required source(s), stopping before processing:")
        for m in missing_required:
            print(f"  - {m}")
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)

    source_files = {
        "product export": args.product_export,
        "productgroups export": args.productgroups,
        "contacts export (suppliers)": args.contacts,
        "letters export": args.letters,
        "toeslagen copy-paste": args.toeslagen,
        "margeregels copy-paste": args.margeregels,
        "template": args.template,
    }
    missing_optional = []

    parse_result = readers.read_product_export(args.product_export)
    productgroepen = readers.read_productgroups(args.productgroups)

    if args.contacts:
        leveranciers = readers.read_contact_suppliers(args.contacts)
    else:
        leveranciers = []
        missing_optional.append("contacts export -- 'leveranciers' dropdown (column M) left empty")

    if args.letters:
        brieven = readers.read_letters(args.letters)
    else:
        brieven = []
        missing_optional.append("letters export -- 'brieven' dropdown (column Y) left empty")

    if args.toeslagen:
        toeslagen = readers.read_copy_paste_list(args.toeslagen)
    else:
        toeslagen = []
        missing_optional.append("toeslagen copy-paste -- 'toeslagen' dropdown (column C) left empty")

    if args.margeregels:
        margeregels = readers.read_copy_paste_list(args.margeregels)
    else:
        margeregels = []
        missing_optional.append("margeregels copy-paste -- 'margeregels' dropdown (column E) left empty")

    account_lists = {
        "A": productgroepen,
        "C": toeslagen,
        "E": margeregels,
        "M": leveranciers,
        "Y": brieven,
    }

    datum, datum_method = derive_datum(args.product_export)
    mapped_rows, flags = workbook.map_product_rows(parse_result.rows, leveranciers)

    template = xx.TemplateXml(args.template)
    capacity_warnings: list = []

    sheet1_complete = workbook.build_sheet1_xml(template, mapped_rows, flags)
    active_rows = [r for r in mapped_rows if workbook.is_active(r.actief_raw)]
    # active_rows is always a subset of mapped_rows, so any numeric-fallback
    # flag for an active row was already appended to `flags` while building
    # sheet1_complete above. Reusing `flags` here would append the exact same
    # flag a second time for every active row with a numeric fallback --
    # pass a throwaway list so this pass's flags are discarded, not duplicated.
    sheet1_active = workbook.build_sheet1_xml(template, active_rows, [])
    sheet2_xml = workbook.build_sheet2_xml(template, account_lists, capacity_warnings)

    account = args.account_name.strip()
    safe_account = "".join(c for c in account if c not in '\\/:*?"<>|')
    complete_name = f"RPA {safe_account} {datum} V1 compleet.xlsx"
    active_name = f"RPA {safe_account} {datum} V1 actief.xlsx"
    complete_path = unique_output_path(args.output_dir, complete_name)
    active_path = unique_output_path(args.output_dir, active_name)

    template.build_zip(complete_path, sheet1_complete, sheet2_xml)
    template.build_zip(active_path, sheet1_active, sheet2_xml)

    dropdown_counts = {
        col: (ACCOUNT_BOUND_DROPDOWN_COLUMNS[col], len(values))
        for col, values in account_lists.items()
    }

    report_text = report.render_report(
        account_name=account,
        datum=datum,
        datum_method=datum_method,
        source_files={k: (str(v) if v else None) for k, v in source_files.items()},
        missing_optional=missing_optional,
        rows_read=len(parse_result.rows),
        rows_written_complete=len(mapped_rows),
        rows_written_active=len(active_rows),
        malformed_rows=parse_result.malformed_rows,
        dropdown_counts=dropdown_counts,
        capacity_warnings=capacity_warnings,
        flags=flags,
        output_files=[str(complete_path), str(active_path)],
    )
    print(report_text)

    if flags:
        report.write_flags_csv(args.output_dir / f"RPA {safe_account} {datum} flagged-values.csv", flags)
    if parse_result.malformed_rows:
        report.write_malformed_csv(args.output_dir / f"RPA {safe_account} {datum} malformed-rows.csv",
                                    parse_result.malformed_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
