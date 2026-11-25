# T1: test av tillståndsregeln (körning 14)

Spår T1, 2026-11-25. Testet prövar själva tillståndsregeln: index v2 med källfamiljer (officiell från
ögonblicksbilden 2026-11-30) och v1 bredvid. Två frågor. Håller tillstånden när data revideras? Säger de något om
grenens takt de närmaste 3 och 6 månaderna? Testet ändrar ingen skarp regel.

- **Förregistrering:** `docs/mattregister.md`, "2026-11-25 – T1: test av tillståndsregeln (förregistrering, före
  körning)", commit `7b008b3`. Koden kom efter (`841f92b`, bara syntetiska tester), och körningen på riktiga data
  efter den (körlogg `experiments/runs/20261125T092201Z_t1_state_rule.csv`).
- **Synligt före posten:** tabellerna i `docs/resultat/tillstand.md`, tillstånden 2026-10-31, antalet månader per
  tillstånd och gren 2024-01–2026-10 (för MDE) och antalet versioner per kärnserie. Inga utfall, inga reviderade
  tillstånd och inga träffar.
- **Kod:** `src/ai_tracker/state/evaluate.py`, `python -m ai_tracker.state evaluate`. Tillståndsmotorn läses men ändras
  inte. Tester: `tests/test_state_evaluate.py` (syntetiska data, inget nätverk).
- Allt är **rekonstruerat** (as-of-backcast) på den delade bastabellen 2026-11-25. Det är inget skarpt register.

## Kort svar

1. **Revideringar (a).** Med v2 har 91 % av grenmånaderna samma tillstånd med dagens data. Kappa är 0,83 och det
   finns inga hårda byten (accelererar mot bromsar in). Det klarar den registrerade nivån (kappa ≥ 0,70, hårda byten
   ≤ 2 %). Men G6 och G7 byter tillstånd i 6 respektive 8 av 34 månader, och bara 33 % av de räknade serierna har
   reviderade värden alls. För resten är stabiliteten given av konstruktion, inte prövad.
2. **Information (b).** Tillstånden träffar i 74 % (3 månader) och 76 % (6 månader) av fallen. Slumpen ger 68 % och
   71 %, eftersom takten oftast gick upp i fönstret. Att den senaste riktningen fortsätter (persistens) ger 70 % och
   76 %. Holm-p är 0,37 för båda horisonterna. **Informationsvärdet är inte påvisat.** Testet kan bara upptäcka
   mycket stora skillnader (MDE 0,28 och 0,44), så resultatet visar inte heller att tillstånden saknar information.
3. **Bromsar in** förekom 6 gånger (3 månader) och 4 gånger (6 månader) och träffade en gång var. Det är för få fall
   för att säga något.
4. **Beslutsregeln, mekaniskt:** ingen granskning av regeln rekommenderas, och (b) är inte avgjort. Inget positivt
   resultat. Marginalen är liten: vid 3 månader ligger tillstånden 2 träffar över persistensen. Med 2 träffar färre
   hade regeln rekommenderat en granskning (villkor 2).

**Hur tillstånden kan läsas:** som en beskrivning av riktningen i den senaste förändringen i takt för de räknade
källorna, inte som en prognos. Att de pekar ut vad som händer de närmaste månaderna bättre än slumpen eller "samma
riktning som senast" är inte visat. G6 och G7 ändras ofta när data revideras.

## (a) Revideringsstabilitet

Realtid är tillståndet vid månadsslut m med `as_of(m)`, det som rekonstruktionen ger. Dagens data för månad m är de
perioder som var kända vid m, med senaste versionen 2026-11-25. S är grenmånaderna där minst ett av de två är
accelererar, stabil eller bromsar in. Sista kolumnen är andelen räknade serier (realtid) vars värden kända vid m har
ändrats senare.

#### (a) v2: realtid mot dagens data

