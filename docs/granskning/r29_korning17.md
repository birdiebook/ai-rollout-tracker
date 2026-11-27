# R29 – oberoende granskning av körning 17 (S1, AN1, QA1, PV1)

Granskningsspår R29, 2026-11-27, gren `auto17/r29-korning17` (bas `auto17/integration17`, `3c71e70`). R29 har inte
skrivit koden, registerposterna eller rapporterna. Utgångspunkten var att ett påstående är fel tills det gick att visa
ur koden, registret, observationstabellen eller källdokumentet. Spårens egna dokument användes bara för att veta vad som
påstods.

Underlag: koden i `src/ai_tracker/followed/` (`common`, `kreditlagret`, `elflaskhalsen`, `ledtid`, `betalningsgapet`,
`prisvolym`), `sources/anthropic_gaap.py`, `series/anthropic_gaap.py`, `sources/acquisitions.py`, de fem
registerposterna 2026-11-27 i `docs/mattregister.md`, observationstabellen i huvudutcheckningen (876 serier, hämtad
2026-11-27), Anthropics fem prospekt (S-1, tre S-1/A och 424B4) och nio av Quantas 10-Q och 10-K, hämtade på nytt från
www.sec.gov med den generiska klientidentiteten ur miljön, en begäran i taget (inget 403 eller 429, inget sparat i den
delade cachen). Main (`0070cee`) kördes ur en `git archive`-kopia i R29:s scratch-katalog med samma delade data.
Ingen produktionskod och inga dokument från spåren är ändrade. Testerna står i `tests/test_r29_korning17.py`:
fastlåsta registerposter och värden som R29 läst i källan, egenskaper som håller, och fynden R29-2 till R29-5 som
`xfail(strict=True)`.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering | **OK i ordningen, en processavvikelse.** Varje registerpost är committad ensam och före kod och utslag, och texten är oförändrad genom mergarna. KL1:s låsta rapport är byte för byte densamma. S1 byter F0:s räkning av prövade ursprung, som X25 kallade ett beslut för Johannes, utan att ett sådant beslut finns loggat (R29-1) |
| 2. AN1 mot S-1 | **297 av 297 värden och 297 av 297 citat rätt** mot nyhämtade prospekt, läst med en egen tolkning (lxml) och inte med projektets radlista. `known_from` = inlämningsdatum, 75 av 75 observationsrader stämmer. GAAP och run-rate blandas inte i någon serie eller kvot. Summakontrollerna går ihop. En anmärkning om texten i BG1 (R29-6) |
| 3. QA1 mot 10-K/10-Q | **28 fakta lästa i texten, alla rätt, och 36 meningshashar rätt** på R29:s nyhämtade kopior. Kvartal *a* och riktning (upp vid *a*, *a* + 1, ned vid *a* + 4, *a* + 5) stämmer. Märkets text på historiska läsdagar är skriven i efterhand, och två angivna köpeskillingar saknas (R29-4). Ingen effekt på läsdagarna i rapporterna |
| 4. PV1 | **Regeln symmetrisk, aggregeringen inte.** Kvartalsmedlet av månadspriser är aritmetiskt, så en speglad prisbana ger inte den speglade förändringen i takt (R29-2). As-of-gränsen håller, frekvensaggregeringen stämmer med R29:s egen räkning, Cloudflare (`nej`) används inte och syns inte, gemensam orsak står som förbehåll, `main_inputs` stämmer och delas inte. Förbehållet om backfill saknas i rapporten (R29-3) |
| 5. Omräkning | **Rätt.** Minst ett utslag per spår räknat om direkt ur `observations.parquet` med pandas och numpy, utan projektets moduler. Alla stämmer på avrundningen |

*Rättning: X26 (`auto17/integration17`, registret 2026-11-27 X26) rättade R29-2 till R29-5 och R29-1 delvis (ägarbeslutet
kvarstod). Se "Rättat i X26" under varje fynd.*

