# C3: teknisk specifikation för faktormodellen och variant DF

Daterad post enligt F-E5 och F-B22 (`docs/granskning/r6_c0.md`, antagen ordagrant i måttregistret 2026-11-23).
Skriven **2026-11-24, före den första körningen på verklig data**. Commit-hashen för den här filen är den daterade
posten. Efter den committen ändras ingenting här. En ändring blir en ny metodfamilj (G-E), som bara utvärderas i
det skarpa registret.

Före posten har koden bara körts på simulerade data (`tests/test_factor.py`). På den verkliga tabellen har bara
metadata lästs (frekvens, första period, första `known_from`, källa och enhet per serie). Inga takter, faktorer
eller fel har beräknats.

Kod: `src/ai_tracker/factor/` (`dfm.py`, `realtime.py`, `guard.py`) och `src/ai_tracker/nowcast/df.py`.
Specifikationsversion i koden: `SPEC_VERSION = "c3-v1"`.

## 1. Serier per block (F-B21)

Kärnserierna enligt G-A (2026-11-24). G1, G2 och årsserier ingår inte (F-B20, F-B21), alltså inte
`g2_price_at_capability_gpqa`, `eu_ai_ent_eu27`, `eu_ai_ent_se` och `pjm_lf_peak_{dom,rto}_h5`. Listan är fast för
hela backtesten. En serie är med från sitt första `known_from` och från den prognosdag då den uppfyller kravet i
avsnitt 3. BTOS ingår som en serie per regim (varje nyckel `btos_ai_use_v<n>`), med saknade värden utanför regimen.

Typ: M = månad (även dags- och veckoserier efter månadsaggregering), QF = kvartalsflöde, QS = kvartalsstock eller
andel. Datum ur metadata 2026-11-24.

**Block "capex" (capex och leverantörsled: G5, G6, G7), 25 serier**

| Serie | Typ | Första period | Första `known_from` | Källa |
|---|---|---|---|---|
| `capex_hyp4` | QF | 2017Q3 | 2018-10-26 | release |
| `us_constr_datacenter` | M | 2014-01 | 2024-07-01 | backfill |
| `us_pfi_info_proc_eq_sw` | QF | 1947Q1 | 1947-05-01 | backfill |
| `capex_ocf_hyp4` (härledd, `capex_hyp4`/`ocf_hyp4`) | QS | – | – | derived |
| `capex_orcl` | QF | 2010Q3 | 2011-09-23 | release |
| `tsmc_revenue_m` | M | 2006-04 | 2006-05-10 | release |
| `us_ip_semis_m` | M | 1972-01 | 2016-04-15 | release (vintages) |
| `us_ip_computers_m` | M | 1972-01 | 2016-04-15 | release (vintages) |
| `us_imports_tw_m` | M | 1985-01 | 1985-03-17 | backfill |
| `us_imports_kr_m` | M | 1985-01 | 1985-03-17 | backfill |
| `rev_amd_datacenter` | QF | 2021Q2 | 2022-08-03 | release |
| `rev_avgo_semis` | QF | 2017Q4 | 2019-03-15 | release |
| `rev_mrvl_datacenter` | QF | 2022Q1 | 2023-05-26 | release |
| `asml_net_sales` | QF | 2006Q2 | 2007-01-18 | release |
| `us_elec_sales_com_{va,tx,ga,az,or,oh}_m` (6) | M | 2010-01 | 2010-05-01 | backfill, release |
| `eia930_avg_pjm_dom_m` | M | 2018-10 | 2019-08-21 | backfill |
| `eia930_avg_erco_m` | M | 2015-07 | 2016-07-25 | backfill |
| `eia930_avg_azps_m` | M | 2015-07 | 2016-07-25 | backfill |
| `eia930_avg_soco_m` | M | 2018-11 | 2018-12-07 | backfill |
| `eia930_avg_srp_m` | M | 2018-08 | 2018-09-07 | backfill |

**Block "demand" (efterfrågan: G2, G3, G4 med RPO, G8), 29 serier plus BTOS per regim**

