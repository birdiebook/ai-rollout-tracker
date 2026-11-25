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

## Kodning (2026-11-25, efter låsningen)

Kodat efter commit 471c67b. Korpusen byggdes med `python -m ai_tracker.sources.orders_backlog_corpus` (113
pressmeddelanden, inga misslyckade hämtningar). Raderna kodades i arbetsblad per bolag och skrevs till
`curated/orders_backlog.csv` med plats, SHA-256 och datumraden. Meningarna ligger i `data/raw/orders_sentences/`.

### Läsmängd och kodade rader

| Bolag | Dokument | Kandidater | Läsmängd | Värden | varav gränser | Stopp | Definitioner | Katalogserier | Avslutade |
|---|---|---|---|---|---|---|---|---|---|
| Vertiv | 21 | 119 | 211 | 61 | 1 | 19 | 11 | 10 | 10 |
| GE Vernova | 11 | 177 | 311 | 197 | 0 | 1 | 27 | 26 | 0 |
| Eaton | 20 | 209 | 334 | 108 | 4 | 8 | 11 | 10 | 4 |
| Dell | 20 | 26 | 51 | 26 | 5 | 14 | 10 | 3 | 1 |
| Digital Realty | 20 | 731 | 1 312 | 183 | 0 | 0 | 12 | 12 | 0 |
| Equinix | 21 | 114 | 183 | 0 | – | – | – | – | – |
| **Summa** | **113** | **1 376** | **2 402** | **575** | **10** | **42** | **71** | **61** | **15** |

Talen räknar meningar med upprepningar. GE Vernova har 19 jämförelsetal ur segmenttabellernas kolumn för året före
(12 första gången för 2023, 6 revideringar och ett "från 50 GW"). 15 upprepade jämförelsetal kodades inte, eftersom
talet var detsamma som i det första dokumentet. 19 värden har `approx` och räknas som punkter.

**Utanför läsmängden** kodades 4 rader, alla Dell: tre ur 2024-08-29 #14 (efterfrågan på AI-servrar i kvartalet, i
USD och som tillväxt mot kvartalet före, och hittills i året; ordet är "demand") och en ur 2025-08-28 #3 (leveranser av
"AI solutions" under första halvåret av FY26, inget mått-ord). De hittades när agenten sökte efter "AI" och belopp i
Dells pressmeddelanden. Citaten är ersatta med egna ord efter R19 (F-3).

