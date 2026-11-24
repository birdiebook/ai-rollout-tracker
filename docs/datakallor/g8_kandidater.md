# Datakällor G8 v2: kandidater för arbete och produktivitet

Spår L1, körning 13. Kontrollerat 2026-11-24. Bara kartläggning: ingen kod, ingen data i git, och inga mått är
registrerade. Förslaget i slutet är inte förregistrerat och bygger inte på någon dataanalys.

**Varför:** G8 har i dag en källa (Indeeds AI-andel i nio länder), alltså en källfamilj. Med index v2 (K1) får G8
då inget tillstånd. Förslag 5 i [riktning.md](../riktning.md) vill ha minst tre oberoende familjer och en
förregistrerad design "exponerade mot mindre exponerade".

**Metod:** små anrop från sandlådan genom proxyn, ett i taget. User-Agent är projektets ärliga klient
`ai-rollout-tracker (github.com/birdiebook/ai-rollout-tracker)`. För `*.bls.gov` används projektets generiska
klientidentitet med kontaktadress ur `.env` (`SEC_USER_AGENT`), som spår M1 gör, eftersom BLS nekar klienter utan
kontakt: `download.bls.gov/pub/time.series/ce/ce.footnote` gav **HTTP 403** med standardklienten och 200 med den
generiska identiteten. Prover sparades utanför repot. FRED användes inte (villkoren begränsar ML-användning, spår I7).

**Statusnivåer** som i [g6_g7_g8.md](g6_g7_g8.md): **OK** = hämtat och villkor lästa. **PARTIAL** = hämtat men något
saknas (nyckel, historik, villkor). **BLOCKED** = gick inte att hämta ärligt. **Kommersiell klass** enligt
beslutspunkt 3 (`ja`, `nej`, `okänd`): den bygger på läst licenstext och gissas aldrig.

## Vad jag tittade på (läckage)

Inga värden efter 2022 för någon G8-kandidat har lästs. Det som syntes:
- **CES, CPS, JOLTS, OEWS, produktivitet:** serielistor, kodtabeller, fotnoter, första och sista period, antal
  månader och fotnotskoder för de sex senaste månaderna. Inga värden skrevs ut. I CES-vintagefilen syntes
  januari 1990-värdet för 518 och 513 i första kolumnen när strukturen lästes.
- **BTOS:** frågetexter och svarskategorier, och för Q8–Q10 bara celltypen per cykel (procent eller "."). När
  `AI Core Questions.xlsx` lästes syntes några värden för Q7 2025, alltså den befintliga G3-serien `btos_ai_use_v1`.
- **Indeed per yrke:** kolumnnamn, sektornamn, första och sista datum. Inga indexvärden.
- **JobTech:** antal annonser i januari 2019 (ett svar), och om annonser finns i en månad (ja/nej).
- **Anthropic Economic Index:** de sju första raderna i `job_exposure.csv`. Det är exponeringsvärden per yrke, inget utfall.

## Sammanfattning

