"""KR1: spread at issuance. Synthetic term sheets and rows only, no network."""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import credit_issuance_check as chk
from ai_tracker.sources import credit_issuance as ci
from ai_tracker.sources import credit_issuance_corpus as cc
from ai_tracker.sources import credit_terms as ct


def row(label: str, value: str) -> str:
    return f'<TR><TD VALIGN="top"><P>{label}</P></TD><TD>&nbsp;&nbsp;</TD><TD>{value}</TD></TR>\n'


def keyed_sheet() -> str:
    """Two fixed tranches keyed by name (with a continuation row, Meta style) and one floating rate section."""
    return (
        "<html><body><P>Filed Pursuant to Rule 433</P><P>Issuer Free Writing Prospectus dated May 1, 2023</P>"
        "<P>Example Corp.</P><P>Floating Rate Notes due 2025</P><P>4.600% Notes due 2028</P>"
        "<P>5.600% Notes\ndue 2053</P><P>Pricing Term Sheet</P><TABLE>"
        + row("Issuer:", "Example Corp. (the &#8220;Company&#8221;)")
        + row("Trade Date:", "May 1, 2023")
        + row("Settlement Date (T+2):", "May 3, 2023")
        + "</TABLE><P>Floating Rate Notes due 2025</P><TABLE>"
        + row("Aggregate Principal Amount:", "$500,000,000")
        + row("Maturity Date:", "May 3, 2025")
        + row("Coupon (Interest Rate):", "Compounded SOFR, reset quarterly, plus 0.52% per annum")
        + row("Public Offering Price:", "100.000% of principal amount")
        + "</TABLE><P>Fixed Rate Notes</P><TABLE>"
        + row("Title:", "4.600% Notes due 2028 (the &#8220;2028 Notes&#8221;) 5.600% Notes due 2053 "
                        "(the &#8220;2053 Notes&#8221;)")
        + row("Principal Amount:", "<P>2028 Notes: $1,500,000,000</P>")
        + "<TR><TD></TD><TD></TD><TD><P>2053 Notes: $2,500,000,000</P></TD></TR>"
        + row("Maturity:", "2028 Notes: May 15, 2028 2053 Notes: May 15, 2053")
        + row("Public Offering Price:", "2028 Notes: 99.976% 2053 Notes: 99.723%")
        + row("Coupon (Interest Rate):", "2028 Notes: 4.600% 2053 Notes: 5.600%")
        + row("Yield to Maturity:", "2028 Notes: 4.605% 2053 Notes: 5.619%")
        + row("Spread to Benchmark Treasury:", "2028 Notes: T + 95 bps 2053 Notes: T + 177 bps")
        + row("Benchmark Treasury:", "2028 Notes: UST 3.500% due April 30, 2028 2053 Notes: UST 4.000% due "
                                     "November 15, 2052")
        + row("Benchmark Treasury Price/Yield:", "2028 Notes: 99-09+ and 3.655% 2053 Notes: 102-21 and 3.849%")
        + row("Optional Redemption:", "2028 Notes: make-whole call at the Treasury Rate plus 15 basis points")
        + "</TABLE><P>2</P></body></html>")


def section_sheet() -> str:
    """Oracle style: a heading and its own rows per tranche."""
    def tranche(head, amount, maturity, coupon, price, bench, by, spread, yld):
        return (f"<P>{head}</P><TABLE>" + row("Issuer:", "Example Corp.") + row("Principal Amount:", amount)
                + row("Maturity:", maturity) + row("Coupon:", coupon) + row("Price to Public:", price)
                + row("Benchmark Treasury:", bench) + row("Benchmark Treasury Yield:", by)
                + row("Spread to Benchmark Treasury:", spread) + row("Yield:", yld)
                + row("Trade Date:", "March 30, 2020") + row("Settlement Date:", "April 1, 2020 (T+2)") + "</TABLE>")
    return ("<html><body><P>FINAL PRICING TERM SHEET</P>"
            + tranche("2.500 % Notes due 2025 (&#8220;2025 Notes&#8221;)", "$3,500,000,000", "April 1, 2025",
                      "2.500%", "99.963% of the principal amount", "0.500% due March 31, 2025", "0.408%",
                      "+ 210 basis points", "2.508%")
            + tranche("2.950% Notes due 2030 (&#8220;2030 Notes&#8221;)", "$3,250,000,000", "April 1, 2030",
                      "2.950%", "99.897% of the principal amount", "1.500% due February 15, 2030", "0.712%",
                      "+ 225 basis points", "2.962%")
            + "</body></html>")


