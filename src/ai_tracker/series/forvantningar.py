"""External expectations (L9, G9): one series per selected prediction-market question.

The questions come from sources/forvantningar_urval.json (selection rule in docs/kallor/forvantningar.md). Not core
series: no rate is computed until gate G-A registers them.
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import forvantningar as fv

TOPIC_LABEL = {"T1": "förmåga", "T2": "bolag", "T3": "investeringar", "T4": "exportkontroller", "T5": "reglering"}


def key(q: dict) -> str:
    return f"g9_exp_{'mf' if q['platform'] == 'manifold' else 'pm'}_{q['id']}"


def spec(q: dict) -> Spec:
    closed = fv.is_closed(q)
    common = dict(key=key(q), branch="G9", unit="sannolikhet (0–1)", lag_days=1, revised=False, publish=False,
                  closed=closed,
                  question=f"Förväntning ({TOPIC_LABEL[q['topic']]}): {q['title']}")
    why = (f"Avslutad: frågan {q['status']}, stängning {q['close']}. " if closed else "")
    if q["platform"] == "manifold":
        return Spec(label=f"Manifold: {q['title']}", freq="D", source=f"Manifold {q['resolution_url']}",
                    fetch=partial(fv.manifold_series, q), license=fv.LICENSE_MANIFOLD,
                    note=why + "Dagens sista sannolikhet (probAfter) ur marknadens handel, känd från dagen efter "
                              f"(UTC). Ämne {q['topic']}, vald {q['selected_on']}.", **common)
    return Spec(label=f"Polymarket: {q['title']}", freq="W", source=f"Polymarket {q['resolution_url']}",
                fetch=partial(fv.polymarket_series, q), license=fv.LICENSE_POLYMARKET,
                note=why + "Egen ögonblicksbild av Ja-priset (gamma-api) vid första hämtningen efter veckans slut; "
                           "ingen historik (clob.polymarket.com nås inte). known_from = hämtdagen. "
                           f"Ämne {q['topic']}, vald {q['selected_on']}.", **common)


SPECS = [spec(q) for q in fv.load_urval()]
