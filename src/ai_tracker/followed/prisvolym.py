"""PV1 "Pris mot volym": the monthly report of the followed question (register 2026-11-27 "PV1").

"Följs prisfallet vid fast förmåga (G2) av högre användning (G3), och ändras sambandet?"

Read with F0's symmetric rule (common.read_rule): the change in pace of the price at fixed capability (quarterly mean
of a monthly G2 series) against the change in pace of SDK downloads on npm (quarterly mean of weekly sums), sign -1
(the price falling faster is expected to be followed by usage accelerating, and the mirror image), g = 50, h = 20,
k = 2, three rows:

    H  GPQA price (G2's core series)           against npm openai + @anthropic-ai/sdk     (the main reading)
    a  Arena price, variant A                  against the same
    b  GPQA price                              against the same relative to react + express (the npm control)

Derived quantities (keys pv1_*) are not catalog series: they are computed here from catalog series and measured with
common.path_measures (the formulas of state.measures). Months become quarters as the mean of the quarter's three
months (aggregate.derive with monthly frequency); weeks belong to the quarter of their Thursday and a quarter is the
mean of its weekly sums, only once every week of the quarter is known (register PV1, (b)).

Beside the three locked readings, register X26 (point 2, after R29-2) adds H-G, a-G and b-G: the same series,
statistic, bounds, window and sign, with the quarter as the geometric mean (exp of the mean of ln) of its months and
of its weekly sums. ln of an arithmetic mean is not minus ln of the mean of the inverses, so with the locked arithmetic
mean a mirrored price path (1/x) does not give the mirrored change in pace; with the geometric mean it does exactly.
H stays the main reading.

Only rows known on the as-of date are used: the table is cut at the day before anything is computed, so
compute(d, table) equals compute(d, table truncated at d).
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd

from ai_tracker import observations
from ai_tracker.followed import aggregate as A
from ai_tracker.followed import common as C

QUESTION = "Följs prisfallet vid fast förmåga (G2) av högre användning (G3), och ändras sambandet?"
REGISTERED = "2026-11-27"  # the register entry; every month and week published by then was known before it
FIRST_UNSEEN = "2026Q4"  # the first quarter of npm weeks and price months after the entry (entry, (g))

# ------------------------------------------------------------------ inputs (register PV1, (b))

PRICE_GPQA = "g2_price_at_capability_gpqa"
PRICE_ARENA = "g2_price_at_arena_capability"
SDK = ("g3_npm_openai_w", "g3_npm_anthropic_sdk_w")
CONTROL = ("g3_npm_react_w", "g3_npm_express_w")

# derived quantity -> (frequency of the inputs, the input series summed per period)
DERIVED = {
    "pv1_pris_gpqa_q": ("M", (PRICE_GPQA,)),
    "pv1_pris_arena_q": ("M", (PRICE_ARENA,)),
    "pv1_sdk_q": ("W", SDK),
    "pv1_kontroll_q": ("W", CONTROL),
}
RATIO = {"pv1_sdk_rel_q": ("pv1_sdk_q", "pv1_kontroll_q")}
# register X26, point 2: the same quantities with the quarter as the geometric mean of its months or weekly sums
DERIVED_G = {
    "pv1_pris_gpqa_gq": ("M", (PRICE_GPQA,)),
    "pv1_pris_arena_gq": ("M", (PRICE_ARENA,)),
    "pv1_sdk_gq": ("W", SDK),
    "pv1_kontroll_gq": ("W", CONTROL),
}
RATIO_G = {"pv1_sdk_rel_gq": ("pv1_sdk_gq", "pv1_kontroll_gq")}
ALL_DERIVED = {**DERIVED, **DERIVED_G}
ALL_RATIO = {**RATIO, **RATIO_G}

CONTEXT_PRICE = ("g2_price_at_arena_capability_4o", "g2_price_at_capability", "g2_price_rolling12_eci",
                 "g2_price_rolling12_arena", "g2_price_rolling6_arena", "g2_price_frontier_arena")
CONTEXT_NPM = ("g3_npm_openai_w", "g3_npm_anthropic_sdk_w", "g3_npm_google_genai_w", "g3_npm_google_generative_ai_w",
               "g3_npm_vercel_ai_w", "g3_npm_langchain_w", "g3_npm_langchain_core_w", "g3_npm_mcp_sdk_w",
               "g3_npm_react_w", "g3_npm_express_w")

# ------------------------------------------------------------------ the locked reading (register PV1, (c))

READINGS = {  # name -> (X, Y)
    "H": ("pv1_pris_gpqa_q", "pv1_sdk_q"),
    "a": ("pv1_pris_arena_q", "pv1_sdk_q"),
    "b": ("pv1_pris_gpqa_q", "pv1_sdk_rel_q"),
}
MAIN = "H"
READINGS_G = {  # register X26, point 2: beside the locked readings, not instead of them
    "H-G": ("pv1_pris_gpqa_gq", "pv1_sdk_gq"),
    "a-G": ("pv1_pris_arena_gq", "pv1_sdk_gq"),
    "b-G": ("pv1_pris_gpqa_gq", "pv1_sdk_rel_gq"),
}
X26_REGISTERED = "2026-11-27"  # register "X26: rättning av S1, QA1 och PV1 efter granskningen R29"
X_STAT = "change"
G = 50.0  # X: change in pace of the price, log x100
H = 20.0  # Y: change in pace of the downloads, log x100
K = 2
SIGN = -1

READING_NAME = {"H": "Pris vid fast förmåga (GPQA) mot SDK-nedladdningar (huvudläsning)",
                "a": "Pris vid fast Arena-förmåga (variant A) mot SDK-nedladdningar (bisak a)",
                "b": "Pris vid fast förmåga (GPQA) mot SDK-nedladdningar relativt kontrollpaketen (bisak b)"}
READING_NAME.update({
    "H-G": "Pris vid fast förmåga (GPQA) mot SDK-nedladdningar, geometriskt medel (H-G, bredvid H)",
    "a-G": "Pris vid fast Arena-förmåga (variant A) mot SDK-nedladdningar, geometriskt medel (a-G, bredvid a)",
    "b-G": "Pris vid fast förmåga (GPQA) mot SDK-nedladdningar relativt kontrollpaketen, geometriskt medel (b-G, "
           "bredvid b)"})
SHORT_NAME = {"a": "Bisak a (Arena-pris mot SDK)", "b": "Bisak b (GPQA-pris mot SDK relativt kontroll)"}

LABEL = {
    "pv1_pris_gpqa_q": "Pris vid fast förmåga, GPQA (kärnserie)",
    "pv1_pris_arena_q": "Pris vid fast Arena-förmåga, variant A",
    "pv1_sdk_q": "SDK-nedladdningar, openai + @anthropic-ai/sdk",
    "pv1_kontroll_q": "Kontrollpaket, react + express",
    "pv1_sdk_rel_q": "SDK relativt kontroll (kvot)",
    "pv1_pris_gpqa_gq": "Pris vid fast förmåga, GPQA, geometriskt medel",
    "pv1_pris_arena_gq": "Pris vid fast Arena-förmåga, variant A, geometriskt medel",
    "pv1_sdk_gq": "SDK-nedladdningar, geometriskt medel",
    "pv1_kontroll_gq": "Kontrollpaket, geometriskt medel",
    "pv1_sdk_rel_gq": "SDK relativt kontroll, geometriska medel (kvot)",
    "g2_price_at_arena_capability_4o": "Pris vid fast Arena-förmåga, variant B (GPT-4o)",
    "g2_price_at_capability": "Pris vid fast förmåga, ECI (bakåtfylld)",
    "g2_price_rolling12_eci": "Pris vid rörlig tröskel, ECI, 12 mån",
    "g2_price_rolling12_arena": "Pris vid rörlig tröskel, Arena, 12 mån",
    "g2_price_rolling6_arena": "Pris vid rörlig tröskel, Arena, 6 mån",
    "g2_price_frontier_arena": "Frontpris, Arena",
    "g3_npm_openai_w": "npm openai", "g3_npm_anthropic_sdk_w": "npm @anthropic-ai/sdk",
    "g3_npm_google_genai_w": "npm @google/genai", "g3_npm_google_generative_ai_w": "npm @google/generative-ai",
    "g3_npm_vercel_ai_w": "npm ai (Vercel)", "g3_npm_langchain_w": "npm langchain",
    "g3_npm_langchain_core_w": "npm @langchain/core", "g3_npm_mcp_sdk_w": "npm @modelcontextprotocol/sdk",
    "g3_npm_react_w": "npm react (kontroll)", "g3_npm_express_w": "npm express (kontroll)",
}


def used_series() -> set[str]:
    """Every catalog series the report reads."""
    out = {*CONTEXT_PRICE, *CONTEXT_NPM}
    for _, keys in ALL_DERIVED.values():
        out.update(keys)
    return out


# ------------------------------------------------------------------ months and weeks to quarters


def _latest(table: pd.DataFrame, key: str) -> pd.DataFrame:
    """period, value, known_from of the latest vintage per period (the table is already cut at the day)."""
    t = table[table["series"] == key]
    if t.empty:
        return pd.DataFrame(columns=["period", "value", "known_from"])
    return (t.sort_values("known_from", kind="stable").groupby("period")[["value", "known_from"]].last()
            .reset_index())


def monthly_formula(key: str, series: tuple[str, ...]) -> A.Formula:
    """The mean of the quarter's three months of the sum of `series` (months m, m-1, m-2; register PV1, (b))."""
    return A.Formula(key, tuple(A.Term(s, k, 1.0 / 3.0) for s in series for k in range(3)))


