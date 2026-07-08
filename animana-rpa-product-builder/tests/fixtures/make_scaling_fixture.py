#!/usr/bin/env python3
"""Reusable generator for a synthetic, large Animana product-export CSV,
used by tests/test_scaling.py to prove the builder still produces correct
row counts / column widths / autofilter once the template's pre-built
capacity (448 data rows) is exceeded.

Standalone usage:
    python make_scaling_fixture.py --rows 550 --out scaling_product_export.csv

Importable usage:
    from make_scaling_fixture import generate
    path = generate(tmp_path / "scaling_product_export.csv", n_rows=550)
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

# Same column order as the real Animana product export (export_product_dev.csv)
# so this fixture exercises the full DIRECT_FIELD_MAP, not just the minimal
# 7-column signature.
HEADER = [
    "id", "productgroep", "naam", "shortcode", "factuurtekst", "registratie",
    "verkoopeenheid", "stockonpackage", "verpakkingseenheid", "verpakkingsfactor",
    "besteleenheid", "bestelfactor", "barcode", "verkoopprijs", "kostprijs",
    "toeslag", "btw", "memo", "waarschuwing", "dosering", "vrije tekst",
    "Blad productinformatie", "opiaat", "humandrug", "euthanasie",
    "registratie minuten", "leverancier", "artikelnummer", "kanalisatie",
    "actie", "toediening", "indicatie", "costpersellunit", "minmargin",
    "maxmargin", "actief", "farmaceutische vorm",
    "werkzame stof(fen) en concentratie",
]
KANALISATIE_VALUES = ["udd", "uda", "ura", "vrij"]


def _row(i: int) -> list[str]:
    """Builds one data row as a dict keyed by HEADER field name, then
    projects it to HEADER order -- avoids miscounting a positional list
    against a 38-field header by hand."""
    actief = "true" if i % 5 != 0 else "false"  # ~80% active, ~20% inactive
    values = {
        "id": str(1000 + i),
        "productgroep": f"Groep {i % 12}",
        "naam": f"Synthetic Product {i:04d}",
        "shortcode": f"SC{i:04d}",
        "factuurtekst": f"Factuurtekst {i}",
        "registratie": "",
        "verkoopeenheid": "stuk",
        "stockonpackage": "false",
        "verpakkingseenheid": "stuk",
        "verpakkingsfactor": "1",
        "besteleenheid": "stuk",
        "bestelfactor": "1",
        "barcode": f"{i:08d}",  # zero-padded -- exercises leading zeros at scale too
        "verkoopprijs": f"{(i % 500) + 1}.50",
        "kostprijs": f"{(i % 300) + 1}.20",
        "toeslag": "",
        "btw": "H",
        "memo": "",
        "waarschuwing": "",
        "dosering": "",
        "vrije tekst": "",
        "Blad productinformatie": "",
        "opiaat": "false",
        "humandrug": "false",
        "euthanasie": "false",
        "registratie minuten": "",
        "leverancier": "",
        "artikelnummer": "",
        "kanalisatie": KANALISATIE_VALUES[i % len(KANALISATIE_VALUES)],
        "actie": "",
        "toediening": "",
        "indicatie": "",
        "costpersellunit": "",
        "minmargin": "",
        "maxmargin": "",
        "actief": actief,
        "farmaceutische vorm": "",
        "werkzame stof(fen) en concentratie": "",
    }
    return [values[h] for h in HEADER]


def generate(out_path: Path, n_rows: int = 550) -> Path:
    """Writes a synthetic product-export CSV with `n_rows` data rows
    (default 550, comfortably above the required >500 and above the
    template's 448-row pre-built capacity) and returns the path."""
    out_path = Path(out_path)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        for i in range(1, n_rows + 1):
            w.writerow(_row(i))
    return out_path


def _main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rows", type=int, default=550)
    p.add_argument("--out", type=Path, default=Path("scaling_product_export.csv"))
    args = p.parse_args()
    path = generate(args.out, args.rows)
    print(f"wrote {args.rows} rows to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
