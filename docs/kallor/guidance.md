# Källa: bolagens guidance (fas 4, spår E1)

Byggt och kontrollerat 2026-11-23. Bara extraktion: ingen guidance har jämförts med utfall och inga fel är
beräknade. Det görs först när orkestreraren har låst B2 för N1 i måttregistret (posten 2026-11-23 om B2).

Kod: `src/ai_tracker/sources/tsmc_guidance.py` (TSMC, deterministisk tolkning), `src/ai_tracker/sources/guidance_capex.py`
(läsare för den kurerade capex-filen), `src/ai_tracker/series/guidance.py` (katalogposter),
`src/ai_tracker/guidance_check.py` (stickprov). Data: `curated/guidance_capex.csv` (committad, bara siffror och
referenser). Tester: `tests/test_guidance.py` (syntetiska fixturer, inget nät). Hämtning:
`python -m ai_tracker.observations <nycklar>`, stickprov: `python -m ai_tracker.guidance_check`.

## Gemensamt

- **known_from** = dokumentets publiceringsdag: EDGAR:s `filingDate` för SEC-dokument, samtalsdagen för
  Microsofts transkript (samma dag som 8-K:n med resultatet). EDGAR:s `acceptanceDateTime` sparas också. En
  inlämning efter 17.30 ET får nästa arbetsdag som `filingDate` (Alphabets 10-Q 2024-07-23 kl. 23.12 UTC fick
  2024-07-24). Datumet är då konservativt.
- **period** = perioden som guidas. Kvartal (`Q`) är kalenderkvartal. Kalenderår (`CY`) lagras med frekvens A.
  Microsofts räkenskapsår (`FY`, juli–juni) lagras med frekvens A och period = kalenderåret då räkenskapsåret
  slutar, och det står i etiketten. Guidance är känd före periodens slut, så `lag_days` är negativt (−120 för TSMC,
  −200 för kvartal och −800 för år). Datatestet `known_from_after_period_end` håller.
- **Vintages.** Ett värde som upprepas i ett senare dokument ger ingen ny rad. Ett ändrat värde, t.ex. en
  uppdatering mitt i kvartalet eller ett nytt intervall för helåret, blir en ny vintage med sitt eget datum.
- **Licens.** SEC-dokument är offentliga (sec.gov/privacy). Från pressmeddelanden och transkript publiceras bara
  siffror med källhänvisning, aldrig text. Den ordagranna meningen för varje capex-värde finns bara i
  `data/raw/guidance_capex_sentences/` (gitignorerad). I CSV:n finns SHA-256 av meningen och dess plats.
  TSMC-serierna har `publish=True` med samma licens som `tsmc_revenue_m`. Capex-serierna har `publish=False` tills
  granskningen är gjord.

## TSMC (N2)

**Källa:** TSMC:s 6-K med kvartalsrapporten i EDGAR, samma submissions-filer som månadsintäkten. Fram till mitten av
2019 är 6-K:ns huvuddokument själva pressmeddelandet. Från 2019-10 är det ett försättsblad, och pressmeddelandet
(EX-99.1) och presentationen (EX-99.2) hittas via filens `index.json`. Alla 1 314 elektroniska 6-K gås igenom, och
136 inlämningar (163 dokument) innehåller guidance.

**Tolkning (deterministisk):** ett ankare ("management expects", "4Q25 Guidance", "now expects" och några till)
följt av "Revenue … to be between NT$/US$ x billion and/to y billion" inom 600 tecken. Därefter läses växelkurs och
marginaler i samma stycke. Kvartalet är **kalenderkvartalet som innehåller inlämningsdagen**. Om texten namnger ett
kvartal efter ankaret måste det stämma, annars stoppas tolkningen (`ParseError`). Ett felmärkt kvartal kan alltså
aldrig flytta ett värde bakåt i tiden.

| Nyckel | Innehåll | Enhet | Kvartal | Vintages |
|---|---|---|---|---|
| `tsmc_guid_rev_twd_lo/hi` | intäktsintervall i NT$ | mn TWD | 2006Q2–2017Q2 (45) | 51 / 50 |
| `tsmc_guid_rev_usd_lo/hi` | intäktsintervall i US$ | MUSD | 2017Q3–2026Q4 (38) | 39 / 39 |
| `tsmc_guid_fx` | antagen växelkurs | TWD per USD | 2008Q3–2026Q4 (74) | 76 |
| `tsmc_guid_gm_lo/hi`, `tsmc_guid_om_lo/hi` | brutto- och rörelsemarginal | % | 2006Q2–2026Q4 (83) | 87 |

