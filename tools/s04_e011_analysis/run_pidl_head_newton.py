#!/usr/bin/env python3
"""Consistent reduced Amor tangent; fixed old UV-head span, no ridge or SVD."""
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
from run_pidl_energy_head import EvaluationBudget,BudgetStop,ReducedElastic
from run_pidl_block_diagnosis import LocalProblem,make_smooth,sha,dump,tensor_hash
from compute_energy import compute_energy

PROTOCOL='S04-E011-UVHEAD-NEWTON-r1'
GTOL=1e-10


class TangentFailure(RuntimeError):
    pass


class JournalBudget(EvaluationBudget):
    """Persist even an unfinished trial before computation can fail."""
    def __init__(self,folder):
        super().__init__(cap=400,seconds=600.)
        self.folder=folder
    def begin(self,role,final=False):
        row=super().begin(role,final=final)
        dump(self.folder/'trace.json',self.trace)
        return row


class Work:
    def __init__(self,budget):
        self.budget=budget;self.assemblies=0;self.products=0;self.solves=0;self.records=[]
    def check(self):
        if time.monotonic()-self.budget.start>=self.budget.seconds:
            raise BudgetStop('wall_deadline')
    def checkpoint(self):
        if hasattr(self.budget,'folder'):
            dump(self.budget.folder/'work_counts.json',dict(dense_assemblies=self.assemblies,
                explicit_tangent_vector_products=self.products,linear_solves=self.solves))
            dump(self.budget.folder/'tangent_work.json',self.records)
    def product(self,role):
        self.check()
        if self.products>=1000:raise BudgetStop('tangent_product_budget')
        self.products+=1
        self.checkpoint()


def assemble_blocks(gx,gy,weights,degradation,trace,chunk=8192):
    """Engineering shear. At trace0 choose tensile g as generalized tangent.

    No factor-of-two ambiguity: dev energy is mu*(exx²+eyy²+gamma²/2-tr²/3).
    The zero-trace selected matrix is not claimed to equal every one-sided
    Hessian or PyTorch ReLU's AD Hessian at its exact zero.
    """
    r=gx.shape[1];mu=1/2.6;bulk=1/1.2
    h=torch.zeros((2*r,2*r),dtype=gx.dtype,device=gx.device)
    for start in range(0,len(weights),chunk):
        sl=slice(start,min(start+chunk,len(weights)));x,y=gx[sl],gy[sl]
        wg=weights[sl]*degradation[sl]
        q=torch.where(trace[sl]>=0,degradation[sl],torch.ones_like(degradation[sl]))
        c=bulk*weights[sl]*q;dev=mu*wg
        h[:r,:r]+=x.T@((4/3*dev+c)[:,None]*x)+y.T@(dev[:,None]*y)
        h[r:,r:]+=y.T@((4/3*dev+c)[:,None]*y)+x.T@(dev[:,None]*x)
        h[:r,r:]+=x.T@((c-2/3*dev)[:,None]*y)+y.T@(dev[:,None]*x)
    h[r:,:r]=h[:r,r:].T
    asym=float((h-h.T).abs().max())
    h=(h+h.T)*.5  # Roundoff symmetrization; no ridge, rank repair or truncation.
    assert torch.isfinite(h).all()
    return h,asym


