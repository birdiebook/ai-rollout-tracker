# Förstapartspriser: egna ögonblicksbilder (G2, spår B5)

Steg 2, våg 1, spår B5. Byggt 2026-11-23. Målet är att göra G2 (pris vid fast förmåga) levande framåt med priser
direkt från utvecklarna, oberoende av LiteLLM. Här beskrivs åtkomst, metod och nivåkontroll. Ingen takt räknas här.

**Utfall:** av sex utvecklare går bara **Anthropic** att hämta. De andra fem värdarna nekas av sandlådans proxy och
är BLOCKED. Leveransen är därför ramverket (register, insamlare, nivåkontroll, serie), en utvecklare i drift och en
lista över värdar som behöver öppnas.

Kod: `src/ai_tracker/sources/firstparty_prices.py` (register, tolkning, ögonblicksbilder och kontroll mot LiteLLM)
och `src/ai_tracker/series/firstparty_prices.py` (serien). Tester finns i `tests/test_firstparty_prices.py`, med
fixturer och utan nät. Kör en ögonblicksbild och kontrollen med `python -m ai_tracker.sources.firstparty_prices`.

## Åtkomst (kontrollerat 2026-11-23, ett försök per värd)

Klient: `ai_tracker.http` med User-Agent `ai-rollout-tracker (github.com/birdiebook/ai-rollout-tracker)`. Ingen
webbläsarimitation, och inga speglar eller omvägar för nekade värdar.

| Utvecklare | Prissida som prövades | Svar | Status |
|---|---|---|---|
| Anthropic | `platform.claude.com/docs/en/about-claude/pricing.md` (Markdown, 40 kB) | 200 `text/markdown` | **OK** |
| OpenAI | `openai.com/api/pricing/`, `platform.openai.com/docs/pricing` (+ `robots.txt`) | proxy 403 vid CONNECT | **BLOCKED** |
| Google (Gemini API) | `ai.google.dev/gemini-api/docs/pricing` (+ `robots.txt`) | proxy 403 | **BLOCKED** |
| DeepSeek | `api-docs.deepseek.com/quick_start/pricing` (+ `robots.txt`) | proxy 403 | **BLOCKED** |
| Mistral | `mistral.ai/pricing`, `docs.mistral.ai` (+ `robots.txt`) | proxy 403 | **BLOCKED** |
| xAI | `docs.x.ai/docs/models`, `x.ai/api` (+ `robots.txt`) | proxy 403 | **BLOCKED** |

Proxyns svar för alla BLOCKED-värdar: `403 Forbidden (agent proxy: no rule or network setting allows this host)`.
Villkoren för de värdarna har inte kunnat läsas, så de är okontrollerade. API-värdarna (`api.openai.com`,
`api.x.ai`, `api.mistral.ai`, `api.deepseek.com`) nekas också. `generativelanguage.googleapis.com` svarar 403 utan
nyckel och har ändå inga priser. xAI:s `api.x.ai/v1/language-models` har priser men kräver API-nyckel.
Registret i `PROVIDERS` har en rad per utvecklare med status, datum och skäl. En BLOCKED-utvecklare har ingen
tolkare och hämtas aldrig (testat).

**Värdar som behöver öppnas** för att serien ska täcka fler utvecklare: `platform.openai.com` (eller `openai.com`),
`ai.google.dev`, `api-docs.deepseek.com`, `mistral.ai` och `docs.x.ai`. Robots och villkor måste sedan kontrolleras
per värd innan en tolkare läggs till.

### Anthropic: robots och villkor

- `platform.claude.com/robots.txt`: `User-Agent: *`, `Disallow: /api/`. Prissidan ligger under `/docs/` och är
  tillåten. `www.anthropic.com/robots.txt` och `claude.com/robots.txt` har `Allow: /`.
