# Källa: finansiering av utbyggnaden (spår A3, led L5)

Byggt och kontrollerat 2026-11-23 mot riktiga data. Kod: `src/ai_tracker/sources/sec_financing.py` (balanser,
formler, nollfyllnad, härledda kvartal), `src/ai_tracker/series/sec_finansiering.py` (katalogposter, taggar per
bolag), `src/ai_tracker/sources/lease_commitments.py` och `src/ai_tracker/series/lease_commitments.py`
(leasingavtal som inte har börjat), `src/ai_tracker/lease_check.py` (stickprovskontroll). Tester:
`tests/test_finansiering.py`, `tests/test_lease_commitments.py` (fixturer, inget nät). Hämtning:
`python -m ai_tracker.observations <nycklar>`. Ingen analys här: inga takter eller jämförelser.

Kvartalslogik, versioner och kalendermappning för flöden är desamma som i `docs/kallor/sec.md`
(`sources/sec.py` återanvänds oförändrad).

## Åtkomst och licens

- XBRL: `data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (ett anrop per bolag). Dokument för
  leasingtexten och XBRL-instanser för nollkontrollen: `www.sec.gov/Archives/edgar/data/...` (oföränderliga,
  råkopior återanvänds). Filingslistor: `data.sec.gov/submissions/`. Allt via `ai_tracker.http` med deklarerad
  User-Agent från `.env` (skrivs aldrig ut). Inga värdar nekades.
- Licens, som i `sec.md` (sec.gov/privacy, kontrollerad 2026-11-23): *"Information presented on sec.gov is
  considered public information and may be copied or further distributed by users of the web site without the
  SEC's permission."* XBRL-serierna har `publish=True`. Leasingserierna har `publish=False` tills granskningen
  R5 är klar.
- CIK, verifierade mot `entityName`: Microsoft 789019, Alphabet 1652044 (+ Google Inc. 1288776), Amazon 1018724,
  Meta 1326801, Oracle 1341439, CoreWeave 1769628.

## Serier (kvartal, MUSD, release-daterade, gren G5)

`<mått>_<bolag>` för msft, googl, amzn, meta, orcl, crwv, och `<mått>_hyp4` = MSFT + GOOGL + AMZN + META.
Ett hyp4-kvartal finns först när alla fyra har ett värde, och varje version dateras till den senaste av de fyra
inlämningarna (`sec.aggregate`).

| Mått | Typ | Innehåll | Från (MSFT / GOOGL / AMZN / META / ORCL / CRWV; hyp4) |
|---|---|---|---|
| `debt_issued` | flöde | likvid från emission av långfristig skuld | 2011Q4 / 2010Q3 / 2015Q3 / 2016Q1 / 2013Q1 / 2024Q1; 2016Q1 |
| `debt_repaid` | flöde | amortering av skuld | 2011Q4 / 2010Q3 / 2014Q1 / 2016Q1 / 2014Q3 / 2024Q1; 2016Q1 |
| `interest_exp` | flöde | räntekostnad (resultaträkningen) | 2009Q3 / 2010Q3 / 2008Q1 / 2024Q3 / 2008Q3 / 2024Q1; 2024Q3 |
| `lt_debt` | balans | långfristig skuld inkl. kortfristig del, bokfört värde | 2012Q2 / 2024Q4 / 2012Q4 / 2022Q3 / 2019Q2 / 2025Q1; 2024Q4 |
| `fin_lease_liab` | balans | skuld för finansiell leasing | 2017Q2 / 2020Q2 / 2019Q1 / – / 2025Q1 / 2025Q1; ingen hyp4 |
| `op_lease_liab` | balans | skuld för operationell leasing | 2017Q2 / 2019Q1 / 2019Q1 / 2018Q4 / 2025Q1 / 2025Q1; 2019Q1 |
| `cash_sec` | balans | likvida medel + kortfristiga placeringar | 2009Q3 / 2009Q2 / 2009Q2 / 2012Q2 / 2018Q4 / 2025Q3; 2012Q2 |
| `fin_lease_liab_meta_a` | balans, år | Metas skuld för finansiell leasing per 31 december | 2019–2025 |
| `lease_uncommenced` | balans | tecknade leasingavtal som ännu inte börjat (text, se nedan) | 2018Q4 / 2019Q1 / 2020Q4 / 2019Q1 / 2025Q1 / 2025Q1 |

Senaste kvartal i hämtningen 2026-11-23: 2026Q3 för alla (Oracle: kvartalet juni–augusti 2026).
1 970 rader, 44 revideringar (versioner utöver den första).

## Taggar och formler per bolag

Flöden: prioritetslista per kvartal som i `sec.md`. Balanser: en formel är en summa av komponenter, och varje
komponent har en prioritetslista. Formlerna prövas i ordning per kvartal (`|` nedan = reserv).

| Mått | Bolag | Taggar / formel |
|---|---|---|
| debt_issued | MSFT | `ProceedsFromDebtMaturingInMoreThanThreeMonths` |
| | GOOGL | `ProceedsFromDebtNetOfIssuanceCosts` |
| | AMZN, CRWV | `ProceedsFromIssuanceOfLongTermDebt` |
| | META | `ProceedsFromIssuanceOfLongTermDebt`, `ProceedsFromDebtNetOfIssuanceCosts` |
| | ORCL | `ProceedsFromIssuanceOfSeniorLongTermDebt`, `ProceedsFromIssuanceOfLongTermDebt`, `ProceedsFromLongTermLinesOfCredit`, `ProceedsFromIssuanceOfDebt`, `ProceedsFromDebtNetOfIssuanceCosts` |
| debt_repaid | MSFT | `RepaymentsOfDebtMaturingInMoreThanThreeMonths` |
| | GOOGL | `RepaymentsOfDebtAndCapitalLeaseObligations`, `RepaymentsOfDebt` |
| | AMZN | `RepaymentsOfLongTermDebt`, `RepaymentsOfDebt` |
| | META, CRWV | `RepaymentsOfLongTermDebt` |
| | ORCL | `RepaymentsOfDebt`, `RepaymentsOfLongTermDebt` |
| interest_exp | MSFT, GOOGL, AMZN | `InterestExpenseNonoperating`, `InterestExpense` |
| | META | `InterestExpenseDebt`, `InterestExpenseNonoperating`, `InterestExpense` |
| | ORCL | `InterestExpense` |
| | CRWV | `InterestExpenseDebt` |
| lt_debt | MSFT | `LongTermDebtNoncurrent` + `LongTermDebtCurrent` \| `LongTermDebt` |
| | GOOGL, AMZN | `LongTermDebtNoncurrent` + `LongTermDebtCurrent` |
| | META | `LongTermDebtNoncurrent` + `LongTermDebtCurrent` \| `LongTermDebtNoncurrent` |
| | ORCL | `LongTermNotesAndLoans` + `NotesPayableCurrent` |
| | CRWV | `DebtInstrumentCarryingAmount` |
| fin_lease_liab | MSFT | `FinanceLeaseLiability` |
| | övriga | `FinanceLeaseLiability` \| `FinanceLeaseLiabilityCurrent` + `FinanceLeaseLiabilityNoncurrent` |
| op_lease_liab | alla | `OperatingLeaseLiability` \| `OperatingLeaseLiabilityCurrent` + `OperatingLeaseLiabilityNoncurrent` |
| cash_sec | MSFT | `CashCashEquivalentsAndShortTermInvestments` |
| | GOOGL | `CashCashEquivalentsAndShortTermInvestments` \| `CashAndCashEquivalentsAtCarryingValue` + `MarketableSecuritiesCurrent` |
| | AMZN, CRWV | `CashAndCashEquivalentsAtCarryingValue` + `MarketableSecuritiesCurrent` |
| | META | `CashAndCashEquivalentsAtCarryingValue` + (`MarketableSecuritiesCurrent`, `AvailableForSaleSecuritiesDebtSecuritiesCurrent`) |
| | ORCL | `CashAndCashEquivalentsAtCarryingValue` + `AvailableForSaleSecuritiesDebtSecuritiesCurrent` |

Val som spelar roll:
- **Skuld = bokfört värde, lång + kort del.** `LongTermDebt` är nominellt belopp hos Alphabet och Amazon
  (Amazon 2024: 58 000 mot bokfört 57 640) men bokfört hos Microsoft, så komponenterna används i första hand.
- **CoreWeave** taggar balansraderna för skuld med egna taggar från 2026Q2. `DebtInstrumentCarryingAmount`
  (utestående nominellt) finns för alla kvartal och används därför hela vägen, cirka 1 % över bokfört värde
  (2026Q1: 25 149 mot 24 859).
- **Oracle** saknar standardtagg för långfristig skuld. Serien är "notes payable and other borrowings", kort och
  lång del, och inkluderar företagscertifikat.

## Balanser (läckagekritiskt)

- Ett balansvärde är ett instant-fakta på periodens slutdag. Bara rapportdagar behålls: för varje 10-Q/10-K den
  senaste slutdag som förekommer i minst 25 % så många fakta som filingens vanligaste slutdag. Det tar bort
  instanter från andra dagar (händelser efter balansdagen, förvärvsdagar).
- Kalenderkvartal = kvartalet som innehåller räkenskapskvartalets mittpunkt, satt till slutdagen − 45 dagar. Det
  är samma regel som för flöden. Oracles 31 augusti blir Q3.
- Versioner: för varje inlämningsdag d gäller den senaste versionen inlämnad ≤ d. En ny rad skrivs när värdet är
  nytt eller ändrat med mer än 0,5 MUSD. Omräknade jämförelsetal blir nya versioner med det senare datumet.
- Summor: ett kvartal finns först när alla komponenter har ett värde, daterat till den senaste komponenten.
- **Oracle:** kvartalen slutar i aug/nov/feb/maj och lämnas in 10–20 dagar senare, alltså före slutet av det
  kalenderkvartal de mappas till. Alla `*_orcl` har `lag_days = −31`, samma lösning som för `rev_orcl_cloud`.

## Två luckfyllare för flöden

- **Nollfyllnad** (`debt_issued`, `debt_repaid`). En kassaflödesrad som är noll utelämnas ofta: Microsoft har
  inte emitterat långfristig skuld sedan FY2017 och tog bort raden i 10-Q för FY2026. Meta har aldrig amorterat
  långfristig skuld. En 10-Q/10-K som har finansieringssumman men ingen av måttets taggar får 0 för sin egen
  period (3 mån och YTD, inte jämförelsekolumnerna), men **bara om filingens egen XBRL-instans** (alla
  namnrymder, alltså även bolagens egna taggar) saknar ett begrepp som matchar måttets mönster
  (`^Proceeds…(Debt|Notes|Borrowing|Loan|Credit)` respektive `^Repayments…`, utom kortfristigt,
  företagscertifikat, placeringar och leasing). Annars lämnas en lucka, och den nekade filingen loggas
  (`REFUSED`). Bara filingar från 2016. Kontroller som gjordes: Amazons 10-Q 2016 nekades (nettotaggen
  `ProceedsFromRepaymentsOfLongTermDebtAndCapitalSecurities`). Oracles kvartal juni–aug 2024 hade
  `ProceedsFromLongTermLinesOfCredit`, som lades till i Oracles taggar. Ingen nolla i slutdatat revideras senare
  till ett annat värde (kontrollerat).
- **Härlett första kvartal** (`interest_exp`). Meta redovisar räntekostnaden bara i vissa 10-Q. Q1 =
  6M YTD − Q2 (3 mån) ur samma filing, daterad till den filingen.

## Leasingavtal som inte har börjat (`lease_uncommenced_*`, text)

Bolagen redovisar i leasingnoten avtal som är tecknade men inte har börjat (ingen nyttjanderätt eller skuld
ännu), till exempel Microsofts "additional leases, primarily for datacenters, that had not yet commenced of $X
billion". Det finns ingen standardtagg, så siffran extraheras ur texten.

- **Metod.** Alla 10-Q/10-K sedan 2019 (ASC 842) hämtas (EDGAR-arkivet, primärdokumentet), görs om till text
  och delas i meningar (`guidance_capex.sentences`, plus brytning av tabeller som saknar punkt). Kandidater är
  meningar om leasing som "not yet commenced", "expected to commence", "additional lease commitments" och
  liknande. Agenten har läst varje kandidat och valt noten: i en 10-Q kommer noterna före MD&A och i en 10-K
  efter. Kandidater om händelser efter balansdagen, joint ventures, förskott och avvecklade avtal valdes bort.
  Agenten rättade det som det förifyllda arbetsbladet tog fel på (Microsofts 10-K 2020 och 2021 pekade på fel
  mening, och Metas 10-Q 2021Q2–Q3 har en sidbrytning mitt i meningen, så beloppet ligger i nästa del).
- **Lagring.** `curated/lease_commitments.csv`, en rad per belopp: id, company, period (balansdag), lease_type,
  value (MUSD), unit, filed, form, accession, source_url, locator (`sentence #k`), sentence_sha256 och note.
  Meningen sparas bara i `data/raw/lease_commitments_sentences/<id>.txt` (gitignorerad). `known_from` = `filed`
  (EDGAR-inlämningsdagen; beloppet finns inte i pressmeddelandet).
