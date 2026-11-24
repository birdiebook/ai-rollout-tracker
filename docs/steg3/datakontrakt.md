# Datakontraktet mellan Python och den nya hemsidan (W3)

Skriven 2026-11-24 (spår W3). Kontraktet är paketet `web-data/`: statiska JSON-filer med versionsnummer, ett JSON
Schema per dokumenttyp och en licensgrind på ett ställe. Python äger all data och grinden. Den nya sidan (SvelteKit,
`docs/beslutslogg.md` 2026-11-24) läser bara paketet, aldrig observationstabellen.

```
python -m ai_tracker.site_bundle build [--out web-data] [--today YYYY-MM-DD] [--history-from YYYY-MM] [--skip-checks]
python -m ai_tracker.site_bundle fixtures [--out web-data-fixtures]    # syntetiskt paket, committat
python -m ai_tracker.site_bundle validate <katalog>                     # schema + licensskanning + kontrollsummor
python -m ai_tracker.site_bundle sizes <katalog>                        # storleksrapport ur manifestet
```

`build` kör samma lagerkontroller som den gamla sidan (`warehouse`), sätter ihop dokumenten, skannar licenserna,
validerar varje dokument mot sitt schema, kontrollerar storleksbudgetarna och skriver först därefter, till en
temporär katalog som byts in i ett steg. Ett fel i något steg stoppar bygget och lämnar det tidigare paketet orört.
`web-data/` är gitignorerad (data committas aldrig). Bara `web-data-fixtures/` committas, och den är syntetisk.

Koden: `src/ai_tracker/site_bundle/` (`export.py` sätter ihop, `gate.py` licensgrinden, `vintages.py` versionerna,
`schema.py` och `schema/*.json` kontraktet, `build.py` skrivning och budgetar, `synthetic.py` fixturvärlden).
Tester: `tests/test_site_bundle.py`.

## 1. Principer

- **En källa för varje vy.** Dokumenten byggs av samma funktioner som den gamla sidan (`ai_tracker.site.data`,
  `site.flow`, `site.probabilities`): samma ögonblicksbild eller rekonstruktion, samma mått, samma licensregel.
  Paketet skär bara om dem till ett dokument per sida eller entitet och lägger till seriedokumenten. Det ger
  paritet med den gamla sidan för W16 utan dubbel logik.
- **Inget räknas i webbläsaren som pipelinen redan räknar.** Takt, förändring i takt, riktning och percentiler kommer
  färdiga. Tidsresan läser versioner (avsnitt 5) och månadens mått som de stod i registret den månaden
  (`measure_history`), och räknar aldrig om historiken med dagens data.
- **Versionsnummer.** `manifest.version` följer semver. Major ändras när ett fält tas bort, byter typ eller
  betydelse. Minor när ett fält eller dokument läggs till. Alla scheman har `additionalProperties: false` (eller
  `unevaluatedProperties: false`), så ett nytt fält i pipelinen stoppar bygget tills schemat, fixturerna och den här
  texten är uppdaterade. Det är meningen: frontend ska aldrig få ett fält som inte är beskrivet.
- **Ärlig märkning.** Varje dokument med tillståndsdata har `record` (avsnitt 3), och varje månad i ränderna och i
  måtthistoriken har `kind` (`skarp` eller `rekonstruerad`).

## 2. Dokumenten

