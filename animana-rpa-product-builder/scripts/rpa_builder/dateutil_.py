"""Derive DATUM from the source product-export filename. Tries structured
patterns first; falls back to file mtime. Never guesses silently -- always
reports which method was used so a wrong parse is caught immediately."""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

_PATTERNS = [
    (re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})"), lambda m: (m[1], m[2], m[3])),
    (re.compile(r"(\d{2})[-_](\d{2})[-_](20\d{2})"), lambda m: (m[3], m[2], m[1])),
]


def derive_datum(product_export_path: Path) -> tuple[str, str]:
    """Returns (datum_str YYYY-MM-DD, method_description)."""
    name = product_export_path.stem
    for pattern, extract in _PATTERNS:
        m = pattern.search(name)
        if m:
            y, mo, d = extract(m)
            try:
                parsed = dt.date(int(y), int(mo), int(d))
                return parsed.isoformat(), f"parsed from filename '{name}'"
            except ValueError:
                continue
    mtime = dt.date.fromtimestamp(product_export_path.stat().st_mtime)
    return mtime.isoformat(), (
        f"no date pattern found in filename '{name}' -- fell back to file "
        f"last-modified date"
    )
