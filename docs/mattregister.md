# Måttregister (förregistrering)

Låst 2026-11-23, innan någon serie analyserats. Fas 1 kontrollerade bara åtkomst, historik och villkor, och fas 2
hämtar data utan att beräkna takter. Ändringar läggs till längst ned med datum och motivering. Ingenting
här skrivs om.

## 1. Mått per serie

Alla mått beräknas **med `as_of()` på beräkningsdagen**: bara data med `known_from` ≤ dagen, och statistik
över historiken (percentiler, standardavvikelser) beräknas med expanderande fönster fram till dagen, aldrig över
hela perioden.

| Mått | Definition |
|---|---|
| Transform | Logaritm för positiva storheter (capex, intäkter, volymer, priser). Andelar (t.ex. % företag som använder AI) används i nivå, i procentenheter |
| Månadsaggregering | Dags- och veckoserier aggregeras till månad innan takt beräknas: medel för priser och andelar, summa för flöden. Bara observationer kända vid månadens slut används |
| **Takt** | Månad och kvartal: årsförändring i log ×100 (≈ %). Andelar: förändring över 12 månader i procentenheter. Årsdata: förändring från föregående år |
| **Förändring i takt** | Takt nu minus takt 6 månader tidigare (månad), 2 kvartal tidigare (kvartal) eller 1 år tidigare (år) |
| Standardisering | Percentil av takt och förändring i takt mot seriens egen historik fram till beräkningsdagen. Kräver minst 24 månader, 8 kvartal eller 5 år, annars visas måttet utan percentil |
| **Överraskning** | Utfall minus nowcast (N1–N4) i log ×100. Där ingen nowcast finns: utfall minus naiv baslinje B1 (avsnitt 3) |

G1 (förmåga) och G2 (kostnad) mäts med **fördubblings- och halveringstid**: lutningen i en log-linjär regression
över de senaste 24 månaderna av frontvärden (bästa kända värde vid varje datum), omräknad till månader.
Förändring i takt är då fördubblingstiden nu jämfört med 12 månader tidigare. Den exakta serielistan för
G1, G2 och G9 läggs till här när fas 1 S1 är klar, före all analys.

## 2. Gren: diffusionsindex och tillstånd

- **Serier som räknas:** kärnserierna per gren (avsnitt 4) som har ett giltigt mått för förändring i takt på beräkningsdagen.
- **Riktning per serie:** +1 om förändringen i takt > 0,25 × seriens expanderande standardavvikelse för förändring i takt,
  −1 om den < −0,25 × samma standardavvikelse, annars 0 (neutral).
- **Diffusionsindex** = (antal +1 + 0,5 × antal 0) / antal serier, mellan 0 och 1. Ett värde på 0,5 betyder balans.
- **Tillstånd:** *accelererar* om index ≥ 0,67, *bromsar in* om index ≤ 0,33, annars *stabil*. Med färre än 3 serier
  visas indexet men inget tillstånd ("för få serier").
- Strukturbrott i takt (fas 5): metoden registreras här innan den körs första gången.

## 3. Nowcast N1: capex för de fyra största hyperscalers

| Del | Val |
|---|---|
| Mål | `capex_hyp4`, kalenderkvartalets summa för MSFT, GOOGL, AMZN och META, **första versionen** (när alla fyra har lämnat in) |
| Fel | log(prognos) − log(utfall) ×100. Huvudmått MAE, och bias redovisas |
| Prognosdag | Kvartalets slut + 20 dagar, före den första rapporten. Informationsmängd `as_of(prognosdag)` |
| B0 | Slumpvandring: förra kvartalets nivå |
| B1 | Drift: förra kvartalet × exp(medel av de 4 senaste kvartalens log-tillväxt) |
| V1 | B1 + bridge: expanderande OLS av log-tillväxt kvartal för kvartal i capex på motsvarande tillväxt i de månader av kvartalet som är kända på prognosdagen, från `us_imports_tw` (datorer/halvledare), `us_ip_semis` och `us_constr_datacenter` |
| V2 | Samma som V1 men med ridge och λ valt med tidsserie-CV inne i varje träningsfönster |
| Utvärdering | Rolling origin, expanderande fönster. Period: från det första kvartalet med minst 20 kvartal träningsdata och alla indikatorer, till senaste kvartalet. Delperiod från 2023Q1 redovisas separat (regimskifte) |
| Test | Diebold–Mariano mot den bästa av B0 och B1. Holm över V1 och V2 |
| Befordran | Holm-p < 0,10 **och** lägre MAE i både hela perioden och delperioden från 2023. Annars blir B1 huvudmodell |
| Senare baslinje | Bolagens guidance (fas 4) läggs till som B2 när extraktionen är granskad |

Ärlig not: antalet kvartal är litet, så bara stora skillnader går att upptäcka. MDE redovisas.

## 4. Nowcast N2: TSMC:s månadsintäkt

| Del | Val |
|---|---|
| Mål | `tsmc_revenue_m`, NT$, första publicerade värdet |
| Fel | log(prognos) − log(utfall) ×100. Huvudmått MAE |
| Prognosdag | Dag 8 i månaden efter, före publiceringen runt den 10:e |
| B0 | Slumpvandring: förra månaden |
| B1 | Säsongsnaiv tillväxt: y(m−12) × y(m−1) / y(m−13) |
| V1 | B1 + ridge på de indikatorer som är kända på prognosdagen ur listan `kr_semi_exports_20d`, `kr_semi_exports_m`, `tw_exports_m`, `us_imports_tw`, `us_ip_semis` (blockerade eller saknade serier faller bort och listas i resultatet) |
| Utvärdering | Rolling origin, expanderande fönster, från 2012-01 (eller första månaden med 60 månaders träning), delperiod från 2023-01 |
| Test och befordran | Som N1: DM mot bästa baslinjen, Holm (en variant), befordran kräver Holm-p < 0,10 och lägre MAE i båda perioderna |

## 5. Kärnserier per gren

Fylls i när fas 2 har levererat serierna. Valet görs efter tillgång, historik och ärlig `known_from`,
inte efter vad serierna visar. Varje tillägg dateras.

**2026-11-23 (G2–G8), valt efter tillgång, historik och `known_from`. Inga takter har beräknats:**

| Gren | Kärnserier | Anmärkning |
|---|---|---|
| G2 | `g2_price_at_capability_gpqa` | ECI-varianten är bakåtfylld och räknas inte förrän det finns 24 månader egna ögonblicksbilder. Med 1 serie visas index men inget tillstånd |
| G3 | `btos_ai_use_<aktiv regim>`, `eu_ai_ent_eu27`, `eu_ai_ent_se` | BTOS-takt beräknas bara inom en regim. Med för kort regim finns inget mått. Årsserierna har kort historik |
| G4 | `rev_msft`, `rev_googl`, `rev_amzn`, `rev_meta`, `rev_nvda` | Totala intäkter, inte AI-specifika. Segmentintäkter ersätter eller kompletterar när de finns (registreras då) |
| G5 | `capex_hyp4`, `us_constr_datacenter`, `us_pfi_info_proc_eq_sw`, `capex_ocf_hyp4` | `capex_ocf_hyp4` = `capex_hyp4` / `ocf_hyp4` för samma version (`known_from` = den senaste av de två). Behandlas som andel: takt = förändring i procentenheter över 4 kvartal |
| G6 | `tsmc_revenue_m`, `us_ip_semis_m`, `us_ip_computers_m`, `us_imports_tw_m`, `us_imports_kr_m` | |
| G7 | `us_elec_sales_com_{va,tx,ga,az,or,oh}_m` | Ej säsongsjusterade. Årstakten hanterar säsongen |
| G8 | `ai_postings_share_{us,gb,de,fr,ca,au,ie,it,nl}_d` | Dagsdata aggregeras till månadsmedel (avsnitt 1). Andelar: takt i procentenheter |

G1 och G9 läggs till när fas 2 I5 är mergad.

## Ändringar

### 2026-11-23 – G1, G2, G9 preciseras (efter fas 1 S1, före analys)

Fas 1 visade att flera G1-källor är bakåtfyllda eller omskattade (Epoch-modelldatabasen, ECI), att METR inte
längre uppdateras och att Artificial Analysis och OpenRouters tokenvolymer är blockerade av villkor. Därför gäller:

- **Benchmarks (G1):** Epochs egna körningar med tidsstämpel (`Started at` = `known_from`). Frontvärde = bästa
  resultatet känt vid datumet. Andelar mellan 0 och 1 transformeras med logit, så takt = 12-månadersförändring i
  logit(frontvärde) och fördubblingstid används inte. Urval: de 3 benchmarks med flest Epoch-körda modeller bland
  dem vars frontvärde var < 0,80 den 2026-11-23. När ett frontvärde passerar 0,90 ersätts benchmarken av nästa i
  samma rangordning (bland dem med frontvärde < 0,70). Urvalet görs på täckning, inte på utveckling.
- **ECI och Epoch-modelldatabasen (G1, G9):** bara våra egna veckovisa ögonblicksbilder från första hämtningen
  får `known_from`. Bakåtfylld historik får `source="backfill"`, används som beskrivning och ingår inte i
  diffusionsindex förrän det finns 24 månader egna ögonblicksbilder.
- **Träningsberäkning vid fronten (G1):** fördubblingstid enligt avsnitt 1. Bakåtfylld, och flaggas.
- **Pris vid fast förmåga (G2):** lägsta pris per miljon tokens (blandat 3:1 input/output) bland modeller vars
  förmåga är minst tröskeln. Tröskeln är frontens ECI-värde vid 2025-01-01, låst när serien byggs första gången
  och redovisad här. Takt = halveringstid enligt avsnitt 1.
- **METR och Epochs frysta prisdata:** används som referens för att kontrollera våra egna mått, inte som kärnserier.

### 2026-11-23 – G2: tröskel för pris vid fast förmåga låst (fas 2, spår I6, före analys)

Låst vid första bygget av serien, innan någon takt eller halveringstid beräknats.

- **Tröskel (ECI): 141,16.** Högsta ECI bland Epochs modeller med releasedatum ≤ 2025-01-01, i
  `eci_scores.csv` hämtad 2026-11-23 (o1, release 2024-12-17). Konstanten `ECI_THRESHOLD` i
  `src/ai_tracker/series/price_capability.py`. Räknas aldrig om, även när Epoch skattar om ECI.
- **Serie `g2_price_at_capability`** (månad, registrerat huvudmått): lägsta blandade pris
  (3 input : 1 output, USD per miljon tokens) bland modeller med ECI ≥ 141,16, enligt LiteLLM:s prisfil som den
  såg ut vid månadens slut (senaste urvalda commit på `main` med datum ≤ månadsslut). Bara förstapartspriser
  (utvecklarens eget API, regeln i `src/ai_tracker/sources/model_map.py`). En modell räknas från sitt
  releasedatum hos Epoch. ECI-värdena är dagens skattningar, så hela historiken är bakåtfylld
  (`source="backfill"`) och omfattas av regeln ovan om ECI: ingen del av diffusionsindex förrän det finns 24
  månader egna ögonblicksbilder.
- **Variant `g2_price_at_capability_gpqa`, tröskel 0,767676.** Samma mått med förmåga från Epochs egna
  körningar av GPQA Diamond: känd från `Started at` + 7 dagar, bästa körningen per modell (över
  resonemangsnivåer). Tröskeln är bästa körningen bland modeller släppta ≤ 2025-01-01 (o1-2024-12-17,
  hög resonemangsnivå, 152/198 = 0,7676768, avrundat nedåt till 6 decimaler). GPQA Diamond valdes för att den
  har flest Epoch-körda modeller (342 körningar), inte efter utfall. Båda varianterna redovisas. Ingen av dem
  väljs efter hur serierna ser ut. Huvudmåttet är fortsatt ECI-varianten.
- **Prisregler, fastställda vid bygget efter kontroll av enskilda poster (inte av seriens förlopp):**
  utpriset är resonemangspriset när LiteLLM anger ett separat sådant (Gemini 2.5 Flash preview: 0,60 mot
  3,50 USD), eftersom Epoch mäter förmågan med resonemang påslaget. DeepSeeks eget API räknas under båda
  LiteLLM:s namnformer (`deepseek-chat` och `deepseek/deepseek-chat`).
- Takt enligt avsnitt 1 (halveringstid). Inte beräknad i spår I6.

### 2026-11-23 – N1: kortare minsta träningsfönster och en sekundär utvärdering (efter fas 2 I1, före analys)

Fas 2 visade att `capex_hyp4` börjar först 2017Q3. Amazons äldre capex-taggar är netto efter incitament, och att
skarva ihop dem skulle ge ett definitionsbrott. Med kravet på 20 kvartals träning skulle utvärderingen bara få
cirka 16 kvartal. Ingen modell har körts, och ändringen görs bara på grund av seriens längd.

- Minsta träningsfönster för N1 sänks från 20 till **12 kvartal**. V1 och V2 kräver dessutom att alla tre
  indikatorerna finns för kvartalet.
- **Sekundär utvärdering N1b:** samma modeller och baslinjer per bolag (`capex_msft`, `capex_googl`, `capex_amzn`,
  `capex_meta`), utvärderade poolat över bolag och kvartal, med samma regel om 12 kvartals träning per bolag. N1b redovisas
  och ger mer statistisk styrka, men befordran avgörs fortfarande av N1. Diebold–Mariano-testet poolas med
  bolagsvisa förlustdifferenser, och Newey–West-fördröjningen bestäms av antalet kvartal, inte antalet observationer.

### 2026-11-23 – N2: prognosdagen flyttas från dag 8 till dag 5 (efter fas 2 I2, före analys)

Källan för `tsmc_revenue_m` är TSMC:s 6-K till SEC, och `known_from` är inlämningsdatumet. Av 289 månadsrapporter
lämnades 61 (21 %) in dag 8 eller tidigare. Den tidigaste var dag 6. Med dag 8 skulle var femte prognos göras när
utfallet redan var känt. Prognosdagen blir därför **dag 5** i månaden efter. Ändringen bygger bara på
publiceringsdatum, och ingen modell har körts.

### 2026-11-23 – N1 och N2: indikatorer enligt vad fas 2 levererade (före analys)

- `us_imports_tw` blir `us_imports_tw_m`: **total** import från Taiwan (Census FT-900). HS-nivå (8471/8473/8542)
  kräver en nyckel till api.census.gov och finns inte än.
- `us_ip_semis` (`us_ip_semis_m`) finns bara via ALFRED. FRED:s villkor begränsar användning i samband med
  maskininlärning, och primärkällan (federalreserve.gov) är blockerad. Serien **ingår inte** i modellerna i fas 3.
  Den läggs till först efter ett beslut, och då som en ny registrerad variant, inte i efterhand i V1 eller V2.
- N1 V1/V2 använder alltså `us_imports_tw_m` och `us_constr_datacenter` (säsongsjusterad). N2 V1 använder
  `us_imports_tw_m` (Korea- och Taiwanserierna är blockerade).
- `us_imports_tw_m` och `us_constr_datacenter` är bakåtfyllda: bara den senaste versionen finns, så revideringar
  läcker in i backtesten. Det redovisas med resultatet.

### 2026-11-23 – B2 (bolagens guidance) läggs till för N1 och N2 (före extraktion och analys)

Ingen guidance har hämtats eller jämförts med utfall när detta skrivs.

**N2, B2 (TSMC):**
- TSMC ger i sin kvartalsrapport (6-K) ett intervall för kvartalets intäkt i USD och ett antagande om växelkursen
  USD/NT$. `known_from` = inlämningsdatum för 6-K:n.
- Kvartalets intäkt i NT$ = intervallets mittpunkt × den antagna växelkursen.
- För månad m i kvartalet: B2 = (kvartalets intäkt i NT$ − summan av kvartalets kända månader) × B1-andelen.
  B1-andelen = B1:s prognos för m delat med summan av B1:s prognoser för kvartalets okända månader, där m ingår.
- Om ingen guidance för kvartalet är känd på prognosdagen används B1.
- Utvärdering, test och befordran sker som för N2 i övrigt. B2 behandlas som en variant, och Holm-justeringen görs
  över V1 och B2.

**N1, B2 (capex):**
- Definitionen låses i en ny post här när extraktionen (fas 4, spår E1) har dokumenterat hur varje bolags guidance
  är definierad (med eller utan finansiell leasing, kalender- eller räkenskapsår, kvartal eller helår).
- Det görs innan något B2-värde jämförs med utfall.

### 2026-11-23 – Fas 5: tre tolkningar fastställs (före första skarpa ögonblicksbilden)

Fas 5 (spår F5) lämnade tre tolkningsfrågor. De avgörs här efter att den rekonstruerade historiken körts en gång,
och därför bara med motiveringar som inte beror på vad historiken visade. Den första skarpa ögonblicksbilden är
2026-11-30.

1. **Månadsaggregering:** varje månad aggregeras från en och samma version, `as_of(beräkningsdagen)`, och seriens
   sista månad stryks eftersom den kan vara ofullständig. Det följer avsnitt 1 ("allt via `as_of` på beräkningsdagen")
   och undviker att blanda versioner med olika metod eller basår. Båda tolkningarna är fria från läckage.
2. **Tecken för fördubblings- och halveringstid:** kortare tid räknas som acceleration (+1). Det är regelns
   avsikt, och den bokstavliga läsningen skulle vända riktningen.
3. **Inaktuella serier räknas inte:** en kärnserie vars senaste kända period är äldre än aktualitetsgränsen
   (`warehouse.max_age_days`, samma regel som veckotestet) räknas inte i diffusionsindex och listas med orsak.
   En härledd serie är lika aktuell som sin minst aktuella komponent.

Övriga tolkningar i `docs/resultat/tillstand.md` (punkt 4–10) godtas som de står.

### 2026-11-23 – G4: segmentserier finns (spår T2, före analys)

Segmentserier finns: `rev_aws` (2014Q1), `rev_google_cloud` (2020Q1), `rev_msft_intelligent_cloud_fy16`
(2014Q3–2017Q2), `rev_msft_intelligent_cloud_fy18` (2016Q3–2024Q2), `rev_msft_intelligent_cloud_fy25`
(2023Q3–2026Q2), `rev_msft_agents_infra` (2026Q3), `rev_msft_cloud` (2020Q3), `rev_msft_server_cloud_fy18`
(2016Q3–2024Q2), `rev_msft_server_cloud_fy25` (2023Q3–2026Q2), `rev_msft_azure` (2026Q3), `rev_nvda_datacenter`
(2017Q2), `rev_orcl_cloud` (2021Q3), `rev_orcl_oci` (2024Q3). Microsofts omsegmenteringar (FY2018, FY2025,
FY2027) är egna serier, inte skarvar. Källa och kontroller: `docs/kallor/sec_segment.md`. Ingen takt beräknad.

### 2026-11-23 – G4: segmentintäkter ersätter totala intäkter som kärnserier

Avsnitt 5 angav att segmentintäkter ersätter totala intäkter när de finns. Urvalet görs efter
definitionsstabilitet (inga definitionsbrott) och relevans för AI och moln, inte efter vad serierna visar:

| Gren | Kärnserier | Anmärkning |
|---|---|---|
| G4 | `rev_aws`, `rev_google_cloud`, `rev_msft_cloud`, `rev_nvda_datacenter`, `rev_orcl_cloud` | Inga definitionsbrott. Microsofts segmentserier (Intelligent Cloud, Server products) har brott 2017, 2024 och 2026 och används inte. Oracles kvartal märks en månad tidigt (räkenskapsår), och årstakten påverkas inte. Totala intäkter (`rev_*`) finns kvar i katalogen som beskrivning |


### 2026-11-23 – Benchmarkurvalet tillämpat (fas 2, spår I5, före analys)

Regeln ovan körd som kod (`ai_tracker.sources.epoch_hub.select_benchmarks`) på `benchmark_data.zip` hämtad
2026-11-23. Tillämpning: Epoch-körd benchmark = fil i ZIP:en utan `_external` som har `Started at`. Antal modeller =
olika `Model version` med poäng och `Started at` t.o.m. 2026-11-23. Frontvärde = högsta `Best score (across
scorers)` bland samma körningar. Lika antal bryts i bokstavsordning efter filnamn. "Passerar 0,90" tolkas som
> 0,90, och efterträdarens rangordning räknas på ersättningsdagen.

| Rang | Benchmark (fil) | Modeller | Frontvärde | Senaste körning | `superseded_by` |
|---|---|---|---|---|---|
| 1 | FrontierMath-2025-02-28-Private (`frontiermath`) | 100 | 0,524 | 2026-06-08 | FrontierMath-Tiers-1-3-v2-Private |
| 2 | FrontierMath-Tier-4-2025-07-01-Private (`frontiermath_tier_4`) | 71 | 0,479 | 2026-06-08 | FrontierMath-Tier-4-v2-Private |
| 3 | FrontierMath-Erdos (`frontiermath_erdos`) | 17 | 0,103 | 2026-11-19 | – |

Nästa i rangordningen (efterträdare, frontvärde < 0,70): `spireclimb` (13 modeller, 0,413),
`spireclimb_sts1_a20_heart` (13, 0,333), `spireclimb_sts2_a10` (13, 0,493). Uteslutna eftersom frontvärdet var
≥ 0,80: `gpqa_diamond` (341, 0,968), `otis_mock_aime_2024_2025` (319, 1,0), `chess_puzzles` (168, 0,830),
`mystery_game_puzzles` (150, 0,950), `frontiermath_tiers_1_3_v2` (128, 0,951), `math_level_5` (108, 0,981),
`simpleqa_verified` (106, 0,940), `frontiermath_tier_4_v2` (84, 1,0), `mirrorcode` (48, 0,978),
`furniture_assembly` (43, 0,900), `ebr_bench` (36, 0,981), `swe_bench_verified` (33, 0,835).

Serier: `g1_epoch_bench_frontier_<fil>` (frontvärde per månad) och `g1_epoch_bench_runs_<fil>` (antal körningar
per månad) för de tre. Övriga G1/G2/G9-serier från spåret: `g1_epoch_eci_frontier` (vecka),
`g1_epoch_train_compute_frontier`, `g9_epoch_notable_models`, `g9_epoch_open_weights_share` (kvartal),
`g2_epoch_hw_price_performance` (år), `g1_metr_horizon_p50_frontier` (referens), `g9_arxiv_ai_ml_submissions`
med delserierna `g9_arxiv_cs_ai`, `g9_arxiv_cs_lg`, `g9_arxiv_cs_cl` och `g9_arxiv_ai_ml_listed`. Definitioner och
`known_from` i [`kallor/epoch_arxiv.md`](kallor/epoch_arxiv.md).

**Observation, ingen regeländring.** Regeln valde två benchmarks som Epoch har ersatt (`superseded_by`) och inte
kört sedan 2026-06-08. Deras frontvärden ligger därför still av mätskäl, inte av förmågeskäl, och efterträdarna har
redan passerat 0,90 (0,951 och 1,0). Successorregeln slår inte till, eftersom frontvärdena ligger under 0,90.
Det kräver ett beslut av Johannes innan serierna används i diffusionsindex. Förslag: en benchmark med
`superseded_by` eller utan Epoch-körning på 90 dagar räknas som avslutad och ersätts enligt successorregeln. Det
är inte infört, och serierna är byggda enligt regeln som den står.

### 2026-11-23 – G1 och G9: avslutade benchmarks, en per familj, försiktigare datum och kärnserier (före analys)

Fas 2 I5 visade att urvalsregeln valde två benchmarks som Epoch har ersatt (`superseded_by`) och inte kört sedan
2026-06-08. Deras frontvärden står därför still av mätskäl. Ändringarna nedan bygger bara på metadata
(`superseded_by`, senaste körning, antal modeller, benchmarkens namn). Inga frontvärden över tid har analyserats.

- **Avslutad benchmark:** en benchmark med `superseded_by` eller utan Epoch-körning på 90 dagar räknas som avslutad
  och ersätts enligt successorregeln, på samma sätt som när frontvärdet passerar 0,90.
- **En per familj:** högst en benchmark per familj (samma namnprefix före första versions- eller variantled, t.ex.
  `spireclimb_*`). Inom familjen väljs den med flest Epoch-körda modeller, och vid lika antal basvarianten.
- **Datum:** benchmarkvärden får `known_from` = `Started at` + 30 dagar, eftersom körningen startar före publicering.
  Från första hämtningen gäller i stället `first_seen` om den är senare. Fördröjningen mäts och redovisas efter 6 månader.
- Spår F6 kör urvalsregeln med ändringarna som kod och lägger till resultatet (valda benchmarks och antal) som en
  daterad post här. Kärnserierna för G1 är de valda benchmarkernas frontserier.

| Gren | Kärnserier | Anmärkning |
|---|---|---|
| G1 | `g1_epoch_bench_frontier_<valda>`, `g1_epoch_train_compute_frontier`, `g1_epoch_eci_frontier` | `<valda>` = resultatet av urvalsregeln. ECI är spärrad tills det finns 24 månader egna ögonblicksbilder (bakåtfylld). Träningsberäkningen är bakåtfylld och flaggas |
| G9 | `g9_arxiv_cs_ai`, `g9_arxiv_cs_lg`, `g9_arxiv_cs_cl`, `g9_epoch_open_weights_share`, `g9_epoch_notable_models` | arXiv per primärkategori. Epoch-databasens serier är spärrade tills det finns 24 månader egna ögonblicksbilder |

### 2026-11-23 – B2: TSMC före 2017Q3 och definitionen för N1 (före utvärdering)

Guidance har extraherats (fas 4 E1) men inte jämförts med utfall.

- **N2 B2:** fram till 2017Q2 guidade TSMC i NT$. Då används mittpunkten i NT$ direkt, och växelkursen behövs inte.
  Från 2017Q3 gäller mittpunkten i US$ × den antagna växelkursen enligt den tidigare posten.
- **N1 B2**, per bolag och sedan summerat till `capex_hyp4`:
  - **Meta:** helårsintervallets mittpunkt avser capex inklusive amortering på finansiell leasing. Det motsvarar
    `capex_meta` + `fin_lease_meta`. Implicit helår för `capex_meta` = mittpunkten − (kända kvartal av
    `fin_lease_meta` + B1-prognos för årets okända kvartal av `fin_lease_meta`).
  - **Alphabet:** helårsguidance i pressmeddelandet har samma definition som `capex_googl` och används direkt.
  - **Kvartal:** (implicit helår − årets kända kvartal) × B1-andelen. Andelen räknas som för N2 B2: B1:s prognos för
    kvartalet delat med summan av B1:s prognoser för årets okända kvartal.
  - **Amazon och Microsoft:** B1, eftersom guidancen har en annan definition (Amazon netto efter incitament,
    Microsoft inklusive finansiell leasing vid tecknande) som inte går att översätta till våra serier.
  - **Saknas guidance** som är känd på prognosdagen: B1 för det bolaget.
  - Riktningsangivelser (upp/ner) används inte i B2.
- **Utvärdering:** B2 är en variant. Holm-justeringen görs över alla varianter för målet (N1: V1, V2 och B2; N2: V1 och B2).
  Befordran sker enligt samma regel som tidigare.
- **Krav före befordran:** en oberoende granskning av extraktionen ska godkänna de värden som B2 använder.
  Annars befordras B2 inte, oavsett resultat.

### 2026-11-23 – G1: urvalsregeln tillämpad (spår F6, före analys)

Regeln i föregående poster körd som kod (`ai_tracker.sources.epoch_hub.selection_table`) på `benchmark_data.zip`
hämtad 2026-11-23, med urvalsdag 2026-11-23. Inga frontvärden över tid har tittats på. Tillämpning:

- **Avslutad:** `superseded_by` satt i `benchmark_metadata.csv`, eller ingen Epoch-körning startad från och med
  2026-08-25 (90 dagar före urvalsdagen).
- **Familj** (`epoch_hub.family`): första ledet i filnamnet före `_` (`frontiermath_tier_4_v2` → `frontiermath`,
  `spireclimb_sts2_a10` → `spireclimb`). Fel åt bara ett håll: två olika benchmarks med samma första ord hamnar i
  samma familj, och en familj delas aldrig. På dagens 18 Epoch-körda benchmarks har bara `frontiermath` (5) och
  `spireclimb` (3) fler än en medlem.
- **Ordning:** avslutade och de med frontvärde ≥ 0,80 utesluts först. Bland resten väljs en per familj (flest
  modeller, vid lika antal basvarianten, alltså filnamnet lika med familjen). Familjevinnarna rangordnas efter antal
  modeller, och de 3 första väljs.

| Rang | Benchmark (fil) | Familj | Modeller | Frontvärde | Senaste körning |
|---|---|---|---|---|---|
| 1 | FrontierMath-Erdos (`frontiermath_erdos`) | frontiermath | 17 | 0,103 | 2026-11-19 |
| 2 | SpireClimb (`spireclimb`) | spireclimb | 13 | 0,413 | 2026-11-19 |

Bara två familjer återstod, så den tredje platsen är tom och det finns ingen efterträdare i rangordningen (inga fler
familjevinnare med frontvärde < 0,70). Uteslutna:

- **Avslutade:** `frontiermath` (100 modeller, ersatt av FrontierMath-Tiers-1-3-v2-Private), `frontiermath_tier_4`
  (71, ersatt av FrontierMath-Tier-4-v2-Private), `math_level_5` (108, senaste körning 2025-10-30),
  `swe_bench_verified` (33, senaste körning 2026-06-25).
- **Frontvärde ≥ 0,80:** `gpqa_diamond` (341, 0,968), `otis_mock_aime_2024_2025` (319, 1,0), `chess_puzzles` (168,
  0,830), `mystery_game_puzzles` (150, 0,950), `frontiermath_tiers_1_3_v2` (128, 0,951), `simpleqa_verified` (106,
  0,940), `frontiermath_tier_4_v2` (84, 1,0), `mirrorcode` (48, 0,978), `furniture_assembly` (43, 0,900),
  `ebr_bench` (36, 0,981).
