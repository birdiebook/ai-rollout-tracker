# R28 – oberoende granskning av körning 16 (antenner: F0, LT1, BG1, EL1)

Granskningsspår R28, 2026-11-26, gren `auto16/r28-antenner` (bas `auto16/integration16`, `ff072b8`). R28 har inte
skrivit koden, registerposterna eller rapporterna och har inte läst byggarnas slutsatser före granskningen. Utgångspunkten
var att ett påstående är fel tills det gick att visa ur koden, registret, observationstabellen eller källdokumentet.

Underlag: koden i `src/ai_tracker/followed/` (`common`, `aggregate`, `antenner`, `ledtid`, `betalningsgapet`,
`elflaskhalsen`, `kreditlagret`) och `src/ai_tracker/series/ledtid.py`, de fyra registerposterna 2026-11-26 i
`docs/mattregister.md`, observationstabellen i huvudutcheckningen (854 serier, hämtad 2026-11-26) och 15 dokument som
hämtades på nytt från www.sec.gov (8-K, exhibit 99; den generiska klientidentiteten ur `.env`, en begäran i taget, inget
403 eller 429, inget sparat i den delade cachen). Ingen produktionskod och inga dokument från spåren är ändrade. Testerna
står i `tests/test_r28_antenner.py`: fastlåsta registerposter och stickprovsrader, en egenskap som håller (regelns
symmetri) och fynden R28-1 till R28-3 som `xfail(strict=True)`.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering | **OK.** Varje registerpost är committad ensam och före frågans modul, tester och rapport. Texten i posterna är oförändrad sedan dess, också genom mergarna. Koden gör det posterna säger, med en avvikelse i ordalydelse (R28-8) |
| 2. KL1 oförändrad | **OK.** Rapporten per 2026-11-25 och 2025-11-25 är byte för byte densamma på `main` (`8d804df`) och i integrationen |
| 3. Läckage | **OK.** Alla tre frågorna ger samma rapport (JSON och Markdown) på hela tabellen och på tabellen kapad vid 2025-11-26. Räkenskapsår mappas till kalenderkvartal i källserierna |
| 4. Neutralitet | **OK i koden, ensidigt i data.** F0:s regel är exakt symmetrisk (400 slumpade speglingar). Inga larmord. I EL1 och BG1 har huvudläsningen bara haft impulser uppåt (R28-5), och LT1 och EL1 läser samma par med motsatt tecken (R28-4) |
| 5. Omräkning | **Rätt.** Fem eller fler värden och huvudutslaget per fråga räknade om med egen kod direkt ur `observations.parquet`, utan projektets moduler. Alla stämmer på avrundningen |
| 6. Stickprov av `ob_*` | **15 av 15 rätt** mot 8-K på sec.gov. Två anmärkningar om vad talen innehåller (R28-9) |
| 7. Ärlighet | **Bra, med tre fel.** Förbehållet om sedda data slås av för tidigt (R28-1). LT1:s resultatdokument anger fel riktning för förvärvseffekten i huvudläsningen (R28-2). Antennens kolumn "ändrat" visar en ändring som inte är en (R28-3). Run-rate kallas inte redovisad intäkt, och `publish=False` och licensklass stämmer |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Inget must_fix. Fem should_fix (R28-1 till R28-5) och sex anmärkningar. Inget
fynd ändrar ett utslag per 2026-11-26. R28-1 och R28-2 bör rättas före den första osedda läsningen (Dell omkring
2026-12-09, Oracle omkring 2026-12-11), eftersom de gäller hur utslagen ska läsas.

## 1. Förregistrering

Ordningen i git (`git log --follow`, tider i UTC):

| Spår | Registerpost | Första kod | Rapport |
|---|---|---|---|
| F0 | `4d2e13f` 21:29:48, bara `docs/mattregister.md` | `f4b9f4a` 21:35:21 | – |
| LT1 | `6fb0ccd` 21:51:21, bara registret | `4b9cdf9` 21:58:16 | `87dcd10` 22:08:53 |
| BG1 | `12d9581` 21:52:02, bara registret | `be8dc8f` 21:55:51 | `ed48ced` 22:05:26 |
| EL1 | `f8f0046` 22:18:35, bara registret | `1f581e0` 22:23:00 | `5e649c0` 22:32:06 |

