"""Shared test setup."""

import pytest

from ai_tracker import observations


@pytest.fixture(autouse=True)
def _no_shared_base(request, monkeypatch):
    """Unit tests never read the shared base table of a track worktree (.env.local); test_shared_data sets its own.

    Tests marked `real_data` check the real observation table and see the full view (shared base + track rows),
    so they give the same answer in a track worktree as on main.
    """
    if request.node.get_closest_marker("real_data"):
        return
    monkeypatch.setattr(observations, "SHARED_DIR", None)


def real_table_exists() -> bool:
    """True when a real observation table is reachable: the shared base or this checkout's own table."""
    shared = observations.SHARED_DIR
    return observations.PATH.exists() or (shared is not None and (shared / "observations.parquet").exists())
