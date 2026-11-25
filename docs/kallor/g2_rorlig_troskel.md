# Pris vid rörlig förmågetröskel (G2), spår Q1

Körning 14, spår Q1, 2026-11-25. Förslag 6 i [riktning.md](../riktning.md). Definitionerna är låsta i
[måttregistret](../mattregister.md), posten "2026-11-25 – Q1: pris vid rörlig förmågetröskel". Serierna är
katalogserier, inte kärnserier. **Inga takter, halveringstider eller trender beräknas i spåret.**

## 1. Vad som tittades på före registreringen

Registerposten committades innan något värde för de nya serierna räknades. Före posten tittade spåret bara på detta:

- **Referensmodellerna.** För varje månad m till 2026-10 och L = 6 och 12: vilken modell som var etta i tavlan för
  m − L (både enligt det som var känt vid d och enligt det som var känt vid slutet av m − L), och om den finns i b(m)
  med exakt namn. Bara namn och närvaro, inga ratingar. Fynd: ettan saknas i b(m) i 31 av versionerna. Det är nästan
  alltid ett experiment- eller förhandsnamn som tagits bort när modellen släpptes (`gemini-exp-1121`,
  `gemini-exp-1206`, `gemini-2.0-flash-thinking-exp-01-21`, `early-grok-3`, `gemini-2.5-pro-exp-03-25`,
  `gemini-2.5-pro-preview-05-06`), ett namnbyte (`gpt-4-turbo` → `gpt-4-1106-preview`, redan i `arena_map`;
  `chatgpt-4o-latest` finns till 2024-09-04, `chatgpt-4o-latest-20240808` från 2024-09-15; `claude-opus-4-6-thinking`
  finns till 2026-08-11, `claude-opus-4-6-high` från 2026-08-12) eller bytet till visningsnamn (`gemini-2.5-pro` finns
  till 2026-10-15, "Gemini 2.5 Pro" från 2026-10-20). Efterföljarregeln är alltså central och inget undantag.
  *Rättat i X19 (R22-2):* Q1 räknade först `gpt-4-turbo` och `chatgpt-4o-latest` som experimentnamn. Båda är namnbyten,
  och de två senare bytena saknades i Q1:s regel (avsnitt 11).
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
- **Tröskeln** är r(m):s rating i b(m). Hittas r(m) inte i b(m), används modellerna närmast under r(m) i
  referenstavlan (rang 2 – 11) som finns i b(m) och delar minst 3 tidigare tavlor med r(m). Varje sådan kandidat ger en
  tröskel: dess rating plus medianen av skillnaden r − s i de 3 senaste gemensamma tavlorna. Tröskeln är medianen över
  kandidaterna (X19, avsnitt 11; Q1 tog den första kandidaten). Finns ingen kandidat blir månaden en lucka.
- **Värdet** är det lägsta blandade förstapartspriset (3:1, LiteLLM vid månadsslut, G2A:s prisrättningar och regel om
  pensionerade modeller) bland nycklar med rating ≥ tröskeln i b(m).
- **Frontpriset** är priset för den högst rankade prissatta modellen i b(m). Det är sammanhang och inget takmått.
- **ECI-varianten** har tröskeln = högsta ECI bland modeller släppta ≤ slutet av m − 12 (dagens ECI), och värde bara när
  tröskeln är ≥ 128.

## 4. Serier

| Nyckel | Månader | Rader | `backfill`-rader | Månader där efterföljare används | Licensklass |
|---|---|---|---|---|---|
| `g2_price_rolling12_arena` (huvudvariant) | 2025-01 – 2026-10 (22) | 27 | 7 | 8 | `okänd` |
| `g2_price_rolling6_arena` | 2024-07 – 2026-10 (28) | 33 | 10 | 4 | `okänd` |
| `g2_price_frontier_arena` | 2024-01 – 2026-10 (34) | 39 | 5 | – | `okänd` |
| `g2_price_rolling12_eci` | 2025-05 – 2026-10 (18) | 18 | 18 (hela historiken) | – | `ja` |

