# Källa: kraft, kylning, elnät och datacenterbolag ur SEC XBRL

Spår S2, körning 14. Byggt 2026-11-25 och kontrollerat mot bolagens inlämningar. Kod:
`src/ai_tracker/series/sec_stack_kraft.py`. Kvartalslogik och versioner: `sources/sec.py`, `sources/sec_rpo.py` och
`sources/sec_segment.py`. Tester: `tests/test_sec_stack_kraft.py` (syntetiska fixturer, inget nät). Taggvalen är
förregistrerade i `docs/mattregister.md` (2026-11-25, S2) i commit 009602a, före hämtningen av värden. Tilläggen efter
första bygget står i registret samma dag ("S2: tillägg efter första bygget"). Här finns ingen trendanalys.

Syftet är att följa det fysiska lagret i AI-flödet: el, kylning och elnät. Orderstocken hos utrustningstillverkarna
ligger före utbyggnaden. Datacenterbolagen (Equinix och Digital Realty) är lagret mellan utrustningen och molnbolagen.
Serierna är katalogserier, inte kärnserier. De ingår inte i diffusionsindexet.

## Vad som setts före registerposten

Entitetsnamn, räkenskapsår och inlämningslistor. Vilka kandidattaggar som finns och vilka perioder och
inlämningsdatum de täcker. Per inlämning: vilka segmentmedlemmar och markörer som finns på intäkterna, och hur RPO är
taggat (dimension, hinkarnas startdatum och längd). Antal överlappande perioder och största relativa skillnad mellan
kandidattaggar och mellan markörer. Radetiketterna i kassaflödesanalysen. Texten kring RPO-fakta hos Vertiv och Eaton,
för att se vad som taggats. Där syntes enstaka orderstocksbelopp (Vertiv 15,0 och 7,2 mdr USD, Eaton 5,4, 12,9, 15,2 och
26,2 mdr USD). Inga kvartalsserier eller takter räknades före posten.

## Åtkomst och licens

- companyfacts (`data.sec.gov/api/xbrl/companyfacts/`) för totala intäkter och capex. Segment, RPO och Digital Realtys
  flöden läses ur varje inlämnings XBRL-instans (`www.sec.gov/Archives`, samma nedladdning och rå-cache som
  `sec_segment`). Hämtningen gick sekventiellt, med 0,3 s paus per dokument och högst 2,5 anrop per sekund.
- Licens som för övriga SEC-serier (sec.gov/privacy, kontrollerad 2026-11-23): offentlig information, får spridas med
  SEC som källa. Därför `publish=True` och klassen `ja` (regeln `sec` i `ai_tracker.licenses`). Ingen ny licensregel
  behövdes. Inga värden extraheras ur text.

| Bolag | CIK | Räkenskapsår | XBRL från |
|---|---|---|---|
| Vertiv (VRT) | 1674101 | kalenderår | f.d. GS Acquisition Holdings Corp (SPAC). Som Vertiv från 10-K 2020-03-12. Kvartalen 2019 kommer från jämförelsetalen i 10-Q 2020 |
| GE Vernova (GEV) | 1996810 | kalenderår | första 10-Q 2024-04-30. Form 10 (10-12B 2024-02-15, 10-12B/A 2024-03-05) har ingen XBRL: `isXBRL` = 0 och ingen instans i mappen. Historiken börjar med jämförelsetalen i 10-Q 2024 (2023Q1) |
| Eaton (ETN) | 1551182, 31277 | kalenderår | Eaton Corporation plc (Irland, lämnar 10-Q och 10-K) från 10-K 2013-02-28. Föregångaren Eaton Corporation ger 2008–2012 |
| Quanta Services (PWR) | 1050915 | kalenderår | 2009 |
| Equinix (EQIX) | 1101239 | kalenderår | 2010 |
| Digital Realty (DLR) | 1297996 | kalenderår | 2010. companyfacts saknar 10-Q 2026-07-31 och 2026-10-30 (kontrollerat 2026-11-25), så flödena läses ur instanserna |

