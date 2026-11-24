# R15 – granskning av extraherade nyttjandeperioder (P2a)

Granskningsspår R15, 2026-11-24, gren `auto14/r15-nyttjandeperioder` (bas `auto13/p2a-nyttjandeperioder`, `58f6659`).
Granskat: `curated/useful_lives.csv` (305 rader), `sources/useful_lives.py`, `sources/useful_lives_corpus.py`,
`series/useful_lives.py`, `useful_lives_check.py`, `tests/test_useful_lives.py`, `docs/kallor/nyttjandeperioder.md` och
`git log -p main..auto13/p2a-nyttjandeperioder`. Det är den stickprovsgranskning som CLAUDE.md kräver innan
LLM-extraherade värden används. Den är byggd som R5.

Underlag: alla 91 dokument som CSV:n pekar på hämtades på nytt från www.sec.gov med den ärliga klienten (källa
`r15_review`), inte ur P2a:s cache. EDGAR:s submissions-API för de sex bolagen hämtades samma dag. Texten gjordes om
med P2a:s konvertering (`tsmc_sec.to_text` och `guidance_capex.sentences`), eftersom plats och SHA-256 räknas på den.
Fullständigheten prövades med en egen, bredare sökning i hela korpusen (416 dokument), i 8-K med Item 7.01 och 8.01
nära varje ändring och i CoreWeaves S-1.

Inga värden, ingen kod och ingen produktionsfil är ändrade. Testerna finns i `tests/test_r15_nyttjandeperioder.py`:
fastlåsta värden ur läsningen, egenskaper som håller och sex fynd markerade `xfail(strict=True)`. Ingen takt och ingen
N7-körning är gjord.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Ordning och förregistrering | **OK, med anmärkning.** Reglerna committades före första hämtningen och är oförändrade. Två saker efter att värdena setts är inte fullt redovisade: självkontrollen ändrades (F-1), och 82 av 305 rader kommer från en sökning utanför den låsta kandidatregeln (F-2) |
| 2. Semantisk korrekthet | **OK.** 0 fel av 65 i stickprovet (95 % KI 0–5,5 %). Sedan lästes alla 305 rader: 0 fel (KI 0–1,2 %) |
| 3. Fullständighet | **OK.** Alla 21 ändringar i 10-K, 10-Q och 8-K 2018–2026 finns i CSV:n. Inga policyrader eller effekter med nytt belopp saknas. CoreWeaves ändring stod redan i S-1 2025-03-03 (N-1) |
| 4. Datering och `in_effect` | **OK.** `filed` och `accepted` stämmer med EDGAR för alla 305 rader. `in_effect(as_of)` använder inget som var okänt på `as_of` |
| 5. Text i git och hashar | **Anmärkning.** 305 av 305 hashar stämmer i nyhämtade dokument, och inga meningar finns i git. Men källdokumentet citerar hela meningar (F-3) |
| 6. Publicering | `publish=True` kan stå kvar. Noten för `_lo`-serierna behöver ett tillägg (F-4) |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** N7 kan använda värdena som de är. Inget läckage och inga felaktiga värden
hittades. Rättningarna R-1 till R-6 rör dokumentation och seriernas not.

## 1. Ordning och förregistrering – OK, med anmärkning

Tidslinje 2026-11-24 (UTC), ur git och filtider i den delade raw-katalogen:

| Tid | Händelse |
|---|---|
| 20:11:54 | `6ae7368`: kodningsregler och registerpost. Inget dokument hämtat |
| 20:12:50 | Första hämtningen för källan `useful_lives` (Microsofts submissions) |
| 20:14:03 | `documents.json`, 416 dokument |
| 20:17:06 | `fc49225`: korpus, kandidatfilter, läsare, serier, kontroll och tester. Inga värden |
| 20:17:21 | Sista dokumentet hämtat. `candidates.jsonl` (467 kandidater) skrivs |
| 20:25–20:27 | Meningsfiler, `spec.py` och `build.py` (kodningen) |
| 20:32:07 | `58f6659`: 305 rader, dokumentation och ändringar i kod och kontroll |

- `git diff 6ae7368 HEAD` lägger bara till text utanför avsnittet "Kodningsregler". Reglerna och registerposten är
  oförändrade.
