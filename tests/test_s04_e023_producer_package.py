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
    / "docs/research/S04/S04-E023/producer/prepare_and_dispatch.sh"
)


def python_block(name):
    return re.search(r"<<'" + name + r"'\n(.*?)\n" + name, SCRIPT.read_text(), re.S)[1]


def make_assets(tmp_path, monkeypatch):
    old, root, code = [tmp_path / n for n in ("old", "new", "code")]
    root.mkdir()
    code.mkdir()
    locks = {}
    directs = {}
    previous = tmp_path / "previous"
    leak = tmp_path / "leak"
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
        direct_id = "direct-" + state
        directnames = names + [
            "learning_rates.npy",
            "expected_learning_rates.npy",
            "coordinate_map.json",
            "PRE_UPDATE.json",
        ]
        directs[state] = dict(
            run_id=direct_id, files={n: "unused-in-copy-stage" for n in directnames}
        )
        files = [old / "inputs" / (state + ".npz")]
        files += [old / "backbones" / state / n for n in names]
        files += [old / "runs" / rid / n for n in names]
        for p in files:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(str(p.relative_to(old)).encode())
        for name in directnames:
            direct = previous / "runs" / direct_id / name
            direct.parent.mkdir(parents=True, exist_ok=True)
            direct.write_bytes(name.encode())
    leakconfig = code / "docs/research/S04/S04-E023/e022_control_locks.json"
    leakconfig.parent.mkdir(parents=True)
    leakconfig.write_text(json.dumps(directs))
    for state, entry in directs.items():
        for name in entry["files"]:
            p = leak / "runs" / entry["run_id"] / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(name.encode())
    monkeypatch.setenv("E023_BASE22", str(leak))
    directconfig = code / "docs/research/S04/S04-E022/e021_control_locks.json"
    directconfig.parent.mkdir(parents=True)
    directconfig.write_text(json.dumps(directs))
    monkeypatch.setenv("E023_BASE21", str(previous))
    config = code / "docs/research/S04/S04-E020/control_locks.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps(locks))
    monkeypatch.chdir(code)
    monkeypatch.setenv("E023_ROOT", str(root))
    monkeypatch.setenv("E023_BASE19", str(old))
    return old, root


def copy_assets():
    exec(compile(python_block("COPY"), "deployment:COPY", "exec"), {})


def test_copy_manifest_matches_all_87_originals(tmp_path, monkeypatch):
    old, root = make_assets(tmp_path, monkeypatch)
    copy_assets()
    rows = json.loads((root / "asset_copy_manifest.json").read_text())
    assert len(rows) == 87
    for row in rows:
        source, dest = Path(row["source"]), Path(row["destination"])
        assert (
            source.is_relative_to(old)
            or source.is_relative_to(tmp_path / "previous")
            or source.is_relative_to(tmp_path / "leak")
        ) and dest.is_relative_to(root)
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


@pytest.mark.parametrize("mode", ["valid", "changed_bytes", "coherent_wrong_D"])
def test_actual_row_guard_checks_frozen_D_bytes_and_recomputation(tmp_path, mode):
    import copy

    root = tmp_path
    state = "c20s4"
    rid = "row"
    (root / "logs").mkdir()
    data = {
        "head_calibration": {"scale": [1.0, 2.0]},
        "head_gradient_preflight": {"error": 0.0},
    }
    row = {"state": state}
    for folder, key, field in (
        ("preflight_head_scales", "head_calibration", "head_scale_sha256"),
        (
            "preflight_head_gradients",
            "head_gradient_preflight",
            "head_gradient_preflight_sha256",
        ),
    ):
        (root / folder).mkdir()
        p = root / folder / (state + ".json")
        p.write_text(json.dumps(data[key], indent=2, allow_nan=False))
        row[field] = hashlib.sha256(p.read_bytes()).hexdigest()
    record = {"rows": [row]}
    if mode != "valid":
        p = root / "preflight_head_scales" / f"{state}.json"
        p.write_text(json.dumps({"scale": [2.0, 3.0]}, indent=2))
        if mode == "coherent_wrong_D":
            row["head_scale_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    block = python_block("ROW_PREFLIGHT")
    code = block[block.index("row=next(") :]
    scope = dict(
        hashlib=hashlib,
        json=json,
        root=root,
        state=state,
        rid=rid,
        record=record,
        data=data,
    )
    if mode == "valid":
        exec(compile(code, "deployment:ROW_GUARD", "exec"), scope)
        assert (root / "logs" / f"{rid}.preflight.json").exists()
    else:
        with pytest.raises(RuntimeError):
            exec(compile(code, "deployment:ROW_GUARD", "exec"), scope)
