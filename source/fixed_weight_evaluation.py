"""Evaluation primitives for fixed-weight numerical-reference surrogates.

No training, solver, archive discovery, or model imports occur here. Metrics
compare declared fields on a shared native Q4 support. Physics diagnostics are
opt-in for one precisely named producer convention; they are not qualification
of a numerical reference or validation against physical observations.
"""
from __future__ import annotations

from dataclasses import replace
import math
from typing import Mapping, Sequence

import torch

from s09_fem_physics import equilibrium, trial_fatigue
from s09_q4_quadrature import q4_gradient, q4_interpolate, q4_shape_data
from s09_stage0a_transition import carrara_f
from fixed_weight_contract import State, TransitionRequest


PHYSICS_SEMANTICS = "native_q4_amor_at1_carrara_current_H_post_commit_v1"
CHANNELS = ("u_x", "u_y", "d", "d_lower", "H", "alpha_bar", "q_prev")


def _finite(value, name):
    if not torch.is_tensor(value) or not torch.isfinite(value).all():
        raise ValueError(f"{name} must be a finite tensor")


def weighted_errors(prediction, reference, weights):
    """Scalar-channel MAE, RMSE and relative L2 on explicitly weighted support.

    Relative L2 is undefined (None) for an exactly zero reference, including
    an exact zero prediction; absolute metrics remain meaningful in that case.
    """
    for value, name in ((prediction, "prediction"), (reference, "reference"),
                        (weights, "weights")):
        _finite(value, name)
    if prediction.shape != reference.shape or weights.shape != reference.shape:
        raise ValueError("prediction, reference and weights must have equal shapes")
    if torch.any(weights < 0) or not bool(weights.sum() > 0):
        raise ValueError("weights must be nonnegative with positive total")
    error = prediction - reference
    total = weights.sum()
    square = (weights * error.square()).sum()
    reference_square = (weights * reference.square()).sum()
    relative = (float(torch.sqrt(square / reference_square))
                if bool(reference_square > 0) else None)
    return {"mae": float((weights * error.abs()).sum() / total),
            "rmse": float(torch.sqrt(square / total)), "relative_l2": relative}


def _key_identity(key):
    return tuple(getattr(key, name) for name in
                 ("trajectory_id", "condition_id", "reference_id", "mesh_id"))


def _aligned(prediction, reference, mesh):
    names = ("trajectory_id", "condition_id", "reference_id", "mesh_id",
             "cycle", "substep", "ordinal", "branch", "timing", "load")
    if any(getattr(prediction.key, n) != getattr(reference.key, n) for n in names):
        raise ValueError("prediction/reference physical state identities differ")
    if prediction.key.mesh_id != mesh.mesh_id:
        raise ValueError("state and metric mesh identities differ")


def _support_weights(mesh):
    shape, dshape, det = q4_shape_data(mesh.xy, mesh.conn)
    local = torch.einsum("gn,eg->en", shape, det)
    nodes = torch.zeros(len(mesh.xy), dtype=det.dtype, device=det.device)
    nodes.index_add_(0, mesh.conn.reshape(-1), local.reshape(-1))
    return nodes, det, shape, dshape


def field_errors(prediction, reference, mesh):
    """Area-weighted metrics per physical channel; never pool unequal units."""
    _aligned(prediction, reference, mesh)
    nodes, gp, _, _ = _support_weights(mesh)
    if prediction.u.shape != (len(nodes), 2) or reference.u.shape != prediction.u.shape:
        raise ValueError("displacements must have shape [node,2]")
    if prediction.history.shape != (*gp.shape, 3) or reference.history.shape != prediction.history.shape:
        raise ValueError("history must have shape [element,4GP,H|alpha_bar|q_prev]")
    result = {}
    for i, name in enumerate(("u_x", "u_y")):
        result[name] = weighted_errors(prediction.u[:, i], reference.u[:, i], nodes)
    for name in ("d", "d_lower"):
        result[name] = weighted_errors(getattr(prediction, name), getattr(reference, name), nodes)
    for i, name in enumerate(("H", "alpha_bar", "q_prev")):
        result[name] = weighted_errors(prediction.history[..., i], reference.history[..., i], gp)
    return result


def _violation(values):
    positive = values.clamp_min(0)
    return {"max": float(positive.max()), "mean": float(positive.mean()),
            "fraction": float((positive > 0).to(torch.float64).mean())}


