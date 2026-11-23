# Källa: SEC EDGAR XBRL-instanser (RPO, kontrakterad efterfrågan)

Spår A1 (steg 2, våg 1), led L4. Byggt och kontrollerat 2026-11-23 mot riktiga inlämningar. Kod:
`src/ai_tracker/sources/sec_rpo.py` (tolkning av balansfakta, tidsuppdelning, versioner) och
`src/ai_tracker/series/sec_rpo.py` (bolag och katalogposter). Inlämningslista, instanshämtning och cache
importeras från `ai_tracker.sources.sec_segment`, definitionsbrott från `sec_segment.definition_breaks` och
summan från `sec.aggregate` (se `docs/kallor/sec.md` och `docs/kallor/sec_segment.md`). Tester:
`tests/test_sec_rpo.py` (syntetiska instansdokument, inget nät). Hämtning:
`python -m ai_tracker.observations <nycklar>`. Här finns ingen analys. Om serierna blir kärnserier beslutas
i grinden G-A i `docs/mattregister.md`.

## Åtkomst och licens

- Samma väg som `sec_segment.md`: `data.sec.gov/submissions/CIK##########.json` ger 10-Q, 10-K och ändringar,
  och varje inlämnings XBRL-instans hämtas via `www.sec.gov/Archives/.../index.json`. Via `ai_tracker.http.get`
  med 5 anrop/s och deklarerad User-Agent från `.env` (`SEC_USER_AGENT`, aldrig i repot). Inga värdar nekades.
  Råkopiorna ligger i `data/raw/sec_segment/<datum>/` och återanvänds. Första körningen gjorde cirka 300 anrop
  (152 inlämningar), därefter hämtas bara nya inlämningar.
- Licens, samma som `sec.md` (sec.gov/privacy, kontrollerad 2026-11-23): *"Information presented on sec.gov
  is considered public information and may be copied or further distributed by users of the web site without
  the SEC's permission."* Därför `publish=True`, med SEC som källa.
- CIK, kontrollerade mot `name` i submissions: Microsoft 789019, Alphabet 1652044, Amazon 1018724, Oracle
  1341439 och **CoreWeave 1769628** (`CoreWeave, Inc.`, ticker CRWV, räkenskapsår till 31 dec).
- Varför instanser och inte companyfacts: totalen finns i companyfacts, men tidsuppdelningen är dimensionell
  och använder en **typad** dimension (ett datum), och companyfacts saknar dimensioner. En källa för alla
  serier ger samma `filed` för total och andel.

## Taggar

| Mått | Tagg och kontext |
|---|---|
| Totalt RPO | `us-gaap:RevenueRemainingPerformanceObligation`, balanskontext (instant) utan dimension. Amazon taggar från 2020Q3 totalen med bara startdatumaxeln (en enda hink, där Period1 är vägd återstående löptid), och då används den faktan om den är ensam |
| Andel i första hinken | `us-gaap:RevenueRemainingPerformanceObligationPercentage` med bara den typade axeln `RevenueRemainingPerformanceObligationExpectedTimingOfSatisfactionStartDateAxis` = hinkens startdatum |
| Hinkens längd | `us-gaap:RevenueRemainingPerformanceObligationExpectedTimingOfSatisfactionPeriod1` i samma kontext (P12M, P1Y, P24M, P2Y) |
| Äldre andelar | Microsoft FY2018 (10-Q 2017-10 till 2018-04): egen tagg `...PercentageOfRevenueExpectedToBeRecognizedOverNext12Months`. Oracle FY2019–FY2021 (2018-09 till 2021-03): odimensionerad us-gaap-procent. Enligt texten i 10-Q:n 2018-09-19 gäller andelen de närmaste 12 månaderna, och därför deklareras den som 12 månader |

- Fakta med fler dimensioner (kund, segment, närstående) tas inte med. Det gäller Microsofts kommersiella del
  (`MajorCustomersAxis = CommercialCustomersMember`, cirka 6 mdr USD lägre än totalen), Alphabets Google
  Cloud-RPO (från 2026Q1) och närståendedel samt Amazons RPO per kund (OpenAI, Anthropic). De ingår i totalen.
- **Första hinken** är hinken med tidigaste startdatum, förutsatt att den börjar högst 92 dagar efter
  balansdagen. Två taggningsfel hanteras därmed: Alphabet 2023-09-30 (startdatum 2023-07-01) och Oracle
  2026-02-28 (startdatum 2025-12-01, kopierat från föregående kvartal). Hinkens längd måste vara bolagets
  deklarerade horisont. Annars avbryts hämtningen med `HorizonError`, eftersom en ändrad horisont är ett
  definitionsbrott som ska få egna nycklar.
- Alphabets senare hink 2025Q1–Q3 är taggad som 0,0045 (avsett 45 %). Den används inte, eftersom bara den
  första hinken läses.
