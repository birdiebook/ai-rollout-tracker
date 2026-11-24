# C4: regim och strukturbrott, utvecklingsperioden

Körd 2026-11-24 med `python -m ai_tracker.regime`, efter att specifikationen `docs/steg2/c4_spec.md` var committad
(commit `735dc64`, tillägget till G-D och C4:s lås enligt F-D7 och F-E4). Specifikationen är inte ändrad efter
körningen. Ingenting är justerat efter att resultaten har setts. En rättning gällde bara datumtypen i
sammanslagningen för (c) och ändrar inga val.

**Holdouten är stängd.** Alla beräkningsdagar är månadsslut 2012-01-31–2025-06-30 (162 dagar), och körningen läste
bara rader med `known_from` ≤ 2025-06-30 (`regime/guard.py`, `factor/guard.py`). Inga regimsannolikheter, brott eller
faktorbanor efter 2025-06-30 har beräknats eller lästs. Holdouten öppnas för C3 och C4 i samma körning, efter ägarens
godkännande.

**C4 är beskrivande och befordras inte** (F-D6). Siffrorna nedan avgör ingenting.

## Markov-switching per faktorblock

MSIH(2)-AR(0) med EM på C3:s utjämnade faktorbana, omskattad varje beräkningsdag. Alla 189 skattningar konvergerade
(högst 67 iterationer).

| Block | Dagar med sannolikhet | Första | Skiften till inbromsning | Tillbaka | Månader rapporterad expansion / inbromsning | Andel dagar med P ≥ 0,5 | Andel med 0,2 < P < 0,8 |
|---|---|---|---|---|---|---|---|
| capex och leverantörsled | 127 | 2014-12-31 | 3 | 3 | 13 / 114 | 0,91 | 0,04 |
| efterfrågan | 62 | 2020-05-31 | 2 | 1 | 11 / 51 | 0,86 | 0,00 |

Rapporterade skiften (regeln i F-D2, på de lagrade realtidsvärdena):

| Block | Till inbromsning | Till expansion |
|---|---|---|
| capex | 2015-01, 2022-10, 2025-01 | 2022-07, 2024-07, 2025-04 |
| efterfrågan | 2020-06, 2025-03 | 2024-05 |

Vad som syns:

- **"Inbromsning" är i praktiken "den lägre takten av två".** Regimen med högre medel fångar få och extrema
  episoder (för capex μ ≈ 2,3–7,7 mot −2,6–−0,3 i faktorns enhet, för efterfrågan på 2025-05-31 μ 10,4 mot 1,7).
  Därför är 86–91 % av dagarna inbromsning. Det är den svaghet som specifikationen redovisade i förväg (MS på nivån
  av en persistent faktor).
- **Sannolikheterna är nästan alltid nära 0 eller 1** (4 % respektive 0 % av dagarna mellan 0,2 och 0,8), men de
  **växlar mellan närliggande dagar**: capex korsar 0,5 sju gånger och efterfrågan fyra gånger. Ett exempel är capex
  2024-05 till 2025-06 (0,97, 0,04, 0,01, 0,21, 0,57, 0,96, 0,74, 0,99, 0,98, 0,92, 0,01, 0,02, 0,02, 0,10). Orsaken är att
  både faktorbanan (C3) och MS-modellen skattas om varje dag, så regimerna kan beskriva olika episoder från dag till
  dag. Regeln om två dagar i rad dämpar men tar inte bort det.
- **Efterfrågeblocket** har bara 2 serier fram till 2022 och 60 månaders historik bara tack vare `rev_aws` från 2015.
  Fram till 2023 är det en interpolerad kvartalsfaktor (C3).

## Strukturbrott (BOCPD)

58 olika kärnserier räknades i tillståndet någon gång (14–58 per dag). 4 183 serie-dagar har ett värde för
P(r_T ≤ 2).

| Frekvens | Serie-dagar | P ≥ 0,8 | Median P(r_T ≤ 2) |
|---|---|---|---|
| månad | 2 985 | 9 | 0,05 |
| kvartal | 1 066 | 6 | 0,16 |
| år | 132 | 78 | 0,85 |

12 rapporterade brott (0,29 per 100 serie-dagar), efter regeln om 3 perioders tystnad:

| Beräkningsdag | Gren | Serie | Senaste period | P(r_T ≤ 2) |
|---|---|---|---|---|
| 2016-06-30 | G6 | `us_imports_tw_m` | 2016-04 | 0,81 |
| 2020-01-31 | G7 | `pjm_lf_peak_dom_h5` | 2020 | 1,00 |
| 2020-01-31 | G7 | `pjm_lf_peak_rto_h5` | 2020 | 1,00 |
| 2020-06-30 | G7 | `us_elec_sales_com_az_m` | 2020-04 | 0,89 |
| 2020-06-30 | G7 | `eia930_avg_srp_m` | 2020-05 | 0,83 |
| 2020-07-31 | G7 | `us_elec_sales_com_ga_m` | 2020-05 | 0,92 |
| 2021-07-31 | G7 | `us_elec_sales_com_tx_m` | 2021-05 | 0,82 |
| 2023-08-31 | G4 | `rpo_hyp4` | 2023Q2 | 0,81 |
| 2023-10-31 | G5 | `capex_ocf_hyp4` | 2023Q3 | 0,81 |
| 2024-02-29 | G7 | `pjm_lf_peak_dom_h5` | 2024 | 0,83 |
| 2024-02-29 | G7 | `pjm_lf_peak_rto_h5` | 2024 | 0,92 |
| 2024-10-31 | G7 | `us_elec_sales_com_or_m` | 2024-08 | 0,97 |

