# Källa: spread vid emission för AI-tunga emittenter (spår KR1)

Spår KR1, körning 14, 2026-11-25. Kreditpriset för de bolag som bär AI-utbyggnaden, som spreaden mot statsobligationen
när obligationen emitteras. Projektet har redan volymerna (`debt_issued_<bolag>`, `debt_repaid_<bolag>`, leasing,
[finansiering.md](finansiering.md)), men inget pris. Spreaden vid emission är ett pris, och den står i de offentliga
villkorsbilagorna (pricing term sheets) på EDGAR. Bara extraktion och katalogserier. Inga takter och inga jämförelser.

Avsnittet "Kodningsregler" skrevs och committades **innan** något dokument i korpusen hämtades eller någon tranche
kodades. Före låsningen hade agenten sett två saker. (1) Antalet inlämningar per bolag, år och formulär (FWP, 424B2,
424B3, 424B4, 424B5, S-3, S-3ASR) ur EDGAR:s submissions-index, alltså formulärtyp och inlämningsdag, inget innehåll.
(2) Licenstexten i FRED:s serienoter för de möjliga marknadsindexen (avsnittet "Jämförelse med marknaden"), inga
värden. Agenten känner till de stora emissionerna 2020–2025 ur allmän rapportering (Oracle 2020, Amazon 2021, Meta
2022–2025, Alphabet 2025) och villkorsbilagornas vanliga form, men hade inte läst något dokument i korpusen. Tolkningar
som behövs under kodningen skrivs i ett eget avsnitt och skrivs inte in i reglerna i efterhand. Parsern skrivs efter
låsningen, mot dokumenten. En ändring av parsern är ingen regeländring, men den syns i git.

## Kodningsregler (låsta 2026-11-25, före kodningen)

### Korpus

- **Emittenter:** Microsoft (msft, CIK 789019), Alphabet (googl, 1652044), Amazon (amzn, 1018724), Meta (meta,
  1326801), Oracle (orcl, 1341439) och CoreWeave (crwv, 1769628). Samma CIK som i `series/sec_finansiering.py`.
- **Dokument:** primärdokumentet i varje inlämning med formuläret FWP, 424B2 eller 424B5 och EDGAR:s `filingDate`
  2020-01-01–2026-11-25. 424B3 (återförsäljning, utbyte), 424B4 (börsnotering), S-3, S-3ASR, S-4 och 8-K ingår inte.
- **Slutliga villkor.** Ett dokument kodas bara om det anger de slutliga villkoren för minst en tranche: belopp, kupong
  eller ränta, förfallodag och pris till investerare. Ett preliminärt prospekttillägg ("Subject to Completion") och en
  FWP utan slutliga villkor (presentation, aktieerbjudande, annat) kodas inte. De listas med skäl.
- **Ett erbjudande, en källa.** Ett erbjudande är emittent och prisdag med sina tranchar (kupong och förfallodag).
  Finns en FWP med de slutliga villkoren är den källan. Annars är det slutliga prospekttillägget (424B2 eller 424B5)
  källan. Ett senare dokument om samma tranche kodas inte, men det används i självkontrollen.

### Text och plats

- Texten är radlistan `credit_issuance_corpus.lines(html)`: varje tabellrad blir en rad med cellerna åtskilda av
  " | ", varje block (stycke, rubrik, radbrytning) blir en egen rad, blanktecken slås ihop, och tomma rader tas bort.
  Raderna räknas från 0.
- **Plats** = `lines #a-#b`, tranchens block i radlistan: från tranchens första rad med ett villkor (eller rubriken)
  till den sista. När trancherna står som kolumner i en gemensam tabell är blocket hela tabellen, och platsen får
  tillägget ` col #j` (tranchens kolumn bland värdekolumnerna, från 0).
- **SHA-256** räknas av blockets rader, var och en normaliserad, sammanfogade med radbrytning (`block_hash`).

### Rader i `curated/credit_issuance.csv`

En rad per tranche. Alla tal i en rad ska stå i blocket som platsen pekar på (i kolumnen när den anges), utom
`tenor_years` (räknas) och, när det står så nedan, ett datum som räknas fram.

