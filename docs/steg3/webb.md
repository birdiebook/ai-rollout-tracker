# Den nya hemsidan: struktur, kommandon och CI

Skriven 2026-11-24 (spår W4 och W2, våg 0). Bakgrund och byggplan: `docs/steg3/hemsida_vision.md`. Beslutet om stack
och `/next/` finns i `docs/beslutslogg.md` (2026-11-24). Den nuvarande sidan (`src/ai_tracker/site/`, `pages.yml`)
fungerar som förut. Den nya sidan läggs till under `/next/` i samma Pages-publicering.

## Struktur

```
web/
  package.json, package-lock.json   exakta versioner (inga ^/~), låsfilen committas
  svelte.config.js                  adapter-static, allt förrenderas, BASE_PATH (standard /next)
  vite.config.ts                    vite + vitest (jsdom)
  playwright.config.ts              smoke, axe och skärmbilder mot det byggda resultatet
  scripts/
    sync-bundle.mjs                 väljer site_bundle och kopierar den till static/data/
    budget.mjs                      prestandabudget per sida (gzip)
    check-external-hosts.mjs        statisk kontroll: inget laddas från andra värdar
  fixtures/provisional/             PROVISORISK syntetisk bundle (W4), tills W3:s web-data-fixtures/ finns
  fixtures/gen_provisional.py       genererar den (deterministiskt)
  src/
    app.html                        lang="sv", temat sätts före första målningen
    lib/design/                     designsystemet (W2), se nedan
    lib/data/                       typer och laddare för site_bundle (fungerar på server och i webbläsare)
    lib/server/bundle.ts            läser bundlen från disk vid förrenderingen
    lib/components/                 delade sidkomponenter (temaväxlare)
    routes/                         en katalog per huvudvy, se "Sidorna och vem som äger dem"
  tests/e2e/                        Playwright: smoke.spec.ts, a11y.spec.ts, screenshots.spec.ts
```

### Designsystemet (`web/src/lib/design/`, W2)

- `tokens.ts` är den enda källan. Där finns färger för ljust och mörkt läge (avsnitt 4.4), bandopacitet för 50/80/95,
  typografi (bara `system-ui`), avstånd (bas 4 px), radier, rörelse (200–400 ms) och storlekar för markeringar.
  `tokensCss()` genererar CSS-variablerna (`--c-acc`, `--c-model-80`, `--fs-small`, `--space-4` …), och rotlayouten
  lägger in dem i `<head>`. Mörkt läge följer operativsystemet. `data-theme` på `<html>`, eller på vilket element som
  helst, styr temat för det trädet.
- `color.ts` innehåller WCAG-kontrast, OKLab-ΔE och simulering av färgblindhet (samma matriser som datavisualiserings-
  skillens validerare). `tokens.test.ts` kontrollerar textkontrast ≥ 4,5:1, markeringar ≥ 3:1, blått/orange ΔE ≥ 8 vid
  protan, deutan och tritan och ≥ 15 vid normalt seende, samt att varje `var(--c-*)` i koden är definierad.
- `format.ts` ger svensk talformatering (mellanslag, decimalkomma, äkta minus) och månads- och kvartalsetiketter.
- `state.ts` innehåller tillståndsvokabulären (färg, glyf och ord, alltid alla tre) och `divergingFill()`. Den blandar
  orange, grå mitt och blått med `color-mix` i webbläsaren, så att samma förrenderade SVG blir rätt i båda lägena.
- `charts/` innehåller primitiverna: `ChartFrame` (rubrik, genererad mening som tillgängligt namn, statusmärke,
  tooltip, källa, licens och tabellvy), `Axis`, `Line`, `Band` (yta eller staplar), `QuantileDots`, `StripeCell` och
  `Stripes`, `Glyph`, `StatusBadge`, `Legend`, `Tooltip`, `TableToggle` och `DataTable`. Allt importeras från
  `$lib/design`.
- Katalogen visar alla komponenter med exempelvärden: `/next/_katalog/`. Den länkas inte från menyn.

