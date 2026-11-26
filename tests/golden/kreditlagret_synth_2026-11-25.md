# Kreditlagret per 2026-11-25

**Frågan:** Ändras finansieringens pris och tillgång i de yttre lagren, och följer investeringstakten där med?

Yttre lagret: Oracle, CoreWeave, Nebius och IREN, och labben som tabellrader. Inre lagret: Microsoft, Alphabet, Amazon och Meta. Takt = förändring över fyra kvartal (procentenheter för andelar och räntor, log × 100 för belopp). Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1 (samma takt som de fyra senaste kvartalen). Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-25 KL1.

## 1. Pris på skuld

Effektiv ränta = räntekostnad över fyra kvartal / genomsnittlig långfristig skuld (efter aktiverad ränta, så den blir lägre hos bolag som bygger mycket). Microsofts räntekostnad innehåller ränta på finansiell leasing, men nämnaren är bara skulden. Microsofts tal, och därmed inre lagrets, är alltså ränta på skuld och leasing tillsammans och inte priset på skuld.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q4 | 2026-02-14 | `kl_rate_eff_outer` |
| Oracle | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q4 | 2025-12-16 | `kl_rate_eff_orcl` |
| CoreWeave | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q4 | 2026-02-14 | `kl_rate_eff_crwv` |
| Inre lagret | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_rate_eff_inner` |
| Microsoft | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_rate_eff_msft` |
| Alphabet | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_rate_eff_googl` |
| Amazon | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_rate_eff_amzn` |
| Meta | 4,0 % | -0,0 | +0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_rate_eff_meta` |

## 2. Beroende av extern finansiering

**(capex − OCF) / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 19,7 % | -0,3 | +0,0 | +0,1 | 2025Q4 | 2026-02-14 | `kl_fcfgap_outer` |
| Oracle | 18,8 % | -1,2 | +0,2 | +0,4 | 2025Q4 | 2025-12-20 | `kl_fcfgap_orcl` |
| CoreWeave | 20,0 % | -0,0 | -0,0 | +0,0 | 2025Q4 | 2026-02-14 | `kl_fcfgap_crwv` |
| Nebius | 20,0 % | +0,0 | +0,0 | +0,0 | 2025Q4 | 2026-02-14 | `kl_fcfgap_nbis` |
| IREN | 20,0 % | -0,0 | -0,0 | +0,0 | 2025Q4 | 2026-02-07 | `kl_fcfgap_iren` |
| Inre lagret | 20,0 % | -0,0 | -0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_fcfgap_inner` |
| Microsoft | 20,0 % | -0,0 | +0,0 | -0,0 | 2025Q4 | 2026-01-30 | `kl_fcfgap_msft` |
| Alphabet | 20,0 % | +0,0 | +0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_fcfgap_googl` |
| Amazon | 20,0 % | +0,0 | +0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_fcfgap_amzn` |
| Meta | 20,0 % | -0,0 | +0,0 | -0,0 | 2025Q4 | 2026-01-30 | `kl_fcfgap_meta` |

**(emitterad − amorterad skuld) / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 8,1 % | -2,6 | +0,4 | +0,1 | 2025Q4 | 2026-02-14 | `kl_netdebt_outer` |
| Oracle | 7,2 % | -2,5 | +0,5 | +0,1 | 2025Q4 | 2025-12-20 | `kl_netdebt_orcl` |
| CoreWeave | 9,3 % | -2,6 | +0,2 | +0,0 | 2025Q4 | 2026-02-14 | `kl_netdebt_crwv` |
| Inre lagret | 7,1 % | -2,6 | +0,5 | +0,1 | 2025Q4 | 2026-01-30 | `kl_netdebt_inner` |
| Microsoft | 6,9 % | -2,8 | +0,5 | +0,2 | 2025Q4 | 2026-01-30 | `kl_netdebt_msft` |
| Alphabet | 6,5 % | -2,8 | +0,6 | +0,2 | 2025Q4 | 2026-01-30 | `kl_netdebt_googl` |
| Amazon | 7,3 % | -2,9 | +0,4 | +0,1 | 2025Q4 | 2026-01-30 | `kl_netdebt_amzn` |
| Meta | 7,8 % | -1,9 | +0,5 | -0,0 | 2025Q4 | 2026-01-30 | `kl_netdebt_meta` |

**tecknade leasingavtal som inte börjat / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 28,0 % | -6,2 | +0,5 | -0,0 | 2025Q4 | 2026-02-14 | `kl_leases_outer` |
| Oracle | 24,8 % | -6,3 | +0,9 | +0,1 | 2025Q4 | 2025-12-20 | `kl_leases_orcl` |
| CoreWeave | 32,1 % | -5,9 | -0,1 | -0,1 | 2025Q4 | 2026-02-14 | `kl_leases_crwv` |
| Inre lagret | 24,7 % | -6,4 | +0,9 | +0,0 | 2025Q4 | 2026-01-30 | `kl_leases_inner` |
| Alphabet | 22,4 % | -7,3 | +1,3 | +0,3 | 2025Q4 | 2026-01-30 | `kl_leases_googl` |
| Amazon | 25,2 % | -7,5 | +0,5 | +0,1 | 2025Q4 | 2026-01-30 | `kl_leases_amzn` |
| Meta | 26,9 % | -4,1 | +1,1 | -0,3 | 2025Q4 | 2026-01-30 | `kl_leases_meta` |
| Microsoft | 23,6 % | -7,2 | +0,9 | +0,3 | 2025Q4 | 2026-01-30 | `kl_leases_msft` |
| Microsoft (inkl. villkorade, från 2026Q2) | – | – | – | – | – | – | `kl_leases_msft_cond` |

