"""Tiny in-memory contracts only: no archive, optimiser, or scientific solver."""
from dataclasses import replace
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from fixed_weight_contract import (SEMANTICS, Material, Mesh, SplitManifest, State, StateKey,
                                   TrajectoryRecord, TransitionRequest, adapt_decoded_stage0a,
                                   load_trajectory)


def fixture():
    mesh = Mesh(torch.tensor([[0., 0.], [1., 0.], [1., 1.], [0., 1.]], dtype=torch.float64),
                torch.tensor([[0, 1, 2, 3]]), "q4")
    material = Material(210., .3, 2.7, .1, .5, 2., 1e-8, 1.)
    key = StateKey("trajectory", "condition", "reference", "q4", 0, 0, 0, "initial", 0.)
    state = State(key, torch.zeros((4, 2), dtype=torch.float64),
                  torch.full((4,), .1, dtype=torch.float64),
                  torch.full((4,), .1, dtype=torch.float64),
                  torch.ones((1, 4, 3), dtype=torch.float64))
    record = TrajectoryRecord("trajectory", "condition", "reference", "q4", "train",
                              "source-audit-for-this-state-contract", expected_state_count=3,
                              material_values=(210., .3, 2.7, .1, .5, 2., 1e-8, 1.))
    return mesh, material, state, record


def sequence(state):
    u_load = state.u.clone()
    u_load[2:, 1] = .1
    loaded = replace(state, key=replace(state.key, cycle=1, substep=1, ordinal=1, branch="load", load=.1),
                     u=u_load, d=state.d + .1, d_lower=state.d + .1)
    history = loaded.history.clone()
    history[..., 0] = .1  # Current energy H may decrease on unload.
    history[..., 2] = .05  # q_prev may decrease too; neither is max history.
    unloaded = replace(loaded, key=replace(loaded.key, substep=2, ordinal=2, branch="unload", load=0.),
                       u=state.u.clone(), d_lower=loaded.d, history=history)
    return [state, loaded, unloaded]


def test_native_support_and_material_features_are_explicit():
    mesh, material, state, _ = fixture()
    state.validate(mesh, material)
    shape, dshape, det = mesh.quadrature()
    assert shape.shape == (4, 4) and dshape.shape == (1, 4, 2, 4)
    torch.testing.assert_close(det.sum(), mesh.xy.new_tensor(1.))
    assert material.features(mesh.xy).tolist() == [210., .3, 2.7, .1, .5, 2., 1e-8, 1.]
    torch.testing.assert_close(state.fatigue(material), torch.full((1, 4), 4/9, dtype=torch.float64))


def test_load_unload_preserves_native_history_and_committed_lower_bound():
    mesh, material, state, record = fixture()
    result = load_trajectory(record, lambda _: sequence(state), mesh, material)
    assert len(result) == 3
    assert all(torch.equal(item.d_lower, item.d) for item in result)
    assert bool((result[2].history[..., 0] < result[1].history[..., 0]).all())
    assert bool((result[2].history[..., 2] < result[1].history[..., 2]).all())


@pytest.mark.parametrize("change", [{"split": "protected"}, {"qualification_ref": ""}])
def test_access_denied_before_loader_callback(change):
    mesh, material, _, record = fixture()
    called = []
    with pytest.raises(PermissionError):
        load_trajectory(replace(record, **change), lambda _: called.append(True), mesh, material)
    assert called == []


def test_complete_count_required_and_cropped_windows_rejected():
    mesh, material, state, record = fixture()
    called = []
    with pytest.raises(ValueError, match="expected_state_count"):
        load_trajectory(replace(record, expected_state_count=None), lambda _: called.append(True), mesh, material)
    assert called == []
    with pytest.raises(ValueError, match="state count"):
        load_trajectory(record, lambda _: sequence(state)[:2], mesh, material)
    with pytest.raises(ValueError, match="ordinals"):
        load_trajectory(replace(record, expected_state_count=2), lambda _: sequence(state)[1:], mesh, material)


@pytest.mark.parametrize("field,value", [("trajectory_id", "another"), ("condition_id", "another"),
    ("reference_id", "another"), ("mesh_id", "another"), ("ordinal", 2),
    ("timing", "pre_update"), ("cycle", 0), ("branch", "unload")])