| Kolumn | Innehåll |
|---|---|
| `id` | `<bolag>_<prisdag>_<nn>`, nn = tranchens ordning i dokumentet från 01 |
| `company` | bolagets kod ovan |
| `currency` | ISO-kod som det står ("$" = USD, "€" = EUR) |
| `rate_type` | `fixed` eller `floating` |
| `security` | tranchens namn som det står, kort ("4.700% Notes due 2034") |
| `principal` | belopp i miljoner av valutan ("$1,250,000,000" och "$1.25 billion" = 1 250) |
| `pricing_date` | "Trade Date" eller "Pricing Date". Saknas den: datumet i dokumentets rubrik. Saknas också det: `filed`, och noten säger det |
| `settlement_date` | "Settlement Date" som det står. Står bara "T+n": n vardagar efter prisdagen (lördag och söndag räknas inte, helger inte heller), och noten säger det |
| `maturity` | förfallodagen som den står |
| `tenor_years` | (maturity − pricing_date) i dagar / 365,25, två decimaler. Räknas av koden och kontrolleras vid inläsning |
| `coupon_pct` | kupong i procent per år för fast ränta. Tom för rörlig ränta |
| `benchmark` | referensen som den står, kort ("UST 4.250% due November 15, 2034", "Compounded SOFR") |
| `benchmark_type` | `treasury` (amerikansk statsobligation), `sofr`, `mid_swaps` eller `other` |
| `benchmark_yield_pct` | referensens avkastning i procent, om den står |
| `spread_bp` | spreaden mot referensen i baspunkter som den står ("T+45 bps", "+45 basis points", "+0.45%" = 45). Räknas aldrig fram. Tom om den inte står |
| `yield_pct` | emissionens avkastning till förfall (re-offer yield) som den står |
| `price_pct` | pris till investerare i procent av nominellt belopp |
| `filed`, `accepted` | EDGAR:s `filingDate` (= known_from) och `acceptanceDateTime` |
| `form`, `source_url`, `accession` | formulär (FWP, 424B2, 424B5), dokumentets arkivadress och accessionsnummer |
| `locator`, `block_sha256` | plats och hash, se ovan |
| `method` | `parser` (den deterministiska tolkningen) eller `manual` (agenten kodade för hand, noten säger varför) |
| `note` | kort not utan citat |

Blocket sparas bara under `data/raw/credit_issuance_blocks/<id>.txt` (gitignorerad). Inget citat i git.

### Tal

- Belopp, kupong, avkastning, spread och pris kodas som de står, utan avrundning och utan beräkning.
- Ett belopp i en annan valuta räknas inte om till USD.
- Spread anges i baspunkter. "+0.45%" eller "0.45 percent" blir 45. En spread som bara går att räkna fram (avkastning
  minus referensens avkastning) kodas inte.

### Inte kodat

- Företagscertifikat, banklån, terminslån och kreditfaciliteter. De har inga villkorsbilagor på EDGAR.
- Privata placeringar, 144A-obligationer och finansiering i SPV eller projektbolag (till exempel Metas finansiering av
  Hyperion 2025). De registreras inte, så de finns inte i korpusen.
- Konvertibla skuldebrev, aktier och preferensaktier: de prissätts inte som en spread mot statsobligationen.
- Utbyteserbjudanden, remarketing och prospekt för återförsäljning.

### Serier (katalog, gren G5, kvartal)

- **`issuance_<bolag>_q`:** summan av `principal` (MUSD) för tranchar i USD, med fast och rörlig ränta, med prisdag i
  kalenderkvartalet. Bara för bolag med minst en tranche i USD.
- **`spread_issue_ai_q`:** principalvägt medelvärde av `spread_bp` över alla tranchar som är i USD, har fast ränta,
  har `benchmark_type` = `treasury` och har en angiven spread, med prisdag i kvartalet, över alla emittenter. Vikten är
  `principal` (MUSD). Enhet bp.
- **`spread_issue_ai_7_12y_q`:** samma, bara tranchar vars löptid avrundad till hela år är 7–12 (6,5 ≤ `tenor_years`
  < 12,5). Det kontrollerar för löptidsmixen.
- **`spread_issue_<bolag>_q`:** samma per emittent, bara för en emittent med minst fyra kvartal med en sådan tranche i
  korpusen.
- **Luckregeln.** Ett kvartal utan någon tranche som uppfyller villkoren har inget värde. Det är en lucka, inte noll.
  Alla serier står i `KNOWN_GAPS`.
- **Datering (läckagekritiskt).** Värdet för kvartal q dateras till max(dagen efter kvartalets slut, senaste `filed`
  bland trancherna som ingår). En tranche i q som lämnas in efter det datumet ger en ny version, daterad till sin
  inlämning. Ett kvartal som inte är slut på hämtningsdagen har inget värde.
