# Pris mot volym: följd fråga (PV1)

*Ägarbeslut 2026-11-27 (spår B18, `docs/mattregister.md`, 2026-11-27 B18, punkt 2): huvudläsningen är H-G, med kvartalet som geometriskt medel av månaderna och veckosummorna, och bisakerna redovisas som a-G och b-G. De låsta raderna H, a och b (aritmetiskt medel) står kvar bredvid i avsnitt 6 i rapporterna nedan. Antennens utslag, fakta och `main_inputs` följer H-G (katalogserierna är desamma som för H). Inga utslag ändrades: H-G, a-G och b-G ger samma utslag som H, a och b båda dagarna. Övergångsnotisen för F0:s räkning väntar inte längre på ägarens bekräftelse (punkt 1, R29-1 stängt). Rapporterna nedan är genererade på nytt med kommandot.*

*Rättad efter granskningen R29 (rättningsspår X26, `docs/mattregister.md`, 2026-11-27 X26): tre rader bredvid de låsta, H-G, a-G och b-G, med kvartalet som geometriskt medel (exp av medlet av ln) av månaderna och veckosummorna, i ett eget avsnitt 6 i rapporterna nedan (R29-2). Med det aritmetiska medlet ger en speglad prisbana inte den speglade förändringen i takt; med det geometriska gör den det exakt. De geometriska raderna ger samma utslag som de låsta båda dagarna (Arena A: förändring i takt +433,7 och +301,0 vid 2025Q3 och 2025Q4 i stället för +441,0 och +346,0). Huvudläsningen är fortfarande H; om H-G ska ersätta H är ett beslut för Johannes före 2027-01-05. Förbehållen säger nu att historiken är backfill, hämtad 2026-11-23–26 med `known_from` satt efter en regel, så att läsningen per 2025-11-27 kan innehålla senare revideringar (R29-3). Övergångsnotisen för F0:s räkning säger att bytet väntar på ägarens bekräftelse (R29-1). Inga låsta utslag ändrades.*


*Omgenererad i integrationen av körning 17: F0:s räkning av hur ofta regeln kunde prövas är ändrad av S1 (`docs/mattregister.md`, 2026-11-27 S1, punkt 3, registrerad före PV1). Ett ursprung räknas nu som prövat bara när Y finns i fönstret, och rapporten visar båda talen i en övergångsnotis. Per 2026-11-27 ger det 3 av 4 ursprung i stället för 4 av 4 för bisak a. Inga utslag ändrades.*

**Frågan:** Följs prisfallet vid fast förmåga (G2) av högre användning (G3), och ändras sambandet?

Följd fråga, inte en gren. Måtten, aggregaten, läsregeln och gränserna låstes i registret innan något räknades
(`docs/mattregister.md`, "2026-11-27 – PV1", commit `6ed50e2`). Regeln är F0:s symmetriska mall: X är förändringen i
takt för priset vid fast förmåga, Y förändringen i takt för nedladdningar av AI-SDK:er på npm, tecken −1, *g* = 50,
*h* = 20 och *k* = 2. Sedan ägarbeslutet B18 (registret 2026-11-27) är kvartalsvärdet i huvudläsningen och bisakerna ett
geometriskt medel (H-G, a-G och b-G, X26), och de låsta raderna med aritmetiskt medel redovisas bredvid. Källor, kvartalsregler och kontroller: `docs/kallor/prisvolym.md`. Rapporten byggs med

    python -m ai_tracker.followed prisvolym --as-of 2026-11-27 [--json PATH] [--out PATH]

Den använder bara rader som var kända på dagen. Nedan står rapporten per 2026-11-27 och per 2025-11-27, så att
ändringen över ett år syns. Rapporterna är genererade av kommandot och inte redigerade (rubrikerna är en nivå lägre).

**Läsningarna är gjorda på sedda data.** Alla månader och veckor i båda läsningarna var publicerade före registerposten
2026-11-27, så ingen läsning är ett utfall på osedda data. Huvudläsningen kan inte avgöras på någon av dagarna:
GPQA-priset (G2:s kärnserie) börjar 2025-02 och får sin första förändring i takt för 2026Q4, när december 2026 är känd.
Huvudläsningen kan avgöras tidigast med npm-kvartalet 2027Q1, omkring 2027-03-30, och den läsningen är då helt på osedda
data. Bisak a-G (Arena-priset), liksom den låsta raden a, vilar på X-värden som agenten hade sett före posten: nivåerna för variant A stod i
`docs/kallor/g2_arena_pris.md`, och posten skrev ut den ungefärliga banan (registret, avsnitt (f)). a-G:s förändring i
takt stod dessutom i R29. Bisak a-G har därför bara beskrivande värde. Första läsningen med ett osett kvartal är npm-kvartalet 2026Q4, omkring 2027-01-05.

**Inga andra frågor delar serier med huvudläsningen.** PV1:s X och Y (`g2_price_at_capability_gpqa`, `g3_npm_openai_w` +
`g3_npm_anthropic_sdk_w`) ingår inte i någon annan följd frågas huvudläsning (antennen anger dem, X25 punkt 3).

## Vad som skiljer de två dagarna (beskrivning, inget test)

Talen nedan är i huvudläsningens form (geometriskt kvartalsmedel, H-G, a-G och b-G). De låsta raderna H, a och b
(aritmetiskt medel) ger samma utslag båda dagarna, och deras tal står inom parentes där de skiljer sig.

