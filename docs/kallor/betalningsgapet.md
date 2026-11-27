# Källor: Betalningsgapet (BG1)

Följd fråga, inte en gren. Registret: `docs/mattregister.md`, posten "2026-11-26 – BG1". Kod:
`src/ai_tracker/followed/betalningsgapet.py` (F0:s motor, `followed/common.py` och `followed/aggregate.py`). Tester:
`tests/test_followed_betalningsgapet.py` (syntetiska data). Resultat: `docs/resultat/betalningsgapet.md`.

## Inga nya källor

BG1 hämtar ingenting och extraherar ingenting. Alla storheter är summor och kvoter av serier som redan finns i
katalogen, och de härleds när rapporten byggs. Det finns därför inga nya katalogserier, inga `bg1_`-nycklar i
observationstabellen och inga nya licenser. Underlaget och dess licenser:

| Underlag | Serier | Källa och licens | Kommersiell klass |
|---|---|---|---|
| Avskrivningar (P1) | `dep_msft`, `dep_googl`, `dep_amzn`, `dep_orcl`, `dep_crwv` | SEC EDGAR XBRL, public information | `ja` |
| Anläggningstillgångar, netto (P1) | `ppe_net_<bolag>` för samma fem | SEC EDGAR XBRL | `ja` |
| Molnintäkter | `rev_msft_cloud`, `rev_google_cloud`, `rev_aws`, `rev_orcl_cloud`, `rev_crwv` | SEC EDGAR XBRL | `ja` |
| RPO | `rpo_msft`, `rpo_googl`, `rpo_amzn`, `rpo_orcl`, `rpo_crwv` och delarna `rpo_msft_12m`, `rpo_orcl_12m`, `rpo_googl_24m`, `rpo_crwv_24m` | SEC EDGAR XBRL | `ja` |
| Capex | `capex_<bolag>` för samma fem | SEC EDGAR XBRL | `ja` |
| P2b:s avstämningar | `x_dep_rev`, `x_capcost_rev_r08`, `x_capcost_rev_r12`, `x_dep_rev_aws`, `x_rpo_cover` | härledda ur SEC-serierna | `ja` |
| Nyttjandeperioder (P2a) | `useful_life_servers_<bolag>_hi`/`_lo`, `useful_life_computer_equipment_crwv_hi`/`_lo` | extraherade ur 10-K och 10-Q | `ja` |
| AI-nyckeltal | `kpi_msft_azure_growth_v2`, `_v3`, `_cc_v3`, `kpi_msft_ai_business_runrate`, `kpi_amzn_aws_ai_runrate`, `kpi_googl_cloud_backlog` | extraherade ur bolagens dokument (`docs/kallor/ai_nyckeltal.md`) | `ja` |
| Labbens intäkter | `lab_rev_anthropic_company_run_rate`, `_s1`, `lab_rev_anthropic_claude_code_run_rate` | anthropic.com och S-1/A (`docs/kallor/labbintakter.md`), `publish=False` | nyhetsrummet `okänd`, S-1/A `ja` |

Klassen för kommersiell användning gäller per serie i katalogen (`ai_tracker.licenses`). BG1 publicerar inga värden på
den publika sidan. Rapporten i `docs/resultat` visar extraherade siffror med serienyckel och `known_from`, aldrig text.

## Kodning

- **Molnfyran** = Microsoft, Alphabet, Amazon och Oracle. Samma bolag som `rpo_hyp4`. CoreWeave är bara bolagsrad,
  eftersom `ppe_net_crwv` börjar 2024Q4. Meta har ingen molnintäkt och ingen RPO. Nebius och IREN saknar avskrivningar
  och anläggningstillgångar i katalogen.
- **Intäktskrav** `krav(M, r)` = Σ `dep_<c>` över fyra kvartal + *r* × Σ `ppe_net_<c>` vid kvartalets slut. *r* = 0,10
  i huvudläsningen och 0, 0,08 och 0,12 som känslighet.
- **Gapet** `gap_moln(M, r)` = 100 × krav / Σ molnintäkter över fyra kvartal, och `gap_rpo(M, r)` = 100 × krav / Σ RPO
  vid kvartalets slut.
- **Capex** `capex4(M)` = Σ `capex_<c>` över fyra kvartal (för ett bolag samma tal som KL1:s `kl_capex4_<c>`).
- **Versioner** med `aggregate.derive`: en version per datum då en komponent får en ny version, bara när alla
  komponenter finns, `known_from` = den senaste komponenten. Läsdagens vintage gäller för hela historiken. Rapporten
  säger vilka komponenter nästa kvartal saknar.
