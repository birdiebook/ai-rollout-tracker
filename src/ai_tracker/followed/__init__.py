"""Followed questions: questions the owner reads monthly, outside the branches (no state, no index, no core series).

Each question has a registered entry in docs/mattregister.md, catalog series with publish=False and a report:

    python -m ai_tracker.followed kreditlagret --as-of YYYY-MM-DD [--json PATH]

Reports use only rows known on the as-of date (observations.as_of semantics: known_from <= as-of).
"""
