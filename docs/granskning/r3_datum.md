# R3: oberoende granskning av datering och läckage, våg 1 (A1–A4, D3)

Granskningsspår R3, 2026-11-23. Underlaget är den delade observationstabellen (391 426 rader, hämtning 2026-11-23)
och koden på `auto6/r3-datum-a` (ba9ff52). Granskningen är adversariell och gjord på samma sätt som R1: varje
`known_from` har jämförts med första offentliga tillgänglighet enligt källan själv, inte enligt spårets egen
dokumentation. Inga produktionsfiler är ändrade. Tester finns i `tests/test_r3_datum.py`. Tester som visar ett
verkligt fel är markerade `xfail(strict=True)`, så att sviten är grön och felet syns. När felet rättas ska
markeringen tas bort.

Hämtningar gjordes med den ärliga klienten (`ai_tracker.http`, SEC-identitet från `.env`, `save=False`, alltså
ingenting skrevs till den delade rådatan): EDGAR submissions för 18 CIK (39 506 inlämningar), PJM:s
BRA-rapporter och lastprognosrapporter (PDF), EIA-930:s blankettinstruktioner och om-sida, och Manifolds
`/v0/bets` för en marknad. Verktyget WebFetch nådde inte `www.eia.gov` (DNS), men den ärliga klienten gjorde det.
Ingen trendanalys gjordes.

## 1. Dom per källa

| Källa | Serier | known_from-regel | Dom | Kort motivering |
|---|---|---|---|---|
| A1 RPO (`sec_rpo.py`) | `rpo_*` (16) | inlämningsdag för 10-Q/10-K | **OK** | Alla `known_from` är verkliga filingDate. Inget kvartal är daterat före bolagets första egna rapport för balansdagen. Balanser differensieras inte. `rpo_hyp4` finns bara när alla fyra lämnat in, och summan stämmer i alla 28 versioner |
| A2a halvledare, companyfacts och instanser (`halvledare.py`, `sec_instant.py`) | `rev_*`, `capex_*`, `inv_*`, segment, `purchase_oblig_nvda` | inlämningsdag | **OK** | Mittpunktsregeln för Micron, Broadcom, Marvell och Nvidia stämmer i stickproven. Inlämningar efter 17:30 ET har nästa dags filingDate (Micron 2024-12-18 23:52 UTC → 12-19), vilket är konservativt. AMD-överstyrningen ger de rapporterade Data Center-värdena i varje version |
| A2a ASML (`asml_sec.py`) | `asml_net_sales`, `asml_net_bookings*` (4) | 6-K:ns filingDate | **OK** (litet fel som inte påverkar) | Alla datum är 6-K-datum och lika med dagen för pressmeddelandet (2024Q3: 2024-10-15, dagen då ASML av misstag publicerade en dag för tidigt). Två pressmeddelanden tolkas inte (Q2 2013, orderingången Q1 2017), så de kvartalen dateras först till nästa kvartals jämförelsetal. Det är konservativt. Orderingångens regimer är stängda och släpper inte in 2014Q4–2016Q4 eller 2026 |
| A2b neomoln (`neoclouds.py`, `nebius_sec.py`) | `rev/capex/ocf_{orcl,crwv,nbis}`, `capex/ocf_iren` | 10-Q/10-K resp. 6-K | **OK** | Oracle, CoreWeave och IREN dateras som SEC-serierna. Nebius dateras med 6-K:ns filingDate, aldrig före pressmeddelandet. Q1 2024–Q2 2025 kommer ur pressmeddelandet 2025-08-07 (ny bas) och är daterade dit |
| A3 finansiering, XBRL-delen (`sec_financing.py`, `sec_finansiering.py`) | 48 serier | inlämningsdag | **Fel som inte påverkar** | Nollfyllningen hittar inte på data: 105 fyllda inlämningar, inga negativa kvartal, och emissionerna ligger i rätt kvartal. Men `first_available` väljer formel per period utifrån hela historiken. Därför är `lt_debt_meta` och `lt_debt_hyp4` 2025Q4 daterade 266 dagar för sent (2026-10-22 i stället för 2026-01-29). Det är inget läckage, men det ger ett hål i `as_of` under nio månader |
| A4 PJM (`pjm.py`) | `pjm_bra_*` (3), `pjm_lf_*` (18) | publiceringsdag enligt `BRA_POSTED` och `LF_POSTED` | **OK** | Varje datum ligger på eller efter de publicerade filernas egna sparningsdatum (xlsx docProps, PDF CreationDate och ModDate). Reviderade filer (2022/23 och 2024/25) ger samma RTO-värde som originalrapporten. En senare ändring blir en revidering med hämtdatum (testat) |
| A4 EIA-930 (`eia930.py`) | `eia930_*` (12) | backfill: månadsslut + 7 d | **Ej verifierad, troligen fel som inte påverkar** | Alla rader före första hämtningen är märkta `backfill`. Sju dagar stämmer med EIA:s uppgift om 1–2 dagars fördröjning och med hämtningen (DOM till 2026-11-21, övriga till 11-22). Blankettens regel tillåter dock en månad för delregioner. När kolumnen "Demand (MW) (Adjusted)" och delregionsdata började publiceras gick inte att belägga. Samma riskklass som C30 i R1, men märkt som backfill och inte använt i någon modell |
| D3 förväntningar (`forvantningar.py`) | `g9_exp_mf_*` (17), `g9_exp_pm_*` (8) | Manifold: D+1 00:00 UTC. Polymarket: hämtdag | **Fel som inte påverkar** | Varje Manifold-värde är exakt rätt i tid (omräknat ur handeln). Men urvalet gjordes 2026-11-23 med metadata som bara var kända då, och historiken före urvalsdagen är märkt `release`. En `as_of`-vy av G9 före urvalet är därför betingad på framtiden (överlevnadsbias). Polymarket följer dagskonventionen |

