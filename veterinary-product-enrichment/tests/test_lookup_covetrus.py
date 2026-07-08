"""Tests for lookup_covetrus.py against a small SYNTHETIC Covetrus-shaped
workbook built here (mimicking the real sheet's column layout: col A
description, B leverancier, E prijs, H covetrus artikelnummer, I
registration-like code, K barcode, M kanalisatie-like code -- 0-indexed
0, 1, 4, 7, 8, 10, 12). The real 17,551-row asset is NOT present in this
scratchpad and must never be used here -- see references/test-plan.md
section 4.
"""
from __future__ import annotations

import openpyxl
import pytest

import lookup_covetrus


# COLUMNS mapping (0-indexed), copied from the module under test so a test
# failure here would also flag if COLUMNS ever silently shifts again.
COLUMNS = lookup_covetrus.COLUMNS


def _write_covetrus_asset(path, rows: list[dict]):
    """rows: list of dicts keyed by the same names as lookup_covetrus.COLUMNS."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = lookup_covetrus.SHEET_NAME
    ncols = max(COLUMNS.values()) + 1
    header = [""] * ncols
    for name, idx in COLUMNS.items():
        header[idx] = name
    ws.append(header)
    for row in rows:
        line = [""] * ncols
        for name, idx in COLUMNS.items():
            line[idx] = row.get(name, "")
        ws.append(line)
    wb.save(path)


SAMPLE_ROWS = [
    {
        "omschrijving": "Clavubactin 500mg/125mg tablet 10st",
        "leverancier": "Eurovet",
        "prijs": 12.50,
        "covetrus_artikelnummer": "4009001",
        "registratie_achtig": "RVG06193",
        "barcode": "5701170461398",
        "kanalisatie_kort": "UA",
    },
    {
        "omschrijving": "Metacam 1.5mg/ml oral suspensie 32ml",
        "leverancier": "Boehringer",
        "prijs": 18.75,
        "covetrus_artikelnummer": "4009002",
        "registratie_achtig": "RVG12345",
        "barcode": "5701170461404",
        "kanalisatie_kort": "UDD",
    },
    {
        "omschrijving": "Rimadyl 50mg tablet 100st",
        "leverancier": "Zoetis",
        "prijs": 45.00,
        "covetrus_artikelnummer": "4009003",
        "registratie_achtig": "RVG54321",
        "barcode": "5701170461411",
        "kanalisatie_kort": "URA",
    },
    {
        # deliberately near-duplicate of row 0 (different pack size) so
        # sort-order/limit tests have >1 genuine fuzzy match to compare.
        "omschrijving": "Clavubactin 500mg/125mg tablet 20st",
        "leverancier": "Eurovet",
        "prijs": 22.00,
        "covetrus_artikelnummer": "4009004",
        "registratie_achtig": "RVG06193",
        "barcode": "5701170461428",
        "kanalisatie_kort": "UA",
    },
]


@pytest.fixture
def synthetic_asset(tmp_path, monkeypatch):
    asset_path = tmp_path / "covetrus-productenlijst.xlsx"
    _write_covetrus_asset(asset_path, SAMPLE_ROWS)
    monkeypatch.setattr(lookup_covetrus, "ASSET_PATH", asset_path)
    return asset_path


def test_exact_barcode_match(synthetic_asset):
    result = lookup_covetrus.lookup(barcode="5701170461398")
    assert result["available"] is True
    assert len(result["matches"]) == 1
    match = result["matches"][0]
    assert match["score"] == 100
    assert match["omschrijving"] == "Clavubactin 500mg/125mg tablet 10st"
    assert match["covetrus_artikelnummer"] == "4009001"
    assert match["registratie_achtig"] == "RVG06193"
    assert match["kanalisatie_kort"] == "UA"


def test_exact_artikelnummer_match(synthetic_asset):
    result = lookup_covetrus.lookup(artikelnummer="4009002")
    assert result["available"] is True
    assert len(result["matches"]) == 1
    assert result["matches"][0]["omschrijving"] == "Metacam 1.5mg/ml oral suspensie 32ml"


def test_barcode_no_match_returns_empty_matches(synthetic_asset):
    result = lookup_covetrus.lookup(barcode="0000000000000")
    assert result["available"] is True
    assert result["matches"] == []


def test_fuzzy_name_match_above_threshold(synthetic_asset):
    # Same words with the slash removed -- not identical, but a close
    # enough token-sort match (verified >= 80 with rapidfuzz) to surface.
    result = lookup_covetrus.lookup(name="Clavubactin 500mg 125mg tablet 10st")
    assert result["available"] is True
    assert len(result["matches"]) >= 1
    top = result["matches"][0]
    assert top["omschrijving"] == "Clavubactin 500mg/125mg tablet 10st"
    assert top["score"] >= 80


def test_fuzzy_name_match_below_threshold_excluded(synthetic_asset):
    # A name unrelated to anything in the asset must not fuzzy-match.
    result = lookup_covetrus.lookup(name="Compleet Andersoortig Fictief Product Naam")
    assert result["available"] is True
    assert result["matches"] == []


def test_matches_sorted_by_score_descending(synthetic_asset):
    # This query fuzzy-matches both Clavubactin rows (identical 10st pack
    # at 100, near-duplicate 20st pack lower) -- results must come back
    # highest-score first.
    result = lookup_covetrus.lookup(name="Clavubactin 500mg/125mg tablet 10st")
    scores = [m["score"] for m in result["matches"]]
    assert len(scores) >= 2
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == 100


def test_limit_caps_number_of_matches(synthetic_asset):
    result = lookup_covetrus.lookup(name="Clavubactin 500mg/125mg tablet 10st", limit=1)
    assert len(result["matches"]) == 1
    assert result["matches"][0]["score"] == 100


def test_asset_absent_degrades_gracefully(tmp_path, monkeypatch):
    missing_path = tmp_path / "does-not-exist.xlsx"
    monkeypatch.setattr(lookup_covetrus, "ASSET_PATH", missing_path)

    result = lookup_covetrus.lookup(barcode="5701170461398")

    assert result == {
        "available": False,
        "reason": (
            f"Covetrus asset not found at {missing_path}. "
            "Skip this source tier and note its absence in "
            "'toelichting controle'."
        ),
        "matches": [],
    }


def test_asset_absent_does_not_raise_for_any_lookup_kind(tmp_path, monkeypatch):
    missing_path = tmp_path / "does-not-exist.xlsx"
    monkeypatch.setattr(lookup_covetrus, "ASSET_PATH", missing_path)

    # None of these should raise, regardless of which lookup kwarg is used.
    assert lookup_covetrus.lookup(barcode="x")["available"] is False
    assert lookup_covetrus.lookup(artikelnummer="x")["available"] is False
    assert lookup_covetrus.lookup(name="x")["available"] is False


def test_verify_mapping_degrades_gracefully_when_asset_absent(tmp_path, monkeypatch):
    missing_path = tmp_path / "does-not-exist.xlsx"
    monkeypatch.setattr(lookup_covetrus, "ASSET_PATH", missing_path)

    result = lookup_covetrus.verify_mapping()

    assert result == {"available": False, "reason": f"{missing_path} not found"}


def test_verify_mapping_reports_sample_rows_with_current_column_mapping(synthetic_asset):
    result = lookup_covetrus.verify_mapping(sample_rows=2)
    assert result["available"] is True
    assert len(result["sample"]) == 2
    first = result["sample"][0]
    assert first["omschrijving"] == "Clavubactin 500mg/125mg tablet 10st"
    assert first["barcode"] == "5701170461398"
    assert first["kanalisatie_kort"] == "UA"
