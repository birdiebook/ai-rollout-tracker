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
| 2026-11-23 | 1 | I6 pris vid fast förmåga | bygge (två källor, mappning) | ~15 | ~45 | – | 2 serier (ECI + GPQA), git-historik LiteLLM, mappning 123 modeller, tröskel låst, 29 tester |