- **Inga luckor** 2006Q2–2026Q4. Guidance blir känd 8 dagar före till 30 dagar efter kvartalets början (median
  17 dagar efter).
- **Bas.** Fram till 2006Q1 gällde guidance moderbolaget (unconsolidated), och de kvartalen tas inte med. 2006Q2
  angavs båda baserna, och koncernens intervall väljs. Från 2006Q3 gäller koncernen, alltså samma bas som
  `tsmc_revenue_m`. Före 2006 var guidance kvalitativ (volymer, utnyttjandegrad, ASP).
- **Valuta.** NT$-intervall t.o.m. 2017Q2 och US$ från 2017Q3. Växelkursantagandet finns från 2008Q3. Åren
  2008–2011 stod det bara i presentationen, som lämnades in dagen efter, och därför är `known_from` för fx en dag
  senare än för intäkten.
- **Uppdateringar mitt i kvartalet** (nya vintages): 2007-09-10 (Q3), 2008-12-01 (Q4), 2009-03-10 (Q1),
  2015-09-23 (Q3 och ett preliminärt intervall för Q4, känt redan före kvartalet), 2016-02-17 (Q1, jordbävningen)
  och 2019-02-15 (Q1, fotoresistproblemet). Om en uppdatering inte anger marginaler eller växelkurs gäller de
  tidigare värdena i `as_of`. 2007-09-10 sades att marginalerna skulle överträffa den tidigare övre gränsen. Det
  är kvalitativt och inte kodat. Kvalitativa besked utan siffror (2011-09-09: intäkten väntas överträffa
  guidance; 2019-01-28/29: guidance väntas hålla) är inte heller kodade.
- **Inkonsekvens i källan:** för 2019Q1 anger pressmeddelandet (2019-01-17) växelkursen 30,8 och presentationen
  (2019-01-18) 30,6. Båda sparas som vintages i dokumentordning.
- **Flagga för N2:s B2:** registret säger "mittpunkt i USD × antagen växelkurs". Det fungerar från 2017Q3. N2:s
  utvärdering börjar 2012-05, och för 2012–2017Q2 är intervallet redan i NT$. Där är NT$-mittpunkten det naturliga
  valet (ingen växelkurs behövs). Det bör skrivas in i registret innan B2 körs.

## Hyperscalers capex (N1)

**Metod.** Guidance är inte formelartad. Agenten läste varje kandidatmening (automatiskt urval: meningar om capex
med framåtblickande ord ur alla 8-K med Item 2.02, 10-Q och 10-K från 2020-07, 8-K med Item 7.01/8.01 och
Microsofts transkript) och kodade värdena. Varje rad i `curated/guidance_capex.csv` har siffror, enhet, typ
(`point/range/min/approx/direction`), definitionskod, period, `filed`, URL, accessionsnummer, plats (avsnitt och
meningsnummer enligt `guidance_capex.sentences`), SHA-256 av meningen och en kort not. Riktning kodas −2..+2
(+2 = kraftig ökning, +1 = ökar, 0 = i nivå med, −1 = minskar) mot en bas: `qoq`
(föregående kvartal), `yoy` (föregående år), `prior_fy` (föregående räkenskapsår) och `growth_vs_prior`
(tillväxttakten jämfört med föregående års takt). 101 rader.

### Definitioner jämfört med våra serier

Våra serier: `capex_*` = brutto, kontant köp av materiella anläggningstillgångar (kassaflödesanalysen), **utan**
amortering på finansiell leasing. `fin_lease_*` = amortering (principal) på finansiell leasing, separat.

| Bolag | Guidancens definition (kod) | Mot `capex_*` |
|---|---|---|
| Meta | "capital expenditures, including principal payments on finance leases" (`META_CAPEX_INCL_FL`). Uttryckligen från 2022-02. Före det står bara "capital expenditures", men samma pressmeddelanden redovisar utfallet inklusive amortering (sedan minst 2020Q2). Därför har alla rader samma kod | = `capex_meta` + `fin_lease_meta`, alltså direkt jämförbar med summan av två serier vi har |
| Alphabet | Pressmeddelanden: "capital expenditures" = köp av materiella anläggningstillgångar (`GOOGL_CAPEX`). 10-K/10-Q: riktning för "investment in our technical infrastructure" (`GOOGL_TECH_INFRA`), den största delen av capex men inte exakt capex | `GOOGL_CAPEX` = `capex_googl` (samma rad i kassaflödet). Leasing ingår inte |
| Amazon | 10-Q/10-K och pressmeddelandet 2026-10: "cash capital expenditures" = köp **netto** efter intäkter från försäljning och incitament (`AMZN_CASH_CAPEX`). VD-citat 2026-02 och aktieägarbrevet 2026-04: "capital expenditures"/"capex" utan angiven bas (`AMZN_CAPEX_UNSPEC`) | `capex_amzn` är brutto. Skillnaden (intäkter och incitament) finns inte som serie. Amazons "capital investments including finance leases" förekommer inte i guidance |
| Microsoft | "capital expenditures including finance leases" (`MSFT_CAPEX_INCL_FL`): kontant köp + **värdet av nya finansiella leasingavtal vid start**, alltså inte amortering. Från FY26 säger bolaget bara "capital expenditures" med samma innehåll. FY27Q1: en ändrad nyttjandeperiod gör att fler datacenterhyror blir operationella i stället för finansiella, och den guidade siffran påverkas | Inte jämförbar med `capex_msft` (kontant köp). Skillnaden ("finance leases acquired") finns inte i companyfacts, och `fin_lease_msft` (amortering) är något annat |

