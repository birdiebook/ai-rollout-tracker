"""The pre-registered rules of docs/mattregister.md (sections 1, 2, 5 and the "Ändringar" entries) as data.

Everything the state engine needs to know about *which* series and *which* thresholds lives here, so a new
registration (e.g. the G1 and G9 core series) is a data change in this file, not a code change:

- CORE_SERIES mirrors the register's core-series table(s) (section 5) cell by cell, with the register's own
  shorthand: brace lists (`x_{a,b}_m`), the BTOS placeholder `<aktiv regim>` and the G1 placeholder `<valda>`. tests/test_state.py parses the
  register file and asserts that it equals CORE_SERIES, so the two cannot drift apart.
- FAMILIES mirrors the register's source-family table (2026-11-24, diffusion index v2: one vote per source family),
  with the same parity test.
- METHOD_OVERRIDES / AGG_OVERRIDES pin a measure method or aggregation where the default inferred from the
  catalog (unit, branch) is not the registered one.
- BACKFILL_GATED lists series whose backfilled history may only describe, not count, until there are
  24 months of own snapshots (register, change 2026-11-23 on ECI and the Epoch model database).
  BACKFILL_FLAGGED lists backfilled core series that count but carry a flag (training compute).
- DERIVED defines ratio series that are built from two catalog series (capex_ocf_hyp4).
- RECONCILIATIONS lists the A5 reconciliation series (group "Avstämningar"), measured but never counted in a branch.
"""

from __future__ import annotations

import re
from pathlib import Path

from ai_tracker import config

REGISTER_PATH = config.REPO / "docs" / "mattregister.md"

# ------------------------------------------------------------------ section 5: core series per branch
# Mirrors the register table literally (one entry per backticked name in the "Kärnserier" cell).
# tests/test_state.py fails until this structure and the register agree.
CORE_SERIES: dict[str, list[str]] = {
    "G1": ["g1_epoch_bench_frontier_<valda>", "g1_epoch_train_compute_frontier", "g1_epoch_eci_frontier", "g1_arena_text_top"],
    "G2": ["g2_price_at_capability_gpqa"],
    "G3": ["btos_ai_use_<aktiv regim>", "eu_ai_ent_eu27", "eu_ai_ent_se", "g3_npm_{openai,anthropic_sdk,langchain,vercel_ai}_w", "g3_pypi_{openai,anthropic,langchain,llama_index}_wed", "g3_wiki_{chatgpt,llm,genai}_en", "g3_cf_bots_ai_crawler_share", "g3_cf_ai_purpose_user_action"],
    "G4": ["rev_aws", "rev_google_cloud", "rev_msft_cloud", "rev_nvda_datacenter", "rev_orcl_cloud", "rpo_hyp4"],
    "G5": ["capex_hyp4", "us_constr_datacenter", "us_pfi_info_proc_eq_sw", "capex_ocf_hyp4", "capex_orcl"],
    "G6": ["tsmc_revenue_m", "us_ip_semis_m", "us_ip_computers_m", "us_imports_tw_m", "us_imports_kr_m", "rev_amd_datacenter", "rev_avgo_semis", "rev_mrvl_datacenter", "asml_net_sales"],
    "G7": ["us_elec_sales_com_{va,tx,ga,az,or,oh}_m", "eia930_avg_{pjm_dom,erco,azps,soco,srp}_m", "pjm_lf_peak_{dom,rto}_h5"],
    "G8": ["ai_postings_share_{us,gb,de,fr,ca,au,ie,it,nl}_d"],
    "G9": ["g9_arxiv_cs_ai", "g9_arxiv_cs_lg", "g9_arxiv_cs_cl", "g9_epoch_open_weights_share", "g9_epoch_notable_models"],
}

