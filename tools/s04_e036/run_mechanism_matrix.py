#!/usr/bin/env python3
"""Four-state mechanism matrix and separately authorized seen-target witness.

This entry is never imported to start work. The CLI rejects Mac/CPU execution.
All states are independent conditional endpoints: history_commit_count stays 0.
The matrix manifest cannot contain future target fields. See MECHANISM_RUNNER.md.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from run_paired_windows import WindowProblem, Deadline, TimeBudgetExceeded, check_authority
from window_inputs import bound_file, read_json, sha256, state_key, predecessor_key, native_mesh_coordinates
from stage_a_reuse import validate_stage_a_reuse
from cyclic_acceptance import install_sent_common_problem, nodal_box_residual
from compute_energy import compute_energy, get_psi_plus_per_elem
from fatigue_history import compute_fatigue_degrad, update_fatigue_history
from fit import EarlyStopping
from optim import get_optimizer
from q4_quadrature import q4_shape_data, q4_gradient
from mechanism_metrics import (gradient_balance, parameter_geometry, direct_box_projection,
                               projection_receipt, clipped_descent_receipt)
from native_q4_diagnostics import native_readout

CASES = {"c1s2": (1, 2), "c1s4": (1, 4), "c83s2": (83, 2), "c83s4": (83, 4)}
NETWORK_SHA = {
    "c1s2": "5d8d0b3ae3480398dd86d1672af17521b77645b98beac18c78a7f0055b5ddc5f",
    "c1s4": "1f9b8896e2603b02d045d9b20ca42f0bf47ec30b69f3f8c30858f4064ea7db38",
    "c83s2": "aa9811352bb0134d7e7dbac8640c115784290bee9378a67aae0413a463a7da9f",
    "c83s4": "ae9767d8a2cfcde30598127d293997a55a4e575eacf9bb05f431d4e7a093e01c",
}
ARMS = {"Lplus": ("legacy", 1e-5), "L0": ("legacy", 0.),
        "Cplus": ("nodal_clamp", 1e-5), "C0": ("nodal_clamp", 0.)}
SOLVER = dict(first_updates=2000, block_updates=200, matrix_dtype="float32",
              physical_operator_dtype="float64", old_state_dtype="float64",
              fit_dtype="float64", fit_q_stop=1e-3, fit_max_damage_stop=.01,
              rprop_stagnation_blocks=10, rprop_min_relative_score_improvement=.01,
              lbfgs_history_size=100, lbfgs_closures_per_step=25, lbfgs_fixed_f_steps=200,
              lbfgs_stagnation_steps=20, physics_relative_energy_change=1e-10,
              fit_relative_loss_change=1e-8, cumulative_resource_limit=None)
EXTRA_LOCK_FILES = {"tools/s04_e036/run_mechanism_matrix.py",
                    "tools/s04_e036/mechanism_metrics.py", "tools/s04_e036/native_q4_diagnostics.py",
                    "tools/s04_e036/score_paired_windows.py", "source/tri3_quadrature.py"}


def exact_metadata(first, second, label):
    if json.dumps(first, sort_keys=True, allow_nan=False) != json.dumps(second, sort_keys=True, allow_nan=False):
        raise ValueError(label + " differs")


def cpu(value):
    if torch.is_tensor(value):
        result = value.detach().cpu().clone()
        if result.is_floating_point() and not bool(torch.isfinite(result).all()):
            raise ValueError("nonfinite saved tensor")
        return result
    if isinstance(value, dict):
        return {str(k): cpu(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [cpu(v) for v in value]
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise TypeError("unsupported or nonfinite saved value: " + str(type(value)))


def exact_payload(first, second):
    if type(first) is not type(second):
        raise ValueError("readback type differs")
    if torch.is_tensor(first):
        if first.dtype != second.dtype or first.shape != second.shape or not torch.equal(first, second):
            raise ValueError("readback tensor differs")
    elif isinstance(first, dict):
        if first.keys() != second.keys():
            raise ValueError("readback keys differ")
        for name in first:
            exact_payload(first[name], second[name])
    elif isinstance(first, list):
        if len(first) != len(second):
            raise ValueError("readback length differs")
        for a, b in zip(first, second):
            exact_payload(a, b)
    elif first != second:
        raise ValueError("readback scalar differs")


def atomic_file(directory, name, writer):
    path = directory / name
    if path.exists():
        raise FileExistsError(path)
    temporary = directory / ("." + name + "." + uuid.uuid4().hex + ".partial")
    with temporary.open("xb") as stream:
        writer(stream)
        stream.flush()
        os.fsync(stream.fileno())
    # Every output directory has one owner and is created exclusively.
    if path.exists():
        raise FileExistsError(path)
    os.replace(temporary, path)
    return path


def new_json(path, value):
    data = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    return atomic_file(path.parent, path.name, lambda stream: stream.write(data))


def append_event(path, value):
    with path.open("a") as stream:
        stream.write(json.dumps(value, allow_nan=False) + "\n")
        stream.flush()


def validate_manifest(doc):
    if set(doc) != {"schema", "trajectory", "mesh", "common_problem", "cases", "solver", "job_wall_seconds"}:
        raise ValueError("physics manifest admits predecessors only; no future target or arbitrary option")
    if doc["schema"] != "s04_e036_mechanism_inputs_v1" or set(doc["cases"]) != set(CASES):
        raise ValueError("exact four predetermined mechanism states required")
    exact_metadata(doc["solver"], SOLVER, "prospective numerical program")
    wall = doc["job_wall_seconds"]
    if type(wall) not in (int, float) or not math.isfinite(wall) or wall <= 0:
        raise ValueError("finite positive per-job anti-hang setting required")
    for name, (cycle, substep) in CASES.items():
        spec = doc["cases"][name]
        if set(spec) != {"state_key", "predecessor", "admission", "network"}:
            raise ValueError("each physical case contains only qualified predecessor and fixed theta0")
        exact_metadata(spec["state_key"], state_key(doc["trajectory"], cycle, substep), "physical state")
        if spec["network"]["sha256"] != NETWORK_SHA[name]:
            raise ValueError("canonical predecessor network changed; no replacement selection")


def load_problem(path, device):
    path = Path(path).resolve()
    doc = read_json(path)
    validate_manifest(doc)
    root = path.parent
    common = read_json(bound_file(doc["common_problem"], root))
    with np.load(bound_file(doc["mesh"], root), allow_pickle=False) as data:
        nodes = native_mesh_coordinates(data)
        original = np.asarray(data["connectivity"])
        cells = original.astype("<i8")
    if (nodes.shape != (86756, 2) or cells.shape != (86408, 4)
            or not np.array_equal(original, cells) or cells.min() < 0 or cells.max() >= len(nodes)):
        raise ValueError("requires the declared original ordered native Q4 mesh")
    problem = WindowProblem(nodes, cells, common, device)
    # This installs no network. The semantic validation below binds all effective
    # material, quadrature, masks, penalties and acceptance values to Stage A.
    return doc, root, problem


def load_predecessor(spec, root, problem):
    paths = {name: bound_file(spec[name], root) for name in ("predecessor", "admission", "network")}
    key = spec["state_key"]
    oldkey = predecessor_key(key["trajectory"], key["cycle"], key["substep"])
    admission = read_json(paths["admission"])
    expected = dict(schema="s04_e036_predecessor_admission_v1", accepted=True,
                    predecessor_sha256=spec["predecessor"]["sha256"], state_key=oldkey,
                    ordered_mesh_sha256_f32_i64=problem.common["ordered_mesh_sha256_f32_i64"],
                    native_residual_checked=True, checkpoint_readback_verified=True)
    for name, value in expected.items():
        exact_metadata(admission.get(name), value, "F1 predecessor admission " + name)
    for name in ("source_checkpoint", "native_residual_evidence", "checkpoint_readback_evidence"):
        bound_file(admission[name], paths["admission"].parent)
    with np.load(paths["predecessor"], allow_pickle=False) as data:
        arrays = {name: np.asarray(data[name]).copy() for name in
                  ("u", "v", "damage", "history", "active_driver", "f_commit")}
        exact_metadata(json.loads(str(data["state_key_json"].item())), oldkey, "stored predecessor")
        if (str(data["ordered_mesh_sha256_f32_i64"].item()) != expected["ordered_mesh_sha256_f32_i64"]
                or str(data["source_checkpoint_sha256"].item()) != admission["source_checkpoint"]["sha256"]):
            raise ValueError("predecessor source/geometry mismatch")
    for name, value in arrays.items():
        shape = (len(problem.x),) if name in ("u", "v", "damage") else (len(problem.cells), 4)
        if value.shape != shape or value.dtype.kind != "f" or value.dtype.itemsize < 8 or not np.isfinite(value).all():
            raise ValueError("native predecessor must retain finite float64 " + name)
    if ((arrays["damage"] < 0).any() or (arrays["damage"] > 1).any()
            or (arrays["history"] < 0).any() or (arrays["active_driver"] < 0).any()):
        raise ValueError("infeasible old state")
    native = {name: torch.as_tensor(arrays[name], device=problem.device, dtype=torch.float64).clone()
              for name in ("damage", "history", "active_driver")}
    expected_f = compute_fatigue_degrad(native["history"], problem.fatigue)
    if not torch.allclose(expected_f, torch.as_tensor(arrays["f_commit"], device=problem.device), atol=1e-10, rtol=0.):
        raise ValueError("native predecessor f/history mismatch")
    problem.old_state(arrays, oldkey)  # Saved-field/BC check only, no network forward.
    state = torch.load(paths["network"], map_location="cpu", weights_only=True)
    if (not isinstance(state, dict) or sum(value.numel() for value in state.values()) != 1125211
            or any(not torch.is_tensor(value) or value.dtype != torch.float32
                   or not bool(torch.isfinite(value).all()) for value in state.values())):
        raise ValueError("canonical complete 8x400 float32 theta0 required")
    return native, state, admission


class MechanismField:
    """Actual legacy network plus an explicitly named, immutable nodal map."""
    def __init__(self, problem, state, displacement, old, mapping, dtype):
        if mapping not in ("legacy", "nodal_clamp") or dtype not in (torch.float32, torch.float64):
            raise ValueError("unknown declared field mapping/precision")
        self.problem, self.mapping, self.dtype = problem, mapping, dtype
        self.x = problem.native_x.to(dtype=dtype)
        self.lower = old["damage"].detach().to(problem.native_x).clone()
        self.base = problem.field(state, displacement)
        self.net = self.base.net.to(dtype=dtype)
        # Reconstruct numeric constants at the declared precision, rather than
        # casting a rounded float32 pi/2 or load into a supposed f64 replay.
        self.base.domain_extrema = torch.tensor([[-.5, .5], [-.5, .5]], device=self.x.device, dtype=dtype)
        self.base.theta = torch.tensor([math.pi / 2], device=self.x.device, dtype=dtype)
        self.base.lmbda = torch.tensor([displacement], device=self.x.device, dtype=dtype)
        self.lmbda = self.base.lmbda
        install_sent_common_problem(inp=self.x, T_conn=problem.cells, field_comp=self.base,
                                    matprop=problem.mat, pffmodel=problem.model,
                                    irreversibility_penalty_cfg=problem.penalty,
                                    config=problem.common, fatigue_dict=problem.fatigue)
        # problem.field constructs an f32 model. Restore saved values after the
        # dtype conversion so an f64 witness is never silently rounded to f32.
        self.net.load_state_dict(state, strict=True)
        if any(not p.requires_grad for p in self.net.parameters()):
            raise ValueError("all network parameters must remain trainable")

    def values(self):
        u, v, raw = self.base.fieldCalculation(self.x)
        if not all(bool(torch.isfinite(value).all()) for value in (u, v, raw)):
            raise NumericalFailure("nonfinite network field")
        # All four arms share the same native double operator, fields and old
        # state. Only the actual NN evaluation/parameters begin in float32.
        # Promotion remains differentiable; no rounded lower is substituted.
        u, v, raw = (value.to(self.problem.native_x) for value in (u, v, raw))
        d = raw if self.mapping == "legacy" else direct_box_projection(raw, self.lower)
        return dict(u=u, v=v, d=d), raw


def fit_objective(fields, target, mass, weights, derivatives, cells, ell=.01):
    """Q²=J²+G², native nodal/Q4 metric; no coordinate-network derivative."""
    area = weights.sum()
    if not bool(torch.isfinite(area)) or float(area) <= 0 or mass.shape != fields["d"].shape:
        raise ValueError("invalid fit quadrature/mass support")
    channels, total_j, total_g = {}, 0., 0.
    for name, scale in (("u", .12), ("v", .12), ("d", 1.)):
        delta = (fields[name] - target[name].to(fields[name])) / scale
        grad = q4_gradient(delta, cells, derivatives)
        j = (mass * delta.square()).sum() / (3 * area)
        g = ell**2 * (weights * grad.square().sum(-1)).sum() / (3 * area)
        total_j, total_g = total_j + j, total_g + g
        channels[name] = dict(J_squared_contribution=float(j.detach()), G_squared_contribution=float(g.detach()))
    loss = total_j + total_g
    report = dict(Q=float(torch.sqrt(loss.detach())), J=float(torch.sqrt(total_j.detach())),
                  G=float(torch.sqrt(total_g.detach())), channels=channels,
                  max_damage_error=float((fields["d"] - target["d"].to(fields["d"])).abs().max().detach()),
                  max_u_error=float((fields["u"] - target["u"].to(fields["u"])).abs().max().detach()),
                  max_v_error=float((fields["v"] - target["v"].to(fields["v"])).abs().max().detach()))
    return loss, report


def fit_program_stop(report):
    return report["Q"] <= SOLVER["fit_q_stop"] and report["max_damage_error"] <= SOLVER["fit_max_damage_stop"]


def relative_change(before, after):
    if not math.isfinite(before) or not math.isfinite(after) or before <= 0:
        raise ValueError("positive finite baseline required for relative objective change")
    return abs(after - before) / before


def stalled(scores, count, relative_improvement):
    if len(scores) < count + 1:
        return False
    baseline = min(scores[:-count])
    return baseline > 0 and (baseline - min(scores[-count:])) / baseline < relative_improvement


class ClosureLimit(RuntimeError):
    pass


class NumericalFailure(ValueError):
    """A finite algorithm's scientific failure, never a persistence exception."""
    pass


