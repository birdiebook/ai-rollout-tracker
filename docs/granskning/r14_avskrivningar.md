# R14 – granskning av avskrivningar och anläggningstillgångar ur SEC XBRL (P1)

Granskningsspår R14, 2026-11-24, gren `auto14/r14-avskrivningar` (från `auto13/p1-avskrivningar`). Granskat: de 26
katalogserierna i G5 från spår P1 (`dep_*`, `dep_ppe_*`, `ppe_net_*`, `ppe_gross_*`, `dep_hyp4`, `dep_ppe_hyp4`,
`ppe_net_hyp4`, `dep_aws`), koden i `src/ai_tracker/series/sec_avskrivningar.py` och `src/ai_tracker/sources/sec_custom.py`,
testerna i `tests/test_sec_avskrivningar.py`, källdokumentet `docs/kallor/sec_avskrivningar.md`, registerposten
"P1: avskrivningar och anläggningstillgångar som katalogserier" och `git log -p main..auto13/p1-avskrivningar`.

Underlag:
- P1:s tabell (1 061 rader). Serierna byggdes om med grenens kod. Resultatet är identiskt rad för rad: 1 061 av 1 061,
  samma värde och samma `known_from`.
- Primärkällor på www.sec.gov: de renderade kassaflödesanalyserna, balansräkningarna och noterna (R-sidor) i 30
  inlämningar, EDGAR:s inlämningslistor (för inlämningsdatum) och companyfacts (för taggtäckning). Inga värdar var
  blockerade.

**Ingen analys av förlopp gjordes.** Tillväxttalen i punkt 3 räknades bara för att visa hur stort felet är.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering | **OK**. Listan över vad som setts stämmer med filtiderna i cachen |
| 2. Taggval och deklarerade omräkningar | **OK**, med en anmärkning: registret har två regler som pekar åt olika håll för en delvis omräkning |
| 3. `dep_msft` och omklassificeringen 2026 | **Fel.** 2024Q3 ligger kvar på gammal bas, fast Microsoft räknade om kvartalet genom sexmånaderstalet. Inget enskilt kvartal blandar baser |
| 4. `dep_amzn` från 2019, `dep_googl` från 2023 | **OK** |
| 5. Brutto, balansdagar och Oracle | **OK**. En liten anmärkning om Oracles aktualitetsgräns |
| 6. Datering, omräkningar och CoreWeave | **OK för data.** P1:s test av CoreWeave-filtret prövar inte filtret |
| 7. Handkontroller | 15 bolagskvartal i alla sex bolag. Alla stämmer, utom att MSFT 2024Q3 har fel bas |
| 8. `dep_hyp4` och `dep_ppe_hyp4` | **Anmärkning.** Katalognoten för `dep_hyp4` säger inte vilka definitioner som summeras |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** 24 av 26 serier är korrekta i alla versioner som kontrollerades. `dep_msft`
och därmed `dep_hyp4` har ett fel (R-1): ett kvartal står på fel bas i den senaste versionen. Felet är litet i nivå
(2,3 % på helåret FY2025) men stort i takt (årstakten 2025Q3 för `dep_msft` blir +10 % i stället för +21 %). R-1 ska
rättas innan `dep_msft` eller `dep_hyp4` används för takt, alltså innan P2b:s förändring i takt och P3:s träningsdata
läses som slutliga. Övriga rättningar gäller dokumentation och tester.

## 1. Förregistrering – OK

Ordningen enligt git och den delade rå-cachen (alla 2026-11-24, UTC):

| Tid | Commit | Innehåll |
|---|---|---|
| 20:10–20:15 | – | R-sidor: kassaflödesanalyser i 10-K (Microsoft 7, Alphabet och Google 10, Meta 3, Amazon 4, Oracle 1, CoreWeave 1) och Alphabets balansräkning i 10-Q för 2020Q1 |
| 20:16–20:19 | – | XBRL-instanser: alla Microsofts 71 inlämningar och Amazons inlämningar (AWS-segmentet) |
| 20:21 | `8e9e452` | Registerposten och `sec_custom.py`. Inga serier |
| 20:33 | `1389c86` | Seriekod, tester och källdokument |
| 20:35 | `d96e98d` | CoreWeave-filtret för avrundning |
| 20:43 | `0933c9a` | Syntetiska fixtures för webben |

