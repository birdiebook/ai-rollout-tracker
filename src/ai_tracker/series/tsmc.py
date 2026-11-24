"""TSMC monthly revenue (G6, nowcast target N2), from TSMC's SEC 6-K filings. See docs/kallor/tsmc_asien.md."""

from __future__ import annotations

from functools import lru_cache

from ai_tracker.catalog import Spec
from ai_tracker.sources import tsmc_sec

SEC_DISSEMINATION = ("SEC: \"Information presented on sec.gov is considered public information and may be copied "
                     "or further distributed by users of the web site without the SEC's permission. Please consider "
                     "appropriate citation to the SEC as the source.\" (sec.gov/privacy, Website Dissemination). ")


def sixk_license(filer: str, extra: str = "") -> str:
    """Licence text for figures extracted from a foreign issuer's 6-K on EDGAR, naming the filer (TSMC, ASML)."""
    return (f"{SEC_DISSEMINATION}Statutory filing by {filer}; only extracted figures with source citation are "
            f"published." + (f" {extra}" if extra else ""))


LICENSE = sixk_license("TSMC", "TSMC IR terms not readable (403)")


@lru_cache(maxsize=1)
def _reports():
    return tuple((f.filed, r) for f, r in tsmc_sec.reports())


def _fetch(basis: str):
    def fetch():
        return tsmc_sec.vintages(list(_reports()), basis)
    return fetch


SPECS = [
    Spec(
        key="tsmc_revenue_m", branch="G6", label="TSMC:s månadsintäkt (koncern)", unit="mn TWD", freq="M",
        source="SEC EDGAR, TSMC Form 6-K (månadsrapport om intäkter)", fetch=_fetch("consolidated"),
        lag_days=10, license=LICENSE, revised=True, publish=True,
        question="Hur snabbt växer världens största kontraktstillverkare av AI-chip, månad för månad?",
        note="Release-daterad: known_from = 6-K:ns inlämningsdatum (dag 6–16 i månaden efter, median 10). "
             "Från 2006-04. Jämförelsetal som räknats om (t.ex. IFRS 2013) sparas som nya vintages. "
             "Fram till 2012 enligt R.O.C. GAAP, från 2013 IFRS.",
    ),
    Spec(
        key="tsmc_revenue_parent_m", branch="G6", label="TSMC:s månadsintäkt (moderbolag, upphörd 2012)",
        unit="mn TWD", freq="M", source="SEC EDGAR, TSMC Form 6-K (månadsrapport om intäkter)",
        fetch=_fetch("unconsolidated"), lag_days=10, license=LICENSE, revised=True, publish=True,
        question="Längre historik (från 2001-10) för TSMC:s intäkt, innan koncernsiffran fanns.",
        closed=True,
        note="Avslutad: moderbolagets intäkt rapporteras inte efter 2012-12 (IFRS). "
             "Moderbolaget (unconsolidated), R.O.C. GAAP. "
             "2001-10–2002-09 kommer bara från jämförelsetal i rapporter ett år senare, och har den senare "
             "inlämningsdagen som known_from.",
    ),
]
