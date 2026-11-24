"""Multi-year plans (step 2, track D1): a curated CSV of agent-extracted values, loaded as release-dated series.

The agent reads every candidate sentence (ai_tracker.sources.plans_corpus) and records one row per stated value in
curated/plans.csv, coded by the rules in docs/kallor/planer.md (written before coding): measure, kind, number(s),
unit, horizon (which years), definition, direction code if qualitative, document date, URL / accession, locator and
the SHA-256 of the exact source sentence. The sentence itself is kept only in data/raw/plans_sentences (gitignored).

Measures: CAPEX (capex beyond the current fiscal year, multi-year totals; for Oracle and CoreWeave also the current
year), INFRA (announced infrastructure investment amounts that are not stated as capex), CAPACITY (data-center power
targets in MW, relative targets as a multiple, and reported power levels), BACKLOG (CoreWeave's revenue backlog and
segment backlogs; total company RPO is A1's), COMMIT (non-cancelable infrastructure commitments stated in text).

known_from = `filed`, the date the document became public. The loader refuses a plan whose period had already ended
when the document came out (only `reported` values describe the past), and, for MSFT/GOOGL/AMZN/META capex, a
single-year row for the current fiscal year (that is E1's guidance_capex domain).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

from ai_tracker import config
from ai_tracker.sources import guidance_capex

PATH = config.REPO / "curated" / "plans.csv"
SENTENCES_DIR = config.REPO / "data" / "raw" / "plans_sentences"  # gitignored

COLUMNS = ["id", "company", "measure", "kind", "value_lo", "value_hi", "unit", "direction_code", "direction_base",
           "horizon", "year_basis", "period_start", "period_end", "scope", "definition", "filed", "accepted",
           "doc_type", "source_url", "accession", "locator", "sentence_sha256", "xref", "note"]
COMPANIES = {"msft": "Microsoft", "googl": "Alphabet", "amzn": "Amazon", "meta": "Meta", "orcl": "Oracle",
             "crwv": "CoreWeave"}
E1_COMPANIES = ("msft", "googl", "amzn", "meta")
MEASURES = ("CAPEX", "INFRA", "CAPACITY", "BACKLOG", "COMMIT")
KINDS = ("point", "range", "approx", "min", "max", "direction", "reported")
HORIZONS = ("Y", "SPAN", "BY", "ASOF", "OPEN")
DIRECTION_BASES = ("yoy", "growth_vs_prior")
UNITS = {"CAPEX": ("MUSD", "code"), "INFRA": ("MUSD",), "CAPACITY": ("MW", "multiple"), "BACKLOG": ("MUSD",),
         "COMMIT": ("MUSD",)}

# definition code -> what the number measures (company wording, summarised); E1's codes are reused unchanged
DEFINITIONS = dict(guidance_capex.DEFINITIONS) | {
    # capex
    "ORCL_CAPEX": "Oracle: capital expenditures (cash flow statement 'capital expenditures'), fiscal year June-May",
    "CRWV_CAPEX": "CoreWeave: capital expenditures as guided in its press release (company basis)",
    # announced infrastructure investment
    "AMZN_AWS_REGION_INVEST": "Amazon/AWS: planned investment in a country (construction and operation of AWS "
                              "infrastructure Regions / data center complexes), scope = country",
    # capacity (power)
    "MSFT_AI_CAPACITY": "Microsoft: total AI capacity, as a multiple of the level at the start of the period",
    "MSFT_DC_FOOTPRINT": "Microsoft: total datacenter footprint (capacity), as a multiple of the current level",
    "MSFT_POWER_ADDED_Q": "Microsoft: data-center capacity (power) added in the quarter (MW)",
    "AMZN_POWER_ADDED_12M": "Amazon/AWS: power capacity added in the 12 months to the date (MW)",
    "AMZN_POWER_TOTAL": "Amazon/AWS: total power capacity, as a multiple of the current level",
    "ORCL_DC_CAPACITY": "Oracle: data center capacity, as a multiple of the level at the start of the period",
    "ORCL_POWER_ADDED_Q": "Oracle: additional datacenter capacity delivered in the fiscal quarter (MW)",
    "CRWV_ACTIVE_POWER": "CoreWeave: active power (MW) across its data centers",
    "CRWV_CONTRACTED_POWER": "CoreWeave: total contracted power (MW), active plus contracted not yet active",
    "CRWV_POWER_2030_UNSPEC": "CoreWeave: power (MW) by 2030 as stated by the CEO, active or contracted not stated",
    "CRWV_AI_FACTORY_BUILDOUT": "CoreWeave: buildout of AI factories (MW) under the NVIDIA collaboration",
    # backlog not in A1's company-total RPO
    "CRWV_BACKLOG": "CoreWeave: revenue backlog (press-release measure: RPO plus other amounts expected under "
                    "committed customer contracts, subject to delivery)",
    "GOOGL_CLOUD_BACKLOG": "Alphabet: Google Cloud backlog (the part of revenue backlog/RPO related to Google Cloud)",
    "MSFT_COMMERCIAL_RPO": "Microsoft: commercial remaining performance obligation (earnings call)",
    # commitments (not leases)
    "META_NONCANCEL_COMMIT": "Meta: non-cancelable contractual commitments excluding leases (commitments note), "
                             "described as mostly servers, network infrastructure, data centers, third-party cloud "
                             "capacity and Reality Labs hardware",
    "ORCL_UNCOND_OBLIG": "Oracle: unconditional purchase and certain other obligations (cloud capacity / data "
                         "center power arrangements)",
    "ORCL_UNCOND_OBLIG_1Y": "Oracle: unconditional purchase and certain other obligations with terms of one year or "
                            "greater (component supply and data center power)",
    "CRWV_LEASE_EQUIP_COMMIT": "CoreWeave: estimated cost to fulfil obligations to procure and install equipment at "
                               "leased data centers (range)",
    "CRWV_CONSTRUCTION_COMMIT": "CoreWeave: contractual commitments for future data center construction costs",
}


class CsvError(ValueError):
    pass


def _float(x) -> float | None:
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
        if r["company"] not in COMPANIES or r["measure"] not in MEASURES or r["kind"] not in KINDS \
                or r["horizon"] not in HORIZONS or r["year_basis"] not in ("CY", "FY"):
            raise CsvError(f"{where}: company/measure/kind/horizon/year_basis not in the scheme")
        if r["definition"] not in DEFINITIONS:
            raise CsvError(f"{where}: unknown definition {r['definition']!r}")
        if r["unit"] not in UNITS[r["measure"]]:
            raise CsvError(f"{where}: unit {r['unit']!r} not allowed for {r['measure']}")
        if not re.fullmatch(r"[0-9a-f]{64}", r["sentence_sha256"]):
            raise CsvError(f"{where}: sentence_sha256 must be 64 hex characters")
        if not r["source_url"].startswith("https://") or not re.search(r"sentence #\d+", r["locator"]):
            raise CsvError(f"{where}: source_url and a locator with 'sentence #k' are required")
        filed = pd.Timestamp(r["filed"])
        if r["accepted"] and not -4 <= (pd.Timestamp(r["accepted"][:10]) - filed).days <= 1:
            raise CsvError(f"{where}: accepted {r['accepted']} does not match the filing date {r['filed']}")
        if r["horizon"] != "OPEN":
            start, end = pd.Timestamp(r["period_start"]), pd.Timestamp(r["period_end"])
            if not start <= end:
                raise CsvError(f"{where}: period_start must not be after period_end")
            if r["kind"] == "reported" and r["horizon"] != "ASOF":
                raise CsvError(f"{where}: a reported value has horizon ASOF")
            if r["horizon"] == "ASOF":
                if end > filed or r["kind"] == "direction":
                    raise CsvError(f"{where}: an ASOF value is a number at a date on or before the document")
            elif filed > end:
                raise CsvError(f"{where}: plan filed {filed.date()} after its period ended {end.date()}")
            if (r["measure"] == "CAPEX" and r["company"] in E1_COMPANIES and r["horizon"] == "Y"
                    and not start > filed):
                raise CsvError(f"{where}: current-year capex of {r['company']} belongs to guidance_capex (E1)")
        elif r["kind"] in ("reported", "direction"):
            raise CsvError(f"{where}: an OPEN horizon needs a number (no reported/direction)")
        lo, hi = _float(r["value_lo"]), _float(r["value_hi"])
        if r["kind"] == "direction":
            if r["direction_code"] not in ("-2", "-1", "0", "1", "2") or r["direction_base"] not in DIRECTION_BASES \
                    or r["unit"] != "code":
                raise CsvError(f"{where}: a direction needs direction_code -2..2, a direction_base and unit code")
        else:
            if r["unit"] == "code":
                raise CsvError(f"{where}: unit code is for directions only")
            need_lo = r["kind"] != "max"
            need_hi = r["kind"] in ("point", "range", "approx", "reported", "max")
            if (need_lo and lo is None) or (need_hi and hi is None):
                raise CsvError(f"{where}: kind {r['kind']} needs value_lo/value_hi")
            if lo is not None and hi is not None and lo > hi:
                raise CsvError(f"{where}: value_lo > value_hi")
            if r["kind"] in ("point", "approx", "reported") and lo != hi:
                raise CsvError(f"{where}: a point/approx/reported value has value_lo == value_hi")
    df = pd.DataFrame(rows, columns=COLUMNS)
    for c in ("value_lo", "value_hi", "direction_code"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["known_from"] = pd.to_datetime(df["filed"])
    return df


# ------------------------------------------------------------------ series


def horizon_slug(row) -> str:
    """'y' | 'by' | 'asof' | 'span<N>y' (N = whole years covered)."""
    if row["horizon"] != "SPAN":
        return row["horizon"].lower()
    days = (pd.Timestamp(row["period_end"]) - pd.Timestamp(row["period_start"])).days
    return f"span{max(1, round(days / 365.25))}y"


def period_of(row) -> str:
    """Quarter of the balance date for ASOF rows, else the calendar year in which the horizon ends."""
    end = pd.Timestamp(row["period_end"])
    return str(end.to_period("Q-DEC")) if row["horizon"] == "ASOF" else str(end.year)


def fields(row) -> list[tuple[str, float]]:
    """(field, value) pairs a row contributes: lo/hi for numbers (min -> lo, max -> hi), dir_<base> for directions.

    A level at a date (ASOF: reported backlog, power, commitments) is one series whatever its qualifier
    ("approximately", "more than"): field value, the qualifier stays in the CSV's kind.
    """
    if row["kind"] == "direction":
        return [(f"dir_{row['direction_base']}", float(row["direction_code"]))]
    if row["horizon"] == "ASOF" and row["kind"] != "range":
        return [("value", float(row["value_lo"] if pd.notna(row["value_lo"]) else row["value_hi"]))]
    out = []
    if pd.notna(row["value_lo"]):
        out.append(("lo", float(row["value_lo"])))
    if pd.notna(row["value_hi"]):
        out.append(("hi", float(row["value_hi"])))
    if row["kind"] in ("point", "approx", "reported"):
        out = [("value", float(row["value_lo"]))]
    return out


def series_key(row, field: str) -> str:
    slug = row["definition"].lower()
    if row["scope"] and row["scope"] != "global":
        slug += f"_{row['scope'].lower()}"
    return f"plan_{slug}_{horizon_slug(row)}_{field}"


def long_rows(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (series key, period, value, known_from) before vintage de-duplication."""
    out = []
    for _, r in df[df["horizon"] != "OPEN"].iterrows():
        for field, v in fields(r):
            out.append((series_key(r, field), r["company"], r["measure"], r["definition"], horizon_slug(r), field,
                        r["unit"], period_of(r), v, r["known_from"], r["id"]))
    return pd.DataFrame(out, columns=["key", "company", "measure", "definition", "horizon", "field", "unit",
                                      "period", "value", "known_from", "id"])


