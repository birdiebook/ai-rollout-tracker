"""KL1 "Kreditlagret": the followed question's measures as catalog series (register 2026-11-25 "KL1"), publish=False.

Derived quarterly measures per company and per layer, read from the observation table (not from the sources):

    kl_rate_eff_<x>   100 x sum interest_exp(p-3..p) / (0.5 x lt_debt(p-4) + 0.5 x lt_debt(p))      % per year
    kl_fcfgap_<x>     100 x (sum capex - sum ocf) / sum capex, four quarters                          % of capex
    kl_netdebt_<x>    100 x (sum debt_issued - sum debt_repaid) / sum capex, four quarters            % of capex
    kl_leases_<x>     100 x lease_uncommenced(p) / sum capex, four quarters                           % of capex
    kl_capex4_<x>     sum capex over four quarters                                                     MUSD
    kl_rpo_add4_<x>   rpo(p) - rpo(p-4): net additions to RPO over four quarters                       MUSD

<x> is a company or a layer ("outer", "inner"). A layer sums its members' components (not a mean of their ratios), with
the members per measure registered in the entry (table "Lageraggregat"). Vintages as A5 (series/avstamning.py): at
every known_from d of any input, each input takes its latest vintage known on d; a version exists only when every input
has one, so a layer's version exists only once all its members have filed, and it is dated d.

From curated/kreditlagret.csv (sources/kreditlagret.py), only when at least MIN_QUARTERS quarters have a value
(register addendum 2026-11-25, points 4-5):

    kl_coupon_out_crwv_q  outstanding-weighted mean of the stated effective rate on CoreWeave's debt at quarter end
    kl_coupon_new_<co>_q  principal-weighted coupon of new fixed-rate USD debt, no convertibles (none qualifies today)

Not in any branch index, no core series, no state. The measures (level, pace, change in pace, surprise) and the
registered reading come from ai_tracker.followed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series import sec as _sec

OUTER = ("orcl", "crwv", "nbis", "iren")
INNER = ("msft", "googl", "amzn", "meta")
NAMES = {"orcl": "Oracle", "crwv": "CoreWeave", "nbis": "Nebius", "iren": "IREN", "msft": "Microsoft",
         "googl": "Alphabet", "amzn": "Amazon", "meta": "Meta", "outer": "yttre lagret", "inner": "inre lagret"}
DEBT = ("orcl", "crwv", "msft", "googl", "amzn", "meta")
LEASE = ("orcl", "crwv", "googl", "amzn", "meta", "msft", "msft_cond")
RPO = ("orcl", "crwv", "msft", "googl", "amzn")
# layer members per measure (register 2026-11-25 "KL1", table "Lageraggregat")
MEMBERS = {
    "rate_eff": {"outer": ("orcl", "crwv"), "inner": INNER},
    "fcfgap": {"outer": OUTER, "inner": INNER},
    "capex4": {"outer": OUTER, "inner": INNER},
    "netdebt": {"outer": ("orcl", "crwv"), "inner": INNER},
    "leases": {"outer": ("orcl", "crwv"), "inner": ("googl", "amzn", "meta")},
    "rpo_add4": {"outer": ("orcl", "crwv"), "inner": ("msft", "googl", "amzn")},
}
COMPANIES = {"rate_eff": DEBT, "fcfgap": OUTER + INNER, "capex4": OUTER + INNER, "netdebt": DEBT, "leases": LEASE,
             "rpo_add4": RPO}
SOURCE = "Härledd (KL1) ur SEC EDGAR XBRL-serier och extraherade serier i katalogen"
LICENSE = _sec.LICENSE
MAX_AGE = 183  # as the longest component (CoreWeave: 10-K up to 61 days after the quarter, + 92 + 30)
MIN_QUARTERS = 4  # a coupon series needs at least four quarters with a value (register entry, (b))


@dataclass(frozen=True)
class Term:
    series: str
    offset: int = 0  # p - offset
    weight: float = 1.0


@dataclass(frozen=True)
class Formula:
    key: str
    num: tuple[Term, ...]
    den: tuple[Term, ...] = ()  # empty: the value is the numerator
    scale: float = 1.0

    @property
    def components(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(t.series for t in (*self.num, *self.den)))


def _sum4(series: str, weight: float = 1.0) -> tuple[Term, ...]:
    return tuple(Term(series, k, weight) for k in range(4))


def _lease_key(c: str) -> str:
    return f"lease_uncommenced_{c}"


def terms(measure: str, companies: tuple[str, ...]) -> tuple[tuple[Term, ...], tuple[Term, ...], float]:
    """(numerator, denominator, scale) of a measure summed over companies."""
    num: list[Term] = []
    den: list[Term] = []
    for c in companies:
        cap = "capex_msft" if c == "msft_cond" else f"capex_{c}"
        if measure == "rate_eff":
            num += _sum4(f"interest_exp_{c}")
            den += [Term(f"lt_debt_{c}", 4, 0.5), Term(f"lt_debt_{c}", 0, 0.5)]
        elif measure == "fcfgap":
            num += _sum4(cap) + _sum4(f"ocf_{c}", -1.0)
            den += _sum4(cap)
        elif measure == "netdebt":
            num += _sum4(f"debt_issued_{c}") + _sum4(f"debt_repaid_{c}", -1.0)
            den += _sum4(cap)
        elif measure == "leases":
            num.append(Term(_lease_key(c)))
            den += _sum4(cap)
        elif measure == "capex4":
            num += _sum4(cap)
        elif measure == "rpo_add4":
            num += [Term(f"rpo_{c}"), Term(f"rpo_{c}", 4, -1.0)]
        else:
            raise KeyError(measure)
    scale = 1.0 if measure in ("capex4", "rpo_add4") else 100.0
    return tuple(num), tuple(den), scale


def formula(measure: str, who: str) -> Formula:
    companies = MEMBERS[measure][who] if who in ("outer", "inner") else (who,)
    num, den, scale = terms(measure, companies)
    return Formula(f"kl_{measure}_{who}", num, den, scale)


def _versions(rows: pd.DataFrame) -> dict[tuple[str, str], tuple[np.ndarray, np.ndarray, np.ndarray]]:
    out = {}
    r = rows.sort_values("known_from", kind="stable")
    for (s, p), g in r.groupby(["series", "period"], sort=False):
        out[(s, str(p))] = (g["known_from"].to_numpy(dtype="datetime64[ns]"), g["value"].to_numpy(dtype=float),
                            (g["source"] == "backfill").to_numpy())
    return out


def derive(f: Formula, rows: pd.DataFrame) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from, source) of a formula from component rows in observation-table
    form. Pure: no I/O. A version per date on which an input gets a vintage, only when every input has one."""
    rows = rows[rows["series"].isin(f.components)].copy()
    if rows.empty:
        return pd.DataFrame(columns=["period", "value", "known_from", "source"])
    rows["known_from"] = pd.to_datetime(rows["known_from"])
    vers = _versions(rows)
    anchor = f.num[0].series
    periods = sorted({p for (s, p) in vers if s == anchor})
    out = []
    for p in periods:
        per = pd.Period(p, freq="Q-DEC")
        num = [((t.series, str(per - t.offset)), t.weight) for t in f.num]
        den = [((t.series, str(per - t.offset)), t.weight) for t in f.den]
        need = list(dict.fromkeys(k for k, _ in num + den))
        if any(k not in vers for k in need):
            continue
        prev = None
        for d in np.unique(np.concatenate([vers[k][0] for k in need])):
            vals, backfill, ok = {}, False, True
            for k in need:
                kf, v, bf = vers[k]
                i = int(np.searchsorted(kf, d, side="right")) - 1
                if i < 0:
                    ok = False
                    break
                vals[k], backfill = v[i], backfill or bool(bf[i])
            if not ok:
                continue
            n = sum(w * vals[k] for k, w in num)
            if den:
                m = sum(w * vals[k] for k, w in den)
                if not np.isfinite(m) or m == 0:
                    continue
                value = f.scale * n / m
            else:
                value = f.scale * n
            if not np.isfinite(value):
                continue
            if prev is None or not np.isclose(value, prev, rtol=1e-12, atol=0):
                out.append((p, float(value), pd.Timestamp(d), "backfill" if backfill else "derived"))
                prev = value
    df = pd.DataFrame(out, columns=["period", "value", "known_from", "source"])
    return df.sort_values(["known_from", "period"], ignore_index=True)


