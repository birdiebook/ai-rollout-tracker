# R18 – granskning av S2: kraft, kylning, elnät och datacenterbolag ur SEC XBRL

Granskningsspår R18, körning 14, 2026-11-25, gren `auto14k/r18-kraft-datacenter` (från `auto14k/s2-kraft-datacenter`).
Granskat: de 27 katalogserierna i `src/ai_tracker/series/sec_stack_kraft.py`, registerposterna 2026-11-25 (S2) i
`docs/mattregister.md`, källdokumentet `docs/kallor/sec_stack_kraft.md` och testerna `tests/test_sec_stack_kraft.py`.

Underlag: inlämningarnas egna dokument på www.sec.gov (huvuddokumentet för 10-Q och 10-K, 44 dokument, råkopior
under `data/raw/r18_check/`), XBRL-instanserna i den delade cachen (`data/raw/sec_segment/`), companyfacts och
inlämningslistorna (hämtade på nytt i dag). Alla anrop till sec.gov gick sekventiellt. Inget 403 eller 429.

Serierna byggdes om med spårets kod i den här worktree. Resultatet är identiskt med spårets data: 986 rader, samma
nycklar, perioder, `known_from` och värden. Ingen analys av förlopp gjordes. Värden lästes bara för att kontrollera
taggar, datering och definitioner.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering | **OK**. Posten kom före värdena. Tilläggets två regler är regler för datafel |
| 2. Taggval och brott | **Anmärkning.** GE Vernova OK. Eatons segment läser inte 2020 års 10-Q (R18-1). Vertivs bruttosegment har ett skäl som inte håller (R18-3) |
| 3. RPO som balanser | **OK** |
| 4. Capex för datacenterbolagen | **Anmärkning.** Definitionerna är rätt och konsekventa. Equinix gamla tagg förkastas på en rad som inte hör till måttet (R18-2) |
| 5. Handkontroller | **OK.** 12 kontroller, alla sex bolagen, alla värden stämmer. Tre visar för sen första version |
| 6. Grenar, licens och klass | **OK** |
| 7. Förbehåll i dokumentet | **Anmärkning.** Tre påståenden är fel (R18-1, R18-2, R18-3) |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Inga läckage och inga fel värden hittades. Alla registrerade regler är
implementerade som de står. Felen gör att vissa första versioner dateras upp till ett år för sent och att
historik saknas. Det är på den konservativa sidan. Rättningarna R18-1–R18-4 behövs innan serierna används i analys,
och dokumentet behöver rättas.

## 1. Förregistrering – OK

Ordningen (2026-11-25, UTC):

| Tid | Händelse |
|---|---|
| 08:56 | Worktree skapas |
| 08:59–09:13 | 498 filer i den delade cachen för de sex bolagen: `index.json` och XBRL-instanser |
| 09:13:55 | `009602a`: registerposten (taggar, medlemmar, markörer, RPO, grenar, vad som setts) |
| 09:17 | 10-Q 2026-04-22 för GE Vernova läses (texten om omorganisationen) |
| 09:20–09:28 | companyfacts hämtas (råkopiorna skrivs över vid ny hämtning samma dag, så tidigare hämtningar syns inte) |
| 09:23 | `data/observations.parquet` skrivs (första värdena i spårets tabell) |
| 09:24–09:25 | Huvuddokument för handkontrollerna |
| 09:31:20 | `782f173`: kod, tester, källdokument och registrets tillägg |

- Instanserna låg i cachen före posten. Det stämmer med vad posten säger att spåret tittade på: vilka medlemmar och
  markörer som finns per inlämning, hur RPO är taggat och största relativa skillnad mellan kandidattaggar. Det är
  kontroller av täckning och konsistens. Git visar bara vad som committades, inte vad som räknades lokalt.
