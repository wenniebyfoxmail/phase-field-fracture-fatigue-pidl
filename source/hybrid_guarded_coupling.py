"""Bounded monotone working residual + AA / reduced VI Newton directions.

Only a real final frozen-fatigue QP followed by mechanics and the complete
original audit can create a StepProposal. Working points never commit history.
"""
from dataclasses import asdict, replace
from time import perf_counter
import hashlib
import numpy as np
from hybrid_coupled_acceleration import ProjectedAnderson, active_codes, joint_merit
from hybrid_damage import kkt_audit, solve_nodal_qp
from hybrid_history import AcceptedState, frozen_array
from hybrid_reduced_tangent import reduced_direction


def work_merit(damage,force,s):
    """Original equation/bound components; undefined QP operation term omitted.

    NOT the full acceptance merit. No f_solve is synthesized for Newton points.
    """
    values=[damage['primal_inf']/s.bound_tolerance,
        damage['kkt_scaled_inf']/s.damage_tolerance,
        damage['projected_inf']/s.damage_tolerance,
        force['force_scaled']/s.force_tolerance,
        force['force_l2']/(s.force_tolerance*s.force_scale),
        (damage['kkt_l2']+force['force_l2'])/s.joint_residual_sum_tolerance,
        force['boundary_inf']/s.bound_tolerance]
    if not np.isfinite(values).all():raise RuntimeError('nonfinite working residual')
    return float(max(values))


