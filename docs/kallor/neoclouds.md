# Neomoln och Oracle (ledet L5, grenarna G5 och G4): Oracle, CoreWeave, Nebius och IREN

Spår A2b, steg 2. Byggt och kontrollerat 2026-11-23 mot riktiga inlämningar. Bara data: inga takter,
samband eller prognosvärden är beräknade.

Kod: `src/ai_tracker/series/neoclouds.py` (`SPECS`) och `src/ai_tracker/sources/nebius_sec.py` (Nebius 6-K,
nytt). Kvartals- och versionslogiken importeras oförändrad från `sources/sec.py` (se `sec.md`),
brottskontrollen från `sources/sec_segment.py` (`sec_segment.md`) och härledningen Q1 = 6M − Q2 från
`sources/sec_financing.py` (`finansiering.md`). Tester: `tests/test_neoclouds.py` (syntetiska fixturer, inget
nät). Hämtning: `python -m ai_tracker.observations <nycklar>`.

Redan byggt i andra spår och inte dubblerat här: RPO för Oracle och CoreWeave (`rpo.md`), skuld, ränta,
leasing och kassa för Oracle och CoreWeave (`finansiering.md`) och Oracles molnsegment `rev_orcl_cloud` och
`rev_orcl_oci` (`sec_segment.md`).

## Serier (alla kvartal, MUSD, release-daterade, `publish=True`)

| Nyckel | Gren | Innehåll | Från | Till | Kvartal | Reviderade kvartal |
|---|---|---|---|---|---|---|
| `rev_orcl` | G4 | Oracle, totala intäkter | 2008Q3 | 2026Q3 | 73 | 4 |
| `capex_orcl` | G5 | Oracle, köp av anläggningstillgångar | 2010Q3 | 2026Q3 | 65 | 0 |
| `ocf_orcl` | G5 | Oracle, operativt kassaflöde | 2008Q3 | 2026Q3 | 73 | 4 |
| `rev_crwv` | G4 | CoreWeave, totala intäkter | 2024Q1 | 2026Q3 | 11 | 0 |
| `capex_crwv` | G5 | CoreWeave, köp av anläggningstillgångar (kontant) | 2024Q1 | 2026Q3 | 11 | 0 |
| `ocf_crwv` | G5 | CoreWeave, operativt kassaflöde | 2024Q1 | 2026Q3 | 11 | 0 |
| `rev_nbis` | G4 | Nebius, intäkter (koncernen, kvarvarande verksamhet) | 2024Q1 | 2026Q3 | 11 | 0 |
| `capex_nbis` | G5 | Nebius, köp av anläggningstillgångar och immateriella tillgångar | 2024Q1 | 2026Q3 | 11 | 0 |
| `ocf_nbis` | G5 | Nebius, operativt kassaflöde, kvarvarande verksamhet | 2024Q1 | 2026Q3 | 11 | 0 |
| `capex_iren` | G5 | IREN, köp av anläggningstillgångar | 2024Q3 | 2026Q3 | 9 | 0 |
| `ocf_iren` | G5 | IREN, operativt kassaflöde | 2024Q3 | 2026Q3 | 9 | 0 |

Hämtning 2026-11-23: 11 serier och 336 rader. Oracles revideringar: intäkterna 2017Q3–2018Q2 räknades om med
ASC 606 i jämförelsetalen för FY2019 (−0,3 till −2,1 %, t.ex. 2018Q2 11 252 → 11 014), och OCF 2015Q3–2016Q2
räknades om i FY2017 (+15 till +63 MUSD, troligen ASU 2016-09). Båda är vanliga versioner med det senare
datumet. Oracles kvartal sep–nov 2026 (Q2 FY2027) var inte inlämnat vid hämtningen.

## Åtkomst och licens

