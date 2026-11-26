"""R27 sample check of KL1 after the fix X23 (docs/granskning/r27_kreditlagret.md). No network.

Evidence was read on 2026-11-25 in the EDGAR documents behind the 64 rows that X23 added or changed and in the 60
sampled uncoded candidates. R27 fetched every document again from www.sec.gov (generic client identity, one request at a
time, 1.5 s apart, no 403 or 429); all were byte-identical to the shared cache. Only ids, numbers, dates, accession
numbers and hashes are kept here, never filing text.

- Pinned: the register entry "2026-11-25 – X23" (unchanged since 599b24e) and the 64 rows R27 found correct (all fields
  but the note). A change to a pinned row must be reviewed again.
- Properties that hold: the five September rows and CoreWeave's 9.750 % notes as fixed in X23, SpaceX's debt table adds
  up, no row is known before its balance date, SpaceX stays outside every series, layer and reading, the report says
  the debt is group-wide, the command gives docs/resultat for both days, and the seed-27 sample is reproducible.
- Finding R27-1 was a strict xfail; X24 qualified SpaceX's rate on other financings, so it is a plain test now.
"""

from __future__ import annotations

import difflib
import hashlib
import re

import pandas as pd
import pytest

from ai_tracker import catalog, config
from ai_tracker.followed import kreditlagret as F
from ai_tracker.series import kreditlagret as S
from ai_tracker.sources import kreditlagret as kl

REGISTER = config.REPO / "docs" / "mattregister.md"
RESULTS = config.REPO / "docs" / "resultat" / "kreditlagret.md"
SKIPPED = config.REPO / "curated" / "kreditlagret_skipped.csv"
REVIEW_DAY = "2026-11-25"
X23_ENTRY_SHA256 = "9ed845a5d6bcef8549552b2c19fa7d2f38f9fd585424bfd5c33a45a810418c45"  # = 599b24e
S1A1 = ("0001628280-26-068676", "2026-11-02")  # Anthropic S-1/A: the first document with the tables as of 2026-09-30
SEPTEMBER_ROWS = {  # R26-1 as fixed in X23: id -> locator in the S-1/A of 2026-11-02
    "anthropic_amazon_2023_npa_notes-2026-09-30-outstanding": "line #7853",
    "anthropic_amazon_2024_npa_notes-2026-09-30-outstanding": "line #7854",
    "anthropic_amazon_npa_2026-2026-09-30-commitment": "line #7907",
    "anthropic_broadcom_npa_2026-2026-09-30-commitment": "line #7935",
    "anthropic_google_npa_2026-2026-09-30-commitment": "line #7975",
}
SPACEX_FIRST_10Q = "2026-08-04"  # the first 10-Q after the IPO (register X23, point 3)
_REVIEWED_DIGESTS = """
068b478331b3 09ad3ea94e60 0fa40eb05a54 117430aaccd5 1460914c0fc4 1498f34640d3 1abd492b99fa 1b5a7275a4be 1bc89d8fef48
1f9976591a4d 25fb915ed2f8 26e15b4686c3 2d81eabe6432 2ecef869b241 33713cdcb5b7 3470f176c0a3 35e36e262e4b 36559fa52733
383a55c26b5e 3b44ad5d451c 413cca8104e6 466c41fde5c2 4c09ac08e78d 5db47fa1c353 688834e4233a 6dfe76e5b467 716db39e4853
75d10cfcf775 76ca3be59f0e 77d3b6f35dc1 7ccfcbabf75f 80db6486c3f2 80f2d3dc3f30 81f77833dafc 91ce0a093024 98f15a9a4c58
9c7c3d7e9543 9cc97606ea30 9db173ba4cc4 a23071e2e2ea aa720fc4a927 b1a2ca631800 b54f9b22f281 ba4051a79446 ba71fcca3474
bfb967ed4e58 c13db7bb85ae c1ef61237779 c4e35dd37660 cdb68d909b64 d65837268cf5 d88597d6af1a dcc9424415df df12b10d2454
e672abe83bfd ec7bb4713c10 ecbbc9f744c1 ef24eebecade f576f4f57c70 f632047d872a fb459038d24b fc74c7717e7e fd5d15cba35e
ff2d4b45a0b3
"""  # 12-hex SHA-256 prefix per row X23 added (58) or changed (6), all fields but the note, joined by "|"
REVIEWED = frozenset(_REVIEWED_DIGESTS.split())
SAMPLE_SEED = 27
SAMPLE_INDEX = (  # rows of curated/kreditlagret_skipped.csv drawn with weight 2 for "regel" and 1 for "agent"
    11, 61, 65, 69, 78, 100, 127, 135, 140, 147, 151, 167, 168, 175, 205, 221, 233, 247, 279, 287, 289, 308, 316, 351,
    359, 362, 376, 381, 419, 424, 432, 433, 435, 479, 493, 505, 507, 508, 522, 529, 533, 538, 562, 569, 583, 598, 607,
    613, 620, 621, 630, 641, 646, 668, 676, 677, 682, 720, 732, 743)


