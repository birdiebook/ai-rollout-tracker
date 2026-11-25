"""Spread at issuance for AI-heavy issuers (track KR1): curated term-sheet rows, quarterly series and the XBRL check.

Rows. curated/credit_issuance.csv holds one row per tranche of the registered bond offerings of Microsoft, Alphabet,
Amazon, Meta, Oracle and CoreWeave, 2020-01-01 to 2026-11-25, read from the final pricing term sheet (FWP), or from the
final prospectus supplement when an offering has no term sheet, with the deterministic parser (sources/credit_terms.py)
and checked by the agent (method "parser"), or coded by hand where the parser cannot read the document as stated
(method "manual", the note says why). Each row has the document's URL, accession, EDGAR filing date (known_from), the
locator of the tranche's block in the line list (credit_issuance_corpus.lines) and the block's SHA-256; the block text
is kept only under data/raw (gitignored). Every corpus document that is not coded is listed with its reason in
curated/credit_issuance_skipped.csv. Coding rules, committed before any document was read:
docs/kallor/kredit_emission.md; their implementation after review R20: register 2026-11-25, X17.

Series (quarterly, calendar quarter of the pricing date; register 2026-11-25, KR1):
- issuance(company): sum of principal (MUSD) of the company's USD tranches, fixed and floating;
- spread(companies, band): principal-weighted mean of the stated spread over USD fixed-rate tranches with a US
  Treasury benchmark; band (6.5, 12.5) keeps tenors that round to 7-12 years.
A quarter without an eligible tranche has no value (a gap, not zero). A quarter's version is dated
max(day after the quarter end, latest filing date of its tranches); a later filing gives a new version, and a quarter
that has not ended on `as_of` has no value.

    python -m ai_tracker.sources.credit_issuance build      # parse the corpus, write the CSVs and the blocks
    python -m ai_tracker.sources.credit_issuance coverage   # against XBRL debt_issued_<co>, per year and quarter
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from datetime import date

import numpy as np
import pandas as pd

from ai_tracker import config
from ai_tracker.sources import credit_issuance_corpus as cc
from ai_tracker.sources import credit_terms as ct

PATH = config.REPO / "curated" / "credit_issuance.csv"
SKIPPED_PATH = config.REPO / "curated" / "credit_issuance_skipped.csv"  # corpus documents not coded, with the reason
SKIPPED_COLUMNS = ["company", "form", "filed", "accession", "why"]
BLOCKS_DIR = config.REPO / "data" / "raw" / "credit_issuance_blocks"  # gitignored
COMPANIES = {"msft": "Microsoft", "googl": "Alphabet", "amzn": "Amazon", "meta": "Meta", "orcl": "Oracle",
             "crwv": "CoreWeave"}
COLUMNS = ["id", "company", "currency", "rate_type", "security", "principal", "pricing_date", "settlement_date",
           "maturity", "tenor_years", "coupon_pct", "benchmark", "benchmark_type", "benchmark_yield_pct", "spread_bp",
           "yield_pct", "price_pct", "filed", "accepted", "form", "source_url", "accession", "locator", "block_sha256",
           "method", "note"]
NUMERIC = ["principal", "tenor_years", "coupon_pct", "benchmark_yield_pct", "spread_bp", "yield_pct", "price_pct"]
RATE_TYPES = ("fixed", "floating")
BENCHMARK_TYPES = ("treasury", "sofr", "mid_swaps", "other")
METHODS = ("parser", "manual")
FORMS = cc.FORMS
SUPPLEMENTS = ("424B2", "424B5")
COVER_DAYS = 7  # a final supplement is filed 0-7 days after its term sheet
BAND_7_12 = (6.5, 12.5)  # tenor rounded to whole years in 7..12 (register 2026-11-25, KR1)
MIN_SPREAD_QUARTERS = 4  # an issuer gets its own spread series with at least this many quarters
YIELD_TOL = 0.01  # percent: yield = benchmark yield + spread within 1 bp (self-check)

# Rows the parser reads but the document states wrongly or not as the rule needs: (company, pricing date, security)
# -> {column: value, "note": why}. Each is listed in docs/kallor/kredit_emission.md ("Tolkningar").
MANUAL: dict[tuple[str, str, str], dict] = {
    ("orcl", "2021-03-22", "3.950% Notes due 2051"): {
        "principal": 3250.0,
        "note": "FWP states $3,250,000,0000 (one zero too many); the final 424B2 (0001193125-21-091259, filed "
                "2021-03-23) states $3,250,000,000 and the offering total $15,000,000,000",
    },
}


class CsvError(ValueError):
    pass


# ------------------------------------------------------------------ build (agent run, network)


def tranche_set(rows: list[dict]) -> frozenset:
    return frozenset((r["currency"], r["principal"], r["rate_type"], r["coupon_pct"], r["maturity"]) for r in rows)


def locator(r: dict) -> str:
    loc = f"lines #{r['a']}-#{r['b']}"
    return loc + (f" col #{r['col']}" if r["col"] is not None else "")


COVER_RE = re.compile(r"^(US\$|C\$|\$|€|£|¥)\s?([\d,]+)\s+(?:aggregate principal amount of\s+)?"
                      r"(Floating(?: Rate)?|\d+\.\d+\s?%)\s+(?:Senior\s+)?Notes\s+due\s+(\d{4})", re.I)


def cover_tranches(doc_lines: list[str]) -> set[tuple]:
    """(currency, principal in millions, coupon or 'F', maturity year) from the cover of a final prospectus supplement."""
    out = set()
    for line in doc_lines[:150]:
        m = COVER_RE.match(line)
        if m:
            kind = "F" if m.group(3).lower().startswith("floating") else f"{float(m.group(3).rstrip('% ')):.4f}"
            out.add((ct.CURRENCY[m.group(1)], float(m.group(2).replace(",", "")) / 1e6, kind, m.group(4)))
    return out


def offering_tranches(rows: list[dict]) -> set[tuple]:
    """The rows' tranches as on a supplement's cover: (currency, principal, coupon as %.4f or 'F', maturity year)."""
    out = set()
    for r in rows:
        fixed = r["coupon_pct"] is not None and not pd.isna(r["coupon_pct"])
        kind = "F" if r["rate_type"] == "floating" else (f"{float(r['coupon_pct']):.4f}" if fixed else "?")
        out.add((r["currency"], float(r["principal"]) if r["principal"] is not None else None, kind,
                 str(r["maturity"])[:4]))
    return out


def source_of(company: str, filed: str, cover: set[tuple], sources: list[dict]) -> str | None:
    """Accession of the coded source of a final supplement's offering, or None.

    sources: dicts (company, filed, accession, tranches = offering_tranches of its rows). The offering has a source
    when a source of the same company filed 0-COVER_DAYS days before the supplement has a tranche on its cover, or
    when a source has exactly the cover's tranches (register 2026-11-25, X17)."""
    day = pd.Timestamp(filed)
    own = [s for s in sources if s["company"] == company]
    for s in own:
        if s["tranches"] == cover:
            return s["accession"]
    for s in own:
        if 0 <= (day - pd.Timestamp(s["filed"])).days <= COVER_DAYS and s["tranches"] & cover:
            return s["accession"]
    return None


