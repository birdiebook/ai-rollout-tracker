"""X18, fixes after review R21 of CN1: the Alibaba capex cross-check as registered (register change 2026-11-25 after
R21). Synthetic 20-F instance and companyfacts, no network."""

from __future__ import annotations

import json

import pandas as pd

from ai_tracker import china_crosscheck as cc
from ai_tracker.sources import china_sec as cs
from ai_tracker.sources import sec

INSTANCE = """<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:iso4217="http://www.xbrl.org/2003/iso4217"
 xmlns:us-gaap="http://fasb.org/us-gaap/2016-01-31" xmlns:baba="http://www.alibabagroup.com/20170331">
 <xbrli:context id="FY2017"><xbrli:period><xbrli:startDate>2016-04-01</xbrli:startDate>
  <xbrli:endDate>2017-03-31</xbrli:endDate></xbrli:period></xbrli:context>
 <xbrli:context id="FY2020"><xbrli:period><xbrli:startDate>2019-04-01</xbrli:startDate>
  <xbrli:endDate>2020-03-31</xbrli:endDate></xbrli:period></xbrli:context>
 <xbrli:context id="FY2021"><xbrli:period><xbrli:startDate>2020-04-01</xbrli:startDate>
  <xbrli:endDate>2021-03-31</xbrli:endDate></xbrli:period></xbrli:context>
 <xbrli:unit id="CNY"><xbrli:measure>iso4217:CNY</xbrli:measure></xbrli:unit>
 <baba:PaymentsToAcquireOtherPropertyEquipmentIntangibleAssetsAndLicensedCopyrightsOfVideoContent contextRef="FY2017"
  unitRef="CNY">12220000000</baba:PaymentsToAcquireOtherPropertyEquipmentIntangibleAssetsAndLicensedCopyrightsOfVideoContent>
 <us-gaap:PaymentsToAcquireLandUseRightsPropertyAndEquipment contextRef="FY2017" unitRef="CNY">13000000000</us-gaap:PaymentsToAcquireLandUseRightsPropertyAndEquipment>
 <us-gaap:PaymentsToAcquireLandUseRightsPropertyAndEquipment contextRef="FY2020" unitRef="CNY">29000000000</us-gaap:PaymentsToAcquireLandUseRightsPropertyAndEquipment>
 <us-gaap:PaymentsToAcquireLandUseRightsPropertyAndEquipment contextRef="FY2021" unitRef="CNY">41450000000</us-gaap:PaymentsToAcquireLandUseRightsPropertyAndEquipment>
</xbrli:xbrl>"""

QUARTERS = {  # synthetic quarters with the sums of the real ones (FY2017 v1, FY2020 and FY2021 v2)
    "capex_baba_v1": {"2016Q2": 2794.0, "2016Q3": 3348.0, "2016Q4": 3246.0, "2017Q1": 2832.0},
    "capex_baba_v2": {"2019Q2": 5856.0, "2019Q3": 9176.0, "2019Q4": 5749.0, "2020Q1": 3881.0,
                      "2020Q2": 8000.0, "2020Q3": 9000.0, "2020Q4": 10000.0, "2021Q1": 9160.0},
}


def _series(company: str, measure: str, key: str) -> pd.DataFrame:
    data = QUARTERS.get(key, {})
    return pd.DataFrame({"period": list(data), "value": list(data.values()),
                         "known_from": [pd.Timestamp("2021-07-27")] * len(data)})


def _fact(val: float, start: str, end: str, filed: str, accn: str) -> dict:
    return {"val": val, "start": start, "end": end, "form": "20-F", "filed": filed, "accn": accn, "fp": "FY"}


def _companyfacts(cik: int) -> dict:
    if cik == cs.CIKS["bidu"]:
        return {"facts": {"us-gaap": {cc.BIDU_CAPEX: {"units": {"CNY": []}}}}}
    return {"facts": {"us-gaap": {
        cc.BABA_PPE: {"units": {"CNY": [_fact(24662e6, "2019-04-01", "2020-03-31", "2020-07-09", "a-20")]}},
        cc.BABA_INTANGIBLES: {"units": {"CNY": [_fact(12836e6, "2019-04-01", "2020-03-31", "2020-07-09", "a-20")]}}}}}


def _filings(cik: int, form_prefix: str = "6-K", since: str = "2000-01-01") -> list[cs.Filing]:
    assert form_prefix == "20-F" and since == cc.SINCE_20F
    return [cs.Filing(cik, "0001047469-21-000001", "2021-07-27", "2021-07-27T10:00:00.000Z", "20-F", "d.htm")]


def _cached_get(url: str, retries: int = 2) -> bytes:
    if url.endswith("index.json"):
        return json.dumps({"directory": {"item": [{"name": "baba-20210331.xml"}, {"name": "d.htm"}]}}).encode()
    return INSTANCE.encode()


def test_20f_filings_are_read_from_2016():
    assert cc.SINCE_20F == "2016-01-01"  # 20-F FY2016-FY2018: v1's own line FY2015-FY2018, the cloud segment FY2016


def test_v1_line_is_exact_and_the_broader_line_is_a_ratio_only_where_no_exact_line(monkeypatch):
    monkeypatch.setattr(cs, "series", _series)
    monkeypatch.setattr(cs, "filings", _filings)
    monkeypatch.setattr(cs, "cached_get", _cached_get)
    monkeypatch.setattr(sec, "companyfacts", _companyfacts)
    res = cc.run()
    got = {(r.kind.split(":", 1)[0] if r.kind.startswith("v1line") else r.kind, r.check, r.series, r.fy_end):
           round(r.diff, 6) for r in res.itertuples(index=False)}
    assert got == {
        ("v1line", "exact", "capex_baba_v1", "2017-03-31"): 0.0,  # the company's own line, 20-F FY2017 name
        ("cf:ppe", "exact", "capex_baba_v2", "2020-03-31"): 0.0,  # companyfacts PP&E
        ("capex", "ratio", "capex_baba_v2", "2021-03-31"): 36160.0 - 41450.0,  # no exact line: ratio only
    }
    # v1 is never compared with PP&E alone, v2 never with PP&E plus intangibles, and FY2017 / FY2020 get no ratio row
    ratio = res[res.check == "ratio"]
    assert ratio.ratio.round(3).tolist() == [round(36160.0 / 41450.0, 3)]
    summ = cc.summary(res).set_index(["series", "check"])
    assert summ.loc[("capex_baba_v1", "exact"), "exact_in_all_20f"] == 1
    assert summ.loc[("capex_baba_v2", "ratio"), "exact_in_some_20f"] == 0


def test_exact_kinds_map_to_the_series_of_their_definition():
    assert cc.capex_series("cf:ppe") == "capex_baba_v2"
    assert cc.capex_series("cf:ppe+intangibles") == "capex_baba_v1"
    for concept in cc.BABA_V1_LINES:
        assert cc.capex_series(f"v1line:{concept}") == "capex_baba_v1"
