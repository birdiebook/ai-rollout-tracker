"""R20 review of the KR1 extraction: spread at issuance (docs/granskning/r20-kredit-emission.md). No network.

Evidence was read on 2026-11-25 in the term sheets and final prospectus supplements, re-fetched from www.sec.gov with
the honest client (source r20_review, not KR1's cache) and dated with EDGAR's submissions API. Only ids, numbers,
dates, accession numbers and SHA-256 prefixes are kept here, never filing text.

- Pinned rows: the 72 rows of the random sample and the rest of one complete term sheet per issuer (96 rows), as read
  by R20, plus a digest of every row (all 239 were checked with R20's own text and key segmentation). A change to a
  reviewed row must be reviewed again.
- Offerings: every term sheet has the same tranches as the cover of its final supplement (pinned pairs).
- Properties: the locked rules and the register entry are unchanged, the 11 series equal an independent recomputation,
  no version is dated before the quarter end or before a tranche in it was filed, every vintage can be rebuilt from the
  rows filed by then, the issuer mix caveat, licence class and publish flag, no filing text in git.
- Findings R20-1 to R20-5 were strict xfail until corrected; corrected in auto14k/x17-kredit-emission (markers
  removed, assertions unchanged).
"""

from __future__ import annotations

import hashlib
import re

import pandas as pd
import pytest

from ai_tracker import config
from ai_tracker import credit_issuance_check as chk
from ai_tracker.sources import credit_issuance as ci
from ai_tracker.sources import credit_issuance_corpus as cc
from ai_tracker.sources import credit_terms as ct

SOURCE_DOC = config.REPO / "docs" / "kallor" / "kredit_emission.md"
REGISTER = config.REPO / "docs" / "mattregister.md"
REVIEW_DAY = "2026-11-25"
LOCKED_RULES_SHA256 = "23342fd1cee8b459fef3977810c2990da7668b09f10ccf79205ef1f1bb873658"  # = 2bac788
REGISTER_ENTRY_SHA256 = "bc20139ef71728cc67afdcdc244c6b1211817855b43b91839c9385435d9045d2"  # = 2bac788


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    """The curated CSV as strings (exactly as committed)."""
    return pd.read_csv(ci.PATH, dtype=str).fillna("")


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return ci.load()


# ------------------------------------------------------------------ order (point 1)


def _section(text: str, start: str, stop: str) -> str:
    a = text.index(start)
    b = text.find(stop, a + len(start))
    return (text[a:b] if b > 0 else text[a:]).strip()


def test_locked_coding_rules_are_unchanged_since_the_lock():
    text = SOURCE_DOC.read_text(encoding="utf-8")
    rules = _section(text, "## Kodningsregler", "## Tolkningar")
    assert hashlib.sha256(rules.encode()).hexdigest() == LOCKED_RULES_SHA256


def test_register_entry_is_unchanged_since_the_lock():
    text = REGISTER.read_text(encoding="utf-8")
    entry = _section(text, "### 2026-11-25 – KR1", "\n### ")
    assert hashlib.sha256(entry.encode()).hexdigest() == REGISTER_ENTRY_SHA256


# ------------------------------------------------------------------ correctness (point 2)

