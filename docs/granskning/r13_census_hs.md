# R13 – granskning av Census-import per land (spår M2)

Granskningsspår R13, 2026-11-24, gren `auto14/r13-census-hs` från `auto13/m2-census-hs`. Granskat: årsfilen per land
och end-use-kod (`src/ai_tracker/sources/census_enduse.py`, `series/census_enduse.py`, 21 serier), HS-serierna bakom
`CENSUS_API_KEY` (`sources/census_hs.py`, `series/census_hs.py`, 35 serier), `keyed.py` och dess krokar i
`observations.refresh`, `warehouse.fresh` och `pipeline._refresh`, `tests/test_census_hs.py`, registerposten
"2026-11-24 – M2" och [kallor/census_hs.md](../kallor/census_hs.md).

Underlag, hämtat 2026-11-24 från primärkällor:
- `enduse_imports.xlsx` från census.gov (byte för byte samma fil som spårets råkopia, Last-Modified 2026-06-09 12:31:03 GMT).
- Pressmeddelandena för FT-900:s årsrevision, `final_2016.pdf` … `final_2025.pdf` (alla tio år).
- `finalxlsx_2020.zip` … `finalxlsx_2025.zip` (Exhibit 7 och 13). Arkiven för 2016–2019 ger 404.
- `ft900_1701.pdf`, `ft900_2201.pdf` och notisen `20220308_enduse_changes.pdf` (omklassificering av end-use).
- API:ts metadata utan nyckel: `imports/hs.json`, `variables.json`, `examples.json`. Svaren från ett dataanrop utan
  nyckel och med en påhittad nyckel (302 till `missing_key.html` respektive `invalid_key.html`).
- *Guide to International Trade Datasets* (Census, PDF), utvecklarsidan för International Trade och Census API:s
  användarvillkor (*Terms of Service*).

Blockerade värdar: `web.archive.org`, `archive.org`, `federalregister.gov`, `usitc.gov`, `hts.usitc.gov`,
`govinfo.gov` och `cbp.gov` (proxyn nekar). Sessionen har ingen `CENSUS_API_KEY`, så inget dataanrop med nyckel
kunde göras. HS-serierna är alltså prövade mot dokumentationen och med syntetiska svar, inte mot riktiga data.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Saknad nyckel | **OK.** SKIPPED, inga rader och ingen rad i hämtloggen, bevisat på en kopia av den riktiga bastabellen. Undantaget gäller bara serier vars nyckel saknas |
| 2. Nyckelhygien | **OK.** Nyckeln finns varken i loggar, felmeddelanden, råkopiornas sökvägar eller innehåll. En anmärkning om undantagets `__context__` |
| 3. Årsfilens datering och värden | **OK.** Alla tio årsrevisioner (2017–2026) ligger 30–38 dagar före `known_from`. 210 av 210 värden stämmer med filen, och filen stämmer med Exhibit 7 och 13 |
| 4. API-anropet och nollregeln | **Anmärkning.** Anropet följer guiden, och guiden stöder nollregeln. Men nollorna fylls över *båda* svarens period, vilket kan ge falska nollor (R13-1). Ett fel upprepas för alla 35 serier (R13-3). Första anropet med nyckel är inte prövat |
| 5. Nomenklaturbrott | **Anmärkning.** HS-brotten är noterade som registrerat, och HS 2017 från 2017-01 är belagt. I årsfilen finns ett odokumenterat brott i end-use-klassificeringen mellan 2018 och 2019 (R13-4) |
| 6. Census API:s notis | **Anmärkning.** Notisen står i licenssträngen, men den når inte hemsidan på en framträdande plats (R13-2) |
| 7. Förregistrering | **OK.** Registret före koden och oförändrat efter. Det som setts före registreringen är redovisat |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Inget läckage och inga fel värden. Veckojobbet fallerar inte utan nyckel. Fem
fel ska rättas (R-1 – R-5), varav R-1 – R-3 i koden. Ägaren har nu lagt in `CENSUS_API_KEY` i GitHub, så efter en
merge gör nästa veckohämtning det första anropet med nyckel. R-2 (notisen) och R-6 (en kontrollerad första hämtning)
bör därför vara klara innan HS-serierna får data. Inga mått är räknade, och serierna är katalogserier.

