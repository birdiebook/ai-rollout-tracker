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
