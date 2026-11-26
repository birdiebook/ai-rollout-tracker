"""The shared engine of the followed questions (register 2026-11-26 "F0").

A followed question is a module in ai_tracker.followed with

    QUESTION: str                       the question, neutral and both ways (Swedish)
    compute(as_of, table=None) -> dict  everything the report shows, from rows known on `as_of` only
    render(report) -> str               the Markdown report
    antenna(report) -> dict             optional: the question's row in `antenner` (see ANTENNA_KEYS)

and is found by the CLI (followed/__main__.py) without registration. This module holds what the questions share:

- loading as of a day: `prepare`, `asof_rows`; calendar quarters: `quarter`, `minus`, `plus`
- per-series measures from state.measures (level, pace over four quarters in pp or log x100, change in pace against
  two quarters earlier, surprise against B1): `measure`, `measures`, `at`; the same formulas on a bare quarterly
  series for values outside the catalog: `path_measures`
- aggregates over companies with the missing-member rule: ai_tracker.followed.aggregate (re-exported here)
- the symmetric reading rule (register F0, (b)): `read_rule`, `read_measures`, `reading_lines`
- the next filing per company: `next_filings`
- Markdown: `fmt`, `fmt_bn`, `fmt_pct`, `measure_table`

Everything here is a description: no alarm levels, no chosen direction, no p-values.
"""

from __future__ import annotations

import math
from typing import Callable, Mapping

import numpy as np
import pandas as pd

from ai_tracker import observations
from ai_tracker.followed.aggregate import QFREQ, Formula, Term, derive, inputs, missing, sum4  # noqa: F401
from ai_tracker.state import measures as M

# ------------------------------------------------------------------ numbers and quarters


def num(x) -> float | None:
    """A finite float or None (None, NaN, inf and non-numbers give None)."""
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def quarter(x) -> str:
    """The calendar quarter ('2026Q3') of a date, a period string or a Period."""
    if isinstance(x, pd.Period):
        return str(x.asfreq(QFREQ))
    s = str(x)
    if len(s) == 6 and s[4] == "Q":
        return str(pd.Period(s, freq=QFREQ))
    return str(pd.Period(pd.Timestamp(s), freq=QFREQ))


def minus(period: str | None, k: int) -> str | None:
    """The quarter k quarters before `period` (None stays None)."""
    return None if period is None else str(pd.Period(period, freq=QFREQ) - k)


def plus(period: str | None, k: int) -> str | None:
    return minus(period, -k)


# ------------------------------------------------------------------ loading as of a day


def prepare(table: pd.DataFrame | None = None) -> tuple[pd.DataFrame, M.Context]:
    """The observation table (loaded when None) as a copy with known_from as datetime, and its measure context."""
    table = observations.load() if table is None else table
    table = table.copy()
    table["known_from"] = pd.to_datetime(table["known_from"])
    return table, M.Context(table=table)


def asof_rows(table: pd.DataFrame, key: str, when) -> pd.DataFrame:
    """period, value, known_from of the latest vintage per period known on `when`."""
    t = table[(table["series"] == key) & (table["known_from"] <= pd.Timestamp(when))]
    if t.empty:
        return pd.DataFrame(columns=["period", "value", "known_from"])
    return (t.sort_values("known_from").groupby("period")[["value", "known_from"]].last().reset_index()
            .sort_values("period", ignore_index=True))


# ------------------------------------------------------------------ measures


def measure(key: str, when, ctx: M.Context) -> dict:
    """Level, pace, change in pace and surprise of one series as of `when`, with its history (path).

    Keys: series, available, period, known_from, level, pace, change, surprise, surprise_basis, pace_unit, unit,
    method, path ({period: {level, pace, change}}). available=False when the series is unknown or has no rows."""
    if key not in ctx.specs or ctx.rows(key).empty:
        return {"series": key, "available": False}
    out, path = M.measure_path(key, when, ctx)
    res = {"series": key, "available": path is not None, "period": out.get("latest_period"),
           "known_from": out.get("known_from"), "level": num(out.get("level")), "pace": num(out.get("pace")),
           "change": num(out.get("change_in_pace")), "surprise": num(out.get("surprise")),
           "surprise_basis": out.get("surprise_basis", ""), "pace_unit": out.get("pace_unit", ""),
           "unit": ctx.specs[key].unit, "method": out.get("method")}
    res["path"] = {} if path is None else {p: {c: num(v) for c, v in r.items()} for p, r in path.iterrows()}
    return res