def _log_months(table: pd.DataFrame, series: tuple[str, ...]) -> pd.DataFrame:
    """The rows of one monthly series with ln(value) (register X26, point 2). A month whose latest vintage on the day is
    <= 0 has no logarithm: all its rows are dropped, so the quarter that needs it has no value."""
    if len(series) != 1:
        raise ValueError("the geometric mean of months is defined for one series")
    t = table[table["series"] == series[0]].copy()
    if t.empty:
        return t
    last = t.sort_values("known_from", kind="stable").groupby("period")["value"].last()
    bad = set(last[last <= 0].index)
    t = t[~t["period"].isin(bad) & (t["value"] > 0)].copy()
    t["value"] = [math.log(v) for v in t["value"]]
    return t


def monthly_quarters(table: pd.DataFrame, series: tuple[str, ...], key: str = "pv1",
                     geometric: bool = False) -> dict[str, tuple[float, str]]:
    """{quarter: (mean of its three months, known_from)} with aggregate.derive at monthly frequency: a quarter exists
    only once all three months of every series are known, dated by the latest of them. geometric=True (register X26,
    point 2): exp of the mean of the months' ln, for one series."""
    src = _log_months(table, series) if geometric else table
    rows = A.derive(monthly_formula(key, series), src, freq="M")
    if rows.empty:
        return {}
    rows = rows.sort_values("known_from", kind="stable").groupby("period").last()
    out = {}
    for p, r in rows.iterrows():
        m = pd.Period(p, freq="M")
        if m.month % 3 == 0:
            v = float(r["value"])
            out[C.quarter(m)] = (math.exp(v) if geometric else v, str(pd.Timestamp(r["known_from"]).date()))
    return out


