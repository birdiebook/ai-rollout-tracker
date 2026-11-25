# Källa: order och orderstock i resultatpressmeddelanden (spår S3)

Spår S3, körning 14, 2026-11-25. Bara extraktion. Inga takter, inga jämförelser och inga kärnserier är beräknade.
Order och orderstock för kraft, kylning och AI-servrar ligger flera kvartal före den fysiska utbyggnaden, men bolagen
anger dem i pressmeddelanden, inte i XBRL. Spår S2 bygger XBRL-sidan (intäkter, RPO) för samma bolag. S3 tar bara det
som står som tal i resultatpressmeddelandet.

Avsnittet "Kodningsregler" skrevs och committades **innan** någon bilaga hämtades eller något värde kodades. Före
låsningen hade agenten bara sett metadata: EDGAR:s submissions för de sex bolagen (formulär, items, datum, accession)
och indexsidorna för de 113 resultat-8-K:na (bilagornas nummer, beskrivning och filnamn). Ingen bilagetext var hämtad.
Ur allmän kunskap (offentlig rapportering) visste agenten att Vertiv brukar ange organisk ordertillväxt, orderstock och
book-to-bill, att GE Vernova anger order per segment och gasturbiner i GW, att Dell anger order och orderstock för
AI-servrar sedan 2024 och att Digital Realty anger tecknade hyresavtal och en orderstock av avtal som inte har börjat.
Tolkningar som behövs under kodningen skrivs i ett eget avsnitt och skrivs inte in i reglerna i efterhand.

Täckningskontrollen före låsningen visade två saker som reglerna tar med:
- GE Vernovas 8-K för 2025Q2 (2025-07-23, 0001996810-25-000132) är märkt med Item 2.01 i EDGAR, inte 2.02.
- GE Vernova och Eaton lägger pressmeddelandet i en enda bilaga märkt `EX-99`, inte `EX-99.1`. Digital Realty och
  ibland Vertiv har en `EX-99.2` (tilläggsmaterial).

## Kodningsregler (låsta 2026-11-25, före kodningen)

### Korpus

- **Bolag:** Vertiv (`vrt`, CIK 1674101), GE Vernova (`gev`, 1996810), Eaton (`etn`, 1551182), Dell (`dell`,
  1571996), Digital Realty (`dlr`, 1297996) och Equinix (`eqix`, 1101239, valfritt: kodas om tiden räcker, annars
  står det som inte kodat).
- **Dokument:** varje 8-K och 8-K/A med Item 2.02 och EDGAR:s `filingDate` 2022-01-01–2026-11-25. Från varje
  inlämning tas pressmeddelandet: bilagan `EX-99.1`, eller `EX-99` när inlämningen inte har någon `EX-99.1`. `EX-99.2`
  och senare bilagor (tilläggsmaterial, presentationer) ingår inte. GE Vernova från den första inlämningen 2024.
- **Luckregel:** saknar ett räkenskapskvartal ett 8-K med Item 2.02 tas det 8-K som lämnades samma dag som kvartalets
  10-Q eller 10-K, eller upp till sju dagar före, och som har en `EX-99`-bilaga. Känt fall från täckningskontrollen:
  GE Vernova 2025-07-23. Visar texten att bilagan inte är ett resultatpressmeddelande tas den bort, och det redovisas.
- Samtal, presentationer, bolagens egna sidor och 10-Q/10-K ingår inte. Siffror som bara står där kodas inte.
- **Text och plats:** texten är `tsmc_sec.to_text` av bilagan och meningarna är `guidance_capex.sentences` av texten.
  Platsen är `sentence #k` i den listan, räknat från 0. SHA-256 räknas med `guidance_capex.sentence_hash`. En tabell
  blir en lång "mening" och behålls.

### Kandidater och läsmängd

