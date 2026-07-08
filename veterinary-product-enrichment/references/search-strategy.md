# Zoekstrategie -- 5 rondes

Nooit stoppen na één mislukte poging. Log ALTIJD welke rondes daadwerkelijk
zijn uitgevoerd in `toelichting_controle` (vrije tekst per product).

1. **Exacte identificatie**: bestaand registratienummer, barcode,
   artikelnummer+leverancier, exacte productnaam uit de input.
2. **Genormaliseerde naam**: normaliseer hoofdletters/leestekens, expandeer
   afkortingen, strip verpakkingsgrootte-info tijdelijk, probeer
   merk+concentratie / merk+werkzame-stof / merk+vorm combinaties, houd
   rekening met waarschijnlijke typefouten.
3. **Officiële databanken**: NL veterinaire registratie-DB, EU veterinaire
   product-DB, humane geneesmiddelen-DB waar relevant (zie
   `source-hierarchy.md`).
4. **Fabrikant & leverancier**: officiële fabrikant, marketingvergunning-
   houder, leverancier, groothandel, officiële productcatalogus (incl.
   `lookup_covetrus.py` als lokale fallback-ronde).
5. **Waarschijnlijke match**: alleen voorstellen wanneer MEERDERE
   kenmerken overeenkomen (naam, werkzame stof, concentratie, vorm,
   verpakkingsgrootte, fabrikant) -- resultaatstatus wordt dan
   "waarschijnlijk gevonden", nooit gepresenteerd als zeker.

## 'Niet gevonden' -- alleen toegestaan wanneer:

- alle 5 rondes zijn uitgevoerd,
- meerdere naamvarianten zijn geprobeerd,
- NL- en (waar relevant) EU- en humane-geneesmiddelbronnen zijn gecheckt,
- fabrikant/leverancier-bronnen zijn gecheckt,
- overwogen is of het product simpelweg geen geregistreerd geneesmiddel is
  (dan is `Niet van toepassing` het juiste antwoord, niet `Niet gevonden`).

## Batching / schaal

- Verwerk in batches van circa 15-25 producten tegelijk (contextbeheer).
- Boven ~150 rijen: overweeg per-batch parallelle subagents (zie skill
  `superpowers:dispatching-parallel-agents`), en voeg de JSON-resultaten
  samen vóór `write_output.py` wordt aangeroepen.
- Eén batch = één blok in `enrichment_results.json` (`rows: [...]`), zodat
  batches simpelweg geconcateneerd kunnen worden.
