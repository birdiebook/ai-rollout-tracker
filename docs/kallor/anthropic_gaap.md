# Källor: Anthropics redovisade tal (AN1)

Anthropics redovisade (GAAP) intäkter och närliggande resultatposter ur registreringsprospektet, som katalogserier.
Regler: `docs/mattregister.md`, posten "2026-11-27 – AN1" (låst och committad ensam före extraktionen) och tillägget
"2026-11-27 – AN1, tillägg efter extraktionen". Användning: BG1:s avsnitt 5 (`docs/resultat/betalningsgapet.md`).

Alla 19 serier har `publish=False` och klassen `ja` för kommersiell användning (SEC: public information,
sec.gov/privacy, egen extraktion ur dokument på sec.gov). Ingen är kärnserie, inget grenindex och inget tillstånd
berörs. Från prospekten committas bara siffror med källhänvisning, aldrig texten.

## Korpus

Anthropic, PBC (CIK 2130357), huvuddokumentet i varje inlämning:

| Form | Inlämnad | Accession | Kvartal i kvartalstabellen | Hittills i år |
|---|---|---|---|---|
| S-1 | 2026-10-26 | 0001628280-26-067168 | 2025Q1–2026Q2 | sex månader 2025 och 2026 |
| S-1/A | 2026-11-02 | 0001628280-26-068676 | 2025Q1–2026Q3 | nio månader 2025 och 2026 |
| S-1/A | 2026-11-10 | 0001628280-26-072484 | 2025Q1–2026Q3 | nio månader |
| S-1/A | 2026-11-17 | 0001628280-26-074338 | 2025Q1–2026Q3 | nio månader |
| 424B4 | 2026-11-19 | 0001628280-26-074944 | 2025Q1–2026Q3 | nio månader |

Alla har helåren 2023, 2024 och 2025. DRS och DRS/A (sex utkast 2026-06-01 till 2026-10-09) används aldrig: EDGAR
daterar dem efter den konfidentiella inlämningen. FWP och 8-K 2026-11-25 ingår inte. Prospekten har XBRL bara för
försättsbladet (R1–R3), och companyfacts har inga us-gaap-fakta, så HTML-tabellerna tolkas.

## Serierna

| Serie | Tabell | Frekvens | Perioder | Första known_from |
|---|---|---|---|---|
| `lab_gaap_anthropic_revenue_q` | Quarterly Consolidated Statements of Operations (MD&A, ogranskad) | kvartal | 2025Q1–2026Q3 | 2026-10-26 (2026Q3: 2026-11-02) |
| `lab_gaap_anthropic_compute_q` | samma | kvartal | 2025Q1–2026Q3 | samma |
| `lab_gaap_anthropic_opinc_q` | samma | kvartal | 2025Q1–2026Q3 | samma |
| `lab_gaap_anthropic_<post>_a` | Consolidated Statements of Operations, noten Supplemental Operating Expense Information, Consolidated Statements of Cash Flows | år | 2023–2025 | 2026-10-26 (förskotten 2026-11-02) |
| `lab_gaap_anthropic_<post>_ytd` | samma | hittills i år, period = kvartalet då perioden slutar | 2025Q2, 2025Q3, 2026Q2, 2026Q3 | 2026-10-26 (Q2), 2026-11-02 (Q3) |

`<post>` är `revenue` (intäkter), `compute` (compute och infrastruktur, kostnad efter slag), `opinc`
(rörelseresultat, med tecken), `cost_of_revenue` (kostnad för intäkter ur noten om kostnader efter funktion),
`gross_profit` (härlett: intäkter minus kostnad för intäkter, samma dokument och kolumn), `cfo` (kassaflöde från den
löpande verksamheten, med tecken), `capex` (Purchases of property and equipment, positivt utflöde) och
`prepay_leased` (Prepayments for leased assets and equipment, positivt utflöde, från S-1/A 2026-11-02). Allt i MUSD.

Att tänka på när talen läses:
- **Compute och infrastruktur är inte kostnad för intäkter.** Bolaget bytte till kostnader efter slag. Compute omfattar
  all compute, även träning och forskning. Kostnaden för intäkter i noten är bara compute för kundernas arbetslaster
  och viss personal och overhead (träning ligger i Research and development). Bruttoresultatet blir därför högt
  (9 månader 2026: 28,4 mdr på 33,2 mdr i intäkter), medan compute är 18,8 mdr.
- **Rörelseresultatet** innehåller förlikningen i Bartz-målet (1,5 mdr, 2025Q3). Nettoresultatet tas inte med: det
  domineras av värdeförändringar på konvertibler, derivat och SAFE.
- **Förskotten** för leasade tillgångar och utrustning är större än capex (9 månader 2026: 1 955 mot 925 MUSD) och
  läggs inte ihop med den.
- **Run-rate är ett annat mått** (`lab_rev_anthropic_*`, `docs/kallor/labbintakter.md`). Serierna blandas aldrig.

## Tolkningen (deterministisk)

`python -m ai_tracker.sources.anthropic_gaap build` hämtar korpusen (cache delad med KL1, arkivdokument ändras inte)
och tolkar varje dokument:
- Tabellen hittas på sin rubrikrad, som står exakt en gång per dokument. Kvartalstabellens perioder står på raden
  "(in millions) | March 31, 2025 | …" under "Three Months Ended". F-sidornas och sammanfattningens perioder står på två
  rader: grupperna "Year Ended December 31, | Six/Nine Months Ended June 30/September 30," och årtalen. Den andra
  gruppen börjar där årtalen slutar stiga.
