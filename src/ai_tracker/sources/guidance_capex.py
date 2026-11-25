"""Hyperscaler capex guidance: a curated CSV of agent-extracted values, loaded as release-dated series.

The guidance is not formulaic (it is spoken on calls, phrased differently each quarter, often qualitative), so
the agent reads each document and records one row per guided value in curated/guidance_capex.csv: numbers,
units, definition code, period guided, document date, source URL, locator and the SHA-256 of the exact source
sentence. The sentence itself is kept only in data/raw (gitignored): the repo is public, and from reports and
transcripts only extracted figures with a source reference are published.

known_from = `filed`, the date the document became public (the EDGAR filing date for SEC documents, the event
date for a call transcript). The loader refuses a row whose period had already ended when the document came out
(that would be an outcome, not guidance) and a row whose known_from is earlier than its document.

Coded values. kind = point | range | min (at least) | approx (about) | direction. A direction is stored as
direction_code: +2 increase significantly/meaningfully, +1 increase, 0 roughly flat / similar level, -1
decrease, -2 decrease significantly; direction_base says against what: qoq (vs the previous quarter), yoy (vs the
same period a year earlier), prior_fy (the fiscal year vs the previous fiscal year), growth_vs_prior (the growth
rate vs the previous year's growth rate). Definitions: DEFINITIONS below, documented in docs/kallor/guidance.md.

Publication (owner decision R11-4, 2026-11-25): a company's series are published when every row of the company comes
from a document on sec.gov, which is what gives them the licence class "ja" (ai_tracker.licenses, curated rule).
Alphabet, Amazon and Meta qualify; Microsoft's rows come from microsoft.com (class "okänd") and stay withheld. A new
row from another host withholds that company's series again. A new company needs a change to COMPANIES (and a review
of its extraction) first. tests/test_agarbeslut.py checks that publish equals class "ja" for every series.
"""

from __future__ import annotations

import csv
import hashlib
import re
from functools import lru_cache
from pathlib import Path

from urllib.parse import urlparse

import pandas as pd

from ai_tracker import config

PATH = config.REPO / "curated" / "guidance_capex.csv"
SENTENCES_DIR = config.REPO / "data" / "raw" / "guidance_capex_sentences"  # gitignored

COLUMNS = ["id", "company", "horizon", "period", "period_start", "period_end", "kind", "value_lo", "value_hi",
           "unit", "direction_code", "direction_base", "definition", "filed", "accepted", "doc_type", "source_url",
           "accession", "locator", "sentence_sha256", "note"]
COMPANIES = ("msft", "googl", "amzn", "meta")
HORIZONS = ("Q", "FY", "CY")  # next/current quarter, fiscal year (MSFT: July-June), calendar year
KINDS = ("point", "range", "min", "approx", "direction")
DIRECTION_BASES = ("qoq", "yoy", "prior_fy", "growth_vs_prior")

# definition code -> what the guided number measures (company wording, summarised)
DEFINITIONS = {
    "META_CAPEX_INCL_FL": "Meta: capital expenditures including principal payments on finance leases",
    "MSFT_CAPEX_INCL_FL": "Microsoft: capital expenditures including finance leases (cash PP&E + finance leases "
                          "acquired); Microsoft's call guidance basis",
    "GOOGL_CAPEX": "Alphabet: capital expenditures = purchases of property and equipment (cash flow statement)",
    "AMZN_CASH_CAPEX": "Amazon: cash capital expenditures = purchases of property and equipment net of proceeds "
                       "from sales and incentives",
    "AMZN_CAPEX_UNSPEC": "Amazon: 'capital expenditures'/'capex' without a stated basis (CEO statements); Amazon's "
                         "own capex measure in filings is cash capex",
    "GOOGL_TECH_INFRA": "Alphabet: 'investment in our technical infrastructure' (servers, network equipment, data "
                        "centers), the bulk of its capex; 10-K/10-Q outlook wording",
}


class CsvError(ValueError):
    pass


def sentence_hash(sentence: str) -> str:
    """SHA-256 of a source sentence after whitespace normalisation (one space, stripped)."""
    return hashlib.sha256(re.sub(r"\s+", " ", sentence).strip().encode("utf-8")).hexdigest()


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9$•“\"(])")


