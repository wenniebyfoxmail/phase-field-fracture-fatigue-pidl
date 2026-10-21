"""Opt-in physical-substep fatigue fixed point, with one accepted-state commit.

This module has no network or solver dependency. ``solve_for_coefficient`` may
change a trial field, but committed history tensors are never mutated. A fresh
physical residual callback is mandatory; convergence of f alone is insufficient.
"""
from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import uuid

import torch

from fatigue_history import compute_fatigue_degrad, update_fatigue_history


class TrialFatigueNotConverged(RuntimeError):
    """A physical step was rejected; its old histories remain uncommitted."""

    def __init__(self, message, records):
        super().__init__(message)
        self.records = records


@dataclass(frozen=True)
class TrialFatigueResult:
    state: dict
    history: torch.Tensor
    active_driver: torch.Tensor
    f_solve: torch.Tensor
    f_commit: torch.Tensor
    records: list
    residual_receipt: dict


@dataclass
class PhysicalStepOptimizerBudget:
    """One RPROP cap shared by every coefficient refresh at a physical step."""
    epochs_per_outer: int
    max_total_rprop_epochs: int
    rprop_updates: int = 0

    def next_rprop_epochs(self):
        remaining = self.max_total_rprop_epochs - self.rprop_updates
        if remaining <= 0:
            raise TrialFatigueNotConverged(
                "physical-step RPROP budget exhausted; no history commit", [])
        return min(self.epochs_per_outer, remaining)

    def record_rprop_updates(self, count):
        if count < 0 or count > self.next_rprop_epochs():
            raise ValueError("optimizer returned an invalid RPROP update count")
        self.rprop_updates += count


@contextmanager
def track_optimizer_work(optimizer, budget, receipt, kind, max_eval=None):
    """Count completed steps and closure attempts even if fitting raises.

    PyTorch's strong-Wolfe line search may exceed the nominal ``max_eval``
    during one line search. The closure wrapper enforces the declared cap.
    Passing budget=None preserves the legacy optimizer call unchanged.
    """
    if budget is None:
        yield
        return
    handles = []
    if kind == "RPROP":
        def before_rprop_step(optim, args, kwargs):
            budget.next_rprop_epochs()
        handles.append(optimizer.register_step_pre_hook(before_rprop_step))
        handles.append(optimizer.register_step_post_hook(
            lambda optim, args, kwargs: budget.record_rprop_updates(1)))
    elif kind == "LBFGS":
        def before_step(optim, args, kwargs):
            closure = kwargs.get("closure")
            positional = closure is None
            if positional:
                closure = args[-1]
            if not callable(closure):
                raise ValueError("L-BFGS tracking requires a closure")
            def bounded_closure():
                if receipt.get("lbfgs_closure_calls", 0) >= int(max_eval):
                    raise TrialFatigueNotConverged(
                        "physical-step L-BFGS closure budget exhausted; no history commit", [])
                receipt["lbfgs_closure_calls"] = receipt.get("lbfgs_closure_calls", 0) + 1
                return closure()
            if positional:
                return args[:-1] + (bounded_closure,), kwargs
            return args, dict(kwargs, closure=bounded_closure)
        handles.append(optimizer.register_step_pre_hook(before_step))
    else:
        raise ValueError(f"unknown optimizer tracking kind {kind}")
    try:
        yield
    finally:
        for handle in handles:
            handle.remove()
        if kind == "LBFGS":
            states = list(optimizer.state.values())
            receipt["lbfgs_func_evals"] = sum(int(state.get("func_evals", 0)) for state in states)
            receipt["lbfgs_iterations"] = sum(int(state.get("n_iter", 0)) for state in states)


def _detached_copy(value, name):
    if not torch.is_tensor(value):
        raise TypeError(f"{name} must be a tensor")
    if not torch.isfinite(value).all():
        raise ValueError(f"{name} contains nonfinite values")
    return value.detach().clone()


def trial_fatigue_checkpoint_contract(config, irreversibility_penalty_cfg,
                                     common_problem=None, fatigue_dict=None):
    """Portable numerical policy; callbacks are runtime bindings, never state."""
    numerical_config = {
        key: value for key, value in config.items()
        if key not in {"final_residual_check", "final_residual_check_factory"}
    }
    numerical_config.setdefault("history_mode", "trial")
    fatigue_dict = fatigue_dict or {}
    physical_history_keys = (
        "fatigue_on", "loading_type", "accum_type", "degrad_type", "alpha_T",
        "kappa", "alpha_n", "n_power", "history_storage", "damage_history_storage",
        "history_driver_mode", "history_driver_reduction", "explicit_cycle_substeps",
        "explicit_cycle_step_mode", "explicit_cycle_displacements", "explicit_cycle_factors",
        "R_ratio", "initial_alpha_protocol", "paired_initial_state",
    )
    contract = {"version": 1, "coupling": numerical_config,
                "irreversibility_penalty": irreversibility_penalty_cfg,
                "common_problem": common_problem,
                "fatigue_physics": {key: fatigue_dict[key] for key in physical_history_keys
                                    if key in fatigue_dict}}
    # A strict continuation must never silently lose an unserialisable policy.
    return json.loads(json.dumps(contract, sort_keys=True, allow_nan=False))


