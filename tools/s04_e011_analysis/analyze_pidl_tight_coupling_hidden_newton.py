#!/usr/bin/env python3
"""Saved-array analysis of one-hidden-step / Newton closed-pair coupling.

No local model loading/forward, training, SVD, solve, SSH or new FEM. Actual
candidate observations are distinct from accepted closed-pair endpoints.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize, SymLogNorm
from matplotlib.ticker import FormatStrFormatter
from analyze_pidl_head_newton import (BASE,INPUTS,ROOT,ACTIVE_LOG_FLOOR,read_json,record,
    worker_output,fields,verify_four,finite_range,panel)
from analyze_pidl_hidden_newton import hidden_change_check
from analyze_pidl_block_diagnosis import independent_operator,q4_fields,dump,sha
from analyze_pidl_learned_hidden_newton import finite_readout,replay,write_csv,GRAD_KEYS

INITIAL_RUN=BASE/'runs/pf_s04e011_learnednewton_e2dc61d_20261018T125034Z_production'
BASELINE_RUN=BASE/'runs/pf_s04e011_persistphi_f72434a_20261019T112844Z_production'
GTOL=1e-10
ENERGY_MARGIN=1e-10
PREVIOUS_ENERGY=.005267089573071509
METHODS=['FEM','preceding_baseline','new_last_closed']
LABELS=['conditional FEM','preceding persisted-Phi terminal','new last CLOSED endpoint']
SCOPE=('Frozen FEM/PIDL c20s4 peak, physical cycle20/substep4/rawstep99/U=.11999988, native Q4/2x2GP, eta=0. '
       'Same unique e2dc learned-head initial network and audit-saved actual Phi/T; no initial SVD/reconstruction. '
       'Mechanical damage is exact conditional FEM outer18 damage, original UV boundary and Smooth B0 anchor are fixed. '
       'Intervention combines one completed hidden L-BFGS step with immediate Newton correction and per-pair L-BFGS history reset; '
       'not true variable projection or an isolated cadence ablation. Only head-closed complete pairs may become subsequent starts/final endpoints. '
       'All actual candidates are retained, including failed-head observations; no FEM-error endpoint selection. '
       'No whole-network convergence/capacity, physical-teacher, coupled fatigue-evolution or equal-cost optimizer ranking claim. '
       'RAW psi+ in fully degraded regions is secondary to ACTIVE g(d)psi+.')


def js_source(path,role,sources):
    record(path,role,sources);return read_json(path)


def valid_digest(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def validate_budget(info,phase):
    expected=40 if phase=='probe' else 325
    phase_seconds=60 if phase=='probe' else 540
    for key,value in [('prior_evaluations',0),('new_probe_production_cap',365),('total_prior_plus_new_cap',365),
                      ('new_probe_production_deadline_seconds',600),('cap',expected),('deadline_seconds',phase_seconds)]:
        if info.get(key)!=value:raise ValueError('Bound original budget mismatch: '+key)
    if info.get('prior_elapsed_seconds') is not None or info.get('cumulative_elapsed_seconds_claim') is not False:
        raise ValueError('Prior elapsed time unknown; no cumulative wall-time claim is allowed')
    if not isinstance(info.get('evaluations'),int) or not 0<=info['evaluations']<=expected:
        raise ValueError('Phase energy/gradient count outside declared allowance')


def valid_basis_name(name):
    return name=='initial' or (name.startswith('hidden_') and name[7:].isdigit() and 1<=int(name[7:])<=8)


def basis_folder(case,reference):
    """Map a remote pointer to retrieved small metadata; never rebuild missing Phi."""
    parts=Path(reference).parts
    if len(parts)<2 or parts[-2]!='bases' or not valid_basis_name(parts[-1]):
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
        elapsed_seconds=info.get('elapsed_seconds'),new_probe_production_cap=365,prior_evaluations=0,
        deadline_seconds=60,cumulative_wall_time_claim=False,scope='New-allocation repeated actual readouts of one fixed saved Phi and network, not optimizer or capacity evidence')


def field_figures(out,inp,geo,op,physical,gp,provenance,status):
    N,_,w,_=geo;c=inp['cells'];polygons=inp['nodes'][c];mean=lambda a:np.sum(w*a,axis=1)/w.sum(1)
    quantities=[('u','horizontal u'),('v','vertical v'),('raw','RAW psi+'),('active','ACTIVE g(d)psi+')]
    fig,axs=plt.subplots(4,3,figsize=(12.5,13.4),layout='constrained',squeeze=False)
    for i,(key,label) in enumerate(quantities):
        vals={name:mean(gp[name][key] if key in ['raw','active'] else op.interp(f[key],c,N)) for name,f in physical.items() if name in METHODS}
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
    fig.suptitle('FEM / preceding baseline / new CLOSED PIDL c20s4 | exact same FEM damage and boundary',fontsize=11)
    save(fig,out/'c20_tight_coupling_fields.png','FEM-first preceding-baseline/new-closed maps of u/v/raw/active. The new terminal is the actual last CLOSED identity, not the stage nearest FEM. '
        'UV uses linear physical cell means. Raw/active use log10(max(GP/Jacobian-weighted Q4 cell mean,1e-12)) with no upper clipping. '
        'Each row has a common scale across its methods; physical full-GP metric arrays remain untransformed. Partial/unclosed terminal columns are excluded. An explicit rollback to the latest closed pair is allowed; its identity is verified and candidates remain separate in stage tables.',provenance)
    pairs=[('preceding_baseline','FEM','Preceding baseline - FEM'),('new_last_closed','FEM','New last CLOSED - FEM'),('new_last_closed','preceding_baseline','New CLOSED - preceding baseline')]
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
    fig.suptitle('PIDL c20s4 physical signed errors | baseline/FEM, new/FEM, new/baseline',fontsize=11)
    save(fig,out/'c20_tight_coupling_errors.png','Full-domain signed physical Q4 cell-mean differences; no field values are clipped or replaced by logged differences. '
        'UV errors have linear colour scales. Raw/active physical errors use symmetric-log colour normalization with fixed linear threshold1e-12; colourbar ticks remain physical values. '
        'Each row shares one symmetric scale across all three differences and five explicit numeric ticks. Full-GP errors/correlations/integrals remain authoritative. '
        'RAW in fully degraded zones is a secondary diagnostic; active-energy agreement is separately measured.',provenance)



def probe_evidence(run,sources,source_fields):
    """Admission misses are descriptive/inconclusive, not an invented passed probe."""
    case=worker_output(run)/'c20_s4';rp=case/'result.json'
    if rp.exists() and read_json(rp).get('status')=='probe_passed':
        return probe_stability(run,sources,source_fields)
    records=[]
    for name in ['initial_learned_head','probe_repeat_1','probe_repeat_2']:
        path=case/'readouts'/(name+'_actual.json')
        if not path.exists():continue
        row=js_source(path,'unadmitted actual probe observation '+name,sources);identity=readout_identity(row,case,sources)
        identity['independently_checked_source_fields_maxabs']=max(float(np.max(np.abs(identity['_saved_fields'][k]-source_fields[k]))) for k in ['u','v','d'])
        if identity['independently_checked_source_fields_maxabs']>1e-12:raise ValueError('Unadmitted probe has physical source-field mismatch')
        identity.pop('_saved_fields');identity.pop('_force');records.append(identity)
    evidence={}
    for name in ['source_reproduction','probe_admission','probe_repetitions']:
        path=case/(name+'.json')
        if path.exists():evidence[name]=js_source(path,'unadmitted probe '+name,sources)
    return dict(status='unadmitted_or_partial_probe',run=str(run),readouts=records,observations=evidence,
        threshold_unchanged=GTOL,promotion_allowed=False,
        scope='No passed same-Phi admission result; observed vectors are preserved without promoting a production efficacy result')


def save(fig,path,caption,provenance):
    fig.savefig(path,dpi=165);plt.close(fig)
    path.with_suffix('.md').write_text('# '+path.stem+'\n\n'+caption+'\n\n## Data provenance\n\n'+provenance+
        '\n\n## How to read\n\n'+caption+'\n\n## Limitation\n\n'+SCOPE+
        ' Raw parameter gradients, current-Phi projected gradients and global nodal force have separate coordinate spaces. '
        'Different current bases do not give a common coordinate infinity norm. Small energy changes or a closed head do not certify FEM-field recovery. '
        'Missing observations remain gaps; candidate observations are never promoted to closed endpoints by field error. '
        'Large actual Phi/models may remain remotely archived; small saved-array scoring never reconstructs missing Phi.\n',encoding='utf-8')


def classify_checkpoint(label,row):
    if label=='initial':
        if row.get('checkpoint_kind')!='initial' or row.get('pair')!=0 or row.get('pair_completed') is not True or row.get('retained_closed_endpoint') is not True:
            raise ValueError('Invalid initial closed-state metadata')
        if row['conditioned_head_gradient_inf']>GTOL:raise ValueError('Initial head is not closed')
        return 'initial_closed'
    kind,index=label.split('_');pair=int(index)
    if kind not in ['hidden','head'] or not 1<=pair<=8 or row.get('pair')!=pair:raise ValueError('Invalid candidate pair identity')
    if kind=='hidden':
        if row.get('checkpoint_kind')!='hidden_candidate' or row.get('retained_closed_endpoint') is not False:
            raise ValueError('A hidden candidate can never be a closed terminal')
        if row.get('pair_completed') and row.get('completed_pair_head_checkpoint')!='head_'+index:
            raise ValueError('Hidden candidate completed-pair link missing')
        return 'hidden_candidate_in_closed_pair' if row.get('pair_completed') else 'hidden_candidate'
    if row.get('retained_closed_endpoint') is True:
        if row.get('checkpoint_kind')!='closed_head' or row.get('pair_completed') is not True or row['conditioned_head_gradient_inf']>GTOL:
            raise ValueError('Claimed CLOSED head failed original actual-gradient contract')
        return 'closed_head'
    if row.get('checkpoint_kind')!='head_candidate' or row.get('pair_completed') is not False:
        raise ValueError('Invalid unaccepted head-candidate metadata')
    return 'head_candidate_unaccepted'


def select_last_closed(classifications,declared):
    closed=[name for name,kind in classifications if kind in ['initial_closed','closed_head']]
    if not closed or declared!=closed[-1]:raise ValueError('Terminal must match LAST chronological CLOSED complete pair, never candidate/best field')
    return closed[-1]


def terminal(run,sources):
    folder=worker_output(run)/'c20_s4';path=folder/'result.json'
    if not path.exists():return folder,dict(status='missing',terminal_readout_verified=False)
    info=js_source(path,'tight coupling terminal result',sources)
    if (info.get('cycle'),info.get('substep'),info.get('step'))!=(20,4,99):raise ValueError('Wrong terminal state')
    validate_budget(info,'production')
    for key in ['damage_output_row_unchanged','Smooth_B0_anchor_unchanged','mechanical_damage_exact_FEM','boundary_unchanged']:
        if info.get(key) is not True:raise ValueError('Frozen terminal contract missing '+key)
    for key in ['history_commits','rollout_steps','ridge']:
        if info.get(key)!=0:raise ValueError('Unexpected physical update '+key)
    if info.get('current_raw_columns')!=401 or info.get('initial_rank')!=386 or info.get('dynamic_current_feature_basis') is not True or info.get('old_restricted_span_used') is not False:
        raise ValueError('Actual current full401 policy changed')
    for key,value in [('max_hidden_pairs',8),('hidden_total_cap',80),('hidden_step_cap',40),('gradient_inf_tolerance',GTOL)]:
        if info.get(key)!=value:raise ValueError('Coupling policy mismatch '+key)
    if not 0<=info.get('hidden_total_evaluations',np.inf)<=80:raise ValueError('Hidden80-call cap exceeded')
    if info.get('true_variable_projection') is not False or info.get('hidden_history_reset_each_pair') is not True or info.get('cadence_and_history_reset_combined') is not True:
        raise ValueError('Cadence plus history-reset intervention identity missing')
    source=info.get('source_reproduction',{})
    if source.get('passed') is not True or source.get('initial_rank')!=386 or source.get('energy_abs_error',np.inf)>1e-10 or source.get('actual_current_head_gradient_inf',np.inf)>GTOL:
        raise ValueError('Common initial source admission failed')
    verified=info.get('status')=='completed' and info.get('actual_network') is not None
    if verified:finite_readout(info['actual_network'])
    return folder,dict(status=info.get('status','unknown'),terminal_readout_verified=verified,worker=info,
        final_head_closed=bool(verified and info['actual_network']['conditioned_head_gradient_inf']<=GTOL),
        excluded_reason=None if verified else 'Missing/partial terminal readout; saved candidates and closed checkpoints remain descriptive only')


def decision(state):
    endpoint=state['endpoint'];info=endpoint.get('worker',{});metrics=state['metrics']
    if state.get('probe_stability',{}).get('status')!='verified_three_same_actual_Phi':
        return dict(efficacy='inconclusive',primary_met=False,conclusion='Same-Phi source/gradient admission was not completed; no promoted efficacy result. Attempted observations remain descriptive.')
    if not endpoint.get('terminal_readout_verified') or 'new_last_closed' not in metrics:
        return dict(efficacy='inconclusive',primary_met=False,conclusion='No verified restored head-closed terminal readout; no promoted efficacy result.')
    stages=state.get('producer_stages',[])
    closed_count=sum(r['classification']=='closed_head' for r in state['stage_records'])
    all_closed=all(not s.get('nonzero_completed_hidden_step',False) or s.get('pair_completed',False) for s in stages)
    closure_miss=bool(info.get('head_closure_failure_encountered'))
    operational=bool(endpoint['final_head_closed'] and not closure_miss and all_closed)
    if closed_count!=info.get('closed_pairs') or all_closed!=info.get('all_nonzero_hidden_steps_closed') or operational!=info.get('operational_coupling_closure'):
        raise ValueError('Producer closed-pair/coupling summary differs from actual stage metadata')
    hidden=state['hidden_change'];changed=bool(hidden.get('actual_hidden_changed') and hidden.get('verified_from_digest_and_delta'))
    eligible=bool(closed_count>0 and changed and endpoint['final_head_closed'])
    if eligible!=info.get('coupling_endpoint_eligible'):raise ValueError('Producer coupling-endpoint eligibility mismatch')
    gain=metrics['preceding_baseline']['E_el']-metrics['new_last_closed']['E_el'];source_gain=metrics['common_initial']['E_el']-metrics['new_last_closed']['E_el']
    if abs(info.get('previous_same_start_terminal_E_el',np.inf)-metrics['preceding_baseline']['E_el'])>1e-12:
        raise ValueError('Previous comparator energy is not the bound preceding terminal')
    if info.get('directional_margin')!=ENERGY_MARGIN:raise ValueError('Directional energy margin changed')
    primary=bool(operational and eligible and gain>ENERGY_MARGIN)
    verdict='inconclusive' if not operational else ('supports_bounded_directional_gain' if primary else 'negative_for_this_bounded_policy')
    return dict(efficacy=verdict,primary_met=primary,operational_coupling_closure=operational,endpoint_eligible=eligible,
        head_closure_failure_encountered=closure_miss,all_nonzero_hidden_steps_closed=all_closed,closed_pairs=closed_count,
        hidden_actual_changed=changed,preceding_energy_minus_new=gain,original_directional_margin=ENERGY_MARGIN,
        common_initial_energy_minus_new=source_gain,source_relative_energy_reduction=source_gain/metrics['common_initial']['E_el'],
        terminal_actual_Phi_gradient_inf=info['actual_network']['conditioned_head_gradient_inf'],
        conclusion=('A coupling/actual-head closure obstruction prevents judging efficacy; retained closed-pair energy remains descriptive.' if not operational else
                    'The combined cadence/history-reset policy resolves the original directional energy margin against the preceding same-start terminal.' if primary else
                    'This valid bounded policy does not resolve the declared directional improvement with actual hidden movement.')+
                    ' No candidate or FEM-field metric rescues the primary. This does not establish full-network convergence, capacity or FEM evolution reproduction.')


def stage_figures(out,state,provenance):
    rows=state['stage_metrics'];x=np.arange(len(rows));names=[r['stage'].replace('_','') for r in rows]
    def vals(key):return np.array([r.get(key,np.nan) if r.get(key) is not None else np.nan for r in rows],float)
    closed=np.array([r.get('retained_closed_endpoint',False) for r in rows])
    actual=np.array([r.get('actual_observed',False) for r in rows])
    fig,axs=plt.subplots(2,3,figsize=(17,9),layout='constrained')
    specs=[('E_el','Actual elastic energy'),('free_u_l2','Independent global free-u force L2'),('uv_mass_rel_L2','UV mass relative L2 / FEM'),
           ('uv_H1_rel','Q4 gradient/H1 error / FEM'),('active_vs_FEM_relative_L2','ACTIVE weighted relative L2 / FEM'),('conditioned_head_gradient_inf','Saved actual-Phi head gradient infinity')]
    for ax,(key,title) in zip(axs.flat,specs):
        y=vals(key);ax.plot(x,y,'-',color='.7',lw=.8);ax.scatter(x[actual&~closed],y[actual&~closed],facecolors='none',edgecolors='#D55E00',marker='o',label='actual candidate; not terminal')
        ax.scatter(x[closed],y[closed],color='#0072B2',marker='s',s=25,label='accepted CLOSED endpoint')
        ax.set_xticks(x,names,rotation=70,fontsize=7);ax.set_title(title,fontsize=10);ax.grid(alpha=.2)
        if key=='E_el':ax.axhline(state['metrics']['preceding_baseline']['E_el']-ENERGY_MARGIN,color='k',ls=':',label='preceding baseline E - 1e-10')
        if key=='conditioned_head_gradient_inf':ax.set_yscale('log');ax.axhline(GTOL,color='k',ls='--',label='unchanged head target1e-10')
    axs[0,0].legend(fontsize=7);axs[1,2].legend(fontsize=7)
    fig.suptitle('PIDL c20s4: ALL observed candidates and accepted CLOSED pairs in execution order; absent stages are gaps')
    save(fig,out/'tight_coupling_stage_decision.png','All17 planned positions: common initial, hidden1/head1 through hidden8/head8. Hollow orange markers are actual candidates, never terminal-qualified by low energy/FEM error. '
        'Blue squares are retained CLOSED complete-pair endpoints. Missing stages are gaps, not zero. The primary energy line is preceding same-start terminal minus1e-10; the head line is the unchanged actual-Phi gradient target. '
        'Efficacy remains inconclusive if the coupling closure contract cannot be completed, even if an earlier retained closed point has lower energy.',provenance)
    fig,axs=plt.subplots(2,2,figsize=(16,9),layout='constrained')
    for ax,norm in zip(axs[0],['l2','inf']):
        for group,col in [('hidden','#0072B2'),('uv_head','#D55E00')]:ax.plot(x,vals(group+'_gradient_'+norm),'o-',ms=3,color=col,label=group+' raw parameter')
        ax.set_title('Raw Eel parameter gradients '+norm);ax.set_yscale('log');ax.legend(fontsize=8)
    for ax,key,title in [(axs[1,0],'conditioned_head_gradient_inf','Current saved-Phi projected-head gradient'),(axs[1,1],'free_u_l2','Independent physical nodal free-u force')]:
        ax.plot(x,vals(key),'o-',ms=3,color='#009E73');ax.scatter(x[closed],vals(key)[closed],marker='s',color='#0072B2',s=25);ax.set_title(title);ax.set_yscale('log')
    axs[1,0].axhline(GTOL,color='k',ls='--')
    for ax in axs.flat:ax.set_xticks(x,names,rotation=70,fontsize=7);ax.grid(alpha=.2)
    fig.suptitle('PIDL c20s4: parameter, saved-Phi coordinate and nodal physical gradient spaces are separate')
    save(fig,out/'tight_coupling_gradient_spaces.png','Every actual candidate/closed stage in execution order, missing values left blank. Upper panels use original architecture raw-Eel hidden and UV-head gradients; '
        'lower panels show current actual-Phi projected head and independent physical nodal residual. Blue square markers identify accepted closed endpoints. '
        'The actual-Phi gradient after hidden movement has new current coordinates and is not a common physical norm. The1e-10 line applies solely to the head criterion. Log axes do not display exact zero; exact values remain in CSV.',provenance)


def analyze(run,out,probe_run,inputs_manifest=INPUTS,initial_run=INITIAL_RUN,baseline_run=BASELINE_RUN,render=True):
    if out.exists():raise FileExistsError('Refuse overwrite: '+str(out))
    out.mkdir(parents=True);sources=[];manifest=js_source(inputs_manifest,'bound input manifest',sources)
    item=next(x for x in manifest['cases'] if x['cycle']==20);ip=Path(item['path'])
    if ip.stat().st_size!=item['bytes'] or sha(ip)!=item['sha256']:raise ValueError('Input size/SHA mismatch')
    record(ip,'conditional accepted FEM c20 outer18 state',sources);record(Path(__file__),'offline analyzer',sources)
    with np.load(ip,allow_pickle=False) as z:inp={k:z[k] for k in z.files}
    op,oppath=independent_operator(ROOT);record(oppath,'independent native NumPy Q4 operator',sources);geo=op.q4_geometry(inp['nodes'],inp['cells']);N,B,w,_=geo
    n=len(inp['nodes']);mass=np.zeros(n)
    for j in range(4):np.add.at(mass,inp['cells'][:,j],np.sum(w*N[:,j],axis=1))
    fem={k:inp[k+'_fem'].astype(float) for k in ['u','v','d']};ref=q4_fields(fem,inp,op,geo)
    native_error=float(np.max(np.abs(ref['_nodal_force'].reshape(-1)-inp['ru_fem'].reshape(-1))))
    if native_error>1e-10 or ref['independent_free_u_l2']>1e-8:raise ValueError('Independent native FEM force contract failed')
    metrics={};physical={'FEM':fem};gps={'FEM':ref};checks={}
    metrics['FEM'],_=replay(fem,fem,inp,op,geo,ref,mass)
    for name,oldrun in [('common_initial',initial_run),('preceding_baseline',baseline_run)]:
        folder=worker_output(oldrun)/'c20_s4';info=js_source(folder/'result.json',name+' accepted result',sources)
        if info.get('status')!='completed' or info.get('actual_network') is None or info.get('rolled_back'):raise ValueError('Comparator is not its accepted actual terminal')
        f=fields(folder/'fields.npz',n,sources,name+' accepted fields');r,q=replay(f,fem,inp,op,geo,ref,mass);checks[name]=verify_four(info['actual_network'],r)
        metrics[name]=r;physical[name]=f;gps[name]=q
    if abs(metrics['preceding_baseline']['E_el']-PREVIOUS_ENERGY)>1e-12:raise ValueError('Wrong preceding baseline accepted terminal')
    probe=probe_evidence(probe_run,sources,physical['common_initial'])
    folder,endpoint=terminal(run,sources);info=endpoint.get('worker',{})
    stage_metrics=[];stage_records=[];classes=[];saved_fields={};saved_gps={};basis_records=[]
    stages=['initial']+[f'{kind}_{pair}' for pair in range(1,9) for kind in ['hidden','head']]
    for seq,name in enumerate(stages):
        cp=folder/'checkpoints'/name
        if not (cp/'result.json').exists() or not (cp/'fields.npz').exists():
            stage_metrics.append(dict(sequence=seq,stage=name,actual_observed=False,status='missing_or_not_retrieved',retained_closed_endpoint=False));continue
        raw=js_source(cp/'result.json','actual checkpoint/candidate '+name,sources);finite_readout(raw);kind=classify_checkpoint(name,raw)
        link=readout_identity(raw,folder,sources);f=fields(cp/'fields.npz',n,sources,'actual fields '+name)
        if max(float(np.max(np.abs(link['_saved_fields'][k]-f[k]))) for k in ['u','v','d'])>1e-12:raise ValueError('Actual readout/checkpoint field identity mismatch')
        del link['_saved_fields'];r,q=replay(f,fem,inp,op,geo,ref,mass);four=verify_four(raw,r)
        link['independent_nodal_force_maxabs_difference']=float(np.max(np.abs(link.pop('_force')-q['_nodal_force'])))
        if name=='initial':
            if max(float(np.max(np.abs(f[k]-physical['common_initial'][k]))) for k in ['u','v','d'])>1e-12:raise ValueError('Common initial field mismatch')
            for key in ['basis_phi_sha256','hidden_sha256','bound_weights_sha256']:
                if probe.get('readouts') and link[key]!=probe['readouts'][0][key]:raise ValueError('Probe and production actual initial identity mismatch')
        retained=kind in ['initial_closed','closed_head'];classes.append((name,kind));saved_fields[name]=f;saved_gps[name]=q
        stage_metrics.append(dict(sequence=seq,stage=name,actual_observed=True,status='verified_actual',classification=kind,
            pair=raw['pair'],pair_completed=raw['pair_completed'],retained_closed_endpoint=retained,**r,**{k:raw[k] for k in GRAD_KEYS}))
        stage_records.append(dict(stage=name,classification=kind,readout=raw,identity=link,independent_four_checks=four,metrics=r))
    terminal_link=None
    if endpoint.get('terminal_readout_verified'):
        label=select_last_closed(classes,info.get('last_closed_checkpoint'))
        if label!=info.get('last_verified_checkpoint'):raise ValueError('Last verified endpoint is not last CLOSED complete pair')
        f=fields(folder/'fields.npz',n,sources,'restored latest CLOSED terminal fields');r,q=replay(f,fem,inp,op,geo,ref,mass);checks['observed_restored_terminal']=verify_four(info['actual_network'],r)
        if max(float(np.max(np.abs(f[k]-saved_fields[label][k]))) for k in ['u','v','d'])>1e-12:raise ValueError('Terminal differs from chronological latest CLOSED endpoint')
        terminal_link=readout_identity(info['actual_network'],folder,sources)
        if max(float(np.max(np.abs(terminal_link['_saved_fields'][k]-f[k]))) for k in ['u','v','d'])>1e-12:raise ValueError('Final readout fields differ from restored terminal')
        del terminal_link['_saved_fields'];terminal_link['independent_nodal_force_maxabs_difference']=float(np.max(np.abs(terminal_link.pop('_force')-q['_nodal_force'])))
        metrics['observed_restored_terminal']=r
        if endpoint['final_head_closed']:metrics['new_last_closed']=r;physical['new_last_closed']=f;gps['new_last_closed']=q
        if probe.get('evaluations',0)+info['evaluations']>365:raise ValueError('Current probe plus production allocation exceeded365')
    for path in sorted(folder.glob('bases/*/metadata.json')):
        value=js_source(path,'persisted actual basis metadata',sources);validate_basis_metadata(value,path.parent.name=='initial');basis_records.append(dict(path=str(path),metadata=value))
    for path in sorted(folder.glob('head_stage_*/basis_ref.json')):
        link=js_source(path,'head actual-Phi reference',sources);meta=js_source(basis_folder(folder,link['basis_ref'])/'metadata.json','head linked basis metadata',sources)
        if link.get('phi_sha256')!=meta['phi_sha256'] or link.get('transform_sha256')!=meta['transform_sha256']:raise ValueError('Head shared-space reference mismatch')
        basis_records.append(dict(path=str(path),shared_reference=link))
    producer={}
    for name in ['stages','accepted','gradient_readouts','trace']:
        path=folder/(name+'.json')
        if path.exists():producer[name]=js_source(path,'producer '+name,sources)
    if endpoint.get('terminal_readout_verified') and 'stages' not in producer:raise ValueError('Completed arm missing chronological pair records')
    hidden=hidden_change_check(info)
    if endpoint.get('terminal_readout_verified') and not hidden['verified_from_digest_and_delta']:raise ValueError('Missing actual hidden-change proof')
    state=dict(cycle=20,substep=4,step=99,U=.11999988,FEM_reference=item['fem'],endpoint=endpoint,metrics=metrics,
        independent_four_checks=checks,stage_metrics=stage_metrics,stage_records=stage_records,current_bases=basis_records,
        probe_stability=probe,terminal_identity=terminal_link,last_closed_checkpoint=info.get('last_closed_checkpoint'),
        hidden_change=hidden,native_FEM_force_maxabs=native_error,producer_stages=producer.get('stages',[]),producer_records=producer,
        budget_semantics='New prior0 + probe40/60s + production325/540s <=365 calls/600s this round. Historical calls are not erased; no cumulative wall-time claim. In-flight work may finish after no-new-work cutoff.')
    state['decision']=decision(state)
    arrays=dict(nodes=inp['nodes'],cells=inp['cells'],GP_weights=w)
    for name,f in {**physical,**saved_fields}.items():
        for key in ['u','v','d']:arrays[name+'_'+key]=f[key]
        q=saved_gps.get(name,gps.get(name))
        for key in ['raw','active']:arrays[name+'_'+key+'_gp']=q[key]
    np.savez_compressed(out/'scored_fields_gp.npz',**arrays)
    write_csv(out/'metrics.csv',[dict(method=k,**v) for k,v in metrics.items()]);write_csv(out/'stage_metrics.csv',stage_metrics)
    result=dict(protocol='S04-E011-tight-coupling-offline-r1',run=str(run),baseline_run=str(baseline_run),initial_run=str(initial_run),
        state=state,sources=sources,claim_boundary=SCOPE)
    dump(out/'summary.json',result)
    provenance=f'New Run {run.name}; preceding baseline {baseline_run.name}; common initial {initial_run.name}; c20s4 conditional FEM outer18 bound input {ip}. Exact metrics, states and SHA256 sources: summary.json / metrics.csv / stage_metrics.csv / scored_fields_gp.npz.'
    if render:stage_figures(out,state,provenance);field_figures(out,inp,geo,op,physical,gps,provenance,endpoint)
    (out/'README_analysis.md').write_text('# Tight PIDL hidden/Newton coupling at frozen c20s4\n\n'+SCOPE+'\n\n## Data provenance\n\n'+provenance+
        '\n\n## How to read\n\nFour figures show every actual candidate and accepted closed stage, separate gradient spaces, FEM/preceding-baseline/new-last-closed maps, and signed physical differences. '
        'The preceding baseline is its accepted terminal, not the common initial. Both starts reproduce the unique e2dc learned-head source. All17 planned positions remain named; missing or partially retrieved observations are not zero. '
        'Only initial/closed_head can be retained; a hidden point remains a candidate even when its following head closes the pair. Original full-GP Q4 metrics are untransformed. '
        'UV colour scales are linear; raw/active field displays use log10(max(weighted cell mean,1e-12)); physical signed raw/active differences use symmetric-log normalisation with threshold1e-12 and numeric physical ticks.\n\n'
        '## Limitation\n\n'+state['decision']['conclusion']+' '+state['budget_semantics']+' Actual Phi/models can remain remote; SHA/hidden/reference links and small saved fields/forces/vectors are used locally without network forward, SVD, solve or reconstructing absent matrices. '
        'Producer weight digests are identity evidence; this analyzer does not independently load full model weights. Actual source Phi is the audit-captured matrix, not a retroactive claim that older runs saved complete identical Phi. '
        'The primary compares baseline energy minus new closed-terminal energy against the original1e-10 margin with actual hidden movement and operational closure; field metrics do not rescue it.\n',encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--probe-run',type=Path,required=True);p.add_argument('--dest',type=Path)
    p.add_argument('--baseline-run',type=Path,default=BASELINE_RUN);p.add_argument('--initial-run',type=Path,default=INITIAL_RUN);p.add_argument('--inputs-manifest',type=Path,default=INPUTS);a=p.parse_args()
    out=a.dest or a.run/'analysis_tight_coupling'
    result=analyze(a.run.resolve(),out.resolve(),a.probe_run.resolve(),a.inputs_manifest.resolve(),a.initial_run.resolve(),a.baseline_run.resolve())
    print(result['state']['decision'])


if __name__=='__main__':main()
