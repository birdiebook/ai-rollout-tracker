# Antenner: de följda frågorna i en tabell

*Rättad efter granskningen R28 (rättningsspår X25, `docs/mattregister.md`, 2026-11-26 X25): BG1:s fakta har alltid radens kvartal (Oracles rader visades förut som ändrade fast de inte var det), varje fråga anger om huvudläsningen är på osedda data, och rapporten säger vilka frågor som delar serier. Inga utslag ändrades. Avsnittet nedan är genererat på nytt med kommandot.*

Integrationen av körning 16 (F0, LT1, BG1, EL1). Avsnittet nedan är utdata från
`python -m ai_tracker.followed antenner --as-of 2026-11-26` på den sammanslagna koden, oförändrad utom att rubrikerna
ligger en nivå lägre. Varje frågas egen rapport finns i `docs/resultat/<fråga>.md`, och raderna här är samma
huvudläsning som där (kontrollerat: rapporterna per 2026-11-26 är byte för byte desamma i integrationen som i respektive
spårs gren).

Alla utslag per 2026-11-26 bygger på kvartal som var sedda när registerposterna skrevs. De är beskrivningar, inte
utfall på osedda data, och de första osedda läsningarna står i sista kolumnen. Frågorna vägs inte ihop. Flera av dem
läser samma capex-takt i det inre lagret (+9,6 för 2026Q3 i KL1, LT1 och EL1), så de är inte oberoende belägg. LT1:s och EL1:s huvudläsningar har dessutom samma X (`rpo_pwr` + `rpo_etn`), läst med olika statistik och tecken, så "talar för" i LT1 och "talar emot" i EL1 är samma rörelse och tillsammans en observation (avsnittet "Samma serier i flera frågor"). BG1:s rader ändrar kvartal från 2026Q2 till 2026Q3 mot förra månaden, och det står som en ändring per rad.

## Antenner per 2026-11-26

En rad per följd fråga: senaste utslaget (frågans huvudläsning), vad som ändrats mot 2026-10-26 och nästa osedda läsning. Bara data kända på respektive dag. En beskrivning: inga larmnivåer, och frågorna vägs inte ihop. Registret: `docs/mattregister.md`, 2026-11-26 F0, avsnitt (c).

