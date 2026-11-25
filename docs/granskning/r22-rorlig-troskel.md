# R22 – granskning av pris vid rörlig förmågetröskel (Q1)

Granskningsspår R22, körning 14, 2026-11-25, gren `auto14k/r22-rorlig-troskel` (bas `auto14k/q1-rorlig-troskel`,
`415654e`). Granskat: `g2_price_rolling12_arena` (L = 12), `g2_price_rolling6_arena` (L = 6), `g2_price_frontier_arena`
(frontpris) och `g2_price_rolling12_eci`, byggda av Q1 (`src/ai_tracker/series/price_rolling.py`, registerposten
"2026-11-25 – Q1", [kallor/g2_rorlig_troskel.md](../kallor/g2_rorlig_troskel.md), `tests/test_price_rolling.py` och
Q1-blocket i `licenses.py`).

Underlag: Q1:s spårtabell (118 rader), indata laddade med `arena_price._inputs()` och `price_capability._inputs()` (samma
cache som Q1), Arenas Space-filer (`elo_results_<datum>.pkl`), datasetets `text_full` i HEAD `62968a5`, LiteLLM-repot
(`git show <sha>:model_prices_and_context_window.json`), Epochs `benchmark_data.zip` från 2026-11-25 (`eci_scores.csv`,
README och `*_external.csv`), METR:s YAML och Arenas `agent`-parquet. Blockerat: `arena.ai` (proxyn svarar 403, och
`lmarena.ai` skickar dit med 301).

Prövningarna gjordes med engångsskript utanför repot (den oberoende omräkningen, handkontrollerna,
kandidatspridningen och driftmätningen). De läser samma cache och samma råfiler som ovan.

**Ingen analys av förlopp gjordes.** Inga takter eller trender räknades. Känsligheterna nedan prövar reglerna. De är
inte resultat.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering | **OK.** Posten kom före kod och värden, och det som lästes före posten stämmer med spårets skript |
| 2. Referens, tröskel och efterföljare | **OK enligt registret.** Avvikelsen (referensen enligt det som är känt vid d) är motiverad och läcker inte. **Anmärkning:** efterföljarregeln är instabil med gamla Δ (R22-3, R22-5), och två namnbyten utan överlapp saknas (R22-2) |
| 3. Priser, kanal och blandning | **OK** |
| 4. Omräkning | **OK.** Alla 118 rader räknades om oberoende, och 17 versioner och månader kontrollerades för hand mot råfilerna |
| 5. Datering och versioner | **OK för serierna.** Ett kantfall i versionsregeln (R22-1) påverkar inget värde i dag |
| 6. Mättnad | **OK för Arena-varianterna**, och dokumentet säger rätt. ECI-varianten ligger på golvet i 7 av 18 månader, och det står inte i dokumentet (R22-4) |
| 7. Licens | **OK** |
| 8. `backfill` nedströms | Not. Märkningen följer registret, men webbens text om bakåtfyllnad blir missvisande |
| 9. Kostnad per uppgift | **BLOCKED** bekräftat |

**Slutdom: GODKÄND MED ANMÄRKNINGAR som katalogserier.** Inget läckage och inga fel värden enligt de registrerade
reglerna. Fem should_fix (R22-1 – R22-5) och noter. `g2_price_rolling12_arena` är **inte redo som kärnserie**: i 5 av 22
månader beror värdet på vilken efterföljare som bär tröskeln (punkt 2). Det ska rättas med en ny registerpost innan
serien prövas som kärnserie.

## 1. Förregistrering – OK

| Tid (UTC) | Commit | Innehåll |
|---|---|---|
| 09:12:15 | `b5c652c` | Registerposten och avsnitt 1 i källdokumentet |
| 09:16:43 | `6c00c48` | Kod och syntetiska tester |
| 09:42:19 | `415654e` | Värden, handkontroller och känsligheter |