| Gren | Månader i S | Samma tillstånd | Kappa | Hårda byten | Ändrade | Medel abs. indexskillnad | Räknade serier med reviderade värden |
|---|---|---|---|---|---|---|---|
| G1 | 0 | – | – | – | – | – | 12 % |
| G2 | 0 | – | – | – | – | – | – |
| G3 | 12 | 100 % | 1,00 | 0 (0 %) | 0 | 0,000 | 0 % |
| G4 | 34 | 100 % | 1,00 | 0 (0 %) | 0 | 0,000 | 9 % |
| G5 | 34 | 100 % | 1,00 | 0 (0 %) | 0 | 0,000 | 14 % |
| G6 | 34 | 82 % | 0,68 | 0 (0 %) | 6 | 0,063 | 22 % |
| G7 | 34 | 76 % | 0,39 | 0 (0 %) | 8 | 0,063 | 45 % |
| G8 | 0 | – | – | – | – | – | 100 % |
| G9 | 0 | – | – | – | – | – | 0 % |
| Alla | 148 | 91 % | 0,83 | 0 (0 %) | 14 | 0,020 | 33 % |

#### (a) v1: realtid mot dagens data

| Gren | Månader i S | Samma tillstånd | Kappa | Hårda byten | Ändrade | Medel abs. indexskillnad | Räknade serier med reviderade värden |
|---|---|---|---|---|---|---|---|
| G1 | 0 | – | – | – | – | – | 12 % |
| G2 | 0 | – | – | – | – | – | – |
| G3 | 27 | 100 % | 1,00 | 0 (0 %) | 0 | 0,000 | 0 % |
| G4 | 34 | 100 % | 1,00 | 0 (0 %) | 0 | 0,000 | 9 % |
| G5 | 34 | 100 % | 1,00 | 0 (0 %) | 0 | 0,000 | 14 % |
| G6 | 34 | 79 % | 0,54 | 0 (0 %) | 7 | 0,098 | 22 % |
| G7 | 34 | 68 % | 0,27 | 0 (0 %) | 11 | 0,087 | 45 % |
| G8 | 31 | 100 % | 1,00 | 0 (0 %) | 0 | 0,033 | 100 % |
| G9 | 34 | 100 % | 1,00 | 0 (0 %) | 0 | 0,000 | 0 % |
| Alla | 228 | 92 % | 0,86 | 0 (0 %) | 18 | 0,027 | 33 % |

Över alla 306 grenmånader är överensstämmelsen 95 % med v2 och 94 % med v1. Den är högre än i S, eftersom G1, G2,
G8 och G9 har "för få källor" i båda med v2.

**Vad som byter.** Med v2 byter G6 i 2024-05 (stabil → accelererar), 2024-09 och 2024-11 (accelererar → stabil) och
2025-07, 2025-10 och 2025-12 (stabil → bromsar in). G7 byter i 8 månader mellan stabil och accelererar eller bromsar
in, åt båda hållen. Handkontroll av två månader:
- **G6 2025-10:** realtid stabil (index 0,39), med dagens data bromsar in (0,32). Det är Fed G.17 som har reviderats:
  förändringen i takt för `us_ip_computers_m` gick från −0,4 till −11,6 och för `us_ip_semis_m` från 2,0 till −4,6.
  Båda gick från riktning 0 till −1. Övriga sju serier är oförändrade.
- **G7 2025-06:** realtid accelererar (0,70), med dagens data stabil (0,59). EIA:s elförsäljning till kommersiell
  sektor har reviderats för Arizona och Georgia, som gick från +1 till −1.

Spärrade bakåtfyllda serier räknas inte i någon av de två i fönstret (0 grenmånader), som väntat.

## (b) Information om vad som kommer

Prediktion: accelererar vid m betyder att takten går upp till m + h, bromsar in att den går ned. Utfallet räknas för
de serier som räknades vid m, med det registrerade taktmåttet ur versionen vid m + h, och läggs ihop med samma
familjeröster som indexet. Persistensen är riktningen de senaste h månaderna (versionen vid m). Slumpnivån är medlet
av 9 999 blockpermutationer (block om 6 månader inom gren).

#### (b) v2: tillståndet vid m mot riktningen i takt till m + h

