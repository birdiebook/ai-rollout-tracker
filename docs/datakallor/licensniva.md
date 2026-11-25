# Licensnivå: kommersiell användning per serie

Spår K2, körning 13, 2026-11-24. Beslutspunkt 3 i [riktning.md](../riktning.md): sidan förblir icke-kommersiell, men
varje serie får en klass för kommersiell användning, så att en kommersiellt ren delmängd alltid går att räkna fram.
Nya spår väljer öppna licenser (public domain, CC0, CC BY, MIT) när det finns ett val.

Kod: `src/ai_tracker/licenses.py`. Rapport: `PYTHONPATH=src python -m ai_tracker.licenses report [--markdown]`.
Tabellerna nedan är genererade med `--markdown` på katalogen efter integrationen av körning 14, 2026-11-25 (805
serier). Kör om rapporten när serier läggs till.

## Klasserna

| Klass | Betyder |
|---|---|
| `ja` | Den dokumenterade licensen eller villkoren tillåter kommersiell användning och vidarespridning: public domain (amerikanska myndigheter, Fed, EIA), CC0, CC BY 4.0, MIT, SEC:s offentliga information och siffror som vi själva har extraherat ur dokument på sec.gov (10-K, 10-Q, 8-K, 6-K, S-1) |
| `nej` | De dokumenterade villkoren förbjuder det: CC BY-NC, och PJM:s förbud mot vidarepublicering för icke-medlemmar |
| `okänd` | Ingen licens hittades, villkoren gick inte att läsa eller är inte bedömda, så som dokumenten säger. Klassen gissas aldrig |

- **Den kommersiellt rena delmängden är bara `ja`.** `okänd` räknas inte som `ja`.
- **`publish` och klassen är oberoende.** `publish` styr vad den icke-kommersiella sidan visar. `publish=True` med
  `nej` är tillåtet, t.ex. Cloudflare Radar (CC BY-NC). `publish=False` med `ja` är också tillåtet, t.ex.
  standardfelen för Census BTOS (`btos_ai_*_se`). Capex-guidancen var ett exempel tills ägarbeslutet 2026-11-25.
- **Varje serie måste ha en klass.** `catalog.validate()` ger fel för en licenstext som ingen regel eller override
  klassar. En ny serie kan alltså inte läggas till utan klass.

## Hur klassen bestäms

I tur och ordning, och det första som gäller avgör:

1. **Override per serienyckel** (`KEY_OVERRIDES`), med skäl. Den är slutlig. I dag gäller den Arenas två
   prisserier (R10-2) och Q1:s tre Arena-serier (`g2_price_rolling12_arena`, `g2_price_rolling6_arena` och
   `g2_price_frontier_arena`).
2. **Override per källa** (`SOURCE_OVERRIDES`, regex på `Spec.source`), där licenstexten ensam säger för mycket:
   kopior från FRED eller ALFRED, och LMArenas Space-filer.
3. **Kurerade filer.** En serie vars källa nämner `curated/<fil>.csv` får den kurerade regeln på de rader den läser:
   `ja` när alla raderna har `source_url` på sec.gov, annars `okänd`. Raderna är seriens egna där filen har en
   koppling från rad till serie (`ROW_SERIES`: `ai_kpis.csv` och `lab_revenue.csv`). Annars är det bolagets rader för
   en kurerad extraktion (`Kurerad extraktion (curated/<fil>.csv)`), där bolaget är den del av nyckeln som är ett bolag
   i filen. Annars är det raderna som `CURATED_READS` anger, för serier som läser filen utan att vara en extraktion
   (F1). En serie som nämner en kurerad fil utan något av detta blir `okänd`, och `catalog.validate()` ger fel (R10-1).
   Bara identifierande kolumner och `source_url` läses, aldrig värden.
4. **Regler på licenstexten** (`RULES`), i ordning, och första träff avgör. En text som börjar med `derived:` klassas
   del för del, och den mest restriktiva delen avgör. Restriktiva och obedömda regler ligger före de tillåtande, så
   att GH Archive ("CC-BY-4.0" för webbplatsen men "Not checked for publication") blir `okänd`. Ord som begränsar
   användningen ("non-commercial", "all rights reserved", "prohibited", "may be under copyright", "not verified")
   ger `okänd`, och MIT räknas bara som licens, inte som namn (R10-3). En kurerad serie tar den mest restriktiva av
   den kurerade regeln och licenstexten (R10-5).
5. **Härledda serier** (`Spec.components`, avstämningarna i A5 och summorna `*_hyp4` med bolagen i etiketten) tar den
   mest restriktiva klassen av sin egen licens och komponenternas: `ja` bara om alla är `ja`, och `nej` före `okänd`.
   Kvoten `capex_ocf_hyp4` i tillståndsmotorn (`register.DERIVED`) får täljarens och nämnarens klass.

### Regler i ordning

