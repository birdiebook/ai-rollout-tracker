# R8 – granskning av pris vid fast Arena-förmåga (G2A)

Granskningsspår R8, 2026-11-24, gren `auto11/r8-g2-arena`. Granskat: `g2_price_at_arena_capability` (A, referens
`gpt-4-0314`, från 2024-01) och `g2_price_at_arena_capability_4o` (B, referens `gpt-4o-2024-05-13`, från 2024-05),
byggda av G2A (`src/ai_tracker/series/arena_price.py`, `src/ai_tracker/sources/arena_map.py`,
`litellm_prices.deprecations()`, dokumentation `docs/kallor/g2_arena_pris.md`).

Underlag: G2A:s cachar (LiteLLM-ögonblicksbilder och avvecklingsdatum, Arena Space-filer och datasetets git-logg),
Arena-datasetets `text/full` i dagens version och två äldre revisioner (`a220136`, 2026-07-03, och `5537eec`,
2026-09-26) som hämtades från Hugging Face för revisionskontrollen, LiteLLM:s prisfil vid commit `28c33f53`
(raw.githubusercontent.com) och OpenRouters öppna modell-API. Blockerade värdar: `mistral.ai`, `docs.mistral.ai`,
`web.archive.org` och `archive.org` (proxyn nekar).
Serierna byggdes om offline med G2A:s kod. Värdena stämmer rad för rad med G2A:s dokumentation (34 respektive
30 rader, alla `release`, `known_from` = månadsslut + 1 dag).

**Ingen analys av förlopp gjordes utöver vad punkt 5 kräver.** Halveringstiderna nedan räknades bara för att
avgöra om tillståndsmotorns takt är meningsfull på serien. De är inte resultat.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering | **OK** |
| 2. Namnkoppling | **Anmärkning**, med två prisfel i LiteLLM som sätter minimum och en inkonsekvent aliasregel |
| 3. Avvecklingsregeln | **Anmärkning**. Regeln är motiverad, men den påverkar inte takten alls, och den ska registreras som ändring |
| 4. Datering och läckage | **OK för serien.** **Fel i `arena.py`**: en omladdad tavla dateras till första commit fast värdena är från den senare. Mistral Small 3.2:s pris går inte att verifiera |
| 5. Robusthet och takt | **Fel (validitet).** Tröskeln binder inte. Takten bestäms av ett fåtal prissteg, och i A av ett enda pris som inte går att verifiera |
| 6. A eller B | Ingen som kärnserie nu. Efter rättning: **B** |

**Slutdom: UNDERKÄND som kärnserie i G2 i nuvarande form.** Serierna är korrekt daterade och kan finnas kvar som
beskrivande serier (`publish=True` är förenligt med licenserna). Rättningarna R-1 till R-9 nedan behövs innan en
ny registrering prövas. Registreringen ändrar inte grenens tillstånd i dag: G2 har en kärnserie, med A eller B
blir det två, och det krävs tre (`MIN_SERIES`).

## 1. Förregistrering – OK

Ordningen enligt git (alla 2026-11-24, UTC):

| Tid | Commit | Innehåll |
|---|---|---|
| 16:39 | `ca5b0c6` (G12) | Förslaget med båda referenserna och regeln om fast referens i samma tavla. Bara täckning räknades (406 kvalificerade namn, 102 med exakt namnmatchning). Inga priser |
| 18:19 | `e4188f9` | Beslutsloggen: ett G2-spår beslutas |
| 18:25 | `f5c503c` | Referensregeln låses i `docs/kallor/g2_arena_pris.md` avsnitt 1. Ingen kod för serien finns |
| 18:33 | `3f55a7e` | Koppling, seriekod och tester. Första möjliga värden |
| 18:47 | `6047658` | Avvecklingsregeln (avsnitt 2, ny) och dokumentation |
| 18:47 | `e1fae0b` | Effekten av avvecklingsregeln redovisas |

- `git diff f5c503c HEAD -- docs/kallor/g2_arena_pris.md` lägger bara till avsnitt 2–6. Avsnitt 1 är oförändrat.
  Referenserna, efterföljarkedjorna, den inklusiva tröskeln och regeln för bästa variant är desamma i koden
  (`CHAINS`, `TOL`, `key_capability`).
- Referenserna valdes av G12 innan G2A började, efter metadata (lanseringsmodell och etta i tavlan) och inte
  efter priser. G12 räknade antalet kvalificerade namn mot `gpt-4-0314`. Det är täckning och inte utfall.