- Posten listar öppet de orderstocksbelopp som syntes i texten (Vertiv 15,0 och 7,2, Eaton 5,4–26,2 mdr USD).
- **Tilläggets regler är regler för datafel.** Kontrollerat över alla S2-källor
  med ett skript utanför repot:
  - 550-dagarsregeln tar bort exakt en fakta: Equinix 10-Q 0001628280-25-021086 (2025-04-30), kontext
    2023-01-01–2023-03-31, värde 2 225. Dokumentet har bara kolumnerna Q1 2025 (2 225) och Q1 2024 (2 127). Faktan är
    alltså Q1 2025 med fel datum. Bland 10-Q-fakta i flödena är den äldsta som behålls 408 dagar.
  - Regeln om Eatons skalbolag tar bort exakt två fakta, båda 0, ur 10-Q 0001551182-12-000004 (2012-11-14).
  - Ingen av reglerna beror på seriernas förlopp.
- Brottet för GE Vernova följer den registrerade mekanismen (`definition_breaks`, 2 %), och det deklarerades i
  tillägget efter första bygget, som regeln kräver.

## 2. Taggval och brott – anmärkning

**GE Vernova och avknoppningen 2024.** Bara CIK 1996810. Form 10 (10-12B 2024-02-15 och 10-12B/A 2024-03-05) har
`isXBRL` = 0. 8-K 2024-04-02 har XBRL, men `sec.facts` läser bara 10-Q och 10-K. Alla fakta kommer från GE Vernovas
egna 10-Q och 10-K från 2024-04-30. Kvartalen 2023 är bolagets egna jämförelsetal: 2023Q1 6 822 (10-Q 2024-04-30),
2023Q4 = 33 239 − 23 194 = 10 045 (10-K 2025-02-06 och 10-Q 2024-10-23, `known_from` 2025-02-06). Inga värden från
GE före avknoppningen förekommer.

**GE Vernova Electrification.** Omräkningarna i 10-Q 2026 räknades fram ur instanserna: Electrification Q1 2025
1 879 → 1 840 (−2,08 %), Q2 −1,77 %, Q3 −1,38 %, 6M −1,94 %, 9M −1,74 %. Power +0,52 till +0,59 %. Wind oförändrat.
Texten i 10-Q 0001996810-26-000064: "a component of our former Electrification Software business unit was realigned
into Gas Power". Uppdelningen i `_fy24` och `_fy26` stämmer med regeln. Power räknas om med samma omorganisation men
under gränsen. Det blir versioner (R18-6, anmärkning).

**R18-1. Eatons elektriska segment: 2020 års 10-Q läses inte (should_fix).** Medlemsnamnen per inlämning:

| Inlämning | Medlemmar |
|---|---|
| 10-K 2013-02-28 (för 2012) | `ElectricalAmericasMember`, `ElectricalRestOfWorldMember` (äldre indelning) |
| 10-Q 2013 – 10-K 2020-02-26 | `ElectricalProductsMember`, `ElectricalSystemsAndServicesMember` |
| 10-Q 2020-04-30, 2020-07-29, 2020-11-03 | `ElectricalAmericasMember`, `ElectricalGlobalMember` |
| 10-K 2021-02-24 och senare | `ElectricalAmericasSegmentMember`, `ElectricalGlobalSegmentMember` |

Registret anger bara `...SegmentMember`. Det är implementerat som det står, men följden är:
- 2020Q1–Q3 får sin första version ett år för sent (2021-05-04, 2021-08-03, 2021-11-02 i stället för 2020-04-30,
  2020-07-29, 2020-11-03), och 2020Q4 2021-11-02 i stället för 2021-02-24. Värdena är desamma (2020Q1 1 788 och
  1 144 i båda namnen).
- 10-Q 0001551182-20-000127 (2020-04-30) har de nya segmenten för alla kvartal 2018–2019 (till exempel Electrical
  Americas 2019Q1 1 961). De saknas i serien.
- Registrets skäl för startdatumet är fel i detaljen: 10-K för 2012 använde `ElectricalAmericasMember`, inte
  `ElectricalAmericasSegmentMember`. Startdatumet 2020-01-01 är ändå rätt, och det gör det säkert att lägga till
  2020 års namn.
- Källdokumentet säger "2020 års 10-Q har inga kvartalsvisa jämförelsetal för 2019". Det är fel.

Simulerad rättning (namnen från 2020 som alternativ): inga brott. Båda serierna får 32 kvartal från 2018Q4, och
2020Q1–Q4 dateras till 2020 års inlämningar. 2018Q1–Q3 tas då bort av 550-dagarsregeln (578 dagar), fast de är
riktiga omräknade jämförelsetal (R18-9).

