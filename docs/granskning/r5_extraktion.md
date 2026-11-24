# R5: oberoende granskning av de agentextraherade värdena (B4, A3, D1, B6)

Granskningsspår R5, 2026-11-23, på `auto6/r5-extraktion` (bas ba9ff52). Underlaget är `curated/ai_kpis.csv` (169
rader, varav 33 kapacitetskoder) och Nvidias guidance (`sources/nvda_guidance.py`), `curated/lease_commitments.csv`
(190 rader), `curated/plans.csv` (127 rader) och `curated/lab_revenue.csv` (14 rader). Granskningen är adversariell
och byggd som R2. Varje granskat värde lästes om i **originaldokumentet, hämtat på nytt** från www.sec.gov och
www.microsoft.com med den ärliga klienten (`ai_tracker.http`, SEC-identitet från `.env`), inte från spårens cache.
Totalt hämtades 799 dokument. Texten gjordes om på två sätt: med spårens egen konvertering
(`tsmc_sec.to_text` + `guidance_capex.sentences`), för att kunna kontrollera plats och SHA-256, och med en egen
konvertering (BeautifulSoup) och egna sökmönster för Nvidia och för sökningen efter saknade rader. Varje datum
jämfördes med EDGAR:s submissions-API (`filingDate`, `acceptanceDateTime`), som hämtades samma dag.

Inga CSV:er och inga produktionsfiler är ändrade. Tester finns i `tests/test_r5_extraktion.py`: 173 fastlåsta
kontroller av värden som stämmer och 26 fel som är markerade `xfail(strict=True)`. När ett fel rättas ska
markeringen tas bort. Ingen jämförelse mellan prognos och utfall har gjorts, och inga takter har räknats.

**Anthropic:** enligt beslutet 2026-11-23 hämtades ingenting från anthropic.com, claude.com eller
platform.claude.com. B6:s rader från nyhetsrummet granskades mot de sparade meningarna
(`/home/user/wt/b6-labbintakter/data/raw/lab_revenue_sentences/sentences.jsonl`, som inte ligger i den delade
raw-katalogen som briefen anger) och mot B6:s egna råkopior från 2026-11-23. Bara S-1-raden kunde hämtas på nytt
från sec.gov.

## 1. Dom

| Del | Dom | Kort motivering |
|---|---|---|
| **Nvidias guidance** (N3:s B2, 2017Q2–2026Q4) | **GODKÄND** | Alla 39 kvartal är handlästa ur nyhämtade 8-K (EX-99.1 och EX-99.2). Mittpunkt, band (2 %, och 3 % för 14-veckorskvartalet 2026Q4), lo/hi och `known_from` stämmer exakt, 0 fel. Inget 8-K med Item 7.01/8.01 under perioden (55 genomsökta) har en ny intäktssiffra för ett pågående kvartal, bara den kvalitativa 2021-04-12 som B4 redan nämner. Alla accepterades 16.20–16.52 ET, så `filingDate` = samma dag. |
| **ai_kpis.csv, nyckeltal** (136 rader) | **GODKÄND MED RÄTTNINGAR** | 27 av 27 stickprovsrader stämmer i värde, enhet, typ, definition, period och datum. **8 meningar saknas (R5-F6):** antal kunder och organisationer för Microsofts AI-produkter i samtalen (Sales Copilot, Copilot for Security, Foundry). De är varken kodade eller listade under "Inte kodat". Befintliga serier påverkas inte. |
| **ai_kpis.csv, kapacitet** (33 rader, −2..+2) | **GODKÄND MED RÄTTNINGAR** | Alla 33 rader är omlästa: 30 stämmer och 3 är fel (R5-F1, F2b, F3). 3 rader saknas (R5-F2a, F4, F5). Tolkning 7 och 4 tillämpas inte konsekvent. |
| **lease_commitments.csv** (190 rader) | **GODKÄND MED RÄTTNINGAR** | 38 av 38 stickprovsrader stämmer, och alla 190 meningar har lagrad SHA-256 på angiven plats i nyhämtade dokument. **4 Oracle-rader saknas (R5-F7):** belopp i MD&A för 10-Q nov 2023, feb 2024, aug 2024 och nov 2024. Dokumentationen om Oracles luckor är därför fel (R5-F8). Microsofts breddade definition från 2026Q2 är inte flaggad (R5-F9). |
| **plans.csv** (127 rader) | **GODKÄND MED RÄTTNINGAR** | 25 av 25 stickprovsrader stämmer. **1 rad saknas (R5-F10):** Microsofts FY26-plan från samtalet 2025-01-29, som är E1:s `msft-16`. Metas åtagandeserie spänner över ett definitionsbyte (R5-F11). Två mindre kodfel finns (R5-F12) och en trolig saknad Oracle-rad (R5-F13). |
| **lab_revenue.csv** (14 rader) | **GODKÄND, med förbehåll** | ant-11 (S-1/A) är verifierad mot sec.gov: hash, ~81 mdr per 2026-10-31 och `known_from` 2026-11-10 stämmer, och S-1 (10-26) och S-1/A (11-02) lämnade värdet tomt. De 13 raderna från nyhetsrummet stämmer i sak (värde, förbehåll, period, omfång, datePublished) mot sparade meningar och råkopior, men de är **inte oberoende verifierade** mot en ny hämtning. Inga saknade rader hittades. |
| Datering, alla SEC-rader | **OK** | 0 avvikelser av 97 + 190 + 99 + 1 rader: `filed` = filingDate, `accepted` = acceptanceDateTime, URL:ens mapp = accession och `known_from` ≥ acceptance-dagen (New York-tid). Alla 100 rader från Microsofts samtal har en 8-K med Item 2.02 samma dag. Inget tidigare dokument med samma värde hittades i stickproven. |

