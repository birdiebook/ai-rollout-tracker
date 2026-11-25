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
| `story/<YYYY-MM>.json` | `story` | månadens berättelse (W13, från version 1.1.0): korten som den förregistrerade urvalsregeln valde (måttregistret 2026-11-25), med text, fakta, länk och spår per kort | `/manad/<månad>` |
| `story/index.json` | `story_index` | alla månader i berättelsen med antal kort per typ | `/manad/*`, startsidans ingång |
| `report/<YYYYQn>.json` | `report` | kvartalsrapporten som data (W14, från version 1.3.0): kedjan L1–L9 över kvartalet, avstämningarna, skarpa prognoser mot utfall, regimen, data och metod, med genererade meningar | `/kvartal/<kvartal>` |
| `report/index.json` | `report_index` | alla kvartal med typ (skarp eller rekonstruerad) och rapportdag, och det första kvartal som kan bli skarpt | `/kvartal/*`, startsidans ingång |
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
| `rows.counts`, `rows.backfill_last_known`, `rows.backfill_fetched` | antal rader per typ (`release`, `fetch`, `revision`, `backfill`, `derived`); senaste `known_from` för bakåtfyllda rader; senaste hämtdag (`fetched_at`, avrundad uppåt till hel dag) för samma rader (från 1.2.0, avsnitt 5.6) |
| `versions` | tidsresan, avsnitt 5 |

### nowcast/n<k>.json

`publishable` (alltid `true` i dag; ett inhållet mål skulle bara behålla regeln och namnet), `id`, `title`, `target`,
`target_label`, `unit`, `source`, `license`, `decimals`, `error_unit`, `frequency`, `origin_rule`, `results_doc`,
`champion`, `shadows`, `variants[]` (`id`, `text`), `next_origin`, `next_period`, `forecasts[]` (skarpa filer:
`period`, `origin`, `value`, `variants`, `intervals` 50/80/95 för huvudmodellen, `file`, `commit`; aldrig `inputs`),
`scorecard[]` (en rad per fil mot första versionen av utfallet: `forecast`, `outcome`, `err_<modell>`,
`crps_<modell>`, `pit_<modell>`, `hit_<nivå>_<modell>`, `interval_<nivå>`), `summary[]` (MAE och bias per variant),
`coverage[]` (skarp täckning med binomialband), `history` (målets senaste nivåer), `backtest_calibration` (täckning
per nivå med band, Holm, CRPS, PIT och huvudmodellens MAE i backtesten, beräknad vid bygget och alltid märkt som
backtest).

**`commit` (från 1.2.0, R-W1 4a).** `{sha, date}` för den commit som lade till filen (`git log --diff-filter=A
--format=%H%x09%cI -- <fil>`, första raden, alltså det senaste tillägget), med datumet i UTC
(`YYYY-MM-DDTHH:MM:SSZ`). Det är prognosens tidsstämpel, och prognossidan länkar exakt den commiten
(`commit/<sha>`). `null` betyder att bygget saknade git-historiken (till exempel en grund klon). Sidan visar då filen
som "väntar på verifiering", aldrig som skarp. Båda Pages-workflows checkar ut med `fetch-depth: 0`. Bygget stoppas
(`export.CommitError`) om en poängsatt fil committades samma dag som eller efter utfallets `known_from`.
`nowcast/d2.json` har samma fält för sin senaste fil (`commit` bredvid `file`).

### story/<YYYY-MM>.json (W13)

Byggs av `site_bundle.story` för varje månad i posten. `select` är regeln: en ren funktion av månadens post, förra
månadens post, avstämningarna (A5) för båda, de skarpa prognosfilernas scorecard och C4-sektionen. Samma indata ger samma
dokument.

| Fält | Betydelse |
|---|---|
| `month`, `month_sv`, `kind`, `status` | månaden och om posten är skarp eller rekonstruerad |
| `known` | dagen månadens post blev känd (månadsslutet, eller den skarpa ögonblicksbildens datum om det är senare). Inget i dokumentet blev känt senare |
| `previous` | jämförelsemånaden, `null` utan jämförelse |
| `rule` | registrets avsnitt, tak (8), tak per typ, zonerna (≤ 5, ≥ 95) och typordningen |
| `headline`, `n_events`, `types` | rubrikmeningen och antal kort per typ K1–K6 |
| `qualified`, `omitted`, `withheld` | per typ: publicerbara kandidater före taken, de som ströks av taken, och inhållna serier som uppfyllde villkoret (räknas, namnges aldrig) |
| `cards[]` | `type` (K0–K6, K9), `type_label`, `id`, `rank`, `status`, `title`, `text`, `direction` (bara riktning, för färgen), `link` (`kind`: start, branch, series, nowcast, regime, method), `facts` (schema per typ) och `track` (postens värde per månadsslut för kortets serie, K4–K6) |

