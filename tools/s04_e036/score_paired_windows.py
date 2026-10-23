#!/usr/bin/env python3
"""Read-only scoring of saved P1/P2 windows against separately admitted F1.

This entry point never optimizes a network or solves FEM. It replays saved
fields, so its execution is separate from merely preparing this source file.
Targets are supplied only here, never to the training entry point. Results go
to stdout; source runs and target archives are not modified.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
import uuid

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT / "tools/s04_e011_analysis")]
from run_paired_windows import WindowProblem, objective_precision_record
from native_q4_diagnostics import native_readout, physical_gap
from cyclic_persistence import load_verified_step
from run_multicycle_cross_replay import q4_geometry
from window_inputs import CASES, bound_file, load_case, load_manifest, optimizer_work, predecessor_key, read_json, sha256, state_key
from window_inputs import execution_cases


_CALLBACK_FILES = {
    "source/trial_fatigue_coupling.py", "source/cyclic_persistence.py",
    "source/cyclic_acceptance.py", "source/compute_energy.py", "source/fatigue_history.py",
    "source/q4_quadrature.py", "source/network.py", "source/fit.py", "source/optim.py",
    "source/material_properties.py", "source/pff_model.py",
    "SENS_tensile/field_computation.py", "SENS_tensile/run_native_q4_one_step_matrix.py",
    "tools/s04_e036/run_paired_windows.py", "tools/s04_e036/window_inputs.py",
}
_FIELDS = ("u", "v", "d", "history", "active_driver", "f_solve", "f_commit",
           "old_damage", "old_history", "old_active_driver")
_TIGHTENING_SLOTS = {"c1/s2", "c1/s4", "c83/s2", "c83/s4"}


def tightening_map(value):
    """Keep the four prospectively declared sensitivities independent."""
    if not isinstance(value, dict) or set(value) != _TIGHTENING_SLOTS:
        raise ValueError("reference_tightening needs exactly four declared state slots; unavailable values must be null")
    for slot, spec in value.items():
        if spec is not None and (not isinstance(spec, dict) or spec.get("state_slot") != slot):
            raise ValueError("reference_tightening slot differs from its declared state")
    return value


def _strict_metadata(actual, expected, label):
    # Canonical JSON also distinguishes booleans from integers in physical keys.
    if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        raise ValueError(f"{label} differs from the declared comparison")


def _same_tensors(actual, expected, label):
    if set(actual) != set(expected):
        raise ValueError(f"{label} fields differ")
    for name, reference in expected.items():
        value = actual[name]
        if (type(value) is not torch.Tensor or value.dtype != reference.dtype
                or value.shape != reference.shape
                or not torch.equal(value.detach().cpu(), reference.detach().cpu())):
            raise ValueError(f"{label}.{name} is not reproduced exactly")


def _updates(value):
    if type(value) is not int or not 200 <= value <= 2000 or value % 200:
        raise ValueError("saved work must be a completed 200-update block, at most 2000")
    return value


def _verified_work(saved, update, expected_window_before):
    if expected_window_before is None:
        raise ValueError("no verified cumulative predecessor work")
    expected = optimizer_work(_updates(update), expected_window_before)
    _strict_metadata(saved, expected, "optimizer work")
    return expected


def work_comparison(first, second):
    """Equal current-step work need not mean equal cumulative window work."""
    current_equal = first["current_step_updates"] == second["current_step_updates"]
    window_equal = first["window_updates"] == second["window_updates"]
    return dict(current_step_equal_work=current_equal, cumulative_window_equal_work=window_equal,
                P1_optimizer_work=first, P2_optimizer_work=second)


def target_readout(problem, target):
    old = {name: target[source] for name, source in
           (("damage", "old_damage"), ("history", "old_history"), ("active_driver", "old_active_driver"))}
    return native_readout(problem, target, old, target["f_solve"], target["history"], target["f_commit"])


def tightening_readout(spec, root, key, problem, target, mass, readout):
    """One separately admitted sensitivity, with exactly the same old state."""
    slot = f"c{key['cycle']}/s{key['substep']}"
    if slot not in _TIGHTENING_SLOTS:
        raise ValueError("tightening is restricted to the four predeclared states")
    if spec is None:
        return dict(status="unavailable", state_slot=slot,
                    scope="this state only; no general reference-error floor")
    if not isinstance(spec, dict) or set(spec) != {"state_slot", "target", "standard_policy", "tightened_policy"}:
        raise ValueError("tightening needs a target and its predeclared state and policies")
    if spec["state_slot"] != slot:
        raise ValueError("tightening cannot be applied to another state")
    # Numeric policies are preserved with the two native receipts. The native
    # target's policy, source and predecessor bindings are independently checked.
    before, after = spec["standard_policy"], spec["tightened_policy"]
    if (before != {"u_tol": 1e-6, "joint_tol": 4e-4}
            or after != {"u_tol": 1e-8, "joint_tol": 4e-6}):
        raise ValueError("tightening needs the exact predeclared native acceptance tolerances")
    old = {name: target[source] for name, source in
           (("damage", "old_damage"), ("history", "old_history"), ("active_driver", "old_active_driver"))}
    tightened, receipt = load_target(spec["target"], root, key, problem,
                                    expected_predecessor_sha256=target["predecessor_source_sha256"], expected_old=old)
    if target["native_solver_policy"] != before or receipt["native_solver_policy"] != after:
        raise ValueError("native run receipts do not bind the stated standard/tightened solver policies")
    metrics = receipt["physical_replay"]["metrics"]
    if (metrics["u_residual_l2"] > after["u_tol"]
            or metrics["u_residual_l2"] + metrics["phase_box_kkt_l2"] > after["joint_tol"]):
        raise ValueError("tight target fails its explicitly stricter fresh residual thresholds")
    return dict(status="verified_same_predecessor_sensitivity", state_key=key,
                standard_policy=before, tightened_policy=after, admission=receipt,
                primitive=primitive_gap(tightened, target, mass),
                physical=physical_gap(problem, target_readout(problem, tightened), readout),
                scope="this state only; sensitivity to this tolerance change, not an error bound or a shared floor")


def primitive_gap(fields, target, mass):
    components = {}
    for name, scale in (("u", .12), ("v", .12), ("d", 1.)):
        value = fields[name].detach().cpu().numpy().astype(np.float64)
        expected = target[name].detach().cpu().numpy().astype(np.float64)
        if value.shape != mass.shape or expected.shape != mass.shape or not np.isfinite(value).all():
            raise ValueError("primitive field has invalid nodal support or values")
        components[name] = float(np.sum(mass * ((value - expected) / scale) ** 2) / mass.sum())
    return dict(J=float(np.sqrt(sum(components.values()) / 3.)),
                normalized_rms={name: float(np.sqrt(value)) for name, value in components.items()},
                J_squared_contributions={name: value / 3. for name, value in components.items()})


def _improvement(first, second):
    return None if first == 0. else 1. - second / first


def load_target(spec, root, key, problem, *, expected_predecessor_sha256, expected_old):
    """Check source identity and reassemble one saved native F1 transition."""
    if expected_predecessor_sha256 is None or expected_old is None:
        raise ValueError("F1 predecessor chain is unavailable or rejected; later targets cannot skip it")
    if spec is None:
        raise ValueError("F1 target is unavailable; no substitution")
    if set(spec) != {"snapshot", "admission"}:
        raise ValueError("each F1 target needs snapshot and admission only")
    snapshot = bound_file(spec["snapshot"], root)
    admission_path = bound_file(spec["admission"], root)
    admission = read_json(admission_path)
    if admission.get("schema") != "s04_e036_target_admission_v1":
        raise ValueError("wrong F1 admission schema")
    policy = admission.get("solver_policy")
    allowed = ({"u_tol": 1e-6, "joint_tol": 4e-4}, {"u_tol": 1e-8, "joint_tol": 4e-6})
    if (not isinstance(policy, dict) or policy not in allowed
            or any(type(value) not in (int, float) for value in policy.values())):
        raise ValueError("F1 requires explicit predeclared standard or strict solver_policy")
    for name in ("accepted", "native_residual_checked", "checkpoint_readback_verified"):
        if admission.get(name) is not True:
            raise ValueError(f"F1 lacks explicit {name}")
    for name in ("source_checkpoint", "predecessor_checkpoint", "native_residual_evidence", "checkpoint_readback_evidence"):
        bound_file(admission[name], admission_path.parent)
    if admission["predecessor_checkpoint"]["sha256"] != expected_predecessor_sha256:
        raise ValueError("F1 predecessor checkpoint differs from its actual accepted source chain")
    old_key = predecessor_key(key["trajectory"], key["cycle"], key["substep"])
    _strict_metadata(admission["state_key"], key, "F1 admission state")
    _strict_metadata(admission["predecessor_key"], old_key, "F1 admission predecessor")
    if (admission.get("snapshot_sha256") != spec["snapshot"]["sha256"]
            or admission.get("ordered_mesh_sha256_f32_i64") != problem.common["ordered_mesh_sha256_f32_i64"]):
        raise ValueError("F1 admission does not bind this snapshot and mesh")
    with np.load(snapshot, allow_pickle=False) as data:
        arrays = {name: np.asarray(data[name]).copy() for name in _FIELDS}
        _strict_metadata(json.loads(str(data["state_key_json"].item())), key, "F1 saved state")
        _strict_metadata(json.loads(str(data["predecessor_key_json"].item())), old_key, "F1 saved predecessor")
        if str(data["ordered_mesh_sha256_f32_i64"].item()) != problem.common["ordered_mesh_sha256_f32_i64"]:
            raise ValueError("F1 saved mesh differs")
        for name in ("source_checkpoint", "predecessor_checkpoint"):
            if str(data[f"{name}_sha256"].item()) != admission[name]["sha256"]:
                raise ValueError(f"F1 {name} identity differs")
    tensors = {}
    for name, values in arrays.items():
        shape = (len(problem.x),) if name in {"u", "v", "d", "old_damage"} else (len(problem.cells), 4)
        if values.dtype.kind != "f" or values.dtype.itemsize != 8 or values.shape != shape or not np.isfinite(values).all():
            raise ValueError(f"invalid F1 {name}")
        tensors[name] = torch.as_tensor(values, dtype=torch.float64, device=problem.device)
    _same_tensors(dict(damage=tensors["old_damage"], history=tensors["old_history"],
                       active_driver=tensors["old_active_driver"]), expected_old,
                  "F1 native float64 predecessor")
    if (bool(torch.any(tensors["old_damage"] < 0)) or bool(torch.any(tensors["old_damage"] > 1))
            or bool(torch.any(tensors["old_history"] < 0)) or bool(torch.any(tensors["old_active_driver"] < 0))):
        raise ValueError("F1 predecessor is outside physical bounds")
    context = dict(tensors, trial_history=tensors["history"],
                   displacement=torch.tensor([key["displacement"]], dtype=torch.float64, device=problem.device),
                   state_token=uuid.uuid4().hex)
    receipt = problem.residual(None, history_atol=1e-10, history_rtol=0.)(context)
    scale = 1e-10  # Exact FEM policy: absolute history/coefficient identity.
    if receipt.get("accepted") is not True or not bool(torch.all(abs(tensors["f_solve"] - tensors["f_commit"]) <= scale)):
        raise ValueError("F1 failed fresh physical/coefficient replay")
    return tensors, dict(accepted=True, physical_replay=receipt,
                         snapshot_sha256=spec["snapshot"]["sha256"],
                         coefficient_atol=1e-10, coefficient_rtol=0.,
                         history_atol=1e-10, history_rtol=0.,
                         native_solver_policy=policy,
                         predecessor_checkpoint_sha256=admission["predecessor_checkpoint"]["sha256"],
                         source_checkpoint_sha256=admission["source_checkpoint"]["sha256"])


def _diagnostic_snapshots(step, key, arm, problem, expected_old, expected_window_before, reference_readout):
    """Only verified network readouts; these remain unaccepted diagnostics."""
    result, errors, duplicate_updates = {}, [], set()
    if not (step / "snapshot_index.json").is_file():
        return result, errors
    if expected_old is None:
        return result, [dict(status="unverified", reason="no verified predecessor for diagnostic snapshots")]
    for entry in read_json(step / "snapshot_index.json"):
        if entry.get("event") != "outer":
            continue
        try:
            update = _updates(entry["updates"])
            if update in result or update in duplicate_updates:
                result.pop(update, None)
                duplicate_updates.add(update)
                raise ValueError("duplicate outer snapshot at one update count")
            path = (step / "snapshots" / entry["file"]).resolve()
            if not path.is_relative_to((step / "snapshots").resolve()) or path.is_symlink():
                raise ValueError("snapshot escaped its own step")
            payload = torch.load(path, map_location="cpu", weights_only=True)
            _strict_metadata(payload["state_key"], key, "snapshot state")
            _strict_metadata(payload["common_problem"], problem.common, "snapshot mapping")
            if payload["arm"] != arm or _updates(payload["updates"]) != update or payload["event"]["event"] != "outer":
                raise ValueError("snapshot label mismatch")
            work = _verified_work(payload["optimizer_work"], update, expected_window_before)
            _strict_metadata(entry["optimizer_work"], work, "snapshot index work")
            saved = payload["event"]["context"]
            _same_tensors(dict(damage=saved["old_damage"], history=saved["old_history"],
                               active_driver=saved["old_active_driver"]), expected_old, "snapshot predecessor")
            field = problem.field(payload["network_state"], key["displacement"])
            fresh = problem.state(field)
            _same_tensors({name: saved[name] for name in fresh}, fresh, "snapshot network readout")
            context = {name: (value.to(problem.device) if torch.is_tensor(value) else value)
                       for name, value in saved.items()}
            context.update(fresh)
            fresh_acceptance = problem.residual(field)(context)
            if (fresh_acceptance.get("fresh_current_state") is not True
                    or fresh_acceptance.get("state_token") != context["state_token"]
                    or fresh_acceptance["metrics"].get("fresh_history_consistent") is not True):
                raise ValueError("diagnostic snapshot history is not reproduced by its final field")
            old = dict(damage=context["old_damage"], history=context["old_history"],
                       active_driver=context["old_active_driver"])
            _strict_metadata(payload["objective_precision"], objective_precision_record(old, context["f_solve"]),
                             "snapshot objective precision")
            physical = native_readout(problem, fresh, old, context["f_solve"],
                                      context["trial_history"], context["f_commit"])
            result[update] = dict(fields=fresh, optimizer_work=work,
                objective_precision=payload["objective_precision"],
                physical=physical_gap(problem, physical, reference_readout),
                saved_controller_record=payload["event"]["record"], fresh_acceptance=fresh_acceptance,
                accepted_comparison=False,
                interpretation="replayed diagnostic snapshot; numerical acceptance here does not create a committed endpoint")
        except Exception as error:
            errors.append(dict(file=entry.get("file"), reason=str(error), status="unverified"))
    return result, errors


def verify_scoring_control_split(producer_source):
    """Permit dispatch edits only; protect every original metric/replay helper and case body."""
    old = ast.parse(Path(producer_source).read_text())
    current = ast.parse(Path(__file__).read_text())
    protected = ("tightening_map", "_strict_metadata", "_same_tensors", "_updates", "_verified_work",
                 "work_comparison", "target_readout", "tightening_readout", "primitive_gap",
                 "_improvement", "load_target", "_diagnostic_snapshots")
    def functions(tree):
        return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    before, after = functions(old), functions(current)
    digest = lambda node: hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
    identities = {}
    for name in protected:
        if name not in before or name not in after or digest(before[name]) != digest(after[name]):
            raise ValueError(f"producer/current protected scoring implementation differs: {name}")
        identities[name] = digest(after[name])
    def case_body(mapping):
        function = mapping.get("score_bound_run", mapping["score"])
        loop = next(node for node in function.body if isinstance(node, ast.For)
                    and isinstance(node.target, ast.Tuple) and isinstance(node.target.elts[0], ast.Name)
                    and node.target.elts[0].id == "case")
        return ast.Module(body=loop.body, type_ignores=[])
    if digest(case_body(before)) != digest(case_body(after)):
        raise ValueError("producer/current per-case scoring body differs")
    for name in ("_CALLBACK_FILES", "_FIELDS", "_TIGHTENING_SLOTS"):
        def assignment(tree):
            return next(node for node in tree.body if isinstance(node, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets))
        if digest(assignment(old)) != digest(assignment(current)):
            raise ValueError(f"protected scoring constant differs: {name}")
    old_imports = {ast.dump(node, include_attributes=False) for node in old.body
                   if isinstance(node, (ast.Import, ast.ImportFrom))}
    new_imports = {ast.dump(node, include_attributes=False) for node in current.body
                   if isinstance(node, (ast.Import, ast.ImportFrom))}
    if not old_imports <= new_imports:
        raise ValueError("an original scoring import changed")
    return dict(producer_source_sha256=sha256(producer_source), current_source_sha256=sha256(Path(__file__)),
                protected_function_ast_sha256=identities, case_body_ast_sha256=digest(case_body(after)),
                scope="postprocessing dispatch separation only; protected scientific scoring unchanged")


def score_bound_run(run_root, scoring, root, device, *, target_manifest_sha256,
                    requested_case=None, configure_runtime=True, producer_scorer=None):
    """Score actual bound artifacts, optionally for one receipt's execution partition."""
    run_root, root = Path(run_root).resolve(), Path(root).resolve()
    if scoring.get("schema") != "s04_e036_scoring_v1":
        raise ValueError("wrong scoring manifest")
    training_path = bound_file(scoring["training_manifest"], root)
    receipt_path = bound_file(scoring["run_receipt"], root)
    if receipt_path != run_root / "run_receipt.json":
        raise ValueError("run receipt is not from the requested run")
    receipt = read_json(receipt_path)
    if receipt.get("schema") != "s04_e036_paired_run_v1" or receipt.get("manifest_sha256") != scoring["training_manifest"]["sha256"]:
        raise ValueError("run and training manifest differ")
    if receipt["authority"].get("approved") is not True:
        raise ValueError("run does not record an approved execution envelope")
    lock_path = bound_file(scoring["callback_lock"], root)
    if scoring["callback_lock"]["sha256"] != receipt["authority"]["implementation_lock"]["sha256"]:
        raise ValueError("scoring callback lock differs from the producer lock")
    lock = read_json(lock_path)
    if lock.get("schema") != "s04_e036_implementation_lock_v1" or not _CALLBACK_FILES <= set(lock["files"]):
        raise ValueError("incomplete physical replay implementation lock")
    control_split = None
    if producer_scorer is not None:
        original = bound_file(producer_scorer, root)
        if sha256(original) != lock["files"].get("tools/s04_e036/score_paired_windows.py"):
            raise ValueError("producer scorer source differs from its actual implementation lock")
        control_split = verify_scoring_control_split(original)
    for relative, digest in lock["files"].items():
        if relative == "tools/s04_e036/score_paired_windows.py" and control_split is not None:
            continue
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT) or sha256(source) != digest:
            raise ValueError(f"physical replay implementation drift: {relative}")
    if scoring.get("scorer_sha256") != sha256(Path(__file__)):
        raise ValueError("scorer version differs from the scoring manifest")
    if scoring.get("diagnostics_sha256") != sha256(Path(__file__).with_name("native_q4_diagnostics.py")):
        raise ValueError("native physical diagnostics differ from the scoring manifest")
    if scoring.get("q4_geometry_sha256") != sha256(ROOT / "tools/s04_e011_analysis/run_multicycle_cross_replay.py"):
        raise ValueError("Q4 lumped mass implementation differs")
    selected = execution_cases(requested_case)
    if requested_case is not None:
        _strict_metadata(receipt.get("requested_case"), requested_case, "run execution partition")
        _strict_metadata(receipt["authority"].get("requested_case"), requested_case, "authorized partition")
        _strict_metadata(receipt.get("execution_cases"), list(selected), "executed cases")
        _strict_metadata(receipt.get("declared_cases"), list(CASES), "declared cases")
    doc, training_root, nodes, cells, common = load_manifest(training_path, requested_case=requested_case)
    # Endpoint case names already contain s4; use one unambiguous label.
    label = lambda case, substep: f"{case}/s{substep}"
    expected_targets = {label(case, substep) for case, (_, steps) in CASES.items() for substep in steps}
    if set(scoring["targets"]) != expected_targets:
        raise ValueError("scoring requires the exact twelve declared target slots; unavailable slots may be null")
    sensitivity_specs = tightening_map(scoring.get("reference_tightening"))
    if configure_runtime:
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
    problem = WindowProblem(nodes, cells, common, torch.device(device))
    shape, _, weights, _ = q4_geometry(nodes.astype(np.float64), cells)
    mass = np.zeros(len(nodes), dtype=np.float64)
    np.add.at(mass, cells.reshape(-1), np.einsum("eg,gn->en", weights, shape).reshape(-1))
    if not np.isfinite(mass).all() or np.any(mass <= 0):
        raise ValueError("invalid native Q4 lumped nodal area")
    rows, eligible = [], []
    for case, (cycle, steps) in ((name, CASES[name]) for name in selected):
        accepted_parent = {"P1": None, "P2": None}
        accepted_window_work = {"P1": 0, "P2": 0}
        try:
            arrays, pre_key, _, input_admission = load_case(case, doc, training_root, len(nodes), len(cells), common)
            # Preserve the original native common predecessor in both chains;
            # subsequent FEM and PIDL transitions have separate lineages.
            f1_parent = {name: torch.as_tensor(arrays[name], dtype=torch.float64,
                                              device=problem.device).clone()
                         for name in ("damage", "history", "active_driver")}
            f1_parent_sha = input_admission["source_checkpoint"]["sha256"]
            initial_old = problem.old_state(arrays, pre_key)
            input_error = None
        except Exception as error:
            initial_old, input_error = None, str(error)
            f1_parent, f1_parent_sha = None, None
        for substep in steps:
            key, slot = state_key(doc["trajectory"], cycle, substep), label(case, substep)
            row = dict(state_key=key, case=case, status="unverified", accepted_endpoints={},
                       fixed_work_diagnostics=[], unverified_snapshots={})
            rows.append(row)
            try:
                if input_error:
                    raise ValueError(f"common predecessor is unavailable: {input_error}")
                target, target_receipt = load_target(
                    scoring["targets"][slot], root, key, problem,
                    expected_predecessor_sha256=f1_parent_sha, expected_old=f1_parent)
                _strict_metadata(target_receipt["native_solver_policy"], {"u_tol": 1e-6, "joint_tol": 4e-4},
                                 "primary F1 solver policy")
                row["F1"] = target_receipt
                reference_readout = target_readout(problem, target)
                row["F1"]["physical_readout"] = reference_readout["summary"]
                if slot in _TIGHTENING_SLOTS:
                    # Keep this provenance outside tensor fields used by the
                    # general native state/old-state checks.
                    tightening_target = dict(target, predecessor_source_sha256=f1_parent_sha,
                                             native_solver_policy=target_receipt["native_solver_policy"])
                    try:
                        row["reference_sensitivity"] = tightening_readout(
                            sensitivity_specs[slot], root, key, problem,
                            tightening_target, mass, reference_readout)
                    except Exception as error:
                        row["reference_sensitivity"] = dict(status="unverified", reason=str(error),
                            scope="this state only; no general reference-error floor")
                else:
                    row["reference_sensitivity"] = None
                f1_parent = dict(damage=target["d"].clone(), history=target["history"].clone(),
                                 active_driver=target["active_driver"].clone())
                f1_parent_sha = target_receipt["source_checkpoint_sha256"]
            except Exception as error:
                row["reason"] = str(error)
                target = None
                # A missing/rejected native transition ends only the F1 chain.
                # PIDL persistence and its own predecessor chains below still
                # get checked independently, without manufacturing F1 scores.
                f1_parent, f1_parent_sha = None, None
            snapshots = {}
            for arm in ("P1", "P2"):
                step = run_root / case / arm / f"s{substep}"
                expected_old = initial_old if substep == steps[0] else accepted_parent[arm]
                expected_window_before = accepted_window_work[arm]
                try:
                    loaded = load_verified_step(step / "committed", problem.replay)
                    _strict_metadata(loaded["state_key"], key, "PIDL state")
                    if (loaded["metadata"]["arm"] != arm
                            or loaded["metadata"]["coefficient_mode"] != ("frozen_old" if arm == "P1" else "trial")
                            or loaded["provenance"]["case"] != case
                            or loaded["provenance"]["manifest_sha256"] != scoring["training_manifest"]["sha256"]):
                        raise ValueError("PIDL arm or provenance mismatch")
                    if expected_old is None:
                        raise ValueError("no verified predecessor; rejected windows cannot continue")
                    _same_tensors(loaded["old_state"], expected_old, "PIDL predecessor")
                    update = _updates(loaded["metadata"]["rprop_updates"])
                    work = _verified_work(loaded["metadata"]["optimizer_work"], update, expected_window_before)
                    precision = objective_precision_record(loaded["old_state"], loaded["f_solve"])
                    _strict_metadata(loaded["metadata"]["objective_precision"], precision, "endpoint objective precision")
                    if target is not None:
                        row["accepted_endpoints"][arm] = dict(primitive_gap(loaded["fields"], target, mass),
                                                             updates=update, optimizer_work=work, objective_precision=precision)
                        endpoint_readout = native_readout(problem, loaded["fields"], loaded["old_state"],
                                                          loaded["f_solve"], loaded["history"], loaded["f_commit"])
                        row["accepted_endpoints"][arm]["physical"] = physical_gap(problem, endpoint_readout, reference_readout)
                    else:
                        row.setdefault("verified_unscored_endpoints", {})[arm] = dict(updates=update, optimizer_work=work,
                                                                                    objective_precision=precision)
                    accepted_parent[arm] = dict(damage=loaded["fields"]["d"].to(dtype=torch.float64),
                                                history=loaded["history"].to(dtype=torch.float64),
                                                active_driver=loaded["fields"]["active_driver"].to(dtype=torch.float64))
                    accepted_window_work[arm] = work["window_updates"]
                except Exception as error:
                    row.setdefault("endpoint_errors", {})[arm] = str(error)
                    accepted_parent[arm] = None
                    accepted_window_work[arm] = None
                snapshots[arm], errors = (_diagnostic_snapshots(step, key, arm, problem, expected_old,
                                                                expected_window_before, reference_readout)
                                          if target is not None else ({}, []))
                row["unverified_snapshots"][arm] = errors
                row.setdefault("replayed_snapshot_diagnostics", {})[arm] = [
                    dict(updates=update, primitive=primitive_gap(value["fields"], target, mass),
                         **{name: value[name] for name in ("optimizer_work", "objective_precision", "physical", "saved_controller_record",
                                                          "fresh_acceptance", "accepted_comparison", "interpretation")})
                    for update, value in sorted(snapshots[arm].items())]
            for update in sorted(set(snapshots["P1"]) & set(snapshots["P2"])):
                first = primitive_gap(snapshots["P1"][update]["fields"], target, mass)
                second = primitive_gap(snapshots["P2"][update]["fields"], target, mass)
                comparison = work_comparison(snapshots["P1"][update]["optimizer_work"],
                                             snapshots["P2"][update]["optimizer_work"])
                row["fixed_work_diagnostics"].append(dict(updates=update, P1=first, P2=second,
                    P1_physical=snapshots["P1"][update]["physical"],
                    P2_physical=snapshots["P2"][update]["physical"],
                    P1_fresh_acceptance=snapshots["P1"][update]["fresh_acceptance"],
                    P2_fresh_acceptance=snapshots["P2"][update]["fresh_acceptance"],
                    **comparison,
                    improvement=_improvement(first["J"], second["J"]), accepted_comparison=False,
                    interpretation="current_step_equal_work diagnostic; cumulative window work is reported separately; never an accepted improvement"))
            if set(row["accepted_endpoints"]) == {"P1", "P2"}:
                first, second = (row["accepted_endpoints"][arm] for arm in ("P1", "P2"))
                row.update(status="both_endpoints_verified", endpoint_improvement=_improvement(first["J"], second["J"]),
                           endpoint_updates_equal=first["updates"] == second["updates"],
                           endpoint_work_comparison=work_comparison(first["optimizer_work"], second["optimizer_work"]),
                           endpoint_interpretation="accepted endpoints; actual work may differ")
                eligible.append((first["J"], second["J"]))
    aggregate = None
    if len(eligible) == len(expected_targets):
        first, second = np.mean(np.asarray(eligible), axis=0)
        aggregate = dict(mean_J_P1=float(first), mean_J_P2=float(second),
                         improvement=_improvement(float(first), float(second)),
                         weighting="equal weight for all twelve declared states",
                         interpretation="accepted endpoints; not an equal-work estimate")
    return dict(schema="s04_e036_scoring_result_v1", training_manifest_sha256=scoring["training_manifest"]["sha256"],
                target_manifest_sha256=target_manifest_sha256, replay_device=str(device),
                requested_case=requested_case, execution_cases=list(selected), scoring_control_split=control_split,
                callback_lock_sha256=scoring["callback_lock"]["sha256"],
                scorer_sha256=scoring["scorer_sha256"], q4_geometry_sha256=scoring["q4_geometry_sha256"],
                formula="sqrt(sum(m*((du/.12)^2+(dv/.12)^2+dd^2))/(3*sum(m)))",
                physical_metrics_implementation_sha256=sha256(Path(__file__).with_name("native_q4_diagnostics.py")),
                states=rows, verified_endpoint_pairs=len(eligible), declared_states=len(expected_targets),
                fixed_design_aggregate=aggregate,
                aggregate_boundary="No fixed-design aggregate when any declared endpoint pair is unavailable or unverified.",
                claim_boundary="Conditional windows; coupling plus history propagation, not isolated timing causality or fatigue life.")


def score(run_root, target_manifest, device):
    target_manifest = Path(target_manifest).resolve()
    return score_bound_run(run_root, read_json(target_manifest), target_manifest.parent, device,
                           target_manifest_sha256=sha256(target_manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--target-manifest", type=Path, required=True)
    parser.add_argument("--device", required=True,
                        help="Explicit original producer device; exact replay differences remain unverified")
    args = parser.parse_args()
    print(json.dumps(score(args.run_root, args.target_manifest, args.device), indent=2, allow_nan=False))