- `git diff b5c652c 415654e -- docs/mattregister.md` är tom. Posten ändrades inte efter värdena.
- Spårets arbetsfiler stämmer med avsnitt 1. `meta_refs.py` (09:07) och `meta_succ.py` (09:09) skriver bara namn,
  närvaro och antal gemensamma tavlor. De rangordnar efter rating men skriver inga ratingar och läser inga priser.
  Första beräkningen av värden (`compute.py`) skrevs 09:16:53, efter kodcommiten. Spårtabellen skapades 09:18:29.
- Före posten läste spåret ECI-fronten (`g1_epoch_eci_frontier`), som är tröskeln i ECI-varianten. Den användes för
  att se när fronten når 128 och därmed första månaden. Golvet 128 kommer från `model_map`:s täckning, inte från
  utfallet. Det står öppet i dokumentet.
- Begränsning: git och filtider visar inte att inga värden räknades någon annanstans. Inget tyder på det.

## 2. Referens, tröskel och efterföljare

### Referensen enligt det som är känt vid d – OK, avvikelsen håller

- Verifierat: alla 56 tavlor som publicerades 2025-09-01 – 2026-03-31 finns bara i bulkuppladdningen, med belägg
  2026-04-02. Med den bokstavliga regeln blir referenstavlan för m − L i glappet alltid tavlan 2025-08-29. Skälet i
  registret håller.
- Inget läckage. Referenstavlan är alltid känd vid versionens datum d, och d ≤ `known_from`. Den oberoende omräkningen
  ger samma referens och referenstavla i alla 61 versioner.
- Den bokstavliga regeln ändrar bara L = 6 i 2026-05 – 2026-09 (3,375 → 1,125, 10 → 0,2375 och 8 → 0,2375) och inget i
  L = 12. Det stämmer med dokumentet.
- Följd av valet: i glappet är referenstavlan en censurerad bulktavla. Av de 15 högst rankade i tavlan före
  bulkperioden (2025-08-04, bulktavlorna börjar 2025-08-07) och efter den (2026-04-02) saknas fem namn i alla
  bulktavlor. Alla ligger under bulktavlornas etta. Det är bara ett indicium: en etta som bara fanns under glappet
  och sedan togs bort går inte att se.

### Tröskeln läses i b(m) – OK

- När r(m) finns i b(m) är tröskeln dess rating i b(m), och värdet är lägsta pris bland nycklar med rating ≥ tröskeln
  i b(m). Verifierat i alla versioner.
- Namnregel 3 (normaliserad form) används bara i tavlan 2026-10-28: `gemini-2.5-pro` → "Gemini 2.5 Pro" och
  `claude-opus-4-6` → "Claude Opus 4.6". Båda är samma post. Ratingen löper vidare över bytet (1 457,73 den 2026-10-15
  → 1 457,74 den 2026-10-20, och 1 497,99 den 2026-10-13 → 1 497,55 den 2026-10-15). Ingen träff var tvetydig, och
  ingen var falsk.
- `claude-opus-4-6-thinking` → `claude-opus-4-6-high` behandlas inte som namnbyte, och efterföljarregeln tar det.
  `claude-opus-4-6` + Δ 5,46 ger 1 501,71 i tavlan 2026-10-28, mot 1 501,72 för "Claude Opus 4.6 (High)". Felet är
  0,01 poäng.

### Två namnbyten utan överlapp saknas – R22-2 (should_fix)

- `chatgpt-4o-latest` finns i tavlorna 2024-08-22 – 2024-09-04 (sist 1 315,62). Nästa tavla, 2024-09-15, har
  `chatgpt-4o-latest-20240808` (1 315,98) som nytt namn. Det finns inget överlapp, och ratingen löper vidare. Det är
  troligen samma post med nytt namn. Det gick inte att bekräfta i Arenas egen dokumentation (arena.ai nekas).
- `claude-opus-4-6-thinking` (sist 2026-08-11, 1 502,79) → `claude-opus-4-6-high` (från 2026-08-12, 1 502,80) har samma
  mönster.