def admissibility(state, source=None):
    """Raw bounds and no-healing diagnostics, without hiding violations by clipping."""
    for name in ("u", "d", "d_lower", "history"):
        _finite(getattr(state, name), name)
    result = {"damage_below_zero": _violation(-state.d),
              "damage_above_one": _violation(state.d - 1),
              "damage_below_committed_lower": _violation(state.d_lower - state.d),
              "lower_below_zero": _violation(-state.d_lower),
              "lower_above_one": _violation(state.d_lower - 1),
              "negative_history": _violation(-state.history)}
    if source is None:
        result["transition"] = {"status": "skipped", "reason": "no accepted source state"}
    else:
        _transition(source, state.key)
        result["transition"] = {
            "status": "computed",
            "damage_healing": _violation(source.d - state.d),
            "damage_below_source_lower": _violation(source.d_lower - state.d),
            "lower_history_decrease": _violation(source.d_lower - state.d_lower),
            "fatigue_history_decrease": _violation(source.history[..., 1] - state.history[..., 1]),
        }
    return result


def raw_projected_diagnostics(raw, projected, source=None):
    return {"raw": admissibility(raw, source),
            "projected": admissibility(projected, source),
            "interpretation": "Projection enforces bounds only; it does not establish accuracy or equilibrium."}


def _transition(source, target_key):
    # Validate identity/timing/physical ordering and the incoming target branch,
    # but not field admissibility: raw predictions must remain scoreable.
    TransitionRequest(target_key, target_key.load - source.key.load).validate(source.key)


def _tensile_lift(mesh, load):
    y = mesh.xy[:, 1]
    height = y.max() - y.min()
    if not bool(height > 0):
        raise ValueError("tensile boundary requires positive specimen height")
    t = (y - y.min()) / height
    return torch.stack((torch.zeros_like(t), t * load), -1)


def _free_dofs(mesh):
    y = mesh.xy[:, 1]
    fixed = (y == y.min()) | (y == y.max())
    return (~fixed)[:, None].expand(-1, 2)


def _check_tensile_boundary(state, mesh):
    if state.key.mesh_id != mesh.mesh_id:
        raise ValueError("state and baseline mesh identities differ")
    fixed = ~_free_dofs(mesh)
    expected = _tensile_lift(mesh, state.key.load)
    precision = torch.finfo(state.u.dtype)
    tolerance = 8 * precision.eps * max(abs(state.key.load), precision.tiny)
    if not bool((torch.abs(state.u[fixed] - expected[fixed]) <= tolerance).all()):
        raise ValueError("source does not satisfy clamped top/bottom scalar tensile boundary")


def _with_tensile_boundary(u, mesh, load):
    # An admitted source may contain a few ulps of boundary roundoff. Removing
    # the load by subtraction does not remove that error, so write the prescribed
    # rows exactly at every step while leaving every free displacement untouched.
    return torch.where(_free_dofs(mesh), u, _tensile_lift(mesh, load))


def persistence(source, target_key, mesh):
    """Persist internal fields while adding the prescribed tensile load lift.

    This is kinematically admissible, not a mechanical equilibrium solve. The
    unchanged driver/energy fields can be inconsistent under the changed load.
    """
    _transition(source, target_key)
    _check_tensile_boundary(source, mesh)
    u = source.u + _tensile_lift(mesh, target_key.load - source.key.load)
    u = _with_tensile_boundary(u, mesh, target_key.load)
    # A recovered initial is a source-only type. The target has ordinary
    # post-history timing even when persistence starts from recovery.
    return State(key=target_key, u=u, d=source.d.clone(),
                 d_lower=source.d_lower.clone(), history=source.history.clone())


def secant(previous, source, target_key, mesh):
    """Raw load-secant extrapolation within one nonzero signed loading branch.

    Fixed displacement rows are reimposed exactly. Damage/history are not
    clipped and no equilibrium correction is applied; score violations beside
    field errors. Across reversal/zero increment this baseline is undefined.
    """
    _transition(previous, source.key)
    _transition(source, target_key)
    _check_tensile_boundary(previous, mesh)
    _check_tensile_boundary(source, mesh)
    old_delta = source.key.load - previous.key.load
    new_delta = target_key.load - source.key.load
    if old_delta == 0 or new_delta == 0 or old_delta * new_delta <= 0:
        raise ValueError("secant requires nonzero increments of the same sign")
    # branch labels describe the interval arriving at each state. The previous
    # state's incoming branch can be initial/unload before two loading steps.
    if source.key.branch != target_key.branch:
        raise ValueError("secant baseline is undefined across a load-branch change")
    ratio = new_delta / old_delta
    u = source.u + ratio * (source.u - previous.u)
    u = _with_tensile_boundary(u, mesh, target_key.load)
    d = source.d + ratio * (source.d - previous.d)
    history = source.history + ratio * (source.history - previous.history)
    return replace(source, key=target_key, u=u, d=d,
                   d_lower=torch.maximum(source.d_lower, d), history=history)