En mening är kandidat om den har ett mått-ord (`MEASURE_RE`: order, orders, booking(s), backlog, book-to-bill, book to
bill, slot reservation(s), reservation agreement(s), signed, leases, not yet commenced, not-yet-commenced, pipeline)
och minst en siffra. Läsmängden är kandidaterna och meningen efter varje kandidat (talet står ibland i nästa mening).
Agenten läser hela läsmängden. Antalet kandidater, läsmängden och kodade rader redovisas per bolag. Finns ett kodat tal
utanför läsmängden står det under Tolkningar, med antal.

### Vad som kodas per bolag

Bara tal som bolaget anger. Ord som "doubled", "record" eller "strong" kodas inte. En multipel med siffra ("2x",
"1.2x") är ett tal.

- **Vertiv:** order för hela bolaget (organisk tillväxt mot året före, för kvartalet och för rullande tolv månader,
  och andra former som anges), orderstock (nivå i USD och tillväxt) och book-to-bill (kvartal eller tolv månader).
  Regioner kodas inte.
- **GE Vernova:** order för hela bolaget och för segmenten Power, Wind och Electrification (nivå i USD och tillväxt),
  orderstock för hela bolaget och per segment när den anges (också uppdelad på utrustning och service), och alla tal
  i GW för gasturbiner (Gas Power): order, orderstock och reservationer av leveransplatser ("slot reservations"), var
  för sig eller tillsammans, som det står. Andra delsegment i USD kodas inte.
- **Eaton:** order och orderstock för Electrical Americas och Electrical Global (tillväxt i procent och nivåer om de
  anges), book-to-bill för dem, och tillväxt i order eller försäljning till datacenter när den anges som tal (för
  bolaget eller ett segment, som det står). Ett tal för "Electrical" som helhet kodas med segmentet `electrical`.
  Aerospace, Vehicle och eMobility kodas inte.
- **Dell:** order, leveranser ("shipments") och orderstock för AI-servrar ("AI servers", "AI-optimized servers"), i
  USD och som tillväxt, för kvartalet, hittills i året eller helåret, som det står. "Pipeline" kodas inte.
- **Digital Realty:** orderstocken av tecknade avtal som inte har börjat ("signed-but-not-yet-commenced", i USD per år
  som det står: annualized base rent eller annualized GAAP rental revenue), tecknade avtal i kvartalet ("bookings",
  hyra per år i USD, totalt och per kategori som anges: över 1 MW, 0–1 MW, sammankoppling) och MW när det anges.
  Anges både totalen och Digital Realtys andel kodas båda.
- **Equinix (valfritt):** "gross bookings" eller "annualized gross bookings" när de anges som tal i USD.

### Kolumner i `curated/orders_backlog.csv`

En rad per tal (`row_type` = `value`) eller per stopp (`stop`). Kolumner: `id`, `company`, `row_type`, `measure`,
`segment`, `component`, `window`, `form`, `organic`, `unit`, `value`, `qualifier`, `metric_as_stated`,
`fiscal_period`, `period_end`, `filed`, `accepted`, `release_date`, `form_type`, `exhibit`, `source_url`,
`accession`, `locator`, `sentence_sha256` och `note`. Meningen sparas bara i
`data/raw/orders_sentences/<id>.txt` (gitignorerad). Talet i en rad ska stå i den mening som platsen pekar på.

- **`measure`:** `orders`, `backlog`, `book_to_bill`, `slot_reservations`, `backlog_and_slot_reservations`,
  `shipments`, `sales` (Eatons försäljning till datacenter), `leases_signed`, `signed_not_commenced` och `bookings`
  (Equinix).
- **`segment`:** `total` (hela bolaget), för GE Vernova `power`, `wind`, `electrification` och `gas_power`, för Eaton
  `electrical_americas`, `electrical_global`, `electrical` och `data_centers` (bolaget) eller
  `<segment>_data_centers`, för Dell `ai_servers`, för Digital Realty `total`, `gt_1mw`, `0_1mw`, `interconnection`
  och `other` (noten säger vilken).
