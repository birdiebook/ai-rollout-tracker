# Steg 2: från nio grenar till en modell av AI-ekonomins flöde

Skriven 2026-11-23. Bygger på fas 0–6 (`docs/plan.md`). Planen är skriven för agentiskt utförande: varje
arbetsuppgift är ett **spår** med leverans, beroenden och granskning, grupperade i **vågor** som visar vad som kan
köras parallellt och vad som måste vänta.

## 1. Vision för steg 2

> **En löpande, tidsstämplad modell av hela AI-ekonomins flöde, från användning till el, med nowcast, prognos och
> sannolikhet för regimskifte i varje led.**

Fas 0–6 mäter nio grenar var för sig. Steg 2 kopplar ihop dem till en kedja där leden stäms av mot varandra. Kedjan
ska besvara tre frågor, var och en med ett mätbart svar:

| Fråga | Svar | Form |
|---|---|---|
| **Var står vi nu?** | Nowcast per led innan utfallet publiceras | Punkt och intervall, med scorecard |
| **Vart är vi på väg?** | Prognos 1–8 kvartal framåt | Sannolikhetsfördelning, kalibrering redovisas |
| **Har något fundamentalt ändrats?** | Glapp mellan led, regimsannolikhet, strukturbrott | Löpande sannolikhet, månadsvis |

### Vad världsklass betyder här (mätbart)

1. **Skarpt register:** minst fyra nowcastmål med tidsstämplade prognoser och offentlig scorecard.
2. **Bättre än bolagen själva:** huvudmodellerna slår bolagens guidance i det skarpa registret. Bolagens guidance är den starkaste kända baslinjen (N2: MAE 6,4 mot 10,5).
3. **Kalibrerade sannolikheter:** 80 %-intervallen träffar cirka 80 % av utfallen, och det redovisas öppet.
4. **Varje led har ärlig data:** alla grenar G1–G9 har ett tillstånd (minst tre räknade serier), och varje värde har ett `known_from`.
5. **Allt är spårbart:** förregistrering före analys, granskning av varje positivt resultat och ingenting som skrivs om i efterhand.

## 2. Flödesmodellen

### Leden

| Led | Innehåll | Grenar | Status i dag | Steg 2 lägger till |
|---|---|---|---|---|
| **L1 Förmåga och kostnad** | Vad modellerna klarar och vad det kostar | G1, G2 | Tunt (G1 och G2 utan tillstånd) | Egna prisögonblicksbilder, fler benchmarkkällor |
| **L2 Användning** | Hur mycket AI används, av vem | G3 | Tunt (BTOS-regimer, årsdata) | Utvecklaradoption, trafik, bolagens användningstal |
| **L3 Intäkter** | Pengar som kommer in | G4 | Segmentintäkter för moln och Nvidia | Labbens rapporterade intäkter, AI-nyckeltal ur bolagens rapporter |
| **L4 Kontrakterad efterfrågan** | Pengar som är utlovade men inte intäktsförda | ny | Saknas | **RPO och backlog** (MSFT, GOOGL, AMZN, ORCL, CoreWeave) |
| **L5 Investeringar och finansiering** | Capex, leasing, skuld | G5 | Capex, kassaflöde och finansiell leasing för de fyra största | Neoclouds, Oracle, skuld, leasingåtaganden som inte har börjat |
| **L6 Halvledare och minne** | Chips, minne, utrustning | G6 | TSMC, G.17, import | Nvidia, AMD, Broadcom, Micron, ASML |
| **L7 El och byggen** | Fysisk kapacitet | G7, G5 | EIA per delstat, Census datacenterbyggen | PJM:s kapacitetsauktioner och lastprognoser, ERCOT, EIA-930 per timme |
| **L8 Effekter** | Arbete och produktivitet | G8 | Indeed | Arbetsmarknad i exponerade yrken, produktivitet |
| **L9 Forskning och förväntningar** | Fältets tempo och omvärldens förväntningar | G9 | arXiv | Prognosmarknader och Metaculus som jämförelse |

### Avstämningar mellan leden

