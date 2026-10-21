#!/usr/bin/env python3
"""Convert saved native states to explicit predecessor inputs; never solve.

The output binds bytes and state identity only. It is not numerical admission:
native residual and checkpoint-readback evidence must be supplied separately.
MATLAB v7.3 arrays are read with their storage-axis reversal, and the audited
native displacement ordering is [all ux; all uy], not alternating components.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from window_inputs import bound_file, read_json, sha256, state_key


ARRAY_NAMES = ("u", "v", "damage", "history", "active_driver", "f_commit")


def load_support(mesh_path, common_path):
    common = read_json(common_path)
    if common.get("schema") != "s04_e036_common_problem_v1":
        raise ValueError("unknown common problem schema")
    with np.load(mesh_path, allow_pickle=False) as data:
        nodes = np.asarray(data["node_coords"], dtype="<f4")
        raw_cells = np.asarray(data["connectivity"])
        cells = raw_cells.astype("<i8")
    if nodes.shape != (86756, 2) or cells.shape != (86408, 4):
        raise ValueError("only the frozen common Q4 mesh is supported")
    if (not np.isfinite(nodes).all() or not np.array_equal(raw_cells, cells)
            or cells.min() < 0 or cells.max() >= len(nodes)):
        raise ValueError("invalid ordered mesh")
    digest = hashlib.sha256(nodes.tobytes() + cells.tobytes()).hexdigest()
    if digest != common["ordered_mesh_sha256_f32_i64"]:
        raise ValueError("ordered mesh differs from common problem")
    indices = common["fixed_damage_nodes_zero_based"]
    expected = np.flatnonzero((nodes[:, 1] == 0) & (nodes[:, 0] >= -.5)
                              & (nodes[:, 0] <= 0)).tolist()
    if (len(expected) != 251 or indices != expected
            or common.get("fixed_damage_value") != 1.):
        raise ValueError("common problem lacks the canonical 251-node precrack")
    expected_policy = dict(mode="nodal_box_kkt", joint_tol=4e-4, u_tol=1e-6,
                           bounds_tol=1e-8, active_tol=1e-10, bc_tol=5e-8,
                           history_atol=2e-6, history_rtol=2e-6)
    if (common.get("acceptance_config") != expected_policy or common.get("tol_ir") != .001
            or common.get("recovery_penalty_coefficient") != 13781.25):
        raise ValueError("common problem differs from the declared E036 policy")
    return nodes, cells, common


def _mat_object(group, name):
    """Resolve scalar MATLAB struct references; do not guess cell arrays."""
    import h5py
    value = group
    for part in name.strip("/").split("/"):
        if part:
            if not isinstance(value, (h5py.File, h5py.Group)) or part not in value:
                raise ValueError(f"saved native state is missing {name}")
            value = value[part]
        while isinstance(value, h5py.Dataset) and h5py.check_dtype(ref=value.dtype) is not None:
            refs = np.asarray(value).reshape(-1)
            if len(refs) != 1 or not refs[0]:
                raise ValueError(f"{name} is not a scalar MATLAB struct field")
            value = value.file[refs[0]]
    return value


def _mat_array(group, name):
    import h5py
    value = _mat_object(group, name)
    if not isinstance(value, h5py.Dataset) or value.attrs.get("MATLAB_empty", 0):
        raise ValueError(f"{name} must be a saved nonempty numeric array")
    array = np.asarray(value)
    if array.dtype.kind not in "fiu" or not np.isfinite(array).all():
        raise ValueError(f"{name} must contain finite numeric values")
    # MATLAB (element, GP, channel) appears as (channel, GP, element).
    return array.transpose(tuple(reversed(range(array.ndim)))).copy()


def _mat_integer(group, name):
    array = _mat_array(group, name)
    if array.size != 1:
        raise ValueError(f"{name} must be one saved integer")
    value = float(array.item())
    if value != int(value):
        raise ValueError(f"{name} must be one saved integer")
    return int(value)


def _mat_text(group, name):
    import h5py
    value = _mat_object(group, name)
    if not isinstance(value, h5py.Dataset):
        raise ValueError(f"{name} must be explicit saved text")
    array = np.asarray(value)
    if value.attrs.get("MATLAB_class") in (b"char", "char"):
        return "".join(chr(int(item)) for item in array.reshape(-1))
    if array.size == 1 and array.dtype.kind in "SU":
        item = array.item()
        return item.decode("utf-8") if isinstance(item, bytes) else str(item)
    raise ValueError(f"unsupported opaque MATLAB text in {name}; explicit char metadata required")


def read_mat_state(source, source_kind, mat_group, key, n_nodes, n_cells):
    import h5py
    with h5py.File(source, "r") as handle:
        group = _mat_object(handle, mat_group)
        if source_kind == "step-checkpoint":
            if key["substep"] == 0:
                raise ValueError("c1s0 requires complete stage0b initial_state or standard NPZ")
            actual_cycle = _mat_integer(group, "SOL_CYCL_VAR/n_cycle")
            actual_substep = _mat_integer(group, "i_step_completed")
            native_timing = "post_step_checkpoint"
        elif source_kind == "stage0b-initial":
            if (key["cycle"], key["substep"]) != (1, 0):
                raise ValueError("stage0b initial_state can only supply c1s0")
            actual_cycle = _mat_integer(group, "cycle")
            actual_substep = _mat_integer(group, "substep")
            native_timing = _mat_text(group, "timing")
            if native_timing != "pre_cycle_committed":
                raise ValueError("stage0b initial_state is not the committed pre-cycle state")
            imposed = _mat_array(group, "imposed_displacement")
            if imposed.size != 1 or float(imposed.item()) != 0.:
                raise ValueError("stage0b initial_state must have zero imposed displacement")
        else:
            raise ValueError("unsupported MATLAB predecessor source kind")
        if (actual_cycle, actual_substep) != (key["cycle"], key["substep"]):
            raise ValueError("MAT-internal cycle/substep differs from requested physical key")
        displacement = _mat_array(group, "displ").reshape(-1)
        damage = _mat_array(group, "p_field").reshape(-1)
        old_damage = _mat_array(group, "p_field_old").reshape(-1)
        history = _mat_array(group, "history_vars_old")
        if displacement.shape != (2 * n_nodes,) or damage.shape != (n_nodes,):
            raise ValueError("native displacement/damage support mismatch")
        if old_damage.shape != damage.shape or not np.array_equal(damage, old_damage):
            raise ValueError("p_field and p_field_old must describe the same committed damage")
        if history.shape != (n_cells, 4, 4):
            raise ValueError("complete native Q4 history_vars_old (elements,4,4) is required")
        arrays = dict(u=displacement[:n_nodes], v=displacement[n_nodes:], damage=damage,
                      history=history[:, :, 1], active_driver=history[:, :, 2],
                      f_commit=history[:, :, 3])
    return {name: value.copy() for name, value in arrays.items()}, native_timing


def read_standard_state(source, key, digest):
    with np.load(source, allow_pickle=False) as data:
        arrays = {name: np.asarray(data[name]).copy() for name in ARRAY_NAMES}
        if json.loads(str(data["state_key_json"].item())) != key:
            raise ValueError("standard predecessor physical key mismatch")
        if str(data["ordered_mesh_sha256_f32_i64"].item()) != digest:
            raise ValueError("standard predecessor ordered mesh mismatch")
    return arrays, "standard_npz_post_commit"


def validate_state(arrays, key, nodes, n_cells, common):
    for name, value in arrays.items():
        shape = (len(nodes),) if name in {"u", "v", "damage"} else (n_cells, 4)
        if value.shape != shape or value.dtype.kind not in "fiu" or not np.isfinite(value).all():
            raise ValueError(f"invalid predecessor field: {name}")
    if ((arrays["damage"] < 0).any() or (arrays["damage"] > 1).any()
            or (arrays["history"] < 0).any() or (arrays["active_driver"] < 0).any()):
        raise ValueError("saved predecessor is outside physical bounds")
    expected_f = np.where(arrays["history"] > .5, (1. / (arrays["history"] + .5)) ** 2, 1.)
    if not np.allclose(expected_f, arrays["f_commit"], atol=1e-10, rtol=1e-10):
        raise ValueError("history channels 2/4 do not satisfy the declared A/f relation")
    bottom, top = nodes[:, 1] == nodes[:, 1].min(), nodes[:, 1] == nodes[:, 1].max()
    if not bottom.any() or not top.any() or (bottom & top).any():
        raise ValueError("invalid top/bottom support")
    tol = float(common["acceptance_config"]["bc_tol"])
    if (not np.allclose(arrays["u"][bottom | top], 0., atol=tol, rtol=0.)
            or not np.allclose(arrays["v"][bottom], 0., atol=tol, rtol=0.)
            or not np.allclose(arrays["v"][top], key["displacement"], atol=tol, rtol=0.)):
        raise ValueError("saved top/bottom displacement disagrees with physical key")
    if not np.allclose(arrays["damage"][common["fixed_damage_nodes_zero_based"]],
                       1., atol=tol, rtol=0.):
        raise ValueError("saved precrack damage violates the common hard boundary")


def prepare(*, source, source_sha256, source_kind, mat_group, mesh, mesh_sha256,
            common_problem, common_problem_sha256, trajectory, cycle, substep, output):
    if type(cycle) is not int or type(substep) is not int:
        raise ValueError("cycle and substep must be explicit integers")
    key = state_key(trajectory, cycle, substep)
    inputs = {}
    for name, path, digest in (("source_checkpoint", source, source_sha256),
                               ("mesh", mesh, mesh_sha256),
                               ("common_problem", common_problem, common_problem_sha256)):
        inputs[name] = dict(path=str(bound_file(dict(path=str(path), sha256=digest), Path.cwd())),
                            sha256=digest)
    nodes, cells, common = load_support(inputs["mesh"]["path"], inputs["common_problem"]["path"])
    digest = common["ordered_mesh_sha256_f32_i64"]
    if source_kind == "standard-npz":
        arrays, native_timing = read_standard_state(inputs["source_checkpoint"]["path"], key, digest)
    else:
        arrays, native_timing = read_mat_state(inputs["source_checkpoint"]["path"], source_kind,
                                              mat_group, key, len(nodes), len(cells))
    validate_state(arrays, key, nodes, len(cells), common)
    # Detect changes to inputs while they were being read, before creating output.
    for spec in inputs.values():
        bound_file(spec, Path.cwd())
    provenance = dict(schema="s04_e036_predecessor_preparation_v1", source_kind=source_kind,
                      native_timing=native_timing, mat_group=mat_group,
                      inputs=inputs, state_key=key,
                      status="converted_only_not_numerical_admission",
                      native_residual_checked=False, checkpoint_readback_verified=False)
    output = Path(output)
    # Exclusive creation prevents overwriting either an archive or an old attempt.
    with output.open("xb") as stream:
        np.savez_compressed(stream, **arrays, state_key_json=json.dumps(key, sort_keys=True),
                            ordered_mesh_sha256_f32_i64=digest,
                            source_checkpoint_sha256=source_sha256,
                            preparation_json=json.dumps(provenance, sort_keys=True))
    return dict(output=str(output.resolve()), sha256=sha256(output), state_key=key,
                status=provenance["status"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--source-kind", choices=("step-checkpoint", "stage0b-initial", "standard-npz"), required=True)
    parser.add_argument("--mat-group", default="/", help="Explicit saved struct group; '/' for ordinary step checkpoints")
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--mesh-sha256", required=True)
    parser.add_argument("--common-problem", type=Path, required=True)
    parser.add_argument("--common-problem-sha256", required=True)
    parser.add_argument("--trajectory", required=True)
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--substep", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(prepare(**vars(parser.parse_args())), indent=2))


if __name__ == "__main__":
    main()
