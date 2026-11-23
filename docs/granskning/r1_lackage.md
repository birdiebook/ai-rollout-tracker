# R1: oberoende granskning av läckage och datering

Granskningsspår R1, 2026-11-23. Underlaget är `data/observations.parquet` (68 serier, en hämtning 2026-11-23) och
koden på `main` (ba27f21). Granskningen är adversariell: varje `known_from` har jämförts med publiceringsdagen
enligt källan själv, inte med den källa som spåren själva använde (ALFRED). Inga produktionsfiler är ändrade.
Tester finns i `tests/test_r1_leakage.py`. Där är tester som visar ett verkligt fel markerade
`xfail(strict=True)`, så att sviten är grön och felet syns. När felet rättas ska markeringen tas bort.

Hämtningar gjordes med den ärliga klienten (`ai_tracker.http`, generisk User-Agent, SEC-identitet från `.env`).
Proxyn nekade `api.github.com`, men `git clone` fungerade. `federalreserve.gov` och BEA:s flatfiler prövades inte
på nytt, eftersom de redan är kända som nekade respektive hämtade. Ingen trendanalys gjordes.

## 1. Dom per seriegrupp

| Grupp | Serier | known_from-regel | Dom | Kort motivering |
|---|---|---|---|---|
| SEC 10-Q/10-K | `capex_*`, `ocf_*`, `fin_lease_*`, `rev_*` (17) och `*_hyp4` (3) | inlämningsdag (`filed`) | **OK** | 1 019 perioder: första `known_from` är aldrig före första 10-Q/10-K enligt EDGAR. Alla revideringar är daterade till en verklig senare inlämning |
| TSMC 6-K | `tsmc_revenue_m`, `tsmc_revenue_parent_m` | 6-K:ns filingDate | **OK** | 12 av 12 stickprov stämmer med dokument och värde. IFRS-omräkningen av 2012 är daterad 2013 |
| Census FT-900 | `us_imports_tw_m`, `us_imports_kr_m` | månadsslut + 41 d, `LATE` | **Fel som påverkar (litet)** | 2025-10 är daterad 2025-12-11, men releasen kom 2026-01-08. Påverkar N2 (2025-12 och träningsrader efter den). Före 2013 är regeln 1–4 dagar för tidig i 38 av 84 månader, och nedstängningen 2013 täcks inte. Det påverkar inte N1 eller N2 |
| Census C30 datacenter | `us_constr_datacenter`, `_nsa` | månadsslut + 35 d, `LATE` | **Fel som påverkar (stort)** | Kategorin "Data center" publicerades första gången 2024-07-01. Månaderna 2014-01–2024-04 har `known_from` före det datumet, alltså innan serien fanns. N1 V1/V2 för 2021Q4–2024Q1 bygger på data som inte var publicerad |
| BEA NIPA | `us_pfi_*` (4) | kvartalsslut + 31 d, `LATE` | **OK** | Sju stickprov 2024Q4–2026Q2 mot BEA:s arkiv stämmer, inklusive 2025Q3 (2025-12-23) och 2025Q4 (2026-02-20). Före 2013 saknas belägg, och serierna används inte i någon modell |
| Census BTOS | `btos_ai_*` (12) | Publication Date i filen | **Ej verifierad, troligen fel som inte påverkar** | Kolumnen är en tidsplan, eftersom den också listar framtida cykler. Cykel 202520 har publiceringsdagen 2025-10-09, mitt under nedstängningen (2025-10-01–11-12). Den faktiska dagen gick inte att belägga |
| EIA EPM | `us_elec_sales_com_*` (7) | Last-Modified + 2 d. Före 2012-11: backfill + 90 d | **OK** | 17 av 17 nummer 2024–2026 mot "Release Date" i Electricity Monthly Update. `known_from` ligger 2–13 dagar efter releasen |
| ALFRED G.17 och M3 | `us_ip_semis_m`, `us_orders_computers_electronics_m` | ALFRED-vintage | **OK med förbehåll** | Ett vintagedatum kan inte ligga före releasen. Undantaget är platshållare, se avsnitt 3.2. Inga nollor finns i de här serierna. Inget stickprov mot primärkällan gjordes (federalreserve.gov nekas). Serierna ingår inte i N1 eller N2 |
| Indeed | `ai_postings_share_*` (9) | committid (UTC) | **OK, ej fullt verifierbar** | Alla 32 `known_from` är exakta committider på first-parent, och data slutar alltid före commit. 43 av 58 commits är lokala, och då är pushtiden okänd, eftersom api.github.com nekas. Risken är timmar, inte dagar. Ingen modell använder serierna |
| Epoch × LiteLLM | `g2_price_at_capability(_gpqa)` | backfill (månadsslut) | **Fel som inte påverkar** | Redan flaggat som backfill. `Started at` + 7 d går inte att verifiera. Fem embargokörningar startade före modellens release, men de grindas av releasedatumet. Månadsvärdet bygger på commits under hela sista dagen men dateras till dagens början, alltså ≤ 1 dag för tidigt |
| Eurostat och SCB | `eu_ai_ent_*`, `scb_ai_ent_se*` | 31 dec + 31 d, 31 dec, 11 nov | **Ej verifierad** | Publiceringsdagar för 2023–2025 hittades inte (API:et visar bara senaste uppdatering). Ingen modell använder serierna |

