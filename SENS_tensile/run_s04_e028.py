"""Independent, single-attempt E028 producer runner. No default execution."""
import argparse
import copy
import csv
import json
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import time
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
import s04_e027 as old
import s04_e028 as m
from run_s04_e027 import initializer_compatibility, deadline_signal
LOCK=ROOT/'docs/research/S04/S04-E028/data_lock.json'


def dump(p,v): p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')


def device_admission(grant):
    gpu=os.environ.get('CUDA_VISIBLE_DEVICES','')
    if not gpu or ',' in gpu or grant.get('cuda_visible_devices')!=gpu:
        raise PermissionError('explicit single GPU required')
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1:
        raise PermissionError('exactly one visible CUDA producer required')
    uuid=subprocess.check_output(['nvidia-smi','-i',gpu,'--query-gpu=uuid','--format=csv,noheader'],text=True).strip()
    if not uuid or uuid!=grant.get('gpu_uuid'):raise PermissionError('actual GPU UUID mismatch')
    return uuid


def admit(lock,grant,out):
    if platform.system()=='Darwin': raise PermissionError('Mac training prohibited')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    if dirty or grant.get('approved_commit')!=head or lock['protocol']!=m.PROTOCOL or grant.get('protocol')!=m.PROTOCOL:
        raise PermissionError('clean exact source/protocol required')
    if grant.get('execution_authorized') is not True or not grant.get('review_reference') or not grant.get('human_approval_reference'):
        raise PermissionError('authorization/review references required')
    if (grant.get('gpu_hours_cap'),grant.get('ram_gib_cap'),grant.get('output_gib_cap'))!=(2,32,2):
        raise PermissionError('fixed budget mismatch')
    if grant.get('hostname')!=platform.node() or grant.get('output')!=str(out.resolve()):
        raise PermissionError('host/output mismatch')
    uuid=device_admission(grant)
    if out.exists(): raise FileExistsError('fresh output only; no retry')
    return head,uuid


