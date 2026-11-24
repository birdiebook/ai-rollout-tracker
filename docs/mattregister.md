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
