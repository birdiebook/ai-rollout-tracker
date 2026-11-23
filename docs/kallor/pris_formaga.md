# Pris vid fast förmåga (G2)

Fas 2, spår I6. Byggt 2026-11-23. Serien finns inte färdig hos någon källa, så den byggs av LiteLLM:s
prishistorik och Epoch AI:s förmågemått. Här beskrivs bara nivå och metod. Takt och halveringstid beräknas
enligt måttregistret i ett senare steg, inte här.

| Nyckel | Förmåga | Tröskel | Historik | `source` vid första laddning |
|---|---|---|---|---|
| `g2_price_at_capability` (registrerat huvudmått) | Epoch ECI, som hämtat | 141,16 (o1) | 2024-12 – | `backfill`, läcker |
| `g2_price_at_capability_gpqa` (variant) | Epochs egna GPQA Diamond-körningar | 0,767676 (o1, hög) | 2025-02 – | `backfill` (etiketten kommer från ramverket, tidsstämplarna är ärliga) |

Värde för månad m: det lägsta blandade priset, (3 × input + output) / 4 i USD per miljon tokens, bland
förstapartsmodeller vars förmåga är minst tröskeln, enligt prisfilen som den såg ut vid slutet av m. Bara hela
månader tas med. `known_from` = dagen efter månadens sista dag (`lag_days=1`, rättat i X1 2026-11-23: värdet bygger på commits
under hela sista dagen, så med `as_of`-konventionen att en dag betyder dagens slut är det känt först dagen efter). Bygg med
`python -m ai_tracker.observations g2_price_at_capability g2_price_at_capability_gpqa`.

Kod: `src/ai_tracker/sources/litellm_prices.py` (priser), `src/ai_tracker/sources/epoch_capability.py`
(förmåga), `src/ai_tracker/sources/model_map.py` (mappning och förstapartsregel) och
`src/ai_tracker/series/price_capability.py` (beräkning, tröskel och `SPECS`). Tester i
`tests/test_price_capability.py`, med fixturer och utan nät.

## Källor och licens

- **LiteLLM** `model_prices_and_context_window.json` (github.com/BerriAI/litellm). MIT för allt utanför
  `litellm/enterprise/`, vilket kontrollerades i `LICENSE` på `main` 2026-11-23.
- **Epoch AI** `benchmark_data.zip` (`eci_scores.csv`, `gpqa_diamond.csv`, `model_metadata.csv`). CC BY 4.0
  enligt README i ZIP-filen. Källhänvisning: "Epoch AI, 'Capabilities & benchmarking', epoch.ai/benchmarks".
- Serien är härledd ur de två källorna. Båda licenserna är kontrollerade, så `publish=True` gäller, med
  källhänvisning till Epoch AI och LiteLLM.

## Priser: LiteLLM:s git-historik

- Klonen är blobless (`--filter=blob:none`) och ligger i `data/raw/litellm/repo`, utanför den spårade koden
  (`data/` är gitignorerad). Klon och hämtning tar cirka 15 s. git går mot github.com med gits egen
  User-Agent. Epoch hämtas med `ai_tracker.http`.
- **Commits:** de som ändrat filen längs `main`:s first-parent-kedja. Det ger datumet då ändringen kom in på
  `main`, inte författardatumet i PR-grenen. Urval: den sista commiten varje vecka (W-SUN) och varje månad.
  Läget vid varje månadsslut blir då exakt. 184 ögonblicksbilder, 2023-09-07 – 2026-11-23.
- **known_from för ett pris** = datum (UTC) för den första urvalda ögonblicksbilden som innehåller det.
  Det är aldrig tidigare än den verkliga commiten, och alltså konservativt. Ett pris som syns först efter
  månadsslut räknas inte för den månaden (testat).
