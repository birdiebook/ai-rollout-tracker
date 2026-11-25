# Källa: nät, optik och servrar ur SEC XBRL

Spår S1, körning 14. Byggt 2026-11-25 och kontrollerat mot bolagens inlämningar. Kod:
`src/ai_tracker/series/sec_stack_nat.py`. Kvartals-, versions- och segmentlogiken kommer oförändrad från `sources/sec.py`,
`sources/sec_instant.py`, `sources/sec_segment.py` och `sources/sec_custom.py` (se `sec.md`, `sec_segment.md` och
`halvledare.md`). Tester: `tests/test_sec_stack_nat.py` (syntetiska companyfacts- och instansfixturer, inget nät).
Förregistrering: `docs/mattregister.md`, 2026-11-25, S1 (commit `6fab1f5`, före hämtningen av värden), med ett tillägg
efter första bygget samma dag och en rättning efter granskning R17 (commit `56f1efb`, spår X14). Granskning:
`docs/granskning/r17-nat-servrar.md`. Här finns ingen trendanalys.

Syftet är att följa lagren mellan chipen och datacentret: nätverksswitchar (Arista, Cisco), optiska moduler och
komponenter (Coherent, Lumentum) och servermontering (Super Micro, Dell, HPE, Celestica). G6 täckte bara chipen. Alla
serier är katalogserier i G6, inte kärnserier, och de påverkar inte diffusionsindexet eller tillståndsreglerna.

## Åtkomst och licens

- companyfacts (`data.sec.gov/api/xbrl/companyfacts/`) för totala intäkter, lager, Super Micros åtaganden och RPO.
  Segment- och produktrader, Aristas, Ciscos och Lumentums åtaganden och Aristas RPO läses ur varje 10-Q/10-K:s
  XBRL-instans (`www.sec.gov/Archives`, samma nedladdning och rå-cache som `sec_segment`). Instanserna för cirka 340
  inlämningar (filindex och instans, cirka 680 anrop) hämtades en gång, i följd, med 0,3 sekunder mellan inlämningarna
  utöver klientens gräns på 5 anrop per sekund, alltså cirka 3 anrop per sekund. Handkontrollerna hämtade 10
  huvuddokument. Inga 403 eller 429.
- Licens som för övriga SEC-serier (sec.gov/privacy, kontrollerad 2026-11-23): offentlig information som får spridas med
  SEC som källa. `publish=True`, och klassen för kommersiell användning är `ja` (regeln `sec` i `licenses.py`). Ingen
  ny regel behövdes. Siffrorna är taggade XBRL-fakta, ingen text extraheras.
- CIK verifierade mot `entityName` i EDGAR:s submissions: Arista Networks 1596532, Cisco Systems 858877, Coherent Corp.
  820318 (II-VI Incorporated till 2022), Lumentum Holdings 1633978, Super Micro Computer 1375365, Dell Technologies
  1571996, Hewlett Packard Enterprise 1645590, Celestica 1030894.
- **Celestica** lämnar 10-K och 10-Q med XBRL (US GAAP) från 10-K:n för 2024 (2025-03-03). Tidigare lämnade bolaget
  20-F och 6-K enligt IFRS, och de används inte. Serierna börjar därför 2024.
- **Micron:** `capex_mu` (köp av anläggningstillgångar, brutto) finns redan från spår A2a (`series/halvledare.py`): 68
  kvartal 2009Q4–2026Q3 i basen. S1 ändrar den inte.

## Serier (alla kvartal, MUSD, gren G6, release-daterade)

Hämtning 2026-11-25 efter rättningen R17 (spår X14): 42 serier och 1 324 rader (S1:s hämtning hade 1 327). "Rev." är
antalet kvartal med mer än en version. Datatesterna
(`python -m ai_tracker.warehouse`) är gröna på spårets vy (bas och spår), och ingen serie är för gammal.

