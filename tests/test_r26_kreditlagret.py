"""R26 review of KL1 "Kreditlagret" (docs/granskning/r26_kreditlagret.md). No network.

Evidence was read on 2026-11-25 in the 26 EDGAR documents behind curated/kreditlagret.csv (and Anthropic's last S-1/A
and 424B4), re-fetched from www.sec.gov with R26's own client (generic identity, one request at a time, 0.3 s between
documents; not KL1's cache) and dated with EDGAR's submissions API. Only ids, numbers, dates, accession numbers and
hashes are kept here, never filing text.

- Pinned: the register entry and its addendum (unchanged since 4bcb077 and 60af26f) and the 394 reviewed rows that
  were found correct (all fields but the note). A change to a pinned row must be reviewed again; new rows are not
  pinned and need their own review.
- Properties that hold: the registered limits equal the code, the reading's truth table, licence class and publish
  flag, an independent recomputation of three derived series from their components (real data).
- Findings R26-1 to R26-9 are strict xfail. Each flips (XPASS -> failure) when the finding is fixed; then remove the
  marker and keep the assertion.
"""

from __future__ import annotations

import hashlib
import math
import re

import pandas as pd
import pytest

from ai_tracker import catalog, config, licenses
from ai_tracker.followed import kreditlagret as F
from ai_tracker.sources import kreditlagret as kl

