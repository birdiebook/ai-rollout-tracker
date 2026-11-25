# Drift: GitHub Actions

Datahämtning och skarpa nowcasts körs i GitHub Actions. Tidsstämpeln på en prognos beror då inte på att någon
har en interaktiv session öppen. Koden finns i `src/ai_tracker/pipeline.py`, testerna i `tests/test_pipeline.py`.

## Vad körs när

| Workflow | Schema (UTC) | Gör | Committar |
|---|---|---|---|
| `tests.yml` | varje push och PR | pytest | nej |
| `fetch-weekly.yml` | måndagar 03:37 | `pipeline weekly`: hämtar alla katalogserier till Actions-cachen och kör datatesterna i `warehouse.py`. Ett fallerat test fäller jobbet innan cachen sparas. En källa som fallerar ger en varning, men jobbet fortsätter. En serie som är för gammal (aktualitetskontrollen, se nedan) fäller jobbet efter att cachen sparats | nej |
| `nowcast.yml` | dagligen 18:47, med ett nytt försök 21:19 | `pipeline due` avgör om dagen är en registrerad prognosdag. Annars slutar jobbet där. På en prognosdag: återställ cachen, hämta de serier som behövs, skriv prognosen, uppdatera `forecasts/SCORECARD.md` och committa till main | bara den nya `forecasts/<nowcast>/<period>.json` och `SCORECARD.md` |
| `pages.yml` | efter varje lyckad körning av `fetch-weekly.yml`, `snapshot.yml` och `nowcast.yml` (workflow_run), och för hand | `python -m ai_tracker.site build`: kör datatesterna i `warehouse.py` och bygger den publika sidan ur Actions-cachen och de committade `snapshots/` och `forecasts/`. Ett fallerat datatest fäller jobbet, och då publiceras ingenting (den förra sidan ligger kvar). Publicerar med `actions/deploy-pages` | nej |

**Prognosdagar** (registrerade i `docs/mattregister.md`):

- **N2** (TSMC:s månadsintäkt): dag 5 varje månad, för föregående månad. Första: 2026-12-05 (2026-11).
- **N1** (capex för de fyra hyperskalarna): kvartalsslut + 20 dagar, alltså 20 jan, apr, jul och okt, för
  kvartalet som just slutat. Första: 2027-01-20 (2026Q4).
- **N3** (Nvidias datacenterintäkter): räkenskapskvartalets slut + 14 dagar (Nvidias 52/53-veckorskalender), etikett =
  kalenderkvartalet för mittpunkten. Första: 2027-02-14 (2026Q4, nov–jan).
- **N4** (molnintäkter) och **N6** (RPO-summa): kvartalsslut + 20 dagar, samma dag som N1. Första: 2027-01-20 (2026Q4).
- **D2** (prognoser 1–8 kvartal för capex och molnintäkter, skugga): samma dag som N1 och N4, men först från
  2027-01-20. Fil: `forecasts/d2/<kvartalet som just slutat>.json`, första `forecasts/d2/2026Q4.json`. Prognosdagen
  2026-10-20 ligger i D2:s holdout och görs aldrig.
- **N5** (BTOS): dagen före den schemalagda publiceringen enligt det schema som `census_btos` loggar vid varje hämtning
  (`data/raw/census_btos/schedule_log.parquet`). Utan loggat schema, inom ett finansieringsuppehåll eller i en
  ogranskad frågeregim görs ingen prognos. B1 kräver 7 tidigare publiceringar i regimen, så ingen fil skrivs i v3
  (högst 6 cykler); rutinen loggar då en varning. Fil: `forecasts/n5/<insamlingsperiodens slutdatum>.json`.

En prognosdag som infaller på en helg behålls och flyttas inte. De två schematiderna ligger samma UTC-dag.
18:47 kommer efter de amerikanska morgonpubliceringarna och långt före datumbytet, även om GitHub försenar
starten. Försöket 21:19 tar en dag där det första fallerade (till exempel att SEC inte svarade). Om filen redan
är committad hoppar det över.

## Regler som koden håller

