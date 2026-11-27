# Källa: labbens egna intäktsuppgifter (steg 2, spår B6)

Byggt och kontrollerat 2026-11-23. Det här är bara ett register. Inga takter, inga tillväxttal och inga jämförelser
görs här. Ledtråd L3. Granskas i R4 (datum och läckage) och R5 (extraktion).

> **Pausad hämtning från Anthropics sajter.** `www.anthropic.com` och `claude.com` hämtades en gång 2026-11-23, med
> ärlig User-Agent och 0,5 s mellan anrop, och robots.txt tillåter det. Samma dag pausade orkestreraren B5:s
> insamling från Anthropic i väntan på Johannes beslut om villkoren (beslutslogg 2026-11-23). Konsumentvillkoren
> omfattar "websites" och förbjuder automatisk åtkomst "except … where we otherwise explicitly permit it". Samma
> fråga gäller här. Hämtning från de värdarna (`PAUSED_HOSTS`) kräver därför uttryckligt `--allow-paused`.
> Registret och serierna behöver inget nät, eftersom `fetch()` bara läser CSV:n. SEC-delen påverkas inte.
> **Beslut för Johannes:** samma beslut som för B5. Jag rekommenderar att tillåta enstaka hämtning av de citerade
> inläggen för verifiering, som R5 behöver (8 sidor), men ingen löpande genomsökning.

Kod: `src/ai_tracker/sources/lab_revenue.py` (hämtning, tolkning, inläsare, verifiering) och
`src/ai_tracker/series/lab_revenue.py` (katalogposter). Data: `curated/lab_revenue.csv` (committad, bara siffror
och referenser). Tester: `tests/test_lab_revenue.py` (syntetiska fixturer, inget nät).

- Kandidatmeningar: `python -m ai_tracker.sources.lab_revenue --allow-paused` (se pausen ovan). Läser sajtkartan, hämtar alla inlägg i
  nyhetsrummet och listar meningar som nämner intäkter och ett dollarbelopp.
- Kontroll av alla rader: `python -m ai_tracker.sources.lab_revenue verify --allow-paused`. Hämtar om varje dokument och
  kontrollerar SHA-256 för meningen på angiven plats, att talet står i meningen och att `known_from` är lika med
  dokumentets datum. Skriver meningarna till `data/raw/lab_revenue_sentences/` (gitignorerad).
- Laddning: `python -m ai_tracker.observations lab_rev_anthropic_company_run_rate lab_rev_anthropic_company_run_rate_s1 lab_rev_anthropic_claude_code_run_rate`.

## Vad som räknas

**Bara förstapartsuppgifter:** bolagets egna blogg- och nyhetsinlägg, officiella inlämningar (SEC) och uttalanden
av VD eller CFO i bolagets egna kanaler. Andrahandsuppgifter tas aldrig med, till exempel pressartiklar med
"källor nära bolaget" eller intervjuer i andras medier.

Alla serier har etiketten **"(rapporterad)"**. Siffrorna är bolagens egna och inte reviderade. Bolaget säger själv
i S-1 att Run-Rate Revenue "have not been independently verified by third parties". Ofta är siffran en gräns
("over $5 billion"). De blandas aldrig med redovisade intäkter (GAAP).

## Nåbarhet (2026-11-23)

| Värd | Status |
|---|---|
| `www.anthropic.com` (nyhetsrum, sajtkarta) | nåbar, robots.txt `Allow: /` |
| `claude.com` (produktsajt) | nåbar. 308 artiklar genomsökta, inga intäktsuppgifter om bolaget, bara kunders ARR |
| `www.sec.gov`, `data.sec.gov` | nåbara med `SEC_USER_AGENT` |
| `openai.com`, `www.openai.com`, `cdn.openai.com`, `help.openai.com` | **BLOCKED** (proxyn nekar, 403) |
| `x.ai`, `www.x.ai`, `docs.x.ai` | **BLOCKED** |
| `mistral.ai`, `www.mistral.ai`, `docs.mistral.ai` | **BLOCKED** |
| `cohere.com`, `www.cohere.com` | **BLOCKED** |
| `blog.samaltman.com`, `x.com`, `twitter.com`, `youtube.com`, `linkedin.com` (VD:ars egna kanaler) | **BLOCKED** |
| `web.archive.org`, `archive.ph` (äldre versioner av sidor) | **BLOCKED** |
| `efts.sec.gov` (EDGAR fulltextsök) | **BLOCKED**. Företagssök via `www.sec.gov/cgi-bin/browse-edgar` används i stället |

