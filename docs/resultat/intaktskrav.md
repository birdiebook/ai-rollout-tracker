# Resultat: intäktskrav (avskrivningar och kapitalkostnad mot intäkter), spår P2b

Körd 2026-11-24 enligt `docs/mattregister.md`, posten "2026-11-24 – A5: intäktskrav (avskrivningar och kapitalkostnad
mot intäkter)". Kod: `src/ai_tracker/series/avstamning.py` (definitioner och versionsregel),
`src/ai_tracker/state/register.py` (`RECONCILIATIONS`) och `src/ai_tracker/site/flow.py` (korta etiketter). Tester:
`tests/test_avstamning.py` (fixturer, inget nät). Komponenterna kommer från spår P1 (`docs/kallor/sec_avskrivningar.md`).
Bygg: `python -m ai_tracker.observations x_dep_rev x_capcost_rev_r08 x_capcost_rev_r12 x_dep_capex x_dep_rev_aws`
efter komponenterna.

Dokumentet beskriver. Det säger inget om huruvida investeringarna betalar sig, och kvoterna har ingen etikett.

**Omräknat efter rättningen X11 (2026-11-24).** P2b byggdes på P1 före X11. Siffrorna nedan är räknade om med den
sammanslagna koden i körning 13, på basen efter datamergen, per 2026-11-24. Avsnittet "Omräkning efter X11" säger vad
som ändrades.

## Omräkning efter X11

- **Skäl.** Microsoft räknade om 2024Q3 och 2025Q3 genom sexmånaderstalet i 10-Q:n 2026-01-28 (granskning R14, R-1).
  Efter X11 är det en egen version från 2026-01-28. I `dep_hyp4` blev 2024Q3 28 170 MUSD i stället för 28 837 (från
  2026-01-28), och 2025Q3 blev 35 517 redan från 2026-01-28 i stället för från 2026-10-28.
- **Första versionen av varje period är oförändrad.** Det som ändras är de senare versionerna för perioderna
  2024Q3–2025Q4, och antalet versioner: 25 i stället för 28 för `x_dep_rev` och kapitalkostnaden, och 32 i stället för
  35 för `x_dep_capex`. AWS-kvoten ändras inte.
- **Senaste versionen ändras för 2024Q3–2025Q2:**

| Period | `known_from` | `x_dep_rev` | `x_capcost_rev_r08` | `x_capcost_rev_r12` | `x_dep_capex` |
|---|---|---|---|---|---|
| 2024Q3 | 2026-01-28 | 7,69 → 7,64 | 11,57 → 11,52 | 13,50 → 13,46 | 52,96 → 52,63 |
| 2024Q4 | 2026-01-28 | 7,71 → 7,66 | 11,74 → 11,69 | 13,75 → 13,71 | 47,76 → 47,47 |
| 2025Q1 | 2026-04-29 | 7,93 → 7,88 | 12,20 → 12,16 | 14,34 → 14,29 | 44,91 → 44,65 |
| 2025Q2 | 2026-07-29 | 8,19 → 8,15 | 12,74 → 12,69 | 15,01 → 14,96 | 42,24 → 42,01 |

- **2025Q3 och 2025Q4** har samma värde i senaste versionen som förut, men det är känt från 2026-07-29 i stället för
  2026-10-28. Före X11 kom Microsofts omräkning av 2025Q3 först med 10-Q:n för 2026Q3.
- **Måtten per 2026-11-24:** nivån och takten 2026Q3 är oförändrade. Förändringen i takt och överraskningen ändras,
  eftersom takten 2026Q1 jämför med 2025Q1, som nu är lägre: `x_dep_rev` +0,0 (förut +0,6), `x_capcost_rev_r08` +1,8
  (+2,2), `x_capcost_rev_r12` +2,2 (+2,5) och `x_dep_capex` −8,0 (−7,4). Percentilerna för takten är desamma.

## Ordning och vad som setts

- Registerposten committades först (`ae0724b`, med ett tillägg om vad som setts i `082f971`). Koden och testerna kom i
  `477a48a`. Först därefter hämtades komponenterna och kvoterna räknades.
- Före registerposten hade spåret bara sett P1:s resultat: antal kvartal och första och sista period per serie, och två
  enskilda belopp från P1:s handkontroller. Valet av `dep_hyp4` framför `dep_ppe_hyp4` bygger på täckningen (15 mot 9
  kvartal), inte på värden.
- Storleken på Microsofts omräkning (avsnittet om förbehåll) och känsligheten med `dep_ppe_hyp4` räknades efter
  registreringen. Känsligheten och bolagstabellen var registrerade som beskrivande tillägg.
