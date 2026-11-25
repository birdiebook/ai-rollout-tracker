# R17 – granskning av nät, optik och servrar ur SEC XBRL (S1)

Granskningsspår R17, 2026-11-25, gren `auto14k/r17-nat-servrar` (från `auto14k/s1-nat-servrar`). Granskat: de 42
katalogserierna i G6 från spår S1 (Arista, Cisco, Coherent, Lumentum, Super Micro, Dell, HPE och Celestica), koden i
`src/ai_tracker/series/sec_stack_nat.py`, testerna i `tests/test_sec_stack_nat.py`, källdokumentet
`docs/kallor/sec_stack_nat.md`, de två registerposterna "S1: …" 2026-11-25 och
`git log -p claude/elegant-tesla-awd2sz..auto14k/s1-nat-servrar`.

Underlag:
- S1:s tabell (1 327 rader i `/home/user/wt/s1-nat-servrar/data`). Serierna byggdes om med grenens kod, offline ur den
  delade rå-cachen (companyfacts, inlämningslistor och cirka 340 XBRL-instanser). Resultatet är identiskt: 42 av 42
  serier, samma perioder, värden och `known_from`.
- Primärkällor på www.sec.gov: huvuddokumenten i 13 inlämningar (listade i punkt 5), hämtade i följd med minst 0,5
  sekunder mellan dokumenten. Inga 403 eller 429. Textblocken i de cachade instanserna lästes för Aristas, Ciscos,
  Super Micros, HPE:s och Coherents definitioner.
- Egen kod för kontrollerna i punkt 3 och 4 (Q4 = helår − 9M direkt ur companyfacts, inlämningsdatum ur EDGAR:s
  inlämningslistor), inte `sec.py`.

**Ingen analys av förlopp gjordes.** Nivåskiftena i punkt 2 och 3 räknades bara för att visa hur stora felen är.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering | **OK.** Registerposten committades före hämtningen, och det som sågs före den är redovisat |
| 2. Taggval, definitioner och brott | **Fel i `deferred_rev_anet`**: 2018Q3 tar en annan post som kortfristig del (R17-1), och 2017Q4 är ASC 605 (R17-3). **Anmärkningar:** EMC saknas (R17-4), Aristas åtaganden 2016–2017 (R17-5) och HPE:s RPO är förutbetalda intäkter (R17-6). Omfattningsbrotten, HPE:s Server, Aristas omdatering och `exact_facts` är **OK** |
| 3. Kalender och Q4 = helår − 9M | **OK** för mappningen och för 85 Q4-rader. **Fel:** första versionen av Dells ISG och Servers and networking 2021Q4 blandar baser (R17-2) |
| 4. `known_from` och versioner | **OK.** Alla rader har ett inlämningsdatum, ingen ligger före periodens slut, och omräkningar är nya versioner |
| 5. Handkontroller | 11 bolagskvartal i alla åtta bolag mot huvuddokumenten. Allt stämmer utom `deferred_rev_anet` 2018Q3 |
| 6. Licens och klass | **OK** |
| 7. Segmentintäkter är inte AI-intäkter | **OK**, med R17-4 som undantag för rekommendationen om `rev_dell_isg` |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** I 39 av 42 serier hittades inget fel i värden eller datering. Två fel ger
fel värden i enstaka kvartal: `deferred_rev_anet` 2018Q3 (221,9 i stället för 529,9, R17-1), och första versionen av
`rev_dell_isg` och `rev_dell_servers_networking` 2021Q4 (R17-2), som stod i ett år. Inget läckage, licensen stämmer,
och serierna ingår inte i indexet. R17-1 och R17-2 ska rättas före merge eller strax efter, med en daterad
registerpost. Inget av detta ändrar något tillstånd, eftersom serierna är katalogserier.

## 1. Förregistrering – OK

Ordningen enligt git (2026-11-25, UTC):

| Tid | Commit | Innehåll |
|---|---|---|
| 09:09:32 | `6fab1f5` | Registerposten "S1: nät, optik och servrar som katalogserier": bolag, taggar, medlemmar, åtaganden, RPO, brottsregel, kalender, katalog och vad som setts |
| 09:25:45 | `3ffdf21` | Kod, tester, tillägget i registret (omfattningsbrott, HPE:s Server, Aristas RPO-datum) |
| 09:31:47 | `c6bcc87` | Källdokument, beslutslogg och kalibreringsrad |

