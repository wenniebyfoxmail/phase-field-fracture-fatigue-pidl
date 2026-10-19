#!/usr/bin/env python3
"""Reuse the exact saved actual Phi, then at most two hidden/head pairs.

Full CURRENT401-feature design is reconditioned once per hidden change at the
existing numerical cutoff. No fixed old span, ridge, rank search, FEM-error
selection, fatigue update or coupled rollout. Only actually verified chronological
energy/contract-accepted checkpoints survive interruption.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import shutil
from pathlib import Path
import sys
import time
import numpy as np
import torch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_pidl_energy_head import conditioned_basis,ReducedElastic
from run_pidl_head_newton import (JournalBudget,Work as CoreWork,linear_solve,tangent_contract,
    newton_solve,readout,evaluated,BudgetStop,TangentFailure,GTOL)
from run_pidl_hidden_newton import (HiddenTangent,hidden_microblock,
    snapshot,hidden_change,save_checkpoint,hidden_digest)
from run_pidl_head_readout_audit import raw_network_force,state_digest
from run_pidl_learned_head_newton import hard_head_failure,install_uv_head
from run_pidl_block_diagnosis import LocalProblem,make_smooth,sha,dump,tensor_hash
from compute_energy import compute_energy

PROTOCOL='S04-E011-PERSISTED-PHI-HIDDEN-NEWTON-r1'
SOURCE_ENERGY=.005268400005223913
OPTIMIZER_SCALE=.011216514978623431
PHASE_LIMITS={'probe':(40,60.),'production':(325,540.)}
UV_REALIZATION_TOLERANCE=1e-10


class PhaseWork(CoreWork):
    """No fresh SVD/assembly after the phase's ordinary evaluation allowance."""
    def check(self):
        super().check()
        if len(self.budget.trace)>=self.budget.cap-1:
            raise BudgetStop('evaluation_budget')


def global_microblock_stop(stop):
    return stop in {'evaluation_budget','wall_deadline','dense_assembly_budget','tangent_product_budget'}


def phase_budget(folder,phase,start_time=None):
    budget=JournalBudget(folder)
    budget.cap,budget.seconds=PHASE_LIMITS[phase]
    if start_time is not None:budget.start=start_time
    return budget


def verify_source_fields(fields,path):
    with np.load(path,allow_pickle=False) as z:
        errors={k:float(np.max(abs(fields[k]-z[k]))) for k in ['u','v','d']}
    assert max(errors.values())<=1e-12,('initial source-field mismatch',errors)
    return errors


def build_full_space(field,problem,work):
    work.check()
    with torch.no_grad():
        features=field.net.encode(problem.x)
        bubble=((problem.x[:,1]+.5)*(.5-problem.x[:,1])).cpu().numpy()
        head=torch.cat((field.net.output_layer.weight[:2],field.net.output_layer.bias[:2,None]),dim=1).cpu().numpy()
    transform,phi,info=conditioned_basis(features.cpu().numpy(),problem.mass.cpu().numpy(),bubble,.11999988)
    del features
    assert transform.shape[0]==401 and transform.shape[1]>0
    work.check()
    info.update(current_full_raw_columns=401,dynamic_current_feature_basis=True,old_restricted_span_used=False,
                fixed_cutoff_policy=True,no_cutoff_search=True,no_extra_sensitivity_solves=True,
                starting_point='current actual UV head plus retained-subspace increment; discarded coefficients unchanged',
                discarded_raw_coefficients_retained_in_current_head=True)
    return dict(transform=transform,phi=torch.as_tensor(phi,device=problem.device,dtype=torch.float64),
                head_start=head,report=info)