def _rows(d: dict, lines: list[str], parsed: list[dict], counter: dict) -> list[dict]:
    """CSV rows (with the block under "_block") for the parsed tranches of one source document."""
    out = []
    for p in parsed:
        n = counter[(d["company"], p["pricing_date"])] = counter.get((d["company"], p["pricing_date"]), 0) + 1
        block, _ = cc.block_at(lines, locator(p))
        row = {
            "id": f"{d['company']}_{p['pricing_date']}_{n:02d}", "company": d["company"],
            **{c: p[c] for c in ("currency", "rate_type", "security", "principal", "pricing_date",
                                 "settlement_date", "maturity", "tenor_years", "coupon_pct", "benchmark",
                                 "benchmark_type", "benchmark_yield_pct", "spread_bp", "yield_pct", "price_pct")},
            "filed": d["filed"], "accepted": d["accepted"], "form": d["form"], "source_url": d["url"],
            "accession": d["accession"], "locator": locator(p), "block_sha256": cc.block_hash(block),
            "method": "parser", "note": "; ".join(x for x in (p["note"], f"pricing date from the {p['pricing_from']}"
                                                               if p["pricing_from"] != "trade" else "") if x),
        }
        fix = MANUAL.get((d["company"], p["pricing_date"], p["security"]))
        if fix:
            row.update({k: v for k, v in fix.items() if k != "note"})
            row["method"] = "manual"
            row["note"] = "; ".join(x for x in (row["note"], fix["note"]) if x)
        row["_block"] = block
        out.append(row)
    return out


def _order(d: dict) -> tuple:
    return d["filed"], d["accepted"], d["url"]


