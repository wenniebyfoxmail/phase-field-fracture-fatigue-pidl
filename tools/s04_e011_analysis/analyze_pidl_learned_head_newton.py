#!/usr/bin/env python3
"""Offline c20s4 Newton UV-head correction on frozen learned PBD features.

Independent NumPy native-Q4 field/force replay only. No model loading, optimizer,
SSH, training, new parameter step, damage solve or history update occurs here.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from analyze_pidl_head_newton import (BASE, INPUTS, PBD, ROOT, ACTIVE_LOG_FLOOR,
    read_json, record, worker_output, fields, score, verify_four, finite_range, panel)
from analyze_pidl_hidden_newton import boundary_check
from analyze_pidl_block_diagnosis import independent_operator, q4_fields, dump, sha, metric

METHODS=['FEM','saved_PBD_before','learned_head_after']
LABELS=['conditional FEM','saved PBD before','Newton head after']
GTOL=1e-10
SCOPE=('FEM/PIDL c20s4 peak, U=.11999988, canonical native Q4/2x2 Gauss points, eta=0. '
       'Every mechanical field uses exact accepted conditional FEM damage and the original UV boundary. '
       'The PBD accepted network is the starting point; its learned hidden parameters remain fixed. '
       'A fresh full-401-column physical feature design is numerically SVD-resolved, without forcing the old original-feature rank387. '
       'This is one independent frozen-damage mechanical block, not a joint PIDL state, repaired fatigue trajectory, full-network capacity bound or physical teacher. '
       'RAW psi+ is a secondary diagnostic in fully degraded g(d)=0 regions and cannot certify the mechanically active field; ACTIVE g(d)psi+ remains separately reported.')


def json_source(path,role,sources):
    record(path,role,sources);return read_json(path)


def gradient_rows(folder,info,sources):
    path=folder/'gradient_readouts.json'
    rows=json_source(path,'before/final raw physical Eel parameter-gradient readouts',sources) if path.exists() else info.get('gradient_readouts',[])
    if not isinstance(rows,list):raise ValueError('Expected list of raw gradient readouts')
    complete=info.get('status')=='completed'
    required=['E_el','hidden_gradient_l2','hidden_gradient_inf','uv_head_gradient_l2','uv_head_gradient_inf',
              'conditioned_head_gradient_l2','conditioned_head_gradient_inf','free_u_l2','uv_mass_rel_L2','uv_H1_rel']
    for r in rows:
        if r.get('status')=='rejected_or_rolled_back':
            if info.get('rolled_back') is not True or r.get('retained_endpoint_is_before') is not True:
                raise ValueError('Rejected candidate gradient lacks explicit rollback metadata')
            continue
        if r.get('objective')!='raw_Eel' or r.get('status')!='verified':
            if complete:raise ValueError('Unverified/non-rawEel gradient in completed endpoint')
            continue
        for key in required:
            if key not in r or r[key] is None or not np.isfinite(r[key]) or r[key]<0:
                raise ValueError('Missing/nonfinite raw gradient field: '+str(r.get('label'))+':'+key)
    if complete:
        labels=[r.get('label') for r in rows]
        expected_final='final_retained_before' if info.get('rolled_back') else 'final'
        verified_labels=[r.get('label') for r in rows if r.get('status')=='verified']
        if 'before_PBD' not in verified_labels or expected_final not in verified_labels:
            raise ValueError('Completed endpoint lacks verified before/final retained gradient readouts')
    return rows


def endpoint(run,sources):
    folder=worker_output(run)/'c20_s4';p=folder/'result.json'
    if not p.exists():return folder,dict(status='missing',folder=str(folder))
    info=json_source(p,'learned-feature Newton result',sources)
    if info.get('status')!='completed' or info.get('actual_network') is None:
        return folder,dict(status=info.get('status','unknown'),folder=str(folder),worker=info,
                           excluded_reason='Actual terminal network unverified; any fields fallback is excluded from new-candidate scoring')
    if (info.get('cycle'),info.get('substep'),info.get('step'))!=(20,4,99):raise ValueError('Wrong state identity')
    for key in ['hidden_exactly_unchanged','damage_output_row_unchanged','Smooth_B0_anchor_unchanged','mechanical_damage_exact_FEM','boundary_unchanged']:
        if info.get(key) is not True:raise ValueError('Completed frozen contract missing/false: '+key)
    for key in ['history_commits','rollout_steps']:
        if info.get(key)!=0:raise ValueError('Unexpected '+key)
    if info.get('ridge')!=0.:raise ValueError('Ridge contract changed')
    before_hash=info.get('hidden_before_sha256');after_hash=info.get('hidden_after_sha256')
    if not isinstance(before_hash,str) or len(before_hash)!=64 or before_hash!=after_hash:
        raise ValueError('Frozen learned hidden parameter hashes absent or unequal')
    if info.get('hidden_updates')!=0:raise ValueError('Hidden parameters updated in frozen-feature diagnostic')
    if info.get('rolled_back') and info.get('accepted_head_updates')!=0:
        raise ValueError('Rolled-back endpoint cannot retain new accepted head updates')
    if not (folder/'fields.npz').exists():
        return folder,dict(status='fields_missing',folder=str(folder),worker=info)
    return folder,dict(status='completed',folder=str(folder),worker=info)


def decisions(state):
    metrics=state['metrics'];status=state['endpoint']
    if status.get('worker',{}).get('rolled_back') or status.get('worker',{}).get('hard_solver_failure'):
        return dict(retained_current_feature_span_closed=False,new_head_candidate_retained=False,rolled_back=True,
                    conclusion='Stopped or rolled back: verified PBD before is retained, not a new candidate. No new-head improvement or feature-floor claim.')
    if status['status']!='completed' or 'learned_head_after' not in metrics:
        return dict(retained_current_feature_span_closed=False,new_head_candidate_retained=False,conclusion='No verified new terminal network; partial/fallback fields are not an after result')
    info=status['worker'];actual=info['actual_network']
    a=actual.get('conditioned_head_gradient_inf',actual.get('reduced_gradient_inf'))
    c=info.get('conditioned_reduced_gradient_inf',info.get('conditioned_gradient_inf'))
    if a is None or not np.isfinite(a):raise ValueError('Actual installed projected-head gradient missing')
    if c is None or not np.isfinite(c):raise ValueError('Conditioned solver gradient missing')
    rolled_back=info.get('rolled_back') is True;hard=info.get('hard_solver_failure') is True
    closed=bool(a<=GTOL and not rolled_back and not hard);conditioned_closed=bool(c<=GTOL)
    if 'stationarity_closed' in info and bool(info['stationarity_closed'])!=closed:raise ValueError('Worker actual-gradient closure flag mismatch')
    before=metrics['saved_PBD_before'];after=metrics['learned_head_after']
    comparisons={}
    for key in ['E_el','free_u_l2','uv_mass_rel_L2','uv_H1_rel','raw_vs_FEM_relative_L2','active_vs_FEM_relative_L2']:
        comparisons[key]=dict(before=before[key],after=after[key],after_minus_before=after[key]-before[key])
    gain=before['E_el']-after['E_el']
    return dict(actual_installed_projected_head_gradient_inf=a,conditioned_solver_gradient_inf=c,target=GTOL,
        retained_current_feature_span_closed=closed,conditioned_closed=conditioned_closed,
        realization_limited=bool(conditioned_closed and not closed and not rolled_back),energy_decrease=gain,
        rolled_back=rolled_back,new_head_candidate_retained=not rolled_back,accepted_head_updates=info.get('accepted_head_updates'),
        energy_decrease_relative_to_saved_PBD=gain/before['E_el'],comparisons=comparisons,
        hidden_gradient_inf=actual.get('hidden_gradient_inf'),raw_UV_head_gradient_inf=actual.get('uv_head_gradient_inf'),
        global_free_force=after['free_u_l2'],actual_minus_conditioned_gradient_inf=info.get('actual_minus_conditioned_gradient_inf'),
        actual_minus_conditioned_energy=info.get('actual_minus_conditioned_energy'),linear_vs_actual_uv_maxabs=info.get('linear_vs_actual_uv_maxabs'),
        conclusion=('The solver retained the verified PBD before state after rollback; this is not a new head improvement.' if rolled_back else
                    'The actual installed UV head closes only the declared projected-gradient criterion in the numerically retained current learned-feature span.' if closed else
                    'The actual installed UV head does not close the declared projected-gradient criterion; finite-budget or numerical realization limits remain unresolved.')+
                    ' Hidden parameters are frozen but their raw Eel gradients may remain nonzero. Neither head closure nor lower elastic energy establishes whole-network stationarity, global nodal equilibrium, all field improvements, damage consistency or fatigue evolution.')


def save(fig,path,caption,provenance):
    fig.savefig(path,dpi=165);plt.close(fig)
    path.with_suffix('.md').write_text('# '+path.stem+'\n\n'+caption+'\n\n'
        '## Data provenance\n\n'+provenance+'\n\n'
        '## How to read\n\nPanel titles name FEM or PIDL and c20s4. Read the figure-specific caption above for quantities, axes and display transforms. '
        'FEM is the first reference; saved PBD is the actual before state, not an untrained network. '
        'Missing/partial endpoints are blank or absent and never scored as zero improvement.\n\n'
        '## Limitation\n\n'+SCOPE+' Raw network-parameter gradients are producer readouts in original parameter coordinates; '
        'conditioned head gradients and global nodal force belong to different spaces. Independent NumPy field replay does not independently differentiate neural-network parameters. '
        'All physical metrics use full float64 GP arrays and are unaffected by plotting transforms. Visual inspection remains required.\n')


def scalar_and_gradients(out,state,provenance):
    metrics=state['metrics'];rolled_back=bool(state['endpoint'].get('worker',{}).get('rolled_back') or state['endpoint'].get('worker',{}).get('hard_solver_failure'))
    fig,axs=plt.subplots(2,3,figsize=(13,7.8),layout='constrained')
    for ax,(key,title) in zip(axs.ravel(),[('elastic_excess_relative_FEM','Elastic energy excess / FEM'),('free_u_l2','Global free-u force L2'),
        ('uv_mass_rel_L2','Displacement mass relative L2'),('uv_H1_rel','Full Q4 gradient/H1 error'),
        ('raw_vs_FEM_relative_L2','RAW psi+ weighted relative L2'),('active_vs_FEM_relative_L2','ACTIVE g(d)psi+ weighted relative L2')]):
        values=[metrics.get(name,{}).get(key,np.nan) for name in METHODS]
        ax.plot(range(3),values,'o-',color='#0072B2');ax.set_xticks(range(3),['FEM','PBD before','Retained before' if rolled_back else 'Head after'],rotation=20,ha='right')
        ax.set_title(title,fontsize=10);ax.grid(alpha=.2)
    fig.suptitle('FEM/PIDL c20s4 peak | identical FEM damage, boundary and elastic-energy objective',fontsize=11)
    save(fig,out/'learned_head_decision.png','Six independent native-Q4 diagnostics for FEM, saved PBD before, and new actual UV-head endpoint. '
        'Raw psi+ and active g(d)psi+ are separate variables. Relative field norms use the FEM field norm, not percentages unless multiplied by100. '
        'Elastic energy, force, displacement mass/H1 error and raw/active spatial error need not improve together. All ordinates are linear; exact correlations and integrals are in summary.json/metrics.csv.',provenance)
    rows=[r for r in state.get('gradient_readouts',[]) if r.get('status')=='verified'];fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    labels=[r.get('label','unnamed') for r in rows]
    for ax,norm in zip(axs[0],['l2','inf']):
        for prefix,label,color in [('hidden','frozen hidden parameters','#0072B2'),('uv_head','raw UV-head parameters','#D55E00')]:
            if rows:ax.plot(range(len(rows)),[r[prefix+'_gradient_'+norm] for r in rows],'o-',color=color,label=label)
        if rows:ax.set_xticks(range(len(rows)),labels,rotation=20);ax.set_yscale('log');ax.legend(fontsize=8)
        else:ax.text(.5,.5,'NO VERIFIED GRADIENT READOUT',ha='center',transform=ax.transAxes)
        ax.set_title('Producer raw Eel parameter gradient '+('L2' if norm=='l2' else 'infinity norm'));ax.grid(alpha=.2)
    for ax,key,title in [(axs[1,0],'conditioned_head_gradient_inf','Actual installed projected-head gradient infinity'),
                         (axs[1,1],'free_u_l2','Global free-u nodal force L2')]:
        if rows:ax.plot(range(len(rows)),[r[key] for r in rows],'o-',color='#009E73');ax.set_xticks(range(len(rows)),labels,rotation=20);ax.set_yscale('log')
        else:ax.text(.5,.5,'NO VERIFIED READOUT',ha='center',transform=ax.transAxes)
        ax.set_title(title);ax.grid(alpha=.2)
    axs[1,0].axhline(GTOL,color='.4',ls='--',lw=.8)
    fig.suptitle('PIDL c20s4 before/final | raw Eel gradients: parameter / projected-head / nodal spaces kept separate',fontsize=10)
    save(fig,out/'learned_head_gradients.png','Before and final producer raw-Eel gradient readouts. Top: original-coordinate hidden and UV-head parameter norms. '
        'Bottom left: actual installed projected-head infinity norm with its declared1e-10 line; bottom right: global free nodal force with no such threshold. '
        'All gradient ordinates are logarithmic; exact zero values are in summary.json and cannot appear on log axes. '
        'Frozen hidden weights can have a nonzero physical-energy gradient; head closure does not mean whole-network convergence.',provenance)


def field_figures(out,inp,geo,op,physical,gp,provenance,rolled_back=False):
    N,_,w,_=geo;cells=inp['cells'];poly=inp['nodes'][cells];mean=lambda v:np.sum(w*v,axis=1)/w.sum(1)
    labels=LABELS.copy()
    if rolled_back:labels[2]='PBD retained after rollback'
    quantities=[('u','horizontal u'),('v','vertical v'),('raw','RAW psi+'),('active','ACTIVE g(d)psi+')]
    fig,axs=plt.subplots(4,3,figsize=(12.5,13.4),layout='constrained',squeeze=False)
    for row,(key,label) in enumerate(quantities):
        values={name:mean(gp[name][key] if key in ['raw','active'] else op.interp(f[key],cells,N)) for name,f in physical.items()}
        logged=key in ['raw','active']
        if logged:values={name:np.log10(np.maximum(v,ACTIVE_LOG_FLOOR)) for name,v in values.items()}
        lo,hi=finite_range(list(values.values()));pcs=[]
        for j,(name,title) in enumerate(zip(METHODS,labels)):
            ax=axs[row,j]
            if name not in values:
                ax.text(.5,.5,'STOPPED: PBD BEFORE RETAINED' if rolled_back and name=='learned_head_after' else 'NO VERIFIED ENDPOINT',ha='center',va='center',transform=ax.transAxes,fontsize=8);ax.set_axis_off();continue
            pcs.append(panel(ax,poly,values[name],title if row==0 else label,lo,hi))
        if pcs:
            cb=fig.colorbar(pcs[0],ax=axs[row,:].tolist(),shrink=.75,pad=.01);cb.set_ticks(np.linspace(lo,hi,5))
            cb.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f' if logged else '%.2e'));cb.set_label('log10 cell mean '+label if logged else label)
    fig.suptitle('FEM / PIDL c20s4 peak | saved PBD learned features frozen, new UV-head correction',fontsize=11)
    save(fig,out/'c20_learned_head_fields.png','FEM-first before/after full-domain maps of horizontal u, vertical v, RAW psi+ and ACTIVE g(d)psi+. '
        'Each row uses one shared range across all available methods. Displacement is linear physical cell mean. '
        'Raw and active fields are first GP/Jacobian averaged per Q4 cell and then shown as log10(max(cell mean,1e-12)), with no upper clipping. '
        'Raw and active are not interchangeable, and their physical full-GP metrics are unchanged.',provenance)
    fig,axs=plt.subplots(4,3,figsize=(12.5,13.4),layout='constrained',squeeze=False)
    after='PBD retained' if rolled_back else 'Head after'
    pairs=[('saved_PBD_before','FEM','PBD before - FEM'),('learned_head_after','FEM',after+' - FEM'),('learned_head_after','saved_PBD_before',after+' - before')]
    for row,(key,label) in enumerate(quantities):
        values={}
        for a,b,title in pairs:
            if a not in physical or b not in physical:continue
            delta=gp[a][key]-gp[b][key] if key in ['raw','active'] else op.interp(physical[a][key]-physical[b][key],cells,N)
            val=mean(delta)
            if key in ['raw','active']:val=np.sign(val)*np.log10(1+np.abs(val)/ACTIVE_LOG_FLOOR)
            values[title]=val
        lo,hi=finite_range(list(values.values()),signed=True);pcs=[]
        for j,(_,_,title) in enumerate(pairs):
            ax=axs[row,j]
            if title not in values:
                ax.text(.5,.5,'STOPPED: PBD BEFORE RETAINED' if rolled_back else 'NO VERIFIED ENDPOINT',ha='center',va='center',transform=ax.transAxes,fontsize=8);ax.set_axis_off();continue
            pcs.append(panel(ax,poly,values[title],title if row==0 else label+' difference',lo,hi,signed=True))
        if pcs:
            cb=fig.colorbar(pcs[0],ax=axs[row,:].tolist(),shrink=.75,pad=.01);cb.set_ticks(np.linspace(lo,hi,5))
            cb.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f' if key in ['raw','active'] else '%.2e'))
            cb.set_label('signed log10(1+|delta|/1e-12)' if key in ['raw','active'] else label+' signed physical error')
    fig.suptitle('PIDL c20s4 peak | before/after to FEM and after-minus-before | exact same FEM damage',fontsize=11)
    save(fig,out/'c20_learned_head_errors.png','Columns: saved PBD minus FEM, new actual head minus FEM, and head after minus saved PBD. '
        'Horizontal/vertical displacement differences use symmetric linear physical colour scales. '
        'RAW/ACTIVE differences are first physical GP-weighted cell-mean differences, then displayed as sign(delta)*log10(1+abs(delta)/1e-12), '
        'with the same fixed display floor and no upper clipping. Their colourbar labels are transformed dimensionless display coordinates, not physical-energy differences. '
        'Each quantity row shares one symmetric range across all three differences and five explicit numeric ticks; all physical scoring arrays remain unchanged.',provenance)


def analyze(run,out,inputs_manifest=INPUTS,pbd=PBD,render=True):
    if out.exists():raise FileExistsError('Refuse overwrite: '+str(out))
    out.mkdir(parents=True);sources=[];manifest=json_source(inputs_manifest,'input binding manifest',sources)
    item=next(x for x in manifest['cases'] if x['cycle']==20);path=Path(item['path'])
    if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise ValueError('Input size/SHA mismatch')
    record(path,'c20s4 conditional FEM and original PIDL inputs',sources);record(Path(__file__),'offline analyzer',sources)
    with np.load(path,allow_pickle=False) as z:inp={k:z[k] for k in z.files}
    op,oppath=independent_operator(ROOT);record(oppath,'independent native Q4 operator',sources)
    geo=op.q4_geometry(inp['nodes'],inp['cells']);N,B,w,_=geo;n=len(inp['nodes']);mass=np.zeros(n)
    for j in range(4):np.add.at(mass,inp['cells'][:,j],np.sum(w*N[:,j],axis=1))
    fem={k:inp[k+'_fem'].astype(float) for k in ['u','v','d']};ref=q4_fields(fem,inp,op,geo)
    native_error=float(np.max(np.abs(ref['_nodal_force']-inp['ru_fem'])))
    if native_error>1e-10 or ref['independent_free_u_l2']>1e-8:raise ValueError('FEM reference force contract mismatch')
    physical={'FEM':fem};saved=worker_output(pbd)/'c20_s4/U_energy/fields.npz'
    if not saved.exists():raise FileNotFoundError('The frozen saved-PBD before comparator is required: '+str(saved))
    physical['saved_PBD_before']=fields(saved,n,sources,'frozen saved PBD accepted before fields')
    folder,status=endpoint(run,sources);info=status.get('worker',{});before_readout=None;before_replay=None
    if (folder/'before/fields.npz').exists():
        before_replay=fields(folder/'before/fields.npz',n,sources,'fresh before PBD readout')
        maxerr=max(float(np.abs(before_replay[k]-physical['saved_PBD_before'][k]).max()) for k in ['u','v','d'])
        if maxerr>1e-12:raise ValueError('Fresh before readout does not reproduce saved PBD fields')
        before_path=folder/'before/result.json'
        if before_path.exists():before_readout=json_source(before_path,'fresh before raw Eel readout',sources)
    stopped=bool(info.get('rolled_back') or info.get('hard_solver_failure'))
    retained_fields=None
    if status['status']=='completed':
        visible=fields(folder/'fields.npz',n,sources,'verified visible terminal fields (retained before if stopped)')
        if stopped:retained_fields=visible
        else:physical['learned_head_after']=visible
    metrics={};gp={};rows=[];boundaries={};checks={}
    for name,f in physical.items():
        if not np.array_equal(f['d'],fem['d']):raise ValueError('FEM damage changed: '+name)
        boundaries[name]=boundary_check(f,fem,inp);r,q=score(f,fem,inp,op,geo,ref,mass)
        for key,value in metric(ref['raw'],q['raw'],w).items():r['raw_vs_FEM_'+key]=value
        r.update(cycle=20,substep=4,method=name,fixed_FEM_damage_exact=True);metrics[name]=r;gp[name]=q;rows.append(r)
    if before_readout is not None:
        checks['fresh_before']=verify_four(before_readout.get('actual_network',before_readout),metrics['saved_PBD_before'])
    if status['status']=='completed':
        if before_readout is None or before_replay is None:raise ValueError('Completed candidate lacks verified before fields/readout')
        if stopped:
            if retained_fields is None or not all(np.array_equal(retained_fields[k],before_replay[k]) for k in ['u','v','d']):
                raise ValueError('Stopped/rolled-back visible endpoint differs from verified before fields')
            checks['retained_before_terminal']=verify_four(info['actual_network'],metrics['saved_PBD_before'])
        else:checks['after']=verify_four(info['actual_network'],metrics['learned_head_after'])
    raw_rows=gradient_rows(folder,info,sources) if folder.is_dir() else []
    for row in raw_rows:
        name={'before_PBD':'saved_PBD_before','final':'learned_head_after','final_retained_before':'saved_PBD_before'}.get(row.get('label'))
        if row.get('status')=='verified' and name in metrics:checks['gradient_'+row['label']]=verify_four(row,metrics[name])
    basis=None
    if (folder/'basis.json').exists():basis=json_source(folder/'basis.json','current PBD full401 numerical SVD basis',sources)
    if status['status']=='completed':
        if basis is None or basis.get('original_columns')!=401:raise ValueError('Full401 current-feature basis metadata missing')
        if basis.get('rebuilt_from_current_PBD_hidden') is not True or basis.get('old_restricted_span_used') is not False:
            raise ValueError('Basis must rebuild all current PBD features rather than reuse old restricted span')
        rank=basis.get('retained_rank')
        if not isinstance(rank,int) or not 0<rank<=401:raise ValueError('Invalid dynamic retained numerical rank')
    state=dict(cycle=20,substep=4,step=99,load=.11999988,FEM_reference=item['fem'],endpoint=status,metrics=metrics,
        native_FEM_force_maxabs_error=native_error,boundary_checks=boundaries,independent_four_checks=checks,
        gradient_readouts=raw_rows,basis=basis,stopped_or_rolled_back=stopped,missing_methods=[m for m in METHODS if m not in metrics])
    state['decision']=decisions(state)
    scored_arrays=dict(nodes=inp['nodes'],cells=inp['cells'],GP_weights=w)
    for name,f in physical.items():
        for key in ['u','v','d']:scored_arrays[name+'_'+key]=f[key]
        for key in ['raw','active']:scored_arrays[name+'_'+key+'_gp']=gp[name][key]
    exact_path=out/'scored_fields_gp.npz';np.savez_compressed(exact_path,**scored_arrays)
    state['exact_scored_arrays']=dict(path=str(exact_path),bytes=exact_path.stat().st_size,sha256=sha(exact_path),
        semantics='Untransformed float64 native-GP raw/active and actual nodal u/v/d with canonical weights; display transforms are not stored here')
    if folder.is_dir():
        for name in ['accepted.json','trace.json']:
            if (folder/name).exists():state[name[:-5]]=json_source(folder/name,'producer '+name,sources)
    provenance=f'Current Run {run.name}; single prescribed FEM/PIDL c20s4 step99 peak. Saved PBD comparator {pbd.name}; bound FEM input {path}. Source hashes and physical full-GP values: summary.json and metrics.csv.'
    if render:scalar_and_gradients(out,state,provenance);field_figures(out,inp,geo,op,physical,gp,provenance,rolled_back=stopped)
    with (out/'metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result=dict(protocol='S04-E011-learned-head-Newton-offline-r1',run=str(run),state=state,sources=sources,claim_boundary=SCOPE)
    dump(out/'summary.json',result)
    (out/'README_analysis.md').write_text('# Frozen learned PBD features: Newton UV head, c20s4\n\n'+SCOPE+'\n\n'
        'Independent NumPy native-Q4 float64 replay computes Eel, global free-u nodal force, mass/H1 displacement errors, '
        'RAW psi+ and ACTIVE g(d)psi+ weighted L2/correlation/integrals. Exact FEM d and exported top/bottom boundary are checked. '
        'Fresh before fields must reproduce the saved accepted PBD comparator; partial/fallback and rolled-back fields are not scored as new after candidates. '
        'A stopped/rolled-back terminal before readout is verified separately against before, with no new candidate plotted. '
        'Producer before/final raw Eel parameter gradients are separated from the actual projected head gradient, conditioned solver gradient and global force. '
        'Only actual installed projected-head infinity-gradient <=1e-10 qualifies retained current-feature head closure; it does not qualify hidden/full-network stationarity. '
        'Numerical rank is determined from all401 current feature columns and is not forced to the old original-feature rank.\n\n'
        'Four figures: six scalar diagnostics, separate gradient spaces, FEM-first u/v/raw/active maps and signed before/after differences. '
        'UV maps/errors use linear physical scales. Raw/active maps use log10(max(GP-weighted cell mean,1e-12)); '
        'raw/active error maps use sign(delta)*log10(1+abs(delta)/1e-12), after physical cell-mean differencing, with no upper clipping. '
        'All metrics remain full-GP physical values; scored_fields_gp.npz preserves exact scoring arrays and weights with its SHA in summary. Each figure has standalone Data provenance / How to read / Limitation sidecar and needs visual review. '
        'No new experiments, optimizer reruns, SSH, damage solve or history commits occur in this analysis.\n')
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--dest',type=Path)
    ap.add_argument('--inputs-manifest',type=Path,default=INPUTS);ap.add_argument('--pbd-run',type=Path,default=PBD);a=ap.parse_args()
    dest=a.dest if a.dest else a.run/'analysis_learned_head_newton'
    result=analyze(a.run.resolve(),dest.resolve(),a.inputs_manifest.resolve(),a.pbd_run.resolve())
    print(json.dumps(dict(dest=str(dest),status=result['state']['endpoint']['status']),indent=2))


if __name__=='__main__':main()
