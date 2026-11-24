# Nya källor för G1 (förmåga) och G2 (kostnad), spår G12

Steg 2, spår G12, 2026-11-24. Problemet: G1 och G2 har för få serier med ärlig `known_from` för att få ett
tillstånd (minst 3 räknade serier). Spåret bygger fria källor med ärliga tidsstämplar, i första hand git-historik
och daterade publiceringar, och föreslår kärnserier. **Inga takter, trender eller jämförelser har beräknats.**
Kontrollerna nedan gäller bara datakorrekthet och datering.

Kod: `src/ai_tracker/sources/{arena,swebench,aws_gpu,vintages}.py`, serier i
`src/ai_tracker/series/{arena,swebench,aws_gpu,price_capability_provider}.py`, tester i
`tests/test_g12_g1.py` och `tests/test_g12_g2.py` (fixtures, inget nätverk).

## Sammanfattning

| Serie | Gren | Från | Regel för `known_from` | Licens | Publiceras |
|---|---|---|---|---|---|
| `g1_arena_text_top` | G1 | 2023-05 | månadsslut + 1 dag, eller senare commit i Arenas HF-Space eller HF-dataset | CC BY 4.0 | ja |
| `g1_arena_text_sc_top` | G1 | 2024-08 | som ovan | CC BY 4.0 | ja |
| `g1_arena_text_top_gap_ref` | G1 | 2023-12 | som ovan | CC BY 4.0 | ja |
| `g1_arena_webdev_top` | G1 | 2025-11 (ärligt från 2026-04) | som ovan | CC BY 4.0 | ja |
| `g1_swebench_verified_top` | G1 | 2024-10 | månadsslut + 1 dag, tavlan enligt sista commit på `main` ≤ månadsslut | ingen licensfil | nej |
| `g2_aws_a100_gpu_hour` | G2 | 2020-11 | månadsslut + 1 dag, senaste prisliste­version med publiceringstid ≤ månadsslut | AWS-villkor, ingen öppen licens | nej |
| `g2_aws_h100_gpu_hour` | G2 | 2023-08 | som ovan | som ovan | nej |
| `g2_price_at_capability_gpqa_{openai,anthropic,gemini,deepseek}` | G2 | 2025-03 / 2025-03 / 2025-04 / 2026-01 | månadsslut + 1 dag; GPQA-körning räknas från `Started at` + 30 dagar | MIT + CC BY 4.0 | ja |

Alla serier är månadsserier med release-daterade rader (`source="release"`), utom Arena-tavlor som bara finns i
datasetets bulkuppladdning (`source="backfill"`, se nedan). Den gemensamma regeln finns i `sources/vintages.py`:
månad m får värdet från det senast publicerade läget med publiceringsdatum ≤ månadens slut bland de lägen som var
dokumenterade då. Första versionen får `known_from` = månadsslut + 1 dag (samma marginal som de registrerade
G2-serierna). Ett läge som publicerades före månadsslutet men bara kan beläggas senare ger en ny version på
beläggets datum. Ingenting dateras bakåt.

## Arena (LMArena), G1

### Källor och belägg för datering

