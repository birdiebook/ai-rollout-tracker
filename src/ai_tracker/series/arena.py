"""G1: Arena (LMArena) frontier ratings, honestly dated (docs/kallor/g1g2_nya.md). Not core series until registered."""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import arena

_COMMON = ("Frontvärde = högsta rating i senaste publicerade topplistan (kategori overall) som var dokumenterad vid "
           "månadsslut; known_from = månadsslut + 1 dag eller senare belägg (git-commit). Tavlor som bara finns i "
           "datasetets bulkuppladdning 2026-04-02 är source=backfill (censurerade). Skalbrott: Elo→BT 2024-01-09, "
           "stilkontroll 2025-05-16, omviktning 2025-07-23. Se docs/kallor/g1g2_nya.md")

SPECS = [
    Spec(key="g1_arena_text_top", branch="G1", label="Arena text: högsta rating",
         unit="Arena-poäng (Elo/Bradley–Terry)", freq="M", source="LMArena (HF-dataset + Space-filer)",
         fetch=partial(arena.series, "text", "top"), lag_days=1, license=arena.LICENSE, revised=True,
         publish=True, question="Hur stark är den bästa chattmodellen enligt mänskliga parvisa omdömen?",
         note=_COMMON),
    Spec(key="g1_arena_text_sc_top", branch="G1", label="Arena text med stilkontroll: högsta rating",
         unit="Arena-poäng (Bradley–Terry)", freq="M", source="LMArena (HF-dataset + Space-filer)",
         fetch=partial(arena.series, "text_style_control", "top"), lag_days=1, license=arena.LICENSE,
         revised=True, publish=True, question="Samma mått rensat för svarens stil och längd (från 2024-08)",
         note=_COMMON),
    Spec(key="g1_arena_text_top_gap_ref", branch="G1",
         label="Arena text: högsta rating minus Mixtral 8x7B Instruct i samma topplista",
         unit="Arena-poäng", freq="M", source="LMArena (HF-dataset + Space-filer)",
         fetch=partial(arena.series, "text", "gap"), lag_days=1, license=arena.LICENSE, revised=True,
         publish=True, question="Frontens avstånd till en fast referensmodell (oberoende av skalans förankring)",
         note="Referensen finns i varje texttavla från 2023-12-15. " + _COMMON),
    Spec(key="g1_arena_webdev_top", branch="G1", label="Arena WebDev (Code Arena): högsta rating",
         unit="Arena-poäng (Bradley–Terry)", freq="M", source="LMArena (HF-dataset)",
         fetch=partial(arena.series, "webdev", "top"), lag_days=1, license=arena.LICENSE, revised=True,
         publish=True, question="Hur bra bygger den bästa modellen webbappar enligt användarnas omdömen?",
         note="Från 2025-11-12; före 2026-04-02 bara bulkuppladdning (backfill). " + _COMMON),
]
