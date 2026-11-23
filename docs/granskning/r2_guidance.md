# R2: oberoende granskning av bolagens guidance (underlag för B2)

Granskningsspår R2, 2026-11-23. Underlaget är `curated/guidance_capex.csv` (101 rader), TSMC-serierna
`tsmc_guid_*` i `data/observations.parquet` (603 observationer, 163 tolkade dokument) och koden på
`auto2/r2-guidance` (8ab1cf0). Granskningen är adversariell: varje värde har lästs om i **originaldokumentet,
hämtat på nytt** från www.sec.gov respektive microsoft.com (inte E1:s cache), med en egen textkonvertering
(BeautifulSoup) och egna sökmönster, och varje datum har jämförts med EDGAR:s submissions-API (`filingDate`,
`acceptanceDateTime`) hämtat samma dag. Inga produktionsfiler och ingen CSV är ändrade. Tester finns i
`tests/test_r2_guidance.py`: fel är markerade `xfail(strict=True)`, och när felet rättas ska markeringen tas bort.

Ingen guidance har jämförts med utfall och inga prognosfel har beräknats. Pressmeddelandenas tabeller (till exempel
kvartalets köp av anläggningstillgångar i Alphabets FCF-tabell) syntes ofrånkomligen vid läsningen, men inget
användes. Definitionskontrollen för Meta (avsnitt 3.3) jämför bara två redovisade mått för samma kvartal och skriver
bara ut differensen, inte nivåerna.

Hämtningar gjordes med den ärliga klienten (`ai_tracker.http`, SEC-identitet från `.env`). Proxyn nekade
`abc.xyz`, `ir.aboutamazon.com` och `efts.sec.gov` (ett försök vardera, ingen kringgång). Därför har bolagens
samtal och EDGAR:s fulltextsökning inte kunnat användas. I stället gicks alla 8-K för Meta (2020-07–2026-11),
Alphabet (2024-01–2026-11) och Amazon (2023-01–2026-11) igenom, med alla .htm-bilagor via `index.json`.

## 1. Dom

| Del | Används i B2 | Dom | Kort motivering |
|---|---|---|---|
| **Meta** (CY, kvantitativ) | ja, alla 29 rader | **GODKÄND** | 29 av 29 rader stämmer med källan i värde, enhet, guidat år, definition och datum. Inget 8-K med en capex-siffra saknas för 2021–2026. `known_from` = 8-K:ns filingDate, och inget tidigare dokument finns. Definitionen (inkl. amortering på finansiell leasing) stämmer med `capex_meta` + `fin_lease_meta` inom ±5 MUSD för alla kvartal 2023Q1–2026Q3 |
| **Alphabet** (CY, kvantitativ) | ja, 4 rader (5 efter rättning) | **GODKÄND MED RÄTTNINGAR** | De 4 raderna stämmer. **En rad saknas (R2-F1):** pressmeddelandet 2025-07-23 höjer 2025 till cirka 85 mdr. B2 för 2025Q3 använder i dag 75 mdr. Påståendet i `docs/kallor/guidance.md` att höjningen i juli 2025 inte finns i EDGAR är fel |
| Amazon | nej (B1) | GODKÄND (stickprov) | 5 av 5 stickprovsrader stämmer. Inga capex-siffror i 8-K saknas |
| Microsoft | nej (B1) | GODKÄND (stickprov) | 5 av 5 stickprovsrader stämmer, inklusive kvartalsmappning FY→kalender. Alla 29 rader är daterade till samtalsdagen, som också är dagen för 8-K:n med resultatet (Item 2.02) |
| **TSMC** | ja (N2) | **GODKÄND** | 26 kvartal lästa för hand: intervall, valuta, växelkurs, datum och uppdateringar mitt i kvartalet stämmer exakt med lagrade vintages (0 fel). Alla 603 observationer är daterade till en verklig 6-K-inlämning med samma värde, och ingen ligger före EDGAR:s acceptance |
| Datering, alla rader (punkt 3) | – | **OK** | 0 av 72 SEC-rader i CSV:n och 0 av 603 TSMC-observationer är daterade före dokumentets filingDate eller acceptance-dag (New York-tid) |

**Slutsats för B2:** TSMC-delen (N2) och Meta-delen (N1) kan användas som de är. Alphabet-delen kan användas
först när R2-F1 är rättad, annars är Alphabets B2 för 2025Q3 byggd på ett inaktuellt värde. Inget läckage hittades.

## 2. Fel

