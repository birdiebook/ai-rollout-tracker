"""TSMC monthly revenue from its SEC Form 6-K filings (EDGAR), release-dated by filing date.

TSMC furnishes every monthly revenue report to the SEC as a 6-K, the same figures it files with
TWSE/MOPS (the legal channel, deadline the 10th of the following month). MOPS itself refuses this
client (WAF "FOR SECURITY REASONS"), so EDGAR is the history source. Each filing's EDGAR filing date
is its `known_from`: conservative, since the MOPS announcement is usually a few hours earlier on the
same Taiwan day.

Every report also restates the year-ago month (and, in older reports, the previous month). Those
comparatives are kept as later vintages only when they differ from what was known before (beyond
rounding), so restatements (e.g. the 2013 IFRS switch) become real vintages instead of leaking back.

Filings are immutable, so documents are cached: the raw copies that ai_tracker.http saves under
data/raw/tsmc_sec/<date>/ are reused on later runs.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

import pandas as pd

from ai_tracker import http

SOURCE = "tsmc_sec"
CIK = 1046179
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], start=1)}
MONTH_ABBR = {k[:3]: v for k, v in MONTHS.items()}


@dataclass
class Filing:
    accession: str
    filed: str  # EDGAR filing date, YYYY-MM-DD
    form: str
    document: str

    @property
    def url(self) -> str:
        return ARCHIVE.format(cik=CIK, acc=self.accession.replace("-", ""), doc=self.document)


@dataclass
class Report:
    """One monthly revenue report. Values in NT$ million."""

    period: pd.Period
    consolidated: float | None = None
    unconsolidated: float | None = None
    # restated comparatives in the same report: {"consolidated"|"unconsolidated": {period: value}}
    comparatives: dict[str, dict[pd.Period, float]] = field(default_factory=dict)


# ------------------------------------------------------------------ EDGAR access


def filings(form_prefix: str = "6-K") -> list[Filing]:
    """All filings of the given form (amendments included), oldest first."""
    sub = http.get(SUBMISSIONS.format(cik=CIK), SOURCE).json()
    blocks = [sub["filings"]["recent"]]
    blocks += [http.get(SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json() for f in sub["filings"].get("files", [])]
    out = {}
    for b in blocks:
        for form, filed, acc, doc in zip(b["form"], b["filingDate"], b["accessionNumber"], b["primaryDocument"]):
            if form.startswith(form_prefix) and not doc.endswith(".paper"):
                out[acc] = Filing(acc, filed, form, doc)
    return sorted(out.values(), key=lambda f: (f.filed, f.accession))


def _cached(url: str):
    """A raw copy saved by http.get on an earlier day (filings never change), else None."""
    name = http.raw_path(SOURCE, url).name
    hits = sorted((http.RAW_DIR / SOURCE).glob(f"*/{name}"))
    return hits[-1] if hits else None


def document_text(f: Filing) -> str:
    path = _cached(f.url)
    raw = path.read_bytes() if path else http.get(f.url, SOURCE).content
    return to_text(raw.decode("utf-8", errors="replace"))


def to_text(raw: str) -> str:
    """Markup to one line of plain text (tags dropped, entities decoded, whitespace collapsed)."""
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t.replace("\xa0", " ")).strip()


# ------------------------------------------------------------------ parsing

_MONTH = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
_NUM = r"\(?\s*[\d,]+(?:\.\d+)?\s*\)?"
# "net sales for May 2010", "revenue for October 2026", "net sales for October 2002 totaled"
PERIOD_RE = re.compile(r"(?i)(?:net sales|net revenues?|revenues?|sales) for " + _MONTH + r",? (\d{4})")
REPORT_RE = re.compile(r"(?i)(?:sales|revenue) report")
TABLE_RE = re.compile(r"(?i)report\s*(?:\((un)?consolidated\))?\s*:?\s*\(\s*unit\s*:\s*nt\$\s*million[^)]*\)")
THOUSANDS_RE = re.compile(
    r"(?i)\(in nt\$:?\s*thousands?\)\s*period items (\d{4}) (\d{4}) (?:[a-z]{3}\.? invoice amount [\d,]+ [\d,]+ )?"
    r"([a-z]{3})\.? net (?:sales|revenues?) "
    r"([\d,]+) ([\d,]+)")
SENTENCE_RE = re.compile(
    r"(?i)(un)?consolidated basis, (?:net )?(?:sales|revenues?)(?: for " + _MONTH + r",? (\d{4}))? "
    r"(?:was|were) (?:approximately )?NT\$ ?([\d,]+(?:\.\d+)?) (million|billion)")

EARLY_RE = re.compile(r"(?i)net sales for " + _MONTH + r",? (\d{4}) totaled NT\$ ?([\d,]+) million")


def _num(s: str) -> float:
    s = s.strip()
    neg = s.startswith("(")
    v = float(s.strip("() ").replace(",", ""))
    return -v if neg else v


def _amount(s: str) -> float:
    """An NT$ million table amount. These are whole numbers, so "49.956" is a typo for 49,956 (April 2014)."""
    return _num(re.sub(r"\.(?=\d{3}\b)", ",", s))


def _parse_table(seg: str, period: pd.Period) -> tuple[float, dict[pd.Period, float]] | None:
    """(current, comparatives) from the 'Sales/Revenue Report (Unit: NT$ million)' table text after its header."""
    month = period.strftime("%B")
    # new layout (2013-): Period <cur> <prev> M-o-M .. <year ago> Y-o-Y .. Net Sales cur prev pct yago pct
    m = re.match(r"(?i)\s*period " + month + r" \d{4} " + _MONTH + r" \d{4} m-o-m.*?net (?:sales|revenues?) "
                 rf"({_NUM}) ({_NUM}) ({_NUM}) ({_NUM}) ({_NUM})", seg[:600])
    if m:
        cur, prev, _, yago, _ = (_amount(m.group(i)) for i in range(2, 7))
        return cur, {period - 1: prev, period - 12: yago}
    # old layout (-2012): Net Sales <year> * <year-1> Increase (Decrease) % <Month> cur yago pct
    m = re.match(r"(?i)[\s-]*net sales (\d{4})\s*(?:\*|/\(1\)/|\(1\))?\s*(\d{4}).*?" + month + rf" ({_NUM}) ({_NUM})",
                 seg[:600])
    if m and int(m.group(1)) == period.year:
        return _amount(m.group(3)), {period - 12: _amount(m.group(4))}
    # 2004-2005 layout: <year> * <year-1> Growth Rate .. Net Sales for <Month> cur yago pct
    m = re.match(r"(?i)[\s-]*(\d{4})\s*(?:\*|/\(1\)/|\(1\))?\s*(\d{4}) growth.*?net sales for " + month
                 + rf" ({_NUM}) ({_NUM})", seg[:600])
    if m and int(m.group(1)) == period.year:
        return _amount(m.group(3)), {period - 12: _amount(m.group(4))}
    return None


def parse_report(text: str) -> Report | None:
    """Monthly revenue report in a 6-K's plain text, or None if the filing is something else."""
    if not REPORT_RE.search(text):
        return None
    pm = PERIOD_RE.search(text)
    if not pm:
        return None
    period = pd.Period(f"{pm.group(2)}-{MONTHS[pm.group(1).lower()]:02d}", freq="M")
    rep = Report(period)
    for tm in TABLE_RE.finditer(text):
        basis = "unconsolidated" if tm.group(1) else "consolidated" if "onsolidated" in tm.group(0) else None
        if basis is None:  # unlabelled table: the parent-only figures before consolidated reporting began
            basis = "unconsolidated" if period < pd.Period("2013-01", "M") else "consolidated"
        parsed = _parse_table(text[tm.end():], period)
        if parsed and getattr(rep, basis) is None:
            setattr(rep, basis, parsed[0])
            rep.comparatives[basis] = parsed[1]
    if rep.unconsolidated is None and period < pd.Period("2006-01", "M"):  # early reports: parent-only sentence
        em = EARLY_RE.search(text)
        if em and (int(em.group(2)), MONTHS[em.group(1).lower()]) == (period.year, period.month):
            rep.unconsolidated = _num(em.group(3))
    for sm in SENTENCE_RE.finditer(text):  # fallback when a report has no table
        basis = "unconsolidated" if sm.group(1) else "consolidated"
        if sm.group(2) and (int(sm.group(3)), MONTHS[sm.group(2).lower()]) != (period.year, period.month):
            continue
        if getattr(rep, basis) is None:
            v = _num(sm.group(4)) * (1000 if sm.group(5).lower() == "billion" else 1)
            setattr(rep, basis, v)
    # Regulatory section in NT$ thousands: more precise. Parent-only until 2012, consolidated from 2013 (IFRS).
    km = THOUSANDS_RE.search(text)
    if km and int(km.group(1)) == period.year and MONTH_ABBR.get(km.group(3).lower()) == period.month:
        basis = "consolidated" if period >= pd.Period("2013-01", "M") else "unconsolidated"
        precise = _num(km.group(4)) / 1000
        current = getattr(rep, basis)
        if current is None or abs(current - precise) <= 1.0:  # only refine, never override a different figure
            setattr(rep, basis, precise)
    if rep.consolidated is None and rep.unconsolidated is None:
        return None
    return rep