- Begränsning: git visar bara att inga värden *committades* före 18:33, inte att inga räknades lokalt. Inget i
  G12:s eller G2A:s filer tyder på att de gjorde det.
- Den enda ändringen av beräkningen efter första bygget är avvecklingsregeln (punkt 3). Den står öppet som
  ändring i avsnitt 2, men den finns inte i `docs/mattregister.md` (R-7).

## 2. Namnkoppling – anmärkning

`arena_map.problems()` är tom. Alla kopplade nycklar finns i LiteLLM:s historik, med samma `litellm_provider` som i
kopplingen, och alla kopplade namn finns i någon BT-tavla. `coverage()` ger noll ogranskade namn i båda varianterna.

### Stickprov (21 kopplingar, alla som sätter minimum i någon månad först)

| # | Arena-namn | Nyckel | Pris in/ut (LiteLLM) | Bedömning |
|---|---|---|---|---|
| 1 | `gpt-4-turbo` (2024-01) | `gpt-4-1106-preview` | 10/30 | OK. Arenas namn före 2024-02-02 är 1106-förhandsversionen. Bytet syns i tavlorna |
| 2 | `gpt-4-0125-preview` | samma | 10/30 | OK |
| 3 | `claude-3-sonnet-20240229` | samma | 3/15 | OK |
| 4 | `claude-3-5-sonnet-20240620` | samma | 3/15 | OK |
| 5 | `deepseek-v2-api-0628` | `deepseek-chat` från 2024-06-28 | 0,14/0,28 | OK. V2-prislistan. Datumet kommer från versionsnamnet, inte från ett läst release-dokument (det är blockerat) |
| 6 | `gemini-1.5-flash-api-0514` / `-001` | `gemini/gemini-1.5-flash-001` | 0,075/0,30 | OK. Arena bytte själv namn utan överlapp, så det är samma post |
| 7 | `gemini-1.5-flash-002` | samma | 0,075/0,30 | OK |
| 8 | `gemini-2.0-flash-lite-preview-02-05` | samma | 0,075/0,30 | OK. Förhandsversionen hade betalpris |
| 9 | `gpt-5-nano-high` / "GPT-5 nano (High)" | `gpt-5-nano-2025-08-07` | 0,05/0,40 | OK enligt regeln om bästa variant, men se punkt 5 (hög resonemangsnivå ger många fler tokens per svar) |
| 10 | `mistral-small-2506` | `mistral/mistral-small-3-2-2506` | 0,06/0,18 | Kopplingen är OK. **Priset går inte att verifiera** (punkt 4) |
| 11 | `gpt-4o-2024-05-13` | samma | 5/15 | OK |
| 12 | `o1-mini` | `o1-mini-2024-09-12` | 3/12 | OK. Det fanns bara en ögonblicksbild |
| 13 | `gemini-1.5-pro-002` | `gemini/gemini-1.5-pro-002` | 3,5/10,5 | Kopplingen är OK. **Priset är fel från 2024-10-01** (se nedan) |
| 14 | `deepseek-v3` | `deepseek-chat` från 2024-12-26 | 0,14/0,28 | OK. Kampanjpriset gällde till 2025-02-08 |
| 15 | `o3-mini-high` | `o3-mini-2025-01-31` | – | OK. Det är en resonemangsnivå |
| 16 | `mistral-medium` | `mistral/mistral-medium-2312` | – | OK. Arenas post är modellen från december 2023 |
| 17 | `gemini-2.5-pro-exp-03-25` | `gemini/gemini-2.5-pro-preview-03-25` | – | Godtagbart, eftersom Google anger samma modell. Det är ett undantag från regeln att `-exp-` inte kopplas, och undantaget ska stå i dokumentationen |
| 18 | `gemini-3-pro` | `gemini/gemini-3-pro-preview` | – | OK enligt `model_map` |
| 19 | `grok-4-fast-chat` | `xai/grok-4-fast-non-reasoning` | 0,20/0,50 | Rimligt. Den kunde inte beläggas på nytt. Den sätter inte minimum |
| 20 | `kimi-k2.5-instant` / `-thinking` | `moonshot/kimi-k2.5` | – | OK |
| 21 | `qwen-plus-0125` | `dashscope/qwen-plus-2025-01-25` | – | OK |

