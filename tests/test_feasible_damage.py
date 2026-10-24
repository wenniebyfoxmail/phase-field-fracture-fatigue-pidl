"""Focused algebra and channel-isolation checks for S04-E040."""

from __future__ import annotations

import copy
import sys
import unittest
from unittest import mock
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "source"), str(ROOT / "SENS_tensile")]

from feasible_damage import StateReferencedFeasibleDamageMap
from field_computation import FieldComputation
import compute_energy as energy_module


class StateReferencedMapTests(unittest.TestCase):
    def test_bounds_and_exact_accepted_state_hold(self):
        h = torch.tensor([0.0, 0.2, 1.0])
        q_ref = torch.tensor([-2.0, 0.0, 4.0])
        transform = StateReferencedFeasibleDamageMap(h, q_ref)
        self.assertTrue(torch.equal(transform(q_ref), h))
        damage = transform(q_ref + torch.tensor([-1.0, 2.0, 9.0]))
        self.assertTrue(bool((damage >= h).all()))
        self.assertTrue(bool((damage <= 1.0).all()))
        self.assertEqual(float(damage[-1]), 1.0)

    def test_negative_increment_has_zero_damage_jacobian(self):
        h = torch.tensor([0.3])
        q_ref = torch.tensor([1.0])
        q = torch.tensor([0.5], requires_grad=True)
        damage = StateReferencedFeasibleDamageMap(h, q_ref)(q)
        damage.backward()
        self.assertEqual(float(q.grad), 0.0)

    def test_accepted_state_uses_positive_side_derivative(self):
        """A fresh solve starts at q=q_ref and must not be gradient-dead."""
        h = torch.tensor([0.3])
        q_ref = torch.tensor([1.0])
        q = torch.tensor([1.0], requires_grad=True)
        damage = StateReferencedFeasibleDamageMap(h, q_ref, slope=0.25)(q)
        damage.backward()
        self.assertAlmostEqual(float(q.grad), 0.7 * 0.25)

    def test_reference_is_copied_and_nonfinite_values_fail(self):
        h = torch.tensor([0.2])
        q_ref = torch.tensor([0.0])
        transform = StateReferencedFeasibleDamageMap(h, q_ref)
        q_ref.add_(1.0)
        self.assertEqual(float(transform.q_reference), 0.0)
        with self.assertRaises(FloatingPointError):
            transform(torch.tensor([float("nan")]))


class DamageOnlyPartitionTests(unittest.TestCase):
    def test_q_only_partition_preserves_global_displacements(self):
        torch.manual_seed(7)
        net = torch.nn.Linear(2, 3)
        net_q_only = copy.deepcopy(net)
        extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
        theta = torch.tensor([torch.pi / 2])
        base = FieldComputation(net, extrema, torch.tensor(0.1), theta)
        q_only = FieldComputation(
            net_q_only, extrema, torch.tensor(0.1), theta,
            local_patch_dict={
                "enable": True, "x_tip": 0.0, "y_tip": 0.0, "wr": 0.3,
                "output_mode": "q_only", "blend_mode": "damage_partition",
                "hidden_layers": 1, "neurons": 4,
            },
        )
        inp = torch.tensor([[-0.1, 0.0], [0.1, 0.05], [0.4, 0.2]])
        u0, v0, _ = base.fieldCalculation(inp)
        u1, v1, _ = q_only.fieldCalculation(inp)
        torch.testing.assert_close(u0, u1)
        torch.testing.assert_close(v0, v1)

    def test_q_only_requires_damage_partition(self):
        with self.assertRaises(ValueError):
            FieldComputation(
                torch.nn.Linear(2, 3), torch.tensor([[-0.5, 0.5], [-0.5, 0.5]]),
                torch.tensor(0.1), torch.tensor([torch.pi / 2]),
                local_patch_dict={"enable": True, "output_mode": "q_only", "blend_mode": "additive"},
            )


class EnergyPathTests(unittest.TestCase):
    def test_no_irr_mode_is_forwarded_to_element_energy(self):
        values = (torch.ones(2), torch.ones(2), torch.ones(2))
        with mock.patch.object(energy_module, "compute_energy_per_elem", return_value=values) as mocked:
            e_el, e_d, e_irr = energy_module.compute_energy(
                torch.empty(0), torch.empty(0), torch.empty(0), torch.empty(0), torch.empty(0),
                object(), object(), torch.empty(0), include_irreversibility=False,
            )
        self.assertEqual(float(e_el), 2.0)
        self.assertEqual(float(e_d), 2.0)
        self.assertEqual(float(e_irr), 2.0)
        self.assertIs(mocked.call_args.kwargs["include_irreversibility"], False)


if __name__ == "__main__":
    unittest.main()
