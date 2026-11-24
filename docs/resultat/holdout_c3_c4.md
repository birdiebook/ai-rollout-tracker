# Holdouten för C3 (DF) och C4 (regim)

Öppnad och körd en gång 2026-11-24 med `python -m ai_tracker.holdout`, enligt `docs/holdout_logg.md` (posterna
committade i `dac3271` före körningen, git-sha före öppningen `089f70a`, vakterna öppnade i `cba3162`). Ägarens
godkännande: `docs/beslutslogg.md` 2026-11-24. Specifikationerna är oförändrade: `docs/steg2/c3_spec.md` (`5431f41`)
och `docs/steg2/c4_spec.md` (`735dc64`). D2:s holdout är fortsatt stängd.

Körlogg: `experiments/runs/20261124T082422Z_holdout_c3_c4.csv`. Den är märkt `cba3162+dirty` eftersom
`docs/drift.md` var ändrad men inte committad under körningen. Koden var den i `cba3162`. Detaljer per rad
skrevs till `data/derived/holdout/` (committas inte). Väggtid 4 minuter, med cachade faktorer för
utvecklingsdagarna från en torrkörning som bara läste utvecklingsfönstret.

**Holdouten var delvis känd (F-E5).** Baslinjefelen för 2025-07–2026-10 var publicerade i `docs/resultat/n1.md`–`n4.md`
före öppningen. De bakåtfyllda serierna (`us_constr_datacenter`, importserierna, BEA, EIA före arkivet, npm, PyPI och
Wikipedia) har dagens vintage, med revideringar och säsongsfaktorer från tiden efter 2025-06. Det gäller både
faktorerna och BOCPD-serierna. Resultaten nedan är därför inte ett helt blint test.

**Kontroll:** på utvecklingsraderna gav körningen på hela tabellen exakt samma DF-fel som den registrerade
utvecklingskörningen (N1 8, N2 49 och N3 8 rader, största skillnad 0). C4:s utvecklingsfrekvenser blev exakt desamma
som i `docs/resultat/c4_utveckling.md`. Realtidsegenskapen håller alltså också på verklig data.

## C3: DF per mål

Holdout = prognosdagar från 2025-07-01 till dagen före målets första skarpa prognosdag (F-E1, F-E2), med utfall
(första versionen) kända vid körningen. Fel = 100 × (log prognos − log utfall). Negativ MAE-skillnad = DF bättre.

| Mål | Huvudmodell DF bygger på | n holdout | Perioder | MAE DF | MAE B0 | MAE B1 | MAE B2 | MAE B3 | Bias DF | Utfall |
|---|---|---|---|---|---|---|---|---|---|---|
| N1 capex | B1 | 6 | 2025Q2–2026Q3 | 5,61 | 17,21 | 5,99 | – | – | −2,89 | skugga (n < 8, inget test) |
| N2 TSMC | B2 | 17 | 2025-06–2026-10 | 6,65 | 10,05 | 9,56 | 6,45 | 5,37 | +3,04 | **skugga (regeln ej uppfylld)** |
| N3 Nvidia DC | B1 | 5 | 2025Q2–2026Q2 | 8,86 | 16,45 | 6,36 | – | – | −6,38 | skugga (n < 8, inget test) |
| N4 molnintäkter | B1 | 5 | 2025Q3–2026Q3 | 2,09 | 8,66 | 2,14 | – | – | −2,09 | skugga (n < 8, inget test) |

### N2: regeln (F-E6, F-B9, F-B10)

| Del | Värde |
|---|---|
| Jämförelsemodell (bästa av B0, B1, B2 på holdoutraderna) | B2, MAE 6,45 |
| DF − B2, medel av absolutfel | +0,21 (DF sämre) |
| DM-p (Newey–West, HLN) | 0,832 |
| MDE | 2,71 |
| Holm-p i {B3, DF}, B3:s p = 0,0294 från den registrerade körningen | 0,832 (B3: 0,059) |
| Holm-p < 0,10 | **nej** |
| Lägre MAE än B2 på holdouten | **nej** (6,65 mot 6,45) |
| Lägre MAE än B2 i utvecklingen | ja (6,33 mot 6,87, n = 49) |
| Slår nuvarande huvudmodell B3 (F-B10) | nej (holdout 6,65 mot 5,37; utveckling 6,33 mot 5,71) |

