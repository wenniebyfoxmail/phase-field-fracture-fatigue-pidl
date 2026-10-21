"""Joint original-residual projected trust globalization, no trial elimination.

Only the final real QP/mechanics/current-K/physical certificate can propose a
state. Working weights freeze once from the step's original operator diagonals.
"""
from dataclasses import asdict
from time import perf_counter
import hashlib
import numpy as np
from hybrid_coupled_block import block_direction
from hybrid_coupled_acceleration import joint_merit
from hybrid_damage import kkt_audit,solve_nodal_qp
from hybrid_guarded_coupling import work_merit
from hybrid_history import AcceptedState,frozen_array
from hybrid_reduced_tangent import natural_residual


def frozen_weights(mechanics_diagonal,damage_diagonal,gradient_scale):
    a=np.asarray(mechanics_diagonal);h=np.asarray(damage_diagonal)
    if (not np.isfinite(a).all() or not np.isfinite(h).all() or np.any(a<=0) or np.any(h<=0)
        or not np.isfinite(gradient_scale) or gradient_scale<=0):
        raise RuntimeError('invalid initial operator diagonal for frozen joint scales')
    return 1/np.sqrt(a),gradient_scale/np.sqrt(h)


def objective(Ru,F,weights):
    x=weights[0]*np.asarray(Ru);y=weights[1]*np.asarray(F)
    parts=(.5*float(x@x),.5*float(y@y))
    if not np.isfinite(parts).all():raise RuntimeError('nonfinite joint work objective')
    return sum(parts),parts


def trust_norm(su,sd,length):
    if not np.isfinite(length) or length<=0:raise RuntimeError('invalid domain length')
    return max(float(np.max(abs(su),initial=0.))/length,float(np.max(abs(sd),initial=0.)))


def projected_step(base,du,dd,free,dofs,values,lower,crack,radius,length):
    norm=trust_norm(du,dd,length)
    if not np.isfinite(norm):raise RuntimeError('nonfinite joint Newton direction')
    alpha=1. if norm==0 else min(1.,radius/norm)
    u=base['u'].copy();u[free]+=alpha*du;u[dofs]=values
    d=np.clip(base['d']+alpha*dd,lower,1.);d[crack]=1.
    su=u[free]-base['u'][free];sd=d-base['d']
    return u,d,su,sd,dict(alpha=alpha,direction_norm=norm,
        projected_step_norm=trust_norm(su,sd,length),
        projection_change_inf=float(np.max(abs(sd-alpha*dd),initial=0.)))


def model_residual(model,su,sd,gradient_scale):
    # ALL cross terms use the actual projected step, including B*(sd-alpha dd).
    ru=np.asarray(model['Ru']+model['A']@su+model['B']@sd)
    fd=model['F']+sd
    inactive=model['inactive']
    fd[inactive]=model['F'][inactive]+np.asarray(model['C']@su+model['D']@sd)[inactive]/gradient_scale
    if not np.isfinite(ru).all() or not np.isfinite(fd).all():raise RuntimeError('nonfinite joint model residual')
    return ru,fd


def trust_decision(base,model,actual,radius,step_norm,max_radius):
    if not np.isfinite([base,model,actual,radius,step_norm,max_radius]).all():
        raise RuntimeError('nonfinite trust reduction')
    pred=base-model;ared=base-actual
    rho=None if pred<=0 else ared/pred
    if rho is not None and not np.isfinite(rho):raise RuntimeError('nonfinite trust ratio')
    keep=bool(pred>0 and ared>0 and rho>=.1 and step_norm>0)
    new=radius
    if not keep or rho<.25:new=radius*.25
    elif rho>.75 and step_norm>=.9*radius:new=min(max_radius,2*radius)
    return keep,new,dict(predicted_reduction=pred,actual_reduction=ared,rho=rho)


