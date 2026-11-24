# Halvledare och minne (ledet L6, gren G6): AMD, Broadcom, Marvell, Micron, Nvidia och ASML

Spår A2a, steg 2. Byggt och kontrollerat 2026-11-23 mot riktiga inlämningar. Bara data: inga takter,
samband eller prognosvärden är beräknade.

Kod: `src/ai_tracker/series/halvledare.py` (`SPECS`), `src/ai_tracker/sources/sec_instant.py`
(balansposter, nytt), `src/ai_tracker/sources/asml_sec.py` (ASML:s 6-K, nytt). Kvartals-, versions- och
segmentlogiken importeras oförändrad från `sources/sec.py`, `sources/sec_segment.py` och
`series/sec_segments.py` (se `sec.md` och `sec_segment.md`). Tester: `tests/test_halvledare.py`
(syntetiska fixturer, inget nät). Hämtning: `python -m ai_tracker.observations <nycklar>`.

## Serier (alla kvartal, release-daterade, `publish=True`)

| Nyckel | Innehåll | Enhet | Från | Till | Kvartal | Reviderade kvartal |
|---|---|---|---|---|---|---|
| `rev_amd` | AMD, totala intäkter | MUSD | 2009Q2 | 2026Q3 | 70 | 4 |
| `rev_amd_datacenter` | AMD, segment Data Center | MUSD | 2021Q2 | 2026Q3 | 22 | 0 |
| `capex_amd` | AMD, köp av anläggningstillgångar | MUSD | 2009Q3 | 2026Q3 | 69 | 0 |
| `inv_amd` | AMD, varulager | MUSD | 2010Q2 | 2026Q3 | 66 | 2 |
| `rev_avgo` | Broadcom (med Broadcom Ltd och Avago), totala intäkter | MUSD | 2009Q4 | 2026Q2 | 67 | 0 |
| `rev_avgo_semis` | Broadcom, segment Semiconductor solutions | MUSD | 2017Q4 | 2026Q2 | 35 | 4 |
| `rev_mrvl` | Marvell (med Marvell Technology Group), totala intäkter | MUSD | 2008Q2 | 2026Q2 | 73 | 5 |
| `rev_mrvl_datacenter` | Marvell, slutmarknad Data center | MUSD | 2022Q1 | 2026Q2 | 18 | 0 |
| `rev_mu` | Micron, totala intäkter | MUSD | 2009Q4 | 2026Q3 | 68 | 0 |
| `rev_mu_cnbu` | Micron, Compute and Networking BU (avslutad) | MUSD | 2015Q4 | 2025Q2 | 39 | 0 |
| `rev_mu_cmbu` | Micron, Cloud Memory BU | MUSD | 2024Q4 | 2026Q3 | 8 | 0 |
| `capex_mu` | Micron, köp av anläggningstillgångar (brutto) | MUSD | 2009Q4 | 2026Q3 | 68 | 4 |
| `inv_mu` | Micron, varulager | MUSD | 2010Q3 | 2026Q3 | 65 | 1 |
| `capex_nvda` | Nvidia, köp av anläggningstillgångar och immateriella tillgångar | MUSD | 2011Q1 | 2026Q2 | 62 | 1 |
| `inv_nvda` | Nvidia, varulager | MUSD | 2009Q2 | 2026Q2 | 69 | 1 |
| `purchase_oblig_nvda` | Nvidia, åtaganden för lager, leverans och kapacitet | MUSD | 2021Q3 | 2026Q2 | 20 | 0 |
| `asml_net_sales` | ASML, nettoomsättning | MEUR | 2006Q2 | 2026Q3 | 82 | 3 |
| `asml_net_bookings_2006` | ASML, orderingång, definition 2006–2011 (avslutad) | MEUR | 2006Q4 | 2011Q1 | 18 | 0 |
| `asml_net_bookings_ex_euv` | ASML, orderingång exklusive EUV (avslutad) | MEUR | 2011Q3 | 2014Q3 | 13 | 0 |
| `asml_net_bookings` | ASML, orderingång, definition från 2017 (avslutad 2025Q4) | MEUR | 2017Q1 | 2025Q4 | 36 | 0 |

