#!/usr/bin/env python3
"""One completed hidden step, then an actual closed Newton head, at most eight pairs.

Same-source comparison of cadence PLUS per-step LBFGS history resets. This is
not variable projection: no head is solved inside hidden line-search trials.
"""
from __future__ import annotations
import argparse,datetime as dt,json,os,sys,time
from pathlib import Path
import numpy as np
import torch

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_pidl_persisted_phi_hidden_newton as base
from run_pidl_hidden_newton import hidden_named

PROTOCOL='S04-E011-TIGHT-COUPLING-HIDDEN-NEWTON-r1'
PREVIOUS_ENERGY=.005267089573071509
DIRECTIONAL_MARGIN=1e-10
GTOL=base.GTOL


def allocation(result):
    result.update(prior_evaluations=0,new_probe_production_cap=365,total_prior_plus_new_cap=365,
        new_probe_production_deadline_seconds=600,prior_elapsed_seconds=None,cumulative_elapsed_seconds_claim=False)
    return result


def hidden_first_step(net,objective,budget,initial_raw,scale,pair,max_calls):
    """One completed LBFGS.step only; interrupted Wolfe trials restore whole state."""
    assert 2<=max_calls<=40
    parameters=[p for _,p in hidden_named(net)];flags=[p.requires_grad for p in net.parameters()]
    head_before={n:p.detach().clone() for n,p in net.named_parameters() if n.startswith('output_layer.')}
    for name,p in net.named_parameters():p.requires_grad_(not name.startswith('output_layer.'))
    before=base.snapshot(net);accepted=[];last=before;used=0;energy=float(initial_raw)
    stop='hidden_step_budget';hard=False
    optimizer=torch.optim.LBFGS(parameters,lr=1.,max_iter=1,max_eval=20,history_size=5,
        tolerance_grad=0.,tolerance_change=0.,line_search_fn='strong_wolfe')
    def evaluate(backward,endpoint=False):
        nonlocal used
        if used>=max_calls-(0 if endpoint else 1):raise base.BudgetStop('hidden_step_budget')
        row=budget.begin('hidden_LBFGS_closure' if backward else 'hidden_completed_step_readout');used+=1
        optimizer.zero_grad(set_to_none=True);raw=objective();assert torch.isfinite(raw)
        loss=raw/scale
        if backward:
            loss.backward();assert all(p.grad is None or torch.isfinite(p.grad).all() for p in parameters)
        row.update(completed=True,pair=pair,hidden_step_evaluation=used,E_el=float(raw.detach()),optimizer_loss=float(loss.detach()),optimizer_scale=scale)
        base.dump(budget.folder/'trace.json',budget.trace);return loss
    try:
        optimizer.step(lambda:evaluate(True))
        energy=float(evaluate(False,endpoint=True).detach())*scale
        if not base.actual_nonincrease(initial_raw,energy):raise base.TangentFailure('completed_hidden_step_energy_increase')
        delta=max(float((p.detach()-before[n]).abs().max()) for n,p in hidden_named(net))
        last=base.snapshot(net)
        accepted.append(dict(kind='hidden_completed_step_candidate',pair=pair,evaluations=len(budget.trace),E_el=energy,
            hidden_parameter_delta_inf=delta,retained_closed_endpoint=False,actual_energy_verified=True))
        stop='hidden_exact_parameter_stagnation' if delta==0 else 'first_completed_hidden_step'
    except base.BudgetStop as err:stop=str(err)
    except base.TangentFailure as err:stop=str(err);hard=True
    finally:
        net.load_state_dict(last)
        for p,flag in zip(net.parameters(),flags):p.requires_grad_(flag)
        for name,p in net.named_parameters():
            if name in head_before:assert torch.equal(p,head_before[name])
    return dict(stop=stop,evaluations=used,cap=max_calls,accepted=accepted,E_el=energy,hard_failure=hard,
        completed_steps=len(accepted),optimizer='one hidden-only LBFGS step; strong_wolfe; history5 reset EACH pair',
        optimizer_scale=scale,hidden_line_search_head_solves=0)


def record_checkpoint(folder,field,obs,fields,pair,kind,retained):
    row={**obs,'pair':pair,'checkpoint_kind':kind,'pair_completed':retained,
         'retained_closed_endpoint':retained}
    base.save_checkpoint(folder,field,row,fields)
    return row


def head_contract_passed(obs,realization_error,energy_before):
    return bool(base.actual_nonincrease(energy_before,obs['E_el']) and
        realization_error<=base.UV_REALIZATION_TOLERANCE and obs['reduced_gradient_inf']<=GTOL)


