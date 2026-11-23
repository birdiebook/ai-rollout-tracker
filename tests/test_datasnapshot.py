"""Encrypted data snapshot (ai_tracker.datasnapshot): no network, synthetic tables only."""

import io
import json
import zipfile

import pandas as pd
import pytest

from ai_tracker import datasnapshot as ds
from ai_tracker import observations

KEY = "unit-test-key-not-a-secret"
SERIES = ["secret_series_alpha", "hidden_series_beta"]


def _table(fetched="2026-11-16") -> pd.DataFrame:
    rows = [(s, "M", f"2026-0{m}", float(m), pd.Timestamp(f"2026-0{m}-28"), "fetch", pd.Timestamp(fetched))
            for s in SERIES for m in range(1, 6)]
    return pd.DataFrame(rows, columns=observations.COLUMNS)


def _log(fetched="2026-11-16") -> pd.DataFrame:
    return pd.DataFrame({"series": SERIES, "fetched_at": pd.to_datetime([fetched] * 2), "n_periods": [5, 5],
                         "last_period": ["2026-05", "2026-05"], "rows_added": [5, 5]})


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    observations.write_parquet(_table(), d / ds.TABLE)
    observations.write_parquet(_log(), d / ds.LOG)
    state = d / "raw" / "firstparty_prices" / "snapshots.parquet"
    state.parent.mkdir(parents=True)
    pd.DataFrame({"developer": ["x"], "input_per_m": [1.0]}).to_parquet(state)
    (d / "raw" / "sec").mkdir(parents=True)
    (d / "raw" / "sec" / "big_cache.json").write_text("{}")  # raw HTTP copies are never packed
    return d


@pytest.fixture
def snap(data_dir, tmp_path):
    out = tmp_path / "out" / ds.FILE_NAME
    ds.pack(out, data_dir, key=KEY)
    return out


def test_round_trip(snap, data_dir, tmp_path):
    target = tmp_path / "new_session" / "data"
    m = ds.install(snap.read_bytes(), target, key=KEY)
    assert m["installed"] == str(target)
    for rel in (ds.TABLE, ds.LOG, "raw/firstparty_prices/snapshots.parquet"):
        assert (target / rel).read_bytes() == (data_dir / rel).read_bytes()
    assert not (target / "raw" / "sec").exists()
    assert m["observations"] == {"rows": 10, "series": 2, "max_fetched_at": "2026-11-16T00:00:00",
                                 "max_known_from": "2026-05-28T00:00:00"}
    assert m["fetch_log"] == {"rows": 2}
    assert len(m["git_sha"]) > 0
    pd.testing.assert_frame_equal(observations.read_table(target / ds.TABLE), _table())


def test_header_is_minimal_plaintext(snap):
    header, _ = ds.read_header(snap.read_bytes())
    assert set(header) == {"format", "salt", "created_at"}
    assert header["format"] == ds.FORMAT


def test_no_plaintext_series_names(snap):
    blob = snap.read_bytes()
    for needle in SERIES + ["observations.parquet", "fetch_log", "manifest", "firstparty", "series", "known_from"]:
        assert needle.encode() not in blob
        assert needle.encode("utf-16-le") not in blob


def test_salt_and_nonce_are_fresh(data_dir, tmp_path):
    a, b = tmp_path / "a.aisnap", tmp_path / "b.aisnap"
    ds.pack(a, data_dir, key=KEY)
    ds.pack(b, data_dir, key=KEY)
    assert ds.read_header(a.read_bytes())[0]["salt"] != ds.read_header(b.read_bytes())[0]["salt"]
    assert a.read_bytes() != b.read_bytes()


def test_wrong_key_fails_authentication(snap, tmp_path):
    with pytest.raises(ds.SnapshotError, match="authentication failed"):
        ds.install(snap.read_bytes(), tmp_path / "x", key="another-key")
    assert not (tmp_path / "x").exists()


@pytest.mark.parametrize("where", ["ciphertext", "tag", "nonce"])
def test_tampered_ciphertext_fails(snap, where, tmp_path):
    blob = bytearray(snap.read_bytes())
    _, off = ds.read_header(bytes(blob))
    i = {"nonce": off, "ciphertext": off + ds.NONCE_BYTES + 100, "tag": len(blob) - 1}[where]
    blob[i] ^= 0x01
    with pytest.raises(ds.SnapshotError, match="authentication failed"):
        ds.unpack(bytes(blob), key=KEY)


def test_tampered_header_fails(snap):
    """The header is associated data: a changed created_at fails like a changed ciphertext."""
    blob = snap.read_bytes()
    header, off = ds.read_header(blob)
    forged = ds._prefix({**header, "created_at": "2030-01-01T00:00:00Z"})
    assert len(forged) == off
    with pytest.raises(ds.SnapshotError, match="authentication failed"):
        ds.unpack(forged + blob[off:], key=KEY)


def test_truncated_and_foreign_files_fail(snap):
    blob = snap.read_bytes()
    with pytest.raises(ds.SnapshotError):
        ds.unpack(blob[:40], key=KEY)
    with pytest.raises(ds.SnapshotError, match="neither"):
        ds.extract_snapshot(b"hello")


