# R9 – granskning av diffusionsindex v2 (källfamiljer)

Granskningsspår R9, 2026-11-24, gren `auto14/r9-index-v2` från `auto13/k1-kallfamiljer` (`cc686c0`). Granskat:
spår K1, alltså registerposterna "2026-11-24 – Diffusionsindex v2" och "familjenamnet i G2 byts" i
`docs/mattregister.md`, `git log -p main..auto13/k1-kallfamiljer` och koden i `src/ai_tracker/state/`, `letter.py`,
`quarterly.py`, `site/` och `site_bundle/`. Webbsessionens filer (`web/`) lästes men ändrades inte.

Underlag: katalogen (`catalog.by_key()`, 488 serier), syntetiska tabeller i testerna och basens riktiga tabell, som
installerades efter K1 (äldsta säkerhetskopian av basens tabell är skriven 21:02). Med den riktiga tabellen gjordes
bara strukturkontroller: vilka familjer som räknas, licensgrinden och att brevet inte namnger innehållna serier.
**Inga index, tillstånd eller riktningar på riktiga data tolkades eller redovisas här.**

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering och familjetabell | **OK.** Registerposten före koden, tabellen täcker varje kärnpost en gång och följer regeln. Namnbytet i G2 är en egen daterad post. Påståendet om "försiktigare" tillstånd i registerposten håller inte enligt orkestrerarens rekonstruktion (S3). R9 har inte gjort om jämförelsen |
| 2. `branch()` | **OK.** Familjer, röster, räkning och gränser stämmer i alla kantfall. Ett latent flyttalsfel vid exakt tröskel (N1) kan inte ändra något tillstånd med de registrerade tabellerna |
| 3. Licensgrinden | **OK.** En innehållen familj räknas men namnges inte och får ingen röst i brevet, kvartalsrapporten, gamla sidan, metodsidan eller paketet. `gate.scan` är ren, också på riktiga data |
| 4. Ögonblicksbilden | **OK.** Regel, familjetabell och `min_families` sparas. `show`, `due`, `snapshot.yml`, `pipeline publish`, C4 och avstämningarna är opåverkade |
| 5. Paketet 1.1.0 | **OK med anmärkning.** Bara tillägg, fixturerna är reproducerbara. Webben saknar ordet "för få källor" (S1). Fixturbygget läser miljöns BTOS-schema (S2, fanns före K1) |
| 6. Backcast med `--compare` | **OK** på syntetisk tabell |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Inget fel ger fel officiellt index eller tillstånd, läckage, licensexponering
eller trasig rutin. K1 kan mergas till `main`. Det måste ske före den första skarpa ögonblicksbilden 2026-11-30
(jobbet körs 22:41 UTC). Annars skrivs den med v1, och den går inte att skriva om. Tre saker bör ordnas i samband
med mergen:
- S1: webbsessionen lägger till tillståndet "för få källor". Annars visar `/next/` "för få serier" för grenar med
  för få källor, till exempel G8 med nio serier.
- S2: hela sviten fallerar på ett test i alla kataloger med den delade rå-cachen, också i huvudkatalogen. Det är
  miljön och inte K1. Kör testet med en tom rå-katalog eller rätta fixturbygget.
- S3: en daterad registeranteckning om att "försiktigare åt båda hållen" inte håller. Regeln ändras inte.

## 1. Förregistrering och familjetabell – OK

Ordningen (alla 2026-11-24, UTC):

| Tid | Commit | Innehåll |
|---|---|---|
| 20:07 | `7ba72eb` | Registerposten: definition, familjetabell G1–G9, regel v2, v1 bredvid. Bara `docs/mattregister.md` |
| 20:22 | `d80d7e3` | Koden: `FAMILIES`, `branch()`, ögonblicksbild, brev, sidor, paket, tester |
| 20:24 | `ae13284` | Dokumentation (datakontrakt, resultat, beslutslogg, kalibrering) |
| 20:26 | `34600d4` | Ny daterad registerpost: G2-familjens namn |
| 20:27 | `cc686c0` | `docs/drift.md` |
| 21:02 | – | Basens observationstabell skrivs (äldsta säkerhetskopian i `data/merge_backups/`) |
| 21:03 | – | `outputs/state_backcast.csv` i K1:s arbetskatalog: v1 mot v2 på riktiga data, 2024-01–2026-10. Inte committad, inte skriven av K1 |
| 21:04 | `a229548` | Orkestrerarens rättelse om v2:s effekt (`docs/riktning.md`, beslutsloggen), på orkestrerarens gren |

