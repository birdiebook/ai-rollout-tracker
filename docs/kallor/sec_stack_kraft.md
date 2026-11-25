# Källa: kraft, kylning, elnät och datacenterbolag ur SEC XBRL

Spår S2, körning 14. Byggt 2026-11-25 och kontrollerat mot bolagens inlämningar. Kod:
`src/ai_tracker/series/sec_stack_kraft.py`. Kvartalslogik och versioner: `sources/sec.py`, `sources/sec_rpo.py` och
`sources/sec_segment.py`. Tester: `tests/test_sec_stack_kraft.py` (syntetiska fixturer, inget nät). Taggvalen är
förregistrerade i `docs/mattregister.md` (2026-11-25, S2) i commit 009602a, före hämtningen av värden. Tilläggen efter
första bygget står i registret samma dag ("S2: tillägg efter första bygget"). Granskningen R18
(`docs/granskning/r18-kraft-datacenter.md`) fann fyra fel. De rättades i spår X15, och reglerna för rättningen står i
registret ("X15: rättning av S2 efter R18"), i commit d2c14cc före den nya hämtningen. Här finns ingen trendanalys.

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

**Före X15-tillägget** sågs granskningen R18 med alla dess siffror, också de simulerade rättningarna. Egna kontroller av
täckning och konsistens: medlemmar och markörer per inlämning hos Eaton 2020–2021 och om värdena är lika i överlappet,
båda capex-taggarnas fakta per inlämning hos Equinix (med värden, YTD 2009–2019) och kassaflödesanalysen i 10-Q
2011-04-29, Digital Realtys fakta för intäkter och capex i de fyra inlämningarna med `defnref.xml` (värden och
dimensioner), antalet fakta med Microsofts tagg i de sju inlämningarna med filen och Nvidias indexfiler 2012–2013.

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

Hämtning 2026-11-25 efter rättningarna i X15: 30 serier och 1 121 rader (S2 hade 27 serier och 986 rader). "Rev." är
antalet kvartal med mer än en version.

| Nyckel | Gren | Innehåll | Kvartal | Från–till | Rader | Rev. |
|---|---|---|---|---|---|---|
| `rev_vrt` | G7 | intäkter | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `capex_vrt` | G7 | capex | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `rev_vrt_americas` | G7 | segment Americas (inkl. försäljning till andra segment) | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `rev_vrt_apac` | G7 | segment Asia Pacific (inkl. försäljning till andra segment) | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `rev_vrt_emea` | G7 | segment Europe, Middle East & Africa (inkl. försäljning till andra segment) | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `rev_vrt_americas_net` | G7 | segment Americas, extern försäljning | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `rev_vrt_apac_net` | G7 | segment Asia Pacific, extern försäljning | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `rev_vrt_emea_net` | G7 | segment Europe, Middle East & Africa, extern försäljning | 31 | 2019Q1–2026Q3 | 31 | 0 |
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
| `rev_etn_electrical_americas` | G7 | segment Electrical Americas | 35 | 2018Q1–2026Q3 | 35 | 0 |
| `rev_etn_electrical_global` | G7 | segment Electrical Global | 35 | 2018Q1–2026Q3 | 35 | 0 |
| `rpo_etn` | G7 | orderstock (fasta order, taggad som RPO) | 25 | 2020Q3–2026Q3 | 25 | 0 |
| `rev_pwr` | G7 | intäkter | 74 | 2008Q2–2026Q3 | 82 | 8 |
| `capex_pwr` | G7 | capex | 74 | 2008Q2–2026Q3 | 83 | 9 |
| `rpo_pwr` | G7 | RPO totalt | 35 | 2018Q1–2026Q3 | 35 | 0 |
| `rev_eqix` | G4 | intäkter | 70 | 2009Q2–2026Q3 | 77 | 7 |
| `rpo_eqix` | G4 | RPO totalt | 35 | 2018Q1–2026Q3 | 35 | 0 |
| `capex_eqix` | G5 | capex (bygge och utrustning, utan fastighetsköp) | 69 | 2009Q3–2026Q3 | 69 | 0 |
| `rev_dlr` | G4 | intäkter | 70 | 2009Q2–2026Q3 | 70 | 0 |
| `capex_dlr` | G5 | capex (förbättring av fastigheter, utan förvärv) | 69 | 2009Q3–2026Q3 | 69 | 0 |

