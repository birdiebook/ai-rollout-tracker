# R19 – granskning av order och orderstock ur resultatpressmeddelanden (S3)

Granskningsspår R19, körning 14, 2026-11-25, gren `auto14k/r19-order-orderstock`. Granskat: spår S3:s tre commits
(`471c67b`, `620ca42`, `847c8eb`), alltså `curated/orders_backlog.csv` (575 värden och 42 stopp),
`sources/orders_backlog.py`, `sources/orders_backlog_corpus.py`, `orders_check.py`, `series/orders_backlog.py`,
S3:s block i `licenses.py`, registerposterna och `docs/kallor/order_orderstock.md`.

Underlag: alla 113 bilagor hämtades om från www.sec.gov med den ärliga klienten (källa `r19_review`, en i taget, 0,3 s
paus). Alla 113 svarade 200 och var byte för byte lika med S3:s kopior. `filingDate` och `acceptanceDateTime` kommer
från EDGAR:s submissions-API, via en ny körning av `python -m ai_tracker.orders_check --frac 1.0`. Inga svar med 403
eller 429. Tabellerna i GE Vernovas och Digital Realtys bilagor tolkades med en egen parser, oberoende av S3:s
arbetsblad. Equinix är inte kodat och därför inte granskat.

**Inga värden räknades om till takter.** Granskningen prövar bara extraktionen.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Ordning: regler före kodning | **OK** |
| 2. Semantik (stickprov) | **OK.** 0 fel av 65 (95 % KI 0–5,5 %). Hela filen är dessutom kontrollerad med andra metoder, utan fel. En definitionsfråga: GE Vernovas order i GW (F-1) |
| 3. Fullständighet | **OK.** Varje tal som pressmeddelandena anger inom reglerna finns i CSV:n |
| 4. Datering | **OK.** Inget pressmeddelande var offentligt före inlämningsdagen |
| 5. Definitionsbrott och stopp | **Anmärkning.** 42 av 42 stopp är riktiga. En skarv (F-1), en obelagd andel (F-4) och en vilseledande luckorsak (F-2) |
| 6. Text, hash och kontrollen | **OK med anmärkning.** Ingen meningstext i git, alla hashar stämmer och kontrollen klarar `--frac 1.0`. Källdokumentet citerar två hela meningar (F-3) |
| 7. publish och licens | **OK.** `publish=False` på alla 61 serier, klass `ja` enligt den dokumenterade regeln |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Inget läckage, inga fel värden och inga regler som avviker från registret utan
redovisning. Fyra should_fix (R-1 till R-4) gäller nio serier: GE Vernovas order i GW och Digital Realtys åtta serier
med `dlr_share` för tecknade avtal. Övriga 52 serier har inga fynd. `publish=True` kan prövas för dem nu. För de nio
gäller det efter R-1 och R-4.

## 1. Ordning: regler före kodning – OK

Ordningen enligt git och tidsstämplarna i den delade rå-cachen (`data/raw/orders_backlog`, 2026-11-25, UTC):

| Tid | Händelse |
|---|---|
| 09:52 | Submissions för sex bolag (täckningskontroll, bara metadata) |
| 09:53–09:54 | 113 indexsidor (bilagornas typ och filnamn, ingen bilagetext) |
| 09:58 | `471c67b`: kodningsreglerna i källdokumentet och registerposten |
| 12:38 | Korpusen byggs. Den första bilagan sparas 12:38:48, den sista 12:40:33 |
| 12:42–12:59 | S3:s kodningsblad per bolag (i S3:s arbetsyta) |
| 13:08 | `620ca42`: CSV, läsare, korpus, kontroll och serier |
| 13:10–13:11 | Stickprovskontrollen körs (frac 1.0 och 0.3) |
| 13:14 | `847c8eb`: tester, tolkningar och resultat |

- `orders_backlog_corpus.fetch_bytes` återanvänder en befintlig rå-kopia. Hade en bilaga hämtats före 09:58 till den
  delade cachen hade filen behållit den tidigare tiden, som indexsidorna gjorde. Alla 113 bilagor har tider från
  12:38–12:40. Begränsning: det visar bara den delade cachen, inte att ingen text lästes någon annanstans.