| Källa | Värd | Status | Licens | Kommersiell | Historik | Frekvens | Värde för G8 |
|---|---|---|---|---|---|---|---|
| BLS CES, detaljerade branscher | download.bls.gov, www.bls.gov | OK | public domain | ja | 1990-01 (USA) | månad | högt: sysselsättning i exponerade branscher, release-daterad |
| BLS CPS, arbetslöshet per ålder, utbildning och yrke | download.bls.gov | OK | public domain | ja | 1985 (unga akademiker), 2000 (yrken) | månad | högt: unga akademiker och datayrken, NSA revideras inte |
| BLS JOLTS | download.bls.gov | OK | public domain | ja | 2000-12 | månad | lågt: bara sektornivå (51, 54–56) |
| BLS OEWS | www.bls.gov, download.bls.gov | OK | public domain | ja | 1997 | år (maj) | lågt för takt: treårigt rullande urval. Högt som vikter för exponering |
| BLS produktivitet (kvartal och bransch) | download.bls.gov | OK | public domain | ja | 1947 (kvartal), 1987 (bransch, år) | kvartal, år | medel: aggregatet isolerar inte AI |
| BLS API v1 | api.bls.gov | PARTIAL | public domain | ja | – | – | behövs inte, flatfilerna räcker |
| Indeed Hiring Lab, annonser per yrke | raw.githubusercontent.com, git | OK | CC BY 4.0 | ja | 2020-02-01 | dag | medel: samma plattform som dagens G8, ingen förperiod före pandemin |
| JobTech, historiska annonser (Sverige) | historical.api.jobtechdev.se | OK | CC0 | ja | 2016 | dag (aggregeras) | högt: annan utgivare, yrke (SSYK), förperiod 2016–2019 |
| Census BTOS Q9–Q10 (AI:s effekt på antal anställda) | www.census.gov | OK | public domain | ja | 202622 (2026-10) | 2W | högt men kort: två cykler. Takt först från 2027-10 |
| Anthropic Economic Index | huggingface.co | OK | CC BY (utan version), metadata säger MIT | ja | 2025-02 | oregelbunden | medel: användning per uppgift, en plattform. Bättre som exponeringsmått |
| St. Louis Fed, Real-Time Population Survey | www.stlouisfed.org m.fl. | BLOCKED | okänd | okänd | – | – | högt om den gick att nå: AI-användning bland arbetstagare |
| NY Fed, nyutexaminerade på arbetsmarknaden | www.newyorkfed.org | BLOCKED | okänd | okänd | – | – | låg extra nytta: bygger på CPS, som nås via BLS |
| Eurostat LFS, sysselsatta per NACE två siffror | ec.europa.eu | OK | CC BY 4.0 | ja | 2008Q1 | kvartal | medel: J62/J63 per land, brottsflaggor |
| SCB, AKU och nationalräkenskaper per SNI | api.scb.se | OK | CC0 | ja | 1981K1 (NR), 2020K1 (AKU) | kvartal | lågt: grova branscher |
| SCB, generativ AI hos individer (TAB6388) | api.scb.se | OK | CC0 | ja | 2024 | år | lågt för takt: tre år. Passar G3 |
| Exponeringsmått (Eloundou m.fl., AIOE, AEI, BLS-matris) | github.com, huggingface.co, www.bls.gov | OK/PARTIAL | se nedan | ja/okänd | – | – | behövs för designen, inte som serie |
| Lightcast, LinkedIn, ADP | – | BLOCKED | betalkälla | nej | – | – | otestat enligt uppdraget |

## BLS CES: sysselsättning per detaljerad bransch (USA)

| | |
|---|---|
| Åtkomst | `download.bls.gov/pub/time.series/ce/` → 200: `ce.series`, `ce.industry`, `ce.footnote`, `ce.data.50a.Information.Employment` (2,5 MB), `ce.data.60a.ProfessionalBusinessServices.Employment` (9,4 MB). Last-Modified 2026-11-10 13:30 GMT |
| Serier (SA, tusental) | `CES6054150001` datorkonsulter (5415), `CES6054151101` programmering på uppdrag (541511), `CES5051320001` mjukvaruförlag (5132), `CES5051800001` datacenter, databehandling och hosting (518), `CES6054160001` managementkonsulter (5416), `CES6056142001` kundtjänstcenter (56142), `CES6054110001` juridik (5411), `CES6054120001` redovisning (5412), `CES6054180001` reklam (5418), `CES6056140001` kontorsstöd (5614). NSA finns som `CEU…` |
| Historik | 1990-01 för alla. 5415, 518, 5416, 5411, 5412, 5418 och 5614 slutar 2026-10. 5132, 541511 och 56142 slutar 2026-09, alltså en månad senare publicering. Inga saknade månader. Oktober 2025 finns (fotnot F: "Initial release of October 2025 data") |
| Revideringar | två månatliga revideringar (fotnot P = preliminär) och en årlig benchmark med januaridata. Säsongsfaktorer räknas om årligen |
| Vintages | `www.bls.gov/web/empsit/cesvinall.zip` (3,1 MB, 226 filer) har alla publicerade värden per Employment Situation-release från 2003-05. **Men bara på supersektor, två och tre siffror:** 518 (273 releaser, 2003-05 till 2026-01) och 513 (från 2023-01, NAICS 2022), 541 och 561. Inte 5415, 5132, 5416 eller 56142. Zippen är senast ändrad 2026-03-06 och slutar med januarireleasen 2026 |
| Första publicering | Arkiverade Employment Situation (`www.bls.gov/news.release/archives/empsit_MMDDYYYY.htm`, lista i `www.bls.gov/bls/news-release/empsit.htm`, från 1994). Tabell B-1 i releasen visar 5415, 5416, 5411, 5412, 5413, 5418, 5613, 5614, 513 och 518 för månaden, de två föregående månaderna (andra och tredje skattningen) och samma månad året innan. Kontrollerat i releaserna 2016-02-05 och 2026-11-06. 5132, 541511 och 56142 finns inte i B-1 |
| `known_from` | releasedatum ur arkivlistan för värden i B-1 (första, andra och tredje skattningen). Arkivlistan länkar redan till novemberreleasen `empsit_12042026.htm`, som ger **404**. Ett datum räknas därför bara när arkivfilen finns. Flatfilernas Last-Modified (2026-11-10) är senare än releasen (2026-11-06) och duger inte som releasedatum. Värden som inte finns i B-1 (5132, 56142) får regelbaserad backfill och egna ögonblicksbilder framåt. **Läckagerisk:** benchmarkrevideringar för 4- och 6-siffriga branscher syns bara i aktuell vintage |
| Licens | "everything that we publish ... is in the public domain ... we do ask that you cite the Bureau of Labor Statistics as the source." (`www.bls.gov/opub/copyright-information.htm`). API-villkoren kräver dessutom att hämtdatum anges och texten "BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov." (`www.bls.gov/developers/termsOfService.htm`). **Kommersiell: ja** |
| Mäter för G8 | sysselsättning i branscher med stor andel exponerade yrken. Inte yrken: en programmerare på en bank räknas som bank |
| Status | **OK** |