- companyfacts för de åtta bolagen skrevs till rå-cachen 09:21:54–09:22:52, alltså efter registerposten. Filerna skrivs
  över vid varje hämtning, så tiderna visar den sista hämtningen, inte den första.
- Spårets hjälpskript i sessionens arbetskatalog med filtider före 09:09 skriver bara ut täckning (antal fakta,
  slutdatum, inlämningar, medlemmar och taggar per instans), största relativa skillnaden mellan taggar och meningar ur
  textblock. Ett skript skriver ut taggade värden i en enskild inlämning, för att para ihop en tagg med en mening. Det
  stämmer med registrets lista "Vad som setts före denna post", som också säger att enskilda belopp syntes i
  meningarna och i HPE:s tabell.
- Skripten som räknar brott, omräkningar och avstånd har filtider efter 09:09. Tillägget i registret säger att det
  bygger på brottskontrollen och bolagens text, och det redovisar storleken på omräkningarna. Det stämmer.
- Att inga värden räknades före 09:09 går inte att bevisa ur filtiderna. Det som finns (commitordningen och
  skriptens tider och innehåll) stämmer med redovisningen.

**Är tillägget styrt av utfallet?** Nej. Regeln är generell: varje omräkning av totala intäkter över 2 % måste
deklareras, och bolagets egen text avgör om den är en ändrad omfattning eller en rättelse. Alla tre
omfattningsbrott är avvecklad verksamhet som bolaget själv redovisar (Dell 10-K 2022-03-24: "the results of VMware
… are presented as discontinued operations … for all periods presented"; HPE 10-K 2017-12-15: "reclassified the
historical financial results of the former Enterprise Services segment … and our former Software segment to Net loss
from discontinued operations"). Inget av valen beror på seriernas förlopp.

## 2. Taggval, definitioner och brott

### Totala intäkter och omfattningsbrott – OK

En egen genomgång av companyfacts (utan återställning efter brott) visar omräkningarna över 2 %: Coherent 10-K
2014-08-28 (−3,4 % för FY2012), Dell 10-K 2022-03-24 (−8,3 %) och följande 10-Q, HPE från 10-Q 2017-06-08 (−33 %)
till 10-Q 2018-09-04 (−8,6 %). Serierna läser inlämningar från 2014-08-28, 2022-03-24 och 2018-06-07. Första
versionerna av de tidigaste kvartalen är jämförelsetal på den nya omfattningen:

| Serie | Första kvartal | Värde | `known_from` | Inlämning |
|---|---|---|---|---|
| `rev_dell` | 2021Q1 | 22 590 | 2022-06-06 | 10-Q Q1 FY2023 |
| `rev_dell` | 2021Q3 | 26 424 | 2022-12-05 | 10-Q 0001571996-22-000044: "Total net revenue … 26,424" (mot 28 394 med VMware i 10-Q 2021-12-03) |
| `rev_hpe` | 2017Q1 | 6 808 | 2018-06-07 | 10-Q 0001628280-18-007715: "Total net revenue 7,468 … 6,808" |
| `rev_cohr` | 2013Q3 | 150,0 | 2014-11-07 | 10-Q Q1 FY2015 |

Det är konservativt: inget kvartal får ett värde före den nya omfattningen. Anmärkning N-1: för HPE är 2018-06-07
kontrollens datum, inte bolagets. 10-K 2017-12-15 hade redan både ES och Software som avvecklad verksamhet. 2017Q3 och
2017Q4 får därför `known_from` ett år senare än nödvändigt, och serien kunde börja 2016Q4. Källdokumentet säger att
10-Q 2018-06-07 införde mjukvaruomfattningen. Det stämmer inte. Regeln för HPE:s Server (dela vid bolagets egen
inlämning) och regeln för totala intäkter (dela vid kontrollens datum) är olika, men båda är på den säkra sidan.

### HPE:s Server – OK

Fakta för `ServerSegmentMember` per inlämning: alla inlämningar före 2026-03-10 (sista 10-K 2025-12-18) har den gamla
definitionen, och regim 2 börjar med 10-Q 2026-03-10. Den inlämningen säger: "Effective November 1, 2025, HPE
implemented an organizational change by (i) merging the Server, Hybrid Cloud, and Financial Services business segments
into a new segment named Cloud & Artificial Intelligence … The Company reflected these changes to its segment
information retrospectively". Q1 FY2025 räknades om från 4 271 till 4 348 (+1,8 %), Q2 FY2025 från 4 028 till 4 109
(+2,0 %) i 10-Q 2026-06-02. `breaks=("2026-03-10",)` och `detected=("2026-06-02",)` gör det registret säger.

### Aristas RPO-datum – OK

I instanserna har `anet:RevenueRemainingPerformanceObligationIncluding…Amount` kontexten 2024-03-31, 2024-06-30 och
2024-09-30 i 10-Q 2025-05-07, 2025-08-06 och 2025-11-05, medan meningen säger "$3.7 billion as of March 31, 2025",
"$4.7 billion as of June 30, 2025" och "$5.3 billion as of September 30, 2025". Huvuddokumentet i 10-Q 2025-08-06
(0001596532-25-000216) har samma mening. Kontextdatumet är fel och värdet är inlämningens egen balans. 10-K 2023-02-14
anger både totalen 2,2 mdr USD och den smalare RPO-siffran 1,3 mdr USD, så starten vid 2023-02-14 är rätt.

### `exact_facts` – OK

På riktiga data ger `exact_facts` med en dimension samma fakta som `sec_segment.to_facts` i 594 av 594 kombinationer av
inlämning och medlem. Dells produktrader har tre dimensioner i instansen: produkt, ISG och markören
`ConsolidationItemsAxis = OperatingSegmentsMember`, som räknas som neutral. Fakta med en extra dimension räknas inte
(S1:s eget test).

### Ciscos och Super Micros åtaganden, och Dell och HPE utan åtaganden – OK

- Cisco: tabellen "purchase commitments with contract manufacturers and suppliers" är taggad utan dimension i 10-Q
  2021-05-25 (9 809 vid 2021-05-01) och 10-K 2021-09-09 (10 254), och med `InventoriesMember` från 10-Q 2021-11-23, där
  jämförelsetalet 2021-07-31 är samma 10 254. Det är samma tabell. 10-Q 2021-02-16 har ingen tagg.
- Super Micro: 10-K 2023-08-28: "these remaining noncancelable commitments were $ 2.3 billion, including $ 70.5 million
  for related parties". Närstående ingår, som registret säger.
- Dell och HPE taggar bara tidshinkar. Att utelämna dem följer registret.

### Fel R17-1: `deferred_rev_anet` 2018Q3 tar fel post som kortfristig del (must_fix)

Regeln tar `ContractWithCustomerLiabilityCurrent` först och `DeferredRevenueCurrent` bara när den första saknas. I 10-Q
2018-11-05 (0001596532-18-000233) är `ContractWithCustomerLiabilityCurrent` = 10,9 en annan post: "As of September 30,
2018, $10.9 million of our contract liabilities was included in 'Other current liabilities'". Balansräkningen har
"Deferred revenue 318,850" och "Deferred revenue, non-current 211,005", och noten har "Deferred revenue, ending balance
$ 529,855". Serien har 10,9 + 211,0 = **221,9**. Rätt värde är **529,9**. Kvartalen runt omkring är 448,6 (2018Q2,
samma dokument: "Deferred revenue, beginning balance $ 448,644") och 587,2 (2018Q4).