- `git diff 471c67b 847c8eb -- docs/kallor/order_orderstock.md` lägger bara till avsnitten efter reglerna. Reglerna
  är oförändrade. Tillägget i registret är daterat, skrivet efter kodningen och säger det. Tre tolkningar rör
  registrets regler (avslutad serie, Digital Realtys andel och stock vid annat datum än periodens slut). Alla tre är
  redovisade.
- Koden följer reglerna: kvartalet som innehåller mitten (−45 dagar), året för helår (−182 dagar), minst två perioder
  för en katalogserie, gränser blir inga punkter, första dokumentet räknas och ett ändrat tal blir en ny vintage,
  stoppregeln (`expected_stops`, testad mot CSV:n) och kontrollen av datumraden.
- Kandidatregeln i koden är något vidare än listan i reglerna (`ordered`, `ordering` och `lease` i singular). Den
  committades med CSV:n, inte före. Det ger fler kandidater, aldrig färre (N-4).

## 2. Semantik – OK, med en definitionsfråga

**Stickprov.** 58 värderader drogs slumpmässigt per bolag (Vertiv 10, GE Vernova 14, Eaton 12, Dell 8, Digital Realty
14, `random_state=2026112519`). Sju rader lades till för mått som dragningen missade: Digital Realtys orderstock av
avtal (2), Vertivs book-to-bill (1), GE Vernovas reservationer, order och orderstock i GW (1 var) och Dells
leveranser (1). Varje rad lästes i R19:s egen kopia av bilagan: mått, enhet, bas (organiskt, fast valuta, rapporterat
eller inte angivet), fönster (kvartal, tolv månader, hittills i året, helår, stock), period, segment, kvalificerare och
inlämningsdag.

**Resultat: 0 fel av 65.** Exakt 95 % konfidensintervall (Clopper–Pearson) 0–5,5 %. Raderna och deras hashprefix är
fastlåsta i `tests/test_r19_order_orderstock.py`.

**Kontroller av hela filen** (utöver stickprovet):

| Kontroll | Omfång | Utfall |
|---|---|---|
| Hash och tal i meningen, i R19:s egna kopior | 575 värden | 575 rätt |
| Digital Realty: egen tolkning av tabellen över nya avtal (All Regions, Interconnection, Grand Total, 100 % andel) | 171 rader för tecknade avtal | 169 automatiskt och 2 för hand, alla rätt. Tabellens kvartal är radens `fiscal_period` i alla 20 pressmeddelanden |
| Digital Realty: tilläggsmaterialets "Summary of Leasing Activity" (en annan tabell i samma bilaga) | 16 kvartal 2021Q4–2025Q4 | Summan 0–1 MW + över 1 MW + övrigt är densamma som i CSV:n alla 16 kvartal |
| GE Vernova: egen tolkning av segmenttabellerna (kvartalet, kolumnen för året före och rapporterad förändring) | 33 tabeller, 99 tal | Alla stämmer med CSV:ns vintages. De sex revideringarna är exakt de jämförelsetal som skiljer sig. Övriga jämförelsetal är lika med det första talet, så de 15 överhoppade upprepningarna är rätt |
| GE Vernova: organisk tillväxt per segment | 33 rader | "Orders of $X billion" i samma mening stämmer med segmentets tabellnivå i alla 33. Segmentet är alltså rätt |
| GE Vernova: hela bolaget och helår | 26 + 12 rader | Lästa. Helåret per segment är summan av fyra kvartal (±0,1 miljard) |
| Eaton: segment ur blocket | 108 rader | Eget block för varje rad. Alla stämmer. De 14 raderna för book-to-bill i `electrical` säger "the Electrical businesses" |
| Vertiv och Eaton: bas och fönster mot meningens ord | 131 tillväxtrader | 8 flaggor, alla lästa och falska: "organic" gäller försäljningen i rubrikens punkt, och Vertivs 2022Q2 anger valutan som en del av den rapporterade tillväxten |
| Dell | 40 rader (26 värden, 14 stopp) | Alla lästa |
| Vertiv | 61 värden, 19 stopp | Prövade mot en egen sökning i hela texten |

**Tolkningarna i fokuslistan.**
- Eatons rubrik 2022Q2 ("up 25% in Electrical", inget fönster) som tolv månader: stöds av att samma rubrik säger "up
  19% in Aerospace", och Aerospace-blocket anger 19 % organiskt på tolv månader.
