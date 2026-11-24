"""N3: Nvidia's data-center revenue (`rev_nvda_datacenter`), docs/mattregister.md "Steg 2", G-B, with R6's F-B4, F-B5,
F-B9-F-B11, F-B14 and F-B15 (adopted verbatim). Shared machinery: quarterly.py and engine.py.

    python -m ai_tracker.nowcast backtest n3
    python -m ai_tracker.nowcast n3 --origin YYYY-MM-DD      live forecast -> forecasts/n3/<quarter>.json (never rewritten)

Timing (F-B5)
- Nvidia's fiscal year is a 52/53-week year ending on the last Sunday of January. Q1-Q3 are 13 weeks each from the
  previous year end, Q4 ends on the year end (14 weeks in a 53-week year: FY2010, FY2016, FY2021, FY2027). The
  calendar is known in advance; it reproduces "the last Sunday of April, July and October" in every year with data.
- Origin = fiscal quarter end + 14 days. The target at origin o is the fiscal quarter that last ended on or before
  o - 14 days, labelled with the calendar quarter of its midpoint (as sec.calendar_quarter, so Aug-Oct = Q3 and
  Nov-Jan = Q4). Guidance and the data-center share use the same labels.

Models
- B0, B1 (drift over 4 quarters): quarterly.py.
- B2 (F-B15): Nvidia's revenue guidance midpoint for q (`nvda_guid_rev_mid`, as of the origin) x the data-center share
  rev_nvda_datacenter(L) / rev_nvda(L) for the latest quarter L where both are known at the origin (normally q-1).
  No guidance known for q: B1.
- B3 (track C2) and DF (track C3) are registered members of N3's step-2 Holm family {B2, B3, DF} and are not
  implemented here: they enter Holm with p = 1 until they are evaluated (F-B9).
- B2 (and B3) stay in REVIEW_REQUIRED until an independent review has approved the extracted guidance values (F-B14;
  review R5 of track B4's Nvidia 8-K extraction is running): a passing B2 is only a conditional promotion.

A 14-week quarter raises the quarter's log growth by about 7 points (B1 is not adjusted; it is not leakage). Those
quarters are flagged in the backtest frame (`note`).
"""

from __future__ import annotations

import pandas as pd

from ai_tracker import observations
from ai_tracker.nowcast import engine, quarterly
from ai_tracker.sources import sec

TARGET = "rev_nvda_datacenter"
TOTAL = "rev_nvda"
GUIDANCE = "nvda_guid_rev_mid"
ORIGIN_DAYS = 14
VARIANTS = ["B0", "B1", "B2"]
MODELS = ["B2"]
FAMILY = ["B2", "B3", "DF"]  # F-B9, register "C0 preciseras efter granskning R6"
REVIEW_REQUIRED = {
    "B2": "villkorad: väntar på oberoende granskning av extraktionen av Nvidias guidance (R5)",
    "B3": "villkorad: väntar på oberoende granskning av extraktionen av Nvidias guidance (R5)",
}
CHAMPION = "B1"  # register: B1 unless a variant passes the rule (docs/resultat/n3.md). Changing it needs a decision.
FIRST_LIVE = pd.Timestamp("2027-02-14")  # 2026Q4 (Nov 2026 - Jan 2027, 14 weeks); 2026Q3's origin 2026-11-08 passed


# ------------------------------------------------------------------ fiscal calendar (F-B5)


def last_sunday_of_january(year: int) -> pd.Timestamp:
    d = pd.Timestamp(year, 1, 31)
    return d - pd.Timedelta(days=(d.dayofweek - 6) % 7)


def fiscal_quarters(fiscal_year: int) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """(start, end) of Q1-Q4 of the fiscal year that ends in January of `fiscal_year`."""
    prev = last_sunday_of_january(fiscal_year - 1)
    ends = [prev + pd.Timedelta(weeks=13 * k) for k in (1, 2, 3)] + [last_sunday_of_january(fiscal_year)]
    starts = [prev + pd.Timedelta(days=1)] + [e + pd.Timedelta(days=1) for e in ends[:-1]]
    return list(zip(starts, ends))


