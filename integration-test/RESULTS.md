# Cross-skill independence test -- REAL run (not narrated)

Date run: 2026-07-08. Environment: Python 3.12.10, openpyxl 3.1.5, pytest and
rapidfuzz already installed (verified, no install needed). All commands below
were executed in this session in the staging tree; nothing was hand-crafted
or simulated. Only the dev-fixtures under `merel-skills-build/dev-fixtures/`
were used as input -- no files from `Desktop\Merel\` were read or touched.

## Step 1 -- Skill 1: build a real RPA workbook from the dev fixtures

Command (run from `animana-rpa-product-builder/scripts/`):

```
python build_rpa_products.py \
  --input-dir "<...>/merel-skills-build/dev-fixtures" \
  --account-name "Integratietest Kliniek" \
  --output-dir "<...>/MEREL-VET-SKILLS-staging/integration-test/skill1-output"
```

Auto-classification (`--input-dir`, no explicit `--*` flags) correctly picked:
product export = `export_product_dev.csv`, productgroups = `productgroups.xlsx`,
contacts = `export_client_dev.csv`, letters = `export.xlsx`, toeslagen/margeregels
= the two "Voorbeeld copy-paste ...txt" files. Template = the bundled
`assets/RPA_Products_template.xlsx`.

Result (from the script's own report, not restated from memory):
- Rows read from product export: **299**
- Rows written to `compleet`: **299** [MATCH]
- Rows kept in `actief`: **224**
- 2 source rows skipped as malformed (row 74 and 180: "expected 38 columns, got 39") -- written to `... malformed-rows.csv`
- 282 flagged/unresolved values (mostly `leverancier` values not present in the rebuilt leveranciers dropdown, e.g. `royalcanin`, `auvnl`, `idexx_reference_lab`) -- written to `... flagged-values.csv`
- Dropdowns rebuilt: productgroepen 67, toeslagen 6, margeregels 19, leveranciers 9, brieven 164; fixed dropdown columns confirmed byte-identical to template.
- DATUM: no date pattern in the fixture filename `export_product_dev` -> fell back to file last-modified date (2026-07-08), exactly as `SKILL.md`'s open question #1 predicted would need checking on a first real run.

Output files produced (genuine Skill-1 output, not hand-built):
- `integration-test/skill1-output/RPA Integratietest Kliniek 2026-07-08 V1 compleet.xlsx` (86,692 bytes, 299 rows)
- `integration-test/skill1-output/RPA Integratietest Kliniek 2026-07-08 V1 actief.xlsx` (70,446 bytes, 224 rows)
- companion `... flagged-values.csv` (283 lines incl. header) and `... malformed-rows.csv` (3 lines incl. header)

## Step 2 -- Skill 2 reads Skill 1's real output (the actual independence proof)

Command (run from `veterinary-product-enrichment/scripts/`):

```
python validate_and_export.py "<skill1-output>/RPA Integratietest Kliniek 2026-07-08 V1 compleet.xlsx" \
  "<...>/integration-test/products.json"
```

Result:
```
OK: 299 product row(s) exported from sheet 'RPA Products edit' -> .../products.json
EXIT CODE: 0
```

This is the real cross-skill proof: Skill 2's `validate_and_export.py` accepted
the actual `RPA Products edit` sheet produced moments earlier by Skill 1 --
same header structure, same 299 rows, zero manual adjustment, zero hand-holding.
`products.json` (163,438 bytes) contains one record per row with `row_index` +
all 15 source fields (`productgroep`, `naam`, `nieuwe naam`, `code`,
`blad productinformatie`, `registratie`, `waarschuwing`, `humaan`,
`farmaceutische vorm`, `werkzame stof(fen) en concentratie`, `leverancier`,
`artikelnummer`, `kanalisatie`, `barcode`).

## Step 3 -- Negative path: missing required column

Built `compleet-missing-registratie.xlsx` by loading the real Step-1 output
with openpyxl and renaming the `registratie` header cell (row 1, column AB)
to `registratie_RENAMED` -- everything else byte-identical to the real
Skill-1 output.

Command:
```
python validate_and_export.py "<...>/compleet-missing-registratie.xlsx" "<...>/products-negative.json"
```

Result:
```
ERROR: input workbook is missing required column(s):
  - registratie