Stickprovet hittade ingen felkoppling i storlek eller version, ingen förhandsversion kopplad till GA eller tvärtom
(förutom nr 17, som är belagd), och inget batch-, cache- eller rabattpris. `extract()` läser bara
`input_cost_per_token` och `output_cost_per_token`. Kontroller av `no_key`: LiteLLM har inga förstapartsnycklar för
Gemini 1.5 Flash-8B, Mistral Small 2501/2503 eller GLM-4.7-Flash (bara Bedrock och Azure). Klassningen stämmer.

### Fel och anmärkningar

- **F-2a. Prisfel i LiteLLM sätter minimum i B 2024-10 och 2024-11.** `gemini/gemini-1.5-pro-002` står på
  3,50/10,50 USD under hela sin livslängd i LiteLLM. Google sänkte 1.5 Pro till 1,25/5,00 (≤ 128k) från
  2024-10-01. Värdet blir 5,25 i stället för 2,1875 (faktor 2,4). Avsnitt 4 i G2A-dokumentet säger att "alla
  priser ovan stämmer med utvecklarnas listpriser enligt LiteLLM:s `source`". Det är cirkulärt, eftersom
  `source` bara är en länk och inte en kontroll.
- **A-2b. LiteLLM släpar efter i A 2024-08.** Googles sänkning av 1.5 Flash (2024-08-12) syns först 2024-09-15.
  Den daterade nyckeln `-001` finns från 2024-09-15, så 2024-06 – 08 har ingen prissatt 1.5 Flash.
- **A-2c. Aliasregeln är inkonsekvent.** DeepSeeks alias kopplas per version (`ROLLING`). Det odaterade
  `gemini/gemini-1.5-flash` (från 2024-06-21) räknas som "alias som byter modell" och kopplas inte, fast
  Google dokumenterar att det pekade på `-001` tills `-002` kom. Kopplas det som `ROLLING` för perioden
  2024-05-24 – 2024-09-23, blir A 2024-06 0,525 i stället för 6,00 (faktor 11). Övriga månader ändras inte
  (kört).

## 3. Avvecklingsregeln – anmärkning

**Är den motiverad oberoende av utfallet?** Ja, i sak. Värdet ska vara det lägsta pris som förmågan *går att köpa
för*. En pensionerad modell har inget pris, så att räkna den är ett datafel och inget metodval. Regeln gäller alla
nycklar och båda varianterna, och den använder bara metadata som fanns i filen vid månadsslut. Det senare
verifierades: `deprecation_date` för `gemini-1.5-flash-001` (2025-05-24) finns i filen från ögonblicksbilden
2025-01-31, alltså tidigare än G2A:s "senast 2025-03-08". Ett datum som läggs till först efter månadsslutet
påverkar inte månaden (nytt test). Regeln höjer värdet, vilket inte gynnar någon viss berättelse.

**Garden of forking paths?** Ja, i begränsad mening. Regeln infördes efter att G2A sett vilken modell som satte
minimum, och den är en av flera möjliga implementeringar: LiteLLM:s `deprecation_date` vid månadsslut,
utvecklarens faktiska avstängningsdatum, eller att nyckeln tas bort ur LiteLLM. Den valda varianten är den enda som
är ärligt daterad utan extra källor, så valet är försvarbart. Men det ska stå som en ändring efter första bygget.

**Effekt (körd med och utan):**

| | A | B |
|---|---|---|
| Månader med annan modell vid minimum | 2025-05 – 2026-02, 2026-08 | 2026-01, 2026-02, 2026-08 |
| Månader med annat värde | 2026-01, 2026-02 (0,1375 i stället för 0,13125, +4,8 %), 2026-08 (0,1375 i stället för 0,09, +53 %) | samma |
| Halveringstid (tillståndsmotorns takt), alla månader | **identisk** | **identisk** |

Takten påverkas inte, eftersom G2:s registrerade front är löpande minimum (`cummin`, `measures.py`). Fronten tar
tillbaka priset för den pensionerade modellen. Mistral Small 3.2 (0,09 från 2026-03, pensionerad 2026-07-31)
ligger kvar i fronten för alltid. Regeln ändrar alltså bara de nivåer som visas, inte det som räknas. Det
motsäger regelns syfte och gäller hela G2-metoden, inte bara den här serien (R-6).

**Rekommendation:** behåll regeln. Registrera den i `docs/mattregister.md` som ändring 2026-11-24 "efter första
bygget, före analys av takt, utlöst av en nivåkontroll", och ange effekten ovan. Avgör i registret om samma regel
ska gälla `g2_price_at_capability*` (I6). Två regler för pensionerade modeller i samma gren ska inte finnas utan
motivering. Lägg också till att LiteLLM inte alltid anger pensionering, så en pensionerad modell utan datum räknas
fortfarande.

