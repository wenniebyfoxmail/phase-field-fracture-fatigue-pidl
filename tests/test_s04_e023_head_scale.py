"""Algebra and admission checks, no training or optimizer parameter steps."""
import copy, sys
from pathlib import Path
import numpy as np
import pytest
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "SENS_tensile"))
from s04_e023_head_scale import (
    build_candidate,
    build_leak_candidate,
    HEAD_SCALE_RULE,
    LEAK_LOCKS,
    ACTIVATION_RULE,
    DIRECT_LOCKS,
    MAP_LOCKS,
    scales_from_rms,
    calibrate_initial,
    validate_head_scale,
    gradient_coordinate_audit,
    physical_features,
    state_digest,
    validate_behavior_envelope,
)
from aggregate_s04_e023_head_scale_screen import summarize


def pair():
    torch.set_num_threads(2)
    g = MAP_LOCKS["c20s4"]["physical_geometry"]
    mp = MAP_LOCKS["c20s4"]["mapping"]
    base = nn.Linear(2, 2).double()
    x = np.linspace(g["lower"][0] - 0.03, g["upper"][0] + 0.03, 6)
    y = np.linspace(g["lower"][1] - 0.03, g["upper"][1] + 0.03, 5)
    xy = np.array(np.meshgrid(x, y)).reshape(2, -1).T
    mass = np.arange(1, len(xy) + 1, dtype=float)
    old = build_leak_candidate(7, "localized", g, copy.deepcopy(base), mp)
    rng = torch.random.get_rng_state().clone()
    new, cal = build_candidate(7, "localized", g, copy.deepcopy(base), mp, xy, mass)
    assert torch.equal(rng, torch.random.get_rng_state())
    return old, new, cal, xy, mass


def test_initialization_mass_formula_and_no_rng_or_parameter_change():
    old, new, cal, xy, mass = pair()
    assert state_digest(old.residual) == state_digest(new.residual)
    assert sum(p.numel() for p in old.parameters()) == sum(
        p.numel() for p in new.parameters()
    )
    with torch.no_grad():
        phi = physical_features(old, torch.tensor(xy)).numpy()
    expected = np.sqrt(np.sum(mass[:, None] / mass.sum() * phi**2, axis=0))
    np.testing.assert_allclose(cal["rms"], expected, rtol=1e-12, atol=1e-15)
    torch.testing.assert_close(
        old.correction_physical(torch.tensor(xy)),
        new.correction_physical(torch.tensor(xy)),
        rtol=0,
        atol=0,
    )
    assert not new.head_scale.requires_grad and len(cal["scale"]) == 284


@pytest.mark.parametrize("coefficient", [1.0, -0.6])
def test_nonzero_function_equivalence_and_head_gradient_coordinate_relation(
    coefficient
):
    old, new, cal, xy, mass = pair()
    with torch.no_grad():
        old.residual.activations[-1].coeff.fill_(coefficient)
        new.residual.activations[-1].coeff.fill_(coefficient)
        weights = torch.linspace(-0.001, 0.001, 566, dtype=torch.float64).reshape(
            2, 283
        )
        bias = torch.tensor([0.002, -0.001], dtype=torch.float64)
        old.residual.output_layer.weight.copy_(weights)
        old.residual.output_layer.bias.copy_(bias)
        new.residual.output_layer.weight.copy_(weights / new.head_scale[:-1])
        new.residual.output_layer.bias.copy_(bias / new.head_scale[-1])
    q = torch.tensor(xy, dtype=torch.float64)
    torch.testing.assert_close(
        old.correction_physical(q), new.correction_physical(q), rtol=1e-10, atol=1e-12
    )
    torch.testing.assert_close(
        old.components_physical(q)["local_raw"],
        new.components_physical(q)["local_raw"],
        rtol=1e-10,
        atol=1e-12,
    )
    torch.testing.assert_close(old(q * 2), new(q * 2), rtol=1e-10, atol=1e-12)
    goal = torch.linspace(-0.001, 0.002, len(xy) * 2, dtype=torch.float64).reshape(
        -1, 2
    )
    gs = []
    for m in (old, new):
        loss = (
            torch.tensor(mass / mass.sum())[:, None]
            * (m.correction_physical(q) - goal) ** 2
        ).sum()
        gs.append(
            torch.autograd.grad(
                loss, (m.residual.output_layer.weight, m.residual.output_layer.bias)
            )
        )
    torch.testing.assert_close(
        gs[1][0], gs[0][0] * new.head_scale[:-1], rtol=1e-10, atol=1e-12
    )
    torch.testing.assert_close(
        gs[1][1], gs[0][1] * new.head_scale[-1], rtol=1e-10, atol=1e-12
    )
    assert all(p.grad is None for p in new.parameters())


