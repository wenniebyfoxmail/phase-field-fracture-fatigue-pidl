#!/usr/bin/env python3
"""Offline c20s4 fixed-FEM-damage hidden/Newton mechanical-block comparison.

Imports NumPy Q4 replay, not a model/optimizer/producer. Partial fallback fields
are excluded. Raw Eel parameter gradients are producer readouts and are never
confused with a conditioned head gradient or a global nodal force.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from analyze_pidl_head_newton import (BASE, INPUTS, PBD, ROOT, ACTIVE_LOG_FLOOR,
    read_json, record, worker_output, fields, score, verify_four, endpoint,
    finite_range, panel)
from analyze_pidl_block_diagnosis import independent_operator, q4_fields, dump, sha

FIXED_NEWTON = BASE/'runs/pf_s04e011_uvnewton_2f3eddc_20261018T111147Z_production'
METHODS = ['FEM','original_theta0','PBD_full_network','fixed_feature_Newton','hidden_Newton']
LABELS = ['conditional FEM','original PIDL UV','PBD full-network L-BFGS','fixed-feature Newton','hidden + Newton']
SCOPE = ('c20s4 peak only, U=.11999988, canonical native Q4/2x2 Gauss integration, eta=0. '
         'Every mechanical candidate uses the exact same accepted conditional FEM damage and boundary. '
         'The FEM reference is an independent local restart, not a repaired fatigue trajectory or physical teacher. '
         'The new arm starts from the accepted fixed-feature Newton checkpoint; hidden features initially equal original theta0. '
         'Hidden-feature changes plus periodic UV-head corrections test a bounded local optimizer strategy; '
         'they do not prove whole-network expressivity, a joint damage/displacement solution or coupled evolution. '
         'Shared-hidden changes may alter the unused neural-network damage output even when the damage head and Smooth-B0 anchor parameters remain fixed; mechanical damage is exact FEM d.')


def json_source(path,role,sources):
    record(path,role,sources)
    return read_json(path)


def boundary_check(f,fem,inp):
    """Actual exported top/bottom boundary values; no reliance on a worker flag."""
    y=inp['nodes'][:,1];mask=(np.abs(y-y.min())<=1e-12)|(np.abs(y-y.max())<=1e-12)
    if not mask.any():raise ValueError('Boundary node set is empty')
    error=max(float(np.abs(f[k][mask]-fem[k][mask]).max()) for k in ['u','v'])
    if error>1e-12:raise ValueError('Exported displacement boundary changed: '+str(error))
    return dict(top_bottom_nodes=int(mask.sum()),FEM_boundary_maxabs=error,tolerance=1e-12,passed=True)


def new_endpoint(run,sources):
    folder=worker_output(run)/'c20_s4';path=folder/'result.json'
    if not path.exists():return None,dict(status='missing',folder=str(folder))
    info=json_source(path,'hidden/Newton worker result',sources)
    if info.get('status')!='completed' or info.get('actual_network') is None:
        return None,dict(status=info.get('status','unknown'),folder=str(folder),worker=info,
                         excluded_reason='No verified actual terminal network; fallback fields are not a new candidate')
    if info.get('cycle')!=20 or info.get('substep')!=4:raise ValueError('Hidden/Newton state mismatch')
    if not (folder/'fields.npz').exists():
        return None,dict(status='fields_missing',folder=str(folder),worker=info)
    for key in ['history_commits','rollout_steps']:
        if info.get(key)!=0:raise ValueError('Unexpected '+key)
    for key in ['damage_output_row_unchanged','Smooth_B0_anchor_unchanged','mechanical_damage_exact_FEM','boundary_unchanged']:
        if info.get(key) is not True:raise ValueError('Completed worker frozen contract missing/false: '+key)
    if info.get('fixed_raw_span_rank')!=387 or info.get('ridge')!=0.:
        raise ValueError('Completed worker changed retained span387/ridge contract')
    if info.get('NN_damage_field_fixed_claim') is not False:
        raise ValueError('Shared-hidden movement cannot certify fixed unused NN damage output')
    return folder,dict(status='completed',folder=str(folder),worker=info)


def gradient_readouts(folder,info,sources):
    """Exact raw-Eel parameter-gradient rows; final names follow worker schema."""
    path=folder/'gradient_readouts.json' if folder is not None else None
    if path is not None and path.exists():payload=json_source(path,'producer raw Eel parameter-gradient readouts',sources)
    else:payload=info.get('gradient_readouts',[])
    if isinstance(payload,dict):
        rows=[dict(label=k,**v) for k,v in payload.items()]
    elif isinstance(payload,list):rows=payload
    else:raise ValueError('Unknown raw gradient readout structure')
    completed=info.get('status')=='completed'
    required=['E_el','hidden_gradient_l2','hidden_gradient_inf','uv_head_gradient_l2','uv_head_gradient_inf',
              'raw_span_head_gradient_l2','raw_span_head_gradient_inf','free_u_l2']
    if completed and not rows:raise ValueError('Completed endpoint lacks required raw gradient readouts')
    for row in rows:
        if not isinstance(row.get('label'),str) or not row['label']:
            raise ValueError('Gradient readout label missing')
        if row.get('status')!='verified':
            if completed:raise ValueError('Completed endpoint contains unverified gradient row: '+row['label'])
            continue
        if row.get('objective') not in ['raw_Eel','E_el','raw_elastic_energy']:
            raise ValueError('Gradient objective not explicitly raw elastic energy')
        for key in required:
            if key not in row or not np.isfinite(row[key]) or row[key]<0:
                raise ValueError('Required finite nonnegative gradient readout missing/invalid: '+row['label']+':'+key)
        conditioned=['conditioned_head_gradient_l2','conditioned_head_gradient_inf']
        available=all(row.get(key) is not None for key in conditioned)
        if available:
            if any(not np.isfinite(row[key]) or row[key]<0 for key in conditioned):
                raise ValueError('Invalid conditioned gradient: '+row['label'])
        else:
            baseline=row['label'] in ['original_theta0','PBD_U_energy','fixed_feature_Newton']
            reason=row.get('conditioned_head_gradient_unavailable_reason')
            if not baseline or not isinstance(reason,str) or not reason:
                raise ValueError('Missing conditioned gradient without baseline-only unavailability reason: '+row['label'])
    if completed:
        labels=[row['label'] for row in rows]
        for name in ['original_theta0','PBD_U_energy','fixed_feature_Newton']:
            if not any(name in label for label in labels):raise ValueError('Baseline raw gradient readout missing: '+name)
        if not any(label=='final' or label.endswith('/final') or label.endswith('_final') for label in labels):
            raise ValueError('Final actual candidate raw gradient readout missing')
    return rows


def hidden_change_check(info):
    """Validate producer parameter-difference evidence; it is not a local training call."""
    evidence=info.get('hidden_change',{})
    before=evidence.get('before_sha256');after=evidence.get('after_sha256')
    changed=evidence.get('changed')
    if before is not None and after is not None:
        if len(before)!=64 or len(after)!=64:raise ValueError('Invalid hidden state digest')
        hash_changed=before!=after
        if changed is not None and bool(changed)!=hash_changed:raise ValueError('Hidden change flag/digest disagreement')
        changed=hash_changed
    maxabs=evidence.get('maxabs')
    if maxabs is not None:
        if not np.isfinite(maxabs) or maxabs<0:raise ValueError('Invalid hidden parameter delta')
        if changed is not None and bool(changed)!=(maxabs>0):raise ValueError('Hidden change flag/delta disagreement')
    return dict(producer_evidence=evidence,verified_from_digest_and_delta=bool(before and after and maxabs is not None),
                actual_hidden_changed=changed,
                limitation='Checks producer parameter digests/deltas; no Mac model training or hidden-parameter optimization')


def fixed_span_checks(folder,info,fixed,sources):
    path=worker_output(fixed)/'c20_s4/basis.npz'
    record(path,'original fixed retained raw-head span source',sources)
    with np.load(path,allow_pickle=False) as z:transform=np.asarray(z['transform'],dtype=np.float64)
    if transform.shape!=(401,387) or not np.isfinite(transform).all():raise ValueError('Invalid original raw span source')
    span=transform/np.linalg.norm(transform,axis=0)
    digest=hashlib.sha256(span.tobytes()).hexdigest()
    if info['fixed_raw_span_sha256']!=digest:raise ValueError('Retained raw span differs from qualified old Newton input')
    stages=[]
    for path in sorted(folder.glob('head_stage_*/basis.json')):
        row=json_source(path,'current hidden reconditioning full-span evidence',sources)
        if row.get('retained_rank')!=387 or row.get('further_rank_truncation') is not False or row.get('fixed_raw_span') is not True or row.get('ridge')!=0.:
            raise ValueError('Current head stage dropped directions or added ridge')
        stages.append(dict(path=str(path),retained_rank=row['retained_rank'],further_rank_truncation=False,ridge=0.))
    return dict(original_span_sha256=digest,rank=387,all_original_directions_preserved=True,head_stages=stages,
                current_final_conditioned_gradient_available=info['actual_network']['conditioned_head_gradient_inf'] is not None)


def conclusion(state):
    rows=state['metrics'];new=state['new_endpoint'];change=state.get('hidden_change',{})
    if 'hidden_Newton' not in rows:
        return dict(conclusion='No verified new actual endpoint; no gain or optimization/capacity conclusion')
    comparisons={}
    for name in ['original_theta0','PBD_full_network','fixed_feature_Newton']:
        if name in rows:
            e0=rows[name]['E_el'];e1=rows['hidden_Newton']['E_el']
            comparisons[name]=dict(elastic_energy_difference=e1-e0,relative_energy_reduction=1-e1/e0,
                uv_mass_error_difference=rows['hidden_Newton']['uv_mass_rel_L2']-rows[name]['uv_mass_rel_L2'],
                uv_H1_error_difference=rows['hidden_Newton']['uv_H1_rel']-rows[name]['uv_H1_rel'],
                global_free_force_difference=rows['hidden_Newton']['free_u_l2']-rows[name]['free_u_l2'],
                active_error_difference=rows['hidden_Newton']['active_vs_FEM_relative_L2']-rows[name]['active_vs_FEM_relative_L2'])
    fixed=rows.get('fixed_feature_Newton');gain=fixed['E_el']-rows['hidden_Newton']['E_el'] if fixed else None
    accessible=bool(gain is not None and gain>1e-10 and change.get('actual_hidden_changed') is True and change.get('verified_from_digest_and_delta'))
    return dict(comparisons=comparisons,actual_hidden_changed=change.get('actual_hidden_changed'),
        gain_over_fixed_feature_Newton=gain,predeclared_absolute_energy_margin=1e-10,
        accessible_hidden_feature_improvement=accessible,
        conclusion=('Same-energy local improvements, if independently resolved, show an available bounded optimizer/feature-update path. '
                    'A lower Eel does not imply all field errors or global force improved. Raw hidden/UV parameter gradients, '
                    'periodic conditioned-head gradients and global nodal force have different coordinate/physical meanings. '
                    'Neither a finite cap nor flat energy proves whole-network capacity limitation or convergence.'))


def save(fig,path,caption,provenance):
    fig.savefig(path,dpi=160);plt.close(fig)
    path.with_suffix('.md').write_text('# '+path.stem+'\n\n'+caption+'\n\n'
        '## Data provenance\n\n'+provenance+'\n\n'
        '## How to read\n\nRead the panel method/quantity labels and the figure-specific caption above. '
        'FEM and PIDL subjects are explicit. Missing/partial exports are excluded rather than plotted as zero gain. '
        'Exact values and source hashes are in summary.json and metrics.csv.\n\n'
        '## Limitation\n\n'+SCOPE+' Raw parameter gradients are producer raw-Eel readouts; '
        'independent NumPy Q4 energy/force/field metrics do not independently certify these parameter derivatives. '
        'Rendered figures require visual inspection before use in the report.\n')


def scalar_figure(out,state,provenance):
    rows=state['metrics'];fig,axs=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    keys=[('elastic_excess_relative_FEM','Elastic energy excess / conditional FEM'),('free_u_l2','Global free-u nodal force L2'),
          ('uv_mass_rel_L2','Displacement mass relative L2'),('uv_H1_rel','Q4 gradient/H1 relative error'),
          ('active_vs_FEM_relative_L2','Active weighted relative L2 / FEM'),('active_integral','Active integral')]
    for ax,(key,title) in zip(axs.ravel(),keys):
        vals=[rows.get(k,{}).get(key,np.nan) for k in METHODS]
        ax.plot(range(5),vals,'o-',color='#0072B2');ax.set_xticks(range(5),['FEM','theta0 UV','PBD full NN','Fixed Newton','Hidden+Newton'],rotation=25,ha='right',fontsize=8)
        ax.set_title(title,fontsize=10);ax.grid(alpha=.2)
    fig.suptitle('FEM / PIDL c20s4 peak | identical FEM damage, original displacement boundary and raw elastic energy',fontsize=11)
    save(fig,out/'hidden_newton_decision.png','Five methods in the same c20s4 fixed-damage mechanical problem. '
        'Energy, global nodal force, displacement mass/H1 errors and active field error are separate metrics. '
        'All ordinates are linear; exact small FEM force is in metrics.csv. A better energy does not imply every field is better.',provenance)


def gradient_figure(out,state,provenance):
    rows=[r for r in state.get('gradient_readouts',[]) if r.get('status')=='verified']
    fig,axs=plt.subplots(2,2,figsize=(max(14.,.75*len(rows)),9),layout='constrained')
    labels=[str(r.get('label',r.get('role','unnamed'))) for r in rows]
    for ax,norm in zip(axs[0],['l2','inf']):
        for prefix,title,color,marker in [('hidden','hidden parameters','#0072B2','o'),('uv_head','raw UV-head parameters','#D55E00','s')]:
            vals=[r.get(prefix+'_gradient_'+norm,np.nan) for r in rows]
            if vals:ax.plot(range(len(vals)),vals,marker+'-',color=color,label=title)
        if rows:
            ax.set_xticks(range(len(rows)),labels,rotation=30,ha='right',fontsize=8);ax.set_yscale('log');ax.legend(fontsize=8)
        else:ax.text(.5,.5,'NO VERIFIED RAW PARAMETER-GRADIENT READOUT',ha='center',va='center',transform=ax.transAxes,fontsize=8)
        ax.set_title('Producer raw Eel parameter gradient '+('L2' if norm=='l2' else 'infinity norm'));ax.grid(alpha=.2)
    for ax,key,title in [(axs[1,0],'conditioned_head_gradient_inf','Current mass-conditioned projected-head gradient infinity'),
                         (axs[1,1],'free_u_l2','Global free-u nodal force L2 (different space)')]:
        vals=[np.nan if r.get(key) is None else r[key] for r in rows]
        if rows:
            ax.plot(range(len(rows)),vals,'o-',color='#009E73')
            if key=='conditioned_head_gradient_inf':
                for i,r in enumerate(rows):
                    if r.get(key) is None:ax.annotate('unavailable: baseline rank',xy=(i,.1),xycoords=('data','axes fraction'),rotation=90,ha='center',fontsize=7)
            ax.set_xticks(range(len(rows)),labels,rotation=30,ha='right',fontsize=8);ax.set_yscale('log')
        else:ax.text(.5,.5,'NO VERIFIED READOUT',ha='center',transform=ax.transAxes)
        ax.set_title(title,fontsize=10);ax.grid(alpha=.2)
    fig.suptitle('PIDL c20s4 | raw physical Eel | parameter / conditioned / nodal spaces kept separate',fontsize=11)
    save(fig,out/'hidden_newton_parameter_gradients.png','Raw physical Eel derivatives in original network parameter coordinates, separated into hidden and UV output parameters. '
        'Logarithmic ordinate; zero entries cannot be displayed and their exact values remain in summary.json. '
        'Bottom left shows the current mass-conditioned projected-head gradient; bottom right is global nodal force. '
        'They are separate coordinate/physical spaces, so compare only like quantities across labels, never their magnitudes across panels. '
        'A parameter-gradient L2/inf ratio across parameter groups is not a causal contribution. Baselines and checkpoints are named by their actual readout labels. '
        'A baseline whose current retained span is numerically rank deficient has its conditioned-gradient panel explicitly marked unavailable with a reason; raw parameter gradients remain valid.',provenance)


def field_figures(out,inp,geo,op,physical,gp,provenance):
    N,_,w,_=geo;c=inp['cells'];poly=inp['nodes'][c];mean=lambda x:np.sum(w*x,axis=1)/w.sum(1)
    fig,axs=plt.subplots(3,5,figsize=(18,10),layout='constrained',squeeze=False)
    for row,(key,title) in enumerate([('u','horizontal u'),('v','vertical v'),('active','log10(active cell mean)')]):
        values={name:mean(gp[name]['active'] if key=='active' else op.interp(f[key],c,N)) for name,f in physical.items()}
        if key=='active':values={name:np.log10(np.maximum(x,ACTIVE_LOG_FLOOR)) for name,x in values.items()}
        lo,hi=finite_range(list(values.values()));pcs=[]
        for j,(name,label) in enumerate(zip(METHODS,LABELS)):
            ax=axs[row,j]
            if name not in values:
                ax.text(.5,.5,'NO VERIFIED ENDPOINT',ha='center',va='center',transform=ax.transAxes,fontsize=8);ax.set_axis_off();continue
            pcs.append(panel(ax,poly,values[name],label if row==0 else title,lo,hi))
        if pcs:
            cb=fig.colorbar(pcs[0],ax=axs[row,:].tolist(),shrink=.75,pad=.01);cb.set_ticks(np.linspace(lo,hi,5))
            cb.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f' if key=='active' else '%.2e'));cb.set_label(title)
    fig.suptitle('FEM-first / PIDL c20s4 mechanical fields | fixed FEM d | u/v linear, active log10 cell mean',fontsize=11)
    save(fig,out/'c20_hidden_newton_fields.png','Full-domain FEM-first u/v/active comparison. One common colour scale per quantity row across all methods. '
        'Displacements use linear colour scales. Active is GP/Jacobian-weighted Q4 cell mean, then log10(max(mean,1e-12)), no upper clipping; '
        'full-GP numerical metrics are unchanged. These are conditional mechanical hybrids, not full joint PIDL solutions.',provenance)
    fig,axs=plt.subplots(3,4,figsize=(16,10),layout='constrained',squeeze=False)
    for row,(key,title) in enumerate([('u','u error'),('v','v error'),('active','active energy error')]):
        values={}
        for name,f in physical.items():
            if name=='FEM':continue
            delta=gp[name]['active']-gp['FEM']['active'] if key=='active' else op.interp(f[key]-physical['FEM'][key],c,N)
            values[name]=mean(delta)
        lo,hi=finite_range(list(values.values()),signed=True);pcs=[]
        for j,(name,label) in enumerate(zip(METHODS[1:],LABELS[1:])):
            ax=axs[row,j]
            if name not in values:
                ax.text(.5,.5,'NO VERIFIED ENDPOINT',ha='center',va='center',transform=ax.transAxes,fontsize=8);ax.set_axis_off();continue
            pcs.append(panel(ax,poly,values[name],label+' minus FEM',lo,hi,signed=True))
        if pcs:
            cb=fig.colorbar(pcs[0],ax=axs[row,:].tolist(),shrink=.75,pad=.01);cb.set_ticks(np.linspace(lo,hi,5));cb.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2e'));cb.set_label(title)
    fig.suptitle('PIDL minus conditional FEM c20s4 | signed u/v/active errors | symmetric linear colour scales',fontsize=11)
    save(fig,out/'c20_hidden_newton_errors.png','Candidate minus conditional FEM in physical units, full domain. '
        'Rows u/v/active; all signed scales are symmetric and linear with five explicit numeric ticks. '
        'Active errors are physical cell-mean differences, not log differences; metrics use full GP arrays. '
        'The current hidden+Newton candidate is at right only if the actual endpoint is verified.',provenance)


def analyze(run,out,inputs_manifest=INPUTS,pbd=PBD,fixed=FIXED_NEWTON,render=True):
    if out.exists():raise FileExistsError('Refuse overwrite: '+str(out))
    out.mkdir(parents=True);sources=[];manifest=json_source(inputs_manifest,'input binding manifest',sources)
    item=next(r for r in manifest['cases'] if r['cycle']==20);ip=Path(item['path'])
    if ip.stat().st_size!=item['bytes'] or sha(ip)!=item['sha256']:raise ValueError('Input size/SHA mismatch')
    record(ip,'c20s4 independent conditional accepted FEM reference',sources);record(Path(__file__),'offline analyzer',sources)
    with np.load(ip,allow_pickle=False) as z:inp={k:z[k] for k in z.files}
    op,oppath=independent_operator(ROOT);record(oppath,'independent native Q4 NumPy operator',sources)
    geo=op.q4_geometry(inp['nodes'],inp['cells']);N,B,w,_=geo;n=len(inp['nodes']);mass=np.zeros(n)
    for j in range(4):np.add.at(mass,inp['cells'][:,j],np.sum(w*N[:,j],axis=1))
    fem={k:inp[k+'_fem'].astype(float) for k in ['u','v','d']};ref=q4_fields(fem,inp,op,geo)
    native_error=float(np.max(np.abs(ref['_nodal_force']-inp['ru_fem'])))
    if native_error>1e-10 or ref['independent_free_u_l2']>1e-8:raise ValueError('FEM native force contract mismatch')
    physical={'FEM':fem};case=worker_output(pbd)/'c20_s4'
    for name,path in [('original_theta0',case/'fields.npz'),('PBD_full_network',case/'U_energy/fields.npz')]:
        if path.exists():physical[name]=fields(path,n,sources,name)
    fixed_folder,fixed_status=endpoint(fixed,20,sources)
    if fixed_folder:physical['fixed_feature_Newton']=fields(fixed_folder/'fields.npz',n,sources,'verified fixed-feature Newton')
    newfolder,newstatus=new_endpoint(run,sources)
    if newfolder:physical['hidden_Newton']=fields(newfolder/'fields.npz',n,sources,'verified hidden/Newton actual endpoint')
    metrics={};gp={};checks={};rows=[];boundaries={}
    for name,f in physical.items():
        if not np.array_equal(f['d'],fem['d']):raise ValueError('FEM damage changed: '+name)
        boundaries[name]=boundary_check(f,fem,inp)
        r,q=score(f,fem,inp,op,geo,ref,mass);r.update(cycle=20,substep=4,method=name,fixed_FEM_damage_exact=True)
        metrics[name]=r;gp[name]=q;rows.append(r)
    if 'fixed_feature_Newton' in metrics:checks['fixed_feature_Newton']=verify_four(fixed_status['worker']['actual_network'],metrics['fixed_feature_Newton'])
    if 'hidden_Newton' in metrics:checks['hidden_Newton']=verify_four(newstatus['worker']['actual_network'],metrics['hidden_Newton'])
    info=newstatus.get('worker',{});state=dict(cycle=20,substep=4,load=.11999988,FEM_reference=item['fem'],
        metrics=metrics,fixed_feature_endpoint=fixed_status,new_endpoint=newstatus,boundary_checks=boundaries,
        independent_four_checks=checks,native_FEM_force_maxabs_error=native_error,
        missing_methods=[name for name in METHODS if name not in metrics],hidden_change=hidden_change_check(info),
        gradient_readouts=gradient_readouts(Path(newstatus['folder']) if Path(newstatus['folder']).is_dir() else None,info,sources))
    state['gradient_field_checks']={}
    gradient_methods={'original_theta0':'original_theta0','PBD_U_energy':'PBD_full_network','fixed_feature_Newton':'fixed_feature_Newton','final':'hidden_Newton'}
    for row in state['gradient_readouts']:
        method=gradient_methods.get(row.get('label'))
        if row.get('status')=='verified' and method in metrics:
            state['gradient_field_checks'][row['label']]=verify_four(row,metrics[method])
    if newfolder:
        if not state['hidden_change']['verified_from_digest_and_delta']:
            raise ValueError('Completed candidate lacks explicit hidden parameter digest/delta evidence')
        state['fixed_span_checks']=fixed_span_checks(newfolder,info,fixed,sources)
    state['gradient_readout_status']='complete_required_baselines_and_final' if newstatus['status']=='completed' else 'partial_evidence_only'
    state['decision']=conclusion(state)
    evidence_folder=Path(newstatus['folder'])
    if evidence_folder.is_dir():
        for filename in ['accepted.json','trace.json']:
            if (evidence_folder/filename).exists():state[filename[:-5]]=json_source(evidence_folder/filename,'producer '+filename,sources)
    provenance=f'Current Run {run.name}; c20s4 step99 peak U=.11999988. Baselines: {pbd.name} and {fixed.name}. Bound input {ip}. Exact source paths/SHA and readouts: summary.json; independent field metrics: metrics.csv.'
    if render:
        scalar_figure(out,state,provenance);gradient_figure(out,state,provenance);field_figures(out,inp,geo,op,physical,gp,provenance)
    with (out/'metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=dict(protocol='S04-E011-hidden-Newton-offline-r1',run=str(run),state=state,sources=sources,claim_boundary=SCOPE,
        producer_parameter_gradient_boundary='Raw Eel gradients in original network parameter coordinates are producer observations, not independently recomputed by this NumPy field analyzer.')
    dump(out/'summary.json',summary)
    (out/'README_analysis.md').write_text('# PIDL c20s4 hidden-feature / Newton diagnosis\n\n'+SCOPE+'\n\n'
        'Read summary.json/metrics.csv first. This offline analyzer independently recomputes native-Q4 elastic energy, global free-u force, mass-L2, gradient-H1 and active weighted L2. '
        'Exported FEM damage is exactly equal and top/bottom u/v are independently checked against FEM. '
        'Worker raw hidden/UV parameter gradients are a different readout from conditioned head gradients and nodal force; no unsupported stationarity or capacity threshold is introduced. '
        'The registered accessible-hidden-improvement observable is energy decrease >1e-10 relative to fixed-feature Newton together with verified hidden parameter change; this is component evidence only. '
        'Missing/partial terminal fields are excluded. Actual hidden changes require explicit parameter digest/delta evidence.\n\n'
        'Figures: decision scalars, producer raw parameter-gradient readouts, FEM-first mechanical fields, and signed physical errors. '
        'Field maps use u/v linear, active log10(max(GP-weighted cell mean,1e-12)) without upper clipping; signed errors remain physical linear differences. '
        'All figures have standalone Data provenance / How to read / Limitation sidecars and require visual review. '
        'Preserve B0 Smooth Boundary, Smooth-B0 damage map and constrained-Q4 damage route; this run updates no damage or fatigue history.\n')
    return summary


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--dest',type=Path)
    ap.add_argument('--inputs-manifest',type=Path,default=INPUTS);ap.add_argument('--pbd-run',type=Path,default=PBD)
    ap.add_argument('--fixed-newton-run',type=Path,default=FIXED_NEWTON);a=ap.parse_args()
    dest=a.dest if a.dest else a.run/'analysis_hidden_newton'
    result=analyze(a.run.resolve(),dest.resolve(),a.inputs_manifest.resolve(),a.pbd_run.resolve(),a.fixed_newton_run.resolve())
    print(json.dumps(dict(dest=str(dest),new_endpoint_status=result['state']['new_endpoint']['status']),indent=2))


if __name__=='__main__':main()