- **Huvudläsningen H-G** (GPQA-priset mot SDK-nedladdningarna) gav "kan inte avgöras" båda dagarna, eftersom X saknar
  förändring i takt. Priset vid fast GPQA-förmåga föll från 1,93 USD per miljon tokens (kvartalet 2025Q3) till 0,27
  (2026Q3), en takt på −197 log-punkter (−195 i aritmetiskt medel), ungefär en sjundedel på ett år. Det är ett prisfall
  per token, inte per uppgift.
- **Bisak a-G** (Arena-priset mot samma nedladdningar) gav "kan inte avgöras" per 2025-11-27 (X har förändring i takt
  först vid läsdagens kvartal 2025Q3) och "inget av mönstren" per 2026-11-27 (ursprungen 2026Q1 och 2026Q2 har +0,1 och
  −37,7, inom gränsen ±50; i a +3,0 och −37,7). Över historiken på dagen har två ursprung avgjorts, båda "talar emot,
  uppåt": vid 2025Q3 (+434, i a +441) och 2025Q4 (+301, i a +346) slutade Arena-priset falla, eftersom det nådde golvet
  i de billigaste prisnivåerna efter fallen 2024, och nedladdningarna accelererade (+42,9 vid 2025Q4 och +42,4 vid
  2026Q1; i a +42,0 och +44,9). Mönstret var förväntat för X när posten skrevs.
  Det säger att användningen accelererade fast prisfallet stannade av, men Arena A mäter från 2024-07 golvet och inte
  priset vid fast förmåga, så det är ingen läsning av mekanismen vid fast förmåga. Riktningen nedåt (prisfallet blev
  snabbare) har inte prövats i någon rad.
- **Nedladdningarna** växte från 7,9 till 68,1 miljoner per vecka (openai + @anthropic-ai/sdk, kvartalen 2025Q3 och
  2026Q3; 8,0 och 69,4 i aritmetiskt medel), takten från +110,5 till +214,9 och förändringen i takt från +37,9 till
  +62,1 (+36,4 och +60,5). Kontrollpaketen (react + express) växte också snabbare, takten från +49,0 till +121,9 (+49,1 och
  +122,1), så en stor del av SDK-tillväxten delas med npm i stort (CI, speglar). Relativt kontrollen är takten +93,1 och förändringen i
  takt +23,1 vid 2026Q3 (+94,1 och +23,6). Av de två SDK:erna står @anthropic-ai/sdk för den största accelerationen
  (+88,7 i förändring i takt, openai +36,9, beskrivningsrader i aritmetiskt medel), och där räknas verktyg som beror på
  SDK:n med.
- **Vad som kan sägas.** Ingenting om mekanismen ännu. Prisserierna vid fast förmåga är för korta för regeln, och den
  enda rad som har avgjorts (bisak a-G, och a) läser ett prisgolv. Två avgjorda ursprung i samma riktning kan vara slump.

## Rapporten per 2026-11-27

## Pris mot volym per 2026-11-27

**Frågan:** Följs prisfallet vid fast förmåga (G2) av högre användning (G3), och ändras sambandet?

Priset vid fast förmåga (G2) mot nedladdningar av AI-SDK:er på npm (G3). Kvartal: priset som geometriskt medel, exp(medlet av ln), av kvartalets tre månader, nedladdningarna som geometriskt medel av veckosummorna för veckorna vars torsdag ligger i kvartalet (bara hela kvartal). Det är huvudläsningens och bisakernas form sedan ägarbeslutet i registret 2026-11-27 B18, punkt 2. De låsta raderna H, a och b med aritmetiskt medel står bredvid i avsnitt 6, och beskrivningsraderna i tabellerna är aritmetiska medel. Takt = 100 × ln(värdet / värdet fyra kvartal tidigare). Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1. Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-27 PV1, X26 och B18. Klass = klass för kommersiell användning (`ai_tracker.licenses`).

### 1. Pris vid fast förmåga (X)

Lägsta blandade förstapartspris (USD per miljon tokens, 3:1) bland modeller över en fast förmågetröskel. GPQA-varianten är G2:s kärnserie. Arena-variant A är inte kärnserie och mäter från 2024-07 golvet i de billigaste prisnivåerna, eftersom tröskeln inte binder (`docs/kallor/g2_arena_pris.md`). De två första raderna är läsningarnas X, de två därefter samma serier i de låsta radernas form. Övriga rader är beskrivning.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie | Klass |
|---|---|---|---|---|---|---|---|---|
| Pris vid fast förmåga, GPQA (kärnserie), geometriskt medel | 0,2679 USD | -197,2 | – | +31,0 | 2026Q3 | 2026-09-30 | `pv1_pris_gpqa_gq` | ja |
| Pris vid fast Arena-förmåga, variant A, geometriskt medel | 0,1194 USD | -9,5 | +0,0 | +37,7 | 2026Q3 | 2026-10-01 | `pv1_pris_arena_gq` | okänd |
| Pris vid fast förmåga, GPQA, aritmetiskt medel (låst rad) | 0,2733 USD | -195,2 | – | +33,1 | 2026Q3 | 2026-09-30 | `pv1_pris_gpqa_q` | ja |
| Pris vid fast Arena-förmåga, variant A, aritmetiskt medel (låst rad) | 0,1217 USD | -7,6 | +0,0 | +39,6 | 2026Q3 | 2026-10-01 | `pv1_pris_arena_q` | okänd |
| Pris vid fast Arena-förmåga, variant B (GPT-4o) | 0,1217 USD | -7,6 | +10,5 | +39,6 | 2026Q3 | 2026-10-01 | `g2_price_at_arena_capability_4o` | okänd |
| Pris vid fast förmåga, ECI (bakåtfylld) | 0,2042 USD | -108,5 | +347,4 | +24,3 | 2026Q3 | 2026-09-30 | `g2_price_at_capability` | ja |
| Pris vid rörlig tröskel, ECI, 12 mån | 0,2958 USD | +67,9 | – | – | 2026Q3 | 2026-10-01 | `g2_price_rolling12_eci` | ja |
| Pris vid rörlig tröskel, Arena, 12 mån | 0,5333 USD | +120,1 | -24,6 | -128,4 | 2026Q3 | 2026-10-01 | `g2_price_rolling12_arena` | okänd |
| Pris vid rörlig tröskel, Arena, 6 mån | 7,1250 USD | +150,1 | -36,0 | +58,4 | 2026Q3 | 2026-10-01 | `g2_price_rolling6_arena` | okänd |
| Frontpris, Arena | 9,3333 USD | +99,9 | +236,1 | -33,6 | 2026Q3 | 2026-10-01 | `g2_price_frontier_arena` | okänd |
- Pris vid fast förmåga, GPQA (kärnserie), geometriskt medel: 2026Q4 saknar på dagen `g2_price_at_capability_gpqa` 2026-11, 2026-12.
- Pris vid fast Arena-förmåga, variant A, geometriskt medel: 2026Q4 saknar på dagen `g2_price_at_arena_capability` 2026-11, 2026-12.

