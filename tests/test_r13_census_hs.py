"""Review R13 of track M2 (Census imports by country): docs/granskning/r13_census_hs.md.

Passing tests pin the properties that hold (missing key, key hygiene, dating, request shape). The tests of the
confirmed defects R13-1 ... R13-5 were strict xfail; fix track X10 (auto14/x10-census-hs) corrected them, so they are
ordinary tests now.
Synthetic fixtures, no network. The dates and the observed redirect targets were read from census.gov and
api.census.gov on 2026-11-24 (see the review doc).
"""

from __future__ import annotations

import hashlib
import traceback
from datetime import date

import pandas as pd
import pytest
import requests

from ai_tracker import catalog, config, keyed, observations, warehouse
from ai_tracker.series import census_enduse as eu_series
from ai_tracker.series import census_hs as hs_series
from ai_tracker.sources import census_hs

SECRET = "r" * 40
HS_KEYS = [s.key for s in hs_series.SPECS]
DOC = config.REPO / "docs" / "kallor" / "census_hs.md"

# FT-900 Annual Revision for data year Y: "FOR RELEASE" date on final_Y.pdf (all ten years read 2026-11-24)
ANNUAL_REVISION = {2016: "2017-06-02", 2017: "2018-06-06", 2018: "2019-06-06", 2019: "2020-06-04",
                   2020: "2021-06-08", 2021: "2022-06-07", 2022: "2023-06-07", 2023: "2024-06-06",
                   2024: "2025-06-05", 2025: "2026-06-09"}


class Fake:
    def __init__(self, status=200, payload=None, location=""):
        self.status_code, self._payload = status, payload
        self.headers = {"Location": location} if location else {}
        self.is_redirect = status in (301, 302, 303, 307, 308)
        self.ok = status < 400
        self.text = "" if payload is None else str(payload)
        self.content = self.text.encode()

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _months(start, end):
    return [str(p) for p in pd.period_range(start, end, freq="M")]


