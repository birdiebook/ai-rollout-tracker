# R-W1 – licens och läckage för den nya hemsidan (`/next/`)

Granskningsspår R-W1, 2026-11-25, gren `auto14/rw1-licens` (från `main` vid `d0ee879`). Granskat: licensgrinden och
skanningen (`src/ai_tracker/site_bundle/{gate,export,vintages}.py`, `schema/`), versionerna och tidsresan
(`web/src/lib/series/versions.ts`, `web/src/lib/timetravel/`), layouten (`web/src/routes/+layout.svelte`),
prognossidorna (`web/src/routes/prognoser/`), metod- och regimsidorna och kopieringen av paketet till sidan
(`web/scripts/sync-bundle.mjs`).

Underlag: ett riktigt paket byggt på den delade tabellen (`python -m ai_tracker.site_bundle build`, 425 filer,
385 serier, byggt 2026-11-25, 2 min) och den riktiga sidan byggd mot det (`SITE_BUNDLE_DIR=<paket> npm run build`,
1 319 filer). Ingen skarp ögonblicksbild och ingen skarp prognosfil finns ännu (`snapshots/` och `forecasts/` är
tomma utom `SCORECARD.md`). Allt i posten är alltså rekonstruerat, och prognossidorna har bara backtest och väntande
prognoser. Det begränsar vad som gick att pröva för punkt 4 och för skarpa månader i tidsresan.

Granskningsskript (inte committade, ligger utanför repot): sökning efter inhållna nycklar, etiketter och värden i
paketet och i bygget, en kontrollkörning med störda värden, och härledning av inhållna riktningar ur paketet.
Metoderna beskrivs under varje punkt så att de går att upprepa.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Licens i paket och byggd sida | **OK.** Inga inhållna nycklar, etiketter eller värden utanför `withheld`-listorna. Två strukturella luckor (anmärkning): `sync-bundle` kopierade hela katalogen, inte bara manifestets filer (**rättat**), och konstanter i `web/src` skannas inte av grinden |
| 2. Inhållna seriers riktning | **Anmärkning (beslut behövs).** Riktningen per inhållen serie är inte bara härledbar ur index, den står nästan i klartext: `n_up`/`n_neutral`/`n_down` per månad minus de publicerade seriernas riktningar ger exakt fördelningen av de inhållna riktningarna varje månad, och den enskilda seriens riktning i 36 % av fallen. Inte ett licensproblem för de nio serier som räknas i dag, men texten "ingen egen riktning per serie" i datakontraktet stämmer inte. Regel föreslås nedan |
| 3. Läckage i tidsresan | **Fel (ett) och anmärkningar.** Grinden håller i alla kantfall jag prövade (samma dag, UTC, månadsslut, ihopfällning, golden mot riktig data). **Fel:** bakåtfyllda värden visas omärkta mellan `backfill_last_known` och dagen de faktiskt hämtades (41 av 105 serier med bakåtfyllnad, 17 med mer än 180 dagar) – rättningsspår. Rättat här: sidfoten visade dagens underlag, en seriesida visade datumet för första versionen, grensidan listade serier som bara räknas i dag, förmålningsskriptet läste `as_of` annorlunda än butiken, och `leaks()` släppte igenom senare datum i fält utanför sin namnlista |
| 4. Prognossidor | **OK med anmärkning.** Inga backtest-siffror presenteras som skarpa. Skarpa prognoser länkar till filens commit-historik och till filen vid byggets commit, inte till den commit som lade till filen. Paketet saknar den commiten – rättningsspår |

**Slutdom: GODKÄND för publicering under `/next/` med villkor.** Licensen håller i dag. Före publicering ska
rättningarna i den här grenen in, och rättningsspåret RW1-X ska åtgärda bakåtfyllnadsgränsen (3a), eftersom
tidsresan annars visar dagens version av bakåtfyllda perioder som om den var känd tidigare. Beslutet om riktningsregeln
(punkt 2) behöver inte blockera publiceringen, eftersom ingen av de nio räknade inhållna serierna har villkor som
förbjuder härledda verk. Det ska tas innan en ny inhållen serie med andra villkor börjar räknas.

