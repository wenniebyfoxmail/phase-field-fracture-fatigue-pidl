import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_equilibrium_operator import build_graph, graph_to_torch
from s09_q4_quadrature import q4_shape_data
from s09_stage0a_transition import (
    Stage0ATransitionOperator,
    carrara_f,
    fixed_judgement_loss,
    gp_to_node,
    node_to_gp,
    raw_increment_objectives,
    stage0a_objectives,
    support_weights,
)


def fixture(dtype=torch.float64):
    xy_np = np.array([[i / 2, j / 2] for j in range(3) for i in range(3)], dtype=np.float64)
    conn_np = np.array([[0, 1, 4, 3], [1, 2, 5, 4], [3, 4, 7, 6], [4, 5, 8, 7]])
    area = np.array([1, 2, 1, 2, 4, 2, 1, 2, 1], dtype=np.float64) / 16
    graph = graph_to_torch(build_graph(xy_np, conn_np, area, bins=2), "cpu", dtype=dtype)
    conn = torch.as_tensor(conn_np)
    shape, dshape, det = q4_shape_data(graph["xy"], conn)
    d_pre = torch.linspace(0.0, 0.4, len(xy_np), dtype=dtype)
    alpha = torch.full((4, 4), 0.2, dtype=dtype)
    history = torch.stack(
        (torch.full_like(alpha, 0.3), alpha, torch.full_like(alpha, 0.1), carrara_f(alpha)),
        dim=-1,
    )
    path = torch.tensor([0, 0.03125, 0.0625, 0.09375, 0.125, 0], dtype=dtype)
    model = Stage0ATransitionOperator(0.1, [0.2, 0.2, 0.2], [0.1, 0.1], width=8, rank=3).to(dtype)
    return model, graph, conn, shape, dshape, det, d_pre, history, path


def test_q4_messages_preserve_constant_fields_and_support_mass():
    _, graph, conn, shape, _, det, *_ = fixture()
    gp_weight, nodal_weight = support_weights(conn, shape, det, len(graph["xy"]))
    nodes = torch.ones((len(graph["xy"]), 3), dtype=graph["xy"].dtype)
    gp = node_to_gp(nodes, conn, shape)
    torch.testing.assert_close(gp, torch.ones_like(gp))
    back = gp_to_node(gp, conn, shape, gp_weight, nodal_weight)
    torch.testing.assert_close(back, torch.ones_like(back))
    torch.testing.assert_close(nodal_weight.sum(), gp_weight.sum())


def test_frozen_scales_enter_buffers_as_exact_float64_values():
    damage = 0.006896013386826084
    history = [96.63136736963305, 0.00614771012425793, 0.0059082164580187314]
    displacement = [0.00904670012757536, 0.08381964836377313]
    model = Stage0ATransitionOperator(damage, history, displacement, width=8, rank=3)
    assert model.damage_increment_scale.dtype == torch.float64
    assert model.history_increment_scale.dtype == torch.float64
    assert model.displacement_scale.dtype == torch.float64
    assert model.damage_increment_scale.item() == damage
    assert model.history_increment_scale.tolist() == history
    assert model.displacement_scale.tolist() == displacement


def test_zero_heads_preserve_state_and_enforce_peak_boundary():
    model, graph, conn, shape, _, det, d_pre, history, path = fixture()
    out = model(d_pre, history, path, graph, conn, shape, det)
    torch.testing.assert_close(out["d_peak"], d_pre)
    torch.testing.assert_close(out["history_peak"], history)
    y = graph["xy"][:, 1]
    bottom, top = y == y.min(), y == y.max()
    torch.testing.assert_close(out["u_peak"][bottom], torch.zeros((3, 2), dtype=y.dtype))
    torch.testing.assert_close(out["u_peak"][top, 0], torch.zeros(3, dtype=y.dtype))
    torch.testing.assert_close(out["u_peak"][top, 1], torch.full((3,), path[4], dtype=y.dtype))