| Fråga | Senaste utslag | Ändrat mot 2026-10-26 | Nästa osedda läsning |
|---|---|---|---|
| **betalningsgapet**: Växer de intäkter som ska bära investeringarna (molnintäkter, AI-nyckeltal, RPO och frontlabbens intäkter) i takt med intäktskravet från avskrivningar och kapitalkostnad, eller öppnas eller sluts gapet? | talar emot (2026Q3) | kvartal: 2026Q2 → 2026Q3; Gapet mot RPO, molnfyran, r = 0,10: talar för mekanismen (2026Q2) → talar för mekanismen (2026Q3); Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,00 (bara avskrivningar): inget av mönstren (2026Q2) → inget av mönstren (2026Q3); Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,08: talar emot (2026Q2) → talar emot (2026Q3); Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,12: talar emot (2026Q2) → talar emot (2026Q3); Känslighet: gapet mot RPO utan Oracle, r = 0,10: talar för mekanismen (2026Q2) → talar för mekanismen (2026Q3); Microsoft: gapet mot molnintäkterna: talar emot (2026Q2) → talar emot (2026Q3); Microsoft: gapet mot RPO: talar för mekanismen (2026Q2) → talar för mekanismen (2026Q3); Alphabet: gapet mot molnintäkterna: inget av mönstren (2026Q2) → inget av mönstren (2026Q3); Alphabet: gapet mot RPO: talar för mekanismen (2026Q2) → talar för mekanismen (2026Q3); Amazon: gapet mot molnintäkterna: kan inte avgöras (2026Q2) → talar emot (2026Q3); Amazon: gapet mot RPO: kan inte avgöras (2026Q2) → talar för mekanismen (2026Q3); CoreWeave: gapet mot molnintäkterna: talar emot (2026Q2) → talar emot (2026Q3); CoreWeave: gapet mot RPO: talar för mekanismen (2026Q2) → talar för mekanismen (2026Q3); Gapets takt mot molnintäkterna, molnfyran: +7,6 (2026Q2) → +6,5 (2026Q3); Förändring i capex-takt, molnfyran: +7,8 (2026Q2) → +10,7 (2026Q3); Impulser i huvudläsningens historik: upp 4, ned 0, av 6 → upp 5, ned 0, av 7 | Oracle 2026Q4 omkring 2026-12-11, bolagsraderna; molnfyrans huvudläsning när alla fyra har lämnat in (uppskattat 2027-01-31) |
| **elflaskhalsen**: Blir el den bindande begränsningen för utbyggnaden? | talar emot, uppåt (2026Q3) | kvartal: 2026Q2 → 2026Q3; Orderstock elnät, takt: +45,3 (2026Q2) → +54,6 (2026Q3); Capex inre lagret, förändring i takt: +6,2 (2026Q2) → +9,6 (2026Q3); Huvudläsningen, impulser upp/ned: 19/0 av 19 ursprung → 20/0 av 20 ursprung | inre lagrets capex för 2026Q4 när alla fyra har lämnat in, omkring 2027-01-31; Digital Realty 2026Q4 omkring 2027-01-24 |
| **kreditlagret**: Ändras finansieringens pris och tillgång i de yttre lagren, och följer investeringstakten där med? | kan inte avgöras (2026Q3) | kvartal: 2026Q2 → 2026Q3; CoreWeave mot inre lagret, utslag: talar emot (1) (2026Q2) → talar emot (1) (2026Q3); Nebius mot inre lagret, utslag: inget av mönstren (2026Q2) → inget av mönstren (2026Q3); IREN mot inre lagret, utslag: kan inte avgöras (2026Q2) → kan inte avgöras (2026Q3); Förändring i capex-takt, inre: +6,2 (2026Q2) → +9,6 (2026Q3); A har gällt (yttre): 3 av 3 kvartal → 4 av 4 kvartal | Oracle 2026Q4 omkring 2026-12-11, mot inre lagret; yttre lagret när alla fyra har lämnat in (senast uppskattat 2027-02-13) |
| **ledtid**: Rör sig order och orderstock hos leverantörerna (kraft, kylning, elnät, nät, servrar, datacenterleasing) före eller efter capex-takten hos hyperskalarna och de yttre lagren, och ändras ledtiden? | talar för (2026Q3) | kvartal: 2026Q2 → 2026Q3; L1 före K-inre, k = 4: talar för (2026Q2) → talar för (2026Q3); L1 efter K-inre, k = 2: inget av mönstren (2026Q2) → talar för (2026Q3); L2 före K-inre, k = 2: talar för (2026Q2) → talar för (2026Q3); L3 före K-inre, k = 2: inget av mönstren (2026Q2) → inget av mönstren (2026Q3); L3 efter K-inre, k = 2: inget av mönstren (2026Q2) → kan inte avgöras (2026Q3); O1 före K-inre, k = 2: talar för (2026Q2) → talar för (2026Q3); O1 efter K-inre, k = 2: inget av mönstren (2026Q2) → kan inte avgöras (2026Q3); O2 före K-inre, k = 2: talar för (2026Q2) → talar för (2026Q3); O2 efter K-inre, k = 2: inget av mönstren (2026Q2) → talar för (2026Q3); L1 före K-yttre, k = 2: kan inte avgöras (2026Q2) → kan inte avgöras (2026Q3); L1 efter K-yttre, k = 2: kan inte avgöras (2026Q2) → kan inte avgöras (2026Q3); Ledtid L1 före K-inre (k = 4), senaste / median tidigare: 1 / 3,0 kvartal → 1 / 2,0 kvartal; Förändring i takt, L1 Kraft och elnät: +16,5 (2026Q2) → +16,9 (2026Q3); Förändring i takt, K-inre: +6,2 (2026Q2) → +9,6 (2026Q3) | L2 efter K-inre med 2026Q3 omkring 2026-12-09; huvudläsningen (L1 före K-inre) när alla fyra i inre lagret har lämnat in 2026Q4, omkring 2027-01-31 |

### Samma serier i flera frågor

Huvudläsningarnas X och Y som de katalogserier de summerar (X25, punkt 3). Frågor som delar serier ger inte oberoende belägg.

- **betalningsgapet och elflaskhalsen** har delvis samma Y (gemensamt: `capex_amzn` + `capex_googl` + `capex_msft`). Utslagen är inte oberoende.
- **betalningsgapet och ledtid** har delvis samma Y (gemensamt: `capex_amzn` + `capex_googl` + `capex_msft`). Utslagen är inte oberoende.
- **elflaskhalsen och ledtid** har samma huvudpar: X = `rpo_etn` + `rpo_pwr` och Y = `capex_amzn` + `capex_googl` + `capex_meta` + `capex_msft` (elflaskhalsen: X:s takt, tecken −; ledtid: X:s förändring i takt, tecken +). Det är två läsningar av samma rörelse och tillsammans inte mer än en observation. Med olika statistik eller tecken kan samma kvartal ge olika utslag i de två frågorna.

