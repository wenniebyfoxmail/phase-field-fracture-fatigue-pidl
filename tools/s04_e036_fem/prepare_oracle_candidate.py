#!/usr/bin/env python3
"""Prepare the predeclared complete D4 L+ endpoint as a node-solver guess.

No projection, solve or history transfer occurs here. Native MATLAB explicitly
projects only u/d and records the change against the independent F1 predecessor.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from scipy.io import savemat

sys.path.insert(0,str(Path(__file__).resolve().parent))
from export_window import require, sha256, state_key
from prepare_stage_b_config import win


def read_endpoint(fields,completion,cycle,substep,predecessor_sha256):
    require(cycle in (1,83) and substep in (2,4),'oracle state was not prospectively declared')
    done=json.loads(completion.read_text());field_sha=sha256(fields);completion_sha=sha256(completion)
    require(done.get('fields_sha256')==field_sha and done.get('readback_verified') is True
            and done.get('endpoint_complete') is True,'complete read-back endpoint receipt required')
    require(isinstance(done.get('bundle_sha256'),str) and len(done['bundle_sha256'])==64,'source network bundle identity required')
    with np.load(fields,allow_pickle=False) as z:
        m=json.loads(str(z['metadata_json'].item()))
        require(m.get('schema')=='s04_e036_mechanism_fields_v1' and m.get('arm')=='Lplus' and
                m.get('mapping')=='legacy' and m.get('weight_l2')==1e-5 and m.get('stage')=='first_2000' and
                m.get('rprop_updates')==2000 and m.get('history_commit_count')==0 and
                m.get('complete_endpoint') is True,'only the declared L+ complete first-2000 endpoint is eligible')
        key=state_key(m['state_key']['trajectory'],cycle,substep)
        require(m['state_key']==key and m['predecessor_checkpoint_sha256']==predecessor_sha256,
                'endpoint state/F1 predecessor differs; no substitute guess')
        arrays={name:np.asarray(z[name]).copy() for name in ('u','v','d')}
    for name,a in arrays.items():
        require(a.shape==(86756,) and a.dtype.kind=='f' and a.dtype.itemsize in (4,8) and np.isfinite(a).all(),
                'missing/nonfinite complete native nodal fields: '+name)
    initial=dict(u=np.r_[arrays['u'],arrays['v']].astype(np.float64)[:,None],
        d=arrays['d'].astype(np.float64)[:,None],state_key=key,source_snapshot_sha256=field_sha,
        source_completion_sha256=completion_sha,predecessor_checkpoint_sha256=predecessor_sha256,
        arm='L+',mapping_mode='legacy',complete_endpoint=True)
    require(sha256(fields)==field_sha and sha256(completion)==completion_sha,'endpoint changed while reading')
    return initial,dict(source_dtypes={k:str(v.dtype) for k,v in arrays.items()},
        conversion='exact float32-to-float64 embedding or unchanged float64; no clipping/projection',
        network_state_sha256=m['network_state_sha256'],bundle_sha256=done['bundle_sha256'],
        physical_accepted=done.get('physical_accepted'),history_fields_consumed=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fields',required=True,type=Path);p.add_argument('--completion',required=True,type=Path)
    p.add_argument('--cycle',required=True,type=int);p.add_argument('--substep',required=True,type=int)
    p.add_argument('--predecessor-sha256',required=True);p.add_argument('--producer-directory',required=True)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    initial,conversion=read_endpoint(a.fields,a.completion,a.cycle,a.substep,a.predecessor_sha256)
    a.output.mkdir(parents=True,exist_ok=False)
    for name,source in [('fields.npz',a.fields),('completion.json',a.completion)]:
        with (a.output/name).open('xb') as f:f.write(source.read_bytes())
    mat=a.output/'initial_fields.mat';savemat(mat,dict(initial_fields=initial),do_compression=True,long_field_names=True)
    base=win(a.producer_directory)
    spec=dict(path=base+'/initial_fields.mat',sha256=sha256(mat),
        source_snapshot_path=base+'/fields.npz',source_snapshot_sha256=initial['source_snapshot_sha256'],
        source_completion_path=base+'/completion.json',source_completion_sha256=initial['source_completion_sha256'])
    (a.output/'initial_fields_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    (a.output/'preparation.json').write_text(json.dumps(dict(schema='s04_e036_oracle_preparation_v1',
        status='prepared_not_projected_or_solved',source_fields=str(a.fields),source_completion=str(a.completion),
        state_key=initial['state_key'],predecessor_checkpoint_sha256=a.predecessor_sha256,initial_fields=spec,
        native_solves=0,history_commits=0,**conversion),indent=2)+'\n')


if __name__=='__main__':main()
