"""Focused synthetic contracts for the E042 read-only three-trajectory analyzer."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


WORKTREE = Path(__file__).resolve().parents[1]
ANALYZER_PATH = WORKTREE / "scripts" / "analyze_s04_e042_projected_damage.py"
spec = importlib.util.spec_from_file_location("e042_analysis", ANALYZER_PATH)
assert spec is not None and spec.loader is not None
analysis = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = analysis
spec.loader.exec_module(analysis)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: object, *, seal: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if seal:
        path.chmod(0o444)


def phase(step: int) -> dict[str, object]:
    _, cycle, substep, load = analysis.expected_phase(step)
    return {"step": step, "cycle": cycle, "substep": substep, "load": load}


def mesh(root: Path) -> None:
    np.savez(
        root / "mesh.npz",
        xy=np.asarray(((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)), dtype=np.float32),
        triangles=np.asarray(((0, 1, 2),), dtype=np.int64),
        area=np.asarray((0.5,), dtype=np.float32),
        node_weights=np.asarray((1.0 / 6.0,) * 3, dtype=np.float32),
    )


def fields(folder: Path, step: int, *, offset: float, previous: dict[str, np.ndarray] | None) -> dict[str, np.ndarray]:
    folder.mkdir(parents=True, exist_ok=True)
    d = np.asarray((0.1 + offset + step * 0.001, 0.2 + offset, 0.3 + offset), dtype=np.float32)
    trial_a = np.asarray((0.4 + offset + step * 0.01,), dtype=np.float32)
    driver = np.asarray((0.5 + offset + step * 0.01,), dtype=np.float32)
    result = {
        "d": d,
        "history_d": np.zeros_like(d) if previous is None else previous["d"],
        "history_A": np.zeros_like(trial_a) if previous is None else previous["trial_A"],
        "history_prev": np.zeros_like(driver) if previous is None else previous["active_driver"],
        "strain_xx": np.asarray((1.0 + offset + step * 0.01,), dtype=np.float32),
        "strain_yy": np.asarray((0.1 + offset,), dtype=np.float32),
        "strain_xy": np.asarray((0.05,), dtype=np.float32),
        "raw_psi": np.asarray((2.0 + offset + step * 0.02,), dtype=np.float32),
        "active_driver": driver,
        "trial_A": trial_a,
    }
    np.savez(folder / "fields.npz", **result)
    return result


def manifest(folder: Path, *, experiment: str, source: str, arm: str, mesh_hash: str, route_hash: str) -> None:
    write_json(
        folder / "manifest.json",
        {
            "experiment": experiment,
            "protocol": "r1",
            "source_commit": source,
            "baseline": "synthetic U0.12 current_active fem_gp_tri3_g_mean",
            "arm": arm,
            "steps": list(range(1, 16)),
            "factors": list(analysis.LOAD_FACTORS),
            "mesh_order_hash": mesh_hash,
            "field_route_hash": route_hash,
            "irreversibility_in_backward_graph": False,
            "damage_carrier": "d=h+(base(q)-base_reference).detach()+eta; eta projected to h<=d<=1",
        },
    )


def artifact_manifest(folder: Path, schema: str, names: list[str]) -> tuple[str, str]:
    entries = [{"name": name, "bytes": (folder / name).stat().st_size, "sha256": sha(folder / name)} for name in names]
    path = folder / "artifact_manifest.json"
    write_json(path, {"schema": schema, "artifacts": entries})
    return path.name, sha(path)


def pointer_arm(
    result_root: Path,
    *,
    arm: str,
    pointer_schema: str,
    index_schema: str,
    artifact_schema: str,
    route_hash: str,
    offset: float,
    carrier: str | None,
    count: int = 15,
) -> list[dict[str, object]]:
    arm_root = result_root / arm
    records_dir = arm_root / "accepted_states"
    indices_dir = arm_root / "state_indices"
    records_dir.mkdir(parents=True)
    indices_dir.mkdir()
    mesh_hash = "synthetic-mesh-order"

    initial_record = records_dir / "state_000.pt"
    initial_record.write_bytes(b"state_000")
    initial_evidence = arm_root / "initial_state"
    initial_evidence.mkdir()
    write_json(initial_evidence / "initial_state_audit.json", {"ok": True})
    initial_manifest_name, initial_manifest_sha = artifact_manifest(initial_evidence, artifact_schema, ["initial_state_audit.json"])
    initial_index = indices_dir / "state_000.json"
    write_json(
        initial_index,
        {
            "schema": index_schema,
            "state_commit_id": "state_000",
            "parent_state_commit_id": None,
            "parent_index_file": None,
            "parent_index_sha256": None,
            "record_file": initial_record.name,
            "record_sha256": sha(initial_record),
            "evidence_dir": initial_evidence.name,
            "artifact_manifest_file": initial_manifest_name,
            "artifact_manifest_sha256": initial_manifest_sha,
            "mesh_order_hash": mesh_hash,
            "field_route_hash": route_hash,
            "phase": None,
        },
    )
    prior_state, prior_index = "state_000", initial_index
    previous_fields: dict[str, np.ndarray] | None = None
    globals_: list[dict[str, object]] = []
    for step in range(1, count + 1):
        state = f"state_{step:03d}"
        record_path = records_dir / f"{state}.pt"
        record_path.write_bytes(state.encode())
        step_dir = arm_root / f"step_{step:03d}"
        previous_fields = fields(step_dir, step, offset=offset, previous=previous_fields)
        receipt: dict[str, object] = {
            "arm": arm,
            **phase(step),
            "accepted": None,
            "candidate_commit_id": state,
            "accepted_commit_id_before": prior_state,
            "stop_reason": "standard_early_stop",
        }
        if carrier is not None:
            receipt["damage_carrier"] = carrier
        write_json(step_dir / "receipt.json", receipt)
        manifest_name, manifest_sha = artifact_manifest(step_dir, artifact_schema, ["fields.npz", "receipt.json"])
        index_path = indices_dir / f"{state}.json"
        write_json(
            index_path,
            {
                "schema": index_schema,
                "state_commit_id": state,
                "parent_state_commit_id": prior_state,
                "parent_index_file": prior_index.name,
                "parent_index_sha256": sha(prior_index),
                "record_file": record_path.name,
                "record_sha256": sha(record_path),
                "evidence_dir": step_dir.name,
                "artifact_manifest_file": manifest_name,
                "artifact_manifest_sha256": manifest_sha,
                "mesh_order_hash": mesh_hash,
                "field_route_hash": route_hash,
                "phase": phase(step),
            },
        )
        global_record = dict(receipt)
        global_record.update(
            accepted=True,
            accepted_commit_id_after=state,
            acceptance_status="committed_by_pointer",
            step_elapsed_seconds=1.0 + step,
            updates=100 + step,
            theta_rprop_updates=100 + step,
            eta_accepted_updates=step,
            uv_reequilibration_rprop_updates=10,
        )
        globals_.append(global_record)
        prior_state, prior_index = state, index_path
    write_json(arm_root / "steps.json", globals_)
    write_json(
        arm_root / "accepted_state_pointer.json",
        {
            "schema": pointer_schema,
            "accepted_commit_id": prior_state,
            "parent_commit_id": f"state_{count - 1:03d}" if count else None,
            "parent_index_file": f"state_{count - 1:03d}.json" if count else None,
            "record_file": f"state_{count:03d}.pt" if count else "state_000.pt",
            "record_sha256": sha(records_dir / (f"state_{count:03d}.pt" if count else "state_000.pt")),
            "state_index_file": prior_index.name,
            "state_index_sha256": sha(prior_index),
            "mesh_order_hash": mesh_hash,
            "field_route_hash": route_hash,
        },
    )
    return globals_


def build_r001(root: Path) -> Path:
    root.mkdir()
    mesh(root)
    manifest_payload = {
        "experiment": "S04-E037",
        "protocol": "r1",
        "source_commit": "synthetic-r001-source",
        "baseline": "synthetic U0.12 current_active fem_gp_tri3_g_mean",
        "steps": list(range(1, 16)),
        "factors": list(analysis.LOAD_FACTORS),
        "arms": ["original", "primal_dual"],
        "history": "synthetic continuous accepted-only history frozen during physical step",
    }
    write_json(root / "manifest.json", manifest_payload)
    original = root / "original"
    previous: dict[str, np.ndarray] | None = None
    records: list[dict[str, object]] = []
    for step in range(1, 16):
        step_dir = original / f"step_{step:03d}"
        previous = fields(step_dir, step, offset=0.0, previous=previous)
        record = {"arm": "original", **phase(step), "accepted": True, "step_elapsed_seconds": 1.0 + step, "updates": 50 + step}
        write_json(step_dir / "receipt.json", record)
        records.append(record)
    write_json(original / "steps.json", records)
    identity_files = []
    for relative in ["manifest.json", "mesh.npz", "original/steps.json"]:
        path = root / relative
        identity_files.append({"path": relative, "sha256": sha(path), "bytes": path.stat().st_size})
    for step in range(1, 16):
        for name in ("receipt.json", "fields.npz"):
            relative = f"original/step_{step:03d}/{name}"
            path = root / relative
            identity_files.append({"path": relative, "sha256": sha(path), "bytes": path.stat().st_size})
    identity = root / "r001_identity.json"
    write_json(
        identity,
        {"schema": analysis.R001_IDENTITY_SCHEMA, "reference": {key: manifest_payload[key] for key in ("experiment", "protocol", "source_commit", "history")}, "files": identity_files},
    )
    return identity


def build_e040(archive: Path, r001_root: Path) -> Path:
    archive.mkdir()
    result = archive / "results"
    result.mkdir()
    mesh(result)
    contract = {
        "schema": analysis.E040_CONTRACT_SCHEMA,
        "run_id": "pf_s04e040_feasible_damage_synthetic_20261025T203658Z",
        "result": {"experiment": "S04-E040", "protocol": "r1", "arm": "feasible_damage"},
        "package": {
            "preflight_schema": "S04-E040-producer-preflight-v2",
            "schema": "S04-E040-producer-package-receipt-v2",
            "package_commit": "2" * 40,
            "reviewed_runtime_commit": "5" * 40,
            "runtime_manifest_schema": "S04-E040-reviewed-runtime-manifest-v1",
        },
        "baseline": {"model_settings_sha256": "a" * 64, "checkpoint_sha256": "b" * 64, "network_sha256": "c" * 64},
        "r001": {"steps_sha256": sha(r001_root / "original" / "steps.json")},
    }
    contract_path = archive / "e040_contract.json"
    write_json(contract_path, contract)
    manifest(result, experiment="S04-E040", source=contract["package"]["reviewed_runtime_commit"], arm="feasible_damage", mesh_hash="synthetic-mesh-order", route_hash=analysis.EXPECTED_E040_ROUTE_HASH)
    pointer_arm(result, arm="feasible_damage", pointer_schema=analysis.E040_POINTER_SCHEMA, index_schema=analysis.E040_INDEX_SCHEMA, artifact_schema=analysis.E040_MANIFEST_SCHEMA, route_hash=analysis.EXPECTED_E040_ROUTE_HASH, offset=0.1, carrier=None)
    runtime = archive / "reviewed_runtime_manifest.json"
    write_json(runtime, {"schema": contract["package"]["runtime_manifest_schema"], "reviewed_runtime_commit": contract["package"]["reviewed_runtime_commit"]})
    package = archive / "package_receipt.json"
    write_json(package, {"schema": contract["package"]["schema"], "package_commit": contract["package"]["package_commit"], "reviewed_runtime_commit": contract["package"]["reviewed_runtime_commit"], "runtime_manifest_file": runtime.name, "runtime_manifest_sha256": sha(runtime)})
    preflight = {
        "schema": contract["package"]["preflight_schema"],
        "run_id": contract["run_id"],
        "reviewed_runtime_commit": contract["package"]["reviewed_runtime_commit"],
        "package_receipt_sha256": sha(package),
        "r001_steps_sha256": contract["r001"]["steps_sha256"],
        **contract["baseline"],
    }
    (archive / "producer_preflight.txt").write_text("".join(f"{key}={value}\n" for key, value in preflight.items()))
    return contract_path


def build_e042(archive: Path, r001_root: Path) -> Path:
    archive.mkdir()
    result = archive / "results"
    result.mkdir()
    mesh(result)
    runtime_commit = "6" * 40
    package_commit = "7" * 40
    manifest(result, experiment="S04-E042", source=runtime_commit, arm="projected_damage", mesh_hash="synthetic-mesh-order", route_hash=analysis.EXPECTED_E042_ROUTE_HASH)
    records = pointer_arm(result, arm="projected_damage", pointer_schema=analysis.E042_POINTER_SCHEMA, index_schema=analysis.E042_INDEX_SCHEMA, artifact_schema=analysis.E042_MANIFEST_SCHEMA, route_hash=analysis.EXPECTED_E042_ROUTE_HASH, offset=0.2, carrier="reference_base_eta_projected_v1")
    candidate_summary = {
        "arm": "projected_damage",
        "outcome": "completed_all_15_accepted_steps",
        "steps_attempted": 15,
        "steps_accepted": 15,
        "completed_three_cycles": True,
        "final_accepted_commit_id": "state_015",
    }
    write_json(result / "projected_damage" / "summary.json", candidate_summary)
    write_json(result / "results.json", [candidate_summary])
    write_json(
        result / "completed.json",
        {"execution": "runner_finished", "outcome": candidate_summary["outcome"], "results": [candidate_summary]},
    )

    runtime = archive / "reviewed_runtime_manifest.json"
    proof = {"module": "projected_damage", "symbol": "ReferenceBaseProjectedDamage", "module_path": "source/projected_damage.py", "runner_path": "scripts/run_s04_e042_projected_damage.py", "module_sha256": "d" * 64}
    write_json(runtime, {"schema": "S04-E042-reviewed-runtime-manifest-v2", "reviewed_runtime_commit": runtime_commit, "files": [{"path": proof["module_path"], "sha256": proof["module_sha256"]}, {"path": proof["runner_path"], "sha256": "e" * 64}], "e042_import_proof": proof})
    package = archive / "package_receipt.json"
    write_json(package, {"schema": "S04-E042-producer-package-receipt-v2", "package_commit": package_commit, "reviewed_runtime_commit": runtime_commit, "runtime_manifest_file": runtime.name, "runtime_manifest_sha256": sha(runtime)})
    materialization = archive / "materialization_receipt.json"
    write_json(materialization, {"package_receipt_sha256": sha(package), "archive_sha256": None, "runtime_manifest_sha256": sha(runtime), "package_commit": package_commit})
    preflight = archive / "producer_preflight.txt"
    frozen = {"model_settings_sha256": "a" * 64, "checkpoint_sha256": "b" * 64, "network_sha256": "c" * 64, "r001_steps_sha256": sha(r001_root / "original" / "steps.json")}
    preflight_values = {"schema": "S04-E042-producer-preflight-v2", "run_id": "pf_s04e042_projected_damage_synthetic_20261025T203658Z", "reviewed_runtime_commit": runtime_commit, "package_receipt_sha256": sha(package), "runtime_manifest_sha256": sha(runtime), **frozen}
    preflight.write_text("".join(f"{key}={value}\n" for key, value in preflight_values.items()))
    identity = archive / "analysis_identity_receipt.json"
    write_json(identity, {"schema": analysis.E042_IDENTITY_SCHEMA, "run_id": preflight_values["run_id"], "sealed": {"mode": "create_once_0444", "archive_root_file": identity.name}, "runtime": {"reviewed_runtime_commit": runtime_commit, "package_commit": package_commit, "package_receipt_sha256": sha(package), "runtime_manifest_sha256": sha(runtime), "materialization_receipt_sha256": sha(materialization), "runner_path": proof["runner_path"], "runner_sha256": "e" * 64, "e042_import_proof": proof}, "preflight": {"file": preflight.name, "sha256": sha(preflight), "schema": "S04-E042-producer-preflight-v2"}, "frozen_inputs": frozen, "history_timing": {"history_driver_mode": "current_active", "lagged_stiffness_enabled": False, "transaction_boundary": "accepted_only", "transactions_per_physical_step": 1, "commit_mechanism": "pointer_last_after_accepted_candidate_bundle"}, "result_linkage": {"state": "pre_run_identity_only", "completion_receipt": "analysis_result_linkage_receipt.json", "completion_condition": "written only after runner exit code 0 and result-file hash checks"}}, seal=True)
    result_files = {}
    for relative in (
        "manifest.json",
        "mesh.npz",
        "projected_damage/accepted_state_pointer.json",
        "projected_damage/steps.json",
        "projected_damage/summary.json",
        "results.json",
        "completed.json",
    ):
        path = result / relative
        result_files[relative] = {"sha256": sha(path), "bytes": path.stat().st_size}
    linkage = archive / "analysis_result_linkage_receipt.json"
    write_json(linkage, {"schema": analysis.E042_RESULT_LINKAGE_SCHEMA, "run_id": preflight_values["run_id"], "sealed": {"mode": "create_once_0444", "archive_root_file": linkage.name}, "pre_run_identity_receipt_sha256": sha(identity), "producer_preflight_sha256": sha(preflight), "runner_exit_code": 0, "result_files": result_files, "result_summary": {"outcome": candidate_summary["outcome"], "steps_attempted": 15, "steps_accepted": 15, "completed_three_cycles": True, "completed_outcome": candidate_summary["outcome"]}}, seal=True)
    return result


class AnalyzeProjectedDamageTest(unittest.TestCase):
    def build_inputs(self, temporary: Path) -> tuple[Path, Path, Path, Path, Path]:
        r001 = temporary / "r001"
        r001_identity = build_r001(r001)
        e040 = temporary / "e040"
        e040_contract = build_e040(e040, r001)
        e042 = temporary / "e042"
        build_e042(e042, r001)
        return r001, r001_identity, e040, e040_contract, e042

    def test_three_way_comparison_requires_and_reports_identity_checked_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            r001, r001_identity, e040, e040_contract, e042 = self.build_inputs(root)
            output = root / "analysis"
            summary = analysis.analyze(r001, e040, e042, output, r001_identity_path=r001_identity, e040_contract_path=e040_contract)
            self.assertEqual(summary["common_accepted_prefix_steps"], 15)
            self.assertTrue(summary["candidate_completed_fixed_horizon"])
            self.assertIn("No physical success", summary["scientific_boundary"])
            rows = (output / "paired_fields.csv").read_text().splitlines()
            self.assertEqual(len(rows), 1 + 15 * 4 * 2)
            timing = json.loads((output / "timing_summary.json").read_text())
            self.assertTrue(timing["full_horizon_timing_comparable"])
            self.assertFalse(timing["performance_claim_supported"])
            provenance = json.loads((output / "input_provenance.json").read_text())
            self.assertEqual(provenance["e042"]["history_timing"]["history_driver_mode"], "current_active")

    def test_result_linkage_hash_mismatch_fails_before_any_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            r001, r001_identity, e040, e040_contract, e042 = self.build_inputs(root)
            mesh_path = e042 / "results" / "mesh.npz"
            mesh_path.chmod(stat.S_IWUSR | stat.S_IRUSR)
            with mesh_path.open("ab") as handle:
                handle.write(b"tampered")
            output = root / "analysis"
            with self.assertRaisesRegex(analysis.InputContractError, "result (byte count|.*SHA-256 mismatch)"):
                analysis.analyze(r001, e040, e042, output, r001_identity_path=r001_identity, e040_contract_path=e040_contract)
            self.assertFalse(output.exists())

    def test_linkage_anchors_pointer_head_before_any_field_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            r001, r001_identity, e040, e040_contract, e042 = self.build_inputs(root)
            pointer_path = e042 / "results" / "projected_damage" / "accepted_state_pointer.json"
            pointer = json.loads(pointer_path.read_text())
            pointer["parent_commit_id"] = "tampered-parent"
            write_json(pointer_path, pointer)
            output = root / "analysis"
            with self.assertRaisesRegex(analysis.InputContractError, "accepted_state_pointer.*result (byte count|.*SHA-256 mismatch)"):
                analysis.analyze(r001, e040, e042, output, r001_identity_path=r001_identity, e040_contract_path=e040_contract)
            self.assertFalse(output.exists())

    def test_missing_pre_run_identity_receipt_fails_closed_before_any_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            r001, r001_identity, e040, e040_contract, e042 = self.build_inputs(root)
            identity_path = e042 / "analysis_identity_receipt.json"
            identity_path.chmod(0o600)
            identity_path.unlink()
            output = root / "analysis"
            with self.assertRaisesRegex(analysis.InputContractError, "analysis_identity_receipt.json"):
                analysis.analyze(r001, e040, e042, output, r001_identity_path=r001_identity, e040_contract_path=e040_contract)
            self.assertFalse(output.exists())

    def test_history_handoff_mismatch_fails_even_when_result_linkage_is_rebound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            r001, r001_identity, e040, e040_contract, e042 = self.build_inputs(root)
            step_path = e042 / "results" / "projected_damage" / "step_002" / "fields.npz"
            with np.load(step_path, allow_pickle=False) as archive:
                altered = {name: archive[name] for name in archive.files}
            altered["history_d"] = altered["history_d"] + 0.01
            np.savez(step_path, **altered)
            # Rebind the pointer evidence and the post-run linkage exactly as a
            # hostile but self-consistent archive would; continuity must still
            # reject it.
            step_dir = step_path.parent
            receipt = step_dir / "receipt.json"
            artifact_manifest(step_dir, analysis.E042_MANIFEST_SCHEMA, ["fields.npz", "receipt.json"])
            index_path = e042 / "results" / "projected_damage" / "state_indices" / "state_002.json"
            index = json.loads(index_path.read_text())
            index["artifact_manifest_sha256"] = sha(step_dir / "artifact_manifest.json")
            write_json(index_path, index)
            # Rebuild every descendant parent hash and the pointer head.
            indices = e042 / "results" / "projected_damage" / "state_indices"
            for step in range(3, 16):
                current = indices / f"state_{step:03d}.json"
                payload = json.loads(current.read_text())
                payload["parent_index_sha256"] = sha(indices / f"state_{step - 1:03d}.json")
                write_json(current, payload)
            pointer_path = e042 / "results" / "projected_damage" / "accepted_state_pointer.json"
            pointer = json.loads(pointer_path.read_text())
            pointer["state_index_sha256"] = sha(indices / "state_015.json")
            write_json(pointer_path, pointer)
            linkage_path = e042 / "analysis_result_linkage_receipt.json"
            linkage_path.chmod(0o600)
            linkage = json.loads(linkage_path.read_text())
            for relative, entry in linkage["result_files"].items():
                path = e042 / "results" / relative
                entry["sha256"] = sha(path)
                entry["bytes"] = path.stat().st_size
            write_json(linkage_path, linkage, seal=True)
            output = root / "analysis"
            with self.assertRaisesRegex(analysis.InputContractError, "history handoff"):
                analysis.analyze(r001, e040, e042, output, r001_identity_path=r001_identity, e040_contract_path=e040_contract)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