Datatesterna (`python -m ai_tracker.warehouse`) är gröna på spårets vy, aktualiteten inräknad. Undantaget är
`series_in_catalog` för `us_gdp_contrib_final_sales_computers`, en serie som ett annat spår lade i den delade bastabellen
under körningen och som inte finns i den här grenens katalog.

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
| PWR | `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueServicesNet` | `PaymentsToAcquirePropertyPlantAndEquipment` ("Capital expenditures", 2013–2014 "Additions of property and equipment") | identiska i 7 överlappande perioder |
| EQIX | `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues` | `PaymentsToAcquireOtherPropertyPlantAndEquipment` ("Purchases of other property, plant and equipment"), `PaymentsToAcquirePropertyPlantAndEquipment` (samma rad i 10-Q 2010–2018, där "Purchases of property, plant and equipment") | intäktstaggarna identiska i 7 perioder. Capex-taggarna se nedan. "Real estate acquisitions" (`PaymentsToAcquireRealEstate`) ingår inte |
| DLR | `Revenues` ("Total operating revenues") ur instanserna | `PaymentsToDevelopRealEstateAssets` ("Improvements to investments in real estate", 2011–2014 "Improvements to and advances for investments in real estate") ur instanserna | värdena räknades inte om vid etikettbytet (9M 2014 644 637 och helåret 2013 1 189 510 i alla senare inlämningar). "Cash paid for business combination / asset acquisitions" och "Investments in and advances to unconsolidated entities" ingår inte |

**Capex för datacenterbolagen.** Måttet är utbyggnad och förbättring av egen kapacitet: raden för bygge och
utrustning. Köp av befintliga fastigheter, mark och bolag ingår inte. Equinix egen capex i segmentnoten
(`PaymentsToAcquireProductiveAssets`, "Capital expenditures" per region) är lika med raden för "other property, plant and
equipment" i 42 av 52 överlappande perioder och innehåller inte fastighetsköpen. Den taggas inte längre i 10-Q från 2026Q2 och används därför inte. De
två datacenterbolagen är jämförbara med varandra, men inte helt med de stora molnbolagen, vars capex också innehåller
köpt mark och köpta byggnader.