## BLS CPS: arbetslöshet per ålder, utbildning och yrke (USA)

| | |
|---|---|
| Åtkomst | `download.bls.gov/pub/time.series/ln/` → 200: `ln.series` (15 MB, 68 626 serier), kodtabeller och fotnoter. Last-Modified 2026-11-06 13:30 GMT (releasedagen). Datafilen `ln.data.1.AllData` är 393 MB och hämtades inte |
| Serier (NSA, %) | `LNU04023018` unga akademiker: ej i utbildning, kandidatexamen eller högre, 16–24 år (1985-01–). `LNU04023068` samma ålder, gymnasium utan högskola (1985-01–). `LNU04027662` kandidatexamen+, 25 år och äldre (1992-01–). `LNU04034021` data- och matematikyrken (2000-01–). `LNU04032221` kontors- och administrationsyrken (2000-01–). `LNU04000000` alla (1948–). Detaljerade yrken (t.ex. programmerare, `LNU04096715`) finns bara som årsmedel 2023–2025 |
| Revideringar | NSA revideras inte, utom populationskontroller (fotnot 12: januari 2026 reviderades). SA revideras för fem år varje januari. Oktober 2025 samlades inte in (fotnot 10) |
| `known_from` | releasedatum för Employment Situation (samma arkiv som CES). NSA ger därför rena release-daterade rader utan backfill |
| Brott | yrken kodas enligt 2002 års Census-klassificering från 2000 (fotnot 3). Senare kodbyten (2020) är inte kontrollerade här |
| Licens | som CES. **Kommersiell: ja** |
| Mäter för G8 | ingången till arbetsmarknaden för unga akademiker, där exponerade uppgifter är vanligast, och arbetslöshet i datayrken. Urvalet för 16–24 år med examen är litet, så slumpfelet är stort |
| Status | **OK** |

## BLS JOLTS, OEWS och produktivitet

