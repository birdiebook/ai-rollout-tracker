# Källor: Kreditlagret (KL1)

Följd fråga: "Ändras finansieringens pris och tillgång i de yttre lagren, och följer investeringstakten där med?"
Måtten, läsregeln och kodningsreglerna står i `docs/mattregister.md`, posten "2026-11-25 – KL1" och dess tillägg.
Rapporten står i `docs/resultat/kreditlagret.md`.

## Två slags underlag

1. **Härledda serier ur katalogen** (`src/ai_tracker/series/kreditlagret.py`). De bygger på befintliga XBRL-serier:
   `capex_*`, `ocf_*`, `interest_exp_*`, `lt_debt_*`, `debt_issued_*`, `debt_repaid_*`, `lease_uncommenced_*` och
   `rpo_*`. Inga nya hämtningar. Versionerna dateras som A5: `known_from` = den senaste komponenten som används.
2. **Extraktion ur EDGAR-text** (`curated/kreditlagret.csv`, 400 rader, 64 instrument). Lån, ramar och åtaganden som
   inte finns i XBRL: Anthropics registreringsansökan, CoreWeaves 8-K och skuldtabeller och Metas datacenterbolag.

Alla serier är katalogserier med `publish=False` och klassen `ja` för kommersiell användning (SEC: public information,
sec.gov/privacy). Ingen är kärnserie, och inget grenindex ändras.

## Korpus (regeln låst före läsningen)

| Bolag | Dokument | Antal | Kodat |
|---|---|---|---|
| Anthropic, PBC (CIK 2130357) | S-1 2026-10-26, S-1/A 2026-11-02, 2026-11-10 och 2026-11-17, 424B4 2026-11-19 | 5 | 102 rader ur 424B4, daterade till det tidigaste dokumentet med samma rad |
| OpenAI | ingen registreringsansökan (se nedan) | 0 | – |
| CoreWeave (CIK 1769628) | 10-Q och 10-K 2025-05-15–2026-11-12, och 8-K med post 1.01 eller 2.03 | 7 + 17 | 225 rader ur skuldtabellerna (tolkningen), 58 rader ur 8-K |
| Meta (CIK 1326801) | 10-Q och 10-K 2025-01-30–2026-10-22 | 8 | 15 rader (Hyperion och Texas) |
| Oracle (CIK 1341439) | 10-Q och 10-K 2025-03-11–2026-09-11 | 7 | inga: inga belopp för datacenter-SPV eller samriskbolag |

