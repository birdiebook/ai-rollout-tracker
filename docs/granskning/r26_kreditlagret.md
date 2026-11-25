# R26 – granskning av KL1 Kreditlagret (följd fråga)

Granskningsspår R26, 2026-11-25, gren `auto15/r26-kreditlagret` (bas `auto15/kl1-kreditlagret`, `a15b0f5`). Granskat:
registerposten "2026-11-25 – KL1" och tillägget, `curated/kreditlagret.csv` (400 rader), `sources/kreditlagret.py`,
`sources/kreditlagret_coding.py`, `kreditlagret_check.py`, `series/kreditlagret.py`, `followed/kreditlagret.py`,
`tests/test_kreditlagret.py`, `docs/kallor/kreditlagret.md`, `docs/resultat/kreditlagret.md` och `git log -p` för de fem
commits som spåret gjorde. Full granskning: frågan är en följd fråga som Johannes agerar på.

Underlag:
- De 26 EDGAR-dokument som raderna kommer ur, och Anthropics S-1/A 2026-11-17 och 424B4: 28 dokument. Hämtade på nytt
  från www.sec.gov med egen kod, inte KL1:s cache. Den generiska klientidentiteten, en begäran i taget, 0,3 s mellan
  dokumenten. Inget anrop gav 403 eller 429.
- EDGAR:s submissions-API för Anthropic, CoreWeave, Meta, Oracle och SpaceX.
- EDGAR:s företagssökning (browse-edgar) på nio namn: openai, "open ai", xai, x.ai, spacex, "space exploration tech",
  mistral, "safe superintelligence" och "thinking machines".
- SpaceX 10-Q för 2026Q3 och Microsofts 10-K för räkenskapsåret till 2026-06-30 (`0001193125-26-323660`), hämtade på
  nytt. Microsofts companyfacts ur den delade cachen (`data/raw/sec`, 2026-11-25), inte hämtad på nytt.

Inga värden, ingen produktionskod och inget dokument från KL1 är ändrat. R26 räknade om de 53 serierna med KL1:s kod in
i den här worktreens `data/`. De 1 870 raderna är identiska med KL1:s. Testerna finns i
`tests/test_r26_kreditlagret.py`: fastlåsta rader och registertext, egenskaper som håller och nio fynd som
`xfail(strict=True)`.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Ordning och förregistrering | **OK, med anmärkning.** Posten committades före första hämtningen, tillägget före första kodade raden. Redovisningen av tittarna är ärlig. Men läsningarna per 2026-11-25 görs på kvartal som var sedda (R26-7), och regeln läser bara uppgång i pris och beroende (R26-8) |
| 2. Extraktionen | **Fel i 6 rader.** 400 av 400 hashar, datum och dokument stämmer. 272 av 278 handlästa rader är rätt. Fem rader är daterade en vecka för tidigt (R26-1) och ett belopp är fel (R26-2). SpaceX/xAI saknas i labbdelen (R26-3). Okodade kandidater är inte listade (R26-4) |
| 3. Härledda mått | **OK.** En oberoende omräkning ger samma värde och `known_from` i alla versioner av 30 serier. Lagren finns först när alla medlemmar har lämnat in. Inget är framtidsdaterat. Två mått behöver förbehåll i texten (R26-5, R26-6) |
| 4. Rapporten | **OK, med anmärkning.** Kommandot ger exakt rapporterna i `docs/resultat`. Läsregeln följer registret. Inga värden når publika utdata. Texten i avsnitt 5 är missvisande på tre ställen (R26-9) |
| 5. Licens, katalog, tester | **OK.** 53 serier, alla klass `ja`, `publish=False`, `catalog.validate` utan fel. Hela sviten: se avsnitt 5 |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** De härledda måtten, dateringen av dem och läsregeln håller. Rapporten kan läsas
som den är för avsnitt 1–4, med förbehållen nedan. Extraktionen (avsnitt 5 i rapporten) ska inte användas för beslut
förrän R26-1 och R26-2 är rättade. Båda är små och lokala: inget mått, ingen läsning och ingen publik utdata bygger på
de raderna. Registrets villkor för granskningen (minst 30 % av raderna och ett helt dokument per bolag) är uppfyllt.

## 1. Ordning och förregistrering