## 4. Datering och läckage – OK för serien, fel i `arena.py`

**Serien:** varje rad har `known_from` = max(tavlans belägg, månadsslut + 1 dag). Alla 64 rader är första
versioner med `known_from` = månadsslut + 1 dag. Det finns inga `backfill`-rader. Bulktavlorna (belagda
2026-04-02) för 2025-09 – 2026-03 ändrade inget värde, vilket bekräftades genom omkörning. Priser och
avvecklingsdatum tas från ögonblicksbilden vid månadsslut. Ögonblicksbildens datum är UTC-datumet för committern
på `main`:s first-parent-kedja (tidpunkten för merge), och urvalet är sista commit per vecka och månad. Det är
konservativt. En tavla som beläggs efter månadsslut ger en ny version men byter aldrig pris (nytt test).
Efterföljarnas offset räknas bara ur tidigare, kända tavlor och har aldrig använts. Datumen i `ROLLING` och
slutet `_DS_END` är historiskt kända eller konservativa.

**Arenas omräkning:** varje tavla är en egen ögonblicksbild med publiceringsdatum. Värden från senare tavlor används
inte för tidigare månader. **Men datasetet har skrivits om en gång.** Den 2026-07-07 laddades 16 text-tavlor
(2026-04-30 – 2026-07-02) upp på nytt under samma commit-titel. `parse_dataset_log` daterar en tavla till
*första* titlade commit, medan `subset_boards` läser värdena i dagens version. Jämförelsen med revision
`a220136` (2026-07-03) visar att 15 av tavlorna är identiska. **Tavlan 2026-06-10 ändrades:** 670 av 1 036 rader
har nya värden, med skillnader upp till 129 poäng (till exempel `granite-4.1-8b` 1 421 → 1 292). Tavlan dateras
2026-06-11, men värdena var kända först 2026-07-07. Det är läckage i `arena.py` (G12-kod). Det påverkar inte de här
serierna, eftersom 2026-06 använder tavlan 2026-06-25 och referensernas ratingar är oförändrade. Det påverkar inte
heller `g1_arena_*` i dag. Men felet slår igenom vid nästa omladdning. Revisionen `5537eec` (2026-09-26) är
identisk med dagens version för alla tavlor till och med 2026-09-25. (F-4a, strikt xfail-test i
`tests/test_r8_g2_arena.py`.)

**Mistral Small 3.2:**
- Nyckeln `mistral/mistral-small-3-2-2506` finns i LiteLLM först från 2026-03-07, med 0,06/0,18 och
  `source: https://mistral.ai/pricing`. Commit `28c33f53` heter "CircleCI test stability (#23055)", alltså en
  prisändring buntad i en orelaterad PR. I samma commit ändrades `mistral/mistral-small-latest` från 0,10/0,30
  (sedan 2025-03-14) till 0,06/0,18. Avvecklingsdatumet 2026-07-31 kom in först 2026-08-16.
- Modellen finns i Arena från tavlan 2025-07-07 (1 332 mot tröskeln 1 202). Den kvalificerade alltså i åtta månader
  innan den fick ett eget pris.
- Verifiering: `mistral.ai` och Wayback är blockerade. OpenRouter listar i dag Mistral Small 3.2 bara hos tredje
  part (DeepInfra 0,06/0,16 och 0,075/0,20, Venice 0,075/0,20, Parasail 0,09/0,30), inte hos Mistral. För Mistrals
  egna modeller som fortfarande säljs (`mistral-small-2603` 0,15/0,60, Ministral 3) stämmer OpenRouter med
  LiteLLM. Priset 0,06/0,18 kan alltså vara en verklig sänkning hos Mistral eller ett tredjepartspris. **Det gick
  inte att avgöra.**
- Datering: priset är ärligt daterat som "känt i LiteLLM", så det finns inget läckage. Om sänkningen var verklig och
  skedde tidigare, släpar serien. Om priset är fel, är 2026-03 – 07 fel: 0,09 i stället för 0,1375 (−35 %).

## 5. Robusthet och takt – fel (validitet)

Känslighetskörningar med G2A:s kod. Värdet är den första versionen per månad. Halveringstiden räknas med
tillståndsmotorns regel (löpande minimum, log-linjär regression över 24 månader).