*Ägarbeslut: B18 (registret 2026-11-27 B18) loggar Johannes tre beslut i avsnitt 7. R29-1 är stängt, PV1:s huvudläsning
är H-G (R29-2) och KL1 avgör sedda data per läsning (R29-7). Se "Stängt genom B18" och "Avgjort genom B18" nedan.*

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Inget must_fix. Fem should_fix (R29-1 till R29-5) och sex anmärkningar. Inget
fynd ändrar ett utslag eller ett värde per 2026-11-27 eller 2025-11-27. R29-2 och R29-3 bör rättas före PV1:s första
osedda läsning (npm-kvartalet 2026Q4, omkring 2027-01-05), R29-1 och R29-5 före Oracles inlämning omkring 2026-12-11.

## 1. Förregistrering

Ordningen i git (tider i UTC, `git log --graph`):

| Spår | Registerpost (bara `docs/mattregister.md`) | Första kod | Utslag eller rapport |
|---|---|---|---|
| S1 | `654cbc0` 09:58:13 | `af00592` 10:11:22 | `129c038` 10:20:15 |
| AN1 | `9a3cb34` 09:59:25 (tillägg `da32895` 10:08:16, efter extraktionen) | `2218edf` 10:08:16 | `67bd201` 10:19:46 |
| QA1 | `f2192fd` 10:23:41 | `2423dae` 10:34:47 | `5caba60` 10:42:40 |
| PV1 | `6ed50e2` 10:40:56 | `3f6eb55` 10:46:05 | `24c8c9e` 10:48:57 |

- R29 jämförde de rader som de fem registercommitarna lade till med det som `0070cee..HEAD` lägger till i registret.
  De är identiska, och inga rader är borttagna. Ingen annan commit rör registret (mergarna bär bara dessa rader).
- AN1:s tillägg är skrivet efter extraktionen och säger det. Det ändrar ingen post, period, datering eller användning.
  Det enda nya är undantaget `ABSENT` för förskotten i S-1, som inte gissar ett värde utan låter serien börja med
  S-1/A 2026-11-02. R29 kontrollerade att raden saknas i S-1:s kassaflödesanalys.
- PV1:s modul har senast ändrats 10:43, efter posten. R29 kan inte visa om något räknades före posten, men posten anger
  vad som var sett (avsnitt (f)), bland annat Arena-banan som gör bisak a beskrivande, och rapporten säger det.
- **KL1:s låsta del oförändrad.** `python -m ai_tracker.followed kreditlagret --as-of D` på main (`0070cee`) och i
  integrationen, D = 2026-11-25, 2026-11-26, 2026-11-27 och 2025-11-25: rapporten på main är för varje dag ett
  prefix av integrationens, alltså avsnitt 1–7 byte för byte, och S1:s avsnitt 8 kommer efter.
- **EL1:s låsta del.** Samma jämförelse för `elflaskhalsen` per 2026-11-25, 2026-11-26, 2026-11-27 och 2025-11-25: de
  åtta låsta raderna har samma utslag, ursprung och tal. Skillnaderna är talet för prövade ursprung (S1, punkt 3), en
  övergångsnotis per rad och den nionde raden efter de åtta. Elprisraden går från 213 till 27 av 267 prövade ursprung.
- **LT1 och BG1.** Per 2026-11-26 och 2025-11-26 är utfall, ursprung, *t* och alla historiktal utom det nya
  `n_tried` identiska på main och i integrationen (24 läsningar i LT1, 16 i BG1).
- **Gör koden det posterna säger?** S1: 18 KL1-S-rader med KL1:s gränser, *h* = 5, *k* = 2, tecken −; EL1-S med *g* = 10,
  *h* = 5, *k* = 2, tecken −; `n_tried` enligt punkt 3 (med impuls: utfallet är inte kan inte avgöras; utan impuls: Y
  känt i alla *k* kvartal), aldrig större än det gamla talet. AN1: tabeller, rader, tecken och dateringen enligt (b)–(d).
  QA1: kvartal *a* = slutdagens kalenderkvartal, perioder till periodens sista kvartal, ingen väsentlighetsgräns,
  märket från inlämningsdagen. PV1: *g* = 50, *h* = 20, *k* = 2, tecken −1, X:s förändring i takt, tre rader utan
  "eller", månader och veckor enligt (b). Avvikelser: R29-1 (process) och R29-4 (märkets text).

