"""D014 no-optimizer replay and full/region summary. Never chooses a new head."""
import json
from pathlib import Path
import numpy as np
from s04_e024_field_budget import (PROFILES, STATES, GUARDS, InvalidEvidence,
    quantize_head, safe_json, finite,preconditioner,digest_array,branch_change,ratio_norm,BUDGETS,REGIONS,
    qualify_saved_seed,select_initial_incumbent)
from s04_e024_field_runtime import sha,write_json,code_tree_sha


def close_record(actual,saved):
    if isinstance(actual,dict):
        if set(actual)!=set(saved):raise InvalidEvidence('replay record schema')
        for k in actual:close_record(actual[k],saved[k])
    elif isinstance(actual,(list,tuple,np.ndarray)):
        if len(actual)!=len(saved):raise InvalidEvidence('replay record length')
        for a,b in zip(actual,saved):close_record(a,b)
    elif isinstance(actual,(bool,str)) or actual is None:
        if actual!=saved:raise InvalidEvidence('replay flag/value')
    else:
        if not np.isfinite(float(saved)):raise InvalidEvidence('nonfinite stored metric')
        np.testing.assert_allclose(actual,saved,rtol=1e-12,atol=0)


def replay_profile(adapter,folder,eta,strict,check=lambda:None,require_initialization=False,saved_seed=None):
    """Rebuild each visited proxy once and replay every recorded quantized field."""
    metrics=adapter.metrics;theta0=adapter.theta;current=theta0.copy();fields=adapter.origin
    final=json.loads((folder/'final.json').read_text())
    events=[json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines()]
    initialization=None;current_ev=metrics.evaluate(fields);current_source='E023_ORIGIN';event_start=0
    if events and events[0]['kind']=='initialization':
        if saved_seed is None:
            if not hasattr(adapter,'d012_head'):raise InvalidEvidence('seeded replay missing saved head')
            saved_seed=qualify_saved_seed(adapter,metrics,adapter.d012_head,check,
                provenance=getattr(adapter,'d012_provenance',None))
        selected,expected=select_initial_incumbent(adapter,metrics,saved_seed)
        expected=safe_json(expected);close_record(expected,events[0])
        initialization=expected;current=selected['head'].copy();fields=selected['fields']
        current_ev=selected['evaluation'];current_source=selected['record']['source'];event_start=1
    elif require_initialization:
        raise InvalidEvidence('seeded replay missing first initialization event')
    if require_initialization and initialization is None:
        raise InvalidEvidence('seeded replay initialization unavailable')
    outer=-1;trials=0;solves=0;accepted=0;next_k=0;was_accepted=False
    direction=None;pack=None;last_feasible=None
    for ev in events[event_start:]:
        check()
        if ev['kind']=='solver':
            if outer>=0 and not was_accepted:raise InvalidEvidence('continued after rejected/failed profile')
            outer+=1;solves+=1
            if outer>=3 or ev['outer']!=outer:raise InvalidEvidence('solver count/order')
            np.testing.assert_array_equal(np.array(ev['incumbent'],dtype=theta0.dtype),current)
            pack=adapter.proxy(fields,metrics,check)
            if pack.fingerprint()!=ev['model_sha256']:raise InvalidEvidence('proxy model fingerprint')
            direction=None if ev['direction'] is None else np.array(ev['direction'])
            info=ev['info'];last_feasible=bool(info['feasible'])
            transform=info.get('preconditioner_transform_file')
            if transform is None:raise InvalidEvidence('missing full preconditioner transform')
            name=f"outer_{outer}_preconditioner.npy"
            if transform['path']!=name or sha(folder/name)!=transform['sha256']:
                raise InvalidEvidence('preconditioner transform file identity')
            t=np.load(folder/name,allow_pickle=False)
            expected_t,spectrum=preconditioner(pack,metrics.scales_sq)
            if digest_array(t)!=transform['array_sha256']:raise InvalidEvidence('transform array identity')
            np.testing.assert_array_equal(t,expected_t)
            close_record(safe_json(spectrum),info['preconditioner'])
            if direction is not None:
                coordinates=np.asarray(info['solver_coordinates']);finite(coordinates)
                if coordinates.shape!=(theta0.size,):raise InvalidEvidence('full solver coordinates')
                np.testing.assert_allclose(np.einsum('ij,j->i',t,coordinates),direction,rtol=1e-12,atol=0)
            if direction is not None:
                if direction.shape!=(theta0.size,):raise InvalidEvidence('full-head direction schema')
                finite(direction)
                values=pack.values(direction)
                active=list(range(1,13 if strict else 7))+list(range(13,17))
                limits=np.r_[metrics.ceilings,eta*eta*metrics.scales_sq]
                scales=np.where(limits>0,limits,1.)
                valid=bool(np.max(((values-limits)/scales)[active])<=1e-8)
                if valid!=last_feasible:raise InvalidEvidence('proxy feasibility flag')
                if 'proxy_values' in info:close_record(values,info['proxy_values'])
            elif last_feasible:raise InvalidEvidence('missing feasible direction')
            next_k=0;was_accepted=False
        elif ev['kind']=='trial':
            if pack is None or direction is None or not last_feasible or was_accepted:
                raise InvalidEvidence('unadmitted or extra trial')
            if ev['outer']!=outer or ev['k']!=next_k or next_k>=9:
                raise InvalidEvidence('finite trial order')
            head=quantize_head(current+2.**(-next_k)*direction.reshape(theta0.shape),theta0.dtype)
            np.testing.assert_array_equal(head,np.array(ev['head'],dtype=theta0.dtype))
            step=(head.astype(float)-current.astype(float)).ravel()
            f=adapter.realize(head);adapter.check_identity()
            realization=adapter.check_realization(head,f,metrics)
            close_record(branch_change(f,metrics.origin),ev['branch_changed_GP_fraction'])
            actual_ev=metrics.evaluate(f)
            failures=metrics.violations(actual_ev,eta,strict)
            actual=(current_ev['guards']['uv_full']-actual_ev['guards']['uv_full'])/metrics.ceilings[0]
            pred=(pack.c[0]-pack.values(step)[0])/metrics.ceilings[0]
            ratio=actual/pred if pred>0 else -np.inf
            if actual<=1e-8 or pred<=1e-8 or ratio<.1:failures.append('insufficient_actual_or_predicted_gain')
            ok=not failures
            if ok!=ev['accepted'] or failures!=ev['failures']:raise InvalidEvidence('actual admission mismatch')
            close_record(safe_json(actual_ev),ev['actual'])
            close_record(safe_json(realization),ev['realization'])
            close_record(safe_json(float(actual)),ev['actual_reduction'])
            close_record(safe_json(float(pred)),ev['predicted_reduction'])
            close_record(safe_json(float(ratio)),ev['agreement_ratio'])
            close_record(pack.values(step),ev['proxy_values'])
            trials+=1;next_k+=1
            if ok:
                current=head;fields=f;current_ev=actual_ev
                current_source='solver_trial_outer_%d_k_%d'%(outer,next_k-1)
                accepted+=1;was_accepted=True
        else:raise InvalidEvidence('unknown trajectory event')
    counts=dict(solves=solves,trials=trials,accepted_steps=accepted)
    for k,v in counts.items():
        if final['counts'][k]!=v:raise InvalidEvidence('profile count mismatch')
    stop=final['counts']['stop']
    if metrics.ceilings[0]==0:
        if events[event_start:] or stop!='NO_CORRECTION_ALREADY_EXACT':raise InvalidEvidence('zero-UV stop branch')
    elif stop=='MAX_RELINEARIZATIONS':
        if solves!=3 or not was_accepted:raise InvalidEvidence('premature/extra outer stop')
    elif stop=='NO_PROXY_FEASIBLE_RETURN':
        if solves==0 or last_feasible or next_k:raise InvalidEvidence('proxy stop branch')
    elif stop=='ALL_NINE_REJECTED':
        if next_k!=9 or was_accepted:raise InvalidEvidence('backtracking stop branch')
    else:raise InvalidEvidence('unregistered stop rule')
    with np.load(folder/'final.npz',allow_pickle=False) as z:
        np.testing.assert_array_equal(z['original_head'],theta0)
        if initialization is not None:
            np.testing.assert_array_equal(z['initial_head'],np.asarray(initialization['selected']['head'],dtype=theta0.dtype))
        elif 'initial_head' in z.files:
            raise InvalidEvidence('legacy replay has unexpected initial head')
        np.testing.assert_array_equal(z['head'],current)
        for k in fields:np.testing.assert_array_equal(z[k],fields[k])
    report=adapter.physical_report(fields)
    close_record(safe_json(report),final['report'])
    if metrics.violations(metrics.evaluate(fields),eta,strict):raise InvalidEvidence('final actual policy')
    if final['eta']!=eta or final['strict'] is not strict:raise InvalidEvidence('profile label swap')
    if final['centre_digest']!=metrics.centre_digest:raise InvalidEvidence('cumulative centre moved')
    if initialization is not None:
        if 'initialization' not in final['counts'] or 'final_incumbent' not in final['counts']:
            raise InvalidEvidence('seeded profile receipt missing incumbent evidence')
        close_record(initialization,final['counts']['initialization'])
        expected_final=dict(source=current_source,head_sha256=digest_array(current),actual=current_ev,
            retained_initial_incumbent=accepted==0)
        close_record(safe_json(expected_final),final['counts']['final_incumbent'])
        counts.update(initialization=initialization,final_incumbent=safe_json(expected_final))
    elif 'initialization' in final['counts'] or 'final_incumbent' in final['counts']:
        raise InvalidEvidence('legacy profile contains seeded incumbent evidence')
    check();return dict(**counts,stop=stop,head=current,report=report)


