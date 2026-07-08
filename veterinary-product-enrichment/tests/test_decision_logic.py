"""Unit tests for decision_logic.compute_nieuw -- every branch of the
huidig/voorstel/nieuw decision rules documented in decision_logic.py's own
docstring and references/field-rules.md.
"""
from __future__ import annotations

import pytest

from decision_logic import (
    compose_code_plus_zoektermen,
    compute_code_nieuw,
    compute_nieuw,
)


# --- Rule 1: huidig empty + voorstel confidence=Hoog -> auto-fill ----------

def test_empty_huidig_hoog_confidence_autofills():
    nieuw, needs_review = compute_nieuw("", "REG-NL-12345", "Hoog")
    assert nieuw == "REG-NL-12345"
    assert needs_review is False


def test_empty_huidig_hoog_confidence_autofills_even_when_huidig_is_none():
    nieuw, needs_review = compute_nieuw(None, "REG-NL-12345", "Hoog")
    assert nieuw == "REG-NL-12345"
    assert needs_review is False


# --- Rule 2: huidig == voorstel -> nieuw = that value ----------------------

def test_huidig_equals_voorstel_keeps_value():
    nieuw, needs_review = compute_nieuw("udd", "udd", "Hoog")
    assert nieuw == "udd"
    assert needs_review is False


def test_huidig_equals_voorstel_case_and_whitespace_insensitive():
    # decision_logic._norm lowercases + strips before comparing
    nieuw, needs_review = compute_nieuw("Amoxicilline 500mg", "  amoxicilline 500mg  ", "Gemiddeld")
    assert nieuw == "Amoxicilline 500mg"  # huidig value preserved verbatim
    assert needs_review is False


def test_huidig_equals_voorstel_ignoring_trailing_period():
    # Regression: real dev-fixture row 27 had huidig "Tablet." vs a
    # researched voorstel "tablet" -- same value, punctuation-only diff.
    nieuw, needs_review = compute_nieuw("Tablet.", "tablet", "Hoog")
    assert nieuw == "Tablet."  # huidig preserved verbatim, not overwritten
    assert needs_review is False


def test_huidig_equals_voorstel_ignoring_html_entities():
    # Regression: source workbooks sometimes carry raw HTML entities
    # (e.g. '&egrave;') that a plain string compare would treat as unequal
    # to the decoded/plain-text voorstel.
    nieuw, needs_review = compute_nieuw("cr&egrave;me-kleurig", "crème-kleurig", "Hoog")
    assert nieuw == "cr&egrave;me-kleurig"
    assert needs_review is False


def test_huidig_and_voorstel_still_flagged_when_genuinely_different():
    # Guard against over-normalizing: a short paraphrase of a long official
    # text must still be flagged -- these are not the same value.
    nieuw, needs_review = compute_nieuw(
        "Lyofilisaat en suspendeervloeistof voor suspensie voor nasale toediening.",
        "neusdruppels, suspensie",
        "Hoog",
    )
    assert nieuw == "Lyofilisaat en suspendeervloeistof voor suspensie voor nasale toediening."
    assert needs_review is True


# --- Rule 3: huidig != voorstel -> nieuw stays huidig, flagged for review --

def test_huidig_differs_from_voorstel_never_auto_overwritten():
    nieuw, needs_review = compute_nieuw("RVG06193", "RVG09999", "Hoog")
    assert nieuw == "RVG06193"  # huidig wins, even at Hoog confidence
    assert needs_review is True


def test_huidig_differs_from_voorstel_at_low_confidence_also_flagged():
    nieuw, needs_review = compute_nieuw("RVG06193", "RVG09999", "Laag")
    assert nieuw == "RVG06193"
    assert needs_review is True


# --- Rule 4: confidence Gemiddeld/Laag differing from empty huidig -------
# -> never auto-adopted, even though huidig has nothing to lose by filling.

@pytest.mark.parametrize("confidence", ["Gemiddeld", "Laag", "Niet gevonden", "Niet van toepassing", ""])
def test_empty_huidig_sub_hoog_confidence_never_autofills(confidence):
    nieuw, needs_review = compute_nieuw("", "some-proposed-value", confidence)
    assert nieuw == ""
    assert needs_review is True


