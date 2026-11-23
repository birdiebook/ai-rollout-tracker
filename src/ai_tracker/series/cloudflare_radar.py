"""Cloudflare Radar: AI bot and crawler traffic shares, weekly (G3, track B3).

See sources/cloudflare_radar.py and docs/kallor/trafik.md. All values are shares in per cent of a Radar
distribution (normalization PERCENTAGE), so they do not change when the request window changes. Data begins
2024-01 (bot categories) or 2025-01 (AI bot and crawler datasets); the API refuses dates before 2021-12-27 and
pads earlier weeks with zeros, which are dropped.
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import cloudflare_radar as cf
from ai_tracker.sources.cloudflare_radar import Query

_PCT = {"normalization": "PERCENTAGE"}
_CRAWLERS = "/bots/crawlers/timeseries_groups/CLIENT_TYPE"
_PURPOSE = "/ai/bots/timeseries_groups/CRAWL_PURPOSE"
_AGENT = "/ai/bots/timeseries_groups/USER_AGENT"
_CATEGORY = "/bots/timeseries_groups/BOT_CATEGORY"
_AGENTS = {**_PCT, "limitPerGroup": 40}  # high enough that the named agents never fall into "other"

# key -> (query, Swedish label, question)
_DEFS: dict[str, tuple[Query, str, str]] = {
    "g3_cf_html_ai_bot_share": (
        Query(_CRAWLERS, "AI_BOT", _PCT),
        "Cloudflare Radar: andel av HTML-förfrågningar från AI-botar",
        "Hur stor del av webbtrafiken till HTML-sidor kommer från AI-botar?"),
    "g3_cf_html_mixed_bot_share": (
        Query(_CRAWLERS, "MIXED_PURPOSE", _PCT),
        "Cloudflare Radar: andel av HTML-förfrågningar från botar med blandat syfte (t.ex. Googlebot)",
        "Hur stor del av webbtrafiken kommer från botar som både söker och matar AI?"),
    "g3_cf_ai_purpose_training": (
        Query(_PURPOSE, "Training", _PCT),
        "Cloudflare Radar: andel av AI-botarnas förfrågningar för träning",
        "Hur stor del av AI-botarnas trafik samlar träningsdata?"),
    "g3_cf_ai_purpose_search": (
        Query(_PURPOSE, "Search", _PCT),
        "Cloudflare Radar: andel av AI-botarnas förfrågningar för AI-sök",
        "Hur stor del av AI-botarnas trafik indexerar för AI-sök?"),
    "g3_cf_ai_purpose_user_action": (
        Query(_PURPOSE, "User Action", _PCT),
        "Cloudflare Radar: andel av AI-botarnas förfrågningar på uppdrag av en användare",
        "Hur stor del av AI-botarnas trafik är hämtningar som en användare har bett om?"),
    "g3_cf_ai_agent_gptbot": (
        Query(_AGENT, "GPTBot", _AGENTS), "Cloudflare Radar: GPTBot (OpenAI), andel av AI-botarnas förfrågningar",
        "Hur mycket crawlar OpenAI för träning jämfört med andra AI-botar?"),
    "g3_cf_ai_agent_chatgpt_user": (
        Query(_AGENT, "ChatGPT-User", _AGENTS),
        "Cloudflare Radar: ChatGPT-User (OpenAI), andel av AI-botarnas förfrågningar",
        "Hur mycket hämtar ChatGPT på användares uppdrag?"),
    "g3_cf_ai_agent_oai_searchbot": (
        Query(_AGENT, "OAI-SearchBot", _AGENTS),
        "Cloudflare Radar: OAI-SearchBot (OpenAI), andel av AI-botarnas förfrågningar",
        "Hur mycket indexerar OpenAI för sök?"),
    "g3_cf_ai_agent_claudebot": (
        Query(_AGENT, "ClaudeBot", _AGENTS), "Cloudflare Radar: ClaudeBot (Anthropic), andel av AI-botarnas förfrågningar",
        "Hur mycket crawlar Anthropic jämfört med andra AI-botar?"),
    "g3_cf_ai_agent_meta": (
        Query(_AGENT, "Meta-ExternalAgent", _AGENTS),
        "Cloudflare Radar: Meta-ExternalAgent (Meta), andel av AI-botarnas förfrågningar",
        "Hur mycket crawlar Meta för AI jämfört med andra AI-botar?"),
    "g3_cf_ai_agent_bytespider": (
        Query(_AGENT, "Bytespider", _AGENTS),
        "Cloudflare Radar: Bytespider (ByteDance), andel av AI-botarnas förfrågningar",
        "Hur mycket crawlar ByteDance jämfört med andra AI-botar?"),
    "g3_cf_bots_ai_crawler_share": (
        Query(_CATEGORY, "AI_CRAWLER", {}),
        "Cloudflare Radar: AI-crawlers andel av verifierade botars förfrågningar",
        "Hur stor del av den verifierade bottrafiken är AI-crawlers?"),
    "g3_cf_bots_ai_assistant_share": (
        Query(_CATEGORY, "AI_ASSISTANT", {}),
        "Cloudflare Radar: AI-assistenters andel av verifierade botars förfrågningar",
        "Hur stor del av den verifierade bottrafiken är AI-assistenter som hämtar åt användare?"),
}
QUERIES: dict[str, Query] = {k: q for k, (q, _, _) in _DEFS.items()}

_NOTE = ("Veckoandel i procent (Radar aggInterval=1w, normalization PERCENTAGE), vecka måndag–söndag UTC. Hämtas "
         "med CLOUDFLARE_API_TOKEN i GitHub Actions (jobbet cloudflare_radar och veckohämtningen). known_from = "
         "veckans slut + 1 dag (Radar uppdaterar löpande; lastUpdated samma dygn). Radar kan räkna om "
         "klassningen av botar i efterhand, så serien hämtas om i sin helhet varje vecka och ändringar blir "
         "revideringar. Backfillen har dagens version.")


def _spec(key: str) -> Spec:
    q, label, question = _DEFS[key]
    extra = (" Radars kategorier har bytts (API:t kallar bland annat AI_SEARCH och AGGREGATOR för föråldrade), "
             "så nivåbrott vid omklassning är möjliga (docs/kallor/trafik.md)." if q.path == _CATEGORY else "")
    return Spec(key=key, branch="G3", label=label, unit="procent", freq="W",
                source=f"Cloudflare Radar API ({q.path}, {q.group})", fetch=partial(cf.series, key, q), lag_days=1,
                license=cf.LICENSE, revised=True, publish=True, question=question, note=_NOTE + extra)


SPECS = [_spec(k) for k in _DEFS]
