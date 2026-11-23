# Epoch AI, METR och arXiv (G1, G2, G9)

Fas 2, spår I5. Kod: `src/ai_tracker/sources/{epoch_hub,metr,arxiv}.py`, serier i
`src/ai_tracker/series/{epoch_hub,metr,arxiv}.py`. Regler: [måttregistret](../mattregister.md), ändringarna
2026-11-23. Källkartan med licenscitat finns i [datakallor/g1_g2_g9.md](../datakallor/g1_g2_g9.md). Inga takter
beräknas här, eftersom det görs i en senare fas.

Hämtning: `python -m ai_tracker.observations <nycklar>` eller veckojobbet `.github/workflows/collect-weekly.yml`
(måndagar, Actions-cache för `data/`, concurrency-grupp `ai-data`, inga hemligheter).
`python -m ai_tracker.series.epoch_hub` räknar om urvalsregeln och successorkontrollen och skriver ut resultatet
(spår F6). Byten görs aldrig tyst.

## Serier

| Nyckel | Frekv. | Historik | Värde | `known_from` | `source` |
|---|---|---|---|---|---|
| `g1_epoch_bench_frontier_<b>` | M | valda: 2026-08 (b = `frontiermath_erdos`), 2026-11 (`spireclimb`, känd från 2026-12-31). Avslutade: 2025-03 (`frontiermath`), 2025-07 (`frontiermath_tier_4`) | bästa poäng bland körningar startade före månadsslut | 1:a dagen i månaden efter + 30 dagar. Körning som syns först i en senare hämtning: ny version vid max(`Started at` + 30, `first_seen`). Ändrat källvärde: hämtdagen | release |
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
(UTC). Det gäller även när modellen släpptes tidigare. Sedan registerändringen 2026-11-23 ("försiktigare datum",
spår F6) är en körning känd från `Started at` + 30 dagar, avrundat uppåt till midnatt UTC (`epoch_hub.run_known`).
Körningar i den första hämtningen (2026-11-23, `FIRST_FETCH`) har inget observerat publiceringsdatum, så för dem gäller
bara 30-dagarsregeln. En körning som syns först i en senare hämtning är känd från max(`Started at` + 30, `first_seen`).
Månad m får sin första version den första dagen i m+1 + 30 dagar, och då är varje körning i den första hämtningen som
räknas för m känd. Varje senare känd körning som ändrar värdet ger en ny version på sitt kända datum
(`epoch_hub.monthly_vintages`). Körningsloggen `data/epoch/benchmark_runs.parquet` har `first_seen` per körning, och
fördröjningen mäts och redovisas efter 6 månader enligt registret. Om Epoch ersätter en körning (omkörning) så att ett
redan lagrat värde ändras, läggs en ny rad med `known_from` = hämtdagen till (`epoch_hub.with_revisions` och
`observations.new_rows`), och den gamla versionen ligger kvar för `as_of()`. Serierna byggdes om (`--rebuild`)
2026-11-23 med den nya regeln, så de tidigare raderna (första dagen i m+1) finns inte kvar. `lag_days` = 31 i
katalogen ger aktualitetsgränsen 92 dagar.

En hämtning samma dag läser dagens råkopia i `data/raw/epoch/<dag>/` i stället för att ladda ned igen
(`epoch_hub._zip_bytes`). Det gör att en ombyggnad efter en hämtning använder samma version.

**Urval** (måttregistret 2026-11-23, posterna om avslutade benchmarks och "G1: urvalsregeln tillämpad (spår F6)").
Koden finns i `epoch_hub.selection_table`. En benchmark är avslutad om den har `superseded_by` eller saknar Epoch-körning
de senaste 90 dagarna. Avslutade benchmarks och de med frontvärde ≥ 0,80 utesluts. Sedan väljs högst en per familj
(`epoch_hub.family`, första ledet i filnamnet före `_`), den med flest modeller och vid lika antal basvarianten.
Familjevinnarna rangordnas efter antal Epoch-körda modeller. Resultatet blev `frontiermath_erdos` (17 modeller) och
`spireclimb` (13). Bara två familjer återstod, så den tredje platsen är tom och det finns ingen efterträdare.
Det tidigare urvalet, `frontiermath` och `frontiermath_tier_4`, är ersatt av Epoch och ligger kvar som avslutade
katalogserier (`closed=True`, "Avslutad:" i `note`). De är bara beskrivning.

**Byten och `<valda>`.** Kärnserien `g1_epoch_bench_frontier_<valda>` i registret löses upp av tillståndsmotorn per
beräkningsdag genom `series.epoch_hub.selected_on`. Den utgår från den registrerade listan och tillämpar varje byte i
`REPLACEMENTS` (datum, ersatt, efterträdare) från bytets datum. Datumet är den första dagen då den ersatta benchmarken
var avslutad eller mättad (> 0,90) med det som var känt den dagen. Efterträdaren väljs med `apply_successor_rule` och
rangordningen den dagen: familjevinnare som inte är avslutade, har frontvärde < 0,70, inte har varit valda tidigare och
inte tillhör en familj som redan är vald. Byten registreras, de görs aldrig tyst. Försiktighetsregeln är att en vald
benchmark slutar räknas så snart det som är känt på beräkningsdagen visar att den är mättad (känt frontvärde > 0,90)
eller avslutad (senaste kända månad med körning slutade mer än 90 dagar tidigare), även innan bytet är registrerat
(`state.branch.benchmark_guard`). `superseded_by` har ingen daterad historik i källan och verkar därför bara genom ett
registrerat byte, men en benchmark som Epoch slutar köra fångas av 90-dagarsregeln. Före urvalsdagen, alltså i
backcast, gäller den registrerade listan. Urvalet bygger på täckning och metadata, inte på frontvärdenas förlopp.