- Belopp: inom horisonten = total × andel ur samma inlämning, efter horisonten = total − inom. Andelarna är
  avrundade ("approximately"): hela procent för Oracle och CoreWeave, steg om 5 för Microsoft och oftast för Alphabet.
  Beloppen i `_12m`/`_24m` och `_after*` är därför ungefärliga. Microsofts ±2,5 procentenheter motsvarar
  ±17 mdr USD på 683 mdr.

**Horisont per bolag.** Bara Microsoft och Oracle anger 12 månader. Alphabet och CoreWeave anger bara 24
månader, och Amazon anger ingen uppdelning (bara vägd återstående löptid, `...Period1` som P6Y1M6D, som inte
tas med här). En uppdelning ≤12 månader finns alltså inte för GOOGL, AMZN och CRWV i XBRL.

**Övriga orderstockar (Oracle, CoreWeave).** Hela instanserna söktes efter `Backlog`, `Contracted`,
`Committed` och `RemainingPerformance`. Inget annat orderstocksbegrepp är taggat. CoreWeaves "revenue
backlog" i pressmeddelandena är inte RPO och finns inte i XBRL: 2025Q1 var RPO 14,7 mdr USD mot backlog
25,9 mdr, eftersom avtalet med OpenAI ännu inte ingick i RPO (bolaget utredde
fortfarande redovisningen, enligt 10-Q 2025-05-15), och 2025Q3 var RPO 50,0 mdr mot backlog 55,6 mdr. Den som behöver backlog-
måttet får extrahera det ur 8-K (program B4 eller D1).

## Period och kalendermappning

- RPO är en **balans** (stock), inte ett flöde. Ingen YTD-differens. Perioden är **kalenderkvartalet för
  balansdagen**.
- Microsoft, Alphabet, Amazon och CoreWeave har balansdagar på kalenderkvartalens sista dag.
- **Oracle** har balansdagar 31 aug, 30 nov, sista februari och 31 maj, som blir Q3, Q4, Q1 och Q2. Det är
  samma mappning som Oracles segmentintäkter (sep–nov = Q4). Balansen per 30 nov lämnas in runt den 10
  december, alltså före kalenderkvartalets slut, och därför har Oracle-serierna `lag_days = -31`. Läckage-
  kontrollen `known_from_after_period_end` tillåter då värden som är kända upp till 31 dagar före kvartalets
  slut. Värdet är verkligen känt när det lämnas in, men etiketten "Q4" betyder balansen per 30 november.
- `rpo_hyp4` summerar per kalenderkvartal. I Q4 är det alltså tre balanser per 31 dec och Oracles per 30 nov,
  och i övriga kvartal ligger Oracle också en månad före. Det följer måttet N6 i måttregistret
  ("RPO-summa för MSFT, GOOGL, AMZN och ORCL").

## Versioner (läckagekritiskt)

- `known_from` = inlämningens `filed`-datum. Det är konservativt, eftersom pressmeddelandet kommer samma dag
  eller tidigare.
- För varje inlämningsdatum d tar varje balansdag sitt senaste värde bland fakta inlämnade ≤ d. En rad skrivs
  när kvartalets värde är nytt eller ändrat med mer än 0,5 MUSD. En omräknad balans blir alltså en ny version
  med det senare datumet.
- Definitionsbrott: `sec_segment.definition_breaks` (mer än 2 % ändring av en tidigare inlämnad balans) körs
  på totalen per bolag. Upptäckta brott måste stämma med de deklarerade, annars `DefinitionBreakError`. En
  ändrad horisont ger `HorizonError`. **Inga brott hittades.**
- `rpo_hyp4`: ett kvartal finns först när alla fyra har lämnat in. Varje version dateras till den senaste av
  de fyra inlämningarna (`sec.aggregate`).
- I hämtningen 2026-11-23 rapporterar varje inlämning bara balansen för sin egen balansdag. Det finns inga
  jämförelsetal, och därför har serierna **inga revideringar** (en version per kvartal). Om ett bolag senare
  räknar om en balans blir det en ny version.

## Serier (alla kvartal, MUSD, release-daterade, G4)

| Nyckel | Innehåll | Från | Till | Kvartal |
|---|---|---|---|---|
| `rpo_msft` | totalt RPO, Microsoft | 2017Q3 | 2026Q3 | 37 |
| `rpo_msft_12m`, `rpo_msft_after12m` | inom 12 månader / därefter | 2017Q3 | 2026Q3 | 37 |
| `rpo_googl` | totalt RPO, Alphabet | 2019Q4 | 2026Q3 | 28 |
| `rpo_googl_24m`, `rpo_googl_after24m` | inom 24 månader / därefter | 2019Q4 | 2026Q3 | 28 |
| `rpo_amzn` | totalt RPO, Amazon (ingen tidsuppdelning taggad) | 2018Q1 | 2026Q3 | 35 |
| `rpo_orcl` | totalt RPO, Oracle (balansdag en månad före kvartalsslut) | 2018Q3 | 2026Q3 | 33 |
| `rpo_orcl_12m`, `rpo_orcl_after12m` | inom 12 månader / därefter | 2018Q3 | 2026Q3 | 33 |
| `rpo_crwv` | totalt RPO, CoreWeave | 2025Q1 | 2026Q3 | 7 |
| `rpo_crwv_24m`, `rpo_crwv_after24m` | inom 24 månader / därefter | 2025Q1 | 2026Q3 | 7 |
| `rpo_hyp4` | MSFT + GOOGL + AMZN + ORCL | 2019Q4 | 2026Q3 | 28 |