## 1. Licens: paketet och den byggda sidan – OK

**Nycklar och etiketter.** 102 nycklar är inhållna (`gate.withheld_keys`, av 490 kandidater). I paketet gav
`gate.scan` 0 överträdelser. I bygget förekommer inhållna nycklar bara i `data/` (paketets kopia) och i
`gren/G3`, `gren/G9` och `flode/L9` (`index.html` och `__data.json`). Jag läste varje träff i HTML-filerna, och alla
ligger i en `withheld`-post (`{key, label, source, license, why, counted}`). I `_app/**/*.js` (54 filer, kod och
konstanter) finns 0 inhållna nycklar och 0 inhållna etiketter. Inhållna etiketter som inte också är etikett för en
publicerad serie förekommer inte utanför `withheld`-listor i paketet.

**Värden.** Jag jämförde varje tal i paketet (236 887 tal utanför `withheld`, utom manifestets byte och kontrollsummor)
med två mängder:

- *Nivåer:* varje rad (alla versioner) av de inhållna katalogserierna, med minst 4 signifikanta siffror. Med 5
  signifikanta siffror och |x| ≥ 1, och utan tal som också är värden i någon publicerad serie, blev det 2 träffar. Båda
  är slump: `g3_pypi_requests_wed` 19 808 547 (2024-07-21) mot `g3_npm_react_w` 19 808 124 (2023-05-14).
- *Mått:* takt, förändring i takt, nivå, överraskning, standardavvikelse och dödband för varje inhållen serie i dagens
  post, och hela takt- och förändringsbanan (`measure_path`). Det gav 1 041 träffar mot 340 (±20) i två
  kontrollkörningar med värdena störda med 0,037 % respektive 0,029 %. Överskottet består nästan helt av 100·ln(a/b)
  och 100·(a/b − 1) för små heltal (69,315 = 100·ln 2 och så vidare). Sådana tal uppstår i alla serier med små
  heltalsantal, till exempel arXiv-antal mot Epochs modellantal. Utan dem: 113 träffar mot 107 i kontrollen. Det är
  slump, och inget värde av en inhållen serie finns i paketet.

**Nedladdningar, sökindex, delningsbilder.** CSV byggs i webbläsaren ur seriedokumenten (`series/csv.ts`). De finns bara
för publicerade serier och har attributionsraden. Sökindexet `series/index.json` innehåller bara publicerade serier
(skannat). Det finns inga rasterbilder och inga `og:`-taggar i bygget.

**Kalibrering och holdout.** Backtestkalibreringen (`nowcast/n*.json`) gäller bara publicerade mål (N1–N6, alla
`publishable: true`). Holdoutdata på regimsidan (`web/src/lib/regime/holdout.ts`) namnger bara publicerade serier
(`rpo_hyp4`, `rev_google_cloud`). `regime.json` är tom (`available: false`) tills den första skarpa ögonblicksbilden
finns. Metodsidans grenlistor visar inhållna kärnserier som `withheld`-poster.

**Anmärkning 1a – rättad: sidan publicerade hela paketkatalogen.** `sync-bundle.mjs` kopierade katalogen rekursivt
(`cpSync`), så en lös fil i paketkatalogen (en felsökningsdump, en fil från ett annat verktyg) hade publicerats utan
att ha passerat skanningen. Nu kopieras bara filerna i manifestet plus `manifest.json`, och varje fils SHA-256
kontrolleras mot manifestet. En sökväg med `..` eller som börjar med `/` stoppar bygget, och så gör ett riktigt paket
utan fillista. Jag provade med en planterad `stray_debug.json` (kopierades inte) och en ändrad `overview.json`
(bygget stoppades).

