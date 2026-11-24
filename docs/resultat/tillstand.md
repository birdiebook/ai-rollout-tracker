# Tillstånd per gren: mått, diffusionsindex och månatlig ögonblicksbild (fas 5, spår F5)

Byggt 2026-11-23 enligt måttregistret (`docs/mattregister.md`, avsnitt 1, 2 och 5 samt ändringarna
2026-11-23). Registret är inte ändrat. Kod: `src/ai_tracker/state/`, tester: `tests/test_state.py`,
arbetsflöde: `.github/workflows/snapshot.yml`.

| Del | Fil | Vad |
|---|---|---|
| Regler som data | `state/register.py` | Kärnserier per gren (speglar registrets tabell ordagrant), trösklar, lagg, minsta historik, undantag för bakåtfyllt, härledda serier |
| Mått per serie | `state/measures.py` | Transform, månadsaggregering, takt, förändring i takt, percentiler, expanderande SD, riktning, överraskning |
| Gren | `state/branch.py` | Aktiv BTOS-regim, riktning per serie, diffusionsindex, tillstånd |
| Ögonblicksbild | `state/snapshot.py` | `snapshots/<YYYY-MM>.json`, backcast till `outputs/state_backcast.csv` |
| CLI | `python -m ai_tracker.state` | `snapshot --date`, `backcast --start --end`, `due`, `show --date` |

Kärnserielistan finns på ett ställe, `CORE_SERIES` i `state/register.py`, skriven med registrets egna förkortningar
(`us_elec_sales_com_{va,tx,...}_m`, `btos_ai_use_<aktiv regim>`). Ett test läser registerfilen och kräver att den och
`CORE_SERIES` är identiska. G1 och G9 registrerades 2026-11-23 och finns i `CORE_SERIES` (spår F6, se nedan). Metoden per
serie följer katalogens enhet och gren: enhet som börjar med `%` ger andel, enhet som anger 0–1 ger logit, och övriga
G1- och G2-serier ger fördubblings- respektive halveringstid. Avvikelser läggs i `METHOD_OVERRIDES`.

## Hur reglerna är implementerade

- **as_of.** Varje värde hämtas med `observations.as_of(serie, dag)`. Percentiler och standardavvikelse beräknas
  över måttets egna värden för de perioder som är kända på dagen. Två läckagetester (syntetiska data): rader med
  `known_from` efter dagen påverkar inget mått, och en omräkning från en tabell som är kapad vid dagen ger identiskt
  resultat. Samma kontroll på riktiga data för 2024-09-30 och 2025-06-30 gav identiskt resultat.
- **Transform och takt.** Positiva storheter: log ×100, årsförändring (12 mån, 4 kv, 1 år). Andelar: förändring i
  procentenheter över samma lagg. Förändring i takt: 6 mån, 2 kv eller 1 år.
- **Percentiler** kräver minst 24, 8 eller 5 värden av måttet självt (takt respektive förändring i takt). Annars
  visas måttet utan percentil.
- **Riktning:** +1 om förändring i takt > 0,25 × expanderande SD, −1 om < −0,25 × SD, annars 0.
- **Diffusionsindex** = (antal +1 + 0,5 × antal 0) / antal räknade serier. **Tillstånd:** accelererar om ≥ 0,67,
  bromsar in om ≤ 0,33, annars stabil. Med färre än 3 räknade serier visas indexet men tillståndet blir "för få serier".
- **`capex_ocf_hyp4`** = 100 × `capex_hyp4` / `ocf_hyp4` för samma kvartal. En rad bildas vid varje ny version av
  någon av de två, med `known_from` = den senare av de två. Serien behandlas som andel, så takten är förändringen i
  procentenheter över 4 kvartal.
- **BTOS** räknas bara inom en regim (`btos_ai_use_v1`, `_v2`, `_v3` och så vidare).
- **Ögonblicksbilden** innehåller datum, git-sha, UTC-tid, sha256 av registerfilen och reglerna. Per gren finns
  index, tillstånd och antalen +1, 0 och −1. För varje serie finns mått, senaste period, `known_from` för den
  perioden och vilka `source`-etiketter som ingår. Serier som inte räknas listas med skäl.

