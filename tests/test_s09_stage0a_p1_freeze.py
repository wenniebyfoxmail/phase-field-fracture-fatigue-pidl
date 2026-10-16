import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_multiobjective_update import merge_objective_gradients
from s09_stage0a_p1_freeze import freeze_p1_contract, half_ulp_float64, weighted_rms


def synthetic_fields():
    cycles = np.arange(1, 74, dtype=np.int64)
    nodes, elements = 5, 2
    nodal_weight = np.array([1, 2, 3, 2, 1], dtype=np.float64)
    gp_weight = np.ones((elements, 4), dtype=np.float64)
    d_pre = np.zeros((73, nodes), dtype=np.float64)
    # Lowest cycles in every band are near-stagnant; upper ranks have clear growth.
    magnitude = np.linspace(0, 0.2, 73, dtype=np.float64)
    d_peak = d_pre + magnitude[:, None]
    h_pre = np.zeros((73, elements, 4, 4), dtype=np.float64)
    h_peak = h_pre + magnitude[:, None, None, None] * np.array([1, 2, 1, -1], dtype=np.float64)
    u_peak = np.ones((73, nodes, 2), dtype=np.float64) * np.array([0.01, 0.1])
    return dict(cycles=cycles, d_pre=d_pre, d_peak=d_peak, history_pre=h_pre,
                history_peak=h_peak, u_peak=u_peak, nodal_weight=nodal_weight,
                gp_weight=gp_weight)


def test_half_ulp_is_positive_and_representable_at_zero():
    values = np.array([0.0, 1.0, -1.0, np.finfo(np.float64).tiny], dtype=np.float64)
    got = half_ulp_float64(values)
    assert got.dtype == np.float64
    assert np.all(got > 0)
    assert got[0] == np.nextafter(np.float64(0), np.float64(1))


def test_p1_freeze_is_deterministic_and_has_positive_normalisers():
    fields = synthetic_fields()
    left = freeze_p1_contract(**fields)
    right = freeze_p1_contract(**fields)
    assert left == right
    assert len(left["selected_cycles"]) == 16
    assert len(left["growth_cycles"]) >= 4
    assert len(left["near_stagnant_cycles"]) >= 4
    scales = [left["normalisers"]["damage_increment"],
              *left["normalisers"]["history_increment"],
              *left["normalisers"]["displacement"]]
    assert np.all(np.isfinite(scales)) and np.all(np.array(scales) > 0)
    assert left["scientific_execution_authorized"] is False


def test_p1_freeze_rejects_dtype_and_empty_stagnant_group():
    fields = synthetic_fields()
    bad = dict(fields); bad["d_pre"] = bad["d_pre"].astype(np.float32)
    with pytest.raises(ValueError, match="float64"):
        freeze_p1_contract(**bad)
    no_stagnation = dict(fields)
    no_stagnation["d_peak"] = np.ones_like(fields["d_peak"]) * 0.2
    with pytest.raises(ValueError, match="P1_NOT_READY"):
        freeze_p1_contract(**no_stagnation)


def test_weighted_rms_is_stable_for_tiny_nonzero_values():
    scalar = np.full((3, 4), 1e-200, dtype=np.float64)
    scalar_weight = np.array([1, 2, 3, 4], dtype=np.float64)
    assert weighted_rms(scalar, scalar_weight) == pytest.approx(1e-200)
    channels = np.stack([scalar, scalar * 2], axis=-1)
    np.testing.assert_allclose(weighted_rms(channels, scalar_weight), [1e-200, 2e-200])
    assert weighted_rms(np.zeros_like(scalar), scalar_weight) == 0


def test_p1_freeze_preserves_tiny_nonzero_displacement_rms():
    fields = synthetic_fields()
    fields["u_peak"][:] = 1e-200
    result = freeze_p1_contract(**fields)
    np.testing.assert_allclose(result["normalisers"]["displacement"], [1e-200, 1e-200])


def test_gradient_merge_projects_conflicts_and_clips_deterministically():
    gradients = [torch.tensor([2.0, 0.0]), torch.tensor([-1.0, 1.0]), torch.tensor([0.0, 3.0])]
    left, diagnostic_left = merge_objective_gradients(gradients, clip_norm=0.5)
    right, diagnostic_right = merge_objective_gradients(gradients, clip_norm=0.5)
    torch.testing.assert_close(left, right)
    assert diagnostic_left["conflict_projection_count"] > 0
    assert diagnostic_left["merged_norm_after_clip"] <= 0.5 + 1e-7
    assert diagnostic_left["order"] == diagnostic_right["order"]


def test_gradient_merge_handles_zero_and_rejects_nonfinite():
    merged, diagnostics = merge_objective_gradients([torch.zeros(2), torch.tensor([1.0, 0.0])])
    assert torch.isfinite(merged).all()
    assert diagnostics["zero_gradient_count"] == 1
    with pytest.raises(FloatingPointError):
        merge_objective_gradients([torch.tensor([float("nan"), 0.0])])
