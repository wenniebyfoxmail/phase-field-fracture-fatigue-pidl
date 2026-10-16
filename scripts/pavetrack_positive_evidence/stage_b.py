#!/usr/bin/env python3
"""Producer-only frozen E003 rescoring; local imports/test seams do no inference."""
import time
BOOT_START=time.monotonic()
import argparse,copy,collections,hashlib,io,json,math,os,sys,threading,zipfile
from pathlib import Path,PureWindowsPath
from contextlib import contextmanager
import numpy as np
import importlib.util
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=module('e012b_stage_a',Path(__file__).with_name('run.py'));fast=module('e012b_fast',Path(__file__).with_name('fast_labels.py'));runtime=module('e012b_runtime',Path(__file__).with_name('stage_b_runtime.py'))
window=module('e012b_window',Path(__file__).with_name('window_json.py'));a.scoped.Cursor=window.cursor_type(a.scoped.Cursor)
CONTRACT='docs/research/S01/S01-E012/stage_B/';PROTOCOL='S01-E012-B-v1';read=a.read;sha=a.sha;checked=a.checked

def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.tmp');temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf8');temp.replace(path)

class Guard:
    def __init__(self,cfg,clock=time.monotonic,memory=None,start=None):
        self.cfg=cfg;self.clock=clock;self.start=clock() if start is None else start;self.memory=memory or (lambda:runtime.aggregate_memory(a.mem.peak_rss));self.gpu=lambda:(0,0);self.peak=0;self.allocated=0;self.reserved=0;self.counts=collections.Counter();self.lock=threading.RLock()
    def check(self):
        with self.lock:
            self.peak=max(self.peak,self.memory());x,y=self.gpu();self.allocated=max(self.allocated,x);self.reserved=max(self.reserved,y);b=self.cfg['budget']
            if self.peak>b['peak_RSS_bytes']:raise RuntimeError('RSS_CAP')
            if self.allocated>b['peak_GPU_allocated_bytes'] or self.reserved>b['peak_GPU_reserved_bytes']:raise RuntimeError('GPU_CAP')
            if self.clock()-self.start>b['total_wall_seconds']:raise RuntimeError('WALL_CAP')
    def take(self,name,n=1):
        with self.lock:
            if self.counts[name]+n>self.cfg['budget'][name]:raise RuntimeError('COUNT_CAP:'+name)
            self.counts[name]+=n;self.check()
    def receipt(self):
        return dict(elapsed_seconds=self.clock()-self.start,peak_RSS_bytes=self.peak,peak_GPU_allocated_bytes=self.allocated,peak_GPU_reserved_bytes=self.reserved,counts=dict(self.counts),model_fits=0,linear_solves=0,original_E003_rescores=0,new_corrector_predictions=0,fresh_access=False)
    @contextmanager
    def monitor(self,run):
        done=threading.Event()
        def watch():
            while not done.wait(.5):
                try:self.check()
                except BaseException as ex:write(run/'status.json',dict(state='stopped_resource',reason=str(ex),resource=self.receipt(),fresh_access=False));os._exit(71)
        t=threading.Thread(target=watch,daemon=True);t.start()
        try:yield
        finally:done.set();t.join()

def contract(args,guard):
    m=read(ROOT/CONTRACT/'source_manifest.json')['files']
    for n,h in m.items():checked(ROOT/n,h,guard.check)
    checked(args.config,m[CONTRACT+'run_config.json'],guard.check);checked(args.lock,m[CONTRACT+'data_lock.json'],guard.check)
    cfg,lock=read(args.config),read(args.lock)
    if cfg['protocol']!=PROTOCOL or lock['protocol']!=PROTOCOL or args.run.name!=cfg['proposed_run_id']:raise ValueError('protocol/run')
    return cfg,lock

