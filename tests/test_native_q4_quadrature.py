from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from q4_quadrature import q4_gradient, q4_interpolate, q4_shape_data  # noqa: E402
from compute_energy import compute_energy_per_elem, get_psi_plus_per_elem  # noqa: E402
from material_properties import MaterialProperties  # noqa: E402
from pff_model import PFFModel  # noqa: E402
from utils import parse_mesh  # noqa: E402
from model_train import (  # noqa: E402
    validate_history_storage_for_connectivity,
    validate_irreversibility_mode_for_connectivity,
)


def test_q4_linear_patch_gradient_and_area():
    points = torch.tensor(
        [[0.0, 0.0], [2.0, 0.1], [2.2, 1.2], [-0.1, 1.0]],
        dtype=torch.float64,
    )
    conn = torch.tensor([[0, 1, 2, 3]], dtype=torch.long)
    shape, dshape, det_j = q4_shape_data(points, conn)
    field = 2.5 * points[:, 0] - 1.75 * points[:, 1] + 0.3
    grad = q4_gradient(field, conn, dshape)
    expected = torch.tensor([2.5, -1.75], dtype=torch.float64)
    assert torch.max(torch.abs(grad[0] - expected)) < 1.0e-12
    assert torch.all(det_j > 0.0)
    polygon = points.numpy()
    area = 0.5 * abs(np.sum(
        polygon[:, 0] * np.roll(polygon[:, 1], -1)
        - polygon[:, 1] * np.roll(polygon[:, 0], -1)
    ))
    assert abs(float(det_j.sum()) - area) < 1.0e-12
    assert torch.max(torch.abs(shape.sum(dim=1) - 1.0)) < 1.0e-14


def test_q4_interpolation_preserves_constant():
    points = torch.tensor(
        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        dtype=torch.float64,
    )
    conn = torch.tensor([[0, 1, 2, 3]], dtype=torch.long)
    shape, _, _ = q4_shape_data(points, conn)
    values = torch.full((4,), 7.25, dtype=torch.float64)
    assert torch.allclose(
        q4_interpolate(values, conn, shape),
        torch.full((1, 4), 7.25, dtype=torch.float64),
        rtol=0.0,
        atol=1.0e-14,
    )


def test_parse_native_q4_abaqus(tmp_path):
    mesh = tmp_path / "one_q4.inp"
    mesh.write_text(
        "*NODE\n1,0,0\n2,1,0\n3,1,1\n4,0,1\n"
        "*ELEMENT, TYPE=CPS4\n1,1,2,3,4\n",
        encoding="utf-8",
    )
    x, y, conn, area = parse_mesh(mesh, gradient_type="numerical")
    assert np.array_equal(conn, np.array([[0, 1, 2, 3]]))
    assert np.array_equal(x, np.array([0.0, 1.0, 1.0, 0.0]))
    assert np.array_equal(y, np.array([0.0, 0.0, 1.0, 1.0]))
    assert np.allclose(area, 1.0)


def test_native_q4_energy_and_gp_history_shapes_are_differentiable():
    points = torch.tensor(
        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        dtype=torch.float64,
    )
    conn = torch.tensor([[0, 1, 2, 3]], dtype=torch.long)
    u = (0.01 * points[:, 0]).clone().requires_grad_(True)
    v = (0.02 * points[:, 1]).clone().requires_grad_(True)
    alpha = torch.tensor([0.1, 0.2, 0.3, 0.2], dtype=torch.float64, requires_grad=True)
    hist_alpha = torch.zeros(4, dtype=torch.float64)
    area = torch.ones(1, dtype=torch.float64)
    fatigue_gp = torch.tensor([[1.0, 0.9, 0.8, 0.7]], dtype=torch.float64)
    material = MaterialProperties(1.0, 0.3, 1.0, 0.01)
    model = PFFModel("AT1", "volumetric", 5.0e-3, residual_stiffness=0.0)
    e_el, e_d, e_irr = compute_energy_per_elem(
        points, u, v, alpha, hist_alpha, material, model, area, conn,
        f_fatigue=fatigue_gp,
        irreversibility_penalty_cfg={"enable": True, "mode": "fem_gp_q4"},
    )
    total = (e_el + e_d + e_irr).sum()
    total.backward()
    assert e_el.shape == e_d.shape == e_irr.shape == (1,)
    assert torch.isfinite(total)
    assert alpha.grad is not None and torch.isfinite(alpha.grad).all()
    active_gp = get_psi_plus_per_elem(
        points, u.detach(), v.detach(), alpha.detach(), material, model, area, conn
    )
    assert active_gp.shape == (1, 4)
    assert torch.isfinite(active_gp).all()


def test_irreversibility_mode_must_match_mesh_arity():
    q4 = torch.tensor([[0, 1, 2, 3]], dtype=torch.long)
    tri3 = torch.tensor([[0, 1, 2]], dtype=torch.long)
    q4_cfg = {"enable": True, "mode": "fem_gp_q4"}
    tri_cfg = {"enable": True, "mode": "fem_gp_tri3"}
    validate_irreversibility_mode_for_connectivity(q4_cfg, q4, "q4")
    validate_irreversibility_mode_for_connectivity(tri_cfg, tri3, "tri3")
    try:
        validate_irreversibility_mode_for_connectivity(q4_cfg, tri3, "mixed")
    except ValueError as exc:
        assert "does not match 3-node connectivity" in str(exc)
    else:
        raise AssertionError("Q4 penalty mode must be rejected on a T3 mesh")


def test_native_q4_history_contract_accepts_q4_and_rejects_t3():
    q4 = torch.tensor([[0, 1, 2, 3]], dtype=torch.long)
    tri3 = torch.tensor([[0, 1, 2]], dtype=torch.long)
    cfg = {
        "fatigue_on": True,
        "history_storage": "q4_gp4",
        "history_driver_reduction": {"enable": True, "mode": "native_q4_gp4"},
    }
    validate_history_storage_for_connectivity(cfg, q4, "q4")
    try:
        validate_history_storage_for_connectivity(cfg, tri3, "mixed")
    except ValueError as exc:
        assert "requires 4-node connectivity" in str(exc)
    else:
        raise AssertionError("native Q4 GP history must be rejected on a T3 mesh")
