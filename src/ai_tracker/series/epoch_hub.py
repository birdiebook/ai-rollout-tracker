"""Epoch AI series for G1 (capability), G2 (hardware cost) and G9 (models database).

Benchmarks: selected by the registered rule (docs/mattregister.md 2026-11-23, applied in the dated note under
Ändringar). The selection is fixed here as data; `python -m ai_tracker.series.epoch_hub` recomputes the rule and
the successor check so a change is visible, never applied silently.
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import epoch_hub as e

# Result of select_benchmarks() on 2026-11-23 (see the note in docs/mattregister.md). Order = rank.
SELECTED_BENCHMARKS = {
    "frontiermath": "FrontierMath (2025-02-28, privat, nivå 1–3)",
    "frontiermath_tier_4": "FrontierMath nivå 4 (2025-07-01, privat)",
    "frontiermath_erdos": "FrontierMath Erdős",
}

_BENCH_NOTE = ("Epochs egna körningar; known_from = första dagen i månaden efter (bara körningar med `Started at` "
               "före månadsslut räknas). Urval enligt måttregistret 2026-11-23.")


def _bench_specs() -> list[Spec]:
    specs = []
    for slug, name in SELECTED_BENCHMARKS.items():
        for column, key, label, unit in (
                ("frontier", f"g1_epoch_bench_frontier_{slug}", f"{name}: bästa resultat", "andel rätt (0–1)"),
                ("runs", f"g1_epoch_bench_runs_{slug}", f"{name}: Epoch-körningar per månad", "antal körningar")):
            specs.append(Spec(
                key=key, branch="G1", label=label, unit=unit, freq="M", source="Epoch AI benchmarkhubben",
                fetch=partial(e.benchmark_series, slug, column, key), lag_days=1, license=e.LICENSE,
                revised=True, publish=True,
                question="Höjs förmågans front på en benchmark som inte är mättad?" if column == "frontier"
                else "Hur tät är Epochs mätning (täckning bakom frontvärdet)?",
                note=_BENCH_NOTE))
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


if __name__ == "__main__":
    runs = e.epoch_runs(e.benchmark_files())
    print("Rule on", e.SELECTION_DATE)
    print(e.select_benchmarks(runs).to_string())
    selected, swaps = e.apply_successor_rule(list(SELECTED_BENCHMARKS), runs, "now")
    print("Successor check today:", swaps or "no replacement", "->", selected)
