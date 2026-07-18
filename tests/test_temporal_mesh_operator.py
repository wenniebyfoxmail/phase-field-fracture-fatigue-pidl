from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from fem_mechanism_operator import StateStatistics  # noqa: E402
from temporal_mesh_operator import (  # noqa: E402
    TEMPORAL_FAMILIES,
    DiagonalSSMTemporal,
    TemporalMeshOperator,
    TransformerTemporal,
    apply_directional_state_update,
    count_parameters,
    match_temporal_width,
    normalized_mesh_features,
)
from train_temporal_mesh_operator import (  # noqa: E402
    apply_observation_reset,
    compute_statistics,
    history_slice,
    training_origins,
)


def tiny_statistics() -> StateStatistics:
    return StateStatistics(
        state_mean=torch.tensor([[0.2, 0.4, 0.8, -3.0]]),
        state_std=torch.tensor([[0.2, 0.3, 0.1, 1.0]]),
        residual_mean=torch.tensor([[0.0, 0.0, 0.0, 0.01]]),
        residual_std=torch.tensor([[0.02, 0.03, 0.01, 0.2]]),
    )


def tiny_graph() -> dict[str, torch.Tensor]:
    coordinates = torch.tensor(
        [[0.0, 0.0], [0.2, 0.0], [0.4, 0.0], [0.6, 0.0], [0.8, 0.0], [1.0, 0.0]]
    )
    src = torch.tensor([0, 1, 1, 2, 2, 3, 3, 4, 4, 5])
    dst = torch.tensor([1, 0, 2, 1, 3, 2, 4, 3, 5, 4])
    edge_index = torch.stack([src, dst])
    delta = coordinates[dst] - coordinates[src]
    edge_attr = torch.cat([delta, delta.abs()], dim=1)
    coarse_edge_index = torch.tensor([[0, 1], [1, 0]])
    coarse_delta = torch.tensor([[0.6, 0.0], [-0.6, 0.0]])
    return {
        "coordinates": coordinates,
        "areas": torch.ones(6),
        "log_area": torch.zeros(6, 1),
        "edge_index": edge_index,
        "edge_attr": edge_attr,
        "cluster_index": torch.tensor([0, 0, 0, 1, 1, 1]),
        "coarse_edge_index": coarse_edge_index,
        "coarse_edge_attr": torch.cat([coarse_delta, coarse_delta.abs()], dim=1),
    }


def tiny_history(length: int = 3) -> torch.Tensor:
    base = torch.tensor(
        [[0.1, 0.2, 0.9, -3.5], [0.15, 0.25, 0.88, -3.2],
         [0.2, 0.3, 0.86, -3.0], [0.25, 0.35, 0.84, -2.8],
         [0.3, 0.4, 0.82, -2.6], [0.35, 0.45, 0.8, -2.4]]
    )
    return torch.stack([base + torch.tensor([0.01 * i, 0.02 * i, -0.01 * i, 0.03 * i]) for i in range(length)])


def test_train_windows_never_cross_c67() -> None:
    for context in (1, 3, 5, 10, 20):
        for rollout_steps in (1, 3):
            origins = training_origins(context, rollout_steps)
            assert min(origins) == context
            assert max(origins) + rollout_steps == 67
            for origin in origins:
                assert origin - context + 1 >= 1
                assert origin + rollout_steps <= 67


def test_history_slice_respects_cycle_numbering() -> None:
    states = torch.arange(1, 90).reshape(89, 1, 1)
    result = history_slice(states, origin_cycle=67, context_length=3)
    assert result[:, 0, 0].tolist() == [65, 66, 67]
    with pytest.raises(ValueError):
        history_slice(states, origin_cycle=2, context_length=3)


def test_normalisation_uses_training_cycles_only() -> None:
    rng = np.random.default_rng(4)
    states = rng.normal(size=(89, 5, 4)).astype(np.float32)
    changed = states.copy()
    changed[67:] = 1.0e8
    first = compute_statistics(states)
    second = compute_statistics(changed)
    for name in ("state_mean", "state_std", "residual_mean", "residual_std"):
        torch.testing.assert_close(getattr(first, name), getattr(second, name))


