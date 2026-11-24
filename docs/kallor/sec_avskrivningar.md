# Källa: avskrivningar och anläggningstillgångar ur SEC XBRL

Spår P1, körning 13. Byggt 2026-11-24 och kontrollerat mot bolagens inlämningar. Kod:
`src/ai_tracker/series/sec_avskrivningar.py` (katalogposter) och `src/ai_tracker/sources/sec_custom.py` (egna taggar ur
instanser och summor ur samma inlämning). Kvartalslogik och versioner: `sources/sec.py` och `sources/sec_instant.py`.
Tester: `tests/test_sec_avskrivningar.py` (syntetiska fixturer, inget nät). Taggvalen är förregistrerade i
`docs/mattregister.md` (2026-11-24, P1), i en commit före den här beräkningen. Här finns ingen trendanalys.

Syftet är att följa pengarna från capex in i resultaträkningen. Avskrivningarna är där capex 2024–2026 hamnar
2026–2031, och nettot av anläggningstillgångarna är kapitalbasen för ett avkastningskrav. Serierna är underlag för
intäktskravet (P2b) och prognosmålet N7 (P3). De är katalogserier, inte kärnserier.

## Åtkomst och licens

- companyfacts (`data.sec.gov/api/xbrl/companyfacts/`), som för de andra SEC-serierna. Microsofts kassaflödesrad och
  Alphabets balansrad för 2020Q1 har egna taggar, som companyfacts saknar. De läses ur varje inlämnings XBRL-instans
  (`www.sec.gov/Archives`, samma nedladdning och rå-cache som `sec_segment`). AWS-segmentet läses också ur instanserna.
- Licens som för övriga SEC-serier (sec.gov/privacy, kontrollerad 2026-11-23): offentlig information, får spridas med
  SEC som källa. Därför `publish=True`. Bara siffror publiceras.
- CIK: Microsoft 789019, Alphabet 1652044 (och Google Inc. 1288776 för balanserna före 2015), Amazon 1018724, Meta
  1326801, Oracle 1341439, CoreWeave 1769628.

## Serier (alla kvartal, MUSD, gren G5, release-daterade)

Hämtning 2026-11-24. "Rev." är antalet kvartal med mer än en version.

| Nyckel | Innehåll | Kvartal | Från–till | Rader | Rev. |
|---|---|---|---|---|---|
| `dep_msft` | Depreciation, amortization, and other (egen tagg) | 65 | 2010Q3–2026Q3 | 69 | 4 |
| `dep_ppe_msft` | Depreciation expense (not om anläggningstillgångar) | 9 | 2024Q3–2026Q3 | 9 | 0 |
| `ppe_net_msft` / `ppe_gross_msft` | netto / brutto | 70 / 70 | 2009Q2–2026Q3 | 70 / 70 | 0 |
| `dep_googl` = `dep_ppe_googl` | Depreciation of property and equipment | 15 | 2023Q1–2026Q3 | 15 | 0 |
| `ppe_net_googl` / `ppe_gross_googl` | netto / brutto | 70 / 66 | 2009Q2 / 2010Q2–2026Q3 | 70 / 66 | 0 |
| `dep_amzn` | D&A of property and equipment and capitalized content costs, operating lease assets, and other | 31 | 2019Q1–2026Q3 | 35 | 4 |
| `dep_ppe_amzn` | Depreciation and amortization expense (anläggningstillgångar) | 11 | 2024Q1–2026Q3 | 11 | 0 |
| `ppe_net_amzn` | netto | 70 | 2009Q2–2026Q3 | 70 | 0 |
| `dep_meta` | Depreciation and amortization | 61 | 2011Q3–2026Q3 | 63 | 2 |
| `dep_ppe_meta` | Depreciation expense | 31 | 2019Q1–2026Q3 | 31 | 0 |
| `ppe_net_meta` / `ppe_gross_meta` | netto / brutto | 58 / 58 | 2012Q2–2026Q3 | 58 / 58 | 0 |
| `dep_orcl` | Depreciation + Amortization of intangible assets | 73 | 2008Q3–2026Q3 | 73 | 0 |
| `dep_ppe_orcl` | Depreciation | 73 | 2008Q3–2026Q3 | 73 | 0 |
| `ppe_net_orcl` | netto | 70 | 2009Q2–2026Q3 | 70 | 0 |
| `dep_crwv` | Depreciation and amortization | 11 | 2024Q1–2026Q3 | 11 | 0 |
| `dep_ppe_crwv` | Depreciation | 11 | 2024Q1–2026Q3 | 11 | 0 |
| `ppe_net_crwv` / `ppe_gross_crwv` | netto / brutto | 8 / 8 | 2024Q4–2026Q3 | 8 / 8 | 0 |
| `dep_hyp4` | summa MSFT+GOOGL+AMZN+META av `dep_*` | 15 | 2023Q1–2026Q3 | 19 | 4 |
| `dep_ppe_hyp4` | summa av `dep_ppe_*` | 9 | 2024Q3–2026Q3 | 9 | 0 |
| `ppe_net_hyp4` | summa av `ppe_net_*` | 58 | 2012Q2–2026Q3 | 58 | 0 |
| `dep_aws` | AWS-segmentets avskrivningar | 11 | 2024Q1–2026Q3 | 11 | 0 |