| Serie | Typ | Första period | Första `known_from` | Källa |
|---|---|---|---|---|
| `btos_ai_use_v1`, `_v2`, `_v3` (en per regim) | M (från 2W) | 2023-09 / 2025-11 / 2026-10 | 2023-09-28 / 2025-12-04 / 2026-11-05 | release |
| `g3_npm_{openai,anthropic_sdk,langchain,vercel_ai}_w` | M (från W) | 2020-07 till 2023-06 | 2020-07-14 till 2023-06-20 | backfill |
| `g3_pypi_{openai,anthropic,langchain,llama_index}_wed` | M (från W) | 2020-02 till 2023-02 | 2020-02-25 till 2023-02-28 | backfill |
| `g3_wiki_{chatgpt,llm,genai}_en` | M (från W) | 2022-10 till 2023-02 | 2022-10-25 till 2023-02-21 | backfill |
| `g3_cf_bots_ai_crawler_share`, `g3_cf_ai_purpose_user_action` | M (från W) | 2024-08 / 2024-12 | 2024-09-02 / 2025-01-06 | backfill |
| `rev_aws` | QF | 2014Q1 | 2015-04-24 | release |
| `rev_google_cloud` | QF | 2020Q1 | 2021-04-28 | release |
| `rev_msft_cloud` | QF | 2020Q3 | 2021-10-26 | release |
| `rev_nvda_datacenter` | QF | 2017Q2 | 2018-08-16 | release |
| `rev_orcl_cloud` | QF | 2021Q3 | 2022-09-13 | release |
| `rpo_hyp4` | QS | 2019Q4 | 2020-02-04 | release |
| `ai_postings_share_{us,gb,de,fr,ca,au,ie}_d` | M (från D) | 2019-01 | 2024-04-30 | release |
| `ai_postings_share_{it,nl}_d` | M (från D) | 2019-01 | 2025-02-08 | release |

Kvartalsstockar och andelar (QS, F-B20): `rpo_hyp4` och `capex_ocf_hyp4`. Övriga kvartalsserier är flöden (QF),
även `us_pfi_info_proc_eq_sw` (årstakt i SAAR).

## 2. Transformation och fönster

- **Takt** exakt som tillståndsmotorn räknar den (registrets avsnitt 1, `state.measures.measure_path` på
  `as_of(prognosdag)`): dags- och veckoserier aggregeras till kalendermånad med motorns regel (medel för andelar,
  priser och "per"-enheter, annars summa), och den sista, ofyllda månaden tas bort. Takt = 12 månaders (månad) eller
  4 kvartals (kvartal) förändring i 100 × log, eller i procentenheter för andelar. Metoden per serie följer
  `state.measures.rule_for`, så `g3_cf_*` (enhet "procent") räknas i log som i tillståndet. En lucka i serien ger
  saknad takt.
- **Fönster:** taktmånader från **2010-01** till prognosdagens kalendermånad. Ett kvartalsvärde ligger i kvartalets
  sista månad (etiketten enligt mittpunktsregeln). Takt före 2010-01 används inte, inte heller för standardiseringen.
- **Månadsgrid:** modellen går månad för månad från 2010-01 till prognosdagens månad. Månader utan data (ojämn
  publicering i slutet och luckor) hanteras av Kalman-filtret.

## 3. Standardisering och urval (F-B16)

- z = (takt − medel) / SD (ddof = 1), där medel och SD räknas över seriens takt i fönstret, i `as_of(prognosdag)`.
  Percentilen i avsnitt 1 används inte.
- En serie används på en prognosdag när den har **minst 24 månatliga eller 8 kvartalsvisa taktvärden** i fönstret.
  SD = 0 utesluter serien.
- Ett block skattas på en prognosdag när **minst 2 serier** är valbara. Annars saknas blockets faktor den dagen, och
  DF saknas för den prognosen och kan inte vara träningsrad.

## 4. Modell (F-B20, F-B22)

Ett block i taget. Blocken skattas var för sig: en faktor per block, laddningarna är begränsade till blocket och det
finns ingen korskoppling mellan blocken.

- Mätekvation: z_it = λ_i · h_i′ s_t + e_it, med s_t = (f_t, f_{t−1}, f_{t−2})′ och e_it ~ N(0, R_i), oberoende över
  serier och tid (vitt brus, inte AR(1)).
