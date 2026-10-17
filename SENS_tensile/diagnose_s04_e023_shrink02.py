"""E024-D005: one fixed .2 scaling of saved D004 increment, no new fit."""
import argparse,json,time,resource,platform,subprocess
from pathlib import Path
import numpy as np,torch
from threadpoolctl import threadpool_limits
from diagnose_s04_e023_terminal_head import scores,network_order,sha,read,write_csv,STATES
from diagnose_s04_e023_endpoints import load_endpoint
from s04_e024_head_tail import HEAD_LOCKS
from run_s04_e024_head_tail_screen import state_digest,US
from s04_e018_global_local import compact_window
FACTOR=.2
PROTOCOL='20261017-r1-E024-D005-single-shrink02'


def run(a):
    source=Path(__file__).resolve().parents[1]
    commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip();assert commit==a.expected_commit
    start=time.perf_counter();torch.set_num_threads(2);torch.set_default_dtype(torch.float64)
    a.out.mkdir(parents=True,exist_ok=False)
    root=a.project/'local_archive/experiments';old=root/'S04-E019/producer_execution_v1/raw';e021=root/'S04-E021/producer_execution_v2/raw';e022=root/'S04-E022/producer_execution_v1/raw';e023=root/'S04-E023/producer_execution_v1/raw'
    previous=root/'S04-E024/centered_head_trust_region_v1'
    assert (previous/'results/receipt.json').read_bytes()==(source/'docs/research/S04/S04-E024/centered_head_receipt.json').read_bytes()
    prior=read(previous/'results/receipt.json');assert prior['diagnostic_code_commit']=='2c9ab039a3e4497125446d6065bad11593d21a93' and prior['states']==list(STATES) and prior['radius_fraction']==.1
    manifest=read(previous/'archive_manifest.json');metric=[];pairs=[];numerics=[];assets=[]
    for state in STATES:
        if time.perf_counter()-start>600:raise RuntimeError('wall budget')
        input_file=previous/'results'/f'{state}_trust_region.npz';identity=manifest['files'][str(input_file.relative_to(previous))]
        assert sha(input_file)==identity['sha256'] and input_file.stat().st_size==identity['bytes'];input_hash=sha(input_file)
        asset0=next(x for x in prior['assets'] if x['run_id']==HEAD_LOCKS[state]['run_id'])
        before=asset0['original_files_sha256_before'];assert all(sha(Path(p))==h for p,h in before.items())
        model,data,base,saved,asset=load_endpoint(old,e021,e022,e023,state,'E023');digest=state_digest(model)
        theta=np.vstack([model.residual.output_layer.weight.detach().numpy().T,model.residual.output_layer.bias.detach().numpy()[None,:]])
        with np.load(input_file,allow_pickle=False) as z:
            delta=z['delta'].copy();original=z['original_coefficients'].copy();previous_coef=z['head_coefficients'].copy();prior_uv=z['uv'].copy()
        np.testing.assert_array_equal(theta,original);np.testing.assert_array_equal(previous_coef-original,delta)
        assert np.isfinite(delta).all() and np.isfinite(prior_uv).all() and delta.shape==theta.shape and prior_uv.shape==saved.shape
        np.testing.assert_allclose(np.linalg.norm(delta)/np.linalg.norm(theta),.1,rtol=0,atol=1e-14)
        coef=theta+FACTOR*delta;realized=network_order(model,data['xy'],base,coef,1024)
        expected=saved+FACTOR*(prior_uv-saved);affine_gap=float(np.max(abs(realized-expected)));assert affine_gap<=1e-12
        ratio=float(np.linalg.norm(coef-theta)/np.linalg.norm(theta));assert abs(ratio-.02)<=1e-14
        with torch.no_grad():window=compact_window(torch.tensor(data['xy']),model.lower,model.upper).numpy()[:,0]
        outside=float(np.max(abs(realized[window==0]-base[window==0])));assert outside==0.
        values={name:scores(uv,data,window) for name,uv in [('E023',saved),('D004',prior_uv),('shrink02',realized)]}
        for name,v in values.items():metric.append(dict(state=state,arm=name,**v))
        for comp in ['E023','D004']:
            for region in values[comp]:pairs.append(dict(state=state,comparator=comp,region=region,baseline=values[comp][region],candidate=values['shrink02'][region],change_percent=100*(values['shrink02'][region]/values[comp][region]-1)))
        numerics.append(dict(state=state,factor=FACTOR,delta_relative=ratio,affine_max_physical_uv_difference=affine_gap,outside_max_physical_uv_difference=outside,model_digest_unchanged=digest==state_digest(model)))
        np.savez_compressed(a.out/f'{state}_shrink02.npz',uv=realized,head_coefficients=coef,delta=coef-theta,original_coefficients=theta)
        assert digest==state_digest(model) and all(p.grad is None for p in model.parameters())
        assert sha(input_file)==input_hash and all(sha(Path(p))==h for p,h in before.items())
        assets.append(dict(**asset,original_files_sha256=before,increment_input_sha256=input_hash,increment_input_path=str(input_file),model_digest_before=digest,model_digest_after=state_digest(model)))
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
        if peak>3*1024**3:raise RuntimeError('observed RSS budget')
        print(state,values['shrink02'],flush=True)
        del model
    for name,rows in [('regional_metrics.csv',metric),('paired_comparison.csv',pairs),('numerical_diagnostics.csv',numerics)]:write_csv(a.out/name,rows)
    if time.perf_counter()-start>600:raise RuntimeError('wall budget before receipt')
    receipt=dict(protocol=PROTOCOL,diagnostic_run_id='S04-E024-D005-R001-local-shrink02',source_commit=commit,runner_sha256=sha(Path(__file__).resolve()),previous_receipt_sha256=sha(previous/'results/receipt.json'),factor=FACTOR,states=list(STATES),assets=assets,wall_seconds=time.perf_counter()-start,peak_rss_bytes=int(peak),linear_fits=0,neural_optimizer_updates=0,original_checkpoint_writes=0,remote_actions=0,new_states_or_holdouts=0,application_tolerance_defined=False,legacy001_route_gate=False)
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-commit',required=True);a=p.parse_args()
    with threadpool_limits(limits=2):run(a)
