# Källor: Kreditlagret (KL1)

Följd fråga: "Ändras finansieringens pris och tillgång i de yttre lagren, och följer investeringstakten där med?"
Måtten, läsregeln och kodningsreglerna står i `docs/mattregister.md`, posten "2026-11-25 – KL1", dess tillägg och
rättningen "2026-11-25 – X23" efter granskningen R26 (`docs/granskning/r26_kreditlagret.md`).
Rapporten står i `docs/resultat/kreditlagret.md`.

## Två slags underlag

1. **Härledda serier ur katalogen** (`src/ai_tracker/series/kreditlagret.py`). De bygger på befintliga XBRL-serier:
   `capex_*`, `ocf_*`, `interest_exp_*`, `lt_debt_*`, `debt_issued_*`, `debt_repaid_*`, `lease_uncommenced_*` och
   `rpo_*`. Inga nya hämtningar. Versionerna dateras som A5: `known_from` = den senaste komponenten som används.
2. **Extraktion ur EDGAR-text** (`curated/kreditlagret.csv`, 458 rader, 81 instrument). Lån, ramar och åtaganden som
   inte finns i XBRL: Anthropics registreringsansökan, SpaceX:s 10-Q (xAI), CoreWeaves 8-K och skuldtabeller och Metas
   datacenterbolag. Okodade kandidatrader står med skäl i `curated/kreditlagret_skipped.csv` (753 rader).

Alla serier är katalogserier med `publish=False` och klassen `ja` för kommersiell användning (SEC: public information,
sec.gov/privacy). Ingen är kärnserie, och inget grenindex ändras.

## Korpus (regeln låst före läsningen)

| Bolag | Dokument | Antal | Kodat |
|---|---|---|---|
| Anthropic, PBC (CIK 2130357) | S-1 2026-10-26, S-1/A 2026-11-02, 2026-11-10 och 2026-11-17, 424B4 2026-11-19 | 5 | 108 rader ur 424B4, daterade till det tidigaste dokumentet med samma rad och samma balansdag |
| SpaceX (CIK 1181412, äger xAI) | 10-Q 2026-08-04 och 2026-10-22 (efter noteringen 2026-06-12) | 2 | 44 rader (X23) |
| OpenAI | ingen registreringsansökan (se nedan) | 0 | – |
| CoreWeave (CIK 1769628) | 10-Q och 10-K 2025-05-15–2026-11-12, och 8-K med post 1.01 eller 2.03 | 7 + 17 | 225 rader ur skuldtabellerna (tolkningen), 61 rader ur 8-K |
| Meta (CIK 1326801) | 10-Q och 10-K 2025-01-30–2026-10-22 | 8 | 20 rader (Louisiana och Texas) |
| Oracle (CIK 1341439) | 10-Q och 10-K 2025-03-11–2026-09-11 | 7 | inga: inga belopp för datacenter-SPV eller samriskbolag |

