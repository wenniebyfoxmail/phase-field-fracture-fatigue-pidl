#!/usr/bin/env python3
"""S01-E012 Stage A. Cache-only evidence qualification; never train or score crops."""
from pathlib import Path
import argparse, collections, copy, hashlib, importlib.util, json, math, os, sys, time, threading
from contextlib import contextmanager
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
scoped=module('e012_scoped',Path(__file__).with_name('scoped_json.py'))
e11=module('e012_frozen_utility',ROOT/'scripts/pavetrack_scalar_utility_cv/run.py')
PROTOCOL='S01-E012-v1'; CONTRACT='docs/research/S01/S01-E012/'
read=e11.read;write=e11.write

def sha(path,check=lambda:None):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        while b:=f.read(1024*1024): h.update(b);check()
    return h.hexdigest()

def checked(path,digest,check=lambda:None):
    if sha(path,check)!=digest: raise ValueError('identity mismatch: '+str(path))

class Guard:
    def __init__(self,cfg,clock=time.monotonic,memory=e11.e9.peak_rss):
        self.cfg=cfg['stage_A'];self.clock=clock;self.memory=memory;self.start=clock();self.peak=0;self.labels=0
    def check(self):
        self.peak=max(self.peak,self.memory())
        if self.peak>self.cfg['peak_RSS_bytes']: raise RuntimeError('RSS_CAP')
        if self.clock()-self.start>self.cfg['wall_seconds']: raise RuntimeError('WALL_CAP')
    def label(self):
        self.labels+=1
        if self.labels>self.cfg['max_singleton_evaluations']: raise RuntimeError('SINGLETON_CAP')
        self.check()
    @contextmanager
    def monitor(self, run):
        done=threading.Event()
        def watch():
            while not done.wait(.5):
                try: self.check()
                except BaseException as ex:
                    write(run/'status.json',dict(state='stopped_resource',reason=str(ex),fresh_access=False));os._exit(71)
        thread=threading.Thread(target=watch,daemon=True);thread.start()
        try: yield
        finally: done.set();thread.join()
    def receipt(self):
        self.check();return dict(elapsed_seconds=self.clock()-self.start,peak_rss_bytes=self.peak,singleton_evaluations=self.labels,model_fits=0,linear_solves=0,new_inference=0,pixel_reads=0,feature_extraction=0,fresh_access=False)

def contract(config,lock,guard=None):
    check=(lambda:None) if guard is None else guard.check
    check()
    manifest=read(ROOT/CONTRACT/'source_manifest.json')['files']
    for name,digest in manifest.items(): checked(ROOT/name,digest,check)
    checked(config,manifest[CONTRACT+'run_config.json'],check);checked(lock,manifest[CONTRACT+'data_lock.json'],check)
    cfg,lk=read(config),read(lock)
    if cfg['protocol']!=PROTOCOL or lk['protocol']!=PROTOCOL or cfg['locations']!=lk['target_locations'] or cfg['held_groups']!=lk['groups']: raise ValueError('protocol/range mismatch')
    return cfg,lk

def bounded_rows(iterator,limit,reason):
    rows=[]
    for row in iterator:
        rows.append(row)
        if len(rows)>limit: raise RuntimeError(reason+': observed at least '+str(len(rows)))
    return rows

def metadata(path,cfg,lock,guard):
    checked(path,lock['metadata_sha256'],guard.check)
    c=scoped.Cursor(path,guard.check)
    try:
        spans=dict(c.fields());rows=bounded_rows(c.selected_rows(spans['records'],set(cfg['locations'])),cfg['stage_A']['max_images'],'IMAGE_CAP')
    finally: c.close()
    if len(rows)>cfg['stage_A']['max_images']: raise RuntimeError('IMAGE_CAP: '+str(len(rows)))
    if len({r['image_id'] for r in rows})!=len(rows) or {str(r['reid']) for r in rows}!=set(cfg['locations']): raise ValueError('metadata unique/complete locations')
    for r in rows:
        if r['split']!='train' or r['width']<=0 or r['height']<=0 or not r['prepared_image_sha256'] or not r['prepared_image']: raise ValueError('metadata train/dimensions/image identity')
        for b in r['crack_boxes_xyxy']: box(b,r)
    return {r['image_id']:r for r in rows}