REGISTER = config.REPO / "docs" / "mattregister.md"
RESULTS = config.REPO / "docs" / "resultat" / "kreditlagret.md"
SKIPPED = config.REPO / "curated" / "kreditlagret_skipped.csv"
REVIEW_DAY = "2026-11-25"
ENTRY_SHA256 = "287a4ea26953850dc25d368706bdc96c03e3a82f34abedc0f4978d045b0b03b2"  # = 4bcb077
ADDENDUM_SHA256 = "4e4866c842eca9c7164959d7a76c57bf688d38dca13cc688d13cd49ef92ab72a"  # = 60af26f
FINDING_ROWS = {  # rows of R26-1 and R26-2, not pinned (they must change)
    "anthropic_amazon_2023_npa_notes-2026-09-30-outstanding", "anthropic_amazon_2024_npa_notes-2026-09-30-outstanding",
    "anthropic_amazon_npa_2026-2026-09-30-commitment", "anthropic_broadcom_npa_2026-2026-09-30-commitment",
    "anthropic_google_npa_2026-2026-09-30-commitment", "crwv_2031_9_75_senior_notes-2026-04-14-principal",
}
S1 = "0001628280-26-067168"  # Anthropic S-1, 2026-10-26: its NPA tables are "As of June 30, 2026"
S1A1_FILED = "2026-11-02"  # the first document with the tables as of September 30, 2026
META_Q1_Q2_2026 = ("0001628280-26-028526", "0001628280-26-050705")  # maximum exposure 45.99 and 46.03 bn, not coded
_REVIEWED_DIGESTS = """
002674eebfae 0062f2f914be 02c627b43954 02cae8f605b8 03439a6955c2 04fabe5a741d 050cb028461f 05178ca9fa9f 056ec026339d
057ed34e1cf7 05da8c5dcf69 0705f197292b 07ecd4a17118 099dd6fdd9d4 09b482b053a2 0ac901160f78 0aeb21f64239 0b1b98dd98ea
0c9655b314b1 0c9e814e5537 0ec8cc2f8813 0ee565884f41 0ef49fe41def 0f65393b13ae 0f798c70e9d5 0fbf5ba0288c 0fefd1dd0ccf
1026b635b5c4 1046d5e336fd 10b202084113 1109c511982f 12590f982de0 12a042c2b386 139db8e0df6f 147c0b46b430 149ff199af61
150b8790c839 18e3ab041967 18ee8b8374ed 1a07e08b84d9 1a77cecb6be8 1c154e2297ad 1cab5b80e01d 1d621c09c3c0 1d8bf6577e01
1e05b93c294e 20f3851f285f 214aaccd0be4 21c274a8e291 223ad5aa748c 22b58ca1db95 2382c860d958 23e7f0eb158f 245265b32878
24f5b7a28ed5 25821ef7dfd4 264a618b1cd1 2717e1bc9c35 274181a517c1 27eb8f7a8b37 2843e8a84e98 28b28e6d7c40 28fac0cde84f
293b5ea61a8b 297301702f32 29f373f79c5d 2a067086e494 2a1f442eb714 2a539c7ccef1 2ae93bbf6f3f 2b0ab17c69b2 2b54036cab80
2b96e6020052 2bc88bf7c84d 2c0f1ee39142 2d8cc523d83b 2dcf6761c5eb 2e2ecd71f1ff 2ec8a5053c8a 2f0f92786a3b 30e95a78f095
314c4c16fda1 3172168e2d80 3190c64930fa 32a4a066c7bc 3340e185c0e5 3489f2b06335 35223caf6d20 361e2e1d1b92 384a990031d9
385008170f73 389dd8083e49 38d7f6b72f4f 390a2f783e91 39f5470c1bac 3bb0058847ce 3d6b8963c43d 3debe5272979 3e34da8cdcda
3f0aa3a521a0 3f1b07314ecd 3f1fa40274ff 40f7e1fd17d3 411cffac8630 426c02445bdb 426c213f3d9c 42b715339ca9 4300df625136
434458e0170a 438130505179 43af754e2151 43d75f2d3e2c 43f59ee26c6f 45739d13c68e 46b927d79062 477fd24085c6 4791902f5f20
497f7f73d78c 49a348c01aab 49b18b247804 4ab0627721d2 4ba608088af7 4bb3f848332d 4bd53727b73d 4be8786f2fd5 4c933788a3e9
4cd79d630a2d 4ce614e91e58 4f2dafbc1e74 4f3a9717d701 4fd22ee85800 50156250dbaf 50a2270eeca6 50e34ae9d8d0 515f987449d5
522e43505394 52ca16107699 5319be905f76 53feaa3e2600 54991cc5ca36 55182fd7e69d 5574da6e013e 55accd3d3a21 55f7ff842335
5625a7854e81 575179a96c34 5766f0dc42cd 586a3e5efcb1 59416f2fda9b 59c9496918b6 5a7a3f7681ed 5c44669d0554 5ca583c764b7
5ceef539d92b 5d110509927c 5d25a7020ada 5d420948d967 5d803186938e 5e84c56b6cf4 5e9df1605e6c 5f1bbed15042 5ffa9016209c
600d0cba944d 604967032de2 6132d87911ba 6135145c0fcd 620cf6dac3ba 626309466a78 626eee32b54d 66b556ba5883 679566593d52
6a5eaa5f0865 6ae588d6e593 6c0069afda3c 6c5120005562 6dee071d0c1a 6e09ebbc42e7 6f4b2dbf6060 6fa1548cb73e 70e4ec834e4f
712303d4fd16 718e23bb6e52 71a128e794de 7334089eee8b 7370dd7c42a1 74e00e7e1019 7515d6e37bf9 75c70ba84af0 7624c7bbd640
77c772d71ea9 7872693286a8 78bce9ce5969 7913cd6223ba 79311fa17f25 79eaedc042d7 7a6bfc97c3ce 7b3b0c2d48e3 7b6141c29521
7bdec7d43742 7be8310d5aa2 7c0d27017a12 7e1fce11d98e 7ec234cf2a02 7ef6cbe447c1 7f4dfda9a94d 80357cbf5e09 81fa6bb28487
82146c5d1c93 82bfc986dc89 844daf3cf679 8513a3813ff3 8552758f4415 85689388f470 85e6dd1b6b38 85eb2ada7ced 863716d15fe4
863c4699560d 87dfdea8af68 87e6f8b50950 880732d24582 8864545a0aeb 8a2c3ea5d3a5 8ad819a02609 8b6b7297d12f 8dfc2c00e8ab
8e3f0c62594c 8eb827df61cb 8ec3a98eb6fa 8ee7cf1404f5 8f5f3719dcc2 8ff5a6e68554 9038726e889d 904dd7319d10 90f4e7d98fd3
919a869d33e6 91fb967f2285 93327e9421ee 934cddd24f8a 937cd11510cf 93d13d67a1a6 943b21f53cdf 95570e0554d8 95eb819ed27b
96d868f20a24 972a2efaa739 9744c6f4b246 97b0f55e81af 98161d1a0c36 9892c5c3a7f3 993bff93d7c8 9982c514cfc7 9b8d76a9130c
9cbd7a83f14b 9eb3148e9dc2 a0251507aeb5 a02d00f02fd8 a038d07c43eb a03dab8c1a29 a1f1e4d2f3f4 a361cb85c11d a361e5f36eb0
a58b8de8ba11 a59ff09e1b84 a5dc2edaee12 a61d30050432 a72054972c01 a806f9961038 a8e69ebfaa97 aacceb779c08 aad51948181e
aaea5fc08824 ac08fa3b15a2 ac2b9ddb64ca ad05dea0baa7 ad3566b4815f ad6116e0357e afc6315c0846 b0455005efe4 b04aac5097da
b0ded75ab322 b13bd2f6525b b1ab11f16423 b1c74a1f8772 b1f8f46ab06a b26373e8ee87 b27ec12baea8 b28f24aec684 b435f97d5048
b4a449ebd00d b52627b23b3a b57e8ecfbcca b636ed8680a9 b738539305e3 b8072368bb7d b84f80bb7aa1 b8649c3e085b b9875ffe369a
b9e47eb64fb9 bc0e294ce43d be5b79d214c9 bef5a37eee1a bfbec706c13f bfd56f36302e bff5327c112a c021ce9a82fe c05298e50ea5
c101c0ed0f7c c135384006e5 c17cb28b228c c2f3d2390e18 c36111b91974 c365045ab3da c448ad208fd9 c4c3d0565b93 c54ac2157c96
c63a706a6286 c701a0d5b84b c86e2d9261ab c8ecf7ef3a24 cad134e3f6e8 cb36f225f4f1 cb92220490ea ccccb08ce781 cdacc8de66a2
cdfb8eb5999c cf6d4d0c3c52 cf8a7e3e7a82 cfa04468a222 cfb5964c91d9 d0091b5e5a99 d067525f46df d10c5304363c d13d8f298c37
d15032d58400 d2a5bd89412d d350f5dbbbc1 d4ae91d3b08c d82b958be819 d87392c930fd d881dd2dcc2c d8df97458712 d94dd89d14d7
d970931669d9 d9afcc04604a da6ff6c908d0 da8a703b9776 dabf8d36a3b9 db72f9ae44b0 dc58f66e26fe de3d1a3e0d17 de5790b1c401
dec50bb10b28 df28ddff9c54 df6bd9773a3d e04670c934e0 e0edc492c05c e27ea29fc079 e2cfc58cd004 e352161c8dc9 e35ec293a7b5
e39046564d49 e456cc7a4b6f e45ecb186337 e4c6706beb15 e6122e756d89 e70d5ba1519b e8013d6c4e50 e8bf3dc49e6d e92d77c740e4
eb7c1b634dbd ebcdbd0141c9 ec2fb33478f8 ed1027b3858a ed3972322614 ef0184213f85 eff7a1a4655e f0290a79b3f3 f178f9ae569e
f2d0f6366d25 f35a62959662 f474ada444c7 f4ca0eba837c f4d353072191 f4ddff6eca79 f59036a04d68 f7015212ad4f f80d61d904dc
f84e759cfc30 f907ffb2b709 f96203eeaa16 fd72d4c8ec77 fd8eb148be7a fe9bc0088ea3 fff05920b943
"""  # 12-hex SHA-256 prefix per reviewed row (all fields but the note)
REVIEWED = frozenset(_REVIEWED_DIGESTS.split())