def bounded_lbfgs_step(optimizer, parameters, closure, work, check_time, cap=25):
    """One accepted step or restore exact pre-step weights; count actual calls."""
    saved = [p.detach().clone() for p in parameters]
    calls = 0
    def guarded():
        nonlocal calls
        check_time()
        if calls >= cap:
            raise ClosureLimit("LBFGS per-step closure cap reached; restored previous parameters")
        calls += 1
        work["lbfgs_closures"] += 1
        return closure()
    try:
        optimizer.step(guarded)
        check_time()
        if any(not bool(torch.isfinite(p).all()) for p in parameters):
            raise ValueError("nonfinite LBFGS parameters")
    except BaseException:
        with torch.no_grad():
            for parameter, previous in zip(parameters, saved):
                parameter.copy_(previous)
        raise
    work["lbfgs_steps"] += 1
    return calls


class EndpointEngine:
    def __init__(self, problem, native_old, state, key, arm, dtype, deadline, provenance):
        self.problem, self.key, self.arm = problem, key, arm
        self.mapping, self.weight_l2 = ARMS[arm] if arm in ARMS else ("legacy", 0.)
        self.dtype, self.deadline, self.provenance = dtype, deadline, provenance
        self.native_old = {name: value.detach().to(device=problem.device, dtype=torch.float64).clone()
                           for name, value in native_old.items()}
        self.old = {name: value.clone() for name, value in self.native_old.items()}
        self.guard = cpu(self.old)
        self.field = MechanismField(problem, state, key["displacement"], self.old, self.mapping, dtype)
        self.work = dict(rprop_updates=0, lbfgs_steps=0, lbfgs_closures=0, coefficient_refreshes=0,
                         history_commits=0, snapshot_replays=0)
        self.coefficient = compute_fatigue_degrad(self.old["history"], problem.fatigue).detach().clone()
        self.events = set()

    def check(self):
        self.deadline.check()

    def verify_old(self):
        exact_payload(self.guard, cpu(self.old))
        if not torch.equal(self.field.lower, self.old["damage"]):
            raise ValueError("immutable mapping lower changed")

    def objective(self):
        fields, _ = self.field.values()
        energy = sum(compute_energy(self.problem.native_x, fields["u"], fields["v"], fields["d"], self.old["damage"],
                                    self.problem.mat, self.problem.model, self.problem.native_area, self.problem.cells,
                                    f_fatigue=self.coefficient.detach(), irreversibility_penalty_cfg=self.problem.penalty))
        if not bool(torch.isfinite(energy)) or float(energy.detach()) <= 0:
            raise NumericalFailure("physical log-energy is nonpositive/nonfinite")
        regularizer = sum(p.square().sum() for name, p in self.field.net.named_parameters() if "weight" in name)
        return torch.log10(energy), self.weight_l2 * regularizer, energy

    def readout(self):
        self.check()
        self.verify_old()
        p = self.problem
        with torch.no_grad():
            fields, raw = self.field.values()
            active = get_psi_plus_per_elem(p.native_x, fields["u"], fields["v"], fields["d"],
                p.mat, p.model, p.native_area, p.cells, history_driver_reduction_dict=p.fatigue["history_driver_reduction"])
            history = update_fatigue_history(self.old["history"], active, self.old["active_driver"], p.fatigue)
            commit = compute_fatigue_degrad(history, p.fatigue).detach()
        if self.arm == "legacy_witness":
            # Target fitting has no physical frozen coefficient. Its physical
            # diagnostic uses fresh trial-f at zero updates, explicitly labeled.
            self.coefficient = commit.detach().clone()
        state = dict(fields, active_driver=active,
                     displacement=torch.tensor([self.key["displacement"]], dtype=torch.float64, device=p.device))
        context = dict(state, old_damage=self.old["damage"], old_history=self.old["history"],
                       old_active_driver=self.old["active_driver"], trial_history=history,
                       f_solve=self.coefficient, f_commit=commit, state_token=uuid.uuid4().hex)
        receipt = p.residual(None)(context)
        delta = abs(self.coefficient - commit)
        fixed = bool(torch.all(delta <= 2e-6 + 2e-6 * torch.maximum(abs(self.coefficient), abs(commit))))
        self.check()
        return dict(fields=state, raw_damage=raw.detach(), history=history.detach(), f_solve=self.coefficient.clone(),
                    f_commit=commit, residual=receipt, coefficient_fixed_point=fixed,
                    physical_accepted=bool(receipt["accepted"] and fixed),
                    C=float(receipt["metrics"]["joint_score"]))

    def refresh(self, readout):
        self.coefficient = readout["f_commit"].detach().clone()
        self.work["coefficient_refreshes"] += 1

    def decomposition(self):
        self.check()
        try:
            physical, regularizer, energy = self.objective()
        except NumericalFailure:
            if self.arm != "legacy_witness":
                raise
            return dict(summary=dict(status="physical_log_objective_undefined_at_this_witness_field"))
        parameters = list(self.field.net.parameters())
        def vector(value, retain):
            grads = torch.autograd.grad(value, parameters, retain_graph=retain, allow_unused=True)
            return [torch.zeros_like(p) if g is None else g for p, g in zip(parameters, grads)]
        a, b, total = vector(physical, True), vector(regularizer, True), vector(physical + regularizer, False)
        summary = gradient_balance(a, b, total)
        summary.update(physical_log10_energy=float(physical.detach()), energy=float(energy.detach()),
                       weighted_parameter_regularizer=float(regularizer.detach()),
                       parameter_geometry=parameter_geometry(self.field.net.state_dict()))
        return dict(summary=summary, physical_gradients=a, regularizer_gradients=b, total_gradients=total)

    def nodal_diagnostic(self, result):
        p = self.problem
        leaf = [result["fields"][name].detach().to(p.native_x).clone().requires_grad_(True) for name in ("u", "v", "d")]
        with torch.enable_grad():
            active = get_psi_plus_per_elem(p.native_x, *leaf, p.mat, p.model, p.native_area, p.cells,
                                           history_driver_reduction_dict=p.fatigue["history_driver_reduction"]).detach()
            history = update_fatigue_history(self.old["history"].to(p.native_x), active,
                                             self.old["active_driver"].to(p.native_x), p.fatigue)
            coefficient = compute_fatigue_degrad(history, p.fatigue).detach()
            energy = sum(compute_energy(p.native_x, *leaf, self.old["damage"].to(p.native_x), p.mat, p.model,
                                        p.native_area, p.cells, f_fatigue=coefficient, irreversibility_penalty_cfg=p.penalty))
            forces = torch.autograd.grad(energy, leaf)
        lower = self.old["damage"].to(p.native_x)
        kkt = nodal_box_residual(leaf[2].detach(), forces[2], lower, torch.ones_like(lower), 1e-10)
        free = torch.ones_like(lower, dtype=torch.bool)
        free[p.common["fixed_damage_nodes_zero_based"]] = False
        raw = result["raw_damage"].to(lower)
        blocked = free & (lower < 1) & (((raw < lower) & (forces[2] < 0)) | ((raw > 1) & (forces[2] > 0)))
        denominator = float(kkt[free].square().sum())
        summary = clipped_descent_receipt(raw, lower, forces[2])
        summary.update(blocked_kkt_squared_share=None if denominator == 0 else float(kkt[blocked].square().sum()) / denominator,
                       applies_to_actual_map=self.mapping == "nodal_clamp",
                       kink_derivative="minimum/maximum ties split derivatives; lower==1 explicitly constant/zero")
        return dict(force_u=forces[0], force_v=forces[1], force_d=forces[2], phase_kkt=kkt,
                    blocked_indices=torch.nonzero(blocked).reshape(-1), raw_to_lower=raw - lower,
                    raw_to_upper=raw - 1, summary=summary)

    def precision_readout(self, result):
        if self.dtype != torch.float32:
            return dict(status="already_float64; no float32 optimization claim")
        refined = EndpointEngine(self.problem, self.native_old, self.field.net.state_dict(), self.key,
                                 self.arm, torch.float64, self.deadline, self.provenance)
        refined.coefficient = self.coefficient.to(dtype=torch.float64).clone()
        output = refined.readout()
        delta = {name: output["fields"][name] - result["fields"][name].to(dtype=torch.float64) for name in ("u", "v", "d")}
        return dict(status="zero_updates", theta_cast_native_geometry_original_native_old=output,
                    network_field_delta=delta,
                    actual_float32_network_fields_promoted_native_operator=result["residual"],
                    old_solver_to_original_native_maxdelta={name: float((self.old[name].to(torch.float64) - value).abs().max())
                                                           for name, value in self.native_old.items()},
                    interpretation="all physics already native64; separates changed network realization from unchanged actual-field native assembly; not an isolated dtype optimization effect")