Hämtning 2026-11-23: 20 serier och 993 rader. Inte med: Broadcoms AI-intäkter, som inte är XBRL-taggade
(ingen AI-medlem på någon axel i 10-Q/10-K 2019–2026). De finns bara i pressmeddelanden och samtal och
lämnas till **spår B4**. Capex för Broadcom och Marvell begärdes inte och är inte byggda (taggen
`PaymentsToAcquirePropertyPlantAndEquipment` finns för båda).

## Åtkomst och licens

- SEC EDGAR via `ai_tracker.http` (5 anrop/s per värd, deklarerad User-Agent från `.env`, aldrig i repot):
  companyfacts, submissions, filindex (`index.json`) och XBRL-instanser. Inga värdar nekades. EDGAR:s
  arkiv svarade ibland 404 på `index.json` för inlämningar som finns (Micron 10-Q 2022-12-22), och
  `sec_segment._cached_get` försöker därför igen två gånger efter 404. Några få gamla ASML-inlämningar
  (2005–2014) har inget `index.json` alls, och då läses bara huvuddokumentet.
- Licens, kontrollerad på sec.gov/privacy 2026-11-23: *"Information presented on sec.gov is considered
  public information and may be copied or further distributed by users of the web site without the SEC's
  permission. Please consider appropriate citation to the SEC as the source."* Därför `publish=True`, med
  SEC som källa. ASML:s siffror kommer ur en lagstadgad inlämning (6-K), och bara extraherade siffror
  publiceras, med källhänvisning (samma SEC-text som för TSMC, men med ASML som inlämnare,
  `series/tsmc.py` `sixk_license`; rättat efter granskning R9).
- CIK verifierade mot `entityName`: AMD 2488, Broadcom Inc. 1730168 (föregångare Broadcom Ltd 1649338 och
  Avago Technologies 1441634), Marvell Technology, Inc. 1835632 (föregångare Marvell Technology Group
  1058057), Micron 723125, Nvidia 1045810, ASML Holding 937966.

## known_from

**Regel: `known_from` = inlämningsdatum (`filed`) för 10-Q/10-K eller 6-K.** Pressmeddelandet kommer samma
dag eller tidigare, så regeln är konservativ. Varje inlämning är en version. Jämförelsetal i senare
dokument ger bara en ny rad om värdet ändrats (mer än 0,5 MUSD, eller 1 MEUR för ASML).

Belägg: avstånd från kalenderkvartalets slut till första egna inlämning, 2015–2026 (jämförelsetal i
senare dokument undantagna):

| Bolag | Min | Max | Kommentar |
|---|---|---|---|
| AMD | 26 | 58 | 10-K i början av februari |
| Broadcom | 67 | 84 | 10-K i mitten av december för aug–okt |
| Marvell | 56 | 88 | 10-K i mitten eller slutet av mars för nov–jan |
| Micron | −13 | 28 | sep–nov lämnas in före 31 december |
| Nvidia | 45 | 77 | som i `sec.md` |
| ASML | 14 | 29 | pressmeddelande och 6-K samma dag |

## Räkenskapskalendrar och kalenderkvartal

Kalenderkvartal = kvartalet som innehåller räkenskapskvartalets mittpunkt (`sec.calendar_quarter`, samma
regel som i `sec.md`). Balansposter (lager, åtaganden) får samma etikett som flödena i samma
räkenskapskvartal: en balansdag används bara om den är ett räkenskapskvartals slutdag enligt bolagets
intäktsfakta (`sec_instant.fiscal_quarters`). Andra datum (förvärvsdagar, ingående balanser vid
standardbyten) tas bort.

| Bolag | Räkenskapsår | Mappning | `lag_days` | Aktualitetsgräns |
|---|---|---|---|---|
| AMD | 52/53 veckor, kvartal slutar sista lördagen i mar/jun/sep/dec | kalenderkvartal | 25 | 60 + 92 + 30 = 182 dagar |
| Broadcom | 52/53 veckor till söndagen närmast 31 okt | nov–jan = Q4, feb–apr = Q1, maj–jul = Q2, aug–okt = Q3 | 25 | 85 + 92 + 30 = 207 |
| Marvell | 52/53 veckor till lördagen närmast 31 jan | som Nvidia: aug–okt = Q3, nov–jan = Q4 | 25 | 90 + 92 + 30 = 212 |
| Micron | 52/53 veckor till torsdagen närmast 31 aug | sep–nov = Q4, dec–feb = Q1, mar–maj = Q2, jun–aug = Q3 | **−31** | 30 + 92 + 30 = 152 |
| Nvidia | 52/53 veckor till sista söndagen i jan | aug–okt = Q3 (`sec.md`) | 25 | 77 + 92 + 30 = 199 (`NVDA_MAX_AGE_DAYS`) |
| ASML | kalenderår | kalenderkvartal | 30 | härledd: 30 + 92 + 30 = 152 |

