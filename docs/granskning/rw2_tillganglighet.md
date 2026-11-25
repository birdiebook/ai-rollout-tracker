# R-W2: Tillgänglighet och prestanda för den nya hemsidan

Oberoende granskningsspår, 2026-11-25, gren `auto14/rw2-a11y` (från `2efe76b`). Underlag: `CLAUDE.md`,
`docs/steg3/hemsida_vision.md` (avsnitt 1, 4, 5 och 6.3) och `docs/steg3/webb.md`.

**Bygget som granskades:** ett riktigt paket (`python -m ai_tracker.site_bundle build`, delad tabell, 388 serier) och
sidan byggd mot det med produktionens bas (`SITE_BUNDLE_DIR=<paket> BASE_PATH=/ai-rollout-tracker/next npm run build`,
466 sidor och 467 delningsbilder). Bygget serverades med `npx vite preview` på en egen port. Alla mätningar gjordes med
Playwright 1.63 och Chromium 1243. Skripten ligger utanför repot (scratchpad) och beskrivs under varje punkt. Det
som ska fortsätta gälla har blivit tester i `web/tests/e2e/rw2.spec.ts`.

## Domar i korthet

| # | Punkt | Dom |
|---|---|---|
| 1 | axe på alla routetyper, ljust och mörkt, interaktiva tillstånd | **OK.** 0 överträdelser i 54 körningar, både före och efter rättningarna. Egen kontroll av SVG-text: 0 av 1 788 under AA |
| 2 | Tangentbord | **Godkänd efter rättning.** Fyra fel rättade: skip-länken raderade vyns tillstånd, fokus tappades när tidsresan startade och slutade, den klistrade tidsraden täckte fokus (2.4.11), och enteckensgenvägar (2.1.4) |
| 3 | Skärmläsare (statisk kontroll) | **OK med anmärkningar.** Alla 108 diagram heter något och har en genererad mening. Landmärken och en h1 per sida. Rättat: ett rubrikhopp och växlingsknappar som bytte namn trots `aria-pressed`. Kvar: tabellvyer går inte att nå utan JS, och tidsresans gren-gnistor saknar tal |
| 4 | Prestanda på mobilprofil | **Underkänd före, godkänd för LCP efter rättning.** LCP gick från 2,1–2,8 s till 0,72–0,81 s (mål < 1,5 s) när CSS:en lades inline. CLS är 0. TBT ligger kvar på 0,46–0,71 s på de tunga sidorna, och orsaken är dolda tabeller som utgör 78 % av DOM:en på seriesidan. Beskrivs för ett rättningsspår |
| 5 | Mörkt läge, forced-colors, minskad rörelse, 200 % zoom | **OK efter rättning**, med en reservation: forced-colors kan inte renderas på riktigt i den här miljön. Rättat: en nedtryckt knapp syntes inte i högkontrastläge, och färgrutorna i förklaringarna försvann |

**Slutdom: godkänd för tillgänglighet (WCAG 2.2 AA) efter rättningarna i den här grenen. För prestanda är LCP- och
CLS-målen uppfyllda efter rättningen, men TBT behöver ett rättningsspår (P1 nedan) innan sidan ersätter den gamla.**

## 1. axe (WCAG 2.2 AA)

**Metod.** `@axe-core/playwright` med taggarna `wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa`, 1280 px, med
`colorScheme` ljust och mörkt. Det blev 27 tillstånd per läge:

- 14 routetyper: start, flöde, led, gren, månatlig serie (`us_ip_semis_m`), daglig serie, prognosöversikt,
  prognossida (N2), avstämningar, regim, metod, sök, månadsberättelse och katalogen.
- Söken öppen med träffar (Ctrl K, "halvledare").
- Tidsresa aktiv på start, gren, serie och månad, plus en sida utan tidsresevy (`#as_of=2026-03-15`).
- Revisionsvyn öppen med reglaget flyttat fem steg.
- Metodsidan med alla reglage flyttade fyra steg, alla `select` bytta och alla kryssrutor ikryssade.
- Månadsberättelsen efter j, j.
- Alla tabellvyer öppna på start, serie, gren och prognos.