| # | Typ | Regel | Klass | Skäl |
|---|---|---|---|---|
| 1 | nyckel | g2_price_at_arena_capability | okänd | tavlorna kommer från LMArenas Space-filer (arena.subset_boards("text")): datasetet är CC BY 4.0, men Space-filerna (belägg och kompletta tabeller) har ingen dokumenterad licens, och Arenas webbvillkor kunde inte läsas |
| 2 | nyckel | g2_price_at_arena_capability_4o | okänd | tavlorna kommer från LMArenas Space-filer (arena.subset_boards("text")): datasetet är CC BY 4.0, men Space-filerna (belägg och kompletta tabeller) har ingen dokumenterad licens, och Arenas webbvillkor kunde inte läsas |
| 3 | nyckel | g2_price_rolling12_arena | okänd | tavlorna kommer från LMArenas Space-filer (arena.subset_boards("text")): datasetet är CC BY 4.0, men Space-filerna (belägg och kompletta tabeller) har ingen dokumenterad licens, och Arenas webbvillkor kunde inte läsas |
| 4 | nyckel | g2_price_rolling6_arena | okänd | tavlorna kommer från LMArenas Space-filer (arena.subset_boards("text")): datasetet är CC BY 4.0, men Space-filerna (belägg och kompletta tabeller) har ingen dokumenterad licens, och Arenas webbvillkor kunde inte läsas |
| 5 | nyckel | g2_price_frontier_arena | okänd | tavlorna kommer från LMArenas Space-filer (arena.subset_boards("text")): datasetet är CC BY 4.0, men Space-filerna (belägg och kompletta tabeller) har ingen dokumenterad licens, och Arenas webbvillkor kunde inte läsas |
| 6 | källa | alfred: /\b(?:AL)?FRED\b\|(?i:stlouisfed\.org)/ | okänd | kopian kommer från FRED eller ALFRED, vars villkor förbjuder användning i samband med maskininlärning; kommersiell användning är inte bedömd (primärkällan vore ja) |
| 7 | källa | arena-space: /LMArena \(HF-dataset \+ Space-filer\)/ | okänd | datasetet är CC BY 4.0, men Space-filerna (belägg och kompletta tabeller) har ingen dokumenterad licens, och Arenas webbvillkor kunde inte läsas |
| 8 | källa | curated: källan nämner curated/<fil>.csv | ja / okänd | raderna som serien läser: seriens egna (ROW_SERIES: ai_kpis.csv, lab_revenue.csv, orders_backlog.csv), annars bolagets (Kurerad extraktion (curated/<fil>.csv)), annars de som anges i CURATED_READS (13 serier). ja: egen extraktion ur dokument på sec.gov (alla raderna har source_url på sec.gov); okänd: egen extraktion, men ur bolagets egna sidor utan dokumenterade villkor; inga angivna rader: okänd, och validate ger fel. Den mest restriktiva av detta och licensreglerna avgör |
| 9 | licens | derived-licence: /^derived: a + b/ | mest restriktiva delen | varje del klassas med reglerna nedan |
| 10 | licens | unverified: /\bunverified\b/ | okänd | licensen är inte verifierad: villkoren saknas eller kunde inte läsas |
| 11 | licens | cc-by-nc: /\bCC[ -]?BY-NC\b/ | nej | CC BY-NC: kommersiell användning är inte tillåten |
| 12 | licens | pjm-republish: /non-?members are specifically prohibited from republishing/ | nej | PJM:s villkor: icke-medlemmar får inte vidarepublicera data |
| 13 | licens | no-open-licence: /no open licen[cs]e\|no (?:data )?licen[cs]e stated\|redistribution not checked\|not checked for publication\|ej kontrollerad för publicering/ | okänd | ingen öppen licens, eller vidarespridning inte kontrollerad |
| 14 | licens | restrictive-wording: /non-?commercial\|all rights reserved\|proprietary\|third[- ]party rights\|may be (?:under\|subject to) copyright\|not in the public domain\|not verified\|personal use only\|prohibit\|not (?:permitted\|allowed)\|does not (?:apply\|cover)\|\bunclear\b/ | okänd | texten begränsar eller reserverar användningen (icke-kommersiell, förbud, upphovsrätt, tredje parts rättigheter, oklar eller inte verifierad status); kommersiell användning är inte bedömd |
| 15 | licens | cc0: /\bCC0\b/ | ja | CC0: fri användning, även kommersiell |
| 16 | licens | cc-by: /\bCC[ -]BY[ -]4\.0\b\|Creative Commons Attribution 4\.0/ | ja | CC BY 4.0: kommersiell användning tillåten med källhänvisning |
| 17 | licens | mit: /(?<![\w-])MIT(?=[ -]?\(?(?i:licen[cs]e)\|[,)])\|(?i:licen[cs]e)\s*:\s*MIT\b/ | ja | MIT: kommersiell användning tillåten med licenstexten |
| 18 | licens | public-domain: /17 U\.S\.C\. § ?105\|\bpublic domain\b/ | ja | public domain (amerikansk myndighet): fri användning med källhänvisning |
| 19 | licens | sec: /sec\.gov/privacy/ | ja | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument |
| 20 | härledning | Spec.components och medlemmarna i *_hyp4 | mest restriktiva | egen klass och komponenternas; ja bara om alla är ja, nej före okänd |