**R18-3. Vertivs segment: brutto valt på ett täckningsskäl som inte håller (should_fix).** Definitionen är
konsekvent: i alla 10-Q 2020–2026 är "Sales" (`OperatingSegmentsMember`) = extern "Net sales" (utan markör) +
intern försäljning (`IntersegmentEliminationMember`). Det stämmer i varje inlämning. Men:
- Den externa serien är komplett. 10-K 2024-02-23 saknar medlemmen utan markör, men 10-K 2025-02-18 har helåret
  2023 som jämförelsetal. Byggd med spårets egna funktioner får extern EMEA 31 kvartal 2019Q1–2026Q3, utan brott.
  Det enda som förloras är att 2023Q4:s första version kommer 2025-02-18 i stället för 2024-02-23.
- Den interna andelen har vuxit kraftigt. EMEA: 11,0 av 217,7 (5 %) 2020Q1, 279,0 av 823,7 (34 %) 2026Q3. En del av
  tillväxten i `rev_vrt_emea` är alltså leveranser till andra regioner.
- Dokumentet säger "Asia Pacific har störst intern försäljning". Det gällde 2020Q1–2021Q4. Från 2022Q1 är EMEA
  störst (2026Q3: EMEA 279,0, Asia Pacific 228,8, Americas 10,2).
- Valet av brutto går att försvara: segmentnotens tabell är "Sales" med en rad "Eliminations" (10-Q
  0001628280-21-015172). MD&A redovisar "Net sales" per segment. Dokumentets "troligen Net Sales" som Vertivs
  huvudsiffra stämmer alltså bara för MD&A.

## 3. RPO som balanser – OK

- Alla 128 rader har balansdag på kalenderkvartalets sista dag. Perioden är balansdagens kvartal och `known_from`
  inlämningsdatumet (minst 22 dagar efter balansdagen).
- GE Vernova: utrustning + tjänster = total i alla 11 kvartal (±1 MUSD avrundning). Kontexterna har exakt
  `ProductOrServiceAxis`.
- Eaton: utan dimension 2020Q3–2024Q1. Från 10-Q 2024-08-01 har beloppet bara startdatumaxeln (en hink, start dagen
  efter balansdagen) och procentandelen för 12 månader. Texten bekräftar att hinken är totalen: "total backlog at
  June 30, 2024 was approximately $ 15.2 billion. At June 30, 2024, approximately 72 % of this backlog is targeted
  for delivery ... in the next twelve months" (10-Q 0001551182-24-000035). Samma för 2020Q3 (5,4) och 2022Q4 (11,4).
- Vertiv: de taggade beloppen är 4–115 MUSD per hink med flera hinkar per balansdag, och texten säger "noncurrent
  deferred revenue". BLOCKED i XBRL är rätt. Ingen `rpo_vrt` finns.
- Quanta: RPO, inte "backlog" (10-K 2020-02-28: RPO 5,30 mdr, backlog 15,00 mdr USD per 2019-12-31).

## 4. Capex för datacenterbolagen – anmärkning

**Equinix.** Raden "Purchases of other property, plant and equipment" är konsekvent 2014–2026, och köp av fastigheter
står på en egen rad hela tiden ("Purchase of real estate", senare "Real estate acquisitions"). Bolagsförvärv står
också för sig.

**R18-2. Equinix gamla tagg förkastas på en rad som inte hör till måttet (should_fix).** `PaymentsToAcquire
PropertyPlantAndEquipment` är samma rad i alla 10-Q 2010–2014, i 10-Q 2016-11-04 och parallellt i 10-Q 2017–2018.
Raden heter i 10-Q 2014-05-02 "Purchases of property, plant and equipment" (105 907), med "Purchase of real estate"
(16 791) separat. I 10-Q 2015 heter samma siffra "Purchases of other property, plant and equipment". 10-Q
2012-11-06 har också fastighetsköpen separat. De två taggarna är identiska i alla 18 överlappande perioder ur 10-Q.
Den enda avvikelsen är helåret 2010 i 10-K 0001193125-11-047157 (2011-02-25), där den gamla taggen är raden
"Purchase of Amsterdam IBX property" (14 861). Följder:
- `capex_eqix` börjar 2014Q1 i stället för 2009Q3.
- 2014Q1–Q4 får sin första version 2015-05-01 till 2015-10-30, alltså ett år för sent. 2016Q3 och 2016Q4 dateras
  2017-11-03 i stället för 2016-11-04 och 2017-02-27, eftersom 10-Q 2016-11-04 använde den gamla taggen.
