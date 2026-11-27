# Betalningsgapet: följd fråga (BG1)

*Ändrat av S1 (`docs/mattregister.md`, 2026-11-27 S1, punkt 3): F0:s räkning av hur ofta regeln kunde prövas är ändrad (S1, punkt 3): ett ursprung räknas som prövat bara när Y finns i fönstret, och varje rad visar det gamla talet bredvid det nya i en övergångsnotis. Rapporterna nedan är genererade på nytt per 2026-11-27 och 2025-11-27. Utom datumen och räkningen är de desamma som per 2026-11-26 och 2025-11-26, så texten om de dagarna gäller också för de nya.*

*Rättad efter granskningen R28 (rättningsspår X25, `docs/mattregister.md`, 2026-11-26 X25): förbehållet om sedda data avgörs nu per läsning och inte av läsdagen, antennen visar alltid radens kvartal, och varje rad visar hur ofta Y var känt i hela fönstret och vilken riktning som inte har prövats. Inga utslag ändrades. Rapporterna nedan är genererade på nytt med kommandot.*

*Tillägg 2026-11-27 (spår AN1, `docs/mattregister.md`, 2026-11-27 AN1): avsnitt 5 har Anthropics redovisade (GAAP) tal ur registreringsprospektet som tabellrader och en kvartalstabell bredvid run-rate, och BLOCKED-raden om dem är borta. Rapporterna nedan är genererade på nytt med kommandot. Allt utanför avsnitt 5 och förbehållet om labbens intäkter är byte för byte detsamma som förut, och inga utslag ändrades.*

**Frågan:** Växer de intäkter som ska bära investeringarna (molnintäkter, AI-nyckeltal, RPO och frontlabbens intäkter) i
takt med intäktskravet från avskrivningar och kapitalkostnad, eller öppnas eller sluts gapet?

Följd fråga, inte en gren. Måtten, läsregeln och gränserna låstes i registret innan något mått räknades
(`docs/mattregister.md`, 2026-11-26 BG1, commit `12d9581`, ensam). Källor, kodning och förbehåll:
`docs/kallor/betalningsgapet.md`. Rapporten byggs med

    python -m ai_tracker.followed betalningsgapet --as-of 2026-11-27 [--json PATH] [--out PATH]

Den använder bara rader som var kända på dagen. Nedan står rapporten per 2026-11-27 och per 2025-11-27, så att
ändringen över ett år syns. Rapporterna är genererade av kommandot och inte redigerade (rubrikerna är en nivå lägre).

**Läsningarna är gjorda på sedda data.** Alla kvartal i båda läsningarna var kända före registerposten, och P2b:s
kvoter mot totala intäkter och KL1:s capex-takt för de inre bolagen var sedda före posten (posten, avsnitt (e)).
Utslagen är därför inga utfall på osedda data. Den första läsningen på osedda kvartal kommer med Oracles inlämning
omkring 2026-12-11 (Oracles bolagsrader). Molnfyrans huvudläsning med 2026Q4 kommer när alla fyra har lämnat in,
uppskattat omkring 2027-01-31. Förbehållet avgörs per läsning (X25, punkt 1), så Oracles rader blir osedda före huvudläsningen. Huvudläsningen har bara haft impulser uppåt (5 av 7 ursprung, ingen nedåt), så riktningen nedåt har inte prövats.

**Kontroller.** `compute(d, tabell)` ger samma rapport som på tabellen kapad vid *d* per 2025-11-26, 2026-10-26 och
2026-11-26 (riktiga data). `capex4` per bolag är lika med KL1:s `kl_capex4_<bolag>` genom `state.measures` (nivå,
takt, förändring i takt och `known_from` per 2026-11-26, alla fem bolag), så `path_measures` och versionsregeln ger
samma tal som katalogvägen. De syntetiska testerna står i `tests/test_followed_betalningsgapet.py`.

## Vad som skiljer de två dagarna (beskrivning, inget test)

- **Gapet mot molnintäkterna öppnas båda åren, men långsammare nu.** Gapets takt för molnfyran (*r* = 0,10) var
  +10,2 per 2025Q3 och +6,5 per 2026Q3. Intäktskravet växte med +30,9 och +38,3 log-enheter per år, molnintäkterna med
  +20,7 och +31,8. Intäkterna har alltså knappat in, men kravet växer fortfarande snabbast. Nivån är 55,5 % och 56,7 %
  av molnintäkterna, men nivån är ingen marginal (hela bolagens kapital mot bara molnet).
- **Det är kapitalkostnaden, inte avskrivningarna, som öppnar gapet.** Med *r* = 0 (bara avskrivningar) var takten
  +6,4 per 2025Q3 och −1,6 per 2026Q3: avskrivningarna växer nu något långsammare än molnintäkterna. Med *r* = 0,08
  och 0,12 är takten +5,5 och +7,4 per 2026Q3. Skillnaden är nettot av anläggningstillgångar, som växer snabbare än
  avskrivningarna och innehåller pågående byggen som ännu inte skrivs av.
- **Mot RPO sluts gapet kraftigt båda åren.** Gapets takt mot RPO var −36,7 och −33,9: orderstocken växer betydligt
  snabbare än intäktskravet (+67,6 och +72,2 per år). Utan Oracle var takten −7,3 per 2025Q3 och −52,4 per 2026Q3, så
  under det senaste året kommer tillväxten i orderstocken också från de tre andra. Oracles andel av molnfyrans RPO föll
  från 37,6 % till 26,6 %.
- **Läsregeln.** Per 2026-11-26 ger huvudläsningen "talar emot": gapet öppnades (X +7,6 vid 2026Q2) och capex-takten
  steg (förändring i takt +10,7 vid 2026Q3). I historiken (7 ursprung, 2024Q4–2026Q2) öppnades gapet med minst 5 vid 5
  ursprung, och capex-takten steg därefter vid 4 av dem. Det är den mekaniska kopplingen som registret varnar för:
  kravet innehåller capex, så en acceleration i capex höjer både X och *Y*. "Talar emot" är därför ett svagt belägg mot
  mekanismen. Raden med *r* = 0, som är minst kopplad, ger "inget av mönstren" (ingen impuls). Per 2025-11-26 kunde
  huvudläsningen inte avgöras (fönstret efter 2025Q2 var öppet).
- **Raden mot RPO ger "talar för mekanismen"** per 2026-11-26: gapet mot orderstocken slöts (X −69,8) och capex-takten
  steg. Det gäller också utan Oracle. Per 2025-11-26 gav den "inget av mönstren". X är mycket stor och bygger på några
  få mycket stora avtal, så utslaget säger mer om orderstockens språng än om en jämn trend.
- **Bolagen.** Oracle ger "talar för" mot molnintäkterna båda åren men av olika skäl: per 2025-11-26 slöts gapet och
  capex-takten steg (+69,0), per 2026-11-26 öppnades gapet (+27,9) och capex-takten föll (−15,8). Mot RPO gav Oracle
  "talar för" per 2025-11-26 och "talar emot" per 2026-11-26 (gapet mot orderstocken slöts men capex-takten föll).
  Microsoft gick från "talar för" (capex-takten föll 2025Q3) till "talar emot" (gapet öppnades och capex-takten steg
  +21,7). Alphabet ger "inget av mönstren" mot molnintäkterna båda åren. Google Clouds intäkter växer snabbare än
  Alphabets krav (gapets takt −11,6 per 2026Q3), men inte med minst 5 vid ursprungen i fönstret. Amazon gick från
  "inget av mönstren" till "talar emot" mot molnintäkterna. CoreWeave hade inga fyra kvartal per 2025-11-26 (2024Q4
  blev känt först med 10-K:n 2026-03-02) och ger "talar emot" mot molnintäkterna per 2026-11-26.
- **Regimmarkörer.** Per 2025-11-26 märks huvudläsningen av Amazons (2024Q1) och Oracles (2024Q2) längre
  nyttjandeperioder och av Microsofts gamla avskrivningsbas i fönstret. Per 2026-11-26 ligger ingen ändring av det
  högsta värdet inom fönstret. Amazons förkortning 2025Q4 syns bara i det lägsta värdet och märker därför inte enligt
  registret, men den står i listan.
- **Sammanhang.** AI-nyckeltalen och labbens run-rate är högre per 2026-11-26: Microsofts AI-verksamhet 37 mdr i
  årstakt (2026-03) mot 13 mdr (2024-12), Google Clouds orderstock 460 mdr (2026-03) mot 155 mdr (2025-09), och
  Anthropic 81 mdr per 2026-10-31 enligt S-1/A mot 7 mdr per 2025-10-21 i nyhetsrummet. De två Anthropic-talen är
  olika mått (S-1 definierar sitt), och run-rate är inte redovisad intäkt. OpenAI är BLOCKED.
- **Anthropics redovisade intäkter (AN1, tillagt 2026-11-27).** Prospekten ger redovisade (GAAP) tal från
  2026-10-26, så de finns per 2026-11-26 men inte per 2025-11-26. Intäkten var 17,0 mdr för 2026Q3 och 11,6 mdr för
  2026Q2 (4,6 mdr för helåret 2025). Kvartalet × 4 är 67,8 mdr för 2026Q3, under run-rate 81 mdr per 2026-10-31 enligt
  S-1/A, och 46,2 mdr för 2026Q2, nära nyhetsrummets 47 mdr per 2026-05-28. Det är olika mått: den redovisade
  intäkten är summan över kvartalet, run-rate är bolagets egen årstakt vid en dag (28 dagars konsumtion × 13 plus
  abonnemang × 12) och ligger över kvartalet × 4 när intäkterna växer under kvartalet. Kostnaden för compute och
  infrastruktur var 58 % av intäkten 2026Q3 (48 % 2026Q2), och rörelseresultatet −0,6 mdr efter +1,0 mdr kvartalet före.
  Talen står i avsnitt 5 som beskrivning. De ingår inte i regeln, och inga utslag ändras.
