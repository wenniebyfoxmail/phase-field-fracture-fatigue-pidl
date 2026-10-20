"""Production phase functions. Imported tests inject mocks; no work on import."""
import collections,copy,hashlib,io,json
from pathlib import Path
import numpy as np
import e029_support as c
import e029_inputs as inputs
from e029_permissions import inference_payload

def bank(paths,lock,plan,cfg,run,out,guard):
    data=inputs.bank(paths,lock,cfg,guard,out);c.write(out/'bank.json',data)
    # Only inference heads/gates from original models; policies/GT tails skipped.
    models=[]
    for k in range(3):
        saved=inputs.inference_from_saved(paths[f'E018_model_{k}'])
        saved.update(fold=k,arm='saved_E018_geometry',held_locations=cfg['held_groups'][k],source_digest=lock['bundle_identity'])
        inference_payload(saved,k,'saved_E018_geometry',cfg['held_groups'][k],lock['bundle_identity']);models.append(saved)
    old=c.read(paths['E018_OOF'])
    if [r['fold'] for r in old['folds']]!=list(range(3)):raise ValueError('B1 fold keys')
    expected=[]
    for k,row in enumerate(old['folds']):
        if row['held_locations']!=cfg['held_groups'][k] or any(data['image_locations'][r['image_id']] not in row['held_locations'] for r in row['rows']):raise ValueError('B1 held scope')
        expected.append(dict(fold=k,threshold=row['threshold'],source_keys=row['source_keys'],rows=row['rows'],features_and_predictions=row['features_and_predictions']))
        if models[k]['threshold']!=row['threshold']:raise ValueError('B1 gate binding')
    c.write(out/'B1.json',dict(models=models,folds=expected))

def spatial(paths,lock,plan,cfg,run,out,guard,engine):
    bank=c.read(run/'bank/bank.json');scope=c.read(paths['R002_scope']);lookup={r['index']:j for j,r in enumerate(scope['rows'])}
    if len(lookup)!=12238 or set(scope['images'])!={im for im,loc in bank['image_locations'].items() if loc in plan['qualification_reused']}:raise ValueError('R002 map scope')
    for r in scope['rows']:
        b=bank['candidates'][r['index']]
        if (r['image_id'],r['location'],r['context'])!=(b['image_id'],b['location'],bank['contexts'][r['index']]):raise ValueError('R002 context/source index')
        if scope['images'][r['image_id']]!=bank['images'][r['image_id']]:raise ValueError('R002 source SHA/geometry')
    by=collections.defaultdict(list)
    for r in bank['candidates']:by[r['image_id']].append(r)
    new=sorted(set(bank['images'])-set(scope['images']))
    if len(new)!=497:raise ValueError('missing image inventory')
    case_ids=[]
    for g in plan['held_groups']:
        ims=[im for im in new if bank['image_locations'][im] in g]
        for im in [ims[0],ims[-1]]:case_ids.append(min(r['index'] for r in by[im]))
    if len(set(case_ids))!=6:raise ValueError('case identity')
    cache=np.lib.format.open_memmap(out/'native_max.npy',mode='w+',dtype=np.float32,shape=(31156,32,32))
    with np.load(paths['R002_projections'],allow_pickle=False) as old:
        reused=old['native_max']
        if reused.shape!=(12238,32,32) or reused.dtype!=np.float32:raise ValueError('reuse map geometry')
        for i,j in lookup.items():cache[i]=reused[j];guard.take('reused_contexts')
    from PIL import Image
    geometry=c.adapter.geometry
    cases=[];progress=[]
    for im in new:
        rec=bank['images'][im];raw=c.image_path(rec,plan).read_bytes();guard.take('source_image_reads')
        if hashlib.sha256(raw).hexdigest()!=rec['prepared_image_sha256']:raise ValueError('source RGB byte identity')
        guard.take('source_image_decodes')
        with Image.open(io.BytesIO(raw)) as source:
            if source.size!=(1920,1080):raise ValueError('source dimensions')
            with source.convert('RGB') as rgb:array=np.asarray(rgb,dtype=np.uint8).transpose(2,0,1).copy()
        field=geometry.native_predict(array,engine.predict,guard.take);field_sha=hashlib.sha256(field.tobytes()).hexdigest()
        for row in by[im]:
            i=row['index'];ctx=bank['contexts'][i];_,cache[i]=geometry.reduce(field,ctx);guard.take('new_contexts')
            if i in case_ids:
                x1,y1,x2,y2=ctx;np.save(out/f'case_{i}_rgb.npy',array[:,y1:y2,x1:x2]);cases.append(dict(index=i,image_id=im,context=ctx,source_sha256=rec['prepared_image_sha256']));guard.take('case_captures')
        progress.append(dict(image_id=im,source_sha256=rec['prepared_image_sha256'],native_field_sha256=field_sha,contexts=[r['index'] for r in by[im]]));c.write(out/'progress.json',progress)
        cache.flush();del array,field;guard.check()
    if engine.verify_unchanged()!=lock['state_digest']:raise ValueError('frozen spatial state digest')
    desc=[]
    for row in bank['candidates']:
        i=row['index'];p=cache[i];geometry.validate_probability(p,(32,32))
        desc.append(dict(index=i,parent_id=row['parent_id'],image_id=row['image_id'],location=row['location'],**{a:c.adapter.describe(p,row['row']['original_box_xyxy'],row['row']['box_xyxy'],bank['contexts'][i],a) for a in c.adapter.ARMS}));guard.take('descriptor_rows')
    cache.flush();del cache
    c.write(out/'descriptors.json',desc);c.write(out/'cases.json',dict(rule='before GT: first/last new image in each original four-site group, first context; six unique fixed cases',cases=sorted(cases,key=lambda r:case_ids.index(r['index']))))
    c.write(out/'spatial_freeze.json',dict(state_digest=lock['state_digest'],files={p.name:c.sha(p) for p in out.iterdir() if p.is_file()},all_before_any_FIT_supervision=True,source_images=497,new_forwards=19880,reused_images=338,reused_contexts=12238))