- Dokumentet säger att raden "taggades ... i inlämningarna 2012–2013" och att taggen "avviker i en av 19
  överlappande perioder". Avvikelsen gäller 2010, och den gäller en annan rad. Förseningarna står inte i
  dokumentet.

Simulerad rättning (den gamla taggen som andra tagg, bara fakta ur 10-Q): 69 kvartal från 2009Q3, inga
revideringar, inga negativa värden. Värdena från 2014 ändras inte, bara dateringen. En naiv skarv med 10-K-faktan
skulle ge 2010Q4 = 14,861 − 436,046 = −421,2 (testet `test_eqix_capex_never_differences_the_amsterdam_purchase`
spärrar det).

**Digital Realty.** "Improvements to investments in real estate" (`PaymentsToDevelopRealEstateAssets`). Förvärv
("Acquisitions of real estate", bolagsförvärv) och intresseföretag står på egna rader 2010–2015 (10-K 2013-02-28 och
2015-03-02, 10-Q 2014-11-07), och 2026 enligt spårets kontroll. Raden hette "Improvements to and advances for
investments in real estate" 2011–2014. Värdena räknades inte om vid bytet:
9M 2014 är 644 637 både i 10-Q 2014-11-07 och som jämförelsetal i 10-Q 2015-11-06, och helåret 2013 är 1 189 510 i
alla senare 10-K (R18-8, anmärkning). Paritet med companyfacts: bekräftad. Skillnaden är tre rader i `rev_dlr`, och
orsaken är `defnref.xml` (R18-4). companyfacts saknar fortfarande 10-Q 2026-07-31 och 2026-10-30 (hämtat i dag).

**R18-4. `sec_segment.instance_name` väljer `defnref.xml` (should_fix, gemensam kod).** Bekräftat i fyra
DLR-inlämningar (10-Q/A 2010-08-12, 10-Q 2010-11-09, 10-K/A 2011-03-25, 10-Q 2011-05-09) och sju Microsoft-
inlämningar (10-Q 2009-10-23 till 10-Q 2011-04-28). Namnet är kortast, så det sorteras först. Följd här:
`rev_dlr` 2010Q3 dateras 2011-11-07 fast 10-Q 2010-11-09 har värdet (237 486), och 2011Q1 dateras 2012-05-07.
Serierna börjar 2010Q2 i stället för tidigare. Konservativt, men felet gäller alla serier som läser instanser
2009–2011.

## 5. Handkontroller – OK

Senaste version mot bolagets egen rad i huvuddokumentet på www.sec.gov. Spårets egna sju kontroller upprepades inte.