def rows_from_documents(docs: list[dict], fetch=cc.doc_lines) -> tuple[list[dict], list[dict]]:
    """(CSV rows, every document not coded with its reason under "why"), both in filing order.

    Term sheets first: an FWP with final terms is the source of its offering, and a later FWP with the same tranches
    as an earlier one is a re-filing. Then the final prospectus supplements (424B2, 424B5): one whose offering already
    has a source (source_of) is not coded, and one without is the source when the parser reads exactly the tranches on
    its cover. Otherwise it is listed with HAND and "hand": True, and the build stops until it is coded by hand
    (register 2026-11-25, X17)."""
    rows, skipped, sources, seen = [], [], [], {}
    counter: dict[tuple[str, str], int] = {}
    ordered = sorted(docs, key=_order)
    for d in ordered:
        if d["form"] != "FWP":
            continue
        lines = fetch(d["url"])
        k = cc.kind(lines)
        if k != "final":
            skipped.append({**d, "why": k if k == "preliminary" else "no final debt terms"})
            continue
        _, parsed = ct.parse(lines, d["filed"])
        if not parsed:
            skipped.append({**d, "why": "no tranche parsed"})
            continue
        ts = tranche_set(parsed)
        if (d["company"], ts) in seen:
            skipped.append({**d, "why": f"re-filing of {seen[(d['company'], ts)]}"})
            continue
        seen[(d["company"], ts)] = d["accession"]
        new = _rows(d, lines, parsed, counter)
        rows += new
        sources.append({"company": d["company"], "filed": d["filed"], "accession": d["accession"],
                        "tranches": offering_tranches(new)})
    for d in ordered:
        if d["form"] not in SUPPLEMENTS:
            continue
        lines = fetch(d["url"])
        k = cc.kind(lines)
        if k != "final":
            skipped.append({**d, "why": k if k == "preliminary" else "no final debt terms"})
            continue
        cover = cover_tranches(lines)
        if not cover:
            skipped.append({**d, "why": "no debt tranche on the cover"})
            continue
        src = source_of(d["company"], d["filed"], cover, sources)
        if src:
            skipped.append({**d, "why": f"final supplement of {src}"})
            continue
        _, parsed = ct.parse(lines, d["filed"])
        trial = dict(counter)
        new = _rows(d, lines, parsed, trial) if parsed else []
        if new and offering_tranches(new) == cover:
            counter = trial
            rows += new
            sources.append({"company": d["company"], "filed": d["filed"], "accession": d["accession"],
                            "tranches": cover})
            continue
        skipped.append({**d, "hand": True, "why": "final supplement without a term sheet, the parser does not read "
                                                  f"the tranches on its cover: {ct.HAND}"})
    position = {d["url"]: i for i, d in enumerate(ordered)}
    rows.sort(key=lambda r: position[r["source_url"]])  # stable: tranche order within a document
    skipped.sort(key=_order)
    return rows, skipped


def _text(x) -> str:
    """A CSV cell: numbers as stated, without rounding (the shortest form that reads back to the same float)."""
    if x is None:
        return ""
    if isinstance(x, (float, np.floating)):
        x = float(x)
        if math.isnan(x):
            return ""
        return str(int(x)) if x.is_integer() and abs(x) < 1e15 else repr(x)
    return x


def write(rows: list[dict], path=PATH) -> None:
    BLOCKS_DIR.mkdir(parents=True, exist_ok=True)
    for r in rows:
        if "_block" in r:
            (BLOCKS_DIR / f"{r['id']}.txt").write_text("\n".join(r["_block"]), encoding="utf-8")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: _text(r.get(c)) for c in COLUMNS})


def write_skipped(skipped: list[dict], path=SKIPPED_PATH) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SKIPPED_COLUMNS, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for s in skipped:
            w.writerow(s)


def load_skipped(path=SKIPPED_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str).fillna("")


# ------------------------------------------------------------------ load and validate


def _float(x) -> float | None:
    return float(x) if str(x).strip() not in ("", "nan", "None") else None


