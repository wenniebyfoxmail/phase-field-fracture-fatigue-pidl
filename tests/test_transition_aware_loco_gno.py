from __future__ import annotations

import sys
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from fem_mechanism_operator import StateStatistics  # noqa: E402
from train_transition_aware_loco_gno import (  # noqa: E402
    EXPECTED_DATASET_MANIFEST_SHA256,
    GRAPH_FEATURE_KEYS,
    PRIMARY_WARNING_THRESHOLD,
    Window,
    build_training_windows,
    choose_balanced_window,
    load_and_verify_matrix_lock,
    load_graph,
    retrospective_warning_origins,
    sha256_file,
    trajectory_metadata,
    transition_target,
    verify_hash_manifest,
)
from transition_aware_mesh_operator import (  # noqa: E402
    TransitionAwareMeshOperator,
    supervised_transition_loss,
    transition_node_features,
)


def statistics() -> StateStatistics:
    return StateStatistics(
        state_mean=torch.zeros(1, 4),
        state_std=torch.ones(1, 4),
        residual_mean=torch.zeros(1, 4),
        residual_std=torch.ones(1, 4),
    )


def graph() -> dict[str, torch.Tensor]:
    coordinates = torch.tensor(
        [[0.0, 0.0], [0.3, 0.0], [0.6, 0.0], [0.9, 0.0]], dtype=torch.float32
    )
    edge_index = torch.tensor([[0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 2]])
    delta = coordinates[edge_index[1]] - coordinates[edge_index[0]]
    edge_attr = torch.cat([delta, delta.abs()], dim=1)
    coarse_delta = torch.tensor([[0.6, 0.0], [-0.6, 0.0]])
    return {
        "coordinates": coordinates,
        "log_area": torch.zeros(4, 1),
        "areas": torch.tensor([1.0, 1.0, 2.0, 2.0]),
        "edge_index": edge_index,
        "edge_attr": edge_attr,
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
    return torch.stack([base, base + torch.tensor([0.01, 0.02, -0.01, 0.03]), base + torch.tensor([0.02, 0.04, -0.02, 0.06])])


def fake_item(name: str, length: int, first_hit: int) -> dict:
    return {
        "trajectory_id": name,
        "states": torch.zeros(length, 4, 4),
        "first_hit": first_hit,
    }


def test_features_exclude_cycle_and_event_information():
    features = transition_node_features(
        history(), graph(), statistics(), torch.tensor([1.0, 0.0, 1.0, 0.0])
    )
    assert features.shape == (4, 19)
    # 12 state + 2 coordinates + 1 area + exactly 4 declared trajectory flags.
    assert features.shape[1] == 3 * 4 + 2 + 1 + 4


def project_root() -> Path:
    return ROOT.parents[2]


def frozen_dataset_root() -> Path:
    return (
        project_root()
        / "local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701"
        / "analysis/factorial_loco_temporal_dataset_20260729"
    )


def test_real_dataset_and_matrix_lock_are_frozen():
    data_root = frozen_dataset_root()
    verify_hash_manifest(data_root)
    assert sha256_file(data_root / "RUN_MANIFEST.json") == EXPECTED_DATASET_MANIFEST_SHA256
    lock = load_and_verify_matrix_lock(
        ROOT / "docs/experiments/at1_fatigue_mesh_pino_d1_matrix_lock_20260826.json"
    )
    assert lock["evaluation"]["transition_score_threshold"] == PRIMARY_WARNING_THRESHOLD
    assert lock["qualification_boundary"]["teacher_qualified"] is False
    assert lock["qualification_boundary"]["damage_fixed_point_gate"] == "fail"


def test_graph_loader_ignores_duplicate_state_payload():
    loaded, _, ignored = load_graph(frozen_dataset_root() / "graph.npz", torch.device("cpu"))
    assert set(loaded) == set(GRAPH_FEATURE_KEYS)
    assert "states" in ignored
    assert "trajectory_id" in ignored


def test_retrospective_warning_contract_is_exactly_nine_rows():
    first_hit = 83
    rows = [
        target
        for origin in retrospective_warning_origins(first_hit)
        for target in range(origin + 1, origin + 4)
    ]
    assert len(rows) == 9
    assert sum(target < first_hit for target in rows) == 3
    assert sum(target >= first_hit for target in rows) == 6


def test_transition_aware_operator_forward_backward_and_capacity():
    model = TransitionAwareMeshOperator(context=3, hidden_dim=96)
    prediction, logit = model(
        history(), graph(), statistics(), torch.tensor([1.0, 0.0, 1.0, 0.0])
    )
    assert prediction.shape == (4, 4)
    assert logit.shape == ()
    (prediction.square().mean() + logit.square()).backward()
    assert all(parameter.grad is not None for parameter in model.parameters())
    assert 250_000 <= sum(parameter.numel() for parameter in model.parameters()) <= 450_000


def test_balanced_windows_use_training_first_hits_only():
    items = [
        fake_item("factorial_hard_5step_u012", 86, 83),
        fake_item("factorial_hard_8step_u012", 89, 86),
        fake_item("factorial_soft_5step_u012", 87, 84),
    ]
    positive, negative = build_training_windows(items)
    assert positive and negative
    for window in positive:
        item = items[window.trajectory_index]
        targets = range(window.origin_cycle + 1, window.origin_cycle + 4)
        assert any(cycle >= item["first_hit"] for cycle in targets)
    for window in negative:
        item = items[window.trajectory_index]
        targets = range(window.origin_cycle + 1, window.origin_cycle + 4)
        assert all(cycle < item["first_hit"] for cycle in targets)


def test_sampler_alternates_transition_and_ordinary_buckets():
    positive = [Window(0, 80, True)]
    negative = [Window(0, 20, False)]
    import random

    rng = random.Random(1)
    assert choose_balanced_window(positive, negative, 1, rng).contains_transition
    assert not choose_balanced_window(positive, negative, 2, rng).contains_transition


def test_transition_label_and_supervised_loss_have_no_physics_term():
    assert transition_target(82, 83, torch.device("cpu")).item() == 0.0
    assert transition_target(83, 83, torch.device("cpu")).item() == 1.0
    result = supervised_transition_loss(
        torch.tensor(2.0, requires_grad=True),
        torch.tensor(0.0, requires_grad=True),
        torch.tensor(1.0),
        transition_weight=0.25,
    )
    assert set(result.__dict__) == {"total", "field", "transition"}
    assert float(result.total.detach()) == pytest.approx(2.0 + 0.25 * 0.69314718)


@pytest.mark.parametrize(
    ("trajectory_id", "expected"),
    [
        ("factorial_hard_5step_u012", [1, 0, 1, 0]),
        ("factorial_soft_8step_u012", [0, 1, 0, 1]),
    ],
)
def test_only_declared_factorial_metadata_is_decoded(trajectory_id, expected):
    assert trajectory_metadata(trajectory_id, torch.device("cpu")).tolist() == expected
