# Elflaskhalsen: följd fråga (EL1)

*Ägarbeslut 2026-11-27 (spår B18, `docs/mattregister.md`, 2026-11-27 B18, punkt 1): S1:s räkning av prövade ursprung är bekräftad, och övergångsnotisen väntar inte längre på ägarens bekräftelse (R29-1 stängt). Båda talen står kvar i notisen. Inget annat ändrades, och inga utslag ändrades. Rapporterna nedan är genererade på nytt med kommandot.*


*Rättad efter granskningen R29 (rättningsspår X26, `docs/mattregister.md`, 2026-11-27 X26): EL1-S säger inte längre att Quantas förvärv är okontrollerade. De är kodade ur 10-K och 10-Q från 2023 (QA1), inte före, och märket står i LT1:s huvudläsning, som har samma X (R29-5). Övergångsnotisen för F0:s räkning säger att bytet väntar på ägarens bekräftelse (R29-1). Inga utslag ändrades.*


*Tillägg S1 (`docs/mattregister.md`, 2026-11-27 S1, punkt 2 och 3): en nionde rad i avsnitt 5, orderstocken för elnät som förändring i takt mot capex i det inre lagret, bredvid de åtta låsta. Huvudläsningen är oförändrad. Raden är LT1:s huvudläsning med motsatt tecken och ingen ny observation. F0:s räkning av hur ofta regeln kunde prövas är ändrad (S1, punkt 3): ett ursprung räknas som prövat bara när Y finns i fönstret, och varje rad visar det gamla talet bredvid det nya i en övergångsnotis. Rapporterna nedan är genererade på nytt per 2026-11-27 och 2025-11-27. Utom datumen, räkningen och den nya raden är de desamma som per 2026-11-26 och 2025-11-26, så texten om de dagarna gäller också för de nya.*

*Rättad efter granskningen R28 (rättningsspår X25, `docs/mattregister.md`, 2026-11-26 X25): förbehållet om sedda data avgörs nu per läsning och inte av läsdagen, och varje rad visar hur ofta Y var känt i hela fönstret och vilken riktning som inte har prövats (för elpriset mot capex var Y känt i 27 av 267 ursprung, inte 213). Inga utslag ändrades. Rapporterna nedan är genererade på nytt med kommandot.*

**Frågan:** Blir el den bindande begränsningen för utbyggnaden?

Följd fråga, inte en gren. Måtten, aggregaten, läsregeln och gränserna låstes i registret innan något räknades
(`docs/mattregister.md`, "2026-11-26 – EL1", commit `f8f0046`). Regeln är F0:s symmetriska mall. Källor, kodning och
förbehåll: `docs/kallor/elflaskhalsen.md`. Rapporten byggs med

    python -m ai_tracker.followed elflaskhalsen --as-of 2026-11-27 [--json PATH] [--out PATH]

Den använder bara rader som var kända på dagen. Nedan står rapporten per 2026-11-27 och per 2025-11-27, så att
ändringen över ett år syns. Rapporterna är genererade av kommandot och inte redigerade (rubrikerna är en nivå lägre).

**Läsningarna är gjorda på sedda data.** Alla kvartal i båda läsningarna var publicerade före registerposten
2026-11-26. Y:s senaste värden för capex (+6,2 vid 2026Q2 och +9,6 vid 2026Q3) var sedda före posten, och posten sade
att huvudläsningen per 2026-11-26 därför sannolikt skulle bli "talar emot" (posten, avsnitt (f)). Det blev den.
Utslagen är inga utfall på osedda data. Den första läsningen på osedda kvartal kommer när inre lagrets capex för 2026Q4
är känd, omkring 2027-01-31, och för Digital Realty omkring 2027-01-24.

**Samma par som LT1.** Huvudläsningens X (orderstock elnät = `rpo_pwr` + `rpo_etn`) är exakt LT1:s L1, och Y (`kl_capex4_inner`) är LT1:s K-inre. EL1 läser takten med tecken −, LT1 förändringen i takt med tecken +. Samma kvartal (ursprung 2026Q2, capex +9,6 vid 2026Q3) ger därför "talar emot" här och "talar för" i LT1. Det är två läsningar av samma rörelse och tillsammans inte mer än en observation (R28-4).

## Vad som skiljer de två dagarna (beskrivning, inget test)

- **Huvudläsningen** (orderstock för elnät mot capex i det inre lagret) gav "kan inte avgöras" per 2025-11-26 och
  "talar emot, uppåt" per 2026-11-26. Per 2025-11-26 var ursprunget 2025Q2: orderstocken växte med +21,5 log-punkter
  på ett år, men förändringen i capex-takt vid 2025Q3 var +2,0, inom gränsen ±5, och fönstret var öppet. Per
  2026-11-26 är ursprunget 2026Q2: orderstocken växte med +45,3 och capex-takten ökade med +9,6 vid 2026Q3. Elsidan
  stramades åt, och utbyggnaden accelererade ändå. Det pekar på en gemensam efterfrågan och inte på att elen band.
- **Regeln läser i praktiken bara Y.** Orderstocken för elnät har haft en impuls uppåt i alla 20 ursprung sedan
  2021Q3, och ingen nedåt. Utslaget avgörs då av tecknet på förändringen i capex-takt. Över hela historiken (läsdagens
  vintage) blev det 9 "talar för", 9 "talar emot" och 2 "inget av mönstren", alltså ungefär slantsingling.
  Riktningen nedåt, att elsidan lättar och takten ökar, har aldrig kunnat prövas för orderstockarna. Elpriset har haft
  62 impulser uppåt och ingen nedåt sedan 1959 (nominell drift). Lasten har haft 15 uppåt och 1 nedåt.
- **Elsidan steg på alla mått.** Orderstocken för elnät gick från +22,3 till +54,6 i takt, lasten i de fem områdena
  från +3,5 till +4,3 (Dominion från +7,4 till +8,5) och elpriset från +2,8 (2025Q1, det senaste kända kvartalet då)
  till +4,0. Elpriset nådde inte gränsen +5 och gav inget utslag. Gasturbinerna (+67,7) har takt först från 2026Q1 och
  fanns inte i läsningen per 2025-11-26.
