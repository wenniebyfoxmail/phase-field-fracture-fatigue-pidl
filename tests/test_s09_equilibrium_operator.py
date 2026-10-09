import copy
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_equilibrium_operator import (
    EquilibriumOperator, build_graph, correction_scale, graph_to_torch, weighted_l2,
)
from s09_fem_physics import boundary, equilibrium
from s09_q4_quadrature import q4_shape_data


def mesh():
    xy = np.array([[i/2, j/2] for j in range(3) for i in range(3)], dtype=np.float64)
    conn = np.array([[0,1,4,3], [1,2,5,4], [3,4,7,6], [4,5,8,7]], dtype=np.int64)
    area = np.array([1,2,1,2,4,2,1,2,1], dtype=np.float64) / 16
    return xy, conn, area


def test_graph_integral_weights_and_hard_boundary():
    xy, conn, area = mesh()
    graph_np = build_graph(xy, conn, area, bins=2)
    incoming = np.zeros(len(xy))
    np.add.at(incoming, graph_np["edges"][1], graph_np["weight"])
    np.testing.assert_allclose(incoming, 1.0)
    graph = graph_to_torch(graph_np, "cpu", dtype=torch.float64)
    model = EquilibriumOperator([.1, .1], width=8, rank=3).double()
    damage = torch.linspace(0, .8, len(xy), dtype=torch.float64)
    prediction = model(damage, .12, graph)
    bottom = torch.isclose(graph["xy"][:, 1], graph["xy"][:, 1].min())
    top = torch.isclose(graph["xy"][:, 1], graph["xy"][:, 1].max())
    torch.testing.assert_close(prediction[bottom], torch.zeros((3,2), dtype=torch.float64))
    torch.testing.assert_close(prediction[top, 0], torch.zeros(3, dtype=torch.float64))
    torch.testing.assert_close(prediction[top, 1], torch.full((3,), .12, dtype=torch.float64))


def test_physics_gradient_reaches_zero_initialized_decoder():
    xy, conn, area = mesh()
    graph = graph_to_torch(build_graph(xy, conn, area, bins=2), "cpu", dtype=torch.float64)
    model = EquilibriumOperator([.1, .1], width=8, rank=3).double()
    damage = graph["xy"][:, 0] * .6
    prediction = model(damage, .12, graph)
    connectivity = torch.as_tensor(conn)
    shape, derivative, det = q4_shape_data(graph["xy"], connectivity)
    force, _ = equilibrium(prediction, damage, connectivity, shape, derivative, det)
    force[boundary(graph["xy"])].square().mean().backward()
    assert model.decoder[-1].weight.grad.abs().sum() > 0


def test_matched_clones_and_weighted_metric():
    model = EquilibriumOperator([.2, .3], width=8, rank=2)
    clone = EquilibriumOperator([.2, .3], width=8, rank=2)
    clone.load_state_dict(copy.deepcopy(model.state_dict()))
    for left, right in zip(model.parameters(), clone.parameters()):
        torch.testing.assert_close(left, right)
    prediction = torch.tensor([[1., 0.], [0., 2.]])
    target = torch.zeros_like(prediction)
    area = torch.tensor([1., 3.])
    torch.testing.assert_close(weighted_l2(prediction, target, area), torch.sqrt(torch.tensor(13.)))


def test_correction_scale_uses_normalized_displacement():
    xy, _, area = mesh()
    t = xy[:, 1]
    base = np.column_stack((np.zeros(len(xy)), t))
    correction = np.column_stack((np.full(len(xy), .2), np.full(len(xy), -.3)))
    loads = np.array([.1, .2])
    normalized = np.stack((base + correction, base - correction))
    u = normalized * loads[:, None, None]
    np.testing.assert_allclose(correction_scale(u, loads, xy, area), [.2, .3])
