# Epoch AI, METR och arXiv (G1, G2, G9)

Fas 2, spår I5. Kod: `src/ai_tracker/sources/{epoch_hub,metr,arxiv}.py`, serier i
`src/ai_tracker/series/{epoch_hub,metr,arxiv}.py`. Regler: [måttregistret](../mattregister.md), ändringarna
2026-11-23. Källkartan med licenscitat finns i [datakallor/g1_g2_g9.md](../datakallor/g1_g2_g9.md). Inga takter
beräknas här, eftersom det görs i en senare fas.

Hämtning: `python -m ai_tracker.observations <nycklar>` eller veckojobbet `.github/workflows/collect-weekly.yml`
(måndagar, Actions-cache för `data/`, concurrency-grupp `ai-data`, inga hemligheter).
`python -m ai_tracker.series.epoch_hub` räknar om urvalsregeln och successorkontrollen och skriver ut resultatet.
Byten görs aldrig tyst.

## Serier

| Nyckel | Frekv. | Historik | Värde | `known_from` | `source` |
|---|---|---|---|---|---|
| `g1_epoch_bench_frontier_<b>` | M | 2025-03 (b = `frontiermath`), 2025-07 (`frontiermath_tier_4`), 2026-08 (`frontiermath_erdos`) | bästa poäng bland körningar startade före månadsslut | 1:a dagen i månaden efter. Ändrat källvärde: hämtdagen | release |
| `g1_epoch_bench_runs_<b>` | M | som ovan | antal Epoch-körningar startade i månaden | som ovan | release |
| `g1_epoch_eci_frontier` | W (mån–sön) | 2023-02 – | högsta ECI bland modeller släppta t.o.m. veckans slut | historik: veckoslut + 1 dag (nominellt). Nya veckor och revideringar: hämtdagen | backfill, sedan fetch/revision |
| `g1_epoch_train_compute_frontier` | M | 2010-01 – | största `Training compute (FLOP)` bland alla modeller publicerade t.o.m. månaden | historik: månadsslut + 7 (nominellt). Sedan hämtdagen | backfill → fetch/revision |
| `g9_epoch_notable_models` | M | 2010-01 – | antal notable-modeller per publiceringsmånad (0 är en riktig nolla) | som ovan | backfill → fetch/revision |
| `g9_epoch_open_weights_share` | Q | 2015Q1 – | andel `Open model weights?` = Yes bland notable-modeller där fältet är ifyllt | som ovan | backfill → fetch/revision |
| `g2_epoch_hw_price_performance` | A | 2016 – | bästa 16-bit FLOP/s per releasepris i USD bland acceleratorer släppta t.o.m. året | årsslut + 7 (nominellt) | backfill → fetch/revision |
| `g1_metr_horizon_p50_frontier` | M | 2019-02 – 2026-04 | **referens:** högsta p50-tidshorisont (minuter) bland modeller släppta t.o.m. månaden | max(datum i METR:s uppdateringslogg, 2026-03-03, dagen efter månadsslut) | release |
| `g9_arxiv_ai_ml_submissions` | M | 1998-01 – | nya artiklar med primär kategori cs.AI, cs.LG eller cs.CL (summa) | månadsslut + 7 dagar. Revidering: hämtdagen | backfill → fetch/revision |
| `g9_arxiv_cs_ai`, `_cs_lg`, `_cs_cl` | M | 1998-01 – | samma per primär kategori | som ovan | som ovan |
| `g9_arxiv_ai_ml_listed` | M | 1998-01 – | unionen listad i någon av de tre, inklusive korslistningar (varje artikel en gång) | som ovan | som ovan |

Licenser: Epoch och METR CC BY 4.0 (citerade i `LICENSE` i respektive källmodul, `publish=True`). arXiv:
`unverified`, eftersom villkoren inte gick att läsa (arxiv.org och info.arxiv.org blockeras). `publish=False` gäller
tills villkoren är kontrollerade.

## Härledningar och val

**Benchmarkfronten as-of.** En körning räknas för månad m bara om `Started at` ligger före m:s sista ögonblick
(UTC). Det gäller även när modellen släpptes tidigare. Värdet får `known_from` = första dagen i m+1, alltså efter alla
körningar som räknats. Det är registrets regel (`Started at` = `known_from`). Den är optimistisk med körningens
längd plus Epochs publiceringsfördröjning. Därför sparas en körningslogg, `data/epoch/benchmark_runs.parquet`, med
`first_seen` per körning från våra hämtningar, så att fördröjningen kan mätas och regeln kalibreras. Om Epoch
ersätter en körning (omkörning) eller lägger in en körning med gammalt `Started at` ändras det härledda värdet.
Då läggs en ny rad med `known_from` = hämtdagen till (`epoch_hub.with_revisions`), och den gamla versionen
ligger kvar för `as_of()`.