def fit(paths,lock,plan,cfg,run,out,guard,k):
    bank=c.read(run/'bank/bank.json');spatial=c.read(run/'spatial/descriptors.json');loc=[x for x in cfg['locations'] if x not in cfg['held_groups'][k]]
    own=c.scoped_bank(bank,loc);own['targets']=inputs.targets(paths['metadata'],loc,bank['image_locations'],guard)
    ref=c.core.baseline(own);guard.take('FIT_baselines')
    raw=inputs.zip_values(paths['E017_zip'],lock,'fit',k)
    cached=json.loads(raw[f'input_snapshot/fit8_fold_{k}.json']);supervised=json.loads(raw[f'supervision_fold_{k}.json']);context_saved=json.loads(raw[f'context_fold_{k}.json'])
    support=c.supervision.validate_supervision(supervised,cached,own,ref,k,c.core,c.locality,c.audit)
    if support['positive_GT_count']!=[3,5,6][k]:raise ValueError('FIT support unchanged')
    context,rows=c.context(own,guard);guard.take('context_builds')
    if context_saved!=dict(fold=k,locations=loc,**context):raise ValueError('cached FIT context identity')
    for arm in c.adapter.ARMS:
        values=c.features(rows,spatial,arm);labels=supervised['rows'];guard.take('training_target_rows',len(labels))
        model=c.learning.fit([r['values'] for r in values],labels,cfg,guard)
        predictions=c.prediction_rows(model,values,guard);policies=[]
        for gate in plan['gates']:
            added,trace=c.choose(own,model,predictions,cfg,gate);comparison=c.core.compare(own,added,ref);guard.take('FIT_policy_comparisons')
            chosen={r['parent_id'] for r in added};positive=[r for r in cached['rows'] if r['parent_id'] in chosen and r['U']>0]
            policies.append(dict(threshold=gate,source_keys=sorted(chosen),trace=trace,comparison=comparison,positive_GT=len({tuple(t) for r in positive for t in r['new_identities']})))
        model['threshold']=c.core.choose(policies)
        c.write(out/f'{arm}_FIT.json',dict(fold=k,arm=arm,support=support,model=model,predictions=predictions,policies=policies,cached_positive_GT=support['positive_GT_count'],labels_sha256=lock['source_files'][f'supervision_fold_{k}.json'],used_for_gate='own FIT only; no independent claim'))
        exported=dict(c.numeric_model(model),fold=k,arm=arm,held_locations=cfg['held_groups'][k],source_digest=lock['bundle_identity'])
        inference_payload(exported,k,arm,cfg['held_groups'][k],lock['bundle_identity']);c.write(out/f'{arm}_inference.json',exported)

