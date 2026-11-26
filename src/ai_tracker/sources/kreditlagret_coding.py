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
    # X23 (R26-4): the other named compute counterparties, coded as the three above
    Code(ANT, "lines #8213-#8216", "anthropic_commit_spacexai", "commitment", "120500", M, "2026-05", "up_to",
         note="SpaceXAI (SpaceX), terms into 2029; cancellable on 90 days' notice after initial periods ending Jan/Mar "
              "2027"),
    Code(ANT, "lines #8233-#8236", "anthropic_commit_nscale", "commitment", "44600", M, "2026-08", "up_to",
         note="up to approximately, terms into 2033; fees accrue as capacity is delivered"),
    Code(ANT, "lines #8243-#8245", "anthropic_commit_lambda", "commitment", "41300", M, "2026-05", "approx",
         note="terms into 2034; about 34.9 bn of it (the August 2026 agreement) is currently terminable"),
    Code(ANT, "lines #8175-#8177", "anthropic_short_term_commitments_after_q3", "due_total", "6600", M, "2026-09-30",
         "approx", note="short-term agreements entered into after 2026-09-30 (X23)"),
    Code(ANT, "lines #8206-#8207", "anthropic_google_tpu_estimate", "due_total", "125000", M, "", "approx",
         note="low end; TPU compute without a fixed dollar commitment, not in the table; may overlap the 150-175 bn estimate",
         rid="anthropic_google_tpu_estimate-due_total-lo"),
    Code(ANT, "lines #8206-#8207", "anthropic_google_tpu_estimate", "due_total", "150000", M, "", "approx",
         note="high end of the same estimate", rid="anthropic_google_tpu_estimate-due_total-hi"),
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
          note: str = "", principal_at: tuple[str, int] | None = None) -> list[Code]:
    pacc, pline = principal_at or (acc, line_issue)
    out = [Code(pacc, f"line #{pline}", inst, "principal", principal, unit, issued, note=note),
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
    Code(CR["ddtl3"], "line #37", "crwv_ddtl_3_0_facility", "commitment", "2600", M, "2025-07-28",
         note="delayed draw term loan facility (X23)"),
    Code(CR["ddtl3"], "line #37", "crwv_ddtl_3_0_facility", "issue_date", "2025-07-28", D,
         note="date of the credit agreement (X23)"),
    Code(CR["ddtl3"], "line #41", "crwv_ddtl_3_0_facility", "margin_bp", "400", BP,
         note="SOFR loans over daily compounded SOFR (0.00% floor)"),
    Code(CR["ddtl2"], "line #31", "crwv_ddtl_2_0_facility_incremental", "commitment", "3000", M, "2025-09-29",
         note="incremental tranche added by the Fifth Amendment"),
    Code(CR["ddtl2"], "line #31", "crwv_ddtl_2_0_facility_incremental", "issue_date", "2025-09-29", D),
    Code(CR["ddtl2"], "line #36", "crwv_ddtl_2_0_facility", "margin_bp", "1300", BP,
         note="before the Fifth Amendment, non-investment-grade loans over term SOFR (investment-grade 6.00-6.50%)"),
    Code(CR["ddtl2"], "line #36", "crwv_ddtl_2_0_facility_incremental", "margin_bp", "425", BP,
         note="Fifth Amendment tranche, term SOFR loans over three-month term SOFR (X23)"),
    *_note(CR["cv2031"], 38, None, "crwv_2031_convertible_senior_notes", "2587.5", "1.75", "2025-12-11", None, True,
           unsecured_line=39, note="convertible; includes the initial purchasers' option"),
    Code(CR["ddtl4"], "line #37", "crwv_ddtl_4_0_facility", "commitment", "8500", M, "2026-03-30"),
    Code(CR["ddtl4"], "line #37", "crwv_ddtl_4_0_facility", "issue_date", "2026-03-30", D),
    Code(CR["ddtl4"], "line #41", "crwv_ddtl_4_0_facility", "margin_bp", "225", BP,
         note="floating-rate SOFR loans over daily compounded SOFR; non-recourse"),
    *_note(CR["n2031b"], 38, 40, "crwv_2031_9_75_senior_notes", "1750", "9.750", "2026-04-14", "2031-10-01", True,
           principal_at=(CR["n2031c"], 38),
           note="principal from the 8-K of 2026-04-21 (the April 14 issue, $1,750,000,000); the 8-K of 2026-04-14 "
                "writes $1,750,000, a typo (R26-2)"),
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
MQ1_26, MQ2_26 = "0001628280-26-028526", "0001628280-26-050705"  # X23 (R26-4): the Louisiana venture alone
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
    Code(MK25, "line #1532", "meta_dc_ventures", "equity_carrying", "1830", M, "2025-12-31",
         note="carrying value of the equity investment (X23)"),
    # 2026Q1 and 2026Q2 10-Qs: the same maximum exposure, stated in a sentence (only the Louisiana venture existed)
    Code(MQ1_26, "line #405", "meta_dc_ventures", "exposure_max", "45990", M, "2026-03-31",
         note="Louisiana venture only; same reading as the 2026Q3 table (X23)"),
    Code(MQ1_26, "line #405", "meta_dc_ventures", "equity_carrying", "2370", M, "2026-03-31",
         note="Louisiana venture only (X23)"),
    Code(MQ2_26, "line #423", "meta_dc_ventures", "exposure_max", "46030", M, "2026-06-30",
         note="Louisiana venture only; same reading as the 2026Q3 table (X23)"),
    Code(MQ2_26, "line #423", "meta_dc_ventures", "equity_carrying", "2920", M, "2026-06-30",
         note="Louisiana venture only (X23)"),
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

SQ2, SQ3 = "0001628280-26-052535", "0001628280-26-066880"  # SpaceX 10-Q 2026-06-30 and 2026-09-30 (register X23)
SPACEX = [
    # balances on each 10-Q's own balance date (Note 9, table in millions)
    Code(SQ2, "line #466", "spacex_total_debt", "outstanding", "38433", M, "2026-06-30", note="total debt, principal"),
    Code(SQ2, "line #463", "spacex_notes", "outstanding", "25000", M, "2026-06-30", note="principal"),
    Code(SQ2, "line #464", "spacex_x_2027_2030_notes", "outstanding", "27", M, "2026-06-30",
         note="X 2027 and X 2030 notes together, principal"),
    Code(SQ2, "line #465", "spacex_other_financings", "outstanding", "13406", M, "2026-06-30",
         note="includes failed sale-leaseback obligations for infrastructure assets"),
    Code(SQ2, "line #490", "spacex_notes", "rate_pct", "6.030", PCT, "2026-06-30", note="effective interest rate"),
    Code(SQ2, "line #543", "spacex_other_financings", "rate_pct", "5.9", PCT, "2026-06-30",
         note="average fixed interest rate, as stated"),
    Code(SQ3, "line #471", "spacex_total_debt", "outstanding", "38006", M, "2026-09-30", note="total debt, principal"),
    Code(SQ3, "line #468", "spacex_notes", "outstanding", "25000", M, "2026-09-30", note="principal"),
    Code(SQ3, "line #469", "spacex_x_2027_2030_notes", "outstanding", "27", M, "2026-09-30",
         note="X 2027 and X 2030 notes together, principal"),
    Code(SQ3, "line #470", "spacex_other_financings", "outstanding", "12979", M, "2026-09-30",
         note="includes failed sale-leaseback obligations for infrastructure assets"),
    Code(SQ3, "line #497", "spacex_notes", "rate_pct", "6.072", PCT, "2026-09-30", note="effective interest rate"),
    Code(SQ3, "line #548", "spacex_other_financings", "rate_pct", "6.3", PCT, "2026-09-30",
         note="weighted-average fixed interest rate, as stated"),
    Code(SQ3, "line #544", "spacex_xai_revolving_line", "outstanding", "0", M, "2026-09-30",
         note="no borrowings in the period"),
    # related-party financing of AI infrastructure hardware (Valor), part of other financings (current, non-current)
    Code(SQ2, "line #784", "spacex_valor_current", "outstanding", "2039", M, "2026-06-30",
         note="failed sale-leaseback of AI infrastructure hardware with Valor (related party), current; in other financings"),
    Code(SQ2, "line #784", "spacex_valor_noncurrent", "outstanding", "11290", M, "2026-06-30",
         note="the same, non-current"),
    Code(SQ3, "line #805", "spacex_valor_current", "outstanding", "2181", M, "2026-09-30",
         note="failed sale-leaseback of AI infrastructure hardware with Valor (related party), current; in other financings"),
    Code(SQ3, "line #805", "spacex_valor_noncurrent", "outstanding", "10716", M, "2026-09-30",
         note="the same, non-current"),
    # interest expense on the Valor agreements for the quarter of each 10-Q (register X24, point 1; R27-1)
    Code(SQ2, "line #784", "spacex_valor", "interest_expense_q", "327", M, "2026-06-30",
         note="interest expense on the equipment lease agreements with Valor, three months to the period"),
    Code(SQ3, "line #805", "spacex_valor", "interest_expense_q", "351", M, "2026-09-30",
         note="interest expense on the equipment lease agreements with Valor, three months to the period"),
    # terms, from the first 10-Q that states them
    Code(SQ2, "line #488", "spacex_notes", "principal", "25000", M, "2026-06", note="five tranches, 2031 to 2056"),
    Code(SQ2, "line #488", "spacex_notes", "issue_date", "2026-06", D),
    Code(SQ2, "line #488", "spacex_notes", "secured", "unsecured", C),
    Code(SQ2, "line #490", "spacex_notes", "coupon_pct", "5.855", PCT,
         note="weighted-average coupon of the five tranches (5.350 to 6.650 %)"),
    Code(SQ2, "line #498", "spacex_bridge_loan", "commitment", "20000", M, "2026-03",
         note="bridge term loan, repaid in June 2026 from the notes"),
    Code(SQ2, "line #498", "spacex_bridge_loan", "issue_date", "2026-03", D),
    Code(SQ2, "line #498", "spacex_bridge_loan", "secured", "unsecured", C),
    Code(SQ2, "line #505", "spacex_credit_facility", "commitment", "1500", M, "2025-02", "up_to",
         note="five-year revolving credit agreement"),
    Code(SQ2, "line #505", "spacex_credit_facility", "issue_date", "2025-02", D),
    Code(SQ2, "line #505", "spacex_credit_facility", "secured", "unsecured", C),
    Code(SQ2, "line #506", "spacex_credit_facility", "commitment", "5000", M, "2026-05", "up_to",
         note="amended in May 2026"),
    Code(SQ2, "lines #506-#509", "spacex_credit_facility", "maturity", "2031-05-19", D, note="after the May 2026 amendment"),
    Code(SQ2, "line #537", "spacex_xai_revolving_line", "commitment", "250", M, "2024-04", "up_to",
         note="xAI subsidiary, against pledged securities; amended through March 2026"),
    Code(SQ2, "line #537", "spacex_xai_revolving_line", "outstanding", "0", M, "2026-06-30",
         note="no borrowings in the period"),
    # xAI's own debt before the merger (repaid in March 2026, not in the table on 2026-06-30)
    Code(SQ2, "line #527", "spacex_xai_fixed_term_loan", "principal", "1000", M, "2025-06", note="xAI, repaid 2026-03"),
    Code(SQ2, "line #527", "spacex_xai_fixed_term_loan", "issue_date", "2025-06", D),
    Code(SQ2, "line #527", "spacex_xai_fixed_term_loan", "maturity", "2030-06-30", D),
    Code(SQ2, "line #528", "spacex_xai_fixed_term_loan", "coupon_pct", "12.50", PCT),
    Code(SQ2, "line #527", "spacex_xai_floating_term_loan", "principal", "1000", M, "2025-06", note="xAI, repaid 2026-03"),
    Code(SQ2, "line #527", "spacex_xai_floating_term_loan", "issue_date", "2025-06", D),
    Code(SQ2, "line #527", "spacex_xai_floating_term_loan", "maturity", "2030-06-30", D),
    Code(SQ2, "line #528", "spacex_xai_floating_term_loan", "margin_bp", "725", BP, note="over Term SOFR (or ABR + 6.25 %)"),
    Code(SQ2, "line #532", "spacex_xai_secured_notes", "principal", "3000", M, "2025-06", note="xAI, repaid 2026-03"),
    Code(SQ2, "line #532", "spacex_xai_secured_notes", "issue_date", "2025-06", D),
    Code(SQ2, "line #532", "spacex_xai_secured_notes", "maturity", "2030-06-30", D),
    Code(SQ2, "line #532", "spacex_xai_secured_notes", "coupon_pct", "12.5", PCT),
    Code(SQ2, "line #532", "spacex_xai_secured_notes", "secured", "secured", C),
]

ALL = {"anthropic": ANTHROPIC, "crwv": COREWEAVE, "meta": META, "spacex": SPACEX}

# The agent's reasons for uncoded candidate lines (register X23, point 2), by (accession, locator). Lines without an
# entry get a rule category (sources/kreditlagret.SKIP_RULES).
MQ2_25 = "0001628280-25-036791"
SKIP: dict[tuple[str, str], str] = {
    ("0001193125-26-101045", "line #270"): ("Oracles egna placeringar i onoterade skuldebrev och aktier: inte bolagets "
        "finansiering"),
    ("0001193125-26-277521", "line #1432"): ("Oracles egna placeringar i onoterade skuldebrev och aktier: inte bolagets "
        "finansiering"),
    ("0001193125-26-389274", "line #268"): ("Oracles egna placeringar i onoterade skuldebrev och aktier: inte bolagets "
        "finansiering"),
    (MK25, "line #1529"): "leasingåtagandet vid bildandet (cirka 12,31 mdr): samma som kodas ur 10-Q 2025Q3 (rad #603)",
    (MQ1_26, "line #402"): "beskrivning av Louisiana-bolaget (20 % andel): inget nytt belopp utöver de som kodas",
    (MQ1_26, "line #403"): "leasingåtagandet (cirka 12,31 mdr): samma som kodas ur 10-Q 2025Q3 (rad #603)",
    (MQ2_26, "line #417"): "beskrivning av Louisiana-bolaget (20 % andel): inget nytt belopp utöver de som kodas",
    (MQ2_26, "line #418"): "leasingåtagandet (cirka 12,31 mdr): samma som kodas ur 10-Q 2025Q3 (rad #603)",
    (MQ3_26, "line #419"): "beskrivning av de två bolagen: inget nytt belopp; tabellen (rad #427-#431) kodas",
    (SQ2, "line #1224"): "MD&A: samma tal som kodas ur noten (Note 9)",
    (SQ3, "line #1316"): "MD&A: samma tal som kodas ur noten (Note 9)",
    (SQ2, "line #1229"): "MD&A: samma tal som kodas ur noten (Note 9)",
    (SQ3, "line #1324"): "MD&A: samma tal som kodas ur noten (Note 9)",
    (SQ2, "line #1230"): "marginal i ett spann efter kreditbetyg: inte ett enskilt värde",
    (SQ3, "line #1325"): "marginal i ett spann efter kreditbetyg: inte ett enskilt värde",
    (SQ3, "line #509"): "upprepning i 10-Q för 2026-09-30: villkoren kodas ur den första 10-Q:n (2026-08-04)",
    (SQ3, "line #513"): "upprepning i 10-Q för 2026-09-30: villkoren kodas ur den första 10-Q:n (2026-08-04)",
    (SQ2, "line #1216"): "kassaflöde eller likviditet: inte skuld",
    (SQ2, "line #544"): "samma skuld för misslyckade sale-leaseback som kodas ur noten om närstående (rad #784)",
    (SQ3, "line #549"): "samma skuld för misslyckade sale-leaseback som kodas ur noten om närstående (rad #805)",
    (SQ2, "line #416"): ("spektrumaffären med EchoStar: betalningar till en trust som redovisas som förskott, inte "
        "bolagets upplåning"),
    (SQ3, "line #417"): ("spektrumaffären med EchoStar: betalningar till en trust som redovisas som förskott, inte "
        "bolagets upplåning"),
    (SQ2, "line #1241"): ("spektrumaffären: lån till en trust som ska efterges, redovisas som köpeskilling, inte "
        "bolagets upplåning"),
    (SQ3, "line #1337"): ("spektrumaffären: lån till en trust som ska efterges, redovisas som köpeskilling, inte "
        "bolagets upplåning"),
    (SQ2, "line #520"): ("X Corp:s lån från köpet av Twitter (2022 och 2025), återbetalda 2026-03-02: labbdelen kodar "
        "xAI:s och SpaceX:s egen finansiering"),
    (SQ3, "line #527"): ("X Corp:s lån från köpet av Twitter (2022 och 2025), återbetalda 2026-03-02: labbdelen kodar "
        "xAI:s och SpaceX:s egen finansiering"),
    (SQ2, "line #524"): ("X Corp:s lån från köpet av Twitter (2022 och 2025), återbetalda 2026-03-02: labbdelen kodar "
        "xAI:s och SpaceX:s egen finansiering"),
    (SQ2, "line #761"): "remburser säkrade med spärrade medel: inte upplåning",
    (SQ3, "line #781"): "remburser säkrade med spärrade medel: inte upplåning",
    (ANT, "line #336"): ("sammanfattning: del av de 900,9 mdr som väntas före 2031 (451,6 mdr); inte ett fält, totalen "
        "kodas ur MD&A"),
    (ANT, "line #869"): ("konvertering av 612,7 MUSD i lån till aktier vid noteringen (kapitaliseringen): inte skuld "
        "efter noteringen"),
    (ANT, "line #1581"): "sammanfattning: samma åtaganden som kodas ur MD&A (rad #8118-#8122)",
    (ANT, "line #2809"): "riskfaktor: samma ram på 42,0 mdr som kodas ur tabellen (rad #7981)",
    (ANT, "line #2817"): "andel av kapitaliseringen efter noteringen: inte ett belopp för skuld",
    (ANT, "line #6218"): "kapitaliseringstabell: konvertibla lån i verkligt värde, inte nominellt belopp",
    (ANT, "line #6552"): "kostnad för beräkningskraft i resultatanalysen: inte ett instrument",
    (ANT, "line #6589"): "kostnad för beräkningskraft i resultatanalysen: inte ett instrument",
    (ANT, "line #7164"): "kostnad för beräkningskraft i resultatanalysen: inte ett instrument",
    (ANT, "line #7174"): "kostnad för beräkningskraft i resultatanalysen: inte ett instrument",
    (ANT, "line #7271"): "kostnad för beräkningskraft i resultatanalysen: inte ett instrument",
    (ANT, "line #7375"): "kostnad för beräkningskraft i resultatanalysen: inte ett instrument",
    (ANT, "line #7412"): "kostnad för lokaler: inte ett instrument",
    (ANT, "line #7601"): "kostnad för beräkningskraft i resultatanalysen: inte ett instrument",
    (ANT, "line #7636"): "kostnad för beräkningskraft i resultatanalysen: inte ett instrument",
    (ANT, "line #7710"): ("likviditet: 14,8 mdr tillgängligt under kreditfaciliteten; ramen och utnyttjandet kodas (rad "
        "#7796-#7807)"),
    (ANT, "line #7869"): ("beskrivning av Amazons konvertibla lån (6,2 mdr kvar): samma belopp som kodas ur tabellen "
        "(rad #7900-#7901)"),
    (ANT, "line #7961"): "villkor för dragningar (steg om 1,0 mdr): inte ett fält i kodningsreglerna",
    (ANT, "line #8155"): ("not till förpliktelsetabellen: Amazons lån (6,2 mdr) undantas, samma belopp som kodas ur rad "
        "#7900-#7901"),
    (ANT, "line #8156"): ("möjliga nya konvertibla lån, 77,0 mdr = ramarna 42,0, 20,0 och 15,0 mdr, som kodas var för "
        "sig"),
    (ANT, "line #8180"): ("andel som förfaller inom 12 månader: inte ett fält (förfall per år kodas ur tabellen, rad "
        "#8139-#8142)"),
    (ANT, "line #8590"): "sammanfattning: samma uppdelning som rad #336",
    (ANT, "line #8686"): "risktext om placeringar (36,3 mdr): inte skuld",
    (ANT, "line #8809"): "marknadsbeskrivning: inte bolagets belopp",
    (ANT, "line #10761"): "LTBT (stiftelse) som konsoliderad VIE: inte finansiering",
    (ANT, "line #12476"): "LTBT (stiftelse) som konsoliderad VIE: inte finansiering",
    (ANT, "line #13083"): "registreringsrätt för aktier vid konvertering: inte ett fält",
    (ANT, "line #15925"): ("tabell över verkligt värde per nivå: konvertibla lån i verkligt värde, inte nominellt belopp"),
    (ANT, "line #16387"): ("historik: tredje tranchen till Google 2023 vid en tidigare balansdag; tranchens belopp kodas "
        "(rad #16374-#16377)"),
    (ANT, "line #16418"): "inget utgivet under Google 2026 NPA per 2026-09-30: samma läge som tabellen (rad #8021)",
    (ANT, "line #16479"): ("historik över Amazons rollover-lån vid tidigare balansdagar; utestående per 2026-09-30 kodas "
        "ur tabellen (rad #7900-#7901)"),
    (ANT, "line #16492"): ("historik över Amazons rollover-lån vid tidigare balansdagar; utestående per 2026-09-30 kodas "
        "ur tabellen (rad #7900-#7901)"),
    (ANT, "line #16495"): ("historik över Amazons rollover-lån vid tidigare balansdagar; utestående per 2026-09-30 kodas "
        "ur tabellen (rad #7900-#7901)"),
    (ANT, "line #16513"): ("historik över Amazons rollover-lån vid tidigare balansdagar; utestående per 2026-09-30 kodas "
        "ur tabellen (rad #7900-#7901)"),
    (ANT, "line #16524"): "inget utgivet under Amazon 2026 NPA per 2026-09-30: samma läge som tabellen (rad #7953)",
    (ANT, "line #16538"): "kupongen 9,0 % (PIK) för Broadcom-ramen: samma som kodas ur tabellen (rad #7981)",
    (ANT, "line #16596"): "kreditfaciliteten i noterna (avrundade belopp); ramarna kodas ur MD&A (rad #7789-#7798)",
    (ANT, "line #16619"): "kreditfaciliteten i noterna (avrundade belopp); ramarna kodas ur MD&A (rad #7789-#7798)",
    (ANT, "line #16621"): "kreditfaciliteten i noterna (avrundade belopp); ramarna kodas ur MD&A (rad #7789-#7798)",
    (ANT, "line #16622"): "kreditfaciliteten i noterna (avrundade belopp); ramarna kodas ur MD&A (rad #7789-#7798)",
    (ANT, "line #16626"): "kreditfaciliteten i noterna (avrundade belopp); ramarna kodas ur MD&A (rad #7789-#7798)",
    (ANT, "line #16628"): "kreditfaciliteten i noterna (avrundade belopp); ramarna kodas ur MD&A (rad #7789-#7798)",
    (ANT, "line #16632"): ("utnyttjande per 2025-12-31 (tidigare balansdag); läget per 2026-09-30 kodas (rad "
        "#7806-#7807)"),
    (ANT, "line #16637"): ("utnyttjande och remburser per 2026-09-30 i noterna: samma belopp som kodas ur MD&A (rad "
        "#7806-#7807)"),
    (ANT, "line #16732"): "emission av preferensaktier: inte skuld",
    (ANT, "line #17307"): "tabell per 2025-12-31 i noterna (tidigare balansdag); läget per 2026-09-30 kodas ur MD&A",
    (ANT, "line #17552"): "noter: samma ram på 42,0 mdr som kodas ur tabellen (rad #7981)",
    (MQ2_25, "line #418"): ("andra okonsoliderade VIE före datacenterbolagen: förlusten är investeringarnas bokförda "
        "värde"),
    (MQ3_25, "line #415"): ("andra okonsoliderade VIE före datacenterbolagen: förlusten är investeringarnas bokförda "
        "värde"),
    (MQ3_26, "line #454"): "tillgångar som fördes till Texas-bolaget (2,26 mdr): samma belopp som kodas ur rad #418",
    (SQ2, "line #390"): "aktiverad ränta: inte ett instrument",
    (SQ2, "line #473"): "jämförelsekolumn per 2025-12-31, före den första 10-Q:n i korpusen",
    (SQ2, "line #478"): "jämförelsekolumn per 2025-12-31, före den första 10-Q:n i korpusen",
    (SQ2, "line #499"): "användning av lånet (återbetalning av xAI:s och X:s lån): inte ett fält i kodningsreglerna",
    (SQ2, "line #500"): "marginal i ett spann efter kreditbetyg: inte ett enskilt värde",
    (SQ2, "line #510"): "marginal i ett spann efter kreditbetyg: inte ett enskilt värde",
    (SQ2, "line #513"): ("X:s obligationer från 2019 och 2022: kvar 27 MUSD i en rad i tabellen (kodad), så ränta och "
        "belopp per serie vägs inte"),
    (SQ2, "line #514"): ("X:s obligationer från 2019 och 2022: kvar 27 MUSD i en rad i tabellen (kodad), så ränta och "
        "belopp per serie vägs inte"),
    (SQ2, "line #518"): ("X Corp:s lån från köpet av Twitter (2022 och 2025), återbetalda 2026-03-02: labbdelen kodar "
        "xAI:s och SpaceX:s egen finansiering"),
    (SQ2, "line #519"): ("X Corp:s lån från köpet av Twitter (2022 och 2025), återbetalda 2026-03-02: labbdelen kodar "
        "xAI:s och SpaceX:s egen finansiering"),
    (SQ2, "line #531"): "rubrik",
    (SQ2, "line #533"): "samma kupong som kodas ur rad #532",
    (SQ2, "line #557"): "tabell över bokfört och verkligt värde: inte nominellt belopp",
    (SQ2, "line #558"): "tabell över bokfört och verkligt värde: inte nominellt belopp",
    (SQ2, "line #559"): "tabell över bokfört och verkligt värde: inte nominellt belopp",
    (SQ2, "line #560"): "tabell över bokfört och verkligt värde: inte nominellt belopp",
    (SQ2, "line #1222"): "MD&A: samma tal som kodas ur noten (Note 9)",
    (SQ2, "line #1225"): "MD&A: samma tal som kodas ur noten (Note 9)",
    (SQ2, "line #1234"): "MD&A: samma tal som kodas ur noten (Note 9)",
    (SQ2, "line #1256"): "kassaflöde eller likviditet: inte skuld",
    (SQ2, "line #1265"): "MD&A: samma tal som kodas ur noten (Note 9)",
    (SQ3, "line #391"): "aktiverad ränta: inte ett instrument",
    (SQ3, "line #478"): "jämförelsekolumn per 2025-12-31, före den första 10-Q:n i korpusen",
    (SQ3, "line #483"): "jämförelsekolumn per 2025-12-31, före den första 10-Q:n i korpusen",
    (SQ3, "line #493"): "upprepning i 10-Q för 2026-09-30: villkoren kodas ur den första 10-Q:n (2026-08-04)",
    (SQ3, "line #502"): "upprepning i 10-Q för 2026-09-30: villkoren kodas ur den första 10-Q:n (2026-08-04)",
    (SQ3, "line #503"): "användning av lånet (återbetalning av xAI:s och X:s lån): inte ett fält i kodningsreglerna",
    (SQ3, "line #504"): "marginal i ett spann efter kreditbetyg: inte ett enskilt värde",
    (SQ3, "line #514"): "marginal i ett spann efter kreditbetyg: inte ett enskilt värde",
    (SQ3, "line #517"): ("X:s obligationer från 2019 och 2022: kvar 27 MUSD i en rad i tabellen (kodad), så ränta och "
        "belopp per serie vägs inte"),
    (SQ3, "line #518"): ("X:s obligationer från 2019 och 2022: kvar 27 MUSD i en rad i tabellen (kodad), så ränta och "
        "belopp per serie vägs inte"),
    (SQ3, "line #522"): ("X Corp:s lån från köpet av Twitter (2022 och 2025), återbetalda 2026-03-02: labbdelen kodar "
        "xAI:s och SpaceX:s egen finansiering"),
    (SQ3, "line #523"): ("X Corp:s lån från köpet av Twitter (2022 och 2025), återbetalda 2026-03-02: labbdelen kodar "
        "xAI:s och SpaceX:s egen finansiering"),
    (SQ3, "line #526"): ("X Corp:s lån från köpet av Twitter (2022 och 2025), återbetalda 2026-03-02: labbdelen kodar "
        "xAI:s och SpaceX:s egen finansiering"),
    (SQ3, "line #531"): "upprepning i 10-Q för 2026-09-30: villkoren kodas ur den första 10-Q:n (2026-08-04)",
    (SQ3, "line #532"): "upprepning i 10-Q för 2026-09-30: villkoren kodas ur den första 10-Q:n (2026-08-04)",
    (SQ3, "line #535"): "rubrik",
    (SQ3, "line #536"): "upprepning i 10-Q för 2026-09-30: villkoren kodas ur den första 10-Q:n (2026-08-04)",
    (SQ3, "line #537"): "upprepning i 10-Q för 2026-09-30: villkoren kodas ur den första 10-Q:n (2026-08-04)",
    (SQ3, "line #562"): "tabell över bokfört och verkligt värde: inte nominellt belopp",
    (SQ3, "line #563"): "tabell över bokfört och verkligt värde: inte nominellt belopp",
    (SQ3, "line #564"): "tabell över bokfört och verkligt värde: inte nominellt belopp",
    (SQ3, "line #565"): "tabell över bokfört och verkligt värde: inte nominellt belopp",
    (SQ3, "line #800"): "rättstvist: inte ett instrument",
    (SQ3, "line #808"): "Valors utrustningslån per 2025-12-31 (jämförelse): ingår i övrig finansiering",
    (SQ3, "line #1311"): "kassaflöde eller likviditet: inte skuld",
    (SQ3, "line #1314"): "MD&A: samma tal som kodas ur noten (Note 9)",
    (SQ3, "line #1317"): "MD&A: samma tal som kodas ur noten (Note 9)",
    (SQ3, "line #1327"): "MD&A: samma tal som kodas ur noten (Note 9)",
    (SQ3, "line #1350"): "kassaflöde eller likviditet: inte skuld",
    (SQ3, "line #1354"): "kassaflöde eller likviditet: inte skuld",
    (SQ3, "line #1363"): "MD&A: samma tal som kodas ur noten (Note 9)",
}
