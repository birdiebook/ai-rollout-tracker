"""Commercial-use class per series: "ja", "nej" or "okänd" (decision point 3 in docs/riktning.md, 2026-11-24).

The public site stays non-commercial, and `Spec.publish` alone decides what it shows. Orthogonal to that, every series
gets a class for commercial use, so that a commercially clean subset can always be computed. publish=True with class
"nej" is allowed (Cloudflare Radar, CC BY-NC, on the non-commercial site).

    ja     the documented licence or terms allow commercial use and redistribution: public domain (US government works,
           the Fed Board, EIA), CC0, CC BY 4.0, MIT, SEC public information, and figures we extracted ourselves from
           filings on sec.gov (10-K, 10-Q, 8-K, 6-K, S-1)
    nej    the documented terms forbid it: CC BY-NC, PJM's ban on republishing by non-members
    okänd  no licence found, terms not readable or not assessed, as the docs say. A class is never guessed.

`verdict(spec)` decides in this order:
1. KEY_OVERRIDES (series key -> class, reason): final.
2. SOURCE_OVERRIDES: regexes on Spec.source, for cases where the licence string alone says too much (a copy taken
   from FRED or ALFRED, LMArena's Space files).
3. Curated files: a series whose source names curated/<file>.csv gets the curated rule on the rows it reads: "ja" when
   every one of them has its source_url on sec.gov, otherwise "okänd" (company web pages such as microsoft.com have no
   documented terms). The rows are the series' own (ROW_SERIES), else its company's ("Kurerad extraktion
   (curated/<file>.csv)", the company is the key token that is a company in the file), else those declared in
   CURATED_READS. A series that names a curated file without any of these is "okänd", and catalog.validate() reports
   it. Only identifying columns (company, lab, scope, measure, definition) and source_url are read, never values.
4. RULES: ordered regexes on Spec.license, the first match wins. A "derived: a + b" licence is classified part by part.
   A series with a curated rule takes the most restrictive of that rule and its licence.
Derived series (Spec.components, and the *_hyp4 sums with the member companies named in their label) then take the most
restrictive class of their own licence and their components: "ja" only if all are "ja", and "nej" before "okänd".

A licence that nothing classifies raises Unclassified, and catalog.validate() reports it, so a new series cannot be
added without a class. A key override with a class other than ja, nej or okänd raises Unclassified as well.

    python -m ai_tracker.licenses report [--markdown]

Doc: docs/datakallor/licensniva.md.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

from ai_tracker import catalog, config

JA, NEJ, OKAND = "ja", "nej", "okänd"
CLASSES = (JA, NEJ, OKAND)
RANK = {JA: 0, OKAND: 1, NEJ: 2}  # higher = more restrictive; a derived series takes the highest


class Unclassified(ValueError):
    """No rule or override classifies the licence of a series."""


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: str  # regex, searched (re.search) in the licence text, or in Spec.source for SOURCE_OVERRIDES
    klass: str
    reason: str  # Swedish, shown in the report and the doc
    flags: int = re.IGNORECASE

    def matches(self, text: str) -> bool:
        return re.search(self.pattern, text or "", self.flags) is not None


@dataclass(frozen=True)
class Verdict:
    klass: str
    reason: str
    rule: str  # what decided: a rule or override name, "curated", "derived-licence" or "derived"
    scope: str = ""  # the part the reason applies to (the company of a curated series); grouped in the report

    @property
    def full_reason(self) -> str:
        return f"{self.reason} (bolag: {self.scope})" if self.scope else self.reason


# ------------------------------------------------------------------ rules on the licence text (first match wins)
# Restrictive and "not assessed" rules come before the permissive ones: a string that says both "CC-BY-4.0" and
# "Not checked for publication" (GH Archive) is okänd.
RULES: list[Rule] = [
    Rule("unverified", r"\bunverified\b", OKAND,
         "licensen är inte verifierad: villkoren saknas eller kunde inte läsas"),
    Rule("cc-by-nc", r"\bCC[ -]?BY-NC\b", NEJ, "CC BY-NC: kommersiell användning är inte tillåten"),
    Rule("pjm-republish", r"non-?members are specifically prohibited from republishing", NEJ,
         "PJM:s villkor: icke-medlemmar får inte vidarepublicera data"),
    Rule("no-open-licence",
         r"no open licen[cs]e|no (?:data )?licen[cs]e stated|redistribution not checked|not checked for publication"
         r"|ej kontrollerad för publicering", OKAND,
         "ingen öppen licens, eller vidarespridning inte kontrollerad"),
    # R10-3: wording that limits or hedges a permissive token ("CC BY 4.0 for the docs; data non-commercial") is never
    # ja. Not nej: which part the limit covers is not parsed, so the class is not assessed.
    Rule("restrictive-wording",
         r"non-?commercial|all rights reserved|proprietary|third[- ]party rights|may be (?:under|subject to) copyright"
         r"|not in the public domain|not verified|personal use only|prohibit|not (?:permitted|allowed)"
         r"|does not (?:apply|cover)|\bunclear\b", OKAND,
         "texten begränsar eller reserverar användningen (icke-kommersiell, förbud, upphovsrätt, tredje parts "
         "rättigheter, oklar eller inte verifierad status); kommersiell användning är inte bedömd"),
    Rule("cc0", r"\bCC0\b", JA, "CC0: fri användning, även kommersiell"),
    Rule("cc-by", r"\bCC[ -]BY[ -]4\.0\b|Creative Commons Attribution 4\.0", JA,
         "CC BY 4.0: kommersiell användning tillåten med källhänvisning"),
    # MIT as the licence ("MIT (LICENSE ...)", "MIT License", "MIT,", "Licence: MIT"), not as a name (R10-3: "MIT
    # Technology Review"). Case-sensitive, so "submit" never matches.
    Rule("mit", r"(?<![\w-])MIT(?=[ -]?\(?(?i:licen[cs]e)|[,)])|(?i:licen[cs]e)\s*:\s*MIT\b", JA,
         "MIT: kommersiell användning tillåten med licenstexten", flags=0),
    Rule("public-domain", r"17 U\.S\.C\. § ?105|\bpublic domain\b", JA,
         "public domain (amerikansk myndighet): fri användning med källhänvisning"),
    Rule("sec", r"sec\.gov/privacy", JA,
         "SEC: offentlig information som får kopieras och spridas vidare; egna siffror ur inlämnade dokument"),
]

# ------------------------------------------------------------------ overrides
ARENA_SPACE_REASON = ("datasetet är CC BY 4.0, men Space-filerna (belägg och kompletta tabeller) har ingen "
                      "dokumenterad licens, och Arenas webbvillkor kunde inte läsas")

# By series key: (class, reason). Final, also for derived series. Prefer these to free-text source patterns (R10-11).
KEY_OVERRIDES: dict[str, tuple[str, str]] = {
    # R10-2: the price series read arena.subset_boards("text"), which is built from the Space files (and adds the
    # Space-only boards of 2025-08-15/22/29), so they rest on the same files as g1_arena_text_*. Their source text does
    # not name the Space files, so the arena-space source override does not see them.
    **{k: (OKAND, f"tavlorna kommer från LMArenas Space-filer (arena.subset_boards(\"text\")): {ARENA_SPACE_REASON}")
       for k in ("g2_price_at_arena_capability", "g2_price_at_arena_capability_4o")},
}

# By source (regex on Spec.source), before the licence rules.
SOURCE_OVERRIDES: list[Rule] = [
    # R10-4: also a direct FRED copy (fredgraph.csv, fred.stlouisfed.org), not only ALFRED. The acronyms are
    # case-sensitive, so a word such as "Alfred" does not match.
    Rule("alfred", r"\b(?:AL)?FRED\b|(?i:stlouisfed\.org)", OKAND,
         "kopian kommer från FRED eller ALFRED, vars villkor förbjuder användning i samband med maskininlärning; "
         "kommersiell användning är inte bedömd (primärkällan vore ja)", flags=0),
    Rule("arena-space", r"LMArena \(HF-dataset \+ Space-filer\)", OKAND, ARENA_SPACE_REASON),
]

# Curated files (step 3 of the module doc).
CURATED = re.compile(r"^Kurerad extraktion \(curated/([\w.-]+\.csv)\)")
CURATED_FILE = re.compile(r"\bcurated/([\w.-]+\.csv)")  # any mention of a curated file in Spec.source
SEC_HOSTS = frozenset({"www.sec.gov", "sec.gov"})
CURATED_REASON_JA = "egen extraktion ur dokument på sec.gov"
CURATED_REASON_OKAND = "egen extraktion, men ur bolagets egna sidor utan dokumenterade villkor"
UNDECLARED_REASON = ("källan nämner curated/{name}, men det är inte angivet vilka rader serien läser (lägg till den i "
                     "CURATED_READS eller ROW_SERIES)")


def _kpi_key(row: dict) -> str | None:
    from ai_tracker.sources import ai_kpis  # late: keep this module light to import

    return ai_kpis.series_key(row["definition"]) if row.get("definition") else None


def _lab_revenue_key(row: dict) -> str | None:
    # series/lab_revenue.py: one series per (lab, scope, measure). If that key changes, no row maps to the series, it
    # becomes undeclared (okänd) and catalog.validate reports it.
    lab, scope, measure = (row.get(c) or "" for c in ("lab", "scope", "measure"))
    return f"lab_rev_{lab}_{scope}_{measure.lower()}" if lab and scope and measure else None


# File -> function(row) -> the series key the row feeds. With a mapping the rule follows the series' own rows, not every
# row of its company (R10-6). Files without one, and series no row maps to, fall back to the company.
ROW_SERIES = {"ai_kpis.csv": _kpi_key, "lab_revenue.csv": _lab_revenue_key}

# R10-1: series whose Spec.source names a curated file without being a curated extraction of it, and that no row maps
# to: whose rows they read. None = every row of the file (pooled over companies), () = no row (the file is only named).
# The curated rule is applied to those rows.
CURATED_READS: dict[str, tuple[str, tuple[str, ...] | None]] = {
    # F1 (series/guidance_revisions.py, track F1): capex_statements reads every row of the file, Microsoft's too
    **{k: ("guidance_capex.csv", None) for k in ("f1_rev_index_4q", "f1_rev_index_q", "f1_rev_n_4q", "f1_rev_n_q",
                                                 "f1_rev_median_4q", "f1_rev_median_q")},
    # the surprises of Meta and Alphabet use their own capex guidance; TSMC's and Nvidia's come from SEC series
    "f1_surprise_meta_capex": ("guidance_capex.csv", ("meta",)),
    "f1_surprise_googl_capex": ("guidance_capex.csv", ("googl",)),
    "f1_surprise_index": ("guidance_capex.csv", ("meta", "googl")),
    "f1_surprise_index_n": ("guidance_capex.csv", ("meta", "googl")),
    "f1_surprise_tsmc": ("guidance_capex.csv", ()),
    # X8 (R11-7): the US$ sensitivity reads tsmc_rev_usd_q and TSMC's US$ guidance (both SEC 6-K), no row of the file
    "f1_surprise_tsmc_usd": ("guidance_capex.csv", ()),
    "f1_surprise_nvda": ("guidance_capex.csv", ()),
}

# Members of a *_hyp4 sum, as the label names them ("..., MSFT+GOOGL+AMZN+META").
MEMBERS = re.compile(r"\b([A-Z]{2,5}(?:\+[A-Z]{2,5})+)\s*$")


Row = tuple  # (company, source_url host, series key or None) of one curated row


@lru_cache(maxsize=None)
def _curated_rows(path: str, mtime: float) -> tuple[Row, ...]:
    """(company or lab, host of source_url, series key by ROW_SERIES) per row; mtime is part of the cache key. Only
    identifying columns are read, never values."""
    to_key = ROW_SERIES.get(path.replace("\\", "/").rsplit("/", 1)[-1])
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            company = (row.get("company") or row.get("lab") or "").strip().lower()
            host = urlparse((row.get("source_url") or "").strip()).netloc.lower()
            out.append((company, host, to_key(row) if to_key else None))
    return tuple(out)


def _rows_verdict(rows: list[Row], name: str, whose: str, scope: str, rule: str) -> Verdict:
    """ja when every row is on sec.gov, else okänd; `whose` names the rows in the reason ("seriens", "bolagets",
    "bolagens", "filens")."""
    hosts = {h for _, h, _ in rows}
    other = sorted(h or "rader utan källadress" for h in hosts - SEC_HOSTS)
    if rows and not other:
        return Verdict(JA, f"{CURATED_REASON_JA}: {whose} alla rader i curated/{name} kommer från sec.gov", rule, scope)
    if not rows:
        return Verdict(OKAND, f"curated/{name} har inga rader för serien, så raderna kan inte kontrolleras", rule,
                       scope)
    also = "också " if hosts & SEC_HOSTS else ""
    return Verdict(OKAND, f"{CURATED_REASON_OKAND}: {whose} rader i curated/{name} kommer {also}från "
                          f"{', '.join(other)}, och bara sec.gov är kontrollerad", rule, scope)


def _file_verdict(spec: catalog.Spec, name: str) -> Verdict | None:
    """The curated rule for one file named in Spec.source (module doc, step 3); None when the series reads no row."""
    m = CURATED.match(spec.source or "")
    extraction = m is not None and m.group(1) == name
    declared = CURATED_READS.get(spec.key)
    declared = declared if declared is not None and declared[0] == name else None
    if declared is not None and declared[1] == ():
        return None
    undeclared = Verdict(OKAND, UNDECLARED_REASON.format(name=name), "curated-undeclared")
    path = config.REPO / "curated" / name
    if not path.exists():
        if not extraction and declared is None:
            return undeclared
        return Verdict(OKAND, f"kurerad extraktion: curated/{name} saknas, så raderna kan inte kontrolleras", "curated")
    rows = _curated_rows(str(path), path.stat().st_mtime)
    own = [r for r in rows if r[2] == spec.key]
    if own:
        return _rows_verdict(own, name, "seriens", "/".join(sorted({c for c, _, _ in own})), "curated")
    if extraction:
        tokens = set(spec.key.lower().split("_"))
        companies = sorted({c for c, _, _ in rows if c and c in tokens})
        chosen = [r for r in rows if r[0] in companies] if companies else list(rows)
        return _rows_verdict(chosen, name, "bolagets" if companies else "filens", "/".join(companies) or "alla bolag",
                             "curated")
    if declared is not None:
        companies = declared[1]
        if companies is None:
            return _rows_verdict(list(rows), name, "filens", "alla bolag", "curated-reads")
        chosen = [r for r in rows if r[0] in companies]
        return _rows_verdict(chosen, name, "bolagets" if len(companies) == 1 else "bolagens",
                             "/".join(sorted(companies)), "curated-reads")
    return undeclared


def curated_verdict(spec: catalog.Spec) -> Verdict | None:
    """The curated rule (see module doc) on every curated file Spec.source names, the most restrictive; None when it
    names none, or the series reads no row of them."""
    names = dict.fromkeys(CURATED_FILE.findall(spec.source or ""))
    return worst(v for v in (_file_verdict(spec, n) for n in names) if v is not None)


def undeclared_curated(spec: catalog.Spec) -> list[str]:
    """Curated files named in Spec.source whose rows the series is not known to read (catalog.validate reports them)."""
    if spec.key in KEY_OVERRIDES:
        return []
    names = dict.fromkeys(CURATED_FILE.findall(spec.source or ""))
    return [n for n in names if (v := _file_verdict(spec, n)) is not None and v.rule == "curated-undeclared"]


def _part_name(text: str) -> str:
    return text.split(" (")[0].strip()


def licence_verdict(text: str) -> Verdict:
    """Class of a licence text by RULES; a "derived: a + b" text takes the most restrictive of its parts."""
    t = (text or "").strip()
    m = re.match(r"derived:\s*", t, re.IGNORECASE)
    if m:
        parts = [p.strip() for p in re.split(r"\s\+\s", t[m.end():]) if p.strip()]
        if not parts:
            raise Unclassified(f"licence not classified: {t[:80]!r} (a derived licence names no parts)")
        verdicts = [licence_verdict(p) for p in parts]
        worst = max(verdicts, key=lambda v: RANK[v.klass])
        listed = ", ".join(f"{_part_name(p)} {v.klass}" for p, v in zip(parts, verdicts))
        tail = "alla delar är ja" if worst.klass == JA else f"den mest restriktiva delen avgör ({worst.reason})"
        return Verdict(worst.klass, f"härledd ur {listed}; {tail}", "derived-licence")
    for rule in RULES:
        if rule.matches(t):
            return Verdict(rule.klass, rule.reason, rule.name)
    raise Unclassified(f"licence not classified: {t[:80]!r} (add a rule or an override in ai_tracker.licenses)")


def own_verdict(spec: catalog.Spec) -> Verdict:
    """The class of the series itself, before its components: source override, else the most restrictive of the
    curated rule and the licence rules (R10-5: a restrictive licence text is never overruled by sec.gov rows)."""
    for rule in SOURCE_OVERRIDES:
        if rule.matches(spec.source):
            return Verdict(rule.klass, rule.reason, rule.name)
    lic = licence_verdict(spec.license)
    cur = curated_verdict(spec)
    if cur is None:
        return lic
    if RANK[lic.klass] > RANK[cur.klass]:
        return Verdict(lic.klass, f"licenstexten avgör, fast raderna i den kurerade filen är {cur.klass}: {lic.reason}",
                       lic.rule)
    return cur


def components(spec: catalog.Spec, keys: dict) -> tuple[str, ...]:
    """Spec.components plus the members of a *_hyp4 sum that are catalog series."""
    comps = list(spec.components)
    m = MEMBERS.search(spec.label or "") if spec.key.endswith("_hyp4") else None
    if m:
        measure = spec.key[: -len("_hyp4")]
        comps += [k for k in (f"{measure}_{t.lower()}" for t in m.group(1).split("+")) if k in keys]
    return tuple(dict.fromkeys(comps))


def verdict(spec: catalog.Spec, specs: dict | None = None, _seen: frozenset = frozenset()) -> Verdict:
    """Commercial-use verdict of one series (see the module doc for the order). Raises Unclassified."""
    if spec.key in KEY_OVERRIDES:
        klass, reason = KEY_OVERRIDES[spec.key]
        if klass not in CLASSES:  # R10-8: a typo ("okand") would break RANK in every series derived from this one
            raise Unclassified(f"key override class {klass!r} is not one of {', '.join(CLASSES)}")
        return Verdict(klass, reason, "key-override")
    keys = catalog.by_key() if specs is None else specs
    own = own_verdict(spec)
    comps = [c for c in components(spec, keys) if c not in _seen and c != spec.key]
    worst, by = own, None
    for c in comps:
        cs = keys.get(c)
        v = (verdict(cs, keys, _seen | {spec.key}) if cs is not None
             else Verdict(OKAND, f"komponenten {c} finns inte i katalogen", "derived"))
        if RANK[v.klass] > RANK[worst.klass]:
            worst, by = v, c
    if by is not None:
        return Verdict(worst.klass, f"härledd: komponenten {by} är {worst.klass} ({worst.full_reason})", "derived")
    if comps and own.klass == JA:
        return Verdict(JA, f"{own.reason}; alla {len(comps)} komponenter är ja", own.rule, own.scope)
    return own


def classify(spec: catalog.Spec, specs: dict | None = None) -> tuple[str, str]:
    """(class, reason) for commercial use: class is "ja", "nej" or "okänd". Raises Unclassified."""
    v = verdict(spec, specs)
    return v.klass, v.full_reason


def worst(verdicts) -> Verdict | None:
    verdicts = list(verdicts)
    return max(verdicts, key=lambda v: RANK[v.klass]) if verdicts else None


def classify_all(specs: list[catalog.Spec] | None = None) -> tuple[dict[str, Verdict], dict[str, str]]:
    """(key -> verdict, key -> error) for a list of specs (default: the catalog)."""
    specs = catalog.ALL if specs is None else specs
    keys = {**catalog.by_key(), **{s.key: s for s in specs}}
    out, errors = {}, {}
    for s in specs:
        try:
            out[s.key] = verdict(s, keys)
        except Unclassified as e:
            errors[s.key] = str(e)
    return out, errors


# ------------------------------------------------------------------ core entries (register section 5)


def entry_keys(entry: str, keys: dict) -> list[str]:
    """Catalog keys behind one expanded core entry: a placeholder gives every matching series, a ratio series of the
    state engine (register.DERIVED) its numerator and denominator."""
    from ai_tracker.state import register as R

    if R.REGIME_PLACEHOLDER in entry:
        prefix = entry.replace(R.REGIME_PLACEHOLDER, "")
        return sorted(k for k in keys if re.fullmatch(re.escape(prefix) + R.REGIME_SUFFIX, k))
    if R.SELECTED_PLACEHOLDER in entry:
        prefix = entry.replace(R.SELECTED_PLACEHOLDER, "")
        return sorted(k for k in keys if k.startswith(prefix))
    if entry in R.DERIVED:
        return list(R.DERIVED[entry][:2])
    return [entry]


def entry_verdict(entry: str, specs: dict | None = None) -> Verdict:
    """The most restrictive verdict of the series behind a core entry; okänd when none is in the catalog."""
    keys = catalog.by_key() if specs is None else specs
    found = [keys[k] for k in entry_keys(entry, keys) if k in keys]
    if not found:
        return Verdict(OKAND, "posten har ingen serie i katalogen", "missing")
    return worst(verdict(s, keys) for s in found)


READINGS = {"register": "registrets familjetabell (register.entry_families)"}


def entry_families(branch: str) -> tuple[dict[str, str], str]:
    """(expanded core entry -> family id, which reading): the register's source families (track K1). K2's provisional
    reading (PROVISIONAL_FAMILIES) was removed after K1 was merged (R10-12); the numbers were identical."""
    from ai_tracker.state import register as R

    return R.entry_families(branch), "register"


def core_summary(specs: dict | None = None) -> list[dict]:
    """Per branch: core entries and source families by class, and what remains if only "ja" counts."""
    from ai_tracker.state import register as R

    keys = catalog.by_key() if specs is None else specs
    rows = []
    for code in catalog.BRANCHES:
        fams, reading = entry_families(code)
        entries = R.core_entries(code)
        verdicts = {e: entry_verdict(e, keys) for e in entries}
        cls = Counter(v.klass for v in verdicts.values())
        families = sorted(set(fams.get(e, e) for e in entries))
        clean = sorted({fams.get(e, e) for e, v in verdicts.items() if v.klass == JA})
        rows.append({"branch": code, "entries": len(entries), **{k: cls.get(k, 0) for k in CLASSES},
                     "families": len(families), "families_ja": len(clean), "reading": reading,
                     "not_ja": {e: v for e, v in verdicts.items() if v.klass != JA}})
    return rows


# ------------------------------------------------------------------ report

# Source groups for the report: (name, regex on Spec.source, doc under docs/ that quotes the licence text).
SOURCE_GROUPS: list[tuple[str, str, str]] = [
    ("SEC EDGAR XBRL, companyfacts", r"^SEC EDGAR XBRL companyfacts", "kallor/sec.md"),
    ("SEC EDGAR XBRL, RPO", r"^SEC EDGAR XBRL instances \(RPO\)", "kallor/rpo.md"),
    ("SEC EDGAR XBRL, segment", r"^SEC EDGAR XBRL instances \(segment", "kallor/sec_segment.md"),
    # Nvidia's purchase commitments, P1's custom concepts (dep_msft, ppe_*_googl) and S1's instance balances share this
    # source text (group renamed in track X14, run 14, after review R17 N-5)
    ("SEC EDGAR XBRL, instanser (åtaganden, RPO och egna taggar)", r"^SEC EDGAR XBRL instances$", "kallor/sec.md"),
    ("Avstämningar A5 (härledda ur SEC)", r"^Härledd \(A5\)", "kallor/avstamning.md"),
    ("SEC EDGAR, TSMC 6-K", r"^SEC EDGAR, TSMC Form 6-K", "kallor/tsmc_asien.md"),
    ("SEC EDGAR, ASML 6-K", r"^SEC EDGAR, ASML Form 6-K", "kallor/halvledare.md"),
    ("SEC EDGAR, Nebius 6-K", r"^SEC EDGAR, Nebius Form 6-K", "kallor/neoclouds.md"),
    ("SEC EDGAR, Nvidias 8-K (guidance)", r"^SEC EDGAR, Nvidia Form 8-K", "kallor/ai_nyckeltal.md"),
    ("SEC EDGAR, Anthropics S-1/A", r"^SEC EDGAR, Anthropic", "kallor/labbintakter.md"),
    ("F1: revideringar och överraskning (härledda)", r"^Härledd \(F1\)", "kallor/guidance.md"),
    ("Kurerad extraktion: AI-nyckeltal", r"curated/ai_kpis\.csv", "kallor/ai_nyckeltal.md"),
    ("Kurerad extraktion: capex-guidance", r"curated/guidance_capex\.csv", "kallor/guidance.md"),
    ("Kurerad extraktion: planer", r"curated/plans\.csv", "kallor/planer.md"),
    ("Kurerad extraktion: leasing som inte har börjat", r"curated/lease_commitments\.csv", "kallor/finansiering.md"),
    ("Kurerad extraktion: nyttjandeperioder", r"curated/useful_lives\.csv", "kallor/nyttjandeperioder.md"),
    ("Anthropics nyhetsrum", r"anthropic\.com/news", "kallor/labbintakter.md"),
    ("BEA NIPA, releasearkivet", r"^BEA NIPA release archive", "kallor/makro_bea_bls.md"),
    ("BEA NIPA", r"^BEA NIPA", "kallor/census_eu.md"),
    ("BLS, flatfiler (KPI och PPI)", r"^BLS flat file", "kallor/makro_bea_bls.md"),
    ("Census, import per HS-kod och land (API)", r"^US Census Bureau API, intltrade", "kallor/census_hs.md"),
    ("Census, årsfil per land och end-use", r"^US Census Bureau, Annual Country by 5-digit End-Use",
     "kallor/census_hs.md"),
    ("Census BTOS", r"\bBTOS\b", "kallor/census_eu.md"),
    ("Census C30", r"Construction Spending \(C30\)", "kallor/census_eu.md"),
    ("Census FT-900", r"FT-900", "kallor/census_eu.md"),
    ("Census M3 via ALFRED", r"^Census M3 via ALFRED", "datakallor/g6_g7_g8.md"),
    ("Fed G.17", r"^Federal Reserve G\.17", "kallor/fed_g17.md"),
    ("EIA Electric Power Monthly", r"^EIA Electric Power Monthly", "kallor/indeed_vast_eia.md"),
    ("EIA-930", r"^EIA-930", "kallor/el_datacenter.md"),
    ("PJM", r"^PJM", "kallor/el_datacenter.md"),
    ("Indeed Hiring Lab", r"^Indeed Hiring Lab", "kallor/indeed_vast_eia.md"),
    ("Eurostat", r"^Eurostat", "kallor/census_eu.md"),
    ("SCB", r"^SCB", "kallor/census_eu.md"),
    ("Epoch AI", r"^Epoch AI", "kallor/epoch_arxiv.md"),
    ("METR", r"^METR", "kallor/epoch_arxiv.md"),
    ("arXiv", r"^arXiv", "kallor/epoch_arxiv.md"),
    ("LMArena, dataset och Space-filer", r"^LMArena \(HF-dataset \+ Space-filer\)", "kallor/g1g2_nya.md"),
    ("LMArena, dataset", r"^LMArena \(HF-dataset\)", "kallor/g1g2_nya.md"),
    ("SWE-bench", r"^SWE-bench", "kallor/g1g2_nya.md"),
    ("AWS Price List", r"^AWS Price List", "kallor/g1g2_nya.md"),
    ("LiteLLM × Epoch AI", r"^LiteLLM git-historik.*× Epoch", "kallor/pris_formaga.md"),
    ("LiteLLM × LMArena", r"^LiteLLM git-historik.*× LMArena", "kallor/g2_arena_pris.md"),
    ("Anthropics prissida × Epoch AI", r"Anthropics prissida", "kallor/priser.md"),
    ("Cloudflare Radar", r"^Cloudflare Radar", "kallor/trafik.md"),
    ("Wikimedia Pageviews", r"^Wikimedia", "kallor/trafik.md"),
    ("npm", r"^npm", "kallor/utvecklaradoption.md"),
    ("PyPI", r"^PyPI", "kallor/utvecklaradoption.md"),
    ("GH Archive", r"^GH Archive", "kallor/github_ai.md"),
    ("Manifold", r"^Manifold", "kallor/forvantningar.md"),
    ("Polymarket", r"^Polymarket", "kallor/forvantningar.md"),
]


def source_group(source: str) -> tuple[str, str]:
    """(group name, doc) of a Spec.source; an unlisted source is its own group without a doc."""
    for name, pattern, doc in SOURCE_GROUPS:
        if re.search(pattern, source or ""):
            return name, doc
    return (source or "").split(",")[0].split(" (")[0].strip() or "(ingen källa)", ""


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _md_table(header: list[str], rows: list[list]) -> list[str]:
    return (["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
            + ["| " + " | ".join(_cell(c) for c in r) + " |" for r in rows])


def source_rows(verdicts: dict[str, Verdict], specs: list[catalog.Spec]) -> list[list]:
    """[group, n, class, rule, reason, doc] per (source group, verdict), most restrictive first. Scopes (companies)
    with the same reason share a row."""
    groups: dict[tuple, int] = Counter()
    scopes: dict[tuple, set[str]] = defaultdict(set)
    for s in specs:
        v = verdicts.get(s.key)
        if v is None:
            continue
        name, doc = source_group(s.source)
        key = (name, v.klass, v.rule, re.sub(r"; alla \d+ komponenter är ja$", "; alla komponenter är ja", v.reason),
               doc)
        groups[key] += 1
        if v.scope:
            scopes[key].add(v.scope)
    rows = [[name, n, klass, rule, reason + (f" (bolag: {', '.join(sorted(scopes[k]))})" if scopes[k] else ""), doc]
            for k, n in groups.items() for (name, klass, rule, reason, doc) in [k]]
    return sorted(rows, key=lambda r: (-RANK[r[2]], r[0], r[4]))


def branch_rows(verdicts: dict[str, Verdict], specs: list[catalog.Spec]) -> list[list]:
    rows = []
    for code, name in catalog.BRANCHES.items():
        mine = [s for s in specs if s.branch == code and s.key in verdicts]
        cls = Counter(verdicts[s.key].klass for s in mine)
        pub_not_ja = sum(1 for s in mine if s.publish and verdicts[s.key].klass != JA)
        rows.append([f"{code} {name}", len(mine), cls.get(JA, 0), cls.get(NEJ, 0), cls.get(OKAND, 0), pub_not_ja])
    return rows


def rule_rows() -> list[list]:
    rows = [[i, "nyckel", k, c, r] for i, (k, (c, r)) in enumerate(KEY_OVERRIDES.items(), 1)]
    n = len(rows)
    rows += [[n + i, "källa", f"{r.name}: /{r.pattern}/", r.klass, r.reason] for i, r in enumerate(SOURCE_OVERRIDES, 1)]
    n = len(rows)
    rows.append([n + 1, "källa", "curated: källan nämner curated/<fil>.csv", "ja / okänd",
                 f"raderna som serien läser: seriens egna (ROW_SERIES: {', '.join(ROW_SERIES)}), annars bolagets "
                 f"(Kurerad extraktion (curated/<fil>.csv)), annars de som anges i CURATED_READS "
                 f"({len(CURATED_READS)} serier). ja: {CURATED_REASON_JA} (alla raderna har source_url på sec.gov); "
                 f"okänd: {CURATED_REASON_OKAND}; inga angivna rader: okänd, och validate ger fel. Den mest "
                 f"restriktiva av detta och licensreglerna avgör"])
    n = len(rows)
    rows.append([n + 1, "licens", "derived-licence: /^derived: a + b/", "mest restriktiva delen",
                 "varje del klassas med reglerna nedan"])
    n = len(rows)
    rows += [[n + i, "licens", f"{r.name}: /{r.pattern}/", r.klass, r.reason] for i, r in enumerate(RULES, 1)]
    rows.append([len(rows) + 1, "härledning", "Spec.components och medlemmarna i *_hyp4", "mest restriktiva",
                 "egen klass och komponenternas; ja bara om alla är ja, nej före okänd"])
    return rows


def report(markdown: bool = False, specs: list[catalog.Spec] | None = None) -> tuple[str, int]:
    """(text, number of unclassified series)."""
    specs = catalog.ALL if specs is None else specs
    verdicts, errors = classify_all(specs)
    total = Counter(v.klass for v in verdicts.values())
    core = core_summary({**catalog.by_key(), **{s.key: s for s in specs}})
    lines = []
    if markdown:
        lines += ["### Regler i ordning", ""]
        lines += _md_table(["#", "Typ", "Regel", "Klass", "Skäl"], rule_rows())
        lines += ["", "### Klass per källa", ""]
        lines += _md_table(["Källa", "Serier", "Klass", "Regel", "Skäl", "Licenstext"],
                           [r[:5] + [f"[{r[5]}](../{r[5]})" if r[5] else "–"] for r in source_rows(verdicts, specs)])
        lines += ["", "### Antal per gren (alla serier i katalogen)", ""]
        rows = branch_rows(verdicts, specs)
        rows.append(["Summa", len(verdicts), total.get(JA, 0), total.get(NEJ, 0), total.get(OKAND, 0),
                     sum(r[5] for r in rows)])
        lines += _md_table(["Gren", "Serier", "ja", "nej", "okänd", "publish=True men inte ja"], rows)
        lines += ["", "### Kommersiellt ren delmängd: kärnposter", ""]
        lines += _md_table(["Gren", "Kärnposter", "ja", "nej", "okänd", "Familjer", "Familjer kvar med bara ja",
                            "Minst 3 familjer kvar", "Poster som faller bort"],
                           [[r["branch"], r["entries"], r[JA], r[NEJ], r[OKAND], r["families"], r["families_ja"],
                             "ja" if r["families_ja"] >= 3 else "nej",
                             ", ".join(f"`{e}` ({v.klass})" for e, v in r["not_ja"].items()) or "–"] for r in core])
        readings = sorted({r["reading"] for r in core})
        lines += ["", "Familjeläsning: " + ", ".join(READINGS.get(r, r) for r in readings) + "."]
    else:
        lines.append(f"Kommersiell användning, {len(verdicts)} serier: ja {total.get(JA, 0)}, nej {total.get(NEJ, 0)}, "
                     f"okänd {total.get(OKAND, 0)}" + (f", EJ KLASSADE {len(errors)}" if errors else ""))
        lines.append("")
        for r in branch_rows(verdicts, specs):
            lines.append(f"{r[0]:<36} {r[1]:>4} serier  ja {r[2]:>4}  nej {r[3]:>3}  okänd {r[4]:>3}"
                         f"  (publish=True men inte ja: {r[5]})")
        lines.append("")
        for r in source_rows(verdicts, specs):
            lines.append(f"{r[2]:<6} {r[1]:>4}  {r[0]}  [{r[3]}] {r[4]}")
        lines.append("")
        lines.append("Kärnposter (kommersiellt ren delmängd = bara ja):")
        for r in core:
            lines.append(f"{r['branch']}: {r['entries']} poster (ja {r[JA]}, nej {r[NEJ]}, okänd {r[OKAND]}), "
                         f"familjer {r['families']} -> {r['families_ja']} med bara ja ({r['reading']})")
    for key, err in sorted(errors.items()):
        lines.append(f"EJ KLASSAD {key}: {err}")
    return "\n".join(lines) + "\n", len(errors)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m ai_tracker.licenses", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report", help="class per source and branch, and the commercially clean subset")
    r.add_argument("--markdown", action="store_true", help="Markdown tables (docs/datakallor/licensniva.md)")
    a = p.parse_args(argv)
    text, n_errors = report(markdown=a.markdown)
    sys.stdout.write(text)
    return 1 if n_errors else 0


if __name__ == "__main__":
    sys.exit(main())
