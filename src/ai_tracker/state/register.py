"""The pre-registered rules of docs/mattregister.md (sections 1, 2, 5 and the "Ändringar" entries) as data.

Everything the state engine needs to know about *which* series and *which* thresholds lives here, so a new
registration (e.g. the G1 and G9 core series) is a data change in this file, not a code change:

- CORE_SERIES mirrors the register's core-series table(s) (section 5) cell by cell, with the register's own
  shorthand: brace lists (`x_{a,b}_m`) and the BTOS placeholder `<aktiv regim>`. tests/test_state.py parses the
  register file and asserts that it equals CORE_SERIES, so the two cannot drift apart.
- METHOD_OVERRIDES / AGG_OVERRIDES pin a measure method or aggregation where the default inferred from the
  catalog (unit, branch) is not the registered one.
- BACKFILL_GATED lists series whose backfilled history may only describe, not count, until there are
  24 months of own snapshots (register, change 2026-11-23 on ECI and the Epoch model database).
- DERIVED defines ratio series that are built from two catalog series (capex_ocf_hyp4).
"""

from __future__ import annotations

import re
from pathlib import Path

from ai_tracker import config

REGISTER_PATH = config.REPO / "docs" / "mattregister.md"

# ------------------------------------------------------------------ section 5: core series per branch
# Mirrors the register table literally (one entry per backticked name in the "Kärnserier" cell).
# G1 and G9 are not registered yet: add their names here when the register gets them (the test fails until
# this structure and the register agree again).
CORE_SERIES: dict[str, list[str]] = {
    "G1": [],
    "G2": ["g2_price_at_capability_gpqa"],
    "G3": ["btos_ai_use_<aktiv regim>", "eu_ai_ent_eu27", "eu_ai_ent_se"],
    "G4": ["rev_aws", "rev_google_cloud", "rev_msft_cloud", "rev_nvda_datacenter", "rev_orcl_cloud"],
    "G5": ["capex_hyp4", "us_constr_datacenter", "us_pfi_info_proc_eq_sw", "capex_ocf_hyp4"],
    "G6": ["tsmc_revenue_m", "us_ip_semis_m", "us_ip_computers_m", "us_imports_tw_m", "us_imports_kr_m"],
    "G7": ["us_elec_sales_com_{va,tx,ga,az,or,oh}_m"],
    "G8": ["ai_postings_share_{us,gb,de,fr,ca,au,ie,it,nl}_d"],
    "G9": [],
}

# "<aktiv regim>": the regime series are <prefix>v<n>; the active one is resolved per computation date.
REGIME_PLACEHOLDER = "<aktiv regim>"
REGIME_SUFFIX = r"v(\d+)"

# ------------------------------------------------------------------ section 1: measures per series
PACE_LAG = {"M": 12, "Q": 4, "A": 1}  # takt: change over a year
CHANGE_LAG = {"M": 6, "Q": 2, "A": 1}  # förändring i takt: pace now minus pace 6 m / 2 q / 1 y earlier
MIN_HISTORY = {"M": 24, "Q": 8, "A": 5}  # percentiles need at least this many values of the measure
DOUBLING_WINDOW = 24  # months of front values in the log-linear regression (G1, G2)
DOUBLING_CHANGE_LAG = 12  # change in doubling/halving time: now vs 12 months earlier
SUBMONTHLY = {"D", "W", "2W"}  # aggregated to calendar months before any pace is computed

# Methods: "log" (positive quantities, log x100), "share" (percent level, pp), "logit" (bounded 0-1 scores,
# front = running max), "doubling" (G1, front = running max), "halving" (G2 price, front = running min).
METHOD_OVERRIDES: dict[str, str] = {}
AGG_OVERRIDES: dict[str, str] = {}  # "mean" | "sum" for D/W/2W series

# Series that are live nowcast targets: surprise = outcome minus the committed live nowcast (forecasts/<dir>/).
NOWCAST_TARGETS = {"capex_hyp4": "n1", "tsmc_revenue_m": "n2"}

# ------------------------------------------------------------------ backfill exclusion (change 2026-11-23)
BACKFILL_GATED: set[str] = {"g2_price_at_capability"}  # ECI-based; future ECI / Epoch model-db series go here
OWN_SNAPSHOT_MONTHS = 24

# ------------------------------------------------------------------ derived ratio series (section 5, G5)
# key: (numerator, denominator, scale, method, freq, branch). Same version: the ratio is formed whenever either
# component gets a new vintage, with known_from = the later of the two.
DERIVED: dict[str, tuple[str, str, float, str, str, str]] = {
    "capex_ocf_hyp4": ("capex_hyp4", "ocf_hyp4", 100.0, "share", "Q", "G5"),
}

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
