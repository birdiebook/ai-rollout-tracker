"""Review R10 of the commercial-use class (track K2, ai_tracker.licenses): docs/granskning/r10_licensniva.md.

Strict xfail tests mark confirmed defects; they turn into XPASS (and fail) once the defect is fixed, so the marker must
then be removed. The other tests are guards for what the review checked and found correct. Synthetic specs and
fixtures, no network, no observation values.
"""

from __future__ import annotations

import csv
import inspect
import re
from urllib.parse import urlparse

import pandas as pd
import pytest

from ai_tracker import catalog, config, licenses as L
from ai_tracker.series import bea_nipa, census_trade, sec, tsmc

# Licence strings of run-13 series, copied verbatim from their branches (read with git show, 2026-11-24).
BLS_LICENSE = ("Public domain (BLS, www.bls.gov/opub/copyright-information.htm): \"You are free to use our public domain "
               "material without specific permission, although we do ask that you cite the Bureau of Labor Statistics "
               "as the source.\" Source: U.S. Bureau of Labor Statistics.")  # auto13/m1-makro series/bls.py
CENSUS_HS_LICENSE = ("US federal work, free under 17 U.S.C. § 105; the API's dataset metadata (imports/hs.json) gives "
                     "\"license\": \"http://creativecommons.org/publicdomain/zero/1.0/\". Census Data API Terms of "
                     "Service: services that use the API \"should display the following notice prominently\": \"This "
                     "product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau.\" "
                     "Source: U.S. Census Bureau, USA Trade, monthly imports by HS (api.census.gov).")  # m2 census_hs.py
USEFUL_LIVES_LICENSE = ("SEC EDGAR: public information (sec.gov/privacy). Bara extraherade siffror med källhänvisning "
                        "publiceras, aldrig text")  # auto13/p2a-nyttjandeperioder series/useful_lives.py
F1_LICENSE = ("SEC EDGAR: public information (sec.gov/privacy); egna kodade värden, bara siffror med "
              "källhänvisning")  # auto13/f1-revideringar series/guidance_revisions.py
F1_SOURCE = ("Härledd (F1) ur bolagens guidance: curated/fx.csv (granskad i R2), TSMC:s och Nvidias guidance i "
             "SEC-inlämningar, och utfall ur SEC EDGAR")  # F1's SOURCE with the fixture file in place of guidance_capex


def spec(key="zz_s", license="CC BY 4.0", source="test", **kw) -> catalog.Spec:
    return catalog.Spec(key=key, branch="G5", label=kw.pop("label", key), unit="x", freq="Q", source=source,
                        fetch=lambda: pd.Series(dtype=float), lag_days=10, license=license, **kw)


def klass_of(text: str) -> str | None:
    """Class of a licence text, None when no rule classifies it (validate then reports it: safe)."""
    try:
        return L.licence_verdict(text).klass
    except L.Unclassified:
        return None


@pytest.fixture
def curated(tmp_path, monkeypatch):
    """curated/fx.csv: company aaa only on sec.gov, company bbb partly on a company web page (as msft in
    guidance_capex.csv, whose 30 rows are all on www.microsoft.com)."""
    (tmp_path / "curated").mkdir()
    (tmp_path / "curated" / "fx.csv").write_text(
        "id,company,value,source_url\n"
        "a1,aaa,1,https://www.sec.gov/Archives/edgar/data/1/x.htm\n"
        "b1,bbb,2,https://www.example.com/investor/call.html\n", encoding="utf-8")
    monkeypatch.setattr(config, "REPO", tmp_path)
    return tmp_path


# ------------------------------------------------------------------ R10-1 (must_fix): curated file read outside the curated rule


@pytest.mark.xfail(strict=True, reason="R10-1: a source that names curated/<file>.csv but does not start with "
                                       "'Kurerad extraktion (' skips the curated rule; the SEC licence rule gives ja")
@pytest.mark.parametrize("source", [F1_SOURCE, "Curated extraction (curated/fx.csv): SEC EDGAR and company pages"])
def test_r10_1_series_reading_a_curated_file_gets_the_curated_rule(curated, source):
    # F1's pooled revision index reads every row of guidance_capex.csv, msft's too, and has no msft component.
    # Either fix is accepted: the curated rule also covers this source (class not ja), or validate refuses a series
    # that names a curated file without a component from it or a key override.
    s = spec("zz_rev_index_4q", license=F1_LICENSE, source=source)
    assert L.verdict(s, {}).klass != "ja" or any(e.startswith(s.key) for e in catalog.validate([s]))