Bygg med `python -m ai_tracker.observations g2_price_rolling12_arena g2_price_rolling6_arena g2_price_frontier_arena
g2_price_rolling12_eci` (Arena cirka 150 s kall, LiteLLM cirka 35 s, Epoch-ZIP en hämtning). Talen gäller efter
rättningen X19 (avsnitt 11). Q1 hade 28 rader för L = 12, och efterföljare i 9 månader (L = 12) och 7 (L = 6).
Datatesterna (`python -m ai_tracker.warehouse`) passerar: `fresh`, `unique_key`, `no_nulls`,
`known_from_after_period_end`, `fetched_known_from_not_after_fetch`, `freq_matches_catalog`, `no_gaps` och
`series_in_catalog` är alla ok. Ingen månad blev en lucka.

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

| Månad | Version (known_from) | Värde | Referens r(m) | Kandidater | Spridning (poäng) | Δ-ålder (dagar) | Modell vid minimum | Kvalificerade | source |
|---|---|---|---|---|---|---|---|---|---|
| 2025-01 | 2025-02-01 | 0,13125 | `gpt-4-turbo` | – | – | – | `gemini-1.5-flash-002` | 16 | release |
| 2025-02 | 2025-03-01 | 0,13125 | `gpt-4-1106-preview` | – | – | – | `gemini-1.5-flash-002` | 21 | release |
| 2025-03 | 2025-04-01 | 0,13125 | `claude-3-opus-20240229` | – | – | – | `gemini-1.5-flash-002` | 23 | release |
| 2025-04 | 2025-05-01 | 0,13125 | `gpt-4-turbo-2024-04-09` | – | – | – | `gemini-1.5-flash-002` | 27 | release |
| 2025-05 | 2025-06-01 | 0,13125 | `gpt-4o-2024-05-13` | – | – | – | `gemini-2.0-flash-lite-preview-02-05` | 21 | release |
| 2025-06 | 2025-07-01 | 0,13125 | `gpt-4o-2024-05-13` | – | – | – | `gemini-2.0-flash-lite-preview-02-05` | 28 | release |
| 2025-07 | 2025-08-01 | 0,13125 | `gpt-4o-2024-05-13` | – | – | – | `gemini-2.0-flash-lite-preview-02-05` | 30 | release |
| 2025-08 | 2025-09-01 | 0,175 | `chatgpt-4o-latest` | – | – | – | `gemini-2.0-flash-001` | 23 | release |
| 2025-09 | 2025-10-01 | 0,175 | `o1-preview` | – | – | – | `gemini-2.0-flash-001` | 21 | release |
| 2025-10 | 2025-11-01 | 0,175 | `chatgpt-4o-latest-20240903` | 7 (först `o1-preview`) | 0,09 | 25 | `gemini-2.0-flash-001` | 20 | release |
| 2025-11 | 2025-12-01 | 0,85 | `gemini-exp-1121` | 4 (först `o1-preview`) | 0,06 | 25 | `gemini-2.5-flash` | 9 | release |
| 2025-11 | 2026-04-02 | 0,175 | `gemini-exp-1121` | 4 (först `o1-preview`) | 0,64 | 114 | `gemini-2.5-flash-lite-preview-09-2025-no-thinking` | 25 | backfill |
| 2025-12 | 2026-01-01 | 0,85 | `gemini-exp-1206` | 3 (först `o1-2024-12-17`) | 0,12 | 25 | `gemini-2.5-flash` | 9 | release |
| 2025-12 | 2026-04-02 | 0,275 | `gemini-exp-1206` | 3 (först `o1-2024-12-17`) | 0,64 | 148 | `grok-4-1-fast-reasoning` | 28 | backfill |
| 2026-01 | 2026-02-01 | 0,85 | `gemini-2.0-flash-thinking-exp-01-21` | 3 (först `deepseek-r1`) | 0,12 | 25 | `gemini-2.5-flash` | 9 | release |
| 2026-01 | 2026-04-02 | 0,275 | `gemini-2.0-flash-thinking-exp-01-21` | 3 (först `deepseek-r1`) | 0,52 | 178 | `grok-4-1-fast-reasoning` | 28 | backfill |
| 2026-02 | 2026-03-01 | 1 | `early-grok-3` | 2 (först `deepseek-r1`) | 4,80 | 25 | `glm-4.5` | 8 | release |
| 2026-02 | 2026-04-02 | 0,275 | `early-grok-3` | 2 (först `deepseek-r1`) | 8,22 | 206 | `grok-4-1-fast-reasoning` | 31 | backfill |
| 2026-03 | 2026-04-01 | 3,4375 | `gemini-2.5-pro-exp-03-25` | 4 (först `chatgpt-4o-latest-20250326`) | 16,00 | 99 | `gemini-2.5-pro` | 1 | release |
| 2026-03 | 2026-04-02 | 1,125 | `gemini-2.5-pro-exp-03-25` | 4 (först `chatgpt-4o-latest-20250326`) | 19,39 | 313 | `gemini-3-flash` | 7 | backfill |
| 2026-04 | 2026-05-01 | 1,125 | `gemini-2.5-pro-exp-03-25` | 4 (först `o3-2025-04-16`) | 25,25 | 343 | `gemini-3-flash` | 11 | release |
| 2026-05 | 2026-06-01 | 1,125 | `gemini-2.5-pro-preview-05-06` | 4 (först `o3-2025-04-16`) | 21,20 | 296 | `gemini-3-flash` | 19 | release |
| 2026-06 | 2026-07-01 | 1,125 | `gemini-2.5-pro` | – | – | – | `gemini-3-flash` | 15 | release |
| 2026-07 | 2026-08-01 | 1,125 | `gemini-2.5-pro` | – | – | – | `gemini-3-flash` | 18 | release |
| 2026-08 | 2026-09-01 | 0,2375 | `gemini-2.5-pro` | – | – | – | `glm-5.3-flash` | 25 | release |
| 2026-09 | 2026-10-01 | 0,2375 | `gemini-2.5-pro` | – | – | – | `glm-5.3-flash` | 29 | backfill |
| 2026-10 | 2026-11-01 | 0,2375 | `gemini-2.5-pro` | – | – | – | `GLM-5.3-Flash` | 33 | backfill |

