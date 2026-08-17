from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "analysis" / "toy_road_t2_failure_20260817" / "build_t2_failure_package.py"


def _load_module():
    assert MODULE_PATH.is_file(), "T2 failure-package builder must exist"
    spec = importlib.util.spec_from_file_location("t2_failure_package", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_run(root: Path) -> Path:
    output, receipts = root / "output", root / "receipts"
    (output / "substeps").mkdir(parents=True)
    (output / "qualification").mkdir(parents=True)
    receipts.mkdir(parents=True)
    lock = {
        "authorization_scope": "production_authorized", "case_id": "T2_material_state",
        "case_physics_contract_sha256": "a" * 64, "family_contract_sha256": "b" * 64,
        "runtime_lock_sha256": "c" * 64, "source_commit": "d" * 40,
        "source_manifest_sha256": "e" * 64,
        "runtime_expectations": {
            "matlab": {"release": "R2025b", "update": "Update 5", "version": "25.2", "computer": "PCWIN64", "executable_sha256": "1" * 64, "blas": "blas", "lapack": "lapack"},
            "binary_sha256": {"initial": "2" * 64, "AMOR": "3" * 64, "AT1_HISTORY_FATIGUE": "4" * 64, "cholmod2": "5" * 64},
        },
    }
    _write_json(receipts / "T2_EXECUTION_INPUT_LOCK.json", lock)
    _write_json(receipts / "T2_LAUNCH_RECEIPT.json", {"status": "PASS"})
    _write_json(receipts / "T2_PREFLIGHT_LOCK.json", lock)
    _write_json(receipts / "T2_PREFLIGHT_RECEIPT.json", {"status": "PASS"})
    _write_json(receipts / ".id.runtime-measurement.json", {"status": "PASS"})
    _write_json(receipts / ".id.T1_initial_defect.terminal-auth.json", {"schema_version": "toy_road_authenticated_terminal_v1", "status": "PASS", "manifest_sha256": "6" * 64, "package_snapshot_sha256": "7" * 64, "c5_receipt_sha256": "8" * 64, "execution_input_lock_sha256": "9" * 64, "runtime_lock_sha256": "c" * 64})
    _write_json(output / "RUN_RESULT.json", {"authorization_scope": "production_authorized", "case_id": "T2_material_state", "complete": False, "status": "failed", "error_identifier": "toyRoadP0:StaggeredSolveFailed", "error_message": "Stagger convergence failed at cycle 5 substep 4."})
    _write_json(output / "RUNTIME_RECEIPT.json", {"status": "PASS"})
    _write_json(output / "INPUT_SNAPSHOT.json", {"schema_version": "toy_road_p0_input_snapshot_v1", "case_id": "T2_material_state", "source_commit": "d" * 40, "runtime_lock_sha256": "c" * 64, "family_contract_sha256": "b" * 64, "case_physics_contract_sha256": "a" * 64, "execution_input_lock_sha256": "f" * 64, "mesh_sha256": "0" * 64, "case_physics": {"material": {"Gc": 0.008}}})
    for name in ("mesh_geometry.mat", "state0_analysis.mat"):
        (output / name).write_bytes(name.encode())
    for cycle in range(1, 5):
        (output / "substeps" / f"cycle_{cycle:04d}.mat").write_bytes(f"cycle {cycle}".encode())
    with (output / "qualification" / "C5_STAGGER_TRACE.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = ["cycle", "substep_ordinal", "stagger_iteration", "displacement_residual", "projected_phase_kkt", "consecutive_stagger_delta", "primal_feasibility"]
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for iteration in range(1, 1001):
            writer.writerow({"cycle": 5, "substep_ordinal": 4, "stagger_iteration": iteration, "displacement_residual": "3.1e-5", "projected_phase_kkt": "6.4e-6", "consecutive_stagger_delta": "0.017", "primal_feasibility": "0"})
    (root / "T2_material_state.stdout.log").write_text("cycle 5 substep 4 stagger 1000\n", encoding="utf-8")
    (root / "T2_material_state.stderr.log").write_text("Stagger convergence failed at cycle 5 substep 4.\n", encoding="utf-8")
    (root / "launcher.pid").write_text("123", encoding="ascii")
    (root / "evidence" / "T1_initial_defect").mkdir(parents=True)
    (root / "evidence" / "T1_initial_defect" / "huge.mat").write_bytes(b"excluded")
    return root


def test_builds_create_once_complete_failure_dossier(tmp_path: Path) -> None:
    module = _load_module()
    run, destination = _make_run(tmp_path / "run"), tmp_path / "dossier"
    result = module.build_t2_failure_package(run, destination, generated_at_utc="2026-08-17T12:00:00Z")
    classification = json.loads((destination / "FAILURE_CLASSIFICATION.json").read_text(encoding="utf-8"))
    assert classification["status"] == "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4"
    assert classification["newton_failure"] is False
    assert classification["fixed_point_tolerance"] == 1e-3
    assert classification["stagger_iteration_cap"] == 1000
    assert classification["completed_cycle_shards"] == 4
    assert classification["c5_trace_rows"] == 1000
    assert classification["serial_chain_t3_status"] == "PAUSED"
    assert classification["automatic_retry_performed"] is False
    identities = json.loads((destination / "SOURCE_RUNTIME_INPUT_IDENTITIES.json").read_text(encoding="utf-8"))
    assert identities["producer"]["source_commit"] == "d" * 40
    assert identities["runtime"]["binary_sha256"]["AT1_HISTORY_FATIGUE"] == "4" * 64
    assert len(identities["runtime"]["thread_settings_source_sha256"]) == 64
    assert identities["runtime"]["thread_settings"] == {
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1", "MKL_DYNAMIC": "FALSE",
    }
    assert identities["input"]["input_snapshot_sha256"] == _sha256(run / "output" / "INPUT_SNAPSHOT.json")
    assert identities["predecessor"]["terminal_manifest_sha256"] == "6" * 64
    assert (destination / "artifacts" / "output" / "substeps" / "cycle_0004.mat").is_file()
    assert not (destination / "artifacts" / "evidence").exists()
    assert result["artifact_file_count"] == len(result["artifacts"])
    sums = {}
    for line in (destination / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1); sums[relative] = digest
    for relative, digest in sums.items():
        assert _sha256(destination / relative) == digest
    assert "SHA256SUMS.txt" not in sums
    with pytest.raises(FileExistsError):
        module.build_t2_failure_package(run, destination)


def test_rejects_incomplete_failure_trace(tmp_path: Path) -> None:
    module = _load_module(); run = _make_run(tmp_path / "run")
    trace = run / "output" / "qualification" / "C5_STAGGER_TRACE.csv"
    rows = trace.read_text(encoding="utf-8").splitlines(); trace.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(module.FailurePackageError, match="1000"):
        module.build_t2_failure_package(run, tmp_path / "bad")
