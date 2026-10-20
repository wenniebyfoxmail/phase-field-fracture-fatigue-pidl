"""Coupled constrained incremental solver. Library API; no run/training entry.

Only zero-body-force displacement loading is implemented. Traction/body-force
contracts must not be silently mapped to this backend. No accepted state is
mutated: solve_step returns an audited proposal for a separate durable commit.
"""
from dataclasses import dataclass, asdict, replace, fields
import hashlib
import json
from time import perf_counter

import numpy as np

from damage_conditioned_equilibrium import (
    solve_amor_equilibrium, assemble_amor_stiffness, tensile_energy,
)
from hybrid_damage import assemble_nodal_qp, kkt_audit, solve_nodal_qp
from hybrid_history import AcceptedState, frozen_array, trial_history
from native_q4_damage_qp import gauss_interpolation_matrix
from hybrid_coupled_acceleration import CouplingSettings, ProjectedAnderson, active_codes, joint_merit


def digest_config(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class SolverSettings:
    # These are engineering defaults, NOT an authorized scientific run card.
    force_scale: float
    damage_gradient_scale: float
    force_tolerance: float = 1.e-8
    joint_residual_sum_tolerance: float = 4.e-6
    damage_tolerance: float = 1.e-7
    bound_tolerance: float = 1.e-10
    fatigue_tolerance: float = 1.e-8
    qp_precision: float = 1.e-10
    max_outer: int = 100
    max_mechanics: int = 50
    max_qp: int = 200000
    wall_seconds: float = 120.

    def __post_init__(self):
        for k, v in asdict(self).items():
            if not np.isfinite(v) or v <= 0:
                raise ValueError(f"invalid setting {k}")
        for k in ("max_outer", "max_mechanics", "max_qp"):
            if type(getattr(self, k)) is not int:
                raise ValueError("iteration caps must be integers")
        if self.qp_precision > self.bound_tolerance:
            raise ValueError("QP precision must not exceed bound tolerance")


class StepFailure(RuntimeError):
    def __init__(self, message, work):
        super().__init__(message)
        self.work = tuple(work)


@dataclass(frozen=True)
class StepProposal:
    previous_id: str
    state: AcceptedState
    certificate: dict
    work: tuple
    prediction_context: tuple | None = None
    field_evidence: dict | None = None
    accepted_contract: dict | None = None


class NativeQ4Backend:
    def __init__(self, kin, crack, *, youngs_modulus=1., poisson_ratio=.3,
                 gc=.01, length_scale=.01, alpha_t=.5, power=2., thickness=1.):
        setup_started = perf_counter()
        scalars = [youngs_modulus, poisson_ratio, gc, length_scale, alpha_t, power, thickness]
        if (not np.isfinite(scalars).all() or min(youngs_modulus, gc, length_scale,
                                                alpha_t, power, thickness) <= 0
                or not -1 < poisson_ratio < .5):
            raise ValueError("invalid physical coefficients")
        arrays = {}
        for field in fields(kin):
            a = np.ascontiguousarray(getattr(kin, field.name))
            arrays[field.name] = np.frombuffer(a.tobytes(), dtype=a.dtype).reshape(a.shape)
        self.kin = kin = replace(kin, **arrays)
        # The GP feature/state contract is native (+,+),(-,+),(+,-),(-,-).
        from hybrid_kinematics import build_portable_native_q4_kinematics as build_native_q4_kinematics
        reference = build_native_q4_kinematics(kin.points, kin.cells)
        if (np.any(kin.det_jacobians <= 0) or np.any(kin.shape_values < 0)
                or not np.array_equal(kin.shape_values, reference.shape_values)
                or not np.array_equal(kin.b_matrices, reference.b_matrices)
                or not np.array_equal(kin.det_jacobians, reference.det_jacobians)):
            raise ValueError("native GP/geometry identity mismatch")
        if np.asarray(crack).dtype != bool:
            raise ValueError("crack must be an explicit boolean identity mask")
        self.crack = np.frombuffer(np.asarray(crack).tobytes(), dtype=bool)
        if self.crack.shape != (len(kin.points),):
            raise ValueError("crack shape mismatch")
        self.material = dict(youngs_modulus=youngs_modulus, poisson_ratio=poisson_ratio,
                             residual_stiffness=0., thickness=thickness)
        self.gc, self.length_scale = gc, length_scale
        self.alpha_t, self.power = alpha_t, power
        self.gp = gauss_interpolation_matrix(kin)
        h = hashlib.sha256()
        for a in (kin.points, kin.cells, kin.shape_values, kin.b_matrices,
                  kin.det_jacobians, self.crack):
            h.update(np.ascontiguousarray(a).tobytes())
        self.mesh_id = h.hexdigest()
        self.physics_id = digest_config(dict(**self.material, gc=gc, ell=length_scale,
                                            alpha_t=alpha_t, power=power,
                                            law="AT1-Amor-Carrara-nodalK-v1"))
        from hybrid_mechanics import MechanicsWorkspace
        self.mechanics_workspace=MechanicsWorkspace(self.kin,self.material)
        self.mechanics_observer=None
        self.setup_seconds = perf_counter() - setup_started

    def validate_state(self, state):
        if (state.mesh_id != self.mesh_id or state.physics_id != self.physics_id
                or state.damage.size != len(self.kin.points)
                or state.accumulated.shape != (len(self.kin.cells), 4)
                or np.any(state.damage[self.crack] != 1)):
            raise ValueError("accepted state/backend identity mismatch")

    def mechanics(self,d,dofs,values,settings,initial_u=None):
        if self.material!=self.mechanics_workspace.material:raise ValueError('workspace material changed; new identity/backend required')
        return self.mechanics_workspace.solve(d,dofs,values,settings,initial_u=initial_u,
                                               observe=self.mechanics_observer)

    def trial(self, old, u, d):
        psi, _ = tensile_energy(self.kin, u, youngs_modulus=self.material["youngs_modulus"],
                               poisson_ratio=self.material["poisson_ratio"])
        q = trial_history(old, (self.gp @ d).reshape(-1, 4), psi,
                          alpha_t=self.alpha_t, power=self.power)
        return psi, q

    def damage_problem(self, psi, f, old):
        # Existing kernel's w1 = Gc / ell; never pass Gc as w1.
        return assemble_nodal_qp(self.kin, psi, f, old.damage, self.crack,
                                 w1=self.gc / self.length_scale,
                                 length_scale=self.length_scale,
                                 thickness=self.material["thickness"])

    def force_audit(self, u, d, dofs, values, settings):
        matrix = assemble_amor_stiffness(self.kin, d, u, **self.material)
        force = np.asarray(matrix @ u)
        free = np.ones(len(u), bool)
        free[dofs] = False
        free_force = force[free]
        return dict(force_inf=float(np.max(np.abs(free_force), initial=0.)),
                    force_l2=float(np.linalg.norm(free_force)),
                    force_scaled=float(np.max(np.abs(free_force), initial=0.)) / settings.force_scale,
                    boundary_inf=float(np.max(np.abs(u[dofs] - values), initial=0.)),
                    reaction_dofs=dofs.tolist(), reaction_values=force[dofs].tolist())


def solve_step(backend, old, prescribed_dofs, prescribed_values, *, next_load_id,
               settings, predictor=None, classical_initial=None, return_prediction_context=False, work_observer=None,
               coupling=None, iteration_observer=None):
    """One complete coupled physical substep; no retry, commit or training.

    ``predictor.predict(old, u_pred, psi_pred, next_load_id, dofs, values)``
    returns a nodal coefficient a, not an accepted state. It may be omitted.
    Settings, model and all identifiers must be frozen by the future run card.
    """
    work = []
    start = perf_counter()

    def remaining():
        t = settings.wall_seconds - (perf_counter() - start)
        if t <= 0:
            raise RuntimeError("physical-substep wall cap reached")
        return t

    def call(kind, fn):
        remaining()
        tick = perf_counter()
        row = dict(work_id=len(work), kind=kind, status="failed")
        work.append(row)
        try:
            result = work_observer(kind,fn) if work_observer else fn()
            row["status"] = "returned"
            return result
        finally:
            row["wall_seconds"] = perf_counter() - tick
            # A native sparse solve cannot be preempted in-process. An external
            # producer watchdog is required for a hard process wall budget.

    try:
        coupling = CouplingSettings() if coupling is None else coupling
        if not isinstance(coupling,CouplingSettings):raise ValueError('explicit coupling policy required')
        if isinstance(backend,NativeQ4Backend):backend.mechanics_observer=work_observer
        def mechanics(d,initial):
            if isinstance(backend,NativeQ4Backend):
                return backend.mechanics(d,dofs,values,settings,initial_u=initial)
            return backend.mechanics(d,dofs,values,settings)
        backend.validate_state(old)
        previous_id = old.fingerprint()
        attempted_model_id = "NN_OFF"
        if predictor is not None:
            attempted_model_id = getattr(predictor, "model_id", None)
            if not isinstance(attempted_model_id, str) or not attempted_model_id.strip():
                raise ValueError("predictor requires a nonempty frozen model_id")
        if not isinstance(next_load_id, str) or not next_load_id:
            raise ValueError("target load identity required")
        dofs = np.asarray(prescribed_dofs)
        values = np.asarray(prescribed_values, dtype=float)
        if (dofs.ndim != 1 or not np.issubdtype(dofs.dtype, np.integer)
                or values.shape != dofs.shape or not values.size
                or not np.isfinite(values).all() or len(np.unique(dofs)) != len(dofs)
                or np.any(dofs < 0) or np.any(dofs >= old.displacement.size)):
            raise ValueError("invalid prescribed displacement contract")
        dofs = dofs.astype(np.int64)
        lower = old.damage
        u_pred, info = call("common_mechanics_predictor",
                            lambda: mechanics(lower,old.displacement))
        work[-1]["solver"] = info
        d = lower.copy() if classical_initial is None else np.asarray(classical_initial, float).copy()
        initialization_source = "previous_state" if classical_initial is None else "classical"
        neural_used = False
        if (d.shape != lower.shape or not np.isfinite(d).all()
                or np.any(d < lower) or np.any(d > 1)):
            raise ValueError("invalid classical feasible initial guess")
        prediction_context = None
        if predictor is not None or return_prediction_context:
            psi_pred, _ = call("prediction_features", lambda: backend.trial(old, u_pred, lower))
            if return_prediction_context:
                prediction_context = (frozen_array(u_pred), frozen_array(psi_pred))
        if predictor is not None:
            try:
                a = call("network_inference", lambda: predictor.predict(
                    old, frozen_array(u_pred), frozen_array(psi_pred), next_load_id,
                    np.frombuffer(dofs.tobytes(), dtype=dofs.dtype), frozen_array(values)))
                a = np.asarray(a, float)
                if a.shape != lower.shape or not np.isfinite(a).all():
                    raise ValueError("malformed neural prediction")
                d = lower + (1 - lower) * np.clip(a, 0., 1.)
                d[backend.crack] = 1.
                initialization_source, neural_used = "neural", True
            except (ValueError, RuntimeError) as exc:
                initialization_source = "classical_fallback"
                work.append(dict(work_id=len(work), kind="initial_guess_fallback",
                                 reason=str(exc), wall_seconds=0., status="baseline_initial"))
        initial_damage=d.copy()
        policy_id=digest_config(asdict(coupling))
        weights=(np.asarray(backend.gp.T@backend.kin.det_jacobians.reshape(-1))
                 if isinstance(backend,NativeQ4Backend) else np.ones(len(lower)))
        accelerator=ProjectedAnderson(lower,backend.crack,weights,settings.bound_tolerance,coupling)
        pending=None;last_kept=None;last_signs=None;iteration_records=[]
        def array_hash(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
        def cache_snapshot():
            if not isinstance(backend,NativeQ4Backend):return None
            w=backend.mechanics_workspace;return w.factor_key,w.factor
        def cache_restore(snapshot):
            if snapshot is not None:
                backend.mechanics_workspace.factor_key,backend.mechanics_workspace.factor=snapshot
        # The common mechanics result is reusable only if d is identical.
        u_cache = u_pred if np.array_equal(d, lower) else None
        u_guess=u_pred
        for outer in range(1, settings.max_outer + 1):
            warm_vector=u_guess if u_cache is None else u_cache
            warm_u_id=array_hash(warm_vector)
            if u_cache is None:
                u, info = call("mechanics", lambda: mechanics(d,u_guess))
                work[-1]["solver"] = info
            else:
                u = u_cache
            psi, q = call("trial_history", lambda: backend.trial(old, u, d))
            qp = call("damage_assembly", lambda: backend.damage_problem(psi, q.fatigue, old))
            new_d, qp_info = call("damage_qp", lambda: solve_nodal_qp(
                qp, d, eps=settings.qp_precision, max_iter=settings.max_qp, time_limit=remaining()))
            work[-1]["solver"] = qp_info
            if np.array_equal(new_d, d):
                final_u = u
            else:
                final_u, info = call("mechanics_re_equilibration",
                                     lambda: mechanics(new_d,u))
                work[-1]["solver"] = info
            final_psi, final_q = call("final_trial_history", lambda: backend.trial(old, final_u, new_d))
            final_qp = call("fresh_final_damage_assembly",
                            lambda: backend.damage_problem(final_psi, final_q.fatigue, old))
            damage_audit = call("fresh_final_kkt", lambda: kkt_audit(
                final_qp, new_d, gradient_scale=settings.damage_gradient_scale,
                bound_tolerance=settings.bound_tolerance))
            force_audit = call("fresh_final_force", lambda: backend.force_audit(
                final_u, new_d, dofs, values, settings))
            fatigue_residual = float(np.max(np.abs(final_q.fatigue - q.fatigue)))
            scalars = list(damage_audit[k] for k in ("primal_inf", "kkt_scaled_inf", "kkt_l2", "projected_inf"))
            scalars += [force_audit[k] for k in ("force_inf", "force_l2", "force_scaled", "boundary_inf")]
            scalars += [fatigue_residual]
            passed = (np.isfinite(scalars).all()
                      and damage_audit["primal_inf"] <= settings.bound_tolerance
                      and max(damage_audit["kkt_scaled_inf"], damage_audit["projected_inf"]) <= settings.damage_tolerance
                      and force_audit["force_scaled"] <= settings.force_tolerance
                      and force_audit["force_l2"] <= settings.force_tolerance * settings.force_scale
                      and force_audit["force_l2"] + damage_audit["kkt_l2"] <= settings.joint_residual_sum_tolerance
                      and force_audit["boundary_inf"] <= settings.bound_tolerance
                      and fatigue_residual <= settings.fatigue_tolerance)
            merit=joint_merit(damage_audit,force_audit,fatigue_residual,settings)
            # Persist the completed fresh map before any extrapolation, array
            # diagnostics or cache bookkeeping can fail. A later decision is
            # a separate event; absence of that event never implies acceptance.
            if iteration_observer is not None:
                evaluation=dict(event='fresh_evaluation',outer=outer,policy_id=policy_id,
                                previous_id=previous_id,load_id=next_load_id,
                                evaluation='anderson_trial' if pending is not None else 'plain_map',
                                baseline_outer=pending['outer'] if pending is not None else None,
                                damage=dict(damage_audit),
                                force={k:force_audit[k] for k in ('force_inf','force_l2','force_scaled','boundary_inf')},
                                fatigue_residual=fatigue_residual,merit=merit,
                                passed_physical=bool(passed),elapsed_seconds=perf_counter()-start)
                call('iteration_evaluation_evidence',lambda:iteration_observer(evaluation))
            remaining()
            if old.fingerprint() != previous_id:
                raise RuntimeError("accepted preimage mutated")
            diagnostics_started=perf_counter()
            was_trial=pending is not None
            rejected=bool(was_trial and not passed and merit>coupling.merit_factor*pending['merit'])
            code=active_codes(new_d,lower,settings.bound_tolerance)
            fp=accelerator.norm(new_d-d)
            record=dict(event='iteration_decision',outer=outer,policy_id=policy_id,previous_id=previous_id,load_id=next_load_id,
                        evaluation='anderson_trial' if was_trial else 'plain_map',
                        baseline_outer=pending['outer'] if was_trial else None,
                        input_damage_id=array_hash(d),input_equilibrated_u_id=array_hash(u),
                        mechanical_warm_start_u_id=warm_u_id,
                        output_damage_id=array_hash(new_d),output_equilibrated_u_id=array_hash(final_u),
                        final_trial_A_id=array_hash(final_q.accumulated),final_trial_r_id=array_hash(final_q.driver),
                        final_trial_f_id=array_hash(final_q.fatigue),
                        damage=dict(damage_audit),force={k:force_audit[k] for k in ('force_inf','force_l2','force_scaled','boundary_inf')},
                        fatigue_residual=fatigue_residual,merit=merit,passed_physical=bool(passed),
                        fixed_point_rms=fp,observed_fp_ratio_to_last_kept=(fp/last_kept['fp'] if last_kept is not None and last_kept['fp']>0 else None),
                        observed_merit_ratio_to_last_kept=(merit/last_kept['merit'] if last_kept is not None and last_kept['merit']>0 else None),
                        active_counts={str(i):int(np.sum(code==i)) for i in range(4)},
                        active_changes_from_last_kept=int(np.sum(code!=last_kept['active'])) if last_kept is not None else None,
                        kept_as_iteration_point=not rejected,rejection_reason='joint_merit_guard' if rejected else None,
                        qp=dict(qp_info),elapsed_seconds=perf_counter()-start)
            loading=final_q.driver>old.driver
            record['history_loading']=dict(active_gp=int(loading.sum()),id=array_hash(loading),
                                           changes_from_last_kept=int(np.sum(loading!=last_kept['loading'])) if last_kept is not None else None,
                                           fatigue_below_one_gp=int(np.sum(final_q.fatigue<1.)))
            signs=None
            if isinstance(backend,NativeQ4Backend):
                from damage_conditioned_equilibrium import _trace_signs
                signs=_trace_signs(final_u,backend.kin)
                record['trace']=dict(positive=int(signs.sum()),nonpositive=int(signs.size-signs.sum()),
                                     input_equilibrated_id=array_hash(_trace_signs(u,backend.kin)),warm_start_id=array_hash(_trace_signs(warm_vector,backend.kin)),
                                     id=array_hash(signs),changes_from_last_kept=int(np.sum(signs!=last_signs)) if last_signs is not None else None)
            next_guess=None
            proposal_seconds=0.
            if rejected:
                accelerator.reject();cache_restore(pending['cache'])
                d,u_cache=pending['d'],pending['u']
                record['restored_baseline_damage_id']=array_hash(d)
                record['restored_baseline_u_id']=array_hash(u_cache)
                record['restored_baseline_audit']=pending['audit']
                record['next_guess']=dict(reason='restored_baseline_and_disabled' if accelerator.rejections>=coupling.max_rejections else 'restored_baseline')
                pending=None
            elif not passed:
                if was_trial:accelerator.kept_trials+=1
                accelerator.add(d,new_d)
                last_kept=dict(fp=fp,merit=merit,active=code.copy(),loading=loading.copy())
                last_signs=signs.copy() if signs is not None else None
                if outer<settings.max_outer:
                    next_guess,proposal_info=call('coupling_proposal',accelerator.propose)
                    proposal_seconds=work[-1]['wall_seconds']
                else:proposal_info=dict(reason='outer_map_budget_exhausted')
                record['next_guess']=proposal_info
                if next_guess is not None:
                    record['next_guess']['candidate_damage_id']=array_hash(next_guess)
                    record['next_guess']['planned_next_outer']=outer+1
                    pending=dict(outer=outer,merit=merit,d=new_d.copy(),u=final_u.copy(),cache=cache_snapshot(),
                                 audit=dict(damage=dict(damage_audit),force=dict(record['force']),fatigue_residual=fatigue_residual,merit=merit))
                    # This is only an initial guess. The next loop MUST run
                    # the complete original map and fresh physical predicates.
                    d,u_cache,u_guess=next_guess,None,final_u
                else:
                    pending=None;d,u_cache=new_d,final_u
            else:
                if was_trial:accelerator.kept_trials+=1
                record['next_guess']=dict(reason='physical_acceptance_no_acceleration_needed')
            iteration_records.append(record)
            record['diagnostic_wall_seconds']=perf_counter()-diagnostics_started-proposal_seconds
            if iteration_observer is not None:
                import copy
                call('iteration_evidence',lambda:iteration_observer(copy.deepcopy(record)))
            remaining()
            if old.fingerprint()!=previous_id:raise RuntimeError('accepted preimage mutated after evidence')
            if passed:
                state = AcceptedState(final_u, new_d, final_q.accumulated, final_q.driver,
                                      final_q.fatigue, old.opaque, old.version + 1,
                                      old.load_index + 1, old.mesh_id, old.physics_id, next_load_id)
                certificate = dict(passed=True, previous_id=previous_id,
                                   state_id=state.fingerprint(), outer=outer,
                                   settings_id=digest_config(asdict(settings)),
                                   damage=damage_audit, mechanics=force_audit,
                                   fatigue_residual=fatigue_residual,
                                   total_wall_seconds=perf_counter() - start,
                                   model_id=attempted_model_id if neural_used else "NN_OFF",
                                   attempted_model_id=attempted_model_id,
                                   initialization_source=initialization_source,
                                   coupling_policy_id=policy_id,coupling_policy=asdict(coupling),
                                   coupling_work=dict(proposals=accelerator.proposals,kept_accelerated_maps=accelerator.kept_trials,rejections=accelerator.rejections),
                                   iterations=iteration_records,
                                   initial_to_final_damage_rms=float(np.sqrt(np.mean((new_d-initial_damage)**2))),
                                   initial_to_final_damage_inf=float(np.max(abs(new_d-initial_damage))))
                # Keep the actual last solved QP coefficient. Reconstructing it
                # from the accepted history would silently substitute f_commit.
                evidence = dict(f_solve_gp=frozen_array(q.fatigue),
                                psi_raw_commit_gp=frozen_array(final_psi))
                return StepProposal(previous_id, state, certificate, tuple(work), prediction_context, evidence)
        raise RuntimeError("joint iteration cap reached; no accepted proposal")
    except Exception as exc:
        if isinstance(exc, StepFailure):
            raise
        raise StepFailure(str(exc), work) from exc
