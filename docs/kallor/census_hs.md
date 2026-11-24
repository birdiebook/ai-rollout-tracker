# Källor: USA:s import av servrar, datordelar och halvledare per land (spår M2)

Byggt 2026-11-24 i körning 13 (förslag 4 i [riktning.md](../riktning.md)). Registerpost:
"2026-11-24 – M2: import av servrar, datordelar och halvledare per land" i [mattregister.md](../mattregister.md).
Alla serier är katalogserier i G6, inte kärnserier. Inga mått har räknats.

## Sammanfattning

| Nycklar | Källa | Frekv. | Historik | known_from | Status |
|---|---|---|---|---|---|
| `us_imp_eu{21300,21301,21320}_{tw,mx,vn,my,th,cn,world}_a` (21 serier) | Census `enduse_imports.xlsx`, ingen nyckel | A | 2016–2025 | 31 dec + 191 dagar (10 juli året efter) | hämtad, backfill |
| `us_imp_hs{8471,847150,847180,847330,8542}_{tw,mx,vn,my,th,cn,world}_m` (35 serier) | Census API `intltrade/imports/hs` | M | från 2013-01 | max(månadsslut + 41 dagar, sena FT-900-releaser) | **BLOCKED** tills `CENSUS_API_KEY` finns |

Länder (Census `CTY_CODE`): `tw` 5830 Taiwan, `mx` 2010 Mexiko, `vn` 5520 Vietnam, `my` 5570 Malaysia, `th` 5490
Thailand, `cn` 5700 Kina och `world` hela världen (0000 i årsfilen, `-` i API:t). Enhet: MUSD, ej säsongsrensad.

## Finns det nyckelfria månadsdata per land? Nej

Census nyckelfria sidor gicks igenom 2026-11-24:

- `foreign-trade/statistics/historical/enduse.html` (End-use Data Page) har tre produkter: månadsimport per
  huvudkategori (1-siffrig end-use, hela världen, 1992–), årssummor per land och 5-siffrig end-use-kod (2016–2025)
  och en hänvisning till API:t: "detailed End-use statistics available through the International Trade API, monthly
  2010-Present". De gamla landssidorna under `product/enduse/imports/` ger 404.
- `historical/hs.html` hänvisar HS-data per land till USA Trade Online (kräver konto) och API:t.
- FT-900:s bilagor (`ft900xlsx.zip`, arkiv i `ft900_index.html`): Exhibit 8 har 5-siffriga end-use-koder per månad,
  men bara för hela världen och säsongsrensat. Exhibit 16a har avancerad teknik (ATP) per land, men per
  teknikgrupp och inte per vara. ATP-gruppen "Information and Communications" omfattar också telefoner och
  telekomutrustning.

Den nyckelfria leveransen är därför årsfilen per land. Månadsdata per land kräver nyckeln.

## Årsfilen per land och end-use-kod (ingen nyckel)

