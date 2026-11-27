# Antenner: de följda frågorna i en tabell

*Ägarbeslut 2026-11-27 (spår B18, `docs/mattregister.md`, 2026-11-27 B18): prisvolyms rad följer huvudläsningen H-G (geometriskt kvartalsmedel), med bisakerna a-G och b-G och de låsta raderna H, a och b som fakta (punkt 2). Utslaget är detsamma som för H, och `main_inputs` är samma katalogserier. Kreditlagret har en ny fakta, om huvudläsningen är på osedda data, avgjort per läsning (punkt 3; nej per 2026-11-27). Inga utslag ändrades. Avsnittet nedan är genererat på nytt per 2026-11-27.*


*Slutintegrationen av körning 17 (efter R29 och X26): avsnittet nedan är genererat på nytt per 2026-11-27 på den slutliga koden och är oförändrat mot X26.*

*Efter granskningen R29 (rättningsspår X26, `docs/mattregister.md`, 2026-11-27 X26): prisvolym har en ny fakta med utslagen för de geometriska raderna H-G, a-G och b-G bredvid de låsta (samma utslag i dag). Inga rader och inga utslag ändrades.*


*Integrationen av körning 17 (S1, AN1, QA1, PV1): avsnittet nedan är genererat på nytt per 2026-11-27 på den sammanslagna koden. Ny rad: prisvolym (PV1), vars huvudläsning inte kan avgöras (GPQA-priset har ännu ingen förändring i takt) och inte delar serier med någon annan frågas huvudläsning. AN1 (Anthropics redovisade tal i BG1) och QA1 (Quantas förvärv i LT1:s märke) ändrar ingen rad. Övriga rader är desamma som i S1:s gren.*

*Tillägg S1 (`docs/mattregister.md`, 2026-11-27 S1): avsnittet nedan är genererat på nytt per 2026-11-27, och jämförelsen är mot 2026-10-27. Varje frågas huvudläsning och utslag är oförändrade. Nya fakta, märkta "S1", står som tillägg: för kreditlagret den symmetriska läsningen per enhet (pris- och beroendemått mot samma enhets capex-takt, tecken −), för elflaskhalsen orderstocken för elnät som förändring i takt mot capex i det inre lagret, som kan ge impulser nedåt (3 nedåt och 4 uppåt i historiken) men är LT1:s huvudläsning med motsatt tecken och ingen ny observation. Inget nytt kvartal har blivit känt sedan 2026-11-26, så texten nedan om utslagen per 2026-11-26 gäller också per 2026-11-27. F0:s räkning av prövade ursprung (S1, punkt 3) syns i varje frågas rapport, inte här.*

*Rättad efter granskningen R28 (rättningsspår X25, `docs/mattregister.md`, 2026-11-26 X25): BG1:s fakta har alltid radens kvartal (Oracles rader visades förut som ändrade fast de inte var det), varje fråga anger om huvudläsningen är på osedda data, och rapporten säger vilka frågor som delar serier. Inga utslag ändrades. Avsnittet nedan är genererat på nytt med kommandot.*

Integrationen av körning 16 (F0, LT1, BG1, EL1), med PV1 från körning 17. Avsnittet nedan är utdata från
`python -m ai_tracker.followed antenner --as-of 2026-11-27` på den sammanslagna koden, oförändrad utom att rubrikerna
ligger en nivå lägre. Varje frågas egen rapport finns i `docs/resultat/<fråga>.md`, och raderna här är samma
huvudläsning som där (kontrollerat: rapporterna per 2026-11-26 är byte för byte desamma i integrationen som i respektive
spårs gren).

