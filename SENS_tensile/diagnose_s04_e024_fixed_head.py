"""E024-D002: existing step8000 features, offline weighted linear oracle only."""
import argparse,copy,csv,json,platform,resource,time,hashlib
from pathlib import Path
import numpy as np
import torch
from threadpoolctl import threadpool_limits
from s04_e024_fixed_feature_oracle import project_head
from s04_e023_head_scale import physical_features
from s04_e024_head_tail import HEAD_LOCKS,CONTROL_LOCKS,build_candidate,admit_coordinate_map,set_phase,validate_head_scale,validate_coordinate_buffers,check_head_files
from run_s04_e024_head_tail_screen import validate_reference,admit_backbone,predict_in_chunks,anchor_component_geometry,state_digest,US
from s04_e018_global_local import compact_window
PROTOCOL='20261017-r1-E024-D002-fixed8000-tsvd'
STATES=('c20s4','c60s4','c83s4')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def scores(uv,data,window):
    mass=data['mass'];damage=data['damage']>.1
    masks={'full':np.ones(len(mass),bool),'damage':damage,'background':~damage,'inside_background':(~damage)&(window>0)}
    e=np.sum(((uv-data['equilibrated_uv'])/abs(US))**2,axis=1)
    return {name:float(np.sqrt(np.sum(mass[m]*e[m])/np.sum(mass[m]))) for name,m in masks.items()}

def network_order(model,xy,base,coef,chunk):
    out=np.empty_like(base)
    with torch.no_grad():
        weight=torch.tensor(coef[:-1].T.copy());bias=torch.tensor(coef[-1].copy())
        for start in range(0,len(xy),chunk):
            sl=slice(start,start+chunk);x=torch.tensor(xy[sl]);h=model.residual.encode((x-model.local_center)/model.local_scale)
            factor=((x[:,1]+.5)*(.5-x[:,1]))[:,None]*compact_window(x,model.lower,model.upper)
            raw=torch.nn.functional.linear(h*model.head_scale[:-1],weight,bias*model.head_scale[-1])
            out[sl]=base[sl]+(factor*raw).numpy()
    return out