def render(p,predictions,records,scores,out,receipt):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    polygons=p.xy[p.conn].cpu().numpy()
    display={}
    with torch.no_grad():
        for key,values in predictions.items():
            q=torch.as_tensor(values,device=p.xy.device,dtype=torch.float64)
            parts=p.parts(*q.unbind(1))
            gp=[old.q4_interpolate(q[:,j],p.conn,p.N) for j in range(3)]+[parts[3],parts[4]]
            display[key]=[((x*p.w).sum(1)/p.w.sum(1)).cpu().numpy() for x in gp]
    names=list(predictions)
    for error,stem in [(False,'fields'),(True,'errors')]:
        cols=names[1:] if error else names
        fig,axes=plt.subplots(5,len(cols),figsize=(3*len(cols),14),squeeze=False,layout='constrained')
        for j,channel in enumerate(['u','v','d','raw','active']):
            vals=[display[k][j]-display['reference'][j] if error else display[k][j] for k in cols]
            if error:
                hi=max(float(abs(x).max()) for x in vals) or 1e-30;lo=-hi
            else: lo=min(float(x.min()) for x in vals);hi=max(float(x.max()) for x in vals)
            for ax,key,val in zip(axes[j],cols,vals):
                im=PolyCollection(polygons,array=val,cmap='RdBu_r' if error else 'viridis',edgecolors='none',antialiased=False)
                im.set_clim(lo,hi);ax.add_collection(im);ax.autoscale_view();ax.set_aspect('equal')
                ax.set_title(f'{channel}: {key}'+('-FEM' if error else ''));ax.set_xlabel('x');ax.set_ylabel('y')
            fig.colorbar(im,ax=list(axes[j]),shrink=.75)
        fig.suptitle('E028 | exposed synthetic c20s4 / horizon0 / seed1 | '+('signed errors' if error else 'native Q4 element means'))
        fig.savefig(out/f'{stem}.png',dpi=130);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,3.6),layout='constrained')
    for arm in ['B','R']:
        rows=[r for r in records if r['arm']==arm]
        axs[0].semilogy([r['step'] for r in rows],[max(1e-30,r['L_U']+r['L_D']) for r in rows],label=arm)
        axs[1].semilogy([r['step'] for r in rows],[max(1e-30,r['L_active']) for r in rows],label=arm)
    for ax,title in zip(axs,['sampled Lsup','full Z active squared error']):
        ax.set(xlabel='new optimizer update',ylabel=title,title=title);ax.legend()
    fig.suptitle('Optimization trace; not physical evolution');fig.savefig(out/'trace.png',dpi=160);plt.close(fig)
    for stem in ['fields','errors','trace']:
        guide={'fields':'Rows u/v/d/raw/active; columns reference, original common initial, original S/C, mapped new start, B/R. Native Q4 Jacobian-weighted element means with one shared raw scale per row, no clipping.',
               'errors':'Rows u/v/d/raw/active; each column is prediction minus exact FEM reference, one shared symmetric scale per row; native Q4 Jacobian-weighted element means.',
               'trace':'Left sampled LU+LD and right full-support LA versus new optimizer updates. B and R legends; log display floor1e-30 only for plotting. Objectives are optimization traces, not physical histories.'}[stem]
        (out/f'{stem}.md').write_text(f'''# How to read {stem}.png
\n## Figure question
Does directly supervising active energy improve a bounded single-state repair compared with matched feasible pure supervision?
\n## Data provenance
Run output {out}; exact commit {receipt['commit']}; protocol {m.PROTOCOL}. Same scored fields.npz/scores.json/loss_trace.json and four MATs in data_lock.json. c20s4 / horizon0 / seed1 / U=.11999988. Plotting script SENS_tensile/run_s04_e028.py. All nodal fields are on the identical original Q4 mesh.
\n## Visual grammar and panel guide
{guide}
\n## Key numerical takeaway
{json.dumps(scores.get('decision',{}))}. Inspect complete component/feasibility table in scores.json and metrics.csv. Earlier E027 results are frozen descriptive controls; mapped0 shows representation changes separately from optimization.
\n## Limitations and claim boundary
Single exposed synthetic state, no holdout or generalization/physical-evolution validation. No profile-width inference. Large raw-field extrema can hide local contrast; scalar primary uses the full native GP4 Z support. Common mapped0 is shared by B/R; old initial and old S/C have different representation and objective. Direct FEM active supervision is an explicit development target, not independent validation. A primary directional gain can coexist with harmful component costs; inspect both.
''')