## Tolkningar (oklarheter, löst med den försiktigaste läsningen)

Punkterna 1, 7 och 8 bör orkestreraren ta ställning till och registrera.

1. **"Bara observationer kända vid månadens slut används" (månadsaggregering).** Implementerat som: månaderna
   aggregeras ur `as_of(beräkningsdagen)`, alltså en enda version. Dessutom tas den sista månaden i seriens data
   alltid bort, eftersom den kan vara ofullständig. En månad används alltså bara när serien har en observation i en
   senare månad. På en ögonblicksdag (månadens slut) betyder det just att bara observationer som var kända vid
   månadens slut används. Den bokstavliga alternativa läsningen är att varje historisk månad aggregeras ur den
   version som fanns vid just den månadens slut. Den valdes bort av tre skäl: den strider mot avsnitt 1:s
   huvudregel (allt via `as_of` på beräkningsdagen), den blandar versioner med olika metod (Indeed lade om metoden
   2024-07 och 2024-09, och G.17-index byter basår mellan versioner), och den lämnar nästan inga Indeed-månader kvar.
   Indeed-versionerna kommer ungefär en gång i månaden med 4–78 dagars fördröjning, så en månads dagar är sällan
   kända vid samma månads slut. Båda läsningarna är fria från läckage.
2. **Vilken månad en observation hör till:** den månad perioden slutar i. En BTOS-fjortondagarsperiod som slutar
   2025-10-05 hör alltså till oktober. Aggregering sker med medelvärde för andelar, priser och index och med summa för
   flöden, styrt av enheten (`AGG_OVERRIDES` vid behov).
3. **Percentil:** andelen av historiken under värdet, där lika värden räknas till hälften. Historiken omfattar det
   aktuella värdet.
4. **Expanderande SD:** stickprovs-SD (ddof = 1) av förändring i takt fram till och med senaste perioden. Den
   kräver minst 2 värden. Utan SD finns ingen riktning, och serien räknas då inte. Det träffar i dag Eurostats
   årsserier, som bara har ett värde för förändring i takt (2025).
5. **Senaste period:** måtten tas vid seriens senaste kända period. Saknas förändring i takt där, till exempel vid en
   lucka, räknas serien inte. Måttet hämtas inte från en äldre period.
6. **Fördubblings- och halveringstid (G1, G2):** frontvärdet är löpande max för förmåga och löpande min för pris.
   Alla 24 månader i fönstret måste finnas. En lutning med fel tecken, till exempel ett pris som inte faller, ger
   ingen tid och alltså inget mått. Förändring i takt = tiden nu minus tiden 12 månader tidigare.
7. **Tecken för tidsmått.** En kortare fördubblings- eller halveringstid betyder snabbare takt. Riktningen räknas därför på
   −(förändring i tid), så att +1 betyder acceleration också här. En bokstavlig läsning (+1 när tiden ökar) skulle
   kalla en inbromsning för acceleration och strida mot avsnitt 2:s mening. Påverkar i dag ingenting, eftersom
   G2-serien bara har 21 månader.
8. **Ingen regel för inaktuella serier.** Registret säger inget om hur gammal den senaste perioden får vara. En
   serie räknas därför med sin senaste kända period, och `latest_period` och `known_from` visas i ögonblicksbilden.
   Exempel: `rev_nvda` (räkenskapskvartal) ligger ett kvartal efter de andra.
9. **Logit (G1-benchmarks):** frontvärde = löpande max, och takten anges i logit-enheter
   (utan ×100). Riktning och percentiler påverkas inte av skalan. En andel 0–1 utanför G1
   (`g9_epoch_open_weights_share`) mäts som andel i procentenheter (×100, `METHOD_OVERRIDES`).
10. **Överraskning:** utfall minus den skarpa nowcasten när `forecasts/n1|n2/<period>.json` finns och dess origin är
    ≤ beräkningsdagen. Annars utfall minus B1 enligt avsnitt 3 (drift = förra värdet plus medel av de 4 senaste
    förändringarna), på seriens transformerade skala: log ×100, procentenheter eller logit. B1 tar inte hänsyn till
    säsong, så för de ej säsongsrensade serierna (G7 och importserierna) blir överraskningen till stor del
    säsongsmönster. Överraskningen ingår inte i tillståndet.