- `git diff 8e9e452 HEAD -- docs/mattregister.md` är tom. Posten ändrades inte efter beräkningen.
- Registrets lista ("vad som setts") stämmer med filerna. Före posten hämtades bara helårssidor i 10-K och en
  balansräkning, och Microsofts instanser, som registret nämner ("MSFT-taggens täckning och storleken på
  omräkningarna").
- Begränsning: alla Microsofts instanser låg på disk före posten, så kvartalsvärden kunde ha räknats. Git visar inget
  sådant. Microsofts taggval är dessutom tvunget: companyfacts har ingen us-gaap-tagg för raden (punkt 2). Risken för
  ett val efter utfall är därför liten.
- Två ändringar efter första bygget står inte i registret: CoreWeave-filtret (`d96e98d`, tar bort en rad på
  0,5 MUSD, punkt 6) och att Alphabets taggar läses från 2021 (`first_start="2021-01-01"`). Registret säger "från
  2023Q1". Värdena blir desamma, eftersom 2021–2022 bara finns som helår med den nya taggen. Båda är anmärkningar.

## 2. Taggval och deklarerade omräkningar – OK, med en anmärkning

**Täckning (companyfacts, kontrollerad):**

| Bolag | Kontroll | Dom |
|---|---|---|
| MSFT | Ingen us-gaap-tagg för "Depreciation, amortization, and other". Bara den egna taggen i instanserna | Valet är tvunget |
| GOOGL | `Depreciation` finns först från 10-K 2024-01-31 | Stämmer |
| AMZN | `DepreciationDepletionAndAmortization` från 2011, `DepreciationAndAmortization` 2009–2017, `Depreciation` per kvartal i 10-Q först 2025 | Stämmer |
| META | `DepreciationDepletionAndAmortization` från 2012, `Depreciation` från 2013 och i 10-Q från 2019 | Stämmer |
| ORCL, CRWV | Båda raderna finns hela perioden | Stämmer |

- Nettotaggarna är identiska på alla datum där båda finns: GOOGL 7, AMZN 4, META 1 och CRWV 8 datum. Det stämmer med
  registret.
- Alphabets bruttotagg för 2023-12-31 är 166 667 i 10-K 2025-02-05 och 201 803 i alla andra inlämningar (−17 %).
  Att bruttot räknas som netto + ackumulerat är alltså motiverat.

**Deklarerade omräkningar (kontrollerade mot R-sidorna):**
- MSFT 2026-01-28: se punkt 3. Investeringsraden bekräftar flytten: FY2025 609 → 5 329 (+4 720 = 34 153 − 29 433) och
  FY2024 305 → 1 634 (+1 329 = 22 287 − 20 958).
- AMZN 2023-04-28: 2022Q1 8 978 → 9 193 (+2,4 %). Omräkningarna av 2022Q1–Q4 summerar till noll (+215, +122, +123,
  −460), så helåret 41 921 är oförändrat.
- META 2014-04-25: 2013Q1 241 → 233 och 2013Q2 222 → 230. Helåret 2013 (1 011) är oförändrat.

**Stoppregeln fungerar.** Ombygget passerar, så de funna omräkningarna är exakt de deklarerade i alla 26 serier.
Regeln är tvåsidig: en deklarerad omräkning som inte finns stoppar också (nytt test).

**Anmärkning A-2a: två regler för en delvis omräkning.** Registret säger "En serie har en definition. Om raden byter
innehåll och tidigare perioder inte räknas om, börjar serien vid den nya definitionen". Det säger också att en
deklarerad omräkning av en kassaflödesrad ger samma nyckel och att kvartal som inte räknats om ligger kvar på den
gamla basen. Microsofts rad bytte innehåll, och kvartalen i FY2024 och tidigare räknades inte om. P1 följde den andra
regeln, och det är tillåtet enligt registret och redovisat. Resultatet är ändå en serie med två definitioner, med
bytet vid 2024Q3/Q4. Registret bör säga vilken regel som gäller vid en delvis omräkning, och noten för `dep_msft` bör
ange det sista kvartalet på gammal bas.

**Anmärkning A-2b: brottdetektorn efter ett brott.** `definition_breaks` jämför efter ett brott bara värden som lämnats
in efter brottet. Därför flaggas inte omräkningen av 2025Q3 (−38 %, 2026-10-28) eller av helåret FY2024 (−6 %) för sig.
Det är rätt för en omklassificering som rullas ut över flera inlämningar. Men en ny omklassificering inom samma år
skulle inte heller flaggas, om den bara rör perioder som inte rapporterats igen sedan brottet. Det är `sec_segment`:s
regel och gäller inte bara P1.

## 3. `dep_msft` och omklassificeringen 2026 – fel (F-3a)

Microsofts kassaflödesanalys i 10-Q visar tre månader och hittills i år. Raden "Depreciation, amortization, and other"
för FY2025, i MUSD:

| Inlämning | 3M jul–sep 2024 (Q1) | 3M okt–dec 2024 (Q2) | 6M | 3M jan–mar 2025 (Q3) | 9M | Helår |
|---|---|---|---|---|---|---|
| 10-Q 2024-10-30 (0000950170-24-118967) | 7 383 | | | | | |
| 10-Q 2025-01-29 (0000950170-25-010491) | | 6 827 | 14 210 | | | |
| 10-Q 2025-04-30 (0000950170-25-061046) | | | | 8 740 | 22 950 | |
| 10-K 2025-07-30 (0000950170-25-100235) | | | | | | 34 153 |
| 10-Q 2026-01-28 (0001193125-26-027207) | visas inte | 5 667 | **12 383** | | | |
| 10-Q 2026-04-29 (0001193125-26-191507) | | | | 7 734 | **20 116** | |
| 10-K 2026-07-29 (0001193125-26-323660) | | | | | | **29 433** |

**Microsoft räknade om Q1 FY2025 (2024Q3), men bara genom summorna.** På den nya basen är kvartalet 12 383 − 5 667 =
6 716. Nio- och tolvmånaderstalen ger samma svar (20 116 − 5 667 − 7 734 = 6 715, och 29 433 − 5 667 − 7 734 − 9 317 =
6 715). Investeringsraden visar samma flytt: 6M 2 678 − Q2 2 136 = 542, mot −125 ursprungligen, alltså +667.

**Serien har 7 383 för 2024Q3 i alla versioner.** I `sec.py` vinner ett direkt tremånadersvärde över en differens, och
årets första kvartal räknas bara ur ett direkt värde. Därför används aldrig 6M − Q2. Följderna i den senaste
versionen:
- Fyrkvartalsfönstret FY2025 (2024Q3–2025Q2) blir 30 101 i stället för 29 433 (+2,3 %).
- Årstakten 2025Q3 för `dep_msft` blir +10,3 % (8 147 / 7 383) i stället för +21,3 % (8 147 / 6 716).
- `dep_hyp4` 2024Q3 blir 28 837 i stället för 28 170, och dess årstakt 2025Q3 +23,2 % i stället för +26,1 %.

**Samma mekanism daterar 2025Q3 för sent.** Den nya basen för 2025Q3 (17 345 − 9 198 = 8 147) gick att räkna
2026-01-28, men serien får värdet först 2026-10-28. Det är konservativt och inget läckage. Men i versionerna
2026-01-28 till 2026-10-27 står 2025Q3 på gammal bas (13 061) bredvid 2025Q4 på ny bas (9 198).

**Inget enskilt kvartal blandar baser.** Q4 = helår − 9M tar båda från samma bas i varje version: Q4 FY2025 är
34 153 − 22 950 = 11 203 och sedan 29 433 − 20 116 = 9 317. Helåret FY2024 räknades om (22 287 → 20 958), men inte
kvartalen, och omräkningen läggs inte på Q4 (6 380 kvar). Fönstret FY2026 är 38 534, samma som helåret. Allt detta
står i de nya testerna.

**Påståendet i källdokumentet och beslutsloggen är fel för 2024Q3.** "Kvartalen till och med 2024Q3 ligger kvar på den
gamla basen, eftersom Microsoft inte räknade om dem" stämmer bara för kvartalen i FY2024 (2023Q3–2024Q2). De går inte
att räkna om, eftersom bara helåret räknades om (−6,0 %). P2b har tagit över påståendet ("Effekten räknas inte om,
eftersom Microsoft inte har räknat om de kvartalen").

**Fyrkvartalsfönster i P2b och P3 (senaste versionen):**

| Fönstret slutar | I dag | Efter R-1 |
|---|---|---|
| till och med 2024Q3 | gammal bas | gammal bas (går inte att rätta) |
| 2024Q4–2025Q1 | blandat | blandat |
| 2025Q2 | blandat (2024Q3 gammal) | ny bas |
| från 2025Q3 | ny bas | ny bas |

P3 använder första versionen per kvartal. Den är gammal bas till och med 2025Q3 och ny från 2025Q4. P3 poängsätter
inte MSFT:s brottkvartal (F-B8), så blandningen finns i träningsdata men inte i utvärderade rader.

Allvarlighet: **must_fix**. Värdet i den senaste versionen följer inte seriens egen regel att omräkningar är versioner.
Strikt xfail-test: `test_msft_first_quarter_restated_through_ytd_is_a_new_vintage`.

## 4. `dep_amzn` från 2019 och `dep_googl` från 2023 – OK

- **Amazon.** I 10-Q 2018-04-27 (0001018724-18-000072) heter raden "Depreciation of property and equipment, including
  internal-use software and website development, and other amortization, including capitalized content costs". I 10-Q
  2019-04-26 (0001018724-19-000043) heter den "...capitalized content costs, operating lease assets, and other", och
  jämförelsetalet Q1 2018 är oförändrat (3 671). ASC 842 utan omräkning är alltså bekräftat, och starten 2019 är rätt.
  Påståendet att `DepreciationDepletionAndAmortization` i 10-K 2011–2017 också användes för en annan siffra
  kontrollerades inte. Det påverkar inte serien.
- **Alphabet.** I 10-K 2023-02-03 (0001652044-23-000016) heter raden "Depreciation and impairment of property and
  equipment", med egen tagg: 2022 15 287 och 2021 11 555. I 10-K 2024-01-31 (0001652044-24-000022) heter den
  "Depreciation of property and equipment" (`us-gaap:Depreciation`): 2022 13 475 och 2021 10 273. Sexmånaderstalet 2023
  är 6 339 i 10-Q 2023-07-26 och 5 459 i 10-Q 2024-07-24 (−14 %). Definitionsbytet är bekräftat, och att inte skarva är
  rätt. Att 2023 blir känt först 2024 är sent men konservativt.

## 5. Brutto, balansdagar och Oracle – OK

- `summed_instants` parar netto och ackumulerat per accession och datum. P1:s test och ett nytt test på balansnivå
  visar att värden ur olika inlämningar aldrig paras.
- Bruttot stämmer med bolagens egna summor: MSFT 2026Q2 431 767 = "Total, at cost", META 2025Q4 233 726 = "Property and
  equipment, gross", Alphabet 2020Q1 109 684 (egen tagg ur instansen).
- Balanser mappas till räkenskapskvartal med mittpunktsregeln. Oracles balans per 30 november får Q4, samma som flödet.
- **Oracle.** `lag_days = -31` passar: första versionen kommer 8–21 dagar före kalenderkvartalets slut sedan 2011.
  Aktualitetsgränsen 119 = −3 + 92 + 30 är kopierad från `neoclouds`. I P1:s egna data är det största avståndet +1 dag
  (10-K 2010-07-01, 2010Q2), och sedan 2012 högst −8. Gränsen fungerar, men noten "största observerade avstånd"
  stämmer inte exakt för P1:s data (anmärkning).
- Amazon och Oracle har ackumulerade avskrivningar bara vid årets slut (Amazon 10-K 2026-02-06: 177 073). Att
  `ppe_gross_amzn`, `ppe_gross_orcl` och `ppe_gross_hyp4` saknas är rätt.

## 6. Datering, omräkningar och CoreWeave – OK för data

- **known_from.** Alla 1 061 rader har `known_from` lika med ett inlämningsdatum för bolagets 10-Q eller 10-K enligt
  EDGAR. Det finns inga undantag. Bara Oracles 204 rader ligger före kalenderkvartalets slut, högst 21 dagar, vilket
  `lag_days = -31` tillåter. Datatesterna på spårets vy är gröna (bara Arena-prisserierna saknar data, ett känt
  miljöproblem).
- **Omräkningar är nya versioner.** Exempel: `dep_amzn` 2022Q1 (2022-04-29 och 2023-04-28) och `dep_msft` 2024Q4
  (2025-01-29 och 2026-01-28).
- **CoreWeave-filtret** gäller alla fyra CRWV-serier. I riktiga data tar det bort exakt en rad: `dep_crwv` 2025Q2, 560
  den 2026-08-12 efter 559,481. **P1:s test passerar också utan filtret** (A-6a). I testet flyttas sexmånaderstalet
  0,519 MUSD, mer än `sec.TOL`, så `sec.py` behåller det gamla värdet ändå. I verkligheten flyttas det mindre än TOL, och
  då räknas differensen mot det avrundade Q1-talet. Det nya testet prövar det fallet och visar att filtret behövs.
- **Avrundning.** Microsoft och CoreWeave taggar avskrivningen i 0,1 miljard, vilket står i dokumentet. Meta taggar
  `Depreciation` i 0,01 miljard (till exempel 3 330 och 18 000), vilket inte står där. Felet är högst cirka 10 MUSD per
  kvartal (anmärkning).
- **Amazon 2022Q4, tillfälligt.** Mellan 2023-10-27 och 2024-02-01 låg 2022Q1–Q3 på den nya fördelningen, medan Q4 var
  helår minus det gamla 9M-talet. Det följer `sec.py`:s konservativa regel. Summan för 2022 var då 42 381 i stället för
  41 921. Det rättades 2024-02-02 (anmärkning).

## 7. Handkontroller – 15 bolagskvartal

Värden ur R-sidorna på www.sec.gov mot serierna, i MUSD.

| # | Bolag och kvartal | Inlämning (accession) | Rad i rapporten | Serie | Dom |
|---|---|---|---|---|---|
| 1 | MSFT 2024Q3 (Q1 FY2025), omräknat | 10-Q 0000950170-24-118967; 10-Q 0001193125-26-027207 | 3M 7 383; omräknat 6M 12 383 − Q2 5 667 = 6 716 | `dep_msft` 7 383 i alla versioner | **Fel bas** (punkt 3) |
| 2 | MSFT 2024Q4, omräknat | 10-Q 0000950170-25-010491; 10-Q 0001193125-26-027207 | 6 827; 5 667 | 6 827 (2025-01-29), 5 667 (2026-01-28) | OK |
| 3 | MSFT 2025Q2 (Q4 FY2025), omräknat | 10-K 0000950170-25-100235, 10-Q 0000950170-25-061046; 10-K 0001193125-26-323660, 10-Q 0001193125-26-191507 | 34 153 − 22 950 = 11 203; 29 433 − 20 116 = 9 317 | 11 203 (2025-07-30), 9 317 (2026-07-29) | OK |
| 4 | MSFT 2026Q2, balans och Q4 | 10-K 0001193125-26-323660; 10-Q 0001193125-26-191507 | netto 313 076, ackumulerat 118 691, "Total, at cost" 431 767; "Depreciation expense" 34,3 − 24,0 mdr | `ppe_net` 313 076, `ppe_gross` 431 767, `dep_ppe` 10 300 | OK |
| 5 | MSFT 2024Q3, balans | 10-Q 0000950170-24-118967 | 152 863 + 80 517 = 233 380 | `ppe_net` 152 863, `ppe_gross` 233 380 | OK |
| 6 | GOOGL 2025Q4 (Q4) | 10-K 0001652044-26-000018; 10-Q 0001652044-25-000091 | 21 136 − 15 096 = 6 040; netto 246 597, ackumulerat 98 485 | `dep` 6 040 (2026-02-05), `ppe_net` 246 597, `ppe_gross` 345 082 | OK |
| 7 | GOOGL 2023Q2 | 10-Q 0001652044-24-000079; 10-Q 0001652044-24-000053 | 5 459 − 2 635 = 2 824 | 2 824 (2024-07-24) | OK |
| 8 | GOOGL 2020Q1, balans (egen tagg) | 10-Q 0001652044-20-000021 | netto 76 747, brutto 109 684 | 76 747 och 109 684 (2020-04-29) | OK |
| 9 | AMZN 2022Q1, omräknat | 10-Q 0001018724-22-000013; 10-Q 0001018724-23-000008 | 8 978; 9 193 | 8 978 (2022-04-29), 9 193 (2023-04-28) | OK |
| 10 | AMZN 2026Q3 | 10-Q 0001018724-26-000040 | 3M 20 949; segmentnoten 15 142, varav AWS 9 230; netto 508 862 | `dep` 20 949, `dep_ppe` 15 142, `dep_aws` 9 230, `ppe_net` 508 862 | OK |
| 11 | AMZN 2025Q4 (Q4) | 10-K 0001018724-26-000004; 10-Q 0001018724-26-000040 | 41 860 − 29 747 = 12 113; AWS 21 450 − 14 882 = 6 568; segmentsumman = noten om anläggningstillgångar (41 860) | `dep_ppe` 12 113, `dep_aws` 6 568 (2026-02-06) | OK |
| 12 | META 2025Q4 (Q4) | 10-K 0001628280-26-003942; 10-Q 0001628280-25-047240 | 18 616 − 13 205 = 5 411; netto 176 400, brutto 233 726, ackumulerat 57 326 | `dep` 5 411, `ppe_net` 176 400, `ppe_gross` 233 726 (2026-01-29) | OK |
| 13 | META 2013Q1, omräknat | 10-Q 0001326801-13-000011; 10-Q 0001326801-14-000023 | 241; 233 | 241 (2013-05-02), 233 (2014-04-25) | OK |
| 14 | ORCL 2025Q4 (Q2 FY2026, sep–nov) | 10-Q 0001193125-25-315925; 10-Q 0001193125-25-200095 | (3 055 + 826) − (1 351 + 420) = 2 110; 3 055 − 1 351 = 1 704; netto 67 875 | `dep` 2 110, `dep_ppe` 1 704, `ppe_net` 67 875 (2025-12-11) | OK |
| 15 | CRWV 2025Q4 (Q4) | 10-K 0001769628-26-000104; 10-Q 0001769628-25-000062 | 2 454 (miljoner) − 1 633,457 (tusental) = 820,543; 30 557 + 3 384 = 33 941 | `dep` 820,543, `ppe_net` 30 557, `ppe_gross` 33 941 (2026-03-02) | OK |

Kontrollerna omfattar tre Q4 (helår − 9M), fyra omräknade kvartal och balanser i fem bolag. Alla datum i kolumnen
Serie är inlämningsdatum enligt EDGAR.

**Inte verifierat:**
- Vilka poster Microsoft flyttade ur "other". Bara beloppen är kontrollerade, via investeringsraden.
- Om avskrivningen på nyttjanderätter under finansiell leasing ingår i `dep_ppe_*` hos varje bolag. Microsofts
  amortering av sådana tillgångar var 5 403 MUSD FY2026, mot 34 300 i avskrivningar.
- Amazons användning av `DepreciationDepletionAndAmortization` i 10-K 2011–2017 (punkt 4).

## 8. `dep_hyp4` och `dep_ppe_hyp4` – anmärkning

**Står skillnaden i definitioner där `dep_hyp4` används?**

| Ställe | Står det? |
|---|---|
| Källdokumentet (`docs/kallor/sec_avskrivningar.md`) | Ja, tydligt |
| Katalogens etikett ("Avskrivningar enligt kassaflödesanalysen, MSFT+GOOGL+AMZN+META") | Nej, men etiketten är riktig |
| Katalogens not | Bara "Bolagens definitioner skiljer sig (se bolagsserierna)". Innehållet och Microsofts basbyte nämns inte |
| Registerposten | Nej |
| P2b (`REQ_NOTE`, `docs/resultat/intaktskrav.md`) och P3 (`docs/resultat/n7.md`) | Ja |

Serien har `publish=True`, så den publika sidan visar en summa utan innehållet (A-8a). Strikt xfail-test:
`test_dep_hyp4_note_names_the_definitions_it_sums`.

**Hur stor är skillnaden?** Delen av `dep_hyp4` som inte är avskrivning på anläggningstillgångar (`dep_hyp4` −
`dep_ppe_hyp4`) var 27 % 2024Q3, 20 % 2025Q3 och 14 % 2026Q3. Andelen faller, så `dep_hyp4` växer långsammare än
avskrivningen på den fysiska kapaciteten. P2b visar samma sak: takten 2026Q3 är +12,2 med `dep_hyp4` och +19,4 med
`dep_ppe_hyp4`.

**Är `dep_ppe_hyp4` bättre som underlag?** I definition ja: samma innehåll för alla fyra, bara avrundning skiljer
(och möjligen leasing, som inte är verifierat). I täckning nej: 9 kvartal (2024Q3–2026Q3), alltså sex
fyrkvartalsfönster från 2025Q2.
- För P2b: `dep_ppe_hyp4` är det bättre måttet för nivå och takt från 2025Q2. Valet av `dep_hyp4` är registrerat i
  P2b. Ett byte är en registerändring för P2b, inte för P1.
- För P3: `dep_ppe` är för kort för backtest hos MSFT (9), AMZN (11) och GOOGL (15). META (31) och ORCL (73) räcker.
  N7b på `dep_*` kan stå kvar med förbehållet, och N7b på `dep_ppe_meta` och `dep_ppe_orcl` kan redovisas som
  känslighet.

## Rättningar (för ett rättningsspår)

| # | Var | Rättning | Allvarlighet |
|---|---|---|---|
| R-1 | `sec.py` eller `sec_custom.py` (Microsofts rad) | Härled kvartal som bolaget räknat om genom summorna: i en inlämning med både hittills-i-år och tremånadersvärde ger YTD − 3M ett underförstått värde för den tidigare slutdagen, daterat till inlämningen. Då blir 2024Q3 6 716 och 2025Q3 8 147, båda från 2026-01-28. Kontrollera att inga nya brott > 2 % uppstår i andra serier. Det strikta xfail-testet `test_msft_first_quarter_restated_through_ytd_is_a_new_vintage` slår om när felet är rättat. Registrera regeln i `docs/mattregister.md` | must_fix |
| R-2 | `sec_avskrivningar.py` `_spec` för hyp4 | Skriv i noten för `dep_hyp4` vad som summeras: Microsofts rad med "other" (kvartal till och med 2024Q2 på gammal bas efter R-1), Amazons aktiverade innehåll och operationella leasingtillgångar, Metas amortering på immateriella tillgångar, och för Alphabet bara avskrivningar. Hänvisa till `dep_ppe_hyp4` för jämförbarhet. Testet `test_dep_hyp4_note_names_the_definitions_it_sums` slår om. Samma rad i registerposten | should_fix |
| R-3 | `docs/kallor/sec_avskrivningar.md`, `docs/beslutslogg.md` (P1), P2b:s `intaktskrav.md` | Rätta "kvartalen till och med 2024Q3 ... eftersom Microsoft inte räknade om dem": 2024Q3 räknades om genom summorna (6 716 mot 7 383). Bara FY2024:s kvartal (till och med 2024Q2) går inte att räkna om | should_fix |
| R-4 | `tests/test_sec_avskrivningar.py` | Byt ut CoreWeave-testet mot ett som behöver filtret (nytt test i `tests/test_r14_avskrivningar.py`) eller ta bort det gamla | should_fix (gjort i denna granskning) |
| R-5 | `docs/mattregister.md` | Säg vilken regel som gäller vid en delvis omräkning (en definition per serie eller samma nyckel), och ange sista kvartal på gammal bas i noten för `dep_msft` | note |
| R-6 | `docs/mattregister.md`, källdokumentet | Lägg till CoreWeave-filtret och Alphabets `first_start` 2021 som ändringar efter första bygget. Nämn Metas avrundning (0,01 mdr), Oracles faktiska största avstånd (+1 dag) och att Microsofts `Depreciation` per kvartal kommer först i 10-Q 2025-10-29 | note |

## Tester

`tests/test_r14_avskrivningar.py` (fixturer, inget nät). Microsofts fixtur är raden som den lämnats in enligt
R-sidorna 2024-04-25 till 2026-10-28.
- den deklarerade omräkningen är den enda som hittas, och en odeklarerad stoppar (passerar)
- en deklarerad omräkning som inte finns stoppar också (passerar)
- inget enskilt kvartal blandar baser, och fönstret FY2026 är lika med helåret (passerar)
- `known_from` är inlämningsdatum och aldrig före kvartalets slut (passerar)
- CoreWeave-filtret behövs och fungerar (passerar, ersätter P1:s test som inte prövar filtret)
- brutto bildas inte ur netto och ackumulerat från olika inlämningar (passerar)
- Oracles `lag_days` och aktualitetsgräns och kvartalsmappning (passerar)
- 2024Q3 ska få en ny version på ny bas, och fönstret FY2025 ska bli helåret (strikt xfail, R-1)
- noten för `dep_hyp4` ska nämna definitionerna (strikt xfail, R-2)

`python -m pytest -q tests/test_r14_avskrivningar.py tests/test_sec_avskrivningar.py`: 22 passerade, 2 xfail.
Hela sviten: 1 568 passerade, 2 misslyckade (de kända miljöfelen `test_freshness_as_of_last_fetch`, Arena-pris
utan data, och `test_committed_fixtures_are_the_current_synthetic_bundle`, som misslyckas även utan denna
gransknings ändringar), 1 överhoppad, 3 xfail.
