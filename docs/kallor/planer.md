# Källa: bolagens fleråriga planer (steg 2, spår D1)

Byggt och kontrollerat 2026-11-23. Avsnittet "Kodningsregler" skrevs och committades (3a46c63) **innan** någon
kandidatmening kodades. Senare tillägg är daterade och motiverade i avsnittet "Ändringar i reglerna". Bara
extraktion: inga takter, inga jämförelser mot utfall. Extraktionen ska granskas oberoende (R5) innan serierna
används, och därför har alla serier `publish=False`.

Kod: `src/ai_tracker/sources/plans_corpus.py` (korpus och kandidaturval), `src/ai_tracker/sources/plans.py` (läsare,
validering och serier), `src/ai_tracker/series/plans.py` (katalogposter), `src/ai_tracker/plans_check.py`
(stickprov). Data: `curated/plans.csv` (committad, bara siffror och referenser). Meningarna finns bara i
`data/raw/plans_sentences/<id>.txt` och kandidaterna i `data/raw/plans_candidates/` (gitignorerat). Tester:
`tests/test_plans.py` (syntetiska fixturer, inget nät). Körning: `python -m ai_tracker.sources.plans_corpus`
(korpus och kandidater), `python -m ai_tracker.observations <plan_-nycklar>` (serier),
`python -m ai_tracker.plans_check --frac 0.2` (stickprov).

Program D (framåtblick), led L4 (kontrakterad efterfrågan) och L5 (investeringar). Löptidsprofilen för RPO finns
redan i A1 (`rpo_<bolag>_12m`/`_24m` och `_after*`, se `docs/kallor/rpo.md`) och dupliceras inte här.

## Kodningsregler (låsta 2026-11-23, före kodningen)

### Vad som kodas

En rad per uttalat värde i `curated/plans.csv`. Bolag: Microsoft (`msft`), Alphabet (`googl`), Amazon (`amzn`), Meta
(`meta`), Oracle (`orcl`) och CoreWeave (`crwv`). Bara bolagets egna planer och egna mått, aldrig uttalanden om
kunder, marknaden eller branschen ("hyperscalers will spend …").

| Mått (`measure`) | Innehåll | Enhet |
|---|---|---|
| `CAPEX` | Capex för en period **efter** innevarande räkenskapsår (år Y+1 och senare) eller en flerårssumma. För Oracle och CoreWeave, som inte finns i E1:s fil, också innevarande år | MUSD eller kod |
| `INFRA` | Ett aviserat investeringsbelopp i infrastruktur, datacenter eller AI-infrastruktur som inte uttryckligen är capex ("invest $80 billion to build out AI-enabled datacenters", "$X in the U.S. over the next four years"). `scope` = `global` eller landskod (ISO 3166-1 alfa-2) | MUSD |
| `CAPACITY` | Datacenterkapacitet i effekt. `kind` avgör om det är ett mål eller ett redovisat läge (nedan). Relativa mål ("double our total data center footprint over the next two years") får enheten `multiple` (2 = fördubbling, +80 % = 1,8) | MW eller multiple |
| `BACKLOG` | Orderstock som inte är bolagets totala RPO i XBRL: CoreWeaves "revenue backlog" och orderstock eller RPO för ett segment som bolaget anger i text (t.ex. Google Cloud, Microsofts kommersiella RPO, AWS). Bolagets totala RPO kodas inte (A1) | MUSD |
| `COMMIT` | Avtalade, icke uppsägningsbara åtaganden för infrastruktur som anges med belopp i text (servrar, nätverk, datacenterbyggen, utrustning). Leasingavtal som inte har börjat kodas inte (A3), och inte heller allmänna inköpsåtaganden utan koppling till infrastruktur | MUSD |