- **Bara data som var känd på prognosdagen.** Prognosdagen är dagens UTC-datum. Rutinen hämtar först och läser
  sedan med `as_of(origin)`. Allt som hämtas samma dag har `known_from` ≤ i dag. N1:s skrivare och N2:s skrivare
  vägrar en prognosdag i framtiden, och N2 trunkerar dessutom tabellen till `known_from <= origin`.
  `run_live` vägrar en prognosdag som inte är i dag.
- **En missad prognosdag tas inte igen** av schemat. Om båda försöken fallerar kan prognosen köras för hand
  samma UTC-dag (se nedan). Annars noteras dagen som missad. CLI:erna `python -m ai_tracker.nowcast n1 --origin`
  och `python -m ai_tracker.nowcast n2 --origin` finns kvar för manuella körningar (`python -m ai_tracker.nowcast_n2`
  är en shim till det senare).
- **Skrivs aldrig om.** En befintlig prognosfil hoppas över (skrivarna öppnar med läget `x`). `pipeline publish`
  vägrar en sökväg som redan finns i HEAD och vägrar om något annat än den nya filen och scorecarden är
  stagat. Om filen dykt upp på main under tiden ger `git pull --rebase` en konflikt och jobbet fallerar i stället
  för att skriva över.
- **Hämtningen måste lyckas.** Om en serie som prognosen behöver inte gick att hämta skrivs ingen prognos, och
  jobbet fallerar. En prognos görs bara en gång, så ett nytt försök samma dag är bättre än en prognos som
  bygger på gammal data.
- **Scorecard:** varje skarp prognos jämförs med målseriens första vintage (tidigaste `known_from`), per mål,
  med huvudmodellen från filen och övriga varianter som skuggor. Ett utfall som var känt vid prognosdagen räknas
  aldrig. Prognosfilerna läses och ändras aldrig. Scorecarden uppdateras på varje prognosdag, så ett nytt utfall
  syns i den vid nästa prognosdag (N2 varje månad).
- **Faktormodellen (C3) som skugga:** från holdoutens öppning 2026-11-24 (`docs/holdout_logg.md`) innehåller de
  skarpa filerna för N1–N4 `variants.DF` och blocket `df` (huvudmodellen DF bygger på, r̂, koefficienter, antal
  träningsrader, faktorförändringar eller orsaken till att DF saknas). Ett fel i DF stoppar aldrig prognosen.
  Den första körningen utan cache skattar faktorerna på alla tidigare prognosdagar (cirka 2 sekunder per dag,
  några minuter för N2), sedan ligger de i `data/cache/factor/` i Actions-cachen.
- **Horisontprognoser (D2) som skugga:** från 2027-01-20 skriver rutinen `forecasts/d2/<kvartal>.json` med banor för
  h = 1–8 för båda målen (`capex_hyp4` och `rev_cloud3`), alla modeller (B0, B1, B2 för capex, V_kedja), huvudmodellen
  per horisontgrupp (capex B2 för h1–4 och B1 för h5–8, molnet B1) och en lagrad felfördelning per modell och h där
  poolen har minst 8 fel. D2:s holdout är stängd och utvärderas aldrig. `factor/guard.py` släpper bara igenom en
  skarp körning (`live=True`) med prognosdag från `LIVE_FROM["D2"]` = 2027-01-20, och felpoolerna består bara av
  utvecklingens prognosdagar (≤ 2025-06-30) och tidigare skarpa D2-filer. Scorecarden har en egen D2-sektion, där
  varje h poängsätts när dess utfall (första versionen) kommer. Hemsidans prognossida visar en liten solfjäder per mål.
  Körningen tar cirka 10 sekunder.
- **Regim (C4) i ögonblicksbilden:** från 2026-11-30 har ögonblicksbilden sektionen `regime` (`ms` per block, `bocpd` per serie) med P(inbromsning)
  och rapporterat tillstånd per faktorblock och brottsflaggor per räknad kärnserie. Den är inte en del av grenarnas
  tillstånd. Reglerna för skifte och brott kedjas på förra månadens sektion. Den första (2026-11-30) startar från den
  rekonstruerade följden 2012-01–2026-10 (cirka 6 minuter utan cache). Ett fel i C4 skrivs i sektionen och stoppar
  inte ögonblicksbilden.