Tabellerna gäller efter X19. *Kandidater* är antalet giltiga efterföljare (tröskeln är medianen över dem), med den
första i rangordning. *Spridning* är största minus minsta kandidattröskel. *Δ-ålder* är antalet dagar mellan den
senaste Δ-tavlan och b(m). Alla kandidater finns i kolumnen `via` i `price_rolling.table()`.

Från 2025-10 är referensen ofta ett experimentnamn som har försvunnit ur tavlan, och efterföljarna bär tröskeln.
I 2026-03 är första versionen (b(m) = 2025-08-29) bara referensen själv, eftersom b(m) är gammal i mätglappet.

### L = 6 (alla versioner)

| Månad | Version (known_from) | Värde | Referens r(m) | Kandidater | Spridning (poäng) | Δ-ålder (dagar) | Modell vid minimum | Kvalificerade | source |
|---|---|---|---|---|---|---|---|---|---|
| 2024-07 | 2024-08-01 | 0,2625 | `gpt-4-turbo` | – | – | – | `gpt-4o-mini-2024-07-18` | 6 | release |
| 2024-08 | 2024-09-01 | 0,2625 | `gpt-4-1106-preview` | – | – | – | `gpt-4o-mini-2024-07-18` | 7 | release |
| 2024-09 | 2024-10-01 | 0,175 | `claude-3-opus-20240229` | – | – | – | `deepseek-v2.5` | 13 | release |
| 2024-10 | 2024-11-01 | 0,13125 | `gpt-4-turbo-2024-04-09` | – | – | – | `gemini-1.5-flash-002` | 11 | release |
| 2024-11 | 2024-12-01 | 2,1875 | `gpt-4o-2024-05-13` | – | – | – | `gemini-1.5-pro-002` | 4 | release |
| 2024-12 | 2025-01-01 | 0,175 | `gpt-4o-2024-05-13` | – | – | – | `deepseek-v3` | 6 | release |
| 2025-01 | 2025-02-01 | 0,175 | `gpt-4o-2024-05-13` | – | – | – | `deepseek-v3` | 7 | release |
| 2025-02 | 2025-03-01 | 0,175 | `chatgpt-4o-latest` | – | – | – | `gemini-2.0-flash-001` | 7 | release |
| 2025-03 | 2025-04-01 | 0,175 | `o1-preview` | – | – | – | `gemini-2.0-flash-001` | 7 | release |
| 2025-04 | 2025-05-01 | 0,175 | `chatgpt-4o-latest-20240903` | – | – | – | `gemini-2.0-flash-001` | 11 | release |
| 2025-05 | 2025-06-01 | 0,4775 | `gemini-exp-1121` | – | – | – | `deepseek-v3-0324` | 8 | release |
| 2025-06 | 2025-07-01 | 0,85 | `gemini-exp-1206` | – | – | – | `gemini-2.5-flash` | 7 | release |
| 2025-07 | 2025-08-01 | 0,85 | `gemini-2.0-flash-thinking-exp-01-21` | – | – | – | `gemini-2.5-flash` | 7 | release |
| 2025-08 | 2025-09-01 | 3,4375 | `early-grok-3` | – | – | – | `gemini-2.5-pro` | 5 | release |
| 2025-08 | 2025-09-03 | 0,4775 | `early-grok-3` | 2 (först `deepseek-r1`) | 4,80 | 25 | `deepseek-v3.1` | 9 | release |
| 2025-09 | 2025-10-01 | 3,4375 | `gemini-2.5-pro-exp-03-25` | 4 (först `chatgpt-4o-latest-20250326`) | 16,00 | 99 | `gemini-2.5-pro` | 1 | release |
| 2025-10 | 2025-11-01 | 3,4375 | `gemini-2.5-pro-exp-03-25` | 4 (först `o3-2025-04-16`) | 12,49 | 99 | `gemini-2.5-pro` | 1 | release |
| 2025-11 | 2025-12-01 | 3,4375 | `gemini-2.5-pro-preview-05-06` | 4 (först `o3-2025-04-16`) | 8,11 | 25 | `gemini-2.5-pro` | 1 | release |
| 2025-12 | 2026-01-01 | 3,4375 | `gemini-2.5-pro` | – | – | – | `gemini-2.5-pro` | 1 | release |
| 2025-12 | 2026-04-02 | 1,125 | `gemini-2.5-pro` | – | – | – | `gemini-3-flash` | 3 | backfill |
| 2026-01 | 2026-02-01 | 3,4375 | `gemini-2.5-pro` | – | – | – | `gemini-2.5-pro` | 1 | release |
| 2026-01 | 2026-04-02 | 1,125 | `gemini-2.5-pro` | – | – | – | `gemini-3-flash` | 3 | backfill |
| 2026-02 | 2026-03-01 | 3,4375 | `gemini-2.5-pro` | – | – | – | `gemini-2.5-pro` | 1 | release |
| 2026-02 | 2026-04-02 | 1,125 | `gemini-2.5-pro` | – | – | – | `gemini-3-flash` | 6 | backfill |
| 2026-03 | 2026-04-01 | 3,4375 | `gemini-2.5-pro` | – | – | – | `gemini-2.5-pro` | 1 | release |
| 2026-03 | 2026-04-02 | 1,125 | `gemini-2.5-pro` | – | – | – | `gemini-3-flash` | 7 | backfill |
| 2026-04 | 2026-05-01 | 1,125 | `gemini-2.5-pro` | – | – | – | `gemini-3-flash` | 11 | backfill |
| 2026-05 | 2026-06-01 | 3,375 | `gemini-3-pro` | – | – | – | `gemini-3.5-flash` | 6 | backfill |
| 2026-06 | 2026-07-01 | 3,375 | `gemini-3-pro` | – | – | – | `gemini-3.5-flash` | 7 | backfill |
| 2026-07 | 2026-08-01 | 3,375 | `gemini-3-pro` | – | – | – | `gemini-3.5-flash-high` | 7 | backfill |
| 2026-08 | 2026-09-01 | 10 | `claude-opus-4-6` | – | – | – | `claude-opus-4-6-high` | 3 | backfill |
| 2026-09 | 2026-10-01 | 8 | `claude-opus-4-6-thinking` | – | – | – | `claude-opus-5.5-high` | 5 | backfill |
| 2026-10 | 2026-11-01 | 4 | `claude-opus-4-6-thinking` | – | – | – | `Gemini 4 Argon (High)` | 6 | release |

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

