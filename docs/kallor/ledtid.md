# Källor: Ledtid i stacken (LT1)

Följd fråga: "Rör sig order och orderstock hos leverantörerna (kraft, kylning, elnät, nät, servrar, datacenterleasing)
före eller efter capex-takten hos hyperskalarna och de yttre lagren, och ändras ledtiden?" Storheterna, läsregeln och
gränserna står i `docs/mattregister.md`, posten "2026-11-26 – LT1", som committades ensam (6fb0ccd) innan något mått
räknades. Mallen för läsregeln är F0 (posten "2026-11-26 – F0"). Rapporten står i `docs/resultat/ledtid.md`.

    python -m ai_tracker.followed ledtid --as-of YYYY-MM-DD [--json PATH] [--out PATH]
    python -m ai_tracker.observations lt1_rpo_power lt1_rpo_net lt1_dlr_bookings4   # de härledda serierna

Ingen ny källa, ingen ny hämtning från SEC och ingen ny extraktion. Allt bygger på serier som redan finns i katalogen.

## Underlaget

**Köpare.** Capex över fyra kvartal med KL1:s formel (`series.kreditlagret.formula("capex4", ...)`), ur `capex_*`
(SEC XBRL, `docs/kallor/sec.md`, `neoclouds.md`):

| Storhet | Serie | Medlemmar | Förändring i takt från |
|---|---|---|---|
| K-inre | `kl_capex4_inner` | Microsoft, Alphabet, Amazon, Meta | 2019Q4 |
| K-yttre | `kl_capex4_outer` | Oracle, CoreWeave, Nebius, IREN | saknas ännu (serien börjar 2025Q2) |

**Leverantörer.** Läsregelns X i "före" och Y i "efter":

| Rad | Serie | Innehåll | Källa | Förändring i takt från |
|---|---|---|---|---|
| L1 | `lt1_rpo_power` (ny) | `rpo_etn` + `rpo_pwr`: Eatons orderstock av fasta order (taggad som RPO) och Quantas RPO | S2, `sec_stack_kraft.md` | 2022Q1 |
| L2 | `lt1_rpo_net` (ny) | `rpo_csco` + `rpo_dell` + `rpo_smci` | S1, `sec_stack_nat.md` | 2020Q1 |
| L3 | `rpo_eqix` | Equinix RPO | S2 | 2019Q3 |
| O1 | `ob_etn_orders_electrical_americas_ttm_yoy_pct_organic_pct` | Eatons organiska ordertillväxt, Electrical Americas, tolv månader mot året före (%) | S3, `order_orderstock.md` | 2022Q2 |
| O2 | `lt1_dlr_bookings4` (ny) | `ob_dlr_leases_signed_total_dlr_share_q_level_musd` över fyra kvartal (hyra per år för nya avtal, Digital Realtys andel) | S3 | 2024Q1 |

**Sammanhang** (tabeller, ingår inte i läsregeln): medlemmarna var för sig, GE Vernovas RPO (`rpo_gev`, från 2024Q1),
Aristas RPO (`rpo_anet`, från 2022Q4), HPE:s RPO (`rpo_hpe`, från 2024Q2, förutbetalda intäkter), GE Vernovas order och
orderstock i USD, Dells AI-order och AI-orderstock och Digital Realtys nya avtal per kvartal (S3), leverantörernas
intäkter (`rev_*`), capex över fyra kvartal per köpare och köparnas capex-guidance för kalenderåret (KL1:s block).

## Kodning

- **Aggregaten** (`src/ai_tracker/series/ledtid.py`) är summor av medlemmarnas komponenter med `followed.aggregate`
  (`Formula`, `derive`). En version finns först när alla medlemmar har lämnat in för perioden, och `known_from` är den
  senaste komponenten (som A5 och KL1). Medlemmarna är valda efter definition och seriens start, inte efter värden.
