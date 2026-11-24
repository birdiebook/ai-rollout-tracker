# R11 – granskning av revideringsindex och överraskningsindex (F1)

Granskningsspår R11, 2026-11-24, gren `auto14/r11-revideringar` från `auto13/f1-revideringar`. Granskat:
registerposten "F1: revideringar av guidance och överraskning mot guidance", `docs/resultat/f1_revideringar.md`,
`src/ai_tracker/series/guidance_revisions.py`, `src/ai_tracker/sources/tsmc_capex_guidance.py`,
`src/ai_tracker/state/expectations.py`, anropet i `snapshot.write`, `tests/test_guidance_revisions.py` och
`git log -p main..auto13/f1-revideringar`.

Underlag: den delade bastabellen (komponenterna är identiska rad för rad med F1:s egen tabell), F1:s
`tsmc_guid_capex_*` och `f1_*` ur spårets `data/`, den delade rå-cachen (1 314 TSMC-filer av typ 6-K), och
primärkällor som hämtades på nytt: 18 TSMC-dokument (6-K) 2004–2021 och pressmeddelandet 2022-10-13 på
www.sec.gov, Metas 8-K 2020-07-30 och 2020-10-29 (EX-99.1), Metas companyfacts och Nvidias submissions på
data.sec.gov, och 19 av Microsofts samtal (FY2022 Q3–FY2027 Q1) på microsoft.com. Blockerad värd:
`investor.tsmc.com` (proxyn nekar). Därför går TSMC:s egna samtal inte att kontrollera här.

Beräkningen gjordes om med F1:s kod. Resultatet stämmer med spårets siffror: 76 revideringar, 57 från 2020Q3, 29 med
storlek, och rullande 4 kvartal 2026Q4 = 0,67 (n 12: 4 upp, 8 oförändrade, 0 ned).

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering | **OK.** Registret committades före koden och resultaten och har inte ändrats. Hur antalet per kvartal beskrivs stämmer inte helt (R11-9) |
| 2. Microsofts sänkning (`msft-29`) | **Fel.** CSV:n saknar Microsofts siffra från samtalet 2026-07-29 (cirka 175 mdr på den smalare basen). Med den raden är `msft-29` en revidering nedåt på samma bas (−2,9), och 2026Q4 blir 0,62 (R11-1) |
| 3. Upprepningar som oförändrade | **Anmärkning.** Riktningarna drar indexet mot 0,5 (24 av 28 är oförändrade). Asymmetrin mot TSMC och Nvidia påverkar inte indexperioden (R11-6) |
| 4. Överraskningens bas | **OK enligt B2**, med anmärkning: valutan står för en stor del av TSMC:s överraskning, och den går att skilja ut med samma 6-K (R11-7) |
| 5. Läckage | **OK.** Fjorton datum på verklig data ger identiska värden. Kodfel i ett kantfall: stängningsversionen skrivs på kvartalets sista dag, inte när dagen har passerat (R11-2). Cachen tar inte hänsyn till CSV:n (R11-3) |
| 6. TSMC:s capex-budget | **OK inom den registrerade formen.** 18 dokument på sec.gov: inga falska positiva, två falska negativa före 2016. Dokumentationen överdriver täckningen efter 2021 (R11-8) |
| 7. Ögonblicksbilden | **OK.** Avsnittet påverkar inga grenar |
| Övrigt | Publiceringsgrinden för `guid_capex_*` kringgås (R11-4). Metas utsikt för 2020 saknas i indexperioden (R11-5) |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Metoden, dateringen och koden håller, och inget läckage hittades. Två
rättningar krävs före merge: R11-1, eftersom huvudvärdet och två påståenden i texterna är fel, och R11-2, som är en
rad kod. Övriga rättningar kan göras i samma spår.

## 1. Förregistrering – OK

Ordningen enligt git (2026-11-24, UTC):