@pytest.fixture(scope="module")
def csv() -> pd.DataFrame:
    return kl.load()


def _section(text: str, start: str) -> str:
    a = text.index(start)
    b = text.find("\n### ", a + len(start))
    return (text[a:b] if b > 0 else text[a:]).strip()


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ pinned (point 1 and 2)


def test_register_entry_and_addendum_are_unchanged_since_the_lock():
    text = REGISTER.read_text(encoding="utf-8")
    assert _sha(_section(text, "### 2026-11-25 – KL1: följd fråga")) == ENTRY_SHA256
    assert _sha(_section(text, "### 2026-11-25 – KL1 (tillägg)")) == ADDENDUM_SHA256


def _row_digest(r) -> str:
    return hashlib.sha256("|".join(r).encode("utf-8")).hexdigest()[:12]


def test_reviewed_rows_are_unchanged(csv):
    """Every row R26 found correct is still there with the same fields (the note aside). New rows are not pinned."""
    cols = [c for c in kl.COLUMNS if c != "note"]
    now = {_row_digest(r) for r in csv[cols].itertuples(index=False)}
    assert len(REVIEWED) == 394
    assert REVIEWED <= now, f"{len(REVIEWED - now)} reviewed rows changed or removed: review them again"


def test_no_quote_text_in_the_csv(csv):
    assert csv["note"].str.len().max() <= 200
    assert not csv["note"].str.contains("“|”").any()


