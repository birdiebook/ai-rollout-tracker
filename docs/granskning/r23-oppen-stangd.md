# R23 – granskning av öppna mot stängda modeller och Kinas gap (Q2)

Granskningsspår R23, körning 14, 2026-11-25, gren `auto14k/r23-oppen-stangd` (bas `auto14k/q2-oppen-stangd`, `9902313`).
Granskat: de åtta katalogserierna i G1 (`g1_open_*`, `g1_china_*`, Arena och ECI), byggda av Q2 i
`src/ai_tracker/series/open_gap.py`, `src/ai_tracker/sources/arena_meta.py` och `src/ai_tracker/sources/model_origin.py`,
med registerposten 2026-11-25 i `docs/mattregister.md` och dokumentationen `docs/kallor/g1_oppen_stangd.md`.

Underlag: Arena-datasetets `text/full` vid HEAD `62968a5` (66 MB, med `license`, `organization` och `vote_count`), de
270 texttavlorna ur `arena.subset_boards("text")`, de 129 `leaderboard_table_*.csv` och Space-picklarna i den delade
rå-cachen, Space-klonens git-logg, `text_style_control` (204 tavlor) och Epochs `benchmark_data.zip` och `ai_models.zip`
från 2026-11-25. Q2:s hämtade tabell (330 rader) lästes ur `/home/user/wt/q2-oppen-stangd/data`. Inget nät användes
utöver cachen.

**Metod.** Ett eget skript räknade om alla åtta serierna ur rådata, utan `open_gap.py` och `arena_meta.py`: egen
klassning i registrets ordning, egna namnklasser ur de kurerade tabellerna och de mekaniska reglerna, egen
eftersläpning inom en tavla och egen ECI-beräkning. Bara de kurerade tabellerna i `model_origin.py` användes som data.
Elva månader lästes dessutom för hand direkt ur datasetets rader, Space-picklarna och `eci_scores.csv`.

**Ingen analys av förlopp gjordes.** Känslighetsräkningarna i punkt 3 och 7 visar bara hur mycket ett val betyder.
De är inte resultat.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Förregistrering och vad som setts | **OK.** Registret före koden före värdena. Inga värden i de två första commitarna. Registerposten är oförändrad efteråt |
| 2. Klassning | **OK för Arena.** Etiketterna är samtida: 0 avvikelser i 42 712 jämförbara par. **Anmärkning för ECI:** Kimi K3.1 Pro räknas som öppen i 2026-10, fast vikterna kom 2026-11-04 (R23-3) |
| 3. Eftersläpning inom en tavla | **OK.** Betyget läses bara i b(m). Ersättningsregeln är implementerad som registrerad, men enligt en känslighetsräkning kortar den eftersläpningen med 2–3 månader i 8 månader (2025-08 – 2026-03). Storleken står inte i dokumentationen (R23-4) |
| 4. ECI som registrerat | **OK.** Alla 152 rader stämmer. Datum och klassning är dagens, som registret säger |
| 5. Handkontroller | 11 månader i båda måtten och båda källorna. Alla stämmer med serierna, utom gapet 2026-09 (R23-1) |
| 6. Datering och versioner | **Fel.** En tavla som publiceras sista dagen i månaden och beläggs nästa dag kommer aldrig in i den månaden (R23-1). Samma fel finns sedan tidigare i `sources/vintages.py` och ger fel värden i G1:s kärnserie `g1_arena_text_top` (R23-2) |
| 7. Förbehåll och licenser | **OK med anmärkningar.** Golvet 0 binder aldrig. Stilkontroll ger samma nivåer men andra månadsvärden. Licensklasserna och `publish=True` följer prejudikatet för `g1_arena_*` |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Den oberoende omräkningen ger exakt samma värden, `known_from` och `source`
i alla 330 rader, utom fyra. De fyra är gapet för öppna och för Kina i 2026-04 och 2026-09, där sista tavlan i
månaden aldrig läses (R23-1). I 2026-09 blir gapet 27,06 poäng i stället för 42,58. Eftersläpningen påverkas inte i
dagens data. Inget läckage hittades i Arena-klassningen. R23-1 ska rättas innan serierna slås ihop med basen. R23-2
gäller kod som fanns före Q2 och berör en kärnserie före den första ögonblicksbilden 2026-11-30. Övriga punkter gäller
dokumentation och ett regelval för ECI. Ingen av serierna bör bli kärnserie innan R23-1, R23-3 och R23-4 är åtgärdade.