| Nyckel | Innehåll | Kvartal | Från–till | Rader | Rev. |
|---|---|---|---|---|---|
| `rev_anet` | Arista, totala intäkter | 54 | 2013Q2–2026Q3 | 54 | 0 |
| `inv_anet` | Arista, varulager | 50 | 2014Q2–2026Q3 | 51 | 1 |
| `purchase_oblig_anet` | Arista, inköpsåtaganden | 44 | 2015Q4–2026Q3 | 44 | 0 |
| `deferred_rev_anet` | Arista, kontraktsskulder (kort + lång) | 35 | 2018Q1–2026Q3 | 35 | 0 |
| `rpo_anet` | Arista, RPO (total) | 16 | 2022Q4–2026Q3 | 16 | 0 |
| `rev_csco` | Cisco, totala intäkter | 73 | 2008Q3–2026Q3 | 73 | 0 |
| `inv_csco` | Cisco, varulager | 70 | 2009Q2–2026Q3 | 70 | 0 |
| `rev_csco_networking` | Cisco, produktkategorin Networking | 17 | 2022Q3–2026Q3 | 17 | 0 |
| `rev_csco_infra_platforms` | Cisco, Infrastructure Platforms (avslutad) | 20 | 2016Q3–2021Q2 | 31 | 11 |
| `purchase_oblig_csco` | Cisco, inköpsåtaganden för lager | 23 | 2021Q1–2026Q3 | 23 | 0 |
| `rpo_csco` | Cisco, RPO | 33 | 2018Q3–2026Q3 | 34 | 1 |
| `rev_cohr` | Coherent, totala intäkter | 53 | 2013Q3–2026Q3 | 53 | 0 |
| `inv_cohr` | Coherent, varulager | 66 | 2010Q2–2026Q3 | 66 | 0 |
| `rev_cohr_networking` | Coherent, segmentet Networking (avslutad) | 16 | 2021Q3–2025Q2 | 16 | 0 |
| `rev_cohr_datacom` | Coherent, segmentet Datacenter & Communications | 9 | 2024Q3–2026Q3 | 9 | 0 |
| `rev_lite` | Lumentum, totala intäkter | 49 | 2014Q3–2026Q3 | 49 | 0 |
| `inv_lite` | Lumentum, varulager | 46 | 2015Q2–2026Q3 | 47 | 1 |
| `rev_lite_opcomms` | Lumentum, Optical Communications (avslutad) | 36 | 2014Q3–2023Q2 | 36 | 0 |
| `rev_lite_cloud_networking` | Lumentum, Cloud & Networking (avslutad) | 12 | 2022Q3–2025Q2 | 12 | 0 |
| `rev_lite_components` | Lumentum, Components | 9 | 2024Q3–2026Q3 | 9 | 0 |
| `rev_lite_systems` | Lumentum, Systems | 9 | 2024Q3–2026Q3 | 9 | 0 |
| `purchase_oblig_lite` | Lumentum, inköpsåtaganden | 46 | 2015Q2–2026Q3 | 46 | 0 |
| `rev_smci` | Super Micro, totala intäkter | 65 | 2010Q3–2026Q3 | 71 | 6 |
| `inv_smci` | Super Micro, varulager | 34 | 2018Q2–2026Q3 | 34 | 0 |
| `purchase_oblig_smci` | Super Micro, inköpsåtaganden | 33 | 2018Q3–2026Q3 | 33 | 0 |
| `rpo_smci` | Super Micro, RPO | 33 | 2018Q3–2026Q3 | 33 | 0 |
| `rev_dell` | Dell, totala intäkter (utan VMware) | 22 | 2021Q1–2026Q2 | 22 | 0 |
| `inv_dell` | Dell, varulager | 43 | 2015Q4–2026Q2 | 45 | 2 |
| `rev_dell_isg` | Dell, segmentet ISG (EMC från 2016Q3) | 46 | 2015Q1–2026Q2 | 53 | 7 |
| `rev_dell_servers_networking` | Dell, Servers and networking inom ISG (avslutad) | 43 | 2015Q1–2025Q3 | 50 | 7 |
| `rev_dell_ai_servers` | Dell, AI-optimerade servrar och nät | 2 | 2026Q1–2026Q2 | 2 | 0 |
| `rev_dell_traditional_servers` | Dell, traditionella servrar och nät | 2 | 2026Q1–2026Q2 | 2 | 0 |
| `rpo_dell` | Dell, RPO | 34 | 2018Q1–2026Q2 | 34 | 0 |
| `rev_hpe` | HPE, totala intäkter | 38 | 2017Q1–2026Q2 | 38 | 0 |
| `inv_hpe` | HPE, varulager | 44 | 2015Q3–2026Q2 | 46 | 1 |
| `rev_hpe_server_fy24` | HPE, Server, definition FY2024–FY2025 (avslutad) | 12 | 2022Q4–2025Q3 | 16 | 4 |
| `rev_hpe_server_fy26` | HPE, Server, definition från FY2026 | 3 | 2025Q4–2026Q2 | 3 | 0 |
| `rev_hpe_dc_networking` | HPE, Data Center Networking | 3 | 2025Q4–2026Q2 | 3 | 0 |
| `rpo_hpe` | HPE, RPO | 9 | 2024Q2–2026Q2 | 9 | 0 |
| `rev_cls` | Celestica, totala intäkter | 11 | 2024Q1–2026Q3 | 11 | 0 |
| `inv_cls` | Celestica, varulager | 8 | 2024Q4–2026Q3 | 8 | 0 |
| `rev_cls_ccs` | Celestica, segmentet CCS | 11 | 2024Q1–2026Q3 | 11 | 0 |

Korta serier som växer av sig själva: `rev_dell_ai_servers` och `rev_dell_traditional_servers` har kvartalen 2025Q1–Q2
som jämförelsetal, men 2025Q3–Q4 saknas tills 10-Q för Q3 FY2027 (december 2026) ger nio månader för FY2026. Då går
Q4 FY2026 att räkna som helår − 9M, och serien börjar 2025Q1. Samma sak gäller `rev_hpe_server_fy26` och
`rev_hpe_dc_networking` när 10-K för FY2026 kommer i december 2026.

## Taggar och medlemmar per bolag

