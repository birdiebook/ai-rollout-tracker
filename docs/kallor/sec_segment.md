# Källa: SEC EDGAR XBRL-instanser (segmentintäkter)

Spår T2. Byggt och kontrollerat 2026-11-23 mot riktiga inlämningar. Kod:
`src/ai_tracker/sources/sec_segment.py` (hämtning, tolkning, definitionsbrott) och
`src/ai_tracker/series/sec_segments.py` (rader och katalogposter). Kvartals- och versionslogiken är
densamma som för companyfacts och importeras från `ai_tracker.sources.sec` (se `docs/kallor/sec.md`).
Tester: `tests/test_sec_segment.py` (syntetiska instansdokument, inget nät). Hämtning:
`python -m ai_tracker.observations <nycklar>`. Här finns ingen trendanalys. Om serierna blir kärnserier
för G4 beslutas separat i `docs/mattregister.md`.

## Val av källa

companyfacts saknar dimensioner. Två källor har dem: SEC:s Financial Statement and Notes Data Sets
(zip-filer med alla bolag) och varje inlämnings egen XBRL-instans. **Instansdokumenten valdes.**
Det behövs bara cirka 175 inlämningar från fem bolag, varje inlämning har sitt eget datum (`filed`)
direkt i inlämningslistan, och bolagsspecifika medlemmar (t.ex. `amzn:AmazonWebServicesSegmentMember`)
följer med oförändrade. Notes-filerna täcker alla bolag och är därför mycket större per period. De
provades inte.

- Inlämningslista: `data.sec.gov/submissions/CIK##########.json` (plus äldre sidfiler). 10-Q, 10-K och
  ändringar (`/A`), samma formulärfilter som i `sec.py`.
- Instans: `www.sec.gov/Archives/edgar/data/<cik>/<acc>/index.json` ger filnamnen. Från 2019 är det
  den extraherade instansen ur inline-XBRL (`*_htm.xml`), och före 2019 den vanliga instansen (`*.xml`,
  inte `_cal/_def/_lab/_pre`). Två 10-K/A från Alphabet (2016, 2019) saknar XBRL och hoppas över.
- Åtkomst via `ai_tracker.http.get`: 5 anrop/s per värd, deklarerad User-Agent från `.env`. Inga värdar
  nekades av proxyn. Inlämningar ändras aldrig, så råkopiorna i `data/raw/sec_segment/<datum>/`
  återanvänds vid senare körningar. Första körningen gör cirka 360 anrop, och därefter hämtas bara nya
  inlämningar.
- Licens: samma som `sec.md` (sec.gov/privacy, kontrollerad 2026-11-23, public information). Därför
  `publish=True`, med SEC som källa.

## Extraktion

- En fakta räknas när kontextens dimensioner är exakt (axel, medlem). Den enda tillåtna extra dimensionen
  är `ConsolidationItemsAxis = OperatingSegmentsMember`, som Microsoft och Amazon lade till på
  segmentfakta före 2017. Fakta med fler dimensioner, t.ex. segment × produkt eller segment × region,
  tas inte med, så att underuppdelningar inte blandas in.
- Begrepp i prioritetsordning: `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`,
  `SalesRevenueNet`. Före ASC 606 (2018) användes `SalesRevenueNet`.
- Varje fakta blir en `sec.Fact` med `filed` = inlämningens datum. Därefter gäller `sec.vintages` utan
  ändringar: tremånadersfakta används direkt, YTD-värden differensieras, Q4 = helår − 9M, en version per
  inlämningsdatum och konsekvent bas vid omräkningar. Tremånadersfakta i 10-K ignoreras, som i `sec.facts`.
  Segmentintäkter rapporteras som tremånadersvärden i 10-Q för alla fem bolagen, och Amazon, Alphabet
  och Nvidia har dessutom YTD-värden. Q4 kommer alltid från helår − 9M.
- Kalendermappning: kvartalet som innehåller räkenskapskvartalets mittpunkt (`sec.calendar_quarter`).
  Nvidia ligger ungefär en månad efter kalenderkvartalet. **Oracle** (räkenskapsår till maj, kvartal som
  slutar nov/feb/maj/aug) ligger ungefär en månad före: sep–nov räknas som Q4 och lämnas in cirka den
  10 december, alltså före kalenderkvartalets slut. Oracle-serierna har därför `lag_days = -31`, och
  läckagekontrollen `known_from_after_period_end` tillåter då värden som är kända upp till 31 dagar före
  kvartalets slut. Värdet är verkligen känt när det lämnas in, så det är ingen läckage, men etiketten
  "Q4" betyder sep–nov.

## Definitionsbrott (läckagekritiskt)

En omsegmentering behåller ofta medlemsnamnet men räknar om historiken. Om den skarvas in som en
revidering skrivs den gamla definitionens historik över med den nya, och serien blandar två
definitioner. Regeln är därför:

- `definition_breaks`: en inlämning som ändrar ett tidigare inlämnat värde för samma period (start, slut)
  med mer än **2 %** startar en ny regim. Efter ett brott jämförs bara värden som lämnats in från brottet
  och framåt. En omräkning rullas nämligen ut över flera inlämningar: varje 10-Q räknar om sitt
  jämförelsekvartal och 10-K:n räknar om de tidigare åren. Det är samma brott och inte nya brott.
- Varje regim blir **en egen serie** (`regimes`), aldrig en skarv. Den nya definitionens historik kommer
  från jämförelsetalen och dateras med de inlämningar som räknade om den. Mindre ändringar (under 2 %)
  är vanliga versioner.
- Brotten deklareras per rad i `sec_segments.LINES`. Om de upptäckta brotten skiljer sig från de
  deklarerade misslyckas hämtningen med `DefinitionBreakError`. En ny omsegmentering kan alltså inte
  skarvas in tyst. Den granskas, deklareras och får en egen nyckel.
- Ett medlemsnamn som byts utan omräkning (Nvidia `DatacenterMember` → `DataCenterMember`, Oracle
  `CloudServicesMember` → `CloudRevenuesMember`, Alphabet `GoogleCloudSegmentMember`/`GoogleCloudMember`,
  Amazon segment- och produktaxeln) anges som alternativ. Brottskontrollen går över alternativen, så en
  namnändring med nya värden skulle synas som ett brott. Inget sådant hittades.

Upptäckta brott (hämtning 2026-11-23):

| Rad | Brott (inlämning) | Storlek | Tolkning |
|---|---|---|---|
| Microsoft Intelligent Cloud | 2017-10-26 (10-Q Q1 FY2018) | −4,5 % på jämförelsekvartalet | omsegmentering FY2018 |
| Microsoft Intelligent Cloud | 2024-10-30 (10-Q Q1 FY2025) | −17 % | omsegmentering FY2025 |
| Microsoft Server products and cloud services | 2024-10-30 | −18 till −19 % | samma omräkning FY2025 |

Microsoft bytte segment igen från FY2027 (10-Q 2026-10-28): Intelligent Cloud och Server products and
cloud services finns inte längre, och i stället finns segmenten Agents and Infra och Devices and
Consumer samt Azure som egen produktrad. Det är nya medlemmar och därför nya nycklar. AWS, Google Cloud,
Microsoft Cloud, Nvidia Data Center och Oracle har inga brott över 2 %.

## Serier (alla kvartal, MUSD, release-daterade, G4)

| Nyckel | Rad (axel = medlem) | Från | Till | Kvartal | Reviderade kvartal |
|---|---|---|---|---|---|
| `rev_aws` | segment `AmazonWebServicesSegmentMember` (produktaxeln `AmazonWebServicesMember` som reserv, används inte i nuvarande data) | 2014Q1 | 2026Q3 | 51 | 0 |
| `rev_google_cloud` | segment `GoogleCloudMember` / `GoogleCloudSegmentMember` | 2020Q1 | 2026Q3 | 27 | 0 |
| `rev_msft_intelligent_cloud_fy16` | segment `IntelligentCloudMember`, definition FY2016–17 | 2014Q3 | 2017Q2 | 12 | 0 |
| `rev_msft_intelligent_cloud_fy18` | samma, definition FY2018–24 | 2016Q3 | 2024Q2 | 32 | 4 |
| `rev_msft_intelligent_cloud_fy25` | samma, definition FY2025–26 | 2023Q3 | 2026Q2 | 12 | 0 |
| `rev_msft_agents_infra` | segment `AgentsAndInfraMember` (FY2027–) | 2026Q3 | 2026Q3 | 1 | 0 |
| `rev_msft_cloud` | `ProductsOrServicesSecondaryCategorizationAxis = MicrosoftCloudMember` | 2020Q3 | 2026Q3 | 25 | 5 |
| `rev_msft_server_cloud_fy18` | produkt `ServerProductsAndCloudServicesMember` (äldre namn `ServerProductsAndToolsMember`), före FY2025 | 2016Q3 | 2024Q2 | 32 | 4 |
| `rev_msft_server_cloud_fy25` | samma, definition FY2025–26 | 2023Q3 | 2026Q2 | 12 | 0 |
| `rev_msft_azure` | produkt `AzureMember` (FY2027–) | 2026Q3 | 2026Q3 | 1 | 0 |
| `rev_nvda_datacenter` | produkt `DataCenterMember` / `DatacenterMember` (Nvidia taggar marknadsplattform, inte segment) | 2017Q2 | 2026Q2 | 37 | 0 |
| `rev_orcl_cloud` | produkt `CloudRevenuesMember` (FY2026–) / `CloudServicesMember` (FY2023–25): IaaS + SaaS | 2021Q3 | 2026Q3 | 21 | 0 |
| `rev_orcl_oci` | produkt `CloudInfrastructureMember` (FY2026–, med jämförelsetal för FY2025) | 2024Q3 | 2026Q3 | 9 | 0 |

