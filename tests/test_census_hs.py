"""Track M2: Census imports by country (annual end-use file without key, monthly HS API with CENSUS_API_KEY).

Synthetic fixtures in the recorded shapes (enduse_imports.xlsx of 2026-06-09; the API's JSON rows as documented in
the Guide to International Trade Datasets, header first, predicates appended). No network.
"""

from __future__ import annotations

import io
from datetime import date

import pandas as pd
import pytest
import requests

from ai_tracker import catalog, config, keyed, observations, pipeline, warehouse
from ai_tracker.series import census_enduse as eu_series
from ai_tracker.series import census_hs as hs_series
from ai_tracker.sources import census_enduse, census_hs

YEARS = [f"value_{y}" for y in range(16, 26)]


def enduse_xlsx(rows: list[list]) -> bytes:
    df = pd.DataFrame(rows, columns=["CTY_CODE", "CTY_DESC", "END_USE", "COMM_DESC", *YEARS])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="EnduseImp", index=False)
    return buf.getvalue()


ENDUSE = enduse_xlsx([
    ["0000", "World Total", "00000", "Green coffee", *[4_000_000_000 + i for i in range(10)]],
    ["0000", "World Total", "21300", "Computers", *[100_000_000_000 + i * 1_000_000 for i in range(10)]],
    ["5830", "Taiwan", "21300", "Computers", *[10_000_000_000 + i * 2_500_000 for i in range(10)]],
    ["5830", "Taiwan", "21320", "Semiconductors", *[5_000_000 * (i + 1) for i in range(10)]],
])


# ------------------------------------------------------------------ annual end-use file (no key)


def test_enduse_parse_annual_musd_and_years():
    s = census_enduse.parse(ENDUSE, "5830", "21300", "Computers")
    assert list(s.index.astype(str)) == [str(y) for y in range(2016, 2026)]
    assert s.iloc[0] == pytest.approx(10_000.0) and s.iloc[-1] == pytest.approx(10_022.5)  # USD -> MUSD
    assert census_enduse.parse(ENDUSE, "0000", "21300").iloc[-1] == pytest.approx(100_009.0)


def test_enduse_guards():
    with pytest.raises(ValueError, match="expected 'Computers'"):  # a reused or renamed code stops the fetch
        census_enduse.parse(ENDUSE, "5830", "21320", "Computers")
    with pytest.raises(ValueError, match="0 rows"):
        census_enduse.parse(ENDUSE, "5520", "21300")
    bad = io.BytesIO()
    pd.DataFrame({"CTY": ["5830"], "x": [1]}).to_excel(bad, index=False)
    with pytest.raises(ValueError, match="unexpected columns"):
        census_enduse.parse(bad.getvalue(), "5830", "21300")


def test_enduse_known_from_is_july_after_the_annual_revision():
    spec = catalog.by_key()["us_imp_eu21300_tw_a"]
    s = census_enduse.parse(ENDUSE, "5830", "21300", "Computers")
    rows = observations.new_rows(spec, s, observations._empty(), date(2026, 11, 24))
    kf = dict(zip(rows["period"], rows["known_from"]))
    assert kf["2025"] == pd.Timestamp("2026-07-10") > pd.Timestamp("2026-06-09")  # after the documented release
    assert kf["2023"] == pd.Timestamp("2024-07-09")  # leap year: still after the 2024-06-06 release
    assert set(rows["source"]) == {"backfill"}
    assert warehouse.run_checks(warehouse.connect(rows, [spec]))["no_gaps"].empty


def test_enduse_fetch_downloads_once(monkeypatch):
    calls = []

    class R:
        content = ENDUSE

    monkeypatch.setattr(census_enduse.http, "get", lambda url, source: calls.append(url) or R())
    monkeypatch.setattr(census_enduse, "_CACHE", {})
    census_enduse.fetch("5830", "21300", "Computers")
    census_enduse.fetch("0000", "21300", "Computers")
    assert calls == [census_enduse.URL]


