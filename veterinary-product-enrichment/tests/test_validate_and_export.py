"""Tests for validate_and_export.py: missing-required-columns detection and
the happy-path JSON export, per references/test-plan.md section 3."""
from __future__ import annotations

import json

import schema
from validate_and_export import validate_and_export


def test_missing_required_columns_reported_exactly_and_none_guessed(tmp_path, rpa_workbook_factory, sample_row):
    # Deliberately broken input: only "naam" and "code" survive as columns
    # (mirrors test-plan.md's "naam+code only" scenario).
    broken_columns = ["naam", "code"]
    input_path = rpa_workbook_factory(
        rows=[{"naam": "Testproduct", "code": "COD1"}],
        columns=broken_columns,
    )
    output_path = tmp_path / "out.json"

    exit_code = validate_and_export(str(input_path), str(output_path))

    assert exit_code == 2
    # every required column NOT in the broken header must be reported
    expected_missing = [c for c in schema.REQUIRED_COLUMNS if c not in broken_columns]
    assert len(expected_missing) == len(schema.REQUIRED_COLUMNS) - 2
    # no output JSON should have been written on failure
    assert not output_path.exists()


def test_missing_registratie_column_specifically_detected(tmp_path, rpa_workbook_factory):
    # All REQUIRED_COLUMNS present except "registratie".
    columns = [c for c in schema.REQUIRED_COLUMNS if c != "registratie"]
    input_path = rpa_workbook_factory(rows=[{c: "x" for c in columns}], columns=columns)
    output_path = tmp_path / "out.json"

    exit_code = validate_and_export(str(input_path), str(output_path))

    assert exit_code == 2
    assert not output_path.exists()


def test_missing_columns_message_lists_each_missing_column(tmp_path, rpa_workbook_factory, capsys):
    columns = ["naam", "code"]
    input_path = rpa_workbook_factory(rows=[{"naam": "x", "code": "y"}], columns=columns)
    output_path = tmp_path / "out.json"

    validate_and_export(str(input_path), str(output_path))

    captured = capsys.readouterr()
    assert "missing required column" in captured.out.lower()
    for col in schema.REQUIRED_COLUMNS:
        if col not in columns:
            assert f"- {col}" in captured.out


def test_valid_workbook_exports_json_successfully(tmp_path, rpa_workbook_factory, sample_row):
    row = sample_row({
        "naam": "Metacam 1.5mg/ml",
        "code": "METACAM15",
        "registratie": "",
        "leverancier": "Boehringer",
        "artikelnummer": "1234",
        "barcode": "",
        "kanalisatie": "",
        "waarschuwing": "",
        "humaan": "",
        "farmaceutische vorm": "",
        "werkzame stof(fen) en concentratie": "",
        "blad productinformatie": "",
        "productgroep": "Pijnstillers",
        "nieuwe naam": "",
    })
    input_path = rpa_workbook_factory(rows=[row])
    output_path = tmp_path / "out.json"

    exit_code = validate_and_export(str(input_path), str(output_path))

    assert exit_code == 0
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["row_count"] == 1
    assert payload["rows"][0]["naam"] == "Metacam 1.5mg/ml"
    assert payload["rows"][0]["code"] == "METACAM15"
    # only REQUIRED_COLUMNS (+ row_index) are carried into each row record
    assert set(payload["rows"][0].keys()) == {"row_index", *schema.REQUIRED_COLUMNS}


def test_blank_rows_are_skipped(tmp_path, rpa_workbook_factory, sample_row):
    real_row = sample_row({"naam": "Rimadyl", "code": "RIM1"})
    blank_row = sample_row()  # everything ""
    input_path = rpa_workbook_factory(rows=[real_row, blank_row])
    output_path = tmp_path / "out.json"

    exit_code = validate_and_export(str(input_path), str(output_path))

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["row_count"] == 1
    assert payload["rows"][0]["naam"] == "Rimadyl"


def test_header_matching_is_case_insensitive(tmp_path, sample_row, tmp_path_factory):
    import openpyxl
    upper_columns = [c.upper() for c in schema.RPA_COLUMNS]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "RPA Products edit"
    ws.append(upper_columns)
    row = sample_row({"naam": "Apoquel", "code": "APO1"})
    ws.append([row.get(c, "") for c in schema.RPA_COLUMNS])
    input_path = tmp_path / "upper.xlsx"
    wb.save(input_path)
    output_path = tmp_path / "out.json"

    exit_code = validate_and_export(str(input_path), str(output_path))

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["rows"][0]["naam"] == "Apoquel"
