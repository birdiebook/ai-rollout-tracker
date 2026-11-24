# Resultat: intäktskrav (avskrivningar och kapitalkostnad mot intäkter), spår P2b

Körd 2026-11-24 enligt `docs/mattregister.md`, posten "2026-11-24 – A5: intäktskrav (avskrivningar och kapitalkostnad
mot intäkter)". Kod: `src/ai_tracker/series/avstamning.py` (definitioner och versionsregel),
`src/ai_tracker/state/register.py` (`RECONCILIATIONS`) och `src/ai_tracker/site/flow.py` (korta etiketter). Tester:
`tests/test_avstamning.py` (fixturer, inget nät). Komponenterna kommer från spår P1 (`docs/kallor/sec_avskrivningar.md`).
Bygg: `python -m ai_tracker.observations x_dep_rev x_capcost_rev_r08 x_capcost_rev_r12 x_dep_capex x_dep_rev_aws`
efter komponenterna.

Dokumentet beskriver. Det säger inget om huruvida investeringarna betalar sig, och kvoterna har ingen etikett.

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
| `x_dep_rev` | 2026Q3 | 9,39 | 2026-10-30 | 12 | 2023Q4 | 2024-10-30 | 28 |
| `x_capcost_rev_r08` | 2026Q3 | 15,78 | 2026-10-30 | 12 | 2023Q4 | 2024-10-30 | 28 |
| `x_capcost_rev_r12` | 2026Q3 | 18,97 | 2026-10-30 | 12 | 2023Q4 | 2024-10-30 | 28 |
| `x_dep_capex` | 2026Q3 | 28,34 | 2026-10-30 | 12 | 2023Q4 | 2024-10-30 | 35 |
| `x_dep_rev_aws` | 2026Q3 | 19,30 | 2026-10-30 | 8 | 2024Q4 | 2025-10-31 | 8 |

Komponenterna för 2026Q3, i MUSD: avskrivningar 174 399 (fyra kvartal), intäkter 1 856 604 (fyra kvartal),
anläggningstillgångar netto 1 481 755 (balans 2026Q3) och capex 615 355 (fyra kvartal).

Historiken börjar sent. Alphabets definition gäller från 2023, och dess kvartal för 2023 blev kända som
jämförelsetal i 10-Q:erna 2024, de sista (2023Q3 och 2023Q4) 2024-10-30. AWS-segmentets avskrivningar finns per
kvartal från 2024, och 2024Q3 och 2024Q4 blev kända 2025-10-31.

## A5-måtten per 2026-11-24

| Nyckel | Nivå | Takt | Förändring i takt | Percentil, takt | n takt / n förändring | Överraskning (B1-drift) |
|---|---|---|---|---|---|---|
| `x_dep_rev` | 9,39 | +12,2 | +0,6 | 94 | 8 / 6 | +0,9 |
| `x_capcost_rev_r08` | 15,78 | +18,3 | +2,2 | 94 | 8 / 6 | +1,5 |
| `x_capcost_rev_r12` | 18,97 | +19,9 | +2,5 | 94 | 8 / 6 | +1,6 |
| `x_dep_capex` | 28,34 | −32,8 | −7,4 | 6 | 8 / 6 | −3,9 |
| `x_dep_rev_aws` | 19,30 | +22,8 | −6,1 | – | 4 / 2 | −2,7 |

Takten är i log ×100 per år. Ingen serie har percentil för förändringen i takt (färre än 8 värden), och AWS-kvoten
har ingen percentil för takten heller.

Nivåerna i den senaste versionen:

| Period | `x_dep_rev` | `x_capcost_rev_r08` | `x_capcost_rev_r12` | `x_dep_capex` | `x_dep_rev_aws` |
|---|---|---|---|---|---|
| 2023Q4 | 7,16 | 10,68 | 12,44 | 60,51 | – |
| 2024Q1 | 7,28 | 10,84 | 12,62 | 59,49 | – |
| 2024Q2 | 7,43 | 11,11 | 12,95 | 55,70 | – |
| 2024Q3 | 7,69 | 11,57 | 13,50 | 52,96 | – |
| 2024Q4 | 7,71 | 11,74 | 13,75 | 47,76 | 12,38 |
| 2025Q1 | 7,93 | 12,20 | 14,34 | 44,91 | 13,30 |
| 2025Q2 | 8,19 | 12,74 | 15,01 | 42,24 | 14,30 |
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
| 2025Q2 | 8,19 | 6,13 |
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
  gällde kvartal från 2024Q4. Kvartalen 2024Q1–2024Q3 ligger kvar på den gamla basen. I `dep_hyp4` sänkte omräkningen
  2024Q4 med 3,7 % (31 123 till 29 963 MUSD) och 2025Q3 med 12,2 % (40 431 till 35 517 MUSD). I den senaste versionen
  har perioderna 2023Q4–2024Q3 bara gammal bas, 2024Q4–2025Q2 en blandning och perioderna från 2025Q3 bara ny bas.
  - Nivån och takten 2026Q3 jämför bara perioder på ny bas och påverkas inte.
  - Förändringen i takt använder takten 2026Q1, som jämför med 2025Q1, en period med två kvartal på gammal bas. Om den
    gamla basen ligger högre (som 2024Q4) är takten 2026Q1 för låg och förändringen i takt för hög.
  - Percentilerna jämför med takter från 2024Q4–2026Q2 i samma (senaste) version, och alla påverkas.
  Effekten räknas inte om, eftersom Microsoft inte har räknat om de kvartalen.
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
