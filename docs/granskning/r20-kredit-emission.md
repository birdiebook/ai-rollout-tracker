# R20 – granskning av spread vid emission (KR1)

Granskningsspår R20, 2026-11-25, gren `auto14k/r20-kredit-emission` (bas `auto14k/kr1-kredit-emission`, `2f85ed8`).
Granskat: `curated/credit_issuance.csv` (239 rader), `sources/credit_issuance_corpus.py`, `sources/credit_terms.py`,
`sources/credit_issuance.py`, `series/credit_issuance.py`, `credit_issuance_check.py`, `tests/test_credit_issuance.py`,
`docs/kallor/kredit_emission.md`, registerposten och `git log -p claude/elegant-tesla-awd2sz..auto14k/kr1-kredit-emission`.
Det är den extraktionsgranskning som CLAUDE.md och registerposten kräver innan värdena publiceras.

Underlag: EDGAR:s submissions-API för de sex bolagen och alla 146 dokument med formuläret FWP, 424B2 eller 424B5
2020-01-01–2026-11-25, hämtade på nytt från www.sec.gov med den ärliga klienten (källa `r20_review`, inte KR1:s cache).
Dessutom fem 424B3, två 8-K från CoreWeave, fyra 10-Q (Oracle och Microsoft) och FRED:s serienoter för `BAMLC0A0CM` och
`BAA`. Alla SEC-anrop gick i följd med 0,3 s mellan dokumenten, och inget gav 403 eller 429. Texten lästes med en egen
HTML-konvertering (BeautifulSoup), inte med KR1:s `lines()`. Plats och SHA-256 prövades med KR1:s `lines()`, eftersom
de räknas på den.

Inga värden, ingen kod och ingen produktionsfil är ändrade. Testerna finns i `tests/test_r20_kredit_emission.py`:
fastlåsta värden ur läsningen, egenskaper som håller och fem fynd markerade `xfail(strict=True)`. Ingen takt och ingen
jämförelse över tid är gjord.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Ordning och förregistrering | **OK.** Reglerna och registerposten committades före första hämtningen och är oförändrade. Parserändringen efter värdena ändrar ingen rad |
| 2. Korrekthet | **OK.** 0 fel av 72 i det slumpade stickprovet (95 % KI 0–5,0 %). Alla 239 rader prövades också med egen text och egen indelning per tranche: 0 fel (KI 0–1,5 %) |
| 3. Fullständighet | **OK.** Alla 39 registrerade obligationserbjudanden 2020–2026 finns, och varje slutligt prospekttillägg har samma tranchar som CSV:n |
| 4. Avstämning mot XBRL | **OK, med anmärkning.** Tabellen i källdokumentet stämmer. Avstämningen per kvartal saknas (R20-5). Tre av förklaringarna som stod som ej verifierade är nu verifierade |
| 5. Vikt, band, luckor och datering | **OK.** En oberoende omräkning ger samma 82 rader och samma `known_from`. Inget värde är daterat före kvartalets slut eller före en inlämning |
| 6. Licens för marknadsindex | **OK.** ICE BofA och Moody's förbjuder vidarespridning, och inget index används |
| 7. Text i git, hashar och självkontrollen | **OK, med anmärkning.** 239 av 239 hashar stämmer, och kontrollen ger 0 fel. Men den prövar inte talen i tranchens kolumn, som regeln säger (R20-1) |
| Kod som inte påverkar dagens rader | **Anmärkning.** Tre avvikelser från de låsta reglerna slår till först vid en ny ombyggnad (R20-2 till R20-4) |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Inga fel i värden eller datum och inget läckage. Registrets villkor för
granskningen är uppfyllt (minst 30 % av raderna, ett helt dokument per emittent, inga fel i talen). Rättningarna R-1 till
R-5 rör självkontrollen, tre kodvägar som dagens rader inte använder och avstämningen per kvartal. De ändrar inget värde
i dag, men de ska rättas före nästa ombyggnad av CSV:n, eftersom de då kan ändra värden. `publish=True` kräver en daterad
registerpost. R20 ändrar inte flaggan.

**Bedömning av allvar.** R20-1 till R20-5 är avvikelser från de låsta reglerna. Ingen av dem ändrar ett värde, ett datum
eller en rad i dag, och det är prövat. De klassas därför som should_fix, som R22-1. Vill orkestreraren läsa "en
registrerad regel som inte är genomförd som skriven" bokstavligt är R20-1 must_fix.