class Tangent:
    def __init__(self,reduced,work,element_chunk=1024):
        self.reduced,self.work=reduced,work
        p=reduced.problem;r=reduced.rank;ne=len(p.cells)
        self.gx=torch.empty((4*ne,r),dtype=torch.float64,device=p.x.device)
        self.gy=torch.empty_like(self.gx)
        with torch.no_grad():
            for start in range(0,ne,element_chunk):
                work.check();end=min(start+element_chunk,ne)
                local=reduced.phi[p.cells[start:end]]
                grad=torch.einsum('egki,eir->egkr',p.B[start:end],local)
                self.gx[4*start:4*end]=grad[:,:,0].reshape(-1,r)
                self.gy[4*start:4*end]=grad[:,:,1].reshape(-1,r)
            self.w=p.w.reshape(-1)
            self.g=(1-torch.einsum('gi,ei->eg',p.N,p.df[p.cells])).square().reshape(-1)
        assert torch.isfinite(self.gx).all() and torch.isfinite(self.gy).all()
        assert torch.all(self.g>=0) and torch.all(self.g<=1+1e-12)
    def trace_at(self,z):
        p=self.reduced.problem
        q=torch.as_tensor(z,device=p.x.device,dtype=torch.float64)
        with torch.no_grad():
            u,v=self.reduced.fields(q)
            return (p.grad(u)[:,:,0]+p.grad(v)[:,:,1]).reshape(-1)
    def matrix(self,z):
        self.work.check()
        if self.work.assemblies>=10:raise BudgetStop('dense_assembly_budget')
        self.work.assemblies+=1;t0=time.monotonic();tr=self.trace_at(z)
        h,asym=assemble_blocks(self.gx,self.gy,self.w,self.g,tr)
        self.work.records.append(dict(assembly=self.work.assemblies,shape=list(h.shape),
            gradient_basis_shape=list(self.gx.shape),quadrature_points=len(self.w),
            dense_assembly_includes_all_columns=True,column_equivalent_tangent_actions=h.shape[1],
            trace_positive=int((tr>0).sum()),trace_negative=int((tr<0).sum()),trace_zero=int((tr==0).sum()),
            unsymmetrized_maxabs=asym,seconds=time.monotonic()-t0,ridge=0.,extra_rank_truncation=False))
        self.work.checkpoint()
        return h,tr
    def zero_volume_action(self,vec,tr,coefficient,role):
        self.work.product(role);r=self.reduced.rank
        v=torch.as_tensor(vec,device=self.gx.device,dtype=torch.float64)
        t=self.gx@v[:r]+self.gy@v[r:]
        weighted=(1/1.2)*self.w*(tr==0)*coefficient*t
        return torch.cat((self.gx.T@weighted,self.gy.T@weighted))


def linear_solve(h,gradient,work):
    """A failed SPD/solve check stops; no lstsq, pseudoinverse or damping ridge."""
    work.check();work.solves+=1;work.checkpoint()
    g=torch.as_tensor(gradient,device=h.device,dtype=h.dtype)
    chol,info=torch.linalg.cholesky_ex(h,check_errors=False)
    if int(info)!=0:
        raise TangentFailure(f'nonpositive_or_numerically_singular_tangent_cholesky_info_{int(info)}')
    direction=torch.cholesky_solve(-g[:,None],chol)[:,0]
    work.product('linear_solve_residual_H_times_direction')
    residual=h@direction+g
    relative=float(torch.linalg.vector_norm(residual)/torch.linalg.vector_norm(g).clamp(min=1e-30))
    if not torch.isfinite(direction).all() or relative>1e-6:
        raise TangentFailure(f'dense_linear_solve_residual_{relative}')
    return direction.cpu().numpy(),dict(relative_residual=relative,descent_dot=float(g@direction),
                                       cholesky=True,ridge=0.,further_truncation=False)


def readout(problem,u,v,phi,native=None):
    u=u.detach().clone().requires_grad_(True);v=v.detach().clone().requires_grad_(True)
    energy=problem.parts(u,v,problem.df)[0];gu,gv=torch.autograd.grad(energy,(u,v))
    full=torch.cat((gu,gv));gradient=torch.cat((phi.T@gu,phi.T@gv))
    mass=((problem.mass*((u-problem.uf).square()+(v-problem.vf).square())).sum()/
          (problem.mass*(problem.uf.square()+problem.vf.square())).sum())
    h1=(problem.w*(problem.grad(u-problem.uf).square().sum(2)+problem.grad(v-problem.vf).square().sum(2))).sum()/problem.uv_denom
    row=dict(E_el=float(energy.detach()),free_u_l2=float(torch.linalg.vector_norm(full[problem.fu])),
             reduced_gradient_l2=float(torch.linalg.vector_norm(gradient)),reduced_gradient_inf=float(gradient.abs().max()),
             uv_mass_rel_L2=float(torch.sqrt(mass)),uv_H1_rel=float(torch.sqrt(h1)))
    if native is not None:
        err=float((full-torch.as_tensor(native,device=full.device)).abs().max());assert err<=1e-10
        row['native_force_maxabs_error']=err
    assert all(np.isfinite(v) for v in row.values())
    return row,gradient.detach().cpu().numpy()


