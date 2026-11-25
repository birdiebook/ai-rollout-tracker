# R21 – granskning av Kina via SEC (CN1)

Granskningsspår R21, 2026-11-25, gren `auto14k/r21-kina-sec`. Granskat: CN1:s 14 katalogserier för Alibaba och Baidu
(`src/ai_tracker/sources/china_sec.py`, `china_parse.py`, `china_text.py`, `fed_h10.py`,
`src/ai_tracker/series/china_sec.py`, `src/ai_tracker/china_text_check.py`, `src/ai_tracker/china_crosscheck.py`,
`curated/china_text.csv`), dokumentationen `docs/kallor/kina_sec.md` och registerposterna "2026-11-25 – CN1" och
"Ändring av CN1: dateringsregeln".

Underlag:
- 22 pressmeddelanden (exhibit 99.1 till 6-K), hämtade på nytt från www.sec.gov med projektets generiska klient.
  Alla 22 är byte för byte lika med CN1:s råkopior.
- Alibabas 20-F-instanser för FY2018 och FY2026 (hämtade på nytt) och för FY2016 och FY2017 (hämtade av R21:s första
  pass samma dag; FY2018 från det passet jämfördes med en ny hämtning och var identisk).
- companyfacts för Alibaba och Baidu (data.sec.gov, hämtade på nytt).
- Fed:s H.10-historik för renminbi (`dat00_ch.htm`) och 15 arkiverade veckoreleaser 2017–2026 (federalreserve.gov),
  Fed:s villkor (`disclaimer.htm`) och H.10:s sida om releasen.
- Ingen värd var blockerad. sec.gov svarade aldrig 403 eller 429.

Alla 14 serier byggdes om med grenens kod ur råkopiorna. Resultatet är 301 rader med samma värde, period och
`known_from` som i CN1:s tabell. Textkodningen gav samma 26 rader och samma 11 okodade kandidater med samma skäl.
Kontrollmodulen kördes igen mot EDGAR: 26 av 26 rätt. Ingen analys av förlopp gjordes.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering | **OK.** Ändringen av dateringsregeln är daterad, motiverad och konservativ |
| 2. Segmentdefinitioner och brott | **OK.** Varje gräns står i bolagets egen text, och ingen definition skarvas. **Anmärkning:** dokumentet säger att alla omräkningar vid gränserna är under 1 % (R21-2). `capex_baba_v1` säger inte att den innehåller licensierade upphovsrätter till videoinnehåll (R21-4) |
| 3. Kalender och datering | **OK.** Juni-kvartalet är kalenderkvartal 2. `known_from` är 6-K:ns inlämningsdag. Inget läckage |
| 4. Handkontroll | **OK.** 54 tal i 22 pressmeddelanden stämmer, också fyra omräknade jämförelsetal. Alla 26 textrader har rätt mått och kvartal |
| 5. Korskontroll mot 20-F | **OK** för molnet och för Baidu. **Anmärkning:** den registrerade kontrollen mot companyfacts körs inte för Alibabas capex (R21-3). R21 körde den, och den stämmer exakt |
| 6. RMB/USD | **OK.** 103 rader räknade på nytt utan avvikelse. 75 av 75 kurser i stickprovet är oreviderade. Licensen håller |
| 7. Publicering och klass | **OK** |
| 8. Förbehåll | **Anmärkning:** R21-1, R21-2 och R21-4. Övriga påståenden stämmer mot källorna |

**Slutdom: GODKÄND MED ANMÄRKNINGAR som katalogserier.** Inget värde är fel, inget värde är daterat före
inlämningen, och licensklasserna håller. De fyra rättningarna gäller dokumentationen, en etikett och korskontrollen.
Ingen av dem ändrar ett värde. Textserierna kan få `publish=True` om ägaren beslutar det: R21 har läst alla 26
meningar (punkt 4).

## 1. Förregistrering – OK

Ordningen enligt git och råkopiornas tider (2026-11-25, UTC):

