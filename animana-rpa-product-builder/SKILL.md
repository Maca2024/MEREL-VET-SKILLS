---
name: animana-rpa-product-builder
description: Deterministic ETL that turns an Animana veterinary product export (plus a few optional supporting exports/copy-paste lists) into a filled RPA Products workbook, using the client's fixed Excel template. Use when the user asks to build/generate/vullen an "RPA Products" workbook from Animana exports, or mentions "RPA Products template", "productgroepen dropdown", "leveranciers dropdown", or an Animana product/contacts/productgroups export together with an account name.
---

# Animana RPA Product Builder

Purely mechanical, no AI judgment: reads one account's Animana exports and fills
the fixed `RPA Products` template with them. Every decision (field mapping,
dropdown rebuilds, filtering) is deterministic and documented in
`references/field_mapping.md`. This skill never edits, redesigns, or
reformats the template — it only inserts data into the existing structure.

## When to use this skill

The user provides (or points at a folder containing):
1. An Animana product export (`.csv` or `.xlsx`) — **required**.
2. A product groups export (`.xlsx`, sheet "naam" column) — **required**.
3. An account name to stamp into the output filenames — **required**.
4. Optionally: a contacts/clients export (for suppliers), a letters export, and
   two tab-separated copy-paste text files (toeslagen, margeregels).

## How to run it

```bash
python scripts/build_rpa_products.py \
  --product-export "<path to Animana product export>" \
  --productgroups "<path to productgroups export>" \
  --account-name "<Account Name>" \
  --output-dir "<where to write the two output files>" \
  [--contacts "<path to contacts export>"] \
  [--letters "<path to letters export>"] \
  [--toeslagen "<path to toeslagen copy-paste .txt>"] \
  [--margeregels "<path to margeregels copy-paste .txt>"]
```

If the user just hands you a folder of exports without saying which file is
which, use `--input-dir <folder>` instead of the individual `--*` flags — the
script classifies each file by its header signature (never by filename or
extension). Explicit `--*` flags always win over auto-detection.

The template asset is bundled at `assets/RPA_Products_template.xlsx` and is
used automatically (override with `--template` only if the client sends a
newer version of the template — confirm with the user before swapping it in,
since the whole skill is built around this file's exact structure).

## What it produces

Exactly two `.xlsx` files in `--output-dir`, both never overwriting a prior
run (a numeric ` (2)`, ` (3)`, ... suffix is added on a name collision):

- `RPA <account> <datum> V1 compleet.xlsx` — every product row, 1:1, same order.
- `RPA <account> <datum> V1 actief.xlsx` — same file, rows with `actief=false`
  removed (empty `actief` counts as active).

`<datum>` is parsed from the product export's filename if it contains a
recognizable date pattern, otherwise falls back to the file's last-modified
date (the report always says which method was used — check it before trusting
the filename date blindly for a brand-new client).

The script also prints a processing report to stdout (source files used, row
counts, dropdown counts, any missing optional inputs, any flagged/invalid
values) and — only if there's anything to flag — writes companion CSVs
(`... flagged-values.csv`, `... malformed-rows.csv`) next to the output files
so the report stays readable even at 10,000+ rows.

Before handing either file to the client, open it once yourself: it must load
with **zero repair prompt** and every dropdown (productgroepen, leveranciers,
etc.) must still show its arrow. That's the hard acceptance criterion this
skill is built around (see `references/template_layout.md`) — a repair prompt
means something touched the workbook outside this script and the run should
not be trusted.

## Read before making any changes

- `references/field_mapping.md` — the full source→target field mapping,
  dropdown column map, and every validation rule (kanalisatie normalization,
  actie/leverancier pass-through-and-flag, price field semantics).
- `references/template_layout.md` — why this skill edits the template's raw
  XML instead of using openpyxl to save it, and the structural facts that
  design relies on. **Read this before touching `scripts/rpa_builder/xlsx_xml.py`**
  — the template's dropdowns use Excel's extended (x14/extLst) data-validation
  format, which most libraries (including openpyxl's writer) silently destroy
  on save.

## Dependencies

- Python 3.12, `openpyxl` (already available) — used only for *reading*
  `.xlsx` source files, never for writing the output workbooks.
- No other third-party packages required.

## Known open questions (confirm with the client before the real-data run)

1. **DATUM filename convention** — the dev fixture's product export filename
   (`export_product_dev.csv`) has no embedded date, so the filename→date
   parser is untested against a real Animana export name. Check the report's
   "(parsed from filename ... / fell back to ...)" line on the first real run.
2. **actie / leverancier matching is case-sensitive, exact-match only** — no
   normalization is applied (unlike kanalisatie). If real accounts show
   case-variant suppliers/actions, revisit `normalize.py`.
3. **Dropdowns sheet "cleared" columns** (analysegroep 1-3, herinnergroep,
   notificatie, prijsgroep, magazijn) — this build clears only the *values*
   (rows 2+) and keeps the column header label in row 1. Confirm that matches
   the client's expectation.
