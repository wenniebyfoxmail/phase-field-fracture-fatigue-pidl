"""Frozen E003 class-margin attribution, exact box coverage and bounded extraction."""
import collections,hashlib,io,json
from pathlib import Path
import importlib.util
import numpy as np
from PIL import Image
s=importlib.util.spec_from_file_location('e022_geometry_and_pixels',Path(__file__).resolve().parent.parent/'pavetrack_spatial_selector/spatial.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
box=old.box;context_box=old.context_box;image_bytes=old.image_bytes

def decode(raw,record,guard,counter):
    guard.take(counter)
    with Image.open(io.BytesIO(raw)) as src:
        src.load()
        if src.size!=(record['width'],record['height']):raise ValueError('source image dimensions')
        return src.convert('RGB')

def coverage(b,ctx):
    b=box(b);x1,y1,x2,y2=ctx
    if x2<=x1 or y2<=y1:raise ValueError('empty coverage context')
    xs=np.linspace(x1,x2,8);ys=np.linspace(y1,y2,8)
    wx=np.maximum(0,np.minimum(xs[1:],b[2])-np.maximum(xs[:-1],b[0]))/(xs[1:]-xs[:-1])
    wy=np.maximum(0,np.minimum(ys[1:],b[3])-np.maximum(ys[:-1],b[1]))/(ys[1:]-ys[:-1])
    return wy[:,None]*wx[None,:]

def describe_map(heat,original,corrected,ctx):
    h=np.asarray(heat,dtype=np.float64)
    if h.shape!=(7,7) or not np.isfinite(h).all() or (h<0).any():raise ValueError('class attribution map')
    mass=float(h.sum());areas=[];inside=[];z=[];covers=[]
    for b in [original,corrected]:
        cov=coverage(b,ctx);covers.append(cov.tolist());areas.append(float(cov.mean()));inside.append(float(np.sum(h*cov)));z.append(0. if mass<=1e-12 else inside[-1]/mass-areas[-1])
    values=[z[1],(z[1]-z[0])/2]
    if not np.isfinite(values).all() or any(abs(v)>1+1e-12 for v in values):raise ValueError('class descriptor bounds')
    return dict(values=[float(np.clip(v,-1,1)) for v in values],context=ctx,degenerate='zero_mass' if mass<=1e-12 else None,mass=mass,areas=areas,inside_mass=inside,concentrations=z,coverage=covers,heatmap=h.tolist())

def margin_attribution(head,features):
    """Only pooled leaf requires grad; no graph connects to backbone or parameters."""
    import torch
    if head.training or any(p.requires_grad or p.grad is not None for p in head.parameters()):raise ValueError('head parameters not frozen')
    f=features.detach()
    if f.ndim!=4 or tuple(f.shape[1:])!=(576,7,7) or not torch.isfinite(f).all():raise ValueError('final feature geometry/values')
    # clone outside inference_mode creates an ordinary leaf even for inference tensors.
    with torch.inference_mode(False),torch.enable_grad():
        z=f.mean((2,3)).detach().clone().requires_grad_(True)
        logits=head(z)
        if logits.shape!=(len(f),2) or not torch.isfinite(logits).all():raise ValueError('two-class logits')
        derivative=torch.autograd.grad((logits[:,1]-logits[:,0]).sum(),z,create_graph=False,retain_graph=False)[0]
        if not torch.isfinite(derivative).all():raise ValueError('margin input derivative')
        heat=torch.relu(torch.einsum('bk,bkij->bij',derivative.detach(),f.clone()))
    if any(p.grad is not None or p.requires_grad for p in head.parameters()) or features.grad is not None:raise ValueError('unexpected parameter/backbone gradient')
    if not torch.isfinite(heat).all():raise ValueError('nonfinite margin map')
    return [dict(heatmap=h.tolist(),logits=v.tolist(),input_gradient_inf=float(g.abs().max()),parameter_gradients=False,backbone_gradients=False) for h,v,g in zip(heat.detach().cpu(),logits.detach().cpu(),derivative.detach().cpu(),strict=True)]

def backend(cfg,lock,guard,core):
    path=Path(lock['E003_checkpoint'])
    if str(path)!=cfg['spatial']['checkpoint'] or lock['E003_checkpoint_sha256']!=cfg['spatial']['checkpoint_sha256']:raise ValueError('checkpoint scope')
    core.e12.checked(path,lock['E003_checkpoint_sha256'],guard.check)
    bridge=SemanticBackend(cfg,path,guard,core.e8.m.base.validate_reranker_checkpoint)
    core.e12.checked(path,lock['E003_checkpoint_sha256'],guard.check)
    return bridge

class SemanticBackend:
    def __init__(self,cfg,checkpoint,guard,validate):
        # Existing runtime supplies exact GPU1/WDDM identity, resource and transform checks.
        root=Path(__file__).resolve().parent.parent
        spec=importlib.util.spec_from_file_location('e022_gpu_runtime',root/'pavetrack_positive_evidence/stage_b_runtime.py');rt=importlib.util.module_from_spec(spec);spec.loader.exec_module(rt)
        proxy=dict(cfg,scoring={'backend':cfg['spatial']['backend']})
        self.bridge=rt.TorchBackend(proxy,checkpoint,guard,validate);self.guard=guard
        for model in [self.bridge.model,self.bridge.head]:
            model.eval()
            for param in model.parameters():param.requires_grad_(False);param.grad=None
        self.identity=dict(self.bridge.identity,class_mapping={'background':0,'crack':1},checkpoint_sha256=cfg['spatial']['checkpoint_sha256'],head_input_gradients=True,parameter_training=False,backbone_backward=False)
    def maps(self,image,contexts):
        t=self.bridge.torch
        if not 1<=len(contexts)<=16:raise ValueError('semantic batch size')
        for model in [self.bridge.model,self.bridge.head]:
            if model.training or any(p.requires_grad or p.grad is not None for p in model.parameters()):raise ValueError('model not frozen')
        self.guard.take('max_semantic_batches');self.guard.take('backbone_forwards',len(contexts));self.guard.take('head_forwards',len(contexts));self.guard.take('head_input_gradient_rows',len(contexts))
        with t.no_grad(),t.autocast('cuda',enabled=False):
            crops=[]
            for ctx in contexts:
                with image.crop(ctx) as crop:crops.append(self.bridge.transform(crop))
            x=t.stack(crops).to('cuda:0');features=self.bridge.model.features(x).detach().cpu()
        rows=margin_attribution(self.bridge.head,features)
        if any(p.grad is not None or p.requires_grad for p in self.bridge.model.parameters()):raise ValueError('backbone gradient')
        self.guard.check();return rows

def extract(data,run,cfg,guard,core,emit,bridge):
    if (run/'spatial_started.json').exists():raise ValueError('duplicate semantic extraction')
    if cfg['spatial']['grid_size']!=7 or cfg['spatial']['batch_size']!=16 or cfg['spatial']['mass_floor']!=1e-12 or cfg['spatial']['context_padding_fraction']!=.25:raise ValueError('fixed semantic recipe')
    emit('spatial_started.json',dict(protocol=core.PROTOCOL,images=len(data['images']),rows=len(data['candidates']),GT_free=True,fitted_parameters=0,runtime=bridge.identity))
    by=collections.OrderedDict()
    for row in data['candidates']:by.setdefault(row['image_id'],[]).append(row)
    output=[None]*len(data['candidates'])
    with (run/'image_progress.jsonl').open('x',encoding='utf8') as journal:
        for im,rows in by.items():
            if len(rows)>40:raise ValueError('frozen maximum40 contexts per source image')
            guard.check();record=data['images'][im];raw=image_bytes(record,guard);image=decode(raw,record,guard,'source_image_decodes');del raw
            try:
                for offset in range(0,len(rows),16):
                    batch=rows[offset:offset+16];contexts=[context_box([v['row']['original_box_xyxy'],v['row']['box_xyxy']],*image.size) for v in batch]
                    # Candidate geometry has corrected boxes within image bounds, hence positive contexts.
                    if any(ctx[2]<=ctx[0] or ctx[3]<=ctx[1] for ctx in contexts):raise ValueError('candidate identity yielded empty context')
                    maps=bridge.maps(image,contexts)
                    if len(maps)!=len(batch):raise ValueError('semantic batch row identity')
                    for row,ctx,heat in zip(batch,contexts,maps,strict=True):
                        guard.take('spatial_feature_rows');desc=describe_map(heat['heatmap'],row['row']['original_box_xyxy'],row['row']['box_xyxy'],ctx)
                        output[row['index']]=dict(index=row['index'],parent_id=row['parent_id'],image_id=im,location=row['location'],**(heat|desc))
            finally:image.close()
            journal.write(json.dumps(dict(image_id=im,sha256=record['prepared_image_sha256'],rows=len(rows)))+'\n');journal.flush()
    if any(v is None or v['index']!=i for i,v in enumerate(output)):raise ValueError('incomplete semantic descriptors')
    emit('spatial_features.json',dict(protocol=core.PROTOCOL,GT_free=True,fitted_parameters=0,rows=output))
    emit('spatial_extraction_receipt.json',dict(images=len(by),rows=len(output),progress_sha256=core.sha(run/'image_progress.jsonl',guard.check),features_sha256=core.sha(run/'spatial_features.json',guard.check),source_images=data['images'],runtime=bridge.identity,head_input_gradient_rows=guard.counts['head_input_gradient_rows'],parameter_gradient_steps=0,backbone_backward_rows=0))
    return output

def cases(data,targets,added,run,cfg,guard,core,emit):
    # Called only after complete OOF freeze and evaluation, never for learning.
    frozen=core.read(run/'prediction_freeze_receipt.json')
    for n,h in frozen['files'].items():core.e12.checked(run/n,h,guard.check)
    if not (run/'result.json').is_file():raise ValueError('case selection before evaluation')
    by={r['parent_id']:r for r in data['candidates']};originals={r['parent_id']:r for r in data['originals']};kind='OOF_appended' if added else 'FIT_opportunity_not_selected'
    keys={r['parent_id'] for r in added} if added else {r['parent_id'] for payload in data['labels'] for r in payload['rows'] if r['U']>0}
    keys=sorted(keys,key=lambda key:(-originals[key]['score'],by[key]['image_id'],tuple(by[key]['row']['box_xyxy']),key))[:cfg['spatial']['case_limit']];rows=[];buffers=[]
    for j,key in enumerate(keys):
        row=by[key];record=data['images'][row['image_id']];raw=image_bytes(record,guard)
        # One case decode occurs in rendering from this same verified buffer.
        buffers.append(raw);dest=run/'case_images'/f'{j}.jpg';dest.parent.mkdir(exist_ok=True);dest.write_bytes(raw)
        rows.append(dict(parent_id=key,image_id=row['image_id'],location=row['location'],kind=kind,width=record['width'],height=record['height'],original=originals[key],corrected=row['row'],GT=targets[row['image_id']],snapshot=dest.relative_to(run).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),descriptor=data['spatial'][row['index']]))
    payload=dict(rule='actual OOF additions else known FIT opportunities; descending original score,image,box,key; unique source keys; at most6',kind=kind,cases=rows,after_prediction_freeze_and_evaluation=True,used_for_learning=False)
    emit('cases.json',payload);return payload,buffers
