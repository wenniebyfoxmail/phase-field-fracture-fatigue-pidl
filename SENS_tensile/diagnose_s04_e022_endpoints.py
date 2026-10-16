"""Archived E021/E022 endpoints: reuse reviewed reductions, never fit or update."""
import argparse
import gc
import json
import platform
import subprocess
from pathlib import Path
import numpy as np
import torch
from diagnose_s04_e021_endpoints import measure
from diagnose_s04_e020_features import rss
from run_s04_e019_frozen_residual_screen import validate_reference,admit_backbone,anchor_component_geometry,predict_in_chunks,US,sha256
from s04_e019_frozen_residual import state_digest
from s04_e022_screen import (DIRECT_LOCKS,CONTROL_LOCKS,admit_coordinate_control,admit_coordinate_map,
    build_candidate,build_relu_candidate,validate_activation,validate_coordinate_buffers,validate_behavior_envelope,check_pair_identity)
SCIENCE='a540888497d1838a6aa202f59a884e6930e50fb4'
PROTOCOL='20261016-r1-E021-E022-readonly-head-gradient'


def load_endpoint(old,control,candidate,state,arm):
    rss()
    data=validate_reference(state,old/'inputs'/f'{state}.npz')
    backbone,base,_=admit_backbone(state,old/'backbones'/state,data)
    geom=anchor_component_geometry(data['xy'],data['damage'],data['conn'],data['mass'])
    mapping=admit_coordinate_map(state,data,base,geom)
    control_path=control/'runs'/DIRECT_LOCKS[state]['run_id']
    admit_coordinate_control(state,control_path,data,backbone,base)
    if arm=='E021':
        path=control_path;model=build_relu_candidate(7,'localized',geom,backbone,mapping)
    else:
        assert arm=='E022'
        manifest=candidate.parent/'retrieval_verification.json'
        lock=json.loads((Path(__file__).resolve().parents[1]/'docs/research/S04/S04-E022/result_verification.json').read_text())
        assert sha256(manifest)==lock['retrieval_verification_sha256']
        verified=json.loads(manifest.read_text())
        assert verified['all_sha256_verified'] and verified['summary']['valid_completed_runs']==3
        matches=list((candidate/'runs').glob('*-'+state+'-localized-s7'));assert len(matches)==1
        path=matches[0];model=build_candidate(7,'localized',geom,backbone,mapping)
        assert sum(n.startswith('runs/'+path.name+'/') for n in verified['files'])==9
        for name,identity in verified['files'].items():
            if name.startswith('runs/'+path.name+'/'):
                p=candidate/name;assert p.stat().st_size==identity['bytes'] and sha256(p)==identity['sha256']
        receipt=json.loads((path/'RUN_RECEIPT.json').read_text())
        assert receipt['code_commit']==SCIENCE and receipt['dirty'] is False
        for name,h in receipt['archive_file_hashes'].items():assert sha256(path/name)==h
        assets=[json.loads((path/name).read_text()) for name in ('metrics.json','RUN_RECEIPT.json','PRE_UPDATE.json')]
        for asset in assets:validate_behavior_envelope(asset,state)
        record=assets[0];assert record['steps']==record['new_optimizer_steps']==10000
        check_pair_identity(state,geom,record['backbone_digest'],record['initial_residual_digest'],record['sampler_index_sha256'])
        for p in (path/'expected_learning_rates.npy',candidate/'preflight_learning_rates.npy',control_path/'learning_rates.npy'):
            np.testing.assert_array_equal(np.load(path/'learning_rates.npy',allow_pickle=False),np.load(p,allow_pickle=False))
    cp=torch.load(path/'final_step_10000.pt',map_location='cpu',weights_only=True)
    if arm=='E022':validate_behavior_envelope(cp,state)
    model.load_state_dict(cp['model_state_dict'],strict=True);validate_coordinate_buffers(model,mapping)
    if arm=='E022':validate_activation(model)
    assert state_digest(model.backbone)==CONTROL_LOCKS[state]['backbone_digest']
    for n in ('lower','upper','center','scale'):
        torch.testing.assert_close(getattr(model,n),torch.tensor(geom[n]),rtol=0,atol=0)
    with np.load(path/'prediction.npz') as f:saved=f['uv'].copy()
    np.testing.assert_allclose(predict_in_chunks(model,torch.tensor(data['xy'])).numpy(),saved,rtol=0,atol=1e-12)
    assert np.isfinite(saved).all()
    assets=dict(run_id=path.name,reference_sha256=data['reference_sha256'],checkpoint_sha256=sha256(path/'final_step_10000.pt'),prediction_sha256=sha256(path/'prediction.npz'),map=mapping,behavior='E021 relu(coeff*pre)' if arm=='E021' else 'E022 last-hidden leaky_relu(coeff*pre,.01)')
    rss();return model.eval(),data,base,saved,assets


def main():
    p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True);p.add_argument('--control',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--chunk',type=int,default=256);p.add_argument('--single',action='store_true');a=p.parse_args()
    assert 1<=a.chunk<=1024
    torch.set_default_dtype(torch.float64);torch.set_num_threads(2)
    a.out.mkdir(parents=True,exist_ok=False)
    pairs=[(s,arm) for s in ('c20s4','c60s4','c83s4') for arm in ('E021','E022')]
    if a.single:pairs=[('c20s4','E022')]
    results=[]
    for state,arm in pairs:
        model,data,base,saved,assets=load_endpoint(a.old,a.control,a.candidate,state,arm)
        result=measure(model,data,base,saved,a.chunk)
        expected=np.sqrt(np.sum(data['mass']/data['mass'].sum()*np.sum((saved-data['equilibrated_uv'])**2,axis=1))/abs(US)**2)
        np.testing.assert_allclose(result['full_rms'],expected,rtol=0,atol=1e-14)
        if arm=='E021':
            previous=a.control.parent.parent/'endpoint_diagnostic_v1/results'/f'{state}_E021.json'
            prior=json.loads(previous.read_text())
            for now,then in zip(result['head'],prior['head']):
                for key in ('loss_contribution','gradient_norm','scaled_normal_residual'):
                    if now[key] is None:assert then[key] is None
                    else:np.testing.assert_allclose(now[key],then[key],rtol=1e-10,atol=1e-14)
        result.update(state=state,arm=arm,assets=assets,activation_fraction_semantics='active_fraction = strictly positive output, not nonzero or derivative coverage')
        (a.out/f'{state}_{arm}.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');results.append(result)
        print(json.dumps(dict(state=state,arm=arm,full=result['full_rms'],head=result['head'][-1]['scaled_normal_residual'],peak_rss_bytes=rss())),flush=True)
        del model,data,base,saved;gc.collect()
    deps=[Path(__file__),Path(__file__).with_name('diagnose_s04_e021_endpoints.py'),Path(__file__).with_name('diagnose_s04_e020_features.py'),Path(__file__).with_name('s04_e022_screen.py')]
    meta=dict(protocol_revision=PROTOCOL,training=False,parameter_updates=0,optimizer_created=False,least_squares_fit=False,chunk=a.chunk,peak_rss_bytes=rss(),source_hashes={p.name:sha256(p) for p in deps},code_commit=subprocess.check_output(['git','-C',str(Path(__file__).resolve().parents[1]),'rev-parse','HEAD'],text=True).strip(),python=platform.python_version(),torch=str(torch.__version__),numpy=np.__version__,results=results)
    (a.out/'summary.json').write_text(json.dumps(meta,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