**Resultat:** 0 överträdelser i alla 54 körningar, både före och efter rättningarna.

axe lämnar många kontrastnoder som "incomplete", till exempel 102 på startsidan. Nästan alla är SVG-text
(`imgNode`), glyfer (`nonBmp`) och tabeller i rullbara behållare (`elmPartiallyObscured`). SVG-texten kontrollerades
därför för sig. För varje synlig `<text>` beräknades den faktiska fyllningen gånger opaciteten mot närmaste HTML-
bakgrund, på 13 sidor och tillstånd i båda lägena: **0 av 1 788 texter under 4,5:1.** Seriesidan har 45 axeltexter
under 11 px. Det är inget AA-krav, men det ligger under visionens 11–13 px (4.5).

## 2. Tangentbord

**Metod.** Tab genom varje sida tills fokus går runt. För varje stopp registrerades om fokusmarkeringen syns (outline
eller box-shadow), om elementet är dolt eller har storleken noll, och om något annat ligger ovanpå (`elementFromPoint`).
Sedan testades flöden: skip-länk, sökdialog, tidsresa, tabellvy och månadsberättelse. Det gjordes på 11 sidor,
inklusive tidsresa.

**Bra:** inga positiva `tabindex`. Varje stopp har synlig fokusmarkering (`--c-focus`, nästan svart respektive
nästan vit). Inget fokus hamnar på dolda element, och skip-länken är första stoppet och syns vid fokus.

**Sökdialogen följer mönstret:**

- `role=combobox`, `aria-expanded` och `aria-activedescendant`, som följer ↑ och ↓.
- Antalet träffar meddelas i en status ("12 träffar.").
- Första Esc rensar, andra Esc stänger, och fokus går tillbaka till Sök-knappen.
- Tab stannar i dialogen. Det enda stoppet utanför är webbläsarens eget gränssnitt, vilket är det inbyggda modala
  beteendet.

Antalet tabbstopp är rimligt: 23–71 per sida, och 176 på metodsidan med alla reglage.

**Fel som är rättade:**

| Fel | WCAG | Före | Rättning |
|---|---|---|---|
| Skip-länken bytte hashen mot `#main`, så vyns tillstånd försvann (`#fonster=5` blev `#main=`, och fönstret återställdes) | 2.4.3, 2.4.1 | hashen förstördes på alla sidor med tillstånd i URL:en (utan tidsresa) | `web/src/routes/+layout.svelte:19–27,36,52`: med JS flyttar länken fokus till `<main tabindex="-1">` och rör inte URL:en. Utan JS fungerar `href` som förut |
| "Tidsresa: vad visste vi den …?" och "I dag" byter ut tidsraden, så fokus hamnade på `<body>` | 2.4.3 | fokus gick till BODY i båda riktningarna | `web/src/lib/timetravel/TimeBar.svelte:34–44`: fokus går till datumreglaget vid start och till startknappen vid "I dag". Knappen "Visa sidan som i dag" lämnar fokus på `main` (`TimeTravel.svelte`, `showToday`) |
| Den klistrade tidsraden (≥ 861 px) täckte fokuserade element vid Shift+Tab | 2.4.11 (AA) | 7 av 41 stopp helt under raden | `TimeBar.svelte:45–57`: `scroll-padding-top` = radens uppmätta höjd + 18 px medan den klistrar. Efter rättningen täcktes 0 stopp |
| j och k i månadsberättelsen fungerade var som helst på sidan, och "/" öppnade söken. Det är enteckensgenvägar som inte går att stänga av | 2.1.4 (A) | j med fokus i huvudmenyn hoppade till kort 2 | `web/src/lib/story/StoryView.svelte:71–72`: j och k fungerar bara när fokus är i berättelsen (texten är ändrad). `web/src/lib/nav/SearchButton.svelte`: "/" är borttagen, ⌘K och Ctrl K finns kvar (genvägar med modifierare undantas) |

