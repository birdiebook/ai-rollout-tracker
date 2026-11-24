"""A5: reconciliations between the leads (docs/mattregister.md, 2026-11-23 "A5: avstämningar mellan leden").

Derived quarterly ratios of catalog series, read from the observation table (not from the sources):

    x_capex_cloud  capex_hyp4 / (rev_aws + rev_google_cloud + rev_msft_cloud), same quarter       L3-L5
    x_rpo_cover    rpo_hyp4 (balance at quarter end) / sum of capex_hyp4 over the 4 latest quarters L4-L5
    x_nvda_capex   rev_nvda_datacenter / capex_hyp4, same calendar quarter                        L5-L6
    x_debt_capex   sum of debt_issued_hyp4 / sum of capex_hyp4, the 4 latest quarters             L5
    x_capex_ocf    capex_hyp4 / ocf_hyp4 x 100 (the existing capex_ocf_hyp4)                      L5

Vintages (leakage-critical). For a period p the inputs are (series, quarter) pairs: p itself for a same-quarter
term, p-3..p for a 4-quarter sum. A stock (RPO) is the balance at p and is never summed. At every known_from d of
any input, each input takes its latest vintage with known_from <= d; a version exists only when every input has
one, and it is dated d (= the latest component used). A rolling sum therefore exists only once all four quarters
are known on that date. A new row is emitted when the value changes. Rows take source "backfill" if any input
used is a backfill row, else "derived".

Calendar mapping: the components' own (calendar quarter of the fiscal quarter's midpoint), joined on period.
No pace is computed here: measures come from the state engine (group "Avstämningar", not in any branch index).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.series import sec as _sec
from ai_tracker.series import sec_finansiering as _fin
from ai_tracker.series import sec_rpo as _rpo
from ai_tracker.series import sec_segments as _seg

FREQ = "Q"
SOURCE = "Härledd (A5) ur SEC EDGAR XBRL-serier i katalogen"
LAG_DAYS = 25  # as the SEC components; known_from always comes from the components


@dataclass(frozen=True)
class Term:
    series: str
    window: int = 1  # 1 = the period itself (also a stock: balance at the period end); 4 = sum of p-3..p


@dataclass(frozen=True)
class Recon:
    key: str
    label: str
    num: tuple[Term, ...]
    den: tuple[Term, ...]
    lead: str  # led in docs/steg2/plan.md
    question: str
    note: str
    scale: float = 1.0
    unit: str = "kvot"
    max_age_days: int | None = None

    @property
    def components(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(t.series for t in (*self.num, *self.den)))


CLOUD = (Term("rev_aws"), Term("rev_google_cloud"), Term("rev_msft_cloud"))
RECONS = [
    Recon("x_capex_cloud", "Capex / molnintäkter (AWS + Google Cloud + Microsoft Cloud), samma kvartal",
          (Term("capex_hyp4"),), CLOUD, "L3–L5",
          "Hur stor är investeringen i förhållande till molnintäkterna samma kvartal?",
          "capex_hyp4 / (rev_aws + rev_google_cloud + rev_msft_cloud). Capex är MSFT+GOOGL+AMZN+META, molnet tre "
          "segment (Meta har inget)."),
    Recon("x_rpo_cover", "RPO-balans / capex för de fyra senaste kvartalen",
          (Term("rpo_hyp4"),), (Term("capex_hyp4", 4),), "L4–L5",
          "Hur stor är den kontrakterade efterfrågan i förhållande till ett års investeringar?",
          "rpo_hyp4 är en balans vid kvartalets slut (MSFT+GOOGL+AMZN+ORCL) och summeras inte; nämnaren är "
          "capex_hyp4 summerad över kvartalet och de tre föregående. Bolagsmängderna skiljer sig (ORCL mot META)."),
    Recon("x_nvda_capex", "Nvidias datacenterintäkter / capex, samma kalenderkvartal",
          (Term("rev_nvda_datacenter"),), (Term("capex_hyp4"),), "L5–L6",
          "Hur stor del av investeringen motsvaras av Nvidias datacenterförsäljning samma kvartal?",
          "rev_nvda_datacenter / capex_hyp4. Nvidias räkenskapskvartal (aug–okt osv.) märks med kalenderkvartalet "
          f"för mittpunkten, alltså cirka en månad förskjutet. Aktualitet som Nvidia: gräns "
          f"{_sec.NVDA_MAX_AGE_DAYS} dagar (rapporten kommer 45–77 dagar efter kalenderkvartalets slut).",
          max_age_days=_sec.NVDA_MAX_AGE_DAYS),
    Recon("x_debt_capex", "Skuldemission / capex, de fyra senaste kvartalen",
          (Term("debt_issued_hyp4", 4),), (Term("capex_hyp4", 4),), "L5",
          "Hur stor del av ett års investeringar motsvaras av ny långfristig upplåning?",
          "Summa debt_issued_hyp4 / summa capex_hyp4 över kvartalet och de tre föregående (MSFT+GOOGL+AMZN+META)."),
    Recon("x_capex_ocf", "Capex i procent av operativt kassaflöde, samma kvartal",
          (Term("capex_hyp4"),), (Term("ocf_hyp4"),), "L5",
          "Hur stor del av kassaflödet tar investeringarna?",
          "Samma värden och versioner som capex_ocf_hyp4 (capex_hyp4 / ocf_hyp4 × 100). Som avstämning mäts den "
          "med årsförändring i log, inte i procentenheter.",
          scale=100.0, unit="procent av OCF"),
]
BY_KEY = {r.key: r for r in RECONS}
KEYS = [r.key for r in RECONS]


def _component_specs() -> dict[str, Spec]:
    return {s.key: s for mod in (_sec, _seg, _rpo, _fin) for s in mod.SPECS}


def inputs_for(recon: Recon, period: pd.Period) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(series, period) pairs of the numerator and the denominator for `period`."""
    def pairs(terms):
        return [(t.series, str(period - k)) for t in terms for k in range(t.window)]
    return pairs(recon.num), pairs(recon.den)