- **Definitioner.** Medlemmarnas RPO har inga deklarerade definitionsbrott (S1 och S2 kör `sec_segment.definition_breaks`
  på balanserna). Eatons orderstock byter taggning 2024Q2 (utan dimension till en enda tidshink), men meningen i 10-Q
  är densamma, så det är samma definition (S2). HPE:s RPO är förutbetalda intäkter och ingår därför inte i L2. S3:s
  serier byter definition genom nya nycklar (organisk mot rapporterad, kvartal mot tolv månader) och skarvas aldrig.
  O1 är en definition utan stopp 2021Q4–2026Q3. Eatons orderstock utan angiven bas (en ny nyckel från 2025Q2) används
  inte.
- **O1 är en procentserie, inte en nivå.** Takten är 100 × ln(1 + v/100), alltså log × 100 över ett år av
  tolvmånadersorder, som takten för `kl_capex4`. Förändring i takt = takten nu minus takten två kvartal tidigare. Nivån
  är v. Överraskning mot B1 är inte registrerad för en tillväxttakt och visas som saknad (`followed.ledtid.yoy_measure`).
  Att läsa serien med `state.measures` hade gett takten som skillnaden mellan två tillväxttal (procentenheter), och
  det är fel storhet.
- **Rapporten härleder själv.** `followed.ledtid.table_on` skär tabellen vid läsdagen och räknar fram `lt1_*` och
  `kl_capex4_*` ur komponenterna med katalogens egna formler. Rapporten beror alltså inte på när de lagrade härledda
  raderna senast hämtades. På den delade datan 2026-11-26 är de framräknade raderna lika med de lagrade (25, 33 och 17
  rader för `lt1_*`, 66 och 6 för `kl_capex4_inner` och `_outer`), och ett test visar det på syntetiska data.
- **Läsregeln** är F0:s `common.read_measures` med X = förändring i takt, Y = förändring i takt, *g* = *h* = 5 för
  köparna och 10 för leverantörerna, *k* = 2 och 4, tecken +. Varje ursprung i historiken räknas med
  `common.origin_outcome`, samma funktion som regeln använder, så att ledtiden per ursprung kan visas.
- **Ledtiden** är kvartalet som avgjorde ett "talar för" minus ursprunget, i läsningarna med *k* = 4.

### Tolkningar (regeln ändras inte)

1. **Förvärvsmärket i "efter".** Posten säger att ursprung i kvartalen *a*, *a* + 1, *a* + 4 och *a* + 5 märks. Avsikten
   är att märka där leverantörens förändring i takt läses. I "före" är leverantören X, så märket sätts på ursprunget. I
   "efter" är leverantören Y, så märket sätts på kvartalet som avgjorde utfallet. Utslaget påverkas inte. En granskning
   bör pröva tolkningen.
2. **Ursprung i följd.** Ursprung med impuls åt samma håll i flera kvartal i rad avgörs ofta av samma kvartal för Y.
   Ledtiderna räknar då ned (4, 3, 2, 1). Posten räknar varje ursprung för sig, och rapporten säger att en sådan följd
   är en händelse.
3. **Nästa osedda läsning.** En rad får ett nytt *t* när Y får nästa kvartal, alltså när alla medlemmar i Y har lämnat
   in. Dagen uppskattas med `common.next_filings` (nästa kvartals slut plus medianen av avståndet för de åtta senaste
   inlämningarna) per medlem, och den senaste medlemmen avgör.

## Quantas förvärv (QA1)

Spår QA1 efter anmärkningen R28-7, registret 2026-11-27 QA1 (committat ensamt innan inlämningarna lästes). Quantas
förvärv är data i LT1:s befintliga förvärvsmärke, på samma sätt som Eatons. Ingen regel och inget utslag ändras.

    python -m ai_tracker.acquisitions_check          # hämtar dokumenten på nytt och kontrollerar varje rad