# ------------------------------------------------------------------ properties that hold (points 3-5)


def test_registered_limits_equal_the_code():
    entry = _section(REGISTER.read_text(encoding="utf-8"), "### 2026-11-25 – KL1: följd fråga")
    assert "takt ≥ +0,25" in entry and "takt ≥ +5 procentenheter" in entry
    assert "≤ −5 log × 100" in entry and "inre ≤ 0,5 × yttre" in entry
    assert (F.RATE_RISE, F.DEP_RISE, F.CAPEX_FALL, F.EQUAL_SHARE) == (0.25, 5.0, -5.0, 0.5)


@pytest.mark.parametrize("a,d_out,d_in,want", [
    (True, -5.0, -4.9, "stoder"),  # the limits are inclusive for the outer fall
    (True, -4.99, 0.0, "emot_1"),
    (True, -10.0, -5.0, "emot_2"),  # -5 <= 0.5 x -10: equal fall, with A
    (None, -10.0, -5.0, "emot_2"),  # and without A
    (True, -10.0, -4.99, "stoder"),
    (True, -20.0, -9.0, "blandat"),
    (False, -20.0, 30.0, "inget"),
    (False, None, 3.0, "kan_inte_avgoras"),
    (True, None, 3.0, "kan_inte_avgoras"),
])
def test_reading_follows_the_register_at_the_limits(a, d_out, d_in, want):
    assert F.reading(a, d_out, d_in) == want


def test_kl_series_are_withheld_and_commercial_class_ja():
    specs = [s for s in catalog.ALL if s.key.startswith("kl_")]
    assert len(specs) == 53 and not any(s.publish for s in specs)
    assert {licenses.classify(s)[0] for s in specs} == {"ja"}
    assert catalog.validate(specs) == []


def _latest(table: pd.DataFrame, key: str) -> pd.Series:
    t = table[table["series"] == key].sort_values("known_from")
    return t.groupby("period")["value"].last()


def _p(p: str, k: int) -> str:
    return str(pd.Period(p, freq="Q-DEC") - k)


@pytest.fixture(scope="module")
def real():
    from ai_tracker import observations

    t = observations.load()
    if t.empty or "kl_capex4_orcl" not in set(t["series"]):
        pytest.skip("no real observation table with the KL1 series")
    t = t.copy()
    t["known_from"] = pd.to_datetime(t["known_from"])
    return t[t["known_from"] <= pd.Timestamp(REVIEW_DAY)]