- **Diffusionsindex v2 i ögonblicksbilden:** från 2026-11-30 är grenens `index` och `state` regel v2, en röst per
  källfamilj och minst tre familjer (`docs/mattregister.md`, 2026-11-24). `rule_version`, `n_families` och
  `families` står i grenen, och v1 (en röst per serie) under `v1`. `rules` har `index_rule` och familjetabellen.

## Månadsbrev

`snapshot.yml` skriver månadens brev (`docs/manadsbrev/<YYYY-MM>.md`, `python -m ai_tracker.letter --month
<YYYY-MM>`) direkt efter ögonblicksbilden och committar båda i samma commit. Brevet genereras deterministiskt,
utan språkmodell:

- Grenarnas tillstånd, index och mått per serie läses bara ur ögonblicksbilden. Jämförelsemånaden är förra
  månadens ögonblicksbild, eller en rekonstruktion märkt "(rekonstruerad)" när den saknas.
- Nowcasts kommer ur de committade prognosfilerna. Utfall, revideringar, guidance och inaktuella serier kommer
  ur tabellen kapad till ögonblicksbildens informationsmängd (`known_from` ≤ datumet och `fetched_at` ≤
  `table_max_fetched_at`).
- Serier med `publish=False` namnges bara i avsnittet "Visas inte av licensskäl" och visas aldrig med värden.
- Utan ögonblicksbild vägrar kommandot. `--reconstructed` skriver ett brev ur as-of-backcasten med
  "(rekonstruerad)" i rubriken och en varningsruta överst.

Brevet är inte ett register som ögonblicksbilden. Det kan genereras om, och `pipeline publish` committar det när
det är nytt eller ändrat. Om brevsteget fallerar committas ögonblicksbilden ändå (steget har
`continue-on-error`), och brevet körs för hand. Hemsidan visar breven under Månadsbrev.

## Kvartalsrapport

Efter ögonblicksbilden för kvartalets sista månad (mars, juni, september, december) skriver `snapshot.yml` också
kvartalsrapporten "Läget i AI-utrullningen" (`docs/kvartalsrapport/<YYYYQn>.md`, `python -m ai_tracker.quarterly
--if-quarter-end <YYYY-MM>`) och committar den i samma commit som ögonblicksbilden och brevet. Den genereras
deterministiskt, utan språkmodell, på samma villkor som brevet:

- Underlaget är kvartalets tre ögonblicksbilder (jämförelse: månaden före kvartalet), de committade prognosfilerna
  med scorecarden, ögonblicksbildernas regimavsnitt (C4, läses som de är lagrade) och daterade poster i
  `docs/mattregister.md`, `docs/beslutslogg.md` och `docs/granskning/`.
- Saknas någon av de tre ögonblicksbilderna vägrar kommandot. Den första skarpa rapporten blir därför 2027Q1, eftersom
  den första ögonblicksbilden är 2026-11-30. `--quarter <YYYYQn> --reconstructed` skriver en rapport där saknade
  månader är rekonstruerade, märkt "(rekonstruerad)" i rubriken, i en varningsruta och per månad.
- Rapporten kan genereras om och committas när den är ny eller ändrad. Hemsidan visar rapporterna under
  Kvartalsrapporter.

## Aktualitet: en källa som slutar uppdateras

Datatesterna fångar fel i tabellen, men inte en källa som tyst slutar publicera eller byter adress. Därför har
varje öppen serie en högsta ålder, som `warehouse.fresh(today=...)` kontrollerar och `pipeline weekly` kör efter
datatesterna.

- **Ålder** = i dag − slutdatum för den nyaste perioden som är känd i dag (`known_from <= i dag`). Åldern räknas från
  periodens slut och inte från senaste `known_from`, så en revidering av gamla perioder gör inte serien färsk. Det
  gör bara en ny period.
