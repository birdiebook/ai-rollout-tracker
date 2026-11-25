# Pris vid rörlig förmågetröskel (G2), spår Q1

Körning 14, spår Q1, 2026-11-25. Förslag 6 i [riktning.md](../riktning.md). Definitionerna är låsta i
[måttregistret](../mattregister.md), posten "2026-11-25 – Q1: pris vid rörlig förmågetröskel". Serierna är
katalogserier, inte kärnserier. **Inga takter, halveringstider eller trender beräknas i spåret.**

## 1. Vad som tittades på före registreringen

Registerposten committades innan något värde för de nya serierna räknades. Före posten tittade spåret bara på detta:

- **Referensmodellerna.** För varje månad m till 2026-10 och L = 6 och 12: vilken modell som var etta i tavlan för
  m − L (både enligt det som var känt vid d och enligt det som var känt vid slutet av m − L), och om den finns i b(m)
  med exakt namn. Bara namn och närvaro, inga ratingar. Fynd: ettan saknas i b(m) i 31 av versionerna. Det är nästan
  alltid ett experiment- eller förhandsnamn som tagits bort när modellen släpptes (`gpt-4-turbo`,
  `chatgpt-4o-latest`, `gemini-exp-1121`, `gemini-exp-1206`, `gemini-2.0-flash-thinking-exp-01-21`, `early-grok-3`,
  `gemini-2.5-pro-exp-03-25`, `gemini-2.5-pro-preview-05-06`), ett namnbyte (`claude-opus-4-6-thinking` finns till
  2026-08-11, `claude-opus-4-6-high` från 2026-08-12) eller bytet till visningsnamn (`gemini-2.5-pro` finns till
  2026-10-15, "Gemini 2.5 Pro" från 2026-10-20). Efterföljarregeln är alltså central och inget undantag.
- **Kandidater till efterföljare.** För varje sådan version: de tio modellerna närmast under ettan i referenstavlan,
  om de finns i b(m) och i hur många tidigare tavlor de finns tillsammans med ettan. Varje version i API-eran hade en
  kandidat som finns i b(m) med minst 3 gemensamma tavlor. Inga ratingskillnader räknades.
- **Namnformer kring bytet till visningsnamn.** Vilka namn för Claude Opus 4.6/4.7, Gemini 2.5 Pro, 3 Pro och 3.1, och
  GPT-5.4/5.5 som finns i tavlorna från 2026-07 och i vilket datumintervall. Tavlan 2026-10-15 har båda formerna.
- **ECI-fronten per månad** (den publicerade serien `g1_epoch_eci_frontier`, ur dagens ZIP). Den är tröskeln i
  ECI-varianten. Den lästes för att sätta täckningsgolvet: `model_map` täcker modeller med ECI ≥ 128, och fronten når
  128 först 2024-05. Inga priser lästes.
- **Kolumnnamn** i alla filer i Epochs `benchmark_data.zip` (sökning efter token, cost, price) och i METR:s
  `benchmark_results_1_1.yaml`, och README-filen i ZIP-filen (licensen).
- **Arenas `agent`-delmängd:** kolumnerna, antalet modeller per tavla och antalet rader med `cost_per_task_p50`
  (0 till 2026-10-28, 53 – 64 per tavla från 2026-11-02). Inga kostnadsvärden.
- LiteLLM-ögonblicksbilderna och avvecklingsdatumen laddades, men inga priser lästes ut.

## 2. Ordning i git

| Tid (UTC) | Commit | Innehåll |
|---|---|---|
| 09:12 | `b5c652c` | Registerposten och avsnitt 1 ovan. Inga värden |
| 09:16 | `6c00c48` | Kod och syntetiska tester. Inga riktiga data |
| senare | denna commit | Värden, handkontroller och känsligheter |

Begränsning: git visar bara att inga värden committades före registerposten, inte att inga räknades lokalt. Inga
värden räknades före 09:16.

## 3. Definitioner i korthet

Hela regeln står i registret. Kod: `src/ai_tracker/series/price_rolling.py`. Tester:
`tests/test_price_rolling.py` (syntetiska tavlor och priser, inget nät).

- **b(m)** är tavlan för månad m enligt G2A:s regel ([g2_arena_pris.md](g2_arena_pris.md) avsnitt 1).
- **Referensen r(m)** är ettan i tavlan för m − L, enligt det som är känt vid versionens datum d. Ettan kan vara ett
  experimentnamn. Referensen är en förmågenivå, inte ett pris.