def evaluated(reduced,budget,z,role):
    row=budget.begin(role);value,gradient=reduced.value_gradient(z)
    row.update(completed=True,E_el=value,gradient_l2=float(np.linalg.norm(gradient)),gradient_inf=float(abs(gradient).max()))
    if hasattr(budget,'folder'):dump(budget.folder/'trace.json',budget.trace)
    return value,gradient


def tangent_contract(reduced,tangent,h,tr,z,budget):
    """FD on unchanged nonzero branches; isolate exact-zero volumetric terms.

    At zero ReLU's AD second derivative is0 and centered FD uses(g+1)/2.
    Those known terms are explicitly removed before comparing the common
    nonzero-sign tangent; the selected Newton matrix uses q=g at zero.
    """
    rows=[];rng=np.random.default_rng(173);rank=reduced.rank
    for label in ['seeded_random','second_seeded_random']:
        v=rng.normal(size=2*rank);v/=np.linalg.norm(v)
        vt=torch.as_tensor(v,device=h.device,dtype=h.dtype)
        tangent.work.product('dense_H_times_contract_direction');hv=h@vt
        selected=tangent.zero_volume_action(v,tr,tangent.g,'selected_zero_volume_action')
        centered=tangent.zero_volume_action(v,tr,(tangent.g+1)*.5,'centered_zero_volume_action')
        target=hv-selected
        row=budget.begin('AD_tangent_vector_contract');tangent.work.product('AD_explicit_tangent_vector_product')
        q=torch.as_tensor(z,device=h.device,dtype=h.dtype).clone().requires_grad_(True)
        u,vv=reduced.fields(q);energy=reduced.problem.parts(u,vv,reduced.problem.df)[0]
        gradient=torch.autograd.grad(energy,q,create_graph=True)[0]
        ad=torch.autograd.grad((gradient*vt).sum(),q)[0]
        ad_error=float(torch.linalg.vector_norm(ad-target));scale=float(torch.linalg.vector_norm(target))
        assert ad_error<=1e-8+1e-8*scale,(label,'AD contract',ad_error,scale)
        row.update(completed=True,E_el=float(energy.detach()),direction=label,corrected_AD_error=ad_error)
        dtrace=tangent.gx@vt[:rank]+tangent.gy@vt[rank:]
        live=(tr!=0)&(dtrace!=0)
        safe=float((abs(tr[live])/abs(dtrace[live])).min())*.1 if bool(live.any()) else 1e-5
        hs=sorted(set([1e-4,1e-5,1e-6,1e-7,1e-8,min(1e-8,safe),min(1e-9,safe*.1)]),reverse=True)
        entries=[]
        for eps in hs:
            if eps<=0:continue
            _,plus=evaluated(reduced,budget,z+eps*v,'FD_plus_gradient_contract')
            _,minus=evaluated(reduced,budget,z-eps*v,'FD_minus_gradient_contract')
            fd=torch.as_tensor((plus-minus)/(2*eps),device=h.device)-centered
            crossing=int((((tr+eps*dtrace)>0)!=(tr>0))[tr!=0].sum()+(((tr-eps*dtrace)>0)!=(tr>0))[tr!=0].sum())
            error=float(torch.linalg.vector_norm(fd-target))
            entries.append(dict(h=eps,nonzero_branch_crossings=crossing,corrected_FD_error=error))
        eligible=[x for x in entries if x['nonzero_branch_crossings']==0]
        assert eligible and min(x['corrected_FD_error'] for x in eligible)<=1e-8+1e-4*scale,(label,entries,scale)
        rows.append(dict(direction=label,zero_trace_GPs=int((tr==0).sum()),AD_error_after_zero_policy_separation=ad_error,
                         common_nonzero_tangent_norm=scale,FD=entries,zero_policy='selected q=g; AD q0; centered FD q=(g+1)/2; known zero volumetric terms separated'))
    return rows