**OpenAI.** Sökningen gjordes 2026-11-25 i EDGAR:s företagssökning (`www.sec.gov/cgi-bin/browse-edgar?company=openai
&owner=include&action=getcompany&output=atom&count=100`). EDGAR:s fulltextsökning (efts.sec.gov) är blockerad av nätet
i miljön. Sökningen gav 26 bolag vars namn börjar på "OpenAI": fonder och SPV (till exempel "OpenAI Startup Fund I,
L.P." och serier av CGF2021 LLC) med bara Form D. Inget av dem har S-1, S-1/A, F-1 eller F-1/A. Det betyder att
OpenAI inte har någon registreringsansökan under ett namn som börjar på "OpenAI". Ett annat bolagsnamn har inte
prövats. Resultatet sparas i `data/raw/kreditlagret_corpus/openai_search.json`.

**Oracle.** Kandidatraderna (Hyperion, joint venture, variable interest entity, residual value guarantee, special
purpose, med belopp) i Oracles 10-Q och 10-K 2025–2026 gällde bara icke-marknadsnoterade investeringar (Ampere,
TikTok USDS). Ingen rad anger belopp för datacenter-SPV, samriskbolag eller leasingupplägg utöver det som redan finns
i `lease_uncommenced_orcl`. Inget har kodats.

## Text, plats och kontroll

- Text: KR1:s radlista (`credit_issuance_corpus.lines`). Plats `line #k`, eller `lines #a-#b` för en mening som
  prospektet bryter över flera rader. SHA-256 av raden eller raderna. Citatet sparas bara under
  `data/raw/kreditlagret_quotes/<id>.txt` (gitignorerat). CSV:n har bara siffror, koder och referenser.
- Bygget (`python -m ai_tracker.sources.kreditlagret build`) läser de cachade dokumenten. Varje rad stoppas om dess
  värde inte står i citatet. Agentens kodning står i `src/ai_tracker/sources/kreditlagret_coding.py` (plats och värde,
  ingen text). CoreWeaves skuldtabeller kodas av `debt_table`.
- Självkontrollen (`python -m ai_tracker.kreditlagret_check --frac 1.0`) hämtade varje dokument igen utan cache
  2026-11-25: **400 av 400 rader ok, 0 flyttade, 0 fel** (hash, tal i citatet, `filed` och `accepted` mot
  submissions-API:t). Den prövar inte semantiken: vilket instrument, vilken balansdag och om talet är rätt tal.
  En oberoende stickprovsgranskning av extraktionen återstår.
- SEC: den generiska klientidentiteten ur `.env`, en begäran i taget, 0,3 sekunder mellan dokument, stopp vid 403
  eller 429.

## Tolkningar under kodningen

Skrivna här och inte i reglerna, som KR1.
1. **Metas tabell över största möjliga förlust** (10-Q 2026Q3, rader #427–#431). Raderna nämner inte kandidatorden
   (utom restvärdesgarantin), men tabellens rubrik gäller de okonsoliderade datacenterbolagen. De kodas som
   Hyperion-belopp.
2. **CoreWeaves 9,750 %-obligation 2031** (8-K 2026-04-14, rad #38) anger "$1,750,000". Beloppet kodas som det står
   (1,75 MUSD), med en not. 10-Q:n för 2026-06-30 visar 2 750 MUSD för serien med tilläggsemissionen på 1 000 MUSD, så
   talet är troligen 1 750 MUSD. Det påverkar bara vikterna i tabellraderna, eftersom `kl_coupon_new_crwv_q` inte finns
   (tre kvartal, färre än fyra).
3. **Googles NPA 2026.** Tabellen i MD&A anger räntan som "N/A" efter börsnoteringen, medan noten anger 9,0 %. Båda
   står i noten till raden. Kupongen 9,0 % kodas ur noten.
4. **Anthropics A&R-facilitet.** Marginalen anges inte som tal ("plus an applicable margin"), så ingen `margin_bp`.
5. **Datum som bara anger månad** kodas som `ÅÅÅÅ-MM` (tillägget, punkt 2). CoreWeaves förfallodagar i tabellen
   anges som månad.
6. **Nollbelopp** i skuldtabellen ("—") kodas inte, eftersom de inte bidrar till det vägda medlet.
7. **Microsofts effektiva ränta** är hög (8,2 % per 2026Q3). Räntekostnadens tagg kan omfatta ränta på finansiell
   leasing och annat, medan nämnaren bara är skulden. Det är inte verifierat. Samma förbehåll gäller de andra bolagens
   taggar (`docs/kallor/finansiering.md`).

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
kvartal, och Anthropics lån är konvertibler. Värdena står som tabellrader. Lageraggregatens medlemmar står i registret.

## Kända luckor

- Nebius och IREN saknar skuldserier (Nebius lämnar 20-F med årlig XBRL, IREN lämnar 10-Q från räkenskapsåret 2026).
  En IREN-serie ur companyfacts skulle gå att lägga till.
- Privat kredit utanför EDGAR, labbens oregistrerade skuld, spreadar på andrahandsmarknaden (licens) och 144A-affärer
  utan 8-K. CoreWeaves 144A-obligationer syns, eftersom de har 8-K.
- Anthropic lämnar sin första periodrapport efter noteringen. Då kan skuld och åtaganden följas per kvartal.

## Kommandon

    python -m ai_tracker.sources.kreditlagret corpus        # hämtar korpusen (cachade råkopior)
    python -m ai_tracker.sources.kreditlagret openai        # sökningen efter OpenAI
    python -m ai_tracker.sources.kreditlagret build         # skriver curated/kreditlagret.csv och citaten
    python -m ai_tracker.kreditlagret_check --frac 1.0      # självkontroll mot nyhämtade dokument
    python -m ai_tracker.observations kl_capex4_outer ...   # räknar serierna (härledda, ur tabellen)
    python -m ai_tracker.followed kreditlagret --as-of 2026-11-25

Ordningen i git: registerposten (4bcb077), tillägget före kodningen (60af26f), extraktionen (cdf7811), serierna,
rapporten och testerna (3694573), därefter dokumenten.
