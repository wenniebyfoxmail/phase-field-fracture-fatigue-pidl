"""One finite threshold policy; no learned forward, fitting on import or pixels."""
import copy,hashlib,importlib.util,json,math,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
e12=module('e013_e012',ROOT/'scripts/pavetrack_positive_evidence/stage_b.py');e8=e12.a.e11.e8;assignment=e12.a.e11.assignment
read=e12.read;write=e12.write;sha=e12.sha;CONTRACT='docs/research/S01/S01-E013/';PROTOCOL='S01-E013-v1'

def require_producer(cfg):
    import socket
    if os.name!='nt' or socket.gethostname().upper()!=cfg['producer']['hostname']:raise PermissionError('approved CPU Windows producer only')
    parts=lambda x:[v for v in x.lower().split(chr(92)) if v]
    if parts(subprocess.check_output(['whoami'],text=True).strip())!=parts(cfg['producer']['account']):raise PermissionError('producer account')
    if os.path.normcase(os.path.abspath(sys.executable))!=os.path.normcase(os.path.abspath(cfg['producer']['python'])):raise PermissionError('producer Python')
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='-1' or any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS']):raise PermissionError('CPU thread environment')

def digest(rows):return hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
def group_of(location,cfg):
    found=[i for i,g in enumerate(cfg['held_groups']) if location in g]
    if len(found)!=1:raise ValueError('source group')
    return found[0]

def features(originals,manifest,probabilities,cfg):
    """Payload needs no GT, oracle decisions or pooled values."""
    source={r['parent_id']:r for r in originals}
    if len(source)!=len(originals):raise ValueError('duplicate original IDs')
    pairs=[]
    for row,p in zip(manifest,probabilities,strict=True):
        old=source[row['source_parent_key']]
        if old['image_id']!=row['image_id'] or old['reid']!=row['location'] or old['box_xyxy']!=row['original_box_xyxy']:raise ValueError('candidate identity')
        if row['corrector_fold']!=group_of(old['reid'],cfg):raise ValueError('source fold identity')
        if not math.isfinite(p) or not 0<=p<=1:raise ValueError('corrected probability')
        new=dict(old,candidate_id='c:'+str(old['parent_id']),kind='correction',original_box_xyxy=old['box_xyxy'],box_xyxy=row['corrected_box_xyxy'])
        if len(new['box_xyxy'])!=4 or not all(math.isfinite(v) for v in new['box_xyxy']):raise ValueError('box')
        x1,y1,x2,y2=new['box_xyxy']
        if not 0<=x1<x2<=row['width'] or not 0<=y1<y2<=row['height']:raise ValueError('box bounds')
        pairs.extend([old,new])
    corrected,eligible=e12.eligibility(dict(originals=originals,pairs=pairs),probabilities,cfg)
    clip=cfg['feature']['probability_clip']
    def logit(p):
        if not math.isfinite(p) or not 0<=p<=1:raise ValueError('original probability')
        p=min(1-clip,max(clip,p));return math.log(p/(1-p))
    out=[]
    for i,(new,ok) in enumerate(zip(corrected,eligible,strict=True)):
        old=source[new['parent_id']];x=logit(new['probability'])-logit(old['probability'])
        out.append(dict(index=i,parent_id=new['parent_id'],location=new['reid'],image_id=new['image_id'],x=x,eligible=ok,row=new))
    if len({v['parent_id'] for v in out})!=len(out):raise ValueError('duplicate correction IDs')
    return out

def policy(candidates,threshold,locations,cfg):
    if threshold not in cfg['feature']['thresholds']:raise ValueError('unfrozen threshold')
    if threshold=='abstain':return []
    seen={};counts={};accepted=[]
    rows=[c for c in candidates if c['location'] in locations and c['eligible'] and c['x']>=threshold]
    rows.sort(key=lambda c:(-c['row']['score'],c['image_id'],tuple(c['row']['box_xyxy']),c['parent_id']))
    for c in rows:
        im=c['image_id'];group=group_of(c['location'],cfg);prior=seen.get(im,[])
        if any(e8.box_iou(c['row']['box_xyxy'],r['box_xyxy'])>cfg['policy']['correction_duplicate_iou'] for r in prior):continue
        if len(prior)>=cfg['policy']['max_per_image'] or counts.get(group,0)>=cfg['policy']['max_per_source_group']:continue
        accepted.append(c['row']);seen.setdefault(im,[]).append(c['row']);counts[group]=counts.get(group,0)+1
    return sorted(accepted,key=lambda r:r['parent_id'])

