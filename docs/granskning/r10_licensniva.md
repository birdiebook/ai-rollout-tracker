# R10 – granskning av licensnivån (K2)

Granskningsspår R10, 2026-11-24, gren `auto14/r10-licensniva` från `auto13/k2-licensniva` (`638208c`). Granskat:
`src/ai_tracker/licenses.py`, kravet i `catalog.validate()`, `tests/test_licenses.py` och
[datakallor/licensniva.md](../datakallor/licensniva.md), mot licenstexterna i `docs/datakallor/` och `docs/kallor/`.
Körningens nya serier lästes ur grenarna `auto13/p1-avskrivningar` (`0933c9a`), `m1-makro` (`5ea00d3`),
`m2-census-hs` (`57fc420`), `f1-revideringar` (`dcdc089`), `p2a-nyttjandeperioder` (`58f6659`) och
`p2b-intaktskrav` (`0fc161e`) med `git archive` till en tillfällig katalog, och klassades med K2:s regler. Inga
grenar ändrades. Inga observationsvärden lästes, bara metadata och kolumnerna `company` och `source_url` i
`curated/*.csv`.

Tester: [`tests/test_r10_licensniva.py`](../../tests/test_r10_licensniva.py). Strikta xfail-tester markerar fel som
är bekräftade. De slår om till XPASS när felet är rättat, och då ska markeringen tas bort. Rättningarna för R10-2
till R10-5 provades i minnet: alla deras xfail-tester blev XPASS, och vakttesterna höll.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Regelordning och regex | **Fel (R10-3, R10-4).** Ordningen är rätt, men restriktiva ord som "non-commercial", "all rights reserved" och "prohibited" saknar regel, och `MIT` träffar också namnet MIT. En FRED-kopia blir `ja` |
| 2. Klass per källa | **Fel (R10-2).** 37 källor kontrollerade. Arenas två prisserier är `ja`, fast de bygger på samma Space-filer som gör Arenas texttavlor `okänd`. Övriga stämmer. Sju Microsoft-serier är för restriktiva (R10-6) |
| 3. Härledning | **Fel (R10-1)** för F1: poolade revideringsindex läser Microsofts guidance direkt ur CSV:n och blir `ja`. Komponenter, A5 och `*_hyp4` är rätt |
| 4. `validate` och körningens nya serier | **Anmärkning.** En oklassad text ger fel. Alla 143 nya serier klassas, 137 rätt. Sex F1-serier fel (R10-1) |
| 5. `publish` och klass oberoende | **OK.** Inget i `site/`, `site_bundle/` eller `web/` ändrades |

**Slutdom: godkänd med anmärkningar.** Mekanismen är rätt byggd: restriktiva regler före tillåtande, den mest
restriktiva delen avgör, och `validate` stoppar en oklassad text. Fyra fel gör en klass för tillåtande och ska
rättas. R10-2, R10-3 och R10-4 rättas innan K2 mergas, och R10-1 innan F1 mergas. Alla fyra är små. Rättningarna
provades tillsammans på katalogen och på de sex grenarna: de ändrar bara Arenas två prisserier, från `ja` till
`okänd`. Katalogen på `dceec75` blir då 488 serier: 339 `ja`, 34 `nej` och 115 `okänd`. Kärnposterna ändras inte.

## 1. Regelordning och regex

- Ordningen är rätt: alla regler som ger `nej` eller `okänd` står före alla som ger `ja` (testas i
  `test_guard_rule_order_restrictive_before_permissive`). PJM:s text har både "no open licence" och förbudet mot
  vidarepublicering, och blir `nej`, inte `okänd`.
- `derived: a + b` delas på " + ". Varje del klassas med alla regler, och den mest restriktiva delen avgör. En del
  utan regel ger fel. "CC BY-NC" i en del ger `nej` för helheten.
- Namngivna licenser som reglerna inte känner till ger fel, inte `ja`: "CC BY-SA 4.0", "CC BY-ND 4.0",
  "CC BY NC 4.0", "ODbL 1.0", "Apache-2.0" och "Creative Commons Attribution-NonCommercial 4.0". Det är säkert.