- **Gräns** = `lag_days` + en period + 30 dagar för D, W, 2W, M och Q (en period = 1, 7, 14, 31 och 92 dagar), och
  `lag_days` + 400 dagar för A, eftersom årsundersökningar flyttas med veckor mellan åren. Exempel: SEC-kvartal
  25 + 92 + 30 = 147 dagar, EIA 58 + 31 + 30 = 119, BTOS 4 + 14 + 30 = 48, Eurostat 31 + 400 = 431.
- **Undantag i katalogen:** `Spec.closed=True` för avslutade serier (TSMC:s moderbolag, BTOS v1 och v2, SCB
  TAB6405), med skälet i `note`. `Spec.max_age_days` ersätter den härledda gränsen när utgivningen är förskjuten
  mot perioden, också med skälet i `note`: Indeed (månadsbatcher, 83 dagar) och Nvidia (räkenskapskvartalet slutar
  fyra veckor efter kalenderkvartalet, 199 dagar). Gränserna är prövade bakåt mot tabellens riktiga vintages
  (veckovis 2015–2026). De enda träffarna utöver dessa var shutdown-förseningarna hösten 2025 (Census, BEA, G.17),
  och dem ska kontrollen fånga.
- **Serier som kräver en nyckel som saknas** (`ai_tracker.keyed`, i dag Census HS-serierna och `CENSUS_API_KEY`):
  hämtningen hoppas över (`SKIPPED`, ingenting skrivs) och serierna undantas från kontrollen tills nyckeln finns.
  Med nyckeln gäller samma gränser som för andra serier. Har en överhoppad serie redan rader, skrivs en varning.
  Första gången nyckeln finns: kör `python -m ai_tracker.sources.census_hs check` (skriver inget i tabellen) och gå
  igenom listan i [kallor/census_hs.md](kallor/census_hs.md).
- **Exitkod:** 1 om ett datatest fallerar (cachen sparas inte), 2 om bara serier är för gamla. Med 2 sparar
  workflowet cachen, eftersom tabellen i sig är korrekt, och fäller sedan jobbet i steget *Fail on stale series*.
  Med `pipeline weekly <serier>` kontrolleras bara de serierna.
- **Månadsbilden och exitkod 2 (2026-11-25, granskning L3-4).** `snapshot.yml` skriver och committar
  ögonblicksbilden också när bara serier är för gamla. Måtten markerar en för gammal serie som inte räknad, så posten
  stämmer. Jobbet varnar i uppdateringssteget och fälls sist i *Fail on stale series*, efter committen. Tidigare
  hoppade båda försöken (22:41 och 23:29) över skrivningen, och månaden blev en lucka som aldrig rekonstrueras.

**När jobbet fallerar på aktualitet.** Loggen och jobbsammanfattningen listar varje serie med nyaste period, ålder
och gräns, och om hämtningen fallerade i samma körning.

1. *Hämtningen fallerade* (varning `fetch failed` och `fetch FAILED this run`): felsök hämtaren, till exempel ny
   URL, nytt filformat, 403 eller API-nyckel. Det här är fallet där en varning annars hade kunnat stå i veckor.
2. *Hämtningen lyckades men gav ingen ny period* (`fetch ok but no new period`): kontrollera källans egen sida.
   - Publiceringen är försenad av en känd orsak, till exempel en shutdown: lägg in serien i
     `warehouse.KNOWN_STALE` med ett slutdatum och skälet (`{"nyckel": ("2026-12-31", "shutdown, Census")}`). Ta
     bort raden när data är ikapp.
   - Serien är avslutad, till exempel en ny frågelydelse eller en ny tabell: sätt `closed=True` och skriv skälet i
     `note`. Lägg till den nya serien i katalogen.
   - Utgivningen har permanent flyttats: ändra `lag_days` eller sätt `max_age_days` med ett belagt skäl i `note`.
3. Höj aldrig en gräns bara för att få jobbet grönt. En serie som har slutat uppdateras ska synas.