- **Tröskeln** är r(m):s rating i b(m). Hittas r(m) inte i b(m), används nästa modell i referenstavlan som finns i b(m)
  och delar minst 3 tidigare tavlor med r(m). Tröskeln blir då dess rating plus medianen av skillnaden r − s i de 3
  senaste gemensamma tavlorna. Annars blir månaden en lucka.
- **Värdet** är det lägsta blandade förstapartspriset (3:1, LiteLLM vid månadsslut, G2A:s prisrättningar och regel om
  pensionerade modeller) bland nycklar med rating ≥ tröskeln i b(m).
- **Frontpriset** är priset för den högst rankade prissatta modellen i b(m). Det är sammanhang och inget takmått.
- **ECI-varianten** har tröskeln = högsta ECI bland modeller släppta ≤ slutet av m − 12 (dagens ECI), och värde bara när
  tröskeln är ≥ 128.

## 4. Serier

| Nyckel | Månader | Rader | `backfill`-rader | Månader där efterföljare används | Licensklass |
|---|---|---|---|---|---|
| `g2_price_rolling12_arena` (huvudvariant) | 2025-01 – 2026-10 (22) | 28 | 7 | 9 | `okänd` |
| `g2_price_rolling6_arena` | 2024-07 – 2026-10 (28) | 33 | 10 | 7 | `okänd` |
| `g2_price_frontier_arena` | 2024-01 – 2026-10 (34) | 39 | 5 | – | `okänd` |
| `g2_price_rolling12_eci` | 2025-05 – 2026-10 (18) | 18 | 18 (hela historiken) | – | `ja` |

Bygg med `python -m ai_tracker.observations g2_price_rolling12_arena g2_price_rolling6_arena g2_price_frontier_arena
g2_price_rolling12_eci` (Arena cirka 150 s kall, LiteLLM cirka 35 s, Epoch-ZIP en hämtning). Datatesterna
(`python -m ai_tracker.warehouse`) passerar: `fresh`, `unique_key`, `no_nulls`, `known_from_after_period_end`,
`fetched_known_from_not_after_fetch`, `freq_matches_catalog`, `no_gaps` och `series_in_catalog` är alla ok. Ingen
månad blev en lucka.

- **Datering:** Arena-raderna är första versioner med `known_from` = månadsslut + 1 dag, utom versioner som uppstår när
  en senare belagd tavla ändrar värdet (2025-09-03 för Space-filen 2025-08-29 och 2026-04-02 för bulkuppladdningen).
- **`backfill`** betyder här att b(m) eller referenstavlan bara finns i bulkuppladdningen (censurerad). När
  referensmånaden ligger i mätglappet är referenstavlan en sådan tavla: för L = 6 i 2026-03 – 2026-09 och för L = 12 i
  2026-09 – 2027-03. Därför är till exempel L = 6 2026-04 – 2026-09 och L = 12 2026-09 – 2026-10 märkta `backfill`, fast
  de är daterade månadsslut + 1.
- **Täckning av kopplingen:** varje namn med rating ≥ tröskeln i b(m) är granskat i `arena_map` (kopplat eller listat i
  `UNMAPPED` med skäl). `price_rolling.coverage()` ger noll ogranskade namn för båda varianterna. Tröskeln ligger
  över `gpt-4-0314`:s rating i samma tavla i alla 61 versioner, och `UNMAPPED` är gjord mot den nivån.
- **Licens:** Arena-varianterna läser samma texttavlor som G2A, med Space-filerna, och får `okänd` genom nyckel-overriden
  i `licenses.py` (Q1-blocket). ECI-varianten är LiteLLM (MIT) × Epoch (CC BY 4.0), alltså `ja`. Alla har
  `publish=True`.

### Huvudvarianten, L = 12 (alla versioner)

