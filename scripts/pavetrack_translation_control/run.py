"""Single production-only E026 control run; no source images or qualification bank."""
import time
START=time.monotonic()
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import numpy as np

ROOT=Path(__file__).resolve().parents[2]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj


probe=module('e026_probe',Path(__file__).with_name('probe.py'))
old=module('e026_unchanged_e025_model',ROOT/'scripts/pavetrack_controlled_localizer/model.py')
runtime=module('e026_unchanged_runtime',ROOT/'scripts/pavetrack_positive_evidence/stage_b_runtime.py')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while part:=f.read(1024*1024):h.update(part)
    return h.hexdigest()


def write(path,obj):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf8');tmp.replace(path)


class Guard:
    def __init__(self,cfg,out,memory=None,start=None):
        self.cfg=cfg;self.out=out;self.start=START if start is None else start
        self.counts=dict(models=0,updates=0,training_rows=0,prediction_rows=0)
        if memory is None:
            import psutil
            process=psutil.Process()
            def memory():
                info=process.memory_info();return getattr(info,'peak_wset',info.rss)
        self.memory=memory;self.gpu=lambda:(0,0);self.rss=0;self.allocated=0;self.reserved=0
    def take(self,key,n=1):
        self.counts[key]+=n
        if self.counts[key]>self.cfg['budget'][key]:raise RuntimeError('counter cap '+key)
        self.check()
    def check(self):
        self.rss=max(self.rss,int(self.memory()));a,r=self.gpu()
        self.allocated=max(self.allocated,int(a));self.reserved=max(self.reserved,int(r))
        b=self.cfg['budget']
        if time.monotonic()-self.start>b['total_wall_seconds']:raise TimeoutError('600s wall cap')
        if self.rss>b['peak_RSS_bytes'] or self.allocated>b['peak_GPU_allocated_bytes'] or self.reserved>b['peak_GPU_reserved_bytes']:raise MemoryError('resource cap')
        if sum(p.stat().st_size for p in self.out.rglob('*') if p.is_file())>b['output_bytes']:raise RuntimeError('100MiB output cap')
    def receipt(self):
        return dict(elapsed_seconds=time.monotonic()-self.start,peak_RSS_bytes=self.rss,
                    peak_GPU_allocated_bytes=self.allocated,peak_GPU_reserved_bytes=self.reserved,
                    counts=self.counts,source_image_reads=0,qualification_reference_reads=0,OOF=False,E003_loaded=False)


def validate_config(cfg):
    if cfg['protocol']!='S01-E026-v1' or cfg['run_id']!='S01-E026-R001' or cfg['steps']!=128 or cfg['localizer']['parameters']!=29761 or cfg['localizer']['batch_size']!=8:
        raise ValueError('frozen model/step identity')
    if cfg['seeds']!=[[25100+k,25200+k] for k in range(3)] or cfg['test_shifts']!=probe.TEST_SHIFTS.tolist() or cfg['phase_offset']!=[16,16] or cfg['margin']!=1e-6 or cfg['threshold']!=.5:
        raise ValueError('frozen randomness/threshold identity')
    if cfg['budget']!=dict(models=6,updates=768,training_rows=6144,prediction_rows=576,total_wall_seconds=600,peak_RSS_bytes=4*1024**3,peak_GPU_allocated_bytes=4*1024**3,peak_GPU_reserved_bytes=4*1024**3,output_bytes=100*1024**2):
        raise ValueError('frozen budget')


def production_checks(cfg,guard):
    runtime.production_environment(cfg)
    if any(os.environ.get(k)!='1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']):raise PermissionError('CPU1')
    ps_script="Get-CimInstance Win32_Process|Where-Object {$_.Name -like 'python*'}|Select-Object ProcessId,CommandLine|ConvertTo-Json -Compress"
    raw=subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps_script],text=True).strip()
    rows=[] if not raw else json.loads(raw);rows=rows if isinstance(rows,list) else [rows]
    # Windows venv redirector and interpreter may both be named python.exe.
    # All admitted rows must be this interpreter or its launcher ancestor, never a peer.
    import psutil
    allowed={os.getpid(),*[p.pid for p in psutil.Process().parents() if p.name().lower().startswith('python')]}
    if any(row['ProcessId'] not in allowed for row in rows):raise RuntimeError('shared Python compute conflict')
    baseline=json.loads((ROOT/'docs/research/S01/S01-E012/stage_B/gpu_desktop_baseline.json').read_text())
    xml=subprocess.check_output(['nvidia-smi','-i','1','-q','-x'],text=True)
    desktop=runtime.desktop_inventory(xml,baseline,sha)
    info=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.free','--format=csv,noheader,nounits'],text=True)
    gpu=next([s.strip() for s in line.split(',')] for line in info.splitlines() if line.split(',')[0].strip()=='1')
    if gpu[1]!=cfg['producer']['gpu_uuid'] or gpu[2]!=cfg['producer']['gpu_name'] or float(gpu[3])<8192:raise ValueError('GPU identity/free memory')
    import torch,torchvision
    if torch.__version__!=cfg['producer']['torch'] or torchvision.__version__!=cfg['producer']['torchvision']:raise ValueError('torch runtime')
    torch.set_num_threads(1);torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0)!=cfg['producer']['gpu_name']:raise ValueError('logical GPU mapping')
    guard.gpu=lambda:(torch.cuda.max_memory_allocated(0),torch.cuda.max_memory_reserved(0));guard.check()
    return torch,dict(hostname=socket.gethostname(),account=subprocess.check_output(['whoami'],text=True).strip(),pid=os.getpid(),torch=torch.__version__,torchvision=torchvision.__version__,physical_GPU=gpu,desktop=desktop)


