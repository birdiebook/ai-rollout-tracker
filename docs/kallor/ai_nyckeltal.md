# Källa: bolagens AI-nyckeltal (steg 2, spår B4)

Byggt och kontrollerat 2026-11-23, rättat efter granskningen R5 2026-11-24 (spår X3, se "Rättning efter R5"). Bara
extraktion: inga takter, inga jämförelser mellan guidance och utfall.
Avsnittet "Kodningsregler" skrevs och committades (00b98a8) **innan** någon kandidatmening kodades. Tolkningar som
behövdes under kodningen står separat i "Tolkningar under kodningen" och är inte inskrivna i efterhand i reglerna.

Kod: `src/ai_tracker/sources/nvda_guidance.py` (Nvidia, deterministisk tolkning), `src/ai_tracker/series/nvda_guidance.py`,
`src/ai_tracker/sources/ai_kpis_corpus.py` (dokument och kandidatmeningar), `src/ai_tracker/sources/ai_kpis.py` (läsare
och definitionskoder), `src/ai_tracker/series/ai_kpis.py` (katalogposter), `src/ai_tracker/ai_kpis_check.py`
(stickprov). Data: `curated/ai_kpis.csv` (committad, bara siffror och referenser). Tester:
`tests/test_nvda_guidance.py`, `tests/test_ai_kpis.py` (syntetiska fixturer, inget nät). Hämtning:
`python -m ai_tracker.observations <nycklar>`, kandidater: `python -m ai_tracker.sources.ai_kpis_corpus`, stickprov:
`python -m ai_tracker.ai_kpis_check --frac 0.2 --seed 20261123`.

## Nvidias guidance för nästa kvartal (N3, B2)

**Källa:** varje 8-K med Item 2.02 (pressmeddelandet EX-99.1, CFO-kommentaren EX-99.2 upprepar), läst ur filens
fullständiga inlämningstext (`<accession>.txt`), som finns för alla år (äldre inlämningar saknar `index.json`). Alla
174 8-K från 2009 gås igenom, även Item 7.01/8.01 för uppdateringar mitt i kvartalet.