11. **Aktiv BTOS-regim:** den regimserie (`btos_ai_use_v<n>`) vars senast kända observation slutar sist på
    beräkningsdagen. Ingen återgång till en äldre regim sker när den aktiva är för kort. Standardfelsserierna
    (`_se`) ingår inte. Följd: från 2025-12 är v2 aktiv men för kort, och från 2026-11 är v3 aktiv.
12. **Undantag för bakåtfyllt:** gäller `g2_price_at_capability` (ECI-varianten), `g1_epoch_eci_frontier`,
    `g9_epoch_notable_models` och `g9_epoch_open_weights_share` (`BACKFILL_GATED`). `g1_epoch_train_compute_frontier`
    räknas men flaggas (`BACKFILL_FLAGGED`, fältet `flag`). De beskrivs men räknas inte förrän det finns 24 kalendermånader (räknat
    på `known_from`) med egna rader, alltså rader som inte är backfill. Därefter beräknas måtten bara på de egna
    raderna. `g2_price_at_capability_gpqa` har också `source="backfill"`, men registret anger den som kärnserie och
    undantar bara ECI-varianten, så den räknas. Den har ändå för kort historik. De lagdaterade kärnserierna
    (`us_constr_datacenter`, importserierna, BEA-investeringar och Eurostat) räknas enligt registret. Deras
    `sources` visar `backfill`.
13. **Tröskeljämförelsen** görs på det oavrundade indexet: 2/3 = 0,667 är under 0,67 och ger stabil, och 1/3 = 0,333
    är över 0,33 och ger också stabil.
14. **Ögonblicksdag:** registret anger ingen dag. Vald dag är sista kalenderdagen i månaden. `as_of(dag)` tar med
    rader med `known_from` ≤ dagen kl. 00:00. Det som publiceras senare samma dag kommer alltså med först i nästa
    månads ögonblicksbild, och resultatet går att räkna om exakt. Skrivaren vägrar datum i framtiden, datum som inte
    är månadsslut och befintliga filer (öppnas med `x`). `pipeline publish` committar bara nya
    `snapshots/<YYYY-MM>.json`.

## G1 och G9 (spår F6)

Registrerat 2026-11-23 (måttregistret, posterna "G1 och G9: avslutade benchmarks …" och "G1: urvalsregeln tillämpad").

| Gren | Kärnserie | I tillståndsmotorn |
|---|---|---|
| G1 | `g1_epoch_bench_frontier_<valda>` | En serie per vald benchmark på beräkningsdagen (`Context.selection`, som standard `series.epoch_hub.selected_on`): `frontiermath_erdos` och `spireclimb`. Logit av löpande max |
| G1 | `g1_epoch_train_compute_frontier` | Räknas, flaggas som bakåtfylld. Fördubblingstid |
| G1 | `g1_epoch_eci_frontier` | Spärrad tills det finns 24 månader egna ögonblicksbilder |
| G9 | `g9_arxiv_cs_ai`, `g9_arxiv_cs_lg`, `g9_arxiv_cs_cl` | Räknas. Log ×100 |
| G9 | `g9_epoch_open_weights_share`, `g9_epoch_notable_models` | Spärrade tills det finns 24 månader egna ögonblicksbilder |

15. **`<valda>`.** Platshållaren löses upp till frontserierna för de benchmarks som är valda på beräkningsdagen.
    Det är den registrerade listan med registrerade byten (`REPLACEMENTS`) tillämpade från sina datum. Före urvalsdagen
    gäller den registrerade listan. En vald benchmark räknas inte (`branch.benchmark_guard`) när dess frontvärde,
    känt på dagen, är > 0,90, eller när dess senaste kända månad med Epoch-körning slutade mer än 90 dagar före dagen.
    Det gäller även innan bytet har registrerats. En vald serie som saknas i katalogen listas med skäl.
    Ögonblicksbilden redovisar urvalet under `rules.g1_selected_benchmarks`.
