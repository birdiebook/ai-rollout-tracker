# D2: prognoser 1–8 kvartal, utvecklingsperioden

Körd 2026-11-24 med `python -m ai_tracker.nowcast.horizon` (kod `src/ai_tracker/nowcast/horizon.py`), enligt
registerposten "2026-11-23 – D2: prognoser 1–8 kvartal (förregistrering, F-E7)" i `docs/mattregister.md`, med G-E,
G-C (F-C7) och F-E6. Körloggen ligger i `experiments/runs/*_d2_horizon_development.csv`.

**Holdouten är stängd.** Alla prognoser har prognosdag ≤ 2025-06-30 (den sista är 2025-04-20), och körningen läste bara
rader med `known_from` ≤ 2025-06-30 (`factor/guard.py`, `dev_table`). Det senaste utfall som ingår blev känt
2025-05-02. Varje prognosdag går genom `guard.check(family="D2")`, som stoppar en prognosdag efter 2025-06-30 så länge
D2:s holdout är stängd. D2 har en egen flagga (`OPEN_FAMILIES`), så att C3:s öppning inte öppnar D2 (F-E3). Inga
prognoser, fel eller utfall efter 2025-06-30 har beräknats eller lästs.

**Utvecklingskörningen avgör ingenting** (F-E6). Befordran prövas per horisontgrupp (h1–2, h3–4, h5–8) på holdouten.

## Uppställning

- **Mål:** `capex_hyp4` och `rev_cloud3` (AWS + Google Cloud + Microsoft Cloud, byggd som i N4). Utfall = första
  versionen av målkvartalet.
- **Prognosdag:** kalenderkvartalets slut + 20 dagar. L = det senaste kvartal av målet som är känt på prognosdagen.
  Målkvartalet är L + h, där h = 1–8.
- **B0** = nivån i L. **B1** = nivån i L × exp(h × medel av de fyra senaste kvartalens log-tillväxt).
- **B2 (capex):** per bolag som N1:s B2, summerat. Kvartal i ett år med helårsguidance som är känd på prognosdagen
  får N1:s regel: implicit helår minus årets kända kvartal, fördelat över årets okända kvartal med bolagets B1-bana.
  Senare kvartal får det sista guidade kvartalets nivå × exp(k × bolagets B1-drift). Amazon och Microsoft (ingen
  jämförbar guidance) och bolag utan guidat kvartal före får sin egen B1-bana.
- **V_kedja:** direkt OLS per h av g_t(h) = 100 × (log y(t+h) − log y(t)) på en konstant, R_t = årstakten (log ×100)
  i `rpo_hyp4` och X_t = 100 × (log `x_capex_cloud`(t) − medel av log `x_capex_cloud` till och med t). Prognos =
  y(L) × exp(ĝ/100), med regressorerna i L. Minst 12 rader per h.
- **Fel** = 100 × (log prognos − log utfall). Positivt = överskattning.
- **Intervall (G-C, F-C7):** en felpool per mål, modell och h. Ett fel kommer in i poolen först från sitt utfalls
  `known_from` (första versionen). Under 8 fel i poolen finns ingen fördelning, och från 8 till 39 används t.

### Fastställt här där registret är tyst

- **V_kedjas träningsrader** är kvartalen t i historiken som var känd på prognosdagen (as_of för målet, `rpo_hyp4`
  och `x_capex_cloud`), med t + h ≤ L och båda regressorerna definierade i t. Allt är känt på prognosdagen.
  Alternativet, att varje rad tar regressorn från sin egen tidigare prognosdag (som N4:s V1), ger färre rader,
  eftersom `x_capex_cloud` blev känd först 2021-10-27. Valet ger fler rader men samma informationsmängd.
- **Det expanderande medlet** av log `x_capex_cloud` löper över hela den kända historiken till och med t, utan
  minsta längd. Finns någon av regressorerna inte för L görs ingen V_kedja-prognos.
- **Härledda serier byggs om från komponenterna:** `rev_cloud3` och `rpo_hyp4` med `quarterly.aggregate_rows`,
  `x_capex_cloud` med `avstamning.derive` (samma regel som katalogen), så att varje version är den komponenterna ger.
- **Definitionsbrott (N4, F-B8)** för molnet: ett brottkvartal poängsätts inte, och B1:s fönster får inte gå över ett
  känt brott. Inga brott finns i utvecklingsdatan. Capex har ingen brottregel, som i N1.
- **N1:s B2-funktion** (`n1.guided_company`) har fått flaggan `ahead=True`, som tillåter ett kvartal mer än ett
  kvartal efter bolagets senast kända. Regeln är oförändrad, och N1:s eget anrop är oförändrat.

