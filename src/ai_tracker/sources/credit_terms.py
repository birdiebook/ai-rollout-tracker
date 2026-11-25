"""Deterministic parser for EDGAR pricing term sheets (track KR1): one dict per tranche.

Input is the line list of credit_issuance_corpus.lines(). Two layouts occur in the corpus (2020-2026):

- keyed: one table for all tranches; each field's value lists the tranches by key ("2030 Notes: $1,000,000,000
  2035 Notes: ..."), and a field can continue on the next lines (rows without a label cell). Amazon, Alphabet, Meta,
  Microsoft.
- sections: a heading per tranche ("4.450% Notes due 2030 ("2030 Notes")") followed by its own label | value rows.
  Oracle.

A third layout (tranches as table columns) is handled for safety: a principal field with several money cells.

Every value is read as stated (docs/kallor/kredit_emission.md, "Tal"): amounts in millions of the currency, rates
and prices in percent, spreads in basis points. Nothing is computed except tenor_years and a settlement date stated
only as T+n. The parser marks what it could not read (None); the agent reads every document and codes by hand
where the parser fails (method "manual").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|December")
DATE_RE = re.compile(rf"\b({MONTHS})\s+(\d{{1,2}})\s*,\s*(\d{{4}})")
PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s?%")
MONEY_RE = re.compile(r"(US\$|C\$|A\$|NZ\$|\$|€|£|¥|CHF\s?|EUR\s?)\s?(\d[\d,]*(?:\.\d+)?)(?:\s*(billion|million))?",
                      re.I)
CURRENCY = {"$": "USD", "US$": "USD", "C$": "CAD", "A$": "AUD", "NZ$": "NZD", "€": "EUR", "EUR": "EUR", "£": "GBP",
            "¥": "JPY", "CHF": "CHF"}
FLOAT_RE = re.compile(r"(?i)\bSOFR\b|EURIBOR|SONIA|CORRA|floating\s+rate")
KEY_RE = re.compile(r"(?<![\w-])((?:\d{4})(?:\s+[A-Z][A-Za-z-]*)*\s+Notes)\s*:?(?=\s)")
HEADING_RE = re.compile(r"^(?:\d+\.\d+\s?%\s+(?:[A-Z][\w-]*\s+)*Notes\s+due\s+\d{4}|Floating\s+Rate\s+Notes\s+due\s+\d{4})"
                        r"(?:\s*\(.*\))?$")
CONTINUATION_RE = re.compile(r"^\S.{0,60}?\bNotes?\s*:")
PAGE_RE = re.compile(r"^\d{1,3}$|^-\s*\d{1,3}\s*-$")

# label -> field name, first match wins; (pattern, exclude) on the lower-cased label
LABELS: list[tuple[str, str, str]] = [
    ("benchmark_yield", r"benchmark.*yield|treasury.*yield", r"$^"),
    ("benchmark", r"^benchmark", r"price|spread"),
    ("spread_ms", r"spread.*mid-?\s?swap", r"$^"),
    ("mid_swap", r"mid-?\s?swap", r"$^"),
    ("spread", r"spread", r"sofr|floating|swap"),
    ("yield", r"yield", r"$^"),
    ("price", r"price to (?:the )?public|public offering price|issue price|re-?offer price|offering price|"
              r"initial price", r"$^"),
    ("principal", r"principal amount|^size\b|^amount\b|^aggregate (?:nominal|principal)", r"proceeds|discount|denom"),
    ("maturity", r"maturity", r"par call|call date|yield"),
    ("coupon", r"^coupon|^interest rate|coupon \(interest", r"payment|determination|period|reset|record|basis"),
    ("trade", r"trade date|pricing date", r"$^"),
    ("settle", r"^settlement(?: date)?\b", r"trading|clearing|system"),
]
USED = ("principal", "maturity", "coupon", "price", "yield", "spread", "spread_ms", "benchmark", "benchmark_yield",
        "trade", "settle")


@dataclass
class Field:
    name: str | None
    label: str
    cells: list[str]
    a: int
    b: int

    @property
    def value(self) -> str:
        return " ".join(self.cells)


@dataclass
class Tranche:
    key: str
    col: int | None
    values: dict[str, str] = field(default_factory=dict)  # field name -> the tranche's text
    lines: set[int] = field(default_factory=set)
    heading: int | None = None


def field_name(label: str) -> str | None:
    lab = label.lower().strip(" :*")
    for name, pat, excl in LABELS:
        if re.search(pat, lab) and not re.search(excl, lab):
            return name
    return None


def fields(doc_lines: list[str]) -> list[Field]:
    """label | value rows with their continuation lines (rows that start with a tranche key)."""
    out: list[Field] = []
    cur: Field | None = None
    for i, line in enumerate(doc_lines):
        if " | " in line:
            label, *cells = line.split(" | ")
            cur = Field(field_name(label), label, cells, i, i)
            out.append(cur)
        elif PAGE_RE.match(line):
            continue
        elif cur is not None and CONTINUATION_RE.match(line) and not HEADING_RE.match(line):
            cur.cells = [cur.value + " " + line]
            cur.b = i
        else:
            cur = None
    return out


# ------------------------------------------------------------------ values


def to_date(s: str | None) -> str | None:
    m = DATE_RE.search(s or "")
    if not m:
        return None
    return pd.Timestamp(f"{m.group(1)} {m.group(2)} {m.group(3)}").strftime("%Y-%m-%d")


def first_pct(s: str | None) -> float | None:
    m = PCT_RE.search(s or "")
    return float(m.group(1)) if m else None


def last_pct(s: str | None) -> float | None:
    m = PCT_RE.findall(s or "")
    return float(m[-1]) if m else None


def money(s: str | None) -> tuple[str, float] | None:
    """(currency, amount in millions) of the first amount in s."""
    m = MONEY_RE.search(s or "")
    if not m:
        return None
    cur = CURRENCY[m.group(1).strip().upper() if m.group(1).strip().upper() in CURRENCY else m.group(1).strip()]
    x = float(m.group(2).replace(",", ""))
    unit = (m.group(3) or "").lower()
    return cur, x * 1000 if unit == "billion" else x if unit == "million" else x / 1e6


def spread_bp(s: str | None) -> float | None:
    """Spread as stated: 'T + 45 bps', '+45 basis points', '0.250% (+25 basis points)', '+0.45%' (-> 45)."""
    s = s or ""
    for pat, scale in ((r"T\s*\+\s*(\d+(?:\.\d+)?)", 1), (r"\+\s*(\d+(?:\.\d+)?)\s*(?:bps|bp|basis\s+points)\b", 1),
                       (r"(\d+(?:\.\d+)?)\s*(?:bps|bp|basis\s+points)\b", 1), (r"\+?\s*(\d+\.\d+)\s?%", 100)):
        m = re.search(pat, s, re.I)
        if m:
            return round(float(m.group(1)) * scale, 4)
    return None


def frn_spread_bp(s: str | None) -> float | None:
    """The margin over the floating index: 'plus 53 basis points', 'plus 0.52% per annum' (-> 52)."""
    m = re.search(r"(?i)(?:plus|\+)\s*(\d+(?:\.\d+)?)\s*(?:bps|bp|basis\s+points)", s or "")
    if m:
        return float(m.group(1))
    m = re.search(r"(?i)(?:plus|\+)\s*(\d+\.\d+)\s?%", s or "")
    return round(float(m.group(1)) * 100, 4) if m else None


def t_plus(s: str | None) -> int | None:
    m = re.search(r"T\s*\+\s*(\d+)", s or "")
    return int(m.group(1)) if m else None


def add_business_days(day: str, n: int) -> str:
    return (pd.Timestamp(day) + pd.offsets.BDay(n)).strftime("%Y-%m-%d")


def tenor_years(pricing_date: str, maturity: str) -> float:
    return round((pd.Timestamp(maturity) - pd.Timestamp(pricing_date)).days / 365.25, 2)


# ------------------------------------------------------------------ layouts


def _split_keyed(value: str, keys: list[str]) -> dict[str, str]:
    """key -> its text in a keyed value ('2030 Notes: x 2035 Notes: y'); longest keys first so that '2028 Notes' does
    not match inside '2028 Floating Rate Notes'."""
    spans = []
    taken: list[tuple[int, int]] = []
    for k in sorted(keys, key=len, reverse=True):
        for m in re.finditer(rf"(?<![\w-]){re.escape(k)}\s*:?", value):
            if not any(m.start() < e and s < m.end() for s, e in taken):
                spans.append((m.start(), m.end(), k))
                taken.append((m.start(), m.end()))
                break
    spans.sort()
    out = {}
    for i, (s, e, k) in enumerate(spans):
        out[k] = value[e:spans[i + 1][0] if i + 1 < len(spans) else len(value)].strip()
    return out


def keys_of(fs: list[Field]) -> list[str]:
    """Tranche keys in order, from every principal field that lists them (a term sheet can have one block for the
    floating and one for the fixed rate notes)."""
    ks: list[str] = []
    for f in fs:
        if f.name == "principal":
            ks += [m.group(1) for m in KEY_RE.finditer(f.value)]
    return list(dict.fromkeys(ks))


def starts_with_key(value: str, keys: list[str]) -> bool:
    """A keyed value begins with a tranche key; other values only mention one ("the 2028 Notes")."""
    v = value.lstrip()
    return any(v.startswith(k) for k in keys)


SECTION_TITLE_RE = re.compile(r"^(?:Fixed|Floating)\s+Rate\s+Notes$")


def _general(fs: list[Field], t: Tranche) -> None:
    """Fields without tranche keys (one trade date for the whole offering) apply to every tranche."""
    for f in fs:
        if f.name in ("trade", "settle") and f.name not in t.values:
            t.values[f.name] = f.value
            t.lines.update(range(f.a, f.b + 1))


def tranches(doc_lines: list[str]) -> tuple[str, list[Tranche]]:
    """(layout, tranches in document order). Keyed fields are split by key; a principal field without keys is a
    section of its own (from its heading to the next heading, section title or principal field)."""
    fs = fields(doc_lines)
    keys = keys_of(fs)
    principal = [f for f in fs if f.name == "principal"]
    keyed: list[Tranche] = [Tranche(k, j) for j, k in enumerate(keys)]
    for f in fs:
        if f.name in USED and keys and starts_with_key(f.value, keys):
            parts = _split_keyed(f.value, keys)
            for t in keyed:
                if t.key in parts and f.name not in t.values:
                    t.values[f.name] = parts[t.key]
                    t.lines.update(range(f.a, f.b + 1))
    order: list[tuple[int, int, Tranche]] = []
    for t in keyed:
        first = min((f.a for f in principal if t.key in _split_keyed(f.value, keys)), default=0)
        order.append((first, t.col or 0, t))
    columns = [f for f in principal if not (keys and starts_with_key(f.value, keys))
               and len([c for c in f.cells if money(c)]) > 1]
    unkeyed = [f for f in principal if not (keys and starts_with_key(f.value, keys)) and f not in columns
               and money(f.value)]
    heads = [i for i, line in enumerate(doc_lines) if HEADING_RE.match(line)]
    stops = sorted(set(heads) | {i for i, line in enumerate(doc_lines) if SECTION_TITLE_RE.match(line)}
                   | {g.a for g in principal})
    for n, f in enumerate(unkeyed):
        prev = max([g.a for g in principal if g.a < f.a] or [-1])
        h = max([i for i in heads if prev < i < f.a] or [None], key=lambda x: -1 if x is None else x)
        start = h if h is not None else f.a
        end = min([x for x in stops if x > f.a] or [len(doc_lines)])
        t = Tranche(doc_lines[h] if h is not None else f"section {f.a}", None, heading=h)
        if h is not None:
            t.lines.add(h)
        for g in fs:
            if start <= g.a < end and g.name in USED and g.name not in t.values:
                t.values[g.name] = g.value
                t.lines.update(range(g.a, g.b + 1))
        order.append((f.a, 0, t))
    for f in columns:
        n = len([c for c in f.cells if money(c)])
        cols = [Tranche(f"col{j}", j) for j in range(n)]
        for g in fs:
            if g.name in USED and len(g.cells) == n:
                for j, t in enumerate(cols):
                    t.values.setdefault(g.name, g.cells[j])
                    t.lines.update(range(g.a, g.b + 1))
        order += [(f.a, j, t) for j, t in enumerate(cols)]
    out = [t for _, _, t in sorted(order, key=lambda x: (x[0], x[1]))]
    for t in out:
        _general(fs, t)
    kinds = [k for k, on in (("keyed", keyed), ("sections", unkeyed), ("columns", columns)) if on]
    return "+".join(kinds) or "none", out


def header_date(doc_lines: list[str]) -> str | None:
    for line in doc_lines[:20]:
        d = to_date(line)
        if d:
            return d
    return None


def security_name(doc_lines: list[str], t: Tranche, coupon: float | None, maturity: str | None) -> str:
    if t.heading is not None:
        return re.sub(r"\s*\(.*\)$", "", doc_lines[t.heading]).strip()
    year = maturity[:4] if maturity else None
    for line in doc_lines[:40]:
        m = re.search(rf"((?:\d+\.\d+\s?%\s+)?(?:[A-Z][\w-]*\s+)*Notes\s+due\s+{year})\s*\(the\s*[“\"]"
                      rf"{re.escape(t.key)}[”\"]", line) if year else None
        if m:
            return m.group(1)
    for line in doc_lines[:40]:
        if year and re.search(rf"Notes\s+due\s+{year}\b", line) and " | " not in line:
            is_float = "Floating" in t.key
            if ("Floating" in line) == is_float and (coupon is None or f"{coupon:.3f}" in line or f"{coupon}" in line):
                return re.sub(r"^\S*\d[\d,]*\s+", "", line).strip()
    return f"{t.key}"


def parse(doc_lines: list[str], filed: str) -> tuple[str, list[dict]]:
    """(layout, one dict per tranche) with every value as stated; None where the parser found nothing."""
    kind, ts = tranches(doc_lines)
    hdate = header_date(doc_lines)
    rows = []
    shared = None
    shared_ts = [t for t in ts if t.heading is None and t.lines]
    if shared_ts:
        used = set().union(*(t.lines for t in shared_ts))
        shared = (min(used), max(used))
    for t in ts:
        v = t.values
        m = money(v.get("principal"))
        coupon_text = v.get("coupon")
        floating = bool(FLOAT_RE.search(coupon_text or "")) and not re.match(r"\s*\d+(?:\.\d+)?\s?%", coupon_text or "")
        floating = floating or "Floating" in t.key
        pricing = to_date(v.get("trade")) or hdate or filed
        maturity = to_date(v.get("maturity"))
        settle_text = v.get("settle")
        settle = to_date(settle_text)
        settle_note = ""
        if settle is None and t_plus(settle_text) is not None:
            settle = add_business_days(pricing, t_plus(settle_text))
            settle_note = "settlement_date computed from T+n"
        coupon = None if floating else first_pct(coupon_text)
        currency = m[0] if m else None
        spread_label = "spread_ms" if currency not in (None, "USD") and v.get("spread_ms") else "spread"
        if floating:
            sp, btype, bench = frn_spread_bp(coupon_text) or spread_bp(v.get("spread")), "sofr", "Compounded SOFR"
            if currency not in (None, "USD"):
                btype, bench = "other", (re.search(r"(?i)EURIBOR|SONIA|CORRA|SOFR", coupon_text or "") or [None])[0]
        else:
            sp = spread_bp(v.get(spread_label))
            if currency == "USD":
                btype = "treasury" if v.get("benchmark") or re.search(r"(?i)treasury", v.get("spread") or "") else \
                    "other"
            else:
                btype = "mid_swaps" if spread_label == "spread_ms" else "other"
            bench = (v.get("benchmark") or "").strip()[:80] or None
            if spread_label == "spread_ms":
                bench = "mid-swaps"
        a, b = shared if shared and t.heading is None else (min(t.lines), max(t.lines))
        rows.append({
            "key": t.key, "col": t.col, "layout": kind,
            "currency": currency, "rate_type": "floating" if floating else "fixed",
            "security": security_name(doc_lines, t, coupon, maturity),
            "principal": m[1] if m else None,
            "pricing_date": pricing, "pricing_from": "trade" if to_date(v.get("trade")) else
            ("header" if hdate else "filed"),
            "settlement_date": settle, "maturity": maturity,
            "tenor_years": tenor_years(pricing, maturity) if maturity else None,
            "coupon_pct": coupon,
            "benchmark": bench, "benchmark_type": btype,
            "benchmark_yield_pct": None if floating or spread_label == "spread_ms" else last_pct(v.get("benchmark_yield")),
            "spread_bp": sp,
            "yield_pct": None if floating else first_pct(v.get("yield")),
            "price_pct": first_pct(v.get("price")),
            "a": a, "b": b, "note": settle_note,
        })
    return kind, rows
