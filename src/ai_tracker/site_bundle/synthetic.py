"""A small synthetic world for the committed fixtures (web-data-fixtures/) and the tests. No real data.

Series keys, branches, frequencies and units are the catalog's (so routes, flows and nowcasts look like the real
site), but every label is prefixed "[syntetisk]", every source and licence is a test text and every value is drawn
from a seeded random walk. Two series are withheld (publish=False) to exercise the licence gate, and their values
are drawn far from everything else so a value leak would be found by the tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ai_tracker import catalog
from ai_tracker.state import snapshot as S
from ai_tracker.state.measures import Context

TODAY = "2026-11-24"
HISTORY_FROM = "2025-06"
BUILT_UTC = "2026-11-24T00:00:00Z"
GIT_SHA = "fixture"
FETCHED = pd.Timestamp("2026-11-23")
SOURCE = "Syntetisk testkälla"
LICENSE = "CC BY 4.0 (syntetisk testdata, inte verklig data)"

# key -> (start, end, growth per period, volatility, level, publish)
SERIES: dict[str, tuple] = {
    "g1_epoch_eci_frontier": ("2019-01-06", "2026-11-15", 0.004, 0.01, 100.0, True),
    "g2_price_at_capability_gpqa": ("2020-01", "2026-09", -0.04, 0.05, 50.0, True),
    "btos_ai_use_v3": ("2023-09-24", "2026-11-08", 0.002, 0.01, 8.0, True),
    "g3_pypi_openai_wed": ("2020-01-08", "2026-11-11", 0.01, 0.05, 1e5, True),
    "g3_wiki_chatgpt_en": ("2022-12-04", "2026-11-15", 0.002, 0.06, 3e5, True),
    "rev_aws": ("2014Q1", "2026Q3", 0.04, 0.02, 1e3, True),
    "rev_google_cloud": ("2017Q1", "2026Q3", 0.06, 0.03, 9e2, True),
    "rev_msft_cloud": ("2016Q1", "2026Q3", 0.05, 0.02, 4e3, True),
    "rev_nvda_datacenter": ("2015Q1", "2026Q3", 0.07, 0.08, 3e2, True),
    "rpo_hyp4": ("2018Q1", "2026Q3", 0.05, 0.03, 1e5, True),
    "capex_hyp4": ("2012Q1", "2026Q3", 0.04, 0.05, 5e3, True),
    "us_constr_datacenter": ("2014-01", "2026-09", 0.01, 0.02, 1e4, True),
    "tsmc_revenue_m": ("2010-01", "2026-10", 0.01, 0.06, 4e4, True),
    "us_imports_tw_m": ("2012-01", "2026-09", 0.008, 0.05, 3e3, True),
    "us_ip_semis_m": ("2010-01", "2026-10", 0.005, 0.01, 80.0, True),
    "eia930_avg_pjm_dom_m": ("2016-01", "2026-10", 0.004, 0.03, 9e3, True),
    "us_elec_sales_com_va_m": ("2010-01", "2026-08", 0.004, 0.04, 3e3, True),
    "ai_postings_share_us_d": ("2020-02-01", "2026-11-20", 0.0003, 0.004, 2.0, True),
    "g9_epoch_notable_models": ("2015-01", "2026-10", 0.01, 0.15, 10.0, True),
    "x_capex_cloud": ("2017Q1", "2026Q3", 0.0, 0.03, 0.5, True),
    "g9_arxiv_cs_lg": ("2012-01", "2026-10", 0.015, 0.04, 7.77777e6, False),
    "g9_arxiv_cs_ai": ("2012-01", "2026-10", 0.015, 0.04, 6.66666e6, False),
    "us_ip_computers_m": ("2010-01", "2026-10", 0.003, 0.012, 95.0, True),  # last: earlier seeds stay unchanged
}
WITHHELD = [k for k, v in SERIES.items() if not v[5]]
REVISED = {"us_ip_semis_m": 3, "ai_postings_share_us_d": 3, "tsmc_revenue_m": 2}  # vintages per period
D_REISSUE = ["2026-06-01", "2026-09-01"]  # full re-issues of the daily series
LAG_DAYS = {"D": 3, "W": 4, "2W": 4, "M": 14, "Q": 30, "A": 60}
CORE = {
    "G1": ["g1_epoch_eci_frontier"],
    "G2": ["g2_price_at_capability_gpqa"],
    "G3": ["btos_ai_use_v3", "g3_pypi_openai_wed", "g3_wiki_chatgpt_en"],
    "G4": ["rev_aws", "rev_google_cloud", "rev_msft_cloud", "rev_nvda_datacenter", "rpo_hyp4"],
    "G5": ["capex_hyp4", "us_constr_datacenter"],
    "G6": ["tsmc_revenue_m", "us_ip_semis_m", "us_ip_computers_m", "us_imports_tw_m"],
    "G7": ["eia930_avg_pjm_dom_m", "us_elec_sales_com_va_m"],
    "G8": ["ai_postings_share_us_d"],
    "G9": ["g9_arxiv_cs_lg", "g9_arxiv_cs_ai", "g9_epoch_notable_models"],
}
# Source families (index v2) as in the register's table, restricted to the synthetic core series: G6 has a family
# of two published series (Fed G.17), G9 a family of the two withheld arXiv series (counted, never named).
FAMILIES = {
    "G1": {"g1_epoch_eci": ["g1_epoch_eci_frontier"]},
    "G2": {"g2_price_at_capability": ["g2_price_at_capability_gpqa"]},
    "G3": {"btos_ai_use": ["btos_ai_use_v3"], "g3_pypi": ["g3_pypi_openai_wed"], "g3_wiki": ["g3_wiki_chatgpt_en"]},
    "G4": {k: [k] for k in CORE["G4"]},
    "G5": {k: [k] for k in CORE["G5"]},
    "G6": {"tsmc_revenue_m": ["tsmc_revenue_m"], "us_ip_g17": ["us_ip_semis_m", "us_ip_computers_m"],
           "us_imports_ft900": ["us_imports_tw_m"]},
    "G7": {"eia930_avg": ["eia930_avg_pjm_dom_m"], "us_elec_sales_com": ["us_elec_sales_com_va_m"]},
    "G8": {"ai_postings_share": ["ai_postings_share_us_d"]},
    "G9": {"g9_arxiv": ["g9_arxiv_cs_lg", "g9_arxiv_cs_ai"], "g9_epoch_notable_models": ["g9_epoch_notable_models"]},
}
RECONCILIATIONS = ["x_capex_cloud"]


def specs() -> dict[str, catalog.Spec]:
    real = catalog.by_key()
    out = {}
    for key, (*_, publish) in SERIES.items():
        r = real[key]
        out[key] = catalog.Spec(key=key, branch=r.branch, label=f"[syntetisk] {r.label}", unit=r.unit, freq=r.freq,
                                source=SOURCE, fetch=lambda: pd.Series(dtype=float), lag_days=LAG_DAYS[r.freq],
                                license=LICENSE if publish else "unverified: syntetisk testserie som hålls inne",
                                publish=publish, revised=key in REVISED, question=f"Syntetisk fråga om {r.label}?")
    return out


def _periods(start: str, end: str, freq: str) -> pd.PeriodIndex:
    if freq == "2W":
        return pd.period_range(start, end, freq="W-SUN")[::2]
    return pd.period_range(start, end, freq=catalog.FREQS[freq])


def table() -> pd.DataFrame:
    sp = specs()
    parts = []
    for i, (key, (start, end, g, vol, level, _pub)) in enumerate(SERIES.items()):
        freq = sp[key].freq
        rng = np.random.default_rng(1000 + i)
        periods = _periods(start, end, freq)
        base = level * np.exp(np.cumsum(g + vol * rng.standard_normal(len(periods))))
        if sp[key].unit.startswith("%"):
            base = np.clip(base, 0.1, 99.0)
        first = pd.DatetimeIndex(periods.end_time.normalize()) + pd.Timedelta(days=LAG_DAYS[freq])
        n_vint = REVISED.get(key, 1)
        for v in range(n_vint):
            # vintage v: the first release, then revisions published 30 and 90 days later (only for periods
            # whose revision date is not after the fetch date)
            # (a daily series is re-issued in full on fixed fetch dates instead, like the job-postings source)
            if freq == "D" and v:
                kf = pd.DatetimeIndex(np.maximum(first.to_numpy(), np.datetime64(D_REISSUE[v - 1])))
            else:
                kf = first + pd.Timedelta(days=[0, 30, 90][v])
            vals = base * (1 + (0.01 * v * rng.standard_normal(len(periods)) if v else 0))
            keep = (kf <= FETCHED) & ((kf > first) if v else True)  # a revision is a new version, never a duplicate
            parts.append(pd.DataFrame({"series": key, "freq": freq, "period": [str(p) for p in periods[keep]],
                                       "value": vals[keep], "known_from": kf[keep],
                                       "source": "release" if v == 0 else "revision", "fetched_at": FETCHED}))
    t = pd.concat(parts, ignore_index=True)
    t.loc[(t.series == "g9_epoch_notable_models") & (t.period < "2019-01"), "source"] = "backfill"
    return t


def context(root: Path) -> Context:
    return Context(table(), specs=specs(), derived={}, core={k: list(v) for k, v in CORE.items()},
                   forecasts=root / "forecasts", selection=lambda when: [], reconciliations=list(RECONCILIATIONS),
                   families={k: {f: list(e) for f, e in v.items()} for k, v in FAMILIES.items()})


def write_inputs(root: Path, ctx: Context) -> dict:
    """Forecast files, a live snapshot (2026-10, with a C4 section) and one letter and report under `root`."""
    fc = root / "forecasts" / "n2"
    fc.mkdir(parents=True, exist_ok=True)
    (fc / "2026-09.json").write_text(json.dumps({
        "nowcast": "N2", "target": "tsmc_revenue_m", "month": "2026-09", "origin": "2026-10-05", "champion": "B3",
        "value": 41000.0, "variants": {"B0": 40100.0, "B1": 40500.0, "V1": 40600.0, "B2": 41200.0, "B3": 41000.0},
        "distribution": {"models": {"B3": {"intervals": {"50": [39500.0, 42600.0], "80": [38100.0, 44100.0],
                                                         "95": [36400.0, 46200.0]}}}},
        "inputs": [{"series": "g9_arxiv_cs_lg", "period": "2026-08", "value": 1.0, "known_from": "2026-09-10"}],
    }), encoding="utf-8")
    d2 = root / "forecasts" / "d2"
    d2.mkdir(parents=True, exist_ok=True)
    (d2 / "2026-10-20.json").write_text(json.dumps(_d2_file(), ensure_ascii=False), encoding="utf-8")
    snaps = root / "snapshots"
    snaps.mkdir(parents=True, exist_ok=True)
    snap = S.build("2026-10-31", ctx=ctx)
    snap.update(created_utc=BUILT_UTC, git_sha=GIT_SHA, register_sha256="0" * 64)
    snap["regime"] = {"spec_version": "c4-v1", "model": "C4",
                      "ms": {"capex": {"p_slow": 0.12, "state": "expansion", "shift": None, "n_months": 140,
                                       "first_month": "2014-12", "reason": ""},
                             "demand": {"p_slow": 0.83, "state": "inbromsning", "shift": "inbromsning",
                                        "n_months": 96, "first_month": "2018-01", "reason": ""}},
                      "bocpd": [{"series": "rev_google_cloud", "branch": "G4", "latest_period": "2026Q3",
                                 "p_recent": 0.61, "break": True},
                                {"series": "g9_arxiv_cs_lg", "branch": "G9", "latest_period": "2026-10",
                                 "p_recent": 0.7, "break": True}]}
    (snaps / "2026-10.json").write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    letters = root / "letters"
    letters.mkdir(parents=True, exist_ok=True)
    (letters / "2026-10.md").write_text("# Månadsbrev oktober 2026 (syntetiskt)\n\nSyntetisk text för fixturer. "
                                        "Av 6 grenar med tillstånd …\n\n## Grenarna\n\n- G6: stabil\n",
                                        encoding="utf-8")
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "2026Q3.md").write_text("# Kvartalsrapport 2026Q3 (syntetisk)\n\nSyntetisk text för fixturer.\n",
                                       encoding="utf-8")
    return {"snapshots_dir": snaps, "forecasts_dir": root / "forecasts", "letters_dir": letters,
            "reports_dir": reports}


def _d2_file() -> dict:
    """A D2 live file (nowcast.horizon_live layout) with synthetic paths and intervals for both targets."""
    from ai_tracker.nowcast import horizon, horizon_live

    targets = {}
    for i, (name, tg) in enumerate(horizon.TARGETS.items()):
        base_q, base_v = pd.Period("2026Q2", "Q"), [52000.0, 61000.0][i]
        paths, dist = {}, {}
        for h in horizon.HORIZONS:
            champ = horizon_live.CHAMPION[name][horizon_live.group_of(h)]
            v = round(base_v * 1.04 ** h, 1)
            paths[str(h)] = {"quarter": str(base_q + h), "group": horizon_live.group_of(h), "champion": champ,
                             "value": v, "models": {m: round(v * (1 + 0.01 * (j - 1)), 1)
                                                    for j, m in enumerate(tg.models)}}
            w = 0.03 * h ** 0.5
            dist[str(h)] = {"models": {champ: {"intervals": {
                k: [round(v * (1 - z * w), 1), round(v * (1 + z * w), 1)]
                for k, z in (("50", 0.67), ("80", 1.28), ("95", 1.96))}}}}
        targets[name] = {"target": tg.key, "base": str(base_q), "base_value": base_v, "paths": paths,
                         "distribution": dist}
    return {"family": "D2", "origin": "2026-10-20", "targets": targets}


def calibration() -> dict:
    """A synthetic backtest calibration for N2 (the shape of site.probabilities.backtest_calibration)."""
    rows = []
    for model, cov, crps in (("B3", (0.43, 0.78, 0.95), 2.1), ("B1", (0.52, 0.81, 0.94), 2.6)):
        row = {"model": model, "n": 94, "first": "2019-01", "last": "2026-09", "n_student_t": 94, "n_empirical": 0,
               "crps": crps, "calibrated": model == "B1", "pit_mean": 0.48, "pit_var": 0.07}
        for k, c in zip(("50", "80", "95"), cov):
            row[f"coverage_{k}"] = c
            row[f"band_{k}"] = {"50": [0.42, 0.58], "80": [0.74, 0.86], "95": [0.91, 0.98]}[k]
            row[f"holm_{k}"] = 0.04 if model == "B3" and k == "50" else 0.6
        rows.append(row)
    return {"n2": {"available": True, "rows": rows, "n_periods": 94, "first": "2019-01", "last": "2026-09",
                   "best_baseline": "B1", "champion_mae": {"mae": 5.4, "n": 94, "first": "2019-01", "last": "2026-09"},
                   "error": None}}
