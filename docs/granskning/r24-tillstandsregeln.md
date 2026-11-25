# R24 – granskning av testet av tillståndsregeln (T1)

Granskningsspår R24, 2026-11-25, gren `auto14k/r24-tillstandsregeln` (bas `auto14k/t1-tillstandsregeln`). Granskat:
registerposten "2026-11-25 – T1: test av tillståndsregeln" i `docs/mattregister.md`, `src/ai_tracker/state/evaluate.py`,
CLI-kommandot `python -m ai_tracker.state evaluate`, `tests/test_state_evaluate.py`,
`docs/resultat/t1_tillstandsregeln.md`, tilläggen i `docs/resultat/tillstand.md`, `docs/beslutslogg.md` och
`docs/agentkalibrering.md`, körloggen `experiments/runs/20261125T092201Z_t1_state_rule.csv` och T1:s resultatfil
`outputs/t1_tillstandsregeln.json` i T1:s arbetskatalog.

Underlag: den delade bastabellen (780 623 rader, senast ändrad 2026-11-25 08:56 UTC, före T1:s körning), git-historiken,
filtiderna i den delade kladdkatalogen och Fed:s sida för årsrevisionen av G.17 (federalreserve.gov, hämtad
2026-11-25). Inget annat hämtades. Inga värden skrevs till `data/`.

**Arbetssätt.** T1:s körning gjordes om med grenens kod. Resultatfilen blev byte för byte lika (3 min 10 s). Sedan
räknades delarna om med egen kod: "dagens data för m" byggd bokstavligt månad för månad (76 grenmånader), utfall och
persistens med egen taktberäkning (236 grenmånader och horisonter i G4–G7), blockpermutationen med egen kod och
eget frö, kappa, MDE och beslutsregeln. Handkontrollerna i resultatet räknades om från raderna.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering och ordning | **OK**, med en anmärkning om vad som var synligt (R24-4) |
| 2. Dagens data, utfall och läckage | **OK.** Inget värde används före det var känt. Tillståndsmotorn är oförändrad. Två noteringar (R24-5, R24-6) |
| 3. Blockpermutation, Holm och MDE | **OK.** Som registrerat. MDE stod i posten före koden |
| 4. Omräkning för hand | **OK.** Alla omräknade grenmånader stämmer, och handkontrollerna i resultatet stämmer |
| 5. Ordval och beslutsregeln | **Anmärkning.** Regeln är tillämpad mekaniskt och rätt. Två läsningar i resultatet behöver rättas (R24-1, R24-2) |
| 6. De syntetiska testerna | **Anmärkning.** Den tröga världen prövar egenskapen. Slumpvärlden gör det bara för sitt frö (R24-3) |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Inget läckage, inga felaktiga värden och ingen regel som avviker från posten.
Slutsatsen står sig: ingen granskning av regeln rekommenderas, och (b) är inte avgjort. Fyra rättningar av text och
tester behövs (R24-1 till R24-4). Den viktigaste är R24-1: vid 6 månader är persistensen samma jämförelse som
tillståndet, så likheten 35 mot 35,0 är byggd in i testet och inget fynd.

## 1. Förregistrering och ordning – OK, med anmärkning

Ordningen enligt git (alla 2026-11-25, UTC):

| Tid | Commit | Innehåll |
|---|---|---|
| 09:04:16 | – | Filen `bc_realtime.csv` skrivs i den delade kladdkatalogen (se nedan) |
| 09:08:13 | – | Utkastet till registerposten (`t1_entry.md`), samma text som den committade |
| 09:08:38 | `7b008b3` | Registerposten. Bara `docs/mattregister.md` ändras |
| 09:18:32 | `841f92b` | `evaluate.py`, CLI och syntetiska tester. Inga riktiga data |
| 09:22:01 | – | Körningen. Körloggen har `git_sha` `841f92b` utan `+dirty`, och resultatfilen har samma tid |
| 09:25:58 | `a593b09` | Resultat, beslutslogg, kalibrering. Ingen kod |
| 09:45:07 | `fbabbb7` | Parenteser kring tabellhuvuden i koden och "räknat per månad" i texten. Ingen logik ändras |