def _check_row(r: dict) -> None:
    if r["company"] not in COMPANIES:
        raise CsvError("company not in the scheme")
    if r["rate_type"] not in RATE_TYPES or r["benchmark_type"] not in BENCHMARK_TYPES or r["method"] not in METHODS:
        raise CsvError("rate_type, benchmark_type or method not in the scheme")
    if r["form"] not in FORMS:
        raise CsvError(f"form {r['form']!r} not in the corpus forms")
    if not re.fullmatch(r"[A-Z]{3}", r["currency"]):
        raise CsvError("currency must be an ISO code")
    if not re.fullmatch(r"[0-9a-f]{64}", r["block_sha256"]):
        raise CsvError("block_sha256 must be 64 hex characters")
    if not r["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/"):
        raise CsvError("source_url must be an EDGAR archive URL")
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", r["accession"]) or r["accession"].replace("-", "") not in r["source_url"]:
        raise CsvError("accession missing or not the URL's folder")
    if not re.fullmatch(r"lines #\d+-#\d+(?: col #\d+)?", r["locator"]):
        raise CsvError("locator must be 'lines #a-#b' with an optional ' col #j'")
    a, b = (int(x) for x in re.findall(r"#(\d+)", r["locator"])[:2])
    if a > b:
        raise CsvError("locator: a > b")
    filed, pricing = pd.Timestamp(r["filed"]), pd.Timestamp(r["pricing_date"])
    if not 0 <= (filed - pricing).days <= 10:
        raise CsvError("filed must be 0-10 days after the pricing date")
    if r["accepted"] and not -4 <= (pd.Timestamp(r["accepted"][:10]) - filed).days <= 1:
        raise CsvError(f"accepted {r['accepted']} does not match the filing date {r['filed']}")
    if r["settlement_date"] and not 0 <= (pd.Timestamp(r["settlement_date"]) - pricing).days <= 15:
        raise CsvError("settlement_date must be 0-15 days after the pricing date")
    maturity = pd.Timestamp(r["maturity"])
    tenor = _float(r["tenor_years"])
    if tenor is None or abs(tenor - ct.tenor_years(r["pricing_date"], r["maturity"])) > 0.005 or maturity <= pricing:
        raise CsvError("tenor_years must be (maturity - pricing_date) / 365.25 with two decimals")
    principal = _float(r["principal"])
    if principal is None or principal <= 0:
        raise CsvError("principal (millions of the currency) required")
    price = _float(r["price_pct"])
    if price is None or not 80 <= price <= 110:
        raise CsvError("price_pct required, in [80, 110]")
    coupon, spread, yld = (_float(r[c]) for c in ("coupon_pct", "spread_bp", "yield_pct"))
    if r["rate_type"] == "fixed":
        if coupon is None or not 0 < coupon < 20:
            raise CsvError("a fixed-rate tranche needs coupon_pct in (0, 20)")
    elif coupon is not None:
        raise CsvError("a floating-rate tranche has no coupon_pct")
    if spread is not None and not 0 <= spread <= 1500:
        raise CsvError("spread_bp must be in [0, 1500]")
    if r["benchmark_type"] == "treasury" and (r["currency"] != "USD" or r["rate_type"] != "fixed"):
        raise CsvError("a treasury benchmark only for a USD fixed-rate tranche")
    if r["method"] == "manual" and not r["note"].strip():
        raise CsvError("a manual row needs a note saying why")
    if r["method"] == "parser" and ct.HAND in r["note"]:
        raise CsvError("the parser could not apply the rules to this row: code it by hand (MANUAL)")
    if yld is not None and not 0 < yld < 25:
        raise CsvError("yield_pct must be in (0, 25)")


def load(path=PATH) -> pd.DataFrame:
    """The curated rows, validated (CsvError names the row)."""
    with open(path, newline="", encoding="utf-8") as f:
        raw = list(csv.DictReader(f))
    if raw and list(raw[0]) != COLUMNS:
        raise CsvError(f"columns must be {COLUMNS}")
    ids = set()
    for r in raw:
        if r["id"] in ids:
            raise CsvError(f"{r['id']}: duplicate id")
        ids.add(r["id"])
        if not r["id"].startswith(f"{r['company']}_{r['pricing_date']}_"):
            raise CsvError(f"{r['id']}: id must be <company>_<pricing_date>_<nn>")
        try:
            _check_row(r)
        except CsvError as e:
            raise CsvError(f"{r['id']}: {e}") from None
    df = pd.DataFrame(raw, columns=COLUMNS)
    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c].replace("", np.nan))
    return df


# ------------------------------------------------------------------ series