Vad som syns:

- **Månads- och kvartalsserier ger få brott.** Med priorn κ0 = α0 = β0 = 1 krävs ett stort språng (i simuleringen
  4–6 standardavvikelser) för att nå 0,8. Elförsäljningen våren 2020 (pandemin) och några enskilda kvartal
  (RPO 2023Q2, capex/OCF 2023Q3) är de som når gränsen.
- **Årsserierna är strukturellt annorlunda.** PJM-prognoserna har bara 3–8 taktvärden. Med 3 värden är P(r_T ≤ 2) = 1
  per definition, och med hazard 1/3 ligger den högt även därefter (median 0,85). Fyra av de tolv brotten kommer
  därifrån, och tystnadsregeln är det enda som håller nere antalet. Det följer av F-D4 och F-D5 och är inte justerat.
  Ett brott i en årsserie med under cirka 6 värden säger alltså inget.
- G1, G2, G3, G8 och G9 har inga rapporterade brott i utvecklingen. De flesta av G3:s och G8:s serier räknas först
  från 2024–2025.

## F-D6 i utvecklingsperioden

**(b) Omklassning** mot de utjämnade sannolikheterna från banan på 2025-06-30, med samma regel:

| Block | Dagar | Andel där realtid ≠ utjämnat | Månader inbromsning, realtid / utjämnat |
|---|---|---|---|
| capex | 127 | 0,21 | 114 / 89 |
| efterfrågan | 62 | 0,18 | 51 / 62 |

Ungefär var femte månads rapporterade tillstånd byts ut i efterhand. För efterfrågan klassar den utjämnade skattningen
hela perioden 2020-05–2025-06 som inbromsning, eftersom banan på 2025-06-30 lägger den höga regimen på ett fåtal
månader.

**(c) Samband med huvudmodellernas absoluta fel** (Spearmans ρ, P på den senaste beräkningsdagen före prognosdagen,
prognosdag och utfall kända ≤ 2025-06-30). Bara information:

| Mål (huvudmodell) | Block | n | ρ |
|---|---|---|---|
| N1 (B1) | capex | 23 | 0,04 |
| N1 (B1) | efterfrågan | 20 | 0,13 |
| N2 (B3) | capex | 126 | 0,14 |
| N2 (B3) | efterfrågan | 61 | −0,18 |

Inget av sambanden är tydligt. Alla fyra ligger inom ungefär ±1,96/√(n − 1), alltså ±0,43 för N1 och ±0,17
respektive ±0,25 för N2, och är förenliga med slump. Inget test görs, och tecknet skiljer sig mellan blocken för N2.

## Brasklappar

- **Holdouten är delvis känd** (F-E5): baslinjefelen för 2025-07–2026-10 är publicerade, och de bakåtfyllda serierna
  har dagens vintage. Det gäller både faktorerna och BOCPD-serierna.
- **Instabila realtidssannolikheter:** omskattningen varje dag gör att P(inbromsning) kan hoppa mellan 0 och 1 från en
  månad till nästa. Det är en egenskap hos den registrerade metoden (F-D1, F-D3), inte ett fel i koden. Ett skifte
  bör därför läsas tillsammans med de lagrade värdena runt det.
- **Autokorrelation:** BOCPD körs på årstakt, som är starkt autokorrelerad (F-D5). Hur det påverkar antalet och
  tidpunkten för brott är inte prövat här.
- **Små stickprov:** få regimskiften (3–6 per block) och n = 6 (N1) och 16–17 (N2) på holdouten. Holdouten kan bara
  beskriva.

## Utdata och körning

- `python -m ai_tracker.regime` skriver `data/derived/c4/ms.parquet` (per dag och block: P, tillstånd, skifte,
  parametrar) och `data/derived/c4/bocpd.parquet` (per dag och räknad serie: P(r_T ≤ 2), senaste period, brott).
  Ingenting av det committas. Väggtid 6 minuter utan cache, 13 sekunder med cache.
- Tester: `tests/test_regime.py` (EM återfinner simulerade regimer, BOCPD stämmer med uttömmande uppräkning och hittar
  ett planterat brott, reglerna för skifte och brott, giftrader efter beräkningsdagen ändrar ingenting, vakten för
  holdouten).
- Den skarpa anslutningen till ögonblicksbilden byggs när holdouten är öppnad (specifikationen, avsnitt 1).