**ECI** skattas om (IRT) när modeller och benchmarks tillkommer, så hela historiken kan flytta sig vid varje hämtning.
Varje förändring blir en revisionsrad. Veckoserien ger det aktuella frontvärdet varje måndag. Det kräver en senare
aggregering till månad i måttfasen.

**Modelldatabasen** fylls på i efterhand. De senaste månaderna är ofullständiga, och det är inmatningseftersläpning
och ingen trend. Den återfyllda historiken (`source=backfill`) har ett nominellt `known_from` och får enligt
registret inte ingå i diffusionsindex förrän det finns 24 månader egna ögonblicksbilder. I tillståndsmotorn
(`state/register.py`) är `g1_epoch_eci_frontier`, `g9_epoch_notable_models` och `g9_epoch_open_weights_share`
därför spärrade (`BACKFILL_GATED`). `g1_epoch_train_compute_frontier` räknas enligt registret men flaggas
(`BACKFILL_FLAGGED`, fältet `flag` i ögonblicksbilden). Andelen öppna vikter mäts som andel i procentenheter
(0–1 × 100), inte i logit, eftersom logit bara är registrerat för G1-benchmarks.

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
(`submittedDate`, version 1, sorterat stigande, 1 000 per sida eftersom 2 000 oftare gav HTTP 500), och `arxiv:primary_category` räknas. Samma körning
ger unionen inklusive korslistningar. API:et svarar HTTP 500 för `start` ≥ 10 000 (verifierat 2026-11-23, och månader sedan 2026-05 har
upp till 12 900 poster), så ett fönster med fler träffar delas på mitten efter dag tills varje del ryms.
En månad godkänns när antalet unika id stämmer med `totalResults`
(tolerans max(2; 0,2 %)), annars hämtas den igen vid nästa körning.

**arXiv, artighet.** Ett anrop åt gången, minst 3 s mellan anropen och exponentiell backoff (20 s · 2^n, högst
900 s, eller `Retry-After`) vid 429, 5xx och nätfel. Varje körning har en anropsbudget (`ARXIV_MAX_CALLS`), och
månadscachen `data/arxiv/monthly.json` sparas efter varje månad, så att en avbruten återfyllnad fortsätter där den
slutade. Serierna vägrar skriva en ofullständig historik, eftersom den första laddningen blir backfill. Sidorna
sparas inte råa (cirka 2,4 MB per 1 000 poster). Månadsräkningarna med hämtdatum är det som lagras.

**arXiv, `known_from`** = månadsslut + 7 dagar. Sena tillkännagivanden och moderationsstopp behåller sitt
inlämningsdatum, så en månad växer lite i efterhand. Månader hämtas om tills de är 60 dagar gamla, och därefter
anses de stabila. Revideringar efter 60 dagar fångas inte.

## Läckage och förbehåll

- `Started at` är körningens start och inte publiceringen. Därför används `Started at` + 30 dagar. Om 30 dagar räcker
  för körningarna i den första hämtningen går inte att verifiera. Det kalibreras med `first_seen` i körningsloggen
  efter 6 månader.
- I `gpqa_diamond` (56 körningar) och `math_level_5` (52) har många körningar exakt `Started at`
  2025-01-27 00:00:00. Det ser ut som ett platshållardatum för körningar som importerades när hubben startade.
  Inget av dem ingår i urvalet, men det ska kontrolleras om de blir aktuella.
- ECI, modelldatabasen och hårdvaran är återfyllda och reviderade. Före första egna hämtningen 2026-11-23 är
  `known_from` nominellt och inte ett ärligt kunskapsdatum.
- Om en veckokörning missas får nya perioder `min(periodslut + fördröjning, hämtdag)` (ramverkets regel), och det
  kan vara tidigare än vår faktiska hämtning.
- arXiv: summan av månaderna stämmer med en årsfråga (kontrollerat för 2013 och 2015), men nivån har inte
  kunnat stämmas av mot arXivs egen statistik (arxiv.org blockeras).
- Hård hastighetsbegränsning från delade IP-adresser (429) har observerats i fas 1. Hur det ser ut i GitHub
  Actions är inte verifierat. Budgeten gör att en första återfyllnad där kan ta flera körningar.
- Lokalt 2026-11-23 tog arXiv-återfyllnaden (1998-01 – 2026-10) cirka 560 anrop. Efter cirka 480 anrop kom
  perioder med 429/500/503, och backoffen klarade dem.
