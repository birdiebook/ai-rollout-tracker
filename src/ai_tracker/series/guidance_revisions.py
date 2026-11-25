"""F1: revisions of company guidance and surprise against guidance (docs/mattregister.md, 2026-11-24 "F1: revideringar
av guidance och överraskning mot guidance"). Group "Förväntningar mot utfall": measured and shown, never counted in a
branch's diffusion index, no pace (the measures already are changes).

Statements, items and chains
- An item is (company, measure, guided period, definition code). Capex: one statement per row of
  curated/guidance_capex.csv (known_from = filed), so a range restated unchanged in a later release is a statement.
  TSMC (quarterly revenue in the currency it was stated in) and Nvidia (quarterly revenue midpoint, from 2017Q2):
  one statement per vintage of the guidance series in the observation table (a restatement adds no vintage).
  TSMC's annual capex outlook (tsmc_capex_guidance, deterministic parse of the same 6-Ks): one statement per filing.
- Within an item, three chains are kept apart and only statements of one chain are compared: numbers (point,
  range, approx: the midpoint), lower bounds (min) and directions per direction base.
- A registered definition break (DEFINITION_BREAKS) starts a new item from that row on. The break row is no
  revision; break_statements() reports its size against the last statement before the break, so a break never hides
  a change (R11-1).

Revision event: a statement in a chain that already has an earlier statement, at least SAME_EVENT_DAYS after it
(a later statement inside that window is the same event: no event, but it becomes the chain's reference). Size =
100 x (ln new - ln previous) for numbers and bounds; up if size >= DEADBAND, down if <= -DEADBAND, else unchanged.
Directions: the code against the previous code, no size. The first statement of a chain is never a revision, so
TSMC's and Nvidia's quarterly guidance (once per quarter) is a new item; only a later vintage of the same quarter is.

Revision index per calendar quarter of known_from, all companies pooled, from COVERAGE_FROM: D = (n_up + 0.5 x
n_unchanged) / n over the quarter (window 1) or the quarter and the three before it (window 4, the main measure).
n < MIN_EVENTS: no index (n is still reported). Median size over events with a size. A version is emitted at every
event date in the quarter that changes the counts, and once at the quarter's last day if the quarter has no version
yet and the day has passed (known_from = that date; computed from the day after, R11-2). Sensitivity (register,
rättning efter R11): the same index over events with a number only (chains num and min, no directions).

Surprise per company and guided period: s = 100 x (ln U - ln G). U = first vintage of the outcome (sums of first
vintages, known from the latest component); G = midpoint of the last guidance known before U (as_of the day before
U's known_from), on B2's basis rules:
- TSMC quarterly revenue in NT$: sum of the quarter's three months of tsmc_revenue_m; G = N2's B2 rule
  (n2.quarter_guidance: the NT$ midpoint until 2017Q2, the US$ midpoint x the assumed rate from 2017Q3).
- Nvidia quarterly revenue: rev_nvda against nvda_guid_rev_mid, quarters from 2017Q2 (reviewed in R5).
- Meta calendar-year capex: capex_meta + fin_lease_meta over the year's four quarters against META_CAPEX_INCL_FL.
- Alphabet calendar-year capex: capex_googl over the four quarters against GOOGL_CAPEX.
Amazon (net of incentives or unstated basis) and Microsoft (incl. finance leases at inception, quarterly lower
bounds) are not comparable with our outcomes and are left out; directions are never used.
z = s / SD (ddof 1) of the company's own earlier surprises whose outcome was known before this one, at least
MIN_PAST of them; not demeaned. Surprise index per calendar quarter (annual capex counts in the year's Q4) = mean
of the z known, at least MIN_COMPONENTS of them; a version per component that becomes known (known_from = latest).
Sensitivity (R11-7): TSMC in US$ from 2017Q3, U = the quarter's US$ revenue in the quarterly release
(tsmc_usd_revenue), G = the US$ midpoint known the day before; s(NT$) - s(US$) is the FX part, 100 x ln(realised
rate / assumed rate). Not in the surprise index.

Publication (R11-4, owner decision 2026-11-25): every series that reads the curated CSV lists the guid_capex_* series
of the companies whose rows it reads as components and is published only when they all are. The guid_capex_* series of
Alphabet, Amazon and Meta are published (all their rows on sec.gov); Microsoft's are not (microsoft.com). Meta's and
Alphabet's surprises read only their own company's rows (CSV_READS), so they are published; the revision series pool
every company's rows, Microsoft's too, and stay withheld, as does the surprise index (see CSV_READS).
"""

from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timezone
from functools import lru_cache
import numpy as np
import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.sources import guidance_capex

GROUP = "Förväntningar mot utfall"
DEADBAND = 1.0  # |size| < 1 (log x100) = unchanged
SAME_EVENT_DAYS = 7
MIN_EVENTS = 3  # revision index needs n >= 3
WINDOWS = (1, 4)  # quarterly and rolling 4 quarters; 4 is the main measure (register: counts per quarter 0-5)
MAIN_WINDOW = 4
COVERAGE_FROM = pd.Period("2020Q3", "Q-DEC")  # the curated capex extraction reads documents from 2020-07
NVDA_FROM = pd.Period("2017Q2", "Q-DEC")  # Nvidia quarters reviewed by R5 (as B3)
MIN_PAST = 4  # z needs >= 4 earlier surprises of the same company
MIN_COMPONENTS = 2  # surprise index needs >= 2 companies
# row id -> reason: a documented break in what the guided number measures; the row starts a new item
# (register F1, moved by the amendment after R11: the break sits at the first figure on the new basis, msft-r11f1,
# not at msft-29, which is a cut on the same basis)
DEFINITION_BREAKS = {"msft-r11f1": "R5-F14, R11-1: from the 2026-07-29 call (#225-228) more datacenter leases are "
                                   "operating, so MSFT_CAPEX_INCL_FL is narrower than for msft-26; the company put "
                                   "CY2026 at about 175bn on the new basis, unchanged apart from that (#227)"}