| Källa | Åtkomst | Historik och frekvens | Revideringar och `known_from` | Bedömning |
|---|---|---|---|---|
| JOLTS | `download.bls.gov/pub/time.series/jt/` → 200, Last-Modified 2026-11-03 | månad från 2000-12. Branscher bara på sektornivå: Information (510000), Professional and business services (540099), Finance and insurance m.fl. | månatlig och årlig revidering. Releasearkiv `www.bls.gov/bls/news-release/jolts.htm`, 226 releaser från 2008-02 | **OK**, men för grovt för exponering. Möjlig robusthetskontroll (avgångar och anställningar i 51 mot totalt) |
| OEWS | `www.bls.gov/oes/special-requests/oesm25nat.zip` → 200 (280 kB), årsfiler från 1997 (`oes97nat.zip`). Flatfilerna `oe.data.*` (332 MB) har bara senaste året (`oe.release`: 2025A01 = maj 2025) | år, referens maj. Maj 2025 kom 2026-05-15 | alla zip-filer har Last-Modified 2026-05-15 (omladdade), så det duger inte som releasedatum. Releasearkivet hittades inte (`ocwage.htm`, `oes.htm` → 404). **Releasedatum ej verifierade** | **OK** som vikter. Skattningarna bygger på tre års rullande urval, så årliga förändringar är utjämnade och passar inte som takt |
| Produktivitet, kvartal (`pr`) | `download.bls.gov/pub/time.series/pr/` → 200, Last-Modified 2026-11-05 | kvartal, nonfarm business från 1947 | preliminär, reviderad två gånger. Releasearkiv `prod.htm` (`prod2_*`), 151 releaser från 2008-02 | **OK** från primärkällan (i dag via FRED i G8-planen). Mäter hela ekonomin |
| Produktivitet per bransch (`ip`) | `download.bls.gov/pub/time.series/ip/` → 200, Last-Modified 2026-09-24 | år 1987–2025 | årlig revision | **OK**, men arbetsproduktivitet finns bara för mjukvaruförlag (NAICS 5112, äldre kod). För 5415 och 518 finns bara arbetade timmar. Sent (~9 månader) |

## BLS API v1

`POST api.bls.gov/publicAPI/v1/timeseries/data/` med två serier → 200 men `REQUEST_NOT_PROCESSED`: "Request could
not be serviced, as the daily threshold for total number of requests allocated to the user with registration key  has
been reached." Kvoten gäller den delade utgående IP-adressen, som i fas 1. `BLS_API_KEY` är inte satt. **PARTIAL.**
API:t behövs inte: flatfilerna och releasearkiven på `download.bls.gov` och `www.bls.gov` räcker.

## Indeed Hiring Lab: annonser per yrke

| | |
|---|---|
| Åtkomst | `git clone --filter=blob:none https://github.com/hiring-lab/job_postings_tracker` och `raw.githubusercontent.com/.../US/job_postings_by_sector_US.csv` (12 MB) → 200 |
| Innehåll | index för säsongsrensade annonser, 2020-02-01 = 100, sju dagars glidande medel, `total postings` och `new postings`, 47 yrkessektorer (`display_name`, Indeeds egen indelning efter normaliserade titlar, med exempel i `sector-job-title-examples.csv`). Sektorfiler för US, GB, DE, FR, CA och AU, inte IE |
| Historik | 2020-02-01 till 2026-11-13 (dag) |
| Vintages | git-historiken: 258 commits (`--first-parent`) på USA:s sektorfil från 2021-05-27. Uppdateras varje vecka. Ny säsongsrensning infördes i november 2024, och historiken reviderades då |
| `known_from` | som för AI-andelen: commit-dag + en dag ([indeed_vast_eia.md](../kallor/indeed_vast_eia.md)) |
| Licens | samma som AI-trackern: "The data generated by *Indeed Hiring Lab* are available under the Creative Commons Attribution 4.0 International License" (README och LICENSE i repot). **Kommersiell: ja** |
| Mäter för G8 | efterfrågan på exponerade yrken (Software Development, Customer Service, Administrative Assistance, Accounting, Media & Communications) mot mindre exponerade (Nursing, Construction, Driving, Food Preparation & Service, Loading & Stocking) |
| Begränsning | samma plattform och urval som dagens G8-serie. Enligt K1:s regel är det en egen familj (annat begrepp), men informationen är inte oberoende av plattformen. Indexet börjar 2020-02, så det finns ingen förperiod utan pandemin |
| Status | **OK** |

## JobTech: historiska platsannonser (Sverige)

| | |
|---|---|
| Åtkomst | `historical.api.jobtechdev.se/search` → 200 utan nyckel. Parametrar: `occupation-group` (SSYK 4), `occupation-field`, `historical-from`/`historical-to`, `limit=0` ger bara antal |
| Historik | annonser från 2016 (2015-06 tomt, 2016-01 har annonser) till 2026-11 (dag) |
| Licens | API-specifikationen: "Ads are licensed under CC0". Används redan i kpif-nowcast (J7). **Kommersiell: ja** |
| `known_from` | annonsens publiceringsdag är känd, men när annonsen kom in i det historiska API:t är inte belagt. **Ej verifierat.** Förslag: egna ögonblicksbilder framåt, och en konservativ eftersläpning för historiken som registreras |
| Mäter för G8 | annonsvolym per yrke i Sverige, från en annan utgivare än Indeed. Platsbankens marknadsandel ändras över tid, men ett förhållande mellan yrkesgrupper tar bort en del av det |
| Status | **OK** |

