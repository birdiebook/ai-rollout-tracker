# Källor: BNP-bidrag, datorimport och priser från BEA och BLS (spår M1)

Byggt och hämtat 2026-11-24. Det är förslag 4 i [riktning.md](../riktning.md), makrokanalen. Måtten är beskrivande och
blir inte kärnserier. Om de ska ingå i en grens index är det ett G-A-beslut senare.

**Ordning (förregistrering):** definitionerna och dateringsreglerna committades först
([mattregister.md](../mattregister.md), "M1: AI-relaterat bidrag …", commit `d5b9db5`). Koden och testerna
committades sedan (`dcab019`), före första hämtningen av riktiga värden. Före registreringen lästes bara
tabellhuvuden och det senaste kvartalets värde i BEA:s förhandsberäkningar för 2026Q3 och 2017Q3, och de senaste
16 månaderna i BLS-filerna för de fyra prisserierna, för att hitta koder och filformat. Tre faktauppgifter i
registerposten var fel och är rättade i en egen post efteråt. Reglerna ändrades inte.

## Sammanfattning

| Nyckel | Gren | Källa (kod) | Frekv. | Historik | known_from | Typ |
|---|---|---|---|---|---|---|
| `ai_invest_contrib_gross` | G5 | BEA tabell 1.5.2, rad 31 + 38 (`Y034RY` + `B985RY`) | Q | 1947Q2– | "Data published" per release | release (riktiga vintages) |
| `us_gdp_contrib_info_proc_eq` | G5 | tabell 1.5.2 rad 31 (`Y034RY`) | Q | 1947Q2– | som ovan | release |
| `us_gdp_contrib_computers` | G5 | tabell 1.5.2 rad 32 (`B935RY`) | Q | 1959Q2– | som ovan | release |
| `us_gdp_contrib_software` | G5 | tabell 1.5.2 rad 38 (`B985RY`) | Q | 1959Q2– | som ovan | release |
| `us_gdp_real_growth` | G5 | tabell 1.5.2 rad 1 (`A191RL`) | Q | 1947Q2– | som ovan | release |
| `us_imp_computers_nom` | G6 | tabell 4.2.5 och 4.2.5A/B (`B852RC`) | Q | 1972Q1– | som ovan | release |
| `us_imp_computers_real` | G6 | tabell 4.2.6 och 4.2.6B (`B852RX`) | Q | 2007Q1– (i dagens vintage) | som ovan | release |
| `us_imp_computers_contrib_imp` | G6 | tabell 4.2.2 rad 35 (`B852RZ`) | Q | 1972Q1– | som ovan | release |
| `us_cpi_electricity_nsa_m` | G7 | BLS `CUUR0000SEHF01` | M | 1952-01– | releasedag | release / backfill |
| `us_cpi_electricity_sa_m` | G7 | BLS `CUSR0000SEHF01` | M | 1952-01– | senaste revidering | backfill (årets månader release) |
| `us_ppi_data_processing_m` | G4 | BLS `PCU518210518210` | M | 2000-12– | release m + 4, preliminära: filens datum | backfill |
| `us_ppi_elec_commercial_m` | G7 | BLS `PCU22112222112242` | M | 1958-01– | som ovan | backfill |

Alla har `publish=True` (amerikanska federala verk, se Licenser). Warehouse-kontrollerna passerar på spårets vy.
KPI-serierna har en känd lucka i oktober 2025 (`warehouse.KNOWN_GAPS`).

## BEA: releasearkivet ger riktiga vintages