## Bedömningar att känna till

- **SEC och egna extraktioner är `ja`.** sec.gov/privacy: "Information presented on sec.gov is considered public
  information and may be copied or further distributed by users of the web site without the SEC's permission"
  ([kallor/sec.md](../kallor/sec.md)). Det gäller också TSMC:s, ASML:s och Nebius 6-K. TSMC:s IR-villkor gick inte att
  läsa (403), men siffrorna kommer ur den lagstadgade inlämningen på sec.gov, inte från IR-sidan.
- **Microsoft är `okänd` i de kurerade filerna när raderna kommer från microsoft.com** (44 serier: 31 AI-nyckeltal,
  6 capex-guidance, 7 planer). Raderna kommer från resultatsamtalen på microsoft.com, och villkoren för microsoft.com
  är inte dokumenterade. I `ai_kpis.csv` gäller regeln seriens egna rader (R10-6), så de sju Microsoft-nyckeltal som
  bara har rader på sec.gov är `ja`: `kpi_msft_azure_growth_v1`–`v3`, `_cc_v1`–`_cc_v3` och
  `kpi_msft_azure_ai_pts_v2`. I `guidance_capex.csv` och `plans.csv` finns ingen koppling från rad till serie, så där
  gäller bolaget. Alla Microsofts rader där kommer från microsoft.com, så resultatet blir detsamma. Övriga bolag i
  filerna har bara sec.gov-rader och är `ja`.
- **F1:s poolade revideringsindex är `okänd`** (`f1_rev_index_*`, `f1_rev_n_*`, `f1_rev_median_*`).
  De räknar alla rader i `guidance_capex.csv`, också Microsofts från microsoft.com. Det står i `CURATED_READS`, och
  likaså att överraskningen för Meta och Alphabet bara läser bolagens egna rader (`ja`), och att TSMC:s och Nvidias
  inte läser filen alls (R10-1). Det gäller också känsligheten i US$ (`f1_surprise_tsmc_usd`, X8), som läser TSMC:s
  6-K och är `ja`. Efter X8 hade de tio F1-serier som läser filen alla `guid_capex_*` som komponenter (R11-4), och
  därför blev också överraskningarna för Meta och Alphabet `okänd`, via Microsofts rader. **Ägarbeslut 2026-11-25:**
  Metas och Alphabets överraskningar listar nu bara bolagets egna `guid_capex_*` (`guidance_revisions.CSV_READS`,
  bevisat med ett test som ändrar de andra bolagens rader), så de är `ja` och publiceras. Revideringsserierna listar
  fortfarande alla bolags serier och är `okänd`. Överraskningsindexet och dess antal listar från granskningen R25 bara
  Metas och Alphabets serier, som i `CURATED_READS`, och är `ja`. De har `publish=False` tills ägaren beslutar
  (`Spec.withheld_reason`). `guid_capex_*` för Alphabet, Amazon och
  Meta publiceras, eftersom klassen är `ja`, och Microsofts gör det inte (`publish` följer klassen,
  [kallor/guidance.md](../kallor/guidance.md)). Tabellerna nedan är körda efter beslutet: fyra serier har bytt från
  `okänd` till `ja` (de två överraskningarna och, efter R25, indexet och dess antal), och
  `us_gdp_contrib_final_sales_computers` (BEA, `ja`) har tillkommit.
- **Körning 13:s nya serier är `ja`, utom F1-serierna som läser alla rader i den kurerade filen.** Före ägarbeslutet
  2026-11-25 var det de tio F1-serier som läser filen. Nu är det de sex revideringsserierna. Avskrivningar och PP&E (P1),
  avstämningarna för intäktskravet (P2b) och TSMC:s capex-utsikt och US$-intäkt (F1) kommer från sec.gov.
  Nyttjandeperioderna (P2a) är en egen extraktion, och alla rader i `curated/useful_lives.csv` har källa på sec.gov.
  BEA:s releasearkiv och BLS flatfiler (M1) är federala verk, och BLS säger "public domain material"
  ([kallor/makro_bea_bls.md](../kallor/makro_bea_bls.md)). Census-importen (M2) är ett federalt verk, och API:ts
  metadata anger CC0. API-villkoren kräver en notis, som står i `Spec.notice` och visas med serien
  ([kallor/census_hs.md](../kallor/census_hs.md)). Notisen hindrar inte kommersiell användning. Ingen ny regel behövdes:
  alla licenstexter träffar en befintlig regel.
- **Census M3 via ALFRED är `okänd`.** Seriemärkningen är "Public Domain: Citation Requested", men kopian kommer från
  FRED, och FRED:s villkor förbjuder användning "in connection with the development or training of any software
  program or system or machine learning" ([datakallor/g6_g7_g8.md](../datakallor/g6_g7_g8.md)). Med en Census
  API-nyckel och primärkällan blir serien `ja`. Samma override gäller en kopia direkt från FRED (`fredgraph.csv`,
  stlouisfed.org), inte bara ALFRED (R10-4).
