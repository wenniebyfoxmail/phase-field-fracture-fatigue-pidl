#!/usr/bin/env python3
"""S01-E010: fit-partition counterfactual utility, cache-only and producer-only fits."""
from __future__ import annotations
import argparse
import copy
import importlib.util
import math
import os
from pathlib import Path
import sys
import time
from collections import Counter
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('e010_frozen_e009', ROOT/'scripts/pavetrack_localization_cv/run.py')
e9 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e9)
spec = importlib.util.spec_from_file_location('e010_assignment', ROOT/'scripts/pavetrack_rescore_cv/analyze.py')
assignment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assignment)
e8 = e9.e8
PROTOCOL = 'S01-E010-v1'
CONTRACT = 'docs/research/S01/S01-E010/'
read, write, sha = e9.read, e9.write, e9.sha
Budget, pixel_guard, OUTPUT_IMAGE_DIGEST_PATHS = e9.Budget, e9.pixel_guard, e9.OUTPUT_IMAGE_DIGEST_PATHS
features, partitions, scale_train = e9.features, e9.partitions, e9.scale_train


def verify_source(config, lock):
    manifest = read(ROOT/CONTRACT/'source_manifest.json')['files']
    for name, digest in manifest.items():
        e8.m.check_hash(ROOT/name, digest)
    e8.m.check_hash(config, manifest[CONTRACT+'run_config.json'])
    e8.m.check_hash(lock, manifest[CONTRACT+'data_lock.json'])
    cfg, lk = read(config), read(lock)
    if cfg['protocol'] != PROTOCOL or lk['protocol'] != PROTOCOL:
        raise ValueError('protocol')
    return cfg, lk


def load_cached(cache, metadata, cfg, lock):
    return e9.load_cached(cache, metadata, cfg, lock)


def policy_config(cfg):
    return dict(cfg['criterion'], **cfg['policy'])


def eligibility(data):
    """GT-free static eligibility, shared identically by labels and policy."""
    by = {}
    for r in data['originals']:
        by.setdefault(r['image_id'], []).append(r)
    result, scores = [], []
    for old, new, p in zip(data['pairs'][::2], data['pairs'][1::2], data['probabilities'], strict=True):
        if old != data['originals'][old['parent_id']] or new['parent_id'] != old['parent_id'] or new['original_box_xyxy'] != old['box_xyxy']:
            raise ValueError('pair identity')
        if not math.isfinite(float(p)) or not 0 <= p <= 1:
            raise ValueError('cached probability')
        s = math.sqrt(old['proposer_confidence']*float(p))
        ok = s > old['score'] and not any(new['box_xyxy'] == r['box_xyxy'] or e8.box_iou(new['box_xyxy'], r['box_xyxy']) > .7 for r in by[old['image_id']])
        result.append(ok)
        scores.append(s)
    return np.asarray(result, dtype=bool), np.asarray(scores, dtype=np.float64)


def correction(data, index, score):
    row = copy.deepcopy(data['pairs'][2*index+1])
    row.update(candidate_id='c:'+str(row['parent_id']), score=float(score),
               probability=float(data['probabilities'][index]), rescored_correction=True)
    return row


def prefix_roles(rows, targets, metric):
    return assignment.classified(rows, targets, metric)


def counterfactual_context(data, fit_locations):
    locations = {im: loc for im, loc in data['locations'].items() if loc in fit_locations}
    targets = {im: data['targets'][im] for im in locations}
    rows = [r for r in data['originals'] if r['image_id'] in locations]
    metric = e8.metrics(rows, targets, locations, 'score')
    hits = {h for _, h in prefix_roles(rows, targets, metric) if h is not None}
    cutoff = metric['global_score_threshold']
    excluded = [r['score'] for r in rows if cutoff is None or r['score'] < cutoff]
    return dict(rows=rows, targets=targets, locations=locations, metric=metric,
                hits=hits, first_excluded=max(excluded) if excluded else None)