- Avsnitt 1 i källdokumentet räknar `chatgpt-4o-latest` bland experimentnamn som togs bort när modellen släpptes. Det
  stämmer inte.
- Effekt: med båda som namnbyten hittas referensen för L = 12 2025-08 direkt i tavlan 2025-08-04 (1 334,72, mot 1 331,40
  med efterföljaren). Versionen 2025-09-03 (0,13125) försvinner, och månaden blir 0,175. Övriga 60 versioner ändras
  inte. Regeln följer registret, som bara tar namnbyten som är dokumenterade i `arena_map`. Felet är att listan inte
  är komplett och att dokumentet beskriver fallet fel.

### Efterföljarregeln med gamla Δ – R22-3 och R22-5 (should_fix)

Efterföljarregeln jämför ratingar mellan tavlor. Δ mäts i de tre senaste tavlorna som har både r och s och läggs på
s:s rating i b(m). Experimentnamnen försvinner ur tavlorna efter 2025-08-04, och bulktavlorna saknar dem. Därför blir
Δ gamla. För L = 12 är den senaste Δ-tavlan 99 – 359 dagar äldre än b(m) i 10 av 15 versioner med efterföljare.

Prövning 1: i varje sådan version räknades tröskeln med varje giltig kandidat (rang 2 – 11, finns i b(m), minst 3
gemensamma tavlor). Regeln tar den första i rangordning. Spridningen mellan kandidaterna visar hur osäker
efterföljaren är.

| L | Månad, version | Efterföljare | Δ-tavlans ålder (dagar) | Kandidater | Spridning (poäng) | Värden med olika kandidater |
|---|---|---|---|---|---|---|
| 12 | 2025-08, 2025-09-03 | `grok-2-2024-08-13` | 359 | 6 | 6,55 | 0,13125; 0,1375; 0,175 |
| 12 | 2025-10 | `o1-preview` | 25 | 7 | 0,09 | 0,175 |
| 12 | 2025-11, 2026-04-02 | `o1-preview` | 114 | 4 | 0,65 | 0,175 |
| 12 | 2025-12, 2026-04-02 | `o1-2024-12-17` | 148 | 3 | 0,64 | 0,275 |
| 12 | 2026-01, 2026-04-02 | `deepseek-r1` | 178 | 3 | 0,52 | 0,275 |
| 12 | 2026-02, 2026-04-02 | `deepseek-r1` | 206 | 2 | 8,23 | 0,275; 0,315 |
| 12 | 2026-03, 2026-04-02 | `chatgpt-4o-latest-20250326` | 313 | 4 | 19,39 | 1,0; 1,125 |
| 12 | 2026-04 | `o3-2025-04-16` | 342 | 4 | 25,15 | 1,0; 1,125 |
| 12 | 2026-05 | `o3-2025-04-16` | 296 | 4 | 21,20 | 0,75; 1,125 |
| 6 | 2025-02 till 2026-10 (7 versioner) | olika | 25 – 176 | 2 – 9 | 1,02 – 16,01 | ett värde i varje version |

Tabellen visar senaste versionen per månad för L = 12. I 5 av 22 månader (2025-08, 2026-02, 2026-03, 2026-04 och
2026-05) beror värdet på vilken kandidat som råkar stå först. I 2026-04 ger `o3-2025-04-16` tröskeln 1 433,80, medan
de tre andra kandidaterna ger 1 456,3 – 1 459,0. L = 6 påverkas inte av valet av kandidat i någon version.

Prövning 2: hur mycket ändras skillnaden mellan två närliggande modeller (inom 40 poäng, bland de 25 högsta) mellan
månadens tavla och en tavla 3 – 12 månader senare?

| Horisont | Median (poäng) | 90:e percentilen | Över ett skalbyte (2025-05-16 eller 2025-07-23): median, 90:e percentilen |
|---|---|---|---|
| 3 månader | 2,31 | 8,71 | 2,78; 10,98 |
| 6 månader | 3,32 | 11,41 | 1,71; 13,12 |
| 12 månader | 3,82 | 12,09 | 2,87; 10,00 |