def sentences(text: str) -> list[str]:
    """Sentences of a document's plain text (tsmc_sec.to_text); locators count sentences in this list from 0."""
    return [x for x in _SENTENCE_SPLIT.split(text) if x.strip()]


# Candidate sentences for the agent's reading (E1's rule, widened after R11-1). E1 selected sentences with a capex
# word and a forward-looking word. Microsoft's FY2026 Q4 call put the CY2026 figure in the sentence after the capex
# sentences (#228: the lease shift "adjusts our expectation to approximately $175 billion"), without a capex word,
# so the sentence after every sentence with a capex word is also a candidate.
CAPEX_WORD_RE = re.compile(r"(?i)\b(?:capital\s+expenditures?|capex|capital\s+investments?|capital\s+spending|"
                           r"property\s+and\s+equipment|technical\s+infrastructure)\b")
FORWARD_WORD_RE = re.compile(r"(?i)\b(?:expect\w*|anticipat\w*|outlook|guidance|plan\w*|will|forecast\w*|estimat\w*|"
                             r"project\w*|intend\w*|remain\w*|continu\w*|grow\w*|increas\w*)\b")
AMOUNT_RE = re.compile(r"(?i)\$\s?\d+(?:\.\d+)?\s*(?:-\s*\d+(?:\.\d+)?\s*)?(?:billion|bn)\b")


def candidates(sents: list[str]) -> dict[int, str]:
    """Sentence number -> why it is a candidate: 'capex' (a capex word and a forward-looking word) or 'next' (the
    sentence after any sentence with a capex word; R11-1)."""
    out: dict[int, str] = {}
    for i, x in enumerate(sents):
        if CAPEX_WORD_RE.search(x):
            if FORWARD_WORD_RE.search(x):
                out[i] = "capex"
            if i + 1 < len(sents):
                out.setdefault(i + 1, "next")
    return out


def _float(x: str) -> float | None:
    return float(x) if str(x).strip() not in ("", "nan", "None") else None