R28 jämförde de rader som de fyra registercommitarna lade till med de rader som `main..HEAD` lägger till i registret.
De är identiska (ingen rad tillkom, ingen försvann), så posterna ändrades inte i mergarna eller efter att data räknats.
Inga andra commitar på spårens grenar rör registret.

**Är posterna anpassade efter utslag?** Det går inte att utesluta helt, men posterna säger själva vad som var sett, och
det stämmer med vad R28 kan kontrollera. LT1 (e) och EL1 (f) anger att inre lagrets förändring i capex-takt (+6,2 vid
2026Q2 och +9,6 vid 2026Q3) var sedd. Med *h* = 5, KL1:s gräns, var det därmed givet att Y når gränsen uppåt i de två
senaste kvartalen. EL1 skrev uttryckligen att huvudläsningen därför "sannolikt blir talar emot". Det blev den. LT1:s val
av huvudläsning (L1 före K-inre, tecken +) gör samma kända Y till "talar för" om L1 har en impuls uppåt. Båda posterna
säger att läsningarna per 2026-11-26 inte är utfall på osedda data, och resultatdokumenten upprepar det. Gränserna är
runda tal som också används för KL1 (5) och som motiveras före data (10 för orderstock). R28 hittade inget som tyder på
att en gräns valts för att flytta ett utslag.

**Gör koden det posten säger?** R28 läste varje parameter i koden mot posten:
- F0: regeln i `common.read_rule` och `origin_outcome` följer (b) punkt för punkt, också läsdagens utslag (det senaste
  ursprunget med impuls bland *t* − *k* … *t* − 1) och räkningen av hur ofta regeln kunde prövas. Antennerna följer (c).
- LT1: *g* = *h* = 5 för köparna och 10 för leverantörerna i båda rollerna (`limits`), *k* = 2 och 4, tecken +, X och Y
  som förändring i takt, 24 läsningar (5 × 2 × 2 mot K-inre och 2 × 2 för L1 mot K-yttre), O1 som 100 × ln(1 + v/100)
  utan överraskning, förvärvsmärket vid *a*, *a* + 1, *a* + 4 och *a* + 5 (rätt: förändringen i takt flyttas åt ett håll
  vid *a* och *a* + 1 och åt andra hållet vid *a* + 4 och *a* + 5, och tar ut sig vid *a* + 2 och *a* + 3). Avvikelse i
  märkningen för "efter": R28-8.
- BG1: krav, moln, rpo, gap och capex4 som summor av komponenterna, *r* = 0,10 med känslighet 0, 0,08 och 0,12, *g* = *h*
  = 5, *k* = 2, tecken −, raderna 1–5 i posten, regimmarkören för `_hi` i *q* − 7 … *q* och Microsofts gamla bas till
  och med 2024Q2.
- EL1: tolvmånadersmedel som slutar med kvartalets sista månad och kräver alla tolv månader (för lasten i alla fem
  områdena), Dominion bara för sig, gränserna i tabellen, *k* = 2, tecken −, åtta rader med X3 mot Y1 som huvudläsning.

## 2. KL1 oförändrad

`python -m ai_tracker.followed kreditlagret --as-of D` kördes i en separat worktree på `8d804df` (main) och i
integrationen, med samma delade data. Rapporterna per 2026-11-25 (18 809 byte) och 2025-11-25 (14 382 byte) är byte för
byte lika (`cmp`). F0 flyttade `Term`, `Formula` och `derive` från `series/kreditlagret.py` till `followed/aggregate.py`
utan ändring i logiken (R28 läste diffen rad för rad), och de fasta golden-filerna i `tests/golden/` låser den syntetiska
rapporten. KL1:s läsregel är kvar som den låstes, och F0 säger uttryckligen att en symmetrisk KL1 kräver en egen post.

## 3. Läckage

- **Kapning.** LT1 och EL1 kapar tabellen vid läsdagen innan något härleds (`table_on`, `_cut`). BG1 kapar komponenterna
  och läser kontextserierna med `state.measures`, som själv går på `as_of`. R28 körde varje fråga per 2025-11-26 på hela
  tabellen och på tabellen kapad vid dagen. JSON och Markdown är identiska för alla tre. De rader som kom efter dagen
  (ett års inlämningar) påverkar alltså inget.