## 2. Belägg (stickprov)

### 2.1 Census FT-900. Källa: `census.gov/foreign-trade/Press-Release/ft900/ft900_YYMM.pdf`, raden "FOR RELEASE"

| Månad | Release enligt Census | `known_from` | Avvikelse |
|---|---|---|---|
| 2013-08 | 2013-10-24 | 2013-10-11 | **−13 d** (nedstängningen 2013, ingen `LATE` före 2017-11) |
| 2013-09 | 2013-11-14 | 2013-11-10 | **−4 d** |
| 2007-12 | 2008-02-14 | 2008-02-10 | **−4 d** (38 av 84 månader 2006–2012 ligger 1–4 d för tidigt, eftersom releasen kom 42–45 d efter månadsslut) |
| 2018-11 – 2019-02 | 2019-02-06, 03-06, 03-27, 04-17 | samma | 0 |
| 2020-03 | 2020-05-05 | 2020-06-04 | +30 d (konservativt: ALFRED saknar vintagen 2020-05-05) |
| 2025-07 | 2025-09-04 | 2025-09-10 | +6 d |
| 2025-08 | 2025-11-19 | 2025-11-19 | 0 |
| 2025-09 | 2025-12-11 | 2025-12-11 | 0 |
| **2025-10** | **2026-01-08** (ft900_2510.pdf, "THURSDAY, JANUARY 8, 2026") | **2025-12-11** | **−28 d** |
| 2025-11 | 2026-01-29 | 2026-01-29 | 0 |
| 2025-12 | 2026-02-19 | 2026-02-19 | 0 |
| 2026-01 | 2026-03-12 | 2026-03-13 | +1 d |

Totalt lästes cirka 160 PDF:er: alla månader 2006–2017 och stickprov 2018–2026. Ett urval finns som parametrar i testet.

### 2.2 Census C30. Källa: `construction/c30/pdf/prYYYYMM.pdf` och `pdf/news.pdf`

- pr202403.pdf (2024-05-01) och pr202404.pdf (2024-06-03): *"With the May 2024 press release … estimates will
  be available separately for 'Data center' under the private office category back to January 2014."*
  pr202405.pdf (2024-07-01): *"With this May 2024 release … will be available separately for 'Data center'"*.
  Kategorin fanns alltså inte separat före **2024-07-01**. `known_from` för 2014-01 är 2014-03-07 och för 2024-04
  2024-06-04. 124 månader har `known_from` före första publiceringen.
