"""E027 frozen external source. True model forward is producer-only."""
import time
START=time.monotonic()
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import numpy as np

ROOT=Path(__file__).resolve().parents[2]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


prior=module('e027_reviewed_runtime',ROOT/'scripts/pavetrack_translation_control/run.py')
probe=module('e027_probe',Path(__file__).with_name('probe.py'))
write=prior.write;sha=prior.sha


def validate_config(cfg):
    if cfg['protocol']!='S01-E027-v1.1' or cfg['run_id']!='S01-E027-R001' or cfg['primary']!=dict(minimum_images=7,images=12,threshold=.5,margin=1e-6) or cfg['repeat_tolerance']!=1e-6:
        raise ValueError('frozen criteria')
    if cfg['budget']!=dict(models=0,updates=0,training_rows=0,prediction_rows=56,total_wall_seconds=600,peak_RSS_bytes=4*1024**3,peak_GPU_allocated_bytes=4*1024**3,peak_GPU_reserved_bytes=4*1024**3,output_bytes=100*1024**2):
        raise ValueError('frozen budget')
    if cfg['checkpoint']['parameters']!=30905011 or cfg['checkpoint']['tensors']!=74 or cfg['source_models']!=1 or cfg['fit'] or cfg['selector'] or cfg['OOF'] or cfg['fresh_access']:
        raise ValueError('source/model scope')


class Engine:
    def __init__(self,t,cfg,path):
        self.t=t;self.cfg=cfg
        source=module('e027_pinned_official_network',path/'deepcrack.py')
        state=t.load(path/'DeepCrack_CT260_FT1.pth',map_location='cpu',weights_only=True)
        if len(state)!=74 or sum(v.numel() for v in state.values())!=30905011 or any(v.dtype!=t.float32 or not t.isfinite(v).all() for v in state.values()):raise ValueError('external state support')
        self.net=source.DeepCrack();self.net.load_state_dict(state,strict=True);del state
        self.net=self.net.float().to('cuda:0').eval();self.net.requires_grad_(False)
        self.initial=self.digest()
    def digest(self):
        h=hashlib.sha256()
        for key,v in sorted(self.net.state_dict().items()):h.update(key.encode());h.update(v.detach().cpu().contiguous().numpy().tobytes())
        return h.hexdigest()
    def predict(self,rgb):
        t=self.t
        if self.net.training or any(v.requires_grad or v.grad is not None for v in self.net.parameters()):raise ValueError('frozen/no-gradient source')
        x=probe.preprocess(rgb)
        with t.no_grad(),t.autocast('cuda',enabled=False):
            outputs=self.net(t.tensor(x[None],device='cuda:0'));p=outputs[0].sigmoid()[0,0].cpu().numpy().copy()
        if p.shape!=rgb.shape[1:] or p.dtype!=np.float32 or not np.isfinite(p).all() or (p<0).any() or (p>1).any():raise ValueError('final fused output')
        return p
    def verify_unchanged(self):
        if self.digest()!=self.initial or any(v.grad is not None or v.requires_grad for v in self.net.parameters()):raise ValueError('external weights changed')
        return self.initial