**Underlaget.** Quantas 16 inlämningar 10-K och 10-Q med rapportdag 2022-12-31 till 2026-09-30 (CIK 1050915). Agenten
läste förvärvsnoten, MD&A och del II punkt 2 (aktier som getts ut vid förvärv, med slutdagar) i varje dokument och förde
in 53 rader i `curated/acquisitions.csv` (`ai_tracker.sources.acquisitions`): förvärv som anges direkt (slutdag, namn
eller händelse efter balansdagen), antal förvärvade bolag för en period, köpeskilling som den står, Quantas meningar om
förvärvens del i RPO, och kvartal utan förvärv. Varje rad har accession, inlämningsdag, plats (meningens nummer i
dokumentets text) och meningens SHA-256. Den ordagranna meningen sparas bara i `data/raw/acquisitions_sentences/`.
Självkontrollen hämtade alla 16 dokument på nytt från EDGAR 2026-11-27: alla 53 rader har meningen på platsen, sina
siffror och datum i meningen och rätt inlämningsdag. Det kontrollerar plats och siffror, inte tolkningen (vilket kvartal
ett bolag hör till), som är för en oberoende granskning.

**Kvartalet *a*.** Quanta anger de flesta förvärv som ett antal bolag för en period ("during the nine months ended").
Ett bolag som finns i en periods antal men inte i föregående dokuments antal hör till kvartalet mellan dem. Köpeskillingen
anges för hela perioden hittills i året och delas inte upp (registret QA1, punkt 3). Bara Cupertino Electric och Dynamic
Systems anges med egen köpeskilling.

| *a* | Förvärv | Slutdag (där angiven) | Köpeskilling, MUSD (senast kända) | Första dokument |
|---|---|---|---|---|
| 2023Q1 | 3 bolag | 2023-01-05, -10 och -12 | 587,0 (3 mån 2023) | 10-K 2022, 0001050915-23-000010 (2023-02-23) |
| 2023Q2 | inget | – | – | 10-Q 0001050915-23-000150 |
| 2023Q3 | 1 bolag | 2023-08-30 | 622,5 (9 mån 2023) | 10-Q 0001050915-23-000164 (2023-11-02) |
| 2023Q4 | 1 bolag (krafttransformatorer) | oktober 2023 | cirka 300 | 10-Q 0001050915-23-000164 (2023-11-02) |
| 2024Q1 | 3 bolag | 2024-01-19, 02-06 och 03-01 | 449,2 (3 mån 2024) | 10-K 2023, 0001050915-24-000009 (2024-02-22) |
| 2024Q2 | 2 bolag | april 2024; 2024-04-18 och 05-31 | 540,2 (6 mån 2024) | 10-Q 0001050915-24-000082 (2024-05-02) |
| 2024Q3 | Cupertino Electric | 2024-07-17 | 2 035,2 | 10-Q 0001050915-24-000140 (2024-08-01) |
| 2024Q3 | 2 bolag till | bland dem 2024-09-20 | 641,8 (9 mån 2024, utom Cupertino) | 10-Q 0001050915-24-000159 (2024-10-31) |
| 2024Q4 | inget | – | – | 10-K 2024, 0001050915-25-000005 |
| 2025Q1 | 2 bolag | 2025-01-10 och 02-14 | 589,3 (3 mån 2025) | 10-K 2024, 0001050915-25-000005 (2025-02-20) |
| 2025Q2 | 2 bolag | ej angiven | 815,7 (6 mån 2025) | 10-Q 0001050915-25-000103 (2025-07-31) |
| 2025Q3 | Dynamic Systems | 2025-07-25 | 1 673,3 | 10-Q 0001050915-25-000103 (2025-07-31) |
| 2025Q4 | 3 bolag | 2025-11-14 och 12-09 | 2 471,1 (helår 2025, utom Dynamic Systems) | 10-K 2025, 0001050915-26-000006 (2026-02-19) |
| 2026Q1 | inget | – | – | 10-Q 0001050915-26-000016 |
| 2026Q2 | 3 bolag | två 2026-06-18 | 1 430,1 (6 mån 2026) | 10-Q 0001050915-26-000025 (2026-07-30) |
| 2026Q3 | 2 bolag | 2026-07-10, och aktier vid slut 08-31 och 09-11 | 1 799,7 (9 mån 2026) | 10-Q 0001050915-26-000025 (2026-07-30) |
| 2026Q4 | 1 bolag (stålstolpar) | efter 2026-09-30 (aktier vid ett slut 2026-10-14) | ej angiven | 10-Q 0001050915-26-000041 (2026-10-29) |