def week_monday(period: str) -> pd.Timestamp:
    """The Monday of a W-SUN period string 'YYYY-MM-DD/YYYY-MM-DD'."""
    return pd.Timestamp(str(period).split("/")[0])


def week_quarter(period: str) -> str:
    """The quarter of a week: the quarter that holds its Thursday (Monday + 3 days)."""
    return C.quarter(week_monday(period) + pd.Timedelta(days=3))


def quarter_weeks(q: str) -> list[pd.Timestamp]:
    """The Mondays of the weeks that belong to quarter q (their Thursday lies in q)."""
    p = pd.Period(q, freq=A.QFREQ)
    start, end = p.start_time.normalize(), p.end_time.normalize()
    th = start + pd.Timedelta(days=(3 - start.weekday()) % 7)  # first Thursday on or after the quarter's first day
    out = []
    while th <= end:
        out.append(th - pd.Timedelta(days=3))
        th += pd.Timedelta(days=7)
    return out


def weekly_sums(table: pd.DataFrame, series: tuple[str, ...]) -> dict[pd.Timestamp, tuple[float, pd.Timestamp]]:
    """{Monday: (sum over `series`, known_from)}: a week only when every series has it (the latest vintage on the day)."""
    per = []
    for s in series:
        d = _latest(table, s)
        per.append({week_monday(p): (float(v), pd.Timestamp(kf)) for p, v, kf in
                    zip(d["period"], d["value"], d["known_from"])})
    if not per:
        return {}
    weeks = set(per[0]).intersection(*per[1:]) if len(per) > 1 else set(per[0])
    return {w: (sum(x[w][0] for x in per), max(x[w][1] for x in per)) for w in sorted(weeks)}


def weekly_quarters(table: pd.DataFrame, series: tuple[str, ...],
                    geometric: bool = False) -> dict[str, tuple[float, str]]:
    """{quarter: (mean of its weekly sums, known_from)}: a quarter only once every week that belongs to it is known.
    geometric=True (register X26, point 2): exp of the mean of ln of the weekly sums, and no quarter when a weekly sum
    is <= 0."""
    ws = weekly_sums(table, series)
    if not ws:
        return {}
    qs = sorted({C.quarter(w + pd.Timedelta(days=3)) for w in ws}, key=lambda q: pd.Period(q, freq=A.QFREQ))
    out = {}
    for q in qs:
        need = quarter_weeks(q)
        if not all(w in ws for w in need):
            continue
        kf = str(max(ws[w][1] for w in need).date())
        vs = [ws[w][0] for w in need]
        if not geometric:
            out[q] = (sum(vs) / len(vs), kf)
        elif all(v > 0 for v in vs):
            out[q] = (math.exp(sum(math.log(v) for v in vs) / len(vs)), kf)
    return out


def missing_weeks(table: pd.DataFrame, series: tuple[str, ...], q: str) -> dict[str, int]:
    """{series: number of q's weeks without a value on the day} (only series that lack some)."""
    need = quarter_weeks(q)
    out = {}
    for s in series:
        have = {week_monday(p) for p in _latest(table, s)["period"]}
        n = sum(w not in have for w in need)
        if n:
            out[s] = n
    return out


def missing_months(table: pd.DataFrame, series: tuple[str, ...], q: str, when) -> dict[str, list[str]]:
    last = str(pd.Period(q, freq=A.QFREQ).asfreq("M", "end"))
    by: dict[str, list[str]] = {}
    for s, p in A.missing(monthly_formula("pv1", series), table, last, when, freq="M"):
        by.setdefault(s, []).append(p)
    return {s: sorted(ps) for s, ps in by.items()}


# ------------------------------------------------------------------ measures