- `git diff 841f92b..HEAD -- src tests` ändrar bara tabellhuvudenas parenteser. Omkörningen med HEAD gav samma
  resultatfil som körningen med `841f92b`.
- Registerposten har allt som avgör: fönster, V, definitionerna i (a) och (b), persistens, blocklängd, antal
  permutationer, frö, Holm-familjen, minsta antal prediktioner, nedre svansen, MDE och beslutsregeln. Konstanterna
  i koden är desamma, och T1:s test jämför dem med posten.
- MDE räknades före testet och stämmer: 58 prediktioner (52 accelererar, 6 bromsar in) för h = 3 och 48 (44 och 4) för
  h = 6 med v2. Det ger 0,283 och 0,440. Med v1 är det 92 och 80, och 0,225 och 0,341.
- Tillståndsmotorn (`branch.py`, `measures.py`, `snapshot.py`, `register.py`) är oförändrad: diffen mot
  `claude/elegant-tesla-awd2sz` är tom för de filerna.

**Vad som var synligt före posten (R24-4).** Posten säger att bara antalet tillstånd per gren lästes ur
`snapshot.backcast`, "inte index eller serier per månad". Men `bc_realtime.csv` skrevs fyra minuter före posten. Den
har 306 rader, alltså 34 månader och 9 grenar, och tillstånden är identiska med T1:s realtidstillstånd i alla 306
rader (v1 och v2). Filen är alltså med stor sannolikhet T1:s. Den innehåller per månad tillstånd, index och
riktningen för varje räknad serie. Det är mer än antalen. Vid h = 6 är seriernas riktning vid m + 6 i stort sett
utfallet: i G3–G7 och G9 har den samma tecken som seriens utfall i 776 fall och motsatt tecken i 14, och den är 0
(inom dödbandet) i 323. Riktningen vid m är persistensen (punkt 5). Det går inte att veta om T1 läste mer än antalen. Valen som
filen kunde ha påverkat är få: horisonterna, blocklängden och beslutsregelns nivåer. Kappanivån och nivån för hårda
byten gäller (a), som filen inte visar. Ändå ska resultatet säga vilken fil som fanns och vad den innehöll.

## 2. Dagens data, utfall och läckage – OK

**Dagens data för m.** `revised_table` ger en rad per serie och period: värdet och källan från den senaste raden
med `known_from` ≤ V, och `known_from` = periodens första `known_from`. Det är samma sak som posten säger. Kontroller:
- Bokstavlig konstruktion, en tabell per månad (perioder med en rad känd vid m, senaste värde känt vid V,
  `known_from` = m). Tillstånden blev desamma som T1:s reviderade i 76 av 76 grenmånader: G3–G7 och G9 i tio månader
  (2024-05, 2024-09, 2024-11, 2025-06, 2025-07, 2025-10, 2025-12, 2026-03, 2026-07, 2026-10) och G1, G2 och G8 i fyra.
  Det täcker den härledda `capex_ocf_hyp4`, BTOS-regimerna, veckoserierna i G3 och Indeeds dagsserier i G8.
- Syntetiskt test med en härledd kvot där båda komponenterna revideras, en veckoserie och en månadsserie: hela
  posterna är lika (passerar). Rader kända efter V påverkar inte (passerar).
- **Spärren för bakåtfyllda serier.** Alla fyra spärrade serier har bara `backfill`-rader. Egna månader är 0 i båda
  tabellerna i hela fönstret, så spärren påverkar inget här. Men räkningen på den reviderade tabellen är skör (R24-5):
  när en bakåtfylld historik senare revideras av egna rader får perioderna källan från den nya raden och datumet från
  den gamla. Då ser historiken ut som gamla egna ögonblicksbilder, och spärren öppnas i dagens data men inte i realtid.
  Ett syntetiskt test visar det, och att körningen redovisar det (`gated_counted_months`), som posten kräver.