def newton_solve(reduced,tangent,budget,last,initial_h):
    accepted=[];reason='newton_step_budget';h=initial_h;solve_rows=[]
    try:
        for step in range(1,11):
            if np.max(abs(last['gradient']))<=GTOL:reason='conditioned_gradient_tolerance';break
            if step>1:h,_=tangent.matrix(last['z'])
            direction,solve=linear_solve(h,last['gradient'],tangent.work);solve_rows.append(solve)
            dot=float(last['gradient']@direction)
            if dot>=0:raise TangentFailure('Newton_direction_not_descent')
            accepted_trial=False
            for line in range(32):
                alpha=2.**(-line);z=last['z']+alpha*direction
                value,gradient=evaluated(reduced,budget,z,'Newton_Armijo_trial')
                roundoff=32*np.finfo(float).eps*max(abs(value),abs(last['value']),1e-30)
                if value<=last['value']+1e-4*alpha*dot+roundoff:
                    last=dict(z=z.copy(),value=value,gradient=gradient.copy());accepted_trial=True
                    accepted.append(dict(accepted=len(accepted)+1,newton_step=step,evaluations=len(budget.trace),
                        E_el=value,reduced_gradient_l2=float(np.linalg.norm(gradient)),reduced_gradient_inf=float(abs(gradient).max()),
                        alpha=alpha,line_trials=line+1,linear_solve=solve));break
            if not accepted_trial:reason='Armijo_line_search_not_closed';break
        if np.max(abs(last['gradient']))<=GTOL:reason='conditioned_gradient_tolerance'
    except (BudgetStop,TangentFailure) as err:reason=str(err)
    return last,accepted,dict(stop=reason,linear_solves=solve_rows,Armijo_c1=1e-4,max_line_trials=32,
                              newton_steps_max=10,gradient_inf_tolerance=GTOL,small_loss_stop=False)