def run(lock,grant,out):
    head,actual_uuid=admit(lock,grant,out)
    free,total=torch.cuda.mem_get_info()
    if free<20*1024**3: raise MemoryError('less than20GiB initial GPU free')
    cap=free-1024**3;torch.cuda.set_per_process_memory_fraction(cap/total,0)
    started=time.monotonic();out.mkdir(parents=True)
    receipt=dict(protocol=m.PROTOCOL,commit=head,execution='preflight',host=platform.node(),pid=os.getpid(),
        gpu=torch.cuda.get_device_name(0),gpu_uuid=actual_uuid,cuda_visible_devices=os.environ['CUDA_VISIBLE_DEVICES'],
        command=sys.argv,optimizer_steps=0,optimizer_step_calls=0,history_commits=0,retry=False,
        initial_free_cuda_bytes=free,cuda_cap_bytes=cap,source_dirty=False)
    def guard():
        torch.cuda.synchronize()
        if time.monotonic()-started>7200:raise TimeoutError('2GPU-hour joint wall cap')
        if torch.cuda.max_memory_reserved()>cap or torch.cuda.mem_get_info()[0]<1024**3:raise MemoryError('GPU cap/headroom')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>32*1024**3:raise MemoryError('RSS cap')
        if sum(x.stat().st_size for x in out.rglob('*') if x.is_file())>2*1024**3:raise OSError('output cap')
    try:
        dump(out/'data_lock.json',lock)
        parent=Path(grant['parent_output'])
        for row in lock['parent_payloads'].values():old.verify_payload(parent,row)
        state,compat=initializer_compatibility(parent/'S_1500.pt',{'initializer':lock['parent_payloads']['S_1500.pt']})
        dump(out/'start_compatibility.json',compat)
        arrays=old.load_reference(Path(grant['data_root']),lock['reference_lock'])
        p=old.Problem(arrays,'cuda:0');m.validate_current_lower(p);guard()
        prior_copy=p.previous.clone();fatigue_copy=p.f.clone()
        smodel=old.make_model(state,'cuda:0')
        original=np.load(parent/'predictions.npz')
        if not np.array_equal(original['reference'],arrays['ref']):raise ValueError('parent/reference identity mismatch')
        before=old.fields(smodel,p.xy).detach()
        if not np.allclose(before.cpu().numpy(),original['S'],atol=1e-10,rtol=1e-10):raise ValueError('original S replay mismatch')
        initial_payload=torch.load(parent/'initial_state.pt',map_location='cpu',weights_only=True)
        imodel=old.make_model(initial_payload['model'],'cuda:0')
        initial=old.fields(imodel,p.xy).detach();del imodel,initial_payload
        initial_scores=m.component_scores(p,initial)
        if abs(initial_scores['active_error']-.2840885942769706)>1e-8:raise ValueError('original common initial replay mismatch')
        bmodel,rmodel=copy.deepcopy(smodel),copy.deepcopy(smodel);del smodel
        q0=m.fields(bmodel,p);m.check_physical(p,q0)
        common_scores=m.component_scores(p,q0)
        predictions=dict(reference=arrays['ref'],initial=initial.cpu().numpy(),original_S=original['S'],original_C=original['C'],mapped0=q0.detach().cpu().numpy())
        np.savez_compressed(out/'comparison_start.npz',**predictions)
        dump(out/'start_scores.json',dict(initial=initial_scores,mapped0=common_scores))
        del before,initial,q0
        # CPU-only RNG; draw identical streams independently from seed1.
        rngs={k:torch.Generator().manual_seed(1) for k in ['B','R']}
        models={'B':bmodel,'R':rmodel}
        opts={k:torch.optim.Adam(v.parameters(),lr=1e-4,betas=(.9,.999),eps=1e-8,weight_decay=0) for k,v in models.items()}
        if not all(torch.equal(a,b) and a.data_ptr()!=b.data_ptr() for a,b in zip(bmodel.parameters(),rmodel.parameters())):raise ValueError('fork mismatch')
        dump(out/'initial_identity.json',dict(parameters_equal=True,independent_models=True,empty_Adam=all(not o.state for o in opts.values()),seed=1,lower='locked c20s3',precrack_nodes=251,mechanical_weight=0.))
        benchmark={}
        for arm in ['B','R']:
            model=models[arm];t=time.monotonic()
            for _ in range(3):
                guard();model.zero_grad(set_to_none=True);q=m.fields(model,p)
                loss,_=m.objective(p,model,q,p.sample(torch.Generator().manual_seed(1)),arm=='R');loss.backward()
                del q,loss
            torch.cuda.synchronize();benchmark[arm]=(time.monotonic()-t)/3
            model.zero_grad(set_to_none=True)
        estimate=time.monotonic()-started+1.5*m.STEPS*sum(benchmark.values())+900
        if estimate>7200:raise TimeoutError('conservative preflight cost estimate exceeds cap')
        dump(out/'preflight.json',dict(benchmark_seconds=benchmark,estimate_seconds=estimate,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved()))
        scores={'initial':initial_scores,'original_S':m.component_scores(p,torch.as_tensor(predictions['original_S'],device=p.xy.device,dtype=torch.float64)),
                'original_C':m.component_scores(p,torch.as_tensor(predictions['original_C'],device=p.xy.device,dtype=torch.float64)),'mapped0':common_scores}
        milestones=[];records=[];receipt['execution']='running';dump(out/'receipt.json',receipt)
        for arm in ['B','R']:
            model,opt,rng=models[arm],opts[arm],rngs[arm]
            milestones.append(dict(arm=arm,step=0,scores=common_scores,representation=m.representation_stats(model,p)))
            for step in range(1,m.STEPS+1):
                guard();opt.zero_grad(set_to_none=True);q=m.fields(model,p);m.check_physical(p,q)
                loss,log=m.objective(p,model,q,p.sample(rng),arm=='R');loss.backward()
                for param in model.parameters():
                    if param.grad is None:raise ValueError('missing gradient')
                    old.finite(param.grad,'gradient')
                receipt['optimizer_step_calls']+=1;receipt['optimizer_attempt']='in_progress_or_unknown'
                opt.step()
                for param in model.parameters():old.finite(param,'updated parameter')
                receipt['optimizer_steps']+=1;receipt['optimizer_attempt']='completed_finite'
                row=dict(arm=arm,step=step,total_loss=float(loss.detach()),**log);records.append(row)
                with (out/'loss_trace.jsonl').open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
                del q,loss
                if step in [10,50,100,200]:
                    opt.zero_grad(set_to_none=True);q=m.fields(model,p);m.check_physical(p,q)
                    score=m.component_scores(p,q);milestones.append(dict(arm=arm,step=step,scores=score,representation=m.representation_stats(model,p)))
                    if step in [50,200]:np.savez_compressed(out/f'{arm}_{step:03d}_fields.npz',fields=q.detach().cpu().numpy())
                    dump(out/'milestones.json',milestones);dump(out/'receipt.json',receipt)
                    print(json.dumps(dict(arm=arm,step=step,active=score['active_error'],force=score['free_force'],healing=score['healing'])),flush=True)
                    del q
                guard()
            q=m.fields(model,p);m.check_physical(p,q)
            scores[arm]=m.component_scores(p,q);predictions[arm]=q.detach().cpu().numpy();del q
            torch.save(dict(model=model.state_dict(),optimizer=opt.state_dict(),rng=rng.get_state(),protocol=m.PROTOCOL),out/f'{arm}_200.pt')
        if not torch.equal(prior_copy,p.previous) or not torch.equal(fatigue_copy,p.f):raise ValueError('immutable history/fatigue changed')
        b,r=scores['B']['active_error'],scores['R']['active_error']
        ratio=r/b if b is not None and b>1e-12 and r is not None else None
        scores['decision']=dict(R_active=ratio,status='NA' if ratio is None else ('DIRECTIONAL_SIGNAL' if ratio<1-1e-8 else 'NO_DIRECTIONAL_SIGNAL'),scope='exposed single state active-anchor component; inspect full costs')
        dump(out/'scores.json',scores);dump(out/'loss_trace.json',records)
        np.savez_compressed(out/'fields.npz',**predictions)
        with (out/'metrics.csv').open('w') as f:
            keys=list(common_scores);writer=csv.DictWriter(f,fieldnames=['arm']+keys,lineterminator='\n');writer.writeheader()
            for arm,s in scores.items():
                if arm!='decision':writer.writerow(dict(arm=arm,**s))
        render(p,predictions,records,scores,out,receipt);guard()
        receipt['execution']='completed_pending_retrieval_review'
    except BaseException as e:
        receipt.update(execution='stopped_no_retry',error=f'{type(e).__name__}: {e}');raise
    finally:
        receipt.update(elapsed_seconds=time.monotonic()-started,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved(),max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        dump(out/'receipt.json',receipt)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--grant',type=Path);ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    if not args.execute:print('Preparation only: E028 separate two-arm active-anchor repair; no data/weights/optimizer read.')
    else:
        if not args.grant or not args.out:ap.error('execute requires exact grant and fresh output')
        signal.signal(signal.SIGTERM,deadline_signal);signal.signal(signal.SIGINT,deadline_signal)
        run(json.loads(LOCK.read_text()),json.loads(args.grant.read_text()),args.out)
