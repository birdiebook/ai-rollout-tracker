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
  **BLOCKED** (avsnitt 5).
- **Kalshi:** ingen. Villkoren förbjuder lagring och delning (avsnitt 4).

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

## 2. Urvalet 2026-11-23 (omgång 1)

Regeln gav 25 frågor: 17 från Manifold (3 öppna, 14 avgjorda) och 8 från Polymarket (alla öppna). T4
(exportkontroller) fick inga frågor, eftersom ingen kandidat nådde deltagandegränsen med tillräckligt lång löptid.
Polymarket fick inga T1- eller T5-frågor av samma skäl, eftersom AI-taggens förmågefrågor mest är kortlivade
månadsmarknader. Deltagande = unika handlare (Manifold) och total volym i USD (Polymarket) vid urvalet.

| Nyckel | Ämne | Fråga | Status | Stängning | Deltagande |
|---|---|---|---|---|---|
| `g9_exp_mf_C8MtRn2ixX8Y0rV2Oqcy` | T1 | Will OpenAI hint at [read description] or claim to have AGI by 2025 end? | resolved | 2026-01-01 | 1 815 |
| `g9_exp_mf_nKyHon3IPOqJYzaWTHJB` | T1 | Will AI pass the Longbets version of the Turing test by the end of 2029? | open | 2030-01-01 | 998 |
| `g9_exp_mf_OAL8q0Azzl` | T1 | Perfect score achieved by an AI model in the International Math Olympiad (IMO) 2026? | resolved | 2026-07-26 | 539 |
| `g9_exp_mf_tu2ouer9zq` | T1 | Will an AI win a gold medal on International Math Olympiad (IMO) 2025? | resolved | 2025-07-21 | 498 |
| `g9_exp_mf_ektS9GTQmmbhURMFOrjM` | T1 | Will AI get at least bronze on the IMO by end of 2025? | resolved | 2025-07-21 | 370 |
| `g9_exp_mf_5WEpXLx31YdM11zOdo4h` | T1 | Will we get AGI before 2027? | open | 2027-03-01 | 354 |
| `g9_exp_mf_IxB74SW0mHdGXAYlUtWG` | T2 | Will OpenAI be valued more than $75 billion before the end of 2023? | resolved | 2024-01-03 | 401 |
| `g9_exp_mf_ii4d7faxzp` | T2 | Will Nvidia be the largest company in the world by market cap at the end of 2024? | resolved | 2024-12-31 | 310 |
| `g9_exp_mf_52sSQUNR2s` | T2 | Will Anthropic have a higher market cap than OpenAI after both IPO? | open | 2030-12-31 | 137 |
| `g9_exp_mf_0I0JK1Ei1S1V28mCoeDM` | T2 | Will OpenAI have $1 billion in revenue in 2025? | resolved | 2025-08-17 | 116 |
| `g9_exp_mf_K6q1EoIZQuHO1dmyEwvE` | T2 | Will Nvidia have a higher market cap. then Google at the end of 2024? | resolved | 2025-01-01 | 104 |
| `g9_exp_mf_EEtPNn6yLn` | T3 | 5. Multiple serious efforts to put AI data centers in space will take shape. | resolved | 2025-12-15 | 143 |
| `g9_exp_mf_MxFgKUqM4nKTCxpz3ilp` | T3 | Will the pope bless a data center before 2026? | resolved | 2025-12-31 | 138 |
| `g9_exp_mf_BmK6wCA9ol7sjaqB9ZGt` | T3 | In 2024, will OpenAI/Microsoft confirm plans to build a supercomputer like the rumored $100 billion "Stargate"? | resolved | 2025-01-01 | 103 |
| `g9_exp_mf_kuCvMHLZ8wtaYYqb4sWe` | T5 | Will California AI regulation bill SB 1047 become law this session? | resolved | 2024-09-29 | 541 |
| `g9_exp_mf_aHjcaCxaUR8Y1rM4lQdm` | T5 | Will any top AI lab commit to a moratorium on giant AI experiments before 2024? | resolved | 2023-12-31 | 152 |
| `g9_exp_mf_7hfkMUScOwukuWwfYy3I` | T5 | If Trump is elected, will there be an executive order or legislation focused on AI before the 2026 midterms? | resolved | 2025-01-22 | 131 |
| `g9_exp_pm_1298649` | T2 | OpenAI IPO closing market cap above $1T? | open | 2028-01-01 | 1 067 683 |
| `g9_exp_pm_1298657` | T2 | OpenAI IPO closing market cap above $1.2T? | open | 2028-01-01 | 250 898 |
| `g9_exp_pm_5126779` | T3 | Will Indiana enact a data center moratorium by December 31, 2027? | open | 2028-01-01 | 5 074 894 |
| `g9_exp_pm_5179198` | T3 | Will Indiana enact a data center moratorium by December 31, 2028? | open | 2029-01-01 | 662 200 |
| `g9_exp_pm_5123857` | T3 | Will Texas enact a data center moratorium by December 31, 2027? | open | 2028-01-01 | 501 093 |
| `g9_exp_pm_5126796` | T3 | Will Louisiana enact a data center moratorium by December 31, 2027? | open | 2028-01-01 | 421 369 |
| `g9_exp_pm_5126782` | T3 | Will Oklahoma enact a data center moratorium by December 31, 2027? | open | 2028-01-01 | 336 557 |
| `g9_exp_pm_5126793` | T3 | Will Missouri enact a data center moratorium by December 31, 2027? | open | 2028-01-01 | 279 563 |