`DeferredRevenueCurrent` och `…Noncurrent` finns bara i inlämningar till och med 2018-11-05. Om de får företräde
ändras bara 2018Q3. S1:s test `test_arista_contract_liabilities_sum_parts_of_one_filing` kodar den felaktiga
prioriteten (500 + 200 i stället för 499 + 200) och måste ändras samtidigt. Brottskontrollen kunde inte se felet,
eftersom balansen 2018-09-30 bara lämnas in en gång.

### Anmärkning R17-3: `deferred_rev_anet` 2017Q4 är ASC 605 (should_fix)

Registret och koden (`ANET_CL_FIRST = "2017-12-31"  # first ASC 606 balance date`) säger att balanserna från
2017-12-31 är ASC 606. Arista bytte med den modifierade retroaktiva metoden: "we adopted the new standard in our first
quarter of 2018 using the modified retrospective method … we reclassified $16.5 million of deferred revenue as of
January 1, 2018 to other current liabilities and other long-term liabilities" (10-Q 2018-11-05). Jämförelsetalet
2017-12-31 (327,706 + 187,556 = 515,3) är alltså ASC 605, och den första ASC 606-balansen är öppningen 2018-01-01
(498,7, "Deferred revenue, beginning balance … $ 498,740"). 2017Q4 skarvas med ASC 606-kvartalen, med en skillnad på
3,2 %.