## 1. Saknad nyckel – OK

- `census_hs.fetch` anropar `keyed.require` före allt annat, och `MissingKey` fångas i `observations.refresh` före
  det allmänna `except`. Status blir `SKIPPED: CENSUS_API_KEY is not set …`, och `upsert` körs aldrig. Alltså skrivs
  varken rader eller hämtlogg.
- **Veckovägen på en kopia av bastabellen** (764 995 rader, 483 serier, hämtloggen 486 rader):
  `python -m ai_tracker.pipeline --table <kopia> weekly <de 35 HS-nycklarna>` utan nyckel gav exitkod 0, 35 rader
  `SKIPPED`, notisen "35 series skipped: CENSUS_API_KEY is not set" och alla datatester och `fresh` ok. Tabellen och
  hämtloggen hade samma sha256 före och efter.
- **Första hämtningen med nyckel** kördes på samma kopia med en påhittad nyckel och ett syntetiskt API: två anrop för
  alla 35 serier, 5 775 rader `backfill`, `known_from` enligt FT-900:s kalender (2013-08 → 2013-10-24, 2025-10 →
  2026-01-08, 2026-09 → 2026-11-10), inga rader efter hämtdagen och inga överträdelser i datatesterna.
- En överhoppad körning flyttar inte senare perioder. Test: en överhoppad körning 2026-11-15 och sedan en hämtning med
  nyckel 2026-11-24 ger 2026-09 dagen 2026-11-10. Om körningen 11-15 i stället hade loggats som en hämtning utan
  2026-09, hade perioden fått 2026-11-16.
- `warehouse.fresh` undantar bara serier i `keyed.REQUIRES` vars variabel saknas. På hela katalogen utan rader och
  utan nyckel saknas de 35 HS-serierna i listan över gamla serier, medan de 21 nyckelfria årsserierna finns kvar.
  Med nyckeln satt finns HS-serierna med.
- Med en nyckel som inte är aktiverad (302 till `invalid_key.html`) blir status `FAILED`, ingenting skrivs, och
  serierna blir gamla. Veckojobbet går då rött med exitkod 2, synligt. Ett tomt svar (204) blir också `FAILED`
  utan loggrad.

## 2. Nyckelhygien – OK

- Nyckeln skickas bara som parameter i `requests.get`. Råkopian sparas under URL:en utan nyckel
  (`http.raw_path` använder bara URL:ens sökväg plus en sha1 av den publika URL:en), och svaret innehåller inte nyckeln.
- Census omdirigerar till `https://api.census.gov/data/invalid_key.html` respektive `missing_key.html`, utan
  frågesträng (observerat). Meddelandet visar bara sidnamnet.
- Ett `ConnectionError` vars text innehåller URL:en med nyckel (så ser urllib3:s `MaxRetryError` ut) ger ett
  `RuntimeError` utan nyckel, och `traceback.format_exception` visar inte orsaken (`from None`). Statusraden i
  `refresh` och utskriften innehåller inte nyckeln.
- Ingen kod i projektet sätter loggning på DEBUG, så urllib3:s rad med hela URL:en skrivs aldrig. I Actions maskeras
  hemligheter dessutom i loggen.
- *Anmärkning:* `raise … from None` döljer orsaken, men det ursprungliga undantaget med nyckeln ligger kvar i
  `__context__`. Inget i projektet läser det i dag. Den som vill vara helt säker höjer felet utanför `except`-blocket.
- *Anmärkning:* svaret på en omdirigering sätter en cookie `originalReferer` med hela den ursprungliga URL:en. Koden
  använder ingen `Session` och sparar inga cookies, så det spelar ingen roll i dag.

## 3. Årsfilens datering och värden – OK

**Datering.** Regeln är 31 december + 191 dagar, alltså 10 juli året efter och 9 juli när året efter är ett
skottår (data för 2019 och 2023). Alla tio årsrevisioner är lästa i `final_YYYY.pdf`:

| Dataår | Årsrevision ("FOR RELEASE") | `known_from` | Marginal |
|---|---|---|---|
| 2016 | 2017-06-02 | 2017-07-10 | 38 dagar |
| 2017 | 2018-06-06 | 2018-07-10 | 34 |
| 2018 | 2019-06-06 | 2019-07-10 | 34 |
| 2019 | 2020-06-04 | 2020-07-09 | 35 |
| 2020 | 2021-06-08 | 2021-07-10 | 32 |
| 2021 | 2022-06-07 | 2022-07-10 | 33 |
| 2022 | 2023-06-07 | 2023-07-10 | 33 |
| 2023 | 2024-06-06 | 2024-07-09 | 33 |
| 2024 | 2025-06-05 | 2025-07-10 | 35 |
| 2025 | 2026-06-09 | 2026-07-10 | 31 |

Spåret hade belagt 2017–2025. Även 2016 håller (2017-06-02). Att äldre versioner av just den här filen kom samma dag
går fortfarande inte att verifiera (`web.archive.org` är blockerad). Men samma årssummor fanns i årsrevisionens
tabeller samma dag (Exhibit 7 för världen och Exhibit 13 per land), och regeln ligger minst 31 dagar efter. Om filen
först kom tidigare, till exempel i februari med preliminära värden, är regeln bara försiktigare. Inget läckage.

**Backfill.** Hela historiken har vintage 2026-06-09, och en årsrevision ändrar tre år bakåt (`final_2016.pdf`:
"revised statistics … for January 2014 to March 2017"). Det är redovisat. Storleken, för 2024 mellan revisionen
2025-06-05 och filen:

| Värde 2024 | Revision 2025 | Fil 2026 | Ändring |
|---|---|---|---|
| Datorer, världen (Exhibit 7) | 116 758 | 116 768,2 | +0,01 % |
| Datortillbehör, världen | 100 638 | 100 606,5 | −0,03 % |
| Halvledare, världen | 81 897 | 81 654,2 | −0,30 % |
| Mexiko, all import (Exhibit 13) | 505 523,2 | 503 110,1 | −0,48 % |
| Malaysia, all import | 52 488,4 | 52 163,4 | −0,62 % |

För koderna per land kan ändringarna vara större. Det går inte att mäta, eftersom äldre versioner av filen inte finns.

**Värden.** Alla 210 rader i spårets tabell stämmer exakt med filen. Filen stämmer med Census tabeller:
- Exhibit 7 (`finalxlsx_2025.zip`), världen 2023–2025, alla tre koder, på miljonen: till exempel datorer 2025
  218 217 (filen 218 216,9), datortillbehör 143 348 (143 348,2) och halvledare 76 046 (76 045,6).
- Exhibit 13, import 2025 och 2024, summan över alla end-use-koder per land, exakt för alla sex länderna: Taiwan
  201 369,2 och 116 284,9, Mexiko 534 314,9 och 503 110,1, Vietnam 193 879,3, Malaysia 59 536,8, Thailand 91 255,3
  och Kina 308 651,9 (2025).
- Taiwans summa 2025 och 2024 är också summan av `us_imports_tw_m` i bastabellen.
- Landskoderna (5830, 2010, 5520, 5570, 5490, 5700) har rätt `CTY_DESC` i filen, och kodbeskrivningarna är
  *Computers*, *Computer accessories* och *Semiconductors*. Filen har inga dubbletter och inga tomma celler i de 21 raderna.

*Anmärkning:* årsparsern gör icke-numeriska celler till NaN och tar bort dem tyst. HS-parsern stoppar i stället.
Det ger inget läckage (en saknad period dateras senare), men samma hårda regel vore tydligare.

## 4. API-anropet och nollregeln – anmärkning

**Anropet följer dokumentationen.**
- `variables.json`: `GEN_VAL_MO` "15-digit General Imports, Total Value", `I_COMMODITY` "2-, 4-, 6-, or 10-character
  Import Harmonized Code", `CTY_CODE`, `CTY_NAME` och `time` (bara predikat). `CTY_CODE`, `I_COMMODITY`, `DISTRICT`,
  `RP` och `CTY_SUBCODE` har `"required": "default displayed"`.
