"""Read-only E022/E023 physical/actual head coordinates; no fit or update."""
import argparse,copy,gc,json,platform,subprocess
from pathlib import Path
import numpy as np
import torch
from diagnose_s04_e020_features import rss
from diagnose_s04_e021_endpoints import spectrum
from diagnose_s04_e022_endpoints import load_endpoint as load_e022_endpoint
from run_s04_e019_frozen_residual_screen import validate_reference,admit_backbone,predict_in_chunks,anchor_component_geometry,US,sha256
from s04_e019_frozen_residual import state_digest
from s04_e018_global_local import compact_window
from s04_e023_head_scale import LEAK_LOCKS,CONTROL_LOCKS,build_candidate,validate_head_scale,validate_activation,validate_coordinate_buffers,validate_behavior_envelope,admit_coordinate_map,check_pair_identity
REGIONS=('damage','background_inside','background_outside')
SCIENCE='c4ceb5d27fa8d408be1b9f02dcd6b10308f301a2'
PROTOCOL='20261017-r1-E022-E023-physical-scaled-readonly'

def measure_dual(model, data, base, saved, chunk):
    """All-node full objective, three disjoint losses; explicit head algebra."""
    before = state_digest(model)
    named = list(model.residual.named_parameters())
    params = [p for _,p in named]
    gradients = [[torch.zeros_like(p) for p in params] for _ in REGIONS]
    layers = [model.residual.input_layer, *model.residual.hidden_layers]
    width = model.residual.output_layer.in_features
    hdim = width+1
    w = data['mass']/data['mass'].sum()
    xy_np = data['xy']
    with torch.no_grad():
        window = compact_window(torch.tensor(xy_np), model.lower, model.upper).numpy()[:,0]
    active = data['damage'] > .1
    masks = [active, ~active & (window>0), ~active & (window==0)]
    assert np.all(np.sum(masks, axis=0)==1)
    masses = np.array([w[m].sum() for m in masks]); assert np.all(masses>0)
    grams = np.zeros((3,hdim,hdim)); cross = np.zeros((3,hdim,2)); direct = np.zeros((3,hdim,2))
    loss = np.zeros(3)
    stats = [[dict(pos=np.zeros(width),rawpos=np.zeros(width),second=np.zeros(width),ever=np.zeros(width,bool)) for _ in REGIONS] for _ in layers]
    b = np.vstack([model.residual.output_layer.weight.detach().numpy().T,model.residual.output_layer.bias.detach().numpy()[None,:]])
    scale_np=model.head_scale.detach().numpy().copy() if hasattr(model,'head_scale') else np.ones(hdim)
    assert scale_np.shape==(hdim,) and np.isfinite(scale_np).all() and (scale_np>0).all()
    b_physical=scale_np[:,None]*b
    max_uv = 0.; formula_uv = 0.; additive = 0.
    for start in range(0,len(w),chunk):
        sl=slice(start,min(start+chunk,len(w)))
        xy=torch.tensor(xy_np[sl]); wt=torch.tensor(w[sl])
        center=model.local_center if hasattr(model,'local_center') else model.center
        scale=model.local_scale if hasattr(model,'local_scale') else model.scale
        z=(xy-center)/scale
        factor=((xy[:,1]+.5)*(.5-xy[:,1]))[:,None]*compact_window(xy,model.lower,model.upper)
        acts=[]; raw=[]
        for layer,activation in zip(layers,model.residual.activations):
            pre=layer(z);raw.append(pre);z=activation(pre);acts.append(z)
        predicted=torch.tensor(base[sl])+factor*torch.nn.functional.linear(z*torch.tensor(scale_np[:-1]),model.residual.output_layer.weight,model.residual.output_layer.bias*float(scale_np[-1]))
        error=(predicted-torch.tensor(data['equilibrated_uv'][sl]))/abs(US)
        sq=(error**2).sum(dim=1)
        pieces=[(wt*sq*torch.tensor(m[sl])).sum() for m in masks]
        for r,piece in enumerate(pieces):
            g=torch.autograd.grad(piece,params,retain_graph=(r<2 or start==0))
            for dest,src in zip(gradients[r],g):dest.add_(src)
            loss[r]+=float(piece.detach())
        if start==0:
            gfull=torch.autograd.grad(sum(pieces),params)
            # First chunk has exactly the accumulated gradients so far.
            for i,g in enumerate(gfull):
                torch.testing.assert_close(sum(gradients[r][i] for r in range(3)),g,rtol=1e-9,atol=1e-14)
                additive=max(additive,float(torch.max(torch.abs(sum(gradients[r][i] for r in range(3))-g))))
        with torch.no_grad():
            original=torch.tensor(base[sl])+model.correction_physical(xy)
            formula_uv=max(formula_uv,float((predicted-original).abs().max()))
            max_uv=max(max_uv,float(np.max(np.abs(predicted.numpy()-saved[sl]))))
            feature=(factor*torch.cat([z,torch.ones_like(factor)],dim=1)/abs(US)).detach()
            residual_target=torch.tensor((data['equilibrated_uv'][sl]-base[sl])/abs(US))
            # Explicit head prediction must equal current residual output.
            torch.testing.assert_close(feature@torch.tensor(b_physical), (predicted-torch.tensor(base[sl]))/abs(US),rtol=1e-10,atol=1e-14)
            for r,mask in enumerate(masks):
                selected=mask[sl];weights=torch.tensor(w[sl]*selected)
                grams[r]+=(feature.T@(weights[:,None]*feature)).numpy()
                cross[r]+=(feature.T@(weights[:,None]*residual_target)).numpy()
                direct[r]+=(feature.T@(weights[:,None]*error)).numpy()
                for li,(act,pre) in enumerate(zip(acts,raw)):
                    a=act.detach().numpy();x=pre.detach().numpy();ww=weights.numpy()
                    stats[li][r]['pos']+=np.sum(ww[:,None]*(a>0),axis=0)
                    stats[li][r]['rawpos']+=np.sum(ww[:,None]*(x>0),axis=0)
                    stats[li][r]['second']+=np.sum(ww[:,None]*(factor.numpy()*a/abs(US))**2,axis=0)
                    if selected.any():stats[li][r]['ever']|=(np.abs((factor.numpy()*a)[selected])>0).any(axis=0)
        rss()
        del predicted,error,pieces,acts,raw,z,g
    assert state_digest(model)==before
    assert all(p.grad is None for p in model.parameters())
    np.testing.assert_allclose(formula_uv,0,rtol=0,atol=1e-12)
    assert max_uv <= 1e-12
    output_indices={name:i for i,(name,_) in enumerate(named)}
    head_rows=[]
    for r,name in enumerate((*REGIONS,'full')):
        h=grams[r] if r<3 else grams.sum(axis=0)
        c=cross[r] if r<3 else cross.sum(axis=0)
        d=direct[r] if r<3 else direct.sum(axis=0)
        ls=loss[r] if r<3 else loss.sum()
        gs=gradients[r] if r<3 else [sum(g[i] for g in gradients) for i in range(len(params))]
        autograd=np.vstack([gs[output_indices['output_layer.weight']].numpy().T,gs[output_indices['output_layer.bias']].numpy()[None,:]])
        assert all(np.isfinite(v).all() for v in (h,b,c,d))
        for coordinate in ('physical','actual'):
            v=np.ones_like(scale_np) if coordinate=='physical' else scale_np
            hh=h*v[:,None]*v[None,:];cc=c*v[:,None];dd=d*v[:,None]
            bb=b_physical if coordinate=='physical' else b
            gg=autograd/scale_np[:,None] if coordinate=='physical' else autograd
            algebra=np.einsum('ij,jk->ik',hh,bb,optimize=False)-cc
            np.testing.assert_allclose(2*dd,gg,rtol=1e-8,atol=1e-12)
            np.testing.assert_allclose(algebra,dd,rtol=1e-7,atol=1e-12)
            denom=float(np.sqrt(max(0,np.trace(hh)*ls)));diag=np.diag(hh)
            valid=diag>max(float(diag.max())*1e-14,1e-30)
            head_rows.append(dict(coordinate=coordinate,region=name,loss_contribution=float(ls),gradient_norm=float(np.linalg.norm(2*dd)),
                scaled_normal_residual=float(np.linalg.norm(dd)/denom) if denom>1e-30 else None,
                max_feature_residual_correlation=float(np.max(np.linalg.norm(dd[valid],axis=1)/np.sqrt(diag[valid]*ls))) if valid.any() and ls>0 else None,
                normal_vs_direct_max_error=float(np.max(np.abs(algebra-dd))),autodiff_max_error=float(np.max(np.abs(2*dd-gg))),**spectrum(hh)))
    groups={'all':list(range(len(named))),'hidden':[i for i,(n,_) in enumerate(named) if not n.startswith('output_layer.')],'head':[i for i,(n,_) in enumerate(named) if n.startswith('output_layer.')]}
    for i,(n,_) in enumerate(named):groups.setdefault(n.rsplit('.',1)[0],[]).append(i)
    gradient_rows=[]
    for coordinate in ('physical','actual'):
        mapped=[[g.clone() for g in region] for region in gradients]
        if coordinate=='physical':
            for region in mapped:
                region[output_indices['output_layer.weight']].div_(torch.tensor(scale_np[:-1])[None,:])
                region[output_indices['output_layer.bias']].div_(float(scale_np[-1]))
        for group,idx in groups.items():
            dot=np.array([[sum(float(torch.sum(mapped[a][i]*mapped[b_][i])) for i in idx) for b_ in range(3)] for a in range(3)])
            norm=np.sqrt(np.maximum(np.diag(dot),0));denom=norm[0]*norm[1]
            gradient_rows.append(dict(coordinate=coordinate,group=group,damage_norm=float(norm[0]),inside_background_norm=float(norm[1]),outside_background_norm=float(norm[2]),
                full_norm=float(np.sqrt(max(0,dot.sum()))),damage_inside_cosine=float(dot[0,1]/denom) if min(norm[0],norm[1])>1e-30 else None,
                damage_dot_full_gradient=float(dot[0].sum()),inside_background_dot_full_gradient=float(dot[1].sum()),damage_inside_dot=float(dot[0,1])))
    activation_rows=[]
    for li in range(len(layers)):
        for r,name in enumerate(REGIONS):
            s=stats[li][r]
            activation_rows.append(dict(layer=li,region=name,coeff=float(model.residual.activations[li].coeff.detach()),
                active_fraction=float(np.mean(s['pos']/masses[r])),raw_positive_fraction=float(np.mean(s['rawpos']/masses[r])),
                effective_ever_units=int(s['ever'].sum()),width=width,effective_rms_activation=float(np.sqrt(s['second'].sum()/masses[r]/width))))
    damage_outside=active & (window==0)
    damage_outside_loss=float(np.sum(w[damage_outside]*np.sum((saved[damage_outside]-data['equilibrated_uv'][damage_outside])**2,axis=1)/abs(US)**2))
    return dict(damage_outside_nodes=int(damage_outside.sum()),damage_outside_loss_contribution=damage_outside_loss,full_rms=float(np.sqrt(loss.sum())),regional_rms={name:float(np.sqrt(loss[r]/masses[r])) for r,name in enumerate(REGIONS)},
        region_mass=dict(zip(REGIONS,masses.tolist())),head=head_rows,gradients=gradient_rows,activations=activation_rows,
        saved_uv_max_difference=max_uv,formula_uv_max_difference=formula_uv,first_chunk_additivity_max_error=additive,
        model_digest_before=before,model_digest_after=state_digest(model),parameter_updates=0,peak_rss_bytes=rss())