Handkontrollerna ovan gäller Q1:s regler. Efter X19 gäller de utom i tre fall. I L = 12 2025-08 version 1 hittas
referensen nu direkt som `chatgpt-4o-latest-20240808` (1 334,72), med samma värde 0,175. L = 12 2025-08 version 2 finns
inte längre (avsnitt 11). I L = 6 2026-10 hittas referensen nu som "Claude Opus 4.6 (High)" (1 501,72, mot 1 501,71
med efterföljaren), med samma värde 4.

Priskontroll mot utvecklarnas egna sidor (`arena_price.PRICE_CHECKS`) finns bara för nycklar som satte minimum i G2A. I
senaste versionen per månad efter X19 är status för L = 12: 7 `developer_page` och 15 `unchecked` (Q1: 8, 1 `blocked`
och 13); för L = 6: 2 `developer_page`, 5 `blocked` och 21 `unchecked`. Nya nycklar vid minimum (bland andra
`zai/glm-5.3-flash`, `gemini/gemini-3-flash-preview`, `gemini/gemini-3.5-flash`, `xai/grok-4-1-fast-reasoning`,
`mistral/mistral-large-2512`) är bara kontrollerade mot LiteLLM-filen, inte mot utvecklarens prislista. **Det är
overifierat.**

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

