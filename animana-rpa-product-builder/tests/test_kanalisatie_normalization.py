"""kanalisatie normalization is case/whitespace-insensitive ONLY: it must
never guess a 5th value beyond udd/uda/ura/vrij. An unrecognized source
value passes through UNCHANGED and gets flagged for manual review -- never
silently coerced to one of the 4 canonical values."""
from __future__ import annotations

import csv

from rpa_builder.normalize import normalize_kanalisatie

from conftest import load_sheet1_rows, run_cli, write_minimal_productgroups

KANALISATIE_COL = 43  # 0-based; column AT... wait computed below, see test that derives it live


def test_kanalisatie_col_index_is_43():
    # Derived from rpa_builder.mapping.RPA_HEADERS at test time, not hardcoded
    # blind -- guards the constant above against future header reordering.
    from rpa_builder.mapping import RPA_COL
    assert RPA_COL["kanalisatie"] == KANALISATIE_COL


# --- unit level: rpa_builder.normalize.normalize_kanalisatie -----------------

def test_recognized_values_normalize_case_and_whitespace_insensitively():
    for raw, expected in [
        ("udd", "udd"), ("UDD", "udd"), ("  Udd  ", "udd"),
        ("uda", "uda"), ("URA", "ura"), ("Vrij", "vrij"), (" vrij", "vrij"),
    ]:
        value, confident = normalize_kanalisatie(raw)
        assert value == expected
        assert confident is True


def test_unrecognized_value_passes_through_unchanged_and_unconfident():
    value, confident = normalize_kanalisatie("free")
    assert value == "free"  # NOT coerced to 'vrij'
    assert confident is False

    value, confident = normalize_kanalisatie("ur")
    assert value == "ur"  # NOT coerced to 'ura'
    assert confident is False


def test_empty_value_normalizes_to_empty_and_confident():
    for raw in ("", "   ", None):
        value, confident = normalize_kanalisatie(raw)
        assert value == ""
        assert confident is True


# --- integration level: through the real CLI --------------------------------

def test_unrecognized_kanalisatie_value_written_unchanged_and_flagged(tmp_path):
    header = ["id", "productgroep", "naam", "verkoopprijs", "kostprijs", "actief", "barcode", "kanalisatie"]
    src = tmp_path / "product_export.csv"
    with open(src, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerow(["1", "GroepA", "UDD product", "10.00", "5.00", "true", "1", "  UDD  "])
        w.writerow(["2", "GroepA", "Weird product", "10.00", "5.00", "true", "2", "free"])
        w.writerow(["3", "GroepA", "Blank product", "10.00", "5.00", "true", "3", ""])

    productgroups = write_minimal_productgroups(tmp_path / "productgroups.xlsx", ["GroepA"])
    out = tmp_path / "out"
    out.mkdir()
    result = run_cli(out, product_export=src, productgroups=productgroups)
    assert result.returncode == 0, result.stdout + result.stderr

    compleet = next(p for p in out.iterdir() if p.suffix == ".xlsx" and "compleet" in p.name)
    rows = load_sheet1_rows(compleet)
    data_rows = rows[1:]

    assert data_rows[0][KANALISATIE_COL] == "udd"       # normalized
    assert data_rows[1][KANALISATIE_COL] == "free"      # passed through UNCHANGED, not coerced to 'vrij'
    assert data_rows[2][KANALISATIE_COL] in ("", None)  # blank stays blank

    # flagged for manual review, with the raw (unmodified) value quoted
    assert "kanalisatie='free'" in result.stdout
    assert "not confidently mappable to udd/uda/ura/vrij" in result.stdout

    flagged_csv = out / f"RPA Test Kliniek Dev {_datum_from_stdout(result.stdout)} flagged-values.csv"
    assert flagged_csv.exists()
    with open(flagged_csv, encoding="utf-8") as fh:
        flagged = list(csv.DictReader(fh))
    kanalisatie_flags = [f for f in flagged if f["field"] == "kanalisatie"]
    assert len(kanalisatie_flags) == 1
    assert kanalisatie_flags[0]["raw_value"] == "free"


def _datum_from_stdout(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("DATUM: "):
            return line.split()[1]
    raise AssertionError("no DATUM line in stdout")
