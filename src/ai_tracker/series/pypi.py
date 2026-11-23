"""PyPI weekly downloads of AI packages and two control packages (G3, track B1).

Two series per project, both from views of the same BigQuery table (bigquery-public-data.pypi.file_downloads):
- `g3_pypi_<p>_w`: exact weekly totals from full days, i.e. pypistats.org `with_mirrors` (sources/pypistats.py,
  every response kept under RAW_DIR/pypistats so the history grows past 180 days) and any exact BigQuery days.
  A missing day is filled from the weekday profile (sources/download_counts.py).
- `g3_pypi_<p>_wed`: downloads on the Wednesday of each week, 2016 -> : the sampled BigQuery backfill
  (sources/pypi_bq.py, RAW_DIR/pypi_bq) and from 2026-05-27 the same weekday from pypistats. An exact daily
  history is about 1.7 TB of BigQuery quota; the Wednesday sample is about 180 GB (numpy left out).
On a day both have, BigQuery (the source table) wins.
docs/kallor/utvecklaradoption.md has the overlap check between the two and the BigQuery bytes.
"""

from __future__ import annotations

from datetime import date
from functools import partial

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.sources import download_counts, pypi_bq, pypistats

SOURCE = "PyPI BigQuery (bigquery-public-data.pypi.file_downloads) + pypistats.org"
LICENSE = ("CC BY 4.0: PyPI's BigQuery tables and their data (docs.pypi.org/api/bigquery, "
           "github.com/pypi/warehouse docs/user/api/bigquery.md). Attribution: PyPI / Python Software Foundation")
LAG_DAYS = 2  # Linehaul streams to BigQuery within hours; pypistats updates once a day after UTC midnight
_NOTE = ("Nedladdningar per vecka (måndag–söndag, UTC) inklusive speglar (bandersnatch m.fl.), CI och "
         "beroenden: nedladdningar är inte användare. known_from = söndag + 2 dagar. Historik ur BigQuery, "
         "veckovis påfyllnad ur pypistats with_mirrors (samma tabell).")

# key -> (PyPI project, explicit series start (a Monday) or None, label, note)
PROJECTS = {
    "g3_pypi_openai_w": ("openai", date(2020, 2, 17), "openai (OpenAI:s SDK)",
                         "Första versionen med filer kom 2020-02-18; serien börjar veckan 2020-02-17."),
    "g3_pypi_anthropic_w": ("anthropic", None, "anthropic (Anthropics SDK)", ""),
    "g3_pypi_google_generativeai_w": ("google-generativeai", None, "google-generativeai (Googles äldre Gemini-SDK)",
                                      ""),
    "g3_pypi_google_genai_w": ("google-genai", None, "google-genai (Googles Gemini-SDK)", ""),
    "g3_pypi_langchain_w": ("langchain", None, "langchain", ""),
    "g3_pypi_langchain_core_w": ("langchain-core", None, "langchain-core", ""),
    "g3_pypi_transformers_w": ("transformers", date(2019, 9, 30), "transformers (Hugging Face)",
                               "Namnet transformers hade ett annat paket 2016 (0.1); Hugging Face 2.0.0 kom "
                               "2019-09-26 (en torsdag), så serien börjar veckan 2019-09-30."),
    "g3_pypi_torch_w": ("torch", date(2018, 12, 3), "torch (PyTorch)",
                        "Första PyPI-versionen med filer är 1.0.0 (2018-12-07); serien börjar veckan 2018-12-03."),
    "g3_pypi_llama_index_w": ("llama-index", None, "llama-index", ""),
    "g3_pypi_mcp_w": ("mcp", date(2024, 11, 18), "mcp (Model Context Protocol)",
                      "Första versionen med filer (0.9.1) kom 2024-11-20; enstaka nedladdningar av namnet innan "
                      "räknas inte, serien börjar veckan 2024-11-18."),
    "g3_pypi_requests_w": ("requests", date(2016, 5, 23), "requests (kontrollpaket)",
                           "Kontrollpaket, inte en AI-serie. Tabellen börjar 2016-01-22 och saknar 2016-03-09–"
                           "2016-05-18, så onsdagsserien börjar veckan 2016-05-23."),
    "g3_pypi_numpy_w": ("numpy", None, "numpy (kontrollpaket)",
                        "Kontrollpaket, inte en AI-serie. Ingår inte i BigQuery-historiken (kvoten), bara pypistats."),
}


