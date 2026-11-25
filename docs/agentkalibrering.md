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
| 2026-11-24 | 11 | R8 granskning G2 Arena-pris | granskning (adversariell) | ~22 | ~53 | ~251 | UNDERKÄND: golvmått, stegfunktion, Arena-läckage hittat, 3 tester |
| 2026-11-24 | 12 | W5 startsidan | webb (sida) | ~34 | ~86 | ~301 | kedja, tre frågekort, ränder, genererad rubrik, 23 vitest + e2e |
| 2026-11-24 | 12 | W6 led- och grensidor | webb (sidor) | ~34 | ~103 | ~296 | /flode, /flode/L*, /gren/G*, multiplar, inhållna rutor, e2e |
| 2026-11-24 | 12 | W7 serieinstrumentet | webb (2 enheter) | ~41 | ~112 | ~309 | 387 seriesidor, asOf-API (golden mot Python), revisionsvy, CSV, permalänk, 130 vitest |
| 2026-11-24 | 12 | W8 prognossidor | webb (sidor) | ~46 | ~116 | ~312 | översikt, sida per nowcast och skarp prognos, facit, kalibrering, D2-solfjäder |
| 2026-11-24 | 12 | X5 rättning Arena | rättning (läckage + priser) | ~48 | ~122 | ~323 | tavlor versionerade per commit, daterade prisrättningar, ingen G1-historik ändrad |
| 2026-11-24 | 13 | K2 licensnivå | regler och metadata (ingen data) | ~40 | ~55 | – | `licenses.py` (regler, overrides, kurerad regel, härledning), krav i `validate`, CLI, 64 tester, `datakallor/licensniva.md` |
| 2026-11-24 | 13 | K1 källfamiljer och index v2 | regel + konsumenter (förregistrerad) | ~70 | ~95 | – | registerpost med familjetabell (G1–G9), `FAMILIES` med paritetstest, v2 officiell och v1 bredvid, brev, kvartalsrapport, gamla sidan, paket 1.1.0 (scheman, fixturer), 13 nya tester; backcast väntar på data |
| 2026-11-24 | 13 | P2a nyttjandeperioder | extraktion (agentläsning, 416 SEC-dokument, citat) | ~45 | ~90 | – | 305 kodade rader (68 policy, 21 ändringar, 213 effekter, 3 stopp), 30 katalogserier, stickprov 0 fel av 305, 43 tester |
| 2026-11-24 | 13 | M1 makrokanalen (BEA, BLS) | 2 källor, riktiga vintages ur releasearkiv, regeldatering | ~75 | ~95 | – | 12 serier (8 BEA kvartal, 4 BLS månad), 107 BEA-vintages, BLS-releasekalender 1999–, 21 tester |
| 2026-11-24 | 13 | P1 avskrivningar och anläggningstillgångar | källa + katalog (XBRL, egna taggar ur instanser, förregistrerat) | ~95 | ~75 | – | 26 serier, 1 061 rader, 3 deklarerade omräkningar, 9 handkontroller med accession, 15 tester |
| 2026-11-24 | 13 | F1 revideringar och överraskning | mått + härledda serier (förregistrerade) + deterministisk tolkning | ~95 | ~85 | – | 14 serier (12 F1, 2 TSMC capex-budget), avsnitt `expectations`, 76 revideringar, överraskning för 4 bolag, 44 tester |
| 2026-11-24 | 13 | L1 G8-kartläggning | kartläggning (källor, licenser, design), bara dokument | ~35 | ~100 | – | 21 källor och värdar testade, 6 exponeringsmått, G8 v2-förslag (4 familjer) med MDE-metod, 0 kodändringar |
| 2026-11-24 | 13 | M2 Census-import per land (HS och end-use) | källa bakom nyckel + nyckelfri årsfil (sökning efter nyckelfri källa, metadata, xlsx) | ~35 | ~95 | – | 21 årsserier hämtade (end-use 21300/21301/21320 × 7 länder), 35 HS-månadsserier byggda men BLOCKED (`CENSUS_API_KEY`), `keyed.py` (SKIPPED i stället för FAILED), 23 tester |
| 2026-11-24 | 13 | P3 N7 avskrivningar 1–8 kvartal | modell + backtest (förregistrerad, poolad DM per horisontgrupp) | ~45 | ~55 | – | registerpost före kod, `n7.py` (V1, V2, grupperad DM, Holm 6), 26 tester, beslut B1 i alla grupper |
| 2026-11-24 | 13 | P2b intäktskrav | härledning (avstämningar, förregistrerat, vägda termer) | ~50 | ~60 | – | 5 avstämningar, 4 nya tester, känslighet och bolagstabell, resultatdokument; rättat nyckelfel i `observations.combine` (+1 test) |
| 2026-11-24 | 13 | R10 granskning av licensnivån | granskning (regler, 37 källor, 6 grenar lästa, ingen data; två sessioner över en kvotreset) | ~55 | ~115 | – | `granskning/r10_licensniva.md`, 12 fynd (4 must_fix, 2 should_fix, 6 note), 23 strikta xfail och 31 vakttester, rättningarna provade i minnet |
| 2026-11-24 | 13 | R12 granskning av M1 (datering, läckage) | granskning mot primärkällor (BEA, BLS, ALFRED) | ~55 | ~75 | – | 12 releaser omlästa, 107 mot BEA:s nyhetsarkiv, 6 PPI Detailed Reports, 2 must_fix (PPI 518210 före införandet, blandade basår), 12 tester (6 strikt xfail) |
| 2026-11-24 | 13 | R11 granskning F1 | granskning (primärkällor: sec.gov, microsoft.com; omräkning) | ~80 | ~95 | – | 10 fynd (2 måste), saknad Microsoft-rad funnen i samtalet, 18 TSMC-dokument kontrollerade, 6 strikta xfail + 3 tester |
| 2026-11-24 | 13 | R14 granskning av P1 | granskning mot primärkälla (R-sidor i 30 inlämningar, ombygge) | ~75 | ~85 | – | 15 handkontroller, 1 must_fix (MSFT 2024Q3 på gammal bas), 3 should_fix, 9 tester varav 2 strikt xfail |
| 2026-11-24 | 13 | R9 granskning index v2 | granskning (förregistrering, kod, licens, paket, CLI) | ~40 | ~85 | – | GODKÄND MED ANMÄRKNINGAR, inga must_fix; 4 should_fix (webbens ordlista, fixturbygget läser miljön, registerteckning om effekten, kvartalstest), 9 noter; 50 tester varav 4 strikta xfail |
| 2026-11-24 | 13 | R15 granskning av P2a | granskning (extraktion, 91 SEC-dokument nyhämtade, egen sökning i 416) | ~80 | ~95 | – | 0 fel av 65 i stickprovet och 0 av 305 vid fullständig läsning, 21 av 21 ändringar, 4 should_fix och 2 noter (dokumentation), 28 tester varav 6 strikta xfail |
| 2026-11-24 | 13 | X7 rättning av licensnivån (R10) | rättning (regler, deklarerade rader, ingen data) | ~50 | ~75 | – | R10-1–R10-6 och R10-8 rättade, 23 xfail-fall (7 tester) blev vanliga tester, 6 nya tester, klasser kontrollerade på 7 grenar, `licensniva.md` omgenererad (346/34/108) |
| 2026-11-24 | 13 | X6 rättning efter R9 (index v2) | rättning (kod, register, tester) | ~35 | ~70 | – | S2 (schema i kontexten, isolering i conftest), S3 (registeranteckning), N1 (exakt index), N5–N8; 3 strikta xfail blev vanliga tester, 11 nya tester; S1 hör till webbsessionen |
| 2026-11-24 | 13 | X9 rättning av M1 efter R12 | rättningsspår (kod, omräkning, daterad registerpost) | ~35 | ~55 | – | R-1–R-8 (R-3 bara dokument), 6 strikt xfail vända, 7 nya tester, 5 serier omräknade (`us_imp_computers_real` 2007Q1–, PPI 518210 från 2002-02-15, BLS-kalender från 1994-01) |
| 2026-11-24 | 13 | X11 rättning av P1 efter R14 | rättning (regel i kod, ombygge från rå-cache, register och dokument) | ~45 | ~60 | – | omräkning genom summorna, 2 värden i `dep_msft` ändrade, 26 serier ombyggda (1 063 rader), 2 strikta xfail nu vanliga tester, 5 nya tester |
| 2026-11-24 | 13 | R13 granskning av M2 (Census HS och end-use) | granskning mot primärkällor (census.gov, API-metadata, guide, villkor) | ~60 | ~75 | – | GODKÄND MED ANMÄRKNINGAR: inget läckage, veckovägen utan nyckel bevisad på kopia av bastabellen, 10 av 10 årsrevisioner och Exhibit 7/13 kontrollerade, R13-1 – R13-5 (strikt xfail), 12 passerande tester |
| 2026-11-24 | 13 | R16 granskning av N7 (P3) | granskning (oberoende omräkning, SEC-källor, negativt resultat) | ~60 | ~85 | – | omräkning av 10 prognoser och 12 DM-test, trunkering 280 par, 17 värden + 3 dokument mot SEC, 31 tester + 11 på verklig data, 1 strikt xfail |
| 2026-11-24 | 13 | X13 rättning efter R16 (N7) | rättning (resultattext, omräkning utan logg) | ~15 | ~30 | – | R-1 och R-2–R-5 i `n7.md`, strikt xfail blev vanligt test, FY2021-effekten kontrollerad i 10-K, 69/69 N7-tester på P3:s tabell |
| 2026-11-24 | 13 | X12 rättning av P2a efter R15 | rättning (dokumentation, not, läsmängd som kod) | ~35 | ~60 | – | 4 should_fix och N-1, N-2 rättade, registerpost, `supplementary()` täcker alla 82 rader utanför kandidaterna, 11 av 305 fel med gamla kontrollen bekräftat, serierna oförändrade (203 rader), 2 nya tester, 6 xfail blev vanliga |
| 2026-11-24 | 13 | X10 rättning av M2 efter R13 | rättning (kod, register, dokument, ingen nyckel) | ~50 | ~65 | – | R13-1–R13-5 rättade (5 strikta xfail nu vanliga tester), R13-7–R13-9 också, delning per år vid timeout, `check`-kommando för första hämtningen, 14 nya tester; R13-6 blockerad (ingen nyckel), 210 årsrader omhämtade och identiska |
| 2026-11-24 | 13 | X8 rättning F1 efter R11 | rättning (data, kod, register, två känsligheter, ny tolkning) | ~80 | ~100 | – | 3 CSV-rader verifierade mot källan, brottet flyttat (0,67 → 0,62), stängningsversion, cache, publiceringsgrind, US$-intäkt TSMC (40 kvartal), grannkontroll 81 dokument, 12 nya tester, 6 xfail → pass |
| 2026-11-24 | 13 | Integration körning 13 | integration (11 mergar, uppföljning över spår, data, dokument, grindar) | ~50 | ~230 | – | 11 mergar utan förlorad loggpost, K2 klassar 633 serier, P2b omräknat, N7 omkört (beslut oförändrat), 112 serier in i basen, backcast v1/v2, läsanvisningar; webbens vitest röd av paket 1.1.0 (20 tester, ägs av webbsessionen) |
| 2026-11-24 | 13 | W9 tidsresa | webb + läckagegräns | ~56 | ~110 | ~342 | globalt as_of, en grind (gate.ts), golden mot Python-replay, uppspelning |
| 2026-11-24 | 13 | W10 avstämningar och regim | webb (sidor) | ~36 | ~121 | ~312 | /avstamningar, /regim, bidragsdiagram, holdoutresultat, konstanter testade mot Python |
| 2026-11-24 | 13 | W11 utforskbar metod | webb (interaktiv) | ~48 | ~123 | ~344 | dödband, intervall, as_of, Holm-stege; golden mot Python-motorn |
| 2026-11-25 | 13 | W12 navigering och delning | webb (layout, sök, delningsbilder) | ~105 (två pass, kvotstopp) | ~180 | ~380 | ⌘K-sök, djuplänkar, 421 delningsbilder, citeringsrad; hittade basvägsfelet |
| 2026-11-25 | 14 | R-W1 licens och läckage | granskning (adversariell) | ~43 | ~103 | ~274 | licens OK; 5 tidsreseläckor rättade; backfill-gräns fel; härledbar riktning för inhållna |
| 2026-11-25 | 14 | W13 månadens berättelse | regel + Python + webb | ~59 | ~120 | ~390 | regel låst före körning (1ca59b8), story.py, /manad/*, scrollytelling |
| 2026-11-25 | 14 | RW1-X rättning | rättning (schema, CI, scan) | ~43 | ~132 | ~285 | backfill_fetched, commit per skarp prognos, scan-build, tidlös citering |
| 2026-11-25 | 14 | R-W3 neutralitet | granskning | ~20 | ~98 | ~230 | speglingstest symmetriskt; 3 mallasymmetrier rättade; 4 krav före byte av huvudsida |
| 2026-11-25 | 14 | R-W2 tillgänglighet | granskning + rättning | ~56 | ~116 | ~270 | axe 0 i 54 körningar; 4 tangentbordsfel rättade; LCP 0,8 s; TBT kvar (P1) |
| 2026-11-25 | 14 | KR1 spread vid emission | extraktion (deterministisk parser, villkorsbilagor) | ~57 (varav 16 full testsvit) | ~115 | – | 239 tranchar ur 39 FWP, 11 katalogserier, självkontroll 0 fel, kontroll mot 39 slutliga prospekttillägg, 37 tester |

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

## Körning 11–12, iakttagelser (2026-11-24)

- Webbspår tar 34–46 minuter, dubbelt så lång tid som dataspår. Det mesta går åt till grindarna: bygg mot riktigt paket
  (2 min), Playwright (2–3 min) och pytest (7 min), ofta flera gånger. Räkna ett webbspår som cirka 1,5 dataspår.
- Parallella webbspår krockade på förhandsvisningsporten 4173. Playwright testade då tyst ett annat spårs bygge. Ge varje
  spår en egen `PW_PORT`.
- Granskningsspåren hittar fortfarande verkliga fel (R8: Arena-läckaget). Behåll en granskning per ny serie som ska räknas.
- Kvotgränsen nåddes med fem samtidiga spår. Spåret som stoppades kunde återupptas med SendMessage när kvoten var tillbaka,
  utan att något arbete gick förlorat. Med webbspår är 3–4 samtidiga spår per 5-timmarsfönster rimligt.
- Basvägsfelet (`/next` i stället för `/<repo>/next` på en projektsida) syntes inte i några lokala tester. Testa en gång
  mot den publicerade adressen efter första publiceringen.
