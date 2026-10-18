"""Train6-only spatial learning and never-deployed real-sample positive controls."""
import importlib.util
from pathlib import Path
import numpy as np
s=importlib.util.spec_from_file_location('e025_backend_base',Path(__file__).resolve().parent.parent/'pavetrack_qualified_localizer/model.py')
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
ReferenceUnavailable=base.ReferenceUnavailable
digest=base.digest
training_scope=base.training_scope


def network(cfg):
    import torch
    from torch import nn
    from torch.nn import functional as F
    def block(i,o):
        return nn.Sequential(nn.Conv2d(i,o,3,padding=1),nn.ReLU(),nn.Conv2d(o,o,3,padding=1),nn.ReLU())
    class RegionalModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.e0=block(3,8);self.e1=block(8,16);self.e2=block(16,32)
            self.d1=block(48,16);self.d0=block(24,8);self.out=nn.Conv2d(8,1,1)
        def forward(self,x):
            x=F.adaptive_avg_pool2d(x,(32,32));a=self.e0(x);b=self.e1(F.max_pool2d(a,2));z=self.e2(F.max_pool2d(b,2))
            z=self.d1(torch.cat((F.interpolate(z,size=b.shape[-2:],mode='bilinear',align_corners=False),b),1))
            return self.out(self.d0(torch.cat((F.interpolate(z,size=a.shape[-2:],mode='bilinear',align_corners=False),a),1)))
    m=RegionalModel()
    if sum(v.numel() for v in m.parameters())!=cfg['localizer']['parameters']:raise ValueError('spatial capacity')
    return m


def probability_loss(logits,y):
    import torch.nn.functional as F
    p=logits.sigmoid();axes=(1,2,3)
    return (F.binary_cross_entropy_with_logits(logits,y,reduction='none').mean(axes)+1-(2*(p*y).sum(axes)+1)/(p.sum(axes)+y.sum(axes)+1)).mean()


def control_indices(candidates,bank,cfg,fold):
    own=set(cfg['localizer']['train_locations'][fold]);seen=set();selected=[];n=cfg['localizer']['control']['contexts'];size=cfg['spatial']['grid_size']**2
    for r in sorted((v for v in candidates if v['location'] in own),key=lambda v:(int(v['location']),v['image_id'],v['index'])):
        if r['image_id'] in seen:continue
        total=int(bank['values'][bank['lookup'][r['index']]].sum())
        if 0<total<size:seen.add(r['image_id']);selected.append(r['index'])
        if len(selected)==n:return selected
    raise ReferenceUnavailable('fewer than fixed distinct train6 control images with both classes')


def support_buckets(by,bank):
    return {loc:{im:([i for i in ids if bank['values'][bank['lookup'][i]].any()],[i for i in ids if not bank['values'][bank['lookup'][i]].any()]) for im,ids in images.items()} for loc,images in by.items()}


def sample_batch(buckets,rng,batch_size,step):
    sites=sorted(buckets,key=int);ids=[]
    for j in range(batch_size):
        loc=sites[int(rng.integers(len(sites)))];images=sorted(buckets[loc]);im=images[int(rng.integers(len(images)))];pools=buckets[loc][im]
        # First row foreground, second background, repeat over the fixed stream.
        pool=pools[(step*batch_size+j)%2]
        if not pool:pool=pools[1-(step*batch_size+j)%2]
        if not pool:raise ReferenceUnavailable('empty training image context buckets')
        ids.append(pool[int(rng.integers(len(pool)))])
    return ids


def control_metrics(maps,bank,indices):
    from importlib import util
    spec=util.spec_from_file_location('e025_control_metrics',Path(__file__).resolve().parent/'spatial.py');sp=util.module_from_spec(spec);spec.loader.exec_module(sp)
    targets=np.stack([bank['values'][bank['lookup'][i]] for i in indices]);constant=float(targets.mean());records=[sp.component(p,y,constant) for p,y in zip(maps,targets,strict=True)]
    keys=['Brier','constant_Brier','zero_Brier','one_Brier','Dice','constant_Dice','all_background_Dice','all_foreground_Dice']
    values={key:float(np.mean([v[key] for v in records])) for key in keys}
    bg=min(values[k] for k in ['constant_Brier','zero_Brier','one_Brier'])-values['Brier']
    dg=values['Dice']-max(values[k] for k in ['constant_Dice','all_background_Dice','all_foreground_Dice'])
    return dict(metrics=values,constant=constant,Brier_gain=bg,foreground_Dice_gain=dg,passed=bool(bg>1e-6 and dg>1e-6),contexts=records)


