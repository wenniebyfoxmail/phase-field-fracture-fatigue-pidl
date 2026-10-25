"""CPU contracts for the E043 conditional projected eta-KKT helpers."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from projected_damage import ReferenceBaseProjectedDamage, tri3_values
from projected_kkt import armijo_sufficient_decrease, eta_kkt_converged, raw_eta_kkt_residual


class ProjectedEtaKktTests(unittest.TestCase):
    def test_raw_kkt_residual_classifies_lower_upper_and_fixed_dofs(self):
        dtype = torch.float64
        h = torch.tensor([0.2, 0.2, 0.2, 1.0], dtype=dtype)
        q = torch.zeros_like(h)
        carrier = ReferenceBaseProjectedDamage.from_raw_reference(h, q, lambda raw: raw)
        with torch.no_grad():
            carrier.eta.copy_(torch.tensor([0.0, 0.0, 0.8, 0.0], dtype=dtype))
        carrier.project_eta_(q)

        report = raw_eta_kkt_residual(
            carrier,
            q,
            torch.tensor([1.0, -2.0, -3.0, -4.0], dtype=dtype),
            metric=torch.tensor([2.0, 3.0, 5.0, 7.0], dtype=dtype),
            reference_step=0.25,
        )

        self.assertTrue(bool(report.blocked_lower[0]))
        self.assertTrue(bool(report.released_lower[1]))
        self.assertTrue(bool(report.blocked_upper[2]))
        self.assertTrue(bool(report.fixed[3]))
        torch.testing.assert_close(
            report.residual,
            torch.tensor([0.0, -2.0, 0.0, 0.0], dtype=dtype),
            rtol=0.0,
            atol=0.0,
        )
        self.assertFalse(
            eta_kkt_converged(
                report,
                gradient_inf_tolerance=1.0e-6,
                mapping_inf_tolerance=1.0e-6,
            )
        )

    def test_projected_quadratic_reaches_kkt_at_bounds_and_free_coordinate(self):
        dtype = torch.float64
        h = torch.tensor([0.2, 0.2, 0.2, 1.0], dtype=dtype)
        q = torch.zeros_like(h)
        target = torch.tensor([0.0, 0.65, 1.2, 0.8], dtype=dtype)
        metric = torch.tensor([2.0, 3.0, 5.0, 7.0], dtype=dtype)
        carrier = ReferenceBaseProjectedDamage.from_raw_reference(h, q, lambda raw: raw)
        connectivity = torch.tensor([[0, 1, 2], [1, 3, 2]], dtype=torch.long)

        d_before = carrier(q)
        objective_before = 1.0 + 0.5 * (metric * (d_before - target).square()).sum()
        gradient = torch.autograd.grad(objective_before, carrier.eta)[0]
        report_before = raw_eta_kkt_residual(
            carrier, q, gradient, metric=metric, reference_step=1.0
        )

        with torch.no_grad():
            carrier.eta.copy_(report_before.projected_eta)
            carrier.project_eta_(q)
        d_after = carrier(q)
        objective_after = 1.0 + 0.5 * (metric * (d_after - target).square()).sum()
        gradient_after = torch.autograd.grad(objective_after, carrier.eta)[0]
        report_after = raw_eta_kkt_residual(
            carrier, q, gradient_after, metric=metric, reference_step=1.0
        )

        torch.testing.assert_close(
            d_after,
            torch.tensor([0.2, 0.65, 1.0, 1.0], dtype=dtype),
            rtol=0.0,
            atol=0.0,
        )
        self.assertLess(float(objective_after.detach()), float(objective_before.detach()))
        self.assertTrue(bool((d_after >= h).all()))
        self.assertTrue(bool((d_after <= 1.0).all()))
        self.assertTrue(bool((tri3_values(d_after - h, connectivity) >= 0.0).all()))
        self.assertTrue(bool((tri3_values(1.0 - d_after, connectivity) >= 0.0).all()))
        self.assertTrue(
            eta_kkt_converged(
                report_after,
                gradient_inf_tolerance=1.0e-12,
                mapping_inf_tolerance=1.0e-12,
            )
        )
        self.assertTrue(bool(report_after.blocked_lower[0]))
        self.assertTrue(bool(report_after.blocked_upper[2]))
        self.assertTrue(bool(report_after.fixed[3]))

    def test_armijo_requires_a_finite_strict_descent_direction(self):
        self.assertTrue(
            armijo_sufficient_decrease(
                trial_value=0.99,
                base_value=1.0,
                directional_derivative=-0.01,
                armijo_c1=1.0e-4,
            )
        )
        self.assertFalse(
            armijo_sufficient_decrease(
                trial_value=1.0,
                base_value=1.0,
                directional_derivative=-0.01,
                armijo_c1=1.0e-4,
            )
        )
        self.assertFalse(
            armijo_sufficient_decrease(
                trial_value=0.99,
                base_value=1.0,
                directional_derivative=0.0,
                armijo_c1=1.0e-4,
            )
        )


if __name__ == "__main__":
    unittest.main()