- Vertiv 2025Q1, kvartalsorder `unspecified`: meningen saknar "organic", och reglerna går efter meningens ord. Rätt
  enligt regeln. Det ger ett stopp och en serie till, vilket är regelns följd. Vertiv 2024Q2, tolv månader organiskt
  ur rubriken: "organic" står i samma mening och gäller båda talen. Rätt.
- Dell, "AI-optimized server demand" och "AI orders" som order och "AI solutions" som leveranser: rimligt. Noten
  säger ordet. Leveranser hittills i året har bara en period och är ingen katalogserie.
- GE Vernova, inga order per komponent och ingen book-to-bill: följer reglerna, som bara nämner komponenter för
  orderstocken.

**F-1 (should_fix): GE Vernovas order i GW är skarvade och utan konverteringar.** Serien
`ob_gev_orders_gas_power_equipment_q_level_gw` har 7, 2, 1, 3, 2, 2 och 3 GW för 2025Q1–2026Q3.
- 2025Q1 (0001996810-25-000072, raden `gev-2025-04-23-15`) säger "gas turbine orders", alltså kvartalets order.
- Från 2025Q2 (först 0001996810-25-000132, raden `gev-2025-07-23-15`) står talet som en del av "new gas equipment
  contracts", bredvid nya reservationer ("... and 2 GW of orders"). Samma pressmeddelanden anger att reservationer
  konverterades till order: 3, 7, 8, 6, 10 och 13 GW. Orderstocken går ihop först när konverteringarna räknas med:
  förra kvartalets orderstock + kodade order + konverterade − levererade = kvartalets orderstock, inom 1 GW, i alla sex
  kvartal (testat). 2026Q3: 53 + 3 + 13 − 5 = 64 GW.
- Kvartalets orderingång i GW var alltså 5, 8, 11, 8, 12 och 16 GW, inte 2, 1, 3, 2, 2 och 3. Etiketten "Order, GE
  Vernova: Gas Power, utrustning, kvartal (GW)" säger något annat än talen.
- Om 2025Q1:s 7 GW innehåller konverteringar går inte att avgöra ur korpusen. Ordalydelsen bytte innebörd 2025Q2. Enligt
  registret ska serien då delas, inte skarvas.
- Reglerna säger "alla tal i GW för gasturbiner (Gas Power): order, orderstock och reservationer". Tolkning 6 tar bort
  konverteringarna som "flöden i GW som inte är order", fast bolaget kallar dem order ("converted ... to orders").
  Tolkningen är redovisad, så det är ingen dold regeländring. Men den ger en vilseledande serie.
- Raderna själva är rätt lästa. Felet sitter i definitionen. Därför räknas de inte som fel i stickprovet.

## 3. Fullständighet – OK

R19 sökte i hela texten i varje bilaga efter mått-orden med ett tal i närheten, oberoende av S3:s läsmängd, och jämförde
med CSV:n.

| Bolag | Mått | Kvartal som pressmeddelandet anger | I CSV:n |
|---|---|---|---|
| Vertiv | order, kvartal mot året före | 2021Q4–2025Q4 utom 2024Q4 (16), med tre olika baser | 16 av 16 (4 utan bas, 5 fast valuta, 7 organiskt) |
| Vertiv | order, tolv månader, organiskt | 2024Q2–2025Q4 (7) | 7 av 7 |
| Vertiv | orderstock, nivå | 2021Q4–2022Q4, 2023Q3–2024Q1, 2025Q1–2025Q4 (12) | 12 av 12 |
| Vertiv | book-to-bill | 2023Q1–2024Q2, 2025Q1–2025Q4 (10) | 10 av 10 |
| Vertiv | 2026Q1–2026Q3 | inga tal, bara "over 100%" 2026Q3 | gränsen finns |
| GE Vernova | order, hela bolaget och tre segment (nivå, rapporterat, organiskt) | 2024Q1–2026Q3 (11), jämförelsetal för 2023 | alla |
| GE Vernova | GW: orderstock, reservationer, summan | 2025Q1–2026Q3 (7) | 7 av 7 per mått |
| GE Vernova | orderstock, hela bolaget och Electrification utrustning | 2025Q4–2026Q3 och 2025Q3–2026Q3 | alla |
| Eaton | order, tolv månader, organiskt: Electrical Americas / Global | 2021Q4–2026Q3 (20) / 2022Q1–2026Q3 utom 2025Q1 "flat" (18) | 20 och 18 |
| Eaton | orderstock mot året före, per segment | EA organiskt 2021Q4–2025Q1 (14), EG organiskt samma utom 2023Q2–Q4 (11), båda utan bas 2025Q2–2026Q3 (6) | alla |
| Eaton | book-to-bill, Electrical | 2023Q2–2026Q3 (14, varav 4 gränser) | 14 av 14 |
| Dell | AI-servrar: order, orderstock, leveranser | oregelbundet FY2024Q4–FY2027Q3 | alla 26 |
| Digital Realty | tecknade avtal per kategori, hyra och MW | 2021Q4–2026Q3 (20) | 20 av 20, åtta kategorier |
| Digital Realty | orderstock av tecknade avtal | 2024Q3–2026Q3 (9), 100 % andel från 2026Q1 | alla |

