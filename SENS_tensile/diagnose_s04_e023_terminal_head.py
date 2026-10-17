"""E024-D003: existing E023 joint step10000 features, offline weighted linear oracle only."""
import argparse,copy,csv,json,platform,resource,time,hashlib,subprocess,inspect
from pathlib import Path
import numpy as np
import torch
from threadpoolctl import threadpool_limits
from s04_e024_fixed_feature_oracle import project_head
from s04_e023_head_scale import physical_features
from diagnose_s04_e023_endpoints import load_endpoint
from s04_e024_head_tail import HEAD_LOCKS,CONTROL_LOCKS,build_candidate,admit_coordinate_map,set_phase,validate_head_scale,validate_coordinate_buffers,check_head_files
from run_s04_e024_head_tail_screen import validate_reference,admit_backbone,predict_in_chunks,anchor_component_geometry,state_digest,US
from s04_e018_global_local import compact_window
PROTOCOL='20261017-r1-E024-D003-terminal10000-tsvd'
STATES=('c20s4','c60s4','c83s4')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def scores(uv,data,window):
    if not np.isfinite(uv).all():raise ValueError('nonfinite realized UV')
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
    source=Path(__file__).resolve().parents[1]
    commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    assert commit==a.expected_commit
    source_hashes={str(p.relative_to(source)):sha(p) for p in (Path(__file__).resolve(),Path(inspect.getsourcefile(project_head)).resolve())}
    start=time.perf_counter();torch.set_default_dtype(torch.float64);torch.set_num_threads(2)
    a.out.mkdir(parents=True,exist_ok=False)
    old=a.project/'local_archive/experiments/S04-E019/producer_execution_v1/raw'
    root=a.project/'local_archive/experiments'
    e021=root/'S04-E021/producer_execution_v2/raw';e022=root/'S04-E022/producer_execution_v1/raw';e023=root/'S04-E023/producer_execution_v1/raw'
    numerical=[];metric=[];pairs=[];assets=[];spectrum=[];blend_rows=[]
    for state in STATES:
        if time.perf_counter()-start>600:raise RuntimeError('diagnostic wall budget exceeded')
        path=e023/'runs'/HEAD_LOCKS[state]['run_id'];check_head_files(state,path)
        before={str(path/n):sha(path/n) for n in HEAD_LOCKS[state]['files']}
        model,data,base,saved_terminal,asset=load_endpoint(old,e021,e022,e023,state,'E023')
        digest=state_digest(model)
        phi=[]
        with torch.no_grad():
            for i in range(0,len(base),a.chunk):phi.append((physical_features(model,torch.tensor(data['xy'][i:i+a.chunk]))*model.head_scale).numpy())
        phi=np.concatenate(phi);theta=np.vstack([model.residual.output_layer.weight.detach().numpy().T,model.residual.output_layer.bias.detach().numpy()[None,:]])
        explicit=base+abs(US)*(phi@theta)
        forward_error=float(np.max(np.abs(explicit-saved_terminal)));assert forward_error<=1e-12
        window=compact_window(torch.tensor(data['xy']),model.lower,model.upper).detach().numpy()[:,0]
        bases={'backbone':base,'E023':saved_terminal}
        baseline={name:scores(uv,data,window) for name,uv in bases.items()}
        for name,score in baseline.items():metric.append(dict(state=state,arm=name,**score))
        target=(data['equilibrated_uv']-base)/abs(US)
        sol,info=project_head(phi,target,data['mass'])
        if time.perf_counter()-start>600:raise RuntimeError('diagnostic wall budget exceeded after SVD')
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
                for fraction in (.01,.05,.1):
                    blended_coef=theta+fraction*(coef-theta)
                    blended_uv=network_order(model,data['xy'],base,blended_coef,a.chunk)
                    expected=saved_terminal+fraction*(realized-saved_terminal)
                    assert np.max(abs(blended_uv-expected))<1e-12
                    assert np.max(abs(blended_uv[window==0]-base[window==0]))==0.
                    bs=scores(blended_uv,data,window)
                    metric.append(dict(state=state,arm=f'blend_{fraction:g}',**bs))
                    delta_norm=float(np.linalg.norm(blended_coef-theta))
                    blend_rows.append(dict(state=state,fraction=fraction,coefficient_delta_norm=delta_norm,coefficient_delta_relative=delta_norm/np.linalg.norm(theta),field_update_rms=float(np.sqrt(np.sum(data['mass']*np.sum(((blended_uv-saved_terminal)/abs(US))**2,axis=1))/data['mass'].sum())),realization_linearity_max_abs=float(np.max(abs(blended_uv-expected)))))
                    np.savez_compressed(a.out/f'{state}_blend_{fraction:g}.npz',uv=blended_uv,head_coefficients=blended_coef)
                for arm in [r for r in metric if r['state']==state and (r['arm']=='oracle_x1' or r['arm'].startswith('blend_'))]:
                    for region in baseline['E023']:
                        pairs.append(dict(state=state,arm=arm['arm'],region=region,baseline=baseline['E023'][region],candidate=arm[region],change_percent=100*(arm[region]/baseline['E023'][region]-1)))
            np.save(a.out/f"{state}_coeff_x{row['multiplier']:g}.npy",coef,allow_pickle=False)
        assert digest==state_digest(model) and all(p.grad is None for p in model.parameters())
        assert all(sha(Path(p))==h for p,h in before.items())
        assets.append(dict(**asset,original_files_sha256_before=before,model_digest_before=digest,model_digest_after=state_digest(model),original_files_unchanged=True,original_coefficient_norm=float(np.linalg.norm(theta))))
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
        if peak>3*1024**3:raise RuntimeError('diagnostic observed RSS budget exceeded')
        print(state,'DONE',[(r['rank'],r['realized_full_rms']) for r in numerical if r['state']==state],flush=True)
        del model,phi,sol
    for name,rows in [('regional_metrics.csv',metric),('paired_comparison.csv',pairs),('numerical_diagnostics.csv',numerical),('singular_values.csv',spectrum),('partial_correction.csv',blend_rows)]:write_csv(a.out/name,rows)
    if time.perf_counter()-start>600:raise RuntimeError('diagnostic wall budget exceeded before receipt')
    record=dict(diagnostic_run_id='S04-E024-D003-R001-local-tsvd',diagnostic_code_commit=commit,diagnostic_source_sha256=source_hashes,protocol=PROTOCOL,states=list(STATES),stage=10000,assets=assets,wall_seconds=time.perf_counter()-start,peak_rss_bytes=int(peak),linear_diagnostic_solutions=9,neural_optimizer_steps=0,checkpoint_writes=0,remote_actions=0,partial_fractions=[.01,.05,.1],partial_evaluations=9,rank_rule='eps64*max(N,p)*smax, multipliers .1/1/10 all reported; primary1',physical_tolerance_defined=False,legacy001_route_gate=False)
    (a.out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--case',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-commit',required=True);p.add_argument('--chunk',type=int,default=1024);a=p.parse_args();assert 1<=a.chunk<=1024
    with threadpool_limits(limits=2):run(a)
