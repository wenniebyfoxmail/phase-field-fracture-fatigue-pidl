from __future__ import annotations

from pathlib import Path
import json
import sys

import pytest
import torch

from SENS_tensile.field_computation import NonsmoothSigmoid
from source.model_train import _element_diagnostic_state
from source.rrapinn_producer_observer import (
    descendant_pids,
    parse_compute_memory,
    run_observed_process,
    scan_trace_forbidden,
    trace_has_cwd_change,
)


def test_producer_repair_does_not_change_historical_alpha_decoder():
    constraint = NonsmoothSigmoid(2.0, 1.0e-3)
    raw = torch.tensor([-100.0, -2.0, -1.0, 0.0, 1.0, 2.0, 100.0])
    alpha = constraint(raw)
    assert alpha[0] < 0.0
    assert alpha[-1] > 1.0
    assert torch.allclose(alpha[1:-1], torch.tensor([0.0, 0.25, 0.5, 0.75, 1.0]))


def test_element_diagnostic_state_uses_explicit_hard5_schedule():
    cfg = {
        "explicit_cycle_displacements": [0.03, 0.06, 0.09, 0.12, 0.0],
        "step_offset": 1,
    }
    assert _element_diagnostic_state(0, 0.0, cfg) == {
        "physical_cycle": 0,
        "substep_index": -1,
        "displacement": 0.0,
        "state_label": "hard_alpha_recovery",
    }
    c76 = _element_diagnostic_state(379, 0.12, cfg)
    c82 = _element_diagnostic_state(409, 0.12, cfg)
    assert (c76["physical_cycle"], c76["substep_index"]) == (76, 3)
    assert (c82["physical_cycle"], c82["substep_index"]) == (82, 3)
    with pytest.raises(ValueError, match="displacement"):
        _element_diagnostic_state(379, 0.09, cfg)


def test_gpu_memory_parser_sums_only_observed_descendants():
    output = "101, 20\n202, 31.5\n303, 99\n"
    assert parse_compute_memory(output, {101, 202}) == int(51.5 * 1024 * 1024)
    assert parse_compute_memory(output, {404}) == 0


def test_descendant_pid_closure_from_proc_snapshot(tmp_path: Path):
    for pid, ppid in ((10, 1), (11, 10), (12, 11), (20, 1)):
        node = tmp_path / str(pid)
        node.mkdir()
        (node / "stat").write_text(
            f"{pid} (python) S {ppid} 0 0 0 0 0 0\n", encoding="utf-8"
        )
    assert descendant_pids(10, tmp_path) == {10, 11, 12}


def test_strace_ledger_detects_absolute_and_relative_forbidden_paths(tmp_path: Path):
    heldout_11 = tmp_path / "heldout_U0.11"
    heldout_13 = tmp_path / "heldout_U0.13"
    trace = tmp_path / "trace.log"
    trace.write_text(
        f'1 openat(AT_FDCWD, "{heldout_11}/truth.npy", O_RDONLY) = 3\n'
        '1 stat("heldout_U0.13/field.npz", 0x0) = 0\n',
        encoding="utf-8",
    )
    assert scan_trace_forbidden(
        trace,
        cwd=tmp_path,
        forbidden_prefixes=[heldout_11, heldout_13],
    ) == sorted([str(heldout_11 / "truth.npy"), str(heldout_13 / "field.npz")])


def test_strace_ledger_flags_cwd_change_as_unresolvable(tmp_path: Path):
    trace = tmp_path / "trace.log"
    trace.write_text(
        '1 chdir("elsewhere") = 0\n1 openat(AT_FDCWD, "field.npz", O_RDONLY) = 3\n',
        encoding="utf-8",
    )
    assert trace_has_cwd_change(trace) is True