**Tider (git och filtider, UTC 2026-11-25).**

| Händelse | Tid |
|---|---|
| Registerposten, `4bcb077` | 21:06:54 |
| Första mappen för KL1:s råkopior skapas | 21:07:06 |
| Första SEC-anropet (företagssökningen) | 21:07:40 |
| Korpusen hämtad (OpenAI, Anthropic, CoreWeave, Meta, Oracle) | 21:09:07–21:10:09 |
| Tillägget, `60af26f` | 21:12:29 |
| Första citatet sparas (första kodade raden) | 21:14:32 |
| Extraktionen, `cdf7811` | 21:24:47 |
| De härledda serierna i spårets tabell | 21:31 |
| Dokumenten, `a15b0f5` | 21:42:41 |

Posten och tillägget är oförändrade sedan låsningen (SHA-256 fastlåst i testet). Ordningen håller.

**Vad som var sett.** Avsnitt (e) i posten stämmer med siffrorna. Inre lagrets (capex − OCF) / capex är −10,0 %, alltså
capex/OCF 91 %. Nettoemissionen är 43,8 % av capex, alltså 44 %. Det är samma fönster som rapporten per 2026-11-25.
Posten säger att tittarna inte räknas som utfall. Men läsningarna per 2026-11-25 räknas på just de kvartalen, och
resultatdokumentet säger inte det (R26-7). Den första läsningen på data som ingen hade sett kommer med Oracles inlämning
omkring 2026-12-11.

**Tillägget** skrevs efter att agenten sett CoreWeaves skuldtabell för 2026Q3 med värden. Det står i tillägget. Punkt 4
tar med konvertibler i den vägda räntan. Det valet sänker serien, eftersom konvertiblerna har 2–3 % (R26-5).

**Symmetri.** Koden följer registret vid varje gräns (testet `test_reading_follows_the_register_at_the_limits`). Både
"talar för" och "talar emot" kan nås. Två saker syns inte i texten:
- Regeln läser bara en riktning. A kräver att pris eller beroende **stiger**. Ett fall i pris och beroende följt av
  högre capex-takt blir "inget av mönstren". Registret och rapporten säger "åt båda hållen".
- A är nästan alltid uppfyllt. För Oracle gällde A i 28 av 35 kvartal sedan 2018Q1 (genom (capex − OCF) / capex 25
  gånger, nettoemission 14, leasing 6 och ränta 4). För yttre lagret i 4 av 4. Utslaget "talar för" eller "talar emot
  (1)" avgörs då i praktiken av capex-takten ensam.

Det är inte en dold riktning mot "talar för". Men texten "pris eller beroende steg först" säger mer än regeln prövar
(R26-8).

Liten avvikelse: posten säger företagssökning "(JSON)", koden använder Atom-flödet. Det påverkar inget.

## 2. Extraktionen

**Dokument och datum.** Alla 28 dokument är byte för byte lika KL1:s cache (SHA-256). För alla 400 rader stämmer
citatets SHA-256 på platsen, och `filed`, `accepted` och formulär stämmer med submissions-API:t. Alla 102 rader från
Anthropic står i det tidigaste av de fem dokumenten som har samma rad.

**Handläsning.** R26 läste varje rad mot källtexten:
- Anthropic: alla 102 rader (hela 424B4-kedjan).
- Meta: alla 15 rader, och tabellhuvudena i 10-Q 2026Q3.
- CoreWeave: alla 58 rader ur 8-K, och tre hela skuldtabeller (10-Q 2025Q1 i tusental, 10-K 2025 och 10-Q 2026Q3), 103
  rader.

Det är 278 rader, 70 %. De övriga 122 tabellraderna prövades med en egen tolkning av alla sju tabellerna: 0 avvikelser i
225 rader (rätt balansdag, tusental eller miljoner, sektionerna och nollrader). Ett slumpat stickprov på 120 rader (30 %,
frö 20261126) gav 0 fel. Felen nedan hittades bara genom att läsa hela dokument.

**Resultat: 272 av 278 rätt.** Kolumnerna i Anthropics tabell över förpliktelser (Total, 2026–2030, Thereafter) är rätt.
Åtagandena per motpart (minst 47,2, 121,3 och 110,0 mdr) är rätt angivna, med period och kvalificering. Broadcom är
namngiven i prospektet, så "Infrastructure Partner 2026 NPA" som Broadcom är inte en gissning.