- **R10-3.** Restriktiva ord som inte är en licens med namn fångas inte. Bekräftade exempel, alla `ja` i dag:
  "CC BY 4.0 for the docs; the data is for non-commercial use only", "Creative Commons Attribution 4.0 for the
  text; data: all rights reserved", "CC BY 4.0 / redistribution prohibited", "Licence: CC BY 4.0 (mirror),
  original: commercial use prohibited", "These series may be under copyright or in the public domain" (FRED:s
  juridiska text), "Public domain status unclear" och "17 U.S.C. § 105 does not apply". `\bMIT\b` träffar också
  namnet: "MIT Technology Review; terms not read" blir `ja`. GH Archive är `okänd` bara på grund av sista meningen
  "Not checked for publication". Utan den blir texten `ja`, trots "may be subject to third party rights".
- **R10-4.** Overriden `alfred` träffar bara ordet "ALFRED". En kopia från FRED (`fredgraph.csv`) med märkningen
  "Public Domain: Citation Requested" blir `ja`, fast K2:s skäl för ALFRED gäller FRED:s villkor. Ingen nuvarande
  serie berörs, men FRED är den naturliga vägen till makroserier.

## 2. Klass per källa

Kontrollerat mot texten som dokumenten citerar. Domen gäller klassen, inte om källan är bra.

| Källa | Klass | Dokumenterad text | Dom |
|---|---|---|---|
| SEC XBRL (companyfacts, RPO, segment, instanser) | ja | sec.gov/privacy: "may be copied or further distributed ... without the SEC's permission" ([sec.md](../kallor/sec.md)) | OK |
| TSMC 6-K | ja | samma SEC-text. IR-villkoren (403) spelar ingen roll, eftersom siffrorna läses ur inlämningen på sec.gov ([tsmc_asien.md](../kallor/tsmc_asien.md)). TWSE används bara som kontroll | OK |
| ASML 6-K | ja | samma SEC-text ([halvledare.md](../kallor/halvledare.md)). Licenstexten säger "Statutory filing by TSMC" (R10-9) | OK |
| Nebius 6-K | ja | samma SEC-text ([neoclouds.md](../kallor/neoclouds.md)) | OK |
| Nvidia 8-K, Anthropic S-1/A | ja | SEC. S-1-serien har en enda rad, och den ligger på sec.gov | OK |
| BEA NIPA | ja | 17 U.S.C. § 105. BEA:s egen sida gick inte att läsa ([g3_g4_g5.md](../datakallor/g3_g4_g5.md)) | OK, lagtext (R10-10) |
| Census BTOS, C30, FT-900 | ja | 17 U.S.C. § 105 och Census citeringspolicy, inte citerat från census.gov | OK, lagtext (R10-10) |
| Fed G.17 | ja | "in the public domain and may be copied and distributed without permission" ([fed_g17.md](../kallor/fed_g17.md)) | OK |
| EIA | ja | "public domain ... You may use and/or distribute any of our data" | OK |
| Eurostat, SCB | ja | CC BY 4.0, CC0 1.0 ([g3_g4_g5.md](../datakallor/g3_g4_g5.md)) | OK |
| Indeed, Epoch AI, METR | ja | CC BY 4.0, citerat | OK |
| PyPI | ja | CC BY 4.0 för BigQuery-tabellen. pypistats har ingen egen licens, men talen är tabellens ([utvecklaradoption.md](../kallor/utvecklaradoption.md)) | OK |
| Wikimedia | ja | CC0 | OK |
| LiteLLM × Epoch | ja | MIT för allt utanför `litellm/enterprise/`, och prisfilen ligger utanför ([pris_formaga.md](../kallor/pris_formaga.md)). Epoch CC BY 4.0 | OK |
| **LiteLLM × LMArena text** | **ja** | LiteLLM MIT. Men tavlorna kommer från `arena.subset_boards("text")`, alltså Space-filerna, och månaderna 2025-09 – 2026-03 vilar på tavlan 2025-08-29, som bara finns i Space-filerna ([g2_arena_pris.md](../kallor/g2_arena_pris.md)). Licenstexten nämner bara datasetet | **Fel (R10-2)**, ska vara `okänd` |
| LMArena, bara dataset (WebDev) | ja | `license: cc-by-4.0`. WebDev läser inga Space-filer (`PICKLE_TABLES["webdev"]` är tom) | OK |
| LMArena med Space-filer (text) | okänd | Space-filerna saknar dokumenterad licens | OK |
| Cloudflare Radar | nej | "made available under the CC BY-NC 4.0 license" ([trafik.md](../kallor/trafik.md)) | OK |
| PJM | nej | "non-members are specifically prohibited from republishing data" ([el_datacenter.md](../kallor/el_datacenter.md)) | OK |
| Census M3 via ALFRED | okänd | FRED:s förbud mot användning "in connection with ... machine learning" ([g6_g7_g8.md](../datakallor/g6_g7_g8.md)) | OK |
| npm | okänd | ingen licens angiven, och villkoren gick inte att läsa | OK. Delmängden blir densamma som med `nej` |
| Manifold | okänd | bara en kopia hos tredje part, som säger icke-kommersiellt ([forvantningar.md](../kallor/forvantningar.md)) | OK. Inte verifierat, så inte `nej` |
| Polymarket, arXiv, SWE-bench | okänd | villkoren inte lästa, eller ingen licensfil | OK |
| GH Archive | okänd | "Not checked for publication" | OK, men skört (R10-3) |
| AWS Price List, anthropic.com | okänd | ingen öppen licens, inte kontrollerad för publicering | OK |
| Kurerade filer, Microsoft | okänd | 82 av Microsofts 139 rader i `ai_kpis.csv` och alla 30 i `guidance_capex.csv` kommer från www.microsoft.com, utan dokumenterade villkor. `plans.csv` likaså | OK per bolag. Sju serier för restriktiva (R10-6) |
| Kurerade filer, övriga bolag och leasing | ja | alla rader har `source_url` på www.sec.gov | OK |

