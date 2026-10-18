"""D006: native-Q4 physical observables of saved E023 and D005 fields; no updates."""
import argparse,csv,json,time,resource,platform,subprocess,sys
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from diagnose_s04_e023_terminal_head import sha,read,write_csv,STATES
from run_s04_e019_frozen_residual_screen import validate_reference,US,q4_strain,boundary_masks
from s04_e024_head_tail import HEAD_LOCKS
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/censor_projection_diagnostic'))
from weak_form import assemble


def observables(data,uv):
    strain=q4_strain(data['xy'],data['conn'],uv)
    weak=assemble(data['xy'],data['conn'],uv,data['damage'],young=1.,nu=.3,thickness=1.,eta=0.)
    gp_damage=np.einsum('en,gn->eg',data['damage'][data['conn']],weak['shape'])
    gp_xy=np.einsum('enb,gn->egb',data['xy'][data['conn']],weak['shape'])
    positive=weak['psi'];active=(1-gp_damage)**2*positive;driver=2*(1-gp_damage)*positive
    bottom,top=boundary_masks(data['xy']);free=~(bottom|top)
    scale=abs(US)/(np.sum(weak['det'])*abs(US)**2)
    rho=float(scale*np.sqrt(np.sum(weak['force'][free]**2/weak['mass'][free,None])))
    result=dict(strain=strain,psi0=positive,active_energy=active,elastic_damage_driver=driver,force=weak['force'],rho_u=rho,gp_damage=gp_damage,gp_xy=gp_xy,weights=weak['det'],mass=weak['mass'],free=free,rho_scale=scale)
    assert all(np.isfinite(v).all() for v in result.values())
    return result


def compare(candidate,reference,mask,key):
    w=reference['weights'][mask];a=candidate[key][mask];r=reference[key][mask]
    if a.ndim==2:w=w[:,None]
    numerator=float(np.sqrt(np.sum(w*(a-r)**2)));denominator=float(np.sqrt(np.sum(w*r*r)))
    assert denominator>0
    return numerator/denominator