def test_transition_rejects_identity_timing_order_and_branch_drift(field, value):
    _, _, state, _ = fixture()
    target = sequence(state)[1].key
    if field == "cycle":
        target = replace(target, substep=0)
    with pytest.raises(ValueError):
        TransitionRequest(replace(target, **{field: value}), .1).validate(state.key)


def test_delta_load_and_hold_are_checked():
    _, _, state, _ = fixture()
    target = sequence(state)[1].key
    with pytest.raises(ValueError, match="delta_load"):
        TransitionRequest(target, .2).validate(state.key)
    TransitionRequest(replace(target, branch="hold", load=0.), 0.).validate(state.key)


def test_split_groups_whole_conditions_including_other_seeds():
    _, _, _, record = fixture()
    seed2 = replace(record, trajectory_id="seed2")
    manifest = SplitManifest([record, seed2])
    assert len(manifest.allowed_records("train")) == 2
    with pytest.raises(ValueError, match="condition"):
        SplitManifest([record, replace(seed2, split="test")]).validate()
    with pytest.raises(ValueError, match="duplicate"):
        SplitManifest([record, record]).validate()
    with pytest.raises(PermissionError):
        manifest.allowed_records("protected")


@pytest.mark.parametrize("kind", ["history_shape", "d_lower", "nonfinite", "negative_history", "dtype"])
def test_state_rejects_corrupted_fields(kind):
    mesh, material, state, _ = fixture()
    modifications = {
        "history_shape": {"history": state.history.mean(dim=1)},
        "d_lower": {"d_lower": state.d + 1},
        "nonfinite": {"u": state.u + float("nan")},
        "negative_history": {"history": -state.history},
        "dtype": {"d": state.d.float()},
    }
    with pytest.raises(ValueError):
        replace(state, **modifications[kind]).validate(mesh, material)


def test_mesh_rejects_clockwise_and_unsupported_nodes():
    mesh, _, _, _ = fixture()
    with pytest.raises(ValueError, match="Jacobian"):
        replace(mesh, conn=torch.tensor([[0, 3, 2, 1]])).validate()
    with pytest.raises(ValueError, match="unsupported"):
        replace(mesh, xy=torch.cat((mesh.xy, mesh.xy[:1]))).validate()


@pytest.mark.parametrize("kind", ["damage", "alpha", "reference"])
def test_adapter_rejects_reference_evolution_or_identity_drift(kind):
    mesh, material, state, record = fixture()
    states = sequence(state)
    if kind == "damage":
        states[-1] = replace(states[-1], d=state.d, d_lower=state.d_lower)
    elif kind == "alpha":
        history = states[-1].history.clone()
        history[..., 1] = 0.
        states[-1] = replace(states[-1], history=history)
    else:
        states[-1] = replace(states[-1], key=replace(states[-1].key, reference_id="wrong"))
    with pytest.raises(ValueError):
        load_trajectory(record, lambda _: states, mesh, material)


def test_fyr_semantics_are_not_silently_coerced():
    mesh, material, _, record = fixture()
    called = []
    with pytest.raises(ValueError, match="semantics"):
        load_trajectory(replace(record, semantics="fyr_pidl_hist_alpha_hist_fat"),
                        lambda _: called.append(True), mesh, material)
    assert called == []


@pytest.mark.parametrize("values", [None, (210., .3, 9., .1, .5, 2., 1e-8, 1.)])
def test_material_identity_is_checked_before_loading(values):
    mesh, material, _, record = fixture()
    called = []
    with pytest.raises(ValueError, match="material"):
        load_trajectory(replace(record, material_values=values), lambda _: called.append(True), mesh, material)
    assert called == []


def test_post_commit_stale_damage_lower_bound_is_rejected():
    mesh, material, state, record = fixture()
    with pytest.raises(ValueError, match="lower bound must equal"):
        replace(state, d_lower=torch.zeros_like(state.d)).validate(mesh, material)
    states = sequence(state)
    states[1] = replace(states[1], d_lower=state.d)
    with pytest.raises(ValueError, match="lower bound must equal"):
        load_trajectory(record, lambda _: states, mesh, material)