**Utfallet.** Takten vid P_m och vid P_t läses båda ur versionen vid t = m + h, med `measure_path`. Persistensen läser
versionen vid m och P_{m−h}. Kontroller:
- Egen taktberäkning (log ×100 över ett år, procentenheter för kvoten) gav samma utfall och persistens, med v1 och v2,
  i 236 av 236 grenmånader och horisonter i G4–G7. P_m var samma som motorns i alla serier.
- T1:s test kapar tabellen vid m + h och lägger in vilda revideringar dagen efter. Det täcker utfallet. Ett nytt test
  kapar vid m och visar att persistensen inte läser något efter m (passerar).
- Tecknet för fördubblingstid: ett syntetiskt G1-flöde där fördubblingstiden blir kortare ger u = +1, och tvärtom
  (passerar).
- Tillståndet vid m läser bara `as_of(m)`. Inga utfall finns i tillståndet.

**Revideringarna i G6 (R24-6).** Bara Fed G.17 har ändrade värden i G6: `us_ip_semis_m` och `us_ip_computers_m` i 34 av
34 månader. TSMC, ASML och Broadcom har flera rader, men inget värde som var känt vid m har ändrats. Ändringarna kommer
från en enda version, G.17:s årsrevision 2026-11-24, en dag före V. Den byter basår till 2022 och ändrar alla 657
perioder som var kända 2026-10-31. Datumet och basåret stämmer med Fed:s sida ("The 2026 Annual Revision",
"Release Date: November 24, 2026", "an update of the base year to 2022"). Två följder: G6:s resultat i (a) hade sett annorlunda ut med V en dag
tidigare, och exponeringen räknar basårsbytet som en revidering i varje månad, också där tillväxttalen inte ändras.

## 3. Blockpermutation, Holm och MDE – OK

- Blocken är 6 månader från fönstrets början inom varje gren, och sista blocket kan vara kortare. Prediktionerna
  flyttas och utfallen ligger kvar. p = (1 + antalet H* ≥ H) / 10 000, ensidigt. En permutation utan prediktion räknas
  som H* < H i båda svansarna. Allt enligt posten.
- Egen permutation (blocken blandas med `rng.shuffle`, 20 000 permutationer, annat frö): v2 p = 0,184 och 0,250 (T1
  0,184 och 0,261), Holm 0,367 (T1 0,368). v1 p = 0,412 och 0,649 (T1 0,417 och 0,652). p_ned 0,821 och 0,769 (T1 0,820
  och 0,760). Skillnaderna är Monte Carlo-brus.
- Holm-familjen är {v2 h = 3, v2 h = 6}, och v1 har en egen. Testet med färre än 20 prediktioner får p = 1 före Holm.
- **Storleken.** Med oberoende men tröga prediktioner och utfall (Markovkedjor där tillståndet står kvar med
  sannolikheten 0,7–0,95) förkastar testet på 10 %-nivån i 8–11 % av 300 världar. I T1:s slumpvärld med 40 frön var
  rått p < 0,10 i 2 av 50 prövbara horisonter. Blockpermutationen förkastar alltså inte för ofta. Ett test i R24
  prövar det (passerar).
- Kappa (0,825 med v2, 0,856 med v1), andelen lika (0,905 och 0,921) och antalet byten (G6 6, G7 8 med v2) stämmer med
  egen beräkning.

## 4. Omräkning för hand – OK