16. **Benchmarkdatum:** `Started at` + 30 dagar per körning, och månad m blir känd första dagen i m+1 + 30 dagar.
    Se `docs/kallor/epoch_arxiv.md`. Därför har `frontiermath_erdos` bara 2026-08 och 2026-09 kända 2026-11-23,
    och `spireclimb` har inga kända värden före 2026-12-31. Ingen av dem har takt i backcasten.

## Drift

`snapshot.yml` körs dagligen 22:41 UTC, med ett nytt försök 23:29 UTC. Det första steget (`python -m ai_tracker.state
due`) avslutar jobbet om det inte är månadsslut i UTC eller om filen redan finns. På månadsslut återställs
datacachen (`ai-data-`, gruppen `ai-data`), och sedan körs `pipeline weekly` (hämtning plus datatester; ett
underkänt test stoppar jobbet innan något skrivs). Därefter skrivs ögonblicksbilden för det datum som första steget
satte, och bara den nya filen committas med bot-identiteten. Den första skarpa ögonblicksbilden blir
`snapshots/2026-11.json`, som skrivs 2026-11-30. Den skrivs inte nu, eftersom datumet ligger i framtiden.

## Historisk backcast (rekonstruktion, inte ett skarpt register)

`python -m ai_tracker.state backcast --start 2019-01 --end 2026-10` skriver `outputs/state_backcast.csv`
(gitignorerad), med en rad per månad och gren. Varje rad har kolumnen `label` = "rekonstruerad (as-of-backcast,
inte ett skarpt register)". Det skarpa registret börjar med den första committade ögonblicksbilden. Det här är
första gången måtten tittas på. Siffrorna redovisas utan tolkning.

Index (oavrundat, 3 decimaler), tillstånd och antal räknade serier, de sex senaste månaderna. Körd om 2026-11-23
i spår F6 med G1 och G9 registrerade. G4 har sedan F5 segmentserierna som kärnserier.

| Gren | 2026-05 | 2026-06 | 2026-07 | 2026-08 | 2026-09 | 2026-10 |
|---|---|---|---|---|---|---|
| G1 | 0,500 för få (1) | 0,500 för få (1) | 0,500 för få (1) | 0,500 för få (1) | 0,500 för få (1) | 0,500 för få (1) |
| G2 | – för få (0) | – för få (0) | – för få (0) | – för få (0) | – för få (0) | – för få (0) |
| G3 | – för få (0) | – för få (0) | – för få (0) | – för få (0) | – för få (0) | – för få (0) |
| G4 | 1,000 accelererar (5) | 1,000 accelererar (5) | 1,000 accelererar (5) | 1,000 accelererar (5) | 1,000 accelererar (5) | 1,000 accelererar (5) |
| G5 | 0,750 accelererar (4) | 0,750 accelererar (4) | 0,875 accelererar (4) | 0,875 accelererar (4) | 0,875 accelererar (4) | 1,000 accelererar (4) |
| G6 | 0,600 stabil (5) | 0,500 stabil (5) | 0,600 stabil (5) | 0,400 stabil (5) | 0,500 stabil (5) | 0,500 stabil (5) |
| G7 | 0,583 stabil (6) | 0,583 stabil (6) | 0,667 stabil (6) | 0,583 stabil (6) | 0,750 accelererar (6) | 0,583 stabil (6) |
| G8 | 0,944 accelererar (9) | 1,000 accelererar (9) | 1,000 accelererar (9) | 0,944 accelererar (9) | 0,944 accelererar (9) | 0,944 accelererar (9) |
| G9 | 1,000 accelererar (3) | 0,500 stabil (3) | 0,833 accelererar (3) | 0,167 bromsar in (3) | 0,833 accelererar (3) | 0,500 stabil (3) |

Antal månader per tillstånd, 2019-01 till 2026-10, för de månader där grenen har minst 3 serier:

| Gren | Från | Accelererar | Stabil | Bromsar in | Månader |
|---|---|---|---|---|---|
| G4 | 2022-03 | 18 | 21 | 17 | 56 |
| G5 | 2019-08 | 34 | 38 | 15 | 87 |
| G6 | 2019-01 | 27 | 46 | 21 | 94 |
| G7 | 2019-01 | 25 | 46 | 23 | 94 |
| G8 | 2024-04 | 29 | 2 | 0 | 31 |
| G9 | 2019-01 | 16 | 63 | 15 | 94 |