@pytest.mark.parametrize("kind", ["zero_loaded_displacement", "shear", "bottom_motion"])
def test_source_and_target_displacements_obey_boundary_family(kind):
    mesh, material, state, record = fixture()
    states = sequence(state)
    invalid = states[1].u.clone()
    if kind == "zero_loaded_displacement":
        invalid.zero_()
    elif kind == "shear":
        invalid[2:, 0] = .1
    else:
        invalid[:2, 1] = .1
    states[1] = replace(states[1], u=invalid)
    with pytest.raises(ValueError, match="boundary family"):
        states[1].validate(mesh, material)
    with pytest.raises(ValueError, match="boundary family"):
        load_trajectory(record, lambda _: states, mesh, material)


def test_boundary_family_metadata_denied_before_loader():
    mesh, material, _, record = fixture()
    called = []
    with pytest.raises(ValueError, match="boundary family"):
        load_trajectory(replace(record, boundary_family="shear_x"),
                        lambda _: called.append(True), mesh, material)
    assert called == []


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_boundary_roundoff_tolerance_tracks_load_and_dtype(dtype):
    mesh, material, state, _ = fixture()
    mesh = replace(mesh, xy=mesh.xy.to(dtype))
    state = replace(state, u=state.u.to(dtype), d=state.d.to(dtype),
                    d_lower=state.d_lower.to(dtype), history=state.history.to(dtype))
    load = 1e-12
    displacement = state.u.clone()
    displacement[2:, 1] = load
    state = replace(state, key=replace(state.key, load=load), u=displacement)
    state.validate(mesh, material)
    roundoff = displacement.clone()
    roundoff[2:, 1] += 2 * torch.finfo(dtype).eps * load
    replace(state, u=roundoff).validate(mesh, material)
    with pytest.raises(ValueError, match="boundary family"):
        replace(state, u=torch.zeros_like(displacement)).validate(mesh, material)


def decoded_fixture():
    mesh, material, state, _ = fixture()
    loaded = sequence(state)[1]
    history_four = torch.cat((loaded.history, loaded.fatigue(material)[..., None]), dim=-1)
    decoded = SimpleNamespace(logical_cycle=1, logical_substep=1, source_state_key="c0001_s01",
                              imposed_displacement=.1, u_node=loaded.u.numpy().copy(),
                              d_node=loaded.d.numpy().copy(), history_gp=history_four.numpy().copy())
    return decoded, loaded.key, mesh, material


def test_decoded_stage0a_adapter_copies_native_arrays_and_checks_derived_channel():
    decoded, key, mesh, material = decoded_fixture()
    state = adapt_decoded_stage0a(decoded, key, mesh, material,
                                 source_timing="post_history_commit", source_semantics=SEMANTICS)
    assert state.history.shape == (1, 4, 3)
    torch.testing.assert_close(state.fatigue(material), torch.as_tensor(decoded.history_gp[..., 3]))
    assert torch.equal(state.d_lower, state.d)
    decoded.d_node[:] = 0
    decoded.history_gp[:] = 0
    assert bool((state.d == .2).all()) and bool((state.history == 1.).all())


@pytest.mark.parametrize("fault", ["timing", "semantics", "alias", "pre_cycle", "factor",
                                     "load", "cycle", "history_support", "boundary"])
def test_decoded_stage0a_adapter_rejects_semantic_and_field_mismatches(fault):
    decoded, key, mesh, material = decoded_fixture()
    timing, semantics = "post_history_commit", SEMANTICS
    if fault == "timing":
        timing = "pre_cycle_committed"
    elif fault == "semantics":
        semantics = "FYR_PIDL"
    elif fault == "alias":
        decoded.source_state_key = "c0000_s05"
    elif fault == "pre_cycle":
        key = replace(key, substep=0)
        decoded.logical_substep = 0
        decoded.source_state_key = "c0001_s00"
    elif fault == "factor":
        decoded.history_gp[..., 3] = 0
    elif fault == "load":
        decoded.imposed_displacement = .2
    elif fault == "cycle":
        decoded.logical_cycle = 2
    elif fault == "history_support":
        decoded.history_gp = decoded.history_gp.mean(axis=1)
    else:
        decoded.u_node[:] = 0
    with pytest.raises(ValueError):
        adapt_decoded_stage0a(decoded, key, mesh, material,
                             source_timing=timing, source_semantics=semantics)
