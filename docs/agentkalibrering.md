# Agentkalibrering: vad ett spår kostar

En rad per spår, fylls på efter varje körning. Tumreglerna justeras när siffrorna ändras.

## Tumregler (startvärden från kpif-nowcast, körning 2)

- Ett väl avgränsat spår med tester: cirka 13–18 min, 40–60 verktygsanrop och 180–200k tokens.
- Datatunga spår med många källor och udda format (PDF, Excel) tar ungefär dubbelt så lång tid. Räkna dem som 2 spår.
- Granskningsspår mot externa källor tar 70–75 min, styrt av väntan på nät. Starta dem tidigt.
- Ett 5-timmarsfönster rymmer ungefär 25–30 spår. Kör 5–6 spår parallellt och merga i omgångar.
- Väntat för det här projektet: fler PDF- och HTML-källor (rapporter, TSMC, Korea) och LLM-extraktion
  ger fler datatunga spår än i kpif-nowcast.

## Mätningar

| Datum | Körning | Spår | Typ | Tid (min) | Verktygsanrop | Tokens (k) | Leverans |
|---|---|---|---|---|---|---|---|
| 2026-11-23 | – | Fas 0 | ramverk | ~15 | ~25 | – | katalog, observationer, kalender, datatester, utvärdering, CI, 15 tester |
| 2026-11-23 | 1 | I4 Indeed, vast.ai, EIA | 3 källor, git-vintages, xlsx-arkiv | ~16 | ~50 | – | 16 serier (9 Indeed dag, 7 EIA månad), vast.ai BLOCKED (villkor), 21 tester |
| 2026-11-23 | 1 | I6 pris vid fast förmåga | bygge (två källor, mappning) | ~15 | ~45 | – | 2 serier (ECI + GPQA), git-historik LiteLLM, mappning 123 modeller, tröskel låst, 29 tester |
| 2026-11-23 | 1 | I3 Census/EU | datatungt (xlsx, PDF, 6 källor) | ~22 | ~55 | – | 28 serier (BTOS 12, C30 2, G.17/M3 2, BEA 4, handel 2, Eurostat 4, SCB 2), 2W-frekvens, 17 tester |
| 2026-11-23 | 1 | F3-N1 capex-nowcast | modell + backtest (förregistrerad) | ~12 | ~30 | – | motor för rolling origin, B0/B1/V1/V2, N1 + N1b poolat, befordran (B1), skarp skrivare, 17 tester |
| 2026-11-23 | 1 | I7 Fed G.17 primärkälla | källbyte, vintages ur releasearkiv | ~13 | ~38 | – | 2 serier (G3344, G3341), 135 riktiga vintages från 2016-04-15, DDP + reserv, cache, `--rebuild`, 9 tester |
| 2026-11-23 | 1 | F5 tillstånd och ögonblicksbild | regler + motor + drift (förregistrerat) | ~18 | ~35 | – | mått per serie, diffusionsindex, tillstånd, skrivare, backcast 2019-01–2026-10, `snapshot.yml`, 39 tester |
| 2026-11-23 | 1 | E1 guidance | extraktion: deterministisk tolkning + agentläsning, 3 värdar | ~35 | ~95 | – | 24 serier (9 TSMC, 15 capex), 101 kurerade värden, stickprovsskript (0 fel), 28 tester |