- Registerposten kom före koden, och hela K1 var committat innan det fanns riktiga data i basen. K1:s egen
  datakatalog innehöll bara `README.md` och en cache. Begränsning: git visar bara vad som committades, inte vad som
  räknades lokalt. Inget i underlaget tyder på en tidigare körning.
- Första v2-värdena på riktiga data räknades 21:03, efter registerposten och efter K1. Förregistreringen håller.
  Regeln får nu inte ändras med hänvisning till de värdena.

**Familjetabellen.** Tabellen har 37 rader och täcker varje post i de gällande kärnserietabellerna exakt en gång
(K1:s paritetstester och `test_no_two_families_of_a_branch_share_a_series`). Antalet familjer stämmer med registrets
text: G1 3 plus en per vald benchmark, G2 1, G3 7, G4 6, G5 5, G6 7, G7 3, G8 1, G9 3.

Regeln kontrollerades mot katalogens fält. De 11 familjerna med flera serier har var och en en källa (före
skivkoden inom parentes), en enhet och en frekvens: `eu_ai_ent`, `g3_npm`, `g3_pypi`, `g3_wiki`, `us_ip_g17`,
`us_imports_ft900`, `us_elec_sales_com`, `eia930_avg` (DOM ur SUBREGION-filen, de övriga ur BALANCE-filen, samma
undersökning och begrepp), `pjm_lf_peak`, `ai_postings_share` och `g9_arxiv`. Alla enserierfamiljer är olika
inlämnare eller olika begrepp. **Ingen felaktig tilldelning hittades.**

Gränsfallen följer den skrivna regeln:
- `<valda>` ger en familj per benchmark, medan arXiv-kategorier, npm-paket och Wikipedia-sidor är en familj var.
  Registret motiverar undantaget uttryckligen (olika förmågor, högst en benchmark per benchmarkfamilj). Det är ett
  registrerat val, inte en mekanisk följd av "skiva". Det spelar roll först när benchmarkerna börjar räknas (N3).
- Kvarvarande samvariation (ECI och valda benchmarks, `capex_ocf_hyp4` och `capex_hyp4`, npm och PyPI för samma
  SDK:er, PJM DOM och EIA-930 DOM) är redovisad i registret eller följer av regeln om olika källor.

**Namnbytet i G2 är legitimt.** Det är en egen daterad post (20:26), skriven före all beräkning på riktiga data, och
bara namnet ändras. Testet `test_rename_amendment_changes_only_the_name_of_the_g2_family` läser registret före och
efter posten: bara G2:s familjenamn skiljer, och kärnserietabellerna är desamma. Motiveringen håller (det gamla
namnet var katalognyckeln för ECI-varianten). En detalj i texten stämmer inte: "som de andra familjerna med en
serie". Sju enserierfamiljer har inte seriens namn (N2).

**Påståendet om effekten (S3).** Registerposten säger "Påståendena blir försiktigare åt båda hållen", och
beslutspunkt 2 i `docs/riktning.md` säger "Ändringen gör tillstånden mer försiktiga". Orkestrerarens rättelse
(`a229548`) visar att det inte håller i rekonstruktionen. Rättelsen står i beslutsloggen och i avsnitt 6 i
`riktning.md`, men inte i registret och inte i avsnitt 9. Huvudskälet, oberoende källor, påverkas inte.

Avsnitt 2 i registret beskriver fortfarande v1. Det är rätt enligt registrets regel att inget skrivs om, och v2 står
som daterad ändring.

## 2. `branch()` – OK

Kontrollerat med syntetiska tester (`tests/test_r9_index_v2.py`) och mot koden:

| Fall | Resultat |
|---|---|
| Familj där alla serier är inaktuella (riktiga katalogspecar, G.17 slutar 2024-06) | Ingen röst och räknas inte. G6 får 2 familjer och "för få källor", medan v1 med 3 serier har ett tillstånd |
| Inaktuell serie i en blandad familj | Familjens röst bygger bara på den räknade serien |
| Spärrad serie (bakåtfylld, färre än 24 månader egna ögonblicksbilder) | Utesluten före röstningen. G9 med bara arXiv har 1 familj |
| `<valda>` med mättad benchmark (> 0,90), en giltig och en som saknas i katalogen | En familj per benchmark. Den mättade och den saknade får ingen röst och räknas inte |
| BTOS-platshållaren | En familj för alla regimer, bara den aktiva regimen räknas. Ingen känd regim ger ingen familj |
| Tom gren och gren utan räknade serier | "inga registrerade kärnserier", respektive index `None` och "för få källor" (v1 "för få serier") |
| Bara enserierfamiljer (20 slumpade fall, 1–39 serier) | `index_v2 == index_v1` exakt, inte bara ungefär |
| Blandade familjer vid exakt 0,67 och 0,33, och vid 2/3 och 1/3 | Rätt tillstånd. Gränserna jämförs oavrundat |
| Familj med bara innehållna serier | Räknas i indexet och i `n_families` |