## 3. Vilja och förmåga att investera

**Capex över fyra kvartal** (takt = årsförändring i log × 100):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 44,4 mdr | +30,1 | -0,5 | +0,0 | 2025Q4 | 2026-02-14 | `kl_capex4_outer` |
| Oracle | 11,1 mdr | +30,2 | -0,6 | +0,6 | 2025Q4 | 2025-12-20 | `kl_capex4_orcl` |
| CoreWeave | 8,6 mdr | +24,4 | +1,2 | +0,6 | 2025Q4 | 2026-02-14 | `kl_capex4_crwv` |
| Nebius | 11,6 mdr | +32,5 | +2,8 | +0,8 | 2025Q4 | 2026-02-14 | `kl_capex4_nbis` |
| IREN | 13,2 mdr | +31,7 | -4,8 | -1,5 | 2025Q4 | 2026-02-07 | `kl_capex4_iren` |
| Inre lagret | 45,0 mdr | +31,5 | -0,5 | +0,4 | 2025Q4 | 2026-01-30 | `kl_capex4_inner` |
| Microsoft | 11,6 mdr | +34,2 | -0,2 | -0,1 | 2025Q4 | 2026-01-30 | `kl_capex4_msft` |
| Alphabet | 12,3 mdr | +35,8 | -0,8 | -0,1 | 2025Q4 | 2026-01-30 | `kl_capex4_googl` |
| Amazon | 10,9 mdr | +33,5 | +1,2 | +0,6 | 2025Q4 | 2026-01-30 | `kl_capex4_amzn` |
| Meta | 10,2 mdr | +21,8 | -2,6 | +1,2 | 2025Q4 | 2026-01-30 | `kl_capex4_meta` |

