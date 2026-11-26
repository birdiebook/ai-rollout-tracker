# Kreditlagret per 2025-06-30

**Frågan:** Ändras finansieringens pris och tillgång i de yttre lagren, och följer investeringstakten där med?

Yttre lagret: Oracle, CoreWeave, Nebius och IREN, och labben som tabellrader. Inre lagret: Microsoft, Alphabet, Amazon och Meta. Takt = förändring över fyra kvartal (procentenheter för andelar och räntor, log × 100 för belopp). Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1 (samma takt som de fyra senaste kvartalen). Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-25 KL1.

## 1. Pris på skuld

Effektiv ränta = räntekostnad över fyra kvartal / genomsnittlig långfristig skuld (efter aktiverad ränta, så den blir lägre hos bolag som bygger mycket). Microsofts räntekostnad innehåller ränta på finansiell leasing, men nämnaren är bara skulden. Microsofts tal, och därmed inre lagrets, är alltså ränta på skuld och leasing tillsammans och inte priset på skuld.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q1 | 2025-05-15 | `kl_rate_eff_outer` |
| Oracle | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q2 | 2025-06-15 | `kl_rate_eff_orcl` |
| CoreWeave | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q1 | 2025-05-15 | `kl_rate_eff_crwv` |
| Inre lagret | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_rate_eff_inner` |
| Microsoft | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_rate_eff_msft` |
| Alphabet | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_rate_eff_googl` |
| Amazon | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_rate_eff_amzn` |
| Meta | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_rate_eff_meta` |

## 2. Beroende av extern finansiering

**(capex − OCF) / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 20,0 % | +0,0 | -0,0 | -0,0 | 2025Q1 | 2025-05-15 | `kl_fcfgap_outer` |
| Oracle | 20,0 % | +0,0 | +0,0 | -0,0 | 2025Q2 | 2025-06-15 | `kl_fcfgap_orcl` |
| CoreWeave | 20,0 % | -0,0 | -0,0 | -0,0 | 2025Q1 | 2025-05-15 | `kl_fcfgap_crwv` |
| Nebius | 20,0 % | +0,0 | -0,0 | -0,0 | 2025Q1 | 2025-05-15 | `kl_fcfgap_nbis` |
| IREN | 20,0 % | +0,0 | -0,0 | -0,0 | 2025Q1 | 2025-05-08 | `kl_fcfgap_iren` |
| Inre lagret | 20,0 % | -0,0 | -0,0 | -0,0 | 2025Q1 | 2025-04-30 | `kl_fcfgap_inner` |
| Microsoft | 20,0 % | -0,0 | -0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_fcfgap_msft` |
| Alphabet | 20,0 % | -0,0 | -0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_fcfgap_googl` |
| Amazon | 20,0 % | +0,0 | +0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_fcfgap_amzn` |
| Meta | 20,0 % | +0,0 | +0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_fcfgap_meta` |

**(emitterad − amorterad skuld) / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 10,0 % | -3,4 | +0,6 | +0,2 | 2025Q1 | 2025-05-15 | `kl_netdebt_outer` |
| Oracle | 8,3 % | -3,2 | +0,5 | +0,2 | 2025Q2 | 2025-06-15 | `kl_netdebt_orcl` |
| CoreWeave | 11,3 % | -3,1 | +0,7 | +0,2 | 2025Q1 | 2025-05-15 | `kl_netdebt_crwv` |
| Inre lagret | 9,0 % | -3,4 | +0,5 | +0,2 | 2025Q1 | 2025-04-30 | `kl_netdebt_inner` |
| Microsoft | 8,8 % | -3,4 | -0,3 | -0,0 | 2025Q1 | 2025-04-30 | `kl_netdebt_msft` |
| Alphabet | 8,5 % | -3,8 | +0,2 | +0,2 | 2025Q1 | 2025-04-30 | `kl_netdebt_googl` |
| Amazon | 9,5 % | -3,7 | +1,0 | +0,2 | 2025Q1 | 2025-04-30 | `kl_netdebt_amzn` |
| Meta | 9,3 % | -2,9 | +1,2 | +0,4 | 2025Q1 | 2025-04-30 | `kl_netdebt_meta` |

**tecknade leasingavtal som inte börjat / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 32,5 % | -7,6 | +1,0 | +0,3 | 2025Q1 | 2025-05-15 | `kl_leases_outer` |
| Oracle | 27,5 % | -7,7 | +0,9 | +0,4 | 2025Q2 | 2025-06-15 | `kl_leases_orcl` |
| CoreWeave | 36,6 % | -6,6 | +1,2 | +0,5 | 2025Q1 | 2025-05-15 | `kl_leases_crwv` |
| Inre lagret | 29,5 % | -8,0 | +1,4 | +0,6 | 2025Q1 | 2025-04-30 | `kl_leases_inner` |
| Alphabet | 27,8 % | -9,2 | -0,3 | +0,4 | 2025Q1 | 2025-04-30 | `kl_leases_googl` |
| Amazon | 30,8 % | -8,6 | +1,9 | +0,4 | 2025Q1 | 2025-04-30 | `kl_leases_amzn` |
| Meta | 30,1 % | -6,3 | +2,7 | +1,0 | 2025Q1 | 2025-04-30 | `kl_leases_meta` |
| Microsoft | 28,7 % | -7,8 | -1,7 | -0,3 | 2025Q1 | 2025-04-30 | `kl_leases_msft` |
| Microsoft (inkl. villkorade, från 2026Q2) | – | – | – | – | – | – | `kl_leases_msft_cond` |

## 3. Vilja och förmåga att investera

**Capex över fyra kvartal** (takt = årsförändring i log × 100):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 35,6 mdr | +31,7 | -0,3 | +0,1 | 2025Q1 | 2025-05-15 | `kl_capex4_outer` |
| Oracle | 9,6 mdr | +32,6 | +0,1 | -0,3 | 2025Q2 | 2025-06-15 | `kl_capex4_orcl` |
| CoreWeave | 7,1 mdr | +24,6 | -1,9 | -1,0 | 2025Q1 | 2025-05-15 | `kl_capex4_crwv` |
| Nebius | 9,1 mdr | +30,3 | -0,6 | +0,8 | 2025Q1 | 2025-05-15 | `kl_capex4_nbis` |
| IREN | 10,5 mdr | +37,1 | +0,5 | -0,1 | 2025Q1 | 2025-05-08 | `kl_capex4_iren` |
| Inre lagret | 35,5 mdr | +32,1 | +0,8 | -0,3 | 2025Q1 | 2025-04-30 | `kl_capex4_inner` |
| Microsoft | 9,1 mdr | +32,1 | +6,9 | +1,8 | 2025Q1 | 2025-04-30 | `kl_capex4_msft` |
| Alphabet | 9,4 mdr | +36,6 | +3,8 | -0,3 | 2025Q1 | 2025-04-30 | `kl_capex4_googl` |
| Amazon | 8,4 mdr | +32,6 | -2,2 | -0,3 | 2025Q1 | 2025-04-30 | `kl_capex4_amzn` |
| Meta | 8,6 mdr | +26,9 | -5,9 | -2,5 | 2025Q1 | 2025-04-30 | `kl_capex4_meta` |

**Tillskott till RPO över fyra kvartal** (takt = log av tillskottet mot de fyra kvartalen före; klumpigt):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 4,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q1 | 2025-05-15 | `kl_rpo_add4_outer` |
| Oracle | 2,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q2 | 2025-06-15 | `kl_rpo_add4_orcl` |
| CoreWeave | 2,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q1 | 2025-05-15 | `kl_rpo_add4_crwv` |
| Inre lagret | 6,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_rpo_add4_inner` |
| Microsoft | 2,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_rpo_add4_msft` |
| Alphabet | 2,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_rpo_add4_googl` |
| Amazon | 2,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q1 | 2025-04-30 | `kl_rpo_add4_amzn` |

