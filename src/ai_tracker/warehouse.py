"""DuckDB views over the observation table, and the data-quality checks.

Views:
- observations : the versioned table, plus period_end and ordinal (consecutive integer per frequency)
- obs_latest   : latest vintage per (series, period)
- catalog      : key, freq, lag_days, revised for every catalog series

Each check in CHECKS returns the violating rows; empty = pass. tests/test_warehouse.py tests the checks,
tests/test_data_quality.py runs them on the real table when it exists. Pattern from kpif-nowcast.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from ai_tracker import catalog, observations
from ai_tracker.observations import to_periods

# Series with an accepted gap, and why. Keep this short.
KNOWN_GAPS: dict[str, str] = {}

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


def _with_periods(table: pd.DataFrame) -> pd.DataFrame:
    t = table.copy()
    t["period_end"] = pd.NaT
    t["ordinal"] = pd.Series(dtype="int64")
    for freq, idx in t.groupby("freq").groups.items():
        periods = to_periods(t.loc[idx, "period"], freq)
        t.loc[idx, "period_end"] = periods.end_time.normalize()
        t.loc[idx, "ordinal"] = observations.fortnight_ordinal(periods) if freq == "2W" else periods.asi8
    t["period_end"] = pd.to_datetime(t["period_end"])
    t["ordinal"] = t["ordinal"].astype("int64")
    return t


def catalog_frame(specs: list[catalog.Spec] | None = None) -> pd.DataFrame:
    specs = catalog.ALL if specs is None else specs
    return pd.DataFrame([(s.key, s.freq, s.lag_days, s.revised) for s in specs],
                        columns=["key", "freq", "lag_days", "revised"])


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


def run_checks(con: duckdb.DuckDBPyConnection | None = None) -> dict[str, pd.DataFrame]:
    con = con or connect()
    out = {}
    for name, sql in CHECKS.items():
        df = con.execute(sql).df()
        if name == "no_gaps" and len(df):
            df = df[~df["series"].isin(KNOWN_GAPS)]
        out[name] = df
    return out


if __name__ == "__main__":
    for name, df in run_checks().items():
        print(f"{name:40s} {'ok' if df.empty else f'{len(df)} violations'}")
        if len(df):
            print(df.head(10).to_string())
