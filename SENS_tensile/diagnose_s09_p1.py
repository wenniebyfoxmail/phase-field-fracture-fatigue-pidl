#!/usr/bin/env python3
"""Fixed-checkpoint P1 diagnostic: no optimizer, no parameter updates."""
import argparse
import csv
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import numpy as np
import torch
import torch.nn.functional as F
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'source'))
from s09_data import load_data, transform, inventory, build_graph, weighted_abs
from s09_operator import FractureOperator

BASE = 'f58df2d398b9702030f7789f8a8f39f7e8386b2d'


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def reduce_window(current, target, pred, raw, scale, state_scale, area, tau):
    """Area reductions; losses reported per channel before the training /3."""
    a=area.double(); a=a/a.sum()
    avg=lambda x:float((x.double()*a).sum())
    truth=target[:,0]-current[:,0]; growth=pred[:,0]-current[:,0]
    proposal=raw[:,0]*scale[0]
    raw_target=(target-current)/scale
    rl=F.smooth_l1_loss(raw,raw_target,reduction='none')
    sl=F.smooth_l1_loss(pred/state_scale,target/state_scale,reduction='none')
    row={'true_growth':avg(truth),'pred_growth':avg(growth),
         'error':avg((pred[:,0]-target[:,0]).abs()),
         'proposal_negative_area':avg((proposal<0).float()),
         'proposal_positive_area':avg((proposal>0).float()),
         'proposal_negative_mass':avg((-proposal).clamp(min=0)),
         'proposal_positive_mass':avg(proposal.clamp(min=0)),
         'true_active_area':avg((truth>tau).float()),
         'pred_active_area':avg((growth>tau).float()),
         'overlap_mass':avg(torch.minimum(growth,truth)),
         'excess_mass':avg((growth-truth).clamp(min=0)),
         'missed_mass':avg((truth-growth).clamp(min=0))}
    for j,name in enumerate(['damage','history','driver']):
        row['raw_loss_'+name]=avg(rl[:,j]);row['state_loss_'+name]=avg(sl[:,j])
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['dataset','checkpoint','reference-output','out']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--expected-commit',required=True)
    args=p.parse_args(); root=Path(__file__).resolve().parents[1]
    git=lambda *a:subprocess.check_output(['git',*a],cwd=root,text=True).strip()
    if platform.node()!='GPUServer8' or platform.system()!='Linux':raise RuntimeError('Taobo only')
    if git('rev-parse','HEAD')!=args.expected_commit or git('status','--porcelain'):raise RuntimeError('release identity/dirty')
    if not os.getenv('CUDA_VISIBLE_DEVICES') or not torch.cuda.is_available():raise RuntimeError('explicit CUDA required')
    if not str(args.out.resolve()).startswith('/mnt/data2/drtao/wennie/'):raise RuntimeError('output root')
    args.out.mkdir(parents=True,exist_ok=False);start=time.time()
    receipt={'mode':'fixed_checkpoint_forward_only','commit':git('rev-parse','HEAD'),'dirty':'',
             'hostname':platform.node(),'pid':os.getpid(),'command':sys.argv,'start_unix':start,
             'gpu':os.environ['CUDA_VISIBLE_DEVICES'],'checkpoint':str(args.checkpoint),
             'execution_status':'running','optimizer_updates':0,'torch':torch.__version__}
    dump(args.out/'receipt.json',receipt)
    try:
        ck=torch.load(args.checkpoint,map_location='cpu',weights_only=False)
        config=json.loads((root/'configs/s09_e001.json').read_text())
        if ck['commit']!=BASE or ck['step']!=850 or ck['config']!=config or ck['p1_pass']:raise RuntimeError('checkpoint identity')
        stats=ck['stats'];tr,mesh=load_data(args.dataset,config)
        inv=inventory(tr,mesh['areas'],config)
        ref=json.loads((args.reference_output/'data_capability.json').read_text())
        if inv['p1_windows']!=ref['p1_windows'] or stats!=ref['statistics']:raise RuntimeError('windows/stats mismatch')
        graph={k:torch.from_numpy(v).cuda() for k,v in build_graph(mesh,config['radius'],config['coarse_bins']).items()}
        model=FractureOperator(stats['state_mean'],stats['state_scale'],stats['increment_scale'],config['width'],config['rank']).cuda()
        model.load_state_dict(ck['model']);model.eval();model.requires_grad_(False)
        states={k:transform(v['raw'],stats['psi_scale']) for k,v in tr.items() if k in config['train_ids']}
        rows=[];score_errors=[];score_den=[]
        with torch.inference_mode():
            for tid,o in inv['p1_windows']:
                h=torch.from_numpy(states[tid][o-2:o+1]).cuda();target=torch.from_numpy(states[tid][o+1]).cuda()
                path=torch.tensor(config['peak_to_peak_load_factors'],device='cuda')*tr[tid]['umax']/config['path_amplitude_scale']
                pred,raw=model.advance(h,graph,path)
                if not torch.isfinite(pred).all() or not torch.isfinite(raw).all():raise RuntimeError('nonfinite output')
                row=reduce_window(h[-1],target,pred,raw,model.increment_scale,model.state_scale,graph['area'],config['tau'])
                rows.append({'trajectory_id':tid,'origin_index':o,'origin_cycle':o+1,**row})
                # Match original metric arithmetic exactly (float32 subtract -> float64 area).
                score_errors.append(float(weighted_abs(pred[:,0].cpu().numpy()-states[tid][o+1,:,0],mesh['areas'])))
                score_den.append(float(weighted_abs(states[tid][o+1,:,0]-states[tid][o,:,0],mesh['areas'])))
        ratio=sum(score_errors)/sum(score_den)
        expected=json.loads((args.reference_output/'best_metrics.json').read_text())['increment_mae_ratio']
        if abs(ratio-expected)>1e-6:raise RuntimeError('checkpoint metric reproduction outside1e-6')
        if not all(torch.equal(v.cpu(),ck['model'][k]) for k,v in model.state_dict().items()):raise RuntimeError('model changed')
        with (args.out/'windows.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
        sums={k:sum(r[k] for r in rows) for k in ['true_growth','pred_growth','overlap_mass','excess_mass','missed_mass']}
        summary={'increment_mae_ratio':ratio,'expected_ratio':expected,'metric_reproduced':True,'windows':len(rows),
                 'checkpoint_step':ck['step'],'model_unchanged':True,'optimizer_updates':0,
                 'growth_ratio':sums['pred_growth']/sums['true_growth'],
                 'overlap_over_true':sums['overlap_mass']/sums['true_growth'],
                 'excess_over_true':sums['excess_mass']/sums['true_growth'],
                 'missed_over_true':sums['missed_mass']/sums['true_growth'],
                 'window_mean':{k:float(np.mean([r[k] for r in rows])) for k in rows[0] if k not in ['trajectory_id','origin_index','origin_cycle']},
                 'interpretation_boundary':'post-hoc diagnostics; no causal loss/gradient attribution; P1 FAIL unchanged'}
        dump(args.out/'summary.json',summary);receipt['execution_status']='succeeded';print(json.dumps(summary),flush=True)
    except Exception as e:
        receipt.update(execution_status='failed',error=repr(e));raise
    finally:
        receipt.update(elapsed_seconds=time.time()-start,cuda_peak_memory_bytes=torch.cuda.max_memory_allocated())
        dump(args.out/'receipt.json',receipt)

if __name__=='__main__':main()
