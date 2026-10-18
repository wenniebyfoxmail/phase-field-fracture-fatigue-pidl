"""Independent E029 single candidate. Frozen E028 R is reused, never rerun."""
import argparse
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
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
import s04_e027 as old
import s04_e028 as parent
import s04_e029 as m
from run_s04_e027 import initializer_compatibility,deadline_signal
from run_s04_e028 import device_admission
LOCK=ROOT/'docs/research/S04/S04-E029/data_lock.json'


def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')


def admit(lock,grant,out):
    if platform.system()=='Darwin':raise PermissionError('Mac training prohibited')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True) or head!=grant.get('approved_commit'):
        raise PermissionError('clean exact source required')
    if lock['protocol']!=m.PROTOCOL or grant.get('protocol')!=m.PROTOCOL:raise PermissionError('protocol mismatch')
    if grant.get('execution_authorized') is not True or not grant.get('review_reference') or not grant.get('human_approval_reference'):
        raise PermissionError('authorization/review references required')
    if (grant.get('gpu_hours_cap'),grant.get('ram_gib_cap'),grant.get('output_gib_cap'))!=(.5,32,2):raise PermissionError('budget mismatch')
    if grant.get('hostname')!=platform.node() or grant.get('output')!=str(out.resolve()):raise PermissionError('host/output mismatch')
    uuid=device_admission(grant)
    if out.exists():raise FileExistsError('fresh output only; no retry')
    return head,uuid


def render(p,pred,records,control_trace,scores,out,receipt):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    polygons=p.xy[p.conn].cpu().numpy();display={}
    with torch.no_grad():
        for key,val in pred.items():
            q=torch.as_tensor(val,device=p.xy.device,dtype=torch.float64);parts=p.parts(*q.unbind(1))
            gp=[old.q4_interpolate(q[:,j],p.conn,p.N) for j in range(3)]+[parts[3],parts[4]]
            display[key]=[((v*p.w).sum(1)/p.w.sum(1)).cpu().numpy() for v in gp]
    for errors,stem in [(False,'fields'),(True,'errors')]:
        names=list(pred)[1:] if errors else list(pred)
        fig,axes=plt.subplots(5,len(names),figsize=(3*len(names),14),squeeze=False,layout='constrained')
        for j,label in enumerate(['u','v','d','raw','active']):
            values=[display[k][j]-display['reference'][j] if errors else display[k][j] for k in names]
            if errors:hi=max(float(abs(v).max()) for v in values) or 1e-30;lo=-hi
            else:lo=min(float(v.min()) for v in values);hi=max(float(v.max()) for v in values)
            for ax,key,val in zip(axes[j],names,values):
                im=PolyCollection(polygons,array=val,cmap='RdBu_r' if errors else 'viridis',edgecolors='none',antialiased=False)
                im.set_clim(lo,hi);ax.add_collection(im);ax.autoscale_view();ax.set_aspect('equal')
                ax.set(title=f'{label}: {key}'+('-FEM' if errors else ''),xlabel='x',ylabel='y')
            fig.colorbar(im,ax=list(axes[j]),shrink=.75)
        fig.suptitle('E029 | exposed synthetic c20s4 / horizon0 / seed1 | native Q4 element means')
        fig.savefig(out/f'{stem}.png',dpi=125);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,3.6),layout='constrained')
    for name,rows in [('frozen E028_R',control_trace),('E029_R',records)]:
        for ax,key in zip(axes,['L_active','total_loss']):
            ax.semilogy([r['step'] for r in rows],[max(1e-30,r[key]) for r in rows],label=name)
            ax.set(xlabel='optimizer updates',ylabel=key,title=key);ax.legend()
    fig.suptitle('Optimization, not physical evolution; adaptive loss weights vary')
    fig.savefig(out/'trace.png',dpi=160);plt.close(fig)
    for stem in ['fields','errors','trace']:
        guide={'fields':'Rows u/v/d/raw/active. Columns reference, old initial/S/C, old hard0, frozen E028_R, new smooth0 and R. Same unclipped raw scale per row; native Q4 Jacobian-weighted element means.',
               'errors':'Rows u/v/d/raw/active; all prediction columns minus exact FEM reference; same symmetric signed-error scale per row. Native Q4 element means, no clipping or grid interpolation.',
               'trace':'Left full-support squared active relative error and right adaptive total objective, both versus optimizer updates. Frozen E028_R is not rerun. Lines use all200updates; log display floor1e-30 only for plotting; adaptive coefficients vary, so total objectives do not rank full-state quality.'}[stem]
        (out/f'{stem}.md').write_text(f'''# How to read {stem}.png
\n## Figure question
Does changing only the flat damage representation retain the current physical bounds and improve actual active/damage fit after200updates?
\n## Data provenance
Run output {out}, exact source {receipt['commit']}, protocol {m.PROTOCOL}. Same fields.npz/scores.json/loss_trace.json, frozen_control_trace.json, and locked four MATs. Exposed synthetic c20s4/horizon0/seed1, U=.11999988, native mesh. Plot source SENS_tensile/run_s04_e029.py. Lower is committed c20s3, never current target or U0; no history commit.
\n## Visual grammar and panel guide
{guide}
\n## Key numerical takeaway
{json.dumps(scores['decision'])}. Primary compares R200 with its own new smooth0, while frozen E028_R and original S/C/initial remain visible. Check metrics.csv for u/v/d, force, raw/active, bounds and history costs; a relative gain over oldR alone is not success.
\n## Limitations and claim boundary
One exposed synthetic state, no independent repeated unit, physical evolution, holdout or generalization validation. EPS1e-4 changes only the initial interior seed; smooth0 separates that change from training. No width/profile inference. Large raw-field colour ranges can obscure local details; scores use native GP4 Z, not image pixels. R/B gradient norm control is before Adam and is not an actual-step bound. Gradient availability does not itself prove learned growth.
''')


