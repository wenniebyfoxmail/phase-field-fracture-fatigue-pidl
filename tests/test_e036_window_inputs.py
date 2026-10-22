"""Saved-input and identity checks only; no project solver is called."""
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "s04_e036"))
import prepare_predecessor as prep
from window_inputs import (CASES, GP_ORDER, SCHEMA, load_case, load_manifest,
                           native_mesh_coordinates, optimizer_work,
                           predecessor_key, sha256, state_key, validate_budget)


def _budget():
    return dict(updates_per_block=200, max_updates_per_step=2000, max_outer=10,
                step_wall_seconds=600, job_wall_seconds=7200, cumulative_resource_limit=None)


@pytest.mark.parametrize("cycle,first_substep,expected", [
    (1, 1, (1, 0, 0.)), (83, 1, (82, 5, 0.)),
    (20, 4, (20, 3, .08999988)), (60, 4, (60, 3, .08999988)),
])
def test_predecessor_is_the_actual_previous_load_state(cycle, first_substep, expected):
    key = predecessor_key("native-u012", cycle, first_substep)
    assert (key["cycle"], key["substep"], key["displacement"]) == expected
    assert key["timing"] == "post_commit"
    assert key["gp_order"] == GP_ORDER
    assert key["trajectory"] == "native-u012"


@pytest.mark.parametrize("cycle,substep", [(0, 1), (2, 0), (1, 6), (True, 1), (1, 1.0)])
def test_nonphysical_or_ambiguous_state_keys_are_rejected(cycle, substep):
    with pytest.raises(ValueError):
        state_key("native-u012", cycle, substep)


@pytest.mark.parametrize("change", [
    {"max_updates_per_step": 2001}, {"max_outer": 11}, {"updates_per_block": 100},
    {"updates_per_block": 200.0},
    {"job_wall_seconds": float("nan")}, {"step_wall_seconds": True},
    {"job_wall_seconds": 0}, {"extra_budget": "old approval"},
    {"cumulative_resource_limit": 48 * 3600}, {"total_wall_seconds": 86400},
])
def test_budget_cannot_silently_expand_or_inherit_old_authority(change):
    budget = _budget()
    budget.update(change)
    with pytest.raises(ValueError):
        validate_budget(budget)


def test_job_anti_hang_is_explicit_but_not_a_cumulative_resource_cap():
    budget = _budget()
    budget.update(step_wall_seconds=7200, job_wall_seconds=72 * 3600)
    validate_budget(budget)


def test_future_target_is_not_a_manifest_solver_input(tmp_path):
    manifest = dict(schema=SCHEMA, trajectory="native-u012", mesh={}, common_problem={},
                    cases={name: {} for name in CASES}, budget=_budget(),
                    future_targets="c83_s4_target.npz")
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    # Reject the target field before attempting to access otherwise absent inputs.
    with pytest.raises(ValueError, match="future targets"):
        load_manifest(path)


def _small_state(key, n_cells=2):
    nodes = np.array([[-.5, -.5], [.5, -.5], [-.5, .5], [.5, .5]])
    history = np.arange(n_cells * 4, dtype=float).reshape(n_cells, 4) * .01 + .6
    arrays = dict(u=np.zeros(4), v=np.array([0., 0., key["displacement"], key["displacement"]]),
                  damage=np.array([1., .2, .3, .4]), history=history,
                  active_driver=np.full((n_cells, 4), .03),
                  f_commit=(1. / (history + .5)) ** 2)
    common = dict(ordered_mesh_sha256_f32_i64="a" * 64, fixed_damage_nodes_zero_based=[0],
                  acceptance_config={"bc_tol": 5e-8})
    return nodes, arrays, common