def quarterly_measure(key: str, values: dict[str, tuple[float, str]], extra: dict | None = None) -> dict:
    """measure()-shaped dict of a quarterly derived quantity {quarter: (value, known_from)}."""
    base = {"series": key, "derived": True, "method": "log", "pace_unit": "log ×100 per år",
            "surprise_basis": "B1 drift (log x100)", **(extra or {})}
    if not values:
        return {**base, "available": False, "path": {}}
    pm = C.path_measures({q: v for q, (v, _) in values.items()}, "log")
    ok = pm[pm["level"].notna()]
    p = ok.index[-1]
    r = ok.loc[p]
    return {**base, "available": True, "period": p, "known_from": values[p][1], "level": C.num(r["level"]),
            "pace": C.num(r["pace"]), "change": C.num(r["change"]), "surprise": C.num(r["surprise"]),
            "first": ok.index[0],
            "path": {q: {c: C.num(v) for c, v in pm.loc[q, ["level", "pace", "change"]].items()} for q in pm.index}}


def first_known(m: dict, col: str) -> str | None:
    qs = [q for q, v in C.series_of(m, col).items() if v is not None]
    return min(qs, key=lambda q: pd.Period(q, freq=A.QFREQ)) if qs else None


# ------------------------------------------------------------------ licence classes


def classes(keys) -> dict[str, str]:
    """{series: commercial-use class} from ai_tracker.licenses (a derived quantity takes its most restrictive input)."""
    from ai_tracker import catalog, licenses

    specs = catalog.by_key()
    out = {}
    for k in keys:
        if k in specs:
            try:
                out[k] = licenses.classify(specs[k], specs)[0]
            except licenses.Unclassified:
                out[k] = licenses.OKAND
    for key, (_, comps) in ALL_DERIVED.items():
        cs = [out.get(c, licenses.OKAND) for c in comps]
        out[key] = max(cs, key=lambda c: licenses.RANK[c])
    for key, (a, b) in ALL_RATIO.items():
        out[key] = max((out[a], out[b]), key=lambda c: licenses.RANK[c])
    return out


# ------------------------------------------------------------------ compute


def _cut(table: pd.DataFrame | None, when: pd.Timestamp) -> pd.DataFrame:
    table = observations.load() if table is None else table
    t = table[table["series"].isin(used_series())].copy()
    t["known_from"] = pd.to_datetime(t["known_from"])
    if "fetched_at" in t:
        t["fetched_at"] = pd.to_datetime(t["fetched_at"])
    return t[t["known_from"] <= when].reset_index(drop=True)


def decided(r: dict, x: dict, y: dict) -> list[dict]:
    """The origins before t whose outcome was talar för or talar emot, in time order ("ändras sambandet?", register
    PV1, (c)): the same rows as read_rule's history."""
    t = r.get("t")
    if t is None:
        return []
    tp = pd.Period(t, freq=A.QFREQ)
    p = r["params"]
    kw = {"g": p["g"], "h": p["h"], "k": p["k"], "sign": p["sign"]}
    qs = sorted((q for q in x if pd.Period(q, freq=A.QFREQ) < tp), key=lambda q: pd.Period(q, freq=A.QFREQ))
    rows = [C.origin_outcome(q, x, y, t, **kw) for q in qs]
    return [{"origin": o["origin"], "outcome": o["outcome"], "direction": o["direction"], "x": o["x"], "y": o["y"],
             "decided_at": o["decided_at"]} for o in rows if o["outcome"] in (C.FOR, C.AGAINST)]


def fetch_summary(t: pd.DataFrame, when: pd.Timestamp) -> dict:
    """When the rows the readings use were fetched (register X26, point 3): the history is a backfill fetched in one go,
    with known_from set by rule, not archived vintages."""
    inputs = {s for _, keys in DERIVED.values() for s in keys}
    x = t[t["series"].isin(inputs)]
    if x.empty or "fetched_at" not in x or x["fetched_at"].isna().all():
        return {"n": int(len(x)), "first": None, "last": None, "after": 0}
    f = pd.to_datetime(x["fetched_at"])
    return {"n": int(len(x)), "first": str(f.min().date()), "last": str(f.max().date()),
            "after": int((f.dt.normalize() > when.normalize()).sum())}


def _week_known(monday: pd.Timestamp) -> pd.Timestamp:
    return monday + pd.Timedelta(days=6 + 2)  # Sunday + 2 days (utvecklaradoption.md, known_from)


def next_unseen(r: dict) -> tuple[str, str | None]:
    """The next reading with a Y quarter that was not known at the entry, and when the main reading's X first has a
    change in pace (entry, (g))."""
    y = r["measures"]["pv1_sdk_q"]
    t = y.get("period") if y.get("available") else None
    target = FIRST_UNSEEN if t is None else max(C.plus(t, 1), FIRST_UNSEEN, key=lambda q: pd.Period(q, freq=A.QFREQ))
    last = quarter_weeks(target)[-1]
    day = str(_week_known(last).date())
    text = (f"npm-kvartalet {target} när veckan {last.date()}–{(last + pd.Timedelta(days=6)).date()} är känd, omkring "
            f"{day}")
    x = r["measures"]["pv1_pris_gpqa_q"]
    if first_known(x, "change") is None:
        start = x.get("first") if x.get("available") else None
        q0 = C.plus(start, 6) if start else None
        if q0 is not None:
            q0 = max(q0, FIRST_UNSEEN, key=lambda q: pd.Period(q, freq=A.QFREQ))
            xday = str((pd.Period(q0, freq=A.QFREQ).end_time.normalize() + pd.Timedelta(days=1)).date())
            q1 = C.plus(q0, 1)
            yday = str(_week_known(quarter_weeks(q1)[-1]).date())
            text += (f". Huvudläsningens X (GPQA-priset) får sin första förändring i takt för {q0} omkring {xday}, och "
                     f"huvudläsningen kan avgöras tidigast med npm-kvartalet {q1}, omkring {yday}")
    return text, day