## 2. AN1 mot källan

R29 hämtade de fem prospekten själv och läste varje tabell med `lxml` (alla `<table>`, cellernas text, "$" och ")"
sammanslagna), utan projektets radlista och utan `ai_tracker`. Tabellerna identifierades på innehållet (kvartalsrubrik,
"(unaudited)", "Cash flows from operating activities", "Research and development(2)"), inte på rubriken.

- **Värden:** 297 av 297 rader i `curated/anthropic_gaap.csv` har samma värde som R29:s läsning av samma dokument,
  tabell, rad och kolumn, med tecknet vänt för capex och förskott som posten säger.
- **Citat:** alla 297 citat i spårets `data/raw/anthropic_gaap_quotes/quotes.json` har den SHA-256 som CSV:n anger, varje
  rad i citatet finns som en tabellrad i R29:s läsning av den nyhämtade kopian, och cellen på platsen är värdet.
- **known_from:** form, inlämningsdatum och accepteringstid för de fem accessionerna stämmer med EDGAR:s submissions.
  R29 byggde versionerna ur CSV:n med egen kod (första dokument, ny version bara vid ändrat värde, bruttoresultat inom
  samma dokument): 75 av 75 rader i observationstabellen har samma period, värde och `known_from`. Inget värde ändras
  mellan dokumenten. 2026Q3 och nio månader är kända från S-1/A 2026-11-02, allt annat från S-1 2026-10-26, förskotten
  från 2026-11-02.
- **Summor:** Q1–Q4 2025 = helåret, Q1 + Q2 = sex månader och Q1 + Q2 + Q3 = nio månader för 2025 och 2026, för intäkter
  (4 585, 33 242), compute (7 326, 18 808) och rörelseresultat (−8 060, −1 260), alla med skillnad 0.
- **GAAP och run-rate:** `lab_gaap_anthropic_*` och `lab_rev_anthropic_*` är skilda serier. BG1:s kvartalstabell visar
  intäkt, intäkt × 4 och, i en egen kolumn, den senaste run-rate som var känd vid kvartalets slut. Ingen kvot eller summa
  blandar dem. Run-rate-kolumnen följer as-of: per 2025Q4 visas 7,0 mdr per 2025-10-21, inte 9,0 mdr per 2025-12-31
  som blev känt först 2026-04-06.
- Klass `ja` (SEC, public domain), `publish=False`, gränserna för aktualitet och de godtagna luckorna i hittills-i-år
  stämmer med posten.

## 3. QA1 mot Quantas inlämningar

R29 hämtade 10-Q för 2023Q3, 2024Q2, 2024Q3, 2025Q2, 2025Q3, 2026Q1, 2026Q2, 2026Q3 och 10-K för 2025 och läste
texten (lxml, egen meningssökning). Inlämningsdatumen för alla 16 dokument stämmer med EDGAR.

| Vad | Rader (id) | Dom |
|---|---|---|
| Antal förvärvade bolag i perioden | `pwr-2023Q3-02` (4, nio mån 2023), `pwr-2024Q2-04` (5), `pwr-2024Q3-02` (8), `pwr-2025Q2-01` (4), `pwr-2025Q3-dsi-02` (5), `pwr-2025Q4-02` (8, 2025), `pwr-2026Q2-01` (3), `pwr-2026Q3-04` (5) | 8 av 8 rätt |
| Köpeskilling i tabellen (tusental USD) | `pwr-2023Q3-03` 622 474, `pwr-2024Q2-05` 540 168, `pwr-2024Q3-cei-02` 1 967 723, `pwr-2024Q3-03` 641 758, `pwr-2025Q2-02` 815 684, `pwr-2025Q3-dsi-03` 1 668 579, `pwr-2025Q3-dsi-04` 1 673 326, `pwr-2025Q4-03` 2 471 057, `pwr-2024Q3-cei-04` 2 035 230, `pwr-2026Q2-03` 1 430 107, `pwr-2026Q3-05` 1 799 666 | 11 av 11 rätt |
| Köpeskilling i text | `pwr-2023Q4-02` (cirka 300 MUSD) | rätt |
| Slutdagar | `pwr-2024Q3-cei-01` (Cupertino 2024-07-17), `pwr-2025Q3-dsi-01` (Dynamic Systems 2025-07-25), `pwr-2025Q4-01` (2025-11-14 och 2025-12-09, tre förvärv), `pwr-2026Q2-02` (2026-06-18, två), `pwr-2026Q3-03` (2026-07-10, 08-31, 09-11), `pwr-2026Q4-02` (2026-10-14) | 6 av 6 rätt |
| Inga förvärv | `pwr-2026Q1-01` ("no acquisitions completed in the three months ended March 31, 2026") | rätt |
| Följande händelser | `pwr-2026Q3-01` (tungindustriell entreprenör efter 2026-06-30), `pwr-2026Q4-01` (stolptillverkare efter 2026-09-30) | rätt |