**Tillskott till RPO över fyra kvartal** (takt = log av tillskottet mot de fyra kvartalen före; klumpigt):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 4,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q4 | 2026-02-14 | `kl_rpo_add4_outer` |
| Oracle | 2,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q4 | 2025-12-16 | `kl_rpo_add4_orcl` |
| CoreWeave | 2,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q4 | 2026-02-14 | `kl_rpo_add4_crwv` |
| Inre lagret | 6,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_rpo_add4_inner` |
| Microsoft | 2,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_rpo_add4_msft` |
| Alphabet | 2,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_rpo_add4_googl` |
| Amazon | 2,0 mdr | +0,0 | +0,0 | +0,0 | 2025Q4 | 2026-01-30 | `kl_rpo_add4_amzn` |

**CoreWeaves effekt** (MW, takt = log × 100 över fyra kvartal):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| CoreWeave, kontrakterad | – | – | – | – | – | – | `plan_crwv_contracted_power_asof_value` |
| CoreWeave, aktiv | – | – | – | – | – | – | `plan_crwv_active_power_asof_value` |

## 4. Läsregeln, mekaniskt

Gränser (låsta): A = vid t − 2 har den effektiva räntan en takt ≥ +0,25 procentenheter eller ett beroendemått ≥ +5. Capex-takten föll om förändringen i takt ≤ -5. Lika fall: inre ≤ 0,5 × yttre. En negativ förändring i takt betyder att tillväxten avtar, inte att capex minskar. Utslaget är en beskrivning, inget test.

Regeln läser bara uppgång i pris och beroende: A kräver en takt på minst gränsen. Ett fall i pris och beroende följt av högre capex-takt blir "inget av mönstren". Hur ofta A har gällt står under varje utslag. När A nästan alltid gäller, avgörs utslaget i praktiken av capex-takten. En regel som läser båda riktningarna kräver en ny daterad registerpost.

Alla kvartal i den här läsningen var kända före registerposten 2026-11-25, och flera av dem var sedda före posten (posten, avsnitt (e)). Läsningen är därför inget utfall på osedda data. Den första läsningen på osedda kvartal kommer med inlämningar efter 2026-11-25, för Oracle omkring 2026-12-16.

- **Yttre lagret (huvudläsning):** inget av mönstren. t = 2025Q4; A = False (takt vid 2025Q2: rate_eff -0,0, fcfgap -0,3, netdebt -3,0, leases -6,7); förändring i capex-takt yttre -0,5, inre -0,5 (2025Q4).
  A har gällt i 0 av 9 kvartal med minst en takt (2023Q4–2025Q4).
- **Oracle mot inre lagret:** inget av mönstren. t = 2025Q4; A = False (takt vid 2025Q2: rate_eff -0,0, fcfgap -1,4, netdebt -3,0, leases -7,2); förändring i capex-takt yttre -0,6, inre -0,5 (2025Q4).
  A har gällt i 0 av 9 kvartal med minst en takt (2023Q4–2025Q4).
- **CoreWeave mot inre lagret:** inget av mönstren. t = 2025Q4; A = False (takt vid 2025Q2: rate_eff -0,0, fcfgap -0,0, netdebt -2,8, leases -5,8); förändring i capex-takt yttre +1,2, inre -0,5 (2025Q4).
  A har gällt i 0 av 9 kvartal med minst en takt (2023Q4–2025Q4).
- **Nebius mot inre lagret:** inget av mönstren. t = 2025Q4; A = False (takt vid 2025Q2: fcfgap +0,0); förändring i capex-takt yttre +2,8, inre -0,5 (2025Q4).
  A har gällt i 0 av 9 kvartal med minst en takt (2023Q4–2025Q4).
- **IREN mot inre lagret:** inget av mönstren. t = 2025Q4; A = False (takt vid 2025Q2: fcfgap +0,0); förändring i capex-takt yttre -4,8, inre -0,5 (2025Q4).
  A har gällt i 0 av 9 kvartal med minst en takt (2023Q4–2025Q4).

## 5. Labben och utvecklar- och SPV-kanalen (tabellrader ur inlämningarna)

- **Anthropic** (S-1 och ändringar, första 2026-10-26). Läge 2026-09-30:
  - köpåtaganden i tabellen: 313,8 mdr (known_from 2026-10-26)
- OpenAI: ingen registreringsansökan på EDGAR (sökning på namnet 2026-11-25: bara fonder och SPV med Form D).
- Oracle: inga belopp för datacenter-SPV eller samriskbolag i 10-Q och 10-K 2025–2026.

## 6. Att bevaka

Nästa inlämning per bolag, uppskattad som nästa kvartals slut plus medianen av avståndet för de åtta senaste inlämningarna:

- Microsoft: 2026Q3 omkring 2026-10-30 (väntas nu, inte i tabellen ännu; därefter 2026Q4 omkring 2027-01-30) (median 30 dagar, spann 30–30, senast 2026-01-30)
- Alphabet: 2026Q3 omkring 2026-10-30 (väntas nu, inte i tabellen ännu; därefter 2026Q4 omkring 2027-01-30) (median 30 dagar, spann 30–30, senast 2026-01-30)
- Amazon: 2026Q3 omkring 2026-10-30 (väntas nu, inte i tabellen ännu; därefter 2026Q4 omkring 2027-01-30) (median 30 dagar, spann 30–30, senast 2026-01-30)
- Meta: 2026Q3 omkring 2026-10-30 (väntas nu, inte i tabellen ännu; därefter 2026Q4 omkring 2027-01-30) (median 30 dagar, spann 30–30, senast 2026-01-30)
- IREN: 2026Q3 omkring 2026-11-07 (väntas nu, inte i tabellen ännu; därefter 2026Q4 omkring 2027-02-07) (median 38 dagar, spann 38–38, senast 2026-02-07)
- CoreWeave: 2026Q3 omkring 2026-11-14 (väntas nu, inte i tabellen ännu; därefter 2026Q4 omkring 2027-02-14) (median 45 dagar, spann 45–45, senast 2026-02-14)
- Nebius: 2026Q3 omkring 2026-11-14 (väntas nu, inte i tabellen ännu; därefter 2026Q4 omkring 2027-02-14) (median 45 dagar, spann 45–45, senast 2026-02-14)
- Oracle: 2026Q4 omkring 2026-12-16 (median -15 dagar, spann -15–-15, senast 2025-12-16)
- Anthropic: första periodrapporten efter börsnoteringen; ingen historik att uppskatta från.

## 7. Förbehåll

- Med cirka 8–12 kvartal per mått är detta en beskrivning och inget test. Ett mönster kan vara slump.
- RPO är klumpig: enstaka mycket stora avtal flyttar ett kvartal.
- Neomolnens serier börjar 2024, så yttre lagrets takt och förändring i takt finns bara för de senaste kvartalen. Nebius och IREN saknar skuldserier och ingår bara i capex och (capex − OCF) / capex.
- Den effektiva räntan är efter aktiverad ränta. Microsofts räntekostnad innehåller ränta på finansiell leasing. CoreWeaves räntor i skuldtabellen står i hela procent.
- Regeln läser bara uppgång i pris och beroende. Hur ofta A har gällt står i avsnitt 4.
- Utanför ramen: privat kredit utanför EDGAR, labbens oregistrerade skuld, spreadar på andrahandsmarknaden (licens) och 144A-affärer utan 8-K. OpenAI har ingen registreringsansökan på EDGAR.
- Nyhetsuppgifter om kreditbetyg (KBRA, Moody's) är sekundära och används inte som data.