| Tid | Händelse |
|---|---|
| 09:48–09:59 | Det avbrutna första försöket hämtar cirka 700 filer (index och exhibits, bland annat Alibabas pressmeddelanden och Baidu 2007–2017) |
| 12:41–12:46 | Baidus pressmeddelanden 2017–2026 hämtas |
| 12:51 | `9f6e33f` registerposten |
| 12:54–12:56 | Fler 6-K-filer (Baidus index, andra exhibits från Alibaba) |
| 12:59 | `5b14701` kodningsreglerna som kod |
| 13:00 | Kontrollmodulen körs (råkopior under `china_text_check`) |
| 13:04 | 20-F-instanserna för korskontrollen |
| 13:06 | `ad9b987` dateringsändringen, sedan `efb5c71` med kod och serier (samma sekund, i den ordningen) |
| 13:10–13:11 | `d2dfec7` och `1ca81ef`: dokument och driftnot |

- Posten säger vad som var sett före den: inlämningslistor, titlar, tabellhuvuden, radetiketter och fotnoter, och att
  siffrorna syntes. Det stämmer med råkopiornas tider. Git visar att inget värde committades före 13:06. Git kan inte
  visa att inget räknades lokalt, och inget i filerna tyder på det.
- Efter den första kodningskörningen ändrades bara `FY_HEADING` (`git diff 5b14701 efb5c71`). Mönstret matchade titeln
  i fjärde kvartalets pressmeddelanden, så att inget där kodades. Rättelsen gör att koden följer regel 4 som den är
  skriven, och den står i registret.
- Dateringsregeln ändrades efter dateringskontrollen men före analys, med datum och motivering. Den nya regeln behåller
  inlämningsdagen som `known_from`. Det är senare än datumet i pressmeddelandet, alltså konservativt och utan
  läckage. Den gamla regeln hade tagit bort pressmeddelanden utan att något läckage undveks. Ändringen godtas.
- Liten avvikelse: posten säger 47 pressmeddelanden från Alibaba. Koden läser 48, ett per kvartal 2014Q4–2026Q3, utan
  lucka (N-1).

## 2. Segmentdefinitioner och brott – OK, med anmärkning

R21 läste gränserna i pressmeddelandena själva:

| Gräns | Pressmeddelande | Vad texten säger (R21:s sammanfattning) |
|---|---|---|
| `rev_baba_cloud_v1` börjar | 2016-08-11 | Första segmenttabellen med "Cloud computing" |
| `v1` → `v2` | 2021-08-03 | DingTalk flyttas till molnsegmentet från 2021-04-01. Jämförelsetalen räknas om ("Comparative figures were reclassified") |
| `v2` → en release | 2023-08-10 | Sex affärsgrupper. Cloud Intelligence Group omfattar Alibaba Cloud och DingTalk |
| → `v3` | 2023-11-16 | DingTalk flyttas till "All others" från kvartalet till 2023-09-30, med omräknade jämförelsetal. Det står i pressmeddelandet 2023-11-16 självt, inte bara i 2024-08-15 som dokumentet citerar |
| `v3` → `v4` | 2026-08-20 | Cloud Intelligence Group och T-Head slås ihop till AI Cloud and Compute Services. AI-modellabben och Qwen låg i "All others" och bildar ett eget segment |
| `capex_baba_v1` → en release | 2018-08-23 | Raden nämner licensierade upphovsrätter i etiketten |
| → `capex_baba_v2` | 2018-11-02 | Anläggningstillgångar på en egen rad. Upphovsrätter och immateriella tillgångar på en annan |

Gränsen för DingTalk 2023-11-16 är alltså rätt. Det syns också i siffrorna: 2023Q3 är 27 648 både 2023-11-16 och
2024-11-15.

**Ingen skarv.** Varje definition har en egen nyckel (`ERAS`). `era_vintages` läser bara pressmeddelanden inom
definitionens datum. En odeklarerad omräkning inom en definition stoppar hämtningen. Ingen sådan finns.

**Omräkningarnas storlek vid gränserna** (samma kvartal, MRMB, före → efter):