- Guiden, "Default Values for Parameters": "The default value for all string type parameters is a dash (-)". Utan
  `CTY_CODE` blir svaret alltså summan för alla länder ("TOTAL FOR ALL COUNTRIES"), och distrikt och
  tullsatsbestämmelse blir summor i båda anropen. Upprepade predikat är alternativ (`CTY_CODE=1220&CTY_CODE=2010`),
  `time=from+2013-04` ger alla månader från april 2013, predikat läggs till som kolumner, raderna är inte sorterade,
  och 204 betyder att det inte finns några poster.
- API:t uppdateras på releasedagen. Guiden: "updated with the most recent month of trade statistics, after 8:30AM on
  the morning of the … (FT-900) release". Utvecklarsidan: "updated monthly on the day of press release" och
  "revised annually with the publication of April statistics". Dokumentet säger att detta inte är verifierat. Det är
  det nu, så FT-900:s kalender gäller för HS-serierna.
- Licensen i `imports/hs.json` är `http://creativecommons.org/publicdomain/zero/1.0/`, som dokumentet säger.

**Nollregeln stöds av guiden.** Ett 204 betyder enligt guiden att "the U.S. did not export any soybeans to the
Dominican Republic in January of 2013". Poster med månadsvärdet 0 finns när värdet hittills under året inte är 0
(exemplet `["1610","ST PIERRE AND MIQUELON","0","251067",…]`). En saknad post betyder alltså ingen handel alls under
året så långt. Värdefälten har ingen flagga för saknade värden. Den finns bara för kvantiteter (`*_FLAG`).

**R13-1: nollorna fylls över båda svarens period.** `series()` bygger månadsintervallet från hela cachen, det vill
säga landanropet och världsanropet tillsammans. Registret säger "inom svarets period". Om de två svaren slutar på
olika månader, till exempel om releasen sker mellan de två anropen, får alla 30 landserier värdet 0 för den månad som
bara världssvaret har. Körd på kopian av bastabellen: landsvaret till 2026-08 och världssvaret till 2026-09 gav 0,0
för 2026-09 i alla landserier, sparat med `known_from` 2026-11-10. Det riktiga värdet kommer först veckan efter, som
revision. Den schemalagda körningen (måndag 03:37 UTC) sammanfaller aldrig med en release kl. 8:30 ET, men en körning
för hand kan göra det. Nollor efter seriens sista post döljer dessutom att en månad saknas.

**R13-3: ett fel upprepas för varje serie.** Cachen sparar bara lyckade svar. Om anropet misslyckas, gör var och en av
de 35 serierna om båda anropen. Med en nyckel som inte är aktiverad blir det 35 anrop. Om api.census.gov inte svarar
alls, tar varje serie upp till 4 × 180 sekunder plus väntan, alltså cirka 12 minuter, och de 35 serierna cirka 7 timmar.
Veckojobbet har en gräns på 350 minuter och stoppas då, och cachen sparas inte. Felet ska sparas i cachen, så att en
körning gör högst två anrop.

**Första anropet med nyckel är inte prövat.** Guiden varnar för att `time` ger fler timeouts än `YEAR`/`MONTH`, och
rekommenderar många mindre anrop för automatisk hämtning. Spårets anrop är cirka 5 000 rader (6 länder × 5 koder ×
165 månader) och 825 rader för världen, långt mindre än guidens exempel på timeout. Men om formen inte fungerar,
fallerar alla 35 serierna, och veckojobbet går rött med exitkod 2 varje vecka tills det är rättat (R-6).

*Anmärkning:* utvecklarsidan säger att de månatliga dataseten börjar januari 2010. Dokumentet säger att HS-datasetet
börjar 2013-01. Det går inte att se utan nyckel. Starten 2013-01 är registrerad och kan stå kvar.

## 5. Nomenklaturbrott – anmärkning

- **HS 2017:** belagt. Census notis i `ft900_2201.pdf`: "The last WCO modifications to the Harmonized System were
  introduced in March 2017 with January 2017 statistics". Brottet ligger alltså vid 2017-01, som registrerat.
- **HS 2022:** att HS 2022 gäller från januari 2022 i statistiken går inte att belägga i Census text. Enligt
  tullförordningen (presidentkungörelse 10326, enligt minnet med verkan från 27 januari 2022) kan januari 2022 vara en
  blandad månad. Det kunde inte verifieras (`usitc.gov` och `federalregister.gov` är blockerade).
