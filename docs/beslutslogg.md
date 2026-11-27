# Beslutslogg

## 2026-11-23 – Projektet startas

**Val:** eget publikt repo med fullt fokus på AI-utrullningen. Kopplingen till placeringar tas upp senare
och ligger då utanför repot. Spårningen är neutral, med takt och förändring i takt per gren (G1–G9) och
inga larmnivåer. Förregistreringen låser mått och beräkningssätt. Kodlicens MIT.
Plan: [plan.md](plan.md).

## 2026-11-23 – Fas 0: ramverket kopieras från kpif-nowcast

Katalog, versionerad observationstabell, publiceringskalender, DuckDB-datatester och utvärdering
(DM, Holm) kopierades och generaliserades. **Varför kopiera och inte paketera:** ett gemensamt bibliotek
ger beroenden mellan repona innan det är klart vad som faktiskt är gemensamt. **Viktigaste ändringen:**
blandade frekvenser och källdaterade rader. SEC:s companyfacts har en post per inlämnat dokument med
datum, vilket ger riktiga versioner från första hämtningen, till skillnad från SCB-backfillen i kpif-nowcast.
Detaljer: [plan.md](plan.md), avsnitt 7.

## 2026-11-23 – Fas 2, spår I4: Indeed, EIA och vast.ai

**Indeed (G8):** git-historiken i `hiring-lab/ai-tracker` används som vintagearkiv. `known_from` är
commit-tiden på standardgrenen (`--first-parent`) där värdet först fanns, och ändringar blir revideringar.
Bara rå dagdata lagras. Härledda mått kommer senare. **EIA (G7):** kommersiell elförsäljning i VA, TX,
GA, AZ, OR, OH och USA ur EPM:s arkivnummer (tabell 5.4.A) och EIA-861M. `known_from` är Last-Modified
+ 2 dagar, efter belägg att filer läggs upp dagen före release. 2010-01 till 2012-10 är backfill med
läckageflagga. **vast.ai (G6): BLOCKED.** Villkoren (version 2026-09-01) förbjuder automatiserad
insamling och prisindex utan skriftligt avtal, så ingen insamlare och inget dagligt arbetsflöde byggdes.
Detaljer: [kallor/indeed_vast_eia.md](kallor/indeed_vast_eia.md).

## 2026-11-23 – SEC-serier: kalendermappning, Amazons capex och omräkningar

**Kalenderkvartal = kvartalet som innehåller räkenskapskvartalets mittpunkt.** För MSFT, GOOGL, AMZN och
META är det samma som slutdatumets kvartal, eftersom alla deras kvartal slutar på kalenderkvartalets
sista dag. För Nvidia blir aug–okt Q3, så Nvidia ligger ungefär en månad efter. **Varför inte
slutdatum:** då blir aug–okt "Q4", och värdet blir känt före periodens slut, vilket bryter
läckagekontrollen.
**Amazons capex = brutto (`PaymentsToAcquireProductiveAssets`), från 2017Q3.** De äldre taggarna är
netto efter incitament, och en av dem bytte definition 2018. **Varför:** att skarva brutto mot netto
ger ett definitionsbrott, och bruttot matchar de andra tre bolagens rader. Därför börjar `capex_hyp4`
2017Q3. En nettoserie med historik från 2008 går att bygga om måttregistret väljer netto.
**Omräkningar som inte bryts ned per kvartal läggs inte i ett enda kvartal.** Kvartalet behåller då
sin tidigare version. Det är konservativt, och några helår summerar därför inte till det senaste
helårsvärdet. Detaljer: [kallor/sec.md](kallor/sec.md).

## 2026-11-23 – G2: pris vid fast förmåga byggs själva (fas 2, spår I6)

**Val:** `g2_price_at_capability` byggs av LiteLLM:s git-historik (MIT, commit-datum på `main` som
`known_from`) och Epochs ECI (CC BY), med bara förstapartspriser och en explicit mappningstabell. Tröskeln
141,16 (o1) låstes i måttregistret vid första bygget. **Varför förstapart:** återförsäljares priser för
öppna modeller beror på hosting och inte på modellen, och urvalet av återförsäljare i LiteLLM ändras över
tid. **Variant:** `g2_price_at_capability_gpqa` med Epochs egna GPQA-körningar har ärliga tidsstämplar för
förmågan, men är en brusig benchmark nära taket. Båda redovisas, och huvudmåttet är fortfarande ECI-varianten.
Detaljer: [kallor/pris_formaga.md](kallor/pris_formaga.md).

## 2026-11-23 – N2: källa och prognosdag

TSMC:s månadsintäkt hämtas från bolagets 6-K till SEC (2006–), med inlämningsdatum som `known_from`. MOPS och TSMC:s
IR-sida blockerar automatiska anrop. Prognosdagen flyttades till dag 5, eftersom 21 % av rapporterna kom dag 8 eller
tidigare. Koreas och Taiwans exportdata är blockerade (geoblockering, Cloudflare). BOK ECOS fungerar men kräver en
gratisnyckel.

## 2026-11-23 – Spår I3: Census, BEA, ALFRED, Eurostat och SCB

**Val:** regimbrott blir egna serier som aldrig skarvas. BTOS får tre serier: v1 "producing goods or services",
v2 "business functions" och v3 "Super Intelligence or SI (formerly … AI)" från cykel 202622. Det sista är ett
brott enligt frågeformuläret som fältades från 2026-10-19. SCB delas också i två serier, TAB6405 och TAB6814, i stället för att fogas
ihop, eftersom 2026 byter till NACE 2.1 och omfattar fler branscher. **Ny frekvens `2W`** (ISO-fjortondag) så att
`no_gaps` hittar saknade BTOS-cykler. **ALFRED** används för G.17 och M3 eftersom det ger riktiga vintages utan
nyckel och primärkällan inte nås: federalreserve.gov nekas, och api.census.gov kräver nyckel. ALFRED används också
som belägg för publiceringsdagar. **Beslutspunkt feb 2027:** BTOS byter exempel igen från cykel 202702, och
rekommendationen är en ny serie v4. Detaljer: [kallor/census_eu.md](kallor/census_eu.md).

## 2026-11-23 – N2: förregistrerad backtest, V1 befordras inte (fas 3, spår F3-N2)

B0, B1 och V1 (B1 + ridge på importens årstillväxt) kördes enligt registret, 2012-05 – 2026-10 (n=174). V1 ≈ B1
(MAE 10,52 mot 10,51, Holm-p 0,96, sämre även från 2023). **B1 är huvudmodell för N2.** Tolkningar av oklarheter
(utvärderingsstart 2012-05, ridge-detaljer) och förbehåll finns i [resultat/n2.md](resultat/n2.md). Nästa steg som
kan ge mer är TSMC:s kvartalsguidance som B2, och den registreras före analys.

## 2026-11-23 – N1: backtest enligt registret, B1 blir huvudmodell (fas 3, spår F3-N1)

**Utfall:** V1 (OLS-bridge) och V2 (ridge) på `us_imports_tw_m` och `us_constr_datacenter` hade högre MAE än B1
(drift) både 2021Q4–2026Q3 (7,50 och 7,88 mot 6,91, n = 19) och från 2023 (9,59 och 9,43 mot 7,86, n = 14).
Holm-p 0,96 och 0,74. Den poolade utvärderingen per bolag (N1b, n = 130) pekar åt samma håll. **Beslut enligt
regeln:** ingen befordran, `CHAMPION = "B1"`, och V1 och V2 skrivs ut som skuggor i varje skarp prognos.
**Tolkningar som orkestreraren bör bekräfta** (registret är inte ändrat): "B1 + bridge" som regression av B1:s
miss, delkvartal som medel-log av kända månadspositioner, 12 kompletta träningsrader, 2025Q4 utesluten (ingen
känd byggmånad) och Holm-kravet i båda perioderna. Detaljer: [resultat/n1.md](resultat/n1.md).

## 2026-11-23 – Drift i GitHub Actions (spår O1)

Veckohämtning (`fetch-weekly.yml`) och skarpa nowcasts (`nowcast.yml`) körs i Actions via
`src/ai_tracker/pipeline.py`. **Val:** prognosdagen är alltid dagens UTC-datum. En missad dag tas inte igen av
schemat, och en helgdag flyttas inte. Två schematider samma UTC-dag (18:47 och 21:19). Om en serie som prognosen
behöver inte gick att hämta skrivs ingen prognos (hellre ett nytt försök samma dag än en låst prognos på gammal
data). Bara den nya prognosfilen och `forecasts/SCORECARD.md` committas, av `github-actions[bot]`. Scorecarden
jämför mot första vintage. N2:s skrivare vägrar nu också en prognosdag i framtiden, som N1:s redan gjorde. Data
ligger bara i Actions-cachen och laddas inte upp som artefakt (publikt repo, licenser). Detaljer:
[drift.md](drift.md).

## 2026-11-23 – Spår I7: Fed G.17 från primärkällan i stället för ALFRED

**Val:** `us_ip_semis_m` (G3344, NAICS 3344) och den nya `us_ip_computers_m` (G3341, NAICS 3341) hämtas från
federalreserve.gov. Skälet är att FRED:s villkor begränsar användning i samband med maskininlärning, medan Board-data
är public domain (disclaimer.htm). **Riktiga vintages** byggs ur Fed:s releasearkiv, med 135 releaser från
2016-04-15 inklusive årsrevisioner, och known_from är releasedatumet. Datumen stämmer exakt med ALFRED:s vintages.
Den senaste releasen hämtas via DDP. Eftersom DDP:s paket läggs ned 2027-03-31 finns
`current/ipdisk/ip_sa.txt` som reserv. NAICS 334413 publiceras inte separat. Serierna får `publish=True`. M3 ligger
kvar via ALFRED som interimskälla med `publish=False` tills en Census API-nyckel finns. **Modellerna ändras inte:**
`us_ip_semis` är fortfarande utesluten i fas 3, och en ny registrerad variant krävs för att använda den.
Detaljer: [kallor/fed_g17.md](kallor/fed_g17.md).

## 2026-11-23 – Spår T1: aktualitetskontroll i veckojobbet

**Val:** varje öppen serie får en högsta ålder från den nyaste periodens slut: `lag_days` + en period + 30 dagar
(D/W/2W/M/Q), `lag_days` + 400 dagar för A. **Varför periodslut och inte senaste `known_from`:** en revidering av
gamla perioder ska inte dölja att nya perioder har slutat komma. Avslutade serier markeras `closed`, och två
förskjutna utgivningar får `max_age_days` med skäl (Indeed 83 dagar, Nvidia 199 dagar). Gränserna prövades bakåt
veckovis mot tabellens vintages. De enda övriga träffarna var shutdown-förseningarna hösten 2025, som är riktiga
avbrott. En för gammal serie fäller veckojobbet (exitkod 2) men cachen sparas ändå. Detaljer:
[drift.md](drift.md), avsnittet Aktualitet.

## 2026-11-23 – Spår F5: tillstånd per gren och månatlig ögonblicksbild

**Val:** måtten, diffusionsindexet och tillståndsregeln är implementerade exakt enligt registret
(`src/ai_tracker/state/`). Kärnserierna ligger i `CORE_SERIES`, och ett test kräver att listan är identisk med
registrets tabell. G1 och G9 läggs till som data. Där registret är oklart valdes den försiktigaste läsningen:
månader aggregeras ur `as_of(beräkningsdagen)` och den sista, ofullständiga månaden tas bort, en SD kräver minst
2 värden, tröskeln jämförs mot oavrundat index, fördubblings- och halveringstid räknas med omvänt tecken
(kortare tid = accelererar), och det finns ingen regel för inaktuella serier. Den skarpa ögonblicksbilden tas
**sista kalenderdagen i månaden** (`snapshot.yml`), skrivs en gång och committas av boten. Första filen blir
`snapshots/2026-11.json`. Backcasten 2019-01 till 2026-10 är en rekonstruktion och inget skarpt register.
Tre tolkningar bör registreras: månadsaggregeringen, tecknet för tidsmått och inaktuella serier. Detaljer:
[resultat/tillstand.md](resultat/tillstand.md).


## 2026-11-23 – Fas 2, spår I5: Epoch, METR och arXiv

**Val:** Benchmarkfronten lagras som en månadsserie, härledd as-of: bara körningar med `Started at` före månadens
slut räknas, och värdet får `known_from` = dagen efter månadsslut. Ändrade källvärden blir nya rader daterade
hämtdagen. ECI och modelldatabasen lagras som återfyllda serier (`source=backfill`) som de veckovisa
ögonblicksbilderna sedan bygger vidare på. arXiv räknas på **primär kategori**, eftersom API:ets `cat:` också
träffar korslistningar och saknar filter för primär kategori. Alla poster per månad hämtas därför och räknas,
och unionen inklusive korslistningar sparas som en egen serie. **Varför:** varje värde ska gå att spela upp
`as_of()` utan att en senare körning eller korslistning läcker in. Benchmarkurvalet följer regeln exakt. Problemet
med ersatta benchmarks är flaggat i måttregistret för beslut. Detaljer: [kallor/epoch_arxiv.md](kallor/epoch_arxiv.md).

## 2026-11-23 – Spår E1: bolagens guidance extraherad (fas 4), ingen jämförelse med utfall

**TSMC:** tolkas deterministiskt ur 6-K (pressmeddelande och presentation, från 2019 som exhibits). Det ger
2006Q2–2026Q4 utan luckor: intäktsintervall (NT$ t.o.m. 2017Q2, US$ därefter), växelkurs från 2008Q3 och
marginaler. Uppdateringar mitt i kvartalet blir vintages. **Hyperscalers:** agenten har läst och kodat 101 värden i
`curated/guidance_capex.csv` (bara siffror, referenser och hash). Kvantitativ guidance finns för Meta i alla 20
N1-kvartal, för Alphabet i 7 och för Amazon och Microsoft i 3. Transkripten för Alphabet och Amazon nekas av
proxyn. Definitionerna skiljer sig (Meta inklusive amortering på leasing, Amazon netto, Microsoft inklusive nya
finansiella leasingavtal). **Förslag** till B2 för N1 (B1 ersatt av guidance-implicerat kvartal för Meta och
Alphabet) och en flagga för N2:s B2 (NT$-intervall före 2017Q3) finns i [kallor/guidance.md](kallor/guidance.md).
Orkestreraren låser B2 i registret.

## 2026-11-23 – Spår X1: läckagerättningar efter granskningen R1, N1 och N2 omkörda

**Val:** alla åtta åtgärder i [R1](granskning/r1_lackage.md) är genomförda, och de 23 xfail-testerna är vanliga
tester. Viktigast: Census-kategorin datacenter är känd först från sin första publicering 2024-07-01 (2014-01–2024-04
låg tidigare före den), ALFRED:s 0,0-platshållare räknas inte som publicering (FT-900 oktober 2025 är känd
2026-01-08), och en hämtlogg (`data/fetch_log.parquet`) gör att en ny regeldaterad period aldrig dateras till före
en tidigare hämtning som saknade den. Dessutom: N2 poängsätter inte månader med känt utfall, FT-900 har 45 dagars
fördröjning före 2013 och nedstängningen 2013 i `LATE`, BTOS-cykler planerade under finansieringsluckan 2025 är
kända från 2025-11-13 och tidsplanen sparas vid varje hämtning, Indeed och LiteLLM har en dags marginal, och
`as_of`-konventionen (prognosdagen = dagens slut, `known_from == prognosdag` räknas) är dokumenterad.
**Omkörning utan ändringar i modeller eller regler:** N1 kan bara utvärderas från 2024Q2 (n = 9 i stället för 19).
B1 7,00, V1 9,81, V2 9,51, Holm p 0,45. N1b: B1 12,17, V1 14,39, V2 13,48 (n = 36). N2: V1 10,506 mot B1 10,510,
Holm p 0,981. **Ingen befordran, B1 är fortfarande huvudmodell för både N1 och N2.** De gamla siffrorna står kvar
som ogiltiga i [n1.md](resultat/n1.md) och [n2.md](resultat/n2.md). Kvarstående läckage: C30 och FT-900 är
backfill med dagens vintage, och datacenter är säsongsrensad med dagens faktorer. Det gynnar V1/V2 och gör det
negativa resultatet robust, men ett positivt resultat hade krävt realtidsvintages.

## 2026-11-23 – Spår F6: G1 och G9 i tillståndsmotorn

Urvalsregeln från registerändringen 2026-11-23 körs som kod (`epoch_hub.selection_table`). Den valde
`frontiermath_erdos` och `spireclimb`. Bara två familjer återstod, så den tredje platsen är tom. Resultatet står som en
daterad post i [måttregistret](mattregister.md). Benchmarkvärden är kända från `Started at` + 30 dagar, och månaden
blir känd första dagen i nästa månad + 30 dagar. Serierna byggdes om. `<valda>` löses upp per beräkningsdag ur den
registrerade listan och registrerade byten. En vald benchmark slutar räknas så snart den är känd som mättad eller utan
körning i 90 dagar, även innan bytet är registrerat. ECI och modelldatabasen är spärrade, och träningsberäkningen räknas
men flaggas. `frontiermath` och `frontiermath_tier_4` är avslutade katalogserier. Backcast 2024-01–2026-10: G1 har 1
räknad serie och därför inget tillstånd, och G9 har 3. Detaljer i [tillstand.md](resultat/tillstand.md) och
[kallor/epoch_arxiv.md](kallor/epoch_arxiv.md).

## 2026-11-23 – Spår B2: bolagens guidance utvärderad som B2 för N1 och N2

**Val:** B2 byggd exakt enligt registret (posterna om B2 2026-11-23), med `as_of(prognosdag)` för guidance och all
annan indata. Oklarheter lästes konservativt och dokumenterades (B1 flera steg fram = iterad säsongsnaiv tillväxt
för N2 och konstant drift för N1, valuta efter kvartal, ofullständig guidance ger B1, `capex_hyp4` = summan av
bolagens B2). Holm över alla varianter per mål. **N2:** guidance användes i alla 174 månader. B2 MAE 6,42 mot B1
10,51 (2023–: 6,70 mot 9,67), Holm-p < 0,001. B2 klarar regeln, men befordringen är **villkorad: väntar på
oberoende granskning av extraktionen (R2)**. `CHAMPION` är fortfarande B1. **N1:** guidance för Meta i 9 av 9
kvartal, för Alphabet i 6 av 9 och aldrig för Amazon eller Microsoft. B2 MAE 5,85 mot B1 7,00 (n = 9), Holm-p 0,68.
B2 klarar inte regeln, och B1 är huvudmodell. N1b: Meta blir bättre med guidance, Alphabet sämre (inaktuella
vintages när samtalen saknas). Detaljer: [n1.md](resultat/n1.md) och [n2.md](resultat/n2.md).