def test_strace_ledger_detects_relative_openat_through_directory_fd(tmp_path: Path):
    heldout = tmp_path / "heldout_U0.13"
    trace = tmp_path / "trace.log"
    trace.write_text(
        f'1 openat(7<{heldout}>, "truth.npy", O_RDONLY) = 8<{heldout}/truth.npy>\n',
        encoding="utf-8",
    )
    assert scan_trace_forbidden(
        trace, cwd=tmp_path, forbidden_prefixes=[heldout]
    ) == [str(heldout / "truth.npy")]


def test_external_observer_writes_portable_bound_receipts(tmp_path: Path, monkeypatch):
    fake_strace = tmp_path / "strace"
    fake_strace.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, subprocess, sys\n"
        "args = sys.argv[1:]\n"
        "trace = pathlib.Path(args[args.index('-o') + 1])\n"
        "trace.write_text('1 openat(AT_FDCWD, \\\"/usr/lib/libc.so\\\", O_RDONLY) = 3\\n')\n"
        "command = args[args.index('--') + 1:]\n"
        "raise SystemExit(subprocess.call(command))\n",
        encoding="utf-8",
    )
    fake_strace.chmod(0o755)
    monkeypatch.setattr(
        "source.rrapinn_producer_observer.require_observer_tools",
        lambda: {"strace": str(fake_strace), "nvidia-smi": "/fake/nvidia-smi"},
    )
    runtime = tmp_path / "runtime.json"
    access = tmp_path / "access.json"
    trace = tmp_path / "trace.log"
    result = run_observed_process(
        command=[
            sys.executable,
            "-c",
            "import time; print('idx: 301;', flush=True); time.sleep(0.02); "
            "print('idx: 302;', flush=True)",
        ],
        cwd=tmp_path,
        stdout_log=tmp_path / "stdout.log",
        runtime_receipt=runtime,
        path_access_receipt=access,
        path_access_trace=trace,
        forbidden_prefixes=[tmp_path / "heldout_U0.11", tmp_path / "heldout_U0.13"],
        required_steps=[301],
        sample_interval_seconds=0.005,
        memory_query=lambda _pid: 4096,
    )
    assert result["runtime"]["status"] == "PASS"
    receipt = json.loads(access.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS"
    assert receipt["raw_trace"]["path"] == trace.name


def test_external_observer_exception_still_writes_fail_receipts(
    tmp_path: Path, monkeypatch,
):
    fake_strace = tmp_path / "strace"
    fake_strace.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, subprocess, sys\n"
        "args = sys.argv[1:]\n"
        "pathlib.Path(args[args.index('-o') + 1]).write_text('')\n"
        "raise SystemExit(subprocess.call(args[args.index('--') + 1:]))\n",
        encoding="utf-8",
    )
    fake_strace.chmod(0o755)
    monkeypatch.setattr(
        "source.rrapinn_producer_observer.require_observer_tools",
        lambda: {"strace": str(fake_strace), "nvidia-smi": "/fake/nvidia-smi"},
    )
    runtime = tmp_path / "runtime.json"
    access = tmp_path / "access.json"
    with pytest.raises(RuntimeError, match="path-access ledger failed"):
        run_observed_process(
            command=[
                sys.executable,
                "-c",
                "import time; print('idx: 301;', flush=True); time.sleep(0.02); "
                "print('idx: 301;', flush=True); time.sleep(0.02)",
            ],
            cwd=tmp_path,
            stdout_log=tmp_path / "stdout.log",
            runtime_receipt=runtime,
            path_access_receipt=access,
            path_access_trace=tmp_path / "trace.log",
            forbidden_prefixes=[
                tmp_path / "heldout_U0.11", tmp_path / "heldout_U0.13"
            ],
            required_steps=[301],
            sample_interval_seconds=0.005,
            memory_query=lambda _pid: 4096,
        )
    runtime_payload = json.loads(runtime.read_text(encoding="utf-8"))
    access_payload = json.loads(access.read_text(encoding="utf-8"))
    assert runtime_payload["status"] == "FAIL"
    assert access_payload["status"] == "FAIL"
    assert "duplicate producer raw step" in runtime_payload["observer_error"]
