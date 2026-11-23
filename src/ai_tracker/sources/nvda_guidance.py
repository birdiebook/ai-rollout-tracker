"""Nvidia's revenue outlook for the next fiscal quarter, parsed deterministically from its 8-K earnings filings.

Every earnings press release (8-K Item 2.02, EX-99.1; the CFO commentary EX-99.2 repeats it) has an "Outlook"
section for the quarter in progress. The revenue statement is formulaic:

- 2012-02 onward, dollars: "Revenue is expected to be $54.0 billion, plus or minus 2%" (the band was 2% until
  2026Q3, 3% for the 14-week 2026Q4) and until 2013 "Revenue is expected to be between $900 million and $930 million";
- 2009-08 to 2011-11, change on the previous quarter: "Revenue is expected to be up 3 to 5 percent from the second
  quarter", "... flat from the fourth quarter", "... relatively flat, plus or minus two percent, from the third
  quarter", "... up slightly, approximately 2 percent, from the third quarter";
- before 2009-08 the releases carry no revenue outlook (it was given on the call only).

Period = the calendar quarter containing the guided fiscal quarter's midpoint, the same mapping as the revenue
series (sec.calendar_quarter): fiscal quarter k of fiscal year N (which ends in January of N) is calendar quarter k
of year N-1. The guidance is given 3-5 weeks into the guided fiscal quarter, so the filing date must lie inside the
fiscal quarter named in the text ("outlook for the third quarter of fiscal 2026"; dates from fiscal_quarter_dates);
otherwise the filing is rejected (ParseError) and nothing is stored. A statement filed after its fiscal quarter has
ended (a preliminary result, e.g. 2019-01-28 and 2022-08-08) is not guidance and is skipped.

known_from = the EDGAR filing date of the first filing stating the value (Nvidia files at about 16.20 ET, before
the 17.30 cut-off, so the filing date is the release day). acceptanceDateTime is kept alongside. A value repeated in
a later filing adds no row; a changed value (a mid-quarter update) is a new vintage. Documents are read from the
filing's complete submission text (<acc>.txt), which works for every year (older filings have no index.json).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from ai_tracker import http
from ai_tracker.sources import tsmc_sec

SOURCE = "nvda_guidance"
CIK = 1045810
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
FULL_TEXT = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}.txt"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{doc}"
FIRST = "2009-01-01"  # no revenue outlook in the releases before 2009-08

FIELDS = ("rev_lo", "rev_hi", "rev_mid", "band_pct", "qoq_lo", "qoq_hi")


class ParseError(ValueError):
    pass


@dataclass
class Filing:
    accession: str
    filed: str
    accepted: str
    form: str
    items: str


@dataclass
class Outlook:
    fiscal_quarter: int  # 1-4
    fiscal_year: int
    values: dict[str, float]
    kind: str  # "usd" or "qoq"
    statement: str  # the matched revenue statement (kept in data/raw only, never committed)

    @property
    def period(self) -> pd.Period:
        return pd.Period(f"{self.fiscal_year - 1}Q{self.fiscal_quarter}", freq="Q-DEC")

    @property
    def fiscal_dates(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        return fiscal_quarter_dates(self.fiscal_year, self.fiscal_quarter)


def _last_sunday_of_january(year: int) -> pd.Timestamp:
    d = pd.Timestamp(f"{year}-01-31")
    return d - pd.Timedelta(days=(d.dayofweek + 1) % 7)


def fiscal_quarter_dates(fiscal_year: int, quarter: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    """(first day, last day) of Nvidia's fiscal quarter: the fiscal year ends on the last Sunday of January; Q1-Q3
    are 13 weeks, Q4 takes the rest (14 weeks in a 53-week year)."""
    start_fy = _last_sunday_of_january(fiscal_year - 1) + pd.Timedelta(days=1)
    start = start_fy + pd.Timedelta(weeks=13 * (quarter - 1))
    end = _last_sunday_of_january(fiscal_year) if quarter == 4 else start + pd.Timedelta(weeks=13, days=-1)
    return start, end


# ------------------------------------------------------------------ EDGAR access


def filings(first: str = FIRST) -> list[Filing]:
    """All 8-K / 8-K/A filings from `first`, oldest first."""
    sub = http.get(SUBMISSIONS.format(cik=CIK), SOURCE).json()
    blocks = [sub["filings"]["recent"]]
    blocks += [http.get(SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json()
               for f in sub["filings"].get("files", [])]
    out = {}
    for b in blocks:
        for form, filed, acc, items, accepted in zip(b["form"], b["filingDate"], b["accessionNumber"], b["items"],
                                                    b["acceptanceDateTime"]):
            if form.startswith("8-K") and filed >= first:
                out[acc] = Filing(acc, filed, accepted, form, items)
    return sorted(out.values(), key=lambda f: (f.filed, f.accepted, f.accession))


def _cached(url: str):
    name = http.raw_path(SOURCE, url).name
    hits = sorted((http.RAW_DIR / SOURCE).glob(f"*/{name}"))
    return hits[-1] if hits else None


_DOC_RE = re.compile(r"(?s)<DOCUMENT>\s*<TYPE>([^\n<]+).*?<FILENAME>([^\n<]+)(.*?)</DOCUMENT>")


def split_documents(raw: str) -> list[tuple[str, str, str]]:
    """(type, filename, plain text) of each document in a complete submission text file."""
    return [(m.group(1).strip(), m.group(2).strip(), tsmc_sec.to_text(m.group(3))) for m in _DOC_RE.finditer(raw)]


def documents(f: Filing) -> list[tuple[str, str, str]]:
    """The 8-K body and its EX-99 exhibits (type, filename, text); archived filings never change, so any earlier
    raw copy is reused."""
    url = FULL_TEXT.format(cik=CIK, acc=f.accession)
    path = _cached(url)
    raw = (path.read_bytes() if path else http.get(url, SOURCE).content).decode("utf-8", errors="replace")
    return [d for d in split_documents(raw) if d[0].startswith(("8-K", "EX-99"))]


# ------------------------------------------------------------------ parsing

_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
            "ten": 10}
_N = r"(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)"
_PCT = r"\s*(?:percent|%)"
_AMT = r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(million|billion)"  # "$1,050 million" (2014-02)
_EXP = r"(?i)revenue\s+is\s+expected\s+to\s+be\s+"

# "Our outlook for the first quarter of fiscal 2013, is as follows", "NVIDIA's outlook for the fourth quarter of
# fiscal 2027, which includes an additional week, is as follows", "The combined second quarter outlook" (named
# earlier in the same sentence), "NVIDIA expects revenue in the third quarter ending October 25, 2009"
OUTLOOK_RE = re.compile(r"(?i)outlook\s+for\s+(?:the\s+)?(first|second|third|fourth)\s+quarter\s+of\s+fiscal\s+"
                        r"(?:year\s+)?(\d{4})")
EXPECTS_RE = re.compile(r"(?i)expects\s+revenue\s+in\s+the\s+(first|second|third|fourth)\s+quarter\s+ending\s+"
                        r"([A-Z][a-z]+\.?\s+\d{1,2},\s+\d{4})")
REACH = 700  # the revenue statement must start within this many characters of the outlook heading

USD_BAND_RE = re.compile(_EXP + _AMT + r",?\s*plus\s+or\s+minus\s+" + _N + _PCT)
USD_RANGE_RE = re.compile(_EXP + r"between\s+" + _AMT + r"\s+(?:and|to)\s+" + _AMT)
# change on the previous quarter (2009-08 .. 2011-11)
QOQ_RES = (
    ("updown", re.compile(r"(?i)revenue\s+(?:in\s+the\s+[a-z]+\s+quarter[^.]{0,40}?,\s*)?(?:is\s+expected\s+)?"
                          r"to\s+be\s+(up|down)\s+(?:seasonally\s+)?" + _N + r"\s+to\s+" + _N + _PCT)),
    ("flatband", re.compile(_EXP + r"(?:relatively\s+)?flat,?\s*plus\s+or\s+minus\s+" + _N + _PCT)),
    ("approx", re.compile(_EXP + r"(up|down)\s+slightly,?\s*\(?\s*(?:approximately\s+)?" + _N + _PCT)),
    ("flat", re.compile(_EXP + r"flat\b")),
)


def _num(s: str) -> float:
    return float(_WORDNUM.get(s.lower(), s))


def _musd(value: str, unit: str) -> float:
    return float(value.replace(",", "")) * (1000.0 if unit.lower() == "billion" else 1.0)


def _fiscal_from_date(ordinal: str, date: str) -> tuple[int, int]:
    """'third', 'October 25, 2009' -> (3, 2010): the fiscal year ends in late January after the quarter's end."""
    end = pd.Timestamp(date.replace(".", ""))
    q = _ORD[ordinal.lower()]
    return q, end.year + (1 if q < 4 or end.month > 6 else 0)