Felet växer med tiden. Skalbytena gör det inte systematiskt större i det här måttet. Att flytta tröskeln ±5 poäng
ändrar värdet i 11 av 28 versioner för L = 12 (10 av 15 med efterföljare) och i 8 av 33 för L = 6.

Förbehåll 5 i källdokumentet säger att felet "troligen [är] några poäng, men det är inte mätt" (R22-5). Det är nu mätt.
Felet är ofta några poäng, men upp till 25 poäng med Δ som är nästan ett år gamla. Tabellen visar inte heller Δ:s ålder
(R22-3).

## 3. Priser, kanal och blandning – OK

- Pris: `arena_price.live_prices` tar den senaste LiteLLM-ögonblicksbilden ≤ månadsslut, med `PRICE_CORRECTIONS` (bara
  från det senare av ändringsdatum och publiceringsdatum) och utan nycklar som samma fil listar som pensionerade
  senast vid månadsslut. `known_from` ≥ månadsslut + 1. Handkontrollerna läser JSON-filen direkt ur LiteLLM-repot och
  får samma pris.
- Kanal: Arena-varianterna kopplar via `arena_map.pairs_at(månadsslut)`, som bara har förstapartsnycklar
  (`model_map.FIRST_PARTY`). ECI-varianten slår ihop med `model_map.key_models()` på nyckel och leverantör. Billigare
  tredjepartsvärdar ingår inte, vilket står i förbehåll 3.
- Blandning: (3 × in + ut) / 4, med utpris = max(output, reasoning output) som i `litellm_prices`. Samma som G2A och
  I6. Bästa variant per nyckel som i G2A.
- Utan Mistral Small 3.2 ändras inget värde i någon av de tre Arena-serierna. Verifierat.
- Priskontroll: i senaste versionen per månad är `price_check` 8 `developer_page`, 1 `blocked` och 13 `unchecked` för
  L = 12, och 2, 5 och 21 för L = 6. Det stämmer med dokumentet. Nya nycklar vid minimum är inte kontrollerade mot
  utvecklarnas prislistor. Granskningen kontrollerade inte heller dem (N-3).
- ECI-varianten använder X5:s prisregler (rättningar och pensionering), men det gör inte I6-serierna. Den som jämför
  `g2_price_rolling12_eci` med `g2_price_at_capability*` jämför alltså olika prisregler. Det står i registret (N-6).

## 4. Omräkning – OK

- **Koden:** `price_rolling.build` och `build_eci` på samma indata ger Q1:s tabell rad för rad (28 + 33 + 39 + 18 rader).
- **Oberoende omräkning** med ett eget skript efter registertexten. Skriptet delar bara prisuttaget (`live_prices`) och
  kopplingen (`pairs_at`) med koden. Tavelval, referens, namnregler, efterföljare, tröskel, minimum, datering och
  märkning är egna. Alla 100 Arena-versioner är identiska i värde, `known_from`, `source`, nyckel, tröskel, referens,
  efterföljare, b(m), referenstavla och antal kvalificerade. Utan regeln "en version per datum" i Δ blir värdena
  desamma.
- **För hand mot råfilerna:** nio Arena-versioner (andra än Q1:s nio), tre månader av frontpriset och fem ECI-månader.
  Space-filerna lästes med `arena.pickle_tables`, datasetet med pandas och LiteLLM med `git show`. Cachen var lika med
  råfilen i alla tavlor.