def _write_mat(path, key, *, initial=False, missing_history=False):
    nodes, arrays, common = _small_state(key)
    native = np.zeros((2, 4, 4))
    native[:, :, 0] = 87.  # Non-fatigue channel must not be mistaken for A.
    for channel, name in enumerate(("history", "active_driver", "f_commit"), start=1):
        native[:, :, channel] = arrays[name]
    with h5py.File(path, "w") as handle:
        group = handle.create_group("initial_state") if initial else handle
        group.create_dataset("displ", data=np.r_[arrays["u"], arrays["v"]].reshape(1, -1))
        group.create_dataset("p_field", data=arrays["damage"].reshape(1, -1))
        group.create_dataset("p_field_old", data=arrays["damage"].reshape(1, -1))
        if not missing_history:
            group.create_dataset("history_vars_old", data=native.transpose(2, 1, 0))
        if initial:
            group.create_dataset("cycle", data=[[key["cycle"]]])
            group.create_dataset("substep", data=[[key["substep"]]])
            group.create_dataset("imposed_displacement", data=[[0.]])
            timing = group.create_dataset("timing", data=np.array([ord(c) for c in "pre_cycle_committed"], dtype="uint16").reshape(-1, 1))
            timing.attrs["MATLAB_class"] = np.bytes_("char")
        else:
            cycle = group.create_group("SOL_CYCL_VAR")
            cycle.create_dataset("n_cycle", data=[[key["cycle"]]])
            group.create_dataset("i_step_completed", data=[[key["substep"]]])
    return nodes, arrays, common


def test_mat_axes_channels_and_block_displacement_are_preserved(tmp_path):
    key = state_key("native-u012", 20, 3)
    path = tmp_path / "step_checkpoint.mat"
    nodes, expected, common = _write_mat(path, key)
    actual, timing = prep.read_mat_state(path, "step-checkpoint", "/", key, 4, 2)
    for name in expected:
        np.testing.assert_array_equal(actual[name], expected[name])
    prep.validate_state(actual, key, nodes, 2, common)
    assert timing == "post_step_checkpoint"


def test_mat_internal_step_prevents_using_future_target_as_predecessor(tmp_path):
    path = tmp_path / "misleading_filename_c20s3.mat"
    _write_mat(path, state_key("native-u012", 20, 4))
    with pytest.raises(ValueError, match="MAT-internal cycle/substep"):
        prep.read_mat_state(path, "step-checkpoint", "/", state_key("native-u012", 20, 3), 4, 2)


def test_mat_uncommitted_damage_is_rejected(tmp_path):
    key = state_key("native-u012", 20, 3)
    path = tmp_path / "step_checkpoint.mat"
    _write_mat(path, key)
    with h5py.File(path, "r+") as handle:
        handle["p_field_old"][0, 1] = .1
    with pytest.raises(ValueError, match="same committed damage"):
        prep.read_mat_state(path, "step-checkpoint", "/", key, 4, 2)


def test_c1s0_needs_saved_history_not_damage_only_analysis(tmp_path):
    key = state_key("native-u012", 1, 0)
    complete = tmp_path / "initial_state.mat"
    nodes, expected, common = _write_mat(complete, key, initial=True)
    actual, timing = prep.read_mat_state(complete, "stage0b-initial", "initial_state", key, 4, 2)
    prep.validate_state(actual, key, nodes, 2, common)
    np.testing.assert_array_equal(actual["history"], expected["history"])
    assert timing == "pre_cycle_committed"
    incomplete = tmp_path / "state0_analysis.mat"
    _write_mat(incomplete, key, initial=True, missing_history=True)
    with pytest.raises(ValueError, match="missing history_vars_old"):
        prep.read_mat_state(incomplete, "stage0b-initial", "initial_state", key, 4, 2)
    with pytest.raises(ValueError, match="complete stage0b"):
        prep.read_mat_state(complete, "step-checkpoint", "initial_state", key, 4, 2)


def test_top_load_and_history_identity_cannot_be_inferred_from_filename():
    key = state_key("native-u012", 20, 3)
    nodes, arrays, common = _small_state(key)
    arrays["v"][2:] = .11999988
    with pytest.raises(ValueError, match="displacement disagrees"):
        prep.validate_state(arrays, key, nodes, 2, common)
    arrays["v"][2:] = key["displacement"]
    arrays["f_commit"][0, 0] = 1.
    with pytest.raises(ValueError, match="A/f relation"):
        prep.validate_state(arrays, key, nodes, 2, common)


def test_standard_future_state_fails_even_with_matching_support(tmp_path):
    future = state_key("native-u012", 20, 4)
    _, arrays, common = _small_state(future)
    path = tmp_path / "predecessor.npz"
    np.savez(path, **arrays, state_key_json=json.dumps(future),
             ordered_mesh_sha256_f32_i64=common["ordered_mesh_sha256_f32_i64"])
    with pytest.raises(ValueError, match="physical key mismatch"):
        prep.read_standard_state(path, state_key("native-u012", 20, 3), common["ordered_mesh_sha256_f32_i64"])