@pytest.mark.real_data
def test_three_derived_series_equal_an_independent_recomputation(real):
    cap, ocf = _latest(real, "capex_orcl"), _latest(real, "ocf_crwv")
    capc = _latest(real, "capex_crwv")
    ie, ltd = _latest(real, "interest_exp_msft"), _latest(real, "lt_debt_msft")
    got = {k: _latest(real, k) for k in ("kl_capex4_orcl", "kl_fcfgap_crwv", "kl_rate_eff_msft")}
    for p, v in got["kl_capex4_orcl"].items():
        assert math.isclose(v, sum(cap[_p(p, k)] for k in range(4)), rel_tol=1e-9), p
    for p, v in got["kl_fcfgap_crwv"].items():
        c = sum(capc[_p(p, k)] for k in range(4))
        assert math.isclose(v, 100 * (c - sum(ocf[_p(p, k)] for k in range(4))) / c, rel_tol=1e-9), p
    for p, v in got["kl_rate_eff_msft"].items():
        want = 100 * sum(ie[_p(p, k)] for k in range(4)) / (0.5 * ltd[_p(p, 4)] + 0.5 * ltd[p])
        assert math.isclose(v, want, rel_tol=1e-9), p


@pytest.mark.real_data
def test_nothing_is_dated_after_the_review_day_or_before_its_inputs(real):
    kl_rows = real[real["series"].str.startswith("kl_")]
    assert kl_rows["known_from"].max() <= pd.Timestamp(REVIEW_DAY)
    for key in ("kl_capex4_outer", "kl_fcfgap_outer"):
        first = real[real["series"] == key]["known_from"].min()
        iren = real[(real["series"] == "capex_iren") & (real["period"] == "2025Q2")]["known_from"].min()
        assert first >= iren  # the outer layer exists only once IREN has four quarters


@pytest.fixture(scope="module")
def report(real, csv):
    return F.compute(REVIEW_DAY, real, csv)


@pytest.fixture(scope="module")
def text(report):
    return F.render(report)


def _part(text: str, start: str, stop: str) -> str:
    a = text.index(start)
    b = text.find(stop, a + len(start))
    return text[a:b] if b > 0 else text[a:]


@pytest.mark.real_data
def test_report_reading_and_caveats_as_registered(report, text):
    assert {e: r["outcome"] for e, r in report["readings"].items()} == {
        "outer": "kan_inte_avgoras", "orcl": "stoder", "crwv": "emot_1", "nbis": "inget", "iren": "kan_inte_avgoras"}
    caveats = _part(text, "## 7. Förbehåll", "\n## ")
    assert "beskrivning och inget test" in caveats and "slump" in caveats and "aktiverad ränta" in caveats


# ------------------------------------------------------------------ findings (strict xfail until fixed)


@pytest.mark.xfail(strict=True, reason="R26-1 (must_fix): five rows dated 2026-09-30 come from the S-1, which states "
                   "them as of June 30, 2026")
def test_r26_1_september_balances_are_not_dated_to_the_june_s1(csv):
    ant = csv[(csv["company"] == "anthropic") & (csv["period"] == "2026-09-30")]
    assert not (ant["accession"] == S1).any()
    assert (ant["filed"] >= S1A1_FILED).all()


@pytest.mark.xfail(strict=True, reason="R26-2 (must_fix): the 9.750% 2031 notes are coded as 1.75 MUSD; the 8-K of "
                   "2026-04-21 states $1,750,000,000")
def test_r26_2_coreweave_9_75_notes_principal(csv):
    p = csv[(csv["instrument"] == "crwv_2031_9_75_senior_notes") & (csv["field"] == "principal")]
    assert len(p) == 1
    r = p.iloc[0]
    assert float(r["value"]) == 1750.0 and r["filed"] <= "2026-04-21"  # stated in the 8-K 0001769628-26-000183
    crwv = csv[(csv["company"] == "crwv") & (csv["field"] == "principal")]
    assert (crwv["value"].astype(float) >= 100).all()
    assert "1,75 MUSD" not in "\n".join(F._lab_lines(F.extraction(REVIEW_DAY, csv)["rows"]))