| Gräns | Kvartal | Före | Efter | Ändring |
|---|---|---|---|---|
| DingTalk in (`v1` → `v2`) | 2020Q2 – 2021Q1 | 12 345 – 16 761 | 12 437 – 16 865 | +0,6 till +0,9 % |
| 2023: segment före elimineringar (`v2` → release 2023-08-10) | 2022Q2 | 17 685 | 24 127 | +36,4 % |
| 2023: `v2` → `v3` | 2022Q3, 2022Q4, 2023Q1 | 20 757, 20 179, 18 582 | 27 035, 27 364, 24 742 | +30,2, +35,6, +33,2 % |
| DingTalk ut (release 2023-08-10 → `v3`) | 2023Q2 | 25 123 | 25 065 | −0,2 % |
| T-Head in (`v3` → `v4`) | 2025Q2, 2025Q3 | 33 398, 39 824 | 33 418, 39 914 | +0,1, +0,2 % |
| Capex (`capex_baba_v1` → `v2`) | 2017Q3, 2017Q4, 2018Q1 | 8 002, 9 029, 5 616 | 5 322, 6 463, 2 603 | −33,5, −28,4, −53,7 % |

Uppdelningen är rätt. Men dokumentet säger under Förbehåll att "omräkningarna vid gränserna är små (under 1 %)", och
beslutsloggen och spårets sammanfattning säger detsamma. Det gäller DingTalk och T-Head. Det gäller inte
omorganisationen 2023 (+30 till +36 %) eller capex 2018 (−28 till −54 %). Den som läser bara förbehållet kan tro
att serierna nästan går att skarva (**R21-2**, ska rättas).

**`capex_baba_v1` innehåller licensierade upphovsrätter.** I pressmeddelandet 2018-11-02 delas 2017Q3 upp: 5 322 i
anläggningstillgångar och 2 680 i upphovsrätter och immateriella tillgångar, sammanlagt 8 002, som är `v1`:s värde.
I 20-F:n för FY2017 heter samma årsrad (12 220) "...IntangibleAssetsAndLicensedCopyrightsOfVideoContent". I 2017Q3
var alltså en tredjedel av `v1` upphovsrätter och immateriella tillgångar (bland annat videoinnehåll till Youku), inte
datacenter. Etiketten och noten säger bara "anläggningstillgångar och immateriella" (**R21-4**, ska rättas).

**Definitioner med ett enda pressmeddelande** (registrerade före värdena) blir ingen serie. Det kostar data:
2018Q2 för capex och 2023Q2 för molnet blir kända på seriens definition först ett år senare. För capex finns ett
belägg för att 2018-08-23 är samma mått som `v1`: jämförelsetalet 2017Q2 är 3 162 i båda. `v1` hade då kunnat sluta
2018Q2 (9 759) (N-3). Det kräver en daterad registerändring.

**Etiketten för `v4`** säger "(från 2025Q2)". Serien börjar 2026Q2, eftersom `sec.contiguous_tail` tar bort 2025Q2
och 2025Q3 tills luckan 2025Q4–2026Q1 fylls (**R21-1**, ska rättas).

## 3. Kalender och datering – OK

- Alibabas kvartal: "Three months ended June 30, 2015 2016" ger 2016Q2 (räkenskapsårets Q1). "December Quarter 2024"
  ger 2024Q4. "March Quarter 2015 and Full Fiscal Year 2015" och HKEX-titeln 2026-05-13 ger kalenderkvartal 1.
  Kontrollerat i pressmeddelandena och med test.
- `known_from` är 6-K:ns `filingDate` för alla 301 rader. En 6-K som tas emot efter 17:30 i New York får nästa
  arbetsdag (Baidu 2021-02-19 22:55 UTC blir 2021-02-22). Det ger en senare `known_from`, aldrig en tidigare.
- Datum i pressmeddelandena mot inlämningen: Alibaba 47 samma dag och 1 dagen före (2016-01-29). Baidu 17 samma dag,
  6 en dag före och 5 två till sex dagar före (2020-03-04 med 2020-02-27, 2021-02-22 med 2021-02-17 och tre till).
  Allt stämmer med dokumentet.
- Alibabas 6-K tas emot 20–21 UTC i 39 av 48 fall. Fördröjningen från kvartalets slut är 24–78 dagar för Alibaba
  (median 44) och 44–64 dagar för Baidu (median 51). Aktualitetsgränserna 200 och 186 dagar följer av det.
- `known_from` är ett datum. Projektets konvention gör värdet tillgängligt hela dagen, också timmarna före
  pressmeddelandet. Det gäller alla SEC-serier, inte bara CN1 (N-6).

## 4. Handkontroll – OK

