"""Jobs that need secrets only GitHub Actions has (Cloudflare token, keyless GCP auth).

A job is a module ai_tracker.jobs.<name> with `run(out_dir: pathlib.Path) -> None` that writes CSV/JSON
results (aggregates of public data only: the artifact of a public repo is public) into out_dir.
Run in Actions with `.github/workflows/job.yml` (workflow_dispatch, input `job`, any branch as ref);
locally `python -m ai_tracker.jobs <name> [--out DIR]` works where the needed secrets exist.
"""
