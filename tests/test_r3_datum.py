"""R3 independent review: dating (known_from) and leakage for the wave-1 sources (A1-A4, D3).

Evidence was read from the sources themselves on 2026-11-23 (docs/granskning/r3_datum.md):
- EDGAR submissions (filingDate, acceptanceDateTime, reportDate) for every CIK in A1-A3 and the ASML/Nebius 6-Ks,
- PJM: docProps of the posted xlsx files and PDF CreationDate/ModDate of the BRA and load forecast reports,
- EIA-930 form instructions (sub-region demand "within one month after the operating day") and EIA notes,
- Manifold /v0/bets for one market (values recomputed from the raw trade timestamps).

Three kinds of tests:
1. Point-in-time properties of the vintage builders (random fixtures): as of any date d, the output equals a
   brute-force reference that only looks at facts filed <= d. A leak (a value or version visible before its
   filing) fails these.
2. Targeted fixtures for the edge cases: zero fill, formula fallback, ASML regime closure, PJM revisions,
   EIA-930 backfill flags, Manifold day boundaries, Polymarket snapshots.
3. Real-data checks (marked real_data) against the EDGAR/PJM evidence.

Tests marked xfail(strict=True) demonstrate a real dating bug; they turn into failures once the bug is fixed, so
the fix must also remove the mark. No network.
"""

from __future__ import annotations

import random

import pandas as pd
import pytest

from ai_tracker import catalog, observations
from ai_tracker.series import halvledare as h
from ai_tracker.sources import asml_sec, eia930, forvantningar as fv, pjm, sec, sec_financing as sf, sec_instant
from ai_tracker.sources import sec_rpo
from conftest import real_table_exists

M = 1e6
SPECS = catalog.by_key()
TS = pd.Timestamp


def bug(reason: str):
    return pytest.mark.xfail(strict=True, reason=reason)


def as_of_rows(df: pd.DataFrame, d: pd.Timestamp) -> dict[str, float]:
    """Latest value per period among output rows with known_from <= d."""
    got = df[df["known_from"] <= d].sort_values("known_from")
    return got.groupby("period")["value"].last().to_dict()


def check_dates(df: pd.DataFrame, filed: set) -> list:
    return sorted({d for d in df["known_from"] if d not in filed})


# ------------------------------------------------------------------ 1. point-in-time properties (random fixtures)

DATES = pd.date_range("2024-01-15", periods=40, freq="17D")
ENDS = [TS("2023-12-31"), TS("2024-03-31"), TS("2024-06-30"), TS("2024-09-30"), TS("2024-12-31"),
        TS("2024-11-30"), TS("2024-02-29")]  # Oracle-like ends share calendar quarters with month-end ones


def random_facts(seed: int, n: int = 40) -> list[sec.Fact]:
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        end = rnd.choice(ENDS)
        filed = rnd.choice([d for d in DATES if d > end + pd.Timedelta(days=5)])
        out.append(sec.Fact(end, end, rnd.choice([100, 200, 300, 450]) * M, filed,
                            rnd.choice(["10-Q", "10-K", "10-Q/A"]), f"acc-{i:03d}"))
    return out


def rpo_reference(facts: list[sec.Fact], d: pd.Timestamp) -> dict[str, float]:
    """Brute force: per balance date the latest-ranked fact filed <= d; per calendar quarter the latest date."""
    best: dict[pd.Timestamp, sec.Fact] = {}
    for f in facts:
        if f.filed <= d and (f.end not in best or f.rank > best[f.end].rank):
            best[f.end] = f
    per: dict[str, tuple] = {}
    for end, f in best.items():
        p = str(sec_rpo.balance_quarter(end))
        if p not in per or end > per[p][0]:
            per[p] = (end, f.val / M)
    return {p: v for p, (_, v) in per.items()}


@pytest.mark.parametrize("seed", range(12))
def test_rpo_stock_vintages_point_in_time(seed):
    facts = random_facts(seed)
    df = sec_rpo.stock_vintages(facts)
    assert not check_dates(df, {f.filed for f in facts})  # every known_from is a filing date
    for d in list(DATES) + [x - pd.Timedelta(days=1) for x in DATES]:
        assert as_of_rows(df, d) == rpo_reference(facts, d), d