- SEC EDGAR via `ai_tracker.http` (5 anrop/s per värd, deklarerad User-Agent från `.env`, aldrig i repot):
  companyfacts för Oracle, CoreWeave och IREN; submissions, `index.json` och 6-K-bilagor för Nebius. Inga
  värdar nekades. Råkopiorna av Nebius-dokumenten ligger under `data/raw/sec_segment/` (samma cache som
  instanserna) och återanvänds.
- Licens, kontrollerad på sec.gov/privacy 2026-11-23: *"Information presented on sec.gov is considered public
  information and may be copied or further distributed by users of the web site without the SEC's permission.
  Please consider appropriate citation to the SEC as the source."* Därför `publish=True`, med SEC som källa.
  Nebius siffror kommer ur en lagstadgad inlämning (6-K), och bara extraherade siffror publiceras, med
  källhänvisning, aldrig text.
- CIK verifierade mot `entityName`/`name`: Oracle 1341439 (`ORACLE CORP`), CoreWeave 1769628
  (`CoreWeave, Inc.`), Nebius Group N.V. 1513845 (tidigare Yandex N.V.), IREN 1878848 (`IREN Limited`).

## known_from

**Regel: `known_from` = inlämningsdatum (`filed`) för 10-Q/10-K, och för Nebius 6-K:ns inlämningsdatum.**
Pressmeddelandet kommer samma dag eller tidigare (Nebius Q3 2025: pressmeddelande 11 november, 6-K
12 november), så regeln är konservativ. Varje inlämning är en version, och jämförelsetal ger bara en ny rad
om värdet ändrats mer än 0,5 MUSD.

Belägg: avstånd från kalenderkvartalets slut till första egna inlämning (jämförelsetal i senare dokument
undantagna). Aktualitetsgränsen (`Spec.max_age_days`) är största avståndet + 92 + 30, som i `halvledare.md`.

| Bolag | Period | Min | Max | `lag_days` | Aktualitetsgräns |
|---|---|---|---|---|---|
| Oracle | 2015–2026 | −21 | −3 | **−31** | −3 + 92 + 30 = 119 |
| CoreWeave | 2025–2026 | 38 | 61 (10-K) | 45 | 61 + 92 + 30 = 183 |
| Nebius | 2024–2026 (alla pressmeddelanden) | 31 | 51 | 45 | 51 + 92 + 30 = 173 |
| IREN | 2025–2026 | 36 | 58 (10-K) | 40 | 58 + 92 + 30 = 180 |

## Kalenderkvartal

Kalenderkvartal = kvartalet som innehåller räkenskapskvartalets mittpunkt (`sec.calendar_quarter`), samma
regel som i `sec.md` och `halvledare.md`.

- **Oracle** har räkenskapsår till 31 maj och kvartal som slutar 31 aug, 30 nov, sista februari och 31 maj.
  Jun–aug räknas som Q3, sep–nov som Q4, dec–feb som Q1 och mar–maj som Q2: samma mappning som
  `rev_orcl_cloud`, `rpo_orcl` och finansieringsserierna. Oracle ligger alltså ungefär en månad **före**
  kalenderkvartalet, och inlämningen kommer 8–21 dagar före kalenderkvartalets slut. Därför `lag_days = −31`:
  läckagekontrollen `known_from_after_period_end` tillåter då värden som är kända upp till 31 dagar före
  kvartalets slut. Värdet är verkligen känt vid inlämningen, så det är ingen läckage, men etiketten "Q4"
  betyder sep–nov. Testet `test_oracle_offset_quarter_passes_leakage_check` kör kontrollen.
- **CoreWeave** och **Nebius** har kalenderår. **IREN** har räkenskapsår till 30 juni, så kvartalen är
  kalenderkvartal.

## Taggar och rader