def test_conversion_is_exclusive_and_never_creates_numerical_admission(tmp_path, monkeypatch):
    key = state_key("native-u012", 20, 3)
    nodes, arrays, common = _small_state(key)
    source, mesh, common_file = (tmp_path / name for name in ("source.npz", "mesh.npz", "common.json"))
    np.savez(source, **arrays, state_key_json=json.dumps(key),
             ordered_mesh_sha256_f32_i64=common["ordered_mesh_sha256_f32_i64"])
    mesh.write_bytes(b"synthetic mesh bytes")
    common_file.write_text(json.dumps(common))
    monkeypatch.setattr(prep, "load_support", lambda *_: (nodes, np.zeros((2, 4)), common))
    output = tmp_path / "converted.npz"
    kwargs = dict(source=source, source_sha256=sha256(source), source_kind="standard-npz", mat_group="/",
                  mesh=mesh, mesh_sha256=sha256(mesh), common_problem=common_file,
                  common_problem_sha256=sha256(common_file), trajectory="native-u012", cycle=20, substep=3,
                  output=output)
    receipt = prep.prepare(**kwargs)
    assert receipt["status"] == "converted_only_not_numerical_admission"
    with np.load(output, allow_pickle=False) as data:
        provenance = json.loads(str(data["preparation_json"].item()))
        assert data["source_checkpoint_sha256"].item() == sha256(source)
    assert provenance["native_residual_checked"] is False
    assert provenance["checkpoint_readback_verified"] is False
    assert "accepted" not in provenance
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        prep.prepare(**kwargs)
    assert output.read_bytes() == original


def test_case_schema_rejects_future_target_even_if_paths_are_absent():
    doc = dict(cases={"c20s4": dict(predecessor={}, admission={}, network={}, target={})})
    with pytest.raises(ValueError, match="initial network only"):
        load_case("c20s4", doc, Path("."), 4, 2, {})


def test_native_admission_from_another_source_checkpoint_is_rejected(tmp_path):
    key = state_key("native-u012", 20, 3)
    _, arrays, common = _small_state(key)
    source = tmp_path / "source.mat"
    source.write_bytes(b"the actually audited checkpoint")
    evidence = tmp_path / "native_evidence.json"
    evidence.write_text('{"description":"synthetic evidence fixture"}')
    network = tmp_path / "initial_network.pt"
    network.write_bytes(b"network identity fixture; never deserialized")
    predecessor = tmp_path / "predecessor.npz"
    np.savez(predecessor, **arrays, state_key_json=json.dumps(key),
             ordered_mesh_sha256_f32_i64=common["ordered_mesh_sha256_f32_i64"],
             source_checkpoint_sha256="b" * 64,
             preparation_json=json.dumps({"schema": "s04_e036_predecessor_preparation_v1"}))
    bind = lambda path: {"path": str(path), "sha256": sha256(path)}
    admission = tmp_path / "admission.json"
    admission.write_text(json.dumps(dict(schema="s04_e036_predecessor_admission_v1", accepted=True,
        predecessor_sha256=sha256(predecessor), state_key=key,
        ordered_mesh_sha256_f32_i64=common["ordered_mesh_sha256_f32_i64"],
        native_residual_checked=True, checkpoint_readback_verified=True,
        native_residual_evidence=bind(evidence), checkpoint_readback_evidence=bind(evidence),
        source_checkpoint=bind(source))))
    doc = dict(trajectory="native-u012", cases={"c20s4": dict(
        predecessor=bind(predecessor), admission=bind(admission), network=bind(network))})
    with pytest.raises(ValueError, match="different checkpoints"):
        load_case("c20s4", doc, tmp_path, 4, 2, common)


def test_native_coordinates_are_not_float32_promoted_to_float64():
    native = np.array([[.123456789123, .234567891234]], dtype=np.float64)
    solver = native.astype(np.float32)
    assert not np.array_equal(native, solver.astype(np.float64))
    np.testing.assert_array_equal(native_mesh_coordinates(dict(node_coords=solver,
                                      canonical_node_coords=native)), native)
    with pytest.raises(ValueError, match="saved canonical_node_coords"):
        native_mesh_coordinates(dict(node_coords=solver))
    with pytest.raises(ValueError, match="disagree"):
        native_mesh_coordinates(dict(node_coords=solver, canonical_node_coords=native + .01))
    np.testing.assert_array_equal(native_mesh_coordinates(dict(node_coords=native)), native)