Det som inte är kodat följer reglerna eller en redovisad tolkning: bolagstal för Eaton ("23% Backlog Growth"),
regioner, Aerospace, vindkraft i GW, enskilda kontrakt, förändringar i USD, guidance, Dells AI-orderstock "as of
today" och Vertivs orderstock "as of the end of August". Inga tal saknas i långa tabellmeningar. Det visar de egna
tabelltolkningarna för GE Vernova och Digital Realty. Equinix (183 meningar) är inte läst, vilket reglerna tillåter.

## 4. Datering – OK

- Datumraden är samma dag som `filingDate` i 111 av 113 bilagor. Undantagen: Eaton 0001551182-26-000002 (inlämnad
  2026-02-03, daterad "February 26, 2026", ett skrivfel, `release_date` tom) och Equinix 8-K/A 2025-07-31 (daterad
  dagen före, inte kodad).
- `acceptanceDateTime` i New York-tid: Vertiv 06:00–07:28, GE Vernova 06:16–06:36 och Eaton 07:00–08:08 (före
  börsöppning), Dell 16:07–16:39 och Digital Realty 16:01–16:43 (efter börsstängning). Alla är före 17:30, så
  `filingDate` är samma dag som pressmeddelandet. Inget pressmeddelande var offentligt en tidigare dag.
- Vertivs preliminära 8-K 2022-10-03 dateras med sin egen inlämning. Det ordinarie pressmeddelandets 15 % är en senare
  vintage (2022-10-26). GE Vernovas reviderade jämförelsetal för 2025 dateras med 2026 års inlämningar. Summan i GW för
  2025Q1 (50) dateras 2025-07-23, fast delarna var kända 2025-04-23. Det är sent, inte tidigt.
- S3:s observationstabell har 559 rader för de 61 serierna. De är lika med `series_frame` för varje nyckel, med
  known_from 2022-02-04 – 2026-11-24.

Inget läckage.

## 5. Definitionsbrott och stopp – anmärkning

- **Delade brott, som reglerna kräver:** Vertivs bas (utan bas, fast valuta, organiskt, utan bas 2025Q1, organiskt) och
  Eatons orderstock (organiskt till 2025Q1, utan bas från 2025Q2) är egna serier med stopp.
- **F-1:** GE Vernovas order i GW är skarvade (punkt 2).
- **F-4 (should_fix): Digital Realtys andel före 2025 är obelagd.** 13 kvartal (2021Q4–2024Q4) kodas som
  `dlr_share` fast tabellen och texten inte anger någon andel. Belägg för tolkningen: 2025Q1:s tabell (ingen andel
  angiven) är 242,305 miljoner, och texten säger "$242 million ... at its share". 2025Q2:s tabell är 135,320 miljoner,
  och texten säger 177 miljoner vid 100 % och 135 vid Digital Realtys andel. Tilläggsmaterialets tolvmånaderssumma
  2025Q3, som är vid Digital Realtys andel, är 2024Q4 + 2025Q1–Q3 som de rapporterades (572,7 miljoner). Bolaget lägger
  alltså ihop 2024 och 2025 utan omräkning. Belägg emot: inget. Men bolaget bytte behandlingen av samägda bolag i ett
  närliggande mått två gånger: fotnoten till "Estimated cash NOI related to signed leases" säger "Includes Digital
  Realty's share" till 2022Q4, "Excludes" 2023Q1–2023Q4 och "Includes" igen från 2024Q1. Basen för 2021Q4–2024Q1 går
  därför inte att belägga. Tolkningen är rimlig och redovisad i källdokumentet, men seriernas noter säger inget om den.