NUMERIC_CHAINS = ("num", "min")  # chains with a size; the numeric-only sensitivity uses these

STATEMENT_COLUMNS = ["company", "measure", "item", "chain", "period", "definition", "kind", "value", "code",
                     "known_from", "ref"]
EVENT_COLUMNS = ["company", "measure", "item", "chain", "period", "definition", "kind", "known_from", "ref",
                 "prev_known_from", "prev_ref", "prev_value", "value", "prev_code", "code", "size", "direction"]
INDEX_COLUMNS = ["period", "known_from", "n", "n_up", "n_unchanged", "n_down", "index", "median_size", "n_size"]
SURPRISE_COLUMNS = ["company", "measure", "period", "freq", "index_quarter", "outcome", "outcome_known_from",
                    "guidance", "guidance_known_from", "s"]

TSMC_GUIDANCE = {"TWD": ("tsmc_guid_rev_twd_lo", "tsmc_guid_rev_twd_hi"),
                 "USD": ("tsmc_guid_rev_usd_lo", "tsmc_guid_rev_usd_hi")}
TSMC_CAPEX = ("tsmc_guid_capex_lo", "tsmc_guid_capex_hi")
NVDA_GUIDANCE = "nvda_guid_rev_mid"
TSMC_TARGET = "tsmc_revenue_m"
TSMC_USD_TARGET = "tsmc_rev_usd_q"  # R11-7: quarterly US$ revenue from the release (tsmc_usd_revenue)
TSMC_USD_FROM = pd.Period("2017Q3", "Q-DEC")  # TSMC guides in US$ from 2017Q3
NVDA_TARGET = "rev_nvda"
# company -> (CSV definition of the guided number, outcome components summed over the calendar year)
CAPEX_SURPRISE = {"meta": ("META_CAPEX_INCL_FL", ("capex_meta", "fin_lease_meta")),
                  "googl": ("GOOGL_CAPEX", ("capex_googl",))}
# first guided year of the surprise (register F1, column "Från"); Meta's 2020 rows (R11-5) enter the revision index only
CAPEX_SURPRISE_FROM = {"meta": 2021, "googl": 2025}
NUMERIC_KINDS = ("point", "range", "approx")


def _empty(columns) -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in columns})


def _rows(table: pd.DataFrame | None, series: str) -> pd.DataFrame:
    if table is None or table.empty:
        return table.iloc[0:0] if table is not None else pd.DataFrame()
    t = table[table["series"] == series].copy()
    t["known_from"] = pd.to_datetime(t["known_from"])
    return t


# ------------------------------------------------------------------ statements


def capex_statements(csv: pd.DataFrame) -> pd.DataFrame:
    """Statements from the curated capex CSV (guidance_capex.load() frame), one per row."""
    if csv is None or csv.empty:
        return _empty(STATEMENT_COLUMNS)
    d = csv.copy()
    d["known_from"] = pd.to_datetime(d["known_from"])
    d["_order"] = range(len(d))
    d = d.sort_values(["known_from", "_order"], kind="stable")
    out, segment = [], {}
    for r in d.itertuples(index=False):
        base = (r.company, "capex", f"{r.horizon}:{r.period}", r.definition)
        if r.id in DEFINITION_BREAKS:
            segment[base] = segment.get(base, 0) + 1
        seg = segment.get(base, 0)
        definition = r.definition if seg == 0 else f"{r.definition}~{seg}"
        if r.kind == "direction":
            chain, value, code = f"dir:{r.direction_base}", np.nan, float(r.direction_code)
        elif r.kind == "min":
            chain, value, code = "min", float(r.value_lo), np.nan
        else:
            hi = r.value_hi if pd.notna(r.value_hi) else r.value_lo
            chain, value, code = "num", (float(r.value_lo) + float(hi)) / 2, np.nan
        item = f"{r.company}|capex|{r.horizon}:{r.period}|{definition}"
        out.append((r.company, "capex", item, chain, f"{r.horizon}:{r.period}", definition, r.kind, value, code,
                    r.known_from, r.id))
    return pd.DataFrame(out, columns=STATEMENT_COLUMNS)


def _mid_vintages(lo: pd.DataFrame, hi: pd.DataFrame) -> list[tuple[str, float, pd.Timestamp]]:
    """(period, midpoint, known_from) at every date where lo or hi of a period changes, both known; repeats skipped."""
    out = []
    if lo.empty or hi.empty:
        return out
    for p in sorted(set(lo["period"]) & set(hi["period"])):
        a = lo[lo["period"] == p].sort_values("known_from")
        b = hi[hi["period"] == p].sort_values("known_from")
        prev = None
        for d in sorted(set(a["known_from"]) | set(b["known_from"])):
            ak, bk = a[a["known_from"] <= d], b[b["known_from"] <= d]
            if ak.empty or bk.empty:
                continue
            mid = (float(ak["value"].iloc[-1]) + float(bk["value"].iloc[-1])) / 2
            if prev is None or not math.isclose(mid, prev, rel_tol=0, abs_tol=1e-9):
                out.append((str(p), mid, pd.Timestamp(d)))
                prev = mid
    return out