def scoped(originals,candidates,targets,image_locations,locations):
    locs=set(locations);ims={im for im,loc in image_locations.items() if loc in locs}
    return dict(originals=copy.deepcopy([r for r in originals if r['image_id'] in ims]),candidates=copy.deepcopy([r for r in candidates if r['image_id'] in ims]),targets={im:copy.deepcopy(targets[im]) for im in ims},image_locations={im:image_locations[im] for im in ims},locations=list(locations))

def baseline(data):
    metric=e8.metrics(data['originals'],data['targets'],data['image_locations'],'score');hits=e8.admitted_targets(data['originals'],data['targets'],metric)
    return metric,hits

def compare(data,added,reference):
    before,old=reference;rows=data['originals']+added
    metric=e8.metrics(rows,data['targets'],data['image_locations'],'score');hits=e8.admitted_targets(rows,data['targets'],metric)
    ret=None if not old else len(old&hits)/len(old);delta=None if before['macro_location_recall'] is None else metric['macro_location_recall']-before['macro_location_recall']
    classified=assignment.classified(rows,data['targets'],metric)
    fp=sum(hit is None and row['kind']=='correction' for row,hit in classified)
    return dict(retention=ret,retained_old=len(old&hits),lost_old=len(old-hits),new_GT=len(hits-old),net_GT=len(hits)-len(old),macro_delta=delta,added_FP=fp,appended=len(added),new_identities=[list(v) for v in sorted(hits-old)],lost_identities=[list(v) for v in sorted(old-hits)],candidate=metric)

def choose(table):
    active=[r for r in table if r['threshold']!='abstain' and r['comparison']['retention']==1 and r['comparison']['net_GT']>=1 and r['comparison']['macro_delta'] is not None and r['comparison']['macro_delta']>0]
    if not active:return 'abstain'
    return max(active,key=lambda r:(r['comparison']['net_GT'],-r['comparison']['added_FP'],-r['comparison']['appended'],r['threshold']))['threshold']

def calibrate(data,cfg,guard,metric=compare):
    require_producer(cfg);guard.take('threshold_fits');guard.take('fit_baseline_metrics');ref=baseline(data);table=[]
    for threshold in cfg['feature']['thresholds']:
        guard.take('calibration_policy_comparisons');added=policy(data['candidates'],threshold,data['locations'],cfg);score=metric(data,added,ref);guard.check();table.append(dict(threshold=threshold,source_keys=[r['parent_id'] for r in added],comparison=score))
    threshold=choose(table)
    return dict(threshold=threshold,locations=data['locations'],baseline=ref[0],training_original_digest=digest(data['originals']),policies=table,abstained=threshold=='abstain',selection_reason='no protected FIT gain' if threshold=='abstain' else 'FIT netGT, correction FP, exposure, then larger threshold')

def support_labels(payload,candidates,locations):
    if set(payload['locations'])!=set(locations):raise ValueError('FIT label scope')
    by={c['index']:c for c in candidates};positive=set();sites=set();negative=0
    expected=[c['index'] for c in candidates if c['eligible'] and c['location'] in locations]
    if [r['index'] for r in payload['rows']]!=expected:raise ValueError('FIT label completeness/order')
    for row in payload['rows']:
        c=by[row['index']]
        if c['image_id']!=row['image_id'] or any(v[0]!=c['image_id'] for v in row['new_identities']+row['lost_identities']) or c['parent_id']!=row['parent_id'] or c['location']!=row['location'] or c['location'] not in locations or not c['eligible']:raise ValueError('FIT label identity')
        if row['U']!=row['new']-row['lost']-row['FP']:raise ValueError('FIT U algebra')
        if row['U']>0:positive.update(tuple(v) for v in row['new_identities']);sites.add(c['location'])
        else:negative+=1
    return dict(positive_GT_count=len(positive),positive_sites=sorted(sites,key=int),nonpositive=negative)
