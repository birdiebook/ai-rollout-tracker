"""Guard for a public repo: no e-mail addresses or key-like strings in tracked files.

Contact details and keys live in .env (gitignored) and in Actions secrets only.
"""

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}")
ALLOWED = {"you@example.com", "noreply@anthropic.com"}  # placeholders / tool attribution


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    return [REPO / f for f in out.splitlines() if (REPO / f).is_file()]


def test_env_is_not_tracked():
    assert ".env" not in {p.name for p in tracked_files()}


def test_no_email_addresses_in_tracked_files():
    hits = []
    for path in tracked_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        hits += [f"{path.relative_to(REPO)}: {m}" for m in set(EMAIL.findall(text)) - ALLOWED]
    assert not hits, hits
