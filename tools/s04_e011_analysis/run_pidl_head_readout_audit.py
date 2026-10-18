#!/usr/bin/env python3
"""Zero-update repetition audit; stationarity thresholds are labels, never gates."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,os,sys,time
from pathlib import Path
import numpy as np
import torch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_pidl_block_diagnosis import LocalProblem,make_smooth,sha,dump,tensor_hash
from run_pidl_energy_head import conditioned_basis
from run_pidl_head_newton import JournalBudget,BudgetStop
from run_pidl_hidden_newton import snapshot
from compute_energy import compute_energy

PROTOCOL='S04-E011-HEAD-READOUT-AUDIT-r1'
GTOL=1e-10
SOURCE_ENERGY=.005268400005223913


def finite_arrays(arrays):
    return all(np.isfinite(np.asarray(x)).all() for x in arrays.values())


def state_digest(state):
    h=hashlib.sha256()
    for name in sorted(state):
        a=state[name].detach().cpu().contiguous().numpy()
        h.update(name.encode());h.update(str(a.dtype).encode());h.update(str(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()


def projected_label(vector):
    a=np.asarray(vector);norm=float(np.linalg.norm(a));inf=float(np.max(abs(a)))
    return dict(gradient_l2=norm,gradient_inf=inf,gradient_inf_tolerance=GTOL,
                below_or_equal_threshold=bool(inf<=GTOL),threshold_is_readout_label_only=True)


def observation_json(value):
    """Preserve finite flags and JSON nulls instead of losing a nonfinite attempt."""
    if isinstance(value,dict):return {k:observation_json(v) for k,v in value.items()}
    if isinstance(value,list):return [observation_json(v) for v in value]
    if isinstance(value,(float,np.floating)) and not np.isfinite(value):return None
    return value


def save_force(folder,label,fields,gu,gv,info,extra=None):
    arrays={**fields,'gu':gu,'gv':gv,**(extra or {})}
    np.savez_compressed(folder/(label+'.npz'),**arrays)
    dump(folder/(label+'.json'),observation_json({**info,'label':label,'arrays_finite':finite_arrays(arrays)}))
    assert finite_arrays(arrays),'nonfinite fields or forces; attempt arrays were preserved'


def raw_network_force(field,problem,budget,label,folder):
    row=budget.begin(label);named=list(field.net.named_parameters());flags=[p.requires_grad for _,p in named]
    try:
        for _,p in named:p.requires_grad_(True)
        field.net.zero_grad(set_to_none=True)
        u,v,unused_d=field.fieldCalculation(problem.x)
        energy=problem.parts(u,v,problem.df)[0]
        gradients=torch.autograd.grad(energy,tuple(p for _,p in named)+(u,v),allow_unused=True)
        parameter_rows=[];groups={'hidden':[],'uv_head':[]};head_gradients={}
        for (name,p),g in zip(named,gradients[:-2]):
            g=torch.zeros_like(p) if g is None else g
            a=g.detach().cpu().numpy()
            parameter_rows.append(dict(name=name,shape=list(a.shape),finite=bool(np.isfinite(a).all()),
                raw_gradient_l2=float(np.linalg.norm(a)),raw_gradient_inf=float(np.max(abs(a)))))
            groups['uv_head' if name.startswith('output_layer.') else 'hidden'].append(
                (g[:2] if name.startswith('output_layer.') else g).reshape(-1))
            if name.startswith('output_layer.'):head_gradients[name]=g[:2].detach()
        fields=dict(u=u.detach().cpu().numpy(),v=v.detach().cpu().numpy(),d=problem.df.cpu().numpy())
        gu,gv=[a.detach().cpu().numpy() for a in gradients[-2:]]
        info=dict(label=label,E_el=float(energy.detach()),objective='raw_Eel',field_source='independent_full_network_forward',
            parameter_gradients=parameter_rows,unused_NN_damage_min=float(unused_d.detach().min()),
            unused_NN_damage_max=float(unused_d.detach().max()))
        for group,values in groups.items():
            g=torch.cat(values);info[group+'_gradient_l2']=float(torch.linalg.vector_norm(g));info[group+'_gradient_inf']=float(g.abs().max())
        raw_head=torch.cat((head_gradients['output_layer.weight'],head_gradients['output_layer.bias'][:,None]),dim=1).cpu().numpy()
        assert raw_head.shape==(2,401)
        info['raw_UV_head_gradient_shape']=[2,401]
        save_force(folder,label,fields,gu,gv,info,extra={'raw_head_gradient':raw_head})
        assert all(p['finite'] for p in parameter_rows) and np.isfinite(info['E_el'])
        row.update(completed=True,E_el=info['E_el']);dump(budget.folder/'trace.json',budget.trace)
        return fields,gu,gv,info
    finally:
        for (_,p),flag in zip(named,flags):p.requires_grad_(flag)
        field.net.zero_grad(set_to_none=True)


def leaf_force(problem,fields,budget,label,folder):
    row=budget.begin(label)
    u=torch.as_tensor(fields['u'],device=problem.device).clone().requires_grad_(True)
    v=torch.as_tensor(fields['v'],device=problem.device).clone().requires_grad_(True)
    energy=problem.parts(u,v,problem.df)[0];gu,gv=torch.autograd.grad(energy,(u,v))
    gu,gv=[x.detach().cpu().numpy() for x in [gu,gv]]
    info=dict(label=label,E_el=float(energy.detach()),objective='raw_Eel',field_source='cached_network_0_nodal_leaves')
    save_force(folder,label,fields,gu,gv,info);assert np.isfinite(info['E_el'])
    row.update(completed=True,E_el=info['E_el']);dump(budget.folder/'trace.json',budget.trace)
    return gu,gv,info


def cpu_mass(cells,contributions,n):
    mass=np.zeros(n,dtype=np.float64)
    for j in range(4):np.add.at(mass,cells[:,j],contributions[:,j])
    return mass


def save_basis(folder,name,transform,phi,metadata):
    out=folder/name;out.mkdir()
    np.save(out/'transform.npy',transform);np.save(out/'phi.npy',phi)
    dump(out/'metadata.json',{**metadata,'transform_shape':list(transform.shape),'phi_shape':list(phi.shape),
        'finite':bool(np.isfinite(transform).all() and np.isfinite(phi).all())})
    assert np.isfinite(transform).all() and np.isfinite(phi).all()


def check_time(budget):
    if time.monotonic()-budget.start>=budget.seconds:raise BudgetStop('wall_deadline')


def run_state(item,out,device):
    out.mkdir();budget=JournalBudget(out);budget.cap=32;budget.seconds=600.
    assert (item['cycle'],item['substep'],item['step'])==(20,4,99)
    assert sha(item['source_fields'])==item['source_fields_sha256']
    data=dict(np.load(item['input'],allow_pickle=False));problem=LocalProblem(data,device)
    original=torch.load(item['original_model'],map_location=device,weights_only=True)
    initial=torch.load(item['initial_model'],map_location=device,weights_only=True)
    field=make_smooth(original,problem);field.net.load_state_dict(initial);field.net.requires_grad_(False)
    assert not field.williams_enabled and not field.ansatz_enabled and not field.exact_bc_enabled and not field.symmetry_prior
    before=snapshot(field.net);anchor={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
    physical={n:tensor_hash(x) for n,x in [('d',problem.df),('lower',problem.hist),('f',problem.f)]}
    for name in ['forces','bases','cache','mass']:(out/name).mkdir()
    torch.save(before,out/'weights_before.pt')
    basis_source=dict(np.load(item['source_basis'],allow_pickle=False));source_t=basis_source['transform']
    dump(out/'source_basis_identity.json',dict(path=item['source_basis'],sha256=sha(item['source_basis']),
        shape=list(source_t.shape),expected_shape=[401,386],shape_matches=source_t.shape==(401,386)))
    assert source_t.shape==(401,386) and np.isfinite(source_t).all(),'saved basis identity mismatch'
    forces={};network_rows=[];cached=None
    with np.load(item['source_fields'],allow_pickle=False) as z:source_fields={k:z[k] for k in ['u','v','d']}
    for index in range(3):
        fields,gu,gv,info=raw_network_force(field,problem,budget,f'network_{index}',out/'forces')
        if cached is None:
            cached={k:a.copy() for k,a in fields.items()};np.savez_compressed(out/'cache'/'fields.npz',**cached)
        info.update(field_maxabs_vs_cached={k:float(np.max(abs(fields[k]-cached[k]))) for k in fields},
            field_maxabs_vs_source={k:float(np.max(abs(fields[k]-source_fields[k]))) for k in fields},
            energy_error_vs_source=abs(info['E_el']-SOURCE_ENERGY))
        dump(out/'forces'/f'network_{index}.json',info)
        network_rows.append(info);forces[f'network_{index}']=(gu,gv)
        source_ok=max(info['field_maxabs_vs_source'].values())<=1e-12 and info['energy_error_vs_source']<=1e-10
        dump(out/'source_reproduction_attempts.json',network_rows)
        assert source_ok,'source field/energy mismatch; observed attempt saved before stopping'
        assert all(torch.equal(p,before[n]) for n,p in field.net.state_dict().items())
    for index in range(5):
        gu,gv,info=leaf_force(problem,cached,budget,f'nodal_{index}',out/'forces');forces[f'nodal_{index}']=(gu,gv)
    # Fixed geometry source contracts; each energy/gradient graph is counted.
    row=budget.begin('source_energy_contract')
    with torch.no_grad():
        oracle=compute_energy(problem.x,torch.as_tensor(cached['u'],device=device),torch.as_tensor(cached['v'],device=device),
            problem.df,problem.hist,problem.mat,problem.model,problem.area,problem.cells,f_fatigue=problem.f,
            irreversibility_penalty_cfg={'enable':True,'mode':'fem_gp_q4'})[0]
    row.update(completed=True,E_el=float(oracle),source_error=abs(float(oracle)-network_rows[0]['E_el']))
    dump(out/'source_energy_contract.json',row);assert row['source_error']<=1e-10
    row=budget.begin('native_FEM_force_contract')
    uf=problem.uf.detach().clone().requires_grad_(True);vf=problem.vf.detach().clone().requires_grad_(True)
    e=problem.parts(uf,vf,problem.df)[0];gu,gv=torch.autograd.grad(e,(uf,vf));force=torch.cat((gu,gv))
    err=float((force-torch.as_tensor(data['ru_fem'],device=device)).abs().max());free=float(torch.linalg.vector_norm(force[problem.fu]))
    row.update(completed=True,E_el=float(e.detach()),native_force_maxabs=err,free_u_l2=free)
    np.savez_compressed(out/'native_fem_force.npz',gu=gu.cpu().numpy(),gv=gv.cpu().numpy());dump(out/'native_fem_contract.json',row)
    assert err<=1e-10 and free<1e-8
    check_time(budget)
    with torch.no_grad():features=field.net.encode(problem.x).cpu().numpy()
    bubble=((problem.x[:,1]+.5)*(.5-problem.x[:,1])).cpu().numpy();mass0=problem.mass.cpu().numpy()
    np.save(out/'cache'/'features.npy',features);np.save(out/'cache'/'bubble.npy',bubble);np.save(out/'mass'/'mass0.npy',mass0)
    contributions=torch.stack([(problem.w*problem.N[:,j]).sum(1) for j in range(4)],dim=1)
    mass_rows=[]
    for index in range(3):
        check_time(budget);mass=torch.zeros_like(problem.mass)
        for j in range(4):mass.scatter_add_(0,problem.cells[:,j],contributions[:,j])
        a=mass.cpu().numpy();np.save(out/'mass'/f'gpu{index}.npy',a)
        mass_rows.append(dict(label=f'gpu{index}',maxabs_vs_mass0=float(np.max(abs(a-mass0))),l2_vs_mass0=float(np.linalg.norm(a-mass0))))
    cells=problem.cells.cpu().numpy();cm=cpu_mass(cells,contributions.cpu().numpy(),problem.n)
    np.save(out/'mass'/'cpu_add_at.npy',cm)
    w=problem.w.cpu().numpy();N=problem.N.cpu().numpy();c2=np.column_stack([(w*N[:,j]).sum(1) for j in range(4)])
    np.save(out/'mass'/'cpu_numpy_element_sums.npy',cpu_mass(cells,c2,problem.n))
    dump(out/'mass'/'metadata.json',dict(repetitions=mass_rows,cpu_add_at_uses_same_GPU_element_contributions=True,
        cpu_add_at_maxabs_vs_mass0=float(np.max(abs(cm-mass0))),basis_mass='mass0 only; no mass-dependent SVD arms'))
    design=.11999988*bubble[:,None]*np.column_stack((features,np.ones(len(features))))
    bases={'source':design@source_t};save_basis(out/'bases','source',source_t,bases['source'],dict(source_saved_transform=True,retained_rank=386))
    for index in range(3):
        check_time(budget);transform,phi,metadata=conditioned_basis(features,mass0,bubble,.11999988)
        metadata.update(fixed_cutoff_policy=True,no_rank_scan=True,no_sensitivity_solves=True,source_rank_comparison_only=386,
            rank_matches_source=metadata['retained_rank']==386,basis_mass='mass0',cached_features=True)
        save_basis(out/'bases',f'fresh{index}',transform,phi,metadata);bases[f'fresh{index}']=phi
    projections=[];vectors={}
    for bname,phi in bases.items():
        check_time(budget);p=torch.as_tensor(phi,device=device,dtype=torch.float64)
        for fname,(gu,gv) in forces.items():
            check_time(budget);g=torch.cat((p.T@torch.as_tensor(gu,device=device),p.T@torch.as_tensor(gv,device=device))).cpu().numpy()
            key=f'{fname}__{bname}';vectors[key]=g
            np.savez_compressed(out/'projections.npz',**vectors)  # vector persists BEFORE threshold label.
            projections.append(dict(force=fname,basis=bname,**projected_label(g)))
            dump(out/'projections.json',projections)
    p=torch.as_tensor(bases['source'],device=device);gu,gv=forces['network_0'];repeat=[]
    for _ in range(5):
        check_time(budget);repeat.append(torch.cat((p.T@torch.as_tensor(gu,device=device),p.T@torch.as_tensor(gv,device=device))).cpu().numpy())
        np.save(out/'fixed_projection_repeat.npy',np.stack(repeat))
    check_time(budget);after=snapshot(field.net);torch.save(after,out/'weights_after.pt')
    assert all(torch.equal(after[n],before[n]) for n in before)
    assert anchor=={n:tensor_hash(p) for n,p in field.alpha_constraint.state_dict().items()}
    assert physical=={n:tensor_hash(x) for n,x in [('d',problem.df),('lower',problem.hist),('f',problem.f)]}
    result=dict(status='completed',cycle=20,substep=4,step=99,network_repetitions=3,nodal_repetitions=5,fresh_svd_repetitions=3,
        evaluations=len(budget.trace),cap=32,deadline_seconds=600,elapsed_seconds=time.monotonic()-budget.start,
        optimizer_updates=0,parameter_updates=0,history_commits=0,rollout_steps=0,weights_exact_unchanged=True,
        weights_before_sha256=state_digest(before),weights_after_sha256=state_digest(after),Smooth_B0_anchor_unchanged=True,
        mechanical_damage_exact_FEM=True,physical_state_exact_unchanged=True,threshold_is_readout_label_only=True,
        gradient_inf_tolerance=GTOL,source_energy=SOURCE_ENERGY,network_readouts=network_rows,projections=projections,
        source_basis_shape=[401,386],fresh_ranks={name:int(phi.shape[1]) for name,phi in bases.items()},
        cached_features_encode_count=1,basis_mass='mass0 only',ridge=0.,training=False)
    dump(out/'result.json',result);dump(out/'trace.json',budget.trace);return result


def main(args):
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    contract=json.loads(args.contract.read_text());assert contract['protocol']==PROTOCOL
    assert contract['cap']==32 and contract['deadline_seconds']==600 and len(contract['states'])==1
    assert contract['network_repetitions']==3 and contract['nodal_repetitions']==5 and contract['fresh_svd_repetitions']==3
    for entry in contract.get('files',[]):
        p=Path(entry['path']);assert p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256']
    assert not args.out.exists();device=torch.device(args.device)
    assert device.type=='cuda' and torch.cuda.is_available(),'No real-network Mac/CPU audit'
    args.out.mkdir(parents=True)
    dump(args.out/'receipt.json',dict(protocol=PROTOCOL,commit=contract['commit'],run_id=contract['run_id'],pid=os.getpid(),
        host=os.uname().nodename,command=sys.argv,CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
        started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),optimizer_updates=0,history_commits=0))
    try:
        result=run_state(contract['states'][0],args.out/'c20_s4',device);dump(args.out/'rows.json',[result]);dump(args.out/'complete.json',dict(status='completed',states=1))
    except Exception as err:
        dump(args.out/'failure.json',dict(type=type(err).__name__,message=str(err),optimizer_updates=0,history_commits=0));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--device',default='cuda');main(parser.parse_args())