Broadcom, Marvell och Nvidia ligger alltså ungefär en månad **efter** kalenderkvartalet, och Micron ungefär
en månad **före**. Microns kvartal sep–nov lämnas in cirka den 18–22 december, alltså före kalenderkvartalets
slut. Därför `lag_days = −31` (som Oracle i `sec_segment.md`): läckagekontrollen `known_from_after_period_end`
tillåter då värden som är kända upp till 31 dagar före kvartalets slut. Värdet är verkligen känt vid
inlämningen, så det är ingen läckage, men etiketten "Q4" betyder sep–nov. Aktualitetsgränsen är största
observerade avstånd + ett kvartal + 30 dagar (`Spec.max_age_days`, motiverad i `note`).

## Taggar och medlemmar

| Serie | Källa | Taggar eller medlemmar (prioritet) | Kommentar |
|---|---|---|---|
| `rev_amd` | companyfacts | `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueGoodsNet` | `SalesRevenueNet` och `Revenues` används inte: för 2017Q2–Q4 ger de 1 151 / 1 584 / 1 340 i stället för AMD:s rapporterade 1 222 / 1 643 / 1 480 |
| `rev_avgo`, `rev_mrvl`, `rev_mu` | companyfacts | `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet` | föregångarnas CIK ger historiken |
| `capex_amd`, `capex_mu` | companyfacts | `PaymentsToAcquirePropertyPlantAndEquipment` | Micron: brutto, före partnerbidrag (Microns egen "net capex" är lägre) |
| `capex_nvda` | companyfacts + instanser | `PaymentsToAcquireProductiveAssets`, `nvda:PurchasesOfPropertyAndEquipmentAndIntangibleAssets`, `PaymentsToAcquirePropertyPlantAndEquipment` | se nedan |
| `inv_*` | companyfacts | `InventoryNet` (instant) | |
| `purchase_oblig_nvda` | instanser | `PurchaseObligation` utan dimension; därefter `OtherCommitmentsAxis` = `ManufacturingProductionAndLongTermSupplyAndCapacityAgreementCommitmentsMember` (på `PurchaseObligation`, sedan `OtherCommitment`) och `SupplyAndCapacityCommitmentsMember` | se nedan |
| `rev_amd_datacenter` | instanser | segment `DataCenterMember` / `DatacenterMember` | per inlämning korrigerad, se nedan |
| `rev_avgo_semis` | instanser | segment `SemiconductorSolutionsMember` | tvåsegmentsindelningen från FY2019, med jämförelsetal för FY2018 |
| `rev_mrvl_datacenter` | instanser | `ProductOrServiceAxis` = `DataCenterMember` | taggas från 10-K för FY2022. FY2021–FY2022 finns bara som helår, så serien börjar 2022Q1 |
| `rev_mu_cnbu`, `rev_mu_cmbu` | instanser | segment `CNBUMember`, `CMBUMember` | se definitionsbrott |

**Nvidias capex.** Raden heter "Purchases related to property and equipment and intangible assets". Nvidia
använde en egen tagg (`nvda:PurchasesOfPropertyAndEquipmentAndIntangibleAssets`) i alla 10-K för FY2013–FY2023
och i 10-Q för FY2023. companyfacts saknar egna taggar, så kvartalen 2022Q1–Q3 och alla fjärde kvartal
2012–2017 saknades. Den egna taggen läses ur instanserna (från 2012) och läggs som andra prioritet. Där två
taggar har samma period är värdena identiska (13 perioder 2010–2023, t.ex. 9M FY2023 1 324 och FY2023 1 833).
Serien går nu utan lucka från 2011Q1, mot 2018Q1 utan den egna taggen.

