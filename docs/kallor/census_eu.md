# Källor: Census, BEA, ALFRED, Eurostat och SCB (spår I3, fas 2)

Byggt och hämtat 2026-11-23 med den ärliga klienten i `ai_tracker.http`. Källkarta från fas 1:
[`g3_g4_g5.md`](../datakallor/g3_g4_g5.md) och [`g6_g7_g8.md`](../datakallor/g6_g7_g8.md).
Här beskrivs bara hur varje serie hämtas och dateras. Inga trender har analyserats, och måtten förregistreras senare.

Källtyper i observationstabellen:

- `release`: värdet har ett eget publiceringsdatum från källan.
- `backfill`: dagens vintage, daterad med en regel, och revideringar läcker in.
- `revision`: ett ändrat värde, daterat till hämtdagen.

## Sammanfattning

| Nycklar | Gren | Källa | Frekv. | Historik | known_from | Typ |
|---|---|---|---|---|---|---|
| `btos_ai_use_v1/v2/v3`, `btos_ai_expect_v1/v2/v3` (+ `_se`) | G3 | Census BTOS | 2W | v1 202319–202520 (54), v2 202524–202621 (24), v3 från 202622 (2) | Publication Date i filen | release |
| `us_constr_datacenter`, `_nsa` | G5 | Census C30 | M | 2014-01– | max(månadsslut + 35 d, belagd release) | backfill |
| `us_ip_semis_m` | G6 | Fed G.17, federalreserve.gov (G3344) – flyttad i spår I7, se [fed_g17.md](fed_g17.md) | M | 1972– | releasedatum | release (riktiga vintages) |
| `us_orders_computers_electronics_m` | G6 | Census M3 via ALFRED (A34SNO), interim i väntan på Census API-nyckel | M | 1992– | ALFRED-vintage | release (riktiga vintages) |
| `us_pfi_info_proc_eq_sw`, `us_pfi_info_proc_eq`, `us_pfi_computers`, `us_pfi_software` | G5 | BEA NIPA-flatfiler | Q | 1947/1959– | max(kvartalsslut + 31 d, belagd release) | backfill |
| `us_imports_tw_m`, `us_imports_kr_m` | G6 | Census FT-900 `country.xlsx` | M | 1985– | max(månadsslut + 41 d, belagd release) | backfill |
| `eu_ai_ent_eu27`, `_se`, `_de`, `_fr` | G3 | Eurostat `isoc_eb_ai` | A | 2023– | 31 dec + 31 d | backfill |
| `scb_ai_ent_se` | G3 | SCB TAB6405 | A | 2023–2025 | 31 dec referensåret | backfill |
| `scb_ai_ent_se_nace21` | G3 | SCB TAB6814 | A | 2026– | 11 nov referensåret | backfill |

Alla warehouse-kontroller passerar på den hämtade tabellen. De kräver inga undantag i `KNOWN_GAPS`.

**"Belagd release"**: första ALFRED-vintage där perioden finns, för en serie i samma release (TLPRVCONS för C30,
IMP5830 för FT-900 och A679RC1Q027SBEA för BEA). Den används bara som bevis på publiceringsdag, inte som data.
Releaser som kom senare än lagregeln står i `LATE` i respektive seriemodul och registreras i
`publication.LATE_RELEASES`. Saknar ALFRED en vintage blir datumet för sent, vilket är konservativt.

## Census BTOS (G3)

**Filer:** `National.xlsx` innehåller den nuvarande frågan, Q7 (användning) och Q28 (förväntad användning
kommande sex månader), samt fliken *Collection and Reference Dates* med *Publication Date* per cykel.
Fliken täcker även cyklerna före frågebytet. `AI Core Questions.xlsx` innehåller den gamla frågan (Q7 och Q24)
för 202319–202520 och saknar publiceringsdatum. Värdena är andelar "Yes" i procent, med standardfel i en egen
serie (`_se`, publiceras inte).