Omräknat efter X19: båda känsligheterna ger samma resultat som ovan.

## 7. Nivåkontroll: binder tröskeln?

Inte registrerad som känslighet. Det är samma kontroll av datakorrekthet som i G2A (avsnitt 4), och den räknar ingen
takt. Golvet är det lägsta priset bland alla kopplade och prissatta nycklar i samma tavla, utan tröskel.

- **L = 12:** värdet är lika med golvet i 7 av 27 versioner, alla 2025-01 – 2025-07 (golvet var Gemini 1.5 Flash och 2.0
  Flash-Lite, 0,13125). Från 2025-08 ligger värdet över golvet i varje version. Då är förra årets front
  (`chatgpt-4o-latest`, o1-preview och senare) för stark för den billigaste nivån. Q1 hade 8 av 28, med versionen
  2025-09-03 för 2025-08, som inte finns efter X19.
- **L = 6:** värdet är lika med golvet i 1 av 33 versioner (2024-10).
- **ECI-varianten** (R22-4): värdet är lika med golvet i 7 av 18 månader, 2025-05 – 2025-11 (Gemini 2.0 Flash 0,175 till
  2025-07, sedan GPT-5 nano 0,1375). Golvet är här det lägsta priset bland kopplade prissatta nycklar med känd ECI.
  Under de månaderna binder tröskeln alltså inte, och serien visar golvets pris. Från 2025-12 ligger värdet över
  golvet. Marginalen mellan modellen vid minimum och tröskeln är tunn i 2026-03 (0,34 ECI-poäng, Grok 4 Fast 144,32 mot
  143,98) och i 2026-06 (0,37, MiniMax-M3 147,84 mot 147,47).
- Avståndet mellan modellen vid minimum och tröskeln i Arena-varianterna är ofta litet: under 5 poäng i 14 av 60
  versioner och under 1 poäng i 8. Fyra av dem är versioner där bara referensen själv kvalificerar (avstånd 0, L = 6
  2025-12 – 2026-03 i första versionen). Fyra ligger mellan 0,26 och 0,89 poäng (L = 6 2026-06 och 2026-07, L = 12
  2025-11 och 2026-02 i bulkversionerna). Arenas osäkerhetsintervall används inte, så en modell kan kvalificera eller
  falla bort på brus. Q1 hade 15 av 61 och 7.