- **Poster:** `mode` chat eller responses (o3-pro och GPT-5 Pro finns bara som responses), med både in- och
  utpris > 0. Gratisnivåer räknas inte. Standardpriset gäller, så batch, priority, flex, cache och >200k-nivåer
  ignoreras. **Resonemangspris:** finns `output_cost_per_reasoning_token` används det högsta av det och
  `output_cost_per_token`. Epoch mäter förmågan med resonemang påslaget. Regeln påverkar bara
  Gemini 2.5 Flash preview (0,60 mot 3,50 USD) i den här historiken.

### Förstapartsregeln

Ett pris räknas bara från utvecklarens eget API: rätt `litellm_provider` **och** rätt nyckelprefix.
Prefixkontrollen behövs eftersom LiteLLM sätter utvecklarens provider även på vissa återförsäljarnycklar,
till exempel `azure/o3-mini-2025-01-31` och `openrouter/openai/o1-mini` med provider `openai`.

| Utvecklare | provider | Nyckel |
|---|---|---|
| OpenAI | `openai` | utan prefix |
| Anthropic | `anthropic` | utan prefix (inte `us/`, `fast/`) |
| Google | `gemini` | `gemini/` (Gemini API. Vertex räknas inte, så det finns en kanal per utvecklare) |
| xAI | `xai` | `xai/` |
| DeepSeek | `deepseek` | utan prefix eller `deepseek/` |
| Mistral, Moonshot, Z.ai, MiniMax, Meta | `mistral`, `moonshot`, `zai`, `minimax`, `meta` | eget prefix |
| Alibaba | `dashscope` | `dashscope/` (bara Qwen. DashScope säljer också DeepSeek, GLM och Kimi, och de räknas inte) |
| ByteDance | `volcengine` | `volcengine/` |

`-latest`-alias, regionala nycklar, snabbläge, contributor- och batchnivåer räknas aldrig. Moln och
återförsäljare (Azure, Bedrock, Vertex-partnermodeller, OpenRouter, Together, Fireworks, DeepInfra med flera)
räknas inte heller när de kör utvecklarens egen modell. **Följd:** öppna modeller som bara säljs av
tredje part saknar pris. Serien mäter därför förstapartspris, och nivån kan ligga över det billigaste
tillgängliga priset.

## Förmåga

- **ECI (huvudmått):** `eci_scores.csv`, ett värde per modell med Epochs releasedatum. En modell räknas
  från sitt releasedatum, men med det ECI-värde den har i dag.
- **GPQA Diamond (variant):** Epochs egna körningar. `known_from` = `Started at` + 7 dagar. En modells
  förmåga vid ett datum är den bästa körningen över resonemangsnivåer som var känd då. `model_metadata.csv`
  kopplar `Model version` till Epochs modellnamn. GPQA Diamond valdes för täckningen (342 körningar, flest
  Epoch-körda modeller). Kända svagheter: 198 frågor ger brus (standardfel cirka 0,03), benchmarken ligger nära
  taket (0,97), och de första körningarna har platshållardatumet 2025-01-27, så varianten börjar i februari 2025.
- **Pris per token, inte per uppgift.** En modell med hög resonemangsnivå använder fler tokens för samma
  uppgift. Måttet tar inte hänsyn till det, och det gör inte heller Epochs referensdata.

### Tröskeln (låst, se måttregistret)

`ECI_THRESHOLD = 141.16` är högsta ECI bland modeller släppta ≤ 2025-01-01 (o1) i data hämtad 2026-11-23.
`GPQA_THRESHOLD = 0.767676` är o1-2024-12-17 med hög resonemangsnivå (152/198), avrundat nedåt.
Konstanterna står i koden med hänvisning till `docs/mattregister.md`, "Ändringar 2026-11-23 – G2". Ett test
kontrollerar att registret och koden stämmer överens. Tröskeln räknas aldrig om.

