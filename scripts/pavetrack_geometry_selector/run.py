#!/usr/bin/env python3
"""Private E013 runner instance: change only geometry ordering, add FIT audit."""
import time
BOOT_START=time.monotonic()
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('e014_private_e013_runner',HERE.parent/'pavetrack_protected_selector/run.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
c=r.c;geometry=c.module('e014_geometry_policy',HERE/'policy.py')
# These modules are private instances; no frozen source file or sibling changes.
c.PROTOCOL='S01-E014-v1';c.CONTRACT='docs/research/S01/S01-E014/';r.BOOT_START=BOOT_START;r.HERE=HERE
inherited_features=c.features

def features(originals,manifest,probabilities,cfg):
    candidates=inherited_features(originals,manifest,probabilities,cfg)
    for row in candidates:row['geometry_change']=geometry.geometry_change(row['row'],c)
    return candidates

def policy(candidates,threshold,locations,cfg):return geometry.select(candidates,threshold,locations,cfg,c)
c.features=features;c.policy=policy
inherited_fit_and_freeze=r.fit_and_freeze

def fit_and_freeze(data,targets,run,cfg,guard,emit,calibrator=c.calibrate):
    models,support,added=inherited_fit_and_freeze(data,targets,run,cfg,guard,emit,calibrator)
    # All main predictions are already frozen and all diagnostics completed.
    before=c.digest([models,added]);audit=geometry.capacity_audit(data,models,cfg)
    if c.digest([models,added])!=before:raise ValueError('capacity audit mutated main state')
    emit('capacity_audit.json',audit);guard.check()
    return models,support,added
r.fit_and_freeze=fit_and_freeze
if __name__=='__main__':r.main()
