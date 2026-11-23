"""G3: AI co-author trailers in public GitHub commits (step 2 track B2), docs/kallor/github_ai.md.

Part A (g3_gh_*): GH Archive, seven registered sample hours per week, 2021-W01 to 2025-W40, closed (GitHub
removed commit messages from the Events API on 2025-10-08). Part B (g3_ghs_*): GitHub commit search,
weekly from 2024-01, live, revised. A and B are different measures and are never spliced.
"""

from __future__ import annotations

from functools import partial

from ai_tracker.catalog import Spec
from ai_tracker.sources import gharchive, github_search

LICENSE_A = ("GH Archive (www.gharchive.org): site and docs CC-BY-4.0; the event dataset \"includes material that "
             "may be subject to third party rights\" (GitHub's terms). Only weekly counts are stored, no event "
             "content. Not checked for publication.")
LICENSE_B = ("GitHub REST API, search/commits (GitHub Terms of Service, API terms). Only total_count per query "
             "is stored, no commit content. Not checked for publication.")

NOTE_A = ("Historisk och stängd: GitHub tog bort commits ur PushEvent i Events API (GH Archive från timme "
          "2025-10-08-17), så måttet kan inte föras vidare ur GH Archive. Sju registrerade urvalstimmar per vecka. "
          "Trailern beror på verktygens standardinställningar (mätbrott när de ändras), se docs/kallor/github_ai.md.")
NOTE_B = ("GitHubs commit-sökning (standardgrenen i publika repon), total_count. De 8 senaste veckorna frågas om "
          "vid varje hämtning; backfill (2024-01 till första hämtningen) är dagens version, så sena merges och "
          "raderade repon läcker in. Annat mått än g3_gh_* (GH Archive), skarvas inte.")

GROUP_LABEL = {"claude": "Claude", "copilot": "GitHub Copilot", "cursor": "Cursor", "devin": "Devin",
               "codex": "OpenAI Codex", "google": "Google (Gemini Code Assist, Jules)", "aider": "Aider",
               "amp": "Amp", "other": "övriga agenter och AI-granskningsbottar"}


def _a(key: str, label: str, unit: str, fetch) -> Spec:
    return Spec(key=key, branch="G3", label=label, unit=unit, freq="W",
                source="GH Archive timfiler (data.gharchive.org), 7 urvalstimmar per vecka", fetch=fetch,
                lag_days=2, license=LICENSE_A, revised=False, publish=False,
                question="Hur stor del av publika commits skrivs med en AI-agent som medförfattare?",
                note=NOTE_A, closed=True)


def _b(key: str, label: str, unit: str, name: str, kind: str) -> Spec:
    return Spec(key=key, branch="G3", label=label, unit=unit, freq="W",
                source="GitHub REST API search/commits (total_count)",
                fetch=partial(github_search.fetch, key, name, kind), lag_days=1, license=LICENSE_B,
                revised=True, publish=False,
                question="Hur stor del av publika commits skrivs med en AI-agent som medförfattare, nu?",
                note=NOTE_B)


SPECS = [
    _a("g3_gh_ai_coauthor_share_w", "Andel publika commits med AI-medförfattare (GH Archive)", "% av commits",
       partial(gharchive.share, "ai_commits")),
    _a("g3_gh_ai_coauthor_repos_w", "Repon med minst en AI-medförfattad commit (GH Archive, urval)",
       "repon per urvalsvecka (7 timmar)", partial(gharchive.level, "ai_repos")),
    _a("g3_gh_push_commits_w", "Publika push-commits (GH Archive, urval)", "commits per urvalsvecka (7 timmar)",
       partial(gharchive.level, "commits")),
] + [
    _a(f"g3_gh_ai_coauthor_share_{g}_w", f"Andel publika commits med {lbl} som medförfattare (GH Archive)",
       "% av commits", partial(gharchive.share, f"ai_{g}"))
    for g, lbl in GROUP_LABEL.items()
] + [
    _b("g3_ghs_ai_coauthor_share_w", "Andel commits med AI-medförfattare (GitHub-sökning)", "% av commits",
       "any", "share"),
    _b("g3_ghs_commits_w", "Commits per vecka i GitHubs sökindex", "commits per vecka", "all", "level"),
    _b("g3_ghs_ai_coauthor_commits_w", "Commits med AI-medförfattare per vecka (GitHub-sökning)",
       "commits per vecka", "any", "level"),
] + [
    _b(f"g3_ghs_ai_coauthor_share_{g}_w", f"Andel commits med {GROUP_LABEL[g]} som medförfattare (GitHub-sökning)",
       "% av commits", g, "share")
    for g in ("claude", "copilot", "cursor")
]

# GH Archive outage 2021-10-22 to 2021-10-28 (sample hours missing): ISO week 2021-W43 has 3 of 7 hours, no value.
KNOWN_GAPS = {s.key: "GH Archive outage 2021-10-22..28: week 2021-10-25 has 3 of 7 sample hours (< 5)"
              for s in SPECS if s.key.startswith("g3_gh_")}