## 1. Förregistrering – OK

Ordningen enligt git (alla 2026-11-25, UTC):

| Tid | Commit | Innehåll |
|---|---|---|
| 09:14:58 | `13d6d9b` | Bara `docs/mattregister.md`: nycklar, klassningsordning, namnbyten, censurering, datering, licens |
| 09:27:23 | `bc39cc5` | Kod och tester (syntetiska), kurerade tabeller. Inga ratingar eller ECI-värden i diffen (sökt efter tal av typen 1 234,5 och 123,45) |
| 09:38:36 | `9902313` | Värdena, dokumentationen, beslutsloggen och en daterad rättelse av en faktauppgift i registret |

- `git diff 13d6d9b HEAD -- docs/mattregister.md` tar inte bort någon rad. Rättelsen är tillagd sist och ändrar inga
  regler. Den stämmer i sak: 4 modeller går från "Proprietary" till en öppen licens, `minimax-m2.5` byter mellan två
  öppna licenser, och `gpt-5.4` och `gpt-5.4-high` har tomt fält i 7 tavlor (kontrollerat i datasetet).
- Den enda kodändringen efter värdena (`9902313`) lägger till diagnostikfältet `reach_fallback`. Ingen regel ändras.
- Vad som lästes före posten: skript i den delade arbetskatalogen från före 09:14 räknar bara täckning per
  klassningssteg. Det stämmer med listan i posten. Begränsning: arbetskatalogen delas av flera spår, och transkriptet
  finns inte här. Git visar att inga värden committades före registret, inte att inga räknades lokalt.

## 2. Klassning – OK för Arena, anmärkning för ECI

**Arena: etiketterna är samtida.** Registret läser vikter och organisation ur Arenas egna rader per tavla. Risken är
att datasetets bulkuppladdning 2026-04-02 bär dagens etikett även för äldre tavlor. Det prövades mot källor från
samma tid:

- 42 377 par (tavla, namn) 2024-01-09 – 2025-08-04, datasetets etikett mot senaste `leaderboard_table_*.csv` med datum
  ≤ tavlans: 0 par där datasetet säger öppen och den samtida tabellen stängd. De 173 avvikelserna är alla
  `claude-3-5-haiku-20241022`, som Space-tabellen stavar "Propretary" (R23-8).
- 335 par i 2023 mot de tio första tabellerna (bara visningsnamn), matchade på normaliserat namn: 0 avvikelser.
- De fyra modeller som byter från stängd till öppen (`minimax-m2.7`, `minimax-m3`, Mistral Large 4, Inkling 2 Small)
  byter i HEAD först vid släppet. Arena skriver alltså inte om äldre tavlors etiketter.
- Två modeller bytte i Space-tabellerna 2024: `mistral-large-2407` (Proprietary 07-31 – 08-01, sedan Mistral Research)
  och `deepseek-v2-api-0628` (Proprietary 07-16 – 07-31, sedan DeepSeek). Klassningen följer tabellen per datum.
- Steg 3 (senare uppgift, vikter bara om stängd) gäller 60 par och 14 namn: GPT-4, GPT-3.5 och Claude i Space-tavlorna
  2023, `pplx-*`, `mai-1-preview`. Alla är stängda modeller. Steg 4 (kurerat) gäller 14 par och 4 namn, alla med
  referens.
- Kan inte prövas: bulktavlorna 2025-08-07 – 2026-03-31 har ingen samtida andra källa. De öppna topparna i de månaderna
  (`glm-4.6`, `glm-4.7`, `kimi-k2.5-thinking`, `qwen3.5-397b-a17b`) hade öppna vikter från släppet enligt Epoch.
- `llama-4-maverick-03-26-experimental` (plats 2–10 i 2025-04 – 2025-08) lämnas utanför. Räknas den som stängd, som
  Epoch gör med osläppta modeller, ändras inget värde i 2025-04 – 2025-12 (kontrollerat i båda versionerna).