Lokalt: `python -m ai_tracker.warehouse [datum]` visar för gamla serier ett visst datum och kör datatesterna.

## Data och cache

Observationstabellen ligger i Actions-cachen (`data/`, nyckel `ai-data-<run_id>`, återställs med prefixet
`ai-data-`). Där ligger också hämtloggen `data/fetch_log.parquet` (en rad per lyckad hämtning och serie, även när
inget nytt kom). Den hindrar att en försenad release som saknas i `LATE` bakåtdateras (spår X1), så en kall cache
tappar också det skyddet för perioder som var sena vid förra hämtningen. Den committas aldrig och laddas bara upp krypterad (se Datasnapshot nedan), eftersom artefakter i ett publikt
repo går att ladda ned och flera källor har licenser som inte är kontrollerade. Alla datajobb delar concurrency-gruppen
`ai-data`, så två jobb skriver aldrig cachen samtidigt. Det gäller även `collect-weekly.yml` (Epoch, spår I5).
GitHub tar bort en cache som inte använts på sju dagar. Veckohämtningen håller den varm. En kall cache betyder
bara att allt hämtas om (backfill), vilket tar längre tid.

## Datasnapshot (krypterad artefakt till nya sessioner)

En ny molnsession börjar med tom `data/`. Att bygga om tar 1–2 timmar, och BigQuery- och Cloudflare-serierna går
bara att hämta i Actions. Därför packar `fetch-weekly.yml` tabellen till en krypterad artefakt efter att cachen
sparats (`src/ai_tracker/datasnapshot.py`, tester i `tests/test_datasnapshot.py`).

- **Innehåll:** `observations.parquet`, `fetch_log.parquet` och små tillståndsfiler som inte går att hämta igen
  (`STATE_FILES`: egna prissnapshots för förstapartspriser, BTOS-schemaloggen, Epochs körlogg och LiteLLM-cachen,
  var och en högst 50 MB). Råkopiorna under `data/raw` packas inte, eftersom de är stora och går att hämta igen.
- **Kryptering:** AES-256-GCM med en nyckel som härleds ur `DATA_KEY` med scrypt (n = 2^15, r = 8, p = 1) och ett
  slumpat salt per fil. Det enda som står i klartext är ett litet huvud med formatversion, salt och skapelsetid.
  Huvudet autentiseras också (associerad data). Inuti ligger ett manifest med git-sha, antal rader och serier,
  senaste `fetched_at` och `known_from` samt SHA-256 per fil. `fetch` kontrollerar allt innan något skrivs.
- **Artefakt:** `data-snapshot` (en fil, `data-snapshot.aisnap`), sparas i 14 dagar. Utan secreten `DATA_KEY` hoppas
  stegen över med en notis, och jobbet går igenom ändå. Nyckeln skickas bara som miljövariabel till pack-steget och
  skrivs aldrig ut. Steget ligger före *Fail on stale series*, så en tabell som klarat datatesterna packas även när
  jobbet sedan fallerar på aktualitet. `collect-weekly.yml` (04:17) kommer efter veckohämtningen (03:37), så Epoch-
  och prisdata i snapshoten är från förra veckans insamling.
- **Installation:** till utcheckningens `data/`. Kommandot vägrar om den lokala tabellen är lika ny eller nyare
  (senaste `fetched_at`), utom med `--force`. Filer som ersätts sparas i `data/snapshot_backups/` (de 5 senaste).
  Skrivningen sker under samma lås som `datamerge` och är atomär per fil. I en spår-worktree
  (`AI_TRACKER_SHARED_DATA` satt) vägrar standardmålet: installera i main-utcheckningen, som är basen.

**Ny session** (i main-utcheckningen, `DATA_KEY` satt som miljövariabel med samma värde som secreten):

```
python -m pip install -q -r ci/requirements.txt          # setup-skriptet gör detta
PYTHONPATH=src python -m ai_tracker.datasnapshot fetch     # senaste data-snapshot från main
PYTHONPATH=src python -m ai_tracker.warehouse              # datatester och aktualitet på den installerade tabellen
PYTHONPATH=src python -m ai_tracker.observations           # hämtar bara det som är nytt sedan snapshoten
```

