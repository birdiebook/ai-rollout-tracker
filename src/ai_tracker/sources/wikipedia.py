"""Wikipedia pageviews (Wikimedia Analytics REST API, no key) for AI products and topics (G3, track B3).

Endpoint: wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{lang}.wikipedia/all-access/user/{title}/daily/
{start}/{end}. Agent "user" (spiders and, from 2020, "automated" traffic excluded), all access methods, daily
from 2015-07-01. One call per title returns the whole history.

Topics and titles are fixed in TOPICS (written 2026-11-23 before any pageviews were fetched; see
docs/kallor/trafik.md). Pageviews are counted under the title that was requested, so a page move splits the
history: views before a move sit under the former title (now a redirect). Each topic therefore sums its current
title and its *former* titles (redirects tagged as moves or former names, checked on 2026-11-23 against the page
source via api.wikimedia.org). Plain alias redirects ("Large language models") are not counted.

Weekly value = sum of daily views over the W-SUN week; a day without a row counts as 0 (the API omits days
without views). Only weeks whose Sunday is covered by the response are kept (no partial last week).

Licence: pageview data is CC0 1.0 (see docs/kallor/trafik.md for the quoted terms).
"""

from __future__ import annotations

import time
from urllib.parse import quote

import pandas as pd
import requests

from ai_tracker import http

SOURCE = "wikipedia"
API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
START = "20150701"  # first day of the pageviews API
LANGS = ("en", "de", "fr", "es", "ja")
OTHER = ("de", "fr", "es", "ja")  # the "xen" series: the four largest non-English editions in this set

http.MIN_INTERVAL.setdefault("wikimedia.org", 1.0)  # shared egress IPs hit Wikimedia's rate limit quickly

# topic -> language -> titles (current title first, then former titles). Fixed before fetching.
TOPICS: dict[str, dict[str, tuple[str, ...]]] = {
    "chatgpt": {"en": ("ChatGPT",), "de": ("ChatGPT",), "fr": ("ChatGPT",), "es": ("ChatGPT",), "ja": ("ChatGPT",)},
    "claude": {"en": ("Claude (AI)", "Claude (language model)"), "de": ("Claude",),
               "fr": ("Claude (modèle de langage)",), "es": ("Claude (chatbot)",), "ja": ("Claude",)},
    "gemini": {"en": ("Google Gemini", "Gemini (chatbot)", "Bard (chatbot)", "Google Bard"),
               "de": ("Google Gemini",), "fr": ("Gemini (intelligence artificielle)",),
               "es": ("Gemini (bot conversacional)",), "ja": ("Gemini (チャットボット)",)},
    "copilot": {"en": ("Microsoft Copilot", "Bing Chat", "Bing AI"), "de": ("Microsoft Copilot",),
                "fr": ("Microsoft Copilot",), "es": ("Microsoft Copilot",), "ja": ("Microsoft Copilot",)},
    "grok": {"en": ("Grok (chatbot)",), "de": ("Grok",), "fr": ("Grok",), "es": ("Grok (chatbot)",), "ja": ("Grok",)},
    "deepseek": {"en": ("DeepSeek",), "de": ("DeepSeek",), "fr": ("DeepSeek",), "es": ("DeepSeek",),
                 "ja": ("DeepSeek",)},
    "perplexity": {"en": ("Perplexity AI",), "de": ("Perplexity AI",), "fr": ("Perplexity AI",),
                   "es": ("Perplexity",), "ja": ("Perplexity",)},
    "llm": {"en": ("Large language model",), "de": ("Large Language Model",), "fr": ("Grand modèle de langage",),
            "es": ("Modelo de lenguaje de gran tamaño",), "ja": ("大規模言語モデル",)},
    "genai": {"en": ("Generative AI", "Generative artificial intelligence"),
              "de": ("Generative künstliche Intelligenz",), "fr": ("Intelligence artificielle générative",),
              "es": ("Inteligencia artificial generativa",), "ja": ("生成的人工知能",)},
    "ai": {"en": ("Artificial intelligence",), "de": ("Künstliche Intelligenz",), "fr": ("Intelligence artificielle",),
           "es": ("Inteligencia artificial",), "ja": ("人工知能",)},
    "openai": {"en": ("OpenAI",), "de": ("OpenAI",), "fr": ("OpenAI",), "es": ("OpenAI",), "ja": ("OpenAI",)},
    "anthropic": {"en": ("Anthropic",), "de": ("Anthropic",), "fr": ("Anthropic",), "es": ("Anthropic",),
                  "ja": ("Anthropic",)},
}


