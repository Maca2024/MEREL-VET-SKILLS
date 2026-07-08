# Template structure discoveries (why the code looks the way it does)

Verified directly against the bundled `assets/RPA_Products_template.xlsx`
(also `Templete RPA Products (1).xlsx` in the dev fixtures — same file).

## The one fact that drives the whole architecture

The template's dropdown lists are **not** wired with Excel's classic
`<dataValidation>` element. They use the *extended* x14 format, nested inside
`<extLst><ext ...><x14:dataValidations>...</x14:dataValidations></ext></extLst>`
at the end of `xl/worksheets/sheet1.xml`. This is how Excel 2010+ stores list
validations whose source is a formula reference on another sheet
(`dropdowns!$A$2:$A$249` etc).

**openpyxl's writer does not round-trip this extension.** Loading the
template with openpyxl already prints:

```
UserWarning: Data Validation extension is not supported and will be removed
```

Confirmed experimentally: `openpyxl.load_workbook(template) → wb.save(...)`
silently produces a workbook with **zero working dropdowns** — every one of
the 13 x14 data-validation rules is gone. Since "all validations preserved,
opens without repair prompt" is a hard acceptance criterion, **this skill
never round-trips the workbook through openpyxl's writer.** All output is
produced by direct ZIP/XML surgery in `xlsx_xml.py`:

- `styles.xml`, `sharedStrings.xml`, theme, and every other zip part are
  copied byte-for-byte, untouched.
- `xl/worksheets/sheet1.xml` ('RPA Products edit') and `xl/worksheets/sheet2.xml`
  ('dropdowns') are the only two parts rewritten, and only the specific
  regions described below — the extLst validation block is left untouched
  unless the row count exceeds the template's pre-built capacity (see below).

openpyxl is still used, but only for **reading** source `.csv`/`.xlsx` files
(product export, productgroups, contacts, letters) — never for writing.

## Sheet1 ('RPA Products edit') structural facts

- 46 columns, A:AT, one header row, then **448 pre-styled empty data rows**
  (rows 2–449) — every cell in every one of those rows already carries the
  correct style index (`s="..."`) for its column (currency format on
  kostprijs/verkoopprijs ex/verpakkingsfactor/bestelfactor/registratie
  minuten, text format `@` on productgroep/naam/code, General elsewhere).
  Verified: the per-column style vector is byte-identical across every one
  of the 448 rows — so it can be read once (from row 2) and reused as a
  template for however many rows we actually generate.
- `<cols>` currently holds per-column custom widths (varying) — the client
  spec requires all of A:AT forced to width 20 regardless, so this block is
  fully replaced, not merged.
- `<autoFilter ref="A1:AT449"/>` and `<dimension ref="A1:AT449"/>` are
  rewritten to match the actual number of data rows written
  (`A1:AT{rows+1}`).
- The x14 validation ranges are generous but **capped at row 449** (e.g.
  `A2:A449`, `H2:H449`). If the account has more than 448 products, those
  extra rows would fall outside every dropdown's range. Handled by
  `bump_validation_row_cap()`: only when needed, it substitutes the literal
  `449` token for the new max row **inside `<xm:sqref>` elements only** —
  verified with a synthetic 598-row fixture (2× the dev fixture) that this
  correctly widens every one of the 13 ranges and the file still opens
  cleanly (well-formed XML, valid zip, openpyxl round-trip load OK).
- All generated data cells use **inline strings** (`t="inlineStr"`), never
  shared-string indices — this means `sharedStrings.xml` never needs to be
  touched/appended to for the data rows, eliminating a whole class of
  index-corruption risk. Numeric target fields (kostprijs, verkoopprijs ex,
  verpakkingsfactor, bestelfactor, registratie minuten) are written as real
  `<v>` numbers instead, matching their pre-applied currency number format.
  `barcode` and `code` are force-text regardless of how numeric they look
  (leading zeros).

## Sheet2 ('dropdowns') structural facts

- 19 "content" columns (A, C, E, G, I, K, M, O, Q, S, U, W, Y, AA, AC, AE, AG,
  AI, AK) separated by narrow blank spacer columns (B, D, F, ...) that are
  never populated — left untouched.
- Row 1 = column header labels for every column, **always kept verbatim**,
  even for the "cleared" columns (S/U/W/AE/AG/AI/AK) — only their *data* rows
  (2+) are wiped. This is a documented assumption (see SKILL.md open
  questions), not a verbatim client instruction for the header row
  specifically.
- The 7 **fixed** columns (G/I/K/O/Q/AA/AC) are copied **cell-fragment for
  cell-fragment, byte-identical**, straight from the template's XML for the
  matching row number — not regenerated from parsed values. This is the
  strongest possible fidelity guarantee for "never touch these."
- The 5 **account-bound** columns (A/C/E/M/Y) are rebuilt as fresh inlineStr
  cells, reusing whatever style index the template used for that column's
  data rows (read once from row 2), so visual formatting is unaffected even
  though the values are new.
- Column widths: A:AT-style "fixed width 20" does NOT apply here — this
  sheet autosizes each of the 19 content columns to its longest populated
  value (header included) using a simple `len(text) + 2` heuristic (clamped
  8–80). Spacer columns keep their original template width untouched. This
  is a cosmetic approximation of Excel's real autofit, not pixel-exact —
  acceptable since the acceptance criterion only requires it to not use a
  fixed width.
- No AutoFilter on this sheet (confirmed: template has none; output doesn't
  add one).

## Verified end-to-end (dev fixtures, this session)

- Ran against all 6 dev-fixture source files with account name "Kliniek
  Voorbeeld": 301 source rows → 2 correctly-detected malformed rows (real
  trailing-comma defect in the fixture CSV, not a parser bug) → 299 rows
  written 1:1 to the compleet file, 224 kept in the actief file (order and
  content verified to exactly match filtering the compleet file by
  actief∈{true,''}).
- Both output files: valid zip (`zipfile.testzip()` → no errors), both
  worksheet XML parts well-formed (`xml.etree.ElementTree.fromstring`
  succeeds), the x14 extLst validation block is present and intact, dropdown
  columns spot-checked (account-bound rebuilt correctly, fixed columns match
  template values, cleared columns empty from row 2 down), price fields load
  as real floats via openpyxl, verkoopprijs incl loads as `None` (empty),
  barcode loads as a string, actief-file filtering verified row-by-row.
- Re-ran against a synthetic 598-row fixture (2× the dev product export) to
  exercise the >448-row scaling path — first attempt caught a **real bug**
  (an inverted regex lookbehind meant the "449" row-cap tokens were never
  bumped); fixed and re-verified: `dimension`/`autoFilter` correctly widen to
  `A1:AT599`, every one of the 13 x14 `<xm:sqref>` ranges widens from 449 to
  599, zero stray "449" tokens left, file still well-formed and loads in
  openpyxl.