- **Omfattning utan ny definition**, med not: GE Vernovas orderstock från 2026Q1 innehåller Prolec GE. Utan not: Eatons
  Electrical Global har "Total backlog" från 2026Q1 och köpte Boyd Thermal 2026-03-12, som redovisas i segmentet.
  Orderstockens tillväxt går från 19 % till 73, 103 och 121 % (N-5).
- **Stopp: 42 av 42 är riktiga.** R19 läste varje stopp mot pressmeddelandet. Kontrollen `--frac 1.0` kördes om och gav
  samma tre `still_stated`-träffar som S3 rapporterade. Alla tre är falska: `dell-2024-05-30-s01` (meningen anger
  ordernivån "increasing sequentially to $2.6 billion", ingen procent), `etn-2025-08-05-s01` (rubriken anger
  orderstocken för hela Electrical, och "organic" gäller försäljningen) och `vrt-2022-10-26-s01` (jämförelsetal för
  2021Q4 och 2022Q1). Eatons "flat organically" (2025Q1) ger ett stopp, eftersom ord inte kodas (N-3).
- **F-2 (should_fix): luckorsaken säger "not stated" fast en gräns anges.** `KNOWN_GAP_PERIODS` för
  `ob_etn_book_to_bill_electrical_ttm_ratio_ratio` säger "not stated in any results release in the corpus" för 2023Q3,
  2023Q4, 2025Q1 och 2025Q2. Pressmeddelandena anger "over 1.1" och "greater than 1.0" (rader `etn-2023-10-31-04`,
  `etn-2024-02-01-04`, `etn-2025-05-02-05`, `etn-2025-08-05-06`). `gap_periods` räknar bara stopp och punkter.
- **Avslutad serie (N-2).** Stoppregeln räknar en gräns som att definitionen anges, men regeln för avslutad serie gör det
  inte. Därför är Vertivs organiska kvartalsorder avslutad fast pressmeddelandet 2026Q3 anger "over 100%". Det står i
  registrets tillägg och i ett test. Det är en tolkning av "senaste rad" som gjordes efter att värdena var lästa, men den
  är redovisad.

## 6. Text, hash och kontrollen – OK med anmärkning

- `git ls-files data` visar bara `data/README.md`. `data/raw/orders_sentences/` täcks av `.gitignore` (`data/*`).
- CSV:n har bara korta ord: `metric_as_stated` är högst 69 tecken, och citat i noterna är högst 8 ord (test).
- Alla 575 hashar och tal stämmer i R19:s egna kopior. `python -m ai_tracker.orders_check --frac 1.0` gav 617 rader,
  0 flyttade meningar, 0 fel i datum och 3 `still_stated` (punkt 5).
- **F-3 (should_fix):** `docs/kallor/order_orderstock.md` citerar två hela meningar ur Dells pressmeddelanden (15 och 12
  ord, under "Utanför läsmängden"). Det strider mot CLAUDE.md ("aldrig själva texten"). R15 gav samma fynd för P2a.
- Arbetsbladen och byggskriptet som tillämpade regeln om första dokumentet ligger bara i S3:s arbetsyta (N-6). CSV:n
  har alla fält, och R19:s kontroller av revideringarna (punkt 2) visar att regeln är rätt tillämpad.

## 7. publish och licens – OK

- Alla 61 serier har `publish=False`. `catalog.validate()` ger inga fel för `ob_`.
- Klassen är `ja` genom regeln för kurerade filer (`ROW_SERIES["orders_backlog.csv"]`, alla rader har `source_url` på
  www.sec.gov). Det följer `docs/datakallor/licensniva.md`: "SEC:s offentliga information och siffror som vi själva har
  extraherat ur dokument på sec.gov". Blocket i `licenses.py` är avgränsat och namnger spåret.
- Inga `ob_`-serier är kärnserier (test mot `state.register.CORE_SERIES`).

## Rättningar