def measures(keys, when, ctx: M.Context) -> dict[str, dict]:
    return {k: measure(k, when, ctx) for k in keys}


def at(m: dict, period: str | None, col: str) -> float | None:
    """A column (level, pace, change) of a measure's path at `period`; None when absent."""
    if not m.get("available") or period is None:
        return None
    return (m.get("path") or {}).get(period, {}).get(col)


def series_of(m: dict, col: str) -> dict[str, float | None]:
    """{period: value} of one column of a measure's path (the input of read_rule)."""
    if not m.get("available"):
        return {}
    return {p: r.get(col) for p, r in (m.get("path") or {}).items()}


PACE_LAG, CHANGE_LAG = 4, 2  # quarters (register section 1: pace over a year, change against two quarters earlier)


def path_measures(values: Mapping[str, float] | pd.Series, method: str = "log") -> pd.DataFrame:
    """The registered quarterly measures of a bare series {quarter: value}, for values outside the catalog.

    method "log": y = 100 ln(x) (x > 0); "share": y = x in percentage points. pace = y - y(t-4), change = pace -
    pace(t-2), surprise = y - B1 with B1 = y(t-1) + (y(t-1) - y(t-5)) / 4 (drift, as state.measures.surprise).
    Quarters are made regular (gaps are NaN). Columns level, y, pace, change, surprise; index = quarter strings."""
    s = pd.Series(values, dtype=float)
    if s.empty:
        return pd.DataFrame(columns=["level", "y", "pace", "change", "surprise"])
    s.index = pd.PeriodIndex([pd.Period(str(p), freq=QFREQ) for p in s.index])
    s = s.sort_index()
    s = s.reindex(pd.period_range(s.index[0], s.index[-1], freq=QFREQ))
    if method == "log":
        y = 100.0 * np.log(s.where(s > 0))
    elif method == "share":
        y = s
    else:
        raise ValueError(f"unknown method {method}")
    pace = y - y.shift(PACE_LAG)
    change = pace - pace.shift(CHANGE_LAG)
    b1 = y.shift(1) + (y.shift(1) - y.shift(5)) / 4.0
    out = pd.DataFrame({"level": s, "y": y, "pace": pace, "change": change, "surprise": y - b1})
    out.index = out.index.astype(str)
    return out


# ------------------------------------------------------------------ the symmetric reading rule (register F0, (b))

FOR, AGAINST, NEITHER, UNDECIDED = "talar_for", "talar_emot", "inget", "kan_inte_avgoras"
OUTCOMES = (FOR, AGAINST, NEITHER, UNDECIDED)
OUTCOME_TEXT = {FOR: "talar för mekanismen", AGAINST: "talar emot", NEITHER: "inget av mönstren",
                UNDECIDED: "kan inte avgöras"}


def _val(d: Mapping[str, float | None], q: str) -> float | None:
    return num(d.get(q)) if q in d else None


def origin_outcome(q: str, x: Mapping[str, float | None], y: Mapping[str, float | None], t: str | None, *,
                   g: float, h: float, k: int, sign: int) -> dict:
    """The outcome of one origin quarter q (register F0, (b), points 1-3)."""
    xv = _val(x, q)
    row = {"origin": q, "x": xv, "direction": 0, "expected": 0, "outcome": UNDECIDED, "decided_at": None,
           "y": None, "reason": ""}
    if xv is None:
        row["reason"] = f"X saknas vid {q}"
        return row
    if abs(xv) < g:
        row.update(outcome=NEITHER, reason="ingen impuls")
        return row
    d = 1 if xv >= g else -1
    e = sign * d
    row.update(direction=d, expected=e)
    for j in range(1, k + 1):
        qj = plus(q, j)
        yv = _val(y, qj)
        if yv is None:
            open_ = t is None or pd.Period(qj, freq=QFREQ) > pd.Period(t, freq=QFREQ)
            row["reason"] = f"fönstret öppet till {plus(q, k)}" if open_ else f"Y saknas vid {qj}"
            return row
        if e * yv >= h and e * yv > 0:
            row.update(outcome=FOR, decided_at=qj, y=yv)
            return row
        if e * yv <= -h and e * yv < 0:
            row.update(outcome=AGAINST, decided_at=qj, y=yv)
            return row
    row.update(outcome=NEITHER, reason=f"Y nådde inte gränsen i {plus(q, 1)}–{plus(q, k)}")
    return row


