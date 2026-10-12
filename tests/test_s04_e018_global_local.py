"""Nontraining mathematical/interface checks for the frozen E018 representation."""
import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).parents[1] / "SENS_tensile"))
from s04_e018_global_local import (PARAMETER_COUNT, US, build_model,
                                   compact_window, damage_geometry)


@pytest.fixture
def geometry():
    return damage_geometry(np.array([[-.2, -.1], [.2, .1], [.4, .3]]),
                           np.array([.2, 1., 0.]), np.array([.3, .4, .3]))


def test_exact_counts_initialization_pairing_and_caller_state(geometry):
    dtype = torch.get_default_dtype()
    before = torch.random.get_rng_state().clone()
    control = build_model(7, "control", geometry)
    local = build_model(7, "localized", geometry)
    assert torch.equal(before, torch.random.get_rng_state())
    assert torch.get_default_dtype() == dtype
    assert sum(p.numel() for p in control.parameters()) == PARAMETER_COUNT
    for (name, value), (other_name, other_value) in zip(control.named_parameters(), local.named_parameters()):
        assert name == other_name
        assert value.dtype == torch.float64
        assert torch.equal(value, other_value)
    assert control.global_branch.name_activation == "TrainableTanh"
    assert local.local_branch.name_activation == "TrainableReLU"


@pytest.mark.parametrize("arm", ["control", "localized"])
def test_normalized_raw_interface_and_exact_bc(geometry, arm):
    model = build_model(7, arm, geometry)
    xy = torch.tensor([[-.4, -.5], [.3, .5], [.0, .0]], dtype=torch.float64)
    with torch.no_grad():
        torch.testing.assert_close(model(2 * xy), model.raw_physical(xy), rtol=0, atol=0)
        uv = model.physical_uv(xy)
    assert torch.equal(uv[:2], torch.tensor([[0., 0.], [0., US]], dtype=torch.float64))


def test_damage_coverage_background_support_and_zero_width_core():
    xy = np.array([[.0, .0], [.0, .1], [.01, .01], [.4, .4]])
    damage = np.array([.2, .9, .1, 0.])
    g = damage_geometry(xy, damage, np.array([.1, .2, .3, .4]))
    assert g["scale"][0] == .02
    assert g["damage_nodes"] == 2  # strict > .1
    assert g["support_mass"] == pytest.approx(.6)
    assert g["background_support_fraction"] == pytest.approx(3 / 7)
    w = compact_window(torch.tensor(xy), torch.tensor(g["lower"]), torch.tensor(g["upper"]))
    torch.testing.assert_close(w[:2], torch.ones(2, 1, dtype=torch.float64), rtol=0, atol=0)
    assert w[-1].item() == 0
    json.dumps(g, allow_nan=False)


@pytest.mark.parametrize("x", [-.22, -.2, .2, .22])
def test_c2_window_joins(x):
    point = torch.tensor([[x, 0.]], dtype=torch.float64, requires_grad=True)
    lower = torch.tensor([-.2, -.1], dtype=torch.float64)
    upper = torch.tensor([.2, .1], dtype=torch.float64)
    w = compact_window(point, lower, upper)
    first = torch.autograd.grad(w.sum(), point, create_graph=True)[0]
    second = torch.autograd.grad(first[:, 0].sum(), point)[0]
    assert w.item() == pytest.approx(0 if abs(x) > .2 else 1, abs=1e-13)
    assert first[0, 0].item() == pytest.approx(0, abs=1e-10)
    assert second[0, 0].item() == pytest.approx(0, abs=1e-8)


def test_local_support_and_reconstruction(geometry):
    model = build_model(7, "localized", geometry)
    xy = torch.tensor([[.4, .3], [.0, .0]], dtype=torch.float64)
    with torch.no_grad():
        out = model.components_physical(xy)
    assert out["window"][0, 0] == 0
    assert torch.equal(out["local_raw"][0], torch.zeros(2, dtype=torch.float64))
    assert out["window"][1, 0] == 1
    torch.testing.assert_close(out["raw"], out["global_raw"] + out["local_raw"], rtol=0, atol=0)


def test_geometry_is_target_independent_and_checkpoint_roundtrips(geometry):
    xy = np.array([[-.2, -.1], [.2, .1], [.4, .3]])
    damage = np.array([.2, 1., 0.])
    targets = [np.zeros_like(xy), np.full_like(xy, 1e12)]
    manifests = [damage_geometry(xy, damage) for _unused in targets]
    assert manifests[0] == manifests[1]  # target has no API argument/read path
    model = build_model(7, "localized", geometry)
    stream = io.BytesIO()
    torch.save({"arm": model.arm, "geometry": geometry, "state_dict": model.state_dict()}, stream)
    stream.seek(0)
    checkpoint = torch.load(stream, weights_only=True)
    restored = build_model(19, checkpoint["arm"], checkpoint["geometry"])
    restored.load_state_dict(checkpoint["state_dict"], strict=True)
    point = torch.tensor([[.05, .02]], dtype=torch.float64)
    with torch.no_grad():
        torch.testing.assert_close(model(point), restored(point), rtol=0, atol=0)


@pytest.mark.parametrize("xy,damage", [
    (np.zeros((2, 2)), np.zeros(2)),
    (np.zeros((2, 2)), np.array([1., np.nan])),
    (np.ones((2, 2)), np.ones(2)),
    (np.zeros((2, 2)), np.ones(3)),
])
def test_invalid_geometry_fails_closed(xy, damage):
    with pytest.raises(ValueError):
        damage_geometry(xy, damage)
