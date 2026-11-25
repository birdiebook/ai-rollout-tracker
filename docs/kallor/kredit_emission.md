# Källa: spread vid emission för AI-tunga emittenter (spår KR1)

Spår KR1, körning 14, 2026-11-25. Byggt och kontrollerat mot riktiga data samma dag. Kreditpriset för de bolag som bär AI-utbyggnaden, som spreaden mot statsobligationen
när obligationen emitteras. Projektet har redan volymerna (`debt_issued_<bolag>`, `debt_repaid_<bolag>`, leasing,
[finansiering.md](finansiering.md)), men inget pris. Spreaden vid emission är ett pris, och den står i de offentliga
villkorsbilagorna (pricing term sheets) på EDGAR. Bara extraktion och katalogserier. Inga takter och inga jämförelser.

Avsnittet "Kodningsregler" skrevs och committades **innan** något dokument i korpusen hämtades eller någon tranche
kodades. Före låsningen hade agenten sett två saker. (1) Antalet inlämningar per bolag, år och formulär (FWP, 424B2,
424B3, 424B4, 424B5, S-3, S-3ASR) ur EDGAR:s submissions-index, alltså formulärtyp och inlämningsdag, inget innehåll.
(2) Licenstexten i FRED:s serienoter för de möjliga marknadsindexen (avsnittet "Jämförelse med marknaden"), inga
värden. Agenten känner till de stora emissionerna 2020–2025 ur allmän rapportering (Oracle 2020, Amazon 2021, Meta
2022–2025, Alphabet 2025) och villkorsbilagornas vanliga form, men hade inte läst något dokument i korpusen. Tolkningar
som behövs under kodningen skrivs i ett eget avsnitt och skrivs inte in i reglerna i efterhand. Parsern skrivs efter
låsningen, mot dokumenten. En ändring av parsern är ingen regeländring, men den syns i git.

Kod: `src/ai_tracker/sources/credit_issuance_corpus.py` (korpus, radlista, plats och hash),
`src/ai_tracker/sources/credit_terms.py` (parsern), `src/ai_tracker/sources/credit_issuance.py` (CSV, kontroll vid
inläsning, serier, avstämning), `src/ai_tracker/series/credit_issuance.py` (katalogposter),
`src/ai_tracker/credit_issuance_check.py` (självkontroll). Data: `curated/credit_issuance.csv` (committad, bara siffror
och referenser) och `curated/credit_issuance_skipped.csv` (dokumenten i korpusen som inte kodas, med skäl). Tester:
`tests/test_credit_issuance.py` (syntetiska villkorsbilagor, inget nät), `tests/test_r20_kredit_emission.py`
(granskningen R20) och `tests/test_x17_kredit_emission.py` (rättningen X17). Ordningen i git: reglerna och
registerposten (2bac788), koden utan värden (675b2de), parserrättningar och självkontrollen (e5a6ad6), därefter de
kodade värdena (f41fe76). Rättningen efter R20: registerposten X17 (b2aaea5), koden (1b992f1), sedan ombyggnaden.

    python -m ai_tracker.sources.credit_issuance_corpus     # hämtar korpusen, data/raw/credit_issuance_corpus/
    python -m ai_tracker.sources.credit_issuance build      # tolkar dokumenten, skriver de två CSV:erna och blocken
    python -m ai_tracker.credit_issuance_check              # självkontroll mot nyhämtade dokument
    python -m ai_tracker.credit_issuance_check --covers     # erbjudandena mot de slutliga prospekttilläggen, båda hållen
    python -m ai_tracker.sources.credit_issuance coverage   # täckningsgrad mot debt_issued_<bolag>, per år och kvartal

## Kodningsregler (låsta 2026-11-25, före kodningen)

### Korpus

- **Emittenter:** Microsoft (msft, CIK 789019), Alphabet (googl, 1652044), Amazon (amzn, 1018724), Meta (meta,
  1326801), Oracle (orcl, 1341439) och CoreWeave (crwv, 1769628). Samma CIK som i `series/sec_finansiering.py`.
- **Dokument:** primärdokumentet i varje inlämning med formuläret FWP, 424B2 eller 424B5 och EDGAR:s `filingDate`
  2020-01-01–2026-11-25. 424B3 (återförsäljning, utbyte), 424B4 (börsnotering), S-3, S-3ASR, S-4 och 8-K ingår inte.
- **Slutliga villkor.** Ett dokument kodas bara om det anger de slutliga villkoren för minst en tranche: belopp, kupong
  eller ränta, förfallodag och pris till investerare. Ett preliminärt prospekttillägg ("Subject to Completion") och en
  FWP utan slutliga villkor (presentation, aktieerbjudande, annat) kodas inte. De listas med skäl.
- **Ett erbjudande, en källa.** Ett erbjudande är emittent och prisdag med sina tranchar (kupong och förfallodag).
  Finns en FWP med de slutliga villkoren är den källan. Annars är det slutliga prospekttillägget (424B2 eller 424B5)
  källan. Ett senare dokument om samma tranche kodas inte, men det används i självkontrollen.

