# R30 – oberoende granskning av körning 18 (B18, DA1)

Granskningsspår R30, 2026-11-27, gren `auto18/r30-korning18` (bas `auto18/integration18`, `496ecae`, med `3edc854` som
förfader). R30 har inte skrivit koden, registerposterna eller rapporterna. Spårens egna dokument användes bara för att
veta vad som påstods. Varje påstående prövades mot koden, registret, observationstabellen eller källdokumentet.

Underlag: `src/ai_tracker/followed/` (`common`, `kreditlagret`, `prisvolym`, `ledtid`), `sources/acquisitions.py`,
`curated/acquisitions.csv`, de två registerposterna 2026-11-27 DA1 och B18, observationstabellen i huvudutcheckningen
(876 serier) och alla 48 av Dells, Super Micros och Equinix 10-Q och 10-K bakom DA1:s 47 rader. Dokumenten hämtades på
nytt från www.sec.gov med den generiska klientidentiteten ur miljön och sparades bara i R30:s scratch-katalog, inte i
någon `data/raw`. Rapporterna på `3edc854` kördes i en egen worktree utan gren (detached) med samma delade data. Ingen
produktionskod och inga dokument från spåren är ändrade. Testerna står i `tests/test_r30_korning18.py`: fastlåsta
registerposter och 16 rader som R30 läst i källan, märkenas kvartal och riktning per läsdag, en omräkning av L2 utan
projektets kod och fynden R30-1 till R30-3 som `xfail(strict=True)`.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Git-ordningen | **OK.** Båda registerposterna är committade ensamma, före kod, data och utslag, och oförändrade genom mergarna. DA1:s första hämtning från EDGAR är 19 sekunder efter DA1:s post |
| 2. B18 | **Ändrar bara det besluten säger.** KL1 skiljer mot `3edc854` bara i stycket om sedda data (avsnitt 1–7) och i övergångsnotiserna (avsnitt 8, beslut 1). PV1:s antenn och huvudutslag följer H-G, H, a och b står kvar och redovisas. Ingen rapport har kvar "väntar på ägarens bekräftelse" |
| 3. DA1 mot 10-K/10-Q | **47 av 47 meningshashar, inlämningsdagar och formulär rätt** på nyhämtade dokument. 16 rader lästa i texten (8 för Dell): kvartal *a*, riktning och etikett per inlämningsdag stämmer. Tre brister: täckningen anges inte (R30-1), Dells räkenskapsgränser (R30-2, latent) och beskrivningen av Equinix 2025Q4 (R30-3) |
| 4. Omräkning av L2 | **Rätt.** Alla fyra L2-läsningar per 2026-11-27 och DA1:s gräns (28,7 och 19,1 mdr USD) räknade om direkt ur `observations.parquet` med pandas |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Inget must_fix. Tre should_fix (R30-1 till R30-3) och tre anmärkningar. Inget
fynd ändrar ett utslag eller ett värde per 2026-11-27 eller 2025-11-27. R30-1 bör rättas före Dells inlämning omkring
2026-12-09, som ger L2:s första osedda läsning.

## 1. Git-ordningen

Tider i UTC (`git log --graph 3edc854..HEAD`):

| Spår | Registerpost (bara `docs/mattregister.md`) | Första kod eller data | Utslag eller rapport |
|---|---|---|---|
| DA1 | `6899971` 13:40:57 | `b4eabec` 13:54:52 | `3dd2f1b` 13:57:10 |
| B18 | `6981c7a` 13:42:33 (fixturer `e11c9eb` 13:43:00) | `8f93667` 13:51:05 | `f894b7a` 13:56:39 |

- Varje post finns i HEAD med exakt samma text som i sin commit, och diffen `3edc854..HEAD` i registret har inga
  borttagna rader. Integrationen lägger DA1 före B18, i committordning.
- DA1:s post säger att den skrevs innan inlämningarna lästes. Spårets råcache visar den första hämtningen 13:41:16, efter
  posten 13:40:57. B18:s post säger att rapporterna på `3edc854` kördes före posten som jämförelse, och det är tillåtet.
- Fixturerna i HEAD stämmer mot registret (`python -m ai_tracker.site_bundle fixtures` ger ingen diff). Se R30-6 för en
  mellancommit.

## 2. B18 mot de tre besluten

R30 körde `python -m ai_tracker.followed <fråga> --as-of D` på `3edc854` och på HEAD och jämförde utdata rad för rad.