- Data: komponenterna hämtades till spårets egen tabell (known_from = inlämningsdatum), när den delade basen ännu var
  tom. Basen fick sedan en datasnapshot. Dess rader för `capex_hyp4` och `rev_*` är identiska med spårets (samma
  perioder, datum och värden), så siffrorna gäller också för basen ∪ spåret. Måtten räknades med
  `state.branch.reconciliations` per 2026-11-24.
- Fel i den delade vyn, rättat i spåret: `observations.combine` jämförde nycklar som text, och `known_from` skrevs då
  med klockslag i basen (där dagliga serier har klockslag) men utan i spåret. Spårets rader ersatte därför aldrig
  basens, och vyn fick 477 dubblerade rader (`capex_hyp4` och `rev_*`). Nu jämförs tidsstämplar i ett fast format.
  Dubbletterna hade samma värden, och alla fem kvoterna och deras mått blev identiska när de räknades om på den rättade
  vyn.

## Definitioner

Alla är kvartalsserier ×100, summerade över periodens kvartal och de tre föregående. Hyp4 är MSFT, GOOGL, AMZN och META.

| Nyckel | Definition | Led | Enhet |
|---|---|---|---|
| `x_dep_rev` | `dep_hyp4` / (`rev_msft` + `rev_googl` + `rev_amzn` + `rev_meta`) | L3–L5 | procent av intäkterna |
| `x_capcost_rev_r08` | (`dep_hyp4` + 0,08 × `ppe_net_hyp4` vid periodens slut) / samma intäkter | L3–L5 | procent av intäkterna |
| `x_capcost_rev_r12` | som ovan med 0,12 | L3–L5 | procent av intäkterna |
| `x_dep_capex` | `dep_hyp4` / `capex_hyp4` | L5 | procent av capex |
| `x_dep_rev_aws` | `dep_aws` / `rev_aws` | L3–L5 | procent av intäkterna |

- `ppe_net_hyp4` är en balans och summeras inte. Avkastningskravet r gäller per år, före skatt och på det bokförda
  nettot.
- Versioner: en version finns först när alla par (serie, kvartal) är kända på dagen. `known_from` är den senaste
  komponentens datum, och en ny rad skrivs när värdet ändras.
- Mått: takt = årsförändring i log(kvot) ×100. Förändring i takt = takten nu minus takten två kvartal tidigare.
  Percentiler kräver minst 8 värden. Allt räknas `as_of` 2026-11-24.
- Kvoterna räknas inte i något grenindex. De står i gruppen "Avstämningar" i ögonblicksbilden, månadsbrevet och
  flödesvyn, från den första skarpa ögonblicksbilden 2026-11-30.

## Senaste värden

Senaste version känd 2026-11-24. "Versioner" räknar alla rader i serien.

| Nyckel | Period | Nivå | `known_from` | Perioder | Första period | Första `known_from` | Versioner |
|---|---|---|---|---|---|---|---|
| `x_dep_rev` | 2026Q3 | 9,39 | 2026-10-30 | 12 | 2023Q4 | 2024-10-30 | 25 |
| `x_capcost_rev_r08` | 2026Q3 | 15,78 | 2026-10-30 | 12 | 2023Q4 | 2024-10-30 | 25 |
| `x_capcost_rev_r12` | 2026Q3 | 18,97 | 2026-10-30 | 12 | 2023Q4 | 2024-10-30 | 25 |
| `x_dep_capex` | 2026Q3 | 28,34 | 2026-10-30 | 12 | 2023Q4 | 2024-10-30 | 32 |
| `x_dep_rev_aws` | 2026Q3 | 19,30 | 2026-10-30 | 8 | 2024Q4 | 2025-10-31 | 8 |

Komponenterna för 2026Q3, i MUSD: avskrivningar 174 399 (fyra kvartal), intäkter 1 856 604 (fyra kvartal),
anläggningstillgångar netto 1 481 755 (balans 2026Q3) och capex 615 355 (fyra kvartal).

Historiken börjar sent. Alphabets definition gäller från 2023, och dess kvartal för 2023 blev kända som
jämförelsetal i 10-Q:erna 2024, de sista (2023Q3 och 2023Q4) 2024-10-30. AWS-segmentets avskrivningar finns per
kvartal från 2024, och 2024Q3 och 2024Q4 blev kända 2025-10-31.

## A5-måtten per 2026-11-24