def single_label(context, row):
    rows = context['rows']+[row]
    m = e8.metrics(rows, context['targets'], context['locations'], 'score')
    roles = prefix_roles(rows, context['targets'], m)
    hits = {h for _, h in roles if h is not None}
    new = sorted(hits-context['hits'])
    lost = sorted(context['hits']-hits)
    admitted = [(r, h) for r, h in roles if r['candidate_id'] == row['candidate_id']]
    if len(admitted) > 1:
        raise ValueError('nonunique correction')
    fp = int(bool(admitted) and admitted[0][1] is None)
    return dict(new=len(new), lost=len(lost), FP=fp, U=len(new)-len(lost)-fp,
                new_identities=[list(v) for v in new], lost_identities=[list(v) for v in lost],
                admitted=bool(admitted), cutoff=m['global_score_threshold'])


def label_partition(data, fit_locations, eligible, scores, guard=None):
    context = counterfactual_context(data, fit_locations)
    labels = []
    shortcut = full = 0
    for i, row in enumerate(data['pairs'][1::2]):
        if str(row['reid']) not in fit_locations or not eligible[i]:
            continue
        if guard is not None:
            guard.check()
        item = dict(index=i, parent_id=row['parent_id'], image_id=row['image_id'], location=str(row['reid']), score=float(scores[i]))
        # Strictly below the FIRST excluded score group, never <= and never last admitted.
        if context['first_excluded'] is not None and scores[i] < context['first_excluded']:
            value = dict(new=0,lost=0,FP=0,U=0,new_identities=[],lost_identities=[],admitted=False,cutoff=context['metric']['global_score_threshold'])
            shortcut += 1
        else:
            value = single_label(context, correction(data, i, scores[i]))
            full += 1
        labels.append(dict(item, **value))
    signs = Counter('positive' if r['U']>0 else 'negative' if r['U']<0 else 'zero' for r in labels)
    byloc = {loc: dict(Counter('positive' if r['U']>0 else 'negative' if r['U']<0 else 'zero' for r in labels if r['location']==loc)) for loc in fit_locations}
    return dict(fit_locations=list(fit_locations), baseline=context['metric'], baseline_hits=[list(h) for h in sorted(context['hits'])],
                first_excluded=context['first_excluded'], rows=labels, signs=dict(signs), by_location=byloc,
                support_pass=signs['positive']>0 and signs['negative']>0, full_evaluations=full, safe_shortcuts=shortcut)


def evaluate(data, utility, cfg):
    eligible, _ = eligibility(data)
    if len(utility) != len(eligible):
        raise ValueError('utility alignment')
    if any((v is None) != (not ok) or (v is not None and not math.isfinite(v)) for ok, v in zip(eligible, utility, strict=True)):
        raise ValueError('eligible finite utility / ineligible null')
    # Exactly binary admission: unattenuated s0 for admitted rows, never utility multiplication.
    gate = np.asarray([int(ok and v>0) for ok,v in zip(eligible, utility, strict=True)], dtype=np.float64)
    e = e9.evaluate(data, gate, policy_config(cfg))
    e.pop('quality_probabilities')
    for row in e['rows'][len(data['originals']):]:
        row.pop('localization_quality')
        row['predicted_utility'] = utility[next(i for i,r in enumerate(data['pairs'][1::2]) if r['parent_id']==row['parent_id'])]
    e.update(predicted_utilities=list(utility), eligible=eligible.tolist())
    return e


def preparation(data, cfg, guard=None):
    eligible, scores = eligibility(data)
    fit_reports = [label_partition(data, f['fit'], eligible, scores, guard) for f in cfg['folds']]
    oracle_labels = label_partition(data, cfg['locations'], eligible, scores, guard)
    oracle_u = [None if not ok else 0. for ok in eligible]
    for row in oracle_labels['rows']:
        oracle_u[row['index']] = float(row['U']>0)
    oracle = evaluate(data, oracle_u, cfg)
    report = dict(protocol=PROTOCOL, eligible_rows=int(eligible.sum()), total_pairs=len(eligible),
        folds=fit_reports, full_bank_diagnostic=oracle_labels,
        oracle_policy={k:oracle[k] for k in ['delta','retention','net_targets','retained_old_targets','new_detected_targets','lost_old_targets','protected_primary_pass','choice']},
        support_pass=all(f['support_pass'] for f in fit_reports),
        oracle_is_learned_result=False, oracle_is_mathematical_upper_bound=False,
        fits_consumed=0, learned_predictions=0, learned_comparisons=0, source_pixel_reads=0, fresh_access=False)
    report['ready_for_code_review'] = report['support_pass'] and oracle['protected_primary_pass'] is True
    if sum(len(f['rows']) for f in fit_reports) > cfg['budget']['max_fit_counterfactual_labels'] or len(oracle_labels['rows']) > cfg['budget']['max_full_bank_oracle_labels']:
        raise ValueError('label slot budget')
    return report, oracle


