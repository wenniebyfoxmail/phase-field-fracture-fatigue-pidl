"""Closed-form/analytic fixtures only: no model, mesh, optimiser or archive.

Run: python -m unittest discover -s tests -p test_irreversibility_constraints.py
These tests validate algebra and failure examples, not phase-field performance.
"""

import unittest
import importlib.util
from pathlib import Path

import torch

# The historical source/__init__.py eagerly imports application modules.
# Load this standalone kernel only; never import configuration/training here.
spec = importlib.util.spec_from_file_location(
    "irreversibility_constraints", Path(__file__).resolve().parents[1] / "source/irreversibility_constraints.py")
kernel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kernel)
box_projected_gradient = kernel.box_projected_gradient
phr_inequality_term = kernel.phr_inequality_term
update_inequality_multiplier = kernel.update_inequality_multiplier


def vector(values, grad=False):
    return torch.tensor(values, dtype=torch.float64, requires_grad=grad)


class ConstraintContracts(unittest.TestCase):
    def test_valid_reactions_and_fixed_dof(self):
        # lower reaction positive, upper reaction negative, free derivative zero.
        d = vector([0.2, 1.0, 0.6, 0.7])
        residual = box_projected_gradient(
            d, vector([3.0, -4.0, 0.0, 99.0]),
            vector([0.2, 0.2, 0.2, 0.7]), vector([1.0, 1.0, 1.0, 0.7]), 0.1)
        torch.testing.assert_close(residual, torch.zeros_like(d))

    def test_wrong_reaction_sign_and_infeasibility_are_detected(self):
        residual = box_projected_gradient(
            vector([0.2, 1.0, 0.1]), vector([-2.0, 3.0, 0.0]),
            vector([0.2, 0.2, 0.2]), vector([1.0, 1.0, 1.0]), 0.1)
        torch.testing.assert_close(residual, vector([-2.0, 3.0, -1.0]))

    def test_finite_quadratic_penalty_has_exact_optimum_with_healing(self):
        h, slope, penalty = 0.5, 10.0, 1e6
        d = h - slope / penalty  # stationary point, positive second derivative
        self.assertAlmostEqual(slope + penalty * (d - h), 0.0, places=9)
        self.assertGreater(h - d, 0.0)
        self.assertAlmostEqual(h - d, 1e-5)

    def test_one_shot_clipping_fails_for_coupled_quadratic(self):
        # Unconstrained minimiser (-1,1), clip to (0,1). True constrained
        # minimiser (0,0.5); both obey bounds, only the latter is stationary.
        H = torch.tensor([[2.0, 1.0], [1.0, 2.0]], dtype=torch.float64)
        b = vector([1.0, -1.0])
        lo, hi = vector([0.0, 0.0]), vector([2.0, 2.0])
        clipped, solution = vector([0.0, 1.0]), vector([0.0, 0.5])
        self.assertGreater(box_projected_gradient(clipped, H @ clipped + b, lo, hi).abs().max(), 0)
        torch.testing.assert_close(box_projected_gradient(solution, H @ solution + b, lo, hi), vector([0., 0.]))

    def test_gp_only_feasibility_does_not_imply_nodal_feasibility(self):
        # T3 GP3 interpolation of increments: all three GP values positive.
        increment = vector([-0.1, 0.3, 0.3])
        barycentric = torch.tensor([[4., 1., 1.], [1., 4., 1.], [1., 1., 4.]], dtype=torch.float64) / 6
        self.assertTrue(bool((barycentric @ increment > 0).all()))
        self.assertLess(float(increment.min()), 0.0)

    def test_phr_value_and_gradient_on_active_and_inactive_constraints(self):
        c = vector([0.1, -1.0, 0.0], grad=True)
        multipliers, weights = vector([2.0, 2.0, 3.0]), vector([0.2, 0.3, 0.5])
        loss = phr_inequality_term(c, multipliers, 10.0, weights)
        loss.backward()
        torch.testing.assert_close(c.grad, weights * vector([3.0, 0.0, 3.0]))
        self.assertAlmostEqual(float(loss.detach()), -0.01)

    def test_dual_update_sign_release_and_detach(self):
        c = vector([0.1, -1.0, 0.0], grad=True)
        result = update_inequality_multiplier(c, vector([2.0, 2.0, 3.0]), 10.0)
        torch.testing.assert_close(result, vector([3.0, 0.0, 3.0]))
        self.assertFalse(result.requires_grad)

    def test_lower_bound_multiplier_can_balance_nonzero_physical_slope(self):
        d = vector([0.5], grad=True)
        objective = 10 * d.sum() + phr_inequality_term(0.5 - d, vector([10.0]), 20.0, vector([1.0]))
        objective.backward()
        torch.testing.assert_close(d.grad, vector([0.0]))

    def test_sigmoid_cannot_hold_in_exact_arithmetic_and_floor_refresh_drifts(self):
        h, s = vector([0.2]), torch.sigmoid(vector([0.0]))
        accepted = h + (1 - h) * s
        recomputed = accepted + (1 - accepted) * s
        self.assertGreater(float(accepted - h), 0.0)
        torch.testing.assert_close(recomputed - accepted, (1 - h) * s * (1 - s))
        # Values 0.2 -> 0.6 -> 0.8, with unchanged raw network output.
        torch.testing.assert_close(recomputed, vector([0.8]))

    def test_smooth_exact_hold_can_have_zero_parameter_gradient(self):
        z = vector([0.0], grad=True)
        d = 0.2 + 0.8 * z.square() / (1 + z.square())
        (-d).sum().backward()  # physical field gradient -1 wants damage growth
        torch.testing.assert_close(z.grad, vector([0.0]))
        residual = box_projected_gradient(d, vector([-1.0]), vector([0.2]), vector([1.0]))
        self.assertNotEqual(float(residual.detach()), 0)

    def test_reject_invalid_shapes_nonfinite_and_bounds(self):
        with self.assertRaises(ValueError):
            phr_inequality_term(vector([0.0, 1.0]), vector([1.0]), 1.0, vector([1.0]))
        with self.assertRaises(ValueError):
            phr_inequality_term(vector([float('nan')]), vector([1.0]), 1.0, vector([1.0]))
        with self.assertRaises(ValueError):
            phr_inequality_term(vector([0.0]), vector([-1.0]), 1.0, vector([1.0]))
        with self.assertRaises(ValueError):
            update_inequality_multiplier(vector([0.0]), vector([1.0]), 0.0)
        with self.assertRaises(ValueError):
            box_projected_gradient(vector([1.0]), vector([0.0]), vector([1.1]), vector([1.0]))

    def test_finite_inputs_that_overflow_are_rejected_before_clipping(self):
        for dtype, large in [(torch.float32, 1e30), (torch.float64, 1e200)]:
            with self.subTest(dtype=dtype):
                make = lambda x: torch.tensor([x], dtype=dtype)
                with self.assertRaises(ValueError):
                    phr_inequality_term(make(0.0), make(large), 1.0, make(1.0))
                with self.assertRaises(ValueError):
                    update_inequality_multiplier(make(large), make(large), large)
                with self.assertRaises(ValueError):
                    box_projected_gradient(make(0.5), make(large), make(0.0), make(1.0), large)
        with self.assertRaises(ValueError):
            phr_inequality_term(vector([0.0], grad=True), vector([1e150]), 1.0, vector([1e200]))
        for rho in [1e308, 1e-320]:
            with self.subTest(rho=rho), self.assertRaises(ValueError):
                phr_inequality_term(vector([0.0], grad=True), vector([1.0]), rho, vector([1.0]))


if __name__ == '__main__':
    unittest.main()