| Nr | Fynd | Allvar | Rättning | Test (xfail tills rättat) |
|---|---|---|---|---|
| R-1 | F-1 | should_fix | Dela serien. 2025Q1 ("gas turbine orders") blir en egen definition. Från 2025Q2 blir talet "order bland nya kontrakt", och de konverterade reservationerna kodas som egen definition, så att orderingången i GW går att bilda. Det kräver en daterad registerändring (nytt mått eller ny komponent). Alternativet är en not och en etikett som säger att konverteringarna inte ingår | `test_gas_turbine_orders_wording_change_is_split` |
| R-2 | F-2 | should_fix | Låt `gap_periods` skriva "bara en gräns anges" när definitionen har en rad med `gt`/`lt` för perioden | `test_gap_reason_names_the_bound` |
| R-3 | F-3 | should_fix | Korta citaten i källdokumentet till högst tio ord eller skriv om dem med egna ord | `test_source_doc_has_no_long_quotes` |
| R-4 | F-4 | should_fix | Skriv i noten för Digital Realtys åtta serier med `dlr_share` (tecknade avtal) att andelen inte anges före 2025, med beläggen i punkt 5. Skriv beläggen i källdokumentets tolkning 9. Pröva inte serierna som kärnserier innan basen för 2021Q4–2024Q1 är belagd | `test_dlr_share_note_says_the_share_is_not_stated_before_2025` |

Anmärkningar utan rättning:

- N-1: Tre tolkningar rör registrets regler (punkt 1). Alla är redovisade i registrets tillägg.
- N-2: Gränser räknas olika i stoppregeln och i regeln för avslutad serie (punkt 5). Redovisat och testat.
- N-3: Eatons "flat organically" (Electrical Global 2025Q1) är 0 % i sak men kodas inte, eftersom ord inte kodas.
  Det ger en lucka och ett stopp i en serie som annars är hel.
- N-4: Kandidatregeln i koden är något vidare än listan i reglerna och committades med CSV:n.
- N-5: Eatons orderstock från 2026Q1 ("Total backlog") har ingen not om Boyd Thermal (Electrical Global) eller andra
  köp. Talen är rätt lästa, men en not som GE Vernovas om Prolec GE vore tydligare.
- N-6: Byggskriptet för regeln om första dokumentet och stoppen är inte committat (S3:s öppna punkt).
- N-7: Digital Realtys fotnot 2023Q2 säger att hyran över 1 MW innehåller en höjning från en ersatt hyra på 8 MW. Noten
  i CSV:n nämner det inte.
- N-8: Commit-meddelandet i `847c8eb` säger att stoppen bortser från gränser. Den ändringen finns i `620ca42` (S3:s
  öppna punkt).

## Vad som inte kunde verifieras

- Digital Realtys andel för 2021Q4–2024Q1 (punkt 5). Bilagorna säger inget om den, och 10-Q/10-K ingår inte i korpusen.
- Om GE Vernovas 7 GW för 2025Q1 innehåller konverterade reservationer. 2024Q4:s pressmeddelande anger ingen orderstock
  i GW.
- Att "demand" i Dells citat är order. Det är bolagets språk i citatet. Samtalen ingår inte i korpusen.
- Att ingen bilagetext lästes före 09:58 någon annanstans än i den delade cachen (punkt 1).
- Pressmeddelandet kan ha legat på bolagets sida några timmar före 8-K:t samma dag. Det påverkar inte known_from, som
  är en dag.
- Equinix är inte kodat och inte granskat.

## Tester

`tests/test_r19_order_orderstock.py` (inget nätverk, läser bara den committade CSV:n):

- Fastlåsta rader: de 65 raderna i stickprovet (hashprefix, definition, värde, period, inlämning) och en kontrollsumma
  över de 610 granskade raderna utom flödena i GW (F-1). En ändrad eller ny rad kräver ny granskning.
- Egenskaper som håller: Digital Realtys kategorier summerar till totalen (20 kvartal), GE Vernovas segment är
  kompletta i 11 kvartal, orderstock + reservationer = summan i GW (2025Q2 avrundat 1 GW), de kodade ordren i GW
  utesluter konverteringarna (beläggen för F-1), Eatons tolvmånadersorder är kompletta, known_from = inlämningsdagen
  och datumraden, Vertivs tio serier är avslutade, inga kärnserier, korta ord i CSV:n och `publish=False`.
- Fynd F-1 till F-4 som strikta xfail.