def test_r10_1_guard_company_series_of_the_same_file_stay_ja(curated):
    # What a fix must keep: a company whose rows are all on sec.gov stays ja (today and after the fix).
    v = L.verdict(spec("kpi_aaa_x", license=F1_LICENSE, source="Kurerad extraktion (curated/fx.csv)"), {})
    assert v.klass == "ja"


# ------------------------------------------------------------------ R10-2 (must_fix): Arena price reads the Space files


ARENA_PRICE = ("g2_price_at_arena_capability", "g2_price_at_arena_capability_4o")


@pytest.mark.xfail(strict=True, reason="R10-2: the Arena price series read arena.subset_boards('text'), built from the "
                                       "Space files that make g1_arena_text_* okänd, but are ja (the arena-space "
                                       "override matches only the source 'LMArena (HF-dataset + Space-filer)')")
@pytest.mark.parametrize("key", ARENA_PRICE)
def test_r10_2_arena_price_on_space_boards_is_not_ja(key):
    from ai_tracker.series import arena_price
    from ai_tracker.sources import arena

    reads_space = 'subset_boards("text")' in inspect.getsource(arena_price) and bool(arena.PICKLE_TABLES["text"])
    # The defect is gone either way: the class is not ja, or the series no longer read the Space files.
    assert not reads_space or L.verdict(catalog.by_key()[key]).klass != "ja"


def test_r10_2_guard_arena_series_with_the_same_boards_are_okand():
    keys = catalog.by_key()
    assert {L.verdict(keys[k]).klass for k in ("g1_arena_text_top", "g1_arena_text_sc_top",
                                                "g1_arena_text_top_gap_ref")} == {"okänd"}
    assert L.verdict(keys["g1_arena_webdev_top"]).klass == "ja"  # webdev reads no Space tables


# ------------------------------------------------------------------ R10-3 (must_fix): restrictive words lose to a permissive token


ADVERSARIAL = [
    "CC BY 4.0 for the docs; the data is for non-commercial use only",
    "CC BY 4.0 (docs); data: noncommercial research use",
    "Creative Commons Attribution 4.0 for the text; data: all rights reserved",
    "MIT licence for the client; data proprietary, redistribution prohibited",
    "CC BY 4.0 / redistribution prohibited",
    "Licence: CC BY 4.0 (mirror), original: commercial use prohibited",
    "CC BY 4.0 does not cover the data",
    # GH Archive's string without its last sentence ("Not checked for publication."), which alone makes it okänd today
    "GH Archive: site and docs CC-BY-4.0; the event dataset \"includes material that may be subject to third party "
    "rights\"",
    "These series may be under copyright or in the public domain (FRED legal page)",
    "not in the public domain; licensed for personal use only",
    "Public domain status unclear",
    "17 U.S.C. § 105 does not apply (state agency data)",
    "CC BY 4.0 according to a third-party mirror; official terms not verified",
    "MIT Technology Review; terms not read",  # MIT as a name, not the licence
]


@pytest.mark.xfail(strict=True, reason="R10-3: RULES have no restrictive rule for non-commercial, all rights reserved, "
                                       "proprietary, prohibited, third party rights, hedged or negated public domain, "
                                       "'not verified'; the MIT rule matches the name MIT")
@pytest.mark.parametrize("text", ADVERSARIAL)
def test_r10_3_restrictive_wording_is_never_ja(text):
    assert klass_of(text) != "ja"


PROPOSED_RESTRICTIVE = re.compile(
    r"non-?commercial|all rights reserved|proprietary|third[- ]party rights|may be (?:under|subject to) copyright"
    r"|not in the public domain|not verified|personal use only|prohibit|not (?:permitted|allowed)"
    r"|does not (?:apply|cover)|\bunclear\b", re.IGNORECASE)


