"""CPU contract tests for the E040 accepted-state transaction primitives."""

from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

import torch


WORKTREE = Path(__file__).resolve().parents[1]
RUNNER = WORKTREE / "scripts" / "run_s04_e040_feasible_damage.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("s04_e040_runner_for_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class E040TransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def make_initial_state(self):
        runner = self.runner
        torch.manual_seed(7)
        net = torch.nn.Sequential(torch.nn.Linear(2, 3)).float()
        inp = torch.tensor(
            [[-0.5, -0.5], [0.0, 0.0], [0.5, 0.5]], dtype=torch.float32
        )
        field = runner.FieldComputation(
            net,
            torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], dtype=torch.float32),
            torch.tensor(0.0),
            torch.tensor([math.pi / 2], dtype=torch.float32),
            l0=0.01,
        )
        capture = runner.LegacyRawCapture(field.alpha_constraint)
        field.alpha_constraint = capture
        with torch.no_grad():
            field.fieldCalculation(inp)
        self.assertIsNotNone(capture.raw)
        q_ref = capture.raw.detach().clone()
        state = runner.AcceptedState(
            commit_id="state_000",
            history_alpha=torch.tensor([0.0, 0.3, 0.7], dtype=torch.float32),
            hist_fat=torch.zeros(1, dtype=torch.float32),
            psi_plus_prev=torch.zeros(1, dtype=torch.float32),
            q_ref=q_ref,
            parent_commit_id=None,
        )
        return net, inp, state

    def test_pointer_binds_complete_record_and_evidence_before_restore(self):
        runner = self.runner
        net, inp, state = self.make_initial_state()
        with tempfile.TemporaryDirectory() as temporary:
            arm = Path(temporary) / "arm"
            arm.mkdir()
            records = arm / "accepted_states"
            indices = arm / "state_indices"
            pointer = arm / "accepted_state_pointer.json"
            mesh_hash, route_hash = "mesh-test", "route-test"
            deadline = time.monotonic() + 10.0
            staged_record, final_record, audit, record_sha = runner.stage_accepted_state_record(
                records, net, state, mesh_hash, route_hash, inp, "cpu", deadline
            )
            self.assertTrue(audit["passed"])
            self.assertFalse(pointer.exists())

            evidence_stage = arm / ".txn-initial.tmp"
            evidence_stage.mkdir()
            runner.write_json_durable(evidence_stage / "initial_state_audit.json", {"ok": True})
            manifest, manifest_sha = runner.write_artifact_manifest(
                evidence_stage, ["initial_state_audit.json"]
            )
            staged_index, final_index, index_sha = runner.stage_state_index(
                indices,
                state=state,
                parent_index_file=None,
                parent_index_sha256=None,
                record_file=final_record.name,
                record_sha256=record_sha,
                evidence_dir="initial_state",
                artifact_manifest_file=manifest.name,
                artifact_manifest_sha256=manifest_sha,
                mesh_order_hash=mesh_hash,
                route_hash=route_hash,
                phase=None,
            )
            runner.publish_file(staged_record, final_record)
            runner.publish_directory(evidence_stage, arm / "initial_state")
            runner.publish_file(staged_index, final_index)
            publication = runner.publish_pointer_last(
                pointer_path=pointer,
                arm_dir=arm,
                records_dir=records,
                indices_dir=indices,
                state=state,
                final_record_path=final_record,
                record_sha256=record_sha,
                final_index_path=final_index,
                index_sha256=index_sha,
                expected_mesh_hash=mesh_hash,
                expected_route_hash=route_hash,
                device="cpu",
                deadline=deadline,
            )
            self.assertFalse(publication["recovered_after_publication_error"])
            restored, record = runner.restore_accepted_state(
                pointer, arm, records, indices, net, mesh_hash, route_hash, "cpu"
            )
            self.assertEqual(restored.commit_id, "state_000")
            self.assertTrue(torch.equal(restored.q_ref, state.q_ref))
            self.assertTrue(torch.equal(restored.history_alpha, state.history_alpha))
            self.assertEqual(record["state_index"]["evidence_dir"], "initial_state")
            on_disk_pointer = json.loads(pointer.read_text())
            self.assertEqual(on_disk_pointer["accepted_commit_id"], "state_000")

    def test_restore_rejects_tampered_pointer_bound_evidence(self):
        runner = self.runner
        net, inp, state = self.make_initial_state()
        with tempfile.TemporaryDirectory() as temporary:
            arm = Path(temporary) / "arm"
            arm.mkdir()
            records = arm / "accepted_states"
            indices = arm / "state_indices"
            pointer = arm / "accepted_state_pointer.json"
            mesh_hash, route_hash = "mesh-test", "route-test"
            deadline = time.monotonic() + 10.0
            staged_record, final_record, _, record_sha = runner.stage_accepted_state_record(
                records, net, state, mesh_hash, route_hash, inp, "cpu", deadline
            )
            evidence_stage = arm / ".txn-initial.tmp"
            evidence_stage.mkdir()
            runner.write_json_durable(evidence_stage / "initial_state_audit.json", {"ok": True})
            manifest, manifest_sha = runner.write_artifact_manifest(
                evidence_stage, ["initial_state_audit.json"]
            )
            staged_index, final_index, index_sha = runner.stage_state_index(
                indices,
                state=state,
                parent_index_file=None,
                parent_index_sha256=None,
                record_file=final_record.name,
                record_sha256=record_sha,
                evidence_dir="initial_state",
                artifact_manifest_file=manifest.name,
                artifact_manifest_sha256=manifest_sha,
                mesh_order_hash=mesh_hash,
                route_hash=route_hash,
                phase=None,
            )
            runner.publish_file(staged_record, final_record)
            runner.publish_directory(evidence_stage, arm / "initial_state")
            runner.publish_file(staged_index, final_index)
            runner.publish_pointer_last(
                pointer_path=pointer,
                arm_dir=arm,
                records_dir=records,
                indices_dir=indices,
                state=state,
                final_record_path=final_record,
                record_sha256=record_sha,
                final_index_path=final_index,
                index_sha256=index_sha,
                expected_mesh_hash=mesh_hash,
                expected_route_hash=route_hash,
                device="cpu",
                deadline=deadline,
            )
            (arm / "initial_state" / "initial_state_audit.json").write_text('{"ok": false}\n')
            with self.assertRaises(runner.StateContractError):
                runner.restore_accepted_state(
                    pointer, arm, records, indices, net, mesh_hash, route_hash, "cpu"
                )

    def test_full_lineage_rejects_replaced_ancestor_before_restore_or_pointer_advance(self):
        """A valid head must not hide a modified root state-index bundle."""
        runner = self.runner
        net, inp, initial = self.make_initial_state()
        with tempfile.TemporaryDirectory() as temporary:
            arm = Path(temporary) / "arm"
            arm.mkdir()
            records = arm / "accepted_states"
            indices = arm / "state_indices"
            pointer = arm / "accepted_state_pointer.json"
            mesh_hash, route_hash = "mesh-test", "route-test"
            deadline = time.monotonic() + 10.0

            def stage_bundle(
                state,
                evidence_name: str,
                parent_index_file: str | None,
                parent_index_sha256: str | None,
            ):
                staged_record, final_record, _, record_sha = runner.stage_accepted_state_record(
                    records, net, state, mesh_hash, route_hash, inp, "cpu", deadline
                )
                evidence_stage = arm / f".{evidence_name}.tmp"
                evidence_stage.mkdir()
                runner.write_json_durable(evidence_stage / "audit.json", {"state": state.commit_id})
                manifest, manifest_sha = runner.write_artifact_manifest(evidence_stage, ["audit.json"])
                staged_index, final_index, index_sha = runner.stage_state_index(
                    indices,
                    state=state,
                    parent_index_file=parent_index_file,
                    parent_index_sha256=parent_index_sha256,
                    record_file=final_record.name,
                    record_sha256=record_sha,
                    evidence_dir=evidence_name,
                    artifact_manifest_file=manifest.name,
                    artifact_manifest_sha256=manifest_sha,
                    mesh_order_hash=mesh_hash,
                    route_hash=route_hash,
                    phase=None,
                )
                runner.publish_file(staged_record, final_record)
                runner.publish_directory(evidence_stage, arm / evidence_name)
                runner.publish_file(staged_index, final_index)
                return final_record, record_sha, final_index, index_sha

            initial_record, initial_record_sha, initial_index, initial_index_sha = stage_bundle(
                initial, "initial_state", None, None
            )
            runner.publish_pointer_last(
                pointer_path=pointer,
                arm_dir=arm,
                records_dir=records,
                indices_dir=indices,
                state=initial,
                final_record_path=initial_record,
                record_sha256=initial_record_sha,
                final_index_path=initial_index,
                index_sha256=initial_index_sha,
                expected_mesh_hash=mesh_hash,
                expected_route_hash=route_hash,
                device="cpu",
                deadline=deadline,
            )

            state_one = runner.AcceptedState(
                commit_id="state_001",
                history_alpha=initial.history_alpha.detach().clone(),
                hist_fat=initial.hist_fat.detach().clone(),
                psi_plus_prev=initial.psi_plus_prev.detach().clone(),
                q_ref=initial.q_ref.detach().clone(),
                parent_commit_id=initial.commit_id,
            )
            state_one_record, state_one_record_sha, state_one_index, state_one_index_sha = stage_bundle(
                state_one, "step_001", initial_index.name, initial_index_sha
            )
            runner.publish_pointer_last(
                pointer_path=pointer,
                arm_dir=arm,
                records_dir=records,
                indices_dir=indices,
                state=state_one,
                final_record_path=state_one_record,
                record_sha256=state_one_record_sha,
                final_index_path=state_one_index,
                index_sha256=state_one_index_sha,
                expected_mesh_hash=mesh_hash,
                expected_route_hash=route_hash,
                device="cpu",
                deadline=deadline,
            )

            # The head remains state_001 and its pointer hash is untouched.
            # Replacing only state_000 must nevertheless invalidate the child
            # state_001 -> state_000 parent-index SHA link.
            root_index = json.loads(initial_index.read_text())
            root_index["replacement_marker"] = "changed-ancestor-bytes"
            runner.write_json_durable(initial_index, root_index)
            with self.assertRaisesRegex(runner.StateContractError, "state-index hash mismatch"):
                runner.restore_accepted_state(
                    pointer, arm, records, indices, net, mesh_hash, route_hash, "cpu"
                )

            state_two = runner.AcceptedState(
                commit_id="state_002",
                history_alpha=initial.history_alpha.detach().clone(),
                hist_fat=initial.hist_fat.detach().clone(),
                psi_plus_prev=initial.psi_plus_prev.detach().clone(),
                q_ref=initial.q_ref.detach().clone(),
                parent_commit_id=state_one.commit_id,
            )
            state_two_record, state_two_record_sha, state_two_index, state_two_index_sha = stage_bundle(
                state_two, "step_002", state_one_index.name, state_one_index_sha
            )
            with self.assertRaisesRegex(runner.StateContractError, "state-index hash mismatch"):
                runner.publish_pointer_last(
                    pointer_path=pointer,
                    arm_dir=arm,
                    records_dir=records,
                    indices_dir=indices,
                    state=state_two,
                    final_record_path=state_two_record,
                    record_sha256=state_two_record_sha,
                    final_index_path=state_two_index,
                    index_sha256=state_two_index_sha,
                    expected_mesh_hash=mesh_hash,
                    expected_route_hash=route_hash,
                    device="cpu",
                    deadline=deadline,
                )
            self.assertEqual(json.loads(pointer.read_text())["accepted_commit_id"], "state_001")

    def test_pointer_does_not_publish_a_bundle_that_fails_prevalidation(self):
        runner = self.runner
        net, inp, state = self.make_initial_state()
        with tempfile.TemporaryDirectory() as temporary:
            arm = Path(temporary) / "arm"
            arm.mkdir()
            records = arm / "accepted_states"
            indices = arm / "state_indices"
            pointer = arm / "accepted_state_pointer.json"
            mesh_hash, route_hash = "mesh-test", "route-test"
            deadline = time.monotonic() + 10.0
            staged_record, final_record, _, record_sha = runner.stage_accepted_state_record(
                records, net, state, mesh_hash, route_hash, inp, "cpu", deadline
            )
            evidence_stage = arm / ".txn-initial.tmp"
            evidence_stage.mkdir()
            runner.write_json_durable(evidence_stage / "initial_state_audit.json", {"ok": True})
            manifest, manifest_sha = runner.write_artifact_manifest(
                evidence_stage, ["initial_state_audit.json"]
            )
            staged_index, final_index, index_sha = runner.stage_state_index(
                indices,
                state=state,
                parent_index_file=None,
                parent_index_sha256=None,
                record_file=final_record.name,
                record_sha256=record_sha,
                evidence_dir="initial_state",
                artifact_manifest_file=manifest.name,
                artifact_manifest_sha256=manifest_sha,
                mesh_order_hash=mesh_hash,
                route_hash=route_hash,
                phase=None,
            )
            runner.publish_file(staged_record, final_record)
            runner.publish_directory(evidence_stage, arm / "initial_state")
            runner.publish_file(staged_index, final_index)
            (arm / "initial_state" / "initial_state_audit.json").write_text('{"ok": false}\n')

            with self.assertRaises(runner.StateContractError):
                runner.publish_pointer_last(
                    pointer_path=pointer,
                    arm_dir=arm,
                    records_dir=records,
                    indices_dir=indices,
                    state=state,
                    final_record_path=final_record,
                    record_sha256=record_sha,
                    final_index_path=final_index,
                    index_sha256=index_sha,
                    expected_mesh_hash=mesh_hash,
                    expected_route_hash=route_hash,
                    device="cpu",
                    deadline=deadline,
                )
            self.assertFalse(pointer.exists())

    def test_staged_record_requires_bitwise_reload_invariants(self):
        runner = self.runner
        net, inp, state = self.make_initial_state()
        with tempfile.TemporaryDirectory() as temporary:
            records = Path(temporary) / "accepted_states"
            audit = dict(
                passed=True,
                q_reload_bitwise=False,
                d_reload_bitwise=True,
            )
            with mock.patch.object(runner, "reload_audit", return_value=audit):
                with self.assertRaisesRegex(runner.StateContractError, "q\\(theta\\) != q_ref bitwise"):
                    runner.stage_accepted_state_record(
                        records,
                        net,
                        state,
                        "mesh-test",
                        "route-test",
                        inp,
                        "cpu",
                        time.monotonic() + 10.0,
                    )
            self.assertFalse((records / "state_000.pt").exists())
            self.assertEqual(list(records.glob("*.tmp")), [])

    def test_full_step_deadline_keeps_finalization_inside_step_budget(self):
        runner = self.runner
        total_deadline = 3300.0
        step_seconds = 240.0

        # 245 seconds remain: 240 seconds for the whole physical step is still
        # possible because run_step allocates its final 15 seconds internally.
        deadline = runner.full_step_deadline(total_deadline, step_seconds, 3055.0)
        self.assertEqual(deadline, 3295.0)
        self.assertLessEqual(deadline, total_deadline)

        # Exactly one full step remains, and any shorter remainder is rejected.
        self.assertEqual(
            runner.full_step_deadline(total_deadline, step_seconds, 3060.0),
            total_deadline,
        )
        self.assertIsNone(
            runner.full_step_deadline(total_deadline, step_seconds, 3060.000001)
        )


if __name__ == "__main__":
    unittest.main()