def publish_snapshot(directory, engine, result, stage, *, full_diagnostics=False, endpoint=False, extra=None):
    """Publish a complete *diagnostic* state, including rejected finite states.

    Completion means exact serialization and network readback, never an implicit
    scientific acceptance or history commit. Failed persistence is not consumed.
    """
    engine.check()
    directory.mkdir(parents=False)
    metadata = dict(schema="s04_e036_mechanism_fields_v1", state_key=engine.key, arm=engine.arm,
                    mapping=engine.mapping, weight_l2=engine.weight_l2, stage=stage,
                    dtype=str(engine.dtype).split(".")[-1], history_commit_count=0,
                    network_dtype=str(engine.dtype).split(".")[-1], physical_operator_dtype="float64",
                    physical_field_dtype="float64", old_state_dtype="float64",
                    changed_function_family=engine.mapping == "nodal_clamp",
                    coefficient_semantics=("fresh trial-f zero-update physical diagnostic; no physical optimizer" if engine.arm == "legacy_witness"
                                           else "last actually used fixed-f optimizer coefficient"),
                    rprop_updates=engine.work["rprop_updates"], lbfgs_steps=engine.work["lbfgs_steps"],
                    complete_endpoint=endpoint, teacher_initialized=engine.arm == "legacy_witness",
                    predecessor_checkpoint_sha256=engine.provenance["predecessor_checkpoint_sha256"])
    diagnostics = {}
    if full_diagnostics:
        diagnostics = dict(parameter=engine.decomposition(), nodal=engine.nodal_diagnostic(result),
                           precision=engine.precision_readout(result),
                           physical=native_readout(engine.problem, result["fields"], engine.old,
                               result["f_solve"], result["history"], result["f_commit"]))
    payload = cpu(dict(schema="s04_e036_mechanism_snapshot_v1", metadata=metadata,
                       common_problem=engine.problem.common, network_state=dict(engine.field.net.state_dict()),
                       old_state=engine.old, native_old_state=engine.native_old, result=result,
                       work=engine.work, provenance=engine.provenance, diagnostics=diagnostics, extra=extra))
    weights = atomic_file(directory, "network.pt", lambda stream: torch.save(payload["network_state"], stream))
    saved_network = torch.load(weights, map_location="cpu", weights_only=True)
    exact_payload(payload["network_state"], saved_network)
    metadata["network_state_sha256"] = sha256(weights)
    payload["metadata"] = copy.deepcopy(metadata)
    bundle = atomic_file(directory, "bundle.pt", lambda stream: torch.save(payload, stream))
    loaded = torch.load(bundle, map_location="cpu", weights_only=True)
    exact_payload(payload, loaded)
    replay = EndpointEngine(engine.problem, loaded["native_old_state"], saved_network, loaded["metadata"]["state_key"],
                            loaded["metadata"]["arm"], engine.dtype, engine.deadline, loaded["provenance"])
    exact_payload(loaded["old_state"], cpu(replay.old))
    replay.coefficient = loaded["result"]["f_solve"].to(engine.problem.device)
    fresh = replay.readout()
    for name in ("fields", "raw_damage", "history", "f_solve", "f_commit"):
        exact_payload(loaded["result"][name], cpu(fresh[name]))
    if fresh["physical_accepted"] != result["physical_accepted"]:
        raise ValueError("fresh readback changed physical acceptance")
    arrays = {name: loaded["result"]["fields"][name].numpy() for name in ("u", "v", "d")}
    arrays.update(raw_damage=loaded["result"]["raw_damage"].numpy(),
                  old_damage=loaded["native_old_state"]["damage"].numpy(),
                  old_history=loaded["native_old_state"]["history"].numpy(),
                  old_active_driver=loaded["native_old_state"]["active_driver"].numpy(),
                  metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)))
    fields_file = atomic_file(directory, "fields.npz", lambda stream: np.savez(stream, **arrays))
    with np.load(fields_file, allow_pickle=False) as saved:
        for name, value in arrays.items():
            if not np.array_equal(saved[name], value):
                raise ValueError("field NPZ readback changed " + name)
    engine.check()
    engine.work["snapshot_replays"] += 1
    receipt = dict(schema="s04_e036_mechanism_completion_v1", endpoint_complete=endpoint,
                   bundle_sha256=sha256(bundle), fields_sha256=sha256(fields_file), network_sha256=sha256(weights),
                   readback_verified=True, fields_reproduced_exactly=True,
                   physical_accepted=fresh["physical_accepted"], history_commit_count=0,
                   metadata=metadata, fresh_readback=fresh["residual"], actual_work=copy.deepcopy(engine.work))
    new_json(directory / "completion.json", receipt)
    return receipt