@pytest.fixture(scope="module")
def csv() -> pd.DataFrame:
    return kl.load()


def _section(text: str, start: str) -> str:
    a = text.index(start)
    b = text.find("\n### ", a + len(start))
    return (text[a:b] if b > 0 else text[a:]).strip()


def _lab(csv: pd.DataFrame) -> list[str]:
    return F._lab_lines(F.extraction(REVIEW_DAY, csv)["rows"])


def _val(csv: pd.DataFrame, rid: str) -> float:
    return float(csv.loc[csv["id"] == rid, "value"].iloc[0])


# ------------------------------------------------------------------ pinned


def test_register_x23_entry_is_unchanged_since_the_lock():
    text = REGISTER.read_text(encoding="utf-8")
    entry = _section(text, "### 2026-11-25 – X23: rättning av KL1")
    assert hashlib.sha256(entry.encode("utf-8")).hexdigest() == X23_ENTRY_SHA256


def test_the_64_reviewed_rows_are_unchanged(csv):
    """Every row R27 read and found correct is still there with the same fields (the note aside)."""
    cols = [c for c in kl.COLUMNS if c != "note"]
    now = {hashlib.sha256("|".join(r).encode("utf-8")).hexdigest()[:12] for r in csv[cols].itertuples(index=False)}
    assert len(REVIEWED) == 64
    assert REVIEWED <= now, f"{len(REVIEWED - now)} reviewed rows changed or removed: review them again"


def test_rows_per_company_as_documented(csv):
    # X24 (R27-1) added two rows: Valor's interest expense per quarter (instrument spacex_valor, interest_expense_q)
    assert len(csv) == 460 and csv["instrument"].nunique() == 82
    assert csv["company"].value_counts().to_dict() == {"crwv": 286, "anthropic": 108, "spacex": 46, "meta": 20}


# ------------------------------------------------------------------ properties that hold


def test_september_rows_are_dated_to_the_first_september_document(csv):
    rows = csv.set_index("id").loc[sorted(SEPTEMBER_ROWS)]
    assert (rows["accession"] == S1A1[0]).all() and (rows["filed"] == S1A1[1]).all() and (rows["form"] == "S-1/A").all()
    assert rows["locator"].to_dict() == {k: SEPTEMBER_ROWS[k] for k in sorted(SEPTEMBER_ROWS)}
    assert rows["value"].astype(float).to_dict() == {
        "anthropic_amazon_2023_npa_notes-2026-09-30-outstanding": 2186.0,
        "anthropic_amazon_2024_npa_notes-2026-09-30-outstanding": 4017.0,
        "anthropic_amazon_npa_2026-2026-09-30-commitment": 15000.0,
        "anthropic_broadcom_npa_2026-2026-09-30-commitment": 42000.0,
        "anthropic_google_npa_2026-2026-09-30-commitment": 20000.0}


def test_coreweave_9_75_notes_are_1750_plus_1000(csv):
    r = csv.set_index("id").loc["crwv_2031_9_75_senior_notes-2026-04-14-principal"]
    assert (float(r["value"]), r["unit"], r["filed"], r["accession"], r["locator"]) == (
        1750.0, "MUSD", "2026-04-21", "0001769628-26-000183", "line #38")
    add_on = _val(csv, "crwv_2031_9_75_senior_notes_addon-2026-04-21-principal")
    assert 1750.0 + add_on == _val(csv, "crwv_2031_9_75_senior_notes-2026-06-30-outstanding") == 2750.0