| Version | Tavlor | Referens och tröskel | Billigaste kvalificerade | LiteLLM | Värde |
|---|---|---|---|---|---|
| L = 12, 2025-05 | b(m) 2025-05-22 (Space), ref 2024-05-27 (Space, `full_old`) | `gpt-4o-2024-05-13` 1 281,63, i b(m) 1 281,48 | `gemini-2.0-flash-lite-preview-02-05` 1 309,14, 0,075/0,30 | `06484f6e5a` | 0,13125 ✔ |
| L = 12, 2025-10 | b(m) 2025-08-29 (Space), ref 2024-10-28 | `chatgpt-4o-latest-20240903` saknas. `o1-preview` 1 353,85 + Δ 0,97 (2025-07-28, 08-01, 08-04) = 1 354,83 | `gemini-2.0-flash-001` 1 358,15, 0,10/0,40 | `0d84c11bbe` | 0,175 ✔ |
| L = 12, 2026-02, bulkversionen | b(m) 2026-02-26 (bulk), ref 2025-02-27 (Space) | `early-grok-3` saknas. `deepseek-r1` 1 372,92 + Δ 39,24 = 1 412,17 | `deepseek-v3.2` (`deepseek-chat`) 1 419,95, 0,28/0,42 | `7d084dfb9d` | 0,315 ✔ |
| L = 12, 2026-05 | b(m) 2026-05-27 (dataset), ref 2025-05-22 (Space) | `gemini-2.5-pro-preview-05-06` saknas. `o3-2025-04-16` 1 409,38 + Δ 17,33 = 1 426,71 | `mistral-large-3` (`mistral/mistral-large-2512`) 1 430,10, 0,50/1,50 | `a021a5be86` | 0,75 ✔ |
| L = 12, 2026-08 | b(m) 2026-08-27 (dataset), ref 2025-08-29 (Space) | `gemini-2.5-pro` 1 466,24, i b(m) 1 457,75 | `glm-5.3-flash` 1 465,81, 0,15/0,50 | `10631eb834` | 0,2375 ✔ |
| L = 6, 2025-05 | b(m) 2025-05-22, ref 2024-11-22 (Space) | `gemini-exp-1121` 1 365,31, i b(m) 1 361,43 | `deepseek-v3-0324` (`deepseek/deepseek-chat`) 1 367,80, 0,27/1,10 | `06484f6e5a` | 0,4775 ✔ |
| L = 6, 2026-06 | b(m) 2026-06-25 (dataset), ref 2025-12-30 (bulk) | `gemini-3-pro` 1 484,44, i b(m) 1 479,46 | `gemini-3.5-flash` 1 479,90, 1,50/9,00 | `88e03e5487` | 3,375 ✔ |
| L = 6, 2026-08 | b(m) 2026-08-27, ref 2026-02-26 (bulk) | `claude-opus-4-6` 1 501,55, i b(m) 1 497,48 | `claude-opus-4-6`, 5/25 | `10631eb834` | 10 ✔ |
| L = 6, 2026-09 | b(m) 2026-09-25, ref 2026-03-31 (bulk) | `claude-opus-4-6-thinking` saknas. `claude-opus-4-6` 1 497,79 + Δ 5,46 (2026-08-06, 08-10, 08-11) = 1 503,25 | `claude-opus-5.5-high` (`claude-opus-5-5`) 1 517,79, 4/20 | `025292e75b` | 8 ✔ |
| Frontpris, 2025-01 | b(m) 2025-01-28 (Space) | Ettan `gemini-2.0-flash-thinking-exp-01-21` 1 382,00 är inte kopplad. Bästa prissatta: `deepseek-r1` 1 357,65 | `deepseek/deepseek-reasoner`, 0,55/2,19 | `9f0f2b3f01` | 0,96 ✔ |
| Frontpris, 2025-03 | b(m) 2025-03-30 (Space) | Ettan `gemini-2.5-pro-exp-03-25` 1 440,12 har inget pris. Bästa prissatta: `gpt-4.5-preview-2025-02-27` 1 397,82 | 75/150 | `dfb838eaff` | 93,75 ✔ |
| Frontpris, 2026-10 | b(m) 2026-10-28 (dataset) | Ettan "Gemini 4 Carbon (High)" 1 540,04 har inget pris. Bästa prissatta: "Gemini 4 Argon (High)" 1 528,58 | `gemini/gemini-4-argon`, 2/10 | `b2647116ca` | 4 ✔ |
| ECI, 2025-05 | – | GPT-4o (May 2024), 128,13 | Gemini 2.0 Flash, 134,02, 0,10/0,40 | `06484f6e5a` | 0,175 ✔ |
| ECI, 2025-08 | – | Claude 3.5 Sonnet, 130,00 | GPT-5 nano, 139,07, 0,05/0,40 | `fa4c833e58` | 0,1375 ✔ |
| ECI, 2025-12 | – | o1, 141,16 | Grok 4 Fast, 144,32, 0,20/0,50 | `861b103dc0` | 0,275 ✔ |
| ECI, 2026-06 | – | o3-pro, 147,47 | MiniMax-M3, 147,84, 0,30/1,20 | `88e03e5487` | 0,525 ✔ |
| ECI, 2026-09 | – | GPT-5, 150,00 | GPT-6 Luna, 156,45, 0,10/0,50 | `025292e75b` | 0,20 ✔ |