## n per h

En rad är en prognosdag med ett utfall som var känt senast 2025-06-30. Med längre h blir n mindre, eftersom utfallet
ligger längre fram.

| Mål | Prognosdagar | Baslinjer, n per h (h = 1 … 8) | V_kedja, n per h |
|---|---|---|---|
| capex | 2019-10-20 – 2025-04-20 | 23, 22, 21, 20, 19, 18, 17, 16 | 5, 3, 1, 0, 0, 0, 0, 0 |
| moln | 2022-10-20 – 2025-04-20 | 11, 10, 9, 8, 7, 6, 5, 4 | 5, 3, 1, 0, 0, 0, 0, 0 |

För capex begränsas baslinjerna av B1, som kräver fem kända kvartal av `capex_hyp4` (från 2019Q2 som L), och B2,
som kräver fyra tillväxttal för varje bolag. För molnet finns summan först från 2021Q3 som L (Microsoft Cloud), och B1
har fem kända kvartal först med L = 2022Q2. V_kedja
får 12 rader för h = 1 först vid prognosdagen 2024-04-20. Det beror på att `x_capex_cloud` och RPO-årstakten inte
finns före 2020Q4. För h ≥ 4 har V_kedja inget utfall i utvecklingen.

## Punktprognoser

MAE och bias i log ×100. Baslinjerna jämförs på sina gemensamma rader. V_kedja jämförs med den bästa baslinjen på
V_kedjas egna rader.

### Capex (`capex_hyp4`)

| h | n | Baskvartal L | MAE B0 | MAE B1 | MAE B2 | Bias B0 | Bias B1 | Bias B2 | n V_kedja | MAE V_kedja | MAE bästa baslinje, samma rader | Bias V_kedja |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 23 | 2019Q2 – 2024Q4 | 8,4 | 7,1 | 5,8 | −6,2 | −0,8 | +1,2 | 5 | 9,8 | 4,3 (B2) | −0,9 |
| 2 | 22 | 2019Q2 – 2024Q3 | 15,5 | 11,0 | 9,7 | −12,7 | −2,5 | +1,0 | 3 | 12,0 | 6,6 (B2) | −12,0 |
| 3 | 21 | 2019Q2 – 2024Q2 | 21,6 | 17,0 | 15,5 | −18,7 | −4,4 | +0,6 | 1 | 3,1 | 3,6 (B1) | −3,1 |
| 4 | 20 | 2019Q2 – 2024Q1 | 26,5 | 22,6 | 22,9 | −24,4 | −6,7 | +0,4 | 0 | – | – | – |
| 5 | 19 | 2019Q2 – 2023Q4 | 31,1 | 28,4 | 29,7 | −29,7 | −8,1 | +1,1 | 0 | – | – | – |
| 6 | 18 | 2019Q2 – 2023Q3 | 35,3 | 34,4 | 36,9 | −34,3 | −7,7 | +4,2 | 0 | – | – | – |
| 7 | 17 | 2019Q2 – 2023Q2 | 37,8 | 35,0 | 42,4 | −37,8 | −4,3 | +10,0 | 0 | – | – | – |
| 8 | 16 | 2019Q2 – 2023Q1 | 41,4 | 36,2 | 47,4 | −41,4 | +0,5 | +18,2 | 0 | – | – | – |

### Molnintäkter (`rev_cloud3`)

| h | n | Baskvartal L | MAE B0 | MAE B1 | Bias B0 | Bias B1 | n V_kedja | MAE V_kedja | MAE bästa baslinje, samma rader | Bias V_kedja |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 11 | 2022Q2 – 2024Q4 | 4,5 | 1,2 | −4,5 | +0,5 | 5 | 1,3 | 0,8 (B1) | +1,1 |
| 2 | 10 | 2022Q2 – 2024Q3 | 9,3 | 1,9 | −9,3 | +0,8 | 3 | 3,1 | 1,5 (B1) | +3,1 |
| 3 | 9 | 2022Q2 – 2024Q2 | 14,0 | 2,7 | −14,0 | +1,1 | 1 | 8,0 | 1,2 (B1) | +8,0 |
| 4 | 8 | 2022Q2 – 2024Q1 | 18,8 | 3,4 | −18,8 | +1,4 | 0 | – | – | – |
| 5 | 7 | 2022Q2 – 2023Q4 | 23,6 | 4,6 | −23,6 | +1,9 | 0 | – | – | – |
| 6 | 6 | 2022Q2 – 2023Q3 | 28,5 | 5,7 | −28,5 | +2,5 | 0 | – | – | – |
| 7 | 5 | 2022Q2 – 2023Q2 | 33,0 | 6,9 | −33,0 | +4,3 | 0 | – | – | – |
| 8 | 4 | 2022Q2 – 2023Q1 | 37,7 | 7,8 | −37,7 | +7,2 | 0 | – | – | – |

