# Output-schema (single source of truth = `scripts/schema.py`)

Dit document is een leesbare spiegel van `scripts/schema.py`. Bij een
conflict wint `schema.py` (het is wat de code daadwerkelijk uitvoert).

## Kolomvolgorde in het output-werkblad ("Verrijking")

1. Alle 46 originele RPA Products-kolommen, ongewijzigd, in originele
   volgorde (`RPA_COLUMNS`).
2. **code-blok** (5 kolommen):
   `code (huidig)`, `zoektermen (voorstel)`,
   `code + zoektermen (voorstel)`, `beslissing (code)`, `code (nieuw)`
3. **waarschuwing-blok** (6 kolommen, met aparte bronpassage):
   `waarschuwing (huidig)`, `waarschuwing (voorstel)`,
   `waarschuwing (confidence voorstel)`,
   `waarschuwing bronpassage (voorstel)`, `waarschuwing (nieuw)`,
   `beslissing (waarschuwing)`
4. Voor elk van de 7 standaardvelden (`blad productinformatie`,
   `registratie`, `humaan`, `farmaceutische vorm`,
   `werkzame stof(fen) en concentratie`, `kanalisatie`, `barcode`) --
   5 kolommen per veld:
   `{veld} (huidig)`, `{veld} (voorstel)`, `{veld} (confidence voorstel)`,
   `{veld} (nieuw)`, `beslissing ({veld})`
5. **Rij-niveau bron/control** (3 kolommen, niet meer):
   `bron URL`, `resultaatstatus`, `toelichting controle`

Totaal: 46 + 5 + 6 + (7 x 5) + 3 = **95 kolommen**
(geverifieerd tegen de daadwerkelijk geschreven testworkbook, 8 jul 2026).

## Waarom een confidence-kolom per veld, terwijl de brief die niet expliciet
als output-kolom noemt

De nieuw-kolom-beslisregels ("huidig empty + voorstel confidence = Hoog ->
auto-fill", etc.) zijn zonder een bewaarde per-veld confidence-waarde niet
navolgbaar of herhaalbaar bij een latere her-run/audit. Dit is dus geen
toegevoegde scope, maar de minimale infrastructuur om de reeds gespecificeerde
regels uitvoerbaar EN controleerbaar te maken.

## Waarom geen apart 'producttype'-kolom

De opdracht instrueert expliciet "BRON/CONTROL COLUMNS ... do not add more".
Producttype-herkenning is wel verplicht als eerste denk-stap (zie
`field-rules.md`), maar wordt vooralsnog opgenomen in de vrije tekst van
`toelichting controle` in plaats van als eigen kolom, om binnen de
afgesproken kolomset te blijven. Als Merel een aparte kolom wil, is dat een
kleine, geïsoleerde toevoeging aan `schema.py` + `write_output.py`.

## Extra werkblad: "Verwerkingsrapport"

Naast het "Verrijking"-werkblad bevat de output een tweede blad met: totaal
aantal producten, coverage-percentage (bruikbaar resultaat, zie
`README`/SKILL.md voor de definitie), aantal rijen dat handmatige review
nodig heeft, en een telling per `resultaatstatus`-waarde.