**Anmärkning 1b – till rättningsspår: konstanter i `web/src` går förbi grinden.** `holdout.ts`, `reconciliations.json`
och `rules.json` är data som skrivits in i frontend för hand. Grinden skannar bara paketet. I dag är de rena (se ovan),
men inget stoppar en inhållen nyckel där. Förslag: ett steg i `pages-next.yml` efter `vite build`,
`python -m ai_tracker.site_bundle scan-build web/build`. Steget ska ge 0 inhållna nycklar och etiketter i
`_app/**/*.{js,json,css}`, och i `**/*.html` och `**/__data.json` får de bara stå inuti `withheld:[…]`. Testet görs med
en planterad nyckel i en konstant.

## 2. Inhållna seriers riktning – anmärkning, regel föreslås

**Vad som går att härleda.** Allt nedan kommer ur det publika paketet. För varje gren och månad i grenens
`history` finns `n_up`, `n_neutral`, `n_down` och `n_series`, och de räknar även inhållna serier
(`state.branch.branch`). Varje publicerad räknad serie har sin riktning per månad i `measure_history`. Differensen ger
exakt hur de inhållna riktningarna fördelade sig den månaden, och den stämmer i alla 138 månader med inhållna serier
(ingen inkonsistens). Den enskilda seriens riktning är exakt känd när bara en inhållen serie räknas eller när alla
inhållna har samma riktning:

| Gren | Inhållna räknade i dag | (serie × månad) | exakt | bara fördelningen |
|---|---:|---:|---:|---:|
| G3 (npm: openai, anthropic-sdk, langchain, vercel-ai) | 4 | 116 | 38 | 78 |
| G7 (PJM toppbelastning DOM och RTO) | 2 | 92 | 46 | 46 |
| G9 (arXiv cs.AI, cs.LG, cs.CL) | 3 | 138 | 39 | 99 |
| **Totalt** | 9 | 346 | **123 (36 %)** | 223 |

G9 i dag: `n_neutral = 3` av 3, så alla tre arXiv-serier är "stabil", utan någon räkning. Tidsresevyn för grenen
visar dessutom ▲/●/▼-antalen bredvid de publicerade seriernas kort, så att subtraktionen görs med ögat. Att dölja
antalen räcker inte: med bara index och `n_series` får man summan av de inhållna riktningarna, och den är exakt när en
enda inhållen serie räknas. En inhållen serie kan inte räknas i ett publicerat index utan att dess bidrag avslöjas.
Regimsidan kommer på samma sätt att visa en namnlös markör med datum för en inhållen series strukturbrott
(`n_breaks_withheld`).

**Är det ett licensproblem?** Riktningen är tre värden per månad (förändring i takt mot ett dödband), ungefär
1,6 bit per serie och månad. Ingen nivå, takt eller siffra ur källan går att få tillbaka ur den. För de nio räknade
serierna:

- PJM: villkoren tillåter uttryckligen härledda verk ("including publishing and making derivatives of the Data").
  Bara att återpublicera själva datan är förbjudet för icke-medlemmar. Riktningen är ett härlett verk.
- npm och arXiv: hålls inne för att licensen inte gick att läsa ("unverified"), inte för att något förbud är känt.
  arXivs metadata anges som CC0.

Det är alltså inte ett licensproblem i dag. Men beslutet 2026-11-24 ("bara riktningen syns") och datakontraktets
§ 4 ("Ingen egen riktning per serie") läses olika, och kontraktets mening stämmer inte i praktiken.

**Föreslagen regel (för orkestreraren och beslutsloggen):**

> En serie med `publish=False` får räknas i ett publicerat grenindex bara om källans villkor inte förbjuder
> publicering av härledda verk. Räknas den, betraktas dess riktning per månad som publicerad, eftersom den går att
> härleda ur indexet. Det gäller även tecknet för strukturbrott. Detta registreras i `Spec` som
> `derived_ok: bool` med citat ur villkoren. Om villkoren inte gick att läsa ("unverified") räcker det med ett
> dokumenterat skäl att tro att de inte förbjuder härledningar. Grinden vägrar bygga om en räknad inhållen serie saknar
> `derived_ok=True`.