### V_kedjas rader (alla)

| Mål | Prognosdag | L | h | Träningsrader | B0 | B1 | B2 | V_kedja |
|---|---|---|---|---|---|---|---|---|
| capex | 2024-04-20 | 2023Q4 | 1 | 12 | −2,9 | −0,8 | +2,9 | +6,7 |
| capex | 2024-07-20 | 2024Q1 | 1 | 13 | −17,7 | −11,0 | −2,1 | −11,5 |
| capex | 2024-07-20 | 2024Q1 | 2 | 12 | −28,4 | −15,1 | −5,1 | −14,1 |
| capex | 2024-10-20 | 2024Q2 | 1 | 14 | −10,8 | +0,7 | +4,4 | −1,8 |
| capex | 2024-10-20 | 2024Q2 | 2 | 13 | −31,4 | −8,5 | −4,6 | −16,7 |
| capex | 2024-10-20 | 2024Q2 | 3 | 12 | −30,8 | +3,6 | +7,7 | −3,1 |
| capex | 2025-01-20 | 2024Q3 | 1 | 15 | −20,6 | −9,0 | −2,1 | −13,3 |
| capex | 2025-01-20 | 2024Q3 | 2 | 14 | −20,0 | +3,3 | +10,1 | −5,2 |
| capex | 2025-04-20 | 2024Q4 | 1 | 16 | +0,6 | +13,6 | +9,7 | +15,6 |
| moln | 2024-04-20 | 2023Q4 | 1 | 12 | −3,8 | +0,8 | – | +2,2 |
| moln | 2024-07-20 | 2024Q1 | 1 | 13 | −5,2 | −0,3 | – | −0,1 |
| moln | 2024-07-20 | 2024Q1 | 2 | 12 | −10,9 | −1,1 | – | +1,6 |
| moln | 2024-10-20 | 2024Q2 | 1 | 14 | −5,7 | −0,8 | – | −0,2 |
| moln | 2024-10-20 | 2024Q2 | 2 | 13 | −10,6 | −0,9 | – | +2,1 |
| moln | 2024-10-20 | 2024Q2 | 3 | 12 | −13,4 | +1,2 | – | +8,0 |
| moln | 2025-01-20 | 2024Q3 | 1 | 15 | −4,9 | +0,2 | – | +0,9 |
| moln | 2025-01-20 | 2024Q3 | 2 | 14 | −7,7 | +2,5 | – | +5,6 |
| moln | 2025-04-20 | 2024Q4 | 1 | 16 | −2,8 | +2,1 | – | +3,0 |

## Intervall (felpool per h, F-C7)

Bara rader där poolen för samma h hade minst 8 fel med känt utfall på prognosdagen. Alla fördelningar är t (n < 40).
V_kedja har ingen fördelning i utvecklingen, eftersom poolen aldrig når 8 fel.

### Capex

| h | Modell | n med fördelning | Täckning 50 % | Täckning 80 % | Täckning 95 % | CRPS |
|---|---|---|---|---|---|---|
| 1 | B0 | 18 | 67 % | 89 % | 100 % | 5,48 |
| 1 | B1 | 15 | 53 % | 73 % | 93 % | 5,44 |
| 1 | B2 | 15 | 73 % | 93 % | 100 % | 3,88 |
| 2 | B0 | 16 | 44 % | 75 % | 88 % | 8,15 |
| 2 | B1 | 13 | 38 % | 69 % | 85 % | 9,88 |
| 2 | B2 | 13 | 54 % | 92 % | 92 % | 6,90 |
| 3 | B0 | 14 | 29 % | 64 % | 71 % | 12,03 |
| 3 | B1 | 11 | 9 % | 36 % | 82 % | 17,24 |
| 3 | B2 | 11 | 45 % | 64 % | 91 % | 12,98 |
| 4 | B0 | 12 | 25 % | 33 % | 67 % | 16,26 |
| 4 | B1 | 9 | 11 % | 33 % | 67 % | 25,76 |
| 4 | B2 | 9 | 33 % | 56 % | 89 % | 21,63 |
| 5 | B0 | 10 | 0 % | 20 % | 60 % | 20,73 |
| 5 | B1 | 7 | 14 % | 43 % | 71 % | 32,04 |
| 5 | B2 | 7 | 43 % | 43 % | 71 % | 29,24 |
| 6 | B0 | 8 | 12 % | 25 % | 88 % | 22,12 |
| 6 | B1 | 5 | 20 % | 40 % | 60 % | 41,01 |
| 6 | B2 | 5 | 20 % | 40 % | 80 % | 40,10 |
| 7 | B0 | 6 | 17 % | 33 % | 100 % | 17,68 |
| 7 | B1 | 3 | 33 % | 33 % | 67 % | 49,64 |
| 7 | B2 | 3 | 0 % | 33 % | 100 % | 54,83 |
| 8 | B0 | 4 | 25 % | 25 % | 75 % | 11,93 |
| 8 | B1 | 1 | 0 % | 0 % | 100 % | 55,47 |
| 8 | B2 | 1 | 0 % | 0 % | 100 % | 59,26 |