**known_from** = *Publication Date*, alltså 4 dagar efter att insamlingen slutat (t.ex. 202622: insamling
2026-10-19–11-01, publicerad 2026-11-05). Framtida cykler står också i filen (202624 → 2026-12-03).
Publiceringsdatumen för v1 tas från `National.xlsx`, eftersom `AI Core Questions.xlsx` saknar dem.
**Rättat i X1 (2026-11-23):** kolumnen är en tidsplan, inte ett utfall. En cykel vars planerade dag ligger under en
finansieringslucka (2025-10-01–11-12) får `known_from` dagen efter luckan, 2025-11-13. Det gäller cykel 202520
(planerad 2025-10-09). Den faktiska dagen är inte belagd (R1, avsnitt 3.6), och när den är det läggs den i
`census_btos.PUBLISHED`. Varje hämtning sparar tidsplanen med hämtdatum i `data/raw/census_btos/schedule_log.parquet`,
så att tidsplan och utfall kan skiljas åt i efterhand.

**Period och frekvens:** ny frekvens `2W` (ISO-fjortondag). Värdet lagras på den W-SUN-vecka då
insamlingen slutar. Det följer Census egen cykelnumrering (smpdt = ISO-år + fjortondag 01–26).
`no_gaps` numrerar fjortondagarna som ISO-år × 26 + fjortondag (`observations.fortnight_ordinal`).
Då blir även år med 53 veckor rätt: 202626 är 21 dagar (2026-12-14 till 2027-01-03). Med vanlig `W` hade
varannan vecka varit tom, och en saknad cykel hade inte kunnat upptäckas.
Frågan avser referensperioden, alltså de två veckorna *före* insamlingen. Det står i modulens docstring.

**Regimbrott, tre separata serier som aldrig skarvas:**

| Version | Cykler | Lydelse | Belägg |
|---|---|---|---|
| v1 | 202319–202520 | "use Artificial Intelligence (AI) in producing goods or services?" | `AI Core Questions.xlsx` |
| (saknas) | 202521–202523 | ingen insamling | Data Dictionary: federal nedstängning 2025-10-01–11-13, "no data are available for these cycles" |
| v2 | 202524–202621 | "use Artificial Intelligence (AI) in any of its business functions?" | `AI Question Wording Updates.pdf` (2025-12-03): ny lydelse från 2025-11-17, och Census startade själv "a new time series ... beginning with data released on December 4, 2025" på grund av en nivåförskjutning |
| v3 | 202622–202701 | "use Super Intelligence or SI (formerly referred to as Artificial Intelligence or AI) in any of its business functions?" med nya exempel ("SI-powered data analysis; generative SI for marketing ...") | se nedan |