def read_rule(x: Mapping[str, float | None], y: Mapping[str, float | None], *, g: float, k: int, h: float = 0.0,
              sign: int = 1, t: str | None = None) -> dict:
    """The symmetric reading rule (register 2026-11-26 "F0", (b)).

    x: {quarter: X statistic} (pace or change in pace of the leading quantity), y: {quarter: change in pace of the
    following quantity}, both as of the reading day (e.g. series_of(measure(...), "pace")). g > 0: the impulse limit
    in X's unit; h >= 0: the limit for Y; k >= 1: the window in quarters; sign: +1 when Y is expected to move the same
    way as X, -1 when the opposite way. t: Y's latest quarter on the day (default: the latest key of y).

    Returns {"outcome", "text", "origin", "t", "origins" (the reading's origins t-k..t-1), "history", "params"}.
    history counts every origin before t with X known: n_x, n_missing_x, impulses_up, impulses_down,
    by_direction {"up"|"down": {outcome: n}}, no_impulse, n_tested (outcome other than kan_inte_avgoras),
    first, last; and as a description beside F0's count (register X25, point 4): n_y_window (origins with Y known in
    all k quarters of the window) and n_impulse_read (impulses whose outcome was read against Y)."""
    if not g > 0 or k < 1 or h < 0 or sign not in (1, -1):
        raise ValueError("need g > 0, k >= 1, h >= 0 and sign = +1 or -1")
    params = {"g": g, "h": h, "k": k, "sign": sign}
    if t is None:
        t = max(y, key=lambda p: pd.Period(p, freq=QFREQ)) if y else None
    if t is None:
        return {"outcome": UNDECIDED, "text": OUTCOME_TEXT[UNDECIDED], "origin": None, "t": None, "origins": [],
                "reason": "Y saknas", "history": _history([], ), "params": params}
    tp = pd.Period(t, freq=QFREQ)
    kw = {"g": g, "h": h, "k": k, "sign": sign}
    current = [origin_outcome(minus(t, j), x, y, t, **kw) for j in range(k, 0, -1)]  # t-k .. t-1
    hist_q = sorted({p for p in x if pd.Period(p, freq=QFREQ) < tp}, key=lambda p: pd.Period(p, freq=QFREQ))
    hist = [origin_outcome(q, x, y, t, **kw) for q in hist_q]
    for r in hist:  # Y known in the whole window (X25, point 4: a description beside F0's count)
        r["y_window"] = all(_val(y, plus(r["origin"], j)) is not None for j in range(1, k + 1))
    impulses = [r for r in current if r["direction"] != 0]
    if impulses:
        pick = impulses[-1]
        outcome, origin, reason = pick["outcome"], pick["origin"], pick["reason"]
    elif all(r["x"] is not None for r in current):
        outcome, origin, reason = NEITHER, None, "ingen impuls i fönstret"
    else:
        outcome, origin = UNDECIDED, None
        reason = "; ".join(r["reason"] for r in current if r["x"] is None)
    return {"outcome": outcome, "text": OUTCOME_TEXT[outcome], "origin": origin, "t": t, "origins": current,
            "reason": reason, "history": _history(hist), "params": params}


