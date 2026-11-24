"""G1: SWE-bench Verified leaderboard frontier from the experiments repo's git history (docs/kallor/g1g2_nya.md)."""

from __future__ import annotations

from ai_tracker.catalog import Spec
from ai_tracker.sources import swebench

SPECS = [
    Spec(key="g1_swebench_verified_top", branch="G1", label="SWE-bench Verified: högsta andel lösta uppgifter",
         unit="andel (0–1)", freq="M", source="SWE-bench/experiments (git-historik)", fetch=swebench.frontier,
         lag_days=1, license=swebench.LICENSE, revised=True, publish=False,
         question="Hur stor andel verkliga GitHub-ärenden löser det bästa inskickade systemet?",
         note="Bästa resultat i tavlan enligt sista commit på main ≤ månadsslut; known_from = månadsslut + 1. "
              "Historik från 2024-10-15 (repot återskapades). Från 2025-11-18 tas bara akademiska bidrag emot, "
              "och få bidrag sedan 2026-01. Ingen licensfil: publiceras inte. Se docs/kallor/g1g2_nya.md"),
]