Totala intäkter: `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet` (som övriga
`rev_*`). Lumentum taggar mest `RevenueFromContractWithCustomerIncludingAssessedTax`, som läggs först. Taggarna är
identiska i alla överlapp (största relativa skillnad 0,0000), utom `Revenues` mot `SalesRevenueNet` hos Coherent
(3,0 %), Super Micro (3,8 %) och Dell (1,2 %), i perioder som omräkningarna nedan förklarar (tellurium, rättelsen 2019
och ASC 606). Arista och HPE
taggar också `SalesRevenueGoodsNet`, som bara är produkter, och den används inte. Lager: `InventoryNet` hos alla.

| Bolag | Segment- och produktrader | Åtaganden | Övrigt |
|---|---|---|---|
| ANET | inga: ett segment, och bara produkt, tjänst och geografi taggas | `PurchaseCommitmentRemainingMinimumAmountCommitted` utan dimension, från 10-K 2016-02-25 | kontraktsskulder och RPO, se nedan |
| CSCO | produkt: `NetworkingMember` (10-K 2024-09-05: `NetworkingRevenueMember`), `InfrastructurePlatformsMember` | `UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount` med `InventoriesMember`, annars utan dimension, från 2021-05-25 | `RevenueRemainingPerformanceObligation` |
| COHR | segment: `NetworkingSegmentMember`, `DatacenterAndCommunicationsSegmentMember` | inga (bara i 10-K) | – |
| LITE | segment: `OpticalCommunicationsSegmentMember`, `CloudNetworkingSegmentMember`, `ComponentsMember`, `SystemsMember` | `PurchaseCommitmentRemainingMinimumAmountCommitted` utan dimension | RPO bara till 2021, används inte |
| SMCI | inga (raden "Server and storage systems" taggas inte efter 10-K för FY2025) | `PurchaseObligation` utan dimension (companyfacts) | `RevenueRemainingPerformanceObligation` |
| DELL | segment `InfrastructureSolutionsGroupMember` (före 2018-06 `EnterpriseSolutionsGroupMember`); produkt × ISG: `ServersAndNetworkingMember`, `AIOptimizedServersAndNetworkingMember`, `TraditionalServersAndNetworkingMember` | inga (bara tidshinkar, ingen taggad total) | `RevenueRemainingPerformanceObligation` |
| HPE | segmentaxeln: `ServerSegmentMember`, `DataCenterNetworkingMember` | inga (bara tidshinkar från 2025-09) | `RevenueRemainingPerformanceObligation` |
| CLS | segment `CCSSegmentMember` | inga | – |

**Dell, produkt × segment.** Dell taggar produktraderna med två dimensioner (`ProductOrServiceAxis` och
`StatementBusinessSegmentsAxis` = ISG). `sec_segment.to_facts` läser bara en dimension, så `exact_facts` i S1 läser
exakt den angivna mängden, med samma regel i övrigt (samma resultat för en dimension, testat). Ett fakta med en extra
dimension (till exempel geografi) räknas inte.

**Aristas åtaganden.** Meningen "we had non-cancellable purchase commitments of" står i noten från 10-K 2016-02-25.
Tidigare inlämningar använde samma tagg för en annan, liten post (4,5 MUSD i 10-Q 2015-11-06). I 10-Q 2018-11-05 är
den odimensionerade taggen totalen (423,1 MUSD) och medlemmen `PurchaseCommitmentMember` delen till
kontraktstillverkare och leverantörer (370,4). Från 2022 delas totalen i inom och efter 12 månader. Ingen omräkning
över 2 % finns, men det finns heller inga jämförelsetal att pröva. Ordalydelsen ändras (R17-5):

| Inlämning | Mening |
|---|---|
| 10-K 2016-02-25, 10-Q 2016-05-05 | "non-cancelable purchase commitments of $43.9 million / $57.3 million to our contract manufacturers and suppliers" |
| 10-Q 2016-08-05 till 10-Q 2017-11-03 | "non-cancelable purchase commitments of $X million" (odelat belopp) |
| från 10-K 2018-02-20 | "non-cancellable purchase commitments of $195.1 million, of which $147.9 million was to our contract manufacturers and suppliers" |

Från 2018-02-20 är taggen totalen, och delen till kontraktstillverkare och leverantörer var 76 % av den 2017-12-31. Om
beloppen 2015Q4–2017Q3 är totalen eller den delen går inte att avgöra ur texten. Det är alltså inte visat att det är
samma definition före och efter 10-K 2018-02-20, och det står i noten. Serien börjar ändå 2015Q4.