**Var:** BEA:s dataarkiv, `apps.bea.gov/histdata` ("National Accounts (NIPA)"). Arkivsidan hämtar sin katalogträdslista
från en egen JSON-tjänst (`histdata/core/data/Fea_DisplayChildrenC/?HistMainId=7&getDirs=true`). Varje BNP-release har
en katalog `GDP_and_PI/<år>/<kvartal>/<Vintage>_<Månad-D-ÅÅÅÅ>/` med alla NIPA-tabeller som de publicerades, en
arbetsbok per avsnitt (`Section1all_xls.xlsx`, `Section4all_xls.xlsx`). Ingen nyckel behövs. Den senaste releasen läses
också från `apps.bea.gov/national/Release/XLS/Survey/` (xlsx trots namnet), om arkivet skulle släpa efter.

**Vintages:** 107 releaser från 2017-10-27 (förhandsberäkningen för 2017Q3) till 2026-10-29. Releaserna 2002–2017 finns
bara som .xls, och projektet har ingen läsare för det formatet. Värden som publicerades före 2017-10-27 får det datumet,
vilket är konservativt. Varje release ger en rad per kvartal som är nytt eller ändrat (`observations.vintage_rows`),
med en median på 7 rader per kvartal 2017Q4–2025Q4. Ett utdrag per release cachas i `<RAW_DIR>/bea/vintages/`, så att
varje arbetsbokspar (cirka 5,5 MB) bara laddas ned en gång. Första hämtningen tog cirka 3 minuter.

**Koder i stället för radnummer.** Koden (`Y034RY` osv.) läses ur kolumn 3 i tabellen. Radnummer och tabellnamn
ändras: 4.2.5 och 4.2.6 delades i A (1967–1998) och B (från 1999). Delade tabeller slås ihop, och om värdena i
överlappet skiljer sig avbryts läsningen.

**known_from = "Data published" i tabellhuvudet.** Katalognamnet är uppladdningsdagen och avviker i nästan alla
releaser. Oftast ligger katalogen 1–3 dagar efter publiceringen (t.ex. katalog 2018-01-29, publicerad 2018-01-26),
men i två fall ligger den före: 2025Q3 (katalog 2025-12-22, publicerad 2025-12-23) och 2023Q1 Third (katalog
2023-06-20, publicerad 2023-06-29). Med katalogdatumet hade två releaser läckt. En kontroll avbryter om avståndet är
större än 14 dagar eller om datumet ligger före kvartalets slut.

**Fallgrop:** en fil som saknas besvaras med HTTP 200 och en HTML-sida ("BEA: Data Tools"). Läsaren kräver därför att
filen är en zip-fil (xlsx) innan den tolkas.

**Ingen nettovariant.** BEA publicerar importens bidrag till BNP-tillväxten bara för varor och tjänster (tabell 1.5.2,
rad 49–51). För datorer, kringutrustning och delar finns bara bidraget till den reala importens tillväxt (tabell 4.2.2,
`B852RZ`). Att räkna om det till ett BNP-bidrag med importens andel av BNP vore vår egen approximation, eftersom
Fisher-vikterna skiljer sig mellan aggregaten. Den är inte registrerad. Datorimporten visas i stället separat, nominellt,
realt och som bidrag till importtillväxten.

**Kedjade dollar:** basåret följer vintage (2009, 2012 och sedan 2017 dollar). `us_imp_computers_real` jämförs därför
bara inom en vintage, och en omläggning syns som en revidering av hela serien. Kedjade nivåer är inte additiva.

## BLS: flatfiler och BLS egna releasedatum

**Värdar:** `download.bls.gov` och `www.bls.gov` nekar klienter utan kontaktuppgift (Akamai "Access Denied", med
hänvisning till BLS regler för automatiserad hämtning). Med projektets generiska klientidentitet i User-Agent, samma
som för SEC (`SEC_USER_AGENT` i `.env` och som Actions-secret), svarar båda med 200. `http.user_agent` skickar den
till `*.bls.gov`. API:t (`api.bls.gov`) behövs inte. Dess dagskvot för den delade utgående IP-adressen var slut
2026-11-24 (`REQUEST_NOT_PROCESSED`, "daily threshold"), och flatfilerna ger hela historiken i ett anrop.