def table_statements(table: pd.DataFrame | None) -> pd.DataFrame:
    """Statements of TSMC's and Nvidia's quarterly revenue guidance: one per vintage of the midpoint."""
    out = []
    if table is None or table.empty:
        return _empty(STATEMENT_COLUMNS)
    for cur, (lo_key, hi_key) in TSMC_GUIDANCE.items():
        definition = f"TSMC_REV_{cur}"
        for p, mid, kf in _mid_vintages(_rows(table, lo_key), _rows(table, hi_key)):
            out.append(("tsmc", "revenue", f"tsmc|revenue|Q:{p}|{definition}", "num", f"Q:{p}", definition, "range",
                        mid, np.nan, kf, lo_key.removesuffix("_lo")))
    for p, mid, kf in _mid_vintages(_rows(table, TSMC_CAPEX[0]), _rows(table, TSMC_CAPEX[1])):
        out.append(("tsmc", "capex", f"tsmc|capex|CY:{p}|TSMC_CAPEX_USD", "num", f"CY:{p}", "TSMC_CAPEX_USD",
                    "range", mid, np.nan, kf, "tsmc_guid_capex"))
    g = _rows(table, NVDA_GUIDANCE)
    if not g.empty:
        g = g[[pd.Period(p, "Q-DEC") >= NVDA_FROM for p in g["period"]]]
        for p, grp in g.groupby("period", sort=True):
            prev = None
            for v, kf in grp.sort_values("known_from")[["value", "known_from"]].itertuples(index=False):
                if prev is None or not math.isclose(float(v), prev, rel_tol=0, abs_tol=1e-9):
                    out.append(("nvda", "revenue", f"nvda|revenue|Q:{p}|NVDA_REV", "num", f"Q:{p}", "NVDA_REV",
                                "point", float(v), np.nan, pd.Timestamp(kf), NVDA_GUIDANCE))
                    prev = float(v)
    return pd.DataFrame(out, columns=STATEMENT_COLUMNS) if out else _empty(STATEMENT_COLUMNS)


def statements(table: pd.DataFrame | None, csv: pd.DataFrame | None) -> pd.DataFrame:
    parts = [p for p in (capex_statements(csv), table_statements(table)) if len(p)]
    if not parts:
        return _empty(STATEMENT_COLUMNS)
    s = pd.concat(parts, ignore_index=True)
    s["known_from"] = pd.to_datetime(s["known_from"])
    return s


# ------------------------------------------------------------------ revision events


def _size(new: float, prev: float) -> float:
    if not (new > 0 and prev > 0):
        return np.nan
    return 100.0 * (math.log(new) - math.log(prev))


def _direction(size: float) -> int:
    return 1 if size >= DEADBAND else -1 if size <= -DEADBAND else 0


def events(stmts: pd.DataFrame) -> pd.DataFrame:
    """Revision events of every chain (see the module docstring). Depends on earlier statements only, so the events
    known on a date are the same whether later statements exist or not."""
    if stmts is None or stmts.empty:
        return _empty(EVENT_COLUMNS)
    s = stmts.copy()
    s["_order"] = range(len(s))
    out = []
    for (item, chain), grp in s.sort_values(["known_from", "_order"], kind="stable").groupby(
            ["item", "chain"], sort=False):
        ref = None  # the chain's reference statement (the latest statement, also one inside an event window)
        anchor = None  # known_from of the latest statement that counted (or the chain's first statement)
        for r in grp.itertuples(index=False):
            if ref is None:
                ref, anchor = r, r.known_from
                continue
            if (r.known_from - anchor).days < SAME_EVENT_DAYS:
                ref = r  # same event: not a revision, but the later statement is the reference from now on
                continue
            if chain.startswith("dir:"):
                size = np.nan
                direction = int(np.sign(r.code - ref.code)) if pd.notna(r.code) and pd.notna(ref.code) else None
            else:
                size = _size(r.value, ref.value)
                direction = _direction(size) if math.isfinite(size) else None
            if direction is not None:
                out.append((r.company, r.measure, item, chain, r.period, r.definition, r.kind, r.known_from, r.ref,
                            ref.known_from, ref.ref, ref.value, r.value, ref.code, r.code, size, direction))
            ref, anchor = r, r.known_from
    if not out:
        return _empty(EVENT_COLUMNS)
    ev = pd.DataFrame(out, columns=EVENT_COLUMNS)
    return ev.sort_values(["known_from", "company", "item", "chain"], ignore_index=True)


def numeric_only(ev: pd.DataFrame) -> pd.DataFrame:
    """Events with a number (chains num and min): the sensitivity without direction codes (R11-6)."""
    if ev is None or ev.empty:
        return _empty(EVENT_COLUMNS)
    return ev[ev["chain"].isin(NUMERIC_CHAINS)].reset_index(drop=True)


BREAK_COLUMNS = ["company", "measure", "period", "chain", "ref", "known_from", "value", "prev_ref",
                 "prev_known_from", "prev_value", "size", "reason"]


def break_statements(stmts: pd.DataFrame) -> pd.DataFrame:
    """Statements that a registered break keeps out of the comparison, with their size against the last statement
    of the same chain before the break (R11-1). Not revisions: shown so that a break cannot hide a change."""
    if stmts is None or stmts.empty:
        return _empty(BREAK_COLUMNS)
    s = stmts.copy()
    s["_order"] = range(len(s))
    s = s.sort_values(["known_from", "_order"], kind="stable").reset_index(drop=True)
    base = [f"{c}|{m}|{p}|{d.split('~')[0]}" for c, m, p, d in
            s[["company", "measure", "period", "definition"]].itertuples(index=False)]
    s["_base"] = base
    out = []
    for i in s.index[s["ref"].isin(list(DEFINITION_BREAKS))]:
        r = s.loc[i]
        before = s.iloc[:i]
        before = before[(before["_base"] == r["_base"]) & (before["chain"] == r["chain"])
                        & (before["item"] != r["item"])]
        p = before.iloc[-1] if len(before) else None
        size = _size(r["value"], p["value"]) if p is not None and not r["chain"].startswith("dir:") else np.nan
        out.append((r["company"], r["measure"], r["period"], r["chain"], r["ref"], r["known_from"], r["value"],
                    None if p is None else p["ref"], None if p is None else p["known_from"],
                    np.nan if p is None else p["value"], size, DEFINITION_BREAKS[r["ref"]]))
    return pd.DataFrame(out, columns=BREAK_COLUMNS) if out else _empty(BREAK_COLUMNS)