### Text och plats

- Texten är radlistan `credit_issuance_corpus.lines(html)`: varje tabellrad blir en rad med cellerna åtskilda av
  " | ", varje block (stycke, rubrik, radbrytning) blir en egen rad, blanktecken slås ihop, och tomma rader tas bort.
  Raderna räknas från 0.
- **Plats** = `lines #a-#b`, tranchens block i radlistan: från tranchens första rad med ett villkor (eller rubriken)
  till den sista. När trancherna står som kolumner i en gemensam tabell är blocket hela tabellen, och platsen får
  tillägget ` col #j` (tranchens kolumn bland värdekolumnerna, från 0).
- **SHA-256** räknas av blockets rader, var och en normaliserad, sammanfogade med radbrytning (`block_hash`).

### Rader i `curated/credit_issuance.csv`

En rad per tranche. Alla tal i en rad ska stå i blocket som platsen pekar på (i kolumnen när den anges), utom
`tenor_years` (räknas) och, när det står så nedan, ett datum som räknas fram.

| Kolumn | Innehåll |
|---|---|
| `id` | `<bolag>_<prisdag>_<nn>`, nn = tranchens ordning i dokumentet från 01 |
| `company` | bolagets kod ovan |
| `currency` | ISO-kod som det står ("$" = USD, "€" = EUR) |
| `rate_type` | `fixed` eller `floating` |
| `security` | tranchens namn som det står, kort ("4.700% Notes due 2034") |
| `principal` | belopp i miljoner av valutan ("$1,250,000,000" och "$1.25 billion" = 1 250) |
| `pricing_date` | "Trade Date" eller "Pricing Date". Saknas den: datumet i dokumentets rubrik. Saknas också det: `filed`, och noten säger det |
| `settlement_date` | "Settlement Date" som det står. Står bara "T+n": n vardagar efter prisdagen (lördag och söndag räknas inte, helger inte heller), och noten säger det |
| `maturity` | förfallodagen som den står |
| `tenor_years` | (maturity − pricing_date) i dagar / 365,25, två decimaler. Räknas av koden och kontrolleras vid inläsning |
| `coupon_pct` | kupong i procent per år för fast ränta. Tom för rörlig ränta |
| `benchmark` | referensen som den står, kort ("UST 4.250% due November 15, 2034", "Compounded SOFR") |
| `benchmark_type` | `treasury` (amerikansk statsobligation), `sofr`, `mid_swaps` eller `other` |
| `benchmark_yield_pct` | referensens avkastning i procent, om den står |
| `spread_bp` | spreaden mot referensen i baspunkter som den står ("T+45 bps", "+45 basis points", "+0.45%" = 45). Räknas aldrig fram. Tom om den inte står |
| `yield_pct` | emissionens avkastning till förfall (re-offer yield) som den står |
| `price_pct` | pris till investerare i procent av nominellt belopp |
| `filed`, `accepted` | EDGAR:s `filingDate` (= known_from) och `acceptanceDateTime` |
| `form`, `source_url`, `accession` | formulär (FWP, 424B2, 424B5), dokumentets arkivadress och accessionsnummer |
| `locator`, `block_sha256` | plats och hash, se ovan |
| `method` | `parser` (den deterministiska tolkningen) eller `manual` (agenten kodade för hand, noten säger varför) |
| `note` | kort not utan citat |

Blocket sparas bara under `data/raw/credit_issuance_blocks/<id>.txt` (gitignorerad). Inget citat i git.

### Tal

- Belopp, kupong, avkastning, spread och pris kodas som de står, utan avrundning och utan beräkning.
- Ett belopp i en annan valuta räknas inte om till USD.
- Spread anges i baspunkter. "+0.45%" eller "0.45 percent" blir 45. En spread som bara går att räkna fram (avkastning
  minus referensens avkastning) kodas inte.

### Inte kodat

- Företagscertifikat, banklån, terminslån och kreditfaciliteter. De har inga villkorsbilagor på EDGAR.
- Privata placeringar, 144A-obligationer och finansiering i SPV eller projektbolag (till exempel Metas finansiering av
  Hyperion 2025). De registreras inte, så de finns inte i korpusen.
- Konvertibla skuldebrev, aktier och preferensaktier: de prissätts inte som en spread mot statsobligationen.
- Utbyteserbjudanden, remarketing och prospekt för återförsäljning.

### Serier (katalog, gren G5, kvartal)

- **`issuance_<bolag>_q`:** summan av `principal` (MUSD) för tranchar i USD, med fast och rörlig ränta, med prisdag i
  kalenderkvartalet. Bara för bolag med minst en tranche i USD.
- **`spread_issue_ai_q`:** principalvägt medelvärde av `spread_bp` över alla tranchar som är i USD, har fast ränta,
  har `benchmark_type` = `treasury` och har en angiven spread, med prisdag i kvartalet, över alla emittenter. Vikten är
  `principal` (MUSD). Enhet bp.
