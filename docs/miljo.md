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
productionresultssa32.blob.core.windows.net
```

Värdar som medvetet inte finns med: Anthropics webbplatser (pausade enligt beslut 2026-11-23), Kalshi (villkoren
förbjuder lagring), vast.ai (villkoren förbjuder insamling) och de svenska källorna för kpif-nowcast.

## 2. Miljövariabler

| Namn | Värde |
|---|---|
| `SEC_USER_AGENT` | `ai-rollout-tracker` följt av din kontaktadress (samma som Actions-secreten) |
| `GCP_PROJECT_ID` | redan inlagd |
| `CLOUDFLARE_API_TOKEN` | redan inlagd (används bara i Actions) |
| `DATA_KEY` | se avsnitt 4 (när datasnapshoten är byggd) |

## 3. Setup-skript

```bash
#!/bin/bash
if [ -d ai-rollout-tracker ]; then (cd ai-rollout-tracker && python -m pip install -q -r ci/requirements.txt); fi
exit 0
```

## 4. Data i nya sessioner

Data committas aldrig. En ny session bygger observationstabellen med `python -m ai_tracker.observations` (cirka 1–2
timmar, eftersom vissa källor har hastighetsgränser), eller hämtar den krypterade veckosnapshoten från Actions när den
finns: `python -m ai_tracker.datasnapshot fetch` med `DATA_KEY` som miljövariabel och samma värde som
GitHub-secreten `DATA_KEY`. Snapshoten är krypterad, eftersom artefakter i ett publikt repo är publika och flera
serier inte får vidarepubliceras.