def _e011_archive(path, key, initial=False):
    nodes, arrays, common = _small_state(key)
    cells = np.array([[0, 1, 3, 2], [1, 3, 2, 0]])
    native = np.zeros((2, 4, 4))
    if initial:
        arrays.update(history=np.zeros((2, 4)), active_driver=np.zeros((2, 4)), f_commit=np.ones((2, 4)))
    for channel, name in enumerate(("history", "active_driver", "f_commit"), start=1):
        native[:, :, channel] = arrays[name]
    def put(group, name, values):
        values = np.asarray(values)
        group.create_dataset(name, data=values.transpose(tuple(reversed(range(values.ndim)))))
    with h5py.File(path, "w") as file:
        base = file if initial else file.create_group("request28_snapshot")
        put(base, "node_coords", nodes)
        put(base, "connectivity", cells + 1)
        if initial:
            meta = file.create_group("common_meta")
            put(meta, "cycle", [[1]])
            put(meta, "version", [[0]])
            group = file.create_group("common")
            for name, value in dict(u=np.r_[arrays["u"], arrays["v"]].reshape(-1, 1),
                                    d=arrays["damage"].reshape(-1, 1),
                                    lower=arrays["damage"].reshape(-1, 1), history=native,
                                    raw=np.zeros((2, 4)), version=np.array([[0]])).items():
                put(group, name, value)
        else:
            for name, value in dict(cycle=[[key["cycle"]]], substep=[[key["substep"]]],
                                    damage_committed=[[1]], history_committed=[[1]], cyclemax_updated=[[1]],
                                    load_factor=[[key["displacement"] / .12]],
                                    u_node=np.column_stack((arrays["u"], arrays["v"])),
                                    d_node=arrays["damage"].reshape(-1, 1), history_vars_old=native,
                                    alpha_bar_gp=arrays["history"], psi_eff_prev_gp=arrays["active_driver"],
                                    f_alpha_gp=arrays["f_commit"]).items():
                put(base, name, value)
    return nodes, cells, arrays


@pytest.mark.parametrize("initial", [False, True])
def test_e011_explicit_schemas_preserve_native_arrays(tmp_path, initial):
    key = state_key("native-u012", 1 if initial else 20, 0 if initial else 3)
    path = tmp_path / "saved.mat"
    nodes, cells, arrays = _e011_archive(path, key, initial)
    kind = "e011-common-initial" if initial else "e011-request28"
    actual, timing = prep.read_e011_state(path, kind, key, nodes, cells)
    for name in arrays:
        np.testing.assert_array_equal(actual[name], arrays[name])
    assert "not_original_stage0b" in timing if initial else "committed_flags" in timing


@pytest.mark.parametrize("field,value,match", [("substep", 4, "cycle/substep"),
    ("history_committed", 0, "explicitly committed"), ("load_factor", 1., "saved load"),
    ("alpha_bar_gp", 99., "history alias")])
def test_e011_request28_rejects_false_state_identity(tmp_path, field, value, match):
    key = state_key("native-u012", 20, 3)
    path = tmp_path / "saved.mat"
    nodes, cells, _ = _e011_archive(path, key)
    with h5py.File(path, "r+") as file:
        file["request28_snapshot"][field][...] = value
    with pytest.raises(ValueError, match=match):
        prep.read_e011_state(path, "e011-request28", key, nodes, cells)


def test_e011_same_float32_digest_does_not_excuse_native_coordinate_drift(tmp_path):
    key = state_key("native-u012", 20, 3)
    path = tmp_path / "saved.mat"
    nodes, cells, _ = _e011_archive(path, key)
    nodes[0, 0] += 1e-10
    with pytest.raises(ValueError, match="ordered coordinates"):
        prep.read_e011_state(path, "e011-request28", key, nodes, cells)


def test_work_counter_retains_completed_failed_step_and_window_work():
    assert optimizer_work(17, 400) == dict(current_step_updates=17,
                                          window_updates_before_step=400, window_updates=417)
    assert optimizer_work(2000, 8000)["window_updates"] == 10000
    for current, before in ((True, 0), (2001, 0), (1, 1), (1, None), (-1, 0), (0, 8200)):
        with pytest.raises(ValueError):
            optimizer_work(current, before)