Tolkningar och luckor:
- **Etiketten per inlämningsdag (X26, efter R29-4).** Etiketten i CSV:n säger vad som var inlämnat om händelsen på radens
  dag, inte vad som blev känt senare: 2024Q1 är "2 förvärv" i 10-K för 2023 (två slut i januari) och "3 förvärv" från
  10-Q 2024-05-02, 2024Q2 "1 förvärv" 2024-05-02 och "2 förvärv" från 2024-08-01. Där dokumenten på dagen inte avgör
  om en följande händelse och en slutdag gäller samma förvärv står "minst 1 förvärv" (2026Q3 per 2026-07-30, 2026Q4 per
  2026-10-29). Rader för samma händelse och dag har samma etikett, och `acquisitions.load` kontrollerar det.
- **Första angivna köpeskilling (X26, efter R29-4).** Två rader till (55 i stället för 53): Cupertino cirka 1 500 MUSD i
  10-Q 2024-08-01 (utan förvärvad kassa, före justeringar och utan tilläggsköpeskilling) och Dynamic Systems cirka 1 350
  MUSD vid tillträdet i 10-Q 2025-07-31 (före justeringar och tilläggsköpeskilling). Senare dokument ersätter dem i
  märket. Båda kontrollerades mot ett nytt anrop till EDGAR 2026-11-27 (mening, hash, belopp och inlämningsdag), liksom
  de sex rader vars etikett ändrades.
- **2026Q3.** Del II punkt 2 nämner tre förvärv med aktier (07-10, 08-31 och 09-11), men antalet bolag för nio månader
  ökar med två (från 3 till 5). Ett av de tre kan vara ett förvärv som inte räknas som ett eget bolag. Raden har två
  bolag, som antalet säger.
- **2026Q1.** 10-Q för 2026Q1 anger inget förvärv i kvartalet (förvärvsnoten gäller bara 2025), och kassaflödet för
  förvärv var 22,9 MUSD. Raden "inget" bygger på att förvärv saknas i dokumentet, och på att halvårets antal (3) är detsamma
  som antalet nya bolag i 2026Q2-dokumentet.
- **Köpeskillingen** är verkligt värde av hela köpeskillingen (kontant, aktier och tilläggsköpeskilling) som bolaget
  anger den. Senare dokument kan justera den (Cupertino: cirka 1 500 → 1 967,7 → cirka 2 040 → 2 035,2; Dynamic Systems: cirka 1 350 → 1 668,6 → 1 673,3). Märket använder den senast
  kända på läsdagen.
- **Andelar i intresseföretag** (40 % i en stolptillverkare 2025, 49 % i ett samriskbolag 2026) är inte rörelseförvärv
  och kodas inte.
- **Före 2023** kodas inget (registret QA1, punkt 1). Blattner (2021-10-13) har *a* + 4 och *a* + 5 i 2022Q4 och 2023Q1,
  inom L1:s historik, och de kvartalen saknar därför ett märke nedåt.

**Hur ofta märket slår till.** Quanta köper bolag nästan varje kvartal. Av L1:s 19 kvartal med förändring i takt
(2022Q1–2026Q3) har 15 minst ett förvärvsmärke, alla utom 2022Q1–2022Q4. I 2023Q1–2023Q4 pekar alla märken uppåt, i
resten finns märken åt båda hållen. För L1 skiljer märket därför inte ut enstaka kvartal. Det säger att Quantas RPO
växer delvis genom förvärv hela tiden, och att storleken per kvartal inte är känd.