Sidan klipper varje figur till `known` med tidsresans gräns (`web/src/lib/timetravel/gate.ts`) och vägrar bygga om något
på sidan blev känt senare.

### report/<YYYYQn>.json (W14)

Byggs av `site_bundle.report` för varje helt kvartal i postens historik. Innehållet är `ai_tracker.quarterly`s egna
fakta (`summary_facts`, `flow_facts`, `forecast_facts`, `regime_facts`, `data_facts`), samma funktioner som
Markdown-rapporten renderar, matade med postens månader (`site.data.Record`: den skarpa ögonblicksbilden, annars
rekonstruktionen vid månadsslutet, alltså det som ränderna visar). Inget räknas om: tillstånd, index, kvoternas mått,
prognosfel, intervall och C4 kommer ur posten, de committade prognosfilerna och ögonblicksbilderna, och tabellen kapas
vid kvartalets slut (`quarterly.make_inputs`).

| Fält | Betydelse |
|---|---|
| `quarter`, `quarter_sv`, `title`, `kind`, `status` | kvartalet; `skarp` bara när alla tre månaderna har en skarp ögonblicksbild |
| `start`, `end`, `known` | kvartalet och rapportdagen: dagen då kvartalets sista månadsläge blev känt (månadsslutet, eller ögonblicksbildens datum om det är senare). Inget i dokumentet blev känt senare |
| `months`, `base` | kvartalets tre månader och jämförelsemånaden, med typ, känd-dag och ögonblicksbildens fil |
| `recon_note` | varför kvartalet är rekonstruerat (`null` för ett skarpt). Den första skarpa kvartalsrapporten gäller 2027Q1 med den första ögonblicksbilden 2026-11-30 (`report/index.json` `first_live`) |
| `headline`, `summary` | rubrikmeningen, sammanfattningens meningar, antal grenar per tillstånd, tillståndsbyten, grenar som bytte mer än en gång, största indexförändringar |
| `branches[]` | per gren index och tillstånd vid varje månadsslut (`path`), förändring över kvartalet, serier som bytt riktning (`flips`) |
| `chain[]` | L1–L9: grenar, kvoter som rör ledet och en mening (tillståndsbyten och avstämningar) |
| `ratios[]`, `n_ratios_withheld` | avstämningarna vid kvartalets slut med postens mått och nivån före kvartalet |
| `nowcasts[]`, `nowcast_news` | per nowcast skarpa filer med prognosdag till och med kvartalets slut, nya i kvartalet, utfall som blev kända i kvartalet med huvudmodellens lagrade intervall, rullande utvärdering per variant (MAE, bias, mot naiv baslinje, täckning med binomialband), byten av huvudmodell |
| `regime` | C4 per block och månad som lagrat i de skarpa ögonblicksbilderna, skiften och brott (inhållna serier bara räknade) |
| `data` | kärnserier in och ut, revideringar, guidance, inaktuella serier, granskningar och registerändringar daterade i kvartalet. BLOCKED-källor (dagens läge) och nya serier i ett rekonstruerat kvartal (dagens hämtdatum) tas inte med |
| `withheld` | inhållna serier som sista månaden räknade eller mätte, bara namn |