- Nedstängningen 2025: pr202508 2025-11-17, pr202510 2026-01-21 ("also contains initial estimates for the month of
  September"), pr202512 2026-02-27 (även november), pr202601 2026-03-23, och 2026-05-07 (mars, även februari).
  Allt stämmer med `LATE`.
- Revideringar (news.pdf): varje majrelease (i juli) reviderar ej säsongsrensade data cirka 2 år bakåt och
  säsongsrensade cirka 7 år bakåt. 2024 reviderades SA tillbaka till 2017 och 2025 till 2018.

### 2.3 BEA. Källa: bea.gov, nyhetsarkivet för GDP

2024Q4 2025-01-30, 2025Q1 04-30, 2025Q2 07-30, 2025Q3 2025-12-23 ("Initial Estimate"), 2025Q4 2026-02-20, 2026Q1
04-30, 2026Q2 07-30. `known_from` ligger 0–6 d senare. Inga avvikelser.

### 2.4 SEC. Källa: EDGAR submissions (filingDate, acceptanceDateTime)

- För MSFT, GOOGL (inkl. Google Inc.), AMZN, META och NVDA hämtades 532 st 10-Q/10-K. För alla 1 019 perioder i
  17 bolagsserier är första `known_from` ≥ första 10-Q/10-K för kvartalet. Mediandifferensen är 0 d, och max är
  371 d (kvartal som bara går att räkna fram ur senare jämförelsetal).
- Varje `known_from` i bolagsserierna och i `capex_hyp4` är ett verkligt filingDate.
- acceptanceDateTime ligger aldrig på ett senare datum än filingDate. Inlämningar efter 17:30 ET får nästa dags
  datum, och då ligger `known_from` efter den faktiska tidpunkten. Det är konservativt.
- Inlämningsdagen för `capex_hyp4` är senaste av de fyra bolagens: 2017Q4 2018-02-06, 2020Q1 2020-05-01,
  2021Q4 2022-02-04, 2023Q4 2024-02-02, 2024Q4 2025-02-07, 2025Q3 2025-10-31 (EDGAR var öppet under
  nedstängningen), 2025Q4 2026-02-06 och 2026Q3 2026-10-30. Allt stämmer.
- Pressmeddelandena (8-K) kommer före 10-Q för GOOGL, AMZN och META. `known_from` är alltså konservativt.

### 2.5 TSMC. Källa: EDGAR 6-K, dokumentet tolkat och värdet jämfört

| Månad | 6-K filingDate (accession) | `known_from` | Värde stämmer |
|---|---|---|---|
| 2008-01 | 2008-02-14 (0001145549-08-000322) | 2008-02-14 | ja |
| 2012-12 | 2013-01-10 (0001193125-13-008677) | 2013-01-10 | ja |
| 2013-01 (första IFRS) | 2013-02-08 | 2013-02-08 | ja |
| 2020-01 (månadsskifte, nyår) | 2020-02-10 | 2020-02-10 | ja |
| 2025-09, 2025-10, 2025-12 | 2025-10-09, 2025-11-10, 2026-01-09 | samma | ja |
| 2026-01, 2026-10 | 2026-02-10, 2026-11-10 | samma | ja |

Första `known_from` ligger dag 6–16 i m+1, aldrig dag 5 eller tidigare. Revideringar finns i 16 perioder:
2012-01–2012-12 som IFRS-jämförelsetal daterade 2013 (t.ex. 2012-12: 37 114 den 2013-01-10 och 37 154 den
2013-02-08), samt 2006-06, 2006-09, 2011-07 och 2020-07. Ingen är bakåtdaterad.

### 2.6 EIA EPM. Källa: `electricity/monthly/update/archive/<månad>/`, "Release Date"

Datamånad → release / `known_from` (VA): 2024-06 08-23 / 08-29 · 2024-09 11-22 / 12-04 · 2024-11 2025-01-24 /
01-26 · 2025-08 10-24 / 10-26 · 2025-09 11-25 / 11-27 · 2025-10 12-23 / 12-25 · 2025-11 2026-01-26 / 01-28 ·
2026-01 03-24 / 03-26 · 2026-03 05-22 / 06-05 · 2026-07 09-24 / 09-26. Arkivzipparnas Last-Modified stämmer med
releasedagen (t.ex. october2025.zip 2025-10-24 13:08 GMT).

### 2.7 Indeed (git-klon av hiring-lab/ai-tracker)

35 CSV-versioner på first-parent. Sista datadag ligger 2–29 d före commit, och ingen datadag ligger efter commit.
Committare: 15 "GitHub" (webb eller merge, exakt tid) och 43 lokala commits (hiring-lab, lucas-young-indeed,
stham007, HiringLabDataScience). För dem är pushtiden okänd.

## 3. Fel i detalj

### 3.1 C30: kategorin "Data center" fanns inte före 2024-07-01 (störst påverkan)

`known_from` = månadsslut + 35 d ger 2014-01–2024-04 ett datum före första publiceringen. Spårets egen
dokumentation (`docs/kallor/census_eu.md`) skrev att införandedatumet var "fortfarande overifierat". Nu är det
belagt. Dessutom är den säsongsrensade serien (`privsatime.xlsx`) skattad med dagens säsongsfaktorer, som bygger
på data efter varje historisk månad.

**Påverkan på N1 (känslighetskörning, inte ett nytt test):** med `known_from` ≥ 2024-07-01 för datacenter och
2025-10-rättelsen för FT-900 går det inte att bilda V1/V2 före 2024Q2.

| | Period | n | B0 | B1 | V1 | V2 |
|---|---|---|---|---|---|---|
| N1 i dag | 2021Q4–2026Q3 | 19 | 10,64 | 6,91 | 7,50 | 7,88 |
| N1 rättad | 2024Q2–2026Q3 | 9 | 14,79 | 7,00 | 9,81 | 9,51 |
| N1b i dag | 2017Q2–2026Q3 | 130 | 15,54 | 15,04 | 16,01 | 15,77 |
| N1b rättad | 2024Q2–2026Q3 | 36 | 16,39 | 12,17 | 14,39 | 13,48 |

Slutsatsen, B1 som huvudmodell, står sig. Men V1/V2-siffrorna i `docs/resultat/n1.md` bygger till hälften
(10 av 19 kvartal) på data som inte var publicerad. Med n = 9 går ingen skillnad att upptäcka.

### 3.2 FT-900 oktober 2025: ALFRED-platshållaren 0,0

ALFRED-vintagen för IMP5830 den 2025-12-11 har oktober 2025 = 0,0. Riktigt värde (22 253) finns först i
vintagen 2026-01-08. `alfred.first_release()` räknar varje icke-saknat värde som publicerat, så oktober hamnade
inte i `LATE`, och regeln gav 2025-10-31 + 41 = 2025-12-11. Samma brist finns i `alfred.release_rows()`. Där
skulle en nolla bli en release-rad med värdet 0. Det gäller i dag inte G.17 eller M3, som saknar nollor, men det
är latent.

**Påverkan på N2:** målmånad 2025-12 (prognosdag 2026-01-05) använder oktoberimporten, som i verkligheten inte
fanns. Med rättelsen ändras V1 i 11 månader, mest 2026-01 (1,09 log-punkter, via träningsraden 2025-12 och λ).
V1:s MAE för hela perioden går från 10,517 till 10,506 mot B1:s 10,510, och Holm-p från 0,957 till 0,981. Ingen
befordran, och skillnaden är brus. N1 påverkas inte, eftersom ingen N1-prognosdag ligger mellan 2025-12-11 och
2026-01-08.

### 3.3 FT-900 före 2017-11

2006–2012: 38 av 84 månader har `known_from` 1–4 d före releasen (lag 42–45 d mot regelns 41). 2013-08 och
2013-09 ligger 13 respektive 4 d för tidigt. **Påverkar inte** N2, där prognosdag 5 i m+1 bara ser m−2, som
släpps cirka 25 d tidigare, och inte heller N1, vars träning börjar 2017 och vars C30-data saknas före 2014.
Rättas enkelt med `LATE` från PDF:erna eller med lag 45 före 2013.

### 3.4 Latent: senare hämtningar kan bakåtdatera en försenad release

`observations.new_rows()` ger en ny period `min(månadsslut + lag, hämtdag)`. Om en tidigare hämtning efter
regeldatumet saknade perioden, alltså en försenad release som inte finns i `LATE` (en framtida nedstängning),
blir `known_from` regeldatumet, trots att perioden bevisligen inte var publik vid den hämtningen. Det gäller bara
liveläget, eftersom dagens tabell är en enda hämtning. Testet
`test_new_period_is_not_dated_before_a_fetch_that_did_not_have_it` visar felet.

### 3.5 Latent: N2 poängsätter månader vars utfall var känt på prognosdagen

N1 hoppar över sådana kvartal. N2 (`backtest.run`) skriver bara ut antalet, som i dag är 0, eftersom tidigaste
6-K är dag 6. Om TSMC en gång lämnar in dag 5 räknas en "prognos" av ett känt tal in. Testet
`test_n2_month_with_outcome_known_at_origin_is_not_scored` visar det.

### 3.6 BTOS cykel 202520

Filens Publication Date är 2025-10-09, alltså under nedstängningen. Census webb uppdaterades normalt inte då,
men den faktiska dagen hittades inte (BTOS-appen är en JS-app, och katalogen nekas med 403). Kolumnen är dessutom
en tidsplan med framtida cykler. Ingen modell använder BTOS i dag.

## 4. Revideringar och bakåtdatering

- **SEC:** åtta kvartal i `capex_hyp4` har en andra vintage (2021Q1–Q4 och 2023Q1–Q4, Metas omräknade
  jämförelsetal). Kontrollerat mot companyfacts: 2023Q2 = 13 058 − 6 842 = 6 216 (2023-07-27), omräknad
  12 957 − 6 823 = 6 134, daterad 2024-08-01 = dagen för 10-Q:n med jämförelsetalen. Ingen bakåtdatering.
- **TSMC:** IFRS-omräkningen av 2012 är daterad 2013. Se 2.5.
- **BTOS:** filer som skrivs över blir `revision` med hämtdatum (`new_rows`, test finns). v1-värdena kommer ur en
  senare sammanställd fil, och om de skiljer sig från de först publicerade går inte att se.
- **Release-daterade källor i övrigt** (EIA, Indeed, ALFRED): varje ändrat värde blir en ny rad med dokumentets
  datum.

## 5. Backfill: vilka serier och hur stora revideringarna är

Serier som är helt backfill: `us_constr_datacenter(_nsa)`, `us_imports_tw_m`, `us_imports_kr_m`, `us_pfi_*` (4),
`eu_ai_ent_*` (4), `scb_ai_ent_se(_nace21)`, `g2_price_at_capability(_gpqa)` samt EIA före 2012-11.

Revideringarnas storlek, skattad ur riktiga vintages (ALFRED, första publicering mot senaste vintage):

| Belägg | Mått | Revidering |
|---|---|---|
| FT-900, IMP5830 (Taiwan), 107 vintages 2017-11–2026-11 | 12-mån log-tillväxt (N2:s feature) | MAE 0,16 pe, max 0,88 |
| samma | nivå | MAE 0,14 %, max 0,83 % |
| samma | N1:s delkvartalstillväxt | MAE 0,14 pe, korrelation realtid/senaste 1,00 |
| C30, TLPRVCONS (total privat, närmaste belägg; datacenter har inga vintages) | nivå | medel +5,2 %, max 13,6 % |
| samma | 12-mån log-tillväxt | MAE 3,4 pe, max 11,5 |
| samma | N1:s delkvartalstillväxt, 58 kvartal | MAE 1,6 pe mot featurens sd 2,5, **korrelation 0,69** |
| BEA, A679RC (IT-investeringar) | nivå | medel +4,7 %, max 12,5 % |
| samma | kvartalstillväxt | MAE 0,9 pe, max 3,5 |
| Release-daterade (egna vintages i tabellen) | första → senaste, bara reviderade perioder | EIA VA 2,75 %, EIA USA 0,85 %, Indeed US 2,5 %, M3 3,0 %, TSMC 0,10 %, capex_hyp4 0,12 % |

Tolkning: importbackfillen är ofarlig för N1 och N2. C30-backfillen är det inte. Redan på totalnivå förklarar
dagens vintage bara hälften av variansen i realtidsfeaturen, och datacenter är en liten underkategori med
troligen större revideringar. Av G.17:s revidering (MAE 107 log-punkter) är det mesta indexomläggningar, inte
läckage.

## 6. Backtestmotorerna

**N1 (`nowcast/engine.py`, `n1.py`), kodgenomgång:**
- Allt modellinput går genom `InfoSet.get()` = `as_of(origin)`: målets egen historik, båda indikatorerna och
  månadspositionerna J. Även träningsradernas indikatorvärden är vintagen vid prognosdagen.
- OLS, ridge-standardisering och λ-CV körs bara på träningsrader (rader före målkvartalet, ur `as_of`).
- Bara `first_vintage`/`first_known_from` tittar förbi prognosdagen, och de används bara för poäng och för att
  hoppa över kvartal som redan var inlämnade.
- Undantaget för 2025Q4 bygger på tillgänglighet: oktobers byggdata kom 2026-01-21, dagen efter prognosdagen
  (belagt i 2.2). Utfallet spelar ingen roll. Startkvartalet bestäms också av tillgänglighet.

**N2 (`nowcast_n2/engine.py`, `backtest.py`):**
- Input och träningsrader per månad byggs med `as_of(origin_k)`. Träningsrader kräver att utfallet var känt på den
  aktuella prognosdagen. N2 har inga säsongsfaktorer: B1 är säsongsnaiv på `as_of`-värden.
- Brist: månader vars utfall var känt på prognosdagen utesluts inte (3.5).

**Nya tester** (`tests/test_r1_leakage.py`, inget nätverk för motortesterna):
- `test_n1_every_backtest_forecast_is_blind_to_rows_after_its_origin`: hela backtestvägen. Varje rad som blir känd
  efter prognosdagen får ett orimligt värde (×37), också mål- och indikatorrevideringar, och varje poängsatt
  prognos (B0–V2, λ) ska vara oförändrad. En medveten mutation (indikatorn läst 30 d efter prognosdagen) fångas.
- `test_n2_backtest_forecasts_are_blind_to_rows_after_their_origin`: samma test för N2 med sena 6-K i fixturen.
  En mutation (träningsrader utan known_from-filter) fångas.
- `test_n1/n2_sample_selection_does_not_depend_on_outcomes`: vilka perioder som poängsätts ändras inte när
  utfallen skalas slumpvis.
- `test_n1_indicator_revision_after_origin_changes_nothing_but_before_origin_does`.
- Kalendertester mot belagda releaser för FT-900, C30 och BEA, samt datatester mot SEC, TSMC och EIA (hoppas
  över utan parquet).
- xfail(strict=True), alltså verkliga fel: FT-900 2025-10, 2013-08/09 och två månader före 2013; C30 2014-01,
  2019-06, 2021-12, 2023-12 och 2024-04 (för båda nycklarna); ALFRED-platshållaren; `new_rows` vid senare
  hämtningar; N2:s saknade spärr.

Hela pytest: 231 passed, 23 xfailed.

## 7. Rekommenderade åtgärder, i ordning efter påverkan på N1 och N2

**Status 2026-11-23:** åtgärd 1–8 är genomförda i spår X1 (`auto2/x1-rattning`). Alla 23 xfail-tester är vanliga
tester som passerar. N1 och N2 är omkörda, se [n1.md](../resultat/n1.md) och [n2.md](../resultat/n2.md). Åtgärd 3
lades också på regeldaterade rader i releasedaterade serier (EIA före 2012-11), och en ombyggnad (`--rebuild`)
glömmer inte tidigare hämtningar (hämtloggen `data/fetch_log.parquet`).

1. **C30 datacenter (N1, stor):** `known_from` = max(regel, 2024-07-01) för 2014-01–2024-04, till exempel som en
   `FIRST_PUBLISHED`-gräns i `series/census_c30.py`. Kör om den registrerade N1-backtesten och redovisa resultatet
   (B1 är fortfarande huvudmodell). Skriv i `docs/resultat/n1.md` att V1/V2 bara kan utvärderas från 2024Q2
   (n ≈ 9), och flagga SA-faktorerna. Överväg att byta V1/V2 till NSA-serien (`_nsa`). Det kräver en ny
   registrerad variant, inte en ändring i efterhand.
2. **ALFRED-platshållare (N2, liten, men den förstör `LATE`-härledningen):** behandla 0 som saknat värde i
   `first_release()` och `release_rows()` (eller kräv att värdet står kvar i nästa vintage). Lägg till
   `"2025-10": "2026-01-08"` i `LATE` för FT-900. Kör om N2.
3. **`new_rows` vid senare hämtningar (live, alla lag-daterade källor):** ge en ny period known_from ≥ den senaste
   hämtningen där perioden saknades, i praktiken max(regel, senaste `fetched_at` för serien + 1 d), och logga
   hämtningar även när inget nytt tillkom. Det skyddar mot nästa nedstängning.
4. **N2-spärr:** uteslut månader där `outcome_known_from <= origin` i `backtest.run` (som N1 gör). I dag påverkas
   0 månader.
5. **FT-900 före 2017-11:** lag 45 d före 2013, plus `LATE` 2013-08 = 2013-10-24 och 2013-09 = 2013-11-14
   (PDF-belägg finns). Påverkar inte N1 eller N2 i dag.
6. **BTOS 202520 och schemadatum:** sätt known_from ≥ 2025-11-13 för cykler vars schemadatum ligger under en
   finansieringslucka, tills den faktiska dagen är belagd. Spara filens Publication Date vid varje hämtning, så att
   tidsplan och utfall kan skiljas åt.
7. **Indeed och LiteLLM:** lägg en dags marginal på lokala commits (committer ≠ GitHub), eller avrunda till nästa
   dygn. Ingen modell påverkas.
8. **Konvention:** `as_of(when)` tar med `known_from == when`. Skriv i `observations.py` att prognosdagen betyder
   dagens slut och att releasedagar räknas som kända samma dag. I dag krockar inga `LATE`-datum med N1- eller
   N2-prognosdagar (kontrollerat).

## 8. Inte verifierat

- G.17 mot federalreserve.gov (nekas av proxyn) och M3 mot Census historiska pressmeddelanden (sidan hittades inte).
- BTOS faktiska publiceringsdagar. Eurostat och SCB 2023–2025.
- Pushtider för Indeed och LiteLLM (api.github.com nekas). Epochs publiceringsfördröjning efter `Started at`.
- Revideringarnas storlek för C30 datacenter specifikt: det finns ingen vintage före vår första hämtning.
  TLPRVCONS är en proxy.