**"Super Intelligence or SI (formerly … AI)"** är ingen etikett som bara finns i filen. Respondenterna ser den.
Frågeformuläret `BTOS Content V5 Core and SI Instrument - Cycle 2-Tagged.pdf` ("Content Year 5, Cycle 2 with
SI Supplement, Fielded 10/19/2026 – 01/17/2027") använder termen i Q24–Q36, med fotnoten "(Updated 10/19/26) SI
Definition: Computer systems and software that are able to perform tasks normally requiring human
intelligence …". 2026-10-19 är första insamlingsdagen i cykel 202622. Samtidigt byttes exemplen i frågan ut,
och nya frågor tillkom (Q8 om anställdas generativa SI, Q9–Q10 om effekter på antal anställda, alla från
202622). Respondenterna fick alltså en ny term, nya exempel och ett nytt frågesammanhang. Det räknas som brott,
och därför är v3 en egen serie. `National.xlsx` visar bara den senaste frågetexten för alla cykler, så
v2-värdena står där under SI-texten, trots att de samlades in med AI-lydelsen.

**Nästa kända ändring:** `BTOS Content V5 Core Round 3, 4.pdf` ("Fielded 01/18/2027 – 04/11/2027", alltså från
cykel 202702) behåller SI-termen men byter tillbaka exemplen till "machine learning, natural language
processing, virtual agents, voice recognition". v3 slutar därför vid 202701. Cykler efter den sista granskade
regimen lagras inte. `build()` varnar, och en ny regim läggs till efter granskning. Det är en beslutspunkt
från februari 2027: om bytet av exempel räcker för en ny serie v4. **Rekommendation: ny serie**, eftersom
regeln är densamma som för v2→v3.

**Skydd:** fetch kontrollerar att filens frågetext innehåller den senaste regimens term (v1: "in producing
goods or services", v3: "Super Intelligence or SI (formerly …)"). Om Census byter text utan att vi har en regim
avbryts hämtningen, i stället för att serien skarvas tyst.

**Revideringar:** filerna skrivs över och har ingen versionshistorik. Att BTOS inte revideras går inte att
verifiera. Release-daterade rader som får ett nytt värde med samma publiceringsdatum blir därför en
`revision` daterad till hämtdagen (`observations.new_rows`, ny regel för release-daterade källor). v1-värdena
kommer ur en senare sammanställd fil (*AI Core Questions (Original)*). Om de skiljer sig från de först
publicerade värdena går inte att se, vilket är en liten läckagerisk.

## Census Construction Spending, datacenter (G5)

**Fil:** `privsatime.xlsx` (SAAR) och `privtime.xlsx` (NSA), kolumnen *Data center*, MUSD, från 2014-01.
Månader märks `p` (preliminär, senaste månaden) och `r` (reviderad, de två föregående).

**known_from** = max(månadsslut + 35 dagar, belagd release). Release sker första arbetsdagen kl. 10 ET.
ALFRED-vintages för TLPRVCONS visar 29–35 dagar 2011–2026 i normalfallet. Filen anger själv
"Construction Spending, November 2, 2026", och Census kalender listar 2027-01-04 för november 2026.
Senare releaser i `LATE`: 2018-11–2019-01 (nedstängningen 2018–19) och 2025-08–2026-03 (nedstängningen 2025
och efterföljande kompakterat schema, t.ex. september och oktober 2025 båda 2026-01-21).

**Första publicering (rättat i X1, 2026-11-23):** kategorin Data center publicerades separat första gången med
majreleasen 2024-07-01, bakåt till 2014-01 (pr202403.pdf, pr202404.pdf, pr202405.pdf och pdf/news.pdf, se
[R1](../granskning/r1_lackage.md), avsnitt 3.1). Månaderna 2014-01–2024-04 har därför `known_from` 2024-07-01
(`census_c30.FIRST_PUBLISHED`, lagt i `LATE`). Tidigare fick de månadsslut + 35 dagar, alltså ett datum innan
serien fanns.

**Revideringar och läckage:** filen har bara senaste vintage, så allt före vår första hämtning är backfill med
p/r-revideringar och årsrevisioner (majreleasen i juli reviderar NSA cirka 2 år bakåt och SA cirka 7 år bakåt).
**Säsongsrensningen läcker också:** `privsatime.xlsx` är skattad med dagens säsongsfaktorer, som bygger på data
efter varje historisk månad. Den SA-historik som en backtest ser 2024-07-20 är alltså inte den som publicerades
då. Den ej säsongsrensade serien (`_nsa`) har bara revideringsläckaget. Att byta V1/V2 i N1 till `_nsa` kräver en
ny registrerad variant. Från andra hämtningen och framåt blir varje ändring en `revision` med hämtdatum.

## Fed G.17 och Census M3 via ALFRED (G6)

**Uppdatering 2026-11-23 (spår I7):** G.17 hämtas nu från primärkällan med riktiga vintages ur Fed:s
releasearkiv, se [fed_g17.md](fed_g17.md). ALFRED-modulen gäller bara M3 (`series/census_m3_alfred.py`). Den är
märkt som interimskälla med `publish=False` tills en Census API-nyckel finns. Texten nedan beskriver läget i spår I3.

`federalreserve.gov` **nekas av proxyn**, och värden behöver öppnas för att G.17 ska kunna hämtas från primärkällan. Census M3 är bara
maskinläsbar via `api.census.gov`, som kräver nyckel. Exportfunktionen i `econ/currentdata` gav HTTP 400, och
historiksidan har bara PDF-pressmeddelanden. ALFRED ger **riktiga vintages utan nyckel**:
`series/downloaddata?seid=<id>` listar vintage-datum, och `graph/alfredgraph.csv?id=<id>,<id>…&vintage_date=<d1>,<d2>…`
ger högst 12 vintages per anrop. `sources/alfred.py` sparar en rad per (period, vintage) när värdet är nytt eller
ändrat. IPG3344S har 151 vintages från 2015-02-18, A34SNO 376 från 2011-06-24 (förhandsrapport och fullständig
M3-rapport).

**known_from** = vintage-datumet. Värden från före första vintage får det första datumet, vilket är konservativt.
Första publicering: G.17 14–18 dagar efter månadens slut, M3 (förhandsrapporten om varaktiga varor)
21–29 dagar.

**Licens:** FRED/ALFRED-villkor, märkningen "Public Domain: Citation Requested". `publish=False` tills vidare,
eftersom beslutet att föredra primärkällor bygger på att FRED:s villkor begränsar viss användning. Öppnas
`federalreserve.gov` kan G.17 i stället hämtas från primärkällan.

## BEA, privata investeringar i IT (G5)

**Fil:** `apps.bea.gov/national/Release/TXT/NipaDataQ.txt` (35 MB, ingen nyckel) med koderna A679RC
(informationsbehandlingsutrustning och programvara), Y034RC (utrustning), B935RC (datorer och kringutrustning)
och B985RC (programvara). Enheten är MUSD, SAAR, löpande priser, och koderna och etiketterna står i `SeriesRegister.txt`.

**known_from** = max(kvartalsslut + 31 dagar, belagd release). Förhandsberäkningen kom 25–31 dagar efter
kvartalet 2013–2026 (ALFRED A679RC1Q027SBEA). Senare releaser i `LATE` är 2013Q3, 2018Q4, 2025Q3 (2025-12-23) och 2025Q4.

**Läckageflagga:** flatfilerna har bara senaste vintage. Hela historiken är backfill med andra och tredje
skattning, årsrevisioner och omläggningar. Det gäller särskilt programvara och datorer, där BEA ändrar
prisindex och definitioner vid omläggningarna. Riktiga vintages finns i ALFRED (A679RC1Q027SBEA m.fl.) och via
BEA API, som kräver UserID. Det är ett möjligt nästa steg, men det kräver ett beslut eftersom primärkällor föredras.

## USA:s import från Taiwan och Sydkorea (G6)

**Fil:** `www.census.gov/foreign-trade/balance/country.xlsx` (FT-900, landsvis import och export per månad,
MUSD, ej säsongsrensat, från 1985). Taiwan har landskod 5830 och Sydkorea 5800. Månader som ännu inte är
publicerade står som 0 i årets rad och tas bort.

**HS 8471/8473/8542 är BLOCKED:** `api.census.gov` svarar med en 302-omdirigering till `missing_key.html` ("A valid key must be
included with each data API request"). Det som behövs är en gratis Census API-nyckel, som inte har registrerats. Till dess
lagras bara totalimporten.

**known_from** = max(månadsslut + 41 dagar, belagd release). FT-900 kom 32–41 dagar efter månadens slut
2017–2026 (ALFRED IMP5830, vintages från 2017-11). `LATE`: 2018-11–2019-02, 2020-03, 2025-08, 2025-09, 2025-10,
2025-11 och 2025-12. **Rättat i X1 (2026-11-23):** oktober 2025 saknades i `LATE`, eftersom ALFRED:s vintage
2025-12-11 hade platshållaren 0,0 för månaden. Releasen kom 2026-01-08 (ft900_2510.pdf). `alfred.first_release()`
och `release_rows()` räknar nu inte 0,0 som ett publicerat värde. Övriga ALFRED-härledda datum (TLPRVCONS för C30,
A679RC1Q027SBEA för BEA, A34SNO, IPG3344S) är kontrollerade i de sparade vintagefilerna: inga andra nollor finns.
Före 2017-11 är belägget FT-900-pressmeddelandena (R1 läste alla månader 2006–2017): 2006–2012 kom releasen
42–45 dagar efter månadsslut, så månader före 2013 får månadsslut + 45 dagar (före 2006 overifierat, samma regel).
Nedstängningen 2013 ligger i `LATE` (2013-08 → 2013-10-24, 2013-09 → 2013-11-14). Årsrevisioner gör hela
historiken till backfill.

## Eurostat `isoc_eb_ai` (G3)

`E_AI_TANY` (minst en AI-teknik), företag med 10+ sysselsatta, `C10-S951_X_K`, procent av företag, för EU27, SE,
DE och FR. USA ingår inte i undersökningen. Serien börjar 2023: 2021 hade en annan teknikförteckning, och 2022
ställdes frågan inte, så 2021 blir en ensam punkt med lucka. Flaggan `b` (brott) finns för SE och FR 2023, alltså
vid seriens start. Parsern stoppar om en brottsflagga dyker upp senare i serien, och då ska serien delas.

**Definition 2025:** "minst en" omfattar från 2025 en åttonde teknik, generering av bild, video och ljud
(`E_AI_TPVSG`, som bara har värden för 2025). Eurostat flaggar inget brott, men definitionen breddas något.
Det dokumenteras här, och serien delas inte, eftersom källan själv inte markerar brott.

**known_from** = 31 dec referensåret + 31 dagar. ESMS 8.1: "The target is to release data within the survey year
in December." Strukturen för 2025 uppdaterades 2025-12-11 och data senast 2026-06-15. API:t har bara senaste
versionen, så EU27-aggregatet och sena länder kan ha reviderats efter första publiceringen. Det är
backfill-läckage. 2026 (NACE Rev. 2.1) är inte publicerat. Byter Eurostat aggregatkod kommer serien att sluta och behöver granskas.

## SCB, AI i företag (G3)

API v2, `TypAvTeknik=0080` (minst en AI-teknik), `Redovisningsgrupp=Tot250` (10 eller fler anställda), andel i procent.

**Två serier, inte en sammanfogad.** Uppdraget var att foga ihop TAB6405 och TAB6814, men det gjordes inte. Skälet är att
TAB6814 (2026) täcker en annan population: NACE Rev. 2.1 och "samtliga undersökta näringsgrenar", alltså även
A (jordbruk), B (utvinning) och K (finans) med flera, medan TAB6405 täcker SNI 10–63, 68–75, 77–82 och 95.1.
Gruppen "totalt 10 eller fler anställda" har samma storleksdefinition men en bredare branschtäckning, och
näringsgren 68 är bara imputerad för 10+ (tabellnoten). Ett steg mellan 2025 och 2026 vore därför inte en
jämförbar förändring. De kan skarvas i ett förregistrerat mått om det beslutas.

| Nyckel | Tabell | År | known_from | Belägg |
|---|---|---|---|---|
| `scb_ai_ent_se` | TAB6405 | 2023–2025 (2021 = `..`, 2022 saknas; SNI 75 ingår från 2023) | 31 dec referensåret | publiceringsdag för 2023–2024 ej belagd, så regeln är konservativ. Serien är avslutad, och det kostar inget |
| `scb_ai_ent_se_nace21` | TAB6814 | 2026– | 11 nov referensåret (`lag_days = −50`) | tabellens `updated` 2026-11-05T07:00Z |

**Korrigeringen 2026-05-05:** noten i TAB6405 lyder "Uppgifter för redovisningsgruppen Företag, 0-9 anställda har
korrigerats avseende referensår 2025". Den gäller 0–9 anställda, inte `Tot250`, så våra serier påverkas inte. De
okorrigerade värdena finns inte kvar i API:t, eftersom det saknar versionshistorik. Därför kan korrigeringen inte
lagras som revision, och det skulle bara gå för en serie för 0–9 anställda om de gamla värdena fanns arkiverade.

## Ramverksändringar i spåret

- `catalog.FREQS["2W"]` och `observations.fortnight_ordinal` (BTOS-fjortondagar). `no_gaps` använder den för `2W`.
- `observations.new_rows`: om en release-daterad rad har samma (period, known_from) som en lagrad rad men ett
  nytt värde blir den en `revision` med hämtdatum. Äldre vintages i samma hämtning räknas inte som revisioner.
- Seriemoduler registrerar sina belagda sena releaser i `publication.LATE_RELEASES`, i stället för att redigera
  `publication.py`.
- `openpyxl` som beroende (xlsx från Census).

## BLOCKED och nycklar

| Vad | Orsak | Vad som löser det |
|---|---|---|
| ~~G.17 från primärkälla~~ | löst i spår I7: `www.federalreserve.gov` är öppen | [fed_g17.md](fed_g17.md) |
| HS 8471/8473/8542, M3 från primärkälla | `api.census.gov` kräver API-nyckel (gratis registrering) | Census API-nyckel (registreras inte av agenten) |
| BEA-vintages från primärkälla | BEA API kräver UserID | BEA-nyckel, eller ALFRED-vintages efter beslut |
| `www.bls.gov`, `download.bls.gov` | HTTP 403 (behövdes inte i spåret) | – |

Värdar som användes: `www.census.gov`, `apps.bea.gov`, `alfred.stlouisfed.org`, `ec.europa.eu`,
`statistikdatabasen.scb.se`. `api.stlouisfed.org` nås men kräver nyckel, och användes inte.