- Varje mönster kan vara slump. Med 7 ursprung i molnfyrans historik och klumpig RPO är detta en beskrivning och inget
  test.


## Betalningsgapet per 2026-11-27

**Frågan:** Växer de intäkter som ska bära investeringarna (molnintäkter, AI-nyckeltal, RPO och frontlabbens intäkter) i takt med intäktskravet från avskrivningar och kapitalkostnad, eller öppnas eller sluts gapet?

Intäktskrav = avskrivningar över fyra kvartal + r × anläggningstillgångar netto vid kvartalets slut (hela bolaget, bara kapitalet). Bärande intäkter = molnintäkter över fyra kvartal (Microsoft Cloud, Google Cloud, AWS, Oracles moln, CoreWeaves intäkter) eller RPO vid kvartalets slut. Gapet = 100 × intäktskrav / bärande intäkter. Molnfyran = Microsoft, Alphabet, Amazon och Oracle, som summor av komponenterna. Takt = årsförändring i log × 100, så gapets takt är intäktskravets takt minus intäkternas: positiv = gapet öppnas, negativ = gapet sluts. Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1. Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-26 BG1.

### 1. Molnfyran: intäktskrav, bärande intäkter och investeringstakt

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| krav(molnfyran, r=0,10) | 296,0 mdr | +38,3 | +3,5 | +1,7 | 2026Q3 | 2026-10-30 | `krav(molnfyran, r=0,10)` |
| krav(molnfyran, r=0,00) | 160,4 mdr | +30,2 | +1,8 | +0,8 | 2026Q3 | 2026-10-30 | `krav(molnfyran, r=0,00)` |
| moln(molnfyran) | 522,2 mdr | +31,8 | +6,8 | +2,6 | 2026Q3 | 2026-10-30 | `moln(molnfyran)` |
| rpo(molnfyran) | 2 492,7 mdr | +72,2 | -29,1 | -19,9 | 2026Q3 | 2026-10-30 | `rpo(molnfyran)` |
| capex4(molnfyran) | 586,6 mdr | +68,9 | +10,7 | +5,5 | 2026Q3 | 2026-10-30 | `capex4(molnfyran)` |

**Gapet** (procent av molnintäkterna respektive av RPO):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| gap_moln(molnfyran, r=0,10) | 56,7 % | +6,5 | -3,3 | -0,9 | 2026Q3 | 2026-10-30 | `gap_moln(molnfyran, r=0,10)` |
| gap_moln(molnfyran, r=0,00) | 30,7 % | -1,6 | -5,1 | -1,8 | 2026Q3 | 2026-10-30 | `gap_moln(molnfyran, r=0,00)` |
| gap_moln(molnfyran, r=0,08) | 51,5 % | +5,5 | -3,5 | -1,0 | 2026Q3 | 2026-10-30 | `gap_moln(molnfyran, r=0,08)` |
| gap_moln(molnfyran, r=0,12) | 61,9 % | +7,4 | -3,2 | -0,8 | 2026Q3 | 2026-10-30 | `gap_moln(molnfyran, r=0,12)` |
| gap_rpo(molnfyran, r=0,10) | 11,9 % | -33,9 | +32,6 | +21,6 | 2026Q3 | 2026-10-30 | `gap_rpo(molnfyran, r=0,10)` |
| gap_rpo(molnfyran utan Oracle, r=0,10) | 14,9 % | -52,4 | +3,2 | +17,0 | 2026Q3 | 2026-10-30 | `gap_rpo(molnfyran utan Oracle, r=0,10)` |

Nästa kvartal (2026Q4) för molnfyran saknar på dagen: `dep_msft 2026Q4`, `dep_googl 2026Q4`, `dep_amzn 2026Q4`, `dep_orcl 2026Q4`, `ppe_net_msft 2026Q4`, `ppe_net_googl 2026Q4`, `ppe_net_amzn 2026Q4`, `ppe_net_orcl 2026Q4`, `rev_msft_cloud 2026Q4`, `rev_google_cloud 2026Q4`, `rev_aws 2026Q4`, `rev_orcl_cloud 2026Q4`.

### 2. Per bolag (r = 0,10)

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| gap_moln(Microsoft, r=0,10) | 33,5 % | +10,7 | -2,8 | +0,4 | 2026Q3 | 2026-10-28 | `gap_moln(Microsoft, r=0,10)` |
| gap_moln(Alphabet, r=0,10) | 70,1 % | -11,6 | -13,0 | -4,2 | 2026Q3 | 2026-10-29 | `gap_moln(Alphabet, r=0,10)` |
| gap_moln(Amazon, r=0,10) | 80,7 % | +4,2 | -4,2 | -1,6 | 2026Q3 | 2026-10-30 | `gap_moln(Amazon, r=0,10)` |
| gap_moln(Oracle, r=0,10) | 61,6 % | +30,5 | +1,3 | +1,3 | 2026Q3 | 2026-09-11 | `gap_moln(Oracle, r=0,10)` |
| gap_moln(CoreWeave, r=0,10) | 110,5 % | +15,8 | +4,8 | -8,3 | 2026Q3 | 2026-11-12 | `gap_moln(CoreWeave, r=0,10)` |

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| gap_rpo(Microsoft, r=0,10) | 11,2 % | -18,7 | +12,0 | +16,3 | 2026Q3 | 2026-10-28 | `gap_rpo(Microsoft, r=0,10)` |
| gap_rpo(Alphabet, r=0,10) | 11,5 % | -83,2 | +40,5 | +33,0 | 2026Q3 | 2026-10-29 | `gap_rpo(Alphabet, r=0,10)` |
| gap_rpo(Amazon, r=0,10) | 22,5 % | -73,9 | -37,1 | +8,8 | 2026Q3 | 2026-10-30 | `gap_rpo(Amazon, r=0,10)` |
| gap_rpo(Oracle, r=0,10) | 3,6 % | +31,6 | +118,0 | +39,6 | 2026Q3 | 2026-09-11 | `gap_rpo(Oracle, r=0,10)` |
| gap_rpo(CoreWeave, r=0,10) | 8,3 % | +1,6 | +97,8 | +5,5 | 2026Q3 | 2026-11-12 | `gap_rpo(CoreWeave, r=0,10)` |

Komponenterna per bolag:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| krav(Microsoft, r=0,10) | 76,8 mdr | +35,3 | -1,9 | +1,1 | 2026Q3 | 2026-10-28 | `krav(Microsoft, r=0,10)` |
| moln(Microsoft) | 229,2 mdr | +24,7 | +0,9 | +0,7 | 2026Q3 | 2026-10-28 | `moln(Microsoft)` |
| rpo(Microsoft) | 683,0 mdr | +54,0 | -13,9 | -15,2 | 2026Q3 | 2026-10-28 | `rpo(Microsoft)` |
| capex4(Microsoft) | 135,9 mdr | +67,8 | +21,7 | +1,3 | 2026Q3 | 2026-10-28 | `capex4(Microsoft)` |
| krav(Alphabet, r=0,10) | 65,3 mdr | +44,9 | +6,4 | +2,6 | 2026Q3 | 2026-10-29 | `krav(Alphabet, r=0,10)` |
| moln(Alphabet) | 93,2 mdr | +56,4 | +19,4 | +6,9 | 2026Q3 | 2026-10-29 | `moln(Alphabet)` |
| rpo(Alphabet) | 567,7 mdr | +128,1 | -34,1 | -30,3 | 2026Q3 | 2026-10-29 | `rpo(Alphabet)` |
| capex4(Alphabet) | 159,8 mdr | +71,9 | +7,5 | +1,8 | 2026Q3 | 2026-10-29 | `capex4(Alphabet)` |
| krav(Amazon, r=0,10) | 130,2 mdr | +32,2 | +3,5 | +0,7 | 2026Q3 | 2026-10-30 | `krav(Amazon, r=0,10)` |
| moln(Amazon) | 161,4 mdr | +28,0 | +7,7 | +2,3 | 2026Q3 | 2026-10-30 | `moln(Amazon)` |
| rpo(Amazon) | 578,0 mdr | +106,1 | +40,6 | -8,0 | 2026Q3 | 2026-10-30 | `rpo(Amazon)` |
| capex4(Amazon) | 215,2 mdr | +58,3 | +9,9 | +9,9 | 2026Q3 | 2026-10-30 | `capex4(Amazon)` |
| krav(Oracle, r=0,10) | 23,7 mdr | +69,3 | +11,2 | +5,3 | 2026Q3 | 2026-09-11 | `krav(Oracle, r=0,10)` |
| moln(Oracle) | 38,4 mdr | +38,8 | +9,9 | +4,1 | 2026Q3 | 2026-09-11 | `moln(Oracle)` |
| rpo(Oracle) | 664,0 mdr | +37,7 | -106,8 | -34,3 | 2026Q3 | 2026-09-11 | `rpo(Oracle)` |
| capex4(Oracle) | 75,7 mdr | +101,5 | -15,8 | +6,6 | 2026Q3 | 2026-09-11 | `capex4(Oracle)` |
| krav(CoreWeave, r=0,10) | 10,9 mdr | +98,9 | +4,6 | -1,0 | 2026Q3 | 2026-11-12 | `krav(CoreWeave, r=0,10)` |
| moln(CoreWeave) | 9,9 mdr | +83,1 | -0,2 | +7,3 | 2026Q3 | 2026-11-12 | `moln(CoreWeave)` |
| rpo(CoreWeave) | 132,3 mdr | +97,3 | -93,2 | -6,6 | 2026Q3 | 2026-11-12 | `rpo(CoreWeave)` |
| capex4(CoreWeave) | 27,6 mdr | +104,2 | +35,7 | +7,6 | 2026Q3 | 2026-11-12 | `capex4(CoreWeave)` |

### 3. Läsregeln, mekaniskt