def instant_reference(sources, quarters, d):
    by_end = {}
    for fs in sources:  # first source with a fact (filed <= d) for the date wins, latest rank within it
        own = {}
        for f in fs:
            if f.filed <= d and f.end in quarters and (f.end not in own or f.rank > own[f.end].rank):
                own[f.end] = f
        for e, f in own.items():
            by_end.setdefault(e, f)
    per = {}
    for e, f in by_end.items():
        p = str(quarters[e])
        if p not in per or e > per[p][0]:
            per[p] = (e, f.val / M)
    return {p: v for p, (_, v) in per.items()}


@pytest.mark.parametrize("seed", range(8))
def test_sec_instant_vintages_point_in_time(seed):
    """Inventories / Nvidia purchase obligations: priority sources, fiscal ends mapped by the flows' midpoint."""
    rnd = random.Random(100 + seed)
    quarters = {TS("2024-01-28"): pd.Period("2023Q4", "Q"), TS("2024-04-28"): pd.Period("2024Q1", "Q"),
                TS("2024-07-28"): pd.Period("2024Q2", "Q"), TS("2024-10-27"): pd.Period("2024Q3", "Q")}
    ends = list(quarters) + [TS("2024-05-15")]  # an acquisition-date instant, must be dropped
    sources = []
    for s in range(3):
        fs = []
        for i in range(15):
            end = rnd.choice(ends)
            filed = rnd.choice([x for x in DATES if x > end + pd.Timedelta(days=5)])
            fs.append(sec_instant.Instant(end, rnd.choice([10, 20, 30]) * M, filed, "10-Q", f"a{s}-{i}"))
        sources.append(fs)
    df = sec_instant.vintages(sources, quarters)
    for d in DATES:
        assert as_of_rows(df, d) == instant_reference(sources, quarters, d), d


@pytest.mark.parametrize("seed", range(8))
def test_financing_stock_vintages_point_in_time(seed):
    rnd = random.Random(200 + seed)
    ends = {TS("2024-02-29"), TS("2024-05-31"), TS("2024-08-31"), TS("2024-11-30")}  # Oracle fiscal ends
    sources = []
    for s in range(2):
        fs = []
        for i in range(15):
            end = rnd.choice(sorted(ends) + [TS("2024-06-15")])
            filed = rnd.choice([x for x in DATES if x > end + pd.Timedelta(days=5)])
            fs.append(sec.Fact(end, end, rnd.choice([5, 7, 9]) * M, filed, "10-Q", f"f{s}-{i}"))
        sources.append(fs)
    df = sf.stock_vintages(sources, ends)
    quarters = {e: sf.calendar_quarter(e) for e in ends}
    for d in DATES:
        ref = instant_reference([[sec_instant.Instant(f.end, f.val, f.filed, f.form, f.accn) for f in fs]
                                 for fs in sources], quarters, d)
        assert as_of_rows(df, d) == ref, d


def test_oracle_and_micron_offsets_map_to_the_quarter_holding_most_of_the_fiscal_quarter():
    # Oracle Sep-Nov ends 30 Nov -> Q4, filed ~10 Dec (before the calendar quarter ends: real, not a leak)
    assert str(sf.calendar_quarter(TS("2025-11-30"))) == "2025Q4"
    assert str(sec_rpo.balance_quarter(TS("2025-11-30"))) == "2025Q4"
    # Micron FQ1 FY26 (2025-08-29..2025-11-27) and Nvidia FQ4 FY26 (2025-10-27..2026-01-25)
    assert str(sec.calendar_quarter(TS("2025-08-29"), TS("2025-11-27"))) == "2025Q4"
    assert str(sec.calendar_quarter(TS("2025-10-27"), TS("2026-01-25"))) == "2025Q4"
    # Broadcom FQ1 FY26 (2025-11-03..2026-02-01) and Marvell FQ4 FY26 (2025-11-02..2026-01-31)
    assert str(sec.calendar_quarter(TS("2025-11-03"), TS("2026-02-01"))) == "2025Q4"
    assert str(sec.calendar_quarter(TS("2025-11-02"), TS("2026-01-31"))) == "2025Q4"


