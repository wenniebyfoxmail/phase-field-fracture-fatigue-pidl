"""CPU algebra and energy-equivalence checks for the isolated E040 helper."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

import torch

# Project production runners place ``source/`` itself on sys.path; use the
# same layout rather than importing source.__init__, which imports the legacy
# direct-module construction API.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))

from compute_energy import compute_energy
from feasible_damage import (
    DEFAULT_RAW_INCREMENT_SCALE,
    StateReferencedDamageMap,
    compute_elastic_damage_energy,
    freeze_damage_state,
    require_clamp_min_right_derivative,
    state_referenced_damage,
)
from material_properties import MaterialProperties
from pff_model import PFFModel


class _NoIrreversibilityPFF(PFFModel):
    """Raises if the no-irreversibility helper accidentally queries gamma_ir."""

    def irrPenalty(self):  # noqa: N802 - inherited project API spelling
        raise AssertionError("E_irr must not be constructed in this helper")


class FeasibleDamageTests(unittest.TestCase):
    def test_clamp_min_protocol_selects_right_derivative(self):
        require_clamp_min_right_derivative("cpu")

    def test_callable_map_binds_raw_and_damage_to_one_forward_id(self):
        h = torch.tensor([0.1, 0.4], dtype=torch.float64)
        q_ref = torch.tensor([0.2, -0.3], dtype=torch.float64)
        mapping = StateReferencedDamageMap(h, q_ref)

        q1 = q_ref.clone().requires_grad_()
        d1 = mapping(q1)
        first = mapping.latest()
        self.assertEqual(first.forward_id, 1)
        self.assertIs(first.raw_damage, q1)
        self.assertIs(first.damage, d1)
        self.assertTrue(torch.equal(d1, h))

        q2 = (q_ref + 1.0).requires_grad_()
        d2 = mapping(q2)
        second = mapping.latest()
        self.assertEqual(second.forward_id, 2)
        self.assertIs(second.raw_damage, q2)
        self.assertIs(second.damage, d2)
        self.assertTrue(torch.all(d2 > h))

    def test_callable_map_rejects_nonfinite_raw_head(self):
        mapping = StateReferencedDamageMap(torch.zeros(1), torch.zeros(1))
        with self.assertRaises(FloatingPointError):
            mapping(torch.tensor([float('nan')]))

    def test_reference_state_is_exact_and_frozen(self):
        q_ref = torch.tensor(
            [-3.0, -0.2, 0.0, 2.0], dtype=torch.float64, requires_grad=True
        )
        h = torch.tensor([0.0, 0.2, 0.6, 1.0], dtype=torch.float64, requires_grad=True)
        q = q_ref.detach().clone().requires_grad_()

        d = state_referenced_damage(q, h, q_ref)

        self.assertTrue(torch.equal(d, h.detach()))
        d.sum().backward()
        self.assertIsNone(h.grad)
        self.assertIsNone(q_ref.grad)
        expected = DEFAULT_RAW_INCREMENT_SCALE * (1.0 - h.detach())
        torch.testing.assert_close(q.grad, expected)

    def test_mapping_prevents_recession_and_has_no_upper_overshoot(self):
        h = torch.tensor([0.0, 0.2, 0.6, 0.999, 1.0], dtype=torch.float64)
        q_ref = torch.zeros_like(h)
        q = torch.tensor([-100.0, 0.0, 1.0, 100.0, 100.0], dtype=torch.float64)

        d = state_referenced_damage(q, h, q_ref)

        self.assertTrue(torch.all(d >= h))
        self.assertTrue(torch.all(d <= 1.0))
        self.assertEqual(float(d[0]), float(h[0]))
        self.assertEqual(float(d[1]), float(h[1]))
        self.assertEqual(float(d[-1]), 1.0)

    def test_frozen_state_is_detached_and_storage_independent(self):
        h = torch.tensor([0.1, 0.2], requires_grad=True)
        q = torch.tensor([0.3, 0.4], requires_grad=True)
        h_step, q_step = freeze_damage_state(h, q)

        self.assertFalse(h_step.requires_grad)
        self.assertFalse(q_step.requires_grad)
        self.assertNotEqual(h.data_ptr(), h_step.data_ptr())
        self.assertNotEqual(q.data_ptr(), q_step.data_ptr())

    def test_elastic_damage_energy_matches_standard_components_and_gradients(self):
        dtype = torch.float64
        inp = torch.tensor(
            [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=dtype
        )
        conn = torch.tensor([[0, 1, 2], [1, 3, 2]], dtype=torch.long)
        # The project stores twice the geometric triangle area for numerical gradients.
        area = torch.tensor([1.0, 1.0], dtype=dtype)
        u0 = torch.tensor([0.0, 0.02, -0.01, 0.01], dtype=dtype)
        v0 = torch.tensor([0.0, -0.01, 0.03, 0.02], dtype=dtype)
        alpha0 = torch.tensor([0.05, 0.1, 0.2, 0.15], dtype=dtype)
        history = torch.tensor([0.04, 0.11, 0.18, 0.12], dtype=dtype)
        fatigue = torch.tensor([0.9, 0.7], dtype=dtype)
        pff = PFFModel('AT1', 'volumetric', torch.tensor(5e-3, dtype=dtype))
        mat = MaterialProperties(
            torch.tensor(1.0, dtype=dtype),
            torch.tensor(0.3, dtype=dtype),
            torch.tensor(1.0, dtype=dtype),
            torch.tensor(0.01, dtype=dtype),
        )

        u_std, v_std, alpha_std = u0.clone().requires_grad_(), v0.clone().requires_grad_(), alpha0.clone().requires_grad_()
        standard_el, standard_d, _ = compute_energy(
            inp, u_std, v_std, alpha_std, history, mat, pff, area, conn, f_fatigue=fatigue
        )
        standard_grads = torch.autograd.grad(standard_el + standard_d, (u_std, v_std, alpha_std))

        u_new, v_new, alpha_new = u0.clone().requires_grad_(), v0.clone().requires_grad_(), alpha0.clone().requires_grad_()
        direct_el, direct_d = compute_elastic_damage_energy(
            inp, u_new, v_new, alpha_new, mat, pff, area, conn, f_fatigue=fatigue
        )
        direct_grads = torch.autograd.grad(direct_el + direct_d, (u_new, v_new, alpha_new))

        torch.testing.assert_close(direct_el, standard_el, rtol=0.0, atol=0.0)
        torch.testing.assert_close(direct_d, standard_d, rtol=0.0, atol=0.0)
        for got, expected in zip(direct_grads, standard_grads, strict=True):
            torch.testing.assert_close(got, expected, rtol=0.0, atol=0.0)

    def test_energy_helper_never_queries_irreversibility_penalty(self):
        dtype = torch.float64
        inp = torch.tensor([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=dtype)
        conn = torch.tensor([[0, 1, 2]], dtype=torch.long)
        area = torch.tensor([1.0], dtype=dtype)
        u = torch.tensor([0.0, 0.1, 0.0], dtype=dtype, requires_grad=True)
        v = torch.tensor([0.0, 0.0, 0.1], dtype=dtype, requires_grad=True)
        alpha = torch.tensor([0.1, 0.2, 0.3], dtype=dtype, requires_grad=True)
        pff = _NoIrreversibilityPFF('AT1', 'volumetric', torch.tensor(5e-3, dtype=dtype))
        mat = MaterialProperties(
            torch.tensor(1.0, dtype=dtype),
            torch.tensor(0.3, dtype=dtype),
            torch.tensor(1.0, dtype=dtype),
            torch.tensor(0.01, dtype=dtype),
        )

        e_el, e_d = compute_elastic_damage_energy(inp, u, v, alpha, mat, pff, area, conn)
        (e_el + e_d).backward()
        self.assertIsNotNone(alpha.grad)

    def test_energy_aggregation_options_match_standard_components(self):
        dtype = torch.float64
        inp = torch.tensor(
            [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=dtype
        )
        conn = torch.tensor([[0, 1, 2], [1, 3, 2]], dtype=torch.long)
        area = torch.tensor([1.0, 1.0], dtype=dtype)
        u = torch.tensor([0.0, 0.02, -0.01, 0.01], dtype=dtype, requires_grad=True)
        v = torch.tensor([0.0, -0.01, 0.03, 0.02], dtype=dtype, requires_grad=True)
        alpha = torch.tensor([0.05, 0.1, 0.2, 0.15], dtype=dtype, requires_grad=True)
        history = torch.tensor([0.04, 0.11, 0.18, 0.12], dtype=dtype)
        pff = PFFModel('AT1', 'volumetric', torch.tensor(5e-3, dtype=dtype))
        mat = MaterialProperties(
            torch.tensor(1.0, dtype=dtype),
            torch.tensor(0.3, dtype=dtype),
            torch.tensor(1.0, dtype=dtype),
            torch.tensor(0.01, dtype=dtype),
        )

        variants = (
            dict(element_mask=torch.tensor([1.0, 0.0], dtype=dtype)),
            dict(
                element_subset=torch.tensor([1], dtype=torch.long),
                importance_weights=torch.tensor([1.7], dtype=dtype),
            ),
            dict(crack_tip_weights=torch.tensor([0.5, 2.0], dtype=dtype)),
            dict(g_stiffness_override=torch.tensor([0.8, 0.6], dtype=dtype)),
        )
        for kwargs in variants:
            standard_el, standard_d, _ = compute_energy(
                inp, u, v, alpha, history, mat, pff, area, conn, **kwargs
            )
            direct_el, direct_d = compute_elastic_damage_energy(
                inp, u, v, alpha, mat, pff, area, conn, **kwargs
            )
            torch.testing.assert_close(direct_el, standard_el, rtol=0.0, atol=0.0)
            torch.testing.assert_close(direct_d, standard_d, rtol=0.0, atol=0.0)


if __name__ == '__main__':
    unittest.main()