| h | Prediktioner (acc./broms.) | Träffar | Träffkvot | Slumpnivå | Persistens samma månader | p | Holm-p | p_ned (Holm) |
|---|---|---|---|---|---|---|---|---|
| 3 | 57 (51/6) | 42 (acc. 41, broms. 1) | 0,74 | 0,68 | 0,70 | 0,184 | 0,368 | 1,000 |
| 6 | 46 (42/4) | 35 (acc. 34, broms. 1) | 0,76 | 0,71 | 0,76 | 0,261 | 0,368 | 1,000 |

Per gren (v2). Grenar utan tillstånd har inga prediktioner men har utfall, som visar basfrekvensen:

| Gren | h | Prediktioner | Träffkvot | Acc.: träffar/antal | Broms.: träffar/antal | Persistens samma månader | Andel upp i utfallen | Månader med utfall |
|---|---|---|---|---|---|---|---|---|
| G1 | 3 | 0 | – | 0/0 | 0/0 | – | 44 % | 25 av 31 |
| G1 | 6 | 0 | – | 0/0 | 0/0 | – | 42 % | 26 av 28 |
| G3 | 3 | 3 | 0,00 | 0/3 | 0/0 | 0,00 | 33 % | 30 av 31 |
| G3 | 6 | 3 | 0,33 | 1/3 | 0/0 | 0,33 | 48 % | 25 av 28 |
| G4 | 3 | 15 | 0,87 | 13/14 | 0/1 | 0,87 | 83 % | 30 av 31 |
| G4 | 6 | 11 | 0,91 | 10/10 | 0/1 | 0,91 | 91 % | 22 av 28 |
| G5 | 3 | 18 | 0,78 | 14/17 | 0/1 | 0,78 | 76 % | 29 av 31 |
| G5 | 6 | 16 | 0,75 | 12/15 | 0/1 | 0,75 | 75 % | 28 av 28 |
| G6 | 3 | 13 | 0,92 | 12/13 | 0/0 | 0,88 | 68 % | 28 av 31 |
| G6 | 6 | 10 | 0,90 | 9/10 | 0/0 | 0,90 | 71 % | 28 av 28 |
| G7 | 3 | 8 | 0,38 | 2/4 | 1/4 | 0,19 | 57 % | 30 av 31 |
| G7 | 6 | 6 | 0,50 | 2/4 | 1/2 | 0,50 | 50 % | 28 av 28 |
| G8 | 3 | 0 | – | 0/0 | 0/0 | – | 93 % | 28 av 31 |
| G8 | 6 | 0 | – | 0/0 | 0/0 | – | 100 % | 25 av 28 |
| G9 | 3 | 0 | – | 0/0 | 0/0 | – | 39 % | 31 av 31 |
| G9 | 6 | 0 | – | 0/0 | 0/0 | – | 36 % | 28 av 28 |

#### (b) v1 (sekundär, bara information)

| h | Prediktioner (acc./broms.) | Träffar | Träffkvot | Slumpnivå | Persistens samma månader | p | Holm-p | p_ned (Holm) |
|---|---|---|---|---|---|---|---|---|
| 3 | 90 (78/12) | 68 (acc. 63, broms. 5) | 0,76 | 0,74 | 0,72 | 0,417 | 0,833 | 0,707 |
| 6 | 78 (66/12) | 58 (acc. 52, broms. 6) | 0,74 | 0,76 | 0,71 | 0,652 | 0,833 | 0,707 |