**Aristas kontraktsskulder.** Balansräkningens "Deferred revenue" och "Deferred revenue, non-current". Från 10-K
2019-02-15 är de taggade som `ContractWithCustomerLiabilityCurrent` och `...Noncurrent`. I de tre 10-Q:na under 2018
(2018-05-04, 2018-08-08 och 2018-11-05) är de taggade som `DeferredRevenueCurrent` och `DeferredRevenueNoncurrent`, och
de taggarna har då företräde för samma balansdag (rättning efter R17-1). I 10-Q 2018-11-05 är
`ContractWithCustomerLiabilityCurrent` en annan post: "$10.9 million of our contract liabilities was included in 'Other
current liabilities'". S1 tog den posten som kortfristig del, och 2018Q3 blev 221,9 i stället för 529,9 (318,850 +
211,005). Serien börjar 2018Q1 (rättning efter R17-3): Arista bytte till ASC 606 2018-01-01 med den modifierade
retroaktiva metoden och flyttade 16,5 MUSD till övriga skulder, så balansen 2017-12-31 (515,3) är ASC 605 och
öppningsbalansen 2018-01-01 (498,7) ligger inte vid ett kvartalsslut. `ContractWithCustomerLiability` (utan
uppdelning) används inte: den är inte summan av de två delarna hos Arista.

**Aristas RPO.** Bolagets egen tagg
`RevenueRemainingPerformanceObligationIncludingContractLiabilitiesDeferredRevenueAndOtherPerformanceObligationsAmount`,
från 10-K 2023-02-14: "Total revenue from our deferred revenue, contract liabilities and other performance obligations
that is expected to be recognized in future periods". 10-K 2023-02-14 anger både den (2,2 mdr USD) och den äldre,
smalare RPO-siffran (1,3 mdr USD), så den äldre us-gaap-taggen 2018–2022 är en annan definition och tas inte med.

**Ciscos åtaganden.** Tabellen "inventory purchase commitments with contract manufacturers and suppliers". Den taggas
med `InventoriesMember` från 10-Q 2021-11-23 och utan dimension i 10-Q 2021-05-25 och 10-K 2021-09-09. De äldre taggarna
(`PurchaseCommitmentRemainingMinimumAmountCommitted` 2016–2017, `PurchaseObligation` 2018–2019) och året 2020, då
tabellen inte stod med samma ordalydelse, skarvas inte.

## Brott, omfattning och rättelser

Brottskontrollen (`sec_segment.definition_breaks`, en omräkning över 2 % av ett tidigare inlämnat värde) körs på alla
segment- och produktrader, alla balansserier utom lager och, efter tillägget i registret, på totala intäkter. De
upptäckta brotten måste stämma med de deklarerade, annars stoppar hämtningen.

**Segment och produktrader.** Ett nytt segment eller en ny produktkategori är en ny nyckel, och raderna skarvas aldrig:

- Cisco: Infrastructure Platforms (FY2018–FY2021) → kategorierna FY2022–FY2023 ("Secure, Agile Networks" och "Internet
  for the Future", inte byggda) → Networking (FY2024–, med FY2023 som jämförelse).
- Coherent: Networking (FY2023–FY2025, efter förvärvet av Coherent Inc. 2022-07) → Datacenter & Communications (FY2026–).
- Lumentum: Optical Communications (–FY2023) → Cloud & Networking (FY2024–FY2025) → ett rapporterbart segment med
  raderna Components och Systems (FY2026–).
- Dell: Servers and networking (–FY2026 Q3) → AI-optimerade respektive traditionella servrar och nät (10-K 2026-03-16).
  ESG bytte namn till ISG i 10-Q 2018-06-12 utan omräkning över 2 %. ISG och Servers and networking räknades om med
  0,2–1,6 % per helår och kvartal 2018–2019 (ASC 606) och 2022 (efter VMware), som versioner. För 2021Q4 gav det en
  blandning av baser (R17-2, se "Q4 över ett basbyte" nedan).
- **Dells ISG omfattar EMC** från fusionen 2016-09-07 ("On September 7, 2016, EMC Corporation … became a wholly-owned
  subsidiary of Dell Technologies", 10-Q 2016-12-09). ISG går från 3 779 (2016Q2) till 5 989 (2016Q3, delvis EMC) och
  8 395 (2016Q4). Ett förvärv är inget brott, men nivåskiftet är inte organisk tillväxt, och `rev_dell_isg` är
  jämförbar över tid först från 2017Q1 (38 kvartal till 2026Q2, inte 46). I Servers and networking syns inget skifte
  av samma storlek (3 237, 2 910 och 3 612), men hur mycket av EMC som ingår går inte att skilja ut (R17-4).
- **HPE:s Server delas vid omorganisationen** (tillägg i registret). HPE slog ihop Server, Hybrid Cloud och Financial
  Services till segmentet Cloud & AI från 2025-11-01 och räknade om tidigare perioder i 10-Q 2026-03-10 (Server +1,8 %)
  och 2026-06-02 (+2,0 %, där kontrollen slår till). Serien delas vid 2026-03-10: `rev_hpe_server_fy24` (avslutad) och
  `rev_hpe_server_fy26`. FY2025 10-Q och 10-K räknade om FY2024 med −0,6 till −0,8 %, som versioner.
- Inga brott över 2 % för Ciscos, Coherents, Lumentums eller Celesticas rader.
- **Coherent 10-Q 2026-11-04:** affärsenheter flyttades från Industrial till Datacenter & Communications från FY2027,
  och "Prior period segment information has not been recast, as the changes to our segment composition did not have a
  material impact". Det syns inte i datat. `rev_cohr_datacom` har alltså en liten, okänd skillnad i innehåll från 2026Q3.

**Q4 över ett basbyte** (rättning efter R17-2, registret 2026-11-25). Dells 10-K 2022-03-24 lägger ISG på en ny bas
(FY2021 räknas om från 32 588 till 33 002, +1,3 %), men 9M FY2022 i arkivet är den gamla basen (24 771, 10-Q
2021-12-03). `sec.py` parar helåret med den 9M som fanns när helåret lämnades in, så S1:s första version av 2021Q4 var
34 366 − 24 771 = 9 595, ett värde på ingen bas. På samma bas är det 9 219 (9M 25 147, omräknat i 10-Q 2022-12-05).
Servers and networking hade samma fel (4 797 mot 4 720). Varje omräkning är under 2 %, så brottskontrollen ser inget.
Regeln i segment- och produktraderna (`same_basis` i koden): ett kvartal som räknas som differens, i praktiken Q4 =
helår − 9M, används inte när 10-K:t räknar om tidigare inlämnade värden av raden, 9M är inlämnad före 10-K:t och 9M:s
egen inlämning inte räknade om något. Kvartalet väntar då på ett par på samma bas, och det kommer med nästa 10-K. Om
9M:s inlämning också räknade om, låg den nya basen redan i 10-Q:na. Så är det i de fem andra segmentfallen där ett
10-K som räknar om ger Q4: Dells ISG och Servers and networking 2018Q4 (ASC 606), HPE:s Server 2025Q3 och Ciscos
Infrastructure Platforms 2020Q2 och 2021Q2. De ändras inte. Effekt: `rev_dell_isg` och `rev_dell_servers_networking`
2021Q4 har bara 9 219 och 4 720, kända från 10-K 2023-03-30. Gräns: ett 10-K som inför en andra ändring ovanpå en som
redan finns i 10-Q:na upptäcks inte. Totala intäkter följer `sec.py` utan regeln, och där fann R17 ingen blandad Q4.

**Totala intäkter, omfattningsbrott** (tillägg i registret). När en verksamhet redovisas som avvecklad räknar bolaget om
tidigare år, men versionsregeln i `sec.py` räknar bara om de kvartal som lämnas in igen. Därför läser `rev_<co>` bara
inlämningar från det senaste omfattningsbrottet:

| Bolag | Omfattningsbrott | Effekt | Serien börjar |
|---|---|---|---|
| Dell | 10-Q 2017-06-09 (Dell Services, DSG och ECD avvecklade), 10-K 2022-03-24 (VMware avknoppat 2021-11, −8 % för helår FY2020–FY2021) | före tillägget: kvartal till 2020 med VMware, senare utan | 2021Q1 |
| HPE | 10-Q 2017-06-08 (Enterprise Services, −33 %), 10-Q 2018-06-07 (där kontrollen slår till för mjukvaran, −8,6 %; HPE redovisade ES och mjukvaran som avvecklad verksamhet redan i 10-K 2017-12-15) | före tillägget: 2016 med ES, ner till −58 % mellan versioner | 2017Q1 |
| Coherent | 10-K 2014-08-28 (produktlinjen tellurium, −3,4 % för FY2012) | | 2013Q3 |

För HPE är 2018-06-07 kontrollens datum, inte bolagets (R17 N-1): 10-K 2017-12-15 hade redan både Enterprise Services
och mjukvaran som avvecklad verksamhet. Regeln läser bara från 2018-06-07, så 2017Q3 och 2017Q4 får `known_from` ungefär
ett år senare än nödvändigt. Det är konservativt.

Rättelser som blir versioner: Super Micros 10-K och 10-Q/A 2019-05-17 (efter revisionsutskottets utredning, ±3–4 % för
kvartal 2015–2017), och Coherents 10-Q 2012-02-08 (+2,0 % för ett kvartal 2010, inte förklarad i textblocken; påverkar
inte serien). `inv_dell` och `inv_hpe` prövas inte (som registrerat) och kan ha samma blandning för balanser före
avknoppningarna. Omräkningar av lager som syns i datat men inte förklaras (R17 N-3): `inv_lite` 2018Q2 +13,3 % (153,6
→ 174,1 i 10-K 2019-08-27), `inv_hpe` 2016Q3 −3,0 % (1 774 → 1 720, ES och mjukvaran) och `inv_anet` 2014Q4 −3,1 %
(80,5 → 78,0).

**Brottskontrollen skyddar balanser lite** (R17 N-6). Åtaganden, RPO och kontraktsskulder jämförs bara när samma
balansdag lämnas in igen. En ändrad definition utan jämförelsetal syns inte, som i R17-1 (Aristas 2018-09-30 lämnas in
en gång) och R17-5 (Aristas åtaganden 2016–2017).

**Aristas RPO, fel datum.** 10-Q 2025-05-07, 2025-08-06 och 2025-11-05 taggar balansen med en kontext ett år för tidigt.
Texten i 10-Q 2025-05-07 säger "$3.7 billion as of March 31, 2025", men faktat har kontexten 2024-03-31 (där 10-Q
2024-05-08 redan angav 2,6 mdr). På samma sätt 4,7 mdr (2025-06-30) och 5,3 mdr (2025-09-30). I de tre inlämningarna
dateras faktat om till inlämningens balansdag (`ANET_RPO_REDATED`). Utan rättelsen såg det ut som omräkningar med upp
till +61 %, och 2025 års balanser saknades.

## Kalender och datering

known_from är inlämningsdatumet för 10-Q eller 10-K, och varje inlämning är en version. Kalenderkvartal =
kvartalet som innehåller räkenskapskvartalets mittpunkt (`sec.calendar_quarter`). Balanser får räkenskapskvartalets
kalenderkvartal (`sec_instant.fiscal_quarters`), så att lager, åtaganden, kontraktsskulder och RPO har samma etikett som
flödena i samma räkenskapskvartal. För RPO skiljer det sig från `sec_rpo.py`, som använder balansdagens eget
kalenderkvartal. Det spelar roll för Cisco, Dell och HPE, vars balans den 31 januari här är Q4 (nov–jan), inte Q1.

Avstånd från kalenderkvartalets slut till första egna inlämning, 2015–2026, och aktualitetsgränsen (största + 92 +
30). Bara kvartal där första värdet kom högst 100 dagar efter räkenskapskvartalets slut räknas (registret, rättning
efter R17 N-4). Filtret tar bort jämförelsetal i senare dokument och Super Micros sena 10-K för FY2017 (686 dagar) och
FY2024 (240 dagar). `lag_days` är 25 för alla: ingen inlämning kommer före kalenderkvartalets slut.

| Bolag | Räkenskapsår | Mappning | Min | Max | Gräns |
|---|---|---|---|---|---|
| Arista | kalenderår | kalenderkvartal | 31 | 56 | 178 |
| Cisco | 52/53 veckor till sista lördagen i juli | aug–okt = Q3, nov–jan = Q4, feb–apr = Q1, maj–jul = Q2 | 47 | 71 | 193 |
| Coherent | till 30 juni | kalenderkvartal | 32 | 60 | 182 |
| Lumentum | 52/53 veckor till lördagen närmast 30 juni | kvartal slutar −5 till +3 dagar från kalenderkvartalets slut | 27 | 64 | 186 |
| Super Micro | till 30 juni | kalenderkvartal | 33 | 81 | 203 |
| Dell | 52/53 veckor till fredagen närmast 31 januari | aug–okt = Q3, nov–jan = Q4 | 63 | 90 | 212 |
| HPE | till 31 oktober | aug–okt = Q3, nov–jan = Q4 | 61 | 83 | 205 |
| Celestica | kalenderår | kalenderkvartal | 24 | 58 | 180 |

Cisco, Dell och HPE ligger alltså ungefär en månad efter kalenderkvartalet, som Nvidia. Super Micros största avstånd
(81 dagar, 2019Q3) är från åren med sena inlämningar 2017–2019. Super Micro lämnade inga 10-Q mellan 2017-05 och
2019-05, och 10-K för FY2024 kom 2025-02-25. Därför börjar `inv_smci` 2018Q2 och `purchase_oblig_smci` 2018Q3.

## Kontroll mot inlämningarna

Värden ur serierna (senaste version) mot bolagets eget dokument på www.sec.gov (huvuddokumentet i inlämningen). Alla
stämmer.

| Bolag och kvartal | Inlämning (accession) | Serie och värde | I dokumentet |
|---|---|---|---|
| Cisco 2026Q2 (Q4 FY2026, maj–jul), **Q4 = helår − 9M**, brutet räkenskapsår | 10-K 0000858877-26-000132 (2026-09-02) och 10-Q 0000858877-26-000078 (2026-05-19) | `rev_csco` 17 252 = 63 325 − 46 073 | 10-K: "Years Ended July 25, 2026 ... $ 63,325" och i MD&A "Three Months Ended ... Revenue $ 17,252"; 10-Q: nio månader "Total revenue ... 46,073" |
| Cisco 2026Q3 (Q1 FY2027, aug–okt) | 10-Q 0000858877-26-000185 (2026-11-17) | `rev_csco` 18 517, `rev_csco_networking` 11 132, `purchase_oblig_csco` 21 883, `rpo_csco` 46 169 | "Total revenue 18,517"; "Networking $ 11,132"; "Inventory purchase commitments $ 21,883"; RPO "Total $ 46,169" |
| Dell 2026Q2 (Q2 FY2027, maj–jul), **segment**, brutet räkenskapsår | 10-Q 0001571996-26-000046 (2026-09-08) | `rev_dell_ai_servers` 16 401, `rev_dell_isg` 31 782, `rev_dell` 46 971, `rpo_dell` 132 000 | "AI-optimized servers $ 16,401"; "Total ISG net revenue $ 31,782"; "Total net revenue 46,971"; RPO "approximately $ 132 billion" |
| HPE 2026Q2 (Q3 FY2026, maj–jul), **segment** | 10-Q 0001645590-26-000080 (2026-09-03) | `rev_hpe_server_fy26` 6 766, `rev_hpe_dc_networking` 382, `rev_hpe` 12 213 | "Server $ 6,766"; "Data Center Networking 382"; "Total net revenue 12,213" |
| HPE 2025Q3 (Q4 FY2025, aug–okt), Q4 = helår − 9M | 10-K 0001645590-25-000130 (2025-12-18) | `rev_hpe_server_fy24` 4 437 = 17 639 − 13 202 | "Fiscal 2025 Net revenue $ 17,639" (Server) |
| Arista 2026Q3 | 10-Q 0001596532-26-000254 (2026-11-04) | `rev_anet` 3 657,6, `inv_anet` 3 209,8, `purchase_oblig_anet` 11 400, `deferred_rev_anet` 6 839,5, `rpo_anet` 8 600 | "Total revenue 3,657.6"; "Inventories 3,209.8"; "non-cancellable purchase commitments ... of $ 11.4 billion"; "Deferred revenue 5,102.2" + "Deferred revenue, non-current 1,737.3"; RPO "$ 8.6 billion" |
| Arista 2025Q1 (omdaterad) | 10-Q 0001596532-25-000106 (2025-05-07) | `rpo_anet` 3 700 | "amounts to $3.7 billion as of March 31, 2025" (textblocket i inlämningen) |
| Coherent 2026Q3 (Q1 FY2027) | 10-Q 0000820318-26-000023 (2026-11-04) | `rev_cohr_datacom` 1 951,7, `rev_cohr` 2 370,3 | "Datacenter & Communications $ 1,951,725" och "Revenues $ 2,370,324" (tusental) |
| Lumentum 2026Q3 (Q1 FY2027, jun–sep) | 10-Q 0001628280-26-069615 (2026-11-03) | `rev_lite` 1 262,6, `rev_lite_components` 754,2, `inv_lite` 807,7, `purchase_oblig_lite` 2 948,9 | "Net revenue $ 1,262.6"; "Components 754.2"; "Inventories 807.7"; "purchase obligations of $ 2,948.9 million" |
| Super Micro 2026Q3 (Q1 FY2027) | 10-Q 0001375365-26-000027 (2026-11-06) | `rev_smci` 19 945,8, `purchase_oblig_smci` 33 300, `rpo_smci` 5 665,7 | "Net sales ... $ 19,945,832" (tusental); "remaining non-cancelable commitments were $ 33.3 billion"; RPO "approximately $ 5,665.7 million" |
| Celestica 2026Q3 | 10-Q 0001030894-26-000050 (2026-10-26) | `rev_cls_ccs` 4 872,3, `rev_cls` 5 829,7 | CCS "$ 4,872.3"; "Revenue ... $ 5,829.7" |

## Inte med

- Arista har ingen rad för moln eller AI i XBRL. Bolagets andel från stora molnkunder står bara i texten.
- Ciscos kategorier FY2022–FY2023 ("Secure, Agile Networks", "Internet for the Future") och de äldre FY2016–FY2017
  (switchar, routing, datacenter) är inte byggda. De kan läggas till som avslutade nycklar.
- Coherents Photonic Solutions (II-VI, FY2020–FY2022) och HPE:s Compute och HPC & AI (FY2020–FY2023) är inte byggda.
- Celesticas delsegment inom CCS bytte namn och innehåll i 10-Q 2026-10-26 (Communications och Enterprise blev
  Networking och Compute & Storage), och de nya har bara två kvartal.
- Inköpsåtaganden för Coherent (bara i 10-K), Dell och HPE (bara tidshinkar) och Celestica (ingen tagg). Dells och HPE:s
  hinkar går att summera, men taggarna för hinkarna byter namn, och det kräver en egen regel.
- RPO för Lumentum (taggas bara till 2021), Micron (bara i 10-K) och HPE:s kvartal 2022Q3, 2023Q3 och 2024Q1, som saknar
  odimensionerad total. Därför börjar `rpo_hpe` 2024Q2.
- Capex för andra bolag än Micron begärdes inte.

## Förbehåll

- **Inget av detta är AI-intäkter.** Bolagen säljer också till företag, telekom, industri och konsumenter. Segment- och
  produktintäkter är inte AI-intäkter: Ciscos Networking innehåller företagsnät och UCS-servrar, Dells och HPE:s
  serverrader innehåller traditionella servrar, och Coherents och Lumentums segment innehåller telekom och industri.
  Dells `rev_dell_ai_servers` är den enda raden som bolaget själv kallar AI, och den har bara två kvartal.
- **Förvärv är inga brott.** EMC ingår i Dells ISG från 2016-09-07, Juniper i HPE:s nät och RPO från 2025-07, Oclaro i
  Lumentum från 2018-12, Coherent Inc. i II-VI från 2022-07 och Splunk i Cisco från 2024-03. Nivåskiften vid förvärven
  är inte organisk tillväxt. EMC är det största i S1:s data: ISG mer än fördubblas från 2016Q2 till 2016Q4.
- **Åtaganden mäter olika saker.** Arista och Super Micro anger icke uppsägningsbara åtaganden, Cisco åtaganden för lager
  mot kontraktstillverkare och leverantörer, och Lumentum bindande åtaganden för lager och annat. Super Micros siffra
  innehåller närstående (Ablecom och Compuware, cirka 0,2 mdr USD i 2026Q3). Jämför takter, inte nivåer mellan bolagen.
- **RPO och kontraktsskulder** är inte orderstock i vid mening. Cisco och Dell har stora tjänstedelar (support och
  prenumerationer). Aristas RPO omfattar förutbetalda intäkter och icke uppsägningsbar orderstock.
- **HPE:s RPO är förutbetalda intäkter** enligt bolagets egen text (R17-6): "the aggregate amount of remaining
  performance obligations, or deferred revenue" (10-K 2022-12-08 till 10-Q 2024-03-05) och "the aggregate amount of
  deferred revenue" (från 10-Q 2024-06-05). Dells och Ciscos RPO är förutbetalda intäkter plus ofakturerade belopp.
  Jämför inte nivån i `rpo_hpe` med `rpo_dell` eller `rpo_csco`. Juniper ingår från förvärvet 2025-07-02, cirka 2,5 mdr
  USD 2025-10-31 ("approximately $2.5 billion was attributable to the Merger", 10-K 2025-12-18).
- **Avrundning.** Arista och Super Micro anger åtaganden och RPO i 0,1 miljarder USD i texten och taggar dem så. Coherent
  och Super Micro taggar i tusental, de övriga i miljoner med en decimal eller hela miljoner.
- Första versionen av kvartal som bara finns som jämförelsetal (Ciscos Networking FY2023, Coherents och Lumentums nya
  segment för FY2025, Celesticas 2024) har ett `known_from` upp till ett år efter perioden. Det är konservativt.

## Vad som setts före registret

Före registerposten (commit `6fab1f5`) sågs bara täckning: antal fakta, slutdatum, inlämningsdatum och formulär per
tagg i companyfacts, största relativa skillnaden mellan taggar i överlapp, och vilka medlemmar och taggar som finns i
vilka instanser. För att läsa definitionerna lästes textblock i ett urval inlämningar, och där syntes enskilda belopp
(Aristas åtaganden och RPO i sju inlämningar, Super Micros, Lumentums och Ciscos åtaganden i den senaste 10-Q:n, och
HPE:s intäkter per kategori i 10-Q 2026-09-03). Inga kvartalsserier eller takter räknades före posten. Tillägget efter
första bygget bygger på brottskontrollens utfall (vilka inlämningar som räknar om, och hur mycket) och bolagens text.

## Rättning efter R17 (spår X14)

Rättat 2026-11-25 i `auto14k/x14-nat-servrar`, med registerposten "S1: Aristas kontraktsskulder, Q4 över ett basbyte och
aktualitetsgränsen (rättning efter R17)" committad före koden och ombygget. Alla 42 serier byggdes om ur SEC (en
hämtning i följd: companyfacts och inlämningslistor för åtta bolag, instanserna ur den delade rå-cachen). Inga 403 eller
429. Ombygget är identiskt med S1:s tabell utom fyra rader:

| Serie | Kvartal | `known_from` | S1 | X14 | Fynd |
|---|---|---|---|---|---|
| `deferred_rev_anet` | 2017Q4 | 2018-05-04 | 515,262 | utgår | R17-3 |
| `deferred_rev_anet` | 2018Q3 | 2018-11-05 | 221,905 | 529,855 | R17-1 |
| `rev_dell_isg` | 2021Q4 | 2022-03-24 | 9 595 | utgår (9 219 från 2023-03-30 står kvar) | R17-2 |
| `rev_dell_servers_networking` | 2021Q4 | 2022-03-24 | 4 797 | utgår (4 720 från 2023-03-30 står kvar) | R17-2 |

Noterna för `rev_dell_isg` och `rev_dell_servers_networking` (EMC), `purchase_oblig_anet` (ordalydelsen 2018-02-20),
`deferred_rev_anet` och `rpo_hpe` (förutbetalda intäkter) är ändrade. Datatesterna (`python -m ai_tracker.warehouse`) är
gröna på spårets vy.

**Vad som setts före registerposten:** R17:s rapport med dess värden. Ur den delade rå-cachen med S1:s kod och utan nät:
Aristas taggade kontraktsskulder och förutbetalda intäkter per inlämning 2017–2019, och en sökning efter Q4-rader ur
ett 10-K som räknar om tidigare värden, med helår, 9M och Q4 före och efter, och vilka 10-Q som räknade om under året.
Ur S1:s tabell: Dells ISG och Servers and networking 2016Q1–2017Q2 och Aristas åtaganden och kontraktsskulder
2015Q4–2018Q4. Textblock i cachade instanser för Aristas åtaganden 2016–2018, HPE:s RPO 2022–2026 och EMC-fusionen. Den
sökningen ledde till det tredje villkoret i regeln för Q4 (att 9M:s inlämning inte räknade om). Granskningens förslag
utan det villkoret hade också hållit tillbaka fem Q4-rader på en konsekvent bas. Inga takter räknades.
