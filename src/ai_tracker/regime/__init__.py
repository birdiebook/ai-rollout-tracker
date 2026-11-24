"""C4: regime (Markov switching on C3's block factors) and structural breaks (BOCPD per core series), real time.

ms.py (MSIH(2)-AR(0) by EM, filtered and smoothed probabilities), bocpd.py (Adams-MacKay with a normal-gamma prior),
realtime.py (one record per computation date, the reporting rules), evaluate.py (F-D6 criteria), guard.py (the
closed holdout). Specification: docs/steg2/c4_spec.md (locked before the first real-data run, commit 735dc64).
"""