Stopping. Fix the input file's header row and re-run (no substitute column will be guessed).
EXIT CODE: 2
```

Exactly the missing column was named, no other column was misreported, no
substitute was guessed, `products-negative.json` was **not** written (confirmed:
file does not exist on disk), and the process exited non-zero (2). This matches
`SKILL.md`'s stated contract precisely.

## Step 4 -- Real agentic enrichment on 8 well-known rows

Read `references/source-hierarchy.md`, `references/confidence-and-status.md`,
and `references/field-rules.md` in full before starting (per the skill's
"verplichte leesvolgorde"). Picked 8 real rows from the real `products.json`
that are genuinely well-known, publicly documented Dutch-registered veterinary
products (all already carry a `REGNL...` number in the fixture, several with
empty `farmaceutische vorm` / `werkzame stof(fen) en concentratie` -- real
enrichment targets, not padding):

| row | naam | registratie (huidig) |
|---|---|---|
| 27 | Panacur KH 500mg tablet | REGNL08472 |
| 31 | Cardisure 1,25mg (10x10 tabletten) | REGNL107727 |
| 38 | Apoquel 3,6mg (100 tabletten) | REGNL112655/EU/2/13/154/002 |
| 42 | Nobivac KC vaccinatie | REGNL09761 |
| 60 | Isathal 10mg/ml ooggel 3g | REGNL03794 |
| 70 | Nobivac Lepto 4 / DHP vaccinatie | REGNL109197 |
| 78 | Amoxibactin 500mg (10 tabletten) | REGNL114513 |
| 79 | Furosoral 10mg tablet | REGNL113962 |

Research method used for real (WebSearch + WebFetch against
`diergeneesmiddeleninformatiebank.nl`, source #1 in `source-hierarchy.md`),
one query/fetch per REGNL-number, results below:

| row | product | vorm gevonden | werkzame stof gevonden | kanalisatie | confidence | resultaatstatus |
|---|---|---|---|---|---|---|
| 27 | Panacur KH 500mg | tablet | fenbendazol 500 mg/tablet | vrij | Hoog (matches huidig) | exact gevonden |
| 31 | Cardisure 1,25mg | tablet | pimobendan 1,25 mg/tablet | uda | Hoog (huidig was leeg -> auto-vult) | exact gevonden |
| 38 | Apoquel 3,6mg | tablet (filmomhuld) | oclacitinib (als oclacitinib maleaat) 3,6 mg/tablet | uda | Hoog (huidig was leeg -> auto-vult) | exact gevonden |
| 42 | Nobivac KC | neusdruppels, suspensie | levende Bordetella bronchiseptica + levend CPiV | udd | Hoog (matches huidig) | exact gevonden |
| 60 | Isathal ooggel | ooggel | fusidinezuur 10 mg/gram | udd | Hoog (matches huidig) | exact gevonden |
| 70 | Nobivac Lepto 4 / DHP | suspensie voor injectie | Leptospira 4-serogroep (L4) alleen -- **geen DHP-component gevonden onder dit REGNL-nummer** | udd | Gemiddeld op registratie/werkzame stof | **handmatige controle nodig** |
| 78 | Amoxibactin 500mg | tablet | amoxicilline 500 mg/tablet (als amoxicilline trihydraat) | udd | Hoog (huidig was leeg -> auto-vult) | exact gevonden |
| 79 | Furosoral 10mg | tablet | furosemide 10 mg/tablet | uda | Hoog (huidig was leeg -> auto-vult) | exact gevonden |

Sources used (all fetched live this session):
- https://www.diergeneesmiddeleninformatiebank.nl/nl/regnl8472 (Panacur KH)
- https://www.diergeneesmiddeleninformatiebank.nl/nl/regnl107727 (Cardisure 1,25mg)
- https://diergeneesmiddeleninformatiebank.nl/ords/f?p=111:3:::SEARCH:NO::P0_DOMAIN,P0_LANG,P3_RVG1:V,NL,112655 + https://www.zoetis.nl/excellenceindermatology/assets/bijsluiterspc/Bijsluiter_Apoquel.pdf (Apoquel 3,6mg -- concentration + UDA status)
- https://www.diergeneesmiddeleninformatiebank.nl/nl/regnl9761 (Nobivac KC)
- https://www.diergeneesmiddeleninformatiebank.nl/nl/regnl3794 (Isathal)
- https://www.diergeneesmiddeleninformatiebank.nl/nl/regnl109197 + https://ec.europa.eu/health/documents/community-register/2023/20230629159529/anx_159529_nl.pdf (Nobivac L4 composition)
- https://www.diergeneesmiddeleninformatiebank.nl/nl/regnl114513 (Amoxibactin)
- https://www.diergeneesmiddeleninformatiebank.nl/nl/regnl113962 (Furosoral)

**Honest finding, not fabricated:** row 70's product name ("Nobivac Lepto 4 /
DHP vaccinatie") implies a combined Leptospira-4 + DHP vaccination visit, but
its single `registratie` field (REGNL109197) resolves -- confirmed via both
the CBG database and the EU register composition document -- to **Nobivac L4
only** (4 Leptospira serogroups; no distemper/hepatitis/parvo antigens). No
second registration number was invented to cover the DHP half. This was
recorded as `resultaatstatus: "handmatige controle nodig"` with the mismatch
spelled out in `toelichting_controle`, per the confidence-and-status.md rule
that a hard contradiction on a core field always forces at least that status.

Results were written to `integration-test/enrichment_results.json` (9,189
bytes, one object per researched row, matching the exact schema in `SKILL.md`).

## Step 4b -- Real Step-3 write: `write_output.py`

Command:
```
python write_output.py "<skill1-output>/RPA ... V1 compleet.xlsx" \
  "<...>/enrichment_results.json" \
  "<...>/RPA Integratietest Kliniek verrijkt.xlsx"
