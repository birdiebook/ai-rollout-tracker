# Källa: nyttjandeperioder för servrar och nätverksutrustning (spår P2a)

Byggt och kontrollerat 2026-11-24 (spår P2a, körning 13). Bara extraktion. Inga takter, inga avskrivningar och inga jämförelser är beräknade. Serierna är indata till N7
(spår P3), som använder de perioder som var kända på varje prognosdag.

Avsnittet "Kodningsregler" skrevs och committades (6ae7368) **innan** något dokument hämtades eller någon mening kodades. Agenten
kände före låsningen till de stora ändringarna 2020–2025 ur allmän kunskap (offentlig rapportering), men hade inte läst
något av dokumenten i korpusen. Tolkningar som behövs under kodningen skrivs i ett eget avsnitt och skrivs inte in i
reglerna i efterhand.

Kod: `src/ai_tracker/sources/useful_lives_corpus.py` (korpus och kandidater), `src/ai_tracker/sources/useful_lives.py`
(läsare, stegserier, `in_effect`, `changes`), `src/ai_tracker/series/useful_lives.py` (katalogposter),
`src/ai_tracker/useful_lives_check.py` (stickprov). Data: `curated/useful_lives.csv` (committad, bara siffror och
referenser). Tester: `tests/test_useful_lives.py` (syntetiska fixturer, inget nät). Kandidater:
`python -m ai_tracker.sources.useful_lives_corpus`, stickprov: `python -m ai_tracker.useful_lives_check --frac 0.3 --seed
20261124`. Ordningen i git: reglerna (6ae7368), koden utan värden (fc49225), därefter de kodade värdena.

## Kodningsregler (låsta 2026-11-24, före kodningen)

### Korpus

- **Bolag:** Microsoft (msft), Alphabet (googl), Amazon (amzn), Meta (meta), Oracle (orcl) och CoreWeave (crwv).
- **Dokument:** alla 10-K, 10-K/A, 10-KT, 10-Q och 10-Q/A (primärdokumentet) med EDGAR:s `filingDate`
  2018-01-01–2026-11-24, och alla 8-K med Item 2.02 under samma tid (alla EX-99-bilagor). CoreWeave från den första
  inlämningen efter börsnoteringen 2025. S-1, prospekt, samtal och bolagens egna sidor ingår inte.
- **Text och plats:** texten är `tsmc_sec.to_text` av dokumentet och meningarna är `guidance_capex.sentences` av texten.
  Platsen är `sentence #k` i den listan, räknat från 0. SHA-256 räknas med `guidance_capex.sentence_hash`.

### Kandidater

En mening är kandidat om den nämner en tillgångsklass som kan innehålla servrar eller nätverksutrustning (`CLASS_RE`:
servers, network(ing) equipment/assets, computer equipment/hardware, technical infrastructure, information technology,
technology equipment, data center equipment) och antingen nyttjandeperiod eller avskrivning (`LIFE_RE`) eller ett
antal år (`YEARS_RE`). En mening som nämner en ändrad uppskattning ("change in estimate") tillsammans med avskrivningar
är också kandidat. Långa "meningar" (tabeller som blivit en rad) behålls. Agenten läser alla kandidater. Antalet
kandidater och kodade rader redovisas.

### Radtyper i `curated/useful_lives.csv`

En rad per uttalande. Varje rad har bolag, URL, accession, `filed`, `accepted`, dokumenttyp, plats, SHA-256 av meningen
och en kort not utan citat. Meningen sparas bara i `data/raw/useful_lives_sentences/<id>.txt`. Alla tal i en rad ska
stå i den mening som platsen pekar på.

1. **`policy`:** den angivna nyttjandeperioden för en klass i redovisningsprinciperna eller noten om
   anläggningstillgångar. `life_lo`, `life_hi` (lika för en punkt) och `period_end` = dokumentets balansdag
   (EDGAR:s `reportDate`). Perioden gäller vid balansdagen. En rad per dokument och klass, också när värdet är detsamma
   som i förra dokumentet.