class Engine:
    def __init__(self,t,cfg,g):
        self.t=t;self.cfg=cfg;self.g=g
        self.predictor=object.__new__(old.Backend)
        self.predictor.t=t;self.predictor.cfg=cfg;self.predictor.device='cuda:0';self.predictor.loaded={}
    def fit(self,rgb,ys,shifts,seed):
        t=self.t;t.manual_seed(seed);t.cuda.manual_seed_all(seed)
        m=old.network(self.cfg).to('cuda:0').float().train()
        with t.no_grad():m.out.bias.zero_()
        initial=old.digest({k:v.detach().cpu().numpy().tolist() for k,v in m.state_dict().items()})
        opt=t.optim.AdamW(m.parameters(),lr=self.cfg['localizer']['lr'],weight_decay=self.cfg['localizer']['weight_decay'])
        trace=[]
        for step,ss in enumerate(shifts):
            x=np.stack([probe.shift_rgb(a,s) for a,s in zip(rgb,ss,strict=True)])
            y=np.stack([probe.shift_mask(a,s) for a,s in zip(ys,ss,strict=True)])
            x=t.tensor(x,device='cuda:0',dtype=t.float32)/255
            y=t.tensor(y[:,None],device='cuda:0',dtype=t.float32)
            opt.zero_grad(set_to_none=True);loss=old.probability_loss(m(x),y)
            if not t.isfinite(loss):raise ValueError('nonfinite loss')
            loss.backward()
            if any(v.grad is None or not t.isfinite(v.grad).all() for v in m.parameters()):raise ValueError('missing/nonfinite gradients')
            opt.step()
            if any(not t.isfinite(v).all() for v in m.parameters()):raise ValueError('nonfinite weights')
            trace.append(float(loss.detach().cpu()));self.g.take('updates');self.g.take('training_rows',len(rgb))
        state={k:v.detach().cpu().numpy().tolist() for k,v in m.state_dict().items()}
        model=dict(verified=True,state=state,state_digest=old.digest(state),initial_state_digest=initial,seed=seed,steps=len(shifts),loss_trace=trace,from_scratch=True)
        del opt,m,x,y,loss
        self.g.take('models');return model
    def predict(self,model,rgb):
        p=self.predictor.predict(model,rgb);self.g.take('prediction_rows',len(rgb));return p