def test_refuses_without_key(data_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(ds.config, "get", lambda name, default=None: None)
    out = tmp_path / "o.aisnap"
    with pytest.raises(ds.SnapshotError, match="DATA_KEY is not set"):
        ds.pack(out, data_dir)
    assert not out.exists()
    assert ds.main(["pack", "--out", str(out), "--data-dir", str(data_dir)]) == 1
    assert not out.exists()
    assert ds.main(["fetch", "--file", str(out), "--data-dir", str(tmp_path / "t")]) == 1


def test_key_from_environment(data_dir, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATA_KEY", KEY)
    out = tmp_path / "o.aisnap"
    assert ds.main(["pack", "--out", str(out), "--data-dir", str(data_dir)]) == 0
    assert ds.main(["fetch", "--file", str(out), "--data-dir", str(tmp_path / "t")]) == 0
    assert KEY not in capsys.readouterr().out


def _repack(blob: bytes, edit) -> bytes:
    """Decrypt, let `edit(manifest, files)` change the payload, re-encrypt with the right key (an insider error)."""
    import tarfile

    _, payload = ds.decrypt(blob, KEY)
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    manifest = json.loads(files.pop("manifest.json"))
    edit(manifest, files)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, b in [("manifest.json", json.dumps(manifest).encode())] + list(files.items()):
            info = tarfile.TarInfo(name)
            info.size = len(b)
            tar.addfile(info, io.BytesIO(b))
    return ds.encrypt(buf.getvalue(), KEY)


def test_manifest_row_count_mismatch_fails(snap):
    def edit(m, f):
        m["observations"]["rows"] += 1
    with pytest.raises(ds.SnapshotError, match="does not match the manifest"):
        ds.unpack(_repack(snap.read_bytes(), edit), key=KEY)


def test_manifest_hash_mismatch_fails(snap):
    def edit(m, f):
        f[ds.LOG] = f[ds.LOG] + b"x"
    with pytest.raises(ds.SnapshotError, match="SHA-256"):
        ds.unpack(_repack(snap.read_bytes(), edit), key=KEY)


def test_manifest_unsafe_path_fails(snap):
    def edit(m, f):
        f["../escape"] = b"x"
        m["files"]["../escape"] = {"sha256": ds._sha256(b"x"), "bytes": 1}
    with pytest.raises(ds.SnapshotError, match="unsafe"):
        ds.unpack(_repack(snap.read_bytes(), edit), key=KEY)


def test_refuses_to_overwrite_newer_local_table(snap, tmp_path):
    target = tmp_path / "data"
    observations.write_parquet(_table(fetched="2026-11-20"), target / ds.TABLE)
    before = (target / ds.TABLE).read_bytes()
    with pytest.raises(ds.SnapshotError, match="as new or newer"):
        ds.install(snap.read_bytes(), target, key=KEY)
    assert (target / ds.TABLE).read_bytes() == before
    m = ds.install(snap.read_bytes(), target, force=True, key=KEY)
    assert observations.read_table(target / ds.TABLE)["fetched_at"].max() == pd.Timestamp("2026-11-16")
    assert (tmp_path / "data" / "snapshot_backups").is_dir() and m["backup"]
    backup = next((target / "snapshot_backups").iterdir()) / ds.TABLE
    assert backup.read_bytes() == before


def test_replaces_older_local_table_with_backup(snap, tmp_path):
    target = tmp_path / "data"
    observations.write_parquet(_table(fetched="2026-11-09"), target / ds.TABLE)
    m = ds.install(snap.read_bytes(), target, key=KEY)
    assert m["installed"] == str(target) and m["backup"]
    assert ds.install(snap.read_bytes(), target, key=KEY)["installed"] == "unchanged"


def test_artifact_zip_is_unwrapped(snap):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(ds.FILE_NAME, snap.read_bytes())
    assert ds.extract_snapshot(buf.getvalue()) == snap.read_bytes()
    empty = io.BytesIO()
    with zipfile.ZipFile(empty, "w") as zf:
        zf.writestr("other.txt", "x")
    with pytest.raises(ds.SnapshotError, match="expected one"):
        ds.extract_snapshot(empty.getvalue())


def test_find_artifact_picks_newest_from_main():
    class Resp:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    def art(i, created, branch="main", expired=False, name=ds.ARTIFACT):
        return {"id": i, "name": name, "expired": expired, "created_at": created,
                "archive_download_url": f"https://api.github.com/x/{i}/zip",
                "workflow_run": {"id": 100 + i, "head_branch": branch}}

    class Session:
        def get(self, url, timeout=None, **kw):
            assert kw["params"]["name"] == ds.ARTIFACT
            return Resp({"artifacts": [art(1, "2026-11-09T04:00:00Z"), art(2, "2026-11-23T04:00:00Z", "auto/x"),
                                       art(3, "2026-11-16T04:00:00Z"), art(4, "2026-11-20T00:00:00Z", expired=True)]})

    assert ds.find_artifact(Session())["id"] == 3

    class Empty(Session):
        def get(self, url, timeout=None, **kw):
            return Resp({"artifacts": []})

    with pytest.raises(ds.SnapshotError, match="no unexpired"):
        ds.find_artifact(Empty())


def test_track_worktree_default_install_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(observations, "SHARED_DIR", tmp_path / "elsewhere")
    with pytest.raises(ds.SnapshotError, match="track worktree"):
        ds._default_install_dir(None)
    assert ds._default_install_dir(str(tmp_path)) == tmp_path


def test_pack_refuses_empty_data_dir(tmp_path):
    with pytest.raises(ds.SnapshotError, match="nothing to pack"):
        ds.pack(tmp_path / "o.aisnap", tmp_path / "empty", key=KEY)