## 1. Ordning och förregistrering – OK

Tidslinje 2026-11-25 (UTC), ur git och filtider i den delade raw-katalogen:

| Tid | Händelse |
|---|---|
| 09:08:18 | `2bac788`: kodningsregler och registerpost. Inget dokument hämtat |
| 09:09:12 | Första hämtningen för källan `credit_issuance` (Microsofts submissions) |
| 09:11:01 | `documents.json`, 146 dokument |
| 09:19:52 | `675b2de`: korpus, parser och serielogik. Inga värden |
| 09:25:35 | `e5a6ad6` och `f41fe76` i samma sekund: parserrättningar, självkontroll och tester, sedan 239 rader |
| 09:31:07 | `7c38300`: kontroll mot omslagen, avstämningen bara över kvartal som XBRL har |
| 09:35:46 | Sista blockfilen skrivs (ombyggnad efter parserändringen i `dfbd813`) |
| 09:36:11 och 09:53:32 | `dfbd813` (parser och test) och `2f85ed8` (dokumentation) |

- Avsnittet "Kodningsregler" i `docs/kallor/kredit_emission.md` och registerposten är oförändrade sedan `2bac788`. Det
  enda som skiljer är en tom rad. Testerna låser båda med SHA-256.
- I den delade raw-katalogen finns inga FWP:er och inga 424B-dokument från före 09:08:18, ur någon källa.
- Parsern ändrades efter att värdena committats (`dfbd813`). R20 byggde om CSV:n med grenens kod ur sina egna nyhämtade
  dokument. Resultatet är byte för byte samma fil, så ändringen påverkar ingen rad.
- `7c38300` ändrade avstämningen (bara kvartal som XBRL har, kolumnen "senare") och accessionsnumret i den manuella
  raden. Det nya numret, `0001193125-21-091259`, är det slutliga 424B2 från 2021-03-23. Avstämningen är en rapport och
  ingen serie, och ändringen står i källdokumentet.
- **Kan parsern ha anpassats efter utfallet?** Nej, inte för serierna. En villkorsbilaga anger en enda spread mot
  statsobligationen för en tranche i USD med fast ränta. Parsern har inget att välja. Valen i tolkningarna 3–5 (CAD,
  EUR, rörlig ränta) gäller rader som inte ingår i någon spreadserie. Den manuella raden avgörs av ett oberoende
  dokument.
- Begränsning: git visar bara vad som committades, inte vad som lästes lokalt. Inget i filtiderna tyder på läsning före
  låsningen.

## 2. Korrekthet – OK

### Stickprov

Slumpat per emittent med seed 20261145, 30 % av raderna. Dessutom lästes ett helt dokument per emittent. I varje rad
prövades valuta, räntetyp, belopp, kupong, förfallodag, pris, avkastning, referensens namn och avkastning, spread,
referenstyp, prisdag och likviddag mot villkorsbilagan, och `filed` och `accepted` mot EDGAR.

| Bolag | Rader | Slumpat | Hela dokumentet, utöver stickprovet | Fel |
|---|---|---|---|---|
| Microsoft | 10 | 3 | 7 (2026-10-29) | 0 |
| Alphabet | 79 | 24 | 4 (2025-04-28) | 0 |
| Amazon | 68 | 20 | 6 (2021-05-10) | 0 |
| Meta | 33 | 10 | 4 (2023-05-01) | 0 |
| Oracle | 49 | 15 | 3 (2020-03-30) | 0 |
| **Summa** | **239** | **72 (30,1 %)** | **24** | **0** |

Felandel i stickprovet: 0 av 72, 95 % KI 0–5,0 % (Clopper–Pearson). De 96 rader som lästes för hand ger 0–3,8 %, men 24
av dem är inte slumpade.

**Alla rader.** Ett eget skript läste varje tal i varje rad i tranchens egen del av dokumentet: avsnittet för Oracles
layout, och för den gemensamma tabellen texten efter tranchens nyckel ("2031 Notes:") fram till nästa nyckel. 235 av 239
rader klarade det automatiskt. De fyra andra lästes för hand och är rätt: tre obligationer med rörlig ränta i egna
avsnitt utan nyckel (`amzn_2026-03-11_01`, `amzn_2026-07-07_01`, `googl_2026-11-02_01`) och den manuella raden. Det ger
0 fel av 239, KI 0–1,5 %. `filed`, `accepted`, formulär och primärdokument stämmer mot EDGAR i alla 239 rader.

