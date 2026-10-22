"""Tiny synthetic algebra/QP tests only; no archived mesh/network/producer."""

import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import torch

spec = importlib.util.spec_from_file_location("t3_damage_reference",
    Path(__file__).resolve().parents[1] / "source/t3_damage_reference.py")
ref = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ref
spec.loader.exec_module(ref)

try:
    import osqp
    HAS_OSQP = True
except ImportError:
    HAS_OSQP = False


def fixture():
    return dict(xy=np.array([[0., 0.], [2., 0.], [0., 1.], [2., 2.]]),
        conn=np.array([[0, 1, 2], [1, 3, 2]]), area=np.array([1., 2.]),
        psi_plus=np.array([.7, 1.4]), psi_minus=np.array([.3, .8]),
        f=np.array([.2, .9]), w1=1.3, cw=8/3, l0=.17)


def single(**kwargs):
    args = dict(xy=np.array([[0., 0.], [1., 0.], [0., 1.]]),
        conn=np.array([[0, 1, 2]]), area=np.array([.5]),
        psi_plus=0., psi_minus=.3, f=1., w1=1., cw=8/3, l0=1.)
    args.update(kwargs)
    return ref.assemble_t3_damage(**args)


def load_historical_physics():
    """Load only the three declared modules, never training/mesh/network code."""
    default = (Path(__file__).resolve().parents[3]
        / 'local_archive/experiments/S04-E037/preparation/physics')
    root = Path(os.environ.get('PHYSICS_ROOT', default))
    modules = []
    for name in ('compute_energy', 'material_properties', 'pff_model'):
        path = root / 'source' / (name + '.py')
        if not path.is_file():
            raise AssertionError(f'historical physics missing: {path}; set PHYSICS_ROOT')
        spec = importlib.util.spec_from_file_location('historical_t3_test_' + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return modules


class T3Assembly(unittest.TestCase):
    def test_historical_compute_energy_value_gradient_hessian(self):
        physics, material, models = load_historical_physics()
        a = fixture()
        mat = material.MaterialProperties(mat_E=2., mat_nu=.25, w1=a['w1'], l0=a['l0'])
        pff = models.PFFModel(PFF_model='AT1', se_split='volumetric', residual_stiffness=0.)
        # Positive trace in triangle 0, negative trace in triangle 1: both
        # tensile/deviatoric psi_plus and compressive psi_minus are exercised.
        for dtype in (torch.float64, torch.float32):
            with self.subTest(dtype=dtype):
                xy = torch.tensor(a['xy'], dtype=dtype)
                conn = torch.tensor(a['conn'])
                area = torch.tensor(a['area'], dtype=dtype)
                u = torch.tensor([0., .2, 0., -.5], dtype=dtype)
                v = torch.tensor([0., 0., .1, -.2], dtype=dtype)
                f = torch.tensor(a['f'], dtype=dtype)
                d = torch.tensor([.1, .8, .4, .2], dtype=dtype, requires_grad=True)
                s11, s22, s12, _, _ = physics.gradients(xy, u, v, d, area, conn)
                pm, pp = physics.strain_energy_with_split(
                    s11, s22, s12, torch.ones(len(area), dtype=dtype), mat, pff)
                self.assertGreater(pp.min().item(), 0.)
                self.assertGreater(pm.max().item(), 0.)
                qp = ref.assemble_t3_damage(xy.numpy(), conn.numpy(), area.numpy(),
                    pp.detach().numpy(), pm.detach().numpy(), f.numpy(), mat.w1, 8/3, mat.l0)

                def physical_energy(damage):
                    eel, ed, _ = physics.compute_energy(xy, u, v, damage,
                        torch.zeros_like(damage), mat, pff, area, conn, f_fatigue=f,
                        irreversibility_penalty_cfg={'enable': True, 'mode': 'fem_gp_tri3'})
                    return eel + ed

                energy = physical_energy(d)
                grad, = torch.autograd.grad(energy, d)
                hessian = torch.autograd.functional.hessian(physical_energy, d)
                atol = 1e-13 if dtype == torch.float64 else 1e-6
                rtol = 1e-13 if dtype == torch.float64 else 1e-5
                np.testing.assert_allclose(ref.assembled_energy(qp, d.detach()), energy.item(),
                    rtol=rtol, atol=atol)
                np.testing.assert_allclose(ref.assembled_gradient(qp, d.detach()), grad, atol=atol)
                np.testing.assert_allclose(qp.H.toarray(), hessian, atol=atol)
                check = ref.compare_physics_at_field(qp, d.detach(), energy.item(), grad.numpy())
                self.assertTrue(check['accepted'], check)

    def test_centroid_energy_gradient_hessian_against_torch(self):
        a = fixture()
        qp = ref.assemble_t3_damage(**a)
        xy = torch.tensor(a['xy'], dtype=torch.float64)
        conn = torch.tensor(a['conn'])
        area = torch.tensor(a['area'])
        pp, pm, f = [torch.tensor(a[k]) for k in ('psi_plus', 'psi_minus', 'f')]

        def energy(d):
            local = d[conn]
            mean = local.sum(dim=1) / 3
            x, y = xy[conn, 0], xy[conn, 1]
            gx = ((y[:, 1]-y[:, 2])*local[:, 0] + (y[:, 2]-y[:, 0])*local[:, 1]
                  + (y[:, 0]-y[:, 1])*local[:, 2]) / (2*area)
            gy = ((x[:, 2]-x[:, 1])*local[:, 0] + (x[:, 0]-x[:, 2])*local[:, 1]
                  + (x[:, 1]-x[:, 0])*local[:, 2]) / (2*area)
            return torch.sum(area*((1-mean)**2*pp + pm
                + f*a['w1']/a['cw']*(mean+a['l0']**2*(gx**2+gy**2))))

        d = torch.tensor([.1, .8, .4, .2], dtype=torch.float64, requires_grad=True)
        e = energy(d)
        grad, = torch.autograd.grad(e, d)
        hess = torch.autograd.functional.hessian(energy, d)
        np.testing.assert_allclose(ref.assembled_energy(qp, d.detach()), e.item(), rtol=1e-14)
        np.testing.assert_allclose(ref.assembled_gradient(qp, d.detach()), grad, atol=1e-14)
        np.testing.assert_allclose(qp.H.toarray(), hess, atol=1e-14)
        self.assertGreaterEqual(np.linalg.eigvalsh(qp.H.toarray()).min(), -1e-14)

    def test_one_triangle_analytic_elastic_only(self):
        qp = single(psi_plus=1., psi_minus=.4, f=0.)
        np.testing.assert_allclose(qp.H.toarray(), np.ones((3, 3))/9)
        np.testing.assert_allclose(qp.q, np.full(3, -1/3))
        self.assertAlmostEqual(qp.const, .7)
        self.assertAlmostEqual(ref.assembled_energy(qp, np.ones(3)), .2)

    def test_clockwise_orientation_preserves_energy(self):
        a = fixture(); qp = ref.assemble_t3_damage(**a)
        a['conn'] = a['conn'][:, [0, 2, 1]]
        rev = ref.assemble_t3_damage(**a)
        np.testing.assert_allclose(qp.H.toarray(), rev.H.toarray(), atol=1e-14)
        np.testing.assert_allclose(qp.q, rev.q)

    def test_gp_support_has_nodal_healing_witness(self):
        qp = single(); h = np.array([.5, .2, .2]); d = np.full(3, .4)
        np.testing.assert_allclose(qp.gp.toarray(), ref.GP3_BARYCENTRIC)
        g = ref.damage_constraints(qp, h, 'G'); n = ref.damage_constraints(qp, h, 'N')
        self.assertTrue(np.all(g.A@d >= g.lower-1e-15))
        self.assertTrue(np.all(g.A@d <= g.upper))
        self.assertLess((n.A@d-n.lower).min(), -.09)

    def test_physical_and_history_inputs_are_not_silently_repaired(self):
        for changes in [dict(psi_plus=-1.), dict(psi_minus=-.1), dict(f=1.001),
                        dict(f=float('nan')), dict(area=np.array([0.]))]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                single(**changes)
        qp = single()
        for mode in ('G', 'N'):
            for h in ([.2, .2, 1.000001], [-1e-12, .2, .2]):
                with self.subTest(mode=mode, h=h), self.assertRaises(ValueError):
                    ref.damage_constraints(qp, h, mode)

    def test_full_certificate_and_perturbations(self):
        qp = single(); h = np.full(3, .2)
        c = ref.damage_constraints(qp, h, 'N')
        y = -ref.assembled_gradient(qp, h)
        cert = ref.kkt_certificate(qp, c, h, y)
        self.assertTrue(cert['accepted'], cert)
        self.assertFalse(ref.kkt_certificate(qp, c, h-1e-3, y)['accepted'])
        self.assertFalse(ref.kkt_certificate(qp, c, h, np.zeros(3))['accepted'])
        self.assertFalse(ref.kkt_certificate(qp, c, h, -y)['accepted'])
        c = ref.damage_constraints(qp, h, 'G')
        # Positive dual on an infinite GP upper bound is dual-inadmissible.
        bad_y = np.zeros(c.A.shape[0]); bad_y[-1] = .1
        self.assertGreater(ref.kkt_certificate(qp, c, h, bad_y)['dual_linf'], .09)

    def test_missing_osqp_fails_without_fallback(self):
        with patch.dict(sys.modules, {'osqp': None}):
            with self.assertRaises(ref.MissingOSQPError):
                ref.solve_t3_damage(single(), np.full(3, .2))

    def test_time_cap_cannot_expand(self):
        with self.assertRaises(ValueError):
            ref.solve_t3_damage(single(), np.full(3, .2), time_limit=101.)

    def test_physics_comparison_rejects_wrong_value_or_gradient(self):
        qp = single(); d = np.full(3, .2)
        e, g = ref.assembled_energy(qp, d), ref.assembled_gradient(qp, d)
        self.assertTrue(ref.compare_physics_at_field(qp, d, e, g)['accepted'])
        self.assertFalse(ref.compare_physics_at_field(qp, d, e*1.001, g)['accepted'])
        self.assertFalse(ref.compare_physics_at_field(qp, d, e, g+1e-5)['accepted'])

    @unittest.skipUnless(HAS_OSQP, 'OSQP absent: solver path not validated here')
    def test_osqp_certified_analytic_lower_solution(self):
        qp = single(); h = np.full(3, .2)
        result = ref.solve_t3_damage(qp, h, 'N', time_limit=2.)
        self.assertTrue(result.accepted, result.certificate)
        np.testing.assert_allclose(result.x, h, atol=1e-7)

    @unittest.skipUnless(HAS_OSQP, 'OSQP absent: solver path not validated here')
    def test_osqp_G_can_heal_node_where_N_cannot(self):
        qp = single(l0=10.); h = np.array([.5, .2, .2])
        g = ref.solve_t3_damage(qp, h, 'G', time_limit=2.)
        n = ref.solve_t3_damage(qp, h, 'N', time_limit=2.)
        self.assertTrue(g.accepted, g.certificate); self.assertTrue(n.accepted, n.certificate)
        self.assertLess(g.x[0], h[0]-.05)
        self.assertTrue(np.all(n.x >= h-1e-7))


if __name__ == '__main__':
    unittest.main()