def _mean_channels(reports):
    result = {}
    for channel in CHANNELS:
        result[channel] = {}
        for metric in ("mae", "rmse", "relative_l2"):
            values = [r[channel][metric] for r in reports]
            # A zero-reference frame must not silently disappear from a relative average.
            result[channel][metric] = (None if any(v is None for v in values)
                                       else sum(values) / len(values))
    return result


def rollout_errors(predicted: Sequence, reference: Sequence, mesh):
    """Score every provided continuation horizon, with one trajectory summary.

    Caller supplies the complete declared evaluation continuation; truncation is
    rejected when prediction and reference lengths differ. No node/frame random
    splitting or teacher-forcing is performed by this evaluator.
    """
    if not reference or len(predicted) != len(reference):
        raise ValueError("need equal nonempty complete prediction/reference continuations")
    identity = _key_identity(reference[0].key)
    rows = []
    for i, (pred, ref) in enumerate(zip(predicted, reference)):
        if _key_identity(ref.key) != identity:
            raise ValueError("a rollout may contain only one physical trajectory")
        if i:
            _transition(reference[i - 1], ref.key)
        metrics = field_errors(pred, ref, mesh)
        rows.append({"horizon": i + 1, "ordinal": ref.key.ordinal,
                     "cycle": ref.key.cycle, "substep": ref.key.substep,
                     "branch": ref.key.branch, "errors": metrics})
    return {"trajectory_id": identity[0], "condition_id": identity[1],
            "reference_id": identity[2], "mesh_id": identity[3],
            "horizons": rows, "trajectory_mean": _mean_channels([r["errors"] for r in rows])}


def aggregate_trajectories(reports: Sequence[Mapping]):
    """Equal-weight macro means by physical trajectory, never by node or frame."""
    if not reports:
        raise ValueError("no trajectory reports")
    ids = [r["trajectory_id"] for r in reports]
    if len(set(ids)) != len(ids):
        raise ValueError("one report per complete physical trajectory is required")
    horizons = sorted({h["horizon"] for r in reports for h in r["horizons"]})
    by_horizon = []
    for h in horizons:
        rows = [row["errors"] for r in reports for row in r["horizons"] if row["horizon"] == h]
        by_horizon.append({"horizon": h, "n_trajectories": len(rows),
                           "errors": _mean_channels(rows)})
    return {"n_trajectories": len(reports), "weighting": "equal_per_physical_trajectory",
            "macro": _mean_channels([r["trajectory_mean"] for r in reports]),
            "by_horizon": by_horizon}


