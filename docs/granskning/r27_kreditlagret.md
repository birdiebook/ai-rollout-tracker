# R27 – stickprovsgranskning av kreditlagret efter X23

Granskningsspår R27, 2026-11-25, gren `auto15/r27-kreditlagret` (bas `auto15/x23-kreditlagret`, `5890774`). CLAUDE.md
kräver en oberoende stickprovsgranskning innan LLM-extraherade värden används. R27 har inte skrivit koden eller raderna.
Utgångspunkten var att ett värde är fel tills det står i dokumentet.

Granskat:
- alla 64 rader som X23 lade till eller ändrade i `curated/kreditlagret.csv` (`git diff 32e912f auto15/x23-kreditlagret`):
  58 nya (44 SpaceX, 6 Anthropic, 5 Meta, 3 CoreWeave) och 6 ändrade (fem rader från Anthropic och CoreWeaves
  9,750 %-obligation 2031);
- självkontrollen mot nyhämtade dokument för alla 458 rader, som X23 inte kunde avsluta (HTTP 429);
- 60 okodade kandidater ur `curated/kreditlagret_skipped.csv`;
- SpaceX roll i serier, lager och läsregel, och rapporten för båda dagarna.

Underlag. R27 hämtade 58 filer på nytt från www.sec.gov och data.sec.gov: 46 dokument i korpusen, 8 svar från
submissions-API:t och SpaceX S-1 (2026-05-20), 424B4 (2026-06-12) och två 8-K (2026-06-23 och 2026-06-26). Den
generiska klientidentiteten ur `.env`, en begäran i taget och 1,5 s mellan anropen. Inget anrop gav 403 eller 429. Alla
54 filer som fanns i cachen (den delade, och X23:s för SpaceX 10-Q) var byte för byte lika. Kopiorna ligger i
worktreens `data/raw` (gitignorerat).

Inga värden, ingen produktionskod och inga dokument från KL1 eller X23 är ändrade. Testerna står i
`tests/test_r27_kreditlagret.py`: fastlåsta rader och registertext, egenskaper som håller och ett fynd som
`xfail(strict=True)`.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. De 64 raderna | **Rätt i 64 av 64.** Tal, enhet, skala, instrument, bolag, balansdag, kvalificering och datum står i dokumentet. Ingen rad är daterad före det första offentliga dokument som anger värdet. Några rader är daterade senare än nödvändigt (anmärkning A) |
| 2. Självkontrollen mot nyhämtade dokument | **458 av 458 ok.** 0 flyttade, 0 fel i hash, tal, `filed` och `accepted` |
| 3. Okodade kandidater | **60 av 60 rätt överhoppade.** Ingen väsentlig lucka i stickprovet (54 regelrader, 6 agentrader) |
| 4. SpaceX | **OK, med ett fynd.** Ingen serie, inget aggregat och ingen läsning använder raderna. Rapporten säger att skulden gäller hela koncernen. Räntan på övrig finansiering visas utan förbehåll (R27-1) |
| 5. Rapporten | **OK.** Kommandot ger exakt rapporterna i `docs/resultat/kreditlagret.md` per 2026-11-25 och 2025-11-25 |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Inget must_fix. Ett should_fix (R27-1). Extraktionen kan användas som den står,
med förbehållet i R27-1 för SpaceX ränta. Tillsammans med R26 har nu alla 458 rader en oberoende granskning. R26
granskade de 394 rader som X23 inte rörde (278 handlästa, övriga tabellrader med egen tolkning). R27 har läst de 64
som X23 lade till eller ändrade.

## 1. De 64 raderna

Varje rad lästes på sin plats i dokumentet och i sitt sammanhang (tabellrubrik, noter och löptext omkring).