| Bolag och kvartal | Inlämning (accession) | Serie och värde | Rad i dokumentet | Dom |
|---|---|---|---|---|
| VRT 2021Q2 | 10-Q 0001628280-21-015172 (2021-08-02), 10-Q 0001628280-21-008627 | `rev_vrt` 1 260,3, `capex_vrt` 13,6, `rev_vrt_apac` 416,3 | "Net sales" 1 260,3; "Capital expenditures" 6M 30,4 − 3M 16,8; segmentnoten "Sales" Asia Pacific 416,3, intern 18,3, "Eliminations" −34,4 | OK |
| GEV 2023Q4 | 10-K 0001996810-25-000011 (2025-02-06), 10-Q 0001996810-24-000083 | `rev_gev` 10 045, `capex_gev` 280, `known_from` 2025-02-06 | "Total revenues" 33 239 − 9M 23 194; "Additions to property, plant, and equipment and internal-use software" 744 − 464 | OK, bolagets egna inlämningar |
| GEV 2024Q2 | 10-Q 0001996810-24-000067 (2024-07-24), 10-Q 0001996810-24-000008 | `rev_gev` 8 204, Power 4 455, Wind 2 062, Electrification 1 790, `capex_gev` 157, `rpo_gev` 115 476 | "Total revenues" 8 204; segment 4 455, 2 062, 1 790; additions 6M 374 − 3M 217; "Total RPO $ 115,476" | OK |
| ETN 2013Q1 | 10-Q 0001551182-13-000011 (2013-05-03) | `rev_etn` 5 310, `capex_etn` 122 | "Net sales" 5 310; "Capital expenditures for property, plant and equipment" (122) | OK, första kvartalet efter Cooper |
| ETN 2020Q2 | 10-Q 0001551182-20-000167 (2020-07-29) | `rev_etn_electrical_americas` 1 490 (första version 2021-08-03) | Electrical Americas 439 + 1 051 = 1 490 | Värdet OK, dateringen ett år för sen (R18-1) |
| ETN RPO 2020Q3, 2022Q4, 2024Q2 | 10-Q 0001551182-20-000190, 10-K 0001551182-23-000004, 10-Q 0001551182-24-000035 | `rpo_etn` 5 400, 11 400, 15 200 | "total backlog ... approximately $ 5.4 / 11.4 / 15.2 billion" | OK |
| PWR 2012Q4 | 10-K 0001193125-13-087221 (2013-03-01), 10-Q 0001193125-12-457556, 10-Q 0001193125-13-435250 | `rev_pwr` 1 293,2 (2013-03-01), sedan 1 673,3 (2014-03-03) | FY 5 920 269 − 9M 4 627 074 (gammal bas) respektive − 4 246 927 (ny bas). Skillnaden 380 147 är avvecklad verksamhet 9M 2012 | Mekanismen bekräftad (R18-5) |
| PWR 2013Q2 | 10-Q 0001193125-13-328613 (2013-08-09), 10-Q 0001193125-14-303240 (2014-08-08) | `capex_pwr` 81,7, sedan 104,5 | "Additions of property and equipment" Q2 2013 (81 743), som jämförelsetal (104 529) | OK, bolagets egen omräkning |
| PWR 2019Q4, 2021Q3 | 10-K 0001050915-20-000020, 10-Q 0001050915-21-000114 | `rpo_pwr` 5 300 och 4 370, `rev_pwr` 3 353,3, `capex_pwr` 74,6 | RPO "$5.30 billion", "$4.37 billion"; "Revenues" 3 353 278; "Capital expenditures" (74 612) | OK |
| EQIX 2025Q1 | 10-Q 0001628280-25-021086 (2025-04-30) | `rev_eqix` 2025Q1 2 225, 2023Q1 1 998,2 | "Revenues" 2 225 och 2 127, ingen kolumn för 2023 | OK, regeln för feldaterade fakta stämmer |
| EQIX 2014Q1, 2016Q3, 2020Q4 | 10-Q 0001193125-14-179863, 10-Q 0001628280-16-020845, 10-K 0001628280-21-002563, 10-Q 0001628280-20-015158 | `capex_eqix` 105,9 (första version 2015-05-01), 279,5 (2017-11-03), 834,3; `rpo_eqix` 8 400 | 105 907; 9M 727 044 − 6M 447 567; FY 2 282 504 − 9M 1 448 174; "approximately $ 8.4 billion" | Värdena OK, 2014Q1 och 2016Q3 dateras ett år för sent (R18-2) |
| DLR 2026Q2 | 10-Q 0001104659-26-089296 (2026-07-31), 10-Q 0001104659-26-054255 | `rev_dlr` 1 924,0, `capex_dlr` 914,2 | "Total operating revenues" 1 924 040; "Improvements to investments in real estate" 6M 1 784 229 − 3M 870 038 | OK, saknas i companyfacts |
| DLR 2010Q3, 2013Q3 | 10-Q 0001193125-10-254366 (2010-11-09), 10-Q 0001193125-13-438489 | `rev_dlr` 237,5 (första version 2011-11-07), `capex_dlr` 95,0, `rev_dlr` 2013Q3 379,5 | 237 486; 9M 248 737 − 6M 153 701; 379 456 | Värdena OK, 2010Q3 dateras ett år för sent (R18-4) |

Övrigt kontrollerat: Quantas avvecklade verksamhet 2012 är "substantially all of its domestic telecommunications
infrastructure services operations", såld 2012-12-03 (10-Q 2013-11-08). Spårets förbehåll "vilka verksamheter är
inte kontrollerat" kan ersättas med det.