| Månad | Version (known_from) | Värde | Referens r(m) | Efterföljare | Modell vid minimum | Kvalificerade | source |
|---|---|---|---|---|---|---|---|
| 2025-01 | 2025-02-01 | 0,13125 | `gpt-4-turbo` | – | `gemini-1.5-flash-002` | 16 | release |
| 2025-02 | 2025-03-01 | 0,13125 | `gpt-4-1106-preview` | – | `gemini-1.5-flash-002` | 21 | release |
| 2025-03 | 2025-04-01 | 0,13125 | `claude-3-opus-20240229` | – | `gemini-1.5-flash-002` | 23 | release |
| 2025-04 | 2025-05-01 | 0,13125 | `gpt-4-turbo-2024-04-09` | – | `gemini-1.5-flash-002` | 27 | release |
| 2025-05 | 2025-06-01 | 0,13125 | `gpt-4o-2024-05-13` | – | `gemini-2.0-flash-lite-preview-02-05` | 21 | release |
| 2025-06 | 2025-07-01 | 0,13125 | `gpt-4o-2024-05-13` | – | `gemini-2.0-flash-lite-preview-02-05` | 28 | release |
| 2025-07 | 2025-08-01 | 0,13125 | `gpt-4o-2024-05-13` | – | `gemini-2.0-flash-lite-preview-02-05` | 30 | release |
| 2025-08 | 2025-09-01 | 0,175 | `chatgpt-4o-latest` | `gemini-1.5-pro-exp-0827` | `gemini-2.0-flash-001` | 23 | release |
| 2025-08 | 2025-09-03 | 0,13125 | `chatgpt-4o-latest` | `grok-2-2024-08-13` | `gemini-2.0-flash-lite-preview-02-05` | 29 | release |
| 2025-09 | 2025-10-01 | 0,175 | `o1-preview` | – | `gemini-2.0-flash-001` | 21 | release |
| 2025-10 | 2025-11-01 | 0,175 | `chatgpt-4o-latest-20240903` | `o1-preview` | `gemini-2.0-flash-001` | 20 | release |
| 2025-11 | 2025-12-01 | 0,85 | `gemini-exp-1121` | `o1-preview` | `gemini-2.5-flash` | 9 | release |
| 2025-11 | 2026-04-02 | 0,175 | `gemini-exp-1121` | `o1-preview` | `gemini-2.5-flash-lite-preview-09-2025-no-thinking` | 25 | backfill |
| 2025-12 | 2026-01-01 | 0,85 | `gemini-exp-1206` | `o1-2024-12-17` | `gemini-2.5-flash` | 9 | release |
| 2025-12 | 2026-04-02 | 0,275 | `gemini-exp-1206` | `o1-2024-12-17` | `grok-4-1-fast-reasoning` | 28 | backfill |
| 2026-01 | 2026-02-01 | 0,85 | `gemini-2.0-flash-thinking-exp-01-21` | `deepseek-r1` | `gemini-2.5-flash` | 9 | release |
| 2026-01 | 2026-04-02 | 0,275 | `gemini-2.0-flash-thinking-exp-01-21` | `deepseek-r1` | `grok-4-1-fast-reasoning` | 28 | backfill |
| 2026-02 | 2026-03-01 | 1 | `early-grok-3` | `deepseek-r1` | `glm-4.5` | 8 | release |
| 2026-02 | 2026-04-02 | 0,315 | `early-grok-3` | `deepseek-r1` | `deepseek-v3.2` | 26 | backfill |
| 2026-03 | 2026-04-01 | 3,4375 | `gemini-2.5-pro-exp-03-25` | `chatgpt-4o-latest-20250326` | `gemini-2.5-pro` | 1 | release |
| 2026-03 | 2026-04-02 | 1,125 | `gemini-2.5-pro-exp-03-25` | `chatgpt-4o-latest-20250326` | `gemini-3-flash` | 7 | backfill |
| 2026-04 | 2026-05-01 | 1 | `gemini-2.5-pro-exp-03-25` | `o3-2025-04-16` | `glm-4.6` | 25 | release |
| 2026-05 | 2026-06-01 | 0,75 | `gemini-2.5-pro-preview-05-06` | `o3-2025-04-16` | `mistral-large-3` | 29 | release |
| 2026-06 | 2026-07-01 | 1,125 | `gemini-2.5-pro` | – | `gemini-3-flash` | 15 | release |
| 2026-07 | 2026-08-01 | 1,125 | `gemini-2.5-pro` | – | `gemini-3-flash` | 18 | release |
| 2026-08 | 2026-09-01 | 0,2375 | `gemini-2.5-pro` | – | `glm-5.3-flash` | 25 | release |
| 2026-09 | 2026-10-01 | 0,2375 | `gemini-2.5-pro` | – | `glm-5.3-flash` | 30 | backfill |
| 2026-10 | 2026-11-01 | 0,2375 | `gemini-2.5-pro` | – | `GLM-5.3-Flash` | 33 | backfill |

Från 2025-08 är referensen ofta ett experimentnamn som har försvunnit ur tavlan, och efterföljaren bär tröskeln.
I 2026-03 är första versionen (b(m) = 2025-08-29) bara referensen själv, eftersom b(m) är gammal i mätglappet.

### L = 6 (alla versioner)