- **Capex-takten i det inre lagret** gick från +50,5 till +62,4, och förändringen i takt från +2,0 till +9,6.
- **Digital Realtys tecknade MW** är mycket klumpiga. Förändringen i takt var −100,8 vid 2025Q3 och +100,4 vid 2026Q3.
  Därför gav last och orderstock mot MW "talar för, uppåt" per 2025-11-26 och "talar emot, uppåt" per 2026-11-26.
  Bytet säger mer om enstaka stora avtal än om el.
- **Elpriset per 2025-11-26 slutar vid 2025Q1.** PPI-serien är regeldaterad: ett slutligt värde dateras till
  PPI-releasen fyra månader senare, och bara den senaste filens preliminära månader får filens datum. Juni 2025 var
  därför inte känd på dagen, och raden blev "kan inte avgöras".
- **Lasten är backfill.** Båda läsningarna har dagens värden för EIA-930 (inga daterade versioner före 2026-11-23).
  Läsningen per 2025-11-26 kan därför innehålla revideringar som inte var kända då.

Y har förändring i takt från 2019Q4 (capex) och 2024Q1 (Digital Realty), gasturbinerna har takt från 2026Q1, och det
är åtta rader med en gemensam drivkraft bakom både elsidan och capex. Inget av detta är ett test. Ett utslag åt något
håll kan vara slump.

## Tillägg S1: orderstocken som förändring i takt (beskrivning, inget test)

- **Den nya raden** (S1, punkt 2) ger "talar emot, uppåt" per 2026-11-27: orderstockens förändring i takt var +16,5 vid
  2026Q2 och capex-takten ökade +9,6 vid 2026Q3. Per 2025-11-27 gav den "inget av mönstren" (ingen impuls i
  fönstret).
- **Riktningen nedåt har inträffat:** 3 impulser nedåt och 4 uppåt i 18 ursprung (2022Q1–2026Q2). Alla tre nedåt gav
  "talar för, nedåt": orderstocken växte långsammare än förut, och capex-takten steg sedan. Huvudläsningen (takt) har
  20 impulser uppåt och ingen nedåt. Tre händelser är för få för att säga något om mekanismen.
- **Ingen ny observation.** Raden är LT1:s huvudläsning med motsatt tecken. Utfallen per ursprung är spegelvända och
  impulserna desamma per 2026-11-27 och 2025-11-27 (prövat i `tests/test_s1_symmetri.py`).
- **Räkningen (S1, punkt 3):** elpriset mot capex kunde prövas i 27 av 267 ursprung (förut 213), mot Digital Realtys MW
  i 10 (förut 206), och lasten mot MW i 11 av 23 (förut 16). Utslagen ändras inte.
- Alla läsningar är på sedda data. Första osedda läsningen omkring 2027-01-31.

## Elflaskhalsen per 2026-11-27

**Frågan:** Blir el den bindande begränsningen för utbyggnaden?

Elsidan (pris, last och orderstock för elnät och gasturbiner) mot utbyggnadens takt (capex i det inre lagret och tecknade MW hos Digital Realty). Takt = 100 × ln(värdet / värdet fyra kvartal tidigare). Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1 (samma takt som de fyra senaste kvartalen). Månadsserier blir kvartal som medel av de tolv månader som slutar med kvartalets sista månad. Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-26 EL1.

### 1. Elsidan: pris och last

PPI för el till kommersiella kunder (BLS) och medellast per månad ur EIA-930, summerad över PJM, ERCOT, Southern Company, APS och SRP. Dominion är en delregion av PJM och visas för sig.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Elpris, PPI kommersiella kunder (tolv månader) | 240,8 | +4,0 | +0,0 | -0,3 | 2026Q3 | 2026-11-13 | `el1_pris4` |
| Last, fem områden (tolv månader) | 193 893 MW | +4,3 | +1,6 | +1,2 | 2026Q3 | 2026-10-07 | `el1_last4` |
| Last, Dominion (tolv månader) | 16 394 MW | +8,5 | +1,4 | +1,2 | 2026Q3 | 2026-10-31 | `el1_last4_dom` |
- Elpris, PPI kommersiella kunder (tolv månader): 2026Q4 saknar på dagen `us_ppi_elec_commercial_m` 2026-11–2026-12.
- Last, fem områden (tolv månader): 2026Q4 saknar på dagen `eia930_avg_pjm_m` 2026-11–2026-12, `eia930_avg_erco_m` 2026-11–2026-12, `eia930_avg_soco_m` 2026-11–2026-12, `eia930_avg_azps_m` 2026-11–2026-12, `eia930_avg_srp_m` 2026-11–2026-12.
- Last, Dominion (tolv månader): 2026Q4 saknar på dagen `eia930_avg_pjm_dom_m` 2026-10–2026-12.

Lasten är backfill: EIA-930 har inga daterade versioner före 2026-11-23, så äldre månader har dagens värden (revideringar läcker in), och när EIA:s justerade kolumn först publicerades är inte belagt.

### 2. Elsidan: orderstock för elnät och gasturbiner

Orderstock för elnät = Quantas RPO + Eatons totala orderstock (fasta order) vid kvartalets slut. Gasturbiner = GE Vernovas orderstock och reservationer av leveransplatser i GW (extraktion ur pressmeddelanden, `publish=False`).

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Orderstock elnät, Quanta + Eaton | 68,0 mdr | +54,6 | +16,9 | +5,1 | 2026Q3 | 2026-11-03 | `el1_ob_nat` |
| Gasturbiner, orderstock och reservationer | 122,0 GW | +67,7 | -1,6 | -13,6 | 2026Q3 | 2026-10-28 | `ob_gev_backlog_and_slot_reservations_gas_power_equipment_end_level_gw` |
| Quanta Services, RPO | 41,8 mdr | +68,9 | +29,2 | +7,9 | 2026Q3 | 2026-10-29 | `rpo_pwr` |
| Eaton, orderstock | 26,2 mdr | +35,3 | -0,1 | +0,4 | 2026Q3 | 2026-11-03 | `rpo_etn` |
| GE Vernova, RPO utrustning | 104,1 mdr | +65,4 | +14,2 | +2,7 | 2026Q3 | 2026-10-28 | `rpo_gev_equipment` |
| Gasturbiner, orderstock | 64,0 GW | +66,2 | +24,5 | +3,8 | 2026Q3 | 2026-10-28 | `ob_gev_backlog_gas_power_equipment_end_level_gw` |
| Gasturbiner, reservationer | 58,0 GW | +69,3 | -28,8 | -31,4 | 2026Q3 | 2026-10-28 | `ob_gev_slot_reservations_gas_power_equipment_end_level_gw` |
| GE Vernova, orderstock Electrification | 42,2 mdr | +48,4 | – | – | 2026Q3 | 2026-10-28 | `ob_gev_backlog_electrification_equipment_end_level_musd` |
- Orderstock elnät, Quanta + Eaton: 2026Q4 saknar på dagen `rpo_pwr` 2026Q4, `rpo_etn` 2026Q4.