`fetch` hittar den nyaste artefakten via `api.github.com` (listning och nedladdning fungerar från sessionen utan
token) och följer omdirigeringen till `productionresultssa<N>.blob.core.windows.net`. Shardnumret varierar mellan
artefakter. Om proxyn nekar värden säger felmeddelandet vilken den är, och då läggs den till bland miljöns tillåtna
värdar (`docs/miljo.md`, avsnitt 1). Andra varianter:

```
python -m ai_tracker.datasnapshot fetch --run-id <run_id>   # en viss körning
python -m ai_tracker.datasnapshot fetch --url <url>         # URL från GitHub MCP (se nedan)
python -m ai_tracker.datasnapshot fetch --file <fil>        # .aisnap eller artefaktens .zip, redan nedladdad
python -m ai_tracker.datasnapshot info <fil>                # huvud och verifierat manifest
python -m ai_tracker.datasnapshot pack --out <fil>          # packa lokalt (samma som i Actions)
```

Om `api.github.com` skulle nekas: agenten hämtar körningen med `mcp__github__actions_list` (`list_workflow_runs`,
workflow `fetch-weekly.yml`) och nedladdnings-URL:en med `mcp__github__actions_get`
(`download_workflow_run_artifact`, artefakten `data-snapshot`), och kör sedan `datasnapshot fetch --url <url>`.
URL:en är signerad och kortlivad, så den skrivs inte ut av kommandot och ska inte loggas.

**Byta nyckel:** sätt ny `DATA_KEY` både som secret och i miljön. Äldre artefakter går då inte att läsa (de
försvinner ändå efter 14 dagar), så kör `Weekly data fetch` för hand en gång efter bytet.

## Delad data (parallella spår)

Från steg 2 (spår I1) delar alla spår en läskopia av tabellen, och varje spår skriver bara i sin egen `data/`.
Orkestreraren slår ihop spårens data med ett verktyg som kör datatesterna. Ingen handpåläggning, och ingen kopia
av `data/` per spår.

- **Basen** är `/home/user/ai-rollout-tracker/data` (main-utcheckningen): `observations.parquet` och
  `fetch_log.parquet`. Spåren läser den men skriver aldrig i den. Bara `datamerge` skriver där.
- **Nytt spår:** `scripts/new_track.sh <namn> <grenprefix>` (till exempel `scripts/new_track.sh a1-rpo auto5`)
  skapar worktree `/home/user/wt/<namn>` på grenen `<grenprefix>/<namn>` från main, kopierar `.env` och skriver
  `.env.local` med `AI_TRACKER_SHARED_DATA=<main>/data` och `AI_TRACKER_SHARED_RAW=<main>/data/raw`.
  `config.get` läser miljön, sedan `.env.local` och sist `.env`, så alla `python -m ai_tracker.*` i spåret
  använder basen utan fler steg. Båda filerna är gitignorerade.
- **I spåret** ger `observations.load()` och `load_log()` bas ∪ spår. Vid samma (series, period, known_from)
  vinner spårets rad, och i hämtloggen gäller samma sak för (series, fetched_at). `upsert` räknar nya rader mot
  hela vyn, så en vanlig hämtning sparar bara det som är nytt. `drop_series` och `--rebuild` kan inte ta bort
  rader i basen. De skriver i stället serien i `data/rebuilt_series.json`, och då döljer vyn basens rader för
  serien. Basen läggs bara under standardtabellen. En explicit sökväg eller `--table` läser bara den filen.
