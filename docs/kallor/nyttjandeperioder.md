# Källa: nyttjandeperioder för servrar och nätverksutrustning (spår P2a)

Bara extraktion. Inga takter, inga avskrivningar och inga jämförelser är beräknade. Serierna är indata till N7
(spår P3), som använder de perioder som var kända på varje prognosdag.

Avsnittet "Kodningsregler" skrevs och committades **innan** något dokument hämtades eller någon mening kodades. Agenten
kände före låsningen till de stora ändringarna 2020–2025 ur allmän kunskap (offentlig rapportering), men hade inte läst
något av dokumenten i korpusen. Tolkningar som behövs under kodningen skrivs i ett eget avsnitt och skrivs inte in i
reglerna i efterhand.

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