def test_features_have_no_cycle_or_failure_index() -> None:
    state = tiny_history(1)[0]
    graph = tiny_graph()
    features = normalized_mesh_features(
        state, graph["coordinates"], graph["log_area"], tiny_statistics()
    )
    assert features.shape == (6, 7)
    metadata = torch.tensor([0.25, -0.5])
    with_metadata = normalized_mesh_features(
        state, graph["coordinates"], graph["log_area"], tiny_statistics(), metadata
    )
    assert with_metadata.shape == (6, 9)
    torch.testing.assert_close(with_metadata[:, -2:], metadata.expand(6, 2))


@pytest.mark.parametrize("family", TEMPORAL_FAMILIES)
def test_all_temporal_families_forward_and_backward(family: str) -> None:
    width = 16
    model = TemporalMeshOperator(
        temporal_family=family,
        local_dim=12,
        token_dim=8,
        temporal_width=width,
        local_layers=1,
        coarse_layers=1,
        max_context=5,
        transformer_heads=4,
    )
    prediction = model(tiny_history(), tiny_graph(), tiny_statistics())
    assert prediction.shape == (6, 4)
    prediction.square().mean().backward()
    assert all(parameter.grad is not None for parameter in model.parameters())


def test_directional_decoder_preserves_irreversible_semantics() -> None:
    current = tiny_history(1)[0]
    raw_update = torch.randn_like(current) * 20.0
    prediction = apply_directional_state_update(current, raw_update, tiny_statistics())
    assert torch.all(prediction[:, 0] >= current[:, 0])
    assert torch.all(prediction[:, 0] <= 1.0)
    assert torch.all(prediction[:, 1] >= current[:, 1])
    assert torch.all(prediction[:, 2] <= current[:, 2])
    assert torch.all(prediction[:, 2] >= 0.0)
    assert torch.all(prediction[:, 3] >= -12.0)
    assert torch.all(prediction[:, 3] <= 6.0)


def test_ssm_parallel_and_recurrent_paths_are_equivalent() -> None:
    torch.manual_seed(3)
    module = DiagonalSSMTemporal(token_dim=7, width=11)
    tokens = torch.randn(5, 9, 7)
    projected = module.input(tokens)
    torch.testing.assert_close(
        module.parallel_states(projected),
        module.recurrent_states(projected),
        rtol=1.0e-5,
        atol=1.0e-6,
    )
    torch.testing.assert_close(
        module(tokens, recurrent=False),
        module(tokens, recurrent=True),
        rtol=1.0e-5,
        atol=1.0e-6,
    )


def test_transformer_is_temporal_only_across_coarse_tokens() -> None:
    torch.manual_seed(9)
    module = TransformerTemporal(token_dim=8, width=16, heads=4, max_context=5)
    tokens = torch.randn(3, 5, 8)
    baseline = module(tokens)
    changed = tokens.clone()
    changed[0] += 100.0
    perturbed = module(changed)
    torch.testing.assert_close(baseline[1:], perturbed[1:])
    assert not torch.allclose(baseline[0], perturbed[0])


def test_capacity_matching_is_within_one_percent_for_core_families() -> None:
    kwargs = {
        "metadata_dim": 0,
        "local_dim": 48,
        "token_dim": 48,
        "local_layers": 2,
        "coarse_layers": 1,
        "graph_enabled": True,
        "max_context": 20,
        "transformer_heads": 4,
    }
    for family in TEMPORAL_FAMILIES:
        match = match_temporal_width(
            family,
            target_parameters=329_000,
            tolerance=0.01,
            model_kwargs=kwargs,
            candidate_widths=range(8, 513, 4),
        )
        assert match.relative_error <= 0.01
        assert match.parameters == count_parameters(
            TemporalMeshOperator(
                temporal_family=family,
                temporal_width=match.width,
                **kwargs,
            )
        )


def test_observation_resets_are_explicit() -> None:
    prediction = tiny_history(1)[0]
    observation = prediction + 1.0
    raw = apply_observation_reset(prediction, observation, "raw")
    torch.testing.assert_close(raw[:, :3], prediction[:, :3])
    torch.testing.assert_close(raw[:, 3], observation[:, 3])
    full = apply_observation_reset(prediction, observation, "full")
    torch.testing.assert_close(full, observation)
    with pytest.raises(ValueError):
        apply_observation_reset(prediction, observation, "unknown")
