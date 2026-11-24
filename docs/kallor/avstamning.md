# Avstämningar mellan leden (A5)

Spår A5 (steg 2, våg 2). Byggt 2026-11-24. Definitionerna är låsta i `docs/mattregister.md`, posten
"2026-11-23 – A5: avstämningar mellan leden", och registrerades innan något beräknades. Kod:
`src/ai_tracker/series/avstamning.py` (definitioner, versionslogik, katalogposter),
`src/ai_tracker/state/branch.py` (`reconciliations`, gruppen "Avstämningar") och registret i
`src/ai_tracker/state/register.py` (`RECONCILIATIONS`). Tester: `tests/test_avstamning.py` (fixturer, inget nät).
Bygg: `python -m ai_tracker.observations x_capex_cloud x_rpo_cover x_nvda_capex x_debt_capex x_capex_ocf`.
Här finns ingen tolkning av siffrorna.

## Serierna

Alla är kvartalsserier, härledda ur serier som redan finns i katalogen. De läses ur observationstabellen och inte
direkt ur källorna, så att de bygger på exakt de versioner som är sparade.

| Nyckel | Definition | Led | Enhet | Historik (senaste version) | Versioner | Första `known_from` |
|---|---|---|---|---|---|---|
| `x_capex_cloud` | `capex_hyp4` / (`rev_aws` + `rev_google_cloud` + `rev_msft_cloud`), samma kvartal | L3–L5 | kvot | 2020Q3–2026Q3, 25 kvartal | 37 | 2021-10-27 |
| `x_rpo_cover` | `rpo_hyp4` (balans vid kvartalets slut) / summa `capex_hyp4` för kvartalet och de tre föregående | L4–L5 | kvot | 2019Q4–2026Q3, 28 kvartal | 60 | 2020-02-04 |
| `x_nvda_capex` | `rev_nvda_datacenter` / `capex_hyp4`, samma kalenderkvartal | L5–L6 | kvot | 2017Q3–2026Q2, 36 kvartal | 44 | 2018-11-15 |
| `x_debt_capex` | summa `debt_issued_hyp4` / summa `capex_hyp4`, kvartalet och de tre föregående | L5 | kvot | 2018Q2–2026Q3, 34 kvartal | 82 | 2019-07-26 |
| `x_capex_ocf` | `capex_hyp4` / `ocf_hyp4` × 100 (samma som `capex_ocf_hyp4`) | L5 | procent av OCF | 2017Q3–2026Q3, 37 kvartal | 45 | 2018-10-26 |

Historiken begränsas av den kortaste komponenten: Microsoft Cloud från 2020Q3, RPO-summan från 2019Q4 och
`capex_hyp4` från 2017Q3 (Amazons bruttotagg). En rullande summa kräver dessutom tre kvartal före det första.
`x_capex_ocf` har samma värden och versioner som den befintliga `capex_ocf_hyp4` (testat), men som avstämning
mäts den med årsförändring i log, inte i procentenheter.

## Versioner och `known_from`

- För perioden p består indata av par (serie, kvartal): p för en term i samma kvartal och p−3 till p för en
  summa över fyra kvartal.
- Vid varje `known_from` d hos något av indata tar varje par sin senaste version med `known_from` ≤ d. En
  version finns bara när alla par har en, och den dateras d, alltså den senaste komponenten som används. En
  rullande summa finns därför först när alla fyra kvartal är kända på dagen.
- En ny rad skrivs när värdet ändras. En revidering av ett äldre kvartal i fönstret (till exempel en omräknad
  capex för p−3) ger en ny version för varje period vars fönster innehåller det kvartalet.
- **Stock och flöde:** RPO är en balans vid kvartalets slut. Den summeras aldrig, och en omräkning av en
  tidigare balans påverkar inte senare perioder. Capex, skuldemission, intäkter och OCF är flöden.
- `source` blir `derived`, eller `backfill` om något indata är en backfill-rad (inga sådana i dag, eftersom alla
  komponenter är SEC-dokumentdaterade).
- **Kalendermappning** som komponenterna: kalenderkvartalet för räkenskapskvartalets mittpunkt. Nvidias
  kvartal (aug–okt osv.) ligger alltså cirka en månad efter capex-kvartalet med samma etikett, och Oracles
  RPO-balans (30 nov i Q4) en månad före de övriga bolagens.
- Bolagsmängderna skiljer sig: capex är MSFT+GOOGL+AMZN+META, RPO är MSFT+GOOGL+AMZN+ORCL och molnet tre
  segment (Meta har inget). Det är så registret definierar kvoterna.
- **Läckage:** giftestet i `tests/test_avstamning.py` lägger till vilda revideringar av alla komponenter dagen
  efter beräkningsdagen och kontrollerar att `as_of` för varje avstämning och måtten i gruppen är oförändrade,
  och att en avkortad tabell ger samma resultat.

## Drift

- `Spec.components` anger komponenterna. `observations.refresh` hämtar härledda serier sist, så veckokörningen
  bygger dem på samma körnings komponentrader. Om en komponent byggs om (`--rebuild`) ska avstämningarna också
  byggas om.
- Aktualitet: standardgränsen för kvartal (25 + 92 + 30 = 147 dagar). `x_nvda_capex` har Nvidias gräns
  (199 dagar), eftersom Nvidias rapport kommer 45–77 dagar efter kalenderkvartalets slut.
- Licens: komponenternas (SEC, offentlig information, kontrollerad 2026-11-23). `publish=True` bara när alla
  komponenter får publiceras, och `catalog.validate` kontrollerar det.

## Mått och var de visas

- **Mått** enligt registret: takt = årsförändring i log(kvot) ×100, förändring i takt = takten nu minus två
  kvartal tidigare, percentiler med minst 8 värden, allt med `as_of` på beräkningsdagen och expanderande fönster.
- **Räknas inte i något grenindex.** Serierna står inte bland kärnserierna, och `branch` vägrar räkna dem även om
  de skulle läggas dit. Regimmodellen (G-D) använder dem inte.
- Ögonblicksbilden har en egen sektion `reconciliations` (grupp "Avstämningar", `in_diffusion: false`), och
  `python -m ai_tracker.state show` skriver ut dem efter grenarna.
- Månadsbrevet har rubriken "Avstämningar" med nivå, takt och förändring i takt per serie.
- Hemsidan har en liten tabell i avsnittet "Avstämningar mellan leden" på metodsidan. Den fullständiga
  flödesvyn är spår E2.
