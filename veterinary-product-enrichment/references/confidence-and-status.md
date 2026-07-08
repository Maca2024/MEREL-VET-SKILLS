# Twee gescheiden schalen -- niet verwarren

## 1. Per-veld confidence (`{veld} (confidence voorstel)`) -- 5 waarden

Deze schaal geldt per ENKEL VELD (registratie, barcode, kanalisatie, ...) en
stuurt de deterministische nieuw-kolom-logica in `decision_logic.py`.
Gebruik uitsluitend deze 5 waarden, verzin er geen 6e bij:

- **Hoog**: direct en ondubbelzinnig bevestigd door een betrouwbare bron
  (exact registratienummer, exacte barcode, exacte
  naam+concentratie+vorm+verpakking-combinatie, meerdere ID-velden komen
  overeen met maar één mogelijk product). Mag `nieuw` auto-vullen als
  `huidig` leeg is.
- **Gemiddeld**: zeer waarschijnlijke match maar niet elk kenmerk bevestigd
  (naam+concentratie+vorm kloppen, verpakkingsgrootte niet; officiële naam
  gevonden maar geen exacte barcode; één waarschijnlijke match maar een
  kernveld ontbreekt). Wordt NOOIT automatisch overgenomen als dat een
  bestaande waarde zou veranderen.
- **Laag**: alleen beperkt bewijs (alleen merknaam matcht; alleen generieke
  omschrijving gevonden; ondersteunende bron zonder bevestigde exacte
  variant; meerdere varianten blijven mogelijk). Altijd handmatige controle
  nodig.
- **Niet gevonden**: pas na uitputting van ALLE afgesproken zoekrondes,
  zonder bruikbare match/info.
- **Niet van toepassing**: het veld is logisch niet van toepassing voor dit
  producttype (bv. geen 'registratie' voor een verzorgingsproduct, geen
  'kanalisatie' voor een administratieve regel, geen 'farmaceutische vorm'
  voor een verrichting). Dit telt als een BRUIKBAAR resultaat, niet als
  "niet gevonden".

## 2. Rij-niveau `resultaatstatus` -- 8 waarden

Complementair aan, maar VERSCHILLEND van de per-veld confidence hierboven.
Beoordeel het HELE product-rij holistisch (niet mechanisch afgeleid van de
veld-confidences) en kies exact één van:

| Waarde | Wanneer |
|---|---|
| `exact gevonden` | (Bijna) alle toepasselijke velden Hoog-confidence gevonden en identiek aan of correct aanvullend op huidig. |
| `grotendeels gevonden` | De meeste toepasselijke velden gevonden (Hoog/Gemiddeld), een enkel veld ontbreekt of is Laag. |
| `waarschijnlijk gevonden` | Zoekronde 5: meerdere kenmerken komen overeen maar geen volledige zekerheid -- expliciet als "waarschijnlijk, controleren" gelabeld. |
| `gedeeltelijk verrijkt` | Een deelverzameling velden gevonden (bv. alleen barcode+kanalisatie bij een voedingsproduct), de rest terecht leeg/n.v.t. |
| `meerdere mogelijke matches` | Zoekronde leverde >1 kandidaat op die niet met zekerheid te onderscheiden zijn (bv. 2 verpakkingsgroottes, beide barcodes plausibel). |
| `niet van toepassing` | Producttype maakt vrijwel alle velden logisch n.v.t. (bv. verrichting, labtest, administratieve regel). |
| `niet gevonden` | Alle 5 zoekrondes uitgevoerd, niets bruikbaars gevonden, en het is geen duidelijk n.v.t.-geval. |
| `handmatige controle nodig` | Huidig en voorstel conflicteren op een kernveld (bv. registratienummer klopt niet met de rest), of een andere reden waarom een mens per se moet kijken vóór verder gebruik. |

Vuistregel voor de holistische beoordeling: als één kernveld (registratie,
barcode, werkzame stof) een HARDE tegenspraak heeft met de bestaande data
-> altijd minstens `handmatige controle nodig`, ongeacht hoeveel andere
velden wel kloppen.