26 serier och 1 061 rader. Datatesterna (`python -m ai_tracker.warehouse`) är gröna på spårets vy, och ingen av
serierna är för gammal.

Finns inte: `ppe_gross_amzn`, `ppe_gross_orcl` och därmed `ppe_gross_hyp4`. Amazon och Oracle taggar bruttot och de
ackumulerade avskrivningarna bara vid räkenskapsårets slut (balansräkningen visar bara netto).

## Taggar per bolag

Raden i kassaflödesanalysen kontrollerades i den renderade kassaflödesanalysen (R-sidorna) i ett urval 10-K, och
etiketten nedan är bolagets egen.

| Bolag | `dep_<co>` | `dep_ppe_<co>` | Kommentar |
|---|---|---|---|
| MSFT | `msft:DepreciationAmortizationAndOther` ur instansen, i alla 10-Q och 10-K från 2011-07 | `Depreciation`, per kvartal i 10-Q från FY2025, helår sedan 2008 | Inlämningarna 2009-10 till 2011-04 använder en annan tagg. Kvartal från 2010Q3 kommer från jämförelsetal |
| GOOGL | `Depreciation`, perioder från 2021 | samma | Raden heter "Depreciation of property and equipment" från 10-K för 2023, som räknade om 2021–2022 utan nedskrivningar. Tidigare egna taggar (`goog:DepreciationAndImpairmentOnDispositionOfPropertyAndEquipment` m.fl., 2014–2022) har en annan definition och skarvas inte. Amortering på immateriella ligger i "Other" |
| AMZN | `DepreciationDepletionAndAmortization`, perioder från 2019 | `Depreciation` | Raden fick operationella leasingtillgångar 2019 (ASC 842, utan omräkning). Före 2017 låg raden i `DepreciationAndAmortization`, och i 10-K 2011–2017 användes `DepreciationDepletionAndAmortization` också för en annan siffra (helåren 2008–2014 avviker 2–32 % från kassaflödesraden). Serien börjar 2019 |
| META | `DepreciationDepletionAndAmortization` | `Depreciation`, per kvartal från 2019 | samma rad och tagg hela perioden |
| ORCL | `Depreciation` + `AmortizationOfIntangibleAssets` | `Depreciation` | två rader i kassaflödesanalysen. Summan görs bara när båda finns i samma inlämning |
| CRWV | `DepreciationDepletionAndAmortization` | `Depreciation` | samma tagg hela perioden |

