from pathlib import Path
import sys

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from prepare_spatial_degradation_reconstruction_dataset import element_core  # noqa: E402
from evaluate_spatial_degradation_reconstruction_gate import (  # noqa: E402
    c86_metrics,
    element_z_to_nodal_damage,
)
from spatial_degradation_reconstruction import (  # noqa: E402
    OneRingDegradationReconstructor,
    PointwiseDegradationReconstructor,
    damage_to_z,
    matched_pointwise_width,
    reconstruct_damage,
    reconstruction_loss,
    target_increment,
    z_to_damage,
)


def test_damage_z_round_trip_and_increment_are_bounded():
    damage = np.array([0.0, 0.1, 0.5, 0.95, 0.999999, 1.0])
    z = damage_to_z(damage)
    recovered = z_to_damage(z)
    assert np.all((0.0 <= z) & (z <= 12.0))
    assert np.allclose(recovered[:-1], damage[:-1], atol=1.0e-10)
    assert recovered[-1] < 1.0
    prior = np.array([0.0, 0.2, 0.8])
    target = np.array([0.1, 0.2, 0.9])
    increment = target_increment(prior, target)
    assert np.all(increment >= 0.0)
    assert increment[1] == 0.0


def test_reconstruction_never_heals_prior():
    prior = torch.tensor([0.0, 0.2, 0.8])
    raw = torch.tensor([-20.0, 0.0, 20.0])
    damage, z = reconstruct_damage(prior, raw)
    assert torch.all(damage >= prior - 1.0e-7)
    assert torch.all((0.0 <= damage) & (damage < 1.0))
    assert torch.all((0.0 <= z) & (z <= 12.0))


def test_reconstruction_projects_observed_core_to_d095():
    prior = torch.zeros(3)
    raw = torch.full((3,), -20.0)
    core = torch.tensor([False, True, False])
    damage, _ = reconstruct_damage(prior, raw, core_mask=core)
    assert damage[1] >= 0.95 - 1.0e-7
    assert damage[0] < 1.0e-6


def test_element_core_keeps_only_left_connected_component():
    coordinates = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [4.0, 0.0]])
    edges = np.array([[0, 1, 1, 2], [1, 0, 2, 1]], dtype=np.int64)
    damage = np.array([1.0, 1.0, 1.0, 1.0])
    core = element_core(damage, edges, coordinates)
    assert core.tolist() == [True, True, True, False]


def test_matched_models_have_same_contract_and_capacity():
    input_dim = 26
    pointwise_width, pointwise_count, graph_count = matched_pointwise_width(
        input_dim, 16
    )
    assert abs(pointwise_count - graph_count) / graph_count <= 0.02
    pointwise = PointwiseDegradationReconstructor(input_dim, pointwise_width)
    graph = OneRingDegradationReconstructor(input_dim, 16)
    features = torch.randn(4, input_dim)
    edge_index = torch.tensor([[0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 2]])
    edge_attr = torch.randn(edge_index.shape[1], 4)
    assert pointwise(features, edge_index, edge_attr).shape == (4,)
    assert graph(features, edge_index, edge_attr).shape == (4,)
    assert torch.sigmoid(pointwise(features)).max() < 0.01
    assert torch.sigmoid(graph(features, edge_index, edge_attr)).max() < 0.01


def test_exact_reconstruction_has_lower_loss_than_perturbed():
    prior = torch.tensor([0.0, 0.2, 0.5, 0.7])
    target = torch.tensor([0.1, 0.3, 0.7, 0.9])
    target_z = damage_to_z(target)
    prior_z = damage_to_z(prior)
    core = torch.tensor([False, False, False, True])
    areas = torch.ones(4)
    edges = torch.tensor([[0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 2]])
    exact = reconstruction_loss(
        target, target_z, target, target_z, prior_z, core, areas, edges
    )
    perturbed_damage = torch.maximum(prior, target - 0.1)
    perturbed = reconstruction_loss(
        perturbed_damage,
        damage_to_z(perturbed_damage),
        target,
        target_z,
        prior_z,
        core,
        areas,
        edges,
    )
    assert torch.isfinite(perturbed.total)
    assert perturbed.total > exact.total


def test_element_to_nodal_mapping_enforces_prior_and_visible_core():
    connectivity = np.array([[0, 1, 2, 3]], dtype=np.int32)
    mapped = element_z_to_nodal_damage(
        np.array([0.1]),
        connectivity,
        np.array([1.0]),
        np.array([0.0, 0.2, 0.0, 0.0]),
        np.array([False, False, True, False]),
    )
    assert mapped[1] >= 0.2 - 1.0e-12
    assert mapped[2] >= 0.95 - 1.0e-12


def test_c86_metrics_exclude_observed_core_from_primary_error():
    target = np.array([0.99, 0.2, 0.3])
    prediction = np.array([0.95, 0.2, 0.3])
    row = c86_metrics(
        "test",
        prediction,
        target,
        np.zeros(3),
        np.array([True, False, False]),
        np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]]),
        np.ones(3),
    )
    assert row["damage_mae"] == 0.0
    assert row["z_mae"] == 0.0