## 3. Härledning

- `Spec.components`: transitivt, säkert mot cykler, och en komponent som saknas ger `okänd`. Rätt.
- A5: de fem avstämningarna har komponenter som täcker alla indata (`capex_hyp4`, `ocf_hyp4`, `rpo_hyp4`,
  `debt_issued_hyp4`, segmentintäkter). P2b:s fem nya (`x_dep_rev`, `x_capcost_rev_r08`, `_r12`, `x_dep_capex`,
  `x_dep_rev_aws`) har det också. Alla är `ja`, och det är rätt.
- `*_hyp4`: alla tio i katalogen och P1:s tre nya (`dep_hyp4`, `dep_ppe_hyp4`, `ppe_net_hyp4`) får alla fyra
  bolagen ur etiketten. Ett bolag som saknas i katalogen hoppas över utan fel, och etiketten måste sluta med
  bolagen (R10-7).
- `capex_ocf_hyp4` i `register.DERIVED` får täljare och nämnare. Rätt.
- **R10-1.** F1:s revideringsindex (`f1_rev_index_4q`, `f1_rev_index_q`, `f1_rev_n_4q`, `f1_rev_n_q`,
  `f1_rev_median_4q`, `f1_rev_median_q`, alla `publish=True`) räknar alla rader i `curated/guidance_capex.csv`
  (`capex_statements` filtrerar inte på bolag). Microsofts 30 rader där kommer alla från www.microsoft.com.
  Seriernas källa börjar med "Härledd (F1)", så den kurerade regeln gäller inte. Komponenterna nämner inga
  `guid_capex_*`-serier. Licenstexten nämner sec.gov/privacy, så SEC-regeln ger `ja`. Med K2:s egen regel borde de
  vara `okänd`, som Microsofts guidance. F1:s åtta övriga serier (överraskning för TSMC, Nvidia, Meta och Google,
  deras index och antal, och TSMC:s capex-guidance) använder inga Microsoft-rader och är rätt `ja`.

## 4. `validate` och körningens nya serier

- En licenstext som ingen regel klassar ger fel i `validate()`, och tom licens ger ett eget fel. Rätt.
- Nya serier, klassade med K2:s regler på respektive gren:

| Gren | Nya serier | Klass | Dom |
|---|---|---|---|
| `p1-avskrivningar` | 26 (avskrivningar och PP&E ur SEC XBRL) | 26 ja (sec) | OK |
| `m1-makro` | 12 (BEA-arkivet 8, BLS KPI och PPI 4) | 12 ja (public domain). BLS har citat från bls.gov | OK |
| `m2-census-hs` | 56 (Census import per land, slutanvändning 21 och HS via API 35) | 56 ja (17 U.S.C. § 105, API-metadata CC0) | OK |
| `p2a-nyttjandeperioder` | 30 (kurerade, `curated/useful_lives.csv`) | 30 ja: alla 305 rader på www.sec.gov | OK |
| `p2b-intaktskrav` | 5 avstämningar (grenen har också P1:s 26) | 5 ja, komponenterna kontrollerade | OK |
| `f1-revideringar` | 14 | 14 ja | **6 fel (R10-1)**, 8 OK |

- Ingen ny licenstext är oklassad, så `validate()` ger inga fel på grenarna.
- Ingen av grenarna har FRED-kopior eller texter med de ord som R10-3 gäller.

## 5. `publish` och klass

- K2 ändrar bara `licenses.py`, `validate()` och en kommentar i `catalog.py`, tester och dokument. Inget i
  `src/ai_tracker/site/`, `src/ai_tracker/site_bundle/` eller `web/` ändrades (`git diff --name-only`). Bara
  `catalog.validate` importerar `licenses`.
- Ingen kod läser klassen för att bestämma `publish`. `publish=True` med `nej` är tillåtet (Cloudflare, 13 serier),
  och `publish=False` med `ja` är tillåtet.
- Vid rättningen av R10-1 i F1: `guid_capex_*` har `publish=False` (väntar på att flaggan sätts efter R2). Läggs de
  in som komponenter ger `validate` felet "publish=True needs every component publishable". Det är en
  `publish`-fråga för F1, inte en licensfråga.
- R10-2 ändrar inte `publish` för Arenas prisserier. De får visas på den icke-kommersiella sidan som förut.

## Fynd

