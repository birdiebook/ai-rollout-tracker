"""Versioned observations: (series, freq, period, value, known_from, source, fetched_at).

A backtest or a monthly snapshot must only see what was known on its date. `as_of(series, date)`
returns exactly that. Pattern from kpif-nowcast, generalised to mixed frequencies (D/W/M/Q/A) and to
release-dated sources.

How known_from is set:
- Release-dated rows (fetch returns a DataFrame with known_from, e.g. SEC filings): the source's own
  date. Every filing is its own vintage, so revisions are real vintages from day one. source="release".
- Lag-based, first load (backfill): period end + publication lag (publication.py). Values are today's
  vintage, so revisions leak into the backfill. source="backfill".
- Lag-based, later fetches: a new period gets min(period end + lag, fetch date); a changed value
  (revision) gets known_from = fetch date. source="fetch" / "revision".

Storage: data/observations.parquet (not committed, rebuilt by `python -m ai_tracker.observations`).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import catalog, publication

PATH = Path(__file__).resolve().parents[2] / "data" / "observations.parquet"
COLUMNS = ["series", "freq", "period", "value", "known_from", "source", "fetched_at"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="datetime64[ns]" if c in ("known_from", "fetched_at") else
                                      float if c == "value" else object) for c in COLUMNS})


def load(path: Path | None = None) -> pd.DataFrame:
    path = path or PATH
    if not path.exists():
        return _empty()
    df = pd.read_parquet(path)
    for c in ("known_from", "fetched_at"):
        df[c] = pd.to_datetime(df[c])
    return df


def save(df: pd.DataFrame, path: Path | None = None) -> None:
    path = path or PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def to_periods(index, freq: str) -> pd.PeriodIndex:
    return pd.PeriodIndex(index, freq=catalog.FREQS[freq])


def new_rows(spec: catalog.Spec, values: pd.Series | pd.DataFrame, table: pd.DataFrame,
             fetched_at: date | None = None) -> pd.DataFrame:
    """Rows to append for one fetched vintage of `spec` (pure: does not read or write files)."""
    fetched = pd.Timestamp(fetched_at or date.today())
    existing = table[table["series"] == spec.key]
    latest = existing.sort_values("known_from").groupby("period")["value"].last()
    rows = []

    if isinstance(values, pd.DataFrame):  # release-dated: each row is a vintage with its own date
        df = values.dropna(subset=["value"]).copy()
        df["period"] = [str(p) for p in to_periods(df["period"], spec.freq)]
        df["known_from"] = pd.to_datetime(df["known_from"])
        seen = set(zip(existing["period"], pd.to_datetime(existing["known_from"])))
        for p, v, kf in df.sort_values("known_from")[["period", "value", "known_from"]].itertuples(index=False):
            if (p, kf) not in seen:
                rows.append((spec.key, spec.freq, p, float(v), kf, "release", fetched))
                seen.add((p, kf))
        return pd.DataFrame(rows, columns=COLUMNS)

    values = values.dropna().sort_index()
    periods = to_periods(values.index, spec.freq)
    default_kf = publication.known_from(spec.key, periods, spec.lag_days)
    is_backfill = existing.empty
    for p, v, kf in zip(periods, values.to_numpy(), default_kf):
        key = str(p)
        if key not in latest.index:
            rows.append((spec.key, spec.freq, key, float(v), kf if is_backfill else min(kf, fetched),
                         "backfill" if is_backfill else "fetch", fetched))
        elif not np.isclose(latest[key], v, rtol=0, atol=1e-9):
            rows.append((spec.key, spec.freq, key, float(v), fetched, "revision", fetched))
    return pd.DataFrame(rows, columns=COLUMNS)


def upsert(spec: catalog.Spec, values: pd.Series | pd.DataFrame, fetched_at: date | None = None,
           path: Path | None = None) -> int:
    """Append a fetched vintage to the stored table. Returns rows added."""
    table = load(path)
    new = new_rows(spec, values, table, fetched_at)
    if len(new):
        save(new if table.empty else pd.concat([table, new], ignore_index=True), path)
    return len(new)


def as_of(series: str, when: pd.Timestamp | str, table: pd.DataFrame | None = None) -> pd.Series:
    """Values of `series` as known on `when` (latest vintage with known_from <= when), on a PeriodIndex."""
    table = load() if table is None else table
    t = table[(table["series"] == series) & (table["known_from"] <= pd.Timestamp(when))]
    if t.empty:
        return pd.Series(dtype=float, name=series)
    s = t.sort_values("known_from").groupby("period")["value"].last()
    s.index = to_periods(s.index, t["freq"].iloc[0])
    return s.sort_index().rename(series)


def refresh(keys: list[str] | None = None) -> dict[str, str]:
    """Fetch every catalog series (or `keys`). One failing source doesn't stop the rest."""
    status = {}
    for spec in catalog.ALL:
        if keys and spec.key not in keys:
            continue
        try:
            n = upsert(spec, spec.fetch())
            status[spec.key] = f"ok +{n}"
        except Exception as exc:  # noqa: BLE001 - report and continue
            status[spec.key] = f"FAILED: {type(exc).__name__}: {str(exc)[:120]}"
        print(f"{spec.key:32s} {status[spec.key]}")
    return status


if __name__ == "__main__":
    import sys

    refresh(sys.argv[1:] or None)