### Molnintäkter

| h | Modell | n med fördelning | Täckning 50 % | Täckning 80 % | Täckning 95 % | CRPS |
|---|---|---|---|---|---|---|
| 1 | B0 | 6 | 67 % | 83 % | 100 % | 0,71 |
| 1 | B1 | 3 | 33 % | 100 % | 100 % | 0,77 |
| 2 | B0 | 4 | 75 % | 75 % | 100 % | 0,82 |
| 2 | B1 | 1 | 100 % | 100 % | 100 % | 1,06 |
| 3 | B0 | 2 | 100 % | 100 % | 100 % | 0,88 |

CRPS jämförs bara inom samma h och mål, och raderna skiljer sig mellan modellerna (olika långa pooler).

## Tolkning

- **Capex, baslinjer:** B2 har lägst MAE för h = 1–3 (5,8, 9,7 och 15,5 mot B1:s 7,1, 11,0 och 17,0). Från h = 4 är
  B1 lika bra eller bättre. B2:s bias växer med h (+18 vid h = 8), eftersom tillväxten från det sista guidade kvartalet
  fortsätter i ett år då capex ökade snabbt. B0 underskattar hela tiden (bias −6 till −41), som väntat när capex växer.
  Raderna överlappar för h > 1 (samma kvartal i flera prognoser), så det effektiva antalet observationer är mindre än n.
- **Moln, baslinjer:** B1 är klart bättre än B0 på alla h (MAE 1,2 mot 4,5 vid h = 1, 7,8 mot 37,7 vid h = 8). Bias för B1
  ökar med h (+7 vid h = 8). Tillväxten bromsade alltså in efter perioden B1 skattade driften på. Perioden är kort:
  4–11 prognosdagar.
- **V_kedja:** 9 rader för capex och 9 för molnet, alla från 2024-04-20 till 2025-04-20 och bara h = 1–3. För capex är
  V_kedja sämre än B2 på h = 1–2 (MAE 9,8 mot 4,3 och 12,0 mot 6,6), och för molnet sämre än B1 på h = 1–3. Med n = 1–5
  går det inte att skilja något från slump. Det enda som går att säga är att V_kedja inte visar något tecken på att
  vara bättre i utvecklingen.
- **Intervall:** för capex är baslinjernas intervall för smala från h = 3 (täckning 9–45 % för 50 % och 60–91 % för
  95 %). Felen är autokorrelerade och har bias, och poolerna är små (t med 7–17 fel). För h ≥ 6 finns högst 8 rader med
  fördelning. Det är beskrivande, och kalibreringen testas inte här.

## Brasklappar och vad holdouten kan visa

- **Holdouten kan troligen inte pröva V_kedja.** Holdouten har 6 prognosdagar (2025-07-20 – 2026-10-20), och utfallen
  för de längre horisonterna vid de sista prognosdagarna kommer först efter 2026-10. Vid n < 8 i en horisontgrupp görs
  inget test, och V_kedja går in som skugga i det skarpa registret (F-E6).
  **Rekommendation:** räkna n i en horisontgrupp som antalet distinkta prognosdagar med utfall, inte som rader (h1 och h2
  från samma prognosdag är inte oberoende). Då blir n ≤ 6 i alla grupper, så det blir inget test på holdouten. Det bör
  fastställas i registret innan holdouten öppnas.
- **Holdouten är inte blind** (F-E5). N1:s och N4:s fel för 2025Q2–2026Q3 vid h = 1 är redan publicerade i
  `docs/resultat/n1.md` och `n4.md`.
- **B2 bygger på extraherad guidance** (Meta och Alphabet), som för N1 kräver oberoende granskning (R2) innan något
  befordras.
- **V_kedjas träningsrader överlappar** för h > 1, och för molnet har x_capex_cloud och RPO-årstakten bara funnits sedan
  2020Q4. Koefficienterna är skattade på 12–16 rader och är osäkra.