def test_enduse_catalog_entries():
    specs = eu_series.SPECS
    assert len(specs) == 21 and {s.freq for s in specs} == {"A"} and {s.branch for s in specs} == {"G6"}
    assert all(s.publish and s.revised and s.lag_days == 191 for s in specs)
    assert all(s.key not in keyed.REQUIRES for s in specs)  # no key needed


# ------------------------------------------------------------------ monthly HS API (key)

HEADER = ["CTY_CODE", "CTY_NAME", "I_COMMODITY", "GEN_VAL_MO", "CTY_CODE", "I_COMMODITY", "time"]


def row(cty, code, month, value, name="X"):
    return [cty, name, code, str(value), cty, code, month]


ROWS = [HEADER,
        row("5830", "8471", "2026-07", 20_000_000_000, "TAIWAN"),
        row("5830", "8471", "2026-09", 22_500_000_000, "TAIWAN"),
        row("5830", "8471", "2026-08", 0, "TAIWAN"),  # a recorded zero, rows out of order
        row("2010", "847150", "2026-07", 7_000_000_000, "MEXICO"),
        row("2010", "847150", "2026-08", 7_100_000_000, "MEXICO"),
        row("2010", "847150", "2026-09", 7_200_000_000, "MEXICO"),
        row("1220", "8471", "2026-07", 1, "CANADA")]  # not asked for: dropped
WORLD = [["I_COMMODITY", "GEN_VAL_MO", "I_COMMODITY", "time"],
         ["8471", "60000000000", "8471", "2026-07"], ["8471", "61000000000", "8471", "2026-08"],
         ["8471", "65000000000", "8471", "2026-09"]]


def test_hs_parse_countries_and_world():
    df = census_hs.parse(ROWS, {"5830", "2010"})
    assert set(df["cty"]) == {"5830", "2010"}
    tw = census_hs.series(df, "5830", "8471")
    assert list(tw.index.astype(str)) == ["2026-07", "2026-08", "2026-09"]
    assert list(tw) == [20_000.0, 0.0, 22_500.0]  # MUSD; the recorded 0 stays 0
    w = census_hs.parse(WORLD)
    assert set(w["cty"]) == {census_hs.WORLD} and census_hs.series(w, "-", "8471").iloc[-1] == 65_000.0


def test_hs_month_without_record_is_zero():
    rows = [HEADER, row("5520", "8542", "2026-07", 5_000_000), row("5520", "8542", "2026-09", 6_000_000),
            row("5830", "8542", "2026-08", 9_000_000)]
    s = census_hs.series(census_hs.parse(rows), "5520", "8542")
    assert list(s) == [5.0, 0.0, 6.0]


def test_hs_parse_refuses_bad_rows():
    with pytest.raises(ValueError, match="two values"):
        census_hs.parse([HEADER, row("5830", "8471", "2026-07", 1), row("5830", "8471", "2026-07", 2)])
    assert len(census_hs.parse([HEADER] + [row("5830", "8471", "2026-07", 1)] * 2)) == 1  # exact repeat is fine
    with pytest.raises(ValueError, match="non-numeric"):
        census_hs.parse([HEADER, row("5830", "8471", "2026-07", "(D)")])
    with pytest.raises(ValueError, match="missing"):
        census_hs.parse([["CTY_CODE", "time"], ["5830", "2026-07"]])
    with pytest.raises(ValueError, match="no rows"):
        census_hs.series(census_hs.parse(ROWS), "5700", "8471")
    assert census_hs.parse([]).empty


def test_hs_params_pin_the_documented_request():
    p = census_hs.params(("8471", "8542"), ("5830", "2010"))
    assert p[0] == ("get", "CTY_CODE,CTY_NAME,I_COMMODITY,GEN_VAL_MO")
    assert ("CTY_CODE", "5830") in p and ("I_COMMODITY", "8542") in p and p[-1] == ("time", "from 2013-01")
    assert census_hs.params(("8471",))[0] == ("get", "I_COMMODITY,GEN_VAL_MO")  # world total: no CTY_CODE
    assert "key" not in census_hs.public_url(p)


