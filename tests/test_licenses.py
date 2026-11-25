"""Commercial-use class per series (ai_tracker.licenses): rules, overrides, curated rule, derivation, validate, CLI.

Synthetic specs and fixtures, no network. The licence strings are the catalog's own constants, so a test fails if a
documented licence text changes class.
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

from ai_tracker import catalog, config, licenses as L
from ai_tracker.series import (bea_nipa, census_btos, census_c30, census_m3_alfred, census_trade, eia, eurostat_ai,
                               fed_g17, firstparty_prices, github_ai, indeed, npm, pjm, price_capability, sec, tsmc)
from ai_tracker.sources import aws_gpu
from ai_tracker.sources import cloudflare_radar as cf


def spec(key="s", license="CC BY 4.0", source="test", **kw) -> catalog.Spec:
    return catalog.Spec(key=key, branch="G6", label=kw.pop("label", key), unit="x", freq="M", source=source,
                        fetch=lambda: pd.Series(dtype=float), lag_days=10, license=license, **kw)


# ------------------------------------------------------------------ the real catalog


def test_every_catalog_series_is_classified():
    verdicts, errors = L.classify_all()
    assert errors == {}
    assert set(verdicts) == {s.key for s in catalog.ALL}
    assert {v.klass for v in verdicts.values()} <= set(L.CLASSES)
    assert all(v.reason.strip() for v in verdicts.values())
    assert catalog.validate() == []


def _classes(pattern: str) -> set[str]:
    verdicts, _ = L.classify_all()
    found = {verdicts[s.key].klass for s in catalog.ALL if re.search(pattern, s.source)}
    assert found, pattern  # the source is in the catalog
    return found


@pytest.mark.parametrize("pattern,expected", [
    (r"^SEC EDGAR XBRL", "ja"),  # sec.gov/privacy: public information
    (r"^SEC EDGAR, (TSMC|ASML|Nebius) Form 6-K", "ja"),  # our own figures from statutory filings
    (r"^SEC EDGAR, Nvidia Form 8-K", "ja"),
    (r"^Härledd \(A5\)", "ja"),  # reconciliations: all components SEC
    (r"^BEA NIPA", "ja"), (r"BTOS|C30|FT-900", "ja"),  # US government works (17 U.S.C. § 105)
    (r"^Federal Reserve G\.17", "ja"), (r"^EIA", "ja"),  # public domain
    (r"^Eurostat|^Indeed Hiring Lab|^PyPI|^Epoch AI|^METR", "ja"), (r"^SCB|^Wikimedia", "ja"),  # CC BY 4.0, CC0
    (r"^LiteLLM git-historik.*× Epoch", "ja"),  # MIT + CC BY 4.0
    (r"^Cloudflare Radar", "nej"),  # CC BY-NC 4.0
    (r"^PJM", "nej"),  # non-members may not republish
    (r"^Census M3 via ALFRED", "okänd"),  # FRED terms (machine learning), not assessed
    (r"^npm|^arXiv|^Manifold|^Polymarket|^SWE-bench", "okänd"),  # unverified
    (r"^AWS Price List|^GH Archive|anthropic\.com/news|Anthropics prissida", "okänd"),  # no open licence / not checked
    (r"^LMArena \(HF-dataset \+ Space-filer\)", "okänd"),
    (r"^LiteLLM git-historik.*× LMArena", "okänd"),  # the text boards come from the Space files (R10-2)
    (r"^SEC EDGAR, Anthropic", "ja"),  # the S-1 row of curated/lab_revenue.csv is on sec.gov
])
def test_known_sources_have_their_documented_class(pattern, expected):
    assert _classes(pattern) == {expected}


@pytest.mark.parametrize("text,expected", [
    (sec.LICENSE, "ja"), (tsmc.LICENSE, "ja"), (bea_nipa.LICENSE, "ja"), (census_btos.LICENSE, "ja"),
    (census_c30.LICENSE, "ja"), (census_trade.LICENSE, "ja"), (fed_g17.LICENSE, "ja"), (eia.LICENSE, "ja"),
    (eurostat_ai.LICENSE, "ja"), (indeed.LICENSE, "ja"), (price_capability.LICENSE, "ja"),
    (cf.LICENSE, "nej"), (pjm.LICENSE, "nej"),
    (npm.LICENSE, "okänd"), (aws_gpu.LICENSE, "okänd"), (firstparty_prices.LICENSE, "okänd"),
    (github_ai.LICENSE_A, "okänd"), (github_ai.LICENSE_B, "okänd"),
    # the text says public domain, but also FRED's "may be under copyright ... prohibited use" (R10-3); the ALFRED
    # copy is decided by the source override in any case
    (census_m3_alfred.LICENSE, "okänd"),
])
def test_licence_rules_on_the_catalog_constants(text, expected):
    assert L.licence_verdict(text).klass == expected


def test_publish_and_commercial_class_are_orthogonal():
    verdicts, _ = L.classify_all()
    cloudflare = [s for s in catalog.ALL if s.source.startswith("Cloudflare Radar")]
    assert any(s.publish for s in cloudflare) and all(verdicts[s.key].klass == "nej" for s in cloudflare)
    assert catalog.validate([spec("nc", license=cf.LICENSE, publish=True)]) == []
    hidden_ja = [s for s in catalog.ALL if not s.publish and verdicts[s.key].klass == "ja"]
    assert hidden_ja  # e.g. capex guidance before review: not shown, but commercially clean


# ------------------------------------------------------------------ rules and their order


@pytest.mark.parametrize("text,klass,rule", [
    ("unverified: terms not readable", "okänd", "unverified"), ("CC BY 4.0, but the copy is unverified", "okänd", "unverified"),
    ("CC BY-NC 4.0 (example)", "nej", "cc-by-nc"),
    ("site CC-BY-4.0; Not checked for publication.", "okänd", "no-open-licence"),  # not assessed beats CC BY
    ("no open licence. Non-members are specifically prohibited from republishing data", "nej", "pjm-republish"),
    ("CC0 1.0", "ja", "cc0"), ("CC BY 4.0 (README)", "ja", "cc-by"), ("MIT (LICENSE)", "ja", "mit"),
    ("US federal work, free under 17 U.S.C. § 105", "ja", "public-domain"), ("Public domain (agency)", "ja",
                                                                             "public-domain"),
    ("public: see sec.gov/privacy", "ja", "sec"),
    # R10-3: restrictive wording beats a permissive token, but not the nej rules before it
    ("CC BY 4.0 / redistribution prohibited", "okänd", "restrictive-wording"),
    ("all rights reserved", "okänd", "restrictive-wording"),
    ("MIT License", "ja", "mit"), ("Licence: MIT", "ja", "mit"), ("derived: A (MIT, file) + B (CC0)", "ja",
                                                                  "derived-licence"),
])
def test_rules_first_match_wins(text, klass, rule):
    v = L.licence_verdict(text)
    assert (v.klass, v.rule) == (klass, rule)


def test_mit_is_case_sensitive_and_unmatched_text_raises():
    with pytest.raises(L.Unclassified):
        L.licence_verdict("submit a request; permission required")
    with pytest.raises(L.Unclassified):
        L.licence_verdict("checked")
    for name in ("MIT Technology Review", "data from MIT CSAIL", "terms of MIT-IBM Watson AI Lab"):  # MIT as a name
        with pytest.raises(L.Unclassified):
            L.licence_verdict(name)


def test_derived_licence_takes_the_most_restrictive_part():
    assert L.licence_verdict("derived: A (MIT) + B (CC BY 4.0)").klass == "ja"
    v = L.licence_verdict("derived: A (MIT) + B (no data licence stated)")
    assert v.klass == "okänd" and v.rule == "derived-licence" and "A ja" in v.reason
    assert L.licence_verdict("derived: A (CC BY 4.0) + B (CC BY-NC 4.0) + C (unverified)").klass == "nej"
    with pytest.raises(L.Unclassified):
        L.licence_verdict("derived: A (MIT) + B (terms on the website)")
    assert L.licence_verdict("derived: A (MIT) + B (all rights reserved)").klass == "okänd"


def test_unmatched_licence_is_a_validate_error():
    errors = catalog.validate([spec("zz_new", license="terms on the website")])
    assert any(e.startswith("zz_new: licence not classified") for e in errors)
    with pytest.raises(L.Unclassified):
        L.classify(spec("zz_new", license="terms on the website"))
    # an empty licence is reported once, as missing
    assert [e for e in catalog.validate([spec("zz_empty", license="")]) if "zz_empty" in e] == [
        "zz_empty: licence missing (write 'unverified' until checked)"]


# ------------------------------------------------------------------ overrides


def test_key_override_is_final(monkeypatch):
    monkeypatch.setitem(L.KEY_OVERRIDES, "zz_k", ("nej", "test override"))
    assert L.classify(spec("zz_k", license="CC0")) == ("nej", "test override")
    # also an unmatched licence, and a derived series
    assert L.classify(spec("zz_k", license="terms on the website", components=("x",))) == ("nej", "test override")


def test_key_override_with_an_unknown_class_is_an_error(monkeypatch):
    monkeypatch.setitem(L.KEY_OVERRIDES, "zz_typo", ("okand", "typo"))
    with pytest.raises(L.Unclassified, match="okand"):
        L.verdict(spec("zz_typo"))
    assert all(k in L.CLASSES for k, _ in L.KEY_OVERRIDES.values() if k != "okand")
    assert {r.klass for r in L.RULES + L.SOURCE_OVERRIDES} <= set(L.CLASSES)


def test_arena_price_series_are_overridden_by_key():
    from ai_tracker.series import arena_price

    for key in arena_price.KEYS.values():  # follows a rename of the keys
        assert L.verdict(catalog.by_key()[key]).rule == "key-override"
        assert L.KEY_OVERRIDES[key][0] == "okänd"


def test_source_override_beats_the_licence_text():
    v = L.verdict(spec("zz_m3", license=census_m3_alfred.LICENSE, source="Census M3 via ALFRED (X)"))
    assert (v.klass, v.rule) == ("okänd", "alfred")
    assert L.verdict(spec("zz_bea", license=bea_nipa.LICENSE, source="BEA NIPA flat file")).klass == "ja"
    assert L.verdict(spec("zz_ar", source="LMArena (HF-dataset + Space-filer)")).rule == "arena-space"
    assert L.verdict(spec("zz_ar2", source="LMArena (HF-dataset)")).klass == "ja"
    # R10-4: a FRED copy too, by the acronym or the host; a word that only contains the letters does not match
    for source in ("FRED (fred.stlouisfed.org, fredgraph.csv) A34SNO", "St. Louis Fed, api.stlouisfed.org"):
        v = L.verdict(spec("zz_fred", license="Public Domain: Citation Requested", source=source))
        assert (v.klass, v.rule) == ("okänd", "alfred")
    assert L.verdict(spec("zz_alf", license="CC0", source="Alfred's survey (Frederick County)")).klass == "ja"


# ------------------------------------------------------------------ curated extractions


@pytest.fixture
def curated(tmp_path, monkeypatch):
    (tmp_path / "curated").mkdir()
    (tmp_path / "curated" / "fx.csv").write_text(
        "id,company,value,source_url\n"
        "a1,aaa,1,https://www.sec.gov/Archives/edgar/data/1/x.htm\n"
        "a2,aaa,2,https://www.sec.gov/Archives/edgar/data/1/y.htm\n"
        "b1,bbb,3,https://www.sec.gov/Archives/edgar/data/2/x.htm\n"
        "b2,bbb,4,https://www.example.com/investor/call.html\n", encoding="utf-8")
    monkeypatch.setattr(config, "REPO", tmp_path)
    return "Kurerad extraktion (curated/fx.csv): SEC EDGAR och bolagens sidor"


def test_curated_is_ja_only_when_every_row_of_the_company_is_on_sec_gov(curated):
    lic = "SEC EDGAR: public information (sec.gov/privacy); company pages: figures only"
    v = L.verdict(spec("kpi_aaa_users", license=lic, source=curated))
    assert (v.klass, v.rule, v.scope) == ("ja", "curated", "aaa")
    assert L.classify(spec("kpi_aaa_users", license=lic, source=curated))[1].endswith("(bolag: aaa)")
    v = L.verdict(spec("kpi_bbb_users", license=lic, source=curated))
    assert v.klass == "okänd" and "www.example.com" in v.reason
    # no company token in the key: every row of the file counts
    assert L.verdict(spec("kpi_total", license=lic, source=curated)).klass == "okänd"
    # the file is missing: the rows cannot be checked
    v = L.verdict(spec("kpi_aaa_x", license=lic, source="Kurerad extraktion (curated/missing.csv)"))
    assert v.klass == "okänd" and "saknas" in v.reason


def test_curated_rule_on_the_real_files():
    verdicts, _ = L.classify_all()
    msft = [s.key for s in catalog.ALL if s.source.startswith("Kurerad extraktion (curated/ai_kpis.csv)")
            and "_msft_" in s.key]
    # per series since R10-6: a Microsoft KPI is ja when its own rows are all on sec.gov, okänd when some are from
    # microsoft.com
    assert msft and {verdicts[k].klass for k in msft} == {"ja", "okänd"}
    assert {verdicts[k].scope for k in msft} == {"msft"}
    assert all("seriens" in verdicts[k].reason for k in msft)
    for name in ("guidance_capex", "plans"):  # no row mapping: by company, and all Microsoft rows are microsoft.com
        keys = [s.key for s in catalog.ALL if s.source.startswith(f"Kurerad extraktion (curated/{name}.csv)")
                and verdicts[s.key].scope == "msft"]
        assert keys and {verdicts[k].klass for k in keys} == {"okänd"}, name
    lease = [s.key for s in catalog.ALL if s.source.startswith("Kurerad extraktion (curated/lease_commitments.csv)")]
    assert lease and {verdicts[k].klass for k in lease} == {"ja"}  # every row from 10-Q/10-K on sec.gov


def test_series_naming_a_curated_file_must_declare_its_rows(curated, monkeypatch):
    lic = "SEC EDGAR: public information (sec.gov/privacy)"
    s = spec("zz_pooled", license=lic, source="Härledd ur bolagens guidance: curated/fx.csv och SEC EDGAR")
    v = L.verdict(s, {})
    assert (v.klass, v.rule) == ("okänd", "curated-undeclared")  # R10-1: never ja through the licence text
    assert L.undeclared_curated(s) == ["fx.csv"]
    assert any(e.startswith("zz_pooled: source names curated/fx.csv") for e in catalog.validate([s]))
    # declared: every row (pooled over companies), some companies' rows, or no row
    monkeypatch.setitem(L.CURATED_READS, "zz_pooled", ("fx.csv", None))
    v = L.verdict(s, {})
    assert (v.klass, v.rule, v.scope) == ("okänd", "curated-reads", "alla bolag") and "www.example.com" in v.reason
    assert catalog.validate([s]) == []
    monkeypatch.setitem(L.CURATED_READS, "zz_pooled", ("fx.csv", ("aaa",)))
    assert (L.verdict(s, {}).klass, L.verdict(s, {}).scope) == ("ja", "aaa")
    monkeypatch.setitem(L.CURATED_READS, "zz_pooled", ("fx.csv", ()))
    assert L.verdict(s, {}).rule == "sec"  # reads no row: the licence decides
    monkeypatch.setitem(L.CURATED_READS, "zz_pooled", ("fx.csv", ("zzz",)))  # a company with no rows
    assert L.verdict(s, {}).klass == "okänd"
    monkeypatch.setitem(L.CURATED_READS, "zz_pooled", ("other.csv", None))  # declared for another file
    assert L.verdict(s, {}).rule == "curated-undeclared"
    # a key override is final, and then nothing needs declaring
    monkeypatch.delitem(L.CURATED_READS, "zz_pooled")
    monkeypatch.setitem(L.KEY_OVERRIDES, "zz_pooled", ("okänd", "test"))
    assert L.undeclared_curated(s) == [] and catalog.validate([s]) == []
    # every file named counts: a curated extraction that also names another file must declare that one too
    s2 = spec("kpi_aaa_x", license=lic, source="Kurerad extraktion (curated/fx.csv), jämförd med curated/gx.csv")
    assert L.undeclared_curated(s2) == ["gx.csv"] and L.verdict(s2, {}).klass == "okänd"


def test_row_series_follows_the_rows_of_the_series(tmp_path, monkeypatch):
    (tmp_path / "curated").mkdir()
    (tmp_path / "curated" / "lab_revenue.csv").write_text(
        "id,lab,scope,measure,value,source_url\n"
        "a1,lab1,company,RUN_RATE,1,https://www.lab1.example/news/a\n"
        "a2,lab1,company,RUN_RATE_S1,2,https://www.sec.gov/Archives/edgar/data/1/a.htm\n", encoding="utf-8")
    monkeypatch.setattr(config, "REPO", tmp_path)
    lic = "SEC EDGAR: public information (sec.gov/privacy)"
    src = "Nyhetsrum, kurerad extraktion i curated/lab_revenue.csv"
    v = L.verdict(spec("lab_rev_lab1_company_run_rate_s1", license=lic, source=src), {})
    assert (v.klass, v.rule, v.scope) == ("ja", "curated", "lab1")  # same lab, but only its own row counts
    v = L.verdict(spec("lab_rev_lab1_company_run_rate", license=lic, source=src), {})
    assert v.klass == "okänd" and "kommer från www.lab1.example" in v.reason  # no "också": no sec.gov row
    assert L.verdict(spec("lab_rev_lab1_other", license=lic, source=src), {}).rule == "curated-undeclared"


def test_curated_reads_name_real_files_and_companies():
    assert L.CURATED_READS
    for key, (name, companies) in L.CURATED_READS.items():
        path = config.REPO / "curated" / name
        assert path.exists(), key
        present = {r[0] for r in L._curated_rows(str(path), path.stat().st_mtime)}
        assert set(companies or ()) <= present, key


def test_f1_series_get_the_curated_rule_on_the_rows_they_read():
    # F1's source and licence (auto13/f1-revideringar series/guidance_revisions.py), on the real guidance_capex.csv:
    # the pooled revision series read Microsoft's rows from microsoft.com (R10-1); the surprises do not
    source = ("Härledd (F1) ur bolagens guidance: curated/guidance_capex.csv (granskad i R2), TSMC:s och Nvidias "
              "guidance i SEC-inlämningar, och utfall ur SEC EDGAR")
    lic = "SEC EDGAR: public information (sec.gov/privacy); egna kodade värden, bara siffror med källhänvisning"
    classes = {k: L.verdict(spec(k, license=lic, source=source), {}).klass for k in L.CURATED_READS}
    assert {k for k, c in classes.items() if c != "ja"} == {"f1_rev_index_4q", "f1_rev_index_q", "f1_rev_n_4q",
                                                            "f1_rev_n_q", "f1_rev_median_4q", "f1_rev_median_q"}
    assert set(classes.values()) == {"ja", "okänd"}


# ------------------------------------------------------------------ derivation


def test_derived_series_take_the_most_restrictive_component():
    a, b, c = spec("zz_a"), spec("zz_b", license="CC BY-NC 4.0"), spec("zz_c", license="unverified: x")
    specs = {s.key: s for s in (a, b, c)}

    def cls(comps, own="CC BY 4.0"):
        d = spec("zz_d", license=own, components=comps)
        return L.classify(d, {**specs, d.key: d})[0]

    assert cls(("zz_a",)) == "ja"
    assert cls(("zz_a", "zz_c")) == "okänd"
    assert cls(("zz_a", "zz_c", "zz_b")) == "nej"  # nej before okänd
    assert cls(("zz_a",), own="unverified") == "okänd"  # its own licence counts too
    assert cls(("zz_missing",)) == "okänd"
    d = spec("zz_d", components=("zz_b",))
    v = L.verdict(d, {**specs, d.key: d})
    assert v.rule == "derived" and "zz_b" in v.reason


def test_derivation_is_transitive_and_cycle_safe():
    a = spec("zz_a", license="CC BY-NC 4.0")
    b = spec("zz_b", components=("zz_a",))
    c = spec("zz_c", components=("zz_b",))
    loop1, loop2 = spec("zz_l1", components=("zz_l2",)), spec("zz_l2", components=("zz_l1",))
    specs = {s.key: s for s in (a, b, c, loop1, loop2)}
    assert L.classify(c, specs)[0] == "nej"
    assert L.classify(loop1, specs)[0] == "ja"


def test_hyp4_sums_take_their_members():
    members = {k: spec(k, license=lic) for k, lic in (("zz_capex_msft", "CC0"), ("zz_capex_googl", "CC0"),
                                                       ("zz_capex_amzn", "unverified"))}
    total = spec("zz_capex_hyp4", label="Capex, MSFT+GOOGL+AMZN+META", license="CC0")
    keys = {**members, total.key: total}
    assert L.components(total, keys) == ("zz_capex_msft", "zz_capex_googl", "zz_capex_amzn")  # META not in keys
    assert L.classify(total, keys)[0] == "okänd"
    real = catalog.by_key()
    assert set(L.components(real["capex_hyp4"], real)) == {"capex_msft", "capex_googl", "capex_amzn", "capex_meta"}
    assert set(L.components(real["rpo_hyp4"], real)) == {"rpo_msft", "rpo_googl", "rpo_amzn", "rpo_orcl"}


# ------------------------------------------------------------------ core entries and the clean subset


def test_entry_keys_resolve_placeholders_and_state_ratios():
    keys = {k: spec(k) for k in ("btos_ai_use_v1", "btos_ai_use_v3", "btos_ai_use_v3_se",
                                 "g1_epoch_bench_frontier_x", "g1_epoch_bench_frontier_y")}
    assert L.entry_keys("btos_ai_use_<aktiv regim>", keys) == ["btos_ai_use_v1", "btos_ai_use_v3"]
    assert L.entry_keys("g1_epoch_bench_frontier_<valda>", keys) == ["g1_epoch_bench_frontier_x",
                                                                    "g1_epoch_bench_frontier_y"]
    assert L.entry_keys("capex_ocf_hyp4", keys) == ["capex_hyp4", "ocf_hyp4"]
    assert L.entry_verdict("not_in_catalog", keys).klass == "okänd"


def test_core_summary_counts_add_up():
    from ai_tracker.state import register as R

    rows = L.core_summary()
    assert [r["branch"] for r in rows] == list(catalog.BRANCHES)
    for r in rows:
        assert r["entries"] == len(R.core_entries(r["branch"])) == r["ja"] + r["nej"] + r["okänd"]
        assert 0 <= r["families_ja"] <= r["families"] <= r["entries"]
        assert set(r["not_ja"]) <= set(R.core_entries(r["branch"]))
    by = {r["branch"]: r for r in rows}
    assert by["G8"]["families"] == 1  # nine Indeed countries are one source family
    assert {e for e in by["G7"]["not_ja"]} == {"pjm_lf_peak_dom_h5", "pjm_lf_peak_rto_h5"}


def test_core_summary_uses_the_register_families():
    # R10-12: K2's provisional reading is gone now that K1's register.entry_families is merged
    from ai_tracker.state import register as R

    assert not hasattr(L, "PROVISIONAL_FAMILIES")
    for r in L.core_summary():
        fams = R.entry_families(r["branch"])
        assert r["reading"] == "register"
        assert r["families"] == len({fams.get(e, e) for e in R.core_entries(r["branch"])})


# ------------------------------------------------------------------ CLI


def test_cli_report(capsys):
    assert L.main(["report"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Kommersiell användning,") and "Kärnposter" in out
    assert L.main(["report", "--markdown"]) == 0
    md = capsys.readouterr().out
    for heading in ("### Regler i ordning", "### Klass per källa", "### Antal per gren",
                    "### Kommersiellt ren delmängd: kärnposter"):
        assert heading in md
    assert "[kallor/sec.md](../kallor/sec.md)" in md


def test_report_flags_unclassified_series():
    text, n = L.report(specs=[spec("zz_new", license="terms on the website")])
    assert n == 1 and "EJ KLASSAD zz_new" in text


def test_every_source_group_in_the_catalog_links_a_doc_that_exists():
    """Integration of run 14: the KR1 and CN1 sources had no group, so the licence table showed them without a link to
    the doc that quotes the licence text. Every catalog source now falls in a listed group with an existing doc."""
    missing, absent = set(), set()
    for spec in catalog.by_key().values():
        name, doc = L.source_group(spec.source)
        if not doc:
            missing.add(name)
        elif not (config.REPO / "docs" / doc).exists():
            absent.add(doc)
    assert not missing, f"source groups without a doc: {sorted(missing)}"
    assert not absent, f"docs that do not exist: {sorted(absent)}"


def test_kl1_sources_fall_in_the_kreditlagret_groups():
    """Integration of KL1 (run 15): its 52 derived series ('Härledd (KL1) ...') and the CoreWeave coupon series
    (curated/kreditlagret.csv) each link the KL1 source doc, and no other catalog series falls in those groups."""
    groups = {"Kurerad extraktion: kreditlagret", "KL1: kreditlagret (härledda)"}
    hits = {}
    for spec in catalog.by_key().values():
        name, doc = L.source_group(spec.source)
        if name in groups:
            hits[spec.key] = (name, doc)
    assert hits and all(k.startswith("kl_") for k in hits)
    assert {k for k in catalog.by_key() if k.startswith("kl_")} == set(hits)
    assert {doc for _, doc in hits.values()} == {"kallor/kreditlagret.md"}
    assert hits["kl_coupon_out_crwv_q"][0] == "Kurerad extraktion: kreditlagret"
    assert hits["kl_capex4_orcl"][0] == "KL1: kreditlagret (härledda)"
