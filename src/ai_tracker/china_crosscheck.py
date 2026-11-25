"""Cross-check of the CN1 quarterly series against the annual figures in the 20-F XBRL (register entry 2026-11-25 CN1).

(a) Alibaba's cloud segment: the sum of four fiscal quarters (April - March) of each era series against the
    dimensional fact Revenues x StatementBusinessSegmentsAxis = <cloud member> in each 20-F's XBRL instance (the
    member is CloudComputingSegmentMember to the FY2023 20-F, CloudIntelligenceGroupMember from FY2024). Same
    definition: expected within 4 MRMB (rounding).
(b) Capex: the sum of four quarters against the 20-F's cash-flow line: Alibaba
    PaymentsToAcquireLandUseRightsPropertyAndEquipment (instance), Baidu PaymentsToAcquirePropertyPlantAndEquipment
    (companyfacts, CNY). Alibaba's own line excludes land use rights and office campus construction, so a difference
    is expected; the ratio is reported and never used to adjust anything.

    python -m ai_tracker.china_crosscheck

Network: the 20-F instances (5-8 MB each, cached as raw copies) and Baidu's companyfacts. Nothing is written.
"""

from __future__ import annotations

import json

import pandas as pd

from ai_tracker.sources import china_sec, sec, sec_segment

CLOUD_MEMBERS = ("CloudComputingSegmentMember", "CloudIntelligenceGroupMember")
BABA_CAPEX = "PaymentsToAcquireLandUseRightsPropertyAndEquipment"
BIDU_CAPEX = "PaymentsToAcquirePropertyPlantAndEquipment"
SINCE_20F = "2019-01-01"
ROUNDING = 4.0  # MRMB: four quarters, each rounded to millions


def latest(df: pd.DataFrame) -> pd.Series:
    """The latest vintage per period (period -> value)."""
    return df.sort_values("known_from").groupby("period")["value"].last()


def fiscal_sum(values: pd.Series, end: pd.Timestamp) -> float | None:
    """Sum of the four calendar quarters ending at `end`, or None if one is missing."""
    q = pd.Timestamp(end).to_period("Q-DEC")
    qs = [str(q - k) for k in range(4)]
    return float(values[qs].sum()) if all(p in values.index for p in qs) else None


def baba_annual() -> list[tuple[str, str, str, pd.Timestamp, float]]:
    """(filed, accession, kind, fiscal year end, MRMB) of the cloud segment and capex facts in Alibaba's 20-Fs."""
    out = []
    for f in china_sec.filings(china_sec.CIKS["baba"], form_prefix="20-F", since=SINCE_20F):
        index = json.loads(china_sec.cached_get(f.url("index.json")))
        name = sec_segment.instance_name([it["name"] for it in index["directory"]["item"]])
        if name is None:
            continue
        seen = set()
        for d in sec_segment.parse_instance(china_sec.cached_get(f.url(name)), {"Revenues", BABA_CAPEX}):
            if d.unit != "CNY" or (d.end - d.start).days < 360:
                continue
            dims = set(d.dims) - sec_segment.NEUTRAL_DIMS
            if d.concept == "Revenues" and len(dims) == 1:
                axis, member = next(iter(dims))
                kind = f"cloud:{member}" if axis == "StatementBusinessSegmentsAxis" and member in CLOUD_MEMBERS else ""
            elif d.concept == BABA_CAPEX and not dims:
                kind = "capex"
            else:
                kind = ""
            if kind and (kind, d.end) not in seen:
                seen.add((kind, d.end))
                out.append((f.filed, f.accession, kind, d.end, d.value / 1e6))
    return out


def bidu_annual() -> list[tuple[str, str, str, pd.Timestamp, float]]:
    cf = sec.companyfacts(china_sec.CIKS["bidu"])
    out = {}
    for v in cf["facts"]["us-gaap"][BIDU_CAPEX]["units"].get("CNY", []):
        if v.get("form", "").startswith("20-F") and v["start"][5:] == "01-01" and v["end"][5:] == "12-31":
            key = v["end"]
            if key not in out or v["filed"] > out[key][0]:
                out[key] = (v["filed"], v["accn"], "capex", pd.Timestamp(v["end"]), v["val"] / 1e6)
    return sorted(out.values())


def run() -> pd.DataFrame:
    rows = []
    cloud = {e.key: latest(china_sec.series("baba", "rev_cloud", e.key))
             for e in china_sec.ERAS[("baba", "rev_cloud")] if e.key}
    capex = {"capex_baba_v1": latest(china_sec.series("baba", "capex", "capex_baba_v1")),
             "capex_baba_v2": latest(china_sec.series("baba", "capex", "capex_baba_v2"))}
    for filed, acc, kind, end, annual in baba_annual():
        for key, values in (cloud if kind.startswith("cloud") else capex).items():
            s = fiscal_sum(values, end)
            if s is not None:
                rows.append(("baba", kind, str(end.date()), filed, acc, key, annual, s, s - annual, s / annual))
    bidu = latest(china_sec.series("bidu", "capex_total", "capex_bidu"))
    for filed, acc, kind, end, annual in bidu_annual():
        s = fiscal_sum(bidu, end)
        if s is not None:
            rows.append(("bidu", kind, str(end.date()), filed, acc, "capex_bidu", annual, s, s - annual, s / annual))
    return pd.DataFrame(rows, columns=["company", "kind", "fy_end", "filed_20f", "accession", "series", "annual_20f",
                                       "sum_quarters", "diff", "ratio"])


def main() -> None:
    pd.set_option("display.width", 200)
    res = run()
    print(res.to_string(index=False, float_format=lambda x: f"{x:,.3f}" if abs(x) < 10 else f"{x:,.0f}"))


if __name__ == "__main__":
    main()