def run(a):
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip();assert commit==a.expected_commit
    t=time.perf_counter();a.out.mkdir(parents=True,exist_ok=False)
    p=a.project/'local_archive/experiments';old=p/'S04-E019/producer_execution_v1/raw';e023=p/'S04-E023/producer_execution_v1/raw';prev=p/'S04-E024/centered_head_shrink02_v1'
    assert (prev/'results/receipt.json').read_bytes()==(ROOT/'docs/research/S04/S04-E024/shrink02_receipt.json').read_bytes()
    prior=read(prev/'results/receipt.json');manifest=read(prev/'archive_manifest.json');metrics=[];residuals=[];assets=[];locks=[]
    for state in STATES:
        if time.perf_counter()-t>600:raise RuntimeError('wall budget')
        raw=old/'inputs'/f'{state}.npz';data=validate_reference(state,raw)
        with np.load(raw) as z:
            frozen_optional={key:z[key].copy() for key in ['fatigue','prior_damage'] if key in z.files};active_after=z['active_after'].copy()
        frozen={key:value.copy() for key,value in frozen_optional.items()};frozen_damage=data['damage'].copy();input_file=prev/'results'/f'{state}_shrink02.npz'
        assert sha(input_file)==manifest['files'][str(input_file.relative_to(prev))]['sha256'];input_hash=sha(input_file)
        cpdir=e023/'runs'/HEAD_LOCKS[state]['run_id'];before={str(cpdir/n):sha(cpdir/n) for n in HEAD_LOCKS[state]['files']}
        assert all(before[str(cpdir/n)]==h for n,h in HEAD_LOCKS[state]['files'].items())
        with np.load(cpdir/'prediction.npz') as z:base=z['uv'].copy()
        with np.load(input_file) as z:corrected=z['uv'].copy()
        refs=observables(data,data['equilibrated_uv']);geom=read(cpdir/'metrics.json')['geometry'];dist=np.maximum(np.asarray(geom['lower'])-refs['gp_xy'],refs['gp_xy']-np.asarray(geom['upper']));inside=(dist<.02).all(axis=2)
        damage=refs['gp_damage']>.1;masks=dict(full=np.ones_like(damage,bool),damage=damage,background=~damage,inside_background=~damage&inside)
        assert np.max(abs(refs['strain']-data['strain_after']))<=5e-10
        assert np.allclose(refs['weights'],data['gp_weights'],rtol=1e-10,atol=1e-14)
        active_gap=float(np.max(abs(refs['active_energy']-active_after)))
        locks.append(dict(state=state,reference_rho_u=refs['rho_u'],reference_active_after_max_abs_gap=active_gap,reference_active_after_max_abs=float(np.max(abs(active_after)))))
        outputs={'FEM':refs}
        for arm,uv in [('E023',base),('shrink02',corrected)]:
            values=observables(data,uv);outputs[arm]=values
            for region,mask in masks.items():
                for key in ['strain','psi0','active_energy','elastic_damage_driver']:
                    error=compare(values,refs,mask,key)
                    mean=float(np.sum(refs['weights'][mask]*values[key][mask])/np.sum(refs['weights'][mask])) if key!='strain' else None
                    metrics.append(dict(state=state,arm=arm,region=region,quantity=key,relative_gp_l2_error=error,weighted_mean=mean))
            free=refs['free'];gap=refs['rho_scale']*np.sqrt(np.sum((values['force'][free]-refs['force'][free])**2/refs['mass'][free,None]))
            residuals.append(dict(state=state,arm=arm,rho_u=values['rho_u'],force_error_rho_scale=float(gap),reference_rho_u=refs['rho_u'],integrated_active_energy=float(np.sum(values['weights']*values['active_energy'])),trace_sign_mismatch_gp_fraction=float(np.sum(refs['weights']*((values['strain'][...,:2].sum(2)>=0)!=(refs['strain'][...,:2].sum(2)>=0)))/refs['weights'].sum())))
        np.savez_compressed(a.out/f'{state}_physical.npz',gp_xy=refs['gp_xy'],weights=refs['weights'],gp_damage=refs['gp_damage'],**{arm+'_'+key:vals[key] for arm,vals in outputs.items() for key in ['strain','psi0','active_energy','elastic_damage_driver']})
        assert all(np.array_equal(v,frozen[k]) for k,v in frozen_optional.items()) and np.array_equal(data['damage'],frozen_damage)
        assert sha(input_file)==input_hash and all(sha(Path(f))==h for f,h in before.items())
        assets.append(dict(state=state,reference_sha256=sha(raw),uv_input_sha256=input_hash,original_file_hashes=before,frozen_optional_sha256={k:__import__('hashlib').sha256(v.tobytes()).hexdigest() for k,v in frozen_optional.items()},max_history_present=False,frozen_channels_unchanged=True))
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
        if peak>3*1024**3:raise RuntimeError('RSS budget')
        print(state,'DONE',[(x['arm'],x['rho_u']) for x in residuals if x['state']==state],flush=True)
    for name,rows in [('physical_metrics.csv',metrics),('weak_residuals.csv',residuals),('reference_locks.csv',locks)]:write_csv(a.out/name,rows)
    if time.perf_counter()-t>600:raise RuntimeError('wall budget')
    (a.out/'receipt.json').write_text(json.dumps(dict(source_commit=commit,runner_sha256=sha(Path(__file__).resolve()),states=list(STATES),assets=assets,wall_seconds=time.perf_counter()-t,peak_rss_bytes=int(peak),training_updates=0,history_commits=0,fatigue_updates=0,damage_updates=0,remote_actions=0,driver_scope='instantaneous AMOR elastic conjugate 2(1-d)psi0; not net fracture/history/fatigue evolution driver'),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-commit',required=True);a=p.parse_args()
    with threadpool_limits(limits=2):run(a)