- Mariano–Murasawa enligt F-B20: h = (1, 0, 0) för månadsserier och för kvartalsstockar och andelar (QS, i kvartalets
  sista månad). h = (1/3, 1/3, 1/3) för kvartalsflöden (QF, kvartalets årstakt = medel av de tre månadernas årstakt,
  observerad i kvartalets sista månad). Ett kvartalsvärde läggs in först från sitt `known_from` (genom `as_of`).
- Faktordynamik: AR(1), f_t = a · f_{t−1} + u_t med u_t ~ N(0, 1). Innovationsvariansen är fixerad till 1
  (skalnormering). |a| ≤ 0,99.
- Starttillstånd: s_0 ~ N(0, Σ_0), där Σ_0 är den stationära kovariansen, Cov(f_t, f_{t−k}) = a^k / (1 − a²).
- Tecken: efter skattningen vänds faktorn och laddningarna om summan av laddningarna är negativ, så att en högre
  faktor betyder högre takt.

## 5. Skattning (EM), Kalman-filter och utjämning (F-B17, F-B22)

- **Start (deterministisk, samma på varje prognosdag):** f⁰_t = tvärsnittsmedel av de observerade z-värdena i månad
  t, där ett kvartalsvärde räknas i alla tre månader i sitt kvartal. Månader utan data interpoleras linjärt, och före
  första och efter sista värdet hålls värdet konstant. a⁰ = OLS av f⁰_t på f⁰_{t−1} utan konstant, klipps till
  ±0,99. f⁰ skalas så att residualens SD i den AR(1)-skattningen är 1. λ⁰_i = OLS av z_i på h_i′ s⁰_t utan konstant,
  och R⁰_i = residualvariansen, med golvet 0,01. (PCA används inte, eftersom panelen saknar en balanserad del före 2023.)
- **E-steg:** Kalman-filter i informationsform (R diagonal, alla matriser 3 × 3) och RTS-utjämnare. Saknade
  observationer faller bort ur summorna. Log-likelihood med Woodbury-identiteten och determinantlemmat.
- **M-steg (Shumway–Stoffer, Bańbura–Modugno 2014 för saknade data):**
  λ_i = Σ z_it h′E[s_t] / Σ h′E[s_t s_t′]h över de observerade t. R_i = medel över de observerade t av
  z² − 2λ_i z h′E[s_t] + λ_i² h′E[s_t s_t′]h, med golvet **0,01**.
  a = Σ_t E[f_t f_{t−1}] / Σ_t E[f_{t−1}²], t = 1..T, klipps till ±0,99. Innovationsvariansen skattas inte (= 1).
- **Konvergens:** |ΔlogL| / medel(|logL_ny|, |logL_gammal|) < **1e-4**, högst **200** iterationer. Rapporteras per
  skattning (`converged`, `n_iter`).
- **Realtid (F-B17):** laddningar, a och R skattas om från samma start vid **varje prognosdag**, på tabellen trunkerad
  till `known_from` ≤ prognosdagen. Faktorn för prognosdagen är den utjämnade banan över data kända den dagen. Ingen
  parameter skattas på senare data. Ingen varmstart från en tidigare prognosdag.
- **Utdata:** `realtime.vintage(tabell, dag)` ger den utjämnade banan (och variansen) för båda blocken, månad för månad
  från 2010-01 till dagens månad, plus laddningar, R, a, log-likelihood och vilka serier som ingick.
  `realtime.realtime_monthly(tabell, start, slut)` ger den månatliga realtidsserien för C4: månad m = värdet för m i
  banan skattad på m:s sista dag. Resultaten cachas i `data/cache/factor/c3-v1/` (committas inte), med nyckeln
  prognosdag + hash av raderna kända den dagen.

## 6. Variant DF (F-B18, F-B19)

- Huvudmodellen är fast: **B1 för N1, N3 och N4, B2 för N2**. Den byts inte om huvudmodellen senare byts.
- Miss r_s = 100 × (log utfall_s − log huvudmodell_s), utfall = första versionen.
- Regressorer: konstant, Δf_capex och Δf_demand. Δf = medel av faktorn över målperiodens månader minus medel över
  föregående periods månader, båda ur faktorbanan skattad på prognosens egen prognosdag. Månader: kalenderkvartalet
  (N1, N4), räkenskapskvartalets tre kalendermånader, alltså den månad det slutar i och de två före (N3), och månad m
  mot m − 1 (N2).
