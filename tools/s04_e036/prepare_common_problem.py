#!/usr/bin/env python3
"""Bind an existing, audited mesh/precrack export. No network/solver calls."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def build(source):
    with np.load(source, allow_pickle=False) as z:
        xy=np.asarray(z['node_coords'],dtype='<f4')
        cells=np.asarray(z['connectivity'],dtype='<i8')
        mask=np.asarray(z['crack_mask'],dtype=bool)
        d0=np.asarray(z['FEM_initial_damage'])
    if xy.ndim!=2 or xy.shape[1]!=2 or cells.ndim!=2 or cells.shape[1] not in (3,4):
        raise ValueError('native ordered XY/connectivity required')
    if mask.shape!=(len(xy),) or not mask.any() or not np.all(d0[mask]==1):
        raise ValueError('invalid source precrack boundary')
    if not np.isfinite(xy).all() or not np.isfinite(d0).all() or d0.min()<0 or d0.max()>1:
        raise ValueError('invalid initial geometry/damage')
    if cells.min()<0 or cells.max()>=len(xy):raise ValueError('invalid connectivity')
    # Exactly the established canonical precrack, verified against source mask.
    expected=(xy[:,1]==0)&(xy[:,0]>=-.5)&(xy[:,0]<=0)
    if not np.array_equal(mask,expected):raise ValueError('precrack mask differs from canonical source geometry')
    return dict(schema='s04_e036_common_problem_v1',
        ordered_mesh_sha256_f32_i64=hashlib.sha256(xy.tobytes()+cells.tobytes()).hexdigest(),
        fixed_damage_nodes_zero_based=np.flatnonzero(mask).tolist(),fixed_damage_value=1.,
        tol_ir=.001,recovery_penalty_coefficient=13781.25,
        acceptance_config=dict(mode='nodal_box_kkt',joint_tol=4e-4,u_tol=1e-6,
            bounds_tol=1e-8,active_tol=1e-10,bc_tol=5e-8,history_atol=2e-6,history_rtol=2e-6),
        source=dict(path=str(source.resolve()),sha256=hashlib.sha256(source.read_bytes()).hexdigest()),
        notes='Material/BC/acceptance only; does not install an initial predecessor or authorize execution.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=build(a.source)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(a.output),fixed_nodes=len(result['fixed_damage_nodes_zero_based']),mesh=result['ordered_mesh_sha256_f32_i64'])))
if __name__=='__main__':main()
