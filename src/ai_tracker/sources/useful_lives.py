"""Useful lives of servers and network equipment (track P2a): a curated CSV of agent-extracted statements.

Companies state, in the property-and-equipment policy of their 10-K (sometimes a 10-Q), the estimated useful life of
the asset class that holds servers, and announce a change in that estimate in a 10-K, 10-Q or results 8-K. The agent
read every candidate sentence (useful_lives_corpus) and recorded one row per statement in curated/useful_lives.csv:
numbers, asset class (company wording and a scope code), dates, URL / accession, locator and the SHA-256 of the exact
sentence. The sentence itself is kept only in data/raw/useful_lives_sentences (gitignored). Coding rules, written and
committed before the coding: docs/kallor/nyttjandeperioder.md.

Row types:
- policy : life_lo/life_hi in effect at period_end (the document's balance date)
- change : a change in estimate; life_lo/life_hi = new life, old_lo/old_hi = old life (if in the sentence), effective
- effect : the company's stated effect of a change (ref = the change row), signed change in effect_metric
- stop   : the first 10-K that no longer states the life of a class stated in the previous 10-K

known_from = `filed` (EDGAR filingDate). Series (series/useful_lives.py) are sparse step values per calendar quarter:
a value only where a document states it; in_effect() gives the step function as known on a date.
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import pandas as pd

from ai_tracker import config

PATH = config.REPO / "curated" / "useful_lives.csv"
SENTENCES_DIR = config.REPO / "data" / "raw" / "useful_lives_sentences"  # gitignored

COLUMNS = ["id", "company", "row_type", "ref", "asset_class", "class_code", "life_lo", "life_hi", "old_lo", "old_hi",
           "effective", "period_end", "effect_value", "effect_unit", "effect_metric", "effect_basis", "effect_start",
           "effect_end", "filed", "accepted", "doc_type", "source_url", "accession", "locator", "sentence_sha256",
           "note"]
COMPANIES = {"msft": "Microsoft", "googl": "Alphabet", "amzn": "Amazon", "meta": "Meta", "orcl": "Oracle",
             "crwv": "CoreWeave"}
ROW_TYPES = ("policy", "change", "effect", "stop")
SCOPES = ("SERVERS", "NETWORK", "SERVERS_NETWORK", "COMPUTER_EQUIPMENT", "TECH_INFRA", "OTHER")
CLASS_CODES = SCOPES + tuple(f"{s}_SUBSET" for s in SCOPES)
EFFECT_METRICS = ("depreciation", "operating_income", "net_income", "diluted_eps")
EFFECT_UNITS = ("MUSD", "USD per share")
EFFECT_BASES = ("expected", "actual")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()  # a stop row whose policy paragraph is gone (locator "absent")

# Catalog families: which class codes feed which series (docs/kallor/nyttjandeperioder.md, "Katalogserier").
# Within one document and quarter the first code listed wins (the more specific statement).
FAMILIES = {
    "servers": ("SERVERS", "SERVERS_NETWORK"),
    "network": ("NETWORK", "SERVERS_NETWORK"),
    "computer_equipment": ("COMPUTER_EQUIPMENT",),
    "tech_infra": ("TECH_INFRA",),
    "other": ("OTHER",),
}
MAX_LEAD_DAYS = 400  # a change announced before it applies: known_from >= end of the effective quarter - 400 days


class CsvError(ValueError):
    pass


def _float(x) -> float | None:
    return float(x) if str(x).strip() not in ("", "nan", "None") else None


def quarter(day) -> pd.Period:
    """Calendar quarter containing a date."""
    return pd.Timestamp(day).to_period("Q-DEC")


def _check_row(r: dict, ids: dict[str, dict]) -> None:
    if r["company"] not in COMPANIES or r["row_type"] not in ROW_TYPES:
        raise CsvError("company/row_type not in the scheme")
    if not re.fullmatch(r"[0-9a-f]{64}", r["sentence_sha256"]):
        raise CsvError("sentence_sha256 must be 64 hex characters")
    if not r["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/"):
        raise CsvError("source_url must be an EDGAR archive URL")
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", r["accession"]) or r["accession"].replace("-", "") not in r["source_url"]:
        raise CsvError("accession missing or not the URL's folder")
    absent = r["locator"] == "absent"
    if not absent and not re.fullmatch(r"sentence #\d+", r["locator"]):
        raise CsvError("locator must be 'sentence #k' (or 'absent' for a stop row)")
    if absent and (r["row_type"] != "stop" or r["sentence_sha256"] != EMPTY_SHA256):
        raise CsvError("locator 'absent' only for a stop row, with the SHA-256 of an empty string")
    filed = pd.Timestamp(r["filed"])
    if r["accepted"] and not -4 <= (pd.Timestamp(r["accepted"][:10]) - filed).days <= 1:
        raise CsvError(f"accepted {r['accepted']} does not match the filing date {r['filed']}")
    if r["period_end"] and pd.Timestamp(r["period_end"]) >= filed:
        raise CsvError("period_end (balance date) must be before the filing date")
    lo, hi, old_lo, old_hi = (_float(r[c]) for c in ("life_lo", "life_hi", "old_lo", "old_hi"))
    effect_cols = ("effect_value", "effect_unit", "effect_metric", "effect_basis", "effect_start", "effect_end")
    if r["row_type"] != "effect":
        if r["ref"] or any(r[c] for c in effect_cols):
            raise CsvError("ref and effect_* are only for effect rows")
        if r["class_code"] not in CLASS_CODES or not r["asset_class"].strip():
            raise CsvError(f"class_code {r['class_code']!r} not in the scheme, or asset_class missing")
    if r["row_type"] in ("policy", "change"):
        if hi is None or (lo is not None and lo > hi) or not 0 < hi <= 50:
            raise CsvError("life_hi required (and life_lo <= life_hi, years in (0, 50])")
    if r["row_type"] == "policy":
        if not r["period_end"] or old_lo is not None or old_hi is not None or r["effective"]:
            raise CsvError("a policy row has period_end and no old_*/effective")
    elif r["row_type"] == "change":
        if not r["effective"] or not r["period_end"]:
            raise CsvError("a change row needs effective and period_end")
        if (old_lo is None) != (old_hi is None) or (old_lo is not None and old_lo > old_hi):
            raise CsvError("old_lo/old_hi: both or neither, old_lo <= old_hi")
        lead = (quarter(r["effective"]).end_time.normalize() - filed).days
        if lead > MAX_LEAD_DAYS:
            raise CsvError(f"effective quarter ends {lead} days after the filing (> {MAX_LEAD_DAYS})")
    elif r["row_type"] == "effect":
        ref = ids.get(r["ref"])
        if ref is None or ref["row_type"] != "change" or ref["company"] != r["company"]:
            raise CsvError(f"ref {r['ref']!r} is not an earlier change row of the same company")
        if any(r[c] for c in ("life_lo", "life_hi", "old_lo", "old_hi", "effective", "asset_class", "class_code")):
            raise CsvError("an effect row has no life/class columns (they are on the change row)")
        if _float(r["effect_value"]) is None or r["effect_unit"] not in EFFECT_UNITS:
            raise CsvError("effect_value and effect_unit (MUSD / USD per share) required")
        if r["effect_metric"] not in EFFECT_METRICS or r["effect_basis"] not in EFFECT_BASES:
            raise CsvError("effect_metric/effect_basis not in the scheme")
        if (r["effect_metric"] == "diluted_eps") != (r["effect_unit"] == "USD per share"):
            raise CsvError("diluted_eps is in USD per share, the other metrics in MUSD")
        start, end = pd.Timestamp(r["effect_start"]), pd.Timestamp(r["effect_end"])
        if not start < end:
            raise CsvError("effect_start must be before effect_end")
        if r["effect_basis"] == "actual" and end >= filed:
            raise CsvError("an actual effect is stated after its period ended")
    elif r["row_type"] == "stop":
        if any(_float(r[c]) is not None for c in ("life_lo", "life_hi", "old_lo", "old_hi")) or r["effective"]:
            raise CsvError("a stop row has no numbers")
        if not r["doc_type"].startswith("10-K"):
            raise CsvError("a stop is coded in a 10-K")


def load(path: Path | None = None) -> pd.DataFrame:
    """Validated rows of the curated CSV, with known_from (= filed) as Timestamp."""
    path = path or PATH
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if rows and list(rows[0]) != COLUMNS:
        raise CsvError(f"columns {list(rows[0])} != {COLUMNS}")
    ids: dict[str, dict] = {}
    for r in rows:
        try:
            if r["id"] in ids:
                raise CsvError("duplicate id")
            _check_row(r, ids)
        except (CsvError, ValueError) as exc:
            raise CsvError(f"{path.name} id={r.get('id')}: {exc}") from None
        ids[r["id"]] = r
    df = pd.DataFrame(rows, columns=COLUMNS)
    for c in ("life_lo", "life_hi", "old_lo", "old_hi", "effect_value"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["known_from"] = pd.to_datetime(df["filed"])
    return df


# ------------------------------------------------------------------ series

def points(df: pd.DataFrame, company: str, family: str) -> pd.DataFrame:
    """Stated (period, lo, hi, known_from) points of one company and family, before de-duplication.

    policy -> the quarter of period_end; change -> the new life in the quarter of `effective` and, when the old life
    is in the sentence, the old life in the quarter before. Within one document and quarter one point survives:
    policy before change, then the family's first class code (the more specific statement).
    """
    codes = FAMILIES[family]
    d = df[(df["company"] == company) & df["class_code"].isin(codes) & df["row_type"].isin(["policy", "change"])]
    out = []
    for pos, r in enumerate(d.itertuples(index=False)):
        rank = codes.index(r.class_code)
        if r.row_type == "policy":
            out.append((quarter(r.period_end), r.life_lo, r.life_hi, r.known_from, r.accession, (0, rank), pos, r.id))
        else:
            eff = pd.Timestamp(r.effective)
            out.append((quarter(eff), r.life_lo, r.life_hi, r.known_from, r.accession, (1, rank), pos, r.id))
            if pd.notna(r.old_hi):
                out.append((quarter(eff - pd.Timedelta(days=1)), r.old_lo, r.old_hi, r.known_from, r.accession,
                            (1, rank), pos, r.id))
    cols = ["period", "lo", "hi", "known_from", "accession", "prio", "pos", "id"]
    p = pd.DataFrame(out, columns=cols)
    if p.empty:
        return p
    p = p.sort_values(["known_from", "accession", "period", "prio", "pos"], kind="stable")
    return p.drop_duplicates(["accession", "period"], keep="first").reset_index(drop=True)


def series_frame(df: pd.DataFrame, company: str, family: str, bound: str) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) of the lower ('lo') or upper ('hi') end of the stated life.

    A value repeated for the same quarter in a later document adds no row; a changed value is a new vintage.
    """
    p = points(df, company, family)
    out, last = [], {}
    if not p.empty:
        p = p.dropna(subset=[bound])
        for per, v, kf in p[["period", bound, "known_from"]].itertuples(index=False):
            if per in last and last[per] == v:
                continue
            last[per] = v
            out.append((str(per), float(v), kf))
    res = pd.DataFrame(out, columns=["period", "value", "known_from"])
    res = res.drop_duplicates(["period", "known_from"], keep="last")
    return res.sort_values(["period", "known_from"]).reset_index(drop=True)