def _stats(ev: pd.DataFrame) -> tuple:
    n = len(ev)
    up, flat, down = (int((ev["direction"] == k).sum()) for k in (1, 0, -1))
    sizes = ev["size"].astype(float)
    sizes = sizes[np.isfinite(sizes)]
    index = (up + 0.5 * flat) / n if n >= MIN_EVENTS else np.nan
    median = float(np.median(sizes)) if len(sizes) else np.nan
    return n, up, flat, down, index, median, int(len(sizes))


def revision_index(ev: pd.DataFrame, window: int, today, start: pd.Period | None = None) -> pd.DataFrame:
    """Versions of the revision index per calendar quarter (window 1 = the quarter, 4 = it and the 3 before), from
    `start` (default COVERAGE_FROM)."""
    today = pd.Timestamp(today).normalize()
    start = COVERAGE_FROM if start is None else start
    last_q = pd.Period(today, "Q-DEC")
    if ev is None or ev.empty:
        ev = _empty(EVENT_COLUMNS)
    e = ev.copy()
    e["known_from"] = pd.to_datetime(e["known_from"])
    e = e[e["known_from"] <= today]
    e["quarter"] = [pd.Period(d, "Q-DEC") for d in e["known_from"]] if len(e) else pd.Series(dtype="object")
    rows = []
    for q in pd.period_range(start, last_q, freq="Q-DEC"):
        win = e[(e["quarter"] >= q - (window - 1)) & (e["quarter"] <= q)] if len(e) else e
        dates = sorted(set(win.loc[win["quarter"] == q, "known_from"])) if len(win) else []
        end = q.end_time.normalize()
        if end < today:  # register: once the quarter's last day has passed (R11-2)
            dates.append(end)
        prev = None
        for d in dates:
            st = _stats(win[win["known_from"] <= d])
            key = st[:4] + (None if math.isnan(st[5]) else round(st[5], 12),)
            if prev is not None and key == prev:
                continue
            rows.append((str(q), pd.Timestamp(d), *st))
            prev = key
    if not rows:
        return _empty(INDEX_COLUMNS)
    return pd.DataFrame(rows, columns=INDEX_COLUMNS)


# ------------------------------------------------------------------ surprises


def _by_series(table: pd.DataFrame | None, keys) -> dict[str, pd.DataFrame]:
    if table is None or table.empty:
        return {}
    t = table[table["series"].isin(list(keys))].copy()
    t["known_from"] = pd.to_datetime(t["known_from"])
    return {k: g for k, g in t.groupby("series", sort=False)}


def _first(rows: pd.DataFrame | None) -> pd.DataFrame:
    """First vintage per period (value, known_from), indexed by the period string."""
    if rows is None or rows.empty:
        return pd.DataFrame(columns=["value", "known_from"])
    f = rows.sort_values("known_from", kind="stable").groupby("period")[["value", "known_from"]].first()
    f.index = f.index.astype(str)
    return f


def tsmc_surprises(table: pd.DataFrame | None) -> list[tuple]:
    from ai_tracker.nowcast import n2  # lazy: nowcast -> observations -> catalog -> series (this module)

    by = _by_series(table, [TSMC_TARGET, *n2.GUIDANCE.values()])
    first = _first(by.get(TSMC_TARGET))
    if first.empty:
        return []
    out = []
    quarters = sorted({pd.Period(p, "M").asfreq("Q-DEC") for p in first.index})
    for q in quarters:
        months = [str(m) for m in pd.period_range(q.asfreq("M", "s"), q.asfreq("M", "e"), freq="M")]
        if any(m not in first.index for m in months):
            continue
        u = float(first.loc[months, "value"].sum())
        kf = pd.Timestamp(first.loc[months, "known_from"].max())
        g, _source, used = n2.quarter_guidance(q, kf - pd.Timedelta(days=1), by)
        if not (np.isfinite(g) and g > 0 and u > 0):
            continue
        gkf = max(pd.Timestamp(x[-1]) for x in used)
        out.append(("tsmc", "revenue", str(q), "Q", str(q), u, kf, float(g), gkf, 100.0 * math.log(u / g)))
    return out


def nvda_surprises(table: pd.DataFrame | None) -> list[tuple]:
    from ai_tracker import observations  # lazy, see tsmc_surprises

    by = _by_series(table, [NVDA_TARGET, NVDA_GUIDANCE])
    first, guid = _first(by.get(NVDA_TARGET)), by.get(NVDA_GUIDANCE)
    if first.empty or guid is None:
        return []
    out = []
    for p, r in first.iterrows():
        q = pd.Period(p, "Q-DEC")
        if q < NVDA_FROM:
            continue
        kf = pd.Timestamp(r["known_from"])
        known = guid[guid["known_from"] <= kf - pd.Timedelta(days=1)]
        g = observations.as_of(NVDA_GUIDANCE, kf - pd.Timedelta(days=1), known)
        if q not in g.index or not (g[q] > 0 and r["value"] > 0):
            continue
        gkf = pd.Timestamp(known.loc[known["period"].astype(str) == str(q), "known_from"].max())
        out.append(("nvda", "revenue", str(q), "Q", str(q), float(r["value"]), kf, float(g[q]), gkf,
                    100.0 * math.log(float(r["value"]) / float(g[q]))))
    return out


