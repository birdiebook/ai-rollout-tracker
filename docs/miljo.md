# Molnmiljön "ai-rollout-tracker"

Allt en ny session behöver. Fylls i en gång i miljöns inställningar (miljömenyn i sessionens titelrad → Edit).

## 1. Tillåtna värdar (Network access: Limited, package managers och MCP-servrar på)

Klistra in en per rad:

```
data.sec.gov
www.sec.gov
www.census.gov
api.census.gov
www.bea.gov
apps.bea.gov
api.bls.gov
www.bls.gov
download.bls.gov
www.federalreserve.gov
alfred.stlouisfed.org
api.stlouisfed.org
fred.stlouisfed.org
ec.europa.eu
api.scb.se
historical.api.jobtechdev.se
www.eia.gov
eia.gov
api.eia.gov
emp.lbl.gov
www.pjm.com
dataminer2.pjm.com
www.ercot.com
epoch.ai
metr.org
huggingface.co
us.aws.cdn.hf.co
datasets-server.huggingface.co
export.arxiv.org
lmarena.ai
artificialanalysis.ai
openrouter.ai
api.npmjs.org
pypistats.org
wikimedia.org
api.wikimedia.org
api.cloudflare.com
data.gharchive.org
bigquery.googleapis.com
oauth2.googleapis.com
www.googleapis.com
api.manifold.markets
gamma-api.polymarket.com
www.metaculus.com
openapi.twse.com.tw
mops.twse.com.tw
ecos.bok.or.kr
www.microsoft.com
productionresultssa0.blob.core.windows.net
productionresultssa1.blob.core.windows.net
productionresultssa2.blob.core.windows.net
productionresultssa3.blob.core.windows.net
productionresultssa4.blob.core.windows.net
productionresultssa5.blob.core.windows.net
productionresultssa6.blob.core.windows.net
productionresultssa7.blob.core.windows.net
productionresultssa8.blob.core.windows.net
productionresultssa9.blob.core.windows.net
productionresultssa10.blob.core.windows.net
productionresultssa11.blob.core.windows.net
productionresultssa12.blob.core.windows.net
productionresultssa13.blob.core.windows.net
productionresultssa14.blob.core.windows.net
productionresultssa15.blob.core.windows.net
productionresultssa16.blob.core.windows.net
productionresultssa17.blob.core.windows.net
productionresultssa18.blob.core.windows.net
productionresultssa19.blob.core.windows.net
productionresultssa32.blob.core.windows.net
```

Artefakter laddas ned från `productionresultssa<N>.blob.core.windows.net`, och shardnumret varierar mellan artefakter
(2026-11-23 sågs 0, 1, 2, 7, 11, 15, 18 och 32). Neka-meddelandet från `datasnapshot fetch` anger värden. Lägg till
den om den saknas.

Värdar som medvetet inte finns med: Anthropics webbplatser (pausade enligt beslut 2026-11-23), Kalshi (villkoren
förbjuder lagring), vast.ai (villkoren förbjuder insamling) och de svenska källorna för kpif-nowcast.

## 2. Miljövariabler

| Namn | Värde |
|---|---|
| `SEC_USER_AGENT` | `ai-rollout-tracker` följt av din kontaktadress (samma som Actions-secreten) |
| `GCP_PROJECT_ID` | redan inlagd |
| `CLOUDFLARE_API_TOKEN` | redan inlagd (används bara i Actions) |
| `DATA_KEY` | samma värde som GitHub-secreten `DATA_KEY` (avsnitt 4). Används av `datasnapshot fetch` |

## 3. Setup-skript

```bash
#!/bin/bash
if [ -d ai-rollout-tracker ]; then (cd ai-rollout-tracker && python -m pip install -q -r ci/requirements.txt); fi
exit 0
```

## 4. Data i nya sessioner

Data committas aldrig. En ny session hämtar den krypterade veckosnapshoten från Actions (cirka en minut) i stället för
att bygga om tabellen (1–2 timmar). Snapshoten är krypterad, eftersom artefakter i ett publikt repo är publika och
flera serier inte får vidarepubliceras. Detaljer i `docs/drift.md`, avsnittet Datasnapshot.

**Engångsåtgärd för ägaren:**

1. Skapa en nyckel: `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Spara den i en
   lösenordshanterare.
2. GitHub: Settings → Secrets and variables → Actions → New repository secret, namn `DATA_KEY`.
3. Molnmiljön: lägg in samma värde som miljövariabeln `DATA_KEY` (avsnitt 2).
4. Kör `Weekly data fetch` för hand en gång (Actions → Run workflow på main), så att den första artefakten
   `data-snapshot` finns. Därefter skapas en ny varje måndag och sparas i 14 dagar.

**I en ny session** (i `/home/user/ai-rollout-tracker`, efter setup-skriptet):

```bash
cd /home/user/ai-rollout-tracker
PYTHONPATH=src python -m ai_tracker.datasnapshot fetch    # senaste data-snapshot från main → data/
PYTHONPATH=src python -m ai_tracker.warehouse             # datatester och aktualitet
PYTHONPATH=src python -m ai_tracker.observations          # valfritt: hämta det som kommit sedan måndagen
```

- Saknas `DATA_KEY` vägrar kommandot innan något laddas ned. Fel nyckel eller en skadad fil ger "authentication
  failed", och ingenting skrivs.
- Finns redan en lika ny eller nyare `data/observations.parquet` vägrar kommandot. `--force` ersätter den, och den
  gamla sparas i `data/snapshot_backups/`.
- Neka-fel för `productionresultssa<N>.blob.core.windows.net`: lägg till värden i avsnitt 1 och kör igen.
- Ingen artefakt (nyckeln saknades vid senaste körningen, eller den är äldre än 14 dagar): bygg om med
  `PYTHONPATH=src python -m ai_tracker.observations`. BigQuery- och Cloudflare-serierna kommer då bara med en
  körning i Actions.
- Spår-worktrees (`scripts/new_track.sh`) läser basen i main-utcheckningen och behöver ingen egen snapshot.