| Fil | Schema | Innehåll | Sida i visionen |
|---|---|---|---|
| `manifest.json` | `manifest` | version, byggtid, git-sha, status för ögonblicksbilden (live/reconstructed), alla filer med storlek och SHA-256, budgetar | (byggsteg) |
| `overview.json` | `overview` | `record`, rubrikfakta och meningar, grenkort, tillståndsränder (gren × månad), prognoskalender, regimsammanfattning, nyckeltal | `/` |
| `flow.json` | `flow` | L1–L9 med grenarnas tillstånd, nyckelserier med mått och bana, nowcast per led, avstämningar mellan leden, inhållna | `/`, `/flode/L*`, `/avstamning/*` |
| `branch/G1.json` … `G9.json` | `branch` | en gren: index, tillstånd, förändring mot förra månaden, räknade och ej räknade serier med mått och bana, inhållna, indexhistorik | `/gren/G*` |
| `series/index.json` | `series_index` | alla publicerbara serier: nyckel, etikett, gren, frekvens, enhet, källa, licens, kärnserie, räknad, första och senaste period, antal versioner, riktning | sök (⌘K), `/data`, filter |
| `series/<nyckel>.json` | `series` | en publicerbar serie: metadata, licens och attribution, nivåer, mått, måttets bana, måtthistorik per månad, versioner | `/serie/<nyckel>` |
| `nowcast/n1.json` … `n6.json` | `nowcast` | skarpa filer med intervall, scorecard, sammanfattning, täckning, backtestkalibrering, målets senaste nivåer | `/prognos/n*` |
| `nowcast/d2.json` | `horizons` | D2 (1–8 kvartal, skugga): bana och solfjäder ur senaste skarpa fil, sammanfattning per horisont | `/prognos` |
| `regime.json` | `regime` | C4 ur de skarpa ögonblicksbilderna: P(inbromsning) per block och månad, skiften, strukturbrott | `/regim` |
| `method.json` | `method` | registrets regler, tillståndsnamn, kärnserier per gren, leden, nowcastvarianter, källor och licenser, registrets SHA-256 | `/metod` |
| `withheld.json` | `withheld` | alla serier med `publish=False`: nyckel, etikett, källa, licens, skäl, gren | `/metod`, `/data` |
| `letters.json` | `letters` | index över månadsbrev och kvartalsrapporter, nyast först | `/brev`, `/rapport` |
| `letters/<YYYY-MM>.json`, `reports/<YYYYQn>.json` | `publication` | ett brev eller en rapport med Markdown | `/brev/*`, `/rapport/*` |
| `schema/*.json` | – | kopior av schemana som Python validerade mot | typer i frontend |

### Gemensamma format (`schema/common.json`)

- **Tal:** avrundade till 5 signifikanta siffror (mått, index) eller 6 (nivåer, versioner, prognoser). Saknat eller
  icke-ändligt tal är `null`, aldrig `NaN`.
- **Datum:** `YYYY-MM-DD`. **Månad:** `YYYY-MM`. **Period:** som i observationstabellen (`2026`, `2026Q3`, `2026-09`,
  `2026-09-14`, vecka `2026-09-08/2026-09-14`). Alla periodformat sorteras rätt som text.
- **`record`:** `status` (`live`/`reconstructed`), `kind` (`skarp`/`rekonstruerad`), `label`, `month`, `date`,
  `file` (`snapshots/<månad>.json` när den är skarp), `first_live_date`, `live_months`, `recon_label`. Före den första
  skarpa ögonblicksbilden (2026-11-30) är allt `reconstructed` och ska ritas streckat (P9).
- **`state`:** `accelererar`, `stabil`, `bromsar in`, `för få serier`, `inga registrerade kärnserier`.
  **`direction`:** `1`, `0`, `-1` eller `null`.
- **Mått (`measure_fields`):** fälten i `site.data.SERIES_FIELDS`: `latest_period`, `known_from`, `level`, `pace`
  (`pace_unit`), `change_in_pace`, `pace_percentile`, `change_percentile`, `n_pace`, `n_change`, `surprise`
  (`surprise_basis`), `sd_change`, `deadband`, `direction`, `valid`, `reason`, `flag`, `method`, `freq`,
  `measure_freq`, `sources`, `entry`, `resolved`, `own_snapshot_months`.
- **Serie på en sida (`series_entry`):** måtten plus `key`, `label`, `unit`, `question`, `source`, `license` (kort),
  `path` (`periods`, `pace`, `change`: de tio senaste åren av måttet per period, per postens datum). I `flow.json`
  dessutom `counted`, `branch`, `in_core`, och för avstämningar `short`, `span`, `lead`.