**Land.** 65 av referenserna i `ORG_COUNTRY` citerar Epochs fält. 63 stämmer mot `all_ai_models.csv`. Två citerar
organisationens namn fel ("NousResearch" ska vara "Nous Research", "NVIDIA" ska vara "Nvidia"). Landet är rätt i båda
(R23-9).

**ECI: dagens klassning (R23-3).** Registret tar `Accessibility group` som den är i dag och daterar historiken som
`backfill`. Bland Epochs öppna modeller har en enda en dokumenterad viktsläpp efter sitt `date`: Kimi K3.1 Pro
(`date` 2026-10-23, Epochs anteckning: "Weights released on Hugging Face 2026-11-04; API since 2026-10-23"). Den är den
öppna toppen i 2026-10. Utan den är toppen Kimi K3 (158,61), eftersläpningen 7 månader i stället för 6 och gapet
10,60 i stället för 8,01. Arena har inte felet: Kimi K3.1 Pro finns i tavlorna först 2026-11-09. Dokumentet säger
allmänt att en modell räknas som öppen från sitt `date`, men handkontrollen för 2026-10 nämner inte att vikterna kom
efter månaden. MiniMax-M3 och Mistral Large 4 är öppna i ECI före Arenas etikett för öppna vikter, men ingen av dem är
topp, så inget värde ändras.

## 3. Eftersläpning inom en tavla – OK, anmärkning om ersättningsregeln

- Koden läser betyg bara i b(m). b(s) används bara för att välja vilken modell som var fronten. Gapet räknas i b(m).
  Ratingar jämförs aldrig mellan tavlor.
- Namnklasserna stämmer: 27 kurerade byten, 20 tidiga visningsnamn 2026-10-15, och vid bytet 2026-10-20 26 samma namn,
  346 samma normaliserade namn, 16 samma ord och 15 samma licens och röstantal, 13 kurerade, och `Beam 1.0 501B A23B`
  över. Inga två namn i samma klass finns i samma tavla.
- Namnbyten som avgör s*: `gpt-4` → `gpt-4-0314` (18 fall), `gpt-4-turbo` → `gpt-4-1106-preview` (14),
  `chatgpt-4o-latest` → `-20240808` (8) och visningsnamnet "Claude Opus 4.6" (4). `claude-sonnet-5-thinking` → `-high`
  (4 385 → 9 008 röster på 8 dagar, i snitt cirka 450 per dag de följande tio dagarna) är rimligt som fortsättning.
  `claude-fable-5` → `-high` (30 057 → 36 462 på 12 dagar, cirka 530 per dag mot 190–290 före och efter) är inte
  avgjort: det kan vara ett namnbyte eller två varianter som slagits ihop. `kimi-k3` → `kimi-k3-max` (3 619 → 3 569, licens till "Kimi K3 license") är
  samma modell med släppta vikter. Steg 1 läser etiketten per tavla, så Kimi K3 är stängd före 2026-07-26. Ingen av de
  tre avgör något värde.
- **Ersättningsregeln (R23-4).** Regeln är implementerad som registrerad: saknas fronten i b(m), används nästa stängda
  modell i b(s). Den används mycket. I 2025-08 saknas de åtta högsta stängda modellerna i februaris tavla, och den
  nionde (`gemini-2.0-flash-001`) läses. s* = 2025-03 i 2025-06 – 2025-08 vilar på `chatgpt-4o-latest-20250326`, som
  ersätter `gemini-2.5-pro-exp-03-25`. I 2025-08 når den `glm-4.5` med 0,30 poäng (1 429,38 mot 1 429,08).
- **Känslighet** (ett antagande, inte ett värde): ge den borttagna toppen samma försprång före ersättaren som den hade
  i b(s). Då flyttas s* till 2025-03 i fler månader, och eftersläpningen blir 2–3 månader längre:

| Version | Mått | Månader | Regeln | Med försprånget |
|---|---|---|---|---|
| första | båda | 2025-08 | 3 | 5 |
| senaste | Kina | 2025-09 | 3 | 6 |
| senaste | båda | 2025-10 – 2026-01 | 4, 5, 6, 7 | 7, 8, 9, 10 |
| senaste | öppna | 2026-02 – 2026-03 | 8, 9 | 11, 12 |

  Dokumentet säger att regeln kan korta eftersläpningen. Det säger inte hur mycket, och det säger att s* själv bara
  påverkas i 2025-06 – 2025-08 och de första versionerna. Det stämmer för s*, men regeln påverkar också de senaste
  versionerna 2025-09 – 2026-03 genom månaderna före s*.

