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
| 2026-11-23 | steg 2, våg 0 | I1 delad data | infrastruktur (lager, merge, skript) | ~12 | ~20 | – | delad bas + skrivtabell per spår, `datamerge` med datatester, `scripts/new_track.sh`, delad rå-cache, 14 tester |
| 2026-11-24 | 11 | G2A pris vid fast Arena-förmåga | bygge (mappning, förregistrerad referens) | ~29 | ~68 | ~297 | 2 varianter (A gpt-4-0314, B gpt-4o), mappningstabell, avvecklingsregel; väntar på granskning R8 |
| 2026-11-24 | 11 | W3 datakontrakt | infrastruktur (paket, schema, licensskanning) | ~35 | ~77 | ~312 | `site_bundle`, 14 JSON-scheman, versions-v1, 385 serier, 60 syntetiska fixtures |
| 2026-11-24 | 11 | W4 + W2 skelett, designsystem, CI | webb (SvelteKit, tokens, primitiver, CI) | ~29 | ~93 | ~291 | 41 vitest, 78 Playwright, axe, budgetar, `pages-next.yml`, en deploy |
| 2026-11-24 | 13 | M2 Census-import per land (HS och end-use) | källa bakom nyckel + nyckelfri årsfil (sökning efter nyckelfri källa, metadata, xlsx) | ~35 | ~95 | – | 21 årsserier hämtade (end-use 21300/21301/21320 × 7 länder), 35 HS-månadsserier byggda men BLOCKED (`CENSUS_API_KEY`), `keyed.py` (SKIPPED i stället för FAILED), 23 tester |
| 2026-11-24 | 13 | R13 granskning av M2 (Census HS och end-use) | granskning mot primärkällor (census.gov, API-metadata, guide, villkor) | ~60 | ~75 | – | GODKÄND MED ANMÄRKNINGAR: inget läckage, veckovägen utan nyckel bevisad på kopia av bastabellen, 10 av 10 årsrevisioner och Exhibit 7/13 kontrollerade, R13-1 – R13-5 (strikt xfail), 12 passerande tester |

## Körning 1, sammanfattning (2026-11-23, orkestrerare)

- Omkring 25 spår på cirka 2,5 timmars väggtid, 4–7 parallella spår. Källspår tog 9–20 minuter, bygg- och modellspår
  10–25 minuter och granskningsspår 22–27 minuter. arXiv-backfill (I5) tog 85 minuter på grund av hastighetsgränser.
- Granskningsspåren gav körningens viktigaste fynd: R1 hittade ett verkligt läckage (C30 före 2024-07), och R2 hittade
  en saknad guidance-rad. Behåll ett granskningsspår per positivt resultat och per ny datakälla med datum.
- Merge-konflikter uppstod nästan bara i `docs/beslutslogg.md` och `docs/agentkalibrering.md`. Automatisk
  upplösning (behåll båda) fungerade varje gång. Serier i egna moduler (`series/<källa>.py`) gav inga kodkonflikter.
- Ny flaskhals: att slå ihop data mellan arbetskopior (varje spår har sin egen `data/`). Nästa gång: en delad
  läs-kopia plus en skrivkopia per spår.

## Delad data från steg 2 (spår I1)

- Nya spår skapas med `scripts/new_track.sh <namn> <grenprefix>`. Spåret läser basen i main-utcheckningens `data/`
  och skriver bara i sin egen `data/`. Ingen kopia av `data/` behövs.
- När spårets kod är mergad kör orkestreraren `python -m ai_tracker.datamerge /home/user/wt/<namn>/data`. Den kör
  datatesterna och vägrar skriva om de fallerar. Den tar cirka 10 sekunder för hela basen och kan köras om utan
  effekt. Mät tiden per merge i nästa körning. Detaljer finns i `docs/drift.md` (Delad data).
