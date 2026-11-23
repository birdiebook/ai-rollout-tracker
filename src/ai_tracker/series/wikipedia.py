"""Wikipedia pageviews for AI products and topics (G3, track B3); see sources/wikipedia.py and docs/kallor/trafik.md."""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import wikipedia

LICENSE = ("CC0 1.0 (Wikimedia Analytics pageview data; docs/kallor/trafik.md quotes the terms). Attribution given: "
           "Wikimedia Foundation, Pageviews API")
_NOTE = ("Sidvisningar av människor (agent=user, all-access), summa måndag–söndag. Nuvarande titel plus tidigare "
         "titlar (flyttade sidor). known_from = veckans slut + 2 dagar (dagsdata finns dagen efter). Wikimedia "
         "omklassificerar ibland bottrafik i efterhand (revideringar blir nya versioner; backfillen har dagens version).")

_TOPICS = {  # topic -> (Swedish label, question)
    "chatgpt": ("ChatGPT", "Hur stor är uppmärksamheten kring ChatGPT?"),
    "claude": ("Claude (Anthropic)", "Hur stor är uppmärksamheten kring Claude?"),
    "gemini": ("Google Gemini (inkl. Bard)", "Hur stor är uppmärksamheten kring Gemini?"),
    "copilot": ("Microsoft Copilot (inkl. Bing Chat)", "Hur stor är uppmärksamheten kring Copilot?"),
    "grok": ("Grok (xAI)", "Hur stor är uppmärksamheten kring Grok?"),
    "deepseek": ("DeepSeek", "Hur stor är uppmärksamheten kring DeepSeek?"),
    "perplexity": ("Perplexity", "Hur stor är uppmärksamheten kring Perplexity?"),
    "llm": ("Stora språkmodeller (LLM)", "Hur stort är intresset för stora språkmodeller som ämne?"),
    "genai": ("Generativ AI", "Hur stort är intresset för generativ AI som ämne?"),
    "ai": ("Artificiell intelligens", "Hur stort är intresset för AI som ämne (lång historik från 2015)?"),
    "openai": ("OpenAI", "Hur stor är uppmärksamheten kring OpenAI som bolag?"),
    "anthropic": ("Anthropic", "Hur stor är uppmärksamheten kring Anthropic som bolag?"),
}
_SCOPES = {  # suffix -> (languages, Swedish label part)
    "en": (("en",), "engelska Wikipedia"),
    "xen": (wikipedia.OTHER, "tyska, franska, spanska och japanska Wikipedia"),
}


def _spec(topic: str, scope: str) -> Spec:
    label, question = _TOPICS[topic]
    langs, where = _SCOPES[scope]
    titles = "; ".join(f"{lang}: " + " + ".join(wikipedia.TOPICS[topic][lang]) for lang in langs)
    return Spec(key=f"g3_wiki_{topic}_{scope}", branch="G3", label=f"Wikipedia: sidvisningar för {label}, {where}",
                unit="sidvisningar per vecka", freq="W", source="Wikimedia Pageviews API",
                fetch=partial(wikipedia.topic_weekly, topic, langs), lag_days=2, license=LICENSE, revised=True,
                publish=True, question=question, note=f"Titlar: {titles}. {_NOTE}")


SPECS = [_spec(t, s) for t in _TOPICS for s in _SCOPES]