# ------------------------------------------------------------------ source families (register 2026-11-24, index v2)
# Mirrors the register's family table(s) ("| Gren | Källfamilj | Kärnserier |"): per branch, family id -> the core
# entries of that family, written exactly as in CORE_SERIES (a brace entry is one entry and always one family).
# tests/test_state.py parses the register and asserts equality, and that every core entry is in exactly one family.
# A family id with `<valda>` gives one family per selected benchmark (the placeholder replaced by the benchmark).
FAMILIES: dict[str, dict[str, list[str]]] = {
    "G1": {"g1_epoch_bench_<valda>": ["g1_epoch_bench_frontier_<valda>"],
           "g1_epoch_train_compute": ["g1_epoch_train_compute_frontier"],
           "g1_epoch_eci": ["g1_epoch_eci_frontier"],
           "g1_arena_text": ["g1_arena_text_top"]},
    "G2": {"g2_price_at_capability_gpqa": ["g2_price_at_capability_gpqa"]},  # renamed 2026-11-24 (register)
    "G3": {"btos_ai_use": ["btos_ai_use_<aktiv regim>"],
           "eu_ai_ent": ["eu_ai_ent_eu27", "eu_ai_ent_se"],
           "g3_npm": ["g3_npm_{openai,anthropic_sdk,langchain,vercel_ai}_w"],
           "g3_pypi": ["g3_pypi_{openai,anthropic,langchain,llama_index}_wed"],
           "g3_wiki": ["g3_wiki_{chatgpt,llm,genai}_en"],
           "g3_cf_ai_crawler": ["g3_cf_bots_ai_crawler_share"],
           "g3_cf_ai_purpose": ["g3_cf_ai_purpose_user_action"]},
    "G4": {k: [k] for k in ("rev_aws", "rev_google_cloud", "rev_msft_cloud", "rev_nvda_datacenter", "rev_orcl_cloud",
                            "rpo_hyp4")},
    "G5": {k: [k] for k in ("capex_hyp4", "us_constr_datacenter", "us_pfi_info_proc_eq_sw", "capex_ocf_hyp4",
                            "capex_orcl")},
    "G6": {"tsmc_revenue_m": ["tsmc_revenue_m"],
           "us_ip_g17": ["us_ip_semis_m", "us_ip_computers_m"],
           "us_imports_ft900": ["us_imports_tw_m", "us_imports_kr_m"],
           **{k: [k] for k in ("rev_amd_datacenter", "rev_avgo_semis", "rev_mrvl_datacenter", "asml_net_sales")}},
    "G7": {"us_elec_sales_com": ["us_elec_sales_com_{va,tx,ga,az,or,oh}_m"],
           "eia930_avg": ["eia930_avg_{pjm_dom,erco,azps,soco,srp}_m"],
           "pjm_lf_peak": ["pjm_lf_peak_{dom,rto}_h5"]},
    "G8": {"ai_postings_share": ["ai_postings_share_{us,gb,de,fr,ca,au,ie,it,nl}_d"]},
    "G9": {"g9_arxiv": ["g9_arxiv_cs_ai", "g9_arxiv_cs_lg", "g9_arxiv_cs_cl"],
           "g9_epoch_open_weights": ["g9_epoch_open_weights_share"],
           "g9_epoch_notable_models": ["g9_epoch_notable_models"]},
}
INDEX_RULE = "v2"  # the official diffusion index from the snapshot 2026-11-30; v1 is computed and shown alongside
MIN_FAMILIES = 3  # v2: fewer counted families -> index shown, no state
STATE_FEW_FAMILIES = "för få källor"

# "<aktiv regim>": the regime series are <prefix>v<n>; the active one is resolved per computation date.
REGIME_PLACEHOLDER = "<aktiv regim>"
REGIME_SUFFIX = r"v(\d+)"
# "<valda>": the benchmarks selected by the registered rule on the computation date (Context.selection,
# default ai_tracker.series.epoch_hub.selected_on). One series per selected benchmark.
SELECTED_PLACEHOLDER = "<valda>"
# Guard for a selected benchmark (register 2026-11-23): not counted once, with what is known on the date, its
# frontier is > REPLACE_ABOVE or its newest month with an Epoch run ended more than RETIRE_AFTER_DAYS earlier.
BENCH_FRONTIER_PREFIX, BENCH_RUNS_PREFIX = "g1_epoch_bench_frontier_", "g1_epoch_bench_runs_"
REPLACE_ABOVE = 0.90
RETIRE_AFTER_DAYS = 90

