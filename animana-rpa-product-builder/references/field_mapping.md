# Field & dropdown mapping (source of truth: `scripts/rpa_builder/mapping.py`)

This file explains the mapping in prose; the actual constants live in
`mapping.py` so there is exactly one place to change if the spec changes.

## Product field mapping (Animana column → RPA "RPA Products edit" column)

Direct 1:1 copy, no transformation, unless noted:

| Animana column | RPA column | Note |
|---|---|---|
| productgroep | productgroep | |
| naam | naam | |
| shortcode | code | |
| factuurtekst | factuurtekst | |
| kostprijs | kostprijs | written as a real number |
| verkoopeenheid | verkoopeenheid | |
| verpakkingsfactor | verpakkingsfactor | written as a real number |
| verpakkingseenheid | verpakkingseenheid | |
| bestelfactor | bestelfactor | written as a real number |
| besteleenheid | besteleenheid | |
| dosering | dosering | |
| vrije tekst | vrije tekst | |
| Blad productinformatie | blad productinformatie | |
| registratie | registratie | |
| waarschuwing | waarschuwing | |
| memo | memo | |
| opiaat | opiaat | literal 'true'/'false' string, unchanged |
| humandrug | humaan | literal 'true'/'false' string, unchanged |
| euthanasie | euthanasaat | literal 'true'/'false' string, unchanged |
| registratie minuten | registratie minuten | written as a real number |
| farmaceutische vorm | farmaceutische vorm | |
| werkzame stof(fen) en concentratie | werkzame stof(fen) en concentratie | |
| leverancier | leverancier | validated (see below), never guessed |
| artikelnummer | artikelnummer | |
| kanalisatie | kanalisatie | normalized (see below) |
| actief | actief | literal 'true'/'false'/'' string, unchanged; drives the actief-file filter |
| stockonpackage | voorraad obv verpakking | literal 'true'/'false' string, unchanged |
| actie | actie | validated (see below), never guessed |
| barcode | barcode | **always written as text**, never a number — preserves leading zeros |
| btw | btw | literal category ('hoog'/'laag'/'geen'), never converted to a % |
| verkoopprijs | **verkoopprijs ex** | Animana's value is EX btw; written as a real number |

**RPA columns intentionally left blank** (not in the client's mapping spec —
do not populate these even if a plausible-looking Animana source column
exists): nieuwe naam, basisprijs, marge product, **verkoopprijs incl** (never
computed — Animana itself fills this), toeslag, korting, analysegroep 1/2/3,
gewicht, etiket niet printen, verrichting, brief, toon product, verberg.

## Price field rule (do not deviate)

- `verkoopprijs` (Animana, ex btw) → `verkoopprijs ex` (RPA).
- `verkoopprijs incl` is **always left empty**. Never calculated, never
  copied from anywhere. Animana computes it after import.
- `btw` is copied verbatim as its category string (hoog/laag/geen) — never
  turned into a percentage or numeric rate.

## Validation rules (never guess — pass through unchanged + flag)

- **kanalisatie**: case/whitespace-insensitive match against the canonical
  set `{udd, uda, ura, vrij}` → normalize to the canonical lowercase spelling.
  Anything else (including plausible-looking synonyms like `free` or `ur`) is
  written through **unchanged** and flagged in the report — the script never
  guesses a synonym translation.
- **actie**: exact (case-sensitive) match against the fixed dropdown values
  `euthanasia` / `castration` (dropdowns!Q). Empty is fine. Anything else is
  written through unchanged and flagged.
- **leverancier**: exact (case-sensitive) match against **this run's own
  rebuilt leveranciers list** (dropdowns!M, built from the contacts export —
  not the old template values). Empty is fine. Anything else is written
  through unchanged and flagged. In the dev fixtures the contacts export is
  synthetic and unrelated to the product export's supplier strings, so nearly
  every leverancier value is flagged there — that's expected for
  non-correlated dev data, not a bug.
- A numeric-target field (kostprijs, verkoopprijs ex, verpakkingsfactor,
  bestelfactor, registratie minuten) that fails to parse as a number is
  written as **text** instead (never dropped/blanked) and flagged.

## Malformed source rows

A product-export row with the wrong column count (e.g. a stray trailing
comma) is never saved partially or shifted — it is skipped entirely and
reported by 1-based source row number (companion CSV
`... malformed-rows.csv` if there are many). This was exercised against the
real dev fixture: 2 of 301 rows have a genuine extra trailing comma and are
correctly skipped.

## Dropdowns sheet (`dropdowns`) column map

| Letter | Label | Behaviour |
|---|---|---|
| A | productgroepen | **account-bound**: rebuilt from productgroups export `naam` column |
| C | toeslagen | **account-bound**: rebuilt from the toeslagen copy-paste .txt (first tab-field per line) |
| E | margeregels | **account-bound**: rebuilt from the margeregels copy-paste .txt (first tab-field per line) |
| M | leveranciers | **account-bound**: rebuilt from contacts export, rows where `leverancier='true'`, `bedrijfsnaam` column, deduped |
| Y | brieven | **account-bound**: rebuilt from letters export `naam` column (`context` column ignored) |
| G | eenheden | **fixed** — byte-identical to template, never touched |
| I | btw | **fixed** — byte-identical to template, never touched |
| K | optie | **fixed** — byte-identical to template, never touched |
| O | kanalisatie | **fixed** — byte-identical to template, never touched |
| Q | actie | **fixed** — byte-identical to template, never touched |
| AA | aanklikken | **fixed** — byte-identical to template, never touched |
| AC | herinnertype | **fixed** — byte-identical to template, never touched |
| S, U, W, AE, AG, AI, AK | analysegroep 1/2/3, herinnergroep, notificatie, prijsgroep, magazijn | **cleared**: values wiped (header label row 1 kept), never preserved, never rebuilt — explicit client spec |

Optional source missing → its account-bound column is left completely empty
(no values at all, header label untouched) and the report notes it under
"Optional inputs missing".

Account-bound dropdown lists are deduped (case-sensitive, first-seen order
kept) and empty values are skipped, mirroring the explicit "skip empty,
dedupe" instruction given for the contacts/suppliers list — applied
consistently to all five account-bound sources for the same reason (a
duplicate/blank dropdown entry is never useful). This is a design default,
not stated verbatim in the client spec for every column — flag if the client
wants raw/unsorted/non-deduped lists instead.

Each account-bound column has a pre-provisioned capacity baked into the
template's own data-validation formula ranges (A/Y: 248 rows, C/E/M: 48 rows).
As long as a rebuilt list fits, nothing else needs to change. If a real
account's list is longer, every value is still written to the sheet (nothing
is dropped) but entries beyond the capacity won't show an Excel dropdown
arrow — the report flags this explicitly under "Capacity warnings" so it's
never a silent gap.