def execute(packet,meta,cfg,out,guard,engine):
    rgb,ys,folds=(packet[k] for k in ['rgb','masks','fold_indices'])
    states=[];plans=[]
    # Every actual flow and corresponding prior is frozen before the first fit.
    for k in range(3):
        y=ys[folds[k]]
        for j,seed in enumerate(cfg['seeds'][k]):
            ss=probe.flow(seed);prior=probe.position_prior(y,ss)
            np.savez(out/f'plan_{k}_{j}.npz',shifts=ss,position_prior=prior,
                     shared_seam_masks=np.stack([probe.shared_seam_mask(s) for s in probe.TEST_SHIFTS]))
            plans.append((k,j,seed,ss,prior))
    write(out/'plans_freeze.json',dict(files={p.name:sha(p) for p in out.glob('plan_*.npz')},before_any_update=True))
    for k,j,seed,ss,prior in plans:
        model=engine.fit(rgb[folds[k]],ys[folds[k]],ss,seed)
        model.update(fold=k,seed_index=j,flow_file=f'plan_{k}_{j}.npz')
        path=out/f'model_{k}_{j}.json';write(path,model);states.append((k,j,model,prior))
        write(out/'status.json',dict(state='training',models=len(states),counts=guard.counts))
    freeze=dict(files={p.name:sha(p) for p in out.glob('model_*.json')},states=[m['state_digest'] for _,_,m,_ in states],before_any_prediction=True)
    if len(freeze['files'])!=6:raise ValueError('six final states required')
    write(out/'models_freeze.json',freeze)
    results=[]
    for k,j,model,prior in states:
        own_rgb=rgb[folds[k]];target=ys[folds[k]];maps=np.empty((3,4,8,32,32),np.float32)
        for phase,s in enumerate(probe.TEST_SHIFTS):
            batches=[np.stack([probe.shift_rgb(a,s) for a in own_rgb]),
                     np.stack([probe.shift_rgb(a,(s+16)%32) for a in own_rgb]),
                     np.stack([probe.shift_rgb(a,s) for a in np.roll(own_rgb,-1,axis=0)])]
            for kind,x in enumerate(batches):maps[kind,phase]=engine.predict(model,x)
        np.save(out/f'maps_{k}_{j}.npy',maps)
        result=probe.evaluate(maps,target,prior,cfg['margin']);result.update(fold=k,seed=model['seed'],seed_index=j)
        write(out/f'metrics_{k}_{j}.json',result);results.append(result)
        guard.check()
    folds=[dict(fold=k,stable=all(r['passed'] for r in results if r['fold']==k),
                seed_levels=[r['level'] for r in results if r['fold']==k]) for k in range(3)]
    for f in folds:f['level']='L3' if f['stable'] else max(f['seed_levels'])
    result=dict(protocol=cfg['protocol'],run_id=cfg['run_id'],execution='succeeded',folds=folds,
                stable_folds=[f['fold'] for f in folds if f['stable']],
                scope='artificial translated training contents only; no natural-site or semantic claim',
                source_image_reads=0,qualification_reference_reads=0,E003_loaded=False,OOF=None,net_GT=None,retention=None)
    write(out/'result.json',result);return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--reviewed-commit',required=True);parser.add_argument('--manifest-sha256',required=True);args=parser.parse_args()
    # Refuse the development Mac before loading torch, data, or creating a run.
    cfg=json.loads((ROOT/'docs/research/S01/S01-E026/run_config.json').read_text());validate_config(cfg);runtime.production_environment(cfg)
    manifest=ROOT/'docs/research/S01/S01-E026/source_manifest.json'
    if args.source.resolve()!=ROOT or sha(manifest)!=args.manifest_sha256:raise ValueError('source manifest identity')
    for name,h in json.loads(manifest.read_text())['files'].items():
        if sha(ROOT/name)!=h:raise ValueError('source member '+name)
    args.run.mkdir(parents=True,exist_ok=False)
    guard=Guard(cfg,args.run);stop=threading.Event()
    def watchdog():
        while not stop.wait(.25):
            try:
                # No torch/CUDA call on this background I/O monitor.
                if time.monotonic()-START>600 or guard.memory()>4*1024**3:raise RuntimeError('watchdog wall/RSS')
            except Exception as exc:
                write(args.run/'watchdog_stop.json',dict(reason=str(exc),elapsed_seconds=time.monotonic()-START));os._exit(124)
    thread=threading.Thread(target=watchdog,daemon=True);thread.start()
    try:
        lock=json.loads((ROOT/'docs/research/S01/S01-E026/data_lock.json').read_text())
        if set(p.name for p in args.input.iterdir())!=set(lock['files']):raise ValueError('input inventory')
        for name,rec in lock['files'].items():
            p=args.input/name
            if p.stat().st_size!=rec['bytes'] or sha(p)!=rec['sha256']:raise ValueError('input member '+name)
        meta=json.loads((args.input/'identities.json').read_text())
        with np.load(args.input/'controls.npz',allow_pickle=False) as z:packet={k:z[k] for k in z.files}
        probe.validate_packet(packet,meta,lock)
        if meta['seeds']!=cfg['seeds']:raise ValueError('seed identity')
        np.savez(args.run/'controls.npz',**packet);write(args.run/'identities.json',meta)
        # Fail closed if any code attempts to open another producer Run's data.
        own=str(args.run.resolve()).casefold()+os.sep
        def audit(event,params):
            if event=='open' and isinstance(params[0],(str,bytes,os.PathLike)):
                path=os.path.abspath(os.fsdecode(params[0])).casefold()
                if '\\pavetrack_runs\\' in path and not (path+os.sep).startswith(own):raise PermissionError('other Run/source/qualification access forbidden')
        sys.addaudithook(audit)
        t,identity=production_checks(cfg,guard)
        write(args.run/'launch.json',dict(reviewed_commit=args.reviewed_commit,manifest_sha256=args.manifest_sha256,identity=identity,started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source=str(ROOT),input=str(args.input),source_image_reads=0,qualification_reference_reads=0))
        execute(packet,meta,cfg,args.run,guard,Engine(t,cfg,guard))
        # Render only saved evidence; no model or source image access.
        analyze=module('e026_analysis',Path(__file__).with_name('analyze.py'));analyze.render(args.run)
        guard.check();write(args.run/'resource.json',guard.receipt())
        if guard.counts!=dict(models=6,updates=768,training_rows=6144,prediction_rows=576):raise ValueError('completed counters')
        write(args.run/'status.json',dict(state='completed',counts=guard.counts))
        write(args.run/'output_receipt.json',dict(files={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in args.run.iterdir() if p.is_file()}))
        guard.check()
    except BaseException as exc:
        write(args.run/'status.json',dict(state='stopped',reason=repr(exc),counts=guard.counts));write(args.run/'resource.json',guard.receipt());raise
    finally:stop.set()


if __name__=='__main__':main()
