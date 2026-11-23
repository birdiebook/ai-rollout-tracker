# C1: sannolikhetsprognoser för N1 och N2, metod och tolkningar

Spår C1, gren `auto4/c1-sannolikhet`. Metoden är registrerad som grind G-C i `docs/mattregister.md` (avsnittet
"Steg 2: förregistrering", G-C) tillsammans med posten "C0 preciseras efter granskning R6", som antar F-C1–F-C7 i
`docs/granskning/r6_c0.md` ordagrant. Förslaget som C1 lade fram (typ 6, empiriskt från n ≥ 40, Student-t för
8 ≤ n < 40) togs in i F-C2. Där koden och registertexten skiljer sig gäller texten.

**Inget är kört på verklig data.** Alla tester använder syntetiska data. Flaggan `intervals.ENABLED` är `False`.
Orkestreraren gör den första körningen efter merge (se "Så körs det").

## Metod (som registrerad)

- **Rum och tecken (F-C1).** Fel e = 100·(log f − log y). Utfallets kvantiler är Q_y(p) = f·exp(−Q_e(1 − p)/100).
  Täckning, PIT och CRPS räknas i felrummet. Där är de ekvivalenta, eftersom CRPS inte ändras av förskjutning och
  spegling. Ett intervall täcker y om och endast om Q_e((1−L)/2) ≤ e ≤ Q_e((1+L)/2).
- **Felpool (F-C4).** Modellens pseudo-out-of-sample-fel från den registrerade backtesten plus de skarpa felen.
  Varje fel ingår först från utfallets `known_from` (första versionen). Poolen är expanderande.
- **Fördelning (F-C2, F-C3).** n < 8: inget intervall. 8 ≤ n < 40: e ~ ē + s·√(1 + 1/n)·t(n − 1), med s som
  stickprovs-SD (ddof = 1), och ē ingår. n ≥ 40: den empiriska fördelningen, kvantiler enligt Hyndman–Fan typ 6
  (numpy `weibull`).