- **lease_type.** operating och finance (Microsoft till och med FY2025 Q3, Meta till 2023), short_term och
  long_term (Alphabets 10-K delar upp efter löptid), total (ett belopp). Serien per bolag är totalen, eller
  summan av delarna ur samma filing. Meta 2024Q1–Q3 och Oracle till och med FY2024 anger bara operationell
  leasing.
- **Definitioner skiljer sig.** Alphabet, Meta och CoreWeave anger framtida odiskonterade betalningar (Alphabet
  utan köpoptioner, utom 2025Q3). Amazon: totalkolumnen i raden "Leases not yet commenced" i åtagandetabellen,
  från 2020Q4. Microsoft: "leases ... of $X" utan angiven bas. Oracle: "additional lease commitments", före
  FY2025 bara operationell, och i 10-Q för nov 2022 och feb 2023 bara i MD&A.
- **Täckning.** 190 rader: MSFT 58 (2018Q4–2026Q3), GOOGL 36 (2019Q1–), AMZN 24 (2020Q4–), META 51 (2019Q1–),
  ORCL 14 (FY2020–), CRWV 7 (2025Q1–). Oracle anger inget belopp i flera 10-Q 2019–2024, så serien
  `lease_uncommenced_orcl` börjar efter sista luckan (2025Q1). Alla rader finns kvar i CSV:n.
