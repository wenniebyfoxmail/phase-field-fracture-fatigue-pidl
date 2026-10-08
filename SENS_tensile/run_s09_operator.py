#!/usr/bin/env python3
"""S09 audit and bounded P1/P2 runner. Training is prohibited on macOS."""
from __future__ import annotations
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'source'))
from s09_data import load_data, statistics, transform, inventory, build_graph, weighted_abs, evaluate_damage
from s09_operator import FractureOperator, one_step_loss, area_loss, rollout


def dump(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def git(*args):
    return subprocess.check_output(['git',*args],cwd=Path(__file__).resolve().parents[1],text=True).strip()


def tensor_graph(arrays,device):
    return {k:torch.from_numpy(v).to(device) for k,v in arrays.items()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['audit','p1','p2'],required=True)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--config',type=Path,default=Path(__file__).resolve().parents[1]/'configs/s09_e001.json')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--expected-commit')
    p.add_argument('--p1-checkpoint',type=Path)
    args=p.parse_args();config=json.loads(args.config.read_text())
    weights=config.get('supervised_channel_weights',[1,1,1])
    if weights not in ([1,1,1],[1,0,0]):raise ValueError('unsupported loss weights')
    if weights==[1,0,0] and args.mode=='p2':raise ValueError('Damage-only is P1-only; no closed-state rollout')
    if args.mode!='audit':
        if platform.system()!='Linux' or platform.node()!='GPUServer8':
            raise RuntimeError('Training allowed only on frozen Taobo GPUServer8; never Mac')
        if not args.expected_commit or git('rev-parse','HEAD')!=args.expected_commit:
            raise RuntimeError('Require exact committed release')
        if git('status','--porcelain'):
            raise RuntimeError('Dirty release checkout')
        if not os.environ.get('CUDA_VISIBLE_DEVICES') or not torch.cuda.is_available():
            raise RuntimeError('Explicit healthy CUDA GPU required')
        if not str(args.out.resolve()).startswith('/mnt/data2/drtao/wennie/'):
            raise RuntimeError('Fresh attributed /mnt/data2 output required')
        if config['physics_loss_weight']!=0:
            raise RuntimeError('This runner is data-only')
    args.out.mkdir(parents=True,exist_ok=False)
    started=time.time()
    receipt={'experiment_id':config['experiment_id'],'mode':args.mode,'config':config,
             'commit':git('rev-parse','HEAD'),'dirty':git('status','--porcelain'),
             'hostname':platform.node(),'pid':os.getpid(),'cwd':str(Path.cwd()),
             'command':sys.argv,'cuda_visible_devices':os.getenv('CUDA_VISIBLE_DEVICES'),
             'torch_version':torch.__version__,'python':sys.version,'started_unix':started,
             'execution_status':'running','retrieval_status':'pending',
             'scientific_status':'not_evaluated'}
    dump(args.out/'receipt.json',receipt)
    trajectories,mesh=load_data(args.dataset,config)
    stats=statistics(trajectories,config['train_ids'])
    inv=inventory(trajectories,mesh['areas'],config)
    arrays=build_graph(mesh,config['radius'],config['coarse_bins'])
    summary={'statistics':stats,'tau':inv['tau'],'g_ref':inv['g_ref'],
             'p1_windows':inv['p1_windows'],'p1_growth_available':inv['p1_growth_available'],
             'p1_stagnant_available':inv['p1_stagnant_available'],
             'nodes':len(mesh['areas']),'local_edges':arrays['edges'].shape[1],
             'coarse_nodes':len(arrays['coarse_area']),'coarse_edges':arrays['coarse_edges'].shape[1],
             'trajectories':{k:{'states':len(v['raw']),'umax':v['umax']} for k,v in trajectories.items()},
             'state_support':'legacy element fields; no GP/native node reconstruction',
             'closure_status':'unverified','f_prediction':'unavailable',
             'teacher_qualified':False,'test_status':'no untouched test in this corpus'}
    dump(args.out/'data_capability.json',summary)
    with (args.out/'window_inventory.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(inv['windows'][0]));w.writeheader();w.writerows(inv['windows'])
    if args.mode=='audit':
        receipt.update(execution_status='succeeded',scientific_status='data_audit_only',elapsed_seconds=time.time()-started)
        dump(args.out/'receipt.json',receipt);print(json.dumps(summary,indent=2));return
    device=torch.device('cuda');torch.manual_seed(config['seed']);np.random.seed(config['seed'])
    graph=tensor_graph(arrays,device)
    model=FractureOperator(stats['state_mean'],stats['state_scale'],stats['increment_scale'],config['width'],config['rank']).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=config['learning_rate'],weight_decay=config['weight_decay'])
    # CPU store; only current context and targets are transferred to CUDA.
    states={k:torch.from_numpy(transform(v['raw'],stats['psi_scale'])) for k,v in trajectories.items()}
    paths={k:torch.tensor(config['peak_to_peak_load_factors'],device=device)*v['umax']/config['path_amplitude_scale'] for k,v in trajectories.items()}
    if args.mode=='p2':
        if args.p1_checkpoint is None:raise ValueError('P2 requires P1 checkpoint')
        ck=torch.load(args.p1_checkpoint,map_location=device,weights_only=False)
        if ck['config']!=config or ck['commit']!=args.expected_commit or not ck['p1_pass']:
            raise ValueError('P1 checkpoint identity/pass mismatch')
        model.load_state_dict(ck['model']);optimizer.load_state_dict(ck['optimizer'])
    windows=inv['p1_windows'] if args.mode=='p1' else [[r['trajectory_id'],r['origin_index']] for r in inv['windows'] if r['split']=='train']
    rng=np.random.default_rng(config['seed']);budget=config[args.mode+'_updates']
    area=mesh['areas'];history_rows=[];best=float('inf');p1_pass=False

    @torch.no_grad()
    def assess():
        model.eval();errors=[];denominators=[];preds=[];refs=[];curr=[];linear=[];persistence=[]
        selected=inv['p1_windows'] if args.mode=='p1' else [[r['trajectory_id'],r['origin_index']] for r in inv['windows'] if r['split']=='development' and r['origin_index']%5==2]
        for tid,o in selected:
            h=states[tid][o-2:o+1].to(device);steps=1 if args.mode=='p1' else 3
            pred=rollout(model,h,graph,paths[tid],steps)[-1,:,0].cpu().numpy()
            true=states[tid][o+steps,:,0].numpy();current=states[tid][o,:,0].numpy()
            growth=float(weighted_abs(true-current,area))
            if growth>config['tau']:
                errors.append(float(weighted_abs(pred-true,area)));denominators.append(growth)
            preds.append(pred);refs.append(true);curr.append(current);persistence.append(current)
            previous=states[tid][o-1,:,0].numpy()
            linear.append(np.clip(current+steps*(current-previous),current,1))
        score=sum(errors)/sum(denominators) if denominators else None
        if args.mode=='p1':result={'increment_mae_ratio':score,'p1_pass':score is not None and score<=.8}
        else:result={'gno':evaluate_damage(preds,refs,curr,area,config['tau'],inv['g_ref']),
                     'persistence':evaluate_damage(persistence,refs,curr,area,config['tau'],inv['g_ref']),
                     'constrained_linear':evaluate_damage(linear,refs,curr,area,config['tau'],inv['g_ref'])}
        model.train();return score,result

    try:
        initial,metrics=assess();dump(args.out/'initial_metrics.json',metrics)
        for step in range(1,budget+1):
            tid,o=windows[int(rng.integers(len(windows)))];h=states[tid][o-2:o+1].to(device)
            target=states[tid][o+1].to(device);optimizer.zero_grad(set_to_none=True)
            loss,pred=one_step_loss(model,h,target,graph,paths[tid],weights)
            if args.mode=='p2':
                src,dst=graph['edges'];distance=graph['relative'][:,2].clamp(min=1e-3)
                grad_error=((pred[src,0]-pred[dst,0])-(target[src,0]-target[dst,0]))/distance
                loss=loss+.1*(grad_error.square()*graph['weight']).sum()/graph['weight'].sum()
                if step>config['p2_rollout_start']:
                    roll=rollout(model,h,graph,paths[tid],3)
                    future=states[tid][o+1:o+4].to(device)
                    loss=loss+.5*sum(area_loss(roll[j],future[j],model.state_scale,graph['area']) for j in range(3))/3
            if not torch.isfinite(loss):raise FloatingPointError('nonfinite loss')
            loss.backward()
            norm=torch.nn.utils.clip_grad_norm_(model.parameters(),config['gradient_clip'],error_if_nonfinite=True)
            optimizer.step()
            history_rows.append({'step':step,'loss':float(loss.detach()),'gradient_norm':float(norm),'elapsed_seconds':time.time()-started})
            if step%50==0 or step==budget:
                score,metrics=assess();print(json.dumps({'step':step,'loss':history_rows[-1]['loss'],'metrics':metrics}),flush=True)
                dump(args.out/'latest_metrics.json',metrics)
                if score is not None and score<best:
                    best=score;p1_pass=bool(metrics.get('p1_pass',False))
                    torch.save({'model':model.state_dict(),'optimizer':optimizer.state_dict(),'config':config,
                                'stats':stats,'commit':args.expected_commit,'step':step,'p1_pass':p1_pass},args.out/'best.pt')
                    dump(args.out/'best_metrics.json',metrics)
                if args.mode=='p1' and p1_pass:break
        receipt.update(execution_status='succeeded',scientific_status=('p1_memorization_pass' if p1_pass else 'p1_memorization_fail') if args.mode=='p1' else 'development_diagnostic_only',updates=step)
    except Exception as exc:
        receipt.update(execution_status='failed',error=repr(exc));raise
    finally:
        if history_rows:
            with (args.out/'training_history.csv').open('w') as f:
                w=csv.DictWriter(f,fieldnames=list(history_rows[0]));w.writeheader();w.writerows(history_rows)
        receipt['elapsed_seconds']=time.time()-started;receipt['cuda_peak_memory_bytes']=torch.cuda.max_memory_allocated()
        dump(args.out/'receipt.json',receipt)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
