"""Epoch AI series for G1 (capability), G2 (hardware cost) and G9 (models database).

Benchmarks: selected by the registered rule (docs/mattregister.md, entries 2026-11-23; result in the dated note
"G1: urvalsregeln tillämpad (spår F6)"). The selection is fixed here as data; `python -m ai_tracker.series.epoch_hub`
recomputes the rule and the successor check so a change is visible, never applied silently.

`<valda>` in the register (G1 core series `g1_epoch_bench_frontier_<valda>`) resolves through `selected_on`:
the registered list, with each entry of REPLACEMENTS applied from its effective date. The effective date is the
first day on which the replaced benchmark was retired or saturated with what was known that day (see
docs/kallor/epoch_arxiv.md). Between that day and the registration the state engine already stops counting the
benchmark (state.branch.benchmark_guard), so a registration only adds the successor.
"""

from __future__ import annotations

from functools import partial

import pandas as pd

from ai_tracker.catalog import Spec
from ai_tracker.sources import epoch_hub as e

# Result of selection_table() on 2026-11-23 (note "G1: urvalsregeln tillämpad (spår F6)"). Order = rank.
# Only two families were eligible, so the third slot is empty.
SELECTED_BENCHMARKS = {
    "frontiermath_erdos": "FrontierMath Erdős",
    "spireclimb": "SpireClimb",
}

# Successor replacements, registered when they happen: (effective date YYYY-MM-DD, replaced, successor).
# Empty on 2026-11-23: the rule found no selected benchmark retired or saturated.
REPLACEMENTS: list[tuple[str, str, str]] = []
SUCCESSOR_NAMES: dict[str, str] = {}  # slug -> label for each successor in REPLACEMENTS

# The earlier selection (fas 2 I5) that Epoch has superseded: kept as closed catalog entries (description only).
CLOSED_BENCHMARKS = {
    "frontiermath": ("FrontierMath (2025-02-28, privat, nivå 1–3)", "FrontierMath-Tiers-1-3-v2-Private"),
    "frontiermath_tier_4": ("FrontierMath nivå 4 (2025-07-01, privat)", "FrontierMath-Tier-4-v2-Private"),
}


def selected_on(when) -> list[str]:
    """The selected benchmarks (file stems) on `when`: the registered list with REPLACEMENTS applied from their
    effective dates. Dates before the selection date get the registered list (chosen on coverage and metadata,
    not on the scores)."""
    when = pd.Timestamp(when)
    out = list(SELECTED_BENCHMARKS)
    for day, old, new in sorted(REPLACEMENTS):
        if pd.Timestamp(day) <= when and old in out:
            out[out.index(old)] = new
    return out


_BENCH_NOTE = ("Epochs egna körningar. En körning är känd från `Started at` + 30 dagar, och från andra hämtningen "
               "från max(det, first_seen). Månad m (bästa resultat bland körningar startade före månadsslut) får "
               "known_from = första dagen i m+1 + 30 dagar, och senare kända körningar ger nya versioner. Urval enligt "
               "måttregistret 2026-11-23.")


def _bench_specs() -> list[Spec]:
    specs = []
    names = {**SELECTED_BENCHMARKS, **SUCCESSOR_NAMES, **{k: v[0] for k, v in CLOSED_BENCHMARKS.items()}}
    for slug, name in names.items():
        closed = slug in CLOSED_BENCHMARKS
        note = _BENCH_NOTE
        if closed:
            note += (f" Avslutad: Epoch har ersatt benchmarken (superseded_by {CLOSED_BENCHMARKS[slug][1]}) och "
                     "inte kört den sedan 2026-06-08. Ersatt i urvalet 2026-11-23 (spår F6). Bara beskrivning.")
        for column, key, label, unit in (
                ("frontier", f"g1_epoch_bench_frontier_{slug}", f"{name}: bästa resultat", "andel rätt (0–1)"),
                ("runs", f"g1_epoch_bench_runs_{slug}", f"{name}: Epoch-körningar per månad", "antal körningar")):
            specs.append(Spec(
                key=key, branch="G1", label=label, unit=unit, freq="M", source="Epoch AI benchmarkhubben",
                fetch=partial(e.benchmark_series, slug, column, key), lag_days=31, license=e.LICENSE,
                revised=True, publish=True, closed=closed,
                question="Höjs förmågans front på en benchmark som inte är mättad?" if column == "frontier"
                else "Hur tät är Epochs mätning (täckning bakom frontvärdet)?",
                note=note))
    return specs


def _eci():
    return e.eci_frontier(e.benchmark_files())


