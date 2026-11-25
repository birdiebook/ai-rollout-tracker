# R-W3: granskning av neutralitet och läsbarhet på den nya hemsidan (`/next/`)

Granskad 2026-11-25 på grenen `auto14/rw3-neutral` (från `2efe76b`). Granskningen är oberoende av W5–W13 och utgår från
CLAUDE.md (neutral spårning), visionen avsnitt 1 och 4.4, måttregistret "2026-11-25 – W13: urvalsregel för månadens
berättelse" och `docs/steg3/webb.md`.

**Underlag.** Ett riktigt paket (`python -m ai_tracker.site_bundle build`, delad bas från huvudkopians `data/`, 46
månader 2023-01–2026-10, alla rekonstruerade) och sidan byggd på det (`SITE_BUNDLE_DIR=… npm run build`, 467
delningsbilder). Skärmbilder av alla 29 routetyper i ljust och mörkt läge, på desktop (1280 px) och mobil (375 px):
116 bilder. Dessutom en ordlistekörning över all synlig text, `aria-label`, `alt`, `title`, metabeskrivningar och
delningsbildernas SVG (475 filer), en färgkontroll i OKLab med CVD-simulering (Machado 2009, full styrka) och ett
speglingstest av urvalsregeln på riktig data. Skripten låg i sessionens scratchpad och committas inte. Speglingstestet
finns redan som enhetstest (`tests/test_site_story.py::test_the_rule_is_symmetric_under_mirroring`).

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Formuleringar | **Godkänd med anmärkningar.** Inga larmord och inga värderande ord i genererad text. Tre asymmetrier i ordvalet: "tillbaka till expansion", startsidans regimtext som bara nämnde ena tröskeln, och tillståndsskiften märkta "mer/mindre takt". Alla tre är rättade |
| 2. Färger | **Godkänd med anmärkningar.** Inget rött eller grönt, och riktningarna går att skilja vid alla tre typerna av färgblindhet. I ljust läge är blått tyngre än orange (avstånd till mitten 41 mot 35). Det mörka orange drar mot rött. Stabil har samma grå som den naiva baslinjen |
| 3. Urvalsregeln (W13) | **Symmetrisk i praktiken.** Speglingen ger samma kort i samma ordning med omvänd riktning i alla 46 månader. Övervikten uppåt kommer från data, inte från regeln. Två svagheter: samma storhet kan visas två gånger (K5 och K6), och K5 ger ungefär lika många utslag som slumpen skulle ge |
| 4. Fem-sekunderstest | **Neutralt och sant, men rekonstruerat uppfattas som lika säkert som skarpt.** Märket "rekonstruerad historik" är litet och grått bredvid en rubrik i 40 px |
| 5. Läsbarhet | **Delvis godkänd.** Grensidan och metoden förklarar sina begrepp. Startsidan, månadssidan och prognossidorna använder dödband, diffusionsindex, log×100, pe, PIT, CRPS, A5, C4, G-D, BOCPD och spårnamn (C2, R7) utan förklaring där de står |

**Slutdom: godkänd för fortsatt utveckling under `/next/`, med fyra rekommendationer före byte av huvudsida:** (a)
tydligare märkning av rekonstruerat (punkt 4), (b) en registrerad ändring av W13 om dubbletter och slumpnivå (punkt 3),
(c) en balanserad orange i ljust läge och ett mindre rött orange i mörkt läge (punkt 2), och (d) en förklaring på plats
av de fem vanligaste fackorden (punkt 5). Inget av detta väljer en riktning, men (a) och (b) påverkar hur säker sidan
ser ut. Det är en ärlighetsfråga.

---

## 1. Formuleringar