- **LMArena med Space-filer är `okänd`** (12 serier efter körning 14, bland dem G1:s kärnserie `g1_arena_text_top`). Datasetet är
  CC BY 4.0, men Space-filerna, som ger belägg och kompletta tabeller, har ingen dokumenterad licens, och Arenas
  webbvillkor kunde inte läsas ([kallor/g1g2_nya.md](../kallor/g1g2_nya.md)). Serien som bara läser datasetet är `ja`.
  Arenas två prisserier (`g2_price_at_arena_capability` och `_4o`) läser samma texttavlor, och månaderna
  2025-09 – 2026-03 vilar på tavlan 2025-08-29, som bara finns i Space-filerna
  ([kallor/g2_arena_pris.md](../kallor/g2_arena_pris.md)). De är därför `okänd` genom en nyckel-override (R10-2).
  Deras källtext och licenstext nämner inte Space-filerna. Det bör X5 rätta i `series/arena_price.py`.
- **npm är `okänd`, inte `nej`.** [riktning.md](../riktning.md) räknar npm bland det som inte går att använda
  kommersiellt. Dokumentationen säger att ingen licens anges och att npm:s villkor inte gick att läsa
  ([kallor/utvecklaradoption.md](../kallor/utvecklaradoption.md)). Det är `okänd`. Delmängden blir densamma, eftersom
  bara `ja` räknas.
- **PJM är `nej`.** Villkoren för Data Miner 2 tillåter licenstagaren kommersiell användning, men "non-members are
  specifically prohibited from republishing data". Projektet är inte medlem, så våra utdata får inte bära PJM-data
  ([kallor/el_datacenter.md](../kallor/el_datacenter.md)).
- **Manifold är `okänd`.** En kopia hos tredje part säger att icke-kommersiell användning är tillåten. Det är inte
  verifierat mot originalet ([kallor/forvantningar.md](../kallor/forvantningar.md)). Stämmer kopian blir klassen `nej`.
- **GH Archive är `okänd`.** Webbplatsen och dokumentationen är CC BY 4.0, men händelsedatat "includes material that
  may be subject to third party rights" (GitHubs villkor), och licensen är inte kontrollerad för publicering. Båda
  delarna ger `okänd` var för sig. Texten finns bara i `Spec.license` ([`series/github_ai.py`](../../src/ai_tracker/series/github_ai.py)), inte i
  [kallor/github_ai.md](../kallor/github_ai.md).
- **BEA och Census är `ja` som amerikanska federala verk** (17 U.S.C. § 105). BEA:s egen policysida gick inte att
  läsa, och Census-villkoren är inte citerade från census.gov. Klassen bygger på lagen, som Spec-texten säger.
- **LiteLLM är `ja` (MIT).** Licensen gäller filen vi läser. Priserna kommer ursprungligen från leverantörernas
  prissidor, men klassen följer den dokumenterade licensen för det vi använder.
- **ASML:s licenstext** är en kopia av TSMC:s och säger "Statutory filing by TSMC". Klassen påverkas inte, men texten
  bör rättas i `series/halvledare.py`.

## Klass per källa

Länken går till dokumentet som citerar licenstexten.