- Golvet står i kolumnen `floor` i `price_rolling.table()` och `price_rolling.eci_table()` (X19).

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
  utvärderingsdatum). *Tillägg i X19 (R22 N-5):* TheAgentCompany-filen har också en kolumn `Date`. Den är inte tolkad,
  och det är oklart om den är körningens eller modellens datum. Kostnaden är utvärderarens egen, med egna priser och
  egen miljö. Inget ärligt `known_from`. Epochs
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
   före b(m), över omviktningen 2025-07-23 och bytet till stilkontroll som standard 2025-05-16. Felet är mätt (R22):
   skillnaden mellan två närliggande modeller ändras med 2,3 poäng i median på 3 månader och 3,8 poäng på 12 månader,
   och 90:e percentilen är 8,7 respektive 12,1 poäng. Kandidaternas trösklar skiljer sig med upp till 25 poäng när Δ är
   nästan ett år gammal (L = 12 2026-04: 25,25 poäng, Δ-ålder 343 dagar). Med Q1:s regel (första kandidaten) berodde
   värdet på kandidatordningen i 5 av 22 månader för L = 12 (2025-08 och 2026-02 – 2026-05). Efter X19 är tröskeln
   medianen över kandidaterna, så ordningen spelar ingen roll, men osäkerheten finns kvar. Med den lägsta eller den
   högsta kandidattröskeln i stället för medianen blir värdet ett annat i 4 av 22 månader för L = 12 (2026-02 – 2026-05)
   och i ingen månad för L = 6. Δ:s ålder och spridningen står i kolumnerna `delta_to` och `threshold_spread`.
6. **Mätglappet 2025-09 – 2026-03 och den censurerade bulkuppladdningen.** De första versionerna i glappet använder
   tavlan 2025-08-29 och blir ibland bara referensens eget pris. Bulktavlorna saknar modeller som senare bytt namn eller
   tagits bort, så en etta i en bulktavla kan vara fel modell. Sådana rader är märkta `backfill`.
7. **Referensen kan vara ett experimentnamn** som aldrig sålts (till exempel `gemini-exp-1206`, `early-grok-3`). Det är
   avsiktligt: frågan gäller förmågenivån.
8. **ECI-varianten läcker.** ECI och tröskeln är dagens skattningar, och hela historiken är `backfill`. Marginalerna är
   små (Grok 4 Fast 144,32 mot tröskeln 143,98 i 2026-03), och i 2025-05 – 2025-11 ligger serien på golvet (avsnitt 7).
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
- *Efter R22 och X19:* granskningen R22 godkände serierna som katalogserier men inte L = 12 som kärnserie. X19 rättade
  namnbytena och kandidatordningen (avsnitt 11). Kvar före en prövning som kärnserie: ägarens beslut om referensen
  enligt det som är känt vid d (R22 N-1), märkningen `backfill` på webben (N-2), priskontroll av nycklarna vid minimum
  (N-3), och osäkerheten i efterföljarregeln i 2026-02 – 2026-05 (förbehåll 5).

## 11. Rättningar efter granskningen R22 (spår X19)

Rättningsspår X19, körning 14, 2026-11-25, gren `auto14k/x19-rorlig-troskel`. Reglerna står i registret, posten
"2026-11-25 – X19". Q1-posten skrivs inte om.

| Tid (UTC) | Commit | Innehåll |
|---|---|---|
| 13:20 | `4fd3740` | Registerposten X19. Inga nya värden |
| 13:23 | `ab352a3` | Kod och syntetiska tester. Inga riktiga data |
| senare | denna commit | Omräkning, effekt och dokument |

Före registerposten var alla Q1-värden och R22:s mätningar kända. X19 läste dessutom de två namnens tavlor och
ratingar (belägget för namnbytena). Reglerna valdes alltså efter att värdena setts. Skälen är granskningens fynd om
reglernas brister.

### Vad som ändrades

