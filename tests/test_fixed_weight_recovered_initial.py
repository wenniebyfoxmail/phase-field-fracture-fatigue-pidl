"""In-memory recovery and streaming checks; no archive, training or solver."""
from dataclasses import replace
from pathlib import Path
import sys

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from fixed_weight_contract import (
    RECOVERED_INITIAL_SEMANTICS, SEMANTICS, Material, Mesh,
    RecoveredInitialKey, RecoveredInitialState, State, StateKey,
    TrajectoryRecord, TransitionRequest, iter_trajectory, load_trajectory,
)
from fixed_weight_models import FixedWeightFieldModel, ModelConfig


def fixture():
    mesh = Mesh(torch.tensor([[0., 0.], [1., 0.], [1., 1.], [0., 1.]], dtype=torch.float64),
                torch.tensor([[0, 1, 2, 3]]), "q4")
    material = Material(1., .3, .01, .01, .5, 2., 0., 1.)
    key = RecoveredInitialKey("trajectory", "condition", "reference", "q4",
                              1, 0, 0, "initial", 0.)
    damage = torch.tensor([1., .1, 0., 0.], dtype=torch.float64)
    initial = RecoveredInitialState(key, torch.zeros_like(mesh.xy), damage,
                                    damage.clone(), torch.zeros((1, 4, 3), dtype=mesh.xy.dtype))
    target_key = StateKey("trajectory", "condition", "reference", "q4",
                          1, 1, 1, "load", .1)
    u = torch.zeros_like(mesh.xy)
    u[2:, 1] = .1
    target = State(target_key, u, damage.clone(), damage.clone(),
                   torch.ones((1, 4, 3), dtype=mesh.xy.dtype))
    record = TrajectoryRecord("trajectory", "condition", "reference", "q4", "train", "audit",
                              semantics=RECOVERED_INITIAL_SEMANTICS, expected_state_count=2,
                              material_values=(1., .3, .01, .01, .5, 2., 0., 1.))
    return mesh, material, initial, target, record


def test_explicit_recovery_retains_pre_cycle_timing_and_allows_first_transition():
    mesh, material, initial, target, record = fixture()
    initial.validate(mesh, material)
    assert initial.key.timing == "pre_cycle_committed"
    assert bool((initial.fatigue(material) == 1).all())
    TransitionRequest(target.key, .1).validate(initial.key)
    result = load_trajectory(record, lambda _: (initial, target), mesh, material)
    assert isinstance(result, list) and result[0] is initial and result[1] is target


@pytest.mark.parametrize("change", [
    {"cycle": 2}, {"substep": 1}, {"ordinal": 1}, {"branch": "hold"},
    {"load": .1}, {"timing": "post_history_commit"},
])
def test_recovery_key_rejects_aliases_nonzero_load_and_relabelling(change):
    _, _, initial, _, _ = fixture()
    with pytest.raises(ValueError):
        replace(initial.key, **change).validate()


def test_generic_key_and_state_do_not_gain_pre_cycle_admission():
    mesh, material, initial, target, _ = fixture()
    with pytest.raises(ValueError, match="post-history"):
        replace(target.key, timing="pre_cycle_committed").validate()
    with pytest.raises(ValueError, match="explicit RecoveredInitialState"):
        State(initial.key, initial.u, initial.d, initial.d_lower, initial.history).validate(mesh, material)
    with pytest.raises(ValueError, match="explicit RecoveredInitialKey"):
        replace(initial, key=target.key).validate(mesh, material)


@pytest.mark.parametrize("field", ["u", "history", "d_lower"])
def test_recovery_rejects_unreset_fields_and_stale_lower_bound(field):
    mesh, material, initial, _, _ = fixture()
    value = getattr(initial, field).clone()
    value.reshape(-1)[0] += .01 if field != "d_lower" else -.01
    with pytest.raises(ValueError):
        replace(initial, **{field: value}).validate(mesh, material)


def test_old_record_rejects_recovery_and_new_record_requires_it():
    mesh, material, initial, target, record = fixture()
    with pytest.raises(ValueError, match="requires v2"):
        load_trajectory(replace(record, semantics=SEMANTICS), lambda _: (initial, target), mesh, material)
    with pytest.raises(ValueError, match="must begin"):
        load_trajectory(record, lambda _: (target, target), mesh, material)
    with pytest.raises(ValueError, match="first trajectory position"):
        load_trajectory(record, lambda _: (initial, initial), mesh, material)


