"""Small synthetic checks only; no training or reference data access."""
from dataclasses import replace
from pathlib import Path
import sys

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from fixed_weight_evaluation import (
    PHYSICS_SEMANTICS, admissibility, aggregate_trajectories, evaluate_continuation, field_errors,
    matched_costs, persistence, physics_diagnostics, raw_projected_diagnostics,
    rollout_errors, secant, weighted_errors,
)
from s09_fem_physics import amor_fields, trial_fatigue
from s09_q4_quadrature import q4_interpolate, q4_shape_data
from fixed_weight_contract import Material, Mesh, State, StateKey


def material():
    return Material(1., .3, .01, .01, .5, 2., 0., 1.)


def fixture():
    xy = torch.tensor([[0., 0.], [1., 0.], [1., 1.], [0., 1.]], dtype=torch.float64)
    mesh = Mesh(xy, torch.tensor([[0, 1, 2, 3]]), "unit_q4")
    key = StateKey("synthetic", "synthetic_condition", "synthetic_no_physical_reference",
                   "unit_q4", 1, 0, 0, "initial", 0.)
    state = State(key, torch.zeros_like(xy), torch.zeros(4, dtype=xy.dtype),
                  torch.zeros(4, dtype=xy.dtype), torch.zeros((1, 4, 3), dtype=xy.dtype))
    return mesh, state


def next_key(source, load, **kwargs):
    kwargs.setdefault("branch", "load" if load > source.key.load else "unload" if load < source.key.load else "hold")
    return replace(source.key, ordinal=source.key.ordinal + 1,
                   substep=source.key.substep + 1, load=load, **kwargs)


def test_weighted_errors_zero_reference_and_weighted_rmse():
    p = torch.tensor([1., 3.]); r = torch.zeros(2); w = torch.tensor([3., 1.])
    got = weighted_errors(p, r, w)
    assert got["mae"] == 1.5
    assert got["rmse"] == pytest.approx(3 ** .5)
    assert got["relative_l2"] is None
    with pytest.raises(ValueError, match="weights"):
        weighted_errors(p, r, -w)
    with pytest.raises(ValueError, match="finite"):
        weighted_errors(p * float("nan"), r, w)


def test_persistence_and_secant_are_kinematic_and_no_mutation():
    mesh, zero = fixture()
    one = persistence(zero, next_key(zero, .1), mesh)
    two = secant(zero, one, next_key(one, .2), mesh)
    torch.testing.assert_close(two.u[:, 1], mesh.xy[:, 1] * .2)
    torch.testing.assert_close(zero.u, torch.zeros_like(zero.u))
    assert two.d.data_ptr() != one.d.data_ptr()
    with pytest.raises(ValueError, match="same sign"):
        secant(zero, one, next_key(one, 0., branch="unload"), mesh)
    with pytest.raises(ValueError, match="nonzero"):
        secant(zero, one, next_key(one, .1), mesh)
    with pytest.raises(ValueError, match="reference_id mismatch"):
        persistence(one, next_key(one, .2, reference_id="other"), mesh)


def test_secant_uses_two_actual_intervals_not_previous_incoming_branch():
    mesh, zero = fixture()
    # The first case starts at initial; the second follows an earlier unloading
    # state. Both actual secant intervals are loading and must be admitted.
    for previous_branch in ("initial", "unload"):
        previous = replace(zero, key=replace(zero.key, branch=previous_branch))
        source = persistence(previous, next_key(previous, .1), mesh)
        target = secant(previous, source, next_key(source, .2), mesh)
        torch.testing.assert_close(target.u[:, 1], mesh.xy[:, 1] * .2)


def test_transition_rejects_bad_cycle_substep_and_target_branch():
    mesh, zero = fixture()
    target = next_key(zero, .1)
    with pytest.raises(ValueError, match="cycle/substep"):
        persistence(zero, replace(target, substep=0), mesh)
    with pytest.raises(ValueError, match="branch disagrees"):
        persistence(zero, replace(target, branch="unload"), mesh)
    with pytest.raises(ValueError, match="ordinal"):
        persistence(zero, replace(target, ordinal=2), mesh)


def test_raw_violations_are_visible_separately_from_projected():
    mesh, old = fixture()
    old = replace(old, d=torch.full_like(old.d, .4), d_lower=torch.full_like(old.d, .4))
    raw = persistence(old, next_key(old, .1), mesh)
    raw = replace(raw, d=torch.tensor([-.1, .2, .4, 1.2], dtype=old.d.dtype))
    projected = replace(raw, d=raw.d.clamp(min=.4, max=1.))
    report = raw_projected_diagnostics(raw, projected, old)
    assert report["raw"]["transition"]["damage_healing"]["max"] == .5
    assert report["projected"]["transition"]["damage_healing"]["max"] == 0
    assert report["raw"]["damage_above_one"]["max"] == pytest.approx(.2)