| Källa | Serier | Klass | Regel | Skäl | Licenstext |
|---|---|---|---|---|---|
| Cloudflare Radar | 13 | nej | cc-by-nc | CC BY-NC: kommersiell användning är inte tillåten | [kallor/trafik.md](../kallor/trafik.md) |
| PJM | 21 | nej | pjm-republish | PJM:s villkor: icke-medlemmar får inte vidarepublicera data | [kallor/el_datacenter.md](../kallor/el_datacenter.md) |
| AWS Price List | 2 | okänd | no-open-licence | ingen öppen licens, eller vidarespridning inte kontrollerad | [kallor/g1g2_nya.md](../kallor/g1g2_nya.md) |
| Anthropics nyhetsrum | 2 | okänd | curated | egen extraktion, men ur bolagets egna sidor utan dokumenterade villkor: seriens rader i curated/lab_revenue.csv kommer från www.anthropic.com, och bara sec.gov är kontrollerad (bolag: anthropic) | [kallor/labbintakter.md](../kallor/labbintakter.md) |
| Anthropics prissida × Epoch AI | 1 | okänd | derived-licence | härledd ur Anthropic pricing page okänd, Epoch AI benchmarking hub ja; den mest restriktiva delen avgör (ingen öppen licens, eller vidarespridning inte kontrollerad) | [kallor/priser.md](../kallor/priser.md) |
| Census M3 via ALFRED | 1 | okänd | alfred | kopian kommer från FRED eller ALFRED, vars villkor förbjuder användning i samband med maskininlärning; kommersiell användning är inte bedömd (primärkällan vore ja) | [datakallor/g6_g7_g8.md](../datakallor/g6_g7_g8.md) |
| F1: revideringar och överraskning (härledda) | 6 | okänd | curated-reads | egen extraktion, men ur bolagets egna sidor utan dokumenterade villkor: filens rader i curated/guidance_capex.csv kommer också från www.microsoft.com, och bara sec.gov är kontrollerad (bolag: alla bolag) | [kallor/guidance.md](../kallor/guidance.md) |
| GH Archive | 12 | okänd | no-open-licence | ingen öppen licens, eller vidarespridning inte kontrollerad | [kallor/github_ai.md](../kallor/github_ai.md) |
| Kurerad extraktion: AI-nyckeltal | 29 | okänd | curated | egen extraktion, men ur bolagets egna sidor utan dokumenterade villkor: seriens rader i curated/ai_kpis.csv kommer från www.microsoft.com, och bara sec.gov är kontrollerad (bolag: msft) | [kallor/ai_nyckeltal.md](../kallor/ai_nyckeltal.md) |
| Kurerad extraktion: AI-nyckeltal | 2 | okänd | curated | egen extraktion, men ur bolagets egna sidor utan dokumenterade villkor: seriens rader i curated/ai_kpis.csv kommer också från www.microsoft.com, och bara sec.gov är kontrollerad (bolag: msft) | [kallor/ai_nyckeltal.md](../kallor/ai_nyckeltal.md) |
| Kurerad extraktion: capex-guidance | 6 | okänd | curated | egen extraktion, men ur bolagets egna sidor utan dokumenterade villkor: bolagets rader i curated/guidance_capex.csv kommer från www.microsoft.com, och bara sec.gov är kontrollerad (bolag: msft) | [kallor/guidance.md](../kallor/guidance.md) |
| Kurerad extraktion: planer | 7 | okänd | curated | egen extraktion, men ur bolagets egna sidor utan dokumenterade villkor: bolagets rader i curated/plans.csv kommer från www.microsoft.com, och bara sec.gov är kontrollerad (bolag: msft) | [kallor/planer.md](../kallor/planer.md) |
| LMArena, dataset och Space-filer | 7 | okänd | arena-space | datasetet är CC BY 4.0, men Space-filerna (belägg och kompletta tabeller) har ingen dokumenterad licens, och Arenas webbvillkor kunde inte läsas | [kallor/g1g2_nya.md](../kallor/g1g2_nya.md) |
| LiteLLM × LMArena | 5 | okänd | key-override | tavlorna kommer från LMArenas Space-filer (arena.subset_boards("text")): datasetet är CC BY 4.0, men Space-filerna (belägg och kompletta tabeller) har ingen dokumenterad licens, och Arenas webbvillkor kunde inte läsas | [kallor/g2_arena_pris.md](../kallor/g2_arena_pris.md) |
| Manifold | 17 | okänd | unverified | licensen är inte verifierad: villkoren saknas eller kunde inte läsas | [kallor/forvantningar.md](../kallor/forvantningar.md) |
| Polymarket | 8 | okänd | unverified | licensen är inte verifierad: villkoren saknas eller kunde inte läsas | [kallor/forvantningar.md](../kallor/forvantningar.md) |
| SWE-bench | 1 | okänd | unverified | licensen är inte verifierad: villkoren saknas eller kunde inte läsas | [kallor/g1g2_nya.md](../kallor/g1g2_nya.md) |
| arXiv | 5 | okänd | unverified | licensen är inte verifierad: villkoren saknas eller kunde inte läsas | [kallor/epoch_arxiv.md](../kallor/epoch_arxiv.md) |
| npm | 10 | okänd | unverified | licensen är inte verifierad: villkoren saknas eller kunde inte läsas | [kallor/utvecklaradoption.md](../kallor/utvecklaradoption.md) |
| Avstämningar A5 (härledda ur SEC) | 10 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument; alla komponenter är ja | [kallor/avstamning.md](../kallor/avstamning.md) |
| BEA NIPA | 4 | ja | public-domain | public domain (amerikansk myndighet): fri användning med källhänvisning | [kallor/census_eu.md](../kallor/census_eu.md) |
| BEA NIPA, releasearkivet | 9 | ja | public-domain | public domain (amerikansk myndighet): fri användning med källhänvisning | [kallor/makro_bea_bls.md](../kallor/makro_bea_bls.md) |
| BLS, flatfiler (KPI och PPI) | 4 | ja | public-domain | public domain (amerikansk myndighet): fri användning med källhänvisning | [kallor/makro_bea_bls.md](../kallor/makro_bea_bls.md) |
| Census BTOS | 12 | ja | public-domain | public domain (amerikansk myndighet): fri användning med källhänvisning | [kallor/census_eu.md](../kallor/census_eu.md) |
| Census C30 | 2 | ja | public-domain | public domain (amerikansk myndighet): fri användning med källhänvisning | [kallor/census_eu.md](../kallor/census_eu.md) |
| Census FT-900 | 2 | ja | public-domain | public domain (amerikansk myndighet): fri användning med källhänvisning | [kallor/census_eu.md](../kallor/census_eu.md) |
| Census, import per HS-kod och land (API) | 35 | ja | public-domain | public domain (amerikansk myndighet): fri användning med källhänvisning | [kallor/census_hs.md](../kallor/census_hs.md) |
| Census, årsfil per land och end-use | 21 | ja | public-domain | public domain (amerikansk myndighet): fri användning med källhänvisning | [kallor/census_hs.md](../kallor/census_hs.md) |
| EIA Electric Power Monthly | 7 | ja | public-domain | public domain (amerikansk myndighet): fri användning med källhänvisning | [kallor/indeed_vast_eia.md](../kallor/indeed_vast_eia.md) |
| EIA-930 | 12 | ja | public-domain | public domain (amerikansk myndighet): fri användning med källhänvisning | [kallor/el_datacenter.md](../kallor/el_datacenter.md) |
| Epoch AI | 17 | ja | cc-by | CC BY 4.0: kommersiell användning tillåten med källhänvisning | [kallor/epoch_arxiv.md](../kallor/epoch_arxiv.md) |
| Eurostat | 4 | ja | cc-by | CC BY 4.0: kommersiell användning tillåten med källhänvisning | [kallor/census_eu.md](../kallor/census_eu.md) |
| F1: revideringar och överraskning (härledda) | 3 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument; alla komponenter är ja | [kallor/guidance.md](../kallor/guidance.md) |
| F1: revideringar och överraskning (härledda) | 2 | ja | curated-reads | egen extraktion ur dokument på sec.gov: bolagens alla rader i curated/guidance_capex.csv kommer från sec.gov; alla komponenter är ja (bolag: googl/meta) | [kallor/guidance.md](../kallor/guidance.md) |
| F1: revideringar och överraskning (härledda) | 2 | ja | curated-reads | egen extraktion ur dokument på sec.gov: bolagets alla rader i curated/guidance_capex.csv kommer från sec.gov; alla komponenter är ja (bolag: googl, meta) | [kallor/guidance.md](../kallor/guidance.md) |
| Fed G.17 | 2 | ja | public-domain | public domain (amerikansk myndighet): fri användning med källhänvisning | [kallor/fed_g17.md](../kallor/fed_g17.md) |
| Indeed Hiring Lab | 9 | ja | cc-by | CC BY 4.0: kommersiell användning tillåten med källhänvisning | [kallor/indeed_vast_eia.md](../kallor/indeed_vast_eia.md) |
| Kurerad extraktion: AI-nyckeltal | 25 | ja | curated | egen extraktion ur dokument på sec.gov: seriens alla rader i curated/ai_kpis.csv kommer från sec.gov (bolag: amzn, googl, meta, msft, nvda) | [kallor/ai_nyckeltal.md](../kallor/ai_nyckeltal.md) |
| Kurerad extraktion: Kinas textserier | 2 | ja | curated | egen extraktion ur dokument på sec.gov: bolagets alla rader i curated/china_text.csv kommer från sec.gov (bolag: bidu) | [kallor/kina_sec.md](../kallor/kina_sec.md) |
| Kurerad extraktion: capex-guidance | 9 | ja | curated | egen extraktion ur dokument på sec.gov: bolagets alla rader i curated/guidance_capex.csv kommer från sec.gov (bolag: amzn, googl, meta) | [kallor/guidance.md](../kallor/guidance.md) |
| Kurerad extraktion: leasing som inte har börjat | 7 | ja | curated | egen extraktion ur dokument på sec.gov: bolagets alla rader i curated/lease_commitments.csv kommer från sec.gov (bolag: amzn, crwv, googl, meta, msft, orcl) | [kallor/finansiering.md](../kallor/finansiering.md) |
| Kurerad extraktion: nyttjandeperioder | 30 | ja | curated | egen extraktion ur dokument på sec.gov: bolagets alla rader i curated/useful_lives.csv kommer från sec.gov (bolag: amzn, crwv, googl, meta, msft, orcl) | [kallor/nyttjandeperioder.md](../kallor/nyttjandeperioder.md) |
| Kurerad extraktion: order och orderstock | 62 | ja | curated | egen extraktion ur dokument på sec.gov: seriens alla rader i curated/orders_backlog.csv kommer från sec.gov (bolag: dell, dlr, etn, gev, vrt) | [kallor/order_orderstock.md](../kallor/order_orderstock.md) |
| Kurerad extraktion: planer | 32 | ja | curated | egen extraktion ur dokument på sec.gov: bolagets alla rader i curated/plans.csv kommer från sec.gov (bolag: amzn, crwv, googl, meta, orcl) | [kallor/planer.md](../kallor/planer.md) |
| Kurerad extraktion: spread vid emission | 9 | ja | curated | egen extraktion ur dokument på sec.gov: bolagets alla rader i curated/credit_issuance.csv kommer från sec.gov (bolag: amzn, googl, meta, msft, orcl) | [kallor/kredit_emission.md](../kallor/kredit_emission.md) |
| Kurerad extraktion: spread vid emission | 2 | ja | curated | egen extraktion ur dokument på sec.gov: filens alla rader i curated/credit_issuance.csv kommer från sec.gov (bolag: alla bolag) | [kallor/kredit_emission.md](../kallor/kredit_emission.md) |
| LMArena, dataset | 1 | ja | cc-by | CC BY 4.0: kommersiell användning tillåten med källhänvisning | [kallor/g1g2_nya.md](../kallor/g1g2_nya.md) |
| LiteLLM × Epoch AI | 7 | ja | derived-licence | härledd ur LiteLLM model_prices_and_context_window.json ja, Epoch AI benchmarking hub ja; alla delar är ja | [kallor/pris_formaga.md](../kallor/pris_formaga.md) |
| METR | 1 | ja | cc-by | CC BY 4.0: kommersiell användning tillåten med källhänvisning | [kallor/epoch_arxiv.md](../kallor/epoch_arxiv.md) |
| PyPI | 24 | ja | cc-by | CC BY 4.0: kommersiell användning tillåten med källhänvisning | [kallor/utvecklaradoption.md](../kallor/utvecklaradoption.md) |
| SCB | 2 | ja | cc0 | CC0: fri användning, även kommersiell | [kallor/census_eu.md](../kallor/census_eu.md) |
| SEC EDGAR XBRL, RPO | 19 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument | [kallor/rpo.md](../kallor/rpo.md) |
| SEC EDGAR XBRL, RPO | 1 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument; alla komponenter är ja | [kallor/rpo.md](../kallor/rpo.md) |
| SEC EDGAR XBRL, companyfacts | 128 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument | [kallor/sec.md](../kallor/sec.md) |
| SEC EDGAR XBRL, companyfacts | 12 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument; alla komponenter är ja | [kallor/sec.md](../kallor/sec.md) |
| SEC EDGAR XBRL, instanser (åtaganden, RPO och egna taggar) | 10 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument | [kallor/sec.md](../kallor/sec.md) |
| SEC EDGAR XBRL, segment | 47 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument | [kallor/sec_segment.md](../kallor/sec_segment.md) |
| SEC EDGAR, ASML 6-K | 4 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument | [kallor/halvledare.md](../kallor/halvledare.md) |
| SEC EDGAR, Alibaba och Baidu 6-K | 8 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument | [kallor/kina_sec.md](../kallor/kina_sec.md) |
| SEC EDGAR, Alibaba och Baidu 6-K | 4 | ja | derived-licence | härledd ur SEC: "Information presented on sec.gov is considered public information and may be copied or further distributed by users of the web site without the SEC's permission. Please consider appropriate citation to the SEC as the source." ja, Public domain ja; alla delar är ja | [kallor/kina_sec.md](../kallor/kina_sec.md) |
| SEC EDGAR, Anthropics S-1/A | 1 | ja | curated | egen extraktion ur dokument på sec.gov: seriens alla rader i curated/lab_revenue.csv kommer från sec.gov (bolag: anthropic) | [kallor/labbintakter.md](../kallor/labbintakter.md) |
| SEC EDGAR, Nebius 6-K | 3 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument | [kallor/neoclouds.md](../kallor/neoclouds.md) |
| SEC EDGAR, Nvidias 8-K (guidance) | 5 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument | [kallor/ai_nyckeltal.md](../kallor/ai_nyckeltal.md) |
| SEC EDGAR, TSMC 6-K | 14 | ja | sec | SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument | [kallor/tsmc_asien.md](../kallor/tsmc_asien.md) |
| Wikimedia Pageviews | 24 | ja | cc0 | CC0: fri användning, även kommersiell | [kallor/trafik.md](../kallor/trafik.md) |