class Backend(base.Backend):
    def fit(self,cache,bank,candidates,fold,control=None):
        t=self.t;cfg=self.cfg;g=self.guard;by,p,support=training_scope(candidates,bank,cfg,fold)
        selected=control_indices(candidates,bank,cfg,fold);ctl=cfg['localizer']['control']
        seed=(cfg['localizer']['seed'] if control is None else ctl['seeds'][control])+fold
        steps=cfg['localizer']['steps_per_fold'] if control is None else ctl['steps'];batch=cfg['localizer']['batch_size']
        if control is not None and len(selected)!=batch:raise ValueError('control full-batch identity')
        t.manual_seed(seed)
        if self.device.startswith('cuda'):t.cuda.manual_seed_all(seed)
        m=network(cfg).to(self.device).float().train()
        with t.no_grad():m.out.bias.zero_()
        opt=t.optim.AdamW(m.parameters(),lr=cfg['localizer']['lr'],weight_decay=cfg['localizer']['weight_decay'])
        buckets=support_buckets(by,bank);rng=np.random.default_rng(seed);last=None
        for step in range(steps):
            ids=selected if control is not None else sample_batch(buckets,rng,batch,step)
            x=t.tensor(np.asarray(cache[ids]),device=self.device,dtype=t.float32)/255
            y=t.tensor(np.stack([bank['values'][bank['lookup'][i]] for i in ids])[:,None],device=self.device,dtype=t.float32)
            opt.zero_grad(set_to_none=True);loss=probability_loss(m(x),y)
            if not t.isfinite(loss):raise ValueError('nonfinite spatial loss')
            loss.backward()
            if any(v.grad is None or not t.isfinite(v.grad).all() for v in m.parameters()):raise ValueError('nonfinite/missing spatial gradients')
            opt.step()
            if any(not t.isfinite(v).all() for v in m.parameters()):raise ValueError('nonfinite spatial weights')
            for key,n in [('localizer_steps',1),('gradient_steps',1),('parameter_gradient_steps',1),('localizer_training_rows',len(ids)),('localizer_backward_rows',len(ids))]:g.take(key,n)
            if control is not None:g.take('control_steps');g.take('control_training_rows',len(ids))
            last=float(loss.detach().cpu())
        state={k:v.detach().cpu().numpy().tolist() for k,v in m.state_dict().items()}
        return dict(fold=fold,parameters=cfg['localizer']['parameters'],verified=True,state=state,state_digest=digest(state),train_support=support,train_prevalence=p,seed=seed,steps=steps,last_loss=last,runtime=self.identity,control=control,control_indices=selected if control is not None else [],source='own train6 only; control never deployed' if control is not None else 'own train6 final-step multiscale RGB regional model')

    def predict(self,model,rgb):
        t=self.t;key=model['state_digest'];x=np.asarray(rgb)
        if not model['verified'] or digest(model['state'])!=key or x.dtype!=np.uint8 or tuple(x.shape[1:])!=(3,128,128):raise ValueError('frozen spatial model/prediction input')
        if key not in self.loaded:
            m=network(self.cfg);expected=m.state_dict();state={k:t.tensor(v,dtype=expected[k].dtype) for k,v in model['state'].items()}
            m.load_state_dict(state,strict=True);m=m.to(self.device).float().eval();m.requires_grad_(False);self.loaded[key]=m
        m=self.loaded[key]
        if m.training or any(v.requires_grad or v.grad is not None for v in m.parameters()):raise ValueError('prediction freeze')
        with t.no_grad(),t.autocast('cuda',enabled=False):out=m(t.tensor(x,device=self.device,dtype=t.float32)/255).sigmoid()[:,0].cpu().numpy().copy()
        if out.shape!=(len(x),32,32) or out.dtype!=np.float32 or not np.isfinite(out).all() or (out<0).any() or (out>1).any():raise ValueError('spatial output shape/numerics')
        return out