**Hur mycket av Quantas RPO-ökning 2026Q1–Q3 som kan vara förvärvad** (beskrivning, med förbehåll; registret QA1,
punkt 6). Quantas RPO var 23 760 MUSD vid 2025Q4 och 26 240, 33 550 och 41 750 vid 2026Q1–Q3, en ökning med 17 990 MUSD
på tre kvartal:
- 2026Q1 (+2 480): inget förvärv i kvartalet. Ökningen kan bara innehålla förvärv genom att de tre bolag som köptes
  2025Q4 växte efter köpet, och det är inte förvärvad RPO.
- 2026Q2 (+7 310) och 2026Q3 (+8 200): kvartal med förvärv (3 och 2 bolag, köpeskilling 1 799,7 MUSD för hela
  2026Q1–Q3). Quanta anger inte hur mycket RPO de tillförde, och köpeskilling räknas inte om till RPO.
- Quanta beskriver själv förvärvens del med ord: ökningen i RPO och backlog från årsskiftet till 2026-06-30 berodde
  delvis på förvärv i halvåret (10-Q 0001050915-26-000025), och ökningen till 2026-09-30 i första hand på nya uppdrag
  och större volym hos befintliga kunder och i mindre utsträckning på förvärv (10-Q 0001050915-26-000041). Båda är
  rader i CSV:n (`rpo_statement`), med plats och hash.
- Som i X25: LT1:s huvudläsning (ursprung 2026Q2, X +16,5) hamnar under gränsen 10 först om förvärven uppåt vid 2026Q2,
  Quantas tre förvärv 2026Q2 (*a*) och Eatons Boyd Thermal (*a* + 1), tillsammans lade till mer än omkring 3,6 mdr USD
  till L1, och mer om märkena nedåt (Fibrebond och Quantas förvärv 2025Q1 och 2025Q2) räknas med. Läsningen "L1 efter
  K-inre" (Y +16,9 vid 2026Q3) kräver på samma sätt mer än omkring 4,5 mdr från Quantas förvärv 2026Q2 och 2026Q3.
  EL1:s huvudläsning läser takten (+45,3 vid 2026Q2), och den hamnar under gränsen 10 först om förvärven 2025Q3–2026Q2
  (Dynamic Systems, tre bolag 2025Q4, Boyd Thermal och tre bolag 2026Q2) tillsammans fanns kvar i orderstocken med mer
  än omkring 17,1 mdr, cirka 30 % av L1 vid 2026Q2.
- Det går alltså inte att säga hur stor del av ökningen som är förvärvad. Det Quanta skriver talar för att den är en
  mindre del, men det är bolagets bedömning och inget belopp.

## Förvärv i L2 och L3 (DA1)

Spår DA1, körning 18, registret 2026-11-27 DA1 (committat ensamt innan inlämningarna lästes). Dells, Super Micros och
Equinix förvärv är data i LT1:s förvärvsmärke för L2 och L3, med QA1:s mekanism och märkesregel. Ingen regel och inget
utslag ändras.

**Vilka bolag.** Bara bolag vars RPO ingår i L2 eller L3 (`series.ledtid.NET`, L3 i `followed.ledtid`): Dell, Super Micro
och Equinix. HPE och Arista ingår inte i L2 (`rpo_hpe` och `rpo_anet` är sammanhang i rapporten och läses inte) och är
inte kodade. HPE:s förvärv av Juniper Networks (2025) ligger alltså i `rpo_hpe` utan märke, men den serien läses inte.
Cisco ingår i L2, men bara Cisco–Splunk är belagt (LT1 (c)). Ciscos övriga förvärv är inte kodade.