## 4. ECI som registrerat – OK

- Alla 152 ECI-rader stämmer med den egna omräkningen ur `eci_scores.csv` och `all_ai_models.csv`. Täckningen stämmer:
  254 modeller med vikter (4 Qwen-modeller utan), 257 med land (`open_llama_7b` utan).
- Alla rader har `source` = `backfill` och `known_from` = månadsslut + 7 dagar, som registrerat.
- Kinas tidiga värden (R23-6). s0 för Kina är första månaden med en icke-kinesisk modell, öppen eller stängd. Det är
  LLaMA-65B (2023-02-24), en månad före GPT-4. Därför censureras inte 2023-09 – 2024-04, fast filen saknar modeller
  före 2023-02. Värdena (6–13 månader) är undre gränser, som dokumentet säger. 2024-05 (14 månader) är troligen rätt,
  eftersom F = 120,82 ligger nära GPT-4 (121,61), men det går inte att pröva i filen. Måttet för öppna censureras i
  samma månader, eftersom dess s0 är GPT-4:s månad.
- Datum i Epochs filer (R23-7). `eci_scores.csv` daterar "GPT-4 Turbo (Nov 2023)" 2024-01-25, men `all_ai_models.csv`
  har 2023-11-06. Med 2023-11-06 blir ECI-eftersläpningen för öppna 7 i 2024-06 (i dag 5) och för Kina 7, 8 och 9 i
  2024-06 – 2024-08 (i dag 5, 6 och 7). Vilket datum som är rätt är inte verifierat. 13 modeller skiljer mer än 14
  dagar. De flesta är tillkännagivande mot släpp (o3: 2024-12-20 mot 2025-04-16), och då är `date` det rimliga.

## 5. Handkontroller – 11 månader

Lästa direkt ur datasetets rader, Space-picklarna och `eci_scores.csv`, med etikett ur tavlans egen rad (annars
Space-tabellen). Andra månader än Q2:s utom ECI 2026-10.

