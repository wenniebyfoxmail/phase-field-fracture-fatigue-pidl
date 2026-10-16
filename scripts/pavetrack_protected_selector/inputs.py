"""Pinned ZIP input; oracle tail/fields skipped by scoped byte-window reader."""
import json,zipfile,hashlib
from pathlib import Path

def originals_from_file(path,count,parser):
    c=parser(path)
    try:
        top=dict(c.fields());joint=dict(c.fields(top['joint'][0]));rows=[]
        for span in c.items(joint['rows'][0]):
            if len(rows)==count:break
            row=c.decode(span)
            if row['kind']!='original':raise ValueError('immutable prefix')
            rows.append(row)
        if len(rows)!=count:raise ValueError('original count')
        return rows
    finally:c.close()

def load(zip_path,run,cfg,lock,guard,core):
    core.e12.checked(zip_path,lock['source_zip_sha256'],guard.check)
    staging=run/'input_snapshot';staging.mkdir(exist_ok=False)
    with zipfile.ZipFile(zip_path) as src:
        for name,h in lock['source_files'].items():
            if src.getinfo(name).file_size>128*1024*1024:raise ValueError('member size cap')
            raw=src.read(name)
            if hashlib.sha256(raw).hexdigest()!=h:raise ValueError('source member:'+name)
            (staging/name).write_bytes(raw);guard.check()
    source=core.read(staging/'source_receipt.json');score_receipt=core.read(staging/'scoring_receipt.json');launch=core.read(staging/'launch.json')
    if source['original_rows_digest']!=lock['original_rows_digest'] or score_receipt['rows']!=lock['source_correction_count'] or score_receipt['CPU_head_passes']!=2 or launch['reviewed_commit']!=lock['source_commit']:raise ValueError('R004 source lineage')
    parser=lambda path:core.e12.a.scoped.Cursor(path,guard.check)
    original=originals_from_file(staging/'qualification.json',lock['source_original_count'],parser)
    if core.digest(original)!=lock['original_rows_digest']:raise ValueError('original digest')
    identity=core.read(staging/'candidate_identity.json');manifest=identity['rows'];scores=core.read(staging/'scores.json')
    if len(manifest)!=lock['source_correction_count'] or scores['source_keys']!=[r['source_parent_key'] for r in manifest]:raise ValueError('correction score alignment')
    candidates=core.features(original,manifest,scores['probabilities'],cfg)
    if sum(c['eligible'] for c in candidates)!=lock['source_eligible_count']:raise ValueError('eligibility lineage')
    image_locations={r['image_id']:r['reid'] for r in original}
    if len(image_locations)!=cfg['input_counts']['images'] or set(image_locations.values())!=set(cfg['locations']):raise ValueError('image/location lineage')
    labels=[core.read(staging/f'fit8_fold_{i}.json') for i in range(3)]
    return dict(originals=original,candidates=candidates,image_locations=image_locations,labels=labels,snapshot=staging)

def metadata(path,cfg,lock,guard,core):
    # Reuse the scoped metadata contract; existing twelve train sites only.
    local=core.read(core.ROOT/core.e12.a.CONTRACT/'run_config.json');data_lock=core.read(core.ROOT/core.e12.a.CONTRACT/'data_lock.json')
    if data_lock['metadata_sha256']!=lock['metadata_sha256'] or local['locations']!=cfg['locations']:raise ValueError('metadata contract')
    return core.e12.a.metadata(path,local,data_lock,guard)