## 2026-11-23 – N2: B2 (TSMC:s guidance) blir huvudmodell

B2 uppfyllde den förregistrerade befordringsregeln med stor marginal (MAE 6,4 mot 10,5, Holm-p 2,5·10⁻⁸). Den
oberoende granskningen R2 godkände extraktionen. Huvudmodellen byttes därför mekaniskt enligt regeln. Johannes kan
backa beslutet före den första skarpa körningen 2026-12-05. För N1 gav B2 lägre MAE (5,3 mot 7,0, n=9) men klarade
inte Holm-testet, så B1 förblir huvudmodell där. Granskningen hittade en saknad Alphabet-rad, som nu är tillagd.

## 2026-11-23 – Spår C1: en rolling-origin-motor för N1 och N2

**Val:** N2 flyttas från `src/ai_tracker/nowcast_n2/` till `src/ai_tracker/nowcast/n2.py`. Det gemensamma kontraktet
ligger i `nowcast/engine.py`: första vintage, vintage-datum enligt `as_of`, spärren för utfall som är kända vid
prognosdagen, regelns delar (bästa baslinje, kontroll per period, `REVIEW_REQUIRED`-spärren och valet av champion)
och skrivaren som aldrig skriver om. Modellerna och de registrerade reglerna är oförändrade. N1 kräver fortfarande
Holm i båda perioderna och N2 bara i hela perioden, som tidigare. **Kompatibilitet:** `python -m ai_tracker.nowcast_n2`
och `python -m ai_tracker.nowcast_n2.backtest` finns kvar som tunna shims. Ny väg: `python -m ai_tracker.nowcast
n2|backtest n2`. Workflows anropar bara `pipeline`, och pipeline, tester och aktuella dokument använder nu den nya
modulen. **Kontroll:** före och efter flytten gav backtesterna för N1, N1b och N2 bitidentiska fel per origin (1 721
värden), identiska utvärderingar och identiska befordringsbeslut (N1 B1, N2 B2). Torrkörda skarpa prognoser (N2
2026-11-05, N1 2026-10-20, trunkerad tabell) gav identisk JSON utom tidsstämpel och git-sha. Det enda som ändrats i
JSON är att N2:s `created_utc` nu kommer före `git_sha`. Inaktuell motivering i koden rättad: `us_ip_semis` är
utesluten för att den inte ingår i de registrerade varianterna, inte i väntan på FRED-villkoren (G.17 kommer från
Fed sedan I7).

## 2026-11-23 – Fas 6, spår F6-site: publik hemsida på GitHub Pages

**Val:** statisk sida som byggs av `python -m ai_tracker.site build` i `pages.yml` efter varje lyckat datajobb.
Siffror och listor renderas i Python (läsbara utan JavaScript). Diagrammen ritas som inline-SVG av ett eget litet
skript, så sidan laddar ingenting från externa värdar (inget CDN behövdes). **Register:** de committade
ögonblicksbilderna. Före den första visas den rekonstruerade historiken med etiketten "rekonstruerad historik, inte
ett skarpt underlag". **Licenser:** licensregeln ligger på ett ställe (`site/data.py`, `publishable`): bara
`publish=True` visas med värden, och för övriga kärnserier visas bara grenens summering och vilka serier som hålls
inne. **Diagram per serie:** takt och förändring i takt de senaste tio åren ur samma beräkning som
ögonblicksbilden (`measures.measure_path`, en version `as_of` beräkningsdagen). Percentiler och SD bygger på hela
historiken. **Bygget fallerar** om datatesterna i `warehouse.py` fallerar, och då publiceras ingenting.
Ägaren aktiverar Pages en gång (`docs/drift.md`).



## 2026-11-23 – Steg 2 planeras: flödesmodell, sannolikheter och regim

Efter fas 0–6 zoomar projektet ut. I stället för nio separata grenar byggs en kedja från användning till el, där
leden stäms av mot varandra och varje led får nowcast, prognos 1–8 kvartal och regimsannolikhet. Planen är uppdelad
i vågor (0–4) med parallella spår och förregistreringsgrindar: [steg2/plan.md](steg2/plan.md). Sex beslut för
Johannes står i planens avsnitt 7.

## 2026-11-23 – Steg 2: beslut och förregistrering

Johannes godkände rekommendationerna i `docs/steg2/plan.md` avsnitt 7: BigQuery i gratisläget (sandbox, inget
betalkonto) för PyPI och GH Archive, Cloudflare Radar-nyckel, nya värdar, holdout-policyn, ingen betald
transkriptkälla och labbens rapporterade intäkter som en märkt serie. Allt ska vara gratis. Förregistreringen C0
(holdout, mål N3–N6, B3, faktormodell, intervall, regim) står i `docs/mattregister.md` under "Steg 2" och granskas av R6.

## 2026-11-23 – Delad data mellan spår (I1)

Spåren läser en gemensam bas (main-utcheckningens `data/`) och skriver bara i sin egen `data/`. Vyn är bas ∪ spår,
och spårets rad vinner vid samma nyckel. En ombyggd serie döljer basens rader via `rebuilt_series.json`. Data förs
in i basen bara med `python -m ai_tracker.datamerge`, som kör datatesterna och aktualiteten och vägrar skriva om
något fallerar. Valt framför en databasserver: inga nya beroenden, och filerna och datatesterna är desamma som
förut. Detaljer finns i [drift.md](drift.md) (Delad data).


## 2026-11-23 – Månadsbrev

Brevet genereras deterministiskt ur ögonblicksbilden (inga LLM-texter i driften), committas tillsammans med den och
visas på hemsidan. Grenarnas tillstånd och mått läses bara ur ögonblicksbilden. Prognoser, revideringar och guidance
läses ur de committade prognosfilerna och tabellen avgränsad till ögonblicksbildens informationsmängd. Ett fel i brevet
stoppar aldrig ögonblicksbilden.

## 2026-11-23 – Förstapartspriser: Anthropic pausad i väntan på beslut

Spår B5 byggde veckovisa ögonblicksbilder av förstapartspriser. Bara Anthropics prissida gick att nå, eftersom de
andra fem leverantörernas värdar är blockerade. Anthropics villkor förbjuder automatisk åtkomst till tjänsterna "except
... where we otherwise explicitly permit it". Det är oklart om `llms.txt` och `robots.txt` räknas som sådant tillstånd.
Insamlingen är därför pausad (`status="BLOCKED"`, serien stängd) tills Johannes har beslutat. Koden och korskontrollen
mot LiteLLM finns kvar och stämde exakt för alla 23 aktuella modeller.

**Uppdatering samma dag:** Johannes godkände spåret, och insamlingen av Anthropics prissida är påslagen igen (en
hämtning per vecka). Serien är fortfarande `publish=False`, eftersom sidan inte anger någon licens för vidarepublicering.

**Slutligt beslut samma dag:** efter genomgång av villkoren valde Johannes rekommendationen att **pausa**
insamlingen från Anthropics webbplatser (prissidan i B5 och nyhetssidorna i B6). G2 vilar på LiteLLM, som
korskontrollen bekräftade. Inga återkommande automatiska hämtningar görs från anthropic.com, claude.com eller
platform.claude.com. Redan hämtade meningar granskas mot sparade hashar.


## 2026-11-23 – Våg 1: el, neoclouds och labbens intäkter

- **PJM** (kapacitetsauktioner och lastprognoser) har `publish=False`, eftersom PJM:s villkor för icke-medlemmar
  förbjuder vidarepublicering. Lastprognoserna lagras som årsversioner: perioden är rapportåret, och värdet är
  prognosen för år +1, +5 och +10.
- **ERCOT:s kö för stora laster** är PARTIAL. Siffrorna finns bara som diagram i PDF-presentationer, och ingen serie
  byggs utan en granskad extraktion.
- **Neoclouds:** Oracle, CoreWeave, Nebius (6-K, efter dekonsolideringen av Toloka) och IREN. CoreWeaves capex är
  kassaflödesraden, inte bolagets egen periodiserade capex.
- **Labbens intäkter:** bara Anthropic har förstapartsuttalanden. Nyhetsrumssiffrorna och S-1:ns definierade
  "Run-Rate Revenue" är separata serier som aldrig blandas. Anthropic är börsnoterat från 2026-11-19, och reviderade
  intäkter läggs till via SEC när den första 10-Q:n kommer.


## 2026-11-23 – PyPI-historik som onsdagsurval

Exakt daglig PyPI-historik för tolv paket skulle kosta cirka 2,1 TB i BigQuery. Sandboxen ger 1 TB per månad. Historiken
är därför nedladdningarna en onsdag per vecka (176 GB). Exakta veckosummor hämtas framåt via pypistats, som läser samma
tabell och stämde exakt med BigQuery på överlappsdagen. npm har exakta veckosummor från 2015 men ingen verifierad licens
(`publish=False`).


## 2026-11-23 – B3 för N2 passerade regeln, men väntar på granskning

B3 (TSMC:s guidance korrigerad för systematisk avvikelse) gav MAE 5,81 mot B2 6,42 och Holm-p 0,038 i steg 2-familjen.
Spåret bytte huvudmodell mekaniskt, men CLAUDE.md kräver en oberoende granskning per positivt resultat som ska
användas. Bytet är därför återställt (`n2.CHAMPION = "B2"`), och B3 följer med som skugga. Granskningen R7 görs före den
första skarpa N2-prognosen 2026-12-05. N3–N6: inga varianter passerade, och B1 är huvudmodell.


## 2026-11-23 – R5:s tolkningsfrågor avgjorda

Johannes valde rekommendationerna:
- **F2:** B4:s tolkning 7 tillämpas som den står. H20-nedskrivningen kodas −2, och 2026Q2 blir 0.
- **F4–F6:** granskningens läsning gäller. Microsofts koder för 2025Q1 (0) och 2024Q2 (+1) läggs till, och de 8
  produkttalen kodas eller listas under "Inte kodat".

Rättningarna F1–F14 görs i ett eget spår efter att kvoten har återställts.


## 2026-11-24 – GitHub AI-medförfattare: stängd historik

GitHub tog bort commit-meddelanden ur Events API den 2025-10-07, så GH Archive saknar dem efter 2025-10-08. Måttet
(andel publika push-commits med AI-medförfattare) finns därför som stängd historik 2021–2025-W40, byggd ur timfilerna
med ett förregistrerat urval av sju timmar per vecka. BigQuery användes inte (15,7 GB per dag). En levande ersättare
via GitHubs commit-sökning är BLOCKED av hastighetsgränser. Förslag för senare: andel öppnade pull requests från
AI-agenters botkonton i GH Archive, efter att 2026 års täckning har mätts.


## 2026-11-24 – B3 blir huvudmodell för N2 (efter R7)

Granskningen R7 bekräftade B3 med förbehåll. Spåret X4 rättade R7-F1 (Nvidia i gruppmedlet för kvartalsintäkt enligt
registerposten samma dag: bara kvartal från 2017Q2, Nvidias värde på alla tre TSMC-positioner) och R7-F2 (fast
jämförelsemodell `CHAMPION_AT_STEP2`, B2 för N2 och B1 för N1). Den registrerade omkörningen gav B3 MAE 5,83 mot B2
6,42, ΔMAE −0,59, DM-p 0,029 och Holm-p 0,059 i {B3, DF}, och lägre MAE än B0, B1 och B2 i båda perioderna. Det är exakt
R7:s läsning "från 2017Q2, alla positioner". Regeln tillämpades mekaniskt: `n2.CHAMPION = "B3"`. Marginalen mot
gränsen 0,10 är mindre än i C2:s körning (0,038), och vinsten är i praktiken en korrektion av TSMC:s konstanta bias
(cirka +1,6 %). N1 är oförändrad (körlogg identisk med 20261123T214413Z). Den första skarpa prognosen med B3 görs
2026-12-05.

## 2026-11-24 – Holdouten öppnas för C3 och C4

Johannes godkände rekommendationen att öppna holdouten för faktormodellen (C3) och regimmodellen (C4) i en körning.
Båda specifikationerna var låsta (`5431f41`, `735dc64`) innan. D2:s holdout öppnas inte för test, eftersom n < 8
prognosdagar ger skugga direkt (registret 2026-11-24). Öppningen loggas i `docs/holdout_logg.md`.


## 2026-11-24 – Holdouten för C3 och C4: resultat

Holdouten öppnades en gång (logg i `docs/holdout_logg.md`, sha före öppning `089f70a`).
- **Faktormodellen (DF):** klarade inte regeln för N2 (MAE 6,65 mot B2 6,45, Holm-p 0,83), och slår inte heller
  huvudmodellen B3 (5,37). N1, N3 och N4 har n < 8 på holdouten och testas inte. DF följer med som skugga i de skarpa
  filerna för N1–N4. Huvudmodellerna är oförändrade: N1 B1, N2 B3, N3–N6 B1.
- **Regimmodellen (C4):** capex-blocket var i expansion hela holdouten. Efterfrågeblocket rapporterade inbromsning
  juli–november 2025 och skifte tillbaka i december 2025. Två strukturbrott, båda i G4 (RPO 2025Q3, Google Cloud 2026Q1).
  Inget samband med prognosfelen. P(inbromsning) och brotten ingår i månadsbilden från 2026-11-30, som en egen sektion
  utanför grenarnas tillstånd. `shift` lagras som namnet på det nya tillståndet, så att hemsidan och kvartalsrapporten
  kan läsa det.
- Resultaten är delvis kända i förväg (publicerade baslinjefel och bakåtfyllda serier, F-E5): `docs/resultat/holdout_c3_c4.md`.

## 2026-11-24 – Ny hemsida, opublicerbara serier i index och G2-spår

Johannes valde rekommendationerna:
- **Ny hemsida** enligt `docs/steg3/hemsida_vision.md`: SvelteKit (statisk) med D3 och Observable Plot, DuckDB-WASM
  bara i utforskningsläget. Python äger all data och licensgrinden (`site_bundle`). Den nya sidan byggs under `/next/`
  och ersätter den gamla först efter paritetskontroll och granskningar.
- **Serier med `publish=False`** (t.ex. PJM, npm, AWS, SWE-bench) får räknas i grenarnas publicerade index. Bara
  riktningen syns, aldrig värden.
- **G2:** ett spår bygger pris vid fast Arena-förmåga (referensmodeller i samma topplista, handgranskad
  namnkoppling) med granskning, och registreras som kärnserie först efter granskningen.
- **G2 Arena-pris underkänt som kärnserie (R8).** Dateringen håller, men serien mäter i praktiken golvet i den billigaste
  prisnivån (tröskeln binder inte från 2024-07/2025-02), den är en stegfunktion, och variant A:s takt bärs av ett
  overifierat Mistral-pris. G2 har kvar en räknad kärnserie. Rättningsspåret X5 tar R-1–R-8. Viktigast är ett
  läckage i `arena.py`: omladdade tavlor (2026-07-07) var daterade till första commit, och det rör även G1:s
  `g1_arena_text_top`. B från 2024-09 prövas först efter rättningen och en ny granskning.
- **X5 klar (2026-11-24):** Arena-läckaget är rättat. Tavlor versioneras per commit, och den verkliga ändringen var
  2026-07-29. Ingen G1-historik eller G1-tillstånd ändrades. Prisrättningar för Gemini är daterade och belagda. B från
  2024-09 klarar ändå inte villkoret, eftersom takten bärs av ett enda prissteg. **Varken A eller B registreras.** De finns kvar
  som beskrivande serier. G2 har fortsatt en räknad kärnserie. Öppet: ska avvecklingsregeln också gälla
  `g2_price_at_capability*`? Den rekommenderas som daterad registerändring efter en körning som visar effekten.
- **Webbgranskningar (2026-11-25).** R-W1 (licens och läckage), R-W2 (tillgänglighet och prestanda) och R-W3 (neutralitet)
  är klara och deras rättningar mergade. Innan `/next/` blir huvudsida (W16) återstår: TBT under 300 ms och tabeller som
  nås utan JS (R-W2 P1, B1 och B2), tydligare märkning av rekonstruerat, balanserat orange och förklarade fackord
  (R-W3), och W13-ändringarna R-W3a–c, som registreras i måttregistret innan de används. Öppet beslut för Johannes: om
  riktningen för inhållna serier som räknas i ett publicerat index (R-W1 punkt 2).









## 2026-11-24 – Riktning efter steg 2: pengarna, makron och förväntningarna först

Johannes valde rekommendationerna i [riktning.md](riktning.md):
- **Riktning:** inga nya prognosvarianter för N1–N6. Nästa körning bygger det som saknas för alla fyra målgrupperna
  (fond, bankens makroavdelning, strategi i bolag och en nyfiken läsare): oberoende källor i diffusionsindexet (K1),
  revideringar av guidance (F1), avskrivningar och intäktskrav med prognosmålet N7 (P1–P3), BNP-bidrag och elpris (M1),
  serverimport på HS-nivå (M2, väntar på Census-nyckeln) och licenskartläggning för G8 (L1).
- **Diffusionsindex v2:** en röst per källfamilj, minst tre familjer för ett tillstånd, och det blir officiell regel
  från första skarpa ögonblicksbilden 2026-11-30. v1 räknas och redovisas bredvid. Ändringen görs efter att backcasten
  har setts. Den motiveras av att serierna inte är oberoende, inte av utfallet, och den gör tillstånden mer försiktiga
  åt båda hållen.
- **Licensnivå:** sidan förblir icke-kommersiell. Varje serie klassas för kommersiell användning (ja, nej eller okänd)
  så att en kommersiellt ren delmängd alltid går att räkna fram. Nya spår väljer öppna licenser när det finns ett val.

## 2026-11-24 – K2: klass för kommersiell användning per serie

Beslutspunkt 3 genomförd. Varje serie har en klass för kommersiell användning, `ja`, `nej` eller `okänd`
(`ai_tracker.licenses`), och klassen är oberoende av `publish`. `catalog.validate()` ger fel för en licenstext som
ingen regel klassar, så en ny serie kan inte läggas till utan klass. Klassen bygger på dokumenterad licenstext och
gissas aldrig. Härledda serier tar den mest restriktiva klassen av sina komponenter. Egna extraktioner ur dokument på
sec.gov är `ja`. Microsofts kurerade serier är `okänd`, eftersom en del rader kommer från microsoft.com, vars villkor
inte är dokumenterade. Census M3 via ALFRED och LMArena med Space-filer är `okänd`, och npm är `okänd`, inte `nej`.
Utfall på main `dceec75`: 488 serier, 341 `ja`, 34 `nej` (Cloudflare, PJM) och 113 `okänd`. I den kommersiellt rena
delmängden är G4–G6 hela, medan G7 och G9 får färre än tre källfamiljer. Detaljer:
[datakallor/licensniva.md](datakallor/licensniva.md).

