"""SCB statistical database, API v2: AI use in enterprises (NV0116M), CSV output.

https://statistikdatabasen.scb.se/api/v2/tables/<id>/data?lang=sv&outputFormat=csv&valueCodes[...]=...
- TAB6405: "Användning av AI-tekniker efter typ av teknik. Andel företag." 2021-2025 (2021 = '..' for
  "minst en AI-teknik"). Total = SNI 10-63, 68-75, 77-82, 95.1 (SNI 75 from 2023).
- TAB6814: same for 2026-, new reporting groups and NACE Rev. 2.1 coverage (all surveyed industries,
  including A, B, K ...; SNI 68 imputed for 10+).
Table metadata has `updated` and notes (e.g. "Korrigering 2026-05-05 ..."); there is no version history.
"""

from __future__ import annotations

import io

import pandas as pd

from ai_tracker import http

BASE = "https://statistikdatabasen.scb.se/api/v2/tables/"
SOURCE = "scb"


def parse_csv(text: str) -> pd.DataFrame:
    """Wide SCB CSV ("<ContentsCode> <year>" columns) -> long: stub columns, contents, year, value."""
    df = pd.read_csv(io.StringIO(text), dtype=str)
    stubs = [c for c in df.columns if " " not in c]
    long = df.melt(id_vars=stubs, var_name="col", value_name="raw")
    long[["contents", "year"]] = long["col"].str.split(" ", n=1, expand=True)
    long["value"] = pd.to_numeric(long["raw"].str.strip().replace({"..": None, ".": None, "-": None}),
                                  errors="coerce")
    return long.drop(columns=["col", "raw"])


def fetch_table(table: str, codes: dict[str, str]) -> pd.DataFrame:
    params = {"lang": "sv", "outputFormat": "csv"} | {f"valueCodes[{k}]": v for k, v in codes.items()}
    return parse_csv(http.get(BASE + table + "/data", SOURCE, params=params).text)


def metadata(table: str) -> dict:
    return http.get(BASE + table + "/metadata", SOURCE, params={"lang": "sv"}).json()


def share(long: pd.DataFrame, filters: dict[str, str], contents: str) -> pd.Series:
    """Annual series (percent) for one stub combination and one ContentsCode."""
    m = long["contents"] == contents
    for k, v in filters.items():
        m &= long[k] == v
    s = long[m].dropna(subset=["value"]).sort_values("year")
    if s["year"].duplicated().any():
        raise ValueError("SCB: duplicate years")
    return pd.Series(s["value"].to_numpy(dtype=float), index=pd.PeriodIndex(s["year"], freq="Y-DEC"))