| Serie | Källa | Taggar eller rad (prioritet) | Kommentar |
|---|---|---|---|
| `rev_orcl`, `rev_crwv` | companyfacts | `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet` | som `sec.md` |
| `capex_orcl`, `capex_crwv`, `capex_iren` | companyfacts | `PaymentsToAcquirePropertyPlantAndEquipment` | kontant, ur kassaflödet |
| `ocf_orcl`, `ocf_crwv`, `ocf_iren` | companyfacts | `NetCashProvidedByUsedInOperatingActivities`, `...ContinuingOperations` | Oracle använde ContinuingOperations 2012–2018 |
| `rev_nbis` | 6-K | rad `Revenues` i tabellen *Consolidated results* | koncernen: Nebius AI-moln, Avride och TripleTen |
| `capex_nbis` | 6-K | rad `Purchases of property, plant and equipment` / `Purchases of property and equipment (and intangible assets)` i *Selected consolidated cash flow data* | samma post under tre etiketter; lagras som positivt belopp |
| `ocf_nbis` | 6-K | rad `... operating activities – continuing operations` i samma tabell | kvarvarande verksamhet; totalen inkl. avvecklad verksamhet används inte |

**CoreWeave.** XBRL finns först från första 10-Q (2025-05-15). S-1 och 424B (mars 2025) har ingen
finansiell XBRL (companyfacts har bara 10-Q, 10-K, DEF 14A och ett 424B5 med omslagsfakta), så kvartalen
2024Q1–Q4 kommer från jämförelsetalen i 10-Q för 2025 och 10-K för 2025, och deras första version dateras
2025-05-15 till 2026-03-02. Det är konservativt (de var publika i S-1 redan i mars 2025). CoreWeave
rapporterade i tusental till och med 10-K för 2025 och i miljoner från 2026. Jämförelsetal som bara avrundar
ett tidigare värde till hela miljoner (2025Q2: 1 212,788 → 1 212) är ingen revidering och tas bort
(`neoclouds.rounding_revisions_dropped`).

**CoreWeaves capex** här är den kontanta raden i kassaflödet. Bolagets egen capex i pressmeddelandena är
periodiserad (inklusive levererad men obetald utrustning) och skiljer sig därför, i båda riktningarna. GPU:er
som finansieras via leverantörer eller leasing syns inte i den kontanta raden. Leasingskulderna finns i
`fin_lease_liab_crwv` och `op_lease_liab_crwv`.

## Nebius (6-K, utländsk emittent)

Nebius lämnar 20-F (XBRL bara för helår) och inga 10-Q. Kvartalssiffrorna kommer ur pressmeddelandet om
kvartalsresultatet, bilaga 99.1 till en 6-K. 6-K:or med namn som `nbis-YYYYMMDDx6k.htm` (2026-05-20,
2026-08-12, 2026-11-12) innehåller delårsrapporten (1,2–1,8 MB, ingen XBRL enligt submissions) och läses
inte: dokument över 600 kB hoppas över.

- **Tolkning (deterministisk).** Bara inlämningar i feb, mar, maj, jun, aug, sep, nov och dec prövas. Ett
  dokument är ett pressmeddelande om rubriken i början lyder "Nebius (Group N.V.) reports/announces … quarter
  … financial results". I tabellerna *Consolidated results* och *Selected consolidated cash flow data* läses
  rubriken "Three months ended <månad> <dag> [Six/Nine/Twelve months ended …] <år−1> <år> Change" (med
  "In USD $ millions" före eller efter), och varje rad måste ha exakt ett värdepar plus en förändringskolumn per
  block. Annars används raden inte. Värdena blir `sec.Fact` (3 månader och hittills i år, USD) med 6-K:ns
  datum, och därefter gäller `sec.vintages` oförändrat (Q4 = helår − 9M). Q1 föregående år härleds som
  6M − Q2 ur halvårsrapporten (`sec_financing.derived_first_quarters`).
