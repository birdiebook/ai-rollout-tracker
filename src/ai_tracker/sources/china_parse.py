"""Deterministic table parsing of Alibaba's and Baidu's quarterly results releases (track CN1).

Input is the plain text of a release (tsmc_sec.to_text: tags dropped, whitespace collapsed). Only tables are read;
figures that appear only in sentences are extracted by ai_tracker.sources.china_text (curated, publish=False). The
rules are those of the register entry 2026-11-25 CN1 (docs/mattregister.md):

Alibaba (fiscal year to 31 March; its quarters end on calendar quarter ends, so the June quarter is calendar Q2):
- the reported quarter comes from the title ("Announces <Month> Quarter <year> ... Results", or the HKEX-style
  "ANNOUNCEMENT OF THE <MONTH> QUARTER <year> RESULTS");
- cloud segment revenue: the first table after "breakdown of (our) revenue by segment" whose header is "Three months
  ended <Month> <d>, <year-1> <year>", row "AI Cloud and Compute Services" / "Cloud Intelligence Group" / "Cloud
  computing" / "Cloud". After the label, percentages ("7 %", "(25 )%") and a footnote marker ("(3)") are dropped;
  exactly three amounts must remain: prior-year quarter (RMB), quarter (RMB), quarter (US$);
- capex: the reconciliation of net cash provided by operating activities to free cash flow, row "Less: Purchase(s)
  of property and equipment ..." with its full label kept as the definition. The header gives three months (and
  optionally six/nine months or a year); the row must have 3 or 6 amounts, the first two being the prior-year and
  current quarter (RMB). Stored as a positive amount.
Baidu (calendar year):
- the reported quarter comes from the title ("Baidu Announces <First|...|Fourth> Quarter (and Fiscal Year) <year>
  Results");
- capex: row "Less: Capital expenditures" of the first "Condensed Consolidated Statements of Cash Flows" table. Its
  header has four column groups "Three months ended <Month> <d>, <year> (RMB|US$|USD)" (dates, years and currencies
  may be interleaved by the HTML layout), each with three entities in the order Baidu excl. iQIYI, iQIYI, Baidu, Inc.
  The row must have 4 x 3 amounts, the first entity token after the dates must be "Baidu", and in every group the
  third column must equal the first plus the second within 1 MRMB ("Baidu excl. iQIYI represents Baidu, Inc. minus
  iQIYI's consolidated cash flows"), or the table is not used. Only the RMB groups are kept.

A row that does not match its layout exactly is not used (None), never guessed. Values are RMB millions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
AMOUNT = r"\(\s*[\d,]+(?:\.\d+)?\s*\)|-?[\d,]+(?:\.\d+)?|—|-"
# one token after a row label: an amount, a percentage (dropped), a footnote marker (dropped), N/A
TOKEN = re.compile(r"\s*(\(\s*[\d,]+(?:\.\d+)?\s*\)\s*%|-?[\d,]+(?:\.\d+)?\s*%|\(\d\)(?=\s)|N/A|n/m|nm"
                   rf"|{AMOUNT})(?=\s|$)")
SPAN = 2500  # characters after a table header that hold its rows
SUM_TOL = 1.0  # MRMB: Baidu, Inc. = Baidu excl. iQIYI + iQIYI, each rounded to millions


def amount(tok: str) -> float:
    tok = tok.replace(" ", "")
    if tok in ("—", "-"):
        return 0.0
    neg = tok.startswith("(") or tok.startswith("-")
    v = float(tok.strip("()-").replace(",", ""))
    return -v if neg else v


def row_amounts(text: str, pos: int, limit: int = 40) -> list[str]:
    """Amount tokens after a row label at `pos`, up to the next word. Percentages, footnote markers and N/A are
    dropped; they never count as amounts."""
    out = []
    for _ in range(limit):
        m = TOKEN.match(text, pos)
        if not m:
            break
        tok = m.group(1)
        pos = m.end()
        if tok.endswith("%") or re.fullmatch(r"\(\d\)", tok) or tok in ("N/A", "n/m", "nm"):
            continue
        out.append(tok)
    return out


def quarter_of(month: str, day: str | int, year: str | int) -> pd.Period:
    return pd.Timestamp(f"{year} {month} {day}").to_period("Q-DEC")


@dataclass
class Release:
    """Figures of one results release: {measure: {quarter: (value MRMB, row label)}}."""

    company: str
    quarter: pd.Period  # the reported quarter
    dateline: pd.Timestamp | None = None  # the date in the release's dateline or sign-off, if found
    figures: dict[str, dict[pd.Period, tuple[float, str]]] = field(default_factory=dict)

    def add(self, measure: str, q: pd.Period, value: float, label: str) -> None:
        self.figures.setdefault(measure, {}).setdefault(q, (value, label))


def _norm(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip().lower()


CITY = r"(?:H ?angzhou|H ?ong K ?ong|B ?eijing)"  # "H ong Kong": a split letter in one release (2026-03-19)
DATELINE_RE = re.compile(rf"(?i)\b{CITY}(?:,? China)?,? ({MONTHS}|"
                         r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.? (\d{1,2}) ?,? (\d{4})\b")
# HKEX-style announcements end with "Hong Kong, May 15, 2025 As at the date of this results announcement, ..."
SIGNOFF_RE = re.compile(rf"\b{CITY},? ({MONTHS}) (\d{{1,2}}) ?,? (\d{{4}}) As at the date of this")
MONTH_ABBR = {m[:3].lower(): m for m in MONTHS.split("|")}


def dateline(text: str, head: int = 6000) -> pd.Timestamp | None:
    """The release date in its dateline ("HANGZHOU, China, November 25, 2025", "BEIJING, China, Nov 18, 2025") or in
    the sign-off of an HKEX-style announcement."""
    m = DATELINE_RE.search(text[:head]) or SIGNOFF_RE.search(text)
    if not m:
        return None
    month = MONTH_ABBR.get(m.group(1)[:3].lower(), m.group(1))
    try:
        return pd.Timestamp(f"{m.group(3)} {month} {m.group(2)}")
    except ValueError:
        return None


# ------------------------------------------------------------------ Alibaba

BABA_TITLE = re.compile(r"(?i)(?:announces|announcement of the) (March|June|September|December) quarter(?: (\d{4}))?"
                        r"(?: and (?:full )?(?:fiscal )?year (\d{4}))?\b[^.]{0,40}?\bresults")
BABA_SEGMENT_ANCHOR = re.compile(r"(?i)breakdown of (?:our )?(?:total )?revenues? by segments?")
THREE_MONTHS = re.compile(rf"Three months ended ({MONTHS}) (\d{{1,2}}),? (\d{{4}}) (\d{{4}})\b")
BABA_CLOUD_ROW = re.compile(r"(?<![A-Za-z] )\b(AI Cloud and Compute Services|Cloud Intelligence Group"
                            r"|Cloud computing|Cloud)\b(?! (?:business|segment|revenue|and Internet))")
FCF_ANCHOR = re.compile(r"(?i)to free cash flow for the periods indicated")
FCF_HEADER = re.compile(rf"Three months ended ({MONTHS}) (\d{{1,2}}),?"
                        rf"(?: (?:(?:Six|Nine|Twelve) months|(?:Fiscal )?Years?) ended (?:{MONTHS}) \d{{1,2}},?)?"
                        r" (\d{4}) (\d{4})\b")
BABA_CAPEX_ROW = re.compile(r"Less: Purchases? of property and equipment[^\d()]*(?:\([^)]*\)[^\d()]*?)?(?=\s\(|\s\d)")


def baba_quarter(text: str) -> pd.Period | None:
    m = BABA_TITLE.search(text[:4000])
    year = (m.group(2) or m.group(3)) if m else None  # "March Quarter and Full Fiscal Year 2019": the FY's last quarter
    return quarter_of(m.group(1), 1, year) if year else None


def baba_segment(text: str) -> tuple[pd.Period, pd.Period, float, float, str] | None:
    """(prior-year quarter, quarter, prior value, value, row label) of the cloud row, or None."""
    for am in BABA_SEGMENT_ANCHOR.finditer(text):
        hm = THREE_MONTHS.search(text, am.end(), am.end() + 300)
        if not hm:
            continue
        month, day, y0, y1 = hm.groups()
        if int(y1) != int(y0) + 1:
            continue
        rm = BABA_CLOUD_ROW.search(text, hm.end(), hm.end() + SPAN)
        if not rm:
            return None
        vals = row_amounts(text, rm.end())
        if len(vals) != 3:
            return None
        return (quarter_of(month, day, y0), quarter_of(month, day, y1), amount(vals[0]), amount(vals[1]),
                _norm(rm.group(1)))
    return None


def baba_capex(text: str) -> tuple[pd.Period, pd.Period, float, float, str] | None:
    """(prior-year quarter, quarter, prior value, value, row label) of the PP&E line of the FCF reconciliation."""
    for am in FCF_ANCHOR.finditer(text):
        hm = FCF_HEADER.search(text, am.end(), am.end() + 400)
        if not hm:
            continue
        month, day, y0, y1 = hm.groups()
        if int(y1) != int(y0) + 1:
            continue
        rm = BABA_CAPEX_ROW.search(text, hm.end(), hm.end() + SPAN)
        if not rm:
            return None
        vals = row_amounts(text, rm.end())
        if len(vals) not in (3, 6):
            return None
        label = _norm(rm.group(0).removeprefix("Less:"))
        return quarter_of(month, day, y0), quarter_of(month, day, y1), -amount(vals[0]), -amount(vals[1]), label
    return None


def parse_baba(text: str) -> Release | None:
    """An Alibaba quarterly results release in plain text, or None (no results title, or no figure readable)."""
    q = baba_quarter(text)
    if q is None:
        return None
    rel = Release("baba", quarter=q, dateline=dateline(text))
    seg = baba_segment(text)
    if seg is not None and seg[1] == q:
        q0, q1, v0, v1, label = seg
        rel.add("rev_cloud", q1, v1, label)
        rel.add("rev_cloud", q0, v0, label)
    cap = baba_capex(text)
    if cap is not None and cap[1] == q:
        q0, q1, v0, v1, label = cap
        rel.add("capex", q1, v1, label)
        rel.add("capex", q0, v0, label)
    return rel if rel.figures else None


# ------------------------------------------------------------------ Baidu

ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4}
BIDU_TITLE = re.compile(r"(?i)Baidu,? (?:Inc\. )?Announces (First|Second|Third|Fourth) Quarter(?: and (?:Full[- ])?"
                        r"(?:Fiscal )?Year)? (\d{4}) (?:Unaudited )?(?:Financial )?Results")
CF_ANCHOR = re.compile(r"Condensed Consolidated Statements of Cash Flows")
CF_FIRST_ROW = re.compile(r"Net cash")
MONTH_DAY = re.compile(rf"\b({MONTHS}) (\d{{1,2}})\b")
YEAR = re.compile(r"\b(\d{4})\b")
CURRENCY = re.compile(r"\((RMB|US\$|USD)\)")
BIDU_CAPEX_ROW = re.compile(r"Less: Capital expenditures")
ENTITY_KEYS = ("core", "iqiyi", "total")
N_GROUPS = 4


def bidu_quarter(text: str) -> pd.Period | None:
    m = BIDU_TITLE.search(text[:3000])
    return pd.Period(f"{m.group(2)}Q{ORDINAL[m.group(1).lower()]}", freq="Q-DEC") if m else None


def bidu_header(header: str) -> list[tuple[pd.Period, str]] | None:
    """[(quarter, currency)] of the column groups of a Baidu cash-flow header, or None if it does not match."""
    if not header.lstrip().startswith("(In millions"):
        return None
    if header.count("Three months ended") != N_GROUPS or "Twelve months" in header:
        return None
    dates = MONTH_DAY.findall(header)
    head = re.sub(r"\(In millions,\s*unaudited\)", "", header)
    years = YEAR.findall(MONTH_DAY.sub(" ", head))
    cur = CURRENCY.findall(header)
    if not (len(dates) == len(years) == len(cur) == N_GROUPS):
        return None
    last = max(m.end() for m in [*MONTH_DAY.finditer(header), *YEAR.finditer(header), *CURRENCY.finditer(header)])
    entities = header[last:].split()
    if not entities or entities[0] != "Baidu" or header.count("excl.") != N_GROUPS or header.count("Inc.") != N_GROUPS:
        return None
    return [(quarter_of(m, d, y), c) for (m, d), y, c in zip(dates, years, cur)]


def bidu_capex(text: str) -> dict[str, dict[pd.Period, float]] | None:
    """{entity: {quarter: capex MRMB (positive)}} from the three-month cash-flow table, RMB groups only."""
    am = CF_ANCHOR.search(text)
    if not am:
        return None
    fm = CF_FIRST_ROW.search(text, am.end(), am.end() + 1500)
    if not fm:
        return None
    groups = bidu_header(text[am.end():fm.start()])
    if groups is None:
        return None
    rm = BIDU_CAPEX_ROW.search(text, fm.start(), fm.start() + 3 * SPAN)
    if not rm:
        return None
    vals = [-amount(v) for v in row_amounts(text, rm.end())]
    if len(vals) != N_GROUPS * len(ENTITY_KEYS):
        return None
    out: dict[str, dict[pd.Period, float]] = {k: {} for k in ENTITY_KEYS}
    for g, (q, cur) in enumerate(groups):
        core, iqiyi, total = vals[3 * g: 3 * g + 3]
        if abs(core + iqiyi - total) > SUM_TOL:
            return None
        if cur != "RMB":
            continue
        for k, v in zip(ENTITY_KEYS, (core, iqiyi, total)):
            out[k].setdefault(q, v)
    return out


def parse_bidu(text: str) -> Release | None:
    """A Baidu quarterly results release in plain text, or None (no results title, or no capex table)."""
    q = bidu_quarter(text)
    if q is None:
        return None
    rel = Release("bidu", quarter=q, dateline=dateline(text))
    cap = bidu_capex(text)
    if cap is None or q not in cap["total"]:
        return None
    for entity, measure in (("total", "capex_total"), ("core", "capex_core")):
        for p, v in sorted(cap[entity].items()):
            rel.add(measure, p, v, "less: capital expenditures")
    return rel


PARSERS = {"baba": parse_baba, "bidu": parse_bidu}
