"""Shared pytest fixtures for the Veterinary Product Data Enrichment skill.

Adds the skill's scripts/ directory to sys.path so tests can `import schema`,
`import decision_logic`, `import validate_and_export`, `import write_output`,
`import lookup_covetrus` the same way the scripts import each other.
"""
from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import schema  # noqa: E402


def _sample_row(overrides: dict | None = None) -> dict:
    """A minimally-valid RPA_COLUMNS row as a dict, with everything except
    the columns callers care about left blank."""
    row = {col: "" for col in schema.RPA_COLUMNS}
    row.update(overrides or {})
    return row


def write_rpa_workbook(path: Path, rows: list[dict], columns: list[str] | None = None) -> Path:
    """Build an RPA-Products-shaped workbook at `path` from a list of row
    dicts (missing keys default to ""). `columns` lets a test deliberately
    drop/rename header columns (e.g. to test missing-column detection)."""
    columns = columns if columns is not None else list(schema.RPA_COLUMNS)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "RPA Products edit"
    ws.append(columns)
    for row in rows:
        ws.append([row.get(col, "") for col in columns])
    wb.save(path)
    return path


@pytest.fixture
def sample_row():
    return _sample_row


@pytest.fixture
def rpa_workbook_factory(tmp_path):
    def _factory(rows: list[dict], columns: list[str] | None = None, filename: str = "input.xlsx") -> Path:
        return write_rpa_workbook(tmp_path / filename, rows, columns)
    return _factory
