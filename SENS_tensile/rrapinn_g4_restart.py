"""Fail-closed validation and staging for the frozen G4 c60 restart bundle."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import ctypes
import errno
import platform
from pathlib import Path

import numpy as np


SCHEMA = "rrapinn-g4-c60-restart-bundle-v1"
START_STEP = 300
HISTORY_LENGTH = START_STEP + 1
REQUIRED_FILES = {
    "trained_1NN_initTraining.pt",
    "trained_1NN_300.pt",
    "checkpoint_step_300.pt",
    "E_el_vs_cycle.npy",
    "alpha_bar_vs_cycle.npy",
    "x_tip_alpha_vs_cycle.npy",
    "x_tip_vs_cycle.npy",
    "Kt_vs_cycle.npy",
    "time_vs_cycle.npy",
    "energy_gradient_terms_vs_cycle.npy",
}
SOURCE_SETTINGS_SHA256 = "015fe8ddf563b2b9d81b8a681705e2a35f9044206311a6a7e26f40a7dc9c1047"
SOURCE_MESH_SHA256 = "16b447e3dd789e300f5181c3cf9b34322e4f27575867b354f55473d2969a9ed8"
HISTORY_ROLES = {
    "E_el_vs_cycle.npy": "elastic_energy_history",
    "alpha_bar_vs_cycle.npy": "mean_damage_history",
    "x_tip_alpha_vs_cycle.npy": "damage_tip_history",
    "x_tip_vs_cycle.npy": "damage_tip_history_legacy_alias",
    "Kt_vs_cycle.npy": "stress_intensity_history",
    "time_vs_cycle.npy": "runtime_history",
    "energy_gradient_terms_vs_cycle.npy": "energy_gradient_history",
}
MODEL_ROLES = {
    "trained_1NN_initTraining.pt": "pretraining_state",
    "trained_1NN_300.pt": "restart_model_state",
    "checkpoint_step_300.pt": "restart_fatigue_state",
}
FROZEN_FILE_SOURCE_SHA256 = {
    "trained_1NN_initTraining.pt": "1044740e0004fe11688ec4930a4c3ea25cf0bd252bb66b29e6ddca6bbeb07a9e",
    "trained_1NN_300.pt": "1316984f53297075dccadd38efd04972ce3942caa294b4b0a4f61c3c87b10d41",
    "checkpoint_step_300.pt": "771bf8122c34097ddaee55e9952c3bef187aa320dfcd02eed148febe6e10e729",
    "E_el_vs_cycle.npy": "0ae5520c58431f80615b54534f3395b12f65ee76a8f7831a0edd2caf9723ae71",
    "alpha_bar_vs_cycle.npy": "10d23fd4ce8e6b87ed7b9117e94ebadbcf401362cb2b8a9674961876d2aa8cc1",
    "x_tip_alpha_vs_cycle.npy": "ba24cd21ec5d4a497bcf4c75eda72b034e1853c82327b87b0c26724f8723b1d2",
    "x_tip_vs_cycle.npy": "ba24cd21ec5d4a497bcf4c75eda72b034e1853c82327b87b0c26724f8723b1d2",
    "Kt_vs_cycle.npy": "d738ba1d18d813a0ab7ef35aabd2fd1650ededdf225625cddf3479b83a4fec22",
    "time_vs_cycle.npy": "a390b0d731a56ab81f9db6055dee8a47e32ddab31b32b2747f82a85abcc2a7d6",
    "energy_gradient_terms_vs_cycle.npy": "f1394b4b68b143d4ba15b70808859b6792a3fb1ac60ee95a23ceb46f8e872f56",
}


def publish_directory_exclusive(source: Path, destination: Path) -> None:
    """Atomically publish a directory without replacing any existing target."""
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    libc = ctypes.CDLL(None, use_errno=True)
    system = platform.system()
    if system == "Darwin" and hasattr(libc, "renamex_np"):
        result = libc.renamex_np(
            os.fsencode(source), os.fsencode(destination), ctypes.c_uint(0x00000004)
        )
    elif system == "Linux" and hasattr(libc, "renameat2"):
        result = libc.renameat2(
            ctypes.c_int(-100), os.fsencode(source),
            ctypes.c_int(-100), os.fsencode(destination), ctypes.c_uint(1),
        )
    else:
        raise RuntimeError("exclusive atomic directory publication is unsupported")
    if result != 0:
        error = ctypes.get_errno()
        if error in (errno.EEXIST, errno.ENOTEMPTY):
            raise FileExistsError(f"refusing to replace existing destination: {destination}")
        raise OSError(error, os.strerror(error), str(destination))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _safe_file(bundle: Path, name: str) -> Path:
    if Path(name).name != name:
        raise ValueError(f"restart manifest contains unsafe file name: {name!r}")
    path = bundle / name
    if not path.is_file():
        raise FileNotFoundError(f"restart bundle file is missing: {path}")
    return path


def validate_bundle(bundle: Path, expected_manifest_sha256: str | None = None) -> dict:
    bundle = Path(bundle).resolve()
    manifest_path = bundle / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"restart manifest is missing: {manifest_path}")
    manifest_sha = sha256(manifest_path)
    if expected_manifest_sha256 is not None and manifest_sha != expected_manifest_sha256:
        raise ValueError(
            "restart manifest SHA-256 mismatch: "
            f"expected {expected_manifest_sha256}, got {manifest_sha}"
        )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA:
        raise ValueError("unsupported G4 restart-bundle schema")
    if payload.get("training_authorized") is not False:
        raise ValueError("restart bundle must not authorize training")
    if payload.get("development_case") != "U0.12":
        raise ValueError("restart bundle is not the frozen U0.12 development case")
    expected_state = {
        "label": "c60_unloaded_post_commit",
        "raw_step": START_STEP,
        "next_raw_step": START_STEP + 1,
        "history_length": HISTORY_LENGTH,
        "future_history_forbidden": True,
    }
    if payload.get("start_state") != expected_state:
        raise ValueError("restart start-state contract mismatch")
    source = payload.get("source", {})
    if source.get("model_settings_sha256") != SOURCE_SETTINGS_SHA256:
        raise ValueError("restart source settings hash mismatch")
    if source.get("mesh_sha256") != SOURCE_MESH_SHA256:
        raise ValueError("restart source mesh hash mismatch")
    files = payload.get("files")
    if not isinstance(files, dict) or set(files) != REQUIRED_FILES:
        raise ValueError("restart bundle must contain the exact required file set")
    disk_names = {path.name for path in bundle.iterdir() if path.is_file()}
    if disk_names != REQUIRED_FILES | {"manifest.json"}:
        raise ValueError("restart bundle directory contains missing or unexpected files")
    for name, record in files.items():
        expected_role = HISTORY_ROLES.get(name, MODEL_ROLES.get(name))
        if record.get("semantic_role") != expected_role:
            raise ValueError(f"restart semantic role mismatch: {name}")
        if record.get("last_raw_step") != START_STEP:
            raise ValueError(f"restart raw-step boundary mismatch: {name}")
        if record.get("source_sha256") != FROZEN_FILE_SOURCE_SHA256[name]:
            raise ValueError(f"restart frozen source hash mismatch: {name}")
        path = _safe_file(bundle, name)
        if record.get("sha256") != sha256(path):
            raise ValueError(f"restart file SHA-256 mismatch: {name}")
        if name.endswith(".npy"):
            array = np.load(path, allow_pickle=False)
            if array.ndim < 1 or array.shape[0] != HISTORY_LENGTH:
                raise ValueError(f"restart history must have exactly 301 rows: {name}")
            if list(array.shape) != record.get("shape") or str(array.dtype) != record.get("dtype"):
                raise ValueError(f"restart history schema mismatch: {name}")
            finite_policy = record.get("finite_policy")
            expected_policy = {
                "allow_nan": name == "Kt_vs_cycle.npy",
                "allow_inf": False,
            }
            if finite_policy != expected_policy:
                raise ValueError(f"restart finite-value policy mismatch: {name}")
            nan_count = int(np.isnan(array).sum())
            inf_count = int(np.isinf(array).sum())
            if inf_count or (nan_count and not expected_policy["allow_nan"]):
                raise ValueError(f"restart history violates finite-value policy: {name}")
            if record.get("nan_count") != nan_count or record.get("inf_count") != inf_count:
                raise ValueError(f"restart non-finite count mismatch: {name}")
    payload["manifest_sha256"] = manifest_sha
    payload["bundle_root"] = str(bundle)
    return payload


def stage_bundle(bundle: Path, destination: Path, expected_manifest_sha256: str) -> dict:
    payload = validate_bundle(bundle, expected_manifest_sha256)
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"restart destination must not exist: {destination}")
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.stage-", dir=destination.parent))
    try:
        for name in sorted(REQUIRED_FILES):
            shutil.copy2(Path(bundle) / name, temporary / name)
        staged = {name: sha256(temporary / name) for name in sorted(REQUIRED_FILES)}
        expected = {name: payload["files"][name]["sha256"] for name in sorted(REQUIRED_FILES)}
        if staged != expected:
            raise RuntimeError("staged restart files do not match the frozen bundle")
        publish_directory_exclusive(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return payload
