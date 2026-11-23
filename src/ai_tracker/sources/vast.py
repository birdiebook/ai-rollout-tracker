"""vast.ai GPU rental prices: BLOCKED by the terms of service. No collector runs.

vast.ai's Terms of Service (vast.ai/terms, version date 2026-09-01, read 2026-11-23) prohibit, without a
separate written agreement:
- "Engaging in any bulk, systematic, or automated retrieval, collection, copying, downloading,
  harvesting, caching, storage or other extraction of data or other content from the Website to create,
  develop, populate, maintain, or compile, directly or indirectly, a collection, compilation, database,
  dataset, index, benchmark, or directory without written permission from Company."
- "Using any robot, spider, crawler, scraper, script, ... or any other automated method to access, query,
  copy, download, monitor, collect, cache, store or extract data from the Website or Services, except as
  expressly authorized in a separate written agreement with Company."
- using Authorized Data (pricing, availability) "as an input to or for the construction, calculation,
  publication, maintenance, or administration of any index, benchmark, pricing index, price-comparison
  database, or other product or service that measures, compares, tracks, summarizes or reflects pricing".

A daily price collector is exactly that, so it is not built into the catalog or a workflow. Only the
aggregation rule is kept (tested), so that a series can start the day written permission exists:
per GPU model, the median, p25 and p75 of USD per GPU-hour (dph_total / num_gpus) over verified,
rentable on-demand offers, one price per machine (its smallest offer), plus the number of machines.
Host ids, machine ids, hostnames and IP addresses never leave `aggregate`.

The public search API also returns at most 64 offers per query (checked 2026-11-23), so a complete
snapshot would need many sliced queries; that would itself have to be agreed with vast.ai.
"""

from __future__ import annotations

import pandas as pd

BLOCKED = "vast.ai Terms of Service prohibit automated collection and price indices without written agreement"

# series suffix -> (gpu_name values in the API, minimum gpu_ram in MB)
MODELS = {
    "h100_sxm": (("H100 SXM",), 0),
    "h100_pcie": (("H100 PCIE",), 0),
    "h200": (("H200",), 0),
    "a100_80gb": (("A100 SXM4", "A100 PCIE"), 80_000),
    "rtx4090": (("RTX 4090",), 0),
}
STATS = ("median", "p25", "p75", "n_offers")


def aggregate(offers: list[dict], models: dict = MODELS) -> dict[str, dict[str, float]]:
    """{model: {median, p25, p75, n_offers}} from raw offer dicts. Returns numbers only."""
    df = pd.DataFrame([{k: o.get(k) for k in ("machine_id", "gpu_name", "gpu_ram", "num_gpus", "dph_total",
                                                "verification", "rentable", "is_bid")} for o in offers])
    out: dict[str, dict[str, float]] = {}
    if df.empty:
        return {m: {"n_offers": 0.0} for m in models}
    df = df[(df["verification"] == "verified") & (df["rentable"] == True) & (df["is_bid"] != True)  # noqa: E712
            & (pd.to_numeric(df["num_gpus"], errors="coerce") > 0) & pd.to_numeric(df["dph_total"], errors="coerce").gt(0)]
    df = df.assign(per_gpu=df["dph_total"].astype(float) / df["num_gpus"].astype(float))
    # one price per machine: its smallest offer (the API lists 1x, 2x, 4x ... splits of the same machine)
    df = df.sort_values(["machine_id", "num_gpus", "per_gpu"]).drop_duplicates("machine_id")
    for model, (names, min_ram) in models.items():
        p = df[df["gpu_name"].isin(names) & (pd.to_numeric(df["gpu_ram"], errors="coerce") >= min_ram)]["per_gpu"]
        stats = {"n_offers": float(len(p))}
        if len(p):
            stats |= {"median": float(p.median()), "p25": float(p.quantile(0.25)), "p75": float(p.quantile(0.75))}
        out[model] = stats
    return out


def fetch(*_args, **_kwargs):
    raise PermissionError(BLOCKED)