def replay_state(adapter,root,state,check,expected_commit=None):
    case=root/'states'/state;meta=json.loads((case/'receipt.json').read_text())
    if meta.get('code_tree_sha256')!=code_tree_sha():raise InvalidEvidence('numeric worker code tree')
    if meta['state']!=state or (expected_commit is not None and meta['source_commit']!=expected_commit):raise InvalidEvidence('numeric worker source/state')
    if any(meta[k]!=0 for k in ('NN_optimizer_steps','original_checkpoint_writes','history_fatigue_damage_updates','remote_actions')):raise InvalidEvidence('numeric worker mutation receipt')
    if list(meta['profiles'])!=[x[0] for x in PROFILES]:raise InvalidEvidence('worker profile order')
    for p,h in meta['files'].items():
        if sha(case/p)!=h:raise InvalidEvidence('worker file hash '+p)
    if adapter.assets!=meta['assets']:raise InvalidEvidence('state/paired origin identity')
    with np.load(case/'origin.npz',allow_pickle=False) as z:
        for k,v in adapter.origin.items():np.testing.assert_array_equal(z[k],v)
    with np.load(case/'geometry.npz',allow_pickle=False) as z:
        for k in ('xy','conn','damage'):np.testing.assert_array_equal(z[k],adapter.data[k])
        np.testing.assert_array_equal(z['reference_uv'],adapter.data['equilibrated_uv'])
        np.testing.assert_array_equal(z['window'],adapter.window)
        if float(z['us'])!=adapter.us:raise InvalidEvidence('render scale')
    seeded=meta.get('seeded_incumbent_protocol',False)
    if type(seeded) is not bool:raise InvalidEvidence('seeded incumbent protocol flag')
    saved_seed=None
    if seeded:
        if not hasattr(adapter,'d012_head'):raise InvalidEvidence('seeded worker missing saved head')
        saved_seed=qualify_saved_seed(adapter,adapter.metrics,adapter.d012_head,check,
            provenance=getattr(adapter,'d012_provenance',None))
        if 'saved_seed_qualification' not in meta:raise InvalidEvidence('missing saved seed qualification')
        close_record(safe_json(saved_seed['record']),meta['saved_seed_qualification'])
    results={};total_solves=total_trials=0
    for name,eta,strict in PROFILES:
        results[name]=replay_profile(adapter,case/name,eta,strict,check,
            require_initialization=seeded,saved_seed=saved_seed)
        for key in ('solves','trials','accepted_steps','stop'):
            if results[name][key]!=meta['profiles'][name][key]:raise InvalidEvidence('worker/profile count or stop mismatch')
        if seeded:
            close_record(results[name]['initialization'],meta['profiles'][name]['initialization'])
            close_record(results[name]['final_incumbent'],meta['profiles'][name]['final_incumbent'])
        total_solves+=results[name]['solves'];total_trials+=results[name]['trials']
    if total_solves>12 or total_trials>108 or total_solves!=meta['offline_solver_calls'] or total_trials!=meta['actual_candidate_trials']:raise InvalidEvidence('per-state compute counts')
    historical_fields=None if saved_seed is None else saved_seed['fields']
    if historical_fields is None:
        historical_fields=adapter.realize(adapter.d012_head.astype(adapter.theta.dtype))
    historical=adapter.physical_report(historical_fields)
    close_record(safe_json(historical),meta['D012_report'])
    a=results['strict_eta_0.3'];b=results['seven_guard_eta_0.3']
    ev={'guards':b['report']['guards'],'budget_q':b['report']['budget_q']}
    cross=adapter.metrics.violations(ev,.3,True)
    interpretation='observed candidate tradeoff, not an optimal frontier gap'
    if not cross and b['report']['guards']['uv_full']<a['report']['guards']['uv_full']:
        interpretation='seven-guard return is also thirteen-feasible; investigate finite-solver difference'
    adapter.final_identity();check()
    return dict(state=state,code_tree_sha256=code_tree_sha(),numeric_receipt_sha256=sha(case/'receipt.json'),
        input_manifest_sha256=manifest_sha(meta['files']),profiles={k:{x:y for x,y in v.items() if x!='head'} for k,v in results.items()},
        central_cross_guard_failures=cross,central_interpretation=interpretation,
        baseline=adapter.physical_report(adapter.origin),D012_report=historical,
        replayed_solvers=total_solves,replayed_trials=total_trials,new_optimizations=0,
        seeded_incumbent_protocol=seeded,
        saved_seed_qualification=None if saved_seed is None else safe_json(saved_seed['record']),
        scope='all recorded actual trials and saved endpoints replayed; no new candidate selected')