def load_endpoint(old,e021,e022,e023,state,arm):
    if arm=='E022':return load_e022_endpoint(old,e021,e022,state,'E022')
    assert arm=='E023'
    manifest=e023.parent/'retrieval_verification.json'
    lock=json.loads((Path(__file__).resolve().parents[1]/'docs/research/S04/S04-E023/result_verification.json').read_text())
    assert sha256(manifest)==lock['retrieval_verification_sha256']
    verified=json.loads(manifest.read_text());assert verified['all_sha256_verified'] and verified['summary']['valid_completed_runs']==3 and verified['head']==SCIENCE
    data=validate_reference(state,old/'inputs'/f'{state}.npz');backbone,base,_=admit_backbone(state,old/'backbones'/state,data)
    geom=anchor_component_geometry(data['xy'],data['damage'],data['conn'],data['mass']);mapping=admit_coordinate_map(state,data,base,geom)
    matches=list((e023/'runs').glob('*-'+state+'-localized-s7'));assert len(matches)==1;path=matches[0]
    assert sum(n.startswith('runs/'+path.name+'/') for n in verified['files'])==11
    for name,identity in verified['files'].items():
        if name.startswith('runs/'+path.name+'/'):
            p=e023/name;assert p.stat().st_size==identity['bytes'] and sha256(p)==identity['sha256']
    record,receipt,pre=[json.loads((path/n).read_text()) for n in ('metrics.json','RUN_RECEIPT.json','PRE_UPDATE.json')]
    cp=torch.load(path/'final_step_10000.pt',map_location='cpu',weights_only=True)
    for asset in (record,receipt,pre,cp):validate_behavior_envelope(asset,state)
    assert receipt['code_commit']==SCIENCE and receipt['dirty'] is False and record['steps']==record['new_optimizer_steps']==10000 and pre['new_optimizer_steps']==0
    assert len(receipt['archive_file_hashes'])==10
    for name,h in receipt['archive_file_hashes'].items():assert sha256(path/name)==h
    for name,h in LEAK_LOCKS[state]['files'].items():assert sha256(e022/'runs'/LEAK_LOCKS[state]['run_id']/name)==h
    actual=np.load(path/'learning_rates.npy',allow_pickle=False)
    for p in (path/'expected_learning_rates.npy',e023/'preflight_learning_rates.npy',e022/'runs'/LEAK_LOCKS[state]['run_id']/'learning_rates.npy'):
        np.testing.assert_array_equal(actual,np.load(p,allow_pickle=False))
    check_pair_identity(state,geom,record['backbone_digest'],record['initial_residual_digest'],record['sampler_index_sha256'])
    calibration=json.loads((path/'head_scale.json').read_text());formal=json.loads((e023/'baseline_preflight.json').read_text());row=next(x for x in formal['rows'] if x['state']==state)
    for name,folder,key in (('head_scale.json','preflight_head_scales','head_scale_sha256'),('head_gradient_preflight.json','preflight_head_gradients','head_gradient_preflight_sha256')):
        assert sha256(path/name)==sha256(e023/folder/f'{state}.json')==row[key]
    model,local_cal=build_candidate(7,'localized',geom,backbone,mapping,data['xy'],data['mass'])
    # Actual producer D is an immutable part of the saved model. Mac bit replay remains failed.
    model.load_state_dict(cp['model_state_dict'],strict=True);validate_head_scale(model,calibration);validate_activation(model);validate_coordinate_buffers(model,mapping)
    assert state_digest(model.backbone)==CONTROL_LOCKS[state]['backbone_digest']
    for n in ('lower','upper','center','scale'):torch.testing.assert_close(getattr(model,n),torch.tensor(geom[n]),rtol=0,atol=0)
    with np.load(path/'prediction.npz') as f:saved=f['uv'].copy()
    np.testing.assert_allclose(predict_in_chunks(model,torch.tensor(data['xy'])).numpy(),saved,rtol=0,atol=1e-12)
    asset=dict(run_id=path.name,checkpoint_sha256=sha256(path/'final_step_10000.pt'),prediction_sha256=sha256(path/'prediction.npz'),reference_sha256=data['reference_sha256'],head_scale_sha256=sha256(path/'head_scale.json'),map=mapping,behavior='E023 fixed producerD plus E022leak',initial_calibration_bit_exact=(local_cal==calibration),scope='Supplementary actual-saved-model diagnostic; strict Mac LR/mass/D/rho failures retained')
    rss();return model.eval(),data,base,saved,asset