| Nr | Del | Fel | Belägg | Påverkar B2 |
|---|---|---|---|---|
| **R2-F1** | Alphabet | Rad saknas: CY2025 ≈ 85 000 MUSD (`approx`, `GOOGL_CAPEX`) | 8-K Item 2.02, EX-99.1 `googexhibit991q22025.htm`, accession 0001652044-25-000056, filingDate 2025-07-23, acceptance 2025-07-23T20:01:33Z (16.01 ET). VD-citatet: kapitalutgifterna 2025 höjs till "approximately $85 billion". Plats med `guidance_capex.sentences` på `tsmc_sec.to_text`: mening #16, SHA-256 `24e77f6e084fca87e4de7d0fefc0fe445402c81d1ef0ce9eaa6fcb0130fad39a` | **Ja.** `as_of(2025-10-20)` (prognosdagen för 2025Q3) ger 75 000 i stället för 85 000 för både lo och hi. Övriga kvartal påverkas inte: 2025Q2 (2025-07-20) ligger före dokumentet, och 2025Q4 har 91–93 mdr |
| R2-F2 | Alphabet, dokumentation | `docs/kallor/guidance.md` säger att "samtalens siffror för 2025 (t.ex. höjningen i juli 2025) … syns bara när ett senare EDGAR-dokument återger dem" | Se R2-F1 | Nej (text), men täckningstabellen och antalet rader (101) behöver uppdateras |

Orsak till R2-F1: E1:s automatiska kandidaturval byggde på framåtblickande ord. Meningen är formulerad i presens
("we are increasing our investment in capital expenditures in 2025 to approximately $85 billion") och saknar
sådana ord. R2 gjorde en bredare sökning (varje mening om capex med ett dollarbelopp, utom redovisade utfall) i alla
8-K för Meta, Alphabet och Amazon och hittade inga fler saknade värden.

## 3. Belägg

### 3.1 Capex, raderna som B2 använder (alla 33)

Alla 29 Meta-rader (meta-01–15, 17–20, 22, 24, 26–28, 30, 32–35) och de 4 Alphabet-raderna (googl-05, 09, 12, 15)
lästes i originaldokumentet. Värdena och datumen finns som parametrar i `test_b2_capex_row_matches_source`.

- **Värde och enhet:** alla stämmer. Meta anger "$x-y billion" och Alphabet "$x billion", "$x billion to $y
  billion" och "$x to $y billion", vilket är lagrat som MUSD.