def manifest_sha(files):
    import hashlib
    return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def number(value,label,nonnegative=True):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value):
        raise InvalidEvidence('nonfinite/nonnumeric '+label)
    if nonnegative and value<0:raise InvalidEvidence('negative '+label)
    return value


def count(value,label,maximum):
    if type(value) is not int or not 0<=value<=maximum:raise InvalidEvidence('invalid integer count '+label)
    return value


def validate_counts(profile,origin_uv_error):
    solves=count(profile['solves'],'solves',3);trials=count(profile['trials'],'trials',27)
    accepted=count(profile['accepted_steps'],'accepted_steps',3);stop=profile['stop']
    if accepted>min(solves,trials) or trials>9*solves:raise InvalidEvidence('incoherent profile counts')
    if stop=='NO_CORRECTION_ALREADY_EXACT':valid=solves==trials==accepted==0 and origin_uv_error==0
    elif stop=='MAX_RELINEARIZATIONS':valid=solves==accepted==3 and accepted<=trials<=9*accepted
    elif stop=='NO_PROXY_FEASIBLE_RETURN':valid=solves>=1 and accepted==solves-1 and accepted<=trials<=9*accepted
    elif stop=='ALL_NINE_REJECTED':valid=solves>=1 and accepted==solves-1 and 9+accepted<=trials<=9*solves
    else:valid=False
    if not valid:raise InvalidEvidence('profile stop/count structure')
    return solves,trials


