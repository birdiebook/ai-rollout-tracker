"""TSMC quarterly guidance from its SEC Form 6-K earnings filings (EDGAR), release-dated by filing date.

Every quarter TSMC's earnings press release (and the conference presentation, usually filed the same or
the next day) states its outlook for the current quarter: revenue between US$x and US$y billion (NT$
until 2017Q2), the USD/NT$ exchange-rate assumption (from 2008Q3), and gross and operating margin ranges.
See docs/kallor/guidance.md. Occasionally a guidance update is filed mid-quarter (e.g. 2007-09-10).

Until mid-2019 the 6-K's primary document is the release itself; from 2019-10 the primary document is a
cover page and the release / presentation are exhibits (99.1, 99.2), found through the filing index.

The guided quarter is the calendar quarter containing the filing date (guidance is given after the
previous quarter has closed, for the quarter in progress). When the text names the quarter ("for fourth
quarter 2010", "1Q11 Guidance") it must agree, otherwise the filing is rejected (ParseError), so a
mislabelled quarter can never move a value earlier.

known_from = the EDGAR filing date of the first filing that contains the value (the release is filed in
the Taiwan morning, so the date is conservative only by hours). acceptanceDateTime is kept alongside.
A value restated unchanged in a later filing (presentation, Form 20-F) adds no row; a changed value
(mid-quarter update) is a new vintage with its own date.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from ai_tracker import http
from ai_tracker.sources import tsmc_sec

SOURCE = "tsmc_guidance"
CIK = tsmc_sec.CIK
INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/index.json"
COVER_MAX_CHARS = 6000  # a cover page with exhibits is short; a self-contained release is longer
EXHIBITS_FROM = "2019-06-01"  # before this, earnings 6-Ks carry the text in the primary document

FIELDS = ("rev_lo", "rev_hi", "fx", "gm_lo", "gm_hi", "om_lo", "om_hi")


class ParseError(ValueError):
    pass


@dataclass
class Filing:
    accession: str
    filed: str  # YYYY-MM-DD
    accepted: str  # EDGAR acceptanceDateTime (UTC), ISO
    form: str
    document: str

    @property
    def folder(self) -> str:
        return self.accession.replace("-", "")

    def url(self, doc: str | None = None) -> str:
        return tsmc_sec.ARCHIVE.format(cik=CIK, acc=self.folder, doc=doc or self.document)


@dataclass
class Guidance:
    """Guidance found in one document. Revenue in million of `currency`, margins in %, fx in NT$ per US$."""

    quarter: pd.Period | None = None  # quarter named in the text, if any
    currency: str | None = None  # "USD" or "TWD"
    values: dict[str, float] = field(default_factory=dict)
    # a range for the following quarter given in the same statement (only 2015-09-23: "fourth-quarter revenue ...
    # likely to be between NT$198 billion and NT$204 billion"), as (quarter ordinal 1-4, values)
    next_quarter: tuple[int, dict[str, float]] | None = None


# ------------------------------------------------------------------ EDGAR access


def filings() -> list[Filing]:
    """All electronic 6-K / 6-K/A filings with acceptance time, oldest first."""
    sub = http.get(tsmc_sec.SUBMISSIONS.format(cik=CIK), SOURCE).json()
    blocks = [sub["filings"]["recent"]]
    blocks += [http.get(tsmc_sec.SUBMISSIONS_FILE.format(name=f["name"]), SOURCE).json()
               for f in sub["filings"].get("files", [])]
    out = {}
    for b in blocks:
        for form, filed, acc, doc, accepted in zip(b["form"], b["filingDate"], b["accessionNumber"],
                                                   b["primaryDocument"], b["acceptanceDateTime"]):
            if form.startswith("6-K") and not doc.endswith(".paper"):
                out[acc] = Filing(acc, filed, accepted, form, doc)
    return sorted(out.values(), key=lambda f: (f.filed, f.accepted, f.accession))


def _cached(source: str, url: str):
    name = http.raw_path(source, url).name
    hits = sorted((http.RAW_DIR / source).glob(f"*/{name}"))
    return hits[-1] if hits else None


def _text(url: str) -> str:
    """Plain text of one archived document; immutable, so any earlier raw copy is reused."""
    path = _cached(tsmc_sec.SOURCE, url) or _cached(SOURCE, url)
    raw = path.read_bytes() if path else http.get(url, SOURCE).content
    return tsmc_sec.to_text(raw.decode("utf-8", errors="replace"))


def documents(f: Filing) -> list[tuple[str, str]]:
    """(document name, text) for the primary document and, for a cover page, its .htm exhibits."""
    primary = _text(f.url())
    docs = [(f.document, primary)]
    if f.filed >= EXHIBITS_FROM and len(primary) < COVER_MAX_CHARS and re.search(r"(?i)exhibit", primary):
        if tsmc_sec.REPORT_RE.search(primary) and tsmc_sec.PERIOD_RE.search(primary):
            return docs  # a monthly revenue report, no exhibits of interest
        idx_url = INDEX.format(cik=CIK, acc=f.folder)
        path = _cached(SOURCE, idx_url)
        import json
        idx = json.loads(path.read_bytes()) if path else http.get(idx_url, SOURCE).json()
        for item in idx["directory"]["item"]:
            name = item["name"]
            if name.lower().endswith((".htm", ".html")) and name != f.document and "index" not in name:
                docs.append((name, _text(f.url(name))))
    return docs


# ------------------------------------------------------------------ parsing

_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_NUM = r"(\d+(?:\.\d+)?)"
_SNUM = r"(-?\s?\d+(?:\.\d+)?)"  # margins can be negative (1Q09: "between -19% and -15%")
_CUR = r"(NT|US)\s?\$\s?"
_BETWEEN = r"\s*(?:is\s*|are\s*)?(?:expected\s*)?to\s*(?:be|reach)\s*between\s*"
_PCT = r"\s*(?:%|°/o)"  # "49.5°/o" in OCR'd presentations
# "Revenue is expected to be between US$32.2 billion and US$33.4 billion", "Revenues to be between NT$ 102 billion
# and NT$ 104 billion", "first quarter revenue to be between NT$201 billion to NT$203 billion" (2016-02-17)
REV_RE = re.compile(r"(?i)revenues?" + _BETWEEN + _CUR + _NUM + r"\s*billion\s*(?:and|to)\s*" + _CUR + _NUM
                    + r"\s*billion")
# "exchange rate assumption of 1 US dollar to 30.6 NT dollars" / "forecast exchange rate of 29.26 NT dollars to 1 US
# dollar" / "exchange rate assumption (USD:NTD of 1:33.18 versus 1:32.50 on January 14)" (new value first).
# Presentations converted from PDF lose spaces ("exchange rateof30NT dollars to1USdollar").
FX_RE = (re.compile(r"(?i)exchange\s*rate\s*assumption\s*of\s*1\s*US\s*dollars?\s*to\s*" + _NUM + r"\s*NT\s*dollars?"),
         re.compile(r"(?i)forecast\s*exchange\s*rate\s*of\s*" + _NUM + r"\s*NT\s*dollars?\s*to\s*1\s*US\s*dollars?"),
         re.compile(r"(?i)exchange\s*rate\s*assumption\s*\(USD:NTD of 1:" + _NUM))
FX_BEFORE = 200  # "...and exchange rate assumption of 1 US dollar to 29.58 NT dollars, management expects" (2012)
# "is expected to be between 59% and 61%", "is now between 30% and 32%" (mid-quarter updates)
_MBETWEEN = r"\s*(?:is\s*|are\s*)?(?:now\s*)?(?:expected\s*)?(?:to\s*(?:be|reach)\s*)?between\s*"
MARGIN_RE = {
    "gm": re.compile(r"(?i)gross\s*(?:profit\s*)?margin" + _MBETWEEN + _SNUM + _PCT + r"\s*and\s*" + _SNUM + _PCT),
    "om": re.compile(r"(?i)operating\s*(?:profit\s*)?margin" + _MBETWEEN + _SNUM + _PCT + r"\s*and\s*" + _SNUM
                     + _PCT),
}
NEXT_RE = re.compile(r"(?i)(first|second|third|fourth)-quarter revenue[^.]{0,80}?between " + _CUR + _NUM
                     + r"\s*billion\s*(?:and|to)\s*" + _CUR + _NUM + r"\s*billion")
QUARTER_RES = (
    re.compile(r"(?i)\bfor (?:the )?(first|second|third|fourth) quarter (?:of )?(\d{4})"),
    re.compile(r"(?i)\b([1-4])Q[’']?(\d{2}) Guidance"),
)
# Only text from the guidance announcement on counts: the reported (past) quarter, its results and the guidance it
# had ("Guidance 31.8-33.0" in presentation tables) come before it.
ANCHOR_RE = re.compile(r"(?i)(management expects|management[’']s expectations|[1-4]Q[’']?\d{2} Guidance|"
                       r"(?:company|management|TSMC) now expects|(?:is|are) expected to be (?:better|between)|"
                       r"Guidance For the (?:first|second|third|fourth) quarter)")
ANCHOR_REACH = 600  # the revenue range must start within this many characters of the anchor
WINDOW = 800  # margins and FX are read up to this many characters after the revenue range
# Until 2006Q1 guidance was for the parent company only (unconsolidated); 2006Q2 gave both; from 2006Q3 the release
# reports consolidated results and guides on that basis. The target series (tsmc_revenue_m) is consolidated.
CONSOLIDATED_FROM = pd.Period("2006Q2", freq="Q-DEC")


def _quarter(text: str) -> pd.Period | None:
    """The quarter named last in `text` (the one closest to the revenue range), or None."""
    hits = sorted((m.start(), m) for rx in QUARTER_RES for m in rx.finditer(text))
    if not hits:
        return None
    m = hits[-1][1]
    q = _ORD.get(m.group(1).lower()) or int(m.group(1))
    year = int(m.group(2)) if len(m.group(2)) == 4 else 2000 + int(m.group(2))
    return pd.Period(f"{year}Q{q}", freq="Q-DEC")


def _pick(rx: re.Pattern, text: str, start: int, end: int) -> re.Match | None:
    """First match of rx in text[start:end], preferring one stated on a consolidated basis (2006Q2 gave both)."""
    hits = list(rx.finditer(text, start, end))
    for m in hits:
        if re.search(r"(?i)(?<!un)consolidated $", text[max(0, m.start() - 20):m.start()]):
            return m
    return hits[0] if hits else None


def parse_guidance(text: str) -> Guidance | None:
    """Revenue range (and FX, margins when stated) of a guidance statement, or None if there is none.

    Parsing starts at the guidance anchor ("management expects", "4Q25 Guidance", ...). The revenue range must
    follow within ANCHOR_REACH characters; FX and margins are read from the anchor to WINDOW characters after the
    range, stopping at a later revenue range. The quarter is read only between the anchor and the range (the
    reported, past quarter is named before the anchor).
    """
    a = ANCHOR_RE.search(text)
    while a:
        rev = _pick(REV_RE, text, a.start(), a.start() + ANCHOR_REACH + 200)
        if rev is None or rev.start() - a.start() > ANCHOR_REACH:
            a = ANCHOR_RE.search(text, a.end())
            continue
        nxt = REV_RE.search(text, rev.end())
        end = min(nxt.start() if nxt and nxt.start() > rev.end() + 150 else len(text), rev.end() + WINDOW)
        cur1, lo, cur2, hi = rev.groups()
        if cur1.upper() != cur2.upper():
            raise ParseError(f"mixed currencies in revenue range: {rev.group(0)!r}")
        g = Guidance(quarter=_quarter(text[a.start():rev.start()]), currency="USD" if cur1.upper() == "US" else "TWD")
        g.values["rev_lo"], g.values["rev_hi"] = float(lo) * 1000, float(hi) * 1000
        for rx in FX_RE:
            m = rx.search(text, max(0, a.start() - FX_BEFORE), end)
            if m:
                g.values["fx"] = float(m.group(1))
                break
        for k, rx in MARGIN_RE.items():
            m = _pick(rx, text, rev.start(), end)
            if m:
                g.values[f"{k}_lo"], g.values[f"{k}_hi"] = (float(m.group(i).replace(" ", "")) for i in (1, 2))
        nq = NEXT_RE.search(text, rev.end(), rev.end() + 600)
        if nq and nq.group(2).upper() == nq.group(4).upper() == cur1.upper():
            g.next_quarter = (_ORD[nq.group(1).lower()], {"rev_lo": float(nq.group(3)) * 1000,
                                                          "rev_hi": float(nq.group(5)) * 1000})
        for k in ("rev", "gm", "om"):
            if f"{k}_lo" in g.values and g.values[f"{k}_lo"] > g.values[f"{k}_hi"]:
                raise ParseError(f"{k} range reversed: {g.values}")
        return g
    return None


def guided_quarter(filed: str, g: Guidance) -> pd.Period:
    """The calendar quarter containing the filing date; the text's own quarter, if any, must agree."""
    q = pd.Period(filed, freq="Q-DEC")
    if g.quarter is not None and g.quarter != q:
        raise ParseError(f"filed {filed} but text guides {g.quarter}")
    return q