- Korpusmodulen är oförändrad sedan `fc49225`. Omkörd på samma texter ger den exakt de 467 kandidater som P2a läste.
- I den delade raw-katalogen finns inga kopior av dokumenten från före 20:11:54. Git visar bara vad som committades,
  inte vad som lästes lokalt. Agenten säger själv att den kände till de stora ändringarna ur allmän kunskap.

Ändringar efter att värdena setts (mellan `fc49225` och `58f6659`):

- `useful_lives.points()` lägger nu den gamla perioden i kvartalet före ändringskvartalet, i stället för i kvartalet
  för dagen före. Det spelar roll bara för Oracle (räkenskapsåret börjar 1 juni). Rättningen gör att koden följer den
  låsta regeln, och utan den hade Oracles gamla period försvunnit. **OK.**
- **F-1. Självkontrollen ändrades, och det redovisas inte.** Med kontrollen i `fc49225` ger 11 av 305 rader fel:
  8 effekter där beloppet skrivs "$2.0 billion" (mönstret saknade formen med en decimal) och alla 3 stopp. Stoppraden
  pekar på policymeningen, och den meningen har tal för den nya klassen. I `58f6659` läggs decimalformen till, och
  stoppkontrollen byts mot `class_stated()`, som bara räknar klassens namn direkt följt av ett antal år. "0 fel av
  305" gäller alltså den ändrade kontrollen. Ändringarna är rimliga, och R15 bekräftar alla 11 raderna i sak. Men den
  låsta platsregeln för stopp ("finns stycket kvar utan tal är platsen den meningen", annars `absent`) täcker inte
  fallet där stycket finns kvar med tal för en annan klass. Varken valet av plats eller ändringen av kontrollen står
  under "Tolkningar".
- **F-2. Tolkning 1 avviker från den låsta kandidatregeln, och avvikelsen är inte registrerad.** 82 av 305 rader
  kommer från meningar utanför kandidaturvalet: 76 effekter (Microsoft 38, Oracle 24, Meta 9, Amazon 4, Alphabet 1),
  Oracles 5 policyrader 2018–2022 och CoreWeaves ändring. Avvikelsen står i källdokumentet, men utan antal, och inte i
  `docs/mattregister.md` eller beslutsloggen. Sökningen finns inte som kod. Den ändrade ingen kodningsregel, den gör
  bara urvalet större, och den gynnar inget utfall. R15:s egen sökning hittar inga fler rader (punkt 3). Därför är
  det en anmärkning på redovisningen, inte ett fel i värdena.

## 2. Semantisk korrekthet – OK

Varje rad lästes i det nyhämtade dokumentet: meningen på platsen och, för ändringar, meningarna runt den. Bedömt
var klass och räckvidd (`class_code`), lo och hi, gammal period, effektivt datum, effektens belopp, mått, tecken,
grund och period, `period_end` och inlämningsdag.

### Stickprov

Seed 20261124 + 15. Alla ändringar och stopp, 3 policyrader per bolag (CoreWeave har 1) och 5 effektrader per bolag
(CoreWeave har inga).

| Radtyp | Rader | Fel | 95 % KI (Clopper–Pearson) |
|---|---|---|---|
| policy | 16, alla sex bolag | 0 | 0–20,6 % |
| change | 21, alla | 0 | 0–16,1 % |
| effect | 25, fem bolag | 0 | 0–13,7 % |
| stop | 3, alla | 0 | 0–70,8 % |
| **Summa** | **65** | **0** | **0–5,5 %** |

Efter stickprovet lästes också resten (52 policyrader och 188 effekter). Resultatet är **0 fel av 305** (KI 0–1,2 %).
Den risk som återstår ligger i granskarens bedömning av tolkningsfrågorna nedan, inte i siffrorna.

**Effektiva datum (alla 21):** Microsoft "effective beginning fiscal year 2021/2023" ger 2020-07-01 och 2022-07-01.
Alphabet 2021 "effective beginning fiscal year 2021". Amazon "in January 2020/2022/2024" och "effective January 1,
2025". Meta "in 2021" (ett år ger 1 januari), "effective the second/fourth quarter of 2022" och "effective beginning
fiscal year 2025". Oracle "effective at the beginning of fiscal 2023/2025" ger 1 juni. CoreWeave "Effective January 1,
2023". Alla stämmer med reglerna.

