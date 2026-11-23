# Källa: utvecklaradoption (npm, PyPI)

Spår B1 (steg 2, våg 1), led L2, gren G3. Byggt och kört mot riktiga data 2026-11-23. Kod:
`src/ai_tracker/sources/{npm,pypistats,pypi_bq,download_counts}.py`, `src/ai_tracker/series/{npm,pypi}.py`,
BigQuery-jobb i `src/ai_tracker/jobs/pypi_{dryrun,backfill,probe,calibrate}.py`. Tester:
`tests/test_utvecklaradoption.py` (fixtures, inget nät). Hämtning: `python -m ai_tracker.observations <nycklar>`.
Här finns ingen analys. Om serierna blir kärnserier beslutas i grinden G-A.

**Nedladdningar är inte användare.** CI-byggen, containerbyggen, speglar (bandersnatch, Artifactory m.fl.),
cachar och transitiva beroenden räknas med, och ett paket som många andra beror på (requests, numpy, react) räknas
varje gång. Nivåer mellan paket och ekosystem är därför inte jämförbara som antal utvecklare. Pip-cachen sänker
PyPI-talen, och speglar kan både höja och sänka (packaging.python.org, "Analyzing PyPI package downloads").

## Serier (34, alla veckovisa W-SUN, gren G3)

| Nycklar | Innehåll | Historik |
|---|---|---|
| `g3_npm_<paket>_w` (10) | npm, exakt veckosumma: openai, @anthropic-ai/sdk, @google/generative-ai, @google/genai, langchain, @langchain/core, ai (Vercel), @modelcontextprotocol/sdk, kontrollpaketen react och express | react från 2015-02, express från 2021-09, AI-paketen från sin första vecka |
| `g3_pypi_<paket>_w` (12) | PyPI, exakt veckosumma: openai, anthropic, google-generativeai, google-genai, langchain, langchain-core, transformers, torch, llama-index, mcp, kontrollpaketen requests och numpy | från 2026-06-01 (pypistats 180 dagar), växer varje vecka |
| `g3_pypi_<paket>_wed` (12) | PyPI, nedladdningar under veckans **onsdag** (UTC), samma paket | requests från 2016-05, torch 2018-12, transformers 2019-09, openai 2020-02, AI-SDK:erna från sin första release. numpy bara från 2026-05 |

Ingen kvotserie mot kontrollpaketen byggdes (det vore en härledd serie). Kontrollerna finns som egna serier.

Explicita startveckor där namnet tidigare hade en annan ägare eller bara platshållare: `ai` (npm, ett annat paket
2014; Vercels 2.0.0 2023-06-14 → veckan 2023-06-12), `transformers` (ett annat paket 0.1 2016; Hugging Face 2.0.0
2019-09-26 → 2019-09-30), `torch` (första version med filer 1.0.0 2018-12-07 → 2018-12-03), `openai` på PyPI
(2020-02-18 → 2020-02-17), `mcp` (0.9.1 2024-11-20 → 2024-11-18). Datum ur registry.npmjs.org och pypi.org/pypi/<p>/json.

## known_from

- **Regel:** söndag + 2 dagar (`lag_days=2`), samma för npm och PyPI. En vecka tas bara med när söndagen + 2 dagar
  ≤ hämtdagen. Veckokörningen måndag 03:37 UTC tar alltså den vecka som slutade dagen innan först nästa måndag,
  och den får då known_from = tisdagen (regeln "aldrig före en hämtning som saknade perioden" i `observations.py`).
- **Belägg, npm:** "Once per day, soon after UTC midnight, a map-reduce cluster ... crunches the previous day's logs"
  (github.com/npm/registry, docs/download-counts.md). 2026-11-23 20:58 UTC fanns söndagen 2026-11-22 och måndagen
  2026-11-23 var 0, alltså inte beräknad än. En dag som inte är beräknad returneras som 0. Därför regeln om
  söndag + 2 och att hela veckan måste vara täckt.
- **Belägg, PyPI:** Linehaul strömmar nedladdningsloggar till BigQuery (github.com/pypa/linehaul-cloud-function).
  pypistats uppdaterar "once daily", och 2026-11-23 kväll fanns 2026-11-22. Onsdagsserien har samma regel (söndag +
  2), vilket är konservativt eftersom onsdagen är känd redan på fredagen.
- **Historiken är backfill** (`source="backfill"`, dagens årgång). Nedladdningstal revideras i praktiken inte:
  BigQuery och pypistats gav identiska tal för alla elva frågade paket på överlappsdagen 2026-05-27. npm fyller inte
  i sina saknade dagar i efterhand (luckorna 2020, 2022 och 2023 finns kvar). Revideras ett värde blir det en ny
  version med known_from = hämtdagen (`revised=True`).