**Nvidias åtaganden.** Måttet är "outstanding inventory purchase and long-term supply and capacity
obligations". Fram till FY2026 Q2 (2025-07-27) är det `PurchaseObligation` utan dimension. Från FY2026 Q3
taggas tabellen över åtaganden med dimensioner, och medlemmen för tillverkning, leverans och kapacitet bytte
namn till `SupplyAndCapacityCommitmentsMember` i 10-Q 2026-08-26. Den inlämningen anger 2026-04-26 till
119 000 under båda namnen, så namnbytet ändrade inte värdet. Molnavtal (`CloudServiceAgreementCommitmentsMember`,
26–36 mdr USD) och investeringsåtaganden är andra medlemmar och ingår inte. `PurchaseObligation` för
2020-01-26 (186) och 2021-01-31 (317) är en smalare definition före de långa kapacitetsavtalen, och serien
börjar efter luckan (2021Q3). Ingen automatisk brottskontroll görs för instanter. Övergången 2025Q2 →
2025Q3 (45 774 → 50 300) är rimlig enligt Nvidias egna texter, men det är inte verifierat att definitionen är
exakt densamma. Nivån 2026Q2 (279 000) kunde inte kontrolleras ur minnet.

## AMD: felaktiga segmentmedlemmar i sex 10-Q (läckage- och kvalitetskritiskt)

AMD:s sex 10-Q som lämnades in 2023-05-03 till 2024-10-30 har roterade segmentmedlemmar, både för
innevarande kvartal och för jämförelsetalen: `DataCenterMember` innehåller Gaming, `GamingMember` innehåller
Client och `ClientMember` innehåller Data Center. Exempel för 2024Q1: `ClientMember` 2 337 (AMD:s rapporterade
Data Center), `DataCenterMember` 922 (Gaming). 10-K-instanserna (`DatacenterMember`, t.ex. FY2023 6 496 och
FY2024 12 579) och 10-Q från 2025 är korrekta, och de räknar om samma kvartal med rätt värden. Utan korrigering
upptäckte brottskontrollen två falska brott (2023-08-02 och 2025-05-07). `MEMBER_OVERRIDES` läser därför
`ClientMember` för just de sex inlämningarna. Därefter hittar brottskontrollen inga brott, och alla kvartal
2023Q1–2024Q3 stämmer med AMD:s rapporter.

## Definitionsbrott

Brottskontrollen från `sec_segment` (en omräkning över 2 % av ett tidigare inlämnat värde) körs på alla
segmentrader och misslyckas om de upptäckta brotten skiljer sig från de deklarerade. Inga brott upptäcktes
för `rev_amd_datacenter` (efter korrigeringen), `rev_avgo_semis`, `rev_mrvl_datacenter`, `rev_mu_cnbu` eller
`rev_mu_cmbu`. Marvell bytte slutmarknader i 10-K för FY2026 (2026-03-11, `CommunicationsAndOtherMember`
ersatte fyra marknader), men Data center räknades inte om.

**Micron** ersatte sina fyra affärsenheter (CNBU, MBU, SBU och EBU) med CMBU, CDBU, MCBU och AEBU i 10-K för
FY2025 (2025-10-03). Det är nya medlemmar och därför nya nycklar, utan skarv: `rev_mu_cnbu` slutar med
FY2025 Q3 (mar–maj 2025, kalender 2025Q2) och är `closed`. `rev_mu_cmbu` börjar med FY2025 Q1 (sep–nov
2024), där historiken kommer från jämförelsetalen i FY2026:s 10-Q och därför blev känd cirka ett år senare.
CNBU och CMBU har inte samma innehåll (CMBU = minne till hyperskalare, CNBU omfattade också klient och
nätverk), så de ska inte jämföras rakt av.

## ASML (6-K, utländsk emittent)

ASML lämnar inga 10-Q. 20-F:ns XBRL i companyfacts är bara årlig. Kvartalssiffrorna kommer ur
pressmeddelandet om kvartalsresultatet, som lämnas som bilaga till en 6-K samma dag som det publiceras.

- **Dokument.** Alla 6-K (365 stycken från 2002) gås igenom. Bara inlämningar i januari, februari, april,
  juli och oktober prövas. Bland deras dokument hoppas finansiella rapporter, presentationer, IFRS- och
  stämmodokument över (efter namn), och resten tolkas tills ett pressmeddelande känns igen. Dokumenten
  ändras aldrig, så råkopiorna i `data/raw/asml_sec/` återanvänds.