| Gren | h | Prediktioner | Träffkvot | Acc.: träffar/antal | Broms.: träffar/antal | Persistens samma månader | Andel upp i utfallen | Månader med utfall |
|---|---|---|---|---|---|---|---|---|
| G3 | 3 | 4 | 0,75 | 0/0 | 3/4 | 0,62 | 37 % | 30 av 31 |
| G3 | 6 | 5 | 0,60 | 0/1 | 3/4 | 0,60 | 54 % | 28 av 28 |
| G4 | 3 | 15 | 0,87 | 13/14 | 0/1 | 0,87 | 83 % | 30 av 31 |
| G4 | 6 | 11 | 0,91 | 10/10 | 0/1 | 0,91 | 91 % | 22 av 28 |
| G5 | 3 | 18 | 0,78 | 14/17 | 0/1 | 0,78 | 76 % | 29 av 31 |
| G5 | 6 | 16 | 0,75 | 12/15 | 0/1 | 0,75 | 75 % | 28 av 28 |
| G6 | 3 | 9 | 0,89 | 8/9 | 0/0 | 0,78 | 65 % | 31 av 31 |
| G6 | 6 | 7 | 0,86 | 6/7 | 0/0 | 0,86 | 75 % | 28 av 28 |
| G7 | 3 | 9 | 0,22 | 2/6 | 0/3 | 0,33 | 61 % | 31 av 31 |
| G7 | 6 | 9 | 0,33 | 1/6 | 2/3 | 0,33 | 57 % | 28 av 28 |
| G8 | 3 | 26 | 0,92 | 24/26 | 0/0 | 0,87 | 93 % | 28 av 31 |
| G8 | 6 | 23 | 1,00 | 23/23 | 0/0 | 0,87 | 100 % | 25 av 28 |
| G9 | 3 | 9 | 0,44 | 2/6 | 2/3 | 0,33 | 39 % | 31 av 31 |
| G9 | 6 | 7 | 0,14 | 0/4 | 1/3 | 0,14 | 36 % | 28 av 28 |

G1 och G2 har inga tillstånd med v1 heller och står inte i tabellen.

**Läsning.**
- Träffkvoten är till största delen basfrekvens. I G4, G5 och G6 gick takten upp i 68–91 % av månaderna, och där var
  nästan alla prediktioner accelererar. Slumpnivån tar hänsyn till det, eftersom permutationen bara flyttar
  tillstånden inom grenen.
- I G4 och G5 är tillståndens träffkvot exakt densamma som persistensens. Där säger tillstånden inget utöver "samma
  riktning som senast".
- Där tillstånden är blandade och basfrekvensen nära hälften (G7, och G9 med v1) är träffkvoten låg: 0,14–0,50. Det
  pekar på återgång, men p_ned är inte signifikant, och fallen är få.
- G8 med v1 har nästan bara accelererar och träffar 92–100 %. Det säger inget om regeln: tillståndet byter nästan
  aldrig, och takten gick upp nästan hela tiden. En permutation inom grenen kan inte upptäcka information i ett
  tillstånd som inte varierar (ett syntetiskt test visar det).

**MDE, räknad före testet** (registerposten): 0,28 över slumpnivån för h = 3 och 0,44 för h = 6 med v2. Den
observerade skillnaden mot slumpen är 0,05 vid båda. Med slumpnivån 0,68 hade 3-månadersprövningen behövt en
träffkvot runt 0,96 för att upptäckas med 80 % säkerhet. Vid 6 månader går det inte alls. Den låga styrkan sades
före testet.

## (c) Beskrivning, ingen ny regel

#### Andel månader per tillstånd (realtid, 2024-01–2026-10)

| Gren | v2 acc. | v2 stabil | v2 broms. | v2 för få källor | Familjer (medel) | v1 acc. | v1 stabil | v1 broms. | v1 för få serier | Serier (medel) |
|---|---|---|---|---|---|---|---|---|---|---|
| G1 | 0 % | 0 % | 0 % | 100 % | 1,4 | 0 % | 0 % | 0 % | 100 % | 1,4 |
| G2 | 0 % | 0 % | 0 % | 100 % | 0,0 | 0 % | 0 % | 0 % | 100 % | 0,0 |
| G3 | 9 % | 26 % | 0 % | 65 % | 2,3 | 3 % | 65 % | 12 % | 21 % | 5,9 |
| G4 | 53 % | 44 % | 3 % | 0 % | 6,0 | 53 % | 44 % | 3 % | 0 % | 6,0 |
| G5 | 59 % | 38 % | 3 % | 0 % | 5,0 | 59 % | 38 % | 3 % | 0 % | 5,0 |
| G6 | 47 % | 53 % | 0 % | 0 % | 6,9 | 32 % | 68 % | 0 % | 0 % | 8,9 |
| G7 | 12 % | 76 % | 12 % | 0 % | 3,0 | 18 % | 74 % | 9 % | 0 % | 13,0 |
| G8 | 0 % | 0 % | 0 % | 100 % | 0,9 | 85 % | 6 % | 0 % | 9 % | 7,6 |
| G9 | 0 % | 0 % | 0 % | 100 % | 1,0 | 21 % | 68 % | 12 % | 0 % | 3,0 |
| Alla | 20 % | 26 % | 2 % | 52 % | 2,9 | 30 % | 40 % | 4 % | 25 % | 5,6 |