# id, currency, rate_type, principal (millions), coupon, maturity, spread_bp, yield, price, benchmark yield,
# pricing date, settlement date, filed: read by R20 in the re-fetched term sheet (filed: EDGAR filingDate)
READ_BY_R20 = [
    ("amzn_2020-06-01_06", "USD", "fixed", 2000, "2.7", "2060-06-03", "130", "2.749", "98.816", "1.449", "2020-06-01", "2020-06-03", "2020-06-01"),
    ("amzn_2021-05-10_01", "USD", "fixed", 1000, "0.25", "2023-05-12", "10", "0.257", "99.986", "0.157", "2021-05-10", "2021-05-12", "2021-05-11"),
    ("amzn_2021-05-10_02", "USD", "fixed", 2500, "0.45", "2024-05-12", "20", "0.499", "99.854", "0.299", "2021-05-10", "2021-05-12", "2021-05-11"),
    ("amzn_2021-05-10_03", "USD", "fixed", 2750, "1", "2026-05-12", "30", "1.089", "99.568", "0.789", "2021-05-10", "2021-05-12", "2021-05-11"),
    ("amzn_2021-05-10_04", "USD", "fixed", 2250, "1.65", "2028-05-12", "40", "1.659", "99.941", "1.259", "2021-05-10", "2021-05-12", "2021-05-11"),
    ("amzn_2021-05-10_05", "USD", "fixed", 3000, "2.1", "2031-05-12", "50", "2.102", "99.982", "1.602", "2021-05-10", "2021-05-12", "2021-05-11"),
    ("amzn_2021-05-10_06", "USD", "fixed", 2000, "2.875", "2041-05-12", "70", "2.9", "99.623", "2.2", "2021-05-10", "2021-05-12", "2021-05-11"),
    ("amzn_2021-05-10_07", "USD", "fixed", 3250, "3.1", "2051-05-12", "80", "3.137", "99.284", "2.337", "2021-05-10", "2021-05-12", "2021-05-11"),
    ("amzn_2021-05-10_08", "USD", "fixed", 1750, "3.25", "2061-05-12", "95", "3.287", "99.18", "2.337", "2021-05-10", "2021-05-12", "2021-05-11"),
    ("amzn_2022-04-11_03", "USD", "fixed", 2000, "3.3", "2027-04-13", "55", "3.345", "99.794", "2.795", "2022-04-11", "2022-04-13", "2022-04-11"),
    ("amzn_2022-04-11_04", "USD", "fixed", 1500, "3.45", "2029-04-13", "65", "3.485", "99.784", "2.835", "2022-04-11", "2022-04-13", "2022-04-11"),
    ("amzn_2022-04-11_07", "USD", "fixed", 1250, "4.1", "2062-04-13", "130", "4.124", "99.532", "2.824", "2022-04-11", "2022-04-13", "2022-04-11"),
    ("amzn_2022-11-29_03", "USD", "fixed", 2000, "4.55", "2027-12-01", "62.5", "4.563", "99.942", "3.938", "2022-11-29", "2022-12-01", "2022-11-29"),
    ("amzn_2022-11-29_04", "USD", "fixed", 1500, "4.65", "2029-12-01", "80", "4.662", "99.929", "3.862", "2022-11-29", "2022-12-01", "2022-11-29"),
    ("amzn_2025-11-17_01", "USD", "fixed", 2500, "3.9", "2028-11-20", "30", "3.908", "99.978", "3.608", "2025-11-17", "2025-11-20", "2025-11-17"),
    ("amzn_2025-11-17_03", "USD", "fixed", 1500, "4.35", "2033-03-20", "47", "4.375", "99.85", "3.905", "2025-11-17", "2025-11-20", "2025-11-17"),
    ("amzn_2025-11-17_05", "USD", "fixed", 3000, "5.45", "2055-11-20", "75", "5.483", "99.517", "4.733", "2025-11-17", "2025-11-20", "2025-11-17"),
    ("amzn_2026-03-10_01", "USD", "floating", 1750, "", "2028-03-13", "44", "", "100", "", "2026-03-10", "2026-03-13", "2026-03-10"),
    ("amzn_2026-03-10_02", "USD", "floating", 1000, "", "2029-03-13", "59", "", "100", "", "2026-03-10", "2026-03-13", "2026-03-10"),
    ("amzn_2026-03-10_03", "USD", "fixed", 2250, "3.85", "2028-03-13", "30", "3.882", "99.939", "3.582", "2026-03-10", "2026-03-13", "2026-03-10"),
    ("amzn_2026-03-10_08", "USD", "fixed", 2500, "5.65", "2046-03-13", "95", "5.698", "99.431", "4.748", "2026-03-10", "2026-03-13", "2026-03-10"),
    ("amzn_2026-03-11_05", "EUR", "fixed", 2500, "3.7", "2035-03-16", "83", "3.73", "99.774", "", "2026-03-11", "2026-03-16", "2026-03-11"),
    ("amzn_2026-07-07_07", "USD", "fixed", 4000, "6.1", "2056-07-09", "110", "6.147", "99.36", "5.047", "2026-07-07", "2026-07-09", "2026-07-07"),
    ("amzn_2026-09-09_01", "GBP", "fixed", 1250, "5.2", "2029-09-14", "53", "5.211", "99.97", "4.681", "2026-09-09", "2026-09-14", "2026-09-09"),
    ("amzn_2026-09-09_02", "GBP", "fixed", 1000, "5.55", "2032-09-14", "75", "5.561", "99.945", "4.811", "2026-09-09", "2026-09-14", "2026-09-09"),
    ("amzn_2026-09-09_03", "GBP", "fixed", 1000, "6.25", "2038-09-14", "90", "6.277", "99.775", "5.377", "2026-09-09", "2026-09-14", "2026-09-09"),
    ("googl_2020-08-03_04", "USD", "fixed", 1250, "1.9", "2040-08-15", "73", "1.938", "99.371", "1.208", "2020-08-03", "2020-08-05", "2020-08-03"),
    ("googl_2020-08-03_06", "USD", "fixed", 2000, "2.25", "2060-08-15", "108", "2.288", "99.007", "1.208", "2020-08-03", "2020-08-05", "2020-08-03"),
    ("googl_2025-04-28_01", "USD", "fixed", 750, "4", "2030-05-15", "32", "4.129", "99.417", "3.809", "2025-04-28", "2025-05-01", "2025-04-28"),
    ("googl_2025-04-28_02", "USD", "fixed", 1250, "4.5", "2035-05-15", "47", "4.678", "98.585", "4.208", "2025-04-28", "2025-05-01", "2025-04-28"),
    ("googl_2025-04-28_03", "USD", "fixed", 1500, "5.25", "2055-05-15", "62", "5.314", "99.042", "4.694", "2025-04-28", "2025-05-01", "2025-04-28"),
    ("googl_2025-04-28_04", "USD", "fixed", 1500, "5.3", "2065-05-15", "70", "5.394", "98.461", "4.694", "2025-04-28", "2025-05-01", "2025-04-28"),
    ("googl_2025-04-29_02", "EUR", "fixed", 1500, "3", "2033-05-06", "72", "3.081", "99.433", "", "2025-04-29", "2025-05-06", "2025-04-29"),
    ("googl_2025-04-29_03", "EUR", "fixed", 1250, "3.375", "2037-05-06", "95", "3.493", "98.859", "", "2025-04-29", "2025-05-06", "2025-04-29"),
    ("googl_2025-04-29_04", "EUR", "fixed", 1250, "3.875", "2045-05-06", "130", "3.889", "99.808", "", "2025-04-29", "2025-05-06", "2025-04-29"),
    ("googl_2025-11-03_02", "EUR", "fixed", 1000, "2.875", "2031-11-06", "47", "2.903", "99.848", "", "2025-11-03", "2025-11-06", "2025-11-03"),
    ("googl_2025-11-03_03", "EUR", "fixed", 1000, "3.125", "2034-11-06", "62", "3.23", "99.191", "", "2025-11-03", "2025-11-06", "2025-11-03"),
    ("googl_2025-11-03_12", "USD", "fixed", 2000, "5.35", "2045-11-15", "72", "5.368", "99.779", "4.648", "2025-11-03", "2025-11-06", "2025-11-04"),
    ("googl_2026-02-09_05", "USD", "fixed", 1500, "5.5", "2046-02-15", "75", "5.543", "99.484", "4.793", "2026-02-09", "2026-02-13", "2026-02-10"),
    ("googl_2026-02-10_02", "GBP", "fixed", 1250, "4.625", "2032-11-13", "55", "4.612", "99.791", "4.062", "2026-02-10", "2026-02-13", "2026-02-10"),
    ("googl_2026-02-10_04", "GBP", "fixed", 1250, "5.875", "2058-02-13", "60", "5.891", "98.549", "5.291", "2026-02-10", "2026-02-13", "2026-02-10"),
    ("googl_2026-02-10_05", "GBP", "fixed", 1000, "6.125", "2126-02-13", "120", "6.05", "99.732", "4.85", "2026-02-10", "2026-02-13", "2026-02-10"),
    ("googl_2026-05-05_03", "EUR", "fixed", 1500, "3.625", "2034-05-11", "63", "3.642", "99.884", "", "2026-05-05", "2026-05-11", "2026-05-05"),
    ("googl_2026-05-05_04", "EUR", "fixed", 1750, "4.1", "2039-05-11", "93", "4.119", "99.812", "", "2026-05-05", "2026-05-11", "2026-05-05"),
    ("googl_2026-05-05_05", "EUR", "fixed", 1250, "4.5", "2045-05-11", "125", "4.521", "99.736", "", "2026-05-05", "2026-05-11", "2026-05-05"),
    ("googl_2026-05-05_06", "EUR", "fixed", 1250, "4.8", "2063-05-11", "175", "4.842", "99.283", "", "2026-05-05", "2026-05-11", "2026-05-05"),
    ("googl_2026-05-15_04", "JPY", "fixed", 64900, "3.189", "2036-05-16", "75", "3.189", "100", "", "2026-05-15", "2026-05-21", "2026-05-15"),
    ("googl_2026-05-15_06", "JPY", "fixed", 9300, "4.395", "2056-05-16", "109", "4.395", "100", "", "2026-05-15", "2026-05-21", "2026-05-15"),
    ("googl_2026-08-06_02", "USD", "floating", 500, "", "2029-08-10", "60", "", "100", "", "2026-08-06", "2026-08-10", "2026-08-07"),
    ("googl_2026-08-06_07", "USD", "fixed", 4500, "5.45", "2036-08-15", "85", "5.52", "99.466", "4.67", "2026-08-06", "2026-08-10", "2026-08-07"),
    ("googl_2026-08-06_09", "USD", "fixed", 4500, "6.375", "2056-08-15", "115", "6.377", "99.972", "5.227", "2026-08-06", "2026-08-10", "2026-08-07"),
    ("googl_2026-11-02_01", "EUR", "floating", 750, "", "2028-11-05", "50", "", "100", "", "2026-11-02", "2026-11-05", "2026-11-02"),
    ("googl_2026-11-19_02", "CAD", "fixed", 1250, "4.8", "2034-11-24", "117.3", "4.857", "99.626", "3.684", "2026-11-19", "2026-11-24", "2026-11-20"),
    ("googl_2026-11-19_03", "CAD", "fixed", 1500, "5.325", "2038-11-24", "150.4", "5.35", "99.781", "3.846", "2026-11-19", "2026-11-24", "2026-11-20"),
    ("meta_2023-05-01_01", "USD", "fixed", 1500, "4.6", "2028-05-15", "95", "4.605", "99.976", "3.655", "2023-05-01", "2023-05-03", "2023-05-01"),
    ("meta_2023-05-01_02", "USD", "fixed", 1000, "4.8", "2030-05-15", "120", "4.838", "99.774", "3.638", "2023-05-01", "2023-05-03", "2023-05-01"),
    ("meta_2023-05-01_03", "USD", "fixed", 1750, "4.95", "2033-05-15", "135", "4.956", "99.951", "3.606", "2023-05-01", "2023-05-03", "2023-05-01"),
    ("meta_2023-05-01_04", "USD", "fixed", 2500, "5.6", "2053-05-15", "177", "5.619", "99.723", "3.849", "2023-05-01", "2023-05-03", "2023-05-01"),
    ("meta_2023-05-01_05", "USD", "fixed", 1750, "5.75", "2063-05-15", "192", "5.769", "99.702", "3.849", "2023-05-01", "2023-05-03", "2023-05-01"),
    ("meta_2025-10-30_03", "USD", "fixed", 6500, "4.875", "2035-11-15", "78", "4.877", "99.982", "4.097", "2025-10-30", "2025-11-03", "2025-10-30"),
    ("meta_2025-10-30_04", "USD", "fixed", 4500, "5.5", "2045-11-15", "88", "5.515", "99.817", "4.635", "2025-10-30", "2025-11-03", "2025-10-30"),
    ("meta_2025-10-30_06", "USD", "fixed", 4500, "5.75", "2065-11-15", "110", "5.757", "99.888", "4.657", "2025-10-30", "2025-11-03", "2025-10-30"),
    ("meta_2026-04-30_03", "USD", "fixed", 6000, "5.25", "2036-05-15", "90", "5.286", "99.72", "4.386", "2026-04-30", "2026-05-04", "2026-04-30"),
    ("meta_2026-04-30_06", "USD", "fixed", 4000, "6.45", "2066-05-15", "147", "6.46", "99.854", "4.99", "2026-04-30", "2026-05-04", "2026-04-30"),
    ("meta_2026-11-03_02", "USD", "fixed", 3250, "6.25", "2033-11-15", "145", "6.289", "99.778", "4.839", "2026-11-03", "2026-11-05", "2026-11-03"),
    ("meta_2026-11-03_05", "USD", "fixed", 2750, "7.5", "2056-11-15", "220", "7.531", "99.629", "5.331", "2026-11-03", "2026-11-05", "2026-11-03"),
    ("meta_2026-11-04_01", "EUR", "fixed", 1750, "4.3", "2031-02-15", "103", "4.327", "99.914", "", "2026-11-04", "2026-11-12", "2026-11-04"),
    ("meta_2026-11-04_03", "EUR", "fixed", 1000, "4.9", "2035-02-15", "160", "4.933", "99.803", "", "2026-11-04", "2026-11-12", "2026-11-04"),
    ("msft_2026-10-29_01", "USD", "floating", 1000, "", "2028-11-03", "35", "", "100", "", "2026-10-29", "2026-11-04", "2026-10-30"),
    ("msft_2026-10-29_02", "USD", "floating", 1000, "", "2029-11-03", "53", "", "100", "", "2026-10-29", "2026-11-04", "2026-10-30"),
    ("msft_2026-10-29_03", "USD", "fixed", 2000, "4.85", "2028-11-03", "25", "4.869", "99.964", "4.619", "2026-10-29", "2026-11-04", "2026-10-30"),
    ("msft_2026-10-29_04", "USD", "fixed", 3250, "5", "2029-11-03", "35", "5.036", "99.901", "4.686", "2026-10-29", "2026-11-04", "2026-10-30"),
    ("msft_2026-10-29_05", "USD", "fixed", 3250, "5.2", "2031-11-03", "45", "5.204", "99.983", "4.754", "2026-10-29", "2026-11-04", "2026-10-30"),
    ("msft_2026-10-29_06", "USD", "fixed", 2500, "5.35", "2033-11-03", "55", "5.386", "99.793", "4.836", "2026-10-29", "2026-11-04", "2026-10-30"),
    ("msft_2026-10-29_07", "USD", "fixed", 4000, "5.55", "2036-11-03", "65", "5.595", "99.659", "4.945", "2026-10-29", "2026-11-04", "2026-10-30"),
    ("msft_2026-10-29_08", "USD", "fixed", 2000, "6.15", "2046-11-03", "85", "6.183", "99.624", "5.333", "2026-10-29", "2026-11-04", "2026-10-30"),
    ("msft_2026-10-29_09", "USD", "fixed", 4000, "6.25", "2056-11-03", "95", "6.256", "99.919", "5.306", "2026-10-29", "2026-11-04", "2026-10-30"),
    ("msft_2026-10-29_10", "USD", "fixed", 2000, "6.35", "2066-11-03", "105", "6.356", "99.914", "5.306", "2026-10-29", "2026-11-04", "2026-10-30"),
    ("orcl_2020-03-30_01", "USD", "fixed", 3500, "2.5", "2025-04-01", "210", "2.508", "99.963", "0.408", "2020-03-30", "2020-04-01", "2020-03-30"),
    ("orcl_2020-03-30_02", "USD", "fixed", 2250, "2.8", "2027-04-01", "225", "2.834", "99.785", "0.584", "2020-03-30", "2020-04-01", "2020-03-30"),
    ("orcl_2020-03-30_03", "USD", "fixed", 3250, "2.95", "2030-04-01", "225", "2.962", "99.897", "0.712", "2020-03-30", "2020-04-01", "2020-03-30"),
    ("orcl_2020-03-30_04", "USD", "fixed", 3000, "3.6", "2040-04-01", "225", "3.619", "99.731", "1.369", "2020-03-30", "2020-04-01", "2020-03-30"),
    ("orcl_2020-03-30_05", "USD", "fixed", 4500, "3.6", "2050-04-01", "225", "3.619", "99.654", "1.369", "2020-03-30", "2020-04-01", "2020-03-30"),
    ("orcl_2020-03-30_06", "USD", "fixed", 3500, "3.85", "2060-04-01", "250", "3.869", "99.615", "1.369", "2020-03-30", "2020-04-01", "2020-03-30"),
    ("orcl_2021-03-22_05", "USD", "fixed", 3250, "3.95", "2051-03-25", "155", "3.96", "99.825", "2.41", "2021-03-22", "2021-03-24", "2021-03-23"),
    ("orcl_2021-03-22_06", "USD", "fixed", 1500, "4.1", "2061-03-25", "170", "4.11", "99.804", "2.41", "2021-03-22", "2021-03-24", "2021-03-23"),
    ("orcl_2022-11-07_01", "USD", "fixed", 1000, "5.8", "2025-11-10", "120", "5.848", "99.869", "4.648", "2022-11-07", "2022-11-09", "2022-11-08"),
    ("orcl_2022-11-07_02", "USD", "fixed", 1250, "6.15", "2029-11-09", "185", "6.167", "99.905", "4.317", "2022-11-07", "2022-11-09", "2022-11-08"),
    ("orcl_2023-02-02_03", "USD", "fixed", 1500, "4.9", "2033-02-06", "150", "4.909", "99.93", "3.409", "2023-02-02", "2023-02-06", "2023-02-02"),
    ("orcl_2025-01-30_01", "USD", "floating", 500, "", "2028-08-03", "76", "", "100", "", "2025-01-30", "2025-02-03", "2025-01-30"),
    ("orcl_2025-01-30_02", "USD", "fixed", 1500, "4.8", "2028-08-03", "57", "4.822", "99.93", "4.252", "2025-01-30", "2025-02-03", "2025-01-30"),
    ("orcl_2025-09-24_01", "USD", "fixed", 3000, "4.45", "2030-09-26", "75", "4.464", "99.938", "3.714", "2025-09-24", "2025-09-26", "2025-09-24"),
    ("orcl_2025-09-24_04", "USD", "fixed", 2500, "5.875", "2045-09-26", "115", "5.879", "99.953", "4.729", "2025-09-24", "2025-09-26", "2025-09-24"),
    ("orcl_2026-02-02_02", "USD", "fixed", 3000, "4.55", "2029-02-04", "95", "4.596", "99.872", "3.646", "2026-02-02", "2026-02-04", "2026-02-02"),
    ("orcl_2026-11-02_02", "USD", "fixed", 1750, "7.45", "2031-11-04", "275", "7.464", "99.942", "4.714", "2026-11-02", "2026-11-04", "2026-11-02"),
    ("orcl_2026-11-02_03", "USD", "fixed", 2250, "7.85", "2033-11-04", "305", "7.851", "99.995", "4.801", "2026-11-02", "2026-11-04", "2026-11-02"),
]
RANDOM_SAMPLE_SEED = 20261145  # 30 % per issuer: msft 3, googl 24, amzn 20, meta 10, orcl 15
COMPLETE_DOCUMENTS = ("0001193125-26-439794", "0001193125-20-091115", "0001193125-21-156519", "0001193125-25-100802",
                      "0001193125-23-130744")  # one whole term sheet per issuer: msft, orcl, amzn, googl, meta