def held(paths,lock,plan,cfg,run,out,guard,k):
    # This process has no file capability for ZIP, metadata, FIT policy or labels.
    bank=c.read(run/'bank/bank.json');spatial=c.read(run/'spatial/descriptors.json');scope=c.scoped_bank(bank,cfg['held_groups'][k]);context,rows=c.context(scope,guard);guard.take('context_builds')
    for arm in c.adapter.ARMS:
        model=c.read(run/f'fit_{k}/{arm}_inference.json');inference_payload(model,k,arm,cfg['held_groups'][k],lock['bundle_identity'])
        values=c.features(rows,spatial,arm);pred=c.prediction_rows(model,values,guard);added,trace=c.choose(scope,model,pred,cfg,model['threshold'])
        c.write(out/f'{arm}.json',dict(fold=k,arm=arm,held_locations=scope['locations'],threshold=model['threshold'],features_and_predictions=pred,rows=added,source_keys=[r['parent_id'] for r in added],trace=trace,context=context))
    b1=c.read(run/'bank/B1.json');model=b1['models'][k];inference_payload(model,k,'saved_E018_geometry',cfg['held_groups'][k],lock['bundle_identity'])
    class B1Guard:
        def take(self,name,n=1):guard.take('B1_replay_rows' if name=='prediction_rows' else name,n)
    pred=c.prediction_rows(model,rows,B1Guard(),geometry=True);added,trace=c.choose(scope,model,pred,cfg,model['threshold']);old=b1['folds'][k]
    if [r['parent_id'] for r in added]!=old['source_keys'] or added!=old['rows'] or len(pred)!=len(old['features_and_predictions']):raise ValueError('E018 saved policy reproduction')
    for now,before in zip(pred,old['features_and_predictions'],strict=True):
        if any(now[key]!=before[key] for key in ['index','parent_id','image_id','location','values']) or max(abs(x-y) for x,y in zip(now['roles']+[now['rank_score']],before['roles']+[before['rank_score']],strict=True))>1e-12:raise ValueError('E018 GT-free numeric prediction reproduction')
    c.write(out/'saved_E018_geometry.json',dict(fold=k,arm='saved_E018_geometry',rows=added,source_keys=old['source_keys'],saved_state_reproduced=True))

def utility_decision(comparisons):
    u={a:v['net_GT'] for a,v in comparisons['pooled9'].items()}
    D=u['aligned']-max(0,u['saved_E018_geometry'],u['half_shift'])
    protected=all(comparisons[s]['aligned']['lost_old']==0 for s in ['pooled9','pooled12'])
    return dict(D=D,U=u,protected=protected,scientific_verdict='supports' if protected and D>=1 else 'negative')


def evaluate(paths,lock,plan,cfg,run,out,guard):
    freeze=c.read(run/'prediction_freeze.json')
    for f,h in freeze['files'].items():c.checked(run/f,h)
    bank=c.read(run/'bank/bank.json');targets=inputs.targets(paths['metadata'],cfg['locations'],bank['image_locations'],guard)
    added={'E003':[]}
    for arm in ['saved_E018_geometry',*c.adapter.ARMS]:added[arm]=sorted([r for k in range(3) for r in c.read(run/f'held_{k}/{arm}.json')['rows']],key=lambda r:r['parent_id'])
    scopes={'pooled9':plan['primary_locations'],'pooled12':cfg['locations'],'qualification_reused':plan['qualification_reused'],**{f'held_{k}':g for k,g in enumerate(cfg['held_groups'])}}
    comparisons={};evaluations={}
    for name,loc in scopes.items():
        scoped=c.scoped_bank(bank,loc);scoped['targets']={im:targets[im] for im in scoped['image_locations']};ref=c.core.baseline(scoped);guard.take('evaluation_baselines')
        comparisons[name]={}
        for arm in plan['arms']:
            rows=[r for r in added[arm] if r['reid'] in loc];comparison=c.core.compare(scoped,rows,ref);guard.take('evaluation_comparisons');comparisons[name][arm]=comparison
        evaluations[name]=dict(locations=loc,images=len(scoped['image_locations']),original_digest=c.digest(scoped['originals']),baseline=ref[0])
    if comparisons['pooled12']['E003']['retained_old']!=684:raise ValueError('E003684 identity baseline')
    decision=utility_decision(comparisons)
    result=dict(protocol=plan['protocol'],**decision,comparisons=comparisons,scopes=evaluations,originals_unchanged=c.digest(bank['originals'])==lock['original_rows_digest'],scope='conditional selector OOF on consumed development sites; not fresh geography or full-pipeline OOF',E028_site24_negative_preserved=True)
    c.write(out/'result.json',result);c.write(out/'evaluation.json',dict(targets=targets,image_locations=bank['image_locations'],added=added,baseline_rows=bank['originals']))
