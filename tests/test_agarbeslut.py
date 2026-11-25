"""Owner decisions 2026-11-25 (beslutsloggen): publish the capex guidance extracted from documents on sec.gov
(R11-4: Alphabet, Amazon, Meta; Microsoft's rows come from microsoft.com and stay withheld), with the public snapshot's
expectations section withheld per company, and Meta's and Alphabet's surprises published because they read only their
own rows. Synthetic fixtures and the committed curated CSV only, no network.
"""

from __future__ import annotations

import csv
import json
import math

import pandas as pd
import pytest

from ai_tracker import catalog, licenses
from ai_tracker.series import guidance_revisions as GR
from ai_tracker.sources import guidance_capex as GC
from ai_tracker.state import expectations as EX
from ai_tracker.state import snapshot as S
from tests.test_guidance_revisions import csv_rows, obs

WHEN = "2026-11-25"


@pytest.fixture(autouse=True)
def _index_from_2016(monkeypatch):
    monkeypatch.setattr(GR, "COVERAGE_FROM", pd.Period("2016Q1", "Q-DEC"))


def _catalog_publishable():
    specs = catalog.by_key()
    return lambda k: bool(k in specs and specs[k].publish)


# ------------------------------------------------------------------ the guid_capex_* series


def test_guidance_is_published_exactly_where_the_licence_class_is_ja():
    specs = catalog.by_key()
    keys = [k for k in specs if k.startswith("guid_capex_")]
    assert keys
    for k in keys:
        klass, _reason = licenses.classify(specs[k])
        assert specs[k].publish == (klass == licenses.JA), k
    by_company = {c: {specs[k].publish for k in keys if GR.csv_company(k) == c} for c in GC.COMPANIES}
    assert by_company == {"googl": {True}, "meta": {True}, "amzn": {True}, "msft": {False}}
    assert GC.SEC_HOSTS == licenses.SEC_HOSTS
    assert catalog.validate() == []


def test_the_curated_file_has_the_hosts_the_decision_rests_on():
    hosts = {}
    with open(GC.PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            hosts.setdefault(r["company"], set()).add(r["source_url"].split("/")[2])
    assert hosts["msft"] == {"www.microsoft.com"}
    assert all(hosts[c] == {"www.sec.gov"} for c in ("googl", "meta", "amzn"))


def _write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=GC.COLUMNS)
        w.writeheader()
        for i, (company, definition, url) in enumerate(rows):
            w.writerow({"id": f"r-{i}", "company": company, "horizon": "CY", "period": "2026",
                        "period_start": "2026-01-01", "period_end": "2026-12-31", "kind": "approx",
                        "value_lo": 100 + i, "value_hi": 100 + i, "unit": "MUSD", "direction_code": "",
                        "direction_base": "", "definition": definition, "filed": f"2026-0{i + 1}-15", "accepted": "",
                        "doc_type": "8-K", "source_url": url, "accession": "", "locator": "sentence #1",
                        "sentence_sha256": "0" * 64, "note": ""})


def test_one_row_from_another_host_withholds_that_company(tmp_path):
    p = tmp_path / "guidance_capex.csv"
    _write_csv(p, [("googl", "GOOGL_CAPEX", "https://www.sec.gov/Archives/a.htm"),
                   ("amzn", "AMZN_CASH_CAPEX", "https://www.sec.gov/Archives/b.htm"),
                   ("amzn", "AMZN_CAPEX_UNSPEC", "https://ir.example.com/c.htm"),
                   ("msft", "MSFT_CAPEX_INCL_FL", "https://www.microsoft.com/d")])
    assert GC.published_companies(GC.load(p)) == {"googl"}
    flags = {s.key: s.publish for s in GC.specs(p)}
    assert flags["guid_capex_googl_cy_lo"] and not flags["guid_capex_amzn_cy_lo"]
    assert not flags["guid_capex_msft_cy_lo"]


# ------------------------------------------------------------------ the F1 series that read the file


def test_company_surprises_list_only_their_company_and_are_published():
    specs = catalog.by_key()
    for key, reads in GR.CSV_READS.items():
        s = specs[key]
        gate = tuple(k for k in s.components if k.startswith("guid_capex_"))
        assert gate and {GR.csv_company(k) for k in gate} == set(reads), key
        assert s.components == GR.COMPONENTS + GR.csv_component_keys(reads)
        assert licenses.classify(s)[0] == licenses.JA
        # published unless the owner has yet to decide (the surprise index, R25-1): then withheld with that reason
        assert s.publish == (key not in GR.AWAITING_OWNER), key
        assert s.withheld_reason == GR.AWAITING_OWNER.get(key, ""), key
        assert licenses.CURATED_READS[key] == ("guidance_capex.csv", reads)  # the licence rule says the same
    assert set(GR.CSV_READS) == {"f1_surprise_meta_capex", "f1_surprise_googl_capex", "f1_surprise_index",
                                 "f1_surprise_index_n"}
    assert set(GR.AWAITING_OWNER) == {"f1_surprise_index", "f1_surprise_index_n"}