Inga försök har gjorts att ta sig runt spärrarna. OpenAI, xAI, Mistral och Cohere har därför inga serier. Ramverket
tar emot dem (`LABS` i koden) så fort värdarna öppnas: lägg till sajtkartan i `SITEMAPS`, kör kandidatlistan och
lägg till rader.

## SEC

- **Anthropic, PBC** (CIK 2130357, ticker ANT). Inlämningar: S-1 2026-10-26, S-1/A 2026-11-02, 2026-11-10 och
  2026-11-17, samt 424B4 2026-11-19 (prissatt börsnotering). Bolaget definierar **Run-Rate Revenue** som
  konsumtionsavgifter under de 28 dagar som slutar på mätdagen × 13 plus månatliga abonnemangsavgifter på mätdagen
  × 12. Första S-1 lämnade värdet tomt. Värdet (cirka 81 mdr USD per 2026-10-31) står först i S-1/A från
  2026-11-10 och upprepas oförändrat i S-1/A 2026-11-17 och i 424B4.
- **DRS och DRS/A** (sex utkast 2026-06-01 till 2026-10-09) **används aldrig.** EDGAR daterar dem efter den
  konfidentiella inlämningen, men de blev offentliga först senare. Datumet skulle läcka. Inläsaren vägrar
  `doc_type` DRS och DRS/A. Utkasten har dessutom tomma värden ("$ as of .").
- **GAAP-intäkter** i S-1 (kvartal och helår) är redovisning, inte självrapportering, och tas inte med här. De finns
  sedan spår AN1 (2026-11-27) som egna serier `lab_gaap_anthropic_*` ur S-1, S-1/A och 424B4
  (`docs/kallor/anthropic_gaap.md`), skilda från run-rate-serierna här. Companyfacts har ännu inga us-gaap-fakta för
  CIK 2130357. De periodiska rapporterna (första 10-K för 2026) förlänger serierna först efter ett daterat tillägg.
- **xAI:** X.AI Corp. (CIK 2002695, fyra Form D 2023–2025) och X.AI Holdings Corp. (CIK 2079267, två Form D
  2025–2026). Fältet `revenueRange` är "Decline to Disclose" i alla. Ingen intäktsuppgift.
- **OpenAI:** ingen inlämning från OpenAI självt hittades under OpenAI-namn, bara tredjeparts-SPV:er
  ("OpenAI … a Series of …"). Sådana räknas inte.
- **Mistral, Cohere:** ingen emittent hittades. Träffarna var orelaterade bolag och SPV:er.

## Serier

| Nyckel | Mått | Omfång | Punkter | Källa |
|---|---|---|---|---|
| `lab_rev_anthropic_company_run_rate` | RUN_RATE | hela bolaget | 9 (2024-01-01 – 2026-05-28) | nyhetsrummet |
| `lab_rev_anthropic_company_run_rate_s1` | RUN_RATE_S1 | hela bolaget | 1 (2026-10-31) | S-1/A |
| `lab_rev_anthropic_claude_code_run_rate` | RUN_RATE | Claude Code | 3 (2025-09-02 – 2026-02-12) | nyhetsrummet |

Gren G4, enhet MUSD, frekvens D, `publish=False` tills R5 är klar, `max_age_days=400` (oregelbundna uttalanden).

**Varför två mått för samma bolag.** Inläggen i nyhetsrummet säger "run-rate revenue" men anger inte hur måttet
räknas. S-1 definierar det. Det är troligen samma interna mått, men det går inte att verifiera för de äldre
inläggen. Därför hålls de som skilda serier (RUN_RATE och RUN_RATE_S1). Inläsaren vägrar RUN_RATE_S1 från
nyhetsrummet. Måttkoderna ARR och REVENUE_CY (kalenderår, frekvens A) finns i schemat för andra labb men används
inte än.

## known_from och period

- **known_from** = inläggets `datePublished` (schema.org). Det är samma datum som syns på sidan (`<time>`). För
  SEC-dokument är det EDGAR:s `Filing Date` från inlämningens indexsida. Båda kontrolleras av `verify`.
- **period = period_end** = datumet siffran avser, med de här konventionerna:
  - "Today" eller "now" = publiceringsdagen.
  - "In November" eller "By August 2025" = sista dagen i månaden.
  - "At the beginning/start of 2025" = 2025-01-01.
  - "Earlier this month" = publiceringsdagen (senast möjliga).
  - "At the end of 2025" = 2025-12-31.
  - Ett S-1-värde "as of October 31, 2026" = det datumet.

  Inläsaren vägrar period efter publiceringen.