## 2. Belägg

### 2.1 SEC: alla 95 serier ur EDGAR (10-Q, 10-K, 6-K)

- **Varje `known_from` är ett verkligt filingDate** för bolagets CIK (företrädare inräknade, 6-K för ASML och
  Nebius). Det gäller 3 542 rader i 95 serier, med 0 avvikelser.
- **Inget kvartal är för tidigt.** Första `known_from` jämfördes med den första 10-Q/10-K vars reportDate ligger
  minst 40 dagar in i kalenderkvartalet. Sex träffar var falsklarm, eftersom reportDate saknas i EDGAR för Oracles
  10-Q 2014-03-20 och Marvells 10-Q 2018-06-05. Båda är bolagets egen rapport för kvartalet.
- **Sent daterade kvartal** (43 sedan 2016, mer än 5 dagar efter egen rapport) är omräknade segment eller nya
  definitioner, som bara finns som jämförelsetal ett år senare (`rev_orcl_oci`, `rev_mu_cmbu`,
  `rev_mrvl_datacenter`, `rev_avgo_semis` och `rev_amd_datacenter` 2021Q2–2022Q1), samt Metas räntekostnad och
  IREN:s Q4 FY2025. Det är konservativt och korrekt. Ett undantag är fel: `lt_debt_meta` 2025Q4 (avsnitt 3.1).