ECI-tabellen i cachen är lika med `eci_scores.csv` i ZIP-filen (258 modeller, kolumnen `Display name`).

## 5. Datering och versioner – OK för serierna, kantfall R22-1 (should_fix)

- `known_from` = det senare av d och månadsslut + 1 i alla rader. Versionerna 2025-09-03 (Space-filen 2025-08-29) och
  2026-04-02 (bulkuppladdningen) uppstår där registret säger.
- Ingen tavla publicerad efter månadsslut och inget pris efter månadsslut används (Q1:s tester, och den oberoende
  omräkningen).
- En referenstavla som beläggs efter månadsslut ger en ny version på sitt beläggsdatum och används aldrig före det
  (nytt test).
- **R22-1.** Två tavlor publicerades på månadens sista dag och belades dagen efter: 2026-04-30 (belägg 2026-05-01) och
  2026-09-30 (belägg 2026-10-01). `_versions` slår ihop beläggsdagen med månadsslut + 1 och använder då bara tavlor
  belagda senast vid månadsslut. Tavlan används alltså aldrig för sin månad. Registret (och `vintages.py`) säger att en
  sådan tavla ger en ny version på beläggsdagen om värdet ändras. Prövat: med tavlan ändras inget värde i 2026-04 eller
  2026-09 i någon av de tre Arena-serierna. Det är därför should_fix och inte must_fix. Samma kod finns i
  `vintages.monthly` och `arena_price.build`, så rättningen hör hemma i den delade regeln.

## 6. Mättnad – OK för Arena, R22-4 för ECI (should_fix)

Golvet är det lägsta priset bland alla kopplade och prissatta nycklar i samma tavla, utan tröskel (för ECI: bland
kopplade nycklar med känd ECI).

- **L = 12:** värdet är lika med golvet i 8 av 28 versioner, alla 2025-01 – 2025-08 (0,13125). Från 2025-09 ligger det
  över golvet. **L = 6:** 1 av 33 (2024-10). Det stämmer med avsnitt 7 i källdokumentet.
- **ECI-varianten:** värdet är lika med golvet i 7 av 18 månader, 2025-05 – 2025-11 (Gemini 2.0 Flash 0,175, sedan
  GPT-5 nano 0,1375). Från 2025-12 ligger det över. Marginalen till tröskeln är 0,34 ECI-poäng i 2026-03 och 0,37 i
  2026-06. Avsnitt 7 tar bara upp Arena-varianterna (R22-4).
- Tunna marginaler i Arena: under 5 poäng i 15 av 61 versioner och under 1 poäng i 7. Det stämmer med dokumentet (N-4).

## 7. Licens – OK

- Arena-varianterna och frontpriset har klassen `okänd` genom nyckel-overriden i Q1-blocket (samma skäl som R10-2:
  Space-filerna har ingen dokumenterad licens). Licenstexten nämner Space-filerna, vilket G2A:s text inte gör.
- ECI-varianten är `ja` genom `derived-licence`: LiteLLM (MIT, utanför `litellm/enterprise/`, läst i repots `LICENSE`)
  och Epoch (CC BY 4.0, läst i ZIP-filens README). Den läser inga Arena-data.