- **Guidat år:** stämmer. meta-13 och meta-14 ("We expect capital expenditures to be in the range of $30-33
  billion", utan år) står i stycket om 2023 års utsikter, och de sänker 34–37 respektive upprepar 30–33. Det
  stämmer med 2023. meta-05/06 och meta-10/11 är två meningar i samma dokument (innevarande och nästa år).
- **Definition:** `META_CAPEX_INCL_FL` är korrekt för alla Meta-rader. Från 2022-02 (meta-07–10) och 2025-04
  (meta-27 och framåt) står "including principal payments on finance leases" i själva meningen. Övriga år finns
  det i samma pressmeddelandes highlights ("Capital expenditures, including principal payments on finance leases,
  were …"), redan i 2020Q3-meddelandet (meta-01). `GOOGL_CAPEX` är korrekt: Alphabets meddelanden definierar
  capital expenditures som "purchases of property and equipment" (FCF-tabellen), alltså samma rad som `capex_googl`.
  googl-15 (2026-06-04) återger samtalet 2026-04-29 och har samma definition.
- **Datum:** `filed` = EDGAR:s filingDate och `accepted` = acceptanceDateTime för alla 33 rader. Meta lämnar in
  16.03–16.47 ET (meta-12: 06.14 ET) och Alphabet 16.01 ET (googl-15: 17.07 ET), alltså före 17.30, så att
  filingDate är samma dag. **Inget tidigare dokument:** Metas och Alphabets 10-Q kommer senare. Alphabets
  pressmeddelande för 2026Q1 (2026-04-29) innehåller inte 180–190 mdr, så googl-15:s datum 2026-06-04 är det
  första EDGAR-dokumentet. Den verkliga första publiceringen var samtalet 2026-04-29, alltså tidigare. Det är
  konservativt och inget läckage.
- **Fullständighet:** genomgången av alla 8-K visar att varje Meta-siffra 2020-10–2026-10 finns i CSV:n, utom
  helåret **2020** ("approximately $16 billion", 2020-10-29). Det ligger före N1:s period och påverkar inte B2.

### 3.2 Capex, stickprov bland övriga rader (seed 20261124, 20 % av 68 = 14 rader)

| Rad | Kodning | Källan | Dom |
|---|---|---|---|
| amzn-05, amzn-06 | 2024, +2 yoy, cash capex | 10-Q 2024-05-01 / 2024-08-02: cash capex "meaningfully increase in 2024" | rätt |
| amzn-10 | 2025, +1 yoy | 10-Q 2025-08-01: investeringarna bakom cash capex "we expect to increase in 2025" | rätt (som noten säger, investeringarna snarare än cash capex ordagrant) |
| amzn-13 | 2026 ≈ 200 mdr, UNSPEC | 8-K 2026-02-05, VD-citat "about $200 billion in capital expenditures across Amazon in 2026" | rätt |
| amzn-15 | 2026 ≈ 200 mdr, UNSPEC | 8-K Item 7.01 2026-04-09 (aktieägarbrevet): "approximately $200 billion in capex in 2026" | rätt. Accepterad 2026-04-08 18.02 ET, så filingDate är en dag konservativ |
| googl-07, googl-08 | 2025, +1 yoy, tech infra | 10-Q: "We expect to increase, relative to 2024, our investment in our technical infrastructure" | rätt |
| googl-16 | 2027, +2 yoy | 8-K 2026-06-04: 2027 "significantly increase compared to 2026" | rätt |
| meta-25 | 2025, +2 yoy | 8-K 2024-10-30: "significant capital expenditures growth in 2025" | rätt |
| msft-04 | 2023Q1, +1 qoq | samtal FY23Q2 (2023-01-24): "sequential increase" för FY23Q3 = jan–mar 2023 | rätt |
| msft-06 | 2023Q3, +1 qoq | samtal FY23Q4 (2023-07-25): "increase sequentially" för FY24Q1 | rätt |
| msft-08 | 2024Q1, +2 qoq | samtal FY24Q2 (2024-01-30): "increase materially on a sequential basis" | rätt |
| msft-10 | FY2025, +1 prior_fy | samtal 2024-04-25: "FY25 capital expenditures to be higher than FY24" | rätt |
| msft-16 | FY2026, −1 growth_vs_prior | samtal 2025-01-29: "the growth rate will be lower than FY25" | rätt |

**0 fel av 14.** För stickprovens 10-Q-rader (Amazon, Alphabet) lästes också bolagens pressmeddelanden samma dag. De
innehåller inte samma riktning, så inget tidigare dokument finns.

### 3.3 Metas definition mot våra serier (identitetskontroll, inga utfall mot guidance)

Metas pressmeddelanden redovisar kvartalets "capital expenditures, including principal payments on finance
leases". Differensen mot `capex_meta` + `fin_lease_meta` för samma kvartal (senaste versionen):

- 2023Q1–2026Q3 (12 kvartal med uttalandet, Q4-meddelandena har det inte): −4 till +5 MUSD, alltså avrundning. Definitionen i registret stämmer.
- 2020Q3–2022Q3: −124 till +2 MUSD (−2,2 % till +0,1 %, störst 2022Q1). För 2021 stämmer i stället den **första**
  versionen (±5 MUSD), och senare versioner är omräknade. För 2022 avviker båda versionerna, och en trolig förklaring är att Meta från 2022 redovisar köpen
  "net of proceeds" (ej verifierat). Det är en liten avvikelse i målserien, inte i guidancen, och den är liten mot intervallens bredd (1–20 mdr). Den bör
  nämnas i B2:s resultat men kräver ingen rättning.

### 3.4 TSMC (N2)

Urval: 25 % av de 83 kvartalen 2006Q2–2026Q4 med seed 20261124 (21 kvartal) plus 2006Q2, 2008Q3, 2017Q2,
2017Q3, 2019Q1, 2020Q1, 2022Q4 och 2026Q4, alltså 26 kvartal. För varje kvartal hämtades **alla** 6-K som lämnades
in från 20 dagar före kvartalet till kvartalets slut (412 inlämningar, och från 2019-10 bilagorna via
`index.json`). De söktes med ett eget, bredare mönster för intervall ("NT$/US$ x [billion] and/to/– y billion" nära
"expect/guidance/outlook"), och varje träff lästes för hand. Resultatet finns som parametrar i
`test_tsmc_guidance_matches_hand_reading`: lagrade vintages för lo, hi och växelkurs är **exakt** lika med
handläsningen för alla 26 kvartal.

- **Valuta:** NT$ t.o.m. 2017Q2 (213–216 mdr NT$, 2017-04-13) och US$ från 2017Q3 (8,12–8,22 mdr US$, 2017-07-13). Stämmer.
- **2006Q2:** 6-K:n 2006-04-28 anger både moderbolagets intervall (79–81) och koncernens (80–82), och koncernens
  är vald. Pressmeddelandet 2006-04-27 (6-K 0001145549-06-000546) innehåller ingen guidance, så 2006-04-28 är det
  första EDGAR-dokumentet.
- **Växelkurs 2008–2011** står bara i presentationen, som lämnades in dagen efter (2008Q3: 30,20 den 2008-08-01;
  2009Q1: 32,66 den 2009-01-23; 2009Q2: 33,62 den 2009-05-04 efter release 2009-04-30). Stämmer. Från 2012 står
  den i pressmeddelandet.
- **Uppdateringar mitt i kvartalet** i urvalet: 2009-03-10 (2009Q1: 36–38, marginaler 14–16 % och −2–0 %, ingen ny
  växelkurs) och 2019-02-15 (2019Q1: 7,0–7,1 US$, marginaler 41–43 % och 29–31 %). Båda finns. Inga andra
  intervall hittades i någon av de 412 inlämningarna.
- **2019Q1:** pressmeddelandet (2019-01-17) säger 30,8 och presentationen (2019-01-18) 30,6, vilket bekräftar
  inkonsekvensen i källan. Ordningen på vintages är rätt.
- **2026Q4:** 52,3–54,3 mdr US$, växelkurs 31,8, 6-K 2026-10-15. Stämmer.

### 3.5 Datering, alla rader (automatiskt)

- **Capex-CSV:** för alla 72 rader med accessionsnummer är `filed` = EDGAR:s filingDate och `accepted` =
  acceptanceDateTime, URL:ens mapp = accessionsnumret och `known_from` ≥ acceptance-dagen i New York-tid
  (`test_no_capex_row_dated_before_its_edgar_acceptance`). För 30 rader (Alphabets och Amazons 10-Q/10-K samt aktieägarbrevet) är
  acceptance efter 17.30 ET, så dokumentet var offentligt kvällen före `known_from`, vilket är konservativt. De 29
  Microsoft-raderna (transkript, ingen accession) är daterade till samtalsdagen, och för alla 29 finns en 8-K
  (Item 2.02) samma dag. Samtalet hålls efter den. 0 avvikelser.
- **TSMC:** alla 163 tolkade dokumentposter har filingDate och acceptance som i EDGAR, och alla 603 observationer
  har en post med samma kvartal och värde som lämnats in exakt på `known_from`, aldrig tidigare. Den lagrade tabellen
  är identisk med `tsmc_guidance.vintages` körd på nytt. 0 avvikelser.

## 4. Rättningar som krävs

1. **R2-F1:** lägg till raden för Alphabet: company `googl`, horizon `CY`, period 2025, `approx` 85000/85000 MUSD,
   definition `GOOGL_CAPEX`, filed 2025-07-23, accepted 2025-07-23T20:01:33.000Z, doc_type `8-K EX-99.1`,
   källa `https://www.sec.gov/Archives/edgar/data/1652044/000165204425000056/googexhibit991q22025.htm`, accession
   0001652044-25-000056, locator "press release, CEO quote; sentence #16", SHA-256 enligt avsnitt 2. Hämta om
   `guid_capex_googl_cy_lo/hi` och ta bort de två `xfail`-markeringarna i `tests/test_r2_guidance.py`.
2. **R2-F2:** rätta Alphabet-stycket och antalet rader i `docs/kallor/guidance.md`. Höjningen i juli 2025 finns i
   EDGAR. Täckningstabellen: Alphabet 2025Q3 = CY approx (85 mdr).
3. **Kandidaturvalet:** komplettera E1:s urval med "varje capex-mening med ett dollarbelopp" (inte bara
   framåtblickande ord), så att presensformuleringar inte faller bort i framtida uppdateringar. R2:s genomgång gav
   inga fler träffar för Meta, Alphabet och Amazon. Microsofts 8-K genomsöktes inte, eftersom bolaget guidar i
   samtalet och inte används i B2.

Inga rättningar krävs för Meta eller TSMC.

## 5. Begränsningar (ärligt)

- Samtalstranskript för Alphabet och Amazon gick inte att läsa (proxyn nekar), och inte heller EDGAR:s
  fulltextsökning. Guidance som bara gavs i samtal (till exempel en eventuell ändring för Alphabet 2026 i samtalet
  2026-07-22) syns inte. Det följer regeln att `known_from` är det första dokument vi har, och det ger inget läckage,
  bara en mer inaktuell B2.
- Riktningsrader utanför stickprovet är inte omlästa. De används inte i B2.
- Testsviten har ett fel som fanns före R2 och inte gäller guidance:
  `tests/test_state.py::test_every_registered_core_series_exists_and_has_the_registered_method` (KeyError i
  `state/measures.py`). Det misslyckas också utan R2:s ändringar på den här grenen.