def test_series_that_pool_every_company_keep_microsoft_and_stay_withheld():
    specs = catalog.by_key()
    msft = set(GR.csv_component_keys(("msft",)))
    assert msft
    for key in set(GR.CSV_BASED) - set(GR.CSV_READS):
        assert msft <= set(specs[key].components) and not specs[key].publish, key


def _capex_world():
    """Meta and Alphabet outcomes and guidance 2019-2025 (two statements a year each), and Microsoft and Amazon rows
    that the company surprises must not read."""
    parts, rows = [], []
    for y in range(2019, 2026):
        q = [f"{y}Q{k}" for k in (1, 2, 3, 4)]
        kf = [f"{y}-04-25", f"{y}-07-31", f"{y}-10-30", f"{y + 1}-01-29"]
        parts += [obs("capex_meta", "Q", q, [10 + y - 2019 + k for k in range(4)], kf),
                  obs("fin_lease_meta", "Q", q, [0.5] * 4, kf),
                  obs("capex_googl", "Q", q, [20 + 2 * (y - 2019) + k for k in range(4)], kf)]
        d = y - 2019
        rows += [{"period": str(y), "lo": 40 + 4 * d, "hi": 46 + 4 * d, "filed": f"{y}-02-01"},
                 {"period": str(y), "lo": 44 + 4 * d, "hi": 48 + 4 * d, "filed": f"{y}-07-30"},
                 {"company": "googl", "period": str(y), "kind": "approx", "lo": 85 + 8 * d,
                  "definition": "GOOGL_CAPEX", "filed": f"{y}-02-04"},
                 {"company": "googl", "period": str(y), "kind": "approx", "lo": 90 + 8 * d + (y % 2),
                  "definition": "GOOGL_CAPEX", "filed": f"{y}-07-23"},
                 {"company": "amzn", "period": str(y), "kind": "approx", "lo": 60 + d,
                  "definition": "AMZN_CASH_CAPEX", "filed": f"{y}-02-03"},
                 {"company": "amzn", "period": str(y), "kind": "approx", "lo": 66 + d,
                  "definition": "AMZN_CASH_CAPEX", "filed": f"{y}-08-01"}]
        for i, f in enumerate(("01-29", "04-29", "07-29", "10-28")):
            rows.append({"company": "msft", "period": str(y), "kind": "approx", "lo": 150 + 10 * i + d,
                         "definition": "MSFT_CAPEX_INCL_FL", "filed": f"{y}-{f}"})
    # Nvidia (an SEC series in the table) gives the surprise index its second company
    nq = pd.period_range("2019Q1", "2025Q4", freq="Q-DEC")
    parts += [obs("nvda_guid_rev_mid", "Q", nq, [3000 * 1.04 ** i for i in range(len(nq))],
                  [p.start_time + pd.Timedelta(days=50) for p in nq]),
              obs("rev_nvda", "Q", nq, [3000 * 1.04 ** i * (1.02 + 0.01 * (i % 4)) for i in range(len(nq))],
                  [p.end_time.normalize() + pd.Timedelta(days=55) for p in nq])]
    return pd.concat(parts, ignore_index=True), csv_rows(rows)


def _others_changed(rows: pd.DataFrame, own: tuple[str, ...]) -> pd.DataFrame:
    """The same frame with every other company's values scaled and two more rows for other companies."""
    other = rows[~rows["company"].isin(own)].copy()
    other[["value_lo", "value_hi"]] *= 1.37
    extra = csv_rows([{"company": c, "period": "2024", "kind": "approx", "lo": 999, "definition": d,
                       "filed": "2024-12-01", "id": f"extra-{c}"}
                      for c, d in (("msft", "MSFT_CAPEX_INCL_FL"), ("googl", "GOOGL_CAPEX"),
                                   ("meta", "META_CAPEX_INCL_FL")) if c not in own])
    return pd.concat([rows[rows["company"].isin(own)], other, extra], ignore_index=True)


def _series(key, table, csv_frame):
    return GR._series(key, GR.compute(table, csv_frame, WHEN))  # the path of Spec.fetch (GR._fetch)


@pytest.mark.parametrize("key", sorted(GR.CSV_READS))
def test_a_company_surprise_does_not_change_with_another_company_rows(key):
    """The proof behind the narrowed components: if the series starts to read another company's rows (pooling,
    cross-company standardisation), this test fails."""
    table, rows = _capex_world()
    base = _series(key, table, rows)
    assert len(base) >= 1 and base["value"].notna().all()
    own = GR.CSV_READS[key]
    pd.testing.assert_frame_equal(base, _series(key, table, rows[rows["company"].isin(own)].reset_index(drop=True)))
    mixed = _others_changed(rows, own)
    pd.testing.assert_frame_equal(base, _series(key, table, mixed))
    # the perturbation is real: the pooled revision index does move
    assert not _series("f1_rev_median_4q", table, rows).equals(_series("f1_rev_median_4q", table, mixed))


# ------------------------------------------------------------------ the public snapshot section


MSFT_REASON = "the company put CY2026 at about 181818 on the new basis"


