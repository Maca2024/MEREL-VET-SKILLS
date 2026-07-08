---
name: veterinary-product-enrichment
description: Trigger wanneer de gebruiker een Animana/RPA Products-shaped Excel-productenlijst (veterinaire producten) wil laten verrijken/aanvullen/onderzoeken, of vraagt om ontbrekende registratienummers, farmaceutische vorm, werkzame stof(fen)+concentratie, kanalisatie, barcode, waarschuwing, blad productinformatie of praktische zoektermen op te zoeken voor zo'n productenlijst. Voert zelf een agentic onderzoek per product uit (WebSearch/WebFetch tegen publieke veterinaire bronnen, strikte bronhiërarchie + 5-waarden confidence-schaal) en levert huidig/voorstel/nieuw per veld terug -- bestaande data wordt NOOIT stilzwijgend overschreven. NIET gebruiken voor het genereren van de RPA Products-workbook zelf (dat is skill `animana-rpa-product-builder`, skill 1) -- alleen voor het verrijken/onderzoeken van een reeds bestaande, RPA Products-vormige lijst.
---

# Veterinary Product Data Enrichment

Dit is een AGENTIC onderzoeksproces, geen deterministisch script. Jij (Claude)
doet de per-product matching en confidence-beoordeling zelf, met WebSearch/
WebFetch, geleid door dit document. De Python-scripts doen alleen de
mechanische Excel-I/O en de deterministische nieuw-kolom-berekening.

## Verplichte leesvolgorde vóór je begint met onderzoeken

Een fresh Claude-instance die deze skill start moet, vóór de eerste
WebSearch, deze twee documenten hebben gelezen -- ze bevatten de regels die
elke bevinding sturen en zijn NIET optioneel:

1. **`references/source-hierarchy.md`** -- welke bron wint bij een conflict
   (1-7, strikte volgorde) + de KNMvD/WVAB-antibiotica-tier-regel.
2. **`references/confidence-and-status.md`** -- de twee schalen die je
   iedere keer opnieuw moet toepassen: de 5-waarden per-veld confidence
   (Hoog/Gemiddeld/Laag/Niet gevonden/Niet van toepassing) en de losstaande
   8-waarden rij-niveau `resultaatstatus`. Verzin nooit een 6e/9e waarde.

Daarna, per rij: `references/field-rules.md` (per-veld regels + eerst het
producttype bepalen) en `references/search-strategy.md` (de 5 verplichte
zoekrondes + batching bij grote bestanden).

## Kernprincipe

Bestaande data wordt NOOIT stilzwijgend overschreven. Elk verrijkbaar veld
krijgt huidig (ongewijzigd) / voorstel (jouw beste bevinding) / nieuw
(uiteindelijk samengestelde waarde), plus een beslissing-kolom waar de logica
een menselijke keuze vereist. Volledig kolomschema: zie
`references/output-schema.md`.

## Workflow

### Stap 1 -- Valideren + exporteren (mechanisch, script)

```
python scripts/validate_and_export.py <input.xlsx> <products.json>
```

- Werkt op ELK bestand dat aan de RPA Products-structuur voldoet -- een
  verse Skill-1-output, een oudere run, of een handmatig aangepast bestand.
  Maak NOOIT de aanname dat de input vers van Skill 1 komt.
- Ontbrekende verplichte kolommen (`scripts/schema.py: REQUIRED_COLUMNS`)
  -> het script meldt EXACT welke en stopt (exit code 2). Nooit een
  vervangende kolom raden. Meld dit aan de gebruiker en vraag om het
  brondocument te corrigeren.
- Bij succes: `products.json` bevat één record per productrij met
  `row_index` + alle bronvelden die je nodig hebt om te onderzoeken.

### Stap 2 -- Onderzoekslus (agentic, door JOU uitgevoerd)

Voor elke rij in `products.json`, in batches van ~15-25 rijen (zie
`references/search-strategy.md` voor batching/parallellisatie bij grote
bestanden):

1. **Producttype herkennen** (eerste stap, zie `references/field-rules.md`
   onderaan) -- bepaalt welke velden logisch van toepassing zijn.
2. **5 zoekrondes** uitvoeren volgens `references/search-strategy.md`,
   bronnen in de volgorde van `references/source-hierarchy.md`. Gebruik
   `python scripts/lookup_covetrus.py --barcode/--artikelnummer/--name ...`
   als lokale (niet-agentic) fallback-ronde 4 -- degradeert netjes als het
   bundled bestand nog ontbreekt.
3. **Per veld** een voorstel + confidence-label bepalen volgens
   `references/field-rules.md` en de 5-waarden-schaal in
   `references/confidence-and-status.md` (deel 1). Verzin geen 6e waarde.
4. **Rij-niveau `resultaatstatus`** holistisch bepalen (8 waarden, zie
   `references/confidence-and-status.md` deel 2) -- dit is een apart oordeel
   over de HELE rij, niet mechanisch afgeleid uit de veld-confidences.
5. Log in `toelichting_controle` welke zoekrondes/routes daadwerkelijk zijn
   uitgevoerd, met name vóórdat je concludeert tot "niet gevonden".

Schrijf de resultaten naar `enrichment_results.json` volgens dit schema
(één object per rij; zie `test-fixtures/enrichment_results.json` in de
build-workspace voor een volledig uitgewerkt voorbeeld):