- **Inhållen post (`withheld_entry`):** bara `key`, `label`, `source`, `license`, `why`, `counted`, `branch`. Inga tal.

### overview.json

| Fält | Betydelse |
|---|---|
| `headline.counts` | antal grenar per tillstånd |
| `headline.sentence`, `change_sentence` | rubrikmeningen ur data ("Av 7 grenar med tillstånd: 4 accelererar, 3 är stabila och ingen bromsar in.") och ändringarna sedan förra månaden |
| `headline.changes[]` | `code`, `name`, `from`, `to` för varje gren som bytt tillstånd |
| `branches[]` | grenkort: `index`, `state`, `n_series`, `n_up`/`n_neutral`/`n_down`, `previous` (förra månadens aggregat), `delta_index`, `state_changed`, `n_withheld`, `n_withheld_counted`, `has_core` |
| `stripes` | `months[]`, `kind[]` per månad, och per gren `index[]`, `state[]`, `n_series[]` i samma ordning (kolumnform). `thresholds` 0,33/0,67 |
| `calendar[]` | N1–N6 och D2: `next_origin`, `next_period`, huvudmodell, antal skarpa filer |
| `regime` | `available` och senaste värdet per block |
| `facts` | antal serier i katalogen, publicerade, inhållna, nowcasts, senaste hämtning |

### series/<nyckel>.json

| Fält | Betydelse |
|---|---|
| `key`, `label`, `unit`, `freq`, `branch`, `branch_name`, `question`, `source`, `source_family` | katalogens metadata (`Spec`) |
| `license.short`, `license.text`, `license.attribution` | kort etikett, katalogens kontrollerade licenstext, och raden som ska stå vid varje diagram och nedladdning |
| `revised`, `lag_days`, `derived_from` | källan reviderar; publiceringsfördröjning; komponenter för en härledd serie |
| `core`, `reconciliation`, `in_record`, `counted`, `record_branch` | kärnserie i registret; avstämning (A5); mätt i posten; räknad i grenens index |
| `method`, `aggregation` | måttmetod (`log`, `share`, `logit`, `doubling`, `halving`); hur dag/vecka blir månad |
| `measure_as_of`, `measure`, `measure_path` | måttet per postens datum (ur ögonblicksbilden när serien finns där) och dess bana |
| `measure_history` | postens mått varje månadsslut i ränderna, kolumnform: `months`, `kind`, `counted`, `latest_period`, `known_from`, `pace`, `change_in_pace`, `pace_percentile`, `change_percentile`, `direction`, `valid`. Bara för serier som någon gren mätte |
| `levels` | senaste versionen av varje period som var känd byggdagen (`as_of`), i seriens egen frekvens |
| `rows.counts`, `rows.backfill_last_known` | antal rader per typ (`release`, `fetch`, `revision`, `backfill`, `derived`); senaste `known_from` för bakåtfyllda rader |
| `versions` | tidsresan, avsnitt 5 |

### nowcast/n<k>.json

`publishable` (alltid `true` i dag; ett inhållet mål skulle bara behålla regeln och namnet), `id`, `title`, `target`,
`target_label`, `unit`, `source`, `license`, `decimals`, `error_unit`, `frequency`, `origin_rule`, `results_doc`,
`champion`, `shadows`, `variants[]` (`id`, `text`), `next_origin`, `next_period`, `forecasts[]` (skarpa filer:
`period`, `origin`, `value`, `variants`, `intervals` 50/80/95 för huvudmodellen, `file`; aldrig `inputs`),
`scorecard[]` (en rad per fil mot första versionen av utfallet: `forecast`, `outcome`, `err_<modell>`,
`crps_<modell>`, `pit_<modell>`, `hit_<nivå>_<modell>`, `interval_<nivå>`), `summary[]` (MAE och bias per variant),
`coverage[]` (skarp täckning med binomialband), `history` (målets senaste nivåer), `backtest_calibration` (täckning
per nivå med band, Holm, CRPS, PIT och huvudmodellens MAE i backtesten, beräknad vid bygget och alltid märkt som
backtest).

