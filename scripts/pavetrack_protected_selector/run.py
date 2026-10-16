#!/usr/bin/env python3
"""E013 producer-only threshold learning; imports and tests do no real fitting."""
import time
BOOT_START=time.monotonic()
import argparse,collections,copy,hashlib,json,os,sys,threading
from pathlib import Path
from contextlib import contextmanager
import importlib.util
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('e013_core',HERE/'core.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
inputs=c.module('e013_inputs',HERE/'inputs.py')

class Guard:
    def __init__(self,cfg,start=None,clock=time.monotonic,memory=None):
        self.cfg=cfg;self.clock=clock;self.start=clock() if start is None else start;self.memory=memory or (lambda:c.e12.runtime.aggregate_memory(c.e12.a.mem.peak_rss));self.peak=0;self.counts=collections.Counter();self.lock=threading.RLock()
    def check(self):
        with self.lock:
            self.peak=max(self.peak,self.memory())
            if self.peak>self.cfg['budget']['peak_RSS_bytes']:raise RuntimeError('RSS_CAP')
            if self.clock()-self.start>self.cfg['budget']['total_wall_seconds']:raise RuntimeError('WALL_CAP')
    def take(self,name,n=1):
        with self.lock:
            if self.counts[name]+n>self.cfg['budget'][name]:raise RuntimeError('COUNT_CAP:'+name)
            self.counts[name]+=n;self.check()
    def receipt(self):return dict(elapsed_seconds=self.clock()-self.start,peak_RSS_bytes=self.peak,counts=dict(self.counts),pixel_reads=0,backbone_forwards=0,head_forwards=0,new_singleton_U=0,linear_solves=0,model_gradient_steps=0,full12_refits=0,fresh_access=False)
    @contextmanager
    def monitor(self,run):
        done=threading.Event()
        def watch():
            while not done.wait(.5):
                try:self.check()
                except BaseException as ex:c.write(run/'status.json',dict(state='stopped_resource',reason=str(ex),resource=self.receipt()));os._exit(71)
        t=threading.Thread(target=watch,daemon=True);t.start()
        try:yield
        finally:done.set();t.join()

def contract(args,guard):
    files=c.read(c.ROOT/c.CONTRACT/'source_manifest.json')['files']
    for name,h in files.items():c.e12.checked(c.ROOT/name,h,guard.check)
    c.e12.checked(args.config,files[c.CONTRACT+'run_config.json'],guard.check);c.e12.checked(args.lock,files[c.CONTRACT+'data_lock.json'],guard.check)
    cfg,lock=c.read(args.config),c.read(args.lock)
    if cfg['protocol']!=c.PROTOCOL or lock['protocol']!=c.PROTOCOL or args.run.name!=cfg['proposed_run_id']:raise ValueError('contract identity')
    return cfg,lock

def fit_and_freeze(data,targets,run,cfg,guard,emit,calibrator=c.calibrate):
    original_digest=c.digest(data['originals']);models=[];support=[];predictions=[];all_added=[]
    # Main fits and predictions finish before diagnostic jackknifes run.
    for k,held in enumerate(cfg['held_groups']):
        fit=[x for x in cfg['locations'] if x not in held];audit=c.support_labels(data['labels'][k],data['candidates'],fit)
        if audit['positive_GT_count']!=cfg['fit']['expected_positive_GT'][k] or len(audit['positive_sites'])!=cfg['fit']['expected_positive_sites'][k] or audit['nonpositive']==0:raise ValueError('FIT support lineage')
        own=c.scoped(data['originals'],data['candidates'],targets,data['image_locations'],fit);model=calibrator(own,cfg,guard);models.append(model);support.append(audit)
        added=c.policy(data['candidates'],model['threshold'],held,cfg);all_added.extend(copy.deepcopy(added));predictions.append(dict(fold=k,held_locations=held,threshold=model['threshold'],source_keys=[r['parent_id'] for r in added],rows=added))
        emit(f'model_fold_{k}.json',model)
    if c.digest(data['originals'])!=original_digest:raise ValueError('original mutation')
    emit('OOF_predictions.json',dict(protocol=c.PROTOCOL,folds=predictions,original_rows_digest=original_digest,GT_free_prediction=True))
    emit('prediction_freeze_receipt.json',dict(protocol=c.PROTOCOL,files={n:c.sha(run/n,guard.check) for n in ['OOF_predictions.json']+[f'model_fold_{k}.json' for k in range(3)]},frozen_before_held_evaluation=True))
    main_digest=c.digest(models);diagnostics=[]
    for k,audit in enumerate(support):
        held=cfg['held_groups'][k];fit=[x for x in cfg['locations'] if x not in held]
        for omitted in audit['positive_sites']:
            locs=[x for x in fit if x!=omitted];own=c.scoped(data['originals'],data['candidates'],targets,data['image_locations'],locs);model=calibrator(own,cfg,guard)
            diagnostics.append(dict(main_fold=k,omitted_location=omitted,threshold_flipped=model['threshold']!=models[k]['threshold'],model=model))
    if c.digest(models)!=main_digest or c.digest(data['originals'])!=original_digest:raise ValueError('diagnostic feedback/mutation')
    emit('jackknife.json',dict(used_to_choose_main=False,scope='correlated location-deletion sensitivity, not independent validation',fits=diagnostics))
    return models,support,sorted(all_added,key=lambda r:r['parent_id'])

def evaluate(data,targets,added,run,cfg,lock,guard,emit):
    receipt=c.read(run/'prediction_freeze_receipt.json')
    for name,h in receipt['files'].items():c.e12.checked(run/name,h,guard.check)
    own=c.scoped(data['originals'],data['candidates'],targets,data['image_locations'],cfg['locations']);ref=c.baseline(own)
    if len(ref[1])!=lock['source_B12_hits']:raise ValueError('B12 baseline lineage')
    guard.take('final_OOF_comparisons');comparison=c.compare(own,added,ref);held=[]
    for locations in cfg['held_groups']:
        scope=c.scoped(data['originals'],data['candidates'],targets,data['image_locations'],locations);group_added=[r for r in added if r['reid'] in locations];guard.take('held_group_comparisons');baseline=c.baseline(scope);held.append(dict(locations=locations,baseline=baseline[0],comparison=c.compare(scope,group_added,baseline)))
    rule=cfg['criterion'];ret=comparison['retention'];delta=comparison['macro_delta'];passed=ret is not None and delta is not None and ret>=rule['old_E003_retention_minimum'] and comparison['net_GT']>=rule['net_new_GT_minimum'] and delta>0
    result=dict(protocol=c.PROTOCOL,primary_pass=passed,status='protected_learned_net_gain' if passed else 'no_protected_learned_net_gain',comparison=comparison,baseline=ref[0],held_groups=held,original_rows_digest=c.digest(data['originals']),originals_unchanged=True,learned_selection=True,GT_informed_selection=False,scope='conditional OOF selector on consumed reused12 sites; not fresh-site generalisation or old282 verification',fresh_access=False)
    # A closed numerical record makes subsequent QA possible without inference.
    emit('evaluation.json',dict(**result,baseline_rows=data['originals'],rows=data['originals']+added,targets=targets,image_locations=data['image_locations']))
    emit('result.json',result);return result

def verify(run,expected,receipt,source_files):
    wanted=set(expected)|{'analysis/F00_learning.png','analysis/F01_detection.png','analysis/F02_cases.png','analysis/README_analysis.md'}|{'input_snapshot/'+n for n in source_files}
    if set(receipt['files'])!=wanted:raise ValueError('strict output inventory')
    for name,h in receipt['files'].items():c.e12.checked(run/name,h)
    for name,value in expected.items():
        if c.read(run/name)!=value:raise ValueError('trusted semantic mismatch:'+name)
    for name,h in source_files.items():c.e12.checked(run/'input_snapshot'/name,h)
    return True

def execute(args,cfg,lock,guard,launch):
    expected={'launch.json':copy.deepcopy(launch)}
    def emit(name,value):expected[name]=copy.deepcopy(value);c.write(args.run/name,value)
    data=inputs.load(args.source,args.run,cfg,lock,guard,c);records=inputs.metadata(args.metadata,cfg,lock,guard,c)
    if set(records)!=set(data['image_locations']) or any(records[im]['reid']!=loc for im,loc in data['image_locations'].items()):raise ValueError('metadata image membership')
    targets={im:r['crack_boxes_xyxy'] for im,r in records.items()};gate=c.e12.PixelGate([]);sys.addaudithook(gate)
    emit('input_audit.json',dict(protocol=c.PROTOCOL,source_zip_sha256=lock['source_zip_sha256'],original_rows_digest=c.digest(data['originals']),originals=len(data['originals']),corrections=len(data['candidates']),eligible=sum(r['eligible'] for r in data['candidates']),feature=cfg['feature'],fitting_info='each explicit FIT scope only',fresh_access=False))
    emit('features.json',dict(names=[cfg['feature']['name']],rows=data['candidates']))
    models,support,added=fit_and_freeze(data,targets,args.run,cfg,guard,emit)
    result=evaluate(data,targets,added,args.run,cfg,lock,guard,emit)
    # Full R004 oracle content is consulted for explanatory comparison only now.
    reference=c.read(data['snapshot']/'qualification.json');emit('reference_only.json',dict(used_for_training=False,source='E012-R004 GT-informed diagnostic',status=reference['status'],retained=reference['joint']['retained_old'],net=reference['joint']['net_targets'],positive_support=reference['held_support']))
    analysis=c.module('e013_analysis',HERE/'analyze.py');analysis.render(args.run,result,models,support,expected['evaluation.json'],guard)
    gate.output.update(os.path.normcase(os.path.abspath(p)) for p in (args.run/'analysis').glob('*.png'))
    if c.digest(data['originals'])!=lock['original_rows_digest']:raise ValueError('original mutation')
    for key in ['threshold_fits','calibration_policy_comparisons','fit_baseline_metrics','final_OOF_comparisons','held_group_comparisons']:
        if guard.counts[key]!=cfg['budget'][key]:raise ValueError('incomplete phase count:'+key)
    emit('resource.json',guard.receipt());receipt=dict(protocol=c.PROTOCOL,files={p.relative_to(args.run).as_posix():c.sha(p,guard.check) for p in sorted(args.run.rglob('*')) if p.is_file()},fresh_access=False);c.write(args.run/'output_receipt.json',receipt);verify(args.run,expected,receipt,lock['source_files']);guard.check();return result

def main():
    p=argparse.ArgumentParser()
    for name in ['config','lock','source','metadata','run']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reviewed-commit',required=True);args=p.parse_args();cfg=c.read(args.config);c.require_producer(cfg);guard=Guard(cfg,start=BOOT_START);cfg,lock=contract(args,guard);args.run.mkdir(parents=True,exist_ok=False)
    launch=dict(protocol=c.PROTOCOL,run_id=args.run.name,reviewed_commit=args.reviewed_commit,source_manifest_sha256=c.sha(c.ROOT/c.CONTRACT/'source_manifest.json'),config_sha256=c.sha(args.config),lock_sha256=c.sha(args.lock),pid=os.getpid(),command=sys.argv,hostname=__import__('socket').gethostname(),started_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),fresh_access=False);c.write(args.run/'launch.json',launch)
    with guard.monitor(args.run):
        try:result=execute(args,cfg,lock,guard,launch);c.write(args.run/'status.json',dict(state='completed',scientific_status=result['status'],resource=guard.receipt(),fresh_access=False))
        except BaseException as ex:c.write(args.run/'status.json',dict(state='stopped',reason=str(ex),resource=guard.receipt(),fresh_access=False));raise
if __name__=='__main__':main()