| Grenmånad | Vad | T1 | R24 |
|---|---|---|---|
| G6 2025-10 | `us_ip_computers_m`, förändring i takt, realtid → dagens data | −0,4 → −11,6, riktning 0 → −1 | −0,39 → −11,64, dödband 2,75/2,92, 0 → −1 |
| G6 2025-10 | `us_ip_semis_m` | 2,0 → −4,6, 0 → −1 | 2,02 → −4,59, dödband 3,00/3,02, 0 → −1 |
| G6 2025-10 | tillstånd v2 | stabil → bromsar in | stabil → bromsar in (index 0,321) |
| G7 2025-06 | `us_elec_sales_com_az_m` | +1 → −1 | 4,54 → −9,53, +1 → −1 (april 2025: 2 849 → 2 586 GWh, versionerna 2026-06-27 och 2026-10-25) |
| G7 2025-06 | `us_elec_sales_com_ga_m` | +1 → −1 | 5,44 → −4,55, +1 → −1 |
| G7 2025-06 | tillstånd v2 | accelererar → stabil (0,59) | accelererar → stabil (0,589) |
| G6 2024-05 | tillstånd v2 | stabil → accelererar | stabil → accelererar (0,786) |
| G4 2024-03 | utfall h = 3 / persistens | upp / upp | upp / upp (AWS, Google, Nvidia, RPO upp; Microsoft, Oracle ned) |
| G5 2025-01 | utfall h = 3 / h = 6 | ned / upp | ned / upp (`us_pfi_info_proc_eq_sw` saknar utfall vid h = 3) |
| G6 2025-10 | utfall h = 3 och 6 / persistens | upp / ned | upp / ned |
| G7 2025-06 | utfall h = 3 / persistens | upp / ned | upp / ned (PJM:s årsserier saknar utfall) |
| G7 2026-01 | utfall h = 6 / persistens | ned / upp | ned / upp |

Utöver tabellen stämmer alla 236 grenmånader och horisonter i G4–G7 (punkt 2). EIA:s värden kontrollerades inte mot
EIA, bara mot bastabellen. Revideringarna kommer i versionerna ungefär ett år efter den första (Georgia april 2024:
3 801 → 4 056 → 4 197 GWh), men de är inte verifierade mot källan.

## 5. Ordval och beslutsregeln – anmärkning

**Beslutsregeln är tillämpad mekaniskt och rätt.** Villkor 1: kappa 0,825 ≥ 0,70 och inga hårda byten. Villkor 2:
vid h = 3 är H = 42/57 = 0,737 över max(40,0/57 = 0,702; 0,682). Villkor 3: Holm-justerat p_ned är 1,00. Godkänt kräver
Holm-p < 0,10, och Holm-p är 0,368. Med 41 träffar vid h = 3 blir det ingen rekommendation, med 40 blir det en. "Två
träffar färre" stämmer (testat).

**R24-1: persistensen vid 6 månader är tillståndet självt.** Förändringen i takt är registrerad som takten nu minus
takten 6 månader (2 kvartal) tidigare. Persistensen vid h = 6 är tecknet av takten vid P_m minus takten vid P_{m−6},
ur versionen vid m. Det är samma jämförelse, bara utan dödband. I alla 46 prediktioner med v2 vid h = 6 har
persistensen samma riktning som tillståndet, och i T1:s slumpvärld är H lika med persistensen vid h = 6 i 40 av 40
frön. Följder:
- "Vid 6 månader är de lika (35 mot 35,0)" och "I G4 och G5 ... säger tillstånden inget utöver 'samma riktning som
  senast'" är byggda in i testet, inte fynd. Vid h = 3 är det en riktig jämförelse.
- Kriteriet för godkänt (H över persistensen) kan i praktiken inte uppfyllas vid h = 6, och villkor 2 avgörs bara av
  h = 3. Även i T1:s tröga värld, där tillstånden bär information, rekommenderar regeln en granskning, eftersom
  persistensen bär samma information (testat).
- Det är inget brott mot posten: persistensen är definierad så. Men resultatet ska säga det, och en ny registerpost
  ska välja en baslinje som inte är tillståndet självt vid h = 6.

**R24-2: basfrekvensen och persistensen över alla månader.**
- Posten säger att persistensen "redovisas också över alla månader med utfall". Den finns i resultatfilen (0,61 vid
  h = 3 och 0,56 vid h = 6) men inte i resultatet. Den är mycket lägre än på tillståndens månader (0,70 och 0,76). Det
  visar att både tillstånd och persistens träffar mest där takten gick upp nästan hela tiden (G4–G6).
