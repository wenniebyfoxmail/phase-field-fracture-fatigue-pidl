"""Independent regional RGB CNN; no E003 model and no fitting on import."""
import collections,hashlib,json,math,os,subprocess
from pathlib import Path
import numpy as np

class ReferenceUnavailable(ValueError):
    pass

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def network(cfg):
    import torch
    layers=[]
    for j,(i,o,k,s,p) in enumerate(cfg['localizer']['architecture']):
        layers.append(torch.nn.Conv2d(i,o,k,stride=s,padding=p))
        if j<4:layers.append(torch.nn.ReLU())
    model=torch.nn.Sequential(*layers)
    if sum(v.numel() for v in model.parameters())!=cfg['localizer']['parameters']:raise ValueError('CNN capacity')
    return model

def probability_loss(logits,y,weight):
    import torch
    p=logits.sigmoid();axes=(1,2,3)
    return (((p-y)**2).mean(axes)+weight*(1-(2*(p*y).sum(axes)+1)/(p.sum(axes)+y.sum(axes)+1))).mean()

def training_scope(candidates,bank,cfg,fold):
    locs=set(cfg['localizer']['train_locations'][fold]);qual=set(cfg['localizer']['qual_locations'][fold]);held=set(cfg['held_groups'][fold])
    if locs&qual or (locs|qual)&held or locs|qual|held!=set(cfg['locations']):raise ValueError('split overlap/incomplete')
    chosen=[r for r in candidates if r['location'] in locs]
    if len(chosen)!=cfg['localizer']['train_rows'][fold] or set(bank['indices'])!={r['index'] for r in candidates if r['location'] in locs|qual}:raise ValueError('training bank identity')
    by=collections.defaultdict(lambda:collections.defaultdict(list))
    for r in chosen:by[r['location']][r['image_id']].append(r['index'])
    prevalence=float(np.mean([np.mean([np.mean([float(bank['values'][bank['lookup'][i]].mean()) for i in ids]) for ids in images.values()]) for images in by.values()]))
    positive=sum(int(bank['values'][bank['lookup'][r['index']]].sum()) for r in chosen);total=len(chosen)*cfg['spatial']['grid_size']**2
    if not 0<positive<total:raise ReferenceUnavailable('localizer training reference needs both classes')
    return by,prevalence,dict(locations=sorted(locs,key=int),images=sum(len(v) for v in by.values()),contexts=len(chosen),positive_cells=positive,total_cells=total)