| Månad | Mått | Tavla eller fil | F (följande) | L (ledande) | Ledande front som först når F | Serien |
|---|---|---|---|---|---|---|
| 2024-07 | Arena, öppna | Space 2024-07-31 | `llama-3.1-405b-instruct` 1 261,72 | `gpt-4o-2024-05-13` 1 286,05 | 2024-04: `gpt-4-turbo-2024-04-09` 1 256,87 (nej). 2024-05: `gpt-4o-2024-05-13` 1 286,05 | 2 mån, gap 24,33 ✓ |
| 2024-05 | Arena, Kina | Space 2024-05-27 | `yi-large-preview` (01 AI) 1 232,52 | `gpt-4o-2024-05-13` 1 281,63 | 2023-10: `gpt-4` = `gpt-4-0314` 1 188,28 (nej). 2023-11: `gpt-4-turbo` = `gpt-4-1106-preview` 1 249,84 | 6 mån, gap 49,11 ✓ |
| 2025-08 | Arena, öppna (senaste) | Space 2025-08-29 | `glm-4.5` (MIT) 1 429,08 | `gemini-2.5-pro` 1 466,24 | 2025-02: plats 1–8 saknas, plats 9 `gemini-2.0-flash-001` 1 358,15 (nej). 2025-03: toppen saknas, `chatgpt-4o-latest-20250326` 1 429,38 | 5 mån, gap 37,16 ✓ |
| 2026-03 | Arena, öppna (senaste) | dataset 2026-03-31 (bulk) | `kimi-k2.5-thinking` 1 449,46 | `claude-opus-4-6-thinking` 1 500,55 | 2025-05: plats 1–3 saknas, `o3-2025-04-16` 1 408,83 (nej). 2025-06: `gemini-2.5-pro` 1 460,40 | 9 mån, gap 51,09 ✓ |
| 2026-03 | Arena, Kina (senaste) | dataset 2026-03-31 (bulk) | `qwen3.5-max-preview` (stängd) 1 472,39 | som ovan | 2025-10: `gemini-2.5-pro` 1 460,40 (nej). 2025-11: `gemini-3-pro` 1 479,51 | 4 mån, gap 28,16 ✓ |
| 2026-07 | Arena, Kina | dataset 2026-07-30 | `qwen3.7-max-preview` 1 475,12 | `claude-opus-5-max` 1 511,60 | 2025-10: `gemini-2.5-pro` 1 457,51 (nej). 2025-11: `gemini-3-pro` 1 479,46 | 8 mån, gap 36,48 ✓ |
| 2026-09 | Arena, öppna (Q2:s tavla) | dataset 2026-09-25 | `mimo-v2.6-pro` 1 490,73 | `claude-opus-5.5-high` 1 517,79 | 2026-01: `gemini-3-pro` 1 479,40 (nej). 2026-02: `claude-opus-4-6` 1 497,79 | 7 mån, gap 27,06 ✓ mot koden |
| 2026-09 | Arena, öppna (rätt tavla) | dataset 2026-09-30, belagd 2026-10-01 | `mimo-v2.6-pro` 1 490,51 | `gemini-4-argon-high` 1 533,09 | 2026-02: `claude-opus-4-6` 1 497,67 | 7 mån, gap **42,58** ✗ (R23-1) |
| 2024-06 | ECI, öppna | `eci_scores.csv` | Qwen2-72B 122,35 | Claude 3.5 Sonnet 130,00 | GPT-4 Turbo (Nov 2023), `date` 2024-01-25 (R23-7) | 5 mån, gap 7,65 ✓ |
| 2026-10 | ECI, öppna | `eci_scores.csv` | Kimi K3.1 Pro 161,20 (vikter 2026-11-04) | GPT-6 Astra 169,21 | GPT-5.5 Pro, 2026-04-23 | 6 mån, gap 8,01 ✓ mot registret (R23-3) |
| 2024-05 | ECI, Kina | `eci_scores.csv` | DeepSeek-V2 120,82 | GPT-4o (May 2024) 128,13 | GPT-4 (Mar 2023), 2023-03-14; s0 = 2023-02 (LLaMA-65B) | 14 mån, gap 7,31 ✓ |
| 2026-03 | ECI, Kina | `eci_scores.csv` | Qwen 3.6 Plus (stängd) 148,87 | GPT-5.4 Pro 160,31 | GPT-5, 2025-08-07 | 7 mån, gap 11,44 ✓ |

Tavlan per månad följer regeln, utom i 2026-09 (och 2026-04, inte i tabellen), där regeln säger 2026-09-30.

## 6. Datering och versioner – fel

**Det som håller.** Den oberoende omräkningen av alla versioner (brytdag = månadsslut för första versionen, annars
beläggsdagen) ger samma rader, samma `known_from` och samma `source` som Q2 i alla 178 Arena-rader, när den räknar på
samma sätt som koden. `backfill` sätts när b(m) eller b(s*) bara finns i bulkuppladdningen, som registrerat. Därför är
eftersläpningen `backfill` från 2026-04: s* ligger i 2025-11 eller 2026-02, och de tavlorna finns bara i bulken. Inga
dubbletter, inget `known_from` före månadsslut + 1 dag.

**R23-1 (must_fix).** `open_gap.arena_build` lägger beläggsdagarna i en mängd med basdagen månadsslut + 1 och räknar
basdagen med brytdag = månadsslut. En tavla som publiceras sista dagen och beläggs nästa dag får då beläggsdagen lika
med basdagen. Den räknas aldrig: inte i första versionen (belagd efter brytdagen) och inte som egen version (samma dag
som basdagen). Registret säger: "En tavla som publicerades ≤ månadsslut men beläggs senare ger en ny version på
beläggets dag om värdet ändras." Det gäller två månader i dagens data:

| Månad | Tavla som saknas | Serie | Q2 | Rätt |
|---|---|---|---|---|
| 2026-04 | 2026-04-30, belagd 2026-05-01 | `g1_open_gap_arena` | 33,82 | 32,91 |
| 2026-04 | samma | `g1_china_gap_arena` | 27,49 | 28,57 |
| 2026-09 | 2026-09-30, belagd 2026-10-01 | `g1_open_gap_arena` | 27,06 | 42,58 |
| 2026-09 | samma | `g1_china_gap_arena` | 27,06 | 42,58 |