**Tolkning (deterministisk):** rubriken "outlook for the <ordinal> quarter of fiscal <år>" (eller 2009 "expects
revenue in the third quarter ending <datum>") följd inom 700 tecken av intäktsmeningen i en av tre former:

| Period | Form | Lagrat |
|---|---|---|
| 2009Q3–2011Q4 | förändring mot föregående kvartal: "up a to b percent", "down seasonally a to b percent", "flat", "relatively flat, plus or minus two percent", "up slightly, approximately 2 percent" | `nvda_guid_rev_qoq_lo/hi` (%) |
| 2012Q1–2012Q4 | "between $X million and $Y billion" | `nvda_guid_rev_lo/hi`, mitt = (lo+hi)/2 |
| 2013Q1– | "$X billion, plus or minus N%" (N = 2, och 3 för 14-veckorskvartalet 2026Q4) | `nvda_guid_rev_mid`, lo/hi = mitt × (1 ∓ N/100) |

- **Period** = kalenderkvartalet för det guidade räkenskapskvartalets mittpunkt, samma regel som `rev_nvda` och
  `rev_nvda_datacenter` (`sec.calendar_quarter`): räkenskapskvartal k i FY N = kalenderkvartal k år N−1.
  Räkenskapskvartalens datum räknas exakt (räkenskapsåret slutar sista söndagen i januari, Q1–Q3 är 13 veckor).
- **Kontroll:** inlämningsdagen måste ligga inne i det guidade räkenskapskvartalet, annars `ParseError` och inget
  lagras. Ett uttalande efter kvartalets slut (preliminärt utfall: 2019-01-28, 2022-08-08) räknas inte som guidance.
- **known_from** = 8-K:ns `filingDate` (Nvidia lämnar in cirka 16.20 ET, före 17.30). En upprepning i ett senare
  dokument ger ingen ny rad, ett ändrat värde blir en ny vintage.
- **Resultat:** 70 kvartal utan luckor, 2009Q3–2026Q4 (10 i procentform, 60 i dollar). Inga uppdateringar mitt i
  kvartalet med ny siffra. 2021-04-12 (8-K Item 7.01) sa att intäkten för Q1 FY22 låg över guidance på 5,30 mdr.
  Det är kvalitativt och inte kodat (samma regel som för TSMC).
- **8-K med Item 2.02 utan guidance:** 2009-02-10 och 2009-05-07 (ingen guidance i pressmeddelandet före 2009-08),
  2014-05-06 (resultatet släpptes två dagar före samtalet, och guidance kom i 8-K:n 2014-05-08), 2019-01-28 och
  2022-08-08 (preliminära utfall). 2019-11-14 finns guidance bara i CFO-kommentaren (EX-99.2), samma dag.
- **Flagga för N3:s B2:** registret säger "Nvidias guidance för total intäkt (mittpunkt)". Mittpunkten finns från
  2012Q1, och `rev_nvda_datacenter` börjar 2017Q2, så hela N3-perioden täcks. För 2009–2011 finns bara procentform,
  och en mittpunkt i dollar kräver då föregående kvartals intäkt. Det bör registreras om B3 ska använda åren före
  2012 (C2 kräver n ≥ 4 avvikelser, vilket 2012–2017 redan ger).
- **Licens:** SEC EDGAR, offentlig information. Serierna har `publish=True` som TSMC:s guidance, eftersom tolkningen
  är deterministisk och kontrollerad i stickprovet.

## Kodningsregler (låsta 2026-11-23, före kodningen)

### Gemensamt för alla nyckeltal

- **En rad per uttalat värde** i `curated/ai_kpis.csv`: siffra, enhet, typ (`point` = exakt, `approx` = "about",
  "approximately", "nearly"; `min` = "over", "more than", "surpassed", "exceeds"; `range`), definitionskod,
  period, `filed`, URL, accession, plats (`sentence #k` i `guidance_capex.sentences(tsmc_sec.to_text(doc))`),
  SHA-256 av meningen och en kort not. Meningen sparas bara i `data/raw/ai_kpis_sentences/<id>.txt`.
- **Definitionskod = serie.** Varje ändring av definitionen blir en ny kod och därmed en ny serie, även om bolaget
  kallar det samma sak: "monthly" mot "weekly" användare, "monthly active users" mot "users", tokens per månad mot
  tokens per kvartal, run-rate för "AI business" mot "AI revenue", Azure med och utan "other cloud services",
  tillväxt i rapporterad valuta mot konstant valuta. Serier med olika koder slås aldrig ihop.
- **Period.** Flöden som bolaget redovisar för ett kvartal (Azures tillväxt, tokens "this quarter") får
  kalenderkvartalet för räkenskapskvartalets mittpunkt (samma regel som `sec.calendar_quarter`; Microsofts FY Q1 =
  juli–sept = kalender-Q3). Ögonblicksvärden ("now", "currently", "as of", "surpassed") får **månaden** för det
  datum de avser: ett angivet datum eller en angiven månad om texten har det, annars kvartalets sista månad om
  texten säger "at the end of the quarter", annars dokumentets månad. Run-rate är ett ögonblicksvärde.
- **known_from** = dokumentets `filed` (EDGAR) eller, för Microsofts samtal, samma dag som 8-K:n med resultatet.
  Ett värde som upprepas i ett senare dokument ger ingen ny rad i serien (första dokumentet räknas). Ett värde som
  först nämns i ett senare dokument än det som det avser dateras till det senare dokumentet.
- **Bara bolagets egna siffror** om bolagets egna produkter. Siffror om kunder, partner, marknaden eller enskilda
  kundavtal (t.ex. OpenAI:s åtaganden) kodas inte. Procentuella andelar ("X % of the Fortune 500 use ...") kodas
  bara om de är ett återkommande nyckeltal.
- **Inga beräkningar.** Ett värde kodas så som det står. "Doubled" eller "up 5x" utan nivå kodas inte (det är en
  takt, inte en nivå). Tillväxttal kodas bara för Azure (där bolaget redovisar talet varje kvartal) och för molnet
  (Google Cloud, AWS), eftersom de är de uttryckliga nyckeltalen för L3.

### Kapacitetsuttalanden (−2..+2)

Avgränsning: uttalanden om **bolagets egen kapacitet för AI eller moln** (datacenter, GPU/accelerator, Azure, AWS,
Google Cloud; för Nvidia utbudet av datacenterprodukter) i förhållande till efterfrågan. Komponentbrist för annat
(spelkonsoler, PC, Surface, gaming-GPU, logistik) kodas inte. Allmänna ord om investeringar ("we are investing to
add capacity") utan ett påstående om balansen kodas inte.

| Kod | Regel | Exempel på ordalydelse |
|---|---|---|
| **+2** | Efterfrågan överstiger kapaciteten med en uttrycklig förstärkning, eller brist som uttryckligen begränsar intäkten kraftigt | "significantly capacity constrained", "demand significantly exceeds supply", "sold out", "well short of demand" |
| **+1** | Kapacitets- eller utbudsbegränsad, eller efterfrågan överstiger utbudet, utan förstärkning; också "we remain constrained", "constraints impacted revenue" | "capacity constrained", "demand continues to exceed supply", "supply constraints" |
| **0** | Uttryckligen i balans | "supply and demand in balance", "roughly in line with demand" |
| **−1** | Begränsningen är uttryckligen borta eller lättar så att den inte längre styr; "sufficient capacity" | "no longer capacity constrained", "constraints have eased", "we have enough capacity" |
| **−2** | Överkapacitet eller kapacitet som inte används | "excess capacity", "underutilized", "demand below supply" |

- **Tid.** `capacity_time = current` för läget nu eller under det redovisade kvartalet, `forward` för förväntningar
  ("we expect to remain capacity constrained through the fiscal year" = +1 forward, period = perioden som anges
  eller, om ingen anges, dokumentets kvartal). Läget nu och förväntningen är olika serier.
- **En kod per dokument, bolag och tid.** Har dokumentet flera meningar kodas den mening som är mest uttrycklig
  (högst absolutbelopp). Om meningar i samma dokument har olika tecken blir koden 0 och noten säger varför. Den kodade
  meningen sparas, de övriga meningarna räknas i noten.
- **Bristande omnämnande kodas inte.** Att ett dokument inte nämner kapacitet är ingen nolla, utan en lucka.
- **Riktning är inte beräknad**: koden anger vad bolaget säger, inte vår bedömning av läget.
- Period för `current`: kalenderkvartalet för det redovisade räkenskapskvartalet (för 8-K med resultat, 10-Q,
  10-K och samtal). För ett dokument utan redovisat kvartal (8-K Item 7.01/8.01): kvartalet för `filed`.

### Urval av kandidater (låst före kodningen)

Brett, efter lärdomen R2-F1: en mening är kandidat om den har en siffra och ett nyckelord för AI, moln eller
användning (`KPI_RE` i `sources/ai_kpis_corpus.py`), eller om den nämner kapacitet, utbud eller begränsning
tillsammans med ord om efterfrågan, AI, moln eller datacenter (`CAPACITY_RE`), med eller utan siffra. Agenten läser
alla kandidater i de dokument som berörs. Antalet kandidater och kodade rader redovisas nedan.

## Tolkningar under kodningen (inte en del av de låsta reglerna)

Följande fall täcktes inte uttryckligen av reglerna ovan. Valet står här så att granskningen (R5) kan pröva det.

1. **Bara bolagets egna uttalanden.** Analytikers frågor i samtalen kodas inte, även om de nämner kapacitetsbrist.
2. **Hypotetiska formuleringar** i riskavsnitt ("may", "could", "if we") kodas inte. De påstår inget om läget.
3. **Uttalanden om en produkt** ("no capacity constraint on the copilots", MSFT 2024-04-25) räknas inte som motsatt
   tecken mot uttalanden om Azures infrastruktur i samma samtal. Koden blir +1.
4. **Framåtblickande koder**: en rad per angiven horisont, så ett dokument kan ge flera perioder (MSFT 2025-01-29:
   +1 för 2025Q1 och 0 för 2025Q2, "roughly in line" i slutet av FY25). Utan angiven horisont: kvartalet då dokumentet
   lämnades in. "Several quarters in fiscal 2026" kodas till och med FY26 Q2 (minst två kvartal). "Beyond the next
   several quarters" (Nvidia 2026-02-25) är också en angiven horisont: minst två kvartal efter det pågående, alltså
   Q2–Q3 FY27 = 2026Q3 (R5-F3).
5. **"Fully subscribed"** (Trainium2) läses som "sold out", alltså +2. "Largely sold out" och "nearly all ...
   committed" är förbehållna och får +1.
6. **Effektivitet är inte balans.** "Monetize underutilized capacity" i CPU-flottan (MSFT 2026-10-28) handlar om
   effektivitet. Det ändrar inte koden +1 från samma samtal.
7. **Nvidia FY23** (2023-02-22): lagernedskrivningar för "excess supply" av Ampere för Gaming **och Data Center** mot
   efterfrågan kodas −2, eftersom datacenter nämns uttryckligen. Utbudsbrist för Gaming (2025–2026) kodas inte.
   Partnernas kapacitetsbrist (Nvidias 10-Q 2026-08-26 om AI-molnpartner) kodas inte, eftersom den inte är bolagets egen.
   **Tillämpad som den står** (ägarens beslut 2026-11-23, R5-F2): H20-nedskrivningen på 4,5 mdr USD för "excess
   inventory … as the demand for H20 diminished" (Q1 FY26) kodas −2 för 2025Q1, och H200-nedskrivningen i 10-Q:n
   2026-08-26 ger olika tecken mot "supply constraints" i samma dokument, alltså 0 för 2026Q2. "Cloud GPUs are sold out"
   (2025-11-19) gäller molnens uthyrda kapacitet, alltså partner, och kodas inte (2025Q3 är en lucka, R5-F1).
8. **Ordalydelse och definition.** Alphabets tokens per minut beskrivs på tre sätt ("first party models ... via direct
   API", "first party model APIs", "Gemini models ... API tokens"). De behandlas som samma mått (API-trafik till egna
   modeller). Microsofts Copilot-familj (2025-07: "family of Copilot apps", 2025-10: "first party family of
   Copilots") behandlas också som samma mått. GitHub Copilot har däremot fyra koder: användare, betalande användare,
   betalande prenumeranter och organisationer (Copilot for Business mot alla planer).
9. **Inaktiva serier.** Ett nyckeltal som inte har nämnts på 270 dagar före det senaste dokumentet i extraktionen
   (ungefär tre kvartalsrapporter) markeras som avslutat (`closed`), med datumet i noten. Det öppnas igen när en senare
   extraktion hittar det.
10. **Balans och guidance** (R5-F4, F5, enligt granskarens läsning, ägarens beslut 2026-11-23): att utbud och
    efterfrågan var matchade ("matched supply and demand") under det redovisade kvartalet (MSFT 2025-04-30) är
    uttryckligen i balans, 0. Azure-guidance för nästa kvartal "with some impact from the AI capacity availability" (MSFT 2024-04-25) är en
    väntad begränsning, +1 framåt, på samma sätt som `msft-capf-2024q4b`.

## Kodat (179 rader, 56 serier)

383 dokument (2023-01-01–2026-11-17): 288 8-K-dokument med Item 2.02/7.01/8.01, 79 10-Q/10-K och 16 samtal på
microsoft.com (FY23 Q2–FY27 Q1). Kandidaturvalet gav 9 372 meningar (6 447 unika): 2 678/560 för Microsoft
(nyckeltal/kapacitet), 1 384/919 för Nvidia, 1 571/260 för Meta, 963/269 för Amazon och 592/176 för Alphabet. Agenten
gick igenom kandidaterna med riktade sökningar per nyckeltal (tokens, användare och kunder, run-rate, Azure, backlog,
kapacitet) och läste träffarna i 8-K och samtal, och för 10-Q/10-K bara meningar utan hypotetiska ord. Meningar som
bara upprepar ett redan kodat värde kodas som upprepning eller hoppas över.

| Led | Rader | Innehåll |
|---|---|---|
| L2 användning | 71 | tokens (Alphabet API per minut, Microsoft per kvartal, månad och räkenskapsår, Foundry-kunder över en biljon tokens), användare (Gemini-appen, AI Overviews, Meta AI, Copilot-familjen, AI-funktioner, GitHub Copilot, M365 Copilot-platser, Rufus, Alexa for Shopping), kunder och organisationer (Azure OpenAI, Azure AI, Foundry, Agent Service, Copilot Studio, Power Platform, Bedrock, Sales Copilot, Copilot for Security, Foundry med flera modeller, Foundry och Fabric), utvecklare |
| L3 intäkter | 73 | Microsofts AI-verksamhet i årstakt (och en väntad), LinkedIn AI, AWS AI-verksamhet, Amazons chip i årstakt (två definitioner), Google Clouds backlog, Azures tillväxt i % och i konstant valuta (tre definitioner), AI-tjänsternas bidrag till Azure i procentenheter (två definitioner) |
| Kapacitet | 35 | Microsoft (11 nu, 9 framåt), Nvidia (5 + 5), Amazon (3 + 1), Alphabet (1). Meta: inga kodbara uttalanden i 8-K |

**Azure (deterministiskt):** Microsofts pressmeddelanden har en tabell "Constant Currency Reconciliation" med raden
"Azure and other cloud services (revenue) X% Y% Z%" (rapporterad, valutaeffekt, konstant valuta). Raden läses med ett
reguljärt uttryck i varje 8-K med Item 2.02 (16 kvartal, FY23 Q2–FY27 Q1) och stämmer med meningen i pressmeddelandets
highlights för alla 16. Definitionerna byttes två gånger: FY25 (EMS och Power BI flyttades ut, omräknad FY24 i 8-K:n
2024-08-21) och FY27 ("Azure revenue", omräknad FY26 i 8-K:n 2026-09-02). De omräknade kvartalen är vintages i den nya
definitionens serie, daterade till omräkningens 8-K. Serierna `kpi_msft_azure_growth_v1/v2` och `_cc_v1/v2` är
avslutade.

**Inte kodat, och varför:**
- Molnets årstakt (AWS 85–184 mdr, Google Cloud över 50 och 70 mdr) och Google Clouds tillväxt i %: kan räknas ur
  intäktsserierna (`rev_aws`, `rev_google_cloud`). Azure har ingen intäktsserie före FY27, så där kodas tillväxten.
- "Cloud and YouTube" i årstakt (en summa av två delar), Fabric, Sentinel, GitHub och Connect i årstakt (inte
  AI-specifika), Bing och LinkedIn användare, GitHubs totala antal utvecklare.
- Multiplar och tillväxt utan nivå ("doubled", "up 4X", "17x token volume", "40% growth in paid MAU").
- Microsofts Azure-guidance för nästa kvartal i konstant valuta (ges i varje samtal). Den är framåtblickande och
  inte efterfrågad här, men den är kodbar på samma sätt och vore en kandidat till B2 för N4.
- LinkedIn: medlemmar som använder AI-jobbsök dagligen (mer än 10 miljoner) och kunder med "agentic hiring" (25 000),
  samtalet 2026-10-28 (#56). LinkedIns användare kodas inte (se ovan), och kunderna är ett engångstal för en
  rekryteringsfunktion utan återkommande definition. MAI Code Flash (3 miljoner användare i GitHub Copilot förra
  månaden, #74): användning av en enskild modell inne i en annan produkt, inte ett nyckeltal för produkten.
  Båda är bedömningsfall som R5 bad att bara lista (R5-F6).
- Alphabets tokens per månad (480 biljoner, 980 biljoner, 1,3 kvadriljoner) och Gemini-appens MAU före 2025-10,
  Metas MAU för Meta AI utom 2025-04 och Amazons samtal: de finns bara i samtalen på bolagens egna sidor, som proxyn
  nekar (se nedan).

## Serier

Nyckel = `kpi_` + definitionskoden i gemener. Alla har `publish=True` efter granskningen R5 och rättningen X3
(bara siffror med källhänvisning publiceras, aldrig text). Gren: G3
(L2), G4 (L3), G7 (kapacitet). Luckor är väntade och listas i `series/ai_kpis.KNOWN_GAPS`, som läggs till i
`warehouse.KNOWN_GAPS`. Enheter: miljoner användare (även platser), antal, MUSD, %, procentenheter, biljoner tokens
och miljarder tokens per minut. Frekvens M = månaden värdet avser, Q = kalenderkvartalet för det redovisade
räkenskapskvartalet, A = Microsofts räkenskapsår, lagrat som kalenderåret då det slutar.

Öppna serier: `kpi_googl_api_tokens_per_min` (6 värden 2025-10–2026-10), `kpi_googl_gemini_app_mau` (3),
`kpi_googl_cloud_backlog` (2), `kpi_msft_ai_business_runrate` (2), `kpi_msft_ghcp_users` (4),
`kpi_msft_m365_copilot_paid_seats` (3), `kpi_msft_foundry_customers` (2), `kpi_msft_azure_growth_v3` och `_cc_v3`
(5, omräknade FY26 + FY27 Q1), `kpi_amzn_aws_ai_runrate` (2), `kpi_amzn_chips_runrate` (2), kapacitetsserierna för
Microsoft, Nvidia, Amazon och Alphabet, och några med ett värde. Avslutade: 24, bland dem Azure v1/v2 och AI-bidraget.

## Värdar som nekas av proxyn

`abc.xyz` (Alphabets samtal), `ir.aboutamazon.com` (Amazons samtal), `investor.atmeta.com` (Metas samtal),
`investor.nvidia.com` (Nvidias samtal), `blog.google` (Googles siffror från I/O) och `efts.sec.gov` (EDGAR:s
fulltextsökning). Ett försök vardera, ingen kringgång. Med dessa värdar skulle Alphabets tokens per månad, Metas och
Googles användare per kvartal och Amazons och Nvidias kapacitetsuttalanden i samtalen kunna läggas till. Ingen nyckel
behövs, bara att värdarna tillåts.

## Stickprov

`python -m ai_tracker.ai_kpis_check --frac 0.2 --seed 20261123` hämtade om dokumenten (utan cache) för 34 av 169
nyckeltal och 28 av 139 Nvidia-poster. **0 fel** (0 %), och ingen mening hade flyttat. Alla 169 nyckeltal
kontrollerades också mot de sparade dokumenten, med 0 fel. Kontrollen bekräftar att meningen finns på angiven plats
(hash) och att talet, eller ett ord för kapacitetskoden, står i den. För Nvidia tolkas filen om och värdena jämförs.
Den bekräftar **inte** semantiken (period, definition, om ett uttalande gäller bolagets egen kapacitet). Agenten läste
om de 34 raderna i stickprovet och hittade inga fel, men det är ingen oberoende granskning. R5 bör läsa om
stickprovet och alla 33 kapacitetsrader (meningarna finns i `data/raw/ai_kpis_sentences/<id>.txt`, och kodningen som
skrev CSV:n finns i `data/raw/ai_kpis_sentences/spec.py` och `build_kpis.py`).

## Rättning efter R5 (spår X3, 2026-11-24)

Alla fel i `docs/granskning/r5_extraktion.md` som gäller B4 är rättade enligt ägarens beslut 2026-11-23. Varje ny
rad har URL (och accession för SEC), plats, SHA-256 av meningen (meningen bara i `data/raw/ai_kpis_sentences/`) och
`filed` = EDGAR:s filingDate eller, för samtalen, dagen för 8-K:n med resultatet.

| Fel | Rättning |
|---|---|
| R5-F1 | `nvda-cap-2025q3` borttagen (partnernas kapacitet). 2025Q3 är en lucka |
| R5-F2a | `nvda-cap-2025q1` = −2 (H20, 8-K EX-99.1 0001045810-25-000115, mening #2, filed 2025-05-28) |
| R5-F2b | `nvda-cap-2026q2` = 0 (olika tecken, #280 och #323 i samma 10-Q) |
| R5-F3 | `nvda-capf-2026q1` period 2026Q3 |
| R5-F4 | `msft-cap-2025q1` = 0 (samtalet 2025-04-30, #364) |
| R5-F5 | `msft-capf-2024q2` = +1 (samtalet 2024-04-25, #221) |
| R5-F6 | Kodat med fem nya definitionskoder: `MSFT_SALES_COPILOT_ORGS` (2), `MSFT_COPILOT_SECURITY_PAID_CUSTOMERS` (1), `MSFT_FOUNDRY_CUST_ANTHROPIC_OPENAI` (1), `MSFT_FOUNDRY_CUST_MULTI_MODEL` (1) och `MSFT_FOUNDRY_FABRIC_CUSTOMERS` (3). Alla är `min` ("more than"/"over"), period = samtalets månad. "Både Anthropic och OpenAI" och "mer än en modell" är olika mått och har därför olika koder. LinkedIn och MAI Code Flash står under "Inte kodat" |

Valet för R5-F6: alla åtta har en entydig och återkommande eller avgränsad definition i bolagets ordalydelse, så de
kodas hellre än listas. Tre av serierna har bara ett värde och blir avslutade enligt tolkning 9.
`ai_kpis_check` kände inte igen orden för tre kapacitetskoder ("matched supply and demand", "capacity availability"
och 0 vid olika tecken). Ordlistan är utökad, och alla 179 rader stämmer nu mot de sparade dokumenten. De nya och
ändrade raderna kontrollerades också mot nyhämtade dokument (0 fel).

## Licens

SEC-dokument är offentliga (sec.gov/privacy). Från pressmeddelanden och transkript publiceras bara siffror med
källhänvisning. CSV:n innehåller siffror, plats, URL, accession och SHA-256 av meningen, och noterna är omskrivna
utan citat. Meningarna finns bara i `data/raw` (gitignorerad). Microsofts sidor används på samma villkor som i E1.