- **Samma familj:** `spireclimb_sts1_a20_heart` (13, 0,333) och `spireclimb_sts2_a10` (13, 0,493). Lika många
  modeller som `spireclimb`, så basvarianten väljs.

Kärnserier för G1: `g1_epoch_bench_frontier_frontiermath_erdos` och `g1_epoch_bench_frontier_spireclimb` (`<valda>`),
plus `g1_epoch_bench_runs_<b>` som täckningsserier. Datum enligt föregående post: en körning är känd från
`Started at` + 30 dagar (avrundat uppåt till midnatt UTC). Månad m får `known_from` = första dagen i m+1 + 30 dagar,
och en körning som syns först i en senare hämtning ger en ny version vid max(`Started at` + 30, `first_seen`).
SpireClimbs första körningar startade 2026-11-04, så dess första hela månad (2026-11) blir känd 2026-12-31.
`frontiermath` och `frontiermath_tier_4` ligger kvar i katalogen som avslutade serier (beskrivning).

**Tolkningar, fastställda innan några serier har tittats på:**

- "Passerar 0,90" läses fortfarande som > 0,90, som i posten om I5.
- Byten gäller från den första dag då benchmarken var avslutad eller mättad med det som var känt den dagen. Byten
  registreras i `series/epoch_hub.py` (`REPLACEMENTS`) med den dagen. Tills ett byte är registrerat räknas en vald
  benchmark ändå inte när dess kända frontvärde är > 0,90 eller när dess senaste kända månad med körning slutade mer
  än 90 dagar före beräkningsdagen. `superseded_by` har ingen daterad historik och verkar därför bara genom ett
  registrerat byte. Före urvalsdagen (backcast) gäller den registrerade listan.

---

## Steg 2: förregistrering (C0, 2026-11-23)

Skrivs innan någon ny data för steg 2 har hämtats och innan någon ny metod har körts på verklig data.
Plan: `docs/steg2/plan.md`. Grinden G-A (nya kärnserier) läggs till efter våg 1, före första takträkningen.

### G-E Holdout

- **Komplexa metoder** (faktormodell C3, regim C4, horisontprognoser D2) utvecklas bara med prognos- och
  beräkningsdagar till och med **2025-06-30**, och bara med utfall kända senast den dagen.
- **Låst holdout:** 2025-07-01–2026-10-31. Den öppnas **en gång per metodfamilj**. Öppningen loggas i
  `docs/holdout_logg.md` med datum, git-sha och vad som utvärderas. Efter öppningen får familjens specifikation inte
  ändras. En ändring blir en ny familj, som bara utvärderas i det skarpa registret.
- **Enkla registrerade varianter** (C2 och baslinjer för nya mål i C5) utvärderas som tidigare över hela perioden
  med Holm-justering.
- **Det skarpa registret** från 2026-12 är det slutliga facit för alla familjer.

### G-B Nya mål och varianter

**Variantbudget:** högst 3 nya varianter per mål i steg 2, inklusive B3 (C2) och faktormodellen (C3). Holm-familjen
per mål = alla registrerade varianter som inte är baslinjer, utvärderade i samma körning. Befordringsregeln är
oförändrad: Holm-p < 0,10 och lägre MAE i både hela perioden och från 2023, plus granskning vid extraherade indata.

| Mål | Serie och utfall | Prognosdag | Baslinjer | Varianter (registrerade nu) |
|---|---|---|---|---|
| **N3** Nvidias datacenterintäkter | `rev_nvda_datacenter`, första version | Räkenskapskvartalets slut + 14 dagar | B0 slumpvandring, B1 drift (4 kvartal) | B2: Nvidias guidance för total intäkt (mittpunkt) × datacenterandelen senast känd. Guidance extraheras i våg 1 (B4) och granskas |
| **N4** Molnintäkter | `rev_aws` + `rev_google_cloud` + `rev_msft_cloud`, första version där alla tre finns | Kalenderkvartalets slut + 20 dagar | B0, B1 | V1: B1 + OLS av B1:s miss på senast kända kvartalsvisa log-tillväxt i RPO-summan (A1) |
| **N5** Andel företag som använder AI (BTOS) | Aktiv regim, första version | Dagen före den schemalagda publiceringen | B0 senaste värde, B1 drift över de 6 senaste cyklerna inom regimen | Inga nu (bara faktormodellen, om den registreras i G-D-tillägget) |
| **N6** Kontrakterad efterfrågan | RPO-summa för MSFT, GOOGL, AMZN och ORCL, första version där alla fyra finns | Kalenderkvartalets slut + 20 dagar | B0, B1 | V1: B1 + OLS av B1:s miss på kvartalets kända molnintäktstillväxt (N4-komponenter) |

Alla mål använder den gemensamma motorn (`nowcast/engine.py`): `as_of(prognosdag)` för alla indata, utfall =
första versionen och vakt mot utfall som redan är kända på prognosdagen. Fel = log(prognos) − log(utfall) ×100,
och för N5 i procentenheter.

**B3, guidance med systematisk avvikelse (C2), för N1, N2 och N3:**
- Avvikelse per bolag och guidad period: d = log(utfall / guidancens mittpunkt). Mittpunkten är den senaste
  guidance som var känd vid periodens början. TSMC per kvartal i NT$, Meta och Alphabet per kalenderår för capex,
  Nvidia per kvartal för total intäkt.
- Skattning på prognosdagen bara från avvikelser vars utfall var känt då: m = medel av bolagets d, krympt mot
  medelvärdet över bolag med vikten n/(n+4), där n = bolagets antal avvikelser. Kräver n ≥ 4, annars m = 0.
- B3 = B2 beräknad med mittpunkten × exp(m). I övrigt samma formler som B2.

**Faktormodell (C3) som variant för N1–N4:**
- Två faktorer på månadsfrekvens, skattade med EM på standardiserad takt (enligt avsnitt 1) för kärnserierna:
  - "capex och leverantörsled": G5, G6 och G7;
  - "efterfrågan": G2, G3, G4, RPO och G8.
- Kvartalsserier kopplas in med Mariano–Murasawa-aggregering. Ojämn publicering hanteras med Kalman-filter.
  Standardiseringen skattas bara på data känd på prognosdagen.
- Variant "DF": huvudmodellens prognos (B1 för N1, N3 och N4, B2 för N2) + OLS av dess miss på faktorernas
  nowcastade förändring under kvartalet eller månaden. Expanderande fönster, minst 12 rader.

### G-C Intervall och sannolikheter (C1)

- **Nivåer:** 50 %, 80 % och 95 %, samt kvantilerna 2,5, 10, 25, 50, 75, 90 och 97,5 %.
- **Metod:** punktprognos + den empiriska fördelningen av modellens tidigare fel utom stickprov (log ×100). Ett fel
  ingår först från utfallets `known_from`. Kräver minst 20 tidigare fel, annars normalfördelning med expanderande
  standardavvikelse × √(1 + 1/n).
- **Poäng:** CRPS (exakt, stickprovsbaserad), PIT och täckning per nivå. Täckningen redovisas med ett binomialt
  90 %-band.
- **Huvudmodell väljs som tidigare på MAE.** Intervallen redovisas för alla modeller, och dålig kalibrering
  redovisas men byter inte huvudmodell.

### G-D Regim och strukturbrott (C4)

- **Regim:** Markov-switching med två tillstånd (expansion och inbromsning) på den månatliga faktorn "capex och
  leverantörsled" och separat på "efterfrågan". Medel och varians skiljer sig mellan tillstånden, med expanderande
  skattning. Rapporterar P(inbromsning) varje månad.
- **Regimskifte rapporteras** när P(inbromsning) ≥ 0,8 två månader i rad, och skifte tillbaka när den är ≤ 0,2 två
  månader i rad.
- **Strukturbrott** (den metod som avsnitt 2 lämnade öppen): Bayesiansk online-changepoint per kärnserie på takten,
  med hazard 1/36 per månad och normalfördelning med okänt medel och okänd varians. Ett brott rapporteras när
  sannolikheten för körlängd 0–2 är ≥ 0,8.
- **Ett tillägg** till G-D är tillåtet efter att C3 är implementerad, men innan holdouten öppnas för C4. Det får
  bara gälla tekniska detaljer som specifikationen inte kunnat avgöra (t.ex. startvärden), och det dateras.

### 2026-11-23 – C0 preciseras efter granskning R6 (före all körning på verklig data)

Granskningen `docs/granskning/r6_c0.md` (commit 97531e9) underkände G-B och G-D och godkände G-E och G-C med
preciseringar. Inget i steg 2 har körts på verklig data.

**Beslut:** samtliga förslag i granskningen (F-E1–F-E7, F-B1–F-B22, F-C1–F-C7, F-D1–F-D8, avsnitt 7 och 8) antas
**ordagrant** och är en del av registret genom denna hänvisning. Där granskningen ger alternativ gäller:

- **F-B1:** det rekommenderade alternativet. Avvikelsen mäts mot samma guidance som B2 använder på respektive
  prognosposition, och m skattas per position.
- **F-E4:** C4:s specifikation, inklusive tillägget i G-D, låses och committas innan holdouten öppnas för C3.
- **F-B9, avsnitt 7:** Holm-familjerna i steg 2 är N1 {B3, DF}, N2 {B3, DF}, N3 {B2, B3, DF}, N4 {V1, DF} och
  N6 {V1}. Varianter som inte kan utvärderas får p = 1. Familjerna från fas 3–4 är låsta och räknas inte om. Holm över
  alla tester i steg 2 redovisas som information men avgör inte.
- **F-B10:** jämförelsemodellen för en variant är den bästa av B0, B1, målets aktuella huvudmodell och den modell
  varianten bygger på.
- **F-E6:** komplexa familjer testas på holdouten. Befordran kräver Holm-p < 0,10 och lägre MAE både på holdouten och i
  utvecklingsperioden. Vid n < 8 på holdouten görs inget test, och varianten går in som skugga i det skarpa registret.
  Det innebär i förväg att DF bara kan befordras på holdouten för N2.
- **F-E7:** D2 får inte köras på verklig data förrän en egen post för D2 finns här.
- **Planens text** om hierarkisk Bayes i C2 ersätts av registrets krympningsformel (F-B3), och planens "DF med resten av
  våg 1 som senare variant" stryks för N3 (budgeten är full, F-B12).

C1 (intervall) och C2 (B3) implementeras enligt G-C och G-B med dessa preciseringar. Avviker implementationen från
texten gäller texten.

### 2026-11-23 – G-C: tolkningar från C1 fastställs (före första körningen på verklig data)

C1:s tolkningar i `docs/steg2/c1_forslag.md` antas:
- En period som har både en skarp prognos och en rekonstruerad backtestprognos räknas en gång, med det skarpa felet.
- Varje modell utvärderas på alla sina egna backtestrader som har en fördelning. Delperioden från 2023 redovisas separat.
- DM-test på CRPS mot den bästa av B0 och B1 redovisas som information och avgör ingenting.
- Den skarpa filen lagrar felpoolen och t-parametrarna, och scorecard poängsätter den lagrade fördelningen utan
  att räkna om den.

### 2026-11-23 – A5: avstämningar mellan leden (före beräkning)

Härledda serier. Varje version finns först när alla komponenter för perioden har lämnats in. `known_from` = den
senaste komponentens. Samma kalendermappning som komponenterna (mittpunktsregeln). Inga takter är beräknade.

| Nyckel | Definition | Led |
|---|---|---|
| `x_capex_cloud` | `capex_hyp4` / (`rev_aws` + `rev_google_cloud` + `rev_msft_cloud`), samma kvartal | L3–L5 |
| `x_rpo_cover` | `rpo_hyp4` (balans vid kvartalets slut) / summan av `capex_hyp4` för de 4 senaste kvartalen | L4–L5 |
| `x_nvda_capex` | `rev_nvda_datacenter` / `capex_hyp4`, samma kalenderkvartal | L5–L6 |
| `x_debt_capex` | summan av `debt_issued_hyp4` / summan av `capex_hyp4`, de 4 senaste kvartalen | L5 |
| `x_capex_ocf` | befintlig `capex_ocf_hyp4` | L5 |

- **Mått:** takt = årsförändring i log(kvot) ×100. Förändring i takt och percentiler som i avsnitt 1.
- **Räknas inte i grenarnas diffusionsindex.** Avstämningarna redovisas separat i flödesvyn (E2) och i
  månadsbrevet som en egen rubrik.
- **Regimmodellen** (G-D) använder dem inte.

### 2026-11-23 – D2: prognoser 1–8 kvartal (förregistrering, F-E7)

D2 får köras på verklig data från och med denna post.

| Del | Val |
|---|---|
| Mål | `capex_hyp4` och molnintäkterna enligt N4, första version |
| Prognosdag | kalenderkvartalets slut + 20 dagar, samma som N1 och N4. Horisont h = 1–8 kvartal efter det senaste kvartal som är känt på prognosdagen |
| B0 | senast kända nivå |
| B1 | senast kända nivå × exp(h × medel av de 4 senaste kvartalens log-tillväxt) |
| B2 (bara capex) | kvartal i år med helårsguidance känd på prognosdagen: N1:s B2-regel för årets återstående kvartal. Senare kvartal: B1-tillväxt från det sista guidade kvartalet |
| V_kedja | direkt prognos per h: OLS av h-kvartalers log-tillväxt i målet på årstakten i `rpo_hyp4` och på log-avvikelsen i `x_capex_cloud` från sitt expanderande medel, båda kända på prognosdagen. Minst 12 rader per h |
| Holdout | G-E (komplex familj D2). Utvecklingsperiod till och med 2025-06-30 |
| Poäng | MAE och bias per h. Intervall enligt G-C med en felpool per h, där ett fel ingår först när utfallet för den horisonten är känt (F-C7) |
| Befordran | per horisontgrupp (h1–2, h3–4, h5–8): V_kedja mot den bästa av B0, B1 och B2 med regeln i F-E6. Holm över grupperna |

Ärlig not: med cirka 23 kvartal i utvecklingen och 6 i holdouten är D2 främst beskrivande. En befordran är inte
trolig, och resultatet redovisas ändå.

### 2026-11-24 – G-A: nya kärnserier efter våg 1 (före första takträkningen)

Urval efter AI-specifik relevans, minst två års historik vid registreringen (undantag: Cloudflare, som är den enda
globala trafikkällan), ärlig `known_from` och ett mått per företeelse. Kontrollserier (react, express, requests,
numpy), generella ML-paket (torch, transformers), serier med kort historik (MCP, Google-SDK:er efter namnbyten,
CoreWeave, Nebius, Micron CMBU) och oregelbundna nyckeltal (`kpi_*`) ingår inte. Inga takter har beräknats för de nya
serierna. Tabellen ersätter G3–G7 enligt parserregeln (en senare tabell ersätter grenens lista).

| Gren | Kärnserier | Anmärkning |
|---|---|---|
| G3 | `btos_ai_use_<aktiv regim>`, `eu_ai_ent_eu27`, `eu_ai_ent_se`, `g3_npm_{openai,anthropic_sdk,langchain,vercel_ai}_w`, `g3_pypi_{openai,anthropic,langchain,llama_index}_wed`, `g3_wiki_{chatgpt,llm,genai}_en`, `g3_cf_bots_ai_crawler_share`, `g3_cf_ai_purpose_user_action` | PyPI som onsdagsurval (beslut 2026-11-23). Cloudflare från 2024 |
| G4 | `rev_aws`, `rev_google_cloud`, `rev_msft_cloud`, `rev_nvda_datacenter`, `rev_orcl_cloud`, `rpo_hyp4` | RPO = kontrakterad efterfrågan (balans) |
| G5 | `capex_hyp4`, `us_constr_datacenter`, `us_pfi_info_proc_eq_sw`, `capex_ocf_hyp4`, `capex_orcl` | |
| G6 | `tsmc_revenue_m`, `us_ip_semis_m`, `us_ip_computers_m`, `us_imports_tw_m`, `us_imports_kr_m`, `rev_amd_datacenter`, `rev_avgo_semis`, `rev_mrvl_datacenter`, `asml_net_sales` | |
| G7 | `us_elec_sales_com_{va,tx,ga,az,or,oh}_m`, `eia930_avg_{pjm_dom,erco,azps,soco,srp}_m`, `pjm_lf_peak_{dom,rto}_h5` | PJM-prognoserna är årsversioner (prognos för år +5) |

### 2026-11-24 – B3: Nvidia i gruppmedlet för kvartalsintäkt (efter granskning R7)

Granskningen R7 (`docs/granskning/r7_b3_n2.md`) fann att koden utelämnar Nvidia ur gruppmedlet för "kvartalsintäkt",
trots att F-B3 anger att alla bolag med samma guidade storhet och minst en känd avvikelse ingår. Detta är en rättning
till registrets text, inte en ny variant. R7:s rekommendation gäller:
- Nvidias avvikelser (utfall `rev_nvda`, första version, mot mittpunkten i `nvda_guid_rev_mid`) ingår i gruppmedlet
  för **alla tre** TSMC-positioner, med Nvidias enda position (k = 1) som värde.
- Bara kvartal från 2017Q2, eftersom det är de som är granskade (R5).
- Samma krav på att utfallet ska vara känt på prognosdagen som för TSMC.

R7 redovisade att B3 passerar regeln under alla fyra rimliga läsningar (Holm-p 0,040–0,059). Körningen med denna
läsning är den som gäller.

### 2026-11-24 – C3: teknisk specifikation låst (F-E5)

Faktormodellens fria val (serielistor per block, transformationer, standardisering, laddningar, EM, Kalman,
Mariano–Murasawa-vikter enligt F-B20 och DF-regressionen) är fastställda i `docs/steg2/c3_spec.md`, commit `5431f41`.
Specifikationen committades före den första körningen på verklig data och ändras inte. Utvecklingsresultat:
`docs/resultat/c3_utveckling.md`. Holdouten är stängd.

### 2026-11-24 – C4: specifikation låst (G-D-tillägg, F-E4, F-D7)

Regimmodellens fria val är fastställda i `docs/steg2/c4_spec.md`, commit `735dc64`. Specifikationen committades före
den första körningen på verklig data och före holdoutens öppning för C3. Utvecklingsresultat:
`docs/resultat/c4_utveckling.md`. Holdouten är stängd för både C3 och C4. Den öppnas i en körning för båda familjerna
efter ägarens godkännande.

### 2026-11-24 – D2: n i holdout-testet räknas i prognosdagar (före öppning)

För D2 räknas n i en horisontgrupp som antalet **olika prognosdagar**, inte antalet rader (flera horisonter från samma
prognosdag är inte oberoende). Holdouten har 6 prognosdagar, så n < 8 i alla grupper. Enligt F-E6 görs då inget
holdout-test, och V_kedja går in som skugga i det skarpa registret. Utvecklingen (`docs/resultat/d2_utveckling.md`) hade
1–5 rader för V_kedja och avgör ingenting.

### 2026-11-24 – D2 i skarp drift: huvudmodell per horisontgrupp

D2 skrivs som skugga från 2027-01-20 (`forecasts/d2/<kvartal>.json`). Huvudmodellen per horisontgrupp är den baslinje
(B0, B1 eller B2) som hade lägst medel-MAE över gruppens horisonter i utvecklingsperioden: capex B2 (h1–2, h3–4) och
B1 (h5–8), moln B1 i alla grupper. Valet för capex h3–4 är knappt (19,2 mot 19,8). V_kedja är skugga överallt.
Holdout-prognosdagarna (2025-07-01–2027-01-19) körs aldrig.

### 2026-11-24 – G1: Arena-toppen som kärnserie (efter spår G12, före takträkning)

`g1_arena_text_top` (högsta betyg i LMArenas textrankning per månad, daterat med tidsstämplade commits från den
ursprungliga topplistan) läggs till som kärnserie i G1. Urvalet bygger på tillgång, historik och ärliga datum. Bakåtfylld
historik från datasetets massuppladdning 2026-04-02 är daterad därefter. Inga takter är beräknade.
- **Mått:** nivån i Arena-poäng, som redan är en logit-skala. Takt = 12-månadersförändring i poäng (metod "share",
  differens).
- **Bara Bradley–Terry-eran,** från 2024-01. Elo-perioden före bytet används inte. Skalbrotten 2025-05-16 och 2025-07-23
  noteras som kända brott.
- **Referensserier, inte kärnserier:** gapet mot en referensmodell och "style control", eftersom de mäter samma sak.
  SWE-bench (ingen licens, ändrad inlämningspolicy) och AWS GPU-priser (bara ett prisbyte på hela historiken) ingår
  inte heller.

| Gren | Kärnserier | Anmärkning |
|---|---|---|
| G1 | `g1_epoch_bench_frontier_<valda>`, `g1_epoch_train_compute_frontier`, `g1_epoch_eci_frontier`, `g1_arena_text_top` | ECI spärrad (bakåtfylld). Arena från 2024-01 |

### 2026-11-24 – Diffusionsindex v2: en röst per källfamilj (beslut 2026-11-24, gäller från ögonblicksbilden 2026-11-30)

Johannes beslut 2026-11-24 (beslutspunkt 2 i `docs/riktning.md`). Diffusionsindexet i avsnitt 2 ger i dag en röst
per serie. Flera kärnserier är skivor av samma källa: G8 är nio länder ur Indeeds data, G9 har tre arXiv-kategorier och
G7 sex delstater ur samma EIA-tabell. Skivor av samma källa samvarierar och får enigheten att se större ut än den är.
v2 ger därför en röst per källfamilj.

Ärlig not: den rekonstruerade historiken med v1 har redan setts (spår F5 och F6, `docs/resultat/tillstand.md`).
Ändringen motiveras av att serierna inte är oberoende, inte av vad historiken visade. Inget värde med v2 har räknats
på verklig data före denna post. Väntad effekt, bara efter konstruktion: grenar med en eller två familjer (G2, G8 och
G9 så länge Epoch-databasens serier är spärrade) får inget tillstånd, och G7 med tre familjer ligger på gränsen.
Påståendena blir försiktigare åt båda hållen.

**Källfamilj.** Kärnserier som kommer från samma källa, mäter samma begrepp och bara skiljer sig i skiva (land,
delstat, balansområde, zon, paket, kategori, bransch eller frågeregim) är en familj.
- En klammerpost i kärnserietabellen (t.ex. `ai_postings_share_{us,gb,...}_d`) är alltid en familj.
- Serier från olika bolag (olika inlämnare) eller olika källor är olika familjer.
- Olika begrepp ur samma källa är olika familjer.
- `<valda>` i G1 ger en familj per vald benchmark. Urvalsregeln (2026-11-23) väljer redan högst en benchmark per
  benchmarkfamilj, så två valda benchmarks mäter olika förmågor.

**Familjetabell.** Den täcker varje post i de gällande kärnserietabellerna exakt en gång. Koden läser tabellen
(`state.register.FAMILIES`, ett test jämför de två).

| Gren | Källfamilj | Kärnserier | Källa och begrepp |
|---|---|---|---|
| G1 | `g1_epoch_bench_<valda>` | `g1_epoch_bench_frontier_<valda>` | Epochs benchmarkhubb, frontvärde. En familj per vald benchmark |
| G1 | `g1_epoch_train_compute` | `g1_epoch_train_compute_frontier` | Epochs modelldatabas, största träningsberäkning |
| G1 | `g1_epoch_eci` | `g1_epoch_eci_frontier` | Epochs benchmarkhubb, ECI |
| G1 | `g1_arena_text` | `g1_arena_text_top` | LMArena, högsta betyg i textrankningen |
| G2 | `g2_price_at_capability` | `g2_price_at_capability_gpqa` | LiteLLM och Epoch, pris vid fast förmåga |
| G3 | `btos_ai_use` | `btos_ai_use_<aktiv regim>` | Census BTOS, andel företag som använder AI, alla frågeregimer |
| G3 | `eu_ai_ent` | `eu_ai_ent_eu27`, `eu_ai_ent_se` | Eurostat isoc_eb_ai, andel företag som använder AI (Sverige ingår i EU27) |
| G3 | `g3_npm` | `g3_npm_{openai,anthropic_sdk,langchain,vercel_ai}_w` | npm, nedladdningar av AI-paket |
| G3 | `g3_pypi` | `g3_pypi_{openai,anthropic,langchain,llama_index}_wed` | PyPI, nedladdningar av AI-paket |
| G3 | `g3_wiki` | `g3_wiki_{chatgpt,llm,genai}_en` | Wikimedia, sidvisningar för AI-artiklar |
| G3 | `g3_cf_ai_crawler` | `g3_cf_bots_ai_crawler_share` | Cloudflare Radar, AI-crawlers andel av botarnas förfrågningar |
| G3 | `g3_cf_ai_purpose` | `g3_cf_ai_purpose_user_action` | Cloudflare Radar, andel AI-förfrågningar på uppdrag av en användare |
| G4 | `rev_aws` | `rev_aws` | Amazon (SEC), segmentintäkt AWS |
| G4 | `rev_google_cloud` | `rev_google_cloud` | Alphabet (SEC), segmentintäkt Google Cloud |
| G4 | `rev_msft_cloud` | `rev_msft_cloud` | Microsoft (SEC), Microsoft Cloud |
| G4 | `rev_nvda_datacenter` | `rev_nvda_datacenter` | Nvidia (SEC), segmentintäkt Data Center |
| G4 | `rev_orcl_cloud` | `rev_orcl_cloud` | Oracle (SEC), segmentintäkt Cloud |
| G4 | `rpo_hyp4` | `rpo_hyp4` | SEC, RPO för MSFT, GOOGL, AMZN och ORCL (summa) |
| G5 | `capex_hyp4` | `capex_hyp4` | SEC, capex för de fyra största (summa) |
| G5 | `us_constr_datacenter` | `us_constr_datacenter` | Census C30, byggutgifter för datacenter |
| G5 | `us_pfi_info_proc_eq_sw` | `us_pfi_info_proc_eq_sw` | BEA NIPA, investeringar i IT-utrustning och programvara |
| G5 | `capex_ocf_hyp4` | `capex_ocf_hyp4` | SEC, capex som andel av operativt kassaflöde för de fyra största |
| G5 | `capex_orcl` | `capex_orcl` | Oracle (SEC), capex |
| G6 | `tsmc_revenue_m` | `tsmc_revenue_m` | TSMC (6-K), månadsintäkt |
| G6 | `us_ip_g17` | `us_ip_semis_m`, `us_ip_computers_m` | Fed G.17, industriproduktion per bransch |
| G6 | `us_imports_ft900` | `us_imports_tw_m`, `us_imports_kr_m` | Census FT-900, varuimport per land |
| G6 | `rev_amd_datacenter` | `rev_amd_datacenter` | AMD (SEC), segmentintäkt Data Center |
| G6 | `rev_avgo_semis` | `rev_avgo_semis` | Broadcom (SEC), segmentintäkt halvledare |
| G6 | `rev_mrvl_datacenter` | `rev_mrvl_datacenter` | Marvell (SEC), intäkt från slutmarknaden datacenter |
| G6 | `asml_net_sales` | `asml_net_sales` | ASML (6-K), nettoomsättning |
| G7 | `us_elec_sales_com` | `us_elec_sales_com_{va,tx,ga,az,or,oh}_m` | EIA (EPM och 861M), elförsäljning till kommersiell sektor per delstat |
| G7 | `eia930_avg` | `eia930_avg_{pjm_dom,erco,azps,soco,srp}_m` | EIA-930, medellast per balansområde |
| G7 | `pjm_lf_peak` | `pjm_lf_peak_{dom,rto}_h5` | PJM, lastprognos för sommartoppen per zon |
| G8 | `ai_postings_share` | `ai_postings_share_{us,gb,de,fr,ca,au,ie,it,nl}_d` | Indeed Hiring Lab, andel platsannonser som nämner AI, per land |
| G9 | `g9_arxiv` | `g9_arxiv_cs_ai`, `g9_arxiv_cs_lg`, `g9_arxiv_cs_cl` | arXiv, nya artiklar per primärkategori |
| G9 | `g9_epoch_open_weights` | `g9_epoch_open_weights_share` | Epochs modelldatabas, andel modeller med öppna vikter |
| G9 | `g9_epoch_notable_models` | `g9_epoch_notable_models` | Epochs modelldatabas, antal notable-modeller |

Antal familjer: G1 3 plus antalet valda benchmarks (i dag 2, alltså 5), G2 1, G3 7, G4 6, G5 5, G6 7, G7 3, G8 1 och
G9 3. Spärrade serier (ECI, Epochs modelldatabas i G9) räknas inte förrän spärren släpper, och då inte heller deras
familj.

**Gränsfall**, avgjorda mekaniskt med regeln ovan:
- `capex_ocf_hyp4` har samma täljare som `capex_hyp4`, men är ett annat begrepp (andel av kassaflödet). Två familjer,
  även om riktningarna kan samvariera.
- npm och PyPI mäter samma begrepp i olika register. Olika källor, alltså två familjer.
- EIA:s elförsäljning och EIA-930 har samma utgivare men olika undersökningar och begrepp (såld el till kommersiell
  sektor mot medellast i balansområdet). Två familjer. PJM:s lastprognos och EIA-930:s DOM är olika källor och olika
  begrepp (prognos mot utfall).
- Epochs serier (benchmarks, ECI, träningsberäkning, öppna vikter och antal modeller) har samma utgivare men olika
  begrepp. Egna familjer. ECI väger samman hubbens benchmarkresultat, och de valda benchmarkerna körs till stor del på
  samma modeller. Det är en kvarvarande samvariation som regeln inte fångar.
- `rpo_hyp4` och segmentintäkterna i G4 har delvis samma inlämnare men olika begrepp. Egna familjer.
- Fed G.17 (halvledare och datorer) är branschskivor av samma index, och FT-900 (Taiwan och Sydkorea) är landskivor av
  samma tabell. En familj var.
- PJM RTO innehåller DOM, och EU27 innehåller Sverige. Båda paren är redan en familj.