Ändringen är liten: ett fält i `Spec`, nio ifyllda värden och en kontroll i `gate.py`. Med regeln kan riktningsrutan
(▲ ● ▼) för en inhållen serie lika gärna visas öppet. Det är ärligare än en kläckt ruta vars innehåll ändå går att
räkna fram. Datakontraktets § 4 ska rättas till "riktningen per serie går att härleda och räknas som publicerad".

## 3. Läckage i tidsresan – ett fel (rättningsspår), fem rättade anmärkningar

### Vad som håller

Egna tester i `web/src/lib/timetravel/rw1.test.ts` (17 st) och `web/tests/e2e/rw1.spec.ts` (12 per projekt):

- **Samma dag:** en version daterad D finns med på D och saknas på D − 1 (som `observations.as_of`). Klippet innehåller
  aldrig en period, ett datum eller ett värde som bara senare rader hade. Det är identiskt med en kodning av bara de
  rader som var kända den dagen.
- **Månadsslut:** en revision publicerad på månadsslutet finns med i klippet på månadsslutet. Månadens post syns från
  månadsslutet och inte dagen före (`branchOn` 2024-06-29 innehåller ingenting från 2024-06). `lastMonthEnd`
  hanterar skottår. En skarp ögonblicksbild med datum efter månadsslutet flyttar posten senare, aldrig tidigare.
  `snapshot.write` tillåter bara månadsslut, så den grenen används inte i dag.
- **UTC:** `known_from` är UTC-dagar. Ett `Date` klipps vid sin UTC-dag, och en datumsträng med klockslag klipps vid
  den skrivna dagen. URL:en tar bara riktiga kalenderdagar (`2024-02-30` avvisas). `dateLabel` formaterar strängar
  utan `Date`, så en tidszon flyttar aldrig etiketten.
- **Ihopfällda versioner:** före brytdagen visas ingenting, från brytdagen visas den ihopfällda versionen, och en
  brytdag efter D kopieras aldrig in i klippet.
- **Länkar:** `as_of` följer med till varje sida under `/next/` och bara dit (inte till den gamla sidan, inte till
  `/next-old/`, inte externt). Ett gammalt `as_of` i målet ersätts. Sidor utan tidsresevy visar rutan i stället för
  dagens data (befintligt e2e-test).
- **Golden mot riktig data:** `gen_timetravel_golden.py --real` på det riktiga paketet och
  `TT_BUNDLE=… TT_GOLDEN=… npx vitest run timetravel` gav 43/43 gröna, också med den skärpta `leaks()`.
- **I webbläsaren, riktig data och fixtures:** e2e-testet läser all synlig text på `/`, `/gren/G9/`, `/gren/G3/` och
  tre seriesidor per dag (en som inte var publicerad än, en bakåtfylld och en vanlig) för 2019-06-30 och 2026-03-15.
  Det räknar varje datum ("30 jun 2024", ISO) och varje månad ("juni 2024"), utom i tidsreglaget, i den märkta
  jämförelsen med i dag (`data-tt="compare"`), i den märkta bakåtfyllnadsnoten och i SVG-axlarna. Inget ligger efter
  D. Undantagen är meningarna "Tillstånden finns per månadsslut från januari 2023" och "Grenens historik börjar …",
  som anger en byggparameter och ingen kunskap. Med rättningarna nedan bortplockade misslyckas alla 12 fall.

### Fel 3a – till rättningsspår: bakåtfyllnadsgränsen är fel dag

`reconstructedOn(rows.backfill_last_known, D)` märker tidsresan som rekonstruerad bara när D ligger före det **senaste
`known_from`** bland de bakåtfyllda raderna. Men bakåtfyllda rader har dagens version, alltså versionen från
**hämtdagen** (`observations`: "Values are today's vintage"), och deras `known_from` är en regel (periodslut +
fördröjning). För ett datum D mellan `backfill_last_known` och den första hämtningen visar seriesidan bakåtfyllda
perioder, med "känd från <regeldatum>", utan märkning, fast värdena hämtades senare. Exempel:
`us_elec_sales_com_*` (7 serier) har `backfill_last_known` 2013-01-29 och hämtades 2026-11-23. Tidsresa till 2020
visar perioderna 2010-01–2012-10 i 2026 års EIA-861M-version som om de var kända 2013. `scb_ai_ent_se` har gränsen
2025-12-31 och hämtades 2026-11-23. Av 105 publicerade serier med bakåtfyllnad ligger hämtningen mer än 7 dagar efter
gränsen för 41 serier, mer än 30 dagar för 18 och mer än 180 dagar för 17. Medianen är 6 dagar.