Alla utslag per 2026-11-27 (som per 2026-11-26) bygger på kvartal som var sedda när registerposterna skrevs. De är beskrivningar, inte
utfall på osedda data, och de första osedda läsningarna står i sista kolumnen. Frågorna vägs inte ihop. Flera av dem
läser samma capex-takt i det inre lagret (+9,6 för 2026Q3 i KL1, LT1 och EL1), så de är inte oberoende belägg. LT1:s och EL1:s huvudläsningar har dessutom samma X (`rpo_pwr` + `rpo_etn`), läst med olika statistik och tecken, så "talar för" i LT1 och "talar emot" i EL1 är samma rörelse och tillsammans en observation (avsnittet "Samma serier i flera frågor"). BG1:s rader ändrar kvartal från 2026Q2 till 2026Q3 mot förra månaden, och det står som en ändring per rad.

## Antenner per 2026-11-27

En rad per följd fråga: senaste utslaget (frågans huvudläsning), vad som ändrats mot 2026-10-27 och nästa osedda läsning. Bara data kända på respektive dag. En beskrivning: inga larmnivåer, och frågorna vägs inte ihop. Registret: `docs/mattregister.md`, 2026-11-26 F0, avsnitt (c).

| Fråga | Senaste utslag | Ändrat mot 2026-10-27 | Nästa osedda läsning |
|---|---|---|---|
| **betalningsgapet**: Växer de intäkter som ska bära investeringarna (molnintäkter, AI-nyckeltal, RPO och frontlabbens intäkter) i takt med intäktskravet från avskrivningar och kapitalkostnad, eller öppnas eller sluts gapet? | talar emot (2026Q3) | kvartal: 2026Q2 → 2026Q3; Gapet mot RPO, molnfyran, r = 0,10: talar för mekanismen (2026Q2) → talar för mekanismen (2026Q3); Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,00 (bara avskrivningar): inget av mönstren (2026Q2) → inget av mönstren (2026Q3); Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,08: talar emot (2026Q2) → talar emot (2026Q3); Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,12: talar emot (2026Q2) → talar emot (2026Q3); Känslighet: gapet mot RPO utan Oracle, r = 0,10: talar för mekanismen (2026Q2) → talar för mekanismen (2026Q3); Microsoft: gapet mot molnintäkterna: talar emot (2026Q2) → talar emot (2026Q3); Microsoft: gapet mot RPO: talar för mekanismen (2026Q2) → talar för mekanismen (2026Q3); Alphabet: gapet mot molnintäkterna: inget av mönstren (2026Q2) → inget av mönstren (2026Q3); Alphabet: gapet mot RPO: talar för mekanismen (2026Q2) → talar för mekanismen (2026Q3); Amazon: gapet mot molnintäkterna: kan inte avgöras (2026Q2) → talar emot (2026Q3); Amazon: gapet mot RPO: kan inte avgöras (2026Q2) → talar för mekanismen (2026Q3); CoreWeave: gapet mot molnintäkterna: talar emot (2026Q2) → talar emot (2026Q3); CoreWeave: gapet mot RPO: talar för mekanismen (2026Q2) → talar för mekanismen (2026Q3); Gapets takt mot molnintäkterna, molnfyran: +7,6 (2026Q2) → +6,5 (2026Q3); Förändring i capex-takt, molnfyran: +7,8 (2026Q2) → +10,7 (2026Q3); Impulser i huvudläsningens historik: upp 4, ned 0, av 6 → upp 5, ned 0, av 7 | Oracle 2026Q4 omkring 2026-12-11, bolagsraderna; molnfyrans huvudläsning när alla fyra har lämnat in (uppskattat 2027-01-31) |
| **elflaskhalsen**: Blir el den bindande begränsningen för utbyggnaden? | talar emot, uppåt (2026Q3) | kvartal: 2026Q2 → 2026Q3; Orderstock elnät, takt: +45,3 (2026Q2) → +54,6 (2026Q3); Capex inre lagret, förändring i takt: +6,2 (2026Q2) → +9,6 (2026Q3); Huvudläsningen, impulser upp/ned: 19/0 av 19 ursprung → 20/0 av 20 ursprung; S1: samma rad, impulser upp/ned: 3/3 av 17 ursprung → 4/3 av 18 ursprung | inre lagrets capex för 2026Q4 när alla fyra har lämnat in, omkring 2027-01-31; Digital Realty 2026Q4 omkring 2027-01-24 |
| **kreditlagret**: Ändras finansieringens pris och tillgång i de yttre lagren, och följer investeringstakten där med? | kan inte avgöras (2026Q3) | kvartal: 2026Q2 → 2026Q3; CoreWeave mot inre lagret, utslag: talar emot (1) (2026Q2) → talar emot (1) (2026Q3); Nebius mot inre lagret, utslag: inget av mönstren (2026Q2) → inget av mönstren (2026Q3); IREN mot inre lagret, utslag: kan inte avgöras (2026Q2) → kan inte avgöras (2026Q3); Förändring i capex-takt, inre: +6,2 (2026Q2) → +9,6 (2026Q3); A har gällt (yttre): 3 av 3 kvartal → 4 av 4 kvartal; S1 symmetrisk, yttre lagret: ränta: kan inte avgöras; capex − OCF: kan inte avgöras; nettoemission: kan inte avgöras; leasing: kan inte avgöras (2026Q2) → ränta: kan inte avgöras; capex − OCF: kan inte avgöras; nettoemission: kan inte avgöras; leasing: kan inte avgöras (2026Q3); S1 symmetrisk, inre lagret: ränta: kan inte avgöras; capex − OCF: talar emot, uppåt; nettoemission: talar emot, uppåt; leasing: talar emot, uppåt (2026Q2) → ränta: kan inte avgöras; capex − OCF: talar emot, uppåt; nettoemission: talar emot, uppåt; leasing: talar emot, uppåt (2026Q3); S1 symmetrisk, CoreWeave: ränta: kan inte avgöras; capex − OCF: talar för mekanismen, nedåt; nettoemission: talar för mekanismen, nedåt; leasing: talar emot, uppåt (2026Q2) → ränta: kan inte avgöras; capex − OCF: talar för mekanismen, nedåt; nettoemission: talar för mekanismen, nedåt; leasing: talar för mekanismen, nedåt (2026Q3); S1 symmetrisk, Nebius: capex − OCF: talar för mekanismen, nedåt (2026Q2) → capex − OCF: talar för mekanismen, nedåt (2026Q3); S1 symmetrisk, IREN: capex − OCF: kan inte avgöras (2026Q2) → capex − OCF: kan inte avgöras (2026Q3) | Oracle 2026Q4 omkring 2026-12-11, mot inre lagret; yttre lagret när alla fyra har lämnat in (senast uppskattat 2027-02-13) |
| **ledtid**: Rör sig order och orderstock hos leverantörerna (kraft, kylning, elnät, nät, servrar, datacenterleasing) före eller efter capex-takten hos hyperskalarna och de yttre lagren, och ändras ledtiden? | talar för (2026Q3) | kvartal: 2026Q2 → 2026Q3; L1 före K-inre, k = 4: talar för (2026Q2) → talar för (2026Q3); L1 efter K-inre, k = 2: inget av mönstren (2026Q2) → talar för (2026Q3); L2 före K-inre, k = 2: talar för (2026Q2) → talar för (2026Q3); L3 före K-inre, k = 2: inget av mönstren (2026Q2) → inget av mönstren (2026Q3); L3 efter K-inre, k = 2: inget av mönstren (2026Q2) → kan inte avgöras (2026Q3); O1 före K-inre, k = 2: talar för (2026Q2) → talar för (2026Q3); O1 efter K-inre, k = 2: inget av mönstren (2026Q2) → kan inte avgöras (2026Q3); O2 före K-inre, k = 2: talar för (2026Q2) → talar för (2026Q3); O2 efter K-inre, k = 2: inget av mönstren (2026Q2) → talar för (2026Q3); L1 före K-yttre, k = 2: kan inte avgöras (2026Q2) → kan inte avgöras (2026Q3); L1 efter K-yttre, k = 2: kan inte avgöras (2026Q2) → kan inte avgöras (2026Q3); Ledtid L1 före K-inre (k = 4), senaste / median tidigare: 1 / 3,0 kvartal → 1 / 2,0 kvartal; Förändring i takt, L1 Kraft och elnät: +16,5 (2026Q2) → +16,9 (2026Q3); Förändring i takt, K-inre: +6,2 (2026Q2) → +9,6 (2026Q3) | L2 efter K-inre med 2026Q3 omkring 2026-12-09; huvudläsningen (L1 före K-inre) när alla fyra i inre lagret har lämnat in 2026Q4, omkring 2027-01-31 |
| **prisvolym**: Följs prisfallet vid fast förmåga (G2) av högre användning (G3), och ändras sambandet? | kan inte avgöras (2026Q3) | inget ändrat | npm-kvartalet 2026Q4 när veckan 2026-12-28–2027-01-03 är känd, omkring 2027-01-05. Huvudläsningens X (GPQA-priset) får sin första förändring i takt för 2026Q4 omkring 2027-01-01, och huvudläsningen kan avgöras tidigast med npm-kvartalet 2027Q1, omkring 2027-03-30 |

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
- S1: orderstock elnät som förändring i takt mot capex inre lagret: talar emot, uppåt
- S1: samma rad, impulser upp/ned: 4/3 av 18 ursprung
- S1: samma rad, oberoende av LT1: nej: LT1:s huvudläsning med motsatt tecken