def test_empty_huidig_unknown_confidence_label_never_autofills():
    # Defensive: an unrecognised confidence string must not accidentally
    # behave like "Hoog".
    nieuw, needs_review = compute_nieuw("", "some-proposed-value", "hoog")  # wrong case
    assert nieuw == ""
    assert needs_review is True


# --- Rule 5: no result found -> nieuw = huidig (or stays empty) -----------

def test_no_voorstel_found_keeps_filled_huidig():
    nieuw, needs_review = compute_nieuw("bestaande-waarde", "", "Niet gevonden")
    assert nieuw == "bestaande-waarde"
    assert needs_review is False


def test_no_voorstel_found_keeps_filled_huidig_voorstel_none():
    nieuw, needs_review = compute_nieuw("bestaande-waarde", None, "Niet gevonden")
    assert nieuw == "bestaande-waarde"
    assert needs_review is False


def test_no_result_and_huidig_also_empty_stays_empty():
    nieuw, needs_review = compute_nieuw("", "", "Niet gevonden")
    assert nieuw == ""
    assert needs_review is False


def test_both_empty_none_stays_empty():
    nieuw, needs_review = compute_nieuw(None, None, "Niet gevonden")
    assert nieuw == ""
    assert needs_review is False


# --- beslissing overrides ---------------------------------------------------

def test_beslissing_akkoord_adopts_voorstel_regardless_of_confidence():
    nieuw, needs_review = compute_nieuw("oud", "nieuw-voorstel", "Laag", beslissing="akkoord")
    assert nieuw == "nieuw-voorstel"
    assert needs_review is False


def test_beslissing_akkoord_falls_back_to_huidig_if_voorstel_empty():
    nieuw, needs_review = compute_nieuw("oud", "", "Niet gevonden", beslissing="akkoord")
    assert nieuw == "oud"
    assert needs_review is False


def test_beslissing_niet_akkoord_keeps_huidig():
    nieuw, needs_review = compute_nieuw("oud", "voorstel-dat-genegeerd-wordt", "Hoog", beslissing="niet akkoord")
    assert nieuw == "oud"
    assert needs_review is False


def test_beslissing_handmatig_aanpassen_returns_sentinel_none():
    # Caller (write_output.py) is responsible for preserving the previous
    # run's user-entered value when it sees this sentinel.
    nieuw, needs_review = compute_nieuw("oud", "nieuw-voorstel", "Hoog", beslissing="handmatig aanpassen")
    assert nieuw is None
    assert needs_review is False


def test_beslissing_is_case_and_whitespace_insensitive():
    nieuw, _ = compute_nieuw("oud", "nieuw-voorstel", "Hoog", beslissing="  AKKOORD  ")
    assert nieuw == "nieuw-voorstel"


# --- code + zoektermen composition ------------------------------------------

def test_compose_code_plus_zoektermen_appends_up_to_three_terms():
    result = compose_code_plus_zoektermen("METACAM15", ["pijnstiller", "NSAID", "ontsteking", "extra-vierde"])
    assert result == "METACAM15 pijnstiller NSAID ontsteking"


def test_compose_code_plus_zoektermen_no_code():
    result = compose_code_plus_zoektermen("", ["pijnstiller"])
    assert result == "pijnstiller"


def test_compose_code_plus_zoektermen_no_terms():
    result = compose_code_plus_zoektermen("METACAM15", [])
    assert result == "METACAM15"


def test_compute_code_nieuw_akkoord_uses_composed_string():
    nieuw, _ = compute_code_nieuw("METACAM15", "METACAM15 pijnstiller NSAID", beslissing="akkoord")
    assert nieuw == "METACAM15 pijnstiller NSAID"


def test_compute_code_nieuw_niet_akkoord_keeps_original_code():
    nieuw, _ = compute_code_nieuw("METACAM15", "METACAM15 pijnstiller NSAID", beslissing="niet akkoord")
    assert nieuw == "METACAM15"


def test_compute_code_nieuw_handmatig_aanpassen_returns_sentinel_none():
    nieuw, _ = compute_code_nieuw("METACAM15", "METACAM15 pijnstiller NSAID", beslissing="handmatig aanpassen")
    assert nieuw is None


def test_compute_code_nieuw_no_decision_never_touches_operational_code():
    nieuw, _ = compute_code_nieuw("METACAM15", "METACAM15 pijnstiller NSAID", beslissing="")
    assert nieuw == "METACAM15"