**Balanser.** Netto: `PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization`
och sedan `PropertyPlantAndEquipmentNet`. De är identiska i alla överlapp (GOOGL 7 datum, AMZN 4, META 1, CRWV 8).
Brutto = netto + ackumulerade avskrivningar ur samma inlämning och samma taggfamilj. Bruttotaggarna används inte,
eftersom de ibland står för en delsumma: Alphabets 10-K för 2024 taggar 166,7 miljarder som
`PropertyPlantAndEquipmentGross` för 2023-12-31, mot 201,8 i alla andra inlämningar. Alphabets 10-Q för 2020Q1
(0001652044-20-000021) taggar balansen med egna taggar (`goog:PropertyPlantandEquipmentandFinanceLeaseRightofUseAsset...`),
som läses ur instansen. Utan den skulle Alphabets balanser börja 2020Q2. Före 2015 kommer balanserna från Google Inc.

**AWS.** Segmentets avskrivningar taggas som `Depreciation` med `StatementBusinessSegmentsAxis` =
`AmazonWebServicesSegmentMember` (2015–2016 som `DepreciationDepletionAndAmortization`). Värdet finns i alla 10-K som
helår, och per kvartal i 10-Q från 2025-05-02 (ASU 2023-07), med 2024 som jämförelse. Serien börjar därför 2024Q1.
Kvartalen 2024 blir kända först med jämförelsetalen 2025.

## Finansiell leasing i anläggningstillgångarna

I alla sex bolag ingår nyttjanderätter under finansiell leasing i nettot.

| Bolag | Belägg |
|---|---|
| MSFT | Leasingnoten anger finansiell leasing som "Property and equipment, at cost" och "Accumulated depreciation" (10-Q 0001193125-26-436133: 89 779 brutto, 72 625 netto, av totalt 474 052 och 346 844) |
| GOOGL | Balansraden "Property and equipment, net" taggas från 2019 med taggen för anläggningstillgångar inklusive finansiell leasing |
| AMZN | `FinanceLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList` = `PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization` (10-Q 0001018724-26-000040) |
| META | Balansraden taggas från 2019 med taggen inklusive finansiell leasing |
| ORCL | `FinanceLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList` = `PropertyPlantAndEquipmentNet` (10-K 0001193125-26-277521) |
| CRWV | Leasingnoten anger finansiell leasing som "Property and equipment" (10-Q 0001769628-26-000465: 944 brutto, 859 netto) |

Före ASC 842 (2019) låg kapitalleasing (capital leases) i anläggningstillgångarna hos de bolag som hade sådana.
Operationell leasing (hyrda datacenter) ingår aldrig i anläggningstillgångarna, men Amazons `dep_amzn` innehåller
avskrivningen på operationella leasingtillgångar från 2019.

## Omräkningar och definitionsbrott

Omräkningar är versioner med regeln om konsekvent bas i `sec.py`. Omräkningar på mer än 2 % deklareras per serie
(`breaks`), och en ny odeklarerad omräkning stoppar hämtningen.

- **MSFT, deklarerad 2026-01-28.** Från 10-Q:n för Q2 FY2026 flyttade Microsoft belopp ur "Depreciation, amortization,
  and other" till "Net recognized losses (gains) on investments and derivatives". 10-K för FY2026 räknade om helår
  FY2025 (34 153 till 29 433) och FY2024 (22 287 till 20 958), och investeringsraden för FY2025 gick från 609 till 5 329.
  Kvartalen 2024Q4–2025Q3 räknades om med 11–38 % i senare 10-Q och 10-K, som nya versioner. **I den senaste versionen
  ligger kvartalen till och med 2024Q3 kvar på den gamla basen**, eftersom Microsoft inte räknade om dem. Beloppen
  passar med förluster på investeringar (troligen kapitalandelar), men vilka poster som flyttades är inte verifierat i
  texten. `dep_msft` är alltså ingen ren avskrivningsserie, särskilt inte FY2024–FY2026. Använd `dep_ppe_msft` där det
  går.
