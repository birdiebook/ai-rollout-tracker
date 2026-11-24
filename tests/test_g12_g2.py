"""Track G12, G2 sources: AWS GPU list prices and price at fixed capability per provider. Fixtures only."""

from __future__ import annotations

import pandas as pd
import pytest

from ai_tracker.series import price_capability_provider as pcp
from ai_tracker.sources import aws_gpu

HEADER = ('"SKU","OfferTermCode","RateCode","TermType","PriceDescription","EffectiveDate","Unit","PricePerUnit",'
          '"Currency","Instance Type","Tenancy","Operating System","Pre Installed S/W","CapacityStatus","usageType"')


def _row(term="OnDemand", it="p5.48xlarge", price="98.32", ten="Shared", os_="Linux", sw="NA", cap="Used",
         usage=None):
    return ",".join(f'"{x}"' for x in ["S", "T", "R", term, "d", "2023-12-01", "Hrs", price, "USD", it, ten, os_, sw,
                                       cap, usage or f"BoxUsage:{it}"])


def test_filter_rows_keeps_only_standard_on_demand_linux():
    lines = ['"FormatVersion","v1.0"', '"Disclaimer","x"', '"Publication Date","2023-12-22T04:28:46Z"',
             '"Version","20231222042846"', '"OfferCode","AmazonEC2"', HEADER,
             _row(), _row(it="p4d.24xlarge", price="32.7726"),
             _row(term="Reserved", price="50"), _row(ten="Dedicated", price="110"), _row(os_="RHEL", price="99"),
             _row(sw="SQL Web", price="120"), _row(cap="UnusedCapacityReservation", price="98.32"),
             _row(usage="USE1-BoxUsage:p5.48xlarge", price="1"), _row(it="c5.large", price="0.085")]
    cb = _row(price="0.0").replace('"d"', '"$0.00 per Capacity Block Linux p5.48xlarge Instance Hour"')
    lines.append(cb)
    rows = aws_gpu.filter_rows(lines)
    assert rows == [{"instance_type": "p5.48xlarge", "price_per_hour": 98.32, "effective": "2023-12-01"},
                    {"instance_type": "p4d.24xlarge", "price_per_hour": 32.7726, "effective": "2023-12-01"}]


def test_parse_index_dates_by_publication_id():
    idx = {"versions": {"20230905140324": {"versionEffectiveBeginDate": "2023-08-01T00:00:00Z"},
                        "20230928174545": {"versionEffectiveBeginDate": "2023-09-01T00:00:00Z"}}}
    v = aws_gpu.parse_index(idx)
    assert v["published"].tolist() == [pd.Timestamp("2023-09-05 14:03:24"), pd.Timestamp("2023-09-28 17:45:45")]
    assert v["begin"].iloc[0] == pd.Timestamp("2023-08-01")


def test_events_and_monthly_value_per_gpu():
    from ai_tracker.sources import vintages

    v = pd.DataFrame({"version": ["a", "b", "c"],
                      "published": pd.to_datetime(["2025-05-28 10:00", "2025-06-30 12:00", "2025-07-02 09:00"])})
    rows = {"a": pd.DataFrame({"instance_type": ["p5.48xlarge"], "price_per_hour": [98.32]}),
            "b": pd.DataFrame({"instance_type": ["p5.48xlarge"], "price_per_hour": [55.04]}),
            "c": pd.DataFrame({"instance_type": ["p4d.24xlarge"], "price_per_hour": [21.96]})}
    rows["b"] = pd.concat([rows["b"], pd.DataFrame({"instance_type": ["p5.48xlarge"], "price_per_hour": [0.0]})])
    ev = aws_gpu.events_from(v, rows, "p5.48xlarge")  # the $0 Capacity Block row is ignored
    assert ev["value"].tolist() == [pytest.approx(12.29), pytest.approx(6.88)]
    bad = {"a": pd.DataFrame({"instance_type": ["p5.48xlarge"] * 2, "price_per_hour": [98.32, 90.0]})}
    with pytest.raises(ValueError):
        aws_gpu.events_from(v.iloc[:1], bad, "p5.48xlarge")
    m = vintages.monthly(ev, pd.Period("2025-07", "M"))
    assert m.set_index("period")["value"].round(2).to_dict() == {"2025-05": 12.29, "2025-06": 6.88, "2025-07": 6.88}
    assert m["known_from"].tolist() == [pd.Timestamp(d) for d in ("2025-06-01", "2025-07-01", "2025-08-01")]


def test_provider_table_uses_only_that_provider_and_30_day_runs():
    snaps = pd.DataFrame({
        "snapshot_date": pd.to_datetime(["2025-03-31"] * 3 + ["2025-04-30"] * 3),
        "sha": ["s1"] * 3 + ["s2"] * 3,
        "key": ["o-big", "o-small", "g-cheap"] * 2,
        "provider": ["openai", "openai", "gemini"] * 2,
        "input_per_m": [10.0, 1.0, 0.1] * 2,
        "output_per_m": [40.0, 4.0, 0.4] * 2,
    })
    mapping = pd.DataFrame({"key": ["o-big", "o-small", "g-cheap"], "provider": ["openai", "openai", "gemini"],
                            "model": ["O Big", "O Small", "G Cheap"]})
    rel = pd.Timestamp("2025-01-01")
    gpqa = pd.DataFrame({"model": ["O Big", "O Small", "G Cheap"], "version": ["v1", "v2", "v3"],
                         "organization": ["OpenAI", "OpenAI", "Google"], "release": [rel] * 3,
                         "score": [0.80, 0.78, 0.90],
                         # parse_gpqa's known_from = started + 7; started 2025-03-10 for O Small
                         "known_from": pd.to_datetime(["2025-02-01", "2025-03-17", "2025-02-01"])})
    epoch = {"gpqa": gpqa, "eci": pd.DataFrame(columns=["model", "organization", "release", "eci"])}
    t = pcp.provider_table(snaps, epoch, "openai", pd.Timestamp("2025-05-15"), mapping)
    # March: O Small's run (started 03-10) is known only from 04-09 -> only O Big qualifies
    assert t.loc[pd.Period("2025-03", "M"), "key"] == "o-big"
    assert t.loc[pd.Period("2025-04", "M"), "key"] == "o-small"
    assert t.loc[pd.Period("2025-04", "M"), "value"] == pytest.approx((3 * 1 + 4) / 4)
    assert set(t["key"]) <= {"o-big", "o-small"}  # never the cheaper Gemini model


def test_g2_specs_valid():
    from ai_tracker import catalog
    from ai_tracker.series import aws_gpu as sa

    assert catalog.validate(sa.SPECS + pcp.SPECS) == []
    assert not any(s.publish for s in sa.SPECS)
