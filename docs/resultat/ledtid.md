# Ledtid i stacken: följd fråga (LT1)

*Rättad efter granskningen R28 (rättningsspår X25, `docs/mattregister.md`, 2026-11-26 X25): förbehållet om sedda data avgörs nu per läsning, alla förvärv som träffar ett kvartal märks med riktning, och varje rad visar hur ofta Y var känt i hela fönstret. Inga utslag ändrades. Rapporterna nedan är genererade på nytt med kommandot.*

**Frågan:** Rör sig order och orderstock hos leverantörerna (kraft, kylning, elnät, nät, servrar, datacenterleasing)
före eller efter capex-takten hos hyperskalarna och de yttre lagren, och ändras ledtiden?

Följd fråga, inte en gren. Storheterna, läsregeln, gränserna och fönstren låstes i registret innan något mått räknades
(`docs/mattregister.md`, 2026-11-26 LT1, commit 6fb0ccd). Läsregeln är F0:s symmetriska mall. Källor, kodning och
förbehåll: `docs/kallor/ledtid.md`. Rapporten byggs med

    python -m ai_tracker.followed ledtid --as-of 2026-11-26 [--json PATH] [--out PATH]

Den använder bara rader som var kända på dagen. Nedan står rapporten per 2026-11-26 och per 2025-11-26 (ett år
tidigare). Rapporterna är genererade av kommandot och inte redigerade, bara rubriknivåerna är flyttade ett steg.

**Läsningarna är gjorda på sedda data.** Alla kvartal i båda läsningarna var kända när registerposten skrevs
2026-11-26, och enstaka värden var sedda före posten (posten, avsnitt (e)). Utslagen är därför inga utfall på osedda
data. Den första osedda läsningen kommer med Dells 10-Q för 2026Q3, omkring 2026-12-09 (raden "L2 efter K-inre").
Huvudläsningen får ett nytt kvartal när alla fyra i inre lagret har lämnat in 2026Q4, omkring 2027-01-31. Förbehållet avgörs per läsning (X25, punkt 1): när Dells kvartal kommer blir bara de rader som vilar på det osedda, och huvudläsningen behåller förbehållet tills dess egna värden ändras.

**O1 och O2 kommer ur S3:s extraktion ur pressmeddelanden**, som har `publish=False` i väntan på den oberoende
granskningen av extraktionen.

**Samma par som EL1.** L1 (`rpo_etn` + `rpo_pwr`) mot K-inre är exakt EL1:s huvudläsning (orderstock elnät mot capex i inre lagret). LT1 läser förändringen i takt med tecken +, EL1 takten med tecken −. Samma kvartal ger därför "talar för" här och "talar emot" i EL1. Det är två läsningar av samma rörelse och tillsammans inte mer än en observation (R28-4).

## Vad som skiljer de två dagarna (beskrivning, inget test)

- **Huvudläsningen** (L1 kraft och elnät före K-inre, *k* = 2) gav "inget av mönstren" per 2025-11-26 och "talar för
  mekanismen" per 2026-11-26. Per 2026-11-26 är ursprunget 2026Q2: förändringen i takt för L1:s orderstock var +16,5,
  och K-inres capex-takt följde med +9,6 vid 2026Q3. Per 2025-11-26 hade L1 ingen impuls i fönstret 2025Q1–2025Q2.
- **Båda riktningarna talar för per 2026-11-26.** L1 efter K-inre ger också "talar för" (capex-takten +6,2 vid
  2026Q2, L1 +16,9 vid 2026Q3). Det är den väntade bilden när leverantörer och köpare accelererar samtidigt. Regeln
  säger då inte vilken som kom först. Samma sak gäller O2 och, med *k* = 4, L2.
- **I historiken ser L1 snarare ut att följa.** I raden "före" talar alla tre nedgångarna i L1:s takt (2024Q1–2024Q3)
  emot: orderstockens takt föll medan köparnas capex-takt steg med 22–27. Med *k* = 4 talar raden "efter" för i 9 av
  21 ursprung med impuls: capex-takten föll 2023 och L1 följde 2024Q1, och capex-takten steg 2024 och L1 följde 2025Q3. Det är i
  praktiken två händelser, med ursprung i följd som räknas var för sig. Det kan vara slump, och L1:s uppgång 2025Q3
  ligger i ett kvartal som Eatons köp av Fibrebond kan ha påverkat (märkt i rapporten; storleken är inte kontrollerad).
- **Ledtiden.** För L1 före K-inre (*k* = 4) finns tre "talar för", alla per 2026-11-26 (ledtid 3, 1 och 1 kvartal).
  För L1 efter K-inre räknar ledtiderna ned i två följder (4, 3, 2, 1) och är 1 kvartal 2026Q2. Det är för få
  händelser för att säga att ledtiden har ändrats.
- **Övriga rader före K-inre.** L2 nät och servrar talar för båda dagarna (2025Q1 +11,0 och 2026Q2 +25,9). Eatons
  order (O1) och Digital Realtys nya avtal (O2) kunde inte avgöras per 2025-11-26, eftersom båda hade en nedgång
  2025Q2 (−12,9 och −42,8) och fönstret var öppet. Per 2026-11-26 talar båda för, efter uppgångar 2026Q2 (+19,5 och
  +34,2). Equinix (L3) ger "inget av mönstren" båda dagarna med *k* = 2.
- **Yttre lagret** kan inte avgöras någon av dagarna. Förändringen i takt för yttre lagrets capex finns först när
  serien har sju kvartal, alltså från 2026Q4 (inlämningarna i februari 2027).
- **Nivåerna.** L1:s takt gick från +22,3 till +54,6 log × 100 per år, L2:s från +10,5 till +72,0 (Dells RPO växer
  mest) och K-inres capex-takt från +50,5 till +62,4. Digital Realtys nya avtal är klumpiga: förändringen i takt var
  −98,6 per 2025Q3 och +94,5 per 2026Q3.
- **Förvärv i fönstret.** Huvudläsningens ursprung 2026Q2 träffas av två förvärv åt olika håll: Fibrebond (*a* + 4,
  flyttar L1:s förändring i takt nedåt) och Boyd Thermal (*a* + 1, flyttar den uppåt). Nettoriktningen är inte känd.
  Fibrebond kan bara ha dragit X nedåt, så det är Boyd Thermal som kan ha gett utslaget. Som beskrivning (X25, punkt 2):
  X vid 2026Q2 (+16,5) hamnar under gränsen 10 först om Boyd Thermal lade till mer än omkring 3,6 mdr USD till Eatons
  orderstock (cirka 6 % av L1 vid 2026Q2), och ursprunget 2026Q1 (X +15,4, *a* för Boyd Thermal) först vid mer än
  omkring 2,6 mdr. Eatons hela orderstock växte med 3,0 mdr 2026Q1, det kvartal köpet gjordes. Boyd Thermals
  orderstock finns inte i datan, så det går inte att utesluta, men det kräver att förvärvet står för det mesta av Eatons
  ökning. Quantas förvärv är inte kontrollerade (R28-7), och Quanta står för det mesta av L1:s rörelse.


## Ledtid i stacken per 2026-11-26

**Frågan:** Rör sig order och orderstock hos leverantörerna (kraft, kylning, elnät, nät, servrar, datacenterleasing) före eller efter capex-takten hos hyperskalarna och de yttre lagren, och ändras ledtiden?