def main():
    p=argparse.ArgumentParser()
    for name in ('old','e021','e022','e023','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--chunk',type=int,default=256);p.add_argument('--single',action='store_true');a=p.parse_args();assert 1<=a.chunk<=1024
    torch.set_default_dtype(torch.float64);torch.set_num_threads(2);a.out.mkdir(parents=True,exist_ok=False)
    pairs=[(s,arm) for s in ('c20s4','c60s4','c83s4') for arm in ('E022','E023')]
    if a.single:pairs=[('c20s4','E023')]
    results=[]
    for state,arm in pairs:
        model,data,base,saved,assets=load_endpoint(a.old,a.e021,a.e022,a.e023,state,arm)
        result=measure_dual(model,data,base,saved,a.chunk)
        expected=float(np.sqrt(np.sum(data['mass']/data['mass'].sum()*np.sum((saved-data['equilibrated_uv'])**2,axis=1)))/abs(US))
        np.testing.assert_allclose(result['full_rms'],expected,rtol=0,atol=1e-14)
        if arm=='E022':
            prior=json.loads((a.e022.parent.parent/'endpoint_diagnostic_v1/results'/f'{state}_E022.json').read_text())
            for now,then in zip([x for x in result['head'] if x['coordinate']=='physical'],prior['head']):
                for key in ('loss_contribution','gradient_norm','scaled_normal_residual'):
                    if now[key] is None:assert then[key] is None
                    else:np.testing.assert_allclose(now[key],then[key],rtol=1e-10,atol=1e-14)
        result.update(state=state,arm=arm,assets=assets)
        (a.out/f'{state}_{arm}.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');results.append(result)
        print(json.dumps(dict(state=state,arm=arm,full=result['full_rms'],peak_rss_bytes=rss())),flush=True)
        del model,data,base,saved;gc.collect()
    deps=[Path(__file__),Path(__file__).with_name('diagnose_s04_e021_endpoints.py'),Path(__file__).with_name('diagnose_s04_e022_endpoints.py'),Path(__file__).with_name('diagnose_s04_e020_features.py'),Path(__file__).with_name('s04_e023_head_scale.py')]
    meta=dict(protocol_revision=PROTOCOL,training=False,parameter_updates=0,optimizer_created=False,least_squares_fit=False,chunk=a.chunk,peak_rss_bytes=rss(),source_hashes={p.name:sha256(p) for p in deps},code_commit=subprocess.check_output(['git','-C',str(Path(__file__).resolve().parents[1]),'rev-parse','HEAD'],text=True).strip(),python=platform.python_version(),torch=str(torch.__version__),numpy=np.__version__,results=results)
    (a.out/'summary.json').write_text(json.dumps(meta,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
