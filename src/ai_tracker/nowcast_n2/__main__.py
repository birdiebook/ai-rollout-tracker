"""Compatibility shim: python -m ai_tracker.nowcast_n2 --origin YYYY-MM-DD [--refresh]
= python -m ai_tracker.nowcast n2 --origin YYYY-MM-DD [--refresh] (ai_tracker.nowcast.n2)."""

from ai_tracker.nowcast.n2 import main_live as main

if __name__ == "__main__":
    raise SystemExit(main())
