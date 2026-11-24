"""R15 review of the P2a useful-life extraction (docs/granskning/r15_nyttjandeperioder.md). No network.

Evidence was read on 2026-11-24 in the original filings, re-fetched from www.sec.gov with the honest client (source
r15_review, not P2a's cache) and dated with EDGAR's submissions API (filingDate, acceptanceDateTime). Only ids,
numbers, dates and SHA-256 prefixes are kept here, never source text.

- Pinned rows: the 21 change rows and the 44 other rows of the stratified sample, as read by R15, plus a digest of
  every reviewed row (all 305 were read). A change to a reviewed row must be reviewed again.
- Properties: effect signs and periods, in_effect(as_of) uses nothing known after as_of, series dates are filing
  dates, subset changes stay out of the series, stops close only the broader classes, notes quote only short wording.
- Findings marked xfail(strict=True): F-1 to F-4 and N-1, N-2. Remove the mark when the correction is made.
"""

from __future__ import annotations

import hashlib
import re

import pandas as pd
import pytest

from ai_tracker import config
from ai_tracker.sources import useful_lives as ul

SOURCE_DOC = config.REPO / "docs" / "kallor" / "nyttjandeperioder.md"
REGISTER = config.REPO / "docs" / "mattregister.md"
REVIEW_DAY = "2026-11-24"


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    """The curated CSV as strings (exactly as committed)."""
    return pd.read_csv(ul.PATH, dtype=str).fillna("")


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return ul.load()


# ------------------------------------------------------------------ pinned rows (read by R15 in the filings)

# id, class_code, life_lo, life_hi, old_lo, old_hi, effective, filed, accession
CHANGES = [
    ("msft-c2020s", "SERVERS", "4", "4", "3", "3", "2020-07-01", "2020-07-30", "0001564590-20-034944"),
    ("msft-c2020n", "NETWORK", "4", "4", "2", "2", "2020-07-01", "2020-07-30", "0001564590-20-034944"),
    ("msft-c2022", "SERVERS_NETWORK", "6", "6", "4", "4", "2022-07-01", "2022-07-28", "0001564590-22-026876"),
    ("googl-c2021s", "SERVERS", "4", "4", "3", "3", "2021-01-01", "2021-02-02", "0001652044-21-000006"),
    ("googl-c2021n", "NETWORK_SUBSET", "5", "5", "3", "3", "2021-01-01", "2021-02-02", "0001652044-21-000006"),
    ("googl-c2023s", "SERVERS", "6", "6", "", "", "2023-01-01", "2023-02-02", "0001652044-23-000013"),
    ("googl-c2023n", "NETWORK_SUBSET", "6", "6", "", "", "2023-01-01", "2023-02-02", "0001652044-23-000013"),
    ("googl-c2023s2", "SERVERS", "6", "6", "4", "4", "2023-01-01", "2023-02-03", "0001652044-23-000016"),
    ("googl-c2023n2", "NETWORK_SUBSET", "6", "6", "5", "5", "2023-01-01", "2023-02-03", "0001652044-23-000016"),
    ("amzn-c2020", "SERVERS", "4", "4", "3", "3", "2020-01-01", "2020-01-31", "0001018724-20-000004"),
    ("amzn-c2022s", "SERVERS", "5", "5", "4", "4", "2022-01-01", "2022-02-04", "0001018724-22-000005"),
    ("amzn-c2022n", "NETWORK", "6", "6", "5", "5", "2022-01-01", "2022-02-04", "0001018724-22-000005"),
    ("amzn-c2024", "SERVERS", "6", "6", "5", "5", "2024-01-01", "2024-02-02", "0001018724-24-000008"),
    ("amzn-c2025", "SERVERS_NETWORK_SUBSET", "5", "5", "6", "6", "2025-01-01", "2025-02-07", "0001018724-25-000004"),
    ("meta-c2021", "SERVERS_NETWORK_SUBSET", "4", "4", "3", "3", "2021-01-01", "2021-10-26", "0001326801-21-000065"),
    ("meta-c2022a", "SERVERS_NETWORK_SUBSET", "4.5", "4.5", "4", "4", "2022-04-01", "2022-07-28",
     "0001326801-22-000082"),
    ("meta-c2022b", "SERVERS_NETWORK_SUBSET", "5", "5", "4.5", "4.5", "2022-10-01", "2023-02-02",
     "0001326801-23-000013"),
    ("meta-c2025", "SERVERS_NETWORK_SUBSET", "5.5", "5.5", "", "", "2025-01-01", "2025-01-29", "0001326801-25-000014"),
    ("orcl-c2023", "SERVERS", "5", "5", "4", "4", "2022-06-01", "2022-09-13", "0001564590-22-031545"),
    ("orcl-c2025", "SERVERS_NETWORK", "6", "6", "5", "5", "2024-06-01", "2024-09-10", "0000950170-24-104905"),
    ("crwv-c2023", "COMPUTER_EQUIPMENT", "6", "6", "5", "5", "2023-01-01", "2026-03-02", "0001769628-26-000104"),
]
CHANGE_SHA = {
    "msft-c2020s": "d7ff24bd67a8ec95", "msft-c2020n": "d7ff24bd67a8ec95", "msft-c2022": "3e54f7be830817d4",
    "googl-c2021s": "ab2f9fbced82f19e", "googl-c2021n": "ab2f9fbced82f19e", "googl-c2023s": "8f19e44dcad0d8e9",
    "googl-c2023n": "8f19e44dcad0d8e9", "googl-c2023s2": "d73c2864ef16fd12", "googl-c2023n2": "d73c2864ef16fd12",
    "amzn-c2020": "ae85c7be17087f9a", "amzn-c2022s": "0a8c1460bfd12bd9", "amzn-c2022n": "0a8c1460bfd12bd9",
    "amzn-c2024": "48a4d95798c2385d", "amzn-c2025": "d6caba96f003347c", "meta-c2021": "30598708c395fde9",
    "meta-c2022a": "ecc240f061b31f68", "meta-c2022b": "9fd2db81f0fcacfc", "meta-c2025": "7298e74390e3f0cb",
    "orcl-c2023": "592dc6c0add0fcbb", "orcl-c2025": "d4d73ecce5475cf6", "crwv-c2023": "b9325e9a42b46505",
}

