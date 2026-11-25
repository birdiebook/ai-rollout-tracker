# Kina via SEC: Alibaba och Baidu (G4 och G5)

Spår CN1, körning 14. Byggt och kontrollerat 2026-11-25 mot riktiga inlämningar. Bara data: inga takter, samband
eller prognosvärden är beräknade. Registerpost: `docs/mattregister.md`, "2026-11-25 – CN1" och ändringen av
dateringsregeln samma dag.

Utan Kina stämmer inte "världen" i projektets syfte. Alibaba och Baidu lämnar 20-F varje år och sina
kvartalsrapporter som 6-K. Därför går molnintäkter och capex att följa med samma 6-K-teknik som för TSMC, ASML och
Nebius. Tencent lämnar inget till SEC och ingår inte. Kingsoft Cloud hanns inte med.

Kod:
- `src/ai_tracker/sources/china_sec.py`: EDGAR, sökning efter pressmeddelanden, definitionsperioder och vintages.
- `src/ai_tracker/sources/china_parse.py`: tolkning av tabellerna (deterministisk).
- `src/ai_tracker/sources/china_text.py`: kodning av Baidus meningar (regex), skriver `curated/china_text.csv`.
- `src/ai_tracker/china_text_check.py`: kontroll av varje rad i den kurerade filen mot EDGAR.
- `src/ai_tracker/china_crosscheck.py`: korskontroll mot 20-F.
- `src/ai_tracker/sources/fed_h10.py`: Fed:s H.10, dagliga kurser för renminbi.
- `src/ai_tracker/series/china_sec.py`: `SPECS`.

Tester: `tests/test_china_sec.py` (syntetiska fixturer, inget nät). Hämtning:
`python -m ai_tracker.observations <nycklar>`.

## Serier

Alla är katalogserier, inte kärnserier. Kvartal, release-daterade, MRMB som rapporterat (US$-vyerna i MUSD).

| Nyckel | Gren | Innehåll | Från | Till | Kvartal | Publiceras |
|---|---|---|---|---|---|---|
| `rev_baba_cloud_v1` | G4 | Alibaba, segmentet Cloud computing före DingTalk | 2015Q2 | 2021Q1 | 24 | ja (avslutad) |
| `rev_baba_cloud_v2` | G4 | Alibaba, Cloud computing / Cloud med DingTalk | 2020Q2 | 2023Q1 | 12 | ja (avslutad) |
| `rev_baba_cloud_v3` | G4 | Alibaba, Cloud Intelligence Group utan DingTalk | 2022Q3 | 2026Q1 | 15 | ja (avslutad) |
| `rev_baba_cloud_v4` | G4 | Alibaba, AI Cloud and Compute Services | 2026Q2 | 2026Q3 | 2 | ja |
| `capex_baba_v1` | G5 | Alibaba, köp av anläggningstillgångar och immateriella tillgångar | 2013Q4 | 2018Q1 | 18 | ja (avslutad) |
| `capex_baba_v2` | G5 | Alibaba, köp av anläggningstillgångar utan kontorscampus | 2017Q3 | 2026Q3 | 37 | ja |
| `capex_bidu` | G5 | Baidu, Inc., capital expenditures | 2018Q4 | 2026Q3 | 32 | ja |
| `capex_bidu_core` | G5 | Baidu utan iQIYI, capital expenditures | 2018Q4 | 2026Q3 | 32 | ja |
| `rev_baba_cloud_v4_usd`, `capex_baba_v2_usd`, `capex_bidu_usd`, `capex_bidu_core_usd` | G4/G5 | US$-vy av de öppna tabellserierna | som RMB-serien | | | ja |
| `rev_bidu_ai_cloud_infra` | G4 | Baidu, intäkt från AI Cloud Infra (ur text) | 2025Q3 | 2026Q3 | 5 | nej (väntar på granskning) |
| `rev_bidu_core_nonads` | G4 | Baidu Core, intäkter utanför annonser (ur text) | 2020Q3 | 2025Q3 | 21 | nej (avslutad, väntar på granskning) |

