"""Preparation only: one transactional, target-free C0 constraint release.

No CLI, launch, automatic continuation, history commit, or target-file loader.
The owner must bind a producer attempt before calling ``attempt_release``.
Importing this file performs no model/physics work. See DESIGN.md for semantics.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Callable, Any

import torch


@dataclass(frozen=True)
class ReleasePlan:
    damage_trust_radius: float = .02
    node_armijo: float = 1e-4
    node_backtracks: int = 25
    energy_fraction: float = .1
    blocked_work_fraction: float = .1
    lbfgs_history: int = 100
    closures_per_step: int = 25
    stagnant_steps: int = 20
    proxy_relative_change: float = 1e-10


PLAN = ReleasePlan()


class ReleaseStop(RuntimeError):
    """Finite algorithm did not produce a releasable physical candidate."""


def _number(value):
    value = float(value.detach()) if torch.is_tensor(value) else float(value)
    if not math.isfinite(value):
        raise ReleaseStop("nonfinite_value")
    return value


def _roundoff_guard(*values):
    scale = max(abs(_number(x)) for x in values)
    return 64 * torch.finfo(torch.float64).eps * max(scale, torch.finfo(torch.float64).tiny)


def _fields(engine):
    with torch.no_grad():
        fields, raw = engine.field.values()
        return {k: fields[k].detach().clone() for k in ("u", "v", "d")}, raw.detach().clone()


def _energy(engine, fields, frozen_f, *, damage_force=False):
    # Reuse the exact native Q4 energy. Do not differentiate trial f(y).
    from compute_energy import compute_energy
    p = engine.problem
    with torch.enable_grad():
        d = fields["d"].detach().clone().requires_grad_(damage_force)
        value = sum(compute_energy(
            p.native_x, fields["u"].detach(), fields["v"].detach(), d,
            engine.old["damage"], p.mat, p.model, p.native_area, p.cells,
            f_fatigue=frozen_f.detach(), irreversibility_penalty_cfg=p.penalty))
        force = torch.autograd.grad(value, d)[0].detach() if damage_force else None
    if force is not None and not bool(torch.isfinite(force).all()):
        raise ReleaseStop("nonfinite_node_force")
    return _number(value), force


def _verify_actual(engine, fields, raw):
    from mechanism_metrics import direct_box_projection
    lower = engine.old["damage"]
    if not torch.equal(fields["d"], direct_box_projection(raw, lower)):
        raise ValueError("actual_output_is_not_original_C0_map")
    if any(v.dtype != torch.float64 or not bool(torch.isfinite(v).all()) for v in (*fields.values(), raw)):
        raise ReleaseStop("nonfinite_or_non_float64_field")
    if bool(((fields["d"] < lower) | (fields["d"] > 1)).any()):
        raise ValueError("actual_C0_field_not_exactly_feasible")
    fixed = engine.problem.common["fixed_damage_nodes_zero_based"]
    if not bool((fields["d"][fixed] == 1).all()):
        raise ValueError("hard_damage_boundary_changed")
    y = engine.problem.native_x[:, 1]
    top, bottom = y == y.max(), y == y.min()
    bc_error = max(_number(fields["u"][top | bottom].abs().max()),
                   _number(fields["v"][bottom].abs().max()),
                   _number((fields["v"][top] - engine.key["displacement"]).abs().max()))
    if bc_error > engine.problem.common["acceptance_config"]["bc_tol"]:
        raise ValueError("displacement_boundary_changed")
    engine.verify_old()
    return bc_error


def _proposal(engine, initial, raw, frozen_f, mass, plan):
    """A mass-metric projected damage step; displacement is held fixed."""
    from mechanism_metrics import direct_box_projection
    initial_energy, force = _energy(engine, initial, frozen_f, damage_force=True)
    lower, d0 = engine.old["damage"], initial["d"]
    free = lower < 1
    free[engine.problem.common["fixed_damage_nodes_zero_based"]] = False
    blocked = free & (((raw < lower) & (force < 0)) | ((raw > 1) & (force > 0)))
    if not bool(blocked.any()):
        raise ReleaseStop("no_blocked_feasible_direction_at_saved_f")
    direction = torch.where(free, -force / mass, torch.zeros_like(force))
    # Normal reactions at a bound must not set a tiny trust-step scale for the
    # remaining feasible directions. They project to zero for every step size.
    outward = ((d0 == lower) & (direction < 0)) | ((d0 == 1) & (direction > 0))
    direction = torch.where(outward, torch.zeros_like(direction), direction)
    magnitude = _number(direction.abs().max())
    if magnitude == 0:
        raise ReleaseStop("zero_mass_metric_direction")
    step = plan.damage_trust_radius / magnitude
    for backtrack in range(plan.node_backtracks):
        engine.check()
        trial = dict(initial)
        trial["d"] = direct_box_projection(d0 + step * direction, lower)
        trial["d"] = torch.where(free, trial["d"], d0)
        delta = trial["d"] - d0
        slope = _number((force * delta).sum())
        norm2 = _number((mass * delta.square()).sum())
        if norm2 == 0 or slope >= 0:
            raise ReleaseStop("node_step_has_no_resolved_feasible_descent")
        # Projection inequality is an implementation identity, not convergence.
        if slope + norm2 / step > _roundoff_guard(slope, norm2 / step):
            raise ValueError("mass_metric_projection_identity_failed")
        trial_energy, _ = _energy(engine, trial, frozen_f)
        drop = initial_energy - trial_energy
        if (trial_energy <= initial_energy + plan.node_armijo * slope
                and drop > _roundoff_guard(initial_energy, trial_energy)):
            blocked_work = _number((-force[blocked] * delta[blocked]).sum())
            if blocked_work <= _roundoff_guard(slope):
                raise ReleaseStop("node_release_work_below_resolved_scale")
            lifted_raw = raw.clone()
            moving = free & (delta != 0)
            lifted_raw[moving] = trial["d"][moving]
            if not torch.equal(direct_box_projection(lifted_raw, lower), trial["d"]):
                raise ValueError("raw_lift_is_not_a_preimage_of_node_target")
            return dict(fields=trial, raw_preimage=lifted_raw, force_d=force,
                        blocked=blocked, initial_energy=initial_energy,
                        node_energy=trial_energy, node_drop=drop,
                        node_blocked_work=blocked_work, node_slope=slope,
                        step=step, backtracks=backtrack)
        step *= .5
    raise ReleaseStop("node_armijo_failed_once_no_retry")


def _proxy(engine, target, mass):
    """True derivative of a proxy; the raw term is NOT a physical gradient."""
    fields, raw = engine.field.values()
    actual = sum((mass * ((fields[k] - target["fields"][k]) / scale).square()).sum()
                 for k, scale in (("u", .12), ("v", .12), ("d", 1.)))
    lifted = (mass * (raw - target["raw_preimage"]).square()).sum()
    return .5 * (actual + lifted), dict(actual_field_squared=_number(actual),
                                     raw_preimage_squared=_number(lifted))


def attempt_release(engine, *, emit: Callable[[str, dict], None],
                    publish: Callable[[Any, dict, dict], dict]) -> dict:
    """One release transaction, called only from a newly authorized producer job.

    ``engine`` is the loaded terminal C0 EndpointEngine, float64, CUDA. It must
    be sourced from its complete endpoint, not a target-fit/witness endpoint.
    ``emit`` durably records scalar events / proposal arrays in a fresh output.
    ``publish(engine, fresh, extra)`` must call the existing publish_snapshot
    and return its verified completion receipt before weights can be retained.
    Exceptions and unsuccessful release restore every network parameter/buffer.
    Proxy work is recorded separately; it is never called physical LBFGS work.
    """
    from run_mechanism_matrix import bounded_lbfgs_step, ClosureLimit, exact_payload, cpu
    if (engine.arm != "C0" or engine.mapping != "nodal_clamp" or engine.weight_l2 != 0
            or engine.dtype != torch.float64 or engine.problem.native_x.device.type != "cuda"):
        raise ValueError("requires_original_C0_float64_on_authorized_GPU")
    parameters = list(engine.field.net.parameters())
    if sum(p.numel() for p in parameters) != 1125211 or not all(p.requires_grad for p in parameters):
        raise ValueError("complete_unchanged_network_must_be_trainable")
    if engine.work["history_commits"] != 0:
        raise ValueError("release_endpoint_must_have_zero_history_commits")
    engine.check()
    engine.verify_old()
    frozen_f = engine.coefficient.detach().clone()
    if frozen_f.requires_grad or not bool(torch.isfinite(frozen_f).all()):
        raise ValueError("invalid_fixed_f")
    saved = {k: v.detach().clone() for k, v in engine.field.net.state_dict().items()}
    proxy_work = dict(lbfgs_steps=0, lbfgs_closures=0)
    accepted = False
    result = None
    try:
        initial, raw0 = _fields(engine)
        _verify_actual(engine, initial, raw0)
        p = engine.problem
        mass = torch.zeros_like(initial["d"])
        mass.index_add_(0, p.cells.reshape(-1),
                        torch.einsum("eg,gn->en", p.native_weights, p.native_shape).reshape(-1))
        if not bool(torch.isfinite(mass).all()) or not bool((mass > 0).all()):
            raise ValueError("invalid_native_Q4_lumped_mass")
        mass = mass / mass.sum()
        proposal = _proposal(engine, initial, raw0, frozen_f, mass, PLAN)
        emit("node_proposal", dict(plan=asdict(PLAN), proposal=cpu(proposal),
             initial_fields=cpu(initial), initial_raw=cpu(raw0), fixed_f=cpu(frozen_f),
             future_FEM_target_used=False, history_commits=0))
        optimizer = torch.optim.LBFGS(parameters, lr=1., max_iter=1,
            max_eval=PLAN.closures_per_step, tolerance_grad=0., tolerance_change=0.,
            history_size=PLAN.lbfgs_history, line_search_fn="strong_wolfe")
        changes, steps = [], 0
        while True:
            engine.check()
            before = _number(_proxy(engine, proposal, mass)[0])
            def closure():
                optimizer.zero_grad(set_to_none=True)
                value, _ = _proxy(engine, proposal, mass)
                _number(value)
                value.backward()
                if any(q.grad is not None and not bool(torch.isfinite(q.grad).all()) for q in parameters):
                    raise ReleaseStop("nonfinite_proxy_gradient")
                return value
            calls = bounded_lbfgs_step(optimizer, parameters, closure, proxy_work,
                                       engine.check, PLAN.closures_per_step)
            steps += 1
            after, proxy_parts = _proxy(engine, proposal, mass)
            after = _number(after)
            if after > before + _roundoff_guard(before, after):
                raise ReleaseStop("proxy_line_search_increased_objective")
            changes.append(abs(after - before) / max(abs(before), torch.finfo(torch.float64).tiny))
            fields, raw = _fields(engine)
            bc_error = _verify_actual(engine, fields, raw)
            energy, _ = _energy(engine, fields, frozen_f)
            drop = proposal["initial_energy"] - energy
            b = proposal["blocked"]
            actual_work = _number((-proposal["force_d"][b] * (fields["d"][b] - initial["d"][b])).sum())
            receipt = dict(proxy_step=steps, closures=calls, proxy_work=proxy_work.copy(), proxy_objective=after,
                proxy_parts=proxy_parts, fixed_f_energy=energy, fixed_f_energy_drop=drop,
                node_energy_drop=proposal["node_drop"], blocked_work_actual=actual_work,
                blocked_work_node=proposal["node_blocked_work"], bc_error=bc_error,
                actual_blocked_nodes_moved=int((fields["d"][b] != initial["d"][b]).sum()),
                max_u_drift=_number((fields["u"] - initial["u"]).abs().max()),
                max_v_drift=_number((fields["v"] - initial["v"]).abs().max()))
            emit("proxy_step_actual_physical_readback", receipt)
            passed = (drop >= PLAN.energy_fraction * proposal["node_drop"]
                      and drop > _roundoff_guard(energy, proposal["initial_energy"])
                      and actual_work >= PLAN.blocked_work_fraction * proposal["node_blocked_work"]
                      and receipt["actual_blocked_nodes_moved"] > 0)
            if passed:
                fresh = engine.readout()  # Rebuild trial-f; it does not refresh f_solve.
                exact_payload(cpu(fields), cpu({k: fresh["fields"][k] for k in ("u", "v", "d")}))
                exact_payload(cpu(raw), cpu(fresh["raw_damage"]))
                if not torch.equal(engine.coefficient, frozen_f):
                    raise ValueError("coefficient_changed_inside_release")
                extra = dict(method="nodal_damage_raw_preimage_release_v1",
                    release_receipt=receipt, plan=asdict(PLAN), proxy_work=proxy_work.copy(),
                    future_FEM_target_used=False, teacher_initialized=False,
                    interpretation="physical_node_target_retraction; release acceptance is not physical convergence")
                completion = publish(engine, fresh, extra)
                if not (completion.get("readback_verified") is True
                        and completion.get("fields_reproduced_exactly") is True
                        and completion.get("history_commit_count") == 0):
                    raise ValueError("release_persistence_not_verified")
                engine.verify_old()
                if not torch.equal(engine.coefficient, frozen_f):
                    raise ValueError("coefficient_changed_during_publication")
                result = dict(status="release_accepted", physical_accepted=fresh["physical_accepted"],
                              C=fresh["C"], release=receipt, completion=completion,
                              proxy_work=proxy_work.copy())
                accepted = True
                break
            if len(changes) >= PLAN.stagnant_steps and max(changes[-PLAN.stagnant_steps:]) <= PLAN.proxy_relative_change:
                raise ReleaseStop("proxy_stagnation_without_physical_release")
    except (ReleaseStop, ClosureLimit) as error:
        result = dict(status="release_failed_restored_anchor", reason=str(error), physical_accepted=False,
                      proxy_work=proxy_work.copy())
        emit("release_failure", result)
    finally:
        if not accepted:
            engine.field.net.load_state_dict(saved, strict=True)
            exact_payload(cpu(saved), cpu(engine.field.net.state_dict()))
        engine.coefficient = frozen_f.clone()
        engine.verify_old()
        for parameter in parameters:
            parameter.grad = None
    return result