# policy/stop: (sha256 prefix, class_code, life_lo, life_hi, period_end)
# effect: (sha256 prefix, ref, metric, value, basis, start, end)
SAMPLE = {
    "amzn-2019-02-01-p2": ("7a667a0dadfe2961", "NETWORK", "5", "5", "2018-12-31"),
    "amzn-2020-07-31-e3": ("0eec5e0284c324dc", "amzn-c2020", "diluted_eps", "1.05", "actual", "2020-04-01",
                           "2020-06-30"),
    "amzn-2020-10-30-e2": ("a645c448c6d1da51", "amzn-c2020", "net_income", "479", "actual", "2020-07-01",
                           "2020-09-30"),
    "amzn-2022-02-03-e1": ("8d76c24e7ddff9c5", "amzn-c2022s", "depreciation", "-1000", "expected", "2022-01-01",
                           "2022-03-31"),
    "amzn-2022-04-29-e2": ("951bb2c5eb1aa139", "amzn-c2022s", "net_income", "769", "actual", "2022-01-01",
                           "2022-03-31"),
    "amzn-2022-07-29-e6": ("cc1173a1b65c4027", "amzn-c2022s", "diluted_eps", "0.15", "actual", "2022-01-01",
                           "2022-06-30"),
    "amzn-2025-02-07-p1": ("ba554f9f0d9ee52b", "SERVERS", "6", "6", "2024-12-31"),
    "amzn-2026-02-06-p1": ("05f0b6770736cadf", "SERVERS_NETWORK", "5", "6", "2025-12-31"),
    "crwv-2026-03-02-p1": ("e894a30702944526", "COMPUTER_EQUIPMENT", "6", "6", "2025-12-31"),
    "googl-2019-02-05-p3": ("6fdbc38143f30d40", "NETWORK", "3", "5", "2018-12-31"),
    "googl-2020-02-04-p2": ("8f6539a2e21996f4", "SERVERS", "3", "3", "2019-12-31"),
    "googl-2021-04-27-e1": ("b8ee2550f10a849e", "googl-c2021s", "depreciation", "-835", "actual", "2021-01-01",
                            "2021-03-31"),
    "googl-2023-02-03-p2": ("5636f60bdc94adc4", "SERVERS", "4", "4", "2022-12-31"),
    "googl-2023-04-25-e1": ("e374c38ed80dfd69", "googl-c2023s", "depreciation", "-988", "actual", "2023-01-01",
                            "2023-03-31"),
    "googl-2023-07-25-e5": ("a87b59478a645436", "googl-c2023s", "net_income", "1500", "actual", "2023-01-01",
                            "2023-06-30"),
    "googl-2023-10-24-e1": ("a602c9cbabd521d3", "googl-c2023s", "depreciation", "-977", "actual", "2023-07-01",
                            "2023-09-30"),
    "googl-2023-10-24-e3": ("a602c9cbabd521d3", "googl-c2023s", "diluted_eps", "0.06", "actual", "2023-07-01",
                            "2023-09-30"),
    "googl-2025-02-05-s1": ("fa6d6e6bf14f9272", "COMPUTER_EQUIPMENT", "", "", "2024-12-31"),
    "meta-2021-01-28-p1": ("faecb65553b91160", "OTHER", "3", "20", "2020-12-31"),
    "meta-2022-02-03-e3": ("9a2e631d8377af71", "meta-c2021", "depreciation", "-620", "actual", "2021-01-01",
                           "2021-12-31"),
    "meta-2022-02-03-p2": ("2b41274ce1c0838d", "SERVERS_NETWORK", "4", "4", "2021-12-31"),
    "meta-2022-02-03-s1": ("2b41274ce1c0838d", "OTHER", "", "", "2021-12-31"),
    "meta-2023-02-02-e3": ("d52d833412547d6e", "meta-c2022b", "depreciation", "-860", "actual", "2022-01-01",
                           "2022-12-31"),
    "meta-2023-02-02-e5": ("d52d833412547d6e", "meta-c2022b", "diluted_eps", "0.26", "actual", "2022-01-01",
                           "2022-12-31"),
    "meta-2025-07-31-e1": ("d5a5c93f1918a2b9", "meta-c2025", "depreciation", "-1580", "actual", "2025-01-01",
                           "2025-06-30"),
    "meta-2026-01-29-e3": ("5821d45e12906fa6", "meta-c2025", "net_income", "2590", "actual", "2025-01-01",
                           "2025-12-31"),
    "meta-2026-01-29-p1": ("ec20217633a7b078", "SERVERS_NETWORK", "5", "5.5", "2025-12-31"),
    "msft-2021-04-27-e3": ("72c35a75709d7574", "msft-c2020s", "diluted_eps", "0.07", "actual", "2021-01-01",
                           "2021-03-31"),
    "msft-2021-07-29-p1": ("9036d5719abafb21", "COMPUTER_EQUIPMENT", "2", "4", "2021-06-30"),
    "msft-2022-07-28-e3": ("d8ac7e34dc0edfb3", "msft-c2022", "operating_income", "3700", "expected", "2022-07-01",
                           "2023-06-30"),
    "msft-2022-07-28-p1": ("9036d5719abafb21", "COMPUTER_EQUIPMENT", "2", "4", "2022-06-30"),
    "msft-2023-01-24-e4": ("37db26cb4b5446f2", "msft-c2022", "operating_income", "2000", "actual", "2022-07-01",
                           "2022-12-31"),
    "msft-2023-01-24-e5": ("37db26cb4b5446f2", "msft-c2022", "net_income", "1600", "actual", "2022-07-01",
                           "2022-12-31"),
    "msft-2023-07-27-e4": ("fa64458e16f2a57c", "msft-c2022", "diluted_eps", "0.4", "actual", "2022-07-01",
                           "2023-06-30"),
    "msft-2026-07-29-p2": ("815861f4bcfa684e", "SERVERS_NETWORK", "2", "6", "2026-06-30"),
    "msft-2026-07-29-s1": ("815861f4bcfa684e", "COMPUTER_EQUIPMENT", "", "", "2026-06-30"),
    "orcl-2021-06-21-p1": ("0186d896714d97d9", "COMPUTER_EQUIPMENT", "1", "5", "2021-05-31"),
    "orcl-2022-06-21-p1": ("6422e05794904e5c", "COMPUTER_EQUIPMENT", "1", "5", "2022-05-31"),
    "orcl-2023-06-20-e2": ("4a79aabbdae6bf31", "orcl-c2023", "operating_income", "434", "actual", "2022-06-01",
                           "2023-05-31"),
    "orcl-2025-03-11-e1": ("105fc8cb9b0dac14", "orcl-c2025", "operating_income", "181", "actual", "2024-12-01",
                           "2025-02-28"),
    "orcl-2025-03-11-e3": ("105fc8cb9b0dac14", "orcl-c2025", "diluted_eps", "0.05", "actual", "2024-12-01",
                           "2025-02-28"),
    "orcl-2025-03-11-e5": ("105fc8cb9b0dac14", "orcl-c2025", "net_income", "442", "actual", "2024-06-01",
                           "2025-02-28"),
    "orcl-2025-06-18-e4": ("d5951bac43b7400f", "orcl-c2025", "diluted_eps", "0.2", "actual", "2024-06-01",
                           "2025-05-31"),
    "orcl-2026-09-11-p1": ("cb6d5cbc951aa714", "COMPUTER_EQUIPMENT", "1", "6", "2026-08-31"),
}