**OpenAI.** Sökningen gjordes 2026-11-25 i EDGAR:s företagssökning (`www.sec.gov/cgi-bin/browse-edgar?company=openai
&owner=include&action=getcompany&output=atom&count=100`). EDGAR:s fulltextsökning (efts.sec.gov) är blockerad av nätet
i miljön. Sökningen gav 26 bolag vars namn börjar på "OpenAI": fonder och SPV (till exempel "OpenAI Startup Fund I,
L.P." och serier av CGF2021 LLC) med bara Form D. Inget av dem har S-1, S-1/A, F-1 eller F-1/A. Det betyder att
OpenAI inte har någon registreringsansökan under ett namn som börjar på "OpenAI". Ett annat bolagsnamn har inte
prövats. Resultatet sparas i `data/raw/kreditlagret_corpus/openai_search.json`.

**SpaceX (X23).** SpaceX köpte xAI 2026-02-02 (10-Q 2026Q3, rad #296). Korpusen är bolagets 10-Q och 10-K efter
noteringen: två 10-Q. Prospekten och 8-K kodas inte, eftersom 10-Q:erna redovisar skulden som innevarande period.
Skulden gäller hela koncernen (uppskjutning, Starlink och xAI). Den totala skulden var 38 433 MUSD per 2026-06-30 och
38 006 MUSD per 2026-09-30. SpaceX ingår inte i lageraggregaten eller i läsregeln. `kl_coupon_out_spacex_q` finns inte,
eftersom bara två balansdagar har värde.

**Andra labb.** R26 sökte i företagssökningen på xai, x.ai, spacex, mistral, "safe superintelligence" och "thinking
machines". Bara SpaceX har en registreringsansökan. De andra gav inga träffar eller bara fonder och SPV.

**Oracle.** Kandidatraderna (Hyperion, joint venture, variable interest entity, residual value guarantee, special
purpose, med belopp) i Oracles 10-Q och 10-K 2025–2026 gällde bara icke-marknadsnoterade investeringar (Ampere,
TikTok USDS). Ingen rad anger belopp för datacenter-SPV, samriskbolag eller leasingupplägg utöver det som redan finns
i `lease_uncommenced_orcl`. Inget har kodats.

## Text, plats och kontroll

- Text: KR1:s radlista (`credit_issuance_corpus.lines`). Plats `line #k`, eller `lines #a-#b` för en mening som
  prospektet bryter över flera rader. SHA-256 av raden eller raderna. Citatet sparas bara under
  `data/raw/kreditlagret_quotes/<id>.txt` (gitignorerat). CSV:n har bara siffror, koder och referenser.
- Bygget (`python -m ai_tracker.sources.kreditlagret build`) läser de cachade dokumenten. Varje rad stoppas om dess
  värde inte står i citatet. Bygget skriver också listan över okodade kandidater.
- **Datering i labbens korpus** (X23, punkt 1). En rad flyttas till det tidigaste dokument där samma citat står. En rad
  med full balansdag flyttas bara dit om dokumentet anger samma balansdag: i citatet, som "as of <dag>" i de 30 raderna
  före tabellen eller i tabellens noter, eller för löptext inom 30 rader före och efter (`stated_dates`). Före
  rättningen flyttades fem rader per 2026-09-30 till S-1:an 2026-10-26, vars tabeller gäller 30 juni (R26-1). De har nu
  S-1/A 2026-11-02. Regeln är konservativ: höjningarna till 2,75 och 3,25 mdr står redan i S-1:an med en annan
  radbrytning men dateras 2026-11-02. Agentens kodning står i `src/ai_tracker/sources/kreditlagret_coding.py` (plats och värde,
  ingen text). CoreWeaves skuldtabeller kodas av `debt_table`.
- Självkontrollen (`python -m ai_tracker.kreditlagret_check --frac 1.0`) hämtade varje dokument igen utan cache
  2026-11-25: **400 av 400 rader ok, 0 flyttade, 0 fel** (hash, tal i citatet, `filed` och `accepted` mot
  submissions-API:t). Den prövar inte semantiken: vilket instrument, vilken balansdag och om talet är rätt tal.
  R26 hämtade om alla dokument och handläste 278 rader (70 %): 272 rätt, de sex felen rättade i X23.
- X23 körde självkontrollen igen 2026-11-25. SEC svarade HTTP 429 på CoreWeaves submissions-anrop, och körningen
  stoppades enligt regeln utan nya försök. Kontrollen mot de cachade kopiorna (samma kod, datum mot korpuslistorna ur
  submissions-API:t) gav **458 av 458 rader ok**. De 58 nya och de 6 ändrade raderna lästes för hand mot citatet av
  agenten. De har ingen oberoende granskning ännu.
- SEC: den generiska klientidentiteten ur `.env`, en begäran i taget, 0,3 sekunder mellan dokument, stopp vid 403
  eller 429.

## Tolkningar under kodningen

Skrivna här och inte i reglerna, som KR1.
1. **Metas tabell över största möjliga förlust** (10-Q 2026Q3, rader #427–#431). Tabellens rubrik gäller de
   okonsoliderade datacenterbolagen (`meta_dc_ventures`). Samma belopp står i en mening i 10-K 2025 och i 10-Q för
   2026Q1 och 2026Q2, när bara Louisiana-bolaget fanns. De kodas med samma tolkning (X23). Namnet "Hyperion" står inte i
   Metas inlämningar. Blue Owl är namngiven för Louisiana (10-Q 2025Q3, rad #601).
2. **CoreWeaves 9,750 %-obligation 2031.** 8-K:n 2026-04-14 (rad #38) skriver "$1,750,000", ett skrivfel. 8-K:n
   2026-04-21 (rad #38) anger att obligationerna 2026-04-14 var på $1,750,000,000. Beloppet kodas till 1 750 MUSD ur
   den, med `filed` 2026-04-21 (R26-2). Före rättningen stod 1,75 MUSD här.
3. **Googles och Amazons NPA 2026.** Noterna anger kupongen 9,0 % och 8,0 % för lån före noteringen. Efter noteringen
   ska Googles villkor avtalas, och Amazons dragningar regleras i aktier. Tabellen i MD&A anger "N/A". Rapporten visar
   kupongen med det förbehållet (R26-9).
4. **Anthropics A&R-facilitet.** Marginalen anges inte som tal ("plus an applicable margin"), så ingen `margin_bp`.
5. **Datum som bara anger månad** kodas som `ÅÅÅÅ-MM` (tillägget, punkt 2). CoreWeaves förfallodagar i tabellen
   anges som månad.
6. **Nollbelopp** i skuldtabellen ("—") kodas inte, eftersom de inte bidrar till det vägda medlet.
7. **Microsofts effektiva ränta** är hög (8,2 % per 2026Q3). Räntekostnaden innehåller ränta på finansiell leasing:
   2 547 av 3 051 MUSD för räkenskapsåret till 2026-06-30 (`FinanceLeaseInterestExpense` och
   `InterestExpenseNonoperating` i 10-K `0001193125-26-323660`). Enligt R26 säger 10-K:n att ökningen främst kommer
   från leasingräntan. Nämnaren är bara skulden. Måttet är alltså ränta på skuld och leasing tillsammans och inte priset
   på skuld (R26-6). Microsoft står kvar i det inre lagrets ränta, eftersom måttet är låst och läsregeln bara läser det
   yttre lagrets ränta. Samma förbehåll kan gälla de andra bolagens taggar (`docs/kallor/finansiering.md`).
8. **CoreWeaves vägda ränta och konvertiblerna** (R26-5). Konvertiblerna ingår (tillägget, punkt 4) och har 2–3 %
   ränta i tabellen. Deras andel av utestående gick från 0 till 22,7 % mellan 2025Q3 och 2026Q3. Rapporten visar
   räntan utan dem bredvid: 10,4 % och 9,5 %, mot 10,4 % och 7,9 % med dem.
9. **SpaceX.** Övrig finansiering (12 979 MUSD per 2026-09-30) är mest misslyckade sale-leaseback av AI-hårdvara med
   Valor, som är närstående: 2 181 MUSD kortfristigt och 10 716 MUSD långfristigt. De två beloppen kodas som delar
   (`spacex_valor_current`, `spacex_valor_noncurrent`) och räknas inte en gång till i den vägda räntan. xAI:s egna lån
   från 2025-06 (12,5 % obligationer på 3 000 MUSD och två terminslån på 1 000 MUSD) kodas, fast de återbetalades
   2026-03. X Corp:s lån från köpet av Twitter kodas inte. SpaceX Notes har fem trancher, så förfallodagen kodas inte.
10. **Anthropics åtaganden per motpart.** SpaceXAI (upp till 120,5 mdr), Nscale (upp till cirka 44,6 mdr) och Lambda
   (cirka 41,3 mdr) kodas som Microsoft, Google och Amazon (X23). Googles TPU-kapacitet utan fast belopp (cirka
   125–150 mdr) kodas som uppskattning. Den kan överlappa spannet 150–175 mdr för avtal utan fast belopp.
11. **`issue_date` för ramar** där inget lån har getts ut, eller där dagen inte anges, är avtalsdagen:
   `anthropic_broadcom_npa_2026`, `anthropic_rent_npa_2025` och `anthropic_google_2024_npa` (R26, anmärkning).

## Serierna

| Nyckel | Vad | Bolag |
|---|---|---|
| `kl_rate_eff_<x>` | räntekostnad över fyra kvartal / genomsnittlig långfristig skuld, % per år | orcl, crwv, msft, googl, amzn, meta, outer, inner |
| `kl_fcfgap_<x>` | (capex − OCF) / capex, fyra kvartal, % | alla åtta, outer, inner |
| `kl_netdebt_<x>` | (emitterad − amorterad skuld) / capex, fyra kvartal, % | orcl, crwv, de fyra inre, outer, inner |
| `kl_leases_<x>` | tecknade leasingavtal som inte börjat / capex, fyra kvartal, % | orcl, crwv, googl, amzn, meta, msft (till 2026Q1), msft_cond (från 2026Q2), outer, inner |
| `kl_capex4_<x>` | capex över fyra kvartal, MUSD | alla åtta, outer, inner |
| `kl_rpo_add4_<x>` | RPO nu minus fyra kvartal tidigare, MUSD | orcl, crwv, msft, googl, amzn, outer, inner |
| `kl_coupon_out_crwv_q` | utestående-vägd angiven effektiv ränta på CoreWeaves skuld, % | crwv (sju kvartal) |

`kl_coupon_new_<bolag>_q` finns inte: CoreWeave har nya obligationer med fast ränta i USD (utan konvertibler) i tre
kvartal, och Anthropics lån är konvertibler. Filtret mot konvertibler går på kodningen: namnet eller Anthropics NPA
(X23). Värdena står som tabellrader. Lageraggregatens medlemmar står i registret.

## Okodade kandidater (X23)

`curated/kreditlagret_skipped.csv` listar varje kandidatrad som ingen kodad rad täcker: 753 rader (Anthropic 121,
CoreWeave 502, SpaceX 118, Meta 9 och Oracle 3). Kolumnerna är `company`, `accession`, `filed`, `form`, `locator`,
`kind`, `reason` och `reason_by`. 131 skäl är agentens egna, en rad i taget (`agent`, i
`sources/kreditlagret_coding.SKIP`). 622 skäl sätts av en regel i fasta kategorier (`regel`): bilageförteckning,
verkligt värde och resultatposter, aktier och konvertering, villkor utanför kodningsreglerna, garanti och säkerhet,
andra rader i CoreWeaves skuldtabell och annan text i CoreWeaves 10-Q och 10-K. En regelkategori är inte en läsning
av raden. De flesta regelrader är CoreWeaves 10-Q och 10-K, där balanserna kodas ur skuldtabellen och villkoren ur 8-K.

## Kända luckor

- Nebius och IREN saknar skuldserier (Nebius lämnar 20-F med årlig XBRL, IREN lämnar 10-Q från räkenskapsåret 2026).
  En IREN-serie ur companyfacts skulle gå att lägga till.
- Privat kredit utanför EDGAR, labbens oregistrerade skuld, spreadar på andrahandsmarknaden (licens) och 144A-affärer
  utan 8-K. CoreWeaves 144A-obligationer syns, eftersom de har 8-K.
- Anthropic lämnar sin första periodrapport efter noteringen. Då kan skuld och åtaganden följas per kvartal.

## Kommandon

    python -m ai_tracker.sources.kreditlagret corpus        # hämtar korpusen (cachade råkopior)
    python -m ai_tracker.sources.kreditlagret openai        # sökningen efter OpenAI
    python -m ai_tracker.sources.kreditlagret build         # skriver curated/kreditlagret.csv, citaten och
                                                            # curated/kreditlagret_skipped.csv
    python -m ai_tracker.kreditlagret_check --frac 1.0      # självkontroll mot nyhämtade dokument
    python -m ai_tracker.observations kl_capex4_outer ...   # räknar serierna (härledda, ur tabellen)
    python -m ai_tracker.followed kreditlagret --as-of 2026-11-25

Ordningen i git: registerposten (4bcb077), tillägget före kodningen (60af26f), extraktionen (cdf7811), serierna,
rapporten och testerna (3694573), därefter dokumenten. Granskningen R26 (32e912f). Rättningen X23: tillägget i
registret (599b24e) före koden och före hämtningen av SpaceX:s dokument, därefter koden, raderna och dokumenten.
