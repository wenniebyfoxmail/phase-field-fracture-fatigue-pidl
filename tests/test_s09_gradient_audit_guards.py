import copy
import sys
from pathlib import Path

import pytest
import torch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from SENS_tensile.run_s09_multiobjective_gradient_audit import (
    audit_losses, checkpoint_step_count, tensor_state_sha256, validate_output_path,
)
from SENS_tensile.run_s09_equilibrium_operator import physics_loss as e004_physics_loss
from source.s09_equilibrium_operator import EquilibriumOperator, area_mse, build_graph, graph_to_torch
from source.s09_fem_physics import boundary, equilibrium
from source.s09_q4_quadrature import q4_shape_data


def test_output_path_is_contained_and_namespaced():
    accepted = Path("/mnt/data2/drtao/wennie/S09-E005-R001_abc")
    assert validate_output_path(accepted) == accepted
    for rejected in (
        Path("/mnt/data2/drtao/wennie-near/S09-E005-R001_abc"),
        Path("/mnt/data2/drtao/wennie/output"),
        Path("/tmp/S09-E005-R001_abc"),
    ):
        with pytest.raises(RuntimeError):
            validate_output_path(rejected)


def test_checkpoint_step_and_no_update_state_hash():
    model = torch.nn.Linear(2, 1)
    before = tensor_state_sha256(model.state_dict())
    loss = model(torch.ones(1, 2)).square().sum()
    torch.autograd.grad(loss, tuple(model.parameters()))
    after = tensor_state_sha256(model.state_dict())
    assert before == after
    checkpoint = {"optimizer": {"state": {0: {"step": torch.tensor(300.)}}}}
    assert checkpoint_step_count(checkpoint) == 300
    wrong = copy.deepcopy(checkpoint)
    wrong["optimizer"]["state"][0]["step"] = torch.tensor(299.)
    with pytest.raises(RuntimeError, match="step-300"):
        checkpoint_step_count(wrong)


def test_audit_losses_match_authoritative_e004_objectives():
    xy = np.array([[i/2, j/2] for j in range(3) for i in range(3)], dtype=np.float64)
    conn_np = np.array([[0,1,4,3], [1,2,5,4], [3,4,7,6], [4,5,8,7]], dtype=np.int64)
    area = np.array([1,2,1,2,4,2,1,2,1], dtype=np.float64) / 16
    graph = graph_to_torch(build_graph(xy, conn_np, area, bins=2), "cpu")
    conn = torch.as_tensor(conn_np)
    shape, dshape, det = q4_shape_data(graph["xy"], conn)
    physics = (conn, shape, dshape, det)
    free = boundary(graph["xy"])
    model = EquilibriumOperator([.1, .2], width=8, rank=2)
    damage = torch.linspace(0, .7, len(xy))
    load = .12
    target = model(damage, load, graph).detach() + .001
    affine = torch.stack((torch.zeros(len(xy)), graph["xy"][:, 1] * load), dim=1)
    affine_force, _ = equilibrium(affine, damage, *physics)
    normalizer = affine_force[free].square().mean()
    prediction, _, data_loss, physics_value = audit_losses(
        model, damage, target, load, graph, physics, free, normalizer)
    e004_prediction, e004_physics = e004_physics_loss(
        model, damage, load, graph, conn, shape, dshape, det, free, normalizer)
    e004_data = area_mse(e004_prediction / load, target / load,
                         model.correction_scale, graph["area"])
    torch.testing.assert_close(prediction, e004_prediction)
    torch.testing.assert_close(data_loss, e004_data)
    torch.testing.assert_close(physics_value, e004_physics)