### betalningsgapet

- Gapet mot RPO, molnfyran, r = 0,10: talar för mekanismen (2026Q3)
- Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,00 (bara avskrivningar): inget av mönstren (2026Q3)
- Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,08: talar emot (2026Q3)
- Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,12: talar emot (2026Q3)
- Känslighet: gapet mot RPO utan Oracle, r = 0,10: talar för mekanismen (2026Q3)
- Microsoft: gapet mot molnintäkterna: talar emot (2026Q3)
- Microsoft: gapet mot RPO: talar för mekanismen (2026Q3)
- Alphabet: gapet mot molnintäkterna: inget av mönstren (2026Q3)
- Alphabet: gapet mot RPO: talar för mekanismen (2026Q3)
- Amazon: gapet mot molnintäkterna: talar emot (2026Q3)
- Amazon: gapet mot RPO: talar för mekanismen (2026Q3)
- Oracle: gapet mot molnintäkterna: talar för mekanismen (2026Q3)
- Oracle: gapet mot RPO: talar emot (2026Q3)
- CoreWeave: gapet mot molnintäkterna: talar emot (2026Q3)
- CoreWeave: gapet mot RPO: talar för mekanismen (2026Q3)
- Gapets takt mot molnintäkterna, molnfyran: +6,5 (2026Q3)
- Förändring i capex-takt, molnfyran: +10,7 (2026Q3)
- Impulser i huvudläsningens historik: upp 5, ned 0, av 7
- Huvudläsningen på osedda data: nej

### elflaskhalsen

- Elpris (PPI, kommersiella kunder) mot capex inre lagret: inget av mönstren
- Last (fem balansområden) mot capex inre lagret: talar emot, uppåt
- Orderstock gasturbiner (GE Vernova, GW) mot capex inre lagret: talar emot, uppåt
- Elpris (PPI, kommersiella kunder) mot tecknade MW (Digital Realty): inget av mönstren
- Last (fem balansområden) mot tecknade MW (Digital Realty): talar emot, uppåt
- Orderstock elnät (Quanta + Eaton, MUSD) mot tecknade MW (Digital Realty): talar emot, uppåt
- Orderstock gasturbiner (GE Vernova, GW) mot tecknade MW (Digital Realty): talar emot, uppåt
- Orderstock elnät, takt: +54,6 (2026Q3)
- Capex inre lagret, förändring i takt: +9,6 (2026Q3)
- Huvudläsningen, impulser upp/ned: 20/0 av 20 ursprung
- Huvudläsningen på osedda data: nej

### kreditlagret

- Oracle mot inre lagret, utslag: talar för mekanismen (2026Q3)
- CoreWeave mot inre lagret, utslag: talar emot (1) (2026Q3)
- Nebius mot inre lagret, utslag: inget av mönstren (2026Q3)
- IREN mot inre lagret, utslag: kan inte avgöras (2026Q3)
- Yttre lagret, A: ja
- Förändring i capex-takt, yttre: –
- Förändring i capex-takt, inre: +9,6 (2026Q3)
- A har gällt (yttre): 4 av 4 kvartal

### ledtid

- L1 före K-inre, k = 4: talar för (2026Q3)
- L1 efter K-inre, k = 2: talar för (2026Q3)
- L2 före K-inre, k = 2: talar för (2026Q3)
- L2 efter K-inre, k = 2: inget av mönstren (2026Q2)
- L3 före K-inre, k = 2: inget av mönstren (2026Q3)
- L3 efter K-inre, k = 2: kan inte avgöras (2026Q3)
- O1 före K-inre, k = 2: talar för (2026Q3)
- O1 efter K-inre, k = 2: kan inte avgöras (2026Q3)
- O2 före K-inre, k = 2: talar för (2026Q3)
- O2 efter K-inre, k = 2: talar för (2026Q3)
- L1 före K-yttre, k = 2: kan inte avgöras (2026Q3)
- L1 efter K-yttre, k = 2: kan inte avgöras (2026Q3)
- Ledtid L1 före K-inre (k = 4), senaste / median tidigare: 1 / 2,0 kvartal
- Förändring i takt, L1 Kraft och elnät: +16,9 (2026Q3)
- Förändring i takt, K-inre: +9,6 (2026Q3)
- Huvudläsningen på osedda data: nej