Sidan klipper varje figur (ränder, grenhistorik, kvotens och prognosmålets nivåer) till `known` med tidsresans gräns och
vägrar bygga om något på sidan blev känt senare.

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
- **Den byggda sidan** (`python -m ai_tracker.site_bundle scan-build web/build --src web/src`, R-W1 1b, ett steg i
  `pages-next.yml` efter bygget): grinden ovan ser bara paketet, men frontend har också data som skrivits in för hand
  i `web/src` (`holdout.ts`, `reconciliations.json`, `rules.json`). Skanningen läser bygget: `data/` med
  `gate.scan`, `**/__data.json` (SvelteKits laddata, devalue) efter uppackning med samma regel, `**/*.html` med
  varje `withheld:[…]` bortklippt (inga inhållna nycklar i resten; etiketter får stå i markeringen, eftersom sidorna
  namnger inhållna serier med skäl), samt `_app/**/*.{js,json,css}` och alla källfiler under `web/src` (inga
  inhållna nycklar och inga inhållna etiketter alls). En planterad nyckel i en konstant stoppar bygget
  (`tests/test_site_bundle_rw1x.py`).
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
6. **Bakåtfylld historik** (`source="backfill"`) har versionen från dagen raderna hämtades, inte från dagen
   perioderna först publicerades. Deras `known_from` är en regel (periodslut plus fördröjning) och säger därför inte
   när värdet blev känt i den form det har. `rows.backfill_last_known` anger senaste `known_from` bland de
   bakåtfyllda raderna och `rows.backfill_fetched` (från 1.2.0) den senaste hämtdagen för samma rader, avrundad uppåt
   till hel dag. Tidsresa till ett datum före `max(backfill_last_known, backfill_fetched)` märks rekonstruerad
   (`versions.ts` `backfillUntil`), och noten anger båda dagarna. Före rättningen R-W1 3a användes bara regeldagen.
   Då visades till exempel `us_elec_sales_com_*` (regeldag 2013-01-29, hämtad 2026-11-23) omärkta under en
   tidsresa till 2020. I det riktiga paketet 2026-11-25 har 105 publicerade serier bakåtfyllnad, och för 43 av dem
   ligger hämtningen mer än 7 dagar efter regeldagen (18 mer än 30 dagar, 17 mer än 180). Testerna:
   `tests/test_site_bundle_rw1x.py` (Python, även mot den riktiga tabellen), `timetravel.test.ts` (varje
   bakåtfylld serie i paketet, fixturer eller `TT_BUNDLE`), golden-filen (`backfilled` per prov-dag) och
   `rw1.spec.ts` (sidan märker fallet i webbläsaren).
   Samma regel gäller grenposterna: en serie som bakåtfylls efter den första skarpa ögonblicksbilden ändrar inga
   skarpa månader (de läses ur ögonblicksbilderna), och rekonstruerade månader före dess `backfill_fetched` märks
   rekonstruerade.

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
| `story/*.json`, `story/index.json` | 60 kB | 12 kB |
| `report/*.json` (`report/index.json` 60 kB / 12 kB) | 120 kB | 24 kB |
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

## Ändringar

Versionerna 1.1.0–1.3.0 kom från webbsessionen och beskrivs i avsnitten ovan: 1.1.0 `story/` (W13), 1.2.0
`rows.backfill_fetched` och `commit` per skarp prognos (RW1-X), 1.3.0 `report/` (W14). Spår K1 skrev sin ändring som
1.1.0 på sin egen gren innan main hade gått vidare. Vid mergen 2026-11-25 fick den numret 1.4.0.

### 2026-11-24 – 1.4.0: diffusionsindex v2 med källfamiljer (spår K1, numrerad vid mergen 2026-11-25)

En minor. Bara tillägg, och inga fält är borttagna eller har bytt typ. `index` och `state` har kvar sina namn. Det
som ändras är regeln bakom dem, och den anges i `rule_version`. Ett paket 1.3.0 läses alltså som förut av en frontend
för 1.x, som bara saknar de nya fälten och tillståndet nedan.
- `index` och `state` är den officiella regeln. Från ögonblicksbilden 2026-11-30 är det v2: en röst per källfamilj
  (`docs/mattregister.md`, 2026-11-24). `rule_version` anger regeln. En post skriven före v2 saknar fältet i
  ögonblicksbilden och får `"v1"` i paketet.
- Nytt tillstånd i `common.json#/$defs/state`: `"för få källor"` (färre än 3 räknade källfamiljer). `"för få serier"`
  finns kvar för v1.
- `branch/<G>.json`: `rule_version`, `n_families`, `index_v1`, `state_v1`, `families[]` (`family`, `series`,
  `n_series`, `vote`) och `n_families_withheld`. `families` tar bara med räknade familjer vars räknade serier alla får
  visas. En familj med en innehållen serie räknas i indexet och i `n_families`, men namnges inte och har ingen röst i
  paketet (`n_families_withheld`).
- `overview.json`: rutorna har samma fält, och `stripes.rows[]` har `n_families`, `index_v1` och `state_v1` per månad.
  `previous` och `history` (`$defs/aggregate`) har `rule_version`, `n_families`, `index_v1` och `state_v1`.