| Fynd | Rättning |
|---|---|
| R22-1 | Versionen på månadsslut + 1 använder tavlor belagda till och med den dagen (`price_rolling._versions`). Den delade regeln i `vintages.monthly` och `arena_price.build` ändras inte (kärnserier och skyddade moduler), och det hör hemma i ett eget spår |
| R22-2 | `chatgpt-4o-latest` → `chatgpt-4o-latest-20240808` och `claude-opus-4-6-thinking` → `claude-opus-4-6-high` i `price_rolling.RENAMES`, med belägget i koden. Den normaliserade formen prövas också för det nya namnet, så att "Claude Opus 4.6 (High)" hittas efter bytet till visningsnamn. Avsnitt 1 rättat |
| R22-3 | Tröskeln är medianen över alla giltiga kandidater, inte den första. Nya kolumner `delta_from`, `delta_to`, `n_successors` och `threshold_spread` |
| R22-4 | Nivåkontrollen för ECI-varianten i avsnitt 7, och kolumnen `floor` i båda tabellerna |
| R22-5 | Förbehåll 5 redovisar R22:s mätning och osäkerheten efter X19 |

Noter från R22: N-5 (kolumnen `Date` i TheAgentCompany) står i avsnitt 8. N-1, N-2 och N-3 lämnas till ägaren.

### Effekt

Omräknat i spårets tabell med samma indata som Q1 (`arena_price._inputs()`, `price_capability._inputs()`). Med Q1:s
regler återskapar koden Q1:s spårtabell rad för rad (28, 33 och 39 rader).

| Serie | Rader (Q1 → X19) | Ändrade versioner | Senaste värdet per månad |
|---|---|---|---|
| `g2_price_rolling12_arena` | 28 → 27 | 2025-08 version 2025-09-03 (0,13125) finns inte längre. 2026-02 version 2026-04-02: 0,315 → 0,275. 2026-04: 1 → 1,125. 2026-05: 0,75 → 1,125 | ändrat i 4 av 22 månader: 2025-08 (0,13125 → 0,175), 2026-02, 2026-04 och 2026-05 |
| `g2_price_rolling6_arena` | 33 → 33 | inga | oförändrat. Referensen hittas nu direkt i 2025-02 (`chatgpt-4o-latest`) och 2026-09 – 2026-10 (`claude-opus-4-6-thinking`), med samma värden |
| `g2_price_frontier_arena` | 39 → 39 | inga | oförändrat |
| `g2_price_rolling12_eci` | 18 → 18 | inga | oförändrat |

Varje rättning för sig (L = 12; de andra serierna ändras inte av någon av dem):

- **Namnbytena** tar bort versionen 2025-09-03 för 2025-08. Referensen `chatgpt-4o-latest` hittas i b(m) 2025-08-04 som
  `chatgpt-4o-latest-20240808` (1 334,72). I tavlan 2025-08-29 saknas namnet, och medianen av sex kandidater med Δ från
  2025-07-28 – 2025-08-04 ger 1 335,21. Kandidaterna ligger inom 0,15 poäng, och värdet blir 0,175 som i version 1.
  Det stämmer med R22.
- **Medianen** ändrar 2025-08 version 2025-09-03 (0,13125 → 0,1375, utan namnbytena), 2026-02 version 2026-04-02,
  2026-04 och 2026-05.
- **Versionen på månadsslut + 1** ändrar inget värde. Tavlorna 2026-04-30 och 2026-09-30 är nu b(m) i första versionen
  för sin månad i alla tre Arena-serier, med samma värden. Det stämmer med R22. Därför skiljer sig X19:s kandidattrösklar
  för 2026-04 något från R22:s (`o3-2025-04-16` 1 433,73 mot 1 433,80 i tavlan 2026-04-29).

Kontroll av de ändrade versionerna. Kandidaternas trösklar är rating i b(m) + Δ (median av de 3 senaste gemensamma
tavlorna). Kontrollerat mot cachen, inte mot råfilerna. R22 fann cachen lika med råfilerna i alla tavlor.