Alla räkenskapskvartal slutar på kalenderkvartalets sista dag (kontrollerat i bygget för alla flöden). Mittpunktsregeln
ger därför kalenderkvartalet för slutdatumet.

## Serier (alla kvartal, MUSD, release-daterade)

Hämtning 2026-11-25: 27 serier och 986 rader. "Rev." är antalet kvartal med mer än en version.

| Nyckel | Gren | Innehåll | Kvartal | Från–till | Rader | Rev. |
|---|---|---|---|---|---|---|
| `rev_vrt` | G7 | intäkter | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `capex_vrt` | G7 | capex | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `rev_vrt_americas` | G7 | segment Americas (inkl. försäljning till andra segment) | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `rev_vrt_apac` | G7 | segment Asia Pacific (inkl. försäljning till andra segment) | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `rev_vrt_emea` | G7 | segment Europe, Middle East & Africa (inkl. försäljning till andra segment) | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `rev_gev` | G7 | intäkter | 15 | 2023Q1–2026Q3 | 15 | 0 |
| `capex_gev` | G7 | capex | 15 | 2023Q1–2026Q3 | 15 | 0 |
| `rev_gev_power` | G7 | segment Power | 15 | 2023Q1–2026Q3 | 18 | 3 |
| `rev_gev_wind` | G7 | segment Wind | 15 | 2023Q1–2026Q3 | 15 | 0 |
| `rev_gev_electrification_fy24` | G7 | segment Electrification, definition före 2026 (avslutad) | 12 | 2023Q1–2025Q4 | 12 | 0 |
| `rev_gev_electrification_fy26` | G7 | segment Electrification, definition från 2026 | 3 | 2026Q1–2026Q3 | 3 | 0 |
| `rpo_gev` | G7 | RPO totalt | 11 | 2024Q1–2026Q3 | 11 | 0 |
| `rpo_gev_equipment` | G7 | RPO för utrustning | 11 | 2024Q1–2026Q3 | 11 | 0 |
| `rpo_gev_services` | G7 | RPO för tjänster | 11 | 2024Q1–2026Q3 | 11 | 0 |
| `rev_etn` | G7 | intäkter | 74 | 2008Q2–2026Q3 | 74 | 0 |
| `capex_etn` | G7 | capex | 73 | 2008Q3–2026Q3 | 73 | 0 |
| `rev_etn_electrical_americas` | G7 | segment Electrical Americas | 27 | 2020Q1–2026Q3 | 27 | 0 |
| `rev_etn_electrical_global` | G7 | segment Electrical Global | 27 | 2020Q1–2026Q3 | 27 | 0 |
| `rpo_etn` | G7 | orderstock (fasta order, taggad som RPO) | 25 | 2020Q3–2026Q3 | 25 | 0 |
| `rev_pwr` | G7 | intäkter | 74 | 2008Q2–2026Q3 | 82 | 8 |
| `capex_pwr` | G7 | capex | 74 | 2008Q2–2026Q3 | 83 | 9 |
| `rpo_pwr` | G7 | RPO totalt | 35 | 2018Q1–2026Q3 | 35 | 0 |
| `rev_eqix` | G4 | intäkter | 70 | 2009Q2–2026Q3 | 77 | 7 |
| `rpo_eqix` | G4 | RPO totalt | 35 | 2018Q1–2026Q3 | 35 | 0 |
| `capex_eqix` | G5 | capex (bygge och utrustning, utan fastighetsköp) | 51 | 2014Q1–2026Q3 | 51 | 0 |
| `rev_dlr` | G4 | intäkter | 66 | 2010Q2–2026Q3 | 66 | 0 |
| `capex_dlr` | G5 | capex (förbättring av fastigheter, utan förvärv) | 65 | 2010Q3–2026Q3 | 65 | 0 |

