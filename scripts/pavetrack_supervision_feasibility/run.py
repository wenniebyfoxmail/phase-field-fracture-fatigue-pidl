#!/usr/bin/env python3
"""Producer-only C1 supervision opportunity audit; zero learned fits/predictions."""
import time
BOOT_START=time.monotonic()
import copy,importlib.util,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('e017_private_e015',HERE.parent/'pavetrack_locality_selector/run.py');ancestor=importlib.util.module_from_spec(s);s.loader.exec_module(ancestor)
r=ancestor.r;c=ancestor.c;locality=ancestor.locality;inputs=r.inputs
audit=c.module('e017_supervision_audit',HERE/'audit.py')
c.PROTOCOL='S01-E017-v1';c.CONTRACT='docs/research/S01/S01-E017/';r.BOOT_START=BOOT_START;r.HERE=HERE
LegacyGuard=r.Guard
class Guard(LegacyGuard):
    def receipt(self):return dict(**super().receipt(),model_fits=0,learned_predictions=0,held_comparisons=0,full12_comparisons=0)
r.Guard=Guard
verify=r.verify


def execute(args,cfg,lock,guard,launch):
    c.require_producer(cfg)
    expected={'launch.json':copy.deepcopy(launch)}
    def emit(name,value):expected[name]=copy.deepcopy(value);c.write(args.run/name,value)
    data=inputs.load(args.source,args.run,cfg,lock,guard,c);records=inputs.metadata(args.metadata,cfg,lock,guard,c)
    if set(records)!=set(data['image_locations']) or any(records[im]['reid']!=loc for im,loc in data['image_locations'].items()):raise ValueError('metadata membership')
    targets={im:record['crack_boxes_xyxy'] for im,record in records.items()};original_digest=c.digest(data['originals'])
    if original_digest!=lock['original_rows_digest']:raise ValueError('original identity')
    gate=c.e12.PixelGate([]);sys.addaudithook(gate)
    emit('input_audit.json',dict(protocol=c.PROTOCOL,source_zip_sha256=lock['source_zip_sha256'],original_rows_digest=original_digest,originals=len(data['originals']),corrections=len(data['candidates']),eligible=sum(x['eligible'] for x in data['candidates']),scope='three separate own FIT scopes, no held/full12 comparison',fresh_access=False))
    emit('historical_comparison.json',c.read(c.ROOT/c.CONTRACT/'historical_failure_comparison.json'))
    reports=[];cases=[]
    for fold,payload in enumerate(data['labels']):
        report,supervision,features,selected=audit.process_scope(data,targets,payload,fold,cfg,guard,c,locality)
        emit(f'supervision_fold_{fold}.json',supervision);emit(f'context_fold_{fold}.json',features);emit(f'FIT_audit_fold_{fold}.json',report);reports.append(report);cases.extend(selected)
    count=sum(any(o['name']=='decomposed_novel_budget' and o['protected_increment'] for o in f['oracles']) for f in reports)
    primary=count>=cfg['criterion']['required_passing_FITs']
    result=dict(protocol=c.PROTOCOL,run_id=args.run.name,status='supervision_oracle_opportunity' if primary else 'no_protected_decomposed_oracle_opportunity',primary_pass=primary,passing_FITs=count,criterion=cfg['criterion'],GT_informed=True,learned_result=False,models_fitted=0,learned_predictions=0,full12_comparisons=0,held_comparisons=0,primary_is_feasibility_only=True,original_rows_digest=original_digest,originals_unchanged=c.digest(data['originals'])==original_digest,folds=reports,fresh_access=False,scope='consumed/reused upstream, own FIT diagnostic only; not learned gain, predictivity, training sufficiency or fresh generalisation')
    if not result['originals_unchanged']:raise ValueError('original mutation')
    emit('result.json',result)
    cases=sorted(cases,key=lambda x:(-x['original_score'],x['fold'],x['image_id'],tuple(x['corrected_box']),x['parent_id']))[:6]
    emit('cases.json',dict(rule='at most six B-appended examples; original score descending then fold/image/box/key; repeated sources across FIT are correlated',cases=cases,source_pixels=False))
    analysis=c.module('e017_saved_analysis',HERE/'analyze.py');analysis.render(args.run,result,expected['cases.json'],guard)
    gate.output.update(os.path.normcase(os.path.abspath(p)) for p in (args.run/'analysis').glob('*.png'))
    for key in ['fit_baseline_metrics','context_feature_builds','supervision_rows','oracle_comparisons']:
        if guard.counts[key]!=cfg['budget'][key]:raise ValueError('incomplete phase count:'+key)
    if c.digest(data['originals'])!=original_digest:raise ValueError('original mutation')
    emit('resource.json',guard.receipt());receipt=dict(protocol=c.PROTOCOL,files={p.relative_to(args.run).as_posix():c.sha(p,guard.check) for p in sorted(args.run.rglob('*')) if p.is_file()},fresh_access=False);c.write(args.run/'output_receipt.json',receipt);verify(args.run,expected,receipt,lock['source_files']);guard.check();return result
r.execute=execute
if __name__=='__main__':r.main()
