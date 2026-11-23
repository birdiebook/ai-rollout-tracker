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
