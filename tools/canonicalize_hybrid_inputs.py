"""Rebind ONLY derived geometry identity using strict portable Q4 arithmetic.

All scientific field values are copied unchanged. Preserve original manifest
and asset identities; no solve, projection, label promotion or tolerance edit.
"""
import argparse
from dataclasses import replace,fields
import os
from pathlib import Path
import numpy as np
from hybrid_inputs import read_manifest,sha256
from hybrid_kinematics import build_portable_native_q4_kinematics
from hybrid_incremental import NativeQ4Backend
from hybrid_transaction import StateStore
from hybrid_producer_common import write_json


def canonicalize(source,out):
    source=Path(source);out=Path(out)
    m=read_manifest(source/'inputs.json')
    for name,h in m['assets'].items():
        if sha256(source/name)!=h:raise RuntimeError('original input bytes differ')
    with np.load(source/'mesh.npz',allow_pickle=False) as z:
        b=NativeQ4Backend(build_portable_native_q4_kinematics(z['points'],z['cells']),z['crack'],**m['material'])
    old,_=StateStore(source/'state0.npz').load()
    if old.fingerprint()!=m['state0_id'] or old.physics_id!=b.physics_id:raise RuntimeError('original state/physics differs')
    new=replace(old,mesh_id=b.mesh_id)
    for f in fields(old):
        a=getattr(old,f.name)
        if isinstance(a,np.ndarray) and a.tobytes()!=getattr(new,f.name).tobytes():raise RuntimeError('field mutation')
    out.mkdir()
    for name in m['assets']:
        if name!='state0.npz':os.link(source/name,out/name)
    StateStore(out/'state0.npz').initialize(new)
    m.update(mesh_id=b.mesh_id,state0_id=new.fingerprint(),kinematics='hybrid-portable-Q4-float64-fixed-order-v1',
             identity_derivation=dict(original_inputs_sha256=sha256(source/'inputs.json'),original_state0_id=old.fingerprint(),
                                      original_mesh_id=old.mesh_id,scientific_state_arrays_bitwise_unchanged=True,
                                      reason='replace platform-dependent LAPACK-derived B/det with fixed-order explicit2x2 arithmetic; full byte hash remains strict'))
    m['assets']['state0.npz']=sha256(out/'state0.npz');write_json(out/'inputs.json',m)
    return m


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(canonicalize(a.source,a.out)['state0_id'])