def execute(rgbs,out,cfg,guard,engine,reference_loader):
    if rgbs['cfd'].shape!=(12,3,320,480) or rgbs['pavetrack'].shape!=(16,3,128,128) or any(v.dtype!=np.uint8 for v in rgbs.values()):raise ValueError('fixed native RGB arrays')
    order=[(name,j) for name in ['cfd','pavetrack'] for j in range(len(rgbs[name]))]
    paths={};calls=[]
    for repeat,stream in enumerate([order,list(reversed(order))]):
        banks={name:np.lib.format.open_memmap(out/f'{name}_pass{repeat}.npy',mode='w+',dtype=np.float32,shape=(len(rgb),*rgb.shape[-2:])) for name,rgb in rgbs.items()}
        for name,j in stream:
            banks[name][j]=engine.predict(rgbs[name][j]);guard.take('prediction_rows');calls.append(dict(repeat=repeat,source=name,index=j))
        for name,values in banks.items():values.flush();paths[f'{name}_pass{repeat}.npy']=sha(out/f'{name}_pass{repeat}.npy')
        del banks
    state=engine.verify_unchanged();write(out/'prediction_freeze.json',dict(files=paths,state_digest=state,calls=calls,reference_evaluation_started=False,forwards=56,gradient_steps=0))
    maps={name:[np.load(out/f'{name}_pass{r}.npy',mmap_mode='r') for r in range(2)] for name in rgbs}
    differences={name:probe.repeat_difference(*values) for name,values in maps.items()}
    write(out/'repeatability.json',dict(maximum_absolute_difference=differences,tolerance=cfg['repeat_tolerance'],meaning='numerical reproducibility only, not training-seed stability'))
    if any(v>cfg['repeat_tolerance'] for v in differences.values()):raise ValueError('reproducibility unavailable; scientific inconclusive')
    refs=reference_loader()
    np.savez_compressed(out/'references.npz',**refs)
    result=probe.evaluate(maps['cfd'][0],refs['cfd'],maps['pavetrack'][0],refs['pavetrack'],cfg['primary']['margin'])
    write(out/'result.json',result);guard.check();return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--reviewed-commit',required=True);parser.add_argument('--manifest-sha256',required=True);args=parser.parse_args()
    cfg=json.loads((ROOT/'docs/research/S01/S01-E027/run_config.json').read_text());validate_config(cfg)
    # No torch model construction/forward on the Mac, even for a smoke test.
    prior.runtime.production_environment(cfg)
    mp=ROOT/'docs/research/S01/S01-E027/source_manifest.json'
    if sha(mp)!=args.manifest_sha256:raise ValueError('source manifest')
    for name,h in json.loads(mp.read_text())['files'].items():
        if sha(ROOT/name)!=h:raise ValueError('source '+name)
    args.run.mkdir(exist_ok=False,parents=True);guard=prior.Guard(cfg,args.run,start=START);stop=threading.Event()
    def watchdog():
        while not stop.wait(.25):
            if time.monotonic()-START>600 or guard.memory()>4*1024**3:
                write(args.run/'watchdog_stop.json',dict(reason='wall/RSS cap',elapsed=time.monotonic()-START));os._exit(124)
    threading.Thread(target=watchdog,daemon=True).start()
    try:
        lock=json.loads((ROOT/'docs/research/S01/S01-E027/data_lock.json').read_text())
        if set(p.name for p in args.input.iterdir())!=set(lock['files']):raise ValueError('input inventory')
        for name,rec in lock['files'].items():
            p=args.input/name
            if p.stat().st_size!=rec['bytes'] or sha(p)!=rec['sha256']:raise ValueError('locked input '+name)
        rgbs={}
        for name in ['cfd','pavetrack']:
            # The reference member is not decoded until all predictions freeze.
            with np.load(args.input/f'{name}.npz',allow_pickle=False) as z:rgbs[name]=z['rgb']
            shutil.copyfile(args.input/f'{name}_identities.json',args.run/f'{name}_identities.json')
            metadata=json.loads((args.input/f'{name}_identities.json').read_text())
            if len(metadata['rows'])!=len(rgbs[name]) or (name=='cfd' and [r['id'] for r in metadata['rows']]!=lock['cfd_ids']):raise ValueError('image identities')
            if any(hashlib.sha256(a.tobytes()).hexdigest()!=r['rgb_sha256'] for a,r in zip(rgbs[name],metadata['rows'],strict=True)):raise ValueError('RGB row identity')
            np.save(args.run/f'{name}_rgb.npy',rgbs[name])
        own=str(args.run.resolve()).casefold()+os.sep
        def audit(event,values):
            if event=='open' and isinstance(values[0],(str,bytes,os.PathLike)):
                p=os.path.abspath(os.fsdecode(values[0])).casefold()
                if '\\pavetrack_runs\\' in p and not (p+os.sep).startswith(own):raise PermissionError('other Run/source/qualification access')
        sys.addaudithook(audit)
        t,identity=prior.production_checks(cfg,guard);engine=Engine(t,cfg,args.input);guard.check()
        write(args.run/'launch.json',dict(reviewed_commit=args.reviewed_commit,manifest_sha256=args.manifest_sha256,identity=identity,checkpoint=cfg['checkpoint'],source_image_reads=0,qualification_reference_reads=0,gradient_steps=0))
        def references():
            if not (args.run/'prediction_freeze.json').exists():raise RuntimeError('reference before predictions')
            values={}
            for name in ['cfd','pavetrack']:
                with np.load(args.input/f'{name}.npz',allow_pickle=False) as z:values[name]=z['masks']
                meta=json.loads((args.input/f'{name}_identities.json').read_text())
                if any(hashlib.sha256(a.tobytes()).hexdigest()!=r['mask_sha256'] for a,r in zip(values[name],meta['rows'],strict=True)):raise ValueError('reference identity')
                if name=='cfd' and any(r['mask_field']!=lock['cfd_field'] for r in meta['rows']):raise ValueError('reference semantics')
            return values
        execute(rgbs,args.run,cfg,guard,engine,references)
        if sha(args.input/'DeepCrack_CT260_FT1.pth')!=cfg['checkpoint']['sha256']:raise ValueError('checkpoint file changed')
        analyze=module('e027_analyze',Path(__file__).with_name('analyze.py'));analyze.render(args.run)
        guard.check();write(args.run/'resource.json',guard.receipt())
        if guard.counts!=dict(models=0,updates=0,training_rows=0,prediction_rows=56):raise ValueError('exact production counts')
        write(args.run/'status.json',dict(state='completed',counts=guard.counts,source_models=1,model_fits=0))
        write(args.run/'output_receipt.json',dict(files={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in args.run.iterdir() if p.is_file()}));guard.check()
    except BaseException as exc:
        write(args.run/'status.json',dict(state='stopped',reason=repr(exc),counts=guard.counts,scientific='inconclusive_if_validity_failure'));write(args.run/'resource.json',guard.receipt());raise
    finally:stop.set()


if __name__=='__main__':main()