def require_fresh_trial_run_directory(trained_model_path):
    """Strict coupling has no continuation path in this first implementation."""
    path = Path(trained_model_path)
    existing = list(path.glob("checkpoint_step_*.pt"))
    existing += list(path.glob("trained_1NN_[0-9]*.pt"))
    receipts = path.parent / "trial_fatigue_acceptance"
    existing += list(receipts.glob("step_*_accepted.json"))
    existing += list(receipts.glob("step_*_rejected.json"))
    existing += list(receipts.glob("step_*_coefficients.npz"))
    if existing:
        raise RuntimeError(
            "strict fatigue coupling does not support resume; use a fresh run "
            f"directory with the approved common initial state (found {existing[0]})")


def verify_initial_network(path, expected_sha256):
    """Bind initial bytes before loading any deserialised model state."""
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 \
            or any(c not in "0123456789abcdef" for c in expected_sha256):
        raise ValueError("strict fatigue coupling requires an explicit lowercase initial_network_sha256")
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected_sha256:
        raise RuntimeError(f"initial network SHA-256 mismatch: actual={actual}, expected={expected_sha256}")
    return actual


def validate_trial_fatigue_config(fatigue_dict, config):
    """Fail before any fitting if the opt-in route cannot be interpreted."""
    if not config.get("enable", False):
        return
    if not (callable(config.get("final_residual_check"))
            or callable(config.get("final_residual_check_factory"))):
        raise ValueError("trial fatigue coupling requires a fresh final_residual_check callback")
    required = ("max_outer", "f_atol", "f_rtol", "epochs_per_outer",
                "max_total_rprop_epochs", "recovery_lbfgs_max_iter",
                "recovery_lbfgs_max_eval")
    for name in required:
        if name not in config or config[name] is None:
            raise ValueError(f"trial fatigue coupling requires explicit {name}")
    for name in ("epochs_per_outer", "max_total_rprop_epochs",
                 "recovery_lbfgs_max_iter", "recovery_lbfgs_max_eval"):
        value = config[name]
        if isinstance(value, bool) or int(value) != value or value < 1:
            raise ValueError(f"trial fatigue {name} must be a positive integer")
    if fatigue_dict.get("history_storage") not in {"q4_gp4", "tri3_gp3"}:
        raise ValueError("trial fatigue coupling requires native GP history storage")
    reduction = fatigue_dict.get("history_driver_reduction", {}) or {}
    native_mode = {"q4_gp4": "native_q4_gp4", "tri3_gp3": "native_tri3_gp3"}[
        fatigue_dict["history_storage"]]
    if not reduction.get("enable", False) or reduction.get("mode") != native_mode:
        raise ValueError("trial fatigue coupling requires the matching native GP driver reduction")
    if config.get("history_mode", "trial") != "trial":
        raise ValueError("strict fatigue coupling currently accepts trial history mode only")
    if fatigue_dict.get("damage_history_storage") != "previous_accepted_nodal":
        raise ValueError("trial fatigue coupling requires previous_accepted_nodal damage history")
    if not fatigue_dict.get("fatigue_on", False):
        raise ValueError("trial fatigue coupling requires fatigue_on")
    if fatigue_dict.get("loading_type", "cyclic") != "cyclic":
        raise ValueError("trial fatigue coupling requires explicit cyclic loading")
    if not fatigue_dict.get("explicit_cycle_substeps"):
        raise ValueError("trial fatigue coupling requires explicit physical substeps")
    if fatigue_dict.get("history_driver_mode", "current_active") != "current_active":
        raise ValueError("trial fatigue coupling requires current_active history")
    if fatigue_dict.get("accum_type", "carrara") != "carrara":
        raise ValueError("trial fatigue coupling currently implements Carrara accumulation")
    # These paths alter fields, history, the objective, or geometry during the
    # step. They need their own prospective contract, not silent composition.
    unsupported = (
        "fem_oracle", "initial_state_oracle", "hist_alpha_oracle",
        "history_increment_oracle", "alpha_bar_state_oracle", "f_fatigue_oracle",
        "g_stiffness_oracle", "alpha_feedback_oracle", "lagged_stiffness",
        "mirror_alpha_y", "void_notch_mask", "spatial_alpha_T", "psi_hack",
        "tip_weight_cfg", "adaptive_lambda_hist", "staged_alpha", "local_patch_training",
        "symmetry_soft", "side_traction_soft",
    )
    for name in unsupported:
        if (fatigue_dict.get(name) or {}).get("enable", False):
            raise ValueError(f"trial fatigue coupling does not support {name}")
    max_outer = config["max_outer"]
    if isinstance(max_outer, bool) or int(max_outer) != max_outer or max_outer < 1:
        raise ValueError("trial fatigue max_outer must be a positive integer")
    atol, rtol = float(config["f_atol"]), float(config["f_rtol"])
    if not all(math.isfinite(v) and v >= 0 for v in (atol, rtol)) or atol + rtol <= 0:
        raise ValueError("trial fatigue f tolerances must be finite, nonnegative and not both zero")
    relax = float(config.get("relaxation", 1.0))
    if not math.isfinite(relax) or not 0 < relax <= 1:
        raise ValueError("trial fatigue relaxation must be in (0,1]")


