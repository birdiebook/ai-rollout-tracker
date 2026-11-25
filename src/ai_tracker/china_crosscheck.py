"""Cross-check of the CN1 quarterly series against the annual figures in the 20-F XBRL (register entry 2026-11-25 CN1,
and its change after review R21 the same day).

(a) Alibaba's cloud segment: the sum of four fiscal quarters (April - March) of each era series against the
    dimensional fact Revenues x StatementBusinessSegmentsAxis = <cloud member> in each 20-F's XBRL instance (the
    member is CloudComputingSegmentMember to the FY2023 20-F, CloudIntelligenceGroupMember from FY2024). Check
    "segment"; on the same definition expected within 4 MRMB (rounding).
(b) Capex, on the companies' own lines (check "exact", expected within 4 MRMB):
    - capex_baba_v1: companyfacts PaymentsToAcquireOtherPropertyPlantAndEquipment + PaymentsToAcquireIntangibleAssets
      from the same 20-F, and the company's own single line in the FY2016-FY2018 20-F instances (an extension
      element, not in companyfacts; BABA_V1_LINES);
    - capex_baba_v2: companyfacts PaymentsToAcquireOtherPropertyPlantAndEquipment;
    - Baidu: companyfacts PaymentsToAcquirePropertyPlantAndEquipment (CNY).
    Alibaba's broader 20-F line PaymentsToAcquireLandUseRightsPropertyAndEquipment (with land use rights and office
    campus construction) is reported as a ratio (check "ratio") only for a series and year with no exact line; it is
    never used to adjust anything.

    python -m ai_tracker.china_crosscheck

Network: the 20-F instances (5-8 MB each, cached as raw copies) and both companyfacts. Nothing is written.
"""

from __future__ import annotations

import json

import pandas as pd

from ai_tracker.sources import china_sec, sec, sec_segment

CLOUD_MEMBERS = ("CloudComputingSegmentMember", "CloudIntelligenceGroupMember")
BABA_CAPEX = "PaymentsToAcquireLandUseRightsPropertyAndEquipment"  # broader than both series: ratio only
BABA_PPE = "PaymentsToAcquireOtherPropertyPlantAndEquipment"  # companyfacts, FY2017-FY2020
BABA_INTANGIBLES = "PaymentsToAcquireIntangibleAssets"
# The company's own line of PP&E and intangible assets (licensed copyrights from FY2017) in the 20-F instances of
# FY2016, FY2017 and FY2018: capex_baba_v1's definition
BABA_V1_LINES = ("PaymentsToAcquireOtherPropertyPlantAndEquipmentIntangibleAssets",
                 "PaymentsToAcquireOtherPropertyEquipmentIntangibleAssetsAndLicensedCopyrightsOfVideoContent",
                 "PaymentsToAcquireOtherPropertyEquipmentIntangibleAssetsAndLicensedCopyrights")
BIDU_CAPEX = "PaymentsToAcquirePropertyPlantAndEquipment"
SINCE_20F = "2016-01-01"
ROUNDING = 4.0  # MRMB: four quarters, each rounded to millions
# kind -> the capex series on that line's definition (an exact check); BABA_CAPEX ("capex") is the ratio for both
EXACT_CAPEX = {"cf:ppe+intangibles": "capex_baba_v1", "v1line": "capex_baba_v1", "cf:ppe": "capex_baba_v2"}


def latest(df: pd.DataFrame) -> pd.Series:
    """The latest vintage per period (period -> value)."""
    return df.sort_values("known_from").groupby("period")["value"].last()


def fiscal_sum(values: pd.Series, end: pd.Timestamp) -> float | None:
    """Sum of the four calendar quarters ending at `end`, or None if one is missing."""
    q = pd.Timestamp(end).to_period("Q-DEC")
    qs = [str(q - k) for k in range(4)]
    return float(values[qs].sum()) if all(p in values.index for p in qs) else None