def test_calibration_has_no_target_input_and_matches_streamed_audit():
    old, new, cal, xy, mass = pair()
    assert HEAD_SCALE_RULE["target_used"] is False
    q = calibrate_initial(old, xy, mass)
    assert q == cal
    with torch.no_grad():
        phi = physical_features(old, torch.tensor(xy)).numpy()
    base = np.zeros_like(xy)
    target = np.full_like(xy, 0.001)
    audit = gradient_coordinate_audit(new, xy, mass, base, target)
    assert audit["max_abs_difference"] < 1e-12
    with pytest.raises(ValueError):
        calibrate_initial(new, xy, mass * 0)
    with torch.no_grad():
        old.residual.output_layer.bias.fill_(1)
    with pytest.raises(ValueError, match="zero output"):
        calibrate_initial(old, xy, mass)


def test_fixed_floor_zero_and_tiny_columns():
    np.testing.assert_array_equal(scales_from_rms([0.0, 1e-12, 1.0]), [1.0, 1e6, 1.0])
    assert np.isfinite(scales_from_rms([1e-200, 1.0])).all()
    for a in ([0.0, 0.0], [-1.0, 2.0], [np.nan, 1.0], [np.inf, 1.0]):
        with pytest.raises(ValueError):
            scales_from_rms(a)


@pytest.mark.parametrize("which", ["scale", "rms"])
def test_buffer_tamper_rejected(which):
    _, m, cal, _, _ = pair()
    with torch.no_grad():
        getattr(m, "head_" + which)[0] += 1.0
    with pytest.raises(ValueError):
        validate_head_scale(m, cal)


def test_envelope_binds_direct_state_and_rule():
    asset = dict(
        activation_rule=ACTIVATION_RULE,
        paired_e021_control_lock=DIRECT_LOCKS["c20s4"],
        head_scale_rule=HEAD_SCALE_RULE,
        paired_e022_control_lock=LEAK_LOCKS["c20s4"],
    )
    validate_behavior_envelope(asset, "c20s4")
    with pytest.raises(ValueError):
        validate_behavior_envelope(asset, "c60s4")
    with pytest.raises(ValueError):
        validate_behavior_envelope(dict(asset, head_scale_rule={}), "c20s4")


def test_primary_requires_all_three_and_never_promotes_secondary():
    rows = [
        dict(
            state=s,
            displacement_mass_rms_over_abs_Us=0.0008,
            final_damage_conditional_rms=0.002,
            final_background_conditional_rms=0.0001,
            base_damage=0.02,
            base_background=0.0002,
            control_damage=0.003,
            control_background=0.0002,
            direct_E021_damage=0.003,
            direct_E021_background=0.0002,
            direct_E022_damage=0.003,
            direct_E022_background=0.0002,
        )
        for s in LEAK_LOCKS
    ]
    assert summarize(rows)["verdict"].endswith("PASS")
    rows[-1]["displacement_mass_rms_over_abs_Us"] = 0.0011
    assert summarize(rows)["verdict"].endswith("FAIL")
    assert summarize(rows[:2])["verdict"] == "INCONCLUSIVE"
    assert summarize(rows + [rows[0]])["verdict"] == "INADMISSIBLE"


def test_formal_leak_native_profile_is_not_replaced_by_mac():
    from s04_e023_head_scale import require_leak_native_profile, native_replay

    root = Path(
        "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E022/producer_execution_v1/raw/runs"
    )
    directory = root / LEAK_LOCKS["c20s4"]["run_id"]
    if not directory.exists():
        pytest.skip("optional exact E022 local control absent")
    rates = np.load(directory / "learning_rates.npy", allow_pickle=False)
    if np.array_equal(rates, np.asarray(native_replay())):
        require_leak_native_profile("c20s4", directory)
    else:
        with pytest.raises(AssertionError):
            require_leak_native_profile("c20s4", directory)