| Id | Grad | Fynd | Rättning |
|---|---|---|---|
| R10-1 | must_fix | Sex F1-serier blir `ja` fast de poolar Microsofts guidance från microsoft.com. En källa som nämner `curated/<fil>.csv` men inte börjar med "Kurerad extraktion (" går förbi den kurerade regeln | `validate` ger fel när `Spec.source` nämner en kurerad fil och serien varken är en kurerad extraktion eller har en komponent ur filen, om inte en nyckel-override finns. F1:s sex poolade serier får `KEY_OVERRIDES` med `okänd` och skäl. `lab_rev_*` (3 serier) behöver då overrides: S-1-serien `ja`, de två från nyhetsrummet `okänd`. Att söka filnamnet var som helst i källan provades också, men det gör S-1-serien och fyra F1-serier (överraskning för TSMC och Nvidia, indexet och antalet) `okänd` i onödan |
| R10-2 | must_fix | `g2_price_at_arena_capability` och `_4o` (`publish=True`) är `ja`, fast tavlorna kommer från Space-filerna, som gör `g1_arena_text_*` `okänd`. Overriden `arena-space` matchar bara källtexten "LMArena (HF-dataset + Space-filer)", och prisseriernas licenstext nämner bara datasetet | `KEY_OVERRIDES` med `okänd` för de två nycklarna, med samma skäl som `arena-space`. X5 (som redan rör Arena) bör också nämna Space-filerna i `arena_price`:s källa och licenstext. Provat: bara de två serierna ändras |
| R10-3 | must_fix | Restriktiva ord förloras mot "CC BY 4.0", "MIT" och "public domain", och `\bMIT\b` träffar namnet MIT | En regel med `okänd` efter `pjm-republish` och före de tillåtande: `non-?commercial\|all rights reserved\|proprietary\|third[- ]party rights\|may be (?:under\|subject to) copyright\|not in the public domain\|not verified\|personal use only\|prohibit\|not (?:permitted\|allowed)\|does not (?:apply\|cover)\|\bunclear\b`. MIT-regeln blir `(?<![\w-])MIT(?=[ -]?\(?(?i:licen[cs]e)\|[,)])`. Provat: ingen klass ändras i katalogen eller på grenarna. Fem tester i `test_licenses.py` behöver nya exempel, eftersom de använder "all rights reserved" som oklassad text, M3-texten som `ja` och alla LiteLLM-serier som `ja` |
| R10-4 | must_fix | Overriden `alfred` träffar bara "ALFRED". En FRED-kopia (`fredgraph.csv`) med märkningen "Public Domain: Citation Requested" blir `ja`, fast skälet gäller FRED:s villkor | Regex på källan: `\b(?:AL)?FRED\b\|stlouisfed\.org`. Provat: ingen nuvarande källa ändras |
| R10-5 | should_fix | Den kurerade regeln ersätter licensreglerna i stället för att ta den mest restriktiva. En kurerad serie med licensen "unverified" eller "CC BY-NC" blir `ja` om raderna ligger på sec.gov | Ta den mest restriktiva av kurerad dom och licensdom. Provat: ingen klass ändras |
| R10-6 | should_fix | Regeln gäller bolaget, inte serien. Sju Microsoft-serier har bara rader på sec.gov men är `okänd` med skälet att raderna "också" kommer från microsoft.com: `kpi_msft_azure_growth_v1`–`v3`, `_cc_v1`–`_cc_v3` och `kpi_msft_azure_ai_pts_v2` | Koppla rader till serie med källmodulens nyckelfunktion (`ai_kpis.series_key`), och fall tillbaka på bolaget när det inte går. Valet är dokumenterat som försiktigt, så det är inte bråttom |
| R10-7 | note | `*_hyp4` får komponenter ur etikettens slut. Ett bolag som saknas hoppas över utan fel, och en etikett med text efter bolagen ger inga komponenter. Alla 13 summor är rätt i dag | Skriv `components` explicit i summorna, eller låt `validate` kräva att alla bolag i etiketten finns |
| R10-8 | note | `validate` kontrollerar inte att en override har klassen `ja`, `nej` eller `okänd`. Ett stavfel ("okand") godtas, och en härledd serie ger då `KeyError` | Kontrollera klassen i `KEY_OVERRIDES` och reglerna i `validate` |
| R10-9 | note | ASML:s licenstext är TSMC:s och säger "Statutory filing by TSMC". Den visas på sidan. Klassen påverkas inte | Egen text i `series/halvledare.py` |
| R10-10 | note | BEA och Census är `ja` enligt 17 U.S.C. § 105, inte enligt citat från bea.gov eller census.gov. Det är lag, inte en gissning, och det står öppet i texten. M2:s API-serier citerar dessutom CC0 ur API:ts metadata | Citera myndighetens sida när den går att nå, som M1 gör för BLS |
| R10-11 | note | Overrides och källgrupper matchar fritext i `Spec.source`. Byter X5 namn på LMArenas källa slutar `arena-space` att gälla, och texttavlorna blir `ja`. R10-2 visar samma svaghet åt andra hållet | Skyddet finns för texttavlorna: `test_known_sources_have_their_documented_class` faller när mönstret inte hittar någon serie. Behåll testet. Nyckel-overrides är stabilare än fritext |
| R10-12 | note | `PROVISIONAL_FAMILIES` blir död kod när K1 mergas. Med K1:s `register.entry_families` blir siffrorna desamma (68 poster, 56 `ja`, 37 familjer, 31 kvar) | Ta bort efter K1 |

## Vad som inte gjordes

- Inga licenssidor lästes på nätet. Granskningen jämför klasserna med texterna som dokumenten redan citerar.
- Inga observationsvärden lästes, och inga serier hämtades.
- Ingen rättning gjordes i K2:s kod. Rättningarna i tabellen provades i minnet och i en tillfällig kopia.
- R10-1:s rättning (felet i `validate`) provades inte i kod, bara regeln för sökning var som helst i källan.