285 rader och 13 revideringar. Revideringarna är små och kommer från jämförelsetalen i FY2023:s 10-Q
och 10-K: Intelligent Cloud FY2018-definitionen 2021Q3–2022Q2 −0,3 till −0,5 %, Server products and
cloud services samma kvartal +1 till +13 MUSD, och Microsoft Cloud +100 MUSD i fem kvartal (rapporteras
avrundat till 0,1 mdr USD).

`rev_msft_agents_infra` och `rev_msft_azure` har bara ett kvartal. Jämförelsekvartalet 2025Q3 finns,
men det ligger före en lucka och tas bort av `contiguous_tail` (datatestet `no_gaps`). Serierna växer
när 10-Q:erna för FY2027 och 10-K:n med omräknat FY2026 kommer.

Inte med (taggat, men utanför G4:s fråga eller med fel definition): Microsofts `CommercialCloudMember`
(2014–2021, smalare än Microsoft Cloud och därför en annan definition), Oracles
`CloudServicesAndLicenseSupportMember` (mest licenssupport), Nvidias underuppdelningar av Data Center
(`ComputeMember`, `HyperscaleMember`, `AICloudsIndustrialEnterpriseMember`, korta) och Alphabets
intäkter före 2020 (Google Cloud taggades först från 10-K för 2020).

## Kontroll

**Summakontroll** (senaste version, 6 senaste kvartalen): Amazons tre segment = `rev_amzn` exakt.
Microsofts tre segment FY2025-definition och de två FY2027-segmenten = `rev_msft` exakt. Alphabets tre
segment avviker från `rev_googl` med −194 till +207 MUSD. Det är säkringsresultatet, som redovisas
utanför segmenten.

**Mot bolagens rapporter** (ur minnet, MUSD, senaste version):

| Serie | Kvartal | Här | Rapporterat | |
|---|---|---|---|---|
| `rev_aws` | 2024Q4 / 2025Q1 / 2025Q2 / 2025Q3 | 28 786 / 29 267 / 30 873 / 33 006 | 28,8 / 29,3 / 30,9 / 33,0 mdr | stämmer |
| `rev_aws` | 2014Q1 | 1 050 | ca 1,05 mdr | stämmer |
| `rev_google_cloud` | 2024Q4 / 2025Q1 / 2025Q2 / 2025Q3 | 11 955 / 12 260 / 13 624 / 15 157 | 12,0 / 12,3 / 13,6 / 15,2 mdr | stämmer |
| `rev_msft_intelligent_cloud_fy18` | FY24 Q1–Q4 | 24 259 / 25 880 / 26 708 / 28 515 | 24,3 / 25,9 / 26,7 / 28,5 mdr | stämmer |
| `rev_msft_intelligent_cloud_fy25` | FY25 Q1–Q4, FY26 Q1 | 24 092 / 25 544 / 26 751 / 29 878 / 30 897 | 24,1 / 25,5 / 26,8 / 29,9 / 30,9 mdr | stämmer |
| `rev_msft_cloud` | FY25 Q2–Q4, FY26 Q1 | 40 900 / 42 400 / 46 700 / 49 100 | 40,9 / 42,4 / 46,7 / 49,1 mdr | stämmer |
| `rev_nvda_datacenter` | Q2 FY18, Q3 FY25–Q3 FY26 | 416; 30 771 / 35 580 / 39 112 / 41 096 / 51 215 | 0,42; 30,8 / 35,6 / 39,1 / 41,1 / 51,2 mdr | stämmer |
| `rev_orcl_cloud` | Q2 FY25–Q2 FY26 | 5 937 / 6 210 / 6 737 / 7 186 / 7 977 | 5,9 / 6,2 / 6,7 / 7,2 / 8,0 mdr | stämmer |
| `rev_orcl_oci` | Q1 FY25, Q4 FY25, Q1 FY26 | 2 154 / 2 994 / 3 347 | 2,2 / 3,0 / 3,3 mdr | stämmer |

Inga avvikelser hittades. Kvartal från 2025Q4 och framåt (och FY2027-raderna) kunde inte kontrolleras ur
minnet, men summakontrollen håller för dem.

## Kända problem

- Nvidias kvartal aug–okt 2026 och Oracles sep–nov 2026 var inte inlämnade vid hämtningen.
- Microsofts segmentserier tar slut 2026Q2 och efterföljarna har ett kvartal. För en längre serie
  med samma definition är `rev_msft_cloud` (oförändrad genom båda omsegmenteringarna, 2020Q3–) den enda
  Microsoftserien utan brott.
- Första versionen för kvartal som bara finns som jämförelsetal (t.ex. AWS 2014, de omräknade
  Microsoftdefinitionerna) har ett `known_from` som ligger cirka ett år efter perioden. Det är konservativt.
- Google Cloud 2020Q3 och 2020Q4 finns i Google Cloud-medlemmen först som jämförelsetal i 10-Q för
  2021Q3 (Q4 = helår − 9M), och deras första version dateras därför 2021-10-27.
- Tröskeln på 2 % är ett val. En verklig omsegmentering som flyttar under 2 % syns som en revidering,
  och en omräkning över 2 % av andra skäl blir ett brott som måste deklareras.
