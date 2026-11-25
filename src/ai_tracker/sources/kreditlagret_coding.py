"""The agent's coding of KL1 (register 2026-11-25 "KL1", "Kodningsregler för steg 2", and its addendum).

One entry per CSV row: document (accession), locator, instrument, field, value, unit, period, qualifier and a short note
without quotes. No document text is kept here: the build (sources/kreditlagret.build) reads the cached document, checks
that the value stands in the quote at the locator and writes the row with the quote's SHA-256 (the quote itself only
under data/raw). CoreWeave's debt tables are coded by the parser (kreditlagret.debt_table), not listed here.
Interpretations made while coding are listed in docs/kallor/kreditlagret.md ("Tolkningar under kodningen").
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Code:
    accession: str
    locator: str
    instrument: str
    field: str
    value: str
    unit: str
    period: str = ""
    qualifier: str = ""
    note: str = ""
    rid: str | None = None


ANT = "0001628280-26-074944"  # Anthropic 424B4, 2026-11-19 (known_from moves to the earliest document with the line)
M, PCT, BP, D, C = "MUSD", "%", "bp", "date", "code"


def _oblig(line: int, inst: str, values: tuple) -> list[Code]:
    cols = ("due_total", "due_2026", "due_2027", "due_2028", "due_2029", "due_2030", "due_thereafter")
    return [Code(ANT, f"line #{line}", inst, f, str(v), M, "2026-09-30", note="contractual obligations table, "
                 "payments due by year as of 2026-09-30", rid=f"{inst}-2026-09-30-{f}") for f, v in zip(cols, values)]


ANTHROPIC = [
    # Revolving credit agreement of May 2025 (Initial Credit Facility) and its two increases
    Code(ANT, "lines #7789-#7793", "anthropic_credit_facility_2025", "issue_date", "2025-05", D),
    Code(ANT, "lines #7789-#7793", "anthropic_credit_facility_2025", "commitment", "2500", M, "2025-05",
         note="initial revolving commitments"),
    Code(ANT, "lines #7789-#7793", "anthropic_credit_facility_2025", "secured", "secured", C),
    Code(ANT, "lines #7793-#7795", "anthropic_credit_facility_2025", "commitment", "2750", M, "2025-09",
         note="increase in September 2025"),
    Code(ANT, "lines #7793-#7795", "anthropic_credit_facility_2025", "commitment", "3250", M, "2025-11",
         note="increase in November 2025"),
    # A&R Credit Facility of September 2026
    Code(ANT, "lines #7796-#7798", "anthropic_ar_credit_facility", "issue_date", "2026-09", D),
    Code(ANT, "lines #7796-#7798", "anthropic_ar_credit_facility", "commitment", "15000", M, "2026-09"),
    Code(ANT, "lines #7796-#7798", "anthropic_ar_credit_facility", "secured", "secured", C),
    Code(ANT, "lines #7799-#7803", "anthropic_ar_credit_facility", "maturity", "2031-09-04", D,
         note="subject to a springing maturity"),
    Code(ANT, "lines #7806-#7807", "anthropic_ar_credit_facility", "outstanding", "0", M, "2026-09-30",
         note="no borrowings drawn"),
    Code(ANT, "lines #7806-#7807", "anthropic_ar_credit_facility_lc", "outstanding", "205", M, "2026-09-30",
         note="standby letters of credit"),
    Code(ANT, "lines #7812-#7815", "anthropic_ar_credit_facility", "guarantor", "material subsidiaries", C),
    Code(ANT, "lines #7812-#7815", "anthropic_ar_credit_facility", "collateral", "substantially all of our assets", C),
    # Notes outstanding under the NPAs on 2026-09-30 (non-interest-bearing rollover notes to Amazon)
    Code(ANT, "line #7900", "anthropic_amazon_2023_npa_notes", "outstanding", "2186", M, "2026-09-30"),
    Code(ANT, "line #7901", "anthropic_amazon_2024_npa_notes", "outstanding", "4017", M, "2026-09-30"),
    Code(ANT, "lines #7882-#7884", "anthropic_amazon_2023_npa_notes", "rate_pct", "0", PCT, "2026-09-30",
         note="non-interest-bearing rollover notes"),
    Code(ANT, "lines #7882-#7884", "anthropic_amazon_2024_npa_notes", "rate_pct", "0", PCT, "2026-09-30",
         note="non-interest-bearing rollover notes"),
    Code(ANT, "lines #16507-#16509", "anthropic_amazon_2023_npa_notes", "maturity", "2034-03", D,
         note="amended and restated rollover note"),
    # Infrastructure Partner 2026 NPA (Broadcom): notes only to finance rent under the 2026 Lease Arrangement
    Code(ANT, "line #7981", "anthropic_broadcom_npa_2026", "commitment", "42000", M, "2026-09-30",
         note="principal amount available for issuance; nothing outstanding"),
    Code(ANT, "line #7981", "anthropic_broadcom_npa_2026", "coupon_pct", "9.00", PCT, note="paid in kind"),
    Code(ANT, "lines #7987-#7989", "anthropic_broadcom_npa_2026_conditional", "coupon_pct", "13.00", PCT,
         note="notes issued while certain revenue performance conditions are not met"),
    Code(ANT, "lines #7999-#8000", "anthropic_broadcom_npa_2026", "secured", "secured", C, note="on a junior basis"),
    Code(ANT, "lines #7999-#8000", "anthropic_broadcom_npa_2026", "guarantor", "certain of our subsidiaries", C),
    Code(ANT, "lines #7999-#8000", "anthropic_broadcom_npa_2026", "collateral",
         "collateral securing the 2026 Lease Arrangement", C),
    Code(ANT, "lines #16535-#16537", "anthropic_broadcom_npa_2026", "issue_date", "2026-03", D,
         note="agreement entered (second note purchase agreement to finance rent)"),
    # 2025 note purchase agreement to finance rent (ends at the IPO)
    Code(ANT, "lines #16528-#16530", "anthropic_rent_npa_2025", "issue_date", "2025-08", D),
    Code(ANT, "lines #16528-#16530", "anthropic_rent_npa_2025", "commitment", "10000", M, "2025-08", "up_to"),
    Code(ANT, "lines #16532-#16533", "anthropic_rent_npa_2025", "outstanding", "0", M, "2026-09-30"),
    # Google and Amazon 2026 NPAs: capacity, nothing issued
    Code(ANT, "line #8021", "anthropic_google_npa_2026", "commitment", "20000", M, "2026-09-30",
         note="remaining amount available; the table states the interest rate as N/A (terms to be agreed after the IPO)"),
    Code(ANT, "lines #16410-#16412", "anthropic_google_npa_2026", "commitment", "30000", M, "2026-03", "up_to",
         note="original amount"),
    Code(ANT, "lines #16412-#16415", "anthropic_google_npa_2026", "coupon_pct", "9.0", PCT,
         note="notes to the financial statements; the MD&A table (line #8021) states N/A after the IPO"),
    Code(ANT, "line #7953", "anthropic_amazon_npa_2026", "commitment", "15000", M, "2026-09-30",
         note="remaining amount available; nothing outstanding"),
    Code(ANT, "lines #16516-#16518", "anthropic_amazon_npa_2026", "commitment", "20000", M, "2026-04", "up_to",
         note="original amount"),
    Code(ANT, "lines #16518-#16521", "anthropic_amazon_npa_2026", "coupon_pct", "8.0", PCT),
    # Historical convertible promissory notes (all converted or rolled over; issue month as stated)
    Code(ANT, "lines #16372-#16374", "anthropic_google_2023_npa", "commitment", "2000", M, "2023-09", "up_to"),
    Code(ANT, "lines #16374-#16377", "anthropic_google_2023_npa_t1", "principal", "500", M, "2023-09"),
    Code(ANT, "lines #16374-#16377", "anthropic_google_2023_npa_t1", "issue_date", "2023-09", D),
    Code(ANT, "lines #16374-#16377", "anthropic_google_2023_npa_t2", "principal", "750", M, "2024-09"),
    Code(ANT, "lines #16374-#16377", "anthropic_google_2023_npa_t2", "issue_date", "2024-09", D),
    Code(ANT, "lines #16374-#16377", "anthropic_google_2023_npa_t3", "principal", "750", M, "2025-09"),
    Code(ANT, "lines #16374-#16377", "anthropic_google_2023_npa_t3", "issue_date", "2025-09", D),
    Code(ANT, "lines #16378-#16379", "anthropic_google_2023_npa", "coupon_pct", "10.0", PCT,
         note="compounded annually, payable at maturity"),
    Code(ANT, "lines #16400-#16402", "anthropic_google_2024_npa", "principal", "1300", M, "2024-08", "approx"),
    Code(ANT, "lines #16400-#16402", "anthropic_google_2024_npa", "issue_date", "2024-08", D,
         note="agreement entered; the note's issue date is not stated separately"),
    Code(ANT, "lines #16402-#16403", "anthropic_google_2024_npa", "coupon_pct", "8.5", PCT),
    Code(ANT, "lines #16402-#16403", "anthropic_google_2024_npa", "maturity", "2030-08", D),
    Code(ANT, "lines #16422-#16424", "anthropic_amazon_2023_npa", "commitment", "4000", M, "2023-09", "up_to"),
    Code(ANT, "lines #16424-#16426", "anthropic_amazon_2023_npa_t1", "principal", "1200", M, "2023-09"),
    Code(ANT, "lines #16424-#16426", "anthropic_amazon_2023_npa_t1", "issue_date", "2023-09", D),
    Code(ANT, "lines #16424-#16426", "anthropic_amazon_2023_npa_t2", "principal", "3400", M, "2024-03",
         note="principal; proceeds were $2.8 billion (issuance premium)"),
    Code(ANT, "lines #16424-#16426", "anthropic_amazon_2023_npa_t2", "issue_date", "2024-03", D),
    Code(ANT, "lines #16433-#16435", "anthropic_amazon_2023_npa", "coupon_pct", "8.0", PCT,
         note="compounded annually, payable at maturity"),
    Code(ANT, "lines #16427-#16429", "anthropic_amazon_2024_npa", "commitment", "4000", M, "2024-11", "up_to"),
    Code(ANT, "lines #16429-#16432", "anthropic_amazon_2024_npa_t1", "principal", "1300", M, "2024-11"),
    Code(ANT, "lines #16429-#16432", "anthropic_amazon_2024_npa_t1", "issue_date", "2024-11", D),
    Code(ANT, "lines #16429-#16432", "anthropic_amazon_2024_npa_t2", "principal", "1300", M, "2025-05"),
    Code(ANT, "lines #16429-#16432", "anthropic_amazon_2024_npa_t2", "issue_date", "2025-05", D),
    Code(ANT, "lines #16429-#16432", "anthropic_amazon_2024_npa_t3", "principal", "1400", M, "2025-11"),
    Code(ANT, "lines #16429-#16432", "anthropic_amazon_2024_npa_t3", "issue_date", "2025-11", D),
    Code(ANT, "lines #16435-#16437", "anthropic_amazon_2024_npa_t1", "coupon_pct", "8.5", PCT),
    Code(ANT, "lines #16435-#16437", "anthropic_amazon_2024_npa_t1", "maturity", "2034-11", D),
    Code(ANT, "lines #16437-#16438", "anthropic_amazon_2024_npa_t2", "coupon_pct", "0", PCT,
         note="non-interest bearing"),
    Code(ANT, "lines #16437-#16438", "anthropic_amazon_2024_npa_t2", "maturity", "2035-05", D),
    Code(ANT, "lines #16437-#16438", "anthropic_amazon_2024_npa_t3", "coupon_pct", "0", PCT,
         note="non-interest bearing"),
    Code(ANT, "lines #16437-#16438", "anthropic_amazon_2024_npa_t3", "maturity", "2035-11", D),
    # Contractual obligations as of 2026-09-30 (MD&A table, in millions)
    *_oblig(8139, "anthropic_oblig_operating_leases", (4224, 57, 303, 462, 445, 466, 2491)),
    *_oblig(8140, "anthropic_oblig_finance_leases", (1950, 121, 438, 422, 406, 390, 173)),
    *_oblig(8141, "anthropic_oblig_purchase_commitments", (313819, 5053, 28424, 43473, 46901, 44214, 145754)),
    *_oblig(8142, "anthropic_oblig_total", (319993, 5231, 29165, 44357, 47752, 45070, 148418)),
    # Commitments outside the table (approximate as stated)
    Code(ANT, "lines #8118-#8120", "anthropic_oblig_aggregate", "due_total", "900900", M, "2026-09-30", "approx",
         note="table plus short-term and subsequent commitments and leases not yet commenced"),
    Code(ANT, "line #8122", "anthropic_unfixed_compute_estimate", "due_total", "150000", M, "2026-09-30", "approx",
         note="low end of the company's estimate for arrangements without a fixed dollar commitment",
         rid="anthropic_unfixed_compute_estimate-2026-09-30-due_total-lo"),
    Code(ANT, "line #8122", "anthropic_unfixed_compute_estimate", "due_total", "175000", M, "2026-09-30", "approx",
         note="high end of the same estimate", rid="anthropic_unfixed_compute_estimate-2026-09-30-due_total-hi"),
    Code(ANT, "lines #8166-#8168", "anthropic_short_term_commitments", "due_total", "17400", M, "2026-09-30",
         "approx", note="cancelable within one year or term of one year or less"),
    Code(ANT, "lines #8169-#8170", "anthropic_leases_not_commenced", "due_total", "451200", M, "2026-09-30", "approx",
         note="estimated future undiscounted lease obligations, executed and not yet commenced"),
    Code(ANT, "lines #8173-#8175", "anthropic_commitments_after_q3", "due_total", "105700", M, "2026-09-30",
         "approx", note="entered into after 2026-09-30, mostly data center leases and hosting"),
    Code(ANT, "lines #8189-#8191", "anthropic_commit_microsoft", "commitment", "47200", M, "2025-11", "at_least",
         note="November 2026 to June 2033; up to $49.2 billion"),
    Code(ANT, "lines #8194-#8195", "anthropic_commit_google", "commitment", "121300", M, "2026-03", "at_least",
         note="CSP hosting, April 2026 to July 2033 (approximately, as stated)"),
    Code(ANT, "lines #8208-#8209", "anthropic_commit_amazon", "commitment", "110000", M, "2026-04", "at_least",
         note="May 2026 to April 2036"),
]

CR = {  # CoreWeave 8-Ks
    "rcf": "0001769628-25-000003", "n2030": "0001769628-25-000025", "n2031": "0001193125-25-165924",
    "ddtl3": "0001769628-25-000033", "ddtl2": "0001193125-25-227562", "cv2031": "0001769628-25-000105",
    "ddtl4": "0001769628-26-000129", "n2031b": "0001769628-26-000164", "n2031c": "0001769628-26-000183",
    "ddtl5": "0001769628-26-000236", "n2032": "0001769628-26-000291", "ddtl55": "0001769628-26-000357",
    "cv2033": "0001769628-26-000432",
}


def _note(acc: str, line_issue: int, line_terms: int | None, inst: str, principal: str, coupon: str, issued: str,
          maturity: str | None, offering: bool, unit: str = M, unsecured_line: int | None = None,
          note: str = "") -> list[Code]:
    out = [Code(acc, f"line #{line_issue}", inst, "principal", principal, unit, issued, note=note),
           Code(acc, f"line #{line_issue}", inst, "coupon_pct", coupon, PCT),
           Code(acc, f"line #{line_issue}", inst, "issue_date", issued, D)]
    if maturity:
        out.append(Code(acc, f"line #{line_terms}", inst, "maturity", maturity, D))
    if offering:
        out.append(Code(acc, f"line #{line_issue}", inst, "offering", "144A", C))
    if unsecured_line is not None:
        out.append(Code(acc, f"line #{unsecured_line}", inst, "secured", "unsecured", C))
    return out


COREWEAVE = [
    Code(CR["rcf"], "line #37", "crwv_revolving_credit_facility", "commitment", "1500", M, "2025-05-02",
         note="Third Amendment raises the revolving facility from $650.0 million"),
    Code(CR["rcf"], "line #37", "crwv_revolving_credit_facility", "issue_date", "2025-05-02", D,
         note="date of the Third Amendment"),
    *_note(CR["n2030"], 37, 39, "crwv_2030_senior_notes", "2000", "9.250", "2025-05-27", "2030-06-01", False),
    *_note(CR["n2031"], 31, 33, "crwv_2031_9_00_senior_notes", "1750", "9.000", "2025-07-25", "2031-02-01", False),
    Code(CR["ddtl3"], "line #41", "crwv_ddtl_3_0_facility", "margin_bp", "400", BP,
         note="SOFR loans over daily compounded SOFR (0.00% floor)"),
    Code(CR["ddtl2"], "line #31", "crwv_ddtl_2_0_facility_incremental", "commitment", "3000", M, "2025-09-29",
         note="incremental tranche added by the Fifth Amendment"),
    Code(CR["ddtl2"], "line #31", "crwv_ddtl_2_0_facility_incremental", "issue_date", "2025-09-29", D),
    Code(CR["ddtl2"], "line #36", "crwv_ddtl_2_0_facility", "margin_bp", "1300", BP,
         note="before the Fifth Amendment, non-investment-grade loans over term SOFR (investment-grade 6.00-6.50%)"),
    *_note(CR["cv2031"], 38, None, "crwv_2031_convertible_senior_notes", "2587.5", "1.75", "2025-12-11", None, True,
           unsecured_line=39, note="convertible; includes the initial purchasers' option"),
    Code(CR["ddtl4"], "line #37", "crwv_ddtl_4_0_facility", "commitment", "8500", M, "2026-03-30"),
    Code(CR["ddtl4"], "line #37", "crwv_ddtl_4_0_facility", "issue_date", "2026-03-30", D),
    Code(CR["ddtl4"], "line #41", "crwv_ddtl_4_0_facility", "margin_bp", "225", BP,
         note="floating-rate SOFR loans over daily compounded SOFR; non-recourse"),
    *_note(CR["n2031b"], 38, 40, "crwv_2031_9_75_senior_notes", "1.75", "9.750", "2026-04-14", "2031-10-01", True,
           note="principal as stated ($1,750,000); the 10-Q for 2026-06-30 shows 2,750 MUSD for the series with the "
                "$1,000 million add-on, so the stated figure is very likely $1,750 million"),
    *_note(CR["n2031b"], 47, None, "crwv_2032_convertible_senior_notes", "4000", "1.75", "2026-04-14", None, True,
           unsecured_line=48, note="convertible; includes the initial purchasers' option"),
    *_note(CR["n2031c"], 38, 40, "crwv_2031_9_75_senior_notes_addon", "1000", "9.750", "2026-04-21", "2031-10-01",
           True, note="additional notes of the same series"),
    Code(CR["ddtl5"], "line #37", "crwv_ddtl_5_0_facility", "commitment", "3100", M, "2026-05-15"),
    Code(CR["ddtl5"], "line #37", "crwv_ddtl_5_0_facility", "issue_date", "2026-05-15", D),
    Code(CR["ddtl5"], "line #41", "crwv_ddtl_5_0_facility", "margin_bp", "450", BP,
         note="SOFR loans over daily compounded SOFR"),
    *_note(CR["n2032"], 38, 40, "crwv_2032_9_625_senior_notes", "1250", "9.625", "2026-06-18", "2032-07-15", True),
    *_note(CR["n2032"], 38, 40, "crwv_2032_eur_senior_notes", "2000", "8.500", "2026-06-18", "2032-07-15", True,
           unit="MEUR", note="euro-denominated; not converted"),
    Code(CR["ddtl55"], "line #37", "crwv_ddtl_5_5_facility", "commitment", "2600", M, "2026-08-07"),
    Code(CR["ddtl55"], "line #37", "crwv_ddtl_5_5_facility", "issue_date", "2026-08-07", D),
    Code(CR["ddtl55"], "line #41", "crwv_ddtl_5_5_facility", "margin_bp", "550", BP, note="SOFR loans over Term SOFR"),
    *_note(CR["cv2033"], 38, None, "crwv_2033_convertible_senior_notes", "4200", "2.875", "2026-09-22", None, True,
           unsecured_line=39, note="convertible; includes the initial purchasers' option"),
]

MQ3_25, MK25, MQ3_26 = "0001628280-25-047240", "0001628280-26-003942", "0001628280-26-066773"
META = [
    # Louisiana (Hyperion) venture, subsequent-event note of the 2025Q3 10-Q
    Code(MQ3_25, "line #602", "meta_louisiana_venture", "contribution", "4300", M, "2025-10",
         note="Meta's contribution at closing (held-for-sale assets, net)"),
    Code(MQ3_25, "line #602", "meta_louisiana_venture_investor", "contribution", "7000", M, "2025-10",
         note="the investor's cash contribution (80 % interest)"),
    Code(MQ3_25, "line #602", "meta_louisiana_venture", "distribution", "2600", M, "2025-10",
         note="one-time distribution to Meta"),
    Code(MQ3_25, "line #603", "meta_louisiana_venture", "lease_commitment", "12300", M, "2025-10", "approx",
         note="initial four-year lease term, commencing 2029"),
    Code(MQ3_25, "line #603", "meta_louisiana_venture", "rvg_max", "28000", M, "2025-10",
         note="residual value guarantee threshold, effectively begins at this amount and decreases"),
    # 10-K 2025: maximum exposure on 2025-12-31
    Code(MK25, "line #1528", "meta_louisiana_venture", "dev_cost", "27000", M, "2025-12-31", "approx",
         note="total estimated development costs, funded pro rata"),
    Code(MK25, "line #1532", "meta_dc_ventures", "exposure_max", "45950", M, "2025-12-31"),
    # 2026Q3 10-Q: two ventures, maximum exposure table on 2026-09-30
    Code(MQ3_26, "line #418", "meta_texas_venture", "contribution", "2260", M, "2026-07"),
    Code(MQ3_26, "line #418", "meta_texas_venture", "distribution", "1040", M, "2026-07"),
    Code(MQ3_26, "line #422", "meta_texas_venture", "dev_cost", "14000", M, "2026-09-30", "approx",
         note="total estimated development costs (approximately, as stated with the Louisiana figure)"),
    Code(MQ3_26, "line #427", "meta_dc_ventures", "equity_carrying", "4732", M, "2026-09-30"),
    Code(MQ3_26, "line #428", "meta_dc_ventures", "lease_commitment", "18476", M, "2026-09-30"),
    Code(MQ3_26, "line #429", "meta_dc_ventures", "funding_commitment", "3703", M, "2026-09-30"),
    Code(MQ3_26, "line #430", "meta_dc_ventures", "rvg_max", "41493", M, "2026-09-30"),
    Code(MQ3_26, "line #431", "meta_dc_ventures", "exposure_max", "68404", M, "2026-09-30"),
]

ALL = {"anthropic": ANTHROPIC, "crwv": COREWEAVE, "meta": META}