Leverantörer: L1 kraft och elnät (orderstock och RPO, Eaton och Quanta), L2 nät och servrar (RPO, Cisco, Dell och Super Micro), L3 datacenter (Equinix RPO), O1 Eatons organiska order (Electrical Americas, tolv månader) och O2 Digital Realtys nya avtal över fyra kvartal. Köpare: capex över fyra kvartal i inre lagret (Microsoft, Alphabet, Amazon, Meta) och yttre lagret (Oracle, CoreWeave, Nebius, IREN). Takt = förändring över fyra kvartal i log × 100. Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1. Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-26 LT1.

**O1 och O2 kommer ur S3:s extraktion ur pressmeddelanden. Serierna har `publish=False` i väntan på granskningen av extraktionen.**

### 1. Läsregeln, mekaniskt

F0:s symmetriska regel. X och Y är förändring i takt. Gränser: köparnas capex ±5, leverantörernas orderstock och order ±10 (log × 100), samma gräns för en storhet som X (impuls) och som Y (följer). Fönster k = 2 och k = 4 kvartal, tecken +. "Före": X = leverantören, Y = köparen. "Efter": X = köparen, Y = leverantören. Utslaget gäller det senaste ursprunget med impuls bland t − k … t − 1, där t är Y:s senaste kvartal. Det är en beskrivning, inget test.

Före och efter är inte varandras motsats: två utjämnade serier som rör sig ihop kan ge "talar för" i båda riktningarna, och då säger regeln inte vilken som kom först.