| Tid | Commit | Innehåll |
|---|---|---|
| 19:20 | `dceec75` (main) | Basen |
| 20:22 | `b28905b` | Registerposten F1 |
| 20:28 | `b1e3c2e` | Kod och 44 syntetiska tester (1 307 rader) |
| 20:34 | `c4f3191` | Resultat på verklig data, källdokumentation, beslutslogg |
| 20:40, 20:47 | `6e28fa7`, `dcdc089` | Heltal i avsnittet, testantal i resultatet |

- `git diff b28905b HEAD -- docs/mattregister.md` är tom. Registret ändrades inte efter att värden räknats.
- Koden kom sex minuter efter registret, så den skrevs parallellt. Git visar bara att inga värden committades före
  20:28, inte att inga räknades lokalt. Spårets data har bara datum, inte klockslag. Inget tyder på att index
  räknades före posten.
- Det som var synligt står i posten: CSV:ns värden, antal per kvartal och TSMC:s capex-meningar. Att CSV:ns värden var
  synliga betyder att `msft-29` (190 → 170 mdr, med noten "lowered") var känd när brottslistan skrevs. Det behandlas i
  punkt 2.
- **Anmärkning (R11-9).** Posten säger att fönstret valdes ur "antalet uttalanden per kvartal ... 0–5 per kvartal,
  färre än 3 i 14 av 24". Det stämmer inte för CSV:ns rader (1–9 per kvartal, färre än 3 i 8). Det stämmer ungefär
  för uttalanden som har ett tidigare uttalande i samma kedja (0–5, färre än 3 i 15). Det är indexets nämnare, utan
  riktning, så valet beror inte på utfallet. Texten bör säga vad som räknades.

## 2. Microsofts sänkning för 2026 (`msft-29`) – fel

**Vad F1 gör.** Brottslistan har bara `msft-29`. Raden startar ett nytt objekt och jämförs därför inte med `msft-26`
(cirka 190 mdr, 2026-04-29). Det tar bort den enda revideringen nedåt sedan 2024. Rullande 2026Q4 blir 0,67 i stället
för 0,62.