### kreditlagret

- Oracle mot inre lagret, utslag: talar för mekanismen (2026Q3)
- CoreWeave mot inre lagret, utslag: talar emot (1) (2026Q3)
- Nebius mot inre lagret, utslag: inget av mönstren (2026Q3)
- IREN mot inre lagret, utslag: kan inte avgöras (2026Q3)
- Yttre lagret, A: ja
- Förändring i capex-takt, yttre: –
- Förändring i capex-takt, inre: +9,6 (2026Q3)
- A har gällt (yttre): 4 av 4 kvartal
- Huvudläsningen på osedda data: nej
- S1 symmetrisk, yttre lagret: ränta: kan inte avgöras; capex − OCF: kan inte avgöras; nettoemission: kan inte avgöras; leasing: kan inte avgöras (2026Q3)
- S1 symmetrisk, inre lagret: ränta: kan inte avgöras; capex − OCF: talar emot, uppåt; nettoemission: talar emot, uppåt; leasing: talar emot, uppåt (2026Q3)
- S1 symmetrisk, Oracle: ränta: inget av mönstren; capex − OCF: talar för mekanismen, uppåt; nettoemission: talar för mekanismen, uppåt; leasing: talar för mekanismen, uppåt (2026Q3)
- S1 symmetrisk, CoreWeave: ränta: kan inte avgöras; capex − OCF: talar för mekanismen, nedåt; nettoemission: talar för mekanismen, nedåt; leasing: talar för mekanismen, nedåt (2026Q3)
- S1 symmetrisk, Nebius: capex − OCF: talar för mekanismen, nedåt (2026Q3)
- S1 symmetrisk, IREN: capex − OCF: kan inte avgöras (2026Q3)

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

### prisvolym

- Bisak a-G (Arena-pris mot SDK, geometriskt medel): inget av mönstren
- Bisak b-G (GPQA-pris mot SDK relativt kontroll, geometriskt medel): kan inte avgöras
- GPQA-pris (geometriskt medel), förändring i takt: – (2026Q3)
- SDK-nedladdningar (geometriskt medel), förändring i takt: +62,1 (2026Q3)
- Huvudläsningen, impulser upp/ned: 0/0 av 0 ursprung
- Huvudläsningen på osedda data: nej
- Låsta rader H / a / b (aritmetiskt medel): kan inte avgöras / inget av mönstren / kan inte avgöras
