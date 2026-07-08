"""End-to-end run of the real CLI against the full anonymized dev-fixtures
set (all optional inputs supplied). Verifies output-file count and that the
'compleet'/'actief' row counts match numbers independently recomputed from
the raw source CSV -- never trusting the tool's own printed report."""
from __future__ import annotations

import csv

from conftest import DEV_FIXTURES_DIR, load_sheet1_rows, run_full_dev_fixtures

ACTIEF_COL_INDEX = 38  # 0-based; column AM, per rpa_builder.mapping.ACTIEF_COLUMN_LETTER


def _independent_source_counts():
    """Re-parses export_product_dev.csv from scratch (not calling any
    rpa_builder code) to get ground-truth valid/malformed/active counts."""
    path = DEV_FIXTURES_DIR / "export_product_dev.csv"
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    header, data = rows[0], rows[1:]
    ncols = len(header)
    actief_idx = header.index("actief")
    valid = [r for r in data if len(r) == ncols]
    malformed = [r for r in data if len(r) != ncols]
    active = [r for r in valid if (r[actief_idx] or "").strip() in ("", "true")]
    return {
        "ncols": ncols,
        "valid_count": len(valid),
        "malformed_count": len(malformed),
        "active_count": len(active),
    }


def test_produces_exactly_two_output_files(tmp_path):
    result = run_full_dev_fixtures(tmp_path / "out")
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(result.xlsx_files()) == 2, [p.name for p in result.output_files()]
    names = {p.name for p in result.xlsx_files()}
    assert any("compleet" in n for n in names)
    assert any("actief" in n for n in names)


def test_compleet_row_count_matches_independently_recomputed_valid_rows(tmp_path):
    ground_truth = _independent_source_counts()
    result = run_full_dev_fixtures(tmp_path / "out")
    assert result.returncode == 0, result.stdout + result.stderr

    compleet = next(p for p in result.xlsx_files() if "compleet" in p.name)
    rows = load_sheet1_rows(compleet)
    header, data_rows = rows[0], rows[1:]

    assert len(data_rows) == ground_truth["valid_count"]
    # sanity: the run's own report agrees with the independently recomputed number
    assert f"Rows written to 'compleet' file: {ground_truth['valid_count']}" in result.stdout


def test_actief_file_contains_only_true_or_empty_actief_rows(tmp_path):
    ground_truth = _independent_source_counts()
    result = run_full_dev_fixtures(tmp_path / "out")
    assert result.returncode == 0, result.stdout + result.stderr

    actief_path = next(p for p in result.xlsx_files() if "actief" in p.name)
    rows = load_sheet1_rows(actief_path)
    data_rows = rows[1:]

    assert len(data_rows) == ground_truth["active_count"]
    for row in data_rows:
        actief_value = row[ACTIEF_COL_INDEX]
        assert (actief_value or "") in ("", "true"), row