`n_families` räknar bara familjer med minst en räknad serie, och "för få källor" ges exakt när färre än 3 familjer
räknas. Inaktuella serier, benchmarkspärren och bakåtfyllnadsspärren slår till innan familjerna röstar.

**Latent flyttalsfel (N1).** Indexet är ett flyttalsmedel av flyttalsröster. Tre familjer med rösterna 1, 1 och 1/100
(en familj med 50 serier) ger exakt 67/100, men koden räknar 0,6699999999999999 och säger "stabil" i stället för
"accelererar". Registret säger att gränserna jämförs oavrundat. Testet
`test_registered_family_tables_cannot_hit_a_threshold_exactly` går igenom alla kombinationer av räknade serier och
riktningar med de registrerade familjestorlekarna (G1 med upp till tre valda benchmarks). Ingen ger exakt 0,67 eller
0,33, så felet kan inte ändra ett tillstånd i dag. Det kan bli aktuellt med stora familjer. Rättning: räkna rösterna
som bråk (`fractions.Fraction`) och jämför exakt.

**Riktiga data, bara struktur (2026-10-31).** Körningen gick utan fel. Antal räknade familjer (och serier): G1 2 (2),
G2 0 (0), G3 4 (9), G4 6 (6), G5 5 (5), G6 7 (9), G7 3 (13), G8 1 (9), G9 1 (3). Varje räknad serie hör till en
familj i grenens lista, och `n_families` är antalet familjer med röst. Tre räknade familjer har bara innehållna
serier: `g3_npm`, `pjm_lf_peak` och `g9_arxiv`. G1:s benchmarks har inga kända data på dagen, så G1 saknar
tillstånd med båda reglerna.

## 3. Licensgrinden – OK

En syntetisk innehållen serie fördes genom varje konsument, både i en blandad familj (K1:s tester) och som
enserierfamilj vars id är seriens nyckel, som i det riktiga registret (R9:s tester):

| Konsument | Resultat |
|---|---|
| Ögonblicksbilden | Familjen räknas (G9: 2 familjer, varav 1 innehållen). Ögonblicksbilden är registret och innehåller alla serier, som i v1 |
| Månadsbrevet | "2 källor (3 serier: …)", den publika familjens röst och "1 källa med serier som inte visas av licensskäl räknas utan att namnges". Nyckeln och etiketten finns bara i avsnittet "Visas inte av licensskäl" |
| Kvartalsrapporten | v2-ordning med "för få källor", fotnoten "(regel v2)". Nyckeln finns bara i licensavsnittet. K1 hade inget test för kvartalsrapporten (S4, nu tillagt) |
| Gamla sidan, JSON | `families` utan den innehållna familjen, `n_families_withheld` 1. Nyckeln finns bara i `withheld`-listor |
| Gamla sidan, HTML | Nyckeln finns bara i `<section id="withheld">`. Grensidan säger att 1 källa räknas utan att namnges |
| Metodsidan | Familjen vars id är en innehållen nyckel visas inte i familjetabellen. Övriga familjer visar bara publika poster och `n_withheld` |
| Paketet | `E.assemble` stoppar inte, och `gate.scan` är tom med båda arXiv-serierna som egna familjer. Ett planterat familje-id med en innehållen nyckel fångas av `gate.scan` |

På riktiga data: `test_real_bundle_passes_the_gate_and_the_schemas` passerar med v2. Ett rekonstruerat brev för
2026-10 namnger ingen av katalogens 102 innehållna serier (nyckel eller etikett) utanför licensavsnittet.

**Härledning genom subtraktion (N4).** När en grens enda dolda familj har en serie går dess röst att räkna fram ur
index, `n_families` och de visade rösterna. I v1 gick riktningen redan att räkna fram ur antalen upp, oförändrade och
ned. Det gäller i dag G7 (PJM) och G9, där alla räknade serier är innehållna. Regeln tillåter grenens summering, och
v2 gör det inte värre. Licensgranskningen (R10, R-W1) bör ta ställning till om summeringen räcker.

## 4. Ögonblicksbilden – OK