def parse_outlook(text: str) -> Outlook | None:
    """The revenue outlook of one document, or None if there is none.

    The first outlook heading followed (within REACH characters) by a revenue statement counts. A heading with no
    statement nearby (a forward-looking-statements boilerplate mention) is passed over.
    """
    heads = sorted([(m.start(), m, "fy") for m in OUTLOOK_RE.finditer(text)]
                   + [(m.start(), m, "date") for m in EXPECTS_RE.finditer(text)], key=lambda x: x[0])
    for start, h, how in heads:
        q, fy = (_ORD[h.group(1).lower()], int(h.group(2))) if how == "fy" else _fiscal_from_date(h.group(1), h.group(2))
        if how == "date":  # "expects revenue in the third quarter ending ... to be up 5 to 7 percent"
            seg_start = h.start()
        else:
            seg_start = h.end()
        seg = text[seg_start:seg_start + REACH]
        cands = []
        for rx, kind in ((USD_BAND_RE, "band"), (USD_RANGE_RE, "range")):
            m = rx.search(seg)
            if m:
                cands.append((m.start(), kind, m))
        for kind, rx in QOQ_RES:
            m = rx.search(seg)
            if m:
                cands.append((m.start(), kind, m))
        if not cands:
            continue
        _, kind, m = min(cands, key=lambda c: (c[0], c[1] != "flatband"))  # 'flat, plus or minus' over plain 'flat'
        if kind == "band":
            mid, band = _musd(m.group(1), m.group(2)), _num(m.group(3))
            vals = {"rev_mid": mid, "band_pct": band, "rev_lo": mid * (1 - band / 100), "rev_hi": mid * (1 + band / 100)}
            out = Outlook(q, fy, vals, "usd", m.group(0))
        elif kind == "range":
            lo, hi = _musd(m.group(1), m.group(2)), _musd(m.group(3), m.group(4))
            if lo > hi:
                raise ParseError(f"revenue range reversed: {m.group(0)!r}")
            out = Outlook(q, fy, {"rev_lo": lo, "rev_hi": hi, "rev_mid": (lo + hi) / 2}, "usd", m.group(0))
        elif kind == "updown":
            a, b = _num(m.group(2)), _num(m.group(3))
            lo, hi = (a, b) if m.group(1).lower() == "up" else (-b, -a)
            out = Outlook(q, fy, {"qoq_lo": lo, "qoq_hi": hi}, "qoq", m.group(0))
        elif kind == "flatband":
            b = _num(m.group(1))
            out = Outlook(q, fy, {"qoq_lo": -b, "qoq_hi": b}, "qoq", m.group(0))
        elif kind == "approx":
            v = _num(m.group(2)) * (1 if m.group(1).lower() == "up" else -1)
            out = Outlook(q, fy, {"qoq_lo": v, "qoq_hi": v}, "qoq", m.group(0))
        else:  # flat
            out = Outlook(q, fy, {"qoq_lo": 0.0, "qoq_hi": 0.0}, "qoq", m.group(0))
        if out.kind == "qoq" and "qoq_lo" in out.values and out.values["qoq_lo"] > out.values["qoq_hi"]:
            raise ParseError(f"change range reversed: {m.group(0)!r}")
        return out
    return None


