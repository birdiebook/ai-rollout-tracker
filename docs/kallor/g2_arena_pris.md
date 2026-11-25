# Pris vid fast Arena-förmåga (G2), spår G2A

Steg 2, spår G2A, 2026-11-24. Förslaget kommer från spår G12 (`docs/kallor/g1g2_nya.md`, "Pris vid fast
Arena-förmåga"). Serien ska ge G2 ett pris vid fast förmåga med mer än två års ärligt daterad historik. Förmågan
mäts relativt en fast referensmodell i samma Arena-tavla, så att skalbrott (Elo/BT, stilkontroll, omviktning,
förankring) tar ut varandra. **Inga takter, halveringstider eller trender beräknas i spåret.** Serien granskas
oberoende innan den registreras.

## 1. Referensregel (låst 2026-11-24, före beräkning av seriens värden)

Regeln nedan skrevs och committades innan något månadsvärde beräknades. Innan dess kontrollerades bara metadata:
att referensmodellerna finns i tavlorna och vilka namnformer de har. Inga priser eller trösklar tittades på.

### Tavlor

- Arena `text`, kategori `overall`, alla publicerade tavlor enligt `arena.subset_boards("text")`: Space-filer,
  datasetets titlade commits och bulkuppladdningen, med belägg och `source` enligt `docs/kallor/g1g2_nya.md`.
- **Bara Bradley–Terry-eran:** tavlor publicerade från 2024-01-09. Första månaden är 2024-01.
- Månad m använder den senaste tavlan publicerad ≤ månadens slut bland dem som är belagda vid versionens datum.
  Versioner och datum följer regeln i `sources/vintages.py`. Första versionen har `known_from` = månadsslut + 1 dag
  och tavlor med belägg ≤ månadsslut + 1 dag. En tavla som publicerades ≤ månadsslut men beläggs senare ger en ny
  version på beläggets datum, om värdet ändras.
- **Ändrat 2026-11-25** (registerposten 2026-11-25 "Integration 14: månadsgränsen i arena_price (R23-2)"). Tidigare
  räknade första versionen bara belägg till och med månadsslut. En tavla från månadens sista dag som belades dagen
  efter kom då aldrig in i sin månad. Ombyggnaden ändrade inget värde, ingen `known_from` och ingen `source`. Bara
  diagnostiken ändrades: 2026-04 och 2026-09 sätts nu av tavlorna 2026-04-30 och 2026-09-30 i stället för 2026-04-29
  och 2026-09-25, med samma nyckel vid minimum.

### Referens och tröskel

Tröskeln i tavla b är referensens rating **i samma tavla b**. En modell kvalificerar om dess rating i b är ≥
tröskeln. Gränsen är inklusiv, så referensen själv kvalificerar.

| Variant | Nyckel | Referens r0 | Efterföljare, i ordning |
|---|---|---|---|
| A | `g2_price_at_arena_capability` | `gpt-4-0314` (GPT-4 vid lanseringen, mars 2023) | `gpt-4-0613`, `gpt-4-1106-preview` |
| B | `g2_price_at_arena_capability_4o` | `gpt-4o-2024-05-13` (etta i tavlan 2024-06-11) | `gpt-4o-2024-08-06`, `gpt-4-turbo-2024-04-09` |

- **Namnformer:** API-namn till och med 2026-10-19, visningsnamn från 2026-10-20. Referenserna matchas på båda:
  `gpt-4-0314` / "GPT-4 (0314)", `gpt-4-0613` / "GPT-4 (0613)", `gpt-4-1106-preview` / "GPT-4 Turbo Preview (1106)",
  `gpt-4o-2024-05-13` / "GPT-4o (2024-05-13)", `gpt-4o-2024-08-06` / "GPT-4o (2024-08-06)" och
  `gpt-4-turbo-2024-04-09` / "GPT-4 Turbo (2024-04-09)". Finns båda formerna i samma tavla, används API-namnet.
- **Efterföljare** väljs efter metadata, inte efter utfall: OpenAI-ögonblicksbilder nära referensen i tid och med
  lång närvaro i tavlorna. De används bara om r0 saknas i en tavla. I kontrollen 2026-11-24 fanns båda
  referenserna i varje BT-tavla från sin första förekomst (r0 för A från 2024-01-09, för B från 2024-05-15; 252 BT-tavlor till och med 2026-11-22). Kedjan
  är alltså en regel för framtiden, och historiken använder den inte.
- **Överlappsregel:** saknas r0 i tavla b, används den första efterföljaren s i listan som finns i b och som har
  minst 3 tidigare tavlor (publicerade före b och belagda vid versionens datum) där både r0 och s finns. Tröskeln
  blir rating_b(s) + Δ, där Δ = medianen av rating(r0) − rating(s) i de 3 senaste sådana tavlorna. Δ beräknas
  alltså bara ur tidigare tavlor, aldrig ur senare. Uppfyller ingen efterföljare villkoret, får tavlan ingen
  tröskel, och månaden får inget värde från den tavlan.
- Referenserna och kedjorna ändras inte i efterhand. Om både r0 och kedjan försvinner, tar serien slut tills
  registret beslutar om en ny kedja (med datum och motivering).

### Förmåga per prissatt nyckel

- Varje Arena-namn kopplas till en eller flera LiteLLM-nycklar i den handgranskade tabellen
  `src/ai_tracker/sources/arena_map.py` (avsnitt 3). Bara förstapartsnycklar för modellens utvecklare räknas,
  med regeln i `model_map.is_first_party`.
- **Bästa variant per prissatt modell:** en nyckel får den högsta ratingen bland de Arena-namn som är kopplade
  till den och finns i tavlan. Exempel: resonemangsnivåer som `o3-mini` och `o3-mini-high` säljs under samma
  nyckel och samma pris per token. Samma regel som I6:s GPQA-variant.
- **Rullande alias** (`deepseek-chat`, `deepseek-reasoner`, och från rättningen X5 Geminis stabila
  `gemini/gemini-1.5-flash` och `gemini/gemini-1.5-pro`, avsnitt 7) kopplas till varje modellversion de har serverat,
  med datum från när aliaset började peka på den. Vid månadsslut räknas bara den version som aliaset då
  serverade. Finns den inte i tavlan, har nyckeln ingen förmåga den månaden. Föregångarens rating används inte.
- Alias som byter modell utan dokumenterade datum (till exempel `gpt-4o`, `chatgpt-4o-latest`, `-latest`,
  `qwen-plus`, `qwen-max`, `mistral-medium`) kopplas inte.

### Pris och värde

- Pris = LiteLLM:s prisfil vid månadsslut (senaste urvalda commit på `main` med datum ≤ månadsslut), blandat
  3 input : 1 output, USD per miljon tokens. Samma regler för poster och resonemangspris som
  `g2_price_at_capability` (`docs/kallor/pris_formaga.md`).
- Värde för månad m = lägsta blandade pris bland kvalificerade nycklar.
- `known_from` = det senare av tavlans versionsdatum och prisets `known_from` (månadsslut + 1 dag). Priset vid
  månadsslut är fast, eftersom git-historiken inte ändras. Senare versioner av en månad uppstår bara av senare
  belagda tavlor.
- `source` = `backfill` om tavlan bara finns i datasetets bulkuppladdning (belägg 2026-04-02), annars `release`.
- Båda varianterna lagras. Ingen av dem väljs efter hur serierna ser ut.

## 2. Ändring efter första bygget (2026-11-24, före all analys)

**Pensionerade modeller räknas inte.** Det första bygget följde avsnitt 1 exakt. Kontrollen av vilken modell som
satte minimum (en kontroll av datakorrekthet, inte av förlopp) visade att `gemini/gemini-1.5-flash-001` satte
minimum i variant A från 2024-09 till 2026-02, alltså långt efter att Google pensionerat modellen 2025-05-24.
LiteLLM tar inte bort poster när modeller pensioneras, men posten får fältet `deprecation_date`, oftast i förväg
(för 1.5 Flash 001 fanns datumet i filen från senast 2025-03-08). Regeln blev därför:

- En nyckel räknas inte för månad m om LiteLLM-filen vid månadsslut anger `deprecation_date` ≤ månadsslut.
  Bara filen vid månadsslut används, så ett datum som LiteLLM lade till i efterhand påverkar inte tidigare månader
  (inget läckage). Datumen läses med `litellm_prices.deprecations()` (cache `deprecations_v1.parquet`).
- Referensregeln i avsnitt 1 är oförändrad. Ändringen gäller båda varianterna.
- Effekt jämfört med första bygget, redovisad för granskningen: i variant A fick 2025-05 – 2025-12 en annan modell
  vid minimum (Gemini 1.5 Flash 002 och 2.0 Flash-Lite Preview, samma nivå). I båda varianterna fick 2026-01 –
  2026-02 GPT-5 nano (0,1375 i stället för 0,13125 USD) och 2026-08 GPT-5 nano i stället för Mistral Small 3.2
  (pensionerad 2026-07-31; 0,1375 i stället för 0,09 USD). Övriga månader är oförändrade.
- Regeln skulle också passa `g2_price_at_capability*`, men de serierna ändras inte i det här spåret. Regeln är
  registrerad som ändring 2026-11-24 i `docs/mattregister.md` och gäller bara Arena-prisserierna. Om I6-serierna ska
  följa den är en öppen registerfråga (rättning X5).
- LiteLLM anger inte alltid pensionering. En pensionerad modell utan `deprecation_date` räknas fortfarande.

## 3. Namnkoppling Arena → LiteLLM

Tabellen `src/ai_tracker/sources/arena_map.py` är handgranskad. Varje rad har modell, nycklar och belägg: samma
modell, samma version (daterad ögonblicksbild) och samma datum. Kontrollen `arena_map.problems()` körs i testerna.
Den kräver förstapartsnycklar (`model_map.is_first_party`), att varje namn bara finns en gång, att inga rullande
alias finns bland de fasta nycklarna och att inget namn både är kopplat och listat som okopplat.

- **Två namnformer:** båda formerna står i samma rad, till exempel `gpt-5-high` och "GPT-5 (High)".
- **Resonemangsnivåer** (`-high`, `-thinking-32k`, "(Max)", "(xHigh)") kopplas till modellens nyckel. Nyckeln får
  den bästa varianten i tavlan.
- **Undantag från regeln att `-exp-` inte kopplas:** `gemini-2.5-pro-exp-03-25` kopplas till
  `gemini/gemini-2.5-pro-preview-03-25`, eftersom Google anger att det är samma modell (R8, stickprov 17).
- **Namnbyten i Arena**, belagda med tavlorna (inget överlapp): `gpt-4-turbo` (2024-01-09 – 01-25) blev
  `gpt-4-1106-preview` (från 2024-02-02), `gemini-1.5-{pro,flash}-api-0514` (till 2024-10-15) blev `-001` (från
  2024-10-23), `gemini-2.0-flash-lite-preview` blev `-02-05` och `gemini-2.0-flash` blev `-001`.
- **DeepSeeks rullande alias** (`deepseek-chat`, `deepseek-reasoner`, `deepseek-coder`) kopplas per version med
  startdatum från DeepSeeks versionsnyheter. `deepseek-chat`: V2-0628 2024-06-28, V2.5 2024-09-05, V2.5-1210
  2024-12-10, V3 2024-12-26, V3-0324 2025-03-25, V3.1 2025-08-21, V3.1-Terminus 2025-09-22, V3.2-Exp 2025-09-29,
  V3.2 2025-12-01. `deepseek-reasoner`: R1 2025-01-20, R1-0528 2025-05-28 och därefter samma V3.x-versioner med
  thinking. `deepseek-coder`: Coder-V2-0724 2024-07-24 och V2.5 2024-09-05 – 2024-12-09. Efter V4 (första
  Arena-tavla 2026-04-23) är det inte belagt vad aliasen serverar. LiteLLM anger att de pensioneras 2026-07-24 med
  `deepseek-v4-flash` som efterföljare. Aliasen räknas därför inte från 2026-04-23. Datumen före 2026 är från
  DeepSeeks versionsnyheter (api-docs.deepseek.com, blockerad i sandlådan, så de kunde inte läsas på nytt i dag).
  V2-0628 och Coder-V2-0724 dateras med datumet i versionsnamnet.
- **Geminis stabila alias** (X5, R-5) behandlas som DeepSeeks: `gemini/gemini-1.5-flash` och
  `gemini/gemini-1.5-pro` räknas som `-001` från 2024-05-24 till och med 2024-09-23, och inte därefter (avsnitt 7).
- **Inte kopplade:** alias som byter modell (`chatgpt-4o-latest*`, `gpt-5-chat`, `*-chat-latest`,
  `gpt-5.5-instant`, `gpt-4o`, `qwen-max`, `qwen-plus`, `mistral-medium`), Geminis
  experimentmodeller (gratis i AI Studio, och LiteLLM:s pris är inte Googles), Gemma (öppna vikter, LiteLLM:s
  `gemini/gemini-gemma-2-*`-pris har Vertex som källa), DeepSeeks `deepseek/deepseek-v3`, `-r1` och `-v3.2` (inga
  id:n i DeepSeeks API, och aliasen täcker dem) samt förhandsversioner vars släppta identitet inte är belagd.

### Täckning (data 2026-11-24)

Ett namn är kvalificerat om det någon gång har haft en rating ≥ referensen i en BT-tavla.

| | Variant A (gpt-4-0314) | Variant B (gpt-4o-2024-05-13) |
|---|---|---|
| Kvalificerade API-namn (tavlor före 2026-10-20) | 406 | 317 |
| varav kopplade | 205 (50 %) | 181 (57 %) |
| Kvalificerade namn totalt, med visningsnamn | 709 | 551 |
| varav kopplade | 353 | 308 |
| Median av andelen kopplade bland kvalificerade per tavla, 2024 / 2025 / 2026 | 0,46 / 0,38 / 0,49 | 0,44 / 0,47 / 0,56 |

G12 fann 102 av 406 API-namn med exakt namnmatchning. Den handgranskade tabellen kopplar 205. Inga kvalificerade
namn är ogranskade. Ett nytt Arena-namn räknas inte förrän det är granskat, och `arena_price.coverage()` visar
det som `unreviewed`.

Okopplade kvalificerade namn per skäl (variant A, alla namnformer; hela listan finns i `arena_map.UNMAPPED`):

| Skäl | Antal | Exempel |
|---|---|---|
| `open_weights`: öppna vikter utan förstapartspris | 121 | Llama 3.x/4, Nemotron, OLMo/Tulu/Molmo, Gemma, gpt-oss, Qwen öppna modeller, Athene, Phi-4, INTELLECT-3, Inkling |
| `developer_not_first_party`: utvecklarens API finns inte i förstapartsregeln | 110 | Amazon Nova (Bedrock), Cohere Command, AI21 Jamba, Reka, 01.AI Yi, Tencent Hunyuan, Baidu ERNIE, StepFun, Xiaomi MiMo, Meituan LongCat, Ant Ling/Ring, IBM Granite, Upstage Solar, Inception Mercury, Arcee Trinity, Microsoft MAI |
| `no_key`: utvecklaren finns i regeln men LiteLLM saknar nyckel för versionen | 59 | Qwen-Max/Qwen2.5-Max/Qwen3-Max och 3.5–3.7-modellerna, GLM-4/4-Plus/4.6V/4.7-Flash, Grok 2 (aug 2024), Grok 4.1, MiniMax-M1/M2.7, Mistral Small 2501/2503, Muse Spark/Glimmer, Dola Seed 2.0, Gemini 1.5 Flash-8B |
| `experimental`: experiment-, konsument- eller anonyma testnamn | 33 | Gemini `-exp-`, Bard, Gemini Advanced, `amazon-nova-experimental-chat-*`, `early-grok-3`, `late-june-chatbot`, `gpt-5-old` |
| `identity_uncertain`: förhandsversion eller uppdatering utan belagd identitet | 17 | Grok 3 Preview (02-24), Grok 4.20 Beta 1, DeepSeek V4 high-preview/20260813/V4.1, MiniMax-M2.1 Preview, Qwen3.7-Max-Preview, Gemini 1.5 Pro 0409-preview |
| `alias_drifts`: ChatGPT- och chat-latest-alias | 16 | `chatgpt-4o-latest-*`, GPT-5 Chat, GPT-5.2/5.3 Chat, GPT-5.5 Instant |

**Följd:** serierna mäter förstapartspris. Billigare tredjepartspriser för öppna modeller och utvecklare utanför
regeln (till exempel Cohere och Amazon) ingår inte. Den begränsningen påverkar variant A mer än B, eftersom fler
öppna modeller når GPT-4-0314-nivån.

## 4. Serier

| Nyckel | Månader | Rader | `source` |
|---|---|---|---|
| `g2_price_at_arena_capability` (A) | 2024-01 – 2026-10 | 34 | `release` |
| `g2_price_at_arena_capability_4o` (B) | 2024-05 – 2026-10 | 30 | `release` |

Efter X5 ändrades fyra värden (avsnitt 7): A 2024-06 6,00 → 0,525 och 2024-08 0,175 → 0,13125, B 2024-10 och
2024-11 5,25 → 2,1875. `known_from` är oförändrat.

Bygg med `python -m ai_tracker.observations g2_price_at_arena_capability g2_price_at_arena_capability_4o` (Arena
cirka 150 s kall, LiteLLM cirka 35 s kall). Kod: `src/ai_tracker/series/arena_price.py` (tröskel, versioner,
`coverage()`), `src/ai_tracker/sources/arena_map.py` (koppling), `litellm_prices.deprecations()`. Tester:
`tests/test_arena_price.py` (fixturer, inget nät).

- **known_from:** det senare av tavlans versionsdatum (regeln i `vintages.py`, belägg = Space-commit,
  dataset-commit eller bulkuppladdningen 2026-04-02) och månadsslut + 1 dag för priset. Alla rader i dag är
  första versioner med `known_from` = månadsslut + 1 dag. Tavlorna från bulkuppladdningen (2025-08-07 –
  2026-03-31) ändrade inget månadsvärde, så det finns inga `backfill`-rader.
- **Mätglapp 2025-09 – 2026-03:** den kända tavlan vid de månadsskiftena är 2025-08-29 (se `g1g2_nya.md`).
  Modeller som släpptes efter det kan inte kvalificera de månaderna, även om de prissattes.
- **Referensen finns i varje BT-tavla.** Efterföljarkedjan har inte använts.
- **Licens:** LiteLLM (MIT) och Arena-datasetet (CC BY 4.0). Härledda siffror med källhänvisning till LMArena
  och LiteLLM: `publish=True`.

### Nivåkontroll (vilken modell sätter minimum, inte förlopp)

| Period | A: modell vid minimum | B: modell vid minimum |
|---|---|---|
| 2024-01 – 02 | GPT-4 Turbo Preview (1106, 0125), 15 USD | – |
| 2024-03 – 05 | Claude 3 Sonnet, 6 USD | GPT-4o (2024-05-13), 7,50 USD (bara referensen kvalificerar 2024-05 – 08) |
| 2024-06 | Gemini 1.5 Flash via stabila aliaset, 0,525 USD (lanseringspris; före X5 6 USD) | som ovan |
| 2024-07 | DeepSeek V2-0628 (`deepseek-chat`), 0,175 USD | som ovan |
| 2024-08 | Gemini 1.5 Flash via aliaset, 0,13125 USD (prisrättning från 2024-08-12; före X5 0,175) | som ovan |
| 2024-09 – 2025-04 | Gemini 1.5 Flash 001, 0,13125 USD | o1-mini 5,25 (2024-09), Gemini 1.5 Pro 002 2,1875 (2024-10 – 11, prisrättning; före X5 5,25), DeepSeek-V3 (kampanjpris) 0,175 (2024-12 – 2025-01), från 2025-02 Gemini 2.0 Flash-Lite Preview 0,13125 USD |
| 2025-05 – 2025-12 | Gemini 1.5 Flash 002, sedan 2.0 Flash-Lite Preview, 0,13125 USD | Gemini 2.0 Flash-Lite Preview, 0,13125 USD |
| 2026-01 – 02 | GPT-5 nano (high), 0,1375 USD | samma |
| 2026-03 – 07 | Mistral Small 3.2 (2506), 0,09 USD | samma |
| 2026-08 – 10 | GPT-5 nano (high), 0,1375 USD | samma |

Priserna kontrollerades mot utvecklarnas prissidor i rättningen X5 (avsnitt 7.3). LiteLLM:s `source` är bara en
länk och ingen kontroll. **A och B har samma värden från 2025-02**, eftersom samma billiga modeller klarar båda
trösklarna.

**Tröskeln binder inte från 2024-07 (A) och 2025-02 (B).** Nivåkontroll utan tröskel (lägsta pris bland alla
kopplade och prissatta modeller i tavlan, data 2026-11-24 efter X5): värdet skiljer sig från seriens bara 2024-03 –
06 i A och 2024-05 – 2025-01 i B. Därefter mäter serierna golvet i förstapartsprislistornas billigaste nivå
("flash", "nano", "small"), inte priset vid en fast förmåga. Modellen vid minimum ligger 40–130 poäng över
tröskeln i A och cirka 20–40 poäng i B.

**Arenas osäkerhetsintervall används inte.** Tröskeln jämför punktskattningar (`rating`), inte `rating_lower` och
`rating_upper`. I A 2024-03 ligger Claude 3 Haiku 5,6 poäng under tröskeln, väl inom intervallet.

## 5. Förslag till kärnserie (för granskning och registrering)

**Underkänt i granskningen R8** (`docs/granskning/r8_g2_arena.md`). Ingen av varianterna är kärnserie. Förslaget
nedan står kvar som det skrevs. Läget efter rättningen X5 finns i avsnitt 7.

**Variant A (`g2_price_at_arena_capability`) föreslås som kärnserie**, och B redovisas som variant. Skälen gäller
datering och täckning, inte serieförloppet:

- **Datering:** A har ärligt daterade värden från 2024-01 (34 månader i dag), B från 2024-05 (30 månader).
  Referensen i A finns i varje BT-tavla från den första (2024-01-09). B:s referens kom 2024-05-15, och de första
  fyra månaderna kvalificerar bara referensen själv.
- **Täckning:** B har något högre andel kopplade namn (57 % mot 50 % av API-namnen). A:s lägre tröskel släpper in
  fler öppna modeller och utvecklare utanför förstapartsregeln, som inte kan prissättas. Skillnaden i täckning är
  mindre än skillnaden i historik, och båda följer samma regler.
- Om granskningen hellre vill ha högre täckning än längre historik är B alternativet. Den ska då ersätta A och
  inte läggas till, eftersom det är samma företeelse.

## 6. Kända begränsningar

1. **Förstapartsregeln** utesluter öppna modeller som bara säljs av tredje part och utvecklare utanför regeln
   (avsnitt 3). Nivån kan därför ligga över det billigaste tillgängliga priset.
2. **LiteLLM släpar och har fel** (se `pris_formaga.md`, punkt 3). Exempel: `deepseek-chat` stod på 0,60/1,70 USD
   i LiteLLM hösten 2025. Alla `xai/grok-4*` sattes till samma pris i en commit 2026-08-30. Pensionering syns
   bara när LiteLLM anger `deprecation_date` (avsnitt 2).
3. **Arena-rating är ett mått på chattpreferens**, med kända skalbrott. Tröskeln relativt referensen i samma tavla
   tar ut förankring och skalförskjutning, men inte omviktningar som ändrar avståndet mellan modeller
   (2025-05-16 och 2025-07-23).
4. **Mätglappet 2025-09 – 2026-03** (avsnitt 4).
5. **Kopplingen är gjord i dag.** Den avgör bara vilken nyckel som hör till vilket namn, och den använder inte
   priser eller ratingar. DeepSeeks datum kunde inte läsas på nytt i sandlådan.
6. **Pris per token, inte per uppgift.** Resonemangsnivåer som "(Max)" använder fler tokens.

## 7. Rättningar efter granskning R8 (spår X5, 2026-11-24)

Rättningarna R-1 – R-5, R-7 och R-8 från `docs/granskning/r8_g2_arena.md`. Ingen ny kärnserie registreras. Tester:
`tests/test_x5_arena_ratt.py` (fixturer, inget nät). Det tidigare strikta xfail-testet i `tests/test_r8_g2_arena.py`
passerar nu.

### 7.1 R-1: omskrivna Arena-tavlor

En tavla har nu en version per commit som ändrade dess rader, och varje version dateras till sin commit (regeln i
`docs/kallor/g1g2_nya.md`, "Omskrivna tavlor"). Utöver omladdningen 2026-07-07 (som inte ändrade något) hittades en
otitlad omskrivning 2026-07-29 som tog bort variantrader ur sex `text`-tavlor. **Effekt på A och B: ingen.** Ingen av
de ändrade tavlorna var den senaste vid ett månadsslut. Effekten på `g1_arena_*` är också noll.

### 7.2 R-2: daterade prisrättningar

`arena_price.PRICE_CORRECTIONS`. En rättning ersätter LiteLLM:s pris för en (nyckel, leverantör) bara i
ögonblicksbilder daterade från det senare av datumet då priset ändrades och datumet då belägget publicerades, och
bara så länge LiteLLM fortfarande visar det gamla priset. Inget bakdateras.

| Nycklar | Gammalt (LiteLLM) | Nytt | Gäller från | Belägg |
|---|---|---|---|---|
| `gemini/gemini-1.5-pro-002`, `gemini/gemini-1.5-pro-001` | 3,50 / 10,50 | 1,25 / 5,00 | 2024-10-01 (publicerat 2024-09-24) | Googles inlägg "Updated production-ready Gemini models, reduced 1.5 Pro pricing, increased rate limits, and more" (developers.googleblog.com, 2024-09-24). Nivån är kontrollerad på Googles Vertex-prislista (cloud.google.com, läst 2026-11-24): 0,0003125 / 0,00125 USD per 1 000 tecken vid ≤ 128k, cirka 4 tecken per token |
| `gemini/gemini-1.5-flash` (stabila aliaset), `gemini/gemini-1.5-flash-001` | 0,35 / 1,05 | 0,075 / 0,30 | 2024-08-12 (publicerat 2024-08-08) | Googles inlägg "Gemini 1.5 Flash price drop with tuning rollout complete, and more" (2024-08-08). Nivån finns på Vertex-prislistan (0,00001875 / 0,000075 USD per 1 000 tecken), och LiteLLM har själv den från 2024-09-15 (R8 A-2b) |

- **Belägg:** URL, läsdatum och SHA-256 av det citerade avsnittet står i `arena_price.PRICE_EVIDENCE`. Själva texten
  finns bara i `data/raw/price_checks/2026-11-24/quotes.json`.
- **Begränsning:** Googles inlägg (developers.googleblog.com), Gemini API-dokumentationen (ai.google.dev), forumet
  (discuss.ai.google.dev) och Vertex-dokumentationen (docs.cloud.google.com) nekas av proxyn. Titel och datum för
  inläggen är därför tagna ur sökindex och inte lästa på sidan. Vertex-prislistan visar dagens pris och inte när det
  började gälla.
- **Utpriset för 1.5 Pro:** inlägget uppges i en forumtråd visa 2,50 USD för utdata, medan API-prislistan visade
  5,00. Inläggets egen uppgift om en sänkning med 52 % för utdata (10,50 → 5,04) och Vertex-listan ger 5,00, som
  används. Värdet blir 2,1875 i stället för 5,25.
- **Inte rättat:** `gemini/gemini-1.5-pro` (aliaset) stod på 0,35 / 1,05 i LiteLLM 2024-06-21 – 06-30, alltså
  Flash-priset. LiteLLM rättade det själv 2024-07-06. Det ger samma blandade pris som Flash-aliaset 2024-06 (0,525),
  så månadens värde påverkas inte, och Flash vinner när priserna är lika.

### 7.3 R-3: kontroll av varje pris vid minimum

`arena_price.PRICE_CHECKS`, kontrollerat 2026-11-24. `table()` har kolumnen `price_check` per rad.

| Nyckel (månader vid minimum i A/B) | Pris | Status | Kontroll |
|---|---|---|---|
| `gpt-4-1106-preview`, `gpt-4-0125-preview` (A 2024-01 – 02) | 10 / 30 | blockerad | OpenAI:s prissidor nekas av proxyn. Modellerna finns inte på OpenRouter i dag |
| `claude-3-sonnet-20240229` (A 2024-03 – 05) | 3 / 15 | finns inte längre | platform.claude.com/docs pricing läst. Claude 3 Sonnet är pensionerad och listas inte |
| `gemini/gemini-1.5-flash` (A 2024-06, 2024-08) | 0,35 / 1,05, sedan 0,075 / 0,30 | blockerad | Lanseringspriset går inte att kontrollera (ai.google.dev nekas, Vertex visar bara dagens pris). 0,075 / 0,30 = Vertex-listan |
| `deepseek-chat`, `deepseek/deepseek-chat` (A 2024-07, B 2024-12 – 2025-01) | 0,14 / 0,28 | blockerad | api-docs.deepseek.com nekas |
| `gemini/gemini-1.5-flash-001`, `-002` (A 2024-09 – 2025-08) | 0,075 / 0,30 | utvecklarens sida | Vertex-listan |
| `gemini/gemini-1.5-pro-002` (B 2024-10 – 11) | 1,25 / 5,00 efter rättning | utvecklarens sida | Vertex-listan. Datum enligt 7.2 |
| `gemini/gemini-2.0-flash-lite-preview-02-05` (A 2025-09 – 12, B 2025-02 – 12) | 0,075 / 0,30 | utvecklarens sida | Vertex-listan för Gemini 2.0 Flash-Lite (GA-modellen; förhandsversionen listas inte) |
| `gpt-4o-2024-05-13` (B 2024-05 – 08) | 5 / 15 | blockerad | OpenAI nekas. OpenRouter (leverantör OpenAI) visar 5 / 15 i dag |
| `o1-mini-2024-09-12` (B 2024-09) | 3 / 12 | blockerad | OpenAI nekas. Finns inte på OpenRouter i dag |
| `gpt-5-nano-2025-08-07` (A och B 2026-01 – 02, 2026-08 – 10) | 0,05 / 0,40 | blockerad | OpenAI nekas. OpenRouter (leverantör OpenAI) visar 0,05 / 0,40 i dag |
| `mistral/mistral-small-3-2-2506` (A och B 2026-03 – 07) | 0,06 / 0,18 | omstridd | Se 7.4 |

Av 26 månader i B (2024-09 – 2026-10) har 13 ett pris vid minimum som stämmer med utvecklarens egen prislista i
dag. De övriga 13 är overifierade, och 5 av dem är omstridda. OpenRouter är en andrahandskontroll och ersätter inte
utvecklarens sida. Blockerade värdar har inte kringgåtts.

### 7.4 R-4: Mistral Small 3.2

Priset 0,06 / 0,18 gick inte att verifiera. mistral.ai, docs.mistral.ai och archive.org nekas av proxyn. OpenRouter
listar 2026-11-24 bara tredjepartsvärdar för modellen (DeepInfra 0,075 / 0,20). Månaderna 2026-03 – 07 har därför
`price_check = disputed` i A och B. Serierna med och utan nyckeln (`build(exclude_keys=...)`):

| Månad | A och B med nyckeln | A och B utan nyckeln |
|---|---|---|
| 2026-01 – 02 | 0,1375 | 0,1375 |
| 2026-03 – 07 | **0,09** | 0,1375 (GPT-5 nano) |
| 2026-08 – 10 | 0,1375 | 0,1375 |

Övriga månader är lika. Det lagrade värdet behåller nyckeln, och flaggan visar att det är osäkert.

### 7.5 R-5: Geminis alias

Geminis stabila alias behandlas som DeepSeeks rullande alias, i stället för att uteslutas. Före 2024-09-24 fanns
bara en stabil version av 1.5 Flash och 1.5 Pro (`-001`, GA 2024-05-24), så aliaset kan bara ha serverat `-001`.
Det räknas därför som `-001` från 2024-05-24 till och med 2024-09-23. Vad det pekade på efter `-002` används inte.
Googles egen dokumentation om aliasen (ai.google.dev) nekas av proxyn, så slutdatumet är valt försiktigt: dagen före
`-002`. Effekt: A 2024-06 blir 0,525 i stället för 6,00 och, med prisrättningen, 2024-08 0,13125 i stället för 0,175.
B påverkas inte, eftersom 1.5 Flash inte når GPT-4o-nivån.

### 7.6 Robusthet efter rättningen (R8 punkt 5, B från 2024-09)

Halveringstiden räknas med tillståndsmotorns regel: första versionen per månad, löpande minimum, log-linjär
regression över 24 månader. Med start 2024-09 finns 24 månader först 2026-08, så det finns tre värden. Det här är
en känslighetsanalys för registerfrågan och inget resultat.

| Fall | 2026-08 | 2026-09 | 2026-10 |
|---|---|---|---|
| B efter X5 | 6,4 | 8,9 | 12,8 |
| B utan prisrättningarna (före R-2) | 5,6 | 7,3 | 11,0 |
| B utan Mistral Small 3.2 | 7,7 | 11,9 | 20,9 |
| B utan DeepSeek `deepseek-chat` | 5,5 | 7,0 | 9,0 |
| B utan Gemini 1.5 Pro 002 | 5,6 | 7,3 | 11,0 |
| B utan Gemini 2.0 Flash-Lite Preview | 6,1 | 8,1 | 10,9 |
| B utan o1-mini | 6,2 | 8,9 | 12,8 |
| B utan tröskel (alla kopplade och prissatta modeller) | 39,1 | 35,5 | 33,0 |
| B, tröskel −10 eller +10 poäng | 6,4 | 8,9 | 12,8 |
| B, tröskel −25 poäng | 28,1 | 35,5 | 33,0 |
| B, tröskel +25 poäng | 5,6 | 7,2 | 10,7 |

Fynd:

1. **Serien är fortfarande en stegfunktion.** B har 6 nivåer och 7 steg på 26 månader. Varje steg är en enda
   modells inträde, prisändring eller pensionering.
2. **Ett enskilt prissteg flyttar takten med upp till 63 %.** Att ta bort en enda nyckel ger 9,0 – 20,9 månader
   2026-10, mot 12,8. Det omstridda Mistral-priset ensamt ger 12,8 i stället för 20,9.
3. **Tröskeln binder bara 2024-09 – 2025-01.** Utan tröskel blir halveringstiden 33 – 39 månader. Takten 2026-08 – 10
   kommer alltså nästan helt från fallet 5,25 → 0,13 under de fem månader då tröskeln binder. Från 2027-01 ligger de
   månaderna utanför fönstret. Då mäter B bara golvet från 2025-02: med Mistral-nyckeln ett enda steg (0,13125 →
   0,09 i 2026-03), och utan den ingen takt alls, eftersom fronten är platt.
4. **Tröskeln ±10 poäng ändrar inget**, men ±25 poäng flyttar takten mellan 10,7 och 33 månader.

**Slutsats:** efter rättningen mäter B fortfarande golvet i förstapartslistornas billigaste nivå. Det enda som
skiljer B från golvet är fem månader i början, och dess takt beror på enskilda prissteg. Villkoret i R8 R-9 ("en
takt som inte beror på ett enskilt prissteg") är inte uppfyllt. **Rekommendation: registrera varken A eller B som
kärnserie.** Behåll dem som beskrivande serier (`publish=True`, med flaggan `price_check`).