Alla tal lästes i de nyhämtade pressmeddelandena och jämfördes med seriernas rader (MRMB; Baidus capex som Baidu, Inc.
/ utan iQIYI; textraderna i miljarder RMB):

| Inlämnad | Accession | Kontrollerat | Serie |
|---|---|---|---|
| 2015-05-07 | 0001104659-15-035237 | capex 2015Q1 700, 2014Q1 275 | `capex_baba_v1` |
| 2016-08-11 | 0001104659-16-138896 | moln 2016Q2 1 243, 2015Q2 485; capex 2016Q2 2 794 | `v1`, `capex_baba_v1` |
| 2018-08-23 | 0001104659-18-053369 | capex 2017Q2 3 162 (= `v1`), 2018Q2 9 759 | ingen serie |
| 2018-11-02 | 0001104659-18-065748 | capex 2018Q3 11 632; **2017Q3 omräknat** 5 322 (`v1`: 8 002) | `capex_baba_v2` |
| 2020-08-20 | 0001104659-20-097260 | moln 2020Q2 12 345 | `v1` |
| 2021-08-03 | 0001104659-21-099438 | moln 2021Q2 16 051; **2020Q2 omräknat** 12 437; capex 10 897 | `v2`, `capex_baba_v2` |
| 2023-08-10 | 0001104659-23-089768 | moln med DingTalk 2023Q2 25 123, 2022Q2 24 127 | ingen serie |
| 2023-11-16 | 0001104659-23-119081 | moln 2023Q3 27 648, 2022Q3 27 035 | `v3` |
| 2024-08-15 | 0001104659-24-090102 | moln 2024Q2 26 549; **2023Q2 omräknat** 25 065 | `v3` |
| 2025-02-20 | 0001104659-25-015648 | moln 2024Q4 31 742; capex 31 369 | `v3`, `capex_baba_v2` |
| 2025-08-29 | 0001104659-25-085638 | moln 2025Q2 33 398; capex 38 629 | `v3`, `capex_baba_v2` |
| 2026-05-13 | 0001104659-26-060224 | moln 2026Q1 41 626; capex 26 588 | `v3`, `capex_baba_v2` |
| 2026-08-20 | 0001104659-26-099220 | moln 2026Q2 48 437; **2025Q2 omräknat** 33 418; capex 67 660 | `v4`, `capex_baba_v2` |
| 2020-03-04 | 0001193125-20-061595 | 2019Q4 884 / 652; 2018Q4 3 078 / 2 900; 2019Q3 1 212 / 1 031 | `capex_bidu`, `_core` |
| 2020-11-17 | 0001193125-20-295510 | 2020Q3 1 507 / 1 417; utanför annonser 2,9 | capex, `rev_bidu_core_nonads` |
| 2021-02-22 | 0001193125-21-049165 | inga tabeller; utanför annonser 2020Q4 4,2 före rubriken för helåret (helåret 12,4 efter) | `rev_bidu_core_nonads` |
| 2021-05-20 | 0001193125-21-167243 | 2021Q1 1 499 / 1 438; 2020Q4 2 178 / 2 151; 4,2 (huvud med inflätade rader) | capex, text |
| 2022-11-23 | 0001193125-22-291565 | 2022Q3 2 188 / 2 140; 6,5 (inflätat huvud) | capex, text |
| 2023-05-16 | 0001193125-23-145594 | 2023Q1 1 295 / 1 295 (iQIYI "—"); 6,4 | capex, text |
| 2025-11-18 | 0001193125-25-285391 | 2025Q3 3 401 / 3 378; AI Cloud Infra 4,2; 9,3 | capex, båda textserierna |
| 2026-02-26 | 0001193125-26-076505 | 2025Q4 1 972 / 1 952; AI Cloud Infra 5,8 | capex, `rev_bidu_ai_cloud_infra` |
| 2026-08-18 | 0001193125-26-355431 | 2026Q2 11 390 / 11 370; AI Cloud Infra 7,3 | capex, `rev_bidu_ai_cloud_infra` |

54 tal, inga avvikelser. Varje omräknat jämförelsetal hamnar i serien för sin egen definition. Inget kvartal har två
rader i samma serie.