def fiscal_quarter(label: pd.Period) -> tuple[pd.Timestamp, pd.Timestamp]:
    """(start, end) of the fiscal quarter labelled with calendar quarter `label` (midpoint rule)."""
    label = pd.Period(label, freq="Q-DEC")
    for fy in (label.year, label.year + 1):
        for s, e in fiscal_quarters(fy):
            if sec.calendar_quarter(s, e) == label:
                return s, e
    raise ValueError(f"no Nvidia fiscal quarter maps to {label}")


def weeks(label: pd.Period) -> int:
    s, e = fiscal_quarter(label)
    return ((e - s).days + 1) // 7


def origin_for(label: pd.Period) -> pd.Timestamp:
    return fiscal_quarter(label)[1] + pd.Timedelta(days=ORIGIN_DAYS)


def target_quarter(origin) -> pd.Period:
    """F-B5: the fiscal quarter that last ended on or before origin - 14 days, as its calendar-quarter label."""
    cutoff = pd.Timestamp(origin).normalize() - pd.Timedelta(days=ORIGIN_DAYS)
    ended = [(s, e) for fy in (cutoff.year - 1, cutoff.year, cutoff.year + 1) for s, e in fiscal_quarters(fy)
             if e <= cutoff]
    return sec.calendar_quarter(*max(ended, key=lambda x: x[1]))


def quarter_note(label: pd.Period) -> str:
    return "14-week quarter" if weeks(label) == 14 else ""


# ------------------------------------------------------------------ B2 (F-B15)


def b2(info: engine.InfoSet, q: pd.Period, rec: quarterly.Record) -> None:
    dc = info.get(TARGET)
    tot = info.get(TOTAL)
    both = [p for p in dc.index.intersection(tot.index) if p < q and tot[p] > 0]
    guid = info.get(GUIDANCE)
    b1 = rec.levels["B1"]
    if q not in guid.index or not both:
        rec.levels["B2"] = b1
        rec.notes["b2_source"] = "B1: no guidance for the quarter known" if q not in guid.index else \
            "B1: no quarter with data-center and total revenue known"
        return
    L = max(both)
    share = float(dc[L] / tot[L])
    info.mark(GUIDANCE, [q])
    info.mark(TARGET, [L])
    info.mark(TOTAL, [L])
    rec.levels["B2"] = float(guid[q]) * share
    rec.notes.update(b2_source="guidance", b2_guidance=float(guid[q]), b2_share=share, b2_share_quarter=str(L))


SPEC = quarterly.Spec(
    nowcast="n3", label="N3", target=quarterly.Aggregate(TARGET), origin_for=origin_for,
    target_quarter=target_quarter, variants=VARIANTS, models=MODELS, family=FAMILY, review_required=REVIEW_REQUIRED,
    extra=b2, inputs=(TOTAL, GUIDANCE), champion=CHAMPION, quarter_notes=quarter_note)


def backtest(table: pd.DataFrame | None = None, log: bool = True) -> dict:
    table = observations.load() if table is None else table
    out = quarterly.backtest(table, SPEC, log, FIRST_LIVE)
    f = out["frame"]
    if len(f):
        e = f[f["in_period"]]
        out["b2_sources"] = e["b2_source"].value_counts().to_dict() if "b2_source" in e else {}
        out["fourteen_week"] = [str(q) for q in f.loc[f["note"] == "14-week quarter", "quarter"]]
        out["share_lag"] = (e["quarter"].map(lambda q: q.ordinal) -
                            e["b2_share_quarter"].map(lambda s: pd.Period(s, "Q-DEC").ordinal)).value_counts().to_dict() \
            if "b2_share_quarter" in e else {}
    return out


def format_report(out: dict) -> str:
    lines = [quarterly.format_report(out, SPEC)]
    lines.append(f"B2 sources (evaluated quarters): {out.get('b2_sources')}; share quarter lag: {out.get('share_lag')}; "
                 f"14-week target quarters scored: {out.get('fourteen_week')}")
    return "\n".join(lines)


def write_live(table: pd.DataFrame, origin, out_dir, today=None):
    return quarterly.write_live(table, SPEC, origin, out_dir, today)


def first_live_origin(after) -> tuple[pd.Timestamp, pd.Period]:
    """The first registered origin on or after `after`."""
    day = pd.Timestamp(after).normalize()
    q = target_quarter(day)
    while origin_for(q) < day:
        q += 1
    return origin_for(q), q