def compute(as_of, table: pd.DataFrame | None = None) -> dict:
    """The report as of `as_of`. Each reading gets "seen" (register X25, point 1, with PV1's register day): True when
    every value its outcome rests on is the same as in the report as of the register day; always True up to it."""
    when = pd.Timestamp(as_of)
    table = observations.load() if table is None else table
    r = _compute(when, table)
    reg = _compute(pd.Timestamp(REGISTERED), table) if when > pd.Timestamp(REGISTERED) else None
    for x in [*r["readings"].values(), *r["readings_geo"].values()]:  # X26 shares PV1's register day
        if reg is None:
            x["seen"] = True
            continue
        now = (C.series_of(r["measures"][x["x_series"]], X_STAT), C.series_of(r["measures"][x["y_series"]], "change"))
        then = (C.series_of(reg["measures"][x["x_series"]], X_STAT),
                C.series_of(reg["measures"][x["y_series"]], "change"))
        x["seen"] = C.same_inputs(x, *now, *then)
    r["seen_before_register"] = all(x["seen"] for x in r["readings"].values())
    r["main_seen"] = r["readings"][MAIN]["seen"]
    return r


def _compute(when: pd.Timestamp, table: pd.DataFrame) -> dict:
    t = _cut(table, when)
    ms: dict[str, dict] = {}
    vals: dict[str, dict] = {}
    for key, (freq, series) in ALL_DERIVED.items():
        geo = key in DERIVED_G
        vals[key] = (monthly_quarters(t, series, key, geometric=geo) if freq == "M"
                     else weekly_quarters(t, series, geometric=geo))
    for key, (a, b) in ALL_RATIO.items():
        vals[key] = {q: (vals[a][q][0] / vals[b][q][0], max(vals[a][q][1], vals[b][q][1]))
                     for q in vals[a] if q in vals[b] and vals[b][q][0] > 0}
    for key, v in vals.items():
        freq, series = ALL_DERIVED.get(key, ("Q", ALL_RATIO.get(key, ())))
        m = quarterly_measure(key, v, {"components": list(series), "freq_in": freq})
        if m["available"]:
            nxt = C.plus(m["period"], 1)
            if freq == "M":
                m["missing_next"] = {"period": nxt, "months": missing_months(t, series, nxt, when)}
            elif freq == "W":
                m["missing_next"] = {"period": nxt, "weeks": missing_weeks(t, series, nxt)}
        ms[key] = m
    for key in CONTEXT_PRICE:
        ms[key] = quarterly_measure(key, monthly_quarters(t, (key,), key), {"components": [key], "freq_in": "M"})
    for key in CONTEXT_NPM:
        if key not in ms:
            ms[key] = quarterly_measure(key, weekly_quarters(t, (key,)), {"components": [key], "freq_in": "W"})
    readings: dict[str, dict] = {}
    readings_geo: dict[str, dict] = {}
    for target, spec in ((readings, READINGS), (readings_geo, READINGS_G)):
        for name, (x, y) in spec.items():
            rr = C.read_measures(ms[x], ms[y], x_stat=X_STAT, g=G, h=H, k=K, sign=SIGN)
            target[name] = {**rr, "name": name, "x_first": first_known(ms[x], X_STAT),
                            "y_first": first_known(ms[y], "change"),
                            "decided": decided(rr, C.series_of(ms[x], X_STAT), C.series_of(ms[y], "change"))}
    report = {
        "question": QUESTION, "as_of": str(when.date()), "generated": str(date.today()),
        "params": {"g": G, "h": H, "k": K, "sign": SIGN, "x_stat": X_STAT, "main": MAIN},
        "measures": ms, "readings": readings, "readings_geo": readings_geo, "classes": classes(used_series()),
        "fetch": fetch_summary(t, when),
    }
    report["next_unseen"], report["next_unseen_date"] = next_unseen(report)
    return report


# ------------------------------------------------------------------ render

_f = C.fmt


def _who(key: str) -> str:
    return LABEL.get(key, key)


def _level(key: str):
    if key.startswith("g3_npm") or key in ("pv1_sdk_q", "pv1_kontroll_q", "pv1_sdk_gq", "pv1_kontroll_gq"):
        return lambda x: "–" if C.num(x) is None else f"{_f(x / 1e6, 1)} M/vecka"
    if key in ("pv1_sdk_rel_q", "pv1_sdk_rel_gq"):
        return lambda x: _f(x, 3)
    return lambda x: "–" if C.num(x) is None else f"{_f(x, 4)} USD"


HEAD = ["| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie | Klass |",
        "|---|---|---|---|---|---|---|---|---|"]