**Tillgänglighet i diagrammen.** SVG:n har `role="img"` och namnges av rubriken och den genererade meningen.
Hovringstips är till för pekare. För tangentbord och skärmläsare finns samma tal alltid i tabellvyn (knappen "Visa
tabell", `aria-pressed`). Därför är enskilda markeringar inte tabbstopp. Breda tabeller går att fokusera och rulla.

**Responsivt utan layoutskift.** Diagrammen förrenderas med standardbredden och ritas om med den uppmätta bredden
efter hydreringen. Höjden är fast i px, så sidan flyttar sig inte (CLS).

### Data (`web/src/lib/data/`)

Python äger all data och licensgrinden. Frontend läser bara site_bundle (W3: `python -m ai_tracker.site_bundle build`).
Sökvägarna följer W3:s exporterare: `manifest.json`, `overview.json`, `flow.json`, `method.json`, `withheld.json`,
`branch/<G>.json`, `series/index.json`, `series/<nyckel>.json`, `nowcast/<id>.json` och `regime.json`.

- `createBundle(reader)` ger typade laddare: `manifest()`, `overview()`, `flow()`, `method()`, `branch(kod)`,
  `seriesIndex()`, `series(nyckel)`, `nowcast(id)` och `entries()` (id:n för förrenderingen). Varje dokument
  kontrolleras strukturellt, och manifestets `version` (W3:s fält, `schema_version` godtas också) måste ha huvudversion 1. Ett kontraktsbrott stoppar
  bygget.
- På servern (förrenderingen) används `bundle()` från `$lib/server/bundle`, som läser från `static/data/`. I webbläsaren
  används `clientBundle(fetch, base)`, som hämtar samma filer från `/next/data/` (tidsresa och utforskning i våg 1–2).
- `sync-bundle.mjs` väljer källan i den här ordningen: `SITE_BUNDLE_DIR` (riktig bundle), sedan W3:s
  `web-data-fixtures/` (eller `web-data-fixtures/site_bundle/`), och sist `web/fixtures/provisional/`.
  `REQUIRE_REAL_BUNDLE=1` vägrar fixtures. Det används vid publicering.
- **Provisorisk fixture:** W3:s fixtures fanns inte när skelettet byggdes. Den provisoriska fixturen är syntetisk och
  har `"synthetic": true` och `"provisional": true` i manifestet. Med `synthetic` (även W3:s fixtures) visar sidan en
  streckad ruta "Testdata". Den följer W3:s sökvägar och de
  fält som exporteraren hade i sitt utkast. När `web-data-fixtures/` finns används den automatiskt, och
  `loaders.test.ts` kör samma kontroller mot båda. Den provisoriska fixturen kan då tas bort. Skelettet är också prövat
  mot W3:s fixtures som de låg i W3:s arbetskopia 2026-11-24 (bygge, vitest, budget och alla 78 Playwright-tester
  gröna, 34 sidor).

## Kommandon

Kör i `web/` med Node 22.

| Kommando | Vad |
|---|---|
| `npm ci` | installerar exakt det som står i låsfilen |
| `npm run dev` | väljer bundle och startar utvecklingsservern (`http://localhost:5173/next/`) |
| `npm run build` | väljer bundle och förrenderar allt till `web/build/` (adresser under `/next/`) |
| `npm run preview` | serverar `build/` på `http://localhost:4173/next/` |
| `npm run check` | svelte-check (TypeScript och Svelte), varningar räknas som fel |
| `npm test` | vitest: tokens, format, kvantilprickar, komponenter och laddare |
| `npm run test:e2e` | Playwright mot `build/` (startar preview själv), dator 1280 px och mobil 375 px |
| `npm run budget` | gzip-storlek per sida mot budgeten |
| `npm run external-hosts` | statisk kontroll av `build/` |

Riktig data lokalt: `PYTHONPATH=src python -m ai_tracker.site_bundle build --out /tmp/bundle` och sedan
`SITE_BUNDLE_DIR=/tmp/bundle npm run build`. Skärmbilder: `SHOTS_DIR=<katalog> npx playwright test screenshots`.
I sessionsmiljön finns Chromium i `/opt/pw-browsers` (revision 1243). Därför är `@playwright/test` låst till 1.63.0,
och `playwright-core` är låst med `overrides`.

**Budget (gzip, per sida):** JS ≤ 150 kB, CSS ≤ 30 kB och data inlagd i HTML ≤ 100 kB (avsnitt 6.3). Det som laddas
lat, som DuckDB-WASM på `/data`, finns inte i HTML:en och räknas inte. Så ska det vara. Skelettet ligger på 54–75 kB JS
per sida.

## Sidorna och vem som äger dem (våg 1)

| Route | Katalog | Ägare |
|---|---|---|
| `/next/` | `src/routes/+page.*` | W5 Startsidan |
| `/next/flode/` | `src/routes/flode/` | W6 Led och grenar |
| `/next/gren/[id]/` | `src/routes/gren/[id]/` | W6 |
| `/next/serie/[key]/` | `src/routes/serie/[key]/` | W7 Serieinstrumentet (W9 lägger till tidsresa) |
| `/next/prognoser/` | `src/routes/prognoser/` | W8 Prognossidor |
| `/next/metod/` | `src/routes/metod/` | W11 Utforskbar metod |
| `/next/_katalog/` | `src/routes/_katalog/` | W2 (designsystemet) |

Varje sida i skelettet är en platshållare. Den är kopplad till laddarna och har en kommentar högst upp som anger
ägaren.

### Så lägger ett spår i våg 1 till en sida

1. Arbeta bara i din route-katalog. Delade komponenter i `src/lib/design/` ägs av W2 och ändras genom en W2-uppföljning.
   En ny delad komponent läggs i katalogen `/next/_katalog/` med exempel.
2. Data: `+page.server.ts` med `load()` som anropar `bundle()` från `$lib/server/bundle`. En dynamisk route exporterar
   `entries` (se `gren/[id]` och `serie/[key]`), så att varje id förrenderas. Fält som saknas i typerna läggs till i
   `src/lib/data/types.ts`. Hellre ett nytt valfritt fält än en ändrad betydelse, och W3:s schema är facit.
3. Diagram: `ChartFrame` med `description` (en mening genererad ur data) och `table` (samma tal formaterade med
   `format.ts`). Färg betyder bara riktning. Serier i små multiplar ritas med neutral bläckfärg. Status (`recon`, `live`
   eller `backtest`) märks alltid.
4. Länkar: `resolve('/gren/[id]', { id })` från `$app/paths`, aldrig hårdkodat `/next/`.
5. Lägg till routen i `tests/e2e/routes.ts`, så att smoke, axe och skärmbilder täcker den.
6. Klart när `npm run check`, `npm test`, `npm run build`, `npm run budget`, `npm run external-hosts` och
   `npx playwright test` är gröna, och du har granskat skärmbilderna själv.

## Navigering och delning (`web/src/lib/nav/`, W12)

- **Toppnavigeringen** (`MainNav`, `SearchButton`, temaväxlaren) ligger i `+layout.svelte`. På mobil står märket, Sök
  och temat på första raden och menyn på andra. "Flödet" är markerat också på led-, gren- och seriesidor.
- **Sök** (`⌘K`/`Ctrl K`, `/` utanför textfält, eller knappen): en modal `<dialog>` med WAI-ARIA-mönstret combobox med
  listbox (`aria-activedescendant`, ↑/↓, PageUp/PageDown, Enter, Esc rensar och stänger). Indexet `/next/sok.json`
  byggs vid förrenderingen ur `series/index.json`, `overview.json`, `flow.json` och `nowcast/*.json` (bara
  publicerbara serier) och hämtas först när sökningen öppnas. Dialogen laddas också lat. Matchningen bryr sig inte
  om versaler eller accenter, alla ord måste träffa, och en exakt kod (G6, L3, N2, en serienyckel) kommer först.
  Utan JavaScript är knappen en länk till `/next/sok/`, som är ett förrenderat register över allt sökbart.
- **Djuplänkar:** avsnittet ligger i hashen som `avsnitt=<id>` bredvid vyns tillstånd, enligt samma konvention som
  `permalink.ts` (okända nycklar bevaras), till exempel `/next/serie/us_ip_semis_m/#fonster=5&avsnitt=rev-h`. Ett
  vanligt ankare (`#rev-h`) fungerar också. Varje synlig `h2` i `<main>` är ett avsnitt. Id:t är sidans eget, annars
  en slug utan datum. Sidägare: ge rubriker ett eget stabilt `id`, så är länken stabil.
- **Delningsbilder:** `og/<sida>.svg` ritas vid förrenderingen ur samma data som sidan (`describe.server.ts`, `og.ts`),
  och `scripts/og-png.mjs` gör en PNG av varje (1200×630, Playwrights Chromium, cache på innehållets hash). Därför
  installeras Chromium före bygget i CI. Titel och beskrivning genereras ur data. `og:url` och `og:image` är absoluta
  och utgår från `SITE_URL`, annars från GitHub Pages för repot i manifestet. Budget: 120 kB per PNG och 40 kB per SVG
  (bygget stoppas om en bild går över).
- **Citeringsrad** längst ned på varje sida ("Dela och citera"): `AI-utrullningen, <sidan eller serie X (nyckel; källa:
  …)>, version per <datum>, <permalänk>`. Permalänken tar med vyns hash, och `as_of` i hashen blir versionsdatumet.
  Den kan kopieras, och samma ruta listar sidans avsnitt.
- En ny route behöver inget av W12 för att fungera: den får en generisk beskrivning och delningsbild. Lägg den i
  `describe()` i `describe.server.ts` för en egen.

## CI och publicering

Pages har **en** publicering per repo. Därför publicerar ett enda jobb både den nuvarande och den nya sidan:

```
pages.yml (efter veckohämtning, ögonblicksbild, skarpa prognoser eller manuellt)
  next:   uses pages-next.yml (bundle=real, ref=main)  -> artefakt web-next (web/build)
  build:  needs next, körs även om next misslyckades
          python -m ai_tracker.site build --out site       (den nuvarande sidan, oförändrad)
          om next lyckades: web-next -> site/next/          annars en varning, och sidan publiceras utan /next/
          upload-pages-artifact site/
  deploy: needs build (uttryckligt villkor, så att ett misslyckat next aldrig stoppar publiceringen)
```

`pages-next.yml` publicerar aldrig själv. Den körs:

- vid push eller pull request som rör `web/`, `web-data-fixtures/`, `src/ai_tracker/site_bundle/` eller workflowen.
  Då används fixtures, och ingen data eller hemlighet behövs.
- manuellt (`workflow_dispatch`, valet `fixtures` eller `real`).
- från `pages.yml` (`workflow_call`, `real`). Då återställs datacachen, bundlen byggs i Python och
  `REQUIRE_REAL_BUNDLE=1` sätts. Fixtures publiceras alltså aldrig som data. Saknas `ai_tracker.site_bundle` (före W3)
  misslyckas jobbet med en varning, och den nuvarande sidan publiceras utan `/next/`.

Grindarna i ordning: `npm ci`, svelte-check, vitest, förrendering (`handleHttpError: 'fail'`, så att ett schemabrott
eller en trasig länk stoppar bygget), statisk kontroll av externa värdar, budget, Playwright smoke (alla routes,
1280 och 375 px, inga förfrågningar till andra värdar, inga konsolfel, ingen vågrät rullning, SVG finns utan JS),
axe WCAG 2.2 AA i ljust och mörkt läge, och skärmbilder av alla routes. Skärmbilder, Playwright-rapport och
budgetrapport laddas upp som artefakten `web-screenshots`.

`tests/test_web_workflow.py` (pytest) låser designen: ett enda publiceringsjobb, att `/next/` läggs till bara när
bygget lyckats och före Pages-artefakten, att `pages-next.yml` aldrig publicerar och kör alla grindar, och att
beroendena har exakta versioner med en låsfil.

**Engångsanmärkning:** inget nytt behövs i Settings. Pages källa är redan "GitHub Actions" (`docs/drift.md`).
