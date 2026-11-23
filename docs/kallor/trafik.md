# Trafik och uppmärksamhet: Cloudflare Radar och Wikipedia (L2, G3)

Steg 2, spår B3. Kod: `src/ai_tracker/sources/cloudflare_radar.py`, `src/ai_tracker/sources/wikipedia.py`, serier i
`src/ai_tracker/series/cloudflare_radar.py` och `src/ai_tracker/series/wikipedia.py`, jobbet
`src/ai_tracker/jobs/cloudflare_radar.py`. Tester: `tests/test_cloudflare_radar.py`, `tests/test_wikipedia.py`
(fixtures, inget nätverk). Inga takter och inga jämförelser i det här spåret, bara nivåer och datakontroller.

## 1. Serier

| Grupp | Nycklar | Frekvens | Från | Publiceras |
|---|---|---|---|---|
| Radar, HTML-trafik efter klienttyp | `g3_cf_html_ai_bot_share`, `g3_cf_html_mixed_bot_share` | W (mån–sön, UTC) | 2025-10-20 | ja |
| Radar, AI-botarnas syfte | `g3_cf_ai_purpose_training`, `_search`, `_user_action` | W | 2024-12-30 | ja |
| Radar, AI-botar per user agent | `g3_cf_ai_agent_gptbot`, `_chatgpt_user`, `_oai_searchbot`, `_claudebot`, `_meta`, `_bytespider` | W | 2024-12-30 | ja |
| Radar, verifierade botar per kategori | `g3_cf_bots_ai_crawler_share`, `g3_cf_bots_ai_assistant_share` | W | 2024-08-26 / 2024-12-16 | ja |
| Wikipedia, sidvisningar per ämne | `g3_wiki_<ämne>_en` och `g3_wiki_<ämne>_xen` för 12 ämnen (24 serier) | W (mån–sön) | 2015-07 till 2024 beroende på ämne | ja |

`xen` = summan av tyska, franska, spanska och japanska Wikipedia. Engelska hålls separat eftersom den dominerar och
läses över hela världen.

## 2. Cloudflare Radar

**API:** `https://api.cloudflare.com/client/v4/radar/...` med en egen API-token (Account > Radar: Read). Token finns
bara som hemligheten `CLOUDFLARE_API_TOKEN` i GitHub Actions. Dokumentationen på developers.cloudflare.com nekas av
sessionens proxy. Den lästes i stället i källan (`cloudflare/cloudflare-docs`, `src/content/docs/radar/*.mdx`, via
raw.githubusercontent.com) och i Cloudflares OpenAPI-schema (`cloudflare/api-schemas`, `openapi.json`).

**Licens.** `src/content/docs/radar/index.mdx`: *"Data available via Radar API endpoints is made available under the
CC BY-NC 4.0 license."* Projektet är icke-kommersiellt och sidan anger källa och licens per serie, så serierna har
`publish=True` med erkännandet "Cloudflare Radar, CC BY-NC 4.0". NC-villkoret följer med: den som återanvänder
siffrorna från vår sida får inte göra det kommersiellt. **Beslut för Johannes:** om sidan någon gång ska kunna
användas kommersiellt måste Radar-serierna sättas till `publish=False`.

**Endpoints och grupper** (alla med `aggInterval=1w`, `format=json`):

| Serie | Endpoint | Grupp | Vad andelen är av |
|---|---|---|---|
| `g3_cf_html_ai_bot_share` | `/bots/crawlers/timeseries_groups/CLIENT_TYPE` | `AI_BOT` | HTML-förfrågningar i Radars crawler-dataset, fördelade på HUMAN, NON_AI_BOT, AI_BOT och MIXED_PURPOSE |
| `g3_cf_html_mixed_bot_share` | samma | `MIXED_PURPOSE` | samma |
| `g3_cf_ai_purpose_*` | `/ai/bots/timeseries_groups/CRAWL_PURPOSE` | `Training`, `Search`, `User Action` | AI-botarnas förfrågningar (övriga grupper: Mixed Purpose, Undeclared) |
| `g3_cf_ai_agent_*` | `/ai/bots/timeseries_groups/USER_AGENT`, `limitPerGroup=40` | `GPTBot`, `ChatGPT-User`, `OAI-SearchBot`, `ClaudeBot`, `Meta-ExternalAgent`, `Bytespider` | AI-botarnas förfrågningar |
| `g3_cf_bots_ai_*` | `/bots/timeseries_groups/BOT_CATEGORY` | `AI_CRAWLER`, `AI_ASSISTANT` | verifierade botars förfrågningar |