def run(lock,grant,out):
    head,uuid=admit(lock,grant,out);free,total=torch.cuda.mem_get_info()
    if free<20*1024**3:raise MemoryError('20GiB initial free required')
    cap=free-1024**3;torch.cuda.set_per_process_memory_fraction(cap/total,0)
    started=time.monotonic();out.mkdir(parents=True)
    receipt=dict(protocol=m.PROTOCOL,commit=head,execution='preflight',host=platform.node(),pid=os.getpid(),
        gpu_uuid=uuid,gpu=torch.cuda.get_device_name(0),cuda_visible_devices=os.environ['CUDA_VISIBLE_DEVICES'],command=sys.argv,
        optimizer_steps=0,optimizer_step_calls=0,history_commits=0,retry=False,source_dirty=False,cuda_cap_bytes=cap,initial_free_cuda_bytes=free)
    def guard():
        torch.cuda.synchronize()
        if time.monotonic()-started>1800:raise TimeoutError('.5GPU-hour cap')
        if torch.cuda.max_memory_reserved()>cap or torch.cuda.mem_get_info()[0]<1024**3:raise MemoryError('GPU cap/headroom')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>32*1024**3:raise MemoryError('RSS cap')
        if sum(p.stat().st_size for p in out.rglob('*') if p.is_file())>2*1024**3:raise OSError('output cap')
    try:
        dump(out/'data_lock.json',lock)
        s0=Path(grant['s0']);control=Path(grant['control_output'])
        state,compat=initializer_compatibility(s0,{'initializer':lock['s0']});dump(out/'start_compatibility.json',compat)
        for row in lock['control_payloads'].values():old.verify_payload(control,row)
        arrays=old.load_reference(Path(grant['data_root']),lock['reference_lock']);p=old.Problem(arrays,'cuda:0');parent.validate_current_lower(p)
        frozen=np.load(control/'fields.npz');old_scores=json.loads((control/'scores.json').read_text())
        if not np.array_equal(frozen['reference'],arrays['ref']):raise ValueError('reference mismatch')
        model=old.make_model(state,'cuda:0');legacy=old.fields(model,p.xy)
        if not np.allclose(legacy.detach().cpu().numpy(),frozen['original_S'],atol=1e-10,rtol=1e-10):raise ValueError('original S replay mismatch')
        with torch.no_grad():raw_origin=model(p.xy)[:,2];seed=parent.project_damage(legacy[:,2],p.previous,p.fixed_d)
        mapper=m.BoundedIncrement(p.xy,p.previous,p.fixed_d,raw_origin,seed)
        frozen_buffers={k:v.clone() for k,v in mapper.named_buffers()};prior=p.previous.clone();fatigue=p.f.clone()
        q0=m.fields(model,p,mapper);parent.check_physical(p,q0)
        start_scores=parent.component_scores(p,q0)
        for key,val in lock['expected_smooth0_scores'].items():
            if not np.isclose(start_scores[key],val,atol=1e-10,rtol=1e-10):raise ValueError('smooth0 replay mismatch: '+key)
        max_jump=float((q0[:,2]-seed).abs().max())
        if max_jump>m.EPS+1e-14:raise ValueError('initial seed jump exceeds declared epsilon')
        pred={k:frozen[k] for k in ['reference','initial','original_S','original_C']}
        pred.update(hard0=frozen['mapped0'],E028_R=frozen['R'],smooth0=q0.detach().cpu().numpy())
        np.savez_compressed(out/'comparison_start.npz',**pred)
        torch.save(mapper.state_dict(),out/'mapping_initial.pt')
        dump(out/'initial_identity.json',dict(start_sha256=lock['s0']['sha256'],fresh_Adam=True,seed=1,epsilon=m.EPS,max_zero_step_damage_jump=max_jump,
            mapping=mapper.get_extra_state(),frozen_control='E028_R200',mechanical_weight=0.,same_objective_optimizer_sampling=True))
        scores={k:parent.component_scores(p,torch.as_tensor(v,device=p.xy.device,dtype=torch.float64)) for k,v in pred.items()}
        if abs(scores['E028_R']['active_error']-old_scores['R']['active_error'])>1e-10:raise ValueError('frozen R replay mismatch')
        del legacy,q0,raw_origin,seed,state
        optimizer=torch.optim.Adam(model.parameters(),lr=1e-4,betas=(.9,.999),eps=1e-8,weight_decay=0)
        rng=torch.Generator().manual_seed(1);original_params=[x.detach().clone() for x in model.parameters()]
        t=time.monotonic()
        for _ in range(3):
            guard();model.zero_grad(set_to_none=True);q=m.fields(model,p,mapper)
            loss,_=parent.objective(p,model,q,p.sample(torch.Generator().manual_seed(1)),True);loss.backward();del q,loss
        torch.cuda.synchronize();benchmark=(time.monotonic()-t)/3
        if any(not torch.equal(x,y) for x,y in zip(original_params,model.parameters())) or optimizer.state:raise ValueError('benchmark changed parameters/Adam')
        del original_params;model.zero_grad(set_to_none=True)
        estimate=time.monotonic()-started+1.5*m.STEPS*benchmark+300
        if estimate>1800:raise TimeoutError('preflight estimate exceeds finite cap')
        dump(out/'preflight.json',dict(benchmark_seconds=benchmark,estimate_seconds=estimate,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved()))
        records=[];milestones=[]
        def checkpoint(step):
            q=m.fields(model,p,mapper);parent.check_physical(p,q)
            score=parent.component_scores(p,q)
            with torch.no_grad():raw=model(p.xy)[:,2]
            leaf=raw.detach().clone().requires_grad_(True);dd=torch.autograd.grad(mapper(p.xy,leaf).sum(),leaf)[0]
            growth=mapper.variable&(p.ref[:,2]>p.previous+1e-10)
            with torch.no_grad():
                stats=mapper.diagnostics(raw,growth)
                inc=q.detach()[:,2]-p.previous
                stats.update(max_damage_increment=float(inc.max()),positive_increment_nodes=int((inc>1e-10).sum()))
            milestones.append(dict(step=step,scores=score,representation=stats))
            if step in [0,50,200]:np.savez_compressed(out/f'R_{step:03d}_fields.npz',fields=q.detach().cpu().numpy(),NN_raw=raw.cpu().numpy(),relative_raw=(raw-mapper.raw_origin).cpu().numpy(),true_dd_draw=dd.cpu().numpy())
            dump(out/'milestones.json',milestones)
            return q.detach().cpu().numpy(),score
        checkpoint(0);receipt['execution']='running';dump(out/'receipt.json',receipt)
        for step in range(1,201):
            guard();optimizer.zero_grad(set_to_none=True);q=m.fields(model,p,mapper);parent.check_physical(p,q)
            loss,log=parent.objective(p,model,q,p.sample(rng),True);loss.backward()
            for param in model.parameters():
                if param.grad is None:raise ValueError('missing gradient')
                old.finite(param.grad,'gradient')
            receipt['optimizer_step_calls']+=1;receipt['optimizer_attempt']='in_progress_or_unknown';optimizer.step()
            for param in model.parameters():old.finite(param,'updated parameter')
            receipt['optimizer_steps']+=1;receipt['optimizer_attempt']='completed_finite'
            row=dict(arm='R',step=step,total_loss=float(loss.detach()),**log);records.append(row)
            with (out/'loss_trace.jsonl').open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
            del q,loss
            if step in [10,50,100,200]:
                optimizer.zero_grad(set_to_none=True);values,score=checkpoint(step)
                dump(out/'receipt.json',receipt);print(json.dumps(dict(step=step,active=score['active_error'],d_Z=score['zone_d_RMS'],healing=score['healing'])),flush=True)
                if step==200:pred['R']=values;scores['R']=score
            guard()
        if not torch.equal(prior,p.previous) or not torch.equal(fatigue,p.f):raise ValueError('history/fatigue mutated')
        for name,value in mapper.named_buffers():
            if not torch.equal(value,frozen_buffers[name]):raise ValueError('mapping buffer mutated')
        start=scores['smooth0']['active_error'];end=scores['R']['active_error']
        ratio=end/start if start is not None and start>1e-12 and end is not None else None
        scores['decision']=dict(R200_over_own_smooth0=ratio,status='NA' if ratio is None else ('DIRECTIONAL_SIGNAL' if ratio<1-1e-8 else 'NO_DIRECTIONAL_SIGNAL'),
            R200_over_frozen_E028_R=end/scores['E028_R']['active_error'],scope='single exposed-state representation repair; inspect damage growth and all costs')
        np.savez_compressed(out/'fields.npz',**pred);dump(out/'scores.json',scores);dump(out/'loss_trace.json',records)
        control_trace=[x for x in json.loads((control/'loss_trace.json').read_text()) if x['arm']=='R'];dump(out/'frozen_control_trace.json',control_trace)
        torch.save(dict(model=model.state_dict(),mapping=mapper.state_dict(),optimizer=optimizer.state_dict(),rng=rng.get_state(),protocol=m.PROTOCOL),out/'R_200.pt')
        with (out/'metrics.csv').open('w') as f:
            keys=list(scores['R']);writer=csv.DictWriter(f,fieldnames=['arm']+keys,lineterminator='\n');writer.writeheader()
            for key,s in scores.items():
                if key!='decision':writer.writerow(dict(arm=key,**s))
        render(p,pred,records,control_trace,scores,out,receipt);guard();receipt['execution']='completed_pending_retrieval_review'
    except BaseException as e:receipt.update(execution='stopped_no_retry',error=f'{type(e).__name__}: {e}');raise
    finally:
        receipt.update(elapsed_seconds=time.monotonic()-started,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved(),max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        dump(out/'receipt.json',receipt)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--grant',type=Path);ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    if not args.execute:print('Preparation only; no data/weights/optimizer read.')
    else:
        if not args.grant or not args.out:ap.error('execute requires exact grant and fresh output')
        signal.signal(signal.SIGTERM,deadline_signal);signal.signal(signal.SIGINT,deadline_signal)
        run(json.loads(LOCK.read_text()),json.loads(args.grant.read_text()),args.out)