**Slutsats för N3:** Nvidias guidance kan användas som den är. Inget läckage hittades i någon del.

**Publicering:** Nvidias serier har redan `publish=True`, och det kan stå kvar. A3, D1 och B4 kan få `publish=True` när
respektive rättningar är gjorda. Det gäller SEC-rader och rader från microsoft.com på samma villkor som E1 (bara
siffror med källhänvisning). B6 förblir `publish=False`: licensen är inte kontrollerad, hämtningen är pausad och 13
rader är inte oberoende verifierade.

## 2. Fel och saknade rader

| Nr | CSV | Fel | Belägg | Rättning |
|---|---|---|---|---|
| **R5-F1** | ai_kpis | `nvda-cap-2025q3` (+2) kodar "cloud GPUs are sold out", alltså molnens uthyrda GPU-kapacitet. Det är partnernas kapacitet, som tolkning 7 utesluter (10-Q 2026-08-26 om AI-molnpartner kodas inte av samma skäl). Övriga dokument samma dag (EX-99.2 och 10-Q) säger inget om Nvidias eget utbud. | 8-K EX-99.1 `q3fy26pr.htm`, 0001045810-25-000228, mening #4 | Ta bort raden, så att 2025Q3 blir en lucka. Det andra alternativet är att logga en ny tolkning och tillämpa den också på 2026-08-26. |
| **R5-F2a** | ai_kpis | Tolkning 7 kodar FY23-nedskrivningen av Ampere ("excess supply … Data Center", delvis Kina) som −2. Den fullt jämförbara H20-nedskrivningen på 4,5 mdr USD i Q1 FY26 ("excess inventory … as the demand for H20 diminished") är inte kodad. | 8-K EX-99.1 `q1fy26pr.htm`, 0001045810-25-000115, 2025-05-28, mening #2, SHA-256 `0f78d537…3781d0` | Lägg till `NVDA_CAPACITY_CURRENT` 2025Q1 = −2. Rekommendationen är att tillämpa tolkning 7 som den står, eftersom en snävare regel vore en ändring i efterhand. |
| **R5-F2b** | ai_kpis | `nvda-cap-2026q2` = +1 ("currently experiencing certain supply constraints", #280), men samma 10-Q har H200-nedskrivningen "excess inventory … demand … diminished" (#323). Enligt de låsta reglerna ger olika tecken i ett dokument koden 0. | 10-Q 0001045810-26-000075, meningarna #280 och #323 | Sätt koden till 0 och skriv skälet i noten. |
| **R5-F3** | ai_kpis | `nvda-capf-2026q1`: "secured inventory and capacity to meet demand beyond the next several quarters" anger en horisont, men raden har kvartalet för inlämningen. Tolkning 4 kodar "several quarters" som minst två kvartal. | EX-99.2 `q4fy26cfocommentary.htm`, mening #30 | Ändra perioden till 2026Q3 (Q2–Q3 FY27). |
| **R5-F4** | ai_kpis | Saknad rad: samtalet FY25 Q3 (2025-04-30), "We knew Q3 that we had really matched supply and demand pretty carefully". Uttalandet gäller det redovisade kvartalet (2025Q1) och betyder balans, alltså 0 current. Det är det enda samtalet FY24 Q3–FY27 Q1 utan en current-kod. | microsoft.com FY2025 Q3, mening #364, SHA-256 `664b521b…f7bee1b` | Lägg till `MSFT_CAPACITY_CURRENT` 2025Q1 = 0. |
| **R5-F5** | ai_kpis | Saknad rad: samtalet 2024-04-25, i Azure-guidancen för Q4 FY24: "with some impact from the AI capacity availability noted earlier" (och #378: "does impact a little bit the number in Q4"). Det är samma sorts uttalande som `msft-capf-2024q4b`, som är kodat +1. | microsoft.com FY2024 Q3, mening #221, SHA-256 `b87d796c…e36610` | Lägg till `MSFT_CAPACITY_FORWARD` 2024Q2 = +1. |
| **R5-F6** | ai_kpis | Saknade nyckeltal, varken kodade eller listade under "Inte kodat": Sales Copilot (fler än 15 000 organisationer 2023-10-24 #61, fler än 30 000 2024-01-30 #68), Copilot for Security (fler än 1 000 betalande kunder, 2024-07-30 #93), Foundry med flera modeller (fler än 1 500 kunder med både Anthropic och OpenAI, 2026-01-28 #51; fler än 10 000 kunder med mer än en modell, 2026-04-29 #46) och kunder med både Foundry och Fabric (fler än 15 000 2026-04-29 #66, 17 000 2026-07-29 #68 och 19 000 2026-10-28 #84). Bedömningsfall som bara ska tas med i listan: LinkedIn (25 000 kunder med "agentic hiring" och mer än 10 miljoner dagliga användare av AI-jobbsök, 2026-10-28 #56) och MAI Code Flash (3 miljoner användare, #74). | SHA-256 i `MISSING_KPI_SENTENCES` i testerna | Koda raderna med nya definitionskoder, eller lägg till dem under "Inte kodat" med skäl och ta bort testerna. |
| **R5-F7** | lease | Saknade rader: Oracles 10-Q anger "operating lease commitments … We have not recorded these lease commitments" i MD&A med belopp, alltså samma formulering som de kodade raderna för nov 2022 och feb 2023. 2023-11-30: 10 600, 2024-02-29: 18 800, 2024-08-31: 36 200 och 2024-11-30: 36 700 MUSD. | 0000950170-23-069682 #877, -24-029904 #958, -24-104905 #857, -24-134973 #909 (platser i `lease_commitments.sentences`, SHA-256 i `ORCL_MISSING`) | Lägg till fyra rader (operating). |
| R5-F8 | lease, dok. | `finansiering.md`: "Oracle anger inget belopp i flera 10-Q 2019–2024, så serien börjar … 2025Q1" stämmer inte. Med R5-F7 är den sista luckan 2023-08-31, där 10-Q:n bara säger "no significant changes". | Se R5-F7 | Rätta texten och pröva om `lease_uncommenced_orcl` kan börja 2023Q4 (Oracles nov 2023). |
| R5-F9 | lease | Från 2026-06-30 lägger Microsoft till "with some arrangements subject to certain contractual conditions being met". Definitionen är breddad, och raderna saknar not. | `msft-2026-06-30-total`, `msft-2026-09-30-total` | Skriv en not och markera ett definitionsbrott i serien (eller börja en ny serie från 2026Q2). |
| **R5-F10** | plans | Saknad rad: samtalet 2025-01-29 (FY25 Q2) säger att capex-tillväxten FY26 blir "lower than FY25" (FY26 nämns i #239). Det är en plan för nästa räkenskapsår och E1:s `msft-16`. D1 har FY26 först från 2025-04-30. | microsoft.com FY2025 Q2, mening #240, SHA-256 `6d795323…a8487242` | Lägg till CAPEX, FY2026, direction −1, `growth_vs_prior`, xref `msft-16`. |
| **R5-F11** | plans | `META_NONCANCEL_COMMIT` spänner över ett byte av sammansättning: från 2025-09-30 står "third-party cloud capacity arrangements" först i beskrivningen (2025Q2: 27,95 mdr; 2025Q3: 81,19 mdr), och från 2026-03-31 finns tillägget "comprising both short-term and long-term arrangements". D1:s egen regel ger ny kod vid ny ordalydelse (D1:s tolkning 4 bad R5 pröva just detta). | `meta-p030`, `p032`–`p035`, meningen efter platsen | Ny definitionskod från 2025Q3. |
| R5-F12 | plans | Mindre fel: `msft-p022` har `approx`, men meningen säger "double" utan förbehåll, så typen ska vara `point`. `msft-p025` säger "double our overall **capacity**" och inte "datacenter footprint", vilket är ny ordalydelse och enligt D1:s regel ska ge ny kod. | call FY2026 Q3 #34, call FY2026 Q4 #31 | Rätta typen och ge `msft-p025` en egen kod, eller förklara i noten varför det är samma mål. |
| R5-F13 | plans | Trolig saknad rad: Oracles 10-Q för feb 2024, "unconditional purchase obligations to $4.4 billion", "primarily related to capital expenditures for our data centers". Den kopplas alltså till infrastruktur, vilket är D1:s villkor för COMMIT. | 0000950170-24-029904, meningarna #429 och #431, SHA-256 `b9deda3d…1df878848` | Lägg till en rad med egen kod (ordalydelsen skiljer sig från `ORCL_UNCOND_OBLIG`), eller skriv skälet under "Inte kodat". |
| **R5-F14** | guidance_capex (E1) | D1:s flagga är bekräftad. Samtalet 2026-10-28 säger "for the calendar year, spend should be approximately $170 billion", men CSV:n har bara `msft-26` (cirka 190 mdr, 2026-04-29). Microsoft används inte i B2 (R2), så felet påverkar inte N1. | microsoft.com FY2027 Q1, mening #226, SHA-256 `c12864f5…c7f79788` | Lägg till CY2026 approx 170 000 MUSD, filed 2026-10-28. Samtalet 2026-07-29 (#225–227) säger också att fler datacenterleasingavtal blir operationella, vilket sänker `MSFT_CAPEX_INCL_FL` framåt. Det bör noteras som ett definitionsbrott. |

Fet stil = påverkar en serie som laddas. Övriga är dokumentation, mindre kodfel eller bedömningsfall.

## 3. Belägg

### 3.1 Nvidia (N3)

Alla 96 8-K 2017-04–2026-11 hämtades på nytt som fullständig inlämningstext (`<acc>.txt`) och delades i dokument.
De söktes med ett eget, bredare mönster ("revenue … expected … $x billion/million"), och rubriken "quarter of fiscal
YYYY" lästes inom 300 tecken före. Varje kvartal 2017Q2–2026Q4 har exakt ett värde (EX-99.1 och EX-99.2 är lika),
lika med den lagrade vintagen (`test_nvda_outlook_matches_hand_reading`). 2019-11-14 finns guidance bara i
EX-99.2, som B4 skriver. De preliminära utfallen 2019-01-28 ("revenue expected to be $2.20 billion versus previous
guidance") och 2022-08-08 lämnades in efter kvartalets slut och är med rätta inte guidance.

### 3.2 Kapacitetskoder (alla 33)

Varje rad lästes med ±2 meningar och med alla andra kapacitetsmeningar i samma dokument, för att pröva regeln om
den mest uttryckliga meningen och regeln om olika tecken. Utöver felen ovan:

- **Stämmer:** Amazons fyra rader (tolkning 5 är konsekvent: "fully subscribed" ger +2, "largely sold out" och
  "nearly all … committed" ger +1), Alphabet 2026-06-04 (+1, "exceeding the company's available supply"), Microsofts
  18 rader (perioder, horisonter och tolkning 3 och 6 är konsekventa), och Nvidias 2022Q4 (−2 enligt tolkning 7),
  2024Q1, 2024Q3, 2024Q4f, 2025Q1f och 2025Q2f.
- **Anmärkningar utan rättning:** `msft-cap-2025q2` och `msft-cap-2024q3` är kodade på en framåtblickande mening
  (#225) respektive en mindre uttrycklig mening (#284). Mer uttryckliga meningar om läget nu finns (#166 "demand
  remains higher than supply" och #174 "Demand continues to be higher than our available capacity"). Koden blir
  densamma (+1). Samtalet 2024-10-30 (#294, #310) säger att "some of that supply demand will match up" under H2 FY25.
  Det är förbehållet och inte "uttryckligen i balans", så det är rätt att det inte är kodat. Regeln bör förtydligas.
- **Fullständighet:** alla 16 samtal från microsoft.com och alla 367 SEC-dokument i B4:s korpus (korpusen jämfördes
  mot EDGAR, och ingen inlämning saknas) söktes igenom med ett eget kapacitetsmönster. För Amazon, Alphabet och Meta
  hittades inga fler kodbara uttalanden i SEC-dokumenten. Alphabets 10-K 2026-02-05 #286 ("increasingly constrained
  by the availability of power, water, and land") handlar om förutsättningar och inte om balansen mot efterfrågan.
  Samtalen FY23 Q2–FY24 Q2 har inga uttalanden om balansen.

### 3.3 Nyckeltal, stickprov (seed 20261124, 20 % av 136 = 27 rader)

amzn-chip-02, googl-aio-01, googl-tok-01, msft-aai-01/02, msft-aimau-02, msft-aip-2023q4/2025q1/q2/q3, msft-airr-00,
msft-aoai-03, msft-az-2023-07-25-cc, msft-az-2025-04-30-cc/-rep, msft-az-2025-07-30-rep, msft-az-2025-10-29-cc,
msft-az-2026-04-29-cc, msft-az-r24-q1c (omräknad FY24 Q1 i konstant valuta 30 %, ur "31% / 30%"), msft-cps-01,
msft-ftok-01, msft-ghbo-02, msft-lirr-01, msft-m365s-01/03, msft-ppai-05 och msft-ppcp-01: **0 fel av 27.** Hash,
värde, typ (point/approx/min mot "about"/"over"), definition och period stämmer. Tabellraderna för Azure lästes i
sin helhet.

Sökningen efter saknade rader (tokens, run-rate, användare, organisationer och backlog i alla 383 dokument, mot
lagrade hashar och värden) gav R5-F6. Övriga träffar är dokumenterade undantag: molnets årstakt, Connect, GitHub,
multiplar och tillväxt utan nivå, kunders siffror och hypotetiska formuleringar (Amazons "~$50 billion" om
chipverksamheten vore fristående).

### 3.4 Leasing, stickprov (seed 20261124, 20 % av 190 = 38 rader)

Alla 38 stämmer: värde, typ (operating/finance/short/long/total), balansdag och filed. Det gäller också Metas
sidbrytning 2021Q2 (#397), Amazons totalkolumn och CoreWeaves "aggregate … undiscounted". Alla 190 rader
kontrollerades automatiskt i nyhämtade dokument: 190 av 190 har lagrad SHA-256 på angiven plats. Belopp i
kandidatmeningar som inte är kodade är förskott (Alphabet), avvecklingskostnader (Amazon), maximal exponering mot
VIE (CoreWeave) och avtal efter balansdagen (Meta juli 2026, 68 mdr). De är alla rätt bortvalda.

Täckningen jämfördes mot EDGAR (alla 10-Q/10-K sedan 2019 för sex bolag). Filingar utan rad: Alphabets, Metas och
Amazons 10-K för 2018 (före ASC 842, inget belopp), Amazon 2019Q1–2020Q3 (inget belopp) och Oracle 17 stycken. Av
Oracles har 13 inget belopp, och 4 är R5-F7.

### 3.5 Planer, stickprov (seed 20261124, 20 % av 127 = 25 rader)

crwv-p001/p007/p016/p018/p021/p032/p033/p037, googl-p003, meta-p004/p010/p018/p019/p020/p028/p035,
msft-p007/p009/p010/p016/p021/p023 och orcl-p001/p003/p008: **0 fel av 25.** Typ (min "more than"/"surpassed",
approx), horisont, period och definition stämmer.

D1:s fem tolkningar:

1. "This year" läses som FY26. Det är rimligt, eftersom Microsoft talar i räkenskapsår, men det är inte entydigt.
   Godtas.
2. Fördubblingsmålen godtas. Tvåårsperioden från 2025-10-29 behålls vid upprepning ("remain on track"), men se
   R5-F12.
3. 8 GW (aktiv eller kontrakterad effekt anges inte) och 5 GW AI-fabriker har separata koder. Godtas.
4. Metas åtagandetotal: se R5-F11.
5. Oracles byte 2026-08 ger ny kod. Det är rätt.

Fullständighet: D1:s korpus jämfördes mot EDGAR, och inget saknas (541 dokument, varav en saknad samtalssida). En
sökning i alla dokument efter capex-meningar med framåtblick och efter Oracles inköpsåtaganden, mot hashar i både
D1 och E1, gav inga fler planer för nästa år i SEC-dokumenten. Microsofts tidigare uttalanden (FY27 i samtalet
2026-07-29) hör till E1. En jämförelse mot E1:s rader för nästa år visar att alla har en xref i D1, utom `meta-01`
och `meta-06` (före korpusen) och `msft-16` (R5-F10).

### 3.6 Labbens intäkter

| Rad | Kontroll | Resultat |
|---|---|---|
| ant-11 | S-1/A 0001628280-26-072484, nyhämtad, mening #3474 | Hash, värde (approx 81 000), period och `known_from` (filingDate 2026-11-10, accepterad 06.29 ET) stämmer. S-1 2026-10-26 och S-1/A 2026-11-02 har "$ as of October 31, 2026" utan värde. Värdet upprepas oförändrat i S-1/A 11-17, 424B4 och tre FWP. Inget tidigare SEC-dokument har värdet. |
| ant-01–10, ant-cc-01–03 | Sparade meningar och B6:s råkopior | Hash, tal, förbehåll, period och omfång stämmer med reglerna i `labbintakter.md`. datePublished = `known_from` för alla. **Ej oberoende verifierade.** |

Stickprovet (seed 20261124, 3 rader: ant-03, ant-04, ant-cc-02) ingår i tabellen. En sökning i alla 1 129 sparade
sidor efter run-rate och ARR med dollarbelopp gav inga saknade rader, bara en upprepning (Claude Code 1 mdr) och
kunders ARR. Anmärkning: noten på ant-09 säger "no new vintage", men raden laddas som en egen punkt (2026-04-20),
vilket är rätt för frekvens D. Det är noten som behöver rättas.

## 4. Rättningar som krävs

1. **B4:** R5-F1 (ta bort raden), R5-F2a och F2b (tillämpa tolkning 7 konsekvent), R5-F3 (perioden 2026Q3), R5-F4
   och F5 (två rader), och R5-F6 (koda raderna eller lägg dem under "Inte kodat"). Därefter kan `publish=True`
   sättas för B4:s serier.
2. **A3:** R5-F7 (fyra Oracle-rader), R5-F8 (dokumentation och seriens start) och R5-F9 (Microsofts definitionsbrott).
3. **D1:** R5-F10 (Microsoft FY26), R5-F11 (Metas kod från 2025Q3), R5-F12 (två rader) och R5-F13 (Oracle feb 2024,
   eller ett skäl att inte koda).
4. **E1:** R5-F14 (Microsoft CY2026 cirka 170 mdr).
5. **B6:** rätta noten på ant-09. Nyhetsrumsraderna kan verifieras oberoende först om Johannes tillåter enstaka
   hämtning av de åtta citerade sidorna (B6:s rekommendation). Fram till dess gäller `publish=False`.

Varje rättning tar bort sin `xfail`-markering i `tests/test_r5_extraktion.py`.

## 5. Begränsningar (ärligt)

- Sökningarna efter saknade rader använder mönster över hela korpusen. De är bredare än spårens, men inte
  uttömmande. Nyckeltal med en annan ordalydelse än tokens, run-rate, användare, organisationer och backlog kan
  saknas.
- R5-F4, F5 och F6 bygger på R5:s läsning av reglerna. R5-F2 kräver ett val (tolkning 7 som den står, vilket är
  rekommendationen, eller en snävare regel och omkodning av 2022Q4).
- Samtal på andra bolags IR-sidor (abc.xyz, ir.aboutamazon.com, investor.nvidia.com, investor.oracle.com med flera)
  har inte prövats igen, eftersom de är kända som nekade. Inga värdar nekades i R5.
- Testsviten markerar fel med `xfail`. Den kontrollerar inte att de sparade meningarna i `data/raw` finns kvar.

## 6. Status efter rättning (spår X3, 2026-11-24)

Rättat på `auto7/x3-r5-rattning` enligt ägarens beslut 2026-11-23 ("R5:s tolkningsfrågor avgjorda"). Alla 26
`xfail`-markeringar är borttagna, och testerna går igenom som vanliga tester. **0 xfail kvar.** Varje ny rad har
URL (och accession för SEC), plats, SHA-256 av meningen (meningen bara i `data/raw`) och `known_from` = EDGAR:s
filingDate eller, för Microsofts samtal, dagen för 8-K:n med resultatet. Alla nya meningar togs fram ur dokumenten
igen, och deras SHA-256 är lika med R5:s. De nya och ändrade raderna kontrollerades också mot nyhämtade dokument
(19 dokument, ärlig klient, 0 fel). Ingenting hämtades från anthropic.com, claude.com eller platform.claude.com.

| Nr | Status | Rättning |
|---|---|---|
| R5-F1 | rättat | `nvda-cap-2025q3` borttagen; 2025Q3 är en lucka |
| R5-F2a | rättat | `nvda-cap-2025q1` = −2 (H20), tolkning 7 som den står |
| R5-F2b | rättat | `nvda-cap-2026q2` = 0, skälet i noten |
| R5-F3 | rättat | `nvda-capf-2026q1` period 2026Q3 |
| R5-F4 | rättat | `msft-cap-2025q1` = 0 |
| R5-F5 | rättat | `msft-capf-2024q2` = +1 |
| R5-F6 | rättat (kodat) | 8 rader med fem nya koder (`MSFT_SALES_COPILOT_ORGS`, `MSFT_COPILOT_SECURITY_PAID_CUSTOMERS`, `MSFT_FOUNDRY_CUST_ANTHROPIC_OPENAI`, `MSFT_FOUNDRY_CUST_MULTI_MODEL`, `MSFT_FOUNDRY_FABRIC_CUSTOMERS`). LinkedIn och MAI Code Flash står under "Inte kodat" i `ai_nyckeltal.md` |
| R5-F7 | rättat | fyra Oracle-rader (operating, MD&A) |
| R5-F8 | rättat | `finansiering.md` rättad; `lease_uncommenced_orcl` börjar 2023Q4. `lease_check` läser nu också meningen efter beloppet (Oracles MD&A) |
| R5-F9 | rättat | not på båda raderna; `lease_uncommenced_msft` avslutad med 2026Q1, ny serie `lease_uncommenced_msft_cond` från 2026Q2 |
| R5-F10 | rättat | `msft-p029`, xref `msft-16` |
| R5-F11 | rättat | `META_NONCANCEL_COMMIT_CLOUD` från 2025Q3; den gamla koden är avslutad. Testet väntade 6 rader, men det finns 5 (`meta-p030`, `p032`–`p035`) och inget sjätte uttalande. Testet är ändrat till 5, och stickprovsraden `meta-p035` har den nya koden |
| R5-F12 | rättat | `msft-p022` `point`; `msft-p025` kod `MSFT_OVERALL_CAPACITY` |
| R5-F13 | rättat (kodat) | `orcl-p011`, 4 400 MUSD, kod `ORCL_UNCOND_OBLIG_DC_CAPEX` (avslutad, ett värde) |
| R5-F14 | rättat | `msft-29` CY2026 approx 170 000, ny version av samma serie som `msft-26`, med not om definitionsbrottet (fler operationella hyror från 2026-07-29). Påverkar inte N1:s B2 |
| ant-09 | rättat | noten säger nu att raden laddas som en egen punkt (frekvens D) |

Ombyggda serier (`--rebuild`): `kpi_nvda_capacity_current/forward`, `kpi_msft_capacity_current/forward`, de fem
nya `kpi_msft_*`, `lease_uncommenced_msft`, `_orcl` och `_msft_cond`, `plan_meta_noncancel_commit_asof_value`,
`plan_meta_noncancel_commit_cloud_asof_value`, `plan_msft_capex_incl_fl_y_dir_growth_vs_prior`,
`plan_msft_overall_capacity_span2y_value`, `plan_orcl_uncond_oblig_dc_capex_asof_value` och
`guid_capex_msft_cy_lo/hi`.

**Publicering:** B4 (`kpi_*`), A3 (`lease_uncommenced_*`) och D1 (`plan_*`) har `publish=True`. Nvidias serier har
det redan. B6 (`lab_*`) och E1:s capex-guidance (`guid_capex_*`) har kvar `publish=False`.

**Kvar, utan rättning:** R5:s anmärkningar om `msft-cap-2025q2` och `msft-cap-2024q3` (koden blir densamma), och
förtydligandet av regeln för "some of that supply demand will match up" (inte kodat), står kvar som anmärkningar.
Nyhetsrumsraderna i B6 är fortfarande inte oberoende verifierade.