## Census BTOS: AI:s effekt på antal anställda

| | |
|---|---|
| Åtkomst | `www.census.gov/hfp/btos/downloads/National.xlsx` och frågeformuläret `BTOS Content V5 Core and SI Instrument - Cycle 2-Tagged.pdf` → 200. `www2.census.gov` (äldre frågeformulär) → proxyn nekar (CONNECT 403) |
| Frågor | Q9 (formulärets nr 26): "In the last six months, how did this business's use of Super Intelligence (formerly referred to as Artificial Intelligence or AI) affect the number of employees (total headcount) at this business?" Q10 (nr 27): samma om antalet nyanställda. Svar: Increased, Decreased, No change, Do not know. Q8 gäller anställdas användning av generativ AI (G3). Formuläret har också nr 29–30 (AI utför uppgifter som anställda gjorde, och hur många), men de finns inte i `National.xlsx` |
| Historik | från cykel 202622 (insamling 2026-10-19). Två cykler: 202622 (publicerad 2026-11-05) och 202623 (2026-11-19). Före 202622 står "." i alla 81 cykler. Det stämmer med [census_eu.md](../kallor/census_eu.md) |
| Population | frågan visas bara om företaget svarade ja på användning (nr 24). Om andelen avser alla företag eller bara AI-användare framgår inte av filen. **Måste verifieras** |
| `known_from` | *Publication Date* i filen, som för G3-serierna |
| Brott | nästa ändring av exemplen från 202702 (census_eu.md). Samma regel som v2 → v3 ger en ny serie |
| Licens | federal statistik, public domain. **Kommersiell: ja** |
| Mäter för G8 | företagens egen bedömning av AI:s effekt på personalstyrkan. Det är det mest direkta måttet bland kandidaterna, men takt (12 månader) finns först från 2027-10 |
| Status | **OK** (kort historik) |

## Anthropic Economic Index (Hugging Face)

| | |
|---|---|
| Åtkomst | `huggingface.co/api/datasets/Anthropic/EconomicIndex`, datasetkortet (`raw/main/README.md`), `.../commits/main` och `resolve/main/labor_market_impacts/job_exposure.csv` → 200, utan inloggning (`gated: False`) |
| Innehåll | sex releaser (mappar `release_2025_02_10` till `release_2026_06_26`) med användning per O*NET-uppgift och SOC-yrke, samt `labor_market_impacts/job_exposure.csv` (756 SOC-yrken, `observed_exposure`) och `task_penetration.csv`. Varje release är ett urvalsfönster, t.ex. en vecka (2025-11-13 till 2025-11-20). Releasen 2026-06-26 har kalendermånader (april och maj 2026). Schemat byts mellan releaserna |
| Licens | **motstridig text.** Metadata: `license: mit`. Kortets text: "Data released under CC-BY, code released under MIT License." Releasedokumentationen 2026-06-26: "Data released under CC-BY." Ingen CC-version anges. Båda tillåter kommersiell användning, så **kommersiell: ja** för Anthropics egna aggregat. Indatafiler från andra (BTOS, O*NET, IMF, befolkning) har egna villkor och ska inte hämtas härifrån |
| `known_from` | commit-datum på Hugging Face, inte mappnamnet. Exempel: `release_2025_09_15` laddades upp 2025-09-27. Tillägg i efterhand förekommer (2026-05-21, "Append restored per-country/country-state numeric distributions (additions-only)"). Git-historiken ger vintages |
| Ägarens beslut | pausen 2026-11-23 gäller anthropic.com, claude.com och platform.claude.com, eftersom de webbplatsernas villkor förbjuder automatisk åtkomst. Hugging Face är en annan värd, och datasetet har en uttrycklig öppen licens. Om pausen också ska gälla Anthropics dataset på andra värdar är en fråga för Johannes |
| Begränsning | en plattform (Claude), och utgivaren är ett av bolagen som projektet följer. Oregelbundna releaser och byten av schema ger ingen jämn tidsserie |
| Mäter för G8 | användning per uppgift och yrke. Det är ett exponeringsmått, inget utfall på arbetsmarknaden. `observed_exposure` bygger på användning 2025–2026 och är därför inte bestämt i förväg |
| Status | **OK** (åtkomst), beslut om användning väntar |