- **Tolkning (deterministisk).** Från cirka 2011: tabellen med nyckeltal. Kolumnrubrikerna (`Q2 2026 Q3 2026`,
  ibland `FY 2024 FY 2025`, äldre med det senaste kvartalet först) läses direkt före första raden
  `Net sales` / `Total net sales`, och värdena knyts till rubrikerna. Fotnotsmarkeringar (`2`, `(3)`, `*`)
  tas bort, och en rad vars antal värden inte stämmer med antalet kolumner används inte. 2006–2011:
  meningar som "Q3 2009 net sales of EUR 555 million versus Q2 2009 net sales of EUR 277 million" och
  "Q3 2009 net bookings valued at EUR 777 million", där varje siffra har sitt eget kvartal.
- **Täckning.** 80 pressmeddelanden 2005–2026. Tre pressmeddelanden (2011Q3, 2013Q2 och en del av 2011Q2)
  har en layout som inte tolkas. De kvartalen kommer i stället som jämförelsetal ur nästa pressmeddelande, med
  dess senare datum. För tre pressmeddelanden (2016Q1, 2017Q1, 2020Q3) som har en femkolumnstabell i stället
  för nyckeltalen kommer orderingången på samma sätt från nästa kvartal.
- **Revideringar.** Nettoomsättningen 2007Q2–Q4 räknades om något (930/934/955 mot 935/940/973) i
  pressmeddelandena ett år senare. Det ger nya versioner. ASC 606 infördes 2018, och 2017Q4 räknades inte om.
- **Orderingång, definitioner.** Etiketten och fotnoten sparas för varje siffra
  (`Release.figures[...][q] = (värde, definition)`), och serien delas där definitionen ändras:
  - 2006–2011Q1: alla system (`asml_net_bookings_2006`);
  - 2011Q3–2014Q3: "Net bookings, excluding EUV" (`asml_net_bookings_ex_euv`);
  - 2014Q4–2016Q4 **utelämnas**: EUV (NXE:3350B) ingick från 2014Q4, ett krav på leverans inom 12 månader
    gällde från 2015Q2, och därefter ändrades definitionen igen. Två definitioner på nio kvartal ger för korta serier;
  - från 2017Q1: alla systemorder med accepterad skriftlig beställning, inklusive metrologi och inspektion
    (`asml_net_bookings`). Fotnoterna anger två mindre ändringar inom serien: High-NA EUV ingick inte
    2018–2021Q3, och från 2022Q3 ingår inflationsjusteringar. Det är inte separata serier.
- **ASML slutade redovisa orderingång per kvartal efter 2025Q4.** Pressmeddelandena från 2026-04-15 har ingen
  rad för orderingång (bara årlig orderstock i Q4). Alla tre orderserier är därför `closed`.

## Kontroll mot bolagens rapporter

Senaste version, MUSD (ASML MEUR), jämförd med bolagens rapporterade siffror ur minnet. Kvartalen anges som
kalenderkvartal enligt mappningen ovan.