**Läsning av långa meningar.** En tabell blir en lång "mening". För meningar över 700 tecken läste agenten fönster
på 150–220 tecken runt varje mått-ord med en siffra i närheten. För Eaton bestämdes segmentet av blocket meningen står
i (mellan "Sales for the Electrical Americas segment", "Sales for the Electrical Global segment" och "Aerospace segment
sales"), eftersom meningarna om order och orderstock inte upprepar segmentets namn. För Digital Realty, vars `EX-99.1`
är ett finansiellt supplement med pressmeddelandet som avsnitt, läste agenten pressmeddelandets avsnitt (höjdpunkter,
"Leasing Activity" och tabellen över nya avtal per region och produkt). Raden "All Regions" och totalraderna delades
med ett reguljärt uttryck, och varje tal jämfördes för hand med tabelltexten.

### Tolkningar

Tolkningar som behövdes under kodningen. Reglerna ovan är oförändrade.

1. **Samma tal två gånger i ett dokument.** Står ett tal i både rubrik och brödtext kodas en rad, ur meningen med det
   mest precisa talet och den mest bestämda formuleringen (Vertiv 2021Q4: 51,2 % i brödtexten, 51 % i rubriken; Vertiv
   2024Q2: rubriken säger "organic orders ... up 37% on a trailing twelve-month basis", brödtexten bara "orders").
2. **"Organic" och "excluding foreign exchange" i samma mening** kodas `organic` (Vertiv 2024Q1–2024Q4).
3. **Jämförelsetal som bara skiljer sig i avrundning** räknas som samma tal (Vertiv 2022Q3: "+51% in fourth quarter
   2021", kodat 51,2).
4. **Stock vid ett datum som inte är kvartalets slut** kodas inte: Vertivs orderstock "as of the end of August" 2022
   (det preliminära 8-K:t 2022-10-03) och Dells AI-orderstock "as of today" 2025-02-27.
5. **Extra dokument.** Vertivs 8-K 2022-10-03 (preliminära order för tredje kvartalet 2022, med vd-byte) är ett extra
   dokument (`EXTRA_DOCUMENTS`). Det ger ett värde (12 %, fast valuta) som det ordinarie pressmeddelandet reviderade
   till 15 %. Equinix 8-K/A 2025-07-31 är extra genom sin form, men Equinix är inte kodat.
6. **GE Vernova.** Order per komponent (service, utrustning) kodas inte, eftersom reglerna bara nämner uppdelningen för
   orderstock. GW kodas bara för kvartalets summa (order, orderstock, reservationer), inte för enskilda kontrakt
   ("a 1.8 GW order for three H-class gas turbines") och inte för vindkraft. Flöden i GW som inte är order
   (nytecknade reservationer, konverterade reservationer, levererade GW) och förändringar i USD ("backlog growth of $5.2
   B sequentially") passar inte schemat och kodas inte. "Orders exceeded revenue by 1.4X" och Electrifications
   book-to-bill (2026) kodas inte, eftersom reglerna för GE Vernova inte nämner book-to-bill. Electrifications order
   till datacenter ("$2.4 billion in equipment orders to support data centers", "over $5 billion year-to-date") är ett
   delsegment i USD och kodas inte. Alla GW-rader har komponenten `equipment` (gasturbiner). Orderstocken för
   Electrification står i en punkt under segmentets rubrik utan segmentets namn, och noten säger det. Orderstocken från
   2026Q1 innehåller det köpta Prolec GE, och noten säger det. Det är samma definition med ny omfattning, inte en ny
   serie (regeln om ny ordalydelse). *Rättat efter R19 (F-1):* konverterade reservationer är order och kodas från
   2025Q2, och ordren bland nya kontrakt har ett eget mått. Se avsnittet "Rättning efter granskning R19".
7. **Eaton.** "Flat" är ett ord och kodas inte. Därför står ett stopp för Electrical Globals organiska order i 2025Q1.
   Ordertillväxten "excluding one large multi-year data center order" (2025Q1) kodas inte (en egen justering). Tal för
   hela bolaget ("23% Backlog Growth", "The company's backlog was up 18%") och book-to-bill för Electrical och
   Aerospace tillsammans kodas inte, eftersom reglerna bara tar segmenten och Electrical. Rubriken 2022Q2 ("Robust
   Order Activity up 25% in Electrical") har inget fönster. Den kodas som rullande tolv månader, eftersom
   pressmeddelandet bara anger order så, och noten säger det. Eaton anger inga tal för order eller försäljning till
   datacenter, bara ord ("driven by data center momentum").
8. **Dell.** "AI orders" och "AI-optimized server demand" kodas som order för AI-servrar, och "AI solutions" som
   leveranser av AI-servrar. Noten säger ordet. Tillväxten "shipments up more than 100%" och "backlog growing more than
   30%" (2024-05-30) är gränser. De kodas som förändring mot kvartalet före, eftersom meningen börjar med "increasing
   sequentially" och orderstocken gick från 2,9 till 3,8 miljarder (+31 %).
9. **Digital Realty: andel.** Till och med 2024Q4 säger pressmeddelandet inte vilken andel totalen gäller. Tabellens
   rad "Grand Total" och textens "total bookings" kodas ändå som Digital Realtys andel (`dlr_share`), eftersom samma
   rad och samma mening från 2025Q1 (texten) och 2025Q3 (tabellen) heter "at Digital Realty's share". Talen vid 100 %
   andel (från 2025Q2) är en egen serie (`all`). Detta är den viktigaste tolkningen att granska. Kategorin "0–1
   megawatt plus interconnection" kodas inte, eftersom båda delarna kodas var för sig. "FY backlog cash NOI" i
   NAV-tabellen är ett annat mått och kodas inte. *Efter R19 (F-4):* andelen anges inte före 2025, och noterna för
   de åtta serierna säger det. Beläggen står i avsnittet "Rättning efter granskning R19".
10. **Datumraden.** Eatons pressmeddelande 2026-02-03 är daterat "February 26, 2026", alltså efter inlämningen. Det är
    ett skrivfel. `release_date` är tom och known_from är inlämningsdagen.
11. **Avslutad serie.** En gräns ("more than 100%") efter ett stopp öppnar inte serien igen, eftersom en gräns inte är
    en seriepunkt (`orders_backlog.stopped`). Vertivs organiska order 2026Q3 ("over 100%") är ett sådant fall.

### Resultat

- **Vertiv slutade ange order i siffror 2026.** Pressmeddelandena för 2026Q1 och 2026Q2 har inga tal för order,
  orderstock eller book-to-bill, och 2026Q3 bara "Organic Orders Growth over 100%" (en gräns). Alla tio serierna är
  därför avslutade. Det senaste talet är 2025Q4: organiska order +252 %, book-to-bill 2,9 och orderstock 15,0
  miljarder dollar. Vertiv har också bytt definition flera gånger: order utan angiven bas (2021Q4–2022Q2 och 2025Q1),
  i fast valuta (2022Q3–2023Q3) och organiskt (från 2023Q4).
- **GE Vernova** anger order per segment varje kvartal från 2024Q1 (och 2023 genom jämförelsetalen), gasturbinernas
  orderstock och reservationer i GW från 2025Q1 och orderstocken för hela bolaget från 2025Q4. Segmenttabellernas
  jämförelsetal för 2025 ändrades i pressmeddelandena 2026 (till exempel Power 2025Q1 från 6 247 till 6 263 miljoner).
  Det är nya vintages.
- **Eaton** anger bara tillväxt: order som rullande tolv månader och orderstock mot samma månad året före, per segment.
  Från 2025Q2 står orderstockens tillväxt utan ordet "organically", och det blir en ny serie.
- **Dell** anger AI-order och AI-orderstock oregelbundet och i citat. Tre serier har minst två perioder.
- **Digital Realty** anger nya avtal per produkt i varje kvartal sedan 2021Q4 och orderstocken av tecknade avtal från
  2024Q3.
- **Gren.** G7 för Vertiv, GE Vernova och Eaton (kraft och kylning), G6 för Dell (AI-servrar) och G4 för Digital
  Realty (tecknade hyresavtal är kontrakterade intäkter, som RPO).

### Datering

known_from är inlämningsdagen i EDGAR. Datumraden fanns i alla 113 bilagor (`orders_backlog_corpus.dateline`). Den är
samma dag som inlämningen i alla kodade dokument utom Eaton 2026-02-03 (skrivfel, se tolkning 10). Equinix 8-K/A
2025-07-31 är daterat dagen före, eftersom ändringen lämnades in dagen efter originalet. Inget pressmeddelande var
alltså offentligt en tidigare dag än inlämningen, enligt datumraden. Att pressmeddelandet kan ha legat på bolagets sida
några timmar före 8-K:t samma dag ger inget läckage, eftersom known_from är en dag.

### Stickprov

`python -m ai_tracker.orders_check --frac 0.3 --seed 20261125`: 185 rader (11 stopp), 1 fel. Hela filen
(`--frac 1.0`): 617 rader (42 stopp), 3 fel, 0 flyttade meningar. Alla tre felen är `still_stated` för stopp, och
agenten läste meningarna:
- `dell-2024-05-30-s01` (order mot kvartalet före): meningen anger ordernivån "increasing sequentially to $2.6
  billion" och tillväxt för leveranser och orderstock, inte orderns tillväxt i procent.
- `etn-2025-08-05-s01` (Electrical Americas orderstock, organisk): rubriken anger orderstocken för hela Electrical,
  och ordet "organic" gäller försäljningen.
- `vrt-2022-10-26-s01` (order utan angiven bas): meningen anger jämförelsetal för 2021Q4 och 2022Q1.

Alla hashar, tal och datum (filed, accepted och datumraden) stämde. Kontrollen säger inget om semantiken: definition,
period, organiskt eller inte och första dokumentet. Det är för den oberoende granskningen.

### Inte kodat

- **Equinix** (valfritt) är inte kodat. Dokumenten ingår i korpusen, och läsmängden (183 meningar) är inte läst.
- Guidance ("we expect", "at least 110 GW by year-end 2026", Dells guidance för AI-leveranser), "pipeline" och ord
  utan tal ("record", "doubled", "flat").
- Regioner (Vertivs Americas, Digital Realtys regioner), Aerospace, Vehicle och GE Vernovas vindkraft i GW.
- Intervall förekom inte i de kodade måtten.

## Rättning efter granskning R19 (spår X16, 2026-11-25)

R19 godkände extraktionen med anmärkningar (`docs/granskning/r19-order-orderstock.md`). Rättningarna R-1 till R-4
görs här. Bara R-1 ändrar en regel. Den har en daterad post i registret: "S3: GE Vernovas order i GW delas och
konverteringar kodas".

### Regler för GE Vernovas GW (committade före omkodningen)

Före reglerna hade X16 läst GW-meningarna i GE Vernovas sju pressmeddelanden 2025Q1–2026Q3 och R19:s granskning, där
konverteringarna står. Inga andra bilagor lästes.

- **2025Q1** har en egen uppställning: kvartalets "gas turbine orders" och nya reservationer i en mening. Talet behåller
  måttet `orders`. Det är en period, alltså ingen katalogserie.
- **Från 2025Q2** står kvartalets nya kontrakt i en mening ("new gas equipment contracts"), uppdelade på nya
  reservationer och order ("Y GW of orders"). Y kodas med måttet `orders_new_contracts`. Nästa mening anger
  konverteringarna ("Converted X GW of existing slot reservation agreements"). X kodas med måttet `orders_converted`,
  med samma plats och hash som orderstocken, som står i samma mening.
- Läsaren avvisar `orders` i GW för en period från 2025Q2. Ett stopp för `orders` i GW kodas i pressmeddelandet för
  2025Q2, enligt stoppregeln.
- Kvartalets orderingång i GW är `orders_new_contracts` + `orders_converted`. Den blir ingen egen serie.
- Nya reservationer, summan av nya kontrakt och levererade GW kodas inte (tolkning 6 gäller för dem).

### Utfall (efter omkodningen)

- **R-1 (F-1).** Sex rader bytte mått från `orders` till `orders_new_contracts` (2025Q2–2026Q3: 2, 1, 3, 2, 2 och 3
  GW). Sex nya rader har `orders_converted` (3, 7, 8, 6, 10 och 13 GW), ur samma mening som orderstocken. Raden för
  2025Q1 ("gas turbine orders", 7 GW) behåller `orders`, och stoppet står i pressmeddelandet 2025-07-23. Kvartalets
  orderingång i GW, summan av de två måtten, är 5, 8, 11, 8, 12 och 16 GW. Det är samma tal som R19 räknade fram.
  Orderstocken går ihop inom 1 GW i alla sex kvartal (test). `orders_check` mot nyhämtade bilagor gav 35 rätt av 35
  GW-rader. Stoppet gav ingen träff.
- **R-2 (F-2).** En period där bara en gräns anges har nu luckorsaken "only a bound is stated". Det gäller Eatons
  book-to-bill för Electrical 2023Q3, 2023Q4, 2025Q1 och 2025Q2. Efter ett stopp står stoppet kvar och gränsen läggs
  till. Inga andra luckorsaker ändrades.
- **R-3 (F-3).** De två citaten ur Dells pressmeddelanden är ersatta med egna ord. Det längsta citatet i dokumentet
  har nu tio ord.
- **R-4 (F-4).** Noten för de åtta serierna med `dlr_share` säger att andelen inte anges före 2025 och ger beläggen.
  X16 kontrollerade beläggen i de sparade bilagorna:
  - Fotnoten till "Estimated cash NOI related to signed leases" säger "Includes" till och med 2022Q4, "Excludes"
    2023Q1–2023Q4 och "Includes" från 2024Q1. Det är samma byte som R19 såg.
  - Tilläggsmaterialets tabell "Summary of Leasing Activity" (0–1 MW, över 1 MW och övrigt) har samma kvartalstal som
    CSV:n i alla 17 kvartal 2021Q4–2025Q4. Från 2023Q4 är tabellens tolvmånaderssumma lika med summan av de fyra
    kvartalen som de först angavs, inom 0,3 MUSD. Sedan 2025Q1 anger texten Digital Realtys andel, och summorna
    2025Q1–2025Q3 innehåller 2024Q2–2024Q4. Det talar för samma bas för de kvartalen.
  - Före 2023Q4 skiljer summorna upp till 49 MUSD från kvartalen (över 1 MW i 2022Q3). I 2022Q3 är summan för övrigt
    mindre än kvartalet självt. Summorna före 2023Q4 är därför inget belägg, varken för eller emot. För 2021Q4–2024Q1
    är andelen obelagd. Det kräver 10-Q och 10-K, som inte ingår i korpusen.
- **Anmärkningar.** N-5: noten för Eatons tre orderstockserier utan bas och sju rader i CSV:n nämner Fibrebond (köpt
  2025-04-01, Electrical Americas) och Boyd Thermal (köpt 2026-03-12, Electrical Global). Pressmeddelandet säger inte om
  deras orderstock ingår. N-7: fotnoten om en ersatt hyra på 8 MW 2023Q2 står i noten för fyra rader. Den höjer hyran
  men inte kapaciteten. N-1–N-4, N-6 och N-8 kräver ingen ändring. Skriptet för omkodningen är inte committat, liksom
  S3:s (N-6). CSV:n och testerna bär allt.
- **Antal efter rättningen:** 581 värden (10 gränser), 43 stopp, 73 definitioner och 62 katalogserier. GE Vernova har
  203 värden, 2 stopp, 29 definitioner och 27 katalogserier.
- **Effekt på serierna** (`python -m ai_tracker.observations` för alla 62 nycklar i X16:s arbetsyta, jämfört med S3:s
  tabell): de 60 gemensamma serierna har samma perioder, värden och known_from.
  `ob_gev_orders_gas_power_equipment_q_level_gw` (7 rader) finns inte längre. De två nya GW-serierna har 6 rader var.
  Tabellen har 564 rader för `ob_`, mot S3:s 559.
