# F1: revideringar av guidance och överraskning mot guidance

Spår F1, körning 13, 2026-11-24. Förslag 2 i `docs/riktning.md`. Måtten är beskrivande. De är inget test.

**Rättat efter granskning R11 (spår X8, 2026-11-24).** Siffrorna nedan är rättade. Granskningen finns i
`docs/granskning/r11_revideringar.md` och rättningen i registerposten "F1: brottet flyttas, stängningsversionen och
känsligheter (rättning efter granskning R11)". Det viktigaste:
- CSV:n saknade Microsofts siffra från samtalet 2026-07-29 (cirka 175 mdr på den smalare basen, mening #228). Brottet
  R5-F14 ligger mellan `msft-26` (190) och den raden. `msft-29` (170) är därför en revidering nedåt på samma bas
  (−2,9). **Rullande 2026Q4 är 0,62 (n 13: 4/8/1), inte 0,67.**
- Metas utsikt för 2020 (cirka 16 mdr) saknades. Den ändrar 2020Q4–2021Q3 något.
- Två känsligheter redovisas bredvid huvudmåttet: indexet med bara siffror, och TSMC:s överraskning i US$.
- Serierna som läser CSV:n hade `publish=False`, som `guid_capex_*`. Från 2026-11-25 (ägarbeslut R11-4) publiceras
  `guid_capex_*` för Alphabet, Amazon och Meta och Metas och Alphabets överraskningar. Se Publicering nedan.

**Ordning.** Registerposten "F1: revideringar av guidance och överraskning mot guidance" committades först (commit
`b28905b`), därefter koden (`b1e3c2e`), och sist beräkningen på verklig data (denna fil). Före posten var bara detta
synligt: capex-guidancens värden i `curated/guidance_capex.csv` (filen lästes enligt uppdraget), antalet uttalanden per
kvartal i CSV:n (för valet av fönster) och TSMC:s capex-meningar (för att kontrollera tolkningen). Revideringar,
överraskningar och index hade inte räknats.

## Vad som byggdes

- `src/ai_tracker/series/guidance_revisions.py`: uttalanden, revideringar, revideringsindex, överraskningar och
  överraskningsindex. Katalogserier:
  - `f1_rev_index_4q` (huvudmått), `f1_rev_index_q`, `f1_rev_n_4q`, `f1_rev_n_q`, `f1_rev_median_4q`,
    `f1_rev_median_q` (G5);
  - `f1_surprise_tsmc`, `f1_surprise_tsmc_usd` (känslighet, R11-7), `f1_surprise_nvda`, `f1_surprise_index`,
    `f1_surprise_index_n` (G6);
  - `f1_surprise_meta_capex`, `f1_surprise_googl_capex` (G5, årsdata).
  - **Publicering (R11-4).** Serierna som läser `curated/guidance_capex.csv` (revideringsserierna, Metas och Alphabets
    överraskning och överraskningsindexet) listar `guid_capex_*` som komponenter och har därför `publish=False`, som
    de. De avslöjar samma värden: G = U × e^(−s/100). `f1_surprise_tsmc`, `f1_surprise_tsmc_usd` och
    `f1_surprise_nvda` har `publish=True`. **Ägarbeslut 2026-11-25:** `guid_capex_*` för Alphabet, Amazon och Meta
    publiceras (alla rader från sec.gov, klass `ja`). Metas och Alphabets överraskningar läser bara bolagets egna rader
    och listar nu bara dess serier, så de publiceras också. Revideringsserierna och överraskningsindexet listar
    Microsofts serier och har kvar `publish=False`. I ögonblicksbildens avsnitt `expectations` visas värdena per bolag,
    och Microsofts och de poolade måtten har bara period och datum.
- `src/ai_tracker/sources/tsmc_capex_guidance.py`: TSMC:s capex-budget för året, en deterministisk tolkning av samma
  6-K som `tsmc_guidance` läser. Serierna `tsmc_guid_capex_lo/hi` (G6, år). Se `docs/kallor/guidance.md`.
- `src/ai_tracker/sources/tsmc_usd_revenue.py` (X8): TSMC:s kvartalsintäkt i US$ ur pressmeddelandet i samma 6-K,
  serien `tsmc_rev_usd_q` (G6, 2016Q4–2026Q3, 40 kvartal). Bara meningen "In US dollars, <kvartal> quarter revenue was
  $x billion" kodas. Den finns i alla 40 kvartalsrapporter från 2017-01.
- `src/ai_tracker/state/expectations.py`: avsnittet `expectations` i månadens ögonblicksbild, gruppen "Förväntningar mot
  utfall". Det räknas aldrig i en grens diffusionsindex (`in_diffusion` är alltid falskt) och har ingen takt, bara nivå
  och percentil. Ett anrop i `snapshot.write`. Om avsnittet fallerar sparas felet i avsnittet, och ögonblicksbilden
  skrivs ändå.
- Glesa serier (index med n < 3, överraskningsindex med färre än 2 bolag) står i `warehouse.KNOWN_GAPS`.

## Data

Basen var tom, så allt hämtades i spårets `data/`: TSMC:s 6-K (guidance, månadsintäkt och capex-budget), Nvidias
8-K, companyfacts för capex och `rev_nvda`, och den kurerade CSV:n. Inget var blockerat i detta spår. Täckningen
för capex-guidancen är densamma som i E1. Alphabets och Amazons samtal finns inte i EDGAR, och `abc.xyz` och
`ir.aboutamazon.com` nekas av proxyn (BLOCKED, som i `docs/kallor/guidance.md`).

TSMC:s capex-budget: 56 meningsträffar och 35 vintages för 23 år (2004–2026). Under 2016–2021 står budgeten i
pressmeddelandet i januari och när den ändras. **Från 2022 står bara januaribudgeten i 6-K** (R11-8). Pressmeddelandet
2022-10-13 har ingen capex-utsikt. Ändringar som TSMC bara sa i samtalet finns inte här, och `investor.tsmc.com` nekas
av proxyn. TSMC:s capex-budget ger därför inga revideringar efter 2021, eftersom källan saknas, inte för att planen
var oförändrad. Kända okodade besked:
- "slightly above US$9.5 billion" (2016-10-13), registrerat undantag;
- alla besked för 2003 (andra former: "capex in 2003", kolon i stället för verb, "near the mid point", "approach");
- 2009-07-30: ett belopp står mellan subjekt och verb, vilket koden inte tillåter (inget belopp och inget meningsslut
  mellan dem). Höjningen till 2,3 mdr dateras därför en dag sent, från 2009-07-31;
- 2012-04-26: en höjning till 8–8,5 mdr (cirka +32) i en annan ordalydelse saknas. Tabellen per år saknar 2012.

TSMC:s revideringar av capex-budgeten i tabellen nedan är alltså en **undre gräns**.

## Revideringar

78 revideringar. 19 är TSMC:s före 2020-07 och 59 ligger i indexperioden (från 2020Q3). Räknat per år och bolag
(`known_from`):

| Bolag | Mått | År: antal (upp/oförändrad/ned) |
|---|---|---|
| Meta | capex | 2020: 1 (0/1/0), 2021: 4 (0/2/2), 2022: 5 (2/2/1), 2023: 4 (0/1/3), 2024: 6 (5/1/0), 2025: 4 (3/1/0), 2026: 3 (3/0/0) |
| Alphabet | capex | 2024: 3 (0/3/0), 2025: 4 (2/2/0), 2026: 5 (1/4/0) |
| Amazon | capex | 2023: 2 (0/2/0), 2024: 3 (1/2/0), 2025: 3 (0/3/0), 2026: 4 (0/4/0) |
| Microsoft | capex | 2024: 1 (0/1/0), 2025: 4 (2/2/0), 2026: 1 (0/0/1) |
| TSMC | capex | 14: 2004, 2006, 2007, 2009 (2), 2013, 2015 (2) och 2016–2021 en per år. 10 upp och 4 ned. Undre gräns, se ovan |
| TSMC | intäkt | 7: 2007, 2008, 2009, 2015 (2), 2016 och 2019. 4 upp, 1 oförändrad och 2 ned |
| Nvidia | intäkt | inga (ingen uppdatering mitt i kvartalet 2017Q2–2026Q4, som R5 fann) |

- I indexperioden har 31 av 59 revideringar en siffra (17 upp, 7 oförändrade, 7 ned). 28 är riktningar (4 upp, 24
  oförändrade, 0 ned). Riktningarna kommer från Amazon (11), Alphabet (9), Microsoft (5) och Meta (3). Meta står för
  27 av 59.
- Bara en del är ändringar. Revideringar uppåt eller nedåt per år: 2021: 3, 2022: 3, 2023: 3, 2024: 6, 2025: 7 och
  2026: 5 (till 2026-11-24). Resten är oförändrade besked.
- **Sedan 2024-01 har 15 revideringar en siffra: 13 uppåt, en oförändrad (Amazon 2026-04) och en nedåt**, Microsofts
  sänkning för 2026 (2026-10-28, −2,9). Före den var den senaste sänkningen Metas för 2023 (2023-10-25).
- **Microsofts brott.** I samtalet 2026-07-29 sa Microsoft att planen för 2026 var oförändrad utom effekten av den nya
  nyttjandeperioden (#227), och att skiftet till operationell leasing ger cirka 175 mdr (#228). Bolaget kvantifierade
  alltså brottet självt: −8,2 mot 190 mdr. Raden `msft-r11f1` startar det nya objektet och är ingen revidering. Den
  redovisas i avsnittet `expectations` (`break_statements`) med sin storlek. Oktobersiffran (170 mdr, skälet är
  förseningar hos tredjepartsleverantörer) är en sänkning på samma bas.

**Senaste värden** (as of 2026-11-24, samma som ögonblicksbilden 2026-11-30 om inget nytt kommer):

| Mått | Period | Värde | n (upp/oförändrad/ned) | Median (log ×100) | known_from | Percentil |
|---|---|---|---|---|---|---|
| Revideringsindex, rullande 4 kvartal | 2026Q4 | **0,62** | 13 (4/8/1) | +1,8 (6 med storlek) | 2026-10-29 | 56 (24 kvartal) |
| Revideringsindex, kvartal | 2026Q3 | 0,67 | 3 (1/2/0) | +1,8 (1) | 2026-07-31 | – |
| Revideringsindex, kvartal | 2026Q4 | 0,50 | 3 (1/1/1) | −0,5 (2) | 2026-10-29 | 6 (9 kvartal) |

**Förloppet** (rullande 4 kvartal): 0,67 i 2021Q1 och 0,60 i 2021Q2, 0,38–0,60 från 2021Q3 till 2023Q2, 0,33 i 2023Q3
och 0,25 i 2023Q4, när Meta sänkte 2023 flera gånger. Därefter 0,42 (2024Q1), 0,56 (2024Q2), 0,68–0,73 från 2024Q3 till
2026Q3 och 0,62 i 2026Q4. Medianstorleken låg på 0 från 2021Q1 till 2023Q2, var −2,8 och −5,9 i 2023Q3–Q4 och +2,6
till +7,9 från 2024Q3 till 2026Q1. I de senaste tre kvartalen är den +1,8 till +2,9.

**Känslighet för definitionsbrottet** (rullande 4 kvartal, 2026Q4):

| Variant | Index | n (upp/oförändrad/ned) | Microsofts storlek |
|---|---|---|---|
| Huvudmått: julisiffran finns, brottet på `msft-r11f1` | **0,62** | 13 (4/8/1) | −2,9 |
| Brottet ignoreras (utan julisiffran och utan brott) | 0,62 | 13 (4/8/1) | −11,1 |
| F1:s tidigare variant (brottet på `msft-29`, utan julisiffran) | 0,67 | 12 (4/8/0) | – |
| Julisiffran finns, inget brott alls | 0,57 | 14 (4/8/2) | −8,2 (juli) och −2,9 |

Den sista raden räknar bolagets egen omräkning som en sänkning. Det gör inte huvudmåttet, eftersom Microsoft sa att
planen var oförändrad utom definitionen.

**Känslighet: bara siffror (R11-6).** Riktningarna är 28 av 59 händelser, och 24 av dem är oförändrade. En upprepad
riktning som "ökar mot förra året" säger inget om nivån: Alphabets siffra för 2025 steg från 75 till 85 och 92 mdr
medan riktningskoden stod still. Varje sådan händelse drar indexet mot 0,5. Rullande 4 kvartal:

| Kvartal | Alla | Bara siffror | Riktningar (oförändrade av alla) |
|---|---|---|---|
| 2023Q4 | 0,25 (n 6) | 0,12 (n 4) | 2 av 2 |
| 2024Q3 | 0,68 (n 11) | 0,75 (n 4) | 5 av 7 |
| 2024Q4–2026Q1 | 0,68–0,73 (n 12–17) | **1,00** (n 3–5) | 7–10 av 9–12 |
| 2026Q2–Q3 | 0,70–0,71 | 0,92–0,93 | |
| 2026Q4 | 0,62 (n 13) | 0,75 (n 6: 4/1/1) | 7 av 7 |

Till och med 2023Q2 är de två lika, eftersom de första riktningshändelserna kommer 2023. Det publicerade indexet visar alltså en måttlig
övervikt uppåt, medan siffrorna nästan bara gick uppåt 2024–2026. Båda står i avsnittet `expectations`
(`revisions_numeric_only` och `composition_main_window` med upp, oförändrade och ned för siffror och riktningar).

## Överraskning mot guidance

s = 100 × (ln utfall − ln guidancens mittpunkt), första versionen av utfallet mot den senaste guidancen som var känd före.

| Bolag | Perioder | Medel s | Andel > 0 | Senaste | s | z | Percentil (egen historik) | known_from |
|---|---|---|---|---|---|---|---|---|
| TSMC, intäkt (NT$) | 82 (2006Q2–2026Q3) | +1,6 | 87 % | 2026Q3 | +3,3 | +1,77 | 82 | 2026-10-08 |
| TSMC, intäkt i US$ (känslighet) | 37 (2017Q3–2026Q3) | +1,5 | 86 % | 2026Q3 | +3,3 | – | 88 | 2026-10-15 |
| Nvidia, intäkt | 37 (2017Q2–2026Q2) | +4,4 | 92 % | 2026Q2 | +5,6 | +0,76 | 61 | 2026-08-26 |
| Meta, capex för året | 5 (2021–2025) | +0,8 | 80 % | 2025 | +1,7 | +1,90 | 90 (5 år) | 2026-01-29 |
| Alphabet, capex för året | 1 (2025) | −0,6 | – | 2025 | −0,6 | – | – | 2026-02-05 |

**Överraskningsindex** (medel av z, minst 2 bolag): 33 kvartal, 2018Q2–2026Q2. Senaste: **2026Q2 = 0,70** (n 2: TSMC och
Nvidia), känt 2026-08-26, percentil 53. Bara 2025Q4 har tre bolag (Meta). För 2026Q3 finns bara TSMC än. Nvidias
utfall kommer med 10-Q:n, några dagar efter 8-K:n 2026-11-17. Rättningen efter R11 ändrar inte indexet: Metas
överraskning börjar som registrerat 2021, så raderna för 2020 används bara i revideringsindexet.

**TSMC i US$ (känslighet, R11-7).** Från 2017Q3 guidar TSMC i US$, och B2:s bas räknar om till NT$ med antagen kurs.
s i NT$ innehåller därför kursens avvikelse från antagandet. Med US$-intäkten ur samma 6-K går den att skilja ut:
valutadelen = s(NT$) − s(US$) = 100 × (ln faktisk kurs − ln antagen kurs). För 2017Q3–2026Q3 (37 kvartal):
- SD för s i NT$ 1,97, i US$ 1,67, och för valutadelen 1,31. Korrelationen mellan s i NT$ och i US$ är 0,75.
- Valutadelen är i medel +0,2. Den är större än 2 i absolutbelopp i 5 kvartal, och tecknet skiljer sig i 5 kvartal.
- 2025Q2: −0,2 i NT$ men +4,3 i US$ (valutadel −4,6). 2025Q3: +5,2 mot +2,1 (+3,1). 2026Q3: +3,3 mot +3,3.

TSMC:s z, och därmed överraskningsindexet, mäter alltså delvis valutan. B2:s bas är rätt för N2, eftersom målet är i
NT$. För frågan "överträffar TSMC sin egen guidance" är US$-serien `f1_surprise_tsmc_usd` det renare måttet. Den ingår
inte i indexet.

## Ärliga noter

- **Litet n.** I indexperioden kommer 5–15 revideringar per år, och de flesta är oförändrade besked. Ändringarna är 3–7
  per år. Ett kvartal med n ≥ 3 är ovanligt före 2024, så det rullande indexet är huvudmåttet. Det är beskrivande, och
  nivån kan vara slump. En enda sänkning flyttar 2026Q4 från 0,67 till 0,62.
- **Vad registret räknade per kvartal (R11-9).** Posten säger "0–5 per kvartal, färre än 3 i 14 av 24". Det stämmer
  inte med CSV:ns rader (1–9 per kvartal, färre än 3 i 8). Det stämmer ungefär med antalet uttalanden som har ett
  tidigare uttalande i samma kedja, alltså indexets nämnare: 0–5, färre än 3 i 15 av 24 med TSMC och 16 med bara
  CSV:n. Det antalet har ingen riktning, så valet av fönster berodde inte på utfallet.
- **Två händelser för samma rapport.** Alphabets och Metas siffror och riktningar för samma år är olika kedjor. Ett
  rapporttillfälle kan därför ge en siffra och en riktning.
- **Sammansättning.** Meta väger tyngst, och riktningarna (Alphabet, Amazon, Microsoft) är nästan alltid "oförändrad".
  Indexet mäter alltså mest Metas siffror och de andras upprepade riktningar. Täckningen beror på vad som står i
  EDGAR: Alphabets och Amazons samtal saknas.
- **Upprepningar räknas för capex** (som i PMI) men inte för TSMC och Nvidia, som inte upprepar kvartalsguidancen.
  Det står i registret. I indexperioden har asymmetrin ingen effekt: TSMC:s 6-K från 2016 upprepar aldrig
  capex-budgeten oförändrad, och Nvidia uppdaterar aldrig mitt i kvartalet. Före 2016 upprepar TSMC budgeten i cirka
  tio rapporter. De blir inga händelser, så TSMC:s 14 capex-händelser är bara ändringar.
- **z har inget medelvärde avdraget.** TSMC och Nvidia överträffar sin guidance nästan alltid, så indexet ligger över 0
  i 28 av 33 kvartal. Percentilen visar om en period är ovanlig.
- **TSMC i NT$.** Från 2017Q3 är G = US$-mittpunkten × antagen växelkurs (B2:s bas), så s innehåller valutans avvikelse
  från antagandet. Valutadelen redovisas ovan (känsligheten i US$).
- **Nvidia från 2017Q2** (granskat i R5, som i B3). Utfallet är total intäkt, daterat med 10-Q:n i XBRL. Sedan 2024Q2
  lämnas 10-Q samma dag som 8-K. 2017–2024 kom den 5–30 dagar senare i 11 kvartal. Dateringen är alltså konservativ.
- **Metas z** bygger på fyra tidigare år. En SD ur fyra värden är mycket osäker, så z = 1,90 för 2025 ska läsas med det
  förbehållet.
- **Stängningsversionen** dateras kvartalets sista dag men skapas först dagen efter (registret, R11-2). Avsnittet
  `expectations` för en dag är därför lika med seriernas as_of den dagen, utom en stängningsversion daterad samma dag.
- **Dagens datum.** Hämtningen använder nu dagens datum i UTC, som ögonblicksbilden.
- **Metas och Alphabets G** är den sista guidancen före utfallet, alltså från oktober. Överraskningen blir därför liten
  (under 2 %). Den mäter hur väl bolaget kände sitt eget fjärde kvartal, inte hur planen för året ändrades. Det gör
  revideringarna.
- **Inte med:** Amazon och Microsoft (andra definitioner), TSMC:s capex (inget utfall för capex i US$ i katalogen) och
  riktningar.

## Förslag till månadsbrevet (inte infört, `letter.py` är orört)

> **Förväntningar mot utfall.** Bolagens egna capex-planer: revideringsindex [värde] för de fyra senaste kvartalen
> ([n] revideringar, varav [upp] uppåt, [ned] nedåt och [oförändrade] oförändrade; medianrevidering [median] %). Senaste
> utfall mot egen guidance: TSMC [s] % ([kvartal]), Nvidia [s] % ([kvartal]). Överraskningsindex [värde] ([n] bolag,
> percentil [p]). Måtten räknas inte i grenarnas index.

## Tester

`tests/test_guidance_revisions.py`, 44 syntetiska tester utan nät: revideringens tecken och storlek, dödbandet,
upprepning som oförändrad, nytt objekt mot revidering (TSMC och Nvidia), fönstret för samma händelse, riktningar och
baser, definitionskod och definitionsbrott, indexets n ≥ 3, rullande fönster och stängningsversion, att inget dateras
framåt, standardisering först efter 4 tidigare överraskningar, överraskningsindex med minst 2 bolag, TSMC:s B2-bas och
guidance känd före utfallet, capex-summan av första versioner, as_of-trunkering med identiska värden (sex datum),
TSMC-tolkningens godkända och avvisade former, katalogkontraktet och ögonblicksbildens avsnitt.

Samma trunkeringskontroll på verklig data (sju datum 2021-06-30–2026-10-31): index, överraskningar och
överraskningsindex är identiska, 0 avvikelser. Hela sviten: 1 469 passed, 124 skipped, 1 xfailed (main: 1 425 passed).
Den kördes utan spårets egen tabell, eftersom testerna för verklig data annars körs på en ofullständig tabell och
fallerar på serier som spåret inte har hämtat (till exempel `capex_hyp4`).

**Efter rättningen (X8).** `tests/test_x8_revideringar.py` (12 syntetiska tester): brottsraden med storlek och nästa rad
som revidering, känsligheten med bara siffror, tolkningen av US$-intäkten och valutadelen, Metas start 2021,
kandidatregeln med meningen efter en capex-mening, publiceringsgrinden och avsnittets nya delar. R11:s sex strikta
xfail-test passerar nu som vanliga test. Trunkeringstesterna räknar på dagen efter trunkeringsdatumet, eftersom en
stängningsversion daterad den dagen skapas först då (R11-2).

**Vad som inte är kontrollerat:** TSMC-tolkningens omatchade kandidatmeningar lästes bara för 2016–2026. R11 jämförde
18 dokument 2004–2021 på sec.gov och fann inga falska positiva och de luckor som listas under Data. Det kan finnas fler
okodade uttalanden 2004–2015. De påverkar inte indexperioden. TSMC:s egna samtal går inte att läsa här
(`investor.tsmc.com` nekas).