def test_hs_known_from_follows_the_ft900_calendar():
    spec = catalog.by_key()["us_imp_hs847150_tw_m"]
    s = pd.Series([1.0, 2.0, 3.0], index=pd.period_range("2025-09", periods=3, freq="M"))
    rows = observations.new_rows(spec, s, observations._empty(), date(2026, 11, 24))
    kf = dict(zip(rows["period"], rows["known_from"]))
    assert kf["2025-10"] == pd.Timestamp("2026-01-08")  # shutdown release (ft900_2510.pdf), as us_imports_tw_m
    s2 = pd.Series([1.0], index=pd.period_range("2026-08", periods=1, freq="M"))
    assert observations.new_rows(spec, s2, observations._empty())["known_from"].iloc[0] == pd.Timestamp("2026-10-11")


def test_hs_catalog_entries():
    specs = hs_series.SPECS
    assert len(specs) == 35 and {s.freq for s in specs} == {"M"} and {s.branch for s in specs} == {"G6"}
    assert all(keyed.REQUIRES[s.key] == "CENSUS_API_KEY" for s in specs)
    assert all(hs_series.NOTICE in s.license and s.publish for s in specs)
    assert catalog.validate(specs) == []


# ------------------------------------------------------------------ the key: request, errors, raw copies

SECRET = "k" * 40


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
    monkeypatch.setattr(census_hs.time, "sleep", lambda s: None)
    monkeypatch.setattr(census_hs.http, "RAW_DIR", tmp_path / "raw")

    def install(*responses):
        it, calls = iter(responses), []

        def get(url, params=None, **kw):
            calls.append((url, params, kw))
            r = next(it)
            if isinstance(r, Exception):
                raise r
            return r
        monkeypatch.setattr(census_hs.requests, "get", get)
        return calls
    return install


def test_request_sends_key_but_never_saves_or_echoes_it(api, tmp_path):
    calls = api(Fake(200, ROWS))
    assert census_hs.request(census_hs.params(("8471",), ("5830",)), SECRET) == ROWS
    url, params, kw = calls[0]
    assert ("key", SECRET) in params and SECRET not in url and kw["allow_redirects"] is False
    saved = list((tmp_path / "raw").rglob("*.json"))
    assert len(saved) == 1 and SECRET not in str(saved[0])


@pytest.mark.parametrize("response, match", [
    (Fake(302, location="https://api.census.gov/data/invalid_key.html"), "refused the key"),
    (Fake(400, "error: unknown variable 'GEN_VAL_M'"), "HTTP 400"),
    (Fake(400, f"error: invalid key {'k' * 40}"), r"HTTP 400.*\*\*\*"),
    (Fake(200, None), "not JSON"),
    (requests.ConnectionError(f"Max retries exceeded with url: /hs?key={'k' * 40}"), "ConnectionError"),
])
def test_request_errors_do_not_contain_the_key(api, response, match):
    api(*([response] * 4))
    with pytest.raises(RuntimeError, match=match) as exc:
        census_hs.request(census_hs.params(("8471",)), SECRET)
    assert SECRET not in str(exc.value) and exc.value.__cause__ is None


def test_request_204_is_empty_and_5xx_is_retried(api):
    api(Fake(204))
    assert census_hs.request(census_hs.params(("8471",)), SECRET) == []
    calls = api(Fake(503, "busy"), Fake(200, WORLD))
    assert census_hs.request(census_hs.params(("8471",)), SECRET) == WORLD and len(calls) == 2


