"""Catalog series that need an API key the owner may not have added yet (docs/drift.md, "Hemligheter").

A series module registers its keys with the environment variable they need:

    keyed.register([s.key for s in SPECS], "CENSUS_API_KEY")

and its fetch calls `keyed.require(env)`. While the variable is not set (environment, .env.local or .env):
- the fetch raises MissingKey before any request, and `observations.refresh` reports SKIPPED, not FAILED. Nothing
  is written, not even a fetch-log row, so a skipped run never counts as a fetch that lacked a period;
- `warehouse.fresh` leaves the series out, so the weekly job does not fail on series it cannot fetch.
Once the variable is set the series are fetched and checked like any other catalog series.
"""

from __future__ import annotations

from ai_tracker import config

# series key -> name of the environment variable its fetch needs
REQUIRES: dict[str, str] = {}


class MissingKey(RuntimeError):
    """The API key a source needs is not configured: the fetch is skipped, not failed."""


def register(keys, env: str) -> None:
    for k in keys:
        REQUIRES[k] = env


def require(env: str) -> str:
    """The key's value, or MissingKey with a message that names the variable (never a value)."""
    value = config.get(env)
    if not value:
        raise MissingKey(f"{env} is not set: fetch skipped (docs/drift.md, Hemligheter)")
    return value


def unconfigured(keys=None) -> set[str]:
    """Registered series (of `keys`, default all) whose key is not set now."""
    keys = REQUIRES if keys is None else [k for k in keys if k in REQUIRES]
    missing = {env for env in {REQUIRES[k] for k in keys} if not config.get(env)}
    return {k for k in keys if REQUIRES[k] in missing}
