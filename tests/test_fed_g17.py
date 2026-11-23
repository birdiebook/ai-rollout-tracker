"""Fed G.17 from federalreserve.gov (track I7): parsers, vintages and known_from. No network."""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker import catalog, observations
from ai_tracker.sources import fed_g17

T = pd.Timestamp

INDEX_HTML = """
<a href="20261016/">x</a><a href="20261016/g17.pdf">p</a><a href="20261016/ipdisk/alltables.htm">t</a>
<a href="./20160415/ipdisk/alltables.htm">t</a><a href="20160315/g17.pdf">no data dir</a>
<a href="Revisions/20251124/ipdisk/alltables.htm">r</a><a href="revisions/20170331/ipdisk/alltables.htm">r</a>
<a href="Revisions/20160401/g17rev.pdf">no data dir</a>
"""

IP_TEXT = '''"B50001: Total index"
"B50001"        2025     100.0000  101.0000  102.0000  103.0000  104.0000  105.0000  106.0000  107.0000  108.0000  109.0000  110.0000  111.0000
"G3341: Computer and peripheral equipment  NAICS=3341"
"G3341"         2025      90.0000   91.0000   92.0000   93.0000   94.0000   95.0000   96.0000   97.0000   98.0000   99.0000  100.0000  101.0000
"G3341"         2026     102.0000  103.5000
"G3344: Semiconductor and other electronic component  NAICS=3344"
"G3344"         2025     150.0000  151.0000  152.0000  153.0000  154.0000  155.0000  156.0000  157.0000  158.0000  159.0000  160.0000  161.0000
"G3344"         2026     176.7104  176.1804
"G33441: not requested"
"G33441"        2026       1.0000
'''

DDP_PAGE = """<span id="ReleaseLabel"><a href='/releases/G17/default.htm'>G.17 - Industrial Production and Capacity
Utilization</a> - last released Tuesday, November 17, 2026</span>
<option value="rel=G17&amp;series=5d88&amp;lastobs=&amp;filetype=csv&amp;type=package">Table 4: Industrial Production:
Market and Industry Groups [csv, All Observations, 444.1 KB ]</option>
<option value="rel=G17&amp;series=5cb6&amp;lastobs=&amp;from=&amp;to=&amp;filetype=csv&amp;label=include&amp;layout=seriesrow&amp;type=package">Table 5: Industrial Production: Special Aggregates and Selected Detail [csv, All Observations, 216.8 KB ]</option>
"""

DDP_CSV = (
    '"Description:","Unit:","Multiplier:","Currency:","Unique Identifier:","Series Name:",2026-08,2026-09,2026-10\n'
    '"Total index; s.a. IP","Index:_2017_100","1","NA","G17/IP_SPECIAL_AGGREGATES/IP.B50001.S","IP.B50001.S",103.1,103.8,103.4\n'
    '"Computer and peripheral equipment  (NAICS = 3341); s.a. IP","Index:_2017_100","1","NA",'
    '"G17/IP_SPECIAL_AGGREGATES/IP.G3341.S","IP.G3341.S",182.3932,185.0845,190.9586\n'
    '"Semiconductor and other electronic component  (NAICS = 3344); s.a. IP","Index:_2017_100","1","NA",'
    '"G17/IP_SPECIAL_AGGREGATES/IP.G3344.S","IP.G3344.S",,190.7773,195.0164\n'
)


def test_parse_archive_monthly_and_annual_revisions():
    got = fed_g17.parse_archive(INDEX_HTML)
    assert got == {T("2016-04-15"): "20160415", T("2017-03-31"): "revisions/20170331",
                   T("2025-11-24"): "Revisions/20251124", T("2026-10-16"): "20261016"}
    assert list(got) == sorted(got)


def test_parse_ip_text():
    out = fed_g17.parse_ip_text(IP_TEXT)
    assert set(out) == {"G3344", "G3341"}
    s = out["G3344"]
    assert len(s) == 14 and s.index[0] == T("2025-01-01") and s.index[-1] == T("2026-02-01")
    assert s[T("2026-01-01")] == pytest.approx(176.7104)
    assert out["G3341"][T("2026-02-01")] == 103.5
    with pytest.raises(ValueError, match="lacks"):
        fed_g17.parse_ip_text(IP_TEXT, codes=("G3344", "G9999"))
    with pytest.raises(ValueError, match="more than 12"):
        fed_g17.parse_ip_text('"G3344"  2026 ' + " 1.0" * 13)


def test_parse_ddp_page_and_csv():
    released, query = fed_g17.parse_ddp_page(DDP_PAGE)
    assert released == T("2026-11-17")
    assert query.startswith("rel=G17&series=5cb6&") and "layout=seriesrow" in query and "&amp;" not in query
    with pytest.raises(ValueError):
        fed_g17.parse_ddp_page(DDP_PAGE.replace("Table 5", "Table 9"))
    out = fed_g17.parse_ddp_csv(DDP_CSV)
    assert list(out["G3344"].index) == [T("2026-09-01"), T("2026-10-01")]  # empty cell = not published
    assert out["G3341"].iloc[-1] == pytest.approx(190.9586)
    with pytest.raises(ValueError, match="header"):
        fed_g17.parse_ddp_csv(DDP_CSV.replace("Series Name:", "Name:"))
    with pytest.raises(ValueError, match="lacks"):
        fed_g17.parse_ddp_csv(DDP_CSV.replace("IP.G3341.S", "IP.G9999.S"))