def load(path: Path | None = None) -> pd.DataFrame:
    """Validated rows of the curated CSV, with known_from (= filed) as Timestamp."""
    path = path or PATH
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if rows and list(rows[0]) != COLUMNS:
        raise CsvError(f"columns {list(rows[0])} != {COLUMNS}")
    seen = set()
    for r in rows:
        where = f"{path.name} id={r.get('id')}"
        if r["id"] in seen:
            raise CsvError(f"{where}: duplicate id")
        seen.add(r["id"])
        if r["company"] not in COMPANIES or r["horizon"] not in HORIZONS or r["kind"] not in KINDS:
            raise CsvError(f"{where}: company/horizon/kind not in the scheme")
        if r["definition"] not in DEFINITIONS:
            raise CsvError(f"{where}: unknown definition {r['definition']!r}")
        if not re.fullmatch(r"[0-9a-f]{64}", r["sentence_sha256"]):
            raise CsvError(f"{where}: sentence_sha256 must be 64 hex characters")
        if not r["source_url"].startswith("https://") or not r["locator"].strip():
            raise CsvError(f"{where}: source_url and locator are required")
        filed = pd.Timestamp(r["filed"])
        start, end = pd.Timestamp(r["period_start"]), pd.Timestamp(r["period_end"])
        if not start < end:
            raise CsvError(f"{where}: period_start must be before period_end")
        if filed > end:
            raise CsvError(f"{where}: document filed {filed.date()} after the guided period ended {end.date()}")
        # EDGAR acceptance after 17:30 ET gets the next business day as filing date, so acceptance can be up to a
        # weekend earlier; known_from = filing date is then the conservative (later) date
        if r["accepted"] and not -4 <= (pd.Timestamp(r["accepted"][:10]) - filed).days <= 1:
            raise CsvError(f"{where}: accepted {r['accepted']} does not match the filing date {r['filed']}")
        lo, hi = _float(r["value_lo"]), _float(r["value_hi"])
        if r["kind"] == "direction":
            if r["direction_code"] not in ("-2", "-1", "0", "1", "2") or r["direction_base"] not in DIRECTION_BASES:
                raise CsvError(f"{where}: a direction needs direction_code in -2..2 and a direction_base")
        else:
            if lo is None or (r["kind"] in ("point", "range", "approx") and hi is None):
                raise CsvError(f"{where}: kind {r['kind']} needs value_lo (and value_hi)")
            if hi is not None and lo > hi:
                raise CsvError(f"{where}: value_lo > value_hi")
            if r["kind"] in ("point", "approx") and lo != hi:
                raise CsvError(f"{where}: a point/approx value has value_lo == value_hi")
    df = pd.DataFrame(rows, columns=COLUMNS)
    for c in ("value_lo", "value_hi"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["direction_code"] = pd.to_numeric(df["direction_code"], errors="coerce")
    df["known_from"] = pd.to_datetime(df["filed"])
    return df


# ------------------------------------------------------------------ series

# Series in the observation table: (company, horizon, measure). Quarter (Q) and calendar-year (CY) guidance get
# their calendar period. Microsoft's fiscal year (July-June) has no calendar period: its FY rows are stored with
# freq "A" and period = the calendar year in which the fiscal year ends (labelled as such).
MEASURES = {"lo": "value_lo", "hi": "value_hi", "dir": "direction_code"}  # dir series are split by direction_base
LAG = {"Q": -200, "A": -800}  # earliest seen: MSFT FY2026 direction on 2025-01-29, stored as period 2026 (701 days)


def _period(row) -> str:
    end = pd.Timestamp(row["period_end"])
    return str(end.to_period("Q-DEC")) if row["horizon"] == "Q" else str(end.year)


def _versions(df: pd.DataFrame, company: str, horizon: str, measure: str, base: str | None = None) -> pd.DataFrame:
    """series_frame's rows with the definition of the CSV row behind each version."""
    col = MEASURES[measure]
    d = df[(df["company"] == company) & (df["horizon"] == horizon)].copy()
    if measure == "dir":
        d = d[(d["kind"] == "direction") & (d["direction_base"] == base)]
    else:
        d = d[d["kind"] != "direction"]
    d = d.dropna(subset=[col])
    d["period"] = [_period(r) for _, r in d.iterrows()]
    d = d.sort_values("known_from", kind="stable")
    out, last = [], {}
    for p, v, kf, definition in d[["period", col, "known_from", "definition"]].itertuples(index=False):
        if p in last and last[p] == v:
            continue
        last[p] = v
        out.append((p, float(v), kf, definition))
    res = pd.DataFrame(out, columns=["period", "value", "known_from", "definition"])
    return res.drop_duplicates(["period", "known_from"], keep="last").reset_index(drop=True)


def series_frame(df: pd.DataFrame, company: str, horizon: str, measure: str, base: str | None = None) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) for one company/horizon/measure (and direction base).

    `lo`/`hi`: the guided numbers (a point or approx value fills both; a minimum fills lo only). `dir`: the coded
    direction against `base`. A value repeated in a later document adds no row; several statements in one
    document for the same period: the last row in file order wins.
    """
    return _versions(df, company, horizon, measure, base)[["period", "value", "known_from"]]


def definition_switches(df: pd.DataFrame, company: str, horizon: str, measure: str,
                        base: str | None = None) -> list[tuple[str, str, str, str]]:
    """(period, known_from day, old definition, new definition) for every version of the series whose row has
    another definition than the version before it of the same period (Amazon 2026: AMZN_CAPEX_UNSPEC, then
    AMZN_CASH_CAPEX). The register (F1) does not count such a change as a revision, so the series' note names it
    and the monthly letter does not call the earlier value "tidigare" (review R25-2)."""
    out, prev = [], {}
    for p, kf, definition in _versions(df, company, horizon, measure, base)[
            ["period", "known_from", "definition"]].itertuples(index=False):
        if p in prev and prev[p] != definition:
            out.append((p, str(pd.Timestamp(kf).date()), prev[p], definition))
        prev[p] = definition
    return out


def series_key(company: str, horizon: str, measure: str, base: str | None = None) -> str:
    return f"guid_capex_{company}_{horizon.lower()}_{measure}" + (f"_{base}" if base else "")


VARIANTS = [("lo", None), ("hi", None)] + [("dir", b) for b in DIRECTION_BASES]


def switch_note(switches: list[tuple[str, str, str, str]]) -> str:
    """The note's sentence on definition switches ("" without any)."""
    if not switches:
        return ""
    return ("Definitionsbyte inom en period, inte en revidering (F1): "
            + "; ".join(f"{p}: {old} → {new} ({kf})" for p, kf, old, new in switches) + ". ")


