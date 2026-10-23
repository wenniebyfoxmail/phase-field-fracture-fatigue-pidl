"""Explicit conditional-window inputs. Reading these never starts a solver.

Only an admitted *predecessor* enters optimization. Future FEM targets belong
to a separate scoring process and are deliberately absent from this schema.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

SCHEMA = "s04_e036_paired_windows_v2"
PARTITION_SCHEMA = "s04_e036_paired_windows_v3"
GP_ORDER = "(+,+),(-,+),(+,-),(-,-)"
LOADS = (.02999988, .05999988, .08999988, .11999988, 0.)
CASES = {"c1": (1, (1, 2, 3, 4, 5)), "c83": (83, (1, 2, 3, 4, 5)),
         "c20s4": (20, (4,)), "c60s4": (60, (4,))}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    def reject(value):
        raise ValueError(f"nonfinite JSON constant: {value}")
    return json.loads(Path(path).read_text(), parse_constant=reject)


def bound_file(spec, root):
    if set(spec) != {"path", "sha256"}:
        raise ValueError("each input needs exactly path and sha256")
    path = Path(spec["path"])
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    expected = spec["sha256"]
    if not isinstance(expected, str) or len(expected) != 64 or sha256(path) != expected:
        raise ValueError(f"input SHA256 mismatch: {path}")
    return path


def state_key(trajectory, cycle, substep, timing="post_commit"):
    if not isinstance(trajectory, str) or not trajectory:
        raise ValueError("explicit trajectory identity is required")
    if (type(cycle) is not int or type(substep) is not int or cycle < 1
            or substep not in range(6) or (substep == 0 and cycle != 1) or timing != "post_commit"):
        raise ValueError("invalid five-substep physical key")
    return dict(trajectory=trajectory, nominal_umax=.12, cycle=cycle, substep=substep,
                displacement=0. if substep == 0 else LOADS[substep - 1],
                timing=timing, gp_order=GP_ORDER)


def predecessor_key(trajectory, cycle, first_substep):
    if type(first_substep) is not int or first_substep not in range(1, 6):
        raise ValueError("invalid first substep")
    state_key(trajectory, cycle, first_substep)
    if first_substep > 1:
        return state_key(trajectory, cycle, first_substep - 1)
    return state_key(trajectory, 1, 0) if cycle == 1 else state_key(trajectory, cycle - 1, 5)


def native_mesh_coordinates(data):
    """Use saved native precision; never promote rounded float32 as native."""
    solver = np.asarray(data["node_coords"])
    if "canonical_node_coords" in data:
        native = np.asarray(data["canonical_node_coords"])
        if (native.dtype.kind != "f" or native.dtype.itemsize < 8
                or native.shape != solver.shape or not np.isfinite(native).all()
                or not np.array_equal(native.astype("<f4"), solver.astype("<f4"))):
            raise ValueError("canonical native coordinates disagree with solver-visible coordinates")
    else:
        native = solver
        if native.dtype.kind != "f" or native.dtype.itemsize < 8:
            raise ValueError("float32 mesh needs saved canonical_node_coords for native replay")
    return np.asarray(native, dtype="<f8")


def execution_cases(requested_case):
    """Execution partition only; scientific cases remain the fixed four."""
    if requested_case is not None and requested_case not in CASES:
        raise ValueError("unknown requested case")
    return tuple(CASES) if requested_case is None else (requested_case,)


def validate_case_partition(doc, root, requested_case):
    """Bind all networks; permit paired null preimages only outside this job."""
    selected = execution_cases(requested_case)
    if set(doc.get("cases", {})) != set(CASES):
        raise ValueError("all four scientific cases must remain declared")
    missing = []
    for name, spec in doc["cases"].items():
        if not isinstance(spec, dict) or set(spec) != {"predecessor", "admission", "network"}:
            raise ValueError("case requires predecessor, admission and initial network only")
        if not isinstance(spec["network"], dict):
            raise ValueError("every declared case needs a real fixed network binding")
        bound_file(spec["network"], root)
        nulls = [spec[key] is None for key in ("predecessor", "admission")]
        if any(nulls):
            if not all(nulls):
                raise ValueError("unavailable predecessor and admission must both be null")
            if doc["schema"] != PARTITION_SCHEMA or name in selected:
                raise ValueError("null predecessor/admission permitted only for unselected v3 cases")
            missing.append(name)
        else:
            for key in ("predecessor", "admission"):
                if not isinstance(spec[key], dict):
                    raise ValueError("available predecessor/admission require real file bindings")
                bound_file(spec[key], root)
    return tuple(missing)


def load_manifest(path, *, requested_case=None):
    path = Path(path).resolve()
    doc = read_json(path)
    if doc.get("schema") not in {SCHEMA, PARTITION_SCHEMA} or set(doc.get("cases", {})) != set(CASES):
        raise ValueError("requires exactly c1/c83 windows and c20s4/c60s4 endpoints")
    if set(doc) != {"schema", "trajectory", "mesh", "common_problem", "cases", "budget"}:
        raise ValueError("unexpected manifest keys (future targets are not solver inputs)")
    root = path.parent
    validate_case_partition(doc, root, requested_case)
    mesh_path = bound_file(doc["mesh"], root)
    common_path = bound_file(doc["common_problem"], root)
    common = read_json(common_path)
    with np.load(mesh_path, allow_pickle=False) as data:
        # Same names as the existing E011 precrack preparation export.
        # Retain source-coordinate precision for native float64 replay. Only
        # the established ordered-mesh digest uses float32 serialization.
        nodes = native_mesh_coordinates(data)
        raw_cells = np.asarray(data["connectivity"])
        cells = raw_cells.astype("<i8")
    if not np.array_equal(raw_cells, cells):
        raise ValueError("connectivity must contain exact integer indices")
    if nodes.shape != (86756, 2) or cells.shape != (86408, 4):
        raise ValueError("only the frozen common Q4 mesh is in scope")
    if not np.isfinite(nodes).all() or cells.min() < 0 or cells.max() >= len(nodes):
        raise ValueError("invalid mesh")
    digest = hashlib.sha256(nodes.astype("<f4").tobytes() + cells.tobytes()).hexdigest()
    if digest != common["ordered_mesh_sha256_f32_i64"]:
        raise ValueError("common problem and ordered mesh differ")
    if common.get("schema") != "s04_e036_common_problem_v1":
        raise ValueError("unknown common problem schema")
    fixed = np.flatnonzero((nodes[:, 1] == 0) & (nodes[:, 0] >= -.5) & (nodes[:, 0] <= 0)).tolist()
    if len(fixed) != 251 or common.get("fixed_damage_nodes_zero_based") != fixed or common.get("fixed_damage_value") != 1.:
        raise ValueError("common problem does not bind the canonical 251 crack nodes")
    expected_policy = dict(mode="nodal_box_kkt", joint_tol=4e-4, u_tol=1e-6,
                           bounds_tol=1e-8, active_tol=1e-10, bc_tol=5e-8,
                           history_atol=2e-6, history_rtol=2e-6)
    if (common.get("acceptance_config") != expected_policy or common.get("tol_ir") != .001
            or common.get("recovery_penalty_coefficient") != 13781.25):
        raise ValueError("acceptance/penalty policy differs from E036")
    validate_budget(doc["budget"])
    return doc, root, nodes, cells, common


def validate_budget(budget):
    if set(budget) != {"updates_per_block", "max_updates_per_step", "max_outer",
                       "step_wall_seconds", "job_wall_seconds", "cumulative_resource_limit"}:
        raise ValueError("explicit update and wall-clock budgets required")
    if any(type(budget[k]) is not int for k in ("updates_per_block", "max_updates_per_step", "max_outer")):
        raise ValueError("optimizer work limits must be integer counts")
    if (budget["updates_per_block"], budget["max_updates_per_step"], budget["max_outer"]) != (200, 2000, 10):
        raise ValueError("paired E036 arms require identical 10 x 200 update caps")
    if budget["cumulative_resource_limit"] is not None:
        raise ValueError("current authority has no cumulative resource limit")
    for key in ("step_wall_seconds", "job_wall_seconds"):
        value = budget[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"invalid explicit per-job anti-hang setting: {key}")


def optimizer_work(current_step_updates, window_updates_before_step):
    """Count completed RPROP updates, including rejected-step diagnostics."""
    if (type(current_step_updates) is not int or not 0 <= current_step_updates <= 2000
            or type(window_updates_before_step) is not int
            or not 0 <= window_updates_before_step <= 8000
            or window_updates_before_step % 200):
        raise ValueError("invalid current-step or accepted-window work count")
    return dict(current_step_updates=current_step_updates,
                window_updates_before_step=window_updates_before_step,
                window_updates=window_updates_before_step + current_step_updates)


def load_case(name, doc, root, n_nodes, n_cells, common):
    """Return one common preimage; missing/unqualified evidence is unavailable."""
    spec = doc["cases"][name]
    if set(spec) != {"predecessor", "admission", "network"}:
        raise ValueError("case requires predecessor, admission and initial network only")
    if spec["predecessor"] is None or spec["admission"] is None:
        raise ValueError("selected case has no admitted predecessor; no substitution")
    paths = {key: bound_file(value, root) for key, value in spec.items()}
    cycle, steps = CASES[name]
    key = predecessor_key(doc["trajectory"], cycle, steps[0])
    admission = read_json(paths["admission"])
    required = dict(schema="s04_e036_predecessor_admission_v1", accepted=True,
                    predecessor_sha256=spec["predecessor"]["sha256"], state_key=key,
                    ordered_mesh_sha256_f32_i64=common["ordered_mesh_sha256_f32_i64"],
                    native_residual_checked=True, checkpoint_readback_verified=True)
    if any(admission.get(k) != v for k, v in required.items()):
        raise ValueError("predecessor lacks matching native numerical/readback admission")
    if any(admission.get(k) is not True for k in ("accepted", "native_residual_checked", "checkpoint_readback_verified")):
        raise ValueError("admission requires explicit boolean results")
    # Admission must point to concrete evidence, not just an 'accepted' flag.
    for evidence in ("native_residual_evidence", "checkpoint_readback_evidence", "source_checkpoint"):
        bound_file(admission[evidence], paths["admission"].parent)
    with np.load(paths["predecessor"], allow_pickle=False) as data:
        arrays = {k: np.asarray(data[k]).copy() for k in
                  ("u", "v", "damage", "history", "active_driver", "f_commit")}
        stored_key = json.loads(str(data["state_key_json"].item()))
        stored_mesh = str(data["ordered_mesh_sha256_f32_i64"].item())
        source_sha = str(data["source_checkpoint_sha256"].item())
        preparation = json.loads(str(data["preparation_json"].item()))
    if stored_key != key or stored_mesh != common["ordered_mesh_sha256_f32_i64"]:
        raise ValueError("predecessor physical key or ordered support mismatch")
    if source_sha != admission["source_checkpoint"]["sha256"]:
        raise ValueError("admission and predecessor were produced from different checkpoints")
    if not isinstance(preparation, dict):
        raise ValueError("missing preparation provenance")
    for name_, value in arrays.items():
        expected = (n_nodes,) if name_ in {"u", "v", "damage"} else (n_cells, 4)
        if value.shape != expected or not np.isfinite(value).all():
            raise ValueError(f"invalid predecessor {name_} shape or values")
    if ((arrays["damage"] < 0).any() or (arrays["damage"] > 1).any()
            or (arrays["history"] < 0).any() or (arrays["active_driver"] < 0).any()):
        raise ValueError("predecessor outside physical bounds")
    expected_f = np.where(arrays["history"] > .5, (1. / (arrays["history"] + .5)) ** 2, 1.)
    if not np.allclose(expected_f, arrays["f_commit"], atol=1e-10, rtol=1e-10):
        raise ValueError("predecessor fatigue history/coefficient mismatch")
    return arrays, key, paths, admission