def _history(rows: list[dict]) -> dict:
    known = [r for r in rows if r["x"] is not None]
    by = {"up": dict.fromkeys(OUTCOMES, 0), "down": dict.fromkeys(OUTCOMES, 0)}
    for r in known:
        if r["direction"]:
            by["up" if r["direction"] > 0 else "down"][r["outcome"]] += 1
    return {"n_x": len(known), "n_missing_x": len(rows) - len(known),
            "impulses_up": sum(r["direction"] > 0 for r in known),
            "impulses_down": sum(r["direction"] < 0 for r in known),
            "no_impulse": sum(r["direction"] == 0 for r in known), "by_direction": by,
            "n_tested": sum(r["outcome"] != UNDECIDED for r in known),
            "n_y_window": sum(bool(r.get("y_window")) for r in known),
            "n_impulse_read": sum(r["direction"] != 0 and r["outcome"] != UNDECIDED for r in known),
            "first": known[0]["origin"] if known else None, "last": known[-1]["origin"] if known else None}


def read_measures(mx: dict, my: dict, *, x_stat: str = "pace", g: float, k: int, h: float = 0.0,
                  sign: int = 1) -> dict:
    """read_rule on two measure() results: X's `x_stat` ("pace" or "change") against Y's change in pace, with t = Y's
    latest quarter on the day. Adds "x_series", "y_series" and "x_stat"."""
    if x_stat not in ("pace", "change"):
        raise ValueError(x_stat)
    t = my.get("period") if my.get("available") else None
    r = read_rule(series_of(mx, x_stat), series_of(my, "change"), g=g, k=k, h=h, sign=sign, t=t)
    r.update(x_series=mx.get("series"), y_series=my.get("series"), x_stat=x_stat)
    if t is None:
        r["reason"] = f"{my.get('series')}: inget kvartal känt på dagen"
    return r


def reading_lines(r: dict, label: str, nd: int = 1) -> list[str]:
    """Markdown lines for one read_rule result: the outcome with its numbers, then how often the rule could be tried."""
    p = r["params"]
    o = next((x for x in r["origins"] if x["origin"] == r["origin"]), None)
    what = f"X = {r.get('x_series', 'X')} ({'takt' if r.get('x_stat', 'pace') == 'pace' else 'förändring i takt'}), " \
           f"Y = {r.get('y_series', 'Y')} (förändring i takt)"
    head = f"- **{label}:** {r['text']}. t = {r['t'] or '–'}"
    if o is not None:
        head += (f"; ursprung {o['origin']}, X {fmt(o['x'], nd, True)} (gräns ±{fmt(p['g'], nd)}), "
                 f"{'uppgång' if o['direction'] > 0 else 'nedgång'}")
        if o["decided_at"]:
            head += f", Y {fmt(o['y'], nd, True)} vid {o['decided_at']} (gräns ±{fmt(p['h'], nd)})"
    if r.get("reason") and r["outcome"] in (UNDECIDED, NEITHER):
        head += f" ({r['reason']})"
    lines = [head + f". {what}; fönster {p['k']} kvartal, tecken {'+' if p['sign'] > 0 else '−'}."]
    hh = r["history"]
    if hh["n_x"]:
        up, dn = hh["by_direction"]["up"], hh["by_direction"]["down"]
        lines.append(f"  Regeln kunde prövas i {hh['n_tested']} av {hh['n_x']} ursprung med X ({hh['first']}–"
                     f"{hh['last']}). Impulser uppåt {hh['impulses_up']} (för {up[FOR]}, emot {up[AGAINST]}, inget "
                     f"{up[NEITHER]}, kan inte avgöras {up[UNDECIDED]}), nedåt {hh['impulses_down']} (för {dn[FOR]}, "
                     f"emot {dn[AGAINST]}, inget {dn[NEITHER]}, kan inte avgöras {dn[UNDECIDED]}), utan impuls "
                     f"{hh['no_impulse']}.")
        lines.append("  " + tried_note(hh))
    else:
        lines.append("  Regeln kunde inte prövas: X saknas i hela historiken.")
    return lines


def one_sided(h: dict) -> str | None:
    """'nedåt' or 'uppåt' when X has had impulses only the other way (that direction is untested), else None."""
    if h["impulses_up"] and not h["impulses_down"]:
        return "nedåt"
    if h["impulses_down"] and not h["impulses_up"]:
        return "uppåt"
    return None


