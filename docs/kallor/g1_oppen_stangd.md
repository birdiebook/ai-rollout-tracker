# Öppna mot stängda modeller och Kinas gap (G1), spår Q2

Körning 14, spår Q2, 2026-11-25. Förslag 6 i `docs/riktning.md`, andra punkten. Frågan är om förmåga vid fronten
blir en handelsvara (öppna vikter kommer ikapp snabbt) eller förblir en vallgrav, och samma fråga för kinesiska labb
mot övriga. Åtta katalogserier i G1. De ingår inte i grenens index och ändrar inga tillståndsregler.

Regler: `docs/mattregister.md`, "2026-11-25 – Q2: gapet mellan öppna och stängda modeller och Kinas gap". Kod:
`src/ai_tracker/sources/arena_meta.py` (Arenas metadata, namnklasser, klassning),
`src/ai_tracker/sources/model_origin.py` (kurerade tabeller med referens per rad), `src/ai_tracker/series/open_gap.py`
(beräkning och katalog). Tester: `tests/test_q2_open_gap.py` (syntetiska tavlor och ECI-tabeller, inget nät).

## 1. Ordning (förregistrering)

| Commit | Innehåll |
|---|---|
| `13d6d9b` | Registerposten: definitioner, klassningsordning, namnbyten, censurering och datering. Inga värden |
| `bc39cc5` | Kod och tester. Kurerade tabeller byggda ur metadata. Inga värden |
| senare | Serierna räknade på riktiga data, handkontroller, det här dokumentet och en daterad rättelse av en faktauppgift i registerposten (vilka modeller som byter licensfält). Reglerna ändrades inte |

**Det här lästes före registerposten** (metadata och täckning, inga värden i serierna): fältnamnen i Arena-datasetets
kort, värdelistorna för `license` och `organization` i `text`/`overall`, vilka modeller som byter `license` över tid,
rubrikerna i Spacens `leaderboard_table_*.csv`, hur många (tavla, namn)-par varje klassningssteg täcker, vilka namn
som försvinner och dyker upp mellan på varandra följande tavlor, hur många namn reglerna för bytet 2026-10-20 matchar,
kolumnerna i Epochs `eci_scores.csv` och fördelningen av `Model accessibility`, `Accessibility group` och
`Country (of organization)`. Inga ratingar eller ECI-värden per klass, ingen topp per klass och inga eftersläpningar.
Git visar bara att inga värden committades före registerposten. Inget räknades lokalt heller.

## 2. Definitioner

Två grupper per mått: den följande gruppen F (öppna vikter, respektive kinesiska labb) och den ledande gruppen L
(stängda vikter, respektive alla andra klassade labb).

- **Arena, inom en tavla.** b(m) är den tavla (`text`, `overall`) som gäller vid månadsslut. F(m) och L(m) är gruppernas
  högsta rating i b(m). Den ledande fronten i en tidigare månad s är L-gruppens toppmodell i b(s), och dess rating läses
  i b(m). s* är den första månaden där den ratingen är ≥ F(m). Eftersläpningen är m − s* i hela månader. Ratingar
  jämförs aldrig mellan tavlor.
- **ECI, en skala över tiden.** F(t) och L(t) är gruppernas bästa ECI bland modeller med `date` ≤ månadsslut.
  Eftersläpningen är t − min{s: L(s) ≥ F(t)} i hela månader.
- **Golvet 0:** när F leder (F > L) är eftersläpningen 0. Den är också 0 när F ligger efter men över förra månadens
  ledande front. Gapet skiljer fallen åt: det är negativt bara när F leder.
- **Censurering:** när fronten redan nåddes den första månaden med data (s* = s0) är den sanna eftersläpningen okänd och
  minst m − s0. Månaden får då inget värde.
- **Gap** = L − F, positivt när den ledande gruppen ligger före. I Arena är gapet bara sammanhang, eftersom skalan
  ändras mellan tavlor (Elo till BT 2024-01-09, stilkontroll 2025-05-16, omviktning 2025-07-23).

## 3. Klassning och täckning

### Arena