def box(value,record):
    if len(value)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in value): raise ValueError('finite xyxy')
    a,b,c,d=value
    if not (0<=a<c<=record['width'] and 0<=b<d<=record['height']): raise ValueError('box bounds')

def selected_map(c,span,keys):
    end=c.tell();out={}
    for key,item in c.fields(span[0]):
        if key in keys: out[key]=c.decode(item)
    c.seek(end);return out

def load_bank(cache,records,cfg,lock,guard):
    if cache.name!=lock['source_run']: raise ValueError('source run identity')
    checked(cache/'feature_receipt.json',lock['source_receipt_sha256'],guard.check);receipt=read(cache/'feature_receipt.json')
    if set(receipt['files'])!={'paired_train_features.npz','train_bank.json','correction_heads.json','label_audit.json'} or receipt['protocol']!='S01-E007-v1': raise ValueError('receipt inventory/protocol')
    # Arrays/embeddings are deliberately neither opened nor needed. Three JSON payloads only.
    for name in ['train_bank.json','correction_heads.json','label_audit.json']: checked(cache/name,receipt['files'][name],guard.check)
    c=scoped.Cursor(cache/'train_bank.json',guard.check)
    try:
        spans=dict(c.fields());original=list(c.selected_rows(spans['original_rows'],set(cfg['locations'])));pairs=bounded_rows(c.selected_rows(spans['bank'],set(cfg['locations'])),2*cfg['stage_A']['max_corrections'],'CORRECTION_CAP')
        targets=selected_map(c,spans['targets'],set(records));locations=selected_map(c,spans['image_locations'],set(records))
    finally: c.close()
    if len(pairs)%2 or len(pairs)//2>cfg['stage_A']['max_corrections']: raise RuntimeError('CORRECTION_CAP/order: '+str(len(pairs)//2))
    if targets!={k:r['crack_boxes_xyxy'] for k,r in records.items()} or locations!={k:r['reid'] for k,r in records.items()}: raise ValueError('targets/locations identity')
    source_ids=[r['parent_id'] for r in original]
    if len(source_ids)!=len(set(source_ids)) or source_ids!=sorted(source_ids) or any(type(v)!=int or v<0 for v in source_ids): raise ValueError('source parent keys')
    by_id={r['parent_id']:r for r in original};by_image=collections.defaultdict(list)
    for r in original:
        rec=records[r['image_id']];box(r['box_xyxy'],rec)
        if r['reid']!=rec['reid'] or r['kind']!='original' or r['candidate_id']!='o:'+str(r['parent_id']): raise ValueError('original identity')
        for name in ['proposer_confidence','probability','score']:
            if not math.isfinite(r[name]) or not 0<=r[name]<=1: raise ValueError('probability/score')
        if r['score']!=math.sqrt(r['proposer_confidence']*r['probability']) or r['E003_score']!=r['score']: raise ValueError('original E003 score')
        by_image[r['image_id']].append(r)
    chosen=set()
    for rows in by_image.values(): chosen.update(r['parent_id'] for r in sorted(rows,key=lambda r:(-r['E003_score'],tuple(r['box_xyxy']),r['parent_id']))[:cfg['stage_A']['parent_cap_per_image']])
    if [r['parent_id'] for r in pairs[::2]]!=sorted(chosen): raise ValueError('GT-free parent-cap inventory')
    heads=read(cache/'correction_heads.json')['models'];ancestry=[]
    if len(heads)!=4: raise ValueError('head count')
    for i,group in enumerate(cfg['held_groups']):
        h=heads[i];fit=[v for v in cfg['locations'] if v not in group]
        if h['fold']!=i or h['held_locations']!=group or h['fit_locations']!=fit or len(h['fit_ids'])!=len(set(h['fit_ids'])): raise ValueError('OOF head membership')
        ancestry.append(dict(fold=i,held_locations=group,fit_locations=fit,fit_ids_count=len(h['fit_ids']),source_heads_sha256=receipt['files']['correction_heads.json'],verification='locked previously verified E007 correction assignment; no new corrector inference'))
    mapping=[]
    for old,new in zip(pairs[::2],pairs[1::2],strict=True):
        pid=old['parent_id'];rec=records[old['image_id']]
        if old!=by_id[pid] or new['parent_id']!=pid or new['image_id']!=old['image_id'] or new['reid']!=old['reid'] or new['kind']!='correction' or new['candidate_id']!='c:'+str(pid) or new['original_box_xyxy']!=old['box_xyxy']: raise ValueError('pair mapping')
        box(new['box_xyxy'],rec);fold=next(i for i,g in enumerate(cfg['held_groups']) if old['reid'] in g)
        mapping.append(dict(source_run=lock['source_run'],source_parent_key=pid,image_id=old['image_id'],location=old['reid'],original_box_xyxy=old['box_xyxy'],corrected_box_xyxy=new['box_xyxy'],corrector_fold=fold))
    return dict(originals=original,pairs=pairs,targets=targets,locations=locations,records=records,mapping=mapping,ancestry=ancestry,source_files=receipt['files'])