def _fetch(f: Formula):
    def fetch(table: pd.DataFrame | None = None) -> pd.DataFrame:
        from ai_tracker import observations  # lazy: observations -> catalog -> series -> this module

        t = observations.load() if table is None else table
        return derive(f, t[t["series"].isin(f.components)])

    return fetch


LABELS = {
    "rate_eff": ("Effektiv ränta (räntekostnad / genomsnittlig långfristig skuld, fyra kvartal)", "% per år",
                 "Vad kostar skulden, och ändras priset?"),
    "fcfgap": ("Capex som inte bärs av det operativa kassaflödet, fyra kvartal", "% av capex",
               "Hur stor del av investeringen måste finansieras utifrån?"),
    "netdebt": ("Nettoemission av skuld i procent av capex, fyra kvartal", "% av capex",
                "Hur mycket av investeringen motsvaras av ny nettoupplåning?"),
    "leases": ("Tecknade leasingavtal som inte börjat i procent av capex, fyra kvartal", "% av capex",
               "Hur mycket kapacitet är redan bunden via hyresavtal, i förhållande till ett års capex?"),
    "capex4": ("Capex över fyra kvartal", "MUSD", "Vilken investeringstakt syns, och ändras den?"),
    "rpo_add4": ("Tillskott till RPO över fyra kvartal (RPO nu minus fyra kvartal tidigare)", "MUSD",
                 "Hur mycket ny kontrakterad efterfrågan tillkommer netto?"),
}
NOTES = {
    "rate_eff": "Räntekostnaden i resultaträkningen är efter aktiverad ränta på pågående bygge, så måttet blir lägre än "
                "kupongen hos bolag som bygger mycket. ",
    "netdebt": "debt_issued minus debt_repaid, båda som de lagras (positiva belopp). ",
    "leases": "Balans vid kvartalets slut mot ett års capex. ",
    "rpo_add4": "Klumpig: enstaka mycket stora avtal flyttar ett kvartal. Nettot är nya avtal minus intäktsförda. ",
}