def solve_joint_trust(backend,old,dofs,values,load_id,settings,policy,initial_damage,
        u_pred,initialization_source,neural_used,attempted_model_id,
        prediction_context,work,call,remaining,start,observer):
    from hybrid_incremental import StepProposal,digest_config
    previous_id=old.fingerprint();lower=old.damage;records=[];evaluations=0
    policy_id=digest_config(asdict(policy));w=backend.mechanics_workspace
    free=np.flatnonzero(~np.isin(np.arange(len(u_pred)),dofs))
    length=float(np.linalg.norm(np.ptp(backend.kin.points,axis=0)))
    radius=policy.trust_initial_radius
    counts=dict(newton_directions=0,model_trials=0,rejections=0,qp_calls=0,
        working_mechanics_calls=0,final_mechanics_calls=0)
    array_id=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    def emit(row):
        if observer is not None:
            payload=dict(previous_id=previous_id,load_id=load_id,policy_id=policy_id,
                elapsed_seconds=perf_counter()-start);payload.update(row)
            call('iteration_evidence',lambda:observer(payload))
    backend.mechanics_diagnostics=lambda row:emit(dict(event='mechanics_linear_call',outer=evaluations,**row))
    w.qualification_diagnostic=backend.mechanics_diagnostics
    def room():
        remaining()
        if evaluations>=settings.max_outer:raise RuntimeError('fresh candidate budget exhausted')
    def audit(u,d,kind,*,f_solve=None,qp_info=None):
        nonlocal evaluations
        room()
        if kind!='final_real_QP' and evaluations>=settings.max_outer-1:
            raise RuntimeError('joint working fresh budget exhausted; final slot reserved')
        evaluations+=1
        u=np.asarray(u,float).copy();d=np.asarray(d,float).copy()
        if (u.shape!=u_pred.shape or d.shape!=lower.shape or not np.isfinite(u).all()
            or not np.isfinite(d).all() or np.any(d<lower) or np.any(d>1)
            or np.any(d[backend.crack]!=1) or not np.array_equal(u[dofs],values)):
            raise RuntimeError('invalid joint original-domain candidate')
        psi,q=call('joint_trial_history',lambda:backend.trial(old,u,d))
        qp=call('joint_fresh_damage_assembly',lambda:backend.damage_problem(psi,q.fatigue,old))
        da=call('joint_fresh_kkt',lambda:kkt_audit(qp,d,
            gradient_scale=settings.damage_gradient_scale,bound_tolerance=settings.bound_tolerance))
        fa=call('joint_fresh_force',lambda:backend.force_audit(u,d,dofs,values,settings,include_vector=True))
        Ru=fa.pop('free_residual');matrix=fa.pop('original_matrix')
        gradient=np.asarray(qp.hessian@d+qp.linear)
        F,inactive=natural_residual(d,gradient,lower,settings.damage_gradient_scale)
        mw=work_merit(da,fa,settings)
        fatigue=None if f_solve is None else float(np.max(abs(q.fatigue-f_solve)))
        ma=None if f_solve is None else joint_merit(da,fa,fatigue,settings)
        row=dict(event='fresh_evaluation',outer=evaluations,evaluation=kind,m_work=mw,m_accept=ma,
            damage=dict(da),force={k:fa[k] for k in ('force_inf','force_l2','force_scaled','boundary_inf')},
            natural_inf=float(np.max(abs(F),initial=0.)),fatigue_residual=fatigue,
            qp_operation_component='NA' if f_solve is None else 'actual_QP',
            passed_physical=bool(ma is not None and ma<=1),input_damage_id=array_id(d),
            output_equilibrated_u_id=array_id(u),mechanically_eliminated=kind=='final_real_QP',
            fatigue_below_one_gp=int(np.sum(q.fatigue<1.)))
        emit(row);records.append(row)
        if old.fingerprint()!=previous_id:raise RuntimeError('accepted preimage mutated')
        return dict(u=u,d=d,psi=psi,q=q,qp=qp,damage=da,force=fa,Ru=Ru,F=F,
            diagonal=matrix.diagonal()[free],m_work=mw,m_accept=ma,fatigue=fatigue,
            outer=evaluations,load_id=load_id,previous_id=previous_id,alpha=None,
            f_solve=None if f_solve is None else frozen_array(f_solve),qp_info=qp_info,
            full_original_QP_map=False)
    def point_snapshot(tag,p):
        hook=getattr(backend,'unaccepted_point_observer',None)
        if hook is not None:call('unaccepted_joint_point',lambda:hook(tag,p))
    current=audit(u_pred,initial_damage,'initial_joint_work')
    weights=frozen_weights(current['diagonal'],current['qp'].hessian.diagonal(),settings.damage_gradient_scale)
    emit(dict(event='joint_frozen_scales',rule='initial original positive operator diagonals; no floor',
        mechanics_weight_id=array_id(weights[0]),damage_weight_id=array_id(weights[1]),domain_length=length,
        mechanics_weight_range=[float(np.min(weights[0])),float(np.max(weights[0]))],
        damage_weight_range=[float(np.min(weights[1])),float(np.max(weights[1]))]))
    current['phi'],parts=objective(current['Ru'],current['F'],weights)
    emit(dict(event='joint_initial_objective',phi=current['phi'],mechanics_part=parts[0],damage_part=parts[1]))
    box_D=None;seen_candidates={(array_id(current['u']),array_id(current['d']))}
    while True:
        room()
        if current['m_work']<=.01 and np.max(abs(current['F']),initial=0.)<=settings.qp_precision:
            # Exactly one physical certification attempt, no loop/fallback on fail.
            target,qi=call('damage_qp',lambda:solve_nodal_qp(current['qp'],current['d'],
                eps=settings.qp_precision,max_iter=settings.max_qp,time_limit=remaining()))
            work[-1]['solver']=qi;counts['qp_calls']+=1
            before=dict(event='joint_final_QP_start',outer=current['outer'],f_solve_id=array_id(current['q'].fatigue))
            emit(before)
            raw=getattr(backend,'joint_trial_observer',None)
            if raw is not None:call('joint_final_before_mechanics',lambda:raw(dict(before,parent_id=previous_id,load_id=load_id),
                dict(u=current['u'],d=target,f_solve=current['q'].fatigue)))
            counts['final_mechanics_calls']+=1
            mechanics_row=len(work)
            u,mi=call('mechanics_re_equilibration',lambda:backend.mechanics(target,dofs,values,settings,initial_u=current['u']))
            work[mechanics_row]['solver']=mi
            p=audit(u,target,'final_real_QP',f_solve=current['q'].fatigue,qp_info=qi)
            if p['m_accept']>1:raise RuntimeError('final joint physical qualification failed')
            certificate_row=len(work)
            cert=call('accepted_mechanics_factor_certificate',lambda:w.certify_factor(p['d'],p['u'],dofs,observe=backend.mechanics_observer))
            work[certificate_row]['solver']=cert;remaining()
            if old.fingerprint()!=previous_id:raise RuntimeError('accepted preimage mutated before proposal')
            q=p['q'];state=AcceptedState(p['u'],p['d'],q.accumulated,q.driver,q.fatigue,old.opaque,
                old.version+1,old.load_index+1,old.mesh_id,old.physics_id,load_id)
            certificate=dict(passed=True,previous_id=previous_id,state_id=state.fingerprint(),outer=evaluations,
                settings_id=digest_config(asdict(settings)),damage=p['damage'],mechanics=p['force'],
                fatigue_residual=p['fatigue'],total_wall_seconds=perf_counter()-start,
                model_id=attempted_model_id if neural_used else 'NN_OFF',attempted_model_id=attempted_model_id,
                initialization_source=initialization_source,coupling_policy_id=policy_id,coupling_policy=asdict(policy),
                coupling_work=counts,iterations=records,mechanics_factor_qualification=cert,
                m_work=p['m_work'],m_accept=p['m_accept'],true_final_QP=True,
                initial_to_final_damage_rms=float(np.sqrt(np.mean((p['d']-initial_damage)**2))),
                initial_to_final_damage_inf=float(np.max(abs(p['d']-initial_damage))))
            return StepProposal(previous_id,state,certificate,tuple(work),prediction_context,
                dict(f_solve_gp=p['f_solve'],psi_raw_commit_gp=frozen_array(p['psi'])))
        if counts['newton_directions']>=policy.max_newton_directions:
            emit(dict(event='block_direction_budget',directions=counts['newton_directions']))
            raise RuntimeError('joint coupled block direction budget exhausted')
        counts['newton_directions']+=1;point_snapshot('best_before_newton',current)
        emit(dict(event='newton_direction_start',outer=current['outer'],direction=counts['newton_directions'],radius=radius))
        dd,info,model=block_direction(backend,old,current,dofs,settings,policy,call,remaining,emit,return_model=True)
        # Assert free ordering and actual original residual identity before model use.
        if not np.array_equal(model['free_dofs'],free):raise RuntimeError('joint free domain mismatch')
        if policy.mode=='box_residual_trust':
            from hybrid_box_residual_subproblem import Budget,Model,original_natural_jacobian,freeze_variable_metric,solve_box_model
            budget=Budget(policy.subproblem_action_limit,policy.subproblem_update_limit)
            J=call('box_original_J_assembly',lambda:original_natural_jacobian(model,settings.damage_gradient_scale))
            row_weights=np.r_[weights[0],weights[1]]
            if box_D is None:
                box_D=call('box_freeze_variable_metric',lambda:freeze_variable_metric(J,row_weights,budget))
                emit(dict(event='box_frozen_variable_metric',D_id=array_id(box_D),
                    D_range=[float(box_D.min()),float(box_D.max())],norm='||D*p_eff||inf; initial weighted-J column norms, not R006 geometric norm'))
            ls=call('box_model_setup',lambda:Model(J,np.r_[current['Ru'],current['F']],row_weights,box_D,budget))
            model_hook=getattr(backend,'box_model_observer',None)
            if model_hook is not None:call('box_model_evidence',lambda:model_hook(current,J,row_weights,box_D,ls.L))
            newton_p=np.r_[model['du'],dd];kept=False
            while budget.updates<budget.update_limit-1:
                room()
                if radius<policy.trust_min_radius:raise RuntimeError('box trust radius collapsed')
                candidate=call('box_LS_subproblem',lambda:solve_box_model(ls,current,free,dofs,values,
                    lower,backend.crack,radius,newton_p,policy.subspace_steps))
                counts['model_trials']+=1
                meta=dict(event='box_trial_before',outer=current['outer'],direction=counts['newton_directions'],
                    radius=radius,base_phi=current['phi'],model_value=candidate['model_value'],
                    predicted_reduction=candidate['predicted_reduction'],pred_lower=candidate['pred_lower'],
                    pred_upper=candidate['pred_upper'],cauchy_required_bound=candidate['cauchy_required_bound'],
                    cauchy_model_lower_bound=candidate['cauchy_model_lower_bound'],
                    cauchy_pred_lower=candidate['cauchy_pred_lower'],selection=candidate['selection'],
                    model_L_upper=ls.L,model_definition=candidate['certificate_object'],rho=None,rho_status='pending actual nonlinear evaluation',actual_TR_norm=candidate['actual_TR_norm'],
                    inward_ulp_corrections=candidate['inward_ulp_corrections'],
                    subproblem_updates=budget.updates,action_count_upper=budget.used,action_counts=dict(budget.counts),
                    D_id=array_id(box_D),row_weights_id=array_id(row_weights),base_inactive_id=array_id(model['inactive']))
                raw=getattr(backend,'joint_trial_observer',None)
                if raw is not None:call('box_before_candidate_evidence',lambda:raw(dict(meta,parent_id=previous_id,load_id=load_id),
                    dict(u=candidate['u'],d=candidate['d'],base_u=current['u'],base_d=current['d'],
                        base_Ru=current['Ru'],base_F=current['F'],original_Rd=model['Rd'],
                        original_F=np.r_[current['Ru'],current['F']],inactive=model['inactive'],
                        row_weights=row_weights,model_r0=ls.r,D=box_D,free_dofs=free,cauchy_p=candidate['cauchy_p'],cauchy_tail=candidate['cauchy_tail'],actual_p=candidate['p'],actual_p_tail=candidate['p_tail'])))
                emit(meta)
                key=(array_id(candidate['u']),array_id(candidate['d']))
                if key in seen_candidates:
                    budget.update();radius*=.25;counts['rejections']+=1
                    emit(dict(event='box_duplicate_candidate_skipped',next_radius=radius,subproblem_updates=budget.updates))
                    continue
                seen_candidates.add(key)
                trial=audit(candidate['u'],candidate['d'],'box_projected_trial')
                trial['phi'],parts=objective(trial['Ru'],trial['F'],weights)
                pred=candidate['predicted_reduction'];ared=current['phi']-trial['phi'];rho=ared/pred
                if not np.isfinite([ared,rho]).all():raise RuntimeError('nonfinite box trust ratio')
                kept=bool(ared>0 and rho>=.1);next_radius=radius
                if not kept or rho<.25:next_radius=radius*.25
                elif rho>.75 and candidate['actual_TR_norm']>=.9*radius:next_radius=min(policy.trust_max_radius,2*radius)
                emit(dict(event='box_trial_decision',outer=trial['outer'],direction=counts['newton_directions'],
                    radius=radius,next_radius=next_radius,phi=trial['phi'],mechanics_part=parts[0],damage_part=parts[1],
                    actual_reduction=ared,predicted_reduction=pred,rho=rho,kept=kept,
                    selection=candidate['selection'],actual_TR_norm=candidate['actual_TR_norm'],
                    cauchy_required_bound=candidate['cauchy_required_bound'],model_bound_ratio=candidate['pred_lower']/candidate['cauchy_required_bound'],
                    subproblem_updates=budget.updates,action_count_upper=budget.used,action_counts=dict(budget.counts)))
                if next_radius!=radius:budget.update()
                radius=next_radius;trial['alpha']=None
                point_snapshot('candidate_after_newton'if kept else'last_rejected_candidate',trial)
                if kept:current=trial;break
                counts['rejections']+=1
                emit(dict(event='work_point_rollback',outer=trial['outer'],restored_outer=current['outer'],restored_phi=current['phi']))
            emit(dict(event='box_subproblem_end',outer=current['outer'],kept=kept,
                updates=budget.updates,action_count_upper=budget.used,action_counts=dict(budget.counts)))
            del ls,J,model
            if not kept:raise RuntimeError('box subproblem finite update budget exhausted')
            continue
        kept=False
        for attempt in range(1,policy.trust_trials+1):
            room()
            if radius<policy.trust_min_radius:raise RuntimeError('joint trust radius collapsed')
            counts['model_trials']+=1
            u,d,su,sd,step=projected_step(current,model['du'],dd,free,dofs,values,
                lower,backend.crack,radius,length)
            mr,mf=model_residual(model,su,sd,settings.damage_gradient_scale)
            model_phi,model_parts=objective(mr,mf,weights)
            before=dict(event='joint_trial_before',outer=current['outer'],direction=counts['newton_directions'],
                model_trial=attempt,radius=radius,base_phi=current['phi'],model_phi=model_phi,
                model_mechanics_part=model_parts[0],model_damage_part=model_parts[1],
                predicted_reduction=current['phi']-model_phi,**step)
            raw=getattr(backend,'joint_trial_observer',None)
            if raw is not None:call('joint_before_candidate_evidence',lambda:raw(dict(before,parent_id=previous_id,load_id=load_id),
                dict(u=u,d=d,base_u=current['u'],base_d=current['d'],
                    base_Ru=current['Ru'],base_F=current['F'],weights_mechanics=weights[0],weights_damage=weights[1])))
            emit(before)
            if before['predicted_reduction']<=0 or step['projected_step_norm']==0:
                counts['rejections']+=1;radius*=.25
                emit(dict(event='joint_trial_rejected_without_fresh',reason='no positive model reduction',next_radius=radius))
                continue
            trial=audit(u,d,'joint_projected_trial')
            trial['phi'],parts=objective(trial['Ru'],trial['F'],weights)
            kept,new_radius,reductions=trust_decision(current['phi'],model_phi,trial['phi'],radius,
                step['projected_step_norm'],policy.trust_max_radius)
            trial['alpha']=step['alpha']
            emit(dict(event='joint_trial_decision',outer=trial['outer'],direction=counts['newton_directions'],
                model_trial=attempt,radius=radius,next_radius=new_radius,phi=trial['phi'],
                mechanics_part=parts[0],damage_part=parts[1],kept=kept,**reductions,**step))
            point_snapshot('candidate_after_newton' if kept else 'last_rejected_candidate',trial)
            radius=new_radius
            if kept:current=trial;break
            counts['rejections']+=1
            emit(dict(event='work_point_rollback',outer=trial['outer'],restored_outer=current['outer'],restored_phi=current['phi']))
        del model
        if not kept:raise RuntimeError('joint trust finite trial budget exhausted')