| Fall | Ändrade värden | Halveringstid 2026-10 (månader) |
|---|---|---|
| A som byggd | – | 33,0 |
| B som byggd | – | 11,0 |
| A utan avvecklingsregel | 2026-01, 02, 08 | 33,0 (identisk i alla månader) |
| A, tröskel −10 poäng | 2024-03 – 06: 6,00 → 0,50 (Claude 3 Haiku, 5,6 poäng under tröskeln i 2024-03) | 33,0 |
| A, tröskel +25 | 2024-03 – 05: 6 → 15 eller 7,5 | 33,0 |
| B, tröskel +10 | 2024-05 – 08 saknar värde (bara referensen kvalificerar). Lucka i fönstret | 11,0 |
| B, tröskel −25 | 2024-06 – 11 sjunker kraftigt | 33,0 |
| A och B, Mistral Small 3.2 på 0,10/0,30 | 2026-03 – 07: 0,09 → 0,1375 | **A: ingen takt (lutningen är 0)**, B: 16,5 |
| B, Gemini 1.5 Pro 002 på Googles pris | 2024-10 – 11: 5,25 → 2,1875 | 12,8 |
| A, alias för 1.5 Flash (A-2c) | 2024-06: 6,00 → 0,525 | 33,0 |

Fynd:

1. **Tröskeln binder inte.** Från 2024-07 (A) och 2025-02 (B) är seriens värde detsamma som det lägsta priset bland
   *alla* kopplade modeller i tavlan, utan tröskel (kört). Modellen vid minimum ligger 40–130 poäng över tröskeln i
   A och 20–40 poäng i B. Serien mäter alltså golvet i förstapartsprislistornas billigaste nivå ("flash", "nano",
   "small"), inte priset vid en fast förmåga. Trösklarna är irrelevanta från dessa datum, och **A och B har samma
   värden från 2025-02**, inte från 2025-09 som dokumentet säger.
2. **Serien är en stegfunktion.** A har 6 nivåer på 34 månader och B 6 på 30, och varje steg är en enda modells
   inträde, prisändring eller pensionering. Halveringstiden i A var 3,5 månader 2025-12 och 37–39 månader under
   2026-06 – 08. Ökningen är mekanisk: fönstret lämnar 2024 års fall från 15 till 0,13. Fram till 2026-07 kommer
   all lutning från 2024, och därefter bara från ett steg (Mistral 2026-03). Förändringen i takt, och därmed
   riktningen med dödzonen 0,25 SD, mäter alltså när stegen hamnar i fönstret, inte en förändring i takt. G12 avvisade
   AWS-listpriserna med samma argument ("halveringstiden skulle bara spegla om steget ligger i fönstret").
3. **Ett pris som inte går att verifiera bär A:s takt.** A:s halveringstid från 2026-08 (33–39 månader) kommer
   helt från Mistral Small 3.2:s pris på 0,06/0,18. Med 0,10/0,30 finns ingen takt alls. I B ändras takten från
   11,0 till 16,5.
4. **2024 är skört i båda varianterna.** I A avgör 6 poäng, väl inom Arenas osäkerhetsintervall, om 2024-03 – 06
   ligger på 6,00 eller 0,50. I B kvalificerar bara referensen 2024-05 – 08, så värdet är referensens eget pris,
   och 2024-10 – 11 bärs av LiteLLM-felet F-2a. Den inklusiva tröskeln tar inte hänsyn till osäkerhetsintervallen.
5. **Saknade priser:** golvet kan bara sänkas av modeller som är kopplade och prissatta. Täckningen är 50 % (A) och
   57 % (B) av API-namnen, och öppna modeller och utvecklare utanför förstapartsregeln saknas. Det billigaste
   förstapartspriset förklarar nivån, men en saknad billig nyckel, som 1.5 Flash 2024-06, kan flytta en månad med en
   faktor 10.
6. **Pris per token vid hög resonemangsnivå.** `gpt-5-nano-high` sätter minimum 2026-01 – 02 och 2026-08 – 10 med
   priset per token. Nivån "high" använder många fler tokens per svar, så kostnaden för förmågan underskattas mer
   ju mer resonemang som krävs för att nå tröskeln. Begränsningen står i avsnitt 6.6 i G2A-dokumentet, men den slår
   igenom just på de modeller som sätter minimum.
7. **Tillståndsmotorn:** G2 har i dag 1 kärnserie, och A eller B ger 2. Det krävs `MIN_SERIES = 3`, så grenen visar
   index men inget tillstånd i båda fallen. Registreringen påverkar alltså bara seriens egen rad (takt, percentil,
   riktning), och den raden är enligt 2–3 inte meningsfull.