| Serie | Period | Första `known_from` | EDGAR (form, accession, accepterad UTC, rapportdag) |
|---|---|---|---|
| rpo_orcl | 2018Q3 | 2018-09-19 | 10-Q 0001564590-18-023315, 2018-09-19 20:53, 2018-08-31 |
| rpo_orcl | 2025Q3 / 2025Q4 | 2025-09-10 / 2025-12-11 | 10-Q -25-200095 / -25-315925 (31 aug / 30 nov) |
| rpo_orcl | 2026Q3 | 2026-09-11 | 10-Q 0001193125-26-389274, 2026-08-31 |
| rpo_msft | 2017Q3 / 2020Q2 | 2017-10-26 / 2020-07-30 | 10-Q -17-020171 / 10-K -20-034944 (accepterad 2020-07-31 00:44 UTC = 20:44 ET den 30:e) |
| rpo_msft | 2025Q4 / 2026Q3 | 2026-01-28 / 2026-10-28 | 10-Q 0001193125-26-027207 / -26-436133 |
| rpo_crwv | 2025Q1 / 2025Q4 | 2025-05-15 / 2026-03-02 | 10-Q 0001769628-25-000014 / 10-K -26-000104 |
| rev_mu | 2024Q4 / 2025Q4 | 2024-12-19 / 2025-12-18 | 10-Q accepterad 2024-12-18 23:52 resp. 2025-12-17 23:47 UTC (efter 17:30 ET, nästa dag) |
| rev_mu | 2020Q3 / 2026Q3 | 2020-10-19 / 2026-10-09 | 10-K (FY slutar 2020-09-03 resp. 2026-09-03, jun–aug → Q3) |
| rev_avgo | 2019Q4 / 2025Q4 | 2020-03-13 / 2026-03-11 | 10-Q (FQ1 slutar 2 feb resp. 1 feb, nov–jan → Q4) |
| rev_avgo | 2023Q3 / 2026Q2 | 2023-12-14 / 2026-09-10 | 10-K (29 okt) / 10-Q accepterad 2026-09-09 21:56 UTC |
| rev_mrvl | 2021Q1 / 2023Q4 / 2025Q4 | 2021-06-09 / 2024-03-13 / 2026-03-11 | 10-Q (1 maj) / 10-K (3 feb) / 10-K (31 jan) |
| capex_nvda | 2022Q4 / 2025Q4 | 2023-02-24 / 2026-02-25 | 10-K 0001045810-23-000017 / -26-000021 |
| purchase_oblig_nvda | 2021Q3 / 2026Q1 | 2021-11-22 / 2026-05-20 | 10-Q accepterad lördag 2021-11-20 02:16 UTC (filingDate måndag) / 10-Q -26-000052 |
| rev_amd_datacenter | 2023Q1 / 2024Q1 / 2025Q1 | 2023-05-03 / 2024-05-01 / 2025-05-07 | 10-Q -23-000076 (roterad) / -24-000056 (roterad) / -25-000047 (accepterad 05-06 22:04 UTC) |
| debt_issued_meta | 2022Q3 / 2025Q4 | 2022-10-27 / 2026-01-29 | 10-Q -22-000108 / 10-K 0001628280-26-003942 |
| debt_issued_orcl | 2026Q3 (nollfylld) | 2026-09-11 | 10-Q 0001193125-26-389274 |
| asml_net_sales | 2024Q3 / 2025Q4 / 2026Q3 | 2024-10-15 / 2026-01-28 / 2026-10-14 | 6-K accepterad 15:34 / 11:03 / 10:01 UTC |
| rev_nbis | 2025Q3 / 2025Q4 / 2026Q3 | 2025-11-12 / 2026-02-12 / 2026-11-12 | 6-K -25-110028 / -26-013947 / -26-126238 |

ASML:s 365 6-K har nio fall där acceptansdagen (UTC) skiljer sig från filingDate. Inget av dem är ett
resultatmeddelande. Nebius lämnar resultat-6-K samma dag som pressmeddelandet. Den 12 november 2025 kom två 6-K
(13:00 och 16:07 UTC), och värdena är daterade den dagen.

### 2.2 AMD:s överstyrning av segmentmedlemmar

`AMD_ROTATED` är exakt filingDate för de sex 10-Q där medlemmarna är roterade. Varje version av
`rev_amd_datacenter` för 2023Q1–2025Q2 har AMD:s rapporterade Data Center-intäkt: 1 295, 1 321, 1 598, 2 282,
2 337, 2 834, 3 549, 3 859, 3 674 och 3 240 MUSD. Ingen period har en version med Gaming- eller Client-värdet.
Valet av medlem bygger på senare inlämningar, men värdena är de som den roterade inlämningen själv redovisar för
Data Center, så det är inget läckage.

### 2.3 Nollfyllningen i finansieringen

`zero_facts` kördes om på de cachade companyfacts och instanserna:

| Mått | Bolag | Fyllda inlämningar | Vägrade | Kontroll |
|---|---|---|---|---|
| debt_issued | MSFT | 19 (2019-10 – 2023-07, 2025-10 – 2026-10) | 0 | MSFT har inte emitterat obligationer sedan 2017. FY2024 har taggen och fylls inte |
| debt_issued | META | 32 | 0 | Emissionerna aug 2022 (9 921), maj 2023 (8 455), aug 2024 (10 432), okt 2025 (29 906) och 2026Q2 (24 910) ligger i rätt kvartal. Nollorna ligger mellan dem |
| debt_issued | ORCL | 11 | 0 | Fyllt Q1–Q3 FY2020–FY2022 (emissionerna 30 mar 2020 och 24 mar 2021 ligger i Q4). 2026-09-11: föregående års jämförelsekvartal (2025Q3) är också 0 |
| debt_repaid | META | 43 | 0 | Meta har aldrig amorterat långfristig skuld |
| debt_issued | AMZN | 0 | 3 (2016, `ProceedsFromRepaymentsOfLongTermDebtAndCapitalSecurities`) | Lucka lämnas, ingen nolla |

Inget debt-kvartal i tabellen är negativt. Ett fyllt helår över ett 9M-värde som inte är noll skulle ha gett
ett negativt Q4. Nollorna dateras med den egna inlämningen, och jämförelsekolumner fylls inte (testat).

### 2.4 PJM

| Leveransår / årgång | Datum i koden | Belägg (läst 2026-11-23) |
|---|---|---|
| BRA 2020/21, 2021/22, 2023/24 | 2017-05-23, 2018-05-23, 2022-06-21 | Resultatfilens docProps `modified` samma dag |
| BRA 2022/23 | 2021-06-02 | Rapportens PDF CreationDate 2021-06-02 18:52 UTC: "cleared 144,477.3 MW". Resultatfilen sparades om 2022-01-06, men RTO-värdet är oförändrat |
| BRA 2024/25 | 2023-02-27 | Rapporten och filen är reviderade (PDF 2024-06-18, xlsx 2024-05-09, DPL-South efter FERC). RTO 147 477,4 i tabellerna, i texten "147,478 MW". Pressmeddelandet 2023-02-27 lästes inte i sessionen |
| BRA 2025/26 – 2028/29 | 2024-07-30, 2025-07-22, 2025-12-17, 2026-07-14 | docProps `modified` samma dag (19:24, 17:50, 21:03 och 19:02 UTC) |
| LF 2017–2020 | 31 januari | PDF ModDate 2017-01-09, 2017-12-18, 2018-12-24, 2019-12-24 |
| LF 2021–2023 | 31 januari | Datafilernas `created` 2020-12-30, 2021-12-20, 2022-12-12. 2023-PDF:en har ModDate 2023-05-19, men ingen revideringsnotis finns, och datafilen är originalet |
| LF 2024 / 2025 / 2026 | 2024-02-01 / 2025-01-24 / 2026-01-14 | Datafilen `created` 2024-01-31 (revisionen), 2025-01-22, 2026-01-05. Tabellfilerna `modified` 2025-01-24 och 2026-02-06, alltså known_from 2025-01-25 och 2026-02-07 |

Alla datum ligger alltså på eller efter belägget. 2007/08–2013/14 och 2015/16–2018/19 dateras till en senare
rapport, vilket är konservativt.

### 2.5 EIA-930

- EIA:s blankettinstruktioner (`survey/form/eia_930/instructions.pdf`, ModDate 2026-07-20) säger att data ska
  lämnas *"As soon as available, within one month after the operating day, hourly actual demand by sub-region"*.
  Today in Energy 2020-04-06 (id 46117) säger: *"Sub-regional demand data for the largest balancing authorities
  are available with a one- to two-day lag."*
- I hämtningen 2026-11-23 sträcker sig SUBREGION-filen (DOM) till 2026-11-21 och BALANCE-filen till 2026-11-22.
  Sju dagar räcker alltså i dag. Hur fördröjningen såg ut historiskt går inte att se, eftersom EIA skriver om filerna
  dagligen.