## 6. Grenar, licens och klass – OK

- VRT, GEV, ETN och PWR i G7 (fysiska flaskhalsar) med alla mått. EQIX och DLR: intäkter och RPO i G4, capex i G5,
  som `rev_crwv`, `rpo_crwv` och `capex_crwv`. Rimligt och dokumenterat.
- Alla 27: `license` = `series.sec.LICENSE`, klass `ja` med regeln `sec`, `publish=True`, `catalog.validate` tom.
  Inga värden kommer ur text. Licensen stöder flaggan.
- Inga kärnserier, och index och tillståndsregler är orörda.

## 7. Förbehåll i dokumentet – anmärkning

Rätt och tillräckligt: mest annat än AI, RPO är inte orderingång, förvärv ger nivåskiften, korta serier och att
companyfacts kan släpa. Fel eller ofullständigt:
- "2020 års 10-Q har inga kvartalsvisa jämförelsetal för 2019" (R18-1).
- "Raden taggades då `PaymentsToAcquirePropertyPlantAndEquipment` i inlämningarna 2012–2013" och "avviker i en av 19
  överlappande perioder" (R18-2). Förseningarna för 2014 och 2016Q3–Q4 saknas.
- "Asia Pacific har störst intern försäljning" och täckningsskälet för brutto (R18-3).
- Aktualitetsgränsen för Vertiv (72 dagar) kommer från GS Acquisition Holdings 10-K 2019-03-13 och 2020-03-12 (SPAC-
  bolaget före sammanslagningen). Vertivs egna inlämningar har högst 60 dagar. Gränsen blir lösare än nödvändigt,
  men inte fel (R18-7).
- Avsnittet om kvartal med sen första version nämner inte Eatons segment 2020 eller Equinix capex 2014 och 2016.
- Radetiketterna för äldre år saknas: DLR "Improvements to and advances for investments in real estate"
  (2011–2014), Quanta "Additions of property and equipment" (2013–2014) (R18-8).
- Registret säger att pariteten för DLR kontrolleras "i bygget". Den kontrollerades en gång för hand, och resultatet
  står i tillägget. Det finns ingen kod eller test för den (R18-10).

## Rättningar

| # | Grad | Var | Rättning |
|---|---|---|---|
| R18-1 | should_fix | `sec_stack_kraft.py` (`SEG_LINES`, Eaton), registret, källdokumentet | Lägg till `ElectricalAmericasMember` och `ElectricalGlobalMember` (utan markör och med `OperatingSegmentsMember`) som alternativ. Daterat registertillägg: namnbyte i 10-K 2021-02-24, värdena identiska i överlappet (2020Q1 1 788 och 1 144). Rätta registrets skäl för startdatumet (10-K för 2012 använde `ElectricalAmericasMember`) och dokumentets påstående. Avgör samtidigt R18-9. Det strikta xfail-testet `test_etn_2020_10q_segment_names_are_read` slår om när det är rättat |
| R18-2 | should_fix | `sec_stack_kraft.py` (`COMPANIES["eqix"]`), registret, källdokumentet | Använd `PaymentsToAcquirePropertyPlantAndEquipment` som andra tagg för capex, bara fakta ur 10-Q. Skälet i ett daterat tillägg: den enda avvikande överlappningen är en annan rad i ett 10-K (Amsterdam IBX, 14 861), och raden i 10-Q är densamma i alla 18 överlappningar. Rätta dokumentet. Xfail-testet `test_eqix_capex_first_version_from_the_10q_that_reports_it` slår om. Det passerande testet mot den naiva skarven ska fortsätta passera |
| R18-3 | should_fix | källdokumentet, ägarbeslut | Rätta meningen om Asia Pacific och täckningsskälet. Rekommendation: lägg till Vertivs externa segmentförsäljning som egna nycklar (`rev_vrt_*_net`, medlemmen utan markör, 31 kvartal) och behåll bruttoserierna. Valet mellan dem är ägarens |
| R18-4 | should_fix | `sources/sec_segment.py` `instance_name` (gemensam kod, eget spår) | Uteslut `defnref.xml` ur kandidaterna (och helst alla filer som inte är instanser). Hämta om och jämför de serier som läser instanser 2009–2011: DLR, Microsofts avskrivningar (`dep_msft`, P1:s "annan tagg" 2009-10–2011-04 kan vara detta fel) och andra. Xfail-testet `test_instance_name_skips_defnref` slår om |
| R18-5 | note | källdokumentet | Ersätt "troligen" om Quanta 2012Q4 med den kontrollerade förklaringen (telekomverksamheten, 380 147 tusen USD 9M 2012). Första versionen är blandad bas, en känd begränsning i `sec.py` (`docs/kallor/sec.md`) |
| R18-6 | note | – | GE Vernova Power räknas om +0,5–0,6 % av samma omorganisation. Det blir versioner enligt regeln, och senaste versionen blandar baser 2025Q4 tills 10-K för 2026 kommer. Inget att rätta |
| R18-7 | note | källdokumentet | Skriv att Vertivs gräns kommer från SPAC-bolagets 10-K |
| R18-8 | note | källdokumentet | Lägg till de äldre radetiketterna för DLR och Quanta |
| R18-9 | note | registret (vid R18-1) | 550-dagarsregelns premiss ("en 10-Q redovisar perioden och samma period året före") gäller inte omräknad historik efter en ny segmentindelning. Eatons 10-Q 2020-04-30 har 2018 års kvartal (578 dagar). I dag påverkas inget. Avgör vid R18-1 om regeln ska gälla bara odimensionerade flöden, eller om de tre kvartalen får falla bort |
| R18-10 | note | registret eller koden | Skriv att DLR-pariteten är en engångskontroll, eller lägg den i koden som en kontroll som körs vid hämtning |

