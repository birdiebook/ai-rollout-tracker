"""KL1 "Kreditlagret": synthetic tests of the extraction, the check, the derived measures, as_of and the reading.

No network and no real table: documents, component rows and worlds are built here.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from ai_tracker import catalog, kreditlagret_check as chk
from ai_tracker.followed import kreditlagret as F
from ai_tracker.series import kreditlagret as S
from ai_tracker.sources import kreditlagret as kl
from ai_tracker.state import measures as M

# ------------------------------------------------------------------ extraction: the debt table parser

DEBT_HTML = """<html><body><p>10. Debt</p>
<p>The total debt obligations are as follows (dollars in thousands):</p>
<table><tr><td></td><td>Maturities</td><td>Effective Interest Rates</td><td>September 30, 2025</td>
<td>December 31, 2024</td></tr>
<tr><td>DDTL 1.0 Facility</td><td>March 2028</td><td>15</td><td>%</td><td>$</td><td>1,667,500</td><td>$</td><td>2,012,500</td></tr>
<tr><td>2030 Senior Notes</td><td>June 2030</td><td>10</td><td>%</td><td>2,000,000</td><td>&#8212;</td></tr>
<tr><td>2024 Term Loan Facility</td><td>May 2025</td><td>12</td><td>%</td><td>&#8212;</td><td>1,000,000</td></tr>
<tr><td>OEM financing arrangements</td><td>1,185,709</td><td>1,000,000</td></tr>
<tr><td>Less: Unamortized discount and issuance costs</td><td>(100,000)</td><td>(90,000)</td></tr>
<tr><td>Total debt, net</td><td>4,753,209</td><td>3,922,500</td></tr>
</table><p>As of September 30, 2025, the future principal payments were as follows:</p></body></html>"""

DEBT_HTML_M = """<html><body><p>The total debt obligations are as follows (dollars in millions):</p>
<table><tr><td></td><td>Maturities</td><td>Effective Interest Rates</td><td>June 30, 2026</td><td>December 31, 2025</td></tr>
</table><p>Recourse debt:</p><table>
<tr><td>DDTL 2.0 Facility</td><td>Aug 2030</td><td>11 %</td><td>$3,190</td><td>$5,037</td></tr>
<tr><td>Total recourse debt, net</td><td>3,190</td><td>5,037</td></tr></table>
<p>Non-recourse debt:</p><table>
<tr><td>DDTL 4.0 Facility</td><td>Mar 2032</td><td>7 %</td><td>2,837</td><td>&#8212;</td></tr>
</table><p>(1) A footnote.</p></body></html>"""


def _doc(company="crwv", form="10-Q", filed="2025-11-13", acc="0000000000-25-000001", url="https://www.sec.gov/x.htm"):
    return kl.Doc(company, form, filed, f"{filed}T21:00:00.000Z", acc, url)


def test_debt_table_in_thousands():
    lines = kl.cc.lines(DEBT_HTML)
    rows = kl.debt_table(lines)
    by = {r.instrument: r for r in rows}
    assert set(by) == {"crwv_ddtl_1_0_facility", "crwv_2030_senior_notes", "crwv_2024_term_loan_facility",
                       "crwv_oem_financing_arrangements"}
    r = by["crwv_ddtl_1_0_facility"]
    assert (r.balance_date, r.outstanding, r.rate_pct, r.maturity) == ("2025-09-30", 1667.5, 15.0, "2028-03")
    assert by["crwv_2024_term_loan_facility"].outstanding == 0.0
    assert by["crwv_oem_financing_arrangements"].rate_pct is None


def test_debt_table_sections_and_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(kl, "QUOTES_DIR", tmp_path)
    lines = kl.cc.lines(DEBT_HTML_M)
    rows = kl.debt_table(lines)
    assert [r.instrument for r in rows] == ["crwv_ddtl_2_0_facility", "crwv_nonrecourse_ddtl_4_0_facility"]
    out = kl.table_rows(_doc(filed="2026-08-12"), lines)
    fields = {(r.instrument, r.field): r.value for r in out}
    assert fields[("crwv_ddtl_2_0_facility", "outstanding")] == "3190"
    assert fields[("crwv_ddtl_2_0_facility", "rate_pct")] == "11"
    assert fields[("crwv_nonrecourse_ddtl_4_0_facility", "maturity")] == "2032-03"
    assert all(r.period == "2026-06-30" and r.filed == "2026-08-12" for r in out)
    # zero outstanding adds nothing; the thousands table still reads as the stated cell
    out_k = kl.table_rows(_doc(), kl.cc.lines(DEBT_HTML))
    assert not any(r.instrument == "crwv_2024_term_loan_facility" for r in out_k)
    assert {r.value for r in out_k if r.field == "outstanding"} == {"1667.5", "2000", "1185.709"}
    assert (tmp_path / f"{out[0].id}.txt").exists()


# ------------------------------------------------------------------ the number test

@pytest.mark.parametrize("field,value,unit,quote,ok", [
    ("principal", "2000", "MUSD", "issued $2,000 million in aggregate principal amount", True),
    ("principal", "2587.5", "MUSD", "offering of $2,587,500,000 aggregate principal amount", True),
    ("commitment", "15000", "MUSD", "provide for a $15.0 billion senior secured", True),
    ("outstanding", "1139", "MUSD", "DDTL 1.0 Facility | Mar 2028 | 15 % | $1,139 | $1,553", True),
    ("outstanding", "1667.5", "MUSD", "DDTL 1.0 Facility | March 2028 | 15 % | $1,667,500 | $2,012,500", True),
    ("outstanding", "1553", "MUSD", "DDTL 1.0 Facility | Mar 2028 | 15 % | $1,1539 | $15530", False),
    ("principal", "2000", "MEUR", "€2,000 million in aggregate principal amount", True),
    ("outstanding", "0", "MUSD", "we had no borrowings drawn under the facility", True),
    ("outstanding", "0", "MUSD", "we had $5 million of borrowings", False),
    ("coupon_pct", "9.25", "%", "9.250% Senior Notes due 2030", True),
    ("coupon_pct", "9.25", "%", "9.2505% notes", False),
    ("rate_pct", "0", "%", "non-interest-bearing rollover notes", True),
    ("margin_bp", "400", "bp", "4.00% plus the daily compounded SOFR", True),
    ("margin_bp", "225", "bp", "an applicable margin of 2.25% per annum", True),
    ("maturity", "2031-09-04", "date", "will mature on September 4, 2031, subject to", True),
    ("maturity", "2031-09-04", "date", "will mature on September 14, 2031", False),
    ("issue_date", "2026-09", "date", "In September 2026, we entered into", True),
    ("maturity", "2028-03", "date", "DDTL 1.0 Facility | Mar 2028 | 15 %", True),
    ("secured", "secured", "code", "a $2.5 billion senior secured revolving credit facility", True),
    ("secured", "secured", "code", "general senior, unsecured obligations", False),
    ("secured", "unsecured", "code", "general senior, unsecured obligations", True),
    ("offering", "144A", "code", "pursuant to Rule 144A under the Securities Act", True),
    ("guarantor", "material subsidiaries", "code", "guaranteed by certain of our Material Subsidiaries", True),
])
def test_value_in_quote(field, value, unit, quote, ok):
    assert kl.value_in_quote(field, value, unit, quote) is ok


def test_check_value_and_validate():
    kl.check_value("due_2027", "28424", "MUSD")
    kl.check_value("maturity", "2034-03", "date")
    for bad in (("coupon", "9", "%"), ("coupon_pct", "9", "bp"), ("maturity", "March 2034", "date"),
                ("secured", "maybe", "code"), ("principal", "x", "MUSD")):
        with pytest.raises(ValueError):
            kl.check_value(*bad)
    good = {c: "" for c in kl.COLUMNS}
    good.update(id="a", company="crwv", instrument="i", field="coupon_pct", value="9.25", unit="%", filed="2025-05-28",
                locator="line #37", quote_sha256="0" * 64)
    assert kl.validate(pd.DataFrame([good])) == []
    bad = [dict(good, id="b", qualifier="roughly"), dict(good, id="c", locator="lines #5-#5"),
           dict(good, id="d", filed="2026-12-01"), dict(good, id="a")]
    errors = kl.validate(pd.DataFrame([good, *bad]))
    assert any("qualifier" in e for e in errors) and any("range" in e for e in errors)
    assert any("filed" in e for e in errors) and any("duplicate" in e for e in errors)


def test_manual_row_locator_range_and_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(kl, "QUOTES_DIR", tmp_path)
    lines = ["Credit Agreement", "In September 2026, we entered into an agreement to provide for a $15.0 billion senior",
             "secured revolving credit facility. The facility will mature on September 4, 2031."]
    d = _doc(form="S-1", filed="2026-10-26")
    r = kl.manual_row(d, lines, "lines #1-#2", "x_rcf", "commitment", "15000", "MUSD", "2026-09")
    assert r.quote_sha256 == kl.cc.block_hash(lines[1:3]) and r.id == "x_rcf-2026-09-commitment"
    assert (tmp_path / f"{r.id}.txt").read_text(encoding="utf-8") == "\n".join(lines[1:3])
    with pytest.raises(ValueError, match="not in the quote"):
        kl.manual_row(d, lines, "line #1", "x_rcf", "maturity", "2031-09-04", "date")
    with pytest.raises(ValueError, match="outside"):
        kl.manual_row(d, lines, "line #9", "x_rcf", "commitment", "15000", "MUSD")


def _hash_index_of(lines: dict[str, list[str]]):
    return lambda url, width: {kl.quote_hash("\n".join(lines[url][k:k + width])): k
                               for k in range(len(lines[url]) - width + 1)}


def test_earliest_moves_a_row_to_the_first_document_with_the_line(monkeypatch, tmp_path):
    monkeypatch.setattr(kl, "QUOTES_DIR", tmp_path)
    quote_lines = ["Purchase commitments | 313,819 | 5,053"]
    head = "The following table summarizes our contractual obligations as of September 30, 2026 :"
    final = _doc("anthropic", "424B4", "2026-11-19", "acc-3", "u3")
    r = kl.manual_row(final, [head, *quote_lines], "line #1", "a_pc", "due_total", "313819", "MUSD", "2026-09-30")
    docs = [_doc("anthropic", "S-1", "2026-10-26", "acc-1", "u1"), _doc("anthropic", "S-1/A", "2026-11-02", "acc-2", "u2"),
            final]
    lines = {"u1": ["Purchase commitments | 300,000 | 5,053"], "u2": ["a", head, *quote_lines], "u3": [head, *quote_lines]}
    monkeypatch.setattr(kl, "_hash_index", _hash_index_of(lines))
    (moved,) = kl.earliest([r], docs, lines_of=lines.__getitem__)
    assert (moved.filed, moved.form, moved.accession, moved.locator) == ("2026-11-02", "S-1/A", "acc-2", "line #2")
    assert moved.quote_sha256 == r.quote_sha256


def test_earliest_keeps_a_balance_where_the_earlier_document_states_another_date(monkeypatch, tmp_path):
    """R26-1: the S-1 has the same table line, but its table is as of June 30; the September balance is known from the
    first amendment that states September 30 (here in the note under the table)."""
    monkeypatch.setattr(kl, "QUOTES_DIR", tmp_path)
    row = "Amazon 2026 NPA | $15.0 billion | $15.0 billion (2) | $ — | N/A"
    june = ["The following table summarizes the principal terms as of June 30, 2026.", "Agreement | Original | Remaining (1)",
            row, "______________", "(1) A s of June 30, 2026."]
    sept = ["The following table summarizes the principal terms.", "Agreement | Original | Remaining (1)", row, "174",
            "Table of Contents", "______________", "(1) As of September 30, 2026."]
    final = _doc("anthropic", "424B4", "2026-11-19", "acc-3", "u3")
    r = kl.manual_row(final, sept, "line #2", "a_npa", "commitment", "15000", "MUSD", "2026-09-30")
    monthly = kl.manual_row(final, sept, "line #2", "a_npa", "commitment", "15000", "MUSD", "2026-04", rid="m")
    docs = [_doc("anthropic", "S-1", "2026-10-26", "acc-1", "u1"), _doc("anthropic", "S-1/A", "2026-11-02", "acc-2", "u2"),
            final]
    lines = {"u1": june, "u2": sept, "u3": sept}
    monkeypatch.setattr(kl, "_hash_index", _hash_index_of(lines))
    moved, month = kl.earliest([r, monthly], docs, lines_of=lines.__getitem__)
    assert (moved.filed, moved.accession) == ("2026-11-02", "acc-2")
    assert (month.filed, month.accession) == ("2026-10-26", "acc-1")  # a month period moves on the hash alone
    lines["u2"] = june  # no document before the source states September 30: the row stays in the source
    monkeypatch.setattr(kl, "_hash_index", _hash_index_of(lines))
    (kept,) = kl.earliest([r], docs, lines_of=lines.__getitem__)
    assert (kept.filed, kept.accession) == ("2026-11-19", "acc-3")


def test_stated_dates_quote_heading_notes_and_prose():
    lines = ["Notes outstanding as of June 30, 2026, which consist", "x", "A | B", "Amazon | 2,186", "Total | 2,186",
             "17", "Table of Contents", "(1) As of September 30, 2026.", "Other text as of March 31, 2026."]
    assert kl.stated_dates(lines, 3, 3) == {"2026-06-30", "2026-09-30"}  # heading and note, not the prose after
    assert kl.stated_dates(lines, 3, 3, width=1) == {"2026-09-30"}
    prose = ["The table below is as of September 30, 2026 :", "In aggregate, about $900.9 billion.", "end"]
    assert kl.stated_dates(prose, 1, 1) == {"2026-09-30"}
    assert kl.stated_dates(["As of December 31, 2025 and September 30, 2026 (unaudited), no amounts"], 0, 0) == {
        "2025-12-31", "2026-09-30"}


def test_uncoded_candidate_reasons():
    d = _doc("crwv", "10-Q", "2026-11-12", "acc-q")
    agent = {("acc-q", "line #5"): "egen bedömning"}
    assert kl.skip_reason("crwv", d, 5, "4.2 | Form of Note", agent, None) == ("egen bedömning", "agent")
    assert kl.skip_reason("crwv", d, 1, "4.2 | Form of 9.750% Senior Notes due 2031", {}, None) == (
        "bilageförteckning", "regel")
    assert kl.skip_reason("crwv", d, 12, "Total debt | 21,000", {}, (10, 20))[0] == kl.TABLE_REASON
    assert kl.skip_reason("crwv", d, 30, "the conversion rate will be 9.2764 shares", {}, (10, 20))[0].startswith("aktier")
    assert kl.skip_reason("crwv", d, 30, "We may redeem the Notes at 101%", {}, (10, 20))[0].startswith("villkor")
    assert kl.skip_reason("crwv", d, 30, "We had $17.6 billion outstanding under DDTL facilities", {}, None)[0] == \
        kl.PERIODIC_REASON
    sx = _doc("spacex", "10-Q", "2026-10-22", "acc-s")
    assert kl.skip_reason("spacex", sx, 3, "We had $17.6 billion outstanding under loans", {}, None) == (
        kl.NOT_ASSESSED, "ingen")


# ------------------------------------------------------------------ the self-check

def test_check_row_statuses():
    lines = ["header", "The Notes will mature on June 1, 2030 and bear interest at 9.250% per annum.", "other"]
    row = pd.Series({"locator": "line #1", "quote_sha256": kl.quote_hash(lines[1]), "field": "coupon_pct",
                     "value": "9.25", "unit": "%"})
    assert chk.check_row(row, lines) == "ok"
    assert chk.check_row(row, ["new first line", *lines]) == "moved"
    assert chk.check_row(row.copy().replace({"9.25": "9.5"}), lines) == "value_not_in_quote"
    assert chk.check_row(row, ["header", "changed text"]) == "quote_not_found"
    filings = {"acc": {"filed": "2025-05-28", "accepted": "2025-05-28T16:01:02.000Z"}}
    base = pd.Series({"accession": "acc", "filed": "2025-05-28", "accepted": "2025-05-28T16:01:02.000Z"})
    assert chk.check_dates(base, filings) == "ok"
    assert chk.check_dates(base.copy().replace({"2025-05-28": "2025-05-29"}), filings).startswith("filed_differs")
    assert chk.check_dates(base.copy().replace({"acc": "other"}), filings) == "accession_not_in_submissions"


# ------------------------------------------------------------------ derived measures

def _rows(series: str, values: dict[str, float], kf: dict[str, str] | str, source="release") -> pd.DataFrame:
    out = []
    for p, v in values.items():
        k = kf[p] if isinstance(kf, dict) else kf
        out.append({"series": series, "freq": "Q", "period": p, "value": float(v), "known_from": pd.Timestamp(k),
                    "source": source, "fetched_at": pd.Timestamp("2026-11-25")})
    return pd.DataFrame(out)


QS = [str(q) for q in pd.period_range("2024Q1", "2025Q4", freq="Q-DEC")]


def _kf(q: str, lag: int = 30) -> str:
    return str((pd.Period(q, freq="Q-DEC").end_time.normalize() + pd.Timedelta(days=lag)).date())


def test_effective_rate_formula():
    t = pd.concat([_rows("interest_exp_orcl", {q: 100 for q in QS}, {q: _kf(q) for q in QS}),
                   _rows("lt_debt_orcl", {q: 8000 + 1000 * i for i, q in enumerate(QS)}, {q: _kf(q) for q in QS})])
    d = S.derive(S.formula("rate_eff", "orcl"), t)
    assert list(d["period"]) == QS[4:]  # needs lt_debt four quarters before the window's end
    first = d.iloc[0]  # 2025Q1: 400 / (0.5 * lt_debt 2024Q1 + 0.5 * lt_debt 2025Q1)
    assert first.value == pytest.approx(100 * 400 / (0.5 * 8000 + 0.5 * 12000))
    assert first.known_from == pd.Timestamp(_kf("2025Q1"))


def test_dependence_ratios_and_capex_pace():
    kf = {q: _kf(q) for q in QS}
    t = pd.concat([_rows("capex_crwv", {q: 100 for q in QS}, kf), _rows("ocf_crwv", {q: 40 for q in QS}, kf),
                   _rows("debt_issued_crwv", {q: 80 for q in QS}, kf), _rows("debt_repaid_crwv", {q: 20 for q in QS}, kf),
                   _rows("lease_uncommenced_crwv", {q: 1000 for q in QS}, kf),
                   _rows("rpo_crwv", {q: 1000 + 100 * i for i, q in enumerate(QS)}, kf)])
    v = {m: S.derive(S.formula(m, "crwv"), t).set_index("period")["value"] for m in
         ("fcfgap", "netdebt", "leases", "capex4", "rpo_add4")}
    assert v["fcfgap"]["2024Q4"] == pytest.approx(60.0)  # (400 - 160) / 400
    assert v["netdebt"]["2025Q4"] == pytest.approx(60.0)  # (320 - 80) / 400
    assert v["leases"]["2025Q4"] == pytest.approx(250.0)  # 1000 / 400
    assert v["capex4"]["2025Q4"] == pytest.approx(400.0)
    assert v["rpo_add4"]["2025Q4"] == pytest.approx(400.0)  # four quarters of +100
    assert "2024Q3" not in v["fcfgap"].index  # a four-quarter sum needs all four quarters


def test_layer_version_only_when_every_member_has_filed_and_vintages():
    qs = QS[:4]
    t = pd.concat([_rows("capex_orcl", {q: 10 for q in qs}, {q: _kf(q, -10) for q in qs}),
                   _rows("capex_crwv", {q: 20 for q in qs}, {q: _kf(q, 45) for q in qs}),
                   _rows("capex_nbis", {q: 5 for q in qs}, {q: _kf(q, 40) for q in qs}),
                   _rows("capex_iren", {q: 1 for q in qs[1:]}, {q: _kf(q, 38) for q in qs[1:]})])
    f = S.formula("capex4", "outer")
    assert S.derive(f, t).empty  # IREN lacks 2024Q1: no four-quarter version for the layer
    t = pd.concat([t, _rows("capex_iren", {"2024Q1": 1}, {"2024Q1": "2024-05-10"})])
    d = S.derive(f, t)
    assert list(d["period"]) == ["2024Q4"] and d.iloc[0].value == pytest.approx(4 * 36)
    assert d.iloc[0].known_from == pd.Timestamp(_kf("2024Q4", 45))  # the latest member
    # a restatement of one member's quarter is a new version, dated by the restatement
    t = pd.concat([t, _rows("capex_crwv", {"2024Q2": 30}, {"2024Q2": "2025-03-01"})])
    d = S.derive(f, t)
    assert list(d["value"]) == pytest.approx([144.0, 154.0])
    assert d.iloc[1].known_from == pd.Timestamp("2025-03-01")


def test_derive_on_truncated_components_equals_truncated_derive():
    kf = {q: _kf(q, 30) for q in QS}
    t = pd.concat([_rows("capex_meta", {q: 100 + 10 * i for i, q in enumerate(QS)}, kf),
                   _rows("ocf_meta", {q: 150 for q in QS}, kf),
                   _rows("capex_meta", {"2024Q3": 125}, {"2024Q3": "2025-02-01"})])
    f = S.formula("fcfgap", "meta")
    full = S.derive(f, t)
    for d in ("2025-01-31", "2025-02-01", "2025-08-01"):
        trunc = S.derive(f, t[t["known_from"] <= pd.Timestamp(d)])
        want = full[full["known_from"] <= pd.Timestamp(d)].reset_index(drop=True)
        pd.testing.assert_frame_equal(trunc.reset_index(drop=True), want)


def test_coupon_series_from_curated_rows():
    def r(inst, field, value, unit, period, filed):
        return {"company": "crwv", "instrument": inst, "field": field, "value": value, "unit": unit, "period": period,
                "filed": filed, "qualifier": ""}
    df = pd.DataFrame([
        r("a", "outstanding", "1000", "MUSD", "2026-03-31", "2026-05-08"), r("a", "rate_pct", "10", "%", "2026-03-31", "2026-05-08"),
        r("b", "outstanding", "3000", "MUSD", "2026-03-31", "2026-05-08"), r("b", "rate_pct", "6", "%", "2026-03-31", "2026-05-08"),
        r("c", "outstanding", "1000", "MUSD", "2026-03-31", "2026-05-08"),  # no rate: coverage 80 %
        r("n1", "principal", "2000", "MUSD", "2025-05-27", "2025-05-28"), r("n1", "coupon_pct", "9.25", "%", "", "2025-05-28"),
        r("n1", "issue_date", "2025-05-27", "date", "", "2025-05-28"),
        r("n2", "principal", "1000", "MUSD", "2025-06-30", "2025-07-02"), r("n2", "coupon_pct", "10", "%", "", "2025-07-02"),
        r("n2", "issue_date", "2025-06-30", "date", "", "2025-07-02"),
        r("crwv_2031_convertible", "principal", "2500", "MUSD", "2025-06-01", "2025-06-02"),
        r("crwv_2031_convertible", "coupon_pct", "1.75", "%", "", "2025-06-02"),
        r("crwv_2031_convertible", "issue_date", "2025-06-01", "date", "", "2025-06-02"),
        r("eur", "principal", "2000", "MEUR", "2025-06-18", "2025-06-18"), r("eur", "coupon_pct", "8.5", "%", "", "2025-06-18"),
        r("eur", "issue_date", "2025-06-18", "date", "", "2025-06-18"),
    ])
    out = S.coupon_out(df, "crwv").iloc[0]
    assert (out.period, out.value, out.coverage) == ("2026Q1", pytest.approx(7.0), pytest.approx(0.8))
    assert out.known_from == pd.Timestamp("2026-05-08")
    new = S.coupon_new(df, "crwv")
    assert list(new["period"]) == ["2025Q2"]  # convertible and EUR excluded
    assert new.iloc[0].value == pytest.approx((2000 * 9.25 + 1000 * 10) / 3000)
    assert new.iloc[0].known_from == pd.Timestamp("2025-07-02")  # the quarter is over before the last filing


def test_coupon_out_leaves_out_totals_parts_and_on_request_convertibles():
    def r(inst, field, value, co="spacex"):
        return {"company": co, "instrument": inst, "field": field, "value": value, "unit": "%" if field == "rate_pct"
                else "MUSD", "period": "2026-09-30", "filed": "2026-10-22", "qualifier": ""}
    df = pd.DataFrame([r("spacex_total_debt", "outstanding", "38000"), r("spacex_notes", "outstanding", "25000"),
                       r("spacex_notes", "rate_pct", "6"), r("spacex_other", "outstanding", "13000"),
                       r("spacex_other", "rate_pct", "7"), r("spacex_valor_current", "outstanding", "2000"),
                       r("spacex_valor_noncurrent", "outstanding", "11000"),
                       r("crwv_2031_convertible_senior_notes", "outstanding", "1000", "crwv"),
                       r("crwv_2031_convertible_senior_notes", "rate_pct", "2", "crwv"),
                       r("crwv_ddtl", "outstanding", "3000", "crwv"), r("crwv_ddtl", "rate_pct", "10", "crwv")])
    sx = S.coupon_out(df, "spacex").iloc[0]
    assert sx.value == pytest.approx((25000 * 6 + 13000 * 7) / 38000) and sx.coverage == pytest.approx(1.0)
    assert S.coupon_out(df, "crwv").iloc[0].value == pytest.approx(8.0)
    assert S.coupon_out(df, "crwv", convertibles=False).iloc[0].value == pytest.approx(10.0)
    mix = F.convertible_mix(df, "2026Q3")
    assert mix["conv_share"] == pytest.approx(0.25) and mix["value_ex_conv"] == pytest.approx(10.0)
    assert (mix["conv_rate_lo"], mix["conv_rate_hi"]) == (2.0, 2.0) and mix["value_prev"] is None
    assert S.CONVERTIBLE.search("anthropic_google_2024_npa") and not S.CONVERTIBLE.search("crwv_2030_senior_notes")


def test_a_history_counts_quarters_with_a_pace():
    path = {"2025Q1": {"pace": None}, "2025Q2": {"pace": 6.0}, "2025Q3": {"pace": 1.0}, "2025Q4": {"pace": None}}
    ms = {f"kl_{m}_nbis": {"path": {}} for m in F.PRICE_DEP}
    ms["kl_fcfgap_nbis"] = {"path": path}
    assert F.a_history("nbis", ms) == {"held": 1, "of": 2, "first": "2025Q2", "last": "2025Q3"}


def test_lab_lines_qualify_and_name_spacex_only_with_its_rows():
    def row(co, inst, field, value, period="", filed="2026-11-02", qualifier=""):
        return {"id": f"{inst}-{field}-{period}", "company": co, "instrument": inst, "field": field, "value": value,
                "unit": "", "period": period, "filed": filed, "form": "", "qualifier": qualifier, "note": ""}
    rows = [row("anthropic", "anthropic_google_npa_2026", "commitment", "20000", "2026-09-30"),
            row("anthropic", "anthropic_google_npa_2026", "coupon_pct", "9.0"),
            row("anthropic", "anthropic_commit_spacexai", "commitment", "120500", "2026-05", qualifier="up_to"),
            row("crwv", "crwv_ddtl_2_0_facility", "margin_bp", "1300", filed="2025-10-02")]
    lab = "\n".join(F._lab_lines(rows))
    assert "kupong 9,00 % för lån före noteringen" in lab and "SpaceXAI (SpaceX) upp till 120,5 mdr (2026-05)" in lab
    assert "ddtl 2 0 facility 1 300 (före femte tillägget" in lab
    assert "**SpaceX**" not in lab and "xAI (" not in lab  # no SpaceX rows known: nothing about it
    rows += [row("spacex", "spacex_total_debt", "outstanding", "38006", "2026-09-30", "2026-10-22"),
             row("spacex", "spacex_notes", "outstanding", "25000", "2026-09-30", "2026-10-22"),
             row("spacex", "spacex_notes", "rate_pct", "6.072", "2026-09-30", "2026-10-22"),
             row("spacex", "spacex_notes", "coupon_pct", "5.855", "", "2026-08-04")]
    lab = "\n".join(F._lab_lines(rows))
    assert "**SpaceX** (äger xAI" in lab and "total skuld 38,0 mdr; SpaceX Notes 25,0 mdr (effektiv ränta 6,07 %" in lab


def test_catalog_specs_valid_publish_false_and_not_core():
    from ai_tracker.state import register as R

    specs = [s for s in catalog.ALL if s.key.startswith("kl_")]
    assert len(specs) >= 52
    assert catalog.validate(specs) == []
    assert not any(s.publish for s in specs)
    core = {k for keys in R.CORE_SERIES.values() for k in keys}
    assert not core & {s.key for s in specs}
    assert S.MEMBERS["capex4"]["outer"] == ("orcl", "crwv", "nbis", "iren")
    assert S.MEMBERS["leases"]["inner"] == ("googl", "amzn", "meta")


# ------------------------------------------------------------------ the registered reading

@pytest.mark.parametrize("a,d_out,d_in,want", [
    (True, -15.0, 9.0, "stoder"),
    (True, 3.0, 9.0, "emot_1"),
    (True, -4.9, -20.0, "emot_1"),  # held (above the limit): the inner's fall does not make it support
    (True, -20.0, -12.0, "emot_2"),
    (False, -20.0, -12.0, "emot_2"),  # equal fall points to demand, with or without A
    (True, -20.0, -6.0, "blandat"),
    (False, -15.0, 9.0, "inget"),
    (False, 10.0, 2.0, "inget"),
    (None, -15.0, 9.0, "kan_inte_avgoras"),
    (True, None, 9.0, "kan_inte_avgoras"),
    (True, -15.0, None, "kan_inte_avgoras"),
    (False, -15.0, None, "kan_inte_avgoras"),
])
def test_reading_truth_table(a, d_out, d_in, want):
    assert F.reading(a, d_out, d_in) == want


def _world(outer_capex: list[float], inner_capex: list[float], outer_fcfgap: list[float]) -> pd.DataFrame:
    """kl_ series for a synthetic world of 12 quarters (2023Q1-2025Q4), each known 40 days after its quarter."""
    qs = [str(q) for q in pd.period_range("2023Q1", "2025Q4", freq="Q-DEC")]
    kf = {q: _kf(q, 40) for q in qs}
    parts = [_rows("kl_capex4_outer", dict(zip(qs, outer_capex)), kf),
             _rows("kl_capex4_inner", dict(zip(qs, inner_capex)), kf),
             _rows("kl_fcfgap_outer", dict(zip(qs, outer_fcfgap)), kf)]
    for m in ("rate_eff", "netdebt", "leases"):
        parts.append(_rows(f"kl_{m}_outer", {q: 10.0 for q in qs}, kf))
    return pd.concat(parts, ignore_index=True)


def _read(table: pd.DataFrame, when: str) -> dict:
    ctx = M.Context(table=table)
    ms = {k: F.measure(k, when, ctx) for k in
          ("kl_capex4_outer", "kl_capex4_inner", *[f"kl_{m}_outer" for m in F.PRICE_DEP])}
    return F.apply_reading("outer", ms)


def _grow(rates: list[float], start: float = 100.0) -> list[float]:
    out = [start]
    for g in rates[1:]:
        out.append(out[-1] * np.exp(g / 100))
    return out


def test_world_supporting_the_mechanism():
    # outer: dependence rises, then quarterly growth slows from 15 % to 2 %; inner: steady 10 %
    outer = _grow([15] * 9 + [2, 2, 2])
    inner = _grow([10] * 12)
    fcfgap = [20, 20, 20, 20, 22, 25, 30, 35, 40, 45, 45, 45]
    r = _read(_world(outer, inner, fcfgap), "2026-03-01")
    assert r["t"] == "2025Q4" and r["a"] is True
    assert r["capex_change_outer"] < -5 < r["capex_change_inner"]
    assert r["outcome"] == "stoder"


def test_world_against_price_rose_but_pace_held():
    outer = _grow([5] * 8 + [8, 10, 12, 12])  # growth accelerates
    inner = _grow([10] * 12)
    fcfgap = [20, 20, 20, 20, 22, 25, 30, 35, 40, 45, 45, 45]
    r = _read(_world(outer, inner, fcfgap), "2026-03-01")
    assert r["a"] is True and r["outcome"] == "emot_1"


def test_world_against_equal_fall_in_both_layers():
    outer = _grow([15] * 9 + [2, 2, 2])
    inner = _grow([15] * 9 + [3, 3, 3])
    fcfgap = [20.0] * 12  # no rise in dependence
    r = _read(_world(outer, inner, fcfgap), "2026-03-01")
    assert r["a"] is False and r["outcome"] == "emot_2"


def test_world_neither_and_unknown():
    flat = _grow([10] * 12)
    r = _read(_world(flat, flat, [20.0] * 12), "2026-03-01")
    assert r["outcome"] == "inget"
    r = _read(_world(flat, flat, [20.0] * 12), "2024-03-01")  # too short: no change in pace yet
    assert r["outcome"] == "kan_inte_avgoras" and r["missing"]


# ------------------------------------------------------------------ the report and as_of truncation

def _report_world() -> pd.DataFrame:
    """Component series for every company over 2022Q1-2025Q4 and the derived kl_ series built from them."""
    qs = [str(q) for q in pd.period_range("2022Q1", "2025Q4", freq="Q-DEC")]
    rng = np.random.default_rng(7)
    parts = []
    for c in S.OUTER + S.INNER:
        lag = {"orcl": -15, "crwv": 45, "nbis": 45, "iren": 38}.get(c, 30)
        kf = {q: _kf(q, lag) for q in qs}
        capex = _grow(list(rng.normal(8, 3, len(qs))), 1000)
        parts += [_rows(f"capex_{c}", dict(zip(qs, capex)), kf),
                  _rows(f"ocf_{c}", {q: v * 0.8 for q, v in zip(qs, capex)}, kf)]
        if c in S.DEBT:
            parts += [_rows(f"interest_exp_{c}", {q: 50 + i for i, q in enumerate(qs)}, kf),
                      _rows(f"lt_debt_{c}", {q: 5000 + 100 * i for i, q in enumerate(qs)}, kf),
                      _rows(f"debt_issued_{c}", {q: 300 for q in qs}, kf), _rows(f"debt_repaid_{c}", {q: 100 for q in qs}, kf)]
        if c in S.LEASE:
            parts.append(_rows(f"lease_uncommenced_{c}", {q: 2000 + 50 * i for i, q in enumerate(qs)}, kf))
        if c in S.RPO:
            parts.append(_rows(f"rpo_{c}", {q: 10000 + 500 * i for i, q in enumerate(qs)}, kf))
    comp = pd.concat(parts, ignore_index=True)
    # a late restatement, so that truncation matters
    comp = pd.concat([comp, _rows("capex_orcl", {"2025Q2": 2500.0}, {"2025Q2": "2025-12-20"})], ignore_index=True)
    derived = []
    for s in catalog.ALL:
        if s.key.startswith("kl_") and not s.key.startswith("kl_coupon"):
            d = S.derive(S.formula(*s.key.removeprefix("kl_").rsplit("_", 1)) if s.key != "kl_leases_msft_cond"
                         else S.formula("leases", "msft_cond"), comp)
            if not d.empty:
                d = d.assign(series=s.key, freq="Q", fetched_at=pd.Timestamp("2026-11-25"))
                derived.append(d)
    return pd.concat([comp, *derived], ignore_index=True)


@pytest.fixture(scope="module")
def world() -> pd.DataFrame:
    return _report_world()


def _strip(r: dict) -> dict:
    r = json.loads(json.dumps(r, default=str))
    r.pop("generated", None)
    return r


def test_as_of_truncation_gives_the_same_report(world):
    empty_csv = pd.DataFrame(columns=kl.COLUMNS)
    for d in ("2025-06-30", "2025-12-19", "2025-12-20", "2026-03-15"):
        full = F.compute(d, table=world, csv=empty_csv)
        trunc = F.compute(d, table=world[world["known_from"] <= pd.Timestamp(d)], csv=empty_csv)
        assert _strip(full) == _strip(trunc), d
    # the restatement of 2025-12-20 changes the 2025Q2 Oracle level only from that day
    a = F.compute("2025-12-19", table=world, csv=empty_csv)["measures"]["kl_capex4_orcl"]["path"]["2025Q2"]["level"]
    b = F.compute("2025-12-20", table=world, csv=empty_csv)["measures"]["kl_capex4_orcl"]["path"]["2025Q2"]["level"]
    assert a != b


def test_report_renders_the_chain_and_uses_curated_rows_known_on_the_day(world):
    csv = pd.DataFrame([{**{c: "" for c in kl.COLUMNS}, "id": "x", "company": "anthropic",
                         "instrument": "anthropic_oblig_purchase_commitments", "field": "due_total", "value": "313819",
                         "unit": "MUSD", "period": "2026-09-30", "filed": "2026-10-26"}])
    early = F.compute("2026-03-15", table=world, csv=csv)
    assert early["extraction"]["n"] == 0
    text = F.render(F.compute("2026-11-25", table=world, csv=csv))
    assert text.index("## 1. Pris på skuld") < text.index("## 2. Beroende") < text.index("## 3. Vilja")
    assert "## 4. Läsregeln" in text and "## 6. Att bevaka" in text and "## 7. Förbehåll" in text
    assert "`kl_capex4_outer`" in text and "313,8 mdr" in text
    assert "Anthropic: ingen registreringsansökan" in F.render(early)


def test_next_filings_from_the_last_eight_filings(world):
    nf = {x["company"]: x for x in F.next_filings(world, "2026-01-10")}
    assert nf["orcl"]["next_period"] == "2026Q1" and nf["orcl"]["lag_days_median"] == -15
    assert nf["msft"]["estimated"] == "2026-01-30" and nf["msft"]["n"] == 8
    late = world[~((world["series"] == "capex_crwv") & (world["period"] == "2025Q4"))]  # the 10-K has not come
    overdue = {x["company"]: x for x in F.next_filings(late, "2026-02-20")}
    assert overdue["crwv"]["next_period"] == "2025Q4" and overdue["crwv"]["overdue"] is True
    assert overdue["crwv"]["then_period"] == "2026Q1" and overdue["msft"]["overdue"] is False
