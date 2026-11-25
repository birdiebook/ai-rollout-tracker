"""DuckDB views over the observation table, and the data-quality checks.

Views:
- observations : the versioned table, plus period_end and ordinal (consecutive integer per frequency)
- obs_latest   : latest vintage per (series, period)
- catalog      : key, freq, lag_days, revised, closed, max_age_days (bound below) for every catalog series

Each check in CHECKS returns the violating rows; empty = pass. tests/test_warehouse.py tests the checks,
tests/test_data_quality.py runs them on the real table when it exists. Pattern from kpif-nowcast.

Freshness (`fresh`, run by `pipeline weekly`). A source that silently stops publishing passes every check
above, so each open series also has a maximum age:

    age   = today - end of the newest period known on `today` (rows with known_from <= today)
    bound = lag_days + one period + 30 days      for D, W, 2W, M, Q (period = 1, 7, 14, 31, 92 days)
    bound = lag_days + 400 days                   for A (annual surveys move by weeks between years)
    stale = age > bound, or no row at all

Age is measured from the period end, not from the latest known_from, so a revision of old periods never
makes a series look fresh: only a new period does. `Spec.max_age_days` overrides the bound (reason in
`note`, e.g. a release calendar that is offset from the period), `Spec.closed` exempts an ended series,
KNOWN_STALE accepts a stale series until a given date (a source outage that is understood), and a series whose
API key is not set (keyed.py) is left out until the key is added.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from ai_tracker import catalog, keyed, observations
from ai_tracker.observations import to_periods
from ai_tracker.sources import plans as _plans

# Series with an accepted gap, and why. Keep this short.
KNOWN_GAPS: dict[str, str] = {
    "lab_rev_anthropic_company_run_rate": "self-reported figures on irregular dates (period = the stated date)",
    "lab_rev_anthropic_claude_code_run_rate": "self-reported figures on irregular dates (period = the stated date)",
    "guid_capex_msft_q_lo": "Microsoft gives a capex number for the next quarter only in some calls; else a direction",
    "guid_capex_msft_q_dir_qoq": "2025Q3 was guided as a number (over $30bn), not as a direction",
}
KNOWN_GAPS.update(_plans.known_gaps())  # D1 plan series are sparse by design (docs/kallor/planer.md)

# Company AI KPIs (track B4) are stated irregularly; the series module lists its gapped series with the reason.
from ai_tracker.series.ai_kpis import KNOWN_GAPS as _AI_KPI_GAPS  # noqa: E402

KNOWN_GAPS.update(_AI_KPI_GAPS)

# GH Archive outages leave weeks without enough sample hours (track B2, docs/kallor/github_ai.md).
from ai_tracker.series.github_ai import KNOWN_GAPS as _GH_AI_GAPS  # noqa: E402

KNOWN_GAPS.update(_GH_AI_GAPS)

# Useful lives of servers (track P2a) are sparse step values: a value only where a filing states it.
from ai_tracker.series.useful_lives import KNOWN_GAPS as _USEFUL_LIFE_GAPS  # noqa: E402

KNOWN_GAPS.update(_USEFUL_LIFE_GAPS)

# F1 revision and surprise indexes need a minimum count per period (register 2026-11-24, F1).
from ai_tracker.series.guidance_revisions import KNOWN_GAPS as _F1_GAPS  # noqa: E402

KNOWN_GAPS.update(_F1_GAPS)

# Bond issuance and the spread at issuance (track KR1) are irregular: a quarter without a tranche has no value.
from ai_tracker.series.credit_issuance import KNOWN_GAPS as _KR1_GAPS  # noqa: E402

KNOWN_GAPS.update(_KR1_GAPS)

# Accepted gaps per period: series -> {period: why}. The series passes no_gaps only if every missing period within
# its span is listed, so a second gap is still reported. Prefer this to a whole-series exemption in KNOWN_GAPS.
# BLS collected no CPI data for October 2025 (lapse in appropriations; track M1, docs/kallor/makro_bea_bls.md).
from ai_tracker.series.bls import KNOWN_GAP_PERIODS as _BLS_GAP_PERIODS  # noqa: E402

KNOWN_GAP_PERIODS: dict[str, dict[str, str]] = {**_BLS_GAP_PERIODS}

# Stale series accepted until a date (ISO), and why: a known outage, never a permanent exemption
# (that is Spec.max_age_days or Spec.closed). Example: {"us_imports_tw_m": ("2026-12-31", "shutdown, ...")}.
KNOWN_STALE: dict[str, tuple[str, str]] = {
    # Selected 2026-11-23 (register, G1 track F6); Epoch's first runs started 2026-11-04, so the first complete
    # month (2026-11) is known from 2026-12-31 (first day of the next month + 30 days).
    "g1_epoch_bench_frontier_spireclimb": ("2027-01-07", "new series: first month known 2026-12-31"),
    "g1_epoch_bench_runs_spireclimb": ("2027-01-07", "new series: first month known 2026-12-31"),
    # Track B5: own first-party price snapshots from 2026-11-23, no backfill; the first complete month (2026-11) is
    # known 2026-12-01 and computed by the first weekly run after that (Monday 2026-12-07).
    # Track KR1: Microsoft's only registered issuance since 2020 was priced 2026-10-29; the quarter 2026Q4 is known
    # 2027-01-01 (the day after the quarter), so the series has no row until then.
    "issuance_msft_q": ("2027-01-15", "new series: first quarter (2026Q4) known 2027-01-01"),
}

PERIOD_DAYS = {"D": 1, "W": 7, "2W": 14, "M": 31, "Q": 92}
MARGIN_DAYS = 30
ANNUAL_MARGIN_DAYS = 400


def max_age_days(spec: catalog.Spec) -> int:
    """Freshness bound in days from the newest period's end (see module docstring)."""
    if spec.max_age_days is not None:
        return spec.max_age_days
    if spec.freq == "A":
        return spec.lag_days + ANNUAL_MARGIN_DAYS
    return spec.lag_days + PERIOD_DAYS[spec.freq] + MARGIN_DAYS