- **Definitionen och startpunkten.** I pressmeddelandet för Q2 2025 (2025-08-07) är Toloka avkonsoliderad och
  redovisad som avvecklad verksamhet, med omräknade jämförelsetal. Tidigare pressmeddelanden har en annan
  bas: intäkter Q3 2024 43,3 där mot 32,1 omräknat, Q4 2024 37,9 mot 35,2 och Q1 2025 55,3 mot 50,9. Q1 2025
  har dessutom OCF utan uppdelning på kvarvarande verksamhet. Därför läses bara inlämningar från 2025-08-01
  (`nebius_sec.SINCE`). Serierna börjar ändå 2024Q1, eftersom jämförelsetalen i de nyare pressmeddelandena
  ger 2024 på den nya basen (dateras 2025-08-07 till 2026-02-12). De äldre pressmeddelandena (Q3 2024–Q1 2025)
  skulle ge en egen definition med tre kvartal, och den byggs inte.
- **Brottskontroll.** `sec_segment.definition_breaks` körs på de tolkade värdena: en omräkning över 2 % av
  ett tidigare inlämnat värde ger `DefinitionBreakError` om den inte är deklarerad. Inga brott hittades
  2025-08-07 till 2026-11-12.
- **Kontroll mot 20-F (XBRL).** Summan av kvartalen stämmer med 20-F för 2025 (inlämnad 2026-04-30):
  intäkter 529,8 = 529,8, capex 4 066,0 = 4 066,0, OCF kvarvarande verksamhet 401,7 mot 401,9 (Q1 2025 härledd
  som 6M − Q2: −184,3 mot −184,1 i Q1 2026:s jämförelsetal, under toleransen). För 2024: intäkter 91,5 = 91,5
  och capex 807,5 = 807,5 (20-F för 2025, omräknad bas).

## IREN

IREN lämnade 20-F till och med FY2025 och 10-Q/10-K från FY2026 (första 10-Q 2025-11-06). Kvartalen
2024Q3–2025Q2 kommer därför bara från jämförelsetalen i FY2026:s 10-Q (dateras 2025-11-06 till 2026-05-08).
Bara capex och OCF byggs. **Intäkterna byggs inte**: i 10-Q 2026-11-05 flyttades bitcoinbrytningen till
`RevenueNotFromContractWithCustomer`, och `RevenueFromContractWithCustomerExcludingAssessedTax` för samma
kvartal (jul–sep 2025) gick från 240,3 till 7,0 (bara AI-molnet). Totalen (`Revenues`) taggas bara i enstaka
inlämningar, och fram till 2026 var intäkterna mest bitcoinbrytning. En AI-molnserie kräver segmentdata ur
instanserna (eget spår vid behov).

## Kontroll mot bolagens rapporter

Senaste version, MUSD, jämförd med bolagens rapporterade siffror ur minnet. Kvartalen är kalenderkvartal
enligt mappningen ovan.

| Serie | Kvartal | Här | Rapporterat | |
|---|---|---|---|---|
| `rev_orcl` | Q4 FY24–Q2 FY26 (2024Q2–2025Q4) | 14 287 / 13 307 / 14 059 / 14 130 / 15 903 / 14 926 / 16 058 | 14,29 / 13,31 / 14,06 / 14,13 / 15,90 / 14,93 / 16,06 mdr | stämmer |
| `rev_orcl` | FY2024, FY2025 (summa) | 52 961; 57 399 | 52,96; 57,40 mdr | stämmer |
| `capex_orcl` | Q1 FY25–Q2 FY26 | 2 303 / 3 970 / 5 862 / 9 080 / 8 502 / 12 033 | 2,3 / 4,0 / 5,9 / 9,1 / 8,5 / 12,0 mdr; FY2025 21,2 mdr | stämmer |
| `ocf_orcl` | Q1 FY25–Q2 FY26 | 7 427 / 1 304 / 5 933 / 6 157 / 8 140 / 2 066 | 7,4 / 1,3 / 5,9 / 6,2 / 8,1 / 2,1 mdr; FY2025 20,8 mdr | stämmer |
| `rev_crwv` | 2024Q2–2025Q3 | 395 / 584 / 747 / 982 / 1 213 / 1 365 | 0,40 / 0,58 / 0,75 / 0,98 / 1,21 / 1,36 mdr; 2024 1,92 mdr | stämmer |
| `capex_crwv` | 2024 (summa) | 8 702 | 8,7 mdr (S-1) | stämmer |
| `rev_nbis` | 2025Q2, 2025Q3 | 105,1 / 146,1 | 105,1 / 146,1 | stämmer |
| `capex_nbis` | 2025Q2, 2025Q3 | 510,6 / 955,5 | cirka 0,51 / 0,96 mdr | stämmer |