- Träningsrader (pseudo-realtid): tidigare målperioder s med Δf ur banan på s:s egen prognosdag. En rad ingår bara om
  s:s utfall (första versionen) har `known_from` ≤ den aktuella prognosdagen och båda blocken fanns på s:s prognosdag.
  Rader som huvudmodellernas backtest redan utesluter (utfall känt på prognosdagen, definitionsbrott för N3 och N4)
  ingår inte. Expanderande fönster, OLS, **minst 12 rader**.
- Prognos = huvudmodell × exp(r̂/100). Felet blir e_DF = e_huvudmodell + r̂.
- Jämförelsemodell (F-B10): den bästa efter MAE av B0, B1, nuvarande huvudmodell och modellen DF bygger på, på samma
  rader (N1, N3, N4: B0 och B1; N2: B0, B1 och B2). DM-test på absolutfel (Newey–West, HLN) mot den.
- Holm (F-B9): familjerna N1 {B3, DF}, N2 {B3, DF}, N3 {B2, B3, DF} och N4 {V1, DF}. I utvecklingskörningen ingår
  de andra medlemmarna med p = 1. Delperiod från 2023Q1 (N2: 2023-01).

## 7. Holdout (G-E, F-E1–F-E6)

- `factor/guard.py`: `DEV_END = 2025-06-30` och `HOLDOUT_OPEN = False`. Varje faktorskattning, faktorbana,
  DF-prognos och DF-fel med prognosdag efter 2025-06-30 ger `HoldoutClosed`. Utvecklingskörningen läser dessutom bara
  rader med `known_from` ≤ 2025-06-30, så utfall som blev kända senare inte finns (F-E1).
- Holdouten öppnas en gång för hela familjen C3 (DF för N1–N4), i en körning, efter ägarens godkännande, och först när
  C4:s specifikation med tillägget i G-D är committad (F-E4). Öppningen loggas i `docs/holdout_logg.md`.
- Utvecklingskörningen avgör ingenting (F-E6). Befordran prövas på holdouten: Holm-p < 0,10 och lägre MAE både på
  holdouten och i utvecklingsperioden. Vid n < 8 på holdouten görs inget test. Enligt registret kan DF i praktiken
  bara befordras för N2.
- Skarpa DF-prognoser kräver faktorer på holdoutens prognosdagar (träningsraderna, F-B18) och kan därför inte byggas
  förrän holdouten är öppnad.

## 8. Kända svagheter, redovisade i förväg

- **Efterfrågeblocket** består av kvartalsserier fram till 2023 (PyPI från 2023-01 och npm från 2023-07 får 24
  taktvärden, Indeed från 2024-04-30). Fram till dess är faktorn i stort sett en interpolerad kvartalsfaktor (F-B21).
  Blocket kan skattas först när två serier har 8 kvartalsvisa taktvärden, enligt metadata omkring 2020-05.
  DF kräver båda blocken, så DF:s rader börjar tidigast då.
- **BTOS och Cloudflare** får inte 24 månatliga taktvärden före 2025-06-30 och ingår i praktiken inte i utvecklingen.
- **Etiketter:** mittpunktsregeln förskjuter räkenskapskvartal. Nvidias "Q3" innehåller oktober, Oracles "Q3" juni,
  och liknande gäller för Broadcom och Marvell. Ingen läckage (`known_from` styr), men faktorn förskjuts upp till en
  månad för de serierna.
- **Holdouten är delvis känd** (F-E5): baslinjefelen för 2025-07–2026-10 är publicerade i `docs/resultat/n1.md`–`n4.md`,
  och de bakåtfyllda serierna (`us_constr_datacenter`, importserierna, BEA, EIA före arkivet, npm, PyPI, Wikipedia) har
  dagens vintage med revideringar och säsongsfaktorer från tiden efter 2025-06.
- **Litet n:** enligt R6 (avsnitt 6) har N1 och N3 omkring 8–11 utvecklingsrader med 12 träningsrader, N4 inga, och N2
  några tiotal. Utvecklingsresultaten för N1, N3 och N4 är därför bara beskrivande.
