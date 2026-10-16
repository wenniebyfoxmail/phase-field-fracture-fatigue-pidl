#!/usr/bin/env python3
"""Private E014 adapter: add only positive-coordinate intersection eligibility."""
import time
BOOT_START=time.monotonic()
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('e015_private_e014',HERE.parent/'pavetrack_geometry_selector/run.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
r=a.r;c=a.c;locality=c.module('e015_locality',HERE/'locality.py')
c.PROTOCOL='S01-E015-v1';c.CONTRACT='docs/research/S01/S01-E015/';r.BOOT_START=BOOT_START;r.HERE=HERE
inherited_features=c.features;inherited_policy=c.policy

def features(originals,manifest,probabilities,cfg):
    candidates=inherited_features(originals,manifest,probabilities,cfg)
    for row in candidates:row['positive_intersection']=locality.positive_intersection(row['row'])
    return candidates

def policy(candidates,threshold,locations,cfg):
    if threshold not in cfg['feature']['thresholds']:raise ValueError('unfrozen threshold')
    if threshold=='abstain':return []
    retained=[]
    for row in candidates:
        if row['eligible'] and row['location'] in locations:
            value=row['positive_intersection']
            if type(value) is not bool or value!=locality.positive_intersection(row['row']):raise ValueError('locality representation mismatch')
            if value:retained.append(row)
    return inherited_policy(retained,threshold,locations,cfg)
c.features=features;c.policy=policy
inherited_fit_and_freeze=r.fit_and_freeze

def fit_and_freeze(data,targets,run,cfg,guard,emit,calibrator=c.calibrate):
    models,support,added=inherited_fit_and_freeze(data,targets,run,cfg,guard,emit,calibrator)
    before=c.digest([models,added]);audit=locality.retention_audit(data,cfg)
    if c.digest([models,added])!=before:raise ValueError('locality audit mutated main state')
    emit('locality_audit.json',audit);guard.check();return models,support,added
r.fit_and_freeze=fit_and_freeze
if __name__=='__main__':r.main()