| Månad | Version (known_from) | Värde | Referens r(m) | Efterföljare | Modell vid minimum | Kvalificerade | source |
|---|---|---|---|---|---|---|---|
| 2024-07 | 2024-08-01 | 0,2625 | `gpt-4-turbo` | – | `gpt-4o-mini-2024-07-18` | 6 | release |
| 2024-08 | 2024-09-01 | 0,2625 | `gpt-4-1106-preview` | – | `gpt-4o-mini-2024-07-18` | 7 | release |
| 2024-09 | 2024-10-01 | 0,175 | `claude-3-opus-20240229` | – | `deepseek-v2.5` | 13 | release |
| 2024-10 | 2024-11-01 | 0,13125 | `gpt-4-turbo-2024-04-09` | – | `gemini-1.5-flash-002` | 11 | release |
| 2024-11 | 2024-12-01 | 2,1875 | `gpt-4o-2024-05-13` | – | `gemini-1.5-pro-002` | 4 | release |
| 2024-12 | 2025-01-01 | 0,175 | `gpt-4o-2024-05-13` | – | `deepseek-v3` | 6 | release |
| 2025-01 | 2025-02-01 | 0,175 | `gpt-4o-2024-05-13` | – | `deepseek-v3` | 7 | release |
| 2025-02 | 2025-03-01 | 0,175 | `chatgpt-4o-latest` | `gemini-1.5-pro-exp-0827` | `gemini-2.0-flash-001` | 7 | release |
| 2025-03 | 2025-04-01 | 0,175 | `o1-preview` | – | `gemini-2.0-flash-001` | 7 | release |
| 2025-04 | 2025-05-01 | 0,175 | `chatgpt-4o-latest-20240903` | – | `gemini-2.0-flash-001` | 11 | release |
| 2025-05 | 2025-06-01 | 0,4775 | `gemini-exp-1121` | – | `deepseek-v3-0324` | 8 | release |
| 2025-06 | 2025-07-01 | 0,85 | `gemini-exp-1206` | – | `gemini-2.5-flash` | 7 | release |
| 2025-07 | 2025-08-01 | 0,85 | `gemini-2.0-flash-thinking-exp-01-21` | – | `gemini-2.5-flash` | 7 | release |
| 2025-08 | 2025-09-01 | 3,4375 | `early-grok-3` | – | `gemini-2.5-pro` | 5 | release |
| 2025-08 | 2025-09-03 | 0,4775 | `early-grok-3` | `deepseek-r1` | `deepseek-v3.1` | 9 | release |
| 2025-09 | 2025-10-01 | 3,4375 | `gemini-2.5-pro-exp-03-25` | `chatgpt-4o-latest-20250326` | `gemini-2.5-pro` | 1 | release |
| 2025-10 | 2025-11-01 | 3,4375 | `gemini-2.5-pro-exp-03-25` | `o3-2025-04-16` | `gemini-2.5-pro` | 1 | release |
| 2025-11 | 2025-12-01 | 3,4375 | `gemini-2.5-pro-preview-05-06` | `o3-2025-04-16` | `gemini-2.5-pro` | 1 | release |
| 2025-12 | 2026-01-01 | 3,4375 | `gemini-2.5-pro` | – | `gemini-2.5-pro` | 1 | release |
| 2025-12 | 2026-04-02 | 1,125 | `gemini-2.5-pro` | – | `gemini-3-flash` | 3 | backfill |
| 2026-01 | 2026-02-01 | 3,4375 | `gemini-2.5-pro` | – | `gemini-2.5-pro` | 1 | release |
| 2026-01 | 2026-04-02 | 1,125 | `gemini-2.5-pro` | – | `gemini-3-flash` | 3 | backfill |
| 2026-02 | 2026-03-01 | 3,4375 | `gemini-2.5-pro` | – | `gemini-2.5-pro` | 1 | release |
| 2026-02 | 2026-04-02 | 1,125 | `gemini-2.5-pro` | – | `gemini-3-flash` | 6 | backfill |
| 2026-03 | 2026-04-01 | 3,4375 | `gemini-2.5-pro` | – | `gemini-2.5-pro` | 1 | release |
| 2026-03 | 2026-04-02 | 1,125 | `gemini-2.5-pro` | – | `gemini-3-flash` | 7 | backfill |
| 2026-04 | 2026-05-01 | 1,125 | `gemini-2.5-pro` | – | `gemini-3-flash` | 11 | backfill |
| 2026-05 | 2026-06-01 | 3,375 | `gemini-3-pro` | – | `gemini-3.5-flash` | 6 | backfill |
| 2026-06 | 2026-07-01 | 3,375 | `gemini-3-pro` | – | `gemini-3.5-flash` | 7 | backfill |
| 2026-07 | 2026-08-01 | 3,375 | `gemini-3-pro` | – | `gemini-3.5-flash-high` | 7 | backfill |
| 2026-08 | 2026-09-01 | 10 | `claude-opus-4-6` | – | `claude-opus-4-6-high` | 3 | backfill |
| 2026-09 | 2026-10-01 | 8 | `claude-opus-4-6-thinking` | `claude-opus-4-6` | `claude-opus-5.5-high` | 5 | backfill |
| 2026-10 | 2026-11-01 | 4 | `claude-opus-4-6-thinking` | `claude-opus-4-6` | `Gemini 4 Argon (High)` | 6 | release |