Ingen serie har en revision: inga jämförelsetal ändrades inom en definition. `rev_baba_cloud_v4` har bara två kvartal
i följd. Pressmeddelandena 2026-08 och 2026-11 ger också 2025Q2 och 2025Q3 på den nya definitionen, men 2025Q4 och
2026Q1 saknas. Serien börjar därför efter luckan (`sec.contiguous_tail`). 2025Q4 och 2026Q1 kommer som jämförelsetal
i pressmeddelandena för december- och marskvartalen 2027, och då växer serien bakåt till 2025Q2 av sig själv.

## Definitioner per period

Alibabas räkenskapsår slutar 31 mars, men kvartalen slutar på kalenderkvartalens slut. Kvartalet som slutar 30 juni
är kalenderkvartal 2 (räkenskapsårets Q1). Baidu har kalenderår.

**Alibabas moln.** Gränserna kommer från bolagets egen text i pressmeddelandena:

| Serie | Pressmeddelanden | Rad | Vad bolaget skriver |
|---|---|---|---|
| (läses inte) | 2015-01 – 2016-05 | "Cloud computing and Internet infrastructure" | en intäktskategori före segmentredovisningen |
| `v1` | 2016-08-11 – 2021-05-13 | "Cloud computing" | segmentet från FY2017 |
| `v2` | 2021-08-03 – 2023-05-18 | "Cloud computing", från 2022-02-24 "Cloud" | "Beginning on April 1, 2021, we reclassified the results of our DingTalk business, which was previously reported under the innovation initiatives and others segment, to the cloud computing segment. ... Comparative figures were reclassified" |
| (ingen serie) | 2023-08-10 | "Cloud Intelligence Group" | sex affärsgrupper; segmentintäkt "before consolidation adjustments, which primarily relate to inter-segment adjustments"; DingTalk ingår. Bara ett pressmeddelande (2022Q2 och 2023Q2) |
| `v3` | 2023-11-16 – 2026-05-13 | "Cloud Intelligence Group" | "Starting from the quarter ended September 30, 2023, we reclassified the revenue of our DingTalk business, which was previously reported under Cloud Intelligence Group, to All others" (citerat ur 2024-08-15) |
| `v4` | från 2026-08-20 | "AI Cloud and Compute Services" | "Cloud Intelligence Group and T-Head were combined to form AI Cloud and Compute Services." AI-modellabben och Qwen ligger i ett nytt segment, "AI Labs and Applications" |

Bytet från "Cloud computing" till "Cloud" 2022-02 är bara ett nytt namn. Jämförelsetalen är oförändrade (till exempel
2021Q2 = 16 051 både 2021-08 och 2022-08), så det är samma serie.

**Alibabas capex** är raden i bolagets avstämning mot fritt kassaflöde, alltså kontant betalt:

| Serie | Pressmeddelanden | Rad |
|---|---|---|
| `capex_baba_v1` | 2015-01-29 – 2018-05-04 | "Less: Purchase of property and equipment and intangible assets (excluding land use rights and construction in progress)" |
| (ingen serie) | 2018-08-23 | "... property and equipment, intangible assets and licensed copyrights (excluding land use rights and construction in progress relating to office campus)" |
| `capex_baba_v2` | från 2018-11-02 | "Less: Purchase of property and equipment (excluding land use rights and construction in progress relating to office campus(es))" |

Bytet från "campus" till "campuses" 2020-02 ändrade inga jämförelsetal. 2021-08 – 2022-08 har avstämningen också en
egen rad för immateriella tillgångar, men PP&E-raden är densamma.

**Baidus capex** är raden "Less: Capital expenditures" i kassaflödestabellen (tre månader, RMB). Den finns från
pressmeddelandet 2020-03-04 (Q4 2019, med jämförelsetal för 2018Q4 och 2019Q3). Baidu definierar fritt kassaflöde som
"net cash provided by operating activities less capital expenditures". "Baidu excl. iQIYI represents Baidu, Inc. minus
iQIYI's consolidated cash flows." Pressmeddelandet 2021-02-22 (Q4 2020) har inga tabeller. Därför kommer 2020Q4 från
jämförelsetalen i 2021-05-20.

**Baidus AI-moln.** Baidu anger inte AI Cloud som belopp i pressmeddelandena före 2025Q3, bara tillväxt i procent.
Det som går att följa:
- *AI Cloud Infra* (från 2025-11-18): "AI infrastructure and platform services within AI Cloud serving enterprises
  and the public sector". Från 2026 står det att siffrorna kommer ur bolagets interna redovisning, utan revision.