**Metod.** Ordlistan bestod av månadsbrevets `letter.BANNED_WORDS`, registrets larmord och en utökad lista med 60
stammar (kraftig, imponerande, explosion, bubbla, hype, oro, problem, framgång, återhämtning, avmattning, tappar,
tydlig, betydande, massiv, extrem, positiv, negativ, fundamental, tillbaka, normal, risk m.fl.). Jag räknade också
motsatspar (accelererar/bromsar in, ökar/minskar takten, högre/lägre, expansion/inbromsning, övre/nedre zonen) och läste
alla kort på månadssidan för oktober 2026, start-, gren-, regim- och avstämningssidan, och ett urval av seriesidor.

**Träffar och bedömning:**

| Ord | Var | Bedömning |
|---|---|---|
| `varning` (1) | regim: "Det är ingen varning och ingen värdering." | Metatext som avvisar värdering. Godtas |
| `bra`/`dåligt` (5) | start: "Färgen säger riktning, inte om det är bra eller dåligt", avstämningar, en seriefråga | Metatexten godtas. Seriefrågan "Hur bra bygger den bästa modellen webbappar …" (katalogtext) är beskrivande. Godtas |
| `stark` (1) | serie `g1_arena_text_top`: "Hur stark är den bästa chattmodellen …" | Katalogens fråga, inte genererad text. Kan formuleras "Hur högt rankas …". Låg prioritet |
| `svaghet` (1) | regim: "en känd svaghet" hos metoden | Om metoden, inte om utvecklingen. Godtas |
| `extrem` (355) | korttyperna K5 och K6, "extrem percentil" | Statistiskt korrekt, men för en lekman låter "extrem" som larm. Förslag nedan |
| `fundamentalt` (4) | start fråga 3 och regimsidans h1: "Har något fundamentalt ändrats?" | Lätt dramatiskt. "Har takten bytt nivå?" säger samma sak och är exaktare. Låg prioritet |
| `tillbaka` (5 i regimtexter) | "≤ 0,2: tillbaka till expansion", "Skiften tillbaka", "och tillbaka när …" | **Asymmetri.** Orden gör expansion till normalläget och inbromsning till avvikelsen. **Rättat** |
| `positiv`/`negativ` (8) | "en negativ förändring räknas som att takten ökar", "kan fortfarande vara positiv" | Tecken, inte värdering. Godtas |

Ingen genererad mening i paketets berättelser innehåller ett ord från de två registrerade listorna (testet
`test_generated_texts_are_neutral` håller och prövades här mot riktig data). Motsatsparen följer data. Till exempel står
"accelererar" 1 427 gånger och "bromsar in" 806 gånger, eftersom fler grenar accelererar. Inget par saknar sin motsats i
mallarna.

**Asymmetrier i mallarna, och vad som är rättat** (commit `8fb37ee`, med test):

1. `web/src/lib/regime/RegimeMeter.svelte:40`, `HoldoutStrip.svelte:70`, `web/src/routes/regim/+page.svelte:40–41, 93`:
   "tillbaka till expansion" och "Skiften tillbaka" har ersatts med "skifte till expansion" och "Skiften till
   expansion". Regeln är symmetrisk (≥ 0,8 respektive ≤ 0,2 två månader i rad), och nu är orden det också.
   `tests/e2e/regime.spec.ts:27` följer med.
2. `web/src/lib/start/Changed.svelte:23–24`: "Ett skifte registreras när två månader i rad ligger på minst 0,8" nämnde
   bara skiftet till inbromsning. Nu står båda trösklarna där. **Kvar att göra (W5):** diagrammet ritar bara strecket
   vid 0,8 (`Changed.svelte:33`). Rita också 0,2, som `RegimeMeter` gör.
3. `web/src/lib/story/StoryView.svelte:42–44` (`dirWord`): ett tillståndsskifte (K1) märktes "Tillståndsskifte,
   mindre takt" när G9 gick från accelererar till stabil. Det läses som att takten i grenen är lägre, men det som
   ändrats är andelen serier som ökar takten. Kortet märks nu "högre index" eller "lägre index".