- **Merge** (orkestreraren, efter att spårets kod är mergad till main, eftersom katalogen måste känna till
  serierna):

  ```
  python -m ai_tracker.datamerge /home/user/wt/<namn>/data [--series ...] [--replace ...] [--dry-run]
  ```

  Basen är som standard `AI_TRACKER_SHARED_DATA`, annars `data/` i utcheckningen (`--into` för en annan). Per
  serie: *added* (ny i basen), *replaced* (ombyggd i spåret, eller angiven med `--replace`: basens rader ersätts
  helt), *updated* (bas ∪ spår) och *unchanged*. Datatesterna i `warehouse.py` körs på hela resultatet, och
  aktualiteten körs för de serier som slås ihop. Fallerar något skrivs ingenting, och exitkoden blir 1.
  Skrivningen är atomär (temporär fil och rename) och sker under ett lås, och den förra basen sparas i
  `data/merge_backups/` (de 20 senaste). En andra körning ger "nothing to merge". Hela basen tar cirka 10 sekunder.
- **Äldre spår** med en egen full kopia av `data/` går också att slå ihop. Identiska rader blir *unchanged*. En
  serie som byggdes om på det gamla sättet anges med `--replace`, annars ligger båda versionerna kvar.
- **Delad rå-cache** (`AI_TRACKER_SHARED_RAW`, sätts av `new_track.sh`) flyttar `http.RAW_DIR`. Spåren läser och
  skriver där. Det är säkert för HTTP-kopiorna, eftersom varje fil heter källa/hämtdatum/URL-hash och skrivs
  atomärt. Två spår som hämtar samma URL samma dag skriver samma innehåll till samma namn. Det finns också
  föränderliga filer under `RAW_DIR`: git-klonen för Indeed (`indeed/ai-tracker`, två samtidiga `git fetch` kan
  ge ett låsfel, och då räcker det att köra igen) och Census `schedule_log.parquet` (den sista skrivningen
  vinner, med samma innehåll samma dag). LiteLLM-klonen ligger kvar i spårets egen `data/raw`.
- **Begränsning:** två spår som uppdaterar samma serie stegvis kan båda lägga till samma nya period med olika
  `known_from`. Merge ger då två versioner. Planen undviker det, eftersom spåren inom en våg inte rör samma
  serier. Kör `--dry-run` och läs *updated* om du är osäker.

## Hemsidan (GitHub Pages)

**Engångsåtgärd för ägaren:** Settings → Pages → Build and deployment → Source: **GitHub Actions**. Det går inte
att göra från koden. Innan det är gjort fallerar deploy-steget i `pages.yml` (bygget går igenom). Starta sedan
`Pages` för hand en gång (Actions → Pages → Run workflow), eller vänta på nästa veckohämtning.

- **Vad som visas:** startsidan (vad som ändrade takt den här månaden: de nio grenarna med tillstånd,
  diffusionsindex, antal källor och serier och förändring mot föregående månad), en sida per gren (kärnserierna med takt
  och förändring i takt, senaste period, `known_from` och skälet till att en serie inte räknas), prognossidan
  (N1 och N2: skarpa prognoser och scorecard, huvudmodell och skuggor) och metodsidan (neutral inramning,
  måttregistret, filerna i git, källor och licenser, "inte investeringsrådgivning").
- **Register:** de committade ögonblicksbilderna i `snapshots/` är registret. Före den första (2026-11-30) visas
  tillståndet beräknat i efterhand vid varje månadsslut, tydligt märkt "rekonstruerad historik, inte ett skarpt
  underlag". Månader efter den första skarpa ögonblicksbilden rekonstrueras aldrig.
- **Licenser:** bara serier med `Spec.publish=True` visas med värden (en härledd serie kräver att alla
  komponenter får publiceras). En serie med `publish=False` som är kärnserie räknas i grenens index enligt
  registret, men sidan visar bara grenens summering och anger vilka serier som hålls inne och varför. I dag
  gäller det arXiv-serierna i G9 (licensen är inte kontrollerad). Prognosfilernas indata (`inputs`) publiceras inte.
- **Inga externa värdar:** diagrammen är inline-SVG som `assets/app.js` ritar från JSON-filerna i `data/`.
  Testerna i `tests/test_site.py` kontrollerar att sidorna inte laddar något från andra värdar.
- **Lokalt:** `python -m ai_tracker.site build [--out site] [--history-from 2023-01] [--today D]` bygger `site/`
  (gitignorerad), cirka en minut. Titta med `python -m http.server -d site`.