ROW_DIGESTS = {  # sha256 of the committed CSV line, first 12 hex characters (all 239 rows checked by R20)
    "orcl_2020-03-30_01": "9c4aab9f2c48",
    "orcl_2020-03-30_02": "55a6c213d61c",
    "orcl_2020-03-30_03": "a4d5da5e72cc",
    "orcl_2020-03-30_04": "bcfbb3b8898c",
    "orcl_2020-03-30_05": "460c37c6513a",
    "orcl_2020-03-30_06": "3f2ab1f7d50e",
    "amzn_2020-06-01_01": "35bcc62a7d03",
    "amzn_2020-06-01_02": "f7939fd3a030",
    "amzn_2020-06-01_03": "f15548fe28f4",
    "amzn_2020-06-01_04": "0aaacba5b94a",
    "amzn_2020-06-01_05": "70ccd3ad440c",
    "amzn_2020-06-01_06": "53660c81f72d",
    "googl_2020-08-03_01": "19b4be014a4e",
    "googl_2020-08-03_02": "0de22f83ac34",
    "googl_2020-08-03_03": "cb77ef0a09a4",
    "googl_2020-08-03_04": "156752b32e9f",
    "googl_2020-08-03_05": "bc4aefafb7a8",
    "googl_2020-08-03_06": "af9cf4e6aeda",
    "orcl_2021-03-22_01": "1559d8bdcf4c",
    "orcl_2021-03-22_02": "24dd592cbdc4",
    "orcl_2021-03-22_03": "c0b7945c88fe",
    "orcl_2021-03-22_04": "a70e0d79cd37",
    "orcl_2021-03-22_05": "0e83e17ea575",
    "orcl_2021-03-22_06": "2501eadebd26",
    "amzn_2021-05-10_01": "e50e94dd530c",
    "amzn_2021-05-10_02": "80694bda8871",
    "amzn_2021-05-10_03": "1c8a3bdfa928",
    "amzn_2021-05-10_04": "57f3913806a7",
    "amzn_2021-05-10_05": "af438febd557",
    "amzn_2021-05-10_06": "e0f32b9e7f94",
    "amzn_2021-05-10_07": "392585a1ad7e",
    "amzn_2021-05-10_08": "226132ced3a6",
    "amzn_2022-04-11_01": "9e538459983d",
    "amzn_2022-04-11_02": "74f232841e72",
    "amzn_2022-04-11_03": "8b97213c68fc",
    "amzn_2022-04-11_04": "93f371e52517",
    "amzn_2022-04-11_05": "6946eb933531",
    "amzn_2022-04-11_06": "e92d38ea24b2",
    "amzn_2022-04-11_07": "6a8a2c0a146d",
    "orcl_2022-11-07_01": "93e873bf4421",
    "orcl_2022-11-07_02": "eeb124c26c17",
    "orcl_2022-11-07_03": "61fd3840d896",
    "orcl_2022-11-07_04": "eb51765d09ee",
    "amzn_2022-11-29_01": "25209b8cabd6",
    "amzn_2022-11-29_02": "5a3f3616761e",
    "amzn_2022-11-29_03": "e44c6b90f301",
    "amzn_2022-11-29_04": "1630b17a300d",
    "amzn_2022-11-29_05": "00d3e97ea858",
    "orcl_2023-02-02_01": "a3a3755d3bcf",
    "orcl_2023-02-02_02": "5b99f9bd2744",
    "orcl_2023-02-02_03": "21832121796d",
    "orcl_2023-02-02_04": "981202f1b81c",
    "meta_2023-05-01_01": "61d8d17ebaf9",
    "meta_2023-05-01_02": "5b1b3619ef84",
    "meta_2023-05-01_03": "7c63dfb4f2ff",
    "meta_2023-05-01_04": "68ab5da11582",
    "meta_2023-05-01_05": "d91d9616292f",
    "meta_2024-08-07_01": "d5259736abaf",
    "meta_2024-08-07_02": "0a29c1ad159b",
    "meta_2024-08-07_03": "ca2eb3c59079",
    "meta_2024-08-07_04": "89aa33e80b9c",
    "meta_2024-08-07_05": "35a211967e93",
    "orcl_2024-09-25_01": "25bbee635478",
    "orcl_2024-09-25_02": "d082fb324e8e",
    "orcl_2024-09-25_03": "793e861a5454",
    "orcl_2024-09-25_04": "36b62b09edab",
    "orcl_2025-01-30_01": "e283cd7574b6",
    "orcl_2025-01-30_02": "5df144973357",
    "orcl_2025-01-30_03": "0afcadf9c057",
    "orcl_2025-01-30_04": "15bc8f9993df",
    "orcl_2025-01-30_05": "9aad8146099a",
    "orcl_2025-01-30_06": "c5908484dbae",
    "googl_2025-04-28_01": "4668d83631d6",
    "googl_2025-04-28_02": "609c09413e69",
    "googl_2025-04-28_03": "47827c9b67f9",
    "googl_2025-04-28_04": "80cc6140fcdd",
    "googl_2025-04-29_01": "95dc172c2a29",
    "googl_2025-04-29_02": "77f946c501f9",
    "googl_2025-04-29_03": "b85be149aca8",
    "googl_2025-04-29_04": "8c759409dbc9",
    "googl_2025-04-29_05": "87dc4507d6bc",
    "orcl_2025-09-24_01": "0423c280c57f",
    "orcl_2025-09-24_02": "38aebf8b5a7c",
    "orcl_2025-09-24_03": "96c74e0d8345",
    "orcl_2025-09-24_04": "c3c449b843fb",
    "orcl_2025-09-24_05": "bc40fd5e9cb4",
    "orcl_2025-09-24_06": "c0d859967e9f",
    "meta_2025-10-30_01": "1cbf5a4e75c2",
    "meta_2025-10-30_02": "9bd55855b910",
    "meta_2025-10-30_03": "42729c5a0850",
    "meta_2025-10-30_04": "994d4989fa84",
    "meta_2025-10-30_05": "aeafb0082782",
    "meta_2025-10-30_06": "abf7a377875e",
    "googl_2025-11-03_01": "8e5a243f72c8",
    "googl_2025-11-03_02": "237bac8baf80",
    "googl_2025-11-03_03": "80dc8bb24d5e",
    "googl_2025-11-03_04": "bbba5e6fc861",
    "googl_2025-11-03_05": "c50b51e91e65",
    "googl_2025-11-03_06": "5d39b80abd76",
    "googl_2025-11-03_07": "c956b70ffaeb",
    "googl_2025-11-03_08": "f0756b4f111a",
    "googl_2025-11-03_09": "8dc839ec1174",
    "googl_2025-11-03_10": "27e32fbdff01",
    "googl_2025-11-03_11": "5d9429afb0aa",
    "googl_2025-11-03_12": "279062410e5d",
    "googl_2025-11-03_13": "88dedf696091",
    "googl_2025-11-03_14": "af28eccec90b",
    "amzn_2025-11-17_01": "0ef2c780de72",
    "amzn_2025-11-17_02": "6ba3f2be1097",
    "amzn_2025-11-17_03": "e576697b3c1f",
    "amzn_2025-11-17_04": "bb693d775850",
    "amzn_2025-11-17_05": "398873eb5af6",
    "amzn_2025-11-17_06": "ed5e992c830f",
    "orcl_2026-02-02_01": "b57f328d2ee1",
    "orcl_2026-02-02_02": "910dffac2b9a",
    "orcl_2026-02-02_03": "c28b81c3f454",
    "orcl_2026-02-02_04": "6f826f6e3f24",
    "orcl_2026-02-02_05": "a4bec61b8dd9",
    "orcl_2026-02-02_06": "fd9ca97e644e",
    "orcl_2026-02-02_07": "7689836836da",
    "orcl_2026-02-02_08": "b79967a452c6",
    "googl_2026-02-09_01": "fa1093bd981b",
    "googl_2026-02-09_02": "9e504b6b7fbd",
    "googl_2026-02-09_03": "c19df5c4040e",
    "googl_2026-02-09_04": "38f8ef80b9d7",
    "googl_2026-02-09_05": "03b646ca766a",
    "googl_2026-02-09_06": "b09e16682052",
    "googl_2026-02-09_07": "b17679c44fd0",
    "googl_2026-02-10_01": "9f4083767705",
    "googl_2026-02-10_02": "8be2d9544955",
    "googl_2026-02-10_03": "2a0415833f9a",
    "googl_2026-02-10_04": "5ca38591adfc",
    "googl_2026-02-10_05": "494d787ec8c5",
    "amzn_2026-03-10_01": "6d4088827976",
    "amzn_2026-03-10_02": "eef6d739b286",
    "amzn_2026-03-10_03": "10ba2c3b7606",
    "amzn_2026-03-10_04": "b84d46cae0cc",
    "amzn_2026-03-10_05": "a73238e885c1",
    "amzn_2026-03-10_06": "ced25c6dd5b4",
    "amzn_2026-03-10_07": "989a4636cb06",
    "amzn_2026-03-10_08": "7177a84d8826",
    "amzn_2026-03-10_09": "20e35edf7394",
    "amzn_2026-03-10_10": "fccd6402626f",
    "amzn_2026-03-10_11": "f2ceed861ef9",
    "amzn_2026-03-11_01": "b60b9015cc68",
    "amzn_2026-03-11_02": "30064b93d4bd",
    "amzn_2026-03-11_03": "f361e42d8326",
    "amzn_2026-03-11_04": "f109faadbe1c",
    "amzn_2026-03-11_05": "9ed0c657dd9c",
    "amzn_2026-03-11_06": "a6737ab261ee",
    "amzn_2026-03-11_07": "f0788b4a480c",
    "amzn_2026-03-11_08": "60cf34af59dc",
    "meta_2026-04-30_01": "0c35cd817bd7",
    "meta_2026-04-30_02": "f1edd85d2f90",
    "meta_2026-04-30_03": "2caa9162e05d",
    "meta_2026-04-30_04": "bc5960cdaea1",
    "meta_2026-04-30_05": "4f1e9b459957",
    "meta_2026-04-30_06": "d54778caf007",
    "googl_2026-05-05_01": "717895f344db",
    "googl_2026-05-05_02": "c9847b98feec",
    "googl_2026-05-05_03": "a53870f51125",
    "googl_2026-05-05_04": "8bdc2d17d043",
    "googl_2026-05-05_05": "f9ce1911d6de",
    "googl_2026-05-05_06": "7c7a9dae21d9",
    "googl_2026-05-05_07": "708c22245e27",
    "googl_2026-05-05_08": "182f4a3ba1a1",
    "googl_2026-05-05_09": "9d0db39e13c9",
    "googl_2026-05-05_10": "aa9f9fb442d4",
    "googl_2026-05-15_01": "b1582f7750d7",
    "googl_2026-05-15_02": "2cee1fed708b",
    "googl_2026-05-15_03": "0198b429c401",
    "googl_2026-05-15_04": "7c7ac125bdb1",
    "googl_2026-05-15_05": "d44240d85705",
    "googl_2026-05-15_06": "8fc5e9f8bf0f",
    "googl_2026-05-15_07": "2c2ab1569fc2",
    "amzn_2026-06-08_01": "42e748013167",
    "amzn_2026-06-08_02": "2170842f98bd",
    "amzn_2026-06-08_03": "5f228cb0eab1",
    "amzn_2026-06-08_04": "f3906879ad11",
    "amzn_2026-06-08_05": "567805af6b91",
    "amzn_2026-07-07_01": "4a3dc0e9a434",
    "amzn_2026-07-07_02": "a067d4e848cb",
    "amzn_2026-07-07_03": "a829caa9c331",
    "amzn_2026-07-07_04": "3cf09a174135",
    "amzn_2026-07-07_05": "4af04a84f494",
    "amzn_2026-07-07_06": "ac8e02b9ce8b",
    "amzn_2026-07-07_07": "c7596f2422c7",
    "amzn_2026-07-07_08": "6e42c616de0c",
    "googl_2026-08-06_01": "cdecef62db92",
    "googl_2026-08-06_02": "11411354874d",
    "googl_2026-08-06_03": "cf33be96f741",
    "googl_2026-08-06_04": "d959ab1fc2e7",
    "googl_2026-08-06_05": "dd3921ade959",
    "googl_2026-08-06_06": "f94d52e6c990",
    "googl_2026-08-06_07": "230c36dc1ff2",
    "googl_2026-08-06_08": "1e64fd98c23d",
    "googl_2026-08-06_09": "924a07374831",
    "googl_2026-08-06_10": "52c925f3a01b",
    "amzn_2026-09-09_01": "45c85b647501",
    "amzn_2026-09-09_02": "97268730e437",
    "amzn_2026-09-09_03": "66be8182caaf",
    "amzn_2026-09-09_04": "8ba6b1d6aebe",
    "msft_2026-10-29_01": "335cee1c0ee2",
    "msft_2026-10-29_02": "ae83bbc540f1",
    "msft_2026-10-29_03": "21f53d312eeb",
    "msft_2026-10-29_04": "0408118f9da7",
    "msft_2026-10-29_05": "d510031baa99",
    "msft_2026-10-29_06": "7d842c5ceeec",
    "msft_2026-10-29_07": "21ac7e05e3a2",
    "msft_2026-10-29_08": "34335d3f6ac1",
    "msft_2026-10-29_09": "e1509b813e60",
    "msft_2026-10-29_10": "ec1e2245ab4f",
    "googl_2026-11-02_01": "bce23296801c",
    "googl_2026-11-02_02": "918915e9f28e",
    "googl_2026-11-02_03": "a6ab637513d5",
    "googl_2026-11-02_04": "66212ffcddb1",
    "googl_2026-11-02_05": "77dcc6559968",
    "googl_2026-11-02_06": "f6d8fdbb3ff4",
    "googl_2026-11-02_07": "8db41b64ac69",
    "orcl_2026-11-02_01": "d4eb6b042345",
    "orcl_2026-11-02_02": "7ee46fbf4dae",
    "orcl_2026-11-02_03": "3f53fab76ccb",
    "orcl_2026-11-02_04": "f35d4c0c2ee9",
    "orcl_2026-11-02_05": "e7762b956d65",
    "meta_2026-11-03_01": "85ec286190e9",
    "meta_2026-11-03_02": "ed633cefbd6d",
    "meta_2026-11-03_03": "d17804f12a57",
    "meta_2026-11-03_04": "d8992663388d",
    "meta_2026-11-03_05": "9a31ea80dbfb",
    "meta_2026-11-04_01": "0d49d0efd62e",
    "meta_2026-11-04_02": "692a6b646594",
    "meta_2026-11-04_03": "36963edc966a",
    "meta_2026-11-04_04": "fee2a11d55df",
    "meta_2026-11-04_05": "6406fbd465bd",
    "meta_2026-11-04_06": "c3c40faaccfd",
    "googl_2026-11-19_01": "46c2a0d880c7",
    "googl_2026-11-19_02": "aa82b711a079",
    "googl_2026-11-19_03": "711633fd2a2a",
    "googl_2026-11-19_04": "f07ea0133298",
}