### Anmärkning R17-4: EMC saknas (should_fix)

`rev_dell_isg` och `rev_dell_servers_networking` börjar 2015Q1 med Dells ESG före EMC-fusionen ("On September 7, 2016,
EMC Corporation … became a wholly-owned subsidiary of Dell Technologies", 10-Q 2016-12-09). ISG går från 3 779
(2016Q2) till 5 989 (2016Q3, delvis EMC) och 8 395 (2016Q4). Enligt regeln är ett förvärv inget brott, och det är
rätt. Men källdokumentets lista över förvärv nämner inte EMC, som är det största nivåskiftet i S1:s data. Beslutsloggen
och `for_owner` kallar `rev_dell_isg` en av "de längsta rena kandidaterna" med 46 kvartal. Utan EMC-kvartalen är det 38
kvartal (från 2017Q1).

### Anmärkning R17-5: Aristas åtaganden 2016–2017 (should_fix)

Källdokumentet säger "Det är samma definition". Meningarna i noten ändras 2018:

| Inlämning | Mening |
|---|---|
| 10-K 2016-02-25 | "non-cancelable purchase commitments of $43.9 million to our contract manufacturers and suppliers" |
| 10-Q 2016-05-05 | "… of $57.3 million to our contract manufacturers and suppliers" |
| 10-Q 2016-08-05 till 10-Q 2017-11-03 | "… purchase commitments of $X million" (utan uppdelning) |
| 10-K 2018-02-20 | "… of $195.1 million, of which $147.9 million was to our contract manufacturers and suppliers" |

2016 knyts beloppet till kontraktstillverkare och leverantörer. Från 2018-02-20 är den odimensionerade taggen totalen,
och delen till kontraktstillverkare är 76 % av den. Om 2016–2017 års tal är totalen eller delen går inte att avgöra
ur texten, och det finns inga jämförelsetal som brottskontrollen kan pröva. Det är inte visat att det är samma
definition.

### Anmärkning R17-6: HPE:s RPO är förutbetalda intäkter (should_fix)

HPE beskriver sitt taggade RPO så: "the aggregate amount of remaining performance obligations, or deferred revenue"
(10-K 2022-12-08 till 10-Q 2024-03-05) och "the aggregate amount of deferred revenue, was $ 10.6 billion" (10-Q 2026-03-10,
0001645590-26-000032; samma ordalydelse från 10-Q 2024-06-05). Dells och Ciscos RPO är förutbetalda intäkter plus
ofakturerade belopp ("deferred revenue plus unbilled", Dell 10-K 2022-03-24 och Cisco 10-Q 2021-05-25). `rpo_hpe` har
samma etikett som de andra, och varken noten eller källdokumentet säger skillnaden.

### Inte prövat

Lager prövas inte för brott, som registrerat. Omräkningar som syns i datat men inte förklaras (N-3): `inv_lite` 2018Q2
+13,3 % (153,6 → 174,1 i 10-K 2019-08-27), `inv_hpe` 2016Q3 −3,0 % (ES och Software), `inv_anet` 2014Q4 −3,1 %.
Coherents flytt av affärsenheter till D&C från FY2027 räknades inte om ("Prior period segment information has not
been recast", 10-Q 2026-11-04). Det går inte att se i datat, och det står som förbehåll.

## 3. Kalender och Q4 = helår − 9M

### Mappning – OK

Räkenskapskvartalets slutmånad mot periodens kalenderkvartal i alla 42 serier (ombygget):

| Bolag | Räkenskapsår | Slutmånad → kalenderkvartal |
|---|---|---|
| Cisco | sista lördagen i juli | jul → Q2, okt → Q3, jan → Q4 föregående år, apr och maj → Q1 |
| Dell | fredagen närmast 31 jan | jan och feb → Q4 föregående år, apr och maj → Q1, jul och aug → Q2, okt och nov → Q3 |
| HPE | 31 okt | jan → Q4 föregående år, apr → Q1, jul → Q2, okt → Q3 |
| Lumentum | lördagen närmast 30 jun | jan → Q4 föregående år, mar och apr → Q1, jun och jul → Q2, sep och okt → Q3, dec → Q4 |
| Coherent, Super Micro | 30 jun | kalenderkvartal |
| Arista, Celestica | kalenderår | kalenderkvartal |

Cisco slutade Q3 FY2021 den 1 maj (14 veckor), och det kvartalet blir 2021Q1, som det ska. Balanser får
räkenskapskvartalets etikett: Dells RPO 2022-01-28 ("approximately $ 42 billion", 10-K 2022-03-24) är 2021Q4, och HPE:s
lager 2026-01-31 (6 913) är 2025Q4. Valet skiljer sig från `sec_rpo.py`, det står i registret, och det ger ingen
datering före periodens slut. Testet `test_midpoint_rule_maps_each_fiscal_calendar` prövar elva verkliga
kvartalsgränser.

### Q4 = helår − 9M – OK

Med egen kod direkt ur companyfacts: för varje Q4-rad vars första version kommer från ett 10-K räknades helåret ur det
10-K:t minus 9M ur senaste 10-Q före det. 85 rader (Arista 13, Cisco 18, Coherent 12, Lumentum 11, Super Micro 17,
Dell 4, HPE 9, Celestica 1). Alla stämmer på 0,6 MUSD. Ciscos FY2026 (63 325 − 46 073 = 17 252) och HPE:s Server FY2025
(17 639 − 13 202 = 4 437) kontrollerades också av S1 mot dokumenten.

### Fel R17-2: Q4 över ett basbyte (must_fix)

Dells 10-K 2022-03-24 (0001571996-22-000009) har ISG på en ny bas: "Total ISG net revenue $ 34,366 (FY2022) … $ 33,002
(FY2021)", där 10-K 2021-03-26 hade 32 588 för FY2021 (+1,27 %). 9M FY2022 i arkivet då var den gamla basen: "Total ISG
net revenue … 24,771" (10-Q 2021-12-03, 0001571996-21-000063). 10-Q 2022-12-05 (0001571996-22-000044) räknade om 9M
till 25 147. Serien får:

| Serie | 2021Q4, första version (2022-03-24) | Senare version (2023-03-30) | Skillnad |
|---|---|---|---|
| `rev_dell_isg` | 34 366 − 24 771 = **9 595** | 34 366 − 25 147 = 9 219 | +4,1 % |
| `rev_dell_servers_networking` | 17 901 − 13 104 = **4 797** | 17 901 − 13 181 = 4 720 | +1,6 % |

Den första versionen ligger inte på någon bas och stod i ett år. Varje enskild omräkning är under 2 %, så
brottskontrollen ser inget. Källdokumentet säger att ISG "räknades om med 0,6–1,6 %", men kvartalet 2021Q4 ändrades
med −3,9 %. `sec.md` beskriver samma sak för avvecklad verksamhet och säger att den inte går att upptäcka. Här går den
att upptäcka: samma 10-K räknade om tidigare helår av samma rad. En sökning i alla S1:s serier efter Q4-rader ur ett
10-K som också räknade om tidigare perioder gav fyra andra fall (Dells ISG 2018Q4, HPE:s Server 2025Q3, Ciscos
Infrastructure Platforms 2020Q2 och 2021Q2, Super Micro 2017Q2). Där låg 9M redan på den nya basen, eller ändringen var
under 0,5 %. `rev_dell` påverkas inte, eftersom omfattningsregeln läser 9M först ur 10-Q 2022-12-05.

## 4. `known_from` och versioner – OK

- Alla 1 327 rader har `known_from` lika med ett inlämningsdatum för ett 10-Q eller 10-K hos bolaget (EDGAR:s
  inlämningslistor). Minsta avstånd från räkenskapskvartalets slut är 23 dagar (Cisco). Ingen rad är daterad före
  kalenderkvartalets slut. Datatesterna i `warehouse.py` är gröna på S1:s rader.
- Omräkningar blir nya versioner med den omräknande inlämningens datum, till exempel Super Micros rättelse 2019-05-17
  (sex kvartal 2015–2017) och HPE:s Server FY2024 (−0,5 till −0,8 % i FY2025:s 10-Q och 10-K).
- Kvartal som först finns som jämförelsetal får ett senare `known_from` än bolagets publicering. Det är konservativt.
- Aktualitetsgränserna 178–212 dagar stämmer med S1:s metod. Anmärkning N-4: för Super Micro filtreras bolagets egna
  sena inlämningar bort (10-K FY2017 kom 686 dagar efter kvartalet, 10-K FY2024 240 dagar), genom att bara kvartal med
  mindre än 100 dagar mellan räkenskapskvartalets slut och första värdet räknas. Filtret står inte i registret. Det
  gäller bara aktualiteten, och utan det vore gränsen meningslös.

## 5. Handkontroller – 11 bolagskvartal, alla åtta bolag

Värden ur S1:s tabell mot huvuddokumentet i inlämningen på www.sec.gov. Andra kvartal än S1:s egna kontroller.

| Bolag och kvartal | Inlämning (accession) | Serie och värde | I dokumentet | Dom |
|---|---|---|---|---|
| Arista 2018Q3 | 10-Q 0001596532-18-000233 (2018-11-05) | `rev_anet` 563,3, `inv_anet` 216,3, `purchase_oblig_anet` 423,1 | "Total revenue 563,309"; "Inventories 216,313"; "non-cancellable purchase commitments of $423.1 million" | OK |
| Arista 2018Q3, **förutbetalda intäkter** | samma | `deferred_rev_anet` **221,9** | "Deferred revenue 318,850" + "Deferred revenue, non-current 211,005" = 529,855 | **Fel (R17-1)** |
| Arista 2018Q2 | samma | `deferred_rev_anet` 448,6 | "Deferred revenue, beginning balance $ 448,644" (tre månader) | OK |
| Arista 2025Q2, omdaterad RPO | 10-Q 0001596532-25-000216 (2025-08-06) | `rpo_anet` 4 700 | "amounts to $ 4.7 billion as of June 30, 2025" | OK |
| Cisco 2021Q1 (Q3 FY2021, slut 1 maj), **åtaganden** | 10-Q 0000858877-21-000008 (2021-05-25) | `rev_csco` 12 803, `inv_csco` 1 579, `purchase_oblig_csco` 9 809, `rev_csco_infra_platforms` 6 832, `rpo_csco` 28 138 | "Total revenue 12,803"; "Inventories 1,579"; "Total $ 9,809"; "Infrastructure Platforms $ 6,832"; RPO "Total $ 28,138" | OK |
| Dell 2021Q4 (Q4 FY2022), **segment**, Q4 = helår − 9M | 10-K 0001571996-22-000009 (2022-03-24), 10-Q 0001571996-21-000063 och 0001571996-22-000044 | `rev_dell_isg` 9 595 → 9 219, `rev_dell_servers_networking` 4 797 → 4 720, `rev_dell` 27 992, `inv_dell` 5 898, `rpo_dell` 42 000 | ISG 34 366, 24 771 och 25 147; Servers and networking 17 901, 13 104 och 13 181; "Total net revenue … 101,197" och 9M 73 205; "Inventories 5,898"; "approximately $ 42 billion" | Totalen, lagret och RPO OK; första versionen av segmenten **fel (R17-2)** |
| HPE 2017Q1 och 2018Q1 (Q2 FY2017 och FY2018) | 10-Q 0001628280-18-007715 (2018-06-07) | `rev_hpe` 6 808 och 7 468, `inv_hpe` 2018Q1 2 848 | "Total net revenue 7,468 … 6,808"; "Inventory 2,848" | OK |
| HPE 2025Q4 (Q1 FY2026), **segment** | 10-Q 0001645590-26-000032 (2026-03-10) | `rev_hpe_server_fy26` 4 232, `rev_hpe_dc_networking` 444, `rev_hpe` 9 301, `inv_hpe` 6 913, `rpo_hpe` 10 600 | "Server 4,232 | 4,348"; "Data Center Networking 444 | 92"; "Total net revenue 9,301"; "Inventory 6,913"; "aggregate amount of deferred revenue, was $ 10.6 billion" | OK (R17-6 för etiketten) |
| Coherent 2023Q4 (Q2 FY2024), **segment** | 10-Q 0000820318-24-000004 (2024-02-06) | `rev_cohr` 1 131,4, `rev_cohr_networking` 524,2, `inv_cohr` 1 291,6 | "Revenues $ 1,131,434"; Networking "$ 524,235"; "Inventories 1,291,634" (tusental) | OK |
| Lumentum 2019Q1 (Q3 FY2019), **segment, åtaganden** | 10-Q 0001633978-19-000030 (2019-05-07) | `rev_lite` 432,9, `rev_lite_opcomms` 377,9, `inv_lite` 272,2, `purchase_oblig_lite` 208,0 | "Net revenue $ 432.9"; "OpComms $ 377.9"; "Inventories 272.2"; "Purchase obligations of $208.0 million as of March 30, 2019" | OK |
| Super Micro 2023Q2 (Q4 FY2023), **åtaganden**, Q4 = helår − 9M | 10-K 0001375365-23-000036 (2023-08-28) | `rev_smci` 2 184,9, `inv_smci` 1 445,6, `purchase_oblig_smci` 2 300, `rpo_smci` 304,4 | "Total net sales $ 7,123.5" (helår; 9M 4 938,6 ur 10-Q 2023-05-05, companyfacts); "Inventories 1,445,564"; "noncancelable commitments were $ 2.3 billion"; "approximately $ 304.4 million" | OK |
| Celestica 2025Q2, **segment** | 10-Q 0001030894-25-000047 (2025-07-28) | `rev_cls` 2 893,4, `rev_cls_ccs` 2 074,3, `inv_cls` 1 918,1 | "Revenue … $ 2,893.4"; CCS "$ 2,074.3"; "Inventories 1,918.1" | OK |

Inte verifierat mot huvuddokument: Super Micros 9M för FY2023 (bara ur companyfacts), och Dells och HPE:s
segmentvärden före 2021.

## 6. Licens och klass – OK

Alla 42 Spec har `license` = SEC-texten ur `series/sec.py` ("Information presented on sec.gov is considered public
information and may be copied or further distributed …", sec.gov/privacy), `publish=True` och klassen `ja` genom
regeln `sec` i `licenses.py`. Värdena är taggade XBRL-fakta och inga utdrag ur text, så kravet på extraktionsgranskning
gäller inte. Anmärkning N-5: i licensrapporten (`licenses.SOURCE_GROUPS`) hamnar S1:s instansserier (åtaganden för
Arista, Cisco och Lumentum, och `rpo_anet`) i gruppen som heter "Nvidias inköpsåtaganden, P1:s egna taggar".

## 7. Segmentintäkter är inte AI-intäkter – OK

Källdokumentet börjar förbehållen med "Inget av detta är AI-intäkter" och säger att segment- och produktintäkter inte
är AI-intäkter, med exempel per bolag. Varje segmentserie har `SEG_CAVEAT` ("Segment- eller produktintäkter är inte
AI-intäkter …") i noten, och varje total har `CAVEAT`. `rev_dell_ai_servers` har en egen not ("Dells egen avgränsning …
säger inget om slutkundens användning"). Testet `test_every_s1_series_says_it_is_not_ai_revenue_and_carries_the_sec_licence`
prövar det. Undantaget är rekommendationen om `rev_dell_isg` som "ren" kandidat (R17-4).

## Rättningar (för ett rättningsspår)

| # | Var | Rättning | Allvar |
|---|---|---|---|
| R17-1 | `sec_stack_nat.py` `anet_contract_liabilities` | Ge `DeferredRevenueCurrent` och `DeferredRevenueNoncurrent` företräde framför `ContractWithCustomerLiability*` i samma inlämning. Bara 2018Q3 ändras (221,9 → 529,9). Ändra S1:s test som kodar den gamla prioriteten. Daterad registerpost med meningen ur 10-Q 2018-11-05. Det strikta xfail-testet `test_r17_1_…` slår om | must_fix |
| R17-2 | `sec_stack_nat.py` `line_series` | Räkna inte Q4 = helår − 9M ur ett 10-K som räknar om tidigare perioder av samma rad med mer än `sec.TOL`, när 9M-basen är inlämnad före 10-K:t. Vänta på en 9M på den nya basen. Då får `rev_dell_isg` och `rev_dell_servers_networking` 2021Q4 bara 9 219 och 4 720, kända 2023-03-30. Registerpost före ombygget. Minsta godtagbara rättning: säg det i källdokumentet och i noterna. Det strikta xfail-testet `test_r17_2_…` slår om | must_fix |
| R17-3 | `ANET_CL_FIRST`, registret | Börja `deferred_rev_anet` 2018Q1, eller skriv att 2017Q4 är ASC 605 (515,3 mot öppningen 498,7). Rätta kommentaren "first ASC 606 balance date" | should_fix |
| R17-4 | källdokumentet, noterna för `rev_dell_isg` och `rev_dell_servers_networking`, beslutsloggen | Nämn EMC (2016-09-07) och nivåskiftet 2016Q3–Q4. Rätta "längsta rena kandidat": 38 kvartal från 2017Q1 | should_fix |
| R17-5 | källdokumentet, noten för `purchase_oblig_anet` | Stryk "Det är samma definition". Skriv att meningen 2016 knyter beloppet till kontraktstillverkare och leverantörer, och att totalen och delen redovisas var för sig från 10-K 2018-02-20. Alternativt: börja serien 2017Q4 | should_fix |
| R17-6 | noten för `rpo_hpe`, källdokumentet | Skriv att HPE:s taggade RPO är förutbetalda intäkter enligt bolagets egen text, och att den inte är jämförbar med Dells och Ciscos RPO (förutbetalda plus ofakturerade) | should_fix |
| N-1 | källdokumentet | HPE:s nuvarande omfattning börjar i 10-K 2017-12-15. 2018-06-07 är kontrollens datum. Konservativt, men skriv det | note |
| N-2 | registret (rättelse i ny post) | `rev_csco_infra_platforms` läser inlämningar från 10-Q 2017-11-21, inte 2018-11-20 som tabellen säger | note |
| N-3 | källdokumentet | Nämn de oförklarade omräkningarna av lager (`inv_lite` 2018Q2 +13,3 %, `inv_hpe` 2016Q3 −3,0 %, `inv_anet` 2014Q4 −3,1 %) | note |
| N-4 | registret | Skriv in filtret för Super Micros sena inlämningar i regeln för aktualitetsgränsen | note |
| N-5 | `licenses.SOURCE_GROUPS` | Byt namn på gruppen "SEC EDGAR XBRL instances" så att den täcker S1:s serier | note |
| N-6 | brottsregeln | Balanser (åtaganden, RPO, förutbetalda intäkter) jämförs bara när de lämnas in igen. En ändrad definition utan jämförelsetal syns inte (R17-1 och R17-5). Det bör stå i källdokumentet | note |

## Tester

`tests/test_r17_nat_servrar.py` (fixturer, inget nät):
- mittpunktsregeln ger rätt kalenderkvartal för elva verkliga kvartalsgränser hos Cisco, Dell, HPE, Lumentum,
  Coherent och Super Micro (passerar)
- räkenskapsår till juli: Q4 = helår − 9M (17 252) med 10-K:ts datum, balansen den 24 januari blir 2025Q4, och
  `known_from` är alltid ett inlämningsdatum (passerar)
- omfattningsbrotten och rättelsen stämmer med registret (passerar)
- HPE:s Server delas vid 2026-03-10 med kontroll 2026-06-02 (passerar)
- Aristas omdatering flyttar varje faktum ett år fram till inlämningens eget kvartalsslut (passerar)
- varje S1-serie har SEC-licensen, `publish=True`, klass `ja` och en not om att den inte är AI-intäkter (passerar)
- Dell-fixturen ger i dag 9 595 och 9 219 för 2021Q4, och omräkningarna ligger under 2 % (passerar)
- `deferred_rev_anet` 2018Q3 ska vara balansräkningens rad, 529,855 (strikt xfail, R17-1)
- Q4 ska inte räknas över ett basbyte (strikt xfail, R17-2)
- serien ska börja med den första ASC 606-balansen (strikt xfail, R17-3)
- noterna ska nämna EMC, Aristas ordalydelse 2018-02-20 och att HPE:s RPO är förutbetalda intäkter (strikt xfail,
  R17-4 till R17-6)

`python -m pytest -q tests/test_r17_nat_servrar.py tests/test_sec_stack_nat.py`: 31 passerade, 6 xfail.
