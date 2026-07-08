# Covetrus-productenlijst -- kolomtoewijzing (STATUS: GEVERIFIEERD)

Het bundled bestand `assets/covetrus-productenlijst.xlsx` (sheet `PRIJS`,
17.551 rijen) is aangeleverd en staat op de Kathedraal in
`/home/merel/.claude/skills/veterinary-product-enrichment/assets/`.
`scripts/lookup_covetrus.py` blijft ontworpen om te degraderen naar
`{"available": false}` als het bestand ontbreekt (bijv. op een andere
machine), maar de kolommapping hieronder is nu tegen de echte asset
gecontroleerd, niet meer een aanname op 3 rijen.

## Kolomposities (0-indexed, zoals `ws.iter_rows(..., values_only=True)`
teruggeeft) -- gecorrigeerd na een off-by-one bug (de vorige versie van deze
tabel noemde zich "0-indexed" maar bevatte per ongeluk de 1-indexed
Excel-kolomnummers):

| 0-indexed | Excel-kolom | Veld | Voorbeeldwaarde |
|---|---|---|---|
| 0 | A | Omschrijving | "Clavusan 500mg/125mg tablet" |
| 1 | B | Leverancier | "ALFASAN NL" |
| 4 | E | Prijs | "187.15" |
| 7 | H | Covetrus-eigen artikelnummer | "4009001" |
| 8 | I | Registratie-achtige code | "RVG06193" / "REGNL08608" |
| 10 | K | Barcode/GTIN (13-cijferig EAN) | "5701170461398" |
| 12 | M | Kanalisatie-achtige korte code | "UA" / "URA" / "UDD" |

Kolommen C, D, F, G, J, L bevatten andere Covetrus-interne velden (o.a. een
constante `1`, verkoopeenheid, een verpakkingsfactor, en een aantal/
voorraadachtig getal in kolom L) die niet worden gebruikt door deze skill.

## Verificatie uitgevoerd (8 juli 2026)

- `python scripts/lookup_covetrus.py --verify-mapping` getest tegen de volle
  asset: alle 7 velden komen nu overeen met de echte kolominhoud.
- `--barcode 5701170461398` correct gevonden: Clavusan 500mg/125mg (Alfasan),
  score 100.
- `--name "Imaverol"` correct beide verpakkingsgroottes gevonden (100ml/1000ml,
  Audevard), fuzzy score 80.
- Kolom M ("UA", "URA", "UDD" gezien in de steekproef) bevestigd als
  kanalisatie-achtige code -- normalisatie naar `uda`/`ura`/`udd`/`vrij`
  gebeurt in `decision_logic.py`/`field-rules.md`; "UA" wordt daar behandeld
  als een variant die niet blind 1-op-1 op "uda" gemapt mag worden zonder
  aanvullende bevestiging (zie kanalisatie-sectie in `field-rules.md`) --
  dat normalisatiegedrag is door deze kolom-fix niet veranderd, alleen de
  bron-extractie was fout.

## Onderhoud

Dit bestand is een periodiek te verversen asset (geen live scrape). Bij een
nieuwe versie van Merel: overschrijf `assets/covetrus-productenlijst.xlsx`
en draai `--verify-mapping` opnieuw om te bevestigen dat de kolomstructuur
niet gewijzigd is.

**Laatst geverifieerd:** 8 juli 2026, tegen de volledige 17.551-rijen asset
op de Kathedraal.