def test_rows_read_by_r20_are_unchanged(raw):
    cols = ["id", "currency", "rate_type", "principal", "coupon_pct", "maturity", "spread_bp", "yield_pct", "price_pct",
            "benchmark_yield_pct", "pricing_date", "settlement_date", "filed"]
    have = {r[0]: r for r in raw[cols].itertuples(index=False)}
    assert len(READ_BY_R20) == 96
    for want in READ_BY_R20:
        got = have[want[0]]
        assert tuple(got[1:3]) == want[1:3] and float(got[3]) == want[3] and tuple(got[4:]) == want[4:], want[0]


def test_random_sample_is_the_registered_share_and_covers_every_issuer(raw):
    sample = pd.concat([raw[raw.company == c].sample(n=n, random_state=RANDOM_SAMPLE_SEED)
                        for c, n in {"msft": 3, "googl": 24, "amzn": 20, "meta": 10, "orcl": 15}.items()])
    assert len(sample) / len(raw) >= 0.30 and set(sample.company) == {"msft", "googl", "amzn", "meta", "orcl"}
    read = {r[0] for r in READ_BY_R20}
    assert set(sample.id) <= read
    assert set(raw[raw.accession.isin(COMPLETE_DOCUMENTS)].id) <= read
    assert set(raw[raw.accession.isin(COMPLETE_DOCUMENTS)].company) == {"msft", "googl", "amzn", "meta", "orcl"}


