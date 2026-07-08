"""
Deterministic field/dropdown mapping tables for the Animana -> RPA Products ETL.

These are business-spec constants (verified against the real client spec and the
bundled template), not values read from the template at runtime. Template *structure*
(styles, column letters, validation ranges) is discovered at runtime in xml_template.py
so the script keeps working if the template gets minor edits -- but the *business
mapping* below is the contract and must only change on an explicit spec change.
"""

# RPA "RPA Products edit" sheet header -> 0-based column index (A=0 ... AT=45)
RPA_HEADERS = [
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
assert len(RPA_HEADERS) == 46  # A:AT

RPA_COL = {name: idx for idx, name in enumerate(RPA_HEADERS)}  # 0-based

# Animana source column -> RPA target column name. Direct 1:1 copy unless noted.
# Fields not listed here are intentionally left blank in the RPA sheet (not part
# of the client's mapping spec): "nieuwe naam", "basisprijs", "marge product",
# "verkoopprijs incl" (Animana computes it, never write it), "toeslag", "korting",
# "analysegroep 1/2/3", "gewicht", "etiket niet printen", "verrichting", "brief",
# "toon product", "verberg".
DIRECT_FIELD_MAP = {
    "productgroep": "productgroep",
    "naam": "naam",
    "shortcode": "code",
    "factuurtekst": "factuurtekst",
    "kostprijs": "kostprijs",
    "verkoopeenheid": "verkoopeenheid",
    "verpakkingsfactor": "verpakkingsfactor",
    "verpakkingseenheid": "verpakkingseenheid",
    "bestelfactor": "bestelfactor",
    "besteleenheid": "besteleenheid",
    "dosering": "dosering",
    "vrije tekst": "vrije tekst",
    "Blad productinformatie": "blad productinformatie",
    "registratie": "registratie",
    "waarschuwing": "waarschuwing",
    "memo": "memo",
    "opiaat": "opiaat",
    "humandrug": "humaan",
    "euthanasie": "euthanasaat",
    "registratie minuten": "registratie minuten",
    "farmaceutische vorm": "farmaceutische vorm",
    "werkzame stof(fen) en concentratie": "werkzame stof(fen) en concentratie",
    "leverancier": "leverancier",
    "artikelnummer": "artikelnummer",
    "kanalisatie": "kanalisatie",
    "actief": "actief",
    "stockonpackage": "voorraad obv verpakking",
    "actie": "actie",
    "barcode": "barcode",
    "btw": "btw",
    # price field renamed + semantics: Animana verkoopprijs is EX btw
    "verkoopprijs": "verkoopprijs ex",
}

# RPA target columns that must be written as real Excel numbers (numFmt #,##0.00
# in the template), everything else in DIRECT_FIELD_MAP is written as text
# (inline string) to preserve exact source formatting (leading zeros, literal
# 'true'/'false', literal btw category, etc).
NUMERIC_TARGET_FIELDS = {
    "kostprijs", "verkoopprijs ex", "verpakkingsfactor", "bestelfactor",
    "registratie minuten",
}

# Fields whose RPA target column is always written as literal text even if the
# value looks numeric (barcode must never lose leading zeros / become a float).
FORCE_TEXT_TARGET_FIELDS = {"barcode", "code"}

# Boolean-style fields that carry through as the literal strings 'true'/'false'
# (matching the dropdowns!K column's own literal values) -- never converted to
# real Excel booleans, never re-cased.
BOOLEAN_PASSTHROUGH_TARGET_FIELDS = {
    "opiaat", "humaan", "euthanasaat", "actief", "voorraad obv verpakking",
}

# Canonical kanalisatie categories. Normalisation is case/whitespace-insensitive
# ONLY -- no synonym translation (e.g. 'free' is NOT auto-mapped to 'vrij';
# that would be guessing). Unrecognized values pass through unchanged + flagged.
KANALISATIE_CANONICAL = {"udd", "uda", "ura", "vrij"}

# 'RPA Products edit' column letter for the "actief" field, used to filter the
# second (active-only) output file.
ACTIEF_COLUMN_LETTER = "AM"

# --- dropdowns sheet column map -------------------------------------------
# Column letter -> dropdown sheet header label, per the bundled template.
FIXED_DROPDOWN_COLUMNS = {
    "G": "eenheden", "I": "btw", "K": "optie", "O": "kanalisatie",
    "Q": "actie", "AA": "aanklikken", "AC": "herinnertype",
}
ACCOUNT_BOUND_DROPDOWN_COLUMNS = {
    "A": "productgroepen", "C": "toeslagen", "E": "margeregels",
    "M": "leveranciers", "Y": "brieven",
}
# Populated in the template but cleared to empty (values wiped, header label
# kept) per explicit client spec -- not preserved, not rebuilt.
CLEARED_DROPDOWN_COLUMNS = {
    "S": "analysegroep 1", "U": "analysegroep 2", "W": "analysegroep 3",
    "AE": "herinnergroep", "AG": "notificatie", "AI": "prijsgroep",
    "AK": "magazijn",
}

# Generous pre-provisioned capacity for each account-bound dropdown column, as
# baked into the template's x14 data-validation formula ranges (dropdowns!$A$2:
# $A$249 etc). We never need to touch these formula ranges as long as the
# rebuilt list fits -- if it doesn't, we still write every value (Excel dropdown
# arrow just won't show entries beyond the capacity) and flag it in the report.
ACCOUNT_DROPDOWN_CAPACITY = {"A": 248, "C": 48, "E": 48, "M": 48, "Y": 248}