def _table(r: dict, keys) -> list[str]:
    ms, cl = r["measures"], r["classes"]
    lines = list(HEAD)
    for k in keys:
        m = ms[k]
        if not m.get("available"):
            lines.append(f"| {_who(k)} | – | – | – | – | – | – | `{k}` | {cl.get(k, '–')} |")
            continue
        lines.append(f"| {_who(k)} | {_level(k)(m['level'])} | {_f(m['pace'], 1, True)} | {_f(m['change'], 1, True)} "
                     f"| {_f(m['surprise'], 1, True)} | {m['period']} | {m['known_from']} | `{k}` | {cl.get(k, '–')} |")
    return lines


def _missing_lines(ms: dict, keys) -> list[str]:
    out = []
    for k in keys:
        mn = ms[k].get("missing_next") or {}
        if mn.get("months"):
            parts = [f"`{s}` {', '.join(ps)}" for s, ps in mn["months"].items()]
            out.append(f"- {_who(k)}: {mn['period']} saknar på dagen {'; '.join(parts)}.")
        if mn.get("weeks"):
            parts = [f"`{s}` {n} veckor" for s, n in mn["weeks"].items()]
            out.append(f"- {_who(k)}: {mn['period']} saknar på dagen {'; '.join(parts)}.")
    return out


def short(r: dict) -> str:
    """The outcome with the impulse's direction for 'talar för' and 'talar emot'."""
    o = next((x for x in r["origins"] if x["origin"] == r["origin"]), None)
    text = C.OUTCOME_TEXT[r["outcome"]]
    if o is not None and r["outcome"] in (C.FOR, C.AGAINST):
        text += ", uppåt" if o["direction"] > 0 else ", nedåt"
    return text


def _decided_lines(rr: dict) -> list[str]:
    d = rr.get("decided") or []
    if not d:
        return ["  Ändras sambandet? Inget ursprung har avgjorts (talar för eller talar emot) i historiken på dagen."]
    parts = [f"{x['origin']} {C.OUTCOME_TEXT[x['outcome']]}, {'uppåt' if x['direction'] > 0 else 'nedåt'} "
             f"(X {_f(x['x'], 1, True)}, Y {_f(x['y'], 1, True)} vid {x['decided_at']})" for x in d]
    last, before = d[-1], d[:-1]
    n_for = sum(x["outcome"] == C.FOR for x in before)
    n_ag = sum(x["outcome"] == C.AGAINST for x in before)
    s = (f"  Ändras sambandet? Avgjorda ursprung i tidsordning: {'; '.join(parts)}. Senaste: "
         f"{C.OUTCOME_TEXT[last['outcome']]} ({last['origin']})")
    s += (f", tidigare {n_for} talar för och {n_ag} talar emot." if before else ", inga tidigare.")
    return [s + " En beskrivning utan gräns för \"ändrat\"; med så få ursprung kan en skillnad vara slump."]