Klassningen läses per namn och tavla, i registrets ordning. Täckning över alla 270 tavlor i `text` (2023-05-08 –
2026-11-22), data 2026-11-25:

| Steg | Vikter: par | namn | Land: par | namn |
|---|---|---|---|---|
| 1. Tavlans egen rad i datasetet | 61 498 | 859 | 57 201 | 805 |
| 2. Arenas senaste uppgift ≤ tavlans datum (dataset eller Space-tabell) | 4 311 | 293 | 7 789 | 341 |
| 3. Arenas senare uppgift (vikter bara om stängd) | 60 | 14 | 77 | 16 |
| 4. Kurerad tabell (`ARENA_MODELS`) | 14 | 4 | 72 | 5 |
| Organisation utan dokumenterat land | – | – | 770 | 6 |
| Utanför | 30 | 2 | 4 | 1 |

- **Vikter:** `license` = "Proprietary" är stängd, varje annat ifyllt värde är öppna vikter. Det omfattar även
  icke-kommersiella licenser (CC-BY-NC, "Non-commercial", MRL). Arena byter etikett när vikterna släpps: fyra modeller
  går från "Proprietary" till en öppen licens (`minimax-m2.7` från tavlan 2026-04-14, `minimax-m3` från 2026-07-02,
  Mistral Large 4 från 2026-11-06 och Inkling 2 Small från 2026-11-11). Eftersom etiketten läses i varje tavla räknas en
  modell som öppen först från släppet.
- **Utanför (vikter):** `gpt-5-old` (anonymt testnamn, 4 tavlor 2025-08) och `llama-4-maverick-03-26-experimental`
  (en anpassad chattvariant vars vikter aldrig släpptes, 26 tavlor 2025-04 – 2025-08). Arenas Space-tabell har inget
  licensfält för den.
- **Land:** Arenas organisationsnamn (97 varianter) mappas till land i `ORG_COUNTRY`. Referensen är Epochs fält
  `Country (of organization)` för samma organisation i `all_ai_models.csv`, i några fall med en förklaring (Arenas
  `thinky` listar Inkling 2 Small, som Epoch har under Thinking Machines). Utan dokumenterat land: Cognitive
  Computations, Nomic AI och OpenAssistant (Dolphin, GPT4All och OpenAssistant Pythia, små öppna modeller). Kinesisk =
  landet är Kina. "Multinational" (RWKV) räknas som icke-kinesisk.

### Epoch ECI

258 modeller i `eci_scores.csv` (2026-11-25).

| Steg | Vikter | Land |
|---|---|---|
| `eci_scores.csv` (`Accessibility group`, `Country (of organization)`) | 237 | 242 |
| `all_ai_models.csv`, samma `Model` | 1 | 1 |
| Kurerad tabell (`ECI_MODELS`) | 16 | 14 |
| Utanför | 4 | 1 |

- **Utanför (vikter):** Qwen 3.6 Max (Preview), Qwen 3.6 Flash, Qwen 3.5 Plus (hosted 397B-A17B) och Qwen 3.5 Flash
  (hosted 35B-A3B). Det är Alibabas värdade API-modeller, och om vikterna är de publicerade är inte dokumenterat. De
  räknas i Kina-måttet (landet finns), men inte i måttet för öppna mot stängda.
- **Kurerade rader:** PaLM 2 (tre storlekar, stängd, Google) och tretton små öppna modeller (Qwen-Coder, Yi-9B,
  InternLM, ChatGLM2, Vicuna med flera). Referensen är modellens Hugging Face-sida, kontrollerad 2026-11-25 (repot finns,
  skapat nära Epochs datum). Labbens egna sidor (blog.google, databricks.com, alibabacloud.com, platform.openai.com) nekas
  av proxyn och är inte lästa. Det står vid varje rad.
- Epoch räknar API, värdad åtkomst och osläppta modeller som stängda (`Closed weights`). Det följs.

## 4. Namnbyten (Arena)

Samma modell har ofta flera namn. En namnklass knyter ihop dem, och en modells rating i b(m) läses under vilket namn i
klassen som helst.