**Regel v2:**
- Vilka serier som räknas och riktningen per serie, d ∈ {−1, 0, +1}, är oförändrade (avsnitt 2 och ändringarna).
- Familjens röst = medelvärdet av (d + 1)/2 över familjens räknade serier. En familj med en serie röstar 1, 0,5 eller 0.
- **index_v2** = medelvärdet av familjernas röster över familjer med minst en räknad serie.
- Tillstånd med oförändrade gränser, jämförda oavrundat: *accelererar* om index ≥ 0,67, *bromsar in* om index ≤ 0,33,
  annars *stabil*. Med färre än 3 räknade familjer visas indexet men inget tillstånd ("för få källor").
- Om varje familj har en serie är index_v2 = index_v1. Testerna kontrollerar det.

**v1** är regeln i avsnitt 2 (en röst per serie, minst 3 serier, "för få serier"). Den räknas och publiceras bredvid
under namnet v1. v1 blir inte officiell regel igen utan en ny registerpost.

**Gäller** från den första skarpa ögonblicksbilden 2026-11-30 (`snapshots/2026-11.json`). Ögonblicksbilden anger
regelversionen och familjetabellen. Rekonstruerad historik räknas med båda reglerna och märks som rekonstruktion.

**Framtida kärnserier** tilldelas en familj i samma registerpost som lägger till dem, i en tabell med kolumnerna
`Gren | Källfamilj | Kärnserier`. En senare familjetabell ersätter grenens familjer, på samma sätt som en senare
kärnserietabell ersätter grenens kärnserier.

### 2026-11-24 – Diffusionsindex v2: familjenamnet i G2 byts (före beräkning)

Familjen `g2_price_at_capability` i föregående post har samma namn som katalogserien för ECI-varianten
(`g2_price_at_capability`, som inte är kärnserie). Namnet kan då läsas som den serien. Familjen heter i stället
`g2_price_at_capability_gpqa`, efter sin enda serie, som de andra familjerna med en serie. Bara namnet ändras. Inga
värden har räknats. Tabellen ersätter G2:s familjer enligt parserregeln.

| Gren | Källfamilj | Kärnserier | Källa och begrepp |
|---|---|---|---|
| G2 | `g2_price_at_capability_gpqa` | `g2_price_at_capability_gpqa` | LiteLLM och Epoch, pris vid fast förmåga (GPQA Diamond) |

### 2026-11-24 – Diffusionsindex v2: väntad effekt och namnregel rättas (anteckning efter R9, ingen regeländring)

Granskning R9 fann två meningar i de två posterna ovan som inte stämmer. Regeln, familjetabellen, gränserna och
min_families ändras inte.

- **Väntad effekt.** Posten om en röst per källfamilj säger att påståendena blir försiktigare åt båda hållen. Det var
  en väntan efter konstruktion. Orkestrerarens rekonstruktion på riktiga data (2026-05 till 2026-10) gjordes efter
  registerposten och koden, och den visar att meningen inte håller genomgående. G8 får "för få källor" som väntat.
  Men G6 blir "accelererar" och G7 "bromsar in" i månader där v1 sa "stabil". När familjerna är få väger varje familj
  tungt, så indexet kan röra sig mer än med v1. Orkestreraren har rättat samma sak i beslutsloggen och i
  `docs/riktning.md`, avsnitt 6. R9 har inte gjort om jämförelsen.
- **Skälet för v2 gäller.** Indexet ska räkna oberoende källor. Regeln ändras inte på grund av dessa värden, och
  ingen ändring görs i någon riktning.
- **Namnregeln.** Posten om namnbytet i G2 säger att det nya namnet följer serien "som de andra familjerna med en
  serie". Det stämmer inte för alla. Sju familjer med en serie bär inte seriens namn: `g1_epoch_train_compute`,
  `g1_epoch_eci`, `g1_arena_text`, `btos_ai_use`, `g3_cf_ai_crawler`, `g3_cf_ai_purpose` och
  `g9_epoch_open_weights`. Det gäller bara namnen, inga värden.
- **Oavrundat betyder exakt.** Koden räknar nu familjernas röster och index v2 som bråktal och jämför dem exakt med
  0,67 och 0,33. Ett flyttalsmedel kunde annars hamna en hårsmån fel vid en gräns. Med de registrerade
  familjestorlekarna kan ingen kombination träffa en gräns exakt, så inget tillstånd ändras.

### 2026-11-24 – G2: pensionerade modeller i Arena-prisserierna (efter första bygget, före takträkning; granskning R8, rättning X5)

Gäller bara de beskrivande serierna `g2_price_at_arena_capability` (A) och `g2_price_at_arena_capability_4o` (B),
som inte är kärnserier (underkända i R8, `docs/granskning/r8_g2_arena.md`). Ändringen infördes efter första
bygget, före all analys av takt, och den utlöstes av en nivåkontroll: `gemini/gemini-1.5-flash-001` satte minimum
i A långt efter att modellen pensionerats.

- **Regel:** en nyckel räknas inte för månad m om LiteLLM-filen vid månadsslut anger `deprecation_date` ≤
  månadsslut. Bara filen vid månadsslut används. Ett datum som LiteLLM lägger till senare påverkar inte tidigare
  månader. LiteLLM anger inte alltid pensionering, så en pensionerad modell utan datum räknas fortfarande.
- **Motivering:** värdet ska vara det lägsta pris som förmågan går att köpa för. En pensionerad modell har inget
  pris. Bland möjliga sätt att datera pensionering (LiteLLM:s datum vid månadsslut, utvecklarens avstängningsdatum,
  att nyckeln tas bort ur LiteLLM) är det valda det enda som är ärligt daterat utan extra källor.
- **Effekt (R8 punkt 3):** annan modell vid minimum i A 2025-05 – 2026-02 och 2026-08, i B 2026-01, 2026-02 och
  2026-08. Andra värden 2026-01 – 02 (0,1375 i stället för 0,13125) och 2026-08 (0,1375 i stället för 0,09), i båda.
  Halveringstiden med G2:s front (löpande minimum) är identisk med och utan regeln i alla månader, eftersom fronten
  tar tillbaka priset för den pensionerade modellen.
- **Öppen fråga (inte beslutad här):** ska samma regel gälla `g2_price_at_capability` och
  `g2_price_at_capability_gpqa` (spår I6)? De följer i dag inte regeln, och `g2_price_at_capability_gpqa` är
  registrerad kärnserie. Den ändras inte i rättningen. Rekommendation: ja, som en daterad registerändring
  för båda I6-serierna efter en omkörning som redovisar effekten, eftersom två regler för pensionerade modeller i
  samma gren inte ska finnas utan motivering. Effekten på kärnseriens takt blir troligen noll av samma skäl som
  ovan (löpande minimum), men det ska visas och inte antas. Frågan hänger ihop med R8 R-6 (om G2:s front ska bortse
  från pensionerade modeller), som också är öppen.

### 2026-11-24 – P2a: nyttjandeperioder som katalogserier (extraktion, inte kärnserier)

Låst före kodningen. Inga dokument var hämtade och inga värden lästa när posten skrevs. Regler i detalj:
[`docs/kallor/nyttjandeperioder.md`](kallor/nyttjandeperioder.md), avsnittet "Kodningsregler".
- **Vad:** den nyttjandeperiod (år) som Microsoft, Alphabet, Amazon, Meta, Oracle och CoreWeave anger för servrar och
  nätverksutrustning i 10-K, 10-Q och 8-K (Item 2.02) från 2018, och varje ändrad uppskattning med effektivt datum,
  gammal och ny period, klass och bolagets egen effekt (belopp, mått, period) när den anges.
- **Serier:** `useful_life_servers_<bolag>_lo/_hi`, `useful_life_network_<bolag>_lo/_hi` och en serie per bredare
  klass (`useful_life_<klass>_<bolag>_lo/_hi`). Kalenderkvartal, enhet år, gren G5. Värdet i ett kvartal är det som
  ett dokument anger för kvartalet (policy vid balansdagen, eller ny period från kvartalet där ändringen gäller).
- **known_from** = EDGAR:s `filingDate` för det tidigaste SEC-dokumentet som anger värdet. En ändring som meddelas
  innan den gäller får known_from före periodens slut. Det är ett känt framtida värde, inte läckage.
- **Glesa serier, stegfunktion.** Ingen ifyllning i observationstabellen. Den som använder serierna tar det senaste
  kända värdet per kvartal och prognosdag (`useful_lives.in_effect`).
- **Inte kärnserier.** De ingår inte i grenarnas tillstånd, diffusionsindex eller takter. Ingen takt räknas. N7 (P3)
  registrerar själv hur perioderna används.
- **Effekter** (bolagens egna belopp för en ändring) och ändringar för en del av en klass (`_SUBSET`) blir inga
  katalogserier. De finns i `curated/useful_lives.csv` och i `useful_lives.changes()`.
- **Publicering:** `publish=True`, eftersom det är siffror ur offentliga SEC-dokument med källhänvisning. Extraktionen
  stickprovskontrolleras (`useful_lives_check`) och granskas sedan oberoende. Underkänns den sätts `publish=False`.

### 2026-11-24 – P2a: kompletterande kandidatsökning, stoppens plats och självkontrollen (rättning efter R15)

Rättning efter granskningen R15 (`docs/granskning/r15_nyttjandeperioder.md`, F-1 och F-2), spår X12. Posten
2026-11-24 om P2a och kodningsreglerna i `docs/kallor/nyttjandeperioder.md` står kvar oförändrade. Här loggas tre
avvikelser som gjordes under kodningen, när värdena redan var sedda, men som inte registrerades.
- **Kandidatregeln (F-2).** Den låsta kandidatregeln var för smal. Agenten läste också de fem meningarna efter varje
  kandidat som beskriver en ändring och alla andra meningar med en nyttjandeperiod och ett antal år (tolkning 1 i
  källdokumentet). 82 av 305 rader kommer från meningar utanför kandidaturvalet: 76 effekter (Microsoft 38, Oracle 24,
  Meta 9, Amazon 4, Alphabet 1), Oracles 5 policyrader 2018–2022 och CoreWeaves ändring. Motivering: effektmeningar
  nämner sällan klassen med ett antal år, och två klassnamn (Oracle 2018–2022, CoreWeave) föll utanför `CLASS_RE`.
  Avvikelsen gör bara läsmängden större. Den ändrar ingen kodningsregel och gynnar inget utfall, och R15:s bredare
  sökning hittade inga fler rader.
- **Läsmängden är nu kod.** `useful_lives_corpus.supplementary()` ger den kompletterande mängden: 1 271 meningar
  (884 unika) efter en kandidat som beskriver en ändring och 74 (55 unika) med nyttjandeperiod och antal år. Alla 82
  rader finns i den. Från och med nu är läsmängden kandidaterna plus den kompletterande mängden. Koden skrevs i
  efterhand och visar att mängden går att göra om, inte exakt vilka meningar som lästes.
- **Stoppens plats och självkontrollen (F-1).** Platsregeln för stopp täckte inte fallet där stycket finns kvar med tal
  för en ny klass. De tre stoppen pekar då på policymeningen för den nya klassen (tolkning 10). Självkontrollen
  ändrades efter första körningen: belopp i formen med en decimal godkänns, och stoppkontrollen är `class_stated()`
  (klassens namn direkt följt av ett antal år, i någon mening i dokumentet) i stället för att ingen kandidatmening
  anger ett antal år för klassen. Med den första kontrollen (`fc49225`) ger 11 av 305 rader fel (8 effekter och 3
  stopp). R15 bekräftade alla 11 i sak.
- **Effekt:** inga värden, inga serier och ingen kodningsregel ändras. "0 fel av 305" gäller den ändrade kontrollen.

### 2026-11-24 – P1: avskrivningar och anläggningstillgångar som katalogserier (inte kärnserier)

Spår P1 (förslag 3 i `riktning.md`). Serierna är katalogserier i G5 och underlag för intäktskravet (P2b) och prognosmålet
N7 (P3). De ingår inte i diffusionsindexet, och här räknas inga takter eller tillstånd. Kod:
`src/ai_tracker/series/sec_avskrivningar.py` och `sources/sec_custom.py`. Källa och kontroller:
`docs/kallor/sec_avskrivningar.md`.

**Regel för taggval.** Taggen väljs per bolag efter täckning och definitionskonsistens, aldrig efter seriens förlopp.
- `dep_<co>` är den rad (eller de rader) som läggs tillbaka för avskrivningar i kassaflödesanalysen, med bolagets egen
  etikett. Raden har kontrollerats i den renderade kassaflödesanalysen i 10-K (R-sidorna).
- `dep_ppe_<co>` är avskrivningar på anläggningstillgångar utan amortering av förvärvade immateriella tillgångar, ur
  noten om anläggningstillgångar, där den taggas per kvartal.
- En serie har en definition. Om raden byter innehåll och tidigare perioder inte räknas om, börjar serien vid den nya
  definitionen. Äldre perioder skarvas inte på.
- Byte av tagg för samma rad, med identiska värden i överlappet, skarvas per kvartal med `sec.py`:s regel.
- Omräkningar av samma rad är versioner, med regeln om konsekvent bas i `sec.py`. En inlämning som räknar om tidigare
  värden med mer än 2 % (`sec_segment.definition_breaks`) ska deklareras per serie efter granskning, och en odeklarerad
  omräkning stoppar hämtningen. En deklarerad omräkning av en kassaflödesrad ger ingen ny nyckel, eftersom bolagen gör
  omklassificeringar just genom att räkna om jämförelsetalen. Kvartal som bolaget inte räknade om ligger kvar på den
  gamla basen, och det redovisas per serie.

| Bolag | `dep_<co>` | `dep_ppe_<co>` |
|---|---|---|
| MSFT | `msft:DepreciationAmortizationAndOther` ("Depreciation, amortization, and other"), en egen tagg som läses ur varje inlämnings XBRL-instans | `Depreciation`, per kvartal från FY2025 (2024Q3) |
| GOOGL | `Depreciation` ("Depreciation of property and equipment"), från 2023Q1. Definitionen från 10-K för 2023 saknar nedskrivning, och de immateriella ligger i "Other". De äldre egna taggarna ("depreciation and impairment", 2014–2022) skarvas inte | samma tagg och samma värden som `dep_googl` |
| AMZN | `DepreciationDepletionAndAmortization`, bara perioder som börjar 2019-01-01 eller senare. Raden innehåller operationella leasingtillgångar från 2019 (ASC 842, utan omräkning) och dessutom aktiverat innehåll (video och musik) | `Depreciation` (avskrivningar på anläggningstillgångar), per kvartal från 2024 |
| META | `DepreciationDepletionAndAmortization` | `Depreciation`, per kvartal från 2019 |
| ORCL | `Depreciation` + `AmortizationOfIntangibleAssets`, två rader som summeras ur samma inlämning | `Depreciation` |
| CRWV | `DepreciationDepletionAndAmortization` | `Depreciation` |

**Anläggningstillgångar** (balans vid kvartalets slut):
- `ppe_net_<co>`: taggarna `PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization`
  och sedan `PropertyPlantAndEquipmentNet`. De två är identiska i alla överlapp (GOOGL 7, AMZN 4, META 1, CRWV 8). För
  Alphabet 2020Q1 läses bolagets egen tagg ur 10-Q:ns instans.
- `ppe_gross_<co>` = netto + ackumulerade avskrivningar, ur samma inlämning och samma taggfamilj. Familjen med
  finansiell leasing (`...AccumulatedDepreciationAndAmortization`) används först, därefter
  `AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment`. Bruttotaggarna används inte, eftersom de
  ibland står för en delsumma: i Alphabets 10-K för 2024 ligger `PropertyPlantAndEquipmentGross` för 2023-12-31 17 %
  under bruttot i övriga inlämningar.
- Bruttot finns per kvartal bara för MSFT, GOOGL, META och CRWV. Amazon och Oracle taggar bruttot och de ackumulerade
  avskrivningarna bara vid räkenskapsårets slut. Därför finns ingen `ppe_gross_amzn`, `ppe_gross_orcl` eller
  `ppe_gross_hyp4`.
- En balans räknas bara om balansdagen är ett räkenskapskvartals slut. Kalenderkvartal sätts med mittpunktsregeln
  (`sec_instant`).
- Om finansiell leasing ingår redovisas per bolag i källdokumentet. Kontrollen görs mot bolagets egen text, inte mot
  värdena.

**Summor och segment:** `dep_hyp4`, `dep_ppe_hyp4` och `ppe_net_hyp4` (MSFT, GOOGL, AMZN och META) räknas med
`sec.aggregate`. En version finns först när alla fyra är kända, och known_from är den senaste inlämningen. `dep_aws` är
AWS-segmentets avskrivningar (`Depreciation` med `StatementBusinessSegmentsAxis` = `AmazonWebServicesSegmentMember`,
äldre `DepreciationDepletionAndAmortization`). Värdet finns per kvartal i 10-Q från 2025-05 (2025Q1 med 2024 som
jämförelse), och tidigare bara för helår.

**Datering:** known_from är inlämningsdatumet för 10-Q eller 10-K. Varje inlämning är en version, och YTD-differenser,
Q4 = helår − 9M och kalendermappning görs som i `sec.py`.

**Vad som setts före denna post:** vilka perioder och datum varje kandidattagg täcker, och etikett och tagg för
avskrivningsraderna i kassaflödesanalysen i ett urval 10-K (R-sidorna visar också helårsvärdena). Dessutom den relativa
skillnaden mellan kandidattaggar i överlappande perioder, MSFT-taggens täckning och storleken på omräkningarna (relativt),
och Alphabets balansposter i instanserna 2018–2020 (nivåer, för kontrollen netto = brutto − ackumulerat). Inga
kvartalsserier eller takter har räknats.

### 2026-11-24 – A5: intäktskrav (avskrivningar och kapitalkostnad mot intäkter)

Spår P2b (förslag 3 i `riktning.md`, "Följ pengarna hela vägen"). Fem nya avstämningar i samma grupp som A5-posten
2026-11-23. De mäter hur avskrivningar och kapitalkostnad växer i förhållande till intäkterna, och hur långt
avskrivningarna ligger efter investeringarna. De beskriver och tar ingen ställning. Komponenterna är P1:s serier
(posten ovan) och befintliga intäkts- och capexserier.

| Nyckel | Definition (×100, procent) | Led |
|---|---|---|
| `x_dep_rev` | summan av `dep_hyp4` för de 4 senaste kvartalen / summan av `rev_msft` + `rev_googl` + `rev_amzn` + `rev_meta` för samma 4 kvartal | L3–L5 |
| `x_capcost_rev_r08` | (summan av `dep_hyp4` för de 4 senaste kvartalen + 0,08 × `ppe_net_hyp4` vid periodens kvartalsslut) / samma 4-kvartalsintäkter | L3–L5 |
| `x_capcost_rev_r12` | som `x_capcost_rev_r08` med 0,12 | L3–L5 |
| `x_dep_capex` | summan av `dep_hyp4` / summan av `capex_hyp4`, de 4 senaste kvartalen | L5 |
| `x_dep_rev_aws` | summan av `dep_aws` / summan av `rev_aws`, de 4 senaste kvartalen | L3–L5 |

- **Nämnaren är bolagens totala intäkter**, eftersom Meta saknar molnintäkter. Totala intäkter är den nämnare som
  täcker samma fyra bolag som täljaren. AWS-kvoten är den enda där både täljare och nämnare är ett molnsegment.
- **dep_hyp4, inte dep_ppe_hyp4.** Beslutet bygger bara på taggtäckning enligt P1:s resultat: `dep_ppe_hyp4` finns per
  kvartal först från 2024Q3 (Microsoft taggar `Depreciation` per kvartal från FY2025 och Amazon från 2024), alltså 9
  kvartal, medan `dep_hyp4` har 15 (från 2023Q1). `dep_ppe` är alltså inte konsekvent taggad för alla fyra över den
  period som `dep_hyp4` täcker. Förbehållen för `dep_hyp4` gäller: Microsofts rad innehåller "other" (kvartal till och
  med 2024Q3 på den gamla basen), Amazons innehåller innehåll och operationella leasingtillgångar, och Metas innehåller
  amortering på immateriella tillgångar.
- **Avkastningskravet r** är ett antagande och ingen skattning. 0,08 och 0,12 är ett registrerat intervall för en
  årlig avkastning före skatt på nettot av anläggningstillgångarna. Intervallet ändras inte efter att värdena har setts.
  Kvoten är linjär i r, så ett värde mellan ändpunkterna är en interpolation. Intäktskravet omfattar bara kapitalet:
  avskrivningar och avkastning på nettot. Drift, el, personal och skatt ingår inte.
- **Stock och flöde:** `ppe_net_hyp4` är en balans vid kvartalets slut för periodens sista kvartal. Den summeras inte,
  och en omräkning av en tidigare balans påverkar inte senare perioder. Avskrivningar, intäkter och capex är flöden
  över fyra kvartal.
- **Versioner** som A5: en version finns först när alla par (serie, kvartal) är kända på dagen, `known_from` = den
  senaste komponenten, och `source` blir `backfill` om något indata är en backfill-rad. Samma kalendermappning som
  komponenterna (mittpunktsregeln).
- **Mått** som A5: takt = årsförändring i log(kvot) ×100, förändring i takt och percentiler som i avsnitt 1. Räknas
  inte i grenarnas diffusionsindex, och regimmodellen använder dem inte. De redovisas i gruppen "Avstämningar" i
  ögonblicksbilden, månadsbrevet och flödesvyn.
- **Beskrivande tillägg i resultatdokumentet** (`docs/resultat/intaktskrav.md`), inga serier och inga mått:
  (a) samma kvot som `x_dep_rev` med `dep_ppe_hyp4` i täljaren, för de perioder den finns, som känslighet för
  definitionsskillnaderna; (b) per bolag (MSFT, GOOGL, AMZN, META, ORCL, CRWV) `dep_<co>` / `rev_<co>` och
  (`dep_<co>` + r × `ppe_net_<co>`) / `rev_<co>` för r = 0,08 och 0,12, för den senaste perioden där alla komponenter
  finns, med samma versionsregel.

**Vad som setts före denna post:** P1:s resultat med antal kvartal och första och sista period per serie, och P1:s
registerpost och källdokument. P1:s resultat nämner två enskilda belopp från handkontrollerna (Microsofts avskrivningsrad
i Q4 FY2026 och Amazons avskrivningar på anläggningstillgångar 2025). Inga kvoter, takter eller nivåer av komponenterna
har räknats eller setts i detta spår.

### 2026-11-24 – N7: avskrivningar 1–8 kvartal (förregistrering, före körning)

Spår P3 (förslag 3 i `riktning.md`). Posten committas innan någon prognos, något fel eller någon tillväxttakt för
avskrivningarna har räknats. N7 är ett nytt mål i steg 2 med två varianter (budget högst 3, G-B). Kod:
`src/ai_tracker/nowcast/n7.py`, körs med `python -m ai_tracker.nowcast backtest n7`. Avviker koden från texten gäller
texten.

**Vad som setts före posten.** Täckningen för `dep_<bolag>`, `dep_hyp4`, `capex_<bolag>` och `capex_hyp4`: första och
sista kvartal, antal kvartal, luckor och intervallet för known_from i första versionen, samt första versionens datum för
de sex första kvartalen av `dep_googl` och `dep_hyp4`. Brottkvartal och inlämningsdatum enligt F-B8-funktionen
(`quarterly.breaks_of`), utan storlek. Nyttjandeperioderna för servrar (`useful_life_servers_<bolag>_hi`, värden och
datum), som är indata. Dessutom visar `docs/resultat/n1.md` utfallen för `capex_hyp4` och B1:s fel per kvartal
2024Q2–2026Q3, och uppdraget från orkestreraren citerade tre enstaka belopp ur P1:s handkontroller. Inga
avskrivningsserier, tillväxttal eller prognosfel har räknats eller lästs.

| Del | Val |
|---|---|
| Mål N7 | `dep_hyp4` (MSFT, GOOGL, AMZN och META), första versionen. Byggs om ur bolagsserierna med `quarterly.aggregate_rows`, som i N4. `dep_ppe_hyp4` väljs inte, eftersom den bara har 9 kvartal mot 15 |
| N7b | Samma modeller per bolag på `dep_msft`, `dep_googl`, `dep_amzn` och `dep_meta`, poolat över bolag och prognosdagar, som N1b |
| Capex | `capex_<bolag>` (komponenterna i `capex_hyp4`). För N7 summeras bolagens glidande medel |
| Prognosdag | Kalenderkvartalets slut + 20 dagar (`n1.origin_for`). All information `as_of(prognosdag)`, även målets egen historik och nyttjandeperioderna |
| Horisont | L = det senaste kvartalet av målet som är känt på prognosdagen. h = 1–8, och målkvartalet är L + h, som i D2. På de registrerade prognosdagarna har inget av bolagen rapporterat det kvartal som just slutat, så normalt är h = 1 det kvartalet (N1:s nowcastkvartal), och h = 8 ligger sju kvartal efter det |
| Fel | 100 × (log prognos − log utfall). MAE är huvudmått, och bias redovisas |
| B0 | y(L) för alla h |
| B1 | y(L) × exp(h × medel av de 4 senaste kvartalens log-tillväxt), som D2 (`n1.b1_path`) |
| V1 | Rak linje: ŷ(t) = c · m(t), där m(t) = Σ över bolagen av (1/J) · Σ_{j=1..J} capex(t − j) och J = 4N kvartal. N väljs på varje prognosdag ur rutnätet {3, 4, …, 10} år, och c skattas med OLS genom origo |
| V2 | V1 med N per bolag = den senast angivna nyttjandeperioden för servrar (P2a), känd på prognosdagen. Bara c skattas |

**V1 i detalj.**
- **Träningsrad:** ett kvartal t i målets historik `as_of(prognosdag)` med y(t) > 0, där capex(t − 1), …, capex(t − J)
  för vart och ett av enhetens bolag är kända och positiva `as_of(prognosdag)`. Träningen använder alltså de versioner
  som är kända på prognosdagen, som N1. Minst 12 sådana rader.
- **c** = Σ y(t) · m(t) / Σ m(t)², i nivå.
- **Val av N:** kandidater är de N i rutnätet som har minst 12 träningsrader. Kandidaterna jämförs på sina gemensamma
  rader (raderna för den största kandidaten), med c skattat på samma rader. Lägst MAE i stickprovet,
  100 × |log(c · m(t)) − log y(t)|, vinner, och vid lika vinner det mindre N. Därefter skattas c på nytt på alla
  träningsrader för det valda N.
- **Framtida capex:** ett kvartal efter bolagets senast kända capexkvartal Lc får bolagets B1-bana från prognosdagen,
  capex(Lc) × exp(k × medel av de 4 senaste log-tillväxterna), där k = antal kvartal efter Lc. Utan 4 tillväxttal finns
  ingen V1.
- Saknas kandidater finns ingen V1 på prognosdagen. Varianten registreras som saknad och fylls inte i.

**V2 i detalj.** N_bolag = `useful_life_servers_<bolag>_hi`, det värde som gäller för det senaste angivna kvartalet
bland raderna med known_from ≤ prognosdagen (en stegfunktion, samma som `useful_lives.in_effect`). P2a rekommenderar `hi`
för N7. J_bolag = avrundat 4 × N_bolag kvartal, och för N7 har varje bolag sitt eget J i m(t). Samma N gäller för alla
träningsrader och för prognosen. Framtida capex som i V1. V2 saknas om något bolag i enheten saknar en angiven period på
prognosdagen eller har färre än 12 träningsrader. Enligt täckningen är perioden känd från 2019-02-05 (GOOGL), 2018-02-02
(AMZN), 2020-07-30 (MSFT) och 2022-02-03 (META).

**Utvärdering.**
- Per enhet från den första prognosdagen där V1 kan bildas, till och med 2026-10-20 (rolling origin, expanderande
  fönster). En rad är (enhet, prognosdag, h) där första versionen av L + h finns, inte var känd på prognosdagen och inte
  är ett brottkvartal.
- **Definitionsbrott (F-B8, som N4 och D2):** ett kvartal vars första inlämning räknar om ett tidigare kvartal av
  bolagsserien med mer än 2 % poängsätts inte, och B1:s fönster (tillväxttal som slutar i L − 3, …, L) får inte
  innehålla ett brott som är känt på prognosdagen. För N7 gäller alla fyra bolagens brott. Enligt täckningen är
  brottkvartalen MSFT 2025Q4–2026Q3 (den deklarerade omräkningen 2026-01-28 och de följande inlämningarna), AMZN 2023Q1
  och 2023Q4 och META 2014Q1–Q2. Träningsraderna har ingen brottregel.
- **Urval per variant:** varje variant utvärderas på de rader där varianten, B0 och B1 finns. Jämförelsemodellen är den
  bästa av B0 och B1 efter MAE på samma rader (vid lika B0). N7 har ingen tidigare huvudmodell, och V1 och V2 bygger inte
  på någon registrerad modell, så F-B10 ger samma jämförelsemodell.
- **Horisontgrupper:** h1–2, h3–4 och h5–8, som D2. n i en grupp = antalet olika prognosdagar (D2-posten 2026-11-24).
  MAE och bias per h redovisas som information.
- **Perioder:** hela perioden och från 2023, det vill säga prognosdagar från 2023-04-20 (den första där h = 1 är
  2023Q1).

**Test.**
- Diebold–Mariano på absolutfel per grupp och period. d = |fel variant| − |fel jämförelsemodell| per rad. Medlet tas
  över raderna (samma som den poolade MAE:n). Variansen är Newey–West (Bartlett) på summan per prognosdag av d minus
  medlet (Driscoll–Kraay, som `engine.pooled_dm`), med prognosdagarna i tidsordning. Fördröjningen är
  max(⌊4(T/100)^(2/9)⌋, h_max − 1), där h_max är gruppens största h, eftersom prognoser upp till h kvartal framåt
  överlappar. HLN-korrektion med h = h_max, p ur t-fördelningen med T − 1 frihetsgrader. T = antal prognosdagar.
- Inget test (p = 1) vid T < 8 eller när HLN-termen är ≤ 0.
- **Holm-familjen** är {V1, V2} × {h1–2, h3–4, h5–8}, alltså 6 tester, och Holm görs över dem i varje period för sig.
  Ett test som inte kan göras ingår med p = 1.
