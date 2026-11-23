"""Shared test setup."""

import pytest

from ai_tracker import observations


@pytest.fixture(autouse=True)
def _no_shared_base(monkeypatch):
    """Tests never read the shared base table of a track worktree (.env.local); test_shared_data sets its own."""
    monkeypatch.setattr(observations, "SHARED_DIR", None)