def run_state(item,out,device,phase):
    out.mkdir();budget=JournalBudget(out);work=Work(budget)
    data=dict(np.load(item['input'],allow_pickle=False));problem=LocalProblem(data,device)
    assert item['cycle'] in [1,20] and item['step']==5*(item['cycle']-1)+4 and item['substep']==4
    state=torch.load(item['model'],map_location=device,weights_only=True);field=make_smooth(state,problem);field.net.requires_grad_(False)
    before={n:p.clone() for n,p in field.net.state_dict().items()}
    frozen={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
    physical={n:tensor_hash(p) for n,p in [('d',problem.df),('lower',problem.hist),('f',problem.f)]}
    basis_npz=dict(np.load(item['basis'],allow_pickle=False));transform=basis_npz['transform'];head0=basis_npz['theta0_head']
    rank=transform.shape[1];assert transform.shape==(401,{1:388,20:387}[item['cycle']])
    assert np.isfinite(transform).all() and np.isfinite(head0).all() and head0.shape==(2,401)
    with torch.no_grad():
        u0,v0,_=field.fieldCalculation(problem.x);features=field.net.encode(problem.x)
        actual0=torch.cat((field.net.output_layer.weight[:2],field.net.output_layer.bias[:2,None]),dim=1).cpu().numpy()
        assert np.array_equal(actual0,head0), 'basis theta0 head does not match original model'
        bubble=((problem.x[:,1]+.5)*(.5-problem.x[:,1])).cpu().numpy()
        design=.11999988*bubble[:,None]*np.column_stack((features.cpu().numpy(),np.ones(problem.n)))
        phi=torch.as_tensor(design@transform,device=device,dtype=torch.float64)
    del features,design
    reduced=ReducedElastic(problem,phi,u0,v0);tangent=Tangent(reduced,work)
    old_report=json.loads(Path(item['basis_report']).read_text()) if item.get('basis_report') else {}
    basis=dict(source_path=item['basis'],source_sha256=sha(item['basis']),source_report=item.get('basis_report'),
               retained_rank=rank,no_new_SVD=True,no_further_truncation=True,ridge=0.,theta0_head_exact=True,
               preparation_seconds=time.monotonic()-budget.start,old_rank_metadata=old_report,
               gradient_cache_shape=list(tangent.gx.shape),gradient_cache_bytes=2*tangent.gx.numel()*8)
    dump(out/'basis.json',basis);np.savez_compressed(out/'basis.npz',transform=transform,theta0_head=head0)
    z0=np.zeros(2*rank);e0,g0=evaluated(reduced,budget,z0,'initial_energy_gradient');last=dict(z=z0,value=e0,gradient=g0)
    row=budget.begin('source_energy_contract')
    with torch.no_grad():oracle=compute_energy(problem.x,u0,v0,problem.df,problem.hist,problem.mat,problem.model,problem.area,problem.cells,f_fatigue=problem.f,irreversibility_penalty_cfg={'enable':True,'mode':'fem_gp_q4'})[0]
    source_error=abs(float(oracle)-e0);assert source_error<=1e-10*max(1.,abs(e0));row.update(completed=True,E_el=float(oracle),source_error=source_error)
    h0,tr0=tangent.matrix(z0);fd=tangent_contract(reduced,tangent,h0,tr0,z0,budget)
    dump(out/'tangent_contract.json',fd)
    # Probe performs a real factorization/solve but accepts no step or parameter.
    if phase=='probe':
        direction,solve=linear_solve(h0,g0,work)
        np.savez_compressed(out/'tangent_initial.npz',H=h0.cpu().numpy(),gradient=g0,solve_direction=direction)
        assert all(torch.equal(p,before[n]) for n,p in field.net.state_dict().items())
        assert frozen=={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
        assert physical=={n:tensor_hash(p) for n,p in [('d',problem.df),('lower',problem.hist),('f',problem.f)]}
        free,total=torch.cuda.mem_get_info();assert free>=3*1024**3
        result=dict(status='probe_passed',evaluations=len(budget.trace),optimizer_updates=0,history_commits=0,rollout_steps=0,
            dense_assemblies=work.assemblies,explicit_tangent_vector_products=work.products,linear_solves=work.solves,
            linear_solve=solve,free_VRAM=free,total_VRAM=total,actual_tangent_assembly_and_solve=True,
            hidden_and_damage_head_exactly_unchanged=True,hidden_updates=0,parameter_updates=0,
            Smooth_B0_anchor_unchanged=True,frozen_damage_lower_f_unchanged=True)
        dump(out/'trace.json',budget.trace);dump(out/'tangent_work.json',work.records);dump(out/'result.json',result);return result
    row=budget.begin('native_FEM_readout');fem,_=readout(problem,problem.uf,problem.vf,phi,native=data['ru_fem']);assert fem['free_u_l2']<1e-8;row.update(completed=True,**fem)
    row=budget.begin('initial_actual_network_readout');initial,_=readout(problem,u0,v0,phi);row.update(completed=True,**initial)
    np.savez_compressed(out/'tangent_initial.npz',H=h0.cpu().numpy(),gradient=g0)
    last,accepted,solver=newton_solve(reduced,tangent,budget,last,h0)
    raw_head=head0+(transform@last['z'].reshape(2,rank).T).T
    np.savez_compressed(out/'accepted_reduced_candidate.npz',z=last['z'],raw_head=raw_head,conditioned_E_el=last['value'],conditioned_gradient=last['gradient'])
    with torch.no_grad():
        head=torch.as_tensor(raw_head,device=device,dtype=torch.float64);field.net.output_layer.weight[:2].copy_(head[:,:-1]);field.net.output_layer.bias[:2].copy_(head[:,-1]);u,v,_=field.fieldCalculation(problem.x)
        lu,lv=reduced.fields(torch.as_tensor(last['z'],device=device,dtype=torch.float64))
    for n,p in field.net.state_dict().items():
        assert torch.equal(p[2:],before[n][2:]) if n in ['output_layer.weight','output_layer.bias'] else torch.equal(p,before[n])
    assert frozen=={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
    assert physical=={n:tensor_hash(p) for n,p in [('d',problem.df),('lower',problem.hist),('f',problem.f)]}
    actual=None;ag=None
    try:
        row=budget.begin('final_actual_installed_network_readout',final=True);actual,ag=readout(problem,u,v,phi);row.update(completed=True,**actual)
    except BudgetStop as err:solver['terminal_readout_missing']=str(err)
    np.savez_compressed(out/'fields.npz',u=(u if actual else u0).cpu().numpy(),v=(v if actual else v0).cpu().numpy(),d=data['d_fem'])
    if actual:torch.save(field.net.state_dict(),out/'accepted_network.pt')
    cc=bool(np.max(abs(last['gradient']))<=GTOL);ac=bool(actual and actual['reduced_gradient_inf']<=GTOL)
    result=dict(status='completed' if actual else 'partial_terminal_readout_missing',cycle=item['cycle'],substep=4,step=item['step'],
        actual_network=actual,initial=initial,FEM=fem,last_verified_network=actual if actual else initial,
        E_el=actual['E_el'] if actual else None,free_u_l2=actual['free_u_l2'] if actual else None,
        uv_mass_rel_L2=actual['uv_mass_rel_L2'] if actual else None,uv_H1_rel=actual['uv_H1_rel'] if actual else None,
        conditioned_E_el=last['value'],conditioned_reduced_gradient_inf=float(abs(last['gradient']).max()),
        actual_minus_conditioned_gradient_inf=float(np.max(abs(ag-last['gradient']))) if actual else None,
        actual_minus_conditioned_energy=actual['E_el']-last['value'] if actual else None,
        linear_vs_actual_uv_maxabs=max(float((u-lu).abs().max()),float((v-lv).abs().max())),
        stationarity_closed=ac,stationary=ac,conditioned_stationarity_closed=cc,realization_limited=cc and bool(actual) and not ac,
        gradient_inf_tolerance=GTOL,oracle_claim=False,accepted_head_updates=len(accepted),Newton_updates=len(accepted),
        evaluations=len(budget.trace),cap=400,deadline_seconds=600.,elapsed_seconds=time.monotonic()-budget.start,
        dense_assemblies=work.assemblies,explicit_tangent_vector_products=work.products,linear_solves=work.solves,
        hidden_and_damage_head_exactly_unchanged=True,Smooth_B0_anchor_unchanged=True,frozen_damage_lower_f_unchanged=True,
        history_commits=0,rollout_steps=0,ridge=0.,solver=solver,basis=basis)
    if actual:np.savez_compressed(out/'stationarity_vectors.npz',actual_gradient=ag,conditioned_gradient=last['gradient'])
    dump(out/'trace.json',budget.trace);dump(out/'accepted.json',accepted);dump(out/'tangent_work.json',work.records);dump(out/'result.json',result);return result


def main(args):
    torch.set_num_threads(1);torch.set_num_interop_threads(1);assert not args.out.exists()
    contract=json.loads(args.contract.read_text());assert contract['protocol']==PROTOCOL
    for item in contract.get('files',[]):
        p=Path(item['path']);assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
    device=torch.device(args.device);assert device.type=='cuda' and torch.cuda.is_available(),'No Mac/CPU production'
    args.out.mkdir(parents=True);torch.cuda.reset_peak_memory_stats()
    dump(args.out/'receipt.json',dict(protocol=PROTOCOL,commit=contract['commit'],run_id=contract['run_id'],phase=args.phase,
        pid=os.getpid(),host=os.uname().nodename,command=sys.argv,CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
        started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),history_commits=0,rollout_steps=0))
    rows=[]
    try:
        for item in contract['states'][:1] if args.phase=='probe' else contract['states']:
            rows.append(run_state(item,args.out/f'c{item["cycle"]}_s4',device,args.phase));dump(args.out/'rows.json',rows)
            if args.phase=='probe':dump(args.out/'probe_pass.json',{**rows[-1],'status':'passed','peak_allocated':torch.cuda.max_memory_allocated()})
            if rows[-1]['status'].startswith('partial'):break
        dump(args.out/'complete.json',dict(status='completed' if all(r['status'] in ['completed','probe_passed'] for r in rows) else 'partial',states=len(rows),phase=args.phase,history_commits=0,rollout_steps=0))
    except Exception as err:
        dump(args.out/'failure.json',dict(type=type(err).__name__,message=str(err),completed_states=len(rows),history_commits=0));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--phase',choices=['probe','production'],required=True);parser.add_argument('--device',default='cuda');main(parser.parse_args())