## 3. Status: skarp eller rekonstruerad

`manifest.snapshot.status` och varje `record.status` är `live` när den senaste committade ögonblicksbilden
(`snapshots/<månad>.json`) är posten, annars `reconstructed`. Månader före den första skarpa ögonblicksbilden
rekonstrueras med samma kod per månadsslut och märks `rekonstruerad`. En månad efter den första skarpa utan egen
ögonblicksbild blir en lucka och rekonstrueras aldrig (`site.data.Record`). Regimen (C4) finns bara från skarpa
ögonblicksbilder (`regime.available`).

## 4. Licensgrinden

- **Regeln** finns på ett ställe: `site.data.publishable` (Spec.publish=True; en härledd serie kräver att alla
  komponenter är publicerbara). `site_bundle.gate.publishable` anropar den och inget annat.
- **Exporten** tar bara med publicerbara serier i seriedokumenten, och nowcastmål kontrolleras på samma sätt.
- **Skanningen** (`gate.scan`) går igenom varje värde i varje dokument innan något skrivs. En inhållen nyckel (alla
  katalogserier, härledda serier och nowcastmål som inte är publicerbara) får bara stå i en lista under nyckeln
  `withheld`, och en sådan post får bara ha fälten i `withheld_entry`, utan tal. Nyckeln som ordkant i en sträng,
  som objektnyckel eller som filnamn räknas som läcka och stoppar bygget.
- **Tester:** skanningen hittar alla planterade läckor (sträng, etikett, objektnyckel, tal i en inhållen post, filnamn).
  I fixturvärlden har de två inhållna serierna värden kring 7·10⁶ och 6·10⁶, och testet kontrollerar att inget tal i
  paketet, i någon avrundning, är ett av deras värden. En skarp prognosfils `inputs` (som namnger en inhållen serie)
  kommer aldrig med. Ett test kör grinden mot den riktiga katalogen och tabellen.