Sammanlagt 378 rader. Startpunkterna är bolagens första RPO-uppgift efter ASC 606: Microsoft
(10-Q 2017-10-26, FY2018 Q1), Amazon 10-Q 2018-04, Oracle 10-Q 2018-09. Alphabet taggade RPO först i
10-K för 2019. CoreWeaves första 10-Q kom 2025-05-15. Oracles balans per 30 nov 2026 (Q4) var inte inlämnad
vid hämtningen (väntas cirka 10 december).

## Kontroll mot bolagens rapporter

Senaste version, de 8 senaste kvartalen (2024Q4–2026Q3), jämförda med siffror som är kända ur bolagens
rapporter och pressmeddelanden (ur minnet, mdr USD). Här kontrolleras bara att datat är rätt, utan tolkning.

| Serie | Kvartal | Här | Rapporterat | |
|---|---|---|---|---|
| `rpo_msft` (total) | FY25 Q4 (2025Q2) | 375 | total 375, kommersiell 368 | stämmer |
| Microsoft, kommersiell del (inte en serie) | 2024Q4 / 2025Q1 / 2025Q3 / 2025Q4 | 298 / 315 / 392 / 625 | 298 / 315 / 392 / 625 | stämmer, och totalen ligger 6–7 mdr över |
| `rpo_msft_12m` (andel) | 2025Q2 / 2025Q4 | 40 % / 25 % | cirka 40 % / cirka 25 % | stämmer |
| `rpo_googl` | 2024Q4 / 2025Q1 / 2025Q2 / 2025Q3 | 93,2 / 92,4 / 108,2 / 157,7 | 93,2 / 92,4 / 108,2 / 157,7 | stämmer |
| `rpo_googl` | 2025Q4 | 242,8 | Google Cloud-backlog cirka 240 | stämmer i nivå |
| `rpo_amzn` | 2025Q1 / 2025Q2 / 2025Q3 / 2025Q4 | 189 / 195 / 200 / 244 | 189 / 195 / 200 / 244 (främst AWS) | stämmer |
| `rpo_orcl` | 30 nov 2024 / 28 feb 2025 / 31 maj 2025 | 97,3 / 130,2 / 137,8 | 97,3 / 130 / 138 | stämmer |
| `rpo_orcl` | 31 aug 2025 / 30 nov 2025 / 28 feb 2026 | 455,3 / 523,3 / 552,6 | 455 / 523 / 553 | stämmer |
| `rpo_orcl_12m` (andel) | 31 aug 2025 | 10 % | cirka 10 % | stämmer |
| `rpo_crwv` | 2025Q1 / 2025Q2 | 14,7 / 30,1 | 14,7 (10-Q-text, 58 % inom 24 mån) / backlog 30,1 | stämmer |
| `rpo_crwv` | 2025Q3 | 50,0 | backlog 55,6 | inte samma mått (se ovan) |

Intern kontroll: `rpo_hyp4` = summan av de fyra totalerna i varje kvartal (konstruktion och test), och
`_12m` + `_after12m` = totalen. Kunde **inte** kontrolleras ur minnet: Microsoft 2026Q1–Q3 (633 / 684 / 683),
Alphabet 2026Q1–Q3 (467,6 / 519,5 / 567,7), Amazon 2024Q4 och 2026Q1–Q3 (177; 364 / 496 / 578), Oracle
31 maj och 31 aug 2026 (638 / 664) och CoreWeave 2025Q4–2026Q3 (60,7 / 98,8 / 103,7 / 132,3). De är tagna
direkt ur bolagens XBRL, utan omräkning.

## Kända problem

- Andelarna är avrundade, och beloppen inom och efter horisonten är därför ungefärliga (se ovan).
- Horisonterna skiljer sig: 12 månader (MSFT, ORCL) och 24 månader (GOOGL, CRWV). De går inte att summera
  till en gemensam ≤12-månadersserie.
- Oracle ligger en månad före de övriga i `rpo_hyp4`.
- Microsofts RPO omfattar hela bolaget (kommersiellt plus en liten konsumentdel), Amazons och Alphabets
  domineras av AWS och Google Cloud men är bolagstotaler.
- CoreWeave 2025Q1 saknar OpenAI-avtalet i RPO (redovisningen utreddes). Det är bolagets egen redovisning
  och inget definitionsbrott i serien, eftersom ingen omräkning lämnades in.
- RPO-noten anger normalt bara den aktuella balansen. En rättelse kommer därför sannolikt bara via `10-Q/A`
  eller `10-K/A` (ny version), och inte som ett jämförelsetal.