def _bq(kinds: tuple[str, ...]) -> pd.DataFrame:
    try:
        return pypi_bq.load_daily(kinds=kinds)[0]
    except FileNotFoundError:
        return pd.DataFrame(columns=pypi_bq.PROJECTS, dtype=float)


def _pypistats(project: str, refresh: bool) -> pd.Series:
    """Stored pypistats days (today's response included when `refresh`). A day pypistats has for `requests` but
    not for the project had no downloads; a day it has for neither is a gap (NaN)."""
    if refresh:
        pypistats.fetch(project)  # saved under RAW_DIR; stored() reads every saved response
        pypistats.fetch(pypi_bq.CONTROL)
    ps, control = pypistats.stored(project), pypistats.stored(pypi_bq.CONTROL)
    if ps.empty and control.empty:
        return ps
    idx = ps.index.union(control.index)
    span = pd.date_range(idx.min(), idx.max(), freq="D")
    ps = ps.reindex(span)
    ps[ps.isna() & span.isin(control.index)] = 0.0
    return ps


def daily(project: str, kinds: tuple[str, ...] = ("daily",), refresh: bool = True) -> pd.Series:
    """Daily counts: pypistats, overridden by stored BigQuery days of `kinds` (the source table itself).

    Index = every covered day; NaN = gap."""
    ps = _pypistats(project, refresh)
    bq = _bq(kinds)
    bq = bq[project] if project in bq else pd.Series(dtype=float)
    if bq.empty:
        return ps
    return bq.combine_first(ps).sort_index()  # BigQuery where it has a value, else pypistats


def weekly(project: str, start: date | None = None, today: date | None = None) -> pd.Series:
    """Exact weekly totals (W-SUN) from full days only: pypistats (and any exact BigQuery days)."""
    return download_counts.weekly(daily(project), today or date.today(), LAG_DAYS, start)


def wednesday(project: str, start: date | None = None, today: date | None = None) -> pd.Series:
    """Downloads on the Wednesday (UTC) of each W-SUN week: the sampled BigQuery history 2016 -> plus the same
    weekday from pypistats. Weeks whose Wednesday is a gap, or whose Sunday + lag is after today, are left out."""
    today = pd.Timestamp(today or date.today())
    d = daily(project, kinds=("daily", "wed"))
    d = d[d.index.dayofweek == pypi_bq.SAMPLE_WEEKDAY].dropna()
    first = pd.Timestamp(start) if start is not None else d.index[(d > 0).to_numpy()].min()
    if d.empty or pd.isna(first):
        return pd.Series(dtype=float)
    d = d[d.index >= first]
    s = pd.Series(d.to_numpy(), index=d.index.to_period("W-SUN"), dtype=float)
    return s[s.index.end_time.normalize() + pd.Timedelta(days=LAG_DAYS) <= today]


_QUESTION = "Hur snabbt bygger utvecklare med AI-SDK:er (Python)?"
_WED_NOTE = ("Stickprov: nedladdningar under veckans onsdag (UTC), inte veckosumma. BigQuery-historiken läser bara "
             "onsdagar (kostnaden för exakt daglig historik är cirka 1,7 TB, se docs/kallor/utvecklaradoption.md); "
             "från 2026-05-27 samma veckodag ur pypistats. Helgdagar som infaller en onsdag (t.ex. juldagen) syns.")

SPECS = [
    Spec(key=key, branch="G3", label=f"PyPI-nedladdningar per vecka: {label}", unit="nedladdningar per vecka",
         freq="W", source=SOURCE, fetch=partial(weekly, project, start), lag_days=LAG_DAYS, license=LICENSE,
         revised=True, publish=True, question=_QUESTION,
         note=(extra + " Exakt veckosumma; historik från 2026-05-26 (pypistats 180 dagar), växer vecka för vecka. "
               + _NOTE).strip())
    for key, (project, start, label, extra) in PROJECTS.items()
] + [
    Spec(key=key.removesuffix("_w") + "_wed", branch="G3", label=f"PyPI-nedladdningar en onsdag per vecka: {label}",
         unit="nedladdningar per dag (onsdag)", freq="W", source=SOURCE, fetch=partial(wednesday, project, start),
         lag_days=LAG_DAYS, license=LICENSE, revised=True, publish=True, question=_QUESTION,
         note=(extra + " " + _WED_NOTE + " " + _NOTE).strip())
    for key, (project, start, label, extra) in PROJECTS.items()
]