def render(r: dict) -> str:
    ms = r["measures"]
    p = r["params"]
    out = [f"# Pris mot volym per {r['as_of']}", "", f"**Frågan:** {r['question']}", "",
           "Priset vid fast förmåga (G2) mot nedladdningar av AI-SDK:er på npm (G3). Kvartal: priset som medel av "
           "kvartalets tre månader, nedladdningarna som medel av veckosummorna för veckorna vars torsdag ligger i "
           "kvartalet (bara hela kvartal). Takt = 100 × ln(värdet / värdet fyra kvartal tidigare). Förändring i takt = "
           "mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1. Bara data kända på dagen. Registret: "
           "`docs/mattregister.md`, 2026-11-27 PV1. Klass = klass för kommersiell användning (`ai_tracker.licenses`).", ""]

    out += ["## 1. Pris vid fast förmåga (X)", "",
            "Lägsta blandade förstapartspris (USD per miljon tokens, 3:1) bland modeller över en fast förmågetröskel. "
            "GPQA-varianten är G2:s kärnserie. Arena-variant A är inte kärnserie och mäter från 2024-07 golvet i de "
            "billigaste prisnivåerna, eftersom tröskeln inte binder (`docs/kallor/g2_arena_pris.md`). Övriga rader är "
            "beskrivning.", ""]
    out += _table(r, ["pv1_pris_gpqa_q", "pv1_pris_arena_q", *CONTEXT_PRICE])
    out += _missing_lines(ms, ["pv1_pris_gpqa_q", "pv1_pris_arena_q"])

    out += ["", "## 2. Användning: nedladdningar på npm (Y)", "",
            "Nedladdningar per vecka, kvartalsmedel. Huvudläsningens Y är openai + @anthropic-ai/sdk. Bisak b läser "
            "samma summa relativt kontrollpaketen react + express, så att den gemensamma tillväxten i npm (CI, speglar) "
            "tas bort så långt kontrollen speglar den. Nedladdningar är inte användare. Övriga paket är beskrivning.", ""]
    out += _table(r, ["pv1_sdk_q", "pv1_kontroll_q", "pv1_sdk_rel_q", *CONTEXT_NPM])
    out += _missing_lines(ms, ["pv1_sdk_q", "pv1_kontroll_q"])

    out += ["", "## 3. Läsregeln, mekaniskt", "",
            f"F0:s symmetriska regel: X:s förändring i takt mot Y:s förändring i takt, tecken −1, fönster {p['k']} "
            f"kvartal efter ursprunget. Gränser (låsta): X ±{_f(p['g'], 0)}, Y ±{_f(p['h'], 0)} log-punkter. En rad "
            "per par, ingen sammanslagning.", "",
            "- **Talar för, nedåt:** prisfallet blev snabbare (X ≤ −g) och användningen accelererade (Y ≥ +h). "
            "**Talar för, uppåt:** prisfallet blev långsammare (X ≥ +g) och användningen bromsade (Y ≤ −h).",
            "- **Talar emot:** användningens takt gick åt samma håll som priset: prisfallet blev snabbare och användningen "
            "bromsade, eller prisfallet blev långsammare och användningen accelererade.",
            "- Förändringen i takt läser om tillväxten blir snabbare eller långsammare, inte om nivån stiger eller "
            "faller. Utslaget är en beskrivning, inget test.", ""]
    unseen = [k for k, x in r["readings"].items() if x.get("seen") is False]
    if not unseen:
        out += [f"Alla läsningar nedan vilar bara på värden som var kända före registerposten {REGISTERED}. Ingen av "
                f"dem är därför ett utfall på osedda data. Nästa osedda läsning: {r['next_unseen']}. Sedda data avgörs "
                "per läsning (X25, punkt 1).", ""]
    else:
        out += [f"{len(unseen)} av {len(r['readings'])} läsningar vilar på värden som blev kända efter registerposten "
                f"{REGISTERED} och är märkta **osedd** nedan. Sedda data avgörs per läsning (X25, punkt 1).", ""]
    for name, rr in r["readings"].items():
        label = READING_NAME[name]
        lines = C.reading_lines(rr, label)
        lines[0] = lines[0].replace(f"**{label}:** {rr['text']}", f"**{label}:** {short(rr)}", 1)
        if rr.get("x_first") is None:
            lines.append("  X har ännu ingen förändring i takt på dagen (serien är för kort), så varje ursprung kan "
                         "inte avgöras.")
        elif rr.get("y_first") and pd.Period(rr["x_first"], freq=A.QFREQ) < pd.Period(rr["y_first"], freq=A.QFREQ):
            lines.append(f"  X har förändring i takt från {rr['x_first']} och Y från {rr['y_first']}.")
        else:
            lines.append(f"  X har förändring i takt från {rr['x_first']}.")
        lines += _decided_lines(rr)
        if name == MAIN:
            lines.append("  " + C.seen_text(rr.get("seen"), REGISTERED))
        elif rr.get("seen") is False:
            lines.append(f"  **Osedd:** läsningen vilar på värden som blev kända efter registerposten {REGISTERED}.")
        elif name == "a":
            lines.append("  Bisak a vilar på X-värden som var sedda före posten (nivåerna för variant A stod i "
                         "`g2_arena_pris.md`, registret avsnitt (f)) och har bara beskrivande värde.")
        out += lines
    out.append("")

    out += ["## 4. Att bevaka", "",
            f"- Nästa osedda läsning: {r['next_unseen']}.",
            "- Prisserierna får en ny månad dagen efter månadsslut, npm en ny vecka söndag + 2 dagar. Ett kvartal räknas "
            "först när alla dess månader eller veckor är kända.", "",
            "## 5. Förbehåll", "",
            "- **Pris per token, inte per uppgift.** Resonemangsmodeller använder fler tokens per uppgift. Ett snabbare "
            "prisfall per token kan vara ett långsammare fall, eller en ökning, per uppgift (`docs/riktning.md` "
            "avsnitt 4).",
            "- **Gemensam orsak.** En lansering kan både sänka priset (en billig modell kvalificerar) och dra "
            "nedladdningar (ny SDK-version, nya funktioner, uppmärksamhet). Regeln läser Y först kvartalet efter, men "
            "en lansering kan verka över flera kvartal. Ett utslag som talar för mekanismen visar inte att priset "
            "orsakade användningen.",
            "- **Nedladdningar är inte användare.** CI-byggen, containerbyggen, speglar och transitiva beroenden räknas "
            "med, och ett verktyg som börjar bero på en SDK höjer nivån utan nya utvecklare. Kontrollpaketen i bisak b "
            "är inte stabila och tar inte bort skiften i en enskild SDK.",
            "- **Förstapartspris.** Öppna modeller som bara säljs av tredje part ingår inte. Arena-variant A mäter "
            "golvet i de billigaste nivåerna från 2024-07, inte priset vid en fast förmåga.",
            "- **Urval.** npm-paketen valdes 2026-11-23 med kunskap om vilka SDK:er som blev stora. Googles SDK:er ingår "
            "inte i summan, eftersom bytet mellan två paket är en migrering.",
            "- **Korta serier.** GPQA-priset har förändring i takt först från 2026Q4. Med en handfull ursprung är detta "
            "en beskrivning och inget test, och utfall kan vara slump.",
            "- **Licens.** npm-serierna har klassen `okänd` och `publish=False`, Arena-variant A `okänd`. GPQA-priset har "
            "`ja`. Cloudflare Radar (`nej`) används inte.",
            backfill_caveat(r), ""]
    out += render_geo(r)
    return "\n".join(out)


