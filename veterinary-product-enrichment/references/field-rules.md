# Per-veld verrijkingsregels

Bepaal ALTIJD eerst het producttype (zie onderaan) voordat je per veld
beslist of het van toepassing is.

## code + zoektermen (speciaal veld)

- `zoektermen`: max 3 korte, praktische zoektermen voor Animana-personeel,
  bv. "pijnstiller", "NSAID", "antibioticum". Synoniemen zijn goed.
  **NOOIT**: de werkzame stof, de officiële productnaam, de diersoort, of
  iets dat al in een ander Animana-veld van dit product staat.
- Antibiotica krijgen **"AB 1e keus" / "AB 2e keus" / "AB 3e keus"**
  UITSLUITEND wanneer een actuele, betrouwbare KNMvD/WVAB-richtlijn dat
  bevestigt (zie `source-hierarchy.md`). Geen richtlijn gevonden -> alleen
  "antibioticum" als term, geen tier.
- `code + zoektermen (voorstel)` = huidig `code` + de (max 3) termen,
  spatie-gescheiden, bv. `"METACAM15 pijnstiller NSAID"`. Dit wordt
  mechanisch samengesteld door `decision_logic.compose_code_plus_zoektermen`
  -- Claude hoeft alleen de zoektermen-lijst te leveren.
- `code (nieuw)`: akkoord -> samengestelde string; niet akkoord -> ongewijzigd;
  handmatig aanpassen -> gebruiker vult zelf in; geen goede termen gevonden
  -> nieuw = origineel.

## blad productinformatie

Voorkeur: officiële product-info/SPC/bijsluiter-URL (NL registratiedocs > EU
databank > humane geneesmiddeleninfo > officiële fabrikant/MAH-site). Huidig
en voorstel URL's worden NOOIT samengevoegd; `nieuw` wordt precies één
gekozen URL.

## registratie

Voorkeur: officieel REGNL-nummer voor veterinaire producten. Normaliseer
schrijfwijze. Verifieer dat naam+concentratie+vorm+verpakking bij DEZELFDDE
registratie horen voordat je het voorstelt -- nooit een nummer van een
andere variant/verpakkingsgrootte overnemen. Meerdere kandidaten -> markeer
voor handmatige controle. Humane producten kunnen een ander officieel
nummer dragen -- markeer duidelijk als humaan (zie producttype-veld).

## waarschuwing (+ bronpassage)

Max 5 woorden, platte tekst, alleen uit een duidelijke officiële bron, nooit
verzonnen, nooit een lange medische uitleg. `waarschuwing bronpassage
(voorstel)` bevat het exacte brontekst-fragment waarop de korte waarschuwing
is gebaseerd (los opgeslagen, ter verificatie). Meerdere belangrijke
waarschuwingen -> markeer voor handmatige review in plaats van er willekeurig
één te kiezen.

## humaan

`true` alleen bij aantoonbaar humaan geneesmiddel, `false` alleen bij
aantoonbaar veterinair, leeg wanneer het niet betrouwbaar is vast te stellen.

## farmaceutische vorm

Gebruik de officiële vorm, vertaald naar de dichtstbijzijnde
gestandaardiseerde Animana-dropdownwaarde via onderstaande vertaaltabel
wanneer de officiële bewoording niet exact overeenkomt. Vul de tabel aan
naarmate nieuwe vormen tegenkomen (documenteer de toevoeging hier).

| Officiële/bron-term (voorbeelden) | Animana-dropdownwaarde |
|---|---|
| tablet, comprimé | tablet |
| chewable tablet, kauwtablet | kauwtablet |
| capsule, hard/soft capsule | capsule |
| solution for injection, injectievloeistof | injectievloeistof |
| suspension for oral use, orale suspensie | suspensie voor oraal gebruik |
| spot-on solution | oplossing voor spot-on |
| eye drops, oogdruppels | oogdruppels |
| ointment, zalf | zalf |
| powder, poeder | poeder |

## werkzame stof(fen) en concentratie

Elke werkzame stof + concentratie + eenheid, officiële stofnamen, exclusief
hulpstoffen. Combinatieproducten volledig noteren. Nooit een concentratie
afleiden die niet expliciet in een betrouwbare bron staat. Formaat:
`"amoxicilline 500 mg + clavulaanzuur 125 mg"`.

## kanalisatie

Output MOET exact één van zijn: `udd` / `uda` / `ura` / `vrij` (allemaal
kleine letters). Normaliseer bronbewoording/afkortingen (bv. Covetrus'
`"UA"` -> `uda`, waarbij UA/UD-conventies per bron kunnen verschillen --
controleer de betekenis in de brondocumentatie zelf, verzin geen 1-op-1
mapping zonder bevestiging). Verzin nooit een 5e categorie (bv. "GDD" is
geen geldige output). Onduidelijk/tegenstrijdig -> laat `nieuw` leeg en
markeer voor review.

## barcode

Altijd als tekst opslaan (leidende nullen behouden -- `write_output.py`
forceert `number_format='@'` op alle barcode-kolommen). Auto-vul `nieuw`
alleen als `huidig` leeg is EN een exacte match gevonden is. Identiek
huidig/voorstel -> behouden. Verschillend -> nooit automatisch overschrijven,
markeren voor handmatige controle. De barcode moet bij EXACT dezelfde
variant/concentratie/verpakkingsgrootte horen -- nooit gokken tussen
meerdere kandidaat-barcodes.

## Producttype-herkenning (eerste stap per rij)

Bepaal vóórdat je velden invult welk type dit is: veterinair geneesmiddel |
humaan geneesmiddel | vrij diergeneesmiddel | voeding/dieetvoeding |
supplement | verzorgingsproduct | medisch hulpmiddel | verbruiksmateriaal |
laboratoriumproduct | interne verrichting | administratief product |
onbekend. Voor niet-geneesmiddel-types zijn velden als
registratie/farmaceutische vorm/kanalisatie vaak terecht "niet van
toepassing" -- vul dat expliciet in, laat het veld niet gewoon leeg zonder
confidence-label.

Dit producttype wordt niet als aparte output-kolom bewaard (zie
`output-schema.md` voor de overwegning) maar moet wel worden meegenomen in
`toelichting_controle`, zodat een reviewer altijd kan zien waarom een veld
"niet van toepassing" is bevonden.
