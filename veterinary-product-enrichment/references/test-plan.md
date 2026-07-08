# Testplan

## 1. Synthetische testworkbook (research-loop validatie)

Gebruik NIET de anonimiseerde kliniek-steekproef voor matching-validatie
(illustratief, niet gecureerd). Gebruik in plaats daarvan:
`tools/make_synthetic_fixture.py` -> `test-fixtures/synthetic-vet-products.xlsx`
(~18 rijen, RPA Products-vorm, bekende publieke veterinaire producten:
Metacam, Rimadyl, Clavubactin (amoxicilline/clavulaanzuur), Apoquel,
Previcox, Cerenia, Amoxibactin).

Rijen dekken bewust de decision-logic-randgevallen:
- leeg `huidig` + verwacht Hoog-confidence voorstel -> auto-vullen
- `huidig` al correct en gelijk aan voorstel -> ongewijzigd
- `huidig` registratie bewust VERKEERD/verouderd -> conflict, niet
  auto-overschreven, `resultaatstatus = handmatige controle nodig`
- humaan geneesmiddel (off-label diergebruik)
- verzorgingsproduct -> meerdere velden terecht "niet van toepassing"
- interne verrichting / administratieve regel -> vrijwel alles n.v.t.
- fictief/onvindbaar productnaam -> `niet gevonden`
- her-run met een reeds gezette `beslissing` (akkoord + handmatig
  aanpassen) om de merge-logica te toetsen

Run: `python scripts/validate_and_export.py <synthetic.xlsx> <products.json>`,
laat Claude de echte onderzoekslus draaien (WebSearch/WebFetch tegen de
bronhiërarchie) op `products.json`, schrijf `enrichment_results.json`, dan
`python scripts/write_output.py <synthetic.xlsx> <enrichment_results.json> <out.xlsx>`.

Geverifieerd tijdens de build (8 jul 2026) met een handmatig samengestelde
`enrichment_results.json` (ter vervanging van een echte onderzoekslus, om de
mechanische I/O + beslislogica te bewijzen zonder live web-calls):
- alle 18 rijen correct verwerkt, 95 kolommen, workbook opent zonder
  reparatie-prompt (round-trip via `openpyxl.load_workbook` na schrijven).
- Metacam: huidig leeg + Hoog -> auto-fill bevestigd.
- Rimadyl: huidig == voorstel -> ongewijzigd bevestigd.
- Clavubactin: huidig != voorstel -> NIET auto-gewijzigd, status
  "handmatige controle nodig" bevestigd.
- Fictief testproduct: "niet gevonden", niets auto-ingevuld, bevestigd.
- Her-run met `--previous-output`: `beslissing=akkoord` correct toegepast
  (nieuw wordt voorstel), `beslissing=handmatig aanpassen` correct
  behouden (script overschrijft de handmatige waarde niet), bevestigd.

## 2. Onafhankelijkheid van Skill 1

Skill 2 mag NOOIT aannemen dat de input vers van Skill 1 komt. Verifieer
apart, zodra Skill 1 een dev-fixture-output produceert:
1. Draai Skill 1 tegen zijn eigen dev-fixtures -> een RPA Products-workbook.
2. Draai `validate_and_export.py` daar rechtstreeks tegen -- moet slagen
   zonder enige Skill-2-specifieke aanpassing vooraf.
3. Draai ook tegen een handmatig aangepaste kopie (bv. een kolom hernoemd
   of verwijderd) om te bevestigen dat de ontbrekende-kolommen-melding
   correct triggert (zie stap 3 hieronder).

**Nog te doen (blokkeert op Skill 1's build):** stap 1-2 hierboven zijn nog
niet uitgevoerd omdat `skill1-animana-rpa-product-builder/` op moment van
schrijven leeg is (nog niet gebouwd).

## 3. Validatie-pad (ontbrekende kolommen)

Geverifieerd tijdens de build: een workbook met alleen `naam`+`code` als
kolommen levert exit code 2 en een exacte lijst van 12 ontbrekende
kolommen, zonder te gokken naar een vervangende kolom.

## 4. Covetrus-fallback zonder asset

Geverifieerd: `lookup_covetrus.py` geeft `{"available": false, ...}` terug
in plaats van te crashen wanneer `assets/covetrus-productenlijst.xlsx`
ontbreekt (het geval op deze build-machine).

## 5. Echte data (later, apart, op de Kathedraal)

Definitieve validatie tegen Merel's echte (vertrouwelijke) klinieklijst
gebeurt NIET hier -- alleen rechtstreeks op de Kathedraal, buiten deze
scratchpad/repo, zoals afgesproken in de opdracht.