I de första versionerna för 2025-09 – 2026-03 är b(m) tavlan 2025-08-29 (mätglappet). Där kvalificerar bara Gemini
2.5 Pro, och från 2025-12 är den också referensen, så värdet blir referensens eget pris. Bulkversionerna 2026-04-02
använder månadens egen tavla och ändrar värdet för 2025-12 – 2026-03.

### Frontpriset (alla versioner)

| Månad | Version (known_from) | Värde | Modell | source |
|---|---|---|---|---|
| 2024-01 | 2024-02-01 | 15 | `gpt-4-turbo` | release |
| 2024-02 | 2024-03-01 | 15 | `gpt-4-1106-preview` | release |
| 2024-03 | 2024-04-01 | 30 | `claude-3-opus-20240229` | release |
| 2024-04 | 2024-05-01 | 15 | `gpt-4-turbo-2024-04-09` | release |
| 2024-05 | 2024-06-01 | 7,5 | `gpt-4o-2024-05-13` | release |
| 2024-06 | 2024-07-01 | 7,5 | `gpt-4o-2024-05-13` | release |
| 2024-07 | 2024-08-01 | 7,5 | `gpt-4o-2024-05-13` | release |
| 2024-08 | 2024-09-01 | 7,5 | `gpt-4o-2024-05-13` | release |
| 2024-09 | 2024-10-01 | 26,25 | `o1-preview` | release |
| 2024-10 | 2024-11-01 | 26,25 | `o1-preview` | release |
| 2024-11 | 2024-12-01 | 26,25 | `o1-preview` | release |
| 2024-12 | 2025-01-01 | 26,25 | `o1-2024-12-17` | release |
| 2025-01 | 2025-02-01 | 0,96 | `deepseek-r1` | release |
| 2025-02 | 2025-03-01 | 0,96 | `deepseek-r1` | release |
| 2025-03 | 2025-04-01 | 93,75 | `gpt-4.5-preview-2025-02-27` | release |
| 2025-04 | 2025-05-01 | 3,4375 | `gemini-2.5-pro-exp-03-25` | release |
| 2025-05 | 2025-06-01 | 3,4375 | `gemini-2.5-pro-preview-05-06` | release |
| 2025-06 | 2025-07-01 | 3,4375 | `gemini-2.5-pro` | release |
| 2025-07 | 2025-08-01 | 3,4375 | `gemini-2.5-pro` | release |
| 2025-08 | 2025-09-01 | 3,4375 | `gemini-2.5-pro` | release |
| 2025-09 | 2025-10-01 | 3,4375 | `gemini-2.5-pro` | release |
| 2025-10 | 2025-11-01 | 3,4375 | `gemini-2.5-pro` | release |
| 2025-11 | 2025-12-01 | 3,4375 | `gemini-2.5-pro` | release |
| 2025-11 | 2026-04-02 | 4,5 | `gemini-3-pro` | backfill |
| 2025-12 | 2026-01-01 | 3,4375 | `gemini-2.5-pro` | release |
| 2025-12 | 2026-04-02 | 4,5 | `gemini-3-pro` | backfill |
| 2026-01 | 2026-02-01 | 3,4375 | `gemini-2.5-pro` | release |
| 2026-01 | 2026-04-02 | 4,5 | `gemini-3-pro` | backfill |
| 2026-02 | 2026-03-01 | 3,4375 | `gemini-2.5-pro` | release |
| 2026-02 | 2026-04-02 | 10 | `claude-opus-4-6` | backfill |
| 2026-03 | 2026-04-01 | 3,4375 | `gemini-2.5-pro` | release |
| 2026-03 | 2026-04-02 | 10 | `claude-opus-4-6-thinking` | backfill |
| 2026-04 | 2026-05-01 | 10 | `claude-opus-4-6-thinking` | release |
| 2026-05 | 2026-06-01 | 10 | `claude-opus-4-6-thinking` | release |
| 2026-06 | 2026-07-01 | 10 | `claude-opus-4-6-thinking` | release |
| 2026-07 | 2026-08-01 | 10 | `claude-opus-5-max` | release |
| 2026-08 | 2026-09-01 | 10 | `claude-opus-5-max` | release |
| 2026-09 | 2026-10-01 | 8 | `claude-opus-5.5-high` | release |
| 2026-10 | 2026-11-01 | 4 | `Gemini 4 Argon (High)` | release |