Härledda serier som gör kedjan granskningsbar. Var och en registreras före analys (spår A5):

| Avstämning | Definition (förenklad) | Vad ett glapp betyder |
|---|---|---|
| Capex mot molnintäkter | capex för de fyra största / (AWS + Google Cloud + Microsoft Cloud) | Investeringarna springer ifrån intäkterna |
| Täckning av kontrakterad efterfrågan | RPO / capex (rullande 4 kvartal) | Hur mycket framtida intäkter som är säkrade per investerad dollar |
| Nvidias andel av capex | Nvidias datacenterintäkter / capex för de fyra största | Var i kedjan pengarna landar |
| TSMC mot Nvidia | TSMC:s intäkter / Nvidias datacenterintäkter (med fördröjning) | Leverantörsledet före eller efter efterfrågan |
| El mot capex | Tillkommande last (PJM, ERCOT) / capex | Om fysisk kapacitet håller jämna steg |
| Finansieringsgrad | Capex / kassaflöde från rörelsen, och skuldfinansierad andel | Om investeringarna bärs av kassaflöde eller lån |

## 3. Arbetsprogram och spår

Storleken anges i agentspår enligt `docs/agentkalibrering.md`. "+R" betyder att ett oberoende granskningsspår krävs.

### Program I: Infrastruktur

| Spår | Leverans | Beror på | Storlek |
|---|---|---|---|
| **I1 Delad data** | En delad läskopia av observationstabellen för alla spår, en skrivkopia per spår och ett verktyg som slår ihop spårens data till `main` med datatester. Löser körning 1:s flaskhals | – | 1 |
| **I2 Låst holdout** | En mekanism som döljer holdout-perioden för metodutveckling (as_of-gräns plus test) och loggar varje gång den öppnas | C0 (policyn) | 1 |

### Program A: Flödesmodellen (värdekedjans data)

| Spår | Leverans | Beror på | Storlek |
|---|---|---|---|
| **A1 RPO och backlog** | `RevenueRemainingPerformanceObligation` (totalt, inom 12 månader och senare) ur XBRL för MSFT, GOOGL, AMZN, ORCL och CRWV. Versioner per inlämnat dokument | I1 | 1 +R |
| **A2a Halvledarbolag** | Intäkter per segment, capex och lager för NVDA (komplettering), AMD, AVGO, MRVL och MU ur XBRL. ASML ur 6-K | I1 | 2 |
| **A2b Neoclouds och Oracle** | Capex, skuld, RPO och leasing för CoreWeave, Oracle och Nebius (om de rapporterar till SEC) | I1 | 1 |
| **A3 Finansiering** | Skuldemissioner, räntekostnad och leasingskulder ur XBRL. Leasingåtaganden som inte har börjat (text i 10-Q-noter) extraheras med LLM | I1 | 1 +R |
| **A4 El och datacenter** | PJM:s kapacitetsauktioner (priser, volymer) och lastprognoser, ERCOT:s kö för stora laster, EIA-930 per timme för datacentertunga balansområden | I1, värdar | 2 |
| **A5 Avstämningar** | De härledda serierna i avsnitt 2 som registrerade serier, med `known_from` = den senaste av komponenterna | A1, A2a, A3, C0 | 1 |

### Program B: Efterfrågan (fyller L1–L3)