def test_parse_current_date():
    page = '<!--PAGEWATCH--><div class="dates">Release Date: November 17, 2026</div>'
    assert fed_g17.parse_current_date(page) == T("2026-11-17")
    with pytest.raises(ValueError):
        fed_g17.parse_current_date("<div>no date</div>")


def _vintages():
    def s(d):
        return pd.Series({T(k): v for k, v in d.items()})
    return {
        T("2026-09-18"): {"G3344": s({"2026-07-01": 190.0, "2026-08-01": 192.0}), "G3341": s({"2026-08-01": 1.0})},
        T("2026-10-16"): {"G3344": s({"2026-07-01": 190.0, "2026-08-01": 194.5, "2026-09-01": 198.6}),
                          "G3341": s({"2026-08-01": 1.0, "2026-09-01": 2.0})},
        T("2026-11-17"): {"G3344": s({"2026-07-01": 189.0, "2026-08-01": 194.5, "2026-09-01": 190.8,
                                      "2026-10-01": 195.0}),
                          "G3341": s({"2026-08-01": 1.0, "2026-09-01": 2.0, "2026-10-01": 3.0})},
    }


def test_known_from_is_release_date_and_revisions_are_new_rows():
    rows = fed_g17.release_rows("G3344", _vintages())
    got = {(str(r.period.date()), str(r.known_from.date())): r.value for r in rows.itertuples()}
    assert got == {("2026-07-01", "2026-09-18"): 190.0, ("2026-08-01", "2026-09-18"): 192.0,
                   ("2026-08-01", "2026-10-16"): 194.5, ("2026-09-01", "2026-10-16"): 198.6,
                   ("2026-07-01", "2026-11-17"): 189.0, ("2026-09-01", "2026-11-17"): 190.8,
                   ("2026-10-01", "2026-11-17"): 195.0}
    spec = catalog.by_key()["us_ip_semis_m"]
    table = observations.new_rows(spec, rows, observations._empty(), fetched_at=T("2026-11-23").date())
    assert set(table["source"]) == {"release"}
    assert observations.as_of("us_ip_semis_m", "2026-11-16", table).to_dict() == {
        pd.Period("2026-07", "M"): 190.0, pd.Period("2026-08", "M"): 194.5, pd.Period("2026-09", "M"): 198.6}
    assert observations.as_of("us_ip_semis_m", "2026-11-17", table)[pd.Period("2026-09", "M")] == 190.8
    # a later fetch of the same vintages adds nothing
    assert observations.new_rows(spec, rows, table, fetched_at=T("2026-12-01").date()).empty


def test_all_vintages_merges_current_release(monkeypatch):
    v = _vintages()
    archive = {d: x for d, x in v.items() if d < T("2026-11-17")}
    monkeypatch.setattr(fed_g17, "archived_vintages", lambda: dict(archive))
    monkeypatch.setattr(fed_g17, "current_vintage", lambda: (T("2026-11-17"), v[T("2026-11-17")]))
    assert list(fed_g17.all_vintages()) == list(v)
    # once moved to the archive, the current release is not added twice
    monkeypatch.setattr(fed_g17, "current_vintage", lambda: (T("2026-10-16"), v[T("2026-11-17")]))
    got = fed_g17.all_vintages()
    assert list(got) == list(archive) and got[T("2026-10-16")] is archive[T("2026-10-16")]
    monkeypatch.setattr(fed_g17, "current_vintage", lambda: (T("2026-09-01"), v[T("2026-11-17")]))
    with pytest.raises(ValueError, match="older"):
        fed_g17.all_vintages()


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(fed_g17, "CACHE", tmp_path)
    data = fed_g17.parse_ip_text(IP_TEXT)
    assert fed_g17._read_cache(T("2026-10-16")) is None
    fed_g17._write_cache(T("2026-10-16"), data)
    back = fed_g17._read_cache(T("2026-10-16"))
    for code in fed_g17.CODES:
        pd.testing.assert_series_equal(back[code], data[code], check_names=False, check_freq=False)


def test_catalog_uses_primary_source():
    by = catalog.by_key()
    for key in ("us_ip_semis_m", "us_ip_computers_m"):
        s = by[key]
        assert "federalreserve.gov" in s.source and "ALFRED" not in s.source and s.revised
        assert "public domain" in s.license and s.publish
    m3 = by["us_orders_computers_electronics_m"]
    assert "ALFRED" in m3.source and not m3.publish


def test_drop_series(tmp_path):
    path = tmp_path / "obs.parquet"
    spec = catalog.by_key()["us_ip_semis_m"]
    rows = fed_g17.release_rows("G3344", _vintages())
    observations.upsert(spec, rows, fetched_at=T("2026-11-23").date(), path=path)
    assert observations.drop_series(["us_ip_semis_m"], path) == 7
    assert observations.load(path).empty and observations.drop_series(["us_ip_semis_m"], path) == 0