Frontpriset hoppar mellan prisnivåer, eftersom fronten byter leverantör: från 26,25 (o1) till 0,96 (DeepSeek R1, som var
bäst prissatta modell i januari 2025 när Geminis experimentnamn låg över) och 93,75 (GPT-4.5 Preview). Det är sammanhang
och inget takmått. Kolumnen `board_top` i `price_rolling.table()` visar tavlans etta, så att man ser när den inte är
prissatt.

## 5. Handkontroller

Nio versioner kontrollerades mot råfilerna, oberoende av koden: Arenas Space-filer (`elo_results_<datum>.pkl`, lästa
med `arena.pickle_tables`), datasetets `text`-parquet i HEAD (`62968a5`), LiteLLM:s fil vid månadsslut (`git show
<sha>:model_prices_and_context_window.json`) och Epochs `eci_scores.csv` i dagens ZIP. Δ för efterföljarna räknades om
ur råtavlorna. Allt stämmer med serierna.

| Version | Tavlor | Referens och tröskel | Modell vid minimum | Pris i LiteLLM | known_from |
|---|---|---|---|---|---|
| L = 12, 2025-01 | b(m) 2025-01-28 (Space, `text/full`); ref 2024-01-25 (Space, `elo_rating_final`) | Etta `gpt-4-turbo` 1 249,46, bytt till `gpt-4-1106-preview`, som har 1 250,05 i b(m) | `gemini-1.5-flash-002` 1 271,38 | 0,075 / 0,30 (2025-01-31, `9f0f2b3f01`) → 0,13125 | 2025-02-01 |
| L = 12, 2025-08, version 1 | b(m) 2025-08-04 (Space); ref 2024-08-28 (Space) | Etta `chatgpt-4o-latest` 1 316,16 saknas. `gemini-1.5-pro-exp-0827` 1 316,11 + Δ 15,30 (2024-08-27, 08-28, 09-04) = 1 331,40 | `gemini-2.0-flash-001` 1 362,06 (`gemini/gemini-2.0-flash`) | 0,10 / 0,40 (2025-08-30, `fa4c833e58`) → 0,175 | 2025-09-01 |
| L = 12, 2025-08, version 2 | b(m) 2025-08-29 (Space-fil utan datasetmotsvarighet, belagd 2025-09-03) | `gemini-1.5-pro-exp-0827` saknas också. `grok-2-2024-08-13` 1 306,27 + Δ 21,34 = 1 327,60 | `gemini-2.0-flash-lite-preview-02-05` 1 330,85 | 0,075 / 0,30 → 0,13125 | 2025-09-03 |
| L = 12, 2025-12, version 2 | b(m) 2025-12-30 (bulk, belagd 2026-04-02); ref 2024-12-30 (Space) | Etta `gemini-exp-1206` 1 373,46 saknas. `o1-2024-12-17` 1 365,24 + Δ 23,94 (2025-07-28, 08-01, 08-04) = 1 389,18 | `grok-4-1-fast-reasoning` 1 409,83 | xai 0,20 / 0,50 (2025-12-28, `861b103dc0`) → 0,275 | 2026-04-02, `backfill` |
| L = 12, 2026-10 | b(m) 2026-10-28 (dataset, belagd 2026-10-29, visningsnamn); ref 2025-10-17 (bulk) | Etta `gemini-2.5-pro` 1 464,75 = "Gemini 2.5 Pro" 1 457,70 i b(m) | "GLM-5.3-Flash" 1 473,04 (`zai/glm-5.3-flash`) | 0,15 / 0,50 (2026-10-31, `b2647116ca`) → 0,2375 | 2026-11-01, `backfill` (referenstavlan) |
| L = 6, 2024-11 | b(m) 2024-11-22 (Space); ref 2024-05-27 (Space, `full_old`) | Etta `gpt-4o-2024-05-13` 1 281,63, i b(m) 1 284,96 | `gemini-1.5-pro-002` 1 300,58 | 3,50 / 10,50 (2024-11-27, `2d2931a215`), rättat till 1,25 / 5,00 från 2024-10-01 (`PRICE_CORRECTIONS`) → 2,1875 | 2024-12-01 |
| L = 6, 2026-10 | b(m) 2026-10-28; ref 2026-04-30 (dataset) | Etta `claude-opus-4-6-thinking` 1 500,56 saknas (namnet finns till 2026-08-11, `-high` från 2026-08-12). `claude-opus-4-6` = "Claude Opus 4.6" 1 496,25 + Δ 5,46 (2026-08-06, 08-10, 08-11) = 1 501,71 | "Gemini 4 Argon (High)" 1 528,58 (`gemini/gemini-4-argon`) | 2,00 / 10,00 (2026-10-31) → 4,00 | 2026-11-01 |
| Frontpris, 2025-03 | b(m) 2025-03-30 (Space) | Ettan `gemini-2.5-pro-exp-03-25` 1 440,12 är kopplad till `gemini/gemini-2.5-pro-preview-03-25`, men nyckeln finns inte i LiteLLM 2025-03-31. Bästa prissatta: 1 397,82 | `gpt-4.5-preview-2025-02-27` | 75 / 150 (2025-03-31, `dfb838eaff`) → 93,75 | 2025-04-01 |
| ECI, 2026-03 | – | Gemini 2.5 Pro (Mar 2025), ECI 143,98, släppt 2025-03-31, är högst bland modeller släppta ≤ 2025-03-31 | Grok 4 Fast, ECI 144,32 (`xai/grok-4-fast-reasoning`). De billigare kopplade nycklarna (GPT-5 nano 0,1375, Gemini 2.0 Flash och 2.5 Flash-Lite 0,175) har ECI ≤ 139,07 | 0,20 / 0,50 (2026-03-29, `92db2df2f6`) → 0,275 | `backfill` |