- **`component`:** `all`, `equipment`, `services` eller `dlr_share` (Digital Realtys andel).
- **`window`:** `q` (kvartalet), `ttm` (rullande tolv månader, "trailing twelve months", "rolling 12-month"), `ytd`
  (hittills i räkenskapsåret), `fy` (helåret) eller `end` (stocken vid periodens slut, som orderstock).
- **`form`:** `level` (nivå), `yoy_pct` (förändring mot samma period året före, procent), `qoq_pct` (mot kvartalet
  före), `vs_ye_pct` (mot förra räkenskapsårets slut), `ratio` (book-to-bill) och `yoy_mult` (en multipel av värdet
  året före, "2x").
- **`organic`:** `organic` ("organic", "organically"), `cc` ("constant currency", "excluding currency"), `reported`
  (bolaget säger "reported" eller anger både rapporterad och organisk siffra), `unspecified` (en tillväxt utan något av
  orden) eller `na` (nivåer och kvoter).
- **`unit`:** `MUSD`, `pct`, `ratio`, `GW` eller `MW`. "$7.4 billion" = 7 400, "$425 million" = 425. Procent som tal
  (17 för 17 %). En minskning ("down 5%", "decreased 5%") är negativ.
- **`qualifier`:** tom (exakt), `approx` ("approximately", "about", "around", "roughly", "~"), `gt` ("more than",
  "over", "above", "exceeding", "greater than") eller `lt` ("nearly", "almost", "less than", "under"). Rader med `gt`
  eller `lt` är gränser, inte värden. De står i CSV:n men blir inga seriepunkter.
- **`metric_as_stated`:** bolagets ord, kort och på engelska ("organic orders", "backlog", "book-to-bill ratio").
  Ingen hel mening.
- **`fiscal_period`:** bolagets kvartal ("2025Q3", för Dell "FY2026Q3"). `period_end` = sista dagen i det
  räkenskapskvartal eller fönster som talet gäller.
- **`note`:** kort, på engelska, utan citat. För ett tal ur en tabell står tabellens rad och kolumn.

### Definitioner och serier

- **En definition** är bolag, `measure`, `segment`, `component`, `window`, `form`, `organic` och `unit`. Talen kodas
  som de står. Olika definitioner är olika serier. De räknas aldrig om till varandra och skarvas aldrig (organisk mot
  rapporterad, kvartal mot tolv månader, procent mot nivå).
- **Ny ordalydelse med samma definition** ger samma serie, och noten nämner den.
- **Katalogserier:** en serie per definition som har värden för minst två perioder (rader med tom `qualifier` eller
  `approx`). Definitioner med en period står bara i CSV:n och listas.
- **Period:** kalenderkvartalet som innehåller mitten av räkenskapskvartalet (`period_end` − 45 dagar), samma regel som
  `sources/sec.py`. För `window` = `fy` är frekvensen år, och året är det som innehåller `period_end` − 182 dagar.
- **known_from = `filed`.** Ett upprepat värde för samma period ger ingen ny rad. Ett ändrat värde är en ny vintage.

### Första dokumentet och jämförelsetal

- Ett tal för en definition och period kodas i det tidigaste dokumentet i korpusen som anger det.
- Ett senare dokument som anger samma definition och period kodas bara om talet är annorlunda (en revidering). Det
  blir en ny rad, och noten säger det.
- Jämförelsetal för en tidigare period ("up from $5.3 billion", tabellens kolumn för året före) följer samma regel:
  de kodas bara om ingen rad för perioden finns eller om talet skiljer sig.
- Ur tabeller kodas bara kolumner för kvartalet (och jämförelsekvartalet) och för stocken vid periodens slut. Kolumner
  för hittills i året och helåret i tabeller kodas inte. I löptext kodas tal för hittills i året och helåret som de står.

### Stopp

