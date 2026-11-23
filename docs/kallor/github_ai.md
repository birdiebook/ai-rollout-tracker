# Källa: AI-medförfattare i publika commits (G3, spår B2 i steg 2)

Ledtråd L2 (användning), gren G3. Måtten nedan skrevs och committades **innan** några AI-räkningar per vecka
hämtades. Det som hade undersökts före registreringen står under "Vad som var känt före registreringen".
Ingen analys (takt, tillväxt, jämförelser) görs i spåret.

## Vad som var känt före registreringen (2026-11-23)

- **GH Archive har inga commit-meddelanden efter 2025-10-08 16:59 UTC.** GitHub tog bort `commits`, `size`
  och `distinct_size` ur PushEvent i Events API (GitHubs changelog 2025-08-08, "Upcoming changes to GitHub
  Events API payloads": brownout-test 2025-09-08, skarpt 2025-10-07). Kontrollerat i GH Archives timfiler:
  timme `2025-10-08-16` har `commits`, från `2025-10-08-17` har PushEvent bara `repository_id`, `push_id`,
  `ref`, `head` och `before`. Därmed går mått (a)–(c) **inte** att föra vidare ur GH Archive. Serien ur GH Archive
  är historisk och stängd (`closed=True`), och den löpande serien kommer från GitHubs commit-sökning (del B).
- **GH Archives täckning faller under 2026.** Antalet händelser per timme var cirka 160 000 under 2025 och cirka
  47 000 2026-11-22 kl. 12. Timmen 2026-11-01 kl. 12 har 4 720 händelser och ingen PushEvent. Det påverkar inte
  del A (som slutar 2025-10), men gör GH Archive olämpligt som nämnare för nya mått.
- **Mönsterkalibrering:** för att välja identiteter listades de vanligaste `Co-authored-by:`-raderna i två
  timmar (2024-06-05 kl. 14 och 2025-09-01 kl. 12, UTC). Bara vilka identiteter som förekommer användes, inte
  hur de utvecklas över tid. Inga veckovärden hade räknats.

## Del A: GH Archive, historik 2021-01-04 till 2025-10-05 (stängd)

### Enhet och urval

- **Källa:** GH Archives timfiler `https://data.gharchive.org/YYYY-MM-DD-H.json.gz` (samma innehåll som
  BigQuery-tabellerna `githubarchive.*`). Filerna laddas ned och räknas i Python. **BigQuery används inte**,
  se "Budget" nedan.
- **Commit:** ett element i `payload.commits` i en `PushEvent` med `public = true` och `distinct = true`
  (commiten är ny i repot, inte redan pushad till en annan gren). Events API listar högst 20 commits per push,
  så commits utöver 20 syns inte. Både täljare och nämnare räknas på de listade commitsen. Inom en timme räknas
  varje SHA en gång. Över timmar summeras (en SHA som pushas till en fork en annan timme räknas igen, ovanligt).
- **Urvalstimmar (registrerat urval):** vecka = ISO-vecka, måndag–söndag UTC. Varje vecka har sju fasta timmar:
  **mån 02, tis 06, ons 10, tor 14, fre 18, lör 22, sön 12** (UTC). De täcker dygnet jämnt och alla veckodagar,
  och de är desamma varje vecka, så urvalet är jämförbart över tid. 7 av 168 timmar = 4,2 %.
- **Mätbar timme:** filen finns, kan läsas helt och minst 90 % av dess PushEvent har fältet `commits`.
  En timme som inte är mätbar ersätts av nästa timme samma dag (h+1, h+2, h+3, första mätbara).
  Annars saknas den.
- **Vecka med värde:** minst 5 mätbara urvalstimmar. Antalet timmar redovisas i den kurerade filen
  (`n_hours`). Veckan 2025-10-06–12 har bara 3 mätbara timmar före brytpunkten och får inget värde.
- **Period:** 2021-W01 (måndag 2021-01-04) till 2025-W40 (söndag 2025-10-05).

### Identiteter (AI-medförfattare)

En commit är **AI-medförfattad** om meddelandet har minst en rad som matchar
`^\s*co-authored-by:\s*(.+?)\s*$` (skiftlägesokänsligt), och identiteten (namn och e-post, gemener, där ett
inledande `<123456+` i e-posten tas bort) matchar något mönster nedan. Varje mönster hör till en grupp. En commit
kan träffa flera grupper och räknas då i varje grupp men bara en gång i totalen.

| Grupp | Mönster (reguljärt uttryck på identiteten) | Verktyg |
|---|---|---|
| `claude` | `noreply@anthropic\.com`, `claude\[bot\]@users\.noreply\.github\.com` | Claude Code, Claude GitHub-app |
| `copilot` | `\bcopilot@users\.noreply\.github\.com`, `^copilot autofix` | Copilot (förslag i webben, kodagenten), Copilot Autofix |
| `cursor` | `cursoragent@cursor\.com` | Cursor (agent) |
| `devin` | `devin-ai-integration\[bot\]@` | Devin |
| `codex` | `codex@openai\.com`, `chatgpt-codex-connector\[bot\]@` | OpenAI Codex |
| `google` | `gemini-code-assist\[bot\]@`, `google-labs-jules\[bot\]@` | Gemini Code Assist, Jules |
| `aider` | `@aider\.chat` | Aider |
| `amp` | `amp@ampcode\.com` | Amp |
| `other` | `factory-droid\[bot\]@`, `openhands@all-hands\.dev`, `codegen-sh\[bot\]@`, `terragon-labs\[bot\]@`, `coderabbitai\[bot\]@`, `cubic-dev-ai\[bot\]@`, `ellipsis-dev\[bot\]@`, `greptile-apps\[bot\]@`, `qodo-merge-pro\[bot\]@` | övriga agenter och AI-granskningsbottar vars förslag committas |

Inte AI: `dependabot`, `renovate`, `github-actions`, `pre-commit-ci`, `autofix-ci` och andra regelbaserade bottar.
Namnmönster som `cursor` eller `devin` utan e-post används inte, eftersom människor heter så.

### Mått (per vecka, ur urvalstimmarna)

| Nyckel | Mått | Enhet |
|---|---|---|
| `g3_gh_ai_coauthor_share_w` | (a) AI-medförfattade commits / alla commits | % |
| `g3_gh_ai_coauthor_repos_w` | (b) antal olika repon (`repo.id`) med minst en AI-medförfattad commit | repon per urvalsvecka (7 timmar) |
| `g3_gh_push_commits_w` | (c) antal commits (nämnaren) | commits per urvalsvecka (7 timmar) |
| `g3_gh_ai_coauthor_share_<grupp>_w` | (a) per grupp, för `claude`, `copilot`, `cursor`, `devin`, `codex`, `google`, `aider`, `amp`, `other` | % |

(b) och (c) är urvalsnivåer, inte veckototaler. Ungefärlig veckototal = värdet × 168 / antal timmar, men det
räknas inte här. Andelarna påverkas inte av hur många timmar som är med.

### known_from och revidering

- GH Archive skriver varje timfil en gång, cirka en timme efter timmens slut, och skriver inte om den.
  Avbrott ger saknade eller ofullständiga timmar, och de syns som färre mätbara timmar. Veckans sista urvalstimme
  (sön 12) finns före måndagen. `lag_days = 2` (veckans slut + 2 dagar), med marginal.
- All historik räknades 2026-11-23 och får `source="backfill"`. Läckagerisken är liten: filerna är oförändrade
  sedan publiceringen. Det som är valt i efterhand är identitetslistan (verktyg som inte fanns än ger noll).
- Lagring: veckoaggregaten ligger i `curated/github_ai_gharchive.csv` (bara siffror, aggregat av publik data) och
  byggs om med `python -m ai_tracker.sources.gharchive build`. Timresultaten cachas under
  `data/raw/gharchive/hours_v2/` (v1 hade ett fel i förfiltret som missade `Co-Authored-By` med stora bokstäver;
  hittades av testerna innan något veckovärde lästes, och v1-cachen raderades).

### Kända skevheter

- Bara publika repon, och bara push till GitHub (inte GitLab eller interna servrar).
- **Trailern beror på verktygets standardinställning.** När ett verktyg börjar eller slutar skriva trailer som
  standard blir det ett mätbrott, inte en förändring i användning. Kända datum:
  - Claude Code: skriver `Co-Authored-By: Claude <noreply@anthropic.com>` som standard sedan lanseringen
    (förhandsversion 2025-02-24). Den kan stängas av (`includeCoAuthoredBy`). Senare versioner skriver
    modellnamnet i namnet ("Claude Opus 4.5"), men e-posten är densamma.
  - Copilot: trailern `Copilot <…+Copilot@users.noreply.github.com>` kommer när förslag från Copilot godtas på
    github.com och från kodagenten (publik förhandsversion 2025-05-19). Copilot i editorn skriver ingen trailer,
    så den största delen av Copilot-användningen syns inte.
  - Cursor: `Cursor Agent <cursoragent@cursor.com>` från bakgrundsagenterna (2025). Cursor i editorn skriver
    ingen trailer.
  - Aider: skrev länge attribution i författarnamnet ("(aider)"), inte som trailer. Trailern kom som tillval
    2025 och fångas bara därefter.
  - Codex, Devin, Jules: committar ofta som egen författare (bot-konto) i stället för trailer. Det räknas inte.
- Verktyg som inte skriver trailer (de flesta editortillägg) syns inte alls. Måttet är en undre gräns för
  agentisk och delvis agentisk kod, inte för all AI-assisterad kod.
- Stora repon och automatiserade konton kan dominera en enskild timme. (b) är mindre känsligt för det än (a).
- 20-commitstaket per push gör att stora pushar underrepresenteras i båda leden.

## Del B: GitHubs commit-sökning, löpande från 2024-01-01

GH Archive kan inte föra måtten vidare, så den löpande serien kommer från GitHubs sök-API
(`GET https://api.github.com/search/commits`), som indexerar commit-meddelanden på standardgrenen i publika repon.
Endast `total_count` används. Inga commits eller texter sparas.

- **Vecka:** måndag–söndag, `committer-date:YYYY-MM-DD..YYYY-MM-DD` (UTC).
- **Nämnare:** `q = committer-date:<mån>..<sön>`.
- **Täljare per grupp** (fras i meddelandet + datumvillkoret):
  - `claude`: `"noreply@anthropic.com"`
  - `copilot`: `"Copilot@users.noreply.github.com"`
  - `cursor`: `"cursoragent@cursor.com"`
  - totalen `any`: `"noreply@anthropic.com" OR "Copilot@users.noreply.github.com" OR "cursoragent@cursor.com" OR
    "devin-ai-integration" OR "codex@openai.com"` (sökningen tillåter högst fem operatorer).
- **Mått:**

| Nyckel | Mått | Enhet |
|---|---|---|
| `g3_ghs_ai_coauthor_share_w` | `any` / nämnaren | % |
| `g3_ghs_ai_coauthor_share_{claude,copilot,cursor}_w` | grupp / nämnaren | % |
| `g3_ghs_commits_w` | nämnaren | commits per vecka (sökindex) |
| `g3_ghs_ai_coauthor_commits_w` | `any` | commits per vecka (sökindex) |

  Antal repon (b) går inte att få ur sökningens totaler och saknas i del B.
- **Skillnader mot del A:** bara standardgrenen, sökindexets täckning (inte dokumenterad), frasträff var som helst
  i meddelandet (i praktiken trailern), och datum = committer-datum (kan sättas fritt av klienten).
  Del A och del B är **olika mått** och skarvas inte.
- **known_from och revidering:** värdena ändras i efterhand: commits med gammalt datum mergas senare, repon
  raderas eller blir privata, och indexet byggs om. Varje körning frågar om de **8 senaste hela veckorna**. En ny
  vecka får `known_from` = min(veckans slut + 1 dag, hämtdatum), och ett ändrat värde blir en revidering med
  hämtdatumet. Första hämtningen (2024-01 till nu) är dagens version och får `source="backfill"`: där läcker
  senare revideringar in (överlevande repon, sena merges). Detta ska beaktas i varje backtest.
- **Bakåtdaterade commits (upptäckt vid datakontrollen 2026-11-23):** committer-datumet sätts av klienten.
  Träffar för `"noreply@anthropic.com"` med datum i januari 2024, före Claude Code, är bakåtdaterade commits
  (till exempel repon som "målar" GitHubs aktivitetsgraf, och en trailer som namnger "Claude Opus 5.5" med datum
  2024-01-06). Sökningen kan inte filtrera på pushtid. Backfillen av del B är därför **inte** en tidsserie över
  när commits skrevs, utan dagens index sorterat på påstått datum. Bara veckor som hämtas löpande (de 8 senaste,
  och deras revideringar) har ett meningsfullt `known_from`. Del A (pushtid i GH Archive) har inte problemet.
- **Hämtning:** i den schemalagda veckohämtningen (`fetch-weekly.yml`, `GITHUB_TOKEN`). Ett misslyckat anrop
  försöks igen med väntan. En vecka utan svar lämnas ute och frågas igen nästa körning, och bara nya veckor som
  hänger ihop med de lagrade returneras, så att lagret aldrig får hål (lagrets kontroll `no_gaps`).

### Ändringar av del B efter registreringen (2026-11-23, före första hela hämtningen, inga värden analyserade)

1. **Takt:** GitHubs sekundära gräns för sökning slog till redan vid cirka 10 frågor per minut från sessionen
   (anonymt via proxyn, "You have exceeded a secondary rate limit"). Frågorna går nu med minst 6 sekunders
   mellanrum i veckohämtningen, och en sekundär 403 ger 90 s × försök i väntan.
2. **Kall start i Actions:** högst 40 veckor (200 frågor, cirka 20 minuter) per körning, nyaste först. En tom
   cache i Actions fyller alltså historiken bakåt under fem veckokörningar. Hela backfillen (151 veckor) körs en
   gång med jobbet `github_search_counts` (`job.yml`, `GITHUB_TOKEN`, 2,5 s mellanrum) och laddas in i spårets tabell.
3. Startveckan (2024-01-01), frågorna och måtten är oförändrade.

## Budget (BigQuery)

BigQuery-kvoten (1 TB per månad, delad med B1) används inte av spåret. GH Archive i BigQuery är inte partitionerat
på timme, och `payload` (en JSON-sträng med commit-meddelandena) måste läsas helt för varje dag. Torrkörningen och
siffrorna för en dag står under "Körningar". Samma timurval via timfilerna kostar 0 byte i BigQuery, och
nedladdningen sker i sessionen eller i Actions.

## Körningar

(fylls i nedan med datum, byte och tid)
