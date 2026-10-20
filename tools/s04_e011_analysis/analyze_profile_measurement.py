#!/usr/bin/env python3
"""Only saved vectors/sign labels: no energy, gradient, NN, FEM or solve."""
from pathlib import Path
import argparse,csv,hashlib,json,time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import SymLogNorm


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);args=ap.parse_args();run=args.run;out=run/'analysis';out.mkdir(exist_ok=True)
    start=time.monotonic();cpu=time.process_time();archive=run/'retrieved_partial/archive';audit=archive/'measurement_audit'
    load=lambda p:json.loads(p.read_text());dump=lambda p,z:p.write_text(json.dumps(z,indent=2,allow_nan=False)+'\n')
    def arr(e,name):
        ref=e['arrays'][name];p=audit/Path(ref['path']).name
        if hashlib.sha256(p.read_bytes()).hexdigest()!=ref['sha256']:raise ValueError('saved_array_hash_failure')
        return np.load(p,allow_pickle=False)
    events=[load(p) for p in sorted(audit.glob('*.json'))];source=next(e for e in events if e['event']=='source');pred=next(e for e in events if e['event']=='prediction')
    Q=arr(pred,'Qv');q0=arr(source,'q0');free=arr(source,'free_dofs');trace0=arr(source,'trace_sign')
    fields={};traces={};heads=[];comparisons={};deltas={}
    for e in events:
        if e['event']=='side_returned':
            d=e['data'];key=(d['arm'],d['label']);fields[key]=arr(e,'q_raw');traces[key]=arr(e,'trace_sign')
            heads.append({k:d.get(k) for k in ['arm','label','head_gradient_inf','realization_maxabs','rank','E','Ru','boundary_maxabs','rolled_back','source_unchanged']})
        if e['event']=='comparison':
            d=e['data'];key=(d['arm'],d['pair']);fd=arr(e,'FD');error=arr(e,'difference')
            if np.max(abs(Q-fd-error))>1e-14 or abs(float(np.linalg.norm(error))-d['error'])>1e-12:raise ValueError('saved_comparison_reduction_mismatch')
            comparisons[key]=(d,fd,error)
    # Exact frozen mesh geometry only. No q4 operator/gradient is constructed.
    mesh=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_pbd_2c7c5dc_20261017T2110Z_probe/retrieved/root/inputs/c20_peak.npz')
    expected='c51bd3c121378d33c7d08aaf5f88f76b7decba4827c1e8d271bb8c6dec73ecd3'
    if hashlib.sha256(mesh.read_bytes()).hexdigest()!=expected:raise ValueError('frozen_geometry_identity_mismatch')
    z=np.load(mesh);nodes=z['nodes'];cells=z['cells'];n=len(nodes)
    if not np.array_equal(free,z['freeu']):raise ValueError('free_order_mismatch')
    def nodal(v):
        full=np.zeros(2*n);full[free]=v;return np.sqrt(full[:n]**2+full[n:]**2)
    cross={};spatial=[];ab=[]
    for pair,plus,minus in [('h','plus_h','minus_h'),('half','plus_half','minus_half')]:
        fa=comparisons['A',pair][1];fb=comparisons['B',pair][1];gap=float(np.linalg.norm(fa-fb))
        ab.append(dict(pair=pair,FD_A_minus_B_L2=gap,over_Qnorm=gap/np.linalg.norm(Q),over_A_mismatch=gap/comparisons['A',pair][0]['error'],mismatch_cosine=float(np.dot(comparisons['A',pair][2],comparisons['B',pair][2])/(np.linalg.norm(comparisons['A',pair][2])*np.linalg.norm(comparisons['B',pair][2]))),same_side_trace_equal=bool(np.array_equal(traces['A',plus],traces['B',plus]) and np.array_equal(traces['A',minus],traces['B',minus]))))
        for arm in ['A','B']:
            mask=(traces[arm,plus]!=trace0)|(traces[arm,minus]!=trace0);cross[arm,pair]=mask
            support=np.zeros(n,dtype=bool);support[cells[np.any(mask,axis=1)].ravel()]=True
            error=nodal(comparisons[arm,pair][2]);sq=error**2;order=np.argsort(sq);band=np.abs(nodes[:,1])<=.01
            spatial.append(dict(arm=arm,pair=pair,trace_changed_GP=int(mask.sum()),total_GP=int(mask.size),trace_changed_cells=int(np.any(mask,axis=1).sum()),source_zero_GP=int((trace0==0).sum()),plus_zero_GP=int((traces[arm,plus]==0).sum()),minus_zero_GP=int((traces[arm,minus]==0).sum()),
                crossing_adjacent_nodes=int(support.sum()),crossing_adjacent_node_fraction=float(support.mean()),error_squared_share_crossing_adjacent_nodes=float(sq[support].sum()/sq.sum()),error_squared_share_y_abs_le_001=float(sq[band].sum()/sq.sum()),top1percent_nodes_error_squared_share=float(sq[order[-int(np.ceil(.01*n)):]].sum()/sq.sum()),max_error_node=nodes[int(np.argmax(sq))].tolist(),max_error_nodal=float(error.max())))
    repeat=dict(plus_maxabs=float(np.max(abs(fields['A','plus_h']-fields['A','plus_repeat']))),minus_maxabs=float(np.max(abs(fields['A','minus_h']-fields['A','minus_repeat']))),FD_difference_L2=float(np.linalg.norm(comparisons['A','h'][1]-comparisons['A','repeat'][1])))
    result=load(archive/'measurement_result.json')
    summary=dict(result=result,A_B=ab,spatial=spatial,heads=heads,repeat=repeat,error_half_over_h_A=comparisons['A','half'][0]['error']/comparisons['A','h'][0]['error'],error_half_over_h_B=comparisons['B','half'][0]['error']/comparisons['B','h'][0]['error'],
        source_mesh_SHA256=expected,field_evaluations=0,NN_or_AD_or_solve=0,all_saved_comparisons_recomputed=True)
    dump(out/'saved_analysis.json',summary)
    for name,rows in [('FD_metrics',[v[0] for v in comparisons.values()]),('A_B',ab),('spatial',spatial),('heads',heads)]:
        with (out/(name+'.csv')).open('w',newline='') as stream:
            w=csv.DictWriter(stream,fieldnames=list(dict.fromkeys(k for r in rows for k in r)),lineterminator='\n');w.writeheader();w.writerows(rows)
    polys=nodes[cells];fig,axes=plt.subplots(2,2,figsize=(10.5,8),layout='constrained');values=[]
    for arm,pair in [('A','h'),('B','h'),('A','half'),('B','half')]:values.append(np.sqrt(np.mean(nodal(comparisons[arm,pair][2])[cells]**2,axis=1)))
    vmax=max(v.max() for v in values)
    for ax,val,(arm,pair) in zip(axes.flat,values,[('A','h'),('B','h'),('A','half'),('B','half')]):
        pc=PolyCollection(polys,array=val,cmap='viridis',edgecolors='none',linewidths=0,antialiaseds=False,norm=SymLogNorm(linthresh=1e-5,vmin=0,vmax=vmax));ax.add_collection(pc);ax.autoscale_view();ax.set_aspect('equal');ax.set_title(f'{arm}: '+('actual NN profile' if arm=='A' else 'anchored chart field')+f'; {pair}');ax.set_xlabel('x (model units)');ax.set_ylabel('y (model units)')
    fig.colorbar(pc,ax=axes,label='Cell RMS of nodal |Qv - FD|\nUV response per scaled-hidden unit; shared symlog',shrink=.9);fig.savefig(out/'FD_mismatch_fields.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.3),layout='constrained')
    for ax,pair in zip(axes,['h','half']):
        val=cross['A',pair].sum(1);pc=PolyCollection(polys,array=val,cmap='viridis',edgecolors='none',linewidths=0,antialiaseds=False);pc.set_clim(0,4);ax.add_collection(pc);ax.autoscale_view();ax.set_aspect('equal');ax.set_title(f'Actual A {pair}: {int(val.sum())} changed GP');centers=polys[val>0].mean(axis=1);ax.scatter(centers[:,0],centers[:,1],s=65,facecolors='none',edgecolors='#D55E00',linewidths=1.1,label='rings locate changed cells');ax.legend(loc='lower right',fontsize=8);ax.set_xlabel('x (model units)');ax.set_ylabel('y (model units)')
    fig.colorbar(pc,ax=axes,label='GP sign changes vs source, union of + and -\nCount per Q4 cell (0-4)',ticks=[0,1,2,3,4]);fig.savefig(out/'trace_branch_changes.png',dpi=170);plt.close(fig)
    provenance=f'Data provenance: {run.name}; source049f1cae, original frozen c20s4/FEMdamage/UV/B0, seed173. All plotted arrays are hash-verified saved measurement_audit NPYs. Geometry {mesh} SHA {expected}. No fields, forces, gradients, energies, NN, AD or solves were recomputed. Remote full621entry manifest verification and partial-local retrieval are in retrieval_verification.json.'
    (out/'FD_mismatch_fields.md').write_text('''# Actual-profile and chart derivative mismatch fields

How to read: A is actual NN fresh-current-basis/head-closed profile. B is only the fixed-T0 anchored chart field family, not an actual NN endpoint. Rows show original h=1e-6 and h/2=5e-7. Original free-DOF Qv-FD is mapped back into u/v node slots with prescribed increments zero; each cell shows RMS nodal vector magnitude. One common symlog scale, linear below1e-5, full mesh; no clipping or smoothing. The scalar test remains unweighted free-field L2, not this cell visualization.

'''+provenance+'''

Limitation: two finite steps and one direction do not identify an infinitesimal derivative or unique cause. A/B agreement must use vector-gap values in A_B.csv, not similar error norms alone. This is derivative-response mismatch, not FEM/PIDL solution error or optimization improvement; no new solution was accepted.
''')
    (out/'trace_branch_changes.md').write_text('''# Existing native trace labels under actual A perturbations

How to read: each cell is the number of its four Gauss points whose saved sign differs from the source for either + or - perturbation. Left h=1e-6, right h/2=5e-7; identical0-4 scale and full spatial extent. Hollow orange rings locate tiny changed cells; their marker size does not represent physical support area. Trace labels were observed at already-computed native energy evaluations; no new strain evaluation was performed for this plot. Zero sign, when present, remains distinct.

'''+provenance+'''

Limitation: spatial overlap between branch changes and derivative mismatch is a diagnostic association, not proof of a unique causal term. Source has no exact-zero trace GP, but finite steps can still cross a branch. Counts describe GP support; energy relevance and derivative-error norms use different measures. No scan of extra steps or directions and no changed physical split is included.
''')
    dump(out/'analysis_cost.json',dict(wall_seconds=time.monotonic()-start,CPU_seconds=time.process_time()-cpu,field_or_energy_evaluations=0,NN_AD_SVD_solve=0))
    print(json.dumps({k:summary[k] for k in ['A_B','repeat','spatial','error_half_over_h_A','heads']},indent=2))
if __name__=='__main__':main()