def load_endpoint(spec, root, problem, native_old, key, arm, deadline, provenance):
    if set(spec) != {"completion", "bundle"}:
        raise ValueError("continuation needs independently bound completion and bundle")
    completion_path = bound_file(spec["completion"], root)
    bundle = bound_file(spec["bundle"], root)
    receipt = read_json(completion_path)
    if (receipt.get("schema") != "s04_e036_mechanism_completion_v1" or receipt.get("endpoint_complete") is not True
            or receipt.get("readback_verified") is not True or receipt.get("bundle_sha256") != sha256(bundle)):
        raise ValueError("incomplete or unverified source endpoint")
    payload = torch.load(bundle, map_location="cpu", weights_only=True)
    exact_metadata(receipt["metadata"], payload["metadata"], "completion/bundle metadata")
    exact_metadata(payload["metadata"]["state_key"], key, "source endpoint state")
    expected_mapping, expected_l2 = ARMS[arm]
    if (payload["metadata"]["arm"] != arm or payload["metadata"]["history_commit_count"] != 0
            or payload["metadata"]["mapping"] != expected_mapping or payload["metadata"]["weight_l2"] != expected_l2
            or payload["metadata"]["stage"] != "first_2000" or payload["metadata"]["rprop_updates"] != 2000
            or payload["metadata"]["physical_operator_dtype"] != "float64"
            or payload["provenance"]["manifest_sha256"] != provenance["manifest_sha256"]
            or payload["provenance"]["theta0_sha256"] != provenance["theta0_sha256"]
            or payload["provenance"]["predecessor_checkpoint_sha256"] != provenance["predecessor_checkpoint_sha256"]):
        raise ValueError("source endpoint is not the predeclared arm")
    exact_payload(payload["native_old_state"], cpu(native_old))
    exact_payload(payload["old_state"], payload["native_old_state"])
    exact_metadata(payload["common_problem"], problem.common, "source common problem")
    dtype = {"float32": torch.float32, "float64": torch.float64}[payload["metadata"]["dtype"]]
    engine = EndpointEngine(problem, native_old, payload["network_state"], key, arm, dtype, deadline, provenance)
    engine.coefficient = payload["result"]["f_solve"].to(problem.device)
    fresh = engine.readout()
    for name in ("fields", "raw_damage", "history", "f_solve", "f_commit"):
        exact_payload(payload["result"][name], cpu(fresh[name]))
    if (payload["work"]["rprop_updates"] != 2000 or payload["work"]["history_commits"] != 0
            or payload["work"]["lbfgs_steps"] != 0 or payload["work"]["lbfgs_closures"] != 0
            or any(payload["work"][name] != receipt["actual_work"][name] for name in
                   ("rprop_updates", "lbfgs_steps", "lbfgs_closures", "coefficient_refreshes", "history_commits"))):
        raise ValueError("source endpoint work/history differs")
    engine.work.update(receipt["actual_work"])
    return engine, fresh, payload