def test_every_row_is_the_reviewed_row():
    lines = ci.PATH.read_text(encoding="utf-8").splitlines()[1:]
    got = {line.split(",", 1)[0]: hashlib.sha256(line.encode()).hexdigest()[:12] for line in lines}
    assert got == ROW_DIGESTS


def test_manual_row_is_the_final_supplement_amount(df):
    r = df[df["method"] == "manual"]
    assert list(r["id"]) == ["orcl_2021-03-22_05"]
    assert r["principal"].iloc[0] == 3250 and "0001193125-21-091259" in r["note"].iloc[0]  # its 424B2 cover


# ------------------------------------------------------------------ completeness (point 3)

# term sheet accession -> (final supplement accession, tranches on its cover, currency, cover total in millions)
FINAL_SUPPLEMENTS = {
    "0001193125-20-091115": ("0001193125-20-092802", 6, "USD", 20000),
    "0001193125-20-157446": ("0001193125-20-158910", 6, "USD", 10000),
    "0001193125-20-208301": ("0001193125-20-209443", 6, "USD", 10000),
    "0001193125-21-089955": ("0001193125-21-091259", 6, "USD", 15000),
    "0001193125-21-156519": ("0001193125-21-157863", 8, "USD", 18500),
    "0001193125-22-101798": ("0001193125-22-103074", 7, "USD", 12750),
    "0001193125-22-279427": ("0001193125-22-280294", 4, "USD", 7000),
    "0001193125-22-294467": ("0001193125-22-295511", 5, "USD", 8250),
    "0001193125-23-022802": ("0001193125-23-024315", 4, "USD", 5250),
    "0001193125-23-130744": ("0001193125-23-132617", 5, "USD", 8500),
    "0001193125-24-196020": ("0001193125-24-197096", 5, "USD", 10500),
    "0001193125-24-226101": ("0001193125-24-227049", 4, "USD", 6250),
    "0001193125-25-017365": ("0001193125-25-018491", 6, "USD", 7750),
    "0001193125-25-100802": ("0001193125-25-107005", 4, "USD", 5000),
    "0001193125-25-103574": ("0001193125-25-110061", 5, "EUR", 6750),
    "0001193125-25-215807": ("0001193125-25-217490", 6, "USD", 18000),
    "0001193125-25-258837": ("0001193125-25-261217", 6, "USD", 30000),
    "0001193125-25-262837": ("0001193125-25-267232", 6, "EUR", 6500),
    "0001193125-25-263045": ("0001193125-25-267244", 8, "USD", 17500),
    "0001104659-25-113283": ("0001104659-25-114098", 6, "USD", 15000),
    "0001193125-26-033882": ("0001193125-26-035603", 8, "USD", 25000),
    "0001193125-26-043127": ("0001193125-26-046846", 7, "USD", 20000),
    "0001193125-26-044473": ("0001193125-26-048730", 5, "GBP", 5500),
    "0001104659-26-025948": ("0001104659-26-027125", 11, "USD", 37000),
    "0001104659-26-026393": ("0001104659-26-027669", 8, "EUR", 14500),
    "0001193125-26-197902": ("0001193125-26-201738", 6, "USD", 25000),
    "0001193125-26-206404": ("0001193125-26-212210", 6, "EUR", 9000),
    "0001193125-26-206809": ("0001193125-26-212222", 4, "CAD", 8500),
    "0001193125-26-225046": ("0001193125-26-228923", 7, "JPY", 576500),
    "0001104659-26-071456": ("0001104659-26-072332", 5, "CAD", 14000),
    "0001104659-26-081334": ("0001104659-26-081786", 8, "USD", 25000),
    "0001193125-26-338750": ("0001193125-26-340264", 10, "USD", 25000),
    "0001104659-26-106322": ("0001104659-26-107122", 4, "GBP", 4250),
    "0001193125-26-439794": ("0001193125-26-442618", 10, "USD", 25000),
    "0001193125-26-443857": ("0001193125-26-447343", 7, "EUR", 6000),
    "0001193125-26-443918": ("0001193125-26-445846", 5, "USD", 10000),
    "0001193125-26-445646": ("0001193125-26-448015", 5, "USD", 15000),
    "0001193125-26-447522": ("0001193125-26-450754", 6, "EUR", 9000),
    "0001193125-26-469213": ("0001193125-26-470750", 4, "CAD", 6000),
}