# ------------------------------------------------------------------ 2a. financing: zero fill and formula fallback


def cf(**tags):
    return {"facts": {"us-gaap": {t: {"units": {"USD": rows}} for t, rows in tags.items()}}}


def dur(start, end, val, filed, form="10-Q", accn=None):
    return {"start": start, "end": end, "val": int(val * M), "filed": filed, "form": form,
            "accn": accn or f"acc-{filed}"}


def test_zero_fill_is_dated_by_its_own_filing_and_never_fills_comparatives(monkeypatch):
    total = "NetCashProvidedByUsedInFinancingActivities"
    data = cf(**{total: [dur("2025-07-01", "2025-09-30", -5, "2025-10-29", accn="q1"),
                         dur("2024-07-01", "2024-09-30", -4, "2025-10-29", accn="q1"),  # comparative
                         dur("2015-07-01", "2015-09-30", -1, "2015-10-22", accn="old")],  # before ZERO_SINCE
                 "ProceedsFromIssuanceOfLongTermDebt": [dur("2024-07-01", "2024-09-30", 9, "2024-10-30", accn="q0")]})
    monkeypatch.setattr(sf.sec_segment, "instance", lambda f: b"<x:Revenues contextRef='c'>1</x:Revenues>")
    zeros, refused = sf.zero_facts(1, data, ["ProceedsFromIssuanceOfLongTermDebt"], r"^Proceeds\w*Debt", "Short")
    assert refused == []
    assert [(str(z.start.date()), str(z.end.date()), str(z.filed.date())) for z in zeros] == \
        [("2025-07-01", "2025-09-30", "2025-10-29")]
    df = sec.vintages([sec.facts(data, "ProceedsFromIssuanceOfLongTermDebt"), zeros])
    q = df.set_index("period")
    assert q.loc["2025Q3", "value"] == 0 and q.loc["2025Q3", "known_from"] == TS("2025-10-29")
    assert q.loc["2024Q3", "value"] == 9  # the zero fill does not touch the comparative column


def test_zero_fill_refused_without_instance(monkeypatch):
    data = cf(NetCashProvidedByUsedInFinancingActivities=[dur("2025-07-01", "2025-09-30", -5, "2025-10-29")])
    monkeypatch.setattr(sf.sec_segment, "instance", lambda f: None)
    zeros, refused = sf.zero_facts(1, data, ["ProceedsFromIssuanceOfLongTermDebt"], r"^Proceeds\w*Debt", "Short")
    assert zeros == [] and refused and "no XBRL instance" in refused[0]


def frame(rows):
    return pd.DataFrame([(p, v, TS(k)) for p, v, k in rows], columns=["period", "value", "known_from"])


def test_first_available_keeps_the_first_publication_of_an_unchanged_value():
    parts = frame([("2025Q4", 58744, "2026-10-22"), ("2026Q3", 83669, "2026-10-22")])  # noncurrent + current
    noncurrent = frame([("2025Q3", 28834, "2025-10-30"), ("2025Q4", 58744, "2026-01-29"),
                        ("2026Q1", 58748, "2026-04-30")])
    s = sf.first_available([parts, noncurrent])
    first = s.groupby("period")["known_from"].min()
    assert first["2025Q4"] == TS("2026-01-29")


@pytest.mark.parametrize("seed", range(8))
def test_first_available_point_in_time(seed):
    """X2: as of any d, each period comes from the first formula that has it with rows known by d."""
    rnd = random.Random(400 + seed)
    frames = []
    for _ in range(3):
        rows = [(rnd.choice(["2025Q1", "2025Q2", "2025Q3"]), rnd.choice([10, 20, 30]),
                 str(rnd.choice(list(DATES[:15])).date())) for _ in range(rnd.randint(0, 6))]
        frames.append(frame(rows).drop_duplicates(["period", "known_from"]))
    s = sf.first_available(frames)
    for d in list(DATES[:16]) + [x - pd.Timedelta(days=1) for x in DATES[:16]]:
        ref = {}
        for f in frames:
            for p, v in f[f.known_from <= d].sort_values("known_from").groupby("period")["value"].last().items():
                ref.setdefault(p, v)
        assert as_of_rows(s, d) == ref, d


