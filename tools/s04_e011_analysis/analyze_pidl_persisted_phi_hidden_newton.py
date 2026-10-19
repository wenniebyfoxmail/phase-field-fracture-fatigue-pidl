#!/usr/bin/env python3
"""Offline c20s4 persisted-actual-Phi hidden/Newton continuation.

Only reads saved actual checkpoints and independently replays NumPy Q4 fields.
No neural forward, optimization, new damage solve, history update or SSH.
"""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize, SymLogNorm
from matplotlib.ticker import FormatStrFormatter
from analyze_pidl_head_newton import (BASE,INPUTS,ROOT,ACTIVE_LOG_FLOOR,read_json,record,
    worker_output,fields,score,verify_four,finite_range,panel)
from analyze_pidl_hidden_newton import boundary_check,hidden_change_check
from analyze_pidl_block_diagnosis import independent_operator,q4_fields,dump,sha,metric

INITIAL_RUN=BASE/'runs/pf_s04e011_learnednewton_e2dc61d_20261018T125034Z_production'
STAGES=['initial','hidden_1','head_1','hidden_2','head_2']
METHODS=['FEM','initial_learned_head','accepted_terminal']
LABELS=['conditional FEM','initial learned-head endpoint','last actual accepted endpoint']
GTOL=1e-10
ENERGY_MARGIN=1e-10
GRAD_KEYS=['hidden_gradient_l2','hidden_gradient_inf','uv_head_gradient_l2','uv_head_gradient_inf',
           'conditioned_head_gradient_l2','conditioned_head_gradient_inf']
SCOPE=('Single FEM/PIDL c20s4 peak, step99, U=.11999988, native Q4/2x2 Gauss integration, eta=0. '
       'The unique accepted learned-head network is the initial state; it is neither the original network nor the old fixed-feature head. '
       'The initial actual floating-point Phi is copied from the saved audit source, never reconstructed or SVD-rebuilt. '
       'At most two hidden microblocks and full-current401-design Newton head corrections use exact fixed conditional FEM damage and original UV boundary. '
       'All saved verified actual stages are reported in execution order; no endpoint is selected by FEM field error. '
       'No coupled damage/displacement evolution, history commit, teacher, physical truth or whole-network capacity claim. '
       'RAW psi+ in fully degraded g=0 regions is secondary to the separately reported ACTIVE g(d)psi+ field.')


def js_source(path,role,sources):
    record(path,role,sources);return read_json(path)


def finite_readout(row):
    if row.get('status')!='verified' or row.get('objective')!='raw_Eel':
        raise ValueError('Actual checkpoint lacks verified raw-Eel readout')
    for key in ['E_el','free_u_l2','uv_mass_rel_L2','uv_H1_rel']+GRAD_KEYS:
        if row.get(key) is None or not np.isfinite(row[key]) or row[key]<0:
            raise ValueError('Missing/nonfinite actual checkpoint readout '+key)


def replay(f,fem,inp,op,geo,ref,mass):
    if not np.array_equal(f['d'],fem['d']):raise ValueError('Exact FEM mechanical damage changed')
    bc=boundary_check(f,fem,inp)
    row,gp=score(f,fem,inp,op,geo,ref,mass)
    for key,value in metric(ref['raw'],gp['raw'],geo[2]).items():row['raw_vs_FEM_'+key]=value
    row['boundary_maxabs']=bc['FEM_boundary_maxabs'];row['fixed_FEM_damage_exact']=True
    return row,gp