def test_every_offering_equals_its_final_supplement(df):
    assert set(df["accession"]) == set(FINAL_SUPPLEMENTS) and (df["form"] == "FWP").all()
    for acc, (_, n, cur, total) in FINAL_SUPPLEMENTS.items():
        g = df[df["accession"] == acc]
        assert (len(g), set(g["currency"]), float(g["principal"].sum())) == (n, {cur}, total), acc
    counts = df.groupby("company").size().to_dict()
    assert counts == {"msft": 10, "googl": 79, "amzn": 68, "meta": 33, "orcl": 49}  # = the 39 covers, 239 tranches


# ------------------------------------------------------------------ series and dating (point 5)

AS_OF = pd.Timestamp(REVIEW_DAY)
ROWS = {"issuance_googl_q": 5, "issuance_amzn_q": 7, "issuance_meta_q": 4, "issuance_orcl_q": 8, "issuance_msft_q": 0,
        "spread_issue_ai_q": 17, "spread_issue_ai_7_12y_q": 17, "spread_issue_googl_q": 5, "spread_issue_amzn_q": 7,
        "spread_issue_meta_q": 4, "spread_issue_orcl_q": 8}


def _own_versions(rows: pd.DataFrame, f, as_of) -> list[tuple]:
    """R20's own reading of the registered dating: max(day after the quarter, filed), a later filing a new version."""
    out = []
    rows = rows.assign(q=pd.to_datetime(rows["pricing_date"]).dt.to_period("Q").astype(str),
                       f=pd.to_datetime(rows["filed"]))
    for q, g in rows.groupby("q"):
        start = pd.Period(q, "Q").end_time.normalize() + pd.Timedelta(days=1)
        last = None
        for d in sorted({max(start, x) for x in g["f"]}):
            if d <= as_of:
                v = f(g[g["f"] <= d])
                if last is None or abs(v - last) > 1e-9:
                    out.append((q, round(v, 9), d))
                    last = v
    return sorted(out, key=lambda x: (x[2], x[0]))