### 2. Användning: nedladdningar på npm (Y)

Nedladdningar per vecka, kvartalets geometriska medel av veckosummorna. Huvudläsningens Y är openai + @anthropic-ai/sdk. Bisak b-G läser samma summa relativt kontrollpaketen react + express, så att den gemensamma tillväxten i npm (CI, speglar) tas bort så långt kontrollen speglar den. Nedladdningar är inte användare. De tre första raderna är läsningarnas Y, de tre därefter samma storheter i de låsta radernas form. Övriga paket är beskrivning.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie | Klass |
|---|---|---|---|---|---|---|---|---|
| SDK-nedladdningar, openai + @anthropic-ai/sdk, geometriskt medel | 68,1 M/vecka | +214,9 | +62,1 | +3,6 | 2026Q3 | 2026-09-29 | `pv1_sdk_gq` | okänd |
| Kontrollpaket, react + express, geometriskt medel | 301,3 M/vecka | +121,9 | +39,0 | +0,2 | 2026Q3 | 2026-09-29 | `pv1_kontroll_gq` | okänd |
| SDK relativt kontroll, geometriska medel (kvot) | 0,226 | +93,1 | +23,1 | +3,4 | 2026Q3 | 2026-09-29 | `pv1_sdk_rel_gq` | okänd |
| SDK-nedladdningar, aritmetiskt medel (låst rad) | 69,4 M/vecka | +216,2 | +60,5 | +3,4 | 2026Q3 | 2026-09-29 | `pv1_sdk_q` | okänd |
| Kontrollpaket, aritmetiskt medel (låst rad) | 302,8 M/vecka | +122,1 | +36,9 | +0,4 | 2026Q3 | 2026-09-29 | `pv1_kontroll_q` | okänd |
| SDK relativt kontroll, aritmetiska medel (kvot, låst rad) | 0,229 | +94,1 | +23,6 | +3,0 | 2026Q3 | 2026-09-29 | `pv1_sdk_rel_q` | okänd |
| npm openai | 35,4 M/vecka | +179,0 | +36,9 | +7,0 | 2026Q3 | 2026-09-29 | `g3_npm_openai_w` | okänd |
| npm @anthropic-ai/sdk | 34,0 M/vecka | +279,4 | +88,7 | -6,5 | 2026Q3 | 2026-09-29 | `g3_npm_anthropic_sdk_w` | okänd |
| npm @google/genai | 20,4 M/vecka | +290,6 | – | -49,3 | 2026Q3 | 2026-09-29 | `g3_npm_google_genai_w` | okänd |
| npm @google/generative-ai | 4,1 M/vecka | +129,1 | -16,6 | -3,5 | 2026Q3 | 2026-09-29 | `g3_npm_google_generative_ai_w` | okänd |
| npm ai (Vercel) | 22,1 M/vecka | +226,7 | +23,4 | -4,3 | 2026Q3 | 2026-09-29 | `g3_npm_vercel_ai_w` | okänd |
| npm langchain | 2,9 M/vecka | +100,4 | +2,3 | +1,0 | 2026Q3 | 2026-09-29 | `g3_npm_langchain_w` | okänd |
| npm @langchain/core | 5,5 M/vecka | +128,8 | -2,4 | -5,4 | 2026Q3 | 2026-09-29 | `g3_npm_langchain_core_w` | okänd |
| npm @modelcontextprotocol/sdk | 52,1 M/vecka | +219,0 | -253,0 | -21,5 | 2026Q3 | 2026-09-29 | `g3_npm_mcp_sdk_w` | okänd |
| npm react (kontroll) | 171,5 M/vecka | +137,6 | +38,5 | -3,5 | 2026Q3 | 2026-09-29 | `g3_npm_react_w` | okänd |
| npm express (kontroll) | 131,3 M/vecka | +105,0 | +33,6 | +4,6 | 2026Q3 | 2026-09-29 | `g3_npm_express_w` | okänd |
- SDK-nedladdningar, openai + @anthropic-ai/sdk, geometriskt medel: 2026Q4 saknar på dagen `g3_npm_openai_w` 6 veckor; `g3_npm_anthropic_sdk_w` 6 veckor.
- Kontrollpaket, react + express, geometriskt medel: 2026Q4 saknar på dagen `g3_npm_react_w` 6 veckor; `g3_npm_express_w` 6 veckor.

