"""D008: fixed-plane weak and background UV nondegradation, offline only."""
import argparse,json,time,resource,platform,subprocess
from pathlib import Path
import numpy as np,torch
from threadpoolctl import threadpool_limits
from s04_e024_weak_guard import Mechanics
from s04_e024_background_guard import background_plane
from s04_e024_centered_trust_region import product
from s04_e023_head_scale import physical_features
from diagnose_s04_e023_terminal_head import scores,network_order,sha,read,write_csv,STATES
from diagnose_s04_e023_endpoints import load_endpoint
from s04_e024_head_tail import HEAD_LOCKS
from run_s04_e024_head_tail_screen import state_digest,US
from s04_e018_global_local import compact_window
from diagnose_s04_e023_physical import observables,compare


def run(a):
    source=Path(__file__).resolve().parents[1];commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip();assert commit==a.expected_commit
    torch.set_default_dtype(torch.float64);torch.set_num_threads(2);start=time.perf_counter();a.out.mkdir(parents=True,exist_ok=False)
    root=a.project/'local_archive/experiments';old=root/'S04-E019/producer_execution_v1/raw';e021=root/'S04-E021/producer_execution_v2/raw';e022=root/'S04-E022/producer_execution_v1/raw';e023=root/'S04-E023/producer_execution_v1/raw';prev=root/'S04-E024/weak_guard_v1'
    assert (prev/'results/receipt.json').read_bytes()==(source/'docs/research/S04/S04-E024/weak_guard_receipt.json').read_bytes()
    manifest=read(prev/'archive_manifest.json');metrics=[];physical=[];trials=[];audits=[];assets=[]
    for st in STATES:
        if time.perf_counter()-start>600:raise RuntimeError('wall budget')
        model,data,base,origin,asset=load_endpoint(old,e021,e022,e023,st,'E023');digest=state_digest(model)
        cp=e023/'runs'/HEAD_LOCKS[st]['run_id'];before={str(cp/n):sha(cp/n) for n in HEAD_LOCKS[st]['files']};inp=prev/'results'/f'{st}_weak_guard.npz';inputhash=sha(inp);assert inputhash==manifest['files'][str(inp.relative_to(prev))]['sha256']
        theta=np.vstack([model.residual.output_layer.weight.detach().numpy().T,model.residual.output_layer.bias.detach().numpy()[None,:]])
        with np.load(inp) as z:basis=z['basis'].copy();old_uv=z['uv'].copy();np.testing.assert_array_equal(theta,z['original_coefficients'])
        radius=.02*np.linalg.norm(theta)
        np.testing.assert_allclose(np.einsum('ijk,ljk->il',basis,basis),np.eye(2),rtol=0,atol=1e-12)
        mechanics=Mechanics(data['xy'],data['conn'],data['damage'],origin);force0=mechanics.force(origin);dual0=mechanics.dual(force0);f2=float(np.sum(dual0**2));assert np.isfinite(f2) and f2>0
        increments=np.stack([network_order(model,data['xy'],np.zeros_like(base),radius*e,1024)/abs(US) for e in basis])
        w=data['mass']/data['mass'].sum();error=(origin-data['equilibrated_uv'])/abs(US)
        background=data['damage']<=.1;assert background.any()
        with torch.no_grad():window=compact_window(torch.tensor(data['xy']),model.lower,model.upper).numpy()[:,0]
        wbi=w*(background&(window>0));wbi/=wbi.sum();bgi0=float(np.sum(wbi[:,None]*error**2));assert np.isfinite(bgi0) and bgi0>0
        wb=w*background;wb/=wb.sum();bg0=float(np.sum(wb[:,None]*error**2));assert np.isfinite(bg0) and bg0>0
        bg_q=np.einsum('n,ind,jnd->ij',wb,increments,increments)/bg0;bg_g=np.einsum('n,nd,ind->i',wb,error,increments)/bg0
        q=np.einsum('n,ind,jnd->ij',w,increments,increments);g=np.einsum('n,nd,ind->i',w,error,increments);obj0=float(np.sum(w[:,None]*error**2))
        columns=np.stack([mechanics.dual(mechanics.force(abs(US)*d,tangent=True)) for d in increments]);t=np.einsum('ind,jnd->ij',columns,columns)/f2;h=np.einsum('nd,ind->i',dual0,columns)/f2
        assert all(np.isfinite(v).all() for v in [q,g,h,t,basis,bg_q,bg_g]) and np.isfinite(obj0) and obj0>0
        z,solve=background_plane(q/obj0,g/obj0,h,t,bg_g,bg_q);accepted=False;factor=0.;chosen=theta.copy();uv=origin.copy()
        if solve['success'] and solve['feasible']:
            for backtrack in range(9):
                fraction=2.**(-backtrack);delta=radius*np.einsum('i,ijk->jk',fraction*z,basis);coef=theta+delta;candidate=network_order(model,data['xy'],base,coef,1024)
                actual=float(np.sum(mechanics.dual(mechanics.force(candidate))**2));uvobj=float(np.sum(w[:,None]*((candidate-data['equilibrated_uv'])/abs(US))**2));bgobj=float(np.sum(wb[:,None]*((candidate-data['equilibrated_uv'])/abs(US))**2));bgiobj=float(np.sum(wbi[:,None]*((candidate-data['equilibrated_uv'])/abs(US))**2));ratio=float(np.linalg.norm(coef-theta)/np.linalg.norm(theta))
                ok=bool(np.isfinite([actual,uvobj,bgobj,bgiobj,ratio]).all() and actual<=f2 and uvobj<=obj0 and bgobj<=bg0 and bgiobj<=bgi0 and ratio<=.02*(1+1e-12))
                trials.append(dict(state=st,backtrack=backtrack,factor=fraction,force_squared_ratio=actual/f2,uv_mse_ratio=uvobj/obj0,background_mse_ratio=bgobj/bg0,inside_background_mse_ratio=bgiobj/bgi0,delta_relative=ratio,accepted=ok))
                if ok:chosen=coef;uv=candidate;factor=fraction;accepted=True;break
        for arm,v in [('E023',origin),('D007',old_uv),('background_guard',uv)]:metrics.append(dict(state=st,arm=arm,**scores(v,data,window)))
        ref=observables(data,data['equilibrated_uv']);d=ref['gp_damage']>.1;gpdist=np.maximum(np.asarray(read(cp/'metrics.json')['geometry']['lower'])-ref['gp_xy'],ref['gp_xy']-np.asarray(read(cp/'metrics.json')['geometry']['upper']));masks=dict(full=np.ones_like(d),damage=d,background=~d,inside_background=(~d)&(gpdist<.02).all(2))
        for arm,v in [('E023',origin),('D007',old_uv),('background_guard',uv)]:
            ob=observables(data,v)
            for region,mask in masks.items():
                physical.append(dict(state=st,arm=arm,region=region,strain_error=compare(ob,ref,mask,'strain'),elastic_driver_error=compare(ob,ref,mask,'elastic_damage_driver'),active_energy_error=compare(ob,ref,mask,'active_energy'),rho_u=ob['rho_u']))
        final_bg=float(np.sum(wb[:,None]*((uv-data['equilibrated_uv'])/abs(US))**2));assert final_bg<=bg0*(1+1e-13)
        final_bgi=float(np.sum(wbi[:,None]*((uv-data['equilibrated_uv'])/abs(US))**2));assert final_bgi<=bgi0*(1+1e-13)
        affinity=origin+abs(US)*np.einsum('i,ind->nd',factor*z,increments) if accepted else origin.copy();affine_gap=float(np.max(abs(uv-affinity)));assert affine_gap<=1e-12
        actualforce=mechanics.force(uv);actratio=float(np.sum(mechanics.dual(actualforce)**2)/f2);assert actratio<=1+1e-13
        outside=float(abs(uv[window==0]-base[window==0]).max());assert outside==0;np.testing.assert_array_equal(uv[window==0],origin[window==0])
        branchchange=float(np.mean((mechanics.strains(uv)[...,:2].sum(2)>=0)!=mechanics.branches))
        audits.append(dict(state=st,**solve,dimension=2,accepted=accepted,accepted_fraction=factor,background_mse_ratio=final_bg/bg0,inside_background_mse_ratio=final_bgi/bgi0,affine_max_abs=affine_gap,delta_relative=float(np.linalg.norm(chosen-theta)/np.linalg.norm(theta)),actual_force_squared_ratio=actratio,branch_changed_gp_fraction=branchchange,outside_max_abs=outside,radius=radius))
        np.savez_compressed(a.out/f'{st}_background_guard.npz',uv=uv,head_coefficients=chosen,original_coefficients=theta,delta=chosen-theta,basis=basis,plane_z=z,accepted_fraction=factor)
        assert digest==state_digest(model) and all(p.grad is None for p in model.parameters());assert sha(inp)==inputhash and all(sha(Path(p))==v for p,v in before.items())
        assets.append(dict(**asset,original_file_hashes=before,direction_input_sha256=inputhash,model_digest=digest));peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
        if peak>3*1024**3:raise RuntimeError('RSS budget')
        print(st,audits[-1],flush=True);del model,mechanics
    for name,rows in [('uv_metrics.csv',metrics),('physical_metrics.csv',physical),('line_search.csv',trials),('numerics.csv',audits)]:
        if rows:write_csv(a.out/name,rows)
    if time.perf_counter()-start>600:raise RuntimeError('wall budget')
    (a.out/'receipt.json').write_text(json.dumps(dict(source_commit=commit,states=list(STATES),assets=assets,parameter_radius_fraction=.02,wall_seconds=time.perf_counter()-start,peak_rss_bytes=int(peak),offline_two_variable_solves=3,neural_optimizer_steps=0,history_fatigue_damage_updates=0,original_checkpoint_writes=0,remote_actions=0,scope='same frozen D007 plane; actual native-force/fullUV/backgroundUV guards; no fullhead or evolution qualification'),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-commit',required=True);a=p.parse_args()
    with threadpool_limits(limits=2):run(a)
