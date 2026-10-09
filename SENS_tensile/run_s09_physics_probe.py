#!/usr/bin/env python3
"""S09-E003: native FEM physics audit and one-state equilibrium-only PINN probe."""
import argparse, csv, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from s09_fem_physics import *


def dump(p,obj):
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def load(path,device):
    with np.load(path,allow_pickle=False) as a:
        return {k:torch.tensor(a[k],device=device,dtype=torch.long if k=='conn' else torch.float64) for k in a.files}


def audit(a):
    n,b,w=q4_shape_data(a['xy'],a['conn'])
    force,f=equilibrium(a['u'],a['d'],a['conn'],n,b,w)
    errors={}
    for k,actual in [('psi',f['psi']),('g',f['g']),('strain',f['strain'])]:
        errors[k]=float(torch.linalg.vector_norm(actual-a[k])/torch.linalg.vector_norm(a[k]).clamp_min(1e-30))
    dg=q4_interpolate(a['d'],a['conn'],n)
    errors['d_gp']=float(torch.max(torch.abs(dg-a['d_gp'])))
    top=torch.isclose(a['xy'][:,1],a['xy'][:,1].max(),atol=1e-10,rtol=0)
    bottom=torch.isclose(a['xy'][:,1],a['xy'][:,1].min(),atol=1e-10,rtol=0)
    expected=torch.zeros_like(a['u']);expected[top,1]=a['load']
    errors['dirichlet_max_abs']=float(torch.max(torch.abs(a['u'][~boundary(a['xy'])]-expected[~boundary(a['xy'])])))
    return {'errors':errors,'pass':all(v<=1e-8 for v in errors.values()),
        'native_free_force_rms':float(force[boundary(a['xy'])].square().mean().sqrt()),
        'nodes':len(a['xy']),'elements':len(a['conn']), 'area':float(w.sum()),
        'state':'U012 cycle76 substep4 accepted peak; frozen damage only',
        'not_teacher_qualification':True}


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--audit-only',action='store_true')
    p.add_argument('--expected-commit');args=p.parse_args()
    expected_input='fe7aff6a1af536eca0182258276d680499d8aafeef0ec17c74502d1ddad04ffc'
    if hashlib.sha256(args.input.read_bytes()).hexdigest()!=expected_input:raise RuntimeError('Frozen input identity mismatch')
    root=Path(__file__).resolve().parents[1]
    def git(*cmd):return subprocess.check_output(['git',*cmd],cwd=root,text=True).strip()
    if not args.audit_only:
        if platform.system()!='Linux' or platform.node()!='GPUServer8':raise RuntimeError('Taobo only; no Mac training')
        if not os.getenv('CUDA_VISIBLE_DEVICES') or not torch.cuda.is_available():raise RuntimeError('Explicit healthy CUDA required')
        if git('rev-parse','HEAD')!=args.expected_commit or git('status','--porcelain'):raise RuntimeError('Exact clean release required')
        if not str(args.out.resolve()).startswith('/mnt/data2/drtao/wennie/'):raise RuntimeError('Wrong output root')
        torch.cuda.set_per_process_memory_fraction(.33)
    args.out.mkdir(parents=True,exist_ok=False)
    device='cpu' if args.audit_only else 'cuda'
    torch.set_num_threads(4);torch.manual_seed(1)
    a=load(args.input,device);result=audit(a);dump(args.out/'physics_audit.json',result)
    if not result['pass']:raise RuntimeError('Native kinematics/physics identity mismatch')
    if args.audit_only:return
    started=time.time();receipt={'experiment_id':'S09-E003','protocol':'v1-equilibrium-pinn-c0',
        'commit':args.expected_commit,'dirty':git('status','--porcelain'),'hostname':platform.node(),
        'pid':os.getpid(),'command':sys.argv,'started_unix':started,'gpu':os.getenv('CUDA_VISIBLE_DEVICES'),
        'torch':torch.__version__,'input_sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),
        'execution_status':'running','retrieval':'pending','updates_budget':500,'seed':1}
    dump(args.out/'receipt.json',receipt)
    n,b,w=q4_shape_data(a['xy'],a['conn']);free=boundary(a['xy'])
    model=DisplacementPINN().to(device=device,dtype=torch.float64)
    opt=torch.optim.Adam(model.parameters(),lr=.001)
    def evaluate():
        u=model(a['xy'],a['load']);force,f=equilibrium(u,a['d'],a['conn'],n,b,w)
        return u,force,f
    with torch.no_grad():
        u,force,f=evaluate();initial=force[free].square().mean().detach()
        if not torch.isfinite(initial) or initial<=0:raise RuntimeError('Invalid initial normalizer')
    rows=[];best=float('inf')
    try:
        for step in range(501):
            opt.zero_grad(set_to_none=True);u,force,f=evaluate()
            loss=force[free].square().mean()/initial
            if not torch.isfinite(loss):raise FloatingPointError('Nonfinite physics loss')
            if step%25==0:
                ratio=float(loss.detach().sqrt());row={'step':step,'force_rms_ratio_to_affine':ratio,
                    'force_rms':float(force[free].detach().square().mean().sqrt()),
                    'u_rel_l2_to_native_diagnostic':float(torch.linalg.vector_norm(u.detach()-a['u'])/torch.linalg.vector_norm(a['u'])),
                    'elapsed_s':time.time()-started}
                rows.append(row);print(json.dumps(row),flush=True)
                if ratio<best:
                    best=ratio;torch.save(model.state_dict(),args.out/'best.pt')
                    np.savez_compressed(args.out/'best_fields.npz',xy=a['xy'].cpu().numpy(),d=a['d'].cpu().numpy(),
                        u=u.detach().cpu().numpy(),u_native=a['u'].cpu().numpy(),force=force.detach().cpu().numpy(),
                        free=free.cpu().numpy(),step=step)
            if step==500:
                np.savez_compressed(args.out/'final_fields.npz',xy=a['xy'].cpu().numpy(),d=a['d'].cpu().numpy(),
                    u=u.detach().cpu().numpy(),u_native=a['u'].cpu().numpy(),force=force.detach().cpu().numpy(),
                    free=free.cpu().numpy(),step=step)
                break
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),10.,error_if_nonfinite=True);opt.step()
        final=rows[-1];verdict=final['force_rms_ratio_to_affine']<=.8
        dump(args.out/'metrics.json',{'final':final,'best_evaluated_ratio':best,'primary_threshold':.8,
            'primary_pass':verdict,'criterion':'final free-force RMS / initial affine RMS <= 0.8',
            'scope':'single-state fixed-damage weak-form PINN optimization diagnostic; not PINO or fracture forecast',
            'native_free_force_rms':result['native_free_force_rms']})
        receipt.update(execution_status='succeeded',updates=500,scientific_status='c0_probe_pass' if verdict else 'c0_probe_fail')
    except Exception as e:
        receipt.update(execution_status='failed',error=repr(e));raise
    finally:
        with (args.out/'history.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['step']);writer.writeheader();writer.writerows(rows)
        receipt.update(elapsed_s=time.time()-started,cuda_peak_memory_bytes=torch.cuda.max_memory_allocated())
        dump(args.out/'receipt.json',receipt)
if __name__=='__main__':main()