| Nyckel | Nivå | Takt | Förändring i takt | Percentil, takt | n takt / n förändring | Överraskning (B1-drift) |
|---|---|---|---|---|---|---|
| `x_dep_rev` | 9,39 | +12,2 | +0,0 | 94 | 8 / 6 | +0,7 |
| `x_capcost_rev_r08` | 15,78 | +18,3 | +1,8 | 94 | 8 / 6 | +1,4 |
| `x_capcost_rev_r12` | 18,97 | +19,9 | +2,2 | 94 | 8 / 6 | +1,5 |
| `x_dep_capex` | 28,34 | −32,8 | −8,0 | 6 | 8 / 6 | −4,0 |
| `x_dep_rev_aws` | 19,30 | +22,8 | −6,1 | – | 4 / 2 | −2,7 |

Takten är i log ×100 per år. Ingen serie har percentil för förändringen i takt (färre än 8 värden), och AWS-kvoten
har ingen percentil för takten heller.

Nivåerna i den senaste versionen:

| Period | `x_dep_rev` | `x_capcost_rev_r08` | `x_capcost_rev_r12` | `x_dep_capex` | `x_dep_rev_aws` |
|---|---|---|---|---|---|
| 2023Q4 | 7,16 | 10,68 | 12,44 | 60,51 | – |
| 2024Q1 | 7,28 | 10,84 | 12,62 | 59,49 | – |
| 2024Q2 | 7,43 | 11,11 | 12,95 | 55,70 | – |
| 2024Q3 | 7,64 | 11,52 | 13,46 | 52,63 | – |
| 2024Q4 | 7,66 | 11,69 | 13,71 | 47,47 | 12,38 |
| 2025Q1 | 7,88 | 12,16 | 14,29 | 44,65 | 13,30 |
| 2025Q2 | 8,15 | 12,69 | 14,96 | 42,01 | 14,30 |
| 2025Q3 | 8,32 | 13,13 | 15,54 | 39,35 | 15,37 |
| 2025Q4 | 8,60 | 13,73 | 16,29 | 37,20 | 16,66 |
| 2026Q1 | 8,90 | 14,34 | 17,07 | 34,83 | 17,76 |
| 2026Q2 | 9,08 | 14,94 | 17,87 | 31,66 | 18,58 |
| 2026Q3 | 9,39 | 15,78 | 18,97 | 28,34 | 19,30 |

Uppdelat i komponenternas takt för 2026Q3 (log ×100 per år): avskrivningar över fyra kvartal +29,6, intäkter +17,4,
nettot av anläggningstillgångar +45,6 och capex +62,4. Kapitalkostnaden växer snabbare än avskrivningskvoten eftersom
nettot växer snabbare än avskrivningarna. Avskrivningarna växer långsammare än capex, och därför faller `x_dep_capex`.

## Beskrivande tillägg (registrerade, inga serier)

**(a) Känslighet: avskrivningar på anläggningstillgångar (`dep_ppe_hyp4`) i stället för `dep_hyp4`.** Samma nämnare
och samma versionsregel. Serien finns från 2025Q2 (första version 2026-04-29), så takten finns bara för två perioder.

| Period | `x_dep_rev` | Med `dep_ppe_hyp4` |
|---|---|---|
| 2025Q2 | 8,15 | 6,13 |
| 2025Q3 | 8,32 | 6,38 |
| 2025Q4 | 8,60 | 6,65 |
| 2026Q1 | 8,90 | 7,00 |
| 2026Q2 | 9,08 | 7,34 |
| 2026Q3 | 9,39 | 7,75 |

Takten 2026Q3 är +19,4 med `dep_ppe_hyp4` mot +12,2 med `dep_hyp4`. Skillnaden är stor. Den del av `dep_hyp4` som
inte är avskrivningar på anläggningstillgångar (Amazons operationella leasingtillgångar och aktiverade innehåll,
Microsofts "other" och amortering på immateriella tillgångar) växte bara +1,2 log ×100 från 2025Q3 till 2026Q3, och
dess andel föll från 25 % (2025Q2) till 18 % (2026Q3). Den registrerade serien underskattar alltså takten i avskrivningarna på den fysiska kapaciteten.
Med två värden är det inget mått, bara en beskrivning.

**(b) Per bolag, 2026Q3, samma versionsregel.** Kvoterna ×100 över fyra kvartal. Takten gäller avskrivningskvoten.

| Bolag | Avskrivningar / intäkter | Takt | + 8 % på nettot | + 12 % på nettot | `known_from` | Kvartal med kvot |
|---|---|---|---|---|---|---|
| MSFT | 12,16 | +14,6 | 20,17 | 24,17 | 2026-10-28 | 62 |
| GOOGL | 5,94 | +17,1 | 12,27 | 15,44 | 2026-10-29 | 12 |
| AMZN | 9,95 | +10,5 | 15,06 | 17,61 | 2026-10-30 | 28 |
| META | 10,31 | +10,1 | 18,70 | 22,89 | 2026-10-22 | 58 |
| ORCL | 15,16 | +31,7 | 29,41 | 36,53 | 2026-09-11 | 70 |
| CRWV | 53,10 | +13,5 | 99,05 | 122,02 | 2026-11-12 | 8 |