def validate_report(report,base=None,zero_change=False,allow_infinite_budget=False):
    """Validate every consumed physical number, including exact zero-scale policy."""
    if tuple(report['guards'])!=GUARDS or tuple(report['budget_components'])!=BUDGETS:
        raise InvalidEvidence('physical report guard/budget schema')
    for k,v in report['guards'].items():number(v,k)
    keys=[q+'_'+r for q in ('uv','strain','driver') for r in REGIONS]
    if set(report['region_metrics'])!=set(keys):raise InvalidEvidence('region report schema')
    mapped=[*GUARDS[:4],*GUARDS[7:11],GUARDS[11],GUARDS[12],GUARDS[5],GUARDS[6]]
    for key,guard in zip(keys,mapped):
        item=report['region_metrics'][key]
        if set(item)!=set(('error_integral','error_RMS','relative_L2','reference_integral','weight_sum')):
            raise InvalidEvidence('regional metric schema')
        for k in ('error_integral','error_RMS','reference_integral','weight_sum'):number(item[k],key+'.'+k)
        if item['weight_sum']<=0:raise InvalidEvidence('empty fixed region')
        close_record(item['error_integral'],report['guards'][guard])
        close_record(float(np.sqrt(item['error_integral']/item['weight_sum'])),item['error_RMS'])
        if item['reference_integral']==0:
            if item['relative_L2'] is not None:raise InvalidEvidence('undefined reference ratio')
        else:
            number(item['relative_L2'],key+'.relative_L2')
            close_record(float(np.sqrt(item['error_integral']/item['reference_integral'])),item['relative_L2'])
        if base is not None:
            for k in ('weight_sum','reference_integral'):close_record(base['region_metrics'][key][k],item[k])
    number(report['rho_u'],'rho_u');close_record(report['guards']['weak_squared'],report['rho_u']**2)
    if len(report['changes_sq'])!=4:raise InvalidEvidence('four change integrals required')
    for value in report['changes_sq']:number(value,'change integral')
    if zero_change and any(x!=0 for x in report['changes_sq']):raise InvalidEvidence('original cumulative change not zero')
    origin=report if base is None else base
    scales=[origin['guards'][k] for k in ('uv_full','strain_full','driver_full','weak_squared')]
    qs=[ratio_norm(x,y) for x,y in zip(report['changes_sq'],scales)]
    for key,expected in zip(BUDGETS,qs):
        if np.isinf(expected):
            if not allow_infinite_budget or report['budget_components'][key]!='Infinity':raise InvalidEvidence('zero-scale budget not admissible')
        else:number(report['budget_components'][key],key);close_record(expected,report['budget_components'][key])
    if np.isinf(max(qs)):
        if not allow_infinite_budget or report['budget_q']!='Infinity':raise InvalidEvidence('zero-scale Q not admissible')
    else:number(report['budget_q'],'budget_q');close_record(max(qs),report['budget_q'])