def rprop_block(engine, event_file, target=None, fit_geometry=None):
    optimizer = get_optimizer(engine.field.net.parameters(), "RPROP")
    plateau = EarlyStopping(tol_steps=10, min_delta=5e-7, device=engine.problem.device)
    previous = torch.zeros(1, device=engine.problem.device, dtype=engine.dtype)
    for _ in range(200):
        engine.check()
        optimizer.zero_grad(set_to_none=True)
        if target is None:
            physical, regularizer, energy = engine.objective()
            loss = physical + regularizer
        else:
            fields, _ = engine.field.values()
            loss, _ = fit_objective(fields, target, *fit_geometry)
        if not bool(torch.isfinite(loss)):
            raise NumericalFailure("nonfinite RPROP objective")
        loss.backward()
        if any(p.grad is not None and not bool(torch.isfinite(p.grad).all()) for p in engine.field.net.parameters()):
            raise NumericalFailure("nonfinite parameter gradient")
        optimizer.step()
        engine.work["rprop_updates"] += 1
        engine.check()
        plateau(loss.detach(), previous)
        previous = loss.detach()
        if plateau.early_stop and "first_legacy_plateau" not in engine.events:
            engine.events.add("first_legacy_plateau")
            # Saved immediately at the actual first decision, not a later block.
            result = engine.readout()
            publish_snapshot(event_file.parent / "first_legacy_plateau", engine, result, "first_legacy_plateau")
        append_event(event_file, dict(event="rprop", loss_before_update=float(loss.detach()), work=engine.work.copy()))
    engine.verify_old()


