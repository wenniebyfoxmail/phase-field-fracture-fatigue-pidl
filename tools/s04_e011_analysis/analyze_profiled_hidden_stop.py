#!/usr/bin/env python3
"""Close the stopped c20 R2 from saved arrays only: four native field replays.
No NN, feature construction, SVD, tangent action, or equilibrium solve.
"""
from pathlib import Path
import argparse, hashlib, json, time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import SymLogNorm
from analyze_pidl_hidden_directions import Operator, dump, sha256, csvwrite

def array_sha(a):
    return hashlib.sha256(np.ascontiguousarray(a,dtype='<f8').tobytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);args=ap.parse_args()
    started=time.monotonic();cpu=time.process_time();r=args.run;out=r/'analysis';out.mkdir(exist_ok=True)
    receipt=json.loads((out/'UV_transfer_receipt.json').read_text());dm=json.loads((r/'dedup_map.json').read_text())
    source=Path(dm['6f10cb22d01ca243005c1a4c8541d4687e22c4214d863b3e771b23389a16fd57'])
    inp=Path(dm['c51bd3c121378d33c7d08aaf5f88f76b7decba4827c1e8d271bb8c6dec73ecd3'])
    for h,p in [('6f10cb22d01ca243005c1a4c8541d4687e22c4214d863b3e771b23389a16fd57',source),('c51bd3c121378d33c7d08aaf5f88f76b7decba4827c1e8d271bb8c6dec73ecd3',inp),(receipt['npz_sha256'],out/'failed_profile_uv_xor.npz')]:
        if sha256(p)!=h:raise ValueError('saved_input_hash_mismatch')
    z=np.load(source);xor=np.load(out/'failed_profile_uv_xor.npz');data=np.load(inp)
    uv={'source':{}}
    for component in ['u','v']:
        base=np.ascontiguousarray(z[component],dtype='<f8');uv['source'][component]=base
        for name in ['plus','minus']:
            uv.setdefault(name,{})[component]=np.bitwise_xor(base.view('<u8'),xor[name+'_'+component+'_xor']).view('<f8')
        for name in ['source','plus','minus']:
            if array_sha(uv[name][component])!=receipt['array_sha256'][name+'_'+component]:raise ValueError('lossless_array_reconstruction_failed')
    if not np.array_equal(z['d'],data['d_fem']):raise ValueError('fixed_FEM_damage_mismatch')
    op=Operator(data,cap=4,seconds=300);op.audit_out=out
    qs={'FEM':np.r_[data['u_fem'],data['v_fem']],**{k:np.r_[v['u'],v['v']] for k,v in uv.items()}}
    states={k:op.evaluate(q) for k,q in qs.items()};ref=states['FEM'];w=op.w
    def corr(a,b):
        ma=np.sum(w*a)/w.sum();mb=np.sum(w*b)/w.sum();aa=a-ma;bb=b-mb
        return float(np.sum(w*aa*bb)/np.sqrt(np.sum(w*aa*aa)*np.sum(w*bb*bb)))
    rows=[]
    for name,s in states.items():
        a=s['active'];row=dict(label=name,role='frozen_FEM_reference' if name=='FEM' else ('unchanged_PIDL_source' if name=='source' else 'unaccepted_finite_difference_trial'),E=s['E'],Ru=s['Ru'],active_integral=s['active_integral'],active_relL2=float(np.sqrt(np.sum(w*(a-ref['active'])**2)/np.sum(w*ref['active']**2))),active_corr=corr(a,ref['active']))
        if name!='FEM':
            label={'source':'profile_source_0','plus':'trial_1','minus':'trial_2'}[name]
            actual=json.loads((r/'retrieved_partial/archive/readouts'/f'{label}_actual.json').read_text())
            row.update(head_ginf=actual['reduced_gradient_inf'],UV_mass_relL2=actual['uv_mass_rel_L2'],UV_H1_rel=actual['uv_H1_rel'],E_replay_abs_error=abs(row['E']-actual['E_el']),Ru_replay_abs_error=abs(row['Ru']-actual['free_u_l2']))
            if row['E_replay_abs_error']>1e-12 or row['Ru_replay_abs_error']>1e-12:raise ValueError('independent_native_replay_mismatch')
        rows.append(row)
    csvwrite(out/'saved_fields.csv',rows)
    # Shared writer emits CRLF; keep derived tables portable and Git-clean.
    table=out/'saved_fields.csv';table.write_text(table.read_text())
    plus=qs['plus'];minus=qs['minus'];base=qs['source'];h=1e-6
    odd=.5*(plus-minus);even=.5*(plus+minus)-base;free=op.free
    def stats(v):return dict(free_L2=float(np.linalg.norm(v[free])),free_maxabs=float(np.max(np.abs(v[free]))),boundary_maxabs=float(np.max(np.abs(v[op.fixed]))))
    response=dict(h=h,odd_increment=stats(odd),even_increment=stats(even),actual_central_field_response=stats(odd/h),even_over_odd_free_L2=float(np.linalg.norm(even[free])/np.linalg.norm(odd[free])),predicted_Qv_saved=False,derivative_mismatch_norm_recoverable=False,interpretation='Actual saved finite-profile response only; one h cannot distinguish numerical sensitivity from nonlinear or chart effects.')
    dump(out/'saved_response.json',response)
    polygons=op.p[op.c]
    def maps(values,titles,path,signed=False,unit='model units',symlog=False):
        fig,axes=plt.subplots(1,len(values),figsize=(4.2*len(values),4.3),layout='constrained')
        axes=np.atleast_1d(axes);vmax=max(float(np.max(np.abs(a))) for a in values)
        for ax,values,title in zip(axes,values,titles):
            coll=PolyCollection(polygons,array=values,cmap='RdBu_r' if signed else 'viridis',edgecolors='none',linewidths=0,antialiaseds=False,rasterized=True)
            coll.set_clim(-vmax if signed else 0,vmax)
            if symlog:coll.set_norm(SymLogNorm(linthresh=1e-5,vmin=0,vmax=vmax))
            ax.add_collection(coll);ax.autoscale_view();ax.set_aspect('equal');ax.set_title(title,fontsize=10);ax.set_xlabel('x (model units)');ax.set_ylabel('y (model units)')
        fig.colorbar(coll,ax=axes,label=unit,shrink=.85);fig.savefig(path,dpi=170);plt.close(fig)
    avg=lambda a:np.sum(w*a,axis=1)/w.sum(1)
    maps([avg(ref['active']),avg(states['source']['active'])],['Frozen FEM c20s4 active','Unchanged PIDL c20s4 source active'],out/'baseline_active.png',unit='Active density (model units)\nsymlog; linear below 1e-5',symlog=True)
    magnitude=lambda q:np.sqrt(q[:op.n]**2+q[op.n:]**2)
    maps([np.mean(magnitude(odd)[op.c],axis=1),np.mean(magnitude(even)[op.c],axis=1)],['Actual odd UV increment: (q+ - q-)/2','Actual even UV increment: (q+ + q-)/2 - q0'],out/'finite_profile_response.png',unit='UV increment magnitude (model units; shared scale)')
    provenance=f"Run {r.name}; source network endpoint e2dc61d5 c20s4; frozen input {inp} SHA c51bd3c121378d33c7d08aaf5f88f76b7decba4827c1e8d271bb8c6dec73ecd3. Lossless XOR SHA {receipt['npz_sha256']}; every reconstructed UV array SHA checked. Script analyze_profiled_hidden_stop.py uses only four native Q4 2x2-GP field evaluations, with fixed FEM damage, no NN or solves. Exact source/trial file bindings are in UV_transfer_receipt.json."
    (out/'baseline_active.md').write_text(f"# Frozen c20 baseline active fields\n\nHow to read: FEM and unchanged PIDL source use the same full-mesh axes, weighted GP-to-cell mean and common colour limits and a shared symlog colour normalization (linear below 1e-5 model units). Model units; no clipping, smoothing, or selected crop. The unchanged PIDL source has weighted active relL2 {rows[1]['active_relL2']:.9g}, correlation {rows[1]['active_corr']:.9g}, versus the fixed FEM c20s4 reference. This visual describes the pre-existing gap.\n\nData provenance: {provenance}\n\nLimitation: no accepted hidden update was produced. The finite-profile derivative admission failed; this baseline picture is not evidence of improvement, capacity exhaustion, physical truth, or an evolution comparison. FEM and PIDL labels name the methods explicitly.\n")
    (out/'finite_profile_response.md').write_text(f"# Actual saved finite-profile UV response\n\nHow to read: left is odd finite UV increment, right is even component, both at h=1e-6 in one hidden direction. Nodal magnitudes are averaged per Q4 cell with identical spatial extent and common colour limits. Free-DOF L2 odd {response['odd_increment']['free_L2']:.9g}, even {response['even_increment']['free_L2']:.9g}; ratio {response['even_over_odd_free_L2']:.9g}. Shared scale preserves their actual relative size.\n\nData provenance: {provenance}\n\nLimitation: these are two unaccepted finite-difference trial fields, not optimized PIDL endpoints or a predicted-minus-observed derivative-error map. Predicted Qv and the failed error/scale were not saved before the stop, so no mismatch percentage can be recovered. Only one h/direction ran; even response alone cannot identify roundoff, dynamic-subspace effects, head closure, or local-chart mismatch.\n")
    result=dict(run_id=r.name,state='frozen_c20s4_peak_no_history_commit',scientific_status='PREFLIGHT_INCONCLUSIVE_NO_ACCEPTED_CANDIDATE',metrics=rows,response=response,field_evaluations=op.calls,tangent_actions=op.actions,parameter_updates=0,analysis_wall_seconds=time.monotonic()-started,analysis_CPU_seconds=time.process_time()-cpu,raw_source_sha256=sha256(source),input_sha256=sha256(inp),reconstructed_arrays_hash_verified=True,scope='Saved-array replay and visualization only; no NN/Phi/SVD/tangent or equilibrium solve')
    dump(out/'saved_analysis.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