- **Urvalsrisk:** paketlistan är vald i dag, med kunskap om vilka SDK:er som blev stora. Det gäller också
  nivåerna bakåt, och ska vägas in när serierna väljs i G-A.

## npm (api.npmjs.org)

- `GET /downloads/range/<a>:<b>/<paket>`, högst 18 månader per anrop (vi tar 500 dagar), tidigast 2015-01-10.
  Scopade namn skrivs rakt i sökvägen. Cirka 35 anrop per full hämtning. Allt hämtas om varje vecka (få anrop, och
  då fångas eventuella ändringar).
- **Luckor i npm:s egna data:** dagar då alla aktiva kontrollpaket (react, express) är 0: 2020-06-22, 2022-07-22,
  2023-11-03, 2026-09-15, 2026-10-06, 2026-10-14, 2026-10-15, 2026-10-19 och 2026-10-20. De är saknade dagar, inte
  nollor. Veckosumman = summan av rapporterade dagar / deras andel av veckan i paketets egna 8 senaste kompletta
  veckor *före* veckan (bara tidigare data). Färre än 4 sådana veckor ger andelen n/7, färre än 4 rapporterade dagar
  stryker veckan. Exempel: openai 2026-10-12–18, npm:s egen summa 34 407 181 (två nolldagar), vår 51 634 370.
- **express** returnerar 0 för alla dagar före 2021-09-27, så serien börjar där. Kontrollpaketen är inte stabila
  (express mer än fördubblades 2025→2026) och är bara en referens, inte en normalisering i sig.
- Kontroll mot npm:s point-API, vecka 2026-11-09–15: openai 58 843 658, @anthropic-ai/sdk 70 671 564 och react
  260 880 973, identiska med serierna.
- **Licens:** ingen licens anges i download-counts.md, och npm:s Open Source Terms (docs.npmjs.com) går inte att
  läsa från sandlådan. `license="unverified ..."`, `publish=False`.

## PyPI: BigQuery och pypistats

Båda läser `bigquery-public-data.pypi.file_downloads` (en rad per nedladdning). **Licens:** "The tables and its
pertaining data are licensed under the Creative Commons License" (CC BY 4.0), docs.pypi.org/api/bigquery
(github.com/pypi/warehouse, docs/user/api/bigquery.md). `publish=True` med PyPI/PSF som källa.

### Kostnad och design (beslut 2026-11-23)

Tabellen är partitionerad per dag och klustrad på `file.project`. Frågorna läser bara `timestamp` och
`file.project` och bara de dagar som behövs. Mätt med torrkörningar och en kalibrering:

- Torrkörningens uppskattning tar hänsyn till klustringen och var lika med fakturerade byte: 0,127 mot 0,128 GB
  (anthropic+mcp en dag) och 1,516 mot 1,517 GB (tolv paket en dag).
- Varje (paket, dag) kostar minst ett lagringsblock, cirka 0,01–0,05 GB, oavsett hur litet paketet är. En dag
  2026-11-15 kostade 0,67 GB för requests ensam, 1,97 GB för alla tolv paket och 73 GB utan paketfilter.
- **Exakt daglig historik** 2016-01-01 → 2026-11-23 för de tolv paketen: 2 133 GB enligt torrkörning per år (2016:
  15, 2019: 33, 2022: 124, 2024: 263, 2025: 437, 2026: 779). Bara AI-paketen från sitt första år: cirka 660 GB.
  Ett inkrementellt veckojobb med exakta dagar kostar cirka 19 GB per vecka (2026-11-16–22). Båda ryms inte i
  kvoten (1 TB per månad, delad med alla spår, B2 behöver den).

**Därför:**
1. **Veckovis påfyllnad från pypistats.org** (`/api/packages/<p>/overall`, kategorin `with_mirrors` = alla rader,
   samma definition som `COUNT(*)`). Gratis, ingen hemlighet, 180 dagars fönster, och varje svar sparas så att
   historiken växer. API-sidans etikett: "If you want to regularly fetch download counts for a particular package
   or set of packages, cache your results ... you should not need to fetch results from the same API endpoint more
   than once per day". Vi hämtar 12 paket en gång i veckan. pypistats-sidan anger ingen egen licens. Talen är
   BigQuery-tabellens (CC BY 4.0).