- I de månader som har en prediktion gick takten upp i 46 av 57 (81 %) och 37 av 46 (80 %). En konstant prognos "upp"
  hade träffat 0,81 och 0,80 på samma månader, mer än tillstånden (0,74 och 0,76). Det är ingen registrerad baslinje och
  avgör inget, men det visar vad "till största delen basfrekvens" betyder.
- T1:s sammanfattning till orkestreraren säger att "takten gick upp i cirka 62 % av utfallen". Det är andelen över
  alla grenmånader, också grenar utan tillstånd. För träffkvoten är 81 % och 80 % den relevanta andelen.

**Resten av ordvalet håller.** "Informationsvärdet är inte påvisat", "visar inte heller att tillstånden saknar
information", "Skillnader på 5 procentenheter mot slumpen kan helt och hållet vara slump" och förbehållen om ett enda
uppgångsfönster stämmer med underlaget. Delperiodernas skillnader (0,69 mot 0,80 med 32 och 25 prediktioner) är cirka
ett standardfel. MDE-räkningen är en grov tumregel (variansen 0,25 och n/h oberoende fall). Den första överdriver
variansen när basfrekvensen är 0,7–0,8, den andra underskattar beroendet. Det ändrar inte slutsatsen om låg styrka.

**Det syntetiska exemplet i resultatet** (fem frön, träffkvoter 0,22–0,77, 22–39 prediktioner, ett rått p 0,048)
gick att återskapa: frö 3, 5 och 1 med tre grenar och frö 1 och 2 med två ger 0,217–0,771, 22–39 prediktioner och
p 0,048 (frö 3, h = 6). Fröna står inte i resultatet (R24-7).

## 6. De syntetiska testerna – anmärkning

- **Den tröga världen** (`test_persistent_world_states_carry_information`) prövar egenskapen. Med frö 1–6 klarar
  den kraven i alla sex: H 0,76–0,86, slumpnivå cirka 0,52, Holm-p 0,016–0,042.
- **Slumpvärlden** (`test_random_world_states_carry_no_information`) kräver |H − slumpnivå| < 0,1 och Holm-p > 0,10
  vid båda horisonterna, med frö 2. Med frö 1–40 håller kravet i 15 frön, och i fyra av dem prövas en horisont inte
  alls (färre än 20 prediktioner, p = 1) (R24-3). Med frö 1 är skillnaden 0,12–0,13 (strikt xfail). Det som testet
  ska visa, att testet inte förkastar för ofta utan information, prövas av storlekstestet i R24 i stället.
- Trunkeringstestet, testet för senare period, testet för konstant tillstånd, blockordningen, kappa och
  beslutsregeln prövar det de säger.

## Rättningar (för ett rättningsspår)

