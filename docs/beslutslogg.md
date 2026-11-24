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

## 2026-11-24 – Fokus: för Johannes och vänner

Projektet byggs främst för Johannes och några vänner, inte för många användare. De fyra målgrupperna i [riktning.md](riktning.md) är en ribba för kvaliteten på förståelsen, inte en plan för spridning. Arbete som bara gäller spridning prioriteras inte: engelsk version, separata vyer per målgrupp, nedladdningar och kommersiell användning. Licensklassningen (K2) behålls, eftersom repot och sidan är publika och klassningen är billig.

Tillägg samma dag: sidan är Johannes främsta sätt att ta in informationen och ska vara ambitiös. Den ska vara intressant och givande att utforska. Den nya sidan enligt `docs/steg3/hemsida_vision.md` fortsätter i full skala. Månadsbrevet ligger kvar som det är (automatiskt) men prioriteras inte. Varje nytt mått ska därför levereras så att sidan kan visa och förklara det.

## 2026-11-24 – Rättelse om index v2:s effekt

Beslutet om index v2 motiverades bland annat med att v2 gör tillstånden mer försiktiga åt båda hållen. Backcasten på riktiga data (rekonstruktion, 2026-05 till 2026-10) visar att det inte stämmer genomgående. G8 blir "för få källor", men G6 blir "accelererar" i två månader där v1 sa "stabil", och G7 blir "bromsar in" i två månader. Skälet är att varje familj väger tungt när familjerna är få. Huvudskälet för beslutet, att indexet ska räkna oberoende källor, gäller fortfarande. Rekommendationen är att behålla v2. Johannes informeras.

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

## 2026-11-24 – R9: granskning av index v2 (K1)

- **Dom: godkänd med anmärkningar** (`docs/granskning/r9_index_v2.md`). Registerposten kom före koden och före alla
  v2-värden på riktiga data. Familjetabellen täcker varje kärnpost en gång och följer regeln. `branch()`,
  licensgrinden, ögonblicksbilden och paketet 1.1.0 håller i alla prövade kantfall.
- **K1 ska vara på `main` före 2026-11-30 22:41 UTC.** Annars skrivs den första skarpa ögonblicksbilden med v1.
- **Före eller vid mergen:** webbsessionen lägger till "för få källor" (S1). Fixturtestet fallerar i kataloger med den
  delade rå-cachen, och det fanns före K1 (S2). Registret får en daterad anteckning om att "försiktigare åt båda
  hållen" inte håller, utan regeländring (S3).

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