**CoreWeaves effekt** (MW, takt = log × 100 över fyra kvartal):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| CoreWeave, kontrakterad | – | – | – | – | – | – | `plan_crwv_contracted_power_asof_value` |
| CoreWeave, aktiv | – | – | – | – | – | – | `plan_crwv_active_power_asof_value` |

## 4. Läsregeln, mekaniskt

Gränser (låsta): A = vid t − 2 har den effektiva räntan en takt ≥ +0,25 procentenheter eller ett beroendemått ≥ +5. Capex-takten föll om förändringen i takt ≤ -5. Lika fall: inre ≤ 0,5 × yttre. En negativ förändring i takt betyder att tillväxten avtar, inte att capex minskar. Utslaget är en beskrivning, inget test.

Regeln läser bara uppgång i pris och beroende: A kräver en takt på minst gränsen. Ett fall i pris och beroende följt av högre capex-takt blir "inget av mönstren". Hur ofta A har gällt står under varje utslag. När A nästan alltid gäller, avgörs utslaget i praktiken av capex-takten. En regel som läser båda riktningarna kräver en ny daterad registerpost.

Alla kvartal i den här läsningen var kända före registerposten 2026-11-25, och flera av dem var sedda före posten (posten, avsnitt (e)). Läsningen är därför inget utfall på osedda data. Den första läsningen på osedda kvartal kommer med inlämningar efter 2026-11-25.

