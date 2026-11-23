"""US Census Business Trends and Outlook Survey (BTOS): national share of firms using AI.

Files (www.census.gov/hfp/btos/downloads/):
- National.xlsx: core questions for the current wording (Q7 current use, Q28 expected use in the next six
  months) from cycle 202524, plus "Collection and Reference Dates" with the Publication Date per cycle
  (also for cycles published before the wording change, and announced future cycles).
- AI Core Questions.xlsx: the original wording ("in producing goods or services"), Q7 and Q24,
  cycles 202319-202520. It has no publication dates; they come from National.xlsx.

A cycle ("smpdt") = ISO year of the first collection day + fortnight 01-26. Values are stored on the
W-SUN week in which the collection period ends (freq "2W"); the question refers to the two weeks
before collection (reference period), the expectation question to the next six months.

Question wording regimes are separate series, never spliced (docs/kallor/census_eu.md):
v1 202319-202520 "Artificial Intelligence (AI) in producing goods or services"
v2 202524-202621 "Artificial Intelligence (AI) in any of its business functions" (from 2025-11-17)
v3 202622-202701 "Super Intelligence or SI (formerly referred to as Artificial Intelligence or AI) in
   any of its business functions", new examples (instrument "Content Year 5, Cycle 2 with SI
   Supplement", fielded 2026-10-19 to 2027-01-17)
Cycles after the last regime (instrument fielded from 2027-01-18 changes the examples again) are not
assigned to any series until the wording has been reviewed: parse() drops them and warns.

Publication dates: the "Publication Date" column is a schedule (it also lists announced future cycles), not a
record of what happened. Cycle 202520 is scheduled for 2025-10-09, inside the federal funding lapse
(2025-10-01..2025-11-12) when Census did not normally update its site; the actual date could not be documented
(R1 review, docs/granskning/r1_lackage.md 3.6). A cycle scheduled inside a lapse is therefore known from the day
after the lapse (2025-11-13) until its real date is documented in PUBLISHED. Every fetch appends the schedule
with the fetch date to data/raw/census_btos/schedule_log.parquet, so schedule and outcome can be told apart.
"""

from __future__ import annotations

import io
import re
import warnings
from dataclasses import dataclass

import pandas as pd

from ai_tracker import http

BASE = "https://www.census.gov/hfp/btos/downloads/"
NATIONAL = BASE + "National.xlsx"
AI_CORE = BASE + "AI%20Core%20Questions.xlsx"
SOURCE = "census_btos"


@dataclass(frozen=True)
class Regime:
    version: str
    first: int  # first smpdt
    last: int | None  # last smpdt (None = open)
    file: str  # "national" or "ai_core"
    use_qid: int  # question id for current use
    expect_qid: int  # question id for expected use in the next six months
    wording: str


REGIMES = [
    Regime("v1", 202319, 202520, "ai_core", 7, 24,
           "did this business use Artificial Intelligence (AI) in producing goods or services?"),
    Regime("v2", 202524, 202621, "national", 7, 28,
           "did this business use Artificial Intelligence (AI) in any of its business functions?"),
    Regime("v3", 202622, 202701, "national", 7, 28,
           "did this business use Super Intelligence or SI (formerly referred to as Artificial "
           "Intelligence or AI) in any of its business functions?"),
]
SHUTDOWN_CYCLES = (202521, 202522, 202523)  # no collection (federal funding lapse 2025-10-01..11-13)
SHEETS = {  # file -> (estimates sheet, standard-error sheet)
    "national": ("Response Estimates", "Response Standard Errors"),
    "ai_core": ("National Estimates", "National SE"),
}
YES = 1  # answer id
# Federal funding lapses (first day, last day): a publication scheduled inside one is moved to the day after
FUNDING_LAPSES = [(pd.Timestamp("2025-10-01"), pd.Timestamp("2025-11-12"))]
# Documented actual publication dates that override the schedule (cycle -> date, with the source in a comment)
PUBLISHED: dict[int, str] = {}
SCHEDULE_LOG = http.RAW_DIR / "census_btos" / "schedule_log.parquet"


def _pct(x) -> float:
    if isinstance(x, str):
        x = x.strip()
        if not re.fullmatch(r"-?\d+(\.\d+)?%", x):
            return float("nan")  # "." (not asked / no data), "S" (suppressed)
        return float(x[:-1])
    if isinstance(x, (int, float)) and pd.notna(x):
        return float(x) * 100 if abs(x) <= 1 else float(x)
    return float("nan")


def parse_estimates(content: bytes, sheet: str) -> pd.DataFrame:
    """Long frame: qid, answer_id, smpdt, value (percent), question (text)."""
    df = pd.read_excel(io.BytesIO(content), sheet_name=sheet, header=0, dtype=object)
    df = df[pd.to_numeric(df["Question ID"], errors="coerce").notna()]
    cycles = [c for c in df.columns if re.fullmatch(r"\d{6}", str(c).split(".")[0])]
    long = df.melt(id_vars=["Question ID", "Question", "Answer ID"], value_vars=cycles,
                   var_name="smpdt", value_name="raw")
    return pd.DataFrame({
        "qid": long["Question ID"].astype(int).to_numpy(),
        "answer_id": pd.to_numeric(long["Answer ID"]).astype(int).to_numpy(),
        "smpdt": [int(str(c).split(".")[0]) for c in long["smpdt"]],
        "value": [_pct(v) for v in long["raw"]],
        "question": long["Question"].astype(str).to_numpy(),
    })