# ------------------------------------------------------------------ text


def test_lines_keep_table_rows_and_drop_layout_breaks():
    ls = cc.lines(keyed_sheet())
    assert "Principal Amount: | 2028 Notes: $1,500,000,000" in ls
    assert "5.600% Notes due 2053" in ls  # a line break in the source is layout only
    assert "2053 Notes: $2,500,000,000" in ls  # an empty cell is dropped
    assert all(x == x.strip() and x for x in ls)


def test_block_hash_and_locator():
    ls = cc.lines(keyed_sheet())
    block, col = cc.block_at(ls, "lines #2-#4 col #1")
    assert block == ls[2:5] and col == 1
    assert cc.block_hash(block) == cc.block_hash([x + "  " for x in block])  # normalized per line
    with pytest.raises(ValueError):
        cc.block_at(ls, "sentence #3")


def test_kind():
    assert cc.kind(cc.lines(keyed_sheet())) == "final"
    assert cc.kind(cc.lines("<P>SUBJECT TO COMPLETION</P>" + keyed_sheet())) == "preliminary"
    assert cc.kind(cc.lines("<P>Pricing Term Sheet</P><P>100,000,000 shares of Class A Common Stock</P>")) == "other"


# ------------------------------------------------------------------ parser


def test_parse_keyed_with_floating_section():
    layout, rows = ct.parse(cc.lines(keyed_sheet()), "2023-05-01")
    assert layout == "keyed+sections"
    assert [r["security"] for r in rows] == ["Floating Rate Notes due 2025", "4.600% Notes due 2028",
                                             "5.600% Notes due 2053"]
    frn, n28, n53 = rows
    assert frn["rate_type"] == "floating" and frn["principal"] == 500 and frn["spread_bp"] == 52
    assert frn["benchmark_type"] == "sofr" and frn["coupon_pct"] is None and frn["col"] is None
    assert n28 == {**n28, "currency": "USD", "rate_type": "fixed", "principal": 1500, "pricing_date": "2023-05-01",
                   "settlement_date": "2023-05-03", "maturity": "2028-05-15", "coupon_pct": 4.6, "spread_bp": 95,
                   "benchmark_type": "treasury", "benchmark_yield_pct": 3.655, "yield_pct": 4.605,
                   "price_pct": 99.976, "col": 0}
    assert n53["principal"] == 2500 and n53["spread_bp"] == 177 and n53["benchmark_yield_pct"] == 3.849
    assert n53["benchmark"] == "UST 4.000% due November 15, 2052"
    assert n28["tenor_years"] == 5.04 and n53["tenor_years"] == 30.04


def test_parse_sections():
    layout, rows = ct.parse(cc.lines(section_sheet()), "2020-03-30")
    assert layout == "sections"
    assert [(r["security"], r["principal"], r["spread_bp"], r["coupon_pct"]) for r in rows] == [
        ("2.500 % Notes due 2025", 3500, 210, 2.5), ("2.950% Notes due 2030", 3250, 225, 2.95)]
    assert all(r["settlement_date"] == "2020-04-01" and r["pricing_date"] == "2020-03-30" for r in rows)
    assert rows[0]["benchmark_yield_pct"] == 0.408 and rows[1]["yield_pct"] == 2.962
    assert rows[0]["a"] < rows[0]["b"] < rows[1]["a"]  # each tranche has its own block