## St. Louis Fed: Real-Time Population Survey

`www.stlouisfed.org`, `research.stlouisfed.org`, `www.realtimepopulationsurvey.com` och `sites.google.com` → proxyn
nekar ("403 Forbidden (agent proxy: no rule or network setting allows this host)"). Varken data eller villkor gick
att läsa. Känt utan verifiering: undersökningen görs av Bick, Blandin och Deming och mäter generativ AI i arbetet
i vågor sedan 2024. Var data publiceras och under vilken licens är **okänt**. **BLOCKED.**

## NY Fed: arbetsmarknaden för nyutexaminerade

`www.newyorkfed.org` → proxyn nekar (samma fel). **BLOCKED**, licens okänd. Serierna bygger på CPS-mikrodata. BLS-serierna
ovan (`LNU04023018` med flera) täcker samma fråga med en annan åldersgräns (16–24 år i stället för NY Fed:s 22–27, ej verifierat här). Egna
snitt i CPS-mikrodata kräver Census API-nyckel: `api.census.gov/data/2019/cps/basic/jan?get=...` → 302 till
`missing_key.html` (metadata nås utan nyckel). Samma nyckel som M2 väntar på.

## Eurostat och SCB

| Källa | Åtkomst | Innehåll | Bedömning |
|---|---|---|---|
| Eurostat `lfsq_egan22d` | `ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/lfsq_egan22d` → 200 | sysselsatta per NACE Rev. 2 två siffror (J62 programmering, J63 informationstjänster), per land, kvartal 2008Q1–2026Q2, uppdaterad 2026-09-11. Sveriges J62 har brottsflagga `b` | **OK**, CC BY 4.0, kommersiell ja. Endast senaste vintage. Övergången till NACE Rev. 2.1 är inte kontrollerad |
| SCB TAB4936, TAB3786 | `api.scb.se/ov0104/v2beta/api/v2/` → 200 | sysselsatta enligt NR (1981K1–2026K2) och AKU (prel., 2020K1–2026K2), men bara grova branscher (t.ex. "informations- och kommunikationsföretag") | **OK**, CC0, kommersiell ja. För grovt för exponering |
| SCB TAB6388 | samma | användning av generativa AI-verktyg bland individer, per ålder och näringsgren (110 redovisningsgrupper), år 2024–2026 | **OK**, CC0. Tre årsvärden: ett G3-mått, och takt först 2027 |

## Exponeringsmått (indata till designen, inga serier)

| Mått | Åtkomst | Licens | Kommersiell | Kommentar |
|---|---|---|---|---|
| Eloundou m.fl. 2023, "GPTs are GPTs" | `github.com/openai/GPTs-are-GPTs` (git, 8 commits) | MIT (Copyright 2024 OpenAI) | ja | exponering per yrke ur O*NET-uppgifter, bedömd av människor och GPT-4. Bygger på uppgiftsbeskrivningar, inte utfall |
| Felten, Raj och Seamans, AIOE och AIIE | `github.com/AIOE-Data/AIOE` (git) | ingen licensfil | okänd | AIIE ger exponering per bransch (NAICS fyra siffror) direkt, men får inte användas förrän licensen är klar |
| Anthropic `job_exposure.csv` | huggingface.co | CC BY | ja | bygger på användning 2025–2026, alltså inte bestämt i förväg. Bara som robusthetskontroll |
| BLS Employment Projections-matrisen, SOC–CPS-nyckel | `www.bls.gov/emp/ind-occ-matrix/matrix.xlsx` (7,9 MB) → 200 | public domain | ja | bransch × yrke för senaste basåret |
| OEWS bransch × yrke maj 2021 | `www.bls.gov/oes/special-requests/oesm21in4.zip` (31 MB) → 200 | public domain | ja | yrkesfördelning per bransch före ChatGPT. Bästa vikten för exponering per bransch |
| O*NET | `www.onetcenter.org` → proxyn nekar | CC BY 4.0 enligt O*NET (ej verifierat här) | okänd | behövs bara om uppgiftsnivån ska räknas om. Eloundou-repot innehåller redan O*NET-filerna |