**Equinix, den äldre capex-taggen (rättat i X15, R18-2).** Capex-raden har `PaymentsToAcquirePropertyPlantAndEquipment`
i 10-Q 2010-08-04 och 2010-10-29, i 10-Q 2012-04-27 till 2014-11-07 och i 10-Q 2016-11-04, och båda taggarna parallellt
i 10-Q 2017–2018. Raden hette "Purchases of property, plant and equipment" i 10-Q 2010–2014. I två inlämningar har
Equinix den nya taggen på capex-raden och den äldre på ett fastighetsköp: 10-K 2011-02-25 ("Purchase of Amsterdam IBX
property", 14 861 tusen USD för 2010) och 10-Q 2011-04-29 ("Purchase of Paris 4 IBX property", 14 951 för Q1 2011).
Utan de två fakta är taggarna identiska i alla 18 överlappande perioder. Regeln (registret, X15): en tagg med lägre
prioritet används inte ur en inlämning där den har ett annat värde än en tagg med högre prioritet för samma period
(`same_line`). Det tar bort exakt de två fakta. S2 förkastade den äldre taggen helt, så `capex_eqix` började 2014Q1, och
2014Q1–Q4, 2016Q3 och 2016Q4 fick sin första version ett år för sent. Efter rättningen börjar serien 2009Q3 (69 kvartal,
inga revideringar, inga negativa värden), och värdena från 2014 är oförändrade. Bara dateringen ändras: 2014Q1 från
2014-05-02 i stället för 2015-05-01, 2016Q3 från 2016-11-04 och 2016Q4 från 2017-02-27 i stället för 2017-11-03. En
skarv mot Amsterdam-raden hade gett 2010Q4 = 14,9 − 436,0 = −421,2. Det spärras av regeln och av ett test.

**Digital Realty ur instanserna.** Fakta utan dimension gäller Digital Realty Trust, Inc. Partnerskapet (Digital Realty
Trust, L.P.) har samma siffror med `LegalEntityAxis`. Två fel gjorde att S2:s serier började 2010Q2 och 2010Q3 och att
2010Q2–2011Q2 fick sin första version upp till ett år för sent. Båda är rättade i X15:
- `sec_segment.instance_name` valde filen `defnref.xml` i fyra inlämningar 2010–2011 (R18-4). Rättat i den gemensamma
  koden. Det ger tillbaka 10-Q/A 2010-08-12, den första inlämningen med XBRL (den ursprungliga 10-Q 2010-08-05 har
  ingen).
- I 10-Q 2010-11-09, 10-K/A 2011-03-25 och 10-Q 2011-05-09 har alla fakta `LegalEntityAxis`: bolaget med
  `ParentCompanyMember` och partnerskapet med `DigitalRealtyTrustLPMember`, med samma värden. Där finns inga fakta utan
  dimension, så de tre inlämningarna gav inget även efter rättningen ovan. Det var orsaken till de sena versionerna av
  2010Q3–2011Q1, inte `defnref.xml` som granskningen trodde. Regel (registret, X15): saknas fakta utan dimension för en
  tagg i en inlämning, läses fakta med bara `LegalEntityAxis` = `ParentCompanyMember`. Medlemmen finns bara i de tre
  inlämningarna.

Efter rättningen börjar `rev_dlr` 2009Q2 (70 kvartal) och `capex_dlr` 2009Q3 (69). Inga revideringar. 2010Q3 är känt
från 2010-11-09 (237 486 tusen USD) och 2011Q1 från 2011-05-09.

**Paritet med companyfacts** (engångskontroll vid bygget, ingen kontroll i koden; R18-10). Gjord om efter
rättningarna, mot companyfacts hämtat 2026-11-25, för alla versioner till och med 2026-05-01. Instansserien har alla
companyfacts-seriens värden. Skillnaden är bara dateringen av kvartalen ur de tre inlämningarna med
`ParentCompanyMember`, som companyfacts saknar eftersom fakta har en dimension: `rev_dlr` 2009Q3–2011Q1 och `capex_dlr`
2009Q3–2011Q2 är kända tidigare i instansserien. Värdena är desamma. companyfacts saknar fortfarande 10-Q 2026-07-31 och
2026-10-30.

## Segmentintäkter

En fakta räknas bara när kontextens dimensioner är exakt de angivna. En produktaxel, en tidsaxel eller en annan markör
utesluter den.

| Serie | Medlem och markör | Vad siffran är |
|---|---|---|
| `rev_gev_*` | `PowerSegmentMember`, `WindSegmentMember`, `ElectrificationSegmentMember` med `ConsolidationItemsAxis` = `OperatingSegmentsExcludingIntersegmentEliminationMember` | "Segment revenues" i segmentnoten, före eliminering av interna intäkter (till exempel Power 2026Q3: 6 067 varav 8 interna). Markören finns i alla elva inlämningar. `OperatingSegmentsMember` finns bara i 10-Q 2024 och avviker upp till 5 % |
| `rev_etn_electrical_*` | `ElectricalAmericasSegmentMember`, `ElectricalGlobalSegmentMember` (från 10-K 2021-02-24), i 10-Q 2020 `ElectricalAmericasMember`, `ElectricalGlobalMember`. Utan markör och annars med `OperatingSegmentsMember` | "Net sales" per segment. Varianterna utan och med markör är identiska i 156 par, och de två namnen i alla 14 par där båda finns. Bara inlämningar från 2020, eftersom `ElectricalAmericasMember` användes för ett äldre segment i 10-K för 2012. Segmenten finns från 10-Q 2020-04-30, som också redovisar alla kvartal 2018–2019 omräknade till de nya segmenten. Serierna börjar därför 2018Q1, med de kvartalen kända från 2020-04-30 |
| `rev_vrt_*` | `AmericasSegmentMember`, `AsiaPacificSegmentMember`, `EMEASegmentMember` med `ConsolidationItemsAxis` = `OperatingSegmentsMember` | raden "Sales" i segmentnoten, inklusive försäljning till andra segment ("Intersegment sales"). Summan av de tre serierna är större än `rev_vrt` (2026Q3: 4 830,8 mot 4 312,8) |
| `rev_vrt_*_net` | samma medlemmar utan markör | raden "Net Sales" i segmentnoten och "Net sales" per segment i MD&A: extern försäljning. Summan av de tre är `rev_vrt` i alla 31 kvartal. 10-K 2024-02-23 saknar kontexten, så 2023Q4 är känt från 10-K 2025-02-18 |

S2 valde brutto ("Sales") med skälet att medlemmen utan markör saknas i 10-K 2024-02-23. Det skälet håller inte, eftersom
10-K 2025-02-18 har helåret 2023 som jämförelsetal och den externa serien inte förlorar något kvartal (R18-3). Båda
finns nu. Bruttot är segmentnotens tabell ("Sales" med en rad "Eliminations"), det externa är det bolaget redovisar per
segment i MD&A och det som summerar till bolagets intäkter. För tillväxt per region är den externa serien den rätta,
eftersom bruttot också räknar leveranser till de andra regionerna.

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
  bara denna fakta bland S2:s serier. `rev_eqix` 2023Q1 är 1 998,2 (10-Q 2023-05-05). Regeln gäller flöden och
  balanser, inte segmentintäkter (registret, X15, R18-9): segmentnoten efter en ny segmentindelning kan redovisa äldre
  kvartal, som Eatons 10-Q 2020-04-30 med kvartalen 2018Q1–Q3 (578–761 dagar).
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
  182, PWR 61 → 183, EQIX 61 → 183, DLR 62 → 184 dagar. Vertivs 72 dagar kommer från 10-K som SPAC-bolaget GS
  Acquisition Holdings lämnade före sammanslagningen. Vertivs egna inlämningar har högst 60 dagar, så gränsen är lösare
  än nödvändigt, men inte fel (R18-7). GE Vernovas gräns bygger på två års inlämningar och ligger ändå över fristen
  för 10-K (60 dagar) plus marginalen.
- Kvartal som bara finns som jämförelsetal får known_from för den senare inlämningen: Vertivs kvartal 2019 (10-Q
  2020), GE Vernovas kvartal 2023 (10-Q 2024), Eatons Q4 2012, Eatons segmentkvartal 2018–2019 (10-Q 2020-04-30) och
  Vertivs externa segmentförsäljning 2023Q4 (10-K 2025-02-18). Det är sent men konservativt.
- Före rättningen i X15 fick några kvartal sin första version upp till ett år för sent: Eatons segment 2020Q1–Q4,
  Equinix capex 2014Q1–Q4 och 2016Q3–Q4, och Digital Realty 2010Q2–2011Q2. Nu är de daterade till den inlämning som
  först redovisar dem.

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
- **Quanta 2012–2015.** Omräkningar 2013–2016 ger 8–9 reviderade kvartal i `rev_pwr` och `capex_pwr`. Första
  versionen av 2012Q4 (intäkter 1 293,2, capex 49,1) är helåret på ny bas minus 9M på gammal bas, och den rättas
  2014-03-03 (1 673,3 och 60,8). Kontrollerat i R18 (R18-5): helåret i 10-K 2013-03-01 är 5 920 269 tusen USD, 9M på
  gammal bas i 10-Q 2012-11-07 är 4 627 074 och 9M på ny bas i 10-Q 2013-11-08 är 4 246 927. Skillnaden 380 147 är
  intäkten 9M 2012 i den avvecklade verksamheten, "substantially all of its domestic telecommunications infrastructure
  services operations", som såldes 2012-12-03. Det är den kända begränsningen i `sec.py` (Alphabet 2012Q4 i
  `docs/kallor/sec.md`). Orsaken till de senare omräkningarna är inte kontrollerad. Helåret 2013 räknades om i 10-K 2016
  utan kvartal, och kvartalen ligger kvar på den tidigare basen.