Datatesterna (`python -m ai_tracker.warehouse`) är gröna på spårets vy, aktualiteten inräknad.

**Grenar.** Utrustningstillverkarna och elnätsbyggaren ligger i G7 med alla mått, också capex och intäkter, eftersom
de beskriver den fysiska flaskhalsen. Equinix och Digital Realty följer katalogens mönster för CoreWeave: intäkter och
RPO i G4, capex i G5.

## Taggar per bolag

Raderna kontrollerades i den renderade kassaflödesanalysen och resultaträkningen. Etiketten är bolagets egen.

| Bolag | `rev_<co>` | `capex_<co>` | Kommentar |
|---|---|---|---|
| VRT | `RevenueFromContractWithCustomerExcludingAssessedTax` ("Net sales") | `PaymentsToAcquirePropertyPlantAndEquipment` ("Capital expenditures") | `Revenues` 2016–2019 avviker i alla sju överlappande perioder (SPAC-bolagets poster) och används inte. "Investments in capitalized software" ingår inte i capex |
| GEV | `RevenueFromContractWithCustomerExcludingAssessedTax` | `PaymentsToAcquireProductiveAssets` ("Additions to property, plant, and equipment and internal-use software") | |
| ETN | `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet` | `PaymentsToAcquirePropertyPlantAndEquipment` ("Capital expenditures for property, plant and equipment") | båda taggarna identiska i 7 överlappande perioder, föregångarens `SalesRevenueNet` identisk i 7. `Revenues` avviker och används inte |
| PWR | `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueServicesNet` | `PaymentsToAcquirePropertyPlantAndEquipment` ("Capital expenditures") | identiska i 7 överlappande perioder |
| EQIX | `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues` | `PaymentsToAcquireOtherPropertyPlantAndEquipment` ("Purchases of other property, plant and equipment") | identiska i 7 perioder. "Real estate acquisitions" (`PaymentsToAcquireRealEstate`) ingår inte |
| DLR | `Revenues` ("Total operating revenues") ur instanserna | `PaymentsToDevelopRealEstateAssets` ("Improvements to investments in real estate") ur instanserna | "Cash paid for business combination / asset acquisitions" och "Investments in and advances to unconsolidated entities" ingår inte |

**Capex för datacenterbolagen.** Måttet är utbyggnad och förbättring av egen kapacitet: raden för bygge och
utrustning. Köp av befintliga fastigheter, mark och bolag ingår inte. Equinix egen capex i segmentnoten
(`PaymentsToAcquireProductiveAssets`, "Capital expenditures" per region) är lika med raden för "other property, plant and
equipment" i 42 av 52 överlappande perioder och innehåller inte fastighetsköpen. Den taggas inte längre i 10-Q från 2026Q2 och används därför inte. De
två datacenterbolagen är jämförbara med varandra, men inte helt med de stora molnbolagen, vars capex också innehåller
köpt mark och köpta byggnader.

**Equinix 2012–2013.** Raden taggades då `PaymentsToAcquirePropertyPlantAndEquipment`. Den taggen avviker från
`PaymentsToAcquireOtherPropertyPlantAndEquipment` i en av 19 överlappande perioder och skarvas inte. `capex_eqix` börjar
därför 2014Q1.

**Digital Realty ur instanserna.** Fakta utan dimension gäller Digital Realty Trust, Inc. Partnerskapet (Digital Realty
Trust, L.P.) har samma siffror med `LegalEntityAxis`. Instansserien är lika med companyfacts-serien i alla versioner till
och med 2026-05-01, utom tre rader i `rev_dlr` (2009Q2 och första versionen av 2010Q2). Orsaken är att
`sec_segment.instance_name` väljer filen `defnref.xml` i fyra inlämningar 2010–2011 (10-Q/A 2010-08-12, 10-Q
2010-11-09, 10-K/A 2011-03-25 och 10-Q 2011-05-09). Där hittas inga fakta, och kvartalen får sin första version senare
(2011-08-05). Det är konservativt. `capex_dlr` är lika i alla versioner.