def _msft_section(monkeypatch):
    table, rows = _capex_world()
    msft = csv_rows([{"id": "m-1", "company": "msft", "kind": "approx", "lo": 191919, "definition": "MSFT_CAPEX_INCL_FL",
                      "period": "2026", "filed": "2026-04-29"},
                     {"id": "m-2", "company": "msft", "kind": "approx", "lo": 181818,
                      "definition": "MSFT_CAPEX_INCL_FL", "period": "2026", "filed": "2026-07-29"},
                     {"id": "m-3", "company": "msft", "kind": "approx", "lo": 171717,
                      "definition": "MSFT_CAPEX_INCL_FL", "period": "2026", "filed": "2026-10-28"}])
    monkeypatch.setattr(GR, "DEFINITION_BREAKS", {"m-2": MSFT_REASON})
    full = pd.concat([rows, msft], ignore_index=True)
    sec = EX.section(WHEN, table, full)
    return S._clean(sec), full


def _msft_figures(full) -> list[str]:
    """Every number that comes from Microsoft's rows: its values, its event and break sizes."""
    ev = GR.events(GR.statements(None, full))
    br = GR.break_statements(GR.statements(None, full))
    nums = list(full.loc[full["company"] == "msft", "value_lo"])
    nums += list(ev.loc[ev["company"] == "msft", "size"]) + list(ev.loc[ev["company"] == "msft", "prev_value"])
    nums += list(br.loc[br["company"] == "msft", "size"]) + list(br.loc[br["company"] == "msft", "prev_value"])
    return [json.dumps(float(x)) for x in nums if isinstance(x, float) and math.isfinite(x) and x not in (0.0,)]


def test_snapshot_shows_alphabet_amazon_meta_and_withholds_microsoft_and_the_aggregates(monkeypatch):
    sec, full = _msft_section(monkeypatch)
    assert any(b["company"] == "msft" for b in sec["break_statements"])  # the world has what is to be withheld
    assert any(e["company"] == "msft" for e in sec["events_recent"])
    out = EX.withhold(sec, _catalog_publishable())
    text, before = json.dumps(out, ensure_ascii=False), json.dumps(sec, ensure_ascii=False)
    figures = _msft_figures(full) + ["191919", "181818", "171717", MSFT_REASON]
    assert MSFT_REASON in before and sum(f in before for f in figures) >= 4  # the check is not vacuous
    for fig in figures:
        assert fig not in text, fig
    assert out["values_withheld"] == EX.WITHHELD_NOTE and out["values_withheld_companies"] == ["msft"]
    b = next(b for b in out["break_statements"] if b["company"] == "msft")
    assert not {"value", "prev_value", "size", "reason"} & set(b) and b["ref"] == "m-2"
    for e in out["events_recent"]:
        assert ("direction" in e) == (e["company"] != "msft"), e
    assert "msft" not in out["events_per_company_year"]
    assert {"meta", "googl", "amzn"} <= set(out["events_per_company_year"])
    shown = {c["company"]: c for c in out["surprise"]["companies"]}
    assert shown["meta"] == next(c for c in sec["surprise"]["companies"] if c["company"] == "meta")
    assert shown["googl"]["guidance"] is not None and shown["googl"]["surprise"] is not None
    # pooled over every company's rows, Microsoft's too: ids only
    for part in ("revisions", "revisions_numeric_only"):
        for entry in out[part].values():
            for k in ("latest", "latest_with_value"):
                assert entry[k] is None or set(entry[k]) <= {"period", "known_from", "companies"}
    assert set(out["composition_main_window"]) <= {"period"}
    for v in out["surprise"]["index"].values():
        assert v is None or set(v) <= {"period", "known_from", "companies"}
    assert sec["surprise"]["index"]["latest"] is not None  # there was an index to withhold


def test_a_company_is_public_only_with_its_own_surprise_and_the_index_only_with_its_series(monkeypatch):
    sec, _full = _msft_section(monkeypatch)
    pub = _catalog_publishable()
    no_meta = EX.withhold(sec, lambda k: pub(k) and k != "f1_surprise_meta_capex")
    assert no_meta["values_withheld_companies"] == ["meta", "msft"]
    assert set(next(c for c in no_meta["surprise"]["companies"] if c["company"] == "meta")) <= set(EX._SURPRISE_ID)
    assert not EX.company_public("tsmc", pub)  # not a CSV company: never decided here (from_csv keeps it shown)
    with_index = EX.withhold(sec, lambda k: pub(k) or k in EX.SURPRISE_INDEX_SERIES)
    assert with_index["surprise"]["index"] == sec["surprise"]["index"]
    assert with_index["revisions"] != sec["revisions"]  # the pooled index still holds Microsoft's rows


def test_nothing_publishable_withholds_every_csv_company_as_before(monkeypatch):
    sec, _full = _msft_section(monkeypatch)
    out = EX.withhold(sec, lambda k: False)
    assert out["values_withheld_companies"] == sorted(GC.COMPANIES)
    assert set(out["events_per_company_year"]) <= set(EX.TABLE_COMPANIES)
    assert EX.withhold(sec, lambda k: True) == sec