Med v2 saknar grenarna tillstånd i 52 % av grenmånaderna: G1, G2, G8 och G9 hela fönstret och G3 i 65 % av
månaderna. Med v1 är det 25 %. Bromsar in förekommer i 2 % av grenmånaderna med v2.

#### Andra trösklar (beskrivning, inga p-värden)

| Regel | Trösklar | Acc. | Stabil | Broms. | Samma som 0,67/0,33 | (a) kappa | (a) hårda byten | (b) h = 3: träffkvot (slump) | (b) h = 6: träffkvot (slump) |
|---|---|---|---|---|---|---|---|---|---|
| v2 | 0,67/0,33 | 20 % | 26 % | 2 % | 100 % | 0,83 | 0 | 0,74 (0,68, n = 57) | 0,76 (0,71, n = 46) |
| v2 | 0,60/0,40 | 26 % | 13 % | 9 % | 86 % | 0,82 | 0 | 0,61 (0,61, n = 92) | 0,57 (0,61, n = 82) |
| v2 | 0,75/0,25 | 14 % | 34 % | 1 % | 92 % | 0,80 | 0 | 0,77 (0,73, n = 35) | 0,79 (0,78, n = 29) |
| v1 | 0,67/0,33 | 30 % | 40 % | 4 % | 100 % | 0,86 | 0 | 0,76 (0,74, n = 90) | 0,74 (0,76, n = 78) |
| v1 | 0,60/0,40 | 41 % | 21 % | 13 % | 81 % | 0,80 | 0 | 0,62 (0,66, n = 145) | 0,63 (0,67, n = 131) |
| v1 | 0,75/0,25 | 22 % | 49 % | 4 % | 91 % | 0,83 | 0 | 0,76 (0,77, n = 66) | 0,77 (0,79, n = 57) |

Slumpnivåerna i de andra trösklarna bygger på 999 permutationer. Ingen tröskel ger en tydlig marginal mot slumpen.
De vidare trösklarna (0,60/0,40) ger fler tillstånd och en träffkvot på eller under slumpnivån. De smalare
(0,75/0,25) ger färre tillstånd och ungefär samma marginal som de registrerade. Ingen tröskel ändras av detta.

#### Delperioder i (b) (beskrivning)

| Regel | h | Ursprung | Prediktioner | Träffkvot |
|---|---|---|---|---|
| v2 | 3 | till 2025-06 | 32 | 0,69 |
| v2 | 3 | från 2025-07 | 25 | 0,80 |
| v2 | 6 | till 2025-06 | 31 | 0,74 |
| v2 | 6 | från 2025-07 | 15 | 0,80 |
| v1 | 3 | till 2025-06 | 50 | 0,72 |
| v1 | 3 | från 2025-07 | 40 | 0,80 |
| v1 | 6 | till 2025-06 | 49 | 0,76 |
| v1 | 6 | från 2025-07 | 29 | 0,72 |

Delperioderna har 15–50 prediktioner var. Skillnaderna mellan dem ligger inom vad slumpen ger med så få fall.

## Beslutsregeln, mekaniskt

| Villkor (registerposten) | Värde | Utfall |
|---|---|---|
| 1. (a) poolad kappa v2 < 0,70 eller hårda byten v2 > 0,02 | kappa 0,83, hårda byten 0,00 | nej |
| 2. (b) H ≤ max(persistens, slumpnivå) vid både h = 3 och h = 6 | h = 3: 0,74 mot max(0,70; 0,68). h = 6: 0,76 mot max(0,76; 0,71) | nej (h = 3 är över) |
| 3. (b) Holm-justerat p_ned < 0,10 vid någon horisont | 1,00 och 1,00 | nej |
| (b) godkänt: Holm-p < 0,10 och H > persistens | Holm-p 0,37 och 0,37 | nej |

