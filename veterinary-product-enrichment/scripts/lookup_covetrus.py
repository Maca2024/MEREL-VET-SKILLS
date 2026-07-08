"""Local (non-agentic) fallback lookup against the bundled Covetrus
productenlijst (source-hierarchy tier 5 -- see references/source-hierarchy.md).

This is NOT scraped live; it is a bundled reference asset that Merel refreshes
periodically. The column mapping below is inferred from only 3 sample rows
(see references/covetrus-mapping.md) and MUST be verified against the full
asset once it is supplied -- run this script with --verify-mapping for a
quick sanity check when a fresh copy lands in assets/.

Usage (JSON on stdout, always -- never raises on a missing asset so a research
run can continue without this tier):
    python lookup_covetrus.py --barcode 5701170461398
    python lookup_covetrus.py --artikelnummer 4009001
    python lookup_covetrus.py --name "Clavusan 500mg/125mg tablet"
    python lookup_covetrus.py --verify-mapping
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ASSET_PATH = Path(__file__).resolve().parent.parent / "assets" / "covetrus-productenlijst.xlsx"
SHEET_NAME = "PRIJS"

# Column-POSITION mapping (0-indexed), inferred from 3 sample rows -- see
# references/covetrus-mapping.md for the confirmed/pending status of each.
COLUMNS = {
    "omschrijving": 0,
    "leverancier": 1,
    "prijs": 4,
    "covetrus_artikelnummer": 7,
    "registratie_achtig": 8,   # e.g. "RVG06193"
    "barcode": 10,             # 13-digit EAN
    "kanalisatie_kort": 12,    # e.g. "UA"
}


def _load_rows():
    import openpyxl  # local import: keep module importable even if openpyxl
                       # ever becomes optional for a pure "asset absent" check
    wb = openpyxl.load_workbook(ASSET_PATH, data_only=True, read_only=True)
    ws = wb[SHEET_NAME]
    return ws.iter_rows(min_row=2, values_only=True)


def lookup(barcode: str = None, artikelnummer: str = None, name: str = None, limit: int = 5) -> dict:
    if not ASSET_PATH.exists():
        return {
            "available": False,
            "reason": f"Covetrus asset not found at {ASSET_PATH}. "
                      "Skip this source tier and note its absence in "
                      "'toelichting controle'.",
            "matches": [],
        }

    try:
        from rapidfuzz import fuzz
    except ImportError:
        fuzz = None

    matches = []
    for row in _load_rows():
        row_barcode = str(row[COLUMNS["barcode"]]).strip() if row[COLUMNS["barcode"]] else ""
        row_artnr = str(row[COLUMNS["covetrus_artikelnummer"]]).strip() if row[COLUMNS["covetrus_artikelnummer"]] else ""
        row_naam = str(row[COLUMNS["omschrijving"]]).strip() if row[COLUMNS["omschrijving"]] else ""

        score = None
        if barcode and row_barcode and barcode.strip() == row_barcode:
            score = 100
        elif artikelnummer and row_artnr and artikelnummer.strip() == row_artnr:
            score = 100
        elif name and row_naam:
            if fuzz is not None:
                s = fuzz.token_sort_ratio(name.lower(), row_naam.lower())
                score = s if s >= 80 else None
            elif name.strip().lower() in row_naam.lower():
                score = 80

        if score is not None:
            matches.append({
                "score": score,
                "omschrijving": row_naam,
                "leverancier": row[COLUMNS["leverancier"]],
                "prijs": row[COLUMNS["prijs"]],
                "covetrus_artikelnummer": row_artnr,
                "registratie_achtig": row[COLUMNS["registratie_achtig"]],
                "barcode": row_barcode,
                "kanalisatie_kort": row[COLUMNS["kanalisatie_kort"]],
            })

    matches.sort(key=lambda m: -m["score"])
    return {"available": True, "matches": matches[:limit]}


def verify_mapping(sample_rows: int = 5) -> dict:
    """Print a handful of raw rows with the assumed columns highlighted so a
    human (or Claude) can eyeball whether COLUMNS still lines up once the
    real asset is supplied. Does not raise if the asset is absent."""
    if not ASSET_PATH.exists():
        return {"available": False, "reason": f"{ASSET_PATH} not found"}
    out = []
    for i, row in enumerate(_load_rows()):
        if i >= sample_rows:
            break
        out.append({name: row[idx] if idx < len(row) else None for name, idx in COLUMNS.items()})
    return {"available": True, "sample": out}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--barcode")
    p.add_argument("--artikelnummer")
    p.add_argument("--name")
    p.add_argument("--verify-mapping", action="store_true")
    args = p.parse_args()

    if args.verify_mapping:
        print(json.dumps(verify_mapping(), ensure_ascii=False, indent=2))
        return
    result = lookup(barcode=args.barcode, artikelnummer=args.artikelnummer, name=args.name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
