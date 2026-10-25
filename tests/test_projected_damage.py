"""CPU contracts for the S04-E042 projected direct-nodal damage carrier."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from feasible_damage import compute_elastic_damage_energy
from material_properties import MaterialProperties
from pff_model import PFFModel
from projected_damage import ReferenceBaseProjectedDamage, tri3_values


class _NoIrreversibilityPFF(PFFModel):
    """Fails if a test accidentally routes through an irreversibility loss."""

    def irrPenalty(self):  # noqa: N802 - inherited project API spelling
        raise AssertionError("E_irr must not be constructed by the direct path")


class ProjectedDamageTests(unittest.TestCase):
    def test_reference_state_starts_exactly_at_history(self):
        dtype = torch.float64
        h = torch.tensor([0.0, 0.2, 0.6, 1.0], dtype=dtype, requires_grad=True)
        q_ref = torch.tensor([-3.0, -0.2, 0.0, 2.0], dtype=dtype, requires_grad=True)
        carrier = ReferenceBaseProjectedDamage(
            h,
            torch.sigmoid,
            base_reference=torch.sigmoid(q_ref.detach()),
        )

        q = q_ref.detach().clone().requires_grad_()
        d = carrier(q)

        self.assertTrue(torch.equal(d, h.detach()))
        self.assertTrue(carrier.eta.is_leaf)
        self.assertTrue(carrier.eta.requires_grad)
        self.assertFalse(carrier.history_alpha.requires_grad)
        self.assertFalse(carrier.base_reference.requires_grad)
        self.assertFalse(hasattr(carrier, "raw_damage_reference"))
        self.assertEqual(carrier.latest().forward_id, 1)
        self.assertIs(carrier.latest().damage, d)
        self.assertEqual(carrier.latest().mode, "direct_damage")

    def test_block_routes_hold_target_and_reconstruct_direct_eta(self):
        dtype = torch.float64
        h = torch.tensor([0.1, 0.2, 0.3], dtype=dtype)
        q_ref = torch.zeros_like(h)
        q = torch.tensor([0.4, -0.2, 0.6], dtype=dtype, requires_grad=True)
        target = torch.tensor([0.25, 0.55, 0.7], dtype=dtype)
        carrier = ReferenceBaseProjectedDamage.from_raw_reference(h, q_ref, torch.sigmoid)

        reconstructed = carrier.set_damage_(target, q.detach())
        held = carrier.damage(q, mode="hold_damage")
        held_snapshot = carrier.latest()
        direct = carrier.damage(q, mode="direct_damage")
        eta_grad, raw_grad = torch.autograd.grad(
            direct.sum(), (carrier.eta, q), allow_unused=True
        )

        self.assertTrue(torch.equal(held, target))
        self.assertFalse(held.requires_grad)
        torch.testing.assert_close(direct, target, rtol=0.0, atol=8.0 * torch.finfo(dtype).eps)
        self.assertIsNone(raw_grad)
        torch.testing.assert_close(eta_grad, torch.ones_like(eta_grad), rtol=0.0, atol=0.0)
        self.assertTrue(torch.equal(reconstructed, carrier.eta.detach()))
        self.assertEqual(held_snapshot.mode, "hold_damage")
        self.assertIsNone(held_snapshot.base_damage)

        next_q = torch.tensor([-0.6, 0.3, -0.4], dtype=dtype)
        carrier.set_damage_(target, next_q)
        torch.testing.assert_close(
            carrier.damage(next_q, mode="direct_damage"),
            target,
            rtol=0.0,
            atol=8.0 * torch.finfo(dtype).eps,
        )

    def test_projection_enforces_node_and_tri3_bounds(self):
        dtype = torch.float64
        h = torch.tensor([0.1, 0.6, 0.2, 1.0], dtype=dtype)
        q_ref = torch.zeros_like(h)
        q = torch.tensor([-0.4, 0.4, 0.2, 0.7], dtype=dtype)
        carrier = ReferenceBaseProjectedDamage.from_raw_reference(h, q_ref, lambda raw: raw)
        with torch.no_grad():
            carrier.eta.copy_(torch.tensor([-1.0, 1.0, -1.0, 1.0], dtype=dtype))

        report = carrier.project_eta_(q)
        d = carrier(q)
        conn = torch.tensor([[0, 1, 2], [1, 3, 2]], dtype=torch.long)
        metrics = carrier.feasibility_metrics(q, connectivity=conn)

        expected_eta = torch.tensor([0.4, 0.0, -0.2, -0.7], dtype=dtype)
        torch.testing.assert_close(carrier.eta.detach(), expected_eta, rtol=0.0, atol=0.0)
        self.assertTrue(torch.all(d >= h))
        self.assertTrue(torch.all(d <= 1.0))
        self.assertTrue(torch.all(tri3_values(d - h, conn) >= 0.0))
        self.assertTrue(torch.all(tri3_values(1.0 - d, conn) >= 0.0))
        self.assertTrue(torch.equal(report.eta_after, expected_eta))
        self.assertTrue(bool(report.clipped_to_lower[0]))
        self.assertTrue(bool(report.clipped_to_upper[1]))
        for name in (
            "max_node_lower_violation",
            "max_node_upper_violation",
            "max_tri3_lower_violation",
            "max_tri3_upper_violation",
        ):
            self.assertLessEqual(metrics[name], 8.0 * torch.finfo(dtype).eps)

    def test_projected_residual_distinguishes_blocked_and_released_directions(self):
        dtype = torch.float64
        h = torch.tensor([0.2, 0.2, 0.2, 1.0], dtype=dtype)
        q_ref = torch.zeros_like(h)
        q = torch.zeros_like(h)
        carrier = ReferenceBaseProjectedDamage.from_raw_reference(h, q_ref, lambda raw: raw)
        with torch.no_grad():
            carrier.eta.copy_(torch.tensor([0.0, 0.0, 0.8, 0.0], dtype=dtype))
        carrier.project_eta_(q)

        residual = carrier.projected_residual(
            q,
            torch.tensor([1.0, -1.0, -1.0, -1.0], dtype=dtype),
            step_size=0.25,
        )

        self.assertTrue(bool(residual.blocked_lower[0]))
        self.assertTrue(bool(residual.released_lower[1]))
        self.assertTrue(bool(residual.blocked_upper[2]))
        self.assertFalse(bool(residual.released_upper[2]))
        self.assertTrue(bool(residual.fixed[3]))
        self.assertFalse(bool(residual.blocked_lower[3]))
        self.assertFalse(bool(residual.blocked_upper[3]))
        torch.testing.assert_close(
            residual.projected_eta,
            torch.tensor([0.0, 0.25, 0.8, 0.0], dtype=dtype),
            rtol=0.0,
            atol=0.0,
        )
        torch.testing.assert_close(
            residual.residual,
            torch.tensor([0.0, -1.0, 0.0, 0.0], dtype=dtype),
            rtol=0.0,
            atol=0.0,
        )

    def test_lower_active_damage_can_release_and_lower_a_same_objective(self):
        """A lower-active coordinate retains an upward physical direction."""
        dtype = torch.float64
        h = torch.tensor([0.2], dtype=dtype)
        q = torch.zeros_like(h)
        target = torch.tensor([0.6], dtype=dtype)
        carrier = ReferenceBaseProjectedDamage.from_raw_reference(h, q, lambda raw: raw)

        d_before = carrier(q)
        objective_before = (d_before - target).square().sum()
        gradient = torch.autograd.grad(objective_before, carrier.eta)[0]
        residual = carrier.projected_residual(q, gradient, step_size=0.25)

        self.assertTrue(bool(residual.released_lower[0]))
        self.assertLess(float(gradient[0]), 0.0)
        with torch.no_grad():
            carrier.eta.copy_(residual.projected_eta)
            carrier.project_eta_(q)
        d_after = carrier(q)
        objective_after = (d_after - target).square().sum()

        self.assertGreater(float(d_after.detach()[0]), float(h[0]))
        self.assertTrue(torch.all(d_after >= h))
        self.assertLess(float(objective_after.detach()), float(objective_before.detach()))

    def test_physical_loss_backpropagates_to_eta_without_irreversibility_penalty(self):
        dtype = torch.float64
        inp = torch.tensor([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=dtype)
        conn = torch.tensor([[0, 1, 2]], dtype=torch.long)
        area = torch.tensor([1.0], dtype=dtype)
        h = torch.tensor([0.1, 0.2, 0.3], dtype=dtype)
        q_ref = torch.zeros_like(h)
        q = torch.tensor([0.1, -0.3, 0.2], dtype=dtype, requires_grad=True)
        carrier = ReferenceBaseProjectedDamage.from_raw_reference(h, q_ref, lambda raw: raw)
        carrier.project_eta_(q.detach())
        u = torch.tensor([0.0, 0.1, 0.0], dtype=dtype, requires_grad=True)
        v = torch.tensor([0.0, 0.0, 0.1], dtype=dtype, requires_grad=True)
        pff = _NoIrreversibilityPFF("AT1", "volumetric", torch.tensor(5e-3, dtype=dtype))
        mat = MaterialProperties(
            torch.tensor(1.0, dtype=dtype),
            torch.tensor(0.3, dtype=dtype),
            torch.tensor(1.0, dtype=dtype),
            torch.tensor(0.01, dtype=dtype),
        )

        d = carrier(q)
        e_el, e_d = compute_elastic_damage_energy(inp, u, v, d, mat, pff, area, conn)
        (e_el + e_d).backward()

        self.assertIsNotNone(carrier.eta.grad)
        self.assertTrue(torch.isfinite(carrier.eta.grad).all())
        # ``direct_damage`` deliberately detaches the base path: eta sees the
        # physical gradient, while the frozen raw-head block sees none.
        self.assertIsNone(q.grad)


if __name__ == "__main__":
    unittest.main()