**Utfall, tillämpat mekaniskt:** DF klarar inte regeln för N2. Ingen befordran, inget villkorat resultat och ingen
granskning behövs. `n2.CHAMPION` är oförändrad (B3). DF går in som skugga.

Vad som syns: utvecklingens lilla fördel för DF mot B2 (−0,54, p 0,42) kom inte tillbaka på holdouten. DF har där
en positiv bias (+3,0) där B2 har −2,5. Korrektionen över- och underkompenserar alltså med ungefär lika mycket.
B3, som var godkänd före öppningen, har lägst MAE även på holdouten (5,37). Det är information, ingen ny prövning av
B3.

### N1, N3 och N4: beskrivande

Med n = 5–6 görs inget test (F-E6), vilket registret angav i förväg. Siffrorna avgör ingenting.

- **N1:** DF 5,61 mot B1 5,99 på 6 kvartal. Utvecklingen gick åt andra hållet (10,83 mot 8,04 på 8 kvartal). Det
  är förenligt med slump i båda riktningarna.
- **N3:** DF 8,86 mot B1 6,36. Utvecklingens fördel (15,4 mot 21,1, n = 8) kom inte tillbaka. Nvidias räkenskapskvartal
  aug–okt 2026 (prognosdag 2026-11-08) hör till holdouten enligt F-E2, men utfallet fanns inte i tabellen vid körningen.
  Med den raden blir n = 6, fortfarande under 8, så utfallet ändras inte. Raden kan redovisas beskrivande senare och
  räknas inte som en ny öppning.
- **N4:** DF och B1 är i stort sett lika (2,09 mot 2,14). Korrektionen är liten. Raden 2025Q2 (prognosdag
  2025-07-20) hade färre än 12 träningsrader och saknar DF.

### DF som skugga i det skarpa registret

DF skrivs från och med nu som skugga i de skarpa filerna för N1–N4: `variants.DF` och blocket `df` (huvudmodell,
r̂, koefficienter, antal träningsrader och faktorförändringarna, eller orsaken till att DF saknas). Scorecarden och
sidan visar DF bland skuggorna. Det skarpa registret utvärderas med samma regel när målet har minst 8 skarpa
kvartal (24 månader för N2), enligt F-E6. Kontroll på verklig data: den skarpa beräkningen gav samma r̂ och samma
antal träningsrader som holdoutens rad för N2 2026-10, N1 2026Q3 och N4 2026Q3.

## C4: regim och strukturbrott (F-D6)

Beräkningsdagar 2025-07-31–2026-10-31 (16 månadsslut). Realtidsföljden är beräknad från 2012-01-31, så tillstånd och
brottsregel bärs över från utvecklingen. C4 är beskrivande och befordras inte.

### (a) Frekvens

| Block | Dagar med P | Skiften till inbromsning | Tillbaka till expansion | Månader expansion / inbromsning |
|---|---|---|---|---|
| capex och leverantörsled | 16 | 0 | 0 | 16 / 0 |
| efterfrågan | 16 | 0 | 1 (2025-12) | 11 / 5 |

P(inbromsning) per månad:

- **capex:** 0,45 (2025-07), 0,04, 0,23, 0,03, 0,04 och därefter ≤ 0,011 till 2026-10. Hela holdouten rapporteras
  som expansion. Det fortsätter skiftet till expansion 2025-04 i utvecklingen.
