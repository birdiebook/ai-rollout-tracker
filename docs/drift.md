# Drift: GitHub Actions

Datahämtning och skarpa nowcasts körs i GitHub Actions. Tidsstämpeln på en prognos beror då inte på att någon
har en interaktiv session öppen. Koden finns i `src/ai_tracker/pipeline.py`, testerna i `tests/test_pipeline.py`.

## Vad körs när

| Workflow | Schema (UTC) | Gör | Committar |
|---|---|---|---|
| `tests.yml` | varje push och PR | pytest | nej |
| `fetch-weekly.yml` | måndagar 03:37 | `pipeline weekly`: hämtar alla katalogserier till Actions-cachen och kör datatesterna i `warehouse.py`. Ett fallerat test fäller jobbet innan cachen sparas. En källa som fallerar ger en varning, men jobbet fortsätter. En serie som är för gammal (aktualitetskontrollen, se nedan) fäller jobbet efter att cachen sparats | nej |
| `nowcast.yml` | dagligen 18:47, med ett nytt försök 21:19 | `pipeline due` avgör om dagen är en registrerad prognosdag. Annars slutar jobbet där. På en prognosdag: återställ cachen, hämta de serier som behövs, skriv prognosen, uppdatera `forecasts/SCORECARD.md` och committa till main | bara den nya `forecasts/<nowcast>/<period>.json` och `SCORECARD.md` |

**Prognosdagar** (registrerade i `docs/mattregister.md`):

- **N2** (TSMC:s månadsintäkt): dag 5 varje månad, för föregående månad. Första: 2026-12-05 (2026-11).
- **N1** (capex för de fyra hyperskalarna): kvartalsslut + 20 dagar, alltså 20 jan, apr, jul och okt, för
  kvartalet som just slutat. Första: 2027-01-20 (2026Q4).

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
  och `python -m ai_tracker.nowcast_n2 --origin` finns kvar för manuella körningar.
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
- **Exitkod:** 1 om ett datatest fallerar (cachen sparas inte), 2 om bara serier är för gamla. Med 2 sparar
  workflowet cachen, eftersom tabellen i sig är korrekt, och fäller sedan jobbet i steget *Fail on stale series*.
  Med `pipeline weekly <serier>` kontrolleras bara de serierna.

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
`ai-data-`). Den committas aldrig och laddas inte upp som artefakt, eftersom artefakter i ett publikt repo går att
ladda ned och flera källor har licenser som inte är kontrollerade. Alla datajobb delar concurrency-gruppen
`ai-data`, så två jobb skriver aldrig cachen samtidigt. Det gäller även `collect-weekly.yml` (Epoch, spår I5).
GitHub tar bort en cache som inte använts på sju dagar. Veckohämtningen håller den varm. En kall cache betyder
bara att allt hämtas om (backfill), vilket tar längre tid.

## Hemligheter som ägaren lägger in

Settings → Secrets and variables → Actions → New repository secret:

| Namn | Värde | Krävs |
|---|---|---|
| `SEC_USER_AGENT` | `ai-rollout-tracker <kontaktadress>` | **ja**. sec.gov kräver en deklarerad User-Agent med kontaktuppgift. Det finns ingen reserv: saknas den fallerar `fetch-weekly.yml` och `nowcast.yml` direkt med ett tydligt meddelande |
| `CENSUS_API_KEY` | nyckel från api.census.gov | när den finns (används inte av koden än) |
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
python -m ai_tracker.pipeline scorecard                 # forecasts/SCORECARD.md
python -m ai_tracker.pipeline --table <fil> weekly ...  # mot en annan tabell, t.ex. en kopia
```