def matrix_arm(engine, directory):
    directory.mkdir()
    event_file = directory / "events.jsonl"
    initial = engine.readout()
    projection = (projection_receipt(initial["raw_damage"], initial["fields"]["d"], engine.old["damage"])
                  if engine.mapping == "nodal_clamp" else dict(mapping="legacy", changed_function_family=False))
    mass = torch.zeros(len(engine.problem.x), device=engine.problem.device, dtype=torch.float64)
    mass.index_add_(0, engine.problem.cells.reshape(-1), torch.einsum("eg,gn->en", engine.problem.native_weights,
                                                                  engine.problem.native_shape).reshape(-1))
    projection["initial_projection_J"] = float(torch.sqrt((mass * (initial["fields"]["d"] - initial["raw_damage"]).square()).sum()
                                                          / (3 * mass.sum())))
    publish_snapshot(directory / "initial", engine, initial, "initial", full_diagnostics=True, extra=projection)
    # Always 2000 for this prefix. An earlier accepted diagnostic does not
    # shorten one arm of the 2x2 equal-work comparison or commit history.
    for block in range(1, 11):
        rprop_block(engine, event_file)
        result = engine.readout()
        if result["coefficient_fixed_point"] and "first_f_fixed_point" not in engine.events:
            engine.events.add("first_f_fixed_point")
            publish_snapshot(directory / "first_f_fixed_point", engine, result, "first_f_fixed_point")
        last = block == 10
        publish_snapshot(directory / ("first_2000" if last else f"rprop_{block * 200:06d}"), engine, result,
                         "first_2000" if last else "fixed_work", full_diagnostics=last, endpoint=last)
        if not last:
            engine.refresh(result)
    return dict(status="complete_2000_prefix", physical_accepted=result["physical_accepted"], work=engine.work.copy())


def make_lbfgs(engine):
    return torch.optim.LBFGS(engine.field.net.parameters(), lr=1., max_iter=1,
        max_eval=SOLVER["lbfgs_closures_per_step"], tolerance_grad=0., tolerance_change=0.,
        history_size=SOLVER["lbfgs_history_size"], line_search_fn="strong_wolfe")


def lbfgs_phase(engine, directory, target=None):
    """Persistent curvature for one fixed objective; reset only when f changes."""
    directory.mkdir()
    event_file = directory / "events.jsonl"
    p = engine.problem
    mass = torch.zeros(len(p.x), dtype=torch.float64, device=p.device)
    mass.index_add_(0, p.cells.reshape(-1), torch.einsum("eg,gn->en", p.native_weights, p.native_shape).reshape(-1))
    geometry = (mass, p.native_weights, p.native_dshape, p.cells)
    optimizer = make_lbfgs(engine)
    parameters = list(engine.field.net.parameters())
    changes, fixed_steps = [], 0
    def evaluate():
        if target is None:
            a, b, energy = engine.objective()
            return a + b, dict(energy=float(energy.detach()))
        fields, _ = engine.field.values()
        return fit_objective(fields, target, *geometry)
    initial = engine.readout()
    _, report = evaluate()
    publish_snapshot(directory / "initial", engine, initial, "lbfgs_initial", full_diagnostics=True, extra=report)
    while True:
        engine.check()
        if target is not None and fit_program_stop(report):
            reason = "fit_program_stop_reached_not_physical_or_capacity_threshold"
            break
        if target is None and initial["physical_accepted"]:
            reason = "fresh_physical_acceptance"
            break
        before_loss, before_report = evaluate()
        before_value = float(before_loss.detach()) if target is not None else before_report["energy"]
        def closure():
            optimizer.zero_grad(set_to_none=True)
            value, _ = evaluate()
            if not bool(torch.isfinite(value)):
                raise NumericalFailure("nonfinite LBFGS objective")
            value.backward()
            if any(q.grad is not None and not bool(torch.isfinite(q.grad).all()) for q in parameters):
                raise NumericalFailure("nonfinite LBFGS gradient")
            return value
        try:
            calls = bounded_lbfgs_step(optimizer, parameters, closure, engine.work, engine.check,
                                       SOLVER["lbfgs_closures_per_step"])
        except ClosureLimit as error:
            reason = "line_search_limit_restored_previous_state"
            append_event(event_file, dict(event=reason, detail=str(error), work=engine.work.copy()))
            break
        value, report = evaluate()
        after = float(value.detach()) if target is not None else report["energy"]
        changes.append(relative_change(before_value, after))
        fixed_steps += 1
        initial = engine.readout()
        append_event(event_file, dict(event="accepted_lbfgs_step", closures=calls, objective_report=report,
                                     C=initial["C"], physical_accepted=initial["physical_accepted"], work=engine.work.copy()))
        if engine.work["lbfgs_steps"] % 200 == 0:
            publish_snapshot(directory / f"step_{engine.work['lbfgs_steps']:06d}", engine, initial,
                             "lbfgs_fixed_work", extra=report)
        stagnant = (len(changes) >= 20 and max(changes[-20:]) <=
                    (SOLVER["fit_relative_loss_change"] if target is not None else SOLVER["physics_relative_energy_change"]))
        if target is not None and stagnant and not fit_program_stop(report):
            reason = "fit_stagnation_no_capacity_lower_bound"
            break
        if target is None and (stagnant or fixed_steps == SOLVER["lbfgs_fixed_f_steps"]):
            if stagnant and initial["coefficient_fixed_point"] and not initial["physical_accepted"]:
                reason = "fixed_f_numerical_stagnation_not_stationarity_proof"
                break
            if not initial["physical_accepted"]:
                changed = not torch.equal(engine.coefficient, initial["f_commit"])
                engine.refresh(initial)
                # Curvature from another fixed coefficient is invalid. Within
                # each fixed-f block this optimizer persists across all steps.
                if changed:
                    optimizer = make_lbfgs(engine)
                    changes = []
                fixed_steps = 0
                append_event(event_file, dict(event="coefficient_refresh", curvature_reset=changed, work=engine.work.copy()))
    final = engine.readout()
    _, report = evaluate()
    publish_snapshot(directory / "final", engine, final, "lbfgs_final", full_diagnostics=True, endpoint=True,
                     extra=dict(stop_reason=reason, objective_report=report,
                                fit_interpretation="observed approximation upper bound at this seen target, never a capacity lower bound" if target is not None else None))
    return dict(status=reason, physical_accepted=final["physical_accepted"], objective_report=report, work=engine.work.copy())