## 2026-11-24 – K1: diffusionsindex v2 med källfamiljer

- **Regeln** är registrerad i `docs/mattregister.md` ("2026-11-24 – Diffusionsindex v2") och committades före koden
  och före alla v2-värden på verklig data. Familjetabellen följer ägarens läsning av gränsfallen. Inget skäl att
  avvika hittades: urvalsregeln för G1 väljer redan högst en benchmark per benchmarkfamilj, så en familj per vald
  benchmark håller.
- **Ögonblicksbilden** från 2026-11-30: `index` och `state` följer v2, `rule_version` är "v2", och v1 står under
  `v1` i varje gren. Reglerna i filen anger regelversionen och familjetabellen. `snapshot.yml` och
  `pipeline publish` är oförändrade.
- **Paketet** (`site_bundle`) blir version 1.1.0, med bara tillägg och det nya tillståndet "för få källor".
  Webbsessionen behöver lägga till tillståndet i `web/`.
- **En familj med en serie som inte får visas** räknas i indexet men namnges inte och får ingen röst i brevet eller på
  sidorna, på samma sätt som serien själv.
- **Rekonstruktionen** v1 mot v2 väntar på datasnapshoten (`docs/resultat/tillstand.md`, "Index v2").

## 2026-11-24 – P2a: nyttjandeperioder för servrar som katalogserier

- Spåret P2a har extraherat nyttjandeperioderna för servrar och nätverksutrustning hos Microsoft, Alphabet, Amazon,
  Meta, Oracle och CoreWeave ur 10-K, 10-Q och 8-K 2018–2026: 305 rader med citatplats och SHA-256 (68 policyrader,
  21 ändringar, 213 effekter med bolagens egna belopp och 3 klassbyten). Reglerna låstes före kodningen
  (`docs/kallor/nyttjandeperioder.md`).
- 30 katalogserier i G5, glesa stegvärden daterade med inlämningsdagen. De är inga kärnserier. N7 (P3) läser perioderna
  så som de var kända på prognosdagen med `useful_lives.in_effect`.
- Ändringar för en del av flottan (`_SUBSET`, bland annat alla Metas ändringar och Amazons förkortning 2025) blir inga
  serier men finns i CSV:n och i `useful_lives.changes()`.
- `publish=True` enligt registret. Kontrollen mot nyhämtade dokument gav 0 fel av 305. Den oberoende granskningen
  avgör om det står kvar.

## 2026-11-24 – P1: avskrivningar och anläggningstillgångar ur XBRL

- 26 katalogserier i G5 (`dep_*`, `dep_ppe_*`, `ppe_net_*`, `ppe_gross_*`, tre hyp4-summor och `dep_aws`), inte
  kärnserier. Taggvalen förregistrerades före beräkningen. Källa och kontroller: `docs/kallor/sec_avskrivningar.md`.
- **En definition per serie.** När en rad byter innehåll utan omräkning börjar serien vid den nya definitionen (Amazon
  2019, Alphabet 2023), i stället för att äldre perioder skarvas på. Omräkningar över 2 % deklareras per serie, och en
  odeklarerad stoppar hämtningen.
- **Brutto = netto + ackumulerade avskrivningar** ur samma inlämning, eftersom bruttotaggar ibland är delsummor. Amazon
  och Oracle saknar brutto per kvartal, så `ppe_gross_hyp4` finns inte.
- **`dep_msft` är ingen ren avskrivningsserie.** Microsofts rad innehåller "other", och omklassificeringen 2026 räknade
  bara om kvartalen från 2024Q4. P2b och P3 bör använda `dep_ppe_*` där de räcker, och annars redovisa förbehållet.

## 2026-11-24 – F1: revideringar av guidance och överraskning mot guidance

- **Revideringsindex** som i PMI: (uppåt + 0,5 × oförändrade) / antal, alla bolag sammanslagna, med rullande 4 kvartal
  som huvudmått eftersom ett kvartal sällan har 3 revideringar. Ett capex-besked som upprepas i en ny rapport räknas som
  oförändrat. Indexet börjar 2020Q3, när den kurerade capex-filen börjar.
- **Överraskning** mot den senaste guidancen före utfallet, på B2:s bas (TSMC i NT$, Nvidia, Meta och Alphabet), och ett
  index av z utan avdraget medelvärde. Amazon och Microsoft ingår inte, eftersom deras definitioner inte går att jämföra.
- **Egen grupp "Förväntningar mot utfall"** i ögonblicksbilden (`expectations`). Den räknas aldrig i grenarnas index och
  har ingen takt.
- **TSMC:s capex-budget** tolkas deterministiskt ur 6-K (2004–2026), utan LLM.
- **Microsofts sänkning för 2026** (`msft-29`) räknas inte som revidering, på grund av definitionsbrottet R5-F14. Utan
  regeln hade det rullande indexet för 2026Q4 varit 0,62 i stället för 0,67. Båda redovisas i
  `docs/resultat/f1_revideringar.md`.

## 2026-11-24 – Spår M1: BNP-bidrag, datorimport och priser ur BEA:s arkiv och BLS flatfiler

- **BEA-vintages ur BEA:s eget releasearkiv** (`apps.bea.gov/histdata`), inte ur flatfilen eller ALFRED: 107 releaser
  från 2017-10-27, daterade med "Data published" i tabellhuvudet. Katalognamnen är uppladdningsdagar och hade läckt i
  två fall. Ingen nyckel behövs.
- **`ai_invest_contrib_gross`** = BEA:s bidrag från informationsbehandlingsutrustning + programvara (tabell 1.5.2), ur
  samma vintage. **Ingen nettovariant:** BEA publicerar inget BNP-bidrag för datorimport. Importen visas separat.
- **BLS via flatfiler** med projektets generiska klientidentitet i User-Agent (samma som för SEC), eftersom BLS nekar
  klienter utan kontaktuppgift. API:t behövs inte (dess kvot för den delade IP-adressen var slut). Releasedatum tas ur
  BLS arkiv över nyhetsreleaser, alltså primärkällan. KPI SA och PPI dateras efter BLS egna revideringsregler.
- **PPI för databehandling och hosting i G4**, eftersom PPI mäter priset som moln- och hostingbolagen får.
- Inga kärnserier ändras. Detaljer: [kallor/makro_bea_bls.md](kallor/makro_bea_bls.md).

## 2026-11-24 – Fokus: för Johannes och vänner

Projektet byggs främst för Johannes och några vänner, inte för många användare. De fyra målgrupperna i [riktning.md](riktning.md) är en ribba för kvaliteten på förståelsen, inte en plan för spridning. Arbete som bara gäller spridning prioriteras inte: engelsk version, separata vyer per målgrupp, nedladdningar och kommersiell användning. Licensklassningen (K2) behålls, eftersom repot och sidan är publika och klassningen är billig.

Tillägg samma dag: sidan är Johannes främsta sätt att ta in informationen och ska vara ambitiös. Den ska vara intressant och givande att utforska. Den nya sidan enligt `docs/steg3/hemsida_vision.md` fortsätter i full skala. Månadsbrevet ligger kvar som det är (automatiskt) men prioriteras inte. Varje nytt mått ska därför levereras så att sidan kan visa och förklara det.

## 2026-11-24 – L1: källor för G8 v2 kartlagda (inget byggt)

- **Förslag:** G8 v2 med fyra källfamiljer från tre utgivare: Indeeds AI-andel (finns), BLS CES (sysselsättningsgap
  mellan exponerade och mindre exponerade branscher), BLS CPS (arbetslöshetsgap för unga akademiker) och JobTech
  (annonser per yrke i Sverige). Arbetsproduktivitet från BLS är en valfri femte familj. Alla har kommersiell klass `ja`.
- **Användningsmått** (RPS, Anthropic Economic Index, SCB TAB6388 och BTOS Q8) hör till G3 eller används som
  exponeringsmått, inte som utfall i G8.
- **BTOS** frågar sedan cykel 202622 (2026-10) om AI:s effekt på antalet anställda och nyanställda (Q9–Q10). Takt finns
  tidigast 2027-10.
- **BLOCKED:** RPS och NY Fed (värdarna nekas, licens okänd), QCEW, LEHD QWI och O*NET (värdarna nekas) samt
  betalkällorna. CPS-mikrodata kräver Census-nyckeln. AIOE saknar licens (`okänd`).
- **Öppen fråga för Johannes:** gäller pausen för Anthropics webbplatser också Anthropics dataset på Hugging Face
  (öppen licens, annan värd)? Rekommendation: nej, med högst en hämtning per release och bara som exponeringsmått.
- Inget är registrerat och inga utfall är lästa. Designen, med MDE skattad på förperioden före öppning, registreras i
  byggspåret. Detaljer: [datakallor/g8_kandidater.md](datakallor/g8_kandidater.md).

## 2026-11-24 – P2b: intäktskrav som avstämningar

- Fem nya A5-avstämningar (`x_dep_rev`, `x_capcost_rev_r08`, `x_capcost_rev_r12`, `x_dep_capex`, `x_dep_rev_aws`),
  registrerade före beräkningen. De räknas inte i något grenindex. Resultat: `docs/resultat/intaktskrav.md`.
- **`dep_hyp4`, inte `dep_ppe_hyp4`,** valt på täckning (15 mot 9 kvartal). Den registrerade känsligheten visar att
  valet spelar roll: takten 2026Q3 är +12,2 med `dep_hyp4` och +19,4 med `dep_ppe_hyp4`.
- **Avkastningskravet** är ett registrerat intervall, 8–12 % på nettot av anläggningstillgångarna, och ingen skattning.
- **Nämnaren** är totala intäkter, eftersom Meta saknar molnsegment. Bara AWS har en kvot på segmentnivå.

## 2026-11-24 – Rättelse om index v2:s effekt

Beslutet om index v2 motiverades bland annat med att v2 gör tillstånden mer försiktiga åt båda hållen. Backcasten på riktiga data (rekonstruktion, 2026-05 till 2026-10) visar att det inte stämmer genomgående. G8 blir "för få källor", men G6 blir "accelererar" i två månader där v1 sa "stabil", och G7 blir "bromsar in" i två månader. Skälet är att varje familj väger tungt när familjerna är få. Huvudskälet för beslutet, att indexet ska räkna oberoende källor, gäller fortfarande. Rekommendationen är att behålla v2. Johannes informeras.

## 2026-11-24 – M2: serverimport per land, årsfil nu och HS-serier bakom Census-nyckeln

- Census har inga nyckelfria månadsdata per land och vara. Nyckelfritt finns årssummor per land och end-use-kod
  (2016–2025). Spåret hämtar dem som 21 katalogserier i G6 (datorer, datordelar och halvledare från Taiwan, Mexiko,
  Vietnam, Malaysia, Thailand, Kina och hela världen), daterade 10 juli efter årsrevisionen i juni.
- Månadsserierna per HS-kod (8471, 8471.50, 8471.80, 8473.30, 8542) och land är byggda mot Census API men väntar på
  `CENSUS_API_KEY`. Utan nyckeln hoppas de över och fäller inte veckojobbet (`ai_tracker.keyed`).
- Inga av serierna är kärnserier, och inga mått är räknade. Census API:s villkor kräver en notis på hemsidan när
  HS-serierna visas. Detaljer: [kallor/census_hs.md](kallor/census_hs.md).

## 2026-11-24 – P3: N7, avskrivningar 1–8 kvartal

- Förregistrerat före körning (`52a2231`): mål `dep_hyp4`, poolad utvärdering N7b per bolag, baslinjerna B0 och B1 och två
  varianter. V1 är en rak linje på capex med N ur 3–10 år, och V2 använder bolagens angivna nyttjandeperiod för servrar
  (P2a). Ingen V3 med capexguidance, eftersom den skulle kosta tre Holm-platser för mycket liten styrka.
- **N7b avgör, inte summan.** `dep_hyp4` börjar 2023Q1 och har inga utvärderade rader, eftersom MSFT:s brottkvartal
  2025Q4–2026Q3 inte poängsätts. Det är en avvikelse från N1, där N1b bara redovisades. Den är beslutad i förväg.
- **Utfall: ingen variant klarar regeln, och B1 är huvudmodell i alla horisontgrupper.** V1 överskattar systematiskt
  (förhållandet mellan avskrivningar och capex har sjunkit) och är sämre än B1 på kort sikt. V2 har lägre MAE än B1 på
  3–8 kvartal i båda perioderna, men långt från signifikant. Resultat: `docs/resultat/n7.md`.

## 2026-11-24 – Syftet förtydligat: hela AI-flödet, lager för lager

Johannes förtydligade syftet. Projektet byggs för hans egen skull, för att ha bästa möjliga koll på hela AI-flödet lager för lager och se tidigt när något ändrar takt. Kopplingen till egna placeringar är indirekt och görs utanför repot. Repot är publikt och innehåller inga innehav. Följden är att körning 14 omprioriteras ([riktning.md](riktning.md), avsnitt 0 och 8). Först kommer stackens saknade lager (minne, nät, kraft och kylning, datacenterbolag), sedan finansiering, förmåga och kostnad, och Kina. G8 får lägre prioritet.

## 2026-11-24 – R10: granskning av licensnivån (K2)

Granskningen R10 godkänner K2 med anmärkningar ([granskning/r10_licensniva.md](granskning/r10_licensniva.md)).
Mekanismen är rätt byggd, men fyra fel gör en klass för tillåtande. R10-2: Arenas två prisserier är `ja`, fast de
bygger på samma Space-filer som gör Arenas texttavlor `okänd`. R10-3: reglerna saknar restriktiva ord som
"non-commercial", "all rights reserved" och "prohibited", så en text med både ett sådant ord och "CC BY 4.0" blir
`ja`. R10-4: en kopia från FRED fångas inte av ALFRED-regeln. Dessa tre rättas innan K2 mergas. R10-1: F1:s sex
poolade revideringsindex blir `ja`, fast de räknar Microsofts guidance från microsoft.com. Det rättas innan F1
mergas. Alla rättningar är små. Tillsammans ändrar de bara Arenas två prisserier, till `okänd`, och inga
kärnposter. Sju Microsoft-serier med bara SEC-rader är för restriktivt klassade (R10-6), men det är inte bråttom.

## 2026-11-24 – R11: granskning av F1 (revideringar och överraskning)

- **GODKÄND MED ANMÄRKNINGAR** (`docs/granskning/r11_revideringar.md`). Datering och kod håller, och as_of-trunkering
  på verklig data ger identiska värden på 14 datum.
- **Huvudvärdet ändras (R11-1).** CSV:n saknar Microsofts siffra från samtalet 2026-07-29 (cirka 175 mdr på den
  smalare basen). Brottet R5-F14 ligger mellan `msft-26` och den raden, så `msft-29` (170 mdr) är en revidering nedåt
  på samma bas. Rullande 2026Q4 blir 0,62, inte 0,67. "Ingen revidering nedåt sedan 2024" gäller inte.
- Rättningsspåret tar R11-1 och R11-2 före merge (stängningsversionen ska vänta tills kvartalets sista dag har
  passerat) och R11-3 – R11-10 i samma spår. Ägaren avgör om `guid_capex_meta/googl` ska publiceras, eftersom F1:s
  serier i dag kringgår deras `publish=False` (R11-4).

## 2026-11-24 – R14: granskning av P1 (avskrivningar)

- **Godkänd med anmärkningar** (`docs/granskning/r14_avskrivningar.md`). Ombygget är identiskt rad för rad, 15
  handkontroller mot R-sidorna stämmer, och alla `known_from` är inlämningsdatum.
- **Fel (R-1):** Microsoft räknade om 2024Q3 genom sexmånaderstalet i 10-Q 2026-01-28 (6 716 mot 7 383), men
  `dep_msft` behåller det gamla värdet. Fönstret FY2025 blir 30 101 i stället för 29 433, och årstakten 2025Q3 +10 % i
  stället för +21 %. Det rättas innan `dep_msft` och `dep_hyp4` används för takt i P2b och P3. Bara kvartalen i FY2024
  går inte att räkna om.
- Noten för `dep_hyp4` ska säga vilka definitioner som summeras (R-2). `dep_ppe_hyp4` är bättre i definition men har
  bara 9 kvartal.

## 2026-11-24 – R9: granskning av index v2 (K1)

- **Dom: godkänd med anmärkningar** (`docs/granskning/r9_index_v2.md`). Registerposten kom före koden och före alla
  v2-värden på riktiga data. Familjetabellen täcker varje kärnpost en gång och följer regeln. `branch()`,
  licensgrinden, ögonblicksbilden och paketet 1.1.0 håller i alla prövade kantfall.
- **K1 ska vara på `main` före 2026-11-30 22:41 UTC.** Annars skrivs den första skarpa ögonblicksbilden med v1.
- **Före eller vid mergen:** webbsessionen lägger till "för få källor" (S1). Fixturtestet fallerar i kataloger med den
  delade rå-cachen, och det fanns före K1 (S2). Registret får en daterad anteckning om att "försiktigare åt båda
  hållen" inte håller, utan regeländring (S3).

## 2026-11-24 – R15: P2a:s nyttjandeperioder godkända med anmärkningar

- Granskningen R15 (`docs/granskning/r15_nyttjandeperioder.md`) läste alla 305 rader i nyhämtade SEC-dokument: 0 fel
  (stickprovet 0 av 65, 95 % KI 0–5,5 %). Alla 21 ändringar 2018–2026 finns, dateringen stämmer med EDGAR och
  `in_effect(as_of)` använder inget som var okänt på prognosdagen. N7 kan använda serierna som de är.
- `publish=True` står kvar.
- Fyra anmärkningar ska rättas i dokumentationen: självkontrollen ändrades efter första körningen utan att det
  redovisas, avvikelsen från kandidatregeln (82 av 305 rader) ska in i måttregistret, källdokumentet citerar hela
  meningar och noten för `_lo`-serierna ska säga att punkter och intervall blandas. CoreWeaves ändring stod redan i
  S-1 2025-03-03, så known_from är ungefär ett år sent (konservativt).

## 2026-11-24 – X7: rättning av licensnivån efter R10