**Baidus kolumnordning.** Det finns tre layouter för huvudet: rak, inflätad (2021-05-20, 2022-11-23, 2023-08-22,
2023-11-21, 2024-02-28 och 2024-08-22) och toppjusterad (2025-05-21). Ordningen Baidu utan iQIYI, iQIYI, Baidu, Inc.
gäller i alla tre. Kontrollen att totalen är summan skiljer bara på ordningar där iQIYI inte är noll. Utom 2018Q4,
2019Q1, 2019Q2 och 2026Q3 står varje kvartal i två eller tre pressmeddelanden, och värdena är lika. En förväxlad ordning
hade stoppat hämtningen. De fyra kvartalen kommer från pressmeddelanden med rakt huvud, där ordningen står i klartext.
CN1:s tester täcker två av layouterna. R21 lade till den tredje och fallet med "—" (N-7).

**Textraderna.** R21 läste alla 26 meningar. Alla mäter det som serien säger: AI Cloud Infra för rapportkvartalet,
eller Baidu Cores intäkter utanför annonser för rapportkvartalet. De sex raderna ur fjärde kvartalets pressmeddelanden
kommer från kvartalsavsnittet före rubriken för helåret. Formuleringen "non-marketing revenue" (2021-02 och 2021-05)
är samma mått som "non-online marketing revenue". Belägg: 18 par där tillväxten mot året före står i meningen. I alla
18 stämmer det implicita fjolårsvärdet med seriens värde inom avrundningen. Ett exempel: 2021Q4 6,9 med +63 % ger 4,23 för 2020Q4,
och serien har 4,2. För AI Cloud Infra ger 2026Q3 8,2 med +94 % värdet 4,23 för 2025Q3, och serien har 4,2. Baidus
egen tabell 2026-02-26 har också 4,2 för 2025Q3. De 11 okodade kandidaterna har rätt skäl: 5 helårstal, 1 "exceeded",
1 "approximately" för helåret och 4 tabeller i miljarder RMB.

Pressmeddelandena 2020-03-04, 2020-05-20 och 2020-08-17 har inget mått för Baidu Core utanför annonser, bara "Other
revenues" för hela koncernen. Att `rev_bidu_core_nonads` börjar 2020Q3 är alltså rätt. 2026-02-26 skriver att Baidu
Core definieras om till Baidu General Business och att uppdelningen kommer ur interna räkenskaper som inte är
reviderade. Det stämmer med dokumentet.

## 5. Korskontroll mot 20-F – OK för molnet och Baidu, anmärkning för Alibabas capex

`python -m ai_tracker.china_crosscheck` ger samma tabell som dokumentet. R21 kontrollerade också mot nyhämtade
källor:
- 20-F FY2026 (0001193125-26-231755): Cloud Intelligence Group 106 374, 118 028 och 158 132 för FY2024–FY2026,
  exakt summan av fyra kvartal i `v3`.
- Baidus companyfacts: `PaymentsToAcquirePropertyPlantAndEquipment` 6 428, 5 084, 10 896, 8 286, 11 190, 8 134 och
  12 073 för 2019–2025, exakt summan i `capex_bidu`.
- FY2016 för `v1` (3 019 i 20-F FY2017 och FY2018) stämmer exakt. CN1 läser 20-F först från 2019 och kontrollerar inte
  det året.

**Alibabas capex.** Registret säger "Capex mot companyfacts `PaymentsToAcquirePropertyPlantAndEquipment` (och
immateriella tillgångar där det finns)". Koden jämför i stället med 20-F:ns
`PaymentsToAcquireLandUseRightsPropertyAndEquipment`, som också innehåller mark och kontorscampus, och redovisar en kvot
(76–98 %). `capex_baba_v1` jämförs inte alls. Avvikelsen nämns i dokumentet men inte som en daterad registerändring.
Den registrerade kontrollen gick att göra, och den stämmer exakt:

| Serie | År | Summan av fyra kvartal | 20-F / companyfacts |
|---|---|---|---|
| `capex_baba_v1` | FY2015 | 4 770 | 4 770 (20-F FY2016, anläggningstillgångar och immateriella) |
| `capex_baba_v1` | FY2016 | 5 438 | 5 438 |
| `capex_baba_v1` | FY2017 | 12 220 | 12 220 (companyfacts 5 680 + 6 540 immateriella) |
| `capex_baba_v1` | FY2018 | 25 809 | 25 809 (companyfacts 15 601 + 10 208) |
| `capex_baba_v2` | FY2019 | 32 336 | 32 336 (`PaymentsToAcquireOtherPropertyPlantAndEquipment`) |
| `capex_baba_v2` | FY2020 | 24 662 | 24 662 |