def api_rows(params, end_named="2026-09", end_world="2026-09", start="2026-05"):
    """The API's JSON rows for one request (shape as in the Guide to International Trade Datasets)."""
    p: dict[str, list[str]] = {}
    for k, v in params:
        p.setdefault(k, []).append(v)
    if "CTY_CODE" in p:
        rows = [["CTY_CODE", "CTY_NAME", "I_COMMODITY", "GEN_VAL_MO", "CTY_CODE", "I_COMMODITY", "time"]]
        rows += [[c, "X", code, "1000000000", c, code, m] for c in p["CTY_CODE"] for code in p["I_COMMODITY"]
                 for m in _months(start, end_named)]
    else:
        rows = [["I_COMMODITY", "GEN_VAL_MO", "I_COMMODITY", "time"]]
        rows += [[code, "9000000000", code, m] for code in p["I_COMMODITY"] for m in _months(start, end_world)]
    return rows


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Isolated table, raw dir and request stub; `key(value)` sets or unsets CENSUS_API_KEY for keyed.py."""
    monkeypatch.setattr(observations, "PATH", tmp_path / "observations.parquet")
    monkeypatch.setattr(census_hs.http, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(census_hs.time, "sleep", lambda s: None)
    monkeypatch.setattr(census_hs, "_CACHE", {})
    real = config.get
    state = {"key": None, "calls": [], "respond": lambda params: Fake(200, api_rows(params))}

    def get(name, default=None):
        return state["key"] if name == "CENSUS_API_KEY" else real(name, default)

    def fake_get(url, params=None, **kw):
        state["calls"].append(params)
        r = state["respond"](params)
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(keyed.config, "get", get)
    monkeypatch.setattr(census_hs.requests, "get", fake_get)
    return state


def _today(monkeypatch, day: date):
    class D(date):
        @classmethod
        def today(cls):
            return day
    monkeypatch.setattr(observations, "date", D)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


# ------------------------------------------------------------------ 1. missing key (holds)


def test_skipped_refresh_leaves_table_and_fetch_log_byte_identical(env, monkeypatch, tmp_path):
    plain = catalog.Spec(key="plain_m", branch="G6", label="p", unit="x", freq="M", source="test",
                         fetch=lambda: pd.Series([1.0], index=pd.period_range("2026-09", periods=1, freq="M")),
                         lag_days=10, license="unverified")
    observations.upsert(plain, plain.fetch(), fetched_at=date(2026, 11, 2))
    table, log = observations.PATH, observations.log_path()
    before = (_sha(table), _sha(log))
    monkeypatch.setattr(catalog, "ALL", [*hs_series.SPECS])
    status = observations.refresh()
    assert {v.split(":")[0] for v in status.values()} == {"SKIPPED"} and len(status) == 35
    assert (_sha(table), _sha(log)) == before and env["calls"] == []


def test_skipped_run_does_not_push_known_from_of_the_first_keyed_fetch(env, monkeypatch):
    spec = catalog.by_key()["us_imp_hs8471_tw_m"]
    monkeypatch.setattr(catalog, "ALL", [spec])
    _today(monkeypatch, date(2026, 11, 15))  # after 2026-09's release (2026-11-10 by the FT-900 rule)
    assert observations.refresh()[spec.key].startswith("SKIPPED")
    env["key"] = SECRET
    _today(monkeypatch, date(2026, 11, 24))
    assert observations.refresh()[spec.key] == "ok +5"
    kf = observations.load().set_index("period")["known_from"]
    assert kf["2026-09"] == pd.Timestamp("2026-11-10")  # the lag rule, not the day after the skipped run
    # counterfactual: had the skipped run been logged as a fetch without 2026-09, the period would move to 11-16
    log = pd.DataFrame({"series": [spec.key], "fetched_at": [pd.Timestamp("2026-11-15")], "n_periods": [4],
                        "last_period": ["2026-08"], "rows_added": [0]})
    s = pd.Series([1.0], index=pd.period_range("2026-09", periods=1, freq="M"))
    other = observations.new_rows(catalog.by_key(hs_series.SPECS)["us_imp_hs8471_mx_m"], s, observations._empty(),
                                  date(2026, 11, 24), log.assign(series="us_imp_hs8471_mx_m"))
    assert other["known_from"].iloc[0] == pd.Timestamp("2026-11-16")


def test_freshness_exempts_only_series_whose_registered_key_is_unset(monkeypatch):
    con = warehouse.connect(observations._empty())  # whole catalog, no rows at all
    real = config.get
    monkeypatch.setattr(keyed.config, "get", lambda n, d=None: None if n == "CENSUS_API_KEY" else real(n, d))
    stale = set(warehouse.fresh(con, "2026-11-24")["series"])
    assert not stale & set(HS_KEYS)
    assert {s.key for s in eu_series.SPECS} <= stale  # the keyless annual series are still checked
    assert set(keyed.REQUIRES) == set(HS_KEYS)  # nothing else is registered behind a key
    monkeypatch.setattr(keyed.config, "get", lambda n, d=None: SECRET if n == "CENSUS_API_KEY" else real(n, d))
    assert set(HS_KEYS) <= set(warehouse.fresh(con, "2026-11-24")["series"])


def test_key_set_but_refused_is_failed_and_stale_not_skipped(env, monkeypatch):
    env["key"] = SECRET
    env["respond"] = lambda params: Fake(302, location="https://api.census.gov/data/invalid_key.html")
    monkeypatch.setattr(catalog, "ALL", [catalog.by_key()["us_imp_hs8542_cn_m"]])
    status = observations.refresh()["us_imp_hs8542_cn_m"]
    assert status.startswith("FAILED") and "invalid_key.html" in status and SECRET not in status
    assert observations.load().empty and observations.load_log().empty
    stale = warehouse.fresh(warehouse.connect(observations.load(), catalog.ALL), "2026-11-24")
    assert list(stale["series"]) == ["us_imp_hs8542_cn_m"]  # the weekly job goes red, visibly


def test_empty_response_is_failed_without_a_fetch_log_row(env, monkeypatch):
    env["key"] = SECRET
    env["respond"] = lambda params: Fake(204)
    monkeypatch.setattr(catalog, "ALL", [catalog.by_key()["us_imp_hs8471_world_m"]])
    assert observations.refresh()["us_imp_hs8471_world_m"].startswith("FAILED")
    assert observations.load_log().empty


# ------------------------------------------------------------------ 2. key hygiene (holds)


@pytest.mark.parametrize("location", ["https://api.census.gov/data/invalid_key.html",
                                      "https://api.census.gov/data/missing_key.html"])
def test_observed_redirect_targets_name_the_page_not_the_key(env, location):
    env["respond"] = lambda params: Fake(302, location=location)
    with pytest.raises(RuntimeError) as exc:
        census_hs.request(census_hs.params(("8471",)), SECRET)
    assert location.rsplit("/", 1)[-1] in str(exc.value) and SECRET not in str(exc.value)


def test_connection_error_with_the_key_in_its_url_is_not_in_status_or_traceback(env, monkeypatch, capsys):
    env["key"] = SECRET
    env["respond"] = lambda params: requests.ConnectionError(
        f"HTTPSConnectionPool(host='api.census.gov', port=443): Max retries exceeded with url: "
        f"/data/timeseries/intltrade/imports/hs?get=GEN_VAL_MO&key={SECRET}")
    with pytest.raises(RuntimeError) as exc:
        census_hs.request(census_hs.params(("8471",)), SECRET)
    assert SECRET not in "".join(traceback.format_exception(exc.value))  # context suppressed (from None)
    monkeypatch.setattr(catalog, "ALL", [catalog.by_key()["us_imp_hs8471_tw_m"]])
    status = observations.refresh()["us_imp_hs8471_tw_m"]
    assert status.startswith("FAILED") and SECRET not in status and SECRET not in capsys.readouterr().out


def test_raw_copies_never_carry_the_key(env, tmp_path):
    env["key"] = SECRET
    census_hs.fetch("5830", "8471", hs_series.COMMODITIES, hs_series.COUNTRIES)
    saved = list((tmp_path / "raw").rglob("*"))
    assert len([p for p in saved if p.is_file()]) == 2
    assert all(SECRET not in str(p) and SECRET.encode() not in (p.read_bytes() if p.is_file() else b"")
               for p in saved)
    assert all(("key", SECRET) in p for p in env["calls"])  # the key travels only in the request


# ------------------------------------------------------------------ 3. annual file dating (holds)


def test_annual_known_from_is_after_every_verified_annual_revision():
    spec = catalog.by_key()["us_imp_eu21320_my_a"]
    s = pd.Series(1.0, index=pd.period_range("2016", "2025", freq="Y-DEC"))
    rows = observations.new_rows(spec, s, observations._empty(), date(2026, 11, 24))
    kf = dict(zip(rows["period"].astype(int), rows["known_from"]))
    for year, release in ANNUAL_REVISION.items():
        margin = (kf[year] - pd.Timestamp(release)).days
        assert 30 <= margin <= 38, (year, margin)


# ------------------------------------------------------------------ 4. request shape (holds)


def test_request_shape_follows_the_guide():
    named = census_hs.params(hs_series.COMMODITIES, hs_series.COUNTRIES)
    world = census_hs.params(hs_series.COMMODITIES)
    assert [v for k, v in named if k == "CTY_CODE"] == ["5830", "2010", "5520", "5570", "5490", "5700"]
    assert [v for k, v in named if k == "I_COMMODITY"] == ["8471", "847150", "847180", "847330", "8542"]
    assert not any(k == "CTY_CODE" for k, _ in world)  # default "-" = TOTAL FOR ALL COUNTRIES (guide, p. 7)
    assert "time=from+2013-01" in census_hs.public_url(world)  # as the guide's "time=from+2013-04"


def test_world_rows_are_the_world_also_if_the_api_shows_cty_code():
    rows = [["CTY_CODE", "I_COMMODITY", "GEN_VAL_MO", "I_COMMODITY", "time"],
            ["-", "8542", "5000000", "8542", "2026-08"], ["-", "8542", "6000000", "8542", "2026-09"]]
    assert list(census_hs.series(census_hs.parse(rows), census_hs.WORLD, "8542")) == [5.0, 6.0]


# ------------------------------------------------------------------ confirmed defects (fixed in X10)


def test_r13_1_a_month_only_in_the_other_response_is_not_a_zero(env):
    env["key"] = SECRET
    env["respond"] = lambda params: Fake(200, api_rows(params, end_named="2026-08", end_world="2026-09"))
    try:
        tw = census_hs.fetch("5830", "8471", hs_series.COMMODITIES, hs_series.COUNTRIES)
    except (ValueError, RuntimeError):
        return  # refusing the inconsistent pair is also a fix
    idx = list(tw.index.astype(str))
    assert not ("2026-09" in idx and tw.iloc[idx.index("2026-09")] == 0.0)


def test_r13_2_site_attribution_carries_the_census_api_notice():
    from ai_tracker.site_bundle import export
    from ai_tracker.state.measures import Context

    block = export.licence_block("us_imp_hs8471_tw_m", Context(observations._empty()))
    assert hs_series.NOTICE in block["attribution"] or hs_series.NOTICE in block.get("notice", "")


def test_r13_3_a_failing_api_is_asked_once_per_run_not_once_per_series(env):
    env["key"] = SECRET
    env["respond"] = lambda params: Fake(302, location="https://api.census.gov/data/invalid_key.html")
    for spec in hs_series.SPECS:
        with pytest.raises(RuntimeError):
            spec.fetch()
    assert len(env["calls"]) <= 2


def test_r13_4_doc_names_the_end_use_reclassification_seam():
    text = DOC.read_text(encoding="utf-8")
    assert "2019–2021" in text or "2019-2021" in text


def test_r13_5_doc_leap_year_wording():
    assert "9 juli efter ett skottår" not in DOC.read_text(encoding="utf-8")