- **`spread_issue_ai_7_12y_q`:** samma, bara tranchar vars löptid avrundad till hela år är 7–12 (6,5 ≤ `tenor_years`
  < 12,5). Det kontrollerar för löptidsmixen.
- **`spread_issue_<bolag>_q`:** samma per emittent, bara för en emittent med minst fyra kvartal med en sådan tranche i
  korpusen.
- **Luckregeln.** Ett kvartal utan någon tranche som uppfyller villkoren har inget värde. Det är en lucka, inte noll.
  Alla serier står i `KNOWN_GAPS`.
- **Datering (läckagekritiskt).** Värdet för kvartal q dateras till max(dagen efter kvartalets slut, senaste `filed`
  bland trancherna som ingår). En tranche i q som lämnas in efter det datumet ger en ny version, daterad till sin
  inlämning. Ett kvartal som inte är slut på hämtningsdagen har inget värde.
- `lag_days` = 1. Emission är oregelbunden, så `max_age_days` = 1 100 (tre år), med skälet i noten.
- **Publicering:** `publish=False` tills extraktionsgranskningen har godkänt. Klass för kommersiell användning: den
  kurerade regeln (alla rader på sec.gov) och SEC:s villkor, alltså `ja` om alla rader kommer från sec.gov.
- **Inte kärnserier.** De ingår inte i grenarnas tillstånd, diffusionsindex eller takter.

### Avstämning mot XBRL (rapport, ingen serie)

- **Täckningsgrad** per bolag och kalenderår: summan av `principal` för USD-tranchar, placerade i bolagets
  räkenskapskvartal efter `settlement_date` och mappade till kalenderkvartal med mittpunktsregeln
  (`docs/kallor/sec.md`), delad med summan av `debt_issued_<bolag>` (senaste versionen) för samma kvartal. Också per
  kvartal med emission. `python -m ai_tracker.sources.credit_issuance coverage`.
- **Väntade skillnader:** `debt_issued` är likviden (efter rabatt och kostnader, cirka 99 % av beloppet). Taggarna
  omfattar också företagscertifikat med löptid över tre månader (Microsoft), terminslån och kreditfaciliteter (Oracle),
  annan upplåning (Alphabet), 144A-obligationer och skuld i annan valuta. Likviden kommer på likviddagen, inte
  prisdagen.

### Jämförelse med marknaden

Kontrollerat 2026-11-25 i FRED:s serienoter (`fred.stlouisfed.org/series/<id>`, bara licenstexten lästes):
- **ICE BofA** (BAMLC0A0CM, BAMLC4A0C710Y, BAMLC0A4CBBB): "Reproduction of this data in any form is prohibited except
  with the prior written permission of ICE Data Indices", och nyckeltalen ges "for your internal use only". Från april
  2026 visar FRED bara tre år.
- **Moody's** (AAA, BAA): "MOODY'S INFORMATION MAY NOT BE COPIED OR OTHERWISE REPRODUCED, REPACKAGED, FURTHER
  TRANSMITTED, ... BY ANY PERSON WITHOUT MOODY'S PRIOR WRITTEN CONSENT."
- Båda förbjuder vidarespridning (klass `nej`), och en kopia från FRED är `okänd` enligt projektets regel
  ([licensniva.md](../datakallor/licensniva.md)). **Inget marknadsindex läggs till.** Statsräntans nivå behövs inte
  för den angivna spreaden och läggs inte heller till. Behövs den senare: Federal Reserve H.15 eller treasury.gov
  (public domain).

### Självkontroll

`python -m ai_tracker.credit_issuance_check` hämtar om källdokumentet för varje rad (utan cache, alla rader som
standard, eftersom dokumenten är få) och kontrollerar:
- att blocket på platsen har lagrad SHA-256 (annars söks dokumentet igenom, "moved");
- att varje tal i raden står i blocket, i kolumnen när den anges;
- att parsern ger samma värden ur blocket (rader med `method` = `parser`);
- att `filed` och `accepted` stämmer med EDGAR:s submissions;
- att avkastningen stämmer med referensens avkastning plus spreaden, inom 1 bp, när alla tre står.

Kontrollen bekräftar plats, tal och datum, inte semantiken (vilket dokument som är källan, valuta och referens). Det
är för den oberoende granskningen.

### Beslutsregler

- **Publicering:** `publish=True` först efter en oberoende extraktionsgranskning (minst 30 % av raderna och minst ett
  dokument per emittent) utan fel i talen, och med en daterad registerpost.
- **Kärnserie:** inte i den här körningen. Ett förslag kräver godkänd granskning, minst 12 kvartal med värden i
  `spread_issue_ai_7_12y_q` och en registrerad regel för emittentmixen.
- **Ingen takt** räknas i spåret.

### Tester (syntetiska villkorsbilagor, inget nät)