def _notable():
    return e.notable_per_month(e.models_frame(e.model_files(), "notable_ai_models.csv"))


def _open_share():
    return e.open_weights_share(e.models_frame(e.model_files(), "notable_ai_models.csv"))


def _compute():
    return e.train_compute_frontier(e.models_frame(e.model_files(), "all_ai_models.csv"))


def _hw():
    return e.hw_price_performance(e._csv(e.hardware_files(), "ml_hardware.csv"))


_BACKFILL_NOTE = ("Historiken är återfylld (source=backfill, known_from nominellt periodslut + 7 dagar) och "
                  "revideras; bara egna veckovisa ögonblicksbilder har ärlig known_from (måttregistret 2026-11-23).")

SPECS = _bench_specs() + [
    Spec(key="g1_epoch_eci_frontier", branch="G1", label="Epoch Capabilities Index: högsta värde",
         unit="ECI-poäng", freq="W", source="Epoch AI benchmarkhubben (ECI)", fetch=_eci, lag_days=1,
         license=e.LICENSE, revised=True, publish=True,
         question="Flyttar den sammanvägda förmågefronten?",
         note="Högsta ECI bland modeller släppta t.o.m. veckans slut (vecka mån–sön), i dagens skattning. Hämtas på "
              "måndagar, så known_from = dagen efter veckans slut. " + _BACKFILL_NOTE.replace("+ 7 dagar", "+ 1 dag")),
    Spec(key="g1_epoch_train_compute_frontier", branch="G1", label="Största träningsberäkning",
         unit="FLOP", freq="M", source="Epoch AI modelldatabasen (all_ai_models)", fetch=_compute, lag_days=7,
         license=e.LICENSE, revised=True, publish=True,
         question="Växer beräkningen bakom de största modellerna i samma takt?",
         note="Största `Training compute (FLOP)` bland modeller publicerade t.o.m. månadsslut. " + _BACKFILL_NOTE),
    Spec(key="g9_epoch_notable_models", branch="G9", label="Notable-modeller publicerade per månad",
         unit="antal modeller", freq="M", source="Epoch AI modelldatabasen (notable_ai_models)", fetch=_notable,
         lag_days=7, license=e.LICENSE, revised=True, publish=True,
         question="Hur många betydande modeller släpps?",
         note="Från 2010-01. Senaste månaderna är ofullständiga (inmatningseftersläpning), inte en trend. "
              + _BACKFILL_NOTE),
    Spec(key="g9_epoch_open_weights_share", branch="G9", label="Andel notable-modeller med öppna vikter",
         unit="andel (0–1)", freq="Q", source="Epoch AI modelldatabasen (notable_ai_models)", fetch=_open_share,
         lag_days=7, license=e.LICENSE, revised=True, publish=True,
         question="Håller öppna modeller jämna steg med slutna?",
         note="Andel `Open model weights?` = Yes bland modeller där fältet är ifyllt, per publiceringskvartal, "
              "från 2015Q1. " + _BACKFILL_NOTE),
    Spec(key="g2_epoch_hw_price_performance", branch="G2", label="ML-hårdvara: bästa FLOP/s per dollar (16-bit)",
         unit="FLOP/s per USD", freq="A", source="Epoch AI ML-hårdvara", fetch=_hw, lag_days=7,
         license=e.LICENSE, revised=True, publish=True,
         question="Hur snabbt faller kostnaden för beräkning?",
         note="Bästa (Tensor-)FP16/BF16 FLOP/s per releasepris bland acceleratorer släppta t.o.m. årets slut, "
              "från 2016. Glest (få priser per år). " + _BACKFILL_NOTE),
]


def check(today=None) -> tuple[pd.DataFrame, list[str], list[tuple[str, str | None, str]]]:
    """(selection table on the selection date, selection today, successor swaps due today)."""
    files = e.benchmark_files()
    runs, sup = e.epoch_runs(files), e.superseded_by(files)
    table = e.selection_table(runs, e.SELECTION_DATE, sup)
    today = pd.Timestamp(today or pd.Timestamp.now(tz="UTC").date())
    retired = [old for _d, old, _n in REPLACEMENTS]
    current = selected_on(today)
    _new, swaps = e.apply_successor_rule(current, runs, today, retired=retired, superseded=sup)
    return table, current, swaps


if __name__ == "__main__":
    with pd.option_context("display.width", 250, "display.max_colwidth", 90):
        table, current, swaps = check()
        print("Rule on", e.SELECTION_DATE)
        print(table.drop(columns=["active", "retired"]).to_string())
        print("Selected today:", current)
        print("Successor check today:", swaps or "no replacement due")