def check_period(filed: str, o: Outlook) -> pd.Period:
    """The guided calendar quarter. The filing date must lie inside the guided fiscal quarter (guidance comes 3-5
    weeks into it); otherwise the fiscal quarter named in the text is not the one in progress (ParseError)."""
    start, end = o.fiscal_dates
    if not start <= pd.Timestamp(filed) <= end:
        raise ParseError(f"filed {filed} outside the guided Q{o.fiscal_quarter} FY{o.fiscal_year} "
                         f"({start.date()}..{end.date()})")
    return o.period


# ------------------------------------------------------------------ series


def records(items: list[tuple[Filing, list[tuple[str, str, str]]]] | None = None) -> pd.DataFrame:
    """One row per (filing, document) with a revenue outlook: period, fields, filing metadata, statement."""
    if items is None:
        items = [(f, documents(f)) for f in filings()]
    rows = []
    for f, docs in items:
        for typ, name, text in docs:
            o = parse_outlook(text)
            if o is None:
                continue
            if pd.Timestamp(f.filed) > o.fiscal_dates[1]:
                continue  # stated after the fiscal quarter ended: a preliminary result, not guidance
            q = check_period(f.filed, o)
            rows.append({"period": str(q), "fiscal": f"Q{o.fiscal_quarter} FY{o.fiscal_year}", "kind": o.kind,
                         **o.values, "filed": f.filed, "accepted": f.accepted, "accession": f.accession,
                         "doc_type": typ, "document": name, "form": f.form, "items": f.items,
                         "statement": o.statement})
    cols = ["period", "fiscal", "kind", *FIELDS, "filed", "accepted", "accession", "doc_type", "document", "form",
            "items", "statement"]
    return pd.DataFrame(rows, columns=cols)


def vintages(recs: pd.DataFrame, field: str, tol: float = 1e-6) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) for one field; a repeated value adds no row."""
    r = recs.dropna(subset=[field]).sort_values(["filed", "accepted", "accession"], kind="stable")
    last: dict[str, float] = {}
    rows = []
    for p, v, filed in r[["period", field, "filed"]].itertuples(index=False):
        if p not in last or abs(last[p] - v) > tol:
            last[p] = v
            rows.append((p, float(v), pd.Timestamp(filed)))
    df = pd.DataFrame(rows, columns=["period", "value", "known_from"])
    return df.drop_duplicates(["period", "known_from"], keep="last").reset_index(drop=True)


def document_url(accession: str, document: str) -> str:
    return ARCHIVE.format(cik=CIK, folder=accession.replace("-", ""), doc=document)