- `flow.json`: ledens grenar har `n_families` och `rule_version`.
- `method.json`: `rules.index_rule`, `rules.min_families` och `branches[].families` (registrets familjetabell med
  `family`, `entries` och `n_withheld`).
- `families[].family` är källfamiljen i indexet. Det är inte samma sak som `series.source_family`, som är källans namn
  i licenstabellen.
- Fixturerna är regenererade. `us_ip_computers_m` är ny i den syntetiska världen, så att G6 har en familj med två
  serier.
- Tillägg vid mergen 2026-11-25: `story/<YYYY-MM>.json` K0:s `facts.counts` har nyckeln `"för få källor"` när en gren
  har det tillståndet (schemat tillåter redan nya nycklar). K5 och K6 prövar bara publicerbara serier
  (registerändringen 2026-11-25, L3-1), så `withheld.K5` och `withheld.K6` är 0 och `chance.n` räknar bara dem.

## Läsanvisningar för körning 13

Underlag för webbsessionen, 2026-11-24. Per nytt mått: vad det visar, hur det läses och det viktigaste förbehållet.
Inget av måtten nedan är kärnserie. Bara index v2 ändrar hur grenarnas tillstånd räknas.

**Index v2 (`index`, `state`, `rule_version`, `n_families`, `families[]`, `index_v1`, `state_v1`).** Indexet ger en
röst per källfamilj, inte per serie. En familj är serier från samma källa och med samma begrepp, till exempel nio
länder ur Indeeds data. `index` och `state` är den officiella regeln från ögonblicksbilden 2026-11-30, och `index_v1`
och `state_v1` står bredvid för jämförelse. Med färre än tre familjer visas indexet men inget tillstånd ("för få
källor"), och med få familjer väger varje familj tungt, så indexet kan röra sig mer än med v1.

**Förväntningar mot utfall (avsnittet `expectations` i ögonblicksbilden).** Revideringsindexet är andelen höjningar
av bolagens egen guidance (oförändrad räknas som en halv), över fyra kvartal och med minst tre revideringar. Över 0,5
betyder fler höjningar än sänkningar. Överraskningen är utfallet mot bolagets guidance i log ×100, och
överraskningsindexet är medel av standardiserade överraskningar (z) över minst två bolag. Förbehåll: få händelser per
kvartal (n står bredvid), ingen takt, och serierna som läser `curated/guidance_capex.csv` har `publish=False` tills
ägaren beslutar (R11-4). Avsnittet finns i ögonblicksbilden men inte i paketet än.

**Intäktskravet (`x_dep_rev`, `x_capcost_rev_r08`, `x_capcost_rev_r12`, `x_dep_capex`, `x_dep_rev_aws`).**
Avskrivningar, och avskrivningar plus 8 eller 12 % på det bokförda nettot, som procent av intäkterna för MSFT, GOOGL,
AMZN och META över fyra kvartal. `x_dep_capex` är avskrivningar som procent av capex, och AWS-kvoten gäller bara
segmentet. En stigande kvot betyder att kapitalkostnaden växer snabbare än intäkterna, och en fallande `x_dep_capex`
att capex växer snabbare än avskrivningarna. Förbehåll: alla anläggningstillgångar och alla intäkter, inte bara AI, r
är ett antagande, och historiken börjar 2023Q4. Kvoterna står i gruppen "Avstämningar" och räknas aldrig i ett
grenindex (`docs/resultat/intaktskrav.md`).

**Avskrivningar och anläggningstillgångar (`dep_*`, `dep_ppe_*`, `ppe_net_*`, `ppe_gross_*`, `dep_hyp4`, `dep_aws`).**
Avskrivningar per kvartal och bokfört värde av anläggningstillgångar per bolag, ur SEC och daterade med
inlämningsdagen. Måtten visar var capex hamnar i resultaträkningen: dagens capex blir avskrivningar under flera år.
Förbehåll: raderna har olika innehåll per bolag (Microsofts "other", Amazons leasing och innehåll, Metas immateriella
tillgångar). Omräkningar är egna versioner, så den första och den senaste versionen av ett kvartal kan skilja sig.

**Nyttjandeperioder (`useful_life_<klass>_<bolag>_lo` och `_hi`).** Hur många år bolagen skriver av servrar och
nätverksutrustning, extraherat ur 10-K, 10-Q och 8-K med citat. Serierna är glesa stegvärden: ett värde finns bara där
ett dokument anger det, så visa senast kända värde. Jämför över tid med det högsta värdet, eftersom det lägsta kan
sjunka när ett dokument går från en punkt till ett intervall. Förbehåll: en längre period sänker avskrivningarna utan
att kapaciteten ändras.

**N7 (avskrivningar 1–8 kvartal framåt) är bara ett backtest.** Ingen variant klarade regeln, och drift (B1) är
huvudmodell i alla horisontgrupper (`docs/resultat/n7.md`, omkört efter rättningen X11). Det finns ingen skarp N7,
inga filer i `forecasts/` och inget N7 i paketet. Visa det som ett negativt resultat, inte som en prognos.

**BNP-bidrag, elpris och PPI (M1).** `us_gdp_contrib_*` och `ai_invest_contrib_gross` är bidrag till USA:s reala
BNP-tillväxt i procentenheter i årstakt (BEA tabell 1.5.2), med riktiga versioner ur BEA:s releasearkiv.
`us_imp_computers_*` är import av datorer, och KPI för el (`us_cpi_electricity_*`) och PPI för databehandling och el
(`us_ppi_*`) är BLS-index. Visa bidragen bredvid `us_gdp_real_growth`, men räkna ingen kvot, eftersom den blir
instabil när tillväxten är nära noll. Förbehåll: kategorierna är bredare än AI, importen är inte avdragen i
bruttobidraget, och KPI saknar oktober 2025.

**Import per land (M2) och Census-notisen.** `us_imp_eu<kod>_<land>_a` är USA:s årliga import av datorer (21300),
datordelar (21301) och halvledare (21320) per land 2016–2025, i MUSD. Visa fördelningen mellan länderna och
förändringen mellan år. Varje år blir känt 10 juli året efter. Månadsserierna per HS-kod (`us_imp_hs*_m`) väntar på
`CENSUS_API_KEY` och har inga rader än. När de har rader ska notisen "This product uses the Census Bureau Data API but
is not endorsed or certified by the Census Bureau." stå med serien och i sidfoten. Paketet lägger den redan sist i
`license.attribution`.

**Webbgrindar efter integrationen (2026-11-25).** Huvudet på `auto14/integration13` efter mergen av `main` (W12–W14,
paket 1.3.0) och rättningarna efter granskningen L1/L3. Paketet är 1.4.0. Siffrorna ersätter dem från 2026-11-24
(20 röda tester), som inte räknade med det riktiga paketet.
- **Gröna mot fixturerna:** `npm ci`, `npm run check` (0 fel, 0 varningar), `npm run build` med
  `BASE_PATH=/ai-rollout-tracker/next`, `python -m ai_tracker.site_bundle scan-build web/build --src web/src` (0 träffar)
  och Playwright med `PW_PORT=4319` (548 gröna, 2 överhoppade). Bygget mot det riktiga paketet och
  skanningen av det är också gröna.
- **`npm test` mot fixturerna: 20 röda av 396**, i två filer.
  - `src/lib/method/engine.test.ts`, 18 tester. "dead band: golden values from state.branch with the dead band moved":
    "every probed dead band" och "the index steps agree with the probes" för G1, G2, G5, G6, G7 och G8 (12). "registered
    parameters reproduce the record in web-data-fixtures" för G1, G2, G5, G6, G7 och G8 (6). Motorn räknar v1: den ger
    "för få serier" där paketet har "för få källor", och v1:s index där paketet har v2:s.
  - `src/lib/start/model.test.ts`, 2 tester. "start data … uses the pipeline headline and generates the chain sentence
    from flow.json": `countsSentence` skriver "1 bromsar in", Python "en bromsar in". "fixture specifics > shows the
    live N2 forecast and its champion backtest": grenarna med ändrat tillstånd är nu `['G6']`, testet väntar
    `['G6', 'G9']`.
- **`npm test` med det riktiga paketet, som i `pages-next.yml`** (`SITE_BUNDLE_DIR` och `REQUIRE_REAL_BUNDLE=1`, ingen
  `static/data` i en ny utcheckning): **23 röda av 410.** De 20 ovan och "registered parameters reproduce the record in
  <paketet>" för G1 ("för få serier" mot "för få källor"), G6 (index 0,7222 mot 0,7857) och G8 ("accelererar" mot
  "för få källor").