- **Självkontroll.** `python -m ai_tracker.lease_check` hämtar om dokumenten för ett stickprov (20 %, minst
  en rad per bolag). Det kontrollerar att meningen på platsen har lagrad SHA-256, att beloppet står i meningen
  och att meningen, eller den före, handlar om leasing som inte har börjat. Körning 2026-11-23: 38 rader i
  stickprovet, 0 fel, 0 flyttade. Dessutom står beloppet i den sparade meningen för alla 190 rader.
- **Granskning R5** läser om källorna innan serierna används. Fram till dess gäller `publish=False`.

## Kontroll mot rapporterade siffror

Jämfört med bolagens egna balans- och resultaträkningar (senaste version, MUSD):

| Serie och period | Värde | Bolagets siffra |
|---|---|---|
| `cash_sec_msft` 2024Q2 (30 juni 2024) | 75 543 | cash, cash equivalents and short-term investments 75 543 |
| `lt_debt_msft` 2024Q2 | 44 937 | long-term debt 42 688 + current portion 2 249 |
| `fin_lease_liab_msft` 2024Q2 | 27 145 | total finance lease liabilities 27 145 |
| `interest_exp_msft` FY2024 (summa av fyra kvartal) | 2 935 | interest expense 2 935 |
| `cash_sec_googl` 2024Q4 | 95 657 | cash, cash equivalents and marketable securities 95 657 |
| `lt_debt_googl` 2024Q4 | 11 882 | long-term debt 10 883 + current 999 |
| `cash_sec_amzn` 2024Q4 / 2023Q4 | 101 202 / 86 780 | 78 779 + 22 423 / 73 387 + 13 393 |
| `lt_debt_amzn` 2024Q4 | 57 640 | long-term debt 52 623 + current portion 5 017 |
| `interest_exp_amzn` 2023 / 2024 | 3 182 / 2 406 | interest expense 3 182 / 2 406 |
| `debt_issued_amzn` / `debt_repaid_amzn` 2022 | 21 166 / 1 258 | proceeds from long-term debt 21 166 / repayments 1 258 |
| `cash_sec_meta` 2024Q4 / 2023Q4 | 77 815 / 65 403 | 77,81 / 65,40 mdr USD |
| `lt_debt_meta` 2024Q4 | 28 826 | long-term debt 28 826 |
| `debt_issued_meta` 2022 / 2023 | 9 921 / 8 455 | proceeds from long-term debt 9 921 / 8 455 |
| `cash_sec_orcl` 2024Q2 (31 maj 2024) | 10 661 | cash 10 454 + marketable securities 207 |
| `interest_exp_orcl` FY2024 | 3 514 | interest expense 3 514 |