### 3. Läsregeln, mekaniskt

F0:s symmetriska regel: X:s förändring i takt mot Y:s förändring i takt, tecken −1, fönster 2 kvartal efter ursprunget. Gränser (låsta): X ±50, Y ±20 log-punkter. En rad per par, ingen sammanslagning. Huvudläsningen är H-G och bisakerna a-G och b-G (registret 2026-11-27 B18, punkt 2). Med det geometriska kvartalsmedlet ger en speglad prisbana (1/x) exakt det speglade utslaget.

- **Talar för, nedåt:** prisfallet blev snabbare (X ≤ −g) och användningen accelererade (Y ≥ +h). **Talar för, uppåt:** prisfallet blev långsammare (X ≥ +g) och användningen bromsade (Y ≤ −h).
- **Talar emot:** användningens takt gick åt samma håll som priset: prisfallet blev snabbare och användningen bromsade, eller prisfallet blev långsammare och användningen accelererade.
- Förändringen i takt läser om tillväxten blir snabbare eller långsammare, inte om nivån stiger eller faller. Utslaget är en beskrivning, inget test.

Alla läsningar nedan vilar bara på värden som var kända före registerposten 2026-11-27. Ingen av dem är därför ett utfall på osedda data. Nästa osedda läsning: npm-kvartalet 2026Q4 när veckan 2026-12-28–2027-01-03 är känd, omkring 2027-01-05. Huvudläsningens X (GPQA-priset) får sin första förändring i takt för 2026Q4 omkring 2027-01-01, och huvudläsningen kan avgöras tidigast med npm-kvartalet 2027Q1, omkring 2027-03-30. Sedda data avgörs per läsning (X25, punkt 1).