- **Yttre lagret (huvudläsning):** inget av mönstren. t = 2025Q1; A = False (takt vid 2024Q3: rate_eff -0,0, fcfgap +0,0, netdebt -4,0, leases -8,6); förändring i capex-takt yttre -0,3, inre +0,8 (2025Q1).
  A har gällt i 0 av 6 kvartal med minst en takt (2023Q4–2025Q1).
- **Oracle mot inre lagret:** inget av mönstren. t = 2025Q2; A = False (takt vid 2024Q4: rate_eff -0,0, fcfgap +0,0, netdebt -3,7, leases -8,6); förändring i capex-takt yttre +0,1, inre +0,8 (2025Q1).
  A har gällt i 0 av 7 kvartal med minst en takt (2023Q4–2025Q2).
- **CoreWeave mot inre lagret:** inget av mönstren. t = 2025Q1; A = False (takt vid 2024Q3: rate_eff -0,0, fcfgap +0,0, netdebt -3,8, leases -7,8); förändring i capex-takt yttre -1,9, inre +0,8 (2025Q1).
  A har gällt i 0 av 6 kvartal med minst en takt (2023Q4–2025Q1).
- **Nebius mot inre lagret:** inget av mönstren. t = 2025Q1; A = False (takt vid 2024Q3: fcfgap +0,0); förändring i capex-takt yttre -0,6, inre +0,8 (2025Q1).
  A har gällt i 0 av 6 kvartal med minst en takt (2023Q4–2025Q1).
- **IREN mot inre lagret:** inget av mönstren. t = 2025Q1; A = False (takt vid 2024Q3: fcfgap +0,0); förändring i capex-takt yttre +0,5, inre +0,8 (2025Q1).
  A har gällt i 0 av 6 kvartal med minst en takt (2023Q4–2025Q1).

## 5. Labben och utvecklar- och SPV-kanalen (tabellrader ur inlämningarna)

- Anthropic: ingen registreringsansökan känd på dagen.
- OpenAI: ingen registreringsansökan på EDGAR (sökning på namnet 2026-11-25: bara fonder och SPV med Form D).
- Oracle: inga belopp för datacenter-SPV eller samriskbolag i 10-Q och 10-K 2025–2026.

## 6. Att bevaka

Nästa inlämning per bolag, uppskattad som nästa kvartals slut plus medianen av avståndet för de åtta senaste inlämningarna:

- Microsoft: 2025Q2 omkring 2025-07-30 (median 30 dagar, spann 30–30, senast 2025-04-30)
- Alphabet: 2025Q2 omkring 2025-07-30 (median 30 dagar, spann 30–30, senast 2025-04-30)
- Amazon: 2025Q2 omkring 2025-07-30 (median 30 dagar, spann 30–30, senast 2025-04-30)
- Meta: 2025Q2 omkring 2025-07-30 (median 30 dagar, spann 30–30, senast 2025-04-30)
- IREN: 2025Q2 omkring 2025-08-07 (median 38 dagar, spann 38–38, senast 2025-05-08)
- CoreWeave: 2025Q2 omkring 2025-08-14 (median 45 dagar, spann 45–45, senast 2025-05-15)
- Nebius: 2025Q2 omkring 2025-08-14 (median 45 dagar, spann 45–45, senast 2025-05-15)
- Oracle: 2025Q3 omkring 2025-09-15 (median -15 dagar, spann -15–-15, senast 2025-06-15)
- Anthropic: första periodrapporten efter börsnoteringen; ingen historik att uppskatta från.

## 7. Förbehåll

- Med cirka 8–12 kvartal per mått är detta en beskrivning och inget test. Ett mönster kan vara slump.
- RPO är klumpig: enstaka mycket stora avtal flyttar ett kvartal.
- Neomolnens serier börjar 2024, så yttre lagrets takt och förändring i takt finns bara för de senaste kvartalen. Nebius och IREN saknar skuldserier och ingår bara i capex och (capex − OCF) / capex.
- Den effektiva räntan är efter aktiverad ränta. Microsofts räntekostnad innehåller ränta på finansiell leasing. CoreWeaves räntor i skuldtabellen står i hela procent.
- Regeln läser bara uppgång i pris och beroende. Hur ofta A har gällt står i avsnitt 4.
- Utanför ramen: privat kredit utanför EDGAR, labbens oregistrerade skuld, spreadar på andrahandsmarknaden (licens) och 144A-affärer utan 8-K. OpenAI har ingen registreringsansökan på EDGAR.
- Nyhetsuppgifter om kreditbetyg (KBRA, Moody's) är sekundära och används inte som data.