@pytest.mark.parametrize("day", ["2026-06-30", "2026-09-30"])
def test_spacex_debt_table_adds_up(csv, day):
    parts = ("spacex_notes", "spacex_x_2027_2030_notes", "spacex_other_financings")
    total = _val(csv, f"spacex_total_debt-{day}-outstanding")
    assert total == sum(_val(csv, f"{p}-{day}-outstanding") for p in parts)
    valor = sum(_val(csv, f"spacex_valor_{k}-{day}-outstanding") for k in ("current", "noncurrent"))
    assert valor <= _val(csv, f"spacex_other_financings-{day}-outstanding")


def test_no_row_is_known_before_its_balance_date(csv):
    full = csv[csv["period"].str.fullmatch(r"\d{4}-\d{2}-\d{2}")]
    early = full[(full["filed"] <= full["period"]) & ~full["field"].isin(["principal", "commitment"])]
    assert early.empty, sorted(early["id"])  # a principal or commitment at its issue date may be filed that day
    assert (full["filed"] >= full["period"]).all()
    assert (csv.loc[csv["company"] == "spacex", "filed"] >= SPACEX_FIRST_10Q).all()


def test_spacex_is_outside_every_series_layer_and_reading(csv):
    assert not [s.key for s in catalog.ALL if "spacex" in s.key]
    assert "spacex" not in S.OUTER + S.INNER
    assert all("spacex" not in m for layers in S.MEMBERS.values() for m in layers.values())
    assert len(S.coupon_out(csv, "spacex")) < S.MIN_QUARTERS  # two balance dates: table rows only
    assert S.coupon_new(csv, "spacex").empty


def test_report_says_spacex_debt_is_group_wide(csv):
    spacex = next(x for x in _lab(csv) if x.startswith("- **SpaceX**"))
    assert re.search(r"hela koncernen", spacex) and "Starlink" in spacex and "xAI" in spacex
    assert re.search(r"(?s)SpaceX.{0,200}hela koncernen", RESULTS.read_text(encoding="utf-8"))


def test_skipped_sample_seed_27_is_reproducible():
    sk = pd.read_csv(SKIPPED, dtype=str, keep_default_na=False)
    assert len(sk) == 753 and sk["reason_by"].value_counts().to_dict() == {"regel": 622, "agent": 131}
    w = sk["reason_by"].map({"regel": 2.0, "agent": 1.0})
    sample = sk.sample(n=60, weights=w, random_state=SAMPLE_SEED)
    assert tuple(sorted(sample.index)) == SAMPLE_INDEX
    assert sample["reason_by"].value_counts().to_dict() == {"regel": 54, "agent": 6}


@pytest.fixture(scope="module")
def table():
    from ai_tracker import observations

    t = observations.load()
    if t.empty or "kl_capex4_orcl" not in set(t["series"]):
        pytest.skip("no real observation table with the KL1 series")
    return t


def _demote(text: str) -> str:
    return re.sub(r"(?m)^(#+) ", lambda m: "#" + m.group(1) + " ", text)


@pytest.mark.real_data
@pytest.mark.parametrize("day", ["2026-11-25", "2025-11-25"])
def test_command_gives_the_results_document(table, day):
    text = F.render(F.compute(day, table))
    doc = RESULTS.read_text(encoding="utf-8")
    a = doc.index(f"## Kreditlagret per {day}")
    b = doc.find("\n## Kreditlagret per ", a + 10)
    assert (doc[a:b] if b > 0 else doc[a:]).strip() == _demote(text).strip()


@pytest.mark.real_data
def test_without_spacex_rows_only_the_lab_lines_change(table, csv):
    with_sx = F.compute(REVIEW_DAY, table, csv)
    without = F.compute(REVIEW_DAY, table, csv[csv["company"] != "spacex"])
    assert with_sx["measures"] == without["measures"] and with_sx["readings"] == without["readings"]
    diff = [x for x in difflib.unified_diff(F.render(without).splitlines(), F.render(with_sx).splitlines(),
                                            lineterm="", n=0) if x[:1] in "+-" and x[:3] not in ("+++", "---")]
    assert diff and all("SpaceX" in x or "xAI" in x or x.startswith(("+  - ", "-- Utanför")) for x in diff), diff


# ------------------------------------------------------------------ finding (strict xfail until fixed in X24)


def test_r27_1_spacex_other_financings_rate_is_qualified(csv):
    spacex = _lab(csv)
    line = next(x for x in spacex if "övrig finansiering" in x)
    assert "6,3 %" not in line or re.search(r"(?i)räntekostnad", line)
