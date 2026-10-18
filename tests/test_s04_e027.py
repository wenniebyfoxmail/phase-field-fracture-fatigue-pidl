"""Small deterministic unit checks. No optimizer.step or training-loop entry."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"source"), str(ROOT/"SENS_tensile")]
import s04_e027 as m
from compute_energy import compute_energy
from field_computation import FieldComputation
from run_s04_e027 import execution_admission


def fixture():
    xy = np.array([(x, y) for y in (-.5, -.02, .02, .5) for x in (-.5, 0., .25, .5)])
    conn = np.array([[4*j+i, 4*j+i+1, 4*j+i+5, 4*j+i+4] for j in range(3) for i in range(3)])
    ref = np.column_stack((.02*(.25-xy[:, 1]**2)*xy[:, 0], m.US*(xy[:, 1]+.5), .2+.05*xy[:, 0]))
    return dict(xy=xy, conn=conn, ref=ref, previous=np.full(16, .1), f=np.ones((9, 4)),
                free_u=np.arange(32), free_d=np.arange(2, 16))


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_native_energy_equivalence(self):
        p = m.Problem(fixture()); q = p.ref
        actual = p.parts(*q.unbind(1))[:3]
        native = compute_energy(p.xy, *q.unbind(1), p.previous, p.mat, p.pff,
                    p.w.sum(1), p.conn, f_fatigue=p.f,
                    irreversibility_penalty_cfg={"enable": True, "mode": "fem_gp_q4"})
        for x, y in zip(actual, native):
            torch.testing.assert_close(x, y, atol=1e-12, rtol=1e-12)
        self.assertEqual(p.pff.irrPenalty(), 16875)

    def test_force_matches_energy_difference(self):
        p = m.Problem(fixture()); q = p.ref.clone().requires_grad_(True)
        force = p.force(q)
        eps = 1e-7
        for i, j in ((5, 0), (10, 1)):
            hi, lo = p.ref.clone(), p.ref.clone()
            hi[i, j] += eps; lo[i, j] -= eps
            fd = (p.parts(*hi.unbind(1))[0]-p.parts(*lo.unbind(1))[0])/(2*eps)
            self.assertAlmostEqual(float(fd), float(force[i+j*len(q)]), places=8)

    def test_mechanical_gradient_includes_damage(self):
        p = m.Problem(fixture()); q = p.ref.clone().requires_grad_(True)
        g = torch.autograd.grad(m.mechanical_loss(p, q, .1), q)[0]
        self.assertGreater(float(g[:, 2].abs().max()), 0)
        self.assertTrue(torch.isfinite(g).all())

    def test_field_mapping_matches_existing_class(self):
        model = m.NeuralNet(2, 3, 2, 6, "TrainableReLU", 1.).double()
        xy = torch.tensor(fixture()["xy"], dtype=torch.float64)
        fc = FieldComputation(model, torch.tensor([[-.5, .5], [-.5, .5]], dtype=torch.float64),
                torch.tensor([m.US], dtype=torch.float64), torch.tensor([np.pi/2], dtype=torch.float64),
                alpha_constraint="nonsmooth", williams_dict={"enable": False}, ansatz_dict={"enable": False},
                symmetry_prior=False, exact_bc_dict={"enable": False}, local_patch_dict={"enable": False})
        torch.testing.assert_close(m.fields(model, xy), torch.stack(fc.fieldCalculation(xy), 1), atol=1e-15, rtol=1e-14)

    def test_sampler_and_supervision_no_double_weighting(self):
        p = m.Problem(fixture()); rng = torch.Generator().manual_seed(1)
        ids = p.sample(rng)
        self.assertEqual(len(ids[0]), 2048)
        self.assertTrue(p.zone[ids[1]].all())
        q = p.ref+torch.tensor([m.US, 0., 1.], dtype=torch.float64)
        self.assertAlmostEqual(float(p.supervised(q, ids)), 2., places=12)

    def test_clone_nonempty_adam_without_step(self):
        net = torch.nn.Linear(2, 3).double()
        opt = torch.optim.Adam(net.parameters(), lr=1e-4)
        for p in net.parameters():
            opt.state[p] = dict(step=torch.tensor(1000.), exp_avg=torch.full_like(p, .2), exp_avg_sq=torch.full_like(p, .3))
        rng = torch.Generator().manual_seed(7)
        clone, new_opt, new_rng = m.clone_branch(net, opt, rng)
        for p, q in zip(net.parameters(), clone.parameters()):
            self.assertNotEqual(p.data_ptr(), q.data_ptr())
            torch.testing.assert_close(p, q)
            for key in ("step", "exp_avg", "exp_avg_sq"):
                torch.testing.assert_close(opt.state[p][key], new_opt.state[q][key])
                self.assertNotEqual(opt.state[p][key].data_ptr(), new_opt.state[q][key].data_ptr())
        torch.testing.assert_close(torch.rand(8, generator=rng), torch.rand(8, generator=new_rng))

    def test_physical_objective_is_log_plus_named_weight_regularizer(self):
        p = m.Problem(fixture()); net = torch.nn.Linear(2, 3).double()
        q = m.fields(net, p.xy)
        energy = sum(p.parts(*q.unbind(1))[:3])
        expected = torch.log10(energy)+1e-5*net.weight.square().sum()
        torch.testing.assert_close(m.physical_loss(p, q, net), expected)

    def test_mechanical_normalizer_stops(self):
        p = m.Problem(fixture())
        for value in (0., 1e-13, float("nan")):
            with self.assertRaises(ValueError): m.mechanical_loss(p, p.ref, value)

    def test_decision_na_and_direction(self):
        self.assertIsNone(m.decision({"C": {"active_error": .1}, "S": {"active_error": 0.}})["R_active"])
        self.assertEqual(m.decision({"C": {"active_error": .9}, "S": {"active_error": 1.}})["status"], "DIRECTIONAL_SIGNAL")

    def test_payload_tamper_and_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/"x").write_bytes(b"abc")
            row = dict(relative="x", bytes=3, sha256=hashlib.sha256(b"abc").hexdigest())
            self.assertEqual(m.verify_payload(root, row), root/"x")
            (root/"x").write_bytes(b"abd")
            with self.assertRaises(ValueError): m.verify_payload(root, row)
            row["relative"] = "../x"
            with self.assertRaises(ValueError): m.verify_payload(root, row)

    def test_bad_allowlist_rejected_before_io(self):
        with patch.object(m, "verify_payload", side_effect=AssertionError("must not read")):
            with self.assertRaisesRegex(ValueError, "roles"):
                m.load_reference(Path("/nonexistent"), {"protocol": m.PROTOCOL, "payloads": {"extra": {}}})

    def test_mac_execution_forbidden_before_io(self):
        with patch("run_s04_e027.platform.system", return_value="Darwin"):
            with self.assertRaisesRegex(PermissionError, "Mac"):
                execution_admission({}, {})

    def test_unresolved_initializer_blocks_before_cuda(self):
        with patch("run_s04_e027.platform.system", return_value="Linux"), patch("torch.cuda.is_available", side_effect=AssertionError("no GPU probe")):
            with self.assertRaisesRegex(PermissionError, "unresolved"):
                execution_admission({"initializer": {"sha256": None}}, {})


if __name__ == "__main__":
    unittest.main()