### Semantik

- **Källan.** Varje erbjudande har en FWP med de slutliga villkoren, och den är källan. Rubrikens datum är prisdagen i 38
  av 39. Oracles villkorsbilaga 2021 har inget datum i rubriken, och prisdagen tas från "Trade Date". I 8 dokument är
  `filed` dagen efter prisdagen, eftersom de lämnades in efter 17.30 ET. Det är konservativt.
- **Valuta:** USD 172, EUR 38, CAD 13, GBP 9 och JPY 7. Stämmer med tecknen i dokumenten och med omslagen.
- **Räntetyp:** de 12 raderna med rörlig ränta är obligationer mot SOFR eller EURIBOR. Inga andra.
- **Referenstyp:** alla 162 rader i USD med fast ränta prissätts mot en namngiven amerikansk statsobligation. Det finns
  inga andra rader i USD med fast ränta.
- **Tolkning 2** (`col #j` är tranchens nummer bland nycklarna): i alla 186 rader med `col` är j platsen för tranchens
  nyckel i beloppsraden. Docstringen i korpusmodulen beskriver fortfarande kolumner (N-4).
- **Tolkning 3** (CAD): spreaden mot referensobligationen är spreaden mot kurvan plus en kurvjustering, till exempel
  +117,3 = +115 + 2,3. Avkastningen är referensens avkastning plus den spreaden. Valet stämmer med kolumnen `benchmark`.
  Ingen serie.
- **Tolkning 4** (EUR): mid-swaps är marknadens referens för obligationer i euro. Amazons villkorsbilagor anger också
  mid-swap-räntan, och den kodas inte (N-2). Ingen serie.
- **Tolkning 5** (rörlig ränta): marginalen kodas som den står, till exempel "plus 0.44% per annum" = 44 och "plus 35
  basis points" = 35.
- **Tolkning 6** (Oracle 2051): villkorsbilagan anger beloppet med en nolla för mycket. Omslaget på det slutliga 424B2
  (`0001193125-21-091259`) anger 3 250 MUSD för 3.950% Notes due 2051 och totalen 15 000 MUSD. Rätt.

## 3. Fullständighet – OK

R20 klassade alla 146 dokument själv: 47 FWP (39 villkorsbilagor för obligationer, en omregistrering, tre villkorsbilagor
för aktier och fyra pressmeddelanden) och 99 prospekttillägg (47 preliminära och 52 slutliga, varav 39 för obligationer
och 13 för aktier). Det är samma indelning som KR1:s.

| Bolag | Erbjudanden i korpusen | Tranchar på de slutliga omslagen | I CSV:n |
|---|---|---|---|
| Microsoft | 1: 2026-10-29 | 10 | 10 |
| Alphabet | 13: 2020-08-03, 2025-04-28, 2025-04-29, 2025-11-03 (EUR och USD), 2026-02-09, 2026-02-10, 2026-05-05 (EUR och CAD), 2026-05-15, 2026-08-06, 2026-11-02, 2026-11-19 | 79 | 79 |
| Amazon | 10: 2020-06-01, 2021-05-10, 2022-04-11, 2022-11-29, 2025-11-17, 2026-03-10, 2026-03-11, 2026-06-08, 2026-07-07, 2026-09-09 | 68 | 68 |
| Meta | 6: 2023-05-01, 2024-08-07, 2025-10-30, 2026-04-30, 2026-11-03, 2026-11-04 | 33 | 33 |
| Oracle | 9: 2020-03-30, 2021-03-22, 2022-11-07, 2023-02-02, 2024-09-25, 2025-01-30, 2025-09-24, 2026-02-02, 2026-11-02 | 49 | 49 |
| CoreWeave | 0 | – | – |

- Varje slutligt prospekttillägg för obligationer har exakt samma tranchar (valuta, belopp, kupong eller rörlig ränta,
  förfalloår) som sin FWP i CSV:n, och varje rad i CSV:n står på ett omslag. Paren är låsta i testet.
- **Utanför korpusen, enligt reglerna:** Microsofts 424B3 2020, 2021 och 2024 är utbyteserbjudanden. Metas 424B3
  2022-11-29 är utbytet av obligationerna från augusti 2022, som var oregistrerade. Amazons 424B3 2026-08-18 gäller köpet
  av Globalstar, och CoreWeaves 424B3 2025-09-26 gäller Core Scientific.