## Antal per gren

Alla serier i katalogen.

| Gren | Serier | ja | nej | okänd | publish=True men inte ja |
|---|---|---|---|---|---|
| G1 Förmåga | 24 | 16 | 0 | 8 | 7 |
| G2 Kostnad | 16 | 8 | 0 | 8 | 5 |
| G3 Användning | 135 | 75 | 13 | 47 | 38 |
| G4 Intäkter | 76 | 70 | 0 | 6 | 4 |
| G5 Investeringar och finansiering | 238 | 219 | 0 | 19 | 7 |
| G6 Utbud och halvledare | 153 | 152 | 0 | 1 | 0 |
| G7 Fysiska flaskhalsar | 122 | 99 | 21 | 2 | 2 |
| G8 Arbete och produktivitet | 9 | 9 | 0 | 0 | 0 |
| G9 Forskning och öppet ekosystem | 32 | 2 | 0 | 30 | 0 |
| Summa | 805 | 650 | 34 | 121 | 63 |

## Kommersiellt ren delmängd

Per gren: kärnposterna i måttregistret (avsnitt 5) och källfamiljerna, och vad som blir kvar om bara `ja` räknas.

| Gren | Kärnposter | ja | nej | okänd | Familjer | Familjer kvar med bara ja | Minst 3 familjer kvar | Poster som faller bort |
|---|---|---|---|---|---|---|---|---|
| G1 | 4 | 3 | 0 | 1 | 4 | 3 | ja | `g1_arena_text_top` (okänd) |
| G2 | 1 | 1 | 0 | 0 | 1 | 1 | nej | – |
| G3 | 16 | 10 | 2 | 4 | 7 | 4 | ja | `g3_npm_openai_w` (okänd), `g3_npm_anthropic_sdk_w` (okänd), `g3_npm_langchain_w` (okänd), `g3_npm_vercel_ai_w` (okänd), `g3_cf_bots_ai_crawler_share` (nej), `g3_cf_ai_purpose_user_action` (nej) |
| G4 | 6 | 6 | 0 | 0 | 6 | 6 | ja | – |
| G5 | 5 | 5 | 0 | 0 | 5 | 5 | ja | – |
| G6 | 9 | 9 | 0 | 0 | 7 | 7 | ja | – |
| G7 | 13 | 11 | 2 | 0 | 3 | 2 | nej | `pjm_lf_peak_dom_h5` (nej), `pjm_lf_peak_rto_h5` (nej) |
| G8 | 9 | 9 | 0 | 0 | 1 | 1 | nej | – |
| G9 | 5 | 2 | 0 | 3 | 3 | 2 | nej | `g9_arxiv_cs_ai` (okänd), `g9_arxiv_cs_lg` (okänd), `g9_arxiv_cs_cl` (okänd) |