def _own_series(df: pd.DataFrame, as_of) -> dict[str, list[tuple]]:
    usd = df[df["currency"] == "USD"]
    el = usd[(usd["rate_type"] == "fixed") & (usd["benchmark_type"] == "treasury") & usd["spread_bp"].notna()]
    w = lambda g: float((g["spread_bp"] * g["principal"]).sum() / g["principal"].sum())
    out = {f"issuance_{c}_q": _own_versions(usd[usd["company"] == c], lambda g: float(g["principal"].sum()), as_of)
           for c in ("googl", "amzn", "meta", "orcl", "msft")}
    out["spread_issue_ai_q"] = _own_versions(el, w, as_of)
    out["spread_issue_ai_7_12y_q"] = _own_versions(el[(el["tenor_years"] >= 6.5) & (el["tenor_years"] < 12.5)], w,
                                                   as_of)
    for c in ("googl", "amzn", "meta", "orcl"):
        out[f"spread_issue_{c}_q"] = _own_versions(el[el["company"] == c], w, as_of)
    return out


def _branch_series(df: pd.DataFrame, as_of) -> dict[str, list[tuple]]:
    out = {f"issuance_{c}_q": ci.issuance(df, c, as_of) for c in ("googl", "amzn", "meta", "orcl", "msft")}
    out["spread_issue_ai_q"] = ci.spread(df, None, None, as_of)
    out["spread_issue_ai_7_12y_q"] = ci.spread(df, None, ci.BAND_7_12, as_of)
    for c in ("googl", "amzn", "meta", "orcl"):
        out[f"spread_issue_{c}_q"] = ci.spread(df, (c,), None, as_of)
    return {k: sorted(((str(p), round(float(v), 9), pd.Timestamp(d)) for p, v, d in s.itertuples(index=False)),
                      key=lambda x: (x[2], x[0])) for k, s in out.items()}


def test_series_equal_an_independent_recomputation(df):
    own, branch = _own_series(df, AS_OF), _branch_series(df, AS_OF)
    assert {k: len(v) for k, v in branch.items()} == ROWS
    assert own == branch
    assert sorted(ci.spread_issuers(df)) == ["amzn", "googl", "meta", "orcl"]


def test_no_version_is_dated_before_its_quarter_end_or_its_filings(df):
    for key, rows in _branch_series(df, AS_OF).items():
        for period, _, known in rows:
            assert known >= pd.Period(period, "Q").end_time.normalize() + pd.Timedelta(days=1), (key, period)
    late = df[pd.to_datetime(df["filed"]) > pd.to_datetime(df["pricing_date"]).dt.to_period("Q").dt.end_time]
    assert late.empty  # every tranche was filed inside its quarter: every version is known the day after it


def test_every_vintage_rebuilds_from_the_rows_filed_by_then(df):
    """No leakage: the table as known on d (rows filed <= d, as_of = d) gives exactly the versions known by d."""
    full = _branch_series(df, AS_OF)
    days = sorted({pd.Timestamp(x) for x in df["filed"]} | {pd.Timestamp(x) - pd.Timedelta(days=1) for x in df["filed"]}
                  | {pd.Period(q, "Q").end_time.normalize() + pd.Timedelta(days=1)
                     for q in pd.to_datetime(df["pricing_date"]).dt.to_period("Q").astype(str)})
    for d in [x for x in days if x <= AS_OF]:
        then = _branch_series(df[pd.to_datetime(df["filed"]) <= d], d)
        for key, rows in full.items():
            assert then[key] == [r for r in rows if r[2] <= d], (key, d)


def test_filing_on_the_day_after_the_quarter_is_in_the_first_version():
    rows = pd.DataFrame({"pricing_date": ["2024-03-28", "2024-03-29"], "filed": ["2024-03-28", "2024-04-01"],
                         "principal": [1000.0, 3000.0]})
    v = ci.quarter_versions(rows, lambda g: float(g["principal"].sum()), "2024-12-31")
    assert list(v["known_from"]) == [pd.Timestamp("2024-04-01")] and list(v["value"]) == [4000.0]


def test_pooled_spread_is_one_issuer_in_12_of_17_quarters(df):
    el = ci.eligible_spread(df)
    q = pd.to_datetime(el["pricing_date"]).dt.to_period("Q").astype(str)
    issuers = el.assign(q=q)[q < "2026Q4"].groupby("q")["company"].nunique()
    assert len(issuers) == 17 and int((issuers == 1).sum()) == 12
    band = ci.eligible_spread(df, ci.BAND_7_12)
    assert len(el) == 162 and len(band) == 52


def test_band_edges_are_not_decided_by_rounding(df):
    exact = (pd.to_datetime(df["maturity"]) - pd.to_datetime(df["pricing_date"])).dt.days / 365.25
    assert not (((exact - 6.5).abs() < 0.02) | ((exact - 12.5).abs() < 0.02)).any()


# ------------------------------------------------------------------ licence and publication (point 6)


def test_catalog_series_are_unpublished_ja_and_not_core():
    from ai_tracker import catalog, licenses
    from ai_tracker.series import credit_issuance as series
    from ai_tracker.state import register

    keys = {s.key for s in series.SPECS}
    assert keys == set(ROWS)
    assert all(not s.publish and s.max_age_days == 1100 and s.lag_days == 1 for s in series.SPECS)
    assert {licenses.verdict(s, catalog.by_key()).klass for s in series.SPECS} == {licenses.JA}
    core = {k for v in register.CORE_SERIES.values() for k in v}
    assert core and not keys & core
    index = re.compile(r"(?i)\bICE\b|moody|\bFRED\b|BAML")  # no market index enters (licence, point 6)
    assert not any(index.search(s.source + s.license + s.note) for s in series.SPECS)


# ------------------------------------------------------------------ text in git and the self-check (point 7)