- **CoreWeave:** 8-K 2025-05-19 och 2025-07-21 beskriver obligationerna 2030 och 2031 som "private offering". Den enda
  424B5:an (2026-09-17) gäller aktier. Det stämmer med källdokumentet.

## 4. Avstämning mot XBRL – OK, med anmärkning

`python -m ai_tracker.sources.credit_issuance coverage` mot bastabellen ger samma tal som tabellen i källdokumentet, för
alla bolag och år.

**R20-5. Avstämningen per kvartal saknas.** Den låsta regeln säger "Också per kvartal med emission". Kommandot och
källdokumentet har bara år. R20 räknade per kvartal med emission (USD-tranchar efter likviddag i bolagets kvartal,
mittpunktsregeln, mot `debt_issued`):

| Bolag | Kvartal: andel |
|---|---|
| Amazon | 2020Q2 1,008; 2021Q2 0,999; 2022Q2 0,994; 2022Q4 1,002; 2025Q4 1,005; 2026Q1 0,692; 2026Q3 0,520 |
| Meta | 2023Q2 1,005; 2024Q3 1,007; 2025Q4 1,003; 2026Q2 1,004 |
| Oracle | 2020Q2 1,006; 2021Q2 1,004; 2022Q4 0,850; 2023Q1 1,007; 2024Q4 1,006; 2025Q1 1,005; 2025Q4 1,007; 2026Q1 0,938 |
| Alphabet | 2020Q3 1,014; 2025Q2 0,186; 2025Q4 0,659; 2026Q1 0,637; 2026Q3 0,862 |

I kvartal med bara obligationer i USD ligger andelen på 0,99–1,01. Det är en starkare kontroll än årstabellen. Amazons
0,95–0,99 per år kommer från annan upplåning i kvartal utan obligationer (N-7). Där andelen är låg finns obligationer i
annan valuta eller annan upplåning i samma kvartal.

**Förklaringar som stod som ej verifierade (N-6):**
- **Oracle 2022:** verifierat. 10-Q för kvartalet till 2022-08-31 beskriver lån under "Bridge Credit Agreement" och
  "Term Loan Credit Agreement" för köpet av Cerner. Kvartalet är `debt_issued_orcl` 2022Q3 = 20 046, utan någon
  obligation. Beloppet är inte avstämt post för post.
- **Oracle 2024:** verifierat. 10-Q för kvartalet till 2024-08-31 har "Proceeds from issuances of term loan credit
  agreements" 5 627, vilket är exakt `debt_issued_orcl` 2024Q3. Terminslånet togs 2024-06-10.
- **Microsoft 2023–2024:** verifierat i sak, inte i belopp. 10-Q per 2023-09-30 och 2023-12-31 säger att företagscertifikat
  var utgivna och utestående, och att ränteutgiften ökade av dem. Det finns ingen registrerad obligation. Beloppen per
  kvartal är inte avstämda.
- **Oracle 2026** (annan upplåning) är inte verifierat.

## 5. Vikt, löptidsband, luckor och datering – OK

- **Oberoende omräkning.** R20 räknade de elva serierna med egen kod ur CSV:n. Resultatet är samma 82 rader, samma
  värden och samma `known_from` som i KR1:s observationstabell. Samma omräkning finns som test mot grenens funktioner.
- **Vikt:** beloppet i MUSD. **Bandet:** 6,5 ≤ löptid < 12,5. Ingen tranche ligger inom 0,02 år från en gräns, så
  avrundningen av `tenor_years` avgör inget. Bandet har 52 av 162 tranchar.
- **Luckregeln:** inga nollrader. Alla elva nycklar står i `KNOWN_GAPS`. Serien per emittent kräver fyra kvartal, och de
  fyra emittenterna har det.
- **Datering.** Alla 239 tranchar lämnades in inom sitt kvartal. Därför är varje version känd dagen efter kvartalets
  slut, och ingen version är daterad tidigare. Ett test bygger om tabellen som den var känd på varje inlämningsdag,
  dagen före varje inlämning och dagen efter varje kvartal, med `as_of` = den dagen. Det ger exakt de versioner som är
  kända då. En inlämning dagen efter kvartalets slut kommer med i första versionen (test). Felet i R23-1 finns alltså
  inte här.
