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
