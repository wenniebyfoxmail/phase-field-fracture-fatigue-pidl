#!/usr/bin/env python3
"""S01-E009: cache-only, producer-only four-head localisation crossfit."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('e009_e008_dependency', ROOT/'scripts/pavetrack_rescore_cv/run.py')
e8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e8)
PROTOCOL = 'S01-E009-v1'
CONTRACT = 'docs/research/S01/S01-E009/'
INPUTS = ['qualification_evaluation.json', 'qualification_pooled_features.npz',
          'qualification_scores.json', 'qualification_scoring_receipt.json']
SCALARS = ['parent_proposer_logit', 'parent_crack_logit', 'corrected_crack_logit',
           'log_aspect', 'log_area_fraction', 'width_fraction', 'height_fraction',
           'center_x_fraction', 'center_y_fraction', 'parent_iou',
           'nonparent_max_iou', 'nonparent_overlap_max_score']
read, sha = e8.read, e8.sha256_file


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + str(threading.get_ident()) + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    os.replace(tmp, path)


def pixel_guard(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        name = os.fsdecode(args[0]).replace('\\', '/').lower()
        writing = isinstance(args[1], str) and ('w' in args[1] or 'a' in args[1] or 'x' in args[1])
        if not writing and (Path(name).suffix in {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.bmp', '.gif'} or '/images/' in name):
            raise PermissionError('E009 pixel access forbidden')


def verify_source(config, lock):
    manifest = read(ROOT/CONTRACT/'source_manifest.json')['files']
    for name, h in manifest.items():
        e8.m.check_hash(ROOT/name, h)
    e8.m.check_hash(config, manifest[CONTRACT+'run_config.json'])
    e8.m.check_hash(lock, manifest[CONTRACT+'data_lock.json'])
    return read(config), read(lock)


def peak_rss():
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                (n, ctypes.c_size_t) for n in ['PeakWorkingSetSize', 'WorkingSetSize',
                'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage']]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise OSError('cannot measure peak RSS')
        return counters.PeakWorkingSetSize
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)


class Budget:
    def __init__(self, run, cfg, clock=time.monotonic, memory=peak_rss):
        self.run, self.cfg, self.clock, self.memory = run, cfg, clock, memory
        self.start = clock()
        self.fold_start = None
        self.peak = 0
        self.done = threading.Event()

    def check(self):
        self.peak = max(self.peak, self.memory())
        if self.peak > self.cfg['rss_cap_gib']*1024**3:
            raise RuntimeError('RSS_CAP')
        now = self.clock()
        if now-self.start > self.cfg['total_wall_seconds']:
            raise RuntimeError('TOTAL_WALL_CAP')
        if self.fold_start is not None and now-self.fold_start > self.cfg['fit_wall_seconds_per_fold']:
            raise RuntimeError('FIT_WALL_CAP')

    def receipt(self):
        return dict(elapsed_seconds=self.clock()-self.start, peak_rss_bytes=self.peak)

    def monitor(self):
        while not self.done.wait(.5):
            try:
                self.check()
            except BaseException as exc:
                write(self.run/'status.json', dict(state='failed_resource', reason=str(exc),
                      resource=self.receipt(), fits_consumed=len(list(self.run.glob('fold_*_started.json'))),
                      fresh_access=False))
                os._exit(71)

    def start_monitor(self):
        threading.Thread(target=self.monitor, daemon=True).start()


def load_cached(cache, metadata, cfg, lock):
    """Never call inherited load/verified_cache or open any prepared-image path."""
    for name in INPUTS:
        e8.m.check_hash(cache/name, lock['cache_files'][name])
    e8.m.check_hash(metadata, lock['metadata_sha256'])
    evaluation = read(cache/'qualification_evaluation.json')
    scores = read(cache/'qualification_scores.json')
    receipt = read(cache/'qualification_scoring_receipt.json')
    expected = lock['e008_lineage']
    for payload in [evaluation, scores, receipt]:
        if any(payload.get(k) != v for k, v in expected.items()):
            raise ValueError('cached lineage')
    if set(receipt['files']) != set(INPUTS[1:3]):
        raise ValueError('scoring inventory')
    for name, h in receipt['files'].items():
        if lock['cache_files'][name] != h:
            raise ValueError('scoring receipt binding')
    e = evaluation['policies'][0]
    records = [r for r in read(metadata)['records']
               if r['split'] == 'train' and str(r['reid']) in cfg['locations']]
    by = {r['image_id']: r for r in records}
    if len(by) != 330 or set(e['targets']) != set(by):
        raise ValueError('fixed training image bank')
    if e['targets'] != {im:r['crack_boxes_xyxy'] for im, r in by.items()} or e['image_locations'] != {im:str(r['reid']) for im,r in by.items()}:
        raise ValueError('target identity')
    originals, pairs = e['baseline_rows'], e['pair_rows']
    if len(pairs) != 25204 or scores['parent_ids'] != [r['parent_id'] for r in pairs[1::2]] or e['corrected_probabilities'] != scores['probabilities']:
        raise ValueError('cache parent/probability alignment')
    if len(originals) != 19855 or any(r['parent_id'] != i for i,r in enumerate(originals)):
        raise ValueError('original bank identity')
    for old, new in zip(pairs[::2], pairs[1::2], strict=True):
        if old != originals[old['parent_id']] or new['parent_id'] != old['parent_id'] or new['original_box_xyxy'] != old['box_xyxy'] or new['kind'] != 'correction':
            raise ValueError('pair identity')
    with np.load(cache/'qualification_pooled_features.npz', allow_pickle=False) as f:
        if set(f.files) != {'X'}:
            raise ValueError('feature inventory')
        pooled = f['X']
    if pooled.shape != (12602,576) or pooled.dtype != np.float32 or not np.isfinite(pooled).all():
        raise ValueError('pooled feature contract')
    probabilities = np.asarray(scores['probabilities'], dtype=np.float64)
    if probabilities.shape != (12602,) or not np.isfinite(probabilities).all() or np.any((probabilities<0)|(probabilities>1)):
        raise ValueError('cached probability')
    base = e8.metrics(originals, e['targets'], e['image_locations'], 'score')
    if base != e['baseline'] or sum(t['true_positives'] for t in base['locations']) != 282:
        raise ValueError('E003 comparator replay')
    return dict(originals=originals, pairs=pairs, probabilities=probabilities, pooled=pooled,
                records=records, targets=e['targets'], locations=e['image_locations'])


def features(data):
    """Feature construction cannot inspect GT; records passed here contain dimensions only."""
    by = {r['image_id']: (r['width'],r['height']) for r in data['records']}
    originals = {}
    for row in data['originals']:
        originals.setdefault(row['image_id'], []).append(row)
    extra = []
    def logit(p):
        if not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError('feature probability')
        p = min(1-1e-6,max(1e-6,p))
        return math.log(p/(1-p))
    for old,new,p in zip(data['pairs'][::2],data['pairs'][1::2],data['probabilities'],strict=True):
        x1,y1,x2,y2 = new['box_xyxy']
        W,H = by[new['image_id']]
        if not 0<=x1<x2<=W or not 0<=y1<y2<=H:
            raise ValueError('geometry bounds')
        w,h = x2-x1,y2-y1
        others = [(e8.box_iou(new['box_xyxy'],r['box_xyxy']),r['score'])
                  for r in originals[new['image_id']] if r['parent_id'] != old['parent_id']]
        extra.append([logit(old['proposer_confidence']),logit(old['probability']),logit(float(p)),
            math.log(w/h),math.log(w*h/(W*H)),w/W,h/H,(x1+x2)/(2*W),(y1+y2)/(2*H),
            e8.box_iou(old['box_xyxy'],new['box_xyxy']),max((v for v,_ in others),default=0.),
            max((s for v,s in others if v>=.5),default=0.)])
    X = np.column_stack([data['pooled'],np.asarray(extra,dtype=np.float64)])
    if X.shape != (len(extra),588) or not np.isfinite(X).all():
        raise ValueError('feature dimensions/finite')
    return X


def labels(data):
    return np.asarray([int(max((e8.box_iou(r['box_xyxy'],t) for t in data['targets'][r['image_id']]),default=0.)>=.5)
                       for r in data['pairs'][1::2]],dtype=np.float64)


def partitions(data, cfg):
    loc = np.asarray([str(r['reid']) for r in data['pairs'][1::2]])
    if set(loc) != set(cfg['locations']):
        raise ValueError('location scope')
    result = []
    for f in cfg['folds']:
        train = np.flatnonzero(np.isin(loc,f['fit']))
        held = np.flatnonzero(np.isin(loc,f['held']))
        if set(train)&set(held) or len(train)+len(held)!=len(loc) or not len(held):
            raise ValueError('fold partition')
        result.append((train,held))
    if sorted(np.concatenate([h for _,h in result]).tolist()) != list(range(len(loc))):
        raise ValueError('each held exactly once')
    return result


def scale_train(X):
    return X.mean(axis=0), np.maximum(X.std(axis=0,ddof=0),1e-8)


def objective_gradient(theta, Z, y, l2):
    """Analytic deterministic verifier; no optimizer or model fitting."""
    logits = np.einsum('ij,j->i',Z,theta[:-1],optimize=False)+theta[-1]
    prob = np.exp(-np.logaddexp(0.,-logits))
    loss = float(np.mean(np.logaddexp(0.,logits)-y*logits)+.5*l2*np.dot(theta[:-1],theta[:-1]))
    residual = prob-y
    grad = np.r_[np.einsum('ij,i->j',Z,residual,optimize=False)/len(y)+l2*theta[:-1],residual.mean()]
    return loss,grad


def fit_head(X, y, train, held, cfg, guard):
    import torch
    guard.check()
    if set(np.unique(y[train])) != {0.,1.}:
        raise ValueError('empty training class')
    mean,std = scale_train(X[train])
    Z = (X[train]-mean)/std
    tz = torch.from_numpy(Z)
    ty = torch.from_numpy(y[train])
    theta = torch.zeros(X.shape[1]+1,dtype=torch.float64,requires_grad=True)
    optcfg = cfg['optimizer']
    optimizer = torch.optim.LBFGS([theta], **{k:v for k,v in optcfg.items() if k!='name'})
    calls = []
    def objective():
        return torch.nn.functional.binary_cross_entropy_with_logits(tz@theta[:-1]+theta[-1],ty)+.5*cfg['l2']*theta[:-1].square().sum()
    initial = float(objective().detach())
    def closure():
        guard.check()
        optimizer.zero_grad()
        loss = objective()
        if not torch.isfinite(loss):
            raise ValueError('nonfinite objective')
        loss.backward()
        calls.append(float(loss.detach()))
        return loss
    optimizer.step(closure)
    state = optimizer.state[theta]
    model = dict(mean=mean.tolist(),std=std.tolist(),theta=theta.detach().numpy().tolist(),
        train_indices=train.tolist(),held_indices=held.tolist(),positive=int(y[train].sum()),negative=int(len(train)-y[train].sum()),
        initial_objective=initial,closure_objectives=calls,iterations=int(state.get('n_iter',0)),
        func_evals=int(state.get('func_evals',0)))
    final,grad = objective_gradient(np.asarray(model['theta']),Z,y[train],cfg['l2'])
    model.update(final_objective=final,gradient_inf=float(np.max(np.abs(grad))))
    verify_head(model,X,y,train,held,cfg)
    return model


def verify_head(model, X, y, train, held, cfg):
    mean,std = scale_train(X[train])
    if model['train_indices']!=train.tolist() or model['held_indices']!=held.tolist() or model['mean']!=mean.tolist() or model['std']!=std.tolist():
        raise ValueError('fit/scaler isolation')
    theta = np.asarray(model['theta'],dtype=np.float64)
    if theta.shape != (X.shape[1]+1,) or not np.isfinite(theta).all():
        raise ValueError('head coefficient contract')
    final,grad = objective_gradient(theta,(X[train]-mean)/std,y[train],cfg['l2'])
    if not np.isfinite(grad).all() or not math.isfinite(final) or final > model['initial_objective'] or np.max(np.abs(grad))>1e-5:
        raise ValueError('fit convergence')
    if not math.isclose(model['initial_objective'],math.log(2.),rel_tol=0,abs_tol=1e-12) or not math.isclose(final,model['final_objective'],rel_tol=1e-11,abs_tol=1e-12) or not math.isclose(float(np.max(np.abs(grad))),model['gradient_inf'],rel_tol=1e-8,abs_tol=1e-12):
        raise ValueError('objective/gradient replay')
    if model['positive']!=int(y[train].sum()) or model['negative']!=int(len(train)-y[train].sum()) or set(np.unique(y[train]))!={0.,1.}:
        raise ValueError('fit class support')
    calls = model['closure_objectives']
    if not calls or not all(math.isfinite(v) for v in calls) or model['func_evals']!=len(calls) or not 1<=model['iterations']<=cfg['optimizer']['max_iter'] or not 1<=len(calls)<=cfg['optimizer']['max_eval']:
        raise ValueError('optimizer counters')


def predict_all(models, X, folds):
    result = np.full(len(X),np.nan,dtype=np.float64)
    if len(models)!=4 or len(folds)!=4:
        raise ValueError('four heads must be verified before prediction')
    for model,(_,held) in zip(models,folds,strict=True):
        theta = np.asarray(model['theta'])
        z = (X[held]-np.asarray(model['mean']))/np.asarray(model['std'])
        result[held] = np.exp(-np.logaddexp(0.,-(z@theta[:-1]+theta[-1])))
    if not np.isfinite(result).all():
        raise ValueError('incomplete OOF predictions')
    return result


def added_bank(data, quality, cfg):
    from collections import defaultdict
    original,pairs = data['originals'],data['pairs']
    if len(quality)!=len(pairs)//2 or len(data['probabilities'])!=len(quality):
        raise ValueError('quality alignment')
    by = defaultdict(list)
    for r in original:
        by[r['image_id']].append(r)
    proposed = []
    counts = dict(original_count=len(original),scored_pairs=len(quality),ratio_rejected=0,
                  original_duplicate_rejected=0,correction_duplicate_rejected=0,accepted_corrections=0)
    for old,new,p,q in zip(pairs[::2],pairs[1::2],data['probabilities'],quality,strict=True):
        if old!=original[old['parent_id']] or new['parent_id']!=old['parent_id'] or new['original_box_xyxy']!=old['box_xyxy']:
            raise ValueError('pair mutation')
        if not math.isfinite(q) or not 0<=q<=1 or not math.isfinite(p) or not 0<=p<=1:
            raise ValueError('quality probability')
        score = math.sqrt(old['proposer_confidence']*float(p))*float(q)
        if score<=old['score']:
            counts['ratio_rejected']+=1
            continue
        if any(new['box_xyxy']==r['box_xyxy'] or e8.box_iou(new['box_xyxy'],r['box_xyxy'])>cfg['original_duplicate_iou'] for r in by[old['image_id']]):
            counts['original_duplicate_rejected']+=1
            continue
        row = copy.deepcopy(new)
        row.update(candidate_id='c:'+str(old['parent_id']),score=score,probability=float(p),
                   localization_quality=float(q),rescored_correction=True)
        proposed.append(row)
    accepted=[]
    images=defaultdict(list)
    for row in sorted(proposed,key=lambda r:(-r['score'],r['image_id'],tuple(r['box_xyxy']),r['parent_id'])):
        if any(e8.box_iou(row['box_xyxy'],r['box_xyxy'])>cfg['correction_duplicate_iou'] for r in images[row['image_id']]):
            counts['correction_duplicate_rejected']+=1
            continue
        accepted.append(row)
        images[row['image_id']].append(row)
    rows=copy.deepcopy(original)+sorted(accepted,key=lambda r:r['parent_id'])
    counts['accepted_corrections']=len(accepted)
    if rows[:len(original)]!=original or len({r['candidate_id'] for r in rows})!=len(rows):
        raise ValueError('immutable original prefix/unique IDs')
    return rows,counts


def criterion(delta, retention, net, cfg):
    return None if delta is None or retention is None else bool(delta>cfg['minimum_macro_delta_strict'] and retention>=cfg['minimum_retention'] and net>=cfg['minimum_net_targets'])


def evaluate(data, quality, cfg):
    rows,choice=added_bank(data,quality,cfg)
    original=data['originals']
    targets,locations=data['targets'],data['locations']
    bm=e8.metrics(original,targets,locations,'score')
    cm=e8.metrics(rows,targets,locations,'score')
    before=e8.admitted_targets(original,targets,bm)
    after=e8.admitted_targets(rows,targets,cm)
    ret=None if not before else len(before&after)/len(before)
    delta=None if bm['macro_location_recall'] is None else cm['macro_location_recall']-bm['macro_location_recall']
    return dict(baseline=bm,candidate=cm,delta=delta,retention=ret,net_targets=len(after)-len(before),
        retained_old_targets=len(before&after),lost_old_targets=len(before-after),new_detected_targets=len(after-before),
        protected_primary_pass=criterion(delta,ret,len(after)-len(before),cfg),baseline_rows=original,rows=rows,
        pair_rows=data['pairs'],corrected_probabilities=data['probabilities'].tolist(),quality_probabilities=np.asarray(quality).tolist(),
        choice=choice,targets=targets,image_locations=locations,
        added_corrections_in_candidate_prefix=sum(cm['global_score_threshold'] is not None and r['score']>=cm['global_score_threshold'] for r in rows[len(original):]))


def binding(cfg, lock, a):
    return dict(protocol=PROTOCOL,config_sha256=sha(a.config),lock_sha256=sha(a.lock),
        source_manifest_sha256=sha(ROOT/CONTRACT/'source_manifest.json'),cache_files=lock['cache_files'],metadata_sha256=lock['metadata_sha256'],
        run_id=a.run.name,fresh_access=False,scope=cfg['scope'])


def audit(data, X, y, folds, cfg):
    support=[]
    for i,(train,held) in enumerate(folds):
        if set(np.unique(y[train]))!={0.,1.}:
            raise ValueError('empty training class')
        support.append(dict(fold=i,**cfg['folds'][i],train_rows=len(train),train_positive=int(y[train].sum()),held_rows=len(held),held_positive=int(y[held].sum())))
    oracle=evaluate(data,y,cfg)
    return dict(feature_names=['pooled_'+str(i) for i in range(576)]+SCALARS,shape=list(X.shape),
                support=support,oracle_policy={k:oracle[k] for k in ['delta','retention','net_targets','retained_old_targets','new_detected_targets','lost_old_targets','protected_primary_pass','choice']},
                oracle_is_learned_result=False,oracle_is_mathematical_upper_bound=False)


def fit_all(run, X, y, folds, cfg, guard, lineage, fitter=fit_head):
    models=[]
    for i,(train,held) in enumerate(folds):
        guard.check()
        marker=run/f'fold_{i}_started.json'
        if marker.exists():
            raise ValueError('duplicate head fit')
        write(marker,dict(lineage,fold=i,train_indices=train.tolist(),held_indices=held.tolist()))
        guard.fold_start=guard.clock()
        model=fitter(X,y,train,held,cfg,guard)
        guard.check()
        guard.fold_start=None
        verify_head(model,X,y,train,held,cfg)
        write(run/f'fold_{i}_head.json',dict(lineage,fold=i,model=model,resource=guard.receipt()))
        models.append(model)
    return models


def decision(lineage, e, evaluation_sha):
    return dict(lineage,status='inconclusive' if e['protected_primary_pass'] is None else ('protected_net_gain' if e['protected_primary_pass'] else 'stop_negative'),
                evaluation_sha256=evaluation_sha,delta=e['delta'],retention=e['retention'],net_targets=e['net_targets'],
                fresh_access=False,development_allowed=False)


def execute(a, cfg, lock):
    a.run.mkdir(parents=True,exist_ok=False)
    guard=Budget(a.run,cfg['budget'])
    guard.start_monitor()
    lineage=binding(cfg,lock,a)
    write(a.run/'launch_receipt.json',dict(lineage,pid=os.getpid(),started_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),new_model_fits_budget=4))
    try:
        data=load_cached(a.cache,a.metadata,cfg,lock)
        guard.check()
        X=features(data)
        y=labels(data)
        folds=partitions(data,cfg)
        report=audit(data,X,y,folds,cfg)
        write(a.run/'input_audit.json',dict(lineage,**report))
        guard.check()
        if not report['oracle_policy']['protected_primary_pass']:
            write(a.run/'status.json',dict(lineage,state='stop_feasibility',fits_consumed=0,resource=guard.receipt()))
            return
        import torch
        torch.set_num_threads(cfg['threads'])
        torch.manual_seed(cfg['seed'])
        models=fit_all(a.run,X,y,folds,cfg,guard,lineage)
        write(a.run/'four_heads_verified.json',dict(lineage,files={f'fold_{i}_head.json':sha(a.run/f'fold_{i}_head.json') for i in range(4)}))
        write(a.run/'prediction_started.json',lineage)
        q=predict_all(models,X,folds)
        write(a.run/'oof_scores.json',dict(lineage,parent_ids=[r['parent_id'] for r in data['pairs'][1::2]],quality_probabilities=q.tolist()))
        write(a.run/'comparison_started.json',lineage)
        e=evaluate(data,q,cfg)
        write(a.run/'evaluation.json',dict(lineage,**e))
        write(a.run/'decision.json',decision(lineage,e,sha(a.run/'evaluation.json')))
        guard.check()
        write(a.run/'status.json',dict(lineage,state='completed',fits_consumed=4,comparison_count=1,resource=guard.receipt()))
    except BaseException as exc:
        write(a.run/'status.json',dict(lineage,state='failed',reason=str(exc),fits_consumed=len(list(a.run.glob('fold_*_started.json'))),resource=guard.receipt()))
        raise
    finally:
        guard.done.set()


def verify(a, cfg, lock):
    lineage=binding(cfg,lock,a)
    data=load_cached(a.cache,a.metadata,cfg,lock)
    X,y=features(data),labels(data)
    folds=partitions(data,cfg)
    expected_audit=dict(lineage,**audit(data,X,y,folds,cfg))
    if read(a.run/'input_audit.json')!=expected_audit:
        raise ValueError('input audit replay')
    status=read(a.run/'status.json')
    if any(status.get(k)!=v for k,v in lineage.items()):
        raise ValueError('status lineage')
    resource=status['resource']
    if not 0<=resource['elapsed_seconds']<=cfg['budget']['total_wall_seconds'] or not 0<=resource['peak_rss_bytes']<=cfg['budget']['rss_cap_gib']*1024**3:
        raise ValueError('resource receipt')
    if status['state']=='stop_feasibility':
        forbidden=['four_heads_verified.json','prediction_started.json','comparison_started.json','oof_scores.json','evaluation.json','decision.json']
        if expected_audit['oracle_policy']['protected_primary_pass'] or status.get('fits_consumed')!=0 or list(a.run.glob('fold_*')) or any((a.run/n).exists() for n in forbidden):
            raise ValueError('feasibility stop boundary')
        return None,data
    if status['state']!='completed' or status['fits_consumed']!=4 or status['comparison_count']!=1:
        raise ValueError('incomplete execution')
    receipt=read(a.run/'four_heads_verified.json')
    expected=dict(lineage,files={f'fold_{i}_head.json':sha(a.run/f'fold_{i}_head.json') for i in range(4)})
    if receipt!=expected or len(list(a.run.glob('fold_*_started.json')))!=4:
        raise ValueError('four head receipt')
    models=[]
    for i,(train,held) in enumerate(folds):
        payload=read(a.run/f'fold_{i}_head.json')
        if any(payload.get(k)!=v for k,v in lineage.items()) or payload['fold']!=i or read(a.run/f'fold_{i}_started.json')!=dict(lineage,fold=i,train_indices=train.tolist(),held_indices=held.tolist()):
            raise ValueError('head lineage')
        verify_head(payload['model'],X,y,train,held,cfg)
        models.append(payload['model'])
    q=predict_all(models,X,folds)
    expected=dict(lineage,parent_ids=[r['parent_id'] for r in data['pairs'][1::2]],quality_probabilities=q.tolist())
    if read(a.run/'oof_scores.json')!=expected:
        raise ValueError('OOF exact replay')
    e=dict(lineage,**evaluate(data,q,cfg))
    if read(a.run/'evaluation.json')!=e or read(a.run/'decision.json')!=decision(lineage,e,sha(a.run/'evaluation.json')):
        raise ValueError('full protected outcome replay')
    for name in ['prediction_started.json','comparison_started.json']:
        if read(a.run/name)!=lineage:
            raise ValueError('phase marker')
    return e,data


def require_producer(host=None):
    import socket
    if (socket.gethostname() if host is None else host).upper() != 'D-26-09':
        raise PermissionError('E009 actual fitting only on approved D-26-09 producer')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '-1' or os.environ.get('OMP_NUM_THREADS') != '1' or os.environ.get('MKL_NUM_THREADS') != '1':
        raise PermissionError('CPU-only single-thread producer environment required')


def main():
    sys.addaudithook(pixel_guard)
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['execute','verify'])
    for name in ['config','lock','cache','metadata','run']:
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    cfg,lock=verify_source(a.config,a.lock)
    if cfg['protocol']!=PROTOCOL or lock['protocol']!=PROTOCOL:
        raise ValueError('protocol')
    if a.stage=='execute':
        require_producer()
        execute(a,cfg,lock)
    else:
        e,_=verify(a,cfg,lock)
        write(a.run/'verification_receipt.json',dict(status='verified',evaluation_sha256=None if e is None else sha(a.run/'evaluation.json'),source_manifest_sha256=sha(ROOT/CONTRACT/'source_manifest.json'),fits_repeated=0))


if __name__=='__main__':
    main()
