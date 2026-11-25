# CLAUDE.md – ai-rollout-tracker

## Vad projektet är

Projektet följer **AI-utrullningen i världen kvantitativt, neutralt och öppet**. Det ska synas när
utvecklingen ändrar takt, i båda riktningarna. Systerprojekt till kpif-nowcast, och det använder samma
metod: versionerad data, förregistrering, tidsstämplade prognoser och ärlig rapportering.
Plan och faser finns i [`docs/plan.md`](docs/plan.md).

**Målet är bästa möjliga lösning.** Varje val ska ge snabb och effektiv progress med kvalitet. Metoden
följer målet: ramverket från kpif-nowcast används där det passar och byts ut där något annat är bättre.
Det är inte ett lärprojekt.

Arbetssättet är agentiskt: agenten skriver koden och gör räknejobbet, Johannes styr, granskar och fattar
besluten. Johannes har bakgrund inom BI och data engineering och kan SQL, pipelines och datakvalitet väl.
Förklara inte det.

## Arbetsregler

1. **Neutral spårning.** Varje gren (G1–G9) beskrivs med nivå, takt, förändring i takt och överraskning.
   Inga larmnivåer, och inget val av riktning.
2. **Förregistrering.** Mått, beräkningssätt och tillståndsregler låses i `docs/mattregister.md` innan
   data analyseras. Ändringar loggas med datum och motivering.
3. **Flagga läckagerisk direkt.** Varje värde har `known_from`: inlämningsdatum för SEC-dokument,
   publiceringsdatum för övrigt. Inga features beräknas över hela perioden.
4. **Jämför alltid mot baslinje:** naiv baslinje och bolagens egen guidance där den finns.
5. **Var ärlig om osäkerhet.** Kvartalsserier är korta och har regimbrott. Säg när något kan vara slump,
   och när något inte gick att verifiera.
6. **Förklara kort** de modelleringsval som spelar roll. Stanna bara vid verkliga beslutspunkter och ge
   en rekommendation, inte en meny.
7. **Beslutsloggen** (`docs/beslutslogg.md`) uppdateras kort vid viktiga val.

## Licenser och publicering (publikt repo)

- Data committas aldrig. Allt hämtas med skript så att det är reproducerbart.
- Varje `Spec` har `license`. `publish=True`, alltså att visas på den publika sidan, kräver en kontrollerad licens.
- Från rapporter och transkript publiceras bara extraherade siffror med källhänvisning, aldrig själva texten.
- LLM-extraherade värden sparas med dokument, plats och ordagrant citat, och stickprovsgranskas innan de används.
- Varje serie har en klass för kommersiell användning (`ja`, `nej`, `okänd`, `ai_tracker.licenses`), oberoende av
  `publish`. Klassen bygger på dokumenterad licenstext och gissas aldrig, och `catalog.validate` kräver den. Nya
  serier väljer öppna licenser (public domain, CC0, CC BY, MIT) när det finns ett val.
- Inga hemligheter i koden (`.env`). Inga personliga uppgifter och inga innehav i repot.
- API:er som kräver kontaktuppgift i User-Agent (SEC) får en generisk klientidentitet från `.env`.

## Agentiskt arbete

- Bedöm arbete i agentlinsen: parallella spår, inte människotimmar. Enheten är ett **agentspår**, en
  avgränsad leverans med tester i egen worktree. Kostnad per spår står i
  [`docs/agentkalibrering.md`](docs/agentkalibrering.md).
- **Värde för Johannes först** ([`docs/riktning.md`](docs/riktning.md), avsnitt 10): pröva varje spår mot
  värdefiltret (läser han det inom en månad, är det ledande, vad kostar det per kvartal). Full oberoende granskning
  för kärnserier, tillståndsregeln, prognoser och extraktioner han agerar på. Katalogserier får spårets egna
  kontroller och datatester. Färre och större spår (4–5 per körning).