- `publish=True` och klassen är oberoende (`docs/datakallor/licensniva.md`), och G2A har samma kombination.
  `catalog.validate` ger inga fel.

## 8. `backfill` nedströms – not

- Registret: `backfill` när b(m) eller referenstavlan bara finns i bulkuppladdningen. Så är det byggt. L = 12 har 7
  sådana rader, varav 2 daterade månadsslut + 1 (2026-09 och 2026-10). L = 6 har 10, varav 6 (2026-04 – 2026-09).
  Frontpriset har 5, alla daterade 2026-04-02.
- Webben: `site_bundle.export._row_sources` ger `backfill_last_known` 2026-11-01 för L = 12 och 2026-10-01 för L = 6.
  Sidans text blir då att historiken fram till dess är bakåtfylld med dagens version, fast 21 av 28 rader i L = 12 är
  `release`. Gränsen flyttas varje månad till 2027-04-01 för L = 12, eftersom referensmånaden ligger i glappet till
  2026-03. Datakontraktet (5.6) antar att `backfill` betyder regeldaterad med dagens version. Q1:s rader är
  dokumentdaterade.
- `observations.new_rows` behandlar `backfill` i en release-ram som regeldaterat. Det är konservativt: datumet kan bli
  senare, aldrig tidigare.
- Serierna är katalogserier, så `BACKFILL_GATED` gäller inte. Om L = 12 blir kärnserie och spärras räknas 2026-09 –
  2027-03 inte.
- Förslag: en ny registerpost som gör `backfill` = "b(m) bara i bulkuppladdningen" (som G2A) och lägger referenstavlans
  ursprung i en diagnostikkolumn. Inget värde ändras. Alternativet är att webbspåret formulerar texten per rad.

## 9. Kostnad per uppgift – BLOCKED bekräftat

- Arenas `agent`-parquet (HEAD `62968a5`) har 54 tavlor 2026-06-04 – 2026-11-22. `cost_per_task_p50` är tom till och
  med 2026-10-28 och ifylld i de 9 tavlorna från 2026-11-02. Det finns ingen hel månad.
- `arena.ai` nekas av proxyn (403), och `lmarena.ai` skickar dit. Metoden går inte att läsa.
- Epoch: 16 av 67 `*_external.csv` har kostnads- eller tokenkolumner. De flesta har bara modellens release-datum. Aider
  har "Date of evaluation", och TheAgentCompany har en kolumn "Date" som R22 inte har tolkat. Dokumentets "inget
  körningsdatum (bara modellens release, och för Aider ett utvärderingsdatum)" missar den kolumnen. Det påverkar inget
  byggt (N-5).
- METR:s YAML har inga token- eller kostnadsfält. Verifierat.

## 10. Kärnserie?

Q1 föreslår `g2_price_rolling12_arena` som kärnserie i stället för G2A:s A och B. Granskningen stöder inte det i
nuvarande form. Värdet beror på kandidatordningen i 5 av 22 månader (punkt 2), och L = 12 vilar på efterföljare i 9 av
22 månader. L = 6 är robust mot valet av kandidat men känslig för referensregeln (literal mot känd vid d i 2026-05 –
2026-09). Pröva kärnserie först efter R22-2 och R22-3, med en ny registerpost. Grenindex och tillstånd ändras inte i
dag, och ögonblicksbilden 2026-11-30 påverkas inte.

## Noter

- **N-1** Avvikelsen från beställningen (referensen enligt det som är känt vid d) bör bekräftas av ägaren. Skälet håller
  och den läcker inte (punkt 2).
- **N-2** `backfill`-märkningen nedströms (punkt 8).
- **N-3** De flesta nycklar vid minimum är `unchecked` mot utvecklarens prislista. Kontrollen behövs före kärnserie.
- **N-4** Tunna marginaler och Arenas osäkerhetsintervall används inte. Att flytta tröskeln ±5 poäng ändrar 11 av 28
  versioner (L = 12) och 8 av 33 (L = 6).
