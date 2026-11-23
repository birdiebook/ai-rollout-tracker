"""METR time horizon: G1 reference series (not a core series, mattregister 2026-11-23)."""

from __future__ import annotations

from ai_tracker.catalog import Spec
from ai_tracker.sources import metr

SPECS = [
    Spec(key="g1_metr_horizon_p50_frontier", branch="G1", label="METR tidshorisont (50 %): högsta värde",
         unit="minuter", freq="M", source="METR time horizon v1.1", fetch=metr.horizon_frontier, lag_days=1,
         license=metr.LICENSE, revised=True, publish=True,
         question="Referens: hur långa uppgifter klarar de bästa agenterna?",
         note="REFERENSSERIE, inte kärnserie. Högsta p50 bland modeller släppta t.o.m. månaden, per "
              "release-månad; known_from = max(datum i sidans uppdateringslogg, 2026-03-03). Fryst sedan "
              "2026-05; värden över 16 h är enligt METR opålitliga."),
]
