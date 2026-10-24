"""Synthetic contract test for the read-only E040 trajectory analyzer."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


WORKTREE = Path(__file__).resolve().parents[1]
ANALYZER = WORKTREE / "scripts" / "analyze_s04_e040_feasible_damage.py"


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


def _write_arm(root: Path, arm: str, records: list[dict[str, object]], *, candidate: bool) -> Path:
    arm_dir = root / arm
    arm_dir.mkdir(parents=True, exist_ok=True)
    (arm_dir / "steps.json").write_text(json.dumps(records, indent=2) + "\n")
    (arm_dir / "summary.json").write_text(json.dumps({"steps_attempted": len(records)}, indent=2) + "\n")
    for record in records:
        step = int(record["step"])
        step_dir = arm_dir / f"step_{step:03d}"
        step_dir.mkdir(parents=True, exist_ok=True)
        (step_dir / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
        _fields(step_dir, candidate=candidate)
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

    def test_pairs_only_accepted_continuous_prefix_and_separates_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference_root = root / "reference"
            candidate_root = root / "candidate"
            _mesh(reference_root)
            _mesh(candidate_root)
            _write_arm(
                reference_root,
                "original",
                [
                    _record(1, accepted=True, arm="original", load=0.03),
                    _record(2, accepted=True, arm="original", load=0.06),
                ],
                candidate=False,
            )
            _write_arm(
                candidate_root,
                "feasible_damage",
                [
                    _record(1, accepted=True, arm="feasible_damage", load=0.03000000005),
                    _record(2, accepted=False, arm="feasible_damage", load=0.06),
                ],
                candidate=True,
            )
            output = root / "analysis"
            result = self.run_analyzer(reference_root, candidate_root, output)
            self.assertEqual(result.returncode, 0, result.stderr)

            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["common_accepted_prefix_steps"], 1)
            self.assertFalse(summary["reference_horizon_completed_by_candidate"])
            self.assertEqual(summary["terminal_kind"], "unaccepted_record")

            terminal = json.loads((output / "terminal_trial.json").read_text())
            self.assertEqual(terminal["kind"], "unaccepted_record")
            self.assertTrue(terminal["not_used_in_field_or_timing_comparison"])
            self.assertEqual(terminal["candidate_phase"]["step"], 2)

            with (output / "paired_fields.csv").open(newline="") as handle:
                field_rows = list(csv.DictReader(handle))
            self.assertEqual(len(field_rows), 4)
            self.assertEqual({row["quantity"] for row in field_rows}, {"damage_d", "strain_norm", "raw_psi_plus", "fatigue_A_trial"})
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

    def test_rejects_nonidentical_mesh_before_any_field_pairing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference_root = root / "reference"
            candidate_root = root / "candidate"
            _mesh(reference_root)
            _mesh(candidate_root, x_shift=1.0e-4)
            records_reference = [_record(1, accepted=True, arm="original", load=0.03)]
            records_candidate = [_record(1, accepted=True, arm="feasible_damage", load=0.03)]
            _write_arm(reference_root, "original", records_reference, candidate=False)
            _write_arm(candidate_root, "feasible_damage", records_candidate, candidate=True)
            result = self.run_analyzer(reference_root, candidate_root, root / "analysis")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Strict mesh mismatch for xy", result.stderr)


if __name__ == "__main__":
    unittest.main()