def test_projected_outputs_obey_damage_alpha_and_carrara_constraints():
    model, graph, conn, shape, _, det, d_pre, history, path = fixture()
    with torch.no_grad():
        model.node_decoder[-1].bias[:] = torch.tensor([-2.0, 0.2, -0.3], dtype=d_pre.dtype)
        model.gp_decoder[-1].bias[:] = torch.tensor([0.1, 0.5, -0.2], dtype=d_pre.dtype)
    out = model(d_pre, history, path, graph, conn, shape, det)
    assert torch.all(out["d_peak"] >= d_pre)
    assert torch.all(out["d_peak"] <= 1)
    assert torch.all(out["history_peak"][..., 1] >= history[..., 1])
    assert torch.all(out["history_peak"][..., 3] <= history[..., 3])
    torch.testing.assert_close(out["history_peak"][..., 3], carrara_f(out["history_peak"][..., 1]))


def test_separate_objectives_and_fixed_judgement_are_finite_and_differentiable():
    model, graph, conn, shape, dshape, det, d_pre, history, path = fixture()
    out = model(d_pre, history, path, graph, conn, shape, det)
    target = {
        "d_peak": (d_pre + 0.01).clamp(max=1),
        "history_peak": history + torch.tensor([0.01, 0.02, 0.01, -0.01], dtype=d_pre.dtype),
        "u_peak": out["u_peak"].detach() + 0.005 * (graph["xy"][:, 1] * (1-graph["xy"][:, 1]))[:, None],
    }
    scales = {
        "d": torch.tensor(0.1, dtype=d_pre.dtype),
        "u": torch.tensor([0.1, 0.1], dtype=d_pre.dtype),
        "history": torch.tensor([0.2, 0.2, 0.2, 0.2], dtype=d_pre.dtype),
    }
    objectives = stage0a_objectives(
        out, target, scales, conn=conn, shape=shape, dshape=dshape, det=det,
        xy=graph["xy"], equilibrium_scale=1.0,
    )
    assert set(objectives) == {"nodal_state", "gp_history", "equilibrium"}
    assert all(torch.isfinite(value) for value in objectives.values())
    judgement = fixed_judgement_loss(out, target, scales)
    torch.testing.assert_close(
        judgement,
        (2 * objectives["nodal_state"] + objectives["gp_history"]) / 3,
    )
    sum(objectives.values()).backward()
    assert model.node_decoder[-1].weight.grad.abs().sum() > 0
    assert model.gp_decoder[-1].weight.grad.abs().sum() > 0


def test_raw_increment_supervision_corrects_negative_projected_proposals():
    model, graph, conn, shape, _, det, d_pre, history, path = fixture()
    with torch.no_grad():
        model.node_decoder[-1].bias[0] = -1
        model.gp_decoder[-1].bias[1] = -1
    out = model(d_pre, history, path, graph, conn, shape, det)
    target_history = history.clone()
    target_history[..., 1] += 0.02
    target_history[..., 3] = carrara_f(target_history[..., 1])
    target = {"d_peak": d_pre + 0.01, "history_peak": target_history}
    losses = raw_increment_objectives(out, target, d_pre, history, model)
    sum(losses.values()).backward()
    assert model.node_decoder[-1].bias.grad[0] < 0
    assert model.gp_decoder[-1].bias.grad[1] < 0


def test_api_rejects_wrong_time_or_support_shapes():
    model, graph, conn, shape, _, det, d_pre, history, path = fixture()
    for bad_path in (path[:-1], torch.cat((path[:-1], torch.tensor([float("nan")])))):
        try:
            model(d_pre, history, bad_path, graph, conn, shape, det)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid path must fail closed")


def test_api_rejects_invalid_prestate_and_area_identity():
    model, graph, conn, shape, _, det, d_pre, history, path = fixture()
    cases = []
    bad_d = d_pre.clone(); bad_d[0] = -0.1
    cases.append((bad_d, history, graph))
    bad_h = history.clone(); bad_h[0, 0, 3] = 0.4
    cases.append((d_pre, bad_h, graph))
    bad_graph = dict(graph); bad_graph["area"] = graph["area"] * 2
    cases.append((d_pre, history, bad_graph))
    for damage, state, candidate_graph in cases:
        try:
            model(damage, state, path, candidate_graph, conn, shape, det)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid causal pre-state must fail closed")