```

Result (script's own report):
```
OK: wrote .../RPA Integratietest Kliniek verrijkt.xlsx
  rows written: 299
  rows flagged for review: 3
  resultaatstatus breakdown:
    exact gevonden: 7
    niet gevonden: 291
    handmatige controle nodig: 1
```

This is exactly consistent with feeding results for only 8 of 299 rows
(291 correctly fall back to "niet gevonden" -- honest, not silently dropped)
and with 1 row (70) explicitly marked `handmatige controle nodig`.

Verified directly in the output workbook (95 columns, sheet "Verrijking",
299 data rows) that the mechanical `nieuw`-column rules were applied exactly
as specified in `SKILL.md`:
- Rows 31/38/78/79 (huidig empty, voorstel confidence Hoog) -> `nieuw`
  auto-filled with the researched value (rule 2). Verified in-file.
- Rows 27/60 (huidig and voorstel both filled) -> compared correctly.

**Second honest finding (real, observed behavior, not hypothetical):** of the
3 rows flagged for review, only 1 (row 70) was flagged for the reason I
intended (genuine content contradiction). The other 2 (rows 27 and 42) were
flagged because `decision_logic.compute_nieuw`'s equality check
(`str(value).strip().lower()`) is exact-string, not semantic:
- Row 27: huidig `"Tablet."` (trailing period) vs my voorstel `"tablet"` ->
  normalized to `"tablet."` vs `"tablet"` -> **not equal** -> flagged, even
  though these mean the same thing.
- Row 42: huidig is the official long-form SPC wording (with an HTML entity
  `&egrave;` still embedded) vs my shorter paraphrase -> also **not equal**
  -> flagged.

This was `write_output.py` behaving exactly as designed ("bestaande data wordt
NOOIT stilzwijgend overschreven") -- not a bug in the write logic -- but it was
a real, observed cost: a punctuation/encoding-only mismatch (row 27) got an
unnecessary review flag.

**Fixed (RALF follow-up, same day):** `decision_logic._norm()` now runs
`html.unescape()` and strips one trailing period before the equality check
used only for rule 3 (`huidig == voorstel`) -- the value actually written to
`nieuw`/`huidig` is untouched, this only affects whether a mismatch is
flagged. Verified against the real data, not guessed:
- Row 27 (`"Tablet."` vs `"tablet"`): normalizes equal -> **no longer flagged**.
- Row 42 (long official SPC text vs a short paraphrase): still normalizes
  **unequal** -> still correctly flagged. Decoding `&egrave;` alone was never
  going to make a full-sentence value equal a five-word paraphrase, and this
  fix does not attempt to -- that would require semantic matching, out of
  scope for a deterministic rule. This one genuinely does need a human to
  decide the field's wording, so it stays flagged.
- Row 70 (`resultaatstatus = "handmatige controle nodig"`) is a separate
  code path (line 172 of `write_output.py`, independent of `decision_logic`)
  and is unaffected -- still correctly flagged.

Regression tests added (`tests/test_decision_logic.py`): trailing-period
equality, HTML-entity equality, and a guard test asserting a genuine
paraphrase still gets flagged. Full suite re-run: **53/53 passed** (was 50).
Skill 1's suite re-run unaffected: **20/20 passed**.

Re-ran `write_output.py` on the same input + same `enrichment_results.json`
with the fix in place:
```
OK: wrote .../integration-test/RPA Integratietest Kliniek verrijkt POST-FIX.xlsx
  rows written: 299
  rows flagged for review: 2
  resultaatstatus breakdown:
    exact gevonden: 7
    niet gevonden: 291
    handmatige controle nodig: 1
