"""Weekly snapshots of first-party API list prices, straight from the model developers (G2, track B5).

Independent of LiteLLM: the price is read from the developer's own pricing publication, and our snapshot
date is the only date we claim (no history before the first snapshot).

A developer is collected only where it publishes machine-readable pricing, or a pricing page whose terms
allow automated access, and the host is reachable with the honest client (ai_tracker.http). Every
developer is listed in PROVIDERS with its status as checked; BLOCKED ones have no parser and are never
fetched (no mirrors, no workarounds). docs/kallor/priser.md has the checks, robots.txt and terms quotes.

Store: data/raw/firstparty_prices/snapshots.parquet (never committed), one row per (snapshot, model, tier):
snapshot_date (UTC date), fetched_at (UTC), developer, model (name as published), tier, base_tier,
availability, input_per_m, output_per_m (USD per 1M tokens), url, sha256 (of the raw page; the raw copy is
saved by ai_tracker.http under RAW_DIR/firstparty_prices/<date>/). A (snapshot_date, developer) pair is
written once: a second run the same day does not refetch.

`python -m ai_tracker.sources.firstparty_prices` takes today's snapshot and prints the LiteLLM cross-check.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from ai_tracker import config, http

SOURCE = "firstparty_prices"
STORE = config.REPO / "data" / "raw" / SOURCE / "snapshots.parquet"
COLUMNS = ["snapshot_date", "fetched_at", "developer", "model", "tier", "base_tier", "availability",
           "input_per_m", "output_per_m", "url", "sha256"]
LITELLM_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"


# ---------------------------------------------------------------------------------------------- Anthropic

_PRICE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*MTok")
_TIER = re.compile(r"\((for prompts [^)]*)\)", re.I)
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


class ParseError(ValueError):
    """The published page no longer has the layout the parser was written for: fail, never guess."""


def _price(cell: str) -> float:
    m = _PRICE.search(re.sub(r"<sup>.*?</sup>", "", cell))
    if not m:
        raise ParseError(f"no '$x / MTok' price in cell {cell!r}")
    return float(m.group(1))


def parse_anthropic(md: str) -> pd.DataFrame:
    """Rows of the "Model pricing" table on platform.claude.com/docs/en/about-claude/pricing.md.

    Columns model, tier, base_tier, availability, input_per_m, output_per_m. `availability` is "retired"
    or "limited" when the name cell says so (link text such as "retired, except on ..." or "limited
    availability"), else "available". A model with prompt-length tiers ("for prompts up to 100,000 tokens")
    has one row per tier; the first listed tier is the base tier (the standard price, as in LiteLLM).
    """
    start = md.find("## Model pricing")
    if start < 0:
        raise ParseError("section '## Model pricing' not found")
    lines = md[start:].splitlines()
    head = next((i for i, line in enumerate(lines) if line.startswith("| Model |")), None)
    if head is None:
        raise ParseError("model pricing table header not found")
    cols = [c.strip() for c in lines[head].strip().strip("|").split("|")]
    try:
        i_in, i_out = cols.index("Base input tokens"), cols.index("Output tokens")
    except ValueError as exc:
        raise ParseError(f"unexpected columns {cols}") from exc
    rows, seen = [], set()
    for line in lines[head + 2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(cols):
            raise ParseError(f"row with {len(cells)} cells, header has {len(cols)}: {line!r}")
        name_cell = cells[0]
        links = " ".join(_LINK.findall(name_cell)).lower()
        tier_m = _TIER.search(name_cell)
        name = _TIER.sub("", _LINK.sub("", name_cell))
        name = re.sub(r"\(\s*\)", "", name).strip()
        availability = "retired" if "retired" in links else "limited" if "limited" in links else "available"
        inp, outp = _price(cells[i_in]), _price(cells[i_out])
        if not 0 < inp <= outp:
            raise ParseError(f"implausible prices for {name}: {inp} / {outp}")
        rows.append((name, tier_m.group(1) if tier_m else "", name not in seen, availability, inp, outp))
        seen.add(name)
    if not rows:
        raise ParseError("model pricing table has no rows")
    return pd.DataFrame(rows, columns=["model", "tier", "base_tier", "availability", "input_per_m", "output_per_m"])


# ---------------------------------------------------------------------------------------------- registry


@dataclass(frozen=True)
class Provider:
    developer: str
    status: str  # "OK" (collected) or "BLOCKED" (never fetched)
    url: str  # the pricing publication (for BLOCKED: the one we tried)
    checked: str  # date of the access check
    reason: str  # one line: why OK / why BLOCKED (full quotes in docs/kallor/priser.md)
    parser: Callable[[str], pd.DataFrame] | None = None
    litellm_provider: str = ""  # first-party provider in LiteLLM (model_map.FIRST_PARTY), for the cross-check


_PROXY = "host refused by the sandbox proxy (403 at CONNECT, 'no rule or network setting allows this host')"
PROVIDERS: dict[str, Provider] = {
    "anthropic": Provider(
        "anthropic", "OK", "https://platform.claude.com/docs/en/about-claude/pricing.md", "2026-11-23",
        "machine-readable Markdown pricing page listed in platform.claude.com/llms.txt; robots.txt allows all "
        "but /api/", parse_anthropic, "anthropic"),
    "openai": Provider("openai", "BLOCKED", "https://platform.openai.com/docs/pricing", "2026-11-23",
                       f"openai.com, platform.openai.com: {_PROXY}", litellm_provider="openai"),
    "google": Provider("google", "BLOCKED", "https://ai.google.dev/gemini-api/docs/pricing", "2026-11-23",
                       f"ai.google.dev: {_PROXY}", litellm_provider="gemini"),
    "deepseek": Provider("deepseek", "BLOCKED", "https://api-docs.deepseek.com/quick_start/pricing", "2026-11-23",
                         f"api-docs.deepseek.com: {_PROXY}", litellm_provider="deepseek"),
    "mistral": Provider("mistral", "BLOCKED", "https://mistral.ai/pricing", "2026-11-23",
                        f"mistral.ai, docs.mistral.ai: {_PROXY}", litellm_provider="mistral"),
    "xai": Provider("xai", "BLOCKED", "https://docs.x.ai/docs/models", "2026-11-23",
                    f"docs.x.ai, x.ai: {_PROXY}", litellm_provider="xai"),
}


def collected() -> list[Provider]:
    return [p for p in PROVIDERS.values() if p.status == "OK"]


# ---------------------------------------------------------------------------------------------- store


def load(store=STORE) -> pd.DataFrame:
    if not store.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_parquet(store)
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    return df


def snapshot_rows(provider: Provider, text: str, fetched_at: datetime) -> pd.DataFrame:
    """Parsed rows of one fetched page, with the snapshot metadata."""
    rows = provider.parser(text)
    utc = _utc_naive(fetched_at)
    return rows.assign(snapshot_date=utc.normalize(), fetched_at=utc, developer=provider.developer,
                       url=provider.url, sha256=hashlib.sha256(text.encode()).hexdigest())[COLUMNS]


def _utc_naive(when) -> pd.Timestamp:
    """UTC wall time without tz (a naive input is taken as UTC)."""
    t = pd.Timestamp(when)
    return t.tz_convert("UTC").tz_localize(None) if t.tzinfo else t


def take_snapshot(store=STORE, providers: list[Provider] | None = None, now: datetime | None = None,
                  get=None) -> dict[str, str]:
    """Fetch every collected developer once for today's UTC date and append to the store.

    Returns status per developer. A developer already in the store for today is skipped; a failing one
    (HTTP or ParseError) is reported and the others continue. `get(url) -> str` is injectable for tests.
    """
    now = now or datetime.now(timezone.utc)
    day = _utc_naive(now).normalize()
    get = get or (lambda url: http.get(url, SOURCE).text)
    old = load(store)
    have = set(zip(old["snapshot_date"], old["developer"])) if len(old) else set()
    new, status = [], {}
    for p in providers if providers is not None else collected():
        if (day, p.developer) in have:
            status[p.developer] = "already taken today"
            continue
        try:
            rows = snapshot_rows(p, get(p.url), now)
        except Exception as exc:  # noqa: BLE001 - report and continue
            status[p.developer] = f"FAILED: {type(exc).__name__}: {str(exc)[:160]}"
            continue
        new.append(rows)
        status[p.developer] = f"ok {len(rows)} rows"
    if new:
        out = pd.concat([old, *new], ignore_index=True) if len(old) else pd.concat(new, ignore_index=True)
        store.parent.mkdir(parents=True, exist_ok=True)
        tmp = store.with_suffix(".tmp")
        out.to_parquet(tmp, index=False)
        tmp.replace(store)
    return status


# ---------------------------------------------------------------------------------------------- cross-check


def litellm_key_candidates(model: str) -> list[str]:
    """LiteLLM first-party key(s) for a published Anthropic model name: the MODEL_MAP keys when the name is
    an Epoch model there, else the name in LiteLLM's convention ("Claude Opus 5.5" -> "claude-opus-5-5")."""
    from ai_tracker.sources import model_map

    if model in model_map.MODEL_MAP:
        return list(model_map.MODEL_MAP[model][1])
    return [re.sub(r"[\s.]+", "-", model.strip().lower())]


def crosscheck(firstparty: pd.DataFrame, litellm_rows: list[tuple[str, str, float, float]],
               provider: str = "anthropic", rtol: float = 0.005) -> pd.DataFrame:
    """Level check: base-tier first-party price per model vs LiteLLM's price for its key(s).

    `litellm_rows` = litellm_prices.extract(file). Status per (model, key): "match", "mismatch",
    "missing in LiteLLM". Retired models are included (LiteLLM may still list them).
    """
    lite = {k: (i, o) for k, p, i, o in litellm_rows if p == provider}
    out = []
    for r in firstparty[firstparty["base_tier"]].itertuples(index=False):
        for key in litellm_key_candidates(r.model):
            if key not in lite:
                out.append((r.model, r.availability, key, r.input_per_m, r.output_per_m, None, None,
                            "missing in LiteLLM"))
                continue
            li, lo = lite[key]
            ok = abs(li - r.input_per_m) <= rtol * r.input_per_m and abs(lo - r.output_per_m) <= rtol * r.output_per_m
            out.append((r.model, r.availability, key, r.input_per_m, r.output_per_m, li, lo,
                        "match" if ok else "mismatch"))
    return pd.DataFrame(out, columns=["model", "availability", "key", "fp_input", "fp_output", "litellm_input",
                                      "litellm_output", "status"])


def litellm_current() -> list[tuple[str, str, float, float]]:
    from ai_tracker.sources import litellm_prices

    return litellm_prices.extract(http.get(LITELLM_URL, "litellm_current", timeout=120).json())


if __name__ == "__main__":
    for dev, st in take_snapshot().items():
        print(f"{dev:10s} {st}")
    for p in PROVIDERS.values():
        if p.status != "OK":
            print(f"{p.developer:10s} BLOCKED ({p.reason})")
    store = load()
    if len(store):
        latest = store[store["snapshot_date"] == store["snapshot_date"].max()]
        cc = crosscheck(latest[latest["developer"] == "anthropic"], litellm_current())
        print(cc.to_string(index=False))