- **Nivåer (G-C).** Intervallen 50, 80 och 95 %, kvantilerna 2,5, 10, 25, 50, 75, 90 och 97,5 %.
- **Poäng (F-C6).** För den empiriska fördelningen är CRPS = medel|x_i − e| − Σ|x_i − x_j|/(2n²). För t-fallet
  används sluten form. PIT för den empiriska fördelningen är mittrangen (#{x > e} + 0,5·#{x = e} + 0,5)/(n + 1),
  utan randomisering.
- **Kalibrering (F-C5).** Täckningen för en nivå underkänns när Holm-p < 0,10 över de tre nivåerna, i ett t-test av
  träffandelen mot L. Variansen är max(Newey–West, L(1 − L))/n, och p kommer från t(n − 1). Det binomiala 90 %-bandet
  (5:e–95:e percentilen av Bin(n, L)/n) redovisas bredvid. En underkänd kalibrering byter inte huvudmodell.
- **Horisonter (F-C7)** ingår inte. De hör till D2-posten.

## Tolkningar som koden gör (orkestreraren bekräftar eller ändrar)

1. **"Plus de skarpa felen" (F-C4).** En månad eller ett kvartal som har både en skarp prognos och en rekonstruktion
   i backtesten räknas en gång, med det skarpa felet. Om båda räknades skulle perioden få dubbel vikt. (`merge_live`)
2. **Urval i utvärderingen.** Varje modell utvärderas på alla sina backtestrader där den har en fördelning, alltså
   inte bara på punktutvärderingens gemensamma urval. Skälet är att N1:s V1 och V2 har fel först från 2024Q2 (n = 9),
   så ett urval som är gemensamt för alla modeller vore tomt för N1. Delperioden från 2023 (N2 2023-01, N1 2023Q1)
   redovisas separat, som för punktprognoserna.
3. **Jämförelse mellan modeller.** Medel-CRPS per modell redovisas. Ett DM-test på CRPS (förlust ≥ 0) mot den bästa
   av B0 och B1 räknas på parvis gemensamma rader, med Holm över varianterna. Det redovisas bara som information,
   eftersom registret inte har någon regel för CRPS-jämförelse och huvudmodellen väljs på MAE. N1b räknas poolat
   (`engine.pooled_dm`), och felpoolerna blandar aldrig bolag.
4. **Den skarpa filen bär sin fördelning.** Poolen (4 decimaler), metoden och t-parametrarna sparas i
   `distribution` i `forecasts/<nowcast>/<period>.json`. Scorecarden poängsätter den sparade fördelningen och räknar
   aldrig om den, eftersom tidsstämpeln är beviset. Hemsidan visar bara huvudmodellens intervall, inte poolen.
5. **Kvantilpoäng** (medel av pinball-förlusten över de sju kvantilerna) räknas som extra information. Den används
   inte i någon regel.
6. **En konstant pool** (förekommer bara i syntetiska data) blir en punktmassa i stället för en t-fördelning med SD 0.

## Kända begränsningar

- **N1:** B0, B1 och B2 får t-fördelning i flera år framåt (färre än 40 kvartal). V1 och V2 får inget intervall förrän
  de har 8 egna fel. Det dröjer till cirka 2026Q2 räknat från 2024Q2. Kalibreringen för N1 går inte att bedöma med så
  få kvartal.
- **N2:** B2:s pool blandar månader med guidance och månader där B2 föll tillbaka till B1 (före guidancen fanns).
  De tre månaderna i ett kvartal delar guidance, så träffarna är beroende. Därför används Newey–West-variansen.
- **Bakåtfyllda indikatorer** (`us_imports_tw_m`, `us_constr_datacenter`) gör V1:s och V2:s rekonstruerade fel något
  för optimistiska, samma förbehåll som för punktprognoserna. Felen blir då för små, och intervallen för smala.
- Kalibreringen av de skarpa intervallen blir meningsfull först efter cirka 12 skarpa månader för N2.

## Kod

- `src/ai_tracker/nowcast/intervals.py`: pooler as-of (`pool`, `live_errors`, `merge_live`), fördelningen
  (`ErrorDistribution`), CRPS (empirisk, normal, t), PIT, täckningstest, binomialt band, `calibration`, `evaluate`,
  `live_block`, `score_live`. Flaggan `ENABLED` finns här.
- `n1.py` och `n2.py`: `interval_scores`, `evaluate_intervals` (backtest) och `live_distribution` (skarp fil).
  Allt anropas bara när flaggan är på.
- `pipeline.py`: scorecarden får avsnittet "Intervall" (huvudmodellens intervall per prognos, täckning med binomialt
  band och CRPS per variant) när flaggan är på.
- `site/`: prognossidan visar huvudmodellens 80 %-intervall i tabellen, 50 %- och 95 %-intervallen i diagrammet,
  och en tabell med täckning och CRPS när flaggan är på.
- Tester: `tests/test_intervals.py` (pooler as-of, läckage, täckning på iid-normalfel, t-fallets exakta täckning,
  typ 6 på små pooler, CRPS mot sluten form och numerisk integral, likformig PIT, överkonfident modell underkänns,
  binomialt band, skarpa fel i poolen) och `tests/test_intervals_integration.py` (backtest, skarpa filer, scorecard
  och hemsida med flaggan på, oförändrat med flaggan av).

## Så körs det (orkestreraren, efter merge)

1. Sätt `ENABLED = True` i `src/ai_tracker/nowcast/intervals.py`, i en egen commit som hänvisar till G-C.
2. `python -m ai_tracker.nowcast backtest n2` och `python -m ai_tracker.nowcast backtest n1` skriver
   kalibreringstabellerna efter punktresultaten.
3. Från nästa skarpa prognos får filerna fältet `distribution`, och scorecarden och hemsidan visar intervallen.
