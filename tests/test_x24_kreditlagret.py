"""X24: the fix of KL1 after review R27 (register "2026-11-25 – X24", docs/granskning/r27_kreditlagret.md). No network.

R27-1: SpaceX's 6.3 % was shown as the rate of all other financings, of which 99 % is Valor debt whose interest expense
in the same 10-Q is about 10.7 % a year. X24 codes Valor's quarterly interest expense (field interest_expense_q), shows
it next to the qualified 6.3 % and leaves spacex_other_financings' rate out of coupon_out. Only ids, numbers, dates,
accession numbers and hashes are kept here, never filing text.
"""

from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from ai_tracker import config
from ai_tracker.followed import kreditlagret as F
from ai_tracker.series import kreditlagret as S
from ai_tracker.sources import kreditlagret as kl

REGISTER = config.REPO / "docs" / "mattregister.md"
X24_HEADING = "### 2026-11-25 – X24: SpaceX ränta på övrig finansiering"
X24_ENTRY_SHA256 = "7048ced951eb2ab687fe4242296309c4c02436b05ba10cd3387e7091fb7d35c9"
VALOR_INTEREST = {  # id -> (value, accession, filed, locator), read in the cached 10-Qs (byte-identical to SEC, R27)
    "spacex_valor-2026-06-30-interest_expense_q": ("327", "0001628280-26-052535", "2026-08-04", "line #784"),
    "spacex_valor-2026-09-30-interest_expense_q": ("351", "0001628280-26-066880", "2026-10-22", "line #805"),
}


@pytest.fixture(scope="module")
def csv() -> pd.DataFrame:
    return kl.load()


def _section(text: str, start: str) -> str:
    a = text.index(start)
    b = text.find("\n### ", a + len(start))
    return (text[a:b] if b > 0 else text[a:]).strip()


def test_register_x24_entry_is_unchanged():
    entry = _section(REGISTER.read_text(encoding="utf-8"), X24_HEADING)
    assert hashlib.sha256(entry.encode("utf-8")).hexdigest() == X24_ENTRY_SHA256


def test_valor_interest_expense_rows(csv):
    d = csv[csv["field"] == "interest_expense_q"].set_index("id")
    assert set(d.index) == set(VALOR_INTEREST) and set(d["instrument"]) == {"spacex_valor"}
    for rid, (value, acc, filed, loc) in VALOR_INTEREST.items():
        r = d.loc[rid]
        assert (r["value"], r["unit"], r["accession"], r["filed"], r["form"], r["locator"]) == (value, "MUSD", acc,
                                                                                              filed, "10-Q", loc)
        # the same paragraph as the Valor balances on the same balance date
        bal = csv[(csv["instrument"] == "spacex_valor_current") & (csv["period"] == r["period"])].iloc[0]
        assert (bal["locator"], bal["quote_sha256"]) == (r["locator"], r["quote_sha256"])
    assert kl.FIELDS["interest_expense_q"] == "MUSD"


def test_report_line_shows_valor_interest_and_qualifies_the_rate(csv):
    lab = F._lab_lines(F.extraction("2026-11-25", csv)["rows"])
    rate_lines = [x for x in lab if "6,3 %" in x]
    assert len(rate_lines) == 1
    line = rate_lines[0]
    assert "räntekostnaden för Valor-avtalen var 351 MUSD under 2026Q3" in line
    mean = (2181 + 10716 + 2039 + 11290) / 2
    assert F._f(400 * 351 / mean, 1) == "10,7"
    assert "cirka 10,7 % per år av Valor-skulden i snitt (2026-06-30 och 2026-09-30)" in line
    assert "övriga finansieringsavtal" in line and "framgår inte" in line and "known_from 2026-10-22" in line
    debt = next(x for x in lab if x.startswith("  - total skuld"))
    assert "%)" not in debt.split("övrig finansiering")[1]  # no bare rate on the other-financings part


def test_report_before_the_q3_10q_shows_the_amount_without_an_annual_rate(csv):
    lab = "\n".join(F._lab_lines(F.extraction("2026-08-10", csv)["rows"]))
    assert "räntekostnaden för Valor-avtalen var 327 MUSD under 2026Q2" in lab and "5,9 %" in lab
    assert "per år av Valor-skulden" not in lab  # the Valor debt at 2026-03-31 is not coded


def test_lab_line_without_interest_says_so():
    def row(inst, field, value, period="2026-09-30"):
        return {"id": f"{inst}-{field}", "company": "spacex", "instrument": inst, "field": field, "value": value,
                "unit": "", "period": period, "filed": "2026-10-22", "form": "10-Q", "qualifier": "", "note": ""}
    rows = [row("spacex_total_debt", "outstanding", "38006"), row("spacex_other_financings", "outstanding", "12979"),
            row("spacex_other_financings", "rate_pct", "6.3")]
    line = next(x for x in F._lab_lines(rows) if "6,3 %" in x)
    assert "räntekostnaden för Valor-avtalen är inte kodad" in line and "framgår inte" in line


def test_coupon_out_leaves_out_the_rate_on_other_financings():
    def r(inst, field, value, period):
        return {"company": "spacex", "instrument": inst, "field": field, "value": value,
                "unit": "%" if field == "rate_pct" else "MUSD", "period": period, "filed": "2027-05-01",
                "qualifier": ""}
    days = ("2026-06-30", "2026-09-30", "2026-12-31", "2027-03-31")
    df = pd.DataFrame([x for d in days for x in (
        r("spacex_total_debt", "outstanding", "38000", d), r("spacex_notes", "outstanding", "25000", d),
        r("spacex_notes", "rate_pct", "6", d), r("spacex_other_financings", "outstanding", "13000", d),
        r("spacex_other_financings", "rate_pct", "6.3", d), r("spacex_valor_current", "outstanding", "2000", d),
        r("spacex_valor", "interest_expense_q", "351", d))])
    out = S.coupon_out(df, "spacex")
    assert len(out) == 4 >= S.MIN_QUARTERS  # four quarters would give a series: it weighs only the notes
    assert out["value"].tolist() == pytest.approx([6.0] * 4)
    assert out["coverage"].tolist() == pytest.approx([25000 / 38000] * 4)
    assert S.RATE_NOT_FOR_LINE.search("spacex_other_financings") and not S.RATE_NOT_FOR_LINE.search("crwv_ddtl")
    assert S.NOT_AN_INSTRUMENT.search("spacex_valor") and S.NOT_AN_INSTRUMENT.search("spacex_valor_noncurrent")


def test_real_coupon_out_is_unchanged_for_coreweave_and_spacex_stays_without_a_series(csv):
    assert len(S.coupon_out(csv, "spacex")) < S.MIN_QUARTERS
    co = S.coupon_out(csv, "crwv")
    no_rule = csv[~csv["instrument"].str.contains(S.RATE_NOT_FOR_LINE)]
    pd.testing.assert_frame_equal(co, S.coupon_out(no_rule, "crwv"))
