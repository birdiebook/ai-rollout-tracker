# Källa: SEC EDGAR XBRL (companyfacts)

Spår I1, fas 2. Byggt och kontrollerat 2026-11-23 mot riktiga companyfacts. Kod:
`src/ai_tracker/sources/sec.py` (kvartalslogik och versioner) och `src/ai_tracker/series/sec.py`
(katalogposter). Tester: `tests/test_sec.py` (syntetiska fixturer, inget nät). Hämtning:
`python -m ai_tracker.observations <nycklar>`. Här finns ingen trendanalys. Måtten förregistreras
separat i `docs/mattregister.md`.

## Åtkomst och licens

- `data.sec.gov/api/xbrl/companyfacts/CIK##########.json`, ett anrop per bolag via `ai_tracker.http.get`
  (5 anrop/s, deklarerad User-Agent från `.env`, som aldrig hamnar i repot). Råkopior sparas i `data/raw/sec/<datum>/`.
- Licens, kontrollerad på sec.gov/privacy 2026-11-23: *"Information presented on sec.gov is considered
  public information and may be copied or further distributed by users of the web site without the SEC's
  permission. Please consider appropriate citation to the SEC as the source."* Därför `publish=True`,
  med SEC som angiven källa.
- CIK verifierade mot `entityName`: Microsoft 789019, Alphabet 1652044, Google Inc. 1288776 (föregångare,
  ger historiken före 2015), Amazon 1018724, Meta 1326801, Nvidia 1045810.
- companyfacts innehåller bara **standardtaxonomier** (us-gaap, dei, srt). Bolagsspecifika taggar
  (t.ex. `amzn:`, `nvda:`) och alla **dimensioner** (segment, produktaxlar) saknas. Det förklarar flera
  luckor nedan.

## Serier (alla kvartal, MUSD, release-daterade)

| Nyckel | Gren | Innehåll | Från |
|---|---|---|---|
| `capex_msft` | G5 | Additions to property and equipment | 2008Q3 |
| `capex_googl` | G5 | Purchases of property and equipment | 2008Q3 |
| `capex_amzn` | G5 | Purchases of property and equipment (brutto, före intäkter och incitament) | 2017Q3 |
| `capex_meta` | G5 | Purchases of property and equipment, net | 2011Q3 |
| `capex_hyp4` | G5 | summa av de fyra | 2017Q3 |
| `fin_lease_msft/googl/amzn/meta` | G5 | amortering (principal) på finansiell leasing, före ASC 842 capital leases | 2016Q3 / 2024Q1 / 2014Q1 / 2018Q1 |
| `fin_lease_hyp4` | G5 | summa av de fyra | 2024Q1 |
| `ocf_msft/googl/amzn/meta` | G5 | operativt kassaflöde | 2008Q3 / 2008Q3 / 2008Q2 / 2011Q3 |
| `ocf_hyp4` | G5 | summa av de fyra | 2011Q3 |
| `rev_msft/googl/amzn/meta` | G4 | totala intäkter | 2008Q3 / 2008Q2 / 2008Q2 / 2011Q2 |
| `rev_nvda` | G4 | Nvidias totala intäkter | 2008Q2 (kalenderkvartal, se nedan) |

Senaste kvartal i hämtningen 2026-11-23: 2026Q3 för de fyra, 2026Q2 för Nvidia (Nvidias kvartal
aug–okt 2026 fanns ännu inte i companyfacts).

## Taggar per bolag och period

Prioritetslista per serie. Ett kvartal tar första taggen som ensam kan räkna fram det. Bara kvartal som
ingen tagg klarar ensam räknas med taggarna skarvade per faktaperiod (se versionslogiken).

| Mått | Bolag | Taggar (prioritet) | Kommentar |
|---|---|---|---|
| capex | MSFT, GOOGL, META | `PaymentsToAcquirePropertyPlantAndEquipment` | samma tagg hela perioden. GOOGL: Alphabet + Google Inc. |
| capex | AMZN | `PaymentsToAcquireProductiveAssets` | Bara brutto, från 2017Q3. Äldre taggar skarvas **inte**: `PaymentsToAcquirePropertyPlantAndEquipment` (t.o.m. 2017Q1) var netto efter incitament, och `PaymentsForProceedsFromProductiveAssets` (2017Q2–2018Q2) bytte från netto till brutto under samma tagg 2018. 2017Q2 finns inte i någon standardtagg på bruttobasis |
| fin_lease | MSFT | `FinanceLeasePrincipalPayments` | |
| fin_lease | GOOGL | `FinanceLeasePrincipalPayments` | taggas först i 10-K för 2024. Tidigare låg leasing i `RepaymentsOfDebtAndCapitalLeaseObligations` tillsammans med skuld, och den används inte |
| fin_lease | AMZN, META | `FinanceLeasePrincipalPayments`, `RepaymentsOfLongTermCapitalLeaseObligations` | AMZN: identiska i överlappet 2018. META: ingen tagg för 2016–2017, så serien börjar 2018Q1 |
| ocf | alla | `NetCashProvidedByUsedInOperatingActivities`, `...ContinuingOperations` | MSFT använde ContinuingOperations 2013–2016 (identiska i överlappet) |
| rev | alla + NVDA | `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet` | identiska i alla överlapp utom MSFT FY2016–17 (ASC 606, omräknat) |