- De verkliga flaskhalsarna är statistisk budget, datatillgång och licenser (BLOCKED), verifiering
  (ett granskningsspår per positivt resultat) och kalendertid (kvartalsutfall).
- Agenten får committa, merga och pusha till `main` när pytest är grönt på det sammanslagna resultatet och
  reglerna ovan är uppfyllda. Parallella spår körs på egna grenar (`auto*/<spår>`).
- **Skyddat:** skarpa prognoser i `forecasts/` och ögonblicksbilder i `snapshots/` skrivs bara av
  rutinen och skrivs aldrig om i efterhand, eftersom tidsstämpeln är beviset.
- **Aldrig:** force-push, omskrivning av historik på main, radera andras grenar, data eller hemligheter i git.

## Faser

Se `docs/plan.md`, avsnitt 8. Uppdatera här när en fas är klar.

- **Fas 0** ✅ ramverk och CI
- **Fas 1** ✅ källor och licenser (`docs/datakallor/`)
- **Fas 2** ✅ cirka 130 serier i G1–G9 (`docs/kallor/`), måttregister låst (`docs/mattregister.md`)
- **Fas 3** ✅ N1 (capex) och N2 (TSMC) med backtest. Läckagegranskning R1 och rättning X1
- **Fas 4** ✅ guidance (E1), granskning R2. **N2:s huvudmodell är B3 (TSMC:s guidance korrigerad för systematisk
  avvikelse, från 2026-11-24 efter granskning R7)**, N1:s huvudmodell är B1
- **Fas 5** ✅ tillstånd per gren (`python -m ai_tracker.state`), månatlig ögonblicksbild från 2026-11-30
- **Fas 6** ✅ hemsida på GitHub Pages (`python -m ai_tracker.site build`, `pages.yml`; ägaren aktiverar
  Pages en gång, se `docs/drift.md`). Månadsbrev ✅ (`python -m ai_tracker.letter`, committas med ögonblicksbilden)
- **Steg 2** ✅ våg 0–4 (`docs/steg2/plan.md`, status `docs/steg2/STATUS.md`): cirka 400 serier, flödesmodell med
  avstämningar, N3–N6, intervall, faktormodell (skugga), regimmodell (i månadsbilden), prognoser 1–8 kvartal (skugga),
  flödesvy, kvartalsrapport. Holdouten för C3/C4 är öppnad och utvärderad (`docs/holdout_logg.md`)
- **Körning 13** ✅ (`docs/riktning.md`): diffusionsindex v2 med källfamiljer, officiellt från ögonblicksbilden
  2026-11-30 (v1 redovisas bredvid). Klass för kommersiell användning per serie (`ai_tracker.licenses`).
  Avskrivningar och PP&E (P1), nyttjandeperioder (P2a), intäktskrav som avstämningar (P2b), N7 som backtest (ingen
  variant klarar regeln, B1). Revideringar av guidance och överraskningsindex (F1). BNP-bidrag, elpris och PPI (M1).
  Serverimport per land (M2): årsfilen och HS-serierna (hämtade med `CENSUS_API_KEY` 2026-11-25)
- Drift: `docs/drift.md` (veckohämtning, skarpa prognoser N2 dag 5 och N1 kvartal + 20 dagar, ögonblicksbild vid månadsslut)

## Tekniska konventioner

- Python. Kod i `src/ai_tracker/`, tester i `tests/`, `python -m pytest -q`.
- Observationstabellen: `data/observations.parquet` med kolumnerna series, freq, period, value,
  known_from, source och fetched_at. Läs med `observations.as_of()`. Datatester finns i `warehouse.py`.
- Backtest körs med **expanding window / rolling origin**: träna bara på data före varje prognostidpunkt.
- Kod och kommentarer på engelska, dokumentation i `docs/` på svenska.
- Redigera filer med svenska tecken via Edit/Python, aldrig PowerShell Get/Set-Content.
