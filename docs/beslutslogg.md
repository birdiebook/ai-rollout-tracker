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