# SHA-256 of every non-note column of all rows filed on or before the review day, sorted (R15 read all 305)
REVIEWED_DIGEST = "fea8cb74b6dcc705f864eefc11c7c7ea78c496427e33112df9d258f68b168706"
REVIEWED_ROWS = 305


def test_change_rows_match_r15_reading(raw):
    got = raw[raw["row_type"] == "change"].set_index("id")
    assert len(got) == len(CHANGES)
    for cid, code, lo, hi, olo, ohi, eff, filed, acc in CHANGES:
        r = got.loc[cid]
        assert (r.class_code, r.life_lo, r.life_hi, r.old_lo, r.old_hi, r.effective, r.filed, r.accession) == (
            code, lo, hi, olo, ohi, eff, filed, acc), cid
        assert r.sentence_sha256.startswith(CHANGE_SHA[cid]), cid


def test_sample_rows_match_r15_reading(raw):
    got = raw.set_index("id")
    for rid, want in SAMPLE.items():
        r = got.loc[rid]
        assert r.sentence_sha256.startswith(want[0]), rid
        if r.row_type == "effect":
            assert (r.ref, r.effect_metric, r.effect_value, r.effect_basis, r.effect_start, r.effect_end) == want[1:]
        else:
            assert (r.class_code, r.life_lo, r.life_hi, r.period_end) == want[1:], rid


