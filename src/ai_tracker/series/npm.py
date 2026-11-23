"""npm weekly downloads of AI SDK packages and two control packages (G3, track B1). See sources/npm.py and
docs/kallor/utvecklaradoption.md."""

from __future__ import annotations

from datetime import date
from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import npm

SOURCE = "npm download counts API (api.npmjs.org)"
LICENSE = ("unverified: no licence stated in github.com/npm/registry docs/download-counts.md; npm's Open Source "
           "Terms (docs.npmjs.com) could not be read from the sandbox")
_NOTE = ("Nedladdningar per vecka (måndag–söndag, UTC), inte användare: CI-byggen, speglar och cachar räknas med "
         "och beroenden räknas varje gång. known_from = söndag + 2 dagar (npm räknar dagen strax efter UTC-midnatt). "
         "Dagar som npm saknar (0 för alla paket, t.ex. 2026-10-14) fylls ur paketets veckodagsprofil.")

# key -> (npm package, first day to query, explicit series start (a Monday) or None, label, note)
PACKAGES = {
    "g3_npm_openai_w": ("openai", date(2020, 7, 1), None, "openai (OpenAI:s SDK)", ""),
    "g3_npm_anthropic_sdk_w": ("@anthropic-ai/sdk", date(2023, 1, 30), None, "@anthropic-ai/sdk (Anthropics SDK)",
                               ""),
    "g3_npm_google_generative_ai_w": ("@google/generative-ai", date(2023, 12, 11), None,
                                      "@google/generative-ai (Googles äldre Gemini-SDK)", ""),
    "g3_npm_google_genai_w": ("@google/genai", date(2025, 3, 10), None, "@google/genai (Googles Gemini-SDK)", ""),
    "g3_npm_langchain_w": ("langchain", date(2023, 1, 16), None, "langchain (LangChain.js)", ""),
    "g3_npm_langchain_core_w": ("@langchain/core", date(2023, 11, 20), None, "@langchain/core", ""),
    "g3_npm_vercel_ai_w": ("ai", date(2023, 6, 12), date(2023, 6, 12), "ai (Vercel AI SDK)",
                           "Namnet ai hade ett annat paket 2014 (0.0.1–1.1.0); Vercels 2.0.0 kom 2023-06-14, så "
                           "serien börjar veckan 2023-06-12."),
    "g3_npm_mcp_sdk_w": ("@modelcontextprotocol/sdk", date(2024, 11, 11), None,
                         "@modelcontextprotocol/sdk (MCP)", ""),
    "g3_npm_react_w": ("react", npm.EARLIEST, None, "react (kontrollpaket)",
                       "Kontrollpaket för normalisering, inte en AI-serie."),
    "g3_npm_express_w": ("express", npm.EARLIEST, None, "express (kontrollpaket)",
                         "Kontrollpaket för normalisering, inte en AI-serie."),
}


def _fetch(package: str, since: date, start: date | None):
    return npm.weekly(package, since, start)


SPECS = [
    Spec(key=key, branch="G3", label=f"npm-nedladdningar per vecka: {label}", unit="nedladdningar per vecka",
         freq="W", source=SOURCE, fetch=partial(_fetch, pkg, since, start), lag_days=npm.LAG_DAYS, license=LICENSE,
         revised=True, publish=False, question="Hur snabbt bygger utvecklare med AI-SDK:er (JavaScript)?",
         note=(extra + " " + _NOTE).strip())
    for key, (pkg, since, start, label, extra) in PACKAGES.items()
]
