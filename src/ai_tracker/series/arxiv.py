"""arXiv submissions in cs.AI, cs.LG and cs.CL (G9). Counted by primary category; see sources/arxiv.py."""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import arxiv

LICENSE = ("unverified: arXiv metadata CC0 per arXiv's API terms, which could not be read "
           "(arxiv.org/info.arxiv.org refused by the sandbox)")
_NOTE = ("Inlämningsmånad (submittedDate, v1). known_from = månadsslut + 7 dagar; månaden hämtas om tills den är "
         "60 dagar gammal. Nivån är inte avstämd mot arXivs egen statistik (arxiv.org blockeras).")


def _spec(key: str, kind: str, label: str, question: str, extra: str = "") -> Spec:
    return Spec(key=key, branch="G9", label=label, unit="antal artiklar", freq="M", source="arXiv API",
                fetch=partial(arxiv.monthly, kind), lag_days=7, license=LICENSE, revised=True, publish=False,
                question=question, note=(extra + " " + _NOTE).strip())


SPECS = [
    _spec("g9_arxiv_ai_ml_submissions", "primary_all", "arXiv: nya artiklar i cs.AI, cs.LG, cs.CL (primär kategori)",
          "Hur snabbt växer AI-forskningen?", "Huvudserien. Summa av de tre primära kategorierna."),
    _spec("g9_arxiv_cs_ai", "cs.AI", "arXiv: nya artiklar, primär kategori cs.AI", "Delserie cs.AI."),
    _spec("g9_arxiv_cs_lg", "cs.LG", "arXiv: nya artiklar, primär kategori cs.LG", "Delserie cs.LG."),
    _spec("g9_arxiv_cs_cl", "cs.CL", "arXiv: nya artiklar, primär kategori cs.CL", "Delserie cs.CL."),
    _spec("g9_arxiv_ai_ml_listed", "listed", "arXiv: artiklar listade i cs.AI, cs.LG eller cs.CL (inkl. korslistade)",
          "Hur stor är AI-forskningens räckvidd i andra fält?",
          "Unionen inklusive korslistningar från andra primärkategorier, varje artikel en gång."),
]