CHECKS = {
    "unique_key": """
        select series, period, known_from, count(*) as n from observations group by all having count(*) > 1""",
    "no_nulls": """
        select * from observations
        where series is null or period is null or known_from is null or value is null or isnan(value)""",
    # a value cannot be known before its period has ended (negative lag_days allows announced values)
    "known_from_after_period_end": """
        select o.series, o.period, o.known_from, o.source from observations o join catalog c on c.key = o.series
        where o.known_from < o.period_end + to_days(least(c.lag_days, 0))""",
    "fetched_known_from_not_after_fetch": """
        select series, period, known_from, fetched_at, source from observations
        where source in ('fetch', 'revision') and known_from > fetched_at""",
    "freq_matches_catalog": """
        select distinct o.series, o.freq, c.freq as catalog_freq from observations o
        join catalog c on c.key = o.series where o.freq <> c.freq""",
    "no_gaps": """
        select series, min(ordinal) as first, max(ordinal) as last, count(*) as n from obs_latest
        group by series having count(*) <> max(ordinal) - min(ordinal) + 1""",
    "series_in_catalog": """
        select distinct series from observations where series not in (select key from catalog)""",
}


def _ordinals(periods: pd.PeriodIndex, freq: str):
    return observations.fortnight_ordinal(periods) if freq == "2W" else periods.asi8


def _with_periods(table: pd.DataFrame) -> pd.DataFrame:
    t = table.copy()
    t["period_end"] = pd.NaT
    t["ordinal"] = pd.Series(dtype="int64")
    for freq, idx in t.groupby("freq").groups.items():
        periods = to_periods(t.loc[idx, "period"], freq)
        t.loc[idx, "period_end"] = periods.end_time.normalize()
        t.loc[idx, "ordinal"] = _ordinals(periods, freq)
    t["period_end"] = pd.to_datetime(t["period_end"])
    t["ordinal"] = t["ordinal"].astype("int64")
    return t


def catalog_frame(specs: list[catalog.Spec] | None = None) -> pd.DataFrame:
    specs = catalog.ALL if specs is None else specs
    return pd.DataFrame([(s.key, s.freq, s.lag_days, s.revised, s.closed, max_age_days(s),
                          "override" if s.max_age_days is not None else "derived") for s in specs],
                        columns=["key", "freq", "lag_days", "revised", "closed", "max_age_days", "bound"])


