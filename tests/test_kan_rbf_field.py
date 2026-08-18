from __future__ import annotations

import sys
from pathlib import Path

import torch


SOURCE = Path(__file__).resolve().parents[1] / "source"
sys.path.insert(0, str(SOURCE))

from network import KANRBFFieldNet, TopologyKANSingleFrontRBFNet  # noqa: E402


def test_kan_rbf_forward_and_spatial_gradients_are_finite() -> None:
    extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], dtype=torch.float32)
    model = KANRBFFieldNet(2, 3, extrema, kan_width=8, kan_basis=5,
                           rbf_x_centres=9, rbf_y_centres=5)
    points = torch.tensor(
        [[-0.4, 0.0], [0.0, 0.0], [0.25, 0.02], [0.49, -0.01]],
        dtype=torch.float32,
        requires_grad=True,
    )
    output = model(points)
    assert output.shape == (4, 3)
    assert torch.isfinite(output).all()
    gradient = torch.autograd.grad(output.square().sum(), points, create_graph=True)[0]
    assert gradient.shape == points.shape
    assert torch.isfinite(gradient).all()
    output.square().mean().backward()
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())


def test_phase_head_is_localized_and_trainable() -> None:
    extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], dtype=torch.float32)
    model = KANRBFFieldNet(2, 3, extrema, kan_width=8, kan_basis=5,
                           rbf_x_centres=9, rbf_y_centres=5)
    assert model.phase_weight.numel() == 45
    output = model(torch.zeros(2, 2))
    output[:, 2].sum().backward()
    assert model.phase_weight.grad is not None
    assert torch.isfinite(model.phase_weight.grad).all()


def test_topology_features_resolve_crack_side_and_initial_face() -> None:
    extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], dtype=torch.float32)
    model = TopologyKANSingleFrontRBFNet(2, 3, extrema, kan_width=8, kan_basis=5)
    points = torch.tensor([[-0.25, 0.005], [-0.25, -0.005], [0.25, 0.005]])
    features = model.topology_features(model._normalize(points))
    assert features[0, 2] > 0.0 and features[1, 2] < 0.0
    assert features[0, 3] > 0.0 and features[1, 3] < 0.0
    assert abs(features[0, 3]) > abs(features[2, 3])


def test_single_front_phase_is_monotone_and_has_one_symmetric_corridor() -> None:
    extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], dtype=torch.float32)
    model = TopologyKANSingleFrontRBFNet(2, 3, extrema, kan_width=8, kan_basis=5)
    x = torch.linspace(-0.45, 0.45, 101)
    centre = torch.stack([x, torch.zeros_like(x)], dim=1)
    raw = model.phase_raw_field(model._normalize(centre))
    assert torch.all(raw[:-1] >= raw[1:] - 1.0e-7)

    probes = torch.tensor([[-0.25, 0.0], [-0.25, 0.03], [-0.25, -0.03]])
    probe_raw = model.phase_raw_field(model._normalize(probes))
    assert probe_raw[0] > probe_raw[1]
    assert torch.allclose(probe_raw[1], probe_raw[2], atol=1.0e-6)


def test_topology_single_front_forward_and_gradients_are_finite() -> None:
    extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], dtype=torch.float32)
    model = TopologyKANSingleFrontRBFNet(2, 3, extrema, kan_width=8, kan_basis=5)
    points = torch.tensor(
        [[-0.4, 0.0], [0.0, 0.0], [0.25, 0.02], [0.49, -0.01]],
        dtype=torch.float32,
        requires_grad=True,
    )
    output = model(points)
    gradient = torch.autograd.grad(output.square().sum(), points, create_graph=True)[0]
    assert output.shape == (4, 3)
    assert torch.isfinite(output).all()
    assert torch.isfinite(gradient).all()
