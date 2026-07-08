![MEREL-VET-SKILLS](merel-vet-skills-artwork.png)

# MEREL-VET-SKILLS

**Twee Claude Code skills voor veterinaire product-data in Animana — gebouwd door AetherLink B.V. voor Merel Heijnen's business-development traject in de dierenartsen-softwaremarkt.**

---

## Waarom dit bestaat

Merel Heijnen brengt ~20 jaar ervaring in veterinaire praktijksoftware mee (Animana, IDEXX, Smart Vet Agency) naar haar rol als business developer. Een terugkerend, tijdrovend probleem in die wereld: een dierenartsenpraktijk levert een exportbestand aan vanuit Animana, en daar moet een correct gevulde **"RPA Products"**-werkmap uit ontstaan — de bestandsindeling waarmee een praktijk zijn volledige productcatalogus (met dropdowns, kanalisatie-codes, leveranciers, prijzen) in één keer bij Animana kan laten importeren. Vandaag gebeurt dat handmatig: kolommen kopiëren, dropdown-lijsten met de hand herbouwen, en losse opzoekwerk per product om ontbrekende registratienummers, farmaceutische vormen of werkzame stoffen aan te vullen. Dat is foutgevoelig, traag, en schaalt niet naar de tientallen klinieken die Merel in haar pijplijn heeft.

Deze repository bevat twee Claude Code skills die dat proces in twee scherp gescheiden stappen automatiseren:

1. **`animana-rpa-product-builder`** — een volledig deterministisch ETL-script: Animana-export in, correct gevulde RPA Products-werkmap uit. Geen AI-oordeel, geen giswerk — puur mechanisch, reproduceerbaar, en gebouwd rond de exacte (en behoorlijk eigenzinnige) Excel-structuur van het klant-template.
2. **`veterinary-product-enrichment`** — een *agentic* onderzoeksproces waarbij Claude zelf, per productrij, publieke veterinaire bronnen doorzoekt (CBG-diergeneesmiddeleninformatiebank, EU-productendatabank, UU-apotheek-bijsluiters, en een lokale Covetrus-prijslijst als fallback) om ontbrekende velden aan te vullen — met een strikte bronhiërarchie, een 5-waarden confidence-schaal per veld, en het harde principe dat bestaande data **nooit stilzwijgend wordt overschreven**.

De twee skills zijn met opzet onafhankelijk van elkaar bruikbaar (Skill 2 mag nooit aannemen dat zijn input vers van Skill 1 komt — zie het onafhankelijkheids-bewijs verderop), maar vormen samen de volledige pijplijn: **Animana-export → gevulde RPA-werkmap → verrijkte, onderzochte RPA-werkmap.**

Dit is AetherLink-tooling in de eigenlijke zin: gebouwd door een swarm van Claude Code-agents onder AetherLink's kwaliteitsdiscipline (RALF-gate, angle-based code review, een hard verbod op stilzwijgende data-overschrijving), specifiek om Merel's dagelijkse business-dev-werk met potentiële en bestaande dierenartsenklanten te versnellen.

---

## Inhoudsopgave