def test_first_available_never_dates_a_period_earlier_than_its_formula():
    a = frame([("2025Q2", 20, "2025-07-30")])
    b = frame([("2025Q2", 99, "2025-07-01"), ("2025Q1", 9, "2025-04-30")])
    s = sf.first_available([a, b])
    assert s[s.period == "2025Q2"]["known_from"].min() >= TS("2025-07-01")


# ------------------------------------------------------------------ 2b. AMD member override, ASML closure


def test_amd_override_keys_are_the_rotated_10q_filing_dates():
    """EDGAR filingDate of AMD's 10-Qs with rotated members (accessions 0000002488-23-000076 ... -24-000163)."""
    assert set(h.AMD_ROTATED) == {"2023-05-03", "2023-08-02", "2023-11-01", "2024-05-01", "2024-07-31", "2024-10-30"}
    assert set(h.MEMBER_OVERRIDES["rev_amd_datacenter"]) == set(h.AMD_ROTATED)


def release(q, measure, figures):
    r = asml_sec.Release(pd.Period(q, "Q"))
    for p, v, d in figures:
        r.add(measure, pd.Period(p, "Q"), v, d)
    return r


def test_asml_bookings_regimes_are_closed_and_exclude_2016_and_2026():
    rel_2017 = release("2017Q1", "net_bookings", [("2016Q4", 2_000, "net bookings"), ("2017Q1", 1_894, "net bookings")])
    rel_2026 = release("2026Q1", "net_bookings", [("2025Q4", 13_158, "net bookings"),
                                                  ("2026Q1", 7_000, "net bookings")])  # a row ASML no longer has
    items = [("2017-04-19", rel_2017), ("2026-04-15", rel_2026)]
    seen = set()
    for key, lo, hi, test, _ in h.ASML_BOOKINGS:
        df = asml_sec.vintages(items, "net_bookings", keep=lambda q, d, lo=lo, hi=hi, test=test: lo <= q <= hi and test(d))
        seen |= set(df["period"])
        assert SPECS[key].closed
    assert "2016Q4" not in seen and "2026Q1" not in seen
    assert "2017Q1" in seen and "2025Q4" in seen


def test_asml_split_table_q2_2013_reads_the_including_column_and_the_previous_quarter():
    """X2 (R3 item 4): the Cymer-split key figures of 17 July 2013 (layout as in the release, numbers as published)."""
    text = ("ASML reports second quarter 2013 results. Q2 2013 ASML (excluding Cymer) June 2013 Cymer* Preliminary "
            "Purchase Price Allocation Q2 2013 ASML (including Cymer) Q1 2013 ASML Net sales 1,155 32 1,187 892 of "
            "which service and field option sales 239 32 271 215 Net bookings, excluding EUV 1,065 1,065 715 Net "
            "bookings, excluding EUV (units) 38 38 25 Gross profit 483 18 (19 ) 482 341")
    rel = asml_sec.parse_release(text)
    assert rel is not None and rel.quarter == pd.Period("2013Q2", "Q")
    assert rel.figures["net_sales"] == {pd.Period("2013Q2", "Q"): (1187.0, "net sales"),
                                        pd.Period("2013Q1", "Q"): (892.0, "net sales")}
    assert {q: v for q, (v, _) in rel.figures["net_bookings"].items()} == {pd.Period("2013Q2", "Q"): 1065.0,
                                                                          pd.Period("2013Q1", "Q"): 715.0}
    assert all(d == "net bookings, excluding euv" for _, d in rel.figures["net_bookings"].values())


def test_asml_presentation_exhibits_are_skipped():
    """The 2017-04-19 6-K's presentation (asml20170418presentatd98.htm) has no bookings row and was parsed first."""
    assert asml_sec.SKIP_DOC.search("asml20170418presentatd98.htm")
    assert not asml_sec.SKIP_DOC.search("pressreleasequarterlyresul.htm")


