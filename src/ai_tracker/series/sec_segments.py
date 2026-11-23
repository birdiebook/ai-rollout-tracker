"""SEC EDGAR XBRL instances: quarterly segment / product-line revenue for AI and cloud monetisation (G4).

AWS, Google Cloud, Microsoft Intelligent Cloud (and its successors), Microsoft Cloud, Server products
and cloud services, Azure, Nvidia Data Center and Oracle cloud. Release-dated: known_from = filing
date of the 10-Q/10-K, every filing a vintage. Extraction and definition-break detection are in
ai_tracker.sources.sec_segment, quarter and vintage logic in ai_tracker.sources.sec.

Definition breaks are declared per line. A line is split at each declared break into separate series
(one key per definition), never spliced. If the detected breaks differ from the declared ones (a new
re-segmentation), the fetch fails instead of silently mixing definitions: review, then declare the
break and add a key. Members, breaks and checks: docs/kallor/sec_segment.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series.sec import LICENSE
from ai_tracker.sources import sec, sec_segment

SOURCE = "SEC EDGAR XBRL instances (segment dimensions)"
REVENUE = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet")
SEG, PROD = "StatementBusinessSegmentsAxis", "ProductOrServiceAxis"
PROD2 = "ProductsOrServicesSecondaryCategorizationAxis"

AMZN, GOOGL, MSFT, NVDA, ORCL = 1018724, 1652044, 789019, 1045810, 1341439
# First filing date scanned per company (one shared download per company).
SINCE = {AMZN: "2015-01-01", GOOGL: "2020-01-01", MSFT: "2015-07-01", NVDA: "2018-01-01", ORCL: "2022-06-01"}


@dataclass(frozen=True)
class Line:
    """One reported revenue line; `keys` has one series key per definition regime (len(breaks) + 1)."""

    keys: tuple[str, ...]
    cik: int
    members: tuple[tuple[str, str], ...]  # alternative (axis, member) names, see sec_segment.member_facts
    label: str
    breaks: tuple[str, ...] = ()  # declared definition breaks (filing dates)
    regime_notes: tuple[str, ...] = ()
    lag_days: int = 25


LINES = [
    Line(("rev_aws",), AMZN, ((SEG, "AmazonWebServicesSegmentMember"), (PROD, "AmazonWebServicesMember")),
         "AWS (Amazon)"),
    Line(("rev_google_cloud",), GOOGL, ((SEG, "GoogleCloudMember"), (SEG, "GoogleCloudSegmentMember")),
         "Google Cloud (Alphabet)"),
    Line(("rev_msft_intelligent_cloud_fy16", "rev_msft_intelligent_cloud_fy18", "rev_msft_intelligent_cloud_fy25"),
         MSFT, ((SEG, "IntelligentCloudMember"),), "Intelligent Cloud (Microsoft)",
         breaks=("2017-10-26", "2024-10-30"),
         regime_notes=("Segmentdefinition FY2016-FY2017 (inlämnat t.o.m. 2017-08).",
                       "Omräknad segmentdefinition FY2018-FY2024 (inlämnat 2017-10 till 2024-07).",
                       "Omräknad segmentdefinition FY2025-FY2026 (inlämnat från 2024-10); segmentet ersattes FY2027.")),
    Line(("rev_msft_agents_infra",), MSFT, ((SEG, "AgentsAndInfraMember"),),
         "Agents and Infra (Microsoft, segment från FY2027)"),
    Line(("rev_msft_cloud",), MSFT, ((PROD2, "MicrosoftCloudMember"),), "Microsoft Cloud"),
    Line(("rev_msft_server_cloud_fy18", "rev_msft_server_cloud_fy25"), MSFT,
         ((PROD, "ServerProductsAndCloudServicesMember"), (PROD, "ServerProductsAndToolsMember")),
         "Server products and cloud services (Microsoft)", breaks=("2024-10-30",),
         regime_notes=("Definition före omräkningen FY2025 (inlämnat t.o.m. 2024-07).",
                       "Omräknad definition FY2025-FY2026 (inlämnat från 2024-10); raden ersattes FY2027.")),
    Line(("rev_msft_azure",), MSFT, ((PROD, "AzureMember"),), "Azure (Microsoft, egen rad från FY2027)"),
    Line(("rev_nvda_datacenter",), NVDA, ((PROD, "DataCenterMember"), (PROD, "DatacenterMember")),
         "Data Center (Nvidia)"),
    # Oracle's fiscal quarters end in Nov/Feb/May/Aug: Sep-Nov maps to calendar Q4 (midpoint) and is
    # filed ~10 days after it ends, i.e. before the calendar quarter's end; lag_days -31 allows that.
    Line(("rev_orcl_cloud",), ORCL, ((PROD, "CloudRevenuesMember"), (PROD, "CloudServicesMember")),
         "Cloud (IaaS + SaaS, Oracle)", lag_days=-31),
    Line(("rev_orcl_oci",), ORCL, ((PROD, "CloudInfrastructureMember"),), "Cloud Infrastructure (OCI, Oracle)",
         lag_days=-31),
]


class DefinitionBreakError(ValueError):
    """Detected definition breaks differ from the declared ones: review before the series is used."""


@lru_cache(maxsize=None)
def line_facts(line: Line) -> list[sec.Fact]:
    return sec_segment.member_facts((line.cik,), SINCE[line.cik], REVENUE, line.members)


def checked_regimes(line: Line, facts: list[sec.Fact]) -> list[list[sec.Fact]]:
    """Facts per definition regime; raises DefinitionBreakError if detection disagrees with `line.breaks`."""
    found = [str(d.date()) for d in sec_segment.definition_breaks(facts)]
    if found != list(line.breaks):
        raise DefinitionBreakError(f"{line.keys[0]}: detected definition breaks {found}, declared "
                                   f"{list(line.breaks)}; review and declare (docs/kallor/sec_segment.md)")
    return sec_segment.regimes(facts, [pd.Timestamp(b) for b in line.breaks])


@lru_cache(maxsize=None)
def line_series(line: Line) -> tuple[pd.DataFrame, ...]:
    """Release-dated quarterly rows (MUSD) per definition regime, each without gaps."""
    return tuple(sec.contiguous_tail(sec.vintages([reg])) for reg in checked_regimes(line, line_facts(line)))


def _fetch(line: Line, i: int):
    def fetch() -> pd.DataFrame:
        return line_series(line)[i][["period", "value", "known_from"]].copy()

    return fetch


def _spec(line: Line, i: int) -> Spec:
    members = ", ".join(f"{a}={m}" for a, m in line.members)
    note = f"Medlemmar: {members}."
    if line.regime_notes:
        note += " " + line.regime_notes[i]
    return Spec(key=line.keys[i], branch="G4", label=f"Segmentintäkter, {line.label}", unit="MUSD", freq="Q",
                source=SOURCE, fetch=_fetch(line, i), lag_days=line.lag_days, license=LICENSE, revised=True,
                publish=True, question="Hur snabbt växer de intäkter som AI- och molninvesteringarna ska bära?",
                note=note)


SPECS = [_spec(line, i) for line in LINES for i in range(len(line.keys))]
