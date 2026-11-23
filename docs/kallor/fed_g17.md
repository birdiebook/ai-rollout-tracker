# Källa: Fed G.17 från federalreserve.gov (spår I7)

Byggt och hämtat 2026-11-23 med den ärliga klienten i `ai_tracker.http`. Ersätter ALFRED-versionen av
`us_ip_semis_m` från spår I3 ([census_eu.md](census_eu.md)). Skälet är att FRED:s villkor begränsar användning
"in connection with ... machine learning", och att `www.federalreserve.gov` nu är öppen i proxyn. Inga trender har
analyserats.

| Nyckel | G.17-kod | Serie | Historik | known_from | Typ |
|---|---|---|---|---|---|
| `us_ip_semis_m` | G3344 | Semiconductor and other electronic component (NAICS 3344), SA | 1972-01– | releasedatum | release (riktiga vintages) |
| `us_ip_computers_m` | G3341 | Computer and peripheral equipment (NAICS 3341), SA | 1972-01– | releasedatum | release (riktiga vintages) |

**NAICS 334413** (halvledare i snäv mening) publiceras inte som egen serie i G.17. Den finaste nivån är 3344, och
det är samma serie som FRED kallar IPG3344S. Nyckeln `us_ip_semis_m` betyder alltså samma sak som tidigare.

## Vintages: Fed:s eget releasearkiv

Releasesidan `www.federalreserve.gov/releases/g17/` länkar varje tidigare release. Från **2016-04-15** har varje
månadsrelease en katalog `<ÅÅÅÅMMDD>/ipdisk/` med `ip_sa.txt`. Filen innehåller hela historiken för alla IP-serier
enligt den releasen. Årsrevisionerna har samma fil under `Revisions/<ÅÅÅÅMMDD>/ipdisk/` från 2017-03-31.
Det ger **135 vintages** (127 månadsreleaser och 8 årsrevisioner), och `known_from` är katalogens datum.

**Belägg för att katalogdatumet är releasedatumet:** alla 135 datum från 2016-04-15 är exakt desamma som
ALFRED:s vintage-datum för IPG3344S (135 st. från 2016-04-15; ALFRED har inga datum som arkivet saknar och
tvärtom). Kontrollen gjordes 2026-11-23 och används bara som belägg, inte som data. Releasedagen är normalt
den 14–18:e månaden efter. Undantag finns kring nedstängningen 2025: september 2025 publicerades 2025-12-03
(64 dagar efter månadens slut), och oktober och november 2025 kom båda 2025-12-23.

**Senaste releasen** hämtas från Data Download Program (DDP): paketet *Table 5: Industrial Production: Special
Aggregates and Selected Detail* (CSV, alla observationer, serierna `IP.G3344.S` och `IP.G3341.S`). Datumet läses
från DDP-sidan ("last released Tuesday, November 17, 2026"). När releasen senare flyttas till arkivet används
arkivets version, så att den inte läggs in två gånger. Om DDP-datumet är äldre än arkivets senaste release avbryts
hämtningen.

**DDP läggs ned.** Releasesidan meddelar: "On March 31, 2027, the preformatted data package feature in the Data
Download Program (DDP) will be retired in preparation for the July 1, 2027, DDP page removal." Därför har
hämtningen en reserv. Om DDP inte svarar läses `releases/g17/current/ipdisk/ip_sa.txt` med datumet från
`current/default.htm` ("Release Date: November 17, 2026"). Den filen har samma format som arkivet.

**Före 2016-04-15:** värden som publicerades före den äldsta arkiverade vintagen får `known_from` 2016-04-15.
Det är konservativt, eftersom värdena blir kända för sent och inte för tidigt. 2016-filen börjar 1986.
Åren 1972–1985 kommer in med en senare vintage och får dennas datum. Äldre releaser (1997–2016) finns bara
som text- och PDF-tabeller (`g17.txt`, `g17_sup.txt`) med de senaste månaderna. De skulle kunna ge
förstapubliceringar längre bak, men de har inte byggts.

**Basår:** indexets basår byts vid vissa årsrevisioner (2012=100 i 2016 års filer, 2017=100 i dag, och 2022=100
från årsrevisionen 2026-11-24). En revision ändrar alla månader, så `as_of()` ger alltid nivåer från en och samma
release. Nivåer från olika vintages går inte att jämföra, men tillväxttal går. Enheten i katalogen är därför
"index (basår enligt vintage)".

**Cache:** arkiverade releaser ändras inte. Ett utdrag per release (bara G3344 och G3341) sparas i
`data/raw/fed_g17/vintages/<ÅÅÅÅMMDD>.csv` (committas inte), och varje fil på 2,7 MB laddas alltså ned en gång.
Den första hämtningen tog cirka 2 minuter (135 filer). DDP-svaret sparas som rådata med hämtdatum, som vanligt.

## Licens

`www.federalreserve.gov/disclaimer.htm`, avsnittet *Copyright/trademark*: "Unless otherwise indicated,
information on Board's website is in the public domain and may be copied and distributed without permission.
Please cite to the Board as the source of the information." G.17 är Board-data utan annan upphovsman, så
`publish=True`, och källan anges som Federal Reserve Board, G.17.

## Byte i observationstabellen

ALFRED-raderna för `us_ip_semis_m` togs bort och serien byggdes om:
`python -m ai_tracker.observations --rebuild us_ip_semis_m us_ip_computers_m`. Det tog bort 6 538 ALFRED-rader
och lade till 5 253 + 5 563 rader. Alla warehouse-kontroller passerar. Andra kopior av tabellen behöver samma
kommando en gång.

M3 (`us_orders_computers_electronics_m`) ligger kvar via ALFRED i `series/census_m3_alfred.py`, märkt som
interimskälla med `publish=False`, i väntan på en Census API-nyckel.

**Modellerna påverkas inte.** `us_ip_semis` är fortfarande utesluten ur N1 och N2 i fas 3 (registret
2026-11-23). Ska serien användas krävs en ny registrerad variant, och ingen modellkod har ändrats.

## Värdar

`www.federalreserve.gov` (releasearkiv, DDP och villkor) och `alfred.stlouisfed.org` (bara som belägg för
releasedatumen). Inga värdar nekades.