Fynden R10-1 till R10-6 och R10-8 är rättade på grenen `auto14/x7-licensniva`. Katalogen på `dceec75` blir 488
serier: 346 `ja`, 34 `nej` och 108 `okänd`. Arenas två prisserier blev `okänd` (R10-2), och sju Microsoft-nyckeltal med
bara SEC-rader blev `ja` (R10-6). Inga kärnposter ändras. På körningens sex grenar ändras inget annat, utom att F1:s
sex poolade revideringsindex blir `okänd` när F1 mergas (R10-1).
- **R10-1 med deklarerade rader, inte nyckel-overrides.** En serie som nämner en kurerad fil utan att vara en extraktion
  av den anger i `CURATED_READS` vilka bolags rader den läser. Den kurerade regeln räknas sedan på de raderna, så
  klassen följer filen om villkoren för microsoft.com blir dokumenterade. Saknas uppgiften blir serien `okänd`, och
  `validate` ger fel. `lab_rev_*` behövde ingen override: raderna kopplas till serien, så S-1-serien är `ja` och
  nyhetsrummets två serier `okänd`, som förut.
- **Restriktiva ord ger `okänd`, inte `nej`** (R10-3). Regeln ser inte vilken del av texten begränsningen gäller, så
  klassen är inte bedömd.
- R10-8 rättades också, eftersom felet var litet: en nyckel-override med okänd klass ger fel i `validate`.
  Anteckningarna R10-7 och R10-9 till R10-12 är inte rättade.

## 2026-11-24 – X6: rättningar efter R9 (index v2)

- **S2:** den syntetiska världen har ett eget BTOS-schema (en fil som aldrig skrivs), via `Context.btos_schedule`.
  Fixturerna blir då desamma i varje utcheckning, också med den delade rå-cachen. Enhetstesterna pekar dessutom
  `census_btos.SCHEDULE_LOG` till en tom temp-katalog, på samma sätt som den delade basen.
- **S3:** registret har fått en daterad anteckning om att "försiktigare åt båda hållen" inte håller. Regeln ändras
  inte. `docs/riktning.md` avsnitt 9 är orkestrerarens fil och rättas inte här. Johannes bekräftar att beslut 2 står.
- **S1** är inte rättad här. Webben (`web/`) ägs av en annan session, som lägger till "för få källor".
- **Noter:** index v2 avgörs exakt med bråktal (N1). ASML har en egen licenstext (N8). Brevet och gamla sidan hoppar
  över v1-raden när ingen regel ger tillstånd, och röstraden när alla röstande källor är dolda (N5). Kvartalsrapporten
  säger "källor" under v2 (N6), och båda fotnoterna säger att indexet jämförs oavrundat (N7). Namnregeln i G2 är
  rättad i registeranteckningen (N2). N9 väntar, eftersom ingen registrerad familj berörs i dag.

## 2026-11-24 – Spår X9: rättningar i M1 efter granskning R12

- **R-1 och R-2 är rättade**, och serierna är omräknade. PPI 518210 dateras aldrig före indexets införande
  2002-02-15 (9 värden flyttas). BEA-serierna visar bara perioder som finns i den senaste vintage, så
  `us_imp_computers_real` blandar inte längre basår och börjar 2007Q1. Om en ny release tar bort en lagrad period
  stoppar hämtningen, och serien byggs om medvetet.
- **Rättelse av premissen i M1-posten ovan:** "BEA publicerar inget BNP-bidrag för datorimport" var ofullständigt.
  BEA publicerar `BB01RY` "Final sales of computers" (tabell 1.2.2 rad 17), ett nettobidrag för datorer efter handel,
  men inte för programvara. Ingen serie läggs till. Ägaren avgör om `BB01RY` ska förregistreras.
- **BLS-arkivet läses från 1994-01** (sexsiffriga filnamn). Värden före 1994 får arkivets första releasedag enligt
  den registrerade regeln, alltså 5 år tidigare än förut. Den delen av historiken är inte verifierad (KPI SA före 1994,
  PPI för kommersiell el före 1990). Ingen analys använder den.
- Undantag för luckor gäller per period (`KNOWN_GAP_PERIODS`), och kontaktidentiteten skickas bara till sec.gov och
  bls.gov med underdomäner. Detaljer: daterad post i [mattregister.md](mattregister.md).

## 2026-11-24 – X11: rättning av P1 efter R14

- **R-1 rättat.** Ett värde som en 10-Q räknar om bara genom summorna (hittills i år minus tre månader i samma
  inlämning) blir en version daterad till inlämningen. Regeln gäller P1:s flödesserier, skapar inga nya perioder och
  bortser från avrundning. `dep_msft` 2024Q3 får 6 716 från 2026-01-28, och 2025Q3 på den nya basen (8 147) är känd
  från 2026-01-28 i stället för 2026-10-28. Inga andra serier ändras, och första versionen av varje kvartal är
  oförändrad. Tillägg i registret samma dag.
- **Rättelse av P1-posten ovan.** Omklassificeringen 2026 räknade om kvartalen från 2024Q3, inte från 2024Q4. 2024Q3
  räknades om genom sexmånaderstalet. Bara kvartalen till och med 2024Q2 (FY2024 och tidigare) ligger kvar på den gamla
  basen.
- **Delvis omräkning:** nyckeln behålls, och noten anger sista kvartal på gammal bas (granskningens rekommendation).
  Det var redan P1:s praxis och ändrar inga värden. Ägaren kan välja ny nyckel i stället.
- **P2b och P3 ska köras om på den rättade grenen.** P2b: bygg om `x_dep_rev`, `x_capcost_rev_r08`,
  `x_capcost_rev_r12` och `x_dep_capex` (`x_dep_rev_aws` ändras inte), och rätta påståendet i `intaktskrav.md` att
  Microsoft inte räknade om kvartalen. P3: kör om `python -m ai_tracker.nowcast backtest n7` som en ny daterad körning.
  Utfallen (första versionen) är oförändrade, men indata as_of ändras vid origo 2026-04-20, 2026-07-20 och 2026-10-20.
  N7:s specifikation ändras inte.

## 2026-11-24 – R16: granskning av N7 (spår P3)

- Det negativa resultatet står. Ingen variant klarar regeln, och B1 förblir huvudmodell för N7 i alla horisontgrupper
  (`docs/granskning/r16_n7.md`).
- Ordningen register → kod → körning håller. En oberoende omräkning och en trunkering på verklig data (280 par) gav
  samma prognoser, och indata stämmer med SEC. DM, HLN och Holm räknas om exakt.
- V1:s överskattning är till största delen verklig: längre nyttjandeperioder (Microsofts avskrivningar sjönk FY2023
  enligt bolagets 10-K) och capex med stor andel byggnader. För Meta finns en definitionsdel: amortering på immateriella
  tillgångar, 38 % av raden 2015 och 2 % 2022. Microsofts "other" verkar åt andra hållet.
- Rättning R-1 (should_fix): förklaringen av biasen i `docs/resultat/n7.md`. Övrigt är noter. Fyra registrerade
  egenskaper som saknade test har fått tester.

## 2026-11-24 – X13: rättning efter R16 (N7, spår P3)

- R-1: förklaringen av V1:s överskattning i `docs/resultat/n7.md` bygger nu på det som är belagt: längre
  nyttjandeperioder (Microsofts 10-K FY2021 och FY2023), mixen i capex och Metas amortering på immateriella
  tillgångar. Microsofts "other" ger en underskattning 2024Q4–2025Q3, inte en överskattning.
- Noterna R-2–R-5 är rättade i samma fil. Registret och N7:s specifikation är oförändrade, och beslutet står: B1 är
  huvudmodell i alla horisontgrupper.

## 2026-11-24 – X12: anmärkningarna från R15 rättade

- Spåret X12 rättade R15:s fyra should_fix och noterna N-1 och N-2 för P2a:s nyttjandeperioder. Inga värden och inga
  serier ändrades. De 30 serierna räknades om och är identiska (203 rader).
- Avvikelsen från kandidatregeln (82 av 305 rader) och ändringen av självkontrollen (11 av 305 rader fel med den första
  versionen) står nu i måttregistret. Den kompletterande läsmängden är kod (`useful_lives_corpus.supplementary()`).
- Källdokumentet citerar inte längre hela meningar, och noten för `_lo`-serierna säger att punkter och intervall blandas.
- CoreWeaves ändring kodas inte om ur S-1 (known_from står kvar, konservativt). N-3 kodas inte, eftersom inget använder
  raden. N-4 (ändringar för en del av flottan syns inte i serierna) tas i granskningen av P3/N7.

## 2026-11-24 – X10: rättning av M2 efter R13

- **Nollregeln (R13-1):** en månad utan post räknas som 0 bara mellan seriens egen första och sista post, aldrig före
  eller efter. Då kan en release mellan landanropet och världsanropet inte ge falska nollor. Tillägg i registret samma
  dag. Inga värden ändras, eftersom HS-serierna inte har några rader.
- **Census API:s notis (R13-2):** HS-serierna behåller `publish=True`. Notisen ligger i `Spec.notice` och visas med
  seriens attribution på den nya sidan och i sidfoten på den gamla, när serien har rader. Webbsessionen behöver inte
  ändra något, eftersom attributionen redan visas.
- **Hämtningen (R13-3):** ett misslyckat anrop sparas i cachen, så en körning frågar API:t högst en gång per svar.
  Timeout och 5xx efter två nya försök leder till ett anrop per år med samma form (guidens syntax). Ett API som
  hänger kostar nu cirka 13 minuter per körning i stället för cirka 7 timmar.
- **End-use-brottet 2018/2019 (R13-4)** och skottårsformuleringen (R13-5) är rättade i dokumentet och i `NOTE`.
- **Första hämtningen med nyckel (R13-6) är inte gjord.** Sessionen hade ingen `CENSUS_API_KEY`. Listan är nu ett
  kommando: `python -m ai_tracker.sources.census_hs check`. Rekommendation: kör det i en session med nyckeln före
  nästa måndag, annars blir veckojobbet det första riktiga anropet.

## 2026-11-24 – X8: rättning av F1 efter R11