Rättning (schema minor): lägg till `rows.backfill_fetched`, den senaste `fetched_at`-dagen (avrundad uppåt) bland de
bakåtfyllda raderna som var kända byggdagen. Märk tidsresan rekonstruerad när
`D < max(backfill_last_known, backfill_fetched)`, och visa noten med det datumet. Uppdatera `common.json`/`series.json`,
`types.ts`, fixturerna och golden-generatorn, och datakontraktets § 5.6. Testa med en serie där gränsen och hämtningen
skiljer sig. Samma resonemang gäller grenposterna, men där är allt före den första skarpa ögonblicksbilden redan märkt
rekonstruerat, så det blir inget fel förrän en serie bakåtfylls efter 2026-11-30. Det ska registreras som en regel i
samma spår: en ny serie som bakåtfylls efter den första skarpa ögonblicksbilden ändrar inga skarpa månader, och
rekonstruerade månader efter dess `backfill_fetched` märks.

### Rättat i den här grenen (små, uppenbara läckor, med test)

| | Läcka | Rättning | Test |
|---|---|---|---|
| 3b | **Sidfoten** (`+layout.svelte`, utanför tidsresan) skrev "Underlag: <dagens post>". Efter 2026-11-30 hade den stått "skarp ögonblicksbild" under en resa till 2024 | Under tidsresa: "tidsresa, posten som var känd den <D>". Före målning döljs dagens text (`.tt-hide` under `html[data-tt]`) | e2e: sidfoten innehåller "tidsresa" och aldrig dagens etikett. Före hydrering är den dold |
| 3c | **Seriesidan** för en serie som inte var publicerad på D skrev "första version <datum efter D>" | Datumet tas bort ("Inget var publicerat ännu.") | e2e: inget datum efter D |
| 3d | **Grensidan** listade under "Inte i posten <månad>" också serier som bara räknas i dag (en senare G1-urval) eller som inte hade någon version på D, alltså senare kunskap om katalogen | Bara kärnserier med en version på D | Inget eget test (filtret ligger i komponenten). Befintliga e2e för grensidan är gröna |
| 3e | **Förmålningsskriptet** använde ett annat regex än `readAsOf`: `#as%5Fof=2024-06-30` reste i tiden efter hydrering men målade dagens innehåll först. `#as_of=2024-02-30` dolde sidan i onödan | `prepaint.ts`: samma tolkning som `readAsOf` (URLSearchParams och en riktig kalenderdag). Skriptet och testorakelt är samma kod | vitest: skriptet döljer exakt när `readAsOf` ≠ null (9 hashar). e2e: kodad nyckel dold före hydrering, ogiltig dag inte dold |
| 3f | **`leaks()`** kontrollerade bara fält vars namn står i `KNOWN_KEYS`. Ett senare datum under ett annat namn (till exempel `backfill_last_known` eller en tidsstämpel) passerade | Varje värde som *är* en dag, en tidsstämpel eller en daterad period ("a/b", från sin första dag) prövas i alla fält. Text som bara innehåller ett datum, som en licenstext, prövas inte | vitest (3 fall). Golden och invarianter gröna på fixtures och på riktig data |

### Anmärkningar utan rättning

- **Utan JavaScript** körs inget skript, och den förrenderade sidan visar dagens innehåll under en URL med `as_of`,
  utan att påstå ett tidigare datum. Det är dokumenterat och godtagbart. Flikens `<title>` visar dagens titel
  ("läget oktober 2026") fram till hydreringen. Det är kosmetiskt.