def bound_numeric(root,state,record,expected_commit,check):
    case=root/'states'/state;path=case/'receipt.json'
    if sha(path)!=record.get('numeric_receipt_sha256'):raise InvalidEvidence('numeric receipt binding')
    meta=json.loads(path.read_text());tree=code_tree_sha()
    if record.get('code_tree_sha256')!=tree or meta.get('code_tree_sha256')!=tree:
        raise InvalidEvidence('aggregate code tree binding')
    if meta['state']!=state or meta['source_commit']!=expected_commit:raise InvalidEvidence('aggregate numeric identity')
    if manifest_sha(meta['files'])!=record.get('input_manifest_sha256'):raise InvalidEvidence('numeric manifest binding')
    actual={str(p.relative_to(case)) for p in case.rglob('*') if p.is_file() and p!=path}
    if actual!=set(meta['files']):raise InvalidEvidence('numeric file set')
    for name,digest in meta['files'].items():
        check();file=case/name
        if not file.resolve().is_relative_to(case.resolve()) or sha(file)!=digest:
            raise InvalidEvidence('numeric input file hash')
    for key in ('NN_optimizer_steps','original_checkpoint_writes','history_fatigue_damage_updates','remote_actions'):
        count(meta[key],key,0)
    if list(meta['profiles'])!=[x[0] for x in PROFILES]:raise InvalidEvidence('numeric profile order')
    seeded=meta.get('seeded_incumbent_protocol',False)
    if type(seeded) is not bool or record.get('seeded_incumbent_protocol',False)!=seeded:
        raise InvalidEvidence('seeded incumbent numeric/replay identity')
    if seeded:
        if 'saved_seed_qualification' not in meta or 'saved_seed_qualification' not in record:
            raise InvalidEvidence('seeded qualification receipt missing')
        close_record(record['saved_seed_qualification'],meta['saved_seed_qualification'])
    close_record(record['baseline'],json.loads((case/'origin.json').read_text())['report'])
    close_record(record['D012_report'],meta['D012_report'])
    for name,_,_ in PROFILES:
        final=json.loads((case/name/'final.json').read_text())
        close_record(record['profiles'][name]['report'],final['report'])
        for k in ('solves','trials','accepted_steps','stop'):
            if record['profiles'][name][k]!=meta['profiles'][name][k] or record['profiles'][name][k]!=final['counts'][k]:
                raise InvalidEvidence('bound profile counts/stops')
        if seeded:
            close_record(record['profiles'][name]['initialization'],meta['profiles'][name]['initialization'])
            close_record(record['profiles'][name]['final_incumbent'],meta['profiles'][name]['final_incumbent'])
            close_record(record['profiles'][name]['initialization'],final['counts']['initialization'])
            close_record(record['profiles'][name]['final_incumbent'],final['counts']['final_incumbent'])
    return meta


