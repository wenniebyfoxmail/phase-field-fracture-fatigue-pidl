from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


FAILURE_STATUS = "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4"
FIXED_POINT_TOLERANCE = 1e-3
STAGGER_ITERATION_CAP = 1000


class FailurePackageError(RuntimeError):
    pass


def _sealed_producer_root() -> Path:
    return Path(__file__).resolve().parents[2] / "producer_handoffs" / "toy_road_p0_repeatability_20260803"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FailurePackageError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise FailurePackageError(f"nonfinite JSON value: {token}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FailurePackageError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise FailurePackageError(f"JSON root must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _one(paths: Iterable[Path], label: str) -> Path:
    values = list(paths)
    if len(values) != 1:
        raise FailurePackageError(f"expected exactly one {label}, found {len(values)}")
    return values[0]


def _trace_summary(path: Path) -> dict[str, Any]:
    with path.open("r", newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {
        "cycle",
        "substep_ordinal",
        "stagger_iteration",
        "displacement_residual",
        "projected_phase_kkt",
        "consecutive_stagger_delta",
        "primal_feasibility",
    }
    if not rows or not required.issubset(rows[0]):
        raise FailurePackageError("c5 trace columns are incomplete")
    if len(rows) != STAGGER_ITERATION_CAP:
        raise FailurePackageError("c5 trace must contain exactly 1000 stagger rows")
    for expected, row in enumerate(rows, start=1):
        if int(row["cycle"]) != 5 or int(row["substep_ordinal"]) != 4:
            raise FailurePackageError("c5 trace contains a row outside c5/s4")
        if int(row["stagger_iteration"]) != expected:
            raise FailurePackageError("c5 trace stagger ordinals are not 1..1000")
    deltas = [float(row["consecutive_stagger_delta"]) for row in rows]
    for value in deltas:
        if not math.isfinite(value):
            raise FailurePackageError("c5 trace contains nonfinite fixed-point deltas")
    final = rows[-1]
    return {
        "rows": len(rows),
        "minimum_consecutive_stagger_delta": min(deltas),
        "final_consecutive_stagger_delta": deltas[-1],
        "final_displacement_residual": float(final["displacement_residual"]),
        "final_projected_phase_kkt": float(final["projected_phase_kkt"]),
        "final_primal_feasibility": float(final["primal_feasibility"]),
    }


def _physical_projection_hash(snapshot: Path, state0: Path) -> str | None:
    try:
        import h5py
        import numpy as np

        module_path = _sealed_producer_root() / "toy_road_adjudication.py"
        spec = importlib.util.spec_from_file_location("toy_road_adjudication_for_t2", module_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with h5py.File(state0, "r") as handle:
            group = handle["state0"]
            initial_state = {
                "d_node": np.asarray(group["d_node"], dtype=np.float64).T,
                "alpha_bar_gp": np.asarray(group["alpha_bar_gp"], dtype=np.float64).T,
            }
        projection = module.build_physical_input_projection(snapshot.read_bytes(), initial_state)
        return module.physical_input_projection_sha256(projection)
    except Exception:
        return None


def _thread_settings_identity() -> tuple[dict[str, str], str]:
    producer_root = _sealed_producer_root()
    launcher = producer_root / "launch_toy_road_family_case.ps1"
    manifest_path = producer_root / "SOURCE_MANIFEST.json"
    manifest = _read_json(manifest_path)
    launcher_sha256 = _sha256(launcher)
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise FailurePackageError("sealed source manifest files are missing")
    expected = [entry.get("sha256") for entry in entries if isinstance(entry, dict) and entry.get("path") == launcher.name]
    if expected != [launcher_sha256]:
        raise FailurePackageError("thread-setting launcher does not match sealed source manifest")
    text = launcher.read_text(encoding="utf-8")
    required = {
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_DYNAMIC": "FALSE",
    }
    observed: dict[str, str] = {}
    for name, value in required.items():
        matches = re.findall(rf"^\s*{re.escape(name)}\s*=\s*'([^']+)'\s*$", text, flags=re.MULTILINE)
        if matches != [value]:
            raise FailurePackageError(f"sealed launcher thread setting is invalid: {name}")
        observed[name] = value
    return observed, launcher_sha256


def _selected_artifacts(run_root: Path) -> list[Path]:
    relative = [
        "launcher.pid",
        "T2_material_state.stdout.log",
        "T2_material_state.stderr.log",
        "output/INPUT_SNAPSHOT.json",
        "output/mesh_geometry.mat",
        "output/RUN_RESULT.json",
        "output/RUNTIME_RECEIPT.json",
        "output/state0_analysis.mat",
        "output/qualification/C5_STAGGER_TRACE.csv",
        "receipts/T2_EXECUTION_INPUT_LOCK.json",
        "receipts/T2_LAUNCH_RECEIPT.json",
        "receipts/T2_PREFLIGHT_LOCK.json",
        "receipts/T2_PREFLIGHT_RECEIPT.json",
    ]
    relative.extend(f"output/substeps/cycle_{cycle:04d}.mat" for cycle in range(1, 5))
    paths = [run_root / item for item in relative]
    paths.append(_one((run_root / "receipts").glob(".*.runtime-measurement.json"), "runtime measurement"))
    paths.append(_one((run_root / "receipts").glob(".*.T1_initial_defect.terminal-auth.json"), "T1 terminal authentication receipt"))
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FailurePackageError("required T2 artifacts are missing: " + ", ".join(missing))
    return sorted(paths, key=lambda path: path.relative_to(run_root).as_posix())


def _validate_failure(run_root: Path) -> tuple[dict[str, Any], dict[str, Any], list[Path]]:
    run_result = _read_json(run_root / "output" / "RUN_RESULT.json")
    expected = {
        "case_id": "T2_material_state",
        "complete": False,
        "status": "failed",
        "error_identifier": "toyRoadP0:StaggeredSolveFailed",
        "error_message": "Stagger convergence failed at cycle 5 substep 4.",
    }
    for field, value in expected.items():
        if run_result.get(field) != value:
            raise FailurePackageError(f"RUN_RESULT does not prove T2 c5/s4 failure: {field}")
    stderr = (run_root / "T2_material_state.stderr.log").read_text(encoding="utf-8")
    if expected["error_message"] not in stderr:
        raise FailurePackageError("stderr does not contain the terminal c5/s4 error")
    shards = sorted((run_root / "output" / "substeps").glob("cycle_*.mat"))
    if [path.name for path in shards] != [f"cycle_{cycle:04d}.mat" for cycle in range(1, 5)]:
        raise FailurePackageError("T2 must contain exactly the four completed cycle shards c1-c4")
    trace = _trace_summary(run_root / "output" / "qualification" / "C5_STAGGER_TRACE.csv")
    return run_result, trace, _selected_artifacts(run_root)


def _identities(run_root: Path) -> dict[str, Any]:
    lock_path = run_root / "receipts" / "T2_EXECUTION_INPUT_LOCK.json"
    lock = _read_json(lock_path)
    snapshot_path = run_root / "output" / "INPUT_SNAPSHOT.json"
    snapshot = _read_json(snapshot_path)
    auth_path = _one((run_root / "receipts").glob(".*.T1_initial_defect.terminal-auth.json"), "T1 terminal authentication receipt")
    auth = _read_json(auth_path)
    expectations = lock.get("runtime_expectations")
    if not isinstance(expectations, dict):
        raise FailurePackageError("execution lock runtime expectations are missing")
    matlab = expectations.get("matlab")
    binaries = expectations.get("binary_sha256")
    if not isinstance(matlab, dict) or not isinstance(binaries, dict):
        raise FailurePackageError("execution lock MATLAB/MEX identities are missing")
    thread_settings, thread_settings_source_sha256 = _thread_settings_identity()
    return {
        "schema_version": "toy_road_t2_failure_identity_v1",
        "producer": {
            "source_commit": lock.get("source_commit"),
            "source_manifest_sha256": lock.get("source_manifest_sha256"),
            "family_contract_sha256": lock.get("family_contract_sha256"),
            "case_physics_contract_sha256": lock.get("case_physics_contract_sha256"),
        },
        "runtime": {
            "runtime_lock_sha256": lock.get("runtime_lock_sha256"),
            "matlab": matlab,
            "binary_sha256": binaries,
            "thread_settings": thread_settings,
            "thread_settings_source": "launch_toy_road_family_case.ps1",
            "thread_settings_source_sha256": thread_settings_source_sha256,
        },
        "input": {
            "execution_input_lock_sha256": _sha256(lock_path),
            "input_snapshot_sha256": _sha256(snapshot_path),
            "physical_input_projection_sha256": _physical_projection_hash(snapshot_path, run_root / "output" / "state0_analysis.mat"),
            "mesh_sha256": snapshot.get("mesh_sha256"),
            "material_Gc": ((snapshot.get("case_physics") or {}).get("material") or {}).get("Gc"),
        },
        "predecessor": {
            "case_id": "T1_initial_defect",
            "terminal_manifest_sha256": auth.get("manifest_sha256"),
            "package_snapshot_sha256": auth.get("package_snapshot_sha256"),
            "c5_receipt_sha256": auth.get("c5_receipt_sha256"),
            "terminal_auth_receipt_sha256": _sha256(auth_path),
        },
    }


def build_t2_failure_package(
    run_root: Path | str,
    destination: Path | str,
    *,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    run_root = Path(run_root).resolve()
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f"failure package destination already exists: {destination}")
    if not run_root.is_dir():
        raise FailurePackageError(f"T2 run root is missing: {run_root}")
    _, trace, selected = _validate_failure(run_root)
    identities = _identities(run_root)
    generated = generated_at_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    temp_root = Path(tempfile.mkdtemp(prefix=destination.name + ".tmp-", dir=destination.parent))
    try:
        artifacts: list[dict[str, Any]] = []
        for source in selected:
            relative = source.relative_to(run_root)
            target = temp_root / "artifacts" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            before = _sha256(source)
            shutil.copy2(source, target)
            after = _sha256(target)
            if before != after:
                raise FailurePackageError(f"copy hash mismatch: {relative.as_posix()}")
            artifacts.append({"path": f"artifacts/{relative.as_posix()}", "bytes": target.stat().st_size, "sha256": after})
        manifest = {
            "schema_version": "toy_road_t2_immutable_failure_package_v1",
            "case_id": "T2_material_state",
            "status": FAILURE_STATUS,
            "generated_at_utc": generated,
            "source_run_root": str(run_root),
            "artifact_file_count": len(artifacts),
            "artifact_aggregate_sha256": hashlib.sha256(_canonical_bytes(artifacts)).hexdigest(),
            "artifacts": artifacts,
            "excluded_predecessor_tree": "evidence/T1_initial_defect",
            "excluded_predecessor_reason": "bound by authenticated terminal/package hashes; bytes are not duplicated",
        }
        classification = {
            "schema_version": "toy_road_t2_failure_classification_v1",
            "case_id": "T2_material_state",
            "status": FAILURE_STATUS,
            "failure_cycle": 5,
            "failure_substep": 4,
            "failure_layer": "coupled_damage_fixed_point",
            "newton_failure": False,
            "fixed_point_tolerance": FIXED_POINT_TOLERANCE,
            "stagger_iteration_cap": STAGGER_ITERATION_CAP,
            "completed_cycle_shards": 4,
            "c5_trace_rows": trace["rows"],
            "minimum_consecutive_stagger_delta": trace["minimum_consecutive_stagger_delta"],
            "final_consecutive_stagger_delta": trace["final_consecutive_stagger_delta"],
            "final_displacement_residual": trace["final_displacement_residual"],
            "final_projected_phase_kkt": trace["final_projected_phase_kkt"],
            "final_primal_feasibility": trace["final_primal_feasibility"],
            "monitor_energy_role": "auxiliary_not_fatigue_consistent_objective",
            "automatic_retry_performed": False,
            "serial_chain_t3_status": "PAUSED",
        }
        _write_json(temp_root / "PACKAGE_MANIFEST.json", manifest)
        _write_json(temp_root / "FAILURE_CLASSIFICATION.json", classification)
        _write_json(temp_root / "SOURCE_RUNTIME_INPUT_IDENTITIES.json", identities)
        (temp_root / "decision.md").write_text(
            "# T2 material-state decision\n\n"
            f"Status: `{FAILURE_STATUS}`.\n\n"
            "The original T2 run is sealed as a valid negative result. At c5/s4 all 1000 stagger iterations were exhausted while the external consecutive-damage fixed-point gate remained above `1e-3`. This is not classified as a Newton failure. The 1000 cap and all gate thresholds remain unchanged.\n\n"
            "The monitored elastic plus ordinary fracture energy is auxiliary and does not establish convergence of the fatigue/history-dependent objective. The original serial-chain T3 remains paused. This receipt carries no production authorization.\n",
            encoding="utf-8",
            newline="\n",
        )
        inventory_paths = sorted(path for path in temp_root.rglob("*") if path.is_file())
        lines = [f"{_sha256(path)}  {path.relative_to(temp_root).as_posix()}" for path in inventory_paths]
        (temp_root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
        temp_root.rename(destination)
        return manifest
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Seal the original T2 c5/s4 failure package")
    parser.add_argument("run_root", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    manifest = build_t2_failure_package(args.run_root, args.destination)
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