def backfill_caveat(r: dict) -> str:
    """Register X26, point 3 (R29-3): the history is a backfill."""
    f = r.get("fetch") or {}
    when = (f"hämtade {f['first']}–{f['last']}" if f.get("first") and f["first"] != f["last"]
            else f"hämtade {f['first']}" if f.get("first") else "utan hämtningsdatum")
    after = (f" {f['after']} av {f['n']} rader som läsningarna använder hämtades efter läsdagen." if f.get("after")
             else f" Ingen av de {f.get('n', 0)} rader som läsningarna använder hämtades efter läsdagen, men de "
                  "hämtades ändå i efterhand i en omgång.")
    return ("- **Historiken är backfill.** Pris- och npm-raderna är " + when + ", i efterhand, med `known_from` satt "
            "efter en regel (prisserierna vid månadsslut eller dagen efter, npm söndag + 2 dagar), inte som arkiverade "
            "versioner. \"Bara data kända på dagen\" gäller därför `known_from` och inte vad källan visade då: en läsning "
            "per en tidigare dag kan innehålla revideringar och rättningar som inte var kända den dagen." + after)


def _same_text(geo: dict, locked: dict) -> str:
    if geo["outcome"] == locked["outcome"] and short(geo) == short(locked):
        return "Samma utslag som den låsta raden."
    return f"Den låsta raden: {short(locked)}."


def render_geo(r: dict) -> list[str]:
    """Register X26, point 2 (R29-2): H-G, a-G and b-G beside the locked readings, in a section of their own."""
    out = ["## 6. Geometriskt kvartalsmedel (tillägg X26, bredvid de låsta raderna)", "",
           "Tre rader bredvid H, a och b (`docs/mattregister.md`, 2026-11-27 X26, punkt 2, efter granskningen R29-2). "
           "Samma källserier, statistik, gränser, fönster och tecken. Det enda som skiljer är kvartalsvärdet: det "
           "geometriska medlet, exp(medlet av ln), av kvartalets tre månader och av veckosummorna. Med det aritmetiska "
           "medlet ger en speglad prisbana (1/x) inte den speglade förändringen i takt, så riktningen kan avgöra om en "
           "impuls uppstår. Med det geometriska medlet ger den exakt det speglade utslaget. Huvudläsningen är "
           "fortfarande H. Om H-G ska ersätta H är ett beslut för ägaren före den första osedda läsningen.", ""]
    out += _table(r, ["pv1_pris_gpqa_gq", "pv1_pris_arena_gq", "pv1_sdk_gq", "pv1_kontroll_gq", "pv1_sdk_rel_gq"])
    out.append("")
    locked = {"H-G": "H", "a-G": "a", "b-G": "b"}
    for name, rr in r["readings_geo"].items():
        label = READING_NAME[name]
        lines = C.reading_lines(rr, label)
        lines[0] = lines[0].replace(f"**{label}:** {rr['text']}", f"**{label}:** {short(rr)}", 1)
        if rr.get("x_first") is None:
            lines.append("  X har ännu ingen förändring i takt på dagen (serien är för kort), så varje ursprung kan "
                         "inte avgöras.")
        else:
            lines.append(f"  X har förändring i takt från {rr['x_first']}.")
        lines += _decided_lines(rr)
        lines.append("  " + _same_text(rr, r["readings"][locked[name]]))
        if rr.get("seen") is False:
            lines.append(f"  **Osedd:** läsningen vilar på värden som blev kända efter registerposten {X26_REGISTERED}.")
        else:
            lines.append("  " + C.seen_text(True, X26_REGISTERED))
        out += lines
    return out + [""]


# ------------------------------------------------------------------ antenna (register PV1, (h))


def antenna(r: dict) -> dict:
    """PV1's row in `antenner`: the main reading H, the side readings a and b, X's and Y's change in pace, the main
    reading's impulses and whether it is unseen as facts; main_inputs = the catalog series of H."""
    main = r["readings"][MAIN]
    facts = {SHORT_NAME[n]: short(r["readings"][n]) for n in ("a", "b")}
    x, y = r["measures"]["pv1_pris_gpqa_q"], r["measures"]["pv1_sdk_q"]
    facts["GPQA-pris, förändring i takt"] = f"{_f(x.get('change'), 1, True)} ({x.get('period') or '–'})"
    facts["SDK-nedladdningar, förändring i takt"] = f"{_f(y.get('change'), 1, True)} ({y.get('period') or '–'})"
    hh = main["history"]
    facts["Huvudläsningen, impulser upp/ned"] = f"{hh['impulses_up']}/{hh['impulses_down']} av {hh['n_x']} ursprung"
    facts["Huvudläsningen på osedda data"] = "nej" if main.get("seen", True) else "ja"
    geo = r.get("readings_geo") or {}
    if geo:  # register X26, point 2: beside the locked readings, not the row's outcome
        facts["Geometriskt medel H-G / a-G / b-G (X26)"] = " / ".join(short(geo[n]) for n in ("H-G", "a-G", "b-G"))
    inputs = {"x": [PRICE_GPQA], "y": list(SDK), "x_stat": "förändring i takt", "sign": SIGN}
    return C.antenna_row(QUESTION, main["outcome"], short(main), main["t"], facts, r["next_unseen"],
                         r["next_unseen_date"], inputs)