- **Korta serier.** GE Vernova har 15 kvartal (RPO 11), och `rev_gev_electrification_fy26` 3. Eatons segment börjar
  2018 och orderstocken 2020Q3. Långa serier: `rev_etn`, `capex_etn`, `rev_pwr`, `capex_pwr` (73–74 kvartal), `rev_eqix`
  (70), `capex_eqix` (69) och DLR (69–70).
- **Vertivs bruttosegment.** `rev_vrt_americas`, `rev_vrt_apac` och `rev_vrt_emea` innehåller försäljning mellan
  segmenten, så de summerar inte till `rev_vrt`. Den interna försäljningen var störst i Asia Pacific till och med
  2021Q3 och är störst i EMEA från 2021Q4 (2026Q3: EMEA 279,0, Asia Pacific 228,8, Americas 10,2). EMEA:s interna
  andel har vuxit från 5 % (2020Q1) till 34 % (2026Q3), så en del av tillväxten i `rev_vrt_emea` är leveranser till
  andra regioner. Den externa försäljningen per segment är `rev_vrt_*_net`.
- **companyfacts kan släpa.** Digital Realtys två senaste 10-Q saknades i companyfacts. Om det händer andra bolag blir
  serien för gammal och fångas av aktualitetstestet.
- **`defnref.xml` i äldre inlämningar (rättat i X15).** `sec_segment.instance_name` valde den filen när den fanns
  (fyra DLR- och sju Microsoft-inlämningar 2009–2011 i den delade cachen), och då lästes inga fakta ur inlämningen.
  Filen utesluts nu i den gemensamma koden. På denna gren påverkar det `rev_dlr`, `capex_dlr` och `dep_msft`
  (`docs/kallor/sec_avskrivningar.md`). Nvidias inlämningar 2012–2013 har inte filen. Andra spår i körning 14 som läser
  instanser från 2009–2011 har inte kontrollerats här.

