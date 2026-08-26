from __future__ import annotations

import sys
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from fem_mechanism_operator import StateStatistics  # noqa: E402
from probabilistic_increment_mesh_operator import (  # noqa: E402
    LOG_SCALE_BOUNDS,
    ProbabilisticIncrementMeshOperator,
    conditional_laplace_scale_loss,
    normalized_increment_target,
    normalized_laplace_interval,
)


def statistics() -> StateStatistics:
    return StateStatistics(
        state_mean=torch.zeros(1, 4),
        state_std=torch.ones(1, 4),
        residual_mean=torch.tensor([[0.01, 0.02, -0.01, 0.03]]),
        residual_std=torch.tensor([[0.1, 0.2, 0.1, 0.3]]),
    )


def graph() -> dict[str, torch.Tensor]:
    coordinates = torch.tensor(
        [[0.0, 0.0], [0.3, 0.0], [0.6, 0.0], [0.9, 0.0]], dtype=torch.float32
    )
    edge_index = torch.tensor([[0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 2]])
    delta = coordinates[edge_index[1]] - coordinates[edge_index[0]]
    coarse_delta = torch.tensor([[0.6, 0.0], [-0.6, 0.0]])
    return {
        "coordinates": coordinates,
        "log_area": torch.zeros(4, 1),
        "areas": torch.tensor([1.0, 1.0, 2.0, 2.0]),
        "edge_index": edge_index,
        "edge_attr": torch.cat([delta, delta.abs()], dim=1),
        "cluster_index": torch.tensor([0, 0, 1, 1]),
        "coarse_edge_index": torch.tensor([[0, 1], [1, 0]]),
        "coarse_edge_attr": torch.cat([coarse_delta, coarse_delta.abs()], dim=1),
    }


def history() -> torch.Tensor:
    base = torch.tensor(
        [
            [0.1, 0.2, 1.0, -2.0],
            [0.2, 0.3, 0.9, -1.8],
            [0.3, 0.4, 0.8, -1.6],
            [0.4, 0.5, 0.7, -1.4],
        ]
    )
    return torch.stack(
        [
            base,
            base + torch.tensor([0.01, 0.02, -0.01, 0.03]),
            base + torch.tensor([0.02, 0.04, -0.02, 0.06]),
        ]
    )


def forward_output():
    model = ProbabilisticIncrementMeshOperator(context=3, hidden_dim=16)
    output = model(
        history(), graph(), statistics(), torch.tensor([1.0, 0.0, 1.0, 0.0])
    )
    return model, output


def test_forward_is_finite_bounded_and_preserves_irreversible_channels():
    _, output = forward_output()
    assert output.mean_state.shape == (4, 4)
    assert output.normalized_location.shape == (4, 4)
    assert output.normalized_log_scale.shape == (4, 4)
    assert torch.isfinite(output.mean_state).all()
    assert torch.isfinite(output.normalized_log_scale).all()
    lower, upper = LOG_SCALE_BOUNDS
    assert torch.all(output.normalized_log_scale > lower)
    assert torch.all(output.normalized_log_scale < upper)
    current = history()[-1]
    assert torch.all(output.mean_state[:, 0] >= current[:, 0])
    assert torch.all(output.mean_state[:, 1] >= current[:, 1])
    assert torch.all(output.mean_state[:, 2] <= current[:, 2])


def test_scale_phase_freezes_every_parameter_except_scale_decoder():
    model = ProbabilisticIncrementMeshOperator(context=3, hidden_dim=16)
    model.set_scale_training()
    trainable = {name for name, parameter in model.named_parameters() if parameter.requires_grad}
    assert trainable
    assert all(name.startswith("scale_decoder.") for name in trainable)
    model.set_mean_training()
    frozen = {name for name, parameter in model.named_parameters() if not parameter.requires_grad}
    assert frozen
    assert all(name.startswith("scale_decoder.") for name in frozen)


def test_conditional_scale_loss_detaches_mean_and_trains_scale_only():
    model = ProbabilisticIncrementMeshOperator(context=3, hidden_dim=16)
    model.set_scale_training()
    current = history()[-1]
    target = current + torch.tensor([0.02, 0.03, -0.02, 0.04])
    output = model(
        history(), graph(), statistics(), torch.tensor([1.0, 0.0, 1.0, 0.0])
    )
    loss = conditional_laplace_scale_loss(
        output, current, target, graph()["areas"], statistics()
    )
    assert loss.channel_nll.shape == (4,)
    assert torch.isfinite(loss.total)
    loss.total.backward()
    assert all(
        parameter.grad is not None
        for name, parameter in model.named_parameters()
        if name.startswith("scale_decoder.")
    )
    assert all(
        parameter.grad is None
        for name, parameter in model.named_parameters()
        if not name.startswith("scale_decoder.")
    )


def test_normalized_target_round_trip_and_laplace_90_interval():
    stats = statistics()
    current = history()[-1]
    target = current + torch.tensor([0.02, 0.03, -0.02, 0.04])
    normalized = normalized_increment_target(current, target, stats)
    reconstructed = (
        current + normalized * stats.residual_std + stats.residual_mean
    )
    assert torch.allclose(reconstructed, target)

    _, output = forward_output()
    lower, upper = normalized_laplace_interval(output, 0.90)
    expected_width = 2.0 * torch.log(torch.tensor(10.0)) * torch.exp(
        output.normalized_log_scale
    )
    assert torch.allclose(upper - lower, expected_width)
    with pytest.raises(ValueError, match="strictly"):
        normalized_laplace_interval(output, 1.0)