**Filer:** `cu/cu.data.12.USHousing` (KPI, 2,7 MB), `pc/pc.data.56.ISPsSearchPortandDataProcess` och
`pc/pc.data.46.Utilities` (PPI). Kolumner: series_id, year, period (M01–M12, M13 = årsmedel, läses inte), value och
footnote_codes. `-` med fotnoten X betyder att värdet saknas (oktober 2025).

**Releasedatum:** `www.bls.gov/bls/news-release/cpi.htm` och `ppi.htm` listar varje nyhetsrelease från referensmånad
1999-05, med releasedagen i filnamnet (`cpi_11102026.htm`). Det är primärkällan, så ALFRED behövs inte. Oktober 2025
står som "Not published because of 2025 lapse in federal government appropriations". KPI kom 10–30 dagar efter
månadens slut 2003–2025, med median 15 dagar. Det längsta var september 2013 (nedstängningen, 30 dagar).

**Dateringsregler** (registrerade före beräkningen). Filen är vintage för sin senaste release: filens datum =
max(senaste releasedag i arkivet, filens Last-Modified).
- **KPI NSA:** "The CPI-U and CPI-W are considered final when released" (KPI-releasen 2026-11-10). known_from =
  referensmånadens releasedag (`release`). Fotnoten R ger filens datum.
- **KPI SA:** "These factors are updated each February, and the new factors are used to revise the previous 5 years of
  seasonally adjusted data", och för januari 2026 reviderades 2021–2025. Ett värde för år y får releasedagen för
  januari-KPI år y + 5, eller den senaste januari-releasen. Årets månader får sin egen releasedag.
- **PPI:** "All PPIs are subject to monthly revisions up to 4 months after original publication" (PPI-releasen
  2026-11-13, som reviderade juni–september). Preliminära värden (P) får filens datum, slutliga värden releasedagen för
  m + 4. Ett slutligt PPI-värde är därför känt 129–198 dagar efter månadens slut 2003–2025. Det är konservativt: det
  först publicerade värdet finns inte kvar i filen.
- En månad utan egen release får nästa release. Månader före arkivet får arkivets första releasedag. Regeldaterade rader
  märks `backfill`, och från andra hämtningen blir varje ändrat värde en `revision` med hämtdatum.

**Gren för PPI 518210: G4.** PPI mäter priset som producenterna får, här moln-, hosting- och databehandlingsbolagen. Det
är priskomponenten i deras intäkter, och det hör till G4 ("Går det att tjäna pengar på det?"). G6 gäller
leveranskedjan av hårdvara, och G2 gäller pris per förmåga. Indexet säger inget om pris per beräkningsenhet.

**Elpris för kommersiella kunder** (`PCU22112222112242`) i G7, samma kundsektor som EIA:s kommersiella elpris, där de
flesta datacenter finns. Industriell el (`PCU22112222112243`) finns i samma fil om den behövs.

**Lagras från 1952-01:** KPI för el (NSA) har bara enstaka månader före 1952 (decembervärden från 1913). SA-serien börjar
också 1952-01.

## Kontroller