- **Aggregat.** `aggregate.derive` bildar en version först när alla komponenter har en version och daterar den med den
  senaste komponenten. Samma regel som A5 och KL1, oförändrad kod.
- **Räkenskapsår.** Källserierna har bolagens egen mappning till kalenderkvartal. R28 kontrollerade dateringen för
  Cisco (räkenskapskvartalet aug–okt 2026 är 2026Q3, känt 2026-11-17), Dell (maj–jul 2026 är 2026Q2, känt 2026-09-08) och
  Oracle (jun–aug är 2026Q3). L2:s balans ligger därmed upp till en månad efter K-inres kvartalsslut i samma kvartal. Det
  står i LT1:s post och rapport.
- **Datering i månadsserierna.** PPI-serien har två dateringar: slutliga månader får regeldagen (ungefär fyra till fem
  månader efter månaden) och de fem senaste preliminära månaderna får filens dag (2026-11-13). Det är försiktigt, men det
  betyder att historiska läsningar ser elpriset senare än det faktiskt publicerades (per 2025-11-26 slutar elpriset vid
  2025Q1). EIA-930 är backfill med dagens värden, och revideringar kan läcka in i läsningen per 2025-11-26. Båda står i
  EL1:s rapport. Inget av dem påverkar huvudläsningen.

## 4. Neutralitet

R28 speglade in-data i `common.read_rule` 400 gånger med slumpade gränser, fönster, tecken och luckor: X → −X och
Y → −Y ger samma utslag, samma ursprung och impulsräkningen med upp och ned bytta; Y → −Y med tecknet bytt ger samma
utslag. Gränsfallet |X| = *g* läses lika åt båda håll. Testet står i `tests/test_r28_antenner.py`. Modulerna skickar
måtten oförändrade till regeln och har inga egna riktningsval. Inga larmord i koden eller dokumenten (listan i
registret, avsnitt om brevet).

Symmetrin i koden räcker inte överallt i data (R28-5), och två frågor läser samma rörelse med motsatt tecken (R28-4).

## 5. Oberoende omräkning

R28 skrev en egen beräkning (`pandas` och `numpy`, ingen import ur `ai_tracker`): senaste version per period med
`known_from` ≤ dagen, summor av komponenterna, takt = 100 × (ln *v*(*t*) − ln *v*(*t* − 4)), förändring i takt = takten
minus takten två kvartal tidigare, tolvmånadersmedel för månadsserierna, och en egen implementation av F0:s regel.

| Fråga | Storhet | Kvartal | R28 | Rapporten |
|---|---|---|---|---|
| LT1 | L1 nivå (Eaton + Quanta), MUSD | 2026Q3 | 67 950 | 67 950 |
| LT1 | L1 förändring i takt | 2026Q2 / 2026Q3 | +16,47 / +16,91 | +16,5 / +16,9 |
| LT1 | K-inre förändring i capex-takt | 2026Q2 / 2026Q3 | +6,24 / +9,60 | +6,2 / +9,6 |
| LT1 | L1 förändring i takt, per 2025-11-26 | 2025Q3 | +10,39 | +10,4 |
| LT1 | **Huvudutslag** L1 före K-inre, *k* = 2 | per 2026-11-26 | talar för (ursprung 2026Q2, avgjort 2026Q3) | talar för |
| LT1 | Huvudutslag per 2025-11-26 | | inget av mönstren | inget av mönstren |
| BG1 | krav(molnfyran, 0,10), MUSD | 2026Q3 | 295 998 | 295 998 |
| BG1 | moln(molnfyran), MUSD | 2026Q3 | 522 162 | 522 162 |
| BG1 | gap_moln, % | 2026Q3 | 56,687 | 56,687 |
| BG1 | gapets takt | 2026Q2 / 2026Q3 | +7,59 / +6,54 | +7,6 / +6,5 |
| BG1 | capex4 förändring i takt | 2026Q3 | +10,72 | +10,7 |
| BG1 | **Huvudutslag** | per 2026-11-26 | talar emot (2026Q2 → 2026Q3) | talar emot |
| BG1 | Raden mot RPO, X | 2026Q2 | −69,77, talar för | −69,8, talar för |
| BG1 | Huvudutslag per 2025-11-26 | | kan inte avgöras (fönstret öppet) | kan inte avgöras |
| EL1 | X3 orderstock elnät, takt | 2026Q2 / 2026Q3 | +45,27 / +54,58 | +45,3 / +54,6 |
| EL1 | X2 last, takt | 2026Q2 / 2026Q3 | +2,94 / +4,26 | +2,9 / +4,3 |
| EL1 | X1 elpris, takt | 2026Q3 | +4,01 | +4,0 |
| EL1 | X4 gasturbiner, nivå och takt | 2026Q3 | 122 GW, +67,69 | 122, +67,7 |
| EL1 | Y2 tecknade MW över fyra kvartal, förändring i takt | 2026Q3 | 498,4 MW, +100,40 | +100,4 |
| EL1 | **Huvudutslag** X3 mot Y1 | per 2026-11-26 | talar emot, uppåt | talar emot, uppåt |
| EL1 | Huvudutslag per 2025-11-26 | | kan inte avgöras (fönstret öppet) | kan inte avgöras |