**Underlaget.** Alla 10-K och 10-Q med rapportdag från 2022-12-31: 15 för Dell (CIK 1571996, räkenskapsår 2023–2027),
16 för Super Micro (CIK 1375365) och 17 för Equinix (CIK 1101239, med 10-K/A för 2022). Agenten läste förvärvsnoten,
goodwilltabellen, kassaflödets investeringsdel och MD&A i varje dokument och förde in 47 rader i
`curated/acquisitions.csv`: 8 för förvärv eller köpeskilling och 39 för kvartal utan förvärv. Ett kvartal utan förvärv
bygger på att kassaflödet saknar en rad för förvärv (eller visar "—") i dokumentet för perioden till och med kvartalet,
och att noterna inte nämner något förvärv. Raden pekar på kassaflödets mening. Självkontrollen hämtade alla dokument på
nytt från EDGAR 2026-11-27: alla 102 rader i tabellen (Quantas 55 och de nya 47) har meningen på platsen, sina siffror och
datum i meningen och rätt inlämningsdag. Råkopiorna och meningarna ligger i spårets `data/raw` (gitignorerad), inte i
huvudutcheckningens. Spårets `.env.local` pekade den delade råcachen mot huvudutcheckningens `data/raw` (X26:s
anteckning), och den pekades om till spårets egen innan något hämtades.

**Kvartalet *a*** (DA1, punkt 3). Super Micro och Equinix har kalenderkvartal, som Quanta. Dells serie har
räkenskapskvartalets kalenderkvartal (räkenskapsåret slutar omkring 31 januari), så ett förvärv i räkenskapskvartalet
augusti–oktober har *a* = kvartal 3. `acquisitions.quarter_of` flyttar dagen en månad bakåt för Dell. En slutdag inom
några dagar från en räkenskapsgräns får kontrolleras mot inlämningen (ingen av Dells rader har en slutdag).

| Bolag | *a* | Förvärv | Slutdag | Köpeskilling, MUSD | Första dokument |
|---|---|---|---|---|---|
| Dell | 2023Q3 | Moogsoft | i räkenskapskvartalet till 2023-11-03 | ej angiven (goodwill 82, senare 77) | 10-Q 0001571996-23-000046 (2023-12-08) |
| Dell | 2025Q4 | ej namngivet | i räkenskapskvartalet till 2026-01-30 | ej angiven (goodwill 61, kassaflöde 84) | 10-K 0001571996-26-000008 (2026-03-16) |
| Super Micro | 2023Q2 | Gemini Open Cloud Computing | 2023-04-17 | 2,5 (varav 0,3 innehållet ett år) | 10-K 0001375365-23-000036 (2023-08-28) |
| Equinix | 2025Q2 | TIM NextGen DC, tre datacenter i Filippinerna | 2025-06-02 | 183 | 10-Q 0001101239-25-000029 (2025-07-30) |
| Equinix | 2025Q4 | ej namngivet | – | ej angiven (kassaflöde cirka 69) | 10-K 0001101239-26-000032 (2026-02-11) |

Alla andra kvartal 2023Q1–2026Q3 (Dell till och med 2026Q2) har en rad "inget". Tolkningar och luckor:
- **Dell 2025Q4.** 10-K för räkenskapsåret 2026 har "goodwill acquired" 61 MUSD i ISG och 84 MUSD i kassaflödet för förvärv
  av verksamheter och tillgångar. 10-Q för nio månader har inget av dem, så förvärvet ligger i räkenskapskvartal 4
  (2025Q4 i `rpo_dell`). Dell namnger det inte och anger ingen köpeskilling. Etiketten säger "ej namngivet förvärv".
- **Dell, Moogsoft.** Dell anger att goodwillen kommer från förvärvet av Moogsoft i räkenskapskvartalet till 2023-11-03,
  men ingen slutdag och ingen köpeskilling. Kassaflödet för förvärv av verksamheter och tillgångar var 127 MUSD för nio
  månader och 126 för året, så inget nytt kom 2023Q4.
- **Equinix 2025Q4.** Kassaflödet för förvärv av verksamheter var 182 MUSD för nio månader 2025 (TIM) och 251 för året,
  och MD&A skriver att ökningen omfattar TIM ("including the TIM Acquisition"). Noten nämner bara TIM. Skillnaden, cirka
  69 MUSD, kan vara ett annat förvärv eller en senare betalning för TIM. Raden märker det som ett ej namngivet förvärv,
  eftersom märket inte ändrar något utfall och ett förvärv inte kan uteslutas.