**R26-1 (must_fix): fem rader är daterade till 2026-09-30 men kommer ur S-1:an, som anger juni.**

| Rad | Värde | Daterad | Vad S-1:an (2026-10-26) säger |
|---|---|---|---|
| `anthropic_amazon_2023_npa_notes-2026-09-30-outstanding` | 2 186 | 2026-10-26, rad #7721 | tabellen gäller "as of June 30, 2026" (rad #7710) |
| `anthropic_amazon_2024_npa_notes-2026-09-30-outstanding` | 4 017 | 2026-10-26, rad #7722 | samma tabell |
| `anthropic_amazon_npa_2026-2026-09-30-commitment` | 15 000 | 2026-10-26, rad #7773 | not (1): "As of June 30, 2026" (rad #7775) |
| `anthropic_broadcom_npa_2026-2026-09-30-commitment` | 42 000 | 2026-10-26, rad #7801 | not (1): "As of June 30, 2026" (rad #7803) |
| `anthropic_google_npa_2026-2026-09-30-commitment` | 20 000 | 2026-10-26, rad #7841 | not (1): "As of June 30, 2026" (rad #7843) |

Siffrorna för 2026-09-30 står först i S-1/A 2026-11-02 (rad #7842 och noterna på rad #7909, #7937 och #7977). Talen är
desamma, men en balans per 2026-09-30 är känd en vecka för tidigt. Orsaken är regeln `earliest`: den flyttar en rad till
det tidigaste dokumentet med samma rad, och datumet för en tabellrad står utanför raden. Rapporten visar dem på fyra
rader med "known_from 2026-10-26". Inget mått använder raderna.

Rättning: `earliest` flyttar en rad med balansdag bara till ett dokument som anger samma balansdag för raden (i raden, i
tabellens rubrik eller i dess noter). Bygg om. De fem raderna får S-1/A `0001628280-26-068676`, `filed` 2026-11-02.
Regeländringen skrivs som ett daterat tillägg i registret. Testet `test_r26_1_…` slår om.

**R26-2 (must_fix): CoreWeaves 9,750 %-obligation 2031 är kodad till 1,75 MUSD.** 8-K:n 2026-04-14 skriver "$1,750,000"
(rad #38). 8-K:n 2026-04-21 (`0001769628-26-000183`, rad #38, samma rad som tilläggsemissionen är kodad ur) skriver "on
April 14, 2026, CoreWeave issued $1,750,000,000". Noten i CSV:n och `docs/kallor/kreditlagret.md` säger att talet bara
syns i 10-Q:n för 2026-06-30. Det stämmer inte. Rapporten visar "1,75 MUSD" för Johannes.

Rättning: koda beloppet 1 750 ur 8-K:n 2026-04-21, rad #38, `filed` 2026-04-21. Skrivfelet i 8-K:n 2026-04-14 nämns i
noten. Testet `test_r26_2_…` slår om.

**Tolkningar under kodningen** (`docs/kallor/kreditlagret.md`):
1. Metas tabell över största möjliga förlust: rätt läst (kolumnerna 2026-09-30 och 2025-12-31). Men samma belopp står i
   10-Q 2026Q1 (rad #405: 45,99 mdr, bokfört värde 2,37 mdr) och 2026Q2 (rad #423: 46,03 mdr, 2,92 mdr). De är inte
   kodade och inte listade (R26-4).
2. 1,75 MUSD: se R26-2.
3. Googles kupong 9,0 %: står i noterna och gäller lån före noteringen. Tabellen i MD&A anger "N/A", och efter
   noteringen ska villkoren avtalas. Raden är rätt, men rapporten visar 9 % för de återstående 20 mdr utan förbehåll
   (R26-9).

**Härlett utöver texten** (anmärkning, ingen serie påverkas). `issue_date` är avtalsdagen för tre ramar där inget lån
har getts ut eller där dagen inte anges: `anthropic_broadcom_npa_2026` 2026-03, `anthropic_rent_npa_2025` 2025-08 och
`anthropic_google_2024_npa` 2024-08. Fältet betyder dagen lånet togs. Rapportens rubrik "Hyperion" står inte i Metas
inlämningar, och Blue Owl är bara namngiven för Louisiana (10-Q 2025Q3), inte för Texas.

**R26-3 (should_fix): SpaceX, som äger xAI, saknas i labbdelen.** Sökningen efter OpenAI är rätt gjord och rätt
redovisad: 26 namn som börjar på "OpenAI", bara Form D, ingen registreringsansökan. Andra labb söktes inte. SpaceX (CIK
1181412) köpte xAI 2026-02-02 (10-Q 2026Q3, rad #296). Bolaget har S-1 2026-05-20, S-1/A 2026-06-01 och 2026-06-03,
424B4 2026-06-12, 10-Q 2026-08-04 och 2026-10-22, och 8-K om obligationer i juni 2026. Total skuld var 38 006 MUSD per
2026-09-30 (rad #471). Registret tog bara med Anthropic och OpenAI, så KL1 bröt inte mot posten. Men rapporten säger
bara att OpenAI saknas, och läsaren tror att labbdelen är täckt. Övriga sökningar: "safe superintelligence" 0 träffar,
"thinking machines" och mistral bara fonder och SPV (Mistral Acquisition Co är ett annat bolag). Rättning: skriv i
rapporten att xAI finns i SpaceX:s inlämningar och inte är med. Ta med SpaceX genom ett daterat tillägg i registret före
nästa läsning, om Johannes vill.

**R26-4 (should_fix): okodade kandidater är inte räknade eller listade.** Registret kräver det ("Kandidater som inte
kodas räknas och listas med skäl"). Anthropics 424B4 har 153 kandidatrader (125 skuld, 27 åtaganden, 1 SPV) mot 102
rader. Exempel som inte är kodade: Metas belopp för 2026Q1 och 2026Q2 ovan, Anthropics åtaganden till SpaceXAI (upp till
120,5 mdr, S-1/A 2026-11-10 rad #8356), Nscale (rad #8375) och Lambda (cirka 41,3 mdr, rad #8387), och marginalen 4,25 %
för DDTL 2.0:s nya tranche (8-K 2025-10-02, rad #36). Rättning: en lista `curated/kreditlagret_skipped.csv` (dokument,
plats, skäl), som KR1:s. Koda Metas två kvartal med samma tolkning som 2026Q3, eller skriv skälet.

**Konservativt sena datum** (anmärkning, inget läckage). Raderna söks med exakt SHA-256, så en mening som prospektet
bryter annorlunda räknas som ny. Exempel: höjningarna till 2,75 och 3,25 mdr står i S-1:an (2026-10-26, rad #7628–#7630)
men dateras 2026-11-02.

## 3. Härledda mått

- **Omräkning.** Egen kod räknade om varje version av 30 serier: alla sex mått för Oracle, CoreWeave och Microsoft och
  de tolv lageraggregaten. 0 avvikelser i värde och i `known_from` (= den senaste komponenten). Nivå, takt, förändring i
  takt och överraskning mot B1 räknades om för 13 mått: alla lika.
- **Lagren.** En version finns bara när alla medlemmar har en version. Yttre lagrets capex finns från 2025Q2, med IREN:s
  datum. Dess förändring i takt kommer först med 2026Q4, som spåret skriver.
- **as_of.** Vid sex dagar (2024-11-25, 2025-05-15, 2025-11-25, 2026-04-15, 2026-10-27 och 2026-11-25) ger rapporten
  samma text och samma utslag på hela tabellen och på tabellen kapad på dagen. JSON-utdata skiljer vid de fyra tidiga
  dagarna, men bara i metadata (enhet, metod, tom historik) för serier som inte har någon rad på dagen. Docstringen
  lovar exakt lika. Anmärkning, inget läckage.
- **Framtidsdatering.** Ingen `kl_`-rad är känd efter 2026-11-12. Lagrets kontroller (`warehouse`) ger inga fel för
  `kl_`-serierna. Basens tabell har åtta andra rader med `known_from` 2026-12-01 (eia930 och Epoch), som inte är KL1:s.
- **Effektiv ränta (R26-6, should_fix).** Microsofts räntekostnad (`InterestExpenseNonoperating`) var 3 051 MUSD för
  räkenskapsåret till 2026-06-30. Räntan på leasingskulder för finansiell leasing var 2 547 MUSD samma år (10-K, rad
  #1707). 10-K:n säger att räntekostnaden ökade "primarily due to higher finance lease interest expense" (rad #766).
  Leasingräntan ingår alltså i täljaren, medan nämnaren bara är skulden. Det förklarar 8,2 % och takten +2,5. Det är
  inte priset på skuld. CoreWeave använder `InterestExpenseDebt` (bara skuld). Läsregeln påverkas inte, eftersom A bara
  läser det yttre lagrets ränta. Rättning: förbehåll i rapporten och i källdokumentet.
- **CoreWeaves vägda ränta (R26-5, should_fix).** Serien föll från 10,40 % (2025Q3) till 7,90 % (2026Q3), takt −2,5.
  Utan konvertibler föll den från 10,40 % till 9,52 %. Konvertiblernas andel av utestående gick från 0 till 22,7 %.
  Cirka två tredjedelar av fallet är alltså mixen. Rapporten säger det inte. Rättning: visa andelen konvertibler och
  räntan utan dem bredvid (beskrivning, ingen ny serie).
- **Kupong för nya lån.** Filtret mot konvertibler går på instrumentets namn. Anthropics konvertibla lån har inte ordet
  i namnet, men de faller bort i dag eftersom datumen bara anger månad. Anmärkning: filtret ska inte bero på namnet.

## 4. Rapporten

- `python -m ai_tracker.followed kreditlagret --as-of 2026-11-25` och `--as-of 2025-11-25` ger exakt texten i
  `docs/resultat/kreditlagret.md` (0 rader skiljer).
- Utslagen följer registret: Oracle "talar för", CoreWeave "talar emot (1)", Nebius "inget av mönstren", yttre lagret
  och IREN "kan inte avgöras". Per 2025-11-25 Oracle "talar emot (1)". Förbehållen finns (beskrivning och inget test,
  slump, klumpig RPO, aktiverad ränta).
- **Publika utdata.** Bunten byggd per 2026-11-25 (`site_bundle build --skip-checks`). `site_bundle validate` ger 0
  problem. `kl_`-nycklarna står bara i listan `withheld`, med nyckel, rubrik, källa, licens och skäl, och aldrig med
  värden. Den gamla sidans metodsida visar samma lista. Brevet för 2026-10 nämner inte KL1. Alla 53 serier har
  `publish=False`.
- **Ögonblicksbilden 2026-11-30.** Tillståndskoden läser bara kärnserierna (`register.CORE_SERIES`) och slår upp andra
  serier per nyckel. De nya katalogserierna kommer inte in. R26 byggde inte själva ögonblicksbilden.
- **R26-9 (should_fix): tre missvisande rader i avsnitt 5.**
  - "ram Google 2026: 20,0 mdr (…, kupong 9,00 %)": 9 % gäller lån före noteringen. Efter noteringen ska villkoren
    avtalas, och tabellen i MD&A anger "N/A".
  - "ddtl 2 0 facility 1 300": 13,00 % är marginalen före det femte tillägget för lån utan investment grade. Lån med
    investment grade hade 6,00–6,50 %, och den nya tranchen har 4,25 %.
  - Rubriken "Blue Owl m.fl. (Hyperion och Texas)": se avsnitt 2.
  - Rättning: visa notens förbehåll på raden, eller ta bort talet.

## 5. Licens, katalog och tester

- Alla 53 `kl_`-serier har klassen `ja` (52 härledda ur SEC-serier, en ur den kurerade extraktionen ur sec.gov).
  `catalog.validate` ger inga fel. Inga citat i git: `data/raw` är ignorerad, och noterna i CSV:n är korta och utan
  citat.

**Tester:** `python -m pytest -q` på grenen `auto15/r26-kreditlagret`, med de 53 serierna i den här worktreens
`data/`. Resultatet står sist i dokumentet.

## Fynd

| Id | Allvar | Fynd | Rättning | Test |
|---|---|---|---|---|
| R26-1 | must_fix | Fem rader med balansdag 2026-09-30 dateras till S-1:an 2026-10-26, som anger 30 juni. Läckage på en vecka | `earliest` kräver samma balansdag i det tidigare dokumentet. Raderna får S-1/A 2026-11-02 | `test_r26_1_september_balances_are_not_dated_to_the_june_s1` |
| R26-2 | must_fix | CoreWeaves 9,750 %-obligation 2031 är kodad till 1,75 MUSD. 8-K:n 2026-04-21 anger 1 750 MUSD | Koda 1 750 ur 8-K:n 2026-04-21, rad #38 | `test_r26_2_coreweave_9_75_notes_principal` |
| R26-3 | should_fix | SpaceX (xAI) har S-1, 424B4 och 10-Q, men labbdelen nämner bara Anthropic och OpenAI | Skriv det i rapporten. Daterat tillägg om SpaceX ska med | `test_r26_3_lab_section_names_spacex_xai` |
| R26-4 | should_fix | Okodade kandidater är inte räknade eller listade, som registret kräver. Metas 2026Q1 och 2026Q2 saknas | `curated/kreditlagret_skipped.csv` med skäl. Koda eller förklara Metas två kvartal | `test_r26_4_uncoded_candidates_are_listed_with_a_reason` |
| R26-5 | should_fix | CoreWeaves vägda ränta faller mest av mixen med konvertibler | Visa andelen konvertibler och räntan utan dem | `test_r26_5_coreweave_rate_states_the_convertible_mix` |
| R26-6 | should_fix | Microsofts effektiva ränta innehåller ränta på finansiell leasing (2 547 av 3 051 MUSD, enligt 10-K:n) | Förbehåll i rapporten och källdokumentet | `test_r26_6_effective_rate_caveat_names_lease_interest` |
| R26-7 | should_fix | Läsningarna per 2026-11-25 görs på kvartal som var sedda före posten | En mening i resultatdokumentet och i rapporten | `test_r26_7_results_say_the_first_readings_are_on_seen_data` |
| R26-8 | should_fix | Regeln läser bara uppgång, och A gällde i 28 av 35 Oracle-kvartal | Säg båda sakerna i avsnitt 4. En ändrad regel kräver en ny daterad post | `test_r26_8_reading_states_its_direction_and_how_often_a_holds` |
| R26-9 | should_fix | Googles kupong före noteringen och DDTL 2.0:s gamla marginal visas utan förbehåll | Visa förbehållet på raden | `test_r26_9_lab_lines_qualify_coupon_and_margin` |

Anmärkningar utan test: `issue_date` för avtal utan utgivning, konservativt sena datum, JSON-skillnaden vid kapning,
filtret mot konvertibler på namnet, "(JSON)" mot Atom i posten. Grenen `auto15/kl1-kreditlagret` finns på origin
(`a15b0f5`), fast spårets sammanfattning säger att inget är pushat. R26 vet inte vem som pushade.

## För Johannes

- Läs rapportens avsnitt 1–4 som de är. Läs Microsofts ränta som ränta på skuld och leasing tillsammans.
- Använd inte beloppen i avsnitt 5 förrän R26-1 och R26-2 är rättade.
- Oracles "talar för" per 2026-11-25 bygger på kvartal som var sedda innan regeln låstes. Den första läsningen på osedda
  data kommer med Oracles inlämning omkring 2026-12-11.
- Beslutspunkt: ska SpaceX (xAI) med i labbdelen? Rekommendation: ja, som tabellrader, genom ett daterat tillägg före
  nästa läsning. Bolaget har 38 mdr i skuld och lämnar 10-Q.

## Testsviten

`python -m pytest -q` en gång på grenen, 2026-11-25: **2 314 passerade, 2 fel, 1 överhoppad, 11 xfail** (9:51 min).
De 11 xfail är R26:s nio fynd och två äldre. Båda felen är kända och kommer inte från KL1 eller R26:
- `test_data_quality` (riktiga data): `no_gaps` och `series_in_catalog` för körning 14:s serier i den delade basen
  (`ob_*`, `rev_dell_*`, `rev_csco_*`, `inv_smci` med flera). Deras katalogposter finns inte på grenen. Ingen
  `kl_`-serie finns bland felen.
- `test_committed_fixtures_are_the_current_synthetic_bundle`: fixturens SHA-256 för registret ändrades av KL1:s post.
  Fixturerna byggs om vid integrationen.

`tests/test_r26_kreditlagret.py`: 17 passerade och 9 strikta xfail. Med `--runxfail` faller vart och ett av de nio på
just det fynd som testet gäller.