## Inte byggt

- **Segment för Quanta.** Fem segmentindelningar 2018–2026 (Electric Power och Oil and Gas, Pipeline and Industrial,
  Underground Utility, Renewable Energy, sedan Electric och Underground and Infrastructure från 2025), med byten av
  medlemsnamn nästan varje år.
- **Uppdelning av RPO i tid** (se ovan) och RPO per segment, som inte taggas hos något av bolagen.
- **Regioner för Equinix** (Americas, EMEA, Asia-Pacific finns taggade) och produktlinjer för Vertiv och GE Vernova
  (till exempel Gas Power, Grid Solutions och Power Conversion & Storage).
- **Möjliga tillägg:** Equinix fastighetsköp som egen serie och operativt kassaflöde för de sex bolagen.

## Kontroll efter rättningarna (X15)

Nya och omdaterade värden mot bolagets egen rad i den renderade inlämningen på www.sec.gov. Alla stämmer.

| Bolag och kvartal | Inlämning (accession) | Serie och värde | Rad i rapporten |
|---|---|---|---|
| ETN 2018Q1–2019Q4 | 10-Q 0001551182-20-000127 (2020-04-30) | `rev_etn_electrical_americas` 1 838, 1 974, 2 008, 2 094, 1 961, 2 085, 2 040, 2 089, kända från 2020-04-30 | not 13, "New Business Segments": "previously reported segment financial information has been updated for all periods reported in 2018 and 2019", Electrical Americas "Net sales" per kvartal |
| EQIX 2009Q3, 2010Q3 | 10-Q 0001193125-10-241047 (2010-10-29) och 10-Q 0001193125-10-176872 | `capex_eqix` 88,2 och 143,9 | "Purchases of property, plant and equipment" 9M 2010 436 046 och 9M 2009 267 802, minus 6M 292 105 och 179 607 (10-Q 2010-08-04) |
| EQIX 2009Q4, 2010Q4 | 10-K 0001193125-11-047157 (2011-02-25) | `capex_eqix` 101,7 och 143,4 | "Purchases of other property, plant and equipment" 2010 579 397 och 2009 369 542, minus 9M ovan |
| EQIX 2011Q1 | 10-Q 0001193125-11-118503 (2011-04-29) | `capex_eqix` 175,1, aldrig 14,951 | "Purchases of property, plant and equipment" 175 115; "Purchase of Paris 4 IBX property" 14 951 på egen rad |
| DLR 2009Q3, 2010Q3 | 10-Q 0001193125-10-254366 (2010-11-09) | `rev_dlr` 163,2 och 237,5 | "Total operating revenues" 237 486 och 163 227; "Improvements to investments in real estate" 9M 248 737 och 323 155 |
| VRT 2026Q3 | 10-Q 0001628280-26-067893 (2026-10-28) | `rev_vrt_americas_net` 2 988,8, `rev_vrt_apac_net` 779,3, `rev_vrt_emea_net` 544,7 | segmentnoten "Net Sales" 2 988,8, 779,3 och 544,7 (summa 4 312,8 = "Net sales"); MD&A "Europe, Middle East & Africa net sales were $544.7" |
| MSFT 2009Q4, 2010Q4 | 10-Q 0001193125-11-015947 (2011-01-27) | `dep_msft` 615 och 663, kända från 2011-01-27 | "Depreciation, amortization, and other" 663 och 615 (tre månader) |