- **efterfrågan:** 1,00 för 2025-07–2025-10, sedan 0,003 (2025-11), 0,002 (2025-12) och ≤ 0,003 därefter. Rapporterad
  inbromsning till och med 2025-11 och expansion från 2025-12 (regeln om två månader i rad). Under juli–oktober 2025
  lade modellen den höga regimen (μ cirka 8–10) på ett fåtal tidiga månader. Från november skattas regimerna om så
  att de senaste månaderna hamnar i den högre regimen. Det är den instabilitet som `c4_utveckling.md` beskrev.

**BOCPD:** 921 serie-dagar med värde (60 serier), 2 rapporterade brott, 0,22 per 100 serie-dagar (utvecklingen:
0,29).

| Beräkningsdag | Gren | Serie | Senaste period | P(r_T ≤ 2) |
|---|---|---|---|---|
| 2025-10-31 | G4 | `rpo_hyp4` | 2025Q3 | 0,98 |
| 2026-04-30 | G4 | `rev_google_cloud` | 2026Q1 | 0,92 |

Inga brott i årsserierna (PJM) under holdouten.

### (b) Omklassning mot det utjämnade tillståndet från banan på 2026-10-31

| Block | Dagar | Andel där realtid ≠ utjämnat | Månader inbromsning, realtid / utjämnat |
|---|---|---|---|
| capex | 16 | 0,00 | 0 / 0 |
| efterfrågan | 16 | 0,25 | 5 / 1 |

För efterfrågan klassar den utjämnade skattningen bara en av holdoutens månader som inbromsning, mot fem i realtid. De
fyra månaderna juli–oktober 2025 byts alltså ut i efterhand. Utvecklingen hade 0,21 (capex) och 0,18 (efterfrågan).

### (c) Samband med huvudmodellernas absoluta fel (bara information)

P(inbromsning) på den senaste beräkningsdagen ≤ prognosdagen, prognosdagar i holdouten (F-E2).

| Mål (huvudmodell) | Block | n | ρ |
|---|---|---|---|
| N1 (B1) | capex | 6 | −0,43 |
| N1 (B1) | efterfrågan | 6 | −0,20 |
| N2 (B3) | capex | 17 | 0,04 |
| N2 (B3) | efterfrågan | 17 | 0,06 |

Inget samband går att se. Med n = 6 är ±0,9 inom slumpens ram, och för N2 ligger båda nära 0. Capex-sannolikheten
var nästan konstant (nära 0) under holdouten, så rangordningen bygger på mycket små skillnader. Inget test görs.

### C4 i ögonblicksbilden

Från den första ögonblicksbilden efter öppningen (2026-11-30) innehåller `snapshots/<YYYY-MM>.json` sektionen
`regime` (samma schema som sidan och kvartalsrapporten läser): `spec_version` (`735dc64`), `ms` per block med
`p_slow` = P(inbromsning), rapporterat `state`, `shift` (sant den månad tillståndet byts), `n_months`, `reason` och
MS-parametrarna, och `bocpd` per räknad kärnserie med `p_recent` = P(r_T ≤ 2) och `break`. Sektionen är inte en del av grenarnas tillstånd och ändrar inget diffusionsindex (F-D5,
F-D8). Reglerna för skifte och brott kedjas på förra månadens sektion. Den första sektionen startar från den
rekonstruerade följden till och med 2026-10-31 och är märkt så. Kontroll: en sektion för 2026-10-31 byggd på det
sättet gav samma P och samma tillstånd som holdoutkörningen.

## Brasklappar

- **Holdouten var delvis känd** (F-E5, se ovan).
- **Litet n:** N2 är det enda mål med ett test (n = 17, MDE 2,7). Skillnaden mot B2 (+0,21) är en tiondel av MDE.
- **C4 bygger på omskattade banor:** både faktorbanan och MS-modellen skattas om varje månad. Det förklarar
  efterfrågeblockets språng mellan oktober och november 2025 och omklassningen i (b).
- **Ett glapp:** N3 2026Q3 saknade utfall vid körningen (se ovan).