def crop_box(b,record,padding=.1):
    # Exact E008 -> E005 context_box -> E003 pad_box then Python round.
    return list(e11.e8.m.box.context_box(b,record,padding))

def geometry(data,cfg,guard):
    old={};expanded={};original_by=collections.defaultdict(list);correction_by=collections.defaultdict(list)
    for r in data['originals']: original_by[r['image_id']].append(r)
    for r in data['pairs'][1::2]: correction_by[r['image_id']].append(r)
    for im,gt in data['targets'].items():
        guard.check();original=original_by[im];corrected=correction_by[im]
        for j,b in enumerate(gt):
            if any(e11.e8.box_iou(b,r['box_xyxy'])>=.5 for r in original): old[(im,j)]=data['locations'][im]
            if any(e11.e8.box_iou(b,r['box_xyxy'])>=.5 for r in original+corrected): expanded[(im,j)]=data['locations'][im]
    gains=[dict(image_id=im,gt_index=j,location=expanded[(im,j)]) for im,j in sorted(set(expanded)-set(old))]
    groups=[dict(group=i,original_GT=sum(loc in g for loc in old.values()),union_GT=sum(loc in g for loc in expanded.values()),new_GT=sum(v['location'] in g for v in gains),new_sites=len({v['location'] for v in gains if v['location'] in g})) for i,g in enumerate(cfg['held_groups'])]
    return dict(original_geometry_GT=len(old),union_geometry_GT=len(expanded),new_geometry_GT=gains,new_geometry_sites=sorted({r['location'] for r in gains},key=int),by_source_group=groups,not_operating_detection=True)

def missing_scores(data,lock):
    # No registered corrected-score receipt for these sites exists in the frozen
    # allowlist. Never infer scores from E007's inherited probability/embeddings.
    rows=[]
    for identity in data['mapping']:
        rec=data['records'][identity['image_id']]
        rows.append(dict(identity,prepared_image=rec['prepared_image'],prepared_image_sha256=rec['prepared_image_sha256'],width=rec['width'],height=rec['height'],crop_padding=.1,crop_box_xyxy=crop_box(identity['corrected_box_xyxy'],rec),classifier_sha256=lock['frozen_E003_ranker_sha256'],required_scoring_recipe='exact frozen E008 576 pooled features + frozen E003 standardization/ranker; original image/crop transforms; no fitting',score=None,U=None,reason='no approved corrected-crop score cache for this identity'))
    return rows

def support_table(rows,scope,locations):
    selected=[r for r in rows if r['location'] in locations];gt=sorted({tuple(h) for r in selected if r['U']>0 for h in r['new_identities']});sites=sorted({r['location'] for r in selected if r['U']>0 and r['new_identities']},key=int)
    return dict(scope=scope,locations=locations,positive_pairs=sum(r['U']>0 for r in selected),zero_pairs=sum(r['U']==0 for r in selected),negative_pairs=sum(r['U']<0 for r in selected),positive_GT=[list(g) for g in gt],positive_GT_count=len(gt),positive_sites=sites)

