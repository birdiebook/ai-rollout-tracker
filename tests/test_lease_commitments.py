"""Leases not yet commenced (A3): CSV validation, sentence split, amounts, series and the sampling check. No network."""

from __future__ import annotations

import csv
import re

import pandas as pd
import pytest

from ai_tracker import catalog, lease_check
from ai_tracker.series import lease_commitments as lseries
from ai_tracker.sources import guidance_capex as gc
from ai_tracker.sources import lease_commitments as lc

URL = "https://www.sec.gov/Archives/edgar/data/789019/000095017026000001/msft-20260930.htm"
ACCN = "0000950170-26-000001"
TEXT = ("Leases. We lease datacenters. Total $ 27,477 $ 70,973 As of September 30, 2026, we had additional operating "
        "and finance leases, primarily for datacenters, that had not yet commenced of $ 7.4 billion and $ 108.7 "
        "billion, respectively. These leases will commence between fiscal year 2027 and fiscal year 2032.")


def row(**kw):
    base = dict(id="msft-2026-09-30-operating", company="msft", period="2026-09-30", lease_type="operating",
                value="7400", unit="MUSD", filed="2026-10-28", form="10-Q", accession=ACCN, source_url=URL,
                locator="sentence #3", sentence_sha256="0" * 64, note="")
    base.update(kw)
    return base


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=lc.COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return path


def test_table_is_split_from_the_sentence_after_it():
    sents = lc.sentences(TEXT)
    k, s = lc.candidate_sentences(TEXT)[0]
    assert s.startswith("As of September 30, 2026, we had additional") and s.endswith("respectively.")
    assert sents[k] == s and "27,477" not in s


def test_amounts_in_musd():
    assert lc.amounts("of $ 7.4 billion and $ 108.7 billion, respectively") == [7400, 108700]
    assert lc.amounts("payments of $606 million and $5.2 billion") == [606, 5200]


@pytest.mark.parametrize("value, text, ok", [
    (108700, "of $ 108.7 billion", True), (108700, "of $108.70 billion", True), (5930, "approximately $ 5.93 billion", True),
    (606, "$606 million", True), (28869, "1,951 20,321 28,869", True), (2026, "fiscal 2026", False),
    (520, "$5.2 billion", False), (28869, "1,028,869", False), (7400, "$ 7.45 billion", False),
])
def test_number_pattern(value, text, ok):
    assert bool(re.search(lc.number_pattern(value), text)) is ok


def test_load_validates(tmp_path):
    good = write_csv(tmp_path / "a.csv", [row(), row(id="msft-2026-09-30-finance", lease_type="finance", value="108700")])
    df = lc.load(good)
    assert list(df["value"]) == [7400, 108700] and df["known_from"].iloc[0] == pd.Timestamp("2026-10-28")
    bad = [row(lease_type="capital"), row(filed="2026-09-30"), row(filed="2027-03-01"), row(value="-1"),
           row(locator="page 5"), row(accession="0000950170-26-000002"), row(sentence_sha256="abc")]
    for i, r in enumerate(bad):
        with pytest.raises(lc.CsvError):
            lc.load(write_csv(tmp_path / f"b{i}.csv", [r]))
    with pytest.raises(lc.CsvError):  # one value per company, period, type and filing
        lc.load(write_csv(tmp_path / "d.csv", [row(), row(id="other")]))


def frame(rows):
    df = pd.DataFrame(rows, columns=lc.COLUMNS)
    df["value"] = pd.to_numeric(df["value"])
    df["known_from"] = pd.to_datetime(df["filed"])
    return df


def test_series_total_from_parts_and_versions():
    df = frame([row(), row(id="f", lease_type="finance", value="108700"),
                row(id="t", period="2026-06-30", lease_type="total", value="300000", filed="2026-07-29",
                    accession="0000950170-26-000000", source_url=URL.replace("000095017026000001", "000095017026000000")),
                # Oracle: balance date 31 August maps to Q3, like its XBRL series
                row(id="o", company="orcl", period="2026-08-31", lease_type="total", value="288000", filed="2026-09-11")])
    s = lc.series_frame(df, "msft")
    assert dict(zip(s["period"], s["value"])) == {"2026Q2": 300000, "2026Q3": 116100}
    assert dict(zip(lc.series_frame(df, "orcl")["period"], lc.series_frame(df, "orcl")["value"])) == {"2026Q3": 288000}


def sentence_row(text=TEXT, value="7400"):
    k, s = lc.candidate_sentences(text)[0]
    return pd.Series(row(locator=f"sentence #{k}", sentence_sha256=gc.sentence_hash(s), value=value))


def test_check_row_statuses():
    r = sentence_row()
    assert lease_check.check_row(r, TEXT) == "ok"
    assert lease_check.check_row(r, "Intro sentence. " + TEXT) == "moved"
    assert lease_check.check_row(sentence_row(value="7500"), TEXT) == "number_not_in_sentence"
    assert lease_check.check_row(r, TEXT.replace("7.4", "7.3")) == "sentence_not_found"


def test_check_row_amount_in_the_sentence_after_the_lease_sentence():
    text = ("As of June 30, 2026, the Company executed additional lease agreements that had not yet commenced. The "
            "aggregate amount of estimated future undiscounted lease payments associated with such leases is $ 35.5 "
            "billion. Other text.")
    s = lc.sentences(text)[1]
    r = pd.Series(row(locator="sentence #1", sentence_sha256=gc.sentence_hash(s), value="35500"))
    assert lease_check.check_row(r, text) == "ok"
    assert lease_check.check_row(r, "Unrelated. " + s) == "not_a_commitment_sentence"


def test_run_samples_every_company_and_reports_failures():
    df = frame([row(), row(id="c", company="crwv", lease_type="total", value="1")])
    res = lease_check.run(0.2, 0, df, fetch=lambda url: TEXT)
    assert set(res["id"]) == {"msft-2026-09-30-operating", "c"}
    assert dict(zip(res["id"], res["status"]))["c"] == "sentence_not_found"


def test_curated_csv_is_valid_and_has_no_text():
    df = lc.load()
    assert set(df["company"]) == set(lc.COMPANIES)
    assert (df["note"].str.len() < 200).all()  # notes are ours; no source sentences in the repo
    for _, r in df.iterrows():
        assert not re.search(r"(?i)we (have|had) additional|not yet commenced of", r["note"])


def test_lease_specs():
    specs = lseries.SPECS
    assert not catalog.validate(specs)
    assert all(s.publish for s in specs)  # R5 reviewed, X3 corrected
    assert {s.key for s in specs} == {f"lease_uncommenced_{c}" for c in lc.COMPANIES} | {"lease_uncommenced_msft_cond"}
    by = {s.key: s for s in specs}
    assert by["lease_uncommenced_msft"].closed and not by["lease_uncommenced_msft_cond"].closed


def test_msft_definition_break_splits_the_series():
    old, new = lseries.frame("msft"), lseries.frame("msft", "new")
    assert old["period"].iloc[-1] == "2026Q1" and new["period"].iloc[0] == "2026Q2"
    assert not set(old["period"]) & set(new["period"])


def test_orcl_series_starts_after_its_last_gap():
    assert lseries.frame("orcl")["period"].iloc[0] == "2023Q4"  # R5-F7/F8: Aug 2023 states no amount