# Product topics count views only from the product's public launch: some current titles are generic words that
# meant something else before (de "Claude" and "Grok" have views from 2015). Fixed with the topic list.
LAUNCH: dict[str, str] = {
    "chatgpt": "2022-11-30", "claude": "2023-03-14", "gemini": "2023-02-06", "copilot": "2023-02-07",
    "grok": "2023-11-04", "deepseek": "2023-07-17", "perplexity": "2022-12-07",
}


def url(lang: str, title: str, end: str) -> str:
    return f"{API}/{lang}.wikipedia/all-access/user/{quote(title.replace(' ', '_'), safe='')}/daily/{START}/{end}"


def parse(payload: dict) -> pd.Series:
    """API payload -> daily views on a DatetimeIndex (days without a row are absent)."""
    items = payload.get("items", [])
    if not items:
        return pd.Series(dtype=float)
    idx = pd.to_datetime([i["timestamp"][:8] for i in items], format="%Y%m%d")
    return pd.Series([float(i["views"]) for i in items], index=idx).groupby(level=0).sum().sort_index()


def _get(u: str, tries: int = 12):
    """http.get, waiting out Wikimedia's 429s as told by Retry-After (shared egress IPs hit the limit often)."""
    for attempt in range(tries):
        try:
            return http.get(u, SOURCE, retries=0)
        except requests.HTTPError as exc:
            resp = exc.response
            if resp is None or resp.status_code != 429 or attempt == tries - 1:
                raise
            try:
                wait = float(resp.headers.get("retry-after", 5))
            except ValueError:
                wait = 5.0
            time.sleep(min(max(wait, 1.0), 60.0) + 0.5)
    raise RuntimeError("unreachable")


def daily(lang: str, title: str, today: pd.Timestamp | None = None) -> pd.Series:
    """Daily user views of one title; a title that does not exist (404) has none."""
    today = pd.Timestamp(today or pd.Timestamp.now(tz="UTC").date()).normalize()
    end = (today - pd.Timedelta(days=1)).strftime("%Y%m%d")
    try:
        r = _get(url(lang, title, end))
    except requests.HTTPError as exc:  # only a 404 means "no views"
        if exc.response is not None and exc.response.status_code == 404:
            return pd.Series(dtype=float)
        raise
    return parse(r.json())


def weekly_sum(days: list[pd.Series]) -> pd.Series:
    """Sum daily series, then W-SUN weeks; keep weeks up to the last covered Sunday (missing days = 0)."""
    days = [d for d in days if len(d)]
    if not days:
        raise ValueError("no pageviews for any title")
    total = pd.concat(days, axis=1).fillna(0).sum(axis=1)
    last = total.index.max()
    full = pd.date_range(total.index.min(), last, freq="D")
    total = total.reindex(full, fill_value=0.0)
    weeks = total.groupby(total.index.to_period("W-SUN")).sum()
    first = pd.Timestamp(START)  # the API starts on a Wednesday: that week is partial
    return weeks[(weeks.index.end_time.normalize() <= last) & (weeks.index.start_time >= first)]


def topic_weekly(topic: str, langs: tuple[str, ...]) -> pd.Series:
    """Weekly views of `topic` summed over the titles of `langs` (Spec.fetch); product topics from LAUNCH."""
    days = [daily(lang, t) for lang in langs for t in TOPICS[topic][lang]]
    if topic in LAUNCH:
        days = [d[d.index >= pd.Timestamp(LAUNCH[topic])] for d in days]
    return weekly_sum(days)