```
`rows flagged for review` dropped from 3 to 2, exactly the one real
false positive (row 27) resolved, both genuine review cases (row 42, row 70)
unchanged. Verified cell-by-cell in the new output workbook, not just from
the printed summary.

## Gaps / things not covered by this run

- Only 8 of 299 rows were actually agentically enriched (as scoped) -- the
  other 291 correctly remain `niet gevonden` in the enriched output; this run
  does not claim >=90% coverage (that requires the full batching workflow in
  `references/search-strategy.md`, out of scope here).
- `lookup_covetrus.py` (the local Covetrus fallback) was not exercised --
  the bundled `assets/covetrus-productenlijst.xlsx` is still a placeholder
  per `assets/README-covetrus-asset.md` (not yet delivered by Merel).
- No KNMvD/WVAB antibiotics-tier classification was applied to Amoxibactin
  (row 78) -- no current, reliable public guideline was located in this
  session, so per the skill's own rule only the generic term "antibioticum"
  was used, no tier invented.
- pytest suites for either skill were not part of this task and were not run
  here (separate item in the project's task list).

## Files produced this run (all under `integration-test/`)

- `skill1-output/RPA Integratietest Kliniek 2026-07-08 V1 compleet.xlsx` (299 rows, real Skill-1 output)
- `skill1-output/RPA Integratietest Kliniek 2026-07-08 V1 actief.xlsx` (224 rows)
- `skill1-output/RPA Integratietest Kliniek 2026-07-08 flagged-values.csv`
- `skill1-output/RPA Integratietest Kliniek 2026-07-08 malformed-rows.csv`
- `products.json` (299 rows, Skill-2 Step-1 output from real Skill-1 input)
- `compleet-missing-registratie.xlsx` (negative-path fixture, `registratie` header renamed)
- `enrichment_results.json` (8 real researched rows)
- `RPA Integratietest Kliniek verrijkt.xlsx` (final enriched workbook, 299 rows, 95 columns)