**Är undantaget tvingat av tidigare text?** Delvis, men inte i den form F1 valde.
- R5-F14 (`docs/granskning/r5_extraktion.md`) säger att samtalet 2026-07-29 (#225–227) gör fler datacenterhyror
  operationella, och att det "bör noteras som ett definitionsbrott". R5:s rättning lade in `msft-29` som "ny version
  av samma serie som `msft-26`", med en not. R5 delade alltså inte serien.
- CSV:ns not på `msft-29` säger "definition break; R5-F14". Att ett brott finns är alltså dokumenterat före F1.
- Regeln "brott = nytt objekt, ingen revidering" och att brottet läggs på `msft-29` är F1:s eget val. Det gjordes med
  värdet synligt. Registret säger att värdena var synliga, men inte att regeln tar bort den enda sänkningen.
  Beslutsloggen och resultatet redovisar det i efterhand (0,62 utan regeln). Det är öppet redovisat, men inte tvingat.

**Primärkällan avgör frågan.** Samtalet 2026-07-29 (microsoft.com, FY2026 Q4) lästes om med
`guidance_capex.sentences`. Meningsnumren stämmer med CSV:ns lokaliserare (`msft-27` #280, `msft-28` #239).
- #225–226: nyttjandeperioden ändras, och fler framtida datacenterhyror blir operationella i stället för finansiella.
- #227 (SHA-256 `02300381…`): utan effekten av ändringen är förväntningen för kalenderåret 2026 **oförändrad**.
- #228 (SHA-256 `d8cfaeea…a9bb5a84`): skiftet justerar förväntningen till **cirka 175 mdr**. Meningen nämner inte
  capex, och det förklarar troligen varför E1:s kandidaturval missade den.
- 2026-10-28, #226 (SHA-256 `c12864f5…`, `msft-29`): cirka **170 mdr**, och skälet är förseningar hos
  tredjepartsleverantörer.

Brottet ligger alltså mellan `msft-26` (190, gammal bas) och julisiffran (175, ny bas). Bolaget kvantifierade själv
brottet (−15 mdr) och sa att planen i övrigt var oförändrad. Oktobersiffran (170) är på samma bas som julisiffran.
Sänkningen med 5 mdr är en verklig revidering nedåt, −2,9 (100 × ln 170/175). Resultatets mening "de två delarna går
inte att skilja åt" är fel, och "ingen revidering nedåt sedan 2024-01" gäller bara för den ofullständiga CSV:n.

**Med raden och F1:s egen allmänna regel** ("en rad med ett dokumenterat brott mot föregående rad startar ett nytt
objekt") startar julisiffran det nya objektet, och `msft-29` jämförs med den:

| Mått, 2026Q4 | F1 i dag | Rättat (R11-1) | Brottet ignoreras |
|---|---|---|---|
| Rullande 4 kvartal | 0,67 (n 12: 4/8/0) | **0,62** (n 13: 4/8/1) | 0,62 (n 13: 4/8/1) |
| Medianrevidering, 4 kvartal | +1,8 (5 med storlek) | +1,8 (6) | +1,8 (6) |
| Kvartalet | inget (n 2) | **0,50** (n 3: 1/1/1) | 0,50 (n 3) |
| Medianrevidering, kvartalet | +1,8 (1) | −0,5 (2) | −4,7 (2) |
| Microsofts storlek | – | −2,9 | −11,1 |

Övriga kvartal ändras inte. Genomgången av alla 19 samtal i CSV:ns Microsoft-täckning (FY2022 Q3–FY2027 Q1) hittade
ingen annan saknad siffra för capex. Meningen #227 är en upprepning på den gamla basen utan siffra. Den bör inte
kodas som 190, eftersom CSV:n bara kodar siffror som sägs.

**Rekommendation.** Huvudmått: julisiffran läggs till och brottet flyttas till den (R11-1). Det ger 0,62. Känslighet:
"brottet ignoreras" (−11,1 mot 190) och F1:s nuvarande variant (0,67) redovisas bredvid, med skälet. Avsnittet
`expectations` bör dessutom lista uttalanden som ett brott håller utanför jämförelsen, med storleken mot det senaste
uttalandet före brottet. Då kan en brottsregel aldrig dölja en sänkning.

## 3. Upprepningar som oförändrade – anmärkning

Uppdraget (`docs/riktning.md`, förslag 2) talar om mittpunkter och andelen uppåt "som i PMI". F1 räknar dessutom
riktningar och upprepade besked som händelser. Det står i registret. Effekten i indexperioden (57 händelser):

| Typ | Uppåt | Oförändrad | Nedåt |
|---|---|---|---|
| Siffror (29) | 17 | 6 (exakta upprepningar) | 6 |
| Riktningar (28) | 4 | **24** | 0 |

Riktningarna kommer från Amazon (11), Alphabet (9), Microsoft (5) och Meta (3). En upprepad kod som "ökar mot förra
året" säger inget om nivån. Alphabets siffra för 2025 steg från 75 till 85 och 92 mdr, medan riktningskoden för samma
år stod still i tre rapporter. Varje sådan händelse drar indexet mot 0,5. D − 0,5 = (upp − ned) / (2n), så de oförändrade späder ut avvikelsen.

Rullande 4 kvartal, efter R11-1:

| Kvartal | Alla | Bara siffror | Bara riktningar |
|---|---|---|---|
| 2024Q3 | 0,68 (n 11) | 0,75 (n 4) | 0,64 (5 av 7 oförändrade) |
| 2024Q4–2026Q1 | 0,68–0,73 | **1,00** (n 3–5) | 0,55–0,61 |
| 2026Q2–Q3 | 0,70–0,71 | 0,92–0,93 | 0,55–0,56 |
| 2026Q4 | 0,62 (n 13) | 0,75 (n 6: 4/1/1) | 0,50 (7 av 7 oförändrade) |

Det publicerade indexet visar alltså en måttlig övervikt uppåt. Men av de 14 revideringarna med siffra 2024-01 –
2026-10 var 13 uppåt och en oförändrad (Amazon 2026-04), och ingen nedåt före Microsofts sänkning. Det är inte fel enligt registret, men en läsare ser bara 0,67 och n. Antalet
uppåt och nedåt finns i avsnittet men inte i någon katalogserie.

**Asymmetrin mot TSMC och Nvidia.** CSV:n ger en händelse per rapport, medan TSMC:s och Nvidias tabeller bara har
nya vintages när värdet ändras.
- I indexperioden saknar asymmetrin effekt. Alla TSMC-filer från 2016 lästes: capex-budgeten står bara i januari och
  vid ändringar (2016-07, 2017-10, 2018-04, 2019-10, 2020-07, 2021-04), och den upprepas aldrig oförändrad. Nvidia
  har inga uppdateringar mitt i kvartalet.
- Före 2016 upprepar TSMC budgeten i cirka tio rapporter (till exempel 2004-10, 2005-04/07/10, 2006-04/07,
  2007-04/07, 2008-04 och 2013-03). De blir inga händelser, men de hade varit oförändrade händelser med CSV:ns regel.
  TSMC:s capex-händelser (14 under 2004–2021, 10 upp och 4 ned) är därför bara ändringar. Det ligger utanför indexet men syns i
  `events_per_company_year`.

## 4. Överraskningens bas – OK enligt B2

- **TSMC.** G följer `n2.quarter_guidance` (B2): NT$-mittpunkten till och med 2017Q2, därefter US$-mittpunkten
  gånger antagen kurs, känd dagen före utfallet. U är summan av kvartalets tre första månadsversioner, känd när den
  sista månaden är känd. Inget G är känt samma dag som eller efter U (alla 82 kvartal).
- **Valutan.** Den kvartalsintäkt i US$ som resultatet säger saknas står i varje kvartalsrapport i 6-K och går att
  tolka på samma sätt som capex-budgeten. För 2017Q3–2026Q3 (37 kvartal) gav det: SD för s i NT$ 1,97, SD för
  valutadelen 1,31, korrelation mellan s i NT$ och s i US$ 0,75. 2025Q2 är −0,2 i NT$ men +4,3 i US$, och 2025Q3
  +5,2 mot +2,1. TSMC:s z, och därmed överraskningsindexet, mäter alltså till stor del kursens avvikelse från
  antagandet. B2:s bas är rätt för N2, eftersom målet är i NT$. För "utfall mot egen guidance" är den guidade storheten
  intäkten i US$. Påståendet "kan inte skiljas ut med våra serier" är vilseledande (R11-7).
- **Nvidia.** U är `rev_nvda` (första version), daterad med 10-Q:n, som i B3. Sedan 2024Q2 lämnas 10-Q samma dag som
  8-K. 2017–2024 kom den 5–30 dagar senare i 11 kvartal. Dateringen är alltså konservativ, aldrig tidig. G är 8-K:ns
  mittpunkt för kvartalet, känd 84–121 dagar före. För 2026Q3 finns 8-K:n 2026-11-17 men ingen 10-Q ännu (kontrollerat
  i Nvidias submissions), så resultatets mening om det stämmer.
- **Meta och Alphabet.** U är summan av årets fyra första kvartalsversioner. Den är lika med årets första
  publicerade siffra i 10-K. Kontrollerat i companyfacts: Metas köp av anläggningstillgångar 2021 var 18 567 i
  första 10-K (senare 18 690) och 2023 27 266 (senare 27 045). F1 använder de första värdena. G är den sista
  guidancen före U, alltså oktober. Överraskningen blir liten, som resultatet säger.
- **Metas z** bygger på fyra tidigare år. En SD ur fyra värden är mycket osäker, så z = 1,90 för 2025 bör läsas med
  det förbehållet (R11-10).

## 5. Läckage – OK, med ett kodfel i ett kantfall

- **Trunkering på verklig data.** Alla tolv F1-serier räknades på nytt med bara det som var känt på 14 datum
  (2020-12-31, 2021-06-30, 2022-03-31, 2022-11-15, 2023-09-30, 2024-06-30, 2024-12-31, 2025-06-30, 2026-01-31,
  2026-06-30, 2026-07-30, 2026-09-30, 2026-10-28 och 2026-10-31). as_of och alla versioner till och med datumet är
  identiska: 0 avvikelser. Fem av datumen ligger nu som test.
- **Inget framåtdaterat.** Den senaste versionen i F1:s serier är daterad 2026-10-29. Ingen version har ett datum
  efter sin beräkningsdag.
- **Stängningsversionen (R11-2).** Registret säger en version "vid kvartalets sista dag om kvartalet ännu saknar
  version och dagen har passerat". Koden använder `end <= today`, så versionen skrivs redan på dagen. Det gäller i
  verklig data två kvartal (2020Q4 och 2025Q1, rullande 2025Q1 = 0,71). Det blir inget läckage: versionen bygger
  bara på händelser daterade till och med dagen, och lagret registrerar ett nytt värde för samma datum som en
  revision daterad till hämtningsdagen. Men koden följer inte registrets text.
- **`date.today()`.** Hämtningen använder lokal tid och ögonblicksbilden `utc_today()`. I CI är de lika. Notering.
- **Cachen (R11-3).** Cachens nyckel är tabellens längd, senaste datum, värdesumma och dagens datum, men inte CSV:n.
  Om CSV:n ändras i samma process ger hämtningen gamla värden. Veckojobbet ändrar inte CSV:n under körningen, men
  tester kan bli beroende av ordningen.

## 6. TSMC:s capex-budget – OK inom den registrerade formen

**Stickprov mot sec.gov** (18 dokument hämtade på nytt, jämförda med F1:s träffar):

| Inlämnad | Dokument | I 6-K | F1 | Dom |
|---|---|---|---|---|
| 2004-01-30 | d6k.htm | 2004, cirka 2,0 mdr | approx 2 000 | rätt |
| 2004-07-30 | u99171e6vk.htm | 2004, cirka 2,4 mdr | 2 400 | rätt |
| 2006-10-27 | h00832e6vk.htm | 2006, cirka 2,6 mdr | 2 600 | rätt |
| 2008-01-31 | h01850e6vk.htm | 2008, cirka 1,8 mdr | 1 800 | rätt |
| 2009-04-30 | h03306e6vk.htm | 2009, cirka 1,5 mdr | 1 500 | rätt |
| 2009-07-30 | h03544e6vk.htm | 2009, cirka 2,3 mdr, efter två andra belopp i samma mening | ingen träff | falskt negativ, vintagen kommer dagen efter |
| 2009-10-30 | h03742e6vk.htm | 2009, höjd till cirka 2,7 mdr | 2 700 | rätt |
| 2010-01-28 | h03949e6vk.htm | 2010, cirka 4,8 mdr | 4 800 | rätt |
| 2010-04-27 | h04174e6vk.htm | ingen utsikt | – | rätt |
| 2011-01-27 | h04795e6vk.htm | 2011, cirka 7,8 mdr | 7 800 | rätt |
| 2012-01-18 | d284938d6k.htm | 2012, cirka 6 mdr | 6 000 | rätt |
| 2012-04-26 | d341481d6k.htm | 2012 höjd till intervallet 8–8,5 mdr, utan verb och kvalificerare före beloppet | ingen träff | utanför formen, en höjning saknas |
| 2013-04-18 | d524997d6k.htm | 2013, 9,5–10 mdr | 9 500–10 000 | rätt |
| 2015-04-16 | d912667d6k.htm | 2015, 10,5–11 mdr | 10 500–11 000 | rätt |
| 2015-10-15 | d189650d6k.htm | 2015, cirka 8 mdr | 8 000 | rätt |
| 2016-10-13 | d256764d6k.htm | "slightly above" 9,5 mdr | ingen träff | registrerat undantag |
| 2019-10-17 | tsm-ex991_6.htm | 2019, 14–15 mdr | 14 000–15 000 | rätt |
| 2021-04-15 | tsm-ex991_6.htm | 2021, cirka 30 mdr | 30 000 | rätt |

**Hela cachen** (1 314 filer): alla 56 träffar har inlämningsåret som år, så regeln om nästa år används aldrig och
ger inga falska positiva. Från 2016 är tolkningen fullständig mot texten, med det registrerade undantaget 2016-10-13.
Före 2016 finns, utöver de två ovan:
- **2003**, alla utsagor: formerna "capex in 2003", kolon i stället för verb, "near the mid point" och "approach".
  Serien börjar 2004.
- **2009-07-30** ligger nära den registrerade formen, men koden tillåter inget belopp mellan subjekt och verb. Den
  regeln står inte i registret. Effekten är att höjningen dateras en dag sent, alltså konservativt.
- **2012-04-26** är en höjning med cirka +32 som saknas helt. TSMC:s tabell per år saknar därför 2012.

**Efter 2021 (R11-8).** Från 2022 står bara januaribudgeten i 6-K. Pressmeddelandet 2022-10-13 kontrollerades på
sec.gov och saknar capex-utsikt. Enligt allmän rapportering ändrade TSMC budgeten i samtalen 2022 och 2023, men det
gick inte att verifiera här (`investor.tsmc.com` nekas). Resultatets mening "från 2016 står budgeten i
pressmeddelandet i januari och när den ändras" stämmer för 2016–2021 men inte efter. `docs/kallor/guidance.md` har
förbehållet, resultatet saknar det. TSMC bidrar därför med noll revideringar efter 2021. Det betyder att källan
saknas, inte att planen var oförändrad.

## 7. Ögonblicksbilden – OK

- `snapshot.write` lägger till `expectations` efter `build`. Grenarna räknas bara ur `CORE_SERIES`, och inget
  `f1_*` finns där (F1:s test). Ett nytt test visar att `write` ger samma `branches` som `build`, att bara nyckeln
  `expectations` tillkommer och att indatatabellen inte ändras.
- `safe_section` sparar ett fel i avsnittet och låter ögonblicksbilden skrivas. `in_diffusion` är alltid falskt.
- På verklig data (2026-10-31) byggs avsnittet utan fel. Det visar rullande 2026Q4 = 0,67 och
  `definition_breaks: ["msft-29"]`, men inte vad brottet tog bort (punkt 2).
- Veckojobbet: F1:s serier hämtas efter sina komponenter. Med F1:s rader i tabellen passerar datatesterna, och inga
  F1-serier är inaktuella.

## Övrigt

- **Publiceringsgrinden (R11-4).** `guid_capex_*` har `publish=False` "tills granskningen är gjord"
  (`docs/kallor/guidance.md`), och R5 lät dem vara så. F1 läser samma värden direkt ur CSV:n och listar inte
  `guid_capex_*` bland komponenterna, så katalogens regel "publish=True kräver publicerbara komponenter" slår inte
  till. `f1_surprise_meta_capex` och `f1_surprise_googl_capex` avslöjar G exakt (G = U × e^(−s/100), och U är
  publicerat). Licensen är inte problemet, bara grinden.
- **Metas utsikt för 2020 (R11-5).** Metas 8-K 2020-07-30 säger cirka 16 mdr för 2020 (i toppen av det tidigare
  intervallet 14–16), och 8-K 2020-10-29 upprepar cirka 16 mdr som oförändrat. Båda saknas i CSV:n fast E1 läste
  dokument från 2020-07. R2 hittade oktoberraden men behövde den inte för B2. För F1 ligger de i indexperioden:
  rullande 2021Q1 får ett värde (0,67, n 3) och 2021Q2 blir 0,60 i stället för 0,625.
- **Samma bolag och år i två kedjor (R11-10).** Alphabets och Metas siffror och riktningar för samma år är olika
  objekt, så ett och samma rapporttillfälle kan ge två händelser. Det står inte i resultatet.

## Rättningar

| # | Allvar | Var | Rättning |
|---|---|---|---|
| R11-1 | måste | `curated/guidance_capex.csv`, `DEFINITION_BREAKS`, registret, resultatet, beslutsloggen | Lägg till Microsoft CY2026 approx 175 000, filed 2026-07-29, samtalet FY2026 Q4, mening #228, SHA-256 `d8cfaeea2501c1ee5624a917d9860500ddae5d4a279a838f647d23e5a9bb5a84`, not om den nya basen och #227. En ny daterad registerpost flyttar brottet R5-F14 från `msft-29` till den nya raden, med skälet (primärkällan). Då är `msft-29` en revidering nedåt (−2,9). Huvudvärde 2026Q4: 0,62 (n 13), kvartalet 0,50 (n 3). Stryk "går inte att skilja åt" och "ingen revidering nedåt sedan 2024-01". Redovisa "brottet ignoreras" och F1:s nuvarande variant som känslighet. Låt `expectations` lista uttalanden som ett brott håller utanför. Bredda E1:s kandidaturval till meningen efter en capex-mening. Två strikta xfail-test slår om |
| R11-2 | måste | `revision_index` | `end <= today` → `end < today`, som registret säger. Skriv i `expectations` att avsnittet är lika med as_of(när), utom en stängningsversion daterad samma dag, som skapas dagen efter. Strikt xfail-test |
| R11-3 | not | `_fetch` | Ta med CSV:n i cachens nyckel, till exempel filens SHA-256. Strikt xfail-test |
| R11-4 | bör | katalogen | Gör beroendet av CSV:n synligt: lista `guid_capex_*` som komponenter i de F1-serier som bygger på CSV:n (indexen, `f1_surprise_meta_capex`, `f1_surprise_googl_capex`, `f1_surprise_index`). Rekommendation: `publish=False` på dem tills ägaren beslutar om `guid_capex_meta/googl`, som är granskade i R2 och R5. Strikt xfail-test |
| R11-5 | bör | `curated/guidance_capex.csv` | Lägg till Meta CY2020 approx 16 000 från 8-K 2020-07-30 och 2020-10-29 (EX-99.1, Item 2.02), med SHA-256 och plats som övriga rader. Strikt xfail-test |
| R11-6 | bör | registret (känslighet), resultatet, `expectations` | Redovisa indexet med bara siffror bredvid huvudmåttet (registreras som känslighet, inte som nytt huvudmått), och antalet uppåt och nedåt som serier eller i noten. Skriv att 24 av 28 riktningshändelser är oförändrade och att TSMC:s tabell före 2016 bara har ändringar |
| R11-7 | bör | resultatet, registret | Stryk "kan inte skiljas ut". Registrera en känslighet i US$ från 2017Q3 med intäkten i US$ ur samma 6-K, och redovisa valutadelen (SD 1,3 av 2,0, teckenbyte 2025Q2) |
| R11-8 | bör | resultatet, `docs/kallor/guidance.md` | Skriv att 6-K efter 2021 bara har januaribudgeten och att TSMC därför inte ger några revideringar efter 2021. Lista de kända okodade utsagorna 2003–2015 (2003, 2009-07-30 en dag sent, 2012-04-26 +32) och regeln om belopp mellan subjekt och verb |
| R11-9 | not | resultatet | Skriv vad antalet per kvartal i posten räknade (uttalanden med ett tidigare uttalande i samma kedja) |
| R11-10 | not | resultatet | Nämn att Metas z bygger på fyra år, att Nvidias datering är konservativ (0–30 dagar), att två kedjor kan ge två händelser för samma rapport, och skillnaden `date.today()`/`utc_today()` |

## Tester

`tests/test_r11_revideringar.py` (inget nät):
- strikta xfail: julisiffran finns i CSV:n och `msft-29` är en revidering nedåt (R11-1), stängningsversionen väntar
  tills dagen har passerat (R11-2), hämtningen räknar om när CSV:n ändras (R11-3), F1-serier ur CSV:n följer
  grinden för `guid_capex_*` (R11-4), och Metas utsikt för 2020 finns (R11-5)
- passerar: as_of-trunkering på verklig data ger identiska serier (fem datum), guidance är känd före utfallet och z
  kräver fyra tidigare överraskningar, och ögonblicksbildens grenar beror inte på avsnittet

Alla sex xfail-test prövades mot simulerade rättningar i en kopia och slog då om (XPASS). Hela sviten: se
beslutsloggen och spårets slutrapport.