## 6. A eller B – ingen nu, B efter rättning

- Valet påverkar bara 2024 och början av 2025. Från 2025-02 är A och B identiska, så från 2027-01 har de samma
  24-månadersfönster och samma takt.
- **A:s** längre historik är just den del som är skör: tröskelkänslig 2024-03 – 06, aliasluckan 2024-06, och ett
  fall från 15 till 0,13 som dominerar takten till 2026-07. Tröskeln binder inte från 2024-07.
- **B** binder längre (till 2025-01) och har högre täckning (57 %). Dess svagheter (bara referensen 2024-05 – 08,
  F-2a) går att rätta eller avgränsa.
- Rekommendation: om G2 ska ha en Arena-serie, välj **B**, med start 2024-09 (den första månaden med mer än en
  kvalificerad modell). B är en ny registrering och ska göras först när R-1 – R-5 är klara. Då ska också prövas om
  den rättade serien har någon takt som inte bara speglar enskilda steg. Om den inte har det, bör ingen av
  varianterna bli kärnserie.

## Rättningar (för ett rättningsspår)

| # | Var | Rättning |
|---|---|---|
| R-1 | `arena.py` `parse_dataset_log`/`boards` | En tavla ska dateras till den commit vars rader är de som används. Enklast och konservativt: senaste titlade commit (`max` i stället för `min`). Bättre: jämför revisionerna och skapa en ny version där raderna ändras. Gäller även `g1_arena_*`. Det strikta xfail-testet i `tests/test_r8_g2_arena.py` slår om när felet är rättat |
| R-2 | `arena_price.py` / ny prisövergång | Inför en lista över prisrättningar med belägg (utvecklarens prisnyhet och datum) för nycklar som sätter minimum. Den första posten är `gemini/gemini-1.5-pro-002` (och `-001`) med 1,25/5,00 från 2024-10-01. Rättningar dateras till sitt beläggs datum, aldrig tidigare |
| R-3 | dokumentation och kontroll | Ersätt påståendet "alla priser stämmer enligt `source`" med en riktig kontroll per pris vid minimum: utvecklarens prissida eller prisnyhet, med datum. Det som inte går att kontrollera markeras som overifierat |
| R-4 | Mistral Small 3.2 | Verifiera 0,06/0,18 mot Mistral (prisnyhet eller Wayback utanför sandlådan). Gick det inte, flagga 2026-03 – 07 som overifierade och redovisa serien med och utan nyckeln |
| R-5 | `arena_map.py` `ROLLING` | Behandla Geminis odaterade alias som DeepSeeks, med Googles dokumenterade versionsdatum (`gemini/gemini-1.5-flash` → `-001` 2024-05-24 – 2024-09-23, och `gemini/gemini-1.5-pro` på samma sätt), eller skriv i dokumentationen varför Google och DeepSeek behandlas olika |
| R-6 | `docs/mattregister.md` (registerbeslut) | Avgör om G2:s front (löpande minimum) ska bortse från pensionerade modeller. I dag tar fronten tillbaka det som avvecklingsregeln tog bort. Det är en metodändring för G2 och ska förregistreras före analys |
| R-7 | `docs/mattregister.md` | Registrera avvecklingsregeln som ändring 2026-11-24 med motiveringen och effekten i punkt 3, och avgör om den ska gälla även `g2_price_at_capability*` |
| R-8 | `docs/kallor/g2_arena_pris.md` | Rätta "från 2025-09 i praktiken samma serie" till "samma värden från 2025-02". Lägg till att tröskeln inte binder från 2024-07 (A) och 2025-02 (B), redovisa nivåkontrollen utan tröskel, nämn undantaget för `gemini-2.5-pro-exp-03-25` och ange att Arenas osäkerhetsintervall inte används |
| R-9 | registreringsbeslutet | Registrera inte A. Pröva B (från 2024-09) först efter R-1 – R-5, och bara om den rättade serien har en takt som inte beror på ett enskilt prissteg |

## Tester

`tests/test_r8_g2_arena.py` (fixturer, inget nät):
- ett avvecklingsdatum som läggs till efter månadsslut påverkar inte månaden (passerar)
- en tavla som beläggs senare ger en ny version men aldrig ett senare pris (passerar)
- en tavla som laddats upp igen ska dateras till den commit som har värdena (strikt xfail, R-1)

`python -m pytest -q tests/test_r8_g2_arena.py tests/test_arena_price.py`: 18 passerade, 1 xfail. Hela sviten:
se slutrapporten.
