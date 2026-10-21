"""Bind and prove the frozen task-local dependency root before task imports."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import importlib.machinery
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
    stat = path.stat()
    return {"path": str(path), "bytes": stat.st_size, "sha256": sha256(path),
            "readable": os.access(path, os.R_OK), "mtime_ns": stat.st_mtime_ns}


def module_record(name: str) -> dict:
    module = sys.modules.get(name)
    if module is None:
        return {"name": name, "present": False}
    spec = getattr(module, "__spec__", None)
    return {
        "name": name,
        "present": True,
        "file": getattr(module, "__file__", None),
        "path": None if getattr(module, "__path__", None) is None else list(module.__path__),
        "spec_origin": None if spec is None else spec.origin,
        "loader_type": None if spec is None or spec.loader is None else type(spec.loader).__name__,
    }


def finder_record(name: str, path: list[str]) -> dict:
    spec = importlib.machinery.PathFinder.find_spec(name, path)
    return {
        "name": name,
        "found": spec is not None,
        "origin": None if spec is None else spec.origin,
        "loader_type": None if spec is None or spec.loader is None else type(spec.loader).__name__,
        "submodule_search_locations": None if spec is None or spec.submodule_search_locations is None else list(spec.submodule_search_locations),
    }


def load_explicit_package(name: str, initializer: Path, package_directory: Path):
    spec = importlib.util.spec_from_file_location(
        name, initializer, submodule_search_locations=[str(package_directory)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot create standard package spec for {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context-receipt", required=True)
    parser.add_argument("--dependency-root", required=True)
    parser.add_argument("--expected-skimage-sha256", required=True)
    parser.add_argument("--expected-morphology-sha256", required=True)
    parser.add_argument("--expected-skimage-version", required=True)
    parser.add_argument("--expected-skeletonize-sha256", required=True)
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
        "run_id": "HQ-ROAD-CENTERLINE-001-R006",
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
        skimage_init = (dependency / "skimage" / "__init__.py").resolve()
        morphology_init = (dependency / "skimage" / "morphology" / "__init__.py").resolve()
        if not skimage_init.is_file() or not morphology_init.is_file():
            raise FileNotFoundError("frozen skimage or morphology initializer missing")
        if sha256(skimage_init) != args.expected_skimage_sha256 or sha256(morphology_init) != args.expected_morphology_sha256:
            raise RuntimeError("frozen scikit-image initializer hash mismatch")
        record["pythonpath_after"] = os.environ.get("PYTHONPATH")
        record["sys_path_after"] = list(sys.path)
        record["pre_binding"] = {
            "pid": os.getpid(),
            "principal": getpass.getuser(),
            "argv": list(sys.argv),
            "modules": [module_record(name) for name in sorted(name for name in sys.modules if name == "skimage" or name.startswith("skimage."))],
            "pathfinder": [
                finder_record("skimage", [str(dependency)]),
                finder_record("skimage.morphology", [str(dependency / "skimage")]),
            ],
            "files": [file_record(skimage_init), file_record(morphology_init)],
        }
        removed_modules = sorted(name for name in sys.modules if name == "skimage" or name.startswith("skimage."))
        for name in removed_modules:
            del sys.modules[name]
        skimage = load_explicit_package("skimage", skimage_init, skimage_init.parent)
        morphology = load_explicit_package("skimage.morphology", morphology_init, morphology_init.parent)
        setattr(skimage, "morphology", morphology)
        skeletonize = getattr(morphology, "skeletonize")
        skeletonize_module = importlib.import_module(skeletonize.__module__)
        skeletonize_source = Path(skeletonize_module.__file__).resolve()
        expected_skimage = skimage_init
        expected_morphology = morphology_init
        expected_skimage_path = [str(skimage_init.parent)]
        expected_morphology_path = [str(morphology_init.parent)]
        for module, expected_file, expected_path, label in (
            (skimage, expected_skimage, expected_skimage_path, "skimage"),
            (morphology, expected_morphology, expected_morphology_path, "skimage.morphology"),
        ):
            spec = getattr(module, "__spec__", None)
            if Path(module.__file__).resolve() != expected_file:
                raise RuntimeError(f"{label} __file__ mismatch")
            if spec is None or spec.origin is None or Path(spec.origin).resolve() != expected_file:
                raise RuntimeError(f"{label} spec origin mismatch")
            if not isinstance(spec.loader, importlib.machinery.SourceFileLoader):
                raise RuntimeError(f"{label} loader is not SourceFileLoader")
            if list(getattr(module, "__path__", [])) != expected_path:
                raise RuntimeError(f"{label} package path mismatch")
        if getattr(skimage, "__version__", None) != args.expected_skimage_version:
            raise RuntimeError("skimage version mismatch")
        expected_skeletonize_source = (dependency / Path(*skeletonize.__module__.split("."))).with_suffix(".py").resolve()
        if skeletonize_source != expected_skeletonize_source:
            raise RuntimeError("skeletonize implementation path mismatch")
        if sha256(skeletonize_source) != args.expected_skeletonize_sha256:
            raise RuntimeError("skeletonize implementation hash mismatch")
        record["explicit_binding"] = {
            "removed_preexisting_modules": removed_modules,
            "skimage": module_record("skimage"),
            "morphology": module_record("skimage.morphology"),
            "skimage_version": getattr(skimage, "__version__", None),
            "skeletonize_module": skeletonize.__module__,
            "skeletonize_source": str(skeletonize_source),
            "skeletonize_source_sha256": sha256(skeletonize_source),
            "pid": os.getpid(),
        }
        record["specs"] = [spec_record(name) for name in ("skimage", "skimage.morphology", "centerline_core", "d5_runner")]
        spec_origins = {item["name"]: item["origin"] for item in record["specs"]}
        for task_name in ("centerline_core", "d5_runner"):
            expected_task = (target_directory / f"{task_name}.py").resolve()
            if spec_origins[task_name] is None or Path(spec_origins[task_name]).resolve() != expected_task:
                raise RuntimeError(f"task module origin mismatch: {task_name}")
        resolved_skimage_init = Path(skimage.__file__).resolve()
        resolved_morphology_init = Path(morphology.__file__).resolve()
        if resolved_skimage_init != expected_skimage or resolved_morphology_init != expected_morphology:
            raise RuntimeError("resolved scikit-image package is outside the frozen dependency root")
        if sha256(resolved_skimage_init) != args.expected_skimage_sha256 or sha256(resolved_morphology_init) != args.expected_morphology_sha256:
            raise RuntimeError("resolved scikit-image initializer hash mismatch")
        if dependency not in skeletonize_source.parents:
            raise RuntimeError("skeletonize implementation resolved outside frozen dependency root")
        record.update({
            "status": "PASS_SCHEDULED_CONTEXT",
            "skimage_version": getattr(skimage, "__version__", None),
            "skimage_initializer": file_record(resolved_skimage_init),
            "morphology_initializer": file_record(resolved_morphology_init),
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
