"""Fail-closed, create-once terminal adjudication for the one T3-rev run."""
from __future__ import annotations

import hashlib
import importlib.util
import csv
import io
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


CASE_ID = "T3_rev_loading_order"
AUTHORIZATION_CAPABILITY = "exactly_one_T3_rev_loading_order_execution"
COMPONENT_IDENTITY_FILES = {
    "solver_sha256": "solve_toy_road_family_case.m",
    "recovery_sha256": "recover_toy_road_family_state.m",
    "exporter_sha256": "export_toy_road_cycle_shard.m",
    "numerical_gate_contract_sha256": "finalize_toy_road_c5_gate.m",
    "event_contract_sha256": "build_toy_road_family_case.m",
}
RECOVERY_CLASSIFICATION = "FAIL_RECOVERY_NEWTON_NONCONVERGENCE_BEFORE_C1"
RECOVERY_STDOUT_SHA256 = "161140449292d580490e240ed1a32a0e52b04ce5ef2e4898f1ac9db875b42802"
RECOVERY_STDERR_SHA256 = "7873abc4e9e878e008bc250be45a4be6ffd3eb8d497395512751fc95bd7f308a"
RECOVERY_PID_BYTES = b"25476\n"
RECOVERY_RECEIPT_SHA256 = {
    "T3_REV_EXECUTION_INPUT_LOCK.json": "4b12625650ce3930e969f872d9b890e93b2902745d49f6c45af5aa7233f0e238",
    "T3_REV_LAUNCH_RECEIPT.json": "2ef43696071d371610747e4761e88a3e2eaa3b795bf310f1f9503fce3f297382",
    "T3_REV_RUNTIME_MEASUREMENT.json": "4c87b33abea9212e43c7d95768e1198665b55f4423b2e1941094d3734001cce7",
}
RECOVERY_OVERLAY_SHA256 = {
    "+phase_field/+mex/+fem/+assembly/+equilibrium/initial.mexw64": "ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db",
    "build_toy_road_family_case.m": "69d7abd143d9cae1fd4bd9f82f5071b31f7dc0e04a7d6861dab3be913567c51f",
    "CASE_PHYSICS_CONTRACTS.json": "78c1f9fa35d9baa33d45b2891fe62b95d4196bc80559cd7a581dc3aa23552763",
    "FAMILY_CONTRACT.json": "423e0900d6b3dcbc04fe3dda8cfc0f59e74ec3f63d333e42f93a8cc023793e83",
    "main_toy_road_family_case.m": "dc536f22b9f350d400c8e26be4e56695e5fe30a90b9b190d6759d619ddc9cb31",
    "private/run_toy_road_driver_core.m": "13af81eb94fae4a5873eafffffe1faa4cd017dfeb47d7607719c650816b877fa",
    "run_toy_road_controlled_driver_harness.m": "57c0324a4f2d9ad654151c289b083780f8a8527b8a3a7c2434243e9290d86831",
    "solve_toy_road_family_case.m": "a702ac92bd9e490e86a6eaae4c9da2d5122c3bc4fd4ee3ce5900ae0f390c20b6",
    "toy_road_protocol.py": "ffea1dc19587a06b13e95c3e7860e889e4fdf0839afa9e99a8c0cb26a1788c70",
    "toy_road_wait_for_launch_receipt.m": "27a273fb3bd6f3ce924627e10e0382dfad387d5bbc82ab7953f4325a34dd6402",
    "ToyRoadC5Trace.m": "a81058048158e6932bb9e6879caafe3fa2a96d55712f299a9f6c5798fb13abed",
}
RECOVERY_PREF_SHA256 = {
    "creation.timestamp": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "ddux.mlsettings": "e808e9263f6370a4ed8afe24894559e9168d615456431e4d10389eb00f9eed0c",
    "ddux/dduxR2024b.log": "bae8a86c5acd457054b73e5470a490a711041b5cfe50c0a43ebf359839a7d4d7",
    "epfwk_cache-25.2.0.3177638-13610418029628563499.json": "6ae7052321adb4db2728596ef6a96567cc11814ff8b8f16305de9eb37cb7867c",
    "matlab.prf": "53a89d918c411f5d202a1a1fccc531aeddf93e909489f8ea80f8d6c00014d214",
    "migratePref.txt": "f67ab10ad4e4c53121b6a5fe4da9c10ddee905b978d3788d2723d7bfacbe28a9",
    "MLintDefaultSettings.txt": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "webwindowscale.mlsettings": "a888abe039f47eae1b72fd7a8c96ccf55f6d9259b41ec47b793d0292eea1f9d8",
    "webwindowscale/webwindowscaleR2024b.log": "2205cee3af5b4bb3c96b612e6db4dd6e4f0dc512aa4b6f3f6a619e9747e3eb9d",
}


class TerminalValidationError(RuntimeError):
    """The terminal package or its launch chain is not admissible evidence."""


def require_runtime_source_closure(
        seal: Mapping[str, object], launch_receipt: Mapping[str, object], *,
        allow_unpublished_bootstrap: bool = False) -> dict[str, object]:
    """Bind v2 launch provenance while retaining read-only support for the archived v1 run."""
    seal_version = seal.get("schema_version")
    receipt_version = launch_receipt.get("schema_version")
    if seal_version == "toy_road_t3_rev_seal_v1" \
            and receipt_version == "toy_road_t3_rev_launch_receipt_v1":
        return {
            "status": "LEGACY_UNBOUND_RUNTIME_SOURCE_CLOSURE",
            "scientific_adjudication_valid": False,
        }
    if allow_unpublished_bootstrap and seal_version == "toy_road_t3_rev_seal_v2" \
            and receipt_version is None:
        closure = seal.get("runtime_source_closure")
        if not isinstance(closure, dict):
            raise TerminalValidationError("unpublished bootstrap seal omits runtime source closure")
        return {
            "status": "SEALED_RUNTIME_SOURCE_CLOSURE_UNPUBLISHED_BOOTSTRAP",
            "scientific_adjudication_valid": False,
            **closure,
        }
    if seal_version != "toy_road_t3_rev_seal_v2" \
            or receipt_version != "toy_road_t3_rev_launch_receipt_v2":
        raise TerminalValidationError("runtime source closure schema versions are inconsistent")
    closure = seal.get("runtime_source_closure")
    recovery = launch_receipt.get("recovery_geometry_preflight")
    if not isinstance(closure, dict) or not isinstance(recovery, dict):
        raise TerminalValidationError("runtime source closure is missing")
    expected = {
        "family_runtime_source_commit": launch_receipt.get("family_runtime_source_commit"),
        "q1_mex_build_source_commit": launch_receipt.get("q1_mex_build_source_commit"),
        "griphfith_runtime_source_inventory_sha256": launch_receipt.get(
            "griphfith_runtime_source_inventory_sha256"),
        "qualified_t3_input_snapshot_sha256": recovery.get("input_snapshot_sha256"),
        "mesh_x_extent": recovery.get("mesh_x_extent"),
        "at1_recovery_penalty": recovery.get("at1_recovery_penalty"),
    }
    if type(closure) is not type(expected) or set(closure) != set(expected) \
            or any(type(closure[key]) is not type(expected[key]) or closure[key] != expected[key]
                   for key in expected):
        raise TerminalValidationError("launch runtime source closure differs from the seal")
    return {"status": "PASS", "scientific_adjudication_valid": True, **closure}


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TerminalValidationError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise TerminalValidationError(f"cannot load {path.name}: {error}") from error
    finally:
        sys.modules.pop(name, None)
    return module