- **Med `static/data` synkad från det riktiga paketet** (efter `npm run build` eller `npm run sync-bundle` lokalt, som i
  granskningen L1): **24 röda av 410.** Den 24:e är `src/lib/regime/regime.test.ts` "page loads against the bundle >
  every visible reconciliation has its components; withheld ones carry no values" (0 komponenter). Den beror på P2b,
  inte på index v2: paketet har P2b:s fem avstämningar, men `regime/reconciliations.json` speglar dem inte.
- **Följd för Pages.** `pages.yml` tar bara med `/next/` när `pages-next.yml` lyckas. Efter en push till `main`
  publiceras den gamla sidan som förut men utan `/next/`, tills vitest är grön. Johannes väljer före 2026-11-30 om det
  är acceptabelt, eller om webbrättningen ska landa först (STATUS, punkt 6).

Webbsessionen behöver:
- lägga till tillståndet "för få källor" i `design/state.ts`, `data/types.ts`, `start/model.ts` (`State`, `VERB`,
  `asState`, räkningarna), `timetravel/gate.ts` och `start/Hero.svelte`;
- räkna index v2 i metodsidans motor (`method/engine.ts`, `prepare.ts`): en röst per källfamilj ur
  `method.json#branches[].families` och minst `rules.min_families` familjer, med v1 bredvid;