def test_r10_3_guard_catalog_strings_with_such_wording_are_not_ja():
    # The proposed rule (okänd, after pjm-republish and before the permissive rules) changes no current class: the
    # catalog strings with such wording (PJM, Manifold, GH Archive, Census M3 via ALFRED) are nej or okänd already.
    verdicts, _ = L.classify_all()
    hits = [s.key for s in catalog.ALL if PROPOSED_RESTRICTIVE.search(s.license)]
    assert hits and all(verdicts[k].klass != "ja" for k in hits)


def test_r10_3_guard_proposed_mit_pattern_keeps_litellm():
    # The proposed MIT pattern: MIT followed by a licence word, a comma or a parenthesis. LiteLLM keeps its MIT match.
    pattern = re.compile(r"(?<![\w-])MIT(?=[ -]?\(?(?i:licen[cs]e)|[,)])")
    litellm = [s.license for s in catalog.ALL if s.license.startswith("derived: LiteLLM")]
    assert litellm and all(pattern.search(t) for t in litellm)
    assert not pattern.search("MIT Technology Review; terms not read")


# ------------------------------------------------------------------ R10-4 (must_fix): a FRED copy is not caught


@pytest.mark.xfail(strict=True, reason="R10-4: SOURCE_OVERRIDES 'alfred' matches only ALFRED; a FRED copy is ja "
                                       "although the reason names ALFRED/FRED")
def test_r10_4_fred_copy_is_not_ja():
    s = spec("zz_fred", license="Public Domain: Citation Requested (FRED series tag)",
             source="FRED (fred.stlouisfed.org, fredgraph.csv) A34SNO")
    assert L.verdict(s, {}).klass == "okänd"


# ------------------------------------------------------------------ R10-5 (should_fix): the curated rule ignores Spec.license


@pytest.mark.xfail(strict=True, reason="R10-5: the curated rule replaces the licence rules instead of taking the most "
                                       "restrictive of the two")
@pytest.mark.parametrize("license", ["unverified: the exhibit's terms were not read", "CC BY-NC 4.0"])
def test_r10_5_curated_rule_respects_a_restrictive_licence(curated, license):
    v = L.verdict(spec("kpi_aaa_x", license=license, source="Kurerad extraktion (curated/fx.csv)"), {})
    assert v.klass != "ja"


# ------------------------------------------------------------------ R10-6 (should_fix): curated rule per company, not per series