def capex_surprises(table: pd.DataFrame | None, csv: pd.DataFrame | None) -> list[tuple]:
    if csv is None or csv.empty:
        return []
    out = []
    for company, (definition, comps) in CAPEX_SURPRISE.items():
        by = _by_series(table, comps)
        firsts = {c: _first(by.get(c)) for c in comps}
        g_rows = csv[(csv["company"] == company) & (csv["horizon"] == "CY") & (csv["definition"] == definition)
                     & csv["kind"].isin(NUMERIC_KINDS)].copy()
        g_rows["known_from"] = pd.to_datetime(g_rows["known_from"])
        g_rows["_order"] = range(len(g_rows))
        for year in sorted(set(g_rows["period"].astype(str))):
            if int(year) < CAPEX_SURPRISE_FROM[company]:
                continue
            parts = [(c, f"{year}Q{k}") for c in comps for k in (1, 2, 3, 4)]
            if any(p not in firsts[c].index for c, p in parts):
                continue
            u = float(sum(firsts[c].at[p, "value"] for c, p in parts))
            kf = max(pd.Timestamp(firsts[c].at[p, "known_from"]) for c, p in parts)
            prior = g_rows[(g_rows["period"].astype(str) == year) & (g_rows["known_from"] < kf)]
            if prior.empty:
                continue
            last = prior.sort_values(["known_from", "_order"], kind="stable").iloc[-1]
            hi = last["value_hi"] if pd.notna(last["value_hi"]) else last["value_lo"]
            g = (float(last["value_lo"]) + float(hi)) / 2
            if not (g > 0 and u > 0):
                continue
            out.append((company, "capex", year, "A", f"{year}Q4", u, kf, g, pd.Timestamp(last["known_from"]),
                        100.0 * math.log(u / g)))
    return out


USD_SURPRISE_COLUMNS = ["period", "outcome", "outcome_known_from", "guidance", "guidance_known_from", "s", "s_ntd",
                        "fx"]


def tsmc_usd_surprises(table: pd.DataFrame | None, ntd: pd.DataFrame | None = None) -> pd.DataFrame:
    """Sensitivity (R11-7): TSMC's US$ quarterly revenue (first vintage, tsmc_rev_usd_q) against the US$ midpoint
    known the day before, from TSMC_USD_FROM. s_ntd = the main (NT$, B2 basis) surprise of the same quarter and
    fx = s_ntd - s, which is 100 x (ln realised NT$/US$ rate - ln assumed rate)."""
    from ai_tracker import observations  # lazy, see tsmc_surprises

    lo_key, hi_key = TSMC_GUIDANCE["USD"]
    by = _by_series(table, [TSMC_USD_TARGET, lo_key, hi_key])
    first, lo, hi = _first(by.get(TSMC_USD_TARGET)), by.get(lo_key), by.get(hi_key)
    if first.empty or lo is None or hi is None:
        return _empty(USD_SURPRISE_COLUMNS)
    main = {} if ntd is None or ntd.empty else ntd[ntd["company"] == "tsmc"].set_index("period")["s"].to_dict()
    out = []
    for p, r in first.iterrows():
        q = pd.Period(p, "Q-DEC")
        if q < TSMC_USD_FROM:
            continue
        kf = pd.Timestamp(r["known_from"])
        cut = kf - pd.Timedelta(days=1)
        a, b = lo[lo["known_from"] <= cut], hi[hi["known_from"] <= cut]
        ga, gb = observations.as_of(lo_key, cut, a), observations.as_of(hi_key, cut, b)
        if q not in ga.index or q not in gb.index:
            continue
        g, u = (float(ga[q]) + float(gb[q])) / 2, float(r["value"])
        if not (g > 0 and u > 0):
            continue
        gkf = max(pd.Timestamp(x.loc[x["period"].astype(str) == str(q), "known_from"].max()) for x in (a, b))
        s_usd = 100.0 * math.log(u / g)
        s_ntd = main.get(str(q), np.nan)
        out.append((str(q), u, kf, g, gkf, s_usd, s_ntd, s_ntd - s_usd))
    return pd.DataFrame(out, columns=USD_SURPRISE_COLUMNS) if out else _empty(USD_SURPRISE_COLUMNS)


def surprises(table: pd.DataFrame | None, csv: pd.DataFrame | None) -> pd.DataFrame:
    rows = tsmc_surprises(table) + nvda_surprises(table) + capex_surprises(table, csv)
    if not rows:
        return _empty(SURPRISE_COLUMNS + ["n_past", "sd_past", "z"])
    s = pd.DataFrame(rows, columns=SURPRISE_COLUMNS)
    return standardize(s)


def standardize(s: pd.DataFrame, min_past: int = MIN_PAST) -> pd.DataFrame:
    """z = s / SD of the company's earlier surprises (outcome known strictly before this one), >= min_past of them."""
    s = s.copy()
    s["outcome_known_from"] = pd.to_datetime(s["outcome_known_from"])
    n_past, sd_past, z = [], [], []
    for r in s.itertuples(index=False):
        past = s[(s["company"] == r.company) & (s["outcome_known_from"] < r.outcome_known_from)]["s"].to_numpy(float)
        n_past.append(len(past))
        sd = float(np.std(past, ddof=1)) if len(past) >= max(min_past, 2) else np.nan
        sd_past.append(sd)
        z.append(r.s / sd if np.isfinite(sd) and sd > 0 else np.nan)
    s["n_past"], s["sd_past"], s["z"] = n_past, sd_past, z
    return s.sort_values(["outcome_known_from", "company"], ignore_index=True)


def surprise_index(s: pd.DataFrame, min_n: int = MIN_COMPONENTS) -> pd.DataFrame:
    """Versions of the surprise index per calendar quarter: mean z of the components known, >= min_n of them."""
    cols = ["period", "known_from", "value", "n", "companies"]
    if s is None or s.empty:
        return _empty(cols)
    z = s[np.isfinite(s["z"].astype(float))]
    rows = []
    for q, grp in z.groupby("index_quarter", sort=True):
        prev = None
        for d in sorted(set(grp["outcome_known_from"])):
            known = grp[grp["outcome_known_from"] <= d]
            if len(known) < min_n:
                continue
            value = float(known["z"].mean())
            if prev is not None and math.isclose(value, prev, rel_tol=0, abs_tol=1e-12):
                continue
            rows.append((str(q), pd.Timestamp(d), value, int(len(known)), ",".join(sorted(known["company"]))))
            prev = value
    return pd.DataFrame(rows, columns=cols) if rows else _empty(cols)


