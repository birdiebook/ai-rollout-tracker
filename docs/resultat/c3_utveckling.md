# C3: faktormodell och variant DF, utvecklingsperioden

Körd 2026-11-24 med `python -m ai_tracker.nowcast.df`, efter att specifikationen `docs/steg2/c3_spec.md` var
committad (commit `5431f41`, den daterade posten enligt F-E5). Specifikationen är inte ändrad efter körningen. En
buggfix (prognosdagar före fönstrets start 2010-01 gav ett indexfel och har nu ingen faktor) ändrar inga val.

**Holdouten är stängd.** Alla faktorskattningar och DF-fel har prognosdag ≤ 2025-06-30. Den senaste skattade
faktorbanan gäller 2025-06-05, och körningen läste bara rader med `known_from` ≤ 2025-06-30 (`factor/guard.py`).
Inga faktorbanor, prognoser eller fel efter det har beräknats eller lästs.

**Utvecklingskörningen avgör ingenting** (F-E6). Befordran prövas en gång på holdouten, när ägaren har godkänt
öppningen och C4 är låst (F-E4).

## Faktorerna

| Block | Skattade prognosdagar | Konvergerade | Första prognosdag med faktor | Serier i blocket | a (AR(1)) |
|---|---|---|---|---|---|
| capex och leverantörsled | 208 | 208 (högst 117 iterationer) | 2012-02-05 | 16–25 | 0,85–0,98 |
| efterfrågan | 101 | 101 (högst 97 iterationer) | 2020-06-05 | 2–17 | 0,93–0,99 |

264 prognosdagar har skattats (N1–N4 och N2:s månatliga dagar). Efterfrågeblocket finns först från 2020-06, när
`rev_aws` och `rev_nvda_datacenter` båda har 8 kvartalsvisa taktvärden. Fram till 2023 består det av 2–5
kvartalsserier (plus PyPI från 2023), så faktorn är där i stort sett en interpolerad kvartalsfaktor (F-B21). Indeed
kommer in från 2024-04-30. BTOS och Cloudflare får aldrig 24 taktvärden före 2025-06-30 och ingår inte.

## DF mot jämförelsemodellen

Fel = 100 × (log prognos − log utfall), första versionen. Jämförelsemodellen är den bästa av B0, B1, huvudmodellen
och modellen DF bygger på (F-B10), på samma rader. DM-test på absolutfel (Newey–West, HLN). Holm-p inom målets
familj för steg 2, där de andra medlemmarna ingår med p = 1 (N1 och N2: ×2, N3: ×3). Negativ MAE-skillnad = DF bättre.

| Mål | Period | n | Jämförelse | MAE DF | MAE jämförelse | MAE-skillnad | Bias DF | DM p | Holm-p | MDE |
|---|---|---|---|---|---|---|---|---|---|---|
| N1 capex | 2023Q2 – 2025Q1 | 8 | B1 | 10,83 | 8,04 | +2,79 | −4,05 | 0,066 | 0,132 | 3,59 |
| N2 TSMC | 2021-05 – 2025-05 | 49 | B2 | 6,33 | 6,87 | −0,54 | −1,60 | 0,417 | 0,834 | 1,85 |
| N2 TSMC, från 2023 | 2023-01 – 2025-05 | 29 | B2 | 6,03 | 6,84 | −0,81 | +0,74 | 0,400 | 0,801 | 2,67 |
| N3 Nvidia DC | 2023Q2 – 2025Q1 | 8 | B1 | 15,38 | 21,09 | −5,71 | −8,08 | 0,059 | 0,176 | 7,09 |
| N4 molnintäkter | – | 0 | – | – | – | – | – | – | – | – |

För N1 och N3 börjar DF först 2023Q2, så delperioden från 2023 är samma rader som hela perioden.

Rader med båda faktorerna (träningsunderlag): N1 20, N2 61, N3 20, N4 11. DF kräver 12 tidigare rader med känt utfall.

## Tolkning

- **N1 (capex):** DF är sämre än B1 på 8 kvartal (MAE 10,8 mot 8,0). Skillnaden är inte signifikant efter Holm.
  Ingen indikation på att faktorerna hjälper capex-nowcasten i utvecklingen.
- **N2 (TSMC):** DF är något bättre än B2 (MAE 6,3 mot 6,9, även från 2023), men skillnaden är mindre än en tredjedel
  av MDE (1,9) och p = 0,42. Det är förenligt med slump. N2 är det enda mål där holdouten (16–17 månader) kan pröva
  DF (F-E6).
- **N3 (Nvidias datacenter):** DF har klart lägre MAE än B1 (15,4 mot 21,1), men n = 8, MDE 7,1 och Holm-p 0,18. Med
  8 kvartal och 19–20 träningsrader kan en korrektion med konstant och två faktorer se bra ut av ren tur. Båda
  modellernas MAE domineras av 2023Q2 (fel −85 för både B1 och DF). Skillnaden kommer främst från 2024Q1–Q2, där DF
  minskar B1:s överskattning efter språnget (B1 +20 och +26, DF +9 och +5). Inget test på holdouten är möjligt
  (n = 5–6 < 8, F-E6), så DF för N3 kan bara bli skugga i det skarpa registret.
- **N4 (moln):** inga utvecklingsrader. Summan av molnintäkterna har för kort historik för 12 träningsrader före
  2025-06-30 (som R6 räknade ut). DF för N4 utvärderas bara på holdouten, och där är n = 5 < 8, så inget test.

## Brasklappar

- **n är för litet** för N1, N3 och N4. Resultaten där är beskrivande. Bara N2 har ett stickprov som kan visa något,
  och även där är skillnaden inte skild från noll.
- **Holdouten är delvis känd** (F-E5): baslinjefelen för 2025-07–2026-10 är publicerade, och de bakåtfyllda serierna
  har dagens vintage. Faktorbanorna på historiska prognosdagar innehåller därför revideringar som inte var kända då,
  särskilt `us_constr_datacenter` (känd från 2024-07-01, men med dagens revideringar), importserierna, elförsäljningen
  och npm/PyPI.
- **Mittpunktsetiketter** förskjuter räkenskapskvartal (Nvidia, Oracle, Broadcom, Marvell) med upp till en månad i
  faktorn.
- **Skarpa DF-prognoser** kan inte göras förrän holdouten är öppnad, eftersom träningsraderna kräver faktorer på
  holdoutens prognosdagar (F-B18).

## För C4

`factor.realtime.realtime_monthly(tabell, start, slut)` ger realtidsserien (månad m = värdet för m i banan skattad
på m:s sista dag) och `factor.realtime.vintage(tabell, dag)` hela banan på en dag. Båda vägrar dagar efter
2025-06-30 så länge holdouten är stängd.