- Serierna skarvas inte, och brotten står i registret och i `NOTE`, som registrerat. Det finns ingen gemensam
  brottsmekanism i katalogen, och katalogserier utan mått behöver ingen.
- **R13-4: end-use-klassificeringen har ett brott mellan 2018 och 2019 i årsfilen.** Census omklassificerade
  end-use-koder med januari 2022 och lade in ändringen för 2019–2021 vid årsrevisionen 2022-06-07
  (`20220308_enduse_changes.pdf`). Den förra omklassificeringen (januari 2017) lades in för 2014–2016. I filen följer
  alltså 2016–2018 den äldre klassificeringen och 2019–2025 den nya. För världen ändrades 2019 mellan revisionerna
  2021 och 2022 med +7 (datorer), −28 (datortillbehör) och −301 MUSD (halvledare, −0,56 %). Vanliga revisioner av det
  äldsta året i fönstret låg på −0,01 till −0,08 % för halvledare, så det mesta är omklassificering. Per land går
  effekten inte att mäta. Brottet nämns inte i dokumentet, i `NOTE` eller i registret.

## 6. Census API:s notis – anmärkning

Villkoren (lästa 2026-11-24): "All services, which utilize or access the API, should display the following notice
prominently within the application: "This product uses the Census Bureau Data API but is not endorsed or certified
by the Census Bureau."" Texten i `series/census_hs.py` (`NOTICE`) är ordagrann och står i alla 35 seriers `license`.

**R13-2: notisen når inte hemsidan på en framträdande plats.**
- Datakontraktet (`site_bundle.export.licence_block`) lägger notisen bara i `license.text`. `attribution`, som den nya
  sidans serievy visar (`web/src/routes/serie/[key]/+page.svelte`), blir "Källa: … Licens: public domain (amerikansk
  myndighet). Bearbetning: ai-rollout-tracker." utan notis.
- Den gamla sidan visar licenstexten bara i en hopfälld ruta ("villkor") i tabellen över datakällor på metodsidan.
- Dokumentet säger "Hemsidan ska visa den när HS-serierna har data", men inget i koden gör det, och inget test prövar
  det. Serierna har `publish=True`, och nyckeln finns nu i GitHub. Notisen ska alltså vara på plats innan serierna får
  data, eller så sätts `publish=False` tills den är det.
- Årsserierna kommer inte via API:t och behöver ingen notis. Deras licens (`census_trade.LICENSE`) är riktig.

## 7. Förregistrering – OK

| Tid (UTC) | Commit | Innehåll |
|---|---|---|
| 20:59 | `d9f4993` | Registerposten: serier, källor, datering, nollregeln, brotten och regeln för saknad nyckel |
| 21:02 | `be3576e` | Kod och tester |
| 21:05 | `57fc420` | Dokumentation och handkontroll, årsfilen hämtad |

`git diff d9f4993 HEAD -- docs/mattregister.md` är tom, så registret är oförändrat efter koden. Dateringsregeln
bygger på releasedatum och filens metadata, inte på värden. Före registreringen såg spåret filens struktur och första
radens värde, och vid genomgången av FT-900:s bilagor värden för september 2026 i Exhibit 8 och 16a. Det är
redovisat, och det rör inte de registrerade serierna. Inga mått är räknade. Git visar bara ordningen på commits, inte
vad som räknades lokalt, men inget tyder på mer.

*Anmärkning:* om en nyckel tas bort efter att serierna har data, undantas de tyst från aktualitetskontrollen (bara en
notis). En varning när en överhoppad serie redan har rader vore tydligare.

## Inte verifierat

- Svaren från API:t med en riktig nyckel: kolumnerna, att alla 35 kombinationer har poster, hur många månader som saknar
  post och om `time=from 2013-01` ger timeout. Sessionen har ingen nyckel (R-6).
- Att äldre versioner av `enduse_imports.xlsx` kom samma dag som årsrevisionen (`web.archive.org` blockerad). Regeln
  har ändå minst 31 dagars marginal mot årsrevisionen, där samma summor publicerades.