Med projektets meningsdelning på R29:s nyhämtade kopior har 36 av 36 rader i de nio dokumenten rätt SHA-256 på platsen,
och de sparade meningarna i spårets `data/raw` har samma hash. De övriga 17 raderna ligger i dokument som R29 inte
hämtade (självkontrollen i spåret säger 53 av 53).

**Kvartal och riktning.** Händelserna per kvartal bildas ur skillnaden mellan periodernas antal (till exempel fyra på sex
månader 2025 minus två i första kvartalet = två i 2025Q2), och *a* är kvartalet där de nya bolagen tillkom. Ett förvärv
ger ett nivåsteg i RPO vid kvartalets slut, så takten stiger i *a* … *a* + 3 och förändringen i takt (mot två kvartal
tidigare) stiger vid *a* och *a* + 1 och faller vid *a* + 4 och *a* + 5. Koden gör det. Märket läser bara förvärv vars
första dokument var inlämnat på läsdagen (`marks(c, when)`). R29 räknade om beskrivningarna: tillförd RPO från 2026Q1
som tar huvudläsningens X vid 2026Q2 under 10 är 3 613 MUSD (dokumentet: cirka 3,6 mdr), och för "L1 efter K-inre"
4 540 MUSD (cirka 4,5 mdr).

## 4. PV1