def run_state(item,out,device,phase,start_time):
    if phase=='probe':
        result=allocation(base.run_state(item,out,device,phase,start_time))
        base.dump(out/'result.json',result);return result
    out.mkdir();(out/'readouts').mkdir();budget=base.phase_budget(out,phase,start_time);work=base.PhaseWork(budget)
    assert (item['cycle'],item['substep'],item['step'])==(20,4,99)
    for name in ['source_fields','source_phi','source_transform']:assert base.sha(item[name])==item[name+'_sha256']
    data=dict(np.load(item['input'],allow_pickle=False));problem=base.LocalProblem(data,device)
    original=torch.load(item['original_model'],map_location=device,weights_only=True)
    initial=torch.load(item['initial_model'],map_location=device,weights_only=True)
    field=base.make_smooth(original,problem);field.net.load_state_dict(initial);field.net.requires_grad_(False)
    assert not field.williams_enabled and not field.ansatz_enabled and not field.exact_bc_enabled and not field.symmetry_prior
    start=base.snapshot(field.net);anchor={n:base.tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
    physical={n:base.tensor_hash(p) for n,p in [('d',problem.df),('lower',problem.hist),('f',problem.f)]}
    identity=np.eye(401);head=torch.cat((field.net.output_layer.weight[:2],field.net.output_layer.bias[:2,None]),dim=1).detach().cpu().numpy()
    space=base.load_actual_space(item['source_phi'],item['source_transform'],head,device,problem.n)
    base.persist_space(space,out/'bases'/'initial',field,item['source_phi'],item['source_transform'])
    obs,fields,_=base.persisted_readout(field,problem,identity,budget,'initial_learned_head',space)
    with np.load(item['source_fields'],allow_pickle=False) as z:errors={k:float(np.max(abs(fields[k]-z[k]))) for k in ['u','v','d']}
    source=dict(source_energy=base.SOURCE_ENERGY,actual_energy=obs['E_el'],energy_abs_error=abs(obs['E_el']-base.SOURCE_ENERGY),
        actual_current_head_gradient_inf=obs['reduced_gradient_inf'],source_fields_maxabs=errors,initial_rank=386,
        source_fields_path=item['source_fields'],source_fields_sha256=item['source_fields_sha256'],
        passed=bool(max(errors.values())<=1e-12 and abs(obs['E_el']-base.SOURCE_ENERGY)<=1e-10 and obs['reduced_gradient_inf']<=GTOL))
    base.dump(out/'source_reproduction.json',source);assert source['passed'],'source observation persisted before source-admission failure'
    row=budget.begin('source_energy_contract')
    with torch.no_grad():
        u,v,_=field.fieldCalculation(problem.x)
        oracle=base.compute_energy(problem.x,u,v,problem.df,problem.hist,problem.mat,problem.model,problem.area,problem.cells,
            f_fatigue=problem.f,irreversibility_penalty_cfg={'enable':True,'mode':'fem_gp_q4'})[0]
    row.update(completed=True,E_el=float(oracle),source_error=abs(float(oracle)-obs['E_el']));base.dump(out/'source_energy_contract.json',row)
    assert row['source_error']<=1e-10
    row=budget.begin('native_FEM_force_contract');fem,_=base.readout(problem,problem.uf,problem.vf,space['phi'],native=data['ru_fem'])
    row.update(completed=True,**fem);base.dump(out/'native_FEM_force_contract.json',row);assert fem['free_u_l2']<1e-8
    record_checkpoint(out/'checkpoints'/'initial',field,obs,fields,0,'initial',True)
    last=dict(state=base.snapshot(field.net),result=obs,fields=fields,label='initial',space=space)
    gradients=[obs];stages=[];accepted=[];hidden_calls=0;closed_pairs=0;closure_miss=False;reason='max_eight_pairs_completed'
    try:
        for pair in range(1,9):
            work.check();assert last['result']['reduced_gradient_inf']<=GTOL
            remaining=80-hidden_calls
            if remaining<2:reason='hidden_total_budget';break
            before_energy=last['result']['E_el']
            def objective():
                u,v,_=field.fieldCalculation(problem.x);return problem.parts(u,v,problem.df)[0]
            micro=hidden_first_step(field.net,objective,budget,before_energy,base.OPTIMIZER_SCALE,pair,min(40,remaining))
            hidden_calls+=micro['evaluations'];accepted.extend(micro['accepted'])
            stage=dict(pair=pair,hidden=micro,pair_completed=False,retained_closed_endpoint=False,
                nonzero_completed_hidden_step=bool(micro['accepted'] and micro['accepted'][0]['hidden_parameter_delta_inf']>0));stages.append(stage)
            if micro['hard_failure'] or micro['stop']!='first_completed_hidden_step':
                reason=micro['stop'];space=base.restore_verified(field,last);stage['rolled_back']=True;break
            space=base.build_full_space(field,problem,work);base.persist_space(space,out/'bases'/f'hidden_{pair}',field)
            candidate,cf,_=base.persisted_readout(field,problem,identity,budget,f'hidden_{pair}',space)
            gradients.append(candidate);hidden_row=record_checkpoint(out/'checkpoints'/f'hidden_{pair}',field,candidate,cf,pair,'hidden_candidate',False)
            stage['hidden_candidate']=candidate
            if not base.actual_nonincrease(before_energy,candidate['E_el']):
                reason='hidden_actual_energy_increase';space=base.restore_verified(field,last);stage['rolled_back']=True;break
            base.frozen_checks(field,problem,start,anchor,physical)
            correction,cg,linear=base.correct_full_head(field,problem,space,work,budget,out/f'head_stage_{pair}',pair)
            stage['head']=correction
            if correction['hard_failure']:
                reason='hard_head_failure_'+correction['solver']['stop'];closure_miss=True
                space=base.restore_verified(field,last);stage['rolled_back']=True;break
            actual,af,ag=base.persisted_readout(field,problem,identity,budget,f'head_{pair}',space)
            gradients.append(actual);realization=base.linear_realization_error(af,linear)
            checkpoint_row=record_checkpoint(out/'checkpoints'/f'head_{pair}',field,actual,af,pair,'head_candidate',False)
            base.frozen_checks(field,problem,start,anchor,physical)
            passed=head_contract_passed(actual,realization,candidate['E_el'])
            correction.update(actual_network=actual,linear_vs_actual_uv_maxabs=realization,UV_realization_tolerance=base.UV_REALIZATION_TOLERANCE,
                actual_minus_conditioned_energy=actual['E_el']-correction['conditioned_E_el'],
                actual_minus_conditioned_gradient_inf=float(np.max(abs(ag-cg))),actual_endpoint_retained=passed,
                actual_head_stationarity_closed=bool(actual['reduced_gradient_inf']<=GTOL))
            stage['head_contract_passed']=passed
            if not passed:
                closure_miss=True
                reason=('head_realization_contract_failure' if realization>base.UV_REALIZATION_TOLERANCE else
                    'actual_head_gradient_miss' if actual['reduced_gradient_inf']>GTOL else 'head_actual_energy_increase')
                space=base.restore_verified(field,last);stage['rolled_back']=True;break
            closed_pairs+=1;stage.update(pair_completed=True,retained_closed_endpoint=True)
            checkpoint_row.update(checkpoint_kind='closed_head',pair_completed=True,retained_closed_endpoint=True)
            base.dump(out/'checkpoints'/f'head_{pair}'/'result.json',checkpoint_row)
            hidden_row.update(pair_completed=True,retained_closed_endpoint=False,completed_pair_head_checkpoint=f'head_{pair}')
            base.dump(out/'checkpoints'/f'hidden_{pair}'/'result.json',hidden_row)
            for entry in micro['accepted']:entry['incorporated_in_closed_pair']=True
            last=dict(state=base.snapshot(field.net),result=actual,fields=af,label=f'head_{pair}',space=space)
            for entry in correction['accepted']:accepted.append({**entry,'kind':'conditioned_head_inner','pair':pair,'actual_energy_verified':False})
            base.dump(out/'stages.json',stages);base.dump(out/'accepted.json',accepted)
    except (base.BudgetStop,base.TangentFailure) as err:
        reason=str(err);space=base.restore_verified(field,last)
        if stages:stages[-1].update(interrupted=reason,rolled_back=not stages[-1]['pair_completed'],retained_checkpoint=last['label'])
    # A candidate hidden/head can never become the final endpoint by fallback.
    space=base.restore_verified(field,last);final=None;ff=None
    try:
        final,ff,_=base.persisted_readout(field,problem,identity,budget,'final',space,final=True)
        assert base.actual_nonincrease(last['result']['E_el'],final['E_el'])
        gradients.append(final)
    except base.BudgetStop as err:reason+='; terminal_missing_'+str(err)
    base.frozen_checks(field,problem,start,anchor,physical)
    np.savez_compressed(out/'fields.npz',**(ff if final else last['fields']));torch.save(field.net.state_dict(),out/'accepted_network.pt')
    changed=base.hidden_change(start,base.snapshot(field.net));final_closed=bool(final and final['reduced_gradient_inf']<=GTOL)
    all_changed_steps_closed=all(not s['nonzero_completed_hidden_step'] or s['pair_completed'] for s in stages)
    result=allocation(dict(status='completed' if final else 'partial_terminal_readout_missing',cycle=20,substep=4,step=99,
        source_reproduction=source,initial=gradients[0],actual_network=final,last_verified_network=last['result'],
        last_verified_checkpoint=last['label'],last_closed_checkpoint=last['label'],closed_pairs=closed_pairs,
        hidden_pairs_attempted=len(stages),max_hidden_pairs=8,hidden_total_evaluations=hidden_calls,hidden_total_cap=80,hidden_step_cap=40,
        head_closure_failure_encountered=closure_miss,all_nonzero_hidden_steps_closed=all_changed_steps_closed,
        operational_coupling_closure=bool(final_closed and not closure_miss and all_changed_steps_closed),
        coupling_endpoint_eligible=bool(closed_pairs and changed['changed'] and final_closed),
        E_el=final['E_el'] if final else None,free_u_l2=final['free_u_l2'] if final else None,
        uv_mass_rel_L2=final['uv_mass_rel_L2'] if final else None,uv_H1_rel=final['uv_H1_rel'] if final else None,
        head_stationarity_closed=final_closed,gradient_inf_tolerance=GTOL,hidden_change=changed,gradient_readouts=gradients,
        optimizer_scale=base.OPTIMIZER_SCALE,stop=reason,evaluations=len(budget.trace),cap=budget.cap,deadline_seconds=budget.seconds,
        elapsed_seconds=time.monotonic()-budget.start,dense_assemblies=work.assemblies,explicit_tangent_vector_products=work.products,
        linear_solves=work.solves,current_raw_columns=401,dynamic_current_feature_basis=True,initial_rank=386,final_rank=space['transform'].shape[1],
        old_restricted_span_used=False,selection_rule='last chronological CLOSED complete pair, never FEM-error selection',
        cadence_and_history_reset_combined=True,hidden_history_reset_each_pair=True,true_variable_projection=False,
        previous_same_start_terminal_E_el=PREVIOUS_ENERGY,directional_margin=DIRECTIONAL_MARGIN,
        previous_energy_minus_terminal=PREVIOUS_ENERGY-final['E_el'] if final else None,
        damage_output_row_unchanged=True,Smooth_B0_anchor_unchanged=True,mechanical_damage_exact_FEM=True,boundary_unchanged=True,
        NN_damage_field_fixed_claim=False,history_commits=0,rollout_steps=0,ridge=0.,whole_network_capacity_claim=False))
    for name,value in [('result',result),('stages',stages),('accepted',accepted),('gradient_readouts',gradients),('trace',budget.trace)]:base.dump(out/(name+'.json'),value)
    return result


def validate_contract(c,phase):
    assert c['protocol']==PROTOCOL and len(c['states'])==1
    assert c['prior_evaluations']==0 and c['new_total_cap']==365 and c['total_cap']==365 and c['new_deadline_seconds']==600
    assert c['max_hidden_pairs']==8 and c['hidden_total_cap']==80 and c['hidden_step_cap']==40 and c['newton_steps_max']==10
    assert c['dense_assemblies_max']==50 and c['tangent_products_max']==1000
    assert (c['cap'],c['deadline_seconds'])==base.PHASE_LIMITS[phase]


def main(args):
    started=time.monotonic();torch.set_num_threads(1);torch.set_num_interop_threads(1)
    c=json.loads(args.contract.read_text());validate_contract(c,args.phase)
    for entry in c.get('files',[]):
        p=Path(entry['path']);assert p.stat().st_size==entry['bytes'] and base.sha(p)==entry['sha256']
    assert not args.out.exists();device=torch.device(args.device);assert device.type=='cuda' and torch.cuda.is_available()
    args.out.mkdir(parents=True);torch.cuda.reset_peak_memory_stats()
    base.dump(args.out/'receipt.json',allocation(dict(protocol=PROTOCOL,commit=c['commit'],run_id=c['run_id'],phase=args.phase,
        pid=os.getpid(),host=os.uname().nodename,command=sys.argv,CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
        started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),history_commits=0,rollout_steps=0)))
    try:
        result=run_state(c['states'][0],args.out/'c20_s4',device,args.phase,started);base.dump(args.out/'rows.json',[result])
        if args.phase=='probe':base.dump(args.out/'probe_pass.json',{**result,'status':'passed','peak_allocated':torch.cuda.max_memory_allocated()})
        base.dump(args.out/'complete.json',dict(status='completed' if result['status'] in ['completed','probe_passed'] else 'partial',phase=args.phase,states=1))
    except Exception as err:
        base.dump(args.out/'failure.json',dict(type=type(err).__name__,message=str(err),history_commits=0));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--contract',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['probe','production'],required=True);p.add_argument('--device',default='cuda');main(p.parse_args())