- MDE = 2,8 × SE redovisas per test.

**Beslut.**
- Per horisontgrupp, med N1:s stränga läsning (F-B11): en variant klarar gruppen om den i båda perioderna har lägre MAE
  än jämförelsemodellen och Holm-p < 0,10. Annars förblir B1 huvudmodell för gruppen.
- **Vilken utvärdering som avgör:** N7 för en grupp när N7 har minst 8 prognosdagar med varianten i gruppen i båda
  perioderna, annars N7b. Enligt täckningen kan V1 för N7 bildas först 2026-04-20 (`dep_hyp4` från 2023Q1, och
  Alphabets kvartal 2023 blev kända först 2024), och B1 för N7 stoppas 2026 av MSFT:s brottkvartal. **N7b avgör alltså i
  denna backtest, och N7 redovisas.** Det är en avvikelse från N1, där N1b bara redovisades. Utan den regeln kan N7 inte
  avgöras på flera år.
- Klarar båda varianterna en grupp väljs den med lägst MAE på de rader där båda finns.
- En variant som klarar regeln är ett **villkorat** resultat. Den kräver ett oberoende granskningsspår innan den används
  (CLAUDE.md), och V2 dessutom granskningen av P2a:s extraktion. Inga skarpa prognoser skrivs i spåret.

**Holdout (G-E).** V1 och V2 är enkla registrerade varianter med högst två parametrar (N och c) som skattas på
expanderande fönster. De är inga komplexa metodfamiljer som C3, C4 och D2. De utvärderas därför över hela perioden med
Holm, som C2. Rader med prognosdag i holdouten (2025-07-01–2026-10-31) ingår, och antalet redovisas som information.

**Intervall (G-C med F-C7):** en felpool per enhet, modell och h, och ett fel ingår först från sitt utfalls known_from.
Det redovisas som information och avgör ingenting.

**Korta serier.**
- Amazons bruttocapex (`capex_amzn`) börjar 2017Q3, och därmed också `capex_hyp4`. För N7 måste J kvartal av alla fyra
  bolagens capex ligga före t. För `dep_hyp4`:s första kvartal 2023Q1 räcker det till J = 22 (N ≤ 5). N = 6 blir möjligt
  från t = 2023Q3 och N = 10 först från 2027Q3.
- Den större begränsningen är målet. `dep_hyp4` börjar 2023Q1 (Alphabets definition) och ger 12 träningskvartal först på
  prognosdagen 2026-04-20. Därför går N7 inte att testa i backtesten.
- N7b har längre historik. META (avskrivningar och capex från 2011Q3) och MSFT (avskrivningar från 2010Q3, capex från
  2008Q3) ger V1 från ungefär 2014–2017, AMZN från 2023 (capex från 2017Q3 + J + 12 rader) och GOOGL från 2026. N7b är
  den enda utvärderingen med statistisk styrka, och den domineras av META och MSFT.

**Varför ingen V3.** En variant med bolagens capexguidance som framtida capex registreras inte. Guidance finns bara för
Metas och Alphabets capex, Alphabets mål börjar 2023, och framtida capex väger högst 7/J i m(t). Varianten skulle kosta
tre platser i Holm-familjen för mycket liten styrka, som R6 konstaterade om N1:s B3.

**Ärliga noter.**
- Bolagens rader har olika innehåll: MSFT inklusive "other", AMZN inklusive innehåll och operationell leasing, META
  inklusive immateriella tillgångar och GOOGL bara avskrivningar. c tar upp ett konstant förhållande, inte en ändrad mix.
- Capex är betalningar, inte tillgångar som tagits i bruk. Finansiell leasing (stor hos Amazon) ingår inte i capex men
  ingår i avskrivningarna.
- Bolagens egen guidance för avskrivningar är inte extraherad. Jämförelsen med guidance (arbetsregel 4) saknas för N7.

### 2026-11-24 – P1: omräkning genom summorna, delvis omräkning och ändringar efter första bygget (rättning efter granskning R14)

Tillägg till posten "P1: avskrivningar och anläggningstillgångar som katalogserier". Den posten skrivs inte om.
Granskning: `docs/granskning/r14_avskrivningar.md`. Rättningsspår X11 (`auto14/x11-avskrivningar`).

**Skäl (R-1).** Microsoft räknade om 2024Q3 (Q1 FY2025) bara genom sexmånaderstalet i 10-Q:n 2026-01-28: 12 383 − 5 667
= 6 716, mot 7 383 tidigare. I `sec.py` vinner ett direkt tremånadersvärde alltid över en differens, så `dep_msft`
behöll 7 383 i alla versioner. Det följer inte postens egen regel att omräkningar är versioner.

**Ny regel: omräkning genom summorna.** Gäller alla flödesserier i P1 (`dep_*`, `dep_ppe_*` och `dep_aws`), inte
övriga SEC-serier.
- När en 10-Q har både ett hittills-i-år-värde (start s, slut e) och ett tremånadersvärde som slutar e, ger skillnaden
  hittills-i-år-värdet för perioden från s till förra kvartalets slut. Värdet blir en version daterad till inlämningen
  (`sec_custom.implied_by_ytd`).
- Det används bara om inlämningen inte själv redovisar perioden, om ett värde för perioden redan har lämnats in (regeln
  skapar inga nya perioder), och om skillnaden mot det senast inlämnade värdet är större än avrundningen av de tre talen
  (en halv redovisningsenhet vardera: 1,5 MUSD för tal i miljoner, 150 MUSD för tal i 0,1 miljard).
- 10-K används inte, eftersom deras tremånadersvärden är den oreviderade kvartalsnoten.
- Härledda värden prövas av stoppregeln som andra värden. En omräkning över 2 % som bara syns i summorna ska alltså
  också deklareras.

**Effekt.** Två värden ändras, båda i `dep_msft` och därmed `dep_hyp4`: 2024Q3 får versionen 6 716 den 2026-01-28, och
2025Q3 på den nya basen (8 147) är känd från 2026-01-28 i stället för 2026-10-28. `dep_hyp4` 2024Q3 blir 28 170 (i
stället för 28 837) från 2026-01-28. Tabellen får två rader till (1 063). Första versionen av varje kvartal är
oförändrad. Inga andra serier ändras, och inga nya brott över 2 % uppstår. Med bara `sec.TOL` som gräns i stället för
avrundningen hade regeln gett 11 rader till som bara är avrundning (`dep_ppe_meta` och `dep_ppe_hyp4`, 10 MUSD fram
och tillbaka).

**Delvis omräkning (R-5).** Postens två regler pekar åt olika håll när ett bolag räknar om en del av historiken. Det
gäller:
- En deklarerad omräkning behåller nyckeln. Kvartal som bolaget inte räknade om, varken direkt eller genom summorna,
  ligger kvar på den gamla basen. Seriens not anger det sista kvartalet på den gamla basen i den senaste versionen.
  För `dep_msft` är det 2024Q2: FY2024 räknades bara om som helår (22 287 till 20 958), och det går inte att fördela
  på kvartal.
- "En serie har en definition" gäller när raden byter innehåll och inga tidigare perioder räknas om (Amazon 2019,
  Alphabet 2023). Då börjar serien vid den nya definitionen.

**Summornas definitioner (R-2).** `dep_hyp4` summerar fyra definitioner: Microsofts rad med "other" (till och med 2024Q2
på den gamla basen), Amazons rad med aktiverat innehåll och operationella leasingtillgångar, Metas rad med amortering på
immateriella tillgångar, och för Alphabet bara avskrivningar på anläggningstillgångar. Katalognoten säger detta och
hänvisar till `dep_ppe_hyp4` för jämförbar definition.

**Ändringar efter första bygget (R-6).** Båda gjordes i P1 efter förregistreringen och står i koden och källdokumentet:
- CoreWeave rapporterade i tusental till 10-K för 2025 och i miljoner därefter. En senare version som bara avrundar
  till hela miljoner tas bort (`neoclouds.rounding_revisions_dropped`, alla fyra CRWV-serier). Filtret tar bort en rad:
  `dep_crwv` 2025Q2, 560 den 2026-08-12 efter 559,481.
- Alphabets taggar läses för perioder från 2021-01-01 (`first_start`), inte från 2023Q1 som posten säger. Värdena blir
  desamma, eftersom 2021–2022 bara finns som helår med den nya taggen.

### 2026-11-24 – M1: AI-relaterat bidrag till BNP-tillväxt och priser (definitioner, före beräkning)

Spår M1, förslag 4 i [riktning.md](riktning.md). Serierna är beskrivande och blir **inte kärnserier**. Om de ska ingå i
en grens index är det ett G-A-beslut senare. Inga takter eller tillstånd är beräknade.

**Vad som har setts före registreringen.** För att hitta tabeller, koder och filformat lästes tabellhuvuden och det
senaste kvartalets värde i BEA:s förhandsberäkning för 2026Q3 (2026-10-29) och för 2017Q3 (2017-10-27), och de senaste
16 månaderna i BLS-filerna för de fyra prisserierna. Ingen historik och ingen takt har räknats.

**BEA, kvartal, SAAR.** Riktiga vintages ur BEA:s releasearkiv (`apps.bea.gov/histdata`, NIPA, en katalog per
BNP-release med alla tabeller som de publicerades). Arkivets filer är xlsx från 2017-10-27. Den senaste releasen läses
också från `apps.bea.gov/national/Release/XLSX/Survey/`. known_from = datumet "Data published" i tabellhuvudet.
Katalognamnet används inte: det avviker i två fall (2018Q4: katalog 2019-03-01, publicerad 2019-02-28; 2025Q3:
katalog 2025-12-22, publicerad 2025-12-23). Perioder före första arkiverade vintage får den vintagens datum, vilket är
konservativt.

- **`ai_invest_contrib_gross`** = bidraget till procentuell förändring i real BNP från informationsbehandlingsutrustning
  (NIPA-tabell 1.5.2, rad 31, `Y034RY`) + bidraget från programvara (rad 38, `B985RY`). Procentenheter i årstakt.
  Båda talen tas ur samma vintage. BEA avrundar till två decimaler, så summan kan avvika högst 0,01 procentenhet från
  ett oavrundat värde.
- Komponenterna lagras separat: `us_gdp_contrib_info_proc_eq` (`Y034RY`), `us_gdp_contrib_software` (`B985RY`) och
  delmängden datorer och kringutrustning, `us_gdp_contrib_computers` (rad 32, `B935RY`).
- Skala: `us_gdp_real_growth` = real BNP-tillväxt i årstakt (rad 1, `A191RL`, samma tal som tabell 1.1.1 rad 1).
  Ingen kvot mellan bidraget och BNP-tillväxten definieras, eftersom den är instabil när tillväxten är nära noll.

**Ingen nettovariant.** BEA publicerar importens bidrag till BNP-tillväxten bara uppdelat på varor och tjänster (tabell
1.5.2, rad 49–51). För import av datorer, kringutrustning och delar finns bara bidraget till den reala importens
tillväxt (tabell 4.2.2, rad 35, `B852RZ`), inte till BNP:s. Att räkna om det med importens andel av BNP vore vår egen
approximation, eftersom Fisher-vikterna skiljer sig mellan aggregaten. Den registreras inte nu. Datorimporten visas i
stället separat:
- `us_imp_computers_nom`: import av datorer, kringutrustning och delar, MUSD i löpande priser (tabell 4.2.5 och
  4.2.5B, `B852RC`).
- `us_imp_computers_real`: samma i kedjade dollar (tabell 4.2.6 och 4.2.6B, `B852RX`). Basåret följer vintage
  (2009, 2012 eller 2017), så nivån jämförs bara inom en vintage.
- `us_imp_computers_contrib_imp`: bidraget till procentuell förändring i real import (tabell 4.2.2, `B852RZ`),
  procentenheter.

**Förbehåll: kategorierna är bredare än AI.** Informationsbehandlingsutrustning omfattar alla datorer,
kommunikationsutrustning, instrument och kontorsutrustning. Programvara omfattar all köpt, beställd och egenutvecklad
programvara, men inte programvara som ingår i köpt utrustning. Datorimporten omfattar även persondatorer och tillbehör.
Ett bidrag på x procentenheter betyder alltså inte att AI bidrog med x.

**BLS, månad, index.** Flatfiler på `download.bls.gov` (med deklarerad User-Agent). Releasedatum ur BLS arkiv över
nyhetsreleaser (`www.bls.gov/bls/news-release/cpi.htm` och `ppi.htm`, referensmånad och releasedag i filnamnet).
- `us_cpi_electricity_nsa_m` (`CUUR0000SEHF01`) och `us_cpi_electricity_sa_m` (`CUSR0000SEHF01`): KPI-U för el,
  USA-genomsnitt, 1982–84 = 100. G7.
- `us_ppi_data_processing_m` (`PCU518210518210`): PPI för databehandling, hosting och relaterade tjänster (NAICS
  518210), ej säsongsrensat. G4, eftersom PPI mäter det pris som producenterna, alltså moln- och hostingbolagen, får.
- `us_ppi_elec_commercial_m` (`PCU22112222112242`): PPI för eldistribution till kommersiella kunder, ej
  säsongsrensat. G7. Det är samma kundsektor som EIA:s kommersiella elpris.

**Dateringsregler för BLS:**
- KPI NSA är slutlig när den publiceras. known_from = releasedagen för referensmånaden enligt arkivet. En månad utan
  egen release (oktober 2025) får nästa releasedag. Månader före arkivet (före 2002-05) får arkivets första releasedag.
  Ett värde med fotnoten R (reviderat) får datumet för den fil vi läser.
- KPI SA: säsongsfaktorerna revideras varje februari för de fem föregående åren. Ett värde i år y får releasedagen för
  januari-KPI år y + 5, eller den senaste januari-releasen före hämtningen om y + 5 inte har kommit. Månader i
  innevarande år får sin första releasedag.
- PPI: alla index kan revideras varje månad i upp till fyra månader efter publicering. Ett värde med fotnoten P
  (preliminär) får datumet för den fil vi läser, alltså den senaste PPI-releasen. Ett slutligt värde får releasedagen
  för referensmånad m + 4. En referensmånad utan egen release och månader före arkivet behandlas som för KPI.
- Filens datum = max(senaste releasedag i arkivet, filens Last-Modified).
- Regeldaterade rader märks `backfill`. Från andra hämtningen blir varje ändrat värde en `revision` med hämtdatum.

### 2026-11-24 – M1: rättelser av fakta i registerposten ovan (efter hämtningen, reglerna ändras inte)

Tre faktauppgifter i posten "M1: AI-relaterat bidrag till BNP-tillväxt och priser" var fel. Reglerna gäller oförändrade.
- BEA:s senaste release ligger under `apps.bea.gov/national/Release/XLS/Survey/` (xlsx-filer trots namnet), inte
  `XLSX/Survey/`. Den sökvägen svarar med HTTP 200 och en HTML-sida.
- Katalognamnet i BEA:s arkiv avviker från "Data published" i nästan alla releaser 2017–2025, inte bara i två.
  Oftast ligger katalogen 1–3 dagar efter publiceringen. I två fall ligger den före: 2025Q3 (en dag) och 2023Q1 Third
  (katalog 2023-06-20, publicerad 2023-06-29). Regeln att datera med "Data published" står kvar.
- BLS arkiv över nyhetsreleaser börjar med referensmånad 1999-05, inte 2002-05.

Dessutom lagras KPI för el (NSA) från 1952-01, där den månatliga serien börjar och där SA-serien börjar. Före det
finns bara enstaka månader. Oktober 2025 samlades aldrig in och blir en känd lucka i båda KPI-serierna.

### 2026-11-24 – M1: rättningar efter granskning R12 (rättning efter docs/granskning/r12_makro.md)

Granskningen R12 hittade två fel och några brister i M1. Rättningsspåret X9 (gren `auto14/x9-makro`) ändrar reglerna
nedan. Posterna ovan står kvar som de skrevs. Inga takter eller tillstånd är räknade, och serierna är fortfarande
beskrivande.