- `lag_days` = 1. Emission är oregelbunden, så `max_age_days` = 1 100 (tre år), med skälet i noten.
- **Publicering:** `publish=False` tills extraktionsgranskningen har godkänt. Klass för kommersiell användning: den
  kurerade regeln (alla rader på sec.gov) och SEC:s villkor, alltså `ja` om alla rader kommer från sec.gov.
- **Inte kärnserier.** De ingår inte i grenarnas tillstånd, diffusionsindex eller takter.

### Avstämning mot XBRL (rapport, ingen serie)

- **Täckningsgrad** per bolag och kalenderår: summan av `principal` för USD-tranchar, placerade i bolagets
  räkenskapskvartal efter `settlement_date` och mappade till kalenderkvartal med mittpunktsregeln
  (`docs/kallor/sec.md`), delad med summan av `debt_issued_<bolag>` (senaste versionen) för samma kvartal. Också per
  kvartal med emission. `python -m ai_tracker.sources.credit_issuance coverage`.
- **Väntade skillnader:** `debt_issued` är likviden (efter rabatt och kostnader, cirka 99 % av beloppet). Taggarna
  omfattar också företagscertifikat med löptid över tre månader (Microsoft), terminslån och kreditfaciliteter (Oracle),
  annan upplåning (Alphabet), 144A-obligationer och skuld i annan valuta. Likviden kommer på likviddagen, inte
  prisdagen.

### Jämförelse med marknaden

Kontrollerat 2026-11-25 i FRED:s serienoter (`fred.stlouisfed.org/series/<id>`, bara licenstexten lästes):
- **ICE BofA** (BAMLC0A0CM, BAMLC4A0C710Y, BAMLC0A4CBBB): "Reproduction of this data in any form is prohibited except
  with the prior written permission of ICE Data Indices", och nyckeltalen ges "for your internal use only". Från april
  2026 visar FRED bara tre år.
- **Moody's** (AAA, BAA): "MOODY'S INFORMATION MAY NOT BE COPIED OR OTHERWISE REPRODUCED, REPACKAGED, FURTHER
  TRANSMITTED, ... BY ANY PERSON WITHOUT MOODY'S PRIOR WRITTEN CONSENT."
- Båda förbjuder vidarespridning (klass `nej`), och en kopia från FRED är `okänd` enligt projektets regel
  ([licensniva.md](../datakallor/licensniva.md)). **Inget marknadsindex läggs till.** Statsräntans nivå behövs inte
  för den angivna spreaden och läggs inte heller till. Behövs den senare: Federal Reserve H.15 eller treasury.gov
  (public domain).

### Självkontroll

`python -m ai_tracker.credit_issuance_check` hämtar om källdokumentet för varje rad (utan cache, alla rader som
standard, eftersom dokumenten är få) och kontrollerar:
- att blocket på platsen har lagrad SHA-256 (annars söks dokumentet igenom, "moved");
- att varje tal i raden står i blocket, i kolumnen när den anges;
- att parsern ger samma värden ur blocket (rader med `method` = `parser`);
- att `filed` och `accepted` stämmer med EDGAR:s submissions;
- att avkastningen stämmer med referensens avkastning plus spreaden, inom 1 bp, när alla tre står.

Kontrollen bekräftar plats, tal och datum, inte semantiken (vilket dokument som är källan, valuta och referens). Det
är för den oberoende granskningen.

### Beslutsregler

- **Publicering:** `publish=True` först efter en oberoende extraktionsgranskning (minst 30 % av raderna och minst ett
  dokument per emittent) utan fel i talen, och med en daterad registerpost.
- **Kärnserie:** inte i den här körningen. Ett förslag kräver godkänd granskning, minst 12 kvartal med värden i
  `spread_issue_ai_7_12y_q` och en registrerad regel för emittentmixen.
- **Ingen takt** räknas i spåret.

### Tester (syntetiska villkorsbilagor, inget nät)

Parsern (en tranche per tabell och flera tranchar som kolumner), belopp i dollar och miljarder, spread som "T+45",
"+45 bps" och "+0.45%", löptid, bandets gränser (6,49 utanför, 6,5 innanför, 12,49 innanför, 12,5 utanför),
vägningen, luckregeln, rörlig ränta och euro (med i volymen respektive utanför, utanför spreaden), dateringen (sen
inlämning ger en ny version, ett kvartal som inte är slut ger inget värde), CSV-kontrollen och självkontrollen med
falska dokument.