Priskontroll mot utvecklarnas egna sidor (`arena_price.PRICE_CHECKS`) finns bara för nycklar som satte minimum i G2A.
I senaste versionen per månad är status för L = 12: 8 `developer_page`, 1 `blocked` och 13 `unchecked`; för L = 6: 2,
5 och 21. Nya nycklar vid minimum (bland andra `zai/glm-5.3-flash`, `gemini/gemini-3-flash-preview`,
`gemini/gemini-3.5-flash`, `xai/grok-4-1-fast-reasoning`, `mistral/mistral-large-2512`) är bara kontrollerade mot
LiteLLM-filen, inte mot utvecklarens prislista. **Det är overifierat.**

## 6. Känsligheter (registrerade, lagras inte)

**Bokstavlig referensregel** (referensen enligt det som var känt vid slutet av m − L, `literal_reference=True`):

| | Månader med annat värde (senaste versionen) |
|---|---|
| L = 12 | inga. I 2026-09 och 2026-10 är ettan `gemini-2.5-pro` med båda reglerna |
| L = 6 | 2026-05 – 2026-09. Referensen blir `gemini-2.5-pro` (tavlan 2025-08-29) i stället för `gemini-3-pro`, `claude-opus-4-6` och `claude-opus-4-6-thinking`. Värdet blir 1,125 i stället för 3,375 (2026-05 – 07) och 0,2375 i stället för 10 respektive 8 (2026-08 – 09) |

Valet av regel spelar alltså stor roll för L = 6 i de månaderna. Den bokstavliga regeln mäter där fronten för 9–13
månader sedan, inte för 6.

**Utan Mistral Small 3.2** (omstritt pris, G2A R-4): inget värde ändras i någon variant. Modellen ligger under alla
rörliga trösklar.

## 7. Nivåkontroll: binder tröskeln?

Inte registrerad som känslighet. Det är samma kontroll av datakorrekthet som i G2A (avsnitt 4), och den räknar ingen
takt. Golvet är det lägsta priset bland alla kopplade och prissatta nycklar i samma tavla, utan tröskel.

- **L = 12:** värdet är lika med golvet i 8 av 28 versioner, alla 2025-01 – 2025-08 (golvet var Gemini 1.5 Flash och 2.0
  Flash-Lite, 0,13125). Från 2025-09 ligger värdet över golvet i varje version. Då är förra årets front
  (o1-preview och senare) för stark för den billigaste nivån.
- **L = 6:** värdet är lika med golvet i 1 av 33 versioner (2024-10).
- Avståndet mellan modellen vid minimum och tröskeln är ofta litet: under 5 poäng i 15 av 61 versioner och under 1
  poäng i 7. Fyra av dem är versioner där bara referensen själv kvalificerar (avstånd 0, L = 6 i mätglappet), och tre
  ligger mellan 0,4 och 0,9 poäng (L = 6 2026-06 och 2026-07, L = 12 2025-11 i bulkversionen). Arenas
  osäkerhetsintervall används inte, så en modell kan kvalificera eller falla bort på brus.

## 8. Kostnad per uppgift: BLOCKED

Registrerat mått, inte byggt (registret, posten Q1):

- **Arenas `agent`-delmängd** (Agent Arena, från 2026-06-04, 54 tavlor till 2026-11-22) har `cost_per_task_p50` och
  `output_tokens_per_task_p50`. Kolumnerna är tomma till och med 2026-10-28 och ifyllda för 53 – 64 modeller per tavla
  från 2026-11-02. Det finns alltså ingen hel månad ännu, och första möjliga månad för
  `g2_cost_per_task_rolling6_agent` är 2026-12.