@pytest.mark.parametrize("seed", range(6))
def test_asml_vintages_point_in_time(seed):
    rnd = random.Random(300 + seed)
    items = []
    for i, d in enumerate(DATES[:12]):
        q = pd.Period(d - pd.Timedelta(days=20), "Q")
        figs = [(str(q), rnd.choice([100, 110, 200]), "x"), (str(q - 1), rnd.choice([100, 110, 200]), "x")]
        items.append((str(d.date()), release(str(q), "net_sales", figs)))
    df = asml_sec.vintages(items, "net_sales")
    for d in DATES[:12]:
        ref = {}
        for filed, rel in sorted(items, key=lambda x: x[0]):
            if TS(filed) <= d:
                for q, (v, _) in rel.figures["net_sales"].items():
                    if str(q) not in ref or abs(ref[str(q)] - v) > 1:
                        ref[str(q)] = v
        assert as_of_rows(df, d) == ref


# ------------------------------------------------------------------ 2c. PJM


# xlsx docProps 'modified' (UTC) of the posted results files and report PDF CreationDate, read 2026-11-23.
PJM_FILE_EVIDENCE = {2020: "2017-05-23", 2021: "2018-05-23", 2022: "2021-06-02", 2023: "2022-06-21",
                     2025: "2024-07-30", 2026: "2025-07-22", 2027: "2025-12-17", 2028: "2026-07-14"}


@pytest.mark.parametrize("dy,evidence", sorted(PJM_FILE_EVIDENCE.items()))
def test_bra_posted_not_before_the_posted_files(dy, evidence):
    assert TS(pjm.BRA_POSTED[dy][0]) >= TS(evidence)


# Load forecast report PDF ModDate / data xlsx 'created' (all before the posting date used).
LF_EVIDENCE = {2017: "2017-01-09", 2018: "2017-12-18", 2019: "2018-12-24", 2020: "2019-12-24", 2021: "2020-12-30",
               2022: "2021-12-20", 2023: "2022-12-12", 2024: "2024-01-31", 2025: "2025-01-22", 2026: "2026-01-05"}


@pytest.mark.parametrize("v,evidence", sorted(LF_EVIDENCE.items()))
def test_load_forecast_posted_not_before_the_files(v, evidence):
    assert TS(pjm.LF_POSTED[v][0]) >= TS(evidence)


def test_pjm_new_auction_fallback_is_after_last_modified():
    assert pjm.posted(pjm.BRA_POSTED, 2029, "Tue, 22 Dec 2026 21:05:00 GMT") == TS("2026-12-23")


def test_pjm_revised_bra_value_is_a_revision_dated_by_the_fetch():
    spec = SPECS["pjm_bra_cleared_rto_a"]
    table = pd.DataFrame({"series": [spec.key], "freq": ["A"], "period": ["2024"], "value": [147_477.4],
                          "known_from": [TS("2023-02-27")], "source": ["release"], "fetched_at": [TS("2026-11-23")]})
    new = pd.DataFrame({"period": ["2024"], "value": [147_478.9], "known_from": [TS("2023-02-27")]})
    rows = observations.new_rows(spec, new, table, fetched_at=pd.Timestamp("2026-12-01").date())
    assert list(zip(rows["value"], rows["known_from"], rows["source"])) == [(147_478.9, TS("2026-12-01"), "revision")]


# ------------------------------------------------------------------ 2d. EIA-930 backfill flags


def test_eia930_first_load_is_backfill_and_later_months_are_fetch_dated():
    spec = SPECS["eia930_avg_pjm_m"]
    empty = pd.DataFrame(columns=observations.COLUMNS)
    first = pd.Series([100.0, 110.0], index=pd.PeriodIndex(["2026-09", "2026-10"], freq="M"))
    rows = observations.new_rows(spec, first, empty, fetched_at=pd.Timestamp("2026-11-23").date())
    assert set(rows["source"]) == {"backfill"}
    assert list(rows["known_from"]) == [TS("2026-10-07"), TS("2026-11-07")]
    second = pd.Series([100.0, 111.0, 120.0], index=pd.PeriodIndex(["2026-09", "2026-10", "2026-11"], freq="M"))
    rows2 = observations.new_rows(spec, second, rows, fetched_at=pd.Timestamp("2026-12-03").date())
    got = {(r.period, r.source): r.known_from for r in rows2.itertuples()}
    assert got == {("2026-10", "revision"): TS("2026-12-03"), ("2026-11", "fetch"): TS("2026-12-03")}