def test_parse_columns():
    html = ("<TABLE>" + "<TR><TD>Principal Amount:</TD><TD>$1,000,000,000</TD><TD>$2,000,000,000</TD></TR>"
            "<TR><TD>Maturity Date:</TD><TD>June 1, 2030</TD><TD>June 1, 2035</TD></TR>"
            "<TR><TD>Coupon:</TD><TD>4.000%</TD><TD>4.500%</TD></TR>"
            "<TR><TD>Price to Public:</TD><TD>99.500%</TD><TD>99.000%</TD></TR>"
            "<TR><TD>Spread to Benchmark Treasury:</TD><TD>+60 bps</TD><TD>+80 bps</TD></TR>"
            "<TR><TD>Benchmark Treasury:</TD><TD>4.000% due May 31, 2030</TD><TD>4.250% due May 15, 2035</TD></TR>"
            "<TR><TD>Trade Date:</TD><TD>May 28, 2025</TD></TR></TABLE>")
    layout, rows = ct.parse(cc.lines(html), "2025-05-28")
    assert layout == "columns"
    assert [(r["principal"], r["spread_bp"], r["col"], r["maturity"]) for r in rows] == [
        (1000, 60, 0, "2030-06-01"), (2000, 80, 1, "2035-06-01")]


@pytest.mark.parametrize("text, bp", [
    ("T + 45 bps", 45), ("T+45", 45), ("+ 210 basis points", 210), ("0.250% (+25 basis points)", 25),
    ("+0.45%", 45), ("+ 66.7 bps", 66.7), ("+50 bps versus the applicable Government of Canada curve; +51.6 bps "
                                          "versus the applicable Benchmark Bond", 51.6), ("", None)])
def test_spread_as_stated(text, bp):
    assert ct.spread_bp(text) == bp


@pytest.mark.parametrize("text, out", [
    ("$1,250,000,000", ("USD", 1250)), ("$1.25 billion", ("USD", 1250)), ("€750,000,000", ("EUR", 750)),
    ("¥135,500,000,000", ("JPY", 135500)), ("C$1,500,000,000", ("CAD", 1500)), ("£750,000,000", ("GBP", 750)),
    ("none", None)])
def test_money(text, out):
    assert ct.money(text) == out


def test_frn_margin_and_t_plus():
    assert ct.frn_spread_bp("Compounded SOFR ... plus 53 basis points (0.530)% per annum") == 53
    assert ct.frn_spread_bp("EURIBOR plus 0.35% per annum") == 35
    assert ct.t_plus("Settlement Date (T+ 4)**") == 4
    assert ct.add_business_days("2026-10-29", 4) == "2026-11-04"  # Thursday + 4 business days


def test_keyed_split_prefers_longest_key():
    parts = ct._split_keyed("2028 Floating Rate Notes: $1,000 2028 Notes: $2,000",
                            ["2028 Notes", "2028 Floating Rate Notes"])
    assert parts == {"2028 Floating Rate Notes": "$1,000", "2028 Notes": "$2,000"}
    assert not ct.starts_with_key("Applicable EURIBOR rate; the 2028 Notes are...", ["2028 Notes"])
    assert ct.starts_with_key("In the case of the 2028 Notes, SOFR plus 0.44%", ["2028 Notes"])


# ------------------------------------------------------------------ rows and series


def tranche(**kw) -> dict:
    base = dict(id="", company="amzn", currency="USD", rate_type="fixed", security="4.000% Notes due 2031",
                principal=1000.0, pricing_date="2021-05-10", settlement_date="2021-05-12", maturity="2031-05-12",
                tenor_years=None, coupon_pct=4.0, benchmark="UST 4% due 2031", benchmark_type="treasury",
                benchmark_yield_pct=3.5, spread_bp=50.0, yield_pct=4.0, price_pct=99.9, filed="2021-05-11",
                accepted="2021-05-11T17:01:00.000Z", form="FWP",
                source_url="https://www.sec.gov/Archives/edgar/data/1018724/000119312521156519/x.htm",
                accession="0001193125-21-156519", locator="lines #1-#9 col #0", block_sha256="a" * 64,
                method="parser", note="")
    base.update(kw)
    if base["tenor_years"] is None:
        base["tenor_years"] = ct.tenor_years(base["pricing_date"], base["maturity"])
    if not base["id"]:
        base["id"] = f"{base['company']}_{base['pricing_date']}_01"
    return base


def frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=ci.COLUMNS)
    for c in ci.NUMERIC:
        df[c] = pd.to_numeric(df[c])
    return df


def test_band_edges():
    rows = [tranche(maturity=m, pricing_date="2020-01-01", filed="2020-01-01", id=f"amzn_2020-01-01_{i:02d}")
            for i, m in enumerate(["2026-06-27", "2026-07-02", "2032-06-29", "2032-07-02"])]
    df = frame(rows)
    assert list(df["tenor_years"]) == [6.49, 6.5, 12.49, 12.5]
    assert list(ci.eligible_spread(df, ci.BAND_7_12)["tenor_years"]) == [6.5, 12.49]


def test_weighting_gap_rule_and_eligibility():
    df = frame([
        tranche(principal=1000, spread_bp=50, id="amzn_2021-05-10_01"),
        tranche(principal=3000, spread_bp=100, id="amzn_2021-05-10_02"),
        tranche(rate_type="floating", coupon_pct=None, benchmark_type="sofr", spread_bp=30, principal=500,
                id="amzn_2021-05-10_03"),
        tranche(currency="EUR", benchmark_type="mid_swaps", spread_bp=200, principal=900, id="amzn_2021-05-10_04"),
        tranche(pricing_date="2022-04-11", filed="2022-04-11", maturity="2032-04-13", spread_bp=85,
                id="amzn_2022-04-11_01"),
    ])
    s = ci.spread(df, as_of="2026-01-01")
    assert list(s["period"]) == ["2021Q2", "2022Q2"]  # 2021Q3..2022Q1 are gaps, not zero
    assert s["value"].iloc[0] == pytest.approx((1000 * 50 + 3000 * 100) / 4000)  # floating and EUR left out
    iss = ci.issuance(df, "amzn", as_of="2026-01-01")
    assert list(iss["value"]) == [4500, 1000]  # USD fixed and floating, no EUR
    assert ci.issuance(df, "meta", as_of="2026-01-01").empty


def test_dating_late_filing_and_unfinished_quarter():
    df = frame([
        tranche(pricing_date="2021-06-29", filed="2021-06-30", maturity="2031-06-30", principal=1000, spread_bp=50,
                id="amzn_2021-06-29_01"),
        tranche(pricing_date="2021-06-30", filed="2021-07-06", maturity="2031-07-02", principal=1000, spread_bp=70,
                id="amzn_2021-06-30_01"),
    ])
    s = ci.spread(df, as_of="2026-01-01")
    assert list(s["known_from"]) == [pd.Timestamp("2021-07-01"), pd.Timestamp("2021-07-06")]
    assert list(s["value"]) == [50, 60]  # the late filing is a new version of the same quarter
    assert ci.spread(df, as_of="2021-06-30").empty  # the quarter has not ended
    assert len(ci.spread(df, as_of="2021-07-01")) == 1
    late = ci.issuance(df, "amzn", as_of="2026-01-01")
    assert list(late["value"]) == [1000, 2000]
    assert (late["known_from"] > pd.Timestamp("2021-06-30")).all()  # never before the quarter's end


def test_spread_issuers_need_four_quarters():
    rows = [tranche(company="orcl", pricing_date=f"{y}-03-01", filed=f"{y}-03-01", maturity=f"{y + 10}-03-01",
                    id=f"orcl_{y}-03-01_01") for y in (2020, 2021, 2022, 2023)]
    rows += [tranche(company="msft", pricing_date=f"{y}-03-01", filed=f"{y}-03-01", maturity=f"{y + 10}-03-01",
                     id=f"msft_{y}-03-01_01") for y in (2020, 2021, 2022)]
    assert ci.spread_issuers(frame(rows)) == ["orcl"]


