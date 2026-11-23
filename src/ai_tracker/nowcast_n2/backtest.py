"""Compatibility shim: python -m ai_tracker.nowcast_n2.backtest = python -m ai_tracker.nowcast backtest n2."""

from ai_tracker.nowcast.n2 import main_backtest as main

if __name__ == "__main__":
    main()