- **Aktualitet:** `max_age_days` = 1 100 och `lag_days` = 1 i alla elva, med skälet i noten. `issuance_msft_q` står i
  `KNOWN_STALE` till 2027-01-15, och första raden blir känd 2027-01-01.
- **Mixen:** 12 av 17 avslutade kvartal har en enda emittent. Källdokumentet säger det och drar ingen slutsats av den
  poolade serien. Ingen takt är räknad.
- N-5: `spread_issuers()` räknar också det oavslutade kvartalet 2026Q4. Det ändrar inget i dag: Meta har fyra avslutade
  kvartal och Microsoft ett.

## 6. Licens för marknadsindex – OK

R20 läste samma serienoter på FRED 2026-11-25. Noten för ICE BofA förbjuder återgivning utan skriftligt tillstånd och
säger att serien från april 2026 bara har tre år. Noten för Moody's förbjuder kopiering och vidarespridning utan
samtycke. Ingen kod och ingen serie läser ett index (test). Klassen `ja` kommer från den kurerade regeln (alla rader på
sec.gov) och SEC-regeln, och alla elva har `publish=False`.

## 7. Text i git, hashar och självkontrollen – OK, med anmärkning

- `data/` är gitignorerad. CSV:n har en enda not, den manuella radens skäl med tal och referenser. Kolumnerna
  `benchmark` och `security` har bara korta namn. Källdokumentet har bara korta ordalydelser ur dokumenten (några ord,
  som "Subject to Completion") och FRED:s licenstexter.
- Alla 239 block har lagrad SHA-256 i de nyhämtade dokumenten. KR1:s cachade kopior är identiska med de nyhämtade (39 av
  39).
- `python -m ai_tracker.credit_issuance_check --frac 1.0`, körd av R20 utan cache: "239 checked, 0 errors, 0 moved, 1
  manual".

**R20-1. Självkontrollen prövar inte talen i tranchens kolumn.** Den låsta regeln säger att varje tal ska stå "i blocket,
i kolumnen när den anges". `check_row()` söker i hela blocket. I den gemensamma tabellen är blocket hela tabellen, så
ett tal som hör till en annan tranche i samma erbjudande godkänns. För rader från parsern fångas ett sådant fel av
omtolkningen, men den använder samma parser och är inte oberoende. För en manuell rad prövas det inte alls. R20:s egen
kontroll per nyckel visar att inget tal i dag hör till fel tranche. Rättning: pröva talen i tranchens del (nyckeln för
`col #j`), eller logga i registret, med datum, att kolumnkontrollen ersätts av omtolkningen och en oberoende kontroll.

## Kod som inte påverkar dagens rader

- **R20-2. Dokument som inte kodas listas inte, och prospekttillägget används aldrig som källa.** Regeln säger att det
  slutliga prospekttillägget är källan när det inte finns någon FWP, och att dokument som inte kodas "listas med skäl".
  `rows_from_documents()` läser bara FWP:er och hoppar över allt annat utan att lista det. `--covers` prövar bara från
  CSV:n till prospekttilläggen, inte tvärtom. Ett erbjudande utan FWP skulle därför försvinna utan att någon kontroll
  märker det. I dag har alla 39 erbjudanden en FWP (punkt 3). Källdokumentet namnger dessutom bara fyra av de åtta
  FWP:er som inte kodas. Pressmeddelandena (Alphabet 2026-06-01 och 2026-06-03, Meta 2026-10-26, Oracle 2026-02-02) och de
  47 preliminära prospekttilläggen står bara som antal.
- **R20-3. T+n räknar helgdagar som bankdagar.** Regeln säger att likviddagen är n vardagar efter prisdagen, utan lördag,
  söndag och helgdagar. `add_business_days()` hoppar bara över helger. T+2 från 2026-12-23 blir juldagen. Ingen rad
  använder regeln i dag: alla 239 likviddagar står i dokumenten.
- **R20-4. CSV:n skrivs med sex värdesiffror.** `write()` formaterar talen med `:g`. Ett belopp på 1 234 567 miljoner yen
  blir 1 234 570, och priset 99,12345 blir 99,1235. Regeln säger "utan avrundning". Inget tal i dag har fler än sex
  värdesiffror (R20:s kontroll av alla tal mot dokumenten).