def test_csv_roundtrip_and_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(ci, "BLOCKS_DIR", tmp_path / "blocks")
    path = tmp_path / "c.csv"
    good = [tranche(), tranche(id="amzn_2021-05-10_02", rate_type="floating", coupon_pct=None,
                               benchmark_type="sofr", benchmark_yield_pct=None, yield_pct=None, spread_bp=44.0)]
    ci.write(good, path)
    df = ci.load(path)
    assert len(df) == 2 and df["principal"].dtype.kind in "if" and df["coupon_pct"].isna().iloc[1]
    bad = [
        dict(block_sha256="xyz"), dict(accession="0001193125-21-999999"), dict(tenor_years=9.0),
        dict(currency="EUR"), dict(filed="2021-06-30"), dict(method="manual"), dict(locator="sentence #3"),
        dict(rate_type="floating"), dict(price_pct=None), dict(id="amzn_2021-05-11_01"),
    ]
    for b in bad:
        ci.write([tranche(**b)], path)
        with pytest.raises(ci.CsvError):
            ci.load(path)


def test_rows_from_documents_skips_refiling_and_applies_manual(monkeypatch):
    sheet = cc.lines(section_sheet())
    docs = {"u1": sheet, "u2": sheet, "u3": cc.lines("<P>SUBJECT TO COMPLETION</P>" + section_sheet())}
    meta = [dict(company="orcl", form="FWP", url=u, accession=f"0001193125-20-00000{i}", filed="2020-03-30",
                 accepted=f"2020-03-30T1{i}:00:00.000Z") for i, u in enumerate(["u3", "u1", "u2"])]
    monkeypatch.setitem(ci.MANUAL, ("orcl", "2020-03-30", "2.950% Notes due 2030"), {"principal": 3000.0,
                                                                                     "note": "test"})
    rows, skipped = ci.rows_from_documents(meta, fetch=docs.__getitem__)
    assert [r["id"] for r in rows] == ["orcl_2020-03-30_01", "orcl_2020-03-30_02"]
    assert rows[1]["method"] == "manual" and rows[1]["principal"] == 3000 and rows[1]["note"] == "test"
    assert [s["why"] for s in skipped] == ["preliminary", "re-filing of 0001193125-20-000001"]
    assert rows[0]["block_sha256"] == cc.block_hash(cc.block_at(sheet, rows[0]["locator"])[0])


def test_oracle_fiscal_quarters_and_coverage():
    assert [ci.fiscal_calendar_quarter("orcl", d) for d in
            ("2025-06-01", "2025-09-26", "2025-12-05", "2026-02-04", "2026-03-01")] == [
        "2025Q3", "2025Q4", "2026Q1", "2026Q1", "2026Q2"]
    assert ci.fiscal_calendar_quarter("amzn", "2025-09-30") == "2025Q3"
    df = frame([tranche(company="orcl", settlement_date="2025-09-26", pricing_date="2025-09-24", filed="2025-09-24",
                        maturity="2035-09-26", principal=18000, id="orcl_2025-09-24_01")])
    xb = pd.DataFrame({"period": ["2025Q3", "2025Q4"], "value": [100.0, 17800.0]})
    cov = ci.coverage(df, {"orcl": xb})
    row = cov[cov["year"] == "2025"].iloc[0]
    assert row["term_sheets"] == 18000 and row["xbrl"] == 17900 and row["share"] == pytest.approx(18000 / 17900)
    assert row["later"] == 0
    late = ci.coverage(df, {"orcl": xb[xb["period"] == "2025Q3"]})
    assert late.iloc[0]["term_sheets"] == 0 and late.iloc[0]["later"] == 18000


# ------------------------------------------------------------------ self-check


def checked_row(sheet_lines, **kw) -> pd.Series:
    _, parsed = ct.parse(sheet_lines, "2023-05-01")
    p = parsed[1]
    r = tranche(**{c: p[c] for c in ("currency", "rate_type", "security", "principal", "pricing_date",
                                     "settlement_date", "maturity", "tenor_years", "coupon_pct", "benchmark",
                                     "benchmark_type", "benchmark_yield_pct", "spread_bp", "yield_pct",
                                     "price_pct")},
                filed="2023-05-01", locator=ci.locator(p),
                block_sha256=cc.block_hash(cc.block_at(sheet_lines, ci.locator(p))[0]))
    r.update(kw)
    return frame([r]).iloc[0]