## Betalkällor och andra nekade värdar

- **Lightcast, LinkedIn Economic Graph och ADP** (mikrodata som i studier av unga i exponerade yrken): betalkällor
  eller avtal. **BLOCKED**, otestade enligt uppdraget. Kommersiell: nej.
- **Revelio Labs** (gratis "Public Labor Statistics"): `www.reveliolabs.com` → proxyn nekar. Licens okänd. **BLOCKED.**
- **QCEW** (kvartalsvis totalräkning per sexsiffrig NAICS): `data.bls.gov/cew/data/api/...` → proxyn nekar.
  **BLOCKED.** Det är den mest värdefulla nekade källan: fullständig räkning per detaljerad bransch, med cirka fem månaders eftersläpning (ej verifierat).
- **LEHD QWI** (jobbflöden per ålder och bransch): `lehd.ces.census.gov` → proxyn nekar. **BLOCKED.**
- **www2.census.gov** (BTOS:s äldre frågeformulär, CPS-filer): proxyn nekar. **BLOCKED.**

## Förslag (inte registrerat, ingen dataanalys)

### G8 v2: familjer

Grundregel: G8 v2 ska mäta utfall på arbetsmarknaden och produktivitet. Användningsmått (RPS, Economic Index, SCB
TAB6388, BTOS Q8) hör hemma i G3 eller som exponeringsmått. Minst tre familjer ska komma från olika utgivare, så att
kravet på tre familjer inte vilar på Indeed två gånger.

| # | Familj | Källa | Begrepp | Varför |
|---|---|---|---|---|
| 1 | `ai_postings_share_*` (finns) | Indeed | andel annonser som nämner AI | befintlig, nio länder |
| 2 | sysselsättningsgap, exponerade mot mindre exponerade branscher | BLS CES | skillnad i 12-månaderstillväxt | lång historik (1990), release-daterad via B-1, public domain |
| 3 | arbetslöshetsgap för unga akademiker | BLS CPS | `LNU04023018` minus `LNU04023068` | NSA revideras inte, historik från 1985, ett annat urval (hushåll) än CES |
| 4 | annonsgap, exponerade mot mindre exponerade yrken | JobTech | log-kvot av annonser per SSYK-grupp | annan utgivare och ett annat land, CC0, förperiod 2016–2019 |
| 5 (valfri) | arbetsproduktivitet | BLS `pr` | takt i nonfarm business | grenens huvudfråga. Isolerar inte AI, men hör till G8 |

Inte kärna nu: Indeeds index per yrke (samma plattform, ingen förperiod), BTOS Q9–Q10 (tas upp när takt finns,
tidigast 2027-10), Economic Index (en plattform, oregelbunden), OEWS (rullande urval) och JOLTS (sektornivå).
Med familj 1–4 har G8 fyra familjer, alla med kommersiell klass `ja`. G8 klarar då kravet på tre familjer även i den
kommersiellt rena delmängden.

### Design: exponerade mot mindre exponerade

1. **Exponering låses före utfallen.** Yrkesexponering från Eloundou m.fl. (MIT). Branschexponering = yrkesexponering
   vägd med yrkesfördelningen per bransch i OEWS maj 2021. Bara tjänstebranscher med egen CES-serie från 1990.
   Exponerade = högsta femtedelen, mindre exponerade = lägsta femtedelen. Gruppernas sysselsättning summeras.
   Listorna och vikterna skrivs in i registret. Economic Index och AIOE (när licensen är klar) används bara som
   robusthetskontroll.
2. **Par.** CES: exponerad grupp mot mindre exponerad grupp. CPS: unga akademiker mot unga med gymnasium, och data- och
   matematikyrken mot alla. JobTech: exponerade mot mindre exponerade SSYK-grupper. Exponering per SSYK kräver nyckeln
   SOC–ISCO–SSYK, vars tillgång inte är kontrollerad.