Inte med: Nvidias capex. Nvidia använde en egen tagg i 10-Q under räkenskapsåret 2023, så kvartalen
2022Q1–Q3 saknas i companyfacts. Det behövs inte för N1.

**Segment** (AWS, Google Cloud, Intelligent Cloud, Nvidia Data Center) finns inte i companyfacts. De kräver
dimensionerna i dokumentets XBRL-instans eller SEC:s Financial Statement and Notes Data Sets
(kvartalsvisa zip med dimensioner). Det blir ett eget spår.

## Kvartal och kalendermappning

- Kassaflöden i 10-Q är ackumulerade för räkenskapsåret. Fakta grupperas på `start`, och
  kvartal k = YTD(k) − YTD(k−1). Det första slutdatumet, om det ligger ett kvartal efter start, är själva
  kvartalet. Q4 = helår (10-K) − 9M. Tremånadersfakta (resultaträkning, Amazons kassaflöde) används
  direkt och går före en differens. `fy`/`fp` används aldrig, eftersom de beskriver dokumentet och inte faktat.
- Tremånadersfakta i 10-K (den oreviderade kvartalsnoten) ignoreras. Amazons 10-K för 2012 taggade
  2012 års kvartal med 2011 års datum, och Q4 ges ändå av helår − 9M.
- **Kalenderkvartal = kvartalet som innehåller räkenskapskvartalets mittpunkt.** Kontrollerat: alla
  räkenskapskvartal för MSFT (räkenskapsår till juni), GOOGL, AMZN och META slutar på kalenderkvartalets
  sista dag, så regeln är där identisk med slutdatumets kalenderkvartal.
  **Nvidia** (52/53 veckor, slut sista söndagen i januari) har kvartal som slutar i slutet av
  apr/jul/okt/jan. Aug–okt räknas som Q3 och nov–jan som Q4. Nvidia ligger alltså ungefär **en månad
  efter** kalenderkvartalet. Mittpunkt valdes i stället för slutdatum: med slutdatum blir aug–okt "Q4",
  två månader fel, och värdet blir känt (nov) före periodens slut (dec). Det bryter
  läckagekontrollen `known_from_after_period_end`.

## Versionslogik (läckagekritisk)

- `known_from` = `filed` för 10-Q/10-K (konservativt: pressmeddelandet kommer samma dag eller tidigare).
- För varje distinkt `filed`-datum d räknas alla kvartal fram med bara fakta som lämnats in ≤ d. En rad
  (kvartal, värde, known_from = d) skrivs när ett kvartals värde är nytt eller ändrat med mer än
  0,5 MUSD. Mindre skillnader är avrundning, t.ex. Google Inc. i tusental och senare i miljoner. Ett
  kvartal får alltså aldrig ett datum före det dokument som behövs för att räkna fram det.
- Upprepningar som jämförelsetal ger ingen ny rad. Omräkningar och `10-Q/A`/`10-K/A` blir nya versioner
  med det senare datumet.
- **Konsekvent bas.** En differens använder den senaste versionen av slutfaktat, och den version av
  föregående YTD som fanns när slutfaktat lämnades in. Därför ändras ett kvartal bara när dess eget
  slutfaktum lämnas in igen. Om slutfaktat räknats om men föregående YTD inte gjort det, behålls den
  tidigare versionen. Annars skulle en omräkning av ett helt år hamna i ett enda kvartal (Meta räknade om
  helårs-OCF för 2014–2015 utan omräknade 9M, troligen ASU 2016-09, och Microsoft räknade om FY2016 med ASC 606).
  Priset är att en omräkning som verkligen bara gäller Q4 missas. Det är den konservativa sidan.
- Taggskarvning görs först per kvartal (en tagg i taget) och bara därefter per faktaperiod. Exempel:
  Nvidias Q4 FY2019 = helår i den nya intäktstaggen − 9M i den gamla.