R28 räknade också om de sju övriga raderna i EL1 per båda dagarna och raden *k* = 4 och "efter" för L1 i LT1. Alla
stämmer. Resultatdokumentens påståenden om historiken (till exempel "talar för i 9 av 21 ursprung med impuls" för L1
efter K-inre med *k* = 4) stämmer med rapporternas räkningar.

## 6. Stickprov av `ob_*` mot sec.gov

R28 valde 15 rader i de fyra `ob_*`-serier som ingår i läsreglerna, med tyngd på kvartalen 2025–2026 som avgör
utslagen, och läste varje tal i 8-K:ns exhibit 99 som `source_url` pekar på. Raderna står fastlåsta i testerna.

| Serie | Rader (id) | Dom |
|---|---|---|
| Eatons organiska order, Electrical Americas, rullande tolv månader (O1) | `etn-2025-05-02-02` (−4), `etn-2025-08-05-02` (+2), `etn-2026-02-03-02` (+16), `etn-2026-05-05-02` (+42), `etn-2026-11-03-02` (+39) | 5 av 5 rätt, i Electrical Americas avsnitt |
| Digital Realtys nya avtal, hyra per år, bolagets andel (O2) | `dlr-2025-07-24-07` (135,320), `dlr-2026-04-23-07` (422,774), `dlr-2026-10-29-07` (626,604) | 3 av 3 rätt, "Grand Total (at DLR Share)" |
| Digital Realtys nya avtal, MW (Y2) | `dlr-2024-10-24-08` (188,8), `dlr-2025-10-23-08` (49,8), `dlr-2026-07-23-08` (79,0) | 3 av 3 rätt |
| GE Vernovas orderstock och reservationer för gasturbiner, GW (X4) | `gev-2025-07-23-19` (50, jämförelsetal för 2025Q1), `gev-2025-10-22-18` (62), `gev-2026-04-22-18` (100), `gev-2026-10-28-18` (122) | 4 av 4 rätt; 44 + 56 och 64 + 58 går ihop |

Värdena i observationstabellen är desamma som i CSV:n, och `known_from` är 8-K:ns dag. Inget fel. Två saker om vad talen
innehåller står i R28-9.

## 7. Ärlighet

- **Sedda data.** Varje resultatdokument säger att läsningarna per 2026-11-26 är gjorda på kvartal som var kända före
  posten, och anger den första osedda läsningen. I koden slås förbehållet av för tidigt (R28-1).
- **Korta serier och slump.** Varje rapport säger att detta är en beskrivning och inget test, anger antalet ursprung och
  att ett mönster kan vara slump. Inget p-värde räknas.
- **Regimbrott.** Förvärv (LT1, EL1), nyttjandeperioder och Microsofts avskrivningsbas (BG1) och definitionsbrott i
  Azure-talen står i rapporterna. Förvärvsmärket i LT1 är ofullständigt (R28-2), och BG1:s markör läser bara det
  högsta värdet (R28-6).
- **Run-rate.** BG1 visar labbens run-rate som tabellrader, säger att run-rate inte är redovisad intäkt och blandar den
  inte med GAAP-tal. Anthropics GAAP-intäkter och OpenAI står som BLOCKED. Katalogens etiketter för Microsofts och
  Amazons nyckeltal ("intäkt i årstakt") är äldre och inte ändrade här.