- Sidan publiceras maskinläsbart: `platform.claude.com/llms.txt` ("This file provides an overview of the Anthropic
  API documentation") listar `- [Pricing](https://platform.claude.com/docs/en/about-claude/pricing.md)`, och
  servern levererar `text/markdown`.
- Konsumentvillkoren (`anthropic.com/legal/consumer-terms`, "Effective Oct 8, 2025") omfattar "Claude.ai, Claude
  Pro, and other products and services that we may offer for individuals, along with any associated apps,
  software, and websites". De förbjuder "Except when you are accessing our Services via an Anthropic API Key or
  where we otherwise explicitly permit it, to access the Services through automated or non-human means, whether
  through a bot, script, or otherwise" och "To crawl, scrape, or otherwise harvest data or information from our
  Services other than as permitted under these Terms".
- **Bedömning:** spårets regel är att hämta där utvecklaren publicerar maskinläsbara priser. Det gör Anthropic här,
  genom en Markdown-version som `llms.txt` pekar ut för automatiska klienter och som robots.txt tillåter. Vi läser
  den med ett anrop i veckan. Det är inte prövat om `llms.txt` räknas som "explicitly permit it" i villkorens
  mening. **Rekommendation:** behåll insamlingen och `publish=False`. Johannes bekräftar en gång eller stoppar den
  genom att sätta `status="BLOCKED"`.
- **Licens:** sidan anger ingen licens för data. Priser är fakta, men vidarespridning är inte kontrollerad. Därför
  gäller `publish=False`.

## Ögonblicksbilder

- **Lagring:** `data/raw/firstparty_prices/snapshots.parquet` (committas inte, ligger i Actions-cachen). En rad per
  ögonblicksbild, modell och nivå, med `snapshot_date` (UTC), `fetched_at`, `developer`, `model` (namnet som
  publicerat), `tier`, `base_tier`, `availability`, `input_per_m`, `output_per_m`, `url` och `sha256` av sidan.
  Själva sidan sparas av `ai_tracker.http` under `RAW_DIR/firstparty_prices/<datum>/`, så tolkningen kan göras om.
  Paret (datum, utvecklare) skrivs bara en gång.
- **Tolkning (Anthropic):** bara tabellen under `## Model pricing`. Kolumnerna `Base input tokens` och
  `Output tokens` används, och fotnoter (`<sup>`) tas bort. Tolkaren stoppar (`ParseError`) om rubriken,
  kolumnerna eller antalet celler ändras, om ett pris inte går att läsa eller om input > output. Den gissar aldrig.
- **Tillgänglighet:** `retired` om namncellens länk säger "retired" (Opus 4, Opus 4.1 och Sonnet 4 i dag),
  `limited` vid "limited availability" (Mythos 5, 5.1 och 5.2), annars `available`.
- **Nivåer:** Haiku 5.5 har två prisnivåer efter promptlängd (≤ 100 000 tokens 0,10/0,50 USD, däröver 0,50/2,50).
  Den först listade nivån är basnivån och den enda som räknas. Det är samma regel som för LiteLLM, där nivåer över
  200 000 tokens ignoreras.
- **Insamling:** steget "Collect first-party price snapshots" i `collect-weekly.yml` (måndagar 04:17 UTC) kör
  `observations.refresh` för seriens nyckel. Seriens `fetch` tar först dagens ögonblicksbild och räknar sedan om
  serien. `fetch-weekly.yml` (03:37) gör samma sak genom `pipeline weekly`, så 04:17-steget hittar normalt
  "already taken today". Första ögonblicksbilden togs lokalt 2026-11-23 med 22 rader. I Actions blir den första
  2026-11-30, om spåret är mergat då.

## Serie

| Nyckel | Förmåga | Tröskel | Historik | Publiceras |
|---|---|---|---|---|
| `g2_fp_price_at_capability_gpqa_anthropic` | Epochs GPQA Diamond-körningar, kända vid månadsslut | 0,767676 (samma låsta tröskel som `g2_price_at_capability_gpqa`) | 2026-11 – (första värdet är känt 2026-12-01) | nej |

Värde för månad m: det lägsta blandade priset, (3 × input + output) / 4 i USD per miljon tokens, bland Anthropics
modeller som är `available` i basnivån och har GPQA-förmåga ≥ tröskeln. Förmågan är den bästa körningen med
`known_from` ≤ månadsslut, enligt samma regel som `price_capability.capability_gpqa`. Priset tas från den senaste
egna ögonblicksbilden som är högst 7 dagar äldre än månadsslutet. Finns ingen sådan ögonblicksbild får månaden
inget värde, och det syns som ett hål. Ett gammalt läge förs aldrig vidare. Modellnamnet på sidan måste vara en
Anthropic-modell i `model_map.MODEL_MAP`, och Anthropic använder Epochs namn. Mythos-modellerna saknar Epoch-mått och
räknas inte.

- **known_from** = månadsslut + 1 dag (`lag_days=1`, samma regel som de registrerade G2-serierna). Värdet bygger
  på en ögonblicksbild som kan vara tagen på månadens sista dag. Raderna har `source="release"`, och ingen historik
  fylls i bakåt. Före första ögonblicksbilden finns inget.
- **revised=True:** Epoch kan köra om eller ta bort GPQA-körningar.
- **Aktualitet:** serien saknar värde tills november är slut. `warehouse.KNOWN_STALE` accepterar det till
  2026-12-15, eftersom första veckokörningen efter 2026-12-01 är 2026-12-07.
- **En utvecklare per serie, med avsikt.** Ett minimum över de värdar som råkar vara öppna skulle byta definition
  varje gång en värd öppnas. En sammanslagen förstapartsserie registreras när fler utvecklare samlas in.
- **Registrering:** serien är ny och ska in i grind G-A (`docs/mattregister.md`, orkestreraren) innan någon takt
  räknas. Definitionen ovan är förslaget. Tröskeln och blandningen återanvänds oförändrade från registret.

Kontrollberäkning med en simulerad ögonblicksbild vid månadsslut, från ögonblicksbilden 2026-11-23: Claude
Haiku 5.5 (GPQA 0,896, känd 2026-10-16) sätter minimum med 0,20 USD. 13 modeller ligger över tröskeln.

## Nivåkontroll mot LiteLLM (2026-11-23)

Anthropics basnivå jämfördes med LiteLLM:s aktuella `model_prices_and_context_window.json` på `main` (hämtad samma
dag). Nycklarna kommer från `MODEL_MAP`, och för modeller utan Epoch-namn används LiteLLM:s namnkonvention
(`Claude Mythos 5.1` → `claude-mythos-5-1`). Toleransen är 0,5 %.

| Utfall | Modeller |
|---|---|
| **match** (in- och utpris), 23 nycklar | Fable 5.2, 5.1 och 5, Mythos 5.2, 5.1 och 5, Opus 5.5, 5, 4.8, 4.7, 4.6 och 4.5, Sonnet 5.5, 5, 4.6 och 4.5, Haiku 5.5 och 4.5, inklusive daterade nycklar |
| **saknas i LiteLLM** | Opus 4.1, Opus 4, Sonnet 4. Alla tre är `retired` på Anthropics API, och LiteLLM har tagit bort dem |
| **mismatch** | inga |

Anthropics priser i LiteLLM stämmer alltså i dag. De kända felen i LiteLLM gäller andra utvecklare: Geminis
`gemini-1.5-pro-002` har legat kvar på ett gammalt pris, och `xai/grok-4*` har inte verifierats (se
`pris_formaga.md`, punkt 3). De felen kan inte kontrolleras här, eftersom Googles och xAI:s värdar är BLOCKED.
Kontrollen gäller bara nivån vid en tidpunkt. Den säger inget om hur fort LiteLLM följer prisändringar. Det går att
mäta när egna ögonblicksbilder har samlats under en tid, genom att jämföra datumet då ett pris ändrades hos
Anthropic med commit-datumet i LiteLLM.

## Förbehåll

1. **Bara listpris.** Batch, cache, prioritet och regionala tillägg ignoreras, liksom kampanjer som inte står i
   tabellen. Sonnet 5:s introduktionspris 2/10 USD är enligt fotnot 3 numera standardpris, så det räknas.
2. **Tokenisering:** sidan anger att Claude 4.7 och senare modeller ger ungefär 30 % fler tokens för samma text. Pris
   per token är därför inte pris per uppgift. Samma förbehåll gäller för alla G2-serier.
3. **GPQA Diamond** ligger nära taket och är brusig (se `pris_formaga.md`). 13 av Anthropics modeller ligger redan
   över tröskeln, så minimivärdet bestäms i praktiken av den billigaste kvalificerade modellen, i dag Haiku-klassen.
4. **Sidans layout** kan ändras. Då stoppar tolkaren, steget rapporteras som FAILED och månaden får inget värde.