| Serie | Kvartal | Här | Rapporterat | |
|---|---|---|---|---|
| `rev_amd` | 2024Q1–2025Q4 | 5 473 / 5 835 / 6 819 / 7 658 / 7 438 / 7 685 / 9 246 / 10 270 | 5,47 / 5,84 / 6,82 / 7,66 / 7,44 / 7,69 / 9,25 / 10,27 mdr | stämmer |
| `rev_amd_datacenter` | 2024Q1–2025Q3 | 2 337 / 2 834 / 3 549 / 3 859 / 3 674 / 3 240 / 4 341 | 2,34 / 2,83 / 3,55 / 3,86 / 3,67 / 3,24 / 4,34 mdr | stämmer |
| `capex_amd`, `inv_amd` | 2024Q1, 2024Q4 | 142; 5 734 | 142 MUSD; 5,73 mdr | stämmer |
| `rev_avgo` | FY24 Q2–FY25 Q4 (2024Q1–2025Q3) | 12 487 / 13 072 / 14 054 / 14 916 / 15 004 / 15 952 / 18 015 | 12,49 / 13,07 / 14,05 / 14,92 / 15,00 / 15,95 / 18,02 mdr | stämmer |
| `rev_avgo_semis` | FY24 Q2–FY25 Q4 | 7 202 / 7 274 / 8 230 / 8 212 / 8 408 / 9 166 / 11 072 | 7,20 / 7,27 / 8,23 / 8,21 / 8,41 / 9,17 / 11,07 mdr | stämmer |
| `rev_mrvl` | FY25 Q1–FY26 Q3 (2024Q1–2025Q3) | 1 161 / 1 273 / 1 516 / 1 817 / 1 895 / 2 006 / 2 074 | 1,16 / 1,27 / 1,52 / 1,82 / 1,90 / 2,01 / 2,08 mdr | stämmer |
| `rev_mrvl_datacenter` | FY25 Q1–FY26 Q2 | 816 / 881 / 1 101 / 1 366 / 1 441 / 1 490 | 0,82 / 0,88 / 1,10 / 1,37 / 1,44 / 1,49 mdr | stämmer |
| `rev_mu` | FQ2'24–FQ1'26 (2024Q1–2025Q4) | 5 824 / 6 811 / 7 750 / 8 709 / 8 053 / 9 301 / 11 315 / 13 643 | 5,82 / 6,81 / 7,75 / 8,71 / 8,05 / 9,30 / 11,32 / 13,64 mdr | stämmer |
| `rev_mu_cnbu` | FQ1'25–FQ3'25 | 4 395 / 4 564 / 5 069 | 4,4 / 4,6 / 5,1 mdr | stämmer |
| `rev_mu_cmbu` | FQ4'25, FQ1'26 | 4 543 / 5 284 | 4,54 / 5,28 mdr | stämmer |
| `capex_mu`, `inv_mu` | FQ1'25, FQ2'25 | 3 206 / 4 055; 8 705 | 3,21 / 4,06 mdr; 8,71 mdr | stämmer |
| `capex_nvda` | FY25 Q2–FY26 Q3 (2024Q2–2025Q3) | 977 / 813 / 1 077 / 1 227 / 1 895 / 1 636 | 0,98 / 0,81 / 1,08 / 1,23 / 1,90 / 1,64 mdr | stämmer |
| `inv_nvda` | jan 2025 – okt 2025 | 10 080 / 11 333 / 14 962 / 19 784 | 10,08 / 11,33 / 14,96 / 19,78 mdr | stämmer |
| `purchase_oblig_nvda` | okt 2025 | 50 300 | 50,3 mdr | stämmer |
| `asml_net_sales` | 2024Q1–2025Q4 | 5 290 / 6 243 / 7 467 / 9 263 / 7 742 / 7 692 / 7 516 / 9 718 | 5,29 / 6,24 / 7,47 / 9,26 / 7,74 / 7,69 / 7,52 / 9,72 mdr EUR | stämmer |
| `asml_net_bookings` | 2024Q1–2025Q4 | 3 611 / 5 567 / 2 633 / 7 088 / 3 936 / 5 541 / 5 399 / 13 158 | 3,61 / 5,57 / 2,63 / 7,09 / 3,94 / 5,54 / 5,40 / 13,2 mdr EUR | stämmer |

Inga avvikelser hittades. Kvartal från 2026 kunde inte kontrolleras ur minnet (bland annat Microns intäkter
23 860 / 41 456 / 54 229, Broadcoms 29 591 för 2026Q2 och Nvidias åtaganden 95 200 / 119 000 / 279 000). De
är internt konsistenta (YTD-differenser och jämförelsetal går ihop), men nivåerna bör stickprovas mot
pressmeddelandena när B4 läser dem.

## Kända problem

- Första versionen för kvartal som bara finns som jämförelsetal (AMD Data Center 2021, Microns CMBU FY2025
  Q1–Q4, Broadcoms segment FY2018) har ett `known_from` som ligger upp till ett år efter perioden. Det är
  konservativt.
- `sec_instant` mappar balansdagar till räkenskapskvartalets kalenderkvartal (mittpunktsregeln), så att lager
  och intäkter för samma räkenskapskvartal får samma etikett. Spår A1:s RPO-serier (`sources/sec_rpo.py`)
  använder i stället balansdagens eget kalenderkvartal. Det ger samma resultat för bolag med kvartal som slutar
  vid kalenderkvartalets slut, men inte för Nvidia, Broadcom, Marvell eller Micron. Om RPO byggs för något av
  dem bör regeln samordnas.
- Tröskeln för definitionsbrott (2 %) och kontrollen av antal värden i ASML:s tabeller är val. En ny layout i
  ASML:s pressmeddelande ger inga rader (inte fel värden), och syns som en inaktuell serie i `warehouse.fresh`.