## Rättning efter R18 (X15)

| # | Rättning | Effekt |
|---|---|---|
| R18-1 | Eatons namn i 10-Q 2020 läses som alternativ | `rev_etn_electrical_*` 27 → 35 kvartal, från 2018Q1. 2020Q1–Q3 kända från 2020 års 10-Q, 2020Q4 från 10-K 2021-02-24. Inga värden ändras, inga brott |
| R18-9 | 550-dagarsregeln gäller inte segmentintäkter | behåller Eatons 2018Q1–Q3 (578–761 dagar). Inga andra segmentserier ändras |
| R18-2 | Equinix äldre capex-tagg skarvas, utom ur inlämningar där den står på en annan rad | `capex_eqix` 51 → 69 kvartal, från 2009Q3. Värdena från 2014 oförändrade, sex kvartal tidigare daterade |
| R18-3 | Dokumentet rättat; Vertivs externa segmentförsäljning som nya nycklar | tre nya serier, 31 kvartal vardera. Bruttoserierna oförändrade |
| R18-4 | `instance_name` utesluter `defnref.xml` (gemensam kod) | `rev_dlr` och `capex_dlr` tillsammans med punkten nedan; `dep_msft` 65 → 68 kvartal, från 2009Q4, och 2010Q4–2011Q2 kända ett år tidigare (inga värden ändras) |
| följd av R18-4 | Digital Realtys `ParentCompanyMember` i tre inlämningar 2010–2011 | `rev_dlr` 66 → 70 kvartal (från 2009Q2), `capex_dlr` 65 → 69 (från 2009Q3). 2010Q2–2011Q2 kända upp till ett år tidigare. Inga värden ändras |
| R18-5, R18-7, R18-8, R18-10 | Dokumentet: Quantas 2012Q4, Vertivs aktualitetsgräns, äldre radetiketter, pariteten som engångskontroll | inga data ändras |

Den nya regeln för taggval (`same_line`) gäller alla S2:s flöden. Den ändrar bara `capex_eqix`. Alla andra av S2:s 27
serier är identiska med S2:s hämtning, rad för rad.