def tried_note(h: dict) -> str:
    """The description beside F0's count (register X25, point 4): Y known in the whole window, impulses read against
    Y, and the untested direction when X has moved only one way."""
    s = (f"Y var känt i hela fönstret i {h.get('n_y_window', 0)} av {h['n_x']} ursprung, och "
         f"{h.get('n_impulse_read', 0)} av {h['impulses_up'] + h['impulses_down']} impulser kunde läsas mot Y.")
    side = one_sided(h)
    if side:
        s += f" Riktningen {side} har inte prövats: X har inte haft någon impuls {side}."
    elif not (h["impulses_up"] or h["impulses_down"]):
        s += " Ingen riktning har prövats: X har inte haft någon impuls."
    return s


# ------------------------------------------------------------------ seen data per reading (register X25, point 1)


def _q_range(a: str | None, b: str | None) -> list[str]:
    if a is None or b is None or pd.Period(a, freq=QFREQ) > pd.Period(b, freq=QFREQ):
        return []
    return [str(q) for q in pd.period_range(a, b, freq=QFREQ)]


def resting_on(r: dict) -> tuple[list[str], list[str]]:
    """The quarters of X and of Y that a read_rule result's outcome rests on (register X25, point 1): for talar för
    and talar emot, X at the picked origin o and Y in o + 1 ... the deciding quarter; otherwise X at t - k ... t - 1
    and Y at t - k + 1 ... t."""
    t, k = r.get("t"), r["params"]["k"]
    o = next((x for x in r.get("origins", []) if x["origin"] == r.get("origin")), None)
    if o is not None and r["outcome"] in (FOR, AGAINST) and o.get("decided_at"):
        return [o["origin"]], _q_range(plus(o["origin"], 1), o["decided_at"])
    if t is None:
        return [], []
    return _q_range(minus(t, k), minus(t, 1)), _q_range(minus(t, k - 1), t)


def _same(a, b) -> bool:
    a, b = num(a), num(b)
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def same_inputs(r: dict, x_now: Mapping, y_now: Mapping, x_reg: Mapping, y_reg: Mapping) -> bool:
    """True when every value the reading's outcome rests on (resting_on) is the same on the register day as on the
    reading day: the reading is then on seen data. A value missing on both days counts as the same."""
    xq, yq = resting_on(r)
    return (all(_same(x_now.get(q), x_reg.get(q)) for q in xq)
            and all(_same(y_now.get(q), y_reg.get(q)) for q in yq))


SEEN_NOTE = "inget utfall på osedda data"


def seen_text(seen: bool | None, registered: str) -> str:
    """The per-reading note: on seen data (every value it rests on was known on the register day) or not."""
    if seen is None or seen:
        return (f"Läsningen vilar bara på värden som var kända före registerposten {registered}, och den är därför "
                f"{SEEN_NOTE}.")
    return f"Läsningen vilar på värden som blev kända efter registerposten {registered}: ett utfall på osedda data."


# ------------------------------------------------------------------ next filings

MAX_LAG = 200  # days from quarter end: a longer first appearance is a comparative in a later filing