2. **BigQuery-backfill med stickprov:** en fast veckodag (onsdag, UTC) per vecka, en fråga per år, varje AI-paket
   från sitt första år och requests från 2016. numpy är inte med (cirka 45 GB för en andra kontroll). Den slutar
   en måndag cirka 25 veckor bakåt (`backfill_end`), så att pypistats överlappar med några dagar.
3. Onsdagsserien fortsätter framåt med samma veckodag från pypistats. Exakta veckosummor finns från 2026-06.

**Överlappskontroll** 2026-05-27 (BigQuery mot pypistats `with_mirrors`), identiskt för alla elva frågade paket,
till exempel openai 11 732 449, requests 59 359 202, mcp 9 180 436 och llama-index 410 130. På en dag som båda
har vinner BigQuery.

### Byte per jobb (B1, 2026-11-23)

| Jobb (Actions-körning) | Uppskattat | Fakturerat |
|---|---|---|
| `pypi_dryrun`, exakt plan (45265578760) | 2 133 GB (torrkörning) | 0 |
| `pypi_probe`, 418 torrkörningar per paket och år (45266152914) | – | 0 |
| `pypi_calibrate`, två små riktiga frågor (45269823013) | 1,643 GB | 1,645 GB |
| `pypi_dryrun`, stickprovsplan (45270588204) | 224,8 GB med numpy | 0 |
| `pypi_backfill`, onsdagar utan numpy (45270974803) | 175,641 GB | 175,646 GB |
| **Summa B1** | | **cirka 177,3 GB** |

Backfill per år (uppskattat = fakturerat inom 1 MB): 2016 0,35, 2017 0,63, 2018 1,12, 2019 2,54, 2020 4,16,
2021 7,80, 2022 11,48, 2023 18,72, 2024 32,60, 2025 56,68 och 2026-01–05 39,57 GB. Varje jobb skriver
`bytes.json` (uppskattat, bearbetat och fakturerat per fråga) bredvid sina CSV-filer.

### Luckor i tabellen

Tabellen börjar 2016-01-22 och saknar onsdagarna 2016-03-09 till 2016-05-18 (ingen requests-rad). requests
onsdagsserie börjar därför veckan 2016-05-23. En dag utan requests-rad räknas som lucka (NaN) för alla paket,
inte som noll. Ett paket som saknas en dag som requests har hade noll nedladdningar.

## Drift

- **Veckokörningen** (`fetch-weekly.yml`, `pipeline weekly`): npm och pypistats är vanliga katalogserier utan
  hemlighet och uppdateras varje måndag. `python -m ai_tracker.pipeline weekly <B1-nycklar>` kördes lokalt
  2026-11-23: alla hämtningar ok och aktualiteten ok. Den enda kontroll som fallerade var `series_in_catalog`
  för B3:s serier i den delade basen (g3_cf_*, g3_wiki_*), vars kod inte finns på main än.
- **BigQuery i Actions är valfritt:** `workflow_dispatch` med inputen `pypi_bigquery` = `backfill` (en gång,
  cirka 176 GB, lägger historiken i Actions-cachen; körs inte om onsdagsfiler redan finns) eller `incremental`
  (exakta dagar, cirka 19 GB). Stegen har `continue-on-error`, så ett BigQuery-fel stoppar aldrig resten.
  Schemalagda körningar rör inte BigQuery. Utan backfill har Actions-tabellen onsdagsserierna från pypistats
  (cirka 25 veckor bakåt) och framåt. Görs backfillen efter att serierna redan finns i Actions-tabellen, får de
  äldre veckorna known_from = dagen efter senaste hämtning (konservativt). Rekommendation: kör den en gång i en ny
  kvotmånad, före första schemalagda körningen efter merge, om kvoten tillåter.
- Rådata: `RAW_DIR/npm/<datum>/`, `RAW_DIR/pypistats/<datum>/`, `RAW_DIR/pypi_bq/<datum>/{wed,daily}_*.csv` och
  `bytes.json`. Inget committas.

## Hämtning av artefakter

`gh run download` hämtar från `productionresultssa<N>.blob.core.windows.net`, och lagringskontot varierar mellan
körningar (sa32, sa18). Miljön tillät sa0–sa9. sa32 lades till 2026-11-23 och sa18 nekades. Torrkörningarnas
uppskattningar lästes då ur jobbloggen (`gh run view --log`). Backfillens artefakt låg på ett tillåtet konto.

## Inte gjort

- Ögonblicksbilder av nedladdningar från Hugging Face (nämns i planen men inte i spårets brief).
- Spegelfria PyPI-tal (`without_mirrors` finns i pypistats men inte i BigQuery-backfillen utan en kolumn till).