Inga avvikelser hittades. Kvartal från 2026 (bland annat Oracles capex 18 635 / 16 493 / 28 499, CoreWeaves
intäkter 2 078 / 2 575 / 3 661, Nebius intäkter 399,0 / 582,3 / 980,8) och alla IREN-kvartal kunde inte
kontrolleras ur minnet. De är internt konsistenta (YTD-differenser och jämförelsetal går ihop, och för Nebius
stämmer helåren med 20-F), men nivåerna bör stickprovas mot pressmeddelandena när B4 läser dem.

## Andra kandidater (inte byggda)

| Bolag (CIK) | Inlämningar | Bedömning |
|---|---|---|
| Applied Digital (1144879) | 10-Q/10-K, räkenskapsår till 31 maj (Oracle-kalender) | Molntjänsten redovisades som avvecklad verksamhet i 10-K för FY2025, och intäkterna för Q4 FY2025 blir −33,3 (helår på ny bas − 9M på gammal bas, samma fel som i `sec.md` för Motorola). Bolaget är nu hyresvärd för datacenter (bl.a. åt CoreWeave), inte GPU-moln. Capex finns (`PaymentsToAcquirePropertyPlantAndEquipment`) och kan byggas om G5 vill ha datacenterbyggare |
| Nscale plc (2110365) | bara DRS och S-1 (2026) | inga periodiska rapporter ännu; följ när 10-Q eller 20-F kommer |
| Lambda | inget SEC-bolag i `company_tickers.json` | inte noterat |
| Core Scientific (1839341), TeraWulf (1083301), Cipher Digital (1819989), Galaxy Digital (1859392), Bitdeer (1899123), HIVE (1720424) | 10-Q/10-K eller 6-K/40-F | bitcoinbrytare med HPC-värdskap (colocation åt hyresgäster), inte GPU-moln; intäkterna blandar brytning och hyra |
| DigitalOcean (1582961) | 10-Q/10-K | allmänt moln med liten GPU-andel |

## Kända problem

- CoreWeave och Nebius har bara elva kvartal och IREN nio. Kvartalen före första egna inlämning kommer från
  jämförelsetal och har ett `known_from` som ligger upp till ett år efter perioden. Det är konservativt.
- Nebius tolkas ur pressmeddelandets text. En ny layout ger inga rader (inte fel värden), och syns som en
  inaktuell serie i `warehouse.fresh`. Ett omräknat jämförelsetal över 2 % stoppar hämtningen
  (`DefinitionBreakError`) tills det granskats och deklarerats.
- `rev_nbis` omfattar hela koncernen (Avride och TripleTen ingår). Nebius AI-molnsegment redovisas i
  delårsrapporten men tolkas inte här.
- Kassaflödesbaserad capex underskattar utbyggnaden för bolag som finansierar GPU:er via leverantörer eller
  leasing (CoreWeave, IREN). Jämför med `fin_lease_liab_*` och `lease_uncommenced_*`.
- Oracles aktualitetsgräns (119 dagar) bygger på inlämningar 2015–2026. Oracles 10-K kommer i slutet av juni,
  och om det någon gång lämnas efter 30 juni behöver gränsen ses över.
