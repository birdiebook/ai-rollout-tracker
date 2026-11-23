"""Run the warehouse checks on the real observation table, when it has been fetched."""

import pytest

from ai_tracker import observations, warehouse


@pytest.mark.skipif(not observations.PATH.exists(), reason="no data fetched (python -m ai_tracker.observations)")
def test_data_quality():
    failed = {k: df for k, df in warehouse.run_checks().items() if len(df)}
    assert not failed, {k: df.head().to_dict("records") for k, df in failed.items()}


@pytest.mark.skipif(not observations.PATH.exists(), reason="no data fetched (python -m ai_tracker.observations)")
def test_freshness_as_of_last_fetch():
    """No open series past its freshness bound on the day the table was last fetched (not the wall clock)."""
    table = observations.load()
    stale = warehouse.fresh(warehouse.connect(table), table["fetched_at"].max())
    assert stale.empty, warehouse.describe_stale(stale)