Parsern (en tranche per tabell och flera tranchar som kolumner), belopp i dollar och miljarder, spread som "T+45",
"+45 bps" och "+0.45%", löptid, bandets gränser (6,49 utanför, 6,5 innanför, 12,49 innanför, 12,5 utanför),
vägningen, luckregeln, rörlig ränta och euro (med i volymen respektive utanför, utanför spreaden), dateringen (sen
inlämning ger en ny version, ett kvartal som inte är slut ger inget värde), CSV-kontrollen och självkontrollen med
falska dokument.

## Tolkningar under kodningen (inte en del av de låsta reglerna)

Följande fall täcktes inte uttryckligen av reglerna. Valet står här så att granskningen kan pröva det. Inget av dem
ändrar en serie, utom punkt 6, som ändrar ett belopp (volymen och vikten i spreaden).

1. **Tre layouter.** Amazon, Alphabet, Meta och Microsoft har en gemensam tabell där varje fält räknar upp trancherna
   med namn ("2030 Notes: …"). Oracle har ett avsnitt per tranche. En obligation med rörlig ränta står ofta i ett eget
   avsnitt i en annars gemensam tabell. Kolumner per tranche förekom inte, men parsern hanterar dem.
2. **`col #j` i en gemensam tabell** är tranchens nummer bland namnen (från 0), inte en tabellkolumn. Blocket är
   tabellen från den första till den sista rad som någon tranche använder. Ett avsnitt har eget block, och blocket
   omfattar också raderna med prisdag och likviddag när de står utanför avsnittet.
3. **Kanadensiska dollar** anger två spreadar, mot Government of Canada-kurvan och mot referensobligationen. Kolumnen
   `benchmark` och dess avkastning gäller obligationen, så spreaden mot obligationen kodas (till exempel 51,6 bp i
   stället för 50). Det gäller 13 rader i CAD, som inte ingår i någon serie.
4. **Euro** anger spread både mot mid-swaps och mot den tyska statsobligationen. Mid-swaps kodas
   (`benchmark_type` = `mid_swaps`, utan referensens avkastning). Pund anger spread mot en gilt, och yen en spread mot en
   referensränta som inte namnges i fältet (`other`). Ingen av dem ingår i någon serie.
5. **Rörlig ränta:** `spread_bp` är marginalen över SOFR eller EURIBOR som den står ("plus 0.52% per annum" = 52).
   Raderna ingår i volymen (USD) men inte i spreaden.
6. **Oracles 3.950% Notes due 2051 (2021)** står som "$3,250,000,0000" i villkorsbilagan, alltså en nolla för mycket.
   Det slutliga prospekttillägget (0001193125-21-091259, inlämnat samma dag) anger $3,250,000,000 och totalen
   $15,000,000,000. Raden är kodad för hand med 3 250 (`method` = `manual`). known_from påverkas inte.