2. **`change`:** en ändrad uppskattning av nyttjandeperioden. Klass, ny period (`life_lo`, `life_hi`), gammal period
   (`old_lo`, `old_hi`, bara om den står i meningen) och `effective` = dagen då den nya perioden börjar gälla enligt
   texten. Anges bara ett år eller räkenskapsår blir det första dagen i det. Anges ett kvartal blir det första dagen i
   kvartalet. Anges ingen tidpunkt blir det första dagen i den period som dokumentet redovisar, och noten säger det.
   `period_end` = dokumentets balansdag (för 8-K: det redovisade kvartalets slut).
3. **`effect`:** bolagets egen uttalade effekt av en ändring. `ref` = id för ändringsraden. `effect_value` med tecken
   som förändringen i måttet: minskade avskrivningar är negativt för `depreciation`, ökat rörelseresultat är positivt
   för `operating_income`. `effect_metric` är `depreciation`, `operating_income`, `net_income` eller `diluted_eps`.
   `effect_unit` är MUSD eller USD per aktie. `effect_basis` är `expected` (väntad effekt: "we expect", "will") eller
   `actual` (effekten för en avslutad period). `effect_start` och `effect_end` är perioden som effekten gäller
   ("for fiscal year 2023" = räkenskapsåret, "for the three months ended" = kvartalet).
4. **`stop`:** den första 10-K där bolaget inte längre anger perioden för en klass som det angav i föregående 10-K.
   Inga tal. Finns stycket om avskrivningar kvar utan tal är platsen den meningen. Är stycket borta är platsen `absent`
   och SHA-256 räknas av en tom sträng. Ett 10-Q utan uppgift är inget stopp, eftersom 10-Q sällan upprepar principerna.

### Tillgångsklass