Eftersläpningen är densamma (5 och 7 månader). Den rätta raden har `known_from` 2026-05-01 respektive 2026-10-01.
Värdet för månaden revideras aldrig senare, eftersom tavlan bara räknas från nästa månad.

**R23-2 (must_fix, fanns före Q2).** `sources/vintages.monthly` har samma konstruktion, och Q2 följer den som
registrerat ("Versioner som i `sources/vintages.py`"). Dess egen docstring säger att ett tillstånd som beläggs senare ger
en version på beläggets dag. De lagrade värdena i bastabellen:

| Serie | Månad | Lagrat | Rätt (sista tavlan) |
|---|---|---|---|
| `g1_arena_text_top` (kärnserie G1) | 2026-04 | 1 500,21 | 1 500,56 |
| `g1_arena_text_top` | 2026-09 | 1 517,79 | 1 533,09 |
| `g1_arena_text_sc_top` | 2026-04 | 1 502,93 | 1 504,00 |
| `g1_arena_text_sc_top` | 2026-09 | 1 508,55 | 1 524,84 |
| `g1_arena_webdev_top` | 2026-07 | 1 711,88 | 1 703,69 |
| `g1_arena_webdev_top` | 2026-09 | 1 820,31 | 1 817,84 |

Inte kontrollerat: `g1_arena_text_top_gap_ref` och de andra användarna av `vintages.monthly` (`aws_gpu`, `swebench`).
Rättningen ligger utanför Q2 och bör göras före ögonblicksbilden 2026-11-30, eftersom `g1_arena_text_top` är
kärnserie.

**ECI.** Alla 152 rader är `backfill` med `known_from` = månadsslut + 7. Det är registrerat och ärligt märkt.

## 7. Förbehåll och licenser – OK med anmärkningar

- **Golvet 0** binder aldrig i dagens data: inget värde är 0 och inget gap är negativt. Beskrivningen av golvet i
  dokumentet stämmer med koden.
- **Hopp.** Eftersläpningen hoppar som beskrivet (6, 7, …, 12 med tavlan 2025-08-29, 4–9 efter bulken).
- **Små kinesiska urval och samma modeller i båda måtten** stämmer: från 2024-12 är den öppna toppen kinesisk i båda
  källorna, och måtten skiljer sig bara när en stängd kinesisk modell är topp (Arena 2026-03: 4 mot 9 månader).
- **Stilkontroll (R23-5).** `text_style_control` (från 2024-08, censurerad till 2024-12) ger samma spann, 2–9 månader,
  men andra månadsvärden. Skillnaden är upp till 5 månader: öppna 2026-01 är 2 med stilkontroll och 7 utan, 2025-10 –
  2025-12 är 7–9 mot 4–6, och 2026-07 – 2026-08 är 5–6 mot 8–9. Nivån är robust mot vyn. Förändringen från månad till
  månad är det inte.
- **Licens.** Arena-serierna får `okänd` genom källregeln för Space-filerna, samma som `g1_arena_text_top`. ECI-serierna
  får `ja` (CC BY 4.0). `catalog.validate()` är tom. `publish=True` följer prejudikatet för `g1_arena_*` (klassen är
  oberoende av `publish`). Tabellerna i `docs/datakallor/licensniva.md` blir inaktuella efter sammanslagningen
  (LMArena 3 → 7 serier, Epoch AI 13 → 17 enligt `python -m ai_tracker.licenses report --markdown`).
- **Space-tabellerna** dateras med datumet i filnamnet och läses vid HEAD (R23-10). 58 senare ändringar ligger inom 8
  dagar från filens datum. Två filer lades till 12–13 dagar sent (20230619, som inte används eftersom den saknar `key`, och 20240329). Ingen etikett skiljer sig från
  datasetets, så inget värde påverkas.
- **"Propretary" (R23-8).** Space-tabellerna stavar `claude-3-5-haiku-20241022` fel i 55 rader. Regeln läser varje
  annat ifyllt värde än "Proprietary" som öppna vikter. I dag vinner datasetets rad i alla 183 tavlor (179 egna rader,
  4 tidigare datasetrader), så inget värde ändras.

## Rättningar (för ett rättningsspår)

