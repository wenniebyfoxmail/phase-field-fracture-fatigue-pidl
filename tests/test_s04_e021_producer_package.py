"""Deployment checks only: temporary files and early-stop shell paths, no training."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "docs/research/S04/S04-E021/producer/prepare_and_dispatch.sh"
)


def python_block(name):
    return re.search(r"<<'" + name + r"'\n(.*?)\n" + name, SCRIPT.read_text(), re.S)[1]


def make_assets(tmp_path, monkeypatch):
    old, root, code = [tmp_path / n for n in ("old", "new", "code")]
    root.mkdir()
    code.mkdir()
    locks = {}
    for state in ("c20s4", "c60s4", "c83s4"):
        names = [
            "final_step_10000.pt",
            "prediction.npz",
            "metrics.json",
            "monitoring.json",
            "RUN_RECEIPT.json",
        ]
        rid = "control-" + state
        locks[state] = dict(
            run_id=rid, files={n: "unused-in-copy-stage" for n in names}
        )
        files = [old / "inputs" / (state + ".npz")]
        files += [old / "backbones" / state / n for n in names]
        files += [old / "runs" / rid / n for n in names]
        for p in files:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(str(p.relative_to(old)).encode())
    config = code / "docs/research/S04/S04-E020/control_locks.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps(locks))
    monkeypatch.chdir(code)
    monkeypatch.setenv("E021_ROOT", str(root))
    monkeypatch.setenv("E021_BASE19", str(old))
    return old, root


def copy_assets():
    exec(compile(python_block("COPY"), "deployment:COPY", "exec"), {})


def test_copy_manifest_matches_all_33_originals(tmp_path, monkeypatch):
    old, root = make_assets(tmp_path, monkeypatch)
    copy_assets()
    rows = json.loads((root / "asset_copy_manifest.json").read_text())
    assert len(rows) == 33
    for row in rows:
        source, dest = Path(row["source"]), Path(row["destination"])
        assert source.is_relative_to(old) and dest.is_relative_to(root)
        assert source.read_bytes() == dest.read_bytes()
        assert hashlib.sha256(dest.read_bytes()).hexdigest() == row["sha256"]
        assert dest.stat().st_size == row["bytes"]


def test_copy_refuses_existing_destination(tmp_path, monkeypatch):
    old, root = make_assets(tmp_path, monkeypatch)
    dest = root / "inputs/c20s4.npz"
    dest.parent.mkdir()
    dest.write_bytes(b"preserve")
    with pytest.raises(RuntimeError, match="destination reused"):
        copy_assets()
    assert dest.read_bytes() == b"preserve"


def test_copy_refuses_symlink_source(tmp_path, monkeypatch):
    old, root = make_assets(tmp_path, monkeypatch)
    src = old / "inputs/c20s4.npz"
    backup = old / "same-data.npz"
    src.rename(backup)
    src.symlink_to(backup)
    with pytest.raises(RuntimeError, match="symlink"):
        copy_assets()
    assert not (root / "inputs/c20s4.npz").exists()


def test_copy_detects_corrupted_copy(tmp_path, monkeypatch):
    make_assets(tmp_path, monkeypatch)
    actual = shutil.copy2

    def bad_copy(source, dest):
        actual(source, dest)
        Path(dest).write_bytes(b"corrupted")

    monkeypatch.setattr(shutil, "copy2", bad_copy)
    with pytest.raises(RuntimeError, match="asset copy differs"):
        copy_assets()


@pytest.mark.parametrize("platform", ["Darwin", "Linux"])
def test_platform_or_mount_failure_stops_before_any_remote_write(tmp_path, platform):
    tools = tmp_path / "bin"
    tools.mkdir()
    reached = tmp_path / "forbidden-command"
    for name, body in {
        "uname": "printf '%s\\n' " + platform,
        "mountpoint": "exit 1",
        "id": 'touch "' + str(reached) + '"; exit 1',
        "mkdir": 'touch "' + str(reached) + '"; exit 1',
        "python3": 'touch "' + str(reached) + '"; exit 1',
    }.items():
        p = tools / name
        p.write_text("#!/bin/sh\n" + body + "\n")
        p.chmod(0o755)
    env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"])
    result = subprocess.run(
        ["/bin/bash", str(SCRIPT)], cwd=tmp_path, env=env, capture_output=True
    )
    assert result.returncode != 0
    assert not reached.exists()