def inputs(args,cfg,lock,guard):
    z=args.stage_a/'delivery/S01-E012-R002-evidence-v1.zip';checked(z,lock['stage_A_zip_sha256'],guard.check);cached={}
    with zipfile.ZipFile(z) as src:
        for n,h in lock['stage_A_files'].items():
            if src.getinfo(n).file_size>128*1024*1024:raise ValueError('input JSON cap')
            raw=src.read(n)
            if hashlib.sha256(raw).hexdigest()!=h:raise ValueError('stage A member '+n)
            cached[n]=json.loads(raw);guard.check()
    acfg=read(ROOT/a.CONTRACT/'run_config.json');alock=read(ROOT/a.CONTRACT/'data_lock.json')
    records=a.metadata(args.metadata,acfg,alock,guard);data=a.load_bank(args.cache,records,acfg,alock,guard)
    if data['mapping']!=cached['identity_mapping.json'] or a.missing_scores(data,alock)!=cached['missing_scores_manifest.json']['rows']:raise ValueError('full source/crop/mapping identity')
    rows=cached['missing_scores_manifest.json']['rows'];expected=cfg['input_counts']
    if (len(records),len(data['originals']),len(rows))!=(expected['images'],expected['original_rows'],expected['corrections']):raise ValueError('frozen counts')
    if any(data['source_files'][n]!=h for n,h in lock['source_files'].items()):raise ValueError('source files')
    image_root=PureWindowsPath(lock['source_image_root'])
    for row in rows:
        if PureWindowsPath(row['prepared_image']).parent!=image_root or row['classifier_sha256']!=lock['E003_checkpoint_sha256']:raise ValueError('image root/classifier')
    data['manifest']=rows;data['stage_A']=cached;return data

class PixelGate:
    def __init__(self,rows):self.allowed={os.path.normcase(os.path.abspath(r['prepared_image'])) for r in rows};self.output=set()
    def __call__(self,event,args):
        if event!='open':return
        try:name=os.fsdecode(args[0])
        except TypeError:return
        flags=args[2] if len(args)>2 else 0;mode=args[1] if len(args)>1 else None
        writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT))
        if not writing and Path(name).suffix.lower() in {'.png','.jpg','.jpeg','.tiff','.tif','.bmp','.gif','.webp'}:
            normalized=os.path.normcase(os.path.abspath(name))
            if normalized not in self.allowed|self.output:raise PermissionError('out-of-scope pixel read')