def eligible_spread(df: pd.DataFrame, band: tuple[float, float] | None = None) -> pd.DataFrame:
    """USD fixed-rate tranches with a Treasury benchmark and a stated spread (and a tenor in the band)."""
    m = ((df["currency"] == "USD") & (df["rate_type"] == "fixed") & (df["benchmark_type"] == "treasury")
         & df["spread_bp"].notna())
    if band is not None:
        m &= (df["tenor_years"] >= band[0]) & (df["tenor_years"] < band[1])
    return df[m]


def quarter_versions(rows: pd.DataFrame, agg, as_of=None) -> pd.DataFrame:
    """Release-dated quarterly rows from tranche rows (columns pricing_date, filed, principal, ...).

    Quarter = calendar quarter of the pricing date. For a quarter q, every candidate date is
    max(day after the end of q, filed) of one of its tranches; at each, the value is agg() over the tranches filed on or
    before it. A row is written when the value is new or changed. Dates after as_of (default today) are dropped, so a
    quarter that has not ended has no value. agg(frame) -> float or None (None = no value)."""
    as_of = pd.Timestamp(as_of or date.today())
    out = []
    if rows.empty:
        return pd.DataFrame(columns=["period", "value", "known_from"])
    q = pd.PeriodIndex(pd.to_datetime(rows["pricing_date"]), freq="Q-DEC")
    rows = rows.assign(_q=q.astype(str), _filed=pd.to_datetime(rows["filed"]))
    for period, g in rows.groupby("_q"):
        start = pd.Period(period, freq="Q-DEC").end_time.normalize() + pd.Timedelta(days=1)
        last = None
        for d in sorted({max(start, f) for f in g["_filed"]}):
            if d > as_of:
                break
            v = agg(g[g["_filed"] <= d])
            if v is not None and (last is None or abs(v - last) > 1e-9):
                out.append((period, float(v), d))
                last = v
    return pd.DataFrame(out, columns=["period", "value", "known_from"]).sort_values(
        ["known_from", "period"], ignore_index=True)


def _sum_principal(g: pd.DataFrame):
    return float(g["principal"].sum()) if len(g) else None


def _weighted_spread(g: pd.DataFrame):
    w = g["principal"]
    return float((g["spread_bp"] * w).sum() / w.sum()) if len(g) and w.sum() > 0 else None


def issuance(df: pd.DataFrame, company: str, as_of=None) -> pd.DataFrame:
    rows = df[(df["company"] == company) & (df["currency"] == "USD")]
    return quarter_versions(rows, _sum_principal, as_of)


def spread(df: pd.DataFrame, companies: tuple[str, ...] | None = None, band: tuple[float, float] | None = None,
           as_of=None) -> pd.DataFrame:
    rows = eligible_spread(df, band)
    if companies is not None:
        rows = rows[rows["company"].isin(companies)]
    return quarter_versions(rows, _weighted_spread, as_of)


def spread_issuers(df: pd.DataFrame) -> list[str]:
    """Issuers with at least MIN_SPREAD_QUARTERS quarters with an eligible tranche (own series)."""
    e = eligible_spread(df)
    quarters = e.assign(q=pd.PeriodIndex(pd.to_datetime(e["pricing_date"]), freq="Q-DEC").astype(str)).groupby(
        "company")["q"].nunique()
    return [c for c in COMPANIES if quarters.get(c, 0) >= MIN_SPREAD_QUARTERS]


def issuers(df: pd.DataFrame) -> list[str]:
    return [c for c in COMPANIES if ((df["company"] == c) & (df["currency"] == "USD")).any()]


# ------------------------------------------------------------------ reconciliation against XBRL (report)


# Oracle's fiscal quarters (Jun-Aug, Sep-Nov, Dec-Feb, Mar-May) by month -> (calendar quarter of the midpoint, year
# offset): Jun-Aug -> Q3, Sep-Nov -> Q4, Dec -> Q1 of the next year, Jan-Feb -> Q1, Mar-May -> Q2.
ORACLE_QUARTER = {6: (3, 0), 7: (3, 0), 8: (3, 0), 9: (4, 0), 10: (4, 0), 11: (4, 0), 12: (1, 1), 1: (1, 0),
                  2: (1, 0), 3: (2, 0), 4: (2, 0), 5: (2, 0)}


def fiscal_calendar_quarter(company: str, day: str) -> str:
    """Calendar quarter (midpoint rule, docs/kallor/sec.md) of the company's fiscal quarter that contains `day`.
    Only Oracle's fiscal quarters differ from calendar quarters among the six issuers."""
    t = pd.Timestamp(day)
    if company == "orcl":
        q, dy = ORACLE_QUARTER[t.month]
        return f"{t.year + dy}Q{q}"
    return str(t.to_period("Q-DEC"))