- **Inte förvärv** (DA1, punkt 3): Dells försäljning av Secureworks 2025-02-03 (en avyttring, märks inte, fast den
  sänker en nivå), Super Micros köp av fastighet i San Jose 2024 (80 MUSD) och dess andel på 11 % i Ampera 2025,
  Leadteks andel på 30 % som närstående bolag köpte 2023, Equinix samriskbolag (xScale, och atNorth som ett samriskbolag
  köpte 2026-09-02), dess fastighetsköp ("real estate acquisitions") och immateriella tillgångar ur "other asset
  acquisitions" 2023 (8,5 MUSD), där inget bolag eller datacenter anges.
- **Super Micro 2024Q2.** 0,3 MUSD för förvärv i räkenskapsåret 2024 är lika med det innehållna beloppet för Gemini, som
  förföll ett år efter slutdagen. Noten nämner inget annat förvärv.
- **Före 2023** kodas inget. Dell köpte för 70 MUSD verksamheter och tillgångar i räkenskapsåret 2023 (goodwill 48), och
  Equinix köpte Entel Chile och MainOne 2022Q2 och Entel Peru 2022Q3. De har *a* + 4 och *a* + 5 i L2:s och L3:s historik
  (2023Q2–2023Q4 för Equinix) och saknar märke där.

**Hur mycket av RPO-rörelsen vid huvudursprungen som kan vara förvärvad** (beskrivning, med förbehåll; registret DA1,
punkt 5). Ingen av bolagen anger tillförd RPO. Köpeskilling räknas inte om till RPO. Beräkningen drar ett belopp *A*
från nivån från kvartal *a* och framåt och räknar om takten (log × 100 över fyra kvartal) och förändringen i takt (mot
två kvartal tidigare), som i X25 och QA1.
- **L2 före K-inre, huvudursprunget 2026Q2** (X +25,9, talar för, *k* = 2 och *k* = 4): inget förvärvsmärke. Dells förvärv
  2025Q4 har *a* + 4 först 2026Q4. Bara Ciscos okodade förvärv och förvärv före 2023 kan ligga i fönstret.
- **L2 vid 2025Q4 och 2026Q1** (förändring i takt +35,7 och +24,4, Dells ej namngivna förvärv *a* och *a* + 1, uppåt).
  2025Q4 avgör läsningen "L2 efter K-inre", *k* = 4 (talar för), och båda är ursprung med ledtid i "L2 före K-inre".
  Förändringen i takt hamnar under gränsen 10 först om förvärvet lade till mer än omkring 28,7 mdr USD (2025Q4) eller
  19,1 mdr (2026Q1) till L2, alltså 35 % och 20 % av Dells RPO vid de kvartalen. Dells goodwill från förvärvet var 61
  MUSD och kassaflödet 84 MUSD. Dells RPO-ökning från 51 till 82 mdr vid 2025Q4 kan därför knappast vara förvärvad, men
  tillförd RPO är inte belagd.
- **L2, Moogsoft och Gemini** (*a* = 2023Q3 och 2023Q2) träffar kvartal utan impuls (förändring i takt mellan −4,6 och
  +6,8 vid 2023Q2–2024Q4). Super Micros RPO var 304 MUSD vid 2023Q2, under 0,5 % av L2.
- **L3** har ingen impuls i de märkta kvartalen. Vid TIM:s *a* och *a* + 1 (2025Q2 och 2025Q3) var förändringen i takt
  +7,4 och +1,2. En impuls nedåt utan TIM skulle kräva mer än omkring 1,4–2,0 mdr USD tillförd RPO. Vid *a* + 4 och
  *a* + 5 (2026Q2 och 2026Q3, −0,6 och −0,4) skulle en impuls uppåt utan TIM kräva mer än omkring 1,1 mdr, cirka 9 % av
  Equinix RPO vid 2025Q2 och sex gånger köpeskillingen. Det ej namngivna förvärvet 2025Q4 (+5,3 och +9,4 vid 2025Q4 och
  2026Q1) skulle kräva mer än omkring 1,9 mdr för en impuls nedåt.
