"""Focused non-CUDA contracts for E043 acceptance and zero-load policy."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys
import unittest

import torch


WORKTREE = Path(__file__).resolve().parents[1]
RUNNER_PATH = WORKTREE / "scripts" / "run_s04_e043_kkt_zero_load.py"
spec = importlib.util.spec_from_file_location("e043_runner_contract", RUNNER_PATH)
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def kkt_receipt(**overrides: object) -> dict[str, object]:
    receipt: dict[str, object] = {
        "converged": True,
        "final_theta_fixed_recheck": True,
        "eta_kkt_residual_inf": 2.0e-5,
        "eta_kkt_mapping_inf": 1.0e-6,
        "gradient_inf_tolerance": 1.0e-4,
        "mapping_inf_tolerance": 4.0e-6,
    }
    receipt.update(overrides)
    return receipt


class E043KktContractTests(unittest.TestCase):
    def test_accepted_state_paths_share_the_e043_carrier_identity(self):
        expected = "reference_base_eta_projected_kkt_zero_load_v1"
        self.assertEqual(runner.DAMAGE_CARRIER_ID, expected)
        for function in (runner.reload_audit, runner.stage_accepted_state_record, runner.restore_accepted_state):
            self.assertIn("DAMAGE_CARRIER_ID", inspect.getsource(function))

    def test_eta_kkt_receipt_requires_final_recheck_and_numeric_tolerances(self):
        self.assertTrue(runner.eta_kkt_receipt_converged(kkt_receipt()))
        self.assertFalse(
            runner.eta_kkt_receipt_converged(
                kkt_receipt(eta_kkt_residual_inf=2.0e-4)
            )
        )
        self.assertFalse(
            runner.eta_kkt_receipt_converged(
                kkt_receipt(final_theta_fixed_recheck=False)
            )
        )
        self.assertFalse(
            runner.eta_kkt_receipt_converged(
                kkt_receipt(converged=False)
            )
        )
        self.assertFalse(runner.eta_kkt_receipt_converged(None))

    def test_loss_plateau_cannot_accept_without_a_valid_final_kkt_receipt(self):
        self.assertFalse(
            runner.eta_kkt_termination_is_accepting(
                "projected_relative_loss_plateau",
                kkt_receipt(),
            )
        )
        self.assertFalse(
            runner.eta_kkt_termination_is_accepting(
                "loss_plateau_and_eta_kkt",
                kkt_receipt(eta_kkt_mapping_inf=8.0e-6),
            )
        )
        self.assertTrue(
            runner.eta_kkt_termination_is_accepting(
                "loss_plateau_and_eta_kkt",
                kkt_receipt(),
            )
        )

    def test_final_eta_target_does_not_reconstruct_or_change_eta(self):
        dtype = torch.float64
        h = torch.tensor([0.2, 0.4], dtype=dtype)
        q = torch.zeros_like(h)
        carrier = runner.ReferenceBaseProjectedDamage.from_raw_reference(h, q, lambda raw: raw)
        with torch.no_grad():
            carrier.eta.copy_(torch.tensor([0.1, 0.2], dtype=dtype))
        eta_before = carrier.eta.detach().clone()

        target = runner.final_eta_target(carrier, q)

        torch.testing.assert_close(carrier.eta.detach(), eta_before, rtol=0.0, atol=0.0)
        torch.testing.assert_close(
            target,
            torch.tensor([0.3, 0.6], dtype=dtype),
            rtol=0.0,
            atol=8.0 * torch.finfo(dtype).eps,
        )

    def test_zero_load_policy_is_exact_and_does_not_classify_small_load_as_zero(self):
        self.assertTrue(runner.is_zero_load(torch.tensor(0.0)))
        self.assertFalse(runner.is_zero_load(torch.tensor(1.0e-12)))
        self.assertFalse(runner.is_zero_load(torch.tensor(-1.0e-12)))


if __name__ == "__main__":
    unittest.main()