@pytest.mark.parametrize("key,period,expected", [
    ("eia930_avg_pjm_m", "2015-07", "2016-07-25"),  # BA data first public 2016-07-25 (EIA press437)
    ("eia930_avg_pjm_m", "2016-07", "2016-08-07"),  # after that: month end + 7
    ("eia930_peak_erco_m", "2016-06", "2016-07-25"),
    ("eia930_avg_pjm_dom_m", "2018-10", "2019-08-21"),  # sub-region data first public 2019-08-21 (TIE 40993)
    ("eia930_avg_pjm_dom_m", "2019-08", "2019-10-01"),  # then month end + 31 (EIA: sub-region lag 1-30 days)
])
def test_eia930_backfill_not_before_first_publication(key, period, expected):
    """X2 (R3 item 3): backfill rows are floored at the data element's first publication."""
    spec = SPECS[key]
    rows = observations.new_rows(spec, pd.Series([1.0], index=pd.PeriodIndex([period], freq="M")),
                                 pd.DataFrame(columns=observations.COLUMNS), fetched_at=pd.Timestamp("2026-11-23").date())
    assert list(rows["source"]) == ["backfill"] and rows["known_from"].iloc[0] == TS(expected)


def test_eia930_month_needs_two_days_after_its_end():
    hours = pd.DataFrame([("pjm", TS("2026-10-01") + pd.Timedelta(hours=i), 100.0) for i in range(31 * 24)],
                         columns=["area", "ts", "mw"])
    hourly = pd.DataFrame({"area": hours["area"], "date": hours["ts"].dt.normalize(), "hour": hours["ts"].dt.hour + 1,
                           "mw": hours["mw"]})
    assert eia930.monthly(hourly, pd.Timestamp("2026-11-01").date()).empty
    assert len(eia930.monthly(hourly, pd.Timestamp("2026-11-02").date())) == 1


# ------------------------------------------------------------------ 2e. D3 expectations


def test_manifold_trade_at_midnight_belongs_to_the_next_day():
    times = pd.Series([TS("2026-01-01 10:00"), TS("2026-01-02 00:00:00"), TS("2026-01-02 23:59:59.999")])
    df = fv.daily_from_trades(times, pd.Series([0.2, 0.5, 0.7]), TS("2026-01-03"))
    v = df.set_index("period")
    assert v.loc["2026-01-01", "value"] == 0.2 and v.loc["2026-01-01", "known_from"] == TS("2026-01-02")
    assert v.loc["2026-01-02", "value"] == 0.7 and v.loc["2026-01-03", "value"] == 0.7
    for p, kf in zip(df["period"], df["known_from"]):  # every trade used is before known_from
        used = times[times < TS(p) + pd.Timedelta(days=1)]
        assert (used < kf).all()


def test_polymarket_snapshot_is_after_its_week_and_dated_by_the_fetch_day():
    now = TS("2026-11-23 03:37")  # the Monday fetch in collect-weekly
    row = fv.snapshot_row({"outcomes": '["Yes", "No"]', "outcomePrices": '["0.3", "0.7"]'}, now)
    period = pd.Period(row["period"][0], "W-SUN")
    assert row["known_from"][0] > period.end_time  # the week is over
    assert TS("2026-11-23") == row["known_from"][0] <= now  # day convention: < 1 day before the price instant


# ------------------------------------------------------------------ 3. real data (EDGAR / PJM evidence)

@pytest.fixture(scope="module")
def table():
    return observations.load()


