#!/usr/bin/env python3
"""One fixed-hidden Newton UV-head solve starting at the unique PBD c20 model.

Rebuild the FULL current401 raw-feature-plus-bias design; never reuse the old
restricted387-direction span. Only UV output rows may change. No hidden step,
damage solve, history update, rollout, ridge, retry or capacity certificate.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
import time
import numpy as np
import torch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_pidl_energy_head import conditioned_basis,ReducedElastic
from run_pidl_head_newton import (JournalBudget,Work,Tangent,linear_solve,tangent_contract,
    newton_solve,readout,evaluated,BudgetStop,GTOL)
from run_pidl_block_diagnosis import LocalProblem,make_smooth,sha,dump,tensor_hash
from run_pidl_hidden_newton import raw_network_readout,snapshot,hidden_digest
from compute_energy import compute_energy

PROTOCOL='S04-E011-LEARNED-HEAD-NEWTON-r1'
PBD_ENERGY=.005401565679038969


def hard_head_failure(reason):
    return reason.startswith(('nonpositive_or_numerically_singular_tangent',
        'dense_linear_solve_residual','Newton_direction_not_descent','Armijo_line_search_not_closed'))


def install_uv_head(net,head):
    """Only the first two output rows, including bias, are mutable."""
    with torch.no_grad():
        value=torch.as_tensor(head,device=net.output_layer.weight.device,dtype=net.output_layer.weight.dtype)
        if value.shape!=(2,net.output_layer.weight.shape[1]+1):raise ValueError('UV-head shape mismatch')
        net.output_layer.weight[:2].copy_(value[:,:-1]);net.output_layer.bias[:2].copy_(value[:,-1])


def assert_frozen(net,before):
    for name,value in net.state_dict().items():
        old=before[name]
        if name in ['output_layer.weight','output_layer.bias']:
            assert torch.equal(value[2:],old[2:]), 'damage output row changed'
        else:
            assert torch.equal(value,old), 'hidden parameter changed: '+name


def finish_endpoint(net,before,candidate,candidate_fields,before_row,before_fields):
    """No extra energy call: a rejected actual point restores verified PBD."""
    tolerance=128*np.finfo(float).eps*max(abs(before_row['E_el']),abs(candidate['E_el']),1e-30)
    if candidate['E_el']>before_row['E_el']+tolerance:
        net.load_state_dict(before)
        return before_row,before_fields,True,'actual_energy_increase_rollback'
    return candidate,candidate_fields,False,None


def run_state(item,out,device,phase):
    out.mkdir();budget=JournalBudget(out);work=Work(budget)
    assert item['cycle']==20 and item['substep']==4 and item['step']==99
    assert not any(k in item for k in ['basis','old_basis','restricted_span']), 'Fresh full current design required'
    data=dict(np.load(item['input'],allow_pickle=False));problem=LocalProblem(data,device)
    assert data['nodes'].shape==(86756,2) and data['cells'].shape==(86408,4)
    original=torch.load(item['original_model'],map_location=device,weights_only=True)
    initial=torch.load(item['initial_model'],map_location=device,weights_only=True)
    field=make_smooth(original,problem)  # Retain the ORIGINAL B0 anchor.
    field.net.load_state_dict(initial);field.net.requires_grad_(False)
    assert not field.williams_enabled and not field.ansatz_enabled and not field.exact_bc_enabled and not field.symmetry_prior
    before_parameters=snapshot(field.net);hidden_before=hidden_digest(before_parameters)
    anchors={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
    physics={n:tensor_hash(p) for n,p in [('FEM_d',problem.df),('own_lower',problem.hist),('own_f',problem.f)]}
    with torch.no_grad():
        u0,v0,_=field.fieldCalculation(problem.x)
        features=field.net.encode(problem.x)
        assert features.shape==(86756,400)
        head0=torch.cat((field.net.output_layer.weight[:2],field.net.output_layer.bias[:2,None]),dim=1).cpu().numpy()
        y=problem.x[:,1];bubble=((y+.5)*(.5-y)).cpu().numpy()
    transform,phi,basis=conditioned_basis(features.cpu().numpy(),problem.mass.cpu().numpy(),bubble,.11999988)
    del features
    rank=transform.shape[1]
    assert 0<rank<=401 and transform.shape==(401,rank)
    phi=torch.as_tensor(phi,device=device,dtype=torch.float64)
    space=dict(transform=transform,phi=phi)
    basis.update(rebuilt_from_current_PBD_hidden=True,raw_columns=401,old_restricted_span_used=False,
        numerical_policy='existing eps*max(rows,columns)*smax; retain every numerically resolvable current direction',
        preparation_seconds=time.monotonic()-budget.start,initial_model=item['initial_model'],initial_model_sha256=sha(item['initial_model']))
    dump(out/'basis.json',basis);np.savez_compressed(out/'basis.npz',transform=transform,initial_head=head0)
    # Full raw span is identity only for raw-gradient reporting. Newton uses
    # the mass-conditioned current physical basis above, not the old S span.
    identity=np.eye(401)
    before,before_fields,before_gradient=raw_network_readout(field,problem,identity,budget,'before_PBD',space)
    assert abs(before['E_el']-PBD_ENERGY)<=1e-10, 'Not the locked PBD c20 low-energy endpoint'
    (out/'before').mkdir();dump(out/'before/result.json',before);np.savez_compressed(out/'before/fields.npz',**before_fields)
    dump(out/'gradient_readouts.json',[before])
    reduced=ReducedElastic(problem,phi,u0,v0);tangent=Tangent(reduced,work)
    z0=np.zeros(2*rank);e0,g0=evaluated(reduced,budget,z0,'initial_reduced_energy_gradient')
    assert abs(e0-before['E_el'])<=1e-10
    source=budget.begin('source_energy_contract')
    with torch.no_grad():source_value=compute_energy(problem.x,u0,v0,problem.df,problem.hist,problem.mat,problem.model,problem.area,problem.cells,
        f_fatigue=problem.f,irreversibility_penalty_cfg={'enable':True,'mode':'fem_gp_q4'})[0]
    source_error=abs(float(source_value)-e0);assert source_error<=1e-10
    source.update(completed=True,E_el=float(source_value),source_error=source_error)
    h0,tr0=tangent.matrix(z0);fd=tangent_contract(reduced,tangent,h0,tr0,z0,budget);dump(out/'tangent_contract.json',fd)
    np.savez_compressed(out/'tangent_initial.npz',H=h0.cpu().numpy(),gradient=g0)
    if phase=='probe':
        direction,solve=linear_solve(h0,g0,work)
        assert all(torch.equal(p,before_parameters[n]) for n,p in field.net.state_dict().items())
        assert anchors=={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
        assert physics=={n:tensor_hash(p) for n,p in [('FEM_d',problem.df),('own_lower',problem.hist),('own_f',problem.f)]}
        free,total=torch.cuda.mem_get_info();assert free>=3*1024**3
        result=dict(status='probe_passed',evaluations=len(budget.trace),full_raw_parameter_backward=True,
            hidden_backward=True,optimizer_updates=0,parameter_updates=0,hidden_updates=0,
            actual_tangent_assembly_and_solve=True,dense_assemblies=work.assemblies,
            explicit_tangent_vector_products=work.products,linear_solves=work.solves,solve=solve,
            free_VRAM=free,total_VRAM=total,current_full_raw_columns=401,current_rank=rank,
            hidden_exactly_unchanged=True,damage_output_row_unchanged=True,Smooth_B0_anchor_unchanged=True,
            mechanical_damage_exact_FEM=True,boundary_unchanged=True,history_commits=0,rollout_steps=0)
        dump(out/'trace.json',budget.trace);dump(out/'result.json',result);return result
    row=budget.begin('native_FEM_force_contract')
    fem,_=readout(problem,problem.uf,problem.vf,phi,native=data['ru_fem']);assert fem['free_u_l2']<1e-8
    row.update(completed=True,**fem)
    last,accepted,solver=newton_solve(reduced,tangent,budget,dict(z=z0,value=e0,gradient=g0),h0)
    raw_head=head0+(transform@last['z'].reshape(2,rank).T).T
    np.savez_compressed(out/'accepted_reduced_candidate.npz',z=last['z'],raw_head=raw_head,
                        conditioned_E_el=last['value'],conditioned_gradient=last['gradient'])
    hard=hard_head_failure(solver['stop']);rolled_back=hard
    if hard:
        field.net.load_state_dict(before_parameters)
    else:
        install_uv_head(field.net,raw_head)
    with torch.no_grad():linear_u,linear_v=reduced.fields(torch.as_tensor(last['z'],device=device,dtype=torch.float64))
    actual=None;actual_fields=None;actual_gradient=None;candidate_readout=None
    try:
        candidate_readout,candidate_fields,candidate_gradient=raw_network_readout(field,problem,identity,budget,'final',space,final=True)
        actual,actual_fields,energy_rollback,why=finish_endpoint(field.net,before_parameters,candidate_readout,candidate_fields,before,before_fields)
        if why:solver['actual_endpoint_stop']=why
        rolled_back=rolled_back or energy_rollback
        actual_gradient=before_gradient if energy_rollback else candidate_gradient
    except BudgetStop as err:solver['terminal_readout_missing']=str(err)
    assert_frozen(field.net,before_parameters)
    assert hidden_before==hidden_digest(field.net.state_dict())
    assert anchors=={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
    assert physics=={n:tensor_hash(p) for n,p in [('FEM_d',problem.df),('own_lower',problem.hist),('own_f',problem.f)]}
    if actual is None:
        field.net.load_state_dict(before_parameters);visible_fields=before_fields
    else:visible_fields=actual_fields
    np.savez_compressed(out/'fields.npz',**visible_fields);torch.save(field.net.state_dict(),out/'accepted_network.pt')
    gradients=[before]
    if candidate_readout is not None:
        if rolled_back:candidate_readout={**candidate_readout,'status':'rejected_or_rolled_back','retained_endpoint_is_before':True}
        gradients.append(candidate_readout)
    if actual is not None and rolled_back:gradients.append({**actual,'label':'final_retained_before','status':'verified'})
    actual_inf=actual['reduced_gradient_inf'] if actual else None
    conditioned_closed=bool(abs(last['gradient']).max()<=GTOL)
    actual_closed=bool(actual_inf is not None and actual_inf<=GTOL and not hard)
    linear_error=max(float(np.max(abs(visible_fields['u']-linear_u.cpu().numpy()))),
                     float(np.max(abs(visible_fields['v']-linear_v.cpu().numpy())))) if actual else None
    result=dict(status='completed' if actual else 'partial_terminal_readout_missing',cycle=20,substep=4,step=99,
        starting_point='unique PBD c20 U_energy accepted network; current hidden frozen, full current401 raw design',
        before=before,actual_network=actual,candidate_actual_readout=candidate_readout,last_verified_network=actual if actual else before,
        E_el=actual['E_el'] if actual else None,free_u_l2=actual['free_u_l2'] if actual else None,
        uv_mass_rel_L2=actual['uv_mass_rel_L2'] if actual else None,uv_H1_rel=actual['uv_H1_rel'] if actual else None,
        conditioned_E_el=last['value'],conditioned_reduced_gradient_inf=float(abs(last['gradient']).max()),
        actual_minus_conditioned_gradient_inf=float(np.max(abs(actual_gradient-last['gradient']))) if actual else None,
        actual_minus_conditioned_energy=actual['E_el']-last['value'] if actual else None,
        linear_vs_actual_uv_maxabs=linear_error,stationarity_closed=actual_closed,stationary=actual_closed,
        conditioned_stationarity_closed=conditioned_closed,realization_limited=bool(actual and conditioned_closed and not actual_closed and not rolled_back),
        gradient_inf_tolerance=GTOL,rolled_back=rolled_back,hard_solver_failure=hard,solver=solver,
        gradient_readouts=gradients,basis=basis,accepted_head_updates=0 if rolled_back else len(accepted),
        evaluations=len(budget.trace),cap=400,deadline_seconds=600.,elapsed_seconds=time.monotonic()-budget.start,
        dense_assemblies=work.assemblies,explicit_tangent_vector_products=work.products,linear_solves=work.solves,
        hidden_before_sha256=hidden_before,hidden_after_sha256=hidden_digest(field.net.state_dict()),hidden_exactly_unchanged=True,
        damage_output_row_unchanged=True,Smooth_B0_anchor_unchanged=True,mechanical_damage_exact_FEM=True,
        boundary_unchanged=True,hidden_updates=0,history_commits=0,rollout_steps=0,ridge=0.,oracle_claim=False,whole_network_capacity_claim=False)
    for entry in accepted:entry.update(actual_endpoint_retained=bool(actual and not rolled_back),conditioned_inner_point=True)
    if actual is not None:np.savez_compressed(out/'stationarity_vectors.npz',actual_gradient=actual_gradient,conditioned_gradient=last['gradient'])
    dump(out/'accepted.json',accepted);dump(out/'trace.json',budget.trace);dump(out/'gradient_readouts.json',gradients);dump(out/'result.json',result)
    return result


def main(args):
    torch.set_num_threads(1);torch.set_num_interop_threads(1);assert not args.out.exists()
    contract=json.loads(args.contract.read_text());assert contract['protocol']==PROTOCOL and len(contract['states'])==1
    for entry in contract.get('files',[]):
        p=Path(entry['path']);assert p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256']
    device=torch.device(args.device);assert device.type=='cuda' and torch.cuda.is_available(),'No Mac/CPU optimization'
    args.out.mkdir(parents=True);torch.cuda.reset_peak_memory_stats()
    dump(args.out/'receipt.json',dict(protocol=PROTOCOL,commit=contract['commit'],run_id=contract['run_id'],phase=args.phase,
        pid=os.getpid(),host=os.uname().nodename,command=sys.argv,CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
        started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),history_commits=0,rollout_steps=0))
    try:
        result=run_state(contract['states'][0],args.out/'c20_s4',device,args.phase);dump(args.out/'rows.json',[result])
        if args.phase=='probe':dump(args.out/'probe_pass.json',{**result,'status':'passed','peak_allocated':torch.cuda.max_memory_allocated()})
        dump(args.out/'complete.json',dict(status='completed' if result['status'] in ['completed','probe_passed'] else 'partial',states=1,phase=args.phase,history_commits=0,rollout_steps=0))
    except Exception as err:
        dump(args.out/'failure.json',dict(type=type(err).__name__,message=str(err),history_commits=0));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--phase',choices=['probe','production'],required=True);parser.add_argument('--device',default='cuda');main(parser.parse_args())
