# Bronhiërarchie (strikte volgorde)

Een hogere bron overschrijft altijd een lagere bij een conflict. Gebruik nooit
een lagere bron als primaire bron wanneer een hogere bron het product heeft.

1. **Nederlandse Diergeneesmiddeleninformatiebank (CBG)**
   https://www.diergeneesmiddeleninformatiebank.nl/
   Primaire bron voor: registratie (REGNL-nummer), farmaceutische vorm,
   werkzame stof(fen)+concentratie, kanalisatie, blad productinformatie
   (SPC/bijsluiter), humaan=false-bevestiging.

2. **Europese Veterinary Medicines Information / Union Product Database**
   https://medicines.health.europa.eu/veterinary/
   Voor centraal (EU-nummer) geregistreerde producten, of ter bevestiging
   naast een REGNL-nummer (zie voorbeeld Apoquel: REGNL112670/EU/2/13/154/006
   -- beide nummers horen bij hetzelfde product, niet met elkaar verwarren
   als 2 aparte matches).

3. **Nederlandse Geneesmiddeleninformatiebank (humane geneesmiddelen)**
   https://www.geneesmiddeleninformatiebank.nl/
   Alleen relevant voor humane geneesmiddelen (off-label diergebruik) of om
   humaan/veterinair te kunnen onderscheiden.

   Bronnen 1-3 zijn publiek, geen login nodig. Geef de voorkeur aan
   gestructureerde databank-toegang (zoekformulier/detailpagina) boven
   herhaald los pagina's scrapen.

4. **Apotheek Diergeneeskunde Universiteit Utrecht (bijsluiters)**
   https://www.uu.nl/organisatie/apotheek-diergeneeskunde/bijsluiters
   Vooral waardevol voor: eigen bereidingen, off-label humaan-in-dier
   gebruik, geïmporteerde diergeneesmiddelen, producten die slecht gedekt
   zijn door de standaard registratie-databanken. Een officiële CBG/EU-SPC
   wint altijd als die gevonden wordt.

5. **Covetrus-productenlijst (bundled asset, NIET live gescraped)**
   `assets/covetrus-productenlijst.xlsx`, sheet 'PRIJS', via
   `scripts/lookup_covetrus.py`. Lagere-prioriteit fallback, vooral voor
   omschrijving/leverancier/artikelnummer/barcode-verificatie wanneer
   officiële bronnen geen praktische productinfo hebben. Een officiële bron
   overschrijft dit altijd bij conflict. Zie `covetrus-mapping.md` voor de
   (nog te verifiëren) kolomtoewijzing. **Dit bestand is een periodiek te
   verversen asset -- Merel levert een nieuwe kopie aan; vraag er niet
   automatisch een nieuwe versie van op.**

6. **Overige gerenommeerde leverancier-/groothandelbronnen**
   Alleen ter ondersteunende bevestiging, nooit als primaire bron.

7. **Algemene internetbronnen**
   Alleen ondersteunend, nooit primair. Gebruik nooit algemene webshops,
   forums, blogs of ongeverifieerde databases als primaire bron.

## KNMvD/WVAB-richtlijnen (antibiotica-tier)

Publieke documenten mogen automatisch geraadpleegd worden, **uitsluitend**
voor de antibiotica-tier-classificatie (`AB 1e keus` / `AB 2e keus` /
`AB 3e keus` in de zoektermen) en vergelijkbare veterinaire classificaties.
Achter-inlog/betaalde richtlijndocumenten mogen alleen gebruikt worden als
Merel ze zelf als kennisbron aanlevert -- nooit scrapen achter een login.
Geen betrouwbare, actuele richtlijn gevonden -> geen AB-tier toekennen (dan
alleen de generieke term "antibioticum").