def test_reviewed_rows_are_unchanged(raw):
    """All 305 rows filed by the review day were read by R15 (census). A changed or added row needs a new review."""
    cols = [c for c in raw.columns if c != "note"]
    rows = raw[raw["filed"] <= REVIEW_DAY]
    lines = sorted("|".join(r[c] for c in cols) for _, r in rows.iterrows())
    assert len(lines) == REVIEWED_ROWS
    assert hashlib.sha256("\n".join(lines).encode()).hexdigest() == REVIEWED_DIGEST


# ------------------------------------------------------------------ effects: signs and periods

def test_effect_signs_follow_the_direction_of_the_change(df):
    """Longer lives lower depreciation and raise income and EPS; Amazon's 2025 shortening does the opposite."""
    changes = df[df["row_type"] == "change"].set_index("id")
    eff = df[df["row_type"] == "effect"]
    for r in eff.itertuples():
        ch = changes.loc[r.ref]
        longer = pd.isna(ch.old_hi) or ch.life_hi > ch.old_hi
        sign = -1 if r.effect_metric == "depreciation" else 1
        assert (r.effect_value * sign > 0) == longer, r.id


def test_expected_effects_start_when_the_change_applies_and_actual_ones_are_past(df):
    changes = df[df["row_type"] == "change"].set_index("id")
    for r in df[df["row_type"] == "effect"].itertuples():
        if r.effect_basis == "expected":
            assert r.effect_start >= changes.loc[r.ref, "effective"], r.id
        else:
            assert r.effect_end <= r.period_end, r.id