- **Licens och publicering.** `lt1_rpo_power`, `lt1_rpo_net` och `lt1_dlr_bookings4` har `publish=False` och klassen
  `ja` (alla komponenter är SEC-material med klass `ja`). BG1 och EL1 skapar inga katalogserier. Inga serier ingår i
  någon kärnlista eller något grenindex.

## Fynd

### R28-1 (should_fix): förbehållet om sedda data slås av för tidigt

BG1 och EL1 avgör om läsningen är gjord på sedda data med läsdagen: `seen_before_register = str(when.date()) <=
REGISTERED`. Från 2026-11-27 försvinner meningen "Läsningen är därför inget utfall på osedda data" ur båda rapporterna,
också när inget nytt kvartal har kommit (till exempel vid månadsskiftet 2026-11-30). LT1 använder i stället den senaste
`known_from` bland läsregelns storheter, men för hela rapporten: när Dell lämnar in 2026Q3 (omkring 2026-12-09) blir
flaggan falsk, och huvudläsningen (L1 före K-inre) visas utan förbehållet fast den fortfarande bygger på sedda kvartal
fram till omkring 2027-01-31.

*Följd:* Johannes kan läsa ett utslag på sedda data som ett utfall på osedda data i december och januari, alltså just de
månader då de första osedda läsningarna börjar komma.

*Rättning (förslag):* flaggan per läsning, inte per rapport: en läsning är osedd när kvartalet som avgjorde den (eller
*t*, om den inte avgjorts) blev känt efter registerdagen. *Tester:* tre strikta xfail (BG1 och EL1 per 2026-11-30 på
syntetiska data som alla är kända före registerdagen; LT1 med en ny rad i en annan rad än huvudläsningen).

**Rättat i X25** (registret 2026-11-26 X25, punkt 1): "sedd" avgörs per läsning genom att jämföra de värden utfallet vilar på med läsningen per registerdagen (en ny version med samma värde räknas inte som ny). De tre strikta xfail är vanliga tester, och `tests/test_x25_antenner.py` prövar att en läsning med ett nytt kvartal märks osedd.

### R28-2 (should_fix): överlappande förvärv i LT1, fel riktning i resultatdokumentet

`ledtid.acquisition_quarters` bygger märkena med `setdefault`, så när två förvärv träffar samma kvartal visas bara det
första. För L1 träffar Fibrebond (*a* = 2025Q2) och Boyd Thermal (*a* = 2026Q1) båda 2026Q2: Fibrebond som *a* + 4
(flyttar förändringen i takt nedåt) och Boyd Thermal som *a* + 1 (flyttar den uppåt). Rapporten märker huvudläsningens
ursprung 2026Q2 bara med Fibrebond, och `docs/resultat/ledtid.md` skriver att förvärvet "drar ned L1:s förändring i takt
vid 2026Q2, inte upp". Med Boyd Thermal i samma kvartal är riktningen inte känd. Eatons orderstock växte med 3,0 mdr
2026Q1 (19,8 → 22,8 mdr), samma kvartal som köpet. Hur mycket av det som är Boyd Thermal är inte kontrollerat. X är +16,5
mot gränsen 10, så ett tillskott på några log-enheter vänder sannolikt inte utslaget, men det kan inte uteslutas ur
data.

*Rättning (förslag):* lista alla förvärv per kvartal, med riktning (*a*, *a* + 1 upp; *a* + 4, *a* + 5 ned), och rätta
meningen i resultatdokumentet. *Test:* en strikt xfail.

**Rättat i X25** (punkt 2): alla förvärv listas per kvartal med förskjutning och riktning, och meningen i `docs/resultat/ledtid.md` är rättad. Som beskrivning står där också att X vid 2026Q2 hamnar under gränsen 10 först om Boyd Thermal lade till mer än omkring 3,6 mdr USD (Eatons hela ökning 2026Q1 var 3,0 mdr). Den strikta xfail är ett vanligt test.

### R28-3 (should_fix): BG1:s antenn visar en ändring som inte är en

BG1:s fakta för bolagsraderna har kvartalet med bara när det skiljer sig från huvudläsningens *t* (Oracle lämnar in
först). När huvudläsningen går från 2026Q2 till 2026Q3 försvinner suffixet för Oracles rader, och `antenner` listar
"Oracle: gapet mot molnintäkterna: talar för mekanismen (2026Q3) → talar för mekanismen" och samma för RPO som ändringar,
fast Oracles utslag och kvartal är desamma. Det står så i `docs/resultat/antenner.md` per 2026-11-26.