G1 har som mest en räknad serie (`g1_epoch_train_compute_frontier`, flaggad som bakåtfylld) och visar därför index men
inget tillstånd. De valda benchmarkserierna har ingen takt under perioden (se punkt 16), och ECI är spärrad. G9 räknar de
tre arXiv-serierna. Epochs modelldatabas är spärrad. G2 har ingen räknad serie under någon månad. G3 har som mest en
räknad serie (BTOS v1, 2025-05 till 2025-11).

**Förbehåll:**
- Rekonstruktionen använder dagens tabell. Rader som är daterade med publiceringsfördröjning (`source="backfill"`)
  bär dagens version, så revideringar läcker in i historiken. Det gäller `us_constr_datacenter`, importserierna,
  BEA-investeringarna och Eurostat, samt EIA före de arkiverade versionerna. Bara SEC-, TSMC-, G.17-, Indeed- och
  BTOS-raderna har riktiga versionsdatum.
- G8 börjar 2024-04 eftersom Indeeds första sparade version är från 2024-04-29. Varje Indeed-version räknar om
  hela historiken, så takthistoriken i en given månad bygger på den versionens metod.
- G2 och G3 saknar tillstånd hela perioden (för kort historik, regimbyten och årsdata). G1 saknar tillstånd (en räknad
  serie). G9 vilar på tre arXiv-serier som är bakåtfyllda med nominellt `known_from` (månadsslut + 7 dagar), så
  revideringar läcker in i historiken.
- Tillstånden byter ofta för G4–G7. Om tillståndsregeln har något prognos- eller beskrivningsvärde är inte prövat.
  Det är en egen fråga och kräver förregistrering.
- G4 och G5 har 5 respektive 4 serier, så en enda serie flyttar indexet 0,1–0,125 eller mer.

## Index v2 (källfamiljer)

Spår K1, 2026-11-24. Ägarens beslut (beslutspunkt 2 i `docs/riktning.md`): diffusionsindexet ger en röst per
källfamilj och kräver minst tre räknade familjer för ett tillstånd ("för få källor" annars). Det är officiell regel från
den första skarpa ögonblicksbilden 2026-11-30. v1, en röst per serie, räknas och redovisas bredvid. Definition,
familjetabell och regel står i `docs/mattregister.md` ("2026-11-24 – Diffusionsindex v2"), och koden i
`state.register.FAMILIES` och `state.branch`.

**Ordning (förregistrering):** registerposten committades först (`7ba72eb`), koden därefter (`d80d7e3`). Inget
v2-värde har räknats på verklig data före registerposten. En senare daterad post byter bara namnet på G2:s familj,
eftersom det gamla namnet var en annan katalogseries nyckel. Under arbetet fanns ingen verklig observationstabell i
basen, och spåret har inte tittat på några verkliga värden. Familjeindelningen bygger bara på katalogens metadata
(källa, etikett och licens per kärnserie).

**Väntad effekt, bara efter konstruktion:** G2 och G8 har en familj och får "för få källor". G9 har tre familjer,
men två är Epochs spärrade databasserier, så G9 får också "för få källor" tills spärren släpper. G7 har exakt tre
familjer och får ett tillstånd bara om alla tre har en räknad serie.

**Rekonstruktion v1 mot v2:** körs av orkestreraren när datasnapshoten är installerad. Kommandot är

    PYTHONPATH=src python -m ai_tracker.state backcast --start 2024-01 --end 2026-10 --compare 6

Det skriver `outputs/state_backcast.csv` med `index` och `state` (v2), `index_v1` och `state_v1`, `n_series`,
`n_families` och familjernas röster. `--compare 6` skriver ut tabellen för de sista sex månaderna (2026-05 till
2026-10) i Markdown: index, tillstånd, antal serier och antal familjer per gren med båda reglerna. Tabellen är en
rekonstruktion och inget skarpt register, och den redovisas utan annan tolkning än vad som ändrades.