**Tolkningsfrågorna i P2a:s granskningsfokus:**

- Metas kategori "network equipment" (3–20 och 3–25 år) som `OTHER`: försvarbart. Metas eget 10-Q 2021-10-26 säger att
  kategorin har servrar.
- `_SUBSET` för alla Metas ändringar och för Amazons förkortning 2025: rätt enligt orden ("selected cohorts", "a
  majority of", "certain", "a subset of"). Följden för N7 står i punkt 4.
- Alphabet 2023, delat i `SERVERS` och `NETWORK_SUBSET`: rätt. 10-K 2024-01-31 kodas bokstavligt för båda klasserna.
  Det är försvarbart, eftersom intervallet för "information technology assets" redan tidigare var servrarnas och
  nätverkets intervall tillsammans.
- Alphabets 8-K 2023-02-02 anger inget datum. Regelns reserv (första dagen i den redovisade perioden) hade gett
  2022-10-01, vilket är fel i sak. Tolkning 2 tar året ur "for the full fiscal year 2023", och 10-K:t dagen efter
  bekräftar 2023. OK.
- Effektens mått: Oracles "decreased our total operating expenses by X" som `operating_income` +X är rätt i sak,
  eftersom intäkterna inte påverkas. CoreWeaves "reduction in total expenses of $20 million" kodas inte. Det är
  inkonsekvent mot Oracle, men inget använder raden (N-3).
- Tecken: alla 213 effekter har tecknet för förändringen. Förlängningar ger lägre avskrivningar och högre resultat,
  och Amazons förkortning 2025 ger det motsatta (test). Amazons belopp per aktie före splitten 2022 (1,51 USD för
  Q1 2022) är kodade som de står.
- Perioder: kvartal, hittills i år och räkenskapsår stämmer, också Microsofts räkenskapsår (juli–juni), Oracles
  (juni–maj) och Metas belopp för nio månader 2021 och 2022.
- Stopp (tolkning 6): försvarbart. Microsoft byter "computer equipment" mot "servers and network equipment" med samma
  intervall. Alphabet slutar nämna "information technology assets". Meta byter kategorin "network equipment" mot
  "servers and network assets". Inget bolag har slutat ange perioden för servrar. Amazons sammanslagning 2026 och
  Alphabets 2024 är inga stopp, eftersom servrarnas period fortfarande anges. Det är samma läsning som för Microsoft,
  där det är den bredare klassen som försvinner.

## 3. Fullständighet – OK

Korpusen jämfördes mot EDGAR. Alla 187 10-K och 10-Q och alla 188 8-K med Item 2.02 2018-01-01–2026-11-24 finns med.

Den egna sökningen delade alla 416 dokument i meningar och sökte med ett bredare mönster än P2a:s ("useful li",
"depreciable li", "estimated li", "average li", "change in (accounting) estimate", "life study", "refresh cycle",
verb för förlänga eller förkorta före "life/lives", "depreciated … over" och "over a period of"). Det gav 1 576
träffar (814 unika meningar). De 454 unika meningar som nämner en tillgångsklass och inte är kodade lästes. De 257 utan
tillgångsklass söktes efter verb för ändring.

| Bolag | Ändringar i 10-K, 10-Q och 8-K 2018–2026 | I CSV:n | Första SEC-dokument |
|---|---|---|---|
| Microsoft | servrar 3→4 och nätverk 2→4 (FY21), servrar och nätverk 4→6 (FY23) | ja, 3 rader | 10-K 2020-07-30, 10-K 2022-07-28 |
| Alphabet | servrar 3→4 och viss nätverksutrustning 3→5 (2021), servrar 4→6 och viss nätverksutrustning 5→6 (2023) | ja, 6 | 8-K 2021-02-02, 8-K 2023-02-02 |
| Amazon | servrar 3→4 (2020), servrar 4→5 och nätverk 5→6 (2022), servrar 5→6 (2024), en del 6→5 (2025) | ja, 5 | 10-K dagen efter 8-K (2020, 2022, 2024), 10-K 2025-02-07 |
| Meta | utvalda 3→4 (2021), merparten 4→4,5 (Q2 2022) och 4,5→5 (Q4 2022), vissa →5,5 (2025) | ja, 4 | 10-Q 2021-10-26, 10-Q 2022-07-28, 10-K 2023-02-02, 8-K 2025-01-29 |
| Oracle | servrar 4→5 (FY23), servrar och nätverk 5→6 (FY25) | ja, 2 | 10-Q 2022-09-13, 10-Q 2024-09-10 |
| CoreWeave | datorutrustning i datacenter 5→6 (2023) | ja, 1 | 10-K 2026-03-02 i korpusen |

Det finns inga fler ändringar till och med 2026-11-24. Metas "in prior years" (före 2021) har varken tidpunkt eller
belopp och kan inte kodas.

**Första dokumentet:**
- Inget 8-K med Item 2.02 före Oracles 10-Q (2022-09-12, 2024-09-09), Metas 10-Q 2022-07-28 och 10-K 2023-02-02,
  Amazons 10-K 2025-02-07 eller Microsofts 10-K nämner ändringen. Metas 10-Q för Q3 2022 (2022-10-27) nämner inte
  förlängningen från Q4.
- 8-K med Item 7.01 eller 8.01 nära ändringarna (Microsoft 2020-06-26, 2020-08-03 och 2022-06-02, Alphabet 2020-12-21,
  2023-01-20 och 2023-01-25, Meta 2022-05-31 och 2022-11-09) säger inget om nyttjandeperioder.
- **N-1. CoreWeave:** S-1 2025-03-03 (0001193125-25-044231) anger både ändringen (5 → 6 år från 2023-01-01) och
  perioden sex år för "Technology equipment". known_from 2026-03-02 är alltså ungefär ett år sent. Det är konservativt
  och följer den låsta regeln (S-1 ingår inte), men källdokumentet säger att det inte är kontrollerat.
- Microsofts samtal 2022-07-26, två dagar före 10-K:t, är känt och konservativt.

**Policyrader:** varje 10-K 2018–2026 för alla sex bolag har minst en policyrad. Bland 10-Q:n anger bara Oracles
2026-09-11 en period i tabellen, och den är kodad. CoreWeaves 10-Q har tabellen utan perioder.

**Effekter:** varje effektmening med nytt belopp, mått eller period är kodad. De träffar som inte är kodade är
upprepningar (MD&A, 10-Q dagen efter 8-K), förändringar av kostnadsposter "including the effect" (enligt "Inte
kodat") och CoreWeaves effekter för 2023 (tolkning 4).

## 4. Datering och `in_effect` – OK

- `filed`, `accepted`, formulär, `reportDate` (= `period_end` för 10-K och 10-Q) och primärdokument stämmer mot EDGAR
  för alla 305 rader. En inlämning efter 17.30 ET får nästa dags `filingDate`, vilket är konservativt.
- Observationstabellen i P2a:s worktree (203 rader, 30 serier) är identisk med `series_frame`. Varje `known_from` är en
  inlämningsdag i CSV:n. Den längsta ledtiden före periodens slut är 64 dagar (Microsoft 2022Q3, känt 2022-07-28 inne
  i kvartalet). Inget värde är känt innan dess kvartal har börjat.
- `in_effect(bolag, familj, gräns, as_of)` jämfördes med samma funktion på en CSV som bara har rader med `filed` ≤
  `as_of`. Det gjordes för alla bolag, familjer och gränser, på varje inlämningsdag och dagen före: 9 720
  jämförelser och 0 skillnader. En rad som lämnas in efter `as_of` ändrar inte resultatet (test).
- N7 (P3) läser serierna ur observationstabellen med `as_of` och inte via `in_effect`, men stegvärdena är desamma.
  Testet `test_latest_stated_server_life_as_known_on_a_date` låser det värde som V2 tar på några prognosdagar.
- N-4, för P3:s granskning: `_SUBSET` ingår inte i serierna. Det är registrerat, men det betyder att N7:s V2 ser
  Metas `hi` = 4 under hela 2022 (fast merparten gick till 4,5 och sedan 5) och 5 under 2025 (fast de flesta gick
  till 5,5). Amazons `hi` är 6 under 2025, fast en del gick till 5.

## 5. Text i git och hashar – anmärkning

- Alla 305 meningar har den lagrade SHA-256 på angiven plats i de nyhämtade dokumenten. Ingen mening har flyttat. P2a:s
  cachekopior ger exakt samma text som de nyhämtade dokumenten.
- `data/` är gitignorerad. Inga meningsfiler och inga kandidatfiler finns i git.
- Noterna i CSV:n har bara korta ordalydelser, högst 8 ord inom citattecken (test).
- **F-3. Källdokumentet citerar hela meningar.** `docs/kallor/nyttjandeperioder.md` har fem citat på 11–22 ord ur
  dokumenten: Amazons mening om guidance (22 ord), Microsofts effektmening för FY21 (16), Alphabets policymening 2024
  (15), meningen om ikraftträdande 2021 som Microsoft och Alphabet har (12, hela meningen) och Amazons ordalydelse om
  perioden före och efter ändringsdagen (11). Det strider mot CLAUDE.md ("aldrig själva texten") och mot dokumentets
  egen licensdel ("citerar inte, utom korta ordalydelser för klassen"). SEC-texten är offentlig, så risken är liten,
  men regeln är tydlig.

## 6. Publicering

`publish=True` kan stå kvar. Det är siffror ur offentliga SEC-dokument med källhänvisning, och extraktionen håller.

**F-4.** `_lo`-serierna blandar punkter (ändringar) och intervall (policy). `useful_life_servers_msft_lo` och
`useful_life_network_msft_lo` går från 6 till 2 år 2026Q2 utan att perioden har ändrats. Det står i källdokumentet,
men inte i seriernas not, som är den text som visas på sidan. En läsare ser då en förkortning som inte finns.

## Rättningar

| Nr | Fynd | Allvar | Rättning | Test (xfail tills rättat) |
|---|---|---|---|---|
| R-1 | F-1 | should_fix | Lägg till en tolkning i `docs/kallor/nyttjandeperioder.md`: när stycket finns kvar med tal för en ny klass pekar stoppraden på policymeningen. Skriv också att `useful_lives_check` ändrades efter första körningen (`class_stated()` och formen "$X.0 billion") och att den gamla kontrollen gav 11 fel av 305 | `test_stop_check_change_is_disclosed` |
| R-2 | F-2 | should_fix | Logga avvikelsen från kandidatregeln i `docs/mattregister.md` med datum, motivering och antal (82 av 305 rader). Lägg gärna den kompletterande sökningen som kod i `useful_lives_corpus`, så att urvalet går att göra om | `test_candidate_rule_deviation_is_registered` |
| R-3 | F-3 | should_fix | Korta citaten i källdokumentet till högst tio ord eller skriv om dem med egna ord | `test_source_doc_has_no_long_quotes` |
| R-4 | F-4 | should_fix | Skriv i noten för `_lo`-serierna att lo kan sjunka utan att perioden har ändrats, när ett dokument går från en punkt till ett intervall. Alternativet är att bara publicera `_hi` | `test_lo_note_explains_points_and_ranges` |
| R-5 | N-1 | note | Skriv att CoreWeaves S-1 2025-03-03 anger ändringen och perioden, att known_from därför är ungefär ett år sent och att S-1 inte ingår enligt regeln | `test_source_doc_names_coreweave_s1` |
| R-6 | N-2 | note | "Oracle `network` från 2024Q2" ska vara 2024Q1. Serien börjar med den gamla perioden ur ändringsraden | `test_source_doc_oracle_network_start` |

Anmärkningar utan rättning:

- N-3: CoreWeaves effekter för 2023 ("total expenses", "per share") hade kunnat kodas som rörelseresultat +20 MUSD,
  på samma sätt som Oracle. Inget använder dem.
- N-4: se punkt 4. Det rör N7:s V2, inte extraktionen.
- N-5: Metas senare dokument säger "most" i stället för "certain" om ändringen 2025. Koden och värdena är desamma, och
  noten nämner det. Det följer regeln om ny ordalydelse med samma räckvidd.

## Vad som inte kunde verifieras

- Samtal och pressmeddelanden på bolagens egna sidor är inte hämtade. De kan bara göra known_from tidigare, aldrig
  senare.
- 8-K med Item 7.01 och 8.01 är sökta nära ändringarna, inte alla.
- Klassbedömningen (till exempel Metas "network equipment" och Alphabets "information technology assets") vilar på
  bolagens egna ord. Hur stor del av en bredare klass som är servrar går inte att se i dokumenten.
- Granskningen bekräftar extraktionen. Den säger inget om hur väl perioderna förklarar avskrivningarna i N7.