Vilka user agents som räknas som AI-botar bestämmer Cloudflare. Ordlistan säger att de kommer ur
[ai.robots.txt](https://github.com/ai-robots-txt/ai.robots.txt). Vad nämnaren i CLIENT_TYPE exakt är står inte i den
dokumentation som gick att läsa. Ordlistan säger bara att crawler-måtten bygger på förfrågningar efter HTML-sidor.
Andelen HUMAN där (cirka 40 % hösten 2026) är lägre än Radars andel mänsklig HTTP-trafik totalt (cirka 61 %), så
datasetet är inte all trafik. Det är inte verifierat.

**Varför bara andelar.** Radar returnerar aldrig råa volymer. Volymserier (`/ai/bots/timeseries`,
`/bots/timeseries`) är min-max-normerade (`MIN0_MAX`) mot maximum i varje svar. Varje hämtning skalar då om hela
historiken, och en versionerad tabell skulle få nya värden för alla veckor varje gång. Andelar (`PERCENTAGE`) beror
inte på fönstret. Volymserierna tas därför inte med. Radars längsta AI-historik (volym för `AI_CRAWLER` i
`/bots/timeseries`) börjar också 2024, så andelarna förlorar ingen historik. Rangordningen av generativa AI-tjänster
(`/ranking/internet_services/timeseries_groups`, från 2024-03) och fördelningen av Workers AI-inferens per uppgift
gäller Cloudflares egen plattform respektive bara topp 10 som ordningstal, och tas inte med nu.

**Historik (prob 2026-11-23).** API:t vägrar datum före 2021-12-27 och fönster längre än ungefär ett år (73 veckor
vägrades, 47 svarade). Hämtningen går därför i fönster om högst 50 veckor från 2024-01-01. Före den första veckan med
data fyller Radar ut med nollor i alla grupper. Sådana veckor (summan över grupperna är 0) tas bort. En riktig andel 0
i en vecka med data behålls. Första vecka med data (hämtning 2026-11-23):

- CRAWL_PURPOSE och USER_AGENT (AI-botar): 2024-12-30;
- CLIENT_TYPE (crawler-datasetet): 2025-10-20;
- BOT_CATEGORY: `AI_CRAWLER` 2024-08-26, `AI_ASSISTANT` 2024-12-16 (gruppen finns inte i fönstret 2024-01–2024-12,
  så de första veckorna i det fönstret hoppas över).

Alla 13 serier saknar hål fram till veckan 2026-11-16–22.

**known_from = veckans slut (söndag) + 1 dag.** Radar uppdateras löpande. Svarens `meta.lastUpdated` var
2026-11-23T19:30Z vid hämtning samma kväll, och dagsdata fanns till och med föregående dag. En vecka tas bara med när
den har slutat före hämtdagen (UTC), så en halv vecka lagras aldrig. Efter backfillen gäller tabellens vanliga regel:
en ny vecka får min(slut + 1 dag, hämtdag).

**Revideringar.** Radar kan räkna om historiken: annoteringar i svaren visar bland annat "Sampling rate changed to
address data pipeline issue" (2025-08-01, bot-kategorier) och "Cloudflare global network service degradation"
(2025-11-18). API:t kallar flera kategorier föråldrade (`ACCESSIBILITY`, `AGGREGATOR`, `AI_SEARCH`, `ARCHIVER`,
`SOCIAL_MEDIA_MARKETING`, `WEBHOOKS`), så kategoriindelningen har bytts. Hela historiken hämtas om varje vecka, och en
ändrad andel blir en revidering med `known_from` = hämtdagen. Backfillen har dagens version, så tidigare
omklassningar läcker in i den. Serierna har `revised=True`. Varje svars `lastUpdated`, normering och annoteringar
sparas i jobbets `meta.json`.

**Gruppnamn som försvinner.** Om en grupp saknas i ett fönster (agenten var inte med bland de 40 största, eller
kategorin fanns inte) hoppas fönstret över. Om det händer mitt i serien blir det ett hål, och datatestet `no_gaps`
fäller veckohämtningen. Det är avsiktligt.

### Körning

- **Jobbet** `python -m ai_tracker.jobs cloudflare_radar` (workflow `job.yml`, input `job=cloudflare_radar`) hämtar
  alla Radar-serier i katalogen och skriver `<nyckel>.csv`, `meta.json` och en rad per serie i loggen
  (`RADAR {"key": ..., "start": ..., "values": [...]}`). Värden i artefakten och loggen är publika aggregat.
- **Lokalt** (sessionen har ingen token och når inte blob-värden för artefakter): hämta jobbets logg
  (`gh api repos/<repo>/actions/jobs/<id>/logs`), skriv CSV:erna med
  `cloudflare_radar.from_log(text, "data/raw/cloudflare_radar/<datum>")` och kör
  `CLOUDFLARE_RADAR_JOB_DIR=data/raw/cloudflare_radar/<datum> python -m ai_tracker.observations <nycklar>`.
  `Spec.fetch` använder API:t när token finns och annars katalogen i `CLOUDFLARE_RADAR_JOB_DIR`.
- **Driften:** `fetch-weekly.yml` får `CLOUDFLARE_API_TOKEN` som hemlighet. `pipeline weekly` hämtar då Radar-serierna
  direkt från API:t tillsammans med resten av katalogen. Utan token fallerar bara de serierna (en varning), och
  aktualitetskontrollen fäller jobbet om de blir äldre än 1 + 7 + 30 = 38 dagar.

## 3. Wikipedia

**API:** Wikimedia Analytics `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{lang}.wikipedia/
all-access/user/{titel}/daily/20150701/{igår}`. Ingen nyckel. Ärlig User-Agent med projektets URL. Agent `user`
(spindlar och från 2020 även "automated" är bortrensade), alla åtkomstsätt. Ett anrop per titel ger hela historiken.

**Licens.** Wikimedias sida för datasetet (`dumps.wikimedia.org/other/pageviews/readme.html`, läst i källan
`wikimedia/operations-puppet`, `modules/dumps/files/web/html/pageviews_readme.html`, eftersom dumps.wikimedia.org
nekas av proxyn): *"All Analytics datasets are available under the Creative Commons CC0 dedication."* API:t serverar
samma dataset. `publish=True`, med källa angiven.

**Ämnen och titlar** (skrivna och committade 2026-11-23, commit 8139ab6, innan några sidvisningar hämtades):

| Ämne | Engelska titlar (nuvarande först, sedan tidigare) | de / fr / es / ja |
|---|---|---|
| chatgpt | ChatGPT | ChatGPT i alla |
| claude | Claude (AI), Claude (language model) | Claude / Claude (modèle de langage) / Claude (chatbot) / Claude |
| gemini | Google Gemini, Gemini (chatbot), Bard (chatbot), Google Bard | Google Gemini / Gemini (intelligence artificielle) / Gemini (bot conversacional) / Gemini (チャットボット) |
| copilot | Microsoft Copilot, Bing Chat, Bing AI | Microsoft Copilot i alla |
| grok | Grok (chatbot) | Grok / Grok / Grok (chatbot) / Grok |
| deepseek | DeepSeek | DeepSeek i alla |
| perplexity | Perplexity AI | Perplexity AI / Perplexity AI / Perplexity / Perplexity |
| llm | Large language model | Large Language Model / Grand modèle de langage / Modelo de lenguaje de gran tamaño / 大規模言語モデル |
| genai | Generative AI, Generative artificial intelligence | Generative künstliche Intelligenz / Intelligence artificielle générative / Inteligencia artificial generativa / 生成的人工知能 |
| ai | Artificial intelligence | Künstliche Intelligenz / Intelligence artificielle / Inteligencia artificial / 人工知能 |
| openai | OpenAI | OpenAI i alla |
| anthropic | Anthropic | Anthropic i alla |

Titlarna på andra språk är språklänkarna från den engelska artikeln (`api.wikimedia.org/core/v1/wikipedia/en/page/
<titel>/links/language`, 2026-11-23).

**Sidflyttar.** Sidvisningar räknas under den titel som efterfrågades. Efter en flytt blir den gamla titeln en
omdirigering, och visningarna före flytten ligger kvar under den. Kontrollen 2026-11-23 visade att tre av de engelska
arbetstitlarna i listan redan var omdirigeringar ("Claude (language model)" → "Claude (AI)", "Gemini (chatbot)" →
"Google Gemini", "Generative artificial intelligence" → "Generative AI", alla märkta *R from move*). Därför summerar
varje ämne den nuvarande titeln och de tidigare titlarna. Bara omdirigeringar märkta som flytt eller tidigare namn
(*R from move*, *R from former name*, *R former*) räknas. Rena alias, som "Large language models" (*R from plural*),
räknas inte, och inte heller sektioner i andra artiklar. Nivån är därför en undre gräns för ämnets uppmärksamhet.

**Tillägg 2026-11-23, efter den första hämtningen** (en kontroll av datakorrekthet, ingen analys). Startdatum per
titel jämfördes med produktens ålder. Där den nuvarande titeln började abrupt söktes den tidigare titeln i sidans
historik (flyttkommentaren i `api.wikimedia.org/core/v1/wikipedia/<språk>/page/<titel>/history`) eller bland
omdirigeringar till sidan med egen trafik:

| Ämne, språk | Tillagda titlar | Belägg |
|---|---|---|
| gemini, fr | Gemini (IA), Google Gemini, Gemini (chatbot), Bard (chatbot) | "Onalion a déplacé la page [[Gemini (IA)]] vers [[Gemini (intelligence artificielle)]]" 2026-10-03. De övriga är omdirigeringar till sidan med toppveckor på 1 500–4 600 visningar 2023–2026 |
| llm, es | Modelo extenso de lenguaje, Modelo de lenguaje grande | "Aguzado trasladó la página [[Modelo extenso de lenguaje]] a [[Modelo de lenguaje de gran tamaño]]" 2026-09-24. "Modelo de lenguaje grande" är omdirigering med toppvecka 4 753 (2024-06) |
| perplexity, en | Perplexity.ai | omdirigering märkt *R from move*, toppvecka 68 721 (2024-05) |

**Kvarstående nivåbrott som inte gick att laga** (den tidigare titeln hittades inte, eller artikeln var en sektion i
en annan artikel): Microsoft Copilot på engelska (artikeln har nämnvärd trafik först från hösten 2023; Bing Chat-
perioden ligger troligen i artikeln om Microsoft Bing), Perplexity på engelska före 2024-01, de tyska artiklarna
"Generative künstliche Intelligenz" (från 2026-04) och "Perplexity AI" (flyttad från ett användarutkast 2025-10-31),
och "Gemini (IA)" på franska, som börjar abrupt 2025-07-14 men täcks av de andra franska titlarna. Claude på engelska
börjar 2024-01-23 utan tidigare titel. Före det fanns troligen ingen egen artikel.

**Produktämnen räknas från lansering.** Några nuvarande titlar är vanliga ord som betydde något annat innan
(tyskans "Claude" och "Grok" har visningar från 2015, franskans "Grok" från 2022). Visningar före produktens
offentliga lansering räknas därför inte: ChatGPT 2022-11-30, Claude 2023-03-14, Gemini (Bard) 2023-02-06, Copilot
(Bing Chat) 2023-02-07, Grok 2023-11-04, DeepSeek 2023-07-17 och Perplexity 2022-12-07. Bolaget Anthropic räknas från
2021-05-28, då bolaget offentliggjordes (engelska och spanska "Anthropic" har visningar från 2015 respektive 2019,
cirka 50–80 i veckan). Gränsen för Anthropic lades till samtidigt som tillägget nedan. Om en sådan titel pekade på
något annat även en tid efter lanseringen finns en liten rest kvar (tyska "Claude" hade cirka 40 visningar i veckan
före 2023). Ämnena llm, genai, ai och openai har ingen gräns.

**Veckovärde** = summan av dagliga visningar måndag–söndag. En dag utan rad räknas som 0 (API:t utelämnar dagar utan
visningar). Bara veckor vars söndag finns i svaret tas med, så den sista veckan kommer med först när söndagens data
finns. Den första veckan 2015 (API:t börjar onsdag 2015-07-01) tas bort.

**known_from = veckans slut + 2 dagar.** Dagsdata för en dag fanns dagen efter (2026-11-23 kl. 21 UTC fanns
2026-11-22). Veckohämtningen går måndag 03:37 UTC, och då finns söndagen oftast inte än. Veckan kommer då med vid
nästa hämtning, och regeln om frånvarande hämtningar ger `known_from` ≥ tisdagen. 2 dagar är alltså den tidigaste
dag då en vecka säkert fanns.

**Revideringar.** Wikimedia klassar ibland om trafik från automatiska klienter till "automated" i efterhand.
Hela historiken hämtas om varje vecka, och ändringar blir revideringar. Backfillen har dagens version.
`revised=True`.

**Hastighetsgräns.** Sessionens utgående IP delas och får ofta HTTP 429 med `Retry-After`. Hämtningen väntar den tid
som anges (högst 60 s, 12 försök) och har 1 s mellan anrop. I Actions har jobbet en egen IP.

## 4. Datakontroller

PLACEHOLDER

## 5. BLOCKED och värdar

- `developers.cloudflare.com`: nekas av proxyn. Dokumentationen lästes via raw.githubusercontent.com.
- `productionresultssa*.blob.core.windows.net` (artefakter från Actions): nekas av proxyn trots att briefen säger
  att värden är tillåten. Jobbets resultat lästes i stället ur loggen (`gh api .../actions/jobs/<id>/logs`).
- `dumps.wikimedia.org`, `doc.wikimedia.org`, `en.wikipedia.org`, `www.mediawiki.org`: nekas. Licensen lästes i
  källan på GitHub, och sidornas status via `api.wikimedia.org`.
- Inga nya nycklar behövs. Cloudflare-token finns redan i Actions.