def aggregate(root,expected_commit,check=lambda:None):
    """Requires all3 replay receipts: a missing row is incomplete, never zero gain."""
    import csv
    root=Path(root);records=[];rows=[]
    for state in STATES:
        check();path=root/'replay'/state/'verified.json'
        if not path.is_file():raise InvalidEvidence('INCOMPLETE: missing state replay '+state)
        r=json.loads(path.read_text());records.append(r)
        if r['state']!=state or r['source_commit']!=expected_commit or r['new_optimizations']!=0:
            raise InvalidEvidence('replay identity')
        if list(r['profiles'])!=[x[0] for x in PROFILES]:raise InvalidEvidence('all four replay profiles/order required')
        count(r['new_optimizations'],'new replay optimizations',0)
        meta=bound_numeric(root,state,r,expected_commit,check)
        validate_report(r['baseline'],zero_change=True)
        validate_report(r['D012_report'],r['baseline'],allow_infinite_budget=True)
        state_solves=state_trials=0
        for name,eta,strict in PROFILES:
            p=r['profiles'][name];base=r['baseline'];old=r['D012_report']
            validate_report(p['report'],base)
            ss,tt=validate_counts(p,base['guards']['uv_full']);state_solves+=ss;state_trials+=tt
            if tuple(p['report']['guards'])!=GUARDS or tuple(base['guards'])!=GUARDS:raise InvalidEvidence('aggregate thirteen-guard schema')
            for i,key in enumerate(GUARDS):
                value=p['report']['guards'][key];ceiling=base['guards'][key];finite(value,ceiling)
                if value<0 or ceiling<0 or ((strict or i<7) and value>ceiling):raise InvalidEvidence('aggregate actual guard')
            if p['report']['budget_q']>eta:raise InvalidEvidence('aggregate physical budget')
            initial=p.get('initialization',{}).get('selected',{}).get('source','E023_ORIGIN')
            final_source=p.get('final_incumbent',{}).get('source','E023_ORIGIN')
            retained=p.get('final_incumbent',{}).get('retained_initial_incumbent',False)
            for region in ('full','damage','background','inside_background'):
                row=dict(state=state,profile=name,eta=eta,primary=strict,region=region,
                         initial_incumbent_source=initial,final_incumbent_source=final_source,
                         retained_initial_incumbent=retained)
                for quantity in ('uv','strain','driver'):
                    key=quantity+'_'+region
                    e=p['report']['region_metrics'][key]['error_RMS'];e0=base['region_metrics'][key]['error_RMS']
                    ed=old['region_metrics'][key]['error_RMS']
                    row.update({quantity+'_RMS':e,quantity+'_E023_RMS':e0,quantity+'_D012_RMS':ed,
                        quantity+'_change_percent':None if e0==0 else 100*(e/e0-1)})
                row.update(rho_u=p['report']['rho_u'],rho_u_E023=base['rho_u'],budget_q=p['report']['budget_q'],
                           stop=p['stop'],solves=p['solves'],trials=p['trials'])
                rows.append(row)
        if count(r['replayed_solvers'],'state solves',12)!=state_solves or count(r['replayed_trials'],'state trials',108)!=state_trials:
            raise InvalidEvidence('state totals mismatch')
        if count(meta['offline_solver_calls'],'numeric solves',12)!=state_solves or count(meta['actual_candidate_trials'],'numeric trials',108)!=state_trials:
            raise InvalidEvidence('numeric/replay total mismatch')
    solves=sum(r['replayed_solvers'] for r in records);trials=sum(r['replayed_trials'] for r in records)
    if solves>36 or trials>324:raise InvalidEvidence('aggregate run budget')
    out=root/'summary';out.mkdir(exist_ok=False)
    with (out/'regions.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    receipt=dict(source_commit=expected_commit,code_tree_sha256=code_tree_sha(),states=list(STATES),profiles=12,
        strict_profiles=9,diagnostic_seven_guard_profiles=3,offline_solver_calls=solves,
        real_candidate_trials=trials,actual_trials_replayed=trials,new_replay_optimizations=0,
        verdict='COMPARATIVE_FIELD_REPLAY_COMPLETE_NOT_APPLICATION_VALIDATION',
        legacy001='historical_only',application_tolerance=None,NN_optimizer_steps=0,
        original_checkpoint_writes=0,history_fatigue_damage_updates=0,remote_actions=0,
        inputs={str(root/'replay'/s/'verified.json'):sha(root/'replay'/s/'verified.json') for s in STATES},
        seeded_incumbent_protocol={r['state']:r.get('seeded_incumbent_protocol',False) for r in records},
        central_cross_checks={r['state']:{'failures':r['central_cross_guard_failures'],'interpretation':r['central_interpretation']} for r in records})
    write_json(out/'receipt.json',receipt)
    (out/'README_analysis.md').write_text('# D014 complete replay summary\n\nAll12 fixed profiles are reported; no state/radius winner selection. Negative percent means lower error. Four raw physical change budgets remain centred at own original E023. A qualified saved incumbent may be retained after an unresolved local proxy, but it is not a new centre or a global optimum. Diagnostic seven-guard rows are not primary repairs. Regional protection is not pointwise or coupled-history validation. No .001 route verdict.\n\nSee regions.csv, per-state raw replay receipts, original events/coefficients and source/approval/resource records.\n')
    check();return receipt


