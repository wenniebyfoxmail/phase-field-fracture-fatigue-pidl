#!/usr/bin/env python3
"""Same elastic energy, frozen PIDL features, UV head only; no fatigue rollout.

The numerical rank cutoff is explicit, not ridge regularization. A finite budget
endpoint is a candidate, never an oracle. Actual installed-network fields are
scored separately from the linear conditioned realization.
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
from scipy.linalg import svd
from scipy.optimize import minimize
import torch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1]/'source')]
from run_pidl_block_diagnosis import LocalProblem, make_smooth, sha, dump, tensor_hash
from compute_energy import compute_energy

PROTOCOL = 'S04-E011-UVHEAD-r1'


class BudgetStop(RuntimeError):
    pass


class EvaluationBudget:
    """Every energy/gradient call counts, including contracts and final replay."""
    def __init__(self, cap=400, seconds=600., clock=time.monotonic):
        self.cap, self.seconds, self.clock = cap, seconds, clock
        self.start = clock()
        self.trace = []

    def begin(self, role, final=False):
        # Reserve one call for the actual restored-network endpoint. Final
        # observations also obey the no-new-evaluation-after-600s rule.
        limit = self.cap if final else self.cap-1
        if len(self.trace) >= limit:
            raise BudgetStop('evaluation_budget')
        if self.clock()-self.start >= self.seconds:
            raise BudgetStop('wall_deadline')
        row = dict(evaluation=len(self.trace)+1, role=role,
                   start_seconds=self.clock()-self.start, completed=False)
        self.trace.append(row)
        return row


def conditioned_basis(features, mass, bubble, load):
    """Physical-displacement mass-weighted thin SVD, no bubble division/ridge.

    raw_head = theta0 + transform @ z. Thus discarded numerical directions
    retain their original theta0 values, and the starting field is unchanged.
    """
    h = np.asarray(features, dtype=np.float64)
    w = np.asarray(mass, dtype=np.float64).reshape(-1)
    b = np.asarray(bubble, dtype=np.float64).reshape(-1)
    if h.ndim != 2 or w.shape != (len(h),) or b.shape != w.shape:
        raise ValueError('incompatible features/mass/bubble')
    if not all(np.isfinite(x).all() for x in [h,w,b]) or np.any(w < 0) or not np.any(w > 0):
        raise ValueError('finite features/bubble and nonnegative nonzero mass required')
    design = float(load)*b[:,None]*np.column_stack((h,np.ones(len(h))))
    weighted = np.sqrt(w)[:,None]*design
    _, singular, vt = svd(weighted,full_matrices=False,lapack_driver='gesdd')
    rcond = np.finfo(np.float64).eps*max(weighted.shape)
    cutoff = rcond*singular[0] if len(singular) else 0.
    keep = singular > cutoff
    transform = vt[keep].T/singular[keep][None,:]
    phi = design@transform
    gram = phi.T@(w[:,None]*phi)
    info = dict(original_columns=design.shape[1],retained_rank=int(keep.sum()),
                rcond=rcond,singular_cutoff=float(cutoff),singular_values=singular.tolist(),
                rank_cutoff_sensitivity={str(x):int(np.sum(singular>x*cutoff))
                                         for x in [.1,1.,10.]},
                retained_raw_condition=float(singular[0]/singular[keep][-1]) if np.any(keep) else None,
                whitened_gram_maxabs_error=float(np.max(abs(gram-np.eye(len(gram))))) if len(gram) else 0.,
                transform_maxabs=float(np.max(abs(transform))) if transform.size else 0.,
                ridge=0.,starting_point='theta0 plus retained-subspace increment; discarded directions unchanged',
                sensitivity_solves=0)
    assert np.isfinite(transform).all() and np.isfinite(phi).all()
    return transform, phi, info


class ReducedElastic:
    def __init__(self, problem, phi, u0, v0):
        self.problem, self.phi = problem, phi
        self.u0, self.v0 = u0.detach(), v0.detach()
        self.rank = phi.shape[1]

    def fields(self, z):
        increment = self.phi@z.reshape(2,self.rank).T
        return self.u0+increment[:,0], self.v0+increment[:,1]

    def value_gradient(self, z):
        q = torch.as_tensor(np.asarray(z),device=self.phi.device,dtype=torch.float64).clone().requires_grad_(True)
        u,v = self.fields(q)
        value = self.problem.parts(u,v,self.problem.df)[0]
        gradient = torch.autograd.grad(value,q)[0]
        assert torch.isfinite(value) and torch.isfinite(gradient).all()
        return float(value.detach()), gradient.detach().cpu().numpy()


def node_readout(problem, u, v, phi, native_force=None):
    """One elastic-energy/gradient evaluation; caller must count it."""
    u = u.detach().clone().requires_grad_(True)
    v = v.detach().clone().requires_grad_(True)
    value = problem.parts(u,v,problem.df)[0]
    gu,gv = torch.autograd.grad(value,(u,v))
    all_force = torch.cat((gu,gv))
    force = all_force[problem.fu]
    reduced = torch.stack((phi.T@gu,phi.T@gv))
    mass_error = (problem.mass*((u-problem.uf)**2+(v-problem.vf)**2)).sum()
    mass_norm = (problem.mass*(problem.uf**2+problem.vf**2)).sum()
    h1 = (problem.w*(problem.grad(u-problem.uf).square().sum(2)+problem.grad(v-problem.vf).square().sum(2))).sum()/problem.uv_denom
    result = dict(E_el=float(value.detach()),free_u_l2=float(torch.linalg.vector_norm(force)),
                  reduced_gradient_l2=float(torch.linalg.vector_norm(reduced)),
                  reduced_gradient_inf=float(reduced.abs().max()) if reduced.numel() else 0.,
                  uv_mass_rel_L2=float(torch.sqrt(mass_error/mass_norm)),uv_H1_rel=float(torch.sqrt(h1)))
    if native_force is not None:
        native = torch.as_tensor(native_force,device=all_force.device,dtype=all_force.dtype)
        result['native_force_maxabs_error'] = float((all_force-native).abs().max())
        assert result['native_force_maxabs_error'] <= 1e-10
    assert all(np.isfinite(x) for x in result.values())
    return result


def solve_reduced(reduced, budget, initial_value, initial_gradient):
    """L-BFGS-B works only in the unbounded conditioned head coordinates."""
    initial = np.zeros(2*reduced.rank)
    last = dict(z=initial.copy(),value=initial_value,gradient=initial_gradient.copy())
    accepted, cache = [], {}

    def fun(z):
        row = budget.begin('conditioned_head_energy_gradient')
        value,gradient = reduced.value_gradient(z)
        row.update(completed=True,E_el=value,gradient_l2=float(np.linalg.norm(gradient)))
        cache[np.asarray(z).tobytes()] = (value,gradient.copy())
        return value,gradient

    def callback(z):
        key = np.asarray(z).tobytes()
        assert key in cache, 'accepted point lacks a completed value/gradient'
        value,gradient = cache[key]
        assert value <= last['value']+1e-12*max(1.,abs(last['value']))
        last.update(z=np.asarray(z).copy(),value=value,gradient=gradient.copy())
        accepted.append(dict(accepted=len(accepted)+1,evaluations=len(budget.trace),
                             E_el=value,reduced_gradient_l2=float(np.linalg.norm(gradient))))

    reason = 'zero_numerical_rank' if reduced.rank == 0 else 'library_exit'
    scipy_result = None
    if reduced.rank:
        try:
            scipy_result = minimize(fun,initial,jac=True,method='L-BFGS-B',callback=callback,
                                    options=dict(maxiter=400,maxfun=400,maxls=30,maxcor=20,
                                                 ftol=1e-14,gtol=1e-10))
            reason = str(scipy_result.message)
            # A returned trial is never silently promoted to accepted state.
            assert np.array_equal(scipy_result.x,last['z'])
        except BudgetStop as err:
            reason = str(err)
    return last,accepted,dict(stop=reason,library_success=bool(scipy_result.success) if scipy_result is not None else None,
                              library_status=int(scipy_result.status) if scipy_result is not None else None,
                              optimizer='unbounded L-BFGS-B in retained SVD coordinates',
                              ftol=1e-14,gtol=1e-10,maxls=30,maxcor=20)


def run_state(item, out, device, phase):
    out.mkdir()
    budget = EvaluationBudget()
    with np.load(item['input'],allow_pickle=False) as z:
        data = {k:z[k] for k in z.files}
    assert data['nodes'].shape == (86756,2) and data['cells'].shape == (86408,4)
    assert item['cycle'] in [1,20] and item['substep'] == 4 and item['step'] == 5*(item['cycle']-1)+4
    problem = LocalProblem(data,device)
    state = torch.load(item['model'],map_location=device,weights_only=True)
    field = make_smooth(state,problem)
    field.net.requires_grad_(False)
    assert not field.williams_enabled and not field.ansatz_enabled
    assert not field.exact_bc_enabled and not field.symmetry_prior
    initial_parameters = {name:q.detach().clone() for name,q in field.net.state_dict().items()}
    anchor = {name:tensor_hash(q) for name,q in field.alpha_constraint.state_dict().items()}
    frozen_physics = {name:tensor_hash(q) for name,q in [('damage',problem.df),('own_lower',problem.hist),('own_f',problem.f)]}
    with torch.no_grad():
        u0,v0,_ = field.fieldCalculation(problem.x)
        features = field.net.encode(problem.x)
        old_head = torch.cat((field.net.output_layer.weight[:2],field.net.output_layer.bias[:2,None]),dim=1).detach().clone()
        y = problem.x[:,1]
        bubble = (y+.5)*(.5-y)
        raw = field.net.output_layer(features)
        lift = .11999988*(y+.5)
        linear0 = [.11999988*bubble*raw[:,0]+lift*np.cos(np.pi/2),
                   .11999988*bubble*raw[:,1]+lift*np.sin(np.pi/2)]
        initial_realization_error = max(float((u0-linear0[0]).abs().max()),float((v0-linear0[1]).abs().max()))
        assert initial_realization_error <= 1e-12
    transform,phi,basis = conditioned_basis(features.cpu().numpy(),problem.mass.cpu().numpy(),bubble.cpu().numpy(),.11999988)
    phi = torch.as_tensor(phi,device=device,dtype=torch.float64)
    reduced = ReducedElastic(problem,phi,u0,v0)
    basis['preparation_seconds'] = time.monotonic()-budget.start
    basis['initial_encode_BC_network_maxabs_error'] = initial_realization_error
    dump(out/'basis.json',basis)
    np.savez_compressed(out/'basis.npz',transform=transform,theta0_head=old_head.cpu().numpy())
    first = budget.begin('initial_reduced_energy_gradient')
    e0,g0 = reduced.value_gradient(np.zeros(2*reduced.rank))
    first.update(completed=True,E_el=e0,gradient_l2=float(np.linalg.norm(g0)))
    source = budget.begin('source_energy_contract')
    with torch.no_grad():
        oracle = compute_energy(problem.x,u0,v0,problem.df,problem.hist,problem.mat,problem.model,problem.area,problem.cells,
                                f_fatigue=problem.f,irreversibility_penalty_cfg={'enable':True,'mode':'fem_gp_q4'})[0]
    source_error = abs(float(oracle)-e0)
    assert source_error <= 1e-10*max(1.,abs(e0))
    source.update(completed=True,E_el=float(oracle),cached_source_energy_error=source_error)
    if phase == 'probe':
        assert all(torch.equal(q,initial_parameters[name]) for name,q in field.net.state_dict().items())
        assert anchor == {name:tensor_hash(q) for name,q in field.alpha_constraint.state_dict().items()}
        free,total = torch.cuda.mem_get_info()
        assert free >= 3*1024**3, 'Probe leaves less than3GiB VRAM'
        result = dict(status='probe_passed',objective_gradient_evaluations=len(budget.trace),backwards=1,
                      optimizer_updates=0,hidden_updates=0,history_commits=0,rollout_steps=0,
                      hidden_and_damage_head_exactly_unchanged=True,Smooth_B0_anchor_unchanged=True,
                      basis=basis,source_energy_error=source_error,free_VRAM=free,total_VRAM=total)
        dump(out/'trace.json',budget.trace);dump(out/'result.json',result)
        return result
    row = budget.begin('native_FEM_force_contract')
    fem = node_readout(problem,problem.uf,problem.vf,phi,native_force=data['ru_fem'])
    assert fem['free_u_l2'] < 1e-8
    row.update(completed=True,**fem)
    row = budget.begin('initial_actual_network_readout')
    initial = node_readout(problem,u0,v0,phi)
    row.update(completed=True,**initial)
    last,accepted,solver = solve_reduced(reduced,budget,e0,g0)
    raw_head = old_head.cpu().numpy()+(transform@last['z'].reshape(2,reduced.rank).T).T
    np.savez_compressed(out/'accepted_reduced_candidate.npz',z=last['z'],raw_head=raw_head,
                        conditioned_E_el=last['value'],conditioned_gradient=last['gradient'])
    with torch.no_grad():
        h = torch.as_tensor(raw_head,device=device,dtype=torch.float64)
        field.net.output_layer.weight[:2].copy_(h[:,:-1]);field.net.output_layer.bias[:2].copy_(h[:,-1])
        u,v,_ = field.fieldCalculation(problem.x)
        linear_u,linear_v = reduced.fields(torch.as_tensor(last['z'],device=device,dtype=torch.float64))
    preserved = {}
    for name,q in field.net.state_dict().items():
        old = initial_parameters[name]
        preserved[name] = bool(torch.equal(q[2:],old[2:])) if name in ['output_layer.weight','output_layer.bias'] else bool(torch.equal(q,old))
    assert all(preserved.values())
    assert anchor == {name:tensor_hash(q) for name,q in field.alpha_constraint.state_dict().items()}
    assert frozen_physics == {name:tensor_hash(q) for name,q in [('damage',problem.df),('own_lower',problem.hist),('own_f',problem.f)]}
    actual = None
    try:
        row = budget.begin('final_installed_actual_network_readout',final=True)
        actual = node_readout(problem,u,v,phi)
        row.update(completed=True,**actual)
    except BudgetStop as err:
        # No post-deadline evaluation. The unverified reduced candidate is
        # preserved, but the last actually verified network remains theta0.
        solver['terminal_readout_missing'] = str(err)
    np.savez_compressed(out/'fields.npz',u=(u if actual else u0).cpu().numpy(),v=(v if actual else v0).cpu().numpy(),d=data['d_fem'])
    if actual:
        torch.save(field.net.state_dict(),out/'accepted_network.pt')
    result = dict(status='completed' if actual else 'partial_terminal_readout_missing',cycle=item['cycle'],substep=4,step=item['step'],
                  actual_network=actual,last_verified_network=actual if actual else initial,initial=initial,FEM=fem,
                  E_el=actual['E_el'] if actual else None,free_u_l2=actual['free_u_l2'] if actual else None,
                  uv_mass_rel_L2=actual['uv_mass_rel_L2'] if actual else None,uv_H1_rel=actual['uv_H1_rel'] if actual else None,
                  conditioned_E_el=last['value'],conditioned_gradient_l2=float(np.linalg.norm(last['gradient'])),
                  linear_vs_actual_uv_maxabs=max(float((u-linear_u).abs().max()),float((v-linear_v).abs().max())),
                  actual_minus_conditioned_energy=actual['E_el']-last['value'] if actual else None,
                  evaluations=len(budget.trace),cap=400,deadline_seconds=600.,elapsed_seconds=time.monotonic()-budget.start,
                  accepted_head_updates=len(accepted),hidden_and_damage_head_exactly_unchanged=all(preserved.values()),
                  Smooth_B0_anchor_unchanged=True,frozen_damage_lower_f_unchanged=True,history_commits=0,rollout_steps=0,weight_regularizer=0.,ridge=0.,
                  solver=solver,basis=basis,oracle_claim=False)
    dump(out/'accepted.json',accepted);dump(out/'trace.json',budget.trace);dump(out/'result.json',result)
    return result


def main(args):
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    assert not args.out.exists()
    contract = json.loads(args.contract.read_text())
    for item in contract.get('files',[]):
        path = Path(item['path'])
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    device = torch.device(args.device)
    assert device.type == 'cuda' and torch.cuda.is_available(), 'No Mac/CPU production or training fallback'
    assert contract.get('protocol',PROTOCOL) == PROTOCOL
    torch.cuda.reset_peak_memory_stats()
    args.out.mkdir(parents=True)
    dump(args.out/'receipt.json',dict(protocol=PROTOCOL,commit=contract['commit'],run_id=contract['run_id'],
         phase=args.phase,pid=os.getpid(),host=os.uname().nodename,device=str(device),CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
         command=sys.argv,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),history_commits=0,rollout_steps=0))
    rows = []
    try:
        for item in contract['states'][:1] if args.phase == 'probe' else contract['states']:
            rows.append(run_state(item,args.out/f'c{item["cycle"]}_s4',device,args.phase))
            dump(args.out/'rows.json',rows)
            if args.phase == 'probe':
                dump(args.out/'probe_pass.json',{**rows[-1],'status':'passed','peak_allocated':torch.cuda.max_memory_allocated(),
                                                'hidden_updates':0,'optimizer_updates':0,'history_commits':0})
            if rows[-1]['status'].startswith('partial'):
                break
        dump(args.out/'complete.json',dict(status='completed' if all(r['status'] in ['completed','probe_passed'] for r in rows) else 'partial',
             states=len(rows),history_commits=0,rollout_steps=0,phase=args.phase))
    except Exception as err:
        dump(args.out/'failure.json',dict(type=type(err).__name__,message=str(err),completed_states=len(rows),history_commits=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--phase',choices=['probe','production'],required=True)
    parser.add_argument('--device',default='cuda')
    main(parser.parse_args())