| Spår | Leverans | Beror på | Storlek |
|---|---|---|---|
| **B1 Utvecklaradoption** | Nedladdningar per vecka från npm (API från 2015) och PyPI (BigQuery-dataset från 2016, eller pypistats framåt) för AI-SDK:er (openai, anthropic, google-genai, langchain, transformers m.fl.). Snapshots av nedladdningar från Hugging Face | I1, beslut om BigQuery | 1 |
| **B2 GitHub** | Andel publika commits med AI-medförfattare (Copilot, Claude, Cursor m.fl.) och nya repon som använder AI-SDK:er, per vecka, ur GH Archive | I1, beslut om BigQuery | 2 |
| **B3 Trafik och uppmärksamhet** | Cloudflare Radar (AI-botar och AI-trafik), sidvisningar på Wikipedia för AI-produkter (öppet API, CC) | I1, nyckel | 1 |
| **B4 Bolagens AI-nyckeltal** | Extraktion ur pressmeddelanden, 10-Q och tillgängliga transkript: tokens per månad, användare av AI-tjänster, AI-intäkter i årstakt, Azure-tillväxt i procent och uttalanden om kapacitetsbrist. Varje värde har dokument, plats och hash, på samma sätt som E1 i fas 4 | I1 | 2 +R |
| **B5 Priser** | Egna veckovisa ögonblicksbilder av förstapartspriser (där villkoren tillåter), kopplade till förmåga. Gör G2 levande framåt | I1 | 1 |
| **B6 Labbens intäkter** | Register över intäkter som labben själva har uttalat (blogg, VD-uttalanden), med datum och källa. Märks "rapporterad", aldrig blandat med reviderade siffror | I1 | 1 +R |

### Program C: Metodmotor

| Spår | Leverans | Beror på | Storlek |
|---|---|---|---|
| **C0 Förregistrering för steg 2** | Nya mål (N3–N6), varianter per mål, holdout-policy, poängsättning (MAE för punkt, CRPS och täckning för intervall) och variantbudget. Skrivs av orkestreraren och granskas av ett separat spår innan något körs | – | 1 +R |
| **C1 Sannolikhetsprognoser** | Intervall och fördelningar för N1 och N2 (empiriska felfördelningar per modell), CRPS, PIT och täckning i backtest och scorecard | – | 1 |
| **C2 Guidance med systematisk avvikelse** | Hierarkisk Bayes över bolag för hur utfallet brukar landa mot guidance (TSMC i toppen av intervallet, Metas capex mot sitt intervall). Ny registrerad variant B3 för N1, N2 och N3 | C0 | 1 +R |
| **C3 Dynamisk faktormodell** | Faktormodell med blandade frekvenser och ojämn publicering. Faktorer per led ("capexcykel", "efterfrågan", "leverantörsled") och nowcast av mål med modellen som variant | C0, I2, våg 1-data | 2 +R |
| **C4 Regim och strukturbrott** | Markov-switching på faktorerna och takterna (sannolikhet för expansion eller inbromsning) plus Bayesiansk online-changepoint. Den registrerade metoden för strukturbrott (måttregistret, avsnitt 2) | C3, C0 | 1 +R |
| **C5 Nya nowcastmål** | N3 Nvidias datacenterintäkter (guidance finns i 8-K), N4 molnintäkter summerade (AWS + Google Cloud + Microsoft Cloud), N5 BTOS-andel, N6 RPO. Backtest i den gemensamma motorn och skarp drift | C0, A1, A2a | 2 |

### Program D: Framåtblick

| Spår | Leverans | Beror på | Storlek |
|---|---|---|---|
| **D1 Fleråriga planer** | Extraktion av fleråriga capex- och kapacitetsplaner (helårsplaner, flerårsåtaganden, löptidsprofilen för RPO) som framåtblickande serier med datum | I1 | 1 +R |
| **D2 Horisontprognoser 1–8 kvartal** | Sannolikhetsprognoser längs kedjan (RPO → molnintäkter → capex → halvledare), jämförda med naiva modeller och guidance | C0, C1, C3, A1 | 2 +R |
| **D3 Externa förväntningar** | Serier från Metaculus, Manifold, Polymarket och Kalshi för AI-frågor (öppna API:er), plus ett scenarioträd (bas, hög, låg) definierat av kedjans led | I1 | 1 |

### Program E: Produkt

| Spår | Leverans | Beror på | Storlek |
|---|---|---|---|
| **E1 Månadsbrev** | Automatiskt utkast på svenska till varje ögonblicksbild: vad som ändrade takt, nya utfall mot prognoser och nya datakällor. Committas med ögonblicksbilden | – | 1 |
| **E2 Flödesvy** | Kedjan som interaktiv vy på hemsidan, med nowcast och avstämning per led | A5, C3 | 1 |
| **E3 Kvartalsrapport** | "Läget i AI-utrullningen", en mall som fylls från register, scorecard och regimsannolikhet | C4, D2 | 1 |
| **E4 Sannolikheter på hemsidan** | Intervall, kalibrering och regimsannolikhet presenterade | C1, C4 | 1 |