**Urval.** Se måttregistret, 2026-11-23 (benchmarkurvalet tillämpat): `frontiermath`, `frontiermath_tier_4` och
`frontiermath_erdos`. Två av dem är ersatta av Epoch och har inte körts sedan 2026-06-08. Frågan är flaggad för beslut.

**ECI** skattas om (IRT) när modeller och benchmarks tillkommer, så hela historiken kan flytta sig vid varje hämtning.
Varje förändring blir en revisionsrad. Veckoserien ger det aktuella frontvärdet varje måndag. Det kräver en senare
aggregering till månad i måttfasen.

**Modelldatabasen** fylls på i efterhand. De senaste månaderna är ofullständiga, och det är inmatningseftersläpning
och ingen trend. Den återfyllda historiken (`source=backfill`) har ett nominellt `known_from` och får enligt
registret inte ingå i diffusionsindex förrän det finns 24 månader egna ögonblicksbilder.

**Hårdvara:** Epochs egen kolumn `Price-performance` använder den snabbaste precisionen, som byts över tid
(FP32 → FP8/FP4). Vi håller en precision: Tensor-FP16/BF16, annars FP16. Före 2016 finns för få priser. Serien är
gles, med 1–7 acceleratorer med pris per år.

**METR** är en referensserie (`note` börjar med REFERENSSERIE) och ingen kärnserie. Siffrorna i v1.1-filen är
de som gäller efter rättelsen 2026-03-03 ("Corrected a regularization mistake"). En modell får därför
`known_from` = max(datum för den senaste loggraden som nämner modellen, 2026-03-03). Modeller som loggen inte
nämner fanns med före rättelsen, eftersom loggen listar varje tillägg sedan 2025-03. Serien slutar vid den senaste
release-månaden (2026-04). Sidan uppdateras inte längre, och METR anger att värden över 16 timmar är opålitliga.

**arXiv, primär kategori.** API:ets `cat:` träffar även korslistade artiklar, och det finns inget filter för
primär kategori. Därför hämtas alla poster i `cat:cs.AI OR cat:cs.LG OR cat:cs.CL` per inlämningsmånad
(`submittedDate`, version 1, sorterat stigande, 2 000 per sida), och `arxiv:primary_category` räknas. Samma körning
ger unionen inklusive korslistningar. En månad godkänns när antalet unika id stämmer med `totalResults`
(tolerans max(2; 0,2 %)), annars hämtas den igen vid nästa körning.

**arXiv, artighet.** Ett anrop åt gången, minst 3 s mellan anropen och exponentiell backoff (20 s · 2^n, högst
900 s, eller `Retry-After`) vid 429, 5xx och nätfel. Varje körning har en anropsbudget (`ARXIV_MAX_CALLS`), och
månadscachen `data/arxiv/monthly.json` sparas efter varje månad, så att en avbruten återfyllnad fortsätter där den
slutade. Serierna vägrar skriva en ofullständig historik, eftersom den första laddningen blir backfill. Sidorna
sparas inte råa (cirka 4,7 MB per 2 000 poster). Månadsräkningarna med hämtdatum är det som lagras.

**arXiv, `known_from`** = månadsslut + 7 dagar. Sena tillkännagivanden och moderationsstopp behåller sitt
inlämningsdatum, så en månad växer lite i efterhand. Månader hämtas om tills de är 60 dagar gamla, och därefter
anses de stabila. Revideringar efter 60 dagar fångas inte.

## Läckage och förbehåll

- `Started at` är körningens start och inte publiceringen. Värdena är därför optimistiska med dagar. Det kalibreras
  med `first_seen` i körningsloggen.
- I `gpqa_diamond` (56 körningar) och `math_level_5` (52) har många körningar exakt `Started at`
  2025-01-27 00:00:00. Det ser ut som ett platshållardatum för körningar som importerades när hubben startade.
  Inget av dem ingår i urvalet, men det ska kontrolleras om de blir aktuella.
- ECI, modelldatabasen och hårdvaran är återfyllda och reviderade. Före första egna hämtningen 2026-11-23 är
  `known_from` nominellt och inte ett ärligt kunskapsdatum.
- Om en veckokörning missas får nya perioder `min(periodslut + fördröjning, hämtdag)` (ramverkets regel), och det
  kan vara tidigare än vår faktiska hämtning.
- arXiv-nivån har inte kunnat stämmas av mot arXivs egen statistik (arxiv.org blockeras).
- Hård hastighetsbegränsning från delade IP-adresser (429) har observerats i fas 1. Hur det ser ut i GitHub
  Actions är inte verifierat. Budgeten gör att en första återfyllnad där kan ta flera körningar.