class Backend:
    def __init__(self,cfg,guard,core=None,production=True):
        import torch
        self.t=torch;self.cfg=cfg;self.guard=guard;self.loaded={}
        if production:
            rt=core.e12.runtime;rt.production_environment(cfg)
            if os.environ.get('OPENBLAS_NUM_THREADS')!='1':raise PermissionError('CPU1')
            import torchvision
            if torch.__version__!=cfg['producer']['torch'] or torchvision.__version__!=cfg['producer']['torchvision']:raise ValueError('runtime versions')
            rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.free','--format=csv,noheader,nounits'],text=True)
            row=next([v.strip() for v in line.split(',')] for line in rows.splitlines() if line.split(',')[0].strip()=='1')
            if row[1]!=cfg['producer']['gpu_uuid'] or row[2]!=cfg['producer']['gpu_name'] or float(row[3])<8192:raise ValueError('GPU identity/free memory')
            path=core.ROOT/'docs/research/S01/S01-E012/stage_B/gpu_desktop_baseline.json';baseline=core.read(path)
            desktop=rt.desktop_inventory(subprocess.check_output(['nvidia-smi','-i','1','-q','-x'],text=True),baseline,lambda p:core.sha(Path(p),guard.check))
            if torch.cuda.device_count()!=1 or torch.cuda.get_device_name(0)!=cfg['producer']['gpu_name']:raise ValueError('logical GPU')
            self.device='cuda:0';guard.gpu=lambda:(torch.cuda.max_memory_allocated(0),torch.cuda.max_memory_reserved(0))
            self.identity=dict(torch=torch.__version__,torchvision=torchvision.__version__,physical_GPU=row[:3],desktop=desktop,baseline_sha256=core.sha(path),device=self.device,E003_loaded=False)
        else:self.device='cpu';self.identity=dict(domain='synthetic native unit test only',E003_loaded=False)
        torch.set_num_threads(1);torch.set_float32_matmul_precision('highest');torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
        guard.check()
    def fit(self,cache,bank,candidates,fold):
        t=self.t;cfg=self.cfg;g=self.guard;by,p,support=training_scope(candidates,bank,cfg,fold);seed=cfg['localizer']['seed']+fold
        t.manual_seed(seed)
        if self.device.startswith('cuda'):t.cuda.manual_seed_all(seed)
        model=network(cfg).to(self.device).float().train();p0=min(1-1e-4,max(1e-4,p))
        with t.no_grad():model[-1].bias.fill_(math.log(p0/(1-p0)))
        opt=t.optim.AdamW(model.parameters(),lr=cfg['localizer']['lr'],weight_decay=cfg['localizer']['weight_decay']);rng=np.random.default_rng(seed);sites=sorted(by,key=int);last=None
        for step in range(cfg['localizer']['steps_per_fold']):
            ids=[]
            for _ in range(cfg['localizer']['batch_size']):
                loc=sites[int(rng.integers(len(sites)))];images=sorted(by[loc]);im=images[int(rng.integers(len(images)))];pool=by[loc][im];ids.append(pool[int(rng.integers(len(pool)))])
            x=t.tensor(np.asarray(cache[ids]),device=self.device,dtype=t.float32)/255;y=t.tensor(np.stack([bank['values'][bank['lookup'][i]] for i in ids])[:,None],device=self.device,dtype=t.float32)
            opt.zero_grad(set_to_none=True);loss=probability_loss(model(x),y,cfg['localizer']['soft_dice_weight'])
            if not t.isfinite(loss):raise ValueError('nonfinite training loss')
            loss.backward()
            if any(v.grad is None or not t.isfinite(v.grad).all() for v in model.parameters()):raise ValueError('nonfinite/missing CNN gradient')
            opt.step()
            if any(not t.isfinite(v).all() for v in model.parameters()):raise ValueError('nonfinite CNN weights')
            for key,n in [('localizer_steps',1),('gradient_steps',1),('parameter_gradient_steps',1),('localizer_training_rows',len(ids)),('localizer_backward_rows',len(ids))]:g.take(key,n)
            last=float(loss.detach().cpu())
        state={k:v.detach().cpu().numpy().tolist() for k,v in model.state_dict().items()};model.zero_grad(set_to_none=True)
        return dict(fold=fold,parameters=6049,verified=True,state=state,state_digest=digest(state),train_support=support,train_prevalence=p,seed=seed,steps=cfg['localizer']['steps_per_fold'],last_loss=last,runtime=self.identity,source='own train6 RGB region CNN final step; no qualification feedback')
    def predict(self,model,rgb):
        t=self.t;key=model['state_digest'];x=np.asarray(rgb)
        if not model['verified'] or digest(model['state'])!=key or x.dtype!=np.uint8 or tuple(x.shape[1:])!=(3,128,128):raise ValueError('frozen model/prediction input')
        if key not in self.loaded:
            m=network(self.cfg);expected=m.state_dict()
            state={k:t.tensor(v,dtype=expected[k].dtype) for k,v in model['state'].items()};m.load_state_dict(state,strict=True);m=m.to(self.device).float().eval();m.requires_grad_(False);self.loaded[key]=m
        m=self.loaded[key]
        if m.training or any(v.requires_grad or v.grad is not None for v in m.parameters()):raise ValueError('prediction freeze')
        with t.no_grad(),t.autocast('cuda',enabled=False):out=m(t.tensor(x,device=self.device,dtype=t.float32)/255).sigmoid()[:,0].cpu().numpy().copy()
        if out.shape!=(len(x),32,32) or out.dtype!=np.float32 or not np.isfinite(out).all() or (out<0).any() or (out>1).any():raise ValueError('regional map shape/numerics')
        return out