- Märket säger alltså att ett nivåskifte kan finnas i fönstret, inte att det är stort. För L2 och L3 skulle förvärven
  behöva ha tillfört RPO som är många gånger köpeskillingen eller kassaflödet för att ändra ett utslag. Det är en
  beskrivning, ingen regel.

## Datering och kalender

- `known_from` är inlämningsdagen för 10-Q och 10-K (RPO, capex) och för resultat-8-K:et (S3). Aggregatens
  `known_from` är den senaste komponenten. Tabellen skärs vid läsdagen innan något räknas, så en rad som blir känd
  efter dagen påverkar inte rapporten (test).
- Eaton, Quanta, Equinix, Super Micro och köparna utom Oracle har balansdag och kvartal på kalenderkvartalets slut.
  Ciscos och Dells balanser har räkenskapskvartalets kalenderkvartal (S1), alltså upp till en månad efter
  kalenderkvartalets slut. Oracles capex har kvartal som slutar en månad före (KL1).
- Dell lämnar sin 10-Q 63–90 dagar efter kvartalet. L2 har därför ofta ett kvartal mindre än de andra raderna, och
  rapporten säger vilken medlem som saknas.

## Licens och publicering

Alla underliggande serier är SEC-data (sec.gov/privacy: offentlig information som får spridas) och har klassen `ja`
för kommersiell användning (`ai_tracker.licenses`, regeln `sec`, de härledda via sina komponenter). De tre nya
serierna har `publish=False`, som KL1:s. O1 och O2 kommer ur S3:s extraktion, som har `publish=False` i väntan på den
oberoende granskningen av extraktionen. Rapporten säger det vid varje rad där de används.

## Förbehåll

- **Kort historik.** 10–27 ursprung per rad, och färre med impuls. Detta är en beskrivning och inget test. Inget
  p-värde räknas, och ingen korrektion för flera prövningar görs (24 utslag). Ett mönster kan vara slump.
- **Före och efter är inte varandras motsats.** Två utjämnade serier som rör sig ihop ger ofta "talar för" i båda
  riktningarna. Då säger regeln inte vilken som kom först.
- **RPO och orderstock är inte orderingång.** Förändringen är order minus leveranser, plus valuta och förvärv (S2).
  Ciscos och Dells RPO har stora tjänstedelar (support och prenumerationer, S1).
- **Leverantörerna säljer till fler än AI-köparna.** Quanta och Eaton till elbolag och industri, Cisco och Dell till
  företag. Datacenterandelen går inte att skilja ut i XBRL (S2).
- **Förvärv.** Belagda: Cisco–Splunk (2024-03), Eaton–Fibrebond (2025-04-01), Eaton–Boyd Thermal (2026-03-12) och
  Quantas förvärv från 2023 (avsnittet "Quantas förvärv" ovan, QA1) och Dells, Super Micros och Equinix förvärv från
  2023 (avsnittet "Förvärv i L2 och L3" ovan, DA1). Förvärv före 2023 (till exempel Quantas Blattner 2021-10-13) är inte
  kodade, Ciscos förvärv utom Splunk är inte kontrollerade, och HPE:s och Aristas förvärv är inte kodade (de ingår inte
  i L2). Avyttringar märks inte. O1 är organisk och påverkas inte.
- **Digital Realtys andel** är obelagd 2021Q4–2024Q1 (S3, tolkning 9). Nya avtal är klumpiga: förändringen i takt för
  summan över fyra kvartal kan bli nära ±100 log × 100 när ett stort kvartal går in i eller ut ur fönstret.
- **BLOCKED och utanför ramen.** Vertiv: inget RPO i XBRL, och S3:s orderserier slutar 2025Q4. GE Vernova: RPO från
  2024Q1 och order från 2024Q1 (för korta för läsregeln, sammanhang). Schneider Electric, Siemens Energy och ABB finns
  inte på EDGAR. Privata datacenterbyggare och kraftbolagens egna investeringar ingår inte.