- skriva "en" för 1 i `countsSentence`, som Python gör (`site_bundle.export._sv_number`);
- uppdatera de fixturberoende förväntningarna i `start/model.test.ts` (ändringarna är nu bara G6);
- spegla P2b:s fem avstämningar i `regime/reconciliations.json` med fältet `weight` på termen `ppe_net_hyp4` (0,08 och
  0,12; termer utan fältet har vikten 1), och multiplicera med vikten i `recon.ts` `side()`. Då blir
  `regime.test.ts` grön. `tests/test_web_regime_constants.py::test_reconciliation_terms_match_avstamning` kontrollerar
  vikten, och `test_web_mirrors_every_reconciliation` är strikt xfail tills alla tio är speglade;
- veta att K0 i `story/<månad>.json` nu kan ha nyckeln "för få källor" i `facts.counts` (registerändringen
  2026-11-25), och att K5 och K6 inte längre räknar inhållna serier (`withheld.K5` och `withheld.K6` är 0).

## Följda frågor

En följd fråga är en fråga som Johannes läser varje månad, utanför grenarna. Den har en registerpost, katalogserier med
`publish=False` och en rapport (`python -m ai_tracker.followed <fråga> --as-of ÅÅÅÅ-MM-DD [--json PATH]`). Den har
inget tillstånd, inget index och inga kärnserier, och den finns inte i paketet än.

**Kreditlagret (KL1, `kl_*`, `docs/resultat/kreditlagret.md`).** Frågan: "Ändras finansieringens pris och tillgång i
de yttre lagren, och följer investeringstakten där med?" Läs kedjan i ordning: pris på skuld (effektiv ränta, spread
vid emission, CoreWeaves vägda ränta), beroende (capex som inte bärs av kassaflödet, nettoemission och tecknade
leasingavtal, allt i procent av capex) och vilja och förmåga (capex och RPO-tillskott över fyra kvartal, guidance,
CoreWeaves effekt). Yttre lagret (Oracle, CoreWeave, Nebius, IREN) står mot det inre (Microsoft, Alphabet, Amazon,
Meta). Varje mått har nivå, takt, förändring i takt och överraskning mot den naiva baslinjen. Läsregeln ger ett
mekaniskt utslag per lager och per yttre bolag: talar för mekanismen, talar emot (1 eller 2), blandat, inget av
mönstren eller kan inte avgöras. Visa alltid talen bredvid utslaget, eftersom gränserna är fasta. En negativ förändring i
takt betyder att tillväxten avtar, inte att capex minskar. Förbehåll: 8–12 kvartal per mått, så det är en beskrivning
och inget test. RPO är klumpig. Neomolnens serier börjar 2024, så yttre lagrets förändring i takt finns först med
2026Q4. Labbens (Anthropic och SpaceX, som äger xAI) och Metas belopp är tabellrader ur inlämningarna, inte serier.
SpaceX:s skuld gäller hela koncernen. Regeln läser bara uppgång i pris och beroende, och rapporten anger hur ofta A har
gällt. Microsofts effektiva ränta innehåller ränta på finansiell leasing. Lägg aldrig till larmnivåer eller en
sammanvägd siffra.