- **Anthropic, fem rader per 2026-09-30** (R26-1). S-1/A `0001628280-26-068676` (2026-11-02) anger balansdagen 30 september 2026 i
  rubriken för utestående lån (rad #7842) och i noterna till tabellerna för Amazon 2026, Broadcom och Google
  (rad #7909, #7937 och #7977). S-1:an 2026-10-26 anger 30 juni på motsvarande platser (rad #7710, #7775, #7803 och
  #7843). Talen 2 186, 4 017, 15 000, 42 000 och 20 000 MUSD står i S-1/A:n. Dateringen är rätt.
- **Anthropic, sex nya rader.** SpaceXAI upp till 120,5 mdr står ordagrant i S-1:an 2026-10-26 (rad #8005–#8008).
  Nscale upp till cirka 44,6 mdr, Lambda cirka 41,3 mdr och Googles TPU-uppskattning 125–150 mdr står i S-1/A:n
  2026-11-02. Kortfristiga avtal efter kvartalet, cirka 6,6 mdr, står i 424B4 (rad #8175–#8177).
- **CoreWeave.** 8-K:n 2026-04-21 (rad #38) anger att obligationerna 2026-04-14 var på 1 750 MUSD, och att serien
  med tilläggsemissionen blev 2 750 MUSD. Det stämmer med 10-Q:n (2 750 MUSD per 2026-06-30). DDTL 3.0 på 2,6 mdr
  (8-K 2025-07-31, rad #37) och marginalen 4,25 % för DDTL 2.0:s nya tranch (8-K 2025-10-02, rad #36) är rätt.
- **Meta.** Bokfört värde 1,83, 2,37 och 2,92 mdr och största möjliga förlust 45,99 och 46,03 mdr gäller
  Louisiana-bolaget per 2025-12-31, 2026-03-31 och 2026-06-30. Texas-bolaget tillkom i juli 2026. Det förklarar
  hoppet till 68,4 mdr per 2026-09-30.
- **SpaceX, 44 rader.** Skuldtabellen i Note 9 går ihop: 25 000 + 27 + 13 406 = 38 433 MUSD per 2026-06-30 och
  25 000 + 27 + 12 979 = 38 006 MUSD per 2026-09-30. Valor-skulden (2 039 + 11 290 och 2 181 + 10 716 MUSD) står i
  noten om närstående och är en del av övrig finansiering. Räntor, löptider, ramar och säkerhet för SpaceX Notes,
  bryggan, kreditfaciliteten och xAI:s lån står i noten. Den vägda kupongen 5,855 % stämmer med de fem tranchernas
  belopp och kuponger i 8-K:n 2026-06-23.

**Anmärkning A, konservativt sena datum (inget läckage).** Några rader står redan i ett tidigare offentligt dokument,
men med annan radbrytning eller utanför den registrerade korpusen. De dateras därför senare än nödvändigt:
- Nscale, Lambda och TPU-uppskattningen (4 rader) står i S-1:an 2026-10-26 men dateras 2026-11-02.
- Kortfristiga avtal efter kvartalet (6,6 mdr) står i S-1/A:n 2026-11-02 men dateras 2026-11-19.
- SpaceX villkor för bryggan, kreditfaciliteten, xAI:s lån och kreditlinan står i S-1:an 2026-05-20, och obligationerna
  i 8-K:n 2026-06-23. X23-tillägget kodar bara 10-Q, så raderna dateras 2026-08-04.

Ingen rad är daterad före det första dokument som anger värdet för balansdagen. Testet låser att ingen rad med full
balansdag är känd före den dagen, och att SpaceX rader inte är kända före den första 10-Q:n.

## 2. Självkontrollen mot nyhämtade dokument

Projektets kontroll (`kreditlagret_check.run`, andel 1,0) kördes på R27:s nyhämtade kopior. Inget dokument lästes ur
cachen. Resultat: **458 av 458 ok, 0 flyttade, 0 fel, 81 instrument.** Kontrollen omfattar hash, att talet står i
citatet och `filed` och `accepted` mot submissions-API:t. Den prövar inte semantiken. Det gör punkt 1 här och R26.

## 3. Okodade kandidater

Stickprovet drogs reproducerbart: `sample(n=60, weights, random_state=27)` med vikten 2 för regelrader och 1 för
agentrader. Det gav 54 regelrader och 6 agentrader (44 CoreWeave, 9 SpaceX, 6 Anthropic och 1 Meta). Varje rad lästes i
sitt dokument.

Alla 60 var rätt överhoppade. Regelraderna var verkligt värde, kostnader, kassaflöden, aktier, inlösen, säkerheter och
upprepningar i MD&A. Varje instrument som nämns har sina belopp och villkor kodade någon annanstans, eller har aldrig
lånats under (CoreWeaves term loan 2025 på 300 MUSD, avslutad vid noteringen). Med 0 fel av 54 regelrader är andelen
väsentliga luckor sannolikt under cirka 6 % (regeln om tre). En riktad sökning i CoreWeaves 147 rader med
regelkategorin "text utanför skuldtabellen" efter nya instrument 2025–2026 hittade bara instrument som är kodade ur 8-K.

**Anmärkning B, regelordningen.** Koden prövar skuldtabellen före de andra reglerna och "verkligt värde" före "aktier".
Registret (X23, punkt 2) har en annan ordning och nämner också SpaceX 10-Q för regeln om annan text. I koden gäller den
regeln bara CoreWeave. SpaceX rader fick i stället agentens skäl. Det påverkar bara vilken etikett en rad får.

**Anmärkning C, X Corp:s lån.** X B-1 (6 504 MUSD, SOFR + 6,50 %) och X B-3 (5 966 MUSD, 9,50 %) fanns per 2025-12-31 och
återbetalades 2026-03-02 med bryggan. De kodas inte, och skälet står i `docs/kallor` (tolkning 9). Rapportens rad
"xAI:s egna lån före köpet" är korrekt som den står, men den visar 5,0 av cirka 17,5 mdr i lån som SpaceX tog över
med xAI.

## 4. SpaceX roll

- Ingen katalogserie har `spacex` i nyckeln. SpaceX finns inte i `OUTER`, `INNER` eller lagrens medlemmar.
- `coupon_out` ger två balansdagar för SpaceX, färre än fyra, så ingen kupongserie skapas. `coupon_new` ger inget.
- Rapporten per 2026-11-25 utan SpaceX rader ger samma mått och samma läsningar. Bara fyra rader i labbdelen och en
  mening i förbehållen skiljer.
- Rapporten och resultatdokumentet säger att skulden gäller hela koncernen: uppskjutning, Starlink och xAI.

## 5. Rapporten

De 53 serierna räknades om med X23:s kod i den här worktreen. Inga nya rader och inga revideringar, alltså samma 1 870
rader som i basen. `python -m ai_tracker.followed kreditlagret --as-of 2026-11-25` och `--as-of 2025-11-25` ger exakt
avsnitten i `docs/resultat/kreditlagret.md`, med rubrikerna en nivå ned.

## Fynd

### R27-1 (should_fix): SpaceX ränta på övrig finansiering visas utan förbehåll

**Belägg.** Rapporten skriver "övrig finansiering 13,0 mdr (vägd fast ränta 6,3 %), varav misslyckade sale-leaseback av
AI-hårdvara med Valor (närstående) 12,9 mdr". 10-Q:n `0001628280-26-066880` anger 6,3 % för bolagets övriga
finansieringsavtal, som enligt texten oftast har maskiner och utrustning som säkerhet (rad #548). Samma 10-Q anger att
räntekostnaden för Valor-avtalen var 351 MUSD under 2026Q3 och 864 MUSD under årets nio första månader (rad #805). För
2026Q2 anger 10-Q:n `0001628280-26-052535` 327 MUSD (rad #784). 351 MUSD under ett kvartal på 12,9–13,3 mdr motsvarar
cirka 10,7 % per år. Valor är 99 % av posten. Läsaren tror då att SpaceX AI-hårdvara finansieras till 6,3 %, men
bolagets egen räntekostnad pekar på ungefär 11 %. Talet 6,3 % är rätt avläst. Det är kopplingen till hela posten som
inte håller. Om SpaceX får fyra balansdagar skapar `coupon_out` en serie som väger 6,3 % mot hela posten.

**Rättning.** Visa räntekostnaden för Valor-avtalen bredvid 6,3 % på raden i avsnitt 5, eller skriv att 6,3 % gäller
övriga finansieringsavtal enligt bolaget och att Valor-skuldens räntekostnad var 351 MUSD under kvartalet. Ta inte med
`spacex_other_financings` i ett framtida `kl_coupon_out_spacex_q` utan ett daterat tillägg i registret. Testet
`test_r27_1_spacex_other_financings_rate_is_qualified` slår då om.

## Anmärkningar utan test

- A–C ovan.
- Lambdas åtagande visas med avtalsmånaden 2026-05. 34,9 av 41,3 mdr kommer från avtalet i augusti 2026.
- `docs/kallor/kreditlagret.md` säger att självkontrollen mot nyhämtade dokument återstår efter X23. Den är nu gjord
  (punkt 2 här).

## Tester

`tests/test_r27_kreditlagret.py`: 14 passerar och 1 strikt xfail. Med `--runxfail` faller xfail på just sitt fynd. Tre
testfall är `real_data` och kräver de 53 serierna i observationstabellen.

Hela sviten en gång (9:32 min): 2 341 passerade, 2 fel, 3 överhoppade och 3 xfail. Felen är desamma som efter X23 och
kommer inte från KL1, X23 eller R27. `test_data_quality` gäller körning 14:s serier i den delade basen (`ob_*`,
`rev_csco_*`, `inv_smci`), och ingen `kl_`-serie finns bland felen. `test_committed_fixtures_are_the_current_synthetic_bundle`
gäller registrets SHA-256 i fixturen, som ändrades av KL1:s post och X23:s tillägg.