### Täckning, N1-perioden 2021Q4–2026Q3

Vad som var känt på N1:s prognosdag (kvartalets slut + 20 dagar) för kvartalet. `Q` = guidance för kvartalet,
`CY` = för kalenderåret, `FY` = för Microsofts räkenskapsår. `range/approx/min` = siffra, `dir` = bara riktning,
– = inget.

| Kvartal | MSFT | GOOGL | AMZN | META |
|---|---|---|---|---|
| 2021Q4 | – | – | – | CY approx |
| 2022Q1 | – | – | – | CY range |
| 2022Q2–2023Q1 | Q dir | – | – | CY range |
| 2023Q2–2023Q4 | Q dir | – | CY dir | CY range |
| 2024Q1–2024Q2 | Q dir | CY dir | CY dir | CY range |
| 2024Q3–2024Q4 | Q dir, FY dir | CY dir | CY dir | CY range |
| 2025Q1–2025Q2 | Q dir, FY dir | CY approx | CY dir | CY range |
| 2025Q3 | **Q min** (över 30 mdr), FY dir | CY approx | CY dir | CY range |
| 2025Q4 | Q dir, FY dir | CY range | CY dir | CY range |
| 2026Q1 | Q dir, FY dir | CY range | CY approx | CY range |
| 2026Q2–2026Q3 | **Q min**, CY approx, FY dir | CY range | CY approx | CY range |

**Bolagskvartal utan kvantitativ guidance (av 20 per bolag), och varför:**

- **Microsoft, 17:** 2021Q4–2025Q2, 2025Q4 och 2026Q1. Microsoft guidar bara i samtalet. Transkripten på
  microsoft.com finns från FY22Q3 (2022-04-26). Sidorna för FY21Q1–FY22Q2 ger 404, så 2021Q4 och 2022Q1 saknar
  helt guidance i våra källor. Från 2022Q2 finns riktning för nästa kvartal i varje samtal, men en siffra först
  2025-07 (över 30 mdr för 2025Q3). 10-Q/10-K säger bara att capex väntas öka under kommande år, utan period, och
  det kodas inte. 8-K:n innehåller ingen capex-guidance, utom den omräknade
  prognostabellen 2026-09-02, som bara upprepar över 50 mdr för 2026Q3. Den är inte kodad, eftersom tabelltexten
  saknar meningsgränser.
- **Alphabet, 13:** 2021Q4–2024Q4. Alphabet guidar i samtalet, och abc.xyz (transkript) nekas av proxyn.
  Pressmeddelandena (8-K) innehåller en siffra först för 2025 (2025-02-04). 10-K/10-Q ger riktning från 2024-01.
  Samtalens siffror för 2025 (t.ex. höjningen i juli 2025) och 2026 (april 2026) syns bara när ett senare
  EDGAR-dokument återger dem: 8-K:n 2026-06-04 återger aprilsamtalets 180–190 mdr och daterar värdet till 2026-06-04.
- **Amazon, 17:** 2021Q4–2025Q4. Amazon guidar capex i samtalet, och ir.aboutamazon.com nekas av proxyn.
  10-Q/10-K ger riktning från 2023-04. Den första siffran i EDGAR kommer 2026-02-05 (cirka 200 mdr, VD-citat). De
  220 mdr som pressmeddelandet 2026-10-29 bekräftar gavs uppenbarligen tidigare, troligen i samtalet
  för 2026Q2, men finns inte i EDGAR.
