# Källor: Pris mot volym (PV1)

Följd fråga i körning 17: "Följs prisfallet vid fast förmåga (G2) av högre användning (G3), och ändras sambandet?" Ingen
ny källa och ingen ny extraktion. Allt räknas ur serier som redan finns i katalogen. Måtten, aggregaten, gränserna och
läsregeln låstes i registret innan något räknades (`docs/mattregister.md`, "2026-11-27 – PV1", commit `6ed50e2`). Modulen
är `src/ai_tracker/followed/prisvolym.py`, testerna `tests/test_followed_prisvolym.py` och rapporten
`docs/resultat/prisvolym.md`.

    python -m ai_tracker.followed prisvolym --as-of 2026-11-27 [--json PATH] [--out PATH]

## Serier som används

| Roll | Serie | Källa | Frekv. | Historik i tabellen | `known_from` | Klass | `publish` |
|---|---|---|---|---|---|---|---|
| X-H, huvudläsningens pris | `g2_price_at_capability_gpqa` (G2:s kärnserie) | LiteLLM (MIT) × Epoch GPQA Diamond (CC BY 4.0), `pris_formaga.md` | M | 2025-02– | månadsslut (se nedan) | ja | True |
| X-a, bisak a | `g2_price_at_arena_capability` (variant A, inte kärnserie) | LiteLLM × Arena, `g2_arena_pris.md` | M | 2024-01– | månadsslut + 1 dag | okänd | True |
| Y-H, huvudläsningens användning | `g3_npm_openai_w` + `g3_npm_anthropic_sdk_w` | npm download counts, `utvecklaradoption.md` | W | 2020-07– och 2023-01– | söndag + 2 dagar (backfill) | okänd | False |
| Y-b, kontrollen i bisak b | `g3_npm_react_w` + `g3_npm_express_w` | npm | W | 2015-02– och 2021-09– | söndag + 2 dagar (backfill) | okänd | False |

Beskrivning utan läsregel: `g2_price_at_arena_capability_4o`, `g2_price_at_capability` (ECI, bakåtfylld och spärrad i
registret), `g2_price_rolling12_eci`, `g2_price_rolling12_arena`, `g2_price_rolling6_arena`, `g2_price_frontier_arena`
(`g2_rorlig_troskel.md`), och npm-paketen var för sig: openai, @anthropic-ai/sdk, @google/genai, @google/generative-ai,
ai (Vercel), langchain, @langchain/core, @modelcontextprotocol/sdk, react och express.

**Används inte** (registret, avsnitt (b)): Cloudflare Radar (`g3_cf_*`, klass `nej`, CC BY-NC, och bottrafik är inte
användning), GitHubs AI-medförfattade commits (`g3_gh_ai_coauthor_*`, slutar 2025-10-05), PyPI (exakta veckor från
2026-06, onsdagsserien i den delade tabellen från 2026-05) och Wikipedia (`g3_wiki_*`, uppmärksamhet).

## Härledda storheter (inte katalogserier)

Storheterna räknas i rapporten på tabellen kapad vid läsdagen och mäts med `common.path_measures(method="log")`, samma
formler som `state.measures`. De sparas inte i observationstabellen.

| Nyckel | Definition |
|---|---|
| `pv1_pris_gpqa_q` | medel av kvartalets tre månader av `g2_price_at_capability_gpqa` |
| `pv1_pris_arena_q` | samma för `g2_price_at_arena_capability` |
| `pv1_sdk_q` | medel av veckosummorna openai + @anthropic-ai/sdk för veckorna i kvartalet |
| `pv1_kontroll_q` | samma för react + express |
| `pv1_sdk_rel_q` | `pv1_sdk_q` / `pv1_kontroll_q` |

**Månad till kvartal.** `aggregate.derive` med månadsfrekvens och vikten 1/3 för månaderna m, m − 1 och m − 2. Bara
kvartalets sista månad behålls. Ett värde finns först när alla tre månader är kända på dagen, och `known_from` är den
senaste av dem.

**Vecka till kvartal.** En vecka (måndag–söndag) hör till kvartalet där dess torsdag ligger, så varje vecka hör till
exakt ett kvartal (13 eller 14 veckor). För en summa summeras paketen vecka för vecka, och en vecka finns bara när alla
paket har den. Ett kvartal finns först när alla dess veckor är kända på dagen. Värdet är medlet av veckosummorna, och
`known_from` är den senaste veckans. Kvoten är kvoten av kvartalsmedlen.

**as_of.** Tabellen kapas vid läsdagen innan något räknas, och varje rad tas i sin senaste vintage på dagen. Testet
`test_a_row_known_after_the_day_changes_nothing` lägger till en senare vintage, senare månader och ett helt senare
kvartal av veckor och kräver att rapporten blir densamma.

## Läsregeln

F0:s symmetriska regel med X:s förändring i takt mot Y:s förändring i takt, *g* = 50, *h* = 20, *k* = 2 och tecken −1, en
rad per par (registret, avsnitt (c)). Förändring i takt för X, eftersom priset vid fast förmåga nästan alltid faller:
med takt hade X bara haft impulser nedåt (R28-5). Ett jämnt prisfall ger därför ingen impuls. Regeln läser om fallet
blev snabbare eller långsammare.

## Kontroller och fynd

- **Täckning** (2026-11-27): GPQA-priset 2025-02 – 2026-10 (21 månader), Arena A 2024-01 – 2026-10 (34), npm-veckorna
  utan luckor till veckan 2026-11-16–22. npm har fyra revisionsrader (tre veckor), som tas i sin senaste vintage.
- **Datering av GPQA-priset.** I den delade tabellen har `g2_price_at_capability_gpqa` och `g2_price_at_capability`
  `known_from` = månadens sista dag (till exempel 2026-10-31 för 2026-10), medan `pris_formaga.md` och koden
  (`series/price_capability.py`, rättat i X1) säger månadsslut + 1 dag. Raderna hämtades 2026-11-23. Skillnaden är en dag
  och påverkar inte kvartalen i PV1, men raderna bör byggas om. Det är inte gjort i spåret.
- **Kortaste serien styr.** GPQA-priset har nivå per kvartal från 2025Q2, takt från 2026Q2 och förändring i takt först
  från 2026Q4. Huvudläsningen kan därför inte avgöras förrän npm-kvartalet 2027Q1 är känt (omkring 2027-03-30).
- **Stickprov.** Kvartalsmedlen kontrollerades mot tabellen för hand i testerna (syntetiskt) och mot rapporten: npm-summan
  för 2026Q3 är medlet av 13 veckor (2026-06-29 – 2026-09-27), och Arena A:s 2026Q3 är medlet av 0,09, 0,1375 och 0,1375.