1. **HF-datasetet `lmarena-ai/leaderboard-dataset`** (`full`-split = alla publicerade topplistor, kolumnen
   `leaderboard_publish_date`). Datasetet skapades **2026-04-02** ("initial commit", 29 commits "add historical
   data" kl. 19:50 UTC), och därefter kommer varje topplista i en commit med titeln "Update <delmängd> for <datum>".
   Kontrollerat 2026-11-24: alla 66 publiceringsdatum från 2026-04-02 i `text` och `text_style_control` och alla 89 i
   `webdev` har en sådan commit, 0–9 dagar efter publiceringsdatumet (median 1). Raderna för de 195 äldre datumen
   var identiska i revisionen från 2026-04-03 (`676db8d`) och i dagens.
2. **Den gamla Spacen `lmarena-ai/arena-leaderboard`**, med `elo_results_YYYYMMDD.pkl` committade löpande
   2023-05-20 – 2025-09-03 (322 commits). Det är de kompletta publicerade tabellerna. Belägget är den första commit
   som lade till filen (UTC-datum), median 1 dag och högst 26 dagar efter tavlans datum.

**Viktigt fynd: datasetets bakåtfyllda historik är censurerad.** Modeller som senare bytt namn eller tagits bort
saknas i de gamla tavlorna. Exempel: 2024-01-09 saknar `gpt-4-turbo` (etta i den publicerade tavlan, 1 249,3), så
datasetets etta är `gpt-4-0314` (1 190,5). 2023-05-08 saknar alla proprietära modeller (`gpt-4`, `claude-v1`), så
datasetets etta är `vicuna-13b`. De rader som finns är däremot exakt lika med de publicerade (största avvikelse
0,0 mot Space-filerna 2024-01-09, 2024-03-05, 2024-06-11, 2025-08-04 och 2025-08-29). Datasetet ensamt duger alltså
inte för fronten före 2026-04.

### Val per topplista

För varje (delmängd, publiceringsdatum):
- **Space-filen** (samma datum eller en dag ifrån), om en av dess tabeller är exakt lika med datasetets
  `overall`-rader det datumet på alla gemensamma modeller (minst 5). Matchningen avgör vilken tabell Arena själv
  räknar som publicerad `overall`: `elo_rating_median` (2023-05 – 2023-11), `elo_rating_online` (2023-12),
  `elo_rating_final` (2024-01-09 – 2024-03-26), `full` eller `full_old` (2024-03 – 2024-06) och `text/full` eller
  `text/full_style_control` (från 2024-06-29). Datering = Space-commit, `source="release"`.
- Space-filer utan lika datasetdatum (2025-08-08, 08-15, 08-22, 08-29: datasetet har 08-07, 08-14, 08-21, 08-28 med
  andra värden) tas med som egna tavlor, med den tabell som den senaste tidigare matchade filen använde. De lades
  till 2025-09-03.
- Annars **datasetet** med titlad commit som belägg (`release`), och om ingen finns **bulkuppladdningen** med
  belägg 2026-04-02 (`backfill`, censurerad). Omskrivna tavlor får en version per ändring (nästa avsnitt).

Utfall för `text` (260 datasettavlor + 4 Space-tavlor): 136 från Spacen (2023-05-08 – 2025-08-29), 66 från datasetet
med commit (2026-04-02 –) och 62 bara från bulkuppladdningen (2025-08-07 – 2026-03-31). För månaderna 2025-09 –
2026-03 är alltså det som var känt vid månadsslut tavlan från 2025-08-29, och de bakåtfyllda tavlorna ger en
`backfill`-version daterad 2026-04-02. Det är ärligt men grovt: Arenas webbplats publicerade löpande, men den är
blockerad i sandlådan och har inga arkiverade versioner som vi kan belägga.

**Pickle-filerna** läses med en begränsad unpickler (`arena.safe_load`): varje global som filen namnger ersätts av
en ofarlig stub, så ingen kod ur filen körs (testat med en fil som försöker anropa `os.system`). Tabellerna byggs
upp från de råa numpy-buffertarna.

### Omskrivna tavlor: versioner per commit (rättning X5, 2026-11-24)

Granskningen R8 (F-4a) fann att datasetet skrivs om på plats. Kontroll av alla commits som rör delmängdens fil
(`git log -- <delmängd>/full-00000-of-00001.parquet`):

- **2026-07-07:** 16 `text`- och 16 `text_style_control`-tavlor (2026-04-30 – 2026-07-02) laddades upp igen under
  samma titel. Innehållet ändrades inte (jämfört med revisionen före, `a220136` och `2a01fee`).
- **2026-07-29**, commit `b0e3f09` "Remove erroneously published variant rows from text" (ingen titel per tavla):
  sex `text`-tavlor (2026-06-10, 07-14, 07-20, 07-21, 07-26, 07-27) hade upp till sex rader per modell. Toppen
  sjönk med cirka 10 poäng, till exempel 2026-07-27 från 1 521,5 till 1 511,6. R8:s jämförelse (`a220136` mot
  dagens version) fångade 2026-06-10 men inte de fem juli-tavlorna, eftersom de kom efter `a220136`.
- **webdev 2026-04-14** har fem titlade commits, men bara två rör filen. Innehållet är lika.

**Regel:** en tavla har en version per ändringspunkt. Ändringspunkter är senare titlade commits för tavlan och
otitlade commits efter bulkuppladdningen (de kan röra alla tavlor). Varje version läses ur en sparad revision av
filen (`arena.version_plan`, som väljer så få revisioner som möjligt, i dag 2 för `text`, 1 för stilkontroll och
1 för webdev), dateras till den commit som inleder den och slås ihop med föregående version om raderna är lika.
Raderna i HEAD dateras aldrig före den sista ändringspunkten. Kan en revision inte läsas, faller den tidigare
versionen bort. Det skjuter bara upp när något blev känt och bakdaterar aldrig. En modell med flera rader i samma
tavla får sin bästa rad, vilket inte ändrar toppen. Revisionerna cachas i `data/raw/arena/revisions/`.
Antagande: en första titlad commit lägger bara till sin egen tavla. Det är kontrollerat för revisionerna 2026-07-03
och 2026-09-26 (R8) och för 2026-04-03 (G12).

**Effekt på serierna (omkört 2026-11-24):** ingen. Alla rader i `g1_arena_*` (51, 35, 44 och 12) är identiska före och
efter, även `known_from`. Juli-tavlorna med variantrader var aldrig den senaste tavlan vid ett månadsslut (vid
2026-07-31 var det 2026-07-30, som saknar variantrader), och 2026-06-25 ändrades inte. G1:s tillstånd vid alla
månadsslut 2024-06 – 2026-10 och 2026-11-24 är oförändrat. Rättningen behövs för nästa omskrivning.

### Serier och mått

- `g1_arena_text_top`: högsta rating i `text`, kategori `overall`. Elo till och med 2024-01-08, därefter
  Bradley–Terry.
- `g1_arena_text_sc_top`: samma med stilkontroll (från 2024-08-28, standardvy från 2025-05-16).
- `g1_arena_text_top_gap_ref`: högsta rating minus `mixtral-8x7b-instruct-v0.1` (från 2026-10-20 "Mixtral 8x7B
  Instruct v0.1") i samma tavla. Referensen finns i varje texttavla från 2023-12-15. Skillnaden är oberoende av hur
  skalan förankras.
- `g1_arena_webdev_top`: Code Arena (WebDev), från 2025-11-12, ärligt daterad först från 2026-04-02.

Skalbrott enligt datasetkortet (inte korrigerade): Elo → Bradley–Terry 2024-01-09, stilkontroll som standard och
justerad offset 2025-05-16, frekvensbaserad omviktning 2025-07-23, visningsnamn i stället för API-namn från
2026-10-20. Ratingen är relativ till modellpoolen.

**Koppling till G1-måtten.** Arena-poäng är redan på logitskala: en skillnad på d poäng motsvarar
log-odds = d · ln(10)/400 för att vinna mot en modell. Mätregelns logit för begränsade andelar motsvaras därför av
nivån i poäng utan transform: takt = 12-månadersförändring i poäng. Fördubblingstid passar inte.

**Licens:** datasetkortet `license: cc-by-4.0`. Spacen har samma utgivare och används för belägg och kompletta
tabeller. Arenas egna webbvillkor kunde inte läsas (`arena.ai` blockerad). Publicera: ja, med källhänvisning till
LMArena.

Data: HF-parquet per delmängd (text 66 MB, stilkontroll 60 MB, webdev 2 MB) läses från datasetets HEAD-sha. Bara
`overall`-raderna sparas i `data/raw/arena/<datum>/`. Space-filerna cachas i `data/raw/arena/space_pkl/`, eftersom de
inte ändras. Git-klonerna (blobless, utan LFS) ligger i `data/raw/arena/{dataset_repo,space_repo}`.

## SWE-bench Verified, G1

`github.com/SWE-bench/experiments`: varje bidrag är en katalog `evaluation/verified/<datum>_<system>/` med
`results/results.json` (listor med instans-id). Tavlans läge vid ett datum = trädet i sista commit på `main`:s
first-parent-kedja med UTC-datum ≤ datumet. Ett bidrag räknas alltså från dagen det mergades, inte från körningsdatumet
i katalognamnet. Värde = max över bidrag av antal lösta / 500.

- **Historik från 2024-10-15:** repot återskapades den dagen ("Initial commit - reset history"), så äldre bidrag
  dateras med återskapandet (senare än verkligheten, alltså försiktigt). 135 bidrag med resultat i dag.
- **Kontroll av nivåer:** toppbidragens andel stämmer med deras README (`20240924_solver` 45,4 %, TRAE 78,8 %
  med flera försök, Sonar 79,2 % mot README:s 79,4 %). Tavlan blandar ett och flera försök (`attempts: 2+`).
- **Regimbrott och aktivitet** (README): från 2025-11-18 tas bara bidrag från akademiska team och forskningslabb
  med öppen metod emot. Bash-only-körningarna flyttades in under `verified/`. Efter 2026-01-26 har bara ett
  bidrag mergats (2026-09-01).
- **Licens:** repot har ingen licensfil (kontrollerat 2026-11-24). `publish=False`.
- Mått: andel (0–1) → logit enligt registret.

## AWS GPU-listpriser, G2

AWS Price List-bulkfilerna (`pricing.us-east-1.amazonaws.com`, ingen nyckel). `offers/v1.0/aws/AmazonEC2/index.json`
listar en arkiverad version per månad sedan 2015 (124 versioner). **Versionens id är publiceringstiden** (samma som
`Publication Date` i filen, t.ex. `20231222042846` = 2023-12-22 04:28:46Z). Versionen för augusti 2023 publicerades
2023-09-05, så id-datumet, inte `versionEffectiveBeginDate`, är det ärliga datumet. Månad m får priset i den senaste
version som publicerades ≤ månadens slut.

Per version läses `<id>/us-east-1/index.csv` (240–300 MB) strömmande. Bara matchande rader sparas, i
`data/raw/aws_gpu/<id>.csv`. Pris = on-demand, Linux, delad tenancy, ingen förinstallerad mjukvara,
`CapacityStatus` = Used och användningstyp `BoxUsage:<typ>`, delat med antal GPU:er (8 för båda typerna).

- `g2_aws_a100_gpu_hour`: p4d.24xlarge (8 × A100 40 GB), från 2020-11.
- `g2_aws_h100_gpu_hour`: p5.48xlarge (8 × H100), från 2023-08 (p5 lanserades 2023-07-26, och första versionen med
  p5 publicerades i augusti).
- Rader med $0,00 är platshållare för Capacity Blocks (från 2024) och tas bort. Finns fler än ett on-demand-pris för
  en typ i en version, stoppar hämtningen i stället för att gissa.
- Kontroll av nivåer: 2023-12-22-versionen ger p5.48xlarge 98,32 och p4d.24xlarge 32,7726 USD per timme, och
  2026-11-24-versionen 55,04 och 21,957642, vilket är AWS publicerade listpriser.
- **Listpriset har ändrats en gång per typ** under hela historiken (versionen för 2025-07, AWS sänkning av P4- och
  P5-priserna i juni 2025). Serierna är alltså trappsteg med ett enda steg.
- Listpris, inte marknadspris (spot, rabatter och kapacitetsblock ingår inte). Trappstegsserie, eftersom AWS sällan
  ändrar listpriset.
- **Licens:** ingen öppen licens. Filens disclaimer: "This pricing list is for informational purposes only. All
  prices are subject to the additional terms included in the pricing pages on http://aws.amazon.com."
  `publish=False` tills villkoren är prövade.
- Mått: log, halveringstid (avsnitt 1).

## Pris vid fast förmåga per leverantör, G2

`g2_price_at_capability_gpqa_<leverantör>` är samma mått som den registrerade `g2_price_at_capability_gpqa`
(lägsta blandade förstapartspris bland modeller med GPQA Diamond ≥ 0,767676, LiteLLM-filen vid månadsslut), men
bara över en leverantörs eget API. Två skillnader, båda åt senare datum: en GPQA-körning räknas från
`Started at` + 30 dagar (registrets regel för benchmarkvärden) i stället för + 7, och raderna är release-daterade
(månadsslut + 1). Ett senare ändrat värde blir en revision daterad hämtdagen (`epoch_hub.with_revisions`).
Leverantörer med värde varje månad från första månaden: OpenAI och Anthropic (från 2025-03), Google/Gemini API
(2025-04) och DeepSeek (2026-01). Moonshot, Zhipu (zai), xAI, Alibaba (dashscope) och MiniMax har kortare historik
och byggs inte. Begränsning: Epochs GPQA-körningar börjar 2025-01-27, så ingen variant når 24 månader före 2027-03.

## Undersökt men inte byggt

| Källa | Status | Belägg |
|---|---|---|
| Aider polyglot (`aider/website/_data/polyglot_leaderboard.yml`, Apache-2.0) | PARTIAL: avslutad | Git-historiken ger ärliga datum (2024-12-21 – 2025-10-08, 82 commits), men tavlan har inte uppdaterats sedan 2025-10-08. Edit-tavlan slutade 2024-12. För kort och avslutad för en kärnserie |
| LiveBench | BLOCKED/PARTIAL | `livebench.ai` nekas av proxyn (403). HF-datasetet `livebench/model_judgment` uppdaterades senast 2025-04-07. Frågebanken byts vid varje release, så nivåer är inte jämförbara mellan releaser |
| ARC Prize | BLOCKED/PARTIAL | `arcprize.org` nekas av proxyn. HF-dataseten `arcprize/arc_agi_v{1,2}_public_eval` (MIT) har svar per uppgift på den publika evalueringen, senast 2026-06-04, och skulle kräva egen rättning. Den publika mängden är inte topplistans semi-privata mängd |
| Epochs egna körningar, fler familjer | Inget nytt | `benchmark_data.zip` 2026-11-24: 18 Epoch-körda benchmarks i 12 familjer. Urvalsregeln ger fortfarande bara `frontiermath_erdos` och `spireclimb`. Övriga är mättade (≥ 0,80) eller avslutade. `*_external.csv` saknar körningsdatum |
| Fast referensmodells pris (LiteLLM) | Inte informativt | Listpriset för en fast modell ändras 0–2 gånger under hela historiken (`gpt-4o` 1, `gpt-4o-mini` 0, `o1` 0, `claude-3-5-sonnet-20241022` 0, `deepseek-chat` 2). Serien blir nästan konstant |
| Pris vid fast Arena-förmåga | Eget spår behövs | Arena-betyg är ärligt daterade från 2023-05 och skulle ge en G2-serie med mer än 2 års historik. Men bara 102 av 406 Arena-namn som någon gång var minst lika bra som `gpt-4-0314` matchar en förstapartsnyckel i LiteLLM exakt (resonemangssuffix, `chatgpt-4o-latest`, DeepSeeks rullande alias, visningsnamn från 2026-10-20). Det kräver en handgranskad mappning, som för Epoch-namnen i `model_map.py` |
| Epoch ML-hårdvara, pris/prestanda | Finns redan | `g2_epoch_hw_price_performance` (år, glest). Priset hämtas ofta från senare källor (`revised=True`) |
| Azure retail prices, GCP-prislista | BLOCKED | `prices.azure.com` och `cloudpricingcalculator.appspot.com` nekas av proxyn |
| `arena.ai`, `www.swebench.com` | BLOCKED | nekas av proxyn (behövs inte: data hämtas från HF respektive GitHub) |

## Förslag till kärnserier (för registrering av orkestreraren, före analys)

Regel i G-A:s anda: AI-specifik, tillgänglig, minst två års ärligt daterad historik vid registreringen, ett mått
per företeelse och ingen pågående mätpaus. Urvalet nedan bygger bara på tillgång, datering och metadata. Inga
värden över tid har tittats på.

**G1**
- **`g1_arena_text_top`: föreslås.** Release-daterad från 2023-05, med ett glapp där det kända värdet är
  2025-08-29-tavlan fram till 2026-04-02. Förslag: takt beräknas bara inom Bradley–Terry-eran (från 2024-01-09).
  Skalbrotten 2025-05-16 och 2025-07-23 registreras som kända brott, utan korrigering. Mått: nivå i poäng
  (logitskala), takt = 12-månadersförändring.
  Ärlig not: för beräkningsdagar 2025-09 – 2026-04-01 är det kända värdet tavlan från 2025-08-29. En takt som
  beräknas då speglar mätglappet, inte förmågan.
- `g1_arena_text_top_gap_ref`: referensvariant, inte kärnserie (samma företeelse som ovan). Den används för att
  kontrollera att förankringen inte driver nivån.
- `g1_arena_text_sc_top`: inte kärnserie nu (samma företeelse). Om registret föredrar stilkontrollen, ska den
  ersätta och inte läggas till.
- `g1_arena_webdev_top`: inte nu (ärlig historik från 2026-04). Kandidat 2028-04.
- `g1_swebench_verified_top`: inte kärnserie. Inlämningsregeln bröts 2025-11-18, bara ett bidrag sedan 2026-01
  (mätpaus enligt 90-dagarsregeln om inget nytt kommer före 2026-11-30), ingen licens, och tavlan blandar ett och
  flera försök.

Med `g1_epoch_bench_frontier_frontiermath_erdos`, `g1_epoch_bench_frontier_spireclimb` och `g1_arena_text_top`
får G1 tre räknade serier, så snart SpireClimb har sitt första kända värde (2026-12-31).

**G2**
- `g2_aws_h100_gpu_hour` och `g2_aws_a100_gpu_hour`: **inte kärnserier**, trots ärlig datering och lång historik
  (72 respektive 39 månader). Listpriset har ändrats en gång per typ på sex år. Halveringstiden över 24 månader
  skulle då bara spegla om steget ligger i fönstret eller inte. Det är samma skäl som för att inte bygga en fast
  modells LiteLLM-pris. Serierna är referens för hyrpriset på beräkning.
- `g2_price_at_capability_gpqa_<leverantör>`: inte kärnserier nu. Historiken är under 24 månader (från 2025-03), och
  de är en uppdelning av den registrerade `g2_price_at_capability_gpqa`. Beskrivande. De når 24 månader 2027-03.
- **Rekommendation: ett eget spår för pris vid fast Arena-förmåga** (1 spår + granskning). Det är den enda vägen
  till en G2-serie med mer än 2 års ärligt daterad historik nu. Specifikation att registrera före bygget:
  - Förmåga = modellens rating i den senaste dokumenterade Arena-tavlan (text, `overall`) där både modellen och
    en fast referens finns. Kvalificerad om ratingen är ≥ referensens rating i samma tavla. Måttet är då oberoende
    av skalans förankring och Elo/BT-bytet.
  - Referenser, valda efter regel och inte efter utfall: `gpt-4-0314` (GPT-4 vid lansering) och
    `gpt-4o-2024-05-13` (etta i tavlan 2024-06-11).
  - Pris = lägsta blandade förstapartspris enligt LiteLLM vid månadsslut, med samma förstapartsregel som i
    `model_map.py`. Bästa variant per prissatt modell (resonemangsnivåer), som i I6:s GPQA-regel.
  - Kräver en handgranskad tabell från Arena-namn till LiteLLM-nyckel, inklusive DeepSeeks rullande alias och
    visningsnamnen från 2026-10-20. Exakt namnmatchning täcker 102 av 406 kvalificerade namn.

G2 får alltså inga nya räknade serier av det här spåret. Den har fortfarande bara `g2_price_at_capability_gpqa`
tills Arena-spåret är byggt och granskat, eller tills leverantörsserierna når 24 månader.

## Drift

Alla serier hämtas med `python -m ai_tracker.observations <nycklar>` i den vanliga veckohämtningen. Arena hämtar
cirka 130 MB parquet per körning och klonerna uppdateras inkrementellt. AWS hämtar bara nya versioner (en per månad
och den löpande), cirka 300 MB per ny version, strömmande. SWE-bench och LiteLLM är blobless git-kloner.