- **Microsofts julisiffra läggs till och brottet flyttas (R11-1).** Raden `msft-r11f1` (cirka 175 mdr, samtalet
  2026-07-29, #228) läggs till, och en ny registerpost flyttar brottet R5-F14 dit. Skälet är primärkällan: bolaget sa
  att planen var oförändrad utom definitionen. `msft-29` (170 mdr) blir en sänkning på samma bas (−2,9). Rullande
  2026Q4 blir **0,62** (n 13: 4/8/1) och kvartalet 0,50 (n 3). F1:s tidigare 0,67 och "brottet ignoreras" (0,62)
  redovisas som känslighet. Raden som ett brott håller utanför visas med sin storlek (−8,2) i ögonblicksbilden.
- **Metas utsikt för 2020 läggs till (R11-5).** Revideringsindexet ändras för 2020Q4–2021Q3. Metas överraskning börjar
  som registrerat 2021. N1:s B2 och B3 för Meta får 2020: N1b:s MAE för B2 går från 14,43 till 14,34, och N1:s B3 från
  5,44 till 5,43. Inget beslut ändras.
- **Stängningsversionen** skapas när kvartalets sista dag har passerat, som registret säger (R11-2).
- **Känsligheter, inga nya huvudmått.** Indexet med bara siffror (1,00 för 2024Q4–2026Q1, 0,75 för 2026Q4) och TSMC:s
  överraskning i US$ (valutadelens SD 1,3 mot 2,0 för s i NT$). Båda står i avsnittet `expectations`.
- **Publicering (R11-4).** F1-serierna som läser CSV:n har `publish=False` tills ägaren beslutar om
  `guid_capex_meta/googl`.
- **Urvalet** av kandidatmeningar vidgas till meningen efter en capex-mening. Kontrollen läste 81 dokument och hittade
  ingen ny capex-guidance.


## 2026-11-24 – Körning 13 integrerad

- Elva grenar är mergade i ordning på `auto14/integration13`: main (X5 och nya webbsidor), K1, K2, L1, P1, P2a, P2b,
  P3, F1, M1 och M2. Beslutsloggen och kalibreringen har alla poster i tidsordning. I registret står varje spårs poster
  i följd, så att hänvisningar som "posten ovan" fortfarande stämmer. Ingen post är borttagen eller omskriven.
- **K2 efter mergen:** alla 633 serier har en klass, och ingen ny regel behövdes. F1:s känslighet i US$ läser ingen
  rad i den kurerade filen (`CURATED_READS`). K2:s preliminära familjeläsning är borttagen nu när K1:s familjetabell
  finns, och siffrorna blev desamma (R10-12).
- **P2b är omräknat och N7 omkört** på avskrivningsdata efter X11. N7:s beslut ändras inte: ingen variant klarar
  regeln, och B1 är huvudmodell i alla horisontgrupper.
- **Data:** 112 serier lades till i den delade basen och 4 uppdaterades (`guid_capex_*` efter X8). Ingen ersattes.
  HS-serierna (M2) väntar på `CENSUS_API_KEY`.
- F1:s CSV-serier och `guid_capex_*` har kvar `publish=False` tills Johannes beslutar (R11-4). Det strikta
  xfail-testet för "för få källor" står kvar, eftersom webbens `state.ts` på main saknar ordet.

## 2026-11-25 – Inga värden för inhållna serier i den publika ögonblicksbilden

Granskningen L3 (körning 13) visade att den första skarpa ögonblicksbilden (2026-11-30) skulle bära nivå, takt och
percentiler för serier med `publish=False`, bland dem PJM (klass `nej`: "non-members are specifically prohibited from
republishing data"), npm och arXiv (`okänd`), och Microsofts capex-guidance ur `curated/guidance_capex.csv` (R11-4
öppet). Ögonblicksbilden committas till ett publikt repo och skrivs aldrig om, så felet går inte att rätta i efterhand.
- **Regel från och med 2026-11-30.** För en serie som inte får visas har posten nyckel, familj, giltighet, skäl och
  riktning, inga värden: ingen nivå, takt, förändring i takt, percentil, överraskning, standardavvikelse, dödband eller
  brottsannolikhet (C4). Riktningen står kvar, eftersom den räknas i grenens publicerade index (beslutet 2026-11-24).
  Brottflaggan i C4 står kvar, eftersom kort K4 räknar den. Rekonstruktioner i minnet påverkas inte.
- **Förväntningsavsnittet** har inga siffror ur den kurerade filen så länge serierna som läser den har
  `publish=False`. Brottraden för Microsoft visas utan storlek och utan skälstexten, som citerar bolagets siffra
  (`ref` pekar på skälet i koden). Revideringsindexet, överraskningsindexet och Metas och Alphabets överraskningar har
  bara period och datum. Det ändrar X8:s "visas med sin storlek (−8,2) i
  ögonblicksbilden" tills R11-4 är avgjort. TSMC och Nvidia (SEC) visas som förut. Värdena går att räkna fram igen ur
  de daterade serierna när ägaren beslutar.
- **Månadens berättelse** prövar därför inte inhållna serier i K5 och K6, i någon månad (daterad registerändring
  2026-11-25).
- **Rekommendation till Johannes:** behåll regeln. Vill du hellre ha percentiler eller värden i repot behöver det
  beslutet stå här före 2026-11-30 22:41 UTC, eftersom ögonblicksbilden då skrivs en gång för alla.

## 2026-11-25 – Main mergad in i integrationen, paketet blir 1.4.0

- `origin/main` (W12–W14, RW1-X, R-W1–R-W3, WX2 och aktualitetsgränsen 165 dagar för `rev_nvda_datacenter`) är
  mergad in i `auto14/integration13`. Utan gränsen hade uppdateringen före ögonblicksbilden 2026-11-30 gett exit 2.
- **Paketversion.** Main hade redan använt 1.1.0–1.3.0 (berättelsen, backfill-dagen och commit per prognos,
  kvartalsrapporten). K1:s index v2 får därför 1.4.0. Det är en minor: `index` och `state` behåller sina namn, bara
  regeln bakom dem ändras, och fälten är tillägg (`docs/steg3/datakontrakt.md`, Ändringar).
- Loggarna och registret har båda sidornas poster i tidsordning. `quarterly.py` har mains omskrivning med "för få
  källor" i tillståndsordningen.

## 2026-11-25 – T1: tillståndsregeln prövad, ingen granskning rekommenderas

- Förregistrerat test av själva tillståndsregeln (`docs/mattregister.md`, "2026-11-25 – T1", resultat i
  `docs/resultat/t1_tillstandsregeln.md`). Ingen skarp regel ändras, och ögonblicksbilden 2026-11-30 påverkas inte.
- **Revideringar (a):** med v2 har 91 % av grenmånaderna samma tillstånd med dagens data, kappa 0,83 och inga hårda
  byten. Det klarar den registrerade nivån. G6 (Fed G.17) och G7 (EIA:s elförsäljning) byter i 6 och 8 av 34 månader.
  Bara 33 % av de räknade serierna (räknat per månad) har reviderade värden alls, så resten är inte prövat.
- **Information (b):** tillstånden träffar 0,74 (3 månader) och 0,76 (6 månader), mot slumpen 0,68 och 0,71 och
  persistensen 0,70 och 0,76. Holm-p 0,37. Inte avgjort. MDE var 0,28 och 0,44, alltså låg styrka, som sades före
  testet. Bromsar in träffade 1 av 6 och 1 av 4.
- **Regeln tillämpad mekaniskt:** ingen granskning rekommenderas. Marginalen mot persistensen vid 3 månader är 2
  träffar.
- **Rekommendation till Johannes:** läs tillstånden som en beskrivning av läget, inte som en prognos. Gör om testet på
  det skarpa registret när det finns minst 12 ögonblicksbilder (tidigast 2027-11), med en ny registerpost.

## 2026-11-25 – S2: kraft, kylning, elnät och datacenterbolag ur XBRL

- 27 katalogserier, inte kärnserier: intäkter, capex, segment och RPO för Vertiv, GE Vernova, Eaton och Quanta (G7),
  och intäkter, RPO (G4) och capex (G5) för Equinix och Digital Realty. Taggvalen förregistrerades före hämtningen.
  Källa och kontroller: `docs/kallor/sec_stack_kraft.md`.
- **Capex för datacenterbolagen** är bygge och förbättring av egen kapacitet, utan köp av fastigheter och bolag. De två
  är jämförbara med varandra, men inte helt med molnbolagen.
- **Vertivs RPO är BLOCKED i XBRL.** Det Vertiv taggar som RPO är tidsfördelningen av långfristiga förutbetalda
  intäkter. Orderstocken står bara i texten och tas av spår S3.
- **Eatons orderstock** ("total backlog", fasta order) är taggad som RPO och blir `rpo_etn`.
- **Brott:** GE Vernova Electrification delas 2026-04-22 (en del av Electrification Software flyttades till Power).
  Två fel i inlämningarna hanteras med regler i registrets tillägg: en feldaterad fakta hos Equinix och Eatons
  skalbolag 2012.
- Rekommendation: inga av serierna blir kärnserier nu. De flesta är korta (GE Vernova 15 kvartal) eller mest annat än
  AI. `rpo_etn`, `rpo_gev_equipment` och `rpo_pwr` är kandidater för G7 när datacenterandelen finns från S3.

## 2026-11-25 – S1: nät, optik och servrar ur SEC XBRL

- 42 katalogserier i G6 för lagren mellan chip och datacenter: Arista, Cisco, Coherent, Lumentum, Super Micro, Dell,
  HPE och Celestica (totala intäkter, lager, segment- och produktrader, inköpsåtaganden, Aristas kontraktsskulder och
  RPO). Inte kärnserier. Förregistrerat före hämtningen. Källa och kontroller: `docs/kallor/sec_stack_nat.md`.
- **Omfattningsbrott i totala intäkter.** Dell (VMware) och HPE (Enterprise Services och mjukvara) räknade om tidigare
  år när verksamheter blev avvecklade, och versionsregeln blandade då omfattningar i den senaste versionen. `rev_dell`
  börjar därför 2021Q1 och `rev_hpe` 2017Q1 (tillägg i registret). Segmentserierna påverkas inte.
- **Dells AI-rad** (`rev_dell_ai_servers`, från 10-K 2026-03-16) är den enda raden som ett bolag självt kallar AI. Den
  har bara två kvartal nu och växer till sex när 10-Q i december 2026 ger nio månader för FY2026.
- **Två taggningsfel rättade i koden:** Aristas RPO i tre 10-Q 2025 har en kontext ett år för tidigt (omdateras), och
  HPE:s Server delas vid omorganisationen 2026-03-10 trots att kontrollen slår till först 2026-06-02.
- **Rekommendation till Johannes:** låt serierna vara katalogserier tills de har granskats. Om G6 ska få en
  kärnserie för nät eller servrar är `rev_csco_networking` eller `rev_dell_isg` de längsta rena kandidaterna, men båda
  innehåller mycket utanför AI. Ingen av dem ska in före ögonblicksbilden 2026-11-30.

## 2026-11-25 – KR1: spread vid emission som katalogserier (extraktion ur villkorsbilagor)

- **Byggt:** 239 tranchar ur 39 villkorsbilagor (FWP) från Microsoft, Alphabet, Amazon, Meta och Oracle 2020–2026, i
  `curated/credit_issuance.csv`. Elva katalogserier i G5: `issuance_<bolag>_q` (fem bolag), `spread_issue_ai_q`,
  `spread_issue_ai_7_12y_q` och spread per emittent för Alphabet, Amazon, Meta och Oracle. Inte kärnserier, och
  `publish=False` tills extraktionsgranskningen har godkänt. Regler i registret före kodningen
  (`docs/kallor/kredit_emission.md`).
- **Kontroll:** självkontrollen mot nyhämtade dokument gav 0 fel av 239. Alla 39 erbjudanden har samma tranchar som
  det slutliga prospekttillägget. Kontrollen hittade en nolla för mycket i Oracles villkorsbilaga 2021, och raden är
  kodad för hand.
- **Inget marknadsindex.** ICE BofA och Moody's på FRED förbjuder vidarespridning. CoreWeave har inga registrerade
  obligationer (144A), och Metas obligationer 2022 var 144A.
- **Rekommendation till Johannes:** låt granskningen pröva semantiken (källa, valuta, referens) innan serierna
  publiceras. Läs spreaden per emittent, inte den poolade serien, som till stor del visar vilken emittent som kom till
  marknaden.

## 2026-11-25 – Q2: gapet mellan öppna och stängda modeller och Kinas gap (katalogserier)

- Åtta katalogserier i G1 (`g1_open_*`, `g1_china_*`, Arena och ECI). Registerposten committades före koden och koden
  före värdena. Inga kärnserier, inga ändrade tillståndsregler (`docs/kallor/g1_oppen_stangd.md`).
- **Val:** klassningen tas ur källornas egna fält (Arenas `license` och `organization` per tavla, Epochs
  `Accessibility group` och `Country (of organization)`). Kurerade reserver har en referens per rad. Ett namn som inget
  steg klassar lämnas utanför (2 namn i Arena, 4 modeller i ECI).
- **Val:** eftersläpningen i Arena läses inom en tavla, och namnbyten hanteras med namnklasser (27 kurerade byten, 20
  tidiga visningsnamn, 403 mekaniska och 13 kurerade vid bytet 2026-10-20). En borttagen toppmodell ersätts av nästa
  stängda modell i samma månads tavla, vilket kan korta eftersläpningen.
- **Rekommendation till Johannes:** låt serierna vara katalogserier tills en granskning har prövat ersättningsregeln och
  namnklasserna. ECI-varianterna kan räknas först när egna ögonblicksbilder finns.

## 2026-11-25 – Q1: pris vid rörlig förmågetröskel i G2 (katalogserier)

- Fyra katalogserier: `g2_price_rolling12_arena` (huvudvariant), `g2_price_rolling6_arena`, `g2_price_frontier_arena`
  (sammanhang) och `g2_price_rolling12_eci` (backfill). Registerposten committades före värdena
  (`docs/kallor/g2_rorlig_troskel.md`). Grenindex och tillstånd ändras inte.
- **Referensen är ettan för m − L enligt det som är känt vid versionens datum**, inte vid slutet av m − L. Annars blir
  fördröjningen upp till L + 7 månader i mätglappet. Känsligheten visar att valet ändrar L = 6 i 2026-05 – 2026-09.
- **Efterföljarregeln är central:** ettan är ofta ett experimentnamn som tas bort ur tavlan. 9 av 22 månader (L = 12)
  använder en efterföljare med G2A:s överlappsregel. Namn hittas även efter bytet till visningsnamn (normaliserad form).
- **Kostnad per uppgift är BLOCKED:** Agent Arena har kostnad per uppgift först från 2026-11-02, och metoden går inte
  att läsa (arena.ai nekas).
- **Rekommendation till Johannes:** granska `g2_price_rolling12_arena` innan den blir kärnserie. Den skulle ersätta
  Arena-varianterna A och B, inte läggas till.

## 2026-11-25 – Ägarbeslut: spärrregeln, capex-guidance från sec.gov och nettobidraget för datorer

Johannes svarade "kör på dina rekommendationer" på tre rekommendationer samma dag (spår `auto14k/agarbeslut`).

- **1. Spärrregeln står kvar (granskning L3-1).** Ägaren godkände regeln i posten "Inga värden för inhållna serier i
  den publika ögonblicksbilden" ovan. En serie med `publish=False` har bara nyckel, familj, giltighet, skäl och
  riktning i den publika ögonblicksbilden, inga värden. Koden ändras inte. Ögonblicksbilden 2026-11-30 skrivs med
  regeln.
- **2. Capex-guidance ur dokument på sec.gov publiceras (R11-4).**
  - `guid_capex_*` för Alphabet och Meta publiceras. Ägarens uttryckliga godkännande behövdes före N1:s första skarpa
    fil 2027-01-20, eftersom dess indata innehåller serierna (B2).
  - **Amazon ingår med samma regel.** Klassen är `ja`, alla Amazons rader kommer från 10-K, 10-Q och 8-K på sec.gov,
    och extraktionen granskades på samma sätt (E1, R2: 5 av 5 stickprov rätt, R5). Amazon ingår inte i N1:s B2, men
    det finns inget licensskäl att hålla tillbaka serierna.
  - **Regeln står i koden, inte som en lista.** Ett bolag publiceras när alla dess rader i
    `curated/guidance_capex.csv` har källa på sec.gov, vilket är samma villkor som ger klassen `ja`. Ett test kräver
    att `publish` är lika med klassen `ja` för varje serie. En ny rad från en annan värd gör bolagets serier inhållna
    igen.
  - **Microsoft står kvar med `publish=False`.** Raderna kommer från transkripten på microsoft.com, vars villkor inte
    är dokumenterade (klass `okänd`).
  - **F1.** Metas och Alphabets överraskningar läser bara bolagets egna rader. `capex_surprises` väljer bolagets
    rader, och z delar med bolagets egna tidigare överraskningar. Ett test ändrar alla andra bolags rader och kräver
    samma serie. Komponenterna är därför bara bolagets egna `guid_capex_*`, och serierna publiceras. Revideringsindexet,
    medianen och antalen läser alla bolags rader, också Microsofts, och har kvar `publish=False`. Överraskningsindexet
    läser bara Metas och Alphabets rader (och TSMC:s och Nvidias SEC-serier), men står kvar bakom den poolade grinden,
    eftersom beslutet gällde `guid_capex_*` och bolagens egna överraskningar. **Rekommendation:** publicera
    överraskningsindexet med samma bevis, om Johannes vill. Det är en ändring av listan i `CSV_READS`.
  - **Ögonblicksbilden** visar avsnittet `expectations` per bolag. Alphabet, Amazon och Meta har sina värden:
    händelser, antal per år och överraskningar. Microsoft har bara bolag, period, definition och datum, och brottraden
    saknar storlek och skälstext. Revideringsindexet, medianen, antalen, sammansättningen och överraskningsindexet har
    bara period och datum. Det nya fältet `values_withheld_companies` anger bolagen (i dag `msft`). Torrkörning för
    2026-10-31 i en tillfällig katalog: Metas guidance för 2025 (71 000 MUSD, överraskning +1,70, z 1,90), Alphabets
    (92 000 MUSD, −0,60) och revideringarna för 2026 (Meta +7,70, +1,83, +1,80, Alphabet +2,74, Amazon 0,0) syns.
    Ingen av Microsofts siffror och inte skälstexten syns.
  - **Webbplatserna** följer `site.data.publishable` utan ändring i grinden. Paketet byggt mot den riktiga tabellen
    har 0 problem i `validate` och `scan-build`, serierna för Alphabet, Amazon och Meta och de två överraskningarna har
    egna seriesidor, och Microsofts sex serier och åtta F1-serier står bara i `withheld.json`. Den gamla sidan nämner
    Microsofts serier bara i listan över inhållna serier på metodsidan.
- **3. Nettobidraget för datorer förregistreras (R12, R-3).** Registerposten "M1: nettobidrag för datorer efter import
  (BB01RY), ägarbeslut" committades innan något värde hämtades. Serien `us_gdp_contrib_final_sales_computers`
  (tabell 1.2.2 rad 17) har samma arkiv, datering och vintageregel som de andra bidragen i M1. Den är en katalogserie
  och ingen kärnserie. 493 rader, 1978Q2–2026Q3. 24 kvartal i fyra arkiverade releaser lästes för hand, och den
  senaste vintage är lika med flatfilen i alla 194 kvartal. För 2026Q3 är nettobidraget −0,61 procentenheter mot +0,72
  brutto (`us_gdp_contrib_computers`). Cachen laddade bara ned avsnitt 1 igen, och inget extrakt avvek.
- **Kvar:** `docs/datakallor/licensniva.md`:s genererade tabeller är från före beslutet. Två serier har bytt från
  `okänd` till `ja`, och en serie har tillkommit. Kör om rapporten vid nästa integration.

## 2026-11-25 – R17: granskning av S1 (nät, optik och servrar)

- **Godkänd med anmärkningar** (`docs/granskning/r17-nat-servrar.md`). Ombygget är identiskt (42 serier, 1 327 rader),
  alla `known_from` är inlämningsdatum, 85 Q4-rader stämmer med helår − 9M, och 12 bolagskvartal i alla åtta bolag
  kontrollerades mot huvuddokumenten. Registerposten kom före hämtningen, och tillägget efter första bygget är inte
  styrt av seriernas förlopp.
- **Fel (R17-1):** `deferred_rev_anet` 2018Q3 är 221,9 i stället för 529,9. I 10-Q 2018-11-05 är den taggade
  kortfristiga kontraktsskulden en annan post (10,9 i övriga skulder).
- **Fel (R17-2):** första versionen av `rev_dell_isg` 2021Q4 (9 595) är helår på ny bas minus 9M på gammal bas. Rätt
  värde på samma bas är 9 219. Samma sak för `rev_dell_servers_networking` (4 797 mot 4 720). Versionen stod i ett år.
- Fyra anmärkningar om dokumentationen: 2017Q4 i `deferred_rev_anet` är ASC 605, EMC-fusionen saknas för Dells ISG,
  det är inte visat att Aristas åtaganden 2016–2017 har samma definition, och HPE:s RPO är förutbetalda intäkter.
- **Rekommendation:** rätta R17-1 och R17-2 med en daterad registerpost före eller vid mergen. `rev_dell_isg` är inte
  en ren kandidat från 2015, utan från 2017Q1 (38 kvartal). Ingen serie ska bli kärnserie före 2026-11-30.

## 2026-11-25 – R24: granskning av T1 (testet av tillståndsregeln)

- Slutsatsen står: ingen granskning av regeln rekommenderas, och (b) är inte avgjort
  (`docs/granskning/r24-tillstandsregeln.md`).
- Ordningen register → kod → körning håller. Omkörningen gav samma resultatfil. Dagens data byggd bokstavligt (76
  grenmånader), utfall och persistens med egen kod (236 fall), permutationen, Holm, kappa och MDE stämmer. Inget läckage.
- Rättning R24-1 (should_fix): vid 6 månader är persistensen tillståndets egen jämförelse utan dödband (46 av 46
  prediktioner har samma riktning). Likheten 35 mot 35,0 är byggd in i testet, och godkänt kan bara nås vid 3 månader.
- R24-2 till R24-4 (should_fix): persistensen över alla månader (0,61 och 0,56) saknas i resultatet, slumpvärldens test
  håller bara för sitt frö, och filen med tillstånd per månad som fanns före posten ska nämnas. Övrigt är noter. G6:s
  revideringar kommer från G.17:s årsrevision 2026-11-24, en dag före V (verifierat hos Fed).

## 2026-11-25 – R23: granskning av Q2 (öppna mot stängda modeller, Kinas gap)

- **Dom: godkänd med anmärkningar** (`docs/granskning/r23-oppen-stangd.md`). En oberoende omräkning ur rådata ger samma
  värden, `known_from` och `source` i 326 av 330 rader. Arena-klassningen är samtida: 0 avvikelser i 42 712 par mot
  Space-tabeller från samma tid.
- **R23-1 (ska rättas):** en tavla som publiceras sista dagen i månaden och beläggs nästa dag räknas aldrig i den
  månaden. Gapet 2026-04 och 2026-09 blir fel (2026-09: 27,06 i stället för 42,58). **R23-2:** samma fel finns sedan
  tidigare i `sources/vintages.py` och ger fel värden i kärnserien `g1_arena_text_top` (2026-09: 1 517,79 i stället för
  1 533,09). Det bör rättas före ögonblicksbilden 2026-11-30.
- **R23-3:** ECI räknar Kimi K3.1 Pro som öppen i 2026-10, fast Epoch anger att vikterna kom 2026-11-04.
  **Rekommendation till Johannes:** en daterad registerpost som räknar en ECI-modell som öppen från dokumenterat
  viktsläpp. Ingen av serierna blir kärnserie före R23-1, R23-3 och R23-4.

## 2026-11-25 – CN1: Kina via SEC, Alibaba och Baidu som katalogserier

- **Byggt:** 14 katalogserier ur 6-K (`docs/kallor/kina_sec.md`): Alibabas molnsegment i fyra definitioner
  (`rev_baba_cloud_v1`–`v4`, skarvas aldrig), Alibabas capex i två (`capex_baba_v1`, `v2`), Baidus capex (`capex_bidu`,
  `capex_bidu_core`), US$-vyer för de öppna tabellserierna och två textserier för Baidu (`publish=False`). Inga
  kärnserier ändras, och inget index eller tillstånd påverkas.
- **Gränserna** sätts av bolagens egen text om omklassning, inte av en procentgräns. Omräkningarna vid gränserna är
  under 1 %. En odeklarerad omräkning stoppar hämtningen.
- **Datering:** `known_from` = 6-K:ns inlämningsdatum. Fem av Baidus pressmeddelanden 2020–2021 kom 2–6 dagar före
  inlämningen. Registret ändrades före analysen: de används med inlämningsdatumet (konservativt, inget läckage).
- **Valuta:** H.10 hämtas från federalreserve.gov och inte från FRED, eftersom FRED:s villkor ger klassen `okänd`.
- **Kontroll:** molnsegmentet stämmer exakt mot 20-F:ns XBRL på samma definition, Baidus capex exakt mot companyfacts.
  Alla 26 textrader klarar kontrollen mot EDGAR.
- **Rekommendation till Johannes:** låt extraktionsgranskningen pröva Baidus textserier innan de publiceras. Ingen
  serie föreslås som kärnserie nu. `capex_baba_v2` är den bästa kandidaten för G5.

## 2026-11-25 – R22: granskning av Q1 (pris vid rörlig förmågetröskel)

- GODKÄND MED ANMÄRKNINGAR som katalogserier (`docs/granskning/r22-rorlig-troskel.md`). Registerposten kom före kod och
  värden. Alla 118 rader räknades om oberoende, och 17 versioner och månader kontrollerades mot råfilerna. Inget
  läckage och inga fel värden enligt registret.
- Avvikelsen (referensen enligt det som är känt vid versionens datum) håller: alla tavlor i mätglappet finns bara i
  bulkuppladdningen från 2026-04-02.
- `g2_price_rolling12_arena` är inte redo som kärnserie. Efterföljarregeln använder Δ som är upp till 359 dagar gamla,
  och i 5 av 22 månader beror värdet på vilken kandidat som står först (R22-3). Två namnbyten utan överlapp saknas
  (R22-2). ECI-varianten ligger på golvet i 7 av 18 månader utan att dokumentet säger det (R22-4).
- Fem should_fix med strikta xfail-tester, sex nya passerande tester. Grenindex och tillstånd ändras inte.

## 2026-11-25 – S3: order och orderstock ur resultatpressmeddelanden

- Kodningsreglerna låstes och committades före kodningen (471c67b). 575 värden och 42 stopp för Vertiv, GE Vernova,
  Eaton, Dell och Digital Realty ur 113 pressmeddelanden. Equinix (valfritt) är inte kodat.
- 61 katalogserier (G7 kraft och kylning, G6 Dell, G4 Digital Realty), `publish=False` tills den oberoende
  granskningen är godkänd. Klass `ja` (egen extraktion ur sec.gov). Inga kärnserier, och ingen takt är räknad.
- Vertiv slutade ange order i siffror 2026. Alla Vertivs serier är avslutade.
- Stickprov på hela filen: 3 fel av 617, alla grova stoppträffar som agenten läste och bedömde som falska.
- **Rekommendation:** låt granskningen pröva tolkningen av Digital Realtys andel före allt annat. Gasturbinernas GW
  (GE Vernova) och Digital Realtys tecknade avtal i MW är de mest direkta måtten på fysisk utbyggnad, men de är för
  korta (7 och 20 kvartal) för att bli kärnserier nu.

## 2026-11-25 – Rättning efter granskning R25 (spår `auto14k/x22-agarbeslut`)

- **R25-1: överraskningsindexet.** `f1_surprise_index` och `f1_surprise_index_n` listar nu bara Metas och Alphabets
  `guid_capex_*` som komponenter. Det är de rader de läser (`guidance_revisions.CSV_READS`, samma som
  `licenses.CURATED_READS`), och testet i R25 visar det. Klassen blir `ja`. Indexet publiceras ändå inte än, eftersom
  ägarbeslutet i dag gällde `guid_capex_*` och bolagens egna överraskningar. Det står nu uttryckligen
  (`guidance_revisions.AWAITING_OWNER`, nytt fält `Spec.withheld_reason`). Listan över inhållna serier på sidan säger
  "väntar på ägarbeslut" i stället för att namnge Microsofts serier. Ögonblicksbilden visar som förut bara period och
  datum för indexet. **Rekommendation till Johannes:** publicera indexet. Det avslöjar inget som inte redan är publikt,
  eftersom z per bolag går att räkna fram ur de publicerade `f1_surprise_*`. Ändringen är att ta bort nycklarna ur
  `AWAITING_OWNER`.
- **R25-2: definitionsbyte i Amazons serie.** En ny version av en `guid_capex_*`-serie från en rad med en annan
  definition än versionen före är ett definitionsbyte. F1 räknar det inte som en revidering. Seriens not anger nu bytet
  (`guidance_capex.definition_switches`), och månadsbrevet skriver "definitionsbyte från AMZN_CAPEX_UNSPEC till
  AMZN_CASH_CAPEX, inte en revidering" i stället för "tidigare 200 000". I dag gäller det bara Amazons 2026
  (2026-10-29). Torrkörningen av brevet för oktober visar den nya texten. Serien delas inte per definition. Det skulle
  ändra nycklar och rader för en publicerad serie i bastabellen. Paketets versioner räknar fortfarande perioden som
  reviderad (`n_revised_periods`), eftersom paketet saknar ett fält för noten. Att visa noten där är en ändring av
  kontraktet och webben, och hör till ett webbspår.
- **Noterna.** R25-3 rättas i en ny registerpost samma dag. R25-4 står i `docs/drift.md` (Delad data). R25-5:
  stickproven på extraktionen för Amazon, Alphabet och Meta är R2 (5 av 5 för Amazon). R5 kontrollerade bara att
  planerna för nästa år var fullständiga. Hänvisningen "R2: 5 av 5 stickprov rätt, R5" i posten ovan ska läsas så.
  `docs/kallor/guidance.md` är rättad.

## 2026-11-25 – X19: rättning av Q1 efter granskningen R22 (pris vid rörlig förmågetröskel)

- Registerposten "2026-11-25 – X19" committades före omräkningen. Den ändrar tre regler efter att värdena setts, med
  granskningens fynd som skäl: två namnbyten utan överlapp till (`chatgpt-4o-latest`, `claude-opus-4-6-thinking`),
  tröskeln som median över alla giltiga efterföljare i stället för den första, och versionen på månadsslut + 1 med
  tavlor belagda samma dag. `docs/kallor/g2_rorlig_troskel.md` avsnitt 11.
- **Medianen gäller alltid, utan åldersgräns för Δ.** Villkoret "median när Δ är äldre än 90 dagar" ger samma rader på
  dagens data, och en lucka hade tagit bort 2026-03 – 2026-05 för L = 12. Utan gräns väljs ingen gräns i efterhand.
- Effekt: L = 12 ändras i 4 av 22 månader (2025-08 0,13125 → 0,175, 2026-02, 2026-04 och 2026-05). L = 6, frontpriset och
  ECI-varianten ändras inte. Värdet beror inte längre på kandidatordningen, men kandidaternas spridning gör 2026-02 –
  2026-05 osäkra (förbehåll 5).
- Den delade versionsregeln i `vintages.monthly` och `arena_price.build` ändras inte (kärnserier, skyddade moduler). Den
  rättningen hör hemma i ett eget spår.
- Serierna är fortfarande katalogserier. Grenindex och tillstånd ändras inte.

## 2026-11-25 – X21: T1 rättat efter R24

- Rättningsspår X21 har rättat R24-1 till R24-4 och tagit med noterna R24-5 till R24-7
  (`docs/resultat/t1_tillstandsregeln.md`, "Rättningar efter R24"). Testet, konstanterna och beslutsregeln i T1:s
  registerpost är oförändrade, och inget implementationsfel hittades. Ett daterat tillägg står i `docs/mattregister.md`.
- Beslutet står: ingen granskning av regeln rekommenderas, och (b) är inte avgjort. Omkörningen gav samma tal.
- Resultatet säger nu att persistensen vid 6 månader är tillståndets egen jämförelse, så godkänt kan bara nås vid 3
  månader. En konstant prognos "upp" hade träffat 0,81 och 0,80 på tillståndens månader, mer än tillstånden.
- G6:s byten i (a) hänger på G.17:s årsrevision dagen före V: med V = 2026-11-23 byter G6 i 3 månader i stället för 6.
- Nästa registerpost för testet (omkörningen, tidigast 2027-11) ska välja en annan baslinje vid 6 månader och räkna
  spärren för bakåtfyllda serier som i realtid.

## 2026-11-25 – X20: rättning av Q2 efter granskning R23

- **R23-1 och R23-2 rättade:** första versionen av en månad räknar belägg ≤ månadsslut + 1 dag, i
  `sources/vintages.monthly` och i `open_gap.arena_build` (daterad registerpost före koden). Det ändrar
  `g1_arena_text_top` (kärnserie) i 2026-04 och 2026-09 (2026-09: 1 517,79 → 1 533,09), tre andra `g1_arena_*` och
  gapen för öppna och Kina i 2026-04 och 2026-09 (2026-09: 27,06 → 42,58). Ingen eftersläpning ändras, och G1:s
  tillstånd i backcasten 2026-04 – 2026-11 är oförändrat. Serierna är ombyggda i X20:s data.
- **R23-3 rättad:** en ECI-modell räknas som öppen från sitt dokumenterade viktsläpp och som stängd före det. Bara
  2026-10 ändras: 7 månader och gap 9,80 (granskningen skrev 10,60, vilket var fel).
- **R23-4:** ersättningsregelns storlek står nu i dokumentet. Omräkningen ger granskningens tabell.
- **Inte i X20:** `arena_meta.weights_of` (R23-8) och `arena_price.build` är skyddade i körning 14. Den senare har
  samma konstruktion som R23-1 men inga ändrade värden i dag. **Rekommendation till Johannes:** rätta båda i ett eget
  litet spår efter ögonblicksbilden, och slå ihop X20:s data före 2026-11-30.

## 2026-11-25 – R20: KR1:s spread vid emission godkänd med anmärkningar

- Granskningen R20 (`docs/granskning/r20-kredit-emission.md`) läste 72 slumpade rader (30 %) och ett helt dokument per
  emittent i nyhämtade villkorsbilagor: 0 fel (95 % KI 0–5,0 %). Alla 239 rader prövades också med egen text och egen
  indelning per tranche: 0 fel. Alla 39 erbjudanden har samma tranchar som sitt slutliga prospekttillägg, och inget
  registrerat erbjudande 2020–2026 saknas.
- Inget läckage. En oberoende omräkning ger samma 82 rader och samma `known_from`, och varje version går att bygga om ur
  de rader som var inlämnade då.
- Fem should_fix (R20-1 till R20-5): självkontrollen prövar inte talen i tranchens kolumn, dokument som inte kodas
  listas inte, T+n räknar helgdagar som bankdagar, CSV:n skrivs med sex värdesiffror och avstämningen per kvartal
  saknas. Ingen av dem ändrar ett värde i dag.
- **Rekommendation till Johannes:** registrets villkor för granskningen är uppfyllt. Volymerna och spreaden per emittent
  kan få `publish=True` med en daterad registerpost. Visa den poolade serien bara med noten om mixen. Rätta R-1 till R-5
  före nästa ombyggnad av CSV:n.

## 2026-11-25 – X14: rättning av S1 efter R17

- **R17-1 och R17-3 rättade.** `deferred_rev_anet` tar balansräkningens rader i Aristas 10-Q under 2018 (2018Q3 529,9 i
  stället för 221,9) och börjar 2018Q1, den första ASC 606-balansen vid ett kvartalsslut. 2017Q4 (ASC 605) utgår.
- **R17-2 rättat med en smalare regel än granskningens.** I segment- och produktraderna används inte Q4 = helår − 9M
  när 10-K:t räknar om tidigare värden och 9M:s egen inlämning inte gjorde det. Då väntar kvartalet på nästa 10-K.
  `rev_dell_isg` och `rev_dell_servers_networking` 2021Q4 har bara 9 219 och 4 720, kända från 2023-03-30. Villkoret
  om 9M:s inlämning finns för att granskningens förslag också hade hållit tillbaka fem Q4-rader där 10-Q:na redan låg
  på den nya basen. Tre av dem hade försvunnit för gott, och `rev_csco_infra_platforms` hade kortats till tre
  kvartal. `sec.vintages` fick en valfri kontroll, så andra serier är oförändrade.
- **Noterna rättade** (R17-4 till R17-6): EMC i Dells ISG, ordalydelsen för Aristas åtaganden 2016–2017 och att HPE:s RPO
  är förutbetalda intäkter. Rekommendationen i S1:s post ovan gäller med en ändring: `rev_dell_isg` är jämförbar över
  tid från 2017Q1 (38 kvartal), inte från 2015.
- Effekt på datat: 1 324 rader i stället för 1 327, och fyra rader ändrade eller borttagna. Alla 42 serier byggdes om i
  spårets `data/`. Den tabellen ska mergas i stället för S1:s. Om S1:s redan är mergad krävs `--replace` för
  `deferred_rev_anet`, `rev_dell_isg` och `rev_dell_servers_networking`.

## 2026-11-25 – Tokenekonomi och personligt värde (Johannes)

- Projektet byggs i första hand för Johannes. Tokens ska gå till det han läser och använder (`docs/riktning.md`,
  avsnitt 10). Johannes sa ja till båda rekommendationerna.
- **Granskning efter hur mycket han förlitar sig på resultatet.** Full oberoende granskning bara för kärnserier,
  tillståndsregeln, prognoser och extraktioner han agerar på. Katalogserier får spårets egna kontroller och datatester.
  Kraven i CLAUDE.md på stickprov och på en granskning per positivt resultat står kvar. Färre och större spår, 4–5 per
  körning.
- **Personligt läslager:** först "mina lager" på sidan, valt i webbläsaren och sparat bara lokalt, så att inga innehav
  hamnar i repot. Sedan en privat byggning som också visar inhållna serier och aldrig publiceras.
- Användningen loggas i "Värde för Johannes" i `docs/agentkalibrering.md`. Nästa körning efter 14 bygger läsprodukten,
  en lagervy med vad som ändrades per månad, i stället för fler serier.

## 2026-11-25 – R18: granskning av S2 (kraft, kylning, elnät och datacenterbolag)

- **Dom: godkänd med anmärkningar** (`docs/granskning/r18-kraft-datacenter.md`). Registret kom före värdena, och
  tilläggets två regler är regler för datafel. Inga läckage och inga fel värden i 12 handkontroller över alla sex
  bolagen.
- Fyra rättningar före analys: Eatons segment läser inte 2020 års 10-Q (R18-1), Equinix capex förkastar en tagg på
  en rad som inte hör till måttet (R18-2), Vertivs bruttosegment har ett täckningsskäl som inte håller (R18-3), och
  den gemensamma `instance_name` väljer `defnref.xml` i inlämningar 2009–2011 (R18-4, eget spår). Alla ger för sena
  första versioner eller saknad historik, alltså den konservativa sidan.
- Ägarbeslut: ska Vertivs externa segmentförsäljning läggas till bredvid bruttot? Rekommendation: ja.

## 2026-11-25 – X17: rättning av KR1 efter granskningen R20 (spread vid emission)

- Registerposten "2026-11-25 – X17" committades före ombyggnaden. Den ändrar ingen regel. Den säger hur fem låsta regler
  genomförs (R20-1 till R20-5) och preciserar helgdagarna i T+n: den federala kalendern i USA för USD. Långfredagen, en
  lördagshelg som flyttas till fredagen och annan valuta än USD ger ingen framräknad likviddag, och raden kodas för hand.
- Självkontrollen söker nu talen i tranchens del av blocket. Mutationsprov mot de cachade dokumenten: 1 229 av 1 234
  tal från en annan tranche flaggas, mot 0 förut. Den första versionen gav ett falskt fel (en nyckel utan kolon), och
  regeln för var en tranche börjar ändrades till parserns form (tillägg i registret).
- Effekt: ingen. CSV:n och blocken är byte för byte desamma. De 107 dokumenten som inte kodas står med skäl i
  `curated/credit_issuance_skipped.csv`, och de 39 paren FWP–prospekttillägg är exakt R20:s. Självkontrollen och
  `--covers` åt båda hållen mot nyhämtade dokument gav 0 fel.
- Serierna är fortfarande katalogserier med `publish=False`. **Rekommendation till Johannes:** som R20. Volymerna och
  spreaden per emittent kan få `publish=True` med en daterad registerpost, och den poolade serien bara med noten om
  mixen.

## 2026-11-25 – X15: rättning av S2 efter R18

- Alla fyra fel är rättade, och registrets tillägg kom före den nya hämtningen (d2c14cc). Inga värden i redan hämtade
  kvartal ändras. Rättningarna ger längre historik och tidigare första versioner, alltså rätt datering i stället för
  för sen.
- **Eaton** läser segmentnamnen i 2020 års 10-Q. Segmenten börjar 2018Q1, med de omräknade kvartalen 2018–2019 ur 10-Q
  2020-04-30. **Beslut:** 550-dagarsregeln gäller flöden och balanser, inte segmentintäkter, eftersom segmentnoten efter
  en ny indelning redovisar äldre kvartal.
- **Equinix capex** skarvar den äldre taggen och börjar 2009Q3. Taggen står på ett fastighetsköp i två inlämningar,
  inte en: också 10-Q 2011-04-29 (Paris 4). Granskningens förslag "bara 10-Q" räckte därför inte. Regeln utesluter
  taggen ur en inlämning där den skiljer sig från den prioriterade taggen.
- **Vertiv:** de externa segmentserierna `rev_vrt_*_net` är tillagda bredvid bruttot, enligt granskningens
  rekommendation. Rekommendation: använd de externa för tillväxt per region.
- **`defnref.xml`** utesluts i den gemensamma `instance_name`. `dep_msft` får tre kvartal till (från 2009Q4) och tidigare
  versioner 2010Q4–2011Q2. N7 påverkas inte. Digital Realtys sena versioner 2010–2011 hade en annan orsak
  (`ParentCompanyMember` på alla fakta i tre inlämningar), och den är också rättad.

## 2026-11-25 – R19: granskning av S3 (order och orderstock)

- **GODKÄND MED ANMÄRKNINGAR** (`docs/granskning/r19-order-orderstock.md`). Reglerna låstes före kodningen, inget
  läckage och inga fel värden: 0 fel av 65 i stickprovet (95 % KI 0–5,5 %) och inga fel när hela filen prövades med
  egna tabelltolkningar och omhämtade bilagor. 42 av 42 stopp är riktiga.
- Fyra should_fix: GE Vernovas order i GW skarvar 2025Q1 med en smalare definition och saknar konverterade
  reservationer (R-1), en luckorsak säger "not stated" där Eaton anger en gräns (R-2), källdokumentet citerar två hela
  meningar (R-3), och Digital Realtys andel före 2025 är obelagd i seriernas noter (R-4).
- **Rekommendation:** `publish=True` kan prövas för de 52 serierna utan fynd. GE Vernovas order i GW och Digital Realtys
  åtta serier med `dlr_share` väntar på R-1 och R-4. Som kärnkandidat i G7 är gasturbinernas orderstock och
  reservationer i GW bättre än ordren i GW.

## 2026-11-25 – R21: granskning av CN1 (Kina via SEC)

- **Dom: godkänd med anmärkningar** som katalogserier (`docs/granskning/r21-kina-sec.md`). En omräkning ur råkopiorna
  ger samma 301 rader. 22 pressmeddelanden hämtades på nytt från sec.gov och är byte för byte lika med CN1:s kopior. 54
  tal stämmer, också fyra omräknade jämförelsetal. Molnet stämmer exakt mot 20-F, Baidus capex mot companyfacts.
  Inget läckage och inga fel värden.
- **R21-2 (ska rättas):** att omräkningarna vid gränserna är under 1 % gäller DingTalk och T-Head, inte omorganisationen
  2023 (+30 till +36 %) eller capex 2018 (−28 till −54 %). Det rättar CN1-posten ovan.
- **R21-3:** den registrerade kontrollen mot companyfacts körs inte för Alibabas capex. R21 körde den: exakt för
  FY2015–FY2020. **R21-4:** `capex_baba_v1` innehåller licensierade upphovsrätter till videoinnehåll. **R21-1:**
  etiketten för `rev_baba_cloud_v4` säger 2025Q2, men serien börjar 2026Q2.
- **Rekommendation till Johannes:** R21 har läst alla 26 textrader, och mått och kvartal stämmer. Baidus två textserier
  kan få `publish=True` med en daterad ändring. Ingen serie blir kärnserie nu.

## 2026-11-25 – X18: rättning av CN1 efter R21

- **R21-2:** CN1-posten ovan säger att omräkningarna vid gränserna är under 1 %. Det gäller DingTalk och T-Head
  (−0,2 till +0,9 %). Vid omorganisationen 2023 är de +30 till +36 % och för capex 2018 −28 till −54 %.
  `docs/kallor/kina_sec.md` har nu en tabell per gräns. Inget värde ändras, men nivåer över en gräns går inte att
  jämföra.
- **R21-3:** korskontrollen av Alibabas capex körs nu som registrerad, efter en daterad registerändring. `capex_baba_v1`
  stämmer exakt FY2015–FY2018 och `capex_baba_v2` FY2019–FY2020. För FY2021–FY2026 finns ingen rad på samma
  definition, och där redovisas bara kvoten mot den bredare raden (79–98 %). Molnet prövas nu också för FY2016, och det
  stämmer exakt.
- **R21-4 och R21-1:** etiketten och noten för `capex_baba_v1` säger att serien innehåller licensierade upphovsrätter
  till videoinnehåll. Etiketten för `rev_baba_cloud_v4` har inget startkvartal.
- En omräkning ger samma 301 rader som CN1. Inga serier blir kärnserier.

## 2026-11-25 – X16: rättning av S3 efter R19 (order och orderstock)

- **R-1.** GE Vernovas order i GW delas (daterad registerpost, committad före omkodningen). 2025Q1 ("gas turbine
  orders") står ensam med ett stopp. Från 2025Q2 finns två serier: order bland nya kontrakt och reservationer som blev
  order. Orderingången i GW är summan: 5–16 GW per kvartal, inte 1–3. Orderstocken går ihop med båda.
- **R-2–R-4.** Luckorsaken nämner gränsen. Dell-citaten är omskrivna. Noten för Digital Realtys åtta serier med
  `dlr_share` säger att andelen inte anges före 2025 och ger beläggen. Andelen för 2021Q4–2024Q1 är fortfarande obelagd.
- 62 katalogserier, alla `publish=False`. Inga kärnserier, och ingen takt är räknad.
- **Rekommendation:** pröva `publish=True` för de 52 serierna utan fynd och för GE Vernovas två nya GW-serier efter en
  kort granskning av konverteringarna. Vänta med Digital Realtys `dlr_share`-serier tills andelen före 2024Q2 är
  belagd i 10-Q/10-K.

## 2026-11-25 – Körning 14 integrerad

- Åtta rättningsgrenar är mergade i ordning på `auto14k/integration14` från main (9e8541d): X14 (S1), X15 (S2), X16
  (S3), X21 (T1), X17 (KR1), X18 (CN1), X19 (Q1) och X20 (Q2). Varje gren har sitt bygge och sin granskning. Bara
  registret, beslutsloggen och kalibreringen krockade. Båda sidornas poster står i tidsordning, och ett skript har
  kontrollerat rad för rad att ingen post saknas eller står två gånger.
- **Månadsgränsen i `arena_price` (R22-1, R23-2).** Registerposten "Integration 14: månadsgränsen i arena_price" kom
  före koden. Första versionen räknar nu tavlor belagda till och med månadsslut + 1 dag, som X20:s regel. Ombyggnaden
  gav samma värden och `known_from` i alla 34 och 30 rader för `g2_price_at_arena_capability` och `_4o`. Bara
  diagnostiken ändras: tavlorna 2026-04-30 och 2026-09-30 sätter nu värdet för april och september. Q1:s serier läser
  inte `arena_price.build` och är oförändrade. Noten i riktning avsnitt 7 står kvar. Andra kopior av samma
  månadslogik finns inte kvar: `vintages.monthly`, `open_gap` och `price_rolling` är rättade, och övriga läser
  `vintages.monthly` eller räknar redan med beläggets dag.
- **Licenser.** `catalog.validate` klassar alla 805 serier. KR1:s och CN1:s källor fick egna grupper med länk till
  källdokumentet, och ett test kräver att varje grupp har ett dokument. Tabellerna i `datakallor/licensniva.md` är
  genererade om.
- **Data.** Rättningsspårens data är inlagd i basen: 170 serier tillagda och 5 ersatta (`dep_msft` och fyra
  `g1_arena_*`), +3 842 rader (781 117 → 784 959). Byggspåren och granskningsspåren gav inget som saknades i
  rättningsspåren. Deras äldre rader är inte inlagda. Arena-raderna ur integrationen ersatte basens två serier med
  samma innehåll. Datakontrollerna är gröna,
  och rekonstruktionen av tillstånden 2024-01 – 2026-11 är lika med mains i alla 315 grenmånader.
- **Veckohämtningen.** De nya SEC-serierna lägger till cirka 50 anrop till en varm körning och cirka 2 000 till en kall
  (instanser och 6-K, ungefär 2 GB). Det ryms i tidsgränserna. Rekommendation: kör "Weekly data fetch" en gång för hand
  efter pushen, så att cachen är varm före ögonblicksbilden 2026-11-30.
- **Inte ändrat:** publiceringsflaggor och kärnserier. Ägarbesluten som väntar står i `steg2/STATUS.md`. R18-4
  (`defnref.xml` i gemensam instanskod 2009–2011) är rättat för S2:s serier och `dep_msft` men inte kontrollerat för
  alla äldre serier. Det står som öppen fråga.

## 2026-11-25 – KL1: Kreditlagret som följd fråga

- Johannes vill följa tesen om skuld och vilja eller förmåga att investera i de yttre lagren. Den blir en **följd
  fråga**, inte en gren: en registerpost (2026-11-25 KL1), katalogserier med `publish=False` och en månadsrapport
  (`python -m ai_tracker.followed kreditlagret --as-of D`). Inga kärnserier, inget grenindex och ingen tillståndsregel
  ändras, och ögonblicksbilden 2026-11-30 påverkas inte.
- Frågan är symmetrisk, och läsregeln låstes med fasta gränser före beräkningen: pris eller beroende steg först, sedan
  föll capex-takten i yttre lagret medan det inre höll (talar för), eller priset steg och takten höll (emot 1), eller
  takten föll lika i båda lagren (emot 2). Vad orkestreraren och Johannes hade sett i chatten står i posten.
- Extraktionen ur EDGAR följer KR1 och CN1: dokument, plats, SHA-256 och citatet bara under `data/raw`. 400 rader
  (Anthropics S-1, CoreWeaves 8-K och skuldtabeller, Metas datacenterbolag). Självkontroll mot nyhämtade dokument: 400
  av 400 ok. OpenAI har ingen registreringsansökan på EDGAR, och Oracle anger inga belopp för datacenter-SPV.
- Utslag per 2026-11-25: Oracle "talar för", CoreWeave "talar emot (1)", Nebius "inget av mönstren", yttre lagret och
  IREN "kan inte avgöras" (för kort). Per 2025-11-25 gav Oracle "talar emot (1)". Det är en beskrivning, inget test.
- **Rekommendation till Johannes:** läs rapporten månadsvis. Låt en oberoende granskning stickprova extraktionen (minst
  30 % av de agentkodade raderna och en tabell per CoreWeave-rapport) innan något av beloppen används för beslut.
  Gör ingen kärnserie av måtten: med 8–12 kvartal räcker inte historiken för grenarnas regel.

## 2026-11-25 – X23: rättning av KL1 efter granskningen R26 (kreditlagret)

- Registerposten "2026-11-25 – X23" committades före koden och före hämtningen av SpaceX:s dokument. Den ändrar inget
  mått, ingen läsregel och ingen gräns. Den skärper dateringen i labbens korpus, beskriver listan över okodade
  kandidater, tar med SpaceX som tabellrader och säger vilka förbehåll rapporten ska visa.
- **R26-1 och R26-2 (must_fix) är rättade.** En rad med full balansdag flyttas bara till ett tidigare dokument som anger
  samma balansdag. De fem raderna från Anthropic per 2026-09-30 har nu S-1/A 2026-11-02 i stället för S-1:an
  2026-10-26. CoreWeaves 9,750 %-obligation 2031 är 1 750 MUSD ur 8-K:n 2026-04-21. Inga andra av de 394 granskade
  raderna ändrades, och de 53 serierna är oförändrade (1 870 rader).
- **SpaceX (xAI) är med** som tabellrader ur två 10-Q: 38,0 mdr i total skuld per 2026-09-30 för hela koncernen, varav
  25,0 mdr obligationer från 2026-06 (effektiv ränta 6,07 %) och 12,9 mdr misslyckade sale-leaseback av AI-hårdvara
  med Valor, som är närstående. xAI:s egna lån från 2025 hade 12,5 %. SpaceX ingår inte i lagren eller i läsregeln, och
  ingen ny serie skapas (två balansdagar).
- **Okodade kandidater** står med skäl i `curated/kreditlagret_skipped.csv`: 753 rader, 131 med agentens eget skäl och
  622 med en regelkategori. Metas 2026Q1 och 2026Q2, Anthropics åtaganden till SpaceXAI, Nscale och Lambda, DDTL 3.0:s
  ram och DDTL 2.0:s nya marginal är kodade.
- **Microsoft står kvar i det inre lagrets ränta**, med förbehåll. Måttet är låst, och läsregeln läser bara det yttre
  lagrets ränta. Att ta ut Microsoft efter att ha sett talet vore en ändring i efterhand.
- **Läsregeln ändras inte.** Rapporten säger nu att regeln bara läser uppgång och hur ofta A har gällt (Oracle 44 av 58
  kvartal). En regel åt båda hållen är Johannes beslut och kräver en ny post före nästa läsning.
- Självkontrollen mot nyhämtade dokument stoppades av HTTP 429 från SEC, enligt regeln. Mot cachen: 458 av 458 ok.
- **Rekommendation till Johannes:** låt en oberoende granskning läsa de 58 nya och de 6 ändrade raderna (SpaceX,
  Anthropics motparter, Meta, CoreWeave) innan beloppen används för beslut. Den första läsningen på osedda kvartal
  kommer med Oracles inlämning omkring 2026-12-11.

## 2026-11-25 – KL1 integrerad (körning 15)

- `auto15/x23-kreditlagret` (KL1 med granskningen R26 och rättningen X23) är mergad på `auto15/integration15` från
  main (c829d9d). Bara registret, beslutsloggen, kalibreringen och slutet av datakontraktet krockade. Båda sidornas
  poster står i tidsordning, och ett skript har kontrollerat rad för rad att ingen rad saknas eller står två gånger.
  Alla poster från körning 14 är äldre än KL1:s registerpost (4bcb077, 21:06:54 UTC). Den står oändrad, och efter den
  kommer KL1:s tillägg (60af26f) och X23:s tillägg (599b24e).
- **Licenser.** På den sammanslagna katalogen saknade KL1:s två källor en grupp med länk till källdokumentet, så
  testet från körning 14 föll. Båda grupperna länkar nu till `kallor/kreditlagret.md`, och ett nytt test kräver att
  just de 53 `kl_*`-serierna hamnar där. `catalog.validate` klassar alla 858 serier. Tabellerna i
  `datakallor/licensniva.md` är genererade om. Bara de två nya raderna och antalen för G5 ändras.
- **Data.** X23:s data är inlagd i basen: 53 `kl_*`-serier tillagda, inga ersatta eller uppdaterade, +1 870 rader
  (784 959 → 786 829) och +54 rader i hämtloggen. En andra körning gav "nothing to merge". KL1:s och R26:s
  arbetskopior är inte inlagda, eftersom X23 räknade om samma serier. Datakontrollerna är gröna på hela basen. De tre
  SEC-dokumenten för SpaceX låg bara i X23:s egen cache och är kopierade till den delade cachen. Med den sammanslagna
  koden byggs `curated/kreditlagret.csv` (458 rader) och `kreditlagret_skipped.csv` (753 rader) om byte för byte ur
  cachen, utan nätanrop.
- **Torrkörningar** i arbetsytan, inte i `snapshots/`: ögonblicksbilden 2026-11-30, brevet för 2026-11, det verkliga
  paketet och den gamla sidan. Inget `kl_*`-värde och inget värde för en inhållen serie når dem. Bilden och brevet
  nämner ingen `kl_*`-serie. Paketets `withheld.json` och metodsidan listar de 53 nycklarna med etikett, källa och
  skäl, som för andra inhållna serier. Brevets antal nya inhållna serier ökar från 174 till 227, alltså med de 53, utan
  namn.
- **Inte ändrat:** publiceringsflaggor, kärnserier, grentillstånd, index v2 och läsregeln.
- **Öppet:** en oberoende granskning av X23:s 58 nya och 6 rättade rader, självkontrollen mot nyhämtade SEC-dokument
  (stoppad av HTTP 429) och Johannes beslut om läsregeln ska läsa åt båda hållen. Granskningen och beslutet bör vara
  klara före Oracles inlämning omkring 2026-12-11.

## 2026-11-25 – X24: granskningen R27 integrerad och R27-1 rättad (körning 15)

- `auto15/r27-kreditlagret` (granskningen R27, cc53679) är mergad på `auto15/integration15`. Bara en rad i
  kalibreringen kom till, och den hamnade efter X23:s rad. R27:s dom: godkänd med anmärkningar, inget must_fix och
  ett should_fix.
- **R27-1 bekräftat.** I de två 10-Q:erna från SpaceX gäller 5,9 % och 6,3 % bolagets övriga finansieringsavtal, som
  oftast har maskiner och utrustning som säkerhet. Valor-skulden är 99 % av posten. Dess räntekostnad var 351 MUSD
  under 2026Q3, cirka 10,7 % per år av skulden i snitt.
- **Rättning.** Registret fick tillägget X24 före koden. Räntekostnaden för Valor-avtalen kodas per kvartal (två nya
  rader, 460 totalt). Rapporten visar den bredvid bolagets ränta och säger att det inte framgår om Valor-skulden ingår
  i 6,3 %. Bolagets ränta räknas inte i en framtida kupongserie för SpaceX. De 53 serierna, måtten, läsningarna och
  rapporten per 2025-11-25 är oförändrade.
- **Anmärkningarna.** B (regelordningen) är beskriven i registret och i källdokumentet, och koden gäller. A, C och D
  ändras inte: A ger inget läckage, och C och D stämmer med källdokumentet.
- **Självkontroll.** SpaceX:s 46 rader, med de två nya, mot nyhämtade dokument: 46 av 46 ok. Tre anrop till SEC, ett
  i taget, inget 429. Med R27:s 458 av 458 täcker självkontrollen alla rader.
- **Öppet:** Johannes beslut om läsregeln ska läsa åt båda hållen, före Oracles inlämning omkring 2026-12-11.

## 2026-11-26 – CN1: reservväg när EDGAR:s index.json svarar 5xx

- **Problem.** Veckohämtningen 2026-11-25 (manuell körning) var röd. `index.json` för Baidus 6-K
  0001193125-21-014247 svarade 502 i fyra anrop i rad, vart och ett efter `http.get`:s tre nya försök. Därför fick
  `capex_bidu`, `capex_bidu_core` och deras US$-vyer ingen data i Actions-cachen, och aktualitetskontrollen fällde
  jobbet. Övriga serier och datatesterna var gröna, och cachen sparades.
- **Val.** `china_sec.filing_index` läser dokumentlistan ur filingens `-index.htm` när `index.json` svarar 5xx.
  Sidan listar samma dokument med storlek i byte, så `candidate_docs` väljer samma pressmeddelande. Ett 4xx stoppar
  som förut (403 och 429: fair access). Ingen gräns och inget mått ändras, så ingen registerpost behövs. Att hoppa
  över filingen förkastades, eftersom det tyst kan tappa ett pressmeddelande och flytta en årgång.
- **Verifierat i CI.** En manuell veckohämtning på main (e137574, 2026-11-26) var grön. De fyra Baidu-serierna fick 32
  rader var, aktualitetskontrollen var ok och snapshoten har 854 serier. Loggen visar inte om reservvägen användes
  eller om 502-felet hade gått över. Sessionen nådde inte sec.gov, så det gick inte att pröva lokalt.
- **Också i loggen 2026-11-25:** `g3_npm_openai_w` och `g3_npm_anthropic_sdk_w` fick 429 från api.npmjs.org. I
  körningen 2026-11-26 gick båda igenom. Om 429 kommer tillbaka behöver npm-hämtningen glesas ut.

## 2026-11-26 – F0: gemensam motor för följda frågor (körning 16)

- **Varför.** LT1, BG1 och EL1 ska byggas billigt och lika. Det generella i KL1 bröts ut till
  `ai_tracker.followed.common` (inläsning per dag, kvartal, mått via `state.measures`, nästa inlämning, tabeller) och
  `ai_tracker.followed.aggregate` (lageraggregat, version först när alla medlemmar lämnat in, `missing` säger vilka
  som saknas). `series/kreditlagret.py` importerar aggregatet därifrån.
- **Symmetrisk läsregel.** Registerposten "2026-11-26 – F0" låstes före koden. `common.read_rule` läser uppgång och
  nedgång lika, med parametrarna X, Y, g, h, k och tecken, och redovisar hur många ursprung regeln kunde prövas i, per
  riktning. Varje ny fråga låser sina parametrar i en egen post.
- **KL1 oförändrad.** KL1:s regel är låst och läser fortfarande bara uppgång. Rapporten per 2026-11-25 och 2025-11-25
  är byte för byte densamma före och efter (sha256 a1ecd3ad… och 3a2750fb…), och de 1 863 härledda kl_-raderna är
  desamma. Tre golden-filer på den syntetiska världen, renderade med koden före F0, ligger i `tests/golden/`.
- **Upptäckande CLI.** `ai_tracker.followed.questions()` hittar varje modul med `compute` och `render`, så att nya
  spår inte behöver ändra `__main__.py`. `antenner` ger en rad per fråga mot dagen en kalendermånad tidigare.
- **Förkastat.** Att göra KL1:s regel symmetrisk i samma spår, eftersom regeln är låst. Att slå ihop flera ledande
  storheter med "eller" i mallen, eftersom riktningen då blir tvetydig.
- **Öppet för Johannes:** om KL1 ska få en symmetrisk läsning bredvid den låsta, via en ny daterad post, före Oracles
  inlämning omkring 2026-12-11. Rekommendation: ja, en post med mallens regel per pris- och beroendemått mot yttre
  lagrets capex-takt (tecken −1), redovisad bredvid den låsta läsningen.

## 2026-11-26 – LT1: ledtid mellan leverantörernas orderstock och köparnas capex-takt (körning 16)

- **Varför.** Leverantörernas orderstock kan vara en antenn för köparnas capex-takt, men bara om den vänder först.
  Frågan läses åt båda hållen med F0:s symmetriska regel. Registerposten "2026-11-26 – LT1" committades ensam
  (6fb0ccd) innan något mått räknades.
- **Val.** Huvudläsning L1 kraft och elnät (`lt1_rpo_power` = Eatons orderstock + Quantas RPO) före inre lagrets capex
  över fyra kvartal, *k* = 2. Fyra rader till mot inre lagret (L2 nät och servrar, L3 Equinix, O1 Eatons order, O2
  Digital Realtys nya avtal) och L1 mot yttre lagret. Gränser per storhet: 5 för köparnas capex, 10 för leverantörerna
  (klumpigare). *k* = 2 och 4. Inget test, så ingen Holm. Eatons order är en procentserie och räknas om till log-takt.
- **Förkastat.** GE Vernova och Arista i aggregaten (serierna börjar 2024 och 2022, och aggregatet hade krympt till
  några kvartal). HPE (förutbetalda intäkter, annan definition). Ett sammanlagt leverantörsaggregat (Dells och Ciscos
  tjänstedelar hade dominerat). Guidance i läsregeln (kalenderår mot förändring i takt per kvartal kräver en egen
  post).
- **Utfall per 2026-11-26 (sedda data).** Huvudläsningen talar för, men L1 efter K-inre talar också för: leverantörer och
  köpare accelererar samtidigt, och ordningen kan inte avgöras. I historiken ser L1 snarare ut att följa capex
  (2023–2025), men det är två händelser. Per 2025-11-26: inget av mönstren.
- **Öppet för Johannes:** (1) granskning av LT1, särskilt tolkningen av förvärvsmärket i "efter" och om ledtiden ska
  räknas per händelse (första ursprunget i en följd) i en ny post. Rekommendation: ja, en kort post före Dells
  inlämning omkring 2026-12-09. (2) O1 och O2 väntar på granskningen av S3:s extraktion.

## 2026-11-26 – BG1: betalningsgapet som följd fråga (körning 16)

- **Vad.** Intäktskravet (avskrivningar + *r* × anläggningstillgångar netto, som P2b) mot de bärande intäkterna:
  molnintäkterna och RPO för molnfyran (Microsoft, Alphabet, Amazon, Oracle), med CoreWeave som bolagsrad. Läsregeln är
  F0:s symmetriska mall med X = gapets takt och *Y* = förändring i capex-takt för samma bolag (*g* = *h* = 5, *k* = 2,
  tecken −1). Registerposten "2026-11-26 – BG1" committades ensam (`12d9581`) innan något mått räknades.
- **Val.** *r* = 0,10 (mittpunkten i P2b:s intervall) i huvudläsningen, med 0, 0,08 och 0,12 som egna rader. Meta
  utanför (ingen molnintäkt, ingen RPO). CoreWeave bara som bolagsrad, eftersom nettot börjar 2024Q4 och annars kapar
  aggregatets historik. RPO utan Oracle som känslighet för klumpigheten.
- **Inga nya katalogserier.** Storheterna härleds i rapporten med `aggregate.derive` och samma versionsregel som A5 och
  KL1. Skälet: inget nytt hämtas, rapporten fungerar direkt efter merge utan att serier byggs, och `compute(d, tabell)`
  är lika med beräkningen på tabellen kapad vid *d* (prövat på riktiga data vid tre dagar). Nackdelen är att lagrets
  datatester inte täcker storheterna. JSON-rapporten innehåller hela banan för en oberoende omräkning.
- **Utslag (på sedda data).** Per 2026-11-26: huvudläsningen "talar emot" (gapet mot molnintäkterna öppnades och
  capex-takten steg), raden mot RPO "talar för" (gapet mot orderstocken slöts och capex-takten steg), *r* = 0 "inget av
  mönstren". Den mekaniska kopplingen (kravet innehåller capex) gör "talar emot" till ett svagt belägg. Första osedda
  läsningen: Oracle omkring 2026-12-11, molnfyran omkring 2027-01-31.
- **BLOCKED.** Anthropics GAAP-intäkter (inte i katalogen, ingen ny extraktion i körningen) och OpenAI (ingen
  registreringsansökan).
- **Förkastat.** Att slå ihop molnintäkter och RPO till ett X med "eller" (mallen kräver en rad per X). Att räkna
  kravet mot totala intäkter som huvudläsning (P2b har redan de kvoterna, och de visas som sammanhang).

## 2026-11-26 – EL1: följd fråga om elen som begränsning (körning 16)

- **Frågan.** "Blir el den bindande begränsningen för utbyggnaden?" Registerposten "2026-11-26 – EL1" (`f8f0046`)
  committades ensam innan något räknades. F0:s symmetriska regel: fyra X på elsidan (elpris PPI, last i fem
  EIA-930-områden, orderstock för elnät Quanta + Eaton i MUSD, GE Vernovas gasturbiner i GW, takt) mot två Y (capex i
  det inre lagret, Digital Realtys tecknade MW, förändring i takt), tecken −1, *k* = 2, en rad per par. Huvudläsningen är
  orderstock för elnät mot capex.
- **Valt.** Månadsserier blir kvartal som tolvmånadersmedel (ingen säsong). De härledda storheterna räknas i rapporten
  med `aggregate.derive` och `path_measures` och blir inga katalogserier, eftersom de bara behövs här. Takt och inte
  förändring i takt för X, så att en ihållande åtstramning räknas.
- **Utfall (sedda data).** Per 2026-11-26 "talar emot, uppåt": orderstocken växte +45 log-punkter och capex-takten ökade
  +9,6. Posten förutsade det, eftersom Y var sett. Orderstocken har haft impuls uppåt i alla 20 ursprung, så utslaget
  avgörs i praktiken av Y (9 för, 9 emot, 2 inget i historiken). Första osedda läsningen omkring 2027-01-31.
- **Förkastat.** Hela RPO för GE Vernova i elnätsaggregatet (tjänster och förvärv skulle dominera). PJM:s
  kapacitetspriser (klass `nej`). Nya källor (anslutningsköer), som står som förslag med licensfråga.
- **Öppet för Johannes:** (1) om X för orderstockarna ska läsas som förändring i takt i en ny post, så att riktningen
  nedåt kan prövas. Rekommendation: ja, som en extra rad bredvid den låsta, före läsningen 2027-01-31. (2) Om F0:s mall
  ska räkna ett ursprung som prövat bara när Y finns i fönstret. Rekommendation: ja, en rättning av F0 i integrationen.

## 2026-11-26 – Körning 16 integrerad (antenner)

- **Vad.** `auto16/integration16` (F0:s motor) med LT1, BG1 och EL1 mergade i den ordningen (no-ff). Konflikterna låg
  bara i `docs/mattregister.md`, `docs/beslutslogg.md`, `docs/agentkalibrering.md` och de syntetiska fixturerna
  (registrets sha256 i `web-data-fixtures/method.json` och `manifest.json`). Dokumenten löstes genom att alla poster
  behölls, i datumordning och med samma datum i mergeordning (F0, LT1, BG1, EL1). Fixturerna genererades om med `python
  -m ai_tracker.site_bundle fixtures` efter varje merge (bara sha256 ändrades). Inga kodkonflikter: frågorna hittas av
  `followed.questions()`, så ingen gemensam lista behövde ändras.
- **Kontroll.** `catalog.validate()` utan fel. `python -m ai_tracker.followed antenner --as-of 2026-11-26` ger en rad
  per fråga (betalningsgapet, elflaskhalsen, kreditlagret, ledtid), utdata i `docs/resultat/antenner.md`. Varje frågas
  rapport per 2026-11-26 är byte för byte densamma (Markdown och JSON) i integrationen som i spårets egen gren, och
  rapporterna per 2025-11-26 körs utan fel. Full testsvit: första körningen gav ett fel, färskheten för `lt1_*`
  (katalogserier utan rader i basen, eftersom LT1 bara körde riktade tester). Serierna byggdes med `python -m
  ai_tracker.observations lt1_rpo_power lt1_rpo_net lt1_dlr_bookings4` i integrationens `data/` (härledda, ingen
  hämtning), och rapporterna blev oförändrade. Orkestreraren ska köra `python -m ai_tracker.datamerge
  /home/user/wt/integration16/data` efter merge till main.
- **Inte gjort i integrationen.** EL1 rekommenderade att F0:s mall rättas så att ett ursprung räknas som prövat bara när
  Y finns i fönstret. Det är en ändring av en låst regel och kräver en registerpost, så den ligger kvar som beslut.
- **Öppet för Johannes:** (1) F0-rättningen ovan. Rekommendation: ja, som en egen post och ett eget spår med golden före
  och efter för alla fyra frågor. (2) LT1: granskning, särskilt förvärvsmärket i "efter" och ledtid per händelse.
  Rekommendation: ja, före Dells inlämning omkring 2026-12-09. (3) EL1: X för orderstockarna som förändring i takt i en
  extra rad, eftersom orderstocken haft impuls uppåt i alla 20 ursprung och riktningen nedåt annars inte kan prövas.
  Rekommendation: ja, före läsningen 2027-01-31. (4) BG1: granskning före Oracles inlämning omkring 2026-12-11, som är
  första osedda läsningen för både BG1 och KL1. Utslagen per 2026-11-26 är alla på sedda kvartal, och frågorna läser
  delvis samma capex-takt, så de är inte oberoende belägg.

## 2026-11-26 – R28 granskning av körning 16 (antenner)

- **Vad.** Oberoende adversariell granskning av F0, LT1, BG1 och EL1 på `auto16/integration16` (`ff072b8`):
  `docs/granskning/r28_antenner.md`, tester i `tests/test_r28_antenner.py`. Ingen produktionskod ändrad.
- **Dom: GODKÄND MED ANMÄRKNINGAR.** Registerposterna är committade ensamma före kod och rapport och oförändrade sedan
  dess. KL1:s rapport är byte för byte densamma som på main per 2026-11-25 och 2025-11-25. Ingen läcka (samma rapport på
  hel och kapad tabell). Regeln är exakt symmetrisk i koden. Egen omräkning ger samma värden och utslag. 15 av 15
  `ob_*`-rader stämmer mot 8-K på sec.gov.
- **Fynd.** Inget must_fix. Should_fix: förbehållet om sedda data slås av för tidigt (R28-1), överlappande förvärv i LT1
  och fel riktning i resultatdokumentet (R28-2), en skenbar ändring i BG1:s antenn (R28-3), LT1 och EL1 läser samma par
  med motsatt tecken (R28-4), "kunde prövas" räknar ursprung utan Y och regeln har i praktiken bara läst uppgång i EL1
  och BG1 (R28-5).
- **Öppet för Johannes:** (1) Rätta R28-1 och R28-2 före Dells inlämning omkring 2026-12-09. Rekommendation: ja, ett litet
  spår, inga utslag ändras. (2) En mening i antennerna om R28-4. Rekommendation: ja. (3) R28-5 som daterad post före
  läsningen omkring 2027-01-31. Rekommendation: ja, med de nuvarande raderna kvar som huvudläsning. (4) Läs Quantas 10-Q
  för förvärv (R28-7). Rekommendation: ja, som fakta i källdokumenten.

## 2026-11-26 – X25 rättning efter R28 (antenner)

- **Vad.** Rättning av R28-1 till R28-5 i `auto16/integration16`, efter registerposten "2026-11-26 – X25" (committad
  ensam före koden). Inget mått, ingen läsregel och inget utslag ändrat: utslagen för LT1, BG1 och EL1 per 2025-11-26,
  2026-11-26 och 2026-12-31 är identiska före och efter (jämfört i en separat worktree på koden före rättningen).
- **Sedda data per läsning (R28-1).** En läsning är sedd när de värden utfallet vilar på är desamma som i läsningen per
  registerdagen. Valt framför `known_from` per kvartal, eftersom PPI-månader får en ny version när de blir slutliga utan
  att värdet ändras. Kostnad: en extra beräkning per fråga efter registerdagen (1–4 s).
- **Förvärv (R28-2).** Alla förvärv per kvartal, med riktning. Som beskrivning: Boyd Thermal måste ha lagt till mer än
  cirka 3,6 mdr USD till Eatons orderstock för att huvudläsningens X vid 2026Q2 ska hamna under 10. Eatons hela ökning
  2026Q1 var 3,0 mdr. Avvikelsen i "efter" (R28-8) är loggad i posten.
- **Antenner (R28-3, R28-4).** BG1:s fakta har alltid radens kvartal. Antennerna anger huvudläsningens serier och säger
  att LT1 och EL1 har samma huvudpar och är en observation.
- **R28-5 delvis.** F0:s räkning står kvar. Bredvid den: Y känt i hela fönstret, impulser lästa mot Y och riktningen som
  inte prövats (elpriset mot capex: Y känt i 27 av 267 ursprung).
- **Öppet för Johannes:** (1) Byta F0:s "kunde prövas" mot antalet ursprung med Y i fönstret. Rekommendation: ja, som en
  egen post före läsningen omkring 2027-01-31. (2) EL1:s extra rad med förändring i takt för orderstockarna, så att
  riktningen nedåt kan prövas. Rekommendation: ja, i samma post. (3) Quantas förvärv (R28-7) är fortfarande okontrollerade
  och kräver en läsning av Quantas 10-Q, utanför den här körningen (ingen ny källa). Rekommendation: ja, före 2027-01-31.

## 2026-11-26 – Körning 16 slutintegrerad och till main (antenner)

- **Vad.** `auto16/integration16` med F0, LT1, BG1, EL1, granskningen R28 och rättningen X25 pushad till `main`.
  R28 har inget must_fix, och X25 rättade R28-1 till R28-4 och R28-5 delvis. Faslistan i `CLAUDE.md`,
  `docs/steg2/STATUS.md`, `docs/riktning.md` (avsnitt 8, punkt 8) och `docs/drift.md` (avsnittet "Följda frågor")
  uppdaterade.
- **Drift.** Frågornas rapporter och antennraden körs månadsvis med ögonblicksbilden, manuellt tills vidare. De läggs
  inte i `snapshot.yml` i den här körningen, eftersom antennerna inte är ett register och ett automatiskt steg vore ett
  nytt beslut om vad som publiceras.
- **Öppet för Johannes:** om antennraden ska in i det publika månadsbrevet trots `publish=False`-serier.
  Rekommendation: inte än, och i så fall bara utslagen utan värden, efter den första osedda läsningen. Övriga öppna
  punkter står i X25:s post och i `docs/steg2/STATUS.md`, punkt 7.

## 2026-11-27 – S1: symmetriska rader bredvid låsta regler (körning 17)

- **Varför.** Antennerna kunde inte läsa en vändning nedåt: KL1:s låsta regel läser bara uppgång, och EL1:s
  huvudläsning har bara haft impulser uppåt (R28-5). Oracles inlämning omkring 2026-12-11 är den första osedda läsningen.
  Registerposten "2026-11-27 – S1" (`654cbc0`) committades ensam före koden.
- **KL1-S.** F0:s regel per pris- och beroendemått mot samma enhets capex-takt, tecken −1, KL1:s gränser (0,25 och 5
  procentenheter, *h* = 5), *k* = 2. 18 rader: yttre och inre lagret och varje yttre bolag. Ingen ny huvudläsning.
  Avsnitt 1–7 i rapporten (`render_locked`) är byte för byte desamma som före S1, prövat mot golden-filerna från före F0
  och mot rapporterna per 2026-11-27 och 2025-11-27 med koden före S1. KL1-S står i avsnitt 8 och i antennen som fakta.
- **EL1-S.** Orderstocken för elnät som förändring i takt (*g* = 10) mot capex i inre lagret, bredvid de åtta låsta.
  Riktningen nedåt har inträffat (3 nedåt, 4 uppåt). Raden är exakt LT1:s huvudläsning med motsatt tecken, prövat på
  riktiga data: ingen ny observation, och det står i rapporten och antennen.
- **F0:s räkning.** Ett ursprung är prövat bara när Y finns i fönstret (utan impuls: Y känt i alla *k* kvartal).
  Övergångsnotis per rad med det gamla talet. Elpriset mot capex: 27 av 267 i stället för 213. Inga utfall ändrade.
- **Valt.** Bolagen mot sin egen capex (som KL1:s läsning per bolag), inte mot inre lagret, eftersom mekanismen gäller
  samma balansräkning. En fakta per enhet i antennen i stället för 18, så att raden går att läsa.
- **Förkastat.** Att låta KL1-S ersätta huvudläsningen (låst). Att välja ett annat *g* för EL1-S bara för att skilja den
  från LT1 (godtyckligt efter att ha sett LT1).
- **Utfall (sedda data).** Per 2026-11-27: Oracles tre beroendemått "talar för, uppåt" (samma capex-takt −15,8 som den
  låsta läsningen, alltså inget oberoende belägg), inre lagret "talar emot, uppåt", CoreWeave och Nebius "talar för,
  nedåt", yttre lagret kan inte avgöras (ingen förändring i capex-takt före 2026Q4). Beroendemåtten har capex i sig, så
  utslagen är svaga belägg åt båda hållen.
- **Öppet för Johannes:** (1) Granskning av S1 före Oracles inlämning omkring 2026-12-11. Rekommendation: ja, kort, med
  fokus på KL1-S:s mekaniska koppling och byte-identiteten. (2) KL1:s låsta rapport avgör sedda data av läsdagen, så
  stycket om sedda data försvinner efter 2026-11-25 fast inget nytt kvartal kommit. Rekommendation: en post som ger KL1
  X25:s regel per läsning före 2026-12-11. (3) Om EL1-S ska stå kvar när den bara speglar LT1. Rekommendation: ja, men
  läs den inte som en egen observation. (4) R28-7 (Quantas förvärv) är fortfarande okontrollerat och påverkar EL1-S mer
  än huvudläsningen. Rekommendation: läs Quantas 10-Q före 2027-01-31.

## 2026-11-27 – AN1: Anthropics redovisade tal som katalogserier (körning 17)

- **Vad.** Registerposten "2026-11-27 – AN1" låstes ensam före extraktionen. Prospekten (S-1, tre S-1/A och 424B4) har
  XBRL bara för försättsbladet, så HTML-tabellerna tolkas deterministiskt. 19 katalogserier `lab_gaap_anthropic_*`
  (kvartal, år och hittills i år för intäkter, compute, rörelseresultat, kostnad för intäkter, härlett bruttoresultat,
  kassaflöde från rörelsen, capex och förskott), `publish=False`, klass `ja`. Inget värde skiljer sig mellan
  dokumenten. BG1 visar dem i avsnitt 5 bredvid run-rate, och BLOCKED-raden om dem är borta.
- **Val.** Ingen känslighetsrad i BG1:s regel: takten för fyra kvartal finns först för 2026Q4, och med labbets tillväxt
  är X:s tecken i praktiken givet. Labbets intäkter läggs inte till molnintäkterna (dubbelräkning via Bedrock och
  Vertex). Kvartal härleds inte ur skillnader mellan hittills-i-år-värden.
- **Råbudgeten för `withheld.json`** höjdes från 80 till 200 kB (gzip oförändrat 15 kB). Huvudgrenen låg på 79 kB, så
  nästa spår med inhållna serier hade stoppat bygget.
- **Öppet för Johannes:** om de periodiska rapporterna (första 10-K, omkring mars 2027) ska förlänga serierna, med XBRL
  när companyfacts har us-gaap-fakta. Rekommendation: ja, som ett daterat tillägg före 10-K:n, med samma nycklar och
  revideringar som nya versioner. Och om `withheld.json` ska få en kompaktare form i stället för högre budget.