def _spec(measure: str, who: str) -> Spec:
    f = formula(measure, who)
    label, unit, question = LABELS[measure]
    if who in ("outer", "inner"):
        members = ", ".join(NAMES[c] for c in MEMBERS[measure][who])
        who_label = f"{NAMES[who]} ({members})"
        extra = "Summa av medlemmarnas komponenter; en version finns först när alla har lämnat in. "
    elif who == "msft_cond":
        who_label = "Microsoft (inklusive villkorade avtal, från 2026Q2)"
        extra = "Microsofts definition breddades 2026-06-30 (lease_uncommenced_msft_cond); ingen takt över brottet. "
    else:
        who_label = NAMES[who]
        extra = ""
    closed = measure == "leases" and who == "msft"
    if closed:
        extra += "Avslutad 2026Q1: Microsofts definition breddades 2026-06-30 (fortsätter som kl_leases_msft_cond). "
    note = (f"KL1 (följd fråga, register 2026-11-25). {NOTES.get(measure, '')}{extra}known_from = den senaste "
            f"komponenten som används. Aktualitet: gräns {MAX_AGE} dagar, som komponenternas längsta (CoreWeaves 10-K "
            "kommer upp till 61 dagar efter kvartalet). Räknas inte i grenarnas diffusionsindex. publish=False.")
    return Spec(key=f.key, branch="G5", label=f"{label}, {who_label}", unit=unit, freq="Q", source=SOURCE,
                fetch=_fetch(f), lag_days=25, license=LICENSE, revised=True, publish=False, question=question,
                note=note, components=f.components, max_age_days=MAX_AGE, closed=closed)


# ------------------------------------------------------------------ coupon series from the curated extraction

CURATED_SOURCE = ("Kurerad extraktion (curated/kreditlagret.csv) ur CoreWeaves 10-Q och 10-K på SEC EDGAR "
                  "(skuldtabellen)")
CURATED_LICENSE = ("SEC EDGAR: public information (sec.gov/privacy). Bara extraherade siffror med källhänvisning "
                   "publiceras, aldrig text")