- **Vad som saknas:** Arenas metodsida (arena.ai) nekas av proxyn. Det går inte att se vilket pris kostnaden bygger på
  (listpris, cachade tokens, resonemangstokens) eller vilken agentmiljö som används. Måttet byggs när en hel månad
  finns och metoden är läst.
- **Epoch:** `*_external.csv` har kostnad per uppgift för ARC-AGI 1 och 2, CursorBench, DeepSWE, WeirdML, FrontierSWE,
  ALE-Bench, Aider polyglot och OSWorld 2, men inget körningsdatum (bara modellens release, och för Aider ett
  utvärderingsdatum). Kostnaden är utvärderarens egen, med egna priser och egen miljö. Inget ärligt `known_from`. Epochs
  egna körningar (med `Started at`) har inga tokenantal i ZIP-filen, bara länkar till loggar.
- **METR:** `benchmark_results_1_1.yaml` har inga token- eller kostnadsfält.
- **SWE-bench:** repot saknar licens (`publish=False`), och tokenantal per bidrag är inte standardiserade. Inte
  undersökt vidare.

## 9. Förbehåll

1. **Arena mäter preferens, inte förmåga att lösa uppgifter.** Ratingen bygger på parvisa omdömen i chatt. Stil och
   längd påverkar (stilkontroll används inte i `text`). Referensen är fronten i preferens, inte i benchmarks.
2. **Listpris, inte transaktionspris.** LiteLLM:s fil är prislistor. Rabatter, batch, cachade tokens och avtalspriser
   ingår inte. LiteLLM släpar och har fel (G2A avsnitt 6). De flesta nya nycklar vid minimum är inte kontrollerade mot
   utvecklarens prislista.
3. **Öppna vikter följer kanalregeln i `model_map`.** Bara utvecklarens eget API räknas. Billigare tredjepartsvärdar
   för öppna modeller (till exempel Llama, Qwen och gpt-oss hos DeepInfra eller Together) ingår inte, och inte heller
   utvecklare utanför regeln. Nivån kan därför ligga över det billigaste tillgängliga priset.
4. **Pris per token, inte per uppgift.** Resonemangsvarianter (`-high`, "(Max)", "(High)") använder fler tokens per svar
   men säljs till samma pris per token. Bästa varianten per nyckel räknas, så en modell kan kvalificera genom en
   variant som kostar mer per uppgift.
5. **Efterföljarregeln antar att skillnaden mellan två modeller är stabil** mellan tavlor. Δ mäts i tavlor upp till ett år
   före b(m), över omviktningen 2025-07-23 och bytet till stilkontroll som standard 2025-05-16. Felet är troligen några
   poäng, men det är inte mätt.
6. **Mätglappet 2025-09 – 2026-03 och den censurerade bulkuppladdningen.** De första versionerna i glappet använder
   tavlan 2025-08-29 och blir ibland bara referensens eget pris. Bulktavlorna saknar modeller som senare bytt namn eller
   tagits bort, så en etta i en bulktavla kan vara fel modell. Sådana rader är märkta `backfill`.
7. **Referensen kan vara ett experimentnamn** som aldrig sålts (till exempel `gemini-exp-1206`, `early-grok-3`). Det är
   avsiktligt: frågan gäller förmågenivån.
8. **ECI-varianten läcker.** ECI och tröskeln är dagens skattningar, och hela historiken är `backfill`. Marginalerna är
   små (Grok 4 Fast 144,32 mot tröskeln 143,98 i 2026-03).
9. **Korta serier.** 22 månader (L = 12) och 28 (L = 6). Värdena rör sig i steg när en enskild modell kommer in, ändrar
   pris eller pensioneras. Spåret räknar ingen takt.

## 10. Förslag (inte beslutat här)

- Serierna är katalogserier. Grenindex och tillstånd ändras inte. Första skarpa ögonblicksbilden 2026-11-30 påverkas
  inte.
- Om G2 ska få en kärnserie med rörlig tröskel är `g2_price_rolling12_arena` kandidaten. Det kräver först en oberoende
  granskning (förregistrering, efterföljarregeln, normaliseringen av namn, märkningen `backfill` och priserna vid
  minimum). Den skulle ersätta Arena-varianterna A och B, inte läggas till, eftersom det är samma källa och samma
  begrepp (samma familj i index v2). Klassen `okänd` (Space-filerna) gör att den inte ingår i den kommersiellt rena
  delmängden.
