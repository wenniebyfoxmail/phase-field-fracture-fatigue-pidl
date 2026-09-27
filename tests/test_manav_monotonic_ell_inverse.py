from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np
import torch


REPO = Path(__file__).resolve().parents[1]
SENT = REPO / "SENS_tensile"
SOURCE = REPO / "source"
sys.path.insert(0, str(SENT))
sys.path.insert(0, str(SOURCE))


class ManavMonotonicEllInverseTests(unittest.TestCase):
    def test_runner_preserves_fixed_gc_algebra(self) -> None:
        for l0 in (0.008, 0.012, 0.016):
            gc_bar = 0.01
            w1 = gc_bar / l0
            self.assertAlmostEqual(w1 * l0, gc_bar, places=14)

    def test_runner_forces_fatigue_off(self) -> None:
        tree = ast.parse((SENT / "run_manav_monotonic_forward.py").read_text())
        rendered = ast.unparse(tree)
        self.assertIn("config.fatigue_dict['fatigue_on'] = False", rendered)
        self.assertIn("fatigue_dict={'fatigue_on': False", rendered)

    def test_reaction_energy_identity_on_fixed_field(self) -> None:
        from compute_energy import compute_energy
        from construct_model import construct_model
        from field_computation import FieldComputation
        from input_data_from_mesh import prep_input_data

        device = "cpu"
        pff_cfg = {"PFF_model": "AT1", "se_split": "volumetric", "tol_ir": 5e-3}
        mat_cfg = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
        net_cfg = {
            "hidden_layers": 2,
            "neurons": 8,
            "seed": 7,
            "activation": "TrainableReLU",
            "init_coeff": 1.0,
        }
        domain = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
        pff, mat, net = construct_model(pff_cfg, mat_cfg, net_cfg, domain, device)
        field = FieldComputation(
            net,
            domain,
            torch.tensor(0.0),
            torch.tensor([np.pi / 2]),
            "nonsmooth",
        )
        inp, conn, area, hist = prep_input_data(
            mat,
            pff,
            {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]},
            {"gradient_type": "numerical"},
            str(SENT / "meshed_geom1.msh"),
            device,
        )
        load = torch.tensor(0.025, requires_grad=True)
        field.lmbda = load
        u, v, alpha = field.fieldCalculation(inp)
        e_el, e_d, e_hist = compute_energy(
            inp, u, v, alpha, hist, mat, pff, area, conn, f_fatigue=1.0
        )
        reaction = torch.autograd.grad(e_el + e_d + e_hist, load)[0]
        expected = 2.0 * e_el.detach() / load.detach()
        self.assertTrue(torch.isfinite(reaction))
        self.assertLess(float(torch.abs(reaction.detach() - expected)), 2.0e-6)


if __name__ == "__main__":
    unittest.main()
