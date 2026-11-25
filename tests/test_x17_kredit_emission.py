"""X17: KR1 fixes after review R20 (register 2026-11-25, X17). Synthetic documents and the committed lists, no network.

- R20-1: the self-check looks for each number in the tranche's part of the block (key text, column, section).
- R20-2: every corpus document that is not coded is listed with a reason; a final supplement without a term sheet is
  the source, or the build stops; the reverse cover check finds a supplement without a source.
- R20-3: T+n skips US federal holidays and leaves the date to the hand where the calendar cannot decide.
- R20-4: the CSV writer keeps every digit.
- R20-5: coverage per quarter with issuance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from test_credit_issuance import frame, keyed_sheet, row, section_sheet, tranche

from ai_tracker import credit_issuance_check as chk
from ai_tracker.sources import credit_issuance as ci
from ai_tracker.sources import credit_issuance_corpus as cc
from ai_tracker.sources import credit_terms as ct


def _parser_row(lines: list[str], p: dict, **kw) -> pd.Series:
    r = tranche(**{c: p[c] for c in ("currency", "rate_type", "security", "principal", "pricing_date",
                                     "settlement_date", "maturity", "tenor_years", "coupon_pct", "benchmark",
                                     "benchmark_type", "benchmark_yield_pct", "spread_bp", "yield_pct", "price_pct")},
                filed=p["pricing_date"], locator=ci.locator(p),
                block_sha256=cc.block_hash(cc.block_at(lines, ci.locator(p))[0]))
    r.update(kw)
    return frame([r]).iloc[0]


# ------------------------------------------------------------------ R20-1: the tranche's part of the block


def test_key_text_excludes_other_tranches_titles_and_floating_sections():
    ls = cc.lines(keyed_sheet())
    _, parsed = ct.parse(ls, "2023-05-01")
    n28 = parsed[1]
    block, col = cc.block_at(ls, ci.locator(n28))
    own, general = chk.tranche_text(block, col)
    assert "$1,500,000,000" in own and "$2,500,000,000" not in own
    assert "5.600%" not in own  # the Title row names the 2053 Notes after "2028 Notes" but opens nothing
    assert "0.52%" not in own and "$500,000,000" not in own  # the floating section inside the block is general
    assert "May 1, 2023" in general and "May 3, 2023" in general  # dates of the whole offering
    own53, _ = chk.tranche_text(block, 1)
    assert own53.startswith("$2,500,000,000")  # a continuation row that opens with the key


@pytest.mark.parametrize("field, wrong", [("coupon_pct", 5.6), ("yield_pct", 5.619), ("spread_bp", 177.0),
                                          ("price_pct", 99.723), ("benchmark_yield_pct", 3.849),
                                          ("maturity", "2053-05-15")])
def test_another_tranches_number_is_not_accepted(field, wrong):
    ls = cc.lines(keyed_sheet())
    _, parsed = ct.parse(ls, "2023-05-01")
    good = _parser_row(ls, parsed[1])
    assert chk.check_row(good, ls) == ("ok", [])
    bad = good.copy()
    bad[field] = wrong
    bad["method"], bad["note"] = "manual", "test"
    assert chk.check_row(bad, ls) == ("manual", [field])


def test_key_without_colon_opens_and_a_mention_does_not():
    keys = ["2023 Notes", "2024 Notes", "2026 Notes"]
    line = "Maturity Date: | 2023 Notes: May 12, 2023 2024 Notes May 12, 2024 2026 Notes: May 12, 2026"
    assert [k for _, _, k in chk._openings(line, keys)] == keys
    par = "Par Call Date: | 2026 Notes: April 12, 2026 (1 month prior to the maturity date of the 2026 Notes)"
    assert [k for _, _, k in chk._openings(par, keys)] == ["2026 Notes"]
    assert chk._openings("Optional Redemption: | The Issuer may (in the case of the 2023 Notes and 2024 Notes, at "
                         "any time) redeem", keys) == []  # not a keyed value: general
    frn = ("Interest Rate: | In the case of the 2028 Floating Rate Notes, SOFR plus 0.44% per annum. In the case of "
           "the 2029 Floating Rate Notes, SOFR plus 0.56% per annum")
    spans = chk._openings(frn, ["2028 Floating Rate Notes", "2029 Floating Rate Notes", "2028 Notes"])
    assert [k for _, _, k in spans] == ["2028 Floating Rate Notes", "2029 Floating Rate Notes"]


def _column_sheet() -> str:
    return ("<TABLE>" + "<TR><TD>Principal Amount:</TD><TD>$1,000,000,000</TD><TD>$2,000,000,000</TD></TR>"
            "<TR><TD>Maturity Date:</TD><TD>June 1, 2030</TD><TD>June 1, 2035</TD></TR>"
            "<TR><TD>Coupon:</TD><TD>4.000%</TD><TD>4.500%</TD></TR>"
            "<TR><TD>Price to Public:</TD><TD>99.500%</TD><TD>99.000%</TD></TR>"
            "<TR><TD>Spread to Benchmark Treasury:</TD><TD>+60 bps</TD><TD>+80 bps</TD></TR>"
            "<TR><TD>Benchmark Treasury:</TD><TD>4.000% due May 31, 2030</TD><TD>4.250% due May 15, 2035</TD></TR>"
            "<TR><TD>Trade Date:</TD><TD>May 28, 2025</TD></TR></TABLE>")


def test_column_table_uses_the_tranches_cell():
    ls = cc.lines(_column_sheet())
    _, parsed = ct.parse(ls, "2025-05-28")
    second = _parser_row(ls, parsed[1], filed="2025-05-28", settlement_date=None)
    assert chk.check_row(second, ls) == ("ok", [])
    wrong = second.copy()
    wrong["principal"], wrong["method"], wrong["note"] = 1000.0, "manual", "test"
    assert chk.check_row(wrong, ls) == ("manual", ["principal"])
    beyond = second.copy()
    beyond["locator"] = second["locator"].replace("col #1", "col #2")
    assert chk.check_row(beyond, ls) == ("column_not_found", [])


def test_section_rows_keep_the_whole_block():
    ls = cc.lines(section_sheet())
    _, parsed = ct.parse(ls, "2020-03-30")
    block, col = cc.block_at(ls, ci.locator(parsed[0]))
    assert col is None and chk.tranche_text(block, col) == ("\n".join(block), "")


# ------------------------------------------------------------------ R20-2: documents not coded, supplements as source


def _term_sheet() -> str:
    return ("<P>Pricing Term Sheet</P><TABLE>" + row("Trade Date:", "May 28, 2025")
            + row("Settlement Date:", "June 2, 2025") + row("Principal Amount:", "$1,000,000,000")
            + row("Maturity:", "June 1, 2031") + row("Coupon:", "4.000%")
            + row("Price to Public:", "99.500% of the principal amount")
            + row("Benchmark Treasury:", "UST 4.000% due May 31, 2030")
            + row("Spread to Benchmark Treasury:", "T+80 bps")
            + "</TABLE>")


def _final_supplement(coupon: str = "4.000%") -> str:
    return (f"<P>Prospectus Supplement</P><P>$1,000,000,000</P><P>Example Corp.</P>"
            f"<P>$1,000,000,000 {coupon} Notes due 2031</P><P>FINAL PRICING TERMS</P><TABLE>"
            + row("Principal Amount:", "$1,000,000,000") + row("Maturity:", "June 1, 2031")
            + row("Coupon:", coupon) + row("Price to Public:", "99.500% of the principal amount")
            + row("Trade Date:", "May 28, 2025") + "</TABLE>")


def _doc(url: str, form: str, filed: str, n: int) -> dict:
    return {"company": "orcl", "form": form, "url": url, "accession": f"0001193125-25-00000{n}", "filed": filed,
            "accepted": f"{filed}T21:0{n}:00.000Z"}


def test_every_document_not_coded_is_listed_with_its_reason():
    docs = {"fwp": cc.lines(_term_sheet()), "final": cc.lines(_final_supplement()),
            "prelim": cc.lines("<P>Subject to Completion</P>" + _final_supplement()),
            "equity": cc.lines("<P>Prospectus Supplement</P><P>10,000,000 Shares of Common Stock</P>"),
            "press": cc.lines("<P>Example Corp. announces a financing plan</P>")}
    meta = [_doc("prelim", "424B2", "2025-05-27", 1), _doc("fwp", "FWP", "2025-05-28", 2),
            _doc("press", "FWP", "2025-05-28", 3), _doc("final", "424B2", "2025-05-30", 4),
            _doc("equity", "424B5", "2025-05-30", 5)]
    rows, skipped = ci.rows_from_documents(meta, fetch=docs.__getitem__)
    assert {r["accession"] for r in rows} == {"0001193125-25-000002"}
    assert [(s["accession"][-1], s["why"]) for s in skipped] == [
        ("1", "preliminary"), ("3", "no final debt terms"), ("4", "final supplement of 0001193125-25-000002"),
        ("5", "no final debt terms")]
    assert not any(s.get("hand") for s in skipped)


def test_final_supplement_without_term_sheet_is_the_source_or_stops_the_build():
    meta = [_doc("final", "424B2", "2025-05-30", 4)]
    rows, skipped = ci.rows_from_documents(meta, fetch={"final": cc.lines(_final_supplement())}.__getitem__)
    assert [(r["form"], r["principal"], r["coupon_pct"], r["maturity"]) for r in rows] == [
        ("424B2", 1000.0, 4.0, "2031-06-01")] and skipped == []
    # the parser does not read the cover's tranches (the table says 4.100%, the cover 4.000%): not coded, flagged
    odd = cc.lines(_final_supplement().replace("<TD>4.000%</TD>", "<TD>4.100%</TD>"))
    rows, skipped = ci.rows_from_documents(meta, fetch={"final": odd}.__getitem__)
    assert rows == [] and skipped[0]["hand"] and ct.HAND in skipped[0]["why"]


def test_source_of_needs_the_window_or_the_same_tranches():
    cover = {("USD", 1000.0, "4.0000", "2031")}
    two = cover | {("USD", 500.0, "F", "2027")}
    src = [{"company": "orcl", "filed": "2025-05-28", "accession": "a", "tranches": two}]
    assert ci.source_of("orcl", "2025-06-04", cover, src) == "a"  # 7 days, one tranche in common
    assert ci.source_of("orcl", "2025-06-05", cover, src) is None
    assert ci.source_of("meta", "2025-05-30", cover, src) is None
    assert ci.source_of("orcl", "2026-01-05", two, src) == "a"  # the same tranches, outside the window


def test_reverse_cover_check_finds_a_supplement_without_source(monkeypatch):
    lines = cc.lines(_term_sheet())
    _, parsed = ct.parse(lines, "2025-05-28")
    url = "https://www.sec.gov/Archives/edgar/data/1341439/000119312525000002/fwp.htm"
    df = frame([tranche(**{c: parsed[0][c] for c in ("currency", "rate_type", "principal", "pricing_date",
                                                      "settlement_date", "maturity", "tenor_years", "coupon_pct")},
                        company="orcl", filed="2025-05-28", source_url=url, accession="0001193125-25-000002",
                        id="orcl_2025-05-28_01")])
    monkeypatch.setattr(ci, "load", lambda path=None: df)
    monkeypatch.setattr(cc, "BULK_SLEEP", 0)
    subs = {"orcl": [{"form": "FWP", "filed": "2025-05-28", "accession": "0001193125-25-000002",
                      "accepted": "", "primary": "fwp.htm"},
                     {"form": "424B2", "filed": "2025-05-30", "accession": "0001193125-25-000004",
                      "accepted": "", "primary": "s1.htm"},
                     {"form": "424B2", "filed": "2025-09-30", "accession": "0001193125-25-000009",
                      "accepted": "", "primary": "s2.htm"}]}
    docs = {"s1.htm": cc.lines(_final_supplement()), "s2.htm": cc.lines(_final_supplement("5.000%"))}
    cov = chk.covers(fetch=lambda u: docs[u.rsplit("/", 1)[1]], submissions=lambda co: subs.get(co, []))
    got = {(r.check, r.final_accession, r.status) for r in cov.itertuples()}
    assert got == {("source", "0001193125-25-000004", "ok"), ("supplement", "0001193125-25-000004", "ok"),
                   ("supplement", "0001193125-25-000009", "no_source")}


def test_committed_skipped_list_accounts_for_the_whole_corpus():
    if not ci.SKIPPED_PATH.exists():
        pytest.skip("no curated file")
    from test_r20_kredit_emission import FINAL_SUPPLEMENTS

    sk, df = ci.load_skipped(), ci.load()
    assert list(sk.columns) == ci.SKIPPED_COLUMNS and sk["why"].str.len().min() > 0
    assert not set(sk["accession"]) & set(df["accession"]) and sk["accession"].is_unique
    assert len(sk) + df["accession"].nunique() == 146  # the corpus (docs/kallor/kredit_emission.md)
    assert sk["form"].value_counts().to_dict() == {"424B5": 56, "424B2": 43, "FWP": 8}
    covered = sk[sk["why"].str.startswith("final supplement of ")]
    assert dict(zip(covered["why"].str.split().str[-1], covered["accession"])) == {
        k: v[0] for k, v in FINAL_SUPPLEMENTS.items()}  # R20's pairs, read independently
    assert sk["why"].str.replace(r" 0\d{9}-\d{2}-\d{6}$", "", regex=True).value_counts().to_dict() == {
        "preliminary": 47, "final supplement of": 39, "no final debt terms": 18, "no debt tranche on the cover": 2,
        "re-filing of": 1}
    assert not sk["why"].str.contains(ct.HAND).any()


# ------------------------------------------------------------------ R20-3: holidays


def test_t_plus_n_uses_the_us_federal_calendar_and_leaves_unclear_days_to_the_hand():
    assert ct.add_business_days("2026-11-24", 2) == "2026-11-27"  # Thanksgiving
    assert ct.add_business_days("2026-01-16", 1) == "2026-01-20"  # Martin Luther King Jr. Day
    assert ct.add_business_days("2026-04-01", 2) is None  # Good Friday 2026-04-03
    assert ct.add_business_days("2026-07-01", 2) is None  # July 4 on a Saturday, observed Friday 2026-07-03
    assert ct.add_business_days("2026-07-01", 1) == "2026-07-02"
    assert ct.add_business_days("2026-05-05", 2, "EUR") is None  # no calendar for the currency


def test_parser_note_says_code_by_hand_and_load_refuses_it(tmp_path, monkeypatch):
    html = ("<P>Pricing Term Sheet</P><TABLE>" + row("Trade Date:", "April 1, 2026")
            + row("Settlement Date:", "T+2") + row("Principal Amount:", "$1,000,000,000")
            + row("Maturity:", "April 6, 2036") + row("Coupon:", "4.000%") + row("Price to Public:", "99.500%")
            + "</TABLE>")
    _, (p,) = ct.parse(cc.lines(html), "2026-04-01")
    assert p["settlement_date"] is None and ct.HAND in p["note"]
    _, (q,) = ct.parse(cc.lines(html.replace("April 1, 2026", "April 7, 2026")), "2026-04-07")
    assert q["settlement_date"] == "2026-04-09" and q["note"].startswith("settlement_date computed from T+n")
    monkeypatch.setattr(ci, "BLOCKS_DIR", tmp_path / "blocks")
    path = tmp_path / "c.csv"
    ci.write([tranche(settlement_date="", note=p["note"])], path)
    with pytest.raises(ci.CsvError, match="by hand"):
        ci.load(path)
    ci.write([tranche(settlement_date="2021-05-12", note=p["note"] + "; settlement date from the final 424B2",
                      method="manual")], path)
    assert len(ci.load(path)) == 1


# ------------------------------------------------------------------ R20-4: no rounding


def test_numbers_are_written_with_every_digit():
    assert [ci._text(x) for x in (1250.0, np.float64(99.12345), 1234567.0, 0.1, 117.3, float("nan"), None, "x")] == [
        "1250", "99.12345", "1234567", "0.1", "117.3", "", "", "x"]
    assert float(ci._text(np.float64(1 / 3))) == 1 / 3


# ------------------------------------------------------------------ R20-5: coverage per quarter


def test_coverage_per_quarter_with_issuance():
    df = frame([tranche(company="orcl", settlement_date="2025-09-26", pricing_date="2025-09-24", filed="2025-09-24",
                        maturity="2035-09-26", principal=18000, id="orcl_2025-09-24_01"),
                tranche(company="orcl", settlement_date="2025-12-03", pricing_date="2025-12-01", filed="2025-12-01",
                        maturity="2035-12-03", principal=5000, id="orcl_2025-12-01_01")])
    xb = pd.DataFrame({"period": ["2025Q3", "2025Q4"], "value": [100.0, 17880.0]})
    cov = ci.coverage(df, {"orcl": xb})
    assert list(cov.columns) == ci.COVERAGE_COLUMNS
    year = cov[(cov["year"] == "2025") & (cov["quarter"] == "")].iloc[0]
    assert (year["term_sheets"], year["xbrl"], year["later"]) == (18000, 17980, 0)
    q4 = cov[cov["quarter"] == "2025Q4"].iloc[0]
    assert (q4["term_sheets"], q4["xbrl"], q4["xbrl_quarters"]) == (18000, 17880, 1)
    assert q4["share"] == pytest.approx(18000 / 17880)
    later = cov[cov["quarter"] == "2026Q1"].iloc[0]  # Oracle's Dec-Feb quarter, not in XBRL yet
    assert (later["term_sheets"], later["later"], later["xbrl_quarters"]) == (0, 5000, 0) and pd.isna(later["share"])
    assert "2025Q3" not in set(cov["quarter"])  # no issuance in that quarter
