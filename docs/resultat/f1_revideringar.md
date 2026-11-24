# F1: revideringar av guidance och överraskning mot guidance

Spår F1, körning 13, 2026-11-24. Förslag 2 i `docs/riktning.md`. Måtten är beskrivande. De är inget test.

**Ordning.** Registerposten "F1: revideringar av guidance och överraskning mot guidance" committades först (commit
`b28905b`), därefter koden (`b1e3c2e`), och sist beräkningen på verklig data (denna fil). Före posten var bara detta
synligt: capex-guidancens värden i `curated/guidance_capex.csv` (filen lästes enligt uppdraget), antalet uttalanden per
kvartal i CSV:n (för valet av fönster) och TSMC:s capex-meningar (för att kontrollera tolkningen). Revideringar,
överraskningar och index hade inte räknats.

## Vad som byggdes

- `src/ai_tracker/series/guidance_revisions.py`: uttalanden, revideringar, revideringsindex, överraskningar och
  överraskningsindex. Katalogserier (alla `publish=True`):
  - `f1_rev_index_4q` (huvudmått), `f1_rev_index_q`, `f1_rev_n_4q`, `f1_rev_n_q`, `f1_rev_median_4q`,
    `f1_rev_median_q` (G5);
  - `f1_surprise_tsmc`, `f1_surprise_nvda`, `f1_surprise_index`, `f1_surprise_index_n` (G6);
  - `f1_surprise_meta_capex`, `f1_surprise_googl_capex` (G5, årsdata).
- `src/ai_tracker/sources/tsmc_capex_guidance.py`: TSMC:s capex-budget för året, en deterministisk tolkning av samma
  6-K som `tsmc_guidance` läser. Serierna `tsmc_guid_capex_lo/hi` (G6, år). Se `docs/kallor/guidance.md`.
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

TSMC:s capex-budget: 56 meningsträffar och 35 vintages för 23 år (2004–2026). Från 2016 står budgeten i
pressmeddelandet i januari och när den ändras. Ett besked kodades inte: "slightly above US$9.5 billion" (2016-10-13).

## Revideringar

76 revideringar. 19 är TSMC:s före 2020-07 och 57 ligger i indexperioden (från 2020Q3). Räknat per år och bolag
(`known_from`):

| Bolag | Mått | År: antal (upp/oförändrad/ned) |
|---|---|---|
| Meta | capex | 2021: 4 (0/2/2), 2022: 5 (2/2/1), 2023: 4 (0/1/3), 2024: 6 (5/1/0), 2025: 4 (3/1/0), 2026: 3 (3/0/0) |
| Alphabet | capex | 2024: 3 (0/3/0), 2025: 4 (2/2/0), 2026: 5 (1/4/0) |
| Amazon | capex | 2023: 2 (0/2/0), 2024: 3 (1/2/0), 2025: 3 (0/3/0), 2026: 4 (0/4/0) |
| Microsoft | capex | 2024: 1 (0/1/0), 2025: 4 (2/2/0) |
| TSMC | capex | 14: 2004, 2006, 2007, 2009 (2), 2013, 2015 (2) och 2016–2021 en per år. 10 upp och 4 ned |
| TSMC | intäkt | 7: 2007, 2008, 2009, 2015 (2), 2016 och 2019. 4 upp, 1 oförändrad och 2 ned |
| Nvidia | intäkt | inga (ingen uppdatering mitt i kvartalet 2017Q2–2026Q4, som R5 fann) |

- I indexperioden har 29 av 57 revideringar en storlek. 28 är riktningar. Meta står för 26 av 57.
- Bara en del är ändringar. Revideringar uppåt eller nedåt per år: 2021: 3, 2022: 3, 2023: 3, 2024: 6, 2025: 7 och
  2026: 4 (till 2026-11-24). Resten är oförändrade besked.
- **Ingen revidering nedåt sedan 2024-01** i det som räknas. Den sista var Metas sänkning för 2023 (2023-10-25).

**Senaste värden** (as of 2026-11-24, samma som ögonblicksbilden 2026-11-30 om inget nytt kommer):

| Mått | Period | Värde | n (upp/oförändrad/ned) | Median (log ×100) | known_from | Percentil |
|---|---|---|---|---|---|---|
| Revideringsindex, rullande 4 kvartal | 2026Q4 | 0,67 | 12 (4/8/0) | +1,8 (5 med storlek) | 2026-10-29 | 59 (23 kvartal) |
| Revideringsindex, kvartal | 2026Q3 | 0,67 | 3 (1/2/0) | +1,8 (1) | 2026-07-31 | 19 (8 kvartal) |
| Revideringsindex, kvartal | 2026Q4 | inget (n = 2) | 2 (1/1/0) | +1,8 (1) | 2026-10-29 | – |

**Förloppet** (rullande 4 kvartal): 0,63 i 2021Q2, 0,38–0,60 från 2021Q3 till 2023Q2, 0,33 i 2023Q3 och 0,25 i 2023Q4,
när Meta sänkte 2023 flera gånger. Därefter 0,42 (2024Q1), 0,56 (2024Q2) och 0,67–0,73 från 2024Q3. Medianstorleken
låg på 0 från 2021Q3 till 2023Q2, var −2,8 och −5,9 i 2023Q3–Q4 och +2,6 till +7,9 från 2024Q3 till 2026Q1. I de senaste tre kvartalen är den
+1,8 till +2,9.