```json
{
  "rows": [
    {
      "row_index": 2,
      "product_type": "veterinair geneesmiddel",
      "fields": {
        "registratie": {"voorstel": "REGNL06407", "confidence": "Hoog"},
        "barcode": {"voorstel": "8710040060872", "confidence": "Hoog"},
        "kanalisatie": {"voorstel": "udd", "confidence": "Hoog"},
        "farmaceutische vorm": {"voorstel": "suspensie voor oraal gebruik", "confidence": "Hoog"},
        "werkzame stof(fen) en concentratie": {"voorstel": "meloxicam 1,5 mg/ml", "confidence": "Hoog"},
        "humaan": {"voorstel": "false", "confidence": "Hoog"},
        "blad productinformatie": {"voorstel": "https://...", "confidence": "Hoog"},
        "waarschuwing": {"voorstel": "...", "confidence": "Gemiddeld", "bronpassage": "..."},
        "zoektermen": ["pijnstiller", "NSAID"]
      },
      "bron_url": "https://www.diergeneesmiddeleninformatiebank.nl/...",
      "resultaatstatus": "exact gevonden",
      "toelichting_controle": "Ronde 1-3 uitgevoerd; REGNL-nummer bevestigd via CBG."
    }
  ]
}
```

Alleen `voorstel` + `confidence` per veld hoeven geleverd te worden -- de
`huidig`/`nieuw`/`beslissing`-kolommen worden mechanisch berekend in stap 3.
Voor `code` lever je alleen `zoektermen` (lijst van max 3 strings); de
samenstelling van `code + zoektermen (voorstel)` gebeurt automatisch.

### Stap 3 -- Output schrijven (mechanisch, script)

```
python scripts/write_output.py <input.xlsx> <enrichment_results.json> <output.xlsx> [--previous-output <vorige-output.xlsx>]
```

- Past de deterministische nieuw-kolom-regels toe (`scripts/decision_logic.py`)
  -- zie regels hieronder, exact zoals gespecificeerd.
- `--previous-output`: bij een her-run trekt dit menselijk gezette
  `beslissing`-waarden door, en behoudt een `handmatig aanpassen`-waarde
  ALTIJD ongewijzigd (matcht op `code (huidig)`).
- Origineel input-bestand wordt NOOIT aangepast; de output is een nieuw
  bestand met een fris opgebouwd workbook (zie ontwerp-noot in
  `write_output.py` -- de originele template bevat een data-validation-
  extensie die openpyxl niet kan doorzetten; kopiëren zou een
  reparatie-prompt kunnen veroorzaken, dus wordt de output altijd vanaf nul
  opgebouwd).
- Rapporteert aan het einde: aantal rijen, coverage, aantal rijen dat
  review nodig heeft, en een resultaatstatus-verdeling. Neem dat over in je
  antwoord aan de gebruiker -- verzin geen "94% coverage" als het script iets
  anders rapporteerde.

## Nieuw-kolom-beslisregels (exact, per veld toegepast door het script)

1. huidig gevuld + geen betrouwbaar voorstel -> nieuw = huidig (ongewijzigd)
2. huidig leeg + voorstel confidence = Hoog -> nieuw = voorstel (auto-gevuld)
3. huidig en voorstel zijn gelijk -> nieuw = die waarde
4. huidig en voorstel VERSCHILLEN -> nieuw wordt NIET automatisch gewijzigd
   (blijft huidig), rij gemarkeerd voor review
5. voorstel confidence = Gemiddeld/Laag en wijkt af van huidig -> nooit
   automatisch overnemen
6. geen enkel resultaat -> nieuw = huidig, of blijft alleen leeg als huidig
   ook al leeg was

`beslissing`-kolomwaarden: `akkoord` (nieuw = voorstel) | `niet akkoord`
(nieuw = huidig) | `handmatig aanpassen` (gebruiker vult zelf in, script
raakt dit nooit meer aan bij een volgende run).

## Dekkingsdoel

Streef naar >=90% van de productrijen met een bruikbaar resultaat. Dit is
een KWALITEITSDOEL, geen afkapgrens -- gedeeltelijke resultaten worden altijd
bewaard en gerapporteerd, nooit weggelaten omdat de 90% niet gehaald wordt.
Een bruikbaar resultaat = 1+ betrouwbaar gevonden velden, OF een goed
onderbouwde waarschijnlijke match met review-vlag, OF een correct
onderbouwde "niet van toepassing", OF (in het slechtste geval) een heldere
uitleg waarom een product niet betrouwbaar verrijkt kon worden.

## Bestandsstructuur van deze skill

```
SKILL.md                           dit bestand
scripts/
  schema.py                        kolomstructuur (single source of truth)
  decision_logic.py                pure nieuw-kolom-beslisregels (unit-testbaar)
  validate_and_export.py           stap 1
  lookup_covetrus.py               lokale Covetrus-fallback-lookup
  write_output.py                  stap 3
references/
  source-hierarchy.md              bronvolgorde 1-7 + KNMvD/WVAB-regel
  search-strategy.md                5 zoekrondes + batching
  confidence-and-status.md          5-waarden veld-confidence + 8-waarden resultaatstatus
  field-rules.md                    per-veld regels + producttype-herkenning
  output-schema.md                  volledige kolomlijst (spiegelt schema.py)
  covetrus-mapping.md               kolomtoewijzing bundled asset (te verifiëren)
  test-plan.md                      hoe getest is / nog te testen
assets/
  covetrus-productenlijst.xlsx      (nog te leveren door Merel, zie assets/README)
```

## Afhankelijkheden

`openpyxl` (al geïnstalleerd). `rapidfuzz` voor fuzzy naam-matching in
`lookup_covetrus.py` (optioneel -- valt terug op substring-match als het
ontbreekt; installeer met `pip install rapidfuzz` voor betere matches).