**Anmärkningar (inte fel):**

- När tabellvyn öppnas visas tabellen *före* knappen i DOM-ordningen. Den nås med Shift+Tab, och tabellen är ett
  fokuserbart område med namn ("De 600 senaste av 658 värden …"). Det fungerar, men en skärmläsaranvändare måste
  veta om det. Låt det vara som det är. Att flytta fokus vid en växling bryter mot APG.
- Datumfälten (`<input type=date>`) ger 3–4 tabbstopp var. Det är Chromes inbyggda segment.
- Efter ett val i söken hamnar fokus på `<body>`. SvelteKits ruttannonsör läser upp den nya titeln. Det är standard
  och godtagbart.

## 3. Skärmläsare (statisk kontroll)

**Metod.** För varje sida: landmärken, rubrikhierarki (synliga), SVG med `role=img` och deras beräknade namn,
SVG som exponerar text utan roll, live-regioner, glyfer som läses upp, dubblerade id och `lang`. Det gjordes på 15
sidor och tillstånd.

**Resultat:**

- `lang="sv"` och en unik `<title>` som genereras ur data på varje sida, även under tidsresa ("G6 som den var känd
  2026-03-15 – AI-utrullningen").
- Landmärken: `header`, `nav` "Huvudmeny", `main`, `footer` och namngivna `section`/`nav` för varje avsnitt. Det är
  en h1 per sida, inga dubblerade id och inga bilder utan alt.
- **108 diagram-SVG:er på de granskade sidorna. Alla har `role=img`, 0 saknar namn och 0 exponerar sin text utanför
  rollen.** Namnet är rubriken plus den genererade meningen.
- **Är diagrammen begripliga utan syn? Ja, för nästan alla.** Meningarna bär budskapet med tal, inte bara "ett
  diagram över X". Exempel: "Index 0,72 (accelererar) i oktober 2026, 46 månader sedan jan 2023, 18
  tillståndsbyten", "657 av 658 perioder har ändrats sedan de först publicerades … störst jan 2009, −55,3 %",
  "B3: 43 % inom 50 %-intervallet, 77 % inom 80 %-intervallet, 95 % inom 95 %-intervallet (n 226)". Tabellvyn ger
  sedan alla tal.
- Live-regioner finns där något ändras utan sidbyte: sökträffar, tidsresans datum, metodreglagens domar, permalänk
  kopierad och SvelteKits ruttannonsör.

**Rättat:**

- `/prognoser/` hoppade från h1 till h3 ("Kalendern: nästa skarpa prognos"). Nu är det en h2:
  `web/src/routes/prognoser/parts/Calendar.svelte:31` (`headingLevel={2}`).
- Tabellväxlaren hade `aria-pressed` *och* bytte namn ("Visa diagram, nedtryckt" när tabellen visas), vilket APG
  avråder från. Namnet säger nu vad knappen gör och `aria-pressed` är borttaget:
  `web/src/lib/design/charts/TableToggle.svelte`. Samma sak gällde Spela/Paus i tidsraden. Där är glyfen ▶/❚❚
  dessutom `aria-hidden` (`TimeBar.svelte`, knappen Spela).

**Kvar (till rättningsspår, i prioritetsordning):**

1. **B1, tabellvyerna är oåtkomliga utan JavaScript.** `ChartFrame.svelte:83` förrenderar varje tabell med
   `hidden`, och växlaren på rad 91 gör ingenting utan JS. Utan JS finns alltså tabellerna i HTML:en men går inte
   att se, och de är inte heller exponerade för skärmläsare. Visionen P6 och `webb.md` lovar en tabellvy för varje
   diagram. Lösningen hänger ihop med prestanda P1 nedan.
2. **B2, tidsresans gren-gnistor saknar tal.** `web/src/lib/timetravel/views/BranchOn.svelte:112` har bara
   `aria-label` "Postens takt för X vid varje månadsslut fram till …", och ingen tabellvy (10 SVG, 1 tabell på
   `gren/G6/#as_of=…`). Det senaste värdet står i texten under, men historiken går inte att nå utan syn. Lägg till
   antal riktningsbyten och min/max i namnet, eller en gemensam tabell.
3. Små textfrågor:
   - Enheten skrivs "log x100 per år" med ett vanligt x (`src/ai_tracker/state/measures.py:323`) och läses som
     "log x 100". På andra ställen står "log ×100". Gör det enhetligt med ×.
   - "SA" förklaras inte i seriemeningen.
   - Pilarna "→ ↓ ↑" i länktexter ("Till läget →", "Nästa kort ↓") läses upp som "högerpil". Lägg dem i
     `<span aria-hidden="true">`.
4. Hovringstipset har `role="status"` (`Tooltip.svelte:12`) och skapas och tas bort vid varje hovring. För en
   skärmläsare med mus blir det brus, och det meddelas sällan alls eftersom regionen skapas med innehåll. Ta bort
   rollen. Tabellvyn är skärmläsarens väg.

## 4. Prestanda på mobilprofil

**Profil:** 412×823 CSS-px, DPR 1,75, mobil-UA och pekskärm. CPU-strypning 4× (CDP) och Slow 4G med Lighthouses
DevTools-värden: 562,5 ms latens, 1 474,56 kbit/s ned och 675 kbit/s upp. Kall cache, tre körningar per sida, median.
LCP, CLS (största sessionsfönster) och TBT (långa uppgifter efter FCP, delen över 50 ms) mättes med
PerformanceObserver.

| Sida | LCP före | LCP efter | CLS | TBT före | TBT efter | Längsta uppgift efter | JS (överfört, gzip) | HTML (gzip) |
|---|---|---|---|---|---|---|---|---|
| Start | 2 144 ms | **800 ms** | 0,000 | 813 ms | 465 ms | 515 ms | 105 kB | 27 kB |
| Gren G6 | 2 108 | **752** | 0,000 | 567 | 499 | 549 | 104 kB | 34 kB |
| Serie `us_ip_semis_m` (störst) | 2 184 | **760** | 0,000 | 1 157 | 710 | 753 | 113 kB | 60 kB |
| Metod | 2 804 | **784** | 0,000 | 396 | 650 | 700 | 132 kB | 52 kB |
| Månad 2026-10 | 2 392 | **732** | 0,000 | 582 | 457 | 507 | 118 kB | 26 kB |
| Flöde | 2 268 | 808 | 0,000 | 288 | 201 | 251 | 100 kB | 14 kB |
| Prognos N2 | 2 068 | 808 | 0,000 | 276 | 270 | 320 | 116 kB | 15 kB |
| Serie, daglig (`ai_postings_share_fr_d`) | 2 092 | 756 | 0,000 | 568 | 571 | 621 | 113 kB | 64 kB |

TBT varierar ±150 ms mellan körningar (metod 396 → 650 är brus, inte en försämring). Budgeten (`npm run budget`,
gzip -9) ger 92,6–119,5 kB JS per sida, 4,9–7,9 kB CSS och högst 12,7 kB inlagd data. Allt ryms i 150/30/100 kB.

**Orsak till den långsamma LCP:n och rättningen.** `svelte.config.js` hade `inlineStyleThreshold: 0`. Varje sida
hade 4–8 renderblockerande stilmallar efter 26–34 `modulepreload`, så första målningen väntade på en andra rundresa.
Nu läggs all CSS inline (`web/svelte.config.js:23`, `Infinity`), och länkarna står kvar som `disabled` för
klientnavigeringen. HTML:en växer med 3–5 kB gzip per sida, och LCP sjunker med cirka 1,3–2 s.

**Reservation:** `vite preview` kör HTTP/1.1 med sex anslutningar, där stilmallarna köar bakom modulförladdningarna.
GitHub Pages kör HTTP/2, så LCP "före" hade varit lägre där, uppskattningsvis 1,3–1,5 s. Inline-CSS tar ändå bort en
hel rundresa i båda fallen. Testet `CSS is inline` i `rw2.spec.ts` låser rättningen.

**Seriesidornas HTML.** Den största är `serie/us_ip_semis_m` med 519 kB raw och 57 kB gzip, inte 700 kB. 387
seriesidor väger i snitt 122 kB raw och 47 MB tillsammans. Sammansättningen på den största sidan: tabeller 290 kB,
SVG 123 kB och hydreringsdata 51 kB. **5 153 av 6 588 element (78 %) ligger i dolda tabellvyer**. På grensidan G6
är det 2 411 av 3 238, och på startsidan 611 av 2 263. En CPU-profil (4×) av seriesidan visar cirka 730 ms i Sveltes
körtid under hydreringen och cirka 640 ms i parsning och layout. DOM-storleken är alltså det som driver TBT.

**P1, rättningsspår (rekommendation): rendera tabellvyn först när den öppnas, och ge den en väg utan JS.**

- `ChartFrame.svelte:83`: `{#if showTable}<DataTable …/>{/if}` i stället för en förrenderad tabell med `hidden`.
  Väntat resultat på seriesidan: cirka 75 % färre element och cirka 290 kB mindre HTML raw. Uppskattningsvis halveras
  TBT, men det ska mätas.
- Utan JS: växlaren renderas inte före hydreringen (som `SearchButton`). I stället visas en länk till seriens
  publicerade data (`data/series/<nyckel>.json`, eller en förrenderad CSV), så att tabellvägen inte bara försvinner
  för den som saknar JS (B1).
- Ändringen rör W2:s delade komponent och flera tester som läser tabellraderna i förrenderad HTML
  (`timetravel.spec.ts`, seriens tester). Därför ska den göras i ett eget spår och mätas om med samma profil.
- Mål: TBT < 300 ms på serie- och grensidor med 4× strypning. Ett budgetsteg för antal DOM-element per sida
  (till exempel ≤ 2 500) i `budget.mjs` hindrar att det kommer tillbaka.

**Delningsbilderna.** Det är 467 PNG på 32–94 kB (median 64 kB), 28,5 MB tillsammans och 32 MB med SVG:erna. Inga är
över budgeten på 120 kB. Sidorna laddar dem aldrig, de nämns bara i `og:image`, så **de påverkar inte användarens
prestanda.** Kostnaden är artefaktens storlek (bygget är 108 MB, långt under Pages gräns på 1 GB) och byggtiden vid
kall cache. Hashcachen gör ombyggen gratis (0 ritade vid andra bygget). Ingen åtgärd behövs.

**Rättat i budgetgrinden.** `web/scripts/budget.mjs:25–36,67–70`: en tillgång som HTML:en nämner men som saknas i
bygget räknades som 0 kB. När `BASE_PATH` inte var satt som vid bygget passerade alltså varje sida med "JS 0 kB",
vilket hände i den här granskningen. Nu misslyckas budgeten och anger orsaken. I CI sätts `BASE_PATH` på jobbnivå,
så CI har inte varit fel, men grinden kunde tyst bli verkningslös.

## 5. Mörkt läge, forced-colors, minskad rörelse och zoom

- **Mörkt läge:** axe ger 0 överträdelser på alla 27 tillstånd, och SVG-textkontrasten ger 0 under AA (se punkt 1).
  Paletten är egen, inte inverterad, enligt 4.4.
- **forced-colors (Windows högkontrast).** **Reservation:** Playwrights `forcedColors: 'active'` växlar bara
  mediefrågan. Chromium målar inte med systemfärgerna i den här miljön (bakgrunden förblir `rgb(249,249,247)`).
  Den verkliga renderingen kunde därför inte verifieras, och den bör prövas en gång på Windows med Kontrast #1 och
  #2. Statisk granskning:
  - Markeringarna har `forced-color-adjust: none` (639 element på startsidan), och glyferna blir `CanvasText`.
    Riktningen bärs alltid också av glyf och ord.
  - **Rättat:** en nedtryckt `.chip` (tidsfönster, skala, grenval, intervallnivå och filter) skilde sig från de andra
    bara genom bakgrunden, som högkontrastläget ersätter. Nu används `Highlight`/`HighlightText`, och inaktiva knappar
    blir `GrayText` (`web/src/lib/design/base.css:178–197`).
  - **Rättat:** färgrutorna i förklaringarna (`.legend .sw`) var bara bakgrund och försvann, medan markeringarna de
    förklarar behöll sin färg. Nu har de också `forced-color-adjust: none`.
  - Testet `forced colours` i `rw2.spec.ts` kontrollerar båda.
- **prefers-reduced-motion:** 0 element med övergång eller animation på 11 sidor, och `scroll-behavior: auto`.
  Månadsberättelsen rullar utan mjuk rullning, vilket redan testas i `story.spec.ts`. Spela startar bara när
  användaren trycker.
- **200 % zoom (640×450 CSS-px), 400 % (320 px) och textavstånd (1.4.12):** ingen vågrät rullning och inga element
  utanför vyn på 11 sidor. Ingen text klipps. Det enda träffen, `p.desc` i små multiplar, är avsiktligt visuellt dold
  men står kvar som diagrammets beskrivning.
- Målstorlek (2.5.8) passerar i axe. Reglage och knappar har `--hit`.

## Ändrade filer och grindar

| Fil | Ändring |
|---|---|
| `web/svelte.config.js` | `inlineStyleThreshold: Infinity` (LCP) |
| `web/src/routes/+layout.svelte` | skip-länken behåller hashen, `main tabindex="-1"` |
| `web/src/lib/timetravel/TimeBar.svelte`, `TimeTravel.svelte` | fokus vid start och "I dag", `scroll-padding-top` för den klistrade raden, Spela utan `aria-pressed` och med dold glyf |
| `web/src/lib/story/StoryView.svelte` | j och k bara med fokus i berättelsen |
| `web/src/lib/nav/SearchButton.svelte` | "/" borttagen, `aria-keyshortcuts` uppdaterad |
| `web/src/lib/design/charts/TableToggle.svelte` | inget `aria-pressed` på en knapp som byter namn |
| `web/src/routes/prognoser/parts/Calendar.svelte` | h2 i stället för h3 |
| `web/src/lib/design/base.css` | forced-colors: nedtryckt och inaktiv knapp, färgrutor i förklaringar |
| `web/scripts/budget.mjs` | saknade tillgångar ger fel i stället för 0 kB |
| `web/tests/e2e/rw2.spec.ts` (ny), `story.spec.ts`, `timetravel.spec.ts`, `components.test.ts` | tester för rättningarna |
| `docs/steg3/webb.md` | söken, tabellväxlaren och j/k beskrivna som de är nu |

Grindar på det sammanslagna resultatet, med riktigt paket och `BASE_PATH=/ai-rollout-tracker/next`:

- `npm run check`: 0 fel, 0 varningar.
- `npm test`: 371 gröna.
- `npm run build`: 466 sidor.
- `npm run budget`: 466 sidor OK.
- `npm run external-hosts`: OK.
- `PW_PORT=4541 npx playwright test`: 459 gröna och 5 överhoppade av 464, varav 8 nya tester i `rw2.spec.ts` per
  profil. Klistertestet körs bara på datorprofilen. Första körningen gav ett falskt larm i det nya testet (`<body>`
  räknades). Det är rättat, och hela sviten är omkörd grön.
- axe-svepet efter rättningarna: 0 överträdelser i 54 körningar.

Inte prövat: riktig högkontrastrendering på Windows, NVDA/VoiceOver med verklig uppläsning (bara statisk kontroll av
namn, roller och regioner) och fältdata från riktiga mobiler.