### Granskningsspår

| Spår | Granskar | När |
|---|---|---|
| R3 | Datum och läckage för nya källor i A1–A4 | Efter våg 1 A |
| R4 | Datum och läckage för nya källor i B1–B6 och D1 | Efter våg 1 B |
| R5 | Extraktion i A3, B4, B6 och D1 (läser om källorna) | Efter respektive spår |
| R6 | Förregistreringen C0 (konsistens, budget, oklarheter) | Innan våg 2 |
| R7+ | Ett per positivt resultat (C2, C3, C4, C5, D2) | Innan befordran |

## 4. Vågor: parallellt och sekventiellt

```
Våg 0  ─┬─ I1 delad data ───────────────┐
        ├─ C0 förregistrering ── R6 ────┼────────────────────────────┐
        ├─ C1 sannolikhetsprognoser     │                            │
        ├─ E1 månadsbrev                │                            │
        └─ beslut (Johannes)            │                            │
                                        ▼                            ▼
Våg 1  ─┬─ A1 A2a A2b A3 A4 ── R3       (data, helt parallellt)      C2 guidance-avvikelse
        ├─ B1 B2 B3 B4 B5 B6 ── R4, R5                               (behöver bara C0)
        └─ D1 D3                                                     
                                        │
Våg 2  ─┬─ A5 avstämningar (A1, A2a, A3)
        ├─ C5 nya mål N3–N6 (A1, A2a)
        └─ C3 faktormodell (våg 1-data, I2) ── R7
                                        │
Våg 3  ─┬─ C4 regim och strukturbrott (C3) ── R7
        └─ D2 horisontprognoser (C1, C3, A1) ── R7
                                        │
Våg 4  ─── E2 flödesvy, E3 kvartalsrapport, E4 sannolikheter
```

| Våg | Spår (parallellt inom vågen) | Måste vänta på | Antal spår |
|---|---|---|---|
| **0** | I1, C0, C1, E1, beslut. Därefter R6 | – | 4 + 1 granskning |
| **1** | A1, A2a (2), A2b, A3, A4 (2), B1, B2 (2), B3, B4 (2), B5, B6, D1, D3, C2. Därefter R3, R4, R5 | I1, beslut, C0 (för C2) | 19 + 3–4 granskningar |
| **2** | A5, C5 (2), C3 (2). Därefter R7 | Data från våg 1, I2 | 5 + 1–2 granskningar |
| **3** | C4, D2 (2). Därefter R7 | C3 | 3 + 1–2 granskningar |
| **4** | E2, E3, E4 | A5, C4, D2 | 3 |

**Kritisk väg:** C0 → (A1, B1, B4) → C3 → C4 → E3/E4. En andra väg: A1 → C5 och D2.
För att korta den kritiska vägen kör C3 mot den data som finns efter våg 1 A och B1. Resten av våg 1 läggs till som
en senare registrerad variant, inte i efterhand.

**Inom en våg** ska spåren inte röra samma filer. Varje källa får egna moduler (`sources/<källa>.py`,
`series/<källa>.py`), och delade filer (`docs/beslutslogg.md`, `docs/agentkalibrering.md`) slås ihop av
orkestreraren.

## 5. Förregistreringsgrindar

Ingenting analyseras förrän grinden för det är passerad och committad.

| Grind | Innehåll | Före |
|---|---|---|
| **G-A Kärnserier** | Nya serier läggs till som kärnserier per gren eller led, valda på tillgång, historik och `known_from` | Första beräkningen av takt för nya serier |
| **G-B Mål och varianter** | N3–N6 med prognosdag, utfallsversion och baslinjer. Varianter per mål (budget: högst 3 nya per mål i steg 2). Holm-familj | C2, C3, C5 |
| **G-C Sannolikheter** | Intervallnivåer (50 %, 80 %, 95 %), CRPS, regel för kalibrering | C1 i skarp drift, D2 |
| **G-D Regim** | Modellval, tillstånd och tröskel för när regimsannolikheten rapporteras som skifte | C4 |
| **G-E Holdout** | Period och regel. Holdouten öppnas en gång per metodfamilj | C3, C4, D2 |