**Känslighet:** flera modeller ligger inom 1 ECI-poäng från tröskeln, medan Epochs konfidensintervall är
ungefär ±3. Under tröskeln ligger Claude 3.7 Sonnet (141,03), DeepSeek-V3.1 (140,88), Gemini 2.5 Flash (jun
2025, 140,79), DeepSeek-R1 maj 2025 (140,73), Gemini 2.5 Flash (apr 2025, 140,69), o3-mini och Gemini 2.5 Pro
(maj 2025) (båda 140,63). Över tröskeln ligger Kimi K2 (141,27), Gemini 2.5 Flash (maj 2025, 141,57), Mistral
Medium 3.5 (141,58), Claude Sonnet 4 (141,84) och Gemini 2.5 Flash (sep 2025, 141,88). En omskattning av ECI
kan därför flytta modeller över eller under tröskeln, och då ändras historiska värden (`revision`). Det är ett
skäl till att varianterna redovisas sida vid sida.

## Mappning LiteLLM ↔ Epoch

Den explicita tabellen `MODEL_MAP` i `model_map.py` har 123 Epoch-modeller och 181 nycklar. Den byggdes
genom att Epochs versions-id (API-namn som `o3-2025-04-16_high`) matchades mot förstapartsnycklar, och sedan
granskades för hand. Den täcker alla modeller med ECI ≥ 128 eller en GPQA-körning ≥ 0,70 som har en
förstapartsnyckel, så att omskattningar nära tröskeln täcks.

- **Rullande alias** (`deepseek-chat`, `deepseek-reasoner`) mappas till alla modeller de har pekat på.
  Vid ett datum får nyckeln förmågan hos den senast släppta mappade modellen, så före den första mappade
  releasen har den ingen förmåga. Bara nycklar i `ROLLING_ALIASES` får peka på flera modeller (testat).
- **Uppdateringar på plats** där det är osäkert vilken modell nyckeln serverar mappas bara till den modell
  nyckeln säkert har serverat.

**Täckning** (data 2026-11-23): ECI-varianten har 93 av 119 modeller över tröskeln mappade, GPQA-varianten 79
av 107. Alla mappade nycklar finns i prishistoriken.

Omappade modeller över tröskeln, och varför:

| Modeller | Skäl |
|---|---|
| Alibaba: Qwen3-Max, Qwen3-235B-A22B-Thinking (jul 2025), Qwen3.5 397B-A17B, Qwen 3.5 Plus/Flash, Qwen3.5-35B-A3B, Qwen3.5-9B, Qwen 3.6 Plus/Flash/Max (preview)/35B-A3B/27B, Qwen3.7-Plus, Qwen3.7 Flash, Qwen 3.8 27B, Qwen3.8 Max (0902) | DashScope-listan i LiteLLM saknar versionerade nycklar för dem. Bara rörliga alias (`qwen-plus`, `qwen-max`) finns, och de mappas inte |
| Gemma 4 26B A4B, Gemma 4 31B IT | öppna vikter, inget betalpris i Gemini API |
| Muse Spark (apr 2026) | ingen `meta/`-nyckel (först 1.1 finns) |
| Nemotron 3 Ultra, Inkling, Inkling-Small, Beam 1.0, Muse Spark Open | öppna vikter utan förstaparts-API i LiteLLM, bara återförsäljare |
| DeepSeek V4 Flash 0731, V4 Pro 0813, V4.1 Flash, V4.1 Flash 1017 | troligen uppdateringar på plats av `deepseek-v4-flash`, `deepseek-v4-pro` och `deepseek-flash`. Det är inte verifierat. De mappade föregångarna ligger redan över tröskeln, så nycklarna räknas ändå |
| Doubao-Seed-1.6, Doubao-Seed-2.0 Pro/Lite, Doubao Seed Evolving (bara GPQA) | ingen `volcengine/`-nyckel för de versionerna |
| GPT-5.5 Instant (bara GPQA) | bara alias (`chat-latest`) |

Förstapartsnycklar med mycket trafik som saknar Epoch-mått och därför inte kan räknas:
`gpt-6.2-sol`, Codex-modellerna (`gpt-5.1-codex` … `gpt-5.3-codex`), `claude-mythos-*`, `xai/grok-4-1-fast-*`,
`xai/grok-code-fast-1`, `moonshot/kimi-k2-0905-preview`, `minimax/MiniMax-M2*`, `dashscope/qwen3.8-flash`,
`meta/muse-ember-1.0` och `zai/glm-5-code`.