3. **Taktmått.** Gap G = log(exponerade) − log(mindre exponerade). För CPS är gapet skillnaden i procentenheter, som
   12-månaders glidande medel eftersom serierna är NSA. Takt = 12-månadersförändring i G. Statistiken D(T) =
   medeltakten under T månader efter brytpunkten 2022-12 minus medeltakten under tio år före. För den verkliga
   brytpunkten är det 2010–2019, med glappet 2020–2022 överhoppat. Placebodatumen får samma glapp. Tecknet (exponerade
   relativt mindre exponerade) låses i registret. Det väljer ingen riktning.
4. **MDE före öppning.** Förperioden är 1991–2019 för CES och 1986–2019 för CPS. 2020–2022 utesluts ur
   variansskattningen och redovisas som känslighet. Koden läser bara perioder ≤ 2022-10, och för serier med vintages
   `as_of(2022-11-30)`. Nollfördelningen fås med placebodatum: samma D(T) räknas med falska brytpunkter inne i
   förperioden, var tolfte månad, för T = 24, 36 och 48. MDE(T) = (1,96 + 0,84) × standardavvikelsen över
   placebodatumen (80 % styrka, 5 % tvåsidigt). Med tio års förfönster, glapp och T = 48 ryms ungefär ett dussin
   placebodatum för CES, så MDE är själv osäker och redovisas med det antalet. För JobTech är förperioden för kort för
   placebodatum. Där används en AR(1)-modell på månadsförändringar, och MDE redovisas som osäker. Indeed per yrke har
   ingen förperiod utan pandemin, så ingen MDE kan skattas ärligt.
5. **Ordning.** (a) Registerpost med definitioner, listor och metod → commit. (b) MDE på förperioden → commit med
   resultat. (c) Först därefter läses värden efter 2022.
6. **Rapportering.** D(T) med 95 %-intervall per familj, åt båda hållen. Täcker intervallet noll sägs det rakt ut:
   "ingen förändring i gapet större än X procentenheter per år syns ännu". Det är den troliga övre gränsen.
   Tre till fyra tester rapporteras med Holm-korrektion.
7. **Störfaktorer som samvarierar med exponering.** Räntecykeln 2022–2023 (tech är räntekänsligt), överanställningen i
   tech 2020–2022, skatteregeln för FoU-utgifter i USA (Section 174) från 2022, branschkodbytet till NAICS 2022 i CES
   (513/5132) och årliga benchmarkrevideringar. Designen mäter därför "AI och allt annat som samvarierar med
   exponering". Det ska stå i varje resultat.

### Vad som förblir omöjligt med gratis data

- **En kausal AI-effekt.** Det finns ingen exogen variation, bara exponering som samvarierar med räntor, skatt och pandemi.
- **Sysselsättning per detaljerat yrke i realtid.** OEWS är årlig och utjämnad, och CPS har för små urval per yrke.
- **Produktivitet per uppgift eller företag.** Bara aggregat och årliga branschserier, med ~9 månaders eftersläpning.
- **AI-användning bland arbetstagare i USA som tidsserie.** RPS är blockerad och licensen är okänd.
- **Mikrodata om löner och anställningar** (ADP, Lightcast, LinkedIn) är betalkällor.
- **Länder utanför USA, Sverige och EU:s LFS.** Kina och Indien saknas helt.

### Vad som behövs av Johannes

- **Beslut:** gäller pausen för Anthropics webbplatser också Anthropics dataset på Hugging Face? Rekommendation:
  pausen gäller inte där, eftersom villkoren är en uttrycklig öppen licens på en annan värd. Datasetet hämtas högst en
  gång per release och används bara som exponeringsmått, inte som kärnserie.
- **Värdar, om de ska öppnas,** i prioritetsordning: `data.bls.gov` (QCEW), `lehd.ces.census.gov` (QWI per ålder),
  `www.stlouisfed.org` och RPS-värden (licensen läses först), `www.onetcenter.org`, `www.newyorkfed.org` (låg nytta).
- **Nycklar:** `CENSUS_API_KEY` öppnar också CPS-mikrodata. `BLS_API_KEY` behövs inte.

### Kostnad i agentspår

Två byggspår och en granskning, som i riktning.md: (1) CES och CPS från flatfiler med datering ur releasearkiven.
`sources/bls.py` från spår M1 har redan tolkaren och arkivdateringen. (2) Exponeringslistor och JobTech per SSYK.
Därefter ett registerspår med MDE på förperioden, och en granskning innan utfallen öppnas.