För FY2021–FY2026 finns ingen sådan rad i companyfacts, och R21 hittade inte summorna i instanserna. Där är kvoten
det enda som går. Bilden blir starkare än dokumentet säger: Alibabas capex stämmer exakt där en jämförbar rad finns
(**R21-3**, ska rättas: kör den registrerade kontrollen och redovisa den).

FY2023 för `v3` går inte att pröva, eftersom 2022Q2 saknas i `v3`. 20-F:ns 103 497 ger ett implicit 2022Q2 på 24 356.
Pressmeddelandet 2023-08-10 har 24 127 med DingTalk. Skillnaden har motsatt tecken mot DingTalk-effekten 2023Q2
(−58). Den definitionen skiljer sig alltså från `v3` på mer än DingTalk, eller så har 20-F:n en annan grund för
FY2023. Ingen serie påverkas (N-4).

## 6. RMB/USD – OK

- H.10 hämtas från federalreserve.gov. R21 räknade kvartalsmedlen på nytt med en egen tolkning av sidan. Alla 103
  US$-rader blir exakt lika (största avvikelse 0). Kurserna ligger mellan 6,09 och 7,27 CNY per USD 2013Q4–2026Q3.
- `known_from` = max(RMB-radens datum, kvartalets slut + 10 dagar). Inlämningen kommer minst 24 dagar efter
  kvartalets slut, så kursdelen binder aldrig. H.10:s historiksida uppdateras varje måndag med förra veckans kurser,
  så 10 dagar räcker.
- Regeln om 55 dagar binder aldrig: det minsta fullständiga kvartalet har 59 noterade dagar (2019Q1). CN1:s test
  prövar regeln tillsammans med ett pågående kvartal. R21 lade till ett test som prövar den för sig (N-7).
- **Revisioner.** R21 jämförde 15 arkiverade veckoreleaser 2017–2026 (en per år nära kvartalsslut) med dagens
  historiksida: 75 av 75 dagskurser är lika. Fed skriver på H.10:s sida att gamla releaser inte revideras och att de
  kan sakna senare revideringar av data. Revideringar är alltså möjliga men syns inte i stickprovet. Dokumentet bör
  säga det i stället för "inte kontrollerat" (N-2).
- **Licens.** Fed:s villkor säger att informationen på Board:s webbplats är public domain om inget annat anges.
  H.10-sidan anger inget annat. Kurserna certifieras av Federal Reserve Bank of New York för tullsyfte. Klassen `ja`
  håller. Källtexten nämner inte FRED, och regeln alfred slår inte till.

## 7. Publicering och klass – OK

- Tabellserierna har `publish=True` med SEC:s text om spridning, som TSMC:s 6-K-serier. Klass `ja` (regeln sec).
- US$-vyerna är härledda ur SEC och Fed:s public domain. Båda delarna är `ja`.
- Textserierna har `publish=False` och klass `ja` genom kurerade rader som alla kommer från sec.gov.
- `catalog.validate` ger inga fel. Ingen ny regel i `licenses.py` behövs.
- R21 har läst alla 26 textrader (punkt 4). Extraktionen håller för publicering. Att sätta `publish=True` är ett
  beslut för ägaren och ska stå som daterad ändring.

## 8. Förbehåll – anmärkning

Det som stämmer mot källorna: definitionerna per period, intäkter mellan segment från 2023-08 (34 % för FY2023),
T-Head i `v4`, att ingen serie har en revision, AI-andelen (Alibaba anger "AI-related product revenue" i miljoner RMB
från 2026-05, 8 971 för 2026Q1), Baidus tunna mått och att `v4` och AI Cloud Infra är så korta att en ändring i takt
kan vara slump.

Det som behöver rättas: R21-1 (etiketten för `v4`), R21-2 (påståendet om under 1 %) och R21-4 (upphovsrätterna i
`capex_baba_v1`). R21-2 står också i beslutsloggen. Den skrivs inte om, men rättelsen ska stå i en ny post.

## Rättningar (för ett rättningsspår)