*Rättning (förslag):* skriv alltid ut radens kvartal i faktan, eller jämför utslag och kvartal var för sig. *Test:* en
strikt xfail.

**Rättat i X25** (punkt 3): faktan har alltid radens kvartal. Den strikta xfail är ett vanligt test.

### R28-4 (should_fix): LT1 och EL1 läser samma rörelse med motsatt tecken

EL1:s X3 (`el1_ob_nat` = `rpo_pwr` + `rpo_etn`) är exakt LT1:s L1 (`lt1_rpo_power`), och båda läses mot
`kl_capex4_inner`. LT1 läser förändring i takt med tecken + (orderstocken leder capex), EL1 läser takt med tecken −
(elen binder). Samma kvartal (ursprung 2026Q2, capex +9,6 vid 2026Q3) ger därför "talar för" i LT1 och "talar emot" i
EL1. Båda posterna är låsta och var för sig rimliga, men i antennerna står raderna bredvid varandra som om de vore två
belägg. `docs/resultat/antenner.md` säger att frågorna delar capex-takten, men inte att LT1 och EL1 också har samma X.

*Rättning (förslag):* en mening i antennernas rapport (kod, inte register) om att LT1:s huvudläsning och EL1:s
huvudläsning bygger på samma två serier, och att de tillsammans inte är mer än en observation. Inget test (text).

**Rättat i X25** (punkt 3): varje antenn anger huvudläsningens X och Y som katalogserier, och antennernas rapport har avsnittet "Samma serier i flera frågor" som säger att LT1 och EL1 har samma huvudpar och tillsammans är en observation. LT1:s och EL1:s resultatdokument säger det också. Test i `tests/test_x25_antenner.py`.

### R28-5 (should_fix): "kunde prövas" räknar ursprung där Y inte finns, och regeln läser i praktiken bara uppgång

F0 räknar ett ursprung som prövat när utfallet inte är "kan inte avgöras". Ett ursprung utan impuls blir "inget av
mönstren" också när Y inte finns i fönstret. EL1 skriver därför "Regeln kunde prövas i 213 av 267 ursprung" för elpriset
mot capex, fast capex-takten bara har förändring i takt från 2019Q4 (cirka 27 ursprung), och "206 av 267" mot Digital
Realtys MW (från 2024Q1). Det följer F0 (b) ordagrant, men talet överdriver hur ofta regeln har kunnat pröva något.

Samtidigt är regeln symmetrisk i koden men ensidig i data: EL1:s huvudläsning har haft 20 impulser uppåt och ingen nedåt,
elpriset 62 uppåt och ingen nedåt sedan 1959 (lägsta takt −1,8 mot gränsen 5), och BG1:s huvudläsning 5 uppåt och ingen
nedåt av 7. Rapporterna redovisar räkningarna, och EL1:s post säger det själv. Det är samma lärdom som R26-8 för KL1:
riktningen nedåt har inte prövats.

*Rättning (förslag):* beslut för Johannes, eftersom det ändrar låsta poster (se nedan). Inget test.

**Delvis rättat i X25** (punkt 4): F0:s räkning står kvar, och bredvid den visar varje rad i hur många ursprung Y var känt i hela fönstret (för elpriset mot capex 27 av 267) och hur många impulser som kunde läsas mot Y, och säger vilken riktning som inte har prövats. Att byta F0:s räkning och EL1:s extra rad med förändring i takt är kvar som beslut för Johannes.

### R28-6 (note): BG1:s regimmarkör missar Amazons förkortade nyttjandeperiod

Markören läser bara det högsta värdet (`_hi`), som posten säger. Amazons förkortning för en del servrar (6 → 5 år, i
`useful_life_servers_amzn_lo` från 2025Q4, känt 2026-02-06) ligger i huvudläsningens fönster 2024Q3–2026Q2 och höjer
avskrivningarna, alltså X, men märker ingen rad. Resultatdokumentet säger det. Microsofts lägsta värde 6 → 2 år 2026Q2
är troligen en formulering (ett intervall), som rapporten också säger. Ingen ändring föreslås före första osedda
läsningen. En ändring nu vore gjord efter att data setts.