- Raden hittas på sin etikett (exakt text, en fotnotsmarkör "(1)" ignoreras). Cellen läses utan bedömning: "$" och
  tusentalskomma bort, parentes negativt, "—" noll. Saknas tabell, kolumn eller rad, eller blir antalet celler fel,
  stoppar bygget. Enda undantaget är förskotten i S-1, som saknas där och är listade för hand (`ABSENT`).
- Varje värde i varje dokument är en rad i `curated/anthropic_gaap.csv` (297 rader): accession, form, inlämningsdatum,
  URL, tabell, sidnummer, plats (`lines #a,#b,#k col #j` i KR1:s radlista: rubrikraderna, raden och kolumnen) och
  SHA-256 för de raderna. Citatet, raderna ordagrant, ligger i `data/raw/anthropic_gaap_quotes/quotes.json`
  (gitignored). Sammanfattningstabellens intäkter finns med som kontroll men matar ingen serie.
- Versionerna (`versions`): första dokumentet som anger värdet ger `known_from` = dess inlämningsdatum, och ett senare
  dokument ger en ny version bara om värdet ändras. Inget värde skiljer sig mellan de fem dokumenten.

## Kontroller (registerposten, (e))

1. **Självkontroll** (`python -m ai_tracker.anthropic_gaap_check`): alla 297 rader mot nyhämtade kopior (utan cache).
   Citatet på platsen har sin SHA-256, cellen har värdet, och inlämningsdatum och accept-tid stämmer mot EDGAR:s
   submissions. Utfall 2026-11-27: 297 av 297 rätt.
2. **Summakontroller** (`python -m ai_tracker.sources.anthropic_gaap sums`): per dokument Q1–Q4 2025 mot helåret,
   Q1 + Q2 mot sex månader och Q1 + Q2 + Q3 mot nio månader, för intäkter, compute och rörelseresultat, och
   sammanfattningstabellens intäkter mot F-sidornas. Utfall: 70 av 70 kontroller med skillnad 0.
3. **Stickprov för hand** (17 värden, minst 10 enligt posten). Dokumenten hämtades på nytt med en enkel klient (ingen
   cache), tabellerna lästes med en annan tolkning (BeautifulSoup, rad för rad), och agenten jämförde raderna med
   CSV:n. Tolv rader drogs slumpmässigt (frö 20261127) och fem lades till för de viktigaste talen.

| Dokument | Tabell | Post, period | CSV | Läst i källan | Utfall |
|---|---|---|---|---|---|
| S-1/A 2026-11-17 | kvartal | compute 2025Q3 | 2 047 | 2,047 | rätt |
| S-1/A 2026-11-17 | kvartal | compute 2025Q1 | 944 | 944 | rätt |
| S-1/A 2026-11-17 | kvartal | intäkter 2026Q3 | 16 956 | $ 16,956 | rätt |
| S-1 2026-10-26 | resultaträkning | rörelseresultat 2023 | −551 | (551) | rätt |
| S-1 2026-10-26 | resultaträkning | intäkter sex månader 2025 | 1 163 | $ 1,163 | rätt |
| S-1 2026-10-26 | kvartal | intäkter 2026Q2 | 11 555 | $ 11,555 | rätt |
| S-1 2026-10-26 | kvartal | rörelseresultat 2026Q2 | 974 | 974 | rätt |
| S-1 2026-10-26 | kassaflöde | capex 2023 | 2 | (2) | rätt |
| S-1 2026-10-26 | kassaflöde | kassaflöde från rörelsen sex månader 2026 | 3 929 | 3,929 | rätt |
| S-1/A 2026-11-02 | resultaträkning | intäkter 2025 | 4 585 | $ 4,585 | rätt |
| S-1/A 2026-11-02 | kvartal | intäkter 2026Q3 | 16 956 | $ 16,956 | rätt |
| S-1/A 2026-11-10 | kassaflöde | capex 2023 | 2 | (2) | rätt |
| 424B4 2026-11-19 | kassaflöde | capex nio månader 2025 | 111 | (111) | rätt |
| 424B4 2026-11-19 | kassaflöde | kassaflöde från rörelsen nio månader 2026 | 6 569 | 6,569 | rätt |
| S-1/A 2026-11-17 | not, funktion | kostnad för intäkter nio månader 2026 | 4 812 | $ 4,812 | rätt |
| S-1/A 2026-11-17 | kassaflöde | förskott 2025 | 54 | (54) | rätt |
| S-1/A 2026-11-17 | resultaträkning | rörelseresultat nio månader 2025 | −5 224 | (5,224) | rätt |

Kontrollerna bekräftar plats, citat, tal och datum. Att raden är rätt post och kolumnen rätt period bekräftas av
stickprovet och summakontrollerna, inte av självkontrollen. Ingen oberoende granskning är gjord: serierna är
katalogserier och används bara som beskrivning i BG1.

## Kommandon

    python -m ai_tracker.sources.anthropic_gaap build        # tolka korpusen -> curated/anthropic_gaap.csv och citaten
    python -m ai_tracker.sources.anthropic_gaap sums         # summakontrollerna
    python -m ai_tracker.anthropic_gaap_check                # självkontrollen mot nyhämtade kopior
    python -m ai_tracker.observations lab_gaap_anthropic_revenue_q …   # serierna till observationstabellen

## Vad som inte kan sägas

- Kvartalstabellen är ogranskad, och en del kolumner på F-sidorna är märkta "(unaudited)". Vilka kolumner markeringen
  gäller läses inte av tolkningen.
- Sju kvartal och tre år är en kort historik med ett bolag i mycket snabb tillväxt. Takter över fyra kvartal finns
  först med 2026Q4.
- De periodiska rapporterna (första 10-K för 2026) kan revidera talen. De förlänger serierna först efter ett daterat
  tillägg till registerposten.
