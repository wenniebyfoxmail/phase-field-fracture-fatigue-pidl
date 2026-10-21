"""Bind and prove the frozen task-local dependency root before task imports."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import importlib.util
import getpass
import json
import os
import runpy
import sys
import uuid
from pathlib import Path


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def atomic_write_new(path: Path, payload: dict) -> None:
    if path.exists():
        raise FileExistsError(f"scheduled-context receipt already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    with open(temporary, "xb") as stream:
        stream.write((json.dumps(payload, indent=2) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def spec_record(name: str) -> dict:
    spec = importlib.util.find_spec(name)
    return {
        "name": name,
        "found": spec is not None,
        "origin": None if spec is None else spec.origin,
        "submodule_search_locations": None if spec is None or spec.submodule_search_locations is None else list(spec.submodule_search_locations),
    }


def file_record(path: Path) -> dict:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context-receipt", required=True)
    parser.add_argument("--dependency-root", required=True)
    parser.add_argument("--expected-skimage-sha256", required=True)
    parser.add_argument("--expected-morphology-sha256", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("target_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    receipt = Path(args.context_receipt)
    if receipt.exists():
        raise FileExistsError(f"scheduled-context receipt already exists: {receipt}")
    dependency = Path(args.dependency_root).resolve()
    target = Path(args.target).resolve()
    initial_path = list(sys.path)
    record = {
        "schema": 1,
        "status": "FAIL_SCHEDULED_CONTEXT",
        "run_id": "HQ-ROAD-CENTERLINE-001-R005",
        "observed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sys_executable": sys.executable,
        "sys_prefix": sys.prefix,
        "user": getpass.getuser(),
        "pid": os.getpid(),
        "parent_pid": os.getppid(),
        "argv_sha256": canonical_json_sha(sys.argv),
        "context_receipt_path": str(Path(args.context_receipt).resolve()),
        "cwd": os.getcwd(),
        "pythonpath_before": os.environ.get("PYTHONPATH"),
        "sys_path_before": initial_path,
        "dependency_root": str(dependency),
        "target": str(target),
    }
    try:
        if not dependency.is_dir() or not target.is_file():
            raise FileNotFoundError("frozen dependency root or target missing")
        target_directory = target.parent.resolve()
        for task_name in ("d5_runner.py", "centerline_core.py"):
            if (dependency / task_name).exists():
                raise RuntimeError(f"task module shadow exists in dependency root: {task_name}")
        os.environ["PYTHONPATH"] = str(dependency)
        reserved = {target_directory, dependency}
        remainder = [entry for entry in sys.path if Path(entry or os.getcwd()).resolve() not in reserved]
        sys.path[:] = [str(target_directory), str(dependency)] + remainder
        importlib.invalidate_caches()
        record["pythonpath_after"] = os.environ.get("PYTHONPATH")
        record["sys_path_after"] = list(sys.path)
        record["specs"] = [spec_record(name) for name in ("skimage", "skimage.morphology", "centerline_core", "d5_runner")]
        spec_origins = {item["name"]: item["origin"] for item in record["specs"]}
        for task_name in ("centerline_core", "d5_runner"):
            expected_task = (target_directory / f"{task_name}.py").resolve()
            if spec_origins[task_name] is None or Path(spec_origins[task_name]).resolve() != expected_task:
                raise RuntimeError(f"task module origin mismatch: {task_name}")
        skimage = importlib.import_module("skimage")
        morphology = importlib.import_module("skimage.morphology")
        skimage_init = Path(skimage.__file__).resolve()
        morphology_init = Path(morphology.__file__).resolve()
        expected_skimage = (dependency / "skimage" / "__init__.py").resolve()
        expected_morphology = (dependency / "skimage" / "morphology" / "__init__.py").resolve()
        if skimage_init != expected_skimage or morphology_init != expected_morphology:
            raise RuntimeError("resolved scikit-image package is outside the frozen dependency root")
        if sha256(skimage_init) != args.expected_skimage_sha256 or sha256(morphology_init) != args.expected_morphology_sha256:
            raise RuntimeError("resolved scikit-image initializer hash mismatch")
        record.update({
            "status": "PASS_SCHEDULED_CONTEXT",
            "skimage_version": getattr(skimage, "__version__", None),
            "skimage_initializer": file_record(skimage_init),
            "morphology_initializer": file_record(morphology_init),
            "target_file": file_record(target),
        })
        atomic_write_new(receipt, record)
    except BaseException as error:
        record["error"] = f"{type(error).__name__}: {error}"
        atomic_write_new(receipt, record)
        raise

    target_args = args.target_args[1:] if args.target_args[:1] == ["--"] else args.target_args
    sys.argv = [str(target)] + target_args
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