# ------------------------------------------------------------------ section 1: measures per series
PACE_LAG = {"M": 12, "Q": 4, "A": 1}  # takt: change over a year
CHANGE_LAG = {"M": 6, "Q": 2, "A": 1}  # förändring i takt: pace now minus pace 6 m / 2 q / 1 y earlier
MIN_HISTORY = {"M": 24, "Q": 8, "A": 5}  # percentiles need at least this many values of the measure
DOUBLING_WINDOW = 24  # months of front values in the log-linear regression (G1, G2)
DOUBLING_CHANGE_LAG = 12  # change in doubling/halving time: now vs 12 months earlier
SUBMONTHLY = {"D", "W", "2W"}  # aggregated to calendar months before any pace is computed

# Methods: "log" (positive quantities, log x100), "share" (percent level, pp), "logit" (bounded 0-1 scores,
# front = running max), "doubling" (G1, front = running max), "halving" (G2 price, front = running min).
# g9_epoch_open_weights_share is a share (unit "andel (0–1)", which would default to logit): register section 1,
# shares in level and percentage points (a 0-1 share is scaled x100). Logit is registered for G1 benchmarks only.
METHOD_OVERRIDES: dict[str, str] = {"g9_epoch_open_weights_share": "share", "g1_arena_text_top": "share"}
AGG_OVERRIDES: dict[str, str] = {}  # "mean" | "sum" for D/W/2W series
# Registered start periods (scale breaks): measures use only periods from here (register 2026-11-24, Arena BT era).
SERIES_START: dict[str, str] = {"g1_arena_text_top": "2024-01"}

# Series that are live nowcast targets: surprise = outcome minus the committed live nowcast (forecasts/<dir>/).
NOWCAST_TARGETS = {"capex_hyp4": "n1", "tsmc_revenue_m": "n2"}

# ------------------------------------------------------------------ backfill exclusion (change 2026-11-23)
# ECI and the Epoch models database (register 2026-11-23, G1/G9 core table): gated. g2_price_at_capability uses ECI.
BACKFILL_GATED: set[str] = {"g2_price_at_capability", "g1_epoch_eci_frontier", "g9_epoch_open_weights_share",
                            "g9_epoch_notable_models"}
# Backfilled core series that count, with a flag (register 2026-11-23: "Träningsberäkningen är bakåtfylld och flaggas").
BACKFILL_FLAGGED: dict[str, str] = {
    "g1_epoch_train_compute_frontier": "bakåtfylld (Epochs modelldatabas, nominellt known_from), räknas enligt "
                                       "registret men flaggas",
}
OWN_SNAPSHOT_MONTHS = 24

# ------------------------------------------------------------------ derived ratio series (section 5, G5)
# key: (numerator, denominator, scale, method, freq, branch). Same version: the ratio is formed whenever either
# component gets a new vintage, with known_from = the later of the two.
DERIVED: dict[str, tuple[str, str, float, str, str, str]] = {
    "capex_ocf_hyp4": ("capex_hyp4", "ocf_hyp4", 100.0, "share", "Q", "G5"),
}

# ------------------------------------------------------------------ A5: reconciliations (register 2026-11-23)
# Derived catalog series (ai_tracker.series.avstamning). Measured like other quarterly series with the registered
# pace "y/y change in log(ratio) x100" (method log, also for x_capex_ocf, whose catalog unit is a percentage),
# change in pace and percentiles as in section 1. Never counted in a branch's diffusion index: they are a separate
# group in the snapshot, the monthly letter and the site.
RECONCILIATIONS: list[str] = ["x_capex_cloud", "x_rpo_cover", "x_nvda_capex", "x_debt_capex", "x_capex_ocf"]
RECONCILIATION_GROUP = "Avstämningar"
METHOD_OVERRIDES.update({k: "log" for k in RECONCILIATIONS})