def test_no_filing_text_in_git(raw):
    notes = [n for n in raw["note"] if n]
    assert len(notes) == 1 and len(notes[0].split()) < 30  # the manual row's reason, numbers and references only
    assert raw["benchmark"].str.len().max() <= 80 and raw["security"].str.len().max() <= 40
    gitignore = (config.REPO / ".gitignore").read_text(encoding="utf-8")
    assert "data/*" in gitignore.splitlines()
    assert ci.BLOCKS_DIR.relative_to(config.REPO).parts[:2] == ("data", "raw")


# ------------------------------------------------------------------ interpretations that hold (parser, synthetic)


def _row(label: str, value: str) -> str:
    return f"<TR><TD>{label}</TD><TD>{value}</TD></TR>"


def _euro_sheet() -> str:
    return ("<P>Pricing Term Sheet</P><TABLE>" + _row("Trade Date:", "May 5, 2026")
            + _row("Settlement Date (T+4):", "May 11, 2026")
            + _row("Aggregate Principal Amount:", "2034 Notes: €1,500,000,000 2039 Notes: €1,750,000,000")
            + _row("Maturity Date:", "2034 Notes: May 11, 2034 2039 Notes: May 11, 2039")
            + _row("Coupon (Interest Rate):", "2034 Notes: 3.625% per annum 2039 Notes: 4.100% per annum")
            + _row("Public Offering Price:", "2034 Notes: 99.884% 2039 Notes: 99.812%")
            + _row("Yield to Maturity:", "2034 Notes: 3.642% 2039 Notes: 4.119%")
            + _row("Spread to Benchmark Bund:", "2034 Notes: +67.6 bps 2039 Notes: +85.2 bps")
            + _row("Benchmark Bund:", "2034 Notes: DBR 2.200% due February 15, 2034 2039 Notes: DBR 1.000% due May "
                                      "15, 2038")
            + _row("Spread to Mid-Swap Yield:", "2034 Notes: +63 bps 2039 Notes: +93 bps") + "</TABLE>")


def test_euro_rows_take_the_spread_to_mid_swaps():
    _, rows = ct.parse(cc.lines(_euro_sheet()), "2026-05-05")
    assert [(r["currency"], r["spread_bp"], r["benchmark_type"], r["benchmark_yield_pct"]) for r in rows] == [
        ("EUR", 63, "mid_swaps", None), ("EUR", 93, "mid_swaps", None)]
    assert [r["col"] for r in rows] == [0, 1]  # col #j = the tranche's key among the keys (interpretation 2)


# ------------------------------------------------------------------ findings (corrected in X17, were strict xfail)


def _keyed_sheet() -> str:
    return ("<P>Pricing Term Sheet</P><TABLE>" + _row("Trade Date:", "May 1, 2023")
            + _row("Settlement Date (T+2):", "May 3, 2023")
            + _row("Principal Amount:", "2028 Notes: $1,500,000,000 2053 Notes: $2,500,000,000")
            + _row("Maturity:", "2028 Notes: May 15, 2028 2053 Notes: May 15, 2053")
            + _row("Public Offering Price:", "2028 Notes: 99.976% 2053 Notes: 99.723%")
            + _row("Coupon (Interest Rate):", "2028 Notes: 4.600% 2053 Notes: 5.600%")
            + _row("Yield to Maturity:", "2028 Notes: 4.605% 2053 Notes: 5.619%")
            + _row("Spread to Benchmark Treasury:", "2028 Notes: T + 95 bps 2053 Notes: T + 177 bps")
            + _row("Benchmark Treasury:", "2028 Notes: UST 3.500% due April 30, 2028 2053 Notes: UST 4.000% due "
                                          "November 15, 2052")
            + _row("Benchmark Treasury Price/Yield:", "2028 Notes: 99-09+ and 3.655% 2053 Notes: 102-21 and 3.849%")
            + "</TABLE>")


def _csv_row(p: dict, lines: list[str], **kw) -> pd.Series:
    r = {c: p.get(c) for c in ci.COLUMNS}
    r.update(id=f"meta_{p['pricing_date']}_01", company="meta", filed=p["pricing_date"],
             accepted=f"{p['pricing_date']}T20:00:00.000Z", form="FWP",
             source_url="https://www.sec.gov/Archives/edgar/data/1326801/000119312523130744/x.htm",
             accession="0001193125-23-130744", locator=ci.locator(p),
             block_sha256=cc.block_hash(cc.block_at(lines, ci.locator(p))[0]), method="parser", note="")
    r.update(kw)
    frame = pd.DataFrame([r], columns=ci.COLUMNS)
    for c in ci.NUMERIC:
        frame[c] = pd.to_numeric(frame[c])
    return frame.iloc[0]


def test_r20_1_self_check_looks_in_the_tranches_column():
    lines = cc.lines(_keyed_sheet())
    _, parsed = ct.parse(lines, "2023-05-01")
    first = parsed[0]
    assert ci.locator(first).endswith("col #0")
    # a manual row for the 2028 Notes with the 2053 Notes' amount: the amount is in the block, not in column #0
    row = _csv_row(first, lines, principal=2500.0, method="manual", note="test")
    assert chk.check_row(row, lines) == ("manual", ["principal"])


def _supplement() -> str:
    return ("<P>Prospectus Supplement</P><P>$1,000,000,000</P><P>Example Corp.</P>"
            "<P>$1,000,000,000 4.000% Notes due 2031</P><P>FINAL PRICING TERMS</P><TABLE>"
            + _row("Principal Amount:", "$1,000,000,000") + _row("Maturity:", "June 1, 2031")
            + _row("Coupon:", "4.000%") + _row("Price to Public:", "99.500% of the principal amount")
            + _row("Trade Date:", "May 28, 2025") + "</TABLE>")


def test_r20_2_documents_not_coded_are_listed_with_a_reason():
    meta = [{"company": "orcl", "form": "424B2", "url": "u1", "accession": "0001193125-25-000001",
             "filed": "2025-05-28", "accepted": "2025-05-28T21:00:00.000Z"}]
    rows, skipped = ci.rows_from_documents(meta, fetch={"u1": cc.lines(_supplement())}.__getitem__)
    assert rows or [s["accession"] for s in skipped] == ["0001193125-25-000001"]


def test_r20_3_t_plus_n_skips_holidays():
    assert ct.add_business_days("2026-12-23", 2) == "2026-12-28"  # not Christmas Day


def test_r20_4_csv_writer_does_not_round(tmp_path, monkeypatch):
    monkeypatch.setattr(ci, "BLOCKS_DIR", tmp_path / "blocks")
    lines = cc.lines(_keyed_sheet())
    _, parsed = ct.parse(lines, "2023-05-01")
    r = _csv_row(parsed[0], lines).to_dict()
    r.update(currency="JPY", benchmark_type="other", principal=1234567.0, price_pct=99.12345)
    ci.write([r], tmp_path / "c.csv")
    back = ci.load(tmp_path / "c.csv").iloc[0]
    assert back["principal"] == 1234567.0 and back["price_pct"] == 99.12345


def test_r20_5_coverage_is_also_reported_per_quarter():
    rows = pd.DataFrame([{**{c: None for c in ci.COLUMNS}, "company": "orcl", "currency": "USD", "principal": 18000.0,
                          "pricing_date": "2025-09-24", "settlement_date": "2025-09-26"}])
    xb = pd.DataFrame({"period": ["2025Q3", "2025Q4"], "value": [100.0, 17880.0]})
    cov = ci.coverage(rows, {"orcl": xb})
    assert "quarter" in cov.columns