def score(data,run,cfg,lock,guard,backend,expected=None):
    def emit(name,value):
        if expected is not None:expected[name]=copy.deepcopy(value)
        write(run/name,value)
    marker=run/'scoring_started.json'
    if marker.exists():raise ValueError('duplicate scoring forbidden')
    emit('scoring_started.json',dict(protocol=PROTOCOL,checkpoint_sha256=lock['E003_checkpoint_sha256'],candidates=len(data['manifest'])))
    rows=data['manifest'];path=run/'pooled_features.npy';X=np.lib.format.open_memmap(path,mode='w+',dtype=np.float32,shape=(len(rows),576));X[:]=np.nan;X.flush()
    by=collections.OrderedDict()
    for i,row in enumerate(rows):by.setdefault(row['image_id'],[]).append(i)
    with open(run/'image_progress.jsonl','x',encoding='utf8') as journal:
        for im,ids in by.items():
            guard.check();record=rows[ids[0]]
            if len(ids)>cfg['scoring']['max_actual_crops_per_image']:raise ValueError('image crop cap')
            raw=Path(record['prepared_image']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=record['prepared_image_sha256']:raise ValueError('image content identity')
            guard.take('source_image_decodes');image=backend.image(raw,record);del raw
            try:
                guard.take('new_unique_backbone_crop_rows',len(ids));guard.take('max_backbone_batches');Z=backend.features(image,[rows[i] for i in ids])
            finally:image.close()
            if Z.dtype!=np.float32 or Z.shape!=(len(ids),576) or not np.isfinite(Z).all():raise ValueError('feature shape/finite/dtype')
            X[ids]=Z;X.flush();guard.check()
            journal.write(json.dumps(dict(image_id=im,image_sha256=record['prepared_image_sha256'],indices=ids,features_sha256=hashlib.sha256(np.ascontiguousarray(Z).tobytes()).hexdigest()))+'\n');journal.flush()
    del X
    X=np.load(path,mmap_mode='r',allow_pickle=False)
    if not np.isfinite(X).all():raise ValueError('incomplete features')
    def head(pass_name):
        mark=run/(pass_name+'_started.json')
        if mark.exists():raise ValueError('duplicate head pass')
        emit(pass_name+'_started.json',dict(rows=len(X)));out=[]
        for start in range(0,len(X),cfg['scoring']['head_batch']):
            part=X[start:start+cfg['scoring']['head_batch']];guard.take(pass_name,len(part));guard.take('total_head_rows',len(part));out.extend(backend.probabilities(part));guard.check()
        if len(out)!=len(X) or any(not math.isfinite(p) or not 0<=p<=1 for p in out):raise ValueError('finite probabilities')
        return out
    probabilities=head('head_scoring_rows');emit('scores.json',dict(source_keys=[r['source_parent_key'] for r in rows],probabilities=probabilities))
    replay=head('head_verification_rows')
    if replay!=probabilities:raise ValueError('CPU head exact replay')
    receipt=dict(protocol=PROTOCOL,checkpoint_sha256=lock['E003_checkpoint_sha256'],files={n:sha(run/n,guard.check) for n in ['pooled_features.npy','scores.json','image_progress.jsonl']},rows=len(rows),images=len(by),CPU_head_passes=2,resource=guard.receipt(),fresh_access=False)
    emit('scoring_receipt.json',receipt);return probabilities

def eligibility(data,probabilities,cfg):
    by=collections.defaultdict(list);source={r['parent_id']:r for r in data['originals']}
    for r in data['originals']:by[r['image_id']].append(r)
    rows=[];valid=[]
    for i,(old,new,p) in enumerate(zip(data['pairs'][::2],data['pairs'][1::2],probabilities,strict=True)):
        if old!=source[old['parent_id']]:raise ValueError('source key mapping')
        s=math.sqrt(old['proposer_confidence']*p);ok=s>old['score'] and not any(new['box_xyxy']==r['box_xyxy'] or a.e11.e8.box_iou(new['box_xyxy'],r['box_xyxy'])>cfg['policy']['original_duplicate_iou'] for r in by[old['image_id']])
        rows.append(dict(new,score=s,probability=p,rescored_correction=True));valid.append(ok)
    return rows,valid

def joint(data,corrections,selected,cfg,guard):
    guard.take('joint_comparisons');images=collections.defaultdict(list);accepted=[]
    for i in sorted(selected,key=lambda i:(-corrections[i]['score'],corrections[i]['image_id'],tuple(corrections[i]['box_xyxy']),corrections[i]['parent_id'])):
        row=corrections[i]
        if any(a.e11.e8.box_iou(row['box_xyxy'],r['box_xyxy'])>cfg['policy']['correction_duplicate_iou'] for r in images[row['image_id']]):continue
        accepted.append(row);images[row['image_id']].append(row)
    rows=data['originals']+sorted(accepted,key=lambda r:r['parent_id']);e8=a.e11.e8
    bm=e8.metrics(data['originals'],data['targets'],data['locations'],'score');cm=e8.metrics(rows,data['targets'],data['locations'],'score');before=e8.admitted_targets(data['originals'],data['targets'],bm);after=e8.admitted_targets(rows,data['targets'],cm)
    ret=None if not before else len(before&after)/len(before);delta=None if bm['macro_location_recall'] is None else cm['macro_location_recall']-bm['macro_location_recall'];rule=cfg['downstream_detection_criterion'];net=len(after)-len(before)
    return dict(baseline=bm,candidate=cm,retention_B12=ret,retained_old=len(before&after),lost_old=len(before-after),new_targets=len(after-before),net_targets=net,delta=delta,potential_protected_gain=False if ret is None or delta is None else ret>=rule['old_E003_retention_minimum'] and net>=rule['net_new_GT_minimum'] and delta>0,old_hit_denominator='B12 original budget prefix; not consumed four-site282',selected=len(selected),appended=len(accepted),baseline_FP_types=a.e11.assignment.old.fp_types(data['originals'],data['targets'],bm),candidate_FP_types=a.e11.assignment.old.fp_types(rows,data['targets'],cm),new_identities=[list(v) for v in sorted(after-before)],lost_identities=[list(v) for v in sorted(before-after)],rows=rows,GT_informed=True,learned_result=False)

def qualify(data,probs,run,cfg,guard,expected=None):
    def emit(name,value):
        if expected is not None:expected[name]=copy.deepcopy(value)
        write(run/name,value)
    corrections,eligible=eligibility(data,probs,cfg);reports=[]
    for scope,locs in [('full12',cfg['locations'])]+[('fit8_fold_'+str(i),[x for x in cfg['locations'] if x not in g]) for i,g in enumerate(cfg['held_groups'])]:
        context=fast.Context(data,locs,a.e11.e8.metrics,a.e11.e8.box_iou,guard.check);labels=[]
        for i,(row,ok) in enumerate(zip(corrections,eligible,strict=True)):
            if not ok or row['reid'] not in locs:continue
            guard.take('singleton_slots');value=context.label(row);labels.append(dict(index=i,parent_id=row['parent_id'],image_id=row['image_id'],location=row['reid'],score=row['score'],**value))
        report=dict(scope=scope,locations=locs,baseline=context.metric,rows=labels);emit(scope+'.json',report);reports.append(report)
    full=reports[0]['rows'];fit=[a.support_table(r['rows'],r['scope'],r['locations']) for r in reports[1:]];result=a.decision(full,fit,cfg,True)
    result['joint']=joint(data,corrections,[r['index'] for r in full if r['U']>0],cfg,guard);result['location_support']=[a.support_table(full,'full12_site', [loc]) for loc in cfg['locations']];result['eligible_pairs']=sum(eligible);result['ineligible_pairs']=len(eligible)-sum(eligible);result['scope']='conditional reused12-site support; not old282 or new-site validation'
    selected=[];original={r['parent_id']:r for r in data['originals']}
    for role,pred in [('positive',lambda x:x['U']>0),('harm',lambda x:x['lost']>0),('false_positive',lambda x:x['FP']>0)]:
        seen=set()
        for row in sorted((v for v in full if pred(v)),key=lambda v:(-original[v['parent_id']]['score'],v['image_id'],tuple(original[v['parent_id']]['box_xyxy']),v['parent_id'])):
            if row['location'] in seen:continue
            selected.append(dict(role=role,label=row,original=original[row['parent_id']],corrected=corrections[row['index']],GT=data['targets'][row['image_id']]));seen.add(row['location'])
            if len(seen)==2:break
    emit('cases.json',dict(rule='highest original E003 score, image/box/source key; max2 sites per role',cases=selected,missing_roles=[r for r in ['positive','harm','false_positive'] if not any(v['role']==r for v in selected)]))
    return result,reports

def verify(run,cfg,lock,expected,receipt):
    # No model/image/source GT read and no U replay. Exact original semantic
    # objects remain in memory; self-rehashed result tampering cannot pass.
    required=set(expected)|{'pooled_features.npy','image_progress.jsonl','analysis/F00_support.png','analysis/F01_budget.png','analysis/F02_cases.png','analysis/README_analysis.md'}
    if set(receipt['files'])!=required or receipt['protocol']!=PROTOCOL:raise ValueError('strict output inventory')
    for name,digest in receipt['files'].items():checked(run/name,digest)
    for name,value in expected.items():
        if read(run/name)!=value:raise ValueError('semantic mismatch:'+name)
    scoring=expected['scoring_receipt.json']
    for n,h in scoring['files'].items():checked(run/n,h)
    if scoring['CPU_head_passes']!=2:raise ValueError('head passes')
    return True

def execute(args,cfg,lock,guard,launch):
    expected={'launch.json':copy.deepcopy(launch)}
    def emit(name,value):
        expected[name]=copy.deepcopy(value);write(args.run/name,value)
    data=inputs(args,cfg,lock,guard);gate=PixelGate(data['manifest']);sys.addaudithook(gate)
    checked(args.checkpoint,lock['E003_checkpoint_sha256'],guard.check);backend=runtime.TorchBackend(cfg,args.checkpoint,guard,a.e11.e8.m.base.validate_reranker_checkpoint);checked(args.checkpoint,lock['E003_checkpoint_sha256'],guard.check)
    original_digest=hashlib.sha256(json.dumps(data['originals'],sort_keys=True).encode()).hexdigest()
    emit('candidate_identity.json',dict(stage_A_manifest_sha256=lock['stage_A_files']['missing_scores_manifest.json'],rows=data['manifest']))
    emit('source_receipt.json',dict(protocol=PROTOCOL,locked_inputs=lock,original_rows_digest=original_digest,original_count=len(data['originals']),runtime_identity=getattr(backend,'identity',{'synthetic_test_backend':True})))
    probs=score(data,args.run,cfg,lock,guard,backend,expected);del backend
    result,reports=qualify(data,probs,args.run,cfg,guard,expected)
    if hashlib.sha256(json.dumps(data['originals'],sort_keys=True).encode()).hexdigest()!=original_digest:raise ValueError('original rows changed')
    emit('qualification.json',result)
    analysis=module('e012b_analysis',Path(__file__).with_name('stage_b_analyze.py'));analysis.render(args.run,result,reports,expected['cases.json'],guard)
    gate.output.update(os.path.normcase(os.path.abspath(p)) for p in (args.run/'analysis').glob('*.png'))
    emit('resource.json',guard.receipt())
    receipt=dict(protocol=PROTOCOL,files={p.relative_to(args.run).as_posix():sha(p,guard.check) for p in sorted(args.run.rglob('*')) if p.is_file()},fresh_access=False);write(args.run/'output_receipt.json',receipt);verify(args.run,cfg,lock,expected,receipt);guard.check()
    return result

def main():
    p=argparse.ArgumentParser()
    for n in ['config','lock','stage-a','cache','metadata','checkpoint','run']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--reviewed-commit',required=True);args=p.parse_args();cfg=read(args.config);runtime.production_environment(cfg);guard=Guard(cfg,start=BOOT_START)
    cfg,lock=contract(args,guard);args.run.mkdir(parents=True,exist_ok=False)
    launch=dict(protocol=PROTOCOL,run_id=args.run.name,reviewed_commit=args.reviewed_commit,source_manifest_sha256=sha(ROOT/CONTRACT/'source_manifest.json'),config_sha256=sha(args.config),lock_sha256=sha(args.lock),pid=os.getpid(),hostname=__import__('socket').gethostname(),python=sys.version,executable=sys.executable,command=sys.argv,started_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),fresh_access=False)
    write(args.run/'launch.json',launch)
    with guard.monitor(args.run):
        try:result=execute(args,cfg,lock,guard,launch);write(args.run/'status.json',dict(state='completed',qualification=result['status'],resource=guard.receipt(),fresh_access=False))
        except BaseException as ex:
            phase='incomplete_qualification' if (args.run/'scoring_receipt.json').exists() else 'incomplete_scores'
            write(args.run/'status.json',dict(state='stopped',phase=phase,reason=str(ex),resource=guard.receipt(),fresh_access=False));raise
if __name__=='__main__':main()