## Segmentintäkter

En fakta räknas bara när kontextens dimensioner är exakt de angivna. En produktaxel, en tidsaxel eller en annan markör
utesluter den.

| Serie | Medlem och markör | Vad siffran är |
|---|---|---|
| `rev_gev_*` | `PowerSegmentMember`, `WindSegmentMember`, `ElectrificationSegmentMember` med `ConsolidationItemsAxis` = `OperatingSegmentsExcludingIntersegmentEliminationMember` | "Segment revenues" i segmentnoten, före eliminering av interna intäkter (till exempel Power 2026Q3: 6 067 varav 8 interna). Markören finns i alla elva inlämningar. `OperatingSegmentsMember` finns bara i 10-Q 2024 och avviker upp till 5 % |
| `rev_etn_electrical_*` | `ElectricalAmericasSegmentMember`, `ElectricalGlobalSegmentMember`, utan markör och annars med `OperatingSegmentsMember` | "Net sales" per segment. De två varianterna är identiska i 156 par. Bara inlämningar från 2020, eftersom samma medlemsnamn användes för ett äldre segment i 10-K för 2012. Segmenten finns från 10-Q 2020-04-30, och 2020 års 10-Q har inga kvartalsvisa jämförelsetal för 2019, så serierna börjar 2020Q1 |
| `rev_vrt_*` | `AmericasSegmentMember`, `AsiaPacificSegmentMember`, `EMEASegmentMember` med `ConsolidationItemsAxis` = `OperatingSegmentsMember` | raden "Sales" i segmentnoten, inklusive försäljning till andra segment. Raden "Net Sales" (extern försäljning, medlemmen utan markör) avviker upp till 35 % och saknas i 10-K 2024-02-23. Summan av de tre serierna är större än `rev_vrt` (2026Q3: 4 830,8 mot 4 312,8) |

Vertivs egen huvudsiffra per segment är troligen "Net Sales" (extern), eftersom den summerar till bolagets intäkter.
Valet av "Sales" gjordes på täckningen, enligt registrets regel. Se "Möjliga tillägg".

## RPO och orderstock

Balanser vid kvartalets slut, som `sec_rpo`. Period = kalenderkvartalet för balansdagen. Bara totalen räknas. En
uppdelning i tid (inom 12 månader) byggs inte, eftersom tidshinkarna är inkonsekvent taggade: hos PWR 2021 och 2023
har andelen och hinkens längd olika startdatum, och hos ETN 2022–2023 finns inaktuella startdatum och en odimensionerad
andel.

| Serie | Kontext | Anmärkning |
|---|---|---|
| `rpo_gev` | `RevenueRemainingPerformanceObligation` utan dimension | 10-Q: "the aggregate amount of the contracted revenues allocated to our unsatisfied (or partially unsatisfied) performance obligations" |
| `rpo_gev_equipment`, `rpo_gev_services` | samma med `ProductOrServiceAxis` = `ProductMember` / `ServiceMember` | "Equipment-related RPO" och "Services-related RPO". Summan är totalen. Inget RPO per segment taggas |
| `rpo_pwr` | utan dimension | Quantas RPO, inte bolagets "Backlog", som också räknar med uppskattade avrop under ramavtal (MSA). Segmenttabellen för RPO och backlog i 10-Q taggas inte med segmentaxeln |
| `rpo_etn` | utan dimension 2020Q3–2024Q1, därefter med bara startdatumaxeln (en hink) | Eatons "total backlog": "only the amount of orders to which customers are firmly committed are included". Samma mening i 10-Q 2020-11-03, 2023-10-31, 2024-08-01 och 2026-11-03. `sec_rpo.totals` läser en ensam hink som totalen |
| `rpo_eqix` | utan dimension | "revenues, including deferred installation revenues, ... expected to be recognized in future periods related to unsatisfied performance obligations" |