7. **Omregistrerad FWP.** Alphabets FWP 2020-08-04 är samma villkorsbilaga som den 2020-08-03 ("re-filed solely
   for…"). Den tidigare räknas, och den senare hoppas över.
8. **Aktier.** Tre "Pricing Term Sheet" gäller aktier och obligatoriskt konvertibla preferensaktier (Oracle
   2026-02-03, Alphabet 2026-06-03, Meta 2026-10-27). De kodas inte (regeln "Inte kodat").
9. **Alla erbjudanden hade en FWP.** Därför är alla 39 källor FWP:er, och de slutliga prospekttilläggen används bara
   i kontrollen (`--covers`). Sedan X17 prövar ombyggnaden och `--covers` det också åt andra hållet (se "Rättning
   efter R20").

Tillagda 2026-11-25 efter granskningen R20 (de beskriver hur koden redan gjorde, inget värde ändras):

10. **Id över två dokument med samma prisdag.** Numret i `id` räknas per bolag och prisdag, i inlämningsordning. Har
    två dokument samma prisdag (Alphabet 2025-11-03 i EUR och USD, 2026-05-05 i EUR och CAD) fortsätter det andra
    dokumentets nummer där det första slutade. Dollardokumentet 2025-11-03 börjar därför på `_07`. Id:na är unika (N-1).
11. **Amazons mid-swap-ränta i euro.** Amazons sju tranchar i euro med fast ränta anger också mid-swap-räntan. Den
    kodas inte, eftersom tolkning 4 kodar mid-swaps utan referensens avkastning. Raderna ingår inte i någon serie (N-2).
12. **Fyra kvartal för en egen spreadserie** räknas i korpusen, alltså också det kvartal som inte är slut (2026Q4).
    Det ändrar inget i dag: Meta har fyra avslutade kvartal och Microsoft ett (N-5).

## Resultat

### Korpus och rader

- **Korpus:** 146 dokument från 2020-01-01 till 2026-11-25: 47 FWP, 43 424B2 och 56 424B5. Av FWP:erna har 39
  slutliga villkor för obligationer, en är en omregistrering av en av dem (tolkning 7) och sju gäller annat
  (pressmeddelanden och aktier, tolkning 8). Av prospekttilläggen är 47 preliminära och 52 slutliga (obligationer eller
  aktier). Varje obligationserbjudande hade en FWP, och vart och ett har ett slutligt prospekttillägg (`--covers`).
- **Rader:** 239 tranchar ur 39 villkorsbilagor. 238 med `method` = `parser` och en `manual` (tolkning 6).
- **Dokument som inte kodas** (107) står med skäl i `curated/credit_issuance_skipped.csv`: 47 preliminära
  prospekttillägg, 39 slutliga prospekttillägg till ett erbjudande med en FWP som källa, 13 prospekttillägg för aktier
  (11 utan slutliga villkor för skuld, 2 utan obligationer på omslaget) och åtta FWP:er:

| Bolag | Inlämnad | Accession | Skäl |
|---|---|---|---|
| Alphabet | 2020-08-04 | 0001193125-20-208486 | omregistrering av 0001193125-20-208301 (tolkning 7) |
| Oracle | 2026-02-02 | 0001193125-26-032650 | pressmeddelande om finansieringsplanen för 2026 |
| Oracle | 2026-02-03 | 0001193125-26-034351 | villkorsbilaga för obligatoriskt konvertibla preferensaktier |
| Alphabet | 2026-06-01 | 0001193125-26-251733 | pressmeddelande om aktieemissionen |
| Alphabet | 2026-06-03 | 0001193125-26-254474 | villkorsbilaga för aktier och obligatoriskt konvertibla preferensaktier |
| Alphabet | 2026-06-03 | 0001193125-26-254490 | pressmeddelande om prissättningen av aktieemissionen |
| Meta | 2026-10-26 | 0001193125-26-431036 | pressmeddelande om aktier och konvertibla preferensaktier |
| Meta | 2026-10-27 | 0001193125-26-432549 | villkorsbilaga för aktier och obligatoriskt konvertibla preferensaktier |

  Koden ger skälet "no final debt terms" för de sju sista. Beskrivningen här kommer från dokumentens första rader.

| Bolag | Dokument | Tranchar | USD fast ränta | USD rörlig | Annan valuta |
|---|---|---|---|---|---|
| Microsoft | 1 | 10 | 8 | 2 | – |
| Alphabet | 13 | 79 | 32 | 3 | 44 (EUR 24, CAD 8, GBP 5, JPY 7) |
| Amazon | 10 | 68 | 48 | 3 | 17 (EUR 8, CAD 5, GBP 4) |
| Meta | 6 | 33 | 27 | – | 6 (EUR) |
| Oracle | 9 | 49 | 47 | 2 | – |
| CoreWeave | 0 | 0 | – | – | – |

- 162 tranchar ingår i spreadserierna (USD, fast ränta, statsobligation som referens). 52 av dem har löptid 7–12 år.
- **Annan valuta** (i miljoner av valutan, ingår i ingen serie): Alphabet 2025 EUR 13 250; 2026 EUR 15 000, CAD
  14 500, GBP 5 500, JPY 576 500. Amazon 2026 EUR 14 500, CAD 14 000, GBP 4 250. Meta 2026 EUR 9 000.

### Självkontroll

Körd 2026-11-25 mot nyhämtade dokument (`credit_issuance_check`, alla rader): 239 kontrollerade, 0 fel, 0 flyttade,
1 manuell. Blocket har lagrad hash, talen står i blocket, parsern ger samma värden, datumen stämmer med EDGAR, och
avkastningen är referensens avkastning plus spreaden inom 1 bp för alla rader där alla tre står. Den manuella raden
har beloppet utanför blocket, som noten säger.

Kontrollen mot de slutliga prospekttilläggen (`--covers`): alla 39 erbjudanden har samma tranchar (valuta, belopp,
kupong eller rörlig ränta, förfalloår) som omslaget på det slutliga 424B2 eller 424B5. Det är ett oberoende dokument,
så kontrollen prövar också villkorsbilagan själv (den hittade nollan i tolkning 6).

Kontrollen prövar inte semantiken: att rätt dokument är källan, valuta, referens och räntetyp. Det är för den
oberoende granskningen.

Efter rättningen X17 (talen i tranchens del av blocket, se nedan), körd 2026-11-25 mot nyhämtade dokument: 239
kontrollerade, 0 fel, 0 flyttade, 1 manuell (samma belopp som förut). `--covers` åt båda hållen: 39 av 39 erbjudanden
har samma tranchar som sitt slutliga prospekttillägg, och alla 39 slutliga prospekttillägg för obligationer i korpusen
har en källa i CSV:n.

### Täckning mot XBRL (`debt_issued_<bolag>`)

Belopp i USD-tranchar efter likviddag i bolagets räkenskapskvartal, mot `debt_issued` (senaste versionen), MUSD.
Andel = villkorsbilagor / XBRL. 2026 har tre kvartal i XBRL. Det som ännu inte finns i XBRL (2026Q4) står i kolumnen
"senare".

| Bolag | År | Villkorsbilagor | XBRL | Andel | Senare | Skillnaden |
|---|---|---|---|---|---|---|
| Microsoft | 2023 | 0 | 17 846 | 0 | – | ingen registrerad obligation; företagscertifikat (R20: 10-Q per 2023-09-30 och 2023-12-31, beloppen inte avstämda) |
| Microsoft | 2024 | 0 | 6 549 | 0 | – | som 2023 |
| Microsoft | 2026 | 0 | 0 | – | 25 000 | emissionen 2026-10-29 kommer i 10-Q för 2026Q4 |
| Alphabet | 2020 | 10 000 | 11 761 | 0,85 | – | annan upplåning i taggen (finansiering.md) |
| Alphabet | 2021–2024 | 0 | 20 199 / 52 872 / 10 790 / 13 589 | 0 | – | ingen obligation; annan upplåning |
| Alphabet | 2025 | 22 500 | 64 564 | 0,35 | – | euro (13 250 EUR) och annan upplåning |
| Alphabet | 2026 | 45 000 | 85 222 | 0,53 | – | EUR, CAD, GBP och JPY ingår inte |
| Amazon | 2020 / 2021 / 2022 | 10 000 / 18 500 / 21 000 | 10 525 / 19 003 / 21 166 | 0,95 / 0,97 / 0,99 | – | likvid mot nominellt och annan långfristig upplåning |
| Amazon | 2025 | 15 000 | 15 673 | 0,96 | – | som ovan |
| Amazon | 2026 | 62 000 | 115 100 | 0,54 | – | EUR, CAD och GBP ingår inte, och annan upplåning |
| Meta | 2022 | 0 | 9 921 | 0 | – | obligationerna i augusti 2022 var 144A med registreringsrätt; utbytet registrerades 2022-11-29 (424B3, utanför korpusen) |
| Meta | 2023 / 2024 / 2025 | 8 500 / 10 500 / 30 000 | 8 455 / 10 432 / 29 906 | 1,01 / 1,01 / 1,00 | – | likvid efter rabatt |
| Meta | 2026 | 25 000 | 24 910 | 1,00 | 15 000 | november 2026 i 2026Q4 |
| Oracle | 2020 / 2021 | 20 000 / 15 000 | 19 888 / 14 934 | 1,01 / 1,00 | – | likvid efter rabatt |
| Oracle | 2022 | 7 000 | 28 280 | 0,25 | – | brygglån och terminslån för köpet av Cerner (R20: 10-Q till 2022-08-31; 2022Q3 = 20 046 utan obligation) |
| Oracle | 2023 | 5 250 | 5 214 | 1,01 | – | |
| Oracle | 2024 | 6 250 | 11 837 | 0,53 | – | terminslån (R20: 10-Q till 2024-08-31, 5 627 = `debt_issued_orcl` 2024Q3) |
| Oracle | 2025 | 25 750 | 25 591 | 1,01 | – | |
| Oracle | 2026 | 25 000 | 28 213 | 0,89 | 10 000 | annan upplåning (ej verifierat); november 2026 i Oracles kvartal sep–nov |
| CoreWeave | 2024–2026 | 0 | 7 018 / 11 820 / 27 048 | 0 | – | lån och 144A-obligationer (se nedan) |

Per år stämmer det där bolaget bara har registrerade obligationer: Meta 2023–2025 och Oracle 2020, 2021, 2023 och 2025
ligger på 1,00–1,01. Amazons 0,95–0,99 per år kommer från annan upplåning i kvartal utan obligationer (N-7). Andelen
över 1 är rabatt och kostnader (likviden är lägre än det nominella beloppet).

**Per kvartal med emission** (R20-5, regeln "också per kvartal med emission"). Samma belopp, i det kvartal där
likviddagen ligger. Andel med tre decimaler. Räknat 2026-11-25 med `coverage` och lika med R20:s egen tabell.

| Bolag | Kvartal | Villkorsbilagor | XBRL | Andel | Senare | Skillnaden |
|---|---|---|---|---|---|---|
| Microsoft | 2026Q4 | – | – | – | 25 000 | inte i XBRL än |
| Alphabet | 2020Q3 | 10 000 | 9 863 | 1,014 | – | |
| Alphabet | 2025Q2 | 5 000 | 26 846 | 0,186 | – | EUR 6 750 samma kvartal och annan upplåning |
| Alphabet | 2025Q4 | 17 500 | 26 562 | 0,659 | – | EUR 6 500 samma kvartal och annan upplåning |
| Alphabet | 2026Q1 | 20 000 | 31 379 | 0,637 | – | GBP 5 500 samma kvartal och annan upplåning |
| Alphabet | 2026Q3 | 25 000 | 28 996 | 0,862 | – | annan upplåning |
| Amazon | 2020Q2 | 10 000 | 9 918 | 1,008 | – | |
| Amazon | 2021Q2 | 18 500 | 18 516 | 0,999 | – | |
| Amazon | 2022Q2 | 12 750 | 12 824 | 0,994 | – | |
| Amazon | 2022Q4 | 8 250 | 8 235 | 1,002 | – | |
| Amazon | 2025Q4 | 15 000 | 14 927 | 1,005 | – | |
| Amazon | 2026Q1 | 37 000 | 53 441 | 0,692 | – | EUR 14 500 samma kvartal |
| Amazon | 2026Q3 | 25 000 | 48 102 | 0,520 | – | GBP 4 250 samma kvartal och annan upplåning |
| Meta | 2023Q2 | 8 500 | 8 455 | 1,005 | – | |
| Meta | 2024Q3 | 10 500 | 10 432 | 1,007 | – | |
| Meta | 2025Q4 | 30 000 | 29 906 | 1,003 | – | |
| Meta | 2026Q2 | 25 000 | 24 910 | 1,004 | – | |
| Meta | 2026Q4 | – | – | – | 15 000 | inte i XBRL än |
| Oracle | 2020Q2 | 20 000 | 19 888 | 1,006 | – | |
| Oracle | 2021Q2 | 15 000 | 14 934 | 1,004 | – | |
| Oracle | 2022Q4 | 7 000 | 8 234 | 0,850 | – | annan upplåning |
| Oracle | 2023Q1 | 5 250 | 5 214 | 1,007 | – | |
| Oracle | 2024Q4 | 6 250 | 6 210 | 1,006 | – | |
| Oracle | 2025Q1 | 7 750 | 7 711 | 1,005 | – | |
| Oracle | 2025Q4 | 18 000 | 17 880 | 1,007 | – | |
| Oracle | 2026Q1 | 25 000 | 26 664 | 0,938 | – | annan upplåning (ej verifierat) |
| Oracle | 2026Q4 | – | – | – | 10 000 | inte i XBRL än |

I 15 av de 24 kvartalen som XBRL har ligger andelen på 0,99–1,01. Det är en starkare kontroll än årstabellen,
eftersom annan upplåning i andra kvartal inte späder ut den. Alphabet 2020Q3 ligger på 1,014 (137 MUSD, inte utrett).
I de åtta andra finns obligationer i annan valuta eller annan upplåning i samma kvartal.

### Det som inte syns

- **CoreWeave** har inga registrerade obligationer. Obligationerna 2030 och 2031 (maj och juli 2025) erbjöds enligt
  Rule 144A och Regulation S (8-K 2025-05-19, 0001193125-25-122115, och 2025-07-21, 0001193125-25-161520, kontrollerat
  i texten). Den enda 424B5:an (2026-09-17) gäller aktier. CoreWeaves upplåning syns bara som volym (`debt_issued_crwv`).
- **Meta 2022** (144A, se tabellen) och Metas finansiering av Hyperion 2025 (SPV, utanför balansräkningen) finns inte
  i korpusen.
- **Microsoft** har en enda registrerad emission sedan 2020 (2026-10-29, 25 000 MUSD). Serien `issuance_msft_q` får sin
  första rad 2027-01-01 och står i `KNOWN_STALE` till dess. Microsoft får ingen egen spreadserie (ett kvartal).

### Serier (hämtade 2026-11-25)

| Serie | Rader | Kvartal |
|---|---|---|
| `issuance_googl_q` | 5 | 2020Q3–2026Q3 |
| `issuance_amzn_q` | 7 | 2020Q2–2026Q3 |
| `issuance_meta_q` | 4 | 2023Q2–2026Q2 |
| `issuance_orcl_q` | 8 | 2020Q1–2026Q1 |
| `issuance_msft_q` | 0 | första kvartalet 2026Q4, känt 2027-01-01 |
| `spread_issue_ai_q` | 17 | 2020Q1–2026Q3 |
| `spread_issue_ai_7_12y_q` | 17 | 2020Q1–2026Q3 |
| `spread_issue_googl_q`, `_amzn_q`, `_meta_q`, `_orcl_q` | 5, 7, 4, 8 | som volymerna |

Kvartalet 2026Q4 har tranchar från Meta, Microsoft och Oracle och blir känt 2027-01-01. Klass för kommersiell
användning: `ja` för alla elva (den kurerade regeln, alla rader på sec.gov, och SEC:s villkor). Ingen ny regel behövdes
i `licenses.py`. Alla har `publish=False`.

### Kända begränsningar

- **Den poolade spreaden är mest en emittent per kvartal.** 12 av 17 kvartal har en enda emittent, och Oracle
  (BBB-betyg 2025–2026) ligger långt över Alphabet och Microsoft (AA+ och AAA). Den poolade serien visar därför till
  stor del vem som kom till marknaden. Serierna per emittent är det renare måttet. Bandet 7–12 år har 1–6 tranchar per
  kvartal. Med så korta och glesa serier kan en förändring mellan två kvartal vara slump.
- **Bara den registrerade marknaden.** Privata placeringar, 144A, SPV, företagscertifikat, banklån och terminslån
  saknas, och från 2025 en stor del av Alphabets och Amazons upplåning i annan valuta.
- **Spreaden är priset på emissionsdagen**, mot den statsobligation som bolaget och bankerna valde. Den är inte en
  marknadsspread för utestående obligationer.
- **Inget marknadsindex att jämföra med** (licens, se ovan). Ett eget index av emissioner från andra bolag vore
  möjligt med samma teknik, men är inte byggt.

## Rättning efter R20 (X17, 2026-11-25)

Granskningen R20 (`docs/granskning/r20-kredit-emission.md`) godkände extraktionen med fem should_fix. De rör
självkontrollen och tre kodvägar som dagens rader inte använder, och avstämningen per kvartal. Registerposten "2026-11-25
– X17" committades före ombyggnaden. Den ändrar inga regler. Den säger hur reglerna genomförs och preciserar
helgdagarna i T+n. Före posten hade X17 sett KR1:s rader och serier, R20:s granskning och en ombyggnad ur KR1:s cachade
dokument med den gamla koden (samma fil).

| Fynd | Rättning | Effekt i dag |
|---|---|---|
| R20-1 | Självkontrollen söker talen i tranchens del av blocket: texten efter tranchens nyckel i en gemensam tabell, cell j i en kolumntabell, hela avsnittet för en tranche med eget avsnitt. Prisdag och likviddag får också stå på en rad utan nyckel | 0 fel av 239. Se mutationsprovet nedan |
| R20-2 | Ombyggnaden läser också 424B2 och 424B5. Varje dokument som inte kodas listas med skäl i `curated/credit_issuance_skipped.csv`. Ett slutligt prospekttillägg utan FWP blir källan om parserns tranchar är omslagets, annars stoppas ombyggnaden. `--covers` prövar också från prospekttilläggen till källorna | 107 dokument listade. De 39 paren FWP–prospekttillägg är exakt R20:s. Inget prospekttillägg utan källa |
| R20-3 | T+n räknas med den federala helgdagskalendern i USA. Långfredagen, en lördagshelg som flyttas till fredagen och annan valuta än USD ger ingen framräknad likviddag, och raden ska kodas för hand | ingen rad: alla 239 likviddagar står i dokumenten |
| R20-4 | CSV:n skrivs utan avrundning (kortaste form som läses tillbaka till samma tal) | CSV:n är byte för byte densamma |
| R20-5 | `coverage` ger också en rad per kvartal med emission | tabellen ovan, lika med R20:s |

Anmärkningarna N-1, N-2 och N-5 står som tolkning 10–12, N-6 och N-7 i täckningstabellerna, och N-3 och N-4 i
docstrings. N-8 kräver inget.

**Ombyggnad.** `credit_issuance build` med den nya koden ur de cachade dokumenten ger samma `curated/credit_issuance.csv`
byte för byte, och de 239 blocken är identiska med KR1:s. Inget värde, inget datum och ingen serie ändras.

**Tranchens del av blocket.** Den första versionen krävde kolon efter nyckeln. Körd mot de cachade dokumenten gav den ett
falskt fel: Amazons villkorsbilaga 2021 skriver "2024 Notes May 12, 2024" utan kolon, så förfallodagen hamnade i 2023
Notes del. Regeln för var en tranche börjar ändrades då till parserns form, med kolon som tillval, och bara på rader där
värdet börjar med en nyckel. Andra rader räknas som rader utan nyckel. Ändringen gäller kontrollen, inte något värde,
och den står i registret. Därefter: 238 rader rätt och den manuella raden med beloppet utanför, som förut.

**Mutationsprov** mot de cachade dokumenten. I var och en av de 186 raderna med `col` byttes ett tal (belopp,
förfallodag, kupong, avkastning, spread, pris eller referensens avkastning) mot värdet för en annan tranche i samma
dokument och valuta, och raden markerades manuell så att omtolkningen inte körs. Det gav 1 234 felaktiga rader. Den
gamla kontrollen (hela blocket) flaggade 0 av dem och den nya 1 229. De fem som går igenom har det felaktiga talet i
tranchens egen text av andra skäl. I tre fall står den felaktiga spreaden som en procentsats i tranchens text
(kupongen 0,450 %, referensobligationens kupong 0,250 % och 0,500 % av det nominella beloppet), eftersom regeln läser
"+0.45%" som 45 bp. I två fall är den felaktiga kupongen den tyska referensobligationens kupong. För parserrader fångar
omtolkningen också sådana fel.

**Kontroller mot nyhämtade dokument** (2026-11-25, i följd, 0,3 s mellan dokumenten, inget 403 eller 429): se
"Självkontroll" ovan.

**Vad som inte kunde verifieras.** Helgdagsregeln är bara prövad med syntetiska fall, eftersom ingen rad räknar fram
likviddagen. Att prospekttillägget blir källan är bara prövat syntetiskt, eftersom alla erbjudanden har en FWP.