- Om-sidan (`930-content/about.html`) säger att delregioner finns "beginning July 1, 2018", men inte när de
  började publiceras. Den säger inte heller när den justerade efterfrågan infördes. Serierna börjar 2015-07 (BA)
  och 2018-10 (DOM) med `known_from` = månadsslut + 7. Om publiceringen började senare ligger de första
  backfill-raderna före första publicering, som C30 i R1. Ingen modell använder serierna, och alla 1 400 rader är
  märkta `backfill`.

### 2.6 Manifold och Polymarket

- Marknaden `0I0JK1Ei1S1V28mCoeDM` har 293 handelsposter, varav 42 inlösningar och 37 avbrutna limitordrar. Sex
  dagar räknades om direkt ur `createdTime` och `probAfter` (2023-01-12, 2023-06-30, 2024-03-01, 2024-12-31,
  2025-05-15 och 2025-08-17, avgörandedagen 05:27 UTC). Alla stämmer exakt, och sista använda handeln ligger
  alltid före `known_from` = D+1 00:00. En handel exakt vid midnatt hör till nästa dygn (testat).
- Polymarket hämtas på måndagar 03:37 UTC och dateras till måndagen 00:00. Det följer `as_of`-konventionen
  (dagens slut), och priset tas mindre än fyra timmar efter dagens början. Perioden är veckan som slutade dagen före.
- **Urvalet:** 14 av 17 Manifold-frågor var avgjorda vid urvalet. Kriterierna (minst 100 unika handlare,
  livslängd minst 180 dagar, inte avgjord som CANCEL) mättes 2026-11-23. Ett värde från 2023 är rätt i tid, men att
  frågan finns i tabellen beror på vad som hände efter 2023.

## 3. Fel i detalj

### 3.1 `first_available` daterar en balans för sent när en senare inlämning taggar den saknade komponenten

`lt_debt_meta` har två formler: `LongTermDebtNoncurrent + LongTermDebtCurrent`, och som reserv bara den
långfristiga delen. Metas 10-Q 2026-10-22 taggar `LongTermDebtCurrent = 0` för 2025-12-31 som jämförelsetal. Då
får formel 1 kvartalet 2025Q4 med `known_from` 2026-10-22. `first_available` tar varje period ur den första formel
som någonsin har den, så versionen från 10-K 2026-01-29 (samma värde, 58 744) försvinner. Följden är att
`as_of` mellan 2026-01-29 och 2026-10-21 saknar 2025Q4 för `lt_debt_meta` och `lt_debt_hyp4`, men har 2025Q3 och
2026Q1. Det är konservativt, inte ett läckage. Ingen modell använder serierna. Det befintliga testet
`test_first_available_takes_each_period_from_one_formula` låser beteendet.

## 4. Rättningar i prioritetsordning

1. **`sec_financing.first_available`:** välj formel per brytdag, som `balances_at` gör med taggar: vid varje
   inlämningsdag den första formeln som då har perioden. Alternativt: behåll den tidigaste versionen när värdet
   är oförändrat. Ta bort de tre xfail-markeringarna (`test_first_available_keeps_the_first_publication_...` och
   `test_meta_lt_debt_2025q4_known_from_the_10k`), och anpassa det befintliga testet.
2. **Manifold:** märk rader med `known_from` före `selected_on` som `backfill`, eller låt G9-aggregat bara använda
   frågor från och med urvalsdagen. Skriv in det i `docs/kallor/forvantningar.md` före grind G-A. Ta bort xfail i
   `test_manifold_rows_before_selection_are_flagged`.
3. **EIA-930:** belägg när "Demand (MW) (Adjusted)" och delregionsdata började publiceras (EIA:s release notes).
   Om det skedde efter seriernas start ska backfill-raderna få det datumet som golv (som C30-rättningen i X1). För
   `pjm_dom` är 31 dagar den konservativa tolkningen av blankettens regel, men 7 dagar stämmer med EIA:s uppgift
   och med hämtningen.
4. **ASML:** tolka de två missade pressmeddelandena (2013-07-17, nettoomsättning Q2 2013, och 2017-04-19, orderingång
   Q1 2017). Då får kvartalen sitt rätta, tidigare datum. Det gäller fullständighet, inte läckage.
5. **Dokumentation:** skriv i `forvantningar.md` att Polymarket-värdet är måndagens pris, märkt med föregående vecka.