# ------------------------------------------------------------------ series


def reports() -> list[tuple[Filing, Report]]:
    out = []
    for f in filings():
        rep = parse_report(document_text(f))
        if rep is not None:
            out.append((f, rep))
    return out


def vintages(items: list[tuple[str, Report]], basis: str, tol: float = 1.0) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) for one basis.

    `items` = (filing date, report), any order. The report's own month is always a row. A restated
    comparative (year-ago or previous month) becomes a row only when the period was not known yet or
    its value differs from the latest known one by more than `tol` (NT$ million, table rounding).
    """
    known: dict[pd.Period, float] = {}
    rows: dict[tuple[pd.Period, str], float] = {}
    for filed, rep in sorted(items, key=lambda x: x[0]):
        value = getattr(rep, basis)
        if value is None:
            continue
        for p, v in sorted(rep.comparatives.get(basis, {}).items()):
            if p not in known or abs(known[p] - v) > tol:
                rows[(p, filed)] = known[p] = v
        if rep.period not in known or abs(known[rep.period] - value) > 1e-6:
            rows[(rep.period, filed)] = known[rep.period] = value
    df = pd.DataFrame([(str(p), v, pd.Timestamp(d)) for (p, d), v in rows.items()],
                      columns=["period", "value", "known_from"])
    return df.sort_values(["period", "known_from"]).reset_index(drop=True)


def fetch(basis: str = "consolidated") -> pd.DataFrame:
    return vintages([(f.filed, r) for f, r in reports()], basis)


# ------------------------------------------------------------------ TWSE cross-check

TWSE_MONTHLY = "https://openapi.twse.com.tw/v1/opendata/t187ap05_L"


def twse_current(company: str = "2330") -> dict:
    """Latest month from the TWSE open API (current month only; same figures as MOPS), NT$ million.

    Returns {period: value} for the current, previous and year-ago month. Used to cross-check the
    6-K figures; the API has no history and its 出表日期 is the table date, not the announcement date.
    """
    row = next(r for r in http.get(TWSE_MONTHLY, "twse").json() if r.get("公司代號") == company)
    ym = row["資料年月"]  # ROC year + month, e.g. 11510
    period = pd.Period(f"{int(ym[:-2]) + 1911}-{ym[-2:]}", freq="M")
    return {period: float(row["營業收入-當月營收"]) / 1000, period - 1: float(row["營業收入-上月營收"]) / 1000,
            period - 12: float(row["營業收入-去年當月營收"]) / 1000}