## 8. Publicering och kärnserie

- Registrets villkor för granskningen är uppfyllt: 72 slumpade rader (30,1 %), ett helt dokument per emittent och inga
  fel i talen. `publish=True` kräver en daterad registerpost. R20 ändrar inte flaggan.
- Rekommendation: volymerna och serierna per emittent kan publiceras efter registerposten. Den poolade serien bör bara
  visas med noten om mixen, eller vänta tills en regel för mixen är registrerad.
- Kärnserie: nej i den här körningen. Registret kräver en registrerad regel för mixen.

## Rättningar

| Nr | Fynd | Allvar | Rättning | Test (xfail tills rättat) |
|---|---|---|---|---|
| R-1 | R20-1 | should_fix | Pröva varje tal i tranchens del av blocket: nyckelns text för `col #j` i den gemensamma tabellen, kolumnen för en verklig kolumntabell. Alternativt en daterad registerpost som ersätter kolumnkontrollen med omtolkningen och en oberoende kontroll per nyckel | `test_r20_1_self_check_looks_in_the_tranches_column` |
| R-2 | R20-2 | should_fix | Lista varje dokument som inte kodas, med skäl, i `skipped`. Lägg till den omvända kontrollen: varje slutligt prospekttillägg för obligationer ska ha en källa i CSV:n, annars kodas det som källa. Lägg en tabell i källdokumentet med de åtta FWP:er som inte kodas (accession, dag, skäl) | `test_r20_2_documents_not_coded_are_listed_with_a_reason` |
| R-3 | R20-3 | should_fix | Räkna T+n med en kalender för valutans helgdagar (för USD den federala), eller låt parsern lämna likviddagen tom så att raden kodas för hand med en not | `test_r20_3_t_plus_n_skips_holidays` |
| R-4 | R20-4 | should_fix | Skriv talen utan avrundning, till exempel med `repr` eller `format(x, ".15g")` | `test_r20_4_csv_writer_does_not_round` |
| R-5 | R20-5 | should_fix | Lägg till avstämningen per kvartal med emission i `coverage` och en tabell i källdokumentet (R20:s tabell i punkt 4 går att använda) | `test_r20_5_coverage_is_also_reported_per_quarter` |

Anmärkningar utan rättning:

- N-1: Id-numret räknas vidare över två dokument med samma prisdag (Alphabet 2025-11-03 och 2026-05-05). USD-dokumentet
  2025-11-03 börjar därför på `_07`, inte på tranchens ordning i dokumentet. Id:na är unika. Skriv det som en tolkning.
- N-2: Amazons sju tranchar i euro med fast ränta har en angiven mid-swap-ränta som inte kodas. Kolumnregeln säger "om
  den står", och tolkning 4 säger "utan referensens avkastning". Ingen serie påverkas.
- N-3: Docstringen för `kind()` säger att den bara sållar, men `rows_from_documents()` använder den som filter. R20
  prövade att den behåller alla 39 villkorsbilagor för obligationer och bara tar bort de åtta andra.
- N-4: Korpusmodulens docstring beskriver `col #j` som en tabellkolumn. Tolkning 2 använder det för nyckelns nummer.
- N-5: se punkt 5.
- N-6: se punkt 4. Uppdatera tabellen i källdokumentet för Oracle 2022 och 2024 och för Microsoft.
- N-7: Meningen "Där bolaget bara har registrerade obligationer stämmer det … Amazon på 0,95–0,99" blir tydligare per
  kvartal (0,99–1,01 i kvartal med bara obligationer i USD).
- N-8: Commit-meddelandet i `f41fe76` säger 48 villkorsbilagor. Det är 39, och källdokumentet har rätt antal.

## Vad som inte kunde verifieras

- Git och filtiderna visar inte vad agenten läste lokalt före låsningen.
- Microsofts företagscertifikat och Oracles övriga upplåning 2026 är inte avstämda i belopp mot `debt_issued`.
- Yenobligationernas "Reference Rate" namnges inte i villkorsbilagan. Raderna ingår inte i någon serie.
- Privata placeringar, 144A, SPV och lån har inga villkorsbilagor på EDGAR. Granskningen kan bara bekräfta att de inte
  ingår, inte hur stora de är.
- Kreditbetygen i källdokumentet (AAA till BBB) är lästa i Microsofts villkorsbilaga 2026 och Oracles 2025, inte i alla.