- **Arenas egna byten före 2026-10-20:** 27 kurerade par i `ARENA_RENAMES`, med tavlorna som belägg (till exempel
  `gpt-4` → `gpt-4-0314` 2023-12-06, `gpt-4-turbo` → `gpt-4-1106-preview` 2024-02-02, `claude-opus-4-6-thinking` →
  `claude-opus-4-6-high` 2026-08-12, där röstantalet följer med: 72 425 → 72 466). Inte kopplade: delningar (ett namn
  blir två), förhandsversion till GA (olika kontrollpunkter) och borttagna modeller.
- **De första visningsnamnen kom en tavla tidigt**, 2026-10-15 (Claude, Gemini, Kimi och Muse). 20 par med samma
  normaliserade namn, organisation och licens, granskade för hand.
- **Bytet 2026-10-15 → 2026-10-20** (416 och 417 namn): 26 samma namn, 346 samma normaliserade namn, 16 samma mängd ord,
  15 samma licens och röstantal, och 13 kurerade (`DISPLAY_EXTRA`, samma organisation och licens, röstantal som följer
  med). Ett namn blev över: `Beam 1.0 501B A23B`, som var ny den dagen.

## 5. Serier

| Nyckel | Månader med värde | Rader | `source` | Första `known_from` |
|---|---|---|---|---|
| `g1_open_lag_months_arena` | 2024-04 – 2026-10 | 38 | 25 release, 13 backfill | 2024-05-01 |
| `g1_open_gap_arena` | 2023-05 – 2026-10 | 51 | 44 release, 7 backfill | 2023-06-01 |
| `g1_china_lag_months_arena` | 2024-05 – 2026-10 | 38 | 24 release, 14 backfill | 2024-06-01 |
| `g1_china_gap_arena` | 2023-05 – 2026-10 | 51 | 44 release, 7 backfill | 2023-06-01 |
| `g1_open_lag_months_eci` | 2024-06 – 2026-10 | 29 | backfill | 2024-07-07 (nominellt) |
| `g1_open_gap_eci` | 2023-03 – 2026-10 | 44 | backfill | 2023-04-07 (nominellt) |
| `g1_china_lag_months_eci` | 2023-09 – 2026-10 | 38 | backfill | 2023-10-07 (nominellt) |
| `g1_china_gap_eci` | 2023-06 – 2026-10 | 41 | backfill | 2023-07-07 (nominellt) |

- Månaderna före de första värdena i eftersläpningen är censurerade: den ledande fronten i den första månaden (GPT-4 i
  maj 2023 i Arena, GPT-4 i mars 2023 i ECI) låg redan över den följande gruppens topp.
- **Arena-raderna** är versioner enligt `sources/vintages.py`: första versionen har `known_from` = månadsslut + 1 dag,
  och en tavla som beläggs senare ger en ny rad den dagen om värdet ändras. Månaderna 2025-09 – 2026-03 har två
  versioner: först tavlan 2025-08-29, sedan bulkuppladdningen 2026-04-02 (`backfill`). Eftersläpningen har `backfill`
  när b(m) eller b(s*) bara finns i bulkuppladdningen. Därför är eftersläpningen `backfill` från 2026-04 trots att
  tavlorna då är ärligt daterade: s* ligger i 2025-11 – 2026-02.
- **ECI-raderna** är återfyllda (`backfill`, `known_from` = månadsslut + 7 dagar, nominellt). Ärligt daterade värden
  kommer först med våra egna veckohämtningar.
- Hämta med `python -m ai_tracker.observations g1_open_lag_months_arena g1_open_gap_arena g1_china_lag_months_arena
  g1_china_gap_arena g1_open_lag_months_eci g1_open_gap_eci g1_china_lag_months_eci g1_china_gap_eci` (cirka 75 s med
  cachade Arena-filer). Datatesterna i `warehouse.py` passerar (2026-11-25).
- **Licens och klass:** Arena-serierna läser Space-filerna (tavlor och `leaderboard_table_*.csv`), så klassen för
  kommersiell användning är `okänd`, som för `g1_arena_*`. ECI-serierna är CC BY 4.0, klass `ja`. Alla publiceras
  (`publish=True`) med källhänvisning till LMArena respektive Epoch AI.