def sign_weights(y):
    signs = np.sign(y)
    groups = np.unique(signs)
    if not {-1.,1.} <= set(groups):
        raise ValueError('positive and negative support required')
    return np.asarray([1/(len(groups)*np.count_nonzero(signs==s)) for s in signs])


def objective_gradient(theta, Z, y, weights, l2):
    residual = np.einsum('ij,j->i',Z,theta[:-1], optimize=False)+theta[-1]-y
    loss = float(.5*np.dot(weights,residual**2)+.5*l2*np.dot(theta[:-1],theta[:-1]))
    grad = np.r_[np.einsum('ij,i->j',Z,weights*residual,optimize=False)+l2*theta[:-1],np.dot(weights,residual)]
    return loss, grad


def fit_head(X, y, train, held, cfg, guard):
    require_producer()  # Also protects direct calls; synthetic tests never solve.
    guard.check()
    mean, std = scale_train(X[train])
    Z = (X[train]-mean)/std
    A = np.column_stack([Z,np.ones(len(Z))])
    weights = sign_weights(y)
    gram = A.T @ (weights[:,None]*A)
    gram[:-1,:-1] += np.eye(X.shape[1])*cfg['fit']['l2']
    rhs = A.T @ (weights*y)
    theta = np.linalg.solve(gram,rhs)  # ONE solve; no retry/fallback.
    guard.check()
    initial,_ = objective_gradient(np.zeros_like(theta),Z,y,weights,cfg['fit']['l2'])
    final,grad = objective_gradient(theta,Z,y,weights,cfg['fit']['l2'])
    model = dict(mean=mean.tolist(),std=std.tolist(),theta=theta.tolist(),
        train_indices=train.tolist(),held_indices=held.tolist(),weights=weights.tolist(),
        initial_objective=initial,final_objective=final,gradient_inf=float(abs(grad).max()),
        gram_residual_inf=float(abs(gram@theta-rhs).max()),solve_count=1)
    verify_head(model,X,y,train,held,cfg)
    return model


def verify_head(model, X, y, train, held, cfg):
    mean,std = scale_train(X[train])
    weights = sign_weights(y)
    if model['train_indices']!=train.tolist() or model['held_indices']!=held.tolist() or model['mean']!=mean.tolist() or model['std']!=std.tolist() or model['weights']!=weights.tolist() or model['solve_count']!=1:
        raise ValueError('partition/scaler/weight/solve identity')
    theta = np.asarray(model['theta'],dtype=np.float64)
    if theta.shape!=(X.shape[1]+1,) or not np.isfinite(theta).all():
        raise ValueError('finite coefficients')
    Z = (X[train]-mean)/std
    initial,_ = objective_gradient(np.zeros_like(theta),Z,y,weights,cfg['fit']['l2'])
    final,grad = objective_gradient(theta,Z,y,weights,cfg['fit']['l2'])
    if not math.isfinite(final) or not np.isfinite(grad).all() or final>initial or abs(grad).max()>cfg['fit']['gradient_inf_max']:
        raise ValueError('ridge stationarity')
    for key,value in [('initial_objective',initial),('final_objective',final),('gradient_inf',float(abs(grad).max()))]:
        if not math.isclose(value,model[key],rel_tol=1e-9,abs_tol=1e-12):
            raise ValueError('objective/gradient replay')
    A = np.column_stack([Z,np.ones(len(Z))])
    gram=A.T@(weights[:,None]*A)
    gram[:-1,:-1]+=np.eye(X.shape[1])*cfg['fit']['l2']
    residual=float(abs(gram@theta-A.T@(weights*y)).max())
    if not math.isfinite(residual) or residual>cfg['fit']['gradient_inf_max'] or not math.isclose(residual,model['gram_residual_inf'],rel_tol=1e-7,abs_tol=1e-12):
        raise ValueError('Gram residual replay')


def require_producer():
    e9.require_producer()