- **N-5** Epochs TheAgentCompany-fil har en kolumn "Date" (punkt 9).
- **N-6** ECI-varianten och I6 har olika prisregler (punkt 3).
- **N-7** Frontpriset tar den bästa prissatta modellen. Tavlans etta saknar pris i 8 av 39 versioner (kolumnen
  `board_top`). Det är sammanhang och inget takmått, som dokumentet säger.
- **N-8** Kopplingen `arena_map` gjordes 2026-11-24 med dagens kunskap. Den granskades i R8 och ärvs. Namnen kopplas
  efter identitet (samma daterade version), inte efter utfall.

## Rättningar (för ett rättningsspår)

| # | Allvar | Var | Rättning |
|---|---|---|---|
| R22-1 | should_fix | `vintages.monthly`, `arena_price.build`, `price_rolling._versions` | En tavla som publicerats senast vid månadsslut och belagts dagen efter ska ge en version på beläggsdagen om värdet ändras. Enklast: låt versionen på månadsslut + 1 använda tavlor belagda till och med den dagen (som `as_of` läser datum). Delad regel, så ett eget spår och en registeranteckning. Strikt xfail: `test_month_end_board_documented_next_day_gives_a_version` |
| R22-2 | should_fix | `price_rolling.RENAMES`, källdokumentet avsnitt 1 | Lägg till `chatgpt-4o-latest` → `chatgpt-4o-latest-20240808` och `claude-opus-4-6-thinking` → `claude-opus-4-6-high`, med belägget (sista och första datum, ratingen över bytet), i en ny daterad registerpost som säger att värdena var kända (L = 12 2025-08 blir 0,175). `arena_map.py` är skyddad i körning 14, så belägget skrivs i `price_rolling.py` och dokumentet. Rätta beskrivningen av `chatgpt-4o-latest`. Strikt xfail: `test_observed_no_overlap_renames_are_found` |
| R22-3 | should_fix | `price_rolling.threshold` och `build` | Visa Δ:s ålder: kolumnen `delta_from` (datum för den äldsta av de tre Δ-tavlorna). Registrera sedan en regel för gamla Δ, till exempel att tröskeln blir medianen över alla giltiga kandidater när den senaste Δ-tavlan är äldre än 90 dagar, eller en lucka. Det är en regeländring efter att värdena setts, så registerposten ska säga det och hänvisa till R22:s tal. Strikt xfail: `test_successor_offset_age_is_visible` |
| R22-4 | should_fix | källdokumentet avsnitt 7 | Lägg till nivåkontrollen för ECI-varianten: lika med golvet i 7 av 18 månader (2025-05 – 2025-11), och marginalerna 0,34 och 0,37 ECI-poäng. Strikt xfail: `test_level_check_covers_the_eci_variant` |
| R22-5 | should_fix | källdokumentet förbehåll 5 | Ersätt "inte mätt" med R22:s mätning: spridning mellan kandidaterna upp till 25 poäng med Δ som är nästan ett år gamla, och värden som beror på kandidaten i 5 av 22 månader för L = 12. Strikt xfail: `test_successor_caveat_reports_the_measured_error` |

## Tester

`tests/test_r22_rorlig_troskel.py` (fixturer, inget nät):

- passerar: lika rating hos ettan avgörs av namnet; efterföljare tas bara från rang 2 – 11; en annan version av b(m)
  räknas aldrig som Δ-tavla; b(m) bara i bulk ger `backfill` (rörlig serie och frontpris); en referenstavla som
  beläggs efter månadsslut ger en daterad version och används inte före sitt belägg; ECI-varianten tar bort
  pensionerade nycklar
- strikt xfail: R22-1 – R22-5 (ett test per rättning, se tabellen)

`python -m pytest -q tests/test_r22_rorlig_troskel.py tests/test_price_rolling.py`: 26 passerade, 5 xfail.

Rättat i auto14k/x19-rorlig-troskel