- **Huvudläsning, L1 före K-inre, k = 2:** talar för mekanismen. t = 2026Q3; ursprung 2026Q2, X +16,5 (gräns ±10,0), uppgång, Y +9,6 vid 2026Q3 (gräns ±5,0). X = lt1_rpo_power (förändring i takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken +.
  Regeln kunde prövas i 18 av 18 ursprung med X (2022Q1–2026Q2). Impulser uppåt 4 (för 2, emot 1, inget 1, kan inte avgöras 0), nedåt 3 (för 0, emot 3, inget 0, kan inte avgöras 0), utan impuls 11.
  Y var känt i hela fönstret i 17 av 18 ursprung, och 7 av 7 impulser kunde läsas mot Y.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-26, och den är därför inget utfall på osedda data.

Alla läsningar i tabellen vilar bara på värden som var kända före registerposten 2026-11-26 (posten, avsnitt (e) och (f)), och ingen av dem är ett utfall på osedda data. Sedda data avgörs per läsning (X25, punkt 1).

| Leverantör | Köpare | Riktning | k | t | Utslag (ursprung, X, Y) | Prövad / ursprung med X; impulser (för/emot/inget/kan inte avgöras) |
|---|---|---|---|---|---|---|
| L1 Kraft och elnät (Eaton, Quanta) | K-inre | före | 2 | 2026Q3 | **talar för**: 2026Q2 X +16,5, Y +9,6 vid 2026Q3 (förvärv i fönstret: Eaton–Fibrebond a + 4, ned; Eaton–Boyd Thermal a + 1, upp) | 18 av 18 (2022Q1–2026Q2), Y i hela fönstret 17; upp 4 (2/1/1/0), ned 3 (0/3/0/0) |
| L1 Kraft och elnät (Eaton, Quanta) | K-inre | före | 4 | 2026Q3 | **talar för**: 2026Q2 X +16,5, Y +9,6 vid 2026Q3 (förvärv i fönstret: Eaton–Fibrebond a + 4, ned; Eaton–Boyd Thermal a + 1, upp) | 18 av 18 (2022Q1–2026Q2), Y i hela fönstret 15; upp 4 (3/1/0/0), ned 3 (0/3/0/0) |
| L1 Kraft och elnät (Eaton, Quanta) | K-inre | efter | 2 | 2026Q3 | **talar för**: 2026Q2 X +6,2, Y +16,9 vid 2026Q3 (förvärv i fönstret: Eaton–Fibrebond a + 5, ned) | 22 av 27 (2019Q4–2026Q2), Y i hela fönstret 18; upp 11 (3/2/2/4), ned 10 (2/1/6/1) |
| L1 Kraft och elnät (Eaton, Quanta) | K-inre | efter | 4 | 2026Q3 | **talar för**: 2026Q2 X +6,2, Y +16,9 vid 2026Q3 (förvärv i fönstret: Eaton–Fibrebond a + 5, ned) | 22 av 27 (2019Q4–2026Q2), Y i hela fönstret 16; upp 11 (5/2/0/4), ned 10 (4/1/4/1) |
| L2 Nät och servrar (Cisco, Dell, Super Micro) | K-inre | före | 2 | 2026Q3 | **talar för**: 2026Q2 X +25,9, Y +9,6 vid 2026Q3 | 26 av 26 (2020Q1–2026Q2), Y i hela fönstret 25; upp 4 (4/0/0/0), ned 4 (4/0/0/0) |
| L2 Nät och servrar (Cisco, Dell, Super Micro) | K-inre | före | 4 | 2026Q3 | **talar för**: 2026Q2 X +25,9, Y +9,6 vid 2026Q3 | 26 av 26 (2020Q1–2026Q2), Y i hela fönstret 23; upp 4 (4/0/0/0), ned 4 (4/0/0/0) |
| L2 Nät och servrar (Cisco, Dell, Super Micro) | K-inre | efter | 2 | 2026Q2 | **inget av mönstren** (ingen impuls i fönstret) | 26 av 26 (2019Q4–2026Q1), Y i hela fönstret 25; upp 10 (3/0/7/0), ned 10 (3/0/7/0) |
| L2 Nät och servrar (Cisco, Dell, Super Micro) | K-inre | efter | 4 | 2026Q2 | **talar för**: 2025Q2 X +5,9, Y +35,7 vid 2025Q4 | 26 av 26 (2019Q4–2026Q1), Y i hela fönstret 23; upp 10 (6/2/2/0), ned 10 (3/0/7/0) |
| L3 Datacenter (Equinix, RPO) | K-inre | före | 2 | 2026Q3 | **inget av mönstren** (ingen impuls i fönstret) | 28 av 28 (2019Q3–2026Q2), Y i hela fönstret 27; upp 2 (2/0/0/0), ned 2 (0/2/0/0) |
| L3 Datacenter (Equinix, RPO) | K-inre | före | 4 | 2026Q3 | **inget av mönstren** (ingen impuls i fönstret) | 28 av 28 (2019Q3–2026Q2), Y i hela fönstret 25; upp 2 (2/0/0/0), ned 2 (0/2/0/0) |
| L3 Datacenter (Equinix, RPO) | K-inre | efter | 2 | 2026Q3 | **kan inte avgöras**: 2026Q2 X +6,2 (fönstret öppet till 2026Q4) | 26 av 27 (2019Q4–2026Q2), Y i hela fönstret 26; upp 11 (4/0/6/1), ned 10 (1/0/9/0) |
| L3 Datacenter (Equinix, RPO) | K-inre | efter | 4 | 2026Q3 | **kan inte avgöras**: 2026Q2 X +6,2 (fönstret öppet till 2027Q2) | 26 av 27 (2019Q4–2026Q2), Y i hela fönstret 24; upp 11 (4/0/6/1), ned 10 (1/2/7/0) |
| O1 Eatons order (Electrical Americas, organisk, 12 mån) (S3) | K-inre | före | 2 | 2026Q3 | **talar för**: 2026Q2 X +19,5, Y +9,6 vid 2026Q3 | 17 av 17 (2022Q2–2026Q2), Y i hela fönstret 16; upp 6 (5/0/1/0), ned 6 (3/2/1/0) |
| O1 Eatons order (Electrical Americas, organisk, 12 mån) (S3) | K-inre | före | 4 | 2026Q3 | **talar för**: 2026Q2 X +19,5, Y +9,6 vid 2026Q3 | 17 av 17 (2022Q2–2026Q2), Y i hela fönstret 14; upp 6 (6/0/0/0), ned 6 (3/3/0/0) |
| O1 Eatons order (Electrical Americas, organisk, 12 mån) (S3) | K-inre | efter | 2 | 2026Q3 | **kan inte avgöras**: 2026Q2 X +6,2 (fönstret öppet till 2026Q4) | 20 av 27 (2019Q4–2026Q2), Y i hela fönstret 17; upp 11 (2/3/1/5), ned 10 (5/1/2/2) |
| O1 Eatons order (Electrical Americas, organisk, 12 mån) (S3) | K-inre | efter | 4 | 2026Q3 | **kan inte avgöras**: 2026Q2 X +6,2 (fönstret öppet till 2027Q2) | 20 av 27 (2019Q4–2026Q2), Y i hela fönstret 15; upp 11 (2/4/0/5), ned 10 (7/1/0/2) |
| O2 Digital Realtys nya avtal (fyra kvartal) (S3) | K-inre | före | 2 | 2026Q3 | **talar för**: 2026Q2 X +34,2, Y +9,6 vid 2026Q3 | 10 av 10 (2024Q1–2026Q2), Y i hela fönstret 9; upp 6 (6/0/0/0), ned 4 (0/2/2/0) |
| O2 Digital Realtys nya avtal (fyra kvartal) (S3) | K-inre | före | 4 | 2026Q3 | **talar för**: 2026Q2 X +34,2, Y +9,6 vid 2026Q3 | 10 av 10 (2024Q1–2026Q2), Y i hela fönstret 7; upp 6 (6/0/0/0), ned 4 (0/4/0/0) |
| O2 Digital Realtys nya avtal (fyra kvartal) (S3) | K-inre | efter | 2 | 2026Q3 | **talar för**: 2026Q2 X +6,2, Y +94,5 vid 2026Q3 | 14 av 27 (2019Q4–2026Q2), Y i hela fönstret 10; upp 11 (4/3/0/4), ned 10 (0/1/0/9) |
| O2 Digital Realtys nya avtal (fyra kvartal) (S3) | K-inre | efter | 4 | 2026Q3 | **talar för**: 2026Q2 X +6,2, Y +94,5 vid 2026Q3 | 14 av 27 (2019Q4–2026Q2), Y i hela fönstret 8; upp 11 (4/3/0/4), ned 10 (0/1/0/9) |
| L1 Kraft och elnät (Eaton, Quanta) | K-yttre | före | 2 | 2026Q3 | **kan inte avgöras**: 2026Q2 X +16,5 (förvärv i fönstret: Eaton–Fibrebond a + 4, ned; Eaton–Boyd Thermal a + 1, upp) (Y saknas vid 2026Q3) | 11 av 18 (2022Q1–2026Q2), Y i hela fönstret 0; upp 4 (0/0/0/4), ned 3 (0/0/0/3) |
| L1 Kraft och elnät (Eaton, Quanta) | K-yttre | före | 4 | 2026Q3 | **kan inte avgöras**: 2026Q2 X +16,5 (förvärv i fönstret: Eaton–Fibrebond a + 4, ned; Eaton–Boyd Thermal a + 1, upp) (Y saknas vid 2026Q3) | 11 av 18 (2022Q1–2026Q2), Y i hela fönstret 0; upp 4 (0/0/0/4), ned 3 (0/0/0/3) |
| L1 Kraft och elnät (Eaton, Quanta) | K-yttre | efter | 2 | 2026Q3 | **kan inte avgöras** (X saknas vid 2026Q1; X saknas vid 2026Q2) | X saknas |
| L1 Kraft och elnät (Eaton, Quanta) | K-yttre | efter | 4 | 2026Q3 | **kan inte avgöras** (X saknas vid 2025Q3; X saknas vid 2025Q4; X saknas vid 2026Q1; X saknas vid 2026Q2) | X saknas |

### 2. Ledtiden (beskrivning)

I läsningarna med k = 4: kvartal från ursprunget till kvartalet som avgjorde ett "talar för". Senaste ledtiden mot medianen av de tidigare i samma rad. Ingen gräns för "ändrad"; med få ursprung kan en skillnad vara slump. Ursprung i följd med impuls åt samma håll avgörs ofta av samma kvartal för Y, så ledtiderna räknar ned (4, 3, 2, 1). En sådan följd är en händelse och inte flera, och medianen väger den ändå flera gånger.

- L1 Kraft och elnät (Eaton, Quanta) före K-inre: senaste 1 kvartal (2026Q2), median av de 2 tidigare 2,0. Per ursprung: 2025Q3 3 (upp), 2026Q1 1 (upp), 2026Q2 1 (upp).
- L1 Kraft och elnät (Eaton, Quanta) efter K-inre: senaste 1 kvartal (2026Q2), median av de 8 tidigare 2,5. Per ursprung: 2023Q1 4 (ned), 2023Q2 3 (ned), 2023Q3 2 (ned), 2023Q4 1 (ned), 2024Q3 4 (upp), 2024Q4 3 (upp), 2025Q1 2 (upp), 2025Q2 1 (upp), 2026Q2 1 (upp).
- L2 Nät och servrar (Cisco, Dell, Super Micro) före K-inre: senaste 1 kvartal (2026Q2), median av de 7 tidigare 1,0. Per ursprung: 2021Q4 1 (ned), 2022Q1 1 (ned), 2022Q2 1 (ned), 2022Q3 1 (ned), 2025Q1 1 (upp), 2025Q4 2 (upp), 2026Q1 1 (upp), 2026Q2 1 (upp).
- L2 Nät och servrar (Cisco, Dell, Super Micro) efter K-inre: senaste 2 kvartal (2025Q2), median av de 8 tidigare 1,5. Per ursprung: 2021Q4 1 (ned), 2022Q1 1 (ned), 2022Q2 1 (ned), 2024Q1 4 (upp), 2024Q2 3 (upp), 2024Q3 2 (upp), 2024Q4 1 (upp), 2025Q1 3 (upp), 2025Q2 2 (upp).
- L3 Datacenter (Equinix, RPO) före K-inre: senaste 1 kvartal (2024Q3), median av de 1 tidigare 1,0. Per ursprung: 2020Q4 1 (upp), 2024Q3 1 (upp).
- L3 Datacenter (Equinix, RPO) efter K-inre: senaste 1 kvartal (2024Q2), median av de 4 tidigare 1,5. Per ursprung: 2019Q4 1 (ned), 2020Q2 2 (upp), 2020Q3 1 (upp), 2024Q1 2 (upp), 2024Q2 1 (upp).
- O1 Eatons order (Electrical Americas, organisk, 12 mån) före K-inre: senaste 1 kvartal (2026Q2), median av de 8 tidigare 1,0. Per ursprung: 2023Q1 1 (ned), 2023Q2 1 (ned), 2023Q3 1 (ned), 2024Q1 1 (upp), 2024Q2 1 (upp), 2025Q3 3 (upp), 2025Q4 2 (upp), 2026Q1 1 (upp), 2026Q2 1 (upp).
- O1 Eatons order (Electrical Americas, organisk, 12 mån) efter K-inre: senaste 1 kvartal (2025Q2), median av de 8 tidigare 1,0. Per ursprung: 2022Q1 4 (ned), 2022Q2 3 (ned), 2022Q3 2 (ned), 2022Q4 1 (ned), 2023Q1 1 (ned), 2023Q2 1 (ned), 2023Q3 1 (ned), 2024Q1 1 (upp), 2025Q2 1 (upp).
- O2 Digital Realtys nya avtal (fyra kvartal) före K-inre: senaste 1 kvartal (2026Q2), median av de 5 tidigare 1,0. Per ursprung: 2024Q1 1 (upp), 2024Q2 1 (upp), 2024Q3 1 (upp), 2024Q4 1 (upp), 2026Q1 1 (upp), 2026Q2 1 (upp).
- O2 Digital Realtys nya avtal (fyra kvartal) efter K-inre: senaste 1 kvartal (2026Q2), median av de 3 tidigare 1,0. Per ursprung: 2024Q1 1 (upp), 2024Q2 1 (upp), 2024Q3 1 (upp), 2026Q2 1 (upp).
- L1 Kraft och elnät (Eaton, Quanta) före K-yttre: inget "talar för" i historiken.
- L1 Kraft och elnät (Eaton, Quanta) efter K-yttre: inget "talar för" i historiken.

### 3. Måtten

**Storheterna i läsregeln:**

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| L1 Kraft och elnät | 68,0 mdr | +54,6 | +16,9 | +5,1 | 2026Q3 | 2026-11-03 | `lt1_rpo_power` |
| L2 Nät och servrar | 181,3 mdr | +72,0 | +25,9 | +12,9 | 2026Q2 | 2026-09-08 | `lt1_rpo_net` |
| Equinix | 15,9 mdr | +22,5 | -0,4 | +0,7 | 2026Q3 | 2026-10-28 | `rpo_eqix` |
| O1 Eaton, order (Electrical Americas, organisk, 12 mån) | 39,0 % | +32,9 | -2,1 | – | 2026Q3 | 2026-11-03 | `ob_etn_orders_electrical_americas_ttm_yoy_pct_organic_pct` |
| O2 Digital Realty, nya avtal (fyra kvartal) | 1 432,6 MUSD per år | +80,7 | +94,5 | +40,0 | 2026Q3 | 2026-10-29 | `lt1_dlr_bookings4` |
| K-inre | 615,4 mdr | +62,4 | +9,6 | +4,6 | 2026Q3 | 2026-10-30 | `kl_capex4_inner` |
| K-yttre | 125,7 mdr | +113,9 | – | +7,1 | 2026Q3 | 2026-11-12 | `kl_capex4_outer` |

O1 är en tillväxttakt: takten är 100 × ln(1 + v/100), och överraskning mot B1 är inte registrerad för den. RPO och orderstock är balanser; förändringen är order minus leveranser, plus valuta och förvärv.

Aggregat som väntar på en medlem: `lt1_rpo_net` saknar rpo_dell (2026Q3).

**Medlemmarna i L1 och L2, och leverantörer utanför aggregaten** (sammanhang, ingår inte i läsregeln):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Eaton | 26,2 mdr | +35,3 | -0,1 | +0,4 | 2026Q3 | 2026-11-03 | `rpo_etn` |
| Quanta Services | 41,8 mdr | +68,9 | +29,2 | +7,9 | 2026Q3 | 2026-10-29 | `rpo_pwr` |
| GE Vernova | 196,7 mdr | +37,5 | +9,5 | +3,1 | 2026Q3 | 2026-10-28 | `rpo_gev` |
| Cisco | 46,2 mdr | +7,4 | +3,2 | -3,0 | 2026Q3 | 2026-11-17 | `rpo_csco` |
| Dell | 132,0 mdr | +109,9 | +32,9 | +13,7 | 2026Q2 | 2026-09-08 | `rpo_dell` |
| Super Micro | 5,7 mdr | +170,7 | +54,1 | +45,6 | 2026Q3 | 2026-11-06 | `rpo_smci` |
| Arista | 8,6 mdr | +48,4 | -24,9 | -12,2 | 2026Q3 | 2026-11-04 | `rpo_anet` |
| HPE | 10,9 mdr | +7,6 | -27,0 | -7,2 | 2026Q2 | 2026-09-03 | `rpo_hpe` |

**Order och orderstock ur pressmeddelandena (S3, publish=False i väntan på granskningen)** (sammanhang, ingår inte i läsregeln):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| GE Vernova, order (kvartal) | 29,3 mdr | +69,7 | +11,2 | +2,4 | 2026Q3 | 2026-10-28 | `ob_gev_orders_total_q_level_musd` |
| GE Vernova, orderstock | 197,0 mdr | – | – | – | 2026Q3 | 2026-10-28 | `ob_gev_backlog_total_end_level_musd` |
| Dell, AI-order (kvartal) | 60,2 mdr | +158,8 | +88,7 | – | 2026Q3 | 2026-11-24 | `ob_dell_orders_ai_servers_q_level_musd` |
| Dell, AI-orderstock | 132,3 mdr | +197,3 | – | – | 2026Q3 | 2026-11-24 | `ob_dell_backlog_ai_servers_end_level_musd` |
| Digital Realty, nya avtal (kvartal) | 626,6 MUSD per år | +135,4 | +79,7 | +99,2 | 2026Q3 | 2026-10-29 | `ob_dlr_leases_signed_total_dlr_share_q_level_musd` |

**Leverantörernas intäkter (leveranser)** (sammanhang, ingår inte i läsregeln):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Eaton | 8,9 mdr | +24,7 | +9,1 | -0,1 | 2026Q3 | 2026-11-03 | `rev_etn` |
| Quanta Services | 12,0 mdr | +45,4 | +22,0 | +14,3 | 2026Q3 | 2026-10-29 | `rev_pwr` |
| GE Vernova | 12,6 mdr | +23,8 | +8,7 | +8,0 | 2026Q3 | 2026-10-28 | `rev_gev` |
| Vertiv | 4,3 mdr | +47,7 | +21,4 | +22,1 | 2026Q3 | 2026-10-28 | `rev_vrt` |
| Cisco | 18,5 mdr | +21,8 | +10,6 | +3,0 | 2026Q3 | 2026-11-17 | `rev_csco` |
| Dell | 47,0 mdr | +45,6 | +12,3 | -8,8 | 2026Q2 | 2026-09-08 | `rev_dell` |
| Super Micro | 19,9 mdr | +138,0 | +57,9 | +42,0 | 2026Q3 | 2026-11-06 | `rev_smci` |
| Arista | 3,7 mdr | +46,0 | +15,9 | +10,6 | 2026Q3 | 2026-11-04 | `rev_anet` |
| Equinix | 2,6 mdr | +10,4 | +1,1 | -5,9 | 2026Q3 | 2026-10-28 | `rev_eqix` |
| Digital Realty | 1,9 mdr | +18,7 | +3,8 | -7,5 | 2026Q3 | 2026-10-30 | `rev_dlr` |

**Capex över fyra kvartal per köpare** (sammanhang, ingår inte i läsregeln):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Microsoft | 135,9 mdr | +67,8 | +21,7 | +1,3 | 2026Q3 | 2026-10-28 | `kl_capex4_msft` |
| Alphabet | 159,8 mdr | +71,9 | +7,5 | +1,8 | 2026Q3 | 2026-10-29 | `kl_capex4_googl` |
| Amazon | 215,2 mdr | +58,3 | +9,9 | +9,9 | 2026Q3 | 2026-10-30 | `kl_capex4_amzn` |
| Meta | 104,4 mdr | +51,0 | -3,8 | +2,2 | 2026Q3 | 2026-10-22 | `kl_capex4_meta` |
| Oracle | 75,7 mdr | +101,5 | -15,8 | +6,6 | 2026Q3 | 2026-09-11 | `kl_capex4_orcl` |
| CoreWeave | 27,6 mdr | +104,2 | +35,7 | +7,6 | 2026Q3 | 2026-11-12 | `kl_capex4_crwv` |
| Nebius | 17,5 mdr | +197,5 | +44,0 | -2,8 | 2026Q3 | 2026-11-12 | `kl_capex4_nbis` |
| IREN | 4,9 mdr | +203,3 | – | +8,8 | 2026Q3 | 2026-11-05 | `kl_capex4_iren` |

**Köparnas capex-guidance för kalenderåret** (förväntad capex; mittpunkt, guidad takt mot föregående års utfall där F1:s definition finns; ingår inte i läsregeln):

- Microsoft 2026: 170,0 mdr–170,0 mdr; known_from 2026-10-28
- Alphabet 2026: 180,0 mdr–190,0 mdr, guidad takt +70,5; known_from 2026-06-04
- Amazon 2026: 220,0 mdr–220,0 mdr; known_from 2026-10-29
- Meta 2026: 135,0 mdr–145,0 mdr, guidad takt +66,2; known_from 2026-10-21

### 4. Att bevaka

Nästa kvartal per storhet, när alla dess medlemmar har lämnat in (uppskattat ur de åtta senaste inlämningarna per bolag):

- K-inre (Microsoft, Alphabet, Amazon, Meta): 2026Q4 omkring 2027-01-31
- K-yttre (Oracle, CoreWeave, Nebius, IREN): 2026Q4 omkring 2027-02-13
- L1 Kraft och elnät (Eaton, Quanta): 2026Q4 omkring 2027-02-04
- L2 Nät och servrar (Cisco, Dell, Super Micro): 2026Q3 omkring 2026-12-09
- L3 Datacenter (Equinix, RPO): 2026Q4 omkring 2027-01-29
- O1 Eatons order (Electrical Americas, organisk, 12 mån): 2026Q4 omkring 2027-02-04
- O2 Digital Realtys nya avtal (fyra kvartal): 2026Q4 omkring 2027-01-24

Nästa osedda läsning: L2 efter K-inre med 2026Q3 omkring 2026-12-09; huvudläsningen (L1 före K-inre) när alla fyra i inre lagret har lämnat in 2026Q4, omkring 2027-01-31.

### 5. Förbehåll

- Med 10–27 ursprung per rad, och färre med impuls, är detta en beskrivning och inget test. Ett mönster kan vara slump, och ett utfall som talar för mekanismen visar inte orsaken.
- RPO och orderstock är inte orderingång. Ciscos och Dells RPO har stora tjänstedelar. Ciscos och Dells balanser har räkenskapskvartalets kalenderkvartal, upp till en månad efter kalenderkvartalets slut.
- Leverantörerna säljer också till andra än AI-köparna: Quanta och Eaton till elbolag och industri, Cisco och Dell till företag. Ett utslag säger inget om hur stor del som gäller AI.
- Förvärv ger nivåskiften. Belagda förvärv märks i tabellen (Cisco–Splunk 2024Q1, Eaton–Fibrebond 2025Q2, Eaton–Boyd Thermal 2026Q1) med förskjutning och riktning: vid a och a + 1 flyttas förändringen i takt uppåt, vid a + 4 och a + 5 nedåt. Träffar två förvärv samma kvartal åt olika håll är nettoriktningen inte känd. Förvärv hos Quanta, Dell, Super Micro och Equinix är inte kontrollerade.
- O1 och O2 är S3:s extraktion (publish=False i väntan på granskningen). Digital Realtys andel är obelagd 2021Q4–2024Q1 (S3, tolkning 9).
- Vertiv är BLOCKED (inget RPO i XBRL, och S3:s orderserier slutar 2025Q4). GE Vernovas RPO och order är för korta för läsregeln och visas som sammanhang. Yttre lagrets förändring i capex-takt finns först när serien har sju kvartal (från 2026Q4).
- Historiken räknas på läsdagens vintage, så revideringar kan ändra äldre utfall (F0).

## Ledtid i stacken per 2025-11-26

**Frågan:** Rör sig order och orderstock hos leverantörerna (kraft, kylning, elnät, nät, servrar, datacenterleasing) före eller efter capex-takten hos hyperskalarna och de yttre lagren, och ändras ledtiden?

Leverantörer: L1 kraft och elnät (orderstock och RPO, Eaton och Quanta), L2 nät och servrar (RPO, Cisco, Dell och Super Micro), L3 datacenter (Equinix RPO), O1 Eatons organiska order (Electrical Americas, tolv månader) och O2 Digital Realtys nya avtal över fyra kvartal. Köpare: capex över fyra kvartal i inre lagret (Microsoft, Alphabet, Amazon, Meta) och yttre lagret (Oracle, CoreWeave, Nebius, IREN). Takt = förändring över fyra kvartal i log × 100. Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1. Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-26 LT1.

**O1 och O2 kommer ur S3:s extraktion ur pressmeddelanden. Serierna har `publish=False` i väntan på granskningen av extraktionen.**

### 1. Läsregeln, mekaniskt

F0:s symmetriska regel. X och Y är förändring i takt. Gränser: köparnas capex ±5, leverantörernas orderstock och order ±10 (log × 100), samma gräns för en storhet som X (impuls) och som Y (följer). Fönster k = 2 och k = 4 kvartal, tecken +. "Före": X = leverantören, Y = köparen. "Efter": X = köparen, Y = leverantören. Utslaget gäller det senaste ursprunget med impuls bland t − k … t − 1, där t är Y:s senaste kvartal. Det är en beskrivning, inget test.

Före och efter är inte varandras motsats: två utjämnade serier som rör sig ihop kan ge "talar för" i båda riktningarna, och då säger regeln inte vilken som kom först.

- **Huvudläsning, L1 före K-inre, k = 2:** inget av mönstren. t = 2025Q3 (ingen impuls i fönstret). X = lt1_rpo_power (förändring i takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken +.
  Regeln kunde prövas i 14 av 14 ursprung med X (2022Q1–2025Q2). Impulser uppåt 1 (för 0, emot 1, inget 0, kan inte avgöras 0), nedåt 3 (för 0, emot 3, inget 0, kan inte avgöras 0), utan impuls 10.
  Y var känt i hela fönstret i 13 av 14 ursprung, och 4 av 4 impulser kunde läsas mot Y.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-26, och den är därför inget utfall på osedda data.

Alla läsningar i tabellen vilar bara på värden som var kända före registerposten 2026-11-26 (posten, avsnitt (e) och (f)), och ingen av dem är ett utfall på osedda data. Sedda data avgörs per läsning (X25, punkt 1).

| Leverantör | Köpare | Riktning | k | t | Utslag (ursprung, X, Y) | Prövad / ursprung med X; impulser (för/emot/inget/kan inte avgöras) |
|---|---|---|---|---|---|---|
| L1 Kraft och elnät (Eaton, Quanta) | K-inre | före | 2 | 2025Q3 | **inget av mönstren** (ingen impuls i fönstret) | 14 av 14 (2022Q1–2025Q2), Y i hela fönstret 13; upp 1 (0/1/0/0), ned 3 (0/3/0/0) |
| L1 Kraft och elnät (Eaton, Quanta) | K-inre | före | 4 | 2025Q3 | **talar emot**: 2024Q3 X -10,6, Y +24,7 vid 2024Q4 | 14 av 14 (2022Q1–2025Q2), Y i hela fönstret 11; upp 1 (0/1/0/0), ned 3 (0/3/0/0) |
| L1 Kraft och elnät (Eaton, Quanta) | K-inre | efter | 2 | 2025Q3 | **talar för**: 2025Q2 X +5,9, Y +10,4 vid 2025Q3 (förvärv i fönstret: Eaton–Fibrebond a + 1, upp) | 18 av 23 (2019Q4–2025Q2), Y i hela fönstret 14; upp 10 (2/2/2/4), ned 10 (2/1/6/1) |
| L1 Kraft och elnät (Eaton, Quanta) | K-inre | efter | 4 | 2025Q3 | **talar för**: 2025Q2 X +5,9, Y +10,4 vid 2025Q3 (förvärv i fönstret: Eaton–Fibrebond a + 1, upp) | 18 av 23 (2019Q4–2025Q2), Y i hela fönstret 12; upp 10 (4/2/0/4), ned 10 (4/1/4/1) |
| L2 Nät och servrar (Cisco, Dell, Super Micro) | K-inre | före | 2 | 2025Q3 | **talar för**: 2025Q1 X +11,0, Y +5,9 vid 2025Q2 (förvärv i fönstret: Cisco–Splunk a + 4, ned) | 22 av 22 (2020Q1–2025Q2), Y i hela fönstret 21; upp 1 (1/0/0/0), ned 4 (4/0/0/0) |
| L2 Nät och servrar (Cisco, Dell, Super Micro) | K-inre | före | 4 | 2025Q3 | **talar för**: 2025Q1 X +11,0, Y +5,9 vid 2025Q2 (förvärv i fönstret: Cisco–Splunk a + 4, ned) | 22 av 22 (2020Q1–2025Q2), Y i hela fönstret 19; upp 1 (1/0/0/0), ned 4 (4/0/0/0) |
| L2 Nät och servrar (Cisco, Dell, Super Micro) | K-inre | efter | 2 | 2025Q2 | **kan inte avgöras**: 2025Q1 X +16,0 (fönstret öppet till 2025Q3) | 21 av 22 (2019Q4–2025Q1), Y i hela fönstret 21; upp 9 (2/0/6/1), ned 10 (3/0/7/0) |
| L2 Nät och servrar (Cisco, Dell, Super Micro) | K-inre | efter | 4 | 2025Q2 | **kan inte avgöras**: 2025Q1 X +16,0 (fönstret öppet till 2026Q1) | 21 av 22 (2019Q4–2025Q1), Y i hela fönstret 19; upp 9 (4/2/2/1), ned 10 (3/0/7/0) |
| L3 Datacenter (Equinix, RPO) | K-inre | före | 2 | 2025Q3 | **inget av mönstren** (ingen impuls i fönstret) | 24 av 24 (2019Q3–2025Q2), Y i hela fönstret 23; upp 2 (2/0/0/0), ned 2 (0/2/0/0) |
| L3 Datacenter (Equinix, RPO) | K-inre | före | 4 | 2025Q3 | **talar för**: 2024Q3 X +11,5, Y +24,7 vid 2024Q4 | 24 av 24 (2019Q3–2025Q2), Y i hela fönstret 21; upp 2 (2/0/0/0), ned 2 (0/2/0/0) |
| L3 Datacenter (Equinix, RPO) | K-inre | efter | 2 | 2025Q3 | **kan inte avgöras**: 2025Q2 X +5,9 (fönstret öppet till 2025Q4) | 22 av 23 (2019Q4–2025Q2), Y i hela fönstret 22; upp 10 (4/0/5/1), ned 10 (1/0/9/0) |
| L3 Datacenter (Equinix, RPO) | K-inre | efter | 4 | 2025Q3 | **kan inte avgöras**: 2025Q2 X +5,9 (fönstret öppet till 2026Q2) | 20 av 23 (2019Q4–2025Q2), Y i hela fönstret 20; upp 10 (4/0/3/3), ned 10 (1/2/7/0) |
| O1 Eatons order (Electrical Americas, organisk, 12 mån) (S3) | K-inre | före | 2 | 2025Q3 | **kan inte avgöras**: 2025Q2 X -12,9 (fönstret öppet till 2025Q4) | 12 av 13 (2022Q2–2025Q2), Y i hela fönstret 12; upp 2 (2/0/0/0), ned 6 (3/2/0/1) |
| O1 Eatons order (Electrical Americas, organisk, 12 mån) (S3) | K-inre | före | 4 | 2025Q3 | **kan inte avgöras**: 2025Q2 X -12,9 (fönstret öppet till 2026Q2) | 12 av 13 (2022Q2–2025Q2), Y i hela fönstret 10; upp 2 (2/0/0/0), ned 6 (3/2/0/1) |
| O1 Eatons order (Electrical Americas, organisk, 12 mån) (S3) | K-inre | efter | 2 | 2025Q3 | **talar för**: 2025Q2 X +5,9, Y +10,8 vid 2025Q3 | 17 av 23 (2019Q4–2025Q2), Y i hela fönstret 13; upp 10 (2/3/1/4), ned 10 (5/1/2/2) |
| O1 Eatons order (Electrical Americas, organisk, 12 mån) (S3) | K-inre | efter | 4 | 2025Q3 | **talar för**: 2025Q2 X +5,9, Y +10,8 vid 2025Q3 | 17 av 23 (2019Q4–2025Q2), Y i hela fönstret 11; upp 10 (2/4/0/4), ned 10 (7/1/0/2) |
| O2 Digital Realtys nya avtal (fyra kvartal) (S3) | K-inre | före | 2 | 2025Q3 | **kan inte avgöras**: 2025Q2 X -42,8 (fönstret öppet till 2025Q4) | 5 av 6 (2024Q1–2025Q2), Y i hela fönstret 5; upp 4 (4/0/0/0), ned 2 (0/1/0/1) |
| O2 Digital Realtys nya avtal (fyra kvartal) (S3) | K-inre | före | 4 | 2025Q3 | **kan inte avgöras**: 2025Q2 X -42,8 (fönstret öppet till 2026Q2) | 5 av 6 (2024Q1–2025Q2), Y i hela fönstret 3; upp 4 (4/0/0/0), ned 2 (0/1/0/1) |
| O2 Digital Realtys nya avtal (fyra kvartal) (S3) | K-inre | efter | 2 | 2025Q3 | **talar emot**: 2025Q2 X +5,9, Y -98,6 vid 2025Q3 | 10 av 23 (2019Q4–2025Q2), Y i hela fönstret 6; upp 10 (3/3/0/4), ned 10 (0/1/0/9) |
| O2 Digital Realtys nya avtal (fyra kvartal) (S3) | K-inre | efter | 4 | 2025Q3 | **talar emot**: 2025Q2 X +5,9, Y -98,6 vid 2025Q3 | 10 av 23 (2019Q4–2025Q2), Y i hela fönstret 4; upp 10 (3/3/0/4), ned 10 (0/1/0/9) |
| L1 Kraft och elnät (Eaton, Quanta) | K-yttre | före | 2 | – | **kan inte avgöras** (kl_capex4_outer: inget kvartal känt på dagen) | X saknas |
| L1 Kraft och elnät (Eaton, Quanta) | K-yttre | före | 4 | – | **kan inte avgöras** (kl_capex4_outer: inget kvartal känt på dagen) | X saknas |
| L1 Kraft och elnät (Eaton, Quanta) | K-yttre | efter | 2 | 2025Q3 | **kan inte avgöras** (X saknas vid 2025Q1; X saknas vid 2025Q2) | X saknas |
| L1 Kraft och elnät (Eaton, Quanta) | K-yttre | efter | 4 | 2025Q3 | **kan inte avgöras** (X saknas vid 2024Q3; X saknas vid 2024Q4; X saknas vid 2025Q1; X saknas vid 2025Q2) | X saknas |

### 2. Ledtiden (beskrivning)

I läsningarna med k = 4: kvartal från ursprunget till kvartalet som avgjorde ett "talar för". Senaste ledtiden mot medianen av de tidigare i samma rad. Ingen gräns för "ändrad"; med få ursprung kan en skillnad vara slump. Ursprung i följd med impuls åt samma håll avgörs ofta av samma kvartal för Y, så ledtiderna räknar ned (4, 3, 2, 1). En sådan följd är en händelse och inte flera, och medianen väger den ändå flera gånger.

- L1 Kraft och elnät (Eaton, Quanta) före K-inre: inget "talar för" i historiken.
- L1 Kraft och elnät (Eaton, Quanta) efter K-inre: senaste 1 kvartal (2025Q2), median av de 7 tidigare 3,0. Per ursprung: 2023Q1 4 (ned), 2023Q2 3 (ned), 2023Q3 2 (ned), 2023Q4 1 (ned), 2024Q3 4 (upp), 2024Q4 3 (upp), 2025Q1 2 (upp), 2025Q2 1 (upp).
- L2 Nät och servrar (Cisco, Dell, Super Micro) före K-inre: senaste 1 kvartal (2025Q1), median av de 4 tidigare 1,0. Per ursprung: 2021Q4 1 (ned), 2022Q1 1 (ned), 2022Q2 1 (ned), 2022Q3 1 (ned), 2025Q1 1 (upp).
- L2 Nät och servrar (Cisco, Dell, Super Micro) efter K-inre: senaste 1 kvartal (2024Q4), median av de 6 tidigare 1,5. Per ursprung: 2021Q4 1 (ned), 2022Q1 1 (ned), 2022Q2 1 (ned), 2024Q1 4 (upp), 2024Q2 3 (upp), 2024Q3 2 (upp), 2024Q4 1 (upp).
- L3 Datacenter (Equinix, RPO) före K-inre: senaste 1 kvartal (2024Q3), median av de 1 tidigare 1,0. Per ursprung: 2020Q4 1 (upp), 2024Q3 1 (upp).
- L3 Datacenter (Equinix, RPO) efter K-inre: senaste 1 kvartal (2024Q2), median av de 4 tidigare 1,5. Per ursprung: 2019Q4 1 (ned), 2020Q2 2 (upp), 2020Q3 1 (upp), 2024Q1 2 (upp), 2024Q2 1 (upp).
- O1 Eatons order (Electrical Americas, organisk, 12 mån) före K-inre: senaste 1 kvartal (2024Q2), median av de 4 tidigare 1,0. Per ursprung: 2023Q1 1 (ned), 2023Q2 1 (ned), 2023Q3 1 (ned), 2024Q1 1 (upp), 2024Q2 1 (upp).
- O1 Eatons order (Electrical Americas, organisk, 12 mån) efter K-inre: senaste 1 kvartal (2025Q2), median av de 8 tidigare 1,0. Per ursprung: 2022Q1 4 (ned), 2022Q2 3 (ned), 2022Q3 2 (ned), 2022Q4 1 (ned), 2023Q1 1 (ned), 2023Q2 1 (ned), 2023Q3 1 (ned), 2024Q1 1 (upp), 2025Q2 1 (upp).
- O2 Digital Realtys nya avtal (fyra kvartal) före K-inre: senaste 1 kvartal (2024Q4), median av de 3 tidigare 1,0. Per ursprung: 2024Q1 1 (upp), 2024Q2 1 (upp), 2024Q3 1 (upp), 2024Q4 1 (upp).
- O2 Digital Realtys nya avtal (fyra kvartal) efter K-inre: senaste 1 kvartal (2024Q3), median av de 2 tidigare 1,0. Per ursprung: 2024Q1 1 (upp), 2024Q2 1 (upp), 2024Q3 1 (upp).
- L1 Kraft och elnät (Eaton, Quanta) före K-yttre: inget "talar för" i historiken.
- L1 Kraft och elnät (Eaton, Quanta) efter K-yttre: inget "talar för" i historiken.

### 3. Måtten

**Storheterna i läsregeln:**

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| L1 Kraft och elnät | 39,4 mdr | +22,3 | +10,4 | +1,8 | 2025Q3 | 2025-11-04 | `lt1_rpo_power` |
| L2 Nät och servrar | 88,3 mdr | +10,5 | +5,6 | -7,3 | 2025Q2 | 2025-09-08 | `lt1_rpo_net` |
| Equinix | 12,7 mdr | +13,5 | +1,2 | +0,0 | 2025Q3 | 2025-10-29 | `rpo_eqix` |
| O1 Eaton, order (Electrical Americas, organisk, 12 mån) | 7,0 % | +6,8 | +10,8 | – | 2025Q3 | 2025-11-04 | `ob_etn_orders_electrical_americas_ttm_yoy_pct_organic_pct` |
| O2 Digital Realty, nya avtal (fyra kvartal) | 638,9 MUSD per år | -49,4 | -98,6 | -54,2 | 2025Q3 | 2025-10-23 | `lt1_dlr_bookings4` |
| K-inre | 329,8 mdr | +50,5 | +2,0 | -0,1 | 2025Q3 | 2025-10-31 | `kl_capex4_inner` |
| K-yttre | – | – | – | – | – | – | `kl_capex4_outer` |

O1 är en tillväxttakt: takten är 100 × ln(1 + v/100), och överraskning mot B1 är inte registrerad för den. RPO och orderstock är balanser; förändringen är order minus leveranser, plus valuta och förvärv.

Aggregat som väntar på en medlem: `lt1_rpo_net` saknar rpo_dell (2025Q3); `kl_capex4_outer` saknar capex_crwv (2024Q4), capex_nbis (2024Q4), capex_iren (2025Q2), capex_iren (2025Q1), capex_iren (2024Q4); `kl_capex4_crwv` saknar capex_crwv (2024Q4); `kl_capex4_nbis` saknar capex_nbis (2024Q4); `kl_capex4_iren` saknar capex_iren (2025Q2), capex_iren (2025Q1), capex_iren (2024Q4).

**Medlemmarna i L1 och L2, och leverantörer utanför aggregaten** (sammanhang, ingår inte i läsregeln):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Eaton | 18,4 mdr | +14,6 | +8,1 | +1,5 | 2025Q3 | 2025-11-04 | `rpo_etn` |
| Quanta Services | 21,0 mdr | +29,5 | +12,4 | +1,8 | 2025Q3 | 2025-10-30 | `rpo_pwr` |
| GE Vernova | 135,3 mdr | +13,9 | +7,9 | +2,3 | 2025Q3 | 2025-10-22 | `rpo_gev` |
| Cisco | 42,9 mdr | +7,0 | -0,2 | -3,0 | 2025Q3 | 2025-11-18 | `rpo_csco` |
| Dell | 44,0 mdr | +14,7 | +19,8 | -16,5 | 2025Q2 | 2025-09-08 | `rpo_dell` |
| Super Micro | 1,0 mdr | +61,1 | +18,8 | +20,0 | 2025Q3 | 2025-11-07 | `rpo_smci` |
| Arista | 5,3 mdr | +47,4 | +12,1 | +0,8 | 2025Q3 | 2025-11-05 | `rpo_anet` |
| HPE | 10,1 mdr | +32,5 | – | – | 2025Q2 | 2025-09-04 | `rpo_hpe` |

**Order och orderstock ur pressmeddelandena (S3, publish=False i väntan på granskningen)** (sammanhang, ingår inte i läsregeln):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| GE Vernova, order (kvartal) | 14,6 mdr | +44,0 | +39,0 | +15,1 | 2025Q3 | 2025-10-22 | `ob_gev_orders_total_q_level_musd` |
| GE Vernova, orderstock | – | – | – | – | – | – | `ob_gev_backlog_total_end_level_musd` |
| Dell, AI-order (kvartal) | 12,3 mdr | +122,9 | -30,9 | – | 2025Q3 | 2025-11-25 | `ob_dell_orders_ai_servers_q_level_musd` |
| Dell, AI-orderstock | 18,4 mdr | – | – | – | 2025Q3 | 2025-11-25 | `ob_dell_backlog_ai_servers_end_level_musd` |
| Digital Realty, nya avtal (kvartal) | 161,8 MUSD per år | -116,9 | -112,9 | +22,7 | 2025Q3 | 2025-10-23 | `ob_dlr_leases_signed_total_dlr_share_q_level_musd` |

**Leverantörernas intäkter (leveranser)** (sammanhang, ingår inte i läsregeln):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Eaton | 7,0 mdr | +9,7 | +2,6 | -3,1 | 2025Q3 | 2025-11-04 | `rev_etn` |
| Quanta Services | 7,6 mdr | +16,2 | -5,3 | +7,2 | 2025Q3 | 2025-10-30 | `rev_pwr` |
| GE Vernova | 10,0 mdr | +11,2 | +1,1 | +6,4 | 2025Q3 | 2025-10-22 | `rev_gev` |
| Vertiv | 2,7 mdr | +25,5 | +3,8 | -6,1 | 2025Q3 | 2025-10-22 | `rev_vrt` |
| Cisco | 14,9 mdr | +7,3 | -3,5 | -0,4 | 2025Q3 | 2025-11-18 | `rev_csco` |
| Dell | 29,8 mdr | +17,4 | +10,4 | +22,9 | 2025Q2 | 2025-09-08 | `rev_dell` |
| Super Micro | 5,0 mdr | -16,8 | -34,6 | -15,6 | 2025Q3 | 2025-11-07 | `rev_smci` |
| Arista | 2,3 mdr | +24,3 | -0,1 | -2,1 | 2025Q3 | 2025-11-05 | `rev_anet` |
| Equinix | 2,3 mdr | +5,1 | +0,6 | +1,5 | 2025Q3 | 2025-10-29 | `rev_eqix` |
| Digital Realty | 1,6 mdr | +9,7 | +4,1 | +3,1 | 2025Q3 | 2025-10-31 | `rev_dlr` |

**Capex över fyra kvartal per köpare** (sammanhang, ingår inte i läsregeln):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Microsoft | 69,0 mdr | +33,3 | -10,6 | -2,6 | 2025Q3 | 2025-10-29 | `kl_capex4_msft` |
| Alphabet | 77,9 mdr | +45,8 | +3,9 | +4,7 | 2025Q3 | 2025-10-30 | `kl_capex4_googl` |
| Amazon | 120,1 mdr | +54,4 | -1,1 | -3,8 | 2025Q3 | 2025-10-31 | `kl_capex4_amzn` |
| Meta | 62,7 mdr | +72,4 | +22,6 | +3,5 | 2025Q3 | 2025-10-30 | `kl_capex4_meta` |
| Oracle | 27,4 mdr | +125,0 | +33,5 | -2,6 | 2025Q3 | 2025-09-10 | `kl_capex4_orcl` |
| CoreWeave | – | – | – | – | – | – | `kl_capex4_crwv` |
| Nebius | – | – | – | – | – | – | `kl_capex4_nbis` |
| IREN | – | – | – | – | – | – | `kl_capex4_iren` |

**Köparnas capex-guidance för kalenderåret** (förväntad capex; mittpunkt, guidad takt mot föregående års utfall där F1:s definition finns; ingår inte i läsregeln):

- Alphabet 2025: 91,0 mdr–93,0 mdr, guidad takt +56,0; known_from 2025-10-29
- Meta 2025: 70,0 mdr–72,0 mdr, guidad takt +59,3; known_from 2025-10-29

### 4. Att bevaka

Nästa kvartal per storhet, när alla dess medlemmar har lämnat in (uppskattat ur de åtta senaste inlämningarna per bolag):

- K-inre (Microsoft, Alphabet, Amazon, Meta): 2025Q4 omkring 2026-02-01
- K-yttre (Oracle, CoreWeave, Nebius, IREN): inget kvartal känt på dagen.
- L1 Kraft och elnät (Eaton, Quanta): 2025Q4 omkring 2026-02-02
- L2 Nät och servrar (Cisco, Dell, Super Micro): 2025Q3 omkring 2025-12-10
- L3 Datacenter (Equinix, RPO): 2025Q4 omkring 2026-02-03
- O1 Eatons order (Electrical Americas, organisk, 12 mån): 2025Q4 omkring 2026-02-02
- O2 Digital Realtys nya avtal (fyra kvartal): 2025Q4 omkring 2026-01-24

Nästa osedda läsning: med inlämningar efter 2026-11-26 (inga uppskattade ännu).

### 5. Förbehåll

- Med 10–27 ursprung per rad, och färre med impuls, är detta en beskrivning och inget test. Ett mönster kan vara slump, och ett utfall som talar för mekanismen visar inte orsaken.
- RPO och orderstock är inte orderingång. Ciscos och Dells RPO har stora tjänstedelar. Ciscos och Dells balanser har räkenskapskvartalets kalenderkvartal, upp till en månad efter kalenderkvartalets slut.
- Leverantörerna säljer också till andra än AI-köparna: Quanta och Eaton till elbolag och industri, Cisco och Dell till företag. Ett utslag säger inget om hur stor del som gäller AI.
- Förvärv ger nivåskiften. Belagda förvärv märks i tabellen (Cisco–Splunk 2024Q1, Eaton–Fibrebond 2025Q2, Eaton–Boyd Thermal 2026Q1) med förskjutning och riktning: vid a och a + 1 flyttas förändringen i takt uppåt, vid a + 4 och a + 5 nedåt. Träffar två förvärv samma kvartal åt olika håll är nettoriktningen inte känd. Förvärv hos Quanta, Dell, Super Micro och Equinix är inte kontrollerade.
- O1 och O2 är S3:s extraktion (publish=False i väntan på granskningen). Digital Realtys andel är obelagd 2021Q4–2024Q1 (S3, tolkning 9).
- Vertiv är BLOCKED (inget RPO i XBRL, och S3:s orderserier slutar 2025Q4). GE Vernovas RPO och order är för korta för läsregeln och visas som sammanhang. Yttre lagrets förändring i capex-takt finns först när serien har sju kvartal (från 2026Q4).
- Historiken räknas på läsdagens vintage, så revideringar kan ändra äldre utfall (F0).