# ------------------------------------------------------------------ inputs and catalog


def load_csv() -> pd.DataFrame | None:
    return guidance_capex.load() if guidance_capex.PATH.exists() else None


def compute(table: pd.DataFrame | None, csv: pd.DataFrame | None, today) -> dict:
    """Everything F1 publishes, from the observation table and the curated capex CSV (pure: no I/O)."""
    stmts = statements(table, csv)
    ev = events(stmts)
    num = numeric_only(ev)
    s = surprises(table, csv)
    return {"events": ev, "index": {w: revision_index(ev, w, today) for w in WINDOWS},
            "index_numeric": {w: revision_index(num, w, today) for w in WINDOWS}, "breaks": break_statements(stmts),
            "surprises": s, "surprise_index": surprise_index(s), "surprises_tsmc_usd": tsmc_usd_surprises(table, s)}


def _release(df: pd.DataFrame, value: str, period: str = "period", known_from: str = "known_from") -> pd.DataFrame:
    d = df[[period, value, known_from]].rename(columns={period: "period", value: "value", known_from: "known_from"})
    d = d[np.isfinite(d["value"].astype(float))]
    d = d.assign(value=d["value"].astype(float), source="derived")
    return d.drop_duplicates(["period", "known_from"], keep="last").reset_index(drop=True)


def _series(key: str, out: dict) -> pd.DataFrame:
    kind, *rest = SERIES[key][0]
    if kind == "index":
        window, col = rest
        frame = out["index"][window]
        if col == "n":
            return _release(frame, "n")
        d = _release(frame, col)
        # an unchanged value in a later version (e.g. n grew but the median did not) adds no row
        d = d.sort_values("known_from")
        keep, last = [], {}
        for r in d.itertuples(index=False):
            if r.period in last and math.isclose(last[r.period], r.value, rel_tol=0, abs_tol=1e-12):
                continue
            last[r.period] = r.value
            keep.append(r)
        return pd.DataFrame(keep, columns=d.columns) if keep else d.iloc[0:0]
    if kind == "surprise":
        company = rest[0]
        s = out["surprises"]
        return _release(s[s["company"] == company], "s", known_from="outcome_known_from")
    if kind == "surprise_index":
        return _release(out["surprise_index"], rest[0])
    if kind == "surprise_usd":
        return _release(out["surprises_tsmc_usd"], "s", known_from="outcome_known_from")
    raise KeyError(key)


_CACHE: dict = {}


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()  # as the snapshot's utc_today (R11-10)


def csv_stamp(csv: pd.DataFrame | None) -> str:
    """SHA-256 of the curated CSV's loaded rows, for the fetch cache key (R11-3)."""
    if csv is None or csv.empty:
        return ""
    return hashlib.sha256(csv.drop(columns=["known_from"], errors="ignore").to_csv(index=False).encode()).hexdigest()


def _fetch(key: str):
    def fetch(table: pd.DataFrame | None = None) -> pd.DataFrame:
        from ai_tracker import observations  # lazy: observations -> catalog -> series -> this module

        t = observations.load() if table is None else table
        t = t[t["series"].isin(COMPONENTS)]
        csv, today = load_csv(), _utc_today()
        stamp = (len(t), str(t["known_from"].max()) if len(t) else "", float(t["value"].sum()) if len(t) else 0.0,
                 csv_stamp(csv), today)
        if _CACHE.get("stamp") != stamp:  # one computation for all F1 series in a refresh
            _CACHE.clear()
            _CACHE.update(stamp=stamp, out=compute(t, csv, today))
        return _series(key, _CACHE["out"])

    return fetch


COMPONENTS = ("tsmc_guid_rev_twd_lo", "tsmc_guid_rev_twd_hi", "tsmc_guid_rev_usd_lo", "tsmc_guid_rev_usd_hi",
              "tsmc_guid_fx", "tsmc_guid_capex_lo", "tsmc_guid_capex_hi", "nvda_guid_rev_mid", "tsmc_revenue_m",
              TSMC_USD_TARGET, "rev_nvda", "capex_meta", "fin_lease_meta", "capex_googl")
SOURCE = ("Härledd (F1) ur bolagens guidance: curated/guidance_capex.csv (granskad i R2), TSMC:s och Nvidias "
          "guidance i SEC-inlämningar, och utfall ur SEC EDGAR")
LICENSE = "SEC EDGAR: public information (sec.gov/privacy); egna kodade värden, bara siffror med källhänvisning"
_NOTE = (f"Grupp \"{GROUP}\" (register 2026-11-24, F1): mäts och visas, räknas aldrig i en grens diffusionsindex, "
         "ingen takt. ")