def decision(full,fit,cfg,complete):
    held=[support_table(full,'full12_group_'+str(i),g) for i,g in enumerate(cfg['held_groups'])]
    distributed=complete and all(t['positive_GT_count']>=cfg['criterion']['minimum_distinct_positive_GT_per_group'] and len(t['positive_sites'])>=cfg['criterion']['minimum_positive_sites_per_group'] for t in held) and all(t['positive_pairs']>0 and t['zero_pairs']+t['negative_pairs']>0 for t in fit)
    status='incomplete_scores' if not complete else 'qualified_distributed_support' if distributed else 'partial_useful_support' if any(t['positive_GT_count'] for t in held) else 'no_qualified_positive'
    return dict(status=status,held_support=held,fit_support=fit,L2=distributed,learned_detection_result=False,fresh_access=False)


def execute(args,cfg,lock,guard):
    records=metadata(args.metadata,cfg,lock,guard);data=load_bank(args.cache,records,cfg,lock,guard)
    expected={}
    def emit(name,value):
        expected[name]=copy.deepcopy(value);write(args.run/name,value)
    emit('inventory.json',dict(protocol=PROTOCOL,locations=cfg['locations'],images=len(records),originals=len(data['originals']),corrections=len(data['pairs'])//2,parsed_GT_locations=cfg['locations'],source_files=data['source_files'],ancestry=data['ancestry'],score_cache_allowlist=[],inherited_probability_not_rescore=True,fresh_access=False))
    emit('identity_mapping.json',data['mapping']);geo=geometry(data,cfg,guard);emit('geometry.json',geo)
    missing=missing_scores(data,lock);emit('missing_scores_manifest.json',dict(protocol=PROTOCOL,rows=missing,expected_forwards=len(missing),unique_images=len({r['image_id'] for r in missing}),source_receipt_sha256=lock['source_receipt_sha256'],source_bank_sha256=data['source_files']['train_bank.json'],fresh_access=False))
    fit=[support_table([],'fit8_fold_'+str(i),[v for v in cfg['locations'] if v not in g]) for i,g in enumerate(cfg['held_groups'])];result=decision([],fit,cfg,False)
    for table in result['held_support']+result['fit_support']:
        table['missing_score_pairs']=sum(r['location'] in table['locations'] for r in missing);table['computed_utility_pairs']=0;table['positive_pairs']=table['zero_pairs']=table['negative_pairs']=None;table['positive_GT_count']=None;table['positive_GT']=None;table['positive_sites']=None
    result.update(L0=True,L1_geometry_progress=bool(geo['new_geometry_GT']),utility_unavailable=True,joint_diagnostic=None,actual_detector_retention=None,actual_detector_net_gain=None,next_action='prepare exact Stage B frozen E003 rescore approval; no execution authorised')
    emit('qualification.json',result)
    emit('cases.json',case_rows(data,missing,guard))
    (args.run/'stage_B_request.md').write_text(f'''# Stage B preparation only — NOT execution approval\n\nScope: same twelve existing training sites, {len(missing)} corrected crops in {len(records)} images. Exact identities, source heads, coordinates, padded crop bounds and image hashes are in missing_scores_manifest.json. Reuse frozen E003 scoring recipe from reviewed E008; preserve all original E003 rows. No new corrector/model fits, altered boxes or fresh sites.\n\nRequired next work: implement only the frozen score export, bind exact source/encoder/ranker/preprocessing identities, freeze CPU/GPU forward count (maximum {len(missing)}), machine, memory, elapsed-time limits and output receipt. Obtain independent code review and user approval of the final source transfer/public branch/execution version before any pixel reads or forward pass. Current Stage A has no crop score input and reports U unavailable, never zero.\n\nThis manifest bounds a concrete enrichment job; it is not a claim that missing scores caused E011 failure. After rescore, compute distributed positive-U support under the unchanged detection budget before designing a head.\n''',encoding='utf-8')
    # Analysis runs in-process so its elapsed time and RSS are included.
    analysis=module('e012_analysis',Path(__file__).with_name('analyze.py'));analysis.render(args.run,guard)
    emit('resource.json',guard.receipt())
    return expected

def case_rows(data,missing,guard):
    selected=[];seen=set();original_by={r['parent_id']:r for r in data['originals']}
    for r in sorted(missing,key=lambda v:(-original_by[v['source_parent_key']]['score'],v['image_id'],tuple(v['original_box_xyxy']),v['source_parent_key'])):
        guard.check()
        if r['location'] in seen: continue
        selected.append(dict(role='unavailable',**r,GT=data['targets'][r['image_id']]))
        seen.add(r['location'])
        if len(selected)==2: break
    return dict(rule='highest original E003 score then image/box/source key; at most two distinct locations per role',missing_roles=['positive_U','negative_U'],cases=selected)

REQUIRED_FILES={'launch.json','inventory.json','identity_mapping.json','geometry.json','missing_scores_manifest.json','qualification.json','cases.json','resource.json','stage_B_request.md','analysis/F00_support.png','analysis/F01_geometry.png','analysis/F02_cases.png','analysis/README_analysis.md'}

def verify(run,cfg,guard,expected):
    """Compare saved semantics with trusted in-memory results from scoped inputs.

    expected must come from execute(), never from re-reading output JSON.
    No labels, forward passes or fits are repeated by this verifier.
    """
    receipt=read(run/'output_receipt.json')
    if set(receipt)!= {'protocol','files','fresh_access'} or receipt['protocol']!=PROTOCOL or receipt['fresh_access'] is not False or set(receipt['files'])!=REQUIRED_FILES: raise ValueError('exact output inventory/protocol required')
    if set(expected)!= {v for v in REQUIRED_FILES if v.endswith('.json')}: raise ValueError('trusted expected semantic inventory required')
    for name,digest in receipt['files'].items(): checked(run/name,digest,guard.check)
    for name,value in expected.items():
        if read(run/name)!=value: raise ValueError('output semantic mismatch: '+name)
    q=read(run/'qualification.json');inv=read(run/'inventory.json');missing=read(run/'missing_scores_manifest.json')
    if q['status']!='incomplete_scores' or q['L2'] or q['joint_diagnostic'] is not None or inv['score_cache_allowlist'] or len(missing['rows'])!=inv['corrections']: raise ValueError('missing-score semantics')
    if q['actual_detector_retention'] is not None or q['actual_detector_net_gain'] is not None: raise ValueError('unmeasured detection result')
    return True

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--lock',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--reviewed-commit',required=True);a=p.parse_args()
    e11.require_producer();guard=Guard(read(a.config));cfg,lock=contract(a.config,a.lock,guard)
    if a.run.name!='S01-E012-R001': raise ValueError('fixed run identity')
    a.run.mkdir(parents=True,exist_ok=False);sys.addaudithook(e11.pixel_guard)
    with guard.monitor(a.run):
        try:
            launch=dict(protocol=PROTOCOL,reviewed_commit=a.reviewed_commit,source_manifest_sha256=sha(ROOT/CONTRACT/'source_manifest.json'),config_sha256=sha(a.config),lock_sha256=sha(a.lock),pid=os.getpid(),hostname=__import__('socket').gethostname(),started_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),python_executable=sys.executable,python_version=sys.version,command=sys.argv,cache=str(a.cache),metadata=str(a.metadata),output=str(a.run),environment={v:os.environ.get(v) for v in ['CUDA_VISIBLE_DEVICES','OMP_NUM_THREADS','MKL_NUM_THREADS']},fresh_access=False)
            write(a.run/'launch.json',launch)
            expected=execute(a,cfg,lock,guard);expected['launch.json']=launch
            e11.OUTPUT_IMAGE_DIGEST_PATHS.update(os.path.normcase(os.path.abspath(f)) for f in (a.run/'analysis').glob('*.png'))
            files={f.relative_to(a.run).as_posix():sha(f,guard.check) for f in sorted(a.run.rglob('*')) if f.is_file()}
            write(a.run/'output_receipt.json',dict(protocol=PROTOCOL,files=files,fresh_access=False));verify(a.run,cfg,guard,expected)
            write(a.run/'status.json',dict(state='completed',scientific_claim='training_evidence_incomplete_scores',resource=guard.receipt(),fresh_access=False))
        except Exception as ex:
            write(a.run/'status.json',dict(state='stopped',reason=str(ex),fresh_access=False));raise
if __name__=='__main__': main()