- **Vad som syns av en inhållen serie:** namn och skäl i `withheld`-listorna, och att den räknas (`counted`,
  `n_withheld_counted`) i grenens aggregat. Ingen egen riktning per serie, inga värden. Beslutet 2026-11-24 ("bara
  riktningen syns") läses som grenens riktning. Om riktningen per inhållen serie ska visas som en ruta (▲ ● ▼) är
  det en ändring av grinden som granskningen R-W1 bör ta ställning till.

## 5. Versioner för tidsresa (`versions-v1`)

En serie lagrar varje distinkt period och varje distinkt `known_from`-dag en gång, och en rad per version som tre
parallella listor sorterade på (datum, period):

```json
{"encoding": "versions-v1", "freq": "M", "native_freq": "M", "aggregation": null,
 "periods": ["2016-01", "2016-02"], "dates": ["2016-02-15", "2016-03-15"],
 "p": [0, 0, 1], "d": [0, 1, 1], "v": [101.2, 101.4, 99.8],
 "n_versions": 3, "n_revised_periods": 1, "first_known": "2016-02-15", "last_known": "2016-03-15",
 "collapsed_before": null}
```

Uppspelning, exakt `observations.as_of` (rader med `known_from == D` räknas):

```js
function asOf(v, day) {            // day: "YYYY-MM-DD"
  const out = new Map();
  for (let i = 0; i < v.p.length && v.dates[v.d[i]] <= day; i++) out.set(v.periods[v.p[i]], v.v[i]);
  return out;                      // period -> värde som var känt den dagen
}
```

Regler (testade):

1. **Aldrig tidigare än `known_from`.** Varje rad är exakt en version i tabellen på sin dag. Ett `known_from` med
   klockslag flyttas till nästa dag, aldrig bakåt.
2. **Bara det som var känt byggdagen** (`known_from <= as_of`).
3. **En version som avrundad är lika med föregående version av samma period tas bort** (den ändrar ingen uppspelning).
4. **Dagliga serier lagras som kalendermånader:** för varje `known_from`-dag d registrets aggregering
   (`measures.rule_for().agg`, `to_monthly`: den månad som fortfarande fylls tas bort) av `as_of(d)`. Alla dagar som
   en månadsversion bygger på var kända dag d. De dagliga nivåerna finns i `levels`. Det gör jobbannonsserierna
   (51 000 rader var) till cirka 80 kB.
5. **Storleksskydd:** en serie med fler än 6 000 versioner får sina äldsta versioner hopslagna: allt som var känt
   före en brytdag ersätts av versionen som gällde brytdagen, daterad brytdagen (senare, aldrig tidigare).
   `collapsed_before` anger brytdagen, och tidsresa före den visar inget för serien. Ingen serie behöver det i dag.
6. **Bakåtfylld historik** har dagens version (`source="backfill"`). `rows.backfill_last_known` anger senaste
   `known_from` bland de bakåtfyllda raderna, och tidsresa till ett datum före det ska märkas rekonstruerad.

`measure_history` kompletterar versionerna för mått: den visar vad posten (skarp eller rekonstruerad) sa om serien
varje månadsslut, så att tidsresan för takt och riktning läser pipelinens siffror i stället för att räkna om.

## 6. Storlek och budgetar

Mätt på den riktiga tabellen 2026-11-24 (`python -m ai_tracker.site_bundle sizes web-data`):

| Grupp | Filer | Rå | Gzip |
|---|---:|---:|---:|
| `series/` (385 serier + index) | 386 | 3,82 MB | 1,06 MB |
| `branch/` | 9 | 202 kB | 47 kB (G7 störst, 12 kB) |
| `flow.json` | 1 | 65 kB | 18 kB |
| `overview.json` | 1 | 16 kB | 2,6 kB |
| `method.json` | 1 | 34 kB | 7,6 kB |
| `withheld.json` | 1 | 31 kB | 4,2 kB |
| `nowcast/` | 7 | 25 kB | 8,3 kB |
| `regime.json`, `letters.json` | 2 | < 1 kB | < 1 kB |
| `schema/` | 14 | 51 kB | 13 kB |
| `manifest.json` | 1 | 87 kB | – |
| **Totalt** | **422** | **4,25 MB** | **1,16 MB** |

Ett seriedokument är i median 4 kB (1,6 kB gzip), 90:e percentilen 4,5 kB gzip. De största är Fed G.17
(`us_ip_computers_m`, `us_ip_semis_m`: 135 versioner av 658 månader, 110 kB rått, 29 kB gzip) och Indeeds nio
dagliga serier (cirka 90 kB rått, 25 kB gzip, varav ungefär hälften dagliga nivåer). `series/index.json` är 143 kB
rått och 12 kB gzip. Startsidans data är 21 kB gzip. Bygget tog 2 min 12 s inklusive lagerkontrollerna.

Budgetar (rå storlek och gzip, GitHub Pages serverar gzip). Bygget stoppas om en fil eller totalen går över:

| Mönster | Rå | Gzip |
|---|---:|---:|
| `series/*.json` | 300 kB | 75 kB |
| `series/index.json` | 400 kB | 40 kB |
| `branch/*.json` | 250 kB | 40 kB |
| `flow.json` | 200 kB | 30 kB |
| `nowcast/*.json` | 200 kB | 40 kB |
| `overview.json` | 60 kB | 12 kB |
| `method.json`, `regime.json` | 100 kB | 20 kB |
| `manifest.json` | 300 kB | 60 kB |
| `withheld.json` | 80 kB | 15 kB |
| `letters/*`, `reports/*`, `letters.json` | 100–200 kB | 10–60 kB |
| `schema/*.json` | 60 kB | 12 kB |
| **Totalt** | **20 MB** | **4 MB** |
| **Startsidan** (`overview.json` + `flow.json`) | | **100 kB** (visionens "≤ 100 kB data") |

Budgetarna har ungefär 2,5 gånger marginal mot dagens största fil i varje grupp, för cirka två års tillväxt. När en
budget nås är rätt åtgärd i första hand en kompaktare form (kolumnform, kortare bana), inte en högre budget.

## 7. Fixturer (`web-data-fixtures/`)

Ett komplett paket ur en syntetisk värld (`site_bundle/synthetic.py`): 20 publicerbara serier med katalogens
riktiga nycklar, grenar, frekvenser och enheter (så att leden, grenarna och nowcastsidorna ser ut som på riktigt),
men alla etiketter börjar med "[syntetisk]", källan är "Syntetisk testkälla" och alla värden kommer ur en seedad
slumpvandring. Där finns allt som frontend behöver öva på: en skarp ögonblicksbild (2026-10) med rekonstruerade
månader före, en regimsektion med ett skifte och två brott (ett på en inhållen serie), en skarp N2-fil med intervall,
en D2-fil, backtestkalibrering för N2, reviderade serier (tre versioner per period för `us_ip_semis_m`), en daglig
serie med två omutgivningar, en avstämning, två inhållna serier som räknas i G9, ett brev och en rapport.
`manifest.synthetic` är `true`.

Fixturerna regenereras med `python -m ai_tracker.site_bundle fixtures` och är deterministiska (fast byggtid och
`git_sha = "fixture"`). Testet `test_committed_fixtures_are_the_current_synthetic_bundle` bygger om dem och jämför,
så en kontraktsändring utan nya fixturer stoppar pytest.

## 8. Så använder frontendspåren paketet

- **Bygget:** `pages-next.yml` (W4) kör `python -m ai_tracker.site_bundle build --out web-data` och sedan
  SvelteKit-bygget. Under utveckling pekar sidan på `web-data-fixtures/` (till exempel `WEB_DATA=../web-data-fixtures`).
- **Förrendering:** sidornas `load` läser `manifest.json`, `overview.json`, `flow.json`, `branch/*.json`,
  `nowcast/*.json`, `method.json` och `series/index.json` vid bygget och förrenderar SVG. Routerna för
  `/serie/<nyckel>` tas ur `series/index.json` (`entries` i SvelteKit), och `/brev/<månad>` ur `letters.json`.
- **Körtid:** seriedokumenten (med versioner) kopieras som statiska filer och hämtas först när tidsreglaget eller
  revideringsvyn används. Startsidan behöver bara `overview.json` och `flow.json` (cirka 20 kB gzip i dag).
- **Typer:** generera TypeScript-typer ur `schema/*.json` (till exempel `json-schema-to-typescript`), och validera
  med Ajv (draft 2020-12) i frontendens tester mot fixturerna. Python och frontend testas då mot samma filer.
- **Version:** frontend kontrollerar `manifest.version` (major) och vägrar bygga mot en okänd major.
- **Visning:** `record.kind` och `stripes.kind` styr streckad eller hel ram, `license.attribution` står vid varje
  diagram, `withheld`-listorna blir namngivna rutor utan värden, och `backtest_calibration` märks alltid "backtest,
  inte skarpa prognoser".

## 9. Begränsningar och öppet

- Måtthistoriken (`measure_history`) börjar vid `--history-from` (2023-01). Äldre mått finns bara som banan
  (`measure_path`, per postens datum) och kan räknas om ur versionerna men inte läsas ur posten.
- Versionerna för dagliga serier är månadsvisa. Tidsresa i dagsupplösning för dagliga nivåer finns inte.
- Bygget tar cirka två minuter på den riktiga tabellen, nästan allt i rekonstruktionen av tillstånden per månad och i
  backtestkalibreringen (samma kostnad som den gamla sidan).
- Granskningen R-W1 (licens och läckage) ska gå igenom grinden, skanningen och versionsreglerna innan paketet
  publiceras under `/next/`.