- Aggregaten (`*_hyp4`): ett kvartal finns först när alla fyra bolag har ett värde. Varje version
  dateras till den senaste av de fyra inlämningarna, och en ny version skrivs när någon komponent ändras.
- Serierna börjar efter sista luckan (`contiguous_tail`), så att datatestet `no_gaps` håller.

## Antal versioner (hämtning 2026-11-23)

1 200 rader och 72 revideringar totalt.

| Serie | Kvartal | Reviderade kvartal | Revideringar |
|---|---|---|---|
| capex_msft / googl / amzn / meta | 73 / 73 / 37 / 61 | 0 / 5 / 0 / 8 | 0 / 5 / 0 / 8 |
| capex_hyp4 | 37 | 8 | 8 |
| fin_lease (alla) och fin_lease_hyp4 | 41 / 11 / 51 / 35, 11 | 0 | 0 |
| ocf_msft / googl / amzn / meta | 73 / 73 / 74 / 61 | 4 / 5 / 8 / 4 | 4 / 5 / 8 / 4 |
| ocf_hyp4 | 61 | 13 | 20 |
| rev_msft / googl / amzn / meta / nvda | 73 / 74 / 74 / 62 / 73 | 3 / 7 / 0 / 0 / 0 | 3 / 7 / 0 / 0 / 0 |

Revideringarna är små för capex (META 2021 och 2023 ±0,3–1,3 %, GOOGL 2015–16 under 1 %). Större
revideringar finns för OCF (ASU 2016-09 vid AMZN och META 2016) och intäkter (Motorola som avvecklad
verksamhet vid GOOGL 2012–13, ASC 606 vid MSFT 2016–17).

## Kontroll mot bolagens rapporter

Capex per kvartal (MUSD, senaste version) jämfördes med bolagens egna kassaflödesrader, så långt de är
kända. Helår: MSFT FY2024 44 477 och FY2025 64 551, GOOGL 2024 52 535 och 2025 91 447, AMZN 2024
82 999 (brutto), META 2024 37 256. Kvartalen 2024Q4–2025Q4 stämmer för alla fyra. Som intern kontroll
ger META capex + fin_lease bolagets egen capex-definition (inklusive finansiell leasing): 2024Q4 14 836,
2025Q3 19 374 och 2025Q4 22 137, i linje med Metas rapporterade siffror. 2026 års kvartal kunde inte
kontrolleras ur minnet, men är internt konsistenta (YTD-differenser och Amazons TTM-kolumn går ihop).

## Kända problem

- **Definitioner skiljer sig mellan bolagen.** Microsofts och Metas egna capex-siffror inkluderar
  finansiell leasing, Amazons egen siffra ("cash capex") är netto efter intäkter och incitament, och
  `capex_amzn` här är brutto. `fin_lease_*` är amorteringar och inte nya leasingavtal. Microsofts
  "finance leases acquired" finns inte i companyfacts. Måttdefinitionen för N1 låses i måttregistret.
- **Helår där summan av kvartal ≠ senaste helårsvärde** (följden av regeln om konsekvent bas): GOOGL capex
  2014–15 (55 och 23 MUSD), META capex 2020 och 2022 (48 och 245 MUSD), MSFT OCF FY2014–15, GOOGL OCF
  2014, META OCF 2014–15 och MSFT intäkter FY2016–17. Kvartalen visar då den ursprungliga basen.
- **Avvecklad verksamhet i 10-K:** om ett 10-K redovisar helåret på en ny bas (utan en del av
  verksamheten) medan 9M ännu är på den gamla, blir första versionen av Q4 en blandning. Det går inte
  att upptäcka ur datat. Sett vid GOOGL 2012Q4 (Motorola), som rättas i den andra versionen. Påverkar
  inte capex 2017–.
- **AMZN capex börjar 2017Q3**, och det begränsar `capex_hyp4` till 37 kvartal. En nettoserie med lång
  historik (2008–) går att bygga (köp − intäkter och incitament, plus de äldre nettotaggarna) om
  måttregistret väljer netto.
- **GOOGL finansiell leasing bara från 2024Q1**, så `fin_lease_hyp4` har bara 11 kvartal.
- Första versionen för kvartal före bolagets första XBRL-inlämning (2009–2012) kommer från jämförelsetal
  i senare dokument, och dess `known_from` är därför senare än den verkliga publiceringen. Det är konservativt.
- Nvidias senaste kvartal kan saknas några dagar efter rapporten tills companyfacts uppdateras.