# (series, period, first known_from = EDGAR filingDate of the accession, accession)
EDGAR = [
    ("rpo_orcl", "2018Q3", "2018-09-19", "0001564590-18-023315"), ("rpo_orcl", "2025Q3", "2025-09-10", "0001193125-25-200095"),
    ("rpo_orcl", "2025Q4", "2025-12-11", "0001193125-25-315925"), ("rpo_orcl", "2026Q3", "2026-09-11", "0001193125-26-389274"),
    ("rpo_msft", "2017Q3", "2017-10-26", "0001564590-17-020171"), ("rpo_msft", "2020Q2", "2020-07-30", "0001564590-20-034944"),
    ("rpo_msft", "2025Q4", "2026-01-28", "0001193125-26-027207"), ("rpo_msft", "2026Q3", "2026-10-28", "0001193125-26-436133"),
    ("rpo_crwv", "2025Q1", "2025-05-15", "0001769628-25-000014"), ("rpo_crwv", "2025Q4", "2026-03-02", "0001769628-26-000104"),
    ("rev_mu", "2020Q3", "2020-10-19", "0000723125-20-000082"), ("rev_mu", "2024Q4", "2024-12-19", "0000723125-24-000047"),
    ("rev_mu", "2025Q4", "2025-12-18", "0000723125-25-000046"), ("rev_mu", "2026Q3", "2026-10-09", "0000723125-26-000023"),
    ("rev_avgo", "2019Q4", "2020-03-13", "0001730168-20-000045"), ("rev_avgo", "2023Q3", "2023-12-14", "0001730168-23-000096"),
    ("rev_avgo", "2025Q4", "2026-03-11", "0001730168-26-000016"), ("rev_avgo", "2026Q2", "2026-09-10", "0001730168-26-000080"),
    ("rev_mrvl", "2021Q1", "2021-06-09", "0001835632-21-000010"), ("rev_mrvl", "2023Q4", "2024-03-13", "0001835632-24-000009"),
    ("rev_mrvl", "2025Q4", "2026-03-11", "0001835632-26-000011"), ("capex_nvda", "2022Q4", "2023-02-24", "0001045810-23-000017"),
    ("capex_nvda", "2025Q4", "2026-02-25", "0001045810-26-000021"), ("inv_nvda", "2026Q2", "2026-08-26", "0001045810-26-000075"),
    ("purchase_oblig_nvda", "2021Q3", "2021-11-22", "0001045810-21-000163"),
    ("purchase_oblig_nvda", "2026Q1", "2026-05-20", "0001045810-26-000052"),
    ("rev_amd_datacenter", "2023Q1", "2023-05-03", "0000002488-23-000076"),
    ("rev_amd_datacenter", "2024Q1", "2024-05-01", "0000002488-24-000056"),
    ("rev_amd_datacenter", "2025Q1", "2025-05-07", "0000002488-25-000047"),
    ("debt_issued_meta", "2022Q3", "2022-10-27", "0001326801-22-000108"),
    ("debt_issued_meta", "2025Q4", "2026-01-29", "0001628280-26-003942"),
    ("debt_issued_orcl", "2026Q3", "2026-09-11", "0001193125-26-389274"),
    ("cash_sec_orcl", "2025Q4", "2025-12-11", "0001193125-25-315925"), ("rev_orcl", "2026Q3", "2026-09-11", "0001193125-26-389274"),
    ("capex_iren", "2025Q3", "2025-11-06", "0001878848-25-000081"), ("rev_crwv", "2025Q4", "2026-03-02", "0001769628-26-000104"),
    ("asml_net_sales", "2024Q3", "2024-10-15", "0000937966-24-000022"),
    ("asml_net_sales", "2025Q4", "2026-01-28", "0001628280-26-003701"),
    ("asml_net_sales", "2026Q3", "2026-10-14", "0001628280-26-065813"),
    ("asml_net_bookings", "2025Q4", "2026-01-28", "0001628280-26-003701"),
    ("rev_nbis", "2025Q3", "2025-11-12", "0001104659-25-110028"), ("rev_nbis", "2025Q4", "2026-02-12", "0001104659-26-013947"),
    ("rev_nbis", "2026Q3", "2026-11-12", "0001104659-26-126238"),
]