Avgörandekriterierna står på frågans sida (`resolution_url` i urvalsfilen). Urvalet är mekaniskt och har inte justerats
i efterhand. Två svagheter syns redan i titlarna: T3-mönstret `data ?cent` fångar en skämtfråga ("the pope bless a
data center"), och de sex Polymarket-frågorna i T3 handlar om delstatliga moratorier för datacenter. Moratorierna
handlar om fysisk kapacitet, som är led L7, mer än om investeringsvilja. Om regeln ska skärpas sker det i en ny daterad
omgång före nästa urval, aldrig genom att ta bort frågor ur omgång 1.

## 3. Serier och `known_from`

| Nyckel | Frekv. | Värde | `known_from` | `source` |
|---|---|---|---|---|
| `g9_exp_mf_<id>` | D (UTC-dygn) | sannolikheten efter dygnets sista handel (`probAfter` i `/v0/bets`), och föregående dygns värde förs vidare om ingen handel skett | dygnets slut, alltså D+1 00:00 UTC. Varje handel som används har en tidsstämpel före `known_from` | backfill före frågans `selected_on`, därefter release |
| `g9_exp_pm_<id>` | W (mån–sön) | Ja-priset (`outcomePrices`, det pris Polymarket visar) vid den första hämtningen efter att veckan tagit slut | hämtdagen (midnatt UTC), som för andra hämtade värden i `observations.new_rows` | snapshot |

- **Manifold, historik:** hela handelshistoriken hämtas varje gång (sidvis med `before`, 1 000 per sida). Serien
  börjar dygnet för den första handeln och slutar vid det tidigare av stängnings- eller avgörandedygnet och i går.
  Ett ofullständigt dygn lagras aldrig. Själva avgörandet räknas inte som en prisnotering. Historik från API:t är
  tillåten här, eftersom varje handel är tidsstämplad när den gjordes. Om Manifold ändrar en gammal notering blir det
  en ny version med hämtdagen som `known_from` (`observations.new_rows`).
- **Polymarket, bara framåt:** prishistoriken finns bara på `clob.polymarket.com`, och den värden nås inte. Serien
  börjar därför med hämtningen 2026-11-23 (veckan 2026-11-16–22). Veckohämtningen sker på måndagar 03:37 UTC, så
  värdet speglar priset några timmar efter veckans slut. En senare hämtning samma vecka behåller den lagrade
  ögonblicksbilden. En missad vecka ger en lucka, som `no_gaps` fångar.
- **Polymarket, vilken dag priset gäller (R3):** värdet är *måndagens* pris (hämtat omkring 03:37 UTC), men det
  lagras under föregående vecka (mån–sön) och får `known_from` = måndagen 00:00 UTC. Det följer `as_of`-konventionen
  (ett värde som kommer under en dag räknas som känt den dagen), och priset tas mindre än fyra timmar efter dagens
  början. Det är alltså inte veckans stängningspris söndag 24:00 utan ett pris några timmar in i nästa vecka. Den
  som jämför med en annan källas veckovärde ska räkna med den förskjutningen.
- **Urvalsbias i Manifold-historiken (R3, rättat i X2):** varje dygnsvärde är rätt i tid, eftersom det räknas om ur
  handeln. Men frågorna valdes ut den 2026-11-23 med metadata som bara var känd då (minst 100 unika handlare,
  livslängd minst 180 dagar, inte avgjord som CANCEL), och 14 av 17 var redan avgjorda. Att en fråga finns med beror
  alltså på vad som hände senare. Rader med `known_from` före frågans `selected_on` märks därför
  `source="backfill"`, som all historik som laddats i efterhand, och rader från urvalsdagen och framåt `release`
  (`sources/forvantningar.flag_preselection`). **Regel inför grind G-A:** mått på mängdnivå i G9 (antal frågor,
  medel över frågor, spridning) får bara använda rader med `source != "backfill"`, alltså frågor från och med deras
  urvalsdag. Backfill-raderna får användas per fråga, till exempel för att visa en enskild frågas historik, men inte
  i en `as_of`-vy av G9 som helhet före urvalsdagen och inte i en backtest av G9-aggregat. Nya urvalsomgångar får
  sitt eget `selected_on`, så regeln gäller per omgång.
- **Kontroll:** för de öppna Manifold-frågorna stämmer det senaste dygnsvärdet med API:ts aktuella `probability`
  (skillnaden var 0 för en fråga, och de andra skilde sig bara genom dagens handel efter dygnsskiftet).
  Alla värden ligger i [0, 1].
- **Avslutad:** en fråga som inte längre är `open` i urvalsfilen, eller vars planerade stängning har passerat, får
  `closed=True` och inget aktualitetskrav. `python -m ai_tracker.sources.forvantningar status` uppdaterar status och
  stängningsdatum ur plattformens metadata. Den läser aldrig priser. En fråga som avgörs i förtid fångas av
  aktualitetskontrollen tills status har uppdaterats.
- **Inga takter och inga jämförelser mot utfall** här. Serierna är inte kärnserier förrän grind G-A.

## 4. Villkor per plattform

| Plattform | Villkor (citat eller källa) | Bedömning |
|---|---|---|
| Manifold | Den officiella villkorssidan (`docs.manifold.markets/terms`, `/data`) nås inte från sessionen. En kopia av API-dokumentationen hos tredje part säger att användningen omfattas av deras Terms of Service, att akademisk forskning, personliga projekt och icke-kommersiell användning är tillåtna, och att kommersiell AI/ML-träning kräver licens. Det är inte verifierat mot originalet | `unverified`, `publish=False`. Insamling via det öppna API:t, med ärlig User-Agent och under deras gräns på 500 anrop per minut |
| Polymarket | `polymarket.com` (villkoren) och `docs.polymarket.com` nås inte. Gamma-API:t är öppet och kräver ingen nyckel | `unverified`, `publish=False` |
| Kalshi | Kalshi Developer Agreement v1.1 (kalshi-public-docs.s3.amazonaws.com, läst 2026-11-23): "Use of Kalshi APIs is expressly limited to facilitating a members own trading on the Exchange; all other usages are disallowed", och 3.1 förbjuder "Collecting, caching, aggregating, or storing data or content accessed via the API except for purposes of facilitating your own trading on Kalshi. You may not share such data or content with third parties in any manner without prior written authorization from Kalshi." | **Utesluten.** Ingen data hämtas eller lagras. Det kan prövas igen om Kalshi publicerar separata villkor för marknadsdata eller ger skriftligt tillstånd |
| Metaculus | API:t svarar: "The API is only available to authenticated users. Please create an account and use your API token to access the API." Webbsidorna, villkoren inräknade, ligger bakom en Cloudflare-kontroll ("Just a moment..."), och den kringgås inte. Enligt sekundära källor kräver kommersiell användning avtal och förbjuder villkoren användning av data för att träna eller utvärdera AI-modeller. Det är inte verifierat | **BLOCKED** |

`publish=True` kräver att villkoren lästs i original. För Manifold och Polymarket behövs att värdarna
`docs.manifold.markets` och `polymarket.com` släpps igenom, så att villkoren kan läsas och citeras.

## 5. BLOCKED och vad som behövs

- **Metaculus:** ett konto och en API-token, `METACULUS_API_TOKEN` i `.env`, och dessutom villkoren lästa i original
  (sidan bakom Cloudflare). Regeln för Metaculus finns redan i avsnitt 1: binära frågor och datumfrågor, minst 100
  prognosmakare och samma ämnen. Klienten byggs när token finns. Serien blir då gemenskapens median eller sannolikhet
  (`recency_weighted`) med historik, där `known_from` är aggregatets tidsstämpel avrundad uppåt till dygnets slut.
  `http.get` behöver då kunna skicka en `Authorization`-header.
- **Polymarket-historik:** värden `clob.polymarket.com` (`/prices-history`). Med den kan historiken fyllas i för de
  valda marknaderna, och regeln kan då också ta med avslutade Polymarket-frågor.
- **Kalshi:** utesluten av villkoren (avsnitt 4), inte av nätet.
- **Villkorssidor:** `docs.manifold.markets`, `manifold.markets` och `polymarket.com` behövs för att kunna sätta
  `publish=True`.
