from pathlib import Path
import sys

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from fem_mechanism_operator import (  # noqa: E402
    MultiScaleMeshResidualOperator,
    PointwiseResidualOperator,
    StateStatistics,
    apply_state_constraints,
    derived_active_log10,
    mechanism_loss,
    normalized_node_features,
)
from prepare_fem_mechanism_operator_dataset import (  # noqa: E402
    coarse_graph,
    edge_attributes,
    quad_adjacency,
    quad_geometry,
)
from train_fem_mechanism_mesh_operator import (  # noqa: E402
    training_window_starts,
    validate_dataset_scope,
)


def statistics() -> StateStatistics:
    return StateStatistics(
        state_mean=torch.zeros(1, 4),
        state_std=torch.ones(1, 4),
        residual_mean=torch.zeros(1, 4),
        residual_std=torch.ones(1, 4),
    )


def small_graph():
    points = np.array(
        [[0, 0, 0], [1, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0], [2, 1, 0]],
        dtype=float,
    )
    connectivity = np.array([[0, 1, 4, 3], [1, 2, 5, 4]], dtype=np.int64)
    centroids, areas = quad_geometry(points, connectivity)
    coords = 2.0 * (centroids - centroids.min(0)) / np.maximum(np.ptp(centroids, axis=0), 1.0) - 1.0
    edges = quad_adjacency(connectivity)
    attrs = edge_attributes(coords, areas, edges)
    clusters, coarse_edges, coarse_attrs = coarse_graph(coords, areas, edges, bins=2)
    return coords, areas, edges, attrs, clusters, coarse_edges, coarse_attrs


def test_quad_graph_uses_shared_edges_not_shared_corners():
    _, areas, edges, _, _, _, _ = small_graph()
    assert np.allclose(areas, 1.0)
    assert {tuple(edge) for edge in edges.T} == {(0, 1), (1, 0)}


def test_training_windows_never_touch_masked_audit_cycles():
    starts = training_window_starts(rollout_steps=3)
    assert starts
    for start in starts:
        assert set(range(start, start + 4)).isdisjoint({20, 40})
        assert start + 3 <= 67


def test_state_constraints_preserve_irreversibility_and_bounds():
    current = torch.tensor([[0.6, 0.8, 0.7, -3.0], [0.2, 0.1, 0.9, -2.0]])
    residual = torch.tensor([[-1.0, -1.0, 1.0, 20.0], [1.0, 1.0, -1.0, -20.0]])
    result = apply_state_constraints(current, residual, statistics())
    assert torch.all(result[:, 0] >= current[:, 0])
    assert torch.all(result[:, 1] >= current[:, 1])
    assert torch.all(result[:, 2] <= current[:, 2])
    assert torch.all((0.0 <= result[:, 0]) & (result[:, 0] <= 1.0))
    assert torch.all((0.0 <= result[:, 2]) & (result[:, 2] <= 1.0))
    assert torch.all((result[:, 3] >= -12.0) & (result[:, 3] <= 6.0))


def test_derived_active_uses_eta0_damage_degradation():
    state = torch.tensor([[0.0, 0.0, 1.0, -2.0], [0.5, 0.0, 1.0, -2.0]])
    active = derived_active_log10(state)
    assert torch.allclose(active[0], torch.tensor(-2.0))
    expected = active.new_tensor(-2.0 + 2.0 * np.log10(0.5))
    assert torch.allclose(active[1], expected)


def test_pointwise_and_multiscale_contract_and_backward():
    coords, areas, edges, attrs, clusters, coarse_edges, coarse_attrs = small_graph()
    current = torch.tensor([[0.1, 0.2, 1.0, -2.0], [0.2, 0.3, 0.9, -1.5]])
    features = normalized_node_features(
        current,
        torch.tensor(coords, dtype=torch.float32),
        torch.log(torch.tensor(areas, dtype=torch.float32))[:, None],
        2,
        statistics(),
    )
    graph_args = (
        torch.tensor(edges),
        torch.tensor(attrs, dtype=torch.float32),
        torch.tensor(clusters),
        torch.tensor(coarse_edges),
        torch.tensor(coarse_attrs, dtype=torch.float32),
    )
    models = [
        PointwiseResidualOperator(features.shape[1], hidden_dim=12),
        MultiScaleMeshResidualOperator(
            features.shape[1], hidden_dim=12, local_layers=1, coarse_layers=1
        ),
    ]
    for model in models:
        output = model(features, *graph_args)
        assert output.shape == (2, 4)
        output.square().mean().backward()
        assert all(parameter.grad is not None for parameter in model.parameters())


def test_mechanism_loss_is_finite_and_rewards_exact_target():
    _, areas, edges, _, _, _, _ = small_graph()
    target = torch.tensor([[0.1, 0.2, 1.0, -2.0], [0.2, 0.3, 0.9, -1.5]])
    exact, _ = mechanism_loss(
        target, target, torch.tensor(areas), torch.tensor(edges),
    )
    perturbed, parts = mechanism_loss(
        target + torch.tensor([[0.05, 0.02, -0.03, 0.2], [0.02, 0.01, -0.01, -0.1]]),
        target,
        torch.tensor(areas),
        torch.tensor(edges),
    )
    assert torch.isfinite(perturbed)
    assert perturbed > exact
    assert set(parts) == {"state", "active", "support", "gradient", "total"}


def test_single_trajectory_dataset_scope_requires_explicit_provenance():
    valid = {
        "trajectory_id": np.asarray("fem_c89"),
        "physics_family": np.asarray("strict_reverseBC_softHist0"),
        "trajectory_count": np.asarray(1),
    }
    assert validate_dataset_scope(valid) == ("fem_c89", "strict_reverseBC_softHist0")
    with np.testing.assert_raises_regex(ValueError, "provenance/scope"):
        validate_dataset_scope({"trajectory_count": np.asarray(1)})
    invalid_count = {**valid, "trajectory_count": np.asarray(3)}
    with np.testing.assert_raises_regex(ValueError, "exactly one trajectory"):
        validate_dataset_scope(invalid_count)