@pytest.mark.xfail(strict=True, reason="R26-3 (should_fix): SpaceX (xAI since 2026-02-02) has an S-1, a 424B4 and "
                   "10-Qs on EDGAR, and the lab section does not say so")
def test_r26_3_lab_section_names_spacex_xai(csv):
    lab = "\n".join(F._lab_lines(F.extraction(REVIEW_DAY, csv)["rows"]))
    assert re.search(r"SpaceX|xAI", lab)


@pytest.mark.xfail(strict=True, reason="R26-4 (should_fix): candidate lines that are not coded are not counted or "
                   "listed with a reason (register, 'Kandidatrader')")
def test_r26_4_uncoded_candidates_are_listed_with_a_reason(csv):
    sk = pd.read_csv(SKIPPED, dtype=str, keep_default_na=False)
    assert {"accession", "locator", "reason"} <= set(sk.columns) and len(sk) > 0
    for acc in META_Q1_Q2_2026:  # the venture's maximum exposure: coded, or listed with the reason
        assert (csv["accession"] == acc).any() or (sk["accession"] == acc).any()


@pytest.mark.real_data
@pytest.mark.xfail(strict=True, reason="R26-5 (should_fix): CoreWeave's weighted rate falls mostly by the mix of "
                   "convertibles, and the report does not say so")
def test_r26_5_coreweave_rate_states_the_convertible_mix(text):
    line = next(x for x in text.splitlines() if x.startswith("CoreWeave, angiven effektiv ränta"))
    assert re.search(r"(?i)konvertib", line)


@pytest.mark.real_data
@pytest.mark.xfail(strict=True, reason="R26-6 (should_fix): Microsoft's interest expense includes interest on finance "
                   "leases (10-K FY2026: 2,547 of 3,051 MUSD), not said in the report")
def test_r26_6_effective_rate_caveat_names_lease_interest(text):
    price = _part(text, "## 1. Pris på skuld", "## 2.")
    assert re.search(r"(?i)leasing", price)


@pytest.mark.xfail(strict=True, reason="R26-7 (should_fix): the readings per 2026-11-25 use quarters that were seen "
                   "before the register entry, and the results do not say so")
def test_r26_7_results_say_the_first_readings_are_on_seen_data():
    res = RESULTS.read_text(encoding="utf-8")
    assert re.search(r"(?i)(sett|sedd|sedda|tittade)[^.\n]{0,120}(före|innan)[^.\n]{0,60}(post|regist)", res)


@pytest.mark.real_data
@pytest.mark.xfail(strict=True, reason="R26-8 (should_fix): the rule reads only rises in price or dependence, and A "
                   "held in 28 of 35 Oracle quarters since 2018; the report says neither")
def test_r26_8_reading_states_its_direction_and_how_often_a_holds(text):
    rule = _part(text, "## 4. Läsregeln", "## 5.")
    assert re.search(r"(?i)(bara|endast)[^.\n]{0,80}(stig|uppgång|åtstram)", rule)
    assert re.search(r"\d+ av \d+", rule)


@pytest.mark.xfail(strict=True, reason="R26-9 (should_fix): the lab lines show Google's pre-IPO 9 % coupon and "
                   "DDTL 2.0's pre-amendment 13 % margin without saying so")
def test_r26_9_lab_lines_qualify_coupon_and_margin(csv):
    lab = F._lab_lines(F.extraction(REVIEW_DAY, csv)["rows"])
    google = next(x for x in lab if "ram Google 2026" in x)
    assert "kupong" not in google or re.search(r"(?i)före (börs)?notering|före IPO", google)
    margins = next(x for x in lab if x.startswith("- CoreWeave, marginal"))
    m = re.search(r"ddtl 2 0 facility 1 300[^,]*", margins)
    assert m is None or "före" in m.group(0)