**Förslag till holdout (beslut för Johannes):** komplexa metoder (C3, C4, D2) utvecklas på data till och med
2025-06, och 2025-07–2026-10 är låst holdout som öppnas en gång per metodfamilj. Enkla registrerade varianter (C2,
C5) utvärderas som i dag över hela perioden med Holm-justering. Det skarpa registret från 2026-12 är det slutliga facit.

## 6. Kapacitet och körplan

- **Totalt:** cirka 34 spår plus 7–9 granskningar ≈ 42 spår.
- Enligt kalibreringen rymmer ett 5-timmarsfönster cirka 25–30 spår med 5–6 parallellt.
- **Körning 2:** våg 0 och våg 1 (cirka 27 spår inklusive granskning). **Körning 3:** våg 2–4 (cirka 15 spår).
- **Kalendertid** som inte kan köras snabbare: det första skarpa utfallet för N3 och N4 kommer i nästa kvartalsrapport,
  och kalibreringen av sannolikheter blir meningsfull först efter cirka 12 skarpa månader för N2.

## 7. Beslut för Johannes (före våg 1)

| Beslut | Rekommendation | Varför |
|---|---|---|
| BigQuery (PyPI och GH Archive) | **Ja.** Ett eget GCP-projekt med gratiskvot, nyckeln läggs i miljön | Ger B1 och B2 historik från 2016. Utan det blir historiken 180 dagar för PyPI och ingen för GitHub |
| Cloudflare Radar-nyckel | **Ja** (gratis) | Global AI-trafik per dag |
| Nya värdar | **Ja**, öppnas i ett svep: pjm.com, ercot.com, api.npmjs.org, pypistats.org, wikimedia.org, metaculus.com, manifold.markets, polymarket, kalshi, api.cloudflare.com, data.gharchive.org | Behövs för våg 1 |
| Holdout-policy | **Enligt avsnitt 5** | Skyddar mot överanpassning när antalet serier tredubblas |
| Betald transkriptkälla | **Nej just nu** | Pressmeddelanden och 10-Q räcker för det mesta. Omprövas om B4 visar stora luckor |
| Labbens rapporterade intäkter (B6) | **Ja, märkta som rapporterade** | Viktigt led som annars saknas helt |

## 8. Risker och hur planen hanterar dem

| Risk | Hantering |
|---|---|
| **Överanpassning** när serierna blir 300 och kvartalen är få | Förregistrering per grind, variantbudget, Holm, holdout för komplexa metoder, poolning över bolag |
| **Regimskifte efter 2023** gör historiken mindre relevant | Regimmodellen (C4) gör skiftet explicit. Delperioden från 2023 redovisas alltid |
| **Fel i extraktion** (B4, A3, B6, D1) | Dokument, plats och hash per värde, oberoende omläsning (R5) innan användning |
| **Villkor och betalväggar** | Licenskontroll per källa, `publish`-grind, BLOCKED dokumenteras i stället för att kringgås |
| **Driftsbrott** när källor ändrar format | Aktualitetstest, datatester som grind för publicering, larm i veckokörningen |
| **Kalendertid:** facit kommer långsamt | Skarpa prognoser startas så tidigt som möjligt för varje nytt mål |

## 9. Klart när (steg 2)

1. Flödesmodellen har minst åtta led med data, och avstämningarna i avsnitt 2 publiceras.
2. Alla grenar G1–G9 har ett tillstånd (minst tre räknade serier).
3. Minst fyra nowcastmål (N1–N4) har skarpa, tidsstämplade prognoser med intervall.
4. Regimsannolikheten publiceras månadsvis med förregistrerad metod.
5. Prognoser 1–8 kvartal finns för minst capex och molnintäkter, med redovisad kalibrering i backtest.
6. Månadsbrev varje månad och den första kvartalsrapporten är publicerade.
