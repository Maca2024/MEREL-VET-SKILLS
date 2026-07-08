"""Running the builder twice into the same --output-dir with the same
account name/date must never overwrite the first run's files. The actual
mechanism (read from build_rpa_products.unique_output_path) is a
' (2)', ' (3)', ... suffix appended before the extension on collision --
this test asserts that real, observed behavior rather than an assumed
scheme, and separately locks down unique_output_path() as a unit so a
future refactor of the collision strategy is caught."""
from __future__ import annotations

import sys

from conftest import BUILD_SCRIPT, SCRIPTS_DIR, load_sheet1_rows, run_cli, write_minimal_productgroups

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import importlib.util

_spec = importlib.util.spec_from_file_location("build_rpa_products", BUILD_SCRIPT)
build_rpa_products = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_rpa_products)


def _make_source(tmp_path, naam="Product One"):
    import csv
    header = ["id", "productgroep", "naam", "verkoopprijs", "kostprijs", "actief", "barcode"]
    src = tmp_path / "product_export.csv"
    with open(src, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerow(["1", "GroepA", naam, "10.00", "5.00", "true", "1"])
    return src


def test_second_run_same_output_dir_does_not_overwrite_first(tmp_path):
    src1 = _make_source(tmp_path, naam="First Run Product")
    productgroups = write_minimal_productgroups(tmp_path / "productgroups.xlsx", ["GroepA"])
    out = tmp_path / "out"
    out.mkdir()

    result1 = run_cli(out, product_export=src1, productgroups=productgroups)
    assert result1.returncode == 0, result1.stdout + result1.stderr
    files_after_run1 = {p.name: p.read_bytes() for p in result1.xlsx_files()}
    assert len(files_after_run1) == 2

    # Second run: same account name, same output dir, same source filename
    # (so DATUM derivation is identical too) but DIFFERENT product content --
    # if collision-handling failed and silently overwrote, run 1's bytes
    # would be gone.
    src2 = tmp_path / src1.name  # already same path/name as src1 -- reuse deliberately
    with open(src2, "w", newline="", encoding="utf-8") as fh:
        import csv
        w = csv.writer(fh)
        w.writerow(["id", "productgroep", "naam", "verkoopprijs", "kostprijs", "actief", "barcode"])
        w.writerow(["1", "GroepA", "Second Run Product", "10.00", "5.00", "true", "1"])

    result2 = run_cli(out, product_export=src2, productgroups=productgroups)
    assert result2.returncode == 0, result2.stdout + result2.stderr

    all_files = sorted(p.name for p in out.iterdir() if p.suffix == ".xlsx")
    assert len(all_files) == 4, all_files  # 2 from each run -- nothing overwritten

    # Run 1's original files must be byte-for-byte untouched.
    for name, original_bytes in files_after_run1.items():
        assert (out / name).read_bytes() == original_bytes, f"{name} was modified by the second run"

    # Run 2 must have produced its own collision-suffixed pair with its own content.
    run2_files = [p for p in out.iterdir() if p.suffix == ".xlsx" and p.name not in files_after_run1]
    assert len(run2_files) == 2
    compleet2 = next(p for p in run2_files if "compleet" in p.name)
    rows = load_sheet1_rows(compleet2)
    assert rows[1][1] == "Second Run Product"  # column B = naam


def test_unique_output_path_appends_numeric_suffix_on_collision(tmp_path):
    """Locks down the actual collision strategy read from the source
    (build_rpa_products.unique_output_path): first call returns the plain
    name, subsequent calls append ' (2)', ' (3)', ... before the extension."""
    directory = tmp_path
    filename = "RPA Kliniek 2026-01-01 V1 compleet.xlsx"

    first = build_rpa_products.unique_output_path(directory, filename)
    assert first == directory / filename
    first.write_text("run1")

    second = build_rpa_products.unique_output_path(directory, filename)
    assert second != first
    assert second.name == "RPA Kliniek 2026-01-01 V1 compleet (2).xlsx"
    second.write_text("run2")

    third = build_rpa_products.unique_output_path(directory, filename)
    assert third.name == "RPA Kliniek 2026-01-01 V1 compleet (3).xlsx"

    # first file's content must remain exactly what it was
    assert first.read_text() == "run1"
    assert second.read_text() == "run2"