Familjeläsning: registrets familjetabell (register.entry_families).

**Läsning av tabellen.** Bara antal, inga seriers värden. 68 kärnposter, varav 56 `ja`, 4 `nej` och 8 `okänd`. 37
familjer, varav 31 har minst en `ja`-post kvar.

- **G4, G5 och G6 är helt rena.** Alla kärnposter vilar på SEC, Census, BEA och Fed.
- **G3** tappar npm (`okänd`) och Cloudflare (`nej`) och behåller 4 av 7 familjer.
- **G7** tappar PJM (`nej`) och har 2 familjer kvar, alltså under tre.
- **G9** tappar arXiv (`okänd`). Kvar är Epochs två familjer, och båda är spärrade tills det finns 24 månader egna
  ögonblicksbilder (`BACKFILL_GATED`). Tills dess har G9 ingen räknad familj i den rena delmängden.
- **G1** tappar Arena (`okänd`) och har 3 familjer kvar. ECI är spärrad på samma sätt som Epoch i G9.
- **G2 och G8** har en familj var, med eller utan licensfilter.

**Förbehåll.**
- **Familjerna är registrets familjetabell** (`register.entry_families`, K1). K2:s preliminära läsning
  (`PROVISIONAL_FAMILIES`) togs bort när K1 var mergad (R10-12). Siffrorna blev desamma: 68 poster, 56 `ja`, 37
  familjer och 31 kvar.
