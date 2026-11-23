# Externa förväntningar: prognosmarknader och Metaculus (L9, G9)

Steg 2, spår D3. Kod: `src/ai_tracker/sources/forvantningar.py` (urval, hämtning och tolkning per plattform),
serier i `src/ai_tracker/series/forvantningar.py`, urvalet i `src/ai_tracker/sources/forvantningar_urval.json`.
Inga takter, inga jämförelser mot utfall och inget scenarioträd i det här spåret.

## 1. Urvalsregel (skriven och committad innan några priser eller sannolikheter har lästs)

Regeln tillämpas mekaniskt av `python -m ai_tracker.sources.forvantningar select`. Den läser bara metadata: titel,
typ, status, datum, antal handlare eller prognosmakare och volym. Den läser aldrig pris, sannolikhet eller median, och
den skriver aldrig ut sådana värden. Urvalet sparas med datum och ändras inte i efterhand. Ett senare tillägg blir en ny
daterad urvalsomgång med samma regel.

**Ämnen.** En fråga hör till ett ämne om titeln matchar ämnets mönster (skiftlägesokänsligt). Den hamnar i det första
ämne i ordningen T1–T5 som matchar.

| Ämne | Innehåll | Mönster på titeln (reguljärt uttryck) |
|---|---|---|
| T1 Förmåga | AGI- och ASI-datum, benchmarkgränser, nästa generations modeller | `\bAGI\b\|artificial general intelligence\|superintelligen\|\bASI\b\|\bIMO\b\|math(ematical)? olympiad\|ARC-AGI\|FrontierMath\|Humanity's Last Exam\|SWE-bench\|Turing test\|best AI model\|top AI model\|GPT-?[6-9]\|Gemini [4-9]\|Claude [5-9]\|Grok [5-9]` |
| T2 Bolag | Intäkter, värdering, börsnotering för AI-bolag | (`OpenAI\|Anthropic\|xAI\|Mistral\|Safe Superintelligence\|CoreWeave\|Nvidia\|Cerebras`) och (`IPO\|go(es)? public\|valuation\|valued\|revenue\|market cap\|largest company\|funding\|raise`) |
| T3 Investeringar | Hyperskalarnas capex, datacenter | `capex\|capital expenditure\|data ?cent(er\|re)\|Stargate\|gigawatt` |
| T4 Exportkontroller | Chipexport, främst till Kina | `export control\|export ban\|export restriction\|chip export\|AI diffusion\|\bH20\b\|\bH200\b\|Blackwell` |
| T5 Reglering | AI-lagar och regleringsbeslut | `AI Act\|AI regulation\|regulate AI\|AI bill\|AI law\|SB ?1047\|SB ?53\|RAISE Act\|moratorium\|preempt\|executive order` |

För T3–T5 måste titeln dessutom matcha `\bAI\b\|artificial intelligence\|Nvidia\|OpenAI\|Anthropic\|chip\|semiconductor\|Stargate\|data ?cent` (AI-anknytning), utom för Polymarket där kandidaterna redan kommer ur AI-taggen.

**Kandidater per plattform** (fasta sökningar, inga andra):

- **Manifold:** `GET /v0/search-markets` med `term` = vart och ett av orden AGI, artificial general intelligence,
  superintelligence, IMO, ARC-AGI, FrontierMath, SWE-bench, Turing test, AI model, GPT-6, Gemini 4, Claude 5, Grok 5,
  OpenAI, Anthropic, xAI, Nvidia, CoreWeave, AI IPO, capex, data center, Stargate, export controls, H20, H200,
  AI Act, AI regulation, AI bill, AI moratorium, SB 53, `contractType=BINARY`, `filter=all`, `sort=most-popular`,
  `limit=100`.
- **Polymarket:** `GET gamma-api.polymarket.com/events` med `tag_slug=ai`, både `closed=false` och `closed=true`,
  sidvis med `limit=100` tills listan tar slut. Varje marknad i en händelse är en kandidat.
- **Metaculus:** `GET /api/posts/` med `search` = samma ord som för Manifold, `forecast_type=binary,date`.
  **BLOCKED** (avsnitt 4).
- **Kalshi:** ingen. Villkoren förbjuder lagring och delning (avsnitt 3).

**Kriterier** (alla måste vara uppfyllda):

1. **Typ:** binär fråga (Ja/Nej). Metaculus även datumfrågor. Manifold: `outcomeType = BINARY`,
   `mechanism = cpmm-1`, `token = MANA`. Polymarket: utfallen exakt `["Yes", "No"]`.
2. **Likviditet eller deltagande:** Manifold minst 100 unika handlare (`uniqueBettorCount`), Polymarket minst
   250 000 USD i total volym (`volumeNum`), Metaculus minst 100 prognosmakare.
3. **Öppen och långlivad, eller avslutad och långlivad:**
   - öppen: planerad stängning (`closeTime`, `endDate`) minst 90 dagar efter urvalsdagen;
   - avslutad eller avgjord: livslängd (stängning − skapande) minst 180 dagar, stängd 2023-01-01 eller senare, och
     inte avgjord som ogiltig (Manifold `resolution = CANCEL`). Avslutade frågor ger serier med `closed=True`.
     Polymarket: bara öppna, eftersom historik inte går att hämta (avsnitt 2).
4. **Avgörbar:** frågan har ett objektivt kriterium och ett datum. Uteslut titlar som handlar om plattformen själv
   eller om en enskild användare (mönster `manifold\|polymarket\|metaculus\|\bI\b\|\bme\b\|\bmy\b`), och frågor
   utan datum eller år i titel eller stängningsdatum.
5. **Tak:** högst 6 frågor per ämne och plattform, de med högst deltagande (Manifold handlare, Polymarket volym),
   vid lika det lägsta id:t. Från samma Polymarket-händelse högst 2 marknader (de med högst volym).

**Metadata som sparas per fråga** i `forvantningar_urval.json`: plattform, id, titel, ämne, URL till frågan där
avgörandekriterierna står (`resolution_url`), Polymarkets `resolutionSource` när den finns, skapad, planerad
stängning, status vid urvalet, deltagandemåttet och urvalsdagen.

## 2. Serier och `known_from`

(Fylls i när hämtningen är byggd.)

## 3. Villkor per plattform

(Fylls i.)

## 4. BLOCKED

(Fylls i.)