def _versions(rows: pd.DataFrame) -> dict[tuple[str, str], tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """(series, period) -> (known_from, value, is_backfill) sorted by known_from."""
    out = {}
    if rows is None or rows.empty:
        return out
    r = rows.sort_values("known_from", kind="stable")
    for (s, p), g in r.groupby(["series", "period"], sort=False):
        out[(s, str(p))] = (g["known_from"].to_numpy(dtype="datetime64[ns]"), g["value"].to_numpy(dtype=float),
                            (g["source"] == "backfill").to_numpy())
    return out


def derive(recon: Recon, rows: pd.DataFrame) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from, source) of `recon` from component rows in observation-table
    form (columns series, period, value, known_from, source). Pure: no I/O. See the module docstring."""
    rows = rows[rows["series"].isin(recon.components)].copy()
    rows["known_from"] = pd.to_datetime(rows["known_from"])
    vers = _versions(rows)
    first = recon.num[0].series
    periods = sorted({p for (s, p) in vers if s == first})
    out = []
    for p in periods:
        num, den = inputs_for(recon, pd.Period(p, freq="Q-DEC"))
        need = num + den
        if any(k not in vers for k in need):
            continue
        dates = np.unique(np.concatenate([vers[k][0] for k in need]))
        prev = None
        for d in dates:
            vals, backfill, ok = {}, False, True
            for k in need:
                kf, v, bf = vers[k]
                i = int(np.searchsorted(kf, d, side="right")) - 1  # latest vintage with known_from <= d
                if i < 0:
                    ok = False
                    break
                vals[k], backfill = v[i], backfill or bool(bf[i])
            if not ok:
                continue
            n, m = sum(vals[k] for k in num), sum(vals[k] for k in den)
            if not np.isfinite(n) or not np.isfinite(m) or m == 0:
                continue
            value = recon.scale * n / m
            if prev is None or not np.isclose(value, prev, rtol=1e-12, atol=0):
                out.append((p, float(value), pd.Timestamp(d), "backfill" if backfill else "derived"))
                prev = value
    df = pd.DataFrame(out, columns=["period", "value", "known_from", "source"])
    return df.sort_values(["known_from", "period"], ignore_index=True)


def _fetch(recon: Recon):
    def fetch(table: pd.DataFrame | None = None) -> pd.DataFrame:
        from ai_tracker import observations  # lazy: observations -> catalog -> series -> this module

        t = observations.load() if table is None else table
        return derive(recon, t[t["series"].isin(recon.components)])

    return fetch


def _spec(recon: Recon, components: dict[str, Spec]) -> Spec:
    comp = [components[k] for k in recon.components]
    licenses = list(dict.fromkeys(s.license for s in comp))
    note = (f"Avstämning {recon.lead} (A5). {recon.note} En version finns först när alla komponenter för perioden "
            "är kända, known_from = den senaste komponenten. Räknas inte i grenarnas diffusionsindex.")
    return Spec(key=recon.key, branch="G5", label=recon.label, unit=recon.unit, freq=FREQ, source=SOURCE,
                fetch=_fetch(recon), lag_days=LAG_DAYS, license=" | ".join(licenses), revised=True,
                publish=all(s.publish for s in comp), question=recon.question, note=note,
                max_age_days=recon.max_age_days, components=recon.components)


SPECS = [_spec(r, _component_specs()) for r in RECONS]