- `python -m ai_tracker.state --table <tmp> snapshot --date 2026-10-31 --out-dir <tmp>` skriver filen. `rules` har
  `index_rule` "v2", `index_rule_note`, `min_families` 3, `min_series` 3 och hela familjetabellen per gren. Varje
  gren har `rule_version`, `n_families`, `families` och `v1`. G6 får 3 familjer av 5 serier, G4 4 av 4 med
  `index == v1`, G8 och G9 1 familj och "för få källor". En fil skrivs aldrig om (`FileExistsError`).
- `show` skriver `källor=` och v1 per gren och avstämningarna. `due` svarar rätt för 2026-11-24 och 2026-11-30.
- C4-sektionen läggs till som förut (`regime=True`). C4 läser bara `series_used`, som v2 inte ändrar.
  Avstämningarna räknas fortfarande inte i något index.
- `.github/workflows/snapshot.yml`, `pipeline.py` och `regime/` är oförändrade i K1. Testerna för `pipeline publish`
  passerar.
- **Tidpunkt:** jobbet 2026-11-30 22:41 UTC kör den kod som finns på `main`. K1 måste vara mergat före det.

## 5. Paketet 1.1.0 – OK med anmärkning

- **Schemat:** en maskinell jämförelse av `main` och K1 visar bara tillägg. Inga fält är borttagna, inga nya krav
  på befintliga objekt och inga typbyten. Enda ändringen i ett befintligt fält är det nya enum-värdet "för få källor"
  i `common.json#/$defs/state`. "för få serier" finns kvar. Schemakopiorna i `web-data-fixtures/schema/` är identiska.
- **Fixturerna:** `python -m ai_tracker.site_bundle fixtures` två gånger med en tom rå-katalog
  (`AI_TRACKER_SHARED_RAW`) ger filer som är identiska med de committade och med varandra. Manifestet har 1.1.0.
- **S2 (fanns före K1):** i en arbetskatalog med den delade rå-cachen skiljer sig N5:s kalender
  (`next_origin` 2026-12-02 i stället för `null`). Fixturbygget läser BTOS-schemat i miljön
  (`sources.census_btos.SCHEDULE_LOG`). Därför fallerar `test_committed_fixtures_are_the_current_synthetic_bundle` i
  alla kataloger med rå-cachen, också i huvudkatalogen, som har en egen `data/raw/census_btos/schedule_log.parquet`.
  Den som kör `fixtures` där får fixturer som fallerar i CI. Det rör inte K1:s fält.
- **Webben läser bara major** (`web/src/lib/data/loaders.ts`, `SCHEMA_MAJOR = 1`), så 1.1.0 godtas.
- **S1:** `web/src/lib/design/state.ts` och `types.ts` saknar "för få källor". `stateStyle` faller tillbaka på
  "för få serier", och `Glyph` skriver det ordet. `pages.yml` bygger `/next/` från det riktiga paketet, så G8, med
  nio serier, skulle stå som "för få serier" så snart K1 är på `main`. K1:s beslutslogg nämner att webben behöver
  tillståndet, men det är inte gjort.

## 6. Backcast med `--compare` – OK

`python -m ai_tracker.state --table <tmp> backcast --start 2026-08 --end 2026-10 --out <tmp> --compare 2` skriver
CSV:n med etiketten "rekonstruerad" och en Markdown-tabell med 18 rader. En gren utan räknade serier får "–" och
inget fel. `--table` stänger av den delade basen, så körningen är helt syntetisk.

## Rättningar (för ett rättningsspår)