**Känslighet för definitionsbrottet.** Regeln om `msft-29` (R5-F14) registrerades före beräkningen, men raden och dess
värde (cirka 170 mdr mot 190 mdr) var synliga. Utan regeln hade Microsofts sänkning för 2026 räknats som en revidering
nedåt (−11,1). Då hade 2026Q4 fått 0,62 (n 13, 1 ned) i det rullande indexet och 0,50 (n 3) i kvartalsindexet. Sänkningen
beror enligt bolaget på förseningar hos tredjepartsleverantörer, men basen blev också smalare, och de två delarna går inte
att skilja åt. Regeln gäller, och siffran utan regeln redovisas här.

## Överraskning mot guidance

s = 100 × (ln utfall − ln guidancens mittpunkt), första versionen av utfallet mot den senaste guidancen som var känd före.

| Bolag | Perioder | Medel s | Andel > 0 | Senaste | s | z | Percentil (egen historik) | known_from |
|---|---|---|---|---|---|---|---|---|
| TSMC, intäkt (NT$) | 82 (2006Q2–2026Q3) | +1,6 | 87 % | 2026Q3 | +3,3 | +1,77 | 82 | 2026-10-08 |
| Nvidia, intäkt | 37 (2017Q2–2026Q2) | +4,4 | 92 % | 2026Q2 | +5,6 | +0,76 | 61 | 2026-08-26 |
| Meta, capex för året | 5 (2021–2025) | +0,8 | 80 % | 2025 | +1,7 | +1,90 | 90 (5 år) | 2026-01-29 |
| Alphabet, capex för året | 1 (2025) | −0,6 | – | 2025 | −0,6 | – | – | 2026-02-05 |

**Överraskningsindex** (medel av z, minst 2 bolag): 33 kvartal, 2018Q2–2026Q2. Senaste: **2026Q2 = 0,70** (n 2: TSMC och
Nvidia), känt 2026-08-26, percentil 53. Bara 2025Q4 har tre bolag (Meta). För 2026Q3 finns bara TSMC än. Nvidias
utfall kommer med 10-Q:n, några dagar efter 8-K:n 2026-11-17.

## Ärliga noter

- **Litet n.** I indexperioden kommer 5–15 revideringar per år, och de flesta är oförändrade besked. Ändringarna är 3–7
  per år. Ett kvartal med n ≥ 3 är ovanligt före 2024, så det rullande indexet är huvudmåttet. Det är beskrivande, och
  nivån kan vara slump.
- **Sammansättning.** Meta väger tyngst, och riktningarna (Alphabet, Amazon, Microsoft) är nästan alltid "oförändrad".
  Indexet mäter alltså mest Metas siffror och de andras upprepade riktningar. Täckningen beror på vad som står i
  EDGAR: Alphabets och Amazons samtal saknas.
- **Upprepningar räknas för capex** (som i PMI) men inte för TSMC och Nvidia, som inte upprepar kvartalsguidancen.
  Det står i registret.
- **z har inget medelvärde avdraget.** TSMC och Nvidia överträffar sin guidance nästan alltid, så indexet ligger över 0
  i 28 av 33 kvartal. Percentilen visar om en period är ovanlig.
- **TSMC i NT$.** Från 2017Q3 är G = US$-mittpunkten × antagen växelkurs (B2:s bas), så s innehåller valutans avvikelse
  från antagandet. Den kan inte skiljas ut med våra serier, eftersom TSMC:s kvartalsintäkt i US$ saknas i katalogen.
- **Nvidia från 2017Q2** (granskat i R5, som i B3). Utfallet är total intäkt, daterat med 10-Q:n i XBRL.
- **Metas och Alphabets G** är den sista guidancen före utfallet, alltså från oktober. Överraskningen blir därför liten
  (under 2 %). Den mäter hur väl bolaget kände sitt eget fjärde kvartal, inte hur planen för året ändrades. Det gör
  revideringarna.
- **Inte med:** Amazon och Microsoft (andra definitioner), TSMC:s capex (inget utfall i US$) och riktningar.

## Förslag till månadsbrevet (inte infört, `letter.py` är orört)

> **Förväntningar mot utfall.** Bolagens egna capex-planer: revideringsindex [värde] för de fyra senaste kvartalen
> ([n] revideringar, varav [upp] uppåt, [ned] nedåt och [oförändrade] oförändrade; medianrevidering [median] %). Senaste
> utfall mot egen guidance: TSMC [s] % ([kvartal]), Nvidia [s] % ([kvartal]). Överraskningsindex [värde] ([n] bolag,
> percentil [p]). Måtten räknas inte i grenarnas index.

## Tester

`tests/test_guidance_revisions.py`, 45 syntetiska tester utan nät: revideringens tecken och storlek, dödbandet,
upprepning som oförändrad, nytt objekt mot revidering (TSMC och Nvidia), fönstret för samma händelse, riktningar och
baser, definitionskod och definitionsbrott, indexets n ≥ 3, rullande fönster och stängningsversion, att inget dateras
framåt, standardisering först efter 4 tidigare överraskningar, överraskningsindex med minst 2 bolag, TSMC:s B2-bas och
guidance känd före utfallet, capex-summan av första versioner, as_of-trunkering med identiska värden (sex datum),
TSMC-tolkningens godkända och avvisade former, katalogkontraktet och ögonblicksbildens avsnitt.
