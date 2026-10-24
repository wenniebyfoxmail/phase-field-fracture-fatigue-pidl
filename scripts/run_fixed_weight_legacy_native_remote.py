"""Windows-local controller for an explicitly staged legacy verifier.

Start this controller with the explicit py launcher and -3 -B -s -P. It requires
CPython >= 3.11 with those three Python flags enabled and an existing absolute
launcher file path; launcher names and PATH lookup are rejected.
This standard-library transport does not use SSH or inspect archive contents.
It invokes that py launcher with -3 -B -s -P -u, streams stdout/stderr into
exclusive binary files, then atomically publishes execution.json. The source
commit identifies the staged verifier bundle, not this controller's commit.
runner_started means Popen successfully launched the command; it does not mean
the verifier completed or an archive passed. Use the independent receipt checker
after retrieving these files. Existing output files are never replaced.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time


SCHEMA = "fixed_weight_legacy_controller_execution_v1"
OUTPUT_NAMES = ("receipt.jsonl", "stderr.txt", "execution.json")
LOCK_NAME = ".legacy_controller.lock"


def require_controller_runtime():
    """Fail before output creation unless the controller has the required flags."""
    if sys.implementation.name != "cpython" or sys.version_info < (3, 11):
        raise ValueError("controller requires CPython >= 3.11")
    required = {"dont_write_bytecode": "-B", "no_user_site": "-s", "safe_path": "-P"}
    missing = [flag for name, flag in required.items() if not getattr(sys.flags, name, False)]
    if missing:
        raise ValueError("controller must be launched with -3 -B -s -P; missing " + " ".join(missing))


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def absolute_path(value, label):
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(label + " must be an absolute local path")
    return path.resolve()


def refuse_existing_outputs(root):
    existing = [name for name in OUTPUT_NAMES if os.path.lexists(root / name)]
    if existing:
        raise FileExistsError("refusing existing output: " + ", ".join(existing))


def publish_execution(path, value):
    """Publish a complete file atomically without replacing an existing file.

    Windows rename refuses an existing destination. The link operation gives
    the same no-replace behavior for local POSIX synthetic tests. Both operate
    within one directory/filesystem; neither exposes a partially written JSON.
    """
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent,
                                         prefix=".execution-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(value, sort_keys=True, indent=2,
                                    allow_nan=False).encode("utf-8") + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        if os.name == "nt":
            os.rename(temporary, path)  # Atomic and fails if execution.json already exists.
        else:
            os.link(temporary, path)
        temporary.unlink(missing_ok=True)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run_controller(*, py_launcher, run_root, runner, source_dir, deps_dir,
                   archive_roots, verifier_source_commit):
    """Run one local child; platform-neutral only to permit synthetic tests.

    Production entry through main is restricted to Windows. Archives are only
    passed as command arguments; this function never opens their members.
    """
    require_controller_runtime()
    if not isinstance(py_launcher, str) or not py_launcher or "\x00" in py_launcher:
        raise ValueError("py_launcher must be an existing absolute executable file path")
    launcher = absolute_path(py_launcher, "py launcher")
    if not launcher.is_file():
        raise ValueError("py launcher must be an existing absolute executable file path")
    if not isinstance(verifier_source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", verifier_source_commit):
        raise ValueError("verifier_source_commit must be a full lowercase Git commit")
    root = absolute_path(run_root, "run root")
    runner = absolute_path(runner, "runner")
    source = absolute_path(source_dir, "source directory")
    deps = absolute_path(deps_dir, "dependency directory")
    archives = [absolute_path(path, "archive root") for path in archive_roots]
    if len(archives) != 3 or len(set(archives)) != 3:
        raise ValueError("exactly three distinct archive roots are required")
    if any(root == a or root.is_relative_to(a) or a.is_relative_to(root) for a in archives):
        raise ValueError("run root and archive roots must not overlap")
    if not runner.is_file() or not source.is_dir() or not deps.is_dir():
        raise ValueError("staged runner, source directory and dependency directory must exist")
    # The runner binds this exact sibling source layout in verifier_fingerprint.
    if (runner.name != "validate_fixed_weight_legacy_native_archives.py" or
            runner.parent.name != "scripts" or source != runner.parent.parent / "source"):
        raise ValueError("runner/source must retain the staged scripts/ and source/ bundle layout")
    refuse_existing_outputs(root)
    root.mkdir(parents=True, exist_ok=True)
    lock = root / LOCK_NAME
    # Exclusive claim prevents two cooperating controllers racing for this run.
    lock_handle = lock.open("xb")
    try:
        lock_handle.write(json.dumps({"controller_pid": os.getpid()}).encode("ascii"))
        lock_handle.close()
        refuse_existing_outputs(root)
        command = [str(launcher), "-3", "-B", "-s", "-P", "-u", str(runner), *(str(a) for a in archives)]
        environment = os.environ.copy()
        environment.update({
            "PYTHONPATH": os.pathsep.join((str(source), str(deps))),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
            "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2",
            "CUDA_VISIBLE_DEVICES": "",
        })
        controller_path = Path(__file__).resolve()
        controller_hash = sha256_file(controller_path)
        started_utc, started = utc_now(), time.monotonic()
        runner_started, launcher_error, process = False, None, None
        exit_code = 127
        with ExitStack() as stack:
            stdout = stack.enter_context((root / "receipt.jsonl").open("xb"))
            stderr = stack.enter_context((root / "stderr.txt").open("xb"))
            try:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                           stdout=stdout, stderr=stderr, cwd=root,
                                           env=environment, shell=False)
            except OSError as exc:
                launcher_error = {"type": type(exc).__name__, "message": str(exc)}
            else:
                runner_started = True
                try:
                    exit_code = process.wait()
                except BaseException:
                    # Never publish a terminal receipt while an owned child is
                    # still running. On interruption, stop only this child and
                    # propagate the exception; the incomplete attempt is kept.
                    process.terminate()
                    process.wait()
                    raise
            for handle in (stdout, stderr):
                handle.flush()
                os.fsync(handle.fileno())
        execution = {
            "schema": SCHEMA, "exit_code": exit_code,
            "verifier_source_commit": verifier_source_commit,
            "receipt_sha256": sha256_file(root / "receipt.jsonl"),
            "stderr_sha256": sha256_file(root / "stderr.txt"),
            "controller_sha256": controller_hash, "controller_path": str(controller_path),
            "runner_started": runner_started, "launcher_error": launcher_error,
            "hostname": socket.gethostname(), "controller_pid": os.getpid(),
            "runner_pid": None if process is None else process.pid,
            "command": command, "run_root": str(root), "runner": str(runner),
            "source_dir": str(source), "deps_dir": str(deps),
            "archive_roots": [str(a) for a in archives],
            "start_utc": started_utc, "end_utc": utc_now(),
            "wall_seconds": time.monotonic() - started,
            "training": False, "solver": False, "originals_modified": False,
        }
        publish_execution(root / "execution.json", execution)
        return exit_code
    finally:
        lock_handle.close()
        lock.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--py-launcher", required=True, help="existing absolute py executable file path, also used to start this controller with -3 -B -s -P; child arguments are fixed to -3 -B -s -P -u; no PATH lookup")
    parser.add_argument("--run-root", type=Path, required=True, help="local output directory; output names must not already exist")
    parser.add_argument("--runner", type=Path, required=True, help="absolute staged scripts/validate_fixed_weight_legacy_native_archives.py path")
    parser.add_argument("--source-dir", type=Path, required=True, help="absolute sibling staged source/ directory")
    parser.add_argument("--deps-dir", type=Path, required=True, help="absolute task-owned Python dependency directory")
    parser.add_argument("--archive-roots", type=Path, nargs=3, required=True, help="three explicit original archive roots, in approved order")
    parser.add_argument("--verifier-source-commit", required=True, help="full source commit of the staged verifier bundle, not a later controller/checker HEAD")
    args = parser.parse_args(argv)
    if os.name != "nt":
        parser.error("launch this controller locally on Windows; Mac is for synthetic tests only")
    try:
        return run_controller(**vars(args))
    except (OSError, ValueError) as exc:
        print(f"controller refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
