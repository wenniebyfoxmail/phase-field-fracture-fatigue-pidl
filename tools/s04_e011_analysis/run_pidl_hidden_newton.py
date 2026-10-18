#!/usr/bin/env python3
"""Bounded alternating hidden-only LBFGS / fixed-raw-span Newton, c20s4.

Hidden trials hold the UV head fixed. This is not a profiled/variable-projection
optimizer. All reported parameter gradients are of RAW Eel, even when hidden
LBFGS uses the fixed E(theta0) scaling. Physical damage is always frozen FEM d;
the unused network damage field may change through the shared hidden layers.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import numpy as np
from scipy.linalg import svd
import torch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_pidl_head_newton import (JournalBudget,Work,Tangent,assemble_blocks,linear_solve,
    tangent_contract,newton_solve,readout,evaluated,BudgetStop,TangentFailure,GTOL)
from run_pidl_energy_head import ReducedElastic
from run_pidl_block_diagnosis import LocalProblem,make_smooth,sha,dump,tensor_hash
from compute_energy import compute_energy

PROTOCOL='S04-E011-HIDDEN-NEWTON-r1'


class RankLoss(RuntimeError):
    pass


def snapshot(net):return {n:q.detach().clone() for n,q in net.state_dict().items()}
def hidden_named(net):return [(n,p) for n,p in net.named_parameters() if not n.startswith('output_layer.')]
def hidden_digest(state):
    h=hashlib.sha256()
    for n in sorted(state):
        if not n.startswith('output_layer.'):
            a=state[n].detach().cpu().contiguous().numpy()
            h.update(n.encode());h.update(str(a.dtype).encode());h.update(str(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()
def hidden_change(before,after):
    names=[n for n in before if not n.startswith('output_layer.')]
    changed=sum(not torch.equal(before[n],after[n]) for n in names)
    return dict(before_sha256=hidden_digest(before),after_sha256=hidden_digest(after),
                maxabs=max(float((before[n]-after[n]).abs().max()) for n in names),
                changed=bool(changed),changed_tensors=changed,total_hidden_tensors=len(names))


def fixed_raw_span(old_transform):
    t=np.asarray(old_transform,dtype=np.float64)
    lengths=np.linalg.norm(t,axis=0)
    if t.ndim!=2 or not np.isfinite(t).all() or np.any(lengths<=0):raise ValueError('invalid old transform')
    s=t/lengths
    error=float(np.max(abs(s.T@s-np.eye(s.shape[1]))))
    if error>1e-8:raise ValueError('old transform normalized columns are not orthonormal')
    return s,error


def whiten_fixed_span(features,mass,bubble,span,load=.11999988):
    """Recondition ALL raw-span columns. A rank miss aborts, never truncates."""
    h=np.asarray(features,dtype=np.float64);w=np.asarray(mass,dtype=np.float64)
    raw=float(load)*np.asarray(bubble)[:,None]*np.column_stack((h,np.ones(len(h))))
    restricted=raw@span
    _,singular,vt=svd(np.sqrt(w)[:,None]*restricted,full_matrices=False,lapack_driver='gesdd')
    cutoff=np.finfo(float).eps*max(restricted.shape)*singular[0]
    if len(singular)!=span.shape[1] or np.any(singular<=cutoff):
        raise RankLoss(f'full raw span not numerically resolvable: {int(np.sum(singular>cutoff))}/{span.shape[1]}')
    rotation=vt.T/singular[None,:]
    transform=span@rotation;phi=restricted@rotation
    assert np.isfinite(transform).all() and np.isfinite(phi).all()
    return transform,phi,dict(retained_rank=span.shape[1],singular_values=singular.tolist(),
        numerical_cutoff=float(cutoff),condition_number=float(singular[0]/singular[-1]),
        ridge=0.,further_rank_truncation=False,fixed_raw_span=True,
        whitened_gram_maxabs_error=float(np.max(abs(phi.T@(w[:,None]*phi)-np.eye(span.shape[1])))))


class HiddenTangent(Tangent):
    """Same reviewed assembly, with the NEW global fifty-assembly budget."""
    def matrix(self,z):
        self.work.check()
        if self.work.assemblies>=50:raise BudgetStop('dense_assembly_budget')
        self.work.assemblies+=1;t0=time.monotonic();tr=self.trace_at(z)
        h,asym=assemble_blocks(self.gx,self.gy,self.w,self.g,tr)
        self.work.records.append(dict(assembly=self.work.assemblies,shape=list(h.shape),
            gradient_basis_shape=list(self.gx.shape),quadrature_points=len(self.w),
            dense_assembly_includes_all_columns=True,column_equivalent_tangent_actions=h.shape[1],
            trace_positive=int((tr>0).sum()),trace_negative=int((tr<0).sum()),trace_zero=int((tr==0).sum()),
            unsymmetrized_maxabs=asym,seconds=time.monotonic()-t0,ridge=0.,further_rank_truncation=False))
        self.work.checkpoint();return h,tr


def build_space(field,problem,span,work):
    work.check()
    with torch.no_grad():
        features=field.net.encode(problem.x).cpu().numpy()
        bubble=((problem.x[:,1]+.5)*(.5-problem.x[:,1])).cpu().numpy()
    transform,phi,info=whiten_fixed_span(features,problem.mass.cpu().numpy(),bubble,span)
    work.check()
    return dict(transform=transform,phi=torch.as_tensor(phi,device=problem.device,dtype=torch.float64),
                report=info,hidden_sha256=hidden_digest(field.net.state_dict()))


def raw_network_readout(field,problem,span,budget,label,space=None,final=False,old_phi=None):
    """ONE graph/energy call for all parameter AND nodal field gradients."""
    row=budget.begin('raw_network_gradient_'+label,final=final)
    named=list(field.net.named_parameters());flags=[p.requires_grad for _,p in named]
    try:
        for _,p in named:p.requires_grad_(True)
        field.net.zero_grad(set_to_none=True)
        u,v,unused_d=field.fieldCalculation(problem.x)
        value=problem.parts(u,v,problem.df)[0]
        grads=torch.autograd.grad(value,tuple(p for _,p in named)+(u,v),allow_unused=True)
        hidden=[];uv=[]
        for (name,p),g in zip(named,grads[:-2]):
            g=torch.zeros_like(p) if g is None else g
            assert torch.isfinite(g).all()
            (uv if name.startswith('output_layer.') else hidden).append(g[:2].reshape(-1) if name.startswith('output_layer.') else g.reshape(-1))
        hg=torch.cat(hidden);ug=torch.cat(uv);gu,gv=grads[-2:]
        full=torch.cat((gu,gv));raw_span=torch.as_tensor(span,device=u.device,dtype=torch.float64)
        # Output-weight rows and bias gradient are assembled in head-row order.
        gd={n:(torch.zeros_like(p) if g is None else g) for (n,p),g in zip(named,grads[:-2])}
        raw_head_gradient=torch.cat((gd['output_layer.weight'][:2],gd['output_layer.bias'][:2,None]),dim=1)
        sg=(raw_head_gradient@raw_span).reshape(-1)
        conditioned=torch.cat((space['phi'].T@gu,space['phi'].T@gv)) if space is not None else None
        error=(problem.mass*((u-problem.uf).square()+(v-problem.vf).square())).sum()
        norm=(problem.mass*(problem.uf.square()+problem.vf.square())).sum()
        h1=(problem.w*(problem.grad(u-problem.uf).square().sum(2)+problem.grad(v-problem.vf).square().sum(2))).sum()/problem.uv_denom
        result=dict(label=label,status='verified',objective='raw_Eel',E_el=float(value.detach()),
            hidden_gradient_l2=float(torch.linalg.vector_norm(hg)),hidden_gradient_inf=float(hg.abs().max()),
            uv_head_gradient_l2=float(torch.linalg.vector_norm(ug)),uv_head_gradient_inf=float(ug.abs().max()),
            raw_span_head_gradient_l2=float(torch.linalg.vector_norm(sg)),raw_span_head_gradient_inf=float(sg.abs().max()),
            conditioned_head_gradient_l2=float(torch.linalg.vector_norm(conditioned)) if conditioned is not None else None,
            conditioned_head_gradient_inf=float(conditioned.abs().max()) if conditioned is not None else None,
            reduced_gradient_l2=float(torch.linalg.vector_norm(conditioned)) if conditioned is not None else None,
            reduced_gradient_inf=float(conditioned.abs().max()) if conditioned is not None else None,
            free_u_l2=float(torch.linalg.vector_norm(full[problem.fu])),uv_mass_rel_L2=float(torch.sqrt(error/norm)),
            uv_H1_rel=float(torch.sqrt(h1)),unused_NN_damage_min=float(unused_d.min()),unused_NN_damage_max=float(unused_d.max()))
        result['conditioned_head_gradient_available']=space is not None
        result['conditioned_head_gradient_unavailable_reason']=None if space is not None else 'No full-rank current conditioning supplied'
        if old_phi is not None:
            old_gradient=torch.cat((old_phi.T@gu,old_phi.T@gv))
            result['old_fixed_basis_head_gradient_inf']=float(old_gradient.abs().max())
        assert all(v is None or isinstance(v,str) or np.isfinite(v) for v in result.values())
        fields=dict(u=u.detach().cpu().numpy(),v=v.detach().cpu().numpy(),d=problem.df.detach().cpu().numpy())
        row.update(completed=True,E_el=result['E_el'],label=label)
        dump(budget.folder/'trace.json',budget.trace)
        return result,fields,conditioned.detach().cpu().numpy() if conditioned is not None else None
    finally:
        for (_,p),flag in zip(named,flags):p.requires_grad_(flag)
        field.net.zero_grad(set_to_none=True)


def hidden_microblock(net,objective,budget,initial_raw,scale,block,max_calls=40):
    """Whole-step acceptance only; interrupted strong-Wolfe trials roll back."""
    parameters=[p for _,p in hidden_named(net)];allflags=[p.requires_grad for p in net.parameters()]
    head_before={n:p.detach().clone() for n,p in net.named_parameters() if n.startswith('output_layer.')}
    for n,p in net.named_parameters():p.requires_grad_(not n.startswith('output_layer.'))
    accepted=[];last=snapshot(net);last_energy=float(initial_raw);used=0;stop='hidden_block_budget';hard_failure=False
    optimizer=torch.optim.LBFGS(parameters,lr=1.,max_iter=1,max_eval=20,history_size=5,
        tolerance_grad=0.,tolerance_change=0.,line_search_fn='strong_wolfe')
    def evaluate(backward,endpoint=False):
        nonlocal used
        if used>=max_calls-(0 if endpoint else 1):raise BudgetStop('hidden_block_budget')
        trace=budget.begin('hidden_LBFGS_closure' if backward else 'hidden_completed_step_readout');used+=1
        optimizer.zero_grad(set_to_none=True);raw=objective();assert torch.isfinite(raw)
        loss=raw/scale
        if backward:
            loss.backward();assert all(p.grad is None or torch.isfinite(p.grad).all() for p in parameters)
        trace.update(completed=True,block=block,block_evaluation=used,E_el=float(raw.detach()),optimizer_loss=float(loss.detach()),optimizer_scale=scale)
        dump(budget.folder/'trace.json',budget.trace);return loss
    try:
        while used<max_calls-1:
            before=snapshot(net)
            optimizer.step(lambda:evaluate(True))
            energy=float(evaluate(False,endpoint=True).detach())*scale
            eps=128*np.finfo(float).eps*max(abs(last_energy),abs(energy),1e-30)
            if energy>last_energy+eps:raise TangentFailure('completed_hidden_step_energy_increase')
            delta=max(float((p.detach()-before[n]).abs().max()) for n,p in hidden_named(net))
            last=snapshot(net);last_energy=energy
            accepted.append(dict(kind='hidden_actual',block=block,accepted=len(accepted)+1,evaluations=len(budget.trace),
                                 E_el=energy,hidden_parameter_delta_inf=delta,actual_energy_verified=True))
            if delta==0:stop='hidden_exact_parameter_stagnation';break
    except BudgetStop as err:stop=str(err)
    except TangentFailure as err:stop=str(err);hard_failure=True
    finally:
        net.load_state_dict(last)
        for p,flag in zip(net.parameters(),allflags):p.requires_grad_(flag)
        for n,p in net.named_parameters():
            if n in head_before:assert torch.equal(p,head_before[n])
    return dict(stop=stop,evaluations=used,cap=max_calls,accepted=accepted,E_el=last_energy,
                hard_failure=hard_failure,optimizer='hidden-only Torch LBFGS strong_wolfe, history5 reset per block',optimizer_scale=scale,raw_gradient_readouts_separate=True)


def save_checkpoint(folder,field,result,fields):
    folder.mkdir(parents=True,exist_ok=False)
    dump(folder/'result.json',result);np.savez_compressed(folder/'fields.npz',**fields)
    torch.save(field.net.state_dict(),folder/'accepted_network.pt')


def correct_head(field,problem,span,work,budget,folder,stage,space):
    """Current head is the increment origin; never project it or warm-start z."""
    folder.mkdir();r=span.shape[1]
    with torch.no_grad():
        u0,v0,_=field.fieldCalculation(problem.x)
        head=torch.cat((field.net.output_layer.weight[:2],field.net.output_layer.bias[:2,None]),dim=1).cpu().numpy()
    reduced=ReducedElastic(problem,space['phi'],u0,v0);tangent=HiddenTangent(reduced,work)
    z0=np.zeros(2*r);e,g=evaluated(reduced,budget,z0,'head_stage_initial_'+str(stage));last=dict(z=z0,value=e,gradient=g)
    h,tr=tangent.matrix(z0)
    fd=tangent_contract(reduced,tangent,h,tr,z0,budget);dump(folder/'tangent_contract.json',fd)
    last,accepted,solver=newton_solve(reduced,tangent,budget,last,h)
    hard_failure=solver['stop'].startswith(('nonpositive_or_numerically_singular_tangent',
        'dense_linear_solve_residual','Newton_direction_not_descent','Armijo_line_search_not_closed'))
    new_head=head+(space['transform']@last['z'].reshape(2,r).T).T
    if not hard_failure:
        with torch.no_grad():
            q=torch.as_tensor(new_head,device=problem.device,dtype=torch.float64)
            field.net.output_layer.weight[:2].copy_(q[:,:-1]);field.net.output_layer.bias[:2].copy_(q[:,-1])
    dump(folder/'accepted.json',accepted);dump(folder/'solver.json',solver);dump(folder/'basis.json',space['report'])
    np.savez_compressed(folder/'basis.npz',transform=space['transform'],head_start=head,fixed_raw_span=span)
    np.savez_compressed(folder/'reduced_candidate.npz',z=last['z'],head=new_head,gradient=last['gradient'],E_el=last['value'])
    return dict(solver=solver,conditioned_E_el=last['value'],conditioned_gradient_inf=float(abs(last['gradient']).max()),
                accepted=accepted,stage=stage,hard_failure=hard_failure,actual_endpoint_retained=False),last['gradient']


def run_state(item,out,device,phase):
    out.mkdir();budget=JournalBudget(out);work=Work(budget);gradient_rows=[];accepted=[];stages=[]
    assert item['cycle']==20 and item['substep']==4 and item['step']==99
    data=dict(np.load(item['input'],allow_pickle=False));problem=LocalProblem(data,device)
    original=torch.load(item['original_model'],map_location=device,weights_only=True)
    initial=torch.load(item['initial_model'],map_location=device,weights_only=True)
    field=make_smooth(original,problem);field.net.requires_grad_(False)
    original_state=snapshot(field.net);frozen_anchor={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
    for n,p in initial.items():
        if not n.startswith('output_layer.'):assert torch.equal(p.double(),original_state[n])
        elif n in ['output_layer.weight','output_layer.bias']:assert torch.equal(p[2:].double(),original_state[n][2:])
    field.net.load_state_dict(initial);start=snapshot(field.net)
    frozen_physical={n:tensor_hash(p) for n,p in [('d',problem.df),('lower',problem.hist),('f',problem.f)]}
    old=dict(np.load(item['basis'],allow_pickle=False));assert old['transform'].shape==(401,387)
    span,spanerror=fixed_raw_span(old['transform']);spanhash=hashlib.sha256(span.tobytes()).hexdigest()
    with torch.no_grad():
        initial_features=field.net.encode(problem.x).cpu().numpy()
        initial_bubble=((problem.x[:,1]+.5)*(.5-problem.x[:,1])).cpu().numpy()
        initial_design=.11999988*initial_bubble[:,None]*np.column_stack((initial_features,np.ones(problem.n)))
        old_phi=torch.as_tensor(initial_design@old['transform'],device=device,dtype=torch.float64)
    del initial_features,initial_design
    space=build_space(field,problem,span,work)
    if phase=='probe':
        obs,fields,_=raw_network_readout(field,problem,span,budget,'probe_hidden_backward',space)
        with torch.no_grad():u,v,_=field.fieldCalculation(problem.x)
        reduced=ReducedElastic(problem,space['phi'],u,v);tangent=HiddenTangent(reduced,work)
        z=np.zeros(774);e,g=evaluated(reduced,budget,z,'probe_head_gradient');h,tr=tangent.matrix(z)
        fd=tangent_contract(reduced,tangent,h,tr,z,budget);direction,solve=linear_solve(h,g,work)
        assert all(torch.equal(p,start[n]) for n,p in field.net.state_dict().items())
        assert frozen_anchor=={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
        assert frozen_physical=={n:tensor_hash(p) for n,p in [('d',problem.df),('lower',problem.hist),('f',problem.f)]}
        free,total=torch.cuda.mem_get_info();assert free>=3*1024**3
        result=dict(status='probe_passed',evaluations=len(budget.trace),hidden_backward=True,optimizer_updates=0,parameter_updates=0,
                    actual_tangent_assembly_and_solve=True,dense_assemblies=work.assemblies,linear_solves=work.solves,
                    explicit_tangent_vector_products=work.products,solve=solve,free_VRAM=free,total_VRAM=total,
                    fixed_raw_span_rank=387,fixed_raw_span_orthogonality_error=spanerror,history_commits=0,rollout_steps=0,
                    damage_output_row_unchanged=True,Smooth_B0_anchor_unchanged=True,mechanical_damage_exact_FEM=True,boundary_unchanged=True)
        dump(out/'tangent_contract.json',fd);dump(out/'raw_gradient_probe.json',obs);dump(out/'result.json',result);return result
    baseline_labels={b['label'] for b in item['baselines']}
    assert baseline_labels=={'original_theta0','PBD_U_energy','fixed_feature_Newton'}
    optimizer_scale=None;baseline_initial=None;last_verified=None
    for baseline in item['baselines']:
        model=torch.load(baseline['model'],map_location=device,weights_only=True);field.net.load_state_dict(model)
        # Reconditioning is a diagnostic coordinate change only; a comparator
        # rank miss leaves raw gradients valid but conditioned gradient missing.
        missing_reason=None
        try:baseline_space=build_space(field,problem,span,work)
        except RankLoss as err:baseline_space=None;missing_reason=str(err)
        row,fields,_=raw_network_readout(field,problem,span,budget,baseline['label'],baseline_space,
            old_phi=old_phi if baseline['label']=='fixed_feature_Newton' else None)
        if missing_reason:row['conditioned_head_gradient_unavailable_reason']=missing_reason
        gradient_rows.append(row);save_checkpoint(out/'baselines'/baseline['label'],field,row,fields)
        if baseline['label']=='original_theta0':optimizer_scale=row['E_el']
        if baseline['label']=='fixed_feature_Newton':baseline_initial=row
        del baseline_space
    assert optimizer_scale is not None and optimizer_scale>0 and baseline_initial is not None
    field.net.load_state_dict(initial);space=build_space(field,problem,span,work)
    obs,fields,_=raw_network_readout(field,problem,span,budget,'initial_fixed_Newton',space,old_phi=old_phi)
    assert abs(obs['E_el']-.006024051980505792)<=1e-10
    assert obs['old_fixed_basis_head_gradient_inf']<=GTOL, 'accepted fixed-Newton warm start lost its old-basis stationarity'
    del old_phi
    save_checkpoint(out/'checkpoints'/'initial',field,obs,fields)
    last_verified=dict(state=snapshot(field.net),result=obs,fields=fields,label='initial',space=space)
    gradient_rows.append(obs);dump(out/'gradient_readouts.json',gradient_rows)
    row=budget.begin('source_energy_contract')
    with torch.no_grad():u,v,_=field.fieldCalculation(problem.x);oracle=compute_energy(problem.x,u,v,problem.df,problem.hist,problem.mat,problem.model,problem.area,problem.cells,f_fatigue=problem.f,irreversibility_penalty_cfg={'enable':True,'mode':'fem_gp_q4'})[0]
    source_error=abs(float(oracle)-obs['E_el']);assert source_error<=1e-10;row.update(completed=True,E_el=float(oracle),source_error=source_error)
    reason='four_hidden_blocks_completed'
    try:
        for block in range(1,5):
            before_block=snapshot(field.net);before_space=space;before_energy=last_verified['result']['E_el']
            def objective():
                u,v,_=field.fieldCalculation(problem.x);return problem.parts(u,v,problem.df)[0]
            micro=hidden_microblock(field.net,objective,budget,before_energy,optimizer_scale,block)
            for entry in micro['accepted']:entry['retained_in_outer']=False
            accepted.extend(micro['accepted']);stages.append(dict(block=block,hidden=micro,rolled_back=False))
            if micro['hard_failure']:
                field.net.load_state_dict(before_block);space=before_space
                stages[-1]['rolled_back']=True;reason='hard_hidden_failure_'+micro['stop'];break
            # Changed hidden features require a new full-rank conditioning.
            try:space=build_space(field,problem,span,work)
            except RankLoss:
                field.net.load_state_dict(before_block);space=before_space
                stages[-1]['rolled_back']=True;reason='full_rank_reconditioning_failure_rollback';break
            obs,fields,_=raw_network_readout(field,problem,span,budget,f'hidden_block_{block}',space)
            eps=128*np.finfo(float).eps*max(abs(before_energy),abs(obs['E_el']),1e-30)
            if obs['E_el']>before_energy+eps:
                field.net.load_state_dict(before_block);space=before_space;stages[-1]['rolled_back']=True
                reason='hidden_actual_energy_increase_rollback';break
            gradient_rows.append(obs);save_checkpoint(out/'checkpoints'/f'hidden_{block}',field,obs,fields)
            last_verified=dict(state=snapshot(field.net),result=obs,fields=fields,label=f'hidden_{block}',space=space)
            for entry in micro['accepted']:entry['retained_in_outer']=True
            before_head=snapshot(field.net);energy_before_head=obs['E_el']
            corrected,conditioned=correct_head(field,problem,span,work,budget,out/f'head_stage_{block}',block,space)
            stages[-1]['head']=corrected
            if corrected['hard_failure']:
                field.net.load_state_dict(before_head);stages[-1]['head']=corrected
                reason='hard_head_failure_'+corrected['solver']['stop'];break
            obs,fields,actual_gradient=raw_network_readout(field,problem,span,budget,f'head_correction_{block}',space)
            eps=128*np.finfo(float).eps*max(abs(energy_before_head),abs(obs['E_el']),1e-30)
            if obs['E_el']>energy_before_head+eps:
                field.net.load_state_dict(before_head);corrected['actual_energy_rollback']=True
                reason='head_actual_energy_increase_rollback';break
            corrected['actual_endpoint_retained']=True
            corrected['actual_minus_conditioned_gradient_inf']=float(np.max(abs(actual_gradient-conditioned)))
            corrected['actual_minus_conditioned_energy']=obs['E_el']-corrected['conditioned_E_el']
            corrected['actual_network']=obs;stages[-1]['head']=corrected
            gradient_rows.append(obs);save_checkpoint(out/'checkpoints'/f'head_{block}',field,obs,fields)
            last_verified=dict(state=snapshot(field.net),result=obs,fields=fields,label=f'head_{block}',space=space)
            for entry in corrected['accepted']:accepted.append({**entry,'kind':'conditioned_head_inner','block':block,'actual_energy_verified':False})
            dump(out/'gradient_readouts.json',gradient_rows);dump(out/'accepted.json',accepted);dump(out/'stages.json',stages)
    except (BudgetStop,TangentFailure) as err:
        reason=str(err);field.net.load_state_dict(last_verified['state']);space=last_verified['space']
        if stages:stages[-1]['interrupted']=reason;stages[-1]['retained_checkpoint']=last_verified['label']
    # The reserve is a single graph: actual field + raw hidden/head + nodal g.
    final=None;final_fields=None
    try:
        final,final_fields,_=raw_network_readout(field,problem,span,budget,'final',space,final=True)
        gradient_rows.append(final)
    except BudgetStop as err:reason+='; terminal_missing_'+str(err)
    ending=snapshot(field.net);change=hidden_change(start,ending)
    assert torch.equal(ending['output_layer.weight'][2:],start['output_layer.weight'][2:])
    assert torch.equal(ending['output_layer.bias'][2:],start['output_layer.bias'][2:])
    assert frozen_anchor=={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
    assert frozen_physical=={n:tensor_hash(p) for n,p in [('d',problem.df),('lower',problem.hist),('f',problem.f)]}
    assert hashlib.sha256(span.tobytes()).hexdigest()==spanhash
    visible=final if final is not None else last_verified['result'];visible_fields=final_fields if final is not None else last_verified['fields']
    np.savez_compressed(out/'fields.npz',**visible_fields);torch.save(field.net.state_dict() if final else last_verified['state'],out/'accepted_network.pt')
    actual_inf=final['reduced_gradient_inf'] if final else None
    result=dict(status='completed' if final else 'partial_terminal_readout_missing',cycle=20,substep=4,step=99,
        actual_network=final,last_verified_network=last_verified['result'],last_verified_checkpoint=last_verified['label'],
        E_el=final['E_el'] if final else None,free_u_l2=final['free_u_l2'] if final else None,
        uv_mass_rel_L2=final['uv_mass_rel_L2'] if final else None,uv_H1_rel=final['uv_H1_rel'] if final else None,
        hidden_change=change,gradient_readouts=gradient_rows,optimizer_scale=optimizer_scale,
        head_stationarity_closed=bool(actual_inf is not None and actual_inf<=GTOL),gradient_inf_tolerance=GTOL,
        hidden_blocks=len(stages),hidden_block_cap=40,max_hidden_blocks=4,evaluations=len(budget.trace),cap=400,
        deadline_seconds=600.,elapsed_seconds=time.monotonic()-budget.start,dense_assemblies=work.assemblies,
        explicit_tangent_vector_products=work.products,linear_solves=work.solves,stop=reason,
        fixed_raw_span_sha256=spanhash,fixed_raw_span_rank=387,fixed_raw_span_orthogonality_error=spanerror,
        damage_output_row_unchanged=True,Smooth_B0_anchor_unchanged=True,mechanical_damage_exact_FEM=True,
        boundary_unchanged=True,NN_damage_field_fixed_claim=False,history_commits=0,rollout_steps=0,
        ridge=0.,whole_network_capacity_claim=False,true_variable_projection=False)
    dump(out/'result.json',result);dump(out/'gradient_readouts.json',gradient_rows);dump(out/'accepted.json',accepted);dump(out/'stages.json',stages);dump(out/'trace.json',budget.trace)
    return result


def main(args):
    torch.set_num_threads(1);torch.set_num_interop_threads(1);assert not args.out.exists()
    contract=json.loads(args.contract.read_text());assert contract['protocol']==PROTOCOL
    for entry in contract.get('files',[]):
        p=Path(entry['path']);assert p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256']
    device=torch.device(args.device);assert device.type=='cuda' and torch.cuda.is_available(),'No Mac/CPU optimization'
    args.out.mkdir(parents=True);torch.cuda.reset_peak_memory_stats()
    dump(args.out/'receipt.json',dict(protocol=PROTOCOL,commit=contract['commit'],run_id=contract['run_id'],phase=args.phase,pid=os.getpid(),host=os.uname().nodename,
         command=sys.argv,CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),history_commits=0,rollout_steps=0))
    try:
        assert len(contract['states'])==1
        result=run_state(contract['states'][0],args.out/'c20_s4',device,args.phase);dump(args.out/'rows.json',[result])
        if args.phase=='probe':dump(args.out/'probe_pass.json',{**result,'status':'passed','peak_allocated':torch.cuda.max_memory_allocated()})
        dump(args.out/'complete.json',dict(status='completed' if result['status'] in ['completed','probe_passed'] else 'partial',states=1,phase=args.phase,history_commits=0,rollout_steps=0))
    except Exception as err:
        dump(args.out/'failure.json',dict(type=type(err).__name__,message=str(err),history_commits=0));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--phase',choices=['probe','production'],required=True);parser.add_argument('--device',default='cuda');main(parser.parse_args())