- **Ordinarie pressmeddelande** = det pressmeddelande som redovisar ett räkenskapskvartals resultat, ett per kvartal.
  Preliminära siffror, rättelser (8-K/A) och andra 8-K med Item 2.02 är extra dokument. De kan ge värden men aldrig
  stopp.
- **Ett stopp** kodas i det första ordinarie pressmeddelandet som inte anger en definition som det föregående
  ordinarie pressmeddelandet angav för sin egen period. För `window` = `fy` jämförs pressmeddelandena för fjärde
  kvartalet. Ett jämförelsetal räknas inte som att definitionen anges.
- Stoppraden har definitionens kolumner, `fiscal_period` och `period_end` för pressmeddelandets kvartal, inget tal,
  platsen `absent` och SHA-256 av en tom sträng.
- Anges definitionen igen senare blir det nya värderader. Stoppet står kvar, och luckan fylls aldrig.
- En serie vars senaste rad är ett stopp är avslutad (`closed`).

### Datering

- **known_from = `filed`**, EDGAR:s `filingDate`. `acceptanceDateTime` sparas i `accepted`.
- **`release_date`** = datumet i pressmeddelandets datumrad (till exempel "COLUMBUS, Ohio, Oct. 22, 2025"), som det står
  i bilagan. Läsaren kräver att `release_date` ≤ `filed` och att skillnaden är högst tre dagar. Är pressmeddelandet
  daterat före inlämningsdagen var det offentligt tidigare, och known_from är då några dagar sent (konservativt). Det
  redovisas per dokument. Saknas datumraden står det i noten.
- Pressmeddelandet kan ha legat på bolagets sida någon timme före 8-K:t samma dag. Det ger inget läckage, eftersom
  known_from är en dag.

### Publicering och licens

- Gren: G7 för Vertiv, GE Vernova och Eaton (kraft och kylning), G6 för Dell (AI-servrar) och G4 för Digital Realty
  och Equinix (tecknade hyresavtal är kontrakterade intäkter, som RPO i G4).
- `publish=False` tills den oberoende granskningen av extraktionen är godkänd. Licens som för andra SEC-extraktioner
  (sec.gov/privacy). Klassen för kommersiell användning kommer från `ai_tracker.licenses` (kurerade rader på sec.gov).
- **Inga kärnserier.** Serierna ingår inte i grenarnas tillstånd, diffusionsindex eller takter.

### Inte kodat

- Tal i samtal, presentationer och tilläggsbilagor (`EX-99.2`).
- Guidance och prognoser ("we expect orders to ..."), "pipeline" och ord utan tal.
- Regioner (Vertiv), andra delsegment i USD (GE Vernova), andra segment (Eaton).
- Intervall ("between 10% and 15%"). De listas under Inte kodat i resultatet.

### Stickprov

`python -m ai_tracker.orders_check --frac 0.3 --seed 20261125` hämtar om bilagorna utan cache och kontrollerar varje
rad i urvalet:
- meningen på platsen har lagrad SHA-256 (annars söks hela dokumentet, "moved");
- talet står i meningen i en av formerna: USD som "$X billion" eller "$X million" (också med en eller två decimaler)
  eller som tabelltal i miljoner ("7,400", "7400"), procent som "X%" eller "X percent" (absolutbeloppet), kvoter som
  "X.Xx", "X.X times" eller "X.X", GW och MW som "X GW", "X gigawatts", "X MW" eller "X megawatts";
- `filed` och `accepted` stämmer med EDGAR:s submissions, och `release_date` med datumraden i bilagan;
- för ett stopp: ingen mening i bilagan har definitionens mått-ord, segmentets ord (utom `total`) och ett tal i
  enhetens form. Det är en grov kontroll. En träff ger felet `still_stated`, och granskningen läser meningen.

Kontrollen bekräftar plats, tal och datum, inte semantiken (definition, period, organiskt eller inte, första
dokumentet). Det är för den oberoende granskningen.