def load_actual_space(phi_path,transform_path,head,device,n):
    """No reconstruction/SVD: the actual saved floating-point Phi is the input."""
    phi=np.load(phi_path,allow_pickle=False);transform=np.load(transform_path,allow_pickle=False)
    assert phi.dtype==np.float64 and transform.dtype==np.float64
    assert phi.shape==(n,386) and transform.shape==(401,386)
    assert np.isfinite(phi).all() and np.isfinite(transform).all()
    return dict(transform=transform,phi=torch.as_tensor(phi,device=device),head_start=head,
        report=dict(retained_rank=386,current_full_raw_columns=401,actual_saved_Phi_reused=True,
            initial_Phi_reconstructed=False,initial_SVD_calls=0,source_phi_sha256=sha(phi_path),
            source_transform_sha256=sha(transform_path),ridge=0.,fixed_cutoff_policy=True))


def persist_space(space,folder,field,source_phi=None,source_transform=None):
    folder.mkdir(parents=True)
    if source_phi is None:np.save(folder/'phi.npy',space['phi'].detach().cpu().numpy())
    else:shutil.copyfile(source_phi,folder/'phi.npy')
    if source_transform is None:np.save(folder/'transform.npy',space['transform'])
    else:shutil.copyfile(source_transform,folder/'transform.npy')
    space['basis_ref']=str(folder)
    space['report'].update(phi_path=str(folder/'phi.npy'),phi_sha256=sha(folder/'phi.npy'),
        transform_path=str(folder/'transform.npy'),transform_sha256=sha(folder/'transform.npy'),
        bound_hidden_sha256=hidden_digest(field.net.state_dict()),
        originating_weights_sha256=state_digest(field.net.state_dict()))
    dump(folder/'metadata.json',space['report'])


def persisted_readout(field,problem,span,budget,label,space,final=False):
    # raw_network_force uses budget.begin without final; adapt only the one
    # reserved terminal call locally, without changing the reviewed helper.
    original_begin=budget.begin
    if final:budget.begin=lambda role:original_begin(role,final=True)
    try:fields,gu,gv,obs=raw_network_force(field,problem,budget,label,budget.folder/'readouts')
    finally:budget.begin=original_begin
    u=torch.as_tensor(fields['u'],device=problem.device);v=torch.as_tensor(fields['v'],device=problem.device)
    gu_t=torch.as_tensor(gu,device=problem.device);gv_t=torch.as_tensor(gv,device=problem.device)
    g=torch.cat((space['phi'].T@gu_t,space['phi'].T@gv_t)).cpu().numpy()
    np.save(budget.folder/'readouts'/(label+'_actual_projected_gradient.npy'),g)
    error=(problem.mass*((u-problem.uf).square()+(v-problem.vf).square())).sum()
    norm=(problem.mass*(problem.uf.square()+problem.vf.square())).sum()
    h1=(problem.w*(problem.grad(u-problem.uf).square().sum(2)+problem.grad(v-problem.vf).square().sum(2))).sum()/problem.uv_denom
    obs.update(status='verified',basis_ref=space['basis_ref'],basis_phi_sha256=space['report']['phi_sha256'],
        bound_weights_sha256=state_digest(field.net.state_dict()),conditioned_head_gradient_available=True,
        hidden_sha256=hidden_digest(field.net.state_dict()),
        basis_bound_hidden_sha256=space['report']['bound_hidden_sha256'],
        basis_hidden_match=hidden_digest(field.net.state_dict())==space['report']['bound_hidden_sha256'],
        reduced_gradient_inf=float(abs(g).max()),reduced_gradient_l2=float(np.linalg.norm(g)),
        conditioned_head_gradient_inf=float(abs(g).max()),conditioned_head_gradient_l2=float(np.linalg.norm(g)),
        gradient_inf_tolerance=GTOL,head_stationarity_closed=bool(float(abs(g).max())<=GTOL),
        free_u_l2=float(torch.linalg.vector_norm(torch.cat((gu_t,gv_t))[problem.fu])),
        uv_mass_rel_L2=float(torch.sqrt(error/norm)),uv_H1_rel=float(torch.sqrt(h1)))
    dump(budget.folder/'readouts'/(label+'_actual.json'),obs)
    assert obs['basis_hidden_match'],'actual Phi/hidden-state identity mismatch; observed attempt saved'
    assert np.isfinite(g).all(),'nonfinite projected gradient saved before stop'
    return obs,fields,g


