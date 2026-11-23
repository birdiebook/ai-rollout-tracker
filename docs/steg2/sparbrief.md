# Gemensam brief för spår i steg 2

Gäller alla spår i våg 1–4. Spårets egen brief anger leveransen.

- **Arbetskopia:** bara din egen worktree under `/home/user/wt/<spår>` (skapad med `scripts/new_track.sh`). Committa på
  din gren. Pusha inte, och rör inte `main` eller andra arbetskopior.
- **Data:** `AI_TRACKER_SHARED_DATA` i `.env.local` pekar på den delade bastabellen. `observations.load()` ger bas ∪ dina
  rader, och skrivningar går bara till din `data/`. Använd `--rebuild` för serier du bygger om. Data committas aldrig.
- **Läs först:** `CLAUDE.md`, `docs/steg2/plan.md` (ditt spår och dess beroenden), `docs/mattregister.md` (allt under
  "Steg 2"), `src/ai_tracker/{catalog,observations,publication,warehouse,http,config}.py` och `src/ai_tracker/series/__init__.py`.
- **Källor:** en modul per källa (`sources/<källa>.py` och `series/<källa>.py`). HTTP via `ai_tracker.http` med ärlig
  User-Agent. SEC kräver `SEC_USER_AGENT` från `.env`, och värdet skrivs aldrig ut eller committas. Ingen
  webbläsarimitation, och skydd mot botar kringgås aldrig. Värdar som proxyn nekar listas i rapporten.
- **known_from:** dokumentets eller publiceringens faktiska datum. Är det osäkert väljs ett senare datum, aldrig ett
  tidigare. Revideringar blir nya versioner. Bakåtfylld historik märks `source="backfill"`.
- **Licens:** citera villkoren. `publish=True` bara med kontrollerad licens. Från dokument publiceras bara siffror med
  källhänvisning, aldrig text. LLM-extraherade värden sparas med URL eller accession, plats och SHA-256 av meningen.
  Meningen själv sparas bara i `data/raw`.
- **Ingen analys:** inga takter, tillväxttal, korrelationer eller jämförelser mellan prognos och utfall. Mått och
  kärnserier registreras först (grind G-A). Kontroller av datakorrekthet (nivåer mot rapporterade siffror) är tillåtna.
- **Klart när:** tester med fixtures utan nätverk, riktig hämtning körd, `python -m ai_tracker.warehouse` grön (alla
  kontroller inklusive aktualitet) och hela pytest grön. Dokumentationen ligger i `docs/kallor/<källa>.md` på svenska.
  Gemensamma loggar (`docs/beslutslogg.md`, `docs/agentkalibrering.md`) lämnas åt orkestreraren.
- **Slutrapport** (kort, engelska): serier med historik, regel för `known_from` med belägg, licens, BLOCKED och
  nycklar som behövs, väggtid och ungefärligt antal verktygsanrop.

## Källor som kräver hemligheter (BigQuery, Cloudflare)

Hemligheterna finns bara i GitHub Actions. Sessionen har ingen GCP-inloggning och ingen Cloudflare-token.

- **BigQuery** (nyckelfritt via OIDC, sandbox utan betalkonto, 1 TB frågor per månad delat mellan alla spår):
  lägg SQL i `sql/bq/<jobb>.sql` med raden `-- max_gb: N` och kör `.github/workflows/bq.yml`
  (workflow_dispatch, input `job`). Workflowen gör först en torrkörning och vägrar över taket. Kör alltid en
  torrkörning med litet tak först, och logga varje jobbs uppskattade och faktiska byte i `docs/kallor/<källa>.md`.
  Läs bara de kolumner och partitioner som behövs.
- **Cloudflare med flera** (Python): modul `src/ai_tracker/jobs/<jobb>.py` med `run(out_dir)`, körs med
  `.github/workflows/job.yml` (input `job`). Där finns `CLOUDFLARE_API_TOKEN` och GCP-inloggning.
- **Köra på din gren:** pusha grenen (`git -c push.negotiate=true push -u origin <gren>`), dispatcha workflowen med
  `ref` = din gren (GitHub MCP: `mcp__github__actions_run_trigger`, ladda med ToolSearch). Följ körningen med
  `mcp__github__actions_get` och läs loggen med `mcp__github__get_job_logs`.
- **Hämta resultatet:** `mcp__github__actions_get` med `download_workflow_run_artifact` ger en tillfällig URL. Hämta den
  med curl (blob-värdarna `productionresultssa*.blob.core.windows.net` är tillåtna) till `data/raw/<källa>/`.
- **Bara aggregat:** artefakter i ett publikt repo är publika, så resultaten får bara vara aggregat av publik data.
- **Driften:** serien hämtas i den schemalagda driften genom att samma jobb körs i Actions (lägg ett steg i
  `fetch-weekly.yml` eller `collect-weekly.yml` med OIDC-behörighet `id-token: write`).
