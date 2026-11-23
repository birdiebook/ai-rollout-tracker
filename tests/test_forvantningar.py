"""External expectations (D3): selection rule, daily series from trades, Polymarket snapshots (no network)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from ai_tracker import catalog
from ai_tracker.series import forvantningar as sf
from ai_tracker.sources import forvantningar as fv

TODAY = pd.Timestamp("2026-11-23")
MS = 1_000


def ms(day: str) -> int:
    return int(pd.Timestamp(day).value // 1_000_000)


def mf(id_, title, bettors=150, created="2024-01-01", close="2028-01-01", resolved=False, resolution=None,
       otype="BINARY", token="MANA", resolution_time=None):
    m = {"id": id_, "question": title, "outcomeType": otype, "mechanism": "cpmm-1", "token": token,
         "uniqueBettorCount": bettors, "createdTime": ms(created), "closeTime": ms(close), "isResolved": resolved,
         "url": f"https://manifold.markets/x/{id_}", "probability": 0.5}
    if resolved:
        m["resolution"] = resolution or "NO"
        m["resolutionTime"] = ms(resolution_time or close)
    return m


@pytest.mark.parametrize("title,ai_tag,expected", [
    ("Will we get AGI before 2027?", False, "T1"),
    ("Will an AI win gold at the IMO 2025?", False, "T1"),
    ("Will OpenAI IPO before 2027?", False, "T2"),
    ("Will Nvidia be the largest company by market cap?", False, "T2"),
    ("Will OpenAI release GPT-6 and IPO?", False, "T1"),  # first matching topic wins
    ("Will Microsoft capex for AI exceed $100bn?", False, "T3"),
    ("Will Indiana enact a data center moratorium?", True, "T3"),
    ("Will Indiana enact a data center moratorium?", False, "T3"),  # "data cent" is an AI link
    ("Will the US loosen export controls on Nvidia H20?", False, "T4"),
    ("Will the EU delay the AI Act?", False, "T5"),
    ("Will Congress pass a moratorium on state laws?", False, None),  # T5 without an AI link
    ("Will it rain in Paris in 2027?", False, None),
])
def test_topic(title, ai_tag, expected):
    assert fv.topic(title, ai_tag=ai_tag) == expected


def test_manifold_rule():
    markets = [
        mf("ok_open", "Will we get AGI before 2030?"),
        mf("ok_open", "duplicate id is skipped"),
        mf("few", "Will we get AGI before 2030?", bettors=99),
        mf("cash", "Will we get AGI before 2030?", token="CASH"),
        mf("multi", "Will we get AGI before 2030?", otype="MULTIPLE_CHOICE"),
        mf("soon", "Will we get AGI before 2027?", close="2027-02-01"),  # < 90 days left
        mf("ok_res", "Will an AI win IMO gold in 2025?", created="2024-07-01", close="2025-07-21", resolved=True,
           resolution="YES"),
        mf("short", "Will an AI win IMO gold in 2025?", created="2025-03-01", close="2025-07-21", resolved=True),
        mf("old", "Will SB 1047 AI bill pass in 2022?", created="2021-01-01", close="2022-09-29", resolved=True),
        mf("cancel", "Will we get AGI before 2025?", created="2023-01-01", close="2025-01-01", resolved=True,
           resolution="CANCEL"),
        mf("me", "Will I believe in AGI by 2030?"),
        mf("offtopic", "Will it rain in 2030?"),
        # resolved early: life measured to the resolution, which is < 180 days after creation
        mf("early", "Will OpenAI be valued at $1T by 2030?", created="2026-01-01", close="2030-01-01",
           resolved=True, resolution_time="2026-03-01"),
    ]
    out = {c["id"]: c for c in fv.manifold_candidates(markets, TODAY)}
    assert set(out) == {"ok_open", "ok_res"}
    assert out["ok_open"]["status"] == "open" and out["ok_res"]["status"] == "resolved"
    assert out["ok_res"]["close"] == "2025-07-21" and out["ok_open"]["topic"] == "T1"
    assert "probability" not in out["ok_open"]  # metadata only


def pm_event(eid, markets):
    return {"id": eid, "slug": f"ev-{eid}", "markets": markets}


def pm(mid, title, volume=300_000, end="2028-01-01T00:00:00Z", closed=False, outcomes='["Yes", "No"]'):
    return {"id": mid, "question": title, "outcomes": outcomes, "volumeNum": volume, "endDate": end,
            "createdAt": "2025-01-01T00:00:00Z", "closed": closed, "active": True, "archived": False,
            "outcomePrices": '["0.4", "0.6"]', "resolutionSource": ""}


def test_polymarket_rule_and_event_cap():
    events = [pm_event(1, [pm(11, "OpenAI IPO above $1T by 2027?", 900_000), pm(12, "OpenAI IPO above $1.2T?", 800_000),
                           pm(13, "OpenAI IPO above $1.5T?", 700_000), pm(14, "OpenAI IPO above $2T?", 100_000)]),
              pm_event(2, [pm(21, "Will we get AGI in 2027?", closed=True),
                           pm(22, "Which team wins 2027?", outcomes='["A", "B"]'),
                           pm(23, "Will we get AGI before 2027?", end="2026-12-31T00:00:00Z")])]
    cands = fv.polymarket_candidates(events, TODAY)
    assert [c["id"] for c in cands] == ["11", "12", "13"]  # 14 too little volume, event 2 fails type/time/open
    capped = fv.apply_cap(cands)
    assert [c["id"] for c in capped] == ["11", "12"]  # at most 2 per event
    assert capped[0]["resolution_url"] == "https://polymarket.com/event/ev-1"


def test_cap_six_per_topic_by_participation_then_id():
    cands = [{"platform": "manifold", "topic": "T1", "id": f"id{i}", "participation": p, "event": ""}
             for i, p in enumerate([500, 400, 400, 300, 200, 150, 120, 110])]
    assert [c["id"] for c in fv.apply_cap(cands)] == ["id0", "id1", "id2", "id3", "id4", "id5"]


def test_daily_from_trades_carry_forward_and_known_from():
    times = pd.to_datetime(["2025-01-01 10:00", "2025-01-01 23:59", "2025-01-03 08:00", "2025-01-06 01:00"])
    out = fv.daily_from_trades(pd.Series(times), pd.Series([0.2, 0.3, 0.5, 0.9]), pd.Timestamp("2025-01-04"))
    assert list(out["period"]) == ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]
    assert list(out["value"]) == [0.3, 0.3, 0.5, 0.5]  # last trade of the day, carried; 01-06 is after end
    assert (out["known_from"] == pd.to_datetime(out["period"]) + pd.Timedelta(days=1)).all()
    # every trade used is before known_from
    for p, kf in zip(out["period"], out["known_from"]):
        assert times[times < pd.Timestamp(p) + pd.Timedelta(days=1)].max() < kf


def test_manifold_series_ends_yesterday_or_at_close(monkeypatch):
    bets = [{"createdTime": ms("2026-11-20 12:00"), "probAfter": 0.4},
            {"createdTime": ms("2026-11-23 09:00"), "probAfter": 0.7},  # today: not a complete day
            {"createdTime": ms("2026-11-19 12:00"), "probAfter": 0.1}]
    monkeypatch.setattr(fv, "manifold_bets", lambda _id: bets)
    q = {"id": "x", "platform": "manifold", "close": "2028-01-01", "status": "open", "selected_on": "2026-11-22"}
    out = fv.manifold_series(q, now=pd.Timestamp("2026-11-23 18:00"))
    assert list(out["period"]) == ["2026-11-19", "2026-11-20", "2026-11-21", "2026-11-22"]
    assert list(out["value"]) == [0.1, 0.4, 0.4, 0.4]
    # known before the selection day -> backfill (survivorship-conditioned set), from it on -> release
    assert list(out["source"]) == ["backfill", "backfill", "release", "release"]
    closed = dict(q, close="2026-11-20", status="resolved")
    assert fv.manifold_series(closed, now=pd.Timestamp("2026-11-23"))["period"].iloc[-1] == "2026-11-20"


def test_manifold_preselection_rows_are_stored_as_backfill_with_their_trade_dates():
    from ai_tracker import catalog, observations

    q = {"id": "x", "selected_on": "2026-11-23"}
    df = fv.flag_preselection(fv.daily_from_trades(pd.Series(pd.to_datetime(["2026-11-20 10:00", "2026-11-22 10:00"])),
                                                   pd.Series([0.2, 0.6]), pd.Timestamp("2026-11-23")), q)
    spec = catalog.Spec(key="g9_exp_mf_x", branch="G9", label="x", unit="p", freq="D", source="Manifold",
                        fetch=lambda: df, lag_days=1, license="unverified", revised=False, publish=False)
    rows = observations.new_rows(spec, df, pd.DataFrame(columns=observations.COLUMNS),
                                 fetched_at=pd.Timestamp("2026-11-24").date())
    got = {(r.period, r.source): str(r.known_from.date()) for r in rows.itertuples()}
    assert got == {("2026-11-20", "backfill"): "2026-11-21", ("2026-11-21", "backfill"): "2026-11-22",
                   ("2026-11-22", "release"): "2026-11-23", ("2026-11-23", "release"): "2026-11-24"}


def _table(rows):
    return pd.DataFrame(rows, columns=["series", "freq", "period", "value", "known_from", "source", "fetched_at"])


def test_polymarket_snapshot_first_fetch_after_week_end(monkeypatch):
    q = {"id": "11", "platform": "polymarket", "close": "2028-01-01", "status": "open"}
    monkeypatch.setattr(fv, "_gamma_market", lambda _id: pm(11, "t"))
    now = pd.Timestamp("2026-11-23 03:37:12")  # Monday
    out = fv.polymarket_series(q, now=now, table=_table([]))
    assert list(out["period"]) == ["2026-11-16/2026-11-22"]
    assert out["value"].iloc[0] == 0.4 and out["known_from"].iloc[0] == pd.Timestamp("2026-11-23")
    assert out["source"].iloc[0] == "snapshot"
    # a second fetch in the same week keeps the stored snapshot
    stored = _table([("g9_exp_pm_11", "W", "2026-11-16/2026-11-22", 0.4, pd.Timestamp("2026-11-23"), "snapshot",
                      pd.Timestamp("2026-11-23"))])
    monkeypatch.setattr(fv, "_gamma_market", lambda _id: pm(11, "t") | {"outcomePrices": '["0.9", "0.1"]'})
    again = fv.polymarket_series(q, now=pd.Timestamp("2026-11-26 10:00"), table=stored)
    assert list(again["value"]) == [0.4]
    nxt = fv.polymarket_series(q, now=pd.Timestamp("2026-11-30 03:37"), table=stored)
    assert list(nxt["period"]) == ["2026-11-16/2026-11-22", "2026-11-23/2026-11-29"]
    assert list(nxt["value"]) == [0.4, 0.9]
    # closed: nothing new
    assert len(fv.polymarket_series(dict(q, status="closed"), now=pd.Timestamp("2026-11-30 03:37"),
                                    table=stored)) == 1


def test_yes_price_reads_by_outcome_name():
    assert fv.yes_price({"outcomes": '["No", "Yes"]', "outcomePrices": '["0.7", "0.3"]'}) == 0.3


def test_specs_from_urval():
    qs = fv.load_urval()
    assert qs, "selection file is committed"
    specs = {s.key: s for s in sf.SPECS}
    assert catalog.validate(sf.SPECS) == []
    for q in qs:
        s = specs[sf.key(q)]
        assert s.branch == "G9" and not s.publish  # terms unverified
        assert s.freq == ("D" if q["platform"] == "manifold" else "W")
        assert s.closed == fv.is_closed(q)
        if s.closed:
            assert s.note.startswith("Avslutad:")


def test_committed_urval_meets_the_rule():
    """The file holds metadata only, and every entry meets the thresholds of the rule."""
    doc = json.loads(fv.URVAL_PATH.read_text(encoding="utf-8"))
    assert doc["rule"].startswith("docs/kallor/forvantningar.md")
    fields = {"platform", "id", "title", "topic", "resolution_url", "resolution_source", "created", "close",
              "status", "participation", "participation_unit", "event", "selected_on"}
    per_group: dict[tuple, int] = {}
    for q in doc["questions"]:
        assert set(q) == fields  # no price, probability or median
        assert q["platform"] in ("manifold", "polymarket") and q["topic"] in {c for c, _ in fv.TOPICS}
        assert q["participation"] >= (fv.MIN_BETTORS if q["platform"] == "manifold" else fv.MIN_VOLUME_USD)
        assert fv.topic(q["title"], ai_tag=q["platform"] == "polymarket") == q["topic"]
        per_group[(q["platform"], q["topic"], q["selected_on"])] = per_group.get(
            (q["platform"], q["topic"], q["selected_on"]), 0) + 1
    assert max(per_group.values()) <= fv.CAP
