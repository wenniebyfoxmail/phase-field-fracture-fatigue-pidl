"""Synthetic contract tests for the read-only E040 trajectory analyzer."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


WORKTREE = Path(__file__).resolve().parents[1]
ANALYZER = WORKTREE / "scripts" / "analyze_s04_e040_feasible_damage.py"
POINTER_SCHEMA = "S04-E040-accepted-state-pointer-v1"
INDEX_SCHEMA = "S04-E040-state-index-v1"
MANIFEST_SCHEMA = "S04-E040-artifact-manifest-v1"


def _json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mesh(root: Path, *, x_shift: float = 0.0) -> None:
    root.mkdir(parents=True, exist_ok=True)
    np.savez(
        root / "mesh.npz",
        xy=np.asarray(((0.0 + x_shift, 0.0), (1.0 + x_shift, 0.0), (0.0 + x_shift, 1.0)), dtype=np.float32),
        triangles=np.asarray(((0, 1, 2),), dtype=np.int64),
        area=np.asarray((0.5,), dtype=np.float32),
        node_weights=np.asarray((1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0), dtype=np.float32),
    )


def _record(step: int, *, accepted: bool, arm: str, load: float) -> dict[str, object]:
    return {
        "arm": arm,
        "step": step,
        "cycle": 1,
        "substep": step,
        "load": load,
        "accepted": accepted,
        "stop_reason": "standard_early_stop" if accepted else "wall_cap",
        "updates": 10 + step,
        "step_elapsed_seconds": 2.0 + step,
        "metrics": {
            "E_el": 1.0 + step,
            "E_d": 2.0 + step,
            "shadow_E_irr": 0.01 * step,
            "weighted_L2": 0.1,
            "E_noirr": 3.0 + 2.0 * step,
        },
    }


def _fields(step_dir: Path, *, candidate: bool) -> None:
    step_dir.mkdir(parents=True, exist_ok=True)
    offset = 0.1 if candidate else 0.0
    np.savez(
        step_dir / "fields.npz",
        d=np.asarray((0.1 + offset, 0.2 + offset, 0.3 + offset), dtype=np.float32),
        history_d=np.asarray((0.0 + offset, 0.1 + offset, 0.2 + offset), dtype=np.float32),
        strain_xx=np.asarray((1.0 + offset,), dtype=np.float32),
        strain_yy=np.asarray((0.0,), dtype=np.float32),
        strain_xy=np.asarray((0.0,), dtype=np.float32),
        raw_psi=np.asarray((2.0 + offset,), dtype=np.float32),
        trial_A=np.asarray((3.0 + offset,), dtype=np.float32),
        q_raw=np.asarray((0.1, 0.0, -0.1), dtype=np.float32),
        q_ref=np.asarray((0.0, 0.0, 0.0), dtype=np.float32),
    )


def _write_reference_arm(root: Path, records: list[dict[str, object]]) -> Path:
    arm_dir = root / "original"
    arm_dir.mkdir(parents=True, exist_ok=True)
    _json(arm_dir / "steps.json", records)
    for record in records:
        step = int(record["step"])
        step_dir = arm_dir / f"step_{step:03d}"
        step_dir.mkdir(parents=True, exist_ok=True)
        _json(step_dir / "receipt.json", record)
        _fields(step_dir, candidate=False)
    return arm_dir


def _write_manifest(folder: Path, names: list[str]) -> tuple[str, str]:
    entries = [
        {"name": name, "bytes": (folder / name).stat().st_size, "sha256": _sha256(folder / name)}
        for name in names
    ]
    manifest = folder / "artifact_manifest.json"
    _json(manifest, {"schema": MANIFEST_SCHEMA, "artifacts": entries})
    return manifest.name, _sha256(manifest)


def _write_state_record(records_dir: Path, state_id: str) -> tuple[str, str]:
    records_dir.mkdir(parents=True, exist_ok=True)
    path = records_dir / f"{state_id}.pt"
    path.write_bytes(f"synthetic {state_id}".encode())
    return path.name, _sha256(path)


def _write_state_index(
    indices_dir: Path,
    *,
    state_id: str,
    parent_state_id: str | None,
    parent_index_file: str | None,
    record_file: str,
    record_sha: str,
    evidence_dir: str,
    manifest_file: str,
    manifest_sha: str,
    phase: dict[str, object] | None,
) -> tuple[str, str]:
    indices_dir.mkdir(parents=True, exist_ok=True)
    path = indices_dir / f"{state_id}.json"
    _json(
        path,
        {
            "schema": INDEX_SCHEMA,
            "state_commit_id": state_id,
            "parent_state_commit_id": parent_state_id,
            "parent_index_file": parent_index_file,
            "record_file": record_file,
            "record_sha256": record_sha,
            "evidence_dir": evidence_dir,
            "artifact_manifest_file": manifest_file,
            "artifact_manifest_sha256": manifest_sha,
            "mesh_order_hash": "mesh-test",
            "field_route_hash": "route-test",
            "phase": phase,
        },
    )
    return path.name, _sha256(path)


def _write_e040_candidate(
    root: Path,
    accepted_records: list[dict[str, object]],
    *,
    terminal_records: list[dict[str, object]] | None = None,
    write_steps_json: bool = True,
) -> Path:
    """Write the E040 pointer/index/manifest contract without torch payloads."""
    arm_dir = root / "feasible_damage"
    arm_dir.mkdir(parents=True, exist_ok=True)
    records_dir = arm_dir / "accepted_states"
    indices_dir = arm_dir / "state_indices"

    initial_record_file, initial_record_sha = _write_state_record(records_dir, "state_000")
    initial_evidence = arm_dir / "initial_state"
    initial_evidence.mkdir()
    _json(initial_evidence / "initial_state_audit.json", {"synthetic": True})
    initial_manifest_file, initial_manifest_sha = _write_manifest(initial_evidence, ["initial_state_audit.json"])
    current_state = "state_000"
    current_index, current_index_sha = _write_state_index(
        indices_dir,
        state_id=current_state,
        parent_state_id=None,
        parent_index_file=None,
        record_file=initial_record_file,
        record_sha=initial_record_sha,
        evidence_dir="initial_state",
        manifest_file=initial_manifest_file,
        manifest_sha=initial_manifest_sha,
        phase=None,
    )
    current_record_file, current_record_sha = initial_record_file, initial_record_sha
    current_parent_state: str | None = None
    current_parent_index: str | None = None

    global_records: list[dict[str, object]] = []
    for expected_step, global_record in enumerate(accepted_records, start=1):
        step = int(global_record["step"])
        if step != expected_step or global_record["accepted"] is not True:
            raise AssertionError("synthetic E040 accepted records must be contiguous")
        state_id = f"state_{step:03d}"
        step_dir = arm_dir / f"step_{step:03d}"
        _fields(step_dir, candidate=True)
        artifact_receipt = dict(global_record)
        artifact_receipt.pop("step_elapsed_seconds", None)
        artifact_receipt.update(
            accepted=None,
            acceptance_status="prepared_pointer_required",
            candidate_commit_id=state_id,
            accepted_commit_id_before=current_state,
        )
        _json(step_dir / "receipt.json", artifact_receipt)
        manifest_file, manifest_sha = _write_manifest(step_dir, ["receipt.json", "fields.npz"])
        record_file, record_sha = _write_state_record(records_dir, state_id)
        phase = {key: global_record[key] for key in ("step", "cycle", "substep", "load")}
        index_file, index_sha = _write_state_index(
            indices_dir,
            state_id=state_id,
            parent_state_id=current_state,
            parent_index_file=current_index,
            record_file=record_file,
            record_sha=record_sha,
            evidence_dir=step_dir.name,
            manifest_file=manifest_file,
            manifest_sha=manifest_sha,
            phase=phase,
        )
        global_completion = dict(global_record)
        global_completion.update(
            candidate_commit_id=state_id,
            accepted_commit_id_before=current_state,
            accepted_commit_id_after=state_id,
            acceptance_status="committed_by_pointer",
        )
        global_records.append(global_completion)
        current_parent_state, current_parent_index = current_state, current_index
        current_state, current_index, current_index_sha = state_id, index_file, index_sha
        current_record_file, current_record_sha = record_file, record_sha

    _json(
        arm_dir / "accepted_state_pointer.json",
        {
            "schema": POINTER_SCHEMA,
            "accepted_commit_id": current_state,
            "parent_commit_id": current_parent_state,
            "parent_index_file": current_parent_index,
            "record_file": current_record_file,
            "record_sha256": current_record_sha,
            "state_index_file": current_index,
            "state_index_sha256": current_index_sha,
            "mesh_order_hash": "mesh-test",
            "field_route_hash": "route-test",
        },
    )

    terminal_records = terminal_records or []
    for terminal in terminal_records:
        step = int(terminal["step"])
        step_dir = arm_dir / f"step_{step:03d}"
        _fields(step_dir, candidate=True)
        _json(step_dir / "receipt.json", terminal)
    if write_steps_json:
        _json(arm_dir / "steps.json", [*global_records, *terminal_records])
    return arm_dir


class AnalyzeFeasibleDamageTest(unittest.TestCase):
    def run_analyzer(self, reference: Path, candidate: Path, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(ANALYZER),
                "--reference",
                str(reference),
                "--candidate",
                str(candidate),
                "--output",
                str(output),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_pointer_authority_accepts_null_artifact_receipt_and_separates_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference_root = root / "reference"
            candidate_root = root / "candidate"
            _mesh(reference_root)
            _mesh(candidate_root)
            _write_reference_arm(
                reference_root,
                [
                    _record(1, accepted=True, arm="original", load=0.03),
                    _record(2, accepted=True, arm="original", load=0.06),
                ],
            )
            candidate_arm = _write_e040_candidate(
                candidate_root,
                [_record(1, accepted=True, arm="feasible_damage", load=0.03000000005)],
                terminal_records=[_record(2, accepted=False, arm="feasible_damage", load=0.06)],
            )
            artifact_receipt = json.loads((candidate_arm / "step_001" / "receipt.json").read_text())
            self.assertIsNone(artifact_receipt["accepted"])

            output = root / "analysis"
            result = self.run_analyzer(reference_root, candidate_root, output)
            self.assertEqual(result.returncode, 0, result.stderr)

            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["common_accepted_prefix_steps"], 1)
            self.assertFalse(summary["reference_horizon_completed_by_candidate"])
            self.assertEqual(summary["terminal_kind"], "unaccepted_record")

            chain = json.loads((output / "candidate_state_chain.json").read_text())
            self.assertTrue(chain["steps_json"]["present"])
            self.assertEqual(chain["accepted_physical_steps"], [1])

            terminal = json.loads((output / "terminal_trial.json").read_text())
            self.assertEqual(terminal["kind"], "unaccepted_record")
            self.assertTrue(terminal["not_used_in_field_or_timing_comparison"])
            self.assertEqual(terminal["candidate_phase"]["step"], 2)

            with (output / "paired_fields.csv").open(newline="") as handle:
                field_rows = list(csv.DictReader(handle))
            self.assertEqual(len(field_rows), 4)
            self.assertEqual(
                {row["quantity"] for row in field_rows},
                {"damage_d", "strain_norm", "raw_psi_plus", "fatigue_A_trial"},
            )
            self.assertEqual({row["step"] for row in field_rows}, {"1"})

            with (output / "paired_energies.csv").open(newline="") as handle:
                energy_rows = list(csv.DictReader(handle))
            self.assertEqual(len(energy_rows), 1)
            self.assertEqual(energy_rows[0]["reference_E_irr_objective_included"], "True")
            self.assertEqual(energy_rows[0]["candidate_E_irr_objective_included"], "False")

            with (output / "timing.csv").open(newline="") as handle:
                timing_rows = list(csv.DictReader(handle))
            self.assertEqual(len(timing_rows), 1)
            self.assertEqual(timing_rows[0]["step"], "1")
            self.assertEqual(timing_rows[0]["candidate_timing_source"], "steps.json_post_pointer_receipt")

    def test_missing_steps_json_falls_back_to_committed_pointer_chain_without_time_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference_root = root / "reference"
            candidate_root = root / "candidate"
            _mesh(reference_root)
            _mesh(candidate_root)
            _write_reference_arm(
                reference_root,
                [
                    _record(1, accepted=True, arm="original", load=0.03),
                    _record(2, accepted=True, arm="original", load=0.06),
                ],
            )
            _write_e040_candidate(
                candidate_root,
                [
                    _record(1, accepted=True, arm="feasible_damage", load=0.03),
                    _record(2, accepted=True, arm="feasible_damage", load=0.06),
                ],
                write_steps_json=False,
            )

            output = root / "analysis"
            result = self.run_analyzer(reference_root, candidate_root, output)
            self.assertEqual(result.returncode, 0, result.stderr)

            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["candidate_records"], 2)
            self.assertTrue(summary["reference_horizon_completed_by_candidate"])
            timing = json.loads((output / "timing_summary.json").read_text())
            self.assertFalse(timing["timing_complete_for_common_prefix"])
            self.assertFalse(timing["speed_claim_supported"])
            self.assertIsNone(timing["candidate_seconds_common_prefix"])
            self.assertEqual(
                [item["step"] for item in timing["timing_unavailable_phases"]], [1, 2]
            )
            with (output / "timing.csv").open(newline="") as handle:
                self.assertEqual(list(csv.DictReader(handle)), [])
            chain = json.loads((output / "candidate_state_chain.json").read_text())
            self.assertFalse(chain["steps_json"]["present"])
            self.assertEqual(
                chain["steps_json"]["recovery"],
                "pointer_chain_only_after_missing_or_unwritten_steps_json",
            )

    def test_rejects_tampered_manifest_bound_fields_before_pairing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference_root = root / "reference"
            candidate_root = root / "candidate"
            _mesh(reference_root)
            _mesh(candidate_root)
            _write_reference_arm(
                reference_root,
                [_record(1, accepted=True, arm="original", load=0.03)],
            )
            candidate_arm = _write_e040_candidate(
                candidate_root,
                [_record(1, accepted=True, arm="feasible_damage", load=0.03)],
            )
            (candidate_arm / "step_001" / "fields.npz").write_bytes(b"tampered")
            result = self.run_analyzer(reference_root, candidate_root, root / "analysis")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA-256 mismatch", result.stderr)

    def test_rejects_nonidentical_mesh_before_any_field_pairing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference_root = root / "reference"
            candidate_root = root / "candidate"
            _mesh(reference_root)
            _mesh(candidate_root, x_shift=1.0e-4)
            _write_reference_arm(
                reference_root,
                [_record(1, accepted=True, arm="original", load=0.03)],
            )
            _write_e040_candidate(
                candidate_root,
                [_record(1, accepted=True, arm="feasible_damage", load=0.03)],
            )
            result = self.run_analyzer(reference_root, candidate_root, root / "analysis")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Strict mesh mismatch for xy", result.stderr)


if __name__ == "__main__":
    unittest.main()