**Vertiv: BLOCKED i XBRL.** Vertiv taggar inget RPO. De fakta som taggas `RevenueRemainingPerformanceObligation` med
startdatumaxeln är tidsfördelningen av långfristiga förutbetalda intäkter (10-Q 2026-10-28: "The Company expects to
recognize noncurrent deferred revenue of $ 115.0 , $ 6.0 and $ 4.2 in the next 13 to 24 months, the next 25 to 36
months, and thereafter"). De används inte. Vertivs orderstock ("estimated combined order backlog", 10-K Item 1) och
orderingång står bara i texten och i pressmeddelandena. Spår S3 extraherar dem.

Inte heller GE Vernovas orderingång ("orders") eller Quantas backlog taggas. Det som taggas är RPO.

## Omräkningar och definitionsbrott

- Omräkningar av totala intäkter och capex är versioner med regeln om konsekvent bas i `sec.py`, utan ny nyckel.
- Segment och balanser: en inlämning som räknar om tidigare värden med mer än 2 % (`sec_segment.definition_breaks`)
  deklareras, och varje definition får en egen nyckel. En odeklarerad omräkning stoppar hämtningen
  (`DefinitionBreakError`).
- **GE Vernova Electrification, deklarerat 2026-04-22.** "Effective January 1, 2026, the Company realigned the reporting
  of certain of its business units ... a component of our former Electrification Software business unit was realigned
  into Gas Power" (10-Q 2026-04-22). Kvartalen 2025 räknades om med −1,4 till −2,1 %. `rev_gev_electrification_fy24` är
  definitionen till och med 10-K 2026-01-29 (avslutad), `rev_gev_electrification_fy26` definitionen från 2026. Den nya
  serien har bara 2026Q1–2026Q3, eftersom 2025Q4 på den nya basen kräver helåret 2025 ur 10-K för 2026. Power räknades
  om med +0,5 till +0,6 %, under gränsen. Det ger nya versioner av `rev_gev_power` 2025Q1–Q3, daterade till 10-Q 2026.
- Eatons omorganisation 2026 (Vehicle och eMobility blev Mobility) ändrade inte de elektriska segmenten.
- **Feldaterad fakta (Equinix).** 10-Q 2025-04-30 taggar intäkten för Q1 2025 (2 225) med datumen för Q1 2023. En
  fakta i en 10-Q vars period slutar mer än 550 dagar före inlämningen används inte (registrets tillägg). Det gäller
  bara denna fakta bland S2:s serier. `rev_eqix` 2023Q1 är 1 998,2 (10-Q 2023-05-05).
- **Eatons skalbolag.** Eaton Corporation plc lämnade en 10-Q 2012-11-14 före sammanslagningen med Cooper, med intäkten
  0 för Q3 2012. Plc-bolagets fakta före 2013-01-01 används inte. Perioden kommer från Eaton Corporation.
- **Avrundning.** En senare version som bara avrundar tusental till hela miljoner tas bort, som i `neoclouds`. Det tar
  bort en rad i `rev_eqix` och en i `capex_eqix`.

## Kontroll mot inlämningarna

Värden ur serien (senaste version) mot bolagets egna rader i den renderade inlämningen på www.sec.gov. Alla stämmer.

| Bolag och kvartal | Inlämning (accession) | Serie och värde | Rad i rapporten |
|---|---|---|---|
| VRT 2026Q3 | 10-Q 0001628280-26-067893 (2026-10-28) och 10-Q 0001628280-26-050609 | `rev_vrt` 4 312,8, `capex_vrt` 139,1, `rev_vrt_americas` 2 999,0, `rev_vrt_apac` 1 008,1, `rev_vrt_emea` 823,7 | "Net sales" 4 312,8; "Capital expenditures" 9M 425,0 − 6M 285,9; segmentnoten "Sales" 2 999,0, 1 008,1 och 823,7 (därav interna 10,2, 228,8 och 279,0) |
| GEV 2026Q3 | 10-Q 0001996810-26-000163 (2026-10-28) | `rev_gev` 12 642, `rev_gev_power` 6 067, `rev_gev_wind` 2 741, `rev_gev_electrification_fy26` 3 862, `rpo_gev` 196 721, `rpo_gev_equipment` 104 054, `rpo_gev_services` 92 667 | "Segment revenues" 6 067, 3 862, 2 741 (summa 12 671, eliminering −29, totalt 12 642); RPO "$ 196,721 million", "Equipment-related RPO of $ 104,054 million", "Services-related RPO of $ 92,667 million" |
| ETN 2025Q4 (Q4 = helår − 9M) | 10-K 0001551182-26-000007 (2026-02-26) och 10-Q 0001551182-25-000036 | `rev_etn` 7 055, `capex_etn` 392 | "Net sales" 27 448 − 20 393; "Capital expenditures for property, plant and equipment" 919 − 527 |
| ETN 2026Q3 | 10-Q 0001551182-26-000040 (2026-11-03) | `rev_etn` 8 947, `rev_etn_electrical_americas` 4 172, `rev_etn_electrical_global` 2 727, `rpo_etn` 26 200 | segmentnoten "Net sales" 4 172 och 2 727, totalt 8 947; "total backlog at September 30, 2026 was approximately $ 26.2 billion" |
| PWR 2026Q3 | 10-Q 0001050915-26-000041 (2026-10-29) | `rev_pwr` 12 014,9, `rpo_pwr` 41 750 | "Revenues" 12 014 877 (tusental); "remaining performance obligations were approximately $ 41.75 billion" |
| EQIX 2026Q3 | 10-Q 0001101239-26-000180 (2026-10-28) och 10-Q 0001101239-26-000147 | `capex_eqix` 1 558, `rpo_eqix` 15 900 | "Purchases of other property, plant and equipment" 9M 4 392 − 6M 2 834; "Approximately $ 15.9 billion of revenues ... unsatisfied performance obligations" |
| DLR 2026Q3 | 10-Q 0001104659-26-120710 (2026-10-30) och 10-Q 0001104659-26-089296 | `capex_dlr` 1 382,0, `rev_dlr` 1 902,4 | "Improvements to investments in real estate" 9M 3 166 212 − 6M 1 784 229 (tusental); "Total operating revenues" 1 902 418 |

Föregångarskarven för Eaton kontrollerades i companyfacts: 2012Q4 = helår 2012 i plc-bolagets 10-K (16 311) − 9M i
Eaton Corporations 10-Q 2012-10-31 (11 978) = 4 333. December 2012 innehåller alltså Cooper, och kvartalen före inte.

## Kalender och datering

- known_from är inlämningsdatumet för 10-Q eller 10-K. Varje inlämning är en version. YTD-differens och
  Q4 = helår − 9M som i `sec.py`.
- `lag_days` = 25. Aktualitetsgräns per bolag = största observerade avstånd från kvartalets slut till första egna 10-Q
  eller 10-K 2015–2026 + 92 + 30: VRT 72 (10-K 2019-03-13 och 2020-03-12) → 194, GEV 37 (bara 2024–2026) → 159, ETN 60 →
  182, PWR 61 → 183, EQIX 61 → 183, DLR 62 → 184 dagar.
- Kvartal som bara finns som jämförelsetal får known_from för den senare inlämningen: Vertivs kvartal 2019 (10-Q
  2020), GE Vernovas kvartal 2023 (10-Q 2024) och Eatons Q4 2012. Det är sent men konservativt.

## Kända problem och förbehåll

- **Mest annat än AI.** GE Vernova är gasturbiner, vind och elnät. Eaton är också flyg och fordon, och de elektriska
  segmenten säljer till bostäder, industri och energibolag. Quanta bygger elnät och underjordisk infrastruktur för
  energibolag. Vertiv är närmast datacenter, men har också telekom och industri. **Datacenterandelen går inte att
  skilja ut i XBRL.** Spår S3 extraherar bolagens uttalade datacentersiffror (andel av order, orderstock, tillväxt) ur
  pressmeddelandena.
- **RPO är inte orderingång.** RPO och orderstock är balanser. Förändringen mellan två kvartal är order minus leveranser,
  plus valuta och förvärv. GE Vernovas RPO för tjänster är långa serviceavtal (upp till 15 år) och rör sig långsamt.
- **Förvärv.** Inga serier justeras för förvärv. Eaton köpte Cooper 2012, Fibrebond 2025 och Boyd Thermal 2026. Vertiv
  köpte Great Lakes 2025 och fler bolag 2026. GE Vernova konsoliderade Prolec GE 2026. Det syns som nivåskiften.
- **Quanta 2012–2015.** Omräkningar 2013–2016, troligen för avvecklad verksamhet (vilka verksamheter är inte
  kontrollerat i texten), ger 8–9 reviderade kvartal i `rev_pwr` och `capex_pwr`. Första versionen av 2012Q4 (intäkter
  1 293,2, capex 49,1) är troligen helåret på ny bas minus 9M på gammal bas, och den rättas 2014-03-03 (1 673,3 och
  60,8). Samma mekanism som Alphabet 2012Q4 i `docs/kallor/sec.md`. Helåret 2013 räknades om i 10-K 2016 utan
  kvartal, och kvartalen ligger kvar på den tidigare basen.
- **Korta serier.** GE Vernova har 15 kvartal (RPO 11), och `rev_gev_electrification_fy26` 3. Eatons segment och
  orderstock börjar 2020. Långa serier: `rev_etn`, `capex_etn`, `rev_pwr`, `capex_pwr` (73–74 kvartal), `rev_eqix` (70) och
  DLR (65–66).
- **Vertivs segment är brutto.** `rev_vrt_*` innehåller försäljning mellan segmenten, så de summerar inte till
  `rev_vrt`. Asia Pacific har störst intern försäljning (fabriker som levererar till de andra regionerna).
- **companyfacts kan släpa.** Digital Realtys två senaste 10-Q saknades i companyfacts. Om det händer andra bolag blir
  serien för gammal och fångas av aktualitetstestet.
- **`defnref.xml` i äldre inlämningar.** `sec_segment.instance_name` väljer den filen när den finns (fyra DLR- och sju
  Microsoft-inlämningar 2009–2011 i den delade cachen). Då läses inga fakta ur inlämningen. Det påverkar bara första
  versionen av några kvartal här, men kan påverka andra serier som läser instanser från 2009–2011. Det rättas inte här,
  eftersom koden är gemensam.

## Inte byggt

- **Segment för Quanta.** Fem segmentindelningar 2018–2026 (Electric Power och Oil and Gas, Pipeline and Industrial,
  Underground Utility, Renewable Energy, sedan Electric och Underground and Infrastructure från 2025), med byten av
  medlemsnamn nästan varje år.
- **Uppdelning av RPO i tid** (se ovan) och RPO per segment, som inte taggas hos något av bolagen.
- **Regioner för Equinix** (Americas, EMEA, Asia-Pacific finns taggade) och produktlinjer för Vertiv och GE Vernova
  (till exempel Gas Power, Grid Solutions och Power Conversion & Storage).
- **Möjliga tillägg:** Vertivs externa segmentförsäljning ("Net Sales", medlemmen utan markör) som egna nycklar, Equinix
  fastighetsköp som egen serie och operativt kassaflöde för de sex bolagen.