# ------------------------------------------------------------------ series


def records(items: list[tuple[Filing, list[tuple[str, str]]]] | None = None) -> pd.DataFrame:
    """One row per (filing, document) with guidance: quarter, currency, fields, filing metadata."""
    if items is None:
        items = [(f, documents(f)) for f in filings()]
    rows = []
    for f, docs in items:
        for name, text in docs:
            g = parse_guidance(text)
            if g is None:
                continue
            q = guided_quarter(f.filed, g)
            if q < CONSOLIDATED_FROM:
                continue  # parent-only guidance, a different basis than the target
            meta = {"currency": g.currency, "filed": f.filed, "accepted": f.accepted, "accession": f.accession,
                    "document": name, "form": f.form}
            rows.append({"period": str(q), **g.values, **meta})
            if g.next_quarter is not None:
                if g.next_quarter[0] != (q + 1).quarter:
                    raise ParseError(f"filed {f.filed}: second range for quarter {g.next_quarter[0]}, not {q + 1}")
                rows.append({"period": str(q + 1), **g.next_quarter[1], **meta})
    cols = ["period", "currency", *FIELDS, "filed", "accepted", "accession", "document", "form"]
    return pd.DataFrame(rows, columns=cols)


def vintages(recs: pd.DataFrame, value: str, currency: str | None = None, tol: float = 1e-9) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) for one field.

    `currency` restricts revenue fields to ranges stated in that currency. A row is emitted when the quarter's
    value is new or differs from the last known one; repeats in later filings add nothing.
    """
    r = recs.dropna(subset=[value])
    if currency is not None:
        r = r[r["currency"] == currency]
    r = r.sort_values(["filed", "accepted", "accession"])
    last: dict[str, float] = {}
    rows = []
    for p, v, filed in r[["period", value, "filed"]].itertuples(index=False):
        if p not in last or abs(last[p] - v) > tol:
            last[p] = v
            rows.append((p, float(v), pd.Timestamp(filed)))
    df = pd.DataFrame(rows, columns=["period", "value", "known_from"])
    return df.drop_duplicates(["period", "known_from"], keep="last").reset_index(drop=True)