## 6. Handkontroller

Kontrollerade mot rådata med ett eget skript, oberoende av `open_gap.py`: Arena-datasetets parquet (fälten `license`,
`organization`, `rating`), Space-tabellerna läst med `arena.pickle_tables`, och Epochs `eci_scores.csv` direkt ur zip-filen.
Värdena är den senaste versionen 2026-11-25.

| Månad | Mått | Tavla eller fil | F (följande) | L (ledande) | Ledande front som först når F | Värde |
|---|---|---|---|---|---|---|
| 2024-04 | Arena, öppna | Space 2024-04-26 (`full`) | `llama-3-70b-instruct` 1 207,50 | `gpt-4-turbo-2024-04-09` 1 257,40 | 2023-10: `gpt-4` = `gpt-4-0314` 1 188,99 (når inte). 2023-11: `gpt-4-turbo` = `gpt-4-1106-preview` 1 253,03 | 5 mån, gap 49,9 |
| 2024-10 | Arena, öppna | Space 2024-10-28 | `llama-3.1-nemotron-70b-instruct` 1 270,74 | `chatgpt-4o-latest-20240903` 1 340,16 | 2024-04: `gpt-4-turbo-2024-04-09` 1 256,44 (når inte). 2024-05: `gpt-4o-2024-05-13` 1 284,78 | 5 mån, gap 69,4 |
| 2024-10 | Arena, Kina | Space 2024-10-28 | `yi-lightning` (01 AI) 1 285,17 | som ovan | 2024-07: `gpt-4o-2024-05-13` 1 284,78 (når inte, 0,39 poäng under). 2024-08: `chatgpt-4o-latest` = `-20240808` 1 316,13 | 2 mån, gap 55,0 |
| 2025-01 | Arena, öppna | Space 2025-01-28 | `deepseek-r1` (MIT) 1 357,65 | `gemini-2.0-flash-thinking-exp-01-21` 1 382,00 | 2024-10: `chatgpt-4o-latest-20240903` 1 339,59 (når inte). 2024-11: `gemini-exp-1121` 1 365,01 | 2 mån, gap 24,3 |
| 2026-05 | Arena, öppna | dataset 2026-05-27 | `glm-5.1` (MIT, zai) 1 469,27 | `claude-opus-4-6-thinking` 1 499,32 | 2025-10: `gemini-2.5-pro` 1 457,38 (når inte). 2025-11: `gemini-3-pro` 1 479,57 | 6 mån, gap 30,0 |
| 2026-10 | Arena, öppna | dataset 2026-10-28 (visningsnamn) | `MiMo-V2.6-Pro` (MIT, xiaomi) 1 491,35 | `Gemini 4 Carbon (High)` 1 540,04 | 2026-01: `gemini-3-pro` = "Gemini 3 Pro" 1 479,40 (når inte). 2026-02: `claude-opus-4-6` = "Claude Opus 4.6" 1 496,25 | 8 mån, gap 48,7 |
| 2023-09 | ECI, Kina | `eci_scores.csv` | Qwen-14B 101,76 | GPT-4 (Mar 2023) 121,61 | GPT-4 (Mar 2023), 2023-03-14 | 6 mån, gap 19,9 |
| 2024-12 | ECI, öppna | `eci_scores.csv` | DeepSeek-V3 131,69 | o1 141,16 | o1-mini, 2024-09-12 (Claude 3.5 Sonnet 130,00 når inte) | 3 mån, gap 9,5 |
| 2025-07 | ECI, Kina | `eci_scores.csv` | Qwen3-235B-A22B-Thinking (Jul 2025) 143,23 | o3-pro 147,47 | Gemini 2.5 Pro (Mar 2025), 2025-03-31 | 4 mån, gap 4,2 |
| 2026-10 | ECI, öppna | `eci_scores.csv` | Kimi K3.1 Pro 161,20 | GPT-6 Astra 169,21 | GPT-5.5 Pro, 2026-04-23 (GPT-5.4 Pro 160,31 når inte) | 6 mån, gap 8,0 |