def solve_guarded(backend,old,dofs,values,load_id,settings,policy,initial_damage,
        u_pred,initialization_source,neural_used,attempted_model_id,
        prediction_context,work,call,remaining,start,observer):
    from hybrid_incremental import StepProposal, digest_config
    previous_id=old.fingerprint();lower=old.damage
    policy_id=digest_config(asdict(policy));records=[];evaluations=0
    counts=dict(proposals=0,kept_accelerated_maps=0,rejections=0,
                newton_directions=0,qp_calls=0,backtrack_evaluations=0)
    weights=np.asarray(backend.gp.T@backend.kin.det_jacobians.reshape(-1))
    aa=ProjectedAnderson(lower,backend.crack,weights,settings.bound_tolerance,
        replace(policy,mode='projected_anderson_monotone',max_proposals=5,max_rejections=5))
    w=backend.mechanics_workspace
    def snapshot():return w.factor_key,w.factor,w.factor_domain
    def restore(p):w.factor_key,w.factor,w.factor_domain=p['cache']
    def array_id(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    def emit(row):
        if observer is not None:
            payload=dict(previous_id=previous_id,load_id=load_id,policy_id=policy_id,
                elapsed_seconds=perf_counter()-start)
            payload.update(row)
            call('iteration_evidence',lambda:observer(payload))
    backend.mechanics_diagnostics=lambda row:emit(dict(event='mechanics_linear_call',outer=evaluations,**row))
    def room():
        remaining()
        if evaluations>=settings.max_outer:raise RuntimeError('fresh candidate budget exhausted')
    def evaluate(d,warm,kind,base=None,alpha=1.,f_solve=None,qp_info=None,known_u=None):
        nonlocal evaluations
        room();evaluations+=1
        d=np.asarray(d,float).copy()
        if d.shape!=lower.shape or not np.isfinite(d).all() or np.any(d<lower) or np.any(d>1.):
            raise RuntimeError('invalid original-bound work candidate')
        if known_u is None:
            mechanics_row=len(work)
            u,mechanics_info=call('mechanics_re_equilibration',lambda:backend.mechanics(
                d,dofs,values,settings,initial_u=warm))
            work[mechanics_row]['solver']=mechanics_info
            # Persist per-call aggregate diagnostics before any later assembly.
            emit(dict(event='mechanics_return',outer=evaluations,solver=mechanics_info))
        else:u=np.asarray(known_u).copy()
        psi,q=call('final_trial_history',lambda:backend.trial(old,u,d))
        qp=call('fresh_final_damage_assembly',lambda:backend.damage_problem(psi,q.fatigue,old))
        da=call('fresh_final_kkt',lambda:kkt_audit(qp,d,
            gradient_scale=settings.damage_gradient_scale,bound_tolerance=settings.bound_tolerance))
        fa=call('fresh_final_force',lambda:backend.force_audit(u,d,dofs,values,settings))
        mw=work_merit(da,fa,settings)
        fatigue=None if f_solve is None else float(np.max(abs(q.fatigue-f_solve)))
        ma=None if f_solve is None else joint_merit(da,fa,fatigue,settings)
        passed=ma is not None and ma<=1.
        kept=base is None or passed or mw<base['m_work']
        row=dict(event='fresh_evaluation',outer=evaluations,evaluation=kind,
            baseline_outer=None if base is None else base['outer'],alpha=float(alpha),
            damage=dict(da),force={k:fa[k] for k in ('force_inf','force_l2','force_scaled','boundary_inf')},
            m_work=mw,m_accept=ma,merit=ma,fatigue_residual=fatigue,
            qp_operation_component='NA' if f_solve is None else 'actual_QP',
            passed_physical=bool(passed),kept_as_iteration_point=bool(kept),
            input_damage_id=array_id(d),output_equilibrated_u_id=array_id(u),
            elapsed_seconds=perf_counter()-start)
        # Write all scalar evidence before vector diagnostics/candidate decisions.
        emit(row);records.append(row)
        if old.fingerprint()!=previous_id:raise RuntimeError('accepted preimage mutated')
        gradient=np.asarray(qp.hessian@d+qp.linear)
        projected=d-np.clip(d-gradient/settings.damage_gradient_scale,lower,1.)
        worst=int(np.argmax(abs(projected)))
        emit(dict(event='work_point_diagnostics',outer=evaluations,worst_projected_node=worst,
            gradient_at_worst=float(gradient[worst]),lower_gap_at_worst=float(d[worst]-lower[worst]),
            active_at_worst=int(active_codes(d,lower,settings.bound_tolerance)[worst]),
            active_gp_loading=int(np.sum(q.driver>old.driver)),fatigue_below_one_gp=int(np.sum(q.fatigue<1.)),
            d_id=array_id(d),A_id=array_id(q.accumulated),r_id=array_id(q.driver),f_id=array_id(q.fatigue)))
        p=dict(d=d,u=u,psi=psi,q=q,qp=qp,damage=da,force=fa,m_work=mw,m_accept=ma,
            fatigue=fatigue,passed=passed,kept=kept,outer=evaluations,cache=snapshot(),
            load_id=load_id,previous_id=previous_id,
            f_solve=None if f_solve is None else frozen_array(f_solve),qp_info=qp_info)
        if not kept:
            counts['rejections']+=1;restore(base)
            emit(dict(event='work_point_rollback',outer=evaluations,restored_outer=base['outer'],
                restored_d_id=array_id(base['d']),restored_u_id=array_id(base['u']),
                restored_m_work=base['m_work']))
        return p
    def finalize(p):
        if not p['passed'] or p['f_solve'] is None:
            raise RuntimeError('cannot accept a no-QP working point')
        if old.fingerprint()!=previous_id:raise RuntimeError('accepted preimage mutated before proposal')
        cert=call('accepted_mechanics_factor_certificate',lambda:w.certify_factor(
            p['d'],p['u'],dofs,observe=backend.mechanics_observer))
        work[-1]['solver']=cert;remaining()
        q=p['q']
        state=AcceptedState(p['u'],p['d'],q.accumulated,q.driver,q.fatigue,old.opaque,
            old.version+1,old.load_index+1,old.mesh_id,old.physics_id,load_id)
        certificate=dict(passed=True,previous_id=previous_id,state_id=state.fingerprint(),
            outer=evaluations,settings_id=digest_config(asdict(settings)),damage=p['damage'],
            mechanics=p['force'],fatigue_residual=p['fatigue'],total_wall_seconds=perf_counter()-start,
            model_id=attempted_model_id if neural_used else 'NN_OFF',attempted_model_id=attempted_model_id,
            initialization_source=initialization_source,coupling_policy_id=policy_id,
            coupling_policy=asdict(policy),coupling_work=counts,iterations=records,
            mechanics_factor_qualification=cert,m_work=p['m_work'],m_accept=p['m_accept'],
            true_final_QP=True,initial_to_final_damage_rms=float(np.sqrt(np.mean((p['d']-initial_damage)**2))),
            initial_to_final_damage_inf=float(np.max(abs(p['d']-initial_damage))))
        evidence=dict(f_solve_gp=p['f_solve'],psi_raw_commit_gp=frozen_array(p['psi']))
        return StepProposal(previous_id,state,certificate,tuple(work),prediction_context,evidence)
    def search(base,target,kind,f_solve=None,qp_info=None):
        # All backtracks, AA points, ordinary points and final certificates count
        # toward one fresh-candidate cap and the original step clock.
        for backtrack in range(policy.backtrack_candidates):
            room();alpha=2.**(-backtrack)
            d=np.clip(base['d']+alpha*(target-base['d']),lower,1.);d[backend.crack]=1.
            if np.array_equal(d,base['d']) and not (backtrack==0 and f_solve is not None):continue
            if backtrack:counts['backtrack_evaluations']+=1
            p=evaluate(d,base['u'],kind,base,alpha,
                f_solve=f_solve if backtrack==0 else None,qp_info=qp_info if backtrack==0 else None,
                known_u=base['u'] if np.array_equal(d,base['d']) else None)
            if p['kept']:return p
        return None
    known=u_pred if np.array_equal(initial_damage,lower) else None
    current=evaluate(initial_damage,u_pred,'initial_work',known_u=known)
    # Accepted work points strictly improve, hence current is also the complete
    # best checkpoint. Neither lower nor old accumulated/driver is ever changed.
    while True:
        room();base=current;restore(base)
        target,qi=call('damage_qp',lambda:solve_nodal_qp(base['qp'],base['d'],
            eps=settings.qp_precision,max_iter=settings.max_qp,time_limit=remaining()))
        work[-1]['solver']=qi;counts['qp_calls']+=1
        frozen_audit=call('frozen_QP_KKT',lambda:kkt_audit(base['qp'],target,
            gradient_scale=settings.damage_gradient_scale,bound_tolerance=settings.bound_tolerance))
        emit(dict(event='frozen_QP_return',next_outer=evaluations+1,qp=dict(qi),damage=frozen_audit,
            actual_f_solve_id=array_id(base['q'].fatigue)))
        ordinary=search(base,target,'ordinary_QP_map',base['q'].fatigue,qi)
        if ordinary is not None and ordinary['passed']:return finalize(ordinary)
        ratio=1. if ordinary is None else ordinary['m_work']/base['m_work']
        if ordinary is not None:
            current=ordinary
            if np.array_equal(ordinary['d'],target):aa.add(base['d'],target)
            else:aa.history=[]
        else:aa.history=[]
        # Successful AA is not permanently disabled by a lifetime cap. The total
        # fresh cap is authoritative; each proposal still uses original guards.
        if ratio<policy.schur_trigger_ratio:
            aa.proposals=0;aa.rejections=0
            candidate,info=call('coupling_proposal',aa.propose)
            emit(dict(event='anderson_proposal',outer=current['outer'],**info))
            if candidate is not None:
                counts['proposals']+=1
                trial=search(current,candidate,'anderson_work')
                if trial is not None:
                    counts['kept_accelerated_maps']+=1;current=trial
                else:aa.history=[]
            continue
        counts['newton_directions']+=1;restore(current)
        hook=getattr(backend,'unaccepted_point_observer',None)
        if hook is not None:call('unaccepted_before_schur',lambda:hook('best_before_schur',current))
        direction,info=reduced_direction(backend,old,current,dofs,settings,policy,call,remaining,emit)
        current['cache']=snapshot()
        trial=search(current,current['d']+direction,'reduced_VI_Newton')
        aa.history=[]
        if trial is not None:
            current=trial
            if hook is not None:call('unaccepted_after_schur',lambda:hook('candidate_after_schur',current))
        elif ordinary is None:raise RuntimeError('no decreasing ordinary or Schur candidate')