def actual_nonincrease(before,after):
    tolerance=128*np.finfo(float).eps*max(abs(before),abs(after),1e-30)
    return after<=before+tolerance


def linear_realization_error(fields,linear):
    return max(float(np.max(abs(fields['u']-linear[0].detach().cpu().numpy()))),
               float(np.max(abs(fields['v']-linear[1].detach().cpu().numpy()))))


def correct_full_head(field,problem,space,work,budget,folder,stage):
    folder.mkdir();rank=space['transform'].shape[1]
    with torch.no_grad():u,v,_=field.fieldCalculation(problem.x)
    reduced=ReducedElastic(problem,space['phi'],u,v);tangent=HiddenTangent(reduced,work)
    z0=np.zeros(2*rank);e,g=evaluated(reduced,budget,z0,f'head_stage_{stage}_initial')
    h,tr=tangent.matrix(z0)
    fd=tangent_contract(reduced,tangent,h,tr,z0,budget);dump(folder/'tangent_contract.json',fd)
    last,accepted,solver=newton_solve(reduced,tangent,budget,dict(z=z0,value=e,gradient=g),h)
    head=space['head_start']+(space['transform']@last['z'].reshape(2,rank).T).T
    hard=hard_head_failure(solver['stop'])
    if not hard:install_uv_head(field.net,head)
    with torch.no_grad():lu,lv=reduced.fields(torch.as_tensor(last['z'],device=problem.device,dtype=torch.float64))
    dump(folder/'basis_ref.json',dict(basis_ref=space['basis_ref'],phi_sha256=space['report']['phi_sha256'],
        transform_sha256=space['report']['transform_sha256']))
    np.savez_compressed(folder/'conditioned_candidate.npz',z=last['z'],head=head,E_el=last['value'],gradient=last['gradient'],
                        u=lu.cpu().numpy(),v=lv.cpu().numpy())
    dump(folder/'basis.json',space['report']);dump(folder/'accepted.json',accepted);dump(folder/'solver.json',solver)
    return dict(stage=stage,solver=solver,hard_failure=hard,conditioned_E_el=last['value'],
        conditioned_gradient_inf=float(abs(last['gradient']).max()),actual_endpoint_retained=False,accepted=accepted),last['gradient'],(lu,lv)