## Hemligheter som ägaren lägger in

Settings → Secrets and variables → Actions → New repository secret:

| Namn | Värde | Krävs |
|---|---|---|
| `SEC_USER_AGENT` | `ai-rollout-tracker <kontaktadress>` | **ja**. sec.gov och bls.gov (`download.bls.gov`, `www.bls.gov`, BLS-serierna från spår M1) kräver en deklarerad User-Agent med kontaktuppgift och svarar annars 403. Det finns ingen reserv: saknas den fallerar `fetch-weekly.yml` och `nowcast.yml` direkt med ett tydligt meddelande. Namnet gäller numera båda värdarna |
| `CENSUS_API_KEY` | nyckel från api.census.gov (gratis, aktiveras via mejl) | nej, men den låser upp 35 månadsserier: USA:s import per HS-kod (8471, 8471.50, 8471.80, 8473.30, 8542) från Taiwan, Mexiko, Vietnam, Malaysia, Thailand, Kina och hela världen, från 2013 (`us_imp_hs*_m`, [kallor/census_hs.md](kallor/census_hs.md)). Saknas den hoppas de serierna över (SKIPPED) och undantas från aktualitetskontrollen, så jobbet fallerar inte |
| `DATA_KEY` | lång slumpad lösenfras, till exempel `python -c "import secrets; print(secrets.token_urlsafe(32))"` | för datasnapshoten. Samma värde läggs in som miljövariabel i molnmiljön (`docs/miljo.md`). Saknas den hoppas snapshot-stegen över. Värdet sparas också utanför GitHub (lösenordshanterare), eftersom en secret inte går att läsa ut igen |
| `ECOS_API_KEY` | nyckel från Bank of Korea ECOS | när den finns (används inte av koden än, se N2:s blockerade indikatorer) |

Värdena skickas bara som miljövariabler till stegen och skrivs aldrig ut. GitHub maskerar dem i loggarna.

## Viktigt om scheman

- **Schemalagda workflows körs bara från standardgrenen (main).** De startar först när filerna är mergade.
  `nowcast.yml` kör dessutom bara på main (`if: github.ref == 'refs/heads/main'`), så en manuell körning från
  en annan gren gör ingenting.
- GitHub kan försena schemalagda körningar, och stänger av scheman i repon utan aktivitet på 60 dagar.
- Pushen görs med jobbets egen `GITHUB_TOKEN` (`contents: write`). Om main får grenskydd som kräver PR måste
  `github-actions[bot]` få undantag, annars fallerar pushen.

## Köra för hand

Actions → välj workflow → **Run workflow** (workflow_dispatch) på main.

- `Weekly data fetch`: hämtar allt och kör datatesterna.
- `Live nowcasts`: gör samma kontroll som schemat. På en prognosdag skrivs prognosen om den saknas, annars
  händer ingenting. Det går inte att välja datum, eftersom prognosdagen alltid är i dag.

Lokalt (`PYTHONPATH=src`, `.env` med `SEC_USER_AGENT`):

```
python -m ai_tracker.pipeline weekly [serier...]       # hämta + datatester + aktualitet
python -m ai_tracker.pipeline due --today 2026-12-05    # vad som är aktuellt en viss dag (läser bara)
python -m ai_tracker.pipeline live                      # skarpa prognoser som är aktuella i dag
python -m ai_tracker.pipeline d2-live                   # bara D2 (prognosdag i dag, från 2027-01-20)
python -m ai_tracker.pipeline scorecard                 # forecasts/SCORECARD.md
python -m ai_tracker.letter --month 2026-11            # månadsbrev ur snapshots/2026-11.json
python -m ai_tracker.quarterly --quarter 2027Q1         # kvartalsrapport ur snapshots/2027-01..03.json
python -m ai_tracker.pipeline --table <fil> weekly ...  # mot en annan tabell, t.ex. en kopia
python -m ai_tracker.datamerge <spår>/data [--dry-run]  # slå ihop ett spårs data med basen (se Delad data)
```