## Tester

`tests/test_r18_kraft_datacenter.py` (fixturer, inget nät):
- 550-dagarsregeln har marginal över de jämförelsetal som läses i dag och tar bort den feldaterade faktan (passerar)
- GE Vernova: bara bolagets egna 10-Q och 10-K, 8-K används inte, 2023Q4 = helår − 9M daterat 2025-02-06 (passerar)
- GE Vernova 2026: Electrification −2,08 % är ett brott, Power +0,59 % inte (passerar)
- Digital Realty: partnerskapets kontexter läses inte (passerar)
- Eaton: namnen från 2021 läses (passerar); 2020 års namn läses (strikt xfail, R18-1)
- Equinix: ingen skarv mot Amsterdam-raden, inga negativa kvartal (passerar); första versionen ur den 10-Q som
  redovisar kvartalet (strikt xfail, R18-2)
- `instance_name` för senare inlämningar (passerar); `defnref.xml` väljs inte (strikt xfail, R18-4)
- tre påståenden i källdokumentet (strikt xfail, R18-1–R18-3)

Riktade tester: `tests/test_r18_kraft_datacenter.py tests/test_sec_stack_kraft.py` 21 passerade, 6 xfail.

Hela sviten (en gång, 14 min): 2 187 passerade, 2 fel, 1 överhoppad, 8 xfail (2 från basen och 6 här). Båda felen
kommer från miljön. `test_site_bundle.py::test_committed_fixtures_are_the_current_synthetic_bundle` är det kända
felet (fixturerna bär sha256 för `docs/mattregister.md`). `test_data_quality.py::test_data_quality` failar på
`series_in_catalog`: den delade bastabellen fick serien `us_gdp_contrib_final_sales_computers` från ett annat spår
13:46 UTC, mitt under körningen, och den finns inte i den här grenens katalog. S2:s körning hade 2 181 passerade,
och här tillkommer 7 passerande tester.

## Vad som inte kunde verifieras

- Om något räknades lokalt före registerposten. Git och filtiderna visar bara att instanserna hämtades före och att
  värdetabellen skrevs efter.
- GE Vernovas `OperatingSegmentsMember` 2024 ("avviker upp till 5 %") och Equinix segmentcapex ("42 av 52") räknades
  inte om. Ingen av dem används.
- Att Eatons omorganisation 2026 inte rör de elektriska segmenten bekräftas bara av att inga kvartal reviderats.
  Texten lästes inte.
- Vilka andra serier än DLR och Microsoft som påverkas av R18-4.