- *Baidu Cores non-online marketing revenue* (2020-11 – 2025-11, 2020-11 – 2021-05 "non-marketing revenue"):
  Baidu Cores intäkter utanför annonser. Bolaget skriver att ökningen drivs av molnet ("driven by cloud and other
  services", senare "mainly driven by AI Cloud business"), men måttet innehåller mer än molnet. Från 2026-02 heter
  Baidu Core "Baidu General Business" med uppdelningen AI-powered Business, Legacy Business och Others. Måttet anges
  inte längre, och serien är avslutad.

## Datering

`known_from` = 6-K:ns inlämningsdatum i EDGAR. Kontroll mot datumet i pressmeddelandets dateline (eller
underskriften i Alibabas HKEX-format):

| Bolag | Pressmeddelanden | Samma dag | 1 dag före | 2–6 dagar före |
|---|---|---|---|---|
| Alibaba | 48 | 47 | 1 (2016-01-29) | 0 |
| Baidu | 28 | 17 | 6 | 5 |

Baidus fem sena inlämningar: 2020-03-04 (dateline 2020-02-27), 2020-05-20 (05-18), 2020-08-17 (08-13), 2021-02-22
(02-17) och 2021-05-20 (05-18). Siffrorna var då offentliga 2–6 dagar före `known_from`. Det ger inget läckage, bara
en sen `known_from`. Registret ändrades före analysen: pressmeddelandena används, med inlämningsdatumet. Från 2021-08
lämnar Baidu in samma dag eller dagen efter.

Alibabas 6-K tas emot av EDGAR oftast 20–21 UTC (39 av 48), alltså efter börsens stängning i New York. Dateline är
samma dag, så siffran kan ha varit offentlig några timmar före inlämningen, samma kalenderdag. Klockslaget för
pressmeddelandet är inte kontrollerat. Publiceringsfördröjning från kvartalets slut: Alibaba 24–78 dagar (median 44), Baidu 44–64 dagar (median
51). Aktualitetsgränsen är den största + 92 + 30 dagar: 200 för Alibaba och 186 för Baidu.

## US$-vy

MUSD = MRMB / kvartalets medelkurs. Medelkursen är medelvärdet av de dagliga kurserna (CNY per USD) i Fed:s H.10
under kalenderkvartalet. Det är samma data som FRED:s DEXCHUS, men den hämtas från Fed:s egen sida
(`federalreserve.gov/releases/h10/hist/dat00_ch.htm`, "Historical Rates for the Chinese Renminbi (Rates in Chinese
yuan per U.S. dollar)", från 2000-01-03, "ND" på dagar utan kurs). FRED:s villkor förbjuder användning med
maskininlärning, och projektet klassar därför FRED-kopior som `okänd` (`ai_tracker.licenses`, regeln alfred). Fed:s
egen sida är public domain. Ett kvartal med färre än 55 noterade dagar får ingen kurs. `known_from` = max(RMB-radens
`known_from`, kvartalets slut + 10 dagar). Sidan har bara aktuell vintage. Att kurserna inte revideras är ett
antagande, inte kontrollerat mot arkiverade releaser. Bolagens egna US$-belopp i pressmeddelandena använder kursen på
kvartalets sista dag och är därför inte samma sak som vyn här.

## Kontroller

**Handkontroll** mot pressmeddelandets text (rad för rad, värdet i serien mot tabellen eller meningen):

| Bolag | Inlämnad | Accession | Kvartal | Moln (serie) | Capex (serie) |
|---|---|---|---|---|---|
| Alibaba | 2017-08-17 | 0001104659-17-052468 | 2017Q2 | 2 431 (`v1`) | 3 162 (`capex_baba_v1`) |
| Alibaba | 2019-05-15 | 0001104659-19-029738 | 2019Q1 | 7 726 (`v1`) | 5 688 |
| Alibaba | 2021-08-03 | 0001104659-21-099438 | 2021Q2 | 16 051 (`v2`) | 10 897 |
| Alibaba | 2023-02-23 | 0001104659-23-024752 | 2022Q4 | 20 179 (`v2`) | 5 793 |
| Alibaba | 2024-11-15 | 0001104659-24-119688 | 2024Q3 | 29 610 (`v3`) | 16 977 |
| Alibaba | 2026-05-13 | 0001104659-26-060224 | 2026Q1 | 41 626 (`v3`) | 26 588 |
| Alibaba | 2026-11-19 | 0001104659-26-130115 | 2026Q3 | 60 973 (`v4`) | 50 463 |
| Baidu | 2020-03-04 | 0001193125-20-061595 | 2019Q4 | – | 884 (utan iQIYI 652) |
| Baidu | 2021-11-18 | 0001193125-21-333786 | 2021Q3 | 5 200 (utanför annonser) | 2 664 (2 548) |
| Baidu | 2023-05-16 | 0001193125-23-145594 | 2023Q1 | 6 400 (utanför annonser) | 1 295 (1 295) |
| Baidu | 2024-11-21 | 0001193125-24-263052 | 2024Q3 | 7 700 (utanför annonser) | 1 645 (1 637) |
| Baidu | 2025-08-20 | 0001193125-25-183792 | 2025Q2 | 10 000 (utanför annonser) | 3 800 (3 779) |
| Baidu | 2026-11-16 | 0001193125-26-462286 | 2026Q3 | 8 200 (AI Cloud Infra) | 7 349 (7 307) |

Alla 13 stämmer. I tabellerna står Alibabas capex som utflöde i parentes, och serien lagrar beloppet positivt.

**Textraderna.** `python -m ai_tracker.china_text_check` hämtade alla 26 dokument på nytt (utan cache): 26 av 26
har rätt hash vid lokatorn, talet står i meningen, och inlämningsdatum och acceptanstid stämmer med EDGAR. Det
bekräftar plats, hash, tal och datum, inte tolkningen (mått och kvartal). Den delen är för extraktionsgranskningen.
Kodningen: 26 rader kodade, 11 kandidatmeningar inte kodade. 5 är helårssiffror efter rubriken "Fiscal Year <år>
Results". 1 är ett citat med "exceeded RMB 10 billion" (2025-08-20). 1 är "approximately RMB 20 billion for the full
year 2025". 4 är tabeller i miljarder RMB i 2026 års pressmeddelanden (se nedan). I den första körningen matchade
mönstret för rubriken titeln i fjärde kvartalets pressmeddelanden, och inga meningar där kodades. Det var ett fel i
koden, inte i regeln, och det är rättat (registret, samma dag).

**Korskontroll mot 20-F** (`python -m ai_tracker.china_crosscheck`):
- *Alibabas moln:* summan av fyra kvartal (april–mars) stämmer exakt (0 MRMB) med segmentposten i 20-F:ns XBRL för
  varje räkenskapsår på samma definition: `v1` FY2017–FY2021 (20-F 2019–2021, CloudComputingSegmentMember), `v2`
  FY2021–FY2023 (20-F 2022–2023) och `v3` FY2024–FY2026 (20-F 2024–2026, CloudIntelligenceGroupMember). På olika
  definitioner skiljer det som väntat: FY2021 är 60 120 i `v1` och 60 558 i `v2` (DingTalk). 20-F för FY2024 räknar
  om FY2023 till Cloud Intelligence Group, 103 497, mot 77 203 för Cloud i `v2`.
- *Alibabas capex:* summan av fyra kvartal av `capex_baba_v2` är 76–98 % av 20-F:ns
  `PaymentsToAcquireLandUseRightsPropertyAndEquipment` (FY2019–FY2026). Skillnaden är väntad: bolagets rad räknar
  inte med mark och bygge av kontorscampus. Den används inte för att justera något.
- *Baidus capex:* summan av fyra kvartal av `capex_bidu` stämmer exakt med companyfacts
  `PaymentsToAcquirePropertyPlantAndEquipment` för 2019–2025.
- companyfacts har Alibabas capex bara för FY2017–FY2020 (`PaymentsToAcquireOtherPropertyPlantAndEquipment`). Senare
  år finns bara i 20-F:ns egen XBRL-instans, som korskontrollen läser.

## Licens

SEC: "Information presented on sec.gov is considered public information and may be copied or further distributed by
users of the web site without the SEC's permission. Please consider appropriate citation to the SEC as the source."
(sec.gov/privacy, Website Dissemination). Bara extraherade siffror publiceras, med källhänvisning. Klass för
kommersiell användning: `ja` för alla serier (regeln sec, de kurerade raderna kommer alla från sec.gov, och US$-vyerna
är härledda ur SEC och Fed:s public domain). Inga nya regler behövdes i `ai_tracker.licenses`. Textserierna har
`publish=False` tills extraktionsgranskningen är godkänd.

## Förbehåll

- **Segmentdefinitioner.** Fyra definitioner av Alibabas moln på tio år, och varje är en egen serie. Att jämföra
  nivåer över en gräns är fel. Gränserna kommer från bolagets egen text. Omräkningarna vid gränserna är små (under 1 %) och
  hade inte syntes med en procentgräns. Ett nytt omklassat pressmeddelande som inte deklareras stoppar hämtningen med fel.
- **Intäkter mellan segment.** Från 2023-08 redovisas Alibabas segment före koncernelimineringar. Cloud Intelligence
  Group innehåller alltså intäkter från Alibabas egna verksamheter. För FY2023 är skillnaden mot den gamla
  definitionen (utan interna intäkter och med DingTalk) 34 %. Flera pressmeddelanden nämner intäkter från externa kunder
  i texten, men tabellen har bara segmentets hela intäkt.
- **T-Head.** `v4` innehåller Alibabas chipenhet. Det är inte bara moln längre.
- **RMB.** Serierna är i RMB. US$-vyn bär valutaeffekten (kvartalsmedel 2013Q4–2026Q3 mellan 6,09 och 7,27 CNY per USD).
- **Räkenskapsår.** Alibabas "Q1" är kalenderkvartal 2. Serierna är i kalenderkvartal.
- **AI-andelen.** Till och med 2026-03 anger ingen av bolagen AI:s andel av molnintäkten som belopp. Alibaba skrev
  "triple-digit growth" för AI-relaterade produkter. Från 2026-05 anger Alibaba "AI-related product revenue" i
  miljoner RMB i texten. Det är inte extraherat här (se öppna frågor).
- **Baidus mått är tunna.** AI Cloud Infra har 5 kvartal i miljarder RMB med en decimal (±50 MRMB). Intäkter utanför
  annonser är bredare än molnet. Båda kommer ur löptext och väntar på granskning.
- **Korta serier och regimbrott.** `v4` har 2 kvartal och AI Cloud Infra 5. Med så korta serier kan en ändring i takt
  vara slump.
- **Capex-definitionerna** är bolagens egna och skiljer sig åt: Alibaba utan mark och kontorscampus, Baidu som hela
  kassaflödesraden. Nivåerna är inte jämförbara med de amerikanska hyperscalers capex rakt av.

## Drift

Tabellserierna uppdateras av veckohämtningen: nya 6-K hämtas och tolkas, och gamla dokument läses ur råkopiorna. Ett
pressmeddelande som inte hör till någon deklarerad definition, eller som räknar om ett publicerat värde, stoppar
hämtningen av serien med `DefinitionBreakError`. Då ska texten läsas och gränsen deklareras i `china_sec.ERAS`, med en
daterad registerpost. Textserierna uppdateras inte av sig själva: efter ett nytt Baidu-pressmeddelande körs
`python -m ai_tracker.sources.china_text --write` och `python -m ai_tracker.china_text_check`, och CSV-filen committas.

## Öppna frågor och nästa steg

- Baidus pressmeddelanden från 2026 har en tabell i miljarder RMB med AI Cloud Infra också för 2025Q1, 2025Q2, FY2024
  och FY2025. Den läses inte här. En tabelltolkning skulle ge serien två kvartal till bakåt.
- Alibabas "AI-related product revenue" (från 2026-05, i text) är en kandidat för en egen extraktion med
  registerpost och kodningsregler.
- Kingsoft Cloud (6-K) hanns inte med.
- Ingen av serierna föreslås som kärnserie nu. `capex_baba_v2` (37 kvartal, en definition sedan 2018, exakt mot 20-F
  på kassaflödets definition med kända undantag) är den bästa kandidaten för G5 om Kina ska vägas in. Det kräver en
  egen registerpost och en granskning.
