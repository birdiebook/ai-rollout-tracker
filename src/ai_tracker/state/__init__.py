"""Branch states (register sections 1, 2 and 5): per-series measures, diffusion index, monthly snapshot.

    python -m ai_tracker.state snapshot --date YYYY-MM-DD    snapshots/<YYYY-MM>.json (month end; never overwrites)
    python -m ai_tracker.state backcast --start 2019-01 --end 2026-10   outputs/state_backcast.csv (reconstructed)
                                     [--compare N]           ... and a Markdown table v1 vs v2 for the last N months
    python -m ai_tracker.state due [--today D]               is today (UTC) a snapshot day? (GitHub output due=)
    python -m ai_tracker.state show --date YYYY-MM-DD        print the branch states and reconciliations (A5), write nothing
    python -m ai_tracker.state evaluate [--perm N]           T1: the registered test of the state rule (register
                                                             2026-11-25), outputs/t1_tillstandsregeln.json + tables
"""