4. `src/ai_tracker/site_bundle/story.py:326, 355`: "i den nedre zonen (≥ 95 eller ≤ 5)" angav båda zonernas gräns. Nu
   anger kortet bara sin egen gräns ("i den nedre zonen (≤ 5)"). Fixturerna är omgenererade, och testet heter
   `test_a_zone_card_names_only_its_own_bound`.
5. `StoryView.svelte`, Om urvalet: "1 kärnserier i extrem percentil" böjs nu i singular, och "Jämförelsemånad: 2026-09"
   har blivit "september 2026" (vitest i `story.test.ts`).

**Kvar att göra (beskrivs, ändras inte här):**

- Regimmodellen har bara en parameter som visas, P(inbromsning), på startsidan (`Changed.svelte:22`, "Sannolikheten
  för inbromsning …") och i K2-texten (`story.py:248–252`). Det är matematiskt likvärdigt med att visa P(expansion),
  men stapeln växer bara åt ett håll. Visa båda polerna på samma axel: 0 = expansion, 1 = inbromsning, som
  `RegimeMeter` redan gör. Ordparet expansion/inbromsning är dessutom ojämnt: ett tillstånd mot en process. Ett
  neutralare par är "regim med högre takt" och "regim med lägre takt". Det ändrar C4:s vokabulär och kräver ett beslut.
- Byt korttypernas namn från "Kärnserie i extrem percentil" och "Avstämning i extrem percentil" (`story.py:38–39`,
  `StoryView.svelte:26–27`, registret rad 624–625) till "Kärnserie i ytterzon" och "Avstämning i ytterzon". Det är
  registrets ord och ska därför ändras som en daterad ändring.
- Interna koder i texter till läsaren: "(A5)" (`story.py:356`), "(G-D, C4)" (`story.py:252`) och B3:s beskrivning med
  "(spår C2, huvudmodell efter granskning R7)" (`src/ai_tracker/site/data.py:80`). Ersätt dem med en länk till metoden
  och en vanlig mening, till exempel "Avstämningarna räknas inte i grenarnas index" och "B2 korrigerad för bolagens
  systematiska avvikelse mot sin egen guidance".
- Utanför min uppgift, men uppenbart: citeringsraden på startsidan börjar "AI-utrullningen, AI-utrullningen: läget
  oktober 2026". Det är redan noterat som RW1-X (`web/src/lib/nav/ShareCite.svelte:28–31`).

## 2. Färger

| Kontroll (OKLab ΔE×100) | Ljust | Mörkt | Krav |
|---|---|---|---|
| blått/orange, normalt seende | 32,3 | 31,8 | ≥ 15 ✓ |
| blått/orange, protan / deutan / tritan | 26,1 / 30,8 / 30,4 | 26,8 / 28,6 / 32,4 | ≥ 8 ✓ |
| stabil mot blått / orange (sämsta CVD) | 11,3 / 11,6 | 11,5 / 11,0 | – |
| **avstånd till mitten: blått / orange** | **41,2 / 35,1** | 32,7 / 33,0 | symmetri |
| **ljushet L: blått / orange** | **0,575 / 0,640** | 0,622 / 0,622 | symmetri |
| nyans orange (OKLCH, rött ≈ 29°) | 47° | **40°** | – |
| kontrast mot ytan: blått / orange / stabil | 4,30 / 3,48 / 3,46 | 4,79 / 4,48 / 5,24 | ≥ 3:1 ✓ |
| **stabil mot naiv baslinje** | **0,4** | **2,0** | olika roller |
| stabil mot "för få serier" (muted) | 10,9 | **3,6** | – |

**Dom: godkänd med anmärkningar.**

- **Inget rött eller grönt, och glyf och ord finns alltid.** ▲ ● ▼ ○ står bredvid färgen överallt där jag letade
  (tally, kedjan, korten, legender). Därför går riktningen att läsa även i gråskala och vid alla tre typerna av
  färgblindhet. ✓
- **Symmetrin i ljust läge är inte uppfylld.** Blått är mörkare och ligger 17 % längre från mitten än orange. Rutor med
  index 1 väger alltså tyngre än rutor med index 0 i randdiagrammen (`divergingFill`, `web/src/lib/design/state.ts`).
  I mörkt läge är paret balanserat. **Förslag (W2, `web/src/lib/design/tokens.ts:54`):** byt `brk` i ljust läge från
  `#d9661f` till `#c25c00` (L 0,59, nyans 51°, kontrast 4,24, avstånd till mitten 39,2 mot blåtts 41,2, CVD-ΔE ≥ 26,6).
- **Det mörka orange drar mot rött.** `#d95926` har nyansen 40°, och på skärmbilderna i mörkt läge ser enstaka rutor
  (till exempel G1 i randdiagrammet) röda ut. **Förslag (`tokens.ts:71`):** byt till `#d46600` (nyans 51°, L 0,632,
  kontrast 4,73, CVD-ΔE ≥ 27,5). Båda bytena ändrar visionens tabell 4.4 och kräver att `tokens.test.ts` och visionen
  uppdateras i samma ändring.
- **Ser stabil ut som "dåligt"?** Nej. Grått läses som "ingenting" eller "inaktivt", inte som negativt. Två problem
  finns ändå. (1) Stabil (`#8a8880`) och naiv baslinje (`#898781`) är samma färg (ΔE 0,4), så samma grå betyder två
  saker. Baslinjen kan lika gärna ritas streckad i bläckfärgen. (2) I mörkt läge ligger stabil nära "för få serier"
  (ΔE 3,6). Där skiljer bara glyfen (● mot ○). Det räcker för tillgängligheten men inte för helhetsintrycket.
- **Färg på index som inte har något tillstånd.** G1 har "för få serier" (2 serier), men randdiagrammet färgar G1:s
  index orange 2026 (`StripeCell.svelte:37`, `divergingFill(value)` utan hänsyn till tillståndet). På startsidan står
  "○ för få serier" i kedjan, medan randdiagrammet säger "fler minskar takten". **Förslag (W2/W5):** rita index med
  färre än `MIN_SERIES` serier med 45°-mönstret (visionen 4.4) eller med låg opacitet. Detsamma gäller minikartan
  (`Minimap.svelte:44`).
- I ljust läge ligger mittfärgen (`#f0efec`, index 0,5) nära "inget index" (vit ruta med ram). Det går att skilja dem
  åt, men bara på ramen. 45°-mönstret för "inget index" vore tydligare.

## 3. Urvalsregeln för månadens berättelse (W13)

**Spegling på riktig data.** Jag kapslade in `story.select` under en hel riktig paketbyggnad och körde varje månad två
gånger: på sina egna indata och på speglade indata. Speglingen vänder tillstånden (accelererar ↔ bromsar in), sätter
index till 1 − index, byter `n_up` och `n_down`, sätter percentiler till 100 − p, vänder riktning och förändring i
takt, och byter regimskiften och P till 1 − P.

| Resultat (46 månader) | |
|---|---|
| Samma kort-id i samma ordning | 46/46 ✓ |
| Varje riktning omvänd (null förblir null) | 46/46 ✓ |
| K0: högre och lägre byter plats, samma ligger kvar | 46/46 ✓ |
| `qualified` och `omitted` lika per typ | 46/46 ✓ |

Regeln är alltså symmetrisk i praktiken, inte bara på papperet. Avrundningen till två decimaler i K0 och
avrundningen till sex decimaler i ordningsnyckeln gav ingen skillnad.

**Var kommer övervikten uppåt ifrån?**

| | Uppfyllde villkoret (utan tak) | Visades | Ströks av taket |
|---|---|---|---|
| K1 upp / ned / utan riktning | 43 / 37 / 2 | 43 / 37 / 2 | 0 |
| K5 upp / ned | **69 / 42** | 54 / 37 | **15 / 5** |
| K6 upp / ned | 8 / 2 | 8 / 2 | 0 |

Taket förstärker inte övervikten: den är 62 % uppåt före taket och 59 % efter. Övervikten kommer från data, och
uppströms är måtten symmetriska. Percentilen räknar lika värden till hälften, så p(−x) = 100 − p(x) exakt. Dödbandet
är ±0,25 SD, och gränserna 0,33 och 0,67 ligger symmetriskt kring 0,5 (2/3 och 1/3 blir båda stabila). **Ett
undantag finns, utanför W13:** fördubblings- och halveringstid räknas på en löpande maxfront. Om fronten står helt
still i 24 månader blir lutningen 0, och då blir tiden NaN (`measures.rolling_time`). Serien faller ur indexet i stället
för att räknas som att den bromsar in. Det är en asymmetri i registrets avsnitt 1 för G1 och G2. I dag syns den inte,
eftersom G1 och G2 har för få serier, men den bör prövas i en registergranskning.

**`capex_ocf_hyp4` som K5 och `x_capex_ocf` som K6 samma månad.** Detta hände i oktober 2026: kort 3 (K5, percentil
98,4) och kort 6 (K6, percentil 98,5). Enligt registret (rad 469) är `x_capex_ocf` definierad som "befintlig
`capex_ocf_hyp4`". Det är samma storhet, mätt en gång som förändring i takt och en gång som takt. Läsaren ser två blå
kort om samma kvot, och tillsammans med `x_capex_cloud` är tre av sex kort den månaden capex-kvoter i samma riktning.
Det är ingen asymmetri i regeln (samma sak skulle hända nedåt), men samma signal räknas två gånger och väger därmed
dubbelt.

**K5 når taket.** 20 kort ströks över 46 månader, och det är bara K5 som någonsin når sitt tak. Med cirka 60 räknade
kärnserier ligger i snitt cirka 6 i en ytterzon (≤ 5 eller ≥ 95) av ren slump, om percentilerna är jämnt fördelade.
Kravet på att serien inte låg i samma zon månaden innan sänker antalet. I genomsnitt uppfyllde 2,5 serier per månad
K5:s villkor (högst 6). Det är samma storleksordning som slumpen ger. Bara den första månaden (som saknar jämförelse)
fick K9, så sidan säger i praktiken aldrig "inget hände". Det väljer ingen riktning, men det överdriver hur mycket som
händer. G9, med 3 serier, står för 20 av de 82 K1-korten (12 tillståndsbyten på 24 månader). Regeln är symmetrisk, men
med så få serier är bytena mest brus.

**Rekommenderade regeländringar.** De gäller först när de har registrerats som ett nytt daterat avsnitt i
måttregistret, och då gäller de för alla månader:

1. **R-W3a, dubbletter:** en avstämning (K6) vars bas är en räknad kärnserie (registrets tabell över avstämningar,
   kolumnen "befintlig …") och vars kärnserie redan har ett K5-kort samma månad blir inget eget kort. K5-kortet får i
   stället en mening om avstämningen. Antalet räknas under "ströks som dubblett" i Om urvalet.
2. **R-W3b, slumpnivå:** Om urvalet anger för K5 och K6 hur många utslag som väntas av slumpen: "Med N räknade serier
   ligger i snitt N/10 i en ytterzon av en slump." Inga kort väljs bort på grund av det, men läsaren ser
   storleksordningen. Detta följer regel 5 i CLAUDE.md (säg när något kan vara slump).
3. **R-W3c, de som ströks:** visa de kort som ströks av taket med namn och riktning (▲/▼) i Om urvalet, utan figur, i
   stället för bara antalet. Läsaren kan då se att taket inte valde riktning. Ordningen och taket ändras inte.
4. *Övervägt men inte rekommenderat:* att höja K5:s tak till 4. Det minskar inte slumpbruset och ger fler kort.

## 4. Fem-sekunderstest

Jag tittade på första skärmen (1280×900 och 375×812) i båda lägena.

**Startsidan.** Det som uppfattas först är rubriken "Av 7 grenar med tillstånd: 4 accelererar, 3 är stabila och ingen
bromsar in." Därefter kommer raden med fyra räknare (▲ 4, ● 3, ▼ 0, ○ 2) och kedjan med mest blå trianglar. Det är
neutralt: räkneord och registrets ord, och nollan för "bromsar in" står lika stor som de andra. Det är sant enligt
posten, och de två grenarna utan tillstånd står med ("2 utan tillstånd"). **Brist:** att detta är *rekonstruerad*
historik syns bara i ett litet streckat grått märke på raden ovanför rubriken (`web/src/lib/start/Hero.svelte:21–25`).
Rubriken i 40 px ser exakt lika säker ut som en skarp ögonblicksbild kommer att göra. **Förslag:** sätt statusen i
själva rubrikraden när posten är rekonstruerad, till exempel som kicker i ink-färg: "Rekonstruerat läge oktober
2026 · skarpt från 30 nov 2026". Ett annat sätt är att märket får samma storlek och vikt som "Läget oktober 2026".

**Grensidan (G6).** Det som uppfattas först är "▲ accelererar" och talet "0,72" i cirka 60 px. Det är neutralt och
sant. Ett stort ensamt tal kan dock läsas som ett betyg. Underrubriken "diffusionsindex, 0–1" hjälper bara den som
redan kan ordet. Texten "Förra månaden (sep 2026): 0,72, förändring ±0,00" är bra. Indexdiagrammet visar rekonstruerat
som streckad linje och skarpt som ring. Det är den tydligaste statusmarkeringen på sidan.

**Månadssidan (oktober 2026).** Det som uppfattas först är "Oktober 2026" och meningen "6 kort enligt den
förregistrerade regeln (1 tillståndsskifte, 3 kärnserier i extrem percentil, 2 avstämningar i extrem percentil)."
Meningen är neutral men säger inget om vad som hände. Läsaren får veta hur många kort det blev, inte vad korten säger.
Det första kortet (K0, Läget) är bra: kortets rubrik säger "(rekonstruerat)". I marginalen syns orange och blå glyfer
(⇄ ◉ ⚖). Färgen på K6:s ⚖ (blå, "mer takt") ger avstämningar en riktning som registret uttryckligen säger att de
saknar (A5: "räknas inte i grenarnas diffusionsindex"). **Förslag (W13, `StoryView.svelte:41` `dirColor`, och
`story.py:358`):** visa K6 i bläckfärg med ▲/▼ och etiketten "kvotens takt högt/lågt i egen historik", så att blått och
orange bara betyder riktningen i ett index.

**Uppfattas rekonstruerat som lika säkert som skarpt?** Ja, på start- och månadssidan. På grensidan och i
randdiagrammen nej, tack vare streckad linje och "Alla månader är rekonstruerade". Eftersom hela historiken fram till
2026-11-30 är rekonstruerad är detta den viktigaste ändringen före byte av huvudsida.

## 5. Läsbarhet för en kunnig men icke-specialiserad läsare

Förekomster per sida (riktigt paket):

| Term | Start | Gren | Månad | Metod | N2 | Regim | Förklaras där den står? |
|---|---|---|---|---|---|---|---|
| diffusionsindex | 1 | 1 | 4 | – | – | – | Gren: ja (formeln). Start och månad: nej |
| dödband | – | 11 | – | 14 | – | – | Metod: ja (interaktivt). Gren: nej ("mätaren … mot seriens dödband") |
| log×100 per år | – | 27 | 4 | 4 | – | – | Nej. Månad ger "(≈ +106 %)" men grenens kort gör det inte |
| pe per år | – | – | 1 | – | – | – | Nej (förkortning för procentenheter) |
| PIT | – | – | – | 10 | 6 | – | Delvis ("var i fördelningen utfallet hamnade") |
| CRPS | – | – | – | 2 | 2 | – | Delvis ("lägre är skarpare och träffsäkrare"). Aldrig utskrivet |
| Holm 50/80/95 | – | – | – | 9 | 3 | – | Nej, kolumner med p-värden utan rubrikförklaring |
| slumpband | 2 | – | – | 5 | 1 | – | Ja ("grått: 90 % slumpband") |
| MSIH(2), BOCPD, G-D, Markov-switching | – | – | – | – | – | 6 | Nej |
| A5, C4, B0–B3 | 3 | – | 2 | 48 | 56 | 7 | B-koderna har etiketter. A5 och C4 gör det inte |
| 94:e pct | – | 9 | – | – | – | – | Förkortning. Talet bredvid är takten, men pct gäller takten, inte riktningen |

**Konkreta textändringar (beskrivs, ändras inte här):**

- `web/src/lib/start/Chain.svelte:60`: "linjen: diffusionsindex 24 månader" bör bli "linjen: andel serier som ökar
  takten (diffusionsindex), 24 månader".
- `web/src/routes/gren/[id]/+page.svelte:83`: "mätaren under visar förändringen i takt mot seriens dödband" bör bli
  "… mot seriens dödband (±0,25 standardavvikelser: inom bandet räknas takten som oförändrad)".
- `src/ai_tracker/letter.py:63` och `src/ai_tracker/state/measures.py:241`: enheterna "pe per år" och "log x100" bör
  bli "procentenheter per år" och "log×100 per år (≈ % per år)". Ändringen påverkar också månadsbrevet. Gör den i ett
  eget spår med brevets tester.
- `web/src/lib/flow/SeriesMultiple.svelte:86` och `web/src/lib/regime/Components.svelte:46`: "+32,9 · 94:e pct" bredvid
  "▼ minskar takten" förvirrar: hög takt, men minskande. Skriv "takt +32,9 (94:e percentilen av egen historik)" och
  låt riktningsordet stå för sig.
- K5-rubriken "… förändringen i takt i percentil 98,4" (`story.py:330`, K5-kortets `title`) bör kompletteras med en mening
  i klartext först i texten, till exempel "Takten ökar mer än den gjort i 98 % av seriens historik". Det är en
  textändring utan ny beräkning, men eftersom korttexten är registrerad ska den föras in tillsammans med R-W3a–c.
- Prognossidorna: CRPS kan förklaras som "genomsnittligt avstånd mellan prognosfördelningen och utfallet, i målets
  enhet", och Holm-kolumnerna som "p-värde för täckningen, justerat för många jämförelser". Regimsidan: lägg en
  mening före akronymerna om att modellen uppskattar sannolikheten att blocket ligger i en period med lägre takt.
- Seriesidor och G5: "hyperscalers" bör bli "de fyra största molnbolagen".

## Ändrat i den här granskningen

| Fil | Ändring | Test |
|---|---|---|
| `src/ai_tracker/site_bundle/story.py` | ett zonkort anger bara sin egen gräns | `tests/test_site_story.py::test_a_zone_card_names_only_its_own_bound` |
| `web-data-fixtures/story/*.json`, `manifest.json` | omgenererade (`python -m ai_tracker.site_bundle fixtures`) | `test_committed_fixtures_are_the_current_synthetic_bundle` |
| `web/src/lib/story/StoryView.svelte` | singular, jämförelsemånad på svenska, K1 som högre/lägre index | `web/src/lib/story/story.test.ts` ("StoryView texts (R-W3)") |
| `web/src/lib/regime/RegimeMeter.svelte`, `HoldoutStrip.svelte`, `web/src/routes/regim/+page.svelte` | "skifte till expansion" i stället för "tillbaka" | `web/tests/e2e/regime.spec.ts` |
| `web/src/lib/start/Changed.svelte` | båda regimtrösklarna i texten | smoke och axe |

Grindarna, körda på fixturbygget med `PW_PORT=4531`: svelte-check 0 fel och 0 varningar, vitest 372/372, bygget,
budget ok (71 sidor), externa värdar ok, Playwright 444/444. Pytest: `test_site_story`, `test_site_bundle`,
`test_web_regime_constants` och `test_letter` gav 52 gröna.