def baba_annual() -> list[tuple[str, str, str, pd.Timestamp, float]]:
    """(filed, accession, kind, fiscal year end, MRMB) of the cloud segment and capex facts in Alibaba's 20-Fs.

    kind: "cloud:<member>", "v1line:<concept>" (BABA_V1_LINES) or "capex" (BABA_CAPEX).
    """
    out = []
    for f in china_sec.filings(china_sec.CIKS["baba"], form_prefix="20-F", since=SINCE_20F):
        index = json.loads(china_sec.cached_get(f.url("index.json")))
        name = sec_segment.instance_name([it["name"] for it in index["directory"]["item"]])
        if name is None:
            continue
        seen = set()
        concepts = {"Revenues", BABA_CAPEX, *BABA_V1_LINES}
        for d in sec_segment.parse_instance(china_sec.cached_get(f.url(name)), concepts):
            if d.unit != "CNY" or (d.end - d.start).days < 360:
                continue
            dims = set(d.dims) - sec_segment.NEUTRAL_DIMS
            if d.concept == "Revenues" and len(dims) == 1:
                axis, member = next(iter(dims))
                kind = f"cloud:{member}" if axis == "StatementBusinessSegmentsAxis" and member in CLOUD_MEMBERS else ""
            elif d.concept == BABA_CAPEX and not dims:
                kind = "capex"
            elif d.concept in BABA_V1_LINES and not dims:
                kind = f"v1line:{d.concept}"
            else:
                kind = ""
            if kind and (kind, d.end) not in seen:
                seen.add((kind, d.end))
                out.append((f.filed, f.accession, kind, d.end, d.value / 1e6))
    return out


def _fiscal_facts(cf: dict, concept: str) -> dict[tuple[str, str], tuple[str, float]]:
    """(fiscal year end, accession) -> (filed, MRMB) of one CNY concept for Alibaba's fiscal years (April - March)."""
    units = cf.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {})
    out = {}
    for v in units.get("CNY", []):
        if (str(v.get("form", "")).startswith("20-F") and str(v.get("start", ""))[5:] == "04-01"
                and v["end"][5:] == "03-31"):
            out[(v["end"], v["accn"])] = (v["filed"], v["val"] / 1e6)
    return out


def baba_companyfacts() -> list[tuple[str, str, str, pd.Timestamp, float]]:
    """(filed, accession, kind, fiscal year end, MRMB) of Alibaba's capex lines in companyfacts.

    "cf:ppe" = BABA_PPE (capex_baba_v2's definition); "cf:ppe+intangibles" = BABA_PPE + BABA_INTANGIBLES from the
    same 20-F (capex_baba_v1's). Per year the latest 20-F that has every part.
    """
    cf = sec.companyfacts(china_sec.CIKS["baba"])
    ppe, intangibles = _fiscal_facts(cf, BABA_PPE), _fiscal_facts(cf, BABA_INTANGIBLES)
    out = []
    for kind, parts in (("cf:ppe", (ppe,)), ("cf:ppe+intangibles", (ppe, intangibles))):
        best: dict[str, tuple[str, str, float]] = {}
        for (end, accn), (filed, _val) in ppe.items():
            if all((end, accn) in p for p in parts) and (end not in best or filed > best[end][0]):
                best[end] = (filed, accn, sum(p[(end, accn)][1] for p in parts))
        out += [(filed, accn, kind, pd.Timestamp(end), val) for end, (filed, accn, val) in best.items()]
    return sorted(out)


def bidu_annual() -> list[tuple[str, str, str, pd.Timestamp, float]]:
    cf = sec.companyfacts(china_sec.CIKS["bidu"])
    out = {}
    for v in cf["facts"]["us-gaap"][BIDU_CAPEX]["units"].get("CNY", []):
        if v.get("form", "").startswith("20-F") and v["start"][5:] == "01-01" and v["end"][5:] == "12-31":
            key = v["end"]
            if key not in out or v["filed"] > out[key][0]:
                out[key] = (v["filed"], v["accn"], "capex", pd.Timestamp(v["end"]), v["val"] / 1e6)
    return sorted(out.values())


