#!/usr/bin/env python3
"""Conditional P1/P2 windows; execution requires a separately approved envelope.

No pretraining, zero-load recovery, implicit resume, target supervision or FEM
solve is performed here. Importing this module does not launch work. This is a
new entry point; the historical/default training runner remains unchanged.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "SENS_tensile"), str(ROOT / "source"), str(Path(__file__).parent)]

# Reuse the E011 frozen-state network constructor, retaining its legacy free
# damage mapping. Do not import LocalProblem/make_smooth: those change the
# material/field mapping and load future target fields for a different probe.
from run_native_q4_one_step_matrix import make_field
from compute_energy import compute_energy, get_psi_plus_per_elem
from cyclic_acceptance import install_sent_common_problem, make_sent_final_residual_check
from cyclic_persistence import PersistenceVerificationError, persist_verified_step
from fatigue_history import compute_fatigue_degrad
from fit import EarlyStopping
from material_properties import MaterialProperties
from optim import get_optimizer
from pff_model import PFFModel
from q4_quadrature import q4_shape_data
from trial_fatigue_coupling import PhysicalStepOptimizerBudget, TrialFatigueNotConverged, solve_trial_fatigue_step
from window_inputs import CASES, LOADS, bound_file, load_case, load_manifest, optimizer_work, read_json, sha256, state_key
from stage_a_reuse import validate_stage_a_reuse


def write_json(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def cpu_copy(value):
    if torch.is_tensor(value):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: cpu_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [cpu_copy(item) for item in value]
    return copy.deepcopy(value)


def objective_precision_record(old, coefficient):
    """Make the native-history / float32-objective distinction observable."""
    report = {}
    for name, value in {**old, "f_solve": coefficient}.items():
        if value is None:
            report[name] = None
            continue
        native = value.detach().to(dtype=torch.float64)
        rounded = value.detach().to(dtype=torch.float32).to(dtype=torch.float64)
        report[name] = dict(source_dtype=str(value.dtype), objective_dtype="torch.float32",
            float32_roundtrip_maxdelta=float((native - rounded).abs().max().cpu()),
            actually_cast_for_energy=name in {"damage", "f_solve"})
    return dict(fields=report, history_arithmetic_dtype="torch.float64",
        current_active_sampling_dtype="torch.float32",
        interpretation="old native d/A/r retained for fresh residual; energy casts old d and f_solve to float32; A/r are not energy arguments")


def fatigue_config(common):
    return dict(fatigue_on=True, loading_type="cyclic", accum_type="carrara",
                degrad_type="asymptotic", alpha_T=.5, history_storage="q4_gp4",
                history_driver_mode="current_active", damage_history_storage="previous_accepted_nodal",
                explicit_cycle_substeps=5, history_driver_reduction={"enable": True, "mode": "native_q4_gp4"},
                common_problem=common)


def source_provenance(root, implementation_files):
    """Accept either a checkout or a fully bound minimal standalone snapshot."""
    root = Path(root).resolve()
    snapshot_path = root / "source_snapshot.json"
    if snapshot_path.is_file():
        snapshot = read_json(snapshot_path)
        if (set(snapshot) != {"schema", "source_commit", "files"}
                or snapshot["schema"] != "s04_e036_source_snapshot_v1"
                or not isinstance(snapshot["source_commit"], str)
                or re.fullmatch(r"[0-9a-f]{40}", snapshot["source_commit"]) is None
                or not isinstance(snapshot["files"], dict)):
            raise ValueError("invalid standalone source snapshot provenance")
        files = snapshot["files"]
        if any(files.get(name) != digest for name, digest in implementation_files.items()):
            raise ValueError("source snapshot does not cover the complete implementation lock")
        # These are the runtime import roots. A newly copied executable module
        # cannot silently join a snapshot without both independent byte maps.
        runtime = {str(path.relative_to(root)) for directory in
                   (root / "source", root / "SENS_tensile", root / "tools/s04_e036")
                   for path in directory.rglob("*.py")}
        if not runtime <= set(implementation_files):
            raise ValueError("unlocked executable module in standalone source snapshot")
        for relative, digest in files.items():
            candidate = root / relative
            source = candidate.resolve()
            if (Path(relative).is_absolute() or not source.is_relative_to(root)
                    or candidate.is_symlink() or not source.is_file()
                    or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                    or sha256(source) != digest):
                raise ValueError(f"source snapshot file mismatch: {relative}")
        return dict(source_kind="standalone_snapshot", source_commit=snapshot["source_commit"],
                    source_snapshot_sha256=sha256(snapshot_path), git_head=None, git_dirty=None)
    if not (root / ".git").exists():
        raise ValueError("producer needs its own Git checkout or a verified source_snapshot.json")
    return dict(source_kind="git_checkout",
                git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                git_dirty=subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True))


def check_authority(path, manifest_path, device):
    """Fail closed until a human-approved, version-bound envelope is supplied."""
    authority = read_json(path)
    if authority.get("schema") != "s04_e036_execution_authority_v1" or authority.get("approved") is not True:
        raise ValueError("a separately approved execution envelope is required")
    if not isinstance(authority.get("approval_reference"), str) or not authority["approval_reference"].strip():
        raise ValueError("missing actual user approval reference")
    if authority.get("manifest_sha256") != sha256(manifest_path):
        raise ValueError("approval does not cover these inputs/budgets")
    if authority.get("hostname") != platform.node() or platform.system() == "Darwin":
        raise ValueError("this is not the explicitly approved producer (Mac training is forbidden)")
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if not visible or "," in visible or device.type != "cuda" or device.index not in (None, 0):
        raise ValueError("one explicitly selected CUDA GPU and cuda:0 are required")
    if str(authority.get("cuda_visible_devices")) != visible or not torch.cuda.is_available():
        raise ValueError("GPU selection differs from approval or CUDA unavailable")
    lock_path = bound_file(authority["implementation_lock"], Path(path).resolve().parent)
    lock = read_json(lock_path)
    if lock.get("schema") != "s04_e036_implementation_lock_v1":
        raise ValueError("wrong implementation lock")
    for relative, digest in lock["files"].items():
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT) or sha256(source) != digest:
            raise ValueError(f"implementation drift: {relative}")
    required = {"source/trial_fatigue_coupling.py", "source/cyclic_persistence.py",
                "source/cyclic_acceptance.py", "source/compute_energy.py", "source/fatigue_history.py",
                "source/q4_quadrature.py", "source/network.py", "source/fit.py", "source/optim.py",
                "source/material_properties.py", "source/pff_model.py",
                "SENS_tensile/field_computation.py", "SENS_tensile/run_native_q4_one_step_matrix.py",
                "tools/s04_e036/run_paired_windows.py", "tools/s04_e036/window_inputs.py",
                "tools/s04_e036/stage_a_reuse.py"}
    if not required <= set(lock["files"]):
        raise ValueError("incomplete implementation lock")
    provenance = source_provenance(ROOT, lock["files"])
    validation_path = bound_file(authority["fem_validation"], Path(path).resolve().parent)
    validation = read_json(validation_path)
    if validation.get("schema") != "s04_e036_fem_validation_v2" or validation.get("accepted") is not True:
        raise ValueError("completed Stage A reuse validation v2 is required before NN optimization")
    bound_file(authority["stage_a_semantic_binding"], Path(path).resolve().parent)
    return authority, provenance


class TimeBudgetExceeded(RuntimeError):
    """No additional numerical readout may start after a wall-clock stop."""


class Deadline:
    def __init__(self, seconds, label):
        self.end = time.monotonic() + seconds
        self.label = label

    def check(self):
        if time.monotonic() >= self.end:
            raise TimeBudgetExceeded(self.label + " wall-clock budget exhausted")


class WindowProblem:
    def __init__(self, nodes, cells, common, device):
        self.device = device
        self.x = torch.as_tensor(nodes.copy(), dtype=torch.float32, device=device)
        self.native_x = torch.as_tensor(nodes.copy(), dtype=torch.float64, device=device)
        self.cells = torch.as_tensor(cells.copy(), dtype=torch.long, device=device)
        self.area = q4_shape_data(self.x, self.cells)[2].sum(1)
        self.native_shape, self.native_dshape, self.native_weights = q4_shape_data(self.native_x, self.cells)
        self.native_area = self.native_weights.sum(1)
        self.common = common
        self.fatigue = fatigue_config(common)
        self.mat = MaterialProperties(1., .3, 1., .01)
        self.model = PFFModel("AT1", "volumetric", .001, residual_stiffness=0.)
        self.penalty = dict(enable=True, mode="fem_gp_q4", spatial_integration="native_q4_gp4",
                            recovery_penalty_coefficient=13781.25)

    def field(self, network_state, displacement):
        field = make_field(network_state, self.device, displacement, "legacy_nonsmooth")
        field.net.eval()  # No dropout/batch norm; parameters still require gradients.
        install_sent_common_problem(inp=self.x, T_conn=self.cells, field_comp=field,
                                    matprop=self.mat, pffmodel=self.model,
                                    irreversibility_penalty_cfg=self.penalty,
                                    config=self.common, fatigue_dict=self.fatigue)
        return field

    def residual(self, field, *, history_atol=None, history_rtol=None):
        policy = dict(self.common["acceptance_config"])
        if history_atol is not None or history_rtol is not None:
            if (history_atol, history_rtol) != (1e-10, 0.):
                raise ValueError("the only history-policy override is native FEM absolute 1e-10")
            policy.update(history_atol=history_atol, history_rtol=history_rtol)
        return make_sent_final_residual_check(
            inp=self.native_x, T_conn=self.cells, area_T=self.native_area, matprop=self.mat,
            pffmodel=self.model, field_comp=field, irreversibility_penalty_cfg=self.penalty,
            config=policy, fatigue_dict=self.fatigue)

    def state(self, field):
        with torch.no_grad():
            u, v, d = field.fieldCalculation(self.x)
            active = get_psi_plus_per_elem(self.x, u, v, d, self.mat, self.model, self.area,
                                          self.cells, history_driver_reduction_dict=self.fatigue["history_driver_reduction"])
        return dict(u=u.detach(), v=v.detach(), d=d.detach(), active_driver=active.detach(),
                    displacement=field.lmbda.detach())

    def old_state(self, arrays, key):
        old = {name: torch.as_tensor(arrays[source], dtype=torch.float64, device=self.device).clone()
               for name, source in (("damage", "damage"), ("history", "history"), ("active_driver", "active_driver"))}
        # Check the exported committed active driver against its actual field;
        # this is a readout, not a solve and not a replacement for FEM admission.
        u, v, d = [torch.as_tensor(arrays[name], dtype=torch.float64, device=self.device) for name in ("u", "v", "damage")]
        x64 = self.native_x
        active = get_psi_plus_per_elem(x64, u, v, d, self.mat, self.model, self.native_area, self.cells,
                                      history_driver_reduction_dict=self.fatigue["history_driver_reduction"])
        source_active = torch.as_tensor(arrays["active_driver"], dtype=torch.float64, device=self.device)
        if not torch.allclose(active, source_active, atol=2e-6, rtol=2e-6):
            raise ValueError("predecessor active driver does not match its stored field")
        fixed = self.common["fixed_damage_nodes_zero_based"]
        if not bool(torch.all(d[fixed] == 1)):
            raise ValueError("predecessor lacks the common hard precrack")
        y = x64[:, 1]
        bottom, top = y == y.min(), y == y.max()
        if (float(u[bottom | top].abs().max()) > 5e-8 or float(v[bottom].abs().max()) > 5e-8
                or float((v[top] - key["displacement"]).abs().max()) > 5e-8):
            raise ValueError("predecessor load boundary does not match physical key")
        return old

    def replay(self, payload):
        """Reconstruct mapping and final fields from saved weights, then recheck."""
        if payload["common_problem"] != self.common:
            raise ValueError("persisted field mapping differs")
        field = self.field(payload["network_state"], payload["state_key"]["displacement"])
        fresh = self.state(field)
        for name, value in fresh.items():
            expected = payload["fields"][name].to(value.device)
            if value.dtype != expected.dtype or not torch.equal(value, expected):
                raise ValueError(f"saved network/mapping does not reproduce {name}")
        old = {key: value.to(self.device) for key, value in payload["old_state"].items()}
        context = dict(fresh, old_damage=old["damage"], old_history=old["history"],
                       old_active_driver=old["active_driver"], trial_history=payload["history"].to(self.device),
                       f_solve=payload["f_solve"].to(self.device), f_commit=payload["f_commit"].to(self.device),
                       state_token=uuid.uuid4().hex)
        receipt = self.residual(field)(context)
        mode = payload["metadata"]["coefficient_mode"]
        if mode not in {"trial", "frozen_old"}:
            raise ValueError("unknown saved arm policy")
        if mode == "trial":
            delta = abs(context["f_solve"] - context["f_commit"])
            f_ok = bool(torch.all(delta <= 2e-6 + 2e-6 * torch.maximum(abs(context["f_solve"]), abs(context["f_commit"]))))
        else:
            f_old = compute_fatigue_degrad(old["history"], self.fatigue)
            f_ok = bool(torch.allclose(context["f_solve"], f_old, atol=2e-6, rtol=2e-6))
        return dict(accepted=bool(receipt["accepted"] and f_ok), fields_reproduced_exactly=True,
                    coefficient_policy_verified=f_ok, physical_replay=receipt)


def run_step(problem, field, old, key, arm, directory, caps, total_deadline, provenance,
             *, window_updates_before_step):
    optimizer_work(0, window_updates_before_step)
    directory.mkdir()
    snapshots = directory / "snapshots"
    snapshots.mkdir()
    step_deadline = Deadline(caps["step_wall_seconds"], "physical step")
    work = PhysicalStepOptimizerBudget(caps["updates_per_block"], caps["max_updates_per_step"])
    losses, event_index = [], []
    plateau_seen = False
    current_coefficient = None
    current_precision = objective_precision_record(old, None)
    residual_check = None

    def check_time():
        total_deadline.check()
        step_deadline.check()

    def checked_state():
        check_time()
        state = problem.state(field)
        check_time()
        return state

    def snapshot(event):
        # Snapshots are diagnostics only. Only persist_verified_step publishes a
        # committed state; rejected snapshots must never seed another substep.
        number = len(event_index)
        name = f"{number:03d}_{event['event']}_u{work.rprop_updates:04d}.pt"
        counts = optimizer_work(work.rprop_updates, window_updates_before_step)
        payload = cpu_copy(dict(event=event, state_key=key, arm=arm, updates=work.rprop_updates,
                                optimizer_work=counts,
                                objective_precision=current_precision,
                                common_problem=problem.common, network_state=field.net.state_dict()))
        with (snapshots / name).open("xb") as stream:
            torch.save(payload, stream)
        event_index.append(dict(file=name, event=event["event"], updates=work.rprop_updates,
                                optimizer_work=counts))

    def optimize(coefficient, outer):
        nonlocal plateau_seen, current_coefficient, current_precision
        current_coefficient = coefficient.detach().clone()
        current_precision = objective_precision_record(old, current_coefficient)
        optimizer = get_optimizer(field.parameters(), "RPROP")
        plateau = EarlyStopping(tol_steps=10, min_delta=5e-7, device=problem.device)
        previous = torch.zeros(1, device=problem.device)
        for _ in range(work.next_rprop_epochs()):
            check_time()
            optimizer.zero_grad(set_to_none=True)
            u, v, d = field.fieldCalculation(problem.x)
            parts = compute_energy(problem.x, u, v, d, old["damage"].to(dtype=u.dtype), problem.mat, problem.model,
                                   problem.area, problem.cells, f_fatigue=coefficient,
                                   irreversibility_penalty_cfg=problem.penalty)
            energy = sum(parts)
            if not bool(torch.isfinite(energy)) or float(energy.detach()) <= 0:
                raise ValueError("original log-energy domain is nonpositive/nonfinite")
            regularizer = sum(param.square().sum() for name, param in field.net.named_parameters() if "weight" in name)
            loss = torch.log10(energy) + 1e-5 * regularizer
            if not bool(torch.isfinite(loss)):
                raise ValueError("nonfinite original objective")
            loss.backward()
            if any(p.grad is not None and not bool(torch.isfinite(p.grad).all()) for p in field.parameters()):
                raise ValueError("nonfinite parameter gradient")
            optimizer.step()
            work.record_rprop_updates(1)
            # A completed update remains counted if it used the remaining time.
            # Do not start a new field readout after discovering that stop.
            check_time()
            value = loss.detach()
            losses.append(dict(update=work.rprop_updates, outer=outer, loss_before_update=float(value),
                               optimizer_work=optimizer_work(work.rprop_updates, window_updates_before_step)))
            plateau(value, previous)
            if plateau.early_stop and not plateau_seen:
                snapshot(dict(event="first_legacy_loss_plateau", context=checked_state(),
                              old_state=old, f_solve=coefficient, trigger_loss_before_update=float(value),
                              note="post-update network at the legacy stopping decision; diagnostic only"))
                plateau_seen = True
            previous = value
            check_time()

    mode = "frozen_old" if arm == "P1" else "trial"
    coupling = dict(enable=True, coefficient_mode=mode, max_outer=caps["max_outer"],
                    epochs_per_outer=200, max_total_rprop_epochs=2000, f_atol=2e-6, f_rtol=2e-6,
                    relaxation=1., recovery_lbfgs_max_iter=1, recovery_lbfgs_max_eval=1)
    def checked_residual(context):
        check_time()
        receipt = residual_check(context)
        check_time()
        return receipt

    try:
        check_time()
        current_coefficient = compute_fatigue_degrad(old["history"], problem.fatigue)
        current_precision = objective_precision_record(old, current_coefficient)
        check_time()
        residual_check = problem.residual(field)
        check_time()
        result = solve_trial_fatigue_step(
            old_history=old["history"], old_active_driver=old["active_driver"], old_damage=old["damage"],
            initial_f=current_coefficient, fatigue_dict=problem.fatigue, config=coupling,
            solve_for_coefficient=optimize, evaluate_state=checked_state,
            final_residual_check=checked_residual, step=5 * (key["cycle"] - 1) + key["substep"],
            observer=snapshot)
        check_time()
        payload = dict(network_state=field.net.state_dict(), common_problem=problem.common,
                       old_state=old, fields=result.state, history=result.history,
                       f_solve=result.f_solve, f_commit=result.f_commit, state_key=key,
                       provenance=provenance, acceptance_records=result.records,
                       metadata=dict(arm=arm, coefficient_mode=mode, rprop_updates=work.rprop_updates,
                                     optimizer_work=optimizer_work(work.rprop_updates, window_updates_before_step),
                                     objective_precision=current_precision,
                                     history_commit_count=1, legacy_plateau_seen=plateau_seen,
                                     objective="log10(E_el+E_d+E_hist)+1e-5*sum(weight^2)",
                                     dtype="network_and_objective_float32_old_history_float64", damage_mapping="legacy_nonsmooth_plus_common_fixed_nodes"))

        def replay(loaded):
            check_time()
            checked = problem.replay(loaded)
            check_time()
            return checked

        # Finish required diagnostics before completion can be published. There
        # is no success-path finally write that could relabel a completed bundle
        # as rejected solely because a later diagnostic write failed.
        write_json(directory / "loss_trace.json", losses)
        write_json(directory / "snapshot_index.json", event_index)
        check_time()
        try:
            loaded = persist_verified_step(directory / "committed", payload, replay)
        except PersistenceVerificationError as persistence_error:
            cause = persistence_error.__cause__
            seen = set()
            while cause is not None and id(cause) not in seen:
                seen.add(id(cause))
                if isinstance(cause, TimeBudgetExceeded):
                    # The persistence helper already leaves this bundle
                    # incomplete. Restore the stop category for the caller;
                    # genuine persistence/replay failures remain fatal.
                    timeout = TimeBudgetExceeded(str(cause))
                    timeout.persistence_error = str(persistence_error)
                    raise timeout from persistence_error
                cause = cause.__cause__
            raise
        # Only the reloaded bundle may become the next predecessor.
        return loaded
    except Exception as error:
        # Rejection has already happened. Preserve its original exception even
        # when disk/GPU trouble also prevents diagnostic serialization. These
        # callbacks read existing tensors only and start no new numerical solve
        # or field/residual evaluation after a deadline.
        prior_diagnostic = getattr(error, "diagnostic_error", None)
        diagnostic_errors = []

        def best_effort(label, action):
            try:
                action()
            except Exception as diagnostic_error:
                diagnostic_errors.append(f"{label}: {type(diagnostic_error).__name__}: {diagnostic_error}")
                error.diagnostic_error = "; ".join(
                    ([str(prior_diagnostic)] if prior_diagnostic else []) + diagnostic_errors)

        best_effort("terminal snapshot", lambda: snapshot(dict(
            event="terminal_failure", error_type=type(error).__name__, reason=str(error),
            old_state=old, f_solve=current_coefficient,
            note="unaccepted trial; not a continuation source")))
        def failure_loss_trace():
            if not (directory / "loss_trace.json").exists():
                write_json(directory / "loss_trace.json", losses)

        best_effort("loss trace", failure_loss_trace)
        # If normal diagnostics preceded a later persistence failure, retain
        # their original bytes and add the terminal failure in a separate index.
        def failure_snapshot_index():
            filename = ("failure_snapshot_index.json" if (directory / "snapshot_index.json").exists()
                        else "snapshot_index.json")
            write_json(directory / filename, event_index)

        best_effort("snapshot index", failure_snapshot_index)
        best_effort("rejection receipt", lambda: write_json(directory / "rejected.json", dict(
            accepted=False, history_committed=False, state_key=key, arm=arm, reason=str(error),
            error_type=type(error).__name__, updates=work.rprop_updates,
            optimizer_work=optimizer_work(work.rprop_updates, window_updates_before_step),
            objective_precision=current_precision,
            outer_records=getattr(error, "records", []),
            persistence_error=getattr(error, "persistence_error", None),
            diagnostic_error=getattr(error, "diagnostic_error", None))))
        raise


def main(args):
    device = torch.device(args.device)
    authority, source_identity = check_authority(args.authority, args.manifest, device)
    doc, root, nodes, cells, common = load_manifest(args.manifest)
    if args.out.exists():
        raise FileExistsError("a fresh output directory is mandatory; resume is unsupported")
    if shutil.disk_usage(args.out.parent).free < 20 * 1024 ** 3:
        raise RuntimeError("reserve at least 20 GiB for immutable snapshots and bundles")
    args.out.mkdir()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.manual_seed(1)
    torch.use_deterministic_algorithms(True)
    total = Deadline(doc["budget"]["job_wall_seconds"], "this job anti-hang")
    problem = WindowProblem(nodes, cells, common, device)
    authority_root = Path(args.authority).resolve().parent
    reused_stage_a = validate_stage_a_reuse(bound_file(authority["fem_validation"], authority_root),
        bound_file(authority["stage_a_semantic_binding"], authority_root), ROOT, problem)
    receipt = dict(schema="s04_e036_paired_run_v1", started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   host=platform.node(), pid=os.getpid(), command=sys.argv, authority=authority,
                   manifest_sha256=sha256(args.manifest), budget=doc["budget"],
                   cumulative_resource_limit=None,
                   stage_a_reuse=reused_stage_a,
                   **source_identity,
                   cuda_visible_devices=os.environ["CUDA_VISIBLE_DEVICES"],
                   semantics="conditional windows; no continuous c1-to-c83 prediction; no target supervision")
    write_json(args.out / "run_receipt.json", receipt)
    rows = []

    def outcome(row):
        rows.append(row)
        # Preserve completed/failed independent cases even if a global deadline
        # or process interruption prevents the final aggregate file.
        with (args.out / "outcomes.jsonl").open("a") as stream:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    for name, (cycle, substeps) in CASES.items():
        total.check()
        folder = args.out / name
        folder.mkdir()
        try:
            arrays, pre_key, paths, admission = load_case(name, doc, root, len(nodes), len(cells), common)
            total.check()
            common_old = problem.old_state(arrays, pre_key)
            total.check()
            network = torch.load(paths["network"], map_location="cpu", weights_only=True)
            if not isinstance(network, dict) or not all(torch.is_tensor(v) and v.dtype == torch.float32 for v in network.values()):
                raise ValueError("a bare float32 8x400 network state_dict is required")
        except (OSError, ValueError, KeyError) as error:
            write_json(folder / "unavailable.json", dict(reason=str(error), case=name, no_substitution=True))
            outcome(dict(case=name, status="unavailable", reason=str(error)))
            continue
        for arm in ("P1", "P2"):
            window_updates = 0
            old = {key: value.clone() for key, value in common_old.items()}
            field = problem.field(copy.deepcopy(network), LOADS[substeps[0] - 1])
            arm_dir = folder / arm
            arm_dir.mkdir()
            parent = dict(kind="common_FEM_predecessor", state_key=pre_key,
                          predecessor=doc["cases"][name]["predecessor"], admission=doc["cases"][name]["admission"])
            for substep in substeps:
                total.check()
                key = state_key(doc["trajectory"], cycle, substep)
                field.lmbda = torch.tensor([key["displacement"]], device=device, dtype=torch.float32)
                step_dir = arm_dir / f"s{substep}"
                provenance = dict(case=name, initial_network=doc["cases"][name]["network"], parent=parent,
                                  manifest_sha256=sha256(args.manifest),
                                  comparison="common predecessor" if substep == substeps[0] else "own accepted history propagation")
                try:
                    loaded = run_step(problem, field, old, key, arm, step_dir, doc["budget"], total, provenance,
                                      window_updates_before_step=window_updates)
                except Exception as error:
                    outcome(dict(case=name, arm=arm, substep=substep, status="stopped", reason=str(error)))
                    # Persistence failure is never an accepted continuation, even
                    # if in-memory physical checks had passed. No retry here.
                    if isinstance(error, TrialFatigueNotConverged):
                        break
                    if isinstance(error, TimeBudgetExceeded):
                        total.check()  # A per-step timeout may leave independent cases available.
                        break
                    # Version/input/persistence/software failures are common
                    # implementation failures, not another scientific arm.
                    raise
                field = problem.field(loaded["network_state"], key["displacement"])
                expected_work = optimizer_work(loaded["metadata"]["rprop_updates"], window_updates)
                if loaded["metadata"]["optimizer_work"] != expected_work:
                    raise ValueError("verified bundle work does not follow its accepted window")
                window_updates = expected_work["window_updates"]
                old = dict(damage=loaded["fields"]["d"].to(device=device, dtype=torch.float64),
                           history=loaded["history"].to(device=device, dtype=torch.float64),
                           active_driver=loaded["fields"]["active_driver"].to(device=device, dtype=torch.float64))
                parent = dict(kind="own_verified_bundle", state_key=key,
                              path=str((step_dir / "committed").resolve()),
                              bundle_sha256=sha256(step_dir / "committed" / "bundle.pt"))
                outcome(dict(case=name, arm=arm, substep=substep, status="persisted_and_replayed",
                             updates=loaded["metadata"]["rprop_updates"], optimizer_work=expected_work))
                write_json(step_dir / "continuation_source.json", parent)
    write_json(args.out / "outcomes.json", rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    main(parser.parse_args())