| Kontroll | Resultat |
|---|---|
| BEA: senaste vintage mot flatfilen `NipaDataQ.txt` (en oberoende BEA-fil) | alla 7 koder lika över hela historiken (största skillnad 0,0) |
| BEA: releasetexten för 2026Q3 ("GDP (Advance Estimate), 3rd Quarter 2026", 2026-10-29) | texten: 3,4 procent i årstakt, 2,2 procent kvartalet före. Vintage 2026-10-29: `A191RL` 3,4 och 2,2. Texten säger att ökningen inom utrustning leddes av informationsbehandlingsutrustning, "mainly computers and peripheral equipment", vilket stämmer med att `B935RY` är största delen av `Y034RY` |
| BEA: publiceringsdatum mot `LATE` i `series/bea_nipa.py` (ALFRED-belagda sena releaser) | 2018Q4 2019-02-28, 2025Q3 2025-12-23, 2025Q4 2026-02-20: lika |
| BEA: första skattningen efter kvartalets slut | 25–84 dagar, median 28. Över 31 dagar: 2018Q4 (59), 2025Q4 (51), 2025Q3 (84) |
| BLS KPI: releasen 2026-11-10, tabellen för el | ojusterat index september 309,852 och oktober 307,673: lika. SA-förändring september–oktober 0,9 procent mot vår 0,94 |
| BLS PPI el, kommersiella kunder: releasen 2026-11-13, tabell 2 (råvarukod 05-42) | ojusterad 12-månadersförändring 0,6 procent mot vår 0,62 |
| BLS PPI 518210 | **ej verifierad mot en oberoende BLS-källa.** Indexet finns inte i nyhetsreleasen, API-kvoten var slut och `data.bls.gov` nekas av proxyn |
| `python -m ai_tracker.warehouse` på spårets vy | alla datatester ok (basen var tom vid körningen) |

**Revideringar, beskrivande:** för `ai_invest_contrib_gross` var skillnaden mellan första och senaste värde i
genomsnitt 0,14 procentenheter och högst 0,45 (33 kvartal, 2017Q4–2025Q4). Inga takter är beräknade.

## Förbehåll

- **Kategorierna är bredare än AI.** Informationsbehandlingsutrustning omfattar alla datorer, kommunikationsutrustning,
  instrument och kontorsutrustning. Programvara omfattar all köpt, beställd och egenutvecklad programvara, men inte
  programvara som ingår i köpt utrustning (BEA:s fotnot 4). Datorimporten omfattar också persondatorer och tillbehör.
  Ett bidrag på x procentenheter betyder inte att AI bidrog med x.
- **Bidragen är avrundade** till två decimaler. Summan i `ai_invest_contrib_gross` kan avvika 0,01 procentenhet.
- **Årliga och omfattande revideringar** ändrar hela historiken, särskilt prisindex för datorer och programvara. Varje
  sådan release syns som en ny vintage.
- **Ingen kvot mot BNP-tillväxten:** den blir instabil när tillväxten är nära noll.
- **KPI SA och PPI är regeldaterade.** Reglerna följer BLS egna texter, men en extra revidering utanför reglerna skulle
  läcka in. Från andra hämtningen fångas varje ändring som en revision med hämtdatum.

## Licenser

- BEA: amerikanskt federalt verk, fritt enligt 17 U.S.C. § 105. BEA:s sida med riktlinjer för källhänvisning gick att
  läsa men säger inget om licens. Samma licenstext som de befintliga BEA-serierna.
- BLS (`www.bls.gov/opub/copyright-information.htm`): "You are free to use our public domain material without specific
  permission, although we do ask that you cite the Bureau of Labor Statistics as the source."

## BLOCKED och öppet

| Vad | Orsak | Vad som löser det |
|---|---|---|
| BLS API | dagskvoten för den delade IP-adressen slut (25 anrop per dag utan nyckel) | behövs inte, flatfilerna räcker. En v2-nyckel om API:t behövs för G8 |
| `data.bls.gov` | proxyn nekar | – (behövs inte) |
| BEA-vintages 2002–2017 | arkivet har bara .xls | en .xls-läsare (`xlrd`) om längre historik behövs |
| Nettobidrag efter import | BEA publicerar inget BNP-bidrag för datorimport | eget, registrerat approximationsmått, om ägaren vill |
| Census HS 8471/8473/8542 | Census API-nyckel saknas | spår M2 |

De befintliga serierna `us_pfi_*` (flatfilen, bakåtfylld) skulle kunna få riktiga vintages ur samma arkiv (tabell 5.3.5).
Det ändrar källan för serier som modellerna läser, så det kräver ett beslut och en ny registrerad variant.
