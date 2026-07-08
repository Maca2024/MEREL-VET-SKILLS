"""Value-level normalization and dropdown-value validation. Never guesses:
anything not confidently recognized is passed through unchanged and flagged."""
from __future__ import annotations

from .mapping import KANALISATIE_CANONICAL

FIXED_ACTIE_VALUES = {"euthanasia", "castration"}


def normalize_kanalisatie(raw: str) -> tuple[str, bool]:
    """Returns (value_to_write, was_confidently_normalized).
    Case/whitespace-insensitive match to udd/uda/ura/vrij only -- no synonym
    translation (e.g. 'free' or 'ur' are NOT guessed as 'vrij'/'ura')."""
    if raw is None:
        return "", True
    stripped = raw.strip()
    if not stripped:
        return "", True
    lowered = stripped.lower()
    if lowered in KANALISATIE_CANONICAL:
        return lowered, True
    return raw, False


def validate_actie(raw: str) -> bool:
    """True if the value exactly matches one of the fixed actie dropdown
    values (or is empty). No case normalization -- exact match only, per spec
    (this is intentionally strict; revisit if real data shows case variance)."""
    stripped = (raw or "").strip()
    return stripped == "" or stripped in FIXED_ACTIE_VALUES


def validate_leverancier(raw: str, rebuilt_supplier_list: list[str]) -> bool:
    """True if the value exactly matches an entry in THIS run's rebuilt
    leveranciers dropdown list (or is empty)."""
    stripped = (raw or "").strip()
    return stripped == "" or stripped in rebuilt_supplier_list
