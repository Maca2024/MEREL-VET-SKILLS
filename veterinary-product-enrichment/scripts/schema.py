"""Single source of truth for the RPA Products input structure and the
enrichment output structure. Every other script imports from here so the
column layout only ever has to change in one place.

Derived from: dev-fixtures/Templete RPA Products (1).xlsx, sheet
"RPA Products edit", row 1 (46 columns, verified 2026-07-08).
"""

# --- Exact original RPA Products column order (Skill 1 output shape) ------

RPA_COLUMNS = [
    "productgroep", "naam", "nieuwe naam", "code", "factuurtekst", "kostprijs",
    "basisprijs", "btw", "marge product", "verkoopprijs ex", "verkoopprijs incl",
    "toeslag", "korting", "verkoopeenheid", "verpakkingsfactor", "verpakkingseenheid",
    "bestelfactor", "besteleenheid", "dosering", "vrije tekst", "analysegroep 1",
    "analysegroep 2", "analysegroep 3", "gewicht", "etiket niet printen",
    "blad productinformatie", "verrichting", "registratie", "waarschuwing", "memo",
    "opiaat", "humaan", "euthanasaat", "registratie minuten", "actie", "brief",
    "toon product", "verberg", "actief", "farmaceutische vorm",
    "werkzame stof(fen) en concentratie", "leverancier", "artikelnummer",
    "kanalisatie", "barcode", "voorraad obv verpakking",
]

# Columns this skill actually reads/needs to do its job. If any of these are
# missing from the input workbook's header row, validate_and_export.py must
# report exactly which ones and stop -- never guess a substitute column.
REQUIRED_COLUMNS = [
    "productgroep", "naam", "nieuwe naam", "code", "blad productinformatie",
    "registratie", "waarschuwing", "humaan", "farmaceutische vorm",
    "werkzame stof(fen) en concentratie", "leverancier", "artikelnummer",
    "kanalisatie", "barcode",
]

# --- Enrichable fields -------------------------------------------------
# Standard fields: get {veld} (huidig) / (voorstel) / (confidence voorstel) /
# (nieuw) + beslissing ({veld}). "waarschuwing" additionally gets a bronpassage
# column. "code" is handled separately (CODE_OUTPUT_COLUMNS) because its
# huidig/voorstel/nieuw shape is different (zoektermen composition, not a
# plain value swap).

STANDARD_FIELDS = [
    "blad productinformatie",
    "registratie",
    "humaan",
    "farmaceutische vorm",
    "werkzame stof(fen) en concentratie",
    "kanalisatie",
    "barcode",
]

WAARSCHUWING_FIELD = "waarschuwing"

CONFIDENCE_VALUES = ["Hoog", "Gemiddeld", "Laag", "Niet gevonden", "Niet van toepassing"]

RESULTAATSTATUS_VALUES = [
    "exact gevonden", "grotendeels gevonden", "waarschijnlijk gevonden",
    "gedeeltelijk verrijkt", "meerdere mogelijke matches",
    "niet van toepassing", "niet gevonden", "handmatige controle nodig",
]

BESLISSING_VALUES = ["akkoord", "niet akkoord", "handmatig aanpassen", ""]


def field_columns(field: str) -> list[str]:
    """Return the ordered output column names for one standard field."""
    return [
        f"{field} (huidig)",
        f"{field} (voorstel)",
        f"{field} (confidence voorstel)",
        f"{field} (nieuw)",
        f"beslissing ({field})",
    ]


def waarschuwing_columns() -> list[str]:
    return [
        "waarschuwing (huidig)",
        "waarschuwing (voorstel)",
        "waarschuwing (confidence voorstel)",
        "waarschuwing bronpassage (voorstel)",
        "waarschuwing (nieuw)",
        "beslissing (waarschuwing)",
    ]


CODE_OUTPUT_COLUMNS = [
    "code (huidig)",
    "zoektermen (voorstel)",
    "code + zoektermen (voorstel)",
    "beslissing (code)",
    "code (nieuw)",
]

ROW_CONTROL_COLUMNS = ["bron URL", "resultaatstatus", "toelichting controle"]


def enrichment_output_columns() -> list[str]:
    """Full ordered list of NEW columns appended after the 46 original
    RPA_COLUMNS in the output workbook."""
    cols = list(CODE_OUTPUT_COLUMNS)
    cols += waarschuwing_columns()
    for field in STANDARD_FIELDS:
        cols += field_columns(field)
    cols += ROW_CONTROL_COLUMNS
    return cols


def full_output_columns() -> list[str]:
    return list(RPA_COLUMNS) + enrichment_output_columns()


# Barcode-like columns must always be written as text (preserve leading
# zeros, avoid Excel scientific-notation mangling).
TEXT_FORMAT_COLUMNS = {"barcode", "barcode (huidig)", "barcode (voorstel)", "barcode (nieuw)"}