# key -> ((kind, ...), branch, label, unit, freq, lag_days, max_age_days, question, note)
SERIES = {
    "f1_rev_index_4q": (("index", 4, "index"), "G5", "Revideringsindex för guidance, rullande 4 kvartal (andel uppåt)",
                        "index 0–1", "Q", -92, 400,
                        "Höjer eller sänker bolagen sina egna planer?",
                        "(uppåt + 0,5 × oförändrade) / antal revideringar i kvartalet och de tre före; minst 3. "
                        "Huvudmåttet. Aktualitet: oregelbundna händelser, gräns 400 dagar."),
    "f1_rev_index_q": (("index", 1, "index"), "G5", "Revideringsindex för guidance, kvartal (andel uppåt)",
                       "index 0–1", "Q", -92, 400,
                       "Höjer eller sänker bolagen sina egna planer i kvartalet?",
                       "Som f1_rev_index_4q men bara kvartalets händelser; minst 3. Aktualitet: gräns 400 dagar."),
    "f1_rev_n_4q": (("index", 4, "n"), "G5", "Antal revideringar av guidance, rullande 4 kvartal", "antal", "Q", -92,
                    120, "Hur många revideringar bygger indexet på?",
                    "Alla bolag och mått. En version daterad kvartalets sista dag, när dagen har passerat. "
                    "Aktualitet: gräns 120 dagar."),
    "f1_rev_n_q": (("index", 1, "n"), "G5", "Antal revideringar av guidance, kvartal", "antal", "Q", -92, 120,
                   "Hur många revideringar kom i kvartalet?",
                   "Alla bolag och mått. En version daterad kvartalets sista dag, när dagen har passerat. "
                   "Aktualitet: gräns 120 dagar."),
    "f1_rev_median_4q": (("index", 4, "median_size"), "G5",
                         "Medianrevidering av guidance, rullande 4 kvartal (log ×100)", "log ×100", "Q", -92, 400,
                         "Hur stora är revideringarna?",
                         "Median av 100 × (ln ny mittpunkt − ln förra) över revideringar med siffror; riktningar har "
                         "ingen storlek. Aktualitet: gräns 400 dagar."),
    "f1_rev_median_q": (("index", 1, "median_size"), "G5", "Medianrevidering av guidance, kvartal (log ×100)",
                        "log ×100", "Q", -92, 400, "Hur stora är kvartalets revideringar?",
                        "Som f1_rev_median_4q, bara kvartalets händelser. Aktualitet: gräns 400 dagar."),
    "f1_surprise_tsmc": (("surprise", "tsmc"), "G6", "TSMC: kvartalsintäkt mot egen guidance (log ×100)", "log ×100",
                         "Q", 0, 120, "Hur mycket över eller under sin egen guidance hamnade TSMC?",
                         "Summan av kvartalets månader (NT$, första version) mot B2:s mittpunkt (NT$, eller US$ × "
                         "antagen kurs från 2017Q3). Innehåller valutans avvikelse; känslighet i US$: "
                         "f1_surprise_tsmc_usd. Aktualitet: gräns 120 dagar."),
    "f1_surprise_tsmc_usd": (("surprise_usd",), "G6", "TSMC: kvartalsintäkt i US$ mot egen guidance i US$ (log ×100)",
                             "log ×100", "Q", 0, 120,
                             "Hur mycket över eller under sin guidance i US$ hamnade TSMC, utan valutan?",
                             "Känslighet (R11-7), inte i överraskningsindexet: kvartalsintäkten i US$ ur "
                             "pressmeddelandet (tsmc_rev_usd_q, första version) mot US$-mittpunkten känd dagen före, "
                             "från 2017Q3. f1_surprise_tsmc − f1_surprise_tsmc_usd = valutadelen, 100 × (ln faktisk "
                             "kurs − ln antagen kurs). Aktualitet: gräns 120 dagar."),
    "f1_surprise_nvda": (("surprise", "nvda"), "G6", "Nvidia: kvartalsintäkt mot egen guidance (log ×100)",
                         "log ×100", "Q", 0, 199, "Hur mycket över eller under sin egen guidance hamnade Nvidia?",
                         "rev_nvda (första version) mot nvda_guid_rev_mid, från 2017Q2. Aktualitet som Nvidia: gräns "
                         "199 dagar."),
    "f1_surprise_meta_capex": (("surprise", "meta"), "G5", "Meta: capex för året mot egen guidance (log ×100)",
                               "log ×100", "A", 0, 450, "Hur mycket över eller under sin capex-guidance hamnade Meta?",
                               "capex_meta + fin_lease_meta, årets fyra kvartal (första versioner), mot mittpunkten "
                               "för META_CAPEX_INCL_FL. Aktualitet: årsdata, gräns 450 dagar."),
    "f1_surprise_googl_capex": (("surprise", "googl"), "G5", "Alphabet: capex för året mot egen guidance (log ×100)",
                                "log ×100", "A", 0, 450,
                                "Hur mycket över eller under sin capex-guidance hamnade Alphabet?",
                                "capex_googl, årets fyra kvartal (första versioner), mot mittpunkten för GOOGL_CAPEX. "
                                "Aktualitet: årsdata, gräns 450 dagar."),
    "f1_surprise_index": (("surprise_index", "value"), "G6", "Överraskningsindex mot guidance (medel av z)",
                          "standardavvikelser", "Q", 0, 199,
                          "Överträffar bolagen sin egen guidance mer eller mindre än vanligt?",
                          "Medel av z = överraskning / bolagets SD av tidigare överraskningar (minst 4), minst 2 bolag. "
                          "Årets capex räknas i fjärde kvartalet. Aktualitet: gräns 199 dagar."),
    "f1_surprise_index_n": (("surprise_index", "n"), "G6", "Antal bolag i överraskningsindexet", "antal", "Q", 0, 199,
                            "Hur många bolag bygger överraskningsindexet på?",
                            "Antal z i kvartalets senaste version. Aktualitet: gräns 199 dagar."),
}
KEYS = list(SERIES)
# Series that read the curated CSV (R11-4): they list the guid_capex_* series of the companies they read as components
# and follow their publish flag, because they reveal the same values (G = U x exp(-s/100) for Meta and Alphabet).
CSV_BASED = ("f1_rev_index_4q", "f1_rev_index_q", "f1_rev_n_4q", "f1_rev_n_q", "f1_rev_median_4q", "f1_rev_median_q",
             "f1_surprise_meta_capex", "f1_surprise_googl_capex", "f1_surprise_index", "f1_surprise_index_n")
# Series that are sparse by construction (warehouse no_gaps check): a period without enough events or components has
# no value (register: n < 3 gives no index; the surprise index needs 2 companies).
KNOWN_GAPS = {
    "f1_rev_index_q": "no index in a quarter with fewer than 3 revisions",
    "f1_rev_index_4q": "no index when the 4 quarters hold fewer than 3 revisions",
    "f1_rev_median_q": "no median in a quarter without a revision with a size",
    "f1_rev_median_4q": "no median when the 4 quarters hold no revision with a size",
    "f1_surprise_index": "no index in a quarter with fewer than 2 companies' standardised surprises",
    "f1_surprise_index_n": "no version in a quarter with fewer than 2 companies' standardised surprises",
}