@lru_cache(maxsize=4)
def _switches_by_key(path: str, mtime: float) -> dict[str, dict[tuple[str, str], tuple[str, str]]]:
    df = load(Path(path))
    out: dict[str, dict[tuple[str, str], tuple[str, str]]] = {}
    for (company, horizon), _grp in df.groupby(["company", "horizon"], sort=True):
        for measure, base in VARIANTS:
            for p, kf, old, new in definition_switches(df, company, horizon, measure, base):
                out.setdefault(series_key(company, horizon, measure, base), {})[(p, kf)] = (old, new)
    return out


def definition_switch(key: str, period, known_from, path: Path | None = None) -> tuple[str, str] | None:
    """(old, new) definition when the version of guid_capex series `key` for `period` known from `known_from` comes
    from a row with another definition than the version before it; None otherwise (and for any other series)."""
    path = path or PATH
    if not str(key).startswith("guid_capex_") or not path.exists():
        return None
    switches = _switches_by_key(str(path), path.stat().st_mtime).get(key, {})
    return switches.get((str(period), str(pd.Timestamp(known_from).date())))


SEC_HOSTS = frozenset({"www.sec.gov", "sec.gov"})  # as ai_tracker.licenses.SEC_HOSTS (a test checks they agree)


def published_companies(df: pd.DataFrame) -> set[str]:
    """Companies whose every row has its source_url on sec.gov: their series are published (R11-4, module doc)."""
    out = set()
    for company, urls in df.groupby("company")["source_url"]:
        hosts = {urlparse(str(u).strip()).netloc.lower() for u in urls}
        if hosts and hosts <= SEC_HOSTS:
            out.add(company)
    return out


def specs(path: Path | None = None) -> list:
    """One Spec per (company, horizon, measure) present in the curated CSV."""
    from ai_tracker.catalog import Spec

    path = path or PATH
    if not path.exists():
        return []
    df = load(path)
    shown = published_companies(df)
    out = []
    names = {"msft": "Microsoft", "googl": "Alphabet", "amzn": "Amazon", "meta": "Meta"}
    hz_label = {"Q": "kvartal", "FY": "räkenskapsår (MSFT: juli–juni, period = året då det slutar)", "CY": "kalenderår"}
    for (company, horizon), grp in df.groupby(["company", "horizon"], sort=True):
        freq = "Q" if horizon == "Q" else "A"
        for measure, base in VARIANTS:
            if series_frame(df, company, horizon, measure, base).empty:
                continue
            sel = grp[grp["kind"] == "direction"] if measure == "dir" else grp[grp["kind"] != "direction"]
            if base:
                sel = sel[sel["direction_base"] == base]
            defs = ", ".join(sorted(set(sel["definition"])))
            key = series_key(company, horizon, measure, base)
            switches = switch_note(definition_switches(df, company, horizon, measure, base))
            what = {"lo": "lägsta/punktvärde", "hi": "högsta/punktvärde",
                    "dir": f"riktning mot {base} (kod −2..+2)"}[measure]

            def fetch(c=company, h=horizon, m=measure, b=base):
                return series_frame(load(path), c, h, m, b)

            out.append(Spec(
                key=key, branch="G5", label=f"Capex-guidance {names[company]}, {hz_label[horizon]}, {what}",
                unit="MUSD" if measure != "dir" else "kod", freq=freq,
                source="Kurerad extraktion (curated/guidance_capex.csv): SEC EDGAR 8-K/10-Q/10-K och bolagens "
                       "egna sidor", fetch=fetch, lag_days=LAG[freq],
                license="SEC EDGAR: public information (sec.gov/privacy). Bolagssidor: bara extraherade siffror "
                        "med källhänvisning, aldrig text",
                revised=True, publish=company in shown,
                question="Vad sa bolaget att capex skulle bli (baslinje B2 för N1)?",
                note=f"Definition(er): {defs}. {switches}Agentextraherat, stickprovsgranskat. "
                     + ("Publiceras: bolagets alla rader kommer från sec.gov (ägarbeslut R11-4, 2026-11-25). "
                        if company in shown else
                        "Visas inte: bolagets rader kommer inte alla från sec.gov (R11-4). ")
                     + "Se docs/kallor/guidance.md."))
    return out