- `asset_class` = bolagets ord, kort och på engelska som det står ("servers and network equipment", "computer
  equipment").
- `class_code` anger räckvidden:
  - `SERVERS`: bara servrar.
  - `NETWORK`: bara nätverksutrustning ("network equipment", "networking equipment", "network assets").
  - `SERVERS_NETWORK`: servrar och nätverksutrustning med en gemensam period.
  - `COMPUTER_EQUIPMENT`: en bredare klass med datorutrustning ("computer equipment", "computer hardware",
    "information technology equipment", "technology equipment").
  - `TECH_INFRA`: en bredare klass med servrar, nätverk och datacenter ("technical infrastructure").
  - `OTHER`: en annan bredare klass där bolaget säger att servrar ingår. Noten säger vilken.
  - Tillägget `_SUBSET` när bolaget säger att perioden eller ändringen gäller en del av klassen ("certain", "a subset
    of", "some").
- En klass med en annan räckvidd får en annan kod, även om orden liknar varandra. Ny ordalydelse med samma räckvidd
  ("network equipment" mot "networking equipment") har samma kod och nämns i noten.
- Anger ett dokument flera klasser som innehåller servrar kodas varje klass för sig.

### Tal

- Perioder i år. "Four and a half years" = 4,5. Ett intervall ("two to six years") kodas som lo och hi. "Up to N years"
  ger bara hi, och noten säger det.
- Effektens belopp i MUSD ("$3.4 billion" = 3 400) eller USD per aktie. Inga beräkningar: ett belopp kodas som det står,
  och en effekt som inte har ett belopp kodas inte.

### Datum och vintages

- **known_from = `filed`**, EDGAR:s `filingDate`. `acceptanceDateTime` sparas. En inlämning efter 17.30 ET får nästa
  arbetsdag som `filingDate`, så datumet är då konservativt.
- **Första dokumentet räknas.** En ändring kodas i det tidigaste SEC-dokumentet i korpusen som beskriver den. Ett
  senare dokument kodas bara om det anger något som de tidigare raderna för samma ändring inte angav (till exempel den
  gamla perioden), eller anger det annorlunda. Då blir det en ny rad. Upprepningar räknas i dokumentationen men kodas
  inte.
- **Effekter:** varje uttalad effekt med nytt belopp, nytt mått eller ny period är en rad. En upprepning av samma
  belopp för samma mått och period kodas inte.
- Ett samtal eller pressmeddelande på bolagets sida kan ha kommit före SEC-dokumentet. Då är known_from senare än den
  första offentliga uppgiften. Det är konservativt (inget läckage), men datumet kan vara några dagar sent.

### Katalogserier

- **`useful_life_servers_<bolag>_lo` och `_hi`:** perioden för servrar, ur rader med `SERVERS` eller
  `SERVERS_NETWORK` (policy och change).
- **`useful_life_network_<bolag>_lo` och `_hi`:** perioden för nätverksutrustning, ur rader med `NETWORK` eller
  `SERVERS_NETWORK`.
- **`useful_life_<klass>_<bolag>_lo` och `_hi`** för de bredare klasserna (`computer_equipment`, `tech_infra`,
  `other`).
- `_SUBSET`-rader och effektrader blir inga katalogserier. De finns i CSV:n och i `useful_lives.changes()`.
- **Period** = kalenderkvartal. En policyrad ger kvartalet där `period_end` ligger. En ändringsrad ger det nya värdet i
  kvartalet där `effective` ligger och, om den gamla perioden står i meningen, det gamla värdet i kvartalet före.
  known_from = radens `filed`. En ändring som meddelas innan den gäller ger alltså ett värde med known_from före
  periodens slut (`lag_days` = −400).
- **Vintages:** ett upprepat värde för samma period ger ingen ny rad. Ett ändrat värde blir en ny vintage. Har ett
  dokument både en policyrad och en ändringsrad för samma serie och kvartal gäller policyraden.
- **Glesa serier.** Ett värde finns bara där ett dokument anger det. En lucka betyder inte att perioden har ändrats.
  Den som vill ha perioden i ett visst kvartal tar det senaste kända värdet (en stegfunktion, `useful_lives.in_effect`).
  Luckorna listas i `KNOWN_GAPS`.
- Gren G5, enhet år, frekvens Q, `publish=True` (siffror ur offentliga SEC-dokument med källhänvisning, aldrig text).
  `max_age_days` = 550 (ett 10-K om året plus marginal). En serie vars senaste rad är ett stopp är avslutad (`closed`).
- **Inga kärnserier.** Serierna ingår inte i grenarnas tillstånd eller diffusionsindex.

### Inte kodat

- Andra tillgångsklasser (byggnader, inventarier, leasade tillgångar, immateriella tillgångar).
- Utrangering i förtid och accelererade avskrivningar av utvalda tillgångar. De är inte en ändrad nyttjandeperiod för
  klassen. Belopp som nämns listas under "Inte kodat" i resultatet.
- Hypotetiska meningar i riskavsnitt ("if we change our estimates", "could").
- Siffror om kunder, leverantörer eller förvärvade bolag.

### Stickprov

`python -m ai_tracker.useful_lives_check --frac 0.3 --seed 20261124` hämtar om dokumenten utan cache och kontrollerar
varje rad i urvalet: meningen på platsen har lagrad SHA-256 (annars söks hela dokumentet, "moved"), varje tal i raden
står i meningen (perioder som siffra eller ord, belopp som "$X million/billion"), och `filed`/`accepted` stämmer med
EDGAR:s submissions. För en stoppad klass kontrolleras att ingen kandidatmening i dokumentet anger ett antal år för
klassen. Kontrollen bekräftar plats, tal och datum, inte semantiken (klass, räckvidd, effektivt datum). Det är för
den oberoende granskningen.

## Tolkningar under kodningen (inte en del av de låsta reglerna)

Följande fall täcktes inte uttryckligen av reglerna. Valet står här så att granskningen kan pröva det.

1. **Kandidatfiltret var för smalt** på tre punkter, samma lärdom som R2-F1. (a) Meningar om effekt och effektivt datum
   nämner sällan klassen med ett antal år. Microsofts 10-K 2020 anger till exempel effekten på rörelseresultatet för
   FY21 (2,7 miljarder USD) i en egen mening utan klass och period. Agenten läste därför de fem meningarna efter varje
   kandidat som beskriver en ändring.
   (b) Oracles klass "Computer, network, machinery and equipment" i 10-K 2018–2022 matchade inte `CLASS_RE`. (c)
   CoreWeaves "computing equipment utilized in data centers" matchade inte heller. Agenten sökte därför också igenom
   alla meningar i korpusen som har "useful li", "depreciable li" eller "Estimated Useful Life" och ett antal år men
   inte var kandidater (55 unika meningar, alla lästa). Utöver (b) och (c) gällde de immateriella tillgångar och
   totalintervall för alla anläggningstillgångar (Oracle: 1–40 år).

   *Tillägg efter R15 (spår X12):* 82 av 305 rader kommer från meningar utanför kandidaturvalet: 76 effekter
   (Microsoft 38, Oracle 24, Meta 9, Amazon 4, Alphabet 1), Oracles 5 policyrader 2018–2022 och CoreWeaves ändring.
   Avvikelsen från kandidatregeln är registrerad i `docs/mattregister.md` (2026-11-24, rättning efter R15). Sökningen
   finns nu som kod, `useful_lives_corpus.supplementary()`, som `build()` skriver till `supplementary.jsonl`. Den ger
   1 271 meningar (884 unika) efter en ändringskandidat och 74 (55 unika) i sökningen på nyttjandeperiod, och de 82
   raderna finns alla i den mängden. Koden skrevs efter kodningen. Den visar att urvalet går att göra om, men inte
   exakt vilka meningar agenten läste.
2. **Effektivt datum ur en mening i samma stycke.** Microsoft och Alphabet 2021 anger datumet i meningen efter, som
   säger att ändringen gäller från "fiscal year 2021". Noten anger det. Alphabets 8-K 2023-02-02 anger inget datum men
   en effekt "for the full fiscal year 2023" i samma mening, och året kodas därifrån.
   Metas 10-Q 2021-10-26 säger "in prior years as well as in 2021", och 2021-01-01 kodas.
3. **Ett 8-K som nämner ändringen utan perioder.** Amazons guidance (2020-01-30, 2022-02-03, 2024-02-01) säger att
   den guidade siffran innehåller cirka X lägre avskrivningar, eftersom nyttjandeperioden för servrar förlängs från
   1 januari. Perioderna anges inte. Det blir en effektrad (väntad, för kvartalet som guidas) med `ref` till
   ändringsraden i 10-K:t dagen efter. Seriens värde får 10-K:ts datum, eftersom 8-K:t inte anger perioden. Att en
   ändring kom var alltså känt en dag tidigare än den nya perioden.
4. **Effektens mått.** "Decreased our total operating expenses by X" (Oracle) kodas som `operating_income` +X.
   "Operating results ... favorably impacted by approximately $2.1 billion" (Alphabet 2021) kodas som
   `operating_income`. "Benefit to net loss" (Amazon 2022) kodas som `net_income` med plustecken. "Depreciation and
   amortization expense" (Amazon) kodas som `depreciation`. Bara utspädd vinst per aktie kodas. CoreWeaves "reduction
   in total expenses of $20 million" och "per share impact ... $0.10 increase" för 2023 kodas inte: måttet finns inte i
   schemat, och "per share" säger inte om det är utspätt.
5. **Klass och räckvidd.** Metas kategori "network equipment" (10-K 2018–2021, 3–20 och 3–25 år) omfattar enligt Meta
   själv servrar (10-Q 2021-10-26) och kodas som `OTHER`. "Certain network equipment" (Alphabet), "selected cohorts",
   "a majority of", "certain" och "most" servers and network assets (Meta) och "a subset of" (Amazon 2025) får
   `_SUBSET` och ingår inte i katalogserierna. Alphabets "servers and certain network equipment to six years" (2023)
   delas i `SERVERS` och `NETWORK_SUBSET`. Alphabets 10-K 2024-01-31 anger sex år för "information technology
   assets" och för "servers and network equipment" i samma mening. Det kodas bokstavligt för båda klasserna.
6. **Stopp är klassbyten.** Inget bolag har slutat ange en period helt. Tre bredare klasser byts mot en smalare och
   kodas som stopp: Microsoft 10-K 2026-07-29 ("computer equipment" blir "servers and network equipment", samma
   intervall 2–6 år), Alphabet 10-K 2025-02-05 ("information technology assets" försvinner, bara "servers and network
   equipment") och Meta 10-K 2022-02-03 ("network equipment" blir "servers and network assets"). Amazons 10-K
   2026-02-06 slår ihop "servers" och "networking equipment" till en klass. Det är inget stopp, eftersom perioden för
   servrar fortfarande anges, och serien fortsätter med `SERVERS_NETWORK`.
7. **Perioden vid balansdagen.** Amazons 10-K 2021–2025 anger perioden både före och efter ändringsdagen (till
   exempel tre år före 2020-01-01 och fyra år efter). Perioden som gäller vid balansdagen kodas.
8. **Oracles räkenskapsår börjar 1 juni.** Ändringarna gäller från 2022-06-01 och 2024-06-01, alltså mitt i kalender-Q2.
   Enligt regeln får den nya perioden kalender-Q2 och den gamla kvartalet före. Policyraderna för Oracles bredare klass
   har balansdagen 31 maj, som också ligger i kalender-Q2.
9. **Metas andra ändring 2022** (till fem år från Q4) kodas med den gamla perioden 4,5 år, som står i samma mening för
   samma tillgångar.
10. **Stoppens plats och självkontrollen** (tillagt efter R15, spår X12; valen gjordes under kodningen men skrevs inte
    här). Platsregeln för stopp täcker två fall: stycket finns kvar utan tal (platsen är den meningen) eller stycket är
    borta (`absent`). De tre stoppen är klassbyten, och stycket finns kvar med tal för den nya klassen. Platsen är då
    policymeningen, alltså samma mening som policyraden för den nya klassen. Självkontrollen `useful_lives_check`
    ändrades efter första körningen, när värdena var sedda:
    - Belopp: formen "$X.0 billion" (en decimal) lades till.
    - Stopp: kontrollen att meningen på platsen saknar antal år byttes mot `class_stated()`. Den godkänner stoppet om
      ingen mening i dokumentet har klassens namn direkt följt av ett antal år, eller ett antal år följt av "for (our)"
      och klassen. En sammansatt klass som slutar på samma ord räknas inte. Den låsta beskrivningen under Stickprov
      ("ingen kandidatmening ... anger ett antal år för klassen") stämmer därför inte längre ordagrant.

    Med kontrollen i `fc49225` ger 11 av 305 rader fel: 8 effekter med "$X.0 billion" (msft-2023-01-24-e4,
    msft-2023-07-27-e3, googl-2022-02-01-e5, googl-2023-07-25-e4, googl-2024-01-30-e5, amzn-2021-02-03-e4,
    amzn-2022-02-03-e1, amzn-2026-02-06-e3) och alla 3 stopp. X12 körde om båda versionerna på samma texter och fick
    samma 11 rader. R15 läste alla 11 i dokumenten och bekräftade dem i sak. Ändringen är registrerad i
    `docs/mattregister.md` (2026-11-24, rättning efter R15).

## Kodat (305 rader)

Korpus: 416 dokument i 375 inlämningar (187 10-K och 10-Q, 229 bilagor till 188 8-K med Item 2.02), 2018-01-01–
2026-11-24. Kandidaturvalet gav 467 meningar (338 unika) i 116 dokument: 134 för Alphabet, 117 Microsoft, 101 Amazon,
90 Meta, 23 Oracle och 2 CoreWeave. Agenten läste alla. De flesta kandidater som inte kodades är meningar i MD&A om att
marginalen eller kostnaderna påverkades av ändringen, utan ett eget belopp, och upprepningar av en redan kodad mening.

| Bolag | policy | change | effect | stop |
|---|---|---|---|---|
| Microsoft | 9 | 3 | 38 | 1 |
| Alphabet | 20 | 6 | 44 | 1 |
| Amazon | 17 | 5 | 79 | 0 |
| Meta | 9 | 4 | 28 | 1 |
| Oracle | 12 | 2 | 24 | 0 |
| CoreWeave | 1 | 1 | 0 | 0 |
| Summa | 68 | 21 | 213 | 3 |

### Ändringar av nyttjandeperioden

Datum = det första SEC-dokumentet som anger den nya perioden (known_from). Effekt = bolagets egen siffra i MUSD
(väntad när ändringen meddelades, och utfallet för det första hela året).

| Bolag | Klass | Från → till (år) | Gäller från | Känt (dokument) | Väntad effekt | Utfall första året |
|---|---|---|---|---|---|---|
| Microsoft | servrar | 3 → 4 | 2020-07-01 | 2020-07-30 (10-K) | rörelseresultat +2 700 (FY21) | rörelseresultat +2 700 |
| Microsoft | nätverk | 2 → 4 | 2020-07-01 | 2020-07-30 (10-K) | (samma) | (samma) |
| Microsoft | servrar och nätverk | 4 → 6 | 2022-07-01 | 2022-07-28 (10-K) | rörelseresultat +3 700 (FY23) | rörelseresultat +3 700 |
| Alphabet | servrar | 3 → 4 | 2021-01-01 | 2021-02-02 (8-K) | rörelseresultat cirka +2 100 | avskrivningar −2 600 |
| Alphabet | viss nätverksutrustning | 3 → 5 | 2021-01-01 | 2021-02-02 (8-K) | (samma) | (samma) |
| Alphabet | servrar | 4 → 6 | 2023-01-01 | 2023-02-02 (8-K, ny period), 2023-02-03 (10-K, gammal) | avskrivningar cirka −3 400 | avskrivningar −3 900 |
| Alphabet | viss nätverksutrustning | 5 → 6 | 2023-01-01 | 2023-02-02 / 2023-02-03 | (samma) | (samma) |
| Amazon | servrar | 3 → 4 | 2020-01-01 | 2020-01-31 (10-K; 8-K 2020-01-30 utan perioder) | rörelseresultat +2 300 | avskrivningar −2 700 |
| Amazon | servrar | 4 → 5 | 2022-01-01 | 2022-02-04 (10-K; 8-K 2022-02-03) | rörelseresultat +3 100 | avskrivningar −3 600 |
| Amazon | nätverk | 5 → 6 | 2022-01-01 | 2022-02-04 (10-K) | (samma) | (samma) |
| Amazon | servrar | 5 → 6 | 2024-01-01 | 2024-02-02 (10-K; 8-K 2024-02-01) | rörelseresultat +3 100 | avskrivningar −3 200 |
| Amazon | en del av servrar och nätverk | 6 → 5 | 2025-01-01 | 2025-02-07 (10-K) | rörelseresultat cirka −700 | avskrivningar +1 400 |
| Meta | utvalda servrar och nätverk | 3 → 4 | 2021 (inget datum) | 2021-10-26 (10-Q) | – | avskrivningar −620 |
| Meta | merparten av servrar och nätverk | 4 → 4,5 | 2022-04-01 | 2022-07-28 (10-Q) | – | (se nästa rad) |
| Meta | merparten av servrar och nätverk | 4,5 → 5 | 2022-10-01 | 2023-02-02 (10-K) | – | avskrivningar −860 (båda 2022) |
| Meta | vissa servrar och nätverk | → 5,5 | 2025-01-01 | 2025-01-29 (8-K) | avskrivningar cirka −2 900 | avskrivningar −2 920 |
| Oracle | servrar | 4 → 5 | 2022-06-01 | 2022-09-13 (10-Q) | – | rörelseresultat +434 (FY23) |
| Oracle | servrar och nätverk | 5 → 6 | 2024-06-01 | 2024-09-10 (10-Q) | – | rörelseresultat +733 (FY25) |
| CoreWeave | datorutrustning i datacenter | 5 → 6 | 2023-01-01 | 2026-03-02 (första 10-K) | – | inte kodat (se tolkning 4) |

Alla ändringar fram till 2024 förlängde perioden. Amazon förkortade den för en del av flottan från 2025. Effekterna per
kvartal och hittills i år finns i CSV:n (213 rader).

### Senast angiven period för servrar (per 2026-11-24)

| Bolag | Klass | År | Dokument |
|---|---|---|---|
| Microsoft | servers and network equipment | 2–6 | 10-K 2026-07-29 (FY26) |
| Alphabet | servers and network equipment | 6 | 10-K 2026-02-05 |
| Amazon | servers and networking equipment | 5–6 | 10-K 2026-02-06 (en del fem år från 2025) |
| Meta | servers and network assets | 5–5,5 | 10-K 2026-01-29 |
| Oracle | servers and networking equipment | 6 | 10-Q 2026-09-11 |
| CoreWeave | technology equipment | 6 | 10-K 2026-03-02 |

## Serier

30 katalogserier (15 par lo/hi) i G5 (`useful_life_<familj>_<bolag>_lo/_hi`), alla `publish=True`:
- `servers` och `network` för alla utom CoreWeave (Oracle `network` från 2024Q1, med den gamla perioden fem år ur
  ändringsraden),
- `computer_equipment` för Microsoft och Alphabet (avslutade 2026 och 2025), Oracle och CoreWeave,
- `other` för Meta (avslutad 2022).

Tre saker att veta när serierna används:
- **lo och hi blandar punkter och intervall.** En ändring anger en punkt (Microsoft 2022: sex år), policyn ofta ett
  intervall (Microsoft FY26: två till sex år). Microsofts `lo` går därför från 6 till 2 år 2026Q2 utan att något har
  ändrats. För N7 är `hi` den relevanta.
- **Glesa stegvärden.** `useful_lives.in_effect(bolag, "servers", "hi", as_of=prognosdag)` ger perioden per kvartal så
  som den var känd på prognosdagen.
- **Ändringar för en del av flottan syns inte** (`_SUBSET`, R15 N-4). Serien för Meta har `hi` 4 under 2022, fast
  merparten gick till 4,5 och sedan 5 år, och 5 under 2025, fast de flesta gick till 5,5. Amazons `hi` är 6 under 2025,
  fast en del gick till 5. Ändringarna finns i `useful_lives.changes()`.

## Inte kodat

- Amazons utrangering i förtid (10-K 2025-02-07): cirka 920 MUSD i accelererade avskrivningar och kostnader i 2024Q4 och
  cirka −600 MUSD i rörelseresultat 2025. Det är ingen ändrad period för klassen.
- Amazons tunga utrustning (10 → 13 år från 2025, rörelseresultat cirka +900 MUSD 2025): utanför omfånget.
- Avskrivningar per segment "including the effect of our change" (Alphabet 10-Q och 10-K), eftersom det inte är
  ändringens effekt.
- CoreWeaves effekter för 2023 (tolkning 4). R15 (N-3) påpekar att minskningen av totala kostnader, 20 MUSD, kunde
  kodas som rörelseresultat +20 MUSD på samma sätt som Oracles. Raden läggs inte till: inget använder den, och en ny
  rad i den granskade CSV:n kräver en ny granskning.
- Upprepningar: samma period eller samma belopp i ett senare dokument (till exempel Alphabets 10-Q, som upprepar
  beloppen i 8-K:t dagen före).

## Stickprov

`python -m ai_tracker.useful_lives_check --frac 1.0` hämtade om alla 91 dokument och EDGAR:s submissions för de sex
bolagen (utan cache) och kontrollerade alla 305 rader: **0 fel**, och ingen mening hade flyttat. Det gäller den
ändrade kontrollen. Med kontrollen i `fc49225` ger 11 rader fel (tolkning 10). Hash, tal och datum (`filed`,
`accepted`) stämmer för alla. Stickprovet med `--frac 0.3 --seed 20261124` (92 rader, hämtade på nytt en gång till)
gav också 0 fel.

Kontrollen bekräftar plats, tal och datum. Den bekräftar **inte** semantiken: klass och räckvidd, effektivt datum,
effektens tecken och mått, och om första dokumentet verkligen är det första. Agenten läste om alla ändringsrader, men det
är ingen oberoende granskning. Meningarna finns i `data/raw/useful_lives_sentences/<id>.txt` i spårets worktree, och
kodningen som skrev CSV:n i `data/raw/useful_lives_sentences/spec.py` och `build.py`.

## Begränsningar

- Bara SEC-dokument i korpusen. Microsofts samtal 2022-07-26 kom två dagar före 10-K:t. known_from blir då senare än
  den första offentliga uppgiften, vilket är konservativt.
- CoreWeaves S-1 2025-03-03 (0001193125-25-044231) anger redan ändringen från fem till sex år från 2023-01-01 och sex
  år för teknisk utrustning (R15 N-1, läst igen i X12). S-1 ingår inte enligt reglerna, så known_from 2026-03-02 är
  ungefär ett år sent. Det är konservativt.
- Bara 8-K med Item 2.02. Ett 8-K med Item 7.01 eller 8.01 som meddelar en ändring skulle ha missats. R15 läste sådana
  8-K nära varje ändring, och de säger inget om nyttjandeperioder. Alla 8-K med Item 7.01 och 8.01 är inte sökta.
- Ett 10-Q utan uppgift betyder att bolaget inte har angett någon ändring. Serien har ingen rad för kvartalet.

## Licens

SEC-dokument är offentliga (sec.gov/privacy). CSV:n innehåller siffror, plats, URL, accession och SHA-256 av meningen.
Noterna är på engelska och citerar inte, utom korta ordalydelser för klassen (till exempel "a subset of"). Meningarna
finns bara i `data/raw` (gitignorerad).