**Fil:** `www.census.gov/foreign-trade/statistics/product/enduse/imports/enduse_imports.xlsx` ("Annual Country by
5-digit End-Use Code, Annual totals, 2016 - 2025"). Ett blad, en rad per (`CTY_CODE`, `END_USE`) med `CTY_DESC`,
`COMM_DESC` och `value_16` … `value_25` i dollar. Koderna: 21300 *Computers*, 21301 *Computer accessories*
(kringutrustning och datordelar) och 21320 *Semiconductors*. Parsern kräver att `COMM_DESC` stämmer med koden, så
att en kod som byter innehåll stoppar hämtningen.

**Värdebegrepp:** summan över alla end-use-koder för ett land är landets import i FT-900, Census-bas (general
imports). Se kontrollen nedan.

**known_from** = 31 december + 191 dagar, alltså 10 juli året efter (9 juli efter ett skottår). Belägg:

- Filen byts ut vid FT-900:s årsrevision. Serverns Last-Modified är 2026-06-09 12:31:03 GMT, och årsrevisionen 2025
  släpptes 8:30 EDT samma dag (`ft900/final_2025.pdf`, "FOR RELEASE AT 8:30 AM EDT, TUESDAY, JUNE 9, 2026").
  Filens egen metadata säger "created 2026-05-22", alltså förberedd före releasen.
- Årsrevisionerna kom 2018-06-06, 2019-06-06, 2020-06-04, 2021-06-08, 2022-06-07, 2023-06-07, 2024-06-06,
  2025-06-05 och 2026-06-09 (`final_2017.pdf` … `final_2025.pdf`).
- Att äldre versioner av filen kom vid samma release går inte att verifiera. `web.archive.org` nekas av proxyn.
  Regeln ligger därför cirka en månad efter de belagda datumen.

**Läckage:** filen har ingen versionshistorik. Hela historiken 2016–2025 är backfill med vintage 2026-06-09, och
de äldre åren bär senare revisioner. Från nästa årsrevision blir ändrade värden revisioner med hämtdagen.
Fönstret rullar: 2016 faller troligen bort 2027. De lagrade raderna ligger kvar.

**Aktualitet:** gränsen är 191 + 400 = 591 dagar från årets slut. Utan 2026 blir serierna för gamla efter
2027-08-14, och 2026 väntas i juni 2027.

## Månadsserierna per HS-kod och land (nyckel)

**Endpoint:** `api.census.gov/data/timeseries/intltrade/imports/hs` (datasetet ITMONTHLYIMPORTSHS, månadsdata från
2013-01). Ett dataanrop utan nyckel svarar med 302 till `missing_key.html`. Metadata svarar utan nyckel, och
variabelnamnen är låsta från `variables.json` (läst 2026-11-24):

| Variabel | Census beskrivning | Används som |
|---|---|---|
| `GEN_VAL_MO` | 15-digit General Imports, Total Value | värde (dollar → MUSD) |
| `I_COMMODITY` | 2-, 4-, 6-, or 10-character Import Harmonized Code | HS-kod (predikat och kolumn) |
| `CTY_CODE`, `CTY_NAME` | 4-character Country Code, 50-character Country Name | land |
| `time` | ISO-8601 Date/Time value (predikat) | månad, `from 2013-01` |

**HS-koder:** 8471 (alla datorer och enheter, även bärbara), 8471.50 (processorenheter, där många servrar
klassas), 8471.80 (andra enheter, bland annat enheter som byggs in i datorer), 8473.30 (delar och tillbehör till
8471, bland annat kort och moduler) och 8542 (integrerade kretsar). Var en viss AI-server klassas varierar mellan
importörer, så 8471.50, 8471.80 och 8473.30 behövs alla.

**Anrop** enligt *Guide to International Trade Datasets* (Census): två per hämtning för alla 35 serier.

```
get=CTY_CODE,CTY_NAME,I_COMMODITY,GEN_VAL_MO&CTY_CODE=5830&…&CTY_CODE=5700&I_COMMODITY=8471&…&I_COMMODITY=8542&time=from 2013-01
get=I_COMMODITY,GEN_VAL_MO&I_COMMODITY=8471&…&I_COMMODITY=8542&time=from 2013-01      (hela världen)
```

Svaret är en JSON-lista med rubrikraden först, och predikaten läggs till som kolumner. Parsern hittar kolumner via
namn, stoppar om ett (land, kod, månad) har två olika värden eller om ett värde inte är ett tal, och läser 204 som
tomt svar.

**known_from** = max(månadsslut + 41 dagar, belagd sen release), samma regel och samma `LATE` som `us_imports_tw_m`
(se [census_eu.md](census_eu.md)). HS-detaljen släpps med FT-900. Att API:t uppdateras samma dag som releasen är
inte verifierat. FT-900 kom 32–41 dagar efter månadens slut 2017–2026, så regeln ligger på eller efter releasen.

**Läckage och brott:** API:t har bara senaste vintage, så första hämtningen är backfill. Årsrevisionen i juni
ändrar historiken, och ändringarna blir revisioner med hämtdagen. HS-nomenklaturen ändrades 2017-01 (HS 2017) och
2022-01 (HS 2022). I HS 2022 kom den nya positionen 8524 (platta bildskärmsmoduler), som kan ha flyttat varor från
8473.30. Serierna skarvas inte. Brotten är noterade i registret.

**Månader utan post:** en månad inom svarets period som saknar post för ett land och en kod räknas som 0. Antagandet
är att API:t bara har poster för handel som har ägt rum. Det kontrolleras vid första hämtningen med nyckel. Annars
stoppar `no_gaps` serien.

**Nyckeln** skickas bara i själva anropet. Råkopian sparas under URL:en utan nyckel, felmeddelanden innehåller aldrig
URL:en med nyckel, och om API:t skulle eka nyckeln i ett felsvar ersätts den med `***`.

**Licens och villkor:** amerikanskt federalt verk. Datasetets metadata (`imports/hs.json`) anger
`"license": "http://creativecommons.org/publicdomain/zero/1.0/"`. Census API:s användarvillkor kräver att tjänster
som använder API:t visar texten *"This product uses the Census Bureau Data API but is not endorsed or certified by
the Census Bureau."* på en framträdande plats. Texten står i seriernas `license`. Hemsidan ska visa den när
HS-serierna har data.

## Utan nyckel: hoppas över, fäller inte veckojobbet

`ai_tracker.keyed` håller reda på vilka serier som kräver vilken nyckel. Så länge `CENSUS_API_KEY` saknas gäller
följande:

- Hämtningen avbryts före varje anrop med `keyed.MissingKey`. `observations.refresh` rapporterar `SKIPPED`, inte
  `FAILED`. Ingenting skrivs, inte heller i hämtloggen. Det är viktigt: en hämtning som lyckas utan en period gör att
  perioden senare dateras efter den hämtningen.
- `warehouse.fresh` hoppar över serierna, så aktualitetskontrollen fäller inte jobbet.
- `pipeline weekly` skriver en notis ("35 series skipped: CENSUS_API_KEY is not set …").

När nyckeln finns hämtas och kontrolleras serierna som alla andra katalogserier.

## Vad nyckeln låser upp och hur den läggs in

**Låser upp:** de 35 månadsserierna per HS-kod och land, från 2013-01. Med samma nyckel går det också att hämta
end-use per land och månad från 2010 (`intltrade/imports/enduse`, variabeln `I_ENDUSE`) och Census M3 från
primärkällan. Inget av det är byggt.

**Lägga in nyckeln (ägaren, cirka 5 minuter):**

1. Registrera en gratis nyckel på `api.census.gov/data/key_signup.html` (namn eller organisation och e-post).
   Aktivera den med länken i mejlet. En nyckel som inte är aktiverad ger samma omdirigering som en saknad nyckel.
2. GitHub: Settings → Secrets and variables → Actions → New repository secret, namn `CENSUS_API_KEY`.
   `fetch-weekly.yml`, `nowcast.yml` och `snapshot.yml` skickar den redan som miljövariabel.
3. Molnsessioner: samma värde som miljövariabeln `CENSUS_API_KEY` i miljön, eller i `.env` lokalt. Nyckeln
   committas aldrig.
4. Kör `Weekly data fetch` för hand en gång. Första hämtningen är backfill för 2013-01 och framåt.

**Kontrollera vid första hämtningen med nyckel:** att svaret har kolumnerna ovan, att månader utan post är få och
rimliga (annars ändras nollregeln före användning), att 8471 + 8473.30 per land summerat över 2025 ligger nära
end-use 21300 + 21301 i årsfilen (koderna bygger på HS men är inte identiska) och att `LAST_UPDATE` för senaste
månaden ligger på FT-900:s releasedag.

## Kontroll mot Census publicerade tabeller (2026-11-24)

Årsfilen hämtades i spårets `data/` (21 serier × 10 år = 210 rader, källa `backfill`). Datatesterna i
`warehouse.py` passerar på hela vyn (basen och spåret, 499 serier), och ingen av M2-serierna är för gammal.
Handkontroll mot FT-900:s årsrevision 2025 (`finalxlsx_2025.zip`, publicerad 2026-06-09):

| Värde | Vår serie | Census tabell | Census |
|---|---|---|---|
| Import av datorer 2025, hela världen | `us_imp_eu21300_world_a` = 218 217 | Exhibit 7, *Computers*, Annual 2025 | 218 217 |
| Taiwan 2025, summa över alla end-use-koder i årsfilen | 201 369,2 | Exhibit 13, *Taiwan*, Imports | 201 369,2 |

Exhibit 7 är säsongsrensad, men årssummorna är desamma som i årsfilen (ej säsongsrensad). Även 2023 och 2024 och
koderna 21301 och 21320 stämmer på miljonen. Taiwans summa stämmer också för 2024 (116 284,9) och med vår månadsserie
`us_imports_tw_m` summerad över 2025. Mexikos summa stämmer med Exhibit 13 (534 314,9).

## Förregistrering och vad som setts före den

Registerposten committades (`d9f4993`) före koden (`be3576e`) och före hämtningen. Före registerposten såg spåret
bara struktur: kolumner, koder och beskrivningar i årsfilen, att alla 21 kombinationer finns och saknar tomma
celler, och första radens värde (*Green coffee*). Vid genomgången av FT-900:s bilagor syntes dessutom värden för
september 2026 i Exhibit 8 (datorer, datortillbehör och halvledare för hela världen, säsongsrensat) och i
Exhibit 16a (ATP per land). Det är inte de registrerade serierna, men innehållet är närliggande. Det redovisas här.

## Värdar

`www.census.gov` och `api.census.gov` (metadata) användes. `web.archive.org` nekas av proxyn.