- **Vintages.** En siffra som upprepas oförändrad för samma datum i ett senare inlägg ger ingen ny rad (ant-04).
  En ändrad siffra för samma datum skulle bli en ny vintage. Ett värde för ett tidigare datum som nämns först
  senare får sitt senare `known_from`. Till exempel "approximately $9 billion at the end of 2025" sades först
  2026-04-06.
- **Läckagerisk (för R4).** Alla citerade inlägg har `article:modified_time` långt efter publiceringen:
  2026-09-28 för sju inlägg och 2026-10-14 för Ciauri-inlägget. I hela nyhetsrummet (282 inlägg) finns bara 26
  olika ändringsdatum, i klungor (74 inlägg 2026-10-14, 57 inlägg 2026-09-28, 34 inlägg 2026-11-13). Det ser ut som
  ändringar av hela sajten och inte av enskilda texter. Men det går inte att visa att meningen är oförändrad sedan
  publiceringen, eftersom Wayback är blockerad. Det som talar för att texten inte har ändrats: varje mening avser
  en tidpunkt före eller på publiceringsdagen, och samma siffror återkommer oförändrade i senare inlägg (5 mdr per
  augusti 2025 i inlägg från 2025-09-02 och 2025-09-26, över 30 mdr i inlägg från 2026-04-06 och 2026-04-20).
  `modified` sparas per rad.

## Förbehåll (`qualifier`)

| Kod | Betyder |
|---|---|
| `as_stated` | inget förbehåll |
| `approx` | approximately, about, ~ |
| `over` | over, more than, surpassed, crossed, alltså en nedre gräns |
| `nearly` | nearly, almost |

Värdet lagras som det uttalades. En nedre gräns behålls som gräns.

## Uteslutet, med skäl

- **Tillväxtfaktorer utan nivå**, till exempel "EMEA … grown more than 9x", "Asia-Pacific … over 10x", "India …
  doubled", "Claude Code … recurring revenue grow over 5x" och "growing over 10x annually". De ger ingen nivå, och
  att räkna fram en nivå vore härledning.
- **Kundmått**, till exempel antal kunder med mer än 100 000 eller 1 miljon USD i run-rate, och antal
  företagskunder. Det är inte intäkter.
- **Kunders ARR** (Lovable, Genspark, Emergent och andra på claude.com och anthropic.com). Det är inte labbets
  intäkt.
- **Härlett värde:** S-1/A:s "up $10 billion from September 30, 2026" ger implicit cirka 71 mdr USD per 2026-09-30.
  Det står inte uttryckligen och registreras inte.
- **GAAP-intäkter i S-1 och FWP** (kvartalsintäkter 2025–2026). De är redovisade siffror och hör inte till de här
  serierna. Prospektens tal finns i `lab_gaap_anthropic_*` (spår AN1, `docs/kallor/anthropic_gaap.md`).
- **Andrahandsuppgifter:** OpenAI:s, xAI:s, Mistrals och Coheres intäktssiffror som cirkulerar i pressen (The
  Information, Reuters, Bloomberg, CNBC och andra), och VD:ars uttalanden i intervjuer i andras medier eller
  poddar. De kommer inte från bolagens egna kanaler, och bolagens egna kanaler (openai.com, x.ai, x.com och
  andra) är blockerade. Pressvärdarna är också blockerade, så de enskilda siffrorna har inte kunnat listas eller
  kontrolleras här.

## Stickprov

- **Automatiskt, alla 14 rader:** `verify` gav 0 avvikelser 2026-11-23. Hash, tal och datum stämmer mot
  dokumenten.
- **Manuellt, 20 %:** 3 av 14 rader (21 %), slumpade med seed 6. Det som granskades var tolkningen av period,
  förbehåll och omfång, som `verify` inte täcker.
  - ant-cc-02: "In November … reached $1 billion" ger 2025-11-30, as_stated, Claude Code. Rätt.
  - ant-10: "crossed $47 billion earlier this month" ger 2026-05-28, over, hela bolaget. Rätt.
  - ant-02: "At the beginning of 2025 … approximately $1 billion" ger 2025-01-01, approx. Rätt.

  0 fel.

## Licens

- **anthropic.com:** det finns inga särskilda webbvillkor. Konsumentvillkoren omfattar "websites", se pausen
  överst. Bara siffror med
  källhänvisning lagras och publiceras, aldrig text. Licensen är inte kontrollerad för publicering, så
  `publish=False`.
- **SEC EDGAR:** public information (sec.gov/privacy).