| # | Var | Rättning |
|---|---|---|
| R21-1 | `series/china_sec.py`, `TABLE["rev_baba_cloud_v4"]` | Ta bort "(från 2025Q2)" ur etiketten, eller skriv det kvartal serien faktiskt börjar på. En öppen serie bör inte ha startkvartal i etiketten |
| R21-2 | `docs/kallor/kina_sec.md`, Förbehåll; ny post i `docs/beslutslogg.md` | Skriv att omräkningarna är under 1 % vid DingTalk och T-Head, men +30 till +36 % vid omorganisationen 2023 och −28 till −54 % för capex 2018. Lägg tabellen i punkt 2 i dokumentet |
| R21-3 | `china_crosscheck.py`; daterad registerändring | Kör den registrerade kontrollen: companyfacts `PaymentsToAcquireOtherPropertyPlantAndEquipment` (plus `PaymentsToAcquireIntangibleAssets` för `v1`) och 20-F FY2016–FY2018 för `v1`. Läs 20-F från 2016. Redovisa att kontrollen är exakt FY2015–FY2020 och att kvoten bara gäller FY2021–FY2026 |
| R21-4 | `china_sec.ERAS` (definitionstexten för `capex_baba_v1`) och dokumentet | Skriv att `v1` innehåller licensierade upphovsrätter till videoinnehåll (20-F FY2017) och att 2 680 av 8 002 i 2017Q3 var upphovsrätter och immateriella tillgångar |
| N-1 | `docs/mattregister.md` (ny post vid nästa ändring) | 48 pressmeddelanden från Alibaba, inte 47 |
| N-2 | `docs/kallor/kina_sec.md`, US$-vy | Ersätt "inte kontrollerat" med stickprovet (15 releaser, 75 av 75 lika) och Fed:s formulering om att data kan revideras |
| N-3 | registerbeslut | Pröva om pressmeddelandet 2018-08-23 hör till `capex_baba_v1` (jämförelsetalet 2017Q2 är lika). I så fall en daterad ändring som låter `v1` sluta 2018Q2 |
| N-4 | dokumentet | Nämn att FY2023 inte går att pröva för `v3`, och att 2023-08-10 skiljer sig från `v3` på mer än DingTalk |
| N-5 | dokumentet | Citera DingTalk-gränsen ur 2023-11-16, där den står först |
| N-6 | projektet, inte CN1 | `known_from` är ett datum, och värden från samma dag räknas som kända hela dagen |
| N-7 | tester | Tillagt av R21: Baidus toppjusterade huvud, iQIYI "—" och 55-dagarsregeln för sig |

R21-1 till R21-4 har var sitt strikt xfail-test i `tests/test_r21_kina_sec.py`. Testet slår om när felet är rättat.

**Kärnserie.** R21 stöder CN1:s bedömning att `capex_baba_v2` är den bästa kandidaten för G5. Den har 37 kvartal på
en definition och stämmer exakt mot 20-F FY2019–FY2020. Det kräver en egen registerpost och en granskning.

## Tester

`tests/test_r21_kina_sec.py` (syntetiska fixturer, inget nät):
- gränserna i `ERAS` är de som står i pressmeddelandena (passerar)
- varje definition är en egen serie, och ett omräknat jämförelsetal hamnar i den nya serien med sitt eget datum
  (passerar)
- Alibabas räkenskapskvartal blir kalenderkvartal, också i HKEX-titeln (passerar)
- `known_from` är inlämningsdagen, och ett oförändrat jämförelsetal behåller den första dagen (passerar)
- Baidus toppjusterade huvud och iQIYI "—" (passerar)
- 55-dagarsregeln för ett avslutat kvartal, och US$-radernas datum (passerar)
- H.10-delen av licensen är `ja`, och ingen källtext nämner FRED (passerar)
- de 26 kurerade raderna är de som R21 läste, och filens SHA-256 är oförändrad (passerar)
- 2021 års formulering och 2026 års rubrik för helåret (passerar)
- textserierna väntar på publicering, tabellserierna publiceras (passerar)
- R21-1, R21-2, R21-3 och R21-4 (strikt xfail)

`python -m pytest -q tests/test_r21_kina_sec.py tests/test_china_sec.py`: 41 passerade, 4 xfail.
