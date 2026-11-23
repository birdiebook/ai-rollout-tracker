"""Encrypted data snapshot: carry data/ from the weekly Actions fetch into a new cloud session.

data/ is never committed, a full rebuild takes 1-2 h, and some series (BigQuery, Cloudflare) can only be fetched in
Actions. Artifacts of a public repo are public and several series may not be republished (publish=False), so the
weekly fetch uploads the table only as an encrypted artifact (`data-snapshot`, 14 days). docs/drift.md, "Datasnapshot".

    python -m ai_tracker.datasnapshot pack --out snap/data-snapshot.aisnap   # Actions (or locally)
    python -m ai_tracker.datasnapshot fetch [--run-id N | --url U | --file F] [--force]
    python -m ai_tracker.datasnapshot info <file>                            # header + manifest (needs the key)

Both pack and fetch need DATA_KEY (environment, .env.local or .env; config.get). The value is never printed.

File format (version 1):
    MAGIC (8 bytes) | header length (4 bytes, big endian) | header JSON | nonce (12 bytes) | ciphertext + tag
- The header is the only plaintext: {"format": 1, "salt": <base64, 16 random bytes>, "created_at": <UTC ISO>}.
- Key: scrypt(DATA_KEY, salt, n=2**15, r=8, p=1) -> 32 bytes. Cipher: AES-256-GCM with the whole prefix (magic,
  length, header) as associated data, so a changed header fails authentication like a changed ciphertext.
- Payload: a gzip tar with manifest.json and the files. The manifest has the git sha, row and series counts, the
  newest fetched_at and known_from, and the SHA-256 and size of every file; fetch checks all of it before writing.

Contents: data/observations.parquet, data/fetch_log.parquet and the small state files that incremental runs need
and that cannot be refetched (STATE_FILES, e.g. our own weekly first-party price snapshots). Not the raw HTTP copies
(gigabytes, refetchable).

Install: into this checkout's data/ (or --data-dir). Refuses when the local table is as new or newer (its newest
fetched_at >= the snapshot's) unless --force; the replaced files are kept in data/snapshot_backups/ (last 5). In a
track worktree (AI_TRACKER_SHARED_DATA set) the default is refused: install into the main checkout, which is the base.
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from ai_tracker import config, observations

MAGIC = b"AIRTSNAP"
FORMAT = 1
KEY_ENV = "DATA_KEY"
SALT_BYTES = 16
NONCE_BYTES = 12
SCRYPT = {"n": 2 ** 15, "r": 8, "p": 1}
ARTIFACT = "data-snapshot"
FILE_NAME = "data-snapshot.aisnap"
REPO_SLUG = "birdiebook/ai-rollout-tracker"
API = "https://api.github.com"
WORKFLOW = "fetch-weekly.yml"
TABLE = "observations.parquet"
LOG = "fetch_log.parquet"
# Relative to data/. Small state that a later run builds on and that cannot be fetched again; included when present.
STATE_FILES = [
    "raw/firstparty_prices/snapshots.parquet",  # our own weekly price snapshots (B5): history exists only here
    "raw/census_btos/schedule_log.parquet",     # BTOS schedule as seen on each fetch (R1 3.6)
    "epoch/benchmark_runs.parquet",             # Epoch benchmark-runs ledger (own weekly snapshots)
    "raw/litellm/snapshots_v2.parquet",         # LiteLLM extraction cache (saves a full git-history walk)
]
MAX_STATE_BYTES = 50 * 2 ** 20  # a state file above this is skipped with a warning (it is a cache, not state)
MAX_DOWNLOAD_BYTES = 2 * 2 ** 30
KEEP_BACKUPS = 5


class SnapshotError(Exception):
    """A snapshot that cannot be packed, authenticated, verified or installed."""


# ------------------------------------------------------------------------------------------------ crypto


def _key_value(key: str | None = None) -> str:
    value = key if key is not None else config.get(KEY_ENV)
    if not value:
        raise SnapshotError(f"{KEY_ENV} is not set: the snapshot is always encrypted (docs/miljo.md, section 4)")
    return value


def derive_key(secret: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    return Scrypt(salt=salt, length=32, **SCRYPT).derive(secret.encode("utf-8"))


def _prefix(header: dict) -> bytes:
    raw = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("ascii")
    return MAGIC + len(raw).to_bytes(4, "big") + raw


def encrypt(payload: bytes, secret: str, created_at: str | None = None) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = os.urandom(SALT_BYTES)
    header = {"format": FORMAT, "salt": base64.b64encode(salt).decode("ascii"),
              "created_at": created_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    prefix = _prefix(header)
    nonce = os.urandom(NONCE_BYTES)
    return prefix + nonce + AESGCM(derive_key(secret, salt)).encrypt(nonce, payload, prefix)


def read_header(blob: bytes) -> tuple[dict, int]:
    """The plaintext header and the offset where the nonce starts."""
    if blob[:len(MAGIC)] != MAGIC:
        raise SnapshotError("not a data snapshot (bad magic)")
    n = int.from_bytes(blob[len(MAGIC):len(MAGIC) + 4], "big")
    start = len(MAGIC) + 4
    if n > 4096 or len(blob) < start + n + NONCE_BYTES + 16:
        raise SnapshotError("truncated or malformed snapshot header")
    try:
        header = json.loads(blob[start:start + n])
    except ValueError as exc:
        raise SnapshotError("malformed snapshot header") from exc
    if header.get("format") != FORMAT:
        raise SnapshotError(f"unsupported snapshot format {header.get('format')!r} (this code reads {FORMAT})")
    return header, start + n


def decrypt(blob: bytes, secret: str) -> tuple[dict, bytes]:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    header, off = read_header(blob)
    try:
        salt = base64.b64decode(header["salt"], validate=True)
    except (KeyError, ValueError) as exc:
        raise SnapshotError("malformed salt in snapshot header") from exc
    nonce, ct = blob[off:off + NONCE_BYTES], blob[off + NONCE_BYTES:]
    try:
        payload = AESGCM(derive_key(secret, salt)).decrypt(nonce, ct, blob[:off])
    except InvalidTag:
        raise SnapshotError(f"authentication failed: wrong {KEY_ENV} or a damaged/tampered file") from None
    return header, payload


# ------------------------------------------------------------------------------------------------ pack


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_sha() -> str:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.REPO, capture_output=True, text=True,
                             check=True, timeout=10)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _iso(ts) -> str | None:
    return None if pd.isna(ts) else pd.Timestamp(ts).isoformat()


def table_stats(table: pd.DataFrame) -> dict:
    return {"rows": int(len(table)), "series": int(table["series"].nunique()),
            "max_fetched_at": _iso(table["fetched_at"].max()), "max_known_from": _iso(table["known_from"].max())}


def build_payload(data_dir: Path, git_sha: str | None = None) -> tuple[bytes, dict]:
    """(gzip tar with manifest.json + files, manifest). Reads the files in `data_dir` as they are (no shared base)."""
    data_dir = Path(data_dir)
    if not (data_dir / TABLE).exists():
        raise SnapshotError(f"no {TABLE} in {data_dir}: nothing to pack")
    files: dict[str, bytes] = {TABLE: (data_dir / TABLE).read_bytes()}
    if (data_dir / LOG).exists():
        files[LOG] = (data_dir / LOG).read_bytes()
    for rel in STATE_FILES:
        p = data_dir / rel
        if p.is_file():
            if p.stat().st_size > MAX_STATE_BYTES:
                print(f"warning: {rel} is {p.stat().st_size} bytes (> {MAX_STATE_BYTES}), not packed", file=sys.stderr)
                continue
            files[rel] = p.read_bytes()
    table = observations.read_table(data_dir / TABLE)
    log = observations.read_log(data_dir / LOG)
    manifest = {"format": FORMAT, "git_sha": git_sha or _git_sha(),
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "observations": table_stats(table), "fetch_log": {"rows": int(len(log))},
                "files": {rel: {"sha256": _sha256(b), "bytes": len(b)} for rel, b in files.items()}}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=6) as tar:
        for rel, b in [("manifest.json", json.dumps(manifest, indent=1).encode("utf-8"))] + sorted(files.items()):
            info = tarfile.TarInfo(rel)
            info.size, info.mtime, info.mode = len(b), 0, 0o644
            tar.addfile(info, io.BytesIO(b))
    return buf.getvalue(), manifest


def pack(out: Path, data_dir: Path | None = None, key: str | None = None) -> dict:
    secret = _key_value(key)  # before reading anything: never write an unencrypted file
    payload, manifest = build_payload(Path(data_dir or observations.DEFAULT_PATH.parent))
    blob = encrypt(payload, secret, manifest["created_at"])
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.name}.{os.getpid()}.tmp")
    tmp.write_bytes(blob)
    os.replace(tmp, out)
    return manifest


# ------------------------------------------------------------------------------------------------ unpack


def _safe_rel(name: str) -> bool:
    p = Path(name)
    return not p.is_absolute() and ".." not in p.parts and name not in ("", ".")


def unpack(blob: bytes, key: str | None = None) -> tuple[dict, dict[str, bytes]]:
    """Decrypt and verify: (manifest, {relative path: bytes}). Raises SnapshotError on any mismatch."""
    _, payload = decrypt(blob, _key_value(key))
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
            members = {m.name: m for m in tar.getmembers() if m.isfile()}
            if "manifest.json" not in members:
                raise SnapshotError("no manifest in snapshot")
            manifest = json.loads(tar.extractfile(members["manifest.json"]).read())
            files = {}
            for rel in manifest.get("files", {}):
                if not _safe_rel(rel) or rel not in members:
                    raise SnapshotError(f"manifest lists a missing or unsafe path: {rel!r}")
                files[rel] = tar.extractfile(members[rel]).read()
    except (tarfile.TarError, ValueError, OSError) as exc:
        raise SnapshotError(f"malformed snapshot payload: {exc}") from exc
    verify(manifest, files)
    return manifest, files


def verify(manifest: dict, files: dict[str, bytes]) -> None:
    if manifest.get("format") != FORMAT:
        raise SnapshotError(f"unsupported manifest format {manifest.get('format')!r}")
    if TABLE not in files:
        raise SnapshotError(f"snapshot has no {TABLE}")
    for rel, meta in manifest["files"].items():
        b = files[rel]
        if len(b) != meta["bytes"] or _sha256(b) != meta["sha256"]:
            raise SnapshotError(f"{rel}: size or SHA-256 does not match the manifest")
    table = pd.read_parquet(io.BytesIO(files[TABLE]))
    missing = set(observations.COLUMNS) - set(table.columns)
    if missing:
        raise SnapshotError(f"{TABLE} lacks columns {sorted(missing)}")
    for c in ("known_from", "fetched_at"):
        table[c] = pd.to_datetime(table[c])
    got, want = table_stats(table), manifest["observations"]
    if got != want:
        raise SnapshotError(f"{TABLE} does not match the manifest: {got} != {want}")
    if LOG in files:
        n = len(pd.read_parquet(io.BytesIO(files[LOG])))
        if n != manifest["fetch_log"]["rows"]:
            raise SnapshotError(f"{LOG} has {n} rows, manifest {manifest['fetch_log']['rows']}")


def _backup(data_dir: Path, rels: list[str]) -> Path | None:
    present = [r for r in rels if (data_dir / r).exists()]
    if not present:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = data_dir / "snapshot_backups" / stamp
    for rel in present:
        dst = folder / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(data_dir / rel, dst)
    for old in sorted((data_dir / "snapshot_backups").iterdir())[:-KEEP_BACKUPS]:
        shutil.rmtree(old, ignore_errors=True)
    return folder


def install(blob: bytes, data_dir: Path | None = None, force: bool = False, key: str | None = None) -> dict:
    """Verify and write the snapshot's files into `data_dir` (default: this checkout's data/)."""
    manifest, files = unpack(blob, key)
    data_dir = Path(data_dir or observations.DEFAULT_PATH.parent)
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(data_dir / ".merge.lock", "w") as lock:  # same lock as datamerge: never two writers of a base
        fcntl.flock(lock, fcntl.LOCK_EX)
        local_path = data_dir / TABLE
        if local_path.exists():
            if _sha256(local_path.read_bytes()) == manifest["files"][TABLE]["sha256"] and not force:
                manifest["installed"] = "unchanged"
                return manifest
            local = observations.read_table(local_path)
            local_max = local["fetched_at"].max()
            snap_max = manifest["observations"]["max_fetched_at"]
            if not force and not pd.isna(local_max) and (snap_max is None or local_max >= pd.Timestamp(snap_max)):
                raise SnapshotError(
                    f"local {TABLE} is as new or newer (max fetched_at {local_max.isoformat()} >= snapshot "
                    f"{snap_max}); use --force to replace it")
        manifest["backup"] = str(_backup(data_dir, list(files)) or "")
        for rel, b in files.items():
            dst = data_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_name(f".{dst.name}.{os.getpid()}.tmp")
            tmp.write_bytes(b)
            os.replace(tmp, dst)  # atomic per file: a reader sees the old or the new table
    manifest["installed"] = str(data_dir)
    return manifest


# ------------------------------------------------------------------------------------------------ download


def extract_snapshot(blob: bytes) -> bytes:
    """The snapshot file itself: `blob` as is, or the one .aisnap member of an artifact zip."""
    if blob[:len(MAGIC)] == MAGIC:
        return blob
    if blob[:2] != b"PK":
        raise SnapshotError("download is neither a snapshot nor a zip archive")
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = [i for i in zf.infolist() if i.filename.endswith(".aisnap")]
        if len(names) != 1:
            raise SnapshotError(f"expected one .aisnap file in the artifact, found {[i.filename for i in names]}")
        if names[0].file_size > MAX_DOWNLOAD_BYTES:
            raise SnapshotError("snapshot in the artifact is implausibly large")
        return zf.read(names[0])


def _session():
    import requests

    from ai_tracker import http

    s = requests.Session()
    s.headers.update({"User-Agent": http.DEFAULT_UA, "Accept": "application/vnd.github+json",
                      "X-GitHub-Api-Version": "2022-11-28"})
    return s


def _get(session, url: str, **kw):
    import requests

    try:
        r = session.get(url, timeout=120, **kw)
    except requests.exceptions.ProxyError as exc:
        host = urlparse(url).netloc
        raise SnapshotError(
            f"the network proxy refused {host}. If it is a productionresultssa*.blob.core.windows.net host, add it to "
            f"the environment's allowed hosts (docs/miljo.md, section 1) and run again") from exc
    r.raise_for_status()
    return r


def find_artifact(session, run_id: int | None = None, repo: str = REPO_SLUG) -> dict:
    """The newest unexpired `data-snapshot` artifact from main (or from run `run_id`)."""
    if run_id:
        url = f"{API}/repos/{repo}/actions/runs/{run_id}/artifacts"
    else:
        url = f"{API}/repos/{repo}/actions/artifacts"
    arts = _get(session, url, params={"name": ARTIFACT, "per_page": 30}).json().get("artifacts", [])
    arts = [a for a in arts if a.get("name") == ARTIFACT and not a.get("expired")]
    if not run_id:
        arts = [a for a in arts if (a.get("workflow_run") or {}).get("head_branch") == "main"]
    if not arts:
        where = f"run {run_id}" if run_id else "main"
        raise SnapshotError(f"no unexpired '{ARTIFACT}' artifact from {where} (DATA_KEY secret set? retention is "
                            f"14 days). Rebuild with `python -m ai_tracker.observations` instead")
    return max(arts, key=lambda a: a["created_at"])


def download(url: str | None = None, run_id: int | None = None) -> tuple[bytes, str]:
    """(snapshot bytes, description of where they came from)."""
    session = _session()
    if url is None:
        art = find_artifact(session, run_id)
        url = art["archive_download_url"]
        origin = f"artifact {art['id']} (run {art['workflow_run']['id']}, created {art['created_at']})"
    else:
        origin = urlparse(url).netloc
    if urlparse(url).netloc == urlparse(API).netloc:  # .../zip answers 302 to a short-lived blob URL
        r = _get(session, url, allow_redirects=False)
        if r.is_redirect:
            url = r.headers["Location"]  # signed URL: never printed
    session.headers.pop("Accept", None)
    session.headers.pop("X-GitHub-Api-Version", None)
    r = _get(session, url)
    if len(r.content) > MAX_DOWNLOAD_BYTES:
        raise SnapshotError("download is implausibly large")
    return extract_snapshot(r.content), origin


# ------------------------------------------------------------------------------------------------ CLI


def _default_install_dir(data_dir: str | None) -> Path:
    if data_dir:
        return Path(data_dir)
    shared = observations.SHARED_DIR
    own = observations.DEFAULT_PATH.parent
    if shared is not None and shared.resolve() != own.resolve():
        raise SnapshotError(f"{observations.SHARED_ENV} is set (track worktree): install into the main checkout "
                            f"(the shared base), or pass --data-dir explicitly")
    return own


def _summary(m: dict) -> str:
    o = m["observations"]
    return (f"{o['rows']} rows, {o['series']} series, max fetched_at {o['max_fetched_at']}, "
            f"fetch log {m['fetch_log']['rows']} rows, files {sorted(m['files'])}, git {m['git_sha'][:12]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ai_tracker.datasnapshot", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack", help="bundle and encrypt data/")
    p.add_argument("--out", required=True)
    p.add_argument("--data-dir")
    f = sub.add_parser("fetch", help="download, decrypt, verify and install the newest snapshot")
    src = f.add_mutually_exclusive_group()
    src.add_argument("--run-id", type=int, help="take the artifact of this workflow run")
    src.add_argument("--url", help="download URL (api.github.com .../zip or the blob URL from the GitHub MCP tools)")
    src.add_argument("--file", help="a local .aisnap or artifact .zip")
    f.add_argument("--data-dir", help="install here instead of this checkout's data/")
    f.add_argument("--force", action="store_true", help="replace a local table that is as new or newer")
    i = sub.add_parser("info", help="print the header and the verified manifest of a local file")
    i.add_argument("file")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "pack":
            m = pack(Path(args.out), Path(args.data_dir) if args.data_dir else None)
            print(f"packed {args.out}: {_summary(m)}")
        elif args.cmd == "info":
            blob = extract_snapshot(Path(args.file).read_bytes())
            header, _ = read_header(blob)
            print(json.dumps({k: header[k] for k in ("format", "created_at")}))
            print(_summary(unpack(blob)[0]))
        else:
            _key_value()  # fail before any download
            target = _default_install_dir(args.data_dir)
            if args.file:
                blob, origin = extract_snapshot(Path(args.file).read_bytes()), args.file
            else:
                blob, origin = download(args.url, args.run_id)
            m = install(blob, target, force=args.force)
            state = "already installed (identical table)" if m["installed"] == "unchanged" else f"installed in {target}"
            print(f"{origin}: {state}: {_summary(m)}")
            if m.get("backup"):
                print(f"previous files kept in {m['backup']}")
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
