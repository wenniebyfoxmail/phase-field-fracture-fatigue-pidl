"""Saved-output analysis of four chart controls; no model/operator imports."""
from pathlib import Path
import argparse,csv,hashlib,json,time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import SymLogNorm


def main():
    start=time.monotonic();cpu=time.process_time();ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--native-run',type=Path);args=ap.parse_args();case=args.run;a=case/'retrieved_partial/archive';out=case/'analysis';out.mkdir(exist_ok=True)
    load=lambda p:json.loads(p.read_text());native=None if args.native_run is None else args.native_run/'retrieved_partial/archive'
    armroot=lambda arm:native if native is not None and arm.startswith('native_') else a
    arr=lambda arm,name:np.load(armroot(arm)/arm/(name+'.npy'),allow_pickle=False)
    if (a/'measurement_result.json').exists():
        result=load(a/'measurement_result.json')
        if result['status'] not in ['FOUR_ARM_COMPLETE_NO_OPTIMIZATION','FROZEN_PAIR_COMPLETE_NO_OPTIMIZATION']:raise ValueError('not complete control panel')
        if native is not None:
            old=load(args.native_run/'analysis/saved_analysis.json')
            if old['result']['status']!='PARTIAL_STOPPED_NO_RETRY' or [x['arm'] for x in old['result']['arms']]!=['native_constant','native_zero']:raise ValueError('unexpected old native source')
            if result['reused_native_run']!=args.native_run.name:raise ValueError('reused native run mismatch')
            if not np.array_equal(np.load(native/'free_dofs.npy'),np.load(a/'free_dofs.npy')):raise ValueError('cross-run free order mismatch')
            result=dict(result,new_frozen_arms=result['arms'],old_native_result=old['result'],arms=old['result']['arms']+result['arms'],combined_runs=[args.native_run.name,case.name])
    else:
        terminal=load(a/'measurement_terminal.json');failure=load(a/'worker_failure.json')
        if terminal['completed'] or failure['type']!='FileExistsError':raise ValueError('unsupported partial terminal; inspect rather than infer')
        available=[arm for arm in ['native_constant','native_zero','frozen_constant','frozen_zero'] if all((a/arm/(name+'.npy')).exists() for name in ['Qv','FD','difference','plus_q','minus_q'])]
        # Recover scalar reductions only from fully saved array sets, not a rerun.
        recovered=[]
        for arm in available:
            ss=load(a/(arm+'_source_solver.json'))
            recovered.append(dict(arm=arm,source_z_L2=float(np.linalg.norm(np.load(a/arm/'source_z.npy'))),
                source_defect_inf=ss['target_defect_inf'],source_physical_gradient_inf=ss['physical_gradient_inf'],recovered_after_recording_failure=True))
        result=dict(status='PARTIAL_STOPPED_NO_RETRY',failure=failure,terminal=terminal,arms=recovered,counts=terminal['counts'],scientific_elapsed_seconds=terminal['elapsed_seconds'],not_run=['frozen_constant','frozen_zero'])
    free=np.load(a/'free_dofs.npy',allow_pickle=False);arms=[x['arm'] for x in result['arms']]
    mesh=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_pbd_2c7c5dc_20261017T2110Z_probe/retrieved/root/inputs/c20_peak.npz')
    msh='c51bd3c121378d33c7d08aaf5f88f76b7decba4827c1e8d271bb8c6dec73ecd3'
    if hashlib.sha256(mesh.read_bytes()).hexdigest()!=msh:raise ValueError('geometry hash mismatch')
    z=np.load(mesh,allow_pickle=False);nodes=z['nodes'];cells=z['cells'];n=len(nodes)
    if not np.array_equal(free,z['freeu']):raise ValueError('free order mismatch')
    def norm(x):return float(np.sqrt(np.sum(x*x)))
    def nodal(v):
        full=np.zeros(2*n);full[free]=v;return np.sqrt(full[:n]**2+full[n:]**2)
    rows=[];spatial=[];fields={};forwards=[]
    for original in result['arms']:
        arm=original['arm'];Q=arr(arm,'Qv');fd=arr(arm,'FD');err=arr(arm,'difference')
        plus=arr(arm,'plus_q')[free];minus=arr(arm,'minus_q')[free]
        if not np.array_equal((plus-minus)/2e-6,fd) or not np.array_equal(Q-fd,err):raise ValueError('stored FD/difference mismatch')
        if not all(np.isfinite(v).all() for v in [Q,fd,err,plus,minus]):raise ValueError('nonfinite saved data')
        tol=1e-10+1e-4*max(norm(Q),norm(fd),np.finfo(float).tiny)
        row=dict(original);row.update(Qnorm=norm(Q),FDnorm=norm(fd),recomputed_error=norm(err),recomputed_ratio=norm(err)/tol,FD_passed=bool(norm(err)<=tol),original_tolerance=tol)
        source_trace=arr(arm,'source_trace');cross=np.zeros_like(source_trace,dtype=bool);side_est=[]
        for side in ['plus','minus']:
            info=load(armroot(arm)/(arm+'_'+side+'_forward.json'));solver=load(armroot(arm)/(arm+'_'+side+'_solver.json'))
            info.update(arm=arm,side=side,original_physical_g_inf=solver['physical_gradient_inf'],target_defect_inf=solver['target_defect_inf']);forwards.append(info)
            cross|=arr(arm,side+'_trace')!=source_trace
            side_est.append(info['linear_forward_upper_conditional_saved_R'])
        row['conditional_linear_FD_upper']=None if any(x is None for x in side_est) else sum(side_est)/2e-6
        row['conditional_linear_FD_upper_over_gate']=None if row['conditional_linear_FD_upper'] is None else row['conditional_linear_FD_upper']/tol
        row['full_forward_bound_trusted']=False;rows.append(row)
        mag=nodal(err);sq=mag**2;support=np.zeros(n,dtype=bool);support[cells[np.any(cross,axis=1)].ravel()]=True
        sp=dict(arm=arm,changed_GP=int(cross.sum()),changed_cells=int(np.any(cross,axis=1).sum()),source_zero_GP=int((source_trace==0).sum()),max_error_node=nodes[int(np.argmax(mag))].tolist(),max_error_node_value=float(mag.max()),top1percent_error_squared_share=float(np.sort(sq)[-int(np.ceil(.01*n)):].sum()/sq.sum()),cross_adjacent_error_squared_share=float(sq[support].sum()/sq.sum()))
        spatial.append(sp);fields[arm]=(Q,fd,err,mag)
    pairs=[]
    for label,x,y in [('native_target','native_constant','native_zero'),('frozen_target','frozen_constant','frozen_zero'),('constant_branch','native_constant','frozen_constant'),('zero_branch','native_zero','frozen_zero')]:
        if x not in fields or y not in fields:continue
        pairs.append(dict(comparison=label,x=x,y=y,Q_difference=norm(fields[x][0]-fields[y][0]),FD_difference=norm(fields[x][1]-fields[y][1]),error_vector_difference=norm(fields[x][2]-fields[y][2]),source_field_difference=norm((arr(x,'source_q')-arr(y,'source_q'))[free])))
    terms=[]
    for kind in ['constant','zero']:
        x='native_'+kind;y='frozen_'+kind
        if x not in fields or y not in fields:continue
        for name in ['Jv','Cv','KJv','BTKJv','U','head_response','H','factor']:
            xx=arr(x,name);yy=arr(y,name)
            if not np.isfinite(xx).all() or not np.isfinite(yy).all():raise ValueError('nonfinite derivative term')
            terms.append(dict(kind=kind,term=name,native_norm=norm(xx),frozen_norm=norm(yy),difference_norm=norm(xx-yy),native_relative_difference=norm(xx-yy)/max(norm(xx),np.finfo(float).tiny)))
    for name,items in [('derivative_terms',terms),('FD_metrics',rows),('spatial',spatial),('pair_differences',pairs),('forward_estimates',forwards)]:
        with (out/(name+'.csv')).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in items for k in row)),lineterminator='\n');writer.writeheader();writer.writerows(items)
    summary=dict(run_id=case.name,result=result,FD=rows,spatial=spatial,pair_differences=pairs,derivative_terms=terms,geometry_SHA256=msh,full_forward_bound_trusted=False,verdict=('Four controls from two immutable runs; derivative/branch observation only, unique mechanism unresolved without complete forward bound' if len(arms)==4 else 'Partial native pair only; full2x2 incomplete, frozen branches unavailable, unique mechanism unresolved without complete forward bound'),new_field_or_energy_evaluations=0,new_NN_AD_SVD_solve=0)
    (out/'saved_analysis.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    fig,ax=plt.subplots(figsize=(8.6,4.4),layout='constrained');colors=['#D55E00','#E69F00','#0072B2','#56B4E9'][:len(rows)];xs=np.arange(len(rows));ratios=[r['recomputed_ratio'] for r in rows]
    ax.bar(xs,ratios,color=colors);ax.axhline(1,color='#222222',linestyle='--',label='original FD threshold');ax.set_yscale('log');ax.set_xticks(np.arange(4),['Native\ng=g0','Native\ng=0 root','Frozen branch\ng=g0','Frozen branch\ng=0 root']);ax.set_ylabel('||Q - FD||2 / original tolerance');ax.set_title('c20 chart controls: derivative mismatch, not FEM/PIDL solution error');ax.legend()
    ax.set_xlim(-.6,3.6)
    for x in range(len(rows),4):ax.text(x,1.,'NOT RUN',ha='center',va='bottom',rotation=90,color='#666666')
    for x,y in zip(xs,ratios):ax.annotate(f'{y:.4g}×',(x,y),xytext=(0,4),textcoords='offset points',ha='center')
    fig.savefig(out/'FD_four_arm.png',dpi=170);plt.close(fig)
    values=[np.sqrt(np.mean(fields[arm][3][cells]**2,axis=1)) for arm in arms];vmax=max(v.max() for v in values)
    fig,axes=plt.subplots(2,2,figsize=(10.5,8),layout='constrained')
    for ax,arm,val in zip(axes.flat,arms,values):
        pc=PolyCollection(nodes[cells],array=val,cmap='viridis',edgecolors='none',linewidths=0,antialiaseds=False,norm=SymLogNorm(linthresh=1e-5,vmin=0,vmax=vmax));ax.add_collection(pc);ax.autoscale_view();ax.set_aspect('equal');ax.set_title(arm);ax.set_xlabel('x (model units)');ax.set_ylabel('y (model units)')
    for ax in list(axes.flat)[len(arms):]:
        ax.set_axis_off();ax.text(.5,.5,'Frozen branch: NOT RUN\nStopped after recording error',ha='center',va='center',transform=ax.transAxes)
    fig.colorbar(pc,ax=axes,label='Cell RMS of nodal |Q - FD|\nUV per scaled-hidden unit; shared symlog',shrink=.9);fig.savefig(out/'FD_four_arm_fields.png',dpi=170);plt.close(fig)
    provenance=f'Run {case.name}; native run {None if args.native_run is None else args.native_run.name}; native sourcefa9ce259 and new frozen source per verified run manifest, fixedc20s4/FEMdamage/sourcePIDLhistory/Phi/T0/UV/B0, seed173/h1e-6. Selected remote arrays retrieved with SHA/size checks; local mirror partial (three large shared Phi maps remain remote). Geometry SHA {msh}. Source/side fields/Q/FD/differences used without NN, AD, force, energy, tangent, SVD or solve. Native controls come from original partial R1; frozen controls, when present, come from the separately hash-verified completion run. Missing controls are labelled NOT RUN. These chart controls are not installed NN endpoints.'
    for stem,desc in [('FD_four_arm','Bars are original abs1e-10+rel1e-4 L2 gate ratios, not physical residual or FEM/PIDL error. Log y; threshold1 unchanged. A smaller bar is a more consistent derivative check, not a better solution.'),('FD_four_arm_fields','Common full-mesh symlog color scale; free-field error vectors placed into original u/v nodal slots with prescribed increments zero. Each Q4 shows RMS nodal vector magnitude; no smoothing or clipping. This visualization is not the scalar unweighted L2 test.')]:
        (out/(stem+'.md')).write_text('# '+stem+'\n\n## How to read\n\n'+desc+'\n\n## Data provenance\n\n'+provenance+'\n\n## Limitations\n\nComplete forward arithmetic/nonlinear root error is not certified. Even an FD pass is not a unique-cause, architecture-capacity, optimization, FEM qualification or physical validation result.\n')
    (out/'analysis_cost.json').write_text(json.dumps(dict(wall_seconds=time.monotonic()-start,CPU_seconds=time.process_time()-cpu,new_field_or_energy_evaluations=0,NN_AD_SVD_solve=0),indent=2)+'\n')
    print(json.dumps(dict(FD=rows,pairs=pairs,spatial=spatial),indent=2))
if __name__=='__main__':main()
