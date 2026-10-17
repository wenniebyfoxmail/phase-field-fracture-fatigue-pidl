#!/usr/bin/env python3
"""Offline PBD evidence analysis: reads output plus SHA-bound local input NPZs.

No Torch, model import, optimization, history update, remote access or producer call.
Numerical references are independent conditional FEM peaks, never a repaired rollout.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import SymLogNorm

PREP = Path(__file__).resolve().parent
WORKTREE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929')
SOURCE_COMMIT = '2c7c5dc62415389da089ad522ec6c03ff33b1404'
ARMS = ['U_B0', 'head_U_actual', 'U_energy', 'U_supervised',
        'D_B0', 'direct_Q4', 'head_D_actual', 'D_energy', 'D_supervised',
        'original_joint_LBFGS']
COLORS = {'c1':'#0072B2','c20':'#D55E00'}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()

def js(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def dump(path, value):
    def conv(x):
        if isinstance(x, np.generic): return x.item()
        raise TypeError(type(x).__name__)
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=conv)+'\n')

def relative(a,b,w):
    den = float(np.sum(w*b*b)); err=float(np.sum(w*(a-b)**2))
    return float(np.sqrt(err/den)) if den>0 else None

def metric(ref,cand,w):
    diff=cand-ref; den=float(np.sum(w*ref*ref)); wp=w/w.sum()
    r=ref-float(np.sum(wp*ref)); c=cand-float(np.sum(wp*cand))
    cor_den=float(np.sqrt(np.sum(wp*r*r)*np.sum(wp*c*c)))
    return dict(absolute_L2=float(np.sqrt(np.sum(w*diff*diff))),
                reference_norm=float(np.sqrt(den)),
                relative_L2=float(np.sqrt(np.sum(w*diff*diff)/den)) if den>0 else None,
                correlation=float(np.sum(wp*r*c)/cor_den) if cor_den>0 else None,
                reference_integral=float(np.sum(w*ref)),candidate_integral=float(np.sum(w*cand)))

def independent_operator(worktree):
    path=worktree/'tools/s04_e011_analysis/run_multicycle_cross_replay.py'
    spec=importlib.util.spec_from_file_location('pbd_common_q4',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod,path

def checked_fields(path,n,observed):
    with np.load(path,allow_pickle=False) as z:
        out={k:np.asarray(z[k],dtype=np.float64).reshape(-1) for k in ['u','v','d']}
    for k,v in out.items():
        if v.shape!=(n,) or not np.isfinite(v).all(): raise ValueError(f'Invalid {path}:{k}')
    observed.append(dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path)))
    return out

def q4_fields(f, inp, op, geo):
    N,B,w,_=geo;c=inp['cells'];
    gu=op.grad(f['u'],c,B);gv=op.grad(f['v'],c,B);gd=op.grad(f['d'],c,B)
    raw=op.amor_raw(f['u'],f['v'],c,B);dgp=op.interp(f['d'],c,N)
    active=(1-dgp)**2*raw
    # Amor's nondegraded compressive volumetric term is separate from active.
    bulk=1/(3*(1-2*.3));compression=.5*bulk*np.minimum(gu[...,0]+gv[...,1],0)**2
    e_el=float(np.sum(w*(active+compression)))
    e_d=float(np.sum(w*inp['pidl_f_pre']*.375*(dgp+.0001*np.sum(gd*gd,axis=2))))
    history=op.interp(inp['pidl_hist_alpha_pre'],c,N)
    # Independent NumPy nodal derivatives; no retained Torch leaf gradients.
    mu=1/(2*(1+.3));exx=gu[...,0];eyy=gv[...,1];trace=exx+eyy
    shear=gu[...,1]+gv[...,0];g=(1-dgp)**2
    sx=g*(2*mu*((2*exx-eyy)/3)+bulk*np.maximum(trace,0))+bulk*np.minimum(trace,0)
    sy=g*(2*mu*((2*eyy-exx)/3)+bulk*np.maximum(trace,0))+bulk*np.minimum(trace,0)
    tau=g*mu*shear
    ux=np.einsum('eg,egj->ej',w*sx,B[:,:,0,:])+np.einsum('eg,egj->ej',w*tau,B[:,:,1,:])
    uy=np.einsum('eg,egj->ej',w*tau,B[:,:,0,:])+np.einsum('eg,egj->ej',w*sy,B[:,:,1,:])
    force_u=np.bincount(c.ravel(),weights=ux.ravel(),minlength=len(f['d']))
    force_v=np.bincount(c.ravel(),weights=uy.ravel(),minlength=len(f['d']))
    force_all=np.concatenate((force_u,force_v));force=force_all[inp['freeu'].astype(int)]
    local=-2*(1-dgp)*raw+.375*inp['pidl_f_pre']-16875*np.maximum(history-dgp,0)
    gd_cell=np.einsum('eg,gn->en',w*local,N)+np.einsum('eg,egk,egkj->ej',w*.000075*inp['pidl_f_pre'],gd,B)
    gd_nodal=np.bincount(c.ravel(),weights=gd_cell.ravel(),minlength=len(f['d']))
    projected=f['d']-np.clip(f['d']-gd_nodal,0,1)
    exact_bound=(f['d']==0)|(f['d']==1)
    pg_square=float(np.sum(projected*projected))
    e_hist=float(np.sum(w*.5*16875*np.maximum(history-dgp,0)**2))
    return dict(raw=raw,active=active,dgp=dgp,gu=gu,gv=gv,
                _nodal_force=force_all,_nodal_damage_gradient=gd_nodal,
                independent_free_u_l2=float(np.linalg.norm(force)),
                independent_box_projected_damage_l2=float(np.linalg.norm(projected)),
                exact_bound_node_fraction=float(np.mean(exact_bound)),
                exact_bound_projected_residual_squared_share=float(np.sum(projected[exact_bound]**2)/pg_square) if pg_square>0 else None,
                E_el=e_el,E_d=e_d,E_hist=e_hist,physical_energy=e_el+e_d+e_hist,
                d_min=float(f['d'].min()),d_max=float(f['d'].max()),
                negative_damage_node_fraction=float(np.mean(f['d']<0)),
                above_one_damage_node_fraction=float(np.mean(f['d']>1)),
                gp_healing_max=float(np.maximum(history-dgp,0).max()))

def plots_scalar(dest,states):
    fig,axs=plt.subplots(2,3,figsize=(15,9),layout='constrained')
    uarms=['U_B0','head_U_actual','U_energy','U_supervised']
    darms=['D_B0','direct_Q4','head_D_actual','D_energy','D_supervised']
    for state in states:
        cy=state['cycle'];color=COLORS[f'c{cy}'];rows=state['arms']
        def draw(ax,names,key,**kw):
            vals=[rows.get(k,{}).get(key,np.nan) for k in names]
            ax.plot(range(len(names)),[np.nan if v is None else v for v in vals],'o-',color=color,label=f'c{cy}',**kw)
            ax.set_xticks(range(len(names)),names,rotation=30,ha='right',fontsize=8)
        for ax,key in [(axs[0,0],'uv_mass_rel_L2'),(axs[0,1],'uv_H1_rel'),(axs[0,2],'free_u_l2')]:
            draw(ax,uarms,key);ax.set_yscale('log')
        draw(axs[1,0],darms,'physical_energy');axs[1,0].set_yscale('log')
        draw(axs[1,1],darms,'box_projected_damage_l2');axs[1,1].set_yscale('log')
        draw(axs[1,2],darms,'damage_target_mass_rel_L2');axs[1,2].set_yscale('log')
    for ax,title in zip(axs.ravel(),['U: mass-L2 to conditional FEM','U: Q4-H1 to conditional FEM','U: free displacement force L2',
                                   'D: own-history physical energy','D: box projected-gradient L2','D: mass-L2 to direct Q4 candidate']):
        ax.set_title(title,fontsize=10);ax.grid(alpha=.2);ax.legend(fontsize=8)
    axs[1,1].axhline(4e-6,color='.3',ls='--',lw=.8)
    fig.suptitle('PIDL fixed peak blocks | U frozen FEM d; D frozen FEM u/v, PIDL own lower/f | missing ≠ zero',fontsize=11)
    path=dest/'block_scalars.png';fig.savefig(path,dpi=170);plt.close(fig)
    path.with_suffix('.md').write_text('PIDL block metrics at two independent conditional accepted FEM peak references. U and D are different frozen-field problems. D uses PIDL own history, gamma=16875 and box bounds; it is not FEM reproduction (FEM gamma=421875 and hard nodal lower). Dashed D line is the declared direct-reference box-KKT screen, not a FEM certificate. Missing arms have gaps. Source and exact values: summary.json.\n')
    # Objective/energy diagnostics separated from field-quality axes.
    fig,axs=plt.subplots(1,3,figsize=(14,4),layout='constrained')
    for state in states:
        cy=state['cycle'];color=COLORS[f'c{cy}'];folder=Path(state['output_folder'])
        for arm,ax,key in [('original_joint_LBFGS',axs[0],'loss'),('U_energy',axs[1],'loss'),('D_energy',axs[2],'loss')]:
            p=folder/arm/'accepted.json'
            if p.exists():
                vals=js(p);opt=state['arms'].get(arm,{})
                x=[1]+[r['evaluations'] for r in vals];y=[opt.get('initial_loss',np.nan)]+[r[key] for r in vals]
                ax.plot(x,y,'o-',ms=3,color=color,label=f'c{cy}')
            elif arm=='original_joint_LBFGS':
                axs[0].annotate(f'c{cy}: original arm missing/skipped',(.03,.1+.1*(cy==20)),xycoords='axes fraction',fontsize=8)
    for ax,title in zip(axs,['Original joint logE + weight regularizer','U local physical E/E(B0)','D local physical E/E(B0)']):
        ax.set_title(title,fontsize=10);ax.set_xlabel('Objective evaluations (trials included)');ax.set_ylabel('Accepted objective');ax.grid(alpha=.2)
        if ax.lines:ax.legend(fontsize=8)
    path=dest/'accepted_objectives.png';fig.savefig(path,dpi=170);plt.close(fig)
    path.with_suffix('.md').write_text('Accepted objective values only; rejected/unfinished line-search trials are excluded. Original joint control is source-gated float32 and uses legacy unbounded damage. U/D local controls are float64 with different objectives, no regularizer, frozen fields and independent theta0 restarts. Vertical scales and objective values are not comparable across panels. Lower original loss does not imply physical feasibility or FEM proximity.\n')

def joint_field_maps(dest,state,inp,geo,fields,op):
    if 'original_joint_LBFGS' not in fields:return
    N,B,w,_=geo;cells=inp['cells'];polygons=inp['nodes'][cells]
    fem=state['_fem'];pred=fields['original_joint_LBFGS']
    refgp=q4_fields(fem,inp,op,geo);predgp=q4_fields(pred,inp,op,geo)
    quantities=[('horizontal u',op.interp(fem['u'],cells,N),op.interp(pred['u'],cells,N)),
                ('vertical v',op.interp(fem['v'],cells,N),op.interp(pred['v'],cells,N)),
                ('damage d',refgp['dgp'],predgp['dgp']),('active energy',refgp['active'],predgp['active'])]
    fig,axs=plt.subplots(4,3,figsize=(12,14.4),layout='constrained')
    for row,(label,r,c) in enumerate(quantities):
        r=np.sum(w*r,axis=1)/w.sum(1);c=np.sum(w*c,axis=1)/w.sum(1);err=c-r
        lo=min(float(r.min()),float(c.min()));hi=max(float(r.max()),float(c.max()),1e-15);lim=max(float(abs(err).max()),1e-15)
        for col,(values,title) in enumerate([(r,'converged FEM'),(c,'unchanged paired PIDL'),(err,'PIDL minus FEM')]):
            vmin,vmax=(lo,hi) if col<2 else (-lim,lim)
            norm=SymLogNorm(max(abs(vmin),abs(vmax))*1e-5,vmin=vmin,vmax=vmax)
            pc=PolyCollection(polygons,array=values,cmap='viridis' if col<2 else 'RdBu_r',norm=norm,edgecolors='none')
            ax=axs[row,col];ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_xlabel('native x');ax.set_ylabel('native y');ax.set_title(label+' | '+title,fontsize=9);fig.colorbar(pc,ax=ax,shrink=.75)
    fig.suptitle(f"c{state['cycle']}s4 | accepted FEM vs original paired joint PIDL; no combined-arm model",fontsize=11)
    path=dest/f"c{state['cycle']}_joint_fields.png";fig.savefig(path,dpi=160);plt.close(fig)
    path.with_suffix('.md').write_text('Full paired PIDL joint fields, unchanged by the original-control LBFGS (zero nonzero parameter updates), compared with the same-state accepted conditional FEM peak. Rows: horizontal u, vertical v, damage, active energy. Columns: FEM, PIDL, PIDL minus FEM. Each quantity has common FEM/PIDL limits and its own symmetric signed-error scale; different rows have different units/ranges. No damage clipping. GP/Jacobian-weighted Q4 cell means rendered, full GP metrics in summary. This is the original coupled PIDL baseline, unlike independent frozen-field U/D diagnostics. The FEM states are independent local restarts, not a continuous repaired trajectory; no physical teacher or evolution claim.\n')

def field_maps(dest,state,inp,geo,fields,op):
    cy=state['cycle'];N,B,w,_=geo;nodes=inp['nodes'];cells=inp['cells'];polygons=nodes[cells]
    reference=state['_fem']
    choices=[k for k in ['U_B0','head_U_actual','U_energy','U_supervised'] if k in fields]
    if choices:
        ref=q4_fields(reference,inp,op,geo)['active']
        cand=[q4_fields(fields[k],inp,op,geo)['active'] for k in choices]
        draw_maps(dest/f'c{cy}_U_active_maps.png',polygons,w,ref,cand,choices,
                  f'c{cy}s4 | conditional accepted FEM active reference / PIDL U block / signed difference',
                  'FEM reference (d frozen in U block)',
                  'Float64 common native-Q4/GP active energy, no clipping. GP-weighted cell means are rendered; metrics use full GP. All rows share reference/prediction limits; signed differences share one separate symmetric scale. Whole domain shown; symmetric-log colour mapping, linthresh=maxrange*1e-5. U is physical energy minimization or supervised fit at fixed FEM damage, not a coupled PIDL rollout.')
    if 'direct_Q4' in fields:
        target=fields['direct_Q4']['d'];ref=op.interp(target,cells,N)
        choices=[k for k in ['D_B0','head_D_actual','D_energy','D_supervised'] if k in fields]
        cand=[op.interp(fields[k]['d'],cells,N) for k in choices]
        closed=state['arms'].get('direct_Q4',{}).get('closed_box_KKT',False)
        label='conditional Q4 block reference' if closed else 'direct Q4 budget candidate (MISS)'
        if choices:
            draw_maps(dest/f'c{cy}_D_damage_maps.png',polygons,w,ref,cand,choices,
                       f'c{cy}s4 | {label} / Smooth-B0 PIDL / signed difference',label,
                       'Damage GP-weighted Q4 cell means; full domain, no clipping, shared reference/prediction limits across all rows, one separate symmetric signed-error scale. The target is direct box-Q4 damage under PIDL own predecessor damage/f and gamma=16875, frozen FEM u/v. It is NOT FEM damage and NOT FEM reproduction. Target closure status appears in title and summary. Same Smooth-B0 anchor and original UV boundary formula are preserved. Supervised fit is a constructive witness, not a physics-trained result.')

def draw_maps(path,polygons,w,ref,cands,names,title,ref_label,caption):
    fig,axs=plt.subplots(len(cands),3,figsize=(12,3.6*len(cands)),squeeze=False,layout='constrained')
    def cellmean(x):return np.sum(w*x,axis=1)/w.sum(1)
    r=cellmean(ref)
    rendered=[cellmean(c) for c in cands]
    shared_min=min(float(r.min()),*(float(c.min()) for c in rendered))
    shared_max=max(float(r.max()),*(float(c.max()) for c in rendered),1e-15)
    shared_error=max(*(float(np.abs(c-r).max()) for c in rendered),1e-15)
    for i,(cand,name) in enumerate(zip(cands,names)):
        c=rendered[i];err=c-r;vmin=shared_min;vmax=shared_max;lim=shared_error
        for j,(val,lab) in enumerate([(r,ref_label),(c,name),(err,name+' - reference')]):
            lo,hi=(vmin,vmax) if j<2 else (-lim,lim)
            # SymLog preserves signed errors without silently clipping rare hotspots.
            norm=SymLogNorm(max(abs(lo),abs(hi))*1e-5,vmin=lo,vmax=hi)
            pc=PolyCollection(polygons,array=val,cmap='viridis' if j<2 else 'RdBu_r',norm=norm,edgecolors='none')
            ax=axs[i,j];ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_xlabel('native x');ax.set_ylabel('native y');ax.set_title(lab,fontsize=9);fig.colorbar(pc,ax=ax,shrink=.75)
    fig.suptitle(title,fontsize=11);fig.savefig(path,dpi=160);plt.close(fig)
    path.with_suffix('.md').write_text(caption+'\nSource: summary.json; independent conditional c1/c20 peaks, no evolution claim. Rendered images require human visual QA before reporting.\n')

def inference(state):
    rows=state['arms'];notes=[]
    original=rows.get('original_joint_LBFGS')
    if original and state.get('original_objective_reproduction',{}).get('passed') and original.get('source_objective_pass'):
        drop=original['initial_loss']-original['final_loss']
        # Original float32 control must use its declared source qualification.
        floor=64*np.finfo(np.float32).eps*max(1,abs(original['initial_loss']))
        notes.append(dict(question='original_PIDL_stop',loss_drop=drop,readout_roundoff_floor=float(floor),
                          conclusion='same-original-objective descent available; optimizer/stop opportunity, not physical feasibility' if drop>floor else 'no robust original-objective descent demonstrated; stagnation versus representation remains unresolved'))
    else:notes.append(dict(question='original_PIDL_stop',conclusion='source-gated original arm missing/skipped; no original-objective optimizer claim'))
    for block,energy in [('U','E_el'),('D','physical_energy')]:
        arm=rows.get(block+'_energy');witnesses=[(name,rows[name]) for name in [f'head_{block}_actual',block+'_supervised'] if name in rows]
        if not arm:
            notes.append(dict(question=block+'_block',conclusion='energy endpoint missing; block inference pending'));continue
        better=[]
        for name,wit in witnesses:
            if not arm.get('independent_energy_consistent',False) or not wit.get('independent_energy_consistent',False):continue
            delta=arm[energy]-wit[energy]
            ai=arm['independent_float64_energy'][energy];wi=wit['independent_float64_energy'][energy]
            floor=abs(ai-arm[energy])+abs(wi-wit[energy])+128*np.finfo(float).eps*max(1,abs(arm[energy]),abs(wit[energy]))
            if delta>floor and ai-wi>floor:better.append(dict(witness=name,energy_advantage=float(delta),independent_energy_advantage=ai-wi,readout_error_floor=float(floor)))
        notes.append(dict(question=block+'_block',same_parameterization_lower_energy_witnesses=better,
                          conclusion='constructive same-parameterization lower local energy exists: optimization/conditioning opportunity remains' if better else 'no lower same-parameterization energy witness demonstrated; finite-budget fits do not establish a representation lower bound'))
    qc=rows.get('direct_Q4',{})
    notes.append(dict(question='D_reference',closed_box_KKT=qc.get('closed_box_KKT'),
                      conclusion='direct-Q4 is a qualified conditional PIDL-objective box block reference, not FEM reproduction' if qc.get('closed_box_KKT') else 'direct-Q4 did not provide a qualified closed box reference; damage ceiling remains unresolved'))
    return notes

def main(args):
    output=args.output.resolve();dest=args.dest.resolve();manifest_path=args.inputs_manifest.resolve()
    if not output.is_dir():raise FileNotFoundError(output)
    if dest==output or output in dest.parents:raise ValueError('Analysis destination must be outside immutable producer output')
    dest.mkdir(parents=True,exist_ok=False)
    manifest=js(manifest_path);op,op_path=independent_operator(args.worktree.resolve())
    sources=[dict(role='input_manifest',path=str(manifest_path),sha256=sha(manifest_path)),dict(role='offline_Q4_operator',path=str(op_path),sha256=sha(op_path))]
    observed=[];states=[]
    for item in manifest['cases']:
        cy=item['cycle'];case=output/f'c{cy}_s4'
        if not case.is_dir():continue
        p=Path(item['path']);assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
        sources.append(dict(role=f'bound_input_c{cy}',path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
        with np.load(p,allow_pickle=False) as z:inp={k:np.asarray(z[k]) for k in z.files}
        inp['nodes']=np.asarray(inp['nodes'],dtype=np.float64);inp['cells']=np.asarray(inp['cells'],dtype=np.int64)
        n=len(inp['nodes']);geo=op.q4_geometry(inp['nodes'],inp['cells']);N,B,w,_=geo
        fem={k:np.asarray(inp[k+'_fem'],dtype=np.float64) for k in ['u','v','d']}
        femgp=q4_fields(fem,inp,op,geo)
        fd=inp['freed'].astype(int);dd=fem['d'][fd];lower=inp['fem_pre_lower'][fd];rr=inp['rd_fem'][fd].copy()
        atlo=dd<=lower+1e-10;athi=dd>=1-1e-10
        rr[atlo]=np.minimum(rr[atlo],0);rr[athi]=np.maximum(rr[athi],0);rr[atlo&athi]=0
        native_d_norm=float(np.linalg.norm(rr))
        assert native_d_norm<=4e-6 and femgp['independent_free_u_l2']<1e-8

        state=dict(cycle=cy,substep=4,output_folder=str(case),fem_reference=item['fem'],fem_fixed_state_readout={k:femgp[k] for k in ['E_el','E_d','E_hist','physical_energy','independent_free_u_l2','independent_box_projected_damage_l2']},arms={},missing=[],claims=[],_fem=fem)
        state['fem_fixed_state_readout']['native_FEM_feasible_damage_l2']=native_d_norm
        state['fem_fixed_state_readout']['own_PIDL_box_damage_l2_is_different_problem']=True
        own_lower=inp['pidl_hist_alpha_pre'];own_gp=op.interp(own_lower,inp['cells'],N)
        state['incoming_objective_differences']=dict(PIDL_gamma=16875,FEM_gamma=421875,
            PIDL_lower_min=float(own_lower.min()),PIDL_lower_max=float(own_lower.max()),
            PIDL_lower_negative_nodes=int(np.sum(own_lower<0)),PIDL_lower_above_one_nodes=int(np.sum(own_lower>1)),
            PIDL_lower_GP_min=float(own_gp.min()),PIDL_lower_GP_max=float(own_gp.max()),
            PIDL_lower_GP_above_one_count=int(np.sum(own_gp>1)),
            hard_GP_no_healing_infeasible_with_box=bool(np.any(own_gp>1)),
            own_soft_penalty_unavoidable_lower_bound=float(.5*16875*np.sum(w*np.maximum(own_gp-1,0)**2)),
            lower_vs_FEM_pre_maxabs=float(np.max(np.abs(own_lower-inp['fem_pre_lower']))),
            PIDL_committed_f_min=float(inp['pidl_f_pre'].min()),PIDL_committed_f_max=float(inp['pidl_f_pre'].max()),
            FEM_accepted_trial_f_min=float(inp['fem_current_history234'][:,:,2].min()),FEM_accepted_trial_f_max=float(inp['fem_current_history234'][:,:,2].max()),
            f_maxabs_difference=float(np.max(np.abs(inp['pidl_f_pre']-inp['fem_current_history234'][:,:,2]))))

        for name in ['operator_contract','b0_contract','original_objective_reproduction']:
            if (case/(name+'.json')).exists():state[name]=js(case/(name+'.json'))
        b0=checked_fields(case/'b0_fields.npz',n,observed) if (case/'b0_fields.npz').exists() else None
        fields={}
        for arm in ARMS:
            reportpath=case/'result.json' if arm=='U_B0' else case/'initial_D.json' if arm=='D_B0' else case/arm/'result.json'
            if not reportpath.exists():state['missing'].append(arm);continue
            report=js(reportpath)
            accepted_path=case/arm/'accepted.json'
            if accepted_path.exists():
                accepted=js(accepted_path);report['accepted_endpoint_records']=len(accepted)
                report['nonzero_parameter_updates']=sum(x.get('param_delta_inf',0)>0 for x in accepted)
                observed.append(dict(path=str(accepted_path),bytes=accepted_path.stat().st_size,sha256=sha(accepted_path)))
            observed.append(dict(path=str(reportpath),bytes=reportpath.stat().st_size,sha256=sha(reportpath)))
            if arm=='U_B0':f=checked_fields(case/'fields.npz',n,observed)
            elif arm=='D_B0':
                if b0 is None:state['missing'].append(arm+':b0_fields');continue
                f=dict(u=fem['u'],v=fem['v'],d=b0['d'])
            elif arm=='direct_Q4':
                dp=case/arm/'accepted_damage.npy';dd=np.load(dp,allow_pickle=False).astype(np.float64).reshape(-1)
                assert dd.shape==(n,) and np.isfinite(dd).all()
                observed.append(dict(path=str(dp),bytes=dp.stat().st_size,sha256=sha(dp)))
                f=dict(u=fem['u'],v=fem['v'],d=dd)
            else:f=checked_fields(case/arm/'fields.npz',n,observed)
            fields[arm]=f;gp=q4_fields(f,inp,op,geo)
            for key in ['E_el','E_d','E_hist','physical_energy']:
                if key in report:report['independent_'+key+'_difference']=gp[key]-report[key]
            if arm=='D_B0' and (case/'direct_Q4/accepted_damage.npy').exists():
                target=np.load(case/'direct_Q4/accepted_damage.npy',allow_pickle=False).astype(float)
                mass=np.zeros(n)
                for j in range(4):np.add.at(mass,inp['cells'][:,j],np.sum(w*N[:,j],axis=1))
                report['damage_target_mass_rel_L2']=relative(f['d'],target,mass)
            report['independent_energy_consistent']=all(abs(gp[k]-report[k])<=1e-10*max(1,abs(report[k])) for k in ['E_el','E_d','E_hist'] if k in report)
            report['independent_residuals']={k:gp[k] for k in ['independent_free_u_l2','independent_box_projected_damage_l2']}
            for producer_key,independent_key in [('free_u_l2','independent_free_u_l2'),('box_projected_damage_l2','independent_box_projected_damage_l2')]:
                if producer_key in report:assert abs(report[producer_key]-gp[independent_key])<=1e-10, (cy,arm,producer_key)
            if arm=='direct_Q4':
                independently_closed=gp['independent_box_projected_damage_l2']<=4e-6 and gp['d_min']>=0 and gp['d_max']<=1
                assert independently_closed==report['closed_box_KKT'], 'Direct Q4 closure discrepancy'
                report['independently_closed_box_KKT']=independently_closed
            report['independent_float64_energy']={k:gp[k] for k in ['E_el','E_d','E_hist','physical_energy']}
            report['E_el_ratio_to_conditional_FEM']=gp['E_el']/femgp['E_el']
            ref_g=(1-femgp['dgp'])**2
            grad_error=np.sum((gp['gu']-femgp['gu'])**2+(gp['gv']-femgp['gv'])**2,axis=2)
            grad_reference=np.sum(femgp['gu']**2+femgp['gv']**2,axis=2)
            report['FEM_g_weighted_uv_gradient_rel_L2']=float(np.sqrt(np.sum(w*ref_g*grad_error)/np.sum(w*ref_g*grad_reference)))
            if arm in ['U_B0','head_U_actual','U_energy','U_supervised']:
                report['fixed_damage_elastic_energy_excess_relative']=(gp['E_el']-femgp['E_el'])/femgp['E_el']
                assert gp['E_el']>=femgp['E_el']-1e-10, 'Conditional FEM energy minimum contract'

            report['active_vs_conditional_FEM']=metric(femgp['active'],gp['active'],w)
            report['damage_vs_conditional_FEM']=metric(femgp['dgp'],gp['dgp'],w)
            report['independent_bounds_healing']={k:gp[k] for k in ['d_min','d_max','negative_damage_node_fraction','above_one_damage_node_fraction','gp_healing_max','exact_bound_node_fraction','exact_bound_projected_residual_squared_share']}
            # Same-objective witnesses are scored by producer metrics plus independent readout.
            state['arms'][arm]=report
        state['claims']=inference(state)
        joint_field_maps(dest,state,inp,geo,fields,op)
        field_maps(dest,state,inp,geo,fields,op)
        state.pop('_fem');states.append(state)
    plots_scalar(dest,states)
    receipt=js(output/'receipt.json') if (output/'receipt.json').exists() else None
    assert receipt and receipt.get('commit')==SOURCE_COMMIT, 'Unexpected producer commit'
    assert receipt.get('history_commits')==0 and receipt.get('rollout_steps')==0
    summary=dict(schema='S04-E011-PBD-offline-v1',expected_producer_commit=SOURCE_COMMIT,
                 actual_receipt=receipt,producer_commit_matches=bool(receipt and receipt.get('commit')==SOURCE_COMMIT),
                 complete=js(output/'complete.json') if (output/'complete.json').exists() else None,
                 failure=js(output/'failure.json') if (output/'failure.json').exists() else None,
                 source_files=sources,read_fields=observed,states=states,
                 missing_planned_states=[x for x in [1,20] if x not in [v['cycle'] for v in states]],
                 reference_boundary='Independent conditional accepted FEM c1/c20 peaks; not a coherent repaired trajectory or physical teacher',
                 D_objective_boundary='PIDL own prehistory/f, gamma=16875, box bounds + GP soft irreversibility; FEM gamma=421875 with hard nodal lower. D target is NOT FEM reproduction.',
                 limitation='Finite-budget failure to fit does not prove full-network representation impossibility. Frozen-head fit only characterizes frozen features. Supervised witnesses are constructive, not physics-only models.',
                 visual_QA='REQUIRED: generated images must be opened and independently inspected before report adoption')
    dump(dest/'summary.json',summary)
    for sidecar in dest.glob('*.md'):
        sidecar.write_text('# How to read `'+sidecar.with_suffix('.png').name+'`\n\n'+sidecar.read_text()+ '\nQuestion: distinguish PIDL local optimization opportunity from unresolved representation limits at converged FEM c1/c20 peaks.\nExact producer: '+SOURCE_COMMIT+'; run '+str(receipt)+'\nData provenance: '+str(dest/'summary.json')+' SHA256 '+sha(dest/'summary.json')+'; every input/field hash and exact state label is listed there.\nNumerical takeaways and limitations: '+json.dumps([dict(cycle=x['cycle'],claims=x['claims']) for x in states])+'\n')

    (dest/'README_analysis.md').write_text('Offline analysis: original joint control, U local blocks and D local blocks answer separate questions. See summary.json for source identities, source-gate skips, missing arms, accepted fields, costs and constructive witnesses. Original loss reduction proves only an available optimizer/stop opportunity under its original unbounded objective. Local block improvement is not a full joint or fatigue-evolution result. Direct-Q4 D uses PIDL own history and penalty, so never describe its target as reproducing FEM. Do not use failed finite-budget fits as architecture lower bounds.\n\nAll analysis reads immutable retrieved/output plus the exact SHA-bound local input NPZs listed in inputs_manifest.json. No training, history commit, solver call or model import. Figures have sidecars and require rendered visual QA.\n')
    print(json.dumps({'dest':str(dest),'states':len(states),'complete':summary['complete'] is not None,'failure':summary['failure']},ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True,help='retrieved output root containing c1_s4/c20_s4')
    ap.add_argument('--dest',type=Path,required=True,help='new separate analysis destination')
    ap.add_argument('--inputs-manifest',type=Path,required=True)
    ap.add_argument('--worktree',type=Path,default=WORKTREE)
    main(ap.parse_args())