def test_field_identity_and_trajectory_macro_do_not_pool_frames():
    mesh, old = fixture()
    ref1 = persistence(old, next_key(old, .1), mesh)
    ref2 = persistence(ref1, next_key(ref1, .2), mesh)
    pred1 = replace(ref1, d=torch.ones_like(ref1.d))
    pred2 = replace(ref2, d=torch.ones_like(ref2.d))
    long = rollout_errors([pred1, pred2], [ref1, ref2], mesh)
    other = replace(ref1, key=replace(ref1.key, trajectory_id="other"))
    short = rollout_errors([other], [other], mesh)
    report = aggregate_trajectories([long, short])
    assert report["macro"]["d"]["mae"] == .5  # Not frame-pooled 2/3.
    assert report["by_horizon"][1]["n_trajectories"] == 1
    with pytest.raises(ValueError, match="identit"):
        field_errors(pred1, other, mesh)
    with pytest.raises(ValueError, match="complete"):
        rollout_errors([pred1], [ref1, ref2], mesh)
    with pytest.raises(ValueError, match="one report"):
        aggregate_trajectories([long, long])


def test_native_physics_consistency_and_explicit_skips():
    mesh, source = fixture()
    state = persistence(source, next_key(source, .1), mesh)
    assert physics_diagnostics(state, source, mesh, material())["status"] == "skipped"
    shape, dshape, det = q4_shape_data(mesh.xy, mesh.conn)
    fields = amor_fields(state.u, state.d, mesh.conn, shape, dshape)
    alpha, q, _ = trial_fatigue(q4_interpolate(state.d, mesh.conn, shape), fields["psi"],
                              source.history[..., 1], source.history[..., 2])
    state = replace(state, history=torch.stack((fields["psi"], alpha, q), -1))
    result = physics_diagnostics(state, source, mesh, material(), semantics=PHYSICS_SEMANTICS)
    assert result["status"] == "computed"
    assert result["equilibrium"]["status"] == "not_applicable"  # One Q4 has only boundary nodes.
    assert result["phase_kkt"]["status"] == "skipped"
    assert result["elastic_energy"] > 0
    assert result["at1_surface_energy_from_trial_fatigue"] == 0
    assert result["boundary_displacement_max_error"] == 0
    for channel in result["history_consistency"].values():
        assert channel["mae"] == 0


def test_state_energy_and_reconstructed_fatigue_energy_are_distinguished():
    mesh, source = fixture()
    state = persistence(source, next_key(source, .1), mesh)
    history = state.history.clone()
    history[..., 1] = 5.  # Deliberately inconsistent predicted accumulated history.
    state = replace(state, d=torch.full_like(state.d, .2), history=history)
    result = physics_diagnostics(state, source, mesh, material(), semantics=PHYSICS_SEMANTICS)
    assert result["at1_surface_energy_from_state_alpha_bar"] < result["at1_surface_energy_from_trial_fatigue"]
    assert result["history_consistency"]["alpha_bar"]["mae"] > 1
    history = history.clone()
    history[..., 1] = -.1
    invalid = physics_diagnostics(replace(state, history=history), source, mesh, material(), semantics=PHYSICS_SEMANTICS)
    assert invalid["at1_surface_energy_from_state_alpha_bar"] is None
    assert invalid["state_fatigue_energy_status"] == "not_applicable_negative_alpha_bar"


def test_costs_require_quality_and_include_training_and_generation():
    kwargs = dict(training_seconds=20., data_generation_seconds=70.,
                  inference_seconds=10., reference_seconds=50., quality_tolerance=.1)
    refused = matched_costs(**kwargs, quality_error=.2)
    assert refused["inference_speedup"] is None
    assert refused["total_cost_speedup"] is None
    passed = matched_costs(**kwargs, quality_error=.05)
    assert passed["inference_speedup"] == 5
    assert passed["total_cost_speedup"] == .5


def test_continuation_integration_uses_frozen_model_and_schedule_only(monkeypatch):
    from fixed_weight_models import FixedWeightFieldModel, ModelConfig
    from fixed_weight_inference import FrozenPredictor
    mesh, origin = fixture()
    one = persistence(origin, next_key(origin, .1), mesh)
    two = persistence(one, next_key(one, .2), mesh)
    predictor = FrozenPredictor(FixedWeightFieldModel(mesh, ModelConfig(width=8, context_width=4)))
    before = {k: v.clone() for k, v in predictor.model.state_dict().items()}
    original_rollout = predictor.rollout
    calls = []
    def schedule_only(source, requests, mat):
        calls.append((source, requests))
        assert source is origin
        assert all(set(r.__dataclass_fields__) == {"target", "delta_load"} for r in requests)
        assert all(not hasattr(r.target, "u") for r in requests)
        return original_rollout(source, requests, mat)
    monkeypatch.setattr(predictor, "rollout", schedule_only)
    result = evaluate_continuation(predictor, [origin, one, two], mesh, material())
    assert len(calls) == 1 and result["n_horizons"] == 2
    assert len(result["autonomous"]["horizons"]) == len(result["teacher_forced"]["horizons"]) == 2
    assert result["persistence"]["trajectory_mean"]["u_y"]["mae"] == 0
    assert result["secant"]["status"] == "skipped"
    assert result["condition_scope"][0]["training_completed"] is False
    assert result["autonomous"]["diagnostics"][0]["physics"]["status"] == "skipped"
    for key, value in before.items():
        assert torch.equal(value, predictor.model.state_dict()[key])
    monkeypatch.setattr(predictor, "rollout", original_rollout)
    later = evaluate_continuation(predictor, [origin, one, two], mesh, material(), origin_index=1)
    assert later["secant"]["status"] == "computed"
    assert later["secant"]["horizons"][0]["errors"]["u_y"]["mae"] == 0
    with pytest.raises(ValueError, match="origin_index"):
        evaluate_continuation(predictor, [origin, one, two], mesh, material(), origin_index=2)