- **Ingen datering före första publiceringen (R-1).** Ett BLS-värde får known_from = max(regeldatum, seriens första
  publiceringsdag). PPI 518210 infördes med PPI-releasen 2002-02-15 ("7374 Data processing services*", "* denotes
  newly introduced PPI"), men filen har värden från 2000-12. Effekt: 9 värden, 2000-12 – 2001-08, flyttas från
  2001-05-11 – 2002-01-11 till 2002-02-15. Inga värden ändras.
- **BEA-serierna visar bara perioder som finns i den senaste vintage (R-2).** En omfattande revision kan ta bort de
  äldsta kvartalen när basåret för kedjade dollar byts. Med de gamla kvartalen kvar blandade `us_imp_computers_real`
  2009, 2012 och 2017 års dollar i varje vy efter 2018-07-27. Effekt: `us_imp_computers_real` börjar 2007Q1, och 52
  rader för 1999Q1 – 2006Q4 tas bort. De övriga 7 BEA-serierna har inga borttagna perioder och ändras inte. Om en ny
  release tar bort en lagrad period stoppar hämtningen med ett fel, och serien byggs om medvetet (`--rebuild`).
- **Premissen för "ingen nettovariant" var ofullständig (R-3).** BEA publicerar ett nettobidrag för datorer: tabell
  1.2.2 rad 17, "Final sales of computers" (`BB01RY`), där importen dras ifrån. Det omfattar datorer och
  kringutrustning, också hushållens, men inte programvara. Ett nettomått för hela `ai_invest_contrib_gross` finns
  fortfarande inte. Ingen ny serie registreras här. Om `BB01RY` ska förregistreras är det ägarens beslut.
- **BLS arkiv över nyhetsreleaser börjar med referensmånad 1994-01 (R-5).** Rättelsen ovan ("1999-05") var fel. Före
  1999-05 har filnamnen sex siffror (`cpi_051499.txt`), och nu läses de också. Regeln "månader före arkivet får
  arkivets första releasedag" står kvar. Effekt, inga värden ändras:
  - KPI NSA 1994-01 – 1999-04 får sin releasedag i stället för 1999-06-16.
  - PPI 1994-01 – 1999-04 får release m + 4 i stället för 1998-12-11 eller 1999-06-11.
  - Värden före 1994 får arkivets första releasedag: KPI 1994-02-17 i stället för 1999-06-16, och PPI 1994-02-11 i
    stället för 1998-12-11. KPI SA för 1989–1993 får januari-releasen år y + 5 (1994–1998).
  - **Läckagerisk:** när BLS först publicerade den säsongsrensade elserien bakåt till 1952, och PPI för kommersiell el
    före 1990 (bas 12/90, värden från 1958), är inte verifierat. De värdena dateras nu 5 år tidigare än förut. Ingen
    analys använder dem.
- **Filens datum utan Last-Modified (R-6).** Om svaret saknar `Last-Modified` och filen har en månad som arkivlistan
  ännu inte har, är filens datum hämtdagen, inte föregående release. Ingen effekt i dag, eftersom `download.bls.gov`
  skickar `Last-Modified`.
- **Katalognamnet i BEA:s arkiv** ligger 0–4 dagar efter "Data published" i 105 av 107 releaser, inte 1–3 dagar som i
  rättelsen ovan (R-7). Dateringsregeln ändras inte.

Dessutom gäller undantaget för luckor i KPI-serierna nu bara oktober 2025 (`warehouse.KNOWN_GAP_PERIODS`, R-4). En
andra lucka rapporteras.

### 2026-11-24 – F1: revideringar av guidance och överraskning mot guidance (förregistrering, före beräkning)

Spår F1 (förslag 2 i `docs/riktning.md`). Två mått på hur bolagens egna planer ändras och hur utfallet hamnar mot dem.
Inga revideringar, inga överraskningar och inga index har beräknats på verklig data före denna post.

**Vad som var synligt före posten.** Enligt uppdraget lästes `curated/guidance_capex.csv`, så capex-guidancens värden
var synliga. Fönstret för indexet valdes ur **antalet** uttalanden per kvartal i CSV:n (inte riktning eller storlek):
0–5 per kvartal 2021Q1–2026Q4, färre än 3 i 14 av 24 kvartal. För TSMC:s capex-budget lästes de matchade meningarna
och de omatchade kandidatmeningarna för att kontrollera tolkningen (avsnittet nedan). TSMC:s och Nvidias
intäktsguidance och alla utfall har hämtats men inte lästs.

**Objekt och uttalanden**

| Del | Regel |
|---|---|
| Objekt | (bolag, mått, guidad period, definitionskod). Capex ur CSV:n: `company`, `horizon` + `period`, `definition`. TSMC: kvartalsintäkt i angiven valuta (`TSMC_REV_TWD` t.o.m. 2017Q2, `TSMC_REV_USD` från 2017Q3) och årets capex-budget (`TSMC_CAPEX_USD`). Nvidia: kvartalsintäkt (`nvda_guid_rev_mid`), kvartal från 2017Q2 (granskade i R5, som i B3). Marginaler och växelkurs ingår inte |
| Kedjor | Inom ett objekt hålls siffror (point, range, approx; mittpunkten, för approx och point värdet), lägsta gränser (min) och riktningar per `direction_base` isär. Bara uttalanden i samma kedja jämförs |
| Uttalande | Capex ur CSV:n: varje rad, med `known_from` = `filed`. En rad som upprepar förra värdet i ett senare dokument är alltså ett uttalande. TSMC och Nvidia: varje vintage i observationstabellen. Där ger en upprepning ingen vintage |
| Definitionsbrott | En rad med ett dokumenterat brott mot föregående rad i samma objekt startar ett nytt objekt. Listan är låst här: `msft-29` (R5-F14, smalare bas för `MSFT_CAPEX_INCL_FL` från samtalet 2026-07-29). Den utökas bara med en ny post |

**Revidering**

- En **revidering** är ett uttalande i en kedja som redan har ett tidigare uttalande, minst 7 dagar efter det. Ett
  uttalande inom 7 dagar räknas som samma händelse: ingen revidering, men det blir kedjans jämförelsevärde.
- **Storlek** (siffror och lägsta gränser) = 100 × (ln nytt värde − ln förra värdet). **Uppåt** om storleken ≥ 1,
  **nedåt** om den ≤ −1, annars **oförändrad** (dödband |storlek| < 1).
- **Riktning** (kodade kvalitativa besked): koden jämförs med förra koden. Högre är uppåt, lägre nedåt, samma är
  oförändrad. Ingen storlek.
- **Ingen revidering:** det första uttalandet i en kedja. TSMC:s och Nvidias kvartalsguidance, som ges en gång per
  kvartal, är alltså ett nytt objekt. Bara en senare vintage för samma kvartal (en uppdatering mitt i kvartalet, eller
  2015Q4:s preliminära intervall som ersattes) är en revidering. Den första siffran efter bara riktningar är inte heller
  en revidering, och inte heller en siffra med en ny definitionskod (till exempel Amazons 220 mdr som `AMZN_CASH_CAPEX`
  efter 200 mdr som `AMZN_CAPEX_UNSPEC`).
- **Varför upprepningar räknas för capex:** som i PMI ger ett oförändrat besked 0,5. Ett bolag som i en ny rapport står
  fast vid sin plan har gjort ett val. CSV:n har en rad per rapporttillfälle. TSMC:s och Nvidias kvartalsguidance har
  inget sådant tillfälle, och TSMC upprepar sedan 2016 inte capex-budgeten i 6-K.

**Revideringsindex**

- **D = (antal uppåt + 0,5 × antal oförändrade) / antal**, alla bolag och mått sammanslagna, efter kalenderkvartalet
  för `known_from`. Två fönster: kvartalet, och kvartalet med de tre föregående (rullande 4 kvartal).
- **Huvudmått: rullande 4 kvartal.** Skälet är antalet per kvartal ovan. Kvartalsindexet redovisas bredvid.
- Med **n < 3** finns inget index, men n redovisas. Medianstorleken räknas över revideringar med storlek, och deras
  antal redovisas.
- **Period:** från 2020Q3, när den kurerade capex-filen börjar (dokument från 2020-07). TSMC:s revideringar före dess
  finns i händelsetabellen och i antalet per bolag och år, men i ingen indexperiod.
- **Versioner:** en ny version vid varje händelse i kvartalet som ändrar antalen eller medianen, och en vid kvartalets
  sista dag om kvartalet ännu saknar version och dagen har passerat. `known_from` = det datumet.

**Överraskning mot guidance**

| Bolag | Utfall U (första versioner) | Guidance G | Från |
|---|---|---|---|
| TSMC, kvartalsintäkt | summan av kvartalets tre månader i `tsmc_revenue_m` (NT$), känd när den sista månaden är känd | N2:s B2-regel (`n2.quarter_guidance`): NT$-mittpunkten t.o.m. 2017Q2, US$-mittpunkten × antagen växelkurs från 2017Q3 | 2006Q2 |
| Nvidia, kvartalsintäkt | `rev_nvda` | `nvda_guid_rev_mid` | 2017Q2 |
| Meta, capex för kalenderåret | `capex_meta` + `fin_lease_meta`, årets fyra kvartal | mittpunkten för `META_CAPEX_INCL_FL` (range, approx, point) | 2021 |
| Alphabet, capex för kalenderåret | `capex_googl`, årets fyra kvartal | mittpunkten för `GOOGL_CAPEX` | 2025 |

- **G** = den senaste guidancen som var känd **före** utfallet (as_of dagen före U:s `known_from`).
  **s = 100 × (ln U − ln G).**
- **Inte med:** Amazon (guidance netto efter incitament eller utan angiven bas, `capex_amzn` är brutto), Microsoft
  (inklusive nya finansiella leasingavtal vid start, och kvartalssiffrorna är lägsta gränser), TSMC:s capex-budget
  (inget utfall i US$ i katalogen) och alla riktningar.
- **z = s / SD av bolagets egna tidigare överraskningar** (ddof 1), där utfallet var känt före detta utfall. Det krävs
  minst 4. Inget medelvärde dras av, så en systematisk avvikelse finns kvar i z. Percentilen mot egen historik visar
  om den är ovanlig.
- **Överraskningsindex per kalenderkvartal** = medel av de z som är kända. Det krävs minst 2 bolag. Årets capex räknas
  i årets fjärde kvartal och Nvidia i sitt kalenderkvartal (mittpunktsregeln). En version per komponent som blir känd,
  med `known_from` = den senaste komponentens (som A5). Antalet redovisas.
- För TSMC från 2017Q3 innehåller s också avvikelsen från den antagna växelkursen. Det är B2:s bas, och det redovisas
  så.

**Gruppen "Förväntningar mot utfall"**

- Måtten mäts och visas, men räknas **aldrig** i en grens diffusionsindex, och regimmodellen (G-D) använder dem inte.
- **Ingen takt.** De mäter redan förändring. Nivå och percentil mot egen historik (versioner kända på beräkningsdagen,
  minimihistorik som i avsnitt 1: 8 kvartal, 5 år). Ett eget avsnitt `expectations` i månadens ögonblicksbild.
- Gren i katalogen: revideringsindex och capex-överraskningar G5, intäktsöverraskningar och överraskningsindex G6.
  Grenen är bara en etikett här.

**TSMC:s capex-budget (deterministisk tolkning, ingen LLM)**

- Källa: samma 6-K som `tsmc_guidance` läser. En strikt meningsform: året och "capital expenditure(s)", "capex" eller
  "capital budget", ett verb (to be, will be, expected to be, to remain), sedan about, around, approximately, between
  eller in the range of/between, och ett belopp i US$. Året ska vara inlämningsåret eller nästa år.
- Andra ordalydelser kodas inte, till exempel "slightly above US$9.5 billion" (2016-10-13) och "near the mid point".
- Serier `tsmc_guid_capex_lo/hi` (år, MUSD, vintages som övriga TSMC-guidance). Kontrollen av tolkningen gällde
  meningarnas form, inte revideringarna.

### 2026-11-24 – F1: brottet flyttas, stängningsversionen och känsligheter (rättning efter granskning R11)

Spår X8 rättar fynden i `docs/granskning/r11_revideringar.md`. Posten "F1: revideringar av guidance och överraskning
mot guidance" ovan skrivs inte om. Här står vad som ändras, varför och effekten. Alla värden nedan var kända från
granskningen innan posten skrevs. Posten är alltså en rättning, inte en förregistrering.

**1. Definitionsbrottet flyttas från `msft-29` till `msft-r11f1` (R11-1).** Detta är en regeländring efter att värdena
var synliga. Skälet är primärkällan, inte utfallet. I samtalet 2026-07-29 (FY2026 Q4) säger Microsoft att förväntningen
för kalenderåret 2026 är oförändrad utom effekten av den nya nyttjandeperioden (mening #227), och att skiftet till
operationell leasing justerar den till cirka 175 mdr (#228). CSV:n saknade den siffran. Raden `msft-r11f1` läggs till
(SHA-256 `d8cfaeea…a9bb5a84`). Brottet ligger alltså mellan `msft-26` (190 mdr, gammal bas) och `msft-r11f1` (175 mdr,
ny bas). Listan över brott är nu `msft-r11f1`. `msft-29` (170 mdr, 2026-10-28) är en revidering nedåt på samma bas.
- Effekt: storleken för `msft-29` blir −2,9. Rullande 4 kvartal 2026Q4 går från 0,67 (n 12: 4/8/0) till 0,62
  (n 13: 4/8/1). Kvartalet 2026Q4 får ett index, 0,50 (n 3). Övriga kvartal ändras inte av detta.
- Känsligheter som redovisas bredvid: F1:s tidigare variant (brott på `msft-29`, utan julisiffran) 0,67, och "brottet
  ignoreras" (utan julisiffran och utan brott, −11,1 mot 190) 0,62.
- En rad som ett brott håller utanför jämförelsen redovisas i avsnittet `expectations` (`break_statements`) med sin
  storlek mot det senaste uttalandet före brottet. För `msft-r11f1` är den −8,2 mot `msft-26`. Raden är ingen
  revidering. Så kan ett brott aldrig dölja en ändring.

**2. Stängningsversionen (R11-2), ingen regeländring.** Koden följer nu registrets text: versionen vid kvartalets sista
dag skapas först när dagen har passerat. Den dateras fortfarande den sista dagen. En beräkning på kvartalets sista dag
har därför inte den versionen. Den kommer dagen efter.

**3. Två känsligheter, inga nya huvudmått.**
- **Bara siffror (R11-6).** Samma index och samma regler, men bara över revideringar med en siffra (kedjorna med siffror
  och lägsta gränser). Riktningarna är med i huvudmåttet, men 24 av 28 riktningshändelser i indexperioden är
  oförändrade. Känsligheten visar hur mycket de drar mot 0,5. Den redovisas i avsnittet `expectations` och i
  resultatet, tillsammans med antalet upp, oförändrade och ned för siffror och riktningar var för sig.
- **TSMC i US$ (R11-7).** Från 2017Q3. U = kvartalsintäkten i US$ ur pressmeddelandet i samma 6-K (deterministisk
  tolkning av meningen "In US dollars, <kvartal> quarter revenue was $x billion", serien `tsmc_rev_usd_q`). G =
  US$-mittpunkten känd dagen före U. Valutadelen = s(NT$) − s(US$) = 100 × (ln faktisk kurs − ln antagen kurs).
  Serien `f1_surprise_tsmc_usd`. Den ingår inte i överraskningsindexet. Huvudmåttet är kvar på B2:s bas (NT$).

**4. Data (R11-5).** Metas utsikt för 2020 (cirka 16 mdr, 8-K 2020-07-30 och 2020-10-29) läggs till i CSV:n. Raderna
ligger i indexperioden och räknas i revideringsindexet. Rullande 2021Q1 får ett värde (0,67, n 3) och 2021Q2 blir 0,60
i stället för 0,625. Metas överraskning börjar som registrerat 2021 (kolumnen "Från" ovan). 2020 används inte där.

**5. Publicering (R11-4).** F1-serier som läser CSV:n listar `guid_capex_*` som komponenter och har därför
`publish=False` så länge de har det. Ägaren avgör. Måtten ändras inte.

**6. TSMC:s capex-budget, förtydligande (R11-8).** Koden kräver att inget belopp och inget meningsslut står mellan
subjektet och verbet. Det stod inte i posten ovan. Tolkningen ändras inte. Kända okodade utsagor: alla för 2003,
2009-07-30 (höjningen dateras en dag sent, från 2009-07-31) och 2012-04-26 (en höjning med cirka +32 som saknas). Från
2022 står bara januaribudgeten i 6-K, så TSMC:s capex-budget ger inga revideringar efter 2021 i våra källor.

**7. Urval av kandidatmeningar för capex-guidance (R11-1).** Meningen efter varje mening med ett capex-ord är också en
kandidat (`guidance_capex.candidates`). Kontrollen `python -m ai_tracker.guidance_check --neighbours` listar sådana
meningar med ett belopp som inte är kodade.

### 2026-11-24 – M2: import av servrar, datordelar och halvledare per land (katalogserier, inte kärnserier)

Spår M2 (förslag 4 i `docs/riktning.md`). Posten låser serier, källor och datering innan något värde i serierna har
hämtats. Inga mått (takt, förändring i takt) räknas, och serierna ingår inte i grenarnas index. Att göra någon av dem
till kärnserie kräver en egen registerpost och en granskning. Gren G6. Publiceras: ja (Census, amerikanskt
federalt verk).

**Ländernas koder** (Census `CTY_CODE`): `tw` 5830 Taiwan, `mx` 2010 Mexiko, `vn` 5520 Vietnam, `my` 5570 Malaysia,
`th` 5490 Thailand, `cn` 5700 Kina, `world` hela världen (0000 i filen, `-` i API:t).

| Nyckel | Källa | Innehåll | Frekv. | known_from |
|---|---|---|---|---|
| `us_imp_eu{21300,21301,21320}_{tw,mx,vn,my,th,cn,world}_a` | `enduse_imports.xlsx` (Annual Country by 5-digit End-Use Code), ingen nyckel | import per land och end-use-kod: 21300 datorer, 21301 datortillbehör och datordelar, 21320 halvledare. MUSD per år, ej säsongsrensad | A | 31 dec + 191 dagar (10 juli året efter) |
| `us_imp_hs{8471,847150,847180,847330,8542}_{tw,mx,vn,my,th,cn,world}_m` | Census API `intltrade/imports/hs`, kräver `CENSUS_API_KEY` | `GEN_VAL_MO` (general imports, totalvärde) per land och HS-kod: 8471 alla datorer och enheter, 8471.50 processorenheter, 8471.80 andra enheter, 8473.30 delar till 8471, 8542 integrerade kretsar. MUSD, ej säsongsrensad, från 2013-01 | M | max(månadsslut + 41 dagar, sena FT-900-releaser i `census_trade.LATE`) |

**Datering och läckage:**
- *Årsfilen* byts ut vid FT-900:s årsrevision och har ingen versionshistorik. Årsrevisionen kom 4–9 juni 2018–2026
  (`final_YYYY.pdf`, "FOR RELEASE"). Filens Last-Modified på servern är 2026-06-09 12:31 GMT, samma minut som
  releasen (8:30 EDT). Att äldre versioner av filen kom vid samma release går inte att verifiera, så regeln har en
  månads marginal. Hela historiken 2016–2025 är backfill med vintage 2026-06-09.
- *HS-serierna* släpps med FT-900 och dateras därför som `us_imports_tw_m`. API:t har bara senaste vintage, så första
  hämtningen är backfill. Ändrade värden blir revisioner med hämtdagen som `known_from`.
- En månad inom svarets period som saknar post för ett land och en kod räknas som 0. Antagandet är att API:t bara har
  poster för handel som har ägt rum, och det kontrolleras vid första hämtningen med nyckel.

**Kända brott, skarvas inte:** HS 2017 (2017-01) och HS 2022 (2022-01). I HS 2022 kom den nya positionen 8524
(platta bildskärmsmoduler), som kan ha flyttat varor från 8473.30. Brotten noteras och analyseras inte här.

**Utan nyckel:** hämtningen av HS-serierna hoppas över (SKIPPED, inte FAILED), ingenting skrivs, och serierna
undantas från aktualitetskontrollen tills nyckeln finns (`ai_tracker.keyed`). Veckojobbet fallerar alltså inte.

**Inga nyckelfria månadsdata per land:** Census nyckelfria end-use-sidor har månadsdata bara för hela världen
(FT-900 Exhibit 8, säsongsrensad) och per land bara som årssummor. Därför är årsfilen den nyckelfria leveransen.

### 2026-11-24 – M2: nollregeln, brottet i end-use-klassificeringen och Census-notisen (rättning efter granskning R13)

Tillägg till posten "2026-11-24 – M2: import av servrar, datordelar och halvledare per land". Den posten skrivs inte
om. Granskning: `docs/granskning/r13_census_hs.md`. Rättningsspår X10 (`auto14/x10-census-hs`). Inga HS-data har
hämtats, eftersom ingen session har haft `CENSUS_API_KEY`. Ändringen görs alltså innan något värde i HS-serierna har
setts.

**Nollregeln för HS-serierna (R13-1).**
- *Skäl.* Regeln var "en månad inom svarets period som saknar post räknas som 0". Koden fyllde nollor över båda svarens
  gemensamma period, landanropet och världsanropet tillsammans. Om svaren slutar på olika månader, till exempel om
  releasen sker mellan de två anropen, får alla 30 landserier en falsk nolla för den månad som bara världssvaret har.
  Nollor efter seriens sista post döljer dessutom att en månad saknas.
- *Ny regel.* En månad mellan seriens egen första och sista post som saknar post räknas som 0. Månader före den första
  eller efter den sista posten fylls inte. De saknas tills en post kommer, och dateras då med den vanliga regeln, alltså
  efter den senaste hämtningen som saknade perioden.
- *Effekt.* Inga lagrade värden ändras, eftersom HS-serierna inte har några rader. En serie börjar vid sin första post i
  stället för vid svarets första månad. Guiden stöder att en saknad post betyder ingen handel (204 = ingen handel).
  Antalet månader utan post kontrolleras vid första hämtningen med nyckel
  (`python -m ai_tracker.sources.census_hs check`). Ändras regeln efter att data har setts, loggas det här med datum
  och motivering.

**Kända brott, tillägg (R13-4).** Årsserierna `us_imp_eu{21300,21301,21320}_*_a` har ett brott i end-use-klassificeringen
mellan 2018 och 2019. Census omklassificerade end-use-koderna från januari 2022 och lade in ändringen för 2019–2021 vid
årsrevisionen 2022-06-07 (`notices/20220308_enduse_changes.pdf`). 2016–2018 följer alltså den äldre klassificeringen och
2019–2025 den nya. För hela världen ändrades 2019 mellan årsrevisionerna 2021 och 2022 med +7 MUSD (datorer), −28 MUSD
(datortillbehör) och −301 MUSD (halvledare, −0,56 %). Effekten per land går inte att mäta. Brottet skarvas inte, och
inga värden ändras.

**Publicering (R13-2).** HS-serierna har kvar `publish=True`. Census API:s villkor ber om en notis på en framträdande
plats. Notisen ligger i `Spec.notice` och visas med seriens attribution (raden vid varje diagram och nedladdning) och i
den gamla sidans sidfot när någon serie med notis har rader.

**Hämtningen (R13-3, R13-6).** Ett misslyckat anrop sparas i processens cache, så en körning frågar API:t högst en gång
per svar. Ett anrop som får timeout eller 429/5xx efter två nya försök delas upp i ett anrop per år med samma form
(`time=from ÅÅÅÅ-01 to ÅÅÅÅ-12`, syntax enligt guiden). Data, datering och nollregel påverkas inte av uppdelningen.

### 2026-11-25 – W13: urvalsregel för månadens berättelse (före körning på verklig data)

Månadens berättelse på hemsidan (`/next/manad/<YYYY-MM>`, visionen avsnitt 3.4) är en följd av kort som väljs med
regeln nedan, inte med redaktionellt omdöme. Regeln skrivs innan den körts på verklig data. Under utvecklingen har den
bara körts på det syntetiska fixturpaketet. Regeln väljer och ordnar. Den beräknar inga nya mått: allt den läser finns
redan i posten, prognosfilerna eller C4-sektionen.

**Indata för månad M (och inget annat):**

- **Posten för M:** den skarpa ögonblicksbilden `snapshots/M.json` om den finns, annars rekonstruktionen vid M:s
  månadsslut med samma kod (`site.data.Record`), märkt *rekonstruerad*.
- **Jämförelseposten** för M−1 enligt samma regel. Saknas den (M är historikens första månad, eller M−1 är en lucka
  efter den första skarpa ögonblicksbilden) görs ingen jämförelse, och korten K1, K5 och K6 kan inte uppstå.
- **De committade prognosfilerna** i `forecasts/` (N1–N6) och scorecarden mot utfallets första version.
- **C4-sektionen** i M:s skarpa ögonblicksbild. Rekonstruerade månader har ingen sådan, så där uppstår inte K2 och K4.
- **Känd-dag** för M: månadsslutet, eller den skarpa ögonblicksbildens datum om det är senare. Inget värde med
  `known_from` efter känd-dagen används. Sidan kontrollerar det med tidsresans gräns (`web/src/lib/timetravel/gate.ts`).
- **Licens:** bara serier och mål som är publicerbara (`site.data.publishable`) får egna kort. Inhållna serier som
  uppfyller ett villkor räknas per korttyp, men de namnges inte och deras värden visas inte. Grenens tillstånd (K1)
  räknar med dem, som registrerat.

**Korttyperna och villkoren:**

| Typ | Kort | Villkor (alla måste gälla) |
|---|---|---|
| K0 | Läget | Visas alltid, först. Antal grenar per tillstånd i M och, om jämförelse finns, antal grenar med högre, lägre och oförändrat index mot M−1 (avrundat till två decimaler). Räknas inte mot taket |
| K1 | Tillståndsskifte | En gren vars tillstånd i M (accelererar, stabil, bromsar in, för få serier) skiljer sig från dess tillstånd i M−1 |
| K2 | Regimskifte | C4 rapporterar i M ett skifte för ett block (fältet `shift` satt för M), i någon riktning |
| K3 | Nytt skarpt utfall | En committad prognosfil med prognosdag ≤ känd-dagen vars utfall (första versionen) har `known_from` i M, alltså från M:s första dag till och med känd-dagen. Målet ska vara publicerbart |
| K4 | Strukturbrott | C4 rapporterar i M ett brott (BOCPD, G-D) för en publicerbar kärnserie |
| K5 | Kärnserie i extrem percentil | En räknad, giltig och publicerbar kärnserie i M:s post vars percentil för förändring i takt är ≥ 95 (övre zonen) eller ≤ 5 (nedre zonen), och som i M−1:s post inte låg i samma zon. Låg den i motsatt zon, saknade percentil eller räknades inte i M−1 gäller villkoret |
| K6 | Avstämning i extrem percentil | En publicerbar avstämning (A5) vars percentil för takt i M är ≥ 95 eller ≤ 5, och som i M−1 inte låg i samma zon (samma tolkning som K5) |
| K9 | Inga utslag | Visas när inget kort K1–K6 uppfyller sitt villkor. Kortet räknar upp de sex villkoren och säger att inget av dem uppfylldes i M (och, när jämförelse saknas, att K1, K5 och K6 inte kunde prövas). Det väljer inga ersättare |

Percentilerna är registrets (avsnitt 1: seriens egen historik fram till beräkningsdagen, 0–100, lika värden räknas
till hälften). För K5 används förändringen i takt, eftersom det är den som ger seriens riktning i diffusionsindex
(avsnitt 2). För K6 används takten, eftersom avstämningarna inte har någon riktning i ett index (A5) och takten är deras
huvudmått. Vid fördubblings- och halveringstid (G1, G2) betyder en hög percentil för förändringen en längre tid. Kortet
anger då riktningen med registrets tecken (kortare tid = accelererar).

**Ordning och tak:**

1. K0 först. Sedan korttyperna i ordningen K1, K2, K3, K4, K5, K6.
2. Inom typen:
   - K1: absolut indexförändring mot M−1, störst först (saknat index räknas som förändringen 0), sedan grenkod.
   - K2: blockens ordning i C4-sektionen.
   - K3: utfallets läge mot huvudmodellens lagrade centrala intervall: utanför 95 % före utanför 80 %, före utanför
     50 %, före inom 50 % (gränserna räknas som innanför). Sedan huvudmodellens absoluta fel, störst först, sedan
     prognosens id (n1–n6) och period. Saknas lagrade intervall räknas läget som okänt och sorteras sist inom typen.
   - K4: sannolikheten för kort körlängd (`p_recent`), störst först, sedan seriens nyckel.
   - K5 och K6: avståndet |percentil − 50|, störst först, sedan seriens nyckel.
3. **Tak per typ:** K4 högst 3, K5 högst 3, K6 högst 2. K1, K2 och K3 har inget eget tak.
4. **Tak totalt:** högst 8 kort av typerna K1–K6 per månad. Över taket stryks kort från slutet av ordningen. Antalet
   kort som uppfyllde villkoren men ströks (per typ, på grund av typens tak eller det totala taket) visas på sidan.

**Neutralitet:**

- Varje villkor och varje ordning är symmetrisk kring det neutrala: percentil 50 (≥ 95 och ≤ 5), tvåsidiga intervall,
  absolut indexförändring och skiften i båda riktningarna. Ingen ordning använder tecknet. Lika värden avgörs med kod
  eller nyckel, aldrig med riktning.
- Texten genereras ur data med registrets ord (accelererar, stabil, bromsar in, högre, lägre, över, under) och siffror.
  Inga värderande ord och inga larmord. Ett test prövar alla genererade texter mot månadsbrevets lista
  (`letter.BANNED_WORDS`) och en lista med larmord (larm, varning, kris, rekord, dramatisk, kollaps, ras, rusar,
  chock, oroväckande, alarmerande).
- Färg betyder bara riktning (visionen 4.4). Skarp eller rekonstruerad märks på varje månad och kort.

**Determinism:** inget klockslag och ingen slump. Samma post, prognosfiler och C4-sektion ger samma kort i samma
ordning, byte för byte.

**Utanför regeln:** revideringar, nya serier och nya prognoser utan utfall blir inga kort. De visas på serie- och
prognossidorna och i månadsbrevet. En ändring av regeln (trösklar, typer, ordning eller tak) görs som ett nytt daterat
avsnitt här, och den gäller då för alla månader, även de som redan visats.

#### 2026-11-25 – Ändring av W13 (R-W3a–c): dubbletter, slumpnivå och strukna kort

Motivering: granskningen R-W3 (`docs/granskning/rw3_neutralitet.md`, punkt 3) visade att samma storhet kan visas två
gånger samma månad (K5 för `capex_ocf_hyp4` och K6 för `x_capex_ocf` i oktober 2026), att K5 ger ungefär lika många
utslag som slumpen skulle ge, och att läsaren inte kan se vilka kort taket strök. Ändringen skrivs innan den
implementeras. Den gäller för alla månader, även de som redan visats. Trösklar, korttyper, ordning och tak ändras inte.

1. **R-W3a, dubbletter.** En avstämning vars definition i A5-tabellen är "befintlig `<kärnserie>`" (i dag bara
   `x_capex_ocf` = `capex_ocf_hyp4`) blir inget eget K6-kort när den kärnserien har ett K5-kort som visas samma
   månad. K5-kortet får i stället en mening om avstämningen: dess percentil för takt och om den ligger i en ytterzon.
   Prövningen görs när K1–K5 har valts (efter K5:s tak och det totala taket) och före K6:s tak, så att en struken
   dubblett inte tar någon plats. Den räknas som "uppfyllde villkoret" och redovisas i Om urvalet som "ströks som
   dubblett", inte som struken av taket. Har kärnserien inget visat K5-kort gäller K6 som förut. Regeln läser ingen
   riktning.
2. **R-W3b, slumpnivå.** När jämförelse finns anger Om urvalet för K5 och K6 hur många utslag som väntas av en slump:
   med N prövade serier ligger i snitt N/10 i en ytterzon (≤ 5 eller ≥ 95) om percentilerna är jämnt fördelade. N är
   för K5 de räknade och giltiga kärnserierna med percentil för förändring i takt i M, och för K6 avstämningarna med
   percentil för takt i M, publicerbara eller inte. Bredvid står hur många som uppfyllde villkoret (också inhållna
   och dubbletter). Kravet att serien inte låg i samma zon månaden innan gör att slumpens antal för själva villkoret
   är något lägre än N/10, och sidan säger det. Siffran väljer inte bort några kort.
3. **R-W3c, de som ströks.** Kort som uppfyllde villkoren men ströks av typens tak eller det totala taket listas i Om
   urvalet i regelns ordning, med typ, namn (gren eller serie, med grenkod för K5) och riktning med glyf (▲ eller ▼,
   ingen glyf när kortet saknar riktning), utan figur och utan färg. Inhållna serier namnges fortfarande inte.
4. **Texter (följer av R-W3 punkt 4 och 5).** Interna koder står inte i läsartexten: "(A5)", "(G-D, C4)" och
   "(BOCPD, G-D)" ersätts med vanliga ord och en länk till metoden. K5-texten börjar med en mening i klartext om
   percentilen ("Förändringen i takt är högre än i 98 % av seriens egen historik", nedre zonen "lägre än i …").
   K6:s fält `direction` anger zonen (+1 övre, −1 nedre) och ritas i bläckfärg med ▲/▼ och orden "kvotens takt högt
   i egen historik" eller "lågt i egen historik", eftersom avstämningarna saknar riktning i ett index (A5). Blått och
   orange betyder därmed bara riktning i ett diffusionsindex. Tillägg samma dag under implementeringen: K1-rubriken
   skrivs "från X till Y" i stället för med en pil, eftersom rubrikerna också blir länktexter i sidans avsnittslista.
5. **Rekonstruerat.** På månadssidan står statusen (rekonstruerad eller skarp) i rubrikraden, i samma storlek som
   månadsnamnet, och för rekonstruerade månader en mening om vad det betyder. Det ändrar inget urval.

#### 2026-11-25 – Ändring av W13 (L3-1): inhållna serier prövas inte i K5 och K6

Motivering: från den första skarpa ögonblicksbilden (2026-11-30) har den publika posten inga värden för serier som
inte får visas (`publish=False`), inte heller percentiler (beslutsloggen 2026-11-25, granskning L3-1). En skarp månad
kan då inte pröva dem i K5 och K6, men en rekonstruerad månad kan det. För att samma regel ska gälla alla månader
ändras regeln för alla månader. Ändringen skrivs innan den första skarpa posten finns. Trösklar, korttyper, ordning och
tak ändras inte.

1. **K5 och K6** prövar bara publicerbara serier (`site.data.publishable`). En inhållen serie räknas inte längre som
   "uppfyllde villkoret" i dessa typer, så antalet inhållna är 0 för K5 och K6. K3 och K4 räknar inhållna mål och brott
   som förut (brottflaggan står kvar i posten).
2. **Slumpnivån (R-W3b).** N är för K5 de räknade, giltiga och publicerbara kärnserierna med percentil för förändring
   i takt i M, och för K6 de publicerbara avstämningarna med percentil för takt. "Publicerbara eller inte" i R-W3b
   punkt 2 gäller inte längre.
3. **K0** räknar tillståndet "för få källor" (index v2, registret 2026-11-24) för sig, bredvid "för få serier", när det
   förekommer. Tidigare räknades det som "för få serier". Inget urval ändras.

### 2026-11-25 – KR1: spread vid emission för AI-tunga emittenter (extraktion, inte kärnserier)

Låst före kodningen. Inga dokument i korpusen var hämtade och inga värden lästa när posten skrevs. Agenten hade sett
antalet inlämningar per bolag, år och formulär i EDGAR:s submissions-index och licenstexten i FRED:s serienoter för
ICE BofA och Moody's. Regler i detalj: [`docs/kallor/kredit_emission.md`](kallor/kredit_emission.md), avsnittet
"Kodningsregler".
- **Vad:** belopp, kupong, förfallodag, referens, spread mot referensen (bp, som den står), avkastning och pris för
  varje tranche i de registrerade obligationsemissionerna från Microsoft, Alphabet, Amazon, Meta, Oracle och CoreWeave,
  2020-01-01–2026-11-25. Källan är FWP:n med de slutliga villkoren, annars det slutliga prospekttillägget (424B2 eller
  424B5). En rad per tranche i `curated/credit_issuance.csv`, med plats och SHA-256 av blocket. Texten sparas bara
  under `data/raw`.
- **Serier (G5, kvartal):** `issuance_<bolag>_q` (summa av belopp i USD per kvartal efter prisdag, MUSD),
  `spread_issue_ai_q` (principalvägt medelvärde av spreaden över alla emittenter, bp), `spread_issue_ai_7_12y_q`
  (bara löptid avrundad till 7–12 år, 6,5 ≤ löptid < 12,5) och `spread_issue_<bolag>_q` för emittenter med minst fyra
  kvartal med en spread. Spreadserierna tar bara tranchar i USD med fast ränta, en amerikansk statsobligation som
  referens och en angiven spread. Rörlig ränta ingår i volymen men inte i spreaden. Annan valuta ingår i ingen serie.
- **Vikt:** beloppet (MUSD). **Luckregeln:** ett kvartal utan tranche har inget värde, en lucka och inte noll.
- **known_from** för ett kvartal = max(dagen efter kvartalets slut, senaste `filingDate` bland trancherna som ingår).
  En senare inlämning ger en ny version. Ett kvartal som inte är slut har inget värde.
- **Avstämning:** täckningsgraden mot `debt_issued_<bolag>` per bolag och år (efter likviddag och bolagets
  räkenskapskvartal) redovisas i källdokumentet, inte som serie. Skillnaden är likvid mot nominellt belopp,
  företagscertifikat, terminslån, kreditfaciliteter, 144A och annan valuta.
- **Marknadsindex:** inget. ICE BofA och Moody's på FRED förbjuder vidarespridning utan tillstånd.
- **Täckning, ärligt:** serierna visar bara den registrerade marknaden. Privata placeringar, 144A och SPV-finansiering
  syns inte. Spreaden blandar emittenter med olika kreditbetyg, så den poolade serien rör sig också när mixen ändras.
- **Inte kärnserier.** Ingen takt räknas. `publish=False` tills extraktionsgranskningen har godkänt (minst 30 % av
  raderna, ett dokument per emittent, inga fel i talen). Ett förslag om kärnserie kräver godkänd granskning, minst 12
  kvartal i `spread_issue_ai_7_12y_q` och en registrerad regel för emittentmixen.
- **Tester:** syntetiska villkorsbilagor för parsern, löptiden, bandets gränser, vägningen, luckregeln, dateringen,
  CSV-kontrollen och självkontrollen.

### 2026-11-25 – T1: test av tillståndsregeln (förregistrering, före körning)

Spår T1 i körning 14 (`docs/riktning.md`, avsnitt 8, punkt 5). Testet prövar själva tillståndsregeln: avsnitt 2 med
index v2 (en röst per källfamilj, registret 2026-11-24) som huvudregel och v1 som sekundär. Två frågor: håller
tillstånden när data revideras, och säger de något om grenens takt de närmaste månaderna? Testet ändrar ingen skarp
regel: inga trösklar, inget dödband, inga kärnserier och inga familjer. Koden läser tillståndsmotorn
(`state/branch.py`, `measures.py`, `snapshot.py`) och ändrar den inte.

**Vad som var synligt före posten.**
- Tabellerna i `docs/resultat/tillstand.md`: v1 2026-05–2026-10, antalet månader per tillstånd 2019–2026 (v1) och v1
  mot v2 2026-05–2026-10.
- Tillstånden 2026-10-31 med v1 och v2 (en körning av motorn, samma som tabellen).
- För MDE nedan: antalet månader per tillstånd och gren 2024-01–2026-10 med v1 och v2, i realtid ur
  `snapshot.backcast`. Bara antalen lästes, inte index eller serier per månad.
- Antalet versioner per period för kärnserierna, alltså vilka serier som har mer än en version. Inte värdena.
- **Inga utfall** för (a) eller (b): inga reviderade tillstånd, inga takter efter ursprungsmånaden och inga träffar.

**Fönster.** Månadsslut m från 2024-01 till 2026-10: 34 månader och 9 grenar. I (b) ska utfallsdagen m + h vara
senast 2026-10-31. Fönstret är därför m till och med 2026-07 för h = 3 (31 månader) och till och med 2026-04 för
h = 6 (28 månader). Månadsslutet 2026-11-30 ligger efter körningen och används inte.

**Tillstånd i realtid.** Tillståndet vid m räknas med `as_of(m)` på dagens tabell (den delade basen och spårets egen),
med samma kod som `snapshot.backcast`. v2 (`state`) är huvudregel och v1 (`state_v1`) sekundär. Rader med
`source = "backfill"` bär dagens version, så realtid är redan delvis reviderad (förbehållen nedan).

**(a) Revideringsstabilitet**

- **Dagens data för månad m.** För varje serie ingår de perioder som hade minst en rad med `known_from` ≤ m. Varje
  sådan period får värdet och `source` från sin senaste rad med `known_from` ≤ V, där V är körningsdagen 2026-11-25.
  Rader med `known_from` > V används inte. Perioder som blev kända först efter m ingår inte. Tekniskt är det en tabell
  med en rad per serie och period: senaste värdet, och `known_from` = periodens första `known_from`. Tillståndet vid m
  räknas med `as_of(m)` på den tabellen och med samma kod. Härledda serier (`capex_ocf_hyp4`) bildas av de reviderade
  komponenterna. Aktiv BTOS-regim, valda benchmarks, aktualitetsregeln och benchmarkvakten tillämpas av samma kod.
  Spärren för bakåtfyllda serier räknas på den reviderade tabellen. Räknas en spärrad serie i den ena men inte i den
  andra redovisas det.
- **Mängd.** S = de grenmånader där minst ett av de två tillstånden är accelererar, stabil eller bromsar in.
- **Mått**, poolat över grenar (huvudmått) och per gren:
  - överensstämmelse = andelen av S med samma tillstånd;
  - Cohens kappa över S med fyra kategorier: accelererar, stabil, bromsar in och för få (för få källor med v2, för få
    serier med v1). Kappa redovisas inte när den väntade överensstämmelsen är 1;
  - andelen hårda byten = andelen av S där det ena tillståndet är accelererar och det andra bromsar in.
- **Beskrivande.** Överensstämmelse över alla 306 grenmånader, medel av |index reviderat − index realtid|, och
  exponering: andelen räknade serier (realtid) vars värden kända vid m har ändrats i senare versioner. Med exponering
  noll är överensstämmelsen 1 av konstruktion och säger ingenting.

**(b) Information om vad som kommer**

- **Prediktion.** Accelererar vid m förutsäger att grenens takt går upp, bromsar in att den går ned. Stabil och för få
  ger ingen prediktion.
- **Utfall** för gren b, ursprung m och horisont h ∈ {3, 6} månader, med t = månadsslutet m + h:
  - Serierna är de som räknades i b:s tillstånd vid m (samma för v1 och v2), med sin familj, sin senaste period P_m
    och sitt tecken σ: −1 för fördubblings- och halveringstid, annars +1.
  - Takten är det registrerade måttet (avsnitt 1), räknat med `as_of(t)` i `measures.measure_path(s, t)`, alltså samma
    kod som tillståndet. P_t är seriens senaste period vid t.
  - u = tecknet av σ × (takten vid P_t − takten vid P_m), båda ur versionen vid t. Det kräver att P_t är senare än
    P_m och att båda takterna finns. Annars saknar serien utfall. Inget dödband.
  - Grenens utfall med v2: familjens röst = medel av (u + 1)/2 över familjens serier med utfall, och O = medel av
    rösterna över familjer med minst en serie med utfall. Med v1: O = medel av (u + 1)/2 över serierna med utfall.
    **Upp** om O > 1/2 och **ned** om O < 1/2, räknat med exakta bråk. Vid O = 1/2, eller utan serier med utfall,
    saknas utfall, och månaden räknas inte.
  - Inget efter t används. Utfallet läser versionen vid t, inte dagens version.
- **Träff:** accelererar och upp, eller bromsar in och ned. **Träffkvot** H = träffar / prediktioner med utfall, poolat
  över grenar. Den redovisas också per gren och för accelererar och bromsar in var för sig, med andelen upp bland
  utfallen (basfrekvensen).
- **Baslinje 1, persistens:** riktningen i grenens takt de senaste h månaderna fortsätter. För samma serier vid m:
  u' = tecknet av σ × (takten vid P_m − takten vid P_{m−h}), båda ur versionen vid m, där P_{m−h} är seriens senaste
  period vid m − h. Samma aggregering som för utfallet ger upp, ned eller ingen riktning. Persistensens träffkvot räknas
  på samma grenmånader som tillståndens prediktioner: 1 vid samma riktning som utfallet, 0 vid motsatt och 0,5 när
  persistensen saknar riktning. Den redovisas också över alla månader med utfall.
- **Baslinje 2, slump:** blockpermutation av månaderna inom gren. Varje grens tillståndsföljd i fönstret delas i block
  om **6 månader** från fönstrets början (det sista blocket kan vara kortare). Blocken byter plats slumpmässigt, oberoende
  per gren, och utfallen ligger kvar. Antalet månader per tillstånd och gren bevaras. **9 999 permutationer**, frö
  **20261125**. Slumpnivån = medel av H* över permutationerna. p = (1 + antalet permutationer med H* ≥ H) / 10 000,
  ensidigt. En permutation utan prediktion med utfall räknas som H* < H. Blocklängden 6 är minst lika lång som båda
  horisonterna och lika med laggen för förändring i takt. Överlappande utfall och tröga tillstånd hålls då ihop.
- **Testfamilj och Holm.** Familjen är {v2 h = 3, v2 h = 6}, Holm-justerad. v1 med {h = 3, h = 6} redovisas med egen
  Holm, bara som information. Ett test kräver minst 20 prediktioner med utfall, annars p = 1.
- **Nedre svansen.** p_ned = (1 + antalet med H* ≤ H) / 10 000, Holm-justerad i samma familj. Den visar om
  tillstånden pekar fel oftare än slumpen.

**MDE, räknad före testet.** Underlaget är antalet prediktioner i realtid (se ovan), med antagandet att alla får ett
utfall. Med v2 finns 58 prediktioner för h = 3 (52 accelererar och 6 bromsar in) och 48 för h = 6 (44 och 4). Bara
G3–G7 har tillstånd med v2. Utfallen överlappar, så det effektiva antalet är ungefär n/h, alltså 19 och 8. Holms första
steg med två tester är 0,05, ensidigt. Med 80 % styrka blir MDE ≈ (1,645 + 0,842) × 0,5 / √(n/h): **0,28 för h = 3 och
0,44 för h = 6**. Träffkvoten måste alltså ligga cirka 28 respektive 44 procentenheter över slumpnivån för att testet
ska upptäcka skillnaden. Med v1 är det 92 och 80 prediktioner, och MDE blir 0,22 och 0,34.

**Styrkan är låg**, och det sägs nu, före testet. Ett icke-signifikant resultat visar inte att tillstånden saknar
information. Nästan alla prediktioner är accelererar, så "bromsar in → ned" går i praktiken inte att pröva (6 och 4
fall). Tröga tillstånd gör det effektiva antalet mindre än n/h. Grenarna och månaderna är dessutom inte oberoende,
eftersom flera grenar följer samma cykel.

**(c) Beskrivande, ingen ny regel**

- Andelen månader per tillstånd, med v2 och v1, per gren och totalt, 2024-01–2026-10 i realtid.
- Hur ofta grenar saknar tillräckligt många serier eller familjer: andelen för få serier och för få källor, och medel
  av antalet räknade serier och familjer.
- Trösklarna 0,60/0,40 och 0,75/0,25 i stället för 0,67/0,33, ur samma exakta index (≥ den övre och ≤ den undre).
  Andel per tillstånd, överensstämmelse med de registrerade trösklarna, (a) och träffkvoter i (b) med slumpnivå. Inga
  p-värden.
- Delperioder i (b): ursprung till och med 2025-06 och från 2025-07 (G-E:s holdoutfönster). Träffkvoter utan test.

**G-E.** T1 är ingen metodfamilj i G-E. Inget skattas och inget väljs, och regeln var låst före testet. Testet öppnar
därför ingen holdout, och holdoutloggen ändras inte. Delperioden från 2025-07 redovisas för sig.

**Beslutsregel.** Testet ändrar ingen skarp regel. Det ger en rekommendation till Johannes.
- **En granskning av regeln rekommenderas** om minst ett av följande gäller:
  1. (a) Poolad kappa med v2 < **0,70**, eller andelen hårda byten med v2 > **0,02**.
  2. (b) Träffkvoten med v2 är inte högre än den bättre baslinjen vid någon horisont: H ≤ max(persistensen på samma
     månader, slumpnivån) för både h = 3 och h = 6.
  3. (b) Tillstånden pekar fel: Holm-justerat p_ned < 0,10 vid någon horisont.
- **(b) godkänt** är ett positivt resultat och kräver ett granskningsspår (`CLAUDE.md`). Det gäller när Holm-justerat
  p < 0,10 vid minst en horisont och H vid den horisonten är högre än persistensens träffkvot på samma månader.
- **Annars är (b) inte avgjort.** Då ges ingen rekommendation på grund av (b). Tillstånden läses som en beskrivning av
  läget, och deras informationsvärde är inte påvisat.
- **Ger ingen rekommendation:** resultat per gren, v1, de andra trösklarna i (c), delperioderna och kappa per gren. De
  redovisas men avgör inte. En regeländring kräver en ny registerpost och gäller bara framåt.

**Förbehåll som skrivs i resultatet.**
- Många kärnserier har bara en version (`source = "backfill"` eller en enda inlämning). För dem är realtid och
  reviderat lika av konstruktion. Flera versioner finns för Indeed (G8), Fed G.17, TSMC, ASML och Broadcom (G6),
  Microsoft Cloud (G4), capex och kassaflöde för de fyra största (G5), EIA:s elförsäljning från arkivet (G7), BTOS v1
  (G3) och Arena (G1). (a) mäter alltså bara de revideringar som tabellen har som versioner, och överensstämmelsen är
  en övre gräns.
- Utfallen i (b) läser versionen vid t, men bakåtfyllda rader i den versionen bär dagens värden.
- Tillståndet vid m och utfallet delar takten vid P_m med motsatt tecken. Mätfel i den takten ger en mekanisk tendens
  till återgång, alltså färre träffar. Det är en egenskap hos regeln och inget fel i testet. Permutationen bryter
  kopplingen, så tendensen syns som en träffkvot under slumpnivån.

**Kod och tester.** `state/evaluate.py` och `python -m ai_tracker.state evaluate`. Syntetiska tester utan nätverk: en
värld med tröga tillstånd (takten följer långa cykler, så tillståndet håller i sig och utfallet följer det), en värld
där nivån är en slumpvandring (inget samband), och ett test att resultatet för ursprung m och horisont h blir detsamma
när tabellen kapas vid m + h. Konstanterna i posten står i koden, och ett test jämför dem med posten. Körloggen skrivs
till `experiments/runs/`, och resultatet till `docs/resultat/t1_tillstandsregeln.md`.

### 2026-11-25 – S1: nät, optik och servrar som katalogserier (inte kärnserier)

Spår S1, körning 14 (avsnitt 0 och 8 i `riktning.md`: stackens saknade lager). G6 täcker chipen, men inte lagren mellan
chipen och datacentret: nätverksswitchar, optiska moduler och servermontering. Serierna är katalogserier i G6. De ingår
inte i diffusionsindexet och ändrar inga tillståndsregler, och här räknas inga takter eller tillstånd. Kod:
`src/ai_tracker/series/sec_stack_nat.py`. Källa och kontroller: `docs/kallor/sec_stack_nat.md`.

**Bolag** (CIK verifierade mot `entityName` i EDGAR:s submissions):

| Bolag | CIK | Räkenskapsår | Mått |
|---|---|---|---|
| Arista Networks (ANET) | 1596532 | kalenderår | `rev_anet`, `inv_anet`, `purchase_oblig_anet`, `deferred_rev_anet`, `rpo_anet` |
| Cisco (CSCO) | 858877 | 52/53 veckor till sista lördagen i juli | `rev_csco`, `inv_csco`, `rev_csco_networking`, `rev_csco_infra_platforms`, `purchase_oblig_csco`, `rpo_csco` |
| Coherent Corp (COHR, tidigare II-VI) | 820318 | till 30 juni, kvartal = kalenderkvartal | `rev_cohr`, `inv_cohr`, `rev_cohr_networking`, `rev_cohr_datacom` |
| Lumentum (LITE) | 1633978 | 52/53 veckor till lördagen närmast 30 juni | `rev_lite`, `inv_lite`, `rev_lite_opcomms`, `rev_lite_cloud_networking`, `rev_lite_components`, `rev_lite_systems`, `purchase_oblig_lite` |
| Super Micro Computer (SMCI) | 1375365 | till 30 juni, kvartal = kalenderkvartal | `rev_smci`, `inv_smci`, `purchase_oblig_smci`, `rpo_smci` |
| Dell Technologies (DELL) | 1571996 | 52/53 veckor till fredagen närmast 31 januari | `rev_dell`, `inv_dell`, `rev_dell_isg`, `rev_dell_servers_networking`, `rev_dell_ai_servers`, `rev_dell_traditional_servers`, `rpo_dell` |
| Hewlett Packard Enterprise (HPE) | 1645590 | till 31 oktober | `rev_hpe`, `inv_hpe`, `rev_hpe_server`, `rev_hpe_dc_networking`, `rpo_hpe` |
| Celestica (CLS) | 1030894 | kalenderår | `rev_cls`, `inv_cls`, `rev_cls_ccs` |
| Micron (MU) | 723125 | – | `capex_mu` finns redan (spår A2a, `series/halvledare.py`) och ändras inte |

Celestica tas med: bolaget lämnar 10-K och 10-Q med XBRL (US GAAP) från 10-K:n för 2024 (2025-03-03). Tidigare
lämnade det 20-F och 6-K (IFRS), som inte används.

**Regel för taggval.** Taggen väljs per bolag och mått efter täckning och definitionskonsistens, aldrig efter seriens
förlopp.
- En tagg används bara om den står för samma rad i rapporten genom hela perioden. Byte av tagg för samma rad, med
  identiska värden i överlappet, skarvas per kvartal med `sec.py`:s regel. En tagg som också används för en annan rad
  används inte (Aristas `SalesRevenueGoodsNet` är bara produkter, HPE:s `SalesRevenueGoodsNet` likaså).
- **Totala intäkter** (`rev_<co>`): `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet`
  (som de befintliga `rev_*`). Lumentum taggar mest `RevenueFromContractWithCustomerIncludingAssessedTax`, som läggs
  först (identisk med de andra i alla överlapp). Omräkningar är versioner, som för övriga `rev_*`.
- **Lager** (`inv_<co>`): `InventoryNet` vid räkenskapskvartalets slut.
- **Segment- och produktrader** läses ur varje 10-Q/10-K:s XBRL-instans (`sec_segment`), med exakt den angivna
  dimensionsmängden (ett segment eller en produktkategori, för Dell segment × produkt), och intäktstaggarna ovan i
  prioritetsordning. Medlemmarna per rad:

| Nyckel | Medlem (axel) | Inlämningar |
|---|---|---|
| `rev_csco_networking` | `NetworkingMember`, i 10-K 2024-09-05 `NetworkingRevenueMember` (produkt) | från 2023-11-21 (FY2024, med FY2023 som jämförelse) |
| `rev_csco_infra_platforms` | `InfrastructurePlatformsMember` (produkt) | 2018-11-20 till 2021-09-09, avslutad |
| `rev_cohr_networking` | `NetworkingSegmentMember` (segment) | 2022-11-09 till 2025-08-15, avslutad |
| `rev_cohr_datacom` | `DatacenterAndCommunicationsSegmentMember` (segment) | från 2025-11-05 |
| `rev_lite_opcomms` | `OpticalCommunicationsSegmentMember` (segment) | till 2023-08-23, avslutad |
| `rev_lite_cloud_networking` | `CloudNetworkingSegmentMember` (segment) | 2023-11-08 till 2025-08-19, avslutad |
| `rev_lite_components`, `rev_lite_systems` | `ComponentsMember`, `SystemsMember` (på segmentaxeln; Lumentum har ett rapporterbart segment från FY2026) | från 2025-11-05 |
| `rev_dell_isg` | `InfrastructureSolutionsGroupMember`, före 2018-06 `EnterpriseSolutionsGroupMember` (segment) | från 2016-06 |
| `rev_dell_servers_networking` | `ServersAndNetworkingMember` (produkt) × ISG (eller ESG) | till 2025-12-09, avslutad |
| `rev_dell_ai_servers` | `AIOptimizedServersAndNetworkingMember` (produkt) × ISG | från 2026-03-16 |
| `rev_dell_traditional_servers` | `TraditionalServersAndNetworkingMember` (produkt) × ISG | från 2026-03-16 |
| `rev_hpe_server` | `ServerSegmentMember` (segment) | från 2024-03-05 |
| `rev_hpe_dc_networking` | `DataCenterNetworkingMember` (segment) | från 2026-03-10 |
| `rev_cls_ccs` | `CCSSegmentMember` (segment) | från 2025-03-03 |

  Arista har ett segment och taggar bara produkt, tjänst och geografi, så ingen rad för moln eller AI finns. Super
  Micros produktrad "Server and storage systems" taggas inte efter 10-K för FY2025, och bolaget har ett segment, så
  `rev_smci` är måttet. Celesticas delsegment inom CCS (bytte namn och innehåll i 10-Q 2026-10-26) tas inte med.
- **Åtaganden** (`purchase_oblig_<co>`, balans, som `purchase_oblig_nvda`), där totalen taggas varje kvartal:
  - ANET: `PurchaseCommitmentRemainingMinimumAmountCommitted` utan dimension, i inlämningar från 2016-02-25 (från dess
    står meningen "non-cancellable purchase commitments of" i noten, och tidigare inlämningar använde taggen för en
    annan, liten post).
  - CSCO: `UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount` med
    `UnrecordedUnconditionalPurchaseObligationByCategoryOfItemPurchasedAxis` = `InventoriesMember`, och samma tagg utan
    dimension, i inlämningar från 2021-05-25 (tabellen "inventory purchase commitments with contract manufacturers and
    suppliers"). De äldre taggarna (2016–2019) och luckan 2020 skarvas inte.
  - LITE: `PurchaseCommitmentRemainingMinimumAmountCommitted` utan dimension ("purchase obligations").
  - SMCI: `PurchaseObligation` utan dimension ("remaining non-cancelable commitments", inklusive närstående).
  - Inte med: Coherent (bara i 10-K), Dell och HPE (bara tidshinkar, ingen taggad total), Celestica (ingen tagg).
- **Kontraktsskulder, Arista** (`deferred_rev_anet`): `ContractWithCustomerLiabilityCurrent` +
  `ContractWithCustomerLiabilityNoncurrent` ur samma inlämning. I inlämningar från 2018-04-01 (efter ASC 606) tas en del
  som saknas under dessa taggar från `DeferredRevenueCurrent` respektive `DeferredRevenueNoncurrent`. Balanser före
  2017-12-31 (ASC 605) ingår inte.
- **RPO** (`rpo_<co>`), total utan dimension: CSCO, SMCI, DELL och HPE `RevenueRemainingPerformanceObligation`
  (companyfacts). ANET: bolagets egen tagg
  `RevenueRemainingPerformanceObligationIncludingContractLiabilitiesDeferredRevenueAndOtherPerformanceObligationsAmount`
  ur instansen, från 10-K 2023-02-14. Den är totalen "deferred revenue, contract liabilities and other performance
  obligations". `RevenueRemainingPerformanceObligation` före dess är en smalare definition (10-K 2023-02-14 anger båda,
  med olika belopp) och tas inte med. Lumentum (till 2021) och Micron (bara 10-K) tas inte med.
- **Capex** för Micron finns redan som `capex_mu`. Inga andra capex-serier byggs i S1.

**Regel för brott.** Varje segment- och produktrad, och varje balansserie utom lager, prövas med
`sec_segment.definition_breaks`: en inlämning som ändrar ett tidigare inlämnat värde för samma period med mer än 2 %.
De upptäckta brotten måste stämma med de deklarerade, annars stoppar hämtningen (`DefinitionBreakError`).
- För segment- och produktrader är ett deklarerat brott alltid en ny definition: raden delas vid brottet i separata
  nycklar, och de skarvas aldrig. En medlem som ersätts av en ny medlem med annat innehåll är en ny nyckel.
- För åtaganden, kontraktsskulder och RPO avgörs ett deklarerat brott av inlämningens egen text: en ändrad definition
  ger en ny nyckel (eller att serien börjar vid den nya definitionen), en rättelse av samma definition blir en version.
- Totala intäkter och lager prövas inte, som för de befintliga `rev_*` och `inv_*`. Förvärv (Juniper i HPE:s nät från
  2025-07, Oclaro i Lumentum 2018-12, Coherent Inc. i II-VI 2022-07, Splunk i Cisco 2024-03) är inga brott.

**Kalender och datering.** known_from är inlämningsdatumet för 10-Q eller 10-K. Varje inlämning är en version, och
YTD-differenser, Q4 = helår − 9M och kalendermappningen (mittpunktsregeln) görs som i `sec.py`. Balanser (lager,
åtaganden, kontraktsskulder och RPO) får kalenderkvartalet för räkenskapskvartalet (`sec_instant.fiscal_quarters`), så
att en balans och flödena i samma räkenskapskvartal har samma etikett. För RPO skiljer det sig från `sec_rpo.py`
(balansdagens kalenderkvartal) för Cisco, Dell och HPE. Det är ett medvetet val för att samma bolags serier ska kunna
jämföras. `lag_days` är 25 om ingen inlämning kommer före kalenderkvartalets slut. Aktualitetsgränsen är största
observerade avstånd från kalenderkvartalets slut till första egna inlämning (2015–2026) + 92 + 30 dagar, där den
härledda gränsen (147 dagar) är för snäv.

**Katalog:** gren G6, frekvens Q, enhet MUSD, `publish=True` med samma licens som övriga SEC-serier (`series/sec.py`,
klass `ja` i `licenses.py`). Siffrorna är taggade XBRL-fakta, inte extraherad text.

**Vad som setts före denna post:** per bolag och kandidattagg i companyfacts antal fakta, första och sista slutdatum,
inlämningsdatum och formulär, och den största relativa skillnaden mellan taggar i överlappande perioder (inga nivåer).
Per instans: vilka segment- och produktmedlemmar och vilka taggar för åtaganden, kontraktsskulder och RPO som finns i
vilka inlämningar (antal och datum). För att läsa definitionerna lästes textblock i ett urval inlämningar: Aristas
meningar om åtaganden och RPO i sex inlämningar 2015–2023 och 2026-11-04, Super Micros, Lumentums och Ciscos meningar om
åtaganden i den senaste 10-Q:n, Lumentums och Coherents segmenttext och HPE:s segmenttext i 10-Q 2026-09-03. I de
meningarna och i HPE:s tabell över intäkter per kategori syntes enskilda belopp. För Aristas tagg för åtaganden jämfördes
taggen med meningen i två inlämningar (2015-11-06 och 2018-11-05). Inga kvartalsserier eller takter har räknats.

### 2026-11-25 – M1: nettobidrag för datorer efter import (BB01RY), ägarbeslut

Ägarbeslut 2026-11-25 (beslutsloggen samma dag): BEA:s nettobidrag för datorer förregistreras, som granskningen R12
föreslog (R-3). Posten skrivs och committas innan något värde för `BB01RY` hämtas. Reglerna i M1-posterna ovan gäller
oförändrade också för den nya serien.

**Vad som har setts före registreringen.** Granskningen R12 läste `BB01RY` i tre releaser (2017-10-27, 2023-06-29 och
2026-10-29) för att visa att premissen spelade roll. För 2026Q3 var bidraget −0,61 procentenheter i releasen
2026-10-29, mot +0,72 för `B935RY`. Ingen historik och ingen takt har räknats, och inga andra kvartal har lästs.

**Definition.**
- `us_gdp_contrib_final_sales_computers` = bidraget till procentuell förändring i real BNP från slutlig försäljning av
  datorer ("Final sales of computers", NIPA-tabell 1.2.2 rad 17, `BB01RY`). Procentenheter i årstakt (SAAR), med de två
  decimaler som BEA publicerar.
- Samma releasearkiv och samma datering som de andra bidragsserierna i M1. known_from = "Data published" i
  tabellhuvudet. Värden som publicerades före 2017-10-27 får det datumet. Bara perioder som finns i den senaste
  vintage visas (R12, R-2). Koden läses ur tabellens kodkolumn, inte ur radnumret, som kan flyttas mellan vintages.
  Saknas koden i en arkiverad release stoppar hämtningen med ett fel.
- Gren G5, som `us_gdp_contrib_computers`. Det är en katalogserie, inte en kärnserie, och den räknas inte i någon grens
  index. Om den ska bli kärnserie är det ett G-A-beslut senare, med en egen post.

**Vad den omfattar.** Datorer och kringutrustning i all slutlig användning, minus importen. Enligt BEA:s
`SeriesRegister.txt` (R12) består `BB01RC` av privata investeringar i datorer (`B935RC`), hushållens köp (`DCPPRC`) och
export (`B850RC`), minus import av datorer, kringutrustning och delar (`B852RC`). Resten är troligen offentliga
investeringar i datorer, men det är inte verifierat. Serien omfattar inte programvara och inte övrig
informationsbehandlingsutrustning (kommunikationsutrustning, instrument, kontorsutrustning). Den är alltså inget
nettomått för `ai_invest_contrib_gross`, och något sådant registreras inte. Kategorin är bredare än AI, som i M1.

**Hur den läses.**
- Bredvid `us_gdp_contrib_computers` (`B935RY`, tabell 1.5.2 rad 32). Den serien är bruttobidraget från privata
  investeringar i datorer och räknar utrustningen oavsett om den är importerad. `BB01RY` drar ifrån importen och tar med
  hushållens och den offentliga sektorns köp och exporten. När investeringarna växer och till stor del möts av import kan
  bruttobidraget vara positivt och nettobidraget nära noll eller negativt.
- Skillnaden mellan de två serierna definieras inte som en egen serie. Den blandar flera poster (hushåll, offentlig
  sektor, export och import) och är inte granskad.
- Bredvid `us_imp_computers_contrib_imp` (`B852RZ`). Den serien är datorimportens bidrag till den reala importens
  tillväxt, inte till BNP:s, så skalan är en annan. Den visar om en förändring i nettobidraget följer med importen.
- Ingen kvot mot BNP-tillväxten definieras, av samma skäl som i M1. Ett bidrag på x procentenheter betyder inte att AI
  bidrog med x.

**Kontroll efter hämtningen.** Minst tre kvartal kontrolleras för hand mot tabell 1.2.2 i den arkiverade releasen.
Resultatet står i `docs/kallor/makro_bea_bls.md`.

### 2026-11-25 – S2: kraft, kylning, elnät och datacenterbolag som katalogserier (inte kärnserier)

Spår S2, körning 14 (punkt 1 i `riktning.md`, avsnitt 8). Serierna är katalogserier. De ingår inte i diffusionsindexet,
och här räknas inga takter eller tillstånd. Kod: `src/ai_tracker/series/sec_stack_kraft.py`. Källa och kontroller:
`docs/kallor/sec_stack_kraft.md`.

**Bolag.** Alla har kalenderår, och räkenskapskvartalen kontrolleras mot kalenderkvartalen i bygget.

| Bolag | CIK | Anmärkning |
|---|---|---|
| Vertiv (VRT) | 1674101 | f.d. GS Acquisition Holdings Corp. 10-K och 10-Q som Vertiv från 2020-03-12 |
| GE Vernova (GEV) | 1996810 | första 10-Q 2024-04-30. Form 10 (10-12B 2024-02-15, 10-12B/A 2024-03-05) har ingen XBRL, så historiken börjar med jämförelsetalen i 10-Q 2024 |
| Eaton (ETN) | 1551182, 31277 | Eaton Corporation plc (Irland, lämnar 10-Q och 10-K) och föregångaren Eaton Corporation (till 10-Q 2012-10-31), som Alphabet och Google Inc. |
| Quanta Services (PWR) | 1050915 | |
| Equinix (EQIX) | 1101239 | REIT |
| Digital Realty (DLR) | 1297996 | REIT. companyfacts saknar 10-Q 2026-07-31 och 2026-10-30, så flödena läses ur instanserna (nedan) |

**Regel för taggval** (som P1). Taggen väljs per bolag efter täckning och definitionskonsistens, aldrig efter seriens
förlopp. Byte av tagg för samma rad skarvas per kvartal med `sec.py`:s regel, och bara när taggarna är identiska i
överlappet. En kandidattagg som avviker i överlappet används inte.

| Mått | Bolag | Taggar (prioritet) och rad |
|---|---|---|
| `rev_<co>` | VRT | `RevenueFromContractWithCustomerExcludingAssessedTax` ("Net sales"). `Revenues` (2016–2019) avviker i alla sju överlappande perioder och används inte |
| | GEV | `RevenueFromContractWithCustomerExcludingAssessedTax` |
| | ETN | `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet` (identiska i 7 perioder), för båda CIK (föregångarens `SalesRevenueNet` är identisk i 7 perioder). `Revenues` avviker och används inte |
| | PWR | `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueServicesNet` (identiska i 7 perioder) |
| | EQIX | `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues` (identiska i 7 perioder) |
| | DLR | `Revenues` ur instanserna |
| `capex_<co>` | VRT | `PaymentsToAcquirePropertyPlantAndEquipment` ("Capital expenditures"). Raden "Investments in capitalized software" ingår inte |
| | GEV | `PaymentsToAcquireProductiveAssets` ("Additions to property, plant, and equipment and internal-use software") |
| | ETN | `PaymentsToAcquirePropertyPlantAndEquipment` ("Capital expenditures for property, plant and equipment"), båda CIK |
| | PWR | `PaymentsToAcquirePropertyPlantAndEquipment` ("Capital expenditures") |
| | EQIX | `PaymentsToAcquireOtherPropertyPlantAndEquipment` ("Purchases of other property, plant and equipment"). Raden "Real estate acquisitions" (`PaymentsToAcquireRealEstate`) ingår inte |
| | DLR | `PaymentsToDevelopRealEstateAssets` ("Improvements to investments in real estate") ur instanserna. Förvärv och investeringar i intresseföretag ingår inte |

**Capex för datacenterbolagen** är utbyggnad och förbättring av egen kapacitet: raden för bygge och utrustning, inte
köp av befintliga fastigheter eller bolag. Det gör de två jämförbara med varandra. De är inte helt jämförbara med de
stora molnbolagens capex, som också innehåller köpt mark och byggnader.

**Segmentintäkter** (ur instanserna). En fakta räknas bara när kontextens dimensioner är exakt de angivna.

| Serie | Medlem (`StatementBusinessSegmentsAxis`) och markör (`ConsolidationItemsAxis`) |
|---|---|
| `rev_gev_power`, `rev_gev_wind`, `rev_gev_electrification` | `PowerSegmentMember`, `WindSegmentMember`, `ElectrificationSegmentMember`, med `OperatingSegmentsExcludingIntersegmentEliminationMember` (segmentets intäkter före eliminering av interna intäkter). Markören finns i alla elva inlämningar. `OperatingSegmentsMember` finns bara i 10-Q 2024, avviker upp till 5 % och används inte |
| `rev_etn_electrical_americas`, `rev_etn_electrical_global` | `ElectricalAmericasSegmentMember`, `ElectricalGlobalSegmentMember`, utan markör och annars med `OperatingSegmentsMember` (identiska i 156 par). Bara inlämningar från 2020-01-01, eftersom medlemsnamnet `ElectricalAmericasSegmentMember` användes i 10-K för 2012 för ett äldre segment |
| `rev_vrt_americas`, `rev_vrt_apac`, `rev_vrt_emea` | `AmericasSegmentMember`, `AsiaPacificSegmentMember`, `EMEASegmentMember`, med `OperatingSegmentsMember` (segmentets intäkter inklusive försäljning till andra segment). Markören finns i alla inlämningar från 2020-05. Medlemmen utan markör (avviker upp till 35 %) saknas i 10-K 2024-02-23 |

Inte byggt: segment för PWR (fem segmentindelningar 2018–2026), regioner för EQIX och produktlinjer för VRT och GEV.

**RPO och orderstock** (balans vid kvartalets slut, som `sec_rpo`, ur instanserna). Bara totalen, ingen uppdelning i
tid: tidshinkarna är inkonsekvent taggade (PWR 2021 och 2023 har andelens startdatum och längden på olika hinkar,
ETN 2022–2023 har inaktuella startdatum och en odimensionerad andel).

| Serie | Gren | Tagg och kontext |
|---|---|---|
| `rpo_gev` | G7 | `RevenueRemainingPerformanceObligation` utan dimension |
| `rpo_gev_equipment`, `rpo_gev_services` | G7 | samma med `ProductOrServiceAxis` = `ProductMember` respektive `ServiceMember` (alla elva inlämningar) |
| `rpo_pwr` | G7 | utan dimension, från 10-Q 2018-05-09 |
| `rpo_etn` | G7 | Eatons "total backlog" (fasta order), taggad som RPO: utan dimension 2020Q3–2024Q1, därefter med bara startdatumaxeln (en hink), som `sec_rpo.totals` läser som total. Samma mening i 10-Q 2020-11-03, 2023-10-31, 2024-08-01 och 2026-11-03 |
| `rpo_eqix` | G4 | utan dimension, från 10-Q 2018-05-04 |

**Vertiv: RPO och orderstock är BLOCKED i XBRL.** Vertiv taggar inget RPO. Fakta med `RevenueRemainingPerformanceObligation`
och startdatumaxeln är tidsfördelningen av långfristiga förutbetalda intäkter ("expects to recognize noncurrent deferred
revenue of ... in the next 13 to 24 months ..."), inte RPO, och används inte. Orderstocken ("estimated combined order
backlog") står bara i texten. Spår S3 extraherar de uttalade siffrorna ur pressmeddelandena.

**Omräkningar och brott.** Omräkningar är versioner med regeln om konsekvent bas i `sec.py`. En inlämning som räknar om
tidigare värden av en segmentserie eller en balans med mer än 2 % (`sec_segment.definition_breaks`) deklareras efter
granskning, och varje definition får en egen nyckel. En odeklarerad omräkning stoppar hämtningen. För totala intäkter
och capex gäller P1:s regel: omräkningar är versioner och ger ingen ny nyckel. En senare version som bara avrundar
tusental till hela miljoner tas bort, som i `neoclouds`.

**DLR ur instanserna.** Fakta utan dimension gäller Digital Realty Trust, Inc. (partnerskapet har `LegalEntityAxis`).
Samma kvartals- och versionslogik som för companyfacts. Kontroll i bygget: instansserien ska vara lika med
companyfacts-serien i alla versioner till och med 2026-05-01.

**Datering och kalender.** known_from är inlämningsdatumet för 10-Q eller 10-K. YTD-differens, Q4 = helår − 9M och
mittpunktsregeln som i `sec.py`. `lag_days` = 25. Aktualitetsgräns per bolag = största observerade avstånd från
kvartalets slut till första egna inlämning (2015–2026) + 92 + 30.

**Grenar.** VRT, GEV, ETN och PWR (alla mått) i G7. EQIX och DLR: intäkter och RPO i G4, capex i G5, som CoreWeave
(`rev_crwv` i G4, `capex_crwv` i G5). Alla har `unit` MUSD, `freq` Q, SEC-licensen (`series.sec.LICENSE`, klass `ja`)
och `publish=True`. Inga värden extraheras ur text.

**Förbehåll.** GEV och ETN är till största delen annat än AI (gasturbiner, vind, flyg, fordon). Datacenterandelen går
inte att skilja ut i XBRL. Spår S3 extraherar bolagens uttalade datacentersiffror ur pressmeddelandena.

**Vad som setts före denna post:** entitetsnamn, räkenskapsår och inlämningslistor. Vilka kandidattaggar som finns och
vilka perioder och inlämningsdatum de täcker. Per inlämning: vilka segmentmedlemmar och markörer som finns på
intäkterna, och hur RPO är taggat (dimension, hinkarnas startdatum och längd). Antal överlappande perioder och största
relativa skillnad mellan kandidattaggar och mellan markörer. Radetiketterna i kassaflödesanalysen i senaste 10-K (och
10-Q för EQIX och DLR). Texten kring RPO-fakta hos Vertiv (10-K 2026-02-13 och 10-Q 2026-10-28) och Eaton (10-Q 2020-11-03,
2023-10-31, 2024-08-01, 2026-11-03), för att se vad som taggats. Där syntes enstaka orderstocksbelopp (Vertiv 15,0 och
7,2 mdr USD, Eaton 5,4, 12,9, 15,2 och 26,2 mdr USD). Inga kvartalsserier eller takter har räknats.

### 2026-11-25 – S1: tillägg efter första bygget (brott i totala intäkter, HPE:s Server, Aristas RPO-datum)

Tillägg till posten "S1: nät, optik och servrar som katalogserier". Den posten skrivs inte om. Skälet är vad
brottskontrollen och bolagens texter visade vid första bygget, inte seriernas förlopp. Det som setts är storleken på
omräkningarna (relativt), vilka inlämningar som räknar om, och texten om skälen.

1. **Totala intäkter prövas också** med `definition_breaks`. Dell, HPE och Coherent räknade om tidigare år med mer än
   2 % när en verksamhet redovisades som avvecklad: Dell Services, DSG och ECD (10-Q 2017-06-09) och VMware (10-K
   2022-03-24), HPE:s Enterprise Services och mjukvara (10-Q 2017-06-08 och 2018-06-07), och II-VI:s produktlinje
   tellurium (10-K 2014-08-28). Med versionsregeln i `sec.py` räknas bara de kvartal om som bolaget lämnar in igen, så
   den senaste versionen blandar omfattningar (före tillägget låg Dells kvartal till 2020 med VMware och senare utan).
   **Regel:** ett brott i totala intäkter som kommer av ändrad omfattning (avvecklad verksamhet, avknoppning) deklareras
   som omfattningsbrott, och `rev_<co>` läser bara inlämningar från det senaste. Serien börjar alltså vid den nuvarande
   omfattningen, och äldre omfattningar blir inga egna nycklar i S1. En omräkning som rättar samma definition (Super
   Micro 2019-05-17, efter revisionsutskottets utredning) deklareras som rättelse och ger versioner. Coherents omräkning
   2012-02-08 (+2,0 % för ett kvartal 2010) förklaras inte i textblocken. Den deklareras som rättelse och påverkar inte
   serien, som börjar efter 2014-08-28. Lager prövas fortfarande inte.
2. **HPE:s Server delas vid omorganisationen.** HPE slog ihop Server, Hybrid Cloud och Financial Services till segmentet
   Cloud & AI från 2025-11-01 och räknade om tidigare perioder (10-Q 2026-03-10). Server räknades då om med +1,8 %, och
   med +2,0 % i 10-Q 2026-06-02, så kontrollen slår till först i den senare inlämningen. **Regel:** ett deklarerat brott
   delas vid den inlämning där bolaget enligt sin egen text inför den nya definitionen, även när omräkningen där är
   under 2 %. Kontrollen måste då hitta exakt det senare datumet (fältet `detected`). `rev_hpe_server` i posten ovan
   blir därför två nycklar: `rev_hpe_server_fy24` (avslutad) och `rev_hpe_server_fy26`.
3. **Aristas RPO, fel datum i tre 10-Q.** 10-Q 2025-05-07, 2025-08-06 och 2025-11-05 taggar balansen med ett datum ett år
   för tidigt (till exempel "$3.7 billion as of March 31, 2025" i kontexten 2024-03-31). Utan rättelse ser det ut som en
   omräkning av 2024 års balanser, och 2025 års balanser saknas. I de tre inlämningarna dateras faktat om till
   inlämningens egen balansdag (som AMD:s roterade medlemmar i `halvledare.py`).
4. **Coherent, ingen omräkning 2026-11-04.** Coherent flyttade affärsenheter från Industrial till Datacenter &
   Communications från FY2027 och skriver att tidigare perioder inte räknats om eftersom effekten inte är väsentlig. Det
   går inte att upptäcka i datat och ger ingen ny nyckel. Det står som förbehåll i källdokumentet.

### 2026-11-25 – S2: tillägg efter första bygget (före analys)

Första bygget av S2:s serier visade två fel i inlämningarna och ett segmentbrott. Inga takter har räknats. Reglerna för
taggval ändras inte.

1. **Feldaterade fakta i 10-Q.** En 10-Q redovisar perioden och samma period året före. En fakta i en 10-Q vars period
   slutar mer än 550 dagar före inlämningen är därför felaktigt daterad och används inte. Det gäller en fakta: Equinix
   10-Q 2025-04-30 taggar intäkten för Q1 2025 (2 225 MUSD) med datumen för Q1 2023. Utan regeln skulle `rev_eqix`
   2023Q1 få det värdet som ny version. Regeln gäller alla S2-serier (flöden, segment och balanser).
2. **Eatons skalbolag.** Eaton Corporation plc lämnade en 10-Q 2012-11-14, före sammanslagningen med Cooper, med
   intäkten 0 för Q3 2012. Fakta som plc-bolaget lämnat in före 2013-01-01 används inte. Perioden täcks av
   föregångaren Eaton Corporation (31277).
3. **GE Vernova Electrification, brott deklarerat 2026-04-22.** Från 2026-01-01 flyttade GE Vernova en del av
   Electrification Software till Gas Power i Power-segmentet (10-Q 2026-04-22). Kvartalen 2025 räknades om med −1,4 till
   −2,1 %, alltså över gränsen 2 % för Q1. Enligt regeln får varje definition en egen nyckel:
   `rev_gev_electrification_fy24` (inlämnat 2024-04 till 2026-01, avslutad) och `rev_gev_electrification_fy26`.
   Power räknades om med +0,5 till +0,6 %, under gränsen, och det blir vanliga versioner av `rev_gev_power`.
4. **Equinix capex börjar 2014Q1.** Raden taggades `PaymentsToAcquirePropertyPlantAndEquipment` i inlämningarna
   2012–2013. Den taggen avviker från `PaymentsToAcquireOtherPropertyPlantAndEquipment` i en av 19 överlappande perioder
   och skarvas därför inte (registrets regel).
5. **DLR ur instanserna mot companyfacts.** Serierna är lika i alla versioner till och med 2026-05-01, utom tre rader i
   `rev_dlr` (2009Q2 och första versionen av 2010Q2). Orsaken är att `sec_segment.instance_name` väljer filen
   `defnref.xml` i fyra av DLR:s inlämningar 2010–2011, och då hittas inga fakta. Kvartalen får sin första version
   senare (2011-08-05), vilket är konservativt. Samma fil finns i sju av Microsofts inlämningar 2009–2011. Felet
   rättas inte här, eftersom koden är gemensam.

### 2026-11-25 – S3: order och orderstock ur resultatpressmeddelanden (extraktion, inte kärnserier)

Låst före kodningen. Inga bilagor var hämtade och inga värden lästa när posten skrevs. Agenten hade bara sett EDGAR:s
submissions och indexsidorna för resultat-8-K:na (bilagornas nummer och namn). Regler i detalj:
[`docs/kallor/order_orderstock.md`](kallor/order_orderstock.md), avsnittet "Kodningsregler".
- **Vad:** tal för order, orderstock, book-to-bill, reservationer av leveransplatser (GW), AI-servrar och tecknade
  hyresavtal som Vertiv, GE Vernova, Eaton, Dell, Digital Realty och (valfritt) Equinix anger i pressmeddelandet
  (`EX-99.1`, eller `EX-99` när det är den enda bilagan) till 8-K med Item 2.02, inlämnade 2022-01-01–2026-11-25.
  Luckregel för ett kvartal utan Item 2.02 (GE Vernova 2025-07-23).
- **Definitioner:** bolag, mått, segment, komponent, fönster (kvartal, tolv månader, hittills i året, helår, stock vid
  periodens slut), form (nivå, tillväxt mot året före, mot kvartalet före, mot förra årsslutet, kvot, multipel),
  organiskt eller inte, och enhet. Varje kombination är en egen serie. Inget räknas om och inget skarvas.
- **Serier:** `ob_<bolag>_<mått>_<segment>[_<komponent>]_<fönster>_<form>[_<organiskt>]_<enhet>` för varje
  definition med värden för minst två perioder. Kalenderkvartalet som innehåller mitten av räkenskapskvartalet, år
  för helårstal. Gren G7 (Vertiv, GE Vernova, Eaton), G6 (Dell) och G4 (Digital Realty, Equinix).
- **known_from** = EDGAR:s `filingDate`. Datumraden i pressmeddelandet sparas och kontrolleras mot den. Första
  dokumentet som anger ett tal för en period räknas. Ett ändrat tal i ett senare dokument är en ny vintage.
- **Stopp:** när ett ordinarie pressmeddelande slutar ange en definition som det föregående angav kodas ett stopp.
  Luckan fylls inte. Anges definitionen igen fortsätter serien, och stoppet står kvar.
- **Gränser** ("more than", "nearly") står i CSV:n men blir inga seriepunkter.
- **Inte kärnserier.** De ingår inte i grenarnas tillstånd, diffusionsindex eller takter. Ingen takt räknas.
- **Publicering:** `publish=False` tills den oberoende granskningen av extraktionen är godkänd. Stickprov med
  `python -m ai_tracker.orders_check`.

### 2026-11-25 – CN1: Kina via SEC (Alibaba och Baidu), katalogserier

Spår CN1 i körning 14 (förslag 7 i `docs/riktning.md`). Posten låser serier, källrader, datering, brottregler och
kontroller innan någon serie räknas. Serierna är katalogserier: inga mått räknas, och de ingår inte i grenarnas index
eller i tillståndsreglerna. Att göra någon av dem till kärnserie kräver en egen registerpost och en granskning.
Molnintäkter i G4, capex i G5. Tencent lämnar inget till SEC och ingår inte.

**Vad som var sett före posten.** EDGAR:s inlämningslistor för Alibaba (CIK 1577552) och Baidu (CIK 1329099), index
och exhibits för 6-K med kvartalsrapporter (Alibaba 47 pressmeddelanden 2015–2026, Baidu 74 pressmeddelanden
2007–2026), och Fed:s H.10-sida för renminbi. Jag läste titlar, tabellhuvuden, radetiketter och fotnoter om
segmentens innehåll, för att kunna skriva tolkningen. Siffrorna i raderna syntes i den läsningen. Ingen serie är
räknad, och ingen nivå, takt eller jämförelse mellan kvartal är gjord. Råkopiorna hämtades delvis av ett tidigare,
avbrutet försök av samma spår samma dag.

**Källa och datering.** Bolagens pressmeddelanden om kvartalsresultat, som lämnas som exhibit (oftast 99.1) till en
6-K. `known_from` = 6-K:ns inlämningsdatum i EDGAR (`filingDate`). Siffrorna blir offentliga senast då. Kontroll:
datumet i pressmeddelandets dateline (eller underskrift) ska ligga på inlämningsdagen eller dagen före. Fördelningen
redovisas i `docs/kallor/kina_sec.md`. Ligger dateline tidigare än dagen före används inte pressmeddelandet, och det
redovisas. Jämförelsetal för tidigare kvartal i senare pressmeddelanden är nya vintages när de skiljer sig mer än
0,5 MRMB (tabellerna avrundar till hela miljoner). Enhet: miljoner RMB som rapporterat (MRMB). Capex lagras som
positivt belopp.

**Kalender.** Alibabas räkenskapsår slutar 31 mars, men kvartalen slutar på kalenderkvartalens slut. Kvartalet som
slutar 30 juni är alltså kalenderkvartal 2 (räkenskapsårets Q1). Baidu har kalenderår.

**Serier ur tabeller** (deterministisk tolkning, `publish=True` om licenskontrollen håller):

| Nyckel | Gren | Rad i pressmeddelandet | Pressmeddelanden (inlämnade) |
|---|---|---|---|
| `rev_baba_cloud_v1` | G4 | segmentet "Cloud computing", före DingTalk | 2016-08-11 – 2021-05-13 (avslutad) |
| `rev_baba_cloud_v2` | G4 | "Cloud computing", från 2022-02 "Cloud", med DingTalk (omklassat från 2021-04-01) | 2021-08-03 – 2023-05-18 (avslutad) |
| `rev_baba_cloud_v3` | G4 | "Cloud Intelligence Group" utan DingTalk (omklassat från kvartalet till 2023-09-30), före koncernelimineringar | 2023-11-16 – 2026-05-13 (avslutad) |
| `rev_baba_cloud_v4` | G4 | "AI Cloud and Compute Services" (Cloud Intelligence Group och T-Head sammanslagna) | från 2026-08-20 |
| `capex_baba_v1` | G5 | "Less: Purchase of property and equipment and intangible assets (excluding land use rights and construction in progress)" i avstämningen mot fritt kassaflöde | 2015-01-29 – 2018-05-04 (avslutad) |
| `capex_baba_v2` | G5 | "Less: Purchase of property and equipment (excluding land use rights and construction in progress relating to office campus(es))" i samma avstämning | från 2018-11-02 |
| `capex_bidu` | G5 | "Less: Capital expenditures", kolumnen Baidu, Inc., tre månader i RMB | från 2020-03-04 |
| `capex_bidu_core` | G5 | samma rad, kolumnen "Baidu excl. iQIYI" (Baidu, Inc. minus iQIYI:s konsoliderade kassaflöden) | från 2020-03-04 |

- **Alibabas molnrad:** första tabellen efter "breakdown of (our) revenue by segment" med huvudet "Three months ended
  <månad> <dag>, <år−1> <år>". Efter etiketten tas procenttal och fotnotsmarkeringar bort. Exakt tre belopp ska stå
  kvar: samma kvartal året innan (RMB), kvartalet (RMB) och kvartalet (US$). Annars används inte raden.
- **Alibabas capex** är bolagets egen rad i avstämningen mot fritt kassaflöde, alltså kontant betalt för
  anläggningstillgångar, utan mark och pågående bygge av kontorscampus. Det är inte hela raden i
  kassaflödesanalysen, som inte finns i pressmeddelandet. Raden ska ha 3 eller 6 belopp. De två första är samma
  kvartal året innan och kvartalet (RMB).
- **Baidus capex:** kassaflödestabellen med kolumngrupper "Three months ended <datum> (RMB|US$)" (fyra grupper:
  samma kvartal året innan, föregående kvartal, kvartalet och kvartalet i US$), var och en med tre kolumner (Baidu
  excl. iQIYI, iQIYI, Baidu, Inc.). Raden ska ha exakt 12 belopp. I varje grupp ska Baidu, Inc. vara Baidu excl.
  iQIYI plus iQIYI med högst 1 MRMB i avvikelse, annars används inte tabellen. Bara RMB-grupperna sparas. Tabellen
  för tolv månader i fjärde kvartalets pressmeddelande läses inte. Före 2020-03 har pressmeddelandena ingen
  kassaflödestabell, och då finns ingen kvartalsserie.
- **Ej serie:** en definition som bara finns i ett pressmeddelande blir ingen serie. Det gäller Cloud Intelligence
  Group med DingTalk (bara 2023-08-10) och capex-raden med licensierade upphovsrätter (bara 2018-08-23). De
  redovisas i dokumentet. Alibabas intäktsuppdelning före segmentredovisningen ("Cloud computing and Internet
  infrastructure", 2015-01 – 2016-05) är en intäktskategori och inte ett segment. Den läses inte.

**Brott.** En ny definition är en egen serie och skarvas aldrig. Gränserna ovan sätts av bolagets egen text om
omklassning ("Comparative figures were reclassified", eller en ny segmentstruktur). Kontroll i koden: om ett senare
pressmeddelande inom samma definition ändrar ett tidigare publicerat värde med mer än 0,5 MRMB, och inlämningsdagen
inte är deklarerad, stoppas hämtningen med fel. Ett sådant fall utreds mot pressmeddelandets text. Säger texten att
segmentet har omklassats blir det en ny gräns (daterad ändring här). Annars blir det en vanlig revision, som
deklareras och redovisas.

**Serier ur text** (kurerad extraktion, `publish=False` tills extraktionsgranskningen är godkänd):

| Nyckel | Gren | Mening | Pressmeddelanden |
|---|---|---|---|
| `rev_bidu_ai_cloud_infra` | G4 | "revenue from AI Cloud Infra (was\|reached) RMB X billion" för rapportkvartalet | från 2025-11-18 |
| `rev_bidu_core_nonads` | G4 | Baidu Cores "non-online marketing revenue" (2020-11 – 2021-05 "non-marketing revenue") "was/reached RMB X billion" för rapportkvartalet | 2020-11-17 – 2025-11-18 (avslutad: från 2026-02 heter Baidu Core "Baidu General Business" med en annan uppdelning) |

Baidu anger inte AI Cloud som belopp i pressmeddelandena före 2025Q3, bara som tillväxt i procent. Därför finns
ingen längre AI Cloud-serie. Non-online marketing revenue är bredare än AI Cloud (även Apollo, enheter med mera), och
dokumentet säger det.

**Kodningsregler för texten** (låsta före kodningen, regex, ingen LLM):
1. Korpus: exhibit 99.1 i varje Baidu-6-K vars titel är "Baidu Announces <First|Second|Third|Fourth> Quarter ...
   Results", inlämnad från 2020-01-01. Text = `tsmc_sec.to_text`, meningar = `guidance_capex.sentences`, lokator
   "sentence #k" räknat från 0.
2. Kandidatmening: innehåller "AI Cloud Infra" eller "non-(online )?marketing revenue", och "billion".
3. Ett värde kodas bara när meningen säger "was" eller "reached" direkt före beloppet ("RMB" är valfritt, ett
   pressmeddelande 2020-11 saknar det). Belopp med "approximately", "about", "roughly", "around", "over", "more than"
   eller "exceeded" kodas inte. Beloppet är i miljarder RMB och lagras ×1000 som MRMB. Precisionen är då ±50 MRMB.
4. Kvartalet är pressmeddelandets rapportkvartal. En mening som nämner ett annat kvartal eller ett helår ("full
   year", "fiscal year") kodas inte. I fjärde kvartalets pressmeddelande kodas bara meningar före rubriken "Fiscal
   Year <år> Results".
5. Högst ett värde per serie och pressmeddelande. Två olika belopp i samma pressmeddelande för samma serie är ett
   fel som stoppar kodningen.
6. Varje rad i `curated/china_text.csv` har nummer, enhet, period, inlämningsdatum, acceptanstid, URL, accession,
   lokator och SHA-256 av meningen. Själva meningen sparas bara under `data/raw/` (gitignorerat).
7. Kandidatmeningar som inte kodas räknas och läses, och skälet redovisas i dokumentet.
8. Kontrollmodulen hämtar varje dokument på nytt (utan cache) och kontrollerar hash vid lokatorn, att talet står i
   meningen och att inlämningsdatumet stämmer med EDGAR. Alla rader kontrolleras, inte ett urval, eftersom de är få.

**US$-vy** (egna serier med suffix `_usd`, bara för de öppna serierna `rev_baba_cloud_v4`, `capex_baba_v2`,
`capex_bidu` och `capex_bidu_core`): MUSD = MRMB / kvartalets medelkurs. Medelkursen är medelvärdet av de dagliga
noon buying rates för CNY per USD i Fed:s H.10 under kalenderkvartalet. Det är samma data som FRED:s DEXCHUS, men den
hämtas från Fed:s egen historiksida (`federalreserve.gov/releases/h10/hist/dat00_ch.htm`, public domain), eftersom
FRED:s villkor förbjuder användning med maskininlärning (`ai_tracker.licenses`, regeln alfred). Ett kvartal med
färre än 55 noterade dagar får ingen kurs. `known_from` = max(RMB-radens `known_from`, kvartalets slut + 10 dagar).
H.10 kommer varje måndag med förra veckans kurser, så 10 dagar är en marginal. Sidan har bara aktuell vintage.
Antagandet att kurserna inte revideras kontrolleras inte mot arkiverade releaser. Varje RMB-vintage ger en US$-rad.

**Korskontroll mot 20-F.** För varje räkenskapsår med en 20-F med XBRL jämförs summan av fyra kvartal med årets
värde: (a) Alibabas molnsegment mot den dimensionella posten i 20-F:ns XBRL-instans (segmentaxeln), på samma
definition. Förväntad avvikelse högst 4 MRMB (avrundning). (b) Capex mot companyfacts
`PaymentsToAcquirePropertyPlantAndEquipment` (och immateriella tillgångar där det finns). Här väntas en skillnad,
eftersom bolagens egna rader har undantag. Kvoten redovisas och används inte för att justera något. Utfallet
redovisas i dokumentet, även när det inte stämmer.

**Handkontroll:** minst 6 kvartal per bolag läses i pressmeddelandet och jämförs med serien, med accession.

**Tester** (syntetiska 6-K-fixturer, inget nät): tolkningen av varje layout, att en rad med fel antal belopp ger
None, brottkontrollen (odeklarerad omräkning ger fel), vintages för jämförelsetal, Baidus kontroll att totalen är
summan, kodningsreglerna 3–5, kontrollmodulen och medelkursen (färre än 55 dagar ger ingen kurs, `known_from`).

**Beslutsregler:** inga. Serierna analyseras inte i det här spåret. Om en serie föreslås bli kärnserie står skälet i
`for_owner`, och det kräver en ny post.

#### 2026-11-25 – Ändring av CN1: dateringsregeln (efter dateringskontrollen, före analys)

Motivering: kontrollen av dateline mot 6-K visar att 5 av Baidus 28 pressmeddelanden har en dateline 2–6 dagar före
inlämningen: 2020-03-04 (6 dagar), 2020-05-20 (2), 2020-08-17 (4), 2021-02-22 (5) och 2021-05-20 (2). Siffrorna var
alltså offentliga tidigare än `known_from`. Det ger inget läckage, bara en `known_from` som är senare än nödvändigt.
Regeln ovan ("används inte") hade tagit bort Baidus capex för 2019Q4 helt, utan att något läckage undviks. Ändringen
gäller bara dateringen. Den görs innan någon serie analyseras, och inga mått räknas i spåret.
- **Ny regel:** pressmeddelandet används. `known_from` är fortfarande 6-K:ns inlämningsdatum. Avvikelsen redovisas
  per pressmeddelande i `docs/kallor/kina_sec.md`.
- `known_from` sätts inte till datumet i dateline. Datum ur löptext är mindre säkra än EDGAR:s, och regeln ska vara
  konservativ.
- Alibaba: 47 av 48 pressmeddelanden har dateline samma dag som inlämningen och 1 dagen före (2016-01-29). Inget
  ändras där.

Rättelse av koden, inte av regeln: i den första kodningskörningen matchade mönstret för rubriken "Fiscal Year <år>
Results" titeln ("Fourth Quarter and Fiscal Year <år> Results"). Då kodades inga meningar i fjärde kvartalets
pressmeddelanden. Koden följer nu regel 4 som den är skriven, och utfallet är redovisat i dokumentet.

### 2026-11-25 – S3, tillägg efter kodningen: tolkningar (inga regler ändrade)

Skrivet efter kodningen. Reglerna i posten ovan står kvar. Tolkningarna finns i
[`docs/kallor/order_orderstock.md`](kallor/order_orderstock.md), avsnittet "Tolkningar". Tre av dem rör registrets
regler:
- **Avslutad serie.** "Senaste rad" läses som senaste seriepunkt eller stopp. En gräns ("more than 100%") efter ett
  stopp öppnar inte serien igen, eftersom gränser inte är seriepunkter.
- **Digital Realtys andel.** Totaler utan angiven andel (2021Q4–2024Q4) kodas som Digital Realtys andel, eftersom samma
  tabellrad och mening senare heter "at Digital Realty's share". Talen vid 100 % andel är en egen serie.
- **Stock vid ett annat datum än periodens slut** ("as of the end of August", "as of today") kodas inte.

### 2026-11-25 – Rättelse: vad BB01RY omfattar (granskning R25-3)

Posten "M1: nettobidrag för datorer efter import (BB01RY), ägarbeslut" ovan säger under "Hur den läses" att `BB01RY`
"tar med hushållens och den offentliga sektorns köp och exporten". Den säger också att skillnaden mot `B935RY` blandar
"hushåll, offentlig sektor, export och import". Samma post säger att offentliga investeringar bara troligen ingår och
att det inte är verifierat. BEA:s `SeriesRegister.txt` listar bara `B935RC`, `DCPPRC`, `B850RC` och `B852RC` under
`BB01RC`.

Läs därför båda ställena så här: `BB01RY` tar med hushållens köp, exporten och troligen offentliga investeringar (inte
verifierat), och drar ifrån importen. Ingen definition, ingen serie, ingen datering och ingen beräkning ändras.
Seriens beskrivning i katalogen var redan rätt.

### 2026-11-25 – S1: Aristas kontraktsskulder, Q4 över ett basbyte och aktualitetsgränsen (rättning efter R17)

Rättning efter granskning R17 av spår S1 (`docs/granskning/r17-nat-servrar.md`, gren `auto14k/r17-nat-servrar`), i
spår X14 (gren `auto14k/x14-nat-servrar`). Posterna "S1: nät, optik och servrar som katalogserier" och "S1: tillägg
efter första bygget" skrivs inte om. Alla 42 serier är fortfarande katalogserier, så inget här ändrar indexet eller
tillståndsreglerna.

1. **Aristas kontraktsskulder, taggordningen (R17-1).** Posten sa: `ContractWithCustomerLiabilityCurrent` +
   `ContractWithCustomerLiabilityNoncurrent` ur samma inlämning, och i inlämningar från 2018-04-01 tas en del som saknas
   från `DeferredRevenueCurrent` respektive `DeferredRevenueNoncurrent`. I 10-Q 2018-11-05 (0001596532-18-000233) är
   `ContractWithCustomerLiabilityCurrent` (10,9 MUSD) en annan post: "As of September 30, 2018, $10.9 million of our
   contract liabilities was included in 'Other current liabilities'". Balansräkningens rader är "Deferred revenue
   318,850" och "Deferred revenue, non-current 211,005", taggade `DeferredRevenueCurrent` och
   `DeferredRevenueNoncurrent`. **Ny regel:** i inlämningar från 2018-04-01 har `DeferredRevenueCurrent` och
   `DeferredRevenueNoncurrent` företräde framför `ContractWithCustomerLiability*` för samma balansdag i samma inlämning.
   Annars gäller `ContractWithCustomerLiabilityCurrent` och `...Noncurrent`, som förut. Bland inlämningarna från
   2018-04-01 finns `DeferredRevenue*` bara i tre 10-Q (2018-05-04, 2018-08-08 och 2018-11-05). Väntad effekt: bara
   2018Q3 ändras (529,9 i stället för 221,9). 2018Q1 och 2018Q2 tog redan dessa taggar, eftersom
   `ContractWithCustomerLiability*` saknas för de balansdagarna.
2. **Aristas kontraktsskulder börjar 2018Q1 (R17-3).** Posten behandlade balansen 2017-12-31 som ASC 606. Arista bytte
   till ASC 606 2018-01-01 med den modifierade retroaktiva metoden och flyttade 16,5 MUSD förutbetalda intäkter till
   övriga skulder per 2018-01-01 (10-Q 2018-11-05). Jämförelsetalet 2017-12-31 är alltså ASC 605. **Ny regel:**
   `deferred_rev_anet` börjar med balansen 2018-03-31, den första ASC 606-balansen vid ett kvartalsslut.
   Öppningsbalansen 2018-01-01 ligger inte vid ett kvartalsslut och används inte. Effekt: 2017Q4 utgår.
3. **Q4 över ett basbyte i segment- och produktrader (R17-2).** Dells 10-K 2022-03-24 lägger ISG på en ny bas (FY2021
   räknas om från 32 588 till 33 002), men 9M FY2022 i arkivet är då den gamla basen (24 771, 10-Q 2021-12-03). 10-Q
   2022-12-05 räknar om 9M till 25 147. `sec.py` parar helåret med den 9M som fanns när helåret lämnades in, så första
   versionen av 2021Q4 blev 34 366 − 24 771 = 9 595, ett värde på ingen bas. Varje omräkning är under 2 %, så
   brottskontrollen ser inget. **Regel:** i en segment- eller produktrad används inte ett kvartal som räknas som
   differens av två perioder med samma start (i praktiken Q4 = helår − 9M, eftersom 10-Q har kvartalet direkt), när
   alla tre villkoren gäller:
   - inlämningen med det avslutande värdet räknar om ett tidigare inlämnat värde av samma rad (samma start och slut)
     med mer än `sec.TOL` (0,5 MUSD),
   - basen (9M) är inlämnad före den, och
   - basens egen inlämning räknade inte om något tidigare inlämnat värde av raden med mer än `sec.TOL`.

   Kvartalet väntar då på ett par på samma bas. Med `sec.py`:s parning kommer det när helåret lämnas in igen efter att
   9M har räknats om, alltså i nästa 10-K. Om basens inlämning själv räknar om något, låg den nya basen redan i
   10-Q:na, och 10-K:t för bara omräkningen vidare till tidigare helår. Så ser Dells ASC 606 (10-K 2019-03-29), HPE:s
   Server FY2025 (10-K 2025-12-18) och Ciscos årliga omklassningar (10-K 2020-09-03 och 2021-09-09) ut, och de
   påverkas inte. Omräkningarna jämförs inom definitionsregimen, alltså i samma fakta som serien byggs av. Väntad
   effekt: första versionerna av `rev_dell_isg` 2021Q4 (9 595) och `rev_dell_servers_networking` 2021Q4 (4 797) utgår,
   och kvartalen får 9 219 och 4 720 från 10-K 2023-03-30. Inga andra rader ändras.
   **Gräns:** ett 10-K som inför en andra ändring utöver en som redan finns i 10-Q:na upptäcks inte. Totala intäkter
   (`rev_<co>`) följer `sec.py` som förut. R17:s sökning fann ingen blandad Q4 där: Super Micros 2017Q2 använder en 9M
   som lämnades in samma dag som 10-K:t (2019-05-17).
4. **Aktualitetsgränsen (R17 N-4).** Största observerade avstånd i regeln för aktualitetsgränsen räknades bara över
   kvartal där det första värdet kom högst 100 dagar efter räkenskapskvartalets slut. Filtret undantar jämförelsetal i
   senare dokument och Super Micros sena 10-K för FY2017 (686 dagar) och FY2024 (240 dagar). Gränserna (178–212 dagar)
   ändras inte.
5. **Rättelse av fakta (R17 N-2).** `rev_csco_infra_platforms` läser inlämningar från 10-Q 2017-11-21 (första kvartal
   2016Q3), inte från 2018-11-20 som tabellen i posten säger.

Dokumentationen rättas utan ändrade regler: EMC-fusionen i Dells ISG (R17-4), ordalydelsen för Aristas åtaganden
2016–2017 (R17-5) och att HPE:s RPO är förutbetalda intäkter (R17-6). Det står i noterna och i
`docs/kallor/sec_stack_nat.md`.

**Vad som setts före denna post:** granskningsrapporten R17 med dess värden. Ur den delade rå-cachen, med S1:s kod och
utan nät: Aristas taggade kontraktsskulder och förutbetalda intäkter per inlämning 2017–2019 (belopp och datum), och
en sökning i alla S1:s segment- och produktrader och totaler efter Q4-rader ur ett 10-K som räknar om tidigare värden.
Den visade helår, 9M före och efter 10-K:t och de två Q4-värdena för de åtta fallen, och vilka 10-Q mellan
föregående 10-K och 10-K:t som räknade om något. I alla segmentfall utom Dell 2022-03-24 räknade 10-Q:na, och basens
egen inlämning, om jämförelsetalen. Därför står det tredje villkoret i punkt 3. Utan det hade granskningens regel också
hållit tillbaka fem Q4-rader på en konsekvent bas: Dells ISG och Servers and networking 2018Q4 i ett år, och
`rev_hpe_server_fy24` 2025Q3 och `rev_csco_infra_platforms` 2020Q2 och 2021Q2 för gott. Ciscos 10-K 2021-09-09, som
lämnar in FY2020 igen, räknar också om, och hålet 2020Q2 hade kortat den serien till tre kvartal. Ur S1:s tabell
syntes Dells ISG och Servers and networking 2016Q1–2017Q2 och Aristas åtaganden och kontraktsskulder 2015Q4–2018Q4.
Textblock i cachade instanser lästes för Aristas åtaganden 2016–2018, HPE:s RPO 2022–2026 och EMC-fusionen. Inga
takter räknades.

### 2026-11-25 – T1: tillägg efter R24 (rättning efter granskning R24, ingen regel ändras)

Rättningsspår X21 efter granskning R24 (`docs/granskning/r24-tillstandsregeln.md`). R24 fann inget
implementationsfel, inget läckage och inga felaktiga värden. **Testet, konstanterna och beslutsregeln i posten
"2026-11-25 – T1" ändras inte.** Utfallen är redan sedda, så posten får inte ändras i efterhand. Inget räknas om med en
ny regel. Rättningen gäller texten i resultatet, några beskrivande siffror och ett syntetiskt test.

- **R24-1. Persistensen vid h = 6 är tillståndets egen jämförelse.** Förändringen i takt (avsnitt 1) är takten vid den
  senaste perioden minus takten 6 månader (2 kvartal) tidigare. Persistensen vid h = 6 jämför samma två takter ur samma
  version, bara utan dödband. Med v2 har den tillståndets riktning i 46 av 46 prediktioner. Kriteriet för godkänt (H
  högre än persistensen) kan därför i praktiken bara uppfyllas vid h = 3, och villkor 2 avgörs av h = 3. Det är inget
  brott mot posten, men resultatet säger det nu. Effekt på beslutet: ingen.
- **R24-2.** Persistensen över alla månader med utfall, som posten säger ska redovisas, står nu i resultatet: 0,61 vid
  h = 3 och 0,56 vid h = 6. Två beskrivande tal läggs till. De är inte registrerade, räknades efter att utfallen var
  sedda och avgör inget: andelen upp på månaderna med prediktion, som är träffkvoten för en konstant prognos "upp" (0,81
  och 0,80), och hur ofta persistensen har tillståndets riktning (samma, ingen eller motsatt). `information()` räknar
  dem och `markdown()` visar dem i en egen tabell.
- **R24-3.** Det syntetiska testet för slumpvärlden prövade bara ett frö. Det prövar nu storleken över 10 frön med tre
  grenar och kräver att testet faktiskt körs. Bara syntetiska data.
- **R24-4.** Punkten "Vad som var synligt före posten" säger att bara antalen lästes ur `snapshot.backcast`. Filen som
  backcasten skrevs till före posten (`bc_realtime.csv`) hade tillstånd, index och riktning per serie för varje månad.
  Vid h = 6 innehåller den nästan utfallen. Vad som lästes går inte att kontrollera. Resultatet säger det.

**Krav på nästa registerpost för testet** (omkörningen på det skarpa registret, tidigast 2027-11). De gäller inte
körningen 2026-11-25.
1. Baslinjen vid den horisont som är lika med laggen för förändring i takt får inte vara tillståndets egen jämförelse.
   Välj en annan baslinje där, eller jämför med persistens bara vid de andra horisonterna (R24-1).
2. Spärren för bakåtfyllda serier räknas i dagens data med samma antal egna månader som i realtid vid m, inte med
   första `known_from` i den reviderade tabellen (R24-5).
3. Filer med tillstånd, index eller serier per månad som finns före posten nämns med innehåll (R24-4).
4. Om en enda version strax före V står för en grens revideringar redovisas det, med (a) också för V före den
   versionen (R24-6: G.17:s årsrevision 2026-11-24).

### 2026-11-25 – X17: rättning av KR1 efter granskningen R20 (spread vid emission)

Rättningsspår X17, körning 14, efter granskningen R20 (`docs/granskning/r20-kredit-emission.md`). Posten ändrar ingen
regel i posten "2026-11-25 – KR1" eller i de låsta kodningsreglerna i `docs/kallor/kredit_emission.md`, och de skrivs
inte om. Den säger hur fem regler som koden inte följde genomförs, och den preciserar en regel (helgdagar i T+n).
Serierna är fortfarande katalogserier med `publish=False`. Grenindex och tillstånd ändras inte.

**Vad som var känt före posten.** KR1:s 239 rader och elva serier, R20:s granskning med tabellen per kvartal i punkt 4,
och en ombyggnad av CSV:n ur KR1:s cachade dokument med koden före rättningen (byte för byte samma fil, åtta FWP:er
hoppade över). Inga nya värden räknades före posten.

1. **Självkontrollen prövar talen i tranchens del av blocket** (R20-1). Regeln "i kolumnen när den anges" genomförs så.
   För `col #j` i en gemensam tabell (tolkning 2) är tranchens del texten efter nyckel j ("2028 Notes:", eller "In the
   case of the 2028 Floating Rate Notes") fram till nästa nyckel eller radens slut, på varje rad i blocket. Ett namn som
   bara nämns ("the 2028 Notes") är ingen gräns. Nyckellistan läses med parserns `keys_of`, eftersom den definierar j.
   Uppdelningen av texten är kontrollens egen. I en verklig kolumntabell är delen cell j på de rader som har lika många
   värdeceller som beloppsraden. Belopp, förfallodag, kupong, avkastningar, pris och spread ska stå i tranchens del.
   Prisdag och likviddag får också stå på en rad i blocket utan nyckel, eftersom de gäller hela erbjudandet. Ett avsnitt
   (utan `col`) är tranchens eget block, som förut. Samma prövning gäller manuella rader. Omtolkningen med parsern ligger
   kvar för parserrader.
2. **Dokument som inte kodas listas med skäl, och det slutliga prospekttillägget är källan när FWP saknas** (R20-2).
   Ombyggnaden läser också 424B2 och 424B5. Ett preliminärt tillägg, ett tillägg utan obligationer på omslaget och ett
   slutligt tillägg till ett erbjudande som redan har en FWP som källa kodas inte och listas med skäl. Ett erbjudande har
   redan en källa om en FWP från samma bolag, inlämnad 0–7 dagar före tillägget, har minst en tranche som står på
   tilläggets omslag, eller om en källa har exakt omslagets tranchar. Ett slutligt tillägg för obligationer utan FWP blir
   källan, om parserns tranchar är exakt omslagets. Annars stoppas ombyggnaden tills raderna kodas för hand. Alla
   dokument som inte kodas skrivs till `curated/credit_issuance_skipped.csv` (bolag, formulär, inlämningsdag, accession,
   skäl). `--covers` prövar också åt andra hållet: varje slutligt tillägg för obligationer i korpusen ska ha en källa i
   CSV:n.
3. **Helgdagar i T+n** (R20-3, precisering). För USD räknas vardagar med den federala helgdagskalendern i USA (pandas
   `USFederalHolidayCalendar`). Långfredagen och en helgdag på lördag som kalendern flyttar till fredagen stänger inte
   marknaderna lika (SIFMA:s rekommendation och Federal Reserve skiljer sig). Ligger en sådan dag efter prisdagen och
   senast på den framräknade likviddagen, och för annan valuta än USD, räknas likviddagen inte fram. Parsern skriver då
   en not, raden ska kodas för hand med likviddagen ur det slutliga prospekttillägget, och inläsningen av CSV:n stoppar
   en parserrad med den noten.
4. **Talen skrivs som de står** (R20-4). CSV:n skrivs med den kortaste decimalform som läses tillbaka till samma tal
   (`repr`, ett heltal utan ".0"), inte med sex värdesiffror.
5. **Avstämning per kvartal** (R20-5). `coverage` ger också en rad per kvartal med emission: USD-tranchar efter
   likviddag i bolagets räkenskapskvartal (mittpunktsregeln) mot `debt_issued` för samma kvartal. Ett kvartal som XBRL
   ännu inte har står under "senare". Källdokumentet får tabellen.

**Väntad effekt:** ingen rad och inget värde ändras. Alla 39 erbjudanden har en FWP, ingen likviddag är framräknad, inget
tal har fler än sex värdesiffror, och R20:s kontroll per nyckel godkände alla 239 rader. Ger ombyggnaden eller
självkontrollen något annat redovisas det i källdokumentet, och de rader som ändras granskas igen.

**Tester:** de fem strikta xfail-testerna i `tests/test_r20_kredit_emission.py` blir vanliga tester utan ändrade
påståenden. Nya syntetiska tester: tranchens del med en titelrad och en rörlig tranche i samma tabell, kolumntabell,
prospekttillägg som källa och som täckt, omvänd omslagskontroll, helgdagar och osäkra dagar, avstämning per kvartal och
skrivning utan avrundning.

### 2026-11-25 – X15: rättning av S2 efter R18, före ny hämtning (rättning efter `docs/granskning/r18-kraft-datacenter.md`)

Rättningsspår X15, körning 14. Granskningen R18 av S2 fann fyra fel att rätta (R18-1–R18-4) och sex anmärkningar.
Alla fel gav för sena första versioner eller saknad historik. Tidigare poster skrivs inte om. Punkterna nedan ändrar
eller förtydligar S2:s regler och gäller från nästa hämtning. Serierna är fortfarande katalogserier, och inga takter
har räknats.

1. **Eatons segment, namnen i 2020 års 10-Q (R18-1).** 10-Q 2020-04-30, 2020-07-29 och 2020-11-03 taggar de nya
   segmenten `ElectricalAmericasMember` och `ElectricalGlobalMember`. Från 10-K 2021-02-24 heter de
   `ElectricalAmericasSegmentMember` och `ElectricalGlobalSegmentMember`. Båda namnen läses, utan markör och annars
   med `OperatingSegmentsMember`. Per inlämning vinner den första kontext som har fakta (det senare namnet först).
   Värdena är identiska i alla 14 par av segment och period där båda namnen finns. Skälet för starten 2020-01-01 i
   S2-posten rättas: det var `ElectricalAmericasMember` som 10-K för 2012 använde för ett äldre segment. Startdatumet
   står kvar, och det gör det säkert att läsa 2020 års namn.
2. **550-dagarsregelns räckvidd (R18-9).** Regelns premiss är att en 10-Q redovisar perioden och samma period året
   före. Det gäller huvudräkningarna, men inte segmentnoten efter en ny segmentindelning: Eatons 10-Q 2020-04-30
   redovisar omräknade kvartal för 2018–2019, upp till 578 dagar gamla. Regeln gäller därför flöden och balanser
   (totala intäkter, capex och RPO), inte segmentintäkter. Segmentfakta skyddas av den exakta kontexten och av
   brottkontrollen: en fakta som avviker mer än 2 % från en tidigare version av samma kvartal stoppar hämtningen.
3. **Equinix capex, den äldre taggen (R18-2).** `PaymentsToAcquirePropertyPlantAndEquipment` blir andra tagg för
   `capex_eqix`, efter `PaymentsToAcquireOtherPropertyPlantAndEquipment`. Den äldre taggen är raden "Purchases of
   property, plant and equipment" i 10-Q 2010-08-04 och 2010-10-29, i 10-Q 2012-04-27 till 2014-11-07 och i 10-Q
   2016-11-04, och den står parallellt med den nya taggen i 10-Q 2017–2018. I två inlämningar har Equinix den nya
   taggen på capex-raden och den äldre på ett fastighetsköp: 10-K 2011-02-25 ("Purchase of Amsterdam IBX property",
   14 861 tusen USD för 2010) och 10-Q 2011-04-29 ("Purchase of Paris 4 IBX property", 14 951 för Q1 2011). Utan de
   två fakta är taggarna identiska i alla 18 överlappande perioder. Regeln för taggval förtydligas, för alla S2:s
   flöden: en fakta under en tagg med lägre prioritet används inte ur en inlämning där den har ett annat värde än en
   tagg med högre prioritet för samma period. Då står taggen på en annan rad i just den inlämningen. Det tar i dag
   bort exakt de två fakta. Granskningens förslag "bara fakta ur 10-Q" räcker inte, eftersom 10-Q 2011-04-29 också har
   fastighetsköpet under den äldre taggen.
4. **Vertivs segment (R18-3).** Täckningsskälet för brutto i S2-posten håller inte. 10-K 2024-02-23 saknar medlemmen
   utan markör, men 10-K 2025-02-18 har helåret 2023 som jämförelsetal, så den externa försäljningen förlorar inget
   kvartal. Bruttoserierna `rev_vrt_americas`, `rev_vrt_apac` och `rev_vrt_emea` behålls: segmentnotens tabell är
   "Sales" med en rad "Eliminations". Nya katalogserier: `rev_vrt_americas_net`, `rev_vrt_apac_net` och
   `rev_vrt_emea_net`, segmentets externa försäljning ("Net sales"). Kontext exakt: bara
   `StatementBusinessSegmentsAxis` med `AmericasSegmentMember`, `AsiaPacificSegmentMember` respektive
   `EMEASegmentMember`. Inlämningar från 2020-01-01. Gren G7, och datering, brottkontroll, aktualitetsgräns, licens
   (SEC, klass `ja`) och `publish=True` som bruttoserierna. Ett odeklarerat brott stoppar hämtningen.
5. **`instance_name` väljer inte `defnref.xml` (R18-4, gemensam kod).** `sec_segment.instance_name` sorterar
   kandidaterna efter längd, och `defnref.xml` (en referensfil i inlämningar 2009–2011) vann. Filen utesluts nu. I den
   delade cachen finns den i 11 inlämningar: Digital Realty (10-Q/A 2010-08-12, 10-Q 2010-11-09, 10-K/A 2011-03-25,
   10-Q 2011-05-09) och Microsoft (sju inlämningar, 10-Q 2009-10-23 till 10-Q 2011-04-28). Nvidias inlämningar
   2012–2013 har den inte. Serierna på denna gren som läser instanser före 2012 är `rev_dlr`, `capex_dlr` och
   `dep_msft`. Det är en läsrättning, och ingen regel för dem ändras. Bland Microsofts sju inlämningar har bara 10-Q
   2011-01-27 och 2011-04-28 `msft:DepreciationAmortizationAndOther` utan dimension. De fem tidigare använder en annan
   tagg, som P1 skrev.
6. **Digital Realty, bolagets fakta 2010–2011 (följd av R18-4).** I 10-Q 2010-11-09, 10-K/A 2011-03-25 och 10-Q
   2011-05-09 har alla fakta för intäkter och capex `LegalEntityAxis`: Digital Realty Trust, Inc. med
   `ParentCompanyMember` och partnerskapet med `DigitalRealtyTrustLPMember`, med samma värden. Där finns inga fakta
   utan dimension. Det är därför 2010Q3–2011Q1 får sin första version ett år för sent, inte `defnref.xml` som
   granskningen trodde. Regel: per inlämning och tagg läses fakta utan dimension. Saknas de, läses fakta med bara
   `LegalEntityAxis` = `ParentCompanyMember`. Den medlemmen förekommer bara i de tre inlämningarna.
7. **Pariteten för DLR (R18-10).** Jämförelsen mellan instansserien och companyfacts-serien (S2-tillägget, punkt 5)
   är en engångskontroll vid bygget, inte en kontroll i koden. Den görs om efter rättningarna, och resultatet står i
   `docs/kallor/sec_stack_kraft.md`.

**Vad som setts före denna post:** granskningen R18 med alla dess siffror, också de simulerade rättningarna (Eatons
segment 32 kvartal från 2018Q4, `capex_eqix` 69 kvartal från 2009Q3, Vertivs externa EMEA 31 kvartal och de interna
andelarna 5 och 34 %). Egna kontroller av täckning och konsistens: medlemmar och markörer per inlämning hos Eaton
2020–2021 och om värdena är lika i överlappet. Båda capex-taggarnas fakta per inlämning hos Equinix i companyfacts,
med värden (YTD 2009–2019), och kassaflödesanalysen i 10-Q 2011-04-29. Digital Realtys fakta för intäkter och capex
(värden och dimensioner) i de fyra inlämningarna med `defnref.xml`, och vilka inlämningar som har
`ParentCompanyMember`. Antalet fakta med Microsofts tagg i de sju inlämningarna. Nvidias indexfiler 2012–2013. Inga
serier har byggts med reglerna ovan.

### 2026-11-25 – X17 (tillägg): var en tranche börjar i självkontrollen

Tillägg till posten "2026-11-25 – X17", punkt 1, efter den första körningen av den nya självkontrollen mot KR1:s cachade
dokument. Den gav ett falskt fel: Amazons villkorsbilaga 2021 skriver "2024 Notes May 12, 2024" utan kolon, så
förfallodagen räknades till 2023 Notes. En tranches text börjar därför vid nyckeln med kolon som tillval, eller vid "In
the case of (the) <nyckel>", och bara på en rad där värdet (efter etiketten, eller hela fortsättningsraden) börjar med
en nyckel. En nyckel efter "the" börjar ingenting. Andra rader i blocket räknas som rader utan nyckel, där bara prisdag
och likviddag får stå. Det är parserns form. Tillägget gäller kontrollen, inget värde: efter det ger kontrollen 238
rader rätt och den manuella raden med beloppet utanför blocket, som förut.

### 2026-11-25 – X15: utfall efter hämtningen

Reglerna i X15-posten ovan gjorde vid hämtningen det posten säger. Regeln för taggval tar bort exakt två fakta, båda
Equinix äldre capex-tagg (10-K 2011-02-25 och 10-Q 2011-04-29). Undantaget från 550-dagarsregeln behåller exakt sex
segmentfakta, Eatons 2018Q1–Q3 för båda segmenten ur 10-Q 2020-04-30. Inga brott upptäcktes, och inga värden i
tidigare hämtade kvartal ändrades. En rättelse av en detalj i punkt 2: kvartalen 2018Q1–Q3 slutar 578–761 dagar före
inlämningen, inte "upp till 578". Och i punkt 3: radens namn "Purchases of property, plant and equipment" gäller 10-Q
2010–2014. I 10-Q 2016-11-04 och 2017–2018 heter samma rad "Purchases of other property, plant and equipment".
Effekterna per serie står i `docs/kallor/sec_stack_kraft.md` ("Rättning efter R18") och för `dep_msft` i
`docs/kallor/sec_avskrivningar.md`.

### 2026-11-25 – CN1: korskontrollen av Alibabas capex körs som registrerad (rättning efter R21, granskningen av CN1)

Rättningsspår X18 efter granskning R21 (`docs/granskning/r21-kina-sec.md`, R21-3). Registerposten "2026-11-25 – CN1"
säger att capex ska jämföras med companyfacts `PaymentsToAcquirePropertyPlantAndEquipment` och immateriella
tillgångar där det finns. Koden jämförde i stället Alibaba med en bredare rad i 20-F-instanserna
(`PaymentsToAcquireLandUseRightsPropertyAndEquipment`, med mark och kontorscampus), läste 20-F först från 2019 och
prövade aldrig `capex_baba_v1`. Det är ett fel i koden, inte i regeln. Här skrivs regeln ut med Alibabas begrepp, så
att koden kan följa den. Inga serier, värden eller datum ändras. Korskontrollen skriver ingenting.

**Vad som var sett före posten.** R21:s granskning, som redovisar utfallet av den registrerade kontrollen (exakt för
`capex_baba_v1` FY2015–FY2018 och `capex_baba_v2` FY2019–FY2020). Alibabas companyfacts: listan över poster för
`PaymentsToAcquireOtherPropertyPlantAndEquipment` och `PaymentsToAcquireIntangibleAssets` (år, 20-F och värden).
Namnen på kassaflödesbegreppen och segmentmedlemmarna i 20-F-instanserna FY2016–FY2018, utan värden. Ingen summa av
kvartal är räknad av spåret före posten.

**Regel (b) för Alibaba, utskriven.** Summan av fyra räkenskapskvartal (april–mars) jämförs med:
- `capex_baba_v1` (anläggningstillgångar och immateriella tillgångar i en rad): companyfacts
  `PaymentsToAcquireOtherPropertyPlantAndEquipment` plus `PaymentsToAcquireIntangibleAssets`, båda ur samma 20-F
  (den senaste som har båda för året). Dessutom bolagets egen rad i 20-F-instanserna, som är ett tilläggsbegrepp och
  inte finns i companyfacts: `PaymentsToAcquireOtherPropertyPlantAndEquipmentIntangibleAssets` (20-F FY2016),
  `PaymentsToAcquireOtherPropertyEquipmentIntangibleAssetsAndLicensedCopyrightsOfVideoContent` (20-F FY2017) och
  `PaymentsToAcquireOtherPropertyEquipmentIntangibleAssetsAndLicensedCopyrights` (20-F FY2018).
- `capex_baba_v2` (anläggningstillgångar utan immateriella): companyfacts
  `PaymentsToAcquireOtherPropertyPlantAndEquipment` (den senaste 20-F:n för året).
- Samma definition: förväntad avvikelse högst 4 MRMB (avrundning), som för molnet. Utfallet redovisas även om det
  inte stämmer.
- Kvoten mot `PaymentsToAcquireLandUseRightsPropertyAndEquipment` (20-F-instansen) redovisas bara för serie och år där
  ingen av raderna ovan finns. Den används inte för att justera något.
- 20-F läses från 2016-01-01, för både molnet och capex. Då prövas också FY2016 för `rev_baba_cloud_v1`.

Baidus kontroll ändras inte.

**Förtydliganden utan regeländring.**
- `capex_baba_v1` innehåller licensierade upphovsrätter till videoinnehåll, åtminstone från FY2017 (begreppsnamnet i
  20-F FY2017 ovan). I pressmeddelandet 2018-11-02 delas 2017Q3 upp i 5 322 MRMB anläggningstillgångar och 2 680 MRMB
  upphovsrätter och immateriella tillgångar, sammanlagt `v1`:s 8 002 (R21-4). Raden är fortfarande bolagets egen rad.
  Noten och etiketten säger nu vad den innehåller.
- Gränsen för DingTalk (`v2` → `v3`) står i pressmeddelandet 2023-11-16 självt, inte bara i 2024-08-15 som posten och
  dokumentet citerade (R21 N-5). Gränsen är densamma.
- Posten säger 47 pressmeddelanden från Alibaba. Koden läser 48, ett per kvartal 2014Q4–2026Q3, utan lucka (R21 N-1).

### 2026-11-25 – S3: GE Vernovas order i GW delas och konverteringar kodas (rättning efter granskning R19)

Skäl: fynd F-1 i [`docs/granskning/r19-order-orderstock.md`](granskning/r19-order-orderstock.md). Serien
`ob_gev_orders_gas_power_equipment_q_level_gw` skarvar två definitioner. 2025Q1 anger "gas turbine orders". Från 2025Q2
är talet bara ordren bland kvartalets nya kontrakt ("new gas equipment contracts"). Reservationer som blir order står i
en egen mening ("converted ... to orders") och är inte kodade. Registrets regel tar "alla tal i GW för gasturbiner:
order, orderstock och reservationer". Bolaget kallar konverteringarna order, så de hör till regeln. Tolkning 6 i
källdokumentet tog bort dem.

Skrivet efter att talen var lästa. R19 läste meningarna och låste konverteringarna i sitt test. Spår X16 läste samma
meningar före posten: GW-meningarna i GE Vernovas sju pressmeddelanden 2025Q1–2026Q3. Posten rättar alltså en
definition. Den är ingen förregistrering på oläst data. Inga takter räknas.

Regler. De gäller GE Vernova, segment `gas_power`, enhet GW, komponent `equipment`, fönster kvartal och form nivå:
- **Två nya mått.** `orders_new_contracts` är ordren bland kvartalets nya kontrakt ("Y GW of orders" i meningen om
  "new gas equipment contracts"). `orders_converted` är reservationer som blev order i kvartalet ("Converted X GW of
  existing slot reservation agreements").
- **Delning.** `orders` i GW är bara talet "gas turbine orders" från tiden före den nya uppställningen (2025Q1). Från
  2025Q2 kodas ordren i GW som `orders_new_contracts`. Läsaren avvisar en rad `orders` i GW för en period från 2025Q2.
  Om talet för 2025Q1 innehåller konverteringar går inte att avgöra. Därför skarvas det inte med något.
- **Inget läggs ihop.** Kvartalets orderingång i GW är summan av de två måtten. Den blir ingen egen serie, eftersom
  extraktionen inte räknar om något (posten för S3 ovan). Seriernas noter säger hur den bildas.
- **Fortfarande inte kodat:** nya reservationer i kvartalet, summan av nya kontrakt och levererade GW. Reservationerna
  syns redan i stocken. Levererade GW är inget mått som reglerna nämner för GE Vernova.
- Första dokumentet, stoppregeln, dateringen och `publish=False` gäller som i posten för S3. Stoppregeln ger ett stopp
  för `orders` i GW i pressmeddelandet för 2025Q2, eftersom det inte längre anger "gas turbine orders".

Väntad effekt: `ob_gev_orders_gas_power_equipment_q_level_gw` försvinner ur katalogen, eftersom bara 2025Q1 är kvar
(en period). Två nya katalogserier får sex kvartal var, 2025Q2–2026Q3:
`ob_gev_orders_new_contracts_gas_power_equipment_q_level_gw` och `ob_gev_orders_converted_gas_power_equipment_q_level_gw`.
Övriga 60 serier får samma värden. Bara noterna och luckorsakerna ändras (rättningarna R-2 och R-4, som inte rör
registrets regler).