- **`#as_of` före 2015-01-01** visas som 2015-01-01 (`MIN_DAY`), och etiketten säger det. Det är ingen läcka, men
  URL:en och vyn skiljer sig. Skriv tillbaka det klämda datumet till URL:en.
- **Rekonstruerade månader** använder dagens register, katalog och G1-urval på data som var känd då. Det är en
  metodisk efterhandskunskap, inte en dataläcka, och märkningen "rekonstruerad" täcker den. Värt en mening i
  tidsresans rubrik.
- **Revideringsvyn** på seriesidan visar dagens version, märkt "i dag" under rubriken "då mot i dag". Det är avsett och
  märkt.

## 4. Prognossidor – OK med anmärkning

- I det riktiga paketet finns 0 skarpa filer (`forecasts: []`) för N1–N6 och D2. Kortet på `/prognoser/` märks
  "väntar" eller "skugga". Bara `forecasts[]`, det vill säga skarpa filer, ritas som skarpa (`LiveRow`), och raden
  "bara skarpa, committade prognoser; inga backtestmånader" står vid tabellen.
- Backtestkalibreringen (alla sex har `available: true`, till exempel N2: 238 perioder, MAE 5,83) visas bara i
  `BacktestCalibration` med `KindTag kind="backtest"` ("backtest, inte en skarp prognos") och `status="backtest"`
  på varje diagram. `champion_mae` används bara där. D2:s facit märks "skugga".
- **Anmärkning 4a – till rättningsspår: länken till commiten.** `proofLinks` ger `commits/main/<fil>` (filens
  historik) och `blob/<byggets sha>/<fil>`. Ingen av dem pekar på den commit som lade till prognosen, så sidan visar
  inte tidsstämpeln, bara vägen dit. `git_sha` kan också vara `abc1234+dirty`, och då faller länken tillbaka till
  `main`. Rättning: exporten lägger till `commit: {sha, date}` per skarp fil
  (`git log --diff-filter=A --format=%H%x09%cI -- <fil>`, första raden). `pages-next.yml` och `pages.yml` behöver
  `fetch-depth: 0` i `actions/checkout`, eftersom `git log` annars bara ser den senaste commiten. Sidan visar
  "committad <datum> (<sha7>)" med länk till `commit/<sha>`, och ett test kontrollerar att commitdatumet ligger före
  utfallets `known_from` för varje poängsatt rad. En fil utan commit (byggd utan git-historik) visas som "väntar på
  verifiering", aldrig som skarp.

## Rättningsspår RW1-X (förslag, ett spår)

1. 3a: `rows.backfill_fetched` och den nya gränsen (Python, schema minor, typer, fixturer, golden, datakontrakt § 5.6).
2. 4a: `commit` per skarp prognosfil, `fetch-depth: 0` i båda Pages-workflows, visning och testet commit < utfall.
3. 1b: `site_bundle scan-build` på `web/build` i `pages-next.yml`, med test för en planterad konstant.
4. Punkt 2: beslut om regeln. Därefter `Spec.derived_ok`, kontrollen i `gate.py` och rättning av datakontraktets § 4.
   Orkestreraren skriver beslutsloggen.

## Körda grindar (på den här grenen)

- `npm run check` (0 fel, 0 varningar), `npm test` (343 gröna), `npm run build`, `npm run budget` (53 sidor ok),
  `npm run external-hosts` (ok), `PW_PORT=4511 npx playwright test` på fixtures (366 gröna, desktop och mobil, med
  axe och skärmbilder). Hela Playwright-sviten på desktop mot det riktiga paketet: 186 gröna. De 3 som föll först var mina nya tester, innan undantaget för historikens startmånad lades in. Därefter gav `rw1.spec.ts` 24/24 gröna mot det riktiga paketet.
- Golden mot riktig data: `TT_BUNDLE=… TT_GOLDEN=… npx vitest run timetravel` (43 gröna).
- `python -m pytest -q`: 1 570 gröna, 3 överhoppade (8 min).
