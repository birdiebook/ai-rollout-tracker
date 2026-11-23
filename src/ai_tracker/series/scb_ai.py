"""G3: SCB, share of Swedish enterprises (10+ employees) using at least one AI technology, annual.

Two series, not spliced: TAB6405 (2023-2025, SNI 10-63, 68-75, 77-82, 95.1) and TAB6814 (2026-, NACE Rev.
2.1 with all surveyed industries, including agriculture, mining and finance). The table change widens the
population behind "totalt 10 eller fler anställda", so the 2025->2026 step is not a like-for-like change.
2021 is '..' and 2022 not asked, so v1 starts 2023 (SNI 75 is included from 2023).
"""

from __future__ import annotations

from ai_tracker.catalog import Spec
from ai_tracker.sources import scb_ai

LICENSE = ("CC0 1.0. SCB terms: \"Statistik och geodata som SCB tillgängliggör som öppna data i "
           "statistikdatabasen och i vår geodataplattform har licensen Creative commons 0 1.0 Universal, "
           "CC0.\" Källa anges: \"Källa: SCB\".")
ANY_AI = "0080"  # användning av minst en AI-teknik
TEN_PLUS = "Tot250"  # totalt 10 eller fler anställda
TABLES = {  # version -> (table, ContentsCode for the share, first year)
    "v1": ("TAB6405", "000007JC", 2023),
    "v2": ("TAB6814", "000008LC", 2026),
}


def fetch(version: str):
    table, contents, first = TABLES[version]
    long = scb_ai.fetch_table(table, {"TypAvTeknik": ANY_AI, "Redovisningsgrupp": TEN_PLUS,
                                      "ContentsCode": contents, "Tid": "*"})
    s = scb_ai.share(long, {"TypAvTeknik": ANY_AI, "Redovisningsgrupp": TEN_PLUS}, contents)
    return s[s.index.year >= first]


def _spec(version: str, lag_days: int, label_extra: str, note: str, closed: bool = False) -> Spec:
    return Spec(
        key="scb_ai_ent_se" + ("" if version == "v1" else "_nace21"),
        branch="G3",
        label="Andel företag (10+ anställda) i Sverige som använder minst en AI-teknik" + label_extra,
        unit="% av företag",
        freq="A",
        source=f"SCB, It-användning i företag (NV0116), {TABLES[version][0]}",
        fetch=lambda: fetch(version),
        lag_days=lag_days,
        license=LICENSE,
        revised=True,  # corrections happen (TAB6405 2026-05-05); no version history in the API
        publish=True,
        question="Hur stor andel av svenska företag använder AI?",
        note=note,
        closed=closed,
    )


SPECS = [
    _spec("v1", 0, ", 2023–2025 (SNI 2007-täckning)",
          "TAB6405. Avslutad: tabellen ersattes av TAB6814 (NACE 2.1) från referensår 2026. known_from = 31 dec "
          "referensåret (konservativt: publiceringsdag för 2023–2024 ej belagd). Korrigeringen 2026-05-05 gällde "
          "0–9 anställda, inte den här serien.", closed=True),
    _spec("v2", -50, ", från 2026 (NACE 2.1-täckning)",
          "TAB6814, publicerad 2026-11-05 (tabellens updated). known_from = 11 nov referensåret. "
          "Bredare branschtäckning än v1: skarvas inte."),
]