def frozen_checks(field,problem,start,anchor,physical):
    ending=field.net.state_dict()
    assert torch.equal(ending['output_layer.weight'][2:],start['output_layer.weight'][2:])
    assert torch.equal(ending['output_layer.bias'][2:],start['output_layer.bias'][2:])
    assert anchor=={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
    assert physical=={n:tensor_hash(p) for n,p in [('d',problem.df),('lower',problem.hist),('f',problem.f)]}


def restore_verified(field,last):
    field.net.load_state_dict(last['state'])
    return last['space']


def run_state(item,out,device,phase,start_time=None):
    out.mkdir();(out/'readouts').mkdir();budget=phase_budget(out,phase,start_time);work=PhaseWork(budget)
    assert item['cycle']==20 and item['substep']==4 and item['step']==99
    assert 'source_fields' in item and 'source_fields_sha256' in item
    assert sha(item['source_fields'])==item['source_fields_sha256']
    assert sha(item['source_phi'])==item['source_phi_sha256']
    assert sha(item['source_transform'])==item['source_transform_sha256']
    assert not any(k in item for k in ['basis','old_basis','restricted_span'])
    data=dict(np.load(item['input'],allow_pickle=False));problem=LocalProblem(data,device)
    original=torch.load(item['original_model'],map_location=device,weights_only=True)
    initial=torch.load(item['initial_model'],map_location=device,weights_only=True)
    field=make_smooth(original,problem);field.net.load_state_dict(initial);field.net.requires_grad_(False)
    assert not field.williams_enabled and not field.ansatz_enabled and not field.exact_bc_enabled and not field.symmetry_prior
    start=snapshot(field.net);anchor={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
    physical={n:tensor_hash(p) for n,p in [('d',problem.df),('lower',problem.hist),('f',problem.f)]}
    identity=np.eye(401)
    head=torch.cat((field.net.output_layer.weight[:2],field.net.output_layer.bias[:2,None]),dim=1).detach().cpu().numpy()
    space=load_actual_space(item['source_phi'],item['source_transform'],head,device,problem.n)
    persist_space(space,out/'bases'/'initial',field,item['source_phi'],item['source_transform'])
    obs,fields,initial_g=persisted_readout(field,problem,identity,budget,'initial_learned_head',space)
    with np.load(item['source_fields'],allow_pickle=False) as z:
        source_errors={k:float(np.max(abs(fields[k]-z[k]))) for k in ['u','v','d']}
    source_passed=max(source_errors.values())<=1e-12 and abs(obs['E_el']-SOURCE_ENERGY)<=1e-10 and obs['reduced_gradient_inf']<=GTOL
    source_record=dict(source_energy=SOURCE_ENERGY,actual_energy=obs['E_el'],energy_abs_error=abs(obs['E_el']-SOURCE_ENERGY),
        actual_current_head_gradient_inf=obs['reduced_gradient_inf'],initial_rank=386,source_fields_maxabs=source_errors,
        source_fields_path=item['source_fields'],source_fields_sha256=item['source_fields_sha256'],passed=bool(source_passed))
    dump(out/'source_reproduction.json',source_record)
    if phase=='production':assert source_passed,'source admission failed; actual fields/forces/projected gradient already saved'
    dump(out/'initial_basis.json',space['report'])
    source=budget.begin('source_energy_contract')
    with torch.no_grad():
        u,v,_=field.fieldCalculation(problem.x)
        oracle=compute_energy(problem.x,u,v,problem.df,problem.hist,problem.mat,problem.model,problem.area,problem.cells,
            f_fatigue=problem.f,irreversibility_penalty_cfg={'enable':True,'mode':'fem_gp_q4'})[0]
    source_error=abs(float(oracle)-obs['E_el']);assert source_error<=1e-10
    source.update(completed=True,E_el=float(oracle),source_error=source_error)
    native=budget.begin('native_FEM_force_contract')
    fem,_=readout(problem,problem.uf,problem.vf,space['phi'],native=data['ru_fem']);assert fem['free_u_l2']<1e-8
    native.update(completed=True,**fem)
    if phase=='probe':
        obs['source_field_maxabs']=source_errors;obs['source_energy_abs_error']=abs(obs['E_el']-SOURCE_ENERGY)
        repetitions=[obs]
        for index in [1,2]:
            observed,observed_fields,_=persisted_readout(field,problem,identity,budget,f'probe_repeat_{index}',space)
            with np.load(item['source_fields'],allow_pickle=False) as z:
                observed['source_field_maxabs']={k:float(np.max(abs(observed_fields[k]-z[k]))) for k in ['u','v','d']}
            observed['source_energy_abs_error']=abs(observed['E_el']-SOURCE_ENERGY)
            repetitions.append(observed);dump(out/'probe_repetitions.json',repetitions)
            assert all(torch.equal(p,start[n]) for n,p in field.net.state_dict().items())
        all_passed=all(max(r['source_field_maxabs'].values())<=1e-12 and r['source_energy_abs_error']<=1e-10 and r['reduced_gradient_inf']<=GTOL for r in repetitions)
        dump(out/'probe_admission.json',dict(all_three_same_actual_Phi_passed=bool(all_passed),gradient_inf_tolerance=GTOL,
            gradient_inf_spread=float(np.ptp([r['reduced_gradient_inf'] for r in repetitions])),
            spread_is_diagnostic_not_new_threshold=True))
        assert all_passed,'same actual Phi probe failed original source/gradient contracts; all three attempts preserved'
        with torch.no_grad():u,v,_=field.fieldCalculation(problem.x)
        reduced=ReducedElastic(problem,space['phi'],u,v);tangent=HiddenTangent(reduced,work)
        z=np.zeros(2*space['transform'].shape[1]);e,g=evaluated(reduced,budget,z,'probe_reduced_gradient')
        h,tr=tangent.matrix(z);fd=tangent_contract(reduced,tangent,h,tr,z,budget)
        direction,solve=linear_solve(h,g,work)
        assert all(torch.equal(p,start[n]) for n,p in field.net.state_dict().items())
        frozen_checks(field,problem,start,anchor,physical)
        free,total=torch.cuda.mem_get_info();assert free>=3*1024**3
        result=dict(status='probe_passed',evaluations=len(budget.trace),cap=budget.cap,deadline_seconds=budget.seconds,
            prior_evaluations=35,new_probe_production_cap=365,total_prior_plus_new_cap=400,
            new_probe_production_deadline_seconds=600,prior_elapsed_seconds=None,cumulative_elapsed_seconds_claim=False,
            elapsed_seconds=time.monotonic()-budget.start,hidden_backward=True,optimizer_updates=0,parameter_updates=0,
            actual_tangent_assembly_and_solve=True,dense_assemblies=work.assemblies,linear_solves=work.solves,
            explicit_tangent_vector_products=work.products,solve=solve,free_VRAM=free,total_VRAM=total,
            source_reproduction=source_record,actual_Phi_repetition_readouts=repetitions,all_three_same_Phi_readouts_passed=True,initial_rank=386,history_commits=0,rollout_steps=0,
            damage_output_row_unchanged=True,Smooth_B0_anchor_unchanged=True,mechanical_damage_exact_FEM=True,boundary_unchanged=True)
        dump(out/'tangent_contract.json',fd);dump(out/'raw_gradient_probe.json',obs);dump(out/'result.json',result);return result
    gradient_rows=[obs];accepted=[];stages=[]
    save_checkpoint(out/'checkpoints'/'initial',field,obs,fields)
    last=dict(state=snapshot(field.net),result=obs,fields=fields,label='initial',space=space)
    reason='two_hidden_head_pairs_completed'
    try:
        for block in [1,2]:
            work.check()
            before_block=snapshot(field.net);before_space=space;before_energy=last['result']['E_el']
            def objective():
                u,v,_=field.fieldCalculation(problem.x);return problem.parts(u,v,problem.df)[0]
            micro=hidden_microblock(field.net,objective,budget,before_energy,OPTIMIZER_SCALE,block,max_calls=40)
            for entry in micro['accepted']:entry['retained_in_outer']=False
            accepted.extend(micro['accepted']);stages.append(dict(block=block,hidden=micro,rolled_back=False))
            if micro['hard_failure']:
                field.net.load_state_dict(before_block);space=before_space;stages[-1]['rolled_back']=True
                reason='hard_hidden_failure_'+micro['stop'];break
            if global_microblock_stop(micro['stop']):
                # The core restores its last completed optimizer step, but no
                # further SVD/readout is allowed to qualify that new hidden state.
                # Keep the previous whole actually verified checkpoint instead.
                space=restore_verified(field,last);stages[-1]['rolled_back']=True
                stages[-1]['retained_checkpoint']=last['label'];reason=micro['stop'];break
            space=build_full_space(field,problem,work)
            persist_space(space,out/'bases'/f'hidden_{block}',field)
            obs,fields,_=persisted_readout(field,problem,identity,budget,f'hidden_block_{block}',space)
            if not actual_nonincrease(before_energy,obs['E_el']):
                field.net.load_state_dict(before_block);space=before_space;stages[-1]['rolled_back']=True
                reason='hidden_actual_energy_increase_rollback';break
            frozen_checks(field,problem,start,anchor,physical)
            gradient_rows.append(obs);save_checkpoint(out/'checkpoints'/f'hidden_{block}',field,obs,fields)
            last=dict(state=snapshot(field.net),result=obs,fields=fields,label=f'hidden_{block}',space=space)
            for entry in micro['accepted']:entry['retained_in_outer']=True
            head_before=snapshot(field.net);energy_before_head=obs['E_el']
            correction,cg,linear=correct_full_head(field,problem,space,work,budget,out/f'head_stage_{block}',block)
            stages[-1]['head']=correction
            if correction['hard_failure']:
                field.net.load_state_dict(head_before);reason='hard_head_failure_'+correction['solver']['stop'];break
            obs,fields,ag=persisted_readout(field,problem,identity,budget,f'head_correction_{block}',space)
            if not actual_nonincrease(energy_before_head,obs['E_el']):
                field.net.load_state_dict(head_before);correction['actual_energy_rollback']=True
                reason='head_actual_energy_increase_rollback';break
            frozen_checks(field,problem,start,anchor,physical)
            realization_error=linear_realization_error(fields,linear)
            correction.update(linear_vs_actual_uv_maxabs=realization_error,
                UV_realization_tolerance=UV_REALIZATION_TOLERANCE,
                actual_realization_candidate=obs,
                UV_realization_contract_passed=bool(realization_error<=UV_REALIZATION_TOLERANCE))
            if realization_error>UV_REALIZATION_TOLERANCE:
                field.net.load_state_dict(head_before)
                correction['head_realization_contract_failure']=True
                correction['actual_endpoint_retained']=False
                reason='head_realization_contract_failure';break
            correction.update(actual_endpoint_retained=True,actual_network=obs,
                actual_minus_conditioned_energy=obs['E_el']-correction['conditioned_E_el'],
                actual_minus_conditioned_gradient_inf=float(np.max(abs(ag-cg))))
            gradient_rows.append(obs);save_checkpoint(out/'checkpoints'/f'head_{block}',field,obs,fields)
            last=dict(state=snapshot(field.net),result=obs,fields=fields,label=f'head_{block}',space=space)
            for entry in correction['accepted']:accepted.append({**entry,'kind':'conditioned_head_inner','block':block,'actual_energy_verified':False})
            dump(out/'gradient_readouts.json',gradient_rows);dump(out/'accepted.json',accepted);dump(out/'stages.json',stages)
    except (BudgetStop,TangentFailure) as err:
        reason=str(err);space=restore_verified(field,last)
        if stages:stages[-1]['interrupted']=reason;stages[-1]['retained_checkpoint']=last['label']
    final=None;final_fields=None
    try:
        final,final_fields,_=persisted_readout(field,problem,identity,budget,'final',space,final=True)
        if not actual_nonincrease(last['result']['E_el'],final['E_el']):
            raise TangentFailure('terminal actual energy differs from exact last verified state')
        gradient_rows.append(final)
    except BudgetStop as err:reason+='; terminal_missing_'+str(err)
    frozen_checks(field,problem,start,anchor,physical)
    if final is None:space=restore_verified(field,last)
    ending=snapshot(field.net);visible_fields=final_fields if final is not None else last['fields']
    np.savez_compressed(out/'fields.npz',**visible_fields);torch.save(field.net.state_dict(),out/'accepted_network.pt')
    actual_inf=final['reduced_gradient_inf'] if final else None
    result=dict(status='completed' if final else 'partial_terminal_readout_missing',cycle=20,substep=4,step=99,
        source_reproduction=source_record,initial=gradient_rows[0],actual_network=final,
        last_verified_network=last['result'],last_verified_checkpoint=last['label'],
        E_el=final['E_el'] if final else None,free_u_l2=final['free_u_l2'] if final else None,
        uv_mass_rel_L2=final['uv_mass_rel_L2'] if final else None,uv_H1_rel=final['uv_H1_rel'] if final else None,
        gradient_readouts=gradient_rows,hidden_change=hidden_change(start,ending),optimizer_scale=OPTIMIZER_SCALE,
        head_stationarity_closed=bool(actual_inf is not None and actual_inf<=GTOL),gradient_inf_tolerance=GTOL,
        hidden_blocks=len(stages),hidden_block_cap=40,max_hidden_blocks=2,stop=reason,
        evaluations=len(budget.trace),cap=budget.cap,deadline_seconds=budget.seconds,
        prior_evaluations=35,new_probe_production_cap=365,total_prior_plus_new_cap=400,new_probe_production_deadline_seconds=600,
        prior_elapsed_seconds=None,cumulative_elapsed_seconds_claim=False,
        elapsed_seconds=time.monotonic()-budget.start,dense_assemblies=work.assemblies,
        explicit_tangent_vector_products=work.products,linear_solves=work.solves,current_raw_columns=401,
        dynamic_current_feature_basis=True,initial_rank=386,final_rank=space['transform'].shape[1],old_restricted_span_used=False,
        selection_rule='last chronological actual energy and contract accepted checkpoint; never FEM-error selection',
        damage_output_row_unchanged=True,Smooth_B0_anchor_unchanged=True,mechanical_damage_exact_FEM=True,boundary_unchanged=True,
        NN_damage_field_fixed_claim=False,history_commits=0,rollout_steps=0,ridge=0.,whole_network_capacity_claim=False,true_variable_projection=False)
    dump(out/'result.json',result);dump(out/'gradient_readouts.json',gradient_rows);dump(out/'accepted.json',accepted);dump(out/'stages.json',stages);dump(out/'trace.json',budget.trace)
    return result


def validate_contract(contract,phase):
    assert contract['protocol']==PROTOCOL and len(contract['states'])==1
    assert contract['prior_evaluations']==35 and contract['new_total_cap']==365 and contract['total_cap']==400
    assert contract['new_deadline_seconds']==600
    assert contract['max_hidden_blocks']==2 and contract['hidden_block_cap']==40
    assert contract['dense_assemblies_max']==50 and contract['tangent_products_max']==1000
    assert (contract['cap'],contract['deadline_seconds'])==PHASE_LIMITS[phase]


def main(args):
    start_time=time.monotonic()
    torch.set_num_threads(1);torch.set_num_interop_threads(1);assert not args.out.exists()
    contract=json.loads(args.contract.read_text());validate_contract(contract,args.phase)
    for entry in contract.get('files',[]):
        p=Path(entry['path']);assert p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256']
    device=torch.device(args.device);assert device.type=='cuda' and torch.cuda.is_available(),'No Mac/CPU optimization'
    args.out.mkdir(parents=True);torch.cuda.reset_peak_memory_stats()
    dump(args.out/'receipt.json',dict(protocol=PROTOCOL,commit=contract['commit'],run_id=contract['run_id'],phase=args.phase,
        pid=os.getpid(),host=os.uname().nodename,command=sys.argv,CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
        started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),history_commits=0,rollout_steps=0,
        prior_evaluations=35,new_probe_production_cap=365,total_prior_plus_new_cap=400,
        new_probe_production_deadline_seconds=600,prior_elapsed_seconds=None,cumulative_elapsed_seconds_claim=False))
    try:
        result=run_state(contract['states'][0],args.out/'c20_s4',device,args.phase,start_time);dump(args.out/'rows.json',[result])
        if args.phase=='probe':dump(args.out/'probe_pass.json',{**result,'status':'passed','peak_allocated':torch.cuda.max_memory_allocated()})
        dump(args.out/'complete.json',dict(status='completed' if result['status'] in ['completed','probe_passed'] else 'partial',states=1,phase=args.phase,history_commits=0,rollout_steps=0))
    except Exception as err:
        dump(args.out/'failure.json',dict(type=type(err).__name__,message=str(err),history_commits=0));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--phase',choices=['probe','production'],required=True);parser.add_argument('--device',default='cuda');main(parser.parse_args())