- **Regeln** är F0:s, oförändrad, och R28 visade att den är symmetrisk. På riktiga data ger priset speglat (1/*x*, Y
  oförändrat) att bisak a:s två avgjorda ursprung byter från "talar emot, uppåt" till "talar för, nedåt", och
  impulserna upp och ned byter plats.
- **Aggregeringen är inte symmetrisk (R29-2).** Kvartalsvärdet är det aritmetiska medlet av månaderna, och måttet är
  logaritmen av det. För en stegfunktion är log(medel(*x*)) inte −log(medel(1/*x*)). Arena-variant A:s förändring i takt
  är +441,0 och +346,0 vid 2025Q3 och 2025Q4, och för den speglade banan −424,6 och −232,4. I ett syntetiskt exempel (ett
  prissteg med faktor 4 i kvartalets sista månad) ger fallet +28,8, alltså ingen impuls, och den speglade höjningen
  −69,3, en impuls. Ett geometriskt medel (medel av log) är exakt symmetriskt och ger för Arena +433,7, +301,0, +0,1,
  −37,7 och 0,0, samma utslag i dag. GPQA-priset är också en stegfunktion (1,925, 1,075, 0,31, 0,20).
- **As-of-gränsen.** PV1 och LT1 per 2025-11-27, 2026-06-30 och 2026-08-01 ger samma rapport på hela tabellen och på
  tabellen kapad vid dagen.
- **Frekvensaggregeringen.** R29:s egen räkning (veckor till kvartalet där torsdagen ligger, bara hela kvartal, medel
  av veckosummorna; månader som medel av tre) ger samma nivåer, takter och förändringar i takt som rapporten (tabellen i
  avsnitt 5).
- **Backfill (R29-3).** Alla npm-rader är hämtade 2026-11-24–26 och prisraderna 2026-11-23 och 2026-11-25, med
  `known_from` satt efter en regel. Läsningen per 2025-11-27 kan alltså innehålla revideringar som inte var kända då.
  Källdokumentet säger "backfill", men rapportens förbehåll gör det inte (EL1 gör det för EIA-930).
- **Licens.** `g2_price_at_capability_gpqa` `ja`, Arena A `okänd`, npm `okänd` och `publish=False`, de härledda
  `pv1_*` tar den mest restriktiva klassen. Cloudflare (`g3_cf_*`, `nej`) finns inte i `used_series()`, inte i rapporten
  utom i förbehållet att den inte används, och följda frågor ingår inte i sidans paket (`site`, `site_bundle`).
- **Gemensam orsak** står som förbehåll i rapporten. **main_inputs** = `g2_price_at_capability_gpqa` mot
  `g3_npm_openai_w` + `g3_npm_anthropic_sdk_w`, och ingen annan frågas huvudläsning delar dem.

## 5. Oberoende omräkning

R29 skrev en egen beräkning (pandas och numpy, ingen import ur `ai_tracker`): senaste version per period med
`known_from` ≤ dagen, summor av komponenterna, capex över fyra kvartal, takt = 100 × (ln *v*(*t*) − ln *v*(*t* − 4)) och för
kvoter i procentenheter *v*(*t*) − *v*(*t* − 4), förändring i takt mot två kvartal tidigare, och en egen implementation
av F0:s regel.

| Spår | Storhet | R29 | Rapporten |
|---|---|---|---|
| S1 (EL1-S) | X = L1 förändring i takt 2026Q2, Y = K-inre 2026Q3, tecken − | +16,47 / +9,60, talar emot, uppåt | talar emot, uppåt |
| S1 (KL1-S) | Oracle (capex − OCF) / capex, takt 2026Q2, mot capex-takten 2026Q3 | +40,70 / −15,76, talar för, uppåt | +40,7 / −15,8, talar för, uppåt |
| S1 (KL1-S) | Inre lagret, samma mått | +40,02 / +9,60, talar emot, uppåt | +40,0, talar emot, uppåt |
| QA1 (LT1) | L1 2026Q3, förändring i takt 2026Q2 / 2026Q3 | 67 950; +16,47 / +16,91 | 67 950; +16,5 / +16,9 |
| QA1 (LT1) | Huvudläsningen L1 före K-inre, *k* = 2 | talar för (2026Q2 → 2026Q3) | talar för |
| QA1 (LT1) | Tillförd RPO som tar X under 10 / Y under 10 | 3 613 / 4 540 MUSD | cirka 3,6 / 4,5 mdr |
| AN1 (BG1) | Compute i procent av intäkten 2026Q3 | 9 863 / 16 956 = 58,2 % | 58,2 % |
| AN1 | Rörelseresultat 2026Q3 (nio minus sex månader och kvartalstabellen) | −567 | −0,6 mdr |
| PV1 | GPQA-pris 2026Q3, kvartalsmedel och takt | 0,2733 USD, −195,2, ingen förändring i takt | 0,2733, −195,2, – |
| PV1 | SDK-nedladdningar 2026Q3: nivå, takt, förändring i takt | 69,4 M/vecka, +216,2, +60,5 | 69,4, +216,2, +60,5 |
| PV1 | Arena A förändring i takt 2025Q3 … 2026Q3 | +441,0, +346,0, +3,0, −37,7, 0,0 | samma |
| PV1 | Bisak a per 2026-11-27 och historik | inget av mönstren; 2025Q3 och 2025Q4 talar emot, uppåt (Y +42,0, +44,9) | samma |
| PV1 | Bisak a per 2025-11-27; SDK 2025Q3 | kan inte avgöras; 8,0 M/vecka | samma |
| PV1 | Huvudläsningen och bisak b | kan inte avgöras (X saknar förändring i takt) | samma |

## 6. Fynd

### R29-1 (should_fix, S1): F0:s räkning är bytt utan loggat ägarbeslut

X25, punkt 4, säger uttryckligen att det är "beslut för Johannes" att byta F0:s räkning av hur ofta regeln kunde prövas,
eftersom det ändrar låsta poster, och beslutsloggen för körning 16 listar det som öppet (rekommendation: ja, som en egen
post). S1:s post gör bytet i punkt 3, med motivering och övergångsnotis, men varken posten, beslutsloggen eller
`docs/riktning.md` säger att Johannes har beslutat. Inga utfall ändras, och det gamla talet står bredvid, så skadan är
liten. Men talet syns i alla fyra frågornas rapporter (elpriset i EL1: 213 → 27 av 267), och en låst post ändrades av
ett spår på en rekommendation. **Rättning:** logga ägarbeslutet i beslutsloggen (eller, om körningens uppdrag var
beslutet, säg det i S1:s post med ett daterat tillägg). Inte testbart.

**Delvis rättat i X26** (punkt 1): processavvikelsen är loggad i registret och beslutsloggen, och övergångsnotisen i
varje rapport säger att bytet väntar på ägarens bekräftelse. Ett ägarbeslut kan inte loggas av ett spår, och inget
sådant finns i registret, beslutsloggen eller `docs/riktning.md`. Beslutet står kvar som öppet för Johannes
(rekommendation: bekräfta).

**Stängt genom B18** (registret 2026-11-27 B18, punkt 1, och beslutsloggen 2026-11-27): Johannes bekräftade S1:s räkning
2026-11-27. Tillägget "Bytet väntar på ägarens bekräftelse" är borttaget ur övergångsnotisen i varje rapport, och notisen
står kvar med båda talen enligt S1, punkt 3.

### R29-2 (should_fix, PV1): kvartalsmedlet bryter symmetrin

Se avsnitt 4. Måttet är log av ett aritmetiskt medel av månadspriser, så en prissänkning och en lika stor höjning i
log-skala ger olika förändring i takt. För Arena A skiljer det 114 log-punkter vid 2025Q4 (+346,0 mot −232,4). I dag
ändras inget utslag, men med *g* = 50 och prisserier som rör sig i steg kan riktningen avgöra om en impuls uppstår,
vilket strider mot regel 1 (inget val av riktning). Samma sak gäller veckomedlet för npm, i mindre grad. **Rättning:**
ett daterat tillägg till PV1 före den första osedda läsningen (omkring 2027-01-05) med kvartalsvärdet som geometriskt
medel (medel av log) som huvudmått, eller som en rad bredvid den låsta. Strikt xfail:
`test_pv1_mirrored_price_gives_the_mirrored_change_in_pace`.

**Rättat i X26** (registret 2026-11-27 X26, punkt 2, commit `07205d0` ensam före koden): tre rader H-G, a-G och b-G
bredvid de låsta, med kvartalet som geometriskt medel av månaderna och veckosummorna, i rapportens avsnitt 6 och som en
fakta i antennen. De låsta raderna och avsnitt 1–4 är oförändrade, och H är huvudläsning. Utslagen är desamma per
2026-11-27 och 2025-11-27 (Arena A +433,7, +301,0, +0,1, −37,7, 0,0). Testet är ett vanligt test på de geometriska
raderna, och den låsta formens asymmetri är fastlåst bredvid (+28,8 mot −69,3). Om H-G ska ersätta H är kvar som beslut
för Johannes före 2027-01-05.

**Avgjort genom B18** (registret 2026-11-27 B18, punkt 2): H-G är huvudläsningen, och a-G och b-G är bisakernas
redovisade form. H, a och b står kvar som låsta rader bredvid, i rapportens avsnitt 6 och som en fakta i antennen. Inga
utslag ändrades.

### R29-3 (should_fix, PV1): förbehållet om backfill saknas i rapporten

Se avsnitt 4. Läsningen per 2025-11-27 bygger på npm-värden som hämtades ett år senare. Rapporten säger "Bara data kända
på dagen" utan förbehåll. **Rättning:** ett förbehåll i avsnitt 5 som i EL1 ("Lasten är backfill"). Strikt xfail:
`test_pv1_report_says_the_history_is_a_backfill`.

**Rättat i X26** (punkt 3): förbehållet "Historiken är backfill" med hämtningsdatumen (2026-11-23–26) och antalet
använda rader som hämtades efter läsdagen (per 2025-11-27 alla, per 2026-11-27 inga). Testet är ett vanligt test.

### R29-4 (should_fix, QA1): märkets text på historiska läsdagar

1. **Etiketten är skriven i efterhand.** Varje händelse har en etikett, och `marks()` tar etiketten från den senaste
   raden som var känd på dagen, men alla rader har samma etikett. Per 2024-02-25 var bara 10-K för 2023 inlämnat (två
   förvärv i januari 2024, det tredje slöts 2024-03-01), men märket säger "Quanta, 3 förvärv 2024Q1". QA1, punkt 3,
   säger att den senaste uppgiften som var känd på läsdagen ska användas. (Per 2026-08-01 säger märket "2 förvärv
   2026Q3" på två rader ur samma 10-Q, en följande händelse och en slutdag. Om de är samma förvärv går inte att avgöra
   ur texten, så R29 räknar inte det som ett fynd.)
2. **Två angivna köpeskillingar saknas.** 10-Q för 2024Q2 (inlämnad 2024-08-01) anger Cupertinos köpeskilling till
   cirka 1,5 mdr USD, och 10-Q för 2025Q2 (2025-07-31) Dynamic Systems till cirka 1,35 mdr (före tilläggsköpeskilling).
   CSV:n har ingen rad för dem, så märket saknar köpeskilling fram till nästa 10-Q. Punkt 2 och 3 säger att
   köpeskillingen ska stå som den står och att båda raderna står i CSV:n.

Rapporterna per 2026-11-27 och 2025-11-27 påverkas inte (alla senare uppgifter var kända då), och märket ändrar inget
utslag. Det spelar roll för jämförelsen mot förra månaden och för rapporter som byggs om bakåt. **Rättning:** etikett
per rad (eller räkna antalet ur de rader som var kända), och två nya konsiderationsrader. Strikta xfail:
`test_qa1_label_states_only_what_was_filed_on_the_day`, `test_qa1_cupertino_has_its_first_stated_consideration`.

**Rättat i X26** (punkt 4 och 5): etiketten gäller per rad och säger vad som var inlämnat på radens dag (2024Q1 "2
förvärv" per 2024-02-25, 2024Q2 "1 förvärv" per 2024-05-02, "minst 1 förvärv" för 2026Q3 per 2026-07-30 och 2026Q4 per
2026-10-29), och `acquisitions.load` kräver samma etikett för samma händelse och dag. Två nya rader: Cupertino cirka 1
500 MUSD (10-Q 2024-08-01) och Dynamic Systems cirka 1 350 MUSD vid tillträdet (10-Q 2025-07-31), med accession, plats
och hash; de två och de sex omdöpta raderna kontrollerades mot ett nytt anrop till EDGAR (10 av 10 rätt). Per 2026-11-27
ändras bara texten för 2026Q4 i LT1:s märke. Testerna är vanliga tester.

### R29-5 (should_fix, S1 och integrationen): EL1-S säger att Quantas förvärv inte är kontrollerade

EL1-S:s rad (koden i `elflaskhalsen.py` och `docs/resultat/elflaskhalsen.md`, båda dagarna) säger "Quantas förvärv är
inte kontrollerade (R28-7)". QA1 kodade dem för 2023–2026 i samma körning, och integrationen behöll S1:s text. Raden
har samma X som LT1:s huvudläsning, där märket nu finns. **Rättning:** samma text som i LT1 (kodade från 2023, inte före),
gärna med en hänvisning till LT1:s märke. Strikt xfail: `test_el1s_text_does_not_say_quanta_is_unchecked`.

**Rättat i X26** (punkt 6): EL1-S säger att Quantas förvärv är kodade från 2023 (QA1), inte före, och att märket står i
LT1:s huvudläsning. Ingen märkning läggs till i EL1-S (S1, punkt 2). Testet är ett vanligt test.

### R29-6 (note, AN1 i BG1): texten om run-rate och tabellen

Texten säger att run-rate vid kvartalets slut i ett bolag som växer snabbt ligger över kvartalets intäkt × 4. Tabellen
visar motsatsen i fyra av fem rader (2026Q3: intäkt × 4 67,8 mdr, run-rate 47,0 mdr), eftersom kolumnen visar den
senaste run-rate som var känd vid kvartalets slut, ofta från månader tidigare (2026-05-28 för 2026Q3). Påståendet är
inte fel, men tabellen belägger det inte. Föreslås: säg att kolumnens datum ligger före kvartalets slut. Dessutom jämför
raden för kassaflödet hittills i år nio månader (2026Q3) med sex månader (2026Q2) som "före" utan att säga det.

### R29-7 (note, KL1): stycket om sedda data i den låsta delen

KL1:s låsta rapport per 2026-11-27 saknar stycket om sedda data, eftersom den avgör det av läsdagen. Resultatdokumentet
säger det i en rad överst, och S1 listar det som öppet för Johannes. Efter Oracles inlämning omkring 2026-12-11 blir
Oracles läsning osedd medan de andra fortfarande är sedda, och den låsta delen kan inte säga vilken som är vilken. R29
instämmer i S1:s rekommendation: en post som ger KL1 X25:s regel per läsning före 2026-12-11.

**Avgjort genom B18** (registret 2026-11-27 B18, punkt 3): KL1 avgör sedda data per läsning med X25:s mekanism och
registerdagen 2026-11-25. Per 2026-11-27 har avsnitt 4 stycket igen (alla fem läsningarna sedda), och det är den enda
skillnaden i avsnitt 1–7 mot rapporten före B18.

### R29-8 (note, AN1): budgeten för `withheld.json`

`docs/steg3/datakontrakt.md` säger att en kompaktare form är rätt åtgärd i första hand när en budget nås. AN1 höjde den
råa budgeten från 80 till 200 kB och lät gzip-budgeten stå kvar. Det är loggat som ett beslut för ägaren, och filen
innehåller bara namn och skäl (gate.py). Ingen läcka.

### R29-9 (note, QA1): köpeskilling för en period hittills i året

Märket för en period visar köpeskillingen för alla förvärv i perioden hittills i året: "2023Q1: 3 förvärv (587 MUSD, 3
mån 2023)" och "2023Q3: 1 förvärv (622 MUSD, 9 mån 2023)", där 622 innehåller de 587. Texten säger det, men den som
summerar märkena räknar dubbelt.

### R29-10 (note, PV1): datering av prisserierna

`g2_price_at_capability_gpqa` har `known_from` = månadens sista dag, Arena A månadsslut + 1. PV1 hittade det själv och
föreslår en ombyggnad. Ingen effekt på PV1:s kvartal. R29 instämmer.

### R29-11 (note, integrationen): inaktuell prosa i antennerna

`docs/resultat/antenner.md` säger i den handskrivna inledningen "Alla utslag per 2026-11-26 bygger på kvartal som var
sedda", medan rapporten nu står per 2026-11-27. Påståendet gäller fortfarande, men datumet bör följa med.

## 7. Beslut för Johannes

*Alla tre fattade 2026-11-27 enligt rekommendationerna (registret 2026-11-27 B18, beslutsloggen 2026-11-27).*

1. **F0:s räkning (R29-1):** bekräfta S1:s byte i efterhand, eller återställ det gamla talet som huvudtal.
   Rekommendation: bekräfta och logga, eftersom det nya talet är ärligare och det gamla står bredvid.
2. **PV1:s kvartalsmedel (R29-2):** geometriskt medel som ny rad bredvid den låsta, eller som ersättning före första
   osedda läsningen. Rekommendation: ersättning genom ett daterat tillägg före 2027-01-05, eftersom ingen läsning ännu
   har avgjorts på osedda data och den låsta formen bryter regel 1.
3. **KL1:s sedda data per läsning (R29-7):** samma rekommendation som S1, före 2026-12-11.