def candidate_continuation(engine, result, directory):
    if engine.arm != "C0" or engine.dtype != torch.float32 or engine.work["rprop_updates"] != 2000:
        raise ValueError("only the predeclared C0 float32 first-2000 endpoint can continue")
    directory.mkdir()
    event_file = directory / "events.jsonl"
    scores = [result["C"]]
    previous_fields = cpu(result["fields"])
    while not result["physical_accepted"]:
        engine.refresh(result)
        rprop_block(engine, event_file)
        result = engine.readout()
        publish_snapshot(directory / f"rprop_{engine.work['rprop_updates']:06d}", engine, result,
                         "candidate_rprop", full_diagnostics=False)
        scores.append(result["C"])
        unchanged = all(torch.equal(previous_fields[name], cpu(result["fields"][name])) for name in ("u", "v", "d"))
        previous_fields = cpu(result["fields"])
        if unchanged or stalled(scores, 10, .01):
            break
    if result["physical_accepted"]:
        publish_snapshot(directory / "final", engine, result, "candidate_rprop_accepted", full_diagnostics=True, endpoint=True)
        return dict(status="fresh_physical_acceptance_float32", work=engine.work.copy())
    publish_snapshot(directory / "float32_stagnation", engine, result, "candidate_float32_stagnation",
                     full_diagnostics=True, endpoint=True)
    refined = EndpointEngine(engine.problem, engine.native_old, engine.field.net.state_dict(), engine.key,
                             "C0", torch.float64, engine.deadline,
                             dict(engine.provenance, continuation="precision_plus_solver; not isolated dtype effect"))
    refined.work.update(engine.work)
    refined.coefficient = result["f_commit"].to(dtype=torch.float64).clone()
    return lbfgs_phase(refined, directory / "float64_lbfgs")


def phase_authority(args, doc, problem):
    authority, source = check_authority(args.authority, args.manifest, problem.device)
    exact_metadata(authority.get("mechanism_phase"), args.phase, "authorized mechanism phase")
    exact_metadata(authority.get("requested_case", "missing"), args.case, "authorized state partition")
    if authority.get("job_wall_seconds") != doc["job_wall_seconds"] or authority.get("cumulative_resource_limit", "missing") is not None:
        raise ValueError("explicit per-job setting and no cumulative resource cap required")
    root = Path(args.authority).resolve().parent
    lock = read_json(bound_file(authority["implementation_lock"], root))
    if not EXTRA_LOCK_FILES <= set(lock["files"]):
        raise ValueError("mechanism implementation dependencies absent from lock")
    stage_a = validate_stage_a_reuse(bound_file(authority["fem_validation"], root),
                                    bound_file(authority["stage_a_semantic_binding"], root), ROOT, problem)
    if args.phase == "matrix":
        if args.targets is not None or args.source_endpoints is not None:
            raise ValueError("matrix phase cannot receive target or continuation manifests")
    else:
        flag, name = (args.targets, "target_manifest") if args.phase == "target_fit" else (args.source_endpoints, "source_endpoints")
        if flag is None or bound_file(authority[name], root) != Path(flag).resolve():
            raise ValueError("phase-specific input must be separately authorized and hash-bound")
        if args.phase != "target_fit" and args.targets is not None:
            raise ValueError("physics continuation must not receive target fields")
    return dict(authority=authority, source=source, stage_a_reuse=stage_a)


def execution_cases(requested_case):
    if requested_case is not None and requested_case not in CASES:
        raise ValueError("partition must name one of the four predetermined states")
    return tuple(CASES) if requested_case is None else (requested_case,)


def release_contract(witness_completion, physical_readout, conditions):
    """Prepare a reviewable next-phase interface; never starts a hidden release."""
    if witness_completion.get("endpoint_complete") is not True or witness_completion.get("metadata", {}).get("arm") != "legacy_witness":
        raise ValueError("a complete original-family witness is required")
    if not conditions or not isinstance(conditions, str):
        raise ValueError("explicit observed reason for conditional release required")
    return dict(schema="s04_e036_witness_release_request_v1", teacher_initialized=True,
                witness_completion=witness_completion, zero_update_physical_readout=physical_readout,
                observed_condition=conditions, proposed_arms=["legacy_lambda0", "nodal_clamp_lambda0"],
                immutable_old="same separately bound F1 predecessor", execution_status="requires separate phase implementation/review and bound authority",
                forbidden_claim="not physics-only from canonical theta0")