### 3. Utbyggnadens takt

Capex över fyra kvartal (KL1:s lageraggregat) och Digital Realtys tecknade hyresavtal i MW över fyra kvartal (bolagets andel, extraktion, `publish=False`). Yttre lagret och leasing som inte börjat är beskrivning och ingår inte i läsregeln.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Capex inre lagret (fyra kvartal) | 615,4 mdr | +62,4 | +9,6 | +4,6 | 2026Q3 | 2026-10-30 | `kl_capex4_inner` |
| Tecknade MW, Digital Realty (fyra kvartal) | 498 MW | +88,6 | +100,4 | +30,2 | 2026Q3 | 2026-10-29 | `el1_dlr_mw4` |
| Capex yttre lagret (fyra kvartal) | 125,7 mdr | +113,9 | – | +7,1 | 2026Q3 | 2026-11-12 | `kl_capex4_outer` |
| Alphabet, leasing som inte börjat | 130,5 mdr | +112,0 | -35,5 | +10,9 | 2026Q3 | 2026-10-29 | `lease_uncommenced_googl` |
| Amazon, leasing som inte börjat | 164,9 mdr | +78,8 | +32,9 | +1,2 | 2026Q3 | 2026-10-30 | `lease_uncommenced_amzn` |
| Meta, leasing som inte börjat | 355,7 mdr | +181,1 | +16,6 | -17,4 | 2026Q3 | 2026-10-22 | `lease_uncommenced_meta` |
| Oracle, leasing som inte börjat | 288,0 mdr | +106,0 | -62,5 | -34,5 | 2026Q3 | 2026-09-11 | `lease_uncommenced_orcl` |
- Tecknade MW, Digital Realty (fyra kvartal): 2026Q4 saknar på dagen `ob_dlr_leases_signed_total_dlr_share_q_level_mw` 2026Q4.

### 4. Leverantörernas egen capex (beskrivning)

Kvartalets capex, takt mot samma kvartal året före. Om leverantörerna bygger ut sin egen kapacitet lättar flaskhalsen med tiden.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Quanta Services, capex i kvartalet | 268 MUSD | +63,2 | +12,6 | +2,4 | 2026Q3 | 2026-10-29 | `capex_pwr` |
| Eaton, capex i kvartalet | 275 MUSD | +43,5 | +16,3 | +2,7 | 2026Q3 | 2026-11-03 | `capex_etn` |
| GE Vernova, capex i kvartalet | 647 MUSD | +96,3 | +20,5 | +31,6 | 2026Q3 | 2026-10-28 | `capex_gev` |

**Kraftplaner** (senaste uttalande per serie, MW):

- `plan_crwv_contracted_power_asof_value` 2026Q3: 4 600 MW (known_from 2026-11-10)
- `plan_crwv_active_power_asof_value` 2026Q3: 1 700 MW (known_from 2026-11-10)
- `plan_amzn_power_added_12m_asof_value` 2025Q4: 3 900 MW (known_from 2026-04-09)
- `plan_orcl_power_added_q_asof_value` 2026Q3: 850 MW (known_from 2026-09-10)

### 5. Läsregeln, mekaniskt

F0:s symmetriska regel: X:s takt mot Y:s förändring i takt, tecken −1, fönster 2 kvartal efter ursprunget. Gränser (låsta): Elpris (PPI, kommersiella kunder) ±5,0, Last (fem balansområden) ±2,0, Orderstock elnät (Quanta + Eaton, MUSD) ±10,0, Orderstock gasturbiner (GE Vernova, GW) ±10,0; capex inre lagret ±5,0, tecknade MW (Digital Realty) ±10,0. En rad per par, ingen sammanslagning.

- **Talar för, uppåt:** elsidan stramades åt (X ≥ +g) och takten bromsade (Y ≤ −h). **Talar för, nedåt:** elsidan lättade (X ≤ −g) och takten ökade (Y ≥ +h).
- **Talar emot:** takten följde elsidan åt samma håll. Uppåt pekar det på en gemensam efterfrågan och på att elen inte band, nedåt på att efterfrågan föll.
- En negativ förändring i takt betyder att tillväxten avtar, inte att capex minskar. Utslaget är en beskrivning, inget test.

Takten för X gör att en ihållande åtstramning räknas som en impuls varje kvartal. Har X impulser åt bara ett håll avgörs utslaget i praktiken av Y, och den andra riktningen prövas inte. Hur ofta det hänt står under varje rad.

Alla läsningar nedan vilar bara på värden som var publicerade före registerposten 2026-11-26, och Y:s senaste värden för capex var sedda före posten (posten, avsnitt (f)). Ingen av läsningarna är därför ett utfall på osedda data. Den första osedda läsningen: inre lagrets capex för 2026Q4 när alla fyra har lämnat in, omkring 2027-01-31; Digital Realty 2026Q4 omkring 2027-01-24. Sedda data avgörs per läsning (X25, punkt 1).

**Mot capex inre lagret:**