def test_check_row_ok_moved_and_errors():
    ls = cc.lines(keyed_sheet())
    assert chk.check_row(checked_row(ls), ls) == ("ok", [])
    assert chk.check_row(checked_row(ls), ["extra line"] + ls)[0] == "moved"
    assert chk.check_row(checked_row(ls, block_sha256="0" * 64), ls) == ("block_not_found", [])
    assert chk.check_row(checked_row(ls, principal=1600.0), ls) == ("number_not_in_block", ["principal"])
    assert chk.check_row(checked_row(ls, benchmark_type="other"), ls) == ("parse_differs", ["benchmark_type"])
    assert chk.check_row(checked_row(ls, principal=1600.0, method="manual", note="x"), ls) == ("manual",
                                                                                              ["principal"])


def test_check_row_yield_gap():
    ls = cc.lines(keyed_sheet().replace("2028 Notes: 4.605%", "2028 Notes: 4.705%"))
    assert chk.check_row(checked_row(ls), ls)[0] == "yield_gap"


def test_check_dates():
    r = checked_row(cc.lines(keyed_sheet()))
    good = {r["accession"]: {"filed": "2023-05-01", "accepted": r["accepted"]}}
    assert chk.check_dates(r, good) == "ok"
    assert chk.check_dates(r, {}) == "accession_not_in_submissions"
    assert chk.check_dates(r, {r["accession"]: {"filed": "2023-05-02", "accepted": ""}}).startswith("filed_differs")


def test_number_patterns():
    assert any(__import__("re").search(p, "Size: $1.25 billion") for p in chk.amount_patterns("USD", 1250))
    assert any(__import__("re").search(p, "€750,000,000") for p in chk.amount_patterns("EUR", 750))
    assert not any(__import__("re").search(p, "$7,500,000,000") for p in chk.amount_patterns("USD", 750))
    assert any(__import__("re").search(p, "0.450% (+45 basis points)") for p in chk.spread_patterns(45))


def test_cover_cross_check():
    cover = cc.lines("<P>PROSPECTUS SUPPLEMENT</P><P>$17,500,000,000</P><P>$500,000,000 Floating Notes due 2028</P>"
                     "<P>$1,000,000,000 3.875% Notes due 2028</P><P>€750,000,000 2.500% Senior Notes due 2029</P>")
    assert chk.cover_tranches(cover) == {("USD", 500.0, "F", "2028"), ("USD", 1000.0, "3.8750", "2028"),
                                         ("EUR", 750.0, "2.5000", "2029")}
    rows = frame([tranche(currency="USD", principal=1000, coupon_pct=3.875, maturity="2028-11-15")])
    assert chk.row_tranches(rows) == {("USD", 1000.0, "3.8750", "2028")}


def test_section_without_heading_keeps_its_own_block():
    html = ("<TABLE>" + row("Principal Amount:", "$1,000,000,000") + row("Maturity:", "June 1, 2030")
            + row("Coupon:", "4.000%") + row("Price to Public:", "99.500%") + row("Trade Date:", "May 28, 2025")
            + "</TABLE>")
    layout, rows = ct.parse(cc.lines(html), "2025-05-28")
    assert layout == "sections" and rows[0]["col"] is None and ci.locator(rows[0]) == "lines #0-#4"


def test_catalog_entries_are_unpublished_catalog_series():
    from ai_tracker import catalog, licenses
    from ai_tracker.series import credit_issuance as series

    if not ci.PATH.exists():
        pytest.skip("no curated file")
    keys = {s.key for s in series.SPECS}
    assert {"spread_issue_ai_q", "spread_issue_ai_7_12y_q"} <= keys
    assert all(not s.publish and s.branch == "G5" and s.freq == "Q" for s in series.SPECS)
    assert set(series.KNOWN_GAPS) == keys
    assert {licenses.verdict(s, catalog.by_key()).klass for s in series.SPECS} == {licenses.JA}
