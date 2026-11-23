"""PyPI weekly downloads of AI packages and two control packages (G3, track B1).

Daily counts come from two views of the same BigQuery table (bigquery-public-data.pypi.file_downloads):
- history: our own BigQuery backfill (sources/pypi_bq.py, stored under RAW_DIR/pypi_bq), where it exists;
- weekly refresh: pypistats.org `with_mirrors` (sources/pypistats.py, every response kept under
  RAW_DIR/pypistats), for the days after the last BigQuery day.
A day missing from the source is a gap (filled from the weekday profile, sources/download_counts.py).
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
    "g3_pypi_openai_w": ("openai", None, "openai (OpenAI:s SDK)", ""),
    "g3_pypi_anthropic_w": ("anthropic", None, "anthropic (Anthropics SDK)", ""),
    "g3_pypi_google_generativeai_w": ("google-generativeai", None, "google-generativeai (Googles äldre Gemini-SDK)",
                                      ""),
    "g3_pypi_google_genai_w": ("google-genai", None, "google-genai (Googles Gemini-SDK)", ""),
    "g3_pypi_langchain_w": ("langchain", None, "langchain", ""),
    "g3_pypi_langchain_core_w": ("langchain-core", None, "langchain-core", ""),
    "g3_pypi_transformers_w": ("transformers", date(2019, 9, 23), "transformers (Hugging Face)",
                               "Namnet transformers hade ett annat paket 2016 (0.1); Hugging Face 2.0.0 kom "
                               "2019-09-26, så serien börjar veckan 2019-09-23."),
    "g3_pypi_torch_w": ("torch", date(2018, 12, 3), "torch (PyTorch)",
                        "Första PyPI-versionen med filer är 1.0.0 (2018-12-07); serien börjar veckan 2018-12-03."),
    "g3_pypi_llama_index_w": ("llama-index", None, "llama-index", ""),
    "g3_pypi_mcp_w": ("mcp", None, "mcp (Model Context Protocol)", ""),
    "g3_pypi_requests_w": ("requests", None, "requests (kontrollpaket)", "Kontrollpaket, inte en AI-serie."),
    "g3_pypi_numpy_w": ("numpy", None, "numpy (kontrollpaket)", "Kontrollpaket, inte en AI-serie."),
}


def daily(project: str, refresh: bool = True) -> pd.Series:
    """Combined daily counts: BigQuery days first, then pypistats days after the last BigQuery day.

    Index = every covered day; NaN = gap (no `requests` row in BigQuery, or a day pypistats does not have)."""
    if refresh:
        pypistats.fetch(project)  # saves today's response; parsing below reads every stored response
        if project != pypi_bq.CONTROL:
            pypistats.fetch(pypi_bq.CONTROL)
    try:
        wide, covered = pypi_bq.load_daily()
        bq = wide[project] if project in wide else pd.Series(float("nan"), index=covered)
    except FileNotFoundError:
        bq = pd.Series(dtype=float)
    ps = pypistats.stored(project)
    control = pypistats.stored(pypi_bq.CONTROL)
    if not ps.empty:
        span = pd.date_range(min(ps.index.min(), control.index.min() if len(control) else ps.index.min()),
                             ps.index.max(), freq="D")
        # a day pypistats has for `requests` but not for the project had no downloads; a day it has for neither
        # is a gap
        ps = ps.reindex(span)
        ps[ps.isna() & span.isin(control.index)] = 0.0
    if bq.empty:
        return ps
    after = ps[ps.index > bq.index.max()]
    return pd.concat([bq, after]).sort_index()


def weekly(project: str, start: date | None = None, today: date | None = None) -> pd.Series:
    return download_counts.weekly(daily(project), today or date.today(), LAG_DAYS, start)


SPECS = [
    Spec(key=key, branch="G3", label=f"PyPI-nedladdningar per vecka: {label}", unit="nedladdningar per vecka",
         freq="W", source=SOURCE, fetch=partial(weekly, project, start), lag_days=LAG_DAYS, license=LICENSE,
         revised=True, publish=True, question="Hur snabbt bygger utvecklare med AI-SDK:er (Python)?",
         note=(extra + " " + _NOTE).strip())
    for key, (project, start, label, extra) in PROJECTS.items()
]