def connect(table: pd.DataFrame | None = None, specs: list[catalog.Spec] | None = None) -> duckdb.DuckDBPyConnection:
    table = observations.load() if table is None else table
    con = duckdb.connect()
    con.register("observations_df", _with_periods(table))
    con.register("catalog_df", catalog_frame(specs))
    con.execute("create view observations as select * from observations_df")
    con.execute("create view catalog as select * from catalog_df")
    con.execute("""create view obs_latest as
        select * from observations qualify row_number() over (partition by series, period order by known_from desc) = 1""")
    return con


def only_known_gaps(con: duckdb.DuckDBPyConnection, series: str) -> bool:
    """True if every missing period of `series` within its span is listed in KNOWN_GAP_PERIODS."""
    accepted = KNOWN_GAP_PERIODS.get(series)
    if not accepted:
        return False
    got = con.execute("select freq, ordinal from obs_latest where series = ?", [series]).df()
    freq = got["freq"].iloc[0]
    have = set(got["ordinal"].astype("int64"))
    missing = set(range(min(have), max(have) + 1)) - have
    return missing <= {int(o) for o in _ordinals(to_periods(list(accepted), freq), freq)}


def run_checks(con: duckdb.DuckDBPyConnection | None = None) -> dict[str, pd.DataFrame]:
    con = con or connect()
    out = {}
    for name, sql in CHECKS.items():
        df = con.execute(sql).df()
        if name == "no_gaps" and len(df):
            df = df[~df["series"].isin(KNOWN_GAPS)]
            keep = np.array([not only_known_gaps(con, s) for s in df["series"]], dtype=bool)
            df = df[keep].reset_index(drop=True)
        out[name] = df
    return out


FRESH_SQL = """
    with latest as (
        select series, max(period_end) as last_end, arg_max(period, period_end) as last_period,
               max(known_from) as last_known_from
        from observations where known_from <= $today group by series)
    select c.key as series, c.freq, l.last_period, l.last_end, l.last_known_from,
           date_diff('day', l.last_end, $today) as age_days, c.max_age_days, c.bound
    from catalog c left join latest l on l.series = c.key
    where not c.closed and (l.series is null or date_diff('day', l.last_end, $today) > c.max_age_days)
    order by c.key"""


def fresh(con: duckdb.DuckDBPyConnection | None = None, today=None) -> pd.DataFrame:
    """Stale open series on `today` (default: today, UTC date): age, bound and newest period; empty = pass.

    A series with no row known on `today` is stale with age NaN. KNOWN_STALE entries are left out until
    their date has passed.
    """
    con = con or connect()
    today = pd.Timestamp(today if today is not None else pd.Timestamp.now(tz="UTC").date()).normalize()
    df = con.execute(FRESH_SQL, {"today": today.to_pydatetime()}).df()
    accepted = {k for k, (until, _) in KNOWN_STALE.items() if today <= pd.Timestamp(until)}
    accepted |= keyed.unconfigured(df["series"])  # their API key is not set: not fetchable here (keyed.py)
    return df[~df["series"].isin(accepted)].reset_index(drop=True)


def describe_stale(df: pd.DataFrame) -> list[str]:
    """One line per stale series, for logs and the job summary."""
    lines = []
    for r in df.itertuples(index=False):
        if pd.isna(r.last_end):
            lines.append(f"{r.series} ({r.freq}): no data")
        else:
            lines.append(f"{r.series} ({r.freq}): newest period {r.last_period}, ended "
                         f"{pd.Timestamp(r.last_end).date()}, age {int(r.age_days)} d > bound "
                         f"{int(r.max_age_days)} d ({r.bound})")
    return lines


if __name__ == "__main__":
    import sys

    stale = fresh(today=sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"{'fresh':40s} {'ok' if stale.empty else f'{len(stale)} stale series'}")
    for line in describe_stale(stale):
        print("  " + line)
    for name, df in run_checks().items():
        print(f"{name:40s} {'ok' if df.empty else f'{len(df)} violations'}")
        if len(df):
            print(df.head(10).to_string())