F0:s symmetriska regel, en rad per X. X = gapets takt (gräns ±5 log × 100 per år), Y = förändring i capex-takt för samma bolag (gräns ±5), fönster 2 kvartal, tecken −. Gapet öppnas (X ≥ +5) och capex-takten faller med minst 5 först: talar för. Gapet sluts (X ≤ −5) och capex-takten stiger med minst 5 först: talar för. Motsatt rörelse först: talar emot. Håller capex-takten sig inom ±5: inget av mönstren, så regeln skiljer inte "stöder fortsatt takt" från "ingen effekt". Utslaget är en beskrivning, inget test.

Intäktskravet innehåller capex (nettot växer med investeringarna, avskrivningarna följer efter). En uthållig acceleration i capex höjer därför både X och Y och läses som talar emot. Ett utslag som talar emot är ett svagare belägg mot mekanismen än ett som talar för är belägg för den. Raden med r = 0 är minst direkt kopplad.

Alla läsningar nedan vilar bara på värden som var kända före registerposten 2026-11-26, och P2b:s kvoter och KL1:s capex-takt för de inre bolagen var sedda före posten (posten, avsnitt (e)). Ingen av läsningarna är därför ett utfall på osedda data. Den första osedda läsningen kommer med inlämningar efter 2026-11-26 (avsnitt 7). Sedda data avgörs per läsning (X25, punkt 1).