- **AMZN, deklarerad 2023-04-28.** 10-Q:n räknade om 2022Q1 med +2,4 %, och senare inlämningar räknade om 2022Q2–Q4.
  Helåret 2022 är oförändrat (41 921), så omräkningen fördelade om året mellan kvartalen.
- **META, deklarerad 2014-04-25.** 2013Q1 räknades om med −3,3 %, och 2013Q2 med +3,6 % i 10-Q:n 2014-07-24
  (jämförelsetal ett år senare, efter samma omklassificering).
- **CRWV:** rapporterade i tusental till 10-K för 2025 och i miljoner därefter. En senare version som bara avrundar
  till hela miljoner är ingen omräkning och tas bort (som i `neoclouds`, till exempel 2025Q2 559,481 och 560).
- Definitionsbrott utan omräkning (Amazon 2019, Alphabet 2023) hanteras genom att serien börjar vid den nya definitionen.

## Kontroll mot inlämningarna

Värden ur serien (senaste version) mot bolagets egna rader i den renderade rapporten (R-sidor på www.sec.gov).
Alla stämmer.

| Bolag och kvartal | Inlämning (accession) | Serie och värde | Rad i rapporten |
|---|---|---|---|
| MSFT 2026Q3 (Q1 FY2027) | 10-Q 0001193125-26-436133, 2026-10-28 | `dep_msft` 11 744, `dep_ppe_msft` 11 100, `ppe_net_msft` 346 844, `ppe_gross_msft` 474 052 | kassaflöde 3M 11 744; "Depreciation expense" 11,1 mdr; balans 346 844 netto efter 127 208 ackumulerat |
| MSFT 2026Q2 (Q4 FY2026) | 10-K 0001193125-26-323660 och 10-Q 0001193125-26-191507 | `dep_msft` 11 022, `dep_ppe_msft` 10 300, `ppe_net_msft` 313 076 | 38 534 − 27 512 (9M); 34,3 − 24,0 mdr; balans 313 076 |
| MSFT 2015Q4 (Q2 FY2016) | 10-Q 0001193125-16-441821 | `dep_msft` 1 544 | kassaflöde 3M 1 544 |
| AMZN 2026Q3 | 10-Q 0001018724-26-000040, 2026-10-30 | `dep_amzn` 20 949, `dep_ppe_amzn` 15 142, `dep_aws` 9 230, `ppe_net_amzn` 508 862 | kassaflöde 3M 20 949; segmentnoten 4 566 + 1 346 + 9 230 = 15 142; balans 508 862 |
| AMZN 2025Q4 | 10-K 0001018724-26-000004 och 10-Q ovan (9M 2025) | `dep_amzn` 19 471, `dep_ppe_amzn` 12 113, `dep_aws` 6 568, `ppe_net_amzn` 357 025 | 65 756 − 46 285; 41 860 − 29 747; 21 450 − 14 882; balans 357 025 |
| ORCL 2026Q3 (Q1 FY2027, jun–aug) | 10-Q 0001193125-26-389274, 2026-09-11 | `dep_orcl` 3 358, `dep_ppe_orcl` 3 156, `ppe_net_orcl` 127 845 | 3 156 + 202; balans 127 845 |
| ORCL 2026Q2 (Q4 FY2026, mar–maj) | 10-K 0001193125-26-277521 och 10-Q 0001193125-26-101045 | `dep_orcl` 2 847, `dep_ppe_orcl` 2 415, `ppe_net_orcl` 99 957 | (7 623 + 1 671) − (5 208 + 1 239); 7 623 − 5 208; balans 99 957 |
| CRWV 2026Q3 | 10-Q 0001769628-26-000465, 2026-11-12 | `dep_ppe_crwv` 1 900, `ppe_net_crwv` 56 778, `ppe_gross_crwv` 64 554 | "Depreciation" 1 900; 56 778 + 7 776 = 64 554 ("Total property and equipment") |
| GOOGL 2020Q1 | 10-Q 0001652044-20-000021 | `ppe_net_googl` 76 747, `ppe_gross_googl` 109 684 | balans 76 747 (egen tagg); not 109,7 mdr brutto |

