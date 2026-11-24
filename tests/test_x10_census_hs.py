"""Fix track X10 after review R13 of track M2 (docs/granskning/r13_census_hs.md).

Zero rule between a series' own first and last record (R13-1), the Census API notice on the site (R13-2), one request
per run also when it fails, and the per-year split after a timeout (R13-3, R13-6), the strict annual parser, errors
raised outside except, and the warning for a skipped series that already has rows (R13-9), and the first-keyed-fetch
check. Synthetic fixtures, no network.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pandas as pd
import pytest
import requests

from ai_tracker import catalog, config, keyed, observations, pipeline
from ai_tracker.series import census_hs as hs_series
from ai_tracker.site import data as D
from ai_tracker.site import render
from ai_tracker.site_bundle import export
from ai_tracker.sources import census_enduse, census_hs
from ai_tracker.state.measures import Context

SECRET = "x" * 40
HEADER = ["CTY_CODE", "CTY_NAME", "I_COMMODITY", "GEN_VAL_MO", "CTY_CODE", "I_COMMODITY", "time"]
WORLD_HEADER = ["I_COMMODITY", "GEN_VAL_MO", "I_COMMODITY", "time"]


def row(cty, code, month, value):
    return [cty, "X", code, str(value), cty, code, month]


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


@pytest.fixture
def api(monkeypatch, tmp_path):
    """Request stub: `respond(params)` gives a Fake or an exception; `calls` records the params (with the key)."""
    monkeypatch.setattr(census_hs.time, "sleep", lambda s: None)
    monkeypatch.setattr(census_hs.http, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(census_hs, "_CACHE", {})
    monkeypatch.setattr(observations, "PATH", tmp_path / "observations.parquet")
    real = config.get
    state = {"key": SECRET, "calls": [], "respond": None}
    monkeypatch.setattr(keyed.config, "get", lambda n, d=None: state["key"] if n == "CENSUS_API_KEY" else real(n, d))

    def get(url, params=None, **kw):
        state["calls"].append(params)
        r = state["respond"](params)
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(census_hs.requests, "get", get)
    return state


def _time(p):
    return dict(p)["time"]


# ------------------------------------------------------------------ R13-1: zeros only between a series' own records


def test_zeros_only_between_the_series_first_and_last_record():
    rows = [HEADER, row("5520", "8542", "2026-03", 5_000_000), row("5520", "8542", "2026-05", 6_000_000),
            row("5830", "8542", "2026-01", 1_000_000), row("5830", "8542", "2026-07", 2_000_000)]
    df = census_hs.parse(rows)
    vn = census_hs.series(df, "5520", "8542")
    assert list(vn.index.astype(str)) == ["2026-03", "2026-04", "2026-05"]  # not 2026-01..07 (the response's range)
    assert list(vn) == [5.0, 0.0, 6.0]
    assert list(census_hs.series(df, "5830", "8542")) == [1.0, 0, 0, 0, 0, 0, 2.0]


def test_a_month_the_world_response_has_first_is_dated_when_it_arrives(api, monkeypatch):
    """The release race of R13-1 end to end: the country series simply ends a month earlier, and the month it lacks
    is dated after the fetch that lacked it, not by a stored zero."""
    def respond(p, end_named):
        named = any(k == "CTY_CODE" for k, _ in p)
        months = [str(m) for m in pd.period_range("2026-06", end_named if named else "2026-09", freq="M")]
        if named:
            return Fake(200, [HEADER, *[row("5830", "8471", m, 1_000_000_000) for m in months]])
        return Fake(200, [WORLD_HEADER, *[["8471", "9000000000", "8471", m] for m in months]])

    spec = catalog.Spec(key="hs_tw", branch="G6", label="t", unit="MUSD", freq="M", source="test",
                        fetch=lambda: census_hs.fetch("5830", "8471", ("8471",), ("5830",)), lag_days=41,
                        license="test", revised=True)
    monkeypatch.setattr(catalog, "ALL", [spec])

    class D1(date):
        @classmethod
        def today(cls):
            return date(2026, 11, 10)
    monkeypatch.setattr(observations, "date", D1)
    api["respond"] = lambda p: respond(p, "2026-08")
    assert observations.refresh()["hs_tw"] == "ok +3"
    assert "2026-09" not in set(observations.load()["period"].astype(str))

    class D2(date):
        @classmethod
        def today(cls):
            return date(2026, 11, 16)
    monkeypatch.setattr(observations, "date", D2)
    monkeypatch.setattr(census_hs, "_CACHE", {})
    api["respond"] = lambda p: respond(p, "2026-09")
    assert observations.refresh()["hs_tw"] == "ok +1"
    t = observations.load().set_index("period")
    assert t.loc["2026-09", "value"] == 1_000.0 and t.loc["2026-09", "known_from"] == pd.Timestamp("2026-11-11")


# ------------------------------------------------------------------ R13-3, R13-6: one request per run, split by year


def test_a_failure_is_cached_without_the_key_and_named_as_cached(api):
    api["respond"] = lambda p: Fake(400, f"error: unknown variable, key {SECRET}")
    with pytest.raises(RuntimeError) as first:
        hs_series.SPECS[0].fetch()
    with pytest.raises(RuntimeError, match="cached") as again:
        hs_series.SPECS[-1].fetch()
    assert len(api["calls"]) == 1
    assert SECRET not in str(first.value) and SECRET not in str(again.value)
    assert all(v is None for v in (again.value.__cause__, again.value.__context__))


def test_a_hanging_api_costs_one_failed_try_per_run(api, monkeypatch, capsys):
    api["respond"] = lambda p: requests.ReadTimeout(f"Read timed out. (url /hs?key={SECRET})")
    monkeypatch.setattr(catalog, "ALL", [*hs_series.SPECS])
    status = observations.refresh()
    assert len(status) == 35 and all(v.startswith("FAILED") and SECRET not in v for v in status.values())
    # the full request (1 + RETRIES attempts), then the first yearly part (1 + RETRIES attempts), then stop
    assert len(api["calls"]) == 2 * (census_hs.RETRIES + 1)
    assert [_time(p) for p in api["calls"]][-1] == "from 2013-01 to 2013-12"
    assert SECRET not in capsys.readouterr().out


def test_transient_errors_are_raised_without_chained_exceptions(api):
    api["respond"] = lambda p: requests.ConnectionError(f"Max retries exceeded with url: /hs?key={SECRET}")
    with pytest.raises(census_hs.Transient) as exc:
        census_hs.request(census_hs.params(("8471",)), SECRET)
    assert exc.value.__cause__ is None and exc.value.__context__ is None and SECRET not in str(exc.value)
    api["respond"] = lambda p: Fake(503, "busy")
    with pytest.raises(census_hs.Transient, match="HTTP 503"):
        census_hs.request(census_hs.params(("8471",)), SECRET)


def test_a_timeout_splits_the_request_by_year_with_the_same_shape(api):
    full = "from 2013-01"

    def respond(p):
        t = _time(p)
        if t == full:
            return requests.ReadTimeout("Read timed out.")
        year = t.split()[1][:4]
        if year == "2014":
            return Fake(204)  # a year without records is skipped
        months = [f"{year}-01", f"{year}-02"] if year != "2015" else ["2015-01"]
        return Fake(200, [HEADER, *[row("5830", "8471", m, 1_000_000) for m in months]])
    api["respond"] = respond
    rows = census_hs.rows_from(("8471",), ("5830",), SECRET, today=date(2015, 3, 1))
    times = [_time(p) for p in api["calls"]]
    assert times == [full] * (census_hs.RETRIES + 1) + ["from 2013-01 to 2013-12", "from 2014-01 to 2014-12",
                                                        "from 2015-01"]
    assert rows[0] == HEADER and len(rows) == 1 + 3
    s = census_hs.series(census_hs.parse(rows, {"5830"}), "5830", "8471")
    assert s.index.min() == pd.Period("2013-01", "M") and s.index.max() == pd.Period("2015-01", "M")
    assert s["2014-06"] == 0.0  # a year with no records inside the series is no trade (204), as in one request


def test_split_parts_must_share_the_header(api):
    def respond(p):
        t = _time(p)
        if t == "from 2013-01":
            return Fake(504, "gateway")
        if t.startswith("from 2013"):
            return Fake(200, [HEADER, row("5830", "8471", "2013-01", 1)])
        return Fake(200, [["I_COMMODITY", "GEN_VAL_MO", "time"], ["8471", "1", "2014-01"]])
    api["respond"] = respond
    with pytest.raises(ValueError, match="header of 2014"):
        census_hs.rows_from(("8471",), ("5830",), SECRET, today=date(2014, 5, 1))


def test_a_refused_key_is_not_split(api):
    api["respond"] = lambda p: Fake(302, location="https://api.census.gov/data/invalid_key.html")
    with pytest.raises(RuntimeError, match="refused the key"):
        census_hs.rows_from(("8471",), (), SECRET)
    assert len(api["calls"]) == 1


# ------------------------------------------------------------------ R13-2: the notice reaches the site


def test_every_hs_spec_carries_the_notice_and_validate_requires_it_in_the_licence():
    assert all(s.notice == hs_series.NOTICE for s in hs_series.SPECS)
    assert catalog.validate(hs_series.SPECS) == []
    bad = catalog.Spec(key="bad_m", branch="G6", label="b", unit="x", freq="M", source="test", fetch=lambda: None,
                       lag_days=1, license="public domain", notice="Display me.")
    assert any("notice must be quoted in license" in e for e in catalog.validate([bad]))


def test_attribution_carries_the_notice_only_where_the_terms_ask_for_it():
    ctx = Context(observations._empty())
    hs = export.licence_block("us_imp_hs8542_world_m", ctx)
    assert hs["attribution"].endswith(f"Bearbetning: ai-rollout-tracker. {hs_series.NOTICE}")
    plain = export.licence_block("us_imp_eu21320_world_a", ctx)
    assert plain["attribution"].endswith("Bearbetning: ai-rollout-tracker.") and hs_series.NOTICE not in str(plain)


def _rows(key, n=1):
    return pd.DataFrame({"series": [key] * n, "freq": "M", "period": "2026-09", "value": 1.0,
                         "known_from": pd.Timestamp("2026-11-10"), "source": "backfill",
                         "fetched_at": pd.Timestamp("2026-11-24")})


def test_footer_shows_the_notice_once_a_published_series_with_one_has_rows():
    assert D.site_notices(Context(observations._empty())) == []
    assert D.site_notices(Context(_rows("us_imp_eu21300_tw_a"))) == []  # the annual file is not the API
    ctx = Context(pd.concat([_rows("us_imp_hs8471_tw_m"), _rows("us_imp_hs8542_cn_m")], ignore_index=True))
    assert D.site_notices(ctx) == [hs_series.NOTICE]
    build = {"built_utc": "t", "git_sha": "g", "repo": "https://example.org/r", "table_max_fetched_at": "2026-11-24",
             "record": {"month": "2026-11", "label": "rekonstruerad"}, "notices": D.site_notices(ctx)}
    html = render.page("T", "oversikt", "<p>x</p>", None, build)
    footer = html[html.index("<footer>"):html.index("</footer>")]
    assert render.esc(hs_series.NOTICE) in footer
    assert render.esc(hs_series.NOTICE) not in render.page("T", "oversikt", "", None, {**build, "notices": []})
    specs = catalog.by_key()
    specs["us_imp_hs8471_tw_m"] = replace(specs["us_imp_hs8471_tw_m"], publish=False)
    ctx2 = Context(_rows("us_imp_hs8471_tw_m"), specs=specs)
    assert D.site_notices(ctx2) == []  # a withheld series shows no data, so no notice either


# ------------------------------------------------------------------ R13-9: hardening


def test_annual_parser_stops_on_an_empty_or_non_numeric_cell():
    years = [f"value_{y}" for y in range(16, 26)]
    df = pd.DataFrame([["5830", "Taiwan", "21300", "Computers", *[1e9] * 9, "(D)"],
                       ["2010", "Mexico", "21300", "Computers", None, *[1e9] * 9]],
                      columns=["CTY_CODE", "CTY_DESC", "END_USE", "COMM_DESC", *years])
    with pytest.raises(ValueError, match="non-numeric values {2025: '\\(D\\)'}"):
        census_enduse.parse(df, "5830", "21300", "Computers")
    with pytest.raises(ValueError, match="non-numeric values {2016"):
        census_enduse.parse(df, "2010", "21300", "Computers")


def test_skipped_series_that_already_have_rows_give_a_warning(monkeypatch, tmp_path, capsys):
    path = tmp_path / "observations.parquet"
    monkeypatch.setattr(observations, "PATH", path)
    real = config.get
    monkeypatch.setattr(keyed.config, "get", lambda n, d=None: None if n == "CENSUS_API_KEY" else real(n, d))
    monkeypatch.setattr(census_hs, "_CACHE", {})
    hs = catalog.by_key()["us_imp_hs8471_tw_m"]
    monkeypatch.setattr(catalog, "ALL", [hs, catalog.by_key()["us_imp_hs8471_mx_m"]])
    observations.upsert(hs, pd.Series([1.0], index=pd.period_range("2026-09", periods=1, freq="M")),
                        fetched_at=date(2026, 11, 16))
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert pipeline._refresh(None) == []
    out = capsys.readouterr().out
    assert "NOTICE: 2 series skipped" in out
    assert "WARNING: 1 skipped series already have rows" in out and "us_imp_hs8471_tw_m" in out


# ------------------------------------------------------------------ the first-keyed-fetch check (R13-6)


def test_check_reports_the_checklist_without_writing(api):
    def respond(p):
        d = dict(p)
        if "LAST_UPDATE" in d["get"]:
            return Fake(200, [["I_COMMODITY", "GEN_VAL_MO", "LAST_UPDATE", "I_COMMODITY", "time"],
                              ["8542", "1", "2026-11-04", "8542", "2026-09"]])
        if any(k == "CTY_CODE" for k, _ in p):
            return Fake(200, [HEADER, row("5830", "8471", "2025-01", 4_000_000_000),
                              row("5830", "8471", "2025-03", 6_000_000_000),
                              row("5830", "847330", "2025-02", 1_000_000_000)])
        return Fake(200, [WORLD_HEADER, ["8471", "9000000000", "8471", "2025-01"]])
    api["respond"] = respond
    table = pd.concat([_rows("us_imp_eu21300_tw_a").assign(freq="A", period="2025", value=9_000.0),
                       _rows("us_imp_eu21301_tw_a").assign(freq="A", period="2025", value=1_000.0)],
                      ignore_index=True)
    lines = census_hs.check(("8471", "847330"), {"tw": "5830", "world": "-"}, table)
    text = "\n".join(lines)
    assert "8471 tw: 2025-01 .. 2025-03, 2 records, 1 months without a record (0)" in text
    assert "847330 world: NO ROWS" in text
    assert "2025 tw: HS 8471 + 8473.30 = 11,000.0 MUSD, end-use 21300 + 21301 = 10,000.0 MUSD, ratio 1.100" in text
    assert "LAST_UPDATE for 2025-03: ['2026-11-04']" in text
    assert not observations.PATH.exists() and SECRET not in text
