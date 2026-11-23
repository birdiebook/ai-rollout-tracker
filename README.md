# ai-rollout-tracker

Quantitative, neutral tracking of the global AI rollout: capability, cost, adoption, revenue,
investment, semiconductors, physical constraints, labour and research. Each branch is measured by
level, pace, change in pace and surprise versus expectations. Every value is stored with the date it
became known, measures are pre-registered, and monthly snapshots and nowcasts are committed before
the outcome is known.

Plan (Swedish): [docs/plan.md](docs/plan.md).

```bash
python -m pip install -r ci/requirements.txt
PYTHONPATH=src python -m pytest -q
```

Code: MIT. Data is fetched by scripts and never committed; each source keeps its own terms.