Bolagens definitioner skiljer sig (`docs/kallor/sec_avskrivningar.md`). Alphabets serie är bara avskrivningar på
anläggningstillgångar, medan de andra innehåller mer. Oracles kvartal (jun–aug) är märkt 2026Q3 med mittpunktsregeln.
CoreWeaves netto finns från 2024Q4.

## Förbehåll

- **Alla anläggningstillgångar, inte bara AI.** Avskrivningar och netto omfattar kontor, lager, logistik, nät och
  datacenter. Totala intäkter innehåller också reklam, handel, mjukvara och annat utan AI.
- **Nettot innehåller normalt tillgångar som ännu inte skrivs av,** till exempel pågående byggen och mark. De höjer
  kapitalkostnaden men inte avskrivningarna. Andelen är inte kontrollerad i detta spår.
- **Finansiell leasing** ingår i nettot hos alla fyra (P1:s belägg per bolag). Avskrivningen på leasade tillgångar
  ligger normalt i avskrivningsraden, men det är inte kontrollerat per bolag i detta spår. Capex är bara köp mot
  kontant betalning. Täljaren i `x_dep_capex` omfattar alltså tillgångar som inte finns i nämnaren.
- **r är ett antagande.** 8 % och 12 % är ett registrerat intervall, ingen skattning av bolagens kapitalkostnad. Kvoten
  är linjär i r, och takten beror på r: ju högre r, desto mer väger nettot, som växer snabbare.
- **Microsofts definitionsbrott.** Microsofts rad räknades om 2026-01-28 och framåt: "other" krympte, och omräkningen
  gällde kvartal från 2024Q3. 2024Q3 räknades om genom sexmånaderstalet (6 716 mot 7 383 MUSD, R14 R-3). Bara
  kvartalen till och med 2024Q2 (Microsofts FY2024) ligger kvar på den gamla basen. I `dep_hyp4` sänkte omräkningen
  2024Q3 med 2,3 % (28 837 till 28 170 MUSD), 2024Q4 med 3,7 % (31 123 till 29 963 MUSD) och 2025Q3 med 12,2 %
  (40 431 till 35 517 MUSD), alla från 2026-01-28. I den senaste versionen har perioderna 2023Q4–2024Q2 bara gammal
  bas, 2024Q3–2025Q1 en blandning och perioderna från 2025Q2 bara ny bas.
  - Nivån och takten 2026Q3 jämför bara perioder på ny bas och påverkas inte.
  - Förändringen i takt använder takten 2026Q1, som jämför med 2025Q1, en period med ett kvartal på gammal bas
    (2024Q2). Om den gamla basen ligger högre (som 2024Q4) är takten 2026Q1 för låg och förändringen i takt för hög.
  - Percentilerna jämför med takter från 2024Q4–2026Q2 i samma (senaste) version, och alla utom 2026Q2 påverkas.
  Effekten räknas inte om, eftersom kvartalen till och med 2024Q2 inte går att ställa på den nya basen: Microsoft
  räknade inte om FY2024.
- **Olika definitioner i summan:** Amazons rad innehåller operationella leasingtillgångar och aktiverat innehåll,
  Metas amortering på immateriella tillgångar och Microsofts "other". Tillägg (a) visar att valet flyttar takten med
  cirka 7 enheter.
- **Korta serier.** 12 perioder, 8 takter och 6 förändringar i takt för hyp4-kvoterna, 8 perioder och 4 takter för AWS.
  En percentil på 94 av 8 värden betyder bara att takten är den högsta hittills. Det kan vara slump, och det kan bero på
  definitionsbrottet ovan.
- **Nyttjandeperioder** är ett redovisningsval. Förlängda eller förkortade nyttjandeperioder ändrar avskrivningarna
  utan att kapaciteten ändras. Spår P2a samlar bolagens ändringar med citat. Här justeras ingenting.
- **Kalender:** Microsofts räkenskapskvartal är kalenderkvartal. Oracles slutar en månad före kalenderkvartalet och
  ingår bara i bolagstabellen. Hyp4-bolagen har alla kalenderkvartal.

## Vad som inte är gjort

- Inget intäktskrav mot molnintäkter för hela hyp4, eftersom Meta saknar molnsegment. Bara AWS har både avskrivningar
  och intäkter per segment.
- Inga kvoter mot bolagens AI-nyckeltal (`kpi_*`): de är oregelbundna och inte jämförbara mellan bolag.
- Ingen bedömning av om kvoterna är höga eller låga. Måtten beskriver nivå, takt och förändring i takt.