- **Pris vid fast förmåga (GPQA) mot SDK-nedladdningar, geometriskt medel (H-G, huvudläsning):** kan inte avgöras. t = 2026Q3 (X saknas vid 2026Q1; X saknas vid 2026Q2). X = pv1_pris_gpqa_gq (förändring i takt), Y = pv1_sdk_gq (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  X har ännu ingen förändring i takt på dagen (serien är för kort), så varje ursprung kan inte avgöras.
  Ändras sambandet? Inget ursprung har avgjorts (talar för eller talar emot) i historiken på dagen.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-27, och den är därför inget utfall på osedda data.
- **Pris vid fast Arena-förmåga (variant A) mot SDK-nedladdningar, geometriskt medel (bisak a-G):** inget av mönstren. t = 2026Q3 (ingen impuls i fönstret). X = pv1_pris_arena_gq (förändring i takt), Y = pv1_sdk_gq (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 3 av 4 ursprung med X (2025Q3–2026Q2). Impulser uppåt 2 (för 0, emot 2, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 3 av 4 ursprung, och 2 av 2 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 4 av 4; med den nya: 3 av 4.
  X har förändring i takt från 2025Q3.
  Ändras sambandet? Avgjorda ursprung i tidsordning: 2025Q3 talar emot, uppåt (X +433,7, Y +42,9 vid 2025Q4); 2025Q4 talar emot, uppåt (X +301,0, Y +42,4 vid 2026Q1). Senaste: talar emot (2025Q4), tidigare 0 talar för och 1 talar emot. En beskrivning utan gräns för "ändrat"; med så få ursprung kan en skillnad vara slump.
  Bisak a-G vilar på X-värden som var sedda före posten (nivåerna för variant A stod i `g2_arena_pris.md`, registret PV1 avsnitt (f), och förändringen i takt i geometriskt medel stod i R29) och har bara beskrivande värde.
- **Pris vid fast förmåga (GPQA) mot SDK-nedladdningar relativt kontrollpaketen, geometriskt medel (bisak b-G):** kan inte avgöras. t = 2026Q3 (X saknas vid 2026Q1; X saknas vid 2026Q2). X = pv1_pris_gpqa_gq (förändring i takt), Y = pv1_sdk_rel_gq (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  X har ännu ingen förändring i takt på dagen (serien är för kort), så varje ursprung kan inte avgöras.
  Ändras sambandet? Inget ursprung har avgjorts (talar för eller talar emot) i historiken på dagen.

### 4. Att bevaka

- Nästa osedda läsning: npm-kvartalet 2026Q4 när veckan 2026-12-28–2027-01-03 är känd, omkring 2027-01-05. Huvudläsningens X (GPQA-priset) får sin första förändring i takt för 2026Q4 omkring 2027-01-01, och huvudläsningen kan avgöras tidigast med npm-kvartalet 2027Q1, omkring 2027-03-30.
- Prisserierna får en ny månad dagen efter månadsslut, npm en ny vecka söndag + 2 dagar. Ett kvartal räknas först när alla dess månader eller veckor är kända.

### 5. Förbehåll

- **Pris per token, inte per uppgift.** Resonemangsmodeller använder fler tokens per uppgift. Ett snabbare prisfall per token kan vara ett långsammare fall, eller en ökning, per uppgift (`docs/riktning.md` avsnitt 4).
- **Gemensam orsak.** En lansering kan både sänka priset (en billig modell kvalificerar) och dra nedladdningar (ny SDK-version, nya funktioner, uppmärksamhet). Regeln läser Y först kvartalet efter, men en lansering kan verka över flera kvartal. Ett utslag som talar för mekanismen visar inte att priset orsakade användningen.
- **Nedladdningar är inte användare.** CI-byggen, containerbyggen, speglar och transitiva beroenden räknas med, och ett verktyg som börjar bero på en SDK höjer nivån utan nya utvecklare. Kontrollpaketen i bisak b-G är inte stabila och tar inte bort skiften i en enskild SDK.
- **Förstapartspris.** Öppna modeller som bara säljs av tredje part ingår inte. Arena-variant A mäter golvet i de billigaste nivåerna från 2024-07, inte priset vid en fast förmåga.
- **Urval.** npm-paketen valdes 2026-11-23 med kunskap om vilka SDK:er som blev stora. Googles SDK:er ingår inte i summan, eftersom bytet mellan två paket är en migrering.
- **Korta serier.** GPQA-priset har förändring i takt först från 2026Q4. Med en handfull ursprung är detta en beskrivning och inget test, och utfall kan vara slump.
- **Licens.** npm-serierna har klassen `okänd` och `publish=False`, Arena-variant A `okänd`. GPQA-priset har `ja`. Cloudflare Radar (`nej`) används inte.
- **Historiken är backfill.** Pris- och npm-raderna är hämtade 2026-11-23–2026-11-26, i efterhand, med `known_from` satt efter en regel (prisserierna vid månadsslut eller dagen efter, npm söndag + 2 dagar), inte som arkiverade versioner. "Bara data kända på dagen" gäller därför `known_from` och inte vad källan visade då: en läsning per en tidigare dag kan innehålla revideringar och rättningar som inte var kända den dagen. Ingen av de 1485 rader som läsningarna använder hämtades efter läsdagen, men de hämtades ändå i efterhand i en omgång.

### 6. Aritmetiskt kvartalsmedel (de låsta raderna H, a och b, bredvid)

De tre låsta raderna ur registret 2026-11-27 PV1, avsnitt (c), med kvartalet som aritmetiskt medel av månaderna och veckosummorna. Samma källserier, statistik, gränser, fönster och tecken som H-G, a-G och b-G. Fram till ägarbeslutet i registret 2026-11-27 B18, punkt 2, var H huvudläsningen. Med det aritmetiska medlet ger en speglad prisbana inte den speglade förändringen i takt (R29-2), så riktningen kan avgöra om en impuls uppstår. Raderna står kvar och redovisas, men de är inte huvudläsningen. Kvartalsvärdena står i avsnitt 1 och 2 (märkta "låst rad").

- **Pris vid fast förmåga (GPQA) mot SDK-nedladdningar, aritmetiskt medel (H, låst rad bredvid H-G):** kan inte avgöras. t = 2026Q3 (X saknas vid 2026Q1; X saknas vid 2026Q2). X = pv1_pris_gpqa_q (förändring i takt), Y = pv1_sdk_q (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  X har ännu ingen förändring i takt på dagen (serien är för kort), så varje ursprung kan inte avgöras.
  Ändras sambandet? Inget ursprung har avgjorts (talar för eller talar emot) i historiken på dagen.
  Samma utslag som H-G.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-27, och den är därför inget utfall på osedda data.
- **Pris vid fast Arena-förmåga (variant A) mot SDK-nedladdningar, aritmetiskt medel (a, låst rad bredvid a-G):** inget av mönstren. t = 2026Q3 (ingen impuls i fönstret). X = pv1_pris_arena_q (förändring i takt), Y = pv1_sdk_q (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 3 av 4 ursprung med X (2025Q3–2026Q2). Impulser uppåt 2 (för 0, emot 2, inget 0, kan inte avgöras 0), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 3 av 4 ursprung, och 2 av 2 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 4 av 4; med den nya: 3 av 4.
  X har förändring i takt från 2025Q3.
  Ändras sambandet? Avgjorda ursprung i tidsordning: 2025Q3 talar emot, uppåt (X +441,0, Y +42,0 vid 2025Q4); 2025Q4 talar emot, uppåt (X +346,0, Y +44,9 vid 2026Q1). Senaste: talar emot (2025Q4), tidigare 0 talar för och 1 talar emot. En beskrivning utan gräns för "ändrat"; med så få ursprung kan en skillnad vara slump.
  Samma utslag som a-G.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-27, och den är därför inget utfall på osedda data.
- **Pris vid fast förmåga (GPQA) mot SDK-nedladdningar relativt kontrollpaketen, aritmetiskt medel (b, låst rad bredvid b-G):** kan inte avgöras. t = 2026Q3 (X saknas vid 2026Q1; X saknas vid 2026Q2). X = pv1_pris_gpqa_q (förändring i takt), Y = pv1_sdk_rel_q (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  X har ännu ingen förändring i takt på dagen (serien är för kort), så varje ursprung kan inte avgöras.
  Ändras sambandet? Inget ursprung har avgjorts (talar för eller talar emot) i historiken på dagen.
  Samma utslag som b-G.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-27, och den är därför inget utfall på osedda data.

## Rapporten per 2025-11-27

## Pris mot volym per 2025-11-27

**Frågan:** Följs prisfallet vid fast förmåga (G2) av högre användning (G3), och ändras sambandet?

Priset vid fast förmåga (G2) mot nedladdningar av AI-SDK:er på npm (G3). Kvartal: priset som geometriskt medel, exp(medlet av ln), av kvartalets tre månader, nedladdningarna som geometriskt medel av veckosummorna för veckorna vars torsdag ligger i kvartalet (bara hela kvartal). Det är huvudläsningens och bisakernas form sedan ägarbeslutet i registret 2026-11-27 B18, punkt 2. De låsta raderna H, a och b med aritmetiskt medel står bredvid i avsnitt 6, och beskrivningsraderna i tabellerna är aritmetiska medel. Takt = 100 × ln(värdet / värdet fyra kvartal tidigare). Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1. Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-27 PV1, X26 och B18. Klass = klass för kommersiell användning (`ai_tracker.licenses`).

### 1. Pris vid fast förmåga (X)

Lägsta blandade förstapartspris (USD per miljon tokens, 3:1) bland modeller över en fast förmågetröskel. GPQA-varianten är G2:s kärnserie. Arena-variant A är inte kärnserie och mäter från 2024-07 golvet i de billigaste prisnivåerna, eftersom tröskeln inte binder (`docs/kallor/g2_arena_pris.md`). De två första raderna är läsningarnas X, de två därefter samma serier i de låsta radernas form. Övriga rader är beskrivning.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie | Klass |
|---|---|---|---|---|---|---|---|---|
| Pris vid fast förmåga, GPQA (kärnserie), geometriskt medel | 1,9250 USD | – | – | – | 2025Q3 | 2025-09-30 | `pv1_pris_gpqa_gq` | ja |
| Pris vid fast Arena-förmåga, variant A, geometriskt medel | 0,1312 USD | -9,6 | +433,7 | +75,3 | 2025Q3 | 2025-10-01 | `pv1_pris_arena_gq` | okänd |
| Pris vid fast förmåga, GPQA, aritmetiskt medel (låst rad) | 1,9250 USD | – | – | – | 2025Q3 | 2025-09-30 | `pv1_pris_gpqa_q` | ja |
| Pris vid fast Arena-förmåga, variant A, aritmetiskt medel (låst rad) | 0,1312 USD | -10,5 | +441,0 | +86,5 | 2025Q3 | 2025-10-01 | `pv1_pris_arena_q` | okänd |
| Pris vid fast Arena-förmåga, variant B (GPT-4o) | 0,1312 USD | -394,0 | – | – | 2025Q3 | 2025-10-01 | `g2_price_at_arena_capability_4o` | okänd |
| Pris vid fast förmåga, ECI (bakåtfylld) | 0,6042 USD | – | – | – | 2025Q3 | 2025-09-30 | `g2_price_at_capability` | ja |
| Pris vid rörlig tröskel, ECI, 12 mån | 0,1500 USD | – | – | – | 2025Q3 | 2025-10-01 | `g2_price_rolling12_eci` | ja |
| Pris vid rörlig tröskel, Arena, 12 mån | 0,1604 USD | – | – | – | 2025Q3 | 2025-10-01 | `g2_price_rolling12_arena` | okänd |
| Pris vid rörlig tröskel, Arena, 6 mån | 1,5883 USD | +191,8 | – | – | 2025Q3 | 2025-10-01 | `g2_price_rolling6_arena` | okänd |
| Frontpris, Arena | 3,4375 USD | -138,6 | -185,3 | +26,7 | 2025Q3 | 2025-10-01 | `g2_price_frontier_arena` | okänd |
- Pris vid fast förmåga, GPQA (kärnserie), geometriskt medel: 2025Q4 saknar på dagen `g2_price_at_capability_gpqa` 2025-11, 2025-12.
- Pris vid fast Arena-förmåga, variant A, geometriskt medel: 2025Q4 saknar på dagen `g2_price_at_arena_capability` 2025-11, 2025-12.

### 2. Användning: nedladdningar på npm (Y)

Nedladdningar per vecka, kvartalets geometriska medel av veckosummorna. Huvudläsningens Y är openai + @anthropic-ai/sdk. Bisak b-G läser samma summa relativt kontrollpaketen react + express, så att den gemensamma tillväxten i npm (CI, speglar) tas bort så långt kontrollen speglar den. Nedladdningar är inte användare. De tre första raderna är läsningarnas Y, de tre därefter samma storheter i de låsta radernas form. Övriga paket är beskrivning.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie | Klass |
|---|---|---|---|---|---|---|---|---|
| SDK-nedladdningar, openai + @anthropic-ai/sdk, geometriskt medel | 7,9 M/vecka | +110,5 | +37,9 | +14,5 | 2025Q3 | 2025-09-30 | `pv1_sdk_gq` | okänd |
| Kontrollpaket, react + express, geometriskt medel | 89,1 M/vecka | +49,0 | +26,4 | -0,7 | 2025Q3 | 2025-09-30 | `pv1_kontroll_gq` | okänd |
| SDK relativt kontroll, geometriska medel (kvot) | 0,089 | +61,5 | +11,4 | +15,3 | 2025Q3 | 2025-09-30 | `pv1_sdk_rel_gq` | okänd |
| SDK-nedladdningar, aritmetiskt medel (låst rad) | 8,0 M/vecka | +110,8 | +36,4 | +14,0 | 2025Q3 | 2025-09-30 | `pv1_sdk_q` | okänd |
| Kontrollpaket, aritmetiskt medel (låst rad) | 89,3 M/vecka | +49,1 | +25,5 | -1,2 | 2025Q3 | 2025-09-30 | `pv1_kontroll_q` | okänd |
| SDK relativt kontroll, aritmetiska medel (kvot, låst rad) | 0,089 | +61,7 | +10,9 | +15,2 | 2025Q3 | 2025-09-30 | `pv1_sdk_rel_q` | okänd |
| npm openai | 5,9 M/vecka | +102,5 | +34,2 | +13,8 | 2025Q3 | 2025-09-30 | `g3_npm_openai_w` | okänd |
| npm @anthropic-ai/sdk | 2,1 M/vecka | +139,1 | +41,4 | +14,6 | 2025Q3 | 2025-09-30 | `g3_npm_anthropic_sdk_w` | okänd |
| npm @google/genai | 1,1 M/vecka | – | – | – | 2025Q3 | 2025-09-30 | `g3_npm_google_genai_w` | okänd |
| npm @google/generative-ai | 1,1 M/vecka | +181,8 | -48,7 | -8,9 | 2025Q3 | 2025-09-30 | `g3_npm_google_generative_ai_w` | okänd |
| npm ai (Vercel) | 2,3 M/vecka | +200,9 | -9,2 | +12,3 | 2025Q3 | 2025-09-30 | `g3_npm_vercel_ai_w` | okänd |
| npm langchain | 1,1 M/vecka | +88,7 | -4,5 | +9,3 | 2025Q3 | 2025-09-30 | `g3_npm_langchain_w` | okänd |
| npm @langchain/core | 1,5 M/vecka | +118,2 | -32,3 | -1,5 | 2025Q3 | 2025-09-30 | `g3_npm_langchain_core_w` | okänd |
| npm @modelcontextprotocol/sdk | 5,8 M/vecka | – | – | – | 2025Q3 | 2025-09-30 | `g3_npm_mcp_sdk_w` | okänd |
| npm react (kontroll) | 43,3 M/vecka | +57,9 | +29,6 | -3,4 | 2025Q3 | 2025-09-30 | `g3_npm_react_w` | okänd |
| npm express (kontroll) | 45,9 M/vecka | +41,5 | +21,7 | +0,8 | 2025Q3 | 2025-09-30 | `g3_npm_express_w` | okänd |
- SDK-nedladdningar, openai + @anthropic-ai/sdk, geometriskt medel: 2025Q4 saknar på dagen `g3_npm_openai_w` 5 veckor; `g3_npm_anthropic_sdk_w` 5 veckor.
- Kontrollpaket, react + express, geometriskt medel: 2025Q4 saknar på dagen `g3_npm_react_w` 5 veckor; `g3_npm_express_w` 5 veckor.

### 3. Läsregeln, mekaniskt

F0:s symmetriska regel: X:s förändring i takt mot Y:s förändring i takt, tecken −1, fönster 2 kvartal efter ursprunget. Gränser (låsta): X ±50, Y ±20 log-punkter. En rad per par, ingen sammanslagning. Huvudläsningen är H-G och bisakerna a-G och b-G (registret 2026-11-27 B18, punkt 2). Med det geometriska kvartalsmedlet ger en speglad prisbana (1/x) exakt det speglade utslaget.

- **Talar för, nedåt:** prisfallet blev snabbare (X ≤ −g) och användningen accelererade (Y ≥ +h). **Talar för, uppåt:** prisfallet blev långsammare (X ≥ +g) och användningen bromsade (Y ≤ −h).
- **Talar emot:** användningens takt gick åt samma håll som priset: prisfallet blev snabbare och användningen bromsade, eller prisfallet blev långsammare och användningen accelererade.
- Förändringen i takt läser om tillväxten blir snabbare eller långsammare, inte om nivån stiger eller faller. Utslaget är en beskrivning, inget test.

Alla läsningar nedan vilar bara på värden som var kända före registerposten 2026-11-27. Ingen av dem är därför ett utfall på osedda data. Nästa osedda läsning: npm-kvartalet 2026Q4 när veckan 2026-12-28–2027-01-03 är känd, omkring 2027-01-05. Huvudläsningens X (GPQA-priset) får sin första förändring i takt för 2026Q4 omkring 2027-01-01, och huvudläsningen kan avgöras tidigast med npm-kvartalet 2027Q1, omkring 2027-03-30. Sedda data avgörs per läsning (X25, punkt 1).

- **Pris vid fast förmåga (GPQA) mot SDK-nedladdningar, geometriskt medel (H-G, huvudläsning):** kan inte avgöras. t = 2025Q3 (X saknas vid 2025Q1; X saknas vid 2025Q2). X = pv1_pris_gpqa_gq (förändring i takt), Y = pv1_sdk_gq (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  X har ännu ingen förändring i takt på dagen (serien är för kort), så varje ursprung kan inte avgöras.
  Ändras sambandet? Inget ursprung har avgjorts (talar för eller talar emot) i historiken på dagen.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-27, och den är därför inget utfall på osedda data.
- **Pris vid fast Arena-förmåga (variant A) mot SDK-nedladdningar, geometriskt medel (bisak a-G):** kan inte avgöras. t = 2025Q3 (X saknas vid 2025Q1; X saknas vid 2025Q2). X = pv1_pris_arena_gq (förändring i takt), Y = pv1_sdk_gq (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  X har förändring i takt från 2025Q3.
  Ändras sambandet? Inget ursprung har avgjorts (talar för eller talar emot) i historiken på dagen.
  Bisak a-G vilar på X-värden som var sedda före posten (nivåerna för variant A stod i `g2_arena_pris.md`, registret PV1 avsnitt (f), och förändringen i takt i geometriskt medel stod i R29) och har bara beskrivande värde.
- **Pris vid fast förmåga (GPQA) mot SDK-nedladdningar relativt kontrollpaketen, geometriskt medel (bisak b-G):** kan inte avgöras. t = 2025Q3 (X saknas vid 2025Q1; X saknas vid 2025Q2). X = pv1_pris_gpqa_gq (förändring i takt), Y = pv1_sdk_rel_gq (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  X har ännu ingen förändring i takt på dagen (serien är för kort), så varje ursprung kan inte avgöras.
  Ändras sambandet? Inget ursprung har avgjorts (talar för eller talar emot) i historiken på dagen.

### 4. Att bevaka

- Nästa osedda läsning: npm-kvartalet 2026Q4 när veckan 2026-12-28–2027-01-03 är känd, omkring 2027-01-05. Huvudläsningens X (GPQA-priset) får sin första förändring i takt för 2026Q4 omkring 2027-01-01, och huvudläsningen kan avgöras tidigast med npm-kvartalet 2027Q1, omkring 2027-03-30.
- Prisserierna får en ny månad dagen efter månadsslut, npm en ny vecka söndag + 2 dagar. Ett kvartal räknas först när alla dess månader eller veckor är kända.

### 5. Förbehåll

- **Pris per token, inte per uppgift.** Resonemangsmodeller använder fler tokens per uppgift. Ett snabbare prisfall per token kan vara ett långsammare fall, eller en ökning, per uppgift (`docs/riktning.md` avsnitt 4).
- **Gemensam orsak.** En lansering kan både sänka priset (en billig modell kvalificerar) och dra nedladdningar (ny SDK-version, nya funktioner, uppmärksamhet). Regeln läser Y först kvartalet efter, men en lansering kan verka över flera kvartal. Ett utslag som talar för mekanismen visar inte att priset orsakade användningen.
- **Nedladdningar är inte användare.** CI-byggen, containerbyggen, speglar och transitiva beroenden räknas med, och ett verktyg som börjar bero på en SDK höjer nivån utan nya utvecklare. Kontrollpaketen i bisak b-G är inte stabila och tar inte bort skiften i en enskild SDK.
- **Förstapartspris.** Öppna modeller som bara säljs av tredje part ingår inte. Arena-variant A mäter golvet i de billigaste nivåerna från 2024-07, inte priset vid en fast förmåga.
- **Urval.** npm-paketen valdes 2026-11-23 med kunskap om vilka SDK:er som blev stora. Googles SDK:er ingår inte i summan, eftersom bytet mellan två paket är en migrering.
- **Korta serier.** GPQA-priset har förändring i takt först från 2026Q4. Med en handfull ursprung är detta en beskrivning och inget test, och utfall kan vara slump.
- **Licens.** npm-serierna har klassen `okänd` och `publish=False`, Arena-variant A `okänd`. GPQA-priset har `ja`. Cloudflare Radar (`nej`) används inte.
- **Historiken är backfill.** Pris- och npm-raderna är hämtade 2026-11-23–2026-11-25, i efterhand, med `known_from` satt efter en regel (prisserierna vid månadsslut eller dagen efter, npm söndag + 2 dagar), inte som arkiverade versioner. "Bara data kända på dagen" gäller därför `known_from` och inte vad källan visade då: en läsning per en tidigare dag kan innehålla revideringar och rättningar som inte var kända den dagen. 1237 av 1237 rader som läsningarna använder hämtades efter läsdagen.

### 6. Aritmetiskt kvartalsmedel (de låsta raderna H, a och b, bredvid)

De tre låsta raderna ur registret 2026-11-27 PV1, avsnitt (c), med kvartalet som aritmetiskt medel av månaderna och veckosummorna. Samma källserier, statistik, gränser, fönster och tecken som H-G, a-G och b-G. Fram till ägarbeslutet i registret 2026-11-27 B18, punkt 2, var H huvudläsningen. Med det aritmetiska medlet ger en speglad prisbana inte den speglade förändringen i takt (R29-2), så riktningen kan avgöra om en impuls uppstår. Raderna står kvar och redovisas, men de är inte huvudläsningen. Kvartalsvärdena står i avsnitt 1 och 2 (märkta "låst rad").

- **Pris vid fast förmåga (GPQA) mot SDK-nedladdningar, aritmetiskt medel (H, låst rad bredvid H-G):** kan inte avgöras. t = 2025Q3 (X saknas vid 2025Q1; X saknas vid 2025Q2). X = pv1_pris_gpqa_q (förändring i takt), Y = pv1_sdk_q (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  X har ännu ingen förändring i takt på dagen (serien är för kort), så varje ursprung kan inte avgöras.
  Ändras sambandet? Inget ursprung har avgjorts (talar för eller talar emot) i historiken på dagen.
  Samma utslag som H-G.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-27, och den är därför inget utfall på osedda data.
- **Pris vid fast Arena-förmåga (variant A) mot SDK-nedladdningar, aritmetiskt medel (a, låst rad bredvid a-G):** kan inte avgöras. t = 2025Q3 (X saknas vid 2025Q1; X saknas vid 2025Q2). X = pv1_pris_arena_q (förändring i takt), Y = pv1_sdk_q (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  X har förändring i takt från 2025Q3.
  Ändras sambandet? Inget ursprung har avgjorts (talar för eller talar emot) i historiken på dagen.
  Samma utslag som a-G.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-27, och den är därför inget utfall på osedda data.
- **Pris vid fast förmåga (GPQA) mot SDK-nedladdningar relativt kontrollpaketen, aritmetiskt medel (b, låst rad bredvid b-G):** kan inte avgöras. t = 2025Q3 (X saknas vid 2025Q1; X saknas vid 2025Q2). X = pv1_pris_gpqa_q (förändring i takt), Y = pv1_sdk_rel_q (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  X har ännu ingen förändring i takt på dagen (serien är för kort), så varje ursprung kan inte avgöras.
  Ändras sambandet? Inget ursprung har avgjorts (talar för eller talar emot) i historiken på dagen.
  Samma utslag som b-G.
  Läsningen vilar bara på värden som var kända före registerposten 2026-11-27, och den är därför inget utfall på osedda data.