- Hur stor backfill-revisionen och omklassificeringen är per land och kod. Bara världen och landets totala import
  kunde jämföras.
- Dagen då HS 2022 började gälla för import i USA:s tullförordning (`usitc.gov`, `federalregister.gov` blockerade).
- Om HS-datasetet börjar 2010 eller 2013.

## Rättningar (för ett rättningsspår)

| # | Var | Rättning |
|---|---|---|
| R-1 | `sources/census_hs.py` `fetch`/`series` (R13-1, should_fix) | Bygg månadsintervallet per svar (landanropet för länderna, världsanropet för världen), som registret säger. Fyll bara månader mellan seriens första och sista post, aldrig efter den sista. Det strikta xfail-testet `test_r13_1_…` slår om när det är rättat |
| R-2 | `site_bundle/export.py` `licence_block`, gamla sidans `site/` (R13-2, should_fix) | Lägg notisen i `attribution` (eller ett eget fält som sidan visar) för serier vars licens innehåller den, och visa den i sidfoten när någon HS-serie har data. Annars `publish=False` för HS-serierna tills det är gjort. Webbsessionen behöver bara visa fältet. Test `test_r13_2_…` |
| R-3 | `sources/census_hs.py` `_CACHE` (R13-3, should_fix) | Spara även ett misslyckat anrop i cachen, så att en körning gör högst två anrop. Överväg kortare timeout (60 s som `http.get`) och att inte göra om `RequestException` tre gånger. Test `test_r13_3_…` |
| R-4 | `docs/kallor/census_hs.md`, `series/census_enduse.py` `NOTE`, `docs/mattregister.md` (tillägg) (R13-4, should_fix) | Redovisa brottet i end-use-klassificeringen mellan 2018 och 2019 (omklassificering januari 2022, inlagd för 2019–2021) och storleken för världen. Skarva inte. Test `test_r13_4_…` |
| R-5 | `docs/kallor/census_hs.md` (R13-5, note) | "9 juli efter ett skottår" → "9 juli när året efter är ett skottår (data för 2019 och 2023)". Test `test_r13_5_…` |
| R-6 | drift, första hämtningen med nyckel (should_fix) | Kör HS-hämtningen en gång i en session som har nyckeln (molnmiljön har den nu), före eller direkt efter merge, och gå igenom listan "Kontrollera vid första hämtningen med nyckel" i dokumentet. Fungerar `time=from 2013-01` inte, dela anropet per år (`YEAR`). Ändras nollregeln efter att data har setts, ska det loggas i registret med datum och motivering |
| R-7 | `docs/kallor/census_hs.md` (note) | Byt "inte verifierat" om API:ts uppdatering mot citaten i punkt 4. Lägg till backfill-storleken i punkt 3 och att HS 2022:s startdag i tullförordningen inte är verifierad |
| R-8 | `sources/census_enduse.py`, `sources/census_hs.py`, `keyed.py` (note) | Valfritt: stoppa på icke-numeriska celler i årsfilen, höj felet utanför `except` i `request`, och varna när en överhoppad serie redan har rader |

## Tester

`tests/test_r13_census_hs.py` (syntetiska fixturer, inget nät):
- överhoppad hämtning lämnar tabellen och hämtloggen byte för byte oförändrade (passerar)
- en överhoppad körning flyttar inte `known_from` för första hämtningen med nyckel, med motexempel (passerar)
- aktualitetskontrollen undantar bara serier vars registrerade nyckel saknas (passerar)
- en nyckel som Census vägrar ger `FAILED` och en gammal serie, ett 204 ger `FAILED` utan loggrad (passerar)
- de observerade omdirigeringarna, ett `ConnectionError` med nyckeln i URL:en och råkopiorna visar aldrig nyckeln (passerar)
- årsfilens `known_from` ligger 30–38 dagar efter var och en av de tio årsrevisionerna (passerar)
- anropets form följer guiden, och världssvaret tolkas rätt även med en `CTY_CODE`-kolumn (passerar)
- R13-1 – R13-5 (strikt xfail)

`python -m pytest -q tests/test_r13_census_hs.py tests/test_census_hs.py`: 35 passerade, 5 xfail.