### R28-7 (note): Quanta driver L1, och Quantas förvärv är inte kontrollerade

Quantas RPO växte från 26,2 till 33,6 och 41,8 mdr 2026Q1–Q3, och står för det mesta av L1:s förändring i takt vid
huvudläsningens ursprung och avgörande kvartal (EL1:s X3 är samma serie). LT1:s post och rapport säger att förvärv hos
Quanta inte är kontrollerade. R28 rekommenderar att Quantas 10-Q för 2026Q2 och 2026Q3 läses för förvärv innan
huvudläsningen tolkas, och att resultatet förs in som ett belagt förvärv eller som "inget förvärv" i en daterad post.

### R28-8 (note): förvärvsmärket i "efter" följer inte postens ordalydelse

Posten säger att ursprung i kvartalen *a*, *a* + 1, *a* + 4 och *a* + 5 märks. I "efter" är ursprunget köparens kvartal,
och koden märker i stället det kvartal där leverantören (Y) avgjorde läsningen. Det är mer meningsfullt, eftersom det är
där leverantörens förändring i takt läses, men det är en avvikelse från posten. Den bör loggas med datum. Kvartal i
fönstret som lästes utan att avgöra märks inte. **Loggat i X25** (registret 2026-11-26 X25, punkt 2).

### R28-9 (note): vad två av `ob_*`-talen innehåller

- Eatons −4 % för 2025Q1 (O1) står i dokumentet, men samma mening säger +4 % exklusive en stor flerårig datacenterorder
  i 2024Q1. Basårseffekten ligger alltså i O1:s nedgång 2025Q2 (−12,9 i förändring i takt), som gjorde O1 "kan inte
  avgöras" per 2025-11-26, och i O1:s historik. CSV:n säger att talet exklusive ordern inte är kodat.
- Digital Realtys belopp (O2) är "Grand Total", som innehåller interconnection (22,2 av 626,6 MUSD 2026Q3), medan MW
  (Y2) inte gör det. Det är rätt avläst, men O2 och Y2 mäter inte exakt samma avtal.

### R28-10 (note): det går inte att visa ur git vad EL1 hade sett av LT1

LT1:s rapporter committades 22:08:53 på LT1:s gren, tio minuter före EL1:s registerpost (22:18:35, egen gren från F0).
EL1:s X3 är samma serie som LT1:s L1. EL1:s post (f) listar vad som var sett och nämner inte LT1, och EL1 förutsade
utslaget ur Y ensam. R28 kan inte verifiera att EL1-agenten inte läste LT1:s worktree. Det ändrar inget här, eftersom
EL1:s huvudläsning per 2026-11-26 ändå är på sedda data.

### R28-11 (note): PPI och EIA-930 i historiska läsningar

Se avsnitt 3. Försiktig datering för PPI (historiska läsningar ser elpriset senare än det publicerades) och backfill för
EIA-930 (revideringar kan läcka in per 2025-11-26). Båda står i EL1:s rapport. Nämns här för att jämförelsen "mot
förra månaden" i antennerna för EL1:s pris- och lastrader därmed inte visar vad som var känt en månad tidigare i
verkligheten, utan vad tabellens datering säger.

## Beslut för Johannes

1. **R28-1 och R28-2 före den första osedda läsningen.** Rekommendation: rätta båda i ett litet spår före Dells
   inlämning omkring 2026-12-09. Det ändrar inga utslag, bara förbehållet och märkningen, och kräver ingen ny post (R28-2
   följer postens regel för märkning, R28-1 gäller rapporttext).
2. **R28-4.** Rekommendation: en mening i antennerna om att LT1 och EL1 har samma huvudpar. Ingen ändring av posterna.
3. **R28-5.** EL1 och integrationen föreslår redan en extra rad med förändring i takt för orderstockarna och en rättning
   av F0:s räkning av prövade ursprung. Rekommendation: ja till båda, som en daterad post före läsningen omkring
   2027-01-31, med de nuvarande raderna kvar som huvudläsning. Posten bör säga att den skrivs efter att alla kvartal till
   och med 2026Q3 setts.
4. **R28-6 och R28-7.** Rekommendation: ingen ändring av markören nu. Läs Quantas 10-Q för förvärv och för in resultatet
   som fakta i LT1:s och EL1:s källdokument.