| # | Var | Rättning |
|---|---|---|
| R23-1 | `series/open_gap.py` `arena_build` | Basdagens brytdag ska vara basdagen själv (belägg ≤ månadsslut + 1), eller så ska en tavla belagd på basdagen ge en egen version samma dag som ersätter den första. Hämta om de fyra serierna. Det strikta xfail-testet `test_last_day_board_documented_next_day_enters_its_month` slår om när felet är rättat |
| R23-2 | `sources/vintages.py` `monthly` (fanns före Q2) | Samma rättning. Hämta om `g1_arena_*` och kontrollera `aws_gpu` och `swebench`. Före 2026-11-30, eftersom `g1_arena_text_top` är kärnserie. Testet `test_vintages_monthly_keeps_a_last_day_state_documented_next_day` slår om |
| R23-3 | `docs/mattregister.md` (daterad post) och `open_gap.eci_frame` | En ECI-modell räknas som öppen från det senare av `date` och en dokumenterad viktsläpp (Epochs `Accessibility notes`, eller en kurerad rad med referens). Ändrar 2026-10 för öppna (6 → 7 månader, gap 8,01 → 10,60). Testet `test_eci_model_with_weights_after_month_end_is_not_open_that_month` slår om. Alternativt, om regeln behålls: skriv i dokumentet att 2026-10 vilar på en modell vars vikter kom 2026-11-04 |
| R23-4 | `docs/kallor/g1_oppen_stangd.md` punkt 7.2 | Redovisa ersättningsregelns storlek: tabellen i punkt 3 här, att februaris ersättare är plats 9, och att s* i 2025-06 – 2025-08 vilar på 0,30 poäng. Säg att de senaste versionerna 2025-09 – 2026-03 också påverkas |
| R23-5 | dokumentet, avsnitt 8 | Lägg till att stilkontroll ger samma nivå men andra månadsvärden (upp till 5 månader). Takten i Arena-serierna är därför inte robust mot vyn |
| R23-6 | dokumentet, eller en daterad registerpost | Märk ECI-Kinas värden 2023-09 – 2024-04 som undre gränser i serienoten, eller censurera dem med en daterad registerpost |
| R23-7 | dokumentet | Nämn att Epochs två filer daterar GPT-4 Turbo (Nov 2023) olika, och vad det betyder för 2024-06 – 2024-08 |
| R23-8 | `arena_meta.weights_of` (daterad registerpost) | Läs kända felstavningar av "Proprietary" som stängd. Ingen effekt i dag |
| R23-9 | `model_origin.ORG_COUNTRY` | Rätta citaten "NousResearch" och "NVIDIA" till Epochs "Nous Research" och "Nvidia". Lägg gärna till en kontroll mot `all_ai_models.csv` som hoppas över utan filen |
| R23-10 | ingen | Space-tabellernas datering: risken är liten och inget värde påverkas. Ingen åtgärd |

Kärnserie: ingen av serierna bör föreslås före R23-1, R23-3 och R23-4. Om ägaren vill pröva
`g1_open_lag_months_arena` som kärnserie ska registerposten också ta ställning till R23-5 (vy) och till
ersättningsregeln.

## Tester

`tests/test_r23_oppen_stangd.py` (fixturer, inget nät):
- en tavla sista dagen, belagd nästa dag, ska ingå i månaden (strikt xfail, R23-1)
- samma i `vintages.monthly` (strikt xfail, R23-2)
- belägg två dagar efter månadsslut ger en ny version, både i `vintages.monthly` och i `arena_build` (passerar)
- en ECI-modell vars vikter släpps efter månadsslut ska inte vara öppen den månaden (strikt xfail, R23-3)
- etiketten per tavla håller en modell stängd tills Arena märker vikterna som öppna (passerar)
- fronten väljs i b(s) och läses i b(m) (passerar)
- eftersläpningen är `backfill` när b(s*) bara finns i bulken, gapet förblir `release` (passerar)
- en sen tavla för en tidigare månad ändrar värdet först från sitt belägg (passerar)
- ECI-Kinas s0 är första icke-kinesiska modellen oavsett vikter (passerar, beskriver R23-6)
- ECI-serierna har `lag_days` 7 och Arena-serierna 1 (passerar)

`python -m pytest -q tests/test_r23_oppen_stangd.py tests/test_q2_open_gap.py`: 28 passerade, 3 xfail.