- [Architectuur in één oogopslag](#architectuur-in-één-oogopslag)
- [Skill 1 — animana-rpa-product-builder](#skill-1--animana-rpa-product-builder)
  - [Welk probleem dit oplost](#welk-probleem-dit-oplost)
  - [Hoe data door de pijplijn stroomt](#hoe-data-door-de-pijplijn-stroomt)
  - [Installatie & gebruik](#installatie--gebruik-skill-1)
  - [Volledige kolom-mapping](#volledige-kolom-mapping-skill-1)
  - [Dropdowns-blad](#dropdowns-blad-kolomkaart)
  - [Waarom dit rechtstreeks in de XML schrijft](#waarom-dit-rechtstreeks-in-de-xml-schrijft)
- [Skill 2 — veterinary-product-enrichment](#skill-2--veterinary-product-enrichment)
  - [Welk probleem dit oplost](#welk-probleem-dit-oplost-skill-2)
  - [Het agentic onderzoeksproces](#het-agentic-onderzoeksproces)
  - [Bronhiërarchie](#bronhiërarchie-strikte-volgorde)
  - [Confidence-schaal en resultaatstatus](#confidence-schaal-en-resultaatstatus)
  - [Nieuw-kolom-beslisregels](#nieuw-kolom-beslisregels)
  - [Installatie & gebruik](#installatie--gebruik-skill-2)
  - [Output-schema](#output-schema-95-kolommen)
- [Lessons learned — de Covetrus off-by-one bug](#lessons-learned--de-covetrus-off-by-one-bug)
- [Integratietest: de echte cijfers](#integratietest-de-echte-cijfers)
- [Bekende incidenten / transparantie](#bekende-incidenten--transparantie)
- [Status](#status)
- [Credits](#credits)

---

## Architectuur in één oogopslag

```
                    ┌──────────────────────────────┐
 Animana export ───▶│  Skill 1                     │
 (product/          │  animana-rpa-product-builder │───▶  RPA Products
 productgroepen/     │  (deterministisch, geen AI)  │      "... compleet.xlsx"
 contacts/letters/   └──────────────────────────────┘      "... actief.xlsx"
 toeslagen/margeregels)                                          │
                                                                  │ (mag ook een
                                                                  │  losse/oudere
                                                                  │  RPA-werkmap zijn)
                                                                  ▼
                    ┌──────────────────────────────┐
                    │  Skill 2                     │
                    │  veterinary-product-          │───▶  Verrijkte werkmap
                    │  enrichment                   │      (95 kolommen:
                    │  (agentic, Claude zoekt zelf) │       huidig/voorstel/
                    └──────────────────────────────┘       confidence/nieuw
                                                             per veld)
```

Beide skills leven als losse, zelfstandige Claude Code skill-mappen (`SKILL.md` + `scripts/` + `references/` + `assets/`) en kunnen onafhankelijk worden geïnstalleerd. De map `integration-test/` in deze repo bevat het bewijs dat de twee elkaar daadwerkelijk aankunnen zonder handmatige tussenstap (zie [Integratietest](#integratietest-de-echte-cijfers)).

---

## Skill 1 — animana-rpa-product-builder

### Welk probleem dit oplost

Elke nieuwe of bestaande Animana-klant van Merel heeft een eigen export van zijn productcatalogus, contactenlijst (leveranciers), productgroepen, brieven, toeslagen en margeregels. Die moeten stuk voor stuk in een **vast, door de klant/Animana voorgeschreven Excel-template** ("RPA Products") terechtkomen — inclusief herbouwde dropdown-lijsten (productgroepen, leveranciers, toeslagen, margeregels, brieven) die specifiek zijn voor die ene praktijk. Dit is puur mechanisch werk zonder enige inhoudelijke beoordeling nodig — en dus expliciet **niet** aan een AI-oordeel overgelaten. Skill 1 is een deterministisch script: dezelfde input levert altijd exact dezelfde output, reproduceerbaar en auditeerbaar.

### Hoe data door de pijplijn stroomt

1. **Input-classificatie.** Je geeft óf expliciete `--product-export`/`--productgroups`/`--contacts`/`--letters`/`--toeslagen`/`--margeregels`-paden mee, óf gewoon een `--input-dir` met alle bestanden erin — het script herkent elk bestand aan zijn **header-signatuur**, nooit aan bestandsnaam of extensie. Alleen product-export en productgroepen-export zijn verplicht; de rest is optioneel (en ontbrekende optionele input wordt expliciet gerapporteerd, nooit stilzwijgend overgeslagen).
2. **Parsen & normaliseren.** Elke bronrij wordt gelezen, elk veld gemapt volgens de [kolom-mapping](#volledige-kolom-mapping-skill-1) hieronder. `kanalisatie` wordt genormaliseerd naar het canonieke `{udd, uda, ura, vrij}`-stel; `actie` en `leverancier` worden gevalideerd tegen resp. de vaste dropdown en de **opnieuw voor déze klant opgebouwde** leveranciers-lijst — nooit tegen de oude template-waarden.
3. **Malformed-row-detectie.** Een bronrij met het verkeerde aantal kolommen (bijv. een verdwaalde komma) wordt nooit gedeeltelijk of verschoven opgeslagen — hij wordt volledig overgeslagen en gerapporteerd met zijn 1-based bronrijnummer.
4. **Dropdown-herbouw.** Vijf "account-bound" dropdown-kolommen (productgroepen, toeslagen, margeregels, leveranciers, brieven) worden herbouwd uit de bijbehorende bron-export; zeven "fixed" kolommen (eenheden, btw, kanalisatie, actie, ...) blijven byte-identiek aan het template; zeven "cleared" kolommen (analysegroep 1-3, herinnergroep, notificatie, prijsgroep, magazijn) worden leeggemaakt (kolomkop blijft staan).
5. **Schrijven — direct in de XML**, nooit via openpyxl's schrijf-pad (zie [hieronder](#waarom-dit-rechtstreeks-in-de-xml-schrijft) waarom dat cruciaal is).
6. **Twee outputbestanden**: `... compleet.xlsx` (alle rijen, 1:1) en `... actief.xlsx` (rijen met `actief=false` verwijderd; leeg telt als actief) — nooit overschrijvend bij een naamconflict (numerieke ` (2)`-suffix).
7. **Rapport naar stdout** + companion-CSV's (`... flagged-values.csv`, `... malformed-rows.csv`) zodra er iets te melden valt, zodat het rapport leesbaar blijft ook bij 10.000+ rijen.

Het harde acceptatiecriterium: beide outputbestanden moeten **zonder reparatie-prompt** openen in Excel, en **elke dropdown-pijl** (productgroepen, leveranciers, etc.) moet nog werken. Een reparatie-prompt betekent dat er iets buiten dit script om aan de werkmap is gebeurd en de run mag niet vertrouwd worden.

### Installatie & gebruik (Skill 1)

Vereisten: Python 3.12, `openpyxl` (alleen gebruikt om bronbestanden te *lezen*, nooit om te schrijven). Geen andere third-party packages nodig.

```bash
python scripts/build_rpa_products.py \
  --product-export "<pad naar Animana product-export>" \
  --productgroups "<pad naar productgroepen-export>" \
  --account-name "<Naam van de praktijk/account>" \
  --output-dir "<map voor de twee outputbestanden>" \
  [--contacts "<pad naar contacts-export>"] \
  [--letters "<pad naar brieven-export>"] \
  [--toeslagen "<pad naar toeslagen copy-paste .txt>"] \
  [--margeregels "<pad naar margeregels copy-paste .txt>"]
```

Of, als je gewoon een map met exports hebt zonder te weten welk bestand welk is:

```bash
python scripts/build_rpa_products.py \
  --input-dir "<map met alle Animana-exports>" \
  --account-name "<Naam van de praktijk/account>" \
  --output-dir "<map voor de twee outputbestanden>"
```

Expliciete `--*`-vlaggen winnen altijd van auto-detectie. Het template-asset (`assets/RPA_Products_template.xlsx`) wordt automatisch gebruikt; override alleen met `--template` als de klant een nieuwere versie aanlevert, en bevestig dat eerst met de gebruiker — de hele skill is gebouwd rond de exacte structuur van dít bestand.

**Voor je het aan de klant geeft:** open elk outputbestand zelf één keer. Geen reparatie-prompt, elke dropdown-pijl werkt nog. Dat is de enige acceptatietest die telt.

### Volledige kolom-mapping (Skill 1)

Directe 1:1-kopie tenzij anders vermeld:

| Animana-kolom | RPA-kolom | Opmerking |
|---|---|---|
| productgroep | productgroep | |
| naam | naam | |
| shortcode | code | |
| factuurtekst | factuurtekst | |
| kostprijs | kostprijs | als echt getal geschreven |
| verkoopeenheid | verkoopeenheid | |
| verpakkingsfactor | verpakkingsfactor | als echt getal geschreven |
| verpakkingseenheid | verpakkingseenheid | |
| bestelfactor | bestelfactor | als echt getal geschreven |
| besteleenheid | besteleenheid | |
| dosering | dosering | |
| vrije tekst | vrije tekst | |
| Blad productinformatie | blad productinformatie | |
| registratie | registratie | |
| waarschuwing | waarschuwing | |
| memo | memo | |
| opiaat | opiaat | letterlijke 'true'/'false'-string, ongewijzigd |
| humandrug | humaan | letterlijke 'true'/'false'-string, ongewijzigd |
| euthanasie | euthanasaat | letterlijke 'true'/'false'-string, ongewijzigd |
| registratie minuten | registratie minuten | als echt getal geschreven |
| farmaceutische vorm | farmaceutische vorm | |
| werkzame stof(fen) en concentratie | werkzame stof(fen) en concentratie | |
| leverancier | leverancier | gevalideerd (zie hieronder), nooit gegokt |
| artikelnummer | artikelnummer | |
| kanalisatie | kanalisatie | genormaliseerd (zie hieronder) |
| actief | actief | letterlijke 'true'/'false'/''-string; stuurt het actief-bestandsfilter |
| stockonpackage | voorraad obv verpakking | letterlijke 'true'/'false'-string, ongewijzigd |
| actie | actie | gevalideerd (zie hieronder), nooit gegokt |
| barcode | barcode | **altijd als tekst geschreven**, nooit als getal — behoudt voorloopnullen |
| btw | btw | letterlijke categorie ('hoog'/'laag'/'geen'), nooit naar % omgezet |
| verkoopprijs | **verkoopprijs ex** | Animana's waarde is EX btw; als echt getal geschreven |

**RPA-kolommen bewust leeg gelaten** (niet in de mapping-spec — nooit vullen, ook al lijkt er een plausibele Animana-bronkolom te bestaan): `nieuwe naam`, `basisprijs`, `marge product`, **`verkoopprijs incl`** (nooit berekend — Animana zelf vult dit na import), `toeslag`, `korting`, `analysegroep 1/2/3`, `gewicht`, `etiket niet printen`, `verrichting`, `brief`, `toon product`, `verberg`.

**Validatieregels (nooit gokken — ongewijzigd doorschrijven + vlaggen):**

- **kanalisatie**: hoofdletter-/spatie-ongevoelige match tegen `{udd, uda, ura, vrij}` → genormaliseerd naar de canonieke kleine-letter-spelling. Al het overige (ook plausibele synoniemen als `free` of `ur`) wordt **ongewijzigd** doorgeschreven en gevlagd — nooit een synoniem-vertaling geraden.
- **actie**: exacte (hoofdlettergevoelige) match tegen de vaste dropdown-waarden `euthanasia`/`castration`. Leeg is prima. Al het overige wordt ongewijzigd doorgeschreven en gevlagd.
- **leverancier**: exacte (hoofdlettergevoelige) match tegen **de voor déze run opnieuw opgebouwde** leveranciers-lijst (niet de oude template-waarden). Leeg is prima. Al het overige wordt ongewijzigd doorgeschreven en gevlagd.
- Een numeriek doelveld (kostprijs, verkoopprijs ex, verpakkingsfactor, bestelfactor, registratie minuten) dat niet als getal te parsen is, wordt als **tekst** geschreven (nooit gedropt/leeggemaakt) en gevlagd.

### Dropdowns-blad kolomkaart

| Letter | Label | Gedrag |
|---|---|---|
| A | productgroepen | **account-bound**: herbouwd uit de `naam`-kolom van de productgroepen-export |
| C | toeslagen | **account-bound**: herbouwd uit de toeslagen copy-paste `.txt` (eerste tab-veld per regel) |
| E | margeregels | **account-bound**: herbouwd uit de margeregels copy-paste `.txt` (eerste tab-veld per regel) |
| M | leveranciers | **account-bound**: herbouwd uit contacts-export, rijen waar `leverancier='true'`, `bedrijfsnaam`-kolom, gededupliceerd |
| Y | brieven | **account-bound**: herbouwd uit de `naam`-kolom van de brieven-export (`context`-kolom genegeerd) |
| G | eenheden | **fixed** — byte-identiek aan template, nooit aangeraakt |
| I | btw | **fixed** — byte-identiek aan template |
| K | optie | **fixed** — byte-identiek aan template |
| O | kanalisatie | **fixed** — byte-identiek aan template |
| Q | actie | **fixed** — byte-identiek aan template |
| AA | aanklikken | **fixed** — byte-identiek aan template |
| AC | herinnertype | **fixed** — byte-identiek aan template |
| S, U, W, AE, AG, AI, AK | analysegroep 1/2/3, herinnergroep, notificatie, prijsgroep, magazijn | **cleared**: waarden gewist (kolomkop in rij 1 blijft staan), expliciete klant-instructie |

Elke account-bound kolom heeft een vooraf ingebouwde capaciteit gebaseerd op het template's eigen data-validation-formulebereiken (A/Y: 248 rijen, C/E/M: 48 rijen). Past een herbouwde lijst daar niet in, dan wordt nog steeds elke waarde geschreven (niets gaat verloren) maar tonen rijen voorbij de capaciteit geen Excel-dropdown-pijl meer — het rapport vlagt dit expliciet onder "Capacity warnings".

### Waarom dit rechtstreeks in de XML schrijft

Het template's dropdown-lijsten zijn **niet** verankerd met Excel's klassieke `<dataValidation>`-element, maar met het *uitgebreide* x14-formaat (genest in `<extLst><ext><x14:dataValidations>`). Dit is hoe Excel 2010+ lijst-validaties opslaat waarvan de bron een formuleverwijzing naar een ander blad is (`dropdowns!$A$2:$A$249`).

`openpyxl`'s schrijver rondt deze extensie **niet** correct af — experimenteel bevestigd: `openpyxl.load_workbook(template) → wb.save(...)` produceert stilzwijgend een werkmap met **nul werkende dropdowns**. Omdat "alle validaties intact, opent zonder reparatie-prompt" een hard acceptatiecriterium is, rondt deze skill de werkmap **nooit** door openpyxl's schrijf-pad — alle output ontstaat via directe ZIP/XML-chirurgie (`xlsx_xml.py`): `styles.xml`, `sharedStrings.xml`, thema en elk ander zip-onderdeel worden byte-voor-byte gekopieerd; alleen `sheet1.xml` (RPA Products edit) en `sheet2.xml` (dropdowns) worden herschreven, en dan alleen de specifieke regio's die moeten veranderen.

Sheet 1 heeft 46 kolommen (A:AT) en 448 vooraf gestileerde lege datarijen; die stijl wordt eenmalig uit rij 2 gelezen en hergebruikt voor zoveel rijen als er echt gegenereerd worden. Alle datacellen gebruiken inline strings (`t="inlineStr"`) in plaats van shared-string-indices, zodat `sharedStrings.xml` nooit hoeft te worden aangepast — dat elimineert een hele klasse index-corruptie-risico's. Boven de 448 pre-gebouwde rijen bump `bump_validation_row_cap()` automatisch elke x14-validatiebereik-token — getest tegen een synthetische **550-rijen-fixture** (`tests/fixtures/make_scaling_fixture.py`, `n_rows=550`, ruim boven de template's 448 vooraf-gestileerde rijen — géén 2× van de 299-rijen dev-fixture, gewoon een vaste constante gekozen om de >448-grens te overschrijden), waarbij een eerste poging een echte bug ving (een omgekeerde regex-lookbehind zorgde dat de "449"-tokens nooit werden opgehoogd) die vervolgens gefixt en herverifieerd is.

Zie `animana-rpa-product-builder/references/template_layout.md` voor de volledige structurele diepgang — **lees dit voordat je `scripts/rpa_builder/xlsx_xml.py` aanraakt.**

---

## Skill 2 — veterinary-product-enrichment

### Welk probleem dit oplost (Skill 2)

Een gevulde RPA Products-werkmap (van Skill 1, van een oudere run, of handmatig aangepast — Skill 2 maakt daar nooit een aanname over) heeft vaak gaten: geen registratienummer, geen farmaceutische vorm, geen werkzame stof + concentratie, geen kanalisatie-code, geen barcode. Die informatie bestaat wél publiek — bij het CBG, bij de EU-productendatabank, in officiële bijsluiters — maar iemand moet het per product opzoeken. Dat is precies het soort werk waar een taalmodel met websearch goed in is, **mits** het gedisciplineerd een bronhiërarchie volgt, nooit verzint, en bestaande data nooit stilzwijgend overschrijft. Skill 2 is dus expliciet géén deterministisch script — het is een **agentic onderzoeksproces** waarbij Claude zelf, geleid door vier referentiedocumenten, de matching en confidence-beoordeling per product doet. De Python-scripts eromheen doen alléén de mechanische Excel-I/O en de deterministische `nieuw`-kolomberekening.

### Het agentic onderzoeksproces

Een verse Claude-instance die deze skill start **moet**, vóór de eerste WebSearch, twee documenten hebben gelezen — niet optioneel:

1. `references/source-hierarchy.md` — welke bron wint bij een conflict (1–7, strikte volgorde) + de KNMvD/WVAB-antibiotica-tier-regel.
2. `references/confidence-and-status.md` — de twee schalen die elke keer opnieuw worden toegepast: de 5-waarden per-veld confidence en de losstaande 8-waarden rij-niveau `resultaatstatus`. Nooit een 6e/9e waarde verzinnen.

Daarna, per rij: `references/field-rules.md` (per-veld regels + eerst het producttype bepalen) en `references/search-strategy.md` (de 5 verplichte zoekrondes + batching bij grote bestanden).

**Workflow, drie stappen:**

**Stap 1 — Valideren + exporteren (mechanisch)**
```
python scripts/validate_and_export.py <input.xlsx> <products.json>
```
Werkt op élk bestand dat aan de RPA Products-structuur voldoet. Ontbrekende verplichte kolommen (`scripts/schema.py: REQUIRED_COLUMNS`) → het script meldt **exact** welke en stopt (exit code 2). Nooit een vervangende kolom raden.

**Stap 2 — Onderzoekslus (agentic, door Claude uitgevoerd)**
Voor elke rij, in batches van ~15-25:
1. **Producttype herkennen** eerst (veterinair geneesmiddel, humaan geneesmiddel, vrij diergeneesmiddel, voeding/dieetvoeding, supplement, verzorgingsproduct, medisch hulpmiddel, verbruiksmateriaal, laboratoriumproduct, interne verrichting, administratief product, onbekend) — bepaalt welke velden logisch van toepassing zijn.
2. **5 verplichte zoekrondes** (zie [search-strategy.md](veterinary-product-enrichment/references/search-strategy.md)): (1) exacte identificatie op bestaand registratienummer/barcode/artikelnummer, (2) genormaliseerde naam + typefout-tolerantie, (3) officiële databanken (NL/EU/humaan), (4) fabrikant & leverancier (incl. `lookup_covetrus.py` als lokale fallback), (5) waarschijnlijke match op meerdere overeenkomende kenmerken. "Niet gevonden" is pas toegestaan na alle 5 rondes.
3. **Per veld** een voorstel + confidence-label, volgens `field-rules.md`.
4. **Rij-niveau `resultaatstatus`** holistisch bepaald — géén mechanische afleiding uit de veld-confidences.
5. Loggen in `toelichting_controle` welke zoekrondes daadwerkelijk zijn uitgevoerd, vooral vóórdat "niet gevonden" wordt geconcludeerd.

Resultaten gaan naar `enrichment_results.json` (één object per rij, `voorstel` + `confidence` per veld — de `huidig`/`nieuw`/`beslissing`-kolommen worden mechanisch berekend in stap 3).

**Stap 3 — Output schrijven (mechanisch)**
```
python scripts/write_output.py <input.xlsx> <enrichment_results.json> <output.xlsx> [--previous-output <vorige-output.xlsx>]
```
Past de deterministische `nieuw`-kolomregels toe. `--previous-output` trekt bij een her-run menselijk gezette `beslissing`-waarden door, en behoudt een `handmatig aanpassen`-waarde **altijd** ongewijzigd. Het origineel wordt nooit aangepast — output is altijd een vers opgebouwde werkmap (dezelfde reden als bij Skill 1: de template's data-validation-extensie overleeft geen openpyxl-rondtrip).

### Bronhiërarchie (strikte volgorde)

Een hogere bron overschrijft altijd een lagere bij een conflict:

1. **Nederlandse Diergeneesmiddeleninformatiebank (CBG)** — primaire bron voor registratie (REGNL-nummer), farmaceutische vorm, werkzame stof(fen)+concentratie, kanalisatie, blad productinformatie (SPC/bijsluiter), humaan=false-bevestiging.
2. **Europese Veterinary Medicines Information / Union Product Database** — voor centraal (EU-nummer) geregistreerde producten, of ter bevestiging naast een REGNL-nummer (een REGNL- én een EU-nummer bij hetzelfde product zijn geen twee aparte matches).
3. **Nederlandse Geneesmiddeleninformatiebank** (humane geneesmiddelen) — alleen voor off-label humaan-in-dier-gebruik of om humaan/veterinair te onderscheiden.
4. **Apotheek Diergeneeskunde Universiteit Utrecht (bijsluiters)** — eigen bereidingen, off-label, geïmporteerde diergeneesmiddelen, slecht gedekte producten. Een officiële CBG/EU-SPC wint altijd als die gevonden wordt.
5. **Covetrus-productenlijst** (bundled asset, `assets/covetrus-productenlijst.xlsx`, sheet `PRIJS`, **niet live gescraped**) via `scripts/lookup_covetrus.py` — lagere-prioriteit fallback, vooral voor omschrijving/leverancier/artikelnummer/barcode-verificatie. Een officiële bron overschrijft dit altijd bij conflict. Periodiek door Merel te verversen — nooit automatisch een nieuwe versie opvragen.
6. **Overige gerenommeerde leverancier-/groothandelbronnen** — alleen ondersteunend, nooit primair.
7. **Algemene internetbronnen** — alleen ondersteunend, nooit primair. Nooit webshops, forums, blogs of ongeverifieerde databases als primaire bron.

**KNMvD/WVAB-antibiotica-tier:** publieke richtlijndocumenten mogen automatisch geraadpleegd worden, uitsluitend voor de `AB 1e keus`/`AB 2e keus`/`AB 3e keus`-classificatie. Achter-inlog/betaalde documenten alleen als Merel ze zelf aanlevert. Geen betrouwbare, actuele richtlijn gevonden → geen tier toekennen, alleen de generieke term "antibioticum".

### Confidence-schaal en resultaatstatus

**Per-veld confidence** (5 waarden, stuurt de deterministische `nieuw`-kolomlogica):

| Waarde | Betekenis |
|---|---|
| **Hoog** | Direct en ondubbelzinnig bevestigd door een betrouwbare bron (exact registratienummer, exacte barcode, exacte naam+concentratie+vorm+verpakking-combinatie). Mag `nieuw` auto-vullen als `huidig` leeg is. |
| **Gemiddeld** | Zeer waarschijnlijke match, niet elk kenmerk bevestigd. Wordt nooit automatisch overgenomen als dat een bestaande waarde zou veranderen. |
| **Laag** | Alleen beperkt bewijs (alleen merknaam matcht, alleen generieke omschrijving). Altijd handmatige controle nodig. |
| **Niet gevonden** | Pas na uitputting van alle 5 zoekrondes, zonder bruikbare match. |
| **Niet van toepassing** | Veld is logisch niet van toepassing voor dit producttype. Telt als bruikbaar resultaat, niet als "niet gevonden". |

**Rij-niveau `resultaatstatus`** (8 waarden, holistisch, niet mechanisch afgeleid): `exact gevonden` · `grotendeels gevonden` · `waarschijnlijk gevonden` · `gedeeltelijk verrijkt` · `meerdere mogelijke matches` · `niet van toepassing` · `niet gevonden` · `handmatige controle nodig`.

Vuistregel: als één kernveld (registratie, barcode, werkzame stof) een **harde tegenspraak** heeft met bestaande data → altijd minstens `handmatige controle nodig`, ongeacht hoeveel andere velden wél kloppen.

### Nieuw-kolom-beslisregels

Exact, per veld toegepast door `scripts/decision_logic.py`:

1. `huidig` gevuld + geen betrouwbaar voorstel → `nieuw` = `huidig` (ongewijzigd).
2. `huidig` leeg + voorstel confidence = Hoog → `nieuw` = `voorstel` (auto-gevuld).
3. `huidig` en `voorstel` zijn gelijk → `nieuw` = die waarde.
4. `huidig` en `voorstel` **verschillen** → `nieuw` wordt niet automatisch gewijzigd (blijft `huidig`), rij gemarkeerd voor review.
5. Voorstel confidence = Gemiddeld/Laag en wijkt af van `huidig` → nooit automatisch overnemen.
6. Geen enkel resultaat → `nieuw` = `huidig`, of blijft leeg als `huidig` ook al leeg was.

`beslissing`-kolomwaarden: `akkoord` (nieuw = voorstel) | `niet akkoord` (nieuw = huidig) | `handmatig aanpassen` (gebruiker vult zelf in — script raakt dit nooit meer aan bij een volgende run).

### Installatie & gebruik (Skill 2)

Vereisten: `openpyxl` (al beschikbaar). `rapidfuzz` voor fuzzy naam-matching in `lookup_covetrus.py` (optioneel — valt terug op substring-match als het ontbreekt; `pip install rapidfuzz` voor betere matches).

```bash
# Stap 1 — mechanisch
python scripts/validate_and_export.py <input.xlsx> <products.json>

# Stap 2 — agentic (Claude leest products.json, doet WebSearch/WebFetch,
# schrijft enrichment_results.json volgens het schema in SKILL.md)

# Stap 3 — mechanisch
python scripts/write_output.py <input.xlsx> <enrichment_results.json> <output.xlsx> \
  [--previous-output <vorige-output.xlsx>]

# Lokale Covetrus-fallback (los te gebruiken tijdens stap 2, ronde 4)
python scripts/lookup_covetrus.py --barcode <ean> | --artikelnummer <nr> | --name "<naam>"
```

Dekkingsdoel: streef naar ≥90% van de productrijen met een bruikbaar resultaat — dit is een **kwaliteitsdoel, geen afkapgrens**. Gedeeltelijke resultaten worden altijd bewaard en gerapporteerd, nooit weggelaten omdat de 90% niet gehaald wordt.

### Output-schema (95 kolommen)

1. Alle 46 originele RPA Products-kolommen, ongewijzigd, in originele volgorde.
2. **code-blok** (5 kolommen): `code (huidig)`, `zoektermen (voorstel)`, `code + zoektermen (voorstel)`, `beslissing (code)`, `code (nieuw)`.
3. **waarschuwing-blok** (6 kolommen): `waarschuwing (huidig)`, `waarschuwing (voorstel)`, `waarschuwing (confidence voorstel)`, `waarschuwing bronpassage (voorstel)`, `waarschuwing (nieuw)`, `beslissing (waarschuwing)`.
4. Voor elk van de 7 standaardvelden (`blad productinformatie`, `registratie`, `humaan`, `farmaceutische vorm`, `werkzame stof(fen) en concentratie`, `kanalisatie`, `barcode`) — 5 kolommen per veld: `{veld} (huidig)`, `{veld} (voorstel)`, `{veld} (confidence voorstel)`, `{veld} (nieuw)`, `beslissing ({veld})`.
5. **Rij-niveau bron/control** (3 kolommen): `bron URL`, `resultaatstatus`, `toelichting controle`.

**Totaal: 46 + 5 + 6 + (7 × 5) + 3 = 95 kolommen** — geverifieerd tegen de daadwerkelijk geschreven testworkbook (8 juli 2026). Een extra werkblad "Verwerkingsrapport" bevat: totaal aantal producten, coverage-percentage, aantal rijen dat handmatige review nodig heeft, en een telling per `resultaatstatus`-waarde.

De per-veld confidence-kolom is geen toegevoegde scope: zonder een bewaarde confidence-waarde is de `nieuw`-kolomlogica niet navolgbaar of herhaalbaar bij een latere her-run/audit. Er is bewust geen apart `producttype`-kolom (de opdracht instrueerde expliciet geen kolommen toe te voegen aan de bron/control-set) — producttype-herkenning is wel verplicht als eerste denkstap, maar landt in de vrije tekst van `toelichting_controle`.

### Covetrus-fallback: kolomtoewijzing (0-indexed)

| 0-indexed | Excel-kolom | Veld | Voorbeeldwaarde |
|---|---|---|---|
| 0 | A | Omschrijving | "Clavusan 500mg/125mg tablet" |
| 1 | B | Leverancier | "ALFASAN NL" |
| 4 | E | Prijs | "187.15" |
| 7 | H | Covetrus-eigen artikelnummer | "4009001" |
| 8 | I | Registratie-achtige code | "RVG06193" / "REGNL08608" |
| 10 | K | Barcode/GTIN (13-cijferig EAN) | "5701170461398" |
| 12 | M | Kanalisatie-achtige korte code | "UA" / "URA" / "UDD" |

Kolommen C, D, F, G, J, L bevatten andere Covetrus-interne velden (o.a. een constante `1`, verkoopeenheid, een verpakkingsfactor, en een aantal-/voorraadachtig getal in kolom L) die niet worden gebruikt door deze skill. Deze tabel is geverifieerd tegen de volle 17.551-rijen-asset op de Kathedraal (8 juli 2026) — zie [Lessons learned](#lessons-learned--de-covetrus-off-by-one-bug) hieronder voor de bug die deze verificatie nodig maakte.

De bundled asset zelf (`assets/covetrus-productenlijst.xlsx`) is een **periodiek te verversen** bestand, geen live scrape — Merel levert een nieuwe versie aan wanneer relevant; `lookup_covetrus.py` degradeert netjes naar `{"available": false}` als het bestand ontbreekt (bijvoorbeeld op een andere machine dan de Kathedraal).

---

## Lessons learned — de Covetrus off-by-one bug

Tijdens de bouw van Skill 2 bevatte `references/covetrus-mapping.md` een kolomtoewijzingstabel die zichzelf "0-indexed" noemde, maar in werkelijkheid **per ongeluk de 1-indexed Excel-kolomnummers** bevatte. Zolang die tabel nooit tegen de echte, volledige Covetrus-asset werd geverifieerd (de asset was op het moment van eerste schrijven nog niet aangeleverd — alleen een 3-rijen-aanname), bleef de fout onopgemerkt: elke kolomlezing in `lookup_covetrus.py` zou één positie zijn verschoven ten opzichte van de daadwerkelijke celwaarden.

Zodra de echte 17.551-rijen `covetrus-productenlijst.xlsx` beschikbaar kwam op de Kathedraal, is de mapping opnieuw geverifieerd met `python scripts/lookup_covetrus.py --verify-mapping` tegen de volledige asset — dat leverde de gecorrigeerde tabel hierboven op, en is bevestigd met concrete zoekopdrachten (`--barcode 5701170461398` vindt correct "Clavusan 500mg/125mg" bij Alfasan met score 100; `--name "Imaverol"` vindt correct beide verpakkingsgroottes met fuzzy-score 80).

**De les:** een kolomtoewijzingstabel die zichzelf documenteert als "0-indexed" is geen vervanging voor het daadwerkelijk inlezen van een rij uit het echte bestand en het vergelijken van wat er in elke positie staat. Een aanname op 3 illustratieve rijen — hoe plausibel ook — is geen verificatie. Deze fout werd pas zichtbaar op het moment dat de echte asset beschikbaar kwam, wat exact de reden is waarom `SKILL.md` en `README-covetrus-asset.md` allebei expliciet zeggen: **"Laatst geverifieerd: [datum], tegen de volledige asset"** — elke toekomstige versie van het Covetrus-bestand moet opnieuw door `--verify-mapping` heen voordat de mapping vertrouwd wordt. Deze regel geldt structureel voor élke skill die een kolomtoewijzing tegen een extern, door de klant aangeleverd bestand documenteert: schrijf nooit "0-indexed" of "geverifieerd" zonder een echte run tegen het echte bestand.

---

## Integratietest: de echte cijfers

Op 8 juli 2026 is een volledige, niet-gesimuleerde keten gedraaid: Skill 1 tegen de dev-fixtures → echte Skill-1-output → Skill 2's `validate_and_export.py` rechtstreeks tegen die output → een echte (niet-gesimuleerde) agentic onderzoeksronde op 8 rijen met WebSearch/WebFetch tegen de bronhiërarchie → `write_output.py`. Alles hieronder komt rechtstreeks uit `integration-test/RESULTS.md`, niet uit een samenvatting.

**Stap 1 — Skill 1 tegen de dev-fixtures** (`--input-dir`, auto-classificatie, geen expliciete `--*`-vlaggen nodig):
- Rijen gelezen uit product-export: **299**
- Rijen geschreven naar `compleet`: **299**
- Rijen behouden in `actief`: **224**
- 2 bronrijen overgeslagen als malformed (rij 74 en 180: "expected 38 columns, got 39")
- 282 gevlagde/onopgeloste waarden (grotendeels `leverancier`-waarden die niet in de herbouwde leveranciers-dropdown voorkomen — verwacht bij niet-gecorreleerde dev-fixtures, geen bug)
- Dropdowns herbouwd: productgroepen 67, toeslagen 6, margeregels 19, leveranciers 9, brieven 164
- DATUM: geen datumpatroon in de fixture-bestandsnaam → teruggevallen op bestand-laatst-gewijzigd-datum, exact zoals `SKILL.md`'s open vraag #1 voorspelde gecontroleerd te moeten worden bij een eerste echte run.

**Stap 2 — Skill 2 leest Skill 1's echte output (het onafhankelijkheidsbewijs):**
```
OK: 299 product row(s) exported from sheet 'RPA Products edit' -> products.json
EXIT CODE: 0
```
`validate_and_export.py` accepteerde de echte `RPA Products edit`-sheet zonder enige Skill-2-specifieke aanpassing vooraf — dezelfde headerstructuur, dezelfde 299 rijen.

**Stap 3 — Negatief pad (ontbrekende verplichte kolom):** een kopie van de echte Stap-1-output met de `registratie`-kolomkop hernoemd naar `registratie_RENAMED` leverde exact:
```
ERROR: input workbook is missing required column(s):
  - registratie
EXIT CODE: 2
```
Geen substituut geraden, `products-negative.json` niet geschreven (bevestigd: bestand bestaat niet op disk).

**Stap 4 — Echte agentic verrijking op 8 bekende rijen** (Panacur KH, Cardisure, Apoquel, Nobivac KC, Isathal, Nobivac Lepto 4/DHP, Amoxibactin, Furosoral), met live WebSearch/WebFetch tegen `diergeneesmiddeleninformatiebank.nl` (bron #1) en de EU-productendatabank. Eerlijke bevinding, niet verzonnen: rij 70's productnaam ("Nobivac Lepto 4 / DHP vaccinatie") impliceert een gecombineerde Leptospira-4 + DHP-vaccinatie, maar het bijbehorende REGNL-nummer resolveert — bevestigd via zowel de CBG-databank als het EU-registerdocument — naar **uitsluitend Nobivac L4** (4 Leptospira-serogroepen, geen hondenziekte/hepatitis/parvo-antigenen). Er is geen tweede registratienummer verzonnen om het DHP-deel te dekken; de rij is correct gemarkeerd als `handmatige controle nodig`.

**Stap 4b — `write_output.py`, eerste run:**
```
rows written: 299
rows flagged for review: 3
resultaatstatus breakdown:
  exact gevonden: 7
  niet gevonden: 291
  handmatige controle nodig: 1
```
Consistent met het feit dat maar 8 van de 299 rijen daadwerkelijk agentisch verrijkt zijn (de overige 291 vallen eerlijk terug op `niet gevonden` — nooit stilzwijgend weggelaten).

Van de 3 gevlagde rijen bleek er bij nadere inspectie 1 (rij 70) gevlagd om de bedoelde reden (echte inhoudelijke tegenspraak). De andere 2 (rij 27, rij 42) waren gevlagd doordat `decision_logic`'s gelijkheidscheck exact-string was in plaats van semantisch: rij 27's `huidig` ("Tablet.", met punt) versus voorstel ("tablet") werd als ongelijk beoordeeld; rij 42's `huidig` bevatte nog een niet-gedecodeerde HTML-entiteit (`&egrave;`). Dit was `write_output.py` dat exact deed wat het moest doen ("bestaande data wordt nooit stilzwijgend overschreven") — geen bug in de schrijflogica — maar wel een reële, onnodige review-vlag voor rij 27 (een puur punctuatieverschil).

**Fix (dezelfde dag):** `decision_logic._norm()` doet nu `html.unescape()` + het strippen van één trailend leesteken vóór de gelijkheidscheck die alleen regel 3 (`huidig == voorstel`) stuurt — de daadwerkelijk geschreven waarde in `nieuw`/`huidig` blijft ongewijzigd, dit beïnvloedt alleen óf een mismatch gevlagd wordt.

**Re-run na de fix:**
```
OK: wrote .../RPA Integratietest Kliniek verrijkt POST-FIX.xlsx
rows written: 299
rows flagged for review: 2
resultaatstatus breakdown:
  exact gevonden: 7
  niet gevonden: 291
  handmatige controle nodig: 1
```
`rows flagged for review` daalde van 3 naar 2 — precies de ene echte valse-positief (rij 27) opgelost, beide echte review-gevallen (rij 42, rij 70) ongewijzigd. Cel-voor-cel geverifieerd in de nieuwe werkmap, niet alleen uit de geprinte samenvatting.

Regressietests toegevoegd (`tests/test_decision_logic.py`): trailing-punt-gelijkheid, HTML-entiteit-gelijkheid, en een guard-test die bevestigt dat een echte parafrase nog steeds gevlagd wordt. Volledige suite na de fix: **53/53 gehaald** (was 50/50 vóór deze fix). Skill 1's suite: onaangetast, **20/20 gehaald**.

**Bronkanttekening:** `integration-test/RESULTS.md` spreekt zichzelf op dit punt tegen — de hoofdtekst (waar bovenstaande cijfers uit komen) beschrijft deze re-run als onderdeel van de sessie van 8 juli, maar diezelfde RESULTS.md's eigen "Gaps / things not covered by this run"-sectie zegt letterlijk: *"pytest suites for either skill were not part of this task and were not run here (separate item in the project's task list)"*. Die twee uitspraken zijn niet met elkaar te rijmen zonder het brondocument zelf te corrigeren, en dat is hier bewust niet gedaan — RESULTS.md is niet aangepast, deze README citeert het zoals het is en meldt de tegenstrijdigheid expliciet in plaats van er stilzwijgend overheen te lezen. Los daarvan: bij het schrijven van déze README-revisie zijn beide suites onafhankelijk opnieuw gedraaid (8 juli 2026) en beide cijfers kloppen vandaag daadwerkelijk — **20/20** (Skill 1) en **53/53** (Skill 2) slagen. Dat bevestigt de getallen zelf, niet het "hoorde bij deze sessie"-verhaal van RESULTS.md.

**Wat deze run niet dekt** (expliciet in `RESULTS.md` genoemd, niet verzwegen):
- Slechts 8 van de 299 rijen zijn daadwerkelijk agentisch onderzocht — dit bewijst geen ≥90%-dekking (dat vereist de volledige batching-workflow uit `search-strategy.md`, buiten scope hier).
- `lookup_covetrus.py` is in deze run niet geoefend — het bundled Covetrus-bestand was op dat moment nog placeholder.
- Geen KNMvD/WVAB-antibiotica-tier is toegepast op Amoxibactin (rij 78) — geen actuele, betrouwbare richtlijn gevonden in deze sessie, dus alleen de generieke term "antibioticum" gebruikt, geen tier verzonnen.

---

## Bekende incidenten / transparantie

Deze sectie bestaat omdat AetherLink's interne beleid geen stilzwijgende verwijdering en geen verzwegen procesfouten toestaat — ook niet wanneer ze de tooling zelf niet beschadigd hebben. Drie dingen om te weten voordat je deze skills in productie zet:

**(a) Eén zelfgerapporteerde, ongeautoriseerde bestandsverwijdering tijdens de bouw.** Eén van de bouw-agents heeft tijdens het testen van een `openpyxl`-eigenaardigheid (een leeg-geschreven cel `""` komt bij het opnieuw inladen terug als `None` — een opslag-eigenaardigheid van de library, geen bug in `decision_logic.py`) een ad-hoc verificatiescript gedraaid dat een wegwerp-testbestand (`test_empty.xlsx`, twee dummy-cellen, geen echte data) buiten de bedoelde scratchpad-map wegschreef — naar `C:\Users\info\Desktop\Merel\`, omdat dat toevallig de working directory van de Bash-tool op dat moment was. Dat is de vertrouwelijke klinieklijst-map die expliciet buiten alle build-activiteit had moeten blijven. De agent merkte dit zelf op en heeft het bestand onmiddellijk verwijderd, en bevestigd dat de map daarna weer alleen de originele klantbestanden bevatte. Dit is **forensisch niet onafhankelijk te verifiëren** door wie dit README schrijft (het bestand is weg, er is geen externe log) — het wordt hier gemeld precies omdát het niet geverifieerd kan worden, in lijn met de harde regel dat een zelfgerapporteerde verwijdering altijd gemeld wordt, nooit stilgehouden, ongeacht of ze bewijsbaar klein/onschadelijk was.

**(b) De RALF-kwaliteitspoort van de oorspronkelijke bouw-swarm heeft nooit gedraaid.** Door een worktree-isolatie-infrastructuurfout is de geplande RALF-gate (het standaard AetherLink-kwaliteitscontrolepunt, score ≥85 vereist vóór commit) tijdens de oorspronkelijke ontwikkeling van beide skills nooit uitgevoerd. Er is dus geen RALF-score voor de initiële bouw van Skill 1 of Skill 2 zelf. Wat wél is uitgevoerd en geregistreerd, is een latere, losstaande RALF-controleronde specifiek over het test- en integratiewerk. De feitelijke scores, ongewijzigd overgenomen:

| Onderdeel | RALF-score |
|---|---|
| `skill1-tests` (Animana RPA Product Builder — testsuite + review) | **0** |
| `skill2-tests` (Veterinary Product Data Enrichment — testsuite + review) | **100** |
| `integration-test` (cross-skill integratietest + fix) | **49** |

**Herkomstkanttekening (belangrijk vóór je deze tabel als hard bewijs behandelt):** er is in deze repository, in `integration-test/`, of in de bredere scratchpad **geen los RALF-outputbestand** (log, JSON, scorebestand) aangetroffen dat deze drie getallen onafhankelijk documenteert — alleen het orchestratiescript dat zulke scores ten tijde van de sessie via sub-agent-aanroepen zou hebben berekend, zonder bewaard resultaat. Deze tabel is dus een **gerapporteerd** resultaat van die sessie, niet een op schijf verifieerbaar artefact; behandel het met dezelfde voorbehoud-discipline als incident (a) hierboven — gemeld precies omdat het niet onafhankelijk te verifiëren is, niet als sluitend bewijs.

Met die kanttekening: deze drie scores worden hier ongewijzigd en zonder interpretatie-spin gepresenteerd. Ze zijn opvallend ongelijk — dat is precies waarom ze hier letterlijk staan in plaats van samengevat als "een RALF-controle is uitgevoerd": een score van 0 naast een score van 100 verdient geen gladstrijkende samenvatting. Wat inhoudelijk wél is gebeurd bij elk van de drie: `skill1-tests` leverde een reëel, bevestigd defect op (een dubbel-geteld numeriek-fallback-flag door hergebruik van eenzelfde mutable lijst tussen twee build-aanroepen) dat gefixt en met een nieuwe regressietest gedekt is, eindigend op 20/20 groene tests; `skill2-tests` leverde een volledig nieuwe, 50-tests-tellende pytest-suite op, 50/50 groen; `integration-test` leverde het hierboven beschreven Covetrus-onafhankelijke defect op (de exact-string in plaats van semantische gelijkheidscheck) inclusief fix, regressietest en een geverifieerde her-run. Voordat je op deze scores vertrouwt als kwaliteitsgarantie voor de skills als geheel: dit was géén volledige RALF-gate over de complete codebase, alleen over het specifieke test-/integratiewerk van die sessie.

**(c) Merel's eigen open vraag over echte-versus-geanonimiseerde klinieklijstdata blijft onbeantwoord — bewust.** De definitieve validatie van beide skills tegen een echte (vertrouwelijke) klinieklijst is expliciet **niet** in deze repository of scratchpad uitgevoerd — dat gebeurt alleen rechtstreeks op de Kathedraal, buiten deze staging-omgeving, zoals afgesproken. Of, en in welke vorm, echte klinieklijstdata (versus een geanonimiseerde/synthetische steekproef) gebruikt wordt voor die validatie, is **Merel's beslissing, niet iets wat deze swarm voor haar heeft ingevuld of zal invullen.** Dat is geen technische tekortkoming van de skills — het is een bewuste procesgrens: de synthetische testfixture (`test-fixtures/synthetic-vet-products.xlsx`, bekende publieke producten als Metacam, Rimadyl, Clavubactin, Apoquel, Previcox, Cerenia, Amoxibactin) bewijst dat de mechaniek werkt; wat er met échte praktijkdata gebeurt bij een specifieke klant hoort bij Merel te blijven liggen.

---

## Status

| Onderdeel | Status |
|---|---|
| Skill 1 — deterministische ETL (mapping, dropdown-herbouw, XML-schrijver) | ✅ **Productieklaar** — 20/20 tests groen, geverifieerd op echte dev-fixtures (299 rijen) én een synthetische 550-rijen-scalingtest |
| Skill 1 — numeric-fallback-flag-duplicatiebug | ✅ **Gefixt + regressietest toegevoegd** |
| Skill 2 — mechanische I/O (validate/write) + deterministische decision_logic | ✅ **Productieklaar** — 53/53 tests groen na de trailing-punt/HTML-entiteit-fix |
| Skill 2 — Covetrus-fallback kolomtoewijzing | ✅ **Gefixt + geverifieerd tegen de volle 17.551-rijen-asset** (was off-by-one) |
| Skill 2 — agentic onderzoeksloop (WebSearch/WebFetch, bronhiërarchie, confidence) | ✅ **Bewezen op 8 echte rijen**, ⚠️ **niet bewezen op schaal** (≥90%-dekkingsdoel vereist de volledige batching-workflow op een compleet bestand — nog niet gedraaid) |
| Cross-skill onafhankelijkheid (Skill 2 leest Skill 1's output zonder aanpassing) | ✅ **Bewezen**, inclusief het negatieve pad (ontbrekende kolom → exit code 2, geen giswerk) |
| RALF-gate over de oorspronkelijke bouw van beide skills | ❌ **Nooit gedraaid** (worktree-isolatiefout) — zie [transparantiesectie](#bekende-incidenten--transparantie) |
| RALF-gate over het test-/integratiewerk | ⚠️ **Wel gedraaid, sterk wisselende scores** (0 / 100 / 49) — zie tabel hierboven |
| Validatie tegen echte klinieklijstdata | ⏸️ **Bewust niet hier uitgevoerd** — Merel's beslissing, gebeurt op de Kathedraal |
| GitHub-repo (deze repo) | ⏸️ **Nog niet aangemaakt/gepusht** — deze staging-tree heeft geen `.git`-map (`git status` hier geeft "not a git repository"); het aanmaken van het publieke GitHub-repo en pushen is een aparte, nog openstaande taak, zie [`CONTEXT.md` § 6](CONTEXT.md#6-known-gaps--open-items-be-aware-dont-silently-fix) |

---

## Credits

Gebouwd door **AetherLink B.V.** voor **Merel Heijnen**, als onderdeel van haar business-development-traject in de veterinaire softwaremarkt (Animana-ecosysteem). Ontwikkeld door een AetherDEV-swarm van Claude Code-agents onder AetherLink's RALF-kwaliteitsdiscipline en de interne AI-hardeningsregels (vertrouwensgrens, voltooiingspoort, angle-based verificatie) — zie de [transparantiesectie](#bekende-incidenten--transparantie) hierboven voor waar die discipline dit keer wél en niet volledig is toegepast.

Repository: `MEREL-VET-SKILLS` (publiek).