Amazons `Depreciation` i 10-Q är summan av segmenten. I 10-K för 2025 är den lika med noten om anläggningstillgångar
(41 860, 32 067 och 30 225 för 2025, 2024 och 2023).

## Kalender och datering

- known_from är inlämningsdatumet för 10-Q eller 10-K. Varje inlämning är en version.
- MSFT (räkenskapsår till juni), GOOGL, AMZN, META och CRWV: räkenskapskvartalen är kalenderkvartal.
- ORCL: räkenskapsår till 31 maj. Kvartal sep–nov räknas som Q4 (mittpunktsregeln) och lämnas in cirka 10 december,
  före kalenderkvartalets slut. Därför `lag_days = -31` och aktualitetsgränsen 119 dagar, som `rev_orcl`.
  Balansen 30 november hamnar i samma kvartal som flödet.
- Alphabets kvartal 2023 blir kända först med jämförelsetalen i 10-Q 2024 (till exempel 2023Q4 den 2024-10-30),
  eftersom 10-Q under 2023 använde den gamla taggen och definitionen. Det är sent men konservativt.
- Amazons och AWS kvartal 2024 blir kända med jämförelsetalen 2025 av samma skäl.

## Kända problem och förbehåll

- **Alla anläggningstillgångar, inte bara AI-servrar.** Mark, byggnader, kontor, lager, logistik (Amazon), nät och
  pågående byggen ingår. Pågående byggen skrivs inte av förrän de tas i bruk, så bruttot innehåller kapacitet som
  ännu inte skrivs av.
- **Nyttjandeperioden är ett redovisningsval.** Flera bolag har ändrat den för servrar sedan 2022, åt båda hållen. Det
  syns som nivåskiften i avskrivningarna, utan att capex har ändrats. Serierna justeras inte för det. Nyttjandeperioderna
  extraheras i spår P2.
- **Definitionerna skiljer sig mellan bolagen.** `dep_msft` innehåller "other", `dep_amzn` innehåller aktiverat innehåll
  och operationell leasing, `dep_orcl` och `dep_meta` innehåller amortering på immateriella tillgångar, och `dep_googl`
  är bara avskrivningar på anläggningstillgångar. `dep_hyp4` är alltså en summa av olika definitioner. För jämförbarhet
  finns `dep_ppe_*` och `dep_ppe_hyp4`, men bara från 2024Q3.
- **Avrundning.** Microsoft och CoreWeave taggar avskrivningen i noten avrundad till 0,1 miljard USD. `dep_ppe_crwv` kan
  därför ligga över `dep_crwv` (2026Q3: 1 900 mot 1 889), och Q4 = helår − 9M får ett avrundningsfel på upp till cirka
  100 MUSD.
- **Korta serier.** `dep_ppe_hyp4` har 9 kvartal och `dep_hyp4` 15. Långa serier per bolag: `dep_orcl` och `dep_ppe_orcl`
  (73), `dep_msft` (65, med basbrottet ovan) och `dep_meta` (61).
- **Möjliga tillägg, inte byggda:** stängda nycklar för de äldre definitionerna (Alphabet 2014–2022 med nedskrivningar,
  Amazon 2008–2018 före ASC 842), helårsserier för avskrivning på anläggningstillgångar (MSFT och AMZN sedan 2008 och
  2014), och AWS-segmentets nettotillgångar. De senare visas i Amazons segmentnot i 10-Q (313 009 per 2026-09-30) men
  taggas med en extra dimension, och de läses inte här.