- `g1_epoch_bench_frontier_<valda>` räknas här som en post och en familj. I index v2 är det en familj per vald
  benchmark. Alla är Epoch, CC BY 4.0, och alltså `ja`.
- Spärrar för bakåtfylld historik är ingen licensfråga och ingår inte i tabellen. De nämns ovan där de ändrar bilden.

## Hur en klass ändras

- **Ny serie:** licenstexten i `Spec.license` ska träffa en regel. Annars ger `catalog.validate()` fel. Lägg då till en
  regel eller en override med skäl, och citera licenstexten i `docs/kallor/`.
- **Från `okänd` till `ja`:** läs och citera villkoren i källans dokument, uppdatera `Spec.license`, och kör rapporten.
  Klassen följer texten. Det som skulle flytta flest serier: microsoft.com-villkoren (44 serier, och de sex F1-serier
  som läser alla rader i den kurerade filen), npm:s villkor (10), arXiv:s API-villkor (5), Space-licensen hos LMArena (5) och en Census
  API-nyckel för M3 (1).
- **Serie som läser en kurerad fil utan att vara en extraktion av den:** ange vilka bolags rader den läser i
  `CURATED_READS`, eller koppla raderna till serien i `ROW_SERIES`. Annars blir serien `okänd`, och
  `catalog.validate()` ger fel.
- **Val av ny källa:** när det finns ett val väljs public domain, CC0, CC BY eller MIT.

## Vad som lästes

Bara katalogens metadata (`license`, `source`, `components`, `label` och nyckel), registrets kärnposter och
identifierande kolumner i `curated/*.csv` (`company` eller `lab`, för `ai_kpis.csv` `definition`, för
`lab_revenue.csv` `scope` och `measure`) och `source_url`. Inga värden ur observationstabellen lästes, och ingen data
hämtades. Det här är inget mått, så ingen post i måttregistret behövs.
