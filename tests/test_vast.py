"""vast.ai: blocked by terms (no collector, no catalog series); the aggregation rule leaks no identifiers."""

from __future__ import annotations

import pytest

from ai_tracker import catalog
from ai_tracker.sources import vast


def offer(machine, gpu, n, dph, ram=81559, verification="verified", **kw):
    return {"id": 1000 + machine * 10 + n, "machine_id": machine, "host_id": 555, "hostname": "host.example",
            "public_ipaddr": "203.0.113.7", "geolocation": "Somewhere, US", "gpu_name": gpu, "gpu_ram": ram,
            "num_gpus": n, "dph_total": dph, "verification": verification, "rentable": True, "is_bid": False, **kw}


OFFERS = [
    offer(1, "H100 SXM", 1, 2.0), offer(1, "H100 SXM", 2, 4.2),  # same machine: smallest offer counts
    offer(2, "H100 SXM", 2, 5.0),                               # 2.5 per GPU
    offer(3, "H100 SXM", 4, 12.0),                              # 3.0 per GPU
    offer(4, "H100 SXM", 1, 9.0, verification="unverified"),    # excluded
    offer(5, "H100 SXM", 1, 9.0, rentable=False),               # excluded
    offer(6, "A100 SXM4", 1, 1.0, ram=81920), offer(7, "A100 PCIE", 1, 1.4, ram=81920),
    offer(8, "A100 SXM4", 1, 0.5, ram=40960),                   # 40 GB: not A100 80GB
]


def test_aggregate_stats():
    agg = vast.aggregate(OFFERS)
    assert agg["h100_sxm"] == {"n_offers": 3.0, "median": 2.5, "p25": 2.25, "p75": 2.75}
    assert agg["a100_80gb"]["n_offers"] == 2.0 and agg["a100_80gb"]["median"] == pytest.approx(1.2)
    assert agg["h200"] == {"n_offers": 0.0}
    assert vast.aggregate([])["rtx4090"] == {"n_offers": 0.0}


def test_aggregate_leaks_no_identifiers():
    agg = vast.aggregate(OFFERS)
    assert set(agg) == set(vast.MODELS)
    for stats in agg.values():
        assert set(stats) <= set(vast.STATS)
        assert all(isinstance(v, float) for v in stats.values())
    text = repr(agg)
    for needle in ("203.0.113.7", "host.example", "555", "Somewhere", "1010"):
        assert needle not in text


def test_blocked_no_collector():
    with pytest.raises(PermissionError):
        vast.fetch()
    assert not [s for s in catalog.ALL if "vast" in s.key or "vast" in s.source.lower()]