def series_frame(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) of one series.

    A value repeated in a later document adds no row; several statements in one document for the same period: the
    last row in file order wins.
    """
    d = long_rows(df)
    d = d[d["key"] == key].sort_values("known_from", kind="stable")
    out, last = [], {}
    for p, v, kf in d[["period", "value", "known_from"]].itertuples(index=False):
        if p in last and last[p] == v:
            continue
        last[p] = v
        out.append((p, float(v), kf))
    res = pd.DataFrame(out, columns=["period", "value", "known_from"])
    return res.drop_duplicates(["period", "known_from"], keep="last").reset_index(drop=True)


def known_gaps(path: Path | None = None) -> dict[str, str]:
    """Series whose periods are not contiguous, with the reason (warehouse.KNOWN_GAPS): plans and reported levels
    are stated irregularly (a target for 2027 and one for 2029; backlog history for some year-ends only)."""
    path = path or PATH
    if not path.exists():
        return {}
    lr = long_rows(load(path))
    out = {}
    for key, g in lr.groupby("key"):
        freq = "Q-DEC" if g["horizon"].iloc[0] == "asof" else "Y-DEC"
        ords = sorted({pd.Period(p, freq=freq).ordinal for p in g["period"]})
        if len(ords) != ords[-1] - ords[0] + 1:
            out[key] = "D1 plans: irregular statements, a missing period is a period nobody stated (not a zero)"
    return out


MEASURE_LABEL = {"CAPEX": "capexplan", "INFRA": "aviserad infrastrukturinvestering", "CAPACITY": "kapacitet",
                 "BACKLOG": "orderstock", "COMMIT": "åtaganden för infrastruktur"}
HORIZON_LABEL = {"y": "för ett år", "by": "mål senast", "asof": "redovisat läge"}
FIELD_LABEL = {"lo": "lägsta", "hi": "högsta", "value": "värde", "dir_yoy": "riktning mot föregående år (−2..+2)",
               "dir_growth_vs_prior": "tillväxt mot föregående års tillväxt (−2..+2)"}
LICENSE = ("SEC EDGAR: public information (sec.gov/privacy); microsoft.com: bara extraherade siffror med "
           "källhänvisning, aldrig text")


def specs(path: Path | None = None) -> list:
    """One Spec per series key present in the curated CSV."""
    from ai_tracker.catalog import Spec

    path = path or PATH
    if not path.exists():
        return []
    df = load(path)
    lr = long_rows(df)
    out = []
    for key, g in lr.groupby("key", sort=True):
        first = g.iloc[0]
        asof = first["horizon"] == "asof"
        freq = "Q" if asof else "A"
        period_end = [pd.Period(p, freq="Q-DEC" if asof else "Y-DEC").end_time.normalize() for p in g["period"]]
        min_lag = min((kf - pe).days for kf, pe in zip(g["known_from"], period_end))
        # freshness: a plan for a year is restated irregularly (Meta gave a next-year range in 2022 and 2023 only),
        # so 3 years; a level reported every quarter (>= 4 periods) is due within 200 days, a sparse one within 400
        max_age = 1100 if not asof else (200 if g["period"].nunique() >= 4 else 400)
        hz = HORIZON_LABEL.get(first["horizon"], f"summa över {first['horizon'][4:-1]} år")

        def fetch(k=key):
            return series_frame(load(path), k)

        out.append(Spec(
            key=key, branch="G5", freq=freq,
            label=f"{COMPANIES[first['company']]}: {MEASURE_LABEL[first['measure']]}, {hz}, "
                  f"{FIELD_LABEL[first['field']]}",
            unit=first["unit"] if first["unit"] != "code" else "kod",
            source="Kurerad extraktion (curated/plans.csv): SEC EDGAR 8-K/10-Q/10-K/S-1/424B och microsoft.com",
            fetch=fetch, lag_days=min(min_lag, 0) if not asof else min_lag, license=LICENSE,
            revised=True, publish=False,
            question="Vad har bolaget sagt om framtida investeringar, kapacitet och orderstock (program D)?",
            max_age_days=max_age,
            note=f"Definition: {first['definition']} ({DEFINITIONS[first['definition']]}). period = "
                 + ("kvartalet för balansdagen. " if asof else "året då horisonten slutar. ")
                 + f"Agentextraherat, ej granskat (R5). Se docs/kallor/planer.md. Aktualitet: oregelbundna "
                   f"uttalanden, gräns {max_age} dagar."))
    return out