# ------------------------------------------------------------------ section 2: branch state
DEADBAND = 0.25  # x the series' expanding SD of change in pace
ACCELERATING = 0.67  # index >= -> accelererar
BRAKING = 0.33  # index <= -> bromsar in
MIN_SERIES = 3  # fewer: index shown, no state
MIN_SD_VALUES = 2  # an SD needs at least two values (ddof=1); otherwise no direction

STATE_ACCEL, STATE_STABLE, STATE_BRAKE, STATE_FEW = "accelererar", "stabil", "bromsar in", "för få serier"


# ------------------------------------------------------------------ helpers


def expand(name: str) -> list[str]:
    """Brace expansion as written in the register: `a_{x,y}_b` -> [a_x_b, a_y_b] (one brace group)."""
    m = re.search(r"\{([^{}]+)\}", name)
    if not m:
        return [name]
    return [name[: m.start()] + part.strip() + name[m.end():] for part in m.group(1).split(",")]


def core_entries(branch: str, core: dict[str, list[str]] | None = None) -> list[str]:
    """Expanded register entries for a branch (placeholders still unresolved)."""
    return [k for name in (CORE_SERIES if core is None else core).get(branch, []) for k in expand(name)]


def entry_families(branch: str, core: dict[str, list[str]] | None = None,
                   families: dict[str, dict[str, list[str]]] | None = None) -> dict[str, str]:
    """Expanded core entry -> family id for a branch (register 2026-11-24). A register entry that no family lists is
    a family of its own, named after the entry (only test contexts with their own core lists; the parity tests keep
    the real tables complete). A brace entry is always one family."""
    fams = (FAMILIES if families is None else families).get(branch, {})
    owner = {e: fam for fam, entries in fams.items() for e in entries}
    return {k: owner.get(name, name) for name in (CORE_SERIES if core is None else core).get(branch, [])
            for k in expand(name)}


def parse_families(path: Path | None = None) -> dict[str, dict[str, list[str]]]:
    """Families per branch as written in every '| Gren | Källfamilj | Kärnserier |' table of the register.

    Same rule as parse_register: tables in file order, and a later table that names a branch again replaces that
    branch's families. The family id is the backticked token of the 'Källfamilj' cell, its entries the backticked
    tokens of the 'Kärnserier' cell."""
    text = Path(path or REGISTER_PATH).read_text(encoding="utf-8")
    out: dict[str, dict[str, list[str]]] = {}
    table: dict[str, dict[str, list[str]]] | None = None
    for line in [*text.splitlines(), ""]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else None
        if cells is None:
            if table:
                out.update(table)
            table = None
            continue
        if cells[:3] == ["Gren", "Källfamilj", "Kärnserier"]:
            table = {}
            continue
        if table is None or set(cells[0]) <= set("-: "):
            continue
        if re.fullmatch(r"G\d", cells[0]):
            fam = re.findall(r"`([^`]+)`", cells[1])
            if len(fam) == 1:
                table.setdefault(cells[0], {})[fam[0]] = re.findall(r"`([^`]+)`", cells[2])
    return out


def parse_register(path: Path | None = None) -> dict[str, list[str]]:
    """Core series per branch as written in every '| Gren | Kärnserier |' table of the register.

    Tables are read in file order; a later table that names a branch again replaces that branch's list
    (a dated addition supersedes). Names are the backticked tokens of the 'Kärnserier' cell.
    """
    text = Path(path or REGISTER_PATH).read_text(encoding="utf-8")
    out: dict[str, list[str]] = {}
    in_table = False
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else None
        if cells is None:
            in_table = False
            continue
        if cells[:2] == ["Gren", "Kärnserier"]:
            in_table = True
            continue
        if not in_table or set(cells[0]) <= set("-: "):
            continue
        if re.fullmatch(r"G\d", cells[0]):
            out[cells[0]] = re.findall(r"`([^`]+)`", cells[1])
    return out