def valid_digest(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def validate_budget(info,phase):
    expected=40 if phase=='probe' else 325
    phase_seconds=60 if phase=='probe' else 540
    for key,value in [('prior_evaluations',35),('new_probe_production_cap',365),('total_prior_plus_new_cap',400),
                      ('new_probe_production_deadline_seconds',600),('cap',expected),('deadline_seconds',phase_seconds)]:
        if info.get(key)!=value:raise ValueError('Bound original budget mismatch: '+key)
    if info.get('prior_elapsed_seconds') is not None or info.get('cumulative_elapsed_seconds_claim') is not False:
        raise ValueError('Prior elapsed time unknown; no cumulative wall-time claim is allowed')
    if not isinstance(info.get('evaluations'),int) or not 0<=info['evaluations']<=expected:
        raise ValueError('Phase energy/gradient count outside declared allowance')


def basis_folder(case,reference):
    """Map a remote pointer to retrieved small metadata; never rebuild missing Phi."""
    parts=Path(reference).parts
    if len(parts)<2 or parts[-2]!='bases' or parts[-1] not in ['initial','hidden_1','hidden_2']:
        raise ValueError('Unknown persisted basis_ref: '+str(reference))
    return case/'bases'/parts[-1]


def validate_basis_metadata(meta,initial):
    rank=meta.get('retained_rank')
    if not isinstance(rank,int) or not 0<rank<=401 or meta.get('current_full_raw_columns')!=401:
        raise ValueError('Invalid persisted full401 basis metadata')
    for key in ['phi_sha256','transform_sha256','bound_hidden_sha256','originating_weights_sha256']:
        if not valid_digest(meta.get(key)):raise ValueError('Missing persisted identity: '+key)
    if initial:
        if not (rank==386 and meta.get('actual_saved_Phi_reused') is True and
                meta.get('initial_Phi_reconstructed') is False and meta.get('initial_SVD_calls')==0):
            raise ValueError('Initial must reuse saved actual rank386 Phi with no reconstruction/SVD')
        if meta.get('source_phi_sha256')!=meta['phi_sha256'] or meta.get('source_transform_sha256')!=meta['transform_sha256']:
            raise ValueError('Initial actual Phi/T copy does not match its saved source SHA')
    elif not (meta.get('original_columns')==401 and meta.get('dynamic_current_feature_basis') is True and
              meta.get('old_restricted_span_used') is False):
        raise ValueError('Hidden-updated basis must retain current full401 dynamic-rank policy')
    return meta


def readout_identity(row,case,sources):
    """Validate small persisted proof arrays; full actual Phi may remain remote."""
    finite_readout(row)
    label=row.get('label')
    if not isinstance(label,str) or '/' in label or '\\' in label:raise ValueError('Invalid actual readout label')
    base=basis_folder(case,row.get('basis_ref',''));mp=base/'metadata.json'
    meta=js_source(mp,'actual readout linked basis '+label,sources)
    validate_basis_metadata(meta,base.name=='initial')
    if (row.get('basis_hidden_match') is not True or row.get('hidden_sha256')!=row.get('basis_bound_hidden_sha256') or
        row.get('basis_bound_hidden_sha256')!=meta['bound_hidden_sha256'] or row.get('basis_phi_sha256')!=meta['phi_sha256']):
        raise ValueError('Actual Phi is not bound to the readout hidden state')
    if not valid_digest(row.get('bound_weights_sha256')):raise ValueError('Readout full-weight digest missing')
    if row.get('gradient_inf_tolerance')!=GTOL:raise ValueError('Actual readout target changed')
    folder=case/'readouts';jp=folder/(label+'_actual.json');saved=js_source(jp,'saved actual readout identity '+label,sources)
    for key in ['basis_ref','basis_phi_sha256','hidden_sha256','basis_bound_hidden_sha256','bound_weights_sha256']+GRAD_KEYS+['E_el','free_u_l2','uv_mass_rel_L2','uv_H1_rel']:
        if saved.get(key)!=row.get(key):raise ValueError('Checkpoint and persisted actual-readout differ: '+key)
    gp=folder/(label+'_actual_projected_gradient.npy');record(gp,'same actual-Phi projected gradient '+label,sources)
    g=np.load(gp,allow_pickle=False)
    if g.shape!=(2*meta['retained_rank'],) or not np.isfinite(g).all():raise ValueError('Invalid saved actual projected gradient')
    gi=float(np.max(np.abs(g)));gl=float(np.sqrt(np.einsum('i,i->',g,g,optimize=False)))
    if gi!=row['conditioned_head_gradient_inf'] or gi!=row['reduced_gradient_inf']:
        raise ValueError('Saved projected gradient infinity differs from readout')
    if abs(gl-row['conditioned_head_gradient_l2'])>1e-12+1e-9*abs(gl):raise ValueError('Saved projected gradient L2 differs from readout')
    if bool(row.get('head_stationarity_closed'))!=(gi<=GTOL):raise ValueError('Actual head closure label differs from vector')
    fp=folder/(label+'.npz');record(fp,'actual nodal fields/forces/raw UV gradient '+label,sources)
    with np.load(fp,allow_pickle=False) as z:arrays={k:np.asarray(z[k],dtype=float) for k in ['u','v','d','gu','gv','raw_head_gradient']}
    if not all(np.isfinite(v).all() for v in arrays.values()) or arrays['raw_head_gradient'].shape!=(2,401):
        raise ValueError('Nonfinite or incomplete actual field/force/raw-head arrays')
    n=arrays['u'].size
    if any(arrays[k].size!=n for k in ['v','d','gu','gv']):raise ValueError('Incompatible saved readout array lengths')
    local_checks={}
    for name,key in [('phi.npy','phi_sha256'),('transform.npy','transform_sha256')]:
        path=base/name
        if path.exists():
            record(path,'optional local actual basis identity '+label,sources)
            if sha(path)!=meta[key]:raise ValueError('Local actual basis differs from persisted metadata')
            local_checks[name]='present_SHA_verified_without_forward_or_reconstruction'
        else:local_checks[name]='not_retrieved_no_reconstruction'
    return dict(label=label,basis_ref=row['basis_ref'],basis_phi_sha256=meta['phi_sha256'],rank=meta['retained_rank'],
        hidden_sha256=row['hidden_sha256'],basis_bound_hidden_sha256=row['basis_bound_hidden_sha256'],
        bound_weights_sha256=row['bound_weights_sha256'],basis_originating_weights_sha256=meta['originating_weights_sha256'],
        basis_hidden_match=True,actual_projected_gradient_inf=gi,actual_projected_gradient_l2=gl,
        head_closed=gi<=GTOL,local_actual_basis_files=local_checks,fields_maxabs_vs_checkpoint=None,
        _saved_fields={k:arrays[k].reshape(-1) for k in ['u','v','d']},
        _force=np.concatenate([arrays[k].reshape(-1) for k in ['gu','gv']]))


def probe_stability(run,sources,source_fields=None):
    if run is None:return dict(status='probe_evidence_not_supplied')
    case=worker_output(run)/'c20_s4';info=js_source(case/'result.json','same-actual-Phi stability probe result',sources)
    validate_budget(info,'probe')
    if info.get('status')!='probe_passed' or info.get('all_three_same_Phi_readouts_passed') is not True:
        raise ValueError('Persisted actual-Phi stability probe did not pass')
    for key in ['optimizer_updates','parameter_updates','history_commits','rollout_steps']:
        if info.get(key)!=0:raise ValueError('Stability probe changed '+key)
    for key in ['damage_output_row_unchanged','Smooth_B0_anchor_unchanged','mechanical_damage_exact_FEM','boundary_unchanged']:
        if info.get(key) is not True:raise ValueError('Stability probe fixed-state contract missing '+key)
    rows=info.get('actual_Phi_repetition_readouts',[])
    if len(rows)!=3 or [r.get('label') for r in rows]!=['initial_learned_head','probe_repeat_1','probe_repeat_2']:
        raise ValueError('Probe requires the three named actual full-network readouts')
    identities=[];vectors=[];fs=[]
    for row in rows:
        identity=readout_identity(row,case,sources)
        if max(row.get('source_field_maxabs',{}).values(),default=np.inf)>1e-12 or row.get('source_energy_abs_error',np.inf)>1e-10 or not identity['head_closed']:
            raise ValueError('Stability probe does not reproduce original source/1e-10 contract')
        fs.append(identity.pop('_saved_fields'));identity.pop('_force');identities.append(identity)
        vectors.append(np.load(case/'readouts'/(row['label']+'_actual_projected_gradient.npy'),allow_pickle=False))
    for identity in identities[1:]:
        for key in ['basis_phi_sha256','hidden_sha256','bound_weights_sha256']:
            if identity[key]!=identities[0][key]:raise ValueError('Probe did not hold actual Phi/weights fixed')
    source_field_error=None
    if source_fields is not None:
        source_field_error=max(float(np.max(np.abs(f[k]-source_fields[k]))) for f in fs for k in ['u','v','d'])
        if source_field_error>1e-12:raise ValueError('Probe saved fields do not independently reproduce the unique learned-head source')
    maxfield=max(float(np.max(np.abs(f[k]-fs[0][k]))) for f in fs for k in ['u','v','d'])
    if maxfield>1e-12:raise ValueError('Probe actual fields changed beyond original source tolerance')
    gs=np.stack(vectors)
    return dict(status='verified_three_same_actual_Phi',run=str(run),readouts=identities,
        gradient_inf_target=GTOL,projected_gradient_inf_values=[r['actual_projected_gradient_inf'] for r in identities],
        gradient_inf_spread=float(np.ptp([r['actual_projected_gradient_inf'] for r in identities])),
        full_gradient_coordinate_range_inf=float(np.max(np.ptp(gs,axis=0))),fields_maxabs_between_readouts=maxfield,
        independently_checked_source_fields_maxabs=source_field_error,
        original_threshold_unchanged=True,source_reproduction=info.get('source_reproduction'),evaluations=info['evaluations'],
        elapsed_seconds=info.get('elapsed_seconds'),new_probe_production_cap=365,prior_evaluations=35,
        deadline_seconds=60,cumulative_wall_time_claim=False,scope='Repeated actual readouts of one fixed saved Phi and network, not optimizer or capacity evidence')


def terminal(run,sources):
    folder=worker_output(run)/'c20_s4';rp=folder/'result.json'
    if not rp.exists():return folder,dict(status='missing',folder=str(folder))
    info=js_source(rp,'new continuation terminal status',sources)
    if (info.get('cycle'),info.get('substep'),info.get('step'))!=(20,4,99):raise ValueError('Wrong terminal identity')
    excluded=info.get('status')!='completed' or info.get('actual_network') is None or bool(info.get('rolled_back') or info.get('hard_solver_failure'))
    if excluded:
        return folder,dict(status=info.get('status','unknown'),eligible_new_terminal=False,
            folder=str(folder),worker=info,excluded_reason='Partial/rolled-back/hard-failure fields cannot be scored as a new terminal endpoint')
    for key in ['damage_output_row_unchanged','Smooth_B0_anchor_unchanged','mechanical_damage_exact_FEM','boundary_unchanged']:
        if info.get(key) is not True:raise ValueError('Completed frozen-state contract missing: '+key)
    for key in ['history_commits','rollout_steps']:
        if info.get(key)!=0:raise ValueError('Unexpected '+key)
    if info.get('ridge')!=0.:raise ValueError('Ridge contract changed')
    if info.get('current_raw_columns')!=401 or info.get('dynamic_current_feature_basis') is not True or info.get('old_restricted_span_used') is not False:
        raise ValueError('Head correction must use full current401 design with dynamic numerical rank, not old restricted span')
    if info.get('initial_rank')!=386:raise ValueError('Reused initial actual Phi rank must be386')
    validate_budget(info,'production')
    source_record=info.get('source_reproduction',{})
    if source_record.get('passed') is not True or source_record.get('initial_rank')!=386:
        raise ValueError('Source reproduction contract missing')
    if source_record.get('energy_abs_error',np.inf)>1e-10 or source_record.get('actual_current_head_gradient_inf',np.inf)>GTOL:
        raise ValueError('Initial energy/projected-gradient source contract failed')
    finite_readout(info['actual_network'])
    return folder,dict(status='completed',eligible_new_terminal=True,folder=str(folder),worker=info)


def decision(state):
    endpoint=state['endpoint'];metrics=state['metrics']
    if not endpoint.get('eligible_new_terminal') or 'accepted_terminal' not in metrics:
        return dict(new_terminal_verified=False,directional_energy_improvement=False,
            conclusion='No eligible new actual terminal endpoint. All verified saved stages remain descriptive evidence, not a promoted terminal result.')
    info=endpoint['worker'];actual=info['actual_network'];a=actual['conditioned_head_gradient_inf']
    head_closed=bool(a<=GTOL)
    if 'head_stationarity_closed' in info and bool(info['head_stationarity_closed'])!=head_closed:
        raise ValueError('Actual projected-head closure flag mismatch')
    gain=metrics['initial_learned_head']['E_el']-metrics['accepted_terminal']['E_el']
    hidden_verified=bool(state.get('hidden_change',{}).get('verified_from_digest_and_delta') and state.get('hidden_change',{}).get('actual_hidden_changed') is True)
    return dict(new_terminal_verified=True,terminal_checkpoint=state.get('terminal_checkpoint_match'),
        new_state_accepted=state.get('terminal_checkpoint_match')!='initial',
        absolute_energy_decrease=gain,registered_directional_margin=ENERGY_MARGIN,actual_hidden_change_verified=hidden_verified,
        energy_margin_exceeded=bool(gain>ENERGY_MARGIN),directional_energy_improvement=bool(gain>ENERGY_MARGIN and hidden_verified),
        relative_energy_decrease=gain/metrics['initial_learned_head']['E_el'],actual_projected_head_gradient_inf=a,
        actual_head_closed=head_closed,head_gradient_target=GTOL,raw_hidden_gradient_inf=actual['hidden_gradient_inf'],
        raw_UV_parameter_gradient_inf=actual['uv_head_gradient_inf'],global_free_nodal_force=metrics['accepted_terminal']['free_u_l2'],
        conclusion=('The last actual accepted endpoint closes the declared local projected-head criterion.' if head_closed else
                    'The last actual accepted endpoint remains above the declared local projected-head criterion and is reported as unclosed.')+
                    ' Energy improvement beyond1e-10 is component progress only; raw hidden gradient, global force and FEM field errors are separate observables. Head closure is not whole-network stationarity or a capacity certificate.')


def save(fig,path,caption,provenance):
    fig.savefig(path,dpi=165);plt.close(fig)
    path.with_suffix('.md').write_text('# '+path.stem+'\n\n'+caption+'\n\n'
        '## Data provenance\n\n'+provenance+'\n\n'
        '## How to read\n\nFEM/PIDL c20s4 subjects and each accepted stage are explicit in panel labels. '
        'Missing/partial stages are gaps, not zero or interpolated results. Read exact untransformed metrics and source hashes in summary.json, metrics.csv and stage_metrics.csv.\n\n'
        '## Limitation\n\n'+SCOPE+' Raw parameter gradients are producer derivatives in original architecture coordinates; '
        'conditioned-head gradients use the saved actual basis: reused source Phi initially, newly persisted current-feature Phi after hidden movement. Their coordinate norms are not directly the same across hidden updates. '
        'Global nodal force is a separate physical-space quantity. Every figure requires visual review before report adoption.\n')


def stage_figures(out,state,provenance):
    saved=state['stages'];labels=['initial','hidden1','head1','hidden2','head2'];x=np.arange(5)
    def values(key):return [np.nan if r.get(key) is None else r[key] for r in saved]
    fig,axs=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    energy=values('E_el');e0=state['metrics']['initial_learned_head']['E_el']
    specs=[('E_el','Actual accepted elastic energy'),('free_u_l2','Global free-u force L2'),
        ('uv_mass_rel_L2','UV mass relative L2'),('uv_H1_rel','Full Q4 gradient/H1 error'),
        ('active_vs_FEM_relative_L2','ACTIVE weighted relative L2 / FEM'),('conditioned_head_gradient_inf','Actual projected-head gradient infinity')]
    for ax,(key,title) in zip(axs.ravel(),specs):
        ax.plot(x,values(key),'o-',color='#0072B2')
        for i in [2,4]:
            if saved[i]['accepted_verified']:ax.scatter(i,saved[i][key],s=40,marker='s',color='#D55E00',zorder=3)
        ax.set_xticks(x,labels,rotation=25);ax.set_title(title,fontsize=10);ax.grid(alpha=.2)
        if key=='E_el':ax.axhline(e0-ENERGY_MARGIN,ls=':',color='.4',lw=.8,label='initial E - 1e-10 directional margin');ax.legend(fontsize=7)
        if key=='conditioned_head_gradient_inf':ax.set_yscale('log');ax.axhline(GTOL,color='.4',ls='--',lw=.8)
    fig.suptitle('PIDL c20s4 | every saved actual accepted stage, initial → hidden1 → head1 → hidden2 → head2',fontsize=11)
    save(fig,out/'learned_hidden_stage_decision.png','All five planned checkpoint positions, without selecting by FEM error. '
        'Only actual verified saved checkpoints are plotted. Orange squares are actual Newton head corrections; inner conditioned trials are excluded. '
        'Energy directional improvement requires decrease >1e-10 from the unique initial state and verified actual hidden changes. The dotted energy level is the energy margin only, not a convergence threshold. '
        'The1e-10 dashed line applies only to current projected-head gradient infinity; an unclosed endpoint is retained as unclosed. '
        'Raw/active correlation and integrals are in stage_metrics.csv; no scalar alone certifies FEM reproduction.',provenance)
    fig,axs=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    for ax,norm in zip(axs[0],['l2','inf']):
        for group,label,col in [('hidden','hidden parameters','#0072B2'),('uv_head','raw UV-head parameters','#D55E00')]:
            ax.plot(x,values(group+'_gradient_'+norm),'o-',color=col,label=label)
        ax.set_title('Producer raw Eel parameter gradient '+norm);ax.set_yscale('log');ax.legend(fontsize=8)
    for ax,key,title in [(axs[1,0],'conditioned_head_gradient_inf','Current projected-head gradient infinity'),
                         (axs[1,1],'free_u_l2','Independent global free-u force L2')]:
        ax.plot(x,values(key),'o-',color='#009E73');ax.set_title(title);ax.set_yscale('log')
    axs[1,0].axhline(GTOL,color='.4',ls='--',lw=.8)
    for ax in axs.ravel():ax.set_xticks(x,labels,rotation=25);ax.grid(alpha=.2)
    fig.suptitle('PIDL c20s4 raw Eel derivatives | parameter / current projected-head / nodal spaces separate',fontsize=11)
    save(fig,out/'learned_hidden_gradient_spaces.png','Every actual saved stage in execution order. Top: raw elastic-energy hidden/UV parameter gradients, no normalized-loss scaling or weight regularizer. '
        'Bottom: current projected-head infinity gradient and independent global nodal force. Log ordinates; exact zeros remain in summary and cannot be displayed. '
        'The initial actual Phi is reused without reconstruction; the current401 design is SVD-reconditioned only after hidden movement, so projected norms describe their own current basis and its head solve, not a common physical-space norm. '
        'The declared1e-10 projected-head line does not apply to raw hidden gradients or global force.',provenance)


def field_figures(out,inp,geo,op,physical,gp,provenance,status):
    N,_,w,_=geo;c=inp['cells'];polygons=inp['nodes'][c];mean=lambda a:np.sum(w*a,axis=1)/w.sum(1)
    quantities=[('u','horizontal u'),('v','vertical v'),('raw','RAW psi+'),('active','ACTIVE g(d)psi+')]
    fig,axs=plt.subplots(4,3,figsize=(12.5,13.4),layout='constrained',squeeze=False)
    for i,(key,label) in enumerate(quantities):
        vals={name:mean(gp[name][key] if key in ['raw','active'] else op.interp(f[key],c,N)) for name,f in physical.items()}
        logged=key in ['raw','active']
        if logged:vals={name:np.log10(np.maximum(v,ACTIVE_LOG_FLOOR)) for name,v in vals.items()}
        lo,hi=finite_range(list(vals.values()));pcs=[]
        for j,(name,title) in enumerate(zip(METHODS,LABELS)):
            ax=axs[i,j]
            if name not in vals:
                ax.text(.5,.5,'NO ELIGIBLE NEW TERMINAL',ha='center',va='center',transform=ax.transAxes,fontsize=8);ax.set_axis_off();continue
            pcs.append(panel(ax,polygons,vals[name],title if i==0 else label,lo,hi))
        if pcs:
            cb=fig.colorbar(pcs[0],ax=axs[i,:].tolist(),shrink=.75,pad=.01);cb.set_ticks(np.linspace(lo,hi,5));cb.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f' if logged else '%.2e'));cb.set_label('log10 cell mean '+label if logged else label)
    fig.suptitle('FEM / initial / last actual accepted PIDL c20s4 | exact same FEM damage and boundary',fontsize=11)
    save(fig,out/'c20_learned_hidden_fields.png','FEM-first initial/terminal maps of u/v/raw/active. The terminal is the actual last accepted identity, not the stage nearest FEM. '
        'UV uses linear physical cell means. Raw/active use log10(max(GP/Jacobian-weighted Q4 cell mean,1e-12)) with no upper clipping. '
        'Each row has a common scale across its methods; physical full-GP metric arrays remain untransformed. Partial/rollback terminal columns are excluded, while accepted intermediate stages remain in the stage tables.',provenance)
    pairs=[('initial_learned_head','FEM','Initial - FEM'),('accepted_terminal','FEM','Terminal - FEM'),('accepted_terminal','initial_learned_head','Terminal - initial')]
    fig,axs=plt.subplots(4,3,figsize=(12.5,13.4),layout='constrained',squeeze=False)
    for i,(key,label) in enumerate(quantities):
        vals={}
        for a,b,title in pairs:
            if a not in physical or b not in physical:continue
            delta=gp[a][key]-gp[b][key] if key in ['raw','active'] else op.interp(physical[a][key]-physical[b][key],c,N)
            vals[title]=mean(delta)
        lo,hi=finite_range(list(vals.values()),signed=True);pcs=[]
        for j,(_,_,title) in enumerate(pairs):
            ax=axs[i,j]
            if title not in vals:
                ax.text(.5,.5,'NO ELIGIBLE NEW TERMINAL',ha='center',va='center',transform=ax.transAxes,fontsize=8);ax.set_axis_off();continue
            norm=SymLogNorm(ACTIVE_LOG_FLOOR,vmin=lo,vmax=hi) if key in ['raw','active'] else Normalize(lo,hi)
            pc=PolyCollection(polygons,array=vals[title],cmap='RdBu_r',norm=norm,edgecolors='none',rasterized=True)
            ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_title(title if i==0 else label+' signed difference',fontsize=8);ax.set_xlabel('native x');ax.set_ylabel('native y');pcs.append(pc)
        if pcs:
            cb=fig.colorbar(pcs[0],ax=axs[i,:].tolist(),shrink=.75,pad=.01)
            ticks=[lo,lo*.01,0,hi*.01,hi] if key in ['raw','active'] else np.linspace(lo,hi,5)
            cb.set_ticks(ticks);cb.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2e'));cb.set_label(label+' signed physical difference')
    fig.suptitle('PIDL c20s4 physical signed errors | initial/FEM, terminal/FEM, terminal/initial',fontsize=11)
    save(fig,out/'c20_learned_hidden_errors.png','Full-domain signed physical Q4 cell-mean differences; no field values are clipped or replaced by logged differences. '
        'UV errors have linear colour scales. Raw/active physical errors use symmetric-log colour normalization with fixed linear threshold1e-12; colourbar ticks remain physical values. '
        'Each row shares one symmetric scale across all three differences and five explicit numeric ticks. Full-GP errors/correlations/integrals remain authoritative. '
        'RAW in fully degraded zones is a secondary diagnostic; active-energy agreement is separately measured.',provenance)


def write_csv(path,rows):
    names=[]
    for row in rows:
        for key in row:
            if key not in names:names.append(key)
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=names,lineterminator='\n');writer.writeheader();writer.writerows(rows)