# ------------------------------------------------------------------ dating and in_effect

def _family_dates(df, company, family):
    rows = df[(df["company"] == company) & df["class_code"].isin(ul.FAMILIES[family])]
    return sorted(set(rows["known_from"]))


def test_in_effect_equals_a_csv_truncated_at_as_of(df):
    """in_effect(as_of) gives exactly what a CSV holding only rows filed by as_of gives: no future row is used."""
    n = 0
    for company in ul.COMPANIES:
        for family in ul.FAMILIES:
            for t in _family_dates(df, company, family):
                for as_of in (t - pd.Timedelta(days=1), t):
                    known = df[df["known_from"] <= as_of]
                    for bound in ("lo", "hi"):
                        a = ul.in_effect(company, family, bound, as_of=as_of, end="2027Q4", df=df)
                        b = ul.in_effect(company, family, bound, end="2027Q4", df=known)
                        assert (a.empty and b.empty) or a.equals(b), (company, family, bound, as_of)
                        n += 1
    assert n > 300


def test_in_effect_ignores_a_row_filed_after_as_of(df):
    poison = df[df["id"] == "msft-c2022"].copy()
    poison[["id", "accession", "life_lo", "life_hi"]] = ["poison", "0000000000-22-999999", 9.0, 9.0]
    poison["known_from"] = poison["filed"] = pd.Timestamp("2022-07-29")
    with_poison = pd.concat([df, poison], ignore_index=True)
    as_of = "2022-07-28"
    clean = ul.in_effect("msft", "servers", "hi", as_of=as_of, end="2023Q4", df=df)
    assert clean.equals(ul.in_effect("msft", "servers", "hi", as_of=as_of, end="2023Q4", df=with_poison))
    assert ul.in_effect("msft", "servers", "hi", as_of="2022-07-29", end="2023Q4", df=with_poison).max() == 9.0


@pytest.mark.parametrize("company,as_of,life", [
    ("msft", "2022-07-27", 4.0), ("msft", "2022-07-28", 6.0),      # 10-K 2022-07-28 (the call two days before is not SEC)
    ("googl", "2023-02-01", 4.0), ("googl", "2023-02-02", 6.0),    # 8-K 2023-02-02 states the new life
    ("amzn", "2024-02-01", 5.0), ("amzn", "2024-02-02", 6.0),      # the 8-K of 2024-02-01 gives no lives
    ("amzn", "2025-06-30", 6.0),                                    # a subset went to five years: not in the series
    ("meta", "2022-12-31", 4.0), ("meta", "2025-06-30", 5.0),      # Meta's changes are all for part of the fleet
    ("orcl", "2024-09-09", 5.0), ("orcl", "2024-09-10", 6.0),
])
def test_latest_stated_server_life_as_known_on_a_date(df, company, as_of, life):
    """The value N7 (V2) takes: the latest stated quarter of useful_life_servers_<co>_hi known on the origin."""
    s = ul.in_effect(company, "servers", "hi", as_of=as_of, df=df)
    assert s.iloc[-1] == life


def test_series_known_from_is_the_filing_date_of_a_feeding_row(df):
    for company in ul.COMPANIES:
        for family, codes in ul.FAMILIES.items():
            filed = set(df[(df["company"] == company) & df["class_code"].isin(codes)]["known_from"])
            for bound in ("lo", "hi"):
                f = ul.series_frame(df, company, family, bound)
                assert set(f["known_from"]) <= filed, (company, family, bound)
                starts = pd.PeriodIndex(f["period"], freq="Q-DEC").start_time.to_numpy()
                assert (pd.to_datetime(f["known_from"]).to_numpy() >= starts).all()  # not before its quarter starts