- **Huvudläsning: gapet mot molnintäkterna, molnfyran, r = 0,10:** talar emot. t = 2026Q3; ursprung 2026Q2, X +7,6 (gräns ±5,0), uppgång, Y +10,7 vid 2026Q3 (gräns ±5,0). X = gap_moln(molnfyran, r=0,10) (takt), Y = capex4(molnfyran) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 7 av 7 ursprung med X (2024Q4–2026Q2). Impulser uppåt 5 (för 0, emot 4, inget 1, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 6 av 7 ursprung, och 5 av 5 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 7 av 7; med den nya: 7 av 7.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-26, och den är därför inget utfall på osedda data.
- **Gapet mot RPO, molnfyran, r = 0,10:** talar för mekanismen. t = 2026Q3; ursprung 2026Q2, X -69,8 (gräns ±5,0), nedgång, Y +10,7 vid 2026Q3 (gräns ±5,0). X = gap_rpo(molnfyran, r=0,10) (takt), Y = capex4(molnfyran) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 7 av 7 ursprung med X (2024Q4–2026Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 5 (för 5, emot 0, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 6 av 7 ursprung, och 5 av 5 impulser kunde läsas mot Y. Riktningen uppåt har inte prövats: X har inte haft någon impuls uppåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 7 av 7; med den nya: 7 av 7.
- **Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,00 (bara avskrivningar):** inget av mönstren. t = 2026Q3 (ingen impuls i fönstret). X = gap_moln(molnfyran, r=0,00) (takt), Y = capex4(molnfyran) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 6 av 7 ursprung med X (2024Q4–2026Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 7.
  Y var känt i hela fönstret i 6 av 7 ursprung, och 0 av 0 impulser kunde läsas mot Y. Ingen riktning har prövats: X har inte haft någon impuls.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 7 av 7; med den nya: 6 av 7.
- **Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,08:** talar emot. t = 2026Q3; ursprung 2026Q2, X +6,7 (gräns ±5,0), uppgång, Y +10,7 vid 2026Q3 (gräns ±5,0). X = gap_moln(molnfyran, r=0,08) (takt), Y = capex4(molnfyran) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 7 av 7 ursprung med X (2024Q4–2026Q2). Impulser uppåt 4 (för 0, emot 4, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 3.
  Y var känt i hela fönstret i 6 av 7 ursprung, och 4 av 4 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 7 av 7; med den nya: 7 av 7.
- **Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,12:** talar emot. t = 2026Q3; ursprung 2026Q2, X +8,4 (gräns ±5,0), uppgång, Y +10,7 vid 2026Q3 (gräns ±5,0). X = gap_moln(molnfyran, r=0,12) (takt), Y = capex4(molnfyran) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 7 av 7 ursprung med X (2024Q4–2026Q2). Impulser uppåt 5 (för 0, emot 4, inget 1, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 6 av 7 ursprung, och 5 av 5 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 7 av 7; med den nya: 7 av 7.
- **Känslighet: gapet mot RPO utan Oracle, r = 0,10:** talar för mekanismen. t = 2026Q3; ursprung 2026Q2, X -58,1 (gräns ±5,0), nedgång, Y +12,5 vid 2026Q3 (gräns ±5,0). X = gap_rpo(molnfyran utan Oracle, r=0,10) (takt), Y = capex4(molnfyran utan Oracle) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 7 av 7 ursprung med X (2024Q4–2026Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 4 (för 4, emot 0, inget 0, kan inte avgöras 0), utan impuls 3.
  Y var känt i hela fönstret i 6 av 7 ursprung, och 4 av 4 impulser kunde läsas mot Y. Riktningen uppåt har inte prövats: X har inte haft någon impuls uppåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 7 av 7; med den nya: 7 av 7.

**Bolagsrader** (bisak, samma gränser, Y = bolagets egen capex-takt):

- **Microsoft: gapet mot molnintäkterna:** talar emot. t = 2026Q3; ursprung 2026Q2, X +9,7 (gräns ±5,0), uppgång, Y +21,7 vid 2026Q3 (gräns ±5,0). X = gap_moln(Microsoft, r=0,10) (takt), Y = capex4(Microsoft) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 17 av 17 ursprung med X (2022Q2–2026Q2). Impulser uppåt 10 (för 3, emot 5, inget 2, kan inte avgöras 0), nedåt 6 (för 4, emot 2, inget 0, kan inte avgöras 0), utan impuls 1.
  Y var känt i hela fönstret i 16 av 17 ursprung, och 16 av 16 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 17 av 17; med den nya: 17 av 17.
- **Microsoft: gapet mot RPO:** talar för mekanismen. t = 2026Q3; ursprung 2026Q2, X -26,5 (gräns ±5,0), nedgång, Y +21,7 vid 2026Q3 (gräns ±5,0). X = gap_rpo(Microsoft, r=0,10) (takt), Y = capex4(Microsoft) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 32 av 32 ursprung med X (2018Q3–2026Q2). Impulser uppåt 6 (för 2, emot 2, inget 2, kan inte avgöras 0), nedåt 22 (för 11, emot 7, inget 4, kan inte avgöras 0), utan impuls 4.
  Y var känt i hela fönstret i 31 av 32 ursprung, och 28 av 28 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 32 av 32; med den nya: 32 av 32.
- **Alphabet: gapet mot molnintäkterna:** inget av mönstren. t = 2026Q3 (ingen impuls i fönstret). X = gap_moln(Alphabet, r=0,10) (takt), Y = capex4(Alphabet) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 6 av 7 ursprung med X (2024Q4–2026Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 7.
  Y var känt i hela fönstret i 6 av 7 ursprung, och 0 av 0 impulser kunde läsas mot Y. Ingen riktning har prövats: X har inte haft någon impuls.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 7 av 7; med den nya: 6 av 7.
- **Alphabet: gapet mot RPO:** talar för mekanismen. t = 2026Q3; ursprung 2026Q2, X -115,7 (gräns ±5,0), nedgång, Y +7,5 vid 2026Q3 (gräns ±5,0). X = gap_rpo(Alphabet, r=0,10) (takt), Y = capex4(Alphabet) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 7 av 7 ursprung med X (2024Q4–2026Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 4 (för 4, emot 0, inget 0, kan inte avgöras 0), utan impuls 3.
  Y var känt i hela fönstret i 6 av 7 ursprung, och 4 av 4 impulser kunde läsas mot Y. Riktningen uppåt har inte prövats: X har inte haft någon impuls uppåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 7 av 7; med den nya: 7 av 7.
- **Amazon: gapet mot molnintäkterna:** talar emot. t = 2026Q3; ursprung 2026Q2, X +6,2 (gräns ±5,0), uppgång, Y +9,9 vid 2026Q3 (gräns ±5,0). X = gap_moln(Amazon, r=0,10) (takt), Y = capex4(Amazon) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 23 av 23 ursprung med X (2020Q4–2026Q2). Impulser uppåt 4 (för 2, emot 2, inget 0, kan inte avgöras 0), nedåt 4 (för 1, emot 3, inget 0, kan inte avgöras 0), utan impuls 15.
  Y var känt i hela fönstret i 22 av 23 ursprung, och 8 av 8 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 23 av 23; med den nya: 23 av 23.
- **Amazon: gapet mot RPO:** talar för mekanismen. t = 2026Q3; ursprung 2026Q2, X -62,9 (gräns ±5,0), nedgång, Y +9,9 vid 2026Q3 (gräns ±5,0). X = gap_rpo(Amazon, r=0,10) (takt), Y = capex4(Amazon) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 23 av 23 ursprung med X (2020Q4–2026Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 19 (för 7, emot 12, inget 0, kan inte avgöras 0), utan impuls 4.
  Y var känt i hela fönstret i 22 av 23 ursprung, och 19 av 19 impulser kunde läsas mot Y. Riktningen uppåt har inte prövats: X har inte haft någon impuls uppåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 23 av 23; med den nya: 23 av 23.
- **Oracle: gapet mot molnintäkterna:** talar för mekanismen. t = 2026Q3; ursprung 2026Q2, X +27,9 (gräns ±5,0), uppgång, Y -15,8 vid 2026Q3 (gräns ±5,0). X = gap_moln(Oracle, r=0,10) (takt), Y = capex4(Oracle) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 13 av 13 ursprung med X (2023Q2–2026Q2). Impulser uppåt 6 (för 5, emot 1, inget 0, kan inte avgöras 0), nedåt 5 (för 4, emot 1, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 12 av 13 ursprung, och 11 av 11 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 13 av 13; med den nya: 13 av 13.
- **Oracle: gapet mot RPO:** talar emot. t = 2026Q3; ursprung 2026Q2, X -92,7 (gräns ±5,0), nedgång, Y -15,8 vid 2026Q3 (gräns ±5,0). X = gap_rpo(Oracle, r=0,10) (takt), Y = capex4(Oracle) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 28 av 28 ursprung med X (2019Q3–2026Q2). Impulser uppåt 4 (för 4, emot 0, inget 0, kan inte avgöras 0), nedåt 15 (för 11, emot 4, inget 0, kan inte avgöras 0), utan impuls 9.
  Y var känt i hela fönstret i 27 av 28 ursprung, och 19 av 19 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 28 av 28; med den nya: 28 av 28.
- **CoreWeave: gapet mot molnintäkterna:** talar emot. t = 2026Q3; ursprung 2026Q2, X +20,3 (gräns ±5,0), uppgång, Y +35,7 vid 2026Q3 (gräns ±5,0). X = gap_moln(CoreWeave, r=0,10) (takt), Y = capex4(CoreWeave) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 3 ursprung med X (2025Q4–2026Q2). Impulser uppåt 2 (för 0, emot 2, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 1.
  Y var känt i hela fönstret i 1 av 3 ursprung, och 2 av 2 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 3 av 3; med den nya: 2 av 3.
- **CoreWeave: gapet mot RPO:** talar för mekanismen. t = 2026Q3; ursprung 2026Q2, X -26,7 (gräns ±5,0), nedgång, Y +35,7 vid 2026Q3 (gräns ±5,0). X = gap_rpo(CoreWeave, r=0,10) (takt), Y = capex4(CoreWeave) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 2 ursprung med X (2026Q1–2026Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 2 (för 2, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 1 av 2 ursprung, och 2 av 2 impulser kunde läsas mot Y. Riktningen uppåt har inte prövats: X har inte haft någon impuls uppåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 2 av 2; med den nya: 2 av 2.

### 4. Sammanhang

**P2b:s avstämningar** (hyp4 mot totala intäkter, AWS-segmentet och RPO mot capex; katalogserier):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| x_dep_rev | 9,39 | +12,2 | +0,0 | +0,7 | 2026Q3 | 2026-10-30 | `x_dep_rev` |
| x_capcost_rev_r08 | 15,78 | +18,3 | +1,8 | +1,4 | 2026Q3 | 2026-10-30 | `x_capcost_rev_r08` |
| x_capcost_rev_r12 | 18,97 | +19,9 | +2,2 | +1,5 | 2026Q3 | 2026-10-30 | `x_capcost_rev_r12` |
| x_dep_rev_aws | 19,30 | +22,8 | -6,1 | -2,7 | 2026Q3 | 2026-10-30 | `x_dep_rev_aws` |
| x_rpo_cover | 4,05 | +9,8 | -38,7 | -24,5 | 2026Q3 | 2026-10-30 | `x_rpo_cover` |

**RPO på kort sikt** (andelen inom 12 eller 24 månader enligt bolaget, belopp ungefärliga):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| rpo_msft_12m | 204,9 mdr | +25,2 | -13,9 | -8,0 | 2026Q3 | 2026-10-28 | `rpo_msft_12m` |
| rpo_orcl_12m | 86,3 mdr | +64,0 | +14,3 | -1,0 | 2026Q3 | 2026-09-11 | `rpo_orcl_12m` |
| rpo_googl_24m | 312,2 mdr | +128,1 | -24,5 | -18,4 | 2026Q3 | 2026-10-29 | `rpo_googl_24m` |
| rpo_crwv_24m | 47,6 mdr | +81,9 | -60,9 | -14,6 | 2026Q3 | 2026-11-12 | `rpo_crwv_24m` |

Oracles andel av molnfyrans RPO vid 2026Q3: **26,6 %**. RPO är klumpig: enstaka mycket stora avtal flyttar ett kvartal, och raden utan Oracle i avsnitt 3 visar hur mycket Oracle betyder.

Bolagens guidance för molnintäkter finns inte i katalogen, så B1 är enda baslinjen för intäkterna.

### 5. AI-nyckeltal och labbens intäkter (tabellrader, ingår inte i regeln)

- Microsoft: Azure and other cloud services, tillväxt å/å (definition FY25–FY26): **43,0 %** (2026Q2; före: 40,0 % (2026Q1)); 12 värden, known_from 2026-07-29, `kpi_msft_azure_growth_v2`
- Microsoft: Azure, tillväxt å/å (definition från FY27): **48,0 %** (2026Q3; före: 42,0 % (2026Q2)); 5 värden, known_from 2026-10-28, `kpi_msft_azure_growth_v3`
- Microsoft: Azure, tillväxt å/å i konstant valuta (definition från FY27): **48,0 %** (2026Q3; före: 42,0 % (2026Q2)); 5 värden, known_from 2026-10-28, `kpi_msft_azure_growth_cc_v3`
- Microsoft: AI-verksamhetens intäkt i årstakt: **37,0 mdr** (2026-03; före: 13,0 mdr (2024-12)); 2 värden, known_from 2026-04-29, `kpi_msft_ai_business_runrate`
- Amazon: AWS AI-verksamhet, intäkt i årstakt: **25,0 mdr** (2026-07; före: 15,0 mdr (2026-03)); 2 värden, known_from 2026-07-30, `kpi_amzn_aws_ai_runrate`
- Alphabet: Google Clouds orderstock (backlog): **460,0 mdr** (2026-03; före: 155,0 mdr (2025-09)); 2 värden, known_from 2026-04-29, `kpi_googl_cloud_backlog`
- Anthropic, run-rate revenue, hela bolaget (rapporterad): **47,0 mdr** (2026-05-28; före: 30,0 mdr (2026-04-20)); 9 värden, known_from 2026-05-28, `lab_rev_anthropic_company_run_rate`
- Anthropic, Run-Rate Revenue enligt S-1, hela bolaget (rapporterad): **81,0 mdr** (2026-10-31); 1 värde, known_from 2026-11-10, `lab_rev_anthropic_company_run_rate_s1`
- Anthropic, run-rate revenue, Claude Code (produkt) (rapporterad): **2,5 mdr** (2026-02-12; före: 1,0 mdr (2025-11-30)); 3 värden, known_from 2026-02-12, `lab_rev_anthropic_claude_code_run_rate`

AI-nyckeltalen är oregelbundna och har definitionsbrott (Azure v1–v3). Run-rate är bolagets egen årstakt vid en tidpunkt och inte redovisad intäkt, och den blandas inte med GAAP-tal.

**Anthropics redovisade tal (GAAP, ur S-1, S-1/A och 424B4; registret 2026-11-27 AN1):**

- Anthropic, intäkter, per kvartal (GAAP, redovisad): **17,0 mdr** (2026Q3; före: 11,6 mdr (2026Q2)); 7 värden, known_from 2026-11-02, `lab_gaap_anthropic_revenue_q`
- Anthropic, intäkter, per år (GAAP, redovisad): **4,6 mdr** (2025; före: 0,4 mdr (2024)); 3 värden, known_from 2026-10-26, `lab_gaap_anthropic_revenue_a`
- Anthropic, rörelseresultat, per kvartal (GAAP, redovisad): **-0,6 mdr** (2026Q3; före: 1,0 mdr (2026Q2)); 7 värden, known_from 2026-11-02, `lab_gaap_anthropic_opinc_q`
- Anthropic, kassaflöde från den löpande verksamheten, hittills i år (GAAP, redovisad): **6,6 mdr** (2026Q3; före: 3,9 mdr (2026Q2)); 4 värden, known_from 2026-11-02, `lab_gaap_anthropic_cfo_ytd`

| Kvartal | Intäkt | Intäkt × 4 | Compute, % av intäkten | Rörelseresultat | known_from | Senaste run-rate känd vid kvartalets slut |
|---|---|---|---|---|---|---|
| 2025Q1 | 0,4 mdr | 1,5 mdr | 251,1 % | -0,9 mdr | 2026-10-26 | – |
| 2025Q2 | 0,8 mdr | 3,1 mdr | 176,6 % | -1,2 mdr | 2026-10-26 | – |
| 2025Q3 | 1,4 mdr | 5,5 mdr | 148,1 % | -3,1 mdr | 2026-10-26 | 5,0 mdr per 2025-08-31 (känd 2025-09-02, `lab_rev_anthropic_company_run_rate`) |
| 2025Q4 | 2,0 mdr | 8,2 mdr | 144,4 % | -2,8 mdr | 2026-10-26 | 7,0 mdr per 2025-10-21 (känd 2025-10-21, `lab_rev_anthropic_company_run_rate`) |
| 2026Q1 | 4,7 mdr | 18,9 mdr | 71,6 % | -1,7 mdr | 2026-10-26 | 14,0 mdr per 2026-02-12 (känd 2026-02-12, `lab_rev_anthropic_company_run_rate`) |
| 2026Q2 | 11,6 mdr | 46,2 mdr | 48,1 % | 1,0 mdr | 2026-10-26 | 47,0 mdr per 2026-05-28 (känd 2026-05-28, `lab_rev_anthropic_company_run_rate`) |
| 2026Q3 | 17,0 mdr | 67,8 mdr | 58,2 % | -0,6 mdr | 2026-11-02 | 47,0 mdr per 2026-05-28 (känd 2026-05-28, `lab_rev_anthropic_company_run_rate`) |

**Skillnaden mot run-rate.** Den redovisade intäkten är summan av det som intäktsförts under kvartalet (GAAP). Run-rate är bolagets egen årstakt vid en dag: konsumtionsavgifter under 28 dagar × 13 plus månatliga abonnemang × 12 (S-1:s definition, ej GAAP och inte granskad av tredje part; nyhetsrummets äldre värden anger inget beräkningssätt). Intäkt × 4 är bara kvartalet uppräknat till ett år. I ett bolag som växer snabbt ligger run-rate vid kvartalets slut över kvartalets intäkt × 4, och de två mäter alltså olika saker. De blandas aldrig i en serie eller en kvot, och run-rate-kolumnen visar bara vad bolaget hade sagt när kvartalet slutade.

Compute och infrastruktur är en kostnad efter slag och omfattar också träning och forskning; kostnaden för intäkter (noten om kostnader efter funktion, `lab_gaap_anthropic_cost_of_revenue_*`) är bara compute för kundernas arbetslaster med mera. Labbets kostnader för compute är till stor del molnens intäkter. Labbets intäkter läggs inte till molnintäkterna i regeln: en del av dem säljs via molnen (Bedrock, Vertex) och skulle räknas två gånger. Ingen känslighetsrad i regeln (AN1, (f)): kvartalen börjar 2025Q1, så takten för en summa över fyra kvartal finns först för 2026Q4.

- **BLOCKED:** OpenAI: ingen registreringsansökan på EDGAR, och openai.com nekas av proxyn (docs/kallor/labbintakter.md).

### 6. Nyttjandeperioder (regimmarkörer)

Kvartal där ett angivet värde skiljer sig från det föregående i samma serie (servrar; CoreWeave: datorutrustning). Det lägsta värdet blandar punkter och intervall, så en ändring där kan vara en formulering. Märkningarna i avsnitt 3 läser bara det högsta värdet.

- Amazon 2020Q1: högsta 3 → 4 år (known_from 2020-01-31, `useful_life_servers_amzn_hi`)
- Amazon 2020Q1: lägsta 3 → 4 år (known_from 2020-01-31, `useful_life_servers_amzn_lo`)
- Microsoft 2020Q3: högsta 3 → 4 år (known_from 2020-07-30, `useful_life_servers_msft_hi`)
- Microsoft 2020Q3: lägsta 3 → 4 år (known_from 2020-07-30, `useful_life_servers_msft_lo`)
- Alphabet 2021Q1: högsta 3 → 4 år (known_from 2021-02-02, `useful_life_servers_googl_hi`)
- Alphabet 2021Q1: lägsta 3 → 4 år (known_from 2021-02-02, `useful_life_servers_googl_lo`)
- Amazon 2022Q1: högsta 4 → 5 år (known_from 2022-02-04, `useful_life_servers_amzn_hi`)
- Amazon 2022Q1: lägsta 4 → 5 år (known_from 2022-02-04, `useful_life_servers_amzn_lo`)
- Oracle 2022Q2: högsta 4 → 5 år (known_from 2022-09-13, `useful_life_servers_orcl_hi`)
- Oracle 2022Q2: lägsta 4 → 5 år (known_from 2022-09-13, `useful_life_servers_orcl_lo`)
- Microsoft 2022Q3: högsta 4 → 6 år (known_from 2022-07-28, `useful_life_servers_msft_hi`)
- Microsoft 2022Q3: lägsta 4 → 6 år (known_from 2022-07-28, `useful_life_servers_msft_lo`)
- CoreWeave 2023Q1: högsta 5 → 6 år (known_from 2026-03-02, `useful_life_computer_equipment_crwv_hi`)
- CoreWeave 2023Q1: lägsta 5 → 6 år (known_from 2026-03-02, `useful_life_computer_equipment_crwv_lo`)
- Alphabet 2023Q1: högsta 4 → 6 år (known_from 2023-02-02, `useful_life_servers_googl_hi`)
- Alphabet 2023Q1: lägsta 4 → 6 år (known_from 2023-02-02, `useful_life_servers_googl_lo`)
- Amazon 2024Q1: högsta 5 → 6 år (known_from 2024-02-02, `useful_life_servers_amzn_hi`)
- Amazon 2024Q1: lägsta 5 → 6 år (known_from 2024-02-02, `useful_life_servers_amzn_lo`)
- Oracle 2024Q2: högsta 5 → 6 år (known_from 2024-09-10, `useful_life_servers_orcl_hi`)
- Oracle 2024Q2: lägsta 5 → 6 år (known_from 2024-09-10, `useful_life_servers_orcl_lo`)
- Amazon 2025Q4: lägsta 6 → 5 år (known_from 2026-02-06, `useful_life_servers_amzn_lo`)
- Microsoft 2026Q2: lägsta 6 → 2 år (known_from 2026-07-29, `useful_life_servers_msft_lo`)

### 7. Att bevaka

Nästa inlämning per bolag, uppskattad som nästa kvartals slut plus medianen av avståndet för de åtta senaste inlämningarna:

- Oracle: 2026Q4 omkring 2026-12-11 (median -20 dagar, spann -21–-8, senast 2026-09-11)
- Microsoft: 2026Q4 omkring 2027-01-29 (median 29 dagar, spann 28–30, senast 2026-10-28)
- Alphabet: 2026Q4 omkring 2027-01-29 (median 29 dagar, spann 23–36, senast 2026-10-29)
- Amazon: 2026Q4 omkring 2027-01-31 (median 31 dagar, spann 30–38, senast 2026-10-30)
- CoreWeave: 2026Q4 omkring 2027-02-13 (median 44 dagar, spann 38–61, senast 2026-11-12)

Nästa osedda läsning: Oracle 2026Q4 omkring 2026-12-11, bolagsraderna; molnfyrans huvudläsning när alla fyra har lämnat in (uppskattat 2027-01-31).

### 8. Förbehåll

- Med cirka 7 ursprung med X i molnfyrans historik är detta en beskrivning och inget test. Ett mönster kan vara slump, och ett utslag som talar för visar inte orsaken.
- Intäktskravet är härlett med ett antagande: r är ett registrerat intervall och ingen skattning av bolagens kapitalkostnad. Raderna med r = 0, 0,08 och 0,12 visar känsligheten. Drift, el, personal och skatt ingår inte.
- Täljaren är hela bolagets kapital och nämnaren bara molnet eller orderstocken. Gapets nivå är ingen marginal och ingen avkastning. Amazons och Microsofts anläggningstillgångar omfattar mer än molnet. AWS-segmentets egen kvot står i avsnitt 4.
- Definitionerna skiljer sig: Microsoft Cloud innehåller kommersiell Office 365, LinkedIn och Dynamics, Oracles moln innehåller SaaS och Google Cloud innehåller Workspace. Oracles avskrivningar innehåller amortering på immateriella tillgångar, Amazons och Microsofts rader mer än avskrivningar på anläggningstillgångar.
- Regimbrott: ändrade nyttjandeperioder flyttar avskrivningarna utan att kapaciteten ändras (avsnitt 6). Microsofts avskrivningsrad ligger på den gamla basen till och med 2024Q2, så X:s takt till och med 2026Q1 jämför fönster med olika bas för Microsoft och molnfyran (märkt i avsnitt 3).
- RPO är klumpig (till exempel OpenAI hos Oracle) och en balans, medan intäktskravet är ett flöde per år.
- Oracles kvartal slutar en månad före kalenderkvartalet (mittpunktsregeln), och Oracle lämnar in tidigare än de andra.
- CoreWeaves serier börjar 2024, och nettot av anläggningstillgångar först 2024Q4. Bolagsraden har därför få kvartal.
- Labbens run-rate är inte redovisad intäkt. Anthropics redovisade tal kommer ur registreringsprospektet (AN1) och står bara som beskrivning i avsnitt 5. OpenAI är BLOCKED.

## Betalningsgapet per 2025-11-27

**Frågan:** Växer de intäkter som ska bära investeringarna (molnintäkter, AI-nyckeltal, RPO och frontlabbens intäkter) i takt med intäktskravet från avskrivningar och kapitalkostnad, eller öppnas eller sluts gapet?

Intäktskrav = avskrivningar över fyra kvartal + r × anläggningstillgångar netto vid kvartalets slut (hela bolaget, bara kapitalet). Bärande intäkter = molnintäkter över fyra kvartal (Microsoft Cloud, Google Cloud, AWS, Oracles moln, CoreWeaves intäkter) eller RPO vid kvartalets slut. Gapet = 100 × intäktskrav / bärande intäkter. Molnfyran = Microsoft, Alphabet, Amazon och Oracle, som summor av komponenterna. Takt = årsförändring i log × 100, så gapets takt är intäktskravets takt minus intäkternas: positiv = gapet öppnas, negativ = gapet sluts. Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1. Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-26 BG1.

### 1. Molnfyran: intäktskrav, bärande intäkter och investeringstakt

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| krav(molnfyran, r=0,10) | 210,8 mdr | +30,9 | +6,9 | +2,6 | 2025Q3 | 2025-10-31 | `krav(molnfyran, r=0,10)` |
| krav(molnfyran, r=0,00) | 127,6 mdr | +27,1 | +7,4 | +3,0 | 2025Q3 | 2025-10-31 | `krav(molnfyran, r=0,00)` |
| moln(molnfyran) | 380,1 mdr | +20,7 | +1,2 | +0,7 | 2025Q3 | 2025-10-31 | `moln(molnfyran)` |
| rpo(molnfyran) | 1 211,0 mdr | +67,6 | +39,4 | +32,1 | 2025Q3 | 2025-10-31 | `rpo(molnfyran)` |
| capex4(molnfyran) | 294,4 mdr | +51,2 | +0,7 | -0,6 | 2025Q3 | 2025-10-31 | `capex4(molnfyran)` |

**Gapet** (procent av molnintäkterna respektive av RPO):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| gap_moln(molnfyran, r=0,10) | 55,5 % | +10,2 | +5,7 | +1,9 | 2025Q3 | 2025-10-31 | `gap_moln(molnfyran, r=0,10)` |
| gap_moln(molnfyran, r=0,00) | 33,6 % | +6,4 | +6,1 | +2,3 | 2025Q3 | 2025-10-31 | `gap_moln(molnfyran, r=0,00)` |
| gap_moln(molnfyran, r=0,08) | 51,1 % | +9,7 | +5,7 | +2,0 | 2025Q3 | 2025-10-31 | `gap_moln(molnfyran, r=0,08)` |
| gap_moln(molnfyran, r=0,12) | 59,8 % | +10,6 | +5,6 | +1,8 | 2025Q3 | 2025-10-31 | `gap_moln(molnfyran, r=0,12)` |
| gap_rpo(molnfyran, r=0,10) | 17,4 % | -36,7 | -32,5 | -29,6 | 2025Q3 | 2025-10-31 | `gap_rpo(molnfyran, r=0,10)` |
| gap_rpo(molnfyran utan Oracle, r=0,10) | 26,3 % | -7,3 | -7,6 | -1,3 | 2025Q3 | 2025-10-31 | `gap_rpo(molnfyran utan Oracle, r=0,10)` |

Nästa kvartal (2025Q4) för molnfyran saknar på dagen: `dep_msft 2025Q4`, `dep_googl 2025Q4`, `dep_amzn 2025Q4`, `dep_orcl 2025Q4`, `ppe_net_msft 2025Q4`, `ppe_net_googl 2025Q4`, `ppe_net_amzn 2025Q4`, `ppe_net_orcl 2025Q4`, `rev_msft_cloud 2025Q4`, `rev_google_cloud 2025Q4`, `rev_aws 2025Q4`, `rev_orcl_cloud 2025Q4`.

### 2. Per bolag (r = 0,10)

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| gap_moln(Microsoft, r=0,10) | 35,1 % | +21,4 | +0,5 | +2,8 | 2025Q3 | 2025-10-29 | `gap_moln(Microsoft, r=0,10)` |
| gap_moln(Alphabet, r=0,10) | 78,6 % | +4,1 | +5,2 | +1,6 | 2025Q3 | 2025-10-30 | `gap_moln(Alphabet, r=0,10)` |
| gap_moln(Amazon, r=0,10) | 77,4 % | +6,4 | +6,9 | +0,9 | 2025Q3 | 2025-10-31 | `gap_moln(Amazon, r=0,10)` |
| gap_moln(Oracle, r=0,10) | 45,4 % | +11,5 | +18,2 | +5,0 | 2025Q3 | 2025-09-10 | `gap_moln(Oracle, r=0,10)` |
| gap_moln(CoreWeave, r=0,10) | – | – | – | – | – | – | `gap_moln(CoreWeave, r=0,10)` |

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| gap_rpo(Microsoft, r=0,10) | 15,8 % | +2,4 | -9,5 | +5,3 | 2025Q3 | 2025-10-29 | `gap_rpo(Microsoft, r=0,10)` |
| gap_rpo(Alphabet, r=0,10) | 26,4 % | -28,6 | -29,9 | -27,5 | 2025Q3 | 2025-10-30 | `gap_rpo(Alphabet, r=0,10)` |
| gap_rpo(Amazon, r=0,10) | 47,2 % | +3,4 | +5,2 | +4,4 | 2025Q3 | 2025-10-31 | `gap_rpo(Amazon, r=0,10)` |
| gap_rpo(Oracle, r=0,10) | 2,6 % | -118,2 | -83,0 | -105,2 | 2025Q3 | 2025-09-10 | `gap_rpo(Oracle, r=0,10)` |
| gap_rpo(CoreWeave, r=0,10) | – | – | – | – | – | – | `gap_rpo(CoreWeave, r=0,10)` |

Komponenterna per bolag:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| krav(Microsoft, r=0,10) | 62,9 mdr | +42,7 | +2,5 | +3,5 | 2025Q3 | 2025-10-29 | `krav(Microsoft, r=0,10)` |
| moln(Microsoft) | 179,1 mdr | +21,3 | +2,0 | +0,8 | 2025Q3 | 2025-10-29 | `moln(Microsoft)` |
| rpo(Microsoft) | 398,0 mdr | +40,3 | +12,0 | -1,8 | 2025Q3 | 2025-10-29 | `rpo(Microsoft)` |
| capex4(Microsoft) | 69,0 mdr | +33,3 | -10,6 | -2,6 | 2025Q3 | 2025-10-29 | `capex4(Microsoft)` |
| krav(Alphabet, r=0,10) | 41,7 mdr | +31,1 | +5,6 | +2,3 | 2025Q3 | 2025-10-30 | `krav(Alphabet, r=0,10)` |
| moln(Alphabet) | 53,0 mdr | +27,0 | +0,4 | +0,7 | 2025Q3 | 2025-10-30 | `moln(Alphabet)` |
| rpo(Alphabet) | 157,7 mdr | +59,7 | +35,5 | +29,7 | 2025Q3 | 2025-10-30 | `rpo(Alphabet)` |
| capex4(Alphabet) | 77,9 mdr | +45,8 | +3,9 | +4,7 | 2025Q3 | 2025-10-30 | `capex4(Alphabet)` |
| krav(Amazon, r=0,10) | 94,4 mdr | +23,3 | +7,0 | +1,4 | 2025Q3 | 2025-10-31 | `krav(Amazon, r=0,10)` |
| moln(Amazon) | 121,9 mdr | +16,9 | +0,0 | +0,5 | 2025Q3 | 2025-10-31 | `moln(Amazon)` |
| rpo(Amazon) | 200,0 mdr | +19,8 | +1,7 | -3,0 | 2025Q3 | 2025-10-31 | `rpo(Amazon)` |
| capex4(Amazon) | 120,1 mdr | +54,4 | -1,1 | -3,8 | 2025Q3 | 2025-10-31 | `capex4(Amazon)` |
| krav(Oracle, r=0,10) | 11,8 mdr | +34,3 | +21,0 | +5,8 | 2025Q3 | 2025-09-10 | `krav(Oracle, r=0,10)` |
| moln(Oracle) | 26,1 mdr | +22,8 | +2,8 | +0,8 | 2025Q3 | 2025-09-10 | `moln(Oracle)` |
| rpo(Oracle) | 455,3 mdr | +152,5 | +104,0 | +111,0 | 2025Q3 | 2025-09-10 | `rpo(Oracle)` |
| capex4(Oracle) | 27,4 mdr | +125,0 | +33,5 | -2,6 | 2025Q3 | 2025-09-10 | `capex4(Oracle)` |
| krav(CoreWeave, r=0,10) | – | – | – | – | – | – | `krav(CoreWeave, r=0,10)` |
| moln(CoreWeave) | – | – | – | – | – | – | `moln(CoreWeave)` |
| rpo(CoreWeave) | 50,0 mdr | – | – | – | 2025Q3 | 2025-11-13 | `rpo(CoreWeave)` |
| capex4(CoreWeave) | – | – | – | – | – | – | `capex4(CoreWeave)` |

### 3. Läsregeln, mekaniskt

F0:s symmetriska regel, en rad per X. X = gapets takt (gräns ±5 log × 100 per år), Y = förändring i capex-takt för samma bolag (gräns ±5), fönster 2 kvartal, tecken −. Gapet öppnas (X ≥ +5) och capex-takten faller med minst 5 först: talar för. Gapet sluts (X ≤ −5) och capex-takten stiger med minst 5 först: talar för. Motsatt rörelse först: talar emot. Håller capex-takten sig inom ±5: inget av mönstren, så regeln skiljer inte "stöder fortsatt takt" från "ingen effekt". Utslaget är en beskrivning, inget test.

Intäktskravet innehåller capex (nettot växer med investeringarna, avskrivningarna följer efter). En uthållig acceleration i capex höjer därför både X och Y och läses som talar emot. Ett utslag som talar emot är ett svagare belägg mot mekanismen än ett som talar för är belägg för den. Raden med r = 0 är minst direkt kopplad.

Alla läsningar nedan vilar bara på värden som var kända före registerposten 2026-11-26, och P2b:s kvoter och KL1:s capex-takt för de inre bolagen var sedda före posten (posten, avsnitt (e)). Ingen av läsningarna är därför ett utfall på osedda data. Den första osedda läsningen kommer med inlämningar efter 2026-11-26 (avsnitt 7). Sedda data avgörs per läsning (X25, punkt 1).

- **Huvudläsning: gapet mot molnintäkterna, molnfyran, r = 0,10:** kan inte avgöras. t = 2025Q3; ursprung 2025Q2, X +8,0 (gräns ±5,0), uppgång (fönstret öppet till 2025Q4). X = gap_moln(molnfyran, r=0,10) (takt), Y = capex4(molnfyran) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 3 ursprung med X (2024Q4–2025Q2). Impulser uppåt 1 (för 0, emot 0, inget 0, kan inte avgöras 1), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 2 av 3 ursprung, och 0 av 1 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 2 av 3; med den nya: 2 av 3.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-26, och den är därför inget utfall på osedda data.
  Märkning: nyttjandeperioden för Amazon ändrades 2024Q1 (5 → 6 år, högsta värdet, known_from 2024-02-02).
  Märkning: nyttjandeperioden för Oracle ändrades 2024Q2 (5 → 6 år, högsta värdet, known_from 2024-09-10).
  Märkning: Microsofts avskrivningar i fönstret 2023Q3–2025Q2 har kvartal på den gamla basen (till och med 2024Q2).
- **Gapet mot RPO, molnfyran, r = 0,10:** inget av mönstren. t = 2025Q3 (ingen impuls i fönstret). X = gap_rpo(molnfyran, r=0,10) (takt), Y = capex4(molnfyran) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 3 ursprung med X (2024Q4–2025Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 3.
  Y var känt i hela fönstret i 2 av 3 ursprung, och 0 av 0 impulser kunde läsas mot Y. Ingen riktning har prövats: X har inte haft någon impuls.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 3 av 3; med den nya: 2 av 3.
- **Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,00 (bara avskrivningar):** inget av mönstren. t = 2025Q3 (ingen impuls i fönstret). X = gap_moln(molnfyran, r=0,00) (takt), Y = capex4(molnfyran) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 3 ursprung med X (2024Q4–2025Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 3.
  Y var känt i hela fönstret i 2 av 3 ursprung, och 0 av 0 impulser kunde läsas mot Y. Ingen riktning har prövats: X har inte haft någon impuls.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 3 av 3; med den nya: 2 av 3.
- **Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,08:** kan inte avgöras. t = 2025Q3; ursprung 2025Q2, X +7,4 (gräns ±5,0), uppgång (fönstret öppet till 2025Q4). X = gap_moln(molnfyran, r=0,08) (takt), Y = capex4(molnfyran) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 3 ursprung med X (2024Q4–2025Q2). Impulser uppåt 1 (för 0, emot 0, inget 0, kan inte avgöras 1), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 2 av 3 ursprung, och 0 av 1 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 2 av 3; med den nya: 2 av 3.
  Märkning: nyttjandeperioden för Amazon ändrades 2024Q1 (5 → 6 år, högsta värdet, known_from 2024-02-02).
  Märkning: nyttjandeperioden för Oracle ändrades 2024Q2 (5 → 6 år, högsta värdet, known_from 2024-09-10).
  Märkning: Microsofts avskrivningar i fönstret 2023Q3–2025Q2 har kvartal på den gamla basen (till och med 2024Q2).
- **Känslighet: gapet mot molnintäkterna, molnfyran, r = 0,12:** kan inte avgöras. t = 2025Q3; ursprung 2025Q2, X +8,4 (gräns ±5,0), uppgång (fönstret öppet till 2025Q4). X = gap_moln(molnfyran, r=0,12) (takt), Y = capex4(molnfyran) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 3 ursprung med X (2024Q4–2025Q2). Impulser uppåt 1 (för 0, emot 0, inget 0, kan inte avgöras 1), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 2 av 3 ursprung, och 0 av 1 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 2 av 3; med den nya: 2 av 3.
  Märkning: nyttjandeperioden för Amazon ändrades 2024Q1 (5 → 6 år, högsta värdet, known_from 2024-02-02).
  Märkning: nyttjandeperioden för Oracle ändrades 2024Q2 (5 → 6 år, högsta värdet, known_from 2024-09-10).
  Märkning: Microsofts avskrivningar i fönstret 2023Q3–2025Q2 har kvartal på den gamla basen (till och med 2024Q2).
- **Känslighet: gapet mot RPO utan Oracle, r = 0,10:** inget av mönstren. t = 2025Q3 (ingen impuls i fönstret). X = gap_rpo(molnfyran utan Oracle, r=0,10) (takt), Y = capex4(molnfyran utan Oracle) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 3 ursprung med X (2024Q4–2025Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 3.
  Y var känt i hela fönstret i 2 av 3 ursprung, och 0 av 0 impulser kunde läsas mot Y. Ingen riktning har prövats: X har inte haft någon impuls.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 3 av 3; med den nya: 2 av 3.

**Bolagsrader** (bisak, samma gränser, Y = bolagets egen capex-takt):

- **Microsoft: gapet mot molnintäkterna:** talar för mekanismen. t = 2025Q3; ursprung 2025Q2, X +21,7 (gräns ±5,0), uppgång, Y -10,6 vid 2025Q3 (gräns ±5,0). X = gap_moln(Microsoft, r=0,10) (takt), Y = capex4(Microsoft) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 13 av 13 ursprung med X (2022Q2–2025Q2). Impulser uppåt 6 (för 3, emot 1, inget 2, kan inte avgöras 0), nedåt 6 (för 4, emot 2, inget 0, kan inte avgöras 0), utan impuls 1.
  Y var känt i hela fönstret i 12 av 13 ursprung, och 12 av 12 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 13 av 13; med den nya: 13 av 13.
  Märkning: Microsofts avskrivningar i fönstret 2023Q3–2025Q2 har kvartal på den gamla basen (till och med 2024Q2).
- **Microsoft: gapet mot RPO:** talar för mekanismen. t = 2025Q3; ursprung 2025Q2, X +11,2 (gräns ±5,0), uppgång, Y -10,6 vid 2025Q3 (gräns ±5,0). X = gap_rpo(Microsoft, r=0,10) (takt), Y = capex4(Microsoft) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 28 av 28 ursprung med X (2018Q3–2025Q2). Impulser uppåt 7 (för 3, emot 2, inget 2, kan inte avgöras 0), nedåt 18 (för 7, emot 7, inget 4, kan inte avgöras 0), utan impuls 3.
  Y var känt i hela fönstret i 27 av 28 ursprung, och 25 av 25 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 28 av 28; med den nya: 28 av 28.
  Märkning: Microsofts avskrivningar i fönstret 2023Q3–2025Q2 har kvartal på den gamla basen (till och med 2024Q2).
- **Alphabet: gapet mot molnintäkterna:** inget av mönstren. t = 2025Q3 (ingen impuls i fönstret). X = gap_moln(Alphabet, r=0,10) (takt), Y = capex4(Alphabet) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 3 ursprung med X (2024Q4–2025Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 3.
  Y var känt i hela fönstret i 2 av 3 ursprung, och 0 av 0 impulser kunde läsas mot Y. Ingen riktning har prövats: X har inte haft någon impuls.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 3 av 3; med den nya: 2 av 3.
- **Alphabet: gapet mot RPO:** inget av mönstren. t = 2025Q3 (ingen impuls i fönstret). X = gap_rpo(Alphabet, r=0,10) (takt), Y = capex4(Alphabet) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 3 ursprung med X (2024Q4–2025Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 3.
  Y var känt i hela fönstret i 2 av 3 ursprung, och 0 av 0 impulser kunde läsas mot Y. Ingen riktning har prövats: X har inte haft någon impuls.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 3 av 3; med den nya: 2 av 3.
- **Amazon: gapet mot molnintäkterna:** inget av mönstren. t = 2025Q3 (ingen impuls i fönstret). X = gap_moln(Amazon, r=0,10) (takt), Y = capex4(Amazon) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 18 av 19 ursprung med X (2020Q4–2025Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 4 (för 1, emot 3, inget 0, kan inte avgöras 0), utan impuls 15.
  Y var känt i hela fönstret i 18 av 19 ursprung, och 4 av 4 impulser kunde läsas mot Y. Riktningen uppåt har inte prövats: X har inte haft någon impuls uppåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 19 av 19; med den nya: 18 av 19.
- **Amazon: gapet mot RPO:** inget av mönstren. t = 2025Q3 (ingen impuls i fönstret). X = gap_rpo(Amazon, r=0,10) (takt), Y = capex4(Amazon) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 18 av 19 ursprung med X (2020Q4–2025Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 16 (för 5, emot 11, inget 0, kan inte avgöras 0), utan impuls 3.
  Y var känt i hela fönstret i 18 av 19 ursprung, och 16 av 16 impulser kunde läsas mot Y. Riktningen uppåt har inte prövats: X har inte haft någon impuls uppåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 19 av 19; med den nya: 18 av 19.
- **Oracle: gapet mot molnintäkterna:** talar för mekanismen. t = 2025Q3; ursprung 2025Q1, X -6,7 (gräns ±5,0), nedgång, Y +69,0 vid 2025Q2 (gräns ±5,0). X = gap_moln(Oracle, r=0,10) (takt), Y = capex4(Oracle) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 8 av 9 ursprung med X (2023Q2–2025Q2). Impulser uppåt 2 (för 2, emot 0, inget 0, kan inte avgöras 0), nedåt 5 (för 4, emot 1, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 8 av 9 ursprung, och 7 av 7 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 9 av 9; med den nya: 8 av 9.
  Märkning: nyttjandeperioden för Oracle ändrades 2024Q2 (5 → 6 år, högsta värdet, known_from 2024-09-10).
- **Oracle: gapet mot RPO:** talar för mekanismen. t = 2025Q3; ursprung 2025Q2, X -10,3 (gräns ±5,0), nedgång, Y +33,5 vid 2025Q3 (gräns ±5,0). X = gap_rpo(Oracle, r=0,10) (takt), Y = capex4(Oracle) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 24 av 24 ursprung med X (2019Q3–2025Q2). Impulser uppåt 4 (för 4, emot 0, inget 0, kan inte avgöras 0), nedåt 11 (för 10, emot 1, inget 0, kan inte avgöras 0), utan impuls 9.
  Y var känt i hela fönstret i 23 av 24 ursprung, och 15 av 15 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 24 av 24; med den nya: 24 av 24.
  Märkning: nyttjandeperioden för Oracle ändrades 2024Q2 (5 → 6 år, högsta värdet, known_from 2024-09-10).
- **CoreWeave: gapet mot molnintäkterna:** kan inte avgöras. t = – (capex4(CoreWeave): inget kvartal känt på dagen). X = gap_moln(CoreWeave, r=0,10) (takt), Y = capex4(CoreWeave) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
- **CoreWeave: gapet mot RPO:** kan inte avgöras. t = – (capex4(CoreWeave): inget kvartal känt på dagen). X = gap_rpo(CoreWeave, r=0,10) (takt), Y = capex4(CoreWeave) (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.

### 4. Sammanhang

**P2b:s avstämningar** (hyp4 mot totala intäkter, AWS-segmentet och RPO mot capex; katalogserier):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| x_dep_rev | 8,89 | +14,5 | +4,2 | +1,7 | 2025Q3 | 2025-10-31 | `x_dep_rev` |
| x_capcost_rev_r08 | 13,71 | +17,0 | +3,9 | +1,3 | 2025Q3 | 2025-10-31 | `x_capcost_rev_r08` |
| x_capcost_rev_r12 | 16,12 | +17,7 | +3,9 | +1,2 | 2025Q3 | 2025-10-31 | `x_capcost_rev_r12` |
| x_dep_rev_aws | 15,37 | – | – | – | 2025Q3 | 2025-10-31 | `x_dep_rev_aws` |
| x_rpo_cover | 3,67 | +17,1 | +37,3 | +32,2 | 2025Q3 | 2025-10-31 | `x_rpo_cover` |

**RPO på kort sikt** (andelen inom 12 eller 24 månader enligt bolaget, belopp ungefärliga):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| rpo_msft_12m | 159,2 mdr | +28,5 | +12,0 | +1,1 | 2025Q3 | 2025-10-29 | `rpo_msft_12m` |
| rpo_orcl_12m | 45,5 mdr | +19,0 | +3,2 | -4,2 | 2025Q3 | 2025-09-10 | `rpo_orcl_12m` |
| rpo_googl_24m | 86,7 mdr | +69,2 | +35,5 | +27,4 | 2025Q3 | 2025-10-30 | `rpo_googl_24m` |
| rpo_crwv_24m | 21,0 mdr | – | – | – | 2025Q3 | 2025-11-13 | `rpo_crwv_24m` |

Oracles andel av molnfyrans RPO vid 2025Q3: **37,6 %**. RPO är klumpig: enstaka mycket stora avtal flyttar ett kvartal, och raden utan Oracle i avsnitt 3 visar hur mycket Oracle betyder.

Bolagens guidance för molnintäkter finns inte i katalogen, så B1 är enda baslinjen för intäkterna.

### 5. AI-nyckeltal och labbens intäkter (tabellrader, ingår inte i regeln)

- Microsoft: Azure and other cloud services, tillväxt å/å (definition FY25–FY26): **40,0 %** (2025Q3; före: 39,0 % (2025Q2)); 9 värden, known_from 2025-10-29, `kpi_msft_azure_growth_v2`
- Microsoft: Azure, tillväxt å/å (definition från FY27): inget värde känt på dagen (`kpi_msft_azure_growth_v3`)
- Microsoft: Azure, tillväxt å/å i konstant valuta (definition från FY27): inget värde känt på dagen (`kpi_msft_azure_growth_cc_v3`)
- Microsoft: AI-verksamhetens intäkt i årstakt: **13,0 mdr** (2024-12); 1 värde, known_from 2025-01-29, `kpi_msft_ai_business_runrate`
- Amazon: AWS AI-verksamhet, intäkt i årstakt: inget värde känt på dagen (`kpi_amzn_aws_ai_runrate`)
- Alphabet: Google Clouds orderstock (backlog): **155,0 mdr** (2025-09); 1 värde, known_from 2025-10-29, `kpi_googl_cloud_backlog`
- Anthropic, run-rate revenue, hela bolaget (rapporterad): **7,0 mdr** (2025-10-21; före: 5,0 mdr (2025-08-31)); 4 värden, known_from 2025-10-21, `lab_rev_anthropic_company_run_rate`
- Anthropic, Run-Rate Revenue enligt S-1, hela bolaget (rapporterad): inget värde känt på dagen (`lab_rev_anthropic_company_run_rate_s1`)
- Anthropic, run-rate revenue, Claude Code (produkt) (rapporterad): **0,5 mdr** (2025-09-02); 1 värde, known_from 2025-09-02, `lab_rev_anthropic_claude_code_run_rate`

AI-nyckeltalen är oregelbundna och har definitionsbrott (Azure v1–v3). Run-rate är bolagets egen årstakt vid en tidpunkt och inte redovisad intäkt, och den blandas inte med GAAP-tal.

**Anthropics redovisade tal (GAAP, ur S-1, S-1/A och 424B4; registret 2026-11-27 AN1):**

- Anthropic, intäkter, per kvartal (GAAP, redovisad): inget värde känt på dagen (`lab_gaap_anthropic_revenue_q`)
- Anthropic, intäkter, per år (GAAP, redovisad): inget värde känt på dagen (`lab_gaap_anthropic_revenue_a`)
- Anthropic, rörelseresultat, per kvartal (GAAP, redovisad): inget värde känt på dagen (`lab_gaap_anthropic_opinc_q`)
- Anthropic, kassaflöde från den löpande verksamheten, hittills i år (GAAP, redovisad): inget värde känt på dagen (`lab_gaap_anthropic_cfo_ytd`)

Inga redovisade kvartal kända på dagen.

- **BLOCKED:** OpenAI: ingen registreringsansökan på EDGAR, och openai.com nekas av proxyn (docs/kallor/labbintakter.md).

### 6. Nyttjandeperioder (regimmarkörer)

Kvartal där ett angivet värde skiljer sig från det föregående i samma serie (servrar; CoreWeave: datorutrustning). Det lägsta värdet blandar punkter och intervall, så en ändring där kan vara en formulering. Märkningarna i avsnitt 3 läser bara det högsta värdet.

- Amazon 2020Q1: högsta 3 → 4 år (known_from 2020-01-31, `useful_life_servers_amzn_hi`)
- Amazon 2020Q1: lägsta 3 → 4 år (known_from 2020-01-31, `useful_life_servers_amzn_lo`)
- Microsoft 2020Q3: högsta 3 → 4 år (known_from 2020-07-30, `useful_life_servers_msft_hi`)
- Microsoft 2020Q3: lägsta 3 → 4 år (known_from 2020-07-30, `useful_life_servers_msft_lo`)
- Alphabet 2021Q1: högsta 3 → 4 år (known_from 2021-02-02, `useful_life_servers_googl_hi`)
- Alphabet 2021Q1: lägsta 3 → 4 år (known_from 2021-02-02, `useful_life_servers_googl_lo`)
- Amazon 2022Q1: högsta 4 → 5 år (known_from 2022-02-04, `useful_life_servers_amzn_hi`)
- Amazon 2022Q1: lägsta 4 → 5 år (known_from 2022-02-04, `useful_life_servers_amzn_lo`)
- Oracle 2022Q2: högsta 4 → 5 år (known_from 2022-09-13, `useful_life_servers_orcl_hi`)
- Oracle 2022Q2: lägsta 4 → 5 år (known_from 2022-09-13, `useful_life_servers_orcl_lo`)
- Microsoft 2022Q3: högsta 4 → 6 år (known_from 2022-07-28, `useful_life_servers_msft_hi`)
- Microsoft 2022Q3: lägsta 4 → 6 år (known_from 2022-07-28, `useful_life_servers_msft_lo`)
- Alphabet 2023Q1: högsta 4 → 6 år (known_from 2023-02-02, `useful_life_servers_googl_hi`)
- Alphabet 2023Q1: lägsta 4 → 6 år (known_from 2023-02-02, `useful_life_servers_googl_lo`)
- Amazon 2024Q1: högsta 5 → 6 år (known_from 2024-02-02, `useful_life_servers_amzn_hi`)
- Amazon 2024Q1: lägsta 5 → 6 år (known_from 2024-02-02, `useful_life_servers_amzn_lo`)
- Oracle 2024Q2: högsta 5 → 6 år (known_from 2024-09-10, `useful_life_servers_orcl_hi`)
- Oracle 2024Q2: lägsta 5 → 6 år (known_from 2024-09-10, `useful_life_servers_orcl_lo`)

### 7. Att bevaka

Nästa inlämning per bolag, uppskattad som nästa kvartals slut plus medianen av avståndet för de åtta senaste inlämningarna:

- Oracle: 2025Q4 omkring 2025-12-12 (median -19 dagar, spann -21–-10, senast 2025-09-10)
- Alphabet: 2025Q4 omkring 2026-01-28 (median 28 dagar, spann 24–36, senast 2025-10-30)
- Microsoft: 2025Q4 omkring 2026-01-30 (median 30 dagar, spann 25–30, senast 2025-10-29)
- Amazon: 2025Q4 omkring 2026-02-01 (median 32 dagar, spann 31–38, senast 2025-10-31)
- CoreWeave: 2025Q4 omkring 2026-02-13 (median 44 dagar, spann 44–45, senast 2025-11-13)

Nästa osedda läsning: med inlämningar efter 2026-11-26 (inga uppskattade ännu).

### 8. Förbehåll

- Med cirka 7 ursprung med X i molnfyrans historik är detta en beskrivning och inget test. Ett mönster kan vara slump, och ett utslag som talar för visar inte orsaken.
- Intäktskravet är härlett med ett antagande: r är ett registrerat intervall och ingen skattning av bolagens kapitalkostnad. Raderna med r = 0, 0,08 och 0,12 visar känsligheten. Drift, el, personal och skatt ingår inte.
- Täljaren är hela bolagets kapital och nämnaren bara molnet eller orderstocken. Gapets nivå är ingen marginal och ingen avkastning. Amazons och Microsofts anläggningstillgångar omfattar mer än molnet. AWS-segmentets egen kvot står i avsnitt 4.
- Definitionerna skiljer sig: Microsoft Cloud innehåller kommersiell Office 365, LinkedIn och Dynamics, Oracles moln innehåller SaaS och Google Cloud innehåller Workspace. Oracles avskrivningar innehåller amortering på immateriella tillgångar, Amazons och Microsofts rader mer än avskrivningar på anläggningstillgångar.
- Regimbrott: ändrade nyttjandeperioder flyttar avskrivningarna utan att kapaciteten ändras (avsnitt 6). Microsofts avskrivningsrad ligger på den gamla basen till och med 2024Q2, så X:s takt till och med 2026Q1 jämför fönster med olika bas för Microsoft och molnfyran (märkt i avsnitt 3).
- RPO är klumpig (till exempel OpenAI hos Oracle) och en balans, medan intäktskravet är ett flöde per år.
- Oracles kvartal slutar en månad före kalenderkvartalet (mittpunktsregeln), och Oracle lämnar in tidigare än de andra.
- CoreWeaves serier börjar 2024, och nettot av anläggningstillgångar först 2024Q4. Bolagsraden har därför få kvartal.
- Labbens run-rate är inte redovisad intäkt. Anthropics redovisade tal kommer ur registreringsprospektet (AN1) och står bara som beskrivning i avsnitt 5. OpenAI är BLOCKED.