def solve_trial_fatigue_step(*, old_history, old_active_driver, old_damage,
                            initial_f, fatigue_dict, config,
                            solve_for_coefficient, evaluate_state,
                            final_residual_check, step):
    """Return one accepted proposal, or raise without modifying old histories.

    ``evaluate_state()`` returns detached/fresh u, v, d and active_driver tensors.
    ``final_residual_check(context)`` must reassemble the physical residual at
    exactly that state using frozen old damage/history and trial fatigue. Its
    receipt requires accepted (bool), fresh_current_state=True, state_token
    echoed from context, and a metrics dictionary. No loss-based fallback exists.
    """
    if not callable(final_residual_check):
        raise ValueError("trial fatigue coupling requires a fresh final_residual_check callback")
    validation_config = dict(config, final_residual_check=final_residual_check)
    validate_trial_fatigue_config(fatigue_dict, validation_config)
    A_old = _detached_copy(old_history, "old_history")
    r_old = _detached_copy(old_active_driver, "old_active_driver")
    d_old = _detached_copy(old_damage, "old_damage")
    f_next = _detached_copy(initial_f, "initial_f")
    if A_old.shape != r_old.shape or f_next.shape != A_old.shape:
        raise ValueError("old GP history, active driver and fatigue coefficient shapes differ")
    atol, rtol = float(config["f_atol"]), float(config["f_rtol"])
    relaxation = float(config.get("relaxation", 1.0))
    records = []
    for outer in range(1, int(config["max_outer"]) + 1):
        f_solve = f_next.detach().clone()
        try:
            solve_for_coefficient(f_solve.clone(), outer)
        except TrialFatigueNotConverged as error:
            error.records = records + error.records
            raise
        state = {name: _detached_copy(value, name) for name, value in evaluate_state().items()}
        for name in ("u", "v", "d", "active_driver", "displacement"):
            if name not in state:
                raise ValueError(f"fresh state missing {name}")
        active = state["active_driver"]
        if active.shape != A_old.shape or state["d"].shape != d_old.shape:
            raise ValueError("fresh state shape does not match committed history/damage")
        # Always rebuild from the same A_old and r_old. Never from a trial A.
        A_trial = update_fatigue_history(A_old, active, r_old, fatigue_dict).detach()
        f_trial = compute_fatigue_degrad(A_trial, fatigue_dict).detach()
        if not torch.isfinite(A_trial).all() or not torch.isfinite(f_trial).all():
            raise TrialFatigueNotConverged("nonfinite fatigue trial; no history commit", records)
        f_delta = (f_trial - f_solve).abs()
        f_scale = atol + rtol * torch.maximum(f_trial.abs(), f_solve.abs())
        f_converged = bool(torch.all(f_delta <= f_scale).item())
        token = uuid.uuid4().hex
        context = {name: value.clone() for name, value in state.items()}
        context.update(step=int(step), outer=outer, state_token=token,
                       old_damage=d_old.clone(), old_history=A_old.clone(),
                       old_active_driver=r_old.clone(), trial_history=A_trial.clone(),
                       f_solve=f_solve.clone(), f_commit=f_trial.clone())
        receipt = final_residual_check(context)
        if not isinstance(receipt, dict) or type(receipt.get("accepted")) is not bool:
            raise ValueError("fresh residual callback must return an explicit accepted boolean in a receipt")
        if receipt.get("fresh_current_state") is not True or receipt.get("state_token") != token:
            raise ValueError("residual receipt is not bound to the fresh current trial state")
        if not isinstance(receipt.get("metrics"), dict) or not receipt["metrics"]:
            raise ValueError("fresh residual receipt must contain physical metrics")
        record = {"step": int(step), "outer": outer,
                  "f_max_abs_change": float(f_delta.max().item()),
                  "f_converged": f_converged, "residual_accepted": receipt["accepted"],
                  "residual": receipt}
        records.append(record)
        if f_converged and receipt["accepted"]:
            return TrialFatigueResult(state, A_trial, active, f_solve, f_trial,
                                      records, receipt)
        f_next = ((1.0 - relaxation) * f_solve + relaxation * f_trial).detach()
    raise TrialFatigueNotConverged(
        f"step {step} failed trial-fatigue/fresh-residual acceptance after {len(records)} outer iterations; no history commit",
        records,
    )
