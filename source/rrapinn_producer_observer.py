"""External Linux observer for PIDL step runtime, GPU memory, and file access."""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence


STEP_RE = re.compile(r"\bidx:\s*(\d+)\s*;")
QUOTED_PATH_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
DIRFD_RELATIVE_RE = re.compile(
    r"\b\w*at\d*\(\d+<(/[^>]*)>,\s*\"((?:[^\"\\]|\\.)*)\""
)
CWD_CHANGE_RE = re.compile(r"\b(?:chdir|fchdir)\(")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command_sha256(command: Sequence[str]) -> str:
    payload = (json.dumps(list(command), separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def path_policy_sha256(forbidden_prefixes: Sequence[Path]) -> str:
    roots = [str(path.expanduser().resolve()) for path in forbidden_prefixes]
    payload = (json.dumps(roots, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def require_observer_tools() -> dict[str, str]:
    tools = {name: shutil.which(name) for name in ("strace", "nvidia-smi")}
    missing = [name for name, path in tools.items() if not path]
    if missing:
        raise RuntimeError(f"required external observer tools are missing: {missing}")
    try:
        subprocess.run(
            [str(tools["strace"]), "-yy", "-e", "trace=none", "-o", os.devnull,
             "--", "true"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        subprocess.run(
            [str(tools["nvidia-smi"]), "--query-compute-apps=pid,used_gpu_memory",
             "--format=csv,noheader,nounits"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("external observer lacks required -yy/GPU query capability") from exc
    return {name: str(path) for name, path in tools.items()}


def descendant_pids(root_pid: int, proc_root: Path = Path("/proc")) -> set[int]:
    parents: dict[int, int] = {}
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text(encoding="utf-8").split()
            parents[int(entry.name)] = int(fields[3])
        except (FileNotFoundError, PermissionError, ValueError, IndexError):
            continue
    result = {int(root_pid)}
    changed = True
    while changed:
        changed = False
        for pid, ppid in parents.items():
            if ppid in result and pid not in result:
                result.add(pid)
                changed = True
    return result


def parse_compute_memory(output: str, observed_pids: Iterable[int]) -> int:
    observed = {int(pid) for pid in observed_pids}
    total_mib = 0.0
    matched = False
    for line in output.splitlines():
        fields = [part.strip() for part in line.split(",")]
        if len(fields) != 2 or not fields[0].isdigit():
            continue
        if int(fields[0]) not in observed:
            continue
        try:
            total_mib += float(fields[1])
        except ValueError as exc:
            raise RuntimeError("nvidia-smi returned non-numeric used memory") from exc
        matched = True
    return int(total_mib * 1024 * 1024) if matched else 0


def query_compute_memory(root_pid: int) -> int:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_gpu_memory",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError):
        # A transient observer failure must not abort before receipts are written.
        # Persistent failures remain fail-closed through missing peak-memory steps.
        return 0
    return parse_compute_memory(output, descendant_pids(root_pid))


def scan_trace_forbidden(
    trace_path: Path, *, cwd: Path, forbidden_prefixes: Sequence[Path],
) -> list[str]:
    roots = [path.expanduser().resolve() for path in forbidden_prefixes]
    matches: set[str] = set()
    for line in trace_path.read_text(encoding="utf-8", errors="replace").splitlines():
        for directory, encoded in DIRFD_RELATIVE_RE.findall(line):
            try:
                relative = bytes(encoded, "utf-8").decode("unicode_escape")
            except UnicodeDecodeError:
                relative = encoded
            resolved = (Path(directory) / relative).resolve()
            if any(resolved == root or root in resolved.parents for root in roots):
                matches.add(str(resolved))
        for encoded in QUOTED_PATH_RE.findall(line):
            try:
                raw = bytes(encoded, "utf-8").decode("unicode_escape")
            except UnicodeDecodeError:
                raw = encoded
            candidate = Path(raw).expanduser()
            resolved = candidate.resolve() if candidate.is_absolute() else (cwd / candidate).resolve()
            if any(resolved == root or root in resolved.parents for root in roots):
                matches.add(str(resolved))
    return sorted(matches)


def trace_has_cwd_change(trace_path: Path) -> bool:
    """Reject traces whose relative paths cannot be resolved from the launch cwd."""
    return any(
        CWD_CHANGE_RE.search(line)
        for line in trace_path.read_text(encoding="utf-8", errors="replace").splitlines()
    )


def _write_json_exclusive(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def run_observed_process(
    *,
    command: Sequence[str],
    cwd: Path,
    stdout_log: Path,
    runtime_receipt: Path,
    path_access_receipt: Path,
    path_access_trace: Path,
    forbidden_prefixes: Sequence[Path],
    required_steps: Sequence[int],
    sample_interval_seconds: float = 0.25,
    memory_query: Callable[[int], int] = query_compute_memory,
) -> dict:
    """Run one producer command and emit exclusive external-observer receipts."""
    tools = require_observer_tools()
    if not forbidden_prefixes:
        raise ValueError("at least one forbidden path prefix is required")
    if sample_interval_seconds <= 0.0:
        raise ValueError("sample interval must be positive")
    required = [int(step) for step in required_steps]
    if not required or len(required) != len(set(required)):
        raise ValueError("required observer steps must be non-empty and unique")
    outputs = (stdout_log, runtime_receipt, path_access_receipt, path_access_trace)
    if any(path.exists() for path in outputs):
        raise FileExistsError("observer outputs are exclusive-create artifacts")
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)

    command = [str(value) for value in command]
    traced_command = [
        tools["strace"], "-f", "-qq", "-yy", "-s", "4096", "-e", "trace=%file",
        "-o", str(path_access_trace.resolve()), "--", *command,
    ]
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    started_utc = _utc_now()
    started = time.monotonic()
    wall_start: dict[int, float] = {}
    wall_seconds: dict[int, float] = {}
    peak_memory: dict[int, int] = {}
    current_step: int | None = None
    process_returncode: int | None = None
    observer_error: str | None = None
    process: subprocess.Popen | None = None

    try:
        with stdout_log.open("x", encoding="utf-8") as log:
            process = subprocess.Popen(
                traced_command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            if process.stdout is None:
                raise RuntimeError("observer could not open producer stdout")
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                for key, _ in selector.select(timeout=sample_interval_seconds):
                    line = key.fileobj.readline()
                    if not line:
                        continue
                    log.write(line)
                    log.flush()
                    match = STEP_RE.search(line)
                    if match:
                        observed_at = time.monotonic()
                        next_step = int(match.group(1))
                        if current_step is not None and current_step not in wall_seconds:
                            wall_seconds[current_step] = observed_at - wall_start[current_step]
                        current_step = next_step
                        if current_step in wall_start:
                            raise RuntimeError(
                                f"duplicate producer raw step observed: {current_step}"
                            )
                        wall_start[current_step] = observed_at
                        peak_memory.setdefault(current_step, 0)
                if current_step is not None:
                    sample = int(memory_query(process.pid))
                    if sample < 0:
                        raise RuntimeError(
                            "external memory observer returned a negative sample"
                        )
                    peak_memory[current_step] = max(peak_memory[current_step], sample)
                process_returncode = process.poll()
                if process_returncode is not None:
                    for line in process.stdout:
                        log.write(line)
                    log.flush()
                    break
    except Exception as exc:  # receipts below preserve the fail-closed reason
        observer_error = f"{type(exc).__name__}: {exc}"
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        process_returncode = process.returncode if process is not None else -1
    if current_step is not None and current_step not in wall_seconds:
        wall_seconds[current_step] = time.monotonic() - wall_start[current_step]

    ended_utc = _utc_now()
    missing_wall = [step for step in required if step not in wall_seconds]
    missing_memory = [step for step in required if peak_memory.get(step, 0) <= 0]
    runtime_ok = (
        observer_error is None
        and process_returncode == 0
        and not missing_wall
        and not missing_memory
    )
    wall_selected = {str(step): wall_seconds[step] for step in required if step in wall_seconds}
    memory_selected = {str(step): peak_memory[step] for step in required if step in peak_memory}
    runtime_payload = {
        "schema": "rrapinn-g4-external-runtime-v2",
        "observer": "external_launcher_strace_nvidia_smi",
        "status": "PASS" if runtime_ok else "FAIL",
        "started_utc": started_utc,
        "ended_utc": ended_utc,
        "elapsed_seconds": time.monotonic() - started,
        "command_sha256": command_sha256(command),
        "command": command,
        "path_policy_sha256": path_policy_sha256(forbidden_prefixes),
        "common_raw_step_start": min(required),
        "common_raw_step_end": max(required),
        "sample_interval_seconds": float(sample_interval_seconds),
        "wall_time_seconds_by_raw_step": wall_selected,
        "peak_memory_bytes_by_raw_step": memory_selected,
        "wall_time_per_step_seconds": (
            sum(wall_selected.values()) / len(wall_selected) if wall_selected else None
        ),
        "peak_memory_bytes": max(memory_selected.values()) if memory_selected else None,
        "memory_metric": "sampled_descendant_process_max_bytes",
        "missing_wall_steps": missing_wall,
        "missing_peak_memory_steps": missing_memory,
        "producer_returncode": process_returncode,
        "observer_error": observer_error,
    }
    _write_json_exclusive(runtime_receipt, runtime_payload)

    trace_exists = path_access_trace.is_file()
    matches = scan_trace_forbidden(
        path_access_trace, cwd=cwd, forbidden_prefixes=forbidden_prefixes,
    ) if trace_exists else ["<trace_missing>"]
    cwd_changed = trace_has_cwd_change(path_access_trace) if trace_exists else False
    path_ok = (
        observer_error is None
        and process_returncode == 0
        and trace_exists
        and not matches
        and not cwd_changed
    )
    portable_trace_path = os.path.relpath(
        path_access_trace.resolve(), path_access_receipt.parent.resolve()
    )
    path_payload = {
        "schema": "rrapinn-host-path-access-v1",
        "observer": "strace_file_syscalls_follow_forks",
        "status": "PASS" if path_ok else "FAIL",
        "started_utc": started_utc,
        "ended_utc": ended_utc,
        "command_sha256": command_sha256(command),
        "command": command,
        "path_policy_sha256": path_policy_sha256(forbidden_prefixes),
        "producer_cwd": str(cwd.resolve()),
        "forbidden_path_prefixes": [str(path.expanduser().resolve()) for path in forbidden_prefixes],
        "matched_forbidden_paths": matches,
        "cwd_change_syscalls_observed": cwd_changed,
        "raw_trace": {
            "path": portable_trace_path,
            "sha256": sha256_file(path_access_trace) if trace_exists else None,
        },
        "follow_forks": True,
        "fd_paths_decoded": True,
        "producer_returncode": process_returncode,
        "observer_error": observer_error,
    }
    _write_json_exclusive(path_access_receipt, path_payload)
    if not path_ok:
        raise RuntimeError("host path-access ledger failed closed")
    if not runtime_ok:
        raise RuntimeError("external runtime/peak-memory receipt failed closed")
    return {"runtime": runtime_payload, "path_access": path_payload}