COLUMNS = ["company", "kind", "check", "fy_end", "filed_20f", "accession", "series", "annual_20f", "sum_quarters",
           "diff", "ratio"]


def capex_series(kind: str) -> str:
    """The capex series on the definition of an exact line kind ("cf:ppe", "cf:ppe+intangibles", "v1line:<concept>")."""
    return EXACT_CAPEX[kind if kind.startswith("cf:") else kind.split(":", 1)[0]]


def run() -> pd.DataFrame:
    """One row per (20-F fact, series) with a complete fiscal year. check: "segment" (cloud: exact on the same
    definition), "exact" (capex on the company's own line) or "ratio" (Alibaba's broader line, where no exact line)."""
    rows = []
    cloud = {e.key: latest(china_sec.series("baba", "rev_cloud", e.key))
             for e in china_sec.ERAS[("baba", "rev_cloud")] if e.key}
    capex = {"capex_baba_v1": latest(china_sec.series("baba", "capex", "capex_baba_v1")),
             "capex_baba_v2": latest(china_sec.series("baba", "capex", "capex_baba_v2"))}

    def add(company, check, fact, key, values) -> None:
        filed, acc, kind, end, annual = fact
        s = fiscal_sum(values, end)
        if s is not None:
            rows.append(dict(zip(COLUMNS, (company, kind, check, str(end.date()), filed, acc, key, annual, s,
                                           s - annual, s / annual if annual else float("nan")))))

    broader = []
    for fact in baba_annual() + baba_companyfacts():
        kind = fact[2]
        if kind.startswith("cloud:"):
            for key, values in cloud.items():
                add("baba", "segment", fact, key, values)
        elif kind == "capex":
            broader.append(fact)
        else:
            add("baba", "exact", fact, capex_series(kind), capex[capex_series(kind)])
    exact = {(r["series"], r["fy_end"]) for r in rows if r["check"] == "exact"}
    for fact in broader:  # the broader line: a ratio, only for a series and year without an exact line
        for key, values in capex.items():
            if (key, str(fact[3].date())) not in exact:
                add("baba", "ratio", fact, key, values)
    bidu = latest(china_sec.series("bidu", "capex_total", "capex_bidu"))
    for fact in bidu_annual():
        add("bidu", "exact", fact, "capex_bidu", bidu)
    return pd.DataFrame(rows, columns=COLUMNS).sort_values(["company", "series", "fy_end", "filed_20f", "kind"],
                                                           ignore_index=True)


def summary(res: pd.DataFrame) -> pd.DataFrame:
    """Per series and check: fiscal years compared, years within ROUNDING in every 20-F and in at least one (a later
    20-F can restate a year on a new segment definition), largest absolute difference and the ratio range."""
    out = []
    for (company, key, check), g in res.groupby(["company", "series", "check"], sort=True):
        per_year = g.assign(abs_diff=g["diff"].abs()).groupby("fy_end")["abs_diff"]
        years = sorted(g.fy_end.unique())
        out.append((company, key, check, f"{years[0][:4]}-{years[-1][:4]}", len(years),
                    int((per_year.max() <= ROUNDING).sum()), int((per_year.min() <= ROUNDING).sum()),
                    float(g["diff"].abs().max()), float(g.ratio.min()), float(g.ratio.max())))
    return pd.DataFrame(out, columns=["company", "series", "check", "fy_ends", "years", "exact_in_all_20f",
                                      "exact_in_some_20f", "max_abs_diff", "ratio_min", "ratio_max"])


def main() -> None:
    pd.set_option("display.width", 200)
    res = run()
    def fmt(x: float) -> str:
        return f"{x:,.3f}" if abs(x) < 10 else f"{x:,.0f}"

    print(res.to_string(index=False, float_format=fmt))
    print()
    print(summary(res).to_string(index=False, float_format=fmt))


if __name__ == "__main__":
    main()