- **Granskning av regeln rekommenderas inte.**
- **(b) är inte avgjort.** Tillstånden läses som en beskrivning av läget, och deras informationsvärde är inte påvisat.
- **Inget positivt resultat**, så inget granskningsspår krävs för ett fynd.
- Villkor 2 avgörs av en liten marginal. Vid 3 månader har tillstånden 42 träffar och persistensen 40,0. Vid 6 månader
  är de lika (35 mot 35,0). Två träffar färre vid 3 månader hade gett en rekommendation om granskning. Det beslutet
  vilar alltså på en skillnad av slumpens storlek.

## Slump och förbehåll

- **Kort fönster.** 34 månader, varav 28–31 med utfall. Utfallen överlappar (3 och 6 månader), tillstånden är tröga
  och grenarna följer delvis samma cykel. Det effektiva antalet oberoende fall är litet, ungefär 19 och 8 med v2.
  Skillnader på 5 procentenheter mot slumpen kan helt och hållet vara slump.
- **Ett syntetiskt exempel på hur stor slumpen är.** I testvärlden där nivån är en ren slumpvandring (inget samband,
  `world("random")` i `tests/test_state_evaluate.py`) gav fem olika frön träffkvoter mellan 0,22 och 0,77 med 22–39 prediktioner, och i ett fall ett rått p-värde på 0,048 vid en
  horisont. Med så här få fall kan en enskild horisont se bra eller dålig ut av en slump.
- **(a) är en övre gräns.** Många kärnserier har bara en version: `source = "backfill"` (EIA-930, FT-900-importen,
  Census C30, BEA, Eurostat, arXiv, npm, PyPI, Wikipedia, Cloudflare) eller en enda inlämning. För dem är realtid och
  dagens data lika av konstruktion. Flera versioner finns för Indeed (G8), Fed G.17, TSMC, ASML och Broadcom (G6),
  Microsoft Cloud (G4), capex och kassaflöde för de fyra största (G5), EIA:s elförsäljning från arkivet (G7), BTOS v1
  (G3) och Arena (G1). Verkliga revideringar i de bakåtfyllda serierna syns inte här.
- **Realtid är inte helt realtid.** Rader som är bakåtfyllda bär dagens värden också i "realtid". Det gäller även
  utfallen i (b), som läser versionen vid m + h.
- **Återgång av konstruktion.** Tillståndet vid m och utfallet delar takten vid den senaste perioden, med motsatt
  tecken. Mätfel i den ger färre träffar. Det är en egenskap hos regeln, och permutationen bryter kopplingen.
- **Fönstret är en enda fas.** 2024–2026 är en uppgång i de flesta led. Bromsar in förekommer nästan inte (2 % av
  grenmånaderna med v2). Hur tillstånden beter sig när en uppgång vänder är inte prövat, eftersom det inte har hänt i
  fönstret.
- **G-E.** T1 är ingen metodfamilj i G-E och öppnar ingen holdout. Delperioden från 2025-07 redovisas för sig.

## Reproduktion

    PYTHONPATH=src python -m ai_tracker.state evaluate

Standardvärdena är de registrerade (2024-01–2026-10, V = 2026-11-25, 9 999 permutationer, frö 20261125). Kommandot
skriver `outputs/t1_tillstandsregeln.json` (gitignorerad, med alla rader per grenmånad och horisont), tabellerna ovan
och en körlogg i `experiments/runs/`. I körloggen står permutationens p i kolumnen `dm_p_vs_baseline`, och `MAE` är tom.
Tabellen ändras när veckohämtningen lägger till versioner, så en senare körning med samma V kan ge andra siffror om
basen har fått rader med `known_from` ≤ V i efterhand. Körningen tog cirka 3 minuter.