| # | Var | Rättning |
|---|---|---|
| R24-1 | `docs/resultat/t1_tillstandsregeln.md`, och nästa registerpost | Skriv att persistensen vid h = 6 är tillståndets egen jämförelse (P_m mot P_{m−6}, samma som förändringen i takt) utan dödband, att H = persistensen där av konstruktion (46 av 46), och att godkänt därför bara kan nås vid h = 3. Ändra läsningen av G4 och G5. En ny registerpost väljer en annan baslinje för h = 6 eller prövar bara h ≠ laggen mot persistens. Strikt xfail i `tests/test_r24_tillstandsregeln.py` |
| R24-2 | `docs/resultat/t1_tillstandsregeln.md`, sammanfattningen | Redovisa persistensen över alla månader med utfall (0,61 och 0,56), som posten kräver. Lägg till andelen upp på tillståndens månader (81 % och 80 %) och att en konstant prognos "upp" hade träffat 0,81 och 0,80. Ersätt "62 % av utfallen" i sammanfattningen. Strikt xfail |
| R24-3 | `tests/test_state_evaluate.py` | Byt slumpvärldens krav mot ett storlekstest över många frön (eller Markovkedjor, som i R24) och kräv att testet faktiskt körs (`tested`). Kravet att H ligger inom 0,1 från slumpnivån håller bara för vissa frön. Strikt xfail (frö 1) |
| R24-4 | `docs/resultat/t1_tillstandsregeln.md`, "Synligt före posten" | Skriv att `snapshot.backcast` skrevs till en fil före posten med tillstånd, index och riktning per serie för varje månad, att den vid h = 6 nästan innehåller utfallen, och att "bara antalen lästes" är spårets egen uppgift som inte går att kontrollera. Strikt xfail |
| R24-5 | nästa registerpost (omkörningen 2027) | Räkna spärren i dagens data med samma antal egna månader som i realtid vid m, inte med första `known_from` i den reviderade tabellen. Ingen effekt i denna körning. Ett test i R24 visar beteendet och att körningen redovisar det |
| R24-6 | `docs/resultat/t1_tillstandsregeln.md`, (a) | Skriv att G6:s revideringar kommer från G.17:s årsrevision 2026-11-24 (basår 2022), en dag före V, och att exponeringen räknar basårsbytet som revidering. TSMC, ASML och Broadcom har inga ändrade värden i fönstret |
| R24-7 | `docs/resultat/t1_tillstandsregeln.md` | Ange fröna och grenarna för det syntetiska exemplet (3, 5, 1 med G4–G6 och 1, 2 med G4–G5), eller committa skriptet |

## Vad som inte gick att verifiera

- Om T1 läste mer än antalen i `bc_realtime.csv` (R24-4). Filens innehåll och tid går att visa, inte vad som lästes.
- EIA:s månadsvärden mot EIA. Bara bastabellen användes.
- Verkliga revideringar i de bakåtfyllda serierna (EIA-930, FT-900, C30, BEA, Eurostat, arXiv, npm, PyPI, Wikipedia,
  Cloudflare). De syns inte i tabellen, som T1 säger.
- Resultatet beror på bastabellen 2026-11-25. Omkörningen gav samma fil, men en senare hämtning med `known_from` ≤ V
  kan ändra den.

## Tester

`tests/test_r24_tillstandsregeln.py` (syntetiska fixturer, inget nät; de sju fallen med riktiga data är märkta
`real_data` och hoppas över utan tabellen):
- dagens data enligt definitionen för en härledd kvot, en veckoserie och en månadsserie; rader efter V påverkar inte
  (passerar)
- spärren kan öppnas i dagens data när en bakåtfylld historik revideras, och körningen redovisar det (passerar, R24-5)
- persistensen läser inget efter m; fördubblingstidens tecken (passerar)
- persistensen vid h = 6 är seriens egen förändring i takt, och H = persistensen vid h = 6 (passerar, R24-1)
- den tröga världen ger rekommendation om granskning (passerar, R24-1)
- Holm-familjen och p-formeln; blockpermutationens storlek med tröga oberoende följder; v1:s flyttal mot exakt
  klassning för upp till 60 serier (passerar)
- beslutsregeln på de riktiga talen: 2 träffar avgör (passerar)
- handkontrollerna i resultatet och tre bytta tillstånd på riktiga data (passerar)
- slumpvärldens test med ett annat frö (strikt xfail, R24-3)
- resultatets text för R24-1, R24-2 och R24-4 (strikt xfail)

`python -m pytest -q tests/test_r24_tillstandsregeln.py tests/test_state_evaluate.py`: 40 passerade, 4 xfail. Hela
sviten på grenen: 2 205 passerade, 3 överhoppade, 6 xfail och 1 fel. Felet är det kända
`tests/test_site_bundle.py::test_committed_fixtures_are_the_current_synthetic_bundle`: fixturerna bär sha256 av
`docs/mattregister.md`, som T1 lade till i. Fixturerna har inte genererats om.