def write_csv(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def run(a):
    start=time.perf_counter();torch.set_default_dtype(torch.float64);torch.set_num_threads(2)
    a.out.mkdir(parents=True,exist_ok=False)
    old=a.project/'local_archive/experiments/S04-E019/producer_execution_v1/raw';head=a.project/'local_archive/experiments/S04-E023/producer_execution_v1/raw';raw=a.case/'raw'
    manifest=read(a.case/'remote_final_manifest.json');assert manifest['commit']=='231fe4be83e26ef4054a2a6a567da51229185837' and not manifest['dirty']
    assert read(a.case/'final_execution_receipt.json')['producer_valid_rows']==3
    numerical=[];metric=[];pairs=[];assets=[];spectrum=[]
    for state in STATES:
        if time.perf_counter()-start>600:raise RuntimeError('diagnostic wall budget exceeded')
        path=next((raw/'runs').glob('*-'+state+'-localized-s7'));oldpath=head/'runs'/HEAD_LOCKS[state]['run_id'];check_head_files(state,oldpath)
        locked=[path/x for x in ('step_8000.pt','HEAD_ONLY_STAGE_ENTRY.json','head_scale.json','metrics.json','prediction.npz','RUN_RECEIPT.json')]
        for p in locked:
            want=manifest['files'][str(p.relative_to(raw))];assert sha(p)==want['sha256'] and p.stat().st_size==want['bytes']
        before={str(p):sha(p) for p in locked}
        data=validate_reference(state,old/'inputs'/f'{state}.npz');backbone,base,_=admit_backbone(state,old/'backbones'/state,data)
        geom=anchor_component_geometry(data['xy'],data['damage'],data['conn'],data['mass']);mapping=admit_coordinate_map(state,data,base,geom)
        model,local_cal=build_candidate(7,'localized',geom,backbone,mapping,data['xy'],data['mass'])
        snap=torch.load(path/'step_8000.pt',map_location='cpu',weights_only=True)
        assert snap['completed_updates']==8000 and snap['state']==state and snap['run_id']==path.name
        model.load_state_dict(snap['model_state_dict'],strict=True);set_phase(model,'head_only');cal=read(path/'head_scale.json');validate_head_scale(model,cal,'head_only');validate_coordinate_buffers(model,mapping)
        assert state_digest(model.backbone)==CONTROL_LOCKS[state]['backbone_digest'];digest=state_digest(model)
        phi=[]
        with torch.no_grad():
            for i in range(0,len(base),a.chunk):phi.append((physical_features(model,torch.tensor(data['xy'][i:i+a.chunk]))*model.head_scale).numpy())
        phi=np.concatenate(phi);theta=np.vstack([model.residual.output_layer.weight.detach().numpy().T,model.residual.output_layer.bias.detach().numpy()[None,:]])
        saved8000=predict_in_chunks(model,torch.tensor(data['xy'])).numpy();explicit=base+abs(US)*(phi@theta)
        forward_error=float(np.max(np.abs(explicit-saved8000)));assert forward_error<=1e-12
        window=compact_window(torch.tensor(data['xy']),model.lower,model.upper).detach().numpy()[:,0]
        bases={'backbone':base,'stage8000':saved8000}
        for name,p in (('E023',oldpath),('E024',path)):
            with np.load(p/'prediction.npz') as z:bases[name]=z['uv'].copy()
        baseline={name:scores(uv,data,window) for name,uv in bases.items()}
        t=next(x for x in read(path/'monitoring.json') if x['step']==8000)
        np.testing.assert_allclose(baseline['stage8000']['full'],t['displacement_mass_rms_over_abs_Us'],rtol=0,atol=1e-14)
        for name,score in baseline.items():metric.append(dict(state=state,arm=name,**score))
        target=(data['equilibrated_uv']-base)/abs(US)
        sol,info=project_head(phi,target,data['mass'])
        for j,s in enumerate(info.pop('singular_values')):spectrum.append(dict(state=state,index=j+1,singular_value=float(s)))
        for row in sol:
            coef=row.pop('coef');basis_uv=base+abs(US)*row.pop('prediction');projected_uv=base+abs(US)*row.pop('projection_prediction')
            realized=network_order(model,data['xy'],base,coef,a.chunk);score=scores(realized,data,window);projection_score=scores(projected_uv,data,window)
            normalized_error=(realized-basis_uv)/abs(US);realization=float(np.sqrt(np.sum(data['mass']*np.sum(normalized_error**2,axis=1))/data['mass'].sum()))
            outside=float(abs(realized[window==0]-base[window==0]).max());assert outside==0.
            numerical.append(dict(state=state,**info,**row,stage_forward_max_abs=forward_error,network_vs_basis_mass_rms=realization,network_vs_basis_max_abs=float(abs(realized-basis_uv).max()),realized_full_rms=score['full'],projected_full_rms=projection_score['full'],full_rms_realization_gap=abs(score['full']-projection_score['full']),outside_max_abs_delta=outside))
            metric.append(dict(state=state,arm=f"oracle_x{row['multiplier']:g}",**score))
            if row['primary']:
                np.savez_compressed(a.out/f'{state}_oracle.npz',uv=realized,projection_uv=projected_uv,basis_uv=basis_uv,head_coefficients=coef)
                for name,baseline_score in baseline.items():
                    for region in score:pairs.append(dict(state=state,comparator=name,region=region,baseline=baseline_score[region],oracle=score[region],change_percent=100*(score[region]/baseline_score[region]-1)))
            np.save(a.out/f"{state}_coeff_x{row['multiplier']:g}.npy",coef,allow_pickle=False)
        assert digest==state_digest(model) and all(p.grad is None for p in model.parameters())
        assert all(sha(Path(p))==h for p,h in before.items())
        assets.append(dict(state=state,run_id=path.name,reference_sha256=data['reference_sha256'],snapshots=before,head_scale_sha256=sha(path/'head_scale.json'),model_digest_before=digest,model_digest_after=state_digest(model),initial_Mac_calibration_bit_exact=(local_cal==cal),scope='Actual producer snapshot/D, supplemental diagnostic; strict native Mac/LR/mass/D/rho qualification remains refused'))
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
        if peak>3*1024**3:raise RuntimeError('diagnostic observed RSS budget exceeded')
        print(state,'DONE',[(r['rank'],r['realized_full_rms']) for r in numerical if r['state']==state],flush=True)
        del model,phi,sol
    for name,rows in [('regional_metrics.csv',metric),('paired_comparison.csv',pairs),('numerical_diagnostics.csv',numerical),('singular_values.csv',spectrum)]:write_csv(a.out/name,rows)
    record=dict(protocol=PROTOCOL,states=list(STATES),stage=8000,assets=assets,wall_seconds=time.perf_counter()-start,peak_rss_bytes=int(peak),linear_diagnostic_solutions=9,neural_optimizer_steps=0,checkpoint_writes=0,remote_actions=0,rank_rule='eps64*max(N,p)*smax, multipliers .1/1/10 all reported; primary1',physical_tolerance_defined=False,legacy001_route_gate=False)
    (a.out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--case',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--chunk',type=int,default=1024);a=p.parse_args();assert 1<=a.chunk<=1024
    with threadpool_limits(limits=2):run(a)