def test_subset_changes_stay_out_of_the_series(df):
    meta = ul.series_frame(df, "meta", "servers", "hi")
    assert not set(meta["period"]) & {"2021Q1", "2022Q1", "2022Q2", "2022Q3", "2025Q1"}
    amzn = ul.series_frame(df, "amzn", "servers", "hi").set_index("period")["value"]
    assert amzn["2025Q4"] == 6.0 and "2025Q1" not in amzn.index


def test_stops_close_only_the_broader_classes(df):
    closed = {(c, f) for c in ul.COMPANIES for f in ul.FAMILIES if ul.stopped(df, c, f) is not None}
    assert closed == {("msft", "computer_equipment"), ("googl", "computer_equipment"), ("meta", "other")}


def test_csv_notes_quote_only_short_wording(raw):
    for r in raw.itertuples():
        for q in re.findall(r"'([^']+)'", r.note):
            assert len(q.split()) <= 8, r.id
        assert len(r.note) <= 200, r.id


# ------------------------------------------------------------------ findings (strict xfail until corrected)

def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    nxt = text.find("\n## ", start + len(heading))
    return text[start: nxt if nxt > 0 else len(text)]


@pytest.mark.xfail(strict=True, reason="R15 F-1: useful_lives_check was changed after the first run (stop test via "
                   "class_stated(), '$X.0 billion'); with the fc49225 check 11 of 305 rows fail (3 stops, 8 effects). "
                   "The change and the stop locator choice are not under 'Tolkningar'")
def test_stop_check_change_is_disclosed():
    text = SOURCE_DOC.read_text(encoding="utf-8")
    assert "class_stated" in _section(text, "## Tolkningar under kodningen")


@pytest.mark.xfail(strict=True, reason="R15 F-2: 82 of 305 rows come from the supplementary search outside the locked "
                   "candidate rule (tolkning 1); the deviation is not logged in docs/mattregister.md")
def test_candidate_rule_deviation_is_registered():
    text = REGISTER.read_text(encoding="utf-8")
    sections = [s for s in text.split("\n### ") if "P2a" in s.split("\n", 1)[0]]
    assert any("kandidat" in s for s in sections)


@pytest.mark.xfail(strict=True, reason="R15 F-3: the source document quotes whole sentences from the filings "
                   "(5 quotes of 11-22 words); CLAUDE.md publishes numbers with references, never the text")
def test_source_doc_has_no_long_quotes():
    text = re.sub(r"\n\s*", " ", SOURCE_DOC.read_text(encoding="utf-8"))
    quotes = [q for q in re.findall(r'"([^"]{3,300}?)"', text) if not re.search(r"[åäöÅÄÖ]", q)]
    assert max(len(q.split()) for q in quotes) < 11


@pytest.mark.xfail(strict=True, reason="R15 F-4: _lo series mix points (changes) and ranges (policies), so Microsoft's "
                   "servers lo falls from 6 to 2 years in 2026Q2 without a change; the public note does not say so")
def test_lo_note_explains_points_and_ranges():
    from ai_tracker.series import useful_lives as series

    note = next(s.note for s in series.SPECS if s.key == "useful_life_servers_msft_lo")
    assert "intervall" in note


@pytest.mark.xfail(strict=True, reason="R15 N-1: CoreWeave's S-1 of 2025-03-03 (0001193125-25-044231) already states "
                   "the change 5 -> 6 years from 2023-01-01; the document says this was not checked")
def test_source_doc_names_coreweave_s1():
    assert "2025-03-03" in SOURCE_DOC.read_text(encoding="utf-8")


@pytest.mark.xfail(strict=True, reason="R15 N-2: Oracle's network series starts 2024Q1 (old life of the change row), "
                   "not 2024Q2 as the document says")
def test_source_doc_oracle_network_start(df):
    assert ul.series_frame(df, "orcl", "network", "hi")["period"].iloc[0] == "2024Q1"
    assert "Oracle `network` från 2024Q2" not in SOURCE_DOC.read_text(encoding="utf-8")