def test_fetch_with_key_makes_two_requests_for_all_series(api, monkeypatch):
    monkeypatch.setattr(keyed.config, "get", lambda name, default=None: SECRET if name == "CENSUS_API_KEY" else None)
    monkeypatch.setattr(census_hs, "_CACHE", {})
    calls = api(Fake(200, ROWS), Fake(200, WORLD))
    tw = census_hs.fetch("5830", "8471", ("8471", "847150"), ("5830", "2010"))
    world = census_hs.fetch("-", "8471", ("8471", "847150"), ("5830", "2010"))
    mx = census_hs.fetch("2010", "847150", ("8471", "847150"), ("5830", "2010"))
    assert len(calls) == 2 and tw.iloc[-1] == 22_500.0 and world.iloc[0] == 60_000.0 and list(mx) == [7_000, 7_100, 7_200]


# ------------------------------------------------------------------ without the key: skipped, not failed


@pytest.fixture
def no_key(monkeypatch):
    real = config.get
    monkeypatch.setattr(keyed.config, "get", lambda name, default=None: None if name == "CENSUS_API_KEY"
                        else real(name, default))
    monkeypatch.setattr(census_hs, "_CACHE", {})

    def boom(*a, **k):
        raise AssertionError("no request without a key")
    monkeypatch.setattr(census_hs.requests, "get", boom)


def test_missing_key_raises_before_any_request(no_key):
    with pytest.raises(keyed.MissingKey, match="CENSUS_API_KEY is not set"):
        catalog.by_key()["us_imp_hs8471_tw_m"].fetch()


def test_refresh_reports_skipped_and_writes_nothing(no_key, tmp_path, monkeypatch):
    path = tmp_path / "observations.parquet"
    monkeypatch.setattr(observations, "PATH", path)
    hs = catalog.by_key()["us_imp_hs8471_tw_m"]
    plain = catalog.Spec(key="plain_m", branch="G6", label="p", unit="x", freq="M", source="test",
                         fetch=lambda: pd.Series([1.0], index=pd.period_range("2026-09", periods=1, freq="M")),
                         lag_days=10, license="unverified")
    monkeypatch.setattr(catalog, "ALL", [hs, plain])
    status = observations.refresh()
    assert status["us_imp_hs8471_tw_m"].startswith("SKIPPED: CENSUS_API_KEY is not set")
    assert status["plain_m"] == "ok +1"
    assert "us_imp_hs8471_tw_m" not in set(observations.load(path)["series"])
    assert "us_imp_hs8471_tw_m" not in set(observations.load_log(path)["series"])  # no fetch-log row either


def test_missing_key_series_are_left_out_of_freshness(monkeypatch):
    hs = catalog.by_key()["us_imp_hs8471_tw_m"]
    plain = catalog.Spec(key="plain_m", branch="G6", label="p", unit="x", freq="M", source="test",
                         fetch=lambda: None, lag_days=10, license="unverified")
    con = warehouse.connect(observations._empty(), [hs, plain])
    monkeypatch.setattr(keyed.config, "get", lambda name, default=None: None)
    assert list(warehouse.fresh(con, "2026-11-24")["series"]) == ["plain_m"]  # no data, but no key either
    monkeypatch.setattr(keyed.config, "get", lambda name, default=None: SECRET)
    assert set(warehouse.fresh(con, "2026-11-24")["series"]) == {"plain_m", "us_imp_hs8471_tw_m"}


def test_weekly_job_passes_with_only_skipped_series(no_key, tmp_path, monkeypatch, capsys):
    hs = catalog.by_key()["us_imp_hs8471_tw_m"]
    monkeypatch.setattr(observations, "PATH", tmp_path / "observations.parquet")
    monkeypatch.setattr(catalog, "ALL", [hs])
    monkeypatch.setattr(pipeline.config, "get", lambda name, default=None: "agent" if name == "SEC_USER_AGENT" else None)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert pipeline.weekly(today="2026-11-24") == 0
    out = capsys.readouterr().out
    assert "1 series skipped: CENSUS_API_KEY is not set" in out and "fetch failed" not in out