def main(args):
    device = torch.device(args.device)
    # check_authority is intentionally before load_problem: a CPU or Mac caller
    # cannot accidentally instantiate even the full geometry of a science job.
    check_authority(args.authority, args.manifest, device)
    doc, root, problem = load_problem(args.manifest, device)
    provenance = phase_authority(args, doc, problem)
    deadline = Deadline(doc["job_wall_seconds"], "mechanism job")
    if args.out.exists():
        raise FileExistsError("fresh phase output required; no automatic retry/resume")
    args.out.mkdir(parents=True)
    new_json(args.out / "attempt.json", dict(schema="s04_e036_mechanism_attempt_v1", phase=args.phase,
        requested_case=args.case, declared_cases=list(CASES), execution_cases=list(execution_cases(args.case)),
        manifest_sha256=sha256(args.manifest), provenance=provenance, command=sys.argv,
        job_wall_seconds=doc["job_wall_seconds"], cumulative_resource_limit=None, pid=os.getpid(),
        started_unix=time.time(), history_commit_count=0))
    torch.manual_seed(1)
    torch.use_deterministic_algorithms(True)
    targets = sources = None
    if args.phase == "target_fit":
        targets = read_json(args.targets)
        if (set(targets) != {"schema", "physics_manifest", "targets"}
                or targets["schema"] != "s04_e036_mechanism_targets_v1" or set(targets["targets"]) != set(CASES)
                or bound_file(targets["physics_manifest"], Path(args.targets).resolve().parent) != Path(args.manifest).resolve()):
            raise ValueError("separate four-state target manifest must bind exactly this physics manifest")
    if args.phase == "candidate_continuation":
        sources = read_json(args.source_endpoints)
        if (set(sources) != {"schema", "physics_manifest", "cases"}
                or sources["schema"] != "s04_e036_C0_continuation_v1" or set(sources["cases"]) != set(CASES)
                or bound_file(sources["physics_manifest"], Path(args.source_endpoints).resolve().parent) != Path(args.manifest).resolve()):
            raise ValueError("C0 continuation must bind this exact four-state physics manifest")
    outcomes = []
    for name in execution_cases(args.case):
        deadline.check()
        spec = doc["cases"][name]
        native_old, theta0, admission = load_predecessor(spec, root, problem)
        common_provenance = dict(case=name, manifest_sha256=sha256(args.manifest), theta0_sha256=NETWORK_SHA[name],
            predecessor_checkpoint_sha256=admission["source_checkpoint"]["sha256"], predecessor=spec["predecessor"],
            predecessor_admission=spec["admission"], execution_phase=args.phase)
        case_dir = args.out / name
        case_dir.mkdir()
        if args.phase == "matrix":
            for arm in ARMS:
                engine = EndpointEngine(problem, native_old, theta0, spec["state_key"], arm, torch.float32, deadline, common_provenance)
                try:
                    result = matrix_arm(engine, case_dir / arm)
                except (TimeBudgetExceeded, OSError, RuntimeError):
                    # Unknown infrastructure/AD/persistence failures stop this job.
                    raise
                except NumericalFailure as error:
                    # Preserve the failed science arm; no repair/restart/target selection.
                    result = dict(status="failed", reason=str(error), work=engine.work.copy())
                    new_json(case_dir / arm / "failure.json", result)
                outcomes.append(dict(case=name, arm=arm, **result))
                new_json(args.out / f"outcome_{len(outcomes):02d}.json", outcomes[-1])
        elif args.phase == "target_fit":
            from score_paired_windows import load_target
            target, target_receipt = load_target(targets["targets"][name], Path(args.targets).resolve().parent,
                spec["state_key"], problem, expected_predecessor_sha256=admission["source_checkpoint"]["sha256"], expected_old=native_old)
            if target_receipt["native_solver_policy"] != {"u_tol": 1e-6, "joint_tol": 4e-4}:
                raise ValueError("witness must fit admitted standard F1, not replace it with a tighter/selected target")
            engine = EndpointEngine(problem, native_old, theta0, spec["state_key"], "legacy_witness", torch.float64,
                deadline, dict(common_provenance, target_admission=target_receipt, seen_target=True))
            result = lbfgs_phase(engine, case_dir / "legacy_witness", target=target)
            outcomes.append(dict(case=name, **result))
            new_json(args.out / f"outcome_{len(outcomes):02d}.json", outcomes[-1])
        else:
            engine, initial, payload = load_endpoint(sources["cases"][name], Path(args.source_endpoints).resolve().parent,
                problem, native_old, spec["state_key"], "C0", deadline,
                dict(common_provenance, source_endpoint=sources["cases"][name]))
            result = candidate_continuation(engine, initial, case_dir / "C0")
            outcomes.append(dict(case=name, **result))
            new_json(args.out / f"outcome_{len(outcomes):02d}.json", outcomes[-1])
    new_json(args.out / "finished.json", dict(status="program_completed", phase=args.phase, outcomes=outcomes,
        requested_case=args.case, declared_cases=list(CASES), execution_cases=list(execution_cases(args.case)),
        complete_four_state_program=args.case is None,
        history_commit_count=0, scientific_interpretation="conditional independent endpoints; no capacity lower bound or fatigue-life claim"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--phase", choices=("matrix", "target_fit", "candidate_continuation"), required=True)
    parser.add_argument("--targets", type=Path)
    parser.add_argument("--source-endpoints", type=Path)
    parser.add_argument("--case", choices=tuple(CASES),
                        help="Execution partition only; full manifest stays fixed and authority binds this case (null for all)")
    arguments = parser.parse_args()
    try:
        main(arguments)
    except BaseException as error:
        if arguments.out.is_dir() and (arguments.out / "attempt.json").is_file():
            path = arguments.out / "job_failure.json"
            if not path.exists():
                new_json(path, dict(error_type=type(error).__name__, message=str(error), retry_permitted=False,
                                    history_commit_count=0, ended_unix=time.time()))
        raise
