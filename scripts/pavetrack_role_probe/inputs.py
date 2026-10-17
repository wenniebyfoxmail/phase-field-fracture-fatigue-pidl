"""Allowlisted E017 snapshot consumer; no oracle-result or GT-tail decoding."""
import hashlib,zipfile,math

def load(path,run,cfg,lock,guard,core,legacy):
    core.e12.checked(path,lock['source_zip_sha256'],guard.check)
    if path.stat().st_size!=lock['source_zip_bytes']:raise ValueError('source ZIP bytes')
    stage=run/'input_snapshot';stage.mkdir(exist_ok=False)
    with zipfile.ZipFile(path) as src:
        if len(src.namelist())!=len(set(src.namelist())):raise ValueError('duplicate ZIP names')
        for name,h in lock['source_files'].items():
            if name.startswith('/') or '\\' in name or '..' in name.split('/'):raise ValueError('source member path')
            if src.getinfo(name).file_size>128*1024*1024:raise ValueError('member size cap')
            raw=src.read(name)
            if hashlib.sha256(raw).hexdigest()!=h:raise ValueError('source member:'+name)
            dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);guard.check()
    if core.read(stage/'launch.json')['reviewed_commit']!=lock['source_commit']:raise ValueError('E017 commit identity')
    audit=core.read(stage/'input_audit.json')
    if audit['source_zip_sha256']!=lock['ancestor_R004_zip_sha256'] or audit['original_rows_digest']!=lock['original_rows_digest']:raise ValueError('E017 lineage')
    receipt=core.read(stage/'output_receipt.json')
    for name,h in lock['source_files'].items():
        if name!='output_receipt.json' and receipt['files'].get(name)!=h:raise ValueError('E017 source inventory')
    nested=stage/'input_snapshot';source=core.read(nested/'source_receipt.json');score=core.read(nested/'scoring_receipt.json')
    if source['original_rows_digest']!=lock['original_rows_digest'] or score['rows']!=lock['source_correction_count'] or score['CPU_head_passes']!=2 or core.read(nested/'launch.json')['reviewed_commit']!=lock['ancestor_R004_commit']:raise ValueError('R004 lineage')
    originals=legacy.originals_from_file(nested/'qualification.json',lock['source_original_count'],lambda p:core.e12.a.scoped.Cursor(p,guard.check))
    if core.digest(originals)!=lock['original_rows_digest']:raise ValueError('original digest')
    manifest=core.read(nested/'candidate_identity.json')['rows'];scores=core.read(nested/'scores.json')
    if len(manifest)!=lock['source_correction_count'] or scores['source_keys']!=[r['source_parent_key'] for r in manifest]:raise ValueError('correction alignment')
    candidates=core.features(originals,manifest,scores['probabilities'],cfg);locations={r['image_id']:r['reid'] for r in originals}
    if sum(r['eligible'] for r in candidates)!=lock['source_eligible_count'] or len(locations)!=cfg['input_counts']['images'] or set(locations.values())!=set(cfg['locations']):raise ValueError('input counts/scope')
    return dict(originals=originals,candidates=candidates,image_locations=locations,labels=[core.read(nested/f'fit8_fold_{i}.json') for i in range(3)],supervision=[core.read(stage/f'supervision_fold_{i}.json') for i in range(3)],context=[core.read(stage/f'context_fold_{i}.json') for i in range(3)],snapshot=stage)


def validate_supervision(saved,payload,own,ref,fold,core,locality,audit):
    support=audit.validate_cached(payload,own,ref,core)
    if saved['fold']!=fold or saved['locations']!=own['locations'] or saved['GT_informed'] is not True or saved['new_singleton_U']!=0:raise ValueError('supervision scope')
    labels=saved['rows'];candidates=[r for r in own['candidates'] if r['eligible']]
    if len(labels)!=len(candidates):raise ValueError('supervision completeness')
    for y,c,b in zip(labels,candidates,payload['rows'],strict=True):
        if any(y[k]!=c[k] for k in ['index','parent_id','image_id','location']) or y['cached_singleton']!=b:raise ValueError('supervision identity/cached roles')
        q=y['corrected_max_IoU'];p=y['parent_max_IoU'];reference=y['corrected_reference'];parent=y['parent_reference']
        if not all(type(v) in (float,int) and math.isfinite(v) and 0<=v<=1 for v in [q,p]):raise ValueError('quality range')
        for value,quality in [(reference,q),(parent,p)]:
            if value is None:
                if quality!=0:raise ValueError('null reference')
            elif len(value)!=2 or value[0]!=c['image_id'] or type(value[1]) is not int or not 0<=value[1]<len(own['targets'][value[0]]) or quality<=0:raise ValueError('reference scope')
        if reference is None:
            if y['parent_IoU_on_corrected_reference'] is not None or y['gain_same_reference'] is not None:raise ValueError('null reference gain')
        else:
            same=y['parent_IoU_on_corrected_reference'];gain=y['gain_same_reference']
            if type(same) not in (float,int) or not math.isfinite(same) or not 0<=same<=p or type(gain) not in (float,int) or not math.isfinite(gain) or abs(gain-(q-same))>1e-12:raise ValueError('same-reference gain')
        state='no_corrected_reference' if reference is None else ('no_parent_reference' if parent is None else ('same' if parent==reference else 'switched'))
        expected=dict(valid_localisation=q>=.5,novel_reference=reference is not None and tuple(reference) not in ref[1],positive_intersection=locality.positive_intersection(c['row']),fixed_admission=locality.positive_intersection(c['row']) and c['x']>=0)
        if state!=y['reference_state'] or any(type(y[k]) is not bool or y[k]!=v for k,v in expected.items()):raise ValueError('supervision role algebra')
    return support