def test_recovery_is_source_only_and_cannot_skip_first_loading_step():
    _, _, initial, target, _ = fixture()
    with pytest.raises(ValueError, match="only be a transition source"):
        TransitionRequest(initial.key, -.1).validate(target.key)
    with pytest.raises(ValueError, match="c0001_s01"):
        TransitionRequest(replace(target.key, substep=2), .1).validate(initial.key)


def test_stream_consumes_only_one_state_at_a_time_but_requires_exhaustion():
    mesh, material, initial, target, record = fixture()
    observed = []

    def loader(_):
        observed.append("first")
        yield initial
        observed.append("second")
        yield target
        observed.append("exhausted")

    stream = iter_trajectory(record, loader, mesh, material)
    assert observed == []
    assert next(stream) is initial
    assert observed == ["first"]
    assert next(stream) is target
    assert observed == ["first", "second"]
    with pytest.raises(StopIteration):
        next(stream)
    assert observed == ["first", "second", "exhausted"]


def test_stream_prefix_does_not_hide_a_short_or_long_trajectory():
    mesh, material, initial, target, record = fixture()
    stream = iter_trajectory(record, lambda _: iter((initial,)), mesh, material)
    assert next(stream) is initial
    with pytest.raises(ValueError, match="state count"):
        next(stream)
    with pytest.raises(ValueError, match="state count"):
        load_trajectory(record, lambda _: iter((initial, target, target)), mesh, material)


@pytest.mark.parametrize("change", [{"split": "protected"}, {"qualification_ref": ""},
                                    {"expected_state_count": None}, {"material_values": None}])
def test_stream_guards_run_before_loader_callback(change):
    mesh, material, initial, target, record = fixture()
    called = []

    def loader(_):
        called.append(True)
        return iter((initial, target))

    with pytest.raises((ValueError, PermissionError)):
        next(iter_trajectory(replace(record, **change), loader, mesh, material))
    assert called == []


@pytest.mark.parametrize("field", ["d", "alpha"])
def test_stream_snapshots_previous_bound_before_loader_reuses_buffer(field):
    mesh, material, initial, target, record = fixture()
    record = replace(record, expected_state_count=3)

    def loader(_):
        yield initial
        yield target
        if field == "d":
            target.d[1] = .01
            target.d_lower[1] = .01
        else:
            target.history[..., 1] = .5
        yield replace(target, key=replace(target.key, substep=2, ordinal=2, branch="hold"))

    with pytest.raises(ValueError, match="decreases"):
        load_trajectory(record, loader, mesh, material)


@pytest.mark.parametrize("route", ["conditional", "transition"])
def test_existing_model_consumes_explicit_initial_without_relabelling(route):
    mesh, material, initial, target, _ = fixture()
    model = FixedWeightFieldModel(mesh, ModelConfig(route=route, width=4, context_width=2))
    with torch.inference_mode():
        prediction = model(initial, TransitionRequest(target.key, .1), material)
    prediction.state.validate(mesh, material)
    assert prediction.state.key.timing == "post_history_commit"
    assert initial.key.timing == "pre_cycle_committed"
    assert bool((prediction.state.d >= initial.d).all())


def test_persistence_and_secant_leave_initial_type_at_first_action():
    from types import SimpleNamespace
    from fixed_weight_evaluation import persistence, secant, evaluate_continuation
    mesh, material, initial, target, _ = fixture()
    one = persistence(initial, target.key, mesh)
    assert type(one) is State
    one.validate(mesh, material)
    two = secant(initial, one, replace(target.key, ordinal=2, substep=2, load=.2), mesh)
    two.validate(mesh, material)
    unloaded = persistence(two, replace(target.key, ordinal=3, substep=5, load=0., branch='unload'), mesh)
    unloaded.validate(mesh, material)
    assert initial.key.timing == 'pre_cycle_committed'
    assert type(unloaded) is State
    class Predictor:
        def predict(self, source, request, material):
            value = persistence(source, request.target, mesh)
            return SimpleNamespace(state=value, raw_state=value)
        def rollout(self, source, requests, material):
            for request in requests:
                prediction = self.predict(source, request, material)
                yield prediction
                source = prediction.state
    report = evaluate_continuation(Predictor(), [initial, one, two, unloaded], mesh, material)
    assert report['n_horizons'] == 3
    assert report['persistence']['mode'] == 'autonomous_kinematic_persistence'