- **Meta, 0:** Meta anger sitt intervall för helåret i varje pressmeddelande (8-K EX-99.1, "CFO outlook
  commentary"), och upprepar det i 10-Q. Uppdateringen 2022-11-09 (8-K Item 7.01) är med. Riktning för nästa år
  finns från 2023-07.

**Värdar som behövs för full täckning:** `abc.xyz` (Alphabets transkript), `ir.aboutamazon.com` (Amazons
transkript), `investor.atmeta.com` (Meta, behövs inte eftersom 8-K räcker) och `efts.sec.gov` (EDGAR:s
fulltextsökning, som skulle göra sökningen i 8-K/10-Q heltäckande). Alla fyra nekas av proxyn, och inget har
kringgåtts. Microsofts transkript före FY22Q3 finns inte kvar på microsoft.com.

### Stickprov

`python -m ai_tracker.guidance_check --frac 0.2 --seed 20261123` hämtade om dokumenten för 20 av 101 capex-värden
och 33 av 163 TSMC-poster. **0 fel** (0 %), och ingen mening hade flyttat. Alla 101 capex-värden kontrollerades
också (`--frac 1.0`), med 0 fel. Kontrollen bekräftar att meningen finns på angiven plats (hash) och att talet
eller riktningsordet står i den. Den bekräftar **inte** semantiken: att perioden, basen eller definitionen är rätt
tolkad. Det bygger på agentens läsning, och ett oberoende granskningsspår bör läsa om de 20 raderna i stickprovet
(meningarna finns i `data/raw/guidance_capex_sentences/<id>.txt`) innan B2 används.

## Förslag: B2 för N1 (inte ett beslut)

Utgångspunkter: N1:s mål är `capex_hyp4` (brutto, utan leasing). Guidance finns med siffror i alla 20 kvartal bara
för Meta, i 7 för Alphabet och i 3 för Amazon och Microsoft. Alla fyra bolag har siffror bara 2026Q2–2026Q3.
Definitionerna stämmer direkt för Alphabet, och efter en justering för Meta.

**Rekommendation: B2 = B1 per bolag, ersatt av ett guidance-implicerat kvartal där bolaget har en kvantitativ
helårsguidance för kalenderåret, med samma andelslogik som N2:s B2.**

1. För bolag c och kvartal q i år Y, med guidance känd på prognosdagen (q:s slut + 20 dagar): G = mittpunkten av
   den senaste helårsguidancen för Y (för approx: värdet), omräknad till `capex_*`-bas.
   - Meta: G − förväntad amortering på leasing för året. Den förväntade amorteringen = kända kvartal av
     `fin_lease_meta` i år Y plus senast kända kvartal × återstående kvartal.
   - Alphabet (`GOOGL_CAPEX`): G direkt.
   - Amazon: bara `AMZN_CASH_CAPEX`/`UNSPEC`-siffror (2026). Netto mot brutto saknas som serie, så antingen behövs
     en ny serie för intäkter och incitament (XBRL-tagg för försäljning av anläggningstillgångar), eller så
     används B1 för Amazon. Mitt förslag är B1 tills serien finns.
   - Microsoft: B1. Siffrorna (min-värden, inklusive nya finansiella leasingavtal) går inte att räkna om till
     kontant capex utan "finance leases acquired", som saknas.
2. B2_c,q = (G − summan av årets kända kvartal av `capex_c`) × B1-andelen, där B1-andelen = B1:s prognos för q
   delat med summan av B1:s prognoser för årets okända kvartal. B2 för hyp4 = summan över bolagen.
3. Riktningar (`dir`) används inte i B2. Att använda dem, t.ex. att tvinga B1:s tecken q/q att följa Microsofts
   riktning, vore en egen variant och skulle kräva en egen Holm-budget.
4. Utvärderingen bör redovisas både för hela perioden och för de kvartal där B2 ≠ B1, och per bolag (N1b) för Meta
   (n = 20) och Alphabet (n = 7). För hyp4 skiljer sig B2 från B1 bara genom Meta i större delen av perioden.
   Antalet kvartal där guidance verkligen bidrar är litet, så bara stora skillnader går att upptäcka.

Läckage: G tas med `as_of(prognosdag)` på `guid_capex_<bolag>_cy_lo/hi`. Guidance som ges i samtalet efter
kvartalets slut (efter prognosdagen) kommer aldrig med, eftersom `known_from` är dokumentets datum.


## Rättning efter granskning R2 (2026-11-23)

Granskningen (`docs/granskning/r2_guidance.md`) hittade en rad som saknades. Alphabets pressmeddelande 2025-07-23
(8-K EX-99.1, accession 0001652044-25-000056) höjer capex för 2025 till cirka 85 mdr USD. Raden är nu tillagd
(`googl-r2f1`), så filen har 102 rader. Det tidigare påståendet att höjningen i juli 2025 inte finns i EDGAR är fel:
den finns i 8-K:n. Alphabets B2 för 2025Q3 bygger nu på 85 mdr.