| # | Var | Rättning |
|---|---|---|
| S1 | `web/src/lib/design/state.ts`, `web/src/lib/data/types.ts` (webbsessionen) | Lägg till "för få källor" med samma glyf och färg som "för få serier" men eget ord. Helst före eller direkt efter mergen av K1. Det strikta xfail-testet `test_web_state_vocabulary_has_the_v2_state` slår om |
| S2 | `site_bundle/__main__.py` `build_fixtures`, `synthetic.py`, `tests/conftest.py` (fanns före K1) | Den syntetiska världen ska ha ett eget (tomt) BTOS-schema: peka `census_btos.SCHEDULE_LOG` till den temporära katalogen under bygget, eller skicka schemafilen till N5:s kalender. Isolera också `SCHEDULE_LOG` i `conftest.py`, som `SHARED_DIR`. Xfail: `test_synthetic_bundle_does_not_read_the_environments_btos_schedule` |
| S3 | `docs/mattregister.md` (ny daterad anteckning), `docs/riktning.md` avsnitt 9 (orkestreraren) | Anteckna att "Påståendena blir försiktigare åt båda hållen" var en förväntan efter konstruktion som inte håller i rekonstruktionen (beslutsloggen 2026-11-24, "Rättelse om index v2:s effekt"). Ingen regeländring. Låt beslutspunkt 2 säga samma sak som avsnitt 6, och låt ägaren bekräfta att beslutet står |
| S4 | `tests/` | Kvartalsrapportens v2-text saknade test. Tillagt i R9 (`test_quarterly_report_with_v2_snapshots`) |
| N1 | `state/branch.py` `vote`, `diffusion_v2` | Räkna röster och index som bråk och jämför gränserna exakt. Spara flyttalet i filen. Xfail: `test_exact_threshold_is_compared_exactly_with_a_large_family` |
| N2 | registret, nästa post som rör familjer | Rätta "som de andra familjerna med en serie": sju enserierfamiljer har inte seriens namn. Ingen effekt |
| N3 | G1, när benchmarkerna börjar räknas | Undantaget för `<valda>` (en familj per benchmark) är registrerat. Följ samvariationen med ECI när spärren släpper |
| N4 | R10 / R-W1 | Ta ställning till att en ensam dold familjs röst (och i v1 en ensam dold series riktning) går att räkna fram ur grenens summering |
| N5 | `letter.py` `v1_note`, `site/render.py` `v1_text`, `family_votes_text` | Visa inte v1-raden när båda reglerna saknar tillstånd ("för få källor" mot "för få serier"). Skriv inte "Röst per källa …: –" när alla familjer med röst är dolda (G9 i dag) |
| N6 | `quarterly.py` fotnot | "Grenar med tre till fem serier flyttas mycket av en enda serie" bör säga källor med v2, som brevet |
| N7 | brev och sidor (fanns före K1) | Index visas med två decimaler, så 2/3 står som "0,67" bredvid "stabil". Skriv att gränserna jämförs oavrundat, eller visa tre decimaler nära gränsen |
| N8 | `series/halvledare.py` (fanns före K1) | `asml_net_sales` använder TSMC:s licenstext ("Statutory filing by TSMC"). Ge ASML en egen text. Xfail: `test_asml_licence_text_names_asml_not_tsmc` |
| N9 | `site/data.py` `index_families` | En familj vars id är en innehållen nyckel faller bort ur metodsidans familjetabell utan markering. Ingen familj berörs i dag. Visa den som "(1 visas inte)" med ett neutralt id |

## Tester

`tests/test_r9_index_v2.py` (syntetiska fixturer, inget nät; testerna för riktiga data i punkt 2 och 3 kördes för
hand):
- register: namnbytet ändrar bara G2:s namn, familjer med flera serier har en källa, en enhet och en frekvens,
  antal familjer per gren, ingen serie i två familjer (passerar)
- `branch()`: inaktuell familj, inaktuell serie i blandad familj, spärrad familj, benchmarkspärren och `<valda>`,
  BTOS-regimer, tom gren, v2 = v1 exakt för enserierfamiljer, exakta gränser, registrerade tabeller kan inte träffa en
  gräns exakt, innehållen familj räknas (passerar)
- licens: brevet, gamla sidan (JSON, HTML, metod), paketet med `gate.scan`, kvartalsrapporten (passerar)
- ögonblicksbild och CLI: `snapshot`, C4-sektionen, `show`, `due`, `backcast --compare` (passerar)
- paketet: båda "för få"-tillstånden i enum, version 1.1.0 (passerar)
- strikt xfail: N1 (exakt gräns), S2 (fixturbygget läser miljön), S1 (webbens ordlista), N8 (ASML:s licenstext)

`python -m pytest -q tests/test_r9_index_v2.py`: 46 passerade, 4 xfail.

Hela sviten en gång i arbetskatalogen (med den delade basen och rå-cachen): 1 603 passerade, 3 överhoppade,
5 xfail (R8:s och R9:s fyra) och 2 fel, båda utanför K1:
- `test_site_bundle.py::test_committed_fixtures_are_the_current_synthetic_bundle`: S2. Med en tom rå-katalog
  (`AI_TRACKER_SHARED_RAW`) passerar testet.
- `test_data_quality.py::test_freshness_as_of_last_fetch` (riktiga data): `g2_price_at_arena_capability` och
  `g2_price_at_arena_capability_4o` (G2A, underkända i R8) har inga rader i den installerade basen. Det gäller
  datasnapshoten, inte koden här.