- **Elpris (PPI, kommersiella kunder):** inget av mönstren. t = 2026Q3 (ingen impuls i fönstret). X = el1_pris4 (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 27 av 267 ursprung med X (1959Q4–2026Q2). Impulser uppåt 62 (för 7, emot 1, inget 0, kan inte avgöras 54), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 205.
  Y var känt i hela fönstret i 27 av 267 ursprung, och 8 av 62 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 213 av 267; med den nya: 27 av 267.
  X har takt från 1959Q4 och Y förändring i takt från 2019Q4. Ett ursprung före 2019Q3 kan bara bli inget av mönstren (utan impuls) eller kan inte avgöras (Y saknas).
- **Last (fem balansområden):** talar emot, uppåt. t = 2026Q3; ursprung 2026Q2, X +2,9 (gräns ±2,0), uppgång, Y +9,6 vid 2026Q3 (gräns ±5,0). X = el1_last4 (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 23 av 23 ursprung med X (2020Q4–2026Q2). Impulser uppåt 15 (för 6, emot 7, inget 2, kan inte avgöras 0), nedåt 1 (för 1, emot 0, inget 0, kan inte avgöras 0), utan impuls 7.
  Y var känt i hela fönstret i 22 av 23 ursprung, och 16 av 16 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 23 av 23; med den nya: 23 av 23.
- **Orderstock elnät (Quanta + Eaton, MUSD) (huvudläsning):** talar emot, uppåt. t = 2026Q3; ursprung 2026Q2, X +45,3 (gräns ±10,0), uppgång, Y +9,6 vid 2026Q3 (gräns ±5,0). X = el1_ob_nat (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 20 av 20 ursprung med X (2021Q3–2026Q2). Impulser uppåt 20 (för 9, emot 9, inget 2, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 19 av 20 ursprung, och 20 av 20 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 20 av 20; med den nya: 20 av 20.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-26, och den är därför inget utfall på osedda data.
- **Orderstock gasturbiner (GE Vernova, GW):** talar emot, uppåt. t = 2026Q3; ursprung 2026Q2, X +74,6 (gräns ±10,0), uppgång, Y +9,6 vid 2026Q3 (gräns ±5,0). X = ob_gev_backlog_and_slot_reservations_gas_power_equipment_end_level_gw (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 2 ursprung med X (2026Q1–2026Q2). Impulser uppåt 2 (för 0, emot 2, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 1 av 2 ursprung, och 2 av 2 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 2 av 2; med den nya: 2 av 2.

**Mot tecknade MW (Digital Realty):**

- **Elpris (PPI, kommersiella kunder):** inget av mönstren. t = 2026Q3 (ingen impuls i fönstret). X = el1_pris4 (takt), Y = el1_dlr_mw4 (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 10 av 267 ursprung med X (1959Q4–2026Q2). Impulser uppåt 62 (för 0, emot 1, inget 0, kan inte avgöras 61), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 205.
  Y var känt i hela fönstret i 10 av 267 ursprung, och 1 av 62 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 206 av 267; med den nya: 10 av 267.
  X har takt från 1959Q4 och Y förändring i takt från 2024Q1. Ett ursprung före 2023Q4 kan bara bli inget av mönstren (utan impuls) eller kan inte avgöras (Y saknas).
- **Last (fem balansområden):** talar emot, uppåt. t = 2026Q3; ursprung 2026Q2, X +2,9 (gräns ±2,0), uppgång, Y +100,4 vid 2026Q3 (gräns ±10,0). X = el1_last4 (takt), Y = el1_dlr_mw4 (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 11 av 23 ursprung med X (2020Q4–2026Q2). Impulser uppåt 15 (för 4, emot 5, inget 0, kan inte avgöras 6), nedåt 1 (för 0, emot 0, inget 0, kan inte avgöras 1), utan impuls 7.
  Y var känt i hela fönstret i 10 av 23 ursprung, och 9 av 16 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 16 av 23; med den nya: 11 av 23.
  X har takt från 2020Q4 och Y förändring i takt från 2024Q1. Ett ursprung före 2023Q4 kan bara bli inget av mönstren (utan impuls) eller kan inte avgöras (Y saknas).
- **Orderstock elnät (Quanta + Eaton, MUSD):** talar emot, uppåt. t = 2026Q3; ursprung 2026Q2, X +45,3 (gräns ±10,0), uppgång, Y +100,4 vid 2026Q3 (gräns ±10,0). X = el1_ob_nat (takt), Y = el1_dlr_mw4 (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 11 av 20 ursprung med X (2021Q3–2026Q2). Impulser uppåt 20 (för 4, emot 7, inget 0, kan inte avgöras 9), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 10 av 20 ursprung, och 11 av 20 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 11 av 20; med den nya: 11 av 20.
  X har takt från 2021Q3 och Y förändring i takt från 2024Q1. Ett ursprung före 2023Q4 kan bara bli inget av mönstren (utan impuls) eller kan inte avgöras (Y saknas).
- **Orderstock gasturbiner (GE Vernova, GW):** talar emot, uppåt. t = 2026Q3; ursprung 2026Q2, X +74,6 (gräns ±10,0), uppgång, Y +100,4 vid 2026Q3 (gräns ±10,0). X = ob_gev_backlog_and_slot_reservations_gas_power_equipment_end_level_gw (takt), Y = el1_dlr_mw4 (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 2 ursprung med X (2026Q1–2026Q2). Impulser uppåt 2 (för 0, emot 2, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 1 av 2 ursprung, och 2 av 2 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 2 av 2; med den nya: 2 av 2.

**Tillägg S1 (registret 2026-11-27 S1, punkt 2): orderstock elnät som förändring i takt mot capex inre lagret.** En nionde rad bredvid de åtta låsta. Huvudläsningen ovan är oförändrad. X = förändringen i takt för orderstocken (gräns ±10,0), Y och tecken som i huvudläsningen. Förändringen i takt vänder när orderstocken växer långsammare än förut, också när den fortfarande växer, så riktningen nedåt kan inträffa.

- **Orderstock elnät (Quanta + Eaton, MUSD), förändring i takt:** talar emot, uppåt. t = 2026Q3; ursprung 2026Q2, X +16,5 (gräns ±10,0), uppgång, Y +9,6 vid 2026Q3 (gräns ±5,0). X = el1_ob_nat (förändring i takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 18 av 18 ursprung med X (2022Q1–2026Q2). Impulser uppåt 4 (för 1, emot 2, inget 1, kan inte avgöras 0), nedåt 3 (för 3, emot 0, inget 0, kan inte avgöras 0), utan impuls 11.
  Y var känt i hela fönstret i 17 av 18 ursprung, och 7 av 7 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 18 av 18; med den nya: 18 av 18.
  Riktningen nedåt har inträffat: 3 impulser nedåt och 4 uppåt i 18 ursprung med X (nedåt: för 3, emot 0, inget 0, kan inte avgöras 0).
  Samma observation som LT1:s huvudläsning (L1 före K-inre, k = 2): samma X, statistik, gränser, fönster och Y, men tecken +. Utslagen är spegelvända (talar för där är talar emot här och tvärtom) och impulserna desamma, så raden ger ingen observation utöver LT1:s.
  Förvärv flyttar förändringen i takt: uppåt vid förvärvets kvartal och kvartalet efter, nedåt fyra och fem kvartal senare (X25, punkt 2). Boyd Thermal ingår i Eatons orderstock från 2026Q1. Quantas förvärv är kodade ur 10-K och 10-Q från 2023 (`curated/acquisitions.csv`, registret 2026-11-27 QA1), inte före, och märket står i LT1:s huvudläsning, som har samma X (`docs/resultat/ledtid.md`). Raden har inget eget märke (registret 2026-11-27 S1, punkt 2, och X26, punkt 6).
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-27, och den är därför inget utfall på osedda data.

### 6. Att bevaka

Nästa inlämning per bolag, uppskattad som nästa kvartals slut plus medianen av avståndet för de åtta senaste inlämningarna:

- GE Vernova: 2026Q4 omkring 2027-01-23 (median 23 dagar, senast 2026-10-28, `ob_gev_backlog_and_slot_reservations_gas_power_equipment_end_level_gw`)
- Digital Realty: 2026Q4 omkring 2027-01-24 (median 24 dagar, senast 2026-10-29, `ob_dlr_leases_signed_total_dlr_share_q_level_mw`)
- Microsoft: 2026Q4 omkring 2027-01-29 (median 29 dagar, senast 2026-10-28, `capex_msft`)
- Alphabet: 2026Q4 omkring 2027-01-29 (median 29 dagar, senast 2026-10-29, `capex_googl`)
- Meta: 2026Q4 omkring 2027-01-30 (median 30 dagar, senast 2026-10-22, `capex_meta`)
- Quanta Services: 2026Q4 omkring 2027-01-30 (median 30 dagar, senast 2026-10-29, `rpo_pwr`)
- Amazon: 2026Q4 omkring 2027-01-31 (median 31 dagar, senast 2026-10-30, `capex_amzn`)
- Eaton: 2026Q4 omkring 2027-02-04 (median 35 dagar, senast 2026-11-03, `rpo_etn`)
- Månadsserierna (PPI, EIA-930) fyller kvartalet efter hand. Första osedda läsningen: inre lagrets capex för 2026Q4 när alla fyra har lämnat in, omkring 2027-01-31; Digital Realty 2026Q4 omkring 2027-01-24.

### 7. Förbehåll

- Y har kort historik (förändring i takt från 2019Q4 för capex och från 2024Q1 för Digital Realty, se under varje rad), och gasturbinerna har takt först från 2026Q1. Med åtta rader är detta en beskrivning och inget test. Några rader väntas ge "talar för" eller "talar emot" av en slump, och förändringen i takt vänder ofta av sig själv.
- Elnät och gasturbiner drivs också av annat än datacenter: elbolagens nät, förnybart, industri och export. Quantas RPO omfattar förnybart, telekom och rörledningar, och Eatons orderstock gäller hela bolaget.
- Förvärv blåser upp orderstockens takt: Prolec GE i GE Vernovas orderstock från 2026Q1, Boyd Thermal i Eatons Electrical Global från 2026-03-12 (R19).
- Elpriset är reglerade tariffer som speglar bränsle och nätkostnader med fördröjning, inte knapphetspriset. PPI-serien är regeldaterad, så det senaste kvartalet släpar. Elpriset har en nominell drift uppåt.
- Lasten är medellast och inte topplast, påverkas av väder och täcker fem områden, inte hela USA.
- Gasturbinerna och Digital Realtys MW är en extraktion (S3, granskad i R19, `publish=False`). Digital Realtys andel före 2025 är inte belagd (R19, F-4).
- Y för capex är hela capex, där servrar och chip är största delen. En begränsning i el syns troligen tidigare i byggen och leasing.
- "Bindande" kan inte visas: regeln ser samvariation i riktning, inte ett skuggpris, och X och Y har en gemensam drivkraft.
- Utanför ramen: köer för nätanslutning (LBNL), ERCOT:s kö för stora laster, PJM:s kapacitetspriser (klass `nej`, visas inte) och EIA-860M. Förslag med licensfråga, se registret, avsnitt (i).

## Elflaskhalsen per 2025-11-27

**Frågan:** Blir el den bindande begränsningen för utbyggnaden?

Elsidan (pris, last och orderstock för elnät och gasturbiner) mot utbyggnadens takt (capex i det inre lagret och tecknade MW hos Digital Realty). Takt = 100 × ln(värdet / värdet fyra kvartal tidigare). Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1 (samma takt som de fyra senaste kvartalen). Månadsserier blir kvartal som medel av de tolv månader som slutar med kvartalets sista månad. Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-26 EL1.

### 1. Elsidan: pris och last

PPI för el till kommersiella kunder (BLS) och medellast per månad ur EIA-930, summerad över PJM, ERCOT, Southern Company, APS och SRP. Dominion är en delregion av PJM och visas för sig.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Elpris, PPI kommersiella kunder (tolv månader) | 227,8 | +2,8 | -0,2 | +0,1 | 2025Q1 | 2025-08-14 | `el1_pris4` |
| Last, fem områden (tolv månader) | 185 810 MW | +3,5 | -1,0 | -0,1 | 2025Q3 | 2025-10-07 | `el1_last4` |
| Last, Dominion (tolv månader) | 15 065 MW | +7,4 | -0,5 | -0,2 | 2025Q3 | 2025-10-31 | `el1_last4_dom` |
- Elpris, PPI kommersiella kunder (tolv månader): 2025Q2 saknar på dagen `us_ppi_elec_commercial_m` 2025-06.
- Last, fem områden (tolv månader): 2025Q4 saknar på dagen `eia930_avg_pjm_m` 2025-11–2025-12, `eia930_avg_erco_m` 2025-11–2025-12, `eia930_avg_soco_m` 2025-11–2025-12, `eia930_avg_azps_m` 2025-11–2025-12, `eia930_avg_srp_m` 2025-11–2025-12.
- Last, Dominion (tolv månader): 2025Q4 saknar på dagen `eia930_avg_pjm_dom_m` 2025-10–2025-12.

Lasten är backfill: EIA-930 har inga daterade versioner före 2026-11-23, så äldre månader har dagens värden (revideringar läcker in), och när EIA:s justerade kolumn först publicerades är inte belagt.

### 2. Elsidan: orderstock för elnät och gasturbiner

Orderstock för elnät = Quantas RPO + Eatons totala orderstock (fasta order) vid kvartalets slut. Gasturbiner = GE Vernovas orderstock och reservationer av leveransplatser i GW (extraktion ur pressmeddelanden, `publish=False`).

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Orderstock elnät, Quanta + Eaton | 39,4 mdr | +22,3 | +10,4 | +1,8 | 2025Q3 | 2025-11-04 | `el1_ob_nat` |
| Gasturbiner, orderstock och reservationer | 62,0 GW | – | – | – | 2025Q3 | 2025-10-22 | `ob_gev_backlog_and_slot_reservations_gas_power_equipment_end_level_gw` |
| Quanta Services, RPO | 21,0 mdr | +29,5 | +12,4 | +1,8 | 2025Q3 | 2025-10-30 | `rpo_pwr` |
| Eaton, orderstock | 18,4 mdr | +14,6 | +8,1 | +1,5 | 2025Q3 | 2025-11-04 | `rpo_etn` |
| GE Vernova, RPO utrustning | 54,1 mdr | +25,1 | +17,7 | +4,0 | 2025Q3 | 2025-10-22 | `rpo_gev_equipment` |
| Gasturbiner, orderstock | 33,0 GW | – | – | – | 2025Q3 | 2025-10-22 | `ob_gev_backlog_gas_power_equipment_end_level_gw` |
| Gasturbiner, reservationer | 29,0 GW | – | – | – | 2025Q3 | 2025-10-22 | `ob_gev_slot_reservations_gas_power_equipment_end_level_gw` |
| GE Vernova, orderstock Electrification | 26,0 mdr | – | – | – | 2025Q3 | 2025-10-22 | `ob_gev_backlog_electrification_equipment_end_level_musd` |
- Orderstock elnät, Quanta + Eaton: 2025Q4 saknar på dagen `rpo_pwr` 2025Q4, `rpo_etn` 2025Q4.

### 3. Utbyggnadens takt

Capex över fyra kvartal (KL1:s lageraggregat) och Digital Realtys tecknade hyresavtal i MW över fyra kvartal (bolagets andel, extraktion, `publish=False`). Yttre lagret och leasing som inte börjat är beskrivning och ingår inte i läsregeln.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Capex inre lagret (fyra kvartal) | 329,8 mdr | +50,5 | +2,0 | -0,1 | 2025Q3 | 2025-10-31 | `kl_capex4_inner` |
| Tecknade MW, Digital Realty (fyra kvartal) | 205 MW | -70,9 | -100,8 | -55,3 | 2025Q3 | 2025-10-23 | `el1_dlr_mw4` |
| Capex yttre lagret (fyra kvartal) | – | – | – | – | – | – | `kl_capex4_outer` |
| Alphabet, leasing som inte börjat | 42,6 mdr | +194,4 | +37,4 | +19,7 | 2025Q3 | 2025-10-30 | `lease_uncommenced_googl` |
| Amazon, leasing som inte börjat | 75,0 mdr | +39,9 | -20,3 | -5,2 | 2025Q3 | 2025-10-31 | `lease_uncommenced_amzn` |
| Meta, leasing som inte börjat | 58,1 mdr | +114,6 | -59,8 | -43,3 | 2025Q3 | 2025-10-30 | `lease_uncommenced_meta` |
| Oracle, leasing som inte börjat | 99,8 mdr | +101,4 | +6,8 | +67,3 | 2025Q3 | 2025-09-10 | `lease_uncommenced_orcl` |
- Tecknade MW, Digital Realty (fyra kvartal): 2025Q4 saknar på dagen `ob_dlr_leases_signed_total_dlr_share_q_level_mw` 2025Q4.

### 4. Leverantörernas egen capex (beskrivning)

Kvartalets capex, takt mot samma kvartal året före. Om leverantörerna bygger ut sin egen kapacitet lättar flaskhalsen med tiden.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Quanta Services, capex i kvartalet | 142 MUSD | -40,0 | -86,8 | +5,0 | 2025Q3 | 2025-10-30 | `capex_pwr` |
| Eaton, capex i kvartalet | 178 MUSD | -2,8 | +19,1 | -14,6 | 2025Q3 | 2025-11-04 | `capex_etn` |
| GE Vernova, capex i kvartalet | 247 MUSD | +44,0 | +59,5 | +33,2 | 2025Q3 | 2025-10-22 | `capex_gev` |

**Kraftplaner** (senaste uttalande per serie, MW):

- `plan_crwv_contracted_power_asof_value` 2025Q3: 2 900 MW (known_from 2025-11-10)
- `plan_crwv_active_power_asof_value` 2025Q3: 590 MW (known_from 2025-11-10)
- `plan_amzn_power_added_12m_asof_value` 2025Q3: 3 800 MW (known_from 2025-10-30)

### 5. Läsregeln, mekaniskt

F0:s symmetriska regel: X:s takt mot Y:s förändring i takt, tecken −1, fönster 2 kvartal efter ursprunget. Gränser (låsta): Elpris (PPI, kommersiella kunder) ±5,0, Last (fem balansområden) ±2,0, Orderstock elnät (Quanta + Eaton, MUSD) ±10,0, Orderstock gasturbiner (GE Vernova, GW) ±10,0; capex inre lagret ±5,0, tecknade MW (Digital Realty) ±10,0. En rad per par, ingen sammanslagning.

- **Talar för, uppåt:** elsidan stramades åt (X ≥ +g) och takten bromsade (Y ≤ −h). **Talar för, nedåt:** elsidan lättade (X ≤ −g) och takten ökade (Y ≥ +h).
- **Talar emot:** takten följde elsidan åt samma håll. Uppåt pekar det på en gemensam efterfrågan och på att elen inte band, nedåt på att efterfrågan föll.
- En negativ förändring i takt betyder att tillväxten avtar, inte att capex minskar. Utslaget är en beskrivning, inget test.

Takten för X gör att en ihållande åtstramning räknas som en impuls varje kvartal. Har X impulser åt bara ett håll avgörs utslaget i praktiken av Y, och den andra riktningen prövas inte. Hur ofta det hänt står under varje rad.

Alla läsningar nedan vilar bara på värden som var publicerade före registerposten 2026-11-26, och Y:s senaste värden för capex var sedda före posten (posten, avsnitt (f)). Ingen av läsningarna är därför ett utfall på osedda data. Den första osedda läsningen: inre lagrets capex för 2026Q4 när alla fyra har lämnat in, omkring 2027-02-01; Digital Realty 2026Q4 omkring 2027-01-24. Sedda data avgörs per läsning (X25, punkt 1).

**Mot capex inre lagret:**

- **Elpris (PPI, kommersiella kunder):** kan inte avgöras. t = 2025Q3 (X saknas vid 2025Q2). X = el1_pris4 (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 23 av 262 ursprung med X (1959Q4–2025Q1). Impulser uppåt 62 (för 7, emot 1, inget 0, kan inte avgöras 54), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 200.
  Y var känt i hela fönstret i 23 av 262 ursprung, och 8 av 62 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 208 av 262; med den nya: 23 av 262.
  X har takt från 1959Q4 och Y förändring i takt från 2019Q4. Ett ursprung före 2019Q3 kan bara bli inget av mönstren (utan impuls) eller kan inte avgöras (Y saknas).
- **Last (fem balansområden):** kan inte avgöras. t = 2025Q3; ursprung 2025Q2, X +2,9 (gräns ±2,0), uppgång (fönstret öppet till 2025Q4). X = el1_last4 (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 18 av 19 ursprung med X (2020Q4–2025Q2). Impulser uppåt 11 (för 6, emot 4, inget 0, kan inte avgöras 1), nedåt 1 (för 1, emot 0, inget 0, kan inte avgöras 0), utan impuls 7.
  Y var känt i hela fönstret i 18 av 19 ursprung, och 11 av 12 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 18 av 19; med den nya: 18 av 19.
- **Orderstock elnät (Quanta + Eaton, MUSD) (huvudläsning):** kan inte avgöras. t = 2025Q3; ursprung 2025Q2, X +21,5 (gräns ±10,0), uppgång (fönstret öppet till 2025Q4). X = el1_ob_nat (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 15 av 16 ursprung med X (2021Q3–2025Q2). Impulser uppåt 16 (för 9, emot 6, inget 0, kan inte avgöras 1), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 15 av 16 ursprung, och 15 av 16 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 15 av 16; med den nya: 15 av 16.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-26, och den är därför inget utfall på osedda data.
- **Orderstock gasturbiner (GE Vernova, GW):** kan inte avgöras. t = 2025Q3 (X saknas vid 2025Q1; X saknas vid 2025Q2). X = ob_gev_backlog_and_slot_reservations_gas_power_equipment_end_level_gw (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.

**Mot tecknade MW (Digital Realty):**

- **Elpris (PPI, kommersiella kunder):** kan inte avgöras. t = 2025Q3 (X saknas vid 2025Q2). X = el1_pris4 (takt), Y = el1_dlr_mw4 (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 6 av 262 ursprung med X (1959Q4–2025Q1). Impulser uppåt 62 (för 0, emot 1, inget 0, kan inte avgöras 61), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 200.
  Y var känt i hela fönstret i 6 av 262 ursprung, och 1 av 62 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 201 av 262; med den nya: 6 av 262.
  X har takt från 1959Q4 och Y förändring i takt från 2024Q1. Ett ursprung före 2023Q4 kan bara bli inget av mönstren (utan impuls) eller kan inte avgöras (Y saknas).
- **Last (fem balansområden):** talar för mekanismen, uppåt. t = 2025Q3; ursprung 2025Q2, X +2,9 (gräns ±2,0), uppgång, Y -100,8 vid 2025Q3 (gräns ±10,0). X = el1_last4 (takt), Y = el1_dlr_mw4 (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 7 av 19 ursprung med X (2020Q4–2025Q2). Impulser uppåt 11 (för 3, emot 2, inget 0, kan inte avgöras 6), nedåt 1 (för 0, emot 0, inget 0, kan inte avgöras 1), utan impuls 7.
  Y var känt i hela fönstret i 6 av 19 ursprung, och 5 av 12 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 12 av 19; med den nya: 7 av 19.
  X har takt från 2020Q4 och Y förändring i takt från 2024Q1. Ett ursprung före 2023Q4 kan bara bli inget av mönstren (utan impuls) eller kan inte avgöras (Y saknas).
- **Orderstock elnät (Quanta + Eaton, MUSD):** talar för mekanismen, uppåt. t = 2025Q3; ursprung 2025Q2, X +21,5 (gräns ±10,0), uppgång, Y -100,8 vid 2025Q3 (gräns ±10,0). X = el1_ob_nat (takt), Y = el1_dlr_mw4 (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 7 av 16 ursprung med X (2021Q3–2025Q2). Impulser uppåt 16 (för 3, emot 4, inget 0, kan inte avgöras 9), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 6 av 16 ursprung, och 7 av 16 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 7 av 16; med den nya: 7 av 16.
  X har takt från 2021Q3 och Y förändring i takt från 2024Q1. Ett ursprung före 2023Q4 kan bara bli inget av mönstren (utan impuls) eller kan inte avgöras (Y saknas).
- **Orderstock gasturbiner (GE Vernova, GW):** kan inte avgöras. t = 2025Q3 (X saknas vid 2025Q1; X saknas vid 2025Q2). X = ob_gev_backlog_and_slot_reservations_gas_power_equipment_end_level_gw (takt), Y = el1_dlr_mw4 (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.

**Tillägg S1 (registret 2026-11-27 S1, punkt 2): orderstock elnät som förändring i takt mot capex inre lagret.** En nionde rad bredvid de åtta låsta. Huvudläsningen ovan är oförändrad. X = förändringen i takt för orderstocken (gräns ±10,0), Y och tecken som i huvudläsningen. Förändringen i takt vänder när orderstocken växer långsammare än förut, också när den fortfarande växer, så riktningen nedåt kan inträffa.

- **Orderstock elnät (Quanta + Eaton, MUSD), förändring i takt:** inget av mönstren. t = 2025Q3 (ingen impuls i fönstret). X = el1_ob_nat (förändring i takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 13 av 14 ursprung med X (2022Q1–2025Q2). Impulser uppåt 1 (för 1, emot 0, inget 0, kan inte avgöras 0), nedåt 3 (för 3, emot 0, inget 0, kan inte avgöras 0), utan impuls 10.
  Y var känt i hela fönstret i 13 av 14 ursprung, och 4 av 4 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 14 av 14; med den nya: 13 av 14.
  Riktningen nedåt har inträffat: 3 impulser nedåt och 1 uppåt i 14 ursprung med X (nedåt: för 3, emot 0, inget 0, kan inte avgöras 0).
  Samma observation som LT1:s huvudläsning (L1 före K-inre, k = 2): samma X, statistik, gränser, fönster och Y, men tecken +. Utslagen är spegelvända (talar för där är talar emot här och tvärtom) och impulserna desamma, så raden ger ingen observation utöver LT1:s.
  Förvärv flyttar förändringen i takt: uppåt vid förvärvets kvartal och kvartalet efter, nedåt fyra och fem kvartal senare (X25, punkt 2). Boyd Thermal ingår i Eatons orderstock från 2026Q1. Quantas förvärv är kodade ur 10-K och 10-Q från 2023 (`curated/acquisitions.csv`, registret 2026-11-27 QA1), inte före, och märket står i LT1:s huvudläsning, som har samma X (`docs/resultat/ledtid.md`). Raden har inget eget märke (registret 2026-11-27 S1, punkt 2, och X26, punkt 6).
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-27, och den är därför inget utfall på osedda data.

### 6. Att bevaka

Nästa inlämning per bolag, uppskattad som nästa kvartals slut plus medianen av avståndet för de åtta senaste inlämningarna:

- GE Vernova: 2025Q4 omkring 2026-01-23 (median 23 dagar, senast 2025-10-22, `ob_gev_backlog_and_slot_reservations_gas_power_equipment_end_level_gw`)
- Digital Realty: 2025Q4 omkring 2026-01-24 (median 24 dagar, senast 2025-10-23, `ob_dlr_leases_signed_total_dlr_share_q_level_mw`)
- Alphabet: 2025Q4 omkring 2026-01-28 (median 28 dagar, senast 2025-10-30, `capex_googl`)
- Microsoft: 2025Q4 omkring 2026-01-30 (median 30 dagar, senast 2025-10-29, `capex_msft`)
- Meta: 2025Q4 omkring 2026-01-31 (median 31 dagar, senast 2025-10-30, `capex_meta`)
- Quanta Services: 2025Q4 omkring 2026-01-31 (median 31 dagar, senast 2025-10-30, `rpo_pwr`)
- Amazon: 2025Q4 omkring 2026-02-01 (median 32 dagar, senast 2025-10-31, `capex_amzn`)
- Eaton: 2025Q4 omkring 2026-02-02 (median 33 dagar, senast 2025-11-04, `rpo_etn`)
- Månadsserierna (PPI, EIA-930) fyller kvartalet efter hand. Första osedda läsningen: inre lagrets capex för 2026Q4 när alla fyra har lämnat in, omkring 2027-02-01; Digital Realty 2026Q4 omkring 2027-01-24.

### 7. Förbehåll

- Y har kort historik (förändring i takt från 2019Q4 för capex och från 2024Q1 för Digital Realty, se under varje rad), och gasturbinerna har takt först från 2026Q1. Med åtta rader är detta en beskrivning och inget test. Några rader väntas ge "talar för" eller "talar emot" av en slump, och förändringen i takt vänder ofta av sig själv.
- Elnät och gasturbiner drivs också av annat än datacenter: elbolagens nät, förnybart, industri och export. Quantas RPO omfattar förnybart, telekom och rörledningar, och Eatons orderstock gäller hela bolaget.
- Förvärv blåser upp orderstockens takt: Prolec GE i GE Vernovas orderstock från 2026Q1, Boyd Thermal i Eatons Electrical Global från 2026-03-12 (R19).
- Elpriset är reglerade tariffer som speglar bränsle och nätkostnader med fördröjning, inte knapphetspriset. PPI-serien är regeldaterad, så det senaste kvartalet släpar. Elpriset har en nominell drift uppåt.
- Lasten är medellast och inte topplast, påverkas av väder och täcker fem områden, inte hela USA.
- Gasturbinerna och Digital Realtys MW är en extraktion (S3, granskad i R19, `publish=False`). Digital Realtys andel före 2025 är inte belagd (R19, F-4).
- Y för capex är hela capex, där servrar och chip är största delen. En begränsning i el syns troligen tidigare i byggen och leasing.
- "Bindande" kan inte visas: regeln ser samvariation i riktning, inte ett skuggpris, och X och Y har en gemensam drivkraft.
- Utanför ramen: köer för nätanslutning (LBNL), ERCOT:s kö för stora laster, PJM:s kapacitetspriser (klass `nej`, visas inte) och EIA-860M. Förslag med licensfråga, se registret, avsnitt (i).