## Läckage och förbehåll

1. **ECI-varianten läcker.** Både tröskeln och modellernas ECI är dagens skattningar. Vad som gick att veta
   2025 kan ha varit annorlunda. Vilka modeller som alls finns i Epochs ECI-urval är också dagens kunskap.
   Hela historiken får därför `source="backfill"` och används bara som beskrivning, enligt registret. Varje ny
   hämtning där ECI har omskattats ger `revision` med hämtdatum, och de egna ögonblicksbilderna blir ärliga
   versioner.
2. **GPQA-varianten har ärliga tidsstämplar för förmågan** (körningens start + 7 dagar) och för priserna
   (commit-datum). Den kvarvarande risken: Epoch kan köra om eller ta bort körningar. Mappningen är också
   gjord i dag, men den avgör bara vilken nyckel som hör till vilken modell.
3. **LiteLLM släpar och har fel.** Exempel: `deepseek-reasoner` fick DeepSeeks pris 0,28/0,42 USD (från
   september 2025) först 2026-01-16, i båda namnformerna, och formerna hade olika priser fram till dess. `gemini/gemini-1.5-pro-002`
   ligger kvar på 3,50/10,50 USD, trots att Google sänkte priset till 1,25/5 i oktober 2024. Alla
   `xai/grok-4*` sattes till 1,25/2,50 USD i en och samma commit 2026-08-30, vilket inte är verifierat mot xAI.
   Fördröjningar gör serien konservativ. Ett felaktigt lågt pris skulle däremot slå direkt på minimivärdet,
   så modellen som sätter minimum loggas per månad (`table()` ger `key`, `model` och `n_qualifying`).
4. **Kampanjpriser räknas** när LiteLLM listar dem som standardpris. Ett exempel är DeepSeek-V3:s
   introduktionspris 0,14/0,28 USD i december 2024 och januari 2025.
5. Månadens värde är **läget vid månadsslut**, inte ett medelvärde över månaden. Ett mått på fronten
   (bästa pris) mäts vid en tidpunkt.

## Nivåkontroll mot Epochs frysta prisdata

Kontrollen gäller bara nivån (samma storleksordning, samma modeller vid fronten), inte trender. Epochs
`lowest_price_models_data.csv` (fryst 2025-11-20, sista release 2025-02-05) har som högsta tröskel
Claude 3.5 Sonnet (jun 2024). Den är lägre än vår, så samma metod kördes med en kontrolltröskel på den nivån
(ECI 130,00, alltså Claude 3.5 Sonnet, och GPQA 0,540 i Epochs körning). Kontrolltröskeln används bara här.
Epoch använder också 3:1-blandning.

| Modell vid fronten (Epoch, GPQA ≥ Claude 3.5 Sonnet) | Epoch USD | Vår kontrollkörning USD | Kommentar |
|---|---|---|---|
| Claude 3.5 Sonnet (2024-06) | 6,00 | 6,00 (2024-06 – 08) | samma |
| Gemini 1.5 Pro 002 (2024-09) | 2,19 | 5,25 (2024-09 – 11) | samma modell. LiteLLM:s `gemini/`-pris uppdaterades aldrig efter Googles prissänkning (punkt 3) |
| DeepSeek-V3 (2024-12) | 0,48 | 0,175 (2024-12 – 2025-01) | samma modell. Vi får kampanjpriset, Epoch listpriset 0,27/1,10 |
| Gemini 2.0 Flash (2025-02) | 0,175 | 0,175 (2025-02) | samma |

Utfall: samma fyra modeller sätter fronten, och nivåerna ligger i samma storleksordning (skillnad högst
cirka faktor 2,7, med kända orsaker). Epochs lista har dessutom tredjepartspriser (Phi 4, Llama 3.1 405B),
som vår förstapartsregel utesluter. Med registrets tröskel (o1) överlappar serierna inte. Epochs data går
inte så högt, och o1 finns inte i Epochs prisfiler.