# Rows of the curated CSV that a CSV_BASED series reads: the companies; a series not listed reads every row (pooled).
# Meta's and Alphabet's surprises read only their own rows: capex_surprises selects the company's rows, standardize
# divides by the company's own earlier surprises, and _series keeps the company's rows (tests/test_agarbeslut.py fails
# if another company's rows change them). As licenses.CURATED_READS. The revision series pool every row, Microsoft's
# too. The surprise index reads only Meta's and Alphabet's rows as well, but as an index across companies it stays on
# the pooled gate (owner decision 2026-11-25 covered the guid_capex_* series and the two company surprises).
CSV_READS: dict[str, tuple[str, ...]] = {f"f1_surprise_{c}_capex": (c,) for c in CAPEX_SURPRISE}


@lru_cache(maxsize=1)
def csv_component_specs() -> tuple[Spec, ...]:
    """The guid_capex_* series built from the curated CSV (sources.guidance_capex.specs)."""
    return tuple(guidance_capex.specs())


def csv_company(key: str) -> str:
    """The company of a guid_capex_<company>_* key."""
    return key.removeprefix("guid_capex_").split("_", 1)[0]


def csv_component_keys(companies: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """Catalog keys of the guid_capex_* series, of `companies` only when given."""
    return tuple(s.key for s in csv_component_specs() if companies is None or csv_company(s.key) in companies)


def _spec(key: str) -> Spec:
    _kind, branch, label, unit, freq, lag, max_age, question, note = SERIES[key]
    if key in CSV_BASED:
        reads = CSV_READS.get(key)
        gate = csv_component_keys(reads)
        comps = COMPONENTS + gate
        publish = bool(gate) and all(s.publish for s in csv_component_specs() if s.key in gate)
        whose = "alla bolags rader" if reads is None else "bara bolagets egna rader"
        note += (f" Bygger på curated/guidance_capex.csv ({whose}) och följer därför publish-flaggan för "
                 f"guid_capex_*-serierna {'för alla bolag' if reads is None else 'för ' + '/'.join(reads)} (R11-4).")
    else:
        comps, publish = COMPONENTS, True
    return Spec(key=key, branch=branch, label=label, unit=unit, freq=freq, source=SOURCE, fetch=_fetch(key),
                lag_days=lag, license=LICENSE, revised=True, publish=publish, question=question, note=_NOTE + note,
                max_age_days=max_age, components=comps)


@lru_cache(maxsize=1)
def _tsmc_capex_records() -> pd.DataFrame:
    from ai_tracker.sources import tsmc_capex_guidance

    return tsmc_capex_guidance.records()


def _tsmc_capex(field: str):
    def fetch() -> pd.DataFrame:
        from ai_tracker.sources import tsmc_capex_guidance

        return tsmc_capex_guidance.vintages(_tsmc_capex_records(), field)
    return fetch


def _tsmc_capex_specs() -> list[Spec]:
    from ai_tracker.series.tsmc import LICENSE as TSMC_LICENSE

    return [Spec(key=f"tsmc_guid_capex_{f}", branch="G6", unit="MUSD", freq="A",
                 label=f"TSMC:s capex-utsikt för året, {'lägsta/punktvärde' if f == 'lo' else 'högsta/punktvärde'}",
                 source="SEC EDGAR, TSMC Form 6-K (kvartalsrapport: pressmeddelande och presentation)",
                 fetch=_tsmc_capex(f), lag_days=-800, license=TSMC_LICENSE, revised=True, publish=True,
                 question="Hur mycket sa TSMC att det skulle investera under året?",
                 note="Deterministisk tolkning (sources/tsmc_capex_guidance.py, F1) av de 6-K som tsmc_guidance läser. "
                      "period = året som guidas, known_from = 6-K:ns inlämningsdatum; en ändring är en ny vintage. "
                      "2016–2021 står budgeten i pressmeddelandet i januari och när den ändras; från 2022 bara "
                      "januaribudgeten (R11-8), så ändringar efter 2021 saknas. Andra ordalydelser kodas inte. Se "
                      "docs/resultat/f1_revideringar.md. Aktualitet: årets budget kommer i "
                      "januarirapporten, gräns 60 dagar efter årets slut.",
                 max_age_days=60)
            for f in ("lo", "hi")]


@lru_cache(maxsize=1)
def _tsmc_usd_records() -> pd.DataFrame:
    from ai_tracker.sources import tsmc_usd_revenue

    return tsmc_usd_revenue.records()


def _tsmc_usd() -> pd.DataFrame:
    from ai_tracker.sources import tsmc_usd_revenue

    return tsmc_usd_revenue.vintages(_tsmc_usd_records())


def _tsmc_usd_spec() -> Spec:
    from ai_tracker.series.tsmc import LICENSE as TSMC_LICENSE

    return Spec(key=TSMC_USD_TARGET, branch="G6", unit="MUSD", freq="Q",
                label="TSMC:s kvartalsintäkt i US$ (pressmeddelandet)",
                source="SEC EDGAR, TSMC Form 6-K (kvartalsrapportens pressmeddelande)", fetch=_tsmc_usd,
                lag_days=20, license=TSMC_LICENSE, revised=True, publish=True,
                question="Hur stor var TSMC:s kvartalsintäkt i US$, den valuta TSMC guidar i?",
                note="Deterministisk tolkning (sources/tsmc_usd_revenue.py, rättning efter R11-7) av meningen "
                     "\"In US dollars, <kvartal> quarter revenue was $x billion\" i de 6-K som tsmc_guidance läser, "
                     "från 2017-01 (2016Q4). known_from = 6-K:ns inlämningsdatum. Används för F1:s känslighet i US$.")


SPECS = [_spec(k) for k in KEYS] + _tsmc_capex_specs() + [_tsmc_usd_spec()]