def binding(cfg, lock, a):
    return dict(protocol=PROTOCOL,config_sha256=sha(a.config),lock_sha256=sha(a.lock),
        source_manifest_sha256=sha(ROOT/CONTRACT/'source_manifest.json'),cache_files=lock['cache_files'],
        metadata_sha256=lock['metadata_sha256'],run_id=a.run.name,fresh_access=False,scope=cfg['scope'])


def run_models(a, cfg, data, report, guard, lineage, fitter=None):
    if not report['ready_for_code_review']:
        raise ValueError('prefit support/oracle required')
    fitter = fit_head if fitter is None else fitter
    X = features(data)
    eligible,_ = eligibility(data)
    folds = partitions(data,cfg)
    models=[]
    for i,((_,held),fold) in enumerate(zip(folds,report['folds'],strict=True)):
        train=np.asarray([r['index'] for r in fold['rows']],dtype=int)
        held=held[eligible[held]]
        y=np.asarray([r['U'] for r in fold['rows']],dtype=np.float64)
        guard.check()
        marker=a.run/f'fold_{i}_started.json'
        if marker.exists():
            raise ValueError('duplicate head fit')
        write(marker,dict(lineage,fold=i,train_indices=train.tolist(),held_indices=held.tolist()))
        guard.fold_start=guard.clock()
        model=fitter(X,y,train,held,cfg,guard)
        guard.check()
        guard.fold_start=None
        verify_head(model,X,y,train,held,cfg)
        write(a.run/f'fold_{i}_head.json',dict(lineage,fold=i,model=model,resource=guard.receipt()))
        models.append(model)
    write(a.run/'four_heads_verified.json',dict(lineage,files={f'fold_{i}_head.json':sha(a.run/f'fold_{i}_head.json') for i in range(4)}))
    write(a.run/'prediction_started.json',lineage)
    utilities=predict_all(models,X,folds,eligible)
    write(a.run/'oof_scores.json',dict(lineage,parent_ids=[r['parent_id'] for r in data['pairs'][1::2]],eligible=eligible.tolist(),predicted_utilities=utilities))
    write(a.run/'comparison_started.json',lineage)
    e=evaluate(data,utilities,cfg)
    write(a.run/'evaluation.json',dict(lineage,**e))
    write(a.run/'decision.json',e9.decision(lineage,e,sha(a.run/'evaluation.json')))


def predict_all(models, X, folds, eligible):
    if len(models)!=4 or len(folds)!=4:
        raise ValueError('four heads before prediction')
    result=[None]*len(X)
    for model,(_,held) in zip(models,folds,strict=True):
        ids=held[eligible[held]]
        theta=np.asarray(model['theta'])
        Z=(X[ids]-np.asarray(model['mean']))/np.asarray(model['std'])
        pred=np.einsum('ij,j->i',Z,theta[:-1],optimize=False)+theta[-1]
        if not np.isfinite(pred).all():
            raise ValueError('nonfinite prediction')
        for i,p in zip(ids,pred,strict=True):
            result[i]=float(p)
    return result


def execute(a,cfg,lock):
    require_producer()
    a.run.mkdir(parents=True,exist_ok=False)
    guard=Budget(a.run,cfg['budget'])
    guard.start_monitor()
    lineage=binding(cfg,lock,a)
    write(a.run/'launch_receipt.json',dict(lineage,pid=os.getpid(),started_at=time.strftime('%Y-%m-%dT%H:%M:%S%z')))
    try:
        data=load_cached(a.cache,a.metadata,cfg,lock)
        report,_=preparation(data,cfg,guard)
        write(a.run/'input_audit.json',dict(lineage,**report))
        if not report['ready_for_code_review']:
            write(a.run/'status.json',dict(lineage,state='stop_support' if not report['support_pass'] else 'stop_feasibility',fits_consumed=0,comparison_count=0,resource=guard.receipt()))
            return
        run_models(a,cfg,data,report,guard,lineage)
        guard.check()
        write(a.run/'status.json',dict(lineage,state='completed',fits_consumed=4,comparison_count=1,resource=guard.receipt()))
    except BaseException as exc:
        write(a.run/'status.json',dict(lineage,state='failed',reason=str(exc),fits_consumed=len(list(a.run.glob('fold_*_started.json'))),resource=guard.receipt()))
        raise
    finally:
        guard.done.set()


