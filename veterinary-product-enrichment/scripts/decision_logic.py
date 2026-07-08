"""Pure, deterministic implementation of the 'nieuw'-column decision rules.

This is intentionally NOT agentic -- given huidig/voorstel/confidence/
beslissing it always produces the same nieuw value. Keeping it pure and
separate from write_output.py makes it independently unit-testable and
guarantees the same rule is applied identically across thousands of rows,
instead of relying on per-row judgment for a mechanical decision.

Rules (verbatim source: skill brief):
  1. huidig filled + no reliable voorstel            -> nieuw = huidig
  2. huidig empty + voorstel confidence = Hoog        -> nieuw = voorstel
  3. huidig and voorstel are equal                    -> nieuw = that value
  4. huidig and voorstel DIFFER                       -> nieuw NOT auto-changed
  5. confidence Gemiddeld/Laag differs from huidig     -> never auto-adopt
  6. no result at all                                  -> nieuw = huidig
                                                           (stays empty only if
                                                           huidig was empty too)
  beslissing overrides:
    akkoord            -> nieuw = voorstel
    niet akkoord        -> nieuw = huidig
    handmatig aanpassen -> nieuw is user-owned; never touched by this function
                            (caller must preserve the prior nieuw value)
"""

from __future__ import annotations

import html


def _is_empty(value) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _norm(value) -> str:
    """Normalize a value for the rule-3 equality check only (never used to
    decide what gets written -- huidig is always what's returned verbatim).

    Decodes leftover HTML entities (source workbooks sometimes carry raw
    entities like '&egrave;') and drops one trailing period, so genuinely
    identical values ("Tablet." vs "tablet") aren't flagged for human review
    purely over punctuation/encoding differences. Anything else that
    differs -- wording, length, content -- still compares unequal and is
    still flagged, exactly as before.
    """
    if value is None:
        return ""
    normalized = html.unescape(str(value)).strip().lower()
    return normalized.rstrip(".")


def compute_nieuw(huidig, voorstel, confidence: str, beslissing: str = "") -> tuple[str, bool]:
    """Return (nieuw_value, needs_review).

    needs_review is True when a human should look at this cell (huidig and
    voorstel disagree and no beslissing has been recorded yet).
    `beslissing` must be one of schema.BESLISSING_VALUES ("" = not decided).
    For beslissing == "handmatig aanpassen" this function returns
    (None, False) as a sentinel -- the caller MUST keep whatever nieuw value
    already exists in a previous run's output and never overwrite it.
    """
    beslissing = (beslissing or "").strip().lower()

    if beslissing == "handmatig aanpassen":
        return None, False
    if beslissing == "akkoord":
        return voorstel if not _is_empty(voorstel) else huidig, False
    if beslissing == "niet akkoord":
        return huidig, False

    huidig_empty = _is_empty(huidig)
    voorstel_empty = _is_empty(voorstel)

    if huidig_empty and voorstel_empty:
        return "", False

    if not huidig_empty and voorstel_empty:
        return huidig, False

    if huidig_empty and not voorstel_empty:
        if confidence == "Hoog":
            return voorstel, False
        # Gemiddeld / Laag / Niet gevonden / Niet van toepassing / unknown:
        # never auto-fill an empty huidig on anything less than Hoog.
        return "", True

    # both filled
    if _norm(huidig) == _norm(voorstel):
        return huidig, False
    # they differ -> do not auto-change, flag for human review
    return huidig, True


def compose_code_plus_zoektermen(code_huidig, zoektermen: list[str]) -> str:
    terms = [t.strip() for t in (zoektermen or []) if t and t.strip()]
    parts = [str(code_huidig).strip()] if not _is_empty(code_huidig) else []
    parts += terms[:3]
    return " ".join(parts).strip()


def compute_code_nieuw(code_huidig, code_plus_terms, beslissing: str = "") -> tuple[str, bool]:
    beslissing = (beslissing or "").strip().lower()
    if beslissing == "handmatig aanpassen":
        return None, False
    if beslissing == "akkoord":
        return (code_plus_terms or code_huidig), False
    if beslissing == "niet akkoord":
        return code_huidig, False
    # no decision yet: never touch the operational code, keep it usable.
    return code_huidig, False