**Kodas inte:** redovisade utfall för capex, intäktsmål (t.ex. Oracles mål för OCI-intäkter, de hör till L3),
enskilda kundavtal (de ingår i backlog och RPO), hypotetiska formuleringar och riskfaktorer ("we may need to make
significant investments") utan belopp eller period, capex för innevarande år och nästa kvartal för MSFT, GOOGL,
AMZN och META (E1:s domän i `curated/guidance_capex.csv`), och riktningar utan identifierbar period ("capital
expenditures will increase in coming years").

### Typ (`kind`)

- `point` exakt värde, `range` intervall, `approx` "about", "approximately", "roughly", "nearly", "~", `min` "over",
  "more than", "at least", "in excess of", "exceed", `max` "up to", "no more than".
- `direction`: kvalitativ riktning, `direction_code` −2..+2 som i E1: +2 kraftig ökning ("significantly",
  "meaningfully", "notably larger", "well in excess of double"), +1 ökning, 0 i nivå med, −1 minskning, −2 kraftig
  minskning. `direction_base`: `yoy` (perioden mot föregående period av samma längd) eller `growth_vs_prior`
  (tillväxten, i takt eller i dollar som det står, mot föregående periods tillväxt).
- `reported`: ett redovisat läge vid ett datum (CoreWeaves backlog, aktiv eller kontrakterad effekt, kapacitet som
  bolaget säger att det har lagt till). Värdet är ett faktum i dokumentet, inte en plan. `value_lo = value_hi`.

### Horisont

- `horizon`: `Y` ett räkenskaps- eller kalenderår, `SPAN` en flerårsperiod (summa över perioden), `BY` ett läge som
  ska nås senast ett datum ("by the end of 2027"), `ASOF` ett läge vid ett datum (för `reported`), `OPEN` ingen
  identifierbar slutpunkt (sparas i CSV:n men laddas inte som serie).
- `period_start` och `period_end` anges alltid för `Y`, `SPAN`, `BY` och `ASOF`. "Over the next N years" i ett
  dokument från datum d ges `period_start` = d och `period_end` = d + N år (sista dagen i månaden). "By 2028" eller
  "by the end of 2028" ger `period_end` = 2028-12-31. "In 2027" är kalenderåret 2027, "fiscal 2027" bolagets
  räkenskapsår (Microsoft juli–juni, Oracle juni–maj, övriga kalenderår).
- `year_basis`: `CY` eller `FY`. Ett räkenskapsår lagras med frekvens A och perioden = kalenderåret då det slutar
  (som i E1).
- Om perioden står i en annan mening i samma stycke (t.ex. "for fiscal 2026" i föregående mening) anges det i
  noten.

### Definition (`definition`)

Kod för vad talet mäter, med bolagets ordalydelse. Samma kod som i E1 när ordalydelsen är densamma
(`META_CAPEX_INCL_FL`, `MSFT_CAPEX_INCL_FL`, `GOOGL_CAPEX`, `AMZN_CASH_CAPEX`, `AMZN_CAPEX_UNSPEC`,
`GOOGL_TECH_INFRA`). Ny ordalydelse ger en ny kod, och koder slås aldrig ihop i en serie. Koderna listas i
`sources/plans.py` (`DEFINITIONS`) och nedan när de har använts.

### Datum

- `known_from` = `filed`: EDGAR:s `filingDate` för SEC-dokument (`acceptanceDateTime` sparas). För Microsofts
  samtal: samtalsdagen, som är samma dag som 8-K:n med resultatet (Item 2.02). För S-1 och 424B dagen för just det
  dokumentet.
- Samma värde i ett senare dokument ger en ny rad i CSV:n men ingen ny version i serien (första dokumentet räknas).
  Ett ändrat värde blir en ny version.
- Ett mål vars period redan har slutat när dokumentet kom är inget mål och avvisas av inläsningen, utom `reported`.

### Urval av kandidater (brett, efter R2-F1)

En mening är kandidat om den har ett **nyckelord** (capex, capital expenditure, capital spending, capital investment,
infrastructure, data center/datacenter, capacity, power, gigawatt, megawatt, GW, MW, backlog, remaining performance
obligation, commitment, committed, build-out, compute, eller "invest … in" följt av infrastruktur-, datacenter-,
AI- eller kapacitetsord) **och** något av följande, i alla tempus:

- ett dollarbelopp,
- ett effekttal (MW, GW, megawatt, gigawatt),
- ett årtal efter dokumentets år, eller en flerårsfras ("next N years", "multi-year", "through 20xx", "by 20xx",
  "coming years", "over time"),
- ett framåtblickande ord (expect, anticipate, plan, will, intend, target, on track, guide, outlook) tillsammans med
  capex- eller kapacitetsord.

Agenten läser alla kandidater. Antalet dokument, kandidater och kodade rader redovisas nedan.

### Korpus

- SEC EDGAR från 2022-01-01: varje 8-K med Item 2.02, 7.01 eller 8.01 (alla EX-99-bilagor och huvuddokumentet),
  varje 10-Q och 10-K, och för CoreWeave också S-1, S-1/A och 424B.
- microsoft.com: Microsofts sidor för resultatsamtalen (samma adresser som E1 och B4).
- Övriga IR-värdar provas en gång. Nekas de listas de, och inget kringgås.

### Stickprov

`python -m ai_tracker.plans_check --frac 0.2` hämtar om dokumenten för 20 % av raderna och kontrollerar att
meningen finns på angiven plats (SHA-256) och att talet eller riktningsordet står i den. Felandelen redovisas. Ett
oberoende granskningsspår (R5) läser om källorna innan serierna används.

## Ändringar i reglerna (2026-11-23, under kodningen)

Alla ändringar gjordes innan de berörda meningarna kodades.

1. **Långa meningar.** Pressmeddelandenas punktlistor och tabeller blir en enda "mening" på över 1 500 tecken, och
   den första versionen av urvalet hoppade över dem. CoreWeaves aktiva och kontrakterade effekt står bara i sådana
   listor. Nu är en lång mening kandidat om ett nyckelord har ett dollarbelopp eller ett effekttal inom 200 tecken
   (`is_long_candidate`). Det gav 257 nya unika kandidater. Bara CoreWeaves listor innehöll kodbara värden.
2. **Redovisade nivåer med reservation.** Ett läge vid ett datum (`ASOF`) får `kind` `reported` (exakt), `approx`
   eller `min` ("more than 850 MW"). Det blir **en** serie per definition (fältet `value`), och reservationen står kvar
   i CSV:n. Ett intervall (`range`) vid ett datum ger `lo` och `hi`.
3. **Enskilda anläggningar** (Microsofts Fairwater, "scale to two gigawatts", Oracles största datacenter på 800 MW)
   kodas inte. `CAPACITY` gäller bolagets samlade kapacitet.
4. **Åtaganden (`COMMIT`)** kodas bara där texten knyter totalen till infrastruktur och ordalydelsen är stabil: Meta
   (alla kvartal), Oracle och CoreWeave. Alphabets "material purchase commitments and other contractual
   obligations" (energi, licenser, innehåll, infrastruktur, med fyra olika ordalydelser 2021–2026) och Amazons
   åtagandetabell (skuld, leasing, inköp) är allmänna och kodas inte. Se "Inte kodat".
5. **Belopp i annan valuta än USD** kodas inte (CoreWeaves £1,5 mdr i Storbritannien). Ingen valutaomräkning görs.
6. **Bolagets egna köp som kund** (Metas avtal om molnkapacitet för 40 mdr USD, Amazons OpenAI-aktier) kodas inte som
   enskilda händelser. De ingår i nästa kvartals åtagandetotal där bolaget redovisar en sådan.

## Korpus och urval (körning 2026-11-23)

| | Antal |
|---|---|
| Dokument | 541 (MSFT 110 varav 20 samtal, AMZN 106, GOOGL 92, ORCL 78, CRWV 78, META 77), inlämnade 2022-01-18 till 2026-11-12 |
| Hämtning misslyckad | 1: Microsofts samtalssida för FY22 Q2 (HTTP-fel, sidan finns inte kvar) |
| Kandidater | 4 275 meningar, 2 903 unika: dollar 1 739, framåtblickande ord 587, horisont 248, effekt 72, långa 257 |
| Kodade rader | 127 i `curated/plans.csv` |

Agenten läste alla unika kandidater i två nivåer. Nivå 1 (nyckelord för capex, kapacitet, infrastruktur eller
backlog tillsammans med framåtblickande ord, ett senare årtal, ett effekttal eller ordet backlog, cirka 1 150
meningar) lästes i sin helhet. Nivå 2 (cirka 1 500) sorterades först automatiskt i kategorier som inte kan innehålla
planer (leasing, skuld, aktier, skatt, förvärv, resultattabeller, redovisad capex, värdepapper, intäkter, total RPO)
och resten (507 meningar) lästes. Kategoriseringen är ett lässtöd, inte en regel: en mening i en sådan kategori
kunde fortfarande ha kodats, men ingen hade ett kodbart värde i stickprovet som lästes för hand.

## Rader och serier

| Bolag | Mått | Rader | Innehåll |
|---|---|---|---|
| Meta | CAPEX | 15 | Nästa års intervall (2023, 2024) och riktning (2024–2026), från 8-K och 10-Q |
| Meta | COMMIT | 20 | Icke uppsägningsbara åtaganden utan leasing, varje kvartal 2021Q4–2026Q3 |
| Microsoft | BACKLOG | 19 | Kommersiellt RPO från samtalen, 2022Q1–2026Q3 (FY22 Q2-sidan saknas) |
| Microsoft | CAPEX | 3 | FY25 och FY26: riktning, och FY26-tillväxten lägre än FY25 |
| Microsoft | CAPACITY | 6 | AI-kapacitet +80 % FY26, fördubblat datacenterfotavtryck på två år (sagt 2025-10, upprepat 2026-04 och 2026-07), 1 GW tillagt per kvartal 2026Q1 och Q2 |
| Amazon | CAPEX | 2 | 2026 ökar, 2027 ökar kraftigt (10-Q) |
| Amazon | INFRA | 5 | AWS-investeringar per land: Indonesien, Kanada (laddas), Mississippi, Saudiarabien, Mexiko (utan slutår, `OPEN`) |
| Amazon | CAPACITY | 3 | Effekt tillagd på 12 månader (3,8 GW till 2025-09, 3,9 GW 2025), total effekt fördubblad till slutet av 2027 |
| Alphabet | CAPEX | 2 | 2026 (teknisk infrastruktur) och 2027 (capex) ökar kraftigt |
| Alphabet | BACKLOG | 5 | Google Clouds backlog 2025Q3 och 2026Q1–Q3 |
| Oracle | CAPEX | 4 | FY26 50 mdr USD, FY27 ökar (två dokument), FY29 minskar efter toppen FY27–FY28 |
| Oracle | CAPACITY | 2 | Fördubblad datacenterkapacitet 2025, 850 MW levererat i FY27 Q1 |
| Oracle | COMMIT | 4 | Ovillkorade inköpsåtaganden 2025-11 till 2026-08 (ny definition 2026-08) |
| CoreWeave | BACKLOG | 10 | Revenue backlog 2023Q4, 2024Q4 och 2025Q1–2026Q3 |
| CoreWeave | CAPACITY | 21 | Aktiv effekt 2022Q4–2026Q3, kontrakterad effekt 2024Q4–2026Q3, mål: mer än 1,85 GW aktiv effekt vid årsskiftet 2026, mer än 8 GW till 2030, mer än 5 GW AI-fabriker till 2030 |
| CoreWeave | CAPEX | 1 | 2026: 37–39 mdr USD |
| CoreWeave | COMMIT | 5 | Utrustning i hyrda datacenter (intervall, 2025Q4–2026Q3), byggåtaganden 2,1 mdr USD 2026Q3 |

Sammanlagt 36 serier (`plan_<definition>[_<land>]_<horisont>_<fält>`), alla G5, `revised=True`, `publish=False`:

- **Planer** (frekvens A, perioden = året då horisonten slutar, räkenskapsår = året då det slutar): `..._y_lo/hi/value`,
  `..._y_dir_yoy`, `..._y_dir_growth_vs_prior`, `..._by_...` (mål senast ett datum), `..._span<N>y_...`
  (flerårsperiod). `lag_days` = det mest negativa avståndet mellan `known_from` och periodens slut i serien.
- **Redovisade nivåer** (frekvens Q, perioden = kalenderkvartalet för balansdagen, Oracles 30 nov = Q4 som i A1):
  `plan_crwv_backlog_asof_value`, `plan_crwv_active_power_asof_value`, `plan_crwv_contracted_power_asof_value`,
  `plan_msft_commercial_rpo_asof_value`, `plan_googl_cloud_backlog_asof_value`, `plan_meta_noncancel_commit_asof_value`,
  `plan_orcl_uncond_oblig_asof_value` med flera.
- Rader med horisont `OPEN` (Amazons Mississippi, Saudiarabien och Mexiko) finns i CSV:n men laddas inte.
- Luckor är avsiktliga (ingen sa något om perioden) och listas automatiskt i `warehouse.KNOWN_GAPS` via
  `plans.known_gaps()`. Aktualitet: 1 100 dagar för planer (Meta gav ett intervall för nästa år bara 2022 och 2023),
  200 dagar för nivåer som redovisas varje kvartal och 400 för glesa nivåer.

## Datum och läckage

- `known_from` = EDGAR:s `filingDate` för SEC-dokument (`acceptanceDateTime` sparas i `accepted`, och läsaren
  kontrollerar att de stämmer, −4 till +1 dagar). Microsofts samtal dateras till dagen för 8-K:n med resultatet
  (Item 2.02), samma eftermiddag. S-1, 424B och presentationer (8-K EX-99.2) dateras till sitt eget `filingDate`.
- En plan vars period redan har slutat när dokumentet kom avvisas. Ett redovisat läge måste avse ett datum före
  dokumentet. För MSFT, GOOGL, AMZN och META avvisas capex för innevarande år (det hör till E1).
- **Historik som publiceras sent dateras sent.** CoreWeaves backlog för december 2023 och 2024 står först i
  investerarpresentationen 2026-09-17 och har det datumet (S-1 angav bara RPO). CoreWeaves aktiva effekt 2022–2024
  har S-1:ns datum 2025-03-03. Alphabets 2027-riktning har datumet för 8-K:n 2026-06-04, inte samtalet 2026-04-29.
  Allt det är konservativt.
- `python -m ai_tracker.warehouse` är grön (alla kontroller, inklusive `known_from_after_period_end` och aktualitet).

## Överlapp med andra spår

- **E1 (`curated/guidance_capex.csv`).** E1 kodade också riktning och intervall för nästa år för de fyra stora. D1
  kodar dem igen enligt sina egna regler, så att planserierna är kompletta. Kolumnen `xref` anger E1-raden när
  meningen är densamma (17 rader). D1 och E1 skiljer sig i kodningen på två punkter: Metas "similarly significant …
  dollar growth in 2026" har i D1 två koder (yoy +2 och growth_vs_prior 0), och "dollar growth notably larger in 2026
  than 2025" kodas i D1 som growth_vs_prior +2 (E1: yoy +2). Microsofts `prior_fy` i E1 heter `yoy` i D1. Använd
  antingen E1- eller D1-serien för samma bolag och år i en modell, inte båda.
- **Möjlig lucka i E1:** Microsofts samtal 2026-10-28 (mening #226) sänker kalenderåret 2026 till "approximately
  $170 billion" (från cirka 190 mdr USD, `msft-26`). Raden finns inte i `guidance_capex.csv`. Den hör till E1:s domän
  (innevarande år) och är inte kodad här.
- **A1 (RPO).** Bolagens totala RPO och löptidsprofilen (`rpo_<bolag>`, `_12m`/`_24m`, `_after*`) finns i A1 och
  dupliceras inte. D1 tar bara orderstock som A1 inte har: CoreWeaves backlog (RPO plus avtal som ännu inte är RPO),
  Google Clouds del och Microsofts kommersiella del.
- **A3 (leasing).** Leasingavtal som inte har börjat (även CoreWeaves "354 MW undelivered" vid hyrda anläggningar)
  hör till A3 och kodas inte.
- **B4 (AI-nyckeltal).** B4 kodar kapacitetsbrist (−2..+2). D1 kodar kapacitet i MW och mål. Inget överlapp i värden.

## CoreWeaves backlog jämfört med RPO

| Balansdag | Backlog (D1) | RPO (A1, `rpo_crwv`) | Skillnad i texten |
|---|---|---|---|
| 2025-03-31 | 25,9 | 14,7 | 11,2 "other amounts … under committed customer contracts" (OpenAI-avtalet, ännu inte RPO) |
| 2025-09-30 | 55,6 | 50,0 | – |
| 2025-12-31 | 66,8 | 60,7 | – |
| 2026-03-31 | 99,4 | 98,8 | – |
| 2026-06-30 | 104 → 104,2 | 103,7 | – |
| 2026-09-30 | cirka 132,5 | 132,3 | – |

Mdr USD. Det är en datakontroll (nivåerna mot bolagets egna siffror), ingen analys: backlog ≥ RPO i alla kvartal,
som definitionen kräver.

## Licens och värdar

- SEC EDGAR: *"Information presented on sec.gov is considered public information and may be copied or further
  distributed by users of the web site without the SEC's permission."* (sec.gov/privacy). microsoft.com: bara
  extraherade siffror med källhänvisning, aldrig text. `publish=False` tills R5 har granskat.
- SEC via `ai_tracker.http` med deklarerad User-Agent från `.env` (`SEC_USER_AGENT`), 5 anrop/s. Cirka 750 anrop i
  första körningen (submissions, index och dokument), därefter återanvänds råkopiorna.
- **Nekade av proxyn** (ett försök vardera, inget kringgått): `investor.oracle.com`, `investors.coreweave.com`,
  `abc.xyz`, `ir.aboutamazon.com`, `investor.atmeta.com`, `blogs.microsoft.com` (Microsofts blogginlägg om 80 mdr USD
  för AI-datacenter FY25), `news.microsoft.com`, `www.coreweave.com`, `aws.amazon.com`, `about.fb.com`,
  `blog.google` och `efts.sec.gov`. `www.oracle.com/news` och `www.microsoft.com` svarade. Oracles pressmeddelanden
  finns också i 8-K, så oracle.com användes inte.
- Följd: planer som bara sägs i samtal (Oracles capex-guidance FY25–FY26 före mars 2026, CoreWeaves capex-guidance
  2025 och tidigare 2026-intervall, Amazons AWS-backlog, Alphabets backlog för 2025Q4) saknas.

## Inte kodat (med plats, för senare beslut)

- **Intäktsmål** (L3): Oracles OCI-plan 18/32/73/114/144 mdr USD (8-K 2025-09-09, mening #18), Oracles mål om
  225 mdr USD intäkt FY30 (8-K 2026-10-28, #5), AWS-tillväxt över 40 % 2027 och 2028 (8-K 2026-10-29, #20).
- **Allmänna åtagandetotaler**: Alphabets "material purchase commitments and other contractual obligations" i varje
  10-Q och 10-K (13,7 mdr USD 2021 till 924,4 mdr USD 2026Q3, med ändrad ordalydelse), Amazons åtagandetabell (Note 7).
- **Villkorade åtaganden och garantier**: Alphabets backstops för datacenter (upp till 75,7 mdr USD 2026Q3), Metas
  villkorade köp av molnkapacitet (14,72 mdr USD), Amazons lånefacilitet för infrastrukturköp (upp till 80 mdr USD).
- **Enskilda kundavtal**: OpenAI (Microsoft 250 mdr USD, Amazon 38 + 100 mdr USD, CoreWeave 22,4 mdr USD), Meta hos
  CoreWeave (14,2 mdr USD), Anthropic hos Amazon (5 GW), Jane Street hos CoreWeave. De ingår i backlog och RPO.
- **Riktning utan period**: "capital expenditures to increase in coming years" (Microsofts 10-Q och 10-K), Metas
  "beyond 2024 … growing infrastructure investments", Oracles "next few fiscal years".
- **Oklart omfång**: CoreWeaves investering i Spanien, Sverige och Norge (2,2 mdr USD) som "more than double our MW of
  capacity by the end of 2025" (S-1, #2539): det framgår inte om kapaciteten gäller Europa eller hela bolaget.

## Stickprov

`python -m ai_tracker.plans_check --frac 0.2 --seed 20261123` hämtade om dokumenten för 25 av 127 rader, utan cache.
**0 fel (0 %)**, och ingen mening hade flyttat. Kontrollen bekräftar att meningen finns på angiven plats (SHA-256)
och att talet eller riktningsordet står i den. Alla 127 rader kontrollerades också (`--frac 1.0`). Den första fulla körningen flaggade 7 rader, och alla var brister i kontrollens mönster, inte i kodningen: "$34-39 billion" (Metas intervall skrivs med enheten en gång, 3 rader), "another gigawatt" (Microsoft, 2 rader) och tabelltotaler "(in millions)" utan enhetsord (Oracle, 2 rader). Mönstren rättades och har egna tester, och därefter gav den fulla körningen **0 fel av 127**.

Agenten läste dessutom om de 25 meningarna mot kodningen (period, enhet, definition, typ): 0 avvikelser. Det är
samma läsare som kodade och därför ingen oberoende kontroll. **R5 bör läsa om stickprovet** (meningarna i
`data/raw/plans_sentences/<id>.txt`) och särskilt pröva:

1. Microsofts "this year" (AI-kapacitet +80 %) tolkat som FY26.
2. Microsofts och Amazons fördubblingsmål: basnivån anges inte som tal, och Microsofts tvåårsperiod räknas från
   2025-10-29 också när målet upprepas.
3. CoreWeaves "8 GW by 2030" (aktiv eller kontrakterad effekt framgår inte) och skillnaden mot "5 GW AI factories".
4. Metas åtagandetotal som infrastrukturmått: sammansättningen ändras (innehåll 2024Q4–2025Q1, molnkapacitet från
   2025Q3).
5. Oracles definitionsbyte 2026-08 ("terms of one year or greater").

## Kända problem

- Täckningen är bara det som står i EDGAR och på microsoft.com. Bolagens samtal (utom Microsofts) nekas.
- Korpusen börjar 2022-01-01. Metas intervall för 2022 (sagt i oktober 2021) finns bara i E1 (`meta-06`).
- Planserierna är glesa och oregelbundna. En saknad period betyder att inget sades, inte noll.
- Relativa kapacitetsmål (`multiple`) har ingen bas i MW och kan inte räknas om till MW utan antaganden.