def analyze(run,out,inputs_manifest=INPUTS,initial_run=INITIAL_RUN,render=True,probe_run=None):
    if out.exists():raise FileExistsError('Refuse overwrite: '+str(out))
    out.mkdir(parents=True);sources=[];manifest=js_source(inputs_manifest,'input binding manifest',sources)
    item=next(x for x in manifest['cases'] if x['cycle']==20);ip=Path(item['path'])
    if ip.stat().st_size!=item['bytes'] or sha(ip)!=item['sha256']:raise ValueError('Input size/SHA mismatch')
    record(ip,'conditional FEM c20 outer18 input',sources);record(Path(__file__),'offline analyzer',sources)
    with np.load(ip,allow_pickle=False) as z:inp={k:z[k] for k in z.files}
    op,oppath=independent_operator(ROOT);record(oppath,'independent native Q4 NumPy operator',sources)
    geo=op.q4_geometry(inp['nodes'],inp['cells']);N,B,w,_=geo;n=len(inp['nodes']);mass=np.zeros(n)
    for j in range(4):np.add.at(mass,inp['cells'][:,j],np.sum(w*N[:,j],axis=1))
    fem={k:inp[k+'_fem'].astype(float) for k in ['u','v','d']};ref=q4_fields(fem,inp,op,geo)
    native_err=float(np.max(np.abs(ref['_nodal_force']-inp['ru_fem'])))
    if native_err>1e-10 or ref['independent_free_u_l2']>1e-8:raise ValueError('FEM reference native force contract failed')
    initial_folder=worker_output(initial_run)/'c20_s4';initial_info=js_source(initial_folder/'result.json','unique accepted learned-head initial result',sources)
    if initial_info.get('status')!='completed' or initial_info.get('actual_network') is None or initial_info.get('rolled_back'):
        raise ValueError('Initial must be the unique accepted non-rolled-back learned-head endpoint')
    if initial_info['actual_network'].get('conditioned_head_gradient_inf',initial_info['actual_network'].get('reduced_gradient_inf',np.inf))>GTOL:
        raise ValueError('Unique initial learned head is not closed under the declared actual-gradient target')
    start=fields(initial_folder/'fields.npz',n,sources,'unique learned-head accepted initial fields')
    initial_metric,initial_gp=replay(start,fem,inp,op,geo,ref,mass);verify_four(initial_info['actual_network'],initial_metric)
    folder,status=terminal(run,sources);info=status.get('worker',{});physical={'FEM':fem,'initial_learned_head':start};gp={'FEM':ref,'initial_learned_head':initial_gp}
    femmetric,_=replay(fem,fem,inp,op,geo,ref,mass);metrics={'FEM':femmetric,'initial_learned_head':initial_metric}
    stage_rows=[];stage_records=[];stage_fields={};stage_gp={};basis_records=[];readout_records=[]
    probe=probe_stability(probe_run,sources,start)
    if status.get('eligible_new_terminal') and probe.get('status')!='verified_three_same_actual_Phi':
        raise ValueError('Completed route requires --probe-run with the bound three-readout actual-Phi stability evidence')
    for index,label in enumerate(STAGES):
        cp=folder/'checkpoints'/label;rp=cp/'result.json';fp=cp/'fields.npz'
        if not rp.exists() or not fp.exists():
            stage_rows.append(dict(sequence=index,stage=label,accepted_verified=False,status='not_saved_or_incomplete'))
            stage_records.append(dict(stage=label,status='not_saved_or_incomplete',folder=str(cp)));continue
        raw=js_source(rp,'actual accepted '+label+' raw Eel readout',sources);finite_readout(raw)
        identity=readout_identity(raw,folder,sources)
        readout_records.append(dict(stage=label,identity=identity))
        f=fields(fp,n,sources,'actual accepted checkpoint '+label);row,q=replay(f,fem,inp,op,geo,ref,mass);checks=verify_four(raw,row)
        identity['independent_nodal_force_maxabs_difference']=float(np.max(np.abs(identity.pop('_force')-q['_nodal_force'])))
        identity['fields_maxabs_vs_checkpoint']=max(float(np.max(np.abs(identity['_saved_fields'][k]-f[k]))) for k in ['u','v','d'])
        if max(float(np.max(np.abs(identity['_saved_fields'][k]-f[k]))) for k in ['u','v','d'])>1e-12:
            raise ValueError('Persisted actual-readout arrays differ from saved accepted checkpoint')
        del identity['_saved_fields']
        if label=='initial':
            err=max(float(np.abs(f[k]-start[k]).max()) for k in ['u','v','d'])
            if err>1e-12:raise ValueError('Fresh initial does not reproduce the unique accepted learned-head source')
            if raw['conditioned_head_gradient_inf']>GTOL:raise ValueError('Fresh initial actual projected-head gradient fails1e-10')
        flat=dict(sequence=index,stage=label,accepted_verified=True,status='verified_actual',**row)
        for key in GRAD_KEYS:flat[key]=raw[key]
        stage_rows.append(flat);stage_fields[label]=f;stage_gp[label]=q
        stage_records.append(dict(stage=label,status='verified_actual',readout=raw,independent_four_checks=checks,metrics=row))
    if status.get('eligible_new_terminal'):
        initial_identity=next(r['identity'] for r in readout_records if r['stage']=='initial')
        for key in ['basis_phi_sha256','hidden_sha256','bound_weights_sha256']:
            if initial_identity[key]!=probe['readouts'][0][key]:raise ValueError('Probe/production initial identity differs: '+key)
        if probe['evaluations']+info['evaluations']>365:raise ValueError('New probe/production total exceeds365')
        if 'initial' not in stage_fields:raise ValueError('Completed arm lacks reproduced actual initial checkpoint')
        actual=fields(folder/'fields.npz',n,sources,'last actual accepted terminal fields')
        row,q=replay(actual,fem,inp,op,geo,ref,mass);checks=verify_four(info['actual_network'],row)
        final_identity=readout_identity(info['actual_network'],folder,sources)
        final_identity['independent_nodal_force_maxabs_difference']=float(np.max(np.abs(final_identity.pop('_force')-q['_nodal_force'])))
        final_identity['fields_maxabs_vs_checkpoint']=max(float(np.max(np.abs(final_identity['_saved_fields'][k]-actual[k]))) for k in ['u','v','d'])
        if final_identity['fields_maxabs_vs_checkpoint']>1e-12:raise ValueError('Final actual readout fields differ from terminal')
        del final_identity['_saved_fields'];readout_records.append(dict(stage='final',identity=final_identity))
        label=info.get('last_verified_checkpoint')
        if label not in stage_fields:raise ValueError('Terminal identity is not a saved actual accepted checkpoint: '+str(label))
        latest=next(stage for stage in reversed(STAGES) if stage in stage_fields)
        if label!=latest:raise ValueError('Terminal must be the LAST saved accepted stage, never a selected earlier point')
        err=max(float(np.abs(actual[k]-stage_fields[label][k]).max()) for k in ['u','v','d'])
        if err>1e-12:raise ValueError('Final fields are not the declared last accepted checkpoint')
        physical['accepted_terminal']=actual;gp['accepted_terminal']=q;metrics['accepted_terminal']=row
    basis_paths=([folder/'initial_basis.json'] if (folder/'initial_basis.json').exists() else [])+sorted(folder.glob('bases/*/metadata.json'))
    for bp in basis_paths:
        b=js_source(bp,'persisted actual basis metadata',sources)
        initial=bp.name=='initial_basis.json' or bp.parent.name=='initial'
        validate_basis_metadata(b,initial)
        basis_records.append(dict(path=str(bp),metadata=b,
            local_full_matrix_required=False,local_Phi_present=(bp.parent/'phi.npy').exists()))
    for bp in sorted(folder.glob('head_stage_*/basis_ref.json')):
        link=js_source(bp,'head correction shared actual-Phi reference',sources)
        bm=js_source(basis_folder(folder,link['basis_ref'])/'metadata.json','shared head actual-Phi metadata',sources)
        if link.get('phi_sha256')!=bm.get('phi_sha256') or link.get('transform_sha256')!=bm.get('transform_sha256'):
            raise ValueError('Head correction basis_ref/SHA mismatch')
        basis_records.append(dict(path=str(bp),shared_basis_reference=link))
    if status.get('eligible_new_terminal'):
        source_record=info['source_reproduction']
        if source_record.get('source_fields_sha256')!=sha(initial_folder/'fields.npz'):
            raise ValueError('Worker source field SHA differs from the unique accepted initial source')
        if not (folder/'initial_basis.json').exists():raise ValueError('Completed arm initial basis metadata missing')
    state=dict(cycle=20,substep=4,step=99,load=.11999988,FEM_reference=item['fem'],endpoint=status,
        metrics=metrics,stages=stage_rows,stage_records=stage_records,current_bases=basis_records,
        terminal_checkpoint_match=info.get('last_verified_checkpoint'),native_FEM_force_maxabs=native_err,
        hidden_change=hidden_change_check(info),probe_stability=probe,persisted_readout_identity_links=readout_records,
        budget_semantics='prior35 + new probe40 + production325 <=400; probe60s + production540s = new round600s only, not cumulative old wall time; an in-flight call may finish after the no-new-work deadline')
    if status.get('eligible_new_terminal') and not state['hidden_change']['verified_from_digest_and_delta']:
        raise ValueError('Completed arm lacks explicit hidden-change digests and maxabs evidence')
    state['decision']=decision(state)
    if folder.is_dir():
        for name in ['gradient_readouts.json','accepted.json','stages.json','trace.json']:
            if (folder/name).exists():state['producer_'+name[:-5]]=js_source(folder/name,'producer '+name,sources)
    arrays=dict(nodes=inp['nodes'],cells=inp['cells'],GP_weights=w)
    for label,f in stage_fields.items():
        for key in ['u','v','d']:arrays[label+'_'+key]=f[key]
        for key in ['raw','active']:arrays[label+'_'+key+'_gp']=stage_gp[label][key]
    for key in ['raw','active']:arrays['FEM_'+key+'_gp']=ref[key]
    scored=out/'scored_stage_fields_gp.npz';np.savez_compressed(scored,**arrays)
    state['exact_scoring_arrays']=dict(path=str(scored),sha256=sha(scored),bytes=scored.stat().st_size,display_transforms_stored=False)
    provenance=f'Continuation Run {run.name}, c20s4 step99 only; unique initial Run {initial_run.name}; fixed conditional FEM outer18 from {ip}. Exact physical metrics/source hashes: summary.json, metrics.csv, stage_metrics.csv, scored_stage_fields_gp.npz.'
    if render:stage_figures(out,state,provenance);field_figures(out,inp,geo,op,physical,gp,provenance,status)
    metric_rows=[dict(method=name,cycle=20,substep=4,**row) for name,row in metrics.items()]
    write_csv(out/'metrics.csv',metric_rows);write_csv(out/'stage_metrics.csv',stage_rows)
    result=dict(protocol='S04-E011-persisted-Phi-hidden-Newton-offline-r1',run=str(run),state=state,sources=sources,claim_boundary=SCOPE)
    dump(out/'summary.json',result)
    (out/'README_analysis.md').write_text('# PIDL c20s4 learned-head continuation: all actual accepted stages\n\n'+SCOPE+'\n\n'
        'Independent NumPy native-Q4 replay: Eel, global free-u force, mass/H1 errors, RAW/ACTIVE weighted L2, correlations and integrals. '
        'FEM d is exactly equal, boundary is independently checked, and the initial network reproduces the unique learned-head accepted fields while loading the audit-saved actual Phi unchanged (zero initial SVD/reconstruction). '
        'Final identity must match the declared last actual accepted checkpoint; no stage is chosen by FEM field error. '
        'All planned initial/hidden1/head1/hidden2/head2 positions are retained as verified actual data or explicit missing entries. '
        'Partial or globally rolled-back endpoints are not promoted to a new terminal; already verified intermediate checkpoints remain reported.\n\n'
        'Four figures: scalar stage decisions including registered energy decrease >1e-10 and actual projected-head infinity <=1e-10; '
        'separate raw-parameter/current-projected-head/global-force spaces; FEM/initial/terminal UV/raw/active maps; signed physical errors. '
        'Raw/active maps use log10(max(cell mean,1e-12)); their signed physical-error colour scales are symmetric-log with linear threshold1e-12 and physical numeric ticks. '
        'All physical full-GP metrics are unchanged. Small loss changes or a closed head do not establish whole-network stationarity or capacity limits. '
        'Unclosed final head gradients remain reported as unclosed. Same-Phi probe vectors and stage basis/hidden identity links are in summary.json. Large Phi files may remain remote; absent local matrices are not reconstructed and do not prevent small-array analysis. The 600-second deadline is for this round only, not an accumulated wall-time claim. Each figure has standalone Data provenance / How to read / Limitation sidecar and requires visual review.\n')
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--dest',type=Path)
    ap.add_argument('--probe-run',type=Path,required=True);ap.add_argument('--initial-run',type=Path,default=INITIAL_RUN);ap.add_argument('--inputs-manifest',type=Path,default=INPUTS);a=ap.parse_args()
    dest=a.dest if a.dest else a.run/'analysis_persisted_phi_hidden_newton'
    result=analyze(a.run.resolve(),dest.resolve(),a.inputs_manifest.resolve(),a.initial_run.resolve(),probe_run=a.probe_run.resolve())
    print(dict(dest=str(dest),terminal=result['state']['endpoint']['status']))


if __name__=='__main__':main()