def evaluate_continuation(predictor, states, mesh, material, origin_index=0,
                          physics_semantics=None):
    """Evaluate one declared continuation without loading data or training.

    Autonomous calls receive only the origin fields and future load/state keys.
    Teacher forcing is reported separately and receives each accepted reference
    source. The caller admits the complete reference trajectory and owns its
    numerical qualification and dataset split; this function verifies its local
    state/transition contract, not qualification evidence. Results from an
    untrained model remain implementation checks only.
    """
    if len(states) < 2:
        raise ValueError("evaluation needs at least two accepted reference states")
    if type(origin_index) is not int or not 0 <= origin_index < len(states) - 1:
        raise ValueError("origin_index must leave at least one future state")
    for index, state in enumerate(states):
        state.validate(mesh, material)
        if index:
            old = states[index - 1]
            _transition(old, state.key)
            if bool((state.d < old.d).any()) or bool((state.history[..., 1] < old.history[..., 1]).any()):
                raise ValueError("accepted reference damage/fatigue history must not decrease")
    origin = states[origin_index]
    references = states[origin_index + 1:]
    # Deliberately construct from keys/loads alone, before any scoring. Target
    # fields do not enter the autonomous predictor signature.
    requests = [TransitionRequest(target.key, target.key.load - source.key.load)
                for source, target in zip(states[origin_index:-1], references)]
    autonomous = list(predictor.rollout(origin, requests, material))
    if len(autonomous) != len(references):
        raise ValueError("predictor returned an incomplete continuation")
    teacher_forced = [predictor.predict(source, request, material)
                      for source, request in zip(states[origin_index:-1], requests)]
    autonomous_report = rollout_errors([p.state for p in autonomous], references, mesh)
    autonomous_report["mode"] = "autonomous_predicted_state_feedback"
    forced_report = rollout_errors([p.state for p in teacher_forced], references, mesh)
    forced_report["mode"] = "teacher_forced_accepted_reference_source_each_step"
    autonomous_report["diagnostics"] = []
    forced_report["diagnostics"] = []
    scopes = []
    current = origin
    persistent = origin
    persistence_states = []
    for h, (prediction, forced, request) in enumerate(zip(autonomous, teacher_forced, requests)):
        autonomous_report["diagnostics"].append({
            "horizon": h + 1,
            "admissibility": raw_projected_diagnostics(prediction.raw_state, prediction.state, current),
            "physics": physics_diagnostics(prediction.state, current, mesh, material, semantics=physics_semantics),
        })
        forced_source = states[origin_index + h]
        forced_report["diagnostics"].append({
            "horizon": h + 1,
            "admissibility": raw_projected_diagnostics(forced.raw_state, forced.state, forced_source),
            "physics": physics_diagnostics(forced.state, forced_source, mesh, material, semantics=physics_semantics),
        })
        if callable(getattr(predictor, "condition_scope", None)):
            scopes.append({"horizon": h + 1, **predictor.condition_scope(current, request, material)})
        current = prediction.state
        persistent = persistence(persistent, request.target, mesh)
        persistence_states.append(persistent)
    persistence_report = rollout_errors(persistence_states, references, mesh)
    persistence_report["mode"] = "autonomous_kinematic_persistence"
    # A secant needs a second state available BEFORE the forecast origin. Never
    # borrow future reference fields to manufacture a missing baseline history.
    secant_report = {"status": "skipped", "reason": "no accepted state before forecast origin", "horizons": []}
    if origin_index > 0:
        previous, current = states[origin_index - 1], origin
        secant_report = {"status": "computed", "mode": "autonomous_raw_load_secant", "horizons": []}
        for h, (request, reference) in enumerate(zip(requests, references)):
            try:
                candidate = secant(previous, current, request.target, mesh)
            except ValueError as exc:
                secant_report.update(status="partial" if h else "skipped", reason=str(exc), stopped_before_horizon=h + 1)
                break
            secant_report["horizons"].append({"horizon": h + 1, "errors": field_errors(candidate, reference, mesh),
                                             "admissibility": admissibility(candidate, current)})
            previous, current = current, candidate
    return {"trajectory_id": origin.key.trajectory_id, "origin_ordinal": origin.key.ordinal,
            "n_horizons": len(references), "autonomous": autonomous_report,
            "teacher_forced": forced_report, "persistence": persistence_report,
            "secant": secant_report, "condition_scope": scopes or {"status": "unavailable"},
            "interpretation": "Reference-imitation evaluation; one-step fit does not establish autonomous forecast accuracy."}