def next_filings(table: pd.DataFrame, when, filers: Mapping[str, str], n: int = 8, max_lag: int = MAX_LAG) -> list[dict]:
    """Next filing per company: the next calendar quarter's end + the median lag of its last `n` first filings.

    filers: {company: a quarterly series the company's periodic filing carries}. Sorted by the estimated day."""
    when = pd.Timestamp(when)
    out = []
    for c, key in filers.items():
        t = table[(table["series"] == key) & (table["known_from"] <= when)]
        if t.empty:
            continue
        first = t.groupby("period")["known_from"].min().sort_index()
        first.index = pd.PeriodIndex(first.index, freq=QFREQ)
        lags_all = [(kf - p.end_time.normalize()).days for p, kf in first.items()]
        # a period first seen as a comparative in a later filing (lag > max_lag) is not its own filing
        own = [(p, kf, lag) for (p, kf), lag in zip(first.items(), lags_all) if lag <= max_lag]
        if not own:
            continue
        last = own[-n:]
        lags = [lag for _, _, lag in last]
        lag = int(np.median(lags))
        nxt = first.index[-1] + 1
        due = nxt.end_time.normalize() + pd.Timedelta(days=lag)
        while due <= when - pd.Timedelta(days=30):  # more than a month overdue: the next one after it
            nxt += 1
            due = nxt.end_time.normalize() + pd.Timedelta(days=lag)
        row = {"company": c, "series": key, "last_period": str(first.index[-1]),
               "last_filed": str(first.iloc[-1].date()), "next_period": str(nxt), "estimated": str(due.date()),
               "lag_days_median": lag, "lag_days_range": [int(min(lags)), int(max(lags))], "n": len(last),
               "overdue": bool(due <= when), "then_period": None, "then_estimated": None}
        if row["overdue"]:  # the filing after the one that is due now
            row["then_period"] = str(nxt + 1)
            row["then_estimated"] = str(((nxt + 1).end_time.normalize() + pd.Timedelta(days=lag)).date())
        out.append(row)
    return sorted(out, key=lambda r: r["estimated"])


# ------------------------------------------------------------------ Markdown


def fmt(x, nd: int = 1, sign: bool = False) -> str:
    """Swedish number: space as thousands separator, decimal comma, '–' for missing; sign=True adds +/-."""
    x = num(x)
    if x is None:
        return "–"
    s = f"{x:+,.{nd}f}" if sign else f"{x:,.{nd}f}"
    return s.replace(",", " ").replace(".", ",")


def fmt_bn(x) -> str:
    """MUSD as 'mdr' with one decimal."""
    x = num(x)
    return "–" if x is None else fmt(x / 1000, 1) + " mdr"


def fmt_pct(x) -> str:
    return "–" if num(x) is None else fmt(x, 1) + " %"


TABLE_HEAD = ["| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |",
              "|---|---|---|---|---|---|---|---|"]


def measure_table(ms: Mapping[str, dict], keys, level_fmt: Callable, who: Callable[[str], str]) -> list[str]:
    """A Markdown table of measures: one row per series key with level, pace, change in pace, surprise (B1), the
    latest quarter, its known_from and the series key; a series without data gets dashes."""
    lines = list(TABLE_HEAD)
    for k in keys:
        m = ms[k]
        if not m.get("available"):
            lines.append(f"| {who(k)} | – | – | – | – | – | – | `{k}` |")
            continue
        lines.append(f"| {who(k)} | {level_fmt(m['level'])} | {fmt(m['pace'], 1, True)} | {fmt(m['change'], 1, True)} "
                     f"| {fmt(m['surprise'], 1, True)} | {m['period']} | {m['known_from']} | `{k}` |")
    return lines


# ------------------------------------------------------------------ antenna rows

ANTENNA_KEYS = ("question", "outcome", "reading", "t", "facts", "next_unseen", "next_unseen_date", "main_inputs")


def antenna_row(question: str, outcome: str, reading: str, t: str | None, facts: Mapping[str, str],
                next_unseen: str, next_unseen_date: str | None = None, main_inputs: Mapping | None = None) -> dict:
    """The row a question's antenna(report) returns: the question, its main reading (outcome code and text, quarter
    t), facts {label: text} compared month to month, the next unseen reading (text and estimated day) and the main
    reading's inputs (register X25, point 3): {"x": catalog series X sums, "y": the same for Y, "x_stat", "sign"}, or
    None. antenner says when two questions' main readings rest on the same series."""
    mi = None
    if main_inputs is not None:
        mi = {"x": sorted(set(main_inputs["x"])), "y": sorted(set(main_inputs["y"])),
              "x_stat": main_inputs.get("x_stat"), "sign": main_inputs.get("sign")}
    return {"question": question, "outcome": outcome, "reading": reading, "t": t,
            "facts": {str(k): str(v) for k, v in facts.items()}, "next_unseen": next_unseen,
            "next_unseen_date": next_unseen_date, "main_inputs": mi}