def _ai_kpis_hosts() -> dict[str, set[str]]:
    from ai_tracker.sources import ai_kpis

    hosts: dict[str, set[str]] = {}
    with open(config.REPO / "curated" / "ai_kpis.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            hosts.setdefault(ai_kpis.series_key(row["definition"]), set()).add(urlparse(row["source_url"]).netloc)
    return hosts


@pytest.mark.xfail(strict=True, reason="R10-6: Microsoft KPI series whose own rows are all on sec.gov are okänd "
                                       "because other Microsoft rows come from microsoft.com")
def test_r10_6_msft_kpi_series_with_only_sec_rows_are_ja():
    hosts = _ai_kpis_hosts()
    verdicts, _ = L.classify_all()
    pure = [k for k, h in hosts.items() if "_msft_" in k and k in verdicts and h <= L.SEC_HOSTS]
    assert pure  # 7 on 2026-11-24: kpi_msft_azure_growth_{,cc_}v1-v3 and kpi_msft_azure_ai_pts_v2
    assert {verdicts[k].klass for k in pure} == {"ja"}


def test_r10_6_guard_msft_kpi_series_with_microsoft_com_rows_are_okand():
    hosts = _ai_kpis_hosts()
    verdicts, _ = L.classify_all()
    mixed = [k for k, h in hosts.items() if k in verdicts and not h <= L.SEC_HOSTS]
    assert mixed and {verdicts[k].klass for k in mixed} == {"okänd"}


# ------------------------------------------------------------------ R10-8 (note): class of an override is not checked


@pytest.mark.xfail(strict=True, reason="R10-8: validate does not check that an override's class is ja/nej/okänd")
def test_r10_8_validate_rejects_an_override_with_an_unknown_class(monkeypatch):
    monkeypatch.setitem(L.KEY_OVERRIDES, "zz_typo", ("okand", "typo"))
    assert any(e.startswith("zz_typo") for e in catalog.validate([spec("zz_typo")]))


# ------------------------------------------------------------------ guards: what R10 checked and found correct


def test_guard_rule_order_restrictive_before_permissive():
    names = [r.name for r in L.RULES]
    restrictive = [i for i, r in enumerate(L.RULES) if r.klass != L.JA]
    permissive = [i for i, r in enumerate(L.RULES) if r.klass == L.JA]
    assert max(restrictive) < min(permissive), names
    assert L.licence_verdict("PJM, no open licence. Non-members are specifically prohibited from republishing "
                             "data").klass == "nej"  # pjm before no-open-licence: nej, not okänd


@pytest.mark.parametrize("text", ["CC BY-SA 4.0", "CC BY-ND 4.0", "CC BY NC 4.0", "ODbL 1.0", "Apache-2.0",
                                  "Creative Commons Attribution-NonCommercial 4.0", "Copyright 2025 Foo Inc.",
                                  "commercial use prohibited", "License: see website"])
def test_guard_unknown_named_licences_are_unclassified_not_ja(text):
    # Unknown names give an error in validate, never ja: safe (too strict for CC BY-SA, which is a later choice).
    # After the R10-3 fix the two with restrictive words are okänd instead of unclassified; both are safe.
    k = klass_of(text)
    assert k != "ja"
    if k is None:
        assert any(e.startswith("zz_new") for e in catalog.validate([spec("zz_new", license=text)]))


@pytest.mark.parametrize("text,expected", [
    ("CC-BY-NC-SA-4.0", "nej"), ("CC BY-NC-ND 4.0", "nej"), ("derived: CC BY 4.0 + CC BY-NC 4.0", "nej"),
    ("derived: CC BY 4.0+unverified", "okänd"), ("no open licence; CC BY 4.0 for docs", "okänd"),
])
def test_guard_restrictive_named_licences_win(text, expected):
    assert klass_of(text) == expected


@pytest.mark.parametrize("text,expected", [
    (sec.LICENSE, "ja"),  # P1 depreciation and PP&E, P2b reconciliations (SEC XBRL)
    (bea_nipa.LICENSE, "ja"),  # M1 BEA release archive (same string)
    (BLS_LICENSE, "ja"),  # M1 BLS CPI/PPI
    (census_trade.LICENSE, "ja"),  # M2 Census end-use imports by country (same string as FT-900)
    (CENSUS_HS_LICENSE, "ja"),  # M2 Census API imports by HS
    (tsmc.LICENSE, "ja"),  # F1 TSMC capex guidance from 6-K
    (USEFUL_LIVES_LICENSE, "ja"), (F1_LICENSE, "ja"),
])
def test_guard_run13_licence_strings_classify(text, expected):
    assert L.licence_verdict(text).klass == expected
    assert catalog.validate([spec("zz_run13", license=text)]) == []


def test_guard_run13_curated_useful_lives_all_sec_rows_is_ja(tmp_path, monkeypatch):
    (tmp_path / "curated").mkdir()
    (tmp_path / "curated" / "useful_lives.csv").write_text(
        "id,company,source_url\nm1,msft,https://www.sec.gov/Archives/edgar/data/789019/a.htm\n"
        "g1,googl,https://www.sec.gov/Archives/edgar/data/1652044/b.htm\n", encoding="utf-8")
    monkeypatch.setattr(config, "REPO", tmp_path)
    s = spec("useful_life_servers_msft_lo", license=USEFUL_LIVES_LICENSE,
             source="Kurerad extraktion (curated/useful_lives.csv) ur 10-K/10-Q/8-K, SEC EDGAR")
    assert L.verdict(s, {}).klass == "ja"
    assert catalog.validate([s]) == []


def test_guard_hyp4_sums_resolve_every_member_in_their_label():
    keys = catalog.by_key()
    sums = [s for s in catalog.ALL if s.key.endswith("_hyp4")]
    assert sums
    for s in sums:
        members = L.MEMBERS.search(s.label)
        assert members, s.key
        assert len(L.components(s, keys)) == len(members.group(1).split("+")), s.key


def test_guard_publish_is_untouched_by_the_class():
    verdicts, _ = L.classify_all()
    assert any(s.publish and verdicts[s.key].klass == "nej" for s in catalog.ALL)  # Cloudflare on the site
    assert any(not s.publish and verdicts[s.key].klass == "ja" for s in catalog.ALL)
    assert catalog.validate([spec("zz_nc_pub", license="CC BY-NC 4.0", publish=True)]) == []