## 5. Testerna (`tests/test_r3_datum.py`)

- **Punkt-i-tid-egenskaper** för `sec_rpo.stock_vintages`, `sec_instant.vintages`, `sec_financing.stock_vintages`
  och `asml_sec.vintages`, med 34 slumpade fixturer. På varje dag d jämförs `as_of` med en brute force-referens som
  bara ser fakta inlämnade senast d. Kontroll: en variant där alla versioner flyttats 20 dagar bakåt fångas i 12 av
  12 frön.
- **Kantfall:** nollfyllning (egen dag, inga jämförelsekolumner, ingen fyllning utan instans), formelreserv (xfail),
  AMD-nycklar, ASML-regimer, PJM-datum mot filbelägg, PJM-revidering, EIA-930 backfill→fetch→revision, fullständig
  månad, Manifolds midnattsgräns och Polymarket-veckan.
- **Riktig data** (`real_data`): 43 stickprov där första `known_from` är EDGAR:s filingDate, AMD-värdena, inga
  negativa debt-kvartal, EIA-930 backfill-märkt, PJM-datum ur tabellen, samt två xfail (Meta-skulden och
  Manifold-urvalet).
- Hela sviten: 991 passed, 3 skipped, 4 xfailed.

## Status efter rättning (X2, 2026-11-23)

Rättat på `auto6/x2-r3-rattning`. Alla fyra strikta xfail i `tests/test_r3_datum.py` är borttagna och testerna gröna.

1. **`sec_financing.first_available`** väljer nu formel per brytdag (som `balances_at` för taggar). Ett oförändrat
   värde behåller sin första publicering, och ett formelbyte med nytt värde blir en revidering. Det gamla testet
   heter nu `test_first_available_chooses_the_formula_per_cutoff_date`, och ett egenskapstest mot brute force har
   lagts till. Ombyggt: `lt_debt_meta` och `lt_debt_hyp4` 2025Q4 är daterade 2026-01-29 respektive 2026-02-06
   (i stället för 2026-10-22). Samma regel ger `lt_debt_msft` 2012Q2 från 2012-07-26 (reservformeln) och
   `cash_sec_googl` 2009Q4 från 10-K 2010-02-12 i stället för 2010-07-30. Övriga 23 balansserier är oförändrade.
2. **Manifold:** rader med `known_from` före frågans `selected_on` har `source="backfill"`
   (`forvantningar.flag_preselection`). Ombyggt: 17 serier, 9 702 backfill-rader och 3 release-rader. Regeln inför
   G-A finns i `docs/kallor/forvantningar.md`: mått på mängdnivå använder bara rader som inte är backfill.
3. **EIA-930:** golv vid första publicering, belagt på eia.gov. För BA-data är det 2016-07-25 (press437 och TIE
   27212), för delregioner 2019-08-21 (TIE 40993). DOM har 31 dagars fördröjning (om-sidan: "lag of 1–30 days").
   Ombyggt: alla 12 serier. **Kvar:** när kolumnen "Demand (MW) (Adjusted)" infördes gick inte att belägga. De tio
   BA-serierna är flaggade i `docs/kallor/el_datacenter.md`.
4. **ASML:** pressmeddelandet 2013-07-17 läses nu (`parse_split_table`, tabellen delad kring Cymer), och
   presentationsbilagor hoppas över (`presentat` i `SKIP_DOC`). Det senare rättade 2017-04-19 och också 2020-10-14,
   där presentationen tidigare lästes före pressmeddelandet. Nu har `asml_net_sales` 2013Q2, 2017Q1 och 2020Q3
   samt `asml_net_bookings(_ex_euv)` 2013Q2, 2017Q1 och 2020Q3 rätt, tidigare datum. Värdena är desamma som i de
   senare jämförelsetalen.
5. **Polymarket:** i `forvantningar.md` står nu att värdet är måndagens pris, märkt med föregående vecka.

Hela sviten efter merge av main: 1 259 passed, 1 skipped och 26 xfailed. Alla 26 xfail kommer från R5 (`test_r5_extraktion.py`),
inga från R3. `python -m ai_tracker.warehouse` är grön.