def _strict_json(path: Path) -> dict[str, object]:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise TerminalValidationError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate,
                           parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise TerminalValidationError(f"cannot read strict JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise TerminalValidationError(f"JSON root must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_run_tree(root: Path) -> dict[str, object]:
    """Return a deterministic directory-and-file inventory without touching the tree."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise TerminalValidationError(f"run inventory root is not a directory: {root}")
    entries: list[dict[str, object]] = [{
        "relative_path": ".", "entry_type": "directory",
        "size_bytes": None, "sha256": None,
    }]
    paths = sorted(
        root.rglob("*"), key=lambda path: path.relative_to(root).as_posix()
    )
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            entries.append({
                "relative_path": relative, "entry_type": "directory",
                "size_bytes": None, "sha256": None,
            })
        elif path.is_file():
            entries.append({
                "relative_path": relative, "entry_type": "file",
                "size_bytes": path.stat().st_size, "sha256": _sha256(path),
            })
        else:
            raise TerminalValidationError(f"run inventory contains a non-file entry: {relative}")
    return {
        "schema_version": "toy_road_t3_rev_raw_run_tree_inventory_v1",
        "run_root": str(root),
        "entry_count": len(entries),
        "directory_count": sum(item["entry_type"] == "directory" for item in entries),
        "file_count": sum(item["entry_type"] == "file" for item in entries),
        "entries": entries,
    }


def _process_is_running(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        synchronize = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, pid)
        if not handle:
            return False
        try:
            return ctypes.windll.kernel32.WaitForSingleObject(handle, 0) == 258
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _exact_file_inventory(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix())
        if path.is_file()
    }


def authenticate_recovery_nontrajectory(run_root: Path) -> dict[str, object]:
    """Authenticate the sealed PID-25476 zero-load recovery failure and nothing else."""
    run_root = Path(run_root).resolve()
    expected_top = {
        ".toy-road-runtime-overlay", "cache", "launcher.pid", "output", "pref",
        "pref.matlab-startup", "receipts", "T3_REV.stderr.log", "T3_REV.stdout.log",
        "temp", "tmp", "work",
    }
    if not run_root.is_dir() or {path.name for path in run_root.iterdir()} != expected_top:
        raise TerminalValidationError("recovery failure run-root closure is not exact")
    pid_path = run_root / "launcher.pid"
    if pid_path.read_bytes() != RECOVERY_PID_BYTES:
        raise TerminalValidationError("recovery failure launcher PID bytes differ")
    pid = int(RECOVERY_PID_BYTES.strip())
    if _process_is_running(pid):
        raise TerminalValidationError("recovery failure MATLAB process is still running")
    stdout_path = run_root / "T3_REV.stdout.log"
    stderr_path = run_root / "T3_REV.stderr.log"
    if _sha256(stdout_path) != RECOVERY_STDOUT_SHA256 \
            or _sha256(stderr_path) != RECOVERY_STDERR_SHA256:
        raise TerminalValidationError("recovery failure stdout/stderr byte identity differs")
    try:
        stdout = stdout_path.read_text(encoding="utf-8")
        stderr = stderr_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise TerminalValidationError(f"cannot read recovery failure logs: {error}") from error
    iterations = re.findall(
        r"Newton-Raphson iteration:\s+(\d+)\s+res_norm:\s+([0-9.eE+\-]+)", stdout
    )
    if len(iterations) != 250 \
            or [int(number) for number, _ in iterations] != list(range(1, 251)) \
            or iterations[-1] != ("250", "2.09741e+22") \
            or stdout.count("Newton-Raphson did not converge!") != 1:
        raise TerminalValidationError("recovery Newton iteration sequence is not exact")
    stdout_stack = (
        "localProductionRecoveryNewton", "recover_toy_road_family_state (line 13)",
        "run_toy_road_driver_core (line 15)", "main_toy_road_family_case (line 13)",
        "run_toy_road_runtime_bridge (line 90)",
    )
    stderr_stack = (
        "Error using recover_toy_road_family_state (line 18)",
        "Fresh zero-load Hard recovery did not converge.",
        "Error in run_toy_road_driver_core (line 15)",
        "Error in main_toy_road_family_case (line 13)",
        "Error in run_toy_road_runtime_bridge (line 90)",
        "ERROR: MATLAB error Exit Status: 0x00000001",
    )
    if any(token not in stdout for token in stdout_stack) \
            or any(token not in stderr for token in stderr_stack):
        raise TerminalValidationError("recovery failure stack predicates differ")
    receipts = run_root / "receipts"
    if _exact_file_inventory(receipts) != RECOVERY_RECEIPT_SHA256:
        raise TerminalValidationError("recovery failure receipt closure differs")
    output = run_root / "output"
    if not output.is_dir() or any(output.iterdir()):
        raise TerminalValidationError("recovery failure must have zero output artifacts and cycle shards")
    for name in ("cache", "pref", "temp", "tmp", "work"):
        root = run_root / name
        if not root.is_dir() or any(root.iterdir()):
            raise TerminalValidationError(f"recovery failure writable root is not empty: {name}")
    if _exact_file_inventory(run_root / "pref.matlab-startup") != RECOVERY_PREF_SHA256:
        raise TerminalValidationError("recovery failure MATLAB preference closure differs")
    if _exact_file_inventory(run_root / ".toy-road-runtime-overlay") != RECOVERY_OVERLAY_SHA256:
        raise TerminalValidationError("recovery failure runtime overlay closure differs")
    if (run_root / "T3_REV_FAILURE_PACKAGE").exists():
        raise TerminalValidationError("recovery failure cannot carry a numerical failure package")
    return {
        "schema_version": "toy_road_t3_rev_recovery_nontrajectory_evidence_v1",
        "failure_phase": "fresh_zero_load_recovery_before_cycle_1",
        "process_id": pid,
        "process_exited": True,
        "newton_iteration_count": 250,
        "last_iteration": 250,
        "last_res_norm_text": "2.09741e+22",
        "stdout_sha256": RECOVERY_STDOUT_SHA256,
        "stderr_sha256": RECOVERY_STDERR_SHA256,
        "stderr_error": "Fresh zero-load Hard recovery did not converge.",
        "completed_cycle_shards": 0,
        "c5_artifacts": "ABSENT",
        "event_artifacts": "ABSENT",
        "producer_terminal_artifacts": "ABSENT",
        "failure_package": "ABSENT",
        "fatigue_trajectory_available": False,
    }


def _adjudicator_identity() -> tuple[str, str]:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise TerminalValidationError(f"cannot resolve adjudicator commit: {error}") from error
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise TerminalValidationError("adjudicator commit is not a full SHA-1")
    return commit, _sha256(Path(__file__).resolve())


def classify_terminal(terminal: Mapping[str, object]) -> str:
    """Keep every terminal category distinct; no failure is recast as censoring."""
    reason = terminal.get("terminal_reason")
    classes = {
        "confirmed_penetration": "PASS_CONFIRMED_FRACTURE_TRAJECTORY",
        "right_censored": "PASS_NO_CONFIRMED_FRACTURE_BY_C150",
        "coupled_fixed_point_nonconvergence": "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE",
        "newton_nonconvergence": "FAIL_NEWTON_NONCONVERGENCE",
        "recovery_newton_nonconvergence_before_c1": RECOVERY_CLASSIFICATION,
        "startup_failure": "FAIL_STARTUP",
        "runtime_failure": "FAIL_RUNTIME",
    }
    if reason not in classes:
        raise TerminalValidationError(f"unknown terminal_reason: {reason!r}")
    if reason == "confirmed_penetration":
        first_hit = terminal.get("first_hit_cycle")
        confirmed = terminal.get("confirmed_cycle")
        terminal_cycle = terminal.get("terminal_cycle")
        if type(first_hit) is not int or type(confirmed) is not int \
                or type(terminal_cycle) is not int \
                or confirmed != first_hit + 3 or terminal_cycle != confirmed:
            raise TerminalValidationError("confirmed outcome must preserve the exact three-cycle event rule")
    if reason == "right_censored" and (
            terminal.get("terminal_cycle") != 150
            or terminal.get("first_hit_cycle") is not None
            or terminal.get("confirmed_cycle") is not None):
        raise TerminalValidationError("right-censored outcome must end at c150 without a hit or confirmation")
    if reason in {"coupled_fixed_point_nonconvergence", "newton_nonconvergence"}:
        if type(terminal.get("cycle")) is not int or terminal["cycle"] < 1 \
                or type(terminal.get("substep")) is not int \
                or not 1 <= terminal["substep"] <= 5:
            raise TerminalValidationError("solver nonconvergence receipt must report cycle and substep")
    return classes[reason]


def terminal_adjudication_status(classification: str) -> str:
    if classification in {
        "PASS_CONFIRMED_FRACTURE_TRAJECTORY",
        "PASS_NO_CONFIRMED_FRACTURE_BY_C150",
    }:
        return "PASS_TERMINAL_ADJUDICATION"
    if classification.startswith("FAIL_"):
        return classification
    raise TerminalValidationError(f"unknown terminal classification: {classification}")


def require_canonical_seal_bytes(path: Path, seal: Mapping[str, object]) -> str:
    expected = json.dumps(seal, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    actual = Path(path).read_bytes()
    if actual != expected:
        raise TerminalValidationError("seal bytes are not canonical builder bytes")
    return hashlib.sha256(actual).hexdigest()


def _write_create_once(path: Path, value: Mapping[str, object]) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as error:
        raise TerminalValidationError(f"terminal adjudication already exists: {path}") from error


def require_canonical_lock_bytes(protocol: Any, lock_path: Path, lock: Mapping[str, object]) -> None:
    """The launch receipt binds protocol-canonical bytes, not JSON-equivalent text."""
    try:
        expected = protocol.canonical_json_bytes(lock)
    except Exception as error:
        raise TerminalValidationError(f"cannot encode canonical execution lock: {error}") from error
    if not isinstance(expected, bytes) or Path(lock_path).read_bytes() != expected:
        raise TerminalValidationError("execution lock bytes are not authoritative canonical JSON")


def _validate_package_checksum(protocol: Any, snapshot: Mapping[str, object]) -> None:
    """Validate the producer checksum ledger in addition to manifest closure."""
    files = snapshot.get("bytes")
    if not isinstance(files, dict) or "SHA256SUMS.txt" not in files:
        raise TerminalValidationError("terminal package checksum ledger is missing")
    payload = files["SHA256SUMS.txt"]
    if not isinstance(payload, bytes) or not payload.endswith(b"\n") or b"\r" in payload:
        raise TerminalValidationError("terminal package checksum ledger bytes are not canonical")
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise TerminalValidationError("terminal package checksum ledger is not ASCII") from error
    declared: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            raise TerminalValidationError("terminal package checksum row is malformed")
        digest, relative = match.groups()
        if not protocol._canonical_relative_path(relative) or relative in declared:
            raise TerminalValidationError("terminal package checksum path is invalid")
        declared[relative] = digest
    expected_paths = sorted(set(files) - {"SHA256SUMS.txt", "TERMINAL_MANIFEST.json"})
    if list(declared) != expected_paths:
        raise TerminalValidationError("terminal package checksum closure is incomplete")
    for relative, digest in declared.items():
        if hashlib.sha256(files[relative]).hexdigest() != digest:
            raise TerminalValidationError("terminal package checksum digest differs")


def _validate_trajectory_running_envelope(
        protocol: Any, state0_damage: np.ndarray, state0_alpha: np.ndarray,
        shards: Iterable[Mapping[str, object]], connectivity: np.ndarray,
        label: str) -> None:
    """Prevent individually tolerated irreversible-state regressions from accumulating."""
    threshold = protocol.THRESHOLD
    running_damage = np.asarray(state0_damage[:, 0], dtype=np.float64).copy()
    running_alpha = np.asarray(state0_alpha, dtype=np.float64).copy()
    connectivity_values = protocol._require_double_array(
        connectivity, f"{label} trajectory connectivity")
    rounded_connectivity = np.rint(connectivity_values)
    if connectivity_values.ndim != 2 or connectivity_values.shape[1] != 4 \
            or not np.array_equal(connectivity_values, rounded_connectivity) \
            or np.any(rounded_connectivity < 1) \
            or np.any(rounded_connectivity > running_damage.shape[0]) \
            or any(len(set(row)) != 4 for row in rounded_connectivity.astype(np.int64)):
        raise TerminalValidationError(
            f"{label} trajectory connectivity is not valid one-based Q4 connectivity"
        )
    node_indices = rounded_connectivity.astype(np.int64) - 1
    gauss = 1 / math.sqrt(3)
    gauss_points = np.asarray([
        [-gauss, -gauss], [gauss, -gauss],
        [gauss, gauss], [-gauss, gauss],
    ], dtype=np.float64)
    shape_operator = np.empty((4, 4), dtype=np.float64)
    for ordinal, (xi, eta) in enumerate(gauss_points):
        shape_operator[ordinal, :] = 0.25 * np.asarray([
            (1 - xi) * (1 - eta), (1 + xi) * (1 - eta),
            (1 + xi) * (1 + eta), (1 - xi) * (1 + eta),
        ])
    running_gp_damage: np.ndarray | None = None
    if np.any(running_damage < -threshold) or np.any(running_damage > 1 + threshold):
        raise TerminalValidationError(f"{label} state0 damage is outside the trajectory envelope")
    if np.any(running_alpha < -threshold):
        raise TerminalValidationError(f"{label} state0 history is outside the trajectory envelope")
    for cycle, shard in enumerate(shards, start=1):
        damage = protocol._require_double_array(
            shard["d_node"], f"{label} trajectory cycle {cycle}.d_node")
        gp_damage = protocol._require_double_array(
            shard["d_gp"], f"{label} trajectory cycle {cycle}.d_gp")
        alpha = protocol._require_double_array(
            shard["alpha_bar_gp"], f"{label} trajectory cycle {cycle}.alpha_bar_gp")
        if np.any(damage < -threshold) or np.any(damage > 1 + threshold) \
                or np.any(gp_damage < -threshold) or np.any(gp_damage > 1 + threshold):
            raise TerminalValidationError(
                f"{label} cycle {cycle} damage is outside the trajectory envelope"
            )
        if np.any(alpha < -threshold):
            raise TerminalValidationError(
                f"{label} cycle {cycle} history is outside the trajectory envelope"
            )
        if gp_damage.shape != (node_indices.shape[0], 4, damage.shape[1]):
            raise TerminalValidationError(
                f"{label} cycle {cycle} GP damage dimensions differ from authenticated Q4 geometry"
            )
        for substep in range(damage.shape[1]):
            current_damage = damage[:, substep]
            current_gp_damage = gp_damage[:, :, substep]
            current_alpha = alpha[:, :, substep]
            if running_gp_damage is not None \
                    and np.any(current_gp_damage < running_gp_damage - threshold):
                raise TerminalValidationError(
                    f"{label} cycle {cycle} GP damage fell below its running maximum"
                )
            if np.any(current_damage < running_damage - threshold):
                raise TerminalValidationError(
                    f"{label} cycle {cycle} damage fell below its running maximum"
                )
            if np.any(current_alpha < running_alpha - threshold):
                raise TerminalValidationError(
                    f"{label} cycle {cycle} history fell below its running maximum"
                )
            element_damage = current_damage[node_indices]
            expected_gp_damage = (shape_operator @ element_damage.T).T
            if np.any(np.abs(current_gp_damage - expected_gp_damage) > threshold):
                raise TerminalValidationError(
                    f"{label} cycle {cycle} substep {substep + 1} GP damage differs from the "
                    "sealed Q4 nodal-to-GP interpolation"
                )
            if running_gp_damage is None:
                running_gp_damage = current_gp_damage.copy()
            else:
                np.maximum(running_gp_damage, current_gp_damage, out=running_gp_damage)
            np.maximum(running_damage, current_damage, out=running_damage)
            np.maximum(running_alpha, current_alpha, out=running_alpha)


def _validate_snapshot_running_envelope(
        protocol: Any, snapshot: Mapping[str, object], connectivity: np.ndarray,
        label: str) -> None:
    files = snapshot.get("bytes")
    if not isinstance(files, dict):
        raise TerminalValidationError(f"{label} authenticated snapshot bytes are missing")
    state0 = protocol._read_mat_struct_bytes(
        files.get("STATE0.mat"), "state0", f"{label} trajectory state0")
    state0_damage = protocol._require_double_array(
        state0["d_node"], f"{label} trajectory state0.d_node")
    state0_alpha = protocol._require_double_array(
        state0["alpha_bar_gp"], f"{label} trajectory state0.alpha_bar_gp")
    cycle_paths = sorted(
        path for path in files if re.fullmatch(r"substeps/cycle_[0-9]{4}\.mat", path)
    )

    def authenticated_shards() -> Iterable[Mapping[str, object]]:
        for cycle, relative in enumerate(cycle_paths, start=1):
            yield protocol._read_mat_struct_bytes(
                files[relative], "shard", f"{label} trajectory cycle {cycle}")

    _validate_trajectory_running_envelope(
        protocol, state0_damage, state0_alpha, authenticated_shards(), connectivity, label)


def _authenticate_right_censored_package(
        protocol: Any, package_root: Path) -> dict[str, object]:
    """Reuse authoritative package components with the sole c150 event variant."""
    root = protocol._canonical_package_root(Path(package_root), CASE_ID)
    snapshot = protocol._capture_package_bytes(root, CASE_ID)
    manifest = protocol._read_json_bytes(
        snapshot["bytes"].get("TERMINAL_MANIFEST.json"), f"{CASE_ID} terminal manifest"
    )
    protocol._require_exact_fields(manifest, protocol.MANIFEST_FIELDS, f"{CASE_ID} terminal manifest")
    if manifest["protocol_version"] != protocol.PROTOCOL_VERSION \
            or type(manifest["protocol_version"]) is not str \
            or manifest["case_id"] != CASE_ID or type(manifest["case_id"]) is not str:
        raise TerminalValidationError("right-censored manifest protocol or case is invalid")
    authorization_scope = protocol._require_nonempty_text(
        manifest["authorization_scope"], f"{CASE_ID} authorization_scope"
    )
    protocol._validate_manifest_identities(manifest, CASE_ID)
    protocol._validate_manifest_closure(manifest, snapshot, CASE_ID)
    _validate_package_checksum(protocol, snapshot)
    required_paths = {
        "EXECUTION_INPUT_LOCK.json", "STATE0.mat", "EVENT_METADATA.json",
        "TERMINAL_RESULT.json", "SHA256SUMS.txt",
        "qualification/C5_STAGGER_TRACE.csv",
        "qualification/C5_NUMERICAL_GATE_RECEIPT.json",
    }
    if not required_paths.issubset(snapshot["bytes"]):
        raise TerminalValidationError("right-censored package is missing a required artifact")
    lock_bytes = snapshot["bytes"]["EXECUTION_INPUT_LOCK.json"]
    execution_digest = hashlib.sha256(lock_bytes).hexdigest()
    if execution_digest != manifest["execution_input_lock_sha256"]:
        raise TerminalValidationError("right-censored execution lock differs from its manifest")
    lock = protocol._read_json_bytes(lock_bytes, f"{CASE_ID} execution lock")
    protocol.validate_execution_input_lock(lock, CASE_ID)
    if lock["authorization_scope"] != authorization_scope \
            or protocol.canonical_json_bytes(lock) != lock_bytes:
        raise TerminalValidationError("right-censored execution lock is not canonical or package-local")
    protocol._validate_c5(snapshot, manifest, CASE_ID)
    event = protocol._read_json_bytes(snapshot["bytes"]["EVENT_METADATA.json"], f"{CASE_ID} event")
    terminal = protocol._read_json_bytes(
        snapshot["bytes"]["TERMINAL_RESULT.json"], f"{CASE_ID} terminal result"
    )
    protocol._require_exact_fields(event, protocol.EVENT_FIELDS, f"{CASE_ID} event")
    protocol._require_exact_fields(terminal, protocol.TERMINAL_FIELDS, f"{CASE_ID} terminal result")
    if not (
            event["authorization_scope"] == authorization_scope
            and terminal["authorization_scope"] == authorization_scope
            and event["case_id"] == CASE_ID and terminal["case_id"] == CASE_ID
            and event["first_hit_cycle"] is None and terminal["first_hit_cycle"] is None
            and event["confirmed_cycle"] is None and terminal["confirmed_cycle"] is None
            and protocol._exact_json_int(event["terminal_cycle"], 150)
            and protocol._exact_json_int(terminal["terminal_cycle"], 150)
            and protocol._exact_json_int(event["peak_substep_ordinal"], 4)
            and terminal["terminal_reason"] == "right_censored"):
        raise TerminalValidationError(
            "right-censored event and terminal metadata must end at c150 without first-hit or confirmation"
        )
    terminal_path = "substeps/cycle_0150.mat"
    if terminal_path not in snapshot["bytes"] or event["cycle_shard"] != terminal_path \
            or event["cycle_shard_sha256"] != hashlib.sha256(snapshot["bytes"][terminal_path]).hexdigest():
        raise TerminalValidationError("right-censored event metadata does not bind the c150 shard")
    cycle_paths = sorted(
        path for path in snapshot["bytes"]
        if re.fullmatch(r"substeps/cycle_[0-9]{4}\.mat", path)
    )
    expected_cycle_paths = [f"substeps/cycle_{cycle:04d}.mat" for cycle in range(1, 151)]
    if cycle_paths != expected_cycle_paths:
        raise TerminalValidationError("right-censored cycle coverage is not exactly c1-c150")
    state0 = protocol._read_mat_struct_bytes(snapshot["bytes"]["STATE0.mat"], "state0", f"{CASE_ID} state0")
    protocol._require_exact_fields(state0, {"d_node", "alpha_bar_gp"}, f"{CASE_ID} state0")
    state0_damage = protocol._require_double_array(state0["d_node"], f"{CASE_ID} state0.d_node")
    state0_alpha = protocol._require_double_array(
        state0["alpha_bar_gp"], f"{CASE_ID} state0.alpha_bar_gp"
    )
    if state0_damage.ndim != 2 or state0_damage.shape[1] != 1 or state0_damage.shape[0] == 0 \
            or state0_alpha.ndim != 2 or state0_alpha.shape[1] != 4 or state0_alpha.shape[0] == 0 \
            or np.any(state0_damage < -protocol.THRESHOLD) \
            or np.any(state0_damage > 1 + protocol.THRESHOLD) \
            or np.any(state0_alpha < -protocol.THRESHOLD):
        raise TerminalValidationError("right-censored state0 shape or bounds are invalid")
    previous_damage = state0_damage[:, 0]
    previous_alpha = state0_alpha
    shards: list[dict[str, Any]] = []
    for cycle, relative in enumerate(cycle_paths, start=1):
        shard = protocol._read_mat_struct_bytes(snapshot["bytes"][relative], "shard", f"{CASE_ID} cycle {cycle}")
        previous_damage, previous_alpha = protocol._validate_shard(
            shard, manifest, cycle, CASE_ID, previous_damage, previous_alpha,
            state0_damage.shape[0], state0_alpha.shape[0],
        )
        shards.append(shard)
    package = {
        "root": root, "snapshot": snapshot, "manifest": manifest,
        "manifest_sha256": hashlib.sha256(snapshot["bytes"]["TERMINAL_MANIFEST.json"]).hexdigest(),
        "c5_receipt_sha256": hashlib.sha256(
            snapshot["bytes"]["qualification/C5_NUMERICAL_GATE_RECEIPT.json"]
        ).hexdigest(),
        "event": event, "terminal": terminal, "state0": state0, "shards": shards,
    }
    receipt = protocol._terminal_authentication_receipt(package)
    protocol._verify_package_snapshot(package)
    return receipt


def _validate_completed_production_artifacts(
        protocol: Any, package_root: Path, receipt: Mapping[str, object], *,
        allow_test_synthetic_mesh_bytes: bool = False,
) -> dict[str, object]:
    """Authenticate the production-written physical/runtime identity artifacts."""
    root = protocol._canonical_package_root(Path(package_root), CASE_ID)
    captured = protocol._capture_package_bytes(root, CASE_ID)
    files = captured.get("bytes")
    required = {
        "INPUT_SNAPSHOT.json", "RUNTIME_RECEIPT.json", "mesh_geometry.mat",
        "state0_analysis.mat", "EXECUTION_INPUT_LOCK.json", "TERMINAL_MANIFEST.json",
    }
    if not isinstance(files, dict) or not required.issubset(files):
        raise TerminalValidationError("completed package is missing a production identity artifact")
    manifest = protocol._read_json_bytes(
        files["TERMINAL_MANIFEST.json"], f"{CASE_ID} completed terminal manifest")
    lock = protocol._read_json_bytes(
        files["EXECUTION_INPUT_LOCK.json"], f"{CASE_ID} completed execution lock")
    input_snapshot = protocol._read_json_bytes(
        files["INPUT_SNAPSHOT.json"], f"{CASE_ID} completed input snapshot")
    runtime_receipt = protocol._read_json_bytes(
        files["RUNTIME_RECEIPT.json"], f"{CASE_ID} completed runtime receipt")
    snapshot_fields = {
        "schema_version", "authorization_scope", "case_id", "source_commit",
        "runtime_lock_sha256", "family_contract_sha256", "case_physics_contract_sha256",
        "execution_input_lock_sha256", "input_assets_root", "mesh_sha256", "changed_axes",
        "case_physics", "fresh_state0", "resume_allowed", "line_search", "cycle_jump",
    }
    execution_digest = hashlib.sha256(files["EXECUTION_INPUT_LOCK.json"]).hexdigest()
    physical_digest = hashlib.sha256(files["INPUT_SNAPSHOT.json"]).hexdigest()
    input_root = input_snapshot.get("input_assets_root")
    if set(input_snapshot) != snapshot_fields \
            or input_snapshot.get("schema_version") != "toy_road_p0_input_snapshot_v1" \
            or input_snapshot.get("authorization_scope") != "production_authorized" \
            or input_snapshot.get("case_id") != CASE_ID \
            or any(input_snapshot.get(field) != lock.get(field) for field in (
                "source_commit", "runtime_lock_sha256", "family_contract_sha256",
                "case_physics_contract_sha256")) \
            or input_snapshot.get("execution_input_lock_sha256") != execution_digest \
            or manifest.get("execution_input_lock_sha256") != execution_digest \
            or manifest.get("physical_input_sha256") != physical_digest \
            or input_snapshot.get("mesh_sha256") != manifest.get("mesh_sha256") \
            or input_snapshot.get("changed_axes") != ["loading.blocks"] \
            or not isinstance(input_snapshot.get("case_physics"), dict) \
            or type(input_root) is not str or not input_root or not Path(input_root).is_absolute() \
            or input_snapshot.get("fresh_state0") is not True \
            or input_snapshot.get("resume_allowed") is not False \
            or input_snapshot.get("line_search") is not False \
            or input_snapshot.get("cycle_jump") is not False:
        raise TerminalValidationError("completed package physical input identity is not exact")
    matlab = lock.get("runtime_expectations", {}).get("matlab")
    full_matlab_version = None if not isinstance(matlab, dict) else (
        f'{matlab.get("version")} ({matlab.get("release")}) {matlab.get("update")}'
    )
    runtime_fields = {
        "status", "authorization_scope", "case_id", "source_commit",
        "runtime_lock_sha256", "matlab_version", "computer", "blas", "lapack",
    }
    if set(runtime_receipt) != runtime_fields \
            or runtime_receipt.get("status") != "PASS" \
            or runtime_receipt.get("authorization_scope") != "production_authorized" \
            or runtime_receipt.get("case_id") != CASE_ID \
            or runtime_receipt.get("source_commit") != lock.get("source_commit") \
            or runtime_receipt.get("runtime_lock_sha256") != lock.get("runtime_lock_sha256") \
            or runtime_receipt.get("matlab_version") != full_matlab_version \
            or not isinstance(matlab, dict) \
            or any(runtime_receipt.get(field) != matlab.get(field)
                   for field in ("computer", "blas", "lapack")):
        raise TerminalValidationError("completed package runtime receipt differs from the locked identity")
    mesh = protocol._read_mat_struct_bytes(
        files["mesh_geometry.mat"], "mesh_geometry", f"{CASE_ID} completed mesh")
    mesh_fields = {
        "node_coords", "connectivity", "mesh_sha256", "connectivity_sha256",
        "mesh_sha256_semantics", "element_ordering_id", "gp_ordering_id",
    }
    if not mesh_fields.issubset(mesh):
        raise TerminalValidationError("completed package mesh identity is incomplete")
    coordinates = protocol._require_double_array(
        mesh["node_coords"], f"{CASE_ID} completed mesh node_coords")
    connectivity = protocol._require_double_array(
        mesh["connectivity"], f"{CASE_ID} completed mesh connectivity")
    rounded = np.rint(connectivity)
    if coordinates.ndim != 2 or coordinates.shape[1] != 2 \
            or connectivity.ndim != 2 or connectivity.shape[1] != 4 \
            or not np.array_equal(connectivity, rounded):
        raise TerminalValidationError("completed package mesh arrays are not exact Q4 geometry")
    mesh_digest = hashlib.sha256(
        np.asarray(coordinates, dtype="<f8").tobytes(order="F")
        + np.asarray(rounded, dtype="<i8").tobytes(order="F")
    ).hexdigest()
    connectivity_digest = hashlib.sha256(
        np.asarray(rounded, dtype="<i8").tobytes(order="F")
    ).hexdigest()
    if mesh.get("mesh_sha256") != manifest.get("mesh_sha256") \
            or mesh.get("element_ordering_id") != manifest.get("element_ordering_id") \
            or mesh.get("gp_ordering_id") != manifest.get("gp_ordering_id") \
            or mesh.get("mesh_sha256_semantics") != \
            "sha256_matlab_column_major_float64_coords_then_int64_connectivity_v1" \
            or (not allow_test_synthetic_mesh_bytes and (
                mesh.get("mesh_sha256") != mesh_digest
                or mesh.get("connectivity_sha256") != connectivity_digest)):
        raise TerminalValidationError("completed package mesh bytes/identity differ")
    state0 = protocol._read_mat_struct_bytes(
        files["state0_analysis.mat"], "state0", f"{CASE_ID} completed analysis state0")
    if not isinstance(state0, dict) or not {"d_node", "alpha_bar_gp"}.issubset(state0):
        raise TerminalValidationError("completed package analysis state0 is incomplete")
    packaged_state0 = protocol._read_mat_struct_bytes(
        files["STATE0.mat"], "state0", f"{CASE_ID} completed packaged state0")
    analysis_damage = protocol._require_double_array(
        state0["d_node"], f"{CASE_ID} completed analysis state0.d_node")
    analysis_alpha = protocol._require_double_array(
        state0["alpha_bar_gp"], f"{CASE_ID} completed analysis state0.alpha_bar_gp")
    packaged_damage = protocol._require_double_array(
        packaged_state0.get("d_node"), f"{CASE_ID} completed packaged state0.d_node")
    packaged_alpha = protocol._require_double_array(
        packaged_state0.get("alpha_bar_gp"), f"{CASE_ID} completed packaged state0.alpha_bar_gp")
    if analysis_damage.shape != (coordinates.shape[0], 1) \
            or analysis_alpha.shape != (connectivity.shape[0], 4) \
            or not np.array_equal(analysis_damage, packaged_damage) \
            or not np.array_equal(analysis_alpha, packaged_alpha):
        raise TerminalValidationError("completed mesh and initial-state physical dimensions differ")
    if receipt.get("manifest_sha256") != hashlib.sha256(
            files["TERMINAL_MANIFEST.json"]).hexdigest() \
            or receipt.get("execution_input_lock_sha256") != execution_digest:
        raise TerminalValidationError("completed authentication receipt differs from package identities")
    protocol.recheck_authenticated_package(receipt)
    return {
        "manifest": manifest,
        "lock": lock,
        "input_snapshot": input_snapshot,
        "runtime_receipt": runtime_receipt,
        "mesh": mesh,
        "physical_input_sha256": physical_digest,
    }


def _authenticate_completed_package(
        protocol: Any, package_root: Path, *,
        allow_test_synthetic_mesh_bytes: bool = False,
) -> tuple[dict[str, object], dict[str, object]]:
    """Internal completed authentication with one explicit fixture-only mesh seam."""
    root = Path(package_root)
    try:
        snapshot = protocol._capture_package_bytes(
            protocol._canonical_package_root(root, CASE_ID), CASE_ID
        )
        terminal = protocol._read_json_bytes(
            snapshot["bytes"].get("TERMINAL_RESULT.json"), f"{CASE_ID} terminal result"
        )
        classification = classify_terminal(terminal)
        if classification == "PASS_CONFIRMED_FRACTURE_TRAJECTORY":
            receipt = protocol.authenticate_terminal_package(root, CASE_ID)
            _validate_package_checksum(protocol, snapshot)
        elif classification == "PASS_NO_CONFIRMED_FRACTURE_BY_C150":
            receipt = _authenticate_right_censored_package(protocol, root)
        else:
            raise TerminalValidationError("completed-package authentication received a failure outcome")
        if protocol._package_snapshot_sha256(snapshot) != receipt.get("package_snapshot_sha256"):
            raise TerminalValidationError(
                "completed trajectory gate snapshot differs from authoritative authentication"
            )
        artifacts = _validate_completed_production_artifacts(
            protocol, root, receipt,
            allow_test_synthetic_mesh_bytes=allow_test_synthetic_mesh_bytes,
        )
        _validate_snapshot_running_envelope(
            protocol, snapshot, artifacts["mesh"]["connectivity"],
            f"{CASE_ID} completed package")
        return receipt, artifacts
    except TerminalValidationError:
        raise
    except Exception as error:
        raise TerminalValidationError(f"authoritative completed package validation failed: {error}") from error


def authenticate_completed_package(protocol: Any, package_root: Path) -> dict[str, object]:
    """Public authentication has no caller-controlled production-identity relaxation."""
    receipt, _ = _authenticate_completed_package(protocol, package_root)
    return receipt


def _validate_completed_sealed_chain(
        artifacts: Mapping[str, object], authenticated: Mapping[str, object], *,
        sealed_base_root: Path, case_contract: Mapping[str, object], lock: Mapping[str, object],
        launch: Any, repo_root: Path, writable_roots: Mapping[str, object],
) -> None:
    """Cross-bind authenticated output identities to the sealed producer and exact case."""
    manifest = artifacts.get("manifest")
    snapshot = artifacts.get("input_snapshot")
    if not isinstance(manifest, dict) or not isinstance(snapshot, dict):
        raise TerminalValidationError("completed production identity snapshot is missing")
    physics = case_contract.get("physics")
    mesh_identity = physics.get("mesh") if isinstance(physics, dict) else None
    mesh = artifacts.get("mesh")
    expected_components = {
        field: _sha256(sealed_base_root / relative)
        for field, relative in COMPONENT_IDENTITY_FILES.items()
    }
    if manifest.get("source_commit") != lock.get("source_commit") \
            or any(manifest.get(field) != digest for field, digest in expected_components.items()) \
            or snapshot.get("case_physics") != physics \
            or snapshot.get("changed_axes") != case_contract.get("changed_axes") \
            or not isinstance(mesh_identity, dict) \
            or not isinstance(mesh, dict) \
            or any(manifest.get(field) != mesh_identity.get(field) for field in (
                "mesh_sha256", "element_ordering_id", "gp_ordering_id")) \
            or any(mesh.get(field) != mesh_identity.get(field) for field in (
                "mesh_sha256", "connectivity_sha256", "mesh_sha256_semantics",
                "element_ordering_id", "gp_ordering_id")) \
            or manifest.get("state_semantics_id") != "five_substep_post_commit_history_v1" \
            or authenticated.get("runtime_lock_sha256") != lock.get("runtime_lock_sha256") \
            or authenticated.get("family_contract_sha256") != lock.get("family_contract_sha256") \
            or authenticated.get("case_physics_contract_sha256") != lock.get(
                "case_physics_contract_sha256"):
        raise TerminalValidationError(
            "completed source/physical identity differs from the sealed case contract")
    input_root_text = snapshot.get("input_assets_root")
    if type(input_root_text) is not str:
        raise TerminalValidationError("completed physical input asset root is invalid")
    input_root = Path(input_root_text)
    try:
        launch.require_no_reparse_chain(input_root, "completed input assets")
        launch.require_input_assets(
            repo_root, input_root,
            {name: Path(value) for name, value in writable_roots.items()},
        )
    except Exception as error:
        raise TerminalValidationError(
            f"completed physical input assets differ from launch qualification: {error}") from error


def _validate_incomplete_c5_trace(
        protocol: Any, payload: bytes, terminal: Mapping[str, object],
        classification: str) -> None:
    """Validate the exact c5 trace state at a failure before the PASS receipt exists."""
    if not payload.endswith(b"\n") or b"\r" in payload:
        raise TerminalValidationError("incomplete c5 trace bytes are not canonical")
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("ascii"), newline=""))
        if tuple(reader.fieldnames or ()) != protocol.TRACE_COLUMNS:
            raise TerminalValidationError("incomplete c5 trace columns are invalid")
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as error:
        raise TerminalValidationError(f"incomplete c5 trace is malformed: {error}") from error
    parsed: list[dict[str, float | int | str]] = []
    for index, row in enumerate(rows, start=1):
        if set(row) != set(protocol.TRACE_COLUMNS) or any(value is None for value in row.values()):
            raise TerminalValidationError("incomplete c5 trace row is malformed")
        try:
            cycle = protocol._parse_csv_int(row["cycle"], "failure c5 cycle")
            substep = protocol._parse_csv_int(row["substep_ordinal"], "failure c5 substep")
            stagger = protocol._parse_csv_int(row["stagger_iteration"], "failure c5 iteration")
            reassembly = protocol._parse_csv_int(row["reassembly_ordinal"], "failure c5 reassembly")
            metrics = {
                field: protocol._parse_csv_float(row[field], f"failure c5 {field}")
                for field in protocol.TRACE_COLUMNS[6:]
            }
        except Exception as error:
            raise TerminalValidationError(f"incomplete c5 trace value is invalid: {error}") from error
        if row["authorization_scope"] != "production_authorized" \
                or row["case_id"] != CASE_ID or cycle != 5 or substep != 4 \
                or stagger != index or reassembly != index \
                or any(not math.isfinite(float(value)) or value < 0 for value in metrics.values()):
            raise TerminalValidationError("incomplete c5 trace identity or chronology is invalid")
        parsed.append({**metrics, "stagger_iteration": stagger})
    failure_substep = terminal.get("substep")
    if type(failure_substep) is not int:
        raise TerminalValidationError("c5 failure substep is invalid")
    if failure_substep == 4 and classification == "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE":
        if len(parsed) != 1000:
            raise TerminalValidationError("c5 fixed-point failure trace must reach the exact iteration cap")
        final = parsed[-1]
        if float(final["displacement_residual"]) > 4e-4 \
                or float(final["projected_phase_kkt"]) > 4e-4 \
                or float(final["primal_feasibility"]) > 1e-12 \
                or float(final["consecutive_stagger_delta"]) <= 1e-3:
            raise TerminalValidationError("c5 fixed-point trace does not prove exact nonconvergence")
    elif failure_substep == 4 and len(parsed) >= 1000:
        raise TerminalValidationError("c5 Newton failure cannot be recast as iteration-cap failure")


def _validate_failure_package(
        failure_root: Path, terminal: Mapping[str, object], classification: str,
        lock: Mapping[str, object], protocol: Any, run_root: Path,
        launch_receipt: Mapping[str, object], seal_sha256: str,
        extension_manifest_sha256: str, case_contract: Mapping[str, object]) -> dict[str, object]:
    """Authenticate the exact T2-pattern immutable T3-rev failure dossier."""
    root = Path(failure_root)
    if root != run_root / "T3_REV_FAILURE_PACKAGE" or not root.is_dir():
        raise TerminalValidationError("numerical failure package must use the fixed run-local root")
    manifest = _strict_json(root / "PACKAGE_MANIFEST.json")
    failure = _strict_json(root / "FAILURE_CLASSIFICATION.json")
    identities = _strict_json(root / "SOURCE_RUNTIME_INPUT_IDENTITIES.json")
    manifest_fields = {
        "schema_version", "case_id", "status", "source_run_root",
        "artifact_file_count", "artifact_aggregate_sha256", "artifacts",
    }
    failure_fields = {
        "schema_version", "case_id", "status", "failure_cycle", "failure_substep",
        "failure_layer", "newton_failure", "fixed_point_tolerance",
        "stagger_iteration_cap", "completed_cycle_shards", "automatic_retry_performed",
    }
    if set(manifest) != manifest_fields \
            or manifest.get("schema_version") != "toy_road_t3_rev_immutable_failure_package_v1" \
            or manifest.get("case_id") != CASE_ID or manifest.get("status") != classification \
            or manifest.get("source_run_root") != str(run_root) \
            or set(failure) != failure_fields \
            or failure.get("schema_version") != "toy_road_t3_rev_failure_classification_v1" \
            or failure.get("case_id") != CASE_ID or failure.get("status") != classification:
        raise TerminalValidationError("failure package manifest or classification schema is not exact")
    expected_layer = "coupled_damage_fixed_point" if classification.endswith("FIXED_POINT_NONCONVERGENCE") else "newton"
    observed_layer = failure.get("failure_layer")
    if failure.get("failure_cycle") != terminal.get("cycle") \
            or failure.get("failure_substep") != terminal.get("substep") \
            or (expected_layer == "coupled_damage_fixed_point" and observed_layer != expected_layer) \
            or (expected_layer == "newton" and observed_layer not in {"displacement_newton", "phase_newton"}) \
            or failure.get("newton_failure") is not (expected_layer == "newton") \
            or type(failure.get("fixed_point_tolerance")) is not float \
            or failure.get("fixed_point_tolerance") != 1e-3 \
            or type(failure.get("stagger_iteration_cap")) is not int \
            or failure.get("stagger_iteration_cap") != 1000 \
            or failure.get("automatic_retry_performed") is not False:
        raise TerminalValidationError("failure package classification does not bind the terminal numerical failure")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or manifest.get("artifact_file_count") != len(artifacts):
        raise TerminalValidationError("failure package artifact inventory is malformed")
    canonical_artifacts = json.dumps(
        artifacts, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    if manifest.get("artifact_aggregate_sha256") != hashlib.sha256(canonical_artifacts).hexdigest():
        raise TerminalValidationError("failure package artifact aggregate differs")
    paths: list[str] = []
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
            raise TerminalValidationError("failure package artifact entry is malformed")
        relative = item["path"]
        if not isinstance(relative, str) or not relative.startswith("artifacts/") or relative in paths:
            raise TerminalValidationError("failure package artifact path is invalid")
        copied = root / relative
        if not copied.is_file() or copied.stat().st_size != item["bytes"] or _sha256(copied) != item["sha256"]:
            raise TerminalValidationError("failure package artifact bytes do not match inventory")
        live = run_root / Path(relative).relative_to("artifacts")
        if not live.is_file() or live.read_bytes() != copied.read_bytes():
            raise TerminalValidationError("failure package artifact is not the immutable live run byte identity")
        paths.append(relative)
    completed = failure.get("completed_cycle_shards")
    if type(completed) is not int or completed != terminal.get("cycle", 0) - 1:
        raise TerminalValidationError("failure package does not bind exact completed sequential shards")
    expected_relatives = {
        "launcher.pid", "T3_REV.stdout.log", "T3_REV.stderr.log",
        "output/INPUT_SNAPSHOT.json", "output/mesh_geometry.mat", "output/RUN_RESULT.json",
        "output/RUNTIME_RECEIPT.json", "output/state0_analysis.mat",
        "receipts/T3_REV_EXECUTION_INPUT_LOCK.json", "receipts/T3_REV_LAUNCH_RECEIPT.json",
        "receipts/T3_REV_RUNTIME_MEASUREMENT.json",
        *[f"output/substeps/cycle_{cycle:04d}.mat" for cycle in range(1, completed + 1)],
    }
    failure_cycle = terminal.get("cycle", 0)
    failure_substep = terminal.get("substep", 0)
    c5_trace_required = failure_cycle > 5 or (failure_cycle == 5 and failure_substep >= 4)
    c5_pass_required = failure_cycle > 5 or (failure_cycle == 5 and failure_substep == 5)
    if c5_trace_required:
        expected_relatives.add("output/qualification/C5_STAGGER_TRACE.csv")
    if c5_pass_required:
        expected_relatives.add("output/qualification/C5_NUMERICAL_GATE_RECEIPT.json")
    expected_artifact_paths = sorted(f"artifacts/{relative}" for relative in expected_relatives)
    if paths != expected_artifact_paths:
        raise TerminalValidationError("failure package artifact closure is not the exact phase-specific set")
    expected_live_output = sorted(
        relative.removeprefix("output/") for relative in expected_relatives
        if relative.startswith("output/")
    )
    actual_live_output = sorted(
        path.relative_to(run_root / "output").as_posix()
        for path in (run_root / "output").rglob("*") if path.is_file()
    )
    if actual_live_output != expected_live_output:
        raise TerminalValidationError("live numerical-failure output closure is not exact")
    package_files = sorted(
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    )
    if package_files != sorted({
            "PACKAGE_MANIFEST.json", "FAILURE_CLASSIFICATION.json",
            "SOURCE_RUNTIME_INPUT_IDENTITIES.json", "SHA256SUMS.txt", *expected_artifact_paths}):
        raise TerminalValidationError("failure package contains undeclared or missing files")
    sums_payload = (root / "SHA256SUMS.txt").read_bytes()
    if not sums_payload.endswith(b"\n") or b"\r" in sums_payload:
        raise TerminalValidationError("failure package checksum ledger bytes are not canonical")
    sums: dict[str, str] = {}
    try:
        sum_lines = sums_payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise TerminalValidationError("failure package checksum ledger is not ASCII") from error
    for line in sum_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None or match.group(2) in sums:
            raise TerminalValidationError("failure package checksum row is malformed")
        sums[match.group(2)] = match.group(1)
    expected_sums = sorted(set(package_files) - {"SHA256SUMS.txt"})
    if list(sums) != expected_sums \
            or any(_sha256(root / relative) != digest for relative, digest in sums.items()):
        raise TerminalValidationError("failure package checksum closure or digest differs")
    identity_fields = {"schema_version", "producer", "runtime", "input", "launch"}
    producer = identities.get("producer")
    runtime = identities.get("runtime")
    input_identity = identities.get("input")
    launch_identity = identities.get("launch")
    if set(identities) != identity_fields \
            or identities.get("schema_version") != "toy_road_t3_rev_failure_identity_v1" \
            or not all(isinstance(value, dict) for value in (
                producer, runtime, input_identity, launch_identity)):
        raise TerminalValidationError("failure package identity schema is not exact")
    if set(producer) != {"source_commit", "source_manifest_sha256", "family_contract_sha256", "case_physics_contract_sha256"} \
            or any(producer.get(field) != lock.get(field) for field in producer) \
            or set(runtime) != {"runtime_lock_sha256", "matlab", "binary_sha256", "thread_settings"} \
            or runtime.get("runtime_lock_sha256") != lock.get("runtime_lock_sha256") \
            or runtime.get("matlab") != lock.get("runtime_expectations", {}).get("matlab") \
            or runtime.get("binary_sha256") != lock.get("runtime_expectations", {}).get("binary_sha256") \
            or runtime.get("thread_settings") != launch_receipt.get("thread_environment"):
        raise TerminalValidationError("failure package producer/runtime identity differs from the lock")
    lock_sha256 = _sha256(run_root / "receipts" / "T3_REV_EXECUTION_INPUT_LOCK.json")
    artifact_root = root / "artifacts"
    snapshot_path = artifact_root / "output" / "INPUT_SNAPSHOT.json"
    snapshot = _strict_json(snapshot_path)
    if set(input_identity) != {"execution_input_lock_sha256", "input_snapshot_sha256", "mesh_sha256", "output_root", "run_root"} \
            or input_identity.get("execution_input_lock_sha256") != lock_sha256 \
            or input_identity.get("input_snapshot_sha256") != _sha256(snapshot_path) \
            or input_identity.get("mesh_sha256") != snapshot.get("mesh_sha256") \
            or input_identity.get("output_root") != str(run_root / "output") \
            or input_identity.get("run_root") != str(run_root):
        raise TerminalValidationError("failure package input/root identity differs")
    measurement_path = run_root / "receipts" / "T3_REV_RUNTIME_MEASUREMENT.json"
    launch_path = run_root / "receipts" / "T3_REV_LAUNCH_RECEIPT.json"
    if set(launch_identity) != {"seal_sha256", "launch_receipt_sha256", "runtime_measurement_sha256", "extension_source_manifest_sha256"} \
            or launch_identity.get("seal_sha256") != seal_sha256 \
            or launch_identity.get("launch_receipt_sha256") != _sha256(launch_path) \
            or launch_identity.get("runtime_measurement_sha256") != _sha256(measurement_path) \
            or launch_identity.get("extension_source_manifest_sha256") != extension_manifest_sha256:
        raise TerminalValidationError("failure package launch-chain identity differs")
    snapshot_fields = {
        "schema_version", "authorization_scope", "case_id", "source_commit",
        "runtime_lock_sha256", "family_contract_sha256", "case_physics_contract_sha256",
        "execution_input_lock_sha256", "input_assets_root", "mesh_sha256", "changed_axes",
        "case_physics", "fresh_state0", "resume_allowed", "line_search", "cycle_jump",
    }
    physics = case_contract.get("physics")
    mesh_identity = physics.get("mesh") if isinstance(physics, dict) else None
    if set(snapshot) != snapshot_fields or snapshot.get("schema_version") != "toy_road_p0_input_snapshot_v1" \
            or snapshot.get("authorization_scope") != "production_authorized" \
            or snapshot.get("case_id") != CASE_ID \
            or any(snapshot.get(field) != lock.get(field) for field in (
                "source_commit", "runtime_lock_sha256", "family_contract_sha256",
                "case_physics_contract_sha256")) \
            or snapshot.get("execution_input_lock_sha256") != lock_sha256 \
            or snapshot.get("changed_axes") != ["loading.blocks"] \
            or snapshot.get("case_physics") != physics \
            or not isinstance(mesh_identity, dict) \
            or snapshot.get("mesh_sha256") != mesh_identity.get("mesh_sha256") \
            or snapshot.get("fresh_state0") is not True \
            or snapshot.get("resume_allowed") is not False \
            or snapshot.get("line_search") is not False or snapshot.get("cycle_jump") is not False:
        raise TerminalValidationError("failure package input snapshot is not the exact locked case")
    mesh = protocol._read_mat_struct_bytes(
        (artifact_root / "output" / "mesh_geometry.mat").read_bytes(),
        "mesh_geometry", f"{CASE_ID} failure mesh",
    )
    required_mesh_fields = {
        "node_coords", "connectivity", "mesh_sha256", "connectivity_sha256",
        "mesh_sha256_semantics", "element_ordering_id", "gp_ordering_id",
    }
    if not required_mesh_fields.issubset(mesh):
        raise TerminalValidationError("failure package mesh metadata is incomplete")
    coordinates = protocol._require_double_array(
        mesh["node_coords"], f"{CASE_ID} failure mesh node_coords")
    connectivity_values = protocol._require_double_array(
        mesh["connectivity"], f"{CASE_ID} failure mesh connectivity")
    rounded_connectivity = np.rint(connectivity_values)
    if coordinates.ndim != 2 or coordinates.shape[1] != 2 or connectivity_values.ndim != 2 \
            or connectivity_values.shape[1] != 4 \
            or not np.array_equal(connectivity_values, rounded_connectivity):
        raise TerminalValidationError("failure package mesh arrays are not exact Q4 geometry")
    if coordinates.shape[0] == 0 or connectivity_values.shape[0] == 0:
        raise TerminalValidationError("failure package mesh arrays must be nonempty")
    if np.any(rounded_connectivity < 1) or np.any(
            rounded_connectivity > coordinates.shape[0]):
        raise TerminalValidationError(
            "failure package mesh connectivity indices are outside authenticated node rows"
        )
    mesh_digest = hashlib.sha256(
        np.asarray(coordinates, dtype="<f8").tobytes(order="F")
        + np.asarray(rounded_connectivity, dtype="<i8").tobytes(order="F")
    ).hexdigest()
    connectivity_digest = hashlib.sha256(
        np.asarray(rounded_connectivity, dtype="<i8").tobytes(order="F")
    ).hexdigest()
    if mesh.get("mesh_sha256") != mesh_digest \
            or mesh_digest != snapshot.get("mesh_sha256") \
            or connectivity_digest != mesh_identity.get("connectivity_sha256") \
            or mesh.get("connectivity_sha256") != connectivity_digest \
            or mesh.get("mesh_sha256_semantics") != mesh_identity.get("mesh_sha256_semantics") \
            or mesh.get("element_ordering_id") != mesh_identity.get("element_ordering_id") \
            or mesh.get("gp_ordering_id") != mesh_identity.get("gp_ordering_id"):
        raise TerminalValidationError("failure package mesh arrays/identity differ from the case contract")
    runtime_receipt = _strict_json(artifact_root / "output" / "RUNTIME_RECEIPT.json")
    matlab = lock.get("runtime_expectations", {}).get("matlab")
    full_matlab_version = None if not isinstance(matlab, dict) else (
        f'{matlab.get("version")} ({matlab.get("release")}) {matlab.get("update")}'
    )
    if set(runtime_receipt) != {"status", "authorization_scope", "case_id", "source_commit", "runtime_lock_sha256", "matlab_version", "computer", "blas", "lapack"} \
            or runtime_receipt.get("status") != "PASS" \
            or runtime_receipt.get("authorization_scope") != "production_authorized" \
            or runtime_receipt.get("case_id") != CASE_ID \
            or runtime_receipt.get("source_commit") != lock.get("source_commit") \
            or runtime_receipt.get("runtime_lock_sha256") != lock.get("runtime_lock_sha256") \
            or not isinstance(matlab, dict) \
            or runtime_receipt.get("matlab_version") != full_matlab_version \
            or any(runtime_receipt.get(field) != matlab.get(field) for field in ("computer", "blas", "lapack")):
        raise TerminalValidationError("failure package runtime receipt differs from the PASS measurement lock")
    run_result = _strict_json(artifact_root / "output" / "RUN_RESULT.json")
    if set(run_result) != {"authorization_scope", "case_id", "complete", "status", "error_identifier", "error_message"} \
            or run_result.get("authorization_scope") != "production_authorized" \
            or run_result.get("case_id") != CASE_ID or run_result.get("complete") is not False \
            or run_result.get("status") != "failed":
        raise TerminalValidationError("failure package RUN_RESULT schema or status is invalid")
    if expected_layer == "coupled_damage_fixed_point":
        expected_error = (
            "toyRoadP0:StaggeredSolveFailed",
            f"Stagger convergence failed at cycle {terminal['cycle']} substep {terminal['substep']}.",
        )
    else:
        expected_error = (
            "toyRoadP0:DisplacementSolveFailed" if observed_layer == "displacement_newton"
            else "toyRoadP0:PhaseSolveFailed",
            "The displacement Newton solve failed." if observed_layer == "displacement_newton"
            else "The phase Newton solve failed.",
        )
    if (run_result.get("error_identifier"), run_result.get("error_message")) != expected_error \
            or expected_error[1] not in (artifact_root / "T3_REV.stderr.log").read_text(encoding="utf-8"):
        raise TerminalValidationError("failure package numerical error class/message differs")
    if c5_pass_required:
        c5_snapshot = {"bytes": {
            "qualification/C5_STAGGER_TRACE.csv": (
                artifact_root / "output" / "qualification" / "C5_STAGGER_TRACE.csv"
            ).read_bytes(),
            "qualification/C5_NUMERICAL_GATE_RECEIPT.json": (
                artifact_root / "output" / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json"
            ).read_bytes(),
        }}
        protocol._validate_c5(c5_snapshot, {
            "authorization_scope": "production_authorized", "case_id": CASE_ID,
        }, CASE_ID)
    elif c5_trace_required:
        _validate_incomplete_c5_trace(
            protocol,
            (artifact_root / "output" / "qualification" / "C5_STAGGER_TRACE.csv").read_bytes(),
            terminal, classification,
        )
    state0 = protocol._read_mat_struct_bytes(
        (artifact_root / "output" / "state0_analysis.mat").read_bytes(),
        "state0", f"{CASE_ID} failure state0"
    )
    if not isinstance(state0, dict) or not {"d_node", "alpha_bar_gp"}.issubset(state0):
        raise TerminalValidationError("failure package state0 is incomplete")
    state0_damage = protocol._require_double_array(state0["d_node"], f"{CASE_ID} failure state0.d_node")
    state0_alpha = protocol._require_double_array(state0["alpha_bar_gp"], f"{CASE_ID} failure state0.alpha_bar_gp")
    if state0_damage.shape != (coordinates.shape[0], 1) \
            or state0_alpha.shape != (connectivity_values.shape[0], 4):
        raise TerminalValidationError(
            "failure package mesh/state dimensions are not the authenticated geometry dimensions"
        )
    if np.any(state0_damage < -protocol.THRESHOLD) \
            or np.any(state0_damage > 1 + protocol.THRESHOLD):
        raise TerminalValidationError("failure package state0 damage lies outside [0, 1]")
    if np.any(state0_alpha < -protocol.THRESHOLD):
        raise TerminalValidationError("failure package state0 alpha must be nonnegative")
    if not isinstance(mesh_identity, dict):
        raise TerminalValidationError("failure package mesh contract is missing")
    shard_manifest = {
        "mesh_sha256": snapshot["mesh_sha256"],
        "element_ordering_id": mesh_identity.get("element_ordering_id"),
        "gp_ordering_id": mesh_identity.get("gp_ordering_id"),
        "state_semantics_id": "five_substep_post_commit_history_v1",
        "runtime_lock_sha256": lock["runtime_lock_sha256"],
        "family_contract_sha256": lock["family_contract_sha256"],
        "case_physics_contract_sha256": lock["case_physics_contract_sha256"],
        "execution_input_lock_sha256": lock_sha256,
    }
    previous_damage, previous_alpha = state0_damage[:, 0], state0_alpha
    for cycle in range(1, completed + 1):
        shard = protocol._read_mat_struct_bytes(
            (artifact_root / "output" / "substeps" / f"cycle_{cycle:04d}.mat").read_bytes(),
            "shard", f"{CASE_ID} failure cycle {cycle}",
        )
        previous_damage, previous_alpha = protocol._validate_shard(
            shard, shard_manifest, cycle, CASE_ID, previous_damage, previous_alpha,
            state0_damage.shape[0], state0_alpha.shape[0],
        )

    def authenticated_failure_shards() -> Iterable[Mapping[str, object]]:
        for cycle in range(1, completed + 1):
            yield protocol._read_mat_struct_bytes(
                (artifact_root / "output" / "substeps" /
                 f"cycle_{cycle:04d}.mat").read_bytes(),
                "shard", f"{CASE_ID} failure trajectory cycle {cycle}",
            )

    _validate_trajectory_running_envelope(
        protocol, state0_damage, state0_alpha,
        authenticated_failure_shards(), rounded_connectivity,
        f"{CASE_ID} failure package",
    )
    for item in artifacts:
        relative = item["path"]
        copied = root / relative
        live = run_root / Path(relative).relative_to("artifacts")
        if _sha256(copied) != item["sha256"] or copied.read_bytes() != live.read_bytes():
            raise TerminalValidationError("failure artifacts changed during authentication")
    package_digest = hashlib.sha256("".join(
        f"{relative}\0{_sha256(root / relative)}\n" for relative in package_files
    ).encode("utf-8")).hexdigest()
    is_newton = classification == "FAIL_NEWTON_NONCONVERGENCE"
    independently_authenticated_substep = (
        failure_substep if not is_newton
        else failure_substep if failure_cycle == 5 and failure_substep in {4, 5}
        else None
    )
    return {
        "failure_package_sha256": package_digest,
        "package_manifest_sha256": _sha256(root / "PACKAGE_MANIFEST.json"),
        "failure_classification_sha256": _sha256(root / "FAILURE_CLASSIFICATION.json"),
        "sha256sums_sha256": _sha256(root / "SHA256SUMS.txt"),
        "self_reported_substep": failure_substep,
        "substep_provenance": (
            "c5_trace_lifecycle" if is_newton and independently_authenticated_substep == 4
            else "c5_pass_receipt_lifecycle" if is_newton and independently_authenticated_substep == 5
            else "failure_class_implied" if independently_authenticated_substep is not None
            else "producer_self_report_only"
        ),
        "substep_authenticated": independently_authenticated_substep is not None,
        "authenticated_substep": independently_authenticated_substep,
    }


def _validate_failed_runtime_measurement(
        protocol: Any, lock: Mapping[str, object], measurement_path: Path,
        terminal: Mapping[str, object]) -> None:
    """Validate the only producer-written FAIL receipt: path-prefix qualification."""
    measurement = _strict_json(measurement_path)
    fields = {
        "schema_version", "protocol_version", "authorization_scope", "status",
        "producer_entrypoint_authorized", "execution_input_lock_sha256",
        "first_failed_predicate", "first_mismatch_index", "expected_absolute_path",
        "actual_absolute_path", "expected_normalized_path", "actual_normalized_path",
        "matlab_identifier", "message",
    }
    expected_paths = lock.get("runtime_expectations", {}).get("matlab", {}).get(
        "absolute_path_order")
    expected_raw = measurement.get("expected_absolute_path")
    actual_raw = measurement.get("actual_absolute_path")
    expected_normalized = measurement.get("expected_normalized_path")
    actual_normalized = measurement.get("actual_normalized_path")
    mismatch = measurement.get("first_mismatch_index")
    normalized_expected_raw = [
        str(Path(value).resolve()) for value in expected_raw
    ] if isinstance(expected_raw, list) and all(type(value) is str for value in expected_raw) else None
    normalized_actual_raw = [
        str(Path(value).resolve()) for value in actual_raw
    ] if isinstance(actual_raw, list) and all(type(value) is str for value in actual_raw) else None
    if set(measurement) != fields \
            or measurement.get("schema_version") != "toy_road_runtime_measurement_v1" \
            or measurement.get("protocol_version") != lock.get("protocol_version") \
            or measurement.get("authorization_scope") != lock.get("authorization_scope") \
            or measurement.get("status") != "FAIL" \
            or measurement.get("producer_entrypoint_authorized") is not False \
            or measurement.get("execution_input_lock_sha256") != _sha256(
                measurement_path.parent / "T3_REV_EXECUTION_INPUT_LOCK.json") \
            or measurement.get("first_failed_predicate") != "matlab_path_precedence" \
            or measurement.get("matlab_identifier") != "toyRoadP0:RuntimeQualificationFailed" \
            or type(mismatch) is not int or mismatch < 1 \
            or not all(isinstance(value, list) for value in (
                expected_raw, actual_raw, expected_normalized, actual_normalized)) \
            or expected_raw != expected_paths \
            or expected_normalized != normalized_expected_raw \
            or actual_normalized != normalized_actual_raw \
            or len(expected_raw) != len(expected_normalized) \
            or len(actual_raw) != len(actual_normalized) \
            or not all(type(value) is str and value for collection in (
                expected_raw, actual_raw, expected_normalized, actual_normalized)
                       for value in collection):
        raise TerminalValidationError("runtime qualification FAIL measurement schema is not exact")
    shorter = len(actual_normalized) < len(expected_normalized)
    if shorter:
        expected_mismatch = len(actual_normalized) + 1
        expected_message = "MATLAB path is shorter than the locked path prefix."
    else:
        differing = [
            index for index, (actual, expected) in enumerate(
                zip(actual_normalized[:len(expected_normalized)], expected_normalized), start=1)
            if actual != expected
        ]
        if not differing:
            raise TerminalValidationError("runtime qualification FAIL receipt proves no path mismatch")
        expected_mismatch = differing[0]
        expected_message = "Measured absolute MATLAB path precedence differs from the lock."
    expected_terminal_message = f"{expected_message} First mismatch index: {expected_mismatch}."
    if mismatch != expected_mismatch or measurement.get("message") != expected_message \
            or terminal.get("error_message") != expected_terminal_message \
            or measurement_path.read_bytes() != protocol.canonical_json_bytes(measurement):
        raise TerminalValidationError("runtime qualification FAIL measurement semantics differ")


def _validate_startup_or_runtime_failure(
        terminal: Mapping[str, object], classification: str, receipts: Path,
        launch_receipt: Mapping[str, object], seal_sha256: str, run_root: Path,
        lock: Mapping[str, object], protocol: Any) -> dict[str, object]:
    """Validate phase-appropriate failure evidence before demanding producer artifacts."""
    fields = {
        "schema_version", "status", "case_id", "terminal_reason", "failure_phase",
        "cycle", "substep", "error_identifier", "error_message", "seal_sha256",
        "run_root", "launch_receipt_sha256", "runtime_measurement_sha256",
        "failure_package_manifest_sha256",
    }
    phase = terminal.get("failure_phase")
    expected = {
        "bootstrap_before_runtime_measurement": (
            "FAIL_STARTUP", "toyRoad:LaunchCredentialTimeout"),
        "runtime_qualification_before_producer": (
            "FAIL_RUNTIME", "toyRoadP0:RuntimeQualificationFailed"),
        "producer_after_pass_runtime_measurement": (
            "FAIL_RUNTIME", "toyRoadP0:MissingInputAsset"),
    }
    expected_outcome = expected.get(phase)
    if set(terminal) != fields \
            or terminal.get("schema_version") != "toy_road_t3_rev_terminal_failure_v1" \
            or terminal.get("status") != classification \
            or terminal.get("case_id") != CASE_ID \
            or expected_outcome is None or expected_outcome[0] != classification \
            or terminal.get("error_identifier") != expected_outcome[1] \
            or not isinstance(terminal.get("error_message"), str) \
            or not terminal.get("error_message") \
            or terminal.get("cycle") is not None or terminal.get("substep") is not None \
            or terminal.get("failure_package_manifest_sha256") is not None \
            or terminal.get("seal_sha256") != seal_sha256 or terminal.get("run_root") != str(run_root) \
            or terminal.get("launch_receipt_sha256") != _sha256(receipts / "T3_REV_LAUNCH_RECEIPT.json"):
        raise TerminalValidationError("startup/runtime failure receipt class, phase, or binding is not exact")
    if phase == "bootstrap_before_runtime_measurement" \
            and terminal.get("error_message") != "Exact launch credential was not published":
        raise TerminalValidationError("bootstrap failure message is not the launched helper error")
    if phase == "producer_after_pass_runtime_measurement" \
            and re.fullmatch(r"The locked SENS mesh source is absent: .+[\\/]sens_mesh\.m",
                             str(terminal.get("error_message"))) is None:
        raise TerminalValidationError("post-authorization failure message is not the producer error")
    required_logs = (run_root / "T3_REV.stdout.log", run_root / "T3_REV.stderr.log")
    if not all(path.is_file() for path in required_logs):
        raise TerminalValidationError("startup/runtime failure does not retain both launch logs")
    if terminal["error_message"] not in required_logs[1].read_text(encoding="utf-8"):
        raise TerminalValidationError("startup/runtime failure message is absent from stderr")
    measurement_path = receipts / "T3_REV_RUNTIME_MEASUREMENT.json"
    output_files = sorted(
        path.relative_to(run_root / "output").as_posix()
        for path in (run_root / "output").rglob("*") if path.is_file()
    )
    if (run_root / "T3_REV_FAILURE_PACKAGE").exists():
        raise TerminalValidationError("startup/runtime failure cannot carry a numerical failure package")
    if phase == "bootstrap_before_runtime_measurement":
        if measurement_path.exists() or terminal.get("runtime_measurement_sha256") is not None:
            raise TerminalValidationError("pre-measurement failure cannot carry runtime measurement evidence")
        if output_files:
            raise TerminalValidationError("pre-measurement failure cannot carry producer output artifacts")
    elif phase == "runtime_qualification_before_producer":
        if not measurement_path.is_file() \
                or terminal.get("runtime_measurement_sha256") != _sha256(measurement_path):
            raise TerminalValidationError("runtime qualification failure does not bind its FAIL measurement")
        _validate_failed_runtime_measurement(protocol, lock, measurement_path, terminal)
        if output_files:
            raise TerminalValidationError("runtime qualification failure cannot carry producer artifacts")
    else:
        if not measurement_path.is_file() \
                or terminal.get("runtime_measurement_sha256") != _sha256(measurement_path):
            raise TerminalValidationError("post-authorization runtime failure does not bind its PASS measurement")
        try:
            protocol.validate_runtime_measurement(lock, _strict_json(measurement_path))
        except Exception as error:
            raise TerminalValidationError(
                f"post-authorization runtime failure measurement is not genuine PASS: {error}") from error
        if output_files:
            raise TerminalValidationError("post-authorization runtime failure output closure is not exact")
    return {
        "failure_phase": phase,
        "stdout_sha256": _sha256(required_logs[0]),
        "stderr_sha256": _sha256(required_logs[1]),
    }


def _validate_no_pass_bootstrap_evidence(
        run_root: Path, receipts: Path, terminal_root: Path,
        credential_failure_path: Path, timeout_observed: bool,
        launch: Any) -> dict[str, object]:
    """Authenticate a started bootstrap that never received the PASS credential."""
    launch_path = receipts / "T3_REV_LAUNCH_RECEIPT.json"
    measurement_path = receipts / "T3_REV_RUNTIME_MEASUREMENT.json"
    terminal_failure_path = receipts / "T3_REV_TERMINAL_FAILURE.json"
    forbidden = (
        launch_path, measurement_path, terminal_failure_path,
        receipts / "T3_REV_LAUNCH_RECEIPT.INVALIDATED.json",
        receipts / "PREPARED_NO_LAUNCH.json", receipts / "BUSY_NO_LAUNCH.json",
        run_root / "T3_REV_FAILURE_PACKAGE", terminal_root,
    )
    stale = [str(path) for path in forbidden if path.exists()]
    if stale:
        raise TerminalValidationError(
            "bootstrap credential failure carries stale PASS/producer evidence: "
            + ", ".join(stale)
        )
    temporary_credentials = sorted(
        path.name for path in receipts.glob(".T3_REV_LAUNCH_RECEIPT.json.*.tmp")
    )
    if temporary_credentials:
        raise TerminalValidationError(
            "bootstrap credential failure retains unpublished credential bytes"
        )
    stdout_path = run_root / "T3_REV.stdout.log"
    stderr_path = run_root / "T3_REV.stderr.log"
    if not stdout_path.is_file() or not stderr_path.is_file():
        raise TerminalValidationError("bootstrap credential failure lacks exact launcher logs")
    try:
        stderr_lines = stderr_path.read_bytes().splitlines()
    except OSError as error:
        raise TerminalValidationError(f"cannot read bootstrap stderr evidence: {error}") from error
    timeout_line = b"Exact launch credential was not published"
    if timeout_observed != (timeout_line in stderr_lines):
        raise TerminalValidationError("bootstrap credential timeout evidence is not exact")

    pid_path = run_root / "launcher.pid"
    recorded_pid: int | None = None
    if pid_path.is_file():
        pid_bytes = pid_path.read_bytes()
        match = re.fullmatch(rb"([1-9][0-9]*)\n", pid_bytes)
        if match is None:
            raise TerminalValidationError("bootstrap launcher.pid bytes are not canonical")
        recorded_pid = int(match.group(1))

    credential_sha256: str | None = None
    if credential_failure_path.is_file():
        credential = _strict_json(credential_failure_path)
        publication_error_types = {
            "OSError", "FileExistsError", "FileNotFoundError", "PermissionError",
            "NotADirectoryError", "IsADirectoryError", "BlockingIOError", "InterruptedError",
        }
        fields = {
            "schema_version", "status", "case_id", "process_started", "pid",
            "resume_allowed", "retry_allowed", "new_authorization_required", "error_type",
        }
        error_type = credential.get("error_type")
        if set(credential) != fields \
                or credential.get("schema_version") != "toy_road_t3_rev_launch_credential_failed_v1" \
                or credential.get("status") != "LAUNCH_CREDENTIAL_FAILED" \
                or credential.get("case_id") != CASE_ID \
                or credential.get("process_started") is not True \
                or type(credential.get("pid")) is not int or credential["pid"] <= 0 \
                or credential.get("resume_allowed") is not False \
                or credential.get("retry_allowed") is not False \
                or credential.get("new_authorization_required") is not True \
                or error_type not in publication_error_types:
            raise TerminalValidationError("LAUNCH_CREDENTIAL_FAILED receipt schema is not exact")
        if credential_failure_path.read_bytes() != launch.json_payload(credential):
            raise TerminalValidationError("LAUNCH_CREDENTIAL_FAILED receipt bytes are not canonical")
        if recorded_pid is not None and credential.get("pid") != recorded_pid:
            raise TerminalValidationError("credential failure pid differs from launcher.pid")
        credential_sha256 = _sha256(credential_failure_path)
    elif not timeout_observed:
        raise TerminalValidationError("no exact bootstrap credential failure evidence exists")
    elif recorded_pid is None:
        raise TerminalValidationError("credential timeout does not prove a started bootstrap pid")

    allowed_receipts = {
        "T3_REV_EXECUTION_INPUT_LOCK.json",
        *({"LAUNCH_CREDENTIAL_FAILED.json"} if credential_failure_path.is_file() else set()),
    }
    actual_receipts = {
        path.name for path in receipts.iterdir() if path.is_file()
    }
    if actual_receipts != allowed_receipts:
        raise TerminalValidationError("bootstrap credential receipt closure is not exact")
    allowed_top_level = {
        ".toy-road-runtime-overlay", "receipts", "T3_REV.stdout.log", "T3_REV.stderr.log",
        *({"launcher.pid"} if pid_path.is_file() else set()),
    }
    actual_top_level = {path.name for path in run_root.iterdir()}
    if actual_top_level != allowed_top_level:
        raise TerminalValidationError("bootstrap credential run-root closure is not exact")
    return {
        "failure_phase": (
            "launch_credential_publication_failure"
            if credential_failure_path.is_file() else "bootstrap_credential_timeout"
        ),
        "error_identifier": (
            "LAUNCH_CREDENTIAL_FAILED" if credential_failure_path.is_file()
            else "toyRoad:LaunchCredentialTimeout"
        ),
        "credential_failure_sha256": credential_sha256,
        "launcher_pid_sha256": _sha256(pid_path) if pid_path.is_file() else None,
        "stdout_sha256": _sha256(stdout_path),
        "stderr_sha256": _sha256(stderr_path),
    }


def _no_launch_lifecycle_evidence(
        receipts: Path, stderr_path: Path) -> tuple[str, ...]:
    """Inventory every launcher-produced or credential-shaped no-launch marker."""
    evidence: set[str] = set()
    for path in receipts.iterdir():
        name = path.name
        if name == "LAUNCH_CREDENTIAL_FAILED.json" \
                or name.endswith("_NO_LAUNCH.json") \
                or (name != "T3_REV_LAUNCH_RECEIPT.json"
                    and name.startswith("T3_REV_LAUNCH_RECEIPT.")) \
                or name.startswith(".T3_REV_LAUNCH_RECEIPT.json."):
            evidence.add(name)
    if stderr_path.is_file():
        try:
            timeout_observed = b"Exact launch credential was not published" \
                in stderr_path.read_bytes().splitlines()
        except OSError as error:
            raise TerminalValidationError(
                f"cannot read launch lifecycle stderr evidence: {error}") from error
        if timeout_observed:
            evidence.add("toyRoad:LaunchCredentialTimeout")
    return tuple(sorted(evidence))


def _require_exclusive_launch_lifecycle(
        receipts: Path, stderr_path: Path) -> tuple[str, ...]:
    """A live PASS credential is mutually exclusive with all no-launch evidence."""
    evidence = _no_launch_lifecycle_evidence(receipts, stderr_path)
    launch_path = receipts / "T3_REV_LAUNCH_RECEIPT.json"
    if launch_path.exists() and evidence:
        raise TerminalValidationError(
            "live PASS launch receipt conflicts with no-launch lifecycle evidence: "
            + ", ".join(evidence)
        )
    return evidence


def _validate_terminal(
        terminal_root: Path, *, sealed_base_root: Path, extension_root: Path,
        seal_path: Path, run_root: Path | None = None, destination: Path | None = None,
        failure_package_root: Path | None = None, failure_receipt_path: Path | None = None,
        launch: Any | None = None, _emit_adjudication: bool = True,
        preserve_run: bool = False,
        expected_run_inventory: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Authenticate one terminal package and emit one non-authorizing adjudication."""
    test_launch_override = launch is not None
    launch = _load(Path(__file__).with_name("launch_t3_rev.py"), "t3_rev_terminal_launch") \
        if launch is None else launch
    if failure_package_root is not None or failure_receipt_path is not None:
        raise TerminalValidationError("failure evidence roots are fixed by the run contract")
    terminal_root = launch._absolute_literal_path(terminal_root)
    sealed_base_root = launch._absolute_literal_path(sealed_base_root)
    extension_root = launch._absolute_literal_path(extension_root)
    seal_path = launch._absolute_literal_path(seal_path)
    run_root = terminal_root.parent if run_root is None else launch._absolute_literal_path(run_root)
    run_inventory_pre = inventory_run_tree(run_root)
    if expected_run_inventory is not None and expected_run_inventory != run_inventory_pre:
        raise TerminalValidationError("run inventory differs from the retained pre-offline inventory")
    identity_paths = [
        (sealed_base_root, "sealed base"), (extension_root, "extension"),
        (seal_path, "seal"), (run_root, "run root"),
    ]
    if terminal_root.exists():
        identity_paths.insert(0, (terminal_root, "terminal package"))
    for path, label in identity_paths:
        try:
            launch.require_no_reparse_chain(path, label)
        except Exception as error:
            raise TerminalValidationError(f"{label} path identity failed: {error}") from error
    receipts = run_root / "receipts"
    destination = receipts / "T3_REV_TERMINAL_ADJUDICATION.json" if destination is None else Path(destination)
    if preserve_run:
        if not _emit_adjudication or expected_run_inventory is None:
            raise TerminalValidationError(
                "preserve-run mode requires emission and the retained pre-offline inventory"
            )
        destination = destination.resolve()
        try:
            destination.relative_to(run_root)
        except ValueError:
            pass
        else:
            raise TerminalValidationError("preserve-run adjudication destination must be external")
        if destination.exists():
            raise TerminalValidationError(f"terminal adjudication already exists: {destination}")
        if not destination.parent.is_dir():
            raise TerminalValidationError("external adjudication parent must already exist")
    elif _emit_adjudication and launch._literal_path_text(destination) != launch._literal_path_text(
            receipts / "T3_REV_TERMINAL_ADJUDICATION.json"):
        raise TerminalValidationError("terminal adjudication must remain in the run receipt directory")
    verifier = _load(Path(__file__).with_name("verify_extension_diff.py"), "t3_rev_terminal_diff")
    builder = _load(Path(__file__).with_name("build_t3_rev_extension.py"), "t3_rev_terminal_builder")
    base_before = builder.inventory_tree(sealed_base_root)
    extension_before = builder.inventory_tree(extension_root)
    seal = _strict_json(seal_path)
    lock_path = receipts / "T3_REV_EXECUTION_INPUT_LOCK.json"
    lock = _strict_json(lock_path)
    launch_path = receipts / "T3_REV_LAUNCH_RECEIPT.json"
    credential_failure_path = receipts / "LAUNCH_CREDENTIAL_FAILED.json"
    busy_path = receipts / "BUSY_NO_LAUNCH.json"
    prepared_path = receipts / "PREPARED_NO_LAUNCH.json"
    stderr_path = run_root / "T3_REV.stderr.log"
    lifecycle_evidence = _require_exclusive_launch_lifecycle(receipts, stderr_path)
    timeout_observed = "toyRoad:LaunchCredentialTimeout" in lifecycle_evidence
    credential_evidence_exists = credential_failure_path.is_file() or timeout_observed
    if busy_path.is_file():
        raise TerminalValidationError(
            "BUSY_NO_LAUNCH proves the final process check blocked before Popen; "
            "it is not a bootstrap credential terminal"
        )
    if prepared_path.is_file() and not launch_path.is_file():
        raise TerminalValidationError(
            "PREPARED_NO_LAUNCH proves a pre-Popen launch failure, not a credential terminal"
        )
    if credential_evidence_exists and launch_path.exists():
        raise TerminalValidationError(
            "credential failure evidence cannot coexist with a live PASS launch receipt"
        )
    no_pass_bootstrap = credential_evidence_exists and not launch_path.exists()
    launch_receipt: dict[str, object]
    if no_pass_bootstrap:
        launch_receipt = {}
    else:
        launch_receipt = _strict_json(launch_path)
    completed_terminal_path = terminal_root / "TERMINAL_RESULT.json"
    failure_terminal_path = receipts / "T3_REV_TERMINAL_FAILURE.json"
    present_terminal_paths = [
        path for path in (completed_terminal_path, failure_terminal_path) if path.is_file()
    ]
    if no_pass_bootstrap and present_terminal_paths:
        raise TerminalValidationError(
            "bootstrap credential failure cannot carry a producer terminal receipt"
        )
    recovery_nontrajectory = not no_pass_bootstrap and len(present_terminal_paths) == 0
    if not no_pass_bootstrap and not recovery_nontrajectory and len(present_terminal_paths) != 1:
        raise TerminalValidationError("run must contain exactly one fixed completed or failure terminal receipt")
    terminal = (
        {
            "terminal_reason": "startup_failure",
            "failure_phase": "bootstrap_before_runtime_measurement",
        }
        if no_pass_bootstrap else (
            {
                "terminal_reason": "recovery_newton_nonconvergence_before_c1",
                "failure_phase": "fresh_zero_load_recovery_before_cycle_1",
            }
            if recovery_nontrajectory else _strict_json(present_terminal_paths[0])
        )
    )
    classification = classify_terminal(terminal)
    if classification == "FAIL_STARTUP" and not no_pass_bootstrap:
        raise TerminalValidationError(
            "startup credential failure requires the PASS launch receipt to be absent"
        )
    seal_sha256 = require_canonical_seal_bytes(seal_path, seal)
    runtime_identity = seal.get("runtime_identity")
    seal_identity = seal.get("extension_identity")
    if no_pass_bootstrap:
        if not isinstance(runtime_identity, dict) or not isinstance(seal_identity, dict):
            raise TerminalValidationError("canonical seal identities are malformed")
        launch_receipt.update({
            "seal_sha256": seal_sha256,
            "run_root": str(run_root),
            "source_commit": runtime_identity.get("source_commit"),
            "launcher_repository_commit": seal_identity.get("repository_commit"),
            "runtime_lock_sha256": runtime_identity.get("runtime_lock_sha256"),
            "extension_source_manifest_sha256": _sha256(
                extension_root / "EXTENSION_SOURCE_MANIFEST.json"),
            "family_contract_sha256": lock.get("family_contract_sha256"),
            "case_physics_contract_sha256": lock.get("case_physics_contract_sha256"),
            "execution_input_lock_sha256": _sha256(lock_path),
            "launch_nonce": "unpublished-bootstrap-credential",
            "thread_environment": runtime_identity.get("thread_settings"),
            "extension_root": str(extension_root),
            "runtime_overlay_root": str(run_root / ".toy-road-runtime-overlay"),
            "bootstrap_helper_sha256": launch.BOOTSTRAP_HELPER_SHA256,
        })
    else:
        try:
            launch.require_bridge_authorization_receipt(launch_receipt)
        except Exception as error:
            raise TerminalValidationError(f"launch credential is invalid: {error}") from error
    runtime_source_closure = require_runtime_source_closure(
        seal, launch_receipt, allow_unpublished_bootstrap=no_pass_bootstrap)
    try:
        launch._require_seal(seal_path, str(launch_receipt["launcher_repository_commit"]))
    except Exception as error:
        raise TerminalValidationError(f"exact sealed producer/runtime identity failed: {error}") from error
    if seal.get("case_id") != CASE_ID or seal.get("authorization_capability") != AUTHORIZATION_CAPABILITY \
            or seal.get("resume_allowed") is not False or seal.get("follow_on_authorized") is not False \
            or launch_receipt.get("seal_sha256") != seal_sha256 or launch_receipt.get("run_root") != str(run_root):
        raise TerminalValidationError("canonical seal, nonce credential, and run-root binding differ")
    if not isinstance(runtime_identity, dict) or not isinstance(seal_identity, dict) \
            or launch_receipt.get("source_commit") != runtime_identity.get("source_commit") \
            or launch_receipt.get("launcher_repository_commit") != seal_identity.get("repository_commit") \
            or launch_receipt.get("runtime_lock_sha256") != runtime_identity.get("runtime_lock_sha256"):
        raise TerminalValidationError("launch source or runtime identity differs from the canonical seal")
    marker = _strict_json(launch.seal_consumption_marker(seal_sha256))
    expected_marker = {
        "schema_version": "toy_road_t3_rev_seal_consumption_v1", "case_id": CASE_ID,
        "composite_producer": "sealed_T3_base_plus_T3_rev_case_definition_extension",
        "authorization_capability": AUTHORIZATION_CAPABILITY, "seal_sha256": seal_sha256,
        "run_root": str(run_root), "resume_allowed": False, "new_authorization_required": True,
    }
    if marker != expected_marker:
        raise TerminalValidationError("global seal claim does not bind this terminal root")
    manifest = _strict_json(extension_root / "EXTENSION_SOURCE_MANIFEST.json")
    identity = seal.get("extension_identity")
    if not isinstance(identity, dict) or identity.get("extension_source_manifest_sha256") != _sha256(extension_root / "EXTENSION_SOURCE_MANIFEST.json") \
            or launch_receipt.get("extension_source_manifest_sha256") != _sha256(extension_root / "EXTENSION_SOURCE_MANIFEST.json"):
        raise TerminalValidationError("sealed composite extension identity differs")
    try:
        verified = verifier.verify_extension_diff(
            sealed_base_root, extension_root,
            expected_repo_commit=str(launch_receipt["launcher_repository_commit"]),
        )
    except Exception as error:
        raise TerminalValidationError(f"extension verification failed: {error}") from error
    if verified != identity.get("verification"):
        raise TerminalValidationError("extension verification no longer matches the sealed composite")
    protocol_hashes = {item.get("path"): item.get("sha256") for item in manifest.get("shadow_files", []) if isinstance(item, dict)}
    if no_pass_bootstrap:
        launch_receipt["extension_shadow_sha256"] = protocol_hashes
    generated_hash = protocol_hashes.get("toy_road_protocol.py")
    if not isinstance(generated_hash, str) or _sha256(extension_root / "toy_road_protocol.py") != generated_hash:
        raise TerminalValidationError("generated protocol is not the sealed extension byte identity")
    protocol = launch.load_protocol(extension_root / "toy_road_protocol.py", "t3_rev_terminal_protocol", generated_hash)
    try:
        protocol.validate_execution_input_lock(lock, CASE_ID)
        require_canonical_lock_bytes(protocol, lock_path, lock)
    except Exception as error:
        raise TerminalValidationError(f"authoritative execution lock validation failed: {error}") from error
    seal_builder = _load(Path(__file__).with_name("build_t3_rev_seal.py"), "t3_rev_terminal_seal")
    if not launch._exact_json_equal(runtime_identity, seal_builder.EXPECTED_EXECUTION):
        raise TerminalValidationError("sealed runtime/MATLAB/four-MEX identity is not the qualified exact mapping")
    try:
        seal_builder.require_seal_evidence(
            sealed_base_root.parents[1], extension_root, seal)
    except Exception as error:
        raise TerminalValidationError(
            f"sealed predecessor/physics closure failed: {error}") from error
    cases = _strict_json(extension_root / "CASE_PHYSICS_CONTRACTS.json")
    case_table = cases.get("cases")
    case_contract = case_table.get(CASE_ID) if isinstance(case_table, dict) else None
    if not isinstance(case_contract, dict) \
            or lock.get("source_commit") != runtime_identity.get("source_commit") \
            or lock.get("source_manifest_sha256") != runtime_identity.get("source_manifest_sha256") \
            or lock.get("runtime_lock_sha256") != runtime_identity.get("runtime_lock_sha256") \
            or lock.get("family_contract_sha256") != cases.get("family_contract_sha256") \
            or lock.get("case_physics_contract_sha256") != case_contract.get("case_physics_contract_sha256") \
            or launch_receipt.get("family_contract_sha256") != lock.get("family_contract_sha256") \
            or launch_receipt.get("case_physics_contract_sha256") != lock.get("case_physics_contract_sha256"):
        raise TerminalValidationError("seal, extension contracts, launch, and lock identities differ")
    expectations = lock.get("runtime_expectations")
    sealed_matlab = runtime_identity.get("matlab")
    if not isinstance(expectations, dict) or not isinstance(sealed_matlab, dict) \
            or not launch._exact_json_equal(expectations.get("binary_sha256"), runtime_identity.get("four_binary_sha256")) \
            or not isinstance(expectations.get("matlab"), dict) \
            or any(not launch._exact_json_equal(expectations["matlab"].get(field), sealed_matlab.get(field))
                   for field in sealed_matlab if field != "absolute_path_order"):
        raise TerminalValidationError("runtime measurement lock differs from the sealed MATLAB or four-MEX identity")
    if launch_receipt.get("execution_input_lock_sha256") != _sha256(lock_path) \
            or launch_receipt.get("launch_nonce") is None \
            or launch_receipt.get("thread_environment") != runtime_identity.get("thread_settings"):
        raise TerminalValidationError("launch nonce, lock, or sealed thread identity differs")
    writable_roots = lock.get("writable_roots")
    expected_roots = {
        "output": str(terminal_root),
        **{name: str(run_root / name) for name in ("work", "temp", "tmp", "pref", "cache")},
        "matlab_startup_pref": str(run_root / "pref.matlab-startup"),
    }
    runtime_overlay = run_root / ".toy-road-runtime-overlay"
    path_order = expectations.get("matlab", {}).get("absolute_path_order") \
        if isinstance(expectations, dict) else None
    path_binding_failures: list[str] = []
    if not isinstance(writable_roots, dict) or writable_roots != expected_roots:
        path_binding_failures.append("writable_roots")
    if launch_receipt.get("extension_root") != str(extension_root):
        path_binding_failures.append("extension_root")
    if launch_receipt.get("runtime_overlay_root") != str(runtime_overlay):
        path_binding_failures.append("runtime_overlay_root")
    if not isinstance(path_order, list) or len(path_order) != 8:
        path_binding_failures.append("absolute_path_order_schema")
    elif path_order[0] != str(runtime_overlay) or path_order[1] != str(sealed_base_root) \
            or path_order[2:] != sealed_matlab.get("absolute_path_order", [])[2:]:
        path_binding_failures.append("absolute_path_order")
    if path_binding_failures:
        raise TerminalValidationError(
            "terminal/run launch path binding differs: " + ", ".join(path_binding_failures)
        )
    assert isinstance(writable_roots, dict)
    preproducer_phases = {
        "bootstrap_before_runtime_measurement",
        "runtime_qualification_before_producer",
    }
    before_producer = terminal.get("failure_phase") in preproducer_phases
    writable_paths = {name: Path(value) for name, value in writable_roots.items()}
    if before_producer:
        stale_roots = sorted(name for name, path in writable_paths.items() if path.exists())
        if stale_roots:
            raise TerminalValidationError(
                "preproducer failure carries stale writable root reservations: "
                + ", ".join(stale_roots)
            )
    else:
        missing_roots = sorted(name for name, path in writable_paths.items() if not path.is_dir())
        if missing_roots:
            raise TerminalValidationError(
                "producer-entered terminal lacks reserved writable roots: "
                + ", ".join(missing_roots)
            )
        for name, path in writable_paths.items():
            try:
                launch.require_no_reparse_chain(path, f"writable root {name}")
            except Exception as error:
                raise TerminalValidationError(f"writable root identity failed: {error}") from error
    if not launch._exact_json_equal(launch_receipt.get("extension_shadow_sha256"), protocol_hashes) \
            or launch_receipt.get("bootstrap_helper_sha256") != launch.BOOTSTRAP_HELPER_SHA256:
        raise TerminalValidationError("launch shadow or bootstrap identity differs from the extension")
    try:
        launch.require_materialized_runtime_overlay(
            runtime_overlay, protocol_hashes, runtime_identity.get("four_binary_sha256")
        )
    except Exception as error:
        raise TerminalValidationError(f"materialized runtime overlay identity failed: {error}") from error
    authenticated: dict[str, object] | None = None
    phase_evidence: dict[str, object] | None = None
    if no_pass_bootstrap:
        phase_evidence = _validate_no_pass_bootstrap_evidence(
            run_root, receipts, terminal_root, credential_failure_path,
            timeout_observed, launch,
        )
    elif classification in {"PASS_CONFIRMED_FRACTURE_TRAJECTORY", "PASS_NO_CONFIRMED_FRACTURE_BY_C150"}:
        try:
            measurement = _strict_json(receipts / "T3_REV_RUNTIME_MEASUREMENT.json")
            protocol.validate_runtime_measurement(lock, measurement)
            authenticated, completed_artifacts = _authenticate_completed_package(
                protocol, terminal_root,
                allow_test_synthetic_mesh_bytes=test_launch_override,
            )
            _validate_completed_sealed_chain(
                completed_artifacts, authenticated,
                sealed_base_root=sealed_base_root, case_contract=case_contract,
                lock=lock, launch=launch, repo_root=sealed_base_root.parents[1],
                writable_roots=writable_roots,
            )
            protocol.recheck_authenticated_package(authenticated)
        except Exception as error:
            raise TerminalValidationError(f"authoritative terminal package validation failed: {error}") from error
        if authenticated.get("execution_input_lock_sha256") != launch_receipt.get("execution_input_lock_sha256"):
            raise TerminalValidationError("terminal package lock does not bind the launch credential")
        if authenticated.get("package_root") != str(terminal_root):
            raise TerminalValidationError("authenticated terminal package root differs from the locked output root")
    elif classification in {"FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE", "FAIL_NEWTON_NONCONVERGENCE"}:
        try:
            failure_terminal_fields = {
                "schema_version", "status", "case_id", "terminal_reason", "failure_phase",
                "cycle", "substep", "seal_sha256", "run_root", "launch_receipt_sha256",
                "runtime_measurement_sha256", "failure_package_manifest_sha256",
            }
            failure_package = run_root / "T3_REV_FAILURE_PACKAGE"
            if set(terminal) != failure_terminal_fields \
                    or terminal.get("schema_version") != "toy_road_t3_rev_terminal_failure_v1" \
                    or terminal.get("status") != classification \
                    or terminal.get("case_id") != CASE_ID \
                    or terminal.get("failure_phase") != "producer_after_pass_runtime_measurement" \
                    or terminal.get("seal_sha256") != seal_sha256 \
                    or terminal.get("run_root") != str(run_root) \
                    or terminal.get("launch_receipt_sha256") != _sha256(
                        receipts / "T3_REV_LAUNCH_RECEIPT.json") \
                    or terminal.get("runtime_measurement_sha256") != _sha256(
                        receipts / "T3_REV_RUNTIME_MEASUREMENT.json") \
                    or terminal.get("failure_package_manifest_sha256") != _sha256(
                        failure_package / "PACKAGE_MANIFEST.json"):
                raise TerminalValidationError("numerical terminal failure receipt is not exact or bound")
            measurement = _strict_json(receipts / "T3_REV_RUNTIME_MEASUREMENT.json")
            protocol.validate_runtime_measurement(lock, measurement)
            phase_evidence = _validate_failure_package(
                failure_package, terminal, classification, lock, protocol, run_root,
                launch_receipt, seal_sha256, _sha256(
                    extension_root / "EXTENSION_SOURCE_MANIFEST.json"), case_contract,
            )
        except Exception as error:
            raise TerminalValidationError(f"numerical failure package validation failed: {error}") from error
    elif classification == RECOVERY_CLASSIFICATION:
        try:
            measurement = _strict_json(receipts / "T3_REV_RUNTIME_MEASUREMENT.json")
            protocol.validate_runtime_measurement(lock, measurement)
            phase_evidence = authenticate_recovery_nontrajectory(run_root)
        except Exception as error:
            raise TerminalValidationError(
                f"pre-c1 recovery nonconvergence validation failed: {error}"
            ) from error
    else:
        phase_evidence = _validate_startup_or_runtime_failure(
            terminal, classification, receipts, launch_receipt, seal_sha256, run_root,
            lock, protocol,
        )
    if builder.inventory_tree(sealed_base_root) != base_before or builder.inventory_tree(extension_root) != extension_before:
        raise TerminalValidationError("sealed base or extension inventory changed during terminal validation")
    run_inventory_post = inventory_run_tree(run_root)
    if preserve_run and run_inventory_post != run_inventory_pre:
        raise TerminalValidationError("preserve-run inventory changed during terminal validation")
    adjudicator_commit, adjudicator_source_sha256 = _adjudicator_identity()
    result: dict[str, object] = {
        "schema_version": (
            "toy_road_t3_rev_nontrajectory_terminal_adjudication_v1"
            if classification == RECOVERY_CLASSIFICATION
            else "toy_road_t3_rev_terminal_adjudication_v1"
        ),
        "status": terminal_adjudication_status(classification),
        "case_id": CASE_ID,
        "classification": classification,
        "terminal_reason": terminal["terminal_reason"],
        "seal_sha256": seal_sha256,
        "launch_receipt_sha256": None if no_pass_bootstrap else _sha256(launch_path),
        "execution_input_lock_sha256": _sha256(lock_path),
        "runtime_measurement_sha256": _sha256(receipts / "T3_REV_RUNTIME_MEASUREMENT.json")
        if (receipts / "T3_REV_RUNTIME_MEASUREMENT.json").is_file() else None,
        "extension_source_manifest_sha256": _sha256(extension_root / "EXTENSION_SOURCE_MANIFEST.json"),
        "sealed_base_inventory": base_before,
        "sealed_extension_inventory": extension_before,
        "terminal_authentication": authenticated,
        "runtime_source_closure": runtime_source_closure,
        "phase_evidence": phase_evidence,
        "run_inventory_pre": run_inventory_pre if preserve_run else None,
        "run_inventory_post": run_inventory_post if preserve_run else None,
        "run_inventory_unchanged": run_inventory_post == run_inventory_pre,
        "preserve_run": preserve_run,
        "adjudicator_commit": adjudicator_commit,
        "adjudicator_source_sha256": adjudicator_source_sha256,
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    if _emit_adjudication:
        _write_create_once(destination, result)
    return result


def validate_terminal(
        terminal_root: Path, *, sealed_base_root: Path, extension_root: Path,
        seal_path: Path, run_root: Path | None = None, destination: Path | None = None,
        preserve_run: bool = False,
        expected_run_inventory: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Public terminal validation has no caller-selected protocol or evidence roots."""
    return _validate_terminal(
        terminal_root,
        sealed_base_root=sealed_base_root,
        extension_root=extension_root,
        seal_path=seal_path,
        run_root=run_root,
        destination=destination,
        preserve_run=preserve_run,
        expected_run_inventory=expected_run_inventory,
    )
