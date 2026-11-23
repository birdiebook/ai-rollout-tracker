"""Smoke job: proves which secrets are present in Actions without printing them."""

from __future__ import annotations

import json
import os
from pathlib import Path


def run(out_dir: Path) -> None:
    names = ["CLOUDFLARE_API_TOKEN", "GCP_PROJECT_ID"]
    present = {n: bool(os.environ.get(n)) for n in names}
    present["gcp_credentials_file"] = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    (out_dir / "smoke.json").write_text(json.dumps(present, indent=2), encoding="utf-8")
    print(present)