- **KL1 (beslut 3).** Per 2026-11-27 skiljer avsnitt 1–7 bara i ett nytt stycke om sedda data före läsningarna: alla fem
  läsningar är sedda, och nästa osedda läsning kommer med Oracle omkring 2026-12-11. Per 2025-11-27 och 2026-11-25 är
  avsnitt 1–7 byte för byte desamma. Övriga skillnader är övergångsnotiserna i avsnitt 8 (beslut 1). Inga utslag, inga
  tal och ingen "A har gällt" ändras. Antennen har den nya faktan "Huvudläsningen på osedda data: nej". Mekanismen
  (`locked_seen`) jämför varje värde som regel (c) läser, alltså takten vid *t* − 2 för varje pris- och beroendemått,
  capex-förändringen vid *t* och det inre lagrets vid dess kvartal, mot en beräkning per 2026-11-25. Det är samma
  mekanism som S1:s och X25:s. B18:s syntetiska test med en revidering 2026-12-11 gör yttre lagret och Oracle osedda och
  lämnar de tre andra sedda.
- **PV1 (beslut 2).** `MAIN = "H-G"`, och antennens utslag, `t`, fakta och nästa osedda läsning läses ur H-G och
  `pv1_*_gq`. `main_inputs` är samma katalogserier som förut. H, a och b räknas som förut och står i avsnitt 6 och i en
  fakta. Utslagen är desamma för de låsta och de geometriska raderna båda dagarna (2026-11-27: kan inte avgöras, inget av
  mönstren, kan inte avgöras; 2025-11-27: kan inte avgöras för alla tre). Sedda data avgörs per läsning för alla sex
  raderna mot PV1:s registerdag. Påståendet att Arena-värdena i geometriskt medel stod i R29 stämmer (R29 avsnitt 4).
- **F0:s notis (beslut 1).** `PENDING_OWNER` är borttagen ur `common`, och ingen genererad rapport (KL1, LT1, BG1, EL1,
  PV1 per 2026-11-27 och 2025-11-27) innehåller "väntar på ägarens bekräftelse". Båda talen står kvar. De äldre
  kursiva notiserna i `docs/resultat/` som nämner tillägget har en B18-notis ovanför sig.
- `docs/resultat/{kreditlagret,prisvolym,ledtid}.md` och `antenner.md` innehåller varje rad som HEAD genererar per
  2026-11-27 och 2025-11-27.

## 3. DA1 mot 10-K och 10-Q

R30 hämtade alla dokument som de 47 raderna pekar på, tolkade dem med projektets textuppdelning (så att platsen betyder
samma sak) och kontrollerade formulär, inlämningsdag, URL mot `primaryDocument` i EDGAR:s submissions och meningens
SHA-256 på platsen. Alla 47 stämmer. Meningarna i basens `data/raw/acquisitions_sentences` är byte för byte desamma som
R30:s.

R30 läste sedan 16 rader i texten (Dell först) och letade efter förvärv som saknas:

| Rad | Vad R30 läste | Kvartal *a* och märke |
|---|---|---|
| Dell, Moogsoft (10-Q 2023-12-08, #799; 10-K #2770) | goodwill från Moogsoft i de tre månaderna till 2023-11-03; kassaflöde 127 MUSD på nio månader, 126 på året | räkenskapskvartal 3 = `rpo_dell` 2023Q3, som har samma `known_from`. Upp 2023Q3–Q4, ned 2024Q3–Q4 |
| Dell 2023Q4, 2024Q3, 2024Q4 | 126 på året mot 127 på nio månader; inget på nio månader och på året 2025 | inget |
| Dell 2025Q4 (10-K 2026-03-16, #2609) | goodwill förvärvad 61 MUSD (ISG), ingen på nio månader; kassaflöde 84 (#1725); inget namn | räkenskapskvartal 4 = 2025Q4. Etiketten "ej namngivet förvärv" är det som var inlämnat |
| Dell 2025Q3, 2026Q2 | ingen rad för förvärv i kassaflödet | inget |
| Super Micro, Gemini (10-K 2023-08-28, #1457–1459) | slutfört 2023-04-17, 2,5 MUSD varav 0,3 innehållet. 10-Q som lämnades in 2023-05-05, efter slutdagen, nämner inte Gemini | 2023Q2, märket från 2023-08-28 |
| Super Micro 2024Q2 | 0,296 MUSD = det innehållna beloppet | inget |
| Equinix, TIM (10-Q 2025-07-30, #288) | TIM NextGen DC, tre datacenter i Filippinerna, slutfört 2025-06-02, 183 MUSD | 2025Q2, från 2025-07-30. Upp 2025Q2–Q3, ned 2026Q2–Q3 |
| Equinix 2025Q3, 2026Q2, 2026Q3 | 182 på nio månader 2025; inget hittills 2026 (samma mening två gånger, därav samma hash) | inget |
| Equinix 2025Q4 (10-K 2026-02-11, #1467) | 251 MUSD för året mot 182 på nio månader; goodwilltabellen #2682: tillägg 11 i EMEA och 127 i Asien–Stillahavet | 2025Q4. Se R30-3 |

- Ingen av de 39 raderna utan förvärv motsägs av dokumentet: R30 sökte efter rader för förvärv i kassaflödet och efter
  förvärvad goodwill i varje dokument. Där en rad finns är den "—" för perioden eller förklarad (Dell 127/126, Super
  Micro 0,3, Equinix 182).
- **Märket per läsdag.** `acquisition_quarters` ger Moogsoft från 2023-12-08 och inte 2023-12-07, Dells förvärv 2025Q4
  från 2026-03-16 och TIM från 2025-07-30. L2:s huvudursprung 2026Q2 har inget märke. "L2 efter K-inre", *k* = 4, får
  märket vid det avgörande kvartalet 2025Q4 (Dells *a*, upp), vilket är rätt riktning: ett nivåskifte drar Y uppåt mot
  "talar för".
- **HPE.** HPE ingår inte i L2 (`series.ledtid.NET = ("csco", "dell", "smci")`), och `rpo_hpe` läses inte. Att HPE inte
  kodas följer av DA1, punkt 1. Juniper ligger i `rpo_hpe` utan märke, och rapporten säger det.
- **Gränsen.** DA1:s beskrivning av hur mycket tillförd RPO som skulle ändra ett utslag stämmer i R30:s omräkning: 28,7
  och 19,1 mdr USD för L2 vid 2025Q4 och 2026Q1 (35 % och 20 % av Dells RPO), och för L3 1,4–2,0, 1,1 och 1,9 mdr USD.

## 4. Omräkning av L2 per 2026-11-27

Direkt ur `observations.parquet` med pandas: senaste vintage per kvartal med `known_from` ≤ 2026-11-27, L2 = summan av
`rpo_csco`, `rpo_dell` och `rpo_smci`, K-inre = capex över fyra kvartal för Microsoft, Alphabet, Amazon och Meta,
takt = 100 ln(x / x(t − 4)), förändring i takt mot två kvartal tidigare, och F0:s regel (före: *g* = 10, *h* = 5;
efter: *g* = 5, *h* = 10; tecken +1).

| Läsning | R30 | Rapporten |
|---|---|---|
| före, *k* = 2 | talar för: 2026Q2 X +25,9, Y +9,6 vid 2026Q3 | samma |
| före, *k* = 4 | talar för: 2026Q2 X +25,9, Y +9,6 vid 2026Q3 (2025Q4 och 2026Q1 också talar för) | samma |
| efter, *k* = 2 | inget av mönstren (X +0,1 och +2,2) | samma |
| efter, *k* = 4 | talar för: 2025Q2 X +5,9, Y +35,7 vid 2025Q4 | samma, med Dells märke |

Per 2025-11-27 ger samma kod talar för vid 2025Q1 (X +11,0, Y +5,9 vid 2025Q2) i båda före-läsningarna, som rapporten.

## 5. Fynd

### R30-1 (should_fix, DA1): rapporten säger inte till och med vilket kvartal förvärven är kodade

Rapporten säger att Dells, Super Micros och Equinix förvärv "är kodade ur 10-K och 10-Q från 2023", men inte till och
med vilket kvartal (Dell 2026Q2, Super Micro och Equinix 2026Q3). Märket läser bara `curated/acquisitions.csv`, och ett
kvartal efter den sista kodade raden ger inget märke, precis som ett kodat "inget". När Dell lämnar in 2026Q3 omkring
2026-12-09 kommer L2:s första osedda läsning, och ett förvärv i det kvartalet syns då inte, utan att rapporten säger att
kvartalet inte är läst. DA1 gjordes just inför den läsningen. Samma sak gäller Quantas rader i L1 (QA1).
*Rekommendation:* låt förbehållet ange det sista kodade kvartalet per bolag, och märk ursprung och avgörande kvartal
efter det som "förvärv inte kodade", eller koda varje ny inlämning innan läsningen redovisas. Det är text och ingen
regel, så det kräver ingen ny registerpost. Test: `test_r30_1_lt1_report_states_through_which_quarter_the_acquisitions_are_coded`.

### R30-2 (should_fix, DA1, latent): Dells kvartal *a* vid räkenskapsgränserna

`acquisitions.quarter_of(day, "dell")` flyttar dagen en månad bakåt och tar kalenderkvartalet. Dells räkenskapskvartal
slutar på fredagen närmast månadsskiftet, så de första dagarna i maj, augusti, november och februari kan ligga i det
föregående räkenskapskvartalet. Exempel: 2023-11-01 ligger i räkenskapskvartal 3 till 2023-11-03 (2023Q3), men ger
2023Q4. 2023-05-03 och 2024-02-01 hamnar på samma sätt ett kvartal för sent. Docstringen säger att CSV:ns kvartal då ska
vara inlämningens, men `load()` avvisar just en sådan rad ("closed … is not in quarter …"). I dag har ingen Dell-rad en
slutdag, så inget märke är fel. *Rekommendation:* räkna Dells kvartal ur räkenskapskalendern (eller ur rapportdagarna i
EDGAR), eller låt `load()` godta inlämningens kvartal för en slutdag inom en vecka från en gräns. Tester:
`test_r30_2_dell_quarter_of_follows_the_fiscal_calendar_at_its_boundaries`,
`test_r30_2_load_accepts_a_dell_closing_in_the_last_days_of_a_fiscal_quarter`.

### R30-3 (should_fix, DA1): beskrivningen av Equinix 2025Q4 följer inte goodwilltabellen

Raden `eqix-2025Q4-01` och märket ("Equinix, ej namngivet förvärv 2025Q4") är rätt. Men raden, källdokumentet
(`docs/kallor/ledtid.md`) och beslutsloggen säger att skillnaden på cirka 69 MUSD "kan vara ett annat förvärv eller en
senare betalning för TIM". I samma 10-K visar goodwilltabellen tillägg 2025 på 11 MUSD i EMEA bredvid TIM:s 127 MUSD i
Asien–Stillahavet, och förvärvsnoten i 10-Q för nio månader nämner bara TIM:s goodwill. Det talar för ett eget rörelseförvärv i EMEA under
2025Q4 och emot en senare betalning för TIM. Källdokumentet säger att goodwilltabellen lästes i varje dokument. Inget
utslag ändras, eftersom märket ändrar inget utfall. *Rekommendation:* skriv om anteckningen och stycket med goodwilltabellen
som belägg. Test: `test_r30_3_equinix_2025q4_description_follows_the_goodwill_table`.

### R30-4 (note, B18): "byte för byte" i registerposten gäller avsnitt 1–7

B18, punkt 3, säger att KL1:s rapporter per 2025-11-27 och 2026-11-25 "är byte för byte desamma". Det stämmer för
avsnitt 1–7. Avsnitt 8 skiljer i övergångsnotiserna, som beslut 1 ändrar (15 rader per 2026-11-25). Resultatdokumentet
och beslutsloggen skriver det rätt ("avsnitt 1–7"). Posten är låst och ska inte skrivas om. Anmärkningen är till för den
som läser posten.

### R30-5 (note, dokument): två inaktuella påståenden

- `docs/steg2/STATUS.md`, punkt 8, har kvar "Dells förvärv (L2) på samma sätt som Quantas … Rekommendation: ja", som
  DA1 har gjort.
- `docs/kallor/ledtid.md` säger att DA1:s råkopior och meningar ligger i spårets `data/raw` och inte i
  huvudutcheckningens. Integrationen flyttade dem till basens `data/raw` (filerna där är skapade 14:16:44, efter DA1:s
  sista commit, och kalibreringsraden för integrationen säger det). Det är bra för självkontrollen, men meningen
  stämmer inte längre.

### R30-6 (note, process och licens)

- DA1:s commit `b4eabec` (kod och data) har fixturer med registrets hash från `3edc854`. Spåret förde in fixturerna först
  i `3dd2f1b`. HEAD stämmer.
- Anteckningen till `eqix-2025Q4-01` och källdokumentet citerar en kort fras ur 10-K ("including the TIM Acquisition").
  Det är fyra ord och inget faktum som saknas annars, men CLAUDE.md säger att bara extraherade siffror publiceras och
  aldrig själva texten. Det kan skrivas med egna ord.

## 6. Vad R30 inte prövade

- Quantas 55 rader (QA1) och Ciscos förvärv utom Splunk. DA1 kodar dem inte, och R29 granskade QA1.
- Om Dells och Equinix ej namngivna förvärv har tillfört RPO. Bolagen anger inget belopp. Gränsberäkningen visar bara att
  det skulle behöva vara mångdubbelt mer än köpeskillingen eller kassaflödet för att ändra ett utslag.
- Hela testsviten. R30 körde de riktade testerna för B18, DA1, PV1, X26, QA1 och LT1 (112 passerade) och sina egna
  (21 passerade, 4 strikta xfail).
