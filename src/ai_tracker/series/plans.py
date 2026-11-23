"""Multi-year plans (step 2, track D1, program D): capex plans beyond the current year, announced infrastructure
investments, data-center power capacity (targets and reported levels), backlog outside A1's company-total RPO and
infrastructure commitments.

Agent-extracted from SEC filings and microsoft.com call pages, stored as numbers and references only in
curated/plans.csv (ai_tracker.sources.plans; coding rules in docs/kallor/planer.md). Not reviewed yet (R5):
publish=False. Plans are known before their period ends, so lag_days is negative for them; reported levels (ASOF)
are dated by the document that first states them.
"""

from __future__ import annotations

from ai_tracker.sources import plans

SPECS = plans.specs()