def verify(a,cfg,lock):
    lineage=binding(cfg,lock,a)
    data=load_cached(a.cache,a.metadata,cfg,lock)
    report,_=preparation(data,cfg)
    if read(a.run/'input_audit.json')!=dict(lineage,**report):
        raise ValueError('input audit replay')
    status=read(a.run/'status.json')
    if any(status.get(k)!=v for k,v in lineage.items()):
        raise ValueError('status lineage')
    resource=status['resource']
    if not 0<=resource['elapsed_seconds']<=cfg['budget']['total_wall_seconds'] or not 0<=resource['peak_rss_bytes']<=cfg['budget']['rss_cap_gib']*1024**3:
        raise ValueError('resource receipt')
    if not report['ready_for_code_review']:
        expected='stop_support' if not report['support_pass'] else 'stop_feasibility'
        if status['state']!=expected or status.get('fits_consumed')!=0 or status.get('comparison_count')!=0 or list(a.run.glob('fold_*')) or any((a.run/n).exists() for n in ['four_heads_verified.json','prediction_started.json','comparison_started.json','oof_scores.json','evaluation.json','decision.json']):
            raise ValueError('prefit stop boundary')
        return None,data
    if status['state']!='completed' or status['fits_consumed']!=4 or status['comparison_count']!=1:
        raise ValueError('incomplete execution')
    receipt=dict(lineage,files={f'fold_{i}_head.json':sha(a.run/f'fold_{i}_head.json') for i in range(4)})
    if read(a.run/'four_heads_verified.json')!=receipt or len(list(a.run.glob('fold_*_started.json')))!=4:
        raise ValueError('four head receipt')
    X=features(data)
    eligible,_=eligibility(data)
    folds=partitions(data,cfg)
    models=[]
    for i,((_,held),fold) in enumerate(zip(folds,report['folds'],strict=True)):
        train=np.asarray([r['index'] for r in fold['rows']],dtype=int)
        held=held[eligible[held]]
        y=np.asarray([r['U'] for r in fold['rows']],dtype=np.float64)
        payload=read(a.run/f'fold_{i}_head.json')
        if any(payload.get(k)!=v for k,v in lineage.items()) or payload['fold']!=i or read(a.run/f'fold_{i}_started.json')!=dict(lineage,fold=i,train_indices=train.tolist(),held_indices=held.tolist()):
            raise ValueError('head lineage')
        verify_head(payload['model'],X,y,train,held,cfg)
        models.append(payload['model'])
    utilities=predict_all(models,X,folds,eligible)
    if read(a.run/'oof_scores.json')!=dict(lineage,parent_ids=[r['parent_id'] for r in data['pairs'][1::2]],eligible=eligible.tolist(),predicted_utilities=utilities):
        raise ValueError('OOF exact replay')
    e=dict(lineage,**evaluate(data,utilities,cfg))
    if read(a.run/'evaluation.json')!=e or read(a.run/'decision.json')!=e9.decision(lineage,e,sha(a.run/'evaluation.json')):
        raise ValueError('outcome replay')
    for name in ['prediction_started.json','comparison_started.json']:
        if read(a.run/name)!=lineage:
            raise ValueError('phase marker')
    return e,data


def main():
    sys.addaudithook(pixel_guard)
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['prepare','execute','verify'])
    for name in ['config','lock','cache','metadata','run']:
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    cfg,lock=verify_source(a.config,a.lock)
    if a.stage=='prepare':
        a.run.mkdir(parents=True,exist_ok=False)
        guard=Budget(a.run,cfg['budget'])
        guard.start_monitor()
        try:
            report,oracle=preparation(load_cached(a.cache,a.metadata,cfg,lock),cfg,guard)
            write(a.run/'preparation.json',dict(binding(cfg,lock,a),**report))
            write(a.run/'diagnostic_oracle.json',dict(binding(cfg,lock,a),**oracle))
        finally:
            guard.done.set()
    elif a.stage=='execute':
        execute(a,cfg,lock)
    else:
        e,_=verify(a,cfg,lock)
        write(a.run/'verification_receipt.json',dict(status='verified',evaluation_sha256=None if e is None else sha(a.run/'evaluation.json'),source_manifest_sha256=sha(ROOT/CONTRACT/'source_manifest.json'),fits_repeated=0))


if __name__=='__main__':
    main()