@pytest.mark.real_data
@pytest.mark.skipif(not real_table_exists(), reason="no data fetched (python -m ai_tracker.observations)")
@pytest.mark.parametrize("key,period,filed,accn", EDGAR)
def test_first_known_from_is_the_edgar_filing_date(table, key, period, filed, accn):
    g = table[(table.series == key) & (table.period == period)]
    if g.empty:
        pytest.skip(f"{key} {period} not in table")
    assert g["known_from"].min() == TS(filed)


# AMD Data Center revenue as reported (press releases / correctly labelled 10-K), MUSD: the override must give these.
AMD_DC = {"2023Q1": 1295, "2023Q2": 1321, "2023Q3": 1598, "2023Q4": 2282, "2024Q1": 2337, "2024Q2": 2834,
          "2024Q3": 3549, "2024Q4": 3859, "2025Q1": 3674, "2025Q2": 3240}


@pytest.mark.real_data
@pytest.mark.skipif(not real_table_exists(), reason="no data fetched (python -m ai_tracker.observations)")
def test_amd_datacenter_every_vintage_is_the_reported_value(table):
    g = table[table.series == "rev_amd_datacenter"]
    for p, v in AMD_DC.items():
        assert set(g.loc[g.period == p, "value"]) == {v}, p


@pytest.mark.real_data
@pytest.mark.skipif(not real_table_exists(), reason="no data fetched (python -m ai_tracker.observations)")
def test_debt_flows_have_no_negative_quarters(table):
    """A zero-filled FY over a nonzero 9M would show as a negative Q4: the zero fill must never produce one."""
    g = table[table.series.str.match(r"^debt_(issued|repaid)_")]
    assert not len(g[g.value < 0])


@pytest.mark.real_data
@pytest.mark.skipif(not real_table_exists(), reason="no data fetched (python -m ai_tracker.observations)")
def test_eia930_history_before_first_fetch_is_flagged_backfill(table):
    g = table[table.series.str.startswith("eia930_")]
    first_fetch = g["fetched_at"].min()
    assert set(g.loc[g.known_from < first_fetch, "source"]) <= {"backfill"}


@pytest.mark.real_data
@pytest.mark.skipif(not real_table_exists(), reason="no data fetched (python -m ai_tracker.observations)")
def test_pjm_rows_use_the_posting_table(table):
    for dy, (posted, _) in pjm.BRA_POSTED.items():
        g = table[table.series.str.startswith("pjm_bra_") & (table.period == str(dy))]
        assert set(g["known_from"]) <= {TS(posted)}, dy


@pytest.mark.real_data
@pytest.mark.skipif(not real_table_exists(), reason="no data fetched (python -m ai_tracker.observations)")
@pytest.mark.parametrize("key", ["lt_debt_meta", "lt_debt_hyp4"])
def test_meta_lt_debt_2025q4_known_from_the_10k(table, key):
    g = table[(table.series == key) & (table.period == "2025Q4")]
    assert g["known_from"].min() <= TS("2026-02-07")


@pytest.mark.real_data
@pytest.mark.skipif(not real_table_exists(), reason="no data fetched (python -m ai_tracker.observations)")
def test_manifold_rows_before_selection_are_flagged(table):
    for q in fv.load_urval():
        if q["platform"] != "manifold":
            continue
        g = table[table.series == f"g9_exp_mf_{q['id']}"]
        early = g[g.known_from < TS(q["selected_on"])]
        assert set(early["source"]) <= {"backfill"}, q["id"]


@pytest.mark.real_data
@pytest.mark.skipif(not real_table_exists(), reason="no data fetched (python -m ai_tracker.observations)")
def test_eia930_rows_not_before_first_publication(table):
    from ai_tracker.series import eia930 as s930

    g = table[table.series.str.startswith("eia930_")]
    for key, kf in g.groupby("series")["known_from"].min().items():
        kind = "SUBREGION" if "_dom_" in key else "BALANCE"
        assert kf >= TS(s930.FIRST_PUBLISHED[kind]), key