Alla tio stämmer med serierna. Tavlan per månad stämmer med regeln (senast publicerade tavla som var belagd vid
månadsslut). I 2024-10 täcker datasetet inte `chatgpt-4o-latest-20240903` (censurerad bulk), och klassningen kommer
från Space-tabellen (steg 2, "Proprietary").

## 7. Förbehåll

1. **Arena mäter chattpreferens**, inte förmåga i allmänhet. Skillnader på några poäng ligger inom Arenas
   osäkerhetsintervall, som inte används. I 2024-10 avgör 0,39 poäng om Kinas eftersläpning blir 2 eller 3 månader.
2. **Borttagna modeller.** Många tidigare toppmodeller (Geminis experimentmodeller, `early-grok-3`,
   `gemini-2.5-pro-exp-03-25`) finns inte kvar i senare tavlor. Då läses nästa stängda modell från samma månads tavla.
   Från 2025-08 gäller det 7–9 av månaderna före s*. För s* själv gäller det 2025-06 – 2025-08 och de första
   versionerna av 2025-09 – 2026-03: toppen i mars 2025, `gemini-2.5-pro-exp-03-25`, togs bort 2025-06-01 och ersätts av
   `chatgpt-4o-latest-20250326`. Den ledande fronten blir då lägre än den var, och eftersläpningen kan bli kortare än
   den verkliga. Hade februaris topp `early-grok-3` funnits kvar kunde s* ha blivit en månad tidigare.
3. **En eftersläpning i hela månader har golvet 0 och hoppar.** Den växer med en månad varje månad som den följande
   gruppens topp står still, och faller när en ny frontmodell kommer. Mätglappet 2025-09 – 2026-03 syns tydligt: med
   tavlan 2025-08-29 växer den öppna eftersläpningen 6, 7, ..., 12, och bulkuppladdningen 2026-04-02 rättar den till 4–9.
4. **ECI har färre modeller** (258) och skattas om. Klassningen är dagens. En modell vars vikter släpptes senare räknas
   som öppen från sitt `date`. ECI börjar 2023-02. För Kina-måttet ger det värden från 2023-09 med s* = 2023-03 (GPT-4),
   men icke-kinesiska modeller före 2023-02 finns inte i filen. De tidiga värdena (2023-09 – 2024-05) är därför i
   praktiken undre gränser.
5. **Få kinesiska modeller och samma modeller i båda måtten.** Från 2024-12 är den bästa öppna modellen kinesisk i båda
   källorna (DeepSeek, GLM, Qwen, Kimi, MiMo), och den bästa stängda är icke-kinesisk. Måtten för öppna och för Kina blir
   därför ofta lika. De skiljer sig bara när en stängd kinesisk modell (Qwen-Max, ERNIE, Dola-Seed) ligger högst bland
   de kinesiska, till exempel Arena 2026-03 (4 mot 9 månader). Det är en egenskap hos perioden, inte två oberoende
   signaler.
6. **Öppna vikter inkluderar icke-kommersiella licenser.** Arena och Epoch skiljer inte frontens licensvillkor åt i måttet.
7. **Arenas etiketter är källans egna och kan vara fel.** `llama-4-maverick-03-26-experimental` saknar etikett och är
   utanför. Två namn (`gpt-5.4`, `gpt-5.4-high`) har tomt licensfält i sju tavlor och får "stängd" från tidigare tavlor.
8. **Namnklasserna är kurerade** utom bytet 2026-10-20. Ett fel i en klass kan flytta s*. Nya namnbyten kopplas inte
   automatiskt. Då läses nästa modell enligt punkt 2 tills tabellen har granskats.

## 8. Förslag

Inga av serierna föreslås som kärnserier nu. En granskning bör pröva punkt 2 och 8 först, och om Arena-varianten med
stilkontroll (`text_style_control`, standardvyn från 2025-05-16) ger samma bild. ECI-serierna kan räknas först när
det finns egna ögonblicksbilder, som för `g1_epoch_eci_frontier`.