def parse_dates(content: bytes) -> pd.DataFrame:
    """smpdt, col_end, published from National.xlsx 'Collection and Reference Dates'."""
    df = pd.read_excel(io.BytesIO(content), sheet_name="Collection and Reference Dates", header=0)
    df = df[pd.to_numeric(df["Smpdt"], errors="coerce").notna()]
    return pd.DataFrame({
        "smpdt": df["Smpdt"].astype(int).to_numpy(),
        "col_end": pd.to_datetime(df["Col End"]).to_numpy(),
        "published": pd.to_datetime(df["Publication Date"]).to_numpy(),
    })


def release_date(smpdt: int, scheduled: pd.Timestamp) -> pd.Timestamp:
    """known_from for a cycle: a documented date if there is one, else the schedule, moved past a funding lapse."""
    if smpdt in PUBLISHED:
        return pd.Timestamp(PUBLISHED[smpdt])
    scheduled = pd.Timestamp(scheduled)
    for first, last in FUNDING_LAPSES:
        if first <= scheduled <= last:
            return last + pd.Timedelta(days=1)
    return scheduled


def log_schedule(dates: pd.DataFrame, fetched_at: pd.Timestamp, path=None) -> pd.DataFrame:
    """Append the file's schedule (smpdt, col_end, published) with the fetch date; one entry per fetch day."""
    path = SCHEDULE_LOG if path is None else path
    new = dates.assign(fetched_at=pd.Timestamp(fetched_at).normalize())
    if path.exists():
        old = pd.read_parquet(path)
        old = old[old["fetched_at"] != new["fetched_at"].iloc[0]] if len(new) else old
        new = pd.concat([old, new], ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    new.to_parquet(path, index=False)
    return new


def regime_of(smpdt: int) -> Regime | None:
    for r in REGIMES:
        if smpdt >= r.first and (r.last is None or smpdt <= r.last):
            return r
    return None


def check_wording(est: pd.DataFrame, regime: Regime, qid: int) -> None:
    """The question text in the file must match the regime; a silent wording change is a new break."""
    needles = {"v1": "in producing goods or services", "v2": "Artificial Intelligence (AI) in any of its",
               "v3": "Super Intelligence or SI (formerly referred to as Artificial Intelligence or AI)"}
    texts = set(est.loc[est["qid"] == qid, "question"])
    if not any(needles[regime.version] in t for t in texts):
        raise ValueError(f"BTOS Q{qid}: wording for {regime.version} not found in file: {texts}")


def build(national: bytes, ai_core: bytes, what: str, version: str, stat: str = "estimate",
          latest_wording: bool = True) -> pd.DataFrame:
    """Release-dated rows (period = collection end date, value, known_from = publication date).

    what: "use" or "expect"; stat: "estimate" or "se". latest_wording: check that the file's current
    question text is the wording of the newest regime (v3) - National.xlsx shows one text per question.
    """
    regime = next(r for r in REGIMES if r.version == version)
    content = national if regime.file == "national" else ai_core
    sheet = SHEETS[regime.file][0 if stat == "estimate" else 1]
    est = parse_estimates(content, sheet)
    qid = regime.use_qid if what == "use" else regime.expect_qid
    if regime.file == "ai_core":
        check_wording(est, regime, qid)
    elif latest_wording:
        check_wording(est, REGIMES[-1], qid)
    rows = est[(est["qid"] == qid) & (est["answer_id"] == YES)].dropna(subset=["value"])
    unassigned = sorted(c for c in rows["smpdt"] if regime_of(c) is None and c > REGIMES[-1].last)
    if unassigned and version == REGIMES[-1].version:
        warnings.warn(f"BTOS cycles {unassigned} are after the last reviewed wording regime and are not "
                      "stored; review the questionnaire and add a regime (docs/kallor/census_eu.md)")
    rows = rows[[regime_of(c) is regime for c in rows["smpdt"]]]
    dates = parse_dates(national)
    out = rows.merge(dates, on="smpdt", how="left", validate="one_to_one")
    if out["published"].isna().any():
        raise ValueError(f"BTOS: no publication date for cycles {list(out.loc[out['published'].isna(), 'smpdt'])}")
    out = out.sort_values("smpdt")
    known = [release_date(c, d) for c, d in zip(out["smpdt"], out["published"])]
    return pd.DataFrame({"period": out["col_end"].to_numpy(), "value": out["value"].to_numpy(),
                         "known_from": pd.to_datetime(known)})


_CACHE: dict[str, bytes] = {}


def _get(url: str) -> bytes:
    if url not in _CACHE:  # one download per process for all BTOS series
        _CACHE[url] = http.get(url, SOURCE).content
    return _CACHE[url]


_LOGGED: set[str] = set()


def fetch(what: str, version: str, stat: str = "estimate") -> pd.DataFrame:
    national = _get(NATIONAL)
    if NATIONAL not in _LOGGED:  # once per process: the schedule as it stood on this fetch
        log_schedule(parse_dates(national), pd.Timestamp.today())
        _LOGGED.add(NATIONAL)
    return build(national, _get(AI_CORE), what, version, stat)
