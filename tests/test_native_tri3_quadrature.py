from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from compute_energy import compute_energy_per_elem, get_psi_plus_per_elem  # noqa: E402
from material_properties import MaterialProperties  # noqa: E402
from model_train import validate_history_storage_for_connectivity  # noqa: E402
from pff_model import PFFModel  # noqa: E402
from tri3_quadrature import tri3_gradient, tri3_interpolate, tri3_shape_data  # noqa: E402
from utils import parse_mesh  # noqa: E402


def _triangle():
    points = torch.tensor(
        [[0.2, -0.1], [2.1, 0.3], [0.4, 1.7]], dtype=torch.float64
    )
    conn = torch.tensor([[0, 1, 2]], dtype=torch.long)
    return points, conn


def test_tri3_order2_point_order_patch_gradient_and_area():
    points, conn = _triangle()
    shape, dshape, weights = tri3_shape_data(points, conn)
    expected_shape = torch.tensor(
        [[2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]],
        dtype=torch.float64,
    )
    torch.testing.assert_close(shape, expected_shape, rtol=0.0, atol=1.0e-15)
    field = 2.5 * points[:, 0] - 1.75 * points[:, 1] + 0.3
    expected_grad = torch.tensor([2.5, -1.75], dtype=torch.float64)
    torch.testing.assert_close(
        tri3_gradient(field, conn, dshape)[0],
        expected_grad.expand(3, 2), rtol=0.0, atol=1.0e-12,
    )
    twice_area = torch.linalg.det(
        torch.stack((points[1] - points[0], points[2] - points[0]), dim=1)
    )
    assert abs(float(weights.sum()) - 0.5 * float(twice_area)) < 1.0e-12
    constants = torch.full((3,), 7.25, dtype=torch.float64)
    torch.testing.assert_close(
        tri3_interpolate(constants, conn, shape),
        torch.full((1, 3), 7.25, dtype=torch.float64),
        rtol=0.0, atol=1.0e-14,
    )


def test_parse_native_t3_abaqus(tmp_path):
    mesh = tmp_path / "one_t3.inp"
    mesh.write_text(
        "*NODE\n1,0,0\n2,1,0\n3,0,1\n"
        "*ELEMENT, TYPE=CPS3\n1,1,2,3\n",
        encoding="utf-8",
    )
    x, y, conn, area = parse_mesh(mesh, gradient_type="numerical")
    assert np.array_equal(conn, np.array([[0, 1, 2]]))
    assert np.array_equal(x, np.array([0.0, 1.0, 0.0]))
    assert np.array_equal(y, np.array([0.0, 0.0, 1.0]))
    assert np.allclose(area, 0.5)


def test_native_tri3_energy_and_gp_history_are_differentiable():
    points, conn = _triangle()
    u = (0.01 * points[:, 0]).clone().requires_grad_(True)
    v = (0.02 * points[:, 1]).clone().requires_grad_(True)
    alpha = torch.tensor([0.1, 0.3, 0.2], dtype=torch.float64, requires_grad=True)
    hist_alpha = torch.zeros(3, dtype=torch.float64)
    area = torch.tensor([1.67], dtype=torch.float64)  # ignored by native GP kernel
    fatigue_gp = torch.tensor([[1.0, 0.9, 0.8]], dtype=torch.float64)
    material = MaterialProperties(1.0, 0.3, 1.0, 0.01)
    model = PFFModel("AT1", "volumetric", 5.0e-3, residual_stiffness=0.0)
    cfg = {
        "enable": True,
        "mode": "fem_gp_tri3",
        "spatial_integration": "native_tri3_gp3",
    }
    e_el, e_d, e_irr = compute_energy_per_elem(
        points, u, v, alpha, hist_alpha, material, model, area, conn,
        f_fatigue=fatigue_gp, irreversibility_penalty_cfg=cfg,
    )
    total = (e_el + e_d + e_irr).sum()
    total.backward()
    assert e_el.shape == e_d.shape == e_irr.shape == (1,)
    assert torch.isfinite(total)
    assert alpha.grad is not None and torch.isfinite(alpha.grad).all()
    active_gp = get_psi_plus_per_elem(
        points, u.detach(), v.detach(), alpha.detach(), material, model, area, conn,
        history_driver_reduction_dict={"enable": True, "mode": "native_tri3_gp3"},
    )
    assert active_gp.shape == (1, 3)
    assert torch.isfinite(active_gp).all()


def test_native_tri3_history_contract_is_arity_and_storage_strict():
    tri3 = torch.tensor([[0, 1, 2]], dtype=torch.long)
    q4 = torch.tensor([[0, 1, 2, 3]], dtype=torch.long)
    cfg = {
        "fatigue_on": True,
        "history_storage": "tri3_gp3",
        "damage_history_storage": "previous_accepted_nodal",
        "history_driver_reduction": {"enable": True, "mode": "native_tri3_gp3"},
    }
    validate_history_storage_for_connectivity(cfg, tri3, "tri3")
    with pytest.raises(ValueError, match="Q4 fatigue requires|requires 3-node connectivity"):
        validate_history_storage_for_connectivity(cfg, q4, "mixed")