| Version | b(m), referenstavla | Kandidaternas trösklar | Median | Billigaste kvalificerade | Värde |
|---|---|---|---|---|---|
| L = 12, 2026-02, 2026-04-02 | 2026-02-26 (bulk), 2025-02-27; r(m) `early-grok-3` | `deepseek-r1` 1 412,17; `gemini-2.0-flash-001` 1 403,94 (Δ 2025-07-28 – 08-04) | 1 408,05 | `grok-4-1-fast-reasoning` 1 408,32 (`xai/grok-4-1-fast-reasoning`), 0,20 / 0,50 | 0,275 |
| L = 12, 2026-04, 2026-05-01 | 2026-04-30, 2025-04-23; r(m) `gemini-2.5-pro-exp-03-25` | `o3-2025-04-16` 1 433,73; `chatgpt-4o-latest-20250326` 1 457,01; `grok-3-preview-02-24` 1 458,97; `gpt-4.5-preview-2025-02-27` 1 456,32 (Δ 2025-05-19 – 05-22) | 1 456,66 | `gemini-3-flash` 1 466,58 (`gemini/gemini-3-flash-preview`), 0,50 / 3,00 | 1,125 |
| L = 12, 2026-05, 2026-06-01 | 2026-05-27, 2025-05-22; r(m) `gemini-2.5-pro-preview-05-06` | `o3-2025-04-16` 1 426,71; `chatgpt-4o-latest-20250326` 1 445,03; `grok-3-preview-02-24` 1 446,91; `gpt-4.5-preview-2025-02-27` 1 447,91 (Δ 2025-07-28 – 08-04) | 1 445,97 | `gemini-3-flash` 1 466,15, 0,50 / 3,00 | 1,125 |
| L = 12, 2025-08, 2025-09-03 | 2025-08-29, 2024-08-28; r(m) `chatgpt-4o-latest` | sex kandidater 1 335,08 – 1 335,23 (Δ 2025-07-28 – 08-04) | 1 335,21 | `gemini-2.0-flash-001` 1 358,15, 0,10 / 0,40 | 0,175 (ingen ny version) |

**Alternativ till medianen** (R22 föreslog medianen eller en lucka när Δ är äldre än 90 dagar). Prövat efter
omräkningen: medianen bara när den senaste Δ-tavlan är äldre än 90 dagar ger exakt samma rader. Det beror på att alla
kandidater ger samma värde där Δ är färskare. En lucka i stället tar bort 8 av 27 rader för L = 12 (hela 2026-03 –
2026-05 och bulkversionerna för 2025-11 – 2026-02) och 2 av 33 för L = 6 (2025-09 och 2025-10). X19 valde medianen
utan åldersgräns, så att ingen gräns väljs i efterhand.

I 2026-04 och 2026-05 ligger den första kandidaten (`o3-2025-04-16`) 18 – 25 poäng under de tre andra, och Q1:s regel
tog just den. Medianen följer de tre andra. I 2026-02 ligger modellen vid minimum bara 0,26 poäng över medianen.

### Osäkerhet som finns kvar

- **Kandidaternas spridning.** Med den lägsta i stället för den högsta kandidattröskeln blir det senaste värdet ett annat i
  4 av 22 månader för L = 12: 2026-02 (0,275 mot 0,315), 2026-03 (1 mot 1,125), 2026-04 (1 mot 1,125) och 2026-05 (0,75
  mot 1,125). Medianen ger 0,275, 1,125, 1,125 och 1,125. För L = 6 ger alla kandidater samma värde i alla månader.
- **Δ:s ålder.** Den senaste Δ-tavlan är mer än 90 dagar äldre än b(m) i 8 av 13 versioner med efterföljare för L = 12
  (99 – 343 dagar) och i 2 av 4 för L = 6 (99 dagar). Experimentnamnen försvinner ur tavlorna efter 2025-08-04, så Δ
  kan inte bli färskare.
- **±5 poäng** på tröskeln (R22 N-4, efter X19): det senaste värdet per månad ändras i 3 av 22 månader för L = 12
  (+5: 2025-11 och 2026-02; −5: 2025-08) och i 7 av 28 för L = 6.
- **Inte prövat:** priserna för nycklarna vid minimum mot utvecklarnas prislistor (N-3), och vad kolumnen `Date` i
  TheAgentCompany betyder (N-5).

### Data

Spårets tabell (`data/` i worktree `x19-rorlig-troskel`) har de fyra serierna omräknade: 27 + 33 + 39 + 18 rader.
Datatesterna (`python -m ai_tracker.warehouse`) passerar. Q1:s spårtabell har de gamla raderna och ska inte slås ihop.
Slå ihop X19:s tabell med `--replace` för de fyra serierna, så att Q1:s rader inte blir kvar om de redan finns i basen.