def physics_diagnostics(state, source, mesh, material, *, semantics=None):
    """Native Q4 plane-strain AMOR/AT1/Carrara numerical consistency only.

    H is CURRENT undegraded tensile energy, not its historical maximum. The
    accepted post-commit source supplies alpha_bar and q_prev. Boundary is zero
    horizontal and prescribed vertical displacement on both top/bottom edges;
    other boundaries are traction-free, with no body forces. Phase KKT is not
    inferred because penalty coefficients and active constraint data are absent.
    """
    if semantics != PHYSICS_SEMANTICS:
        return {"status": "skipped", "reason": "exact native Q4 producer semantics not declared",
                "required_semantics": PHYSICS_SEMANTICS}
    if source is None:
        return {"status": "skipped", "reason": "accepted source state is required for fatigue consistency"}
    _transition(source, state.key)
    _check_tensile_boundary(source, mesh)
    if material.thickness <= 0 or material.ell <= 0 or material.alpha_t <= 0:
        raise ValueError("positive thickness, ell and alpha_t are required")
    _, det, shape, dshape = _support_weights(mesh)
    force, fields = equilibrium(state.u, state.d, mesh.conn, shape, dshape, det,
                                material.E, material.nu, material.residual_stiffness)
    d_gp = q4_interpolate(state.d, mesh.conn, shape)
    grad_d = q4_gradient(state.d, mesh.conn, dshape)
    alpha, q, fatigue = trial_fatigue(
        d_gp, fields["psi"], source.history[..., 1], source.history[..., 2],
        material.alpha_t, material.fatigue_power, material.residual_stiffness)
    free = _free_dofs(mesh)
    free_force = (force * material.thickness)[free]
    boundary_error = state.u[~free] - _tensile_lift(mesh, state.key.load)[~free]
    surface_base = (3 / 8) * material.Gc / material.ell * (
        d_gp + material.ell ** 2 * grad_d.square().sum(-1))
    surface_density = fatigue * surface_base
    elastic = float((fields["energy"] * det).sum() * material.thickness)
    surface = float((surface_density * det).sum() * material.thickness)
    # Keep the predicted-state energy separate from energy reconstructed by the
    # one-step fatigue law. Their difference is a state-consistency diagnostic.
    # Do not repair negative raw alpha_bar silently to manufacture an energy.
    state_surface = None
    if bool((state.history[..., 1] >= 0).all()):
        state_fatigue = carrara_f(state.history[..., 1], material.alpha_t, material.fatigue_power)
        state_surface = float((state_fatigue * surface_base * det).sum() * material.thickness)
    return {
        "status": "computed", "semantics": PHYSICS_SEMANTICS,
        "interpretation": "Numerical consistency diagnostics, not physical or reference qualification.",
        "equilibrium": {"status": "computed" if free_force.numel() else "not_applicable",
                        "reason": None if free_force.numel() else "mesh has no free displacement DOFs",
                        "free_force_l2": float(torch.linalg.vector_norm(free_force)) if free_force.numel() else None,
                        "free_force_max": float(free_force.abs().max()) if free_force.numel() else None,
                        "n_free_dofs": free_force.numel()},
        "boundary_displacement_max_error": float(boundary_error.abs().max()),
        "elastic_energy": elastic, "at1_surface_energy_from_trial_fatigue": surface,
        "total_energy_from_trial_fatigue": elastic + surface,
        "at1_surface_energy_from_state_alpha_bar": state_surface,
        "total_energy_from_state_alpha_bar": elastic + state_surface if state_surface is not None else None,
        "state_fatigue_energy_status": "computed" if state_surface is not None else "not_applicable_negative_alpha_bar",
        "history_consistency": {
            "H": weighted_errors(state.history[..., 0], fields["psi"], det),
            "alpha_bar": weighted_errors(state.history[..., 1], alpha, det),
            "q_prev": weighted_errors(state.history[..., 2], q, det)},
        "phase_kkt": {"status": "skipped", "reason": "phase penalties and active constraint contract not provided"},
    }


def matched_costs(*, training_seconds, data_generation_seconds, inference_seconds,
                  reference_seconds, quality_error, quality_tolerance):
    """Quality-matched timing for the SAME aggregate evaluated workload.

    Include all training and data-generation cost in total_cost_speedup. The
    caller must measure all timings on a declared common workload/hardware and
    predeclare the error metric/tolerance; this function does not time a run.
    """
    costs = dict(training_seconds=training_seconds, data_generation_seconds=data_generation_seconds,
                 inference_seconds=inference_seconds, reference_seconds=reference_seconds)
    if any(not math.isfinite(float(v)) or v < 0 for v in costs.values()):
        raise ValueError("costs must be finite nonnegative seconds")
    if inference_seconds <= 0 or reference_seconds <= 0:
        raise ValueError("inference and reference timings must be positive")
    if quality_tolerance is None or not math.isfinite(float(quality_tolerance)) or quality_tolerance < 0:
        raise ValueError("a finite nonnegative predeclared quality tolerance is required")
    met = quality_error is not None and math.isfinite(float(quality_error)) and 0 <= quality_error <= quality_tolerance
    total = training_seconds + data_generation_seconds + inference_seconds
    return {**costs, "quality_error": quality_error, "quality_tolerance": quality_tolerance,
            "quality_matched": met, "total_seconds": total,
            "inference_speedup": reference_seconds / inference_seconds if met else None,
            "total_cost_speedup": reference_seconds / total if met else None,
            "status": "computed" if met else "refused_quality_not_met"}