def render(root,check=lambda:None):
    """Declared future render stage: only saved evaluated fields/tables, no forward."""
    import csv
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.tri as tri
    from matplotlib.colors import LogNorm,SymLogNorm
    root=Path(root);summary=root/'summary';records=list(csv.DictReader((summary/'regions.csv').open()))
    fixture='' if len(json.loads((summary/'receipt.json').read_text())['source_commit'])==40 else 'ARTIFICIAL UNIT FIXTURE ONLY | '
    folder=summary/'figures';folder.mkdir(exist_ok=False);inputs={}
    def pin(p):inputs[str(p)]=sha(p)
    pin(summary/'regions.csv');pin(summary/'receipt.json')
    def sidecar(name,body):
        (folder/(name+'.md')).write_text('# '+fixture+'D014 '+name+'\n\n## Data provenance\n\n'+body+'\n\n## How to read\n\nAll12 prespecified profiles are retained in the table. Curves connect only three evaluated radii; the seven-guard central diagnostic is a distinct unfilled marker, never a selected replacement. Negative percent means a lower error than each own E023.\n\n## Limitations\n\nThese states share one exposed synthetic trajectory, fixed D/BC/window/damage and frozen history/fatigue. A retained qualified seed is an already checked point, not a global optimum or an evolved-history result. A regional gain is not pointwise dominance, physical teacher qualification or coupled damage/crack/fatigue validation. Radii are error-normalized exploration scales, not application tolerances. See summary receipt, per-state replay records and figure_inputs.json for exact files/hashes. No unvisited field is rendered.\n')
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),sharey=True)
    for ax,state in zip(axes,STATES):
        for region in ('full','damage','background','inside_background'):
            rr=[next(r for r in records if r['state']==state and r['profile']==name and r['region']==region) for name,_,strict in PROFILES if strict]
            ax.plot([float(r['eta']) for r in rr],[float(r['uv_change_percent']) if r['uv_change_percent'] else np.nan for r in rr],marker='o',label=region)
        d=next(r for r in records if r['state']==state and r['profile']=='seven_guard_eta_0.3' and r['region']=='full')
        ax.scatter([.3],[float(d['uv_change_percent']) if d['uv_change_percent'] else np.nan],marker='D',facecolors='none',edgecolors='black',label='seven-guard full')
        ax.axhline(0,color='gray',lw=.8);ax.set_title(state);ax.set_xlabel('Physical radius eta');ax.grid(alpha=.2)
    axes[0].set_ylabel('UV RMS change vs own E023 (%)');axes[-1].legend(fontsize=7)
    fig.suptitle(fixture+'D014: actual field-budget gains, primary13 guards and central7-guard diagnostic');fig.tight_layout()
    fig.savefig(folder/'field_budget_profile.png',dpi=150);plt.close(fig)
    sidecar('field_budget_profile','Source: regions.csv rebuilt from all quantized raw heads and native-Q4 metrics. Panels show c20/c60/c83 four-domain UV changes against physical radius; shared vertical scale and original E023 references. It is a gain/cost profile, not a curve of optimized capacity. Missing/undefined percentages are left blank. Main numerical takeaways are the exact values in regions.csv; no tolerance or route threshold is overlaid.')
    check()
    fig,axes=plt.subplots(2,3,figsize=(14,7))
    measures=[('rho','full'),('strain','background'),('strain','inside_background'),
              ('driver','damage'),('driver','background'),('driver','inside_background')]
    colors=['#0072B2','#009E73','#D55E00']
    for ax,(quantity,region) in zip(axes.flat,measures):
        for state,color in zip(STATES,colors):
            rr=[next(r for r in records if r['state']==state and r['profile']==name and r['region']==region) for name,_,strict in PROFILES if strict]
            def val(r):
                if quantity=='rho':return np.nan if float(r['rho_u_E023'])==0 else 100*(float(r['rho_u'])/float(r['rho_u_E023'])-1)
                return float(r[quantity+'_change_percent']) if r[quantity+'_change_percent'] else np.nan
            ax.plot([float(r['eta']) for r in rr],[val(r) for r in rr],marker='o',color=color,label=state)
            diagnostic=next(r for r in records if r['state']==state and r['profile']=='seven_guard_eta_0.3' and r['region']==region)
            ax.scatter([.3],[val(diagnostic)],marker='D',facecolors='none',edgecolors=color)
        ax.axhline(0,color='gray',lw=.8);ax.grid(alpha=.2);ax.set_title(quantity+' '+region)
        ax.set_xlabel('physical radius eta');ax.set_ylabel('change vs own E023 (%)')
    axes[0,0].legend(fontsize=8);fig.suptitle(fixture+'D014 physical gains / background costs | open diamonds = seven-guard diagnostic')
    fig.tight_layout();fig.savefig(folder/'physical_tradeoff.png',dpi=150);plt.close(fig)
    sidecar('physical_tradeoff','Panels: actual weak rho, background strain, window-interior background strain, damage elastic-driver error, background driver error and window-interior background driver error. Each panel directly compares all three states on its shared percent axis; axes between quantities have separate ranges. Solid curves are three primary13-guard radii; open diamonds show only the prespecified central7-guard diagnostic. Positive values are costs, negative are improvements; zero is original own E023. This view prevents UV improvement from hiding background strain cost. Exact numerical values come from regions.csv; unlike a new forward or optimizer sweep, rendering only reads verified stored outputs.')
    check()
    for state in STATES:
        case=root/'states'/state
        for p in [case/'geometry.npz',case/'origin.npz',case/'strict_eta_0.3/final.npz']:pin(p)
        with np.load(case/'geometry.npz',allow_pickle=False) as z:geo={k:z[k] for k in z.files}
        with np.load(case/'origin.npz',allow_pickle=False) as z:origin={k:z[k] for k in z.files}
        with np.load(case/'strict_eta_0.3/final.npz',allow_pickle=False) as z:final={k:z[k] for k in z.files}
        xy=geo['xy'];conn=geo['conn'];triangles=np.concatenate([conn[:,[0,1,2]],conn[:,[0,2,3]]])
        mesh=tri.Triangulation(xy[:,0],xy[:,1],triangles)
        uv0=np.linalg.norm(origin['uv']-geo['reference_uv'],axis=1)/float(geo['us'])
        uv1=np.linalg.norm(final['uv']-geo['reference_uv'],axis=1)/float(geo['us'])
        free=(xy[:,1]!=xy[:,1].min())&(xy[:,1]!=xy[:,1].max())
        def contribution(f):
            a=np.zeros(len(xy));a[free]=np.sum(f.reshape(-1,2)**2,axis=1);return a
        f0=contribution(origin['force']);f1=contribution(final['force'])
        fig,axes=plt.subplots(2,3,figsize=(14,6))
        for i,(a,b,label) in enumerate([(uv0,uv1,'nodal UV error / absUs'),(f0,f1,'free-force contribution; sum = rho_u squared')]):
            high=max(float(a.max()),float(b.max()),1e-30);floor=high*1e-12
            for j,v in enumerate([a,b,b-a]):
                ax=axes[i,j]
                if j<2:norm=LogNorm(vmin=floor,vmax=high);colors='viridis';vv=np.maximum(v,floor)
                else:
                    limit=max(float(abs(v).max()),1e-30);norm=SymLogNorm(linthresh=limit*1e-3,vmin=-limit,vmax=limit);colors='RdBu_r';vv=v
                im=ax.tripcolor(mesh,vv,shading='gouraud',cmap=colors,norm=norm,rasterized=True)
                ax.tricontour(mesh,geo['damage'],levels=[.1],colors='black',linewidths=.6)
                ax.tricontourf(mesh,geo['damage'],levels=[.1,1.01],colors='none',hatches=['//'])
                ax.tricontour(mesh,(geo['window']>0).astype(float),levels=[.5],colors='cyan',linewidths=.7)
                ax.set_title(('E023','strict eta=.3','change: blue lower / red higher')[j]+'\n'+label,fontsize=8)
                ax.set_xlabel('x');ax.set_ylabel('y');fig.colorbar(im,ax=ax,shrink=.7)
        fig.suptitle(fixture+'D014 '+state+' | fixed preselected central primary profile | FEM damage>0.1 hatched; window cyan')
        fig.tight_layout();fig.savefig(folder/(state+'_fields.png'),dpi=150);plt.close(fig)
        sidecar(state+'_fields','Preselected example: strict eta=.3 for '+state+', not the best-performing radius. Geometry/target/window, original raw E023 and final stored actual fields are pinned in figure_inputs.json. Top row: baseline and candidate nodal vector UV error / absUs (shared log scale), then signed difference. Bottom: squared scaled mass-dual free-force contribution at free nodes (shared log scale), then signed difference. Each bottom map sums to the actual native rho_u squared; this is not a strong-form point residual or causal regional force attribution. Black hatch/contour is nodal damage>.1, cyan is fixed support. Full mesh is used; axes may have unequal display aspect and Gouraud interpolation is visual only. Log floor is display-only at1e-12 of row maximum; signed symlog is symmetric and includes all extrema. Full table values, including aggregate background costs, govern interpretation; local red/blue spots can coexist with a regional improvement. Numeric rows are in regions.csv and per-state replay receipts.')
        check()
    write_json(folder/'figure_inputs.json',dict(inputs=inputs,render_source_sha256=sha(Path(__file__))))
    check()