- **Mått** med `common.path_measures` (samma formler som `state.measures`): nivå, takt (log × 100 över fyra kvartal),
  förändring i takt (mot två kvartal tidigare) och överraskning mot B1. Gapets takt = kravets takt − intäkternas takt.
- **Läsregeln:** F0:s `read_measures` med X = gapets takt, *Y* = förändring i takt för `capex4` med samma bolag, *g* = 5,
  *h* = 5, *k* = 2 och tecken −1. En rad per X: huvudläsning, gapet mot RPO, tre rader för *r*, RPO utan Oracle och två
  rader per bolag.
- **Regimmarkörer:** varje kvartal där en angiven nyttjandeperiod skiljer sig från det föregående värdet i samma serie
  listas. En läsning märks när det högsta värdet (`_hi`) ändrats inom X:s fönster (*q* − 7 … *q*) för något av bolagen,
  och när Microsofts avskrivningar i fönstret har kvartal på den gamla basen (till och med 2024Q2). Märkningen ändrar
  inget utslag.
- **Nästa inlämning:** F0:s `next_filings` på `capex_<bolag>` (nästa kvartals slut plus medianen av de åtta senaste
  avstånden).

## Förbehåll

- **Intäktskravet är härlett.** *r* är ett registrerat antagande och ingen skattning. Kvoten är linjär i *r*, och *r* =
  0,10 är mittpunkten i P2b:s intervall. Bara kapitalet: drift, el, personal och skatt ingår inte.
- **Hela bolaget mot molnet.** Avskrivningar och netto gäller hela bolaget (Amazons logistik, Microsofts kontor), men
  intäkterna bara molnet. Nivån är ingen marginal. AWS-segmentets egen kvot (`x_dep_rev_aws`, bara avskrivningar) står
  som sammanhang.
- **Nettot innehåller pågående byggen och mark,** som höjer kravet med *r* men inte avskrivningarna (P2b). Raden med
  *r* = 0 skiljer de två delarna åt.
- **Mekanisk koppling.** Nettot växer med capex, och avskrivningarna följer efter. En uthållig acceleration i capex
  höjer både X och *Y* och läses som talar emot.
- **Definitionsbrott:** Microsofts avskrivningsrad till och med 2024Q2 ligger på den gamla basen (P2b, R14). Alphabets
  avskrivningar finns från 2023Q1, vilket begränsar molnfyrans historik: gapets takt finns från 2024Q4.
- **Nyttjandeperioder:** det lägsta värdet blandar punkter och intervall (serienoten), så en ändring där kan vara en
  formulering. Därför märker bara det högsta värdet. En ändring som bara syns i det lägsta värdet (till exempel Amazon
  2025Q4) märker inte, men listas.
- **RPO** är en balans och klumpig (OpenAI hos Oracle). Oracles andel av molnfyrans RPO och raden utan Oracle visar hur
  mycket ett bolag betyder. Bolagen anger andelen på kort sikt med olika horisont (12 eller 24 månader, Amazon ingen).
- **Molnintäkternas omfång** skiljer sig: Microsoft Cloud innehåller kommersiell Office 365, LinkedIn och Dynamics,
  Oracles moln SaaS och Google Cloud Workspace.
- **Oracles kvartal** slutar en månad före kalenderkvartalet (mittpunktsregeln), och Oracle lämnar in före de andra.
  CoreWeave saknar separata kvartal för fjärde kvartalet före 10-K:n (2024Q4 är känt först 2026-03-02).
- **AI-nyckeltal och labbintäkter** är tabellrader: oregelbundna, med definitionsbrott (Azure v1–v3). Run-rate är
  bolagens egen årstakt och inte redovisad intäkt.
- **Guidance:** bolagens guidance för molnintäkter finns inte i katalogen, så B1 är enda baslinjen för intäkterna.

## BLOCKED

- ~~Anthropics redovisade (GAAP) intäkter~~: inte längre BLOCKED. Spår AN1 (registret 2026-11-27 AN1) extraherade dem
  ur S-1, S-1/A och 424B4 som katalogserier `lab_gaap_anthropic_*` (`docs/kallor/anthropic_gaap.md`). BG1 visar dem i
  avsnitt 5 som tabellrader och en kvartalstabell bredvid run-rate, utanför regeln.
- **OpenAI** har ingen registreringsansökan på EDGAR, och openai.com nekas av proxyn.

## Kommandon

    python -m ai_tracker.followed betalningsgapet --as-of 2026-11-26 [--json PATH] [--out PATH]
    python -m ai_tracker.followed antenner --as-of 2026-11-26
    python -m pytest -q tests/test_followed_betalningsgapet.py