Alla stämmer. Siffrorna för 2025–2026 kunde inte kontrolleras ur minnet, men summor och komponenter går ihop.
Exempel: MSFT 2026Q3, `LongTermDebt` 35 481 = 31 090 + 4 391.

## Kända problem

- **`lt_debt_googl` börjar 2024Q4.** 2020–2024 taggade Alphabet balansraden "long-term debt" som
  `LongTermDebtAndCapitalLeaseObligations`, det vill säga inklusive finansiell leasing. Därför börjar
  `lt_debt_hyp4` också 2024Q4 (8 kvartal).
- **Metas finansiella leasingskuld finns bara i 10-K.** Det gäller både companyfacts och 10-Q-instanserna
  (kontrollerat för 2026Q3). Därför finns ingen kvartalsserie för Meta och ingen `fin_lease_liab_hyp4`, bara
  årsserien `fin_lease_liab_meta_a`.
- **Metas räntekostnad** redovisas från 2024Q3 utan luckor (Q1 härleds). Därför börjar `interest_exp_hyp4`
  2024Q3. Före 2022 hade Meta ingen skuld.
- **Alphabets emissions- och amorteringsrader** omfattar mer än obligationer, till exempel 2022: 52 872 i
  emission och 54 068 i amortering, utan obligationsemission. Bruttoflödena är alltså mycket större än
  förändringen i obligationsskulden. Före 2024 ingick troligen amortering på finansiell leasing i
  `RepaymentsOfDebtAndCapitalLeaseObligations` (ej verifierat).
- **Amazon räknade om** emission och amortering 2016–2020 (omklassning mellan lång- och kortfristig upplåning).
  Det ger 8 revideringar per serie, och den första versionen 2019Q2–2020Q1 är högre än den senaste.
- **Oracle byter taggar** mellan filingar. Kvartal räknas då med skarvning per faktaperiod (`sec.quarters_at`).
  Oracles räntekostnad 2009Q3–2010Q2 hade fel tecken i den första versionen och rättades året efter.
- **`cash_sec_googl` 2026Q2** hoppar från 126 840 till 242 474 genom `MarketableSecuritiesCurrent`. Serien
  följer bolagets egen summa, som kan inkludera marknadsnoterade aktieinnehav. Det har inte analyserats.
- **`cash_sec_crwv` börjar 2025Q3.** `MarketableSecuritiesCurrent` taggas först då, och kassan ensam används
  inte som reserv.
- **Nollfyllnaden börjar 2016.** Därför börjar Metas skuldflöden och `debt_*_hyp4` 2016Q1.
- Seriernas definitioner skiljer sig mellan bolag (se noter i katalogen). Måtten för L5 låses i måttregistret
  (grind G-A) innan något räknas på dem.