def test_tiny_mesh_interior_is_not_a_fixed_boundary_row():
    xy = torch.tensor([[0., 0.], [1., 0.], [0., 1e-12], [1., 1e-12],
                       [0., 2e-12], [1., 2e-12]], dtype=torch.float64)
    mesh = Mesh(xy, torch.tensor([[0, 1, 3, 2], [2, 3, 5, 4]]), "tiny-height")
    key = StateKey("t", "c", "synthetic", mesh.mesh_id, 0, 0, 0, "initial", 0.)
    source = State(key, torch.zeros_like(xy), torch.zeros(6, dtype=xy.dtype),
                   torch.zeros(6, dtype=xy.dtype), torch.zeros((2, 4, 3), dtype=xy.dtype))
    state = persistence(source, next_key(source, 1e-14), mesh)
    result = physics_diagnostics(state, source, mesh, material(), semantics=PHYSICS_SEMANTICS)
    assert result["equilibrium"]["n_free_dofs"] == 4
    assert result["equilibrium"]["status"] == "computed"


def test_rounded_loaded_origin_unloads_reloads_and_evaluates_without_boundary_drift():
    from fixed_weight_models import FixedWeightFieldModel, ModelConfig
    from fixed_weight_inference import FrozenPredictor
    xy = torch.tensor([[0., 0.], [1., 0.], [0., .5], [1., .5],
                       [0., 1.], [1., 1.]], dtype=torch.float64)
    mesh = Mesh(xy, torch.tensor([[0, 1, 3, 2], [2, 3, 5, 4]]), "rounded-boundary")
    key = StateKey("t", "c", "synthetic", mesh.mesh_id, 1, 1, 1, "load", .3)
    u = torch.stack((torch.zeros_like(xy[:, 1]), .3 * xy[:, 1]), -1)
    u[4:, 1] = torch.nextafter(u[4:, 1], torch.full_like(u[4:, 1], float("inf")))
    u[2:4] += u.new_tensor([.02, .03])  # Free displacement must be preserved.
    source = State(key, u, torch.zeros(6, dtype=xy.dtype), torch.zeros(6, dtype=xy.dtype),
                   torch.zeros((2, 4, 3), dtype=xy.dtype))
    source.validate(mesh, material())  # One-ulp error is explicitly admitted.
    original = source.u.clone()
    unloaded = persistence(source, next_key(source, 0.), mesh)
    unloaded.validate(mesh, material())
    assert torch.equal(unloaded.u[[0, 1, 4, 5]], torch.zeros_like(unloaded.u[[0, 1, 4, 5]]))
    torch.testing.assert_close(unloaded.u[2:4], source.u[2:4] + u.new_tensor([0., -.15]), rtol=0, atol=0)
    reloaded = persistence(unloaded, next_key(unloaded, .2), mesh)
    reloaded.validate(mesh, material())
    assert torch.equal(reloaded.u[4:, 1], torch.full_like(reloaded.u[4:, 1], .2))
    assert torch.equal(source.u, original)
    predictor = FrozenPredictor(FixedWeightFieldModel(mesh, ModelConfig(width=8, context_width=4)))
    report = evaluate_continuation(predictor, [source, unloaded, reloaded], mesh, material())
    assert report["n_horizons"] == 2
    assert report["persistence"]["trajectory_mean"]["u_y"]["mae"] == 0


def test_secant_reimposes_exact_zero_boundary_after_rounded_extrapolation():
    mesh, initial = fixture()
    previous = persistence(initial, next_key(initial, .3), mesh)
    current = persistence(previous, next_key(previous, .15), mesh)
    rounded = current.u.clone()
    rounded[2:, 1] = torch.nextafter(rounded[2:, 1], torch.full_like(rounded[2:, 1], float("inf")))
    current = replace(current, u=rounded)
    current.validate(mesh, material())
    predicted = secant(previous, current, next_key(current, 0.), mesh)
    assert torch.equal(predicted.u, torch.zeros_like(predicted.u))
    predicted.validate(mesh, material())
    # The zero-load state remains reusable at the next step.
    reloaded = persistence(predicted, next_key(predicted, .1), mesh)
    reloaded.validate(mesh, material())