def coupon_out(df: pd.DataFrame, company: str) -> pd.DataFrame:
    """Outstanding-weighted mean of rate_pct per balance date (calendar quarter); known_from = max(day after the
    quarter, latest filed of the rows used). Rows: period, value, known_from, coverage (share of outstanding with a
    rate)."""
    d = df[df["company"] == company]
    out = d[d["field"] == "outstanding"][["instrument", "period", "value", "filed"]].rename(columns={"value": "out"})
    rate = d[d["field"] == "rate_pct"][["instrument", "period", "value", "filed"]].rename(columns={"value": "rate"})
    m = out.merge(rate, on=["instrument", "period"], how="left", suffixes=("", "_rate"))
    m["out"] = m["out"].astype(float)
    m["rate"] = pd.to_numeric(m["rate"], errors="coerce")
    rows = []
    for period, g in m.groupby("period"):
        q = pd.Period(pd.Timestamp(period), freq="Q-DEC")
        if pd.Timestamp(period) != q.end_time.normalize():
            continue  # a balance date that is not a quarter end (none in the tables)
        g = g[g["out"] > 0]
        rated = g[g["rate"].notna()]
        if rated.empty:
            continue
        value = float((rated["out"] * rated["rate"]).sum() / rated["out"].sum())
        filed = max(pd.Timestamp(x) for x in pd.concat([rated["filed"], rated["filed_rate"]]))
        kf = max(q.end_time.normalize() + pd.Timedelta(days=1), filed)
        rows.append((str(q), value, kf, float(rated["out"].sum() / g["out"].sum())))
    return pd.DataFrame(rows, columns=["period", "value", "known_from", "coverage"])


def coupon_new(df: pd.DataFrame, company: str) -> pd.DataFrame:
    """Principal-weighted coupon of new fixed-rate USD debt per calendar quarter of issue_date, convertibles excluded
    (register addendum, point 5). Same dating rule as coupon_out."""
    d = df[df["company"] == company]
    wide = {}
    for r in d.itertuples(index=False):
        wide.setdefault(r.instrument, {})[r.field] = (r.value, r.unit, r.filed, r.qualifier)
    rows = []
    for inst, f in wide.items():
        if "convertible" in inst or not {"principal", "coupon_pct", "issue_date"} <= set(f):
            continue
        if f["principal"][1] != "MUSD" or f["principal"][3] or len(f["issue_date"][0]) != 10:
            continue  # other currency, a qualified amount or a month-only date
        rows.append((pd.Period(pd.Timestamp(f["issue_date"][0]), freq="Q-DEC"), float(f["principal"][0]),
                     float(f["coupon_pct"][0]), max(pd.Timestamp(f[k][2]) for k in ("principal", "coupon_pct"))))
    if not rows:
        return pd.DataFrame(columns=["period", "value", "known_from"])
    t = pd.DataFrame(rows, columns=["q", "principal", "coupon", "filed"])
    out = []
    for q, g in t.groupby("q"):
        kf = max(q.end_time.normalize() + pd.Timedelta(days=1), g["filed"].max())
        out.append((str(q), float((g["principal"] * g["coupon"]).sum() / g["principal"].sum()), kf))
    return pd.DataFrame(out, columns=["period", "value", "known_from"])


def _curated_specs() -> list[Spec]:
    from ai_tracker.sources import kreditlagret as kl

    if not kl.CSV_PATH.exists():
        return []
    df = kl.load()
    specs = []
    for co in sorted(set(df["company"])):
        for name, fn, label in (("out", coupon_out, "Angiven effektiv ränta på utestående skuld, vägd"),
                                ("new", coupon_new, "Kupong på ny skuld med fast ränta i USD, vägd")):
            if len(fn(df, co)) < MIN_QUARTERS:
                continue  # too few quarters: the values stay table rows (register entry, (b))

            def fetch(fn=fn, co=co):
                return fn(kl.load(), co)[["period", "value", "known_from"]].copy()

            specs.append(Spec(
                key=f"kl_coupon_{name}_{co}_q", branch="G5", label=f"{label}, {NAMES.get(co, co)}", unit="% per år",
                freq="Q", source=CURATED_SOURCE, fetch=fetch, lag_days=1, license=CURATED_LICENSE, revised=True,
                publish=False, question="Vad kostar skulden i de yttre lagren, och ändras priset?",
                note="KL1 (register 2026-11-25 och tillägget). Vägt med utestående belopp; räntorna står i hela procent "
                     "i tabellen (avrundningsbrus upp till ±0,5 procentenheter). Konvertibler ingår. Ett kvartal är "
                     "känt från dagen efter kvartalet eller den senaste inlämningen. Aktualitet: gräns 183 dagar "
                     "(CoreWeaves 10-K kommer upp till 61 dagar efter kvartalet). publish=False.",
                max_age_days=183))
    return specs


SPECS = ([_spec(m, c) for m in COMPANIES for c in COMPANIES[m]]
         + [_spec(m, w) for m in MEMBERS for w in ("outer", "inner")]
         + _curated_specs())
KNOWN_GAPS: dict[str, str] = {}