def in_effect(company: str, family: str = "servers", bound: str = "hi", as_of=None, end=None,
              df: pd.DataFrame | None = None) -> pd.Series:
    """The stated life per calendar quarter as known on `as_of`: a step function (the latest stated value carries).

    Uses only rows with known_from <= as_of, the newest vintage per quarter, and carries the last stated value to
    `end` (default: the last stated quarter). Empty when nothing is known on `as_of`.
    """
    df = load() if df is None else df
    f = series_frame(df, company, family, bound)
    if as_of is not None:
        f = f[f["known_from"] <= pd.Timestamp(as_of)]
    if f.empty:
        return pd.Series(dtype=float)
    latest = f.sort_values("known_from").groupby("period")["value"].last()
    latest.index = pd.PeriodIndex(latest.index, freq="Q-DEC")
    last = latest.index.max() if end is None else max(latest.index.max(), pd.Period(end, freq="Q-DEC"))
    idx = pd.period_range(latest.index.min(), last, freq="Q-DEC")
    return latest.reindex(idx).ffill().rename(f"{company}_{family}_{bound}")


def changes(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Change rows (all class codes, subsets included) with their stated effects (one row per effect; none -> NaN)."""
    df = load() if df is None else df
    ch = df[df["row_type"] == "change"].drop(columns=[c for c in COLUMNS if c.startswith("effect_")] + ["ref"])
    ef = df[df["row_type"] == "effect"][["ref", "id", "effect_value", "effect_unit", "effect_metric", "effect_basis",
                                         "effect_start", "effect_end", "filed"]]
    ef = ef.rename(columns={"id": "effect_id", "filed": "effect_filed"})
    return ch.merge(ef, left_on="id", right_on="ref", how="left").drop(columns=["ref"])


def stopped(df: pd.DataFrame, company: str, family: str) -> pd.Series | None:
    """The stop row if the family's newest policy/change/stop row of the company is a stop, else None."""
    d = df[(df["company"] == company) & df["class_code"].isin(FAMILIES[family])
           & df["row_type"].isin(["policy", "change", "stop"])]
    if d.empty:
        return None
    last = d.sort_values("known_from", kind="stable").iloc[-1]
    return last if last["row_type"] == "stop" else None