COVERAGE_COLUMNS = ["company", "year", "quarter", "term_sheets", "xbrl", "xbrl_quarters", "share", "later"]


def coverage(df: pd.DataFrame, debt_issued: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Per company and calendar year, and per quarter with issuance: USD principal by settlement quarter (the company's
    fiscal quarter, midpoint rule) against XBRL debt_issued (latest vintage) over the quarters XBRL has.

    debt_issued: company -> frame (period, value). Columns: company, year, quarter ("" on the year row, then one row per
    quarter of the year with USD principal), term_sheets (USD principal in the quarters XBRL has), xbrl, xbrl_quarters,
    share = term_sheets / xbrl, later = USD principal in quarters XBRL does not have yet (not in the share)."""
    out = []
    usd = df[df["currency"] == "USD"]
    for co, xb in debt_issued.items():
        own = usd[usd["company"] == co]
        q = [fiscal_calendar_quarter(co, s or p) for s, p in zip(own["settlement_date"], own["pricing_date"])]
        ts = own.assign(q=q).groupby("q")["principal"].sum() if len(own) else pd.Series(dtype=float)
        x = xb.set_index("period")["value"] if len(xb) else pd.Series(dtype=float)
        years = sorted({p[:4] for p in ts.index} | {p[:4] for p in x.index if p[:4] >= "2020"})
        for y in years:
            xq = [p for p in x.index if p.startswith(y)]
            t = float(sum(v for p, v in ts.items() if p.startswith(y) and p in xq))
            later = float(sum(v for p, v in ts.items() if p.startswith(y) and p not in xq))
            v = float(x[xq].sum()) if xq else float("nan")
            out.append((co, y, "", t, v, len(xq), t / v if v else float("nan"), later))
            for p in sorted(p for p, s in ts.items() if p.startswith(y) and s > 0):
                if p in xq:
                    xv = float(x[p])
                    out.append((co, y, p, float(ts[p]), xv, 1, float(ts[p]) / xv if xv else float("nan"), 0.0))
                else:
                    out.append((co, y, p, 0.0, float("nan"), 0, float("nan"), float(ts[p])))
    return pd.DataFrame(out, columns=COVERAGE_COLUMNS)


def _xbrl_latest(key: str) -> pd.DataFrame:
    """Latest vintage of an XBRL catalog series from the observation table (period as str, value)."""
    from ai_tracker import observations

    v = observations.as_of(key, pd.Timestamp.today())
    return pd.DataFrame({"period": v.index.astype(str), "value": v.values})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "coverage"])
    a = ap.parse_args()
    if a.cmd == "build":
        docs = json.loads((cc.CORPUS_DIR / "documents.json").read_text())
        rows, skipped = rows_from_documents(docs)
        for s in skipped:
            if s["form"] == "FWP" or s.get("hand"):
                print(f"not coded: {s['form']} {s['company']} {s['filed']} {s['accession']}: {s['why']}")
        reasons: dict[tuple[str, str], int] = {}
        for s in skipped:
            key = (s["form"], re.sub(r" 0\d{9}-\d{2}-\d{6}$", "", s["why"]))
            reasons[key] = reasons.get(key, 0) + 1
        for (form, why), n in sorted(reasons.items()):
            print(f"{n:4d} {form:6s} {why}")
        hand = [s for s in skipped if s.get("hand")]
        if hand:
            raise SystemExit(f"{len(hand)} final supplements without a term sheet must be coded by hand (MANUAL); "
                             "nothing written")
        for src in sorted({(r["form"], r["accession"]) for r in rows if r["form"] != "FWP"}):
            print(f"coded from the final supplement (no term sheet), read it: {src[0]} {src[1]}")
        write(rows)
        write_skipped(skipped)
        print(f"{len(rows)} rows written to {PATH}, {len(skipped)} documents not coded in {SKIPPED_PATH}")
        load()
    else:
        df = load()
        res = coverage(df, {c: _xbrl_latest(f"debt_issued_{c}") for c in COMPANIES})
        fmt = {"float_format": lambda x: f"{x:,.2f}", "index": False}
        print(res[res["quarter"] == ""].drop(columns="quarter").to_string(**fmt))
        print()
        print(res[res["quarter"] != ""].drop(columns=["year", "xbrl_quarters"]).to_string(**fmt))


if __name__ == "__main__":
    main()
