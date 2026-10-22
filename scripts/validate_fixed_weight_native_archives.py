"""Actual CPU Torch admission of two immutable native archives, streaming.

Writes receipts to stdout only. No FEM solve, training or archive mutation.
Success requires exhaustion of iter_trajectory, including c1s00 and all steps.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import re
import socket
import sys
import time

import h5py
import numpy as np
import torch

from audit_fixed_weight_fem_archive import LOCKS
from fixed_weight_contract import (Mesh, Material, StateKey, RecoveredInitialKey,
    TrajectoryRecord, SplitManifest, RECOVERED_INITIAL_SEMANTICS, iter_trajectory, _require)
from fixed_weight_native_adapter import PRODUCER, RULE, precision_bound_row, adapt_native
from s09_stage0a_capability import (S09_E008_CONTEXT, load_state_index,
    decode_native_static, _mat_numeric)
from s09_stage0a_packet import decode_payload, _reject_external_hdf5_storage


def emit(kind, **v):
    print(json.dumps({'kind':kind, **v}, allow_nan=False), flush=True)


def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def validate_sequence(rows, cycles):
    expected = [f'c{c:04d}_s{s:02d}' for c in range(1,cycles+1) for s in range(6)]
    _require([r['state_key'] for r in rows] == expected, 'incomplete native substep coverage')
    by_key = {r['state_key']:r for r in rows}
    for row in rows:
        c,s = int(row['cycle']),int(row['substep'])
        alias = s == 0 and c > 1
        source = f'c{c-1:04d}_s05' if alias else row['state_key']
        _require(row['source_state_key']==source and row['is_alias']==str(int(alias)), 'invalid native alias')
        _require(row['timing']==('pre_cycle_committed' if s==0 else 'post_history_commit'), 'wrong timing')
        _require(row['converged']=='1', 'unconverged native state')
        _require(float(row['nominal_load_factor']) == [0,.25,.5,.75,1,0][s], 'wrong nominal path')
        if alias:
            _require(all(row[k]==by_key[source][k] for k in
                ('payload_file','payload_sha256','imposed_displacement')), 'alias source mismatch')
    return [r for r in rows if r['is_alias']=='0']


def prepare(root):
    _require(root.name in LOCKS, 'archive outside exact admission scope')
    cycles, amplitude, run, index_hash, static_hash, config_hash = LOCKS[root.name]
    ctx = replace(S09_E008_CONTEXT, run_id=run, state_index_sha256=index_hash, static_sha256=static_hash)
    rows = load_state_index(root/'state_index.csv',ctx)
    physical = validate_sequence(rows,cycles)
    _require({p.name for p in (root/'states').iterdir() if p.is_file()} ==
             {Path(r['payload_file']).name for r in physical}, 'state file membership mismatch')
    members = 0
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8-sig').splitlines():
        match = re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?(.+)',line)
        _require(match is not None, 'invalid manifest')
        path = root/match[2].replace('\\','/')
        _require(path.resolve().is_relative_to(root.resolve()) and path.is_file(), 'manifest missing/escaping file')
        members += 1
    static, static_receipt = decode_native_static(root/'static'/ctx.static_filename,ctx)
    cfg_bytes = (root/'provenance/config_receipt.mat').read_bytes()
    _require(hashlib.sha256(cfg_bytes).hexdigest()==config_hash, 'config identity mismatch')
    static_bytes = (root/'static'/ctx.static_filename).read_bytes()
    _require(hashlib.sha256(static_bytes).hexdigest()==static_hash, 'static changed during read')
    with h5py.File(io.BytesIO(static_bytes),'r') as f, h5py.File(io.BytesIO(cfg_bytes),'r') as cf:
        _reject_external_hdf5_storage(cf)
        st,cfg = f['stage0b_static'],cf['config_receipt']
        values = [float(_mat_numeric(f,st['material_parameters'],k).item())
                  for k in ('E','ni','Gc','ell','alpha_T','p','res_stiff')]+[static['thickness']]
        _require(values==[1,.3,.01,.01,.5,2,0,1], 'material mismatch')
        mat = Material(*values)
        for k in ('u_max','R','alpha_T','res_stiff','n_step','effective_uy',
                  'nominal_load_factor','reset_fatigue_after_recovery'):
            _require(np.array_equal(_mat_numeric(f,st['case_config'],k),_mat_numeric(cf,cfg,k)), 'static/config mismatch '+k)
        _require(float(_mat_numeric(cf,cfg,'u_max').item())==amplitude, 'amplitude mismatch')
        _require(float(_mat_numeric(cf,cfg,'reset_fatigue_after_recovery').item())==1, 'recovery reset absent')
        schedule = _mat_numeric(cf,cfg,'effective_uy').reshape(-1)
        _require(np.array_equal(np.unique(_mat_numeric(f,st['mesh']['native_mesh'],'elem_material_id')),[1.]), 'material IDs mismatch')
        xy = static['xy']; bottom,top = xy[:,1]==xy[:,1].min(),xy[:,1]==xy[:,1].max()
        for k,wanted in (('fix_X',bottom|top),('fix_Y',bottom),('disp_Y',top)):
            ids = _mat_numeric(f,st['boundary_node_masks'],k).reshape(-1)-1
            _require(np.array_equal(np.sort(ids),np.flatnonzero(wanted)), 'boundary mask mismatch '+k)
    source = json.loads((root/'provenance/source_receipt.json').read_text())
    summary = json.loads((root/'run_summary.json').read_text())
    _require(source['source_commit']==PRODUCER and source['source_dirty'] is False, 'producer binding mismatch')
    _require(summary['sealed'] is True and summary['provenance']['run_id']==run and
             summary['unique_payload_count']==len(physical), 'archive summary mismatch')
    mesh_id = 'q4:'+static_receipt['node_coordinates_sha256']+':'+static_receipt['cells_0based_sha256']
    mesh = Mesh(torch.from_numpy(static['xy'].copy()),torch.from_numpy(static['conn'].copy()),mesh_id)
    record = TrajectoryRecord(run,root.name,PRODUCER,mesh_id,
        'train' if amplitude==.115 else 'validation',
        'validation-in-progress:fixed_weight_native_adapter_v1',
        semantics=RECOVERED_INITIAL_SEMANTICS, expected_state_count=cycles*5+1,
        material_values=tuple(values))
    emit('binding',archive=root.name,record=record.__dict__,index_sha256=index_hash,
         config_sha256=config_hash,static_sha256=static_hash,static_receipt=static_receipt,
         physical_states=len(physical),aliases=len(rows)-len(physical),manifest_members=members,
         schedule=schedule.tolist(),rule=RULE)
    return physical,static,schedule,mesh,mat,record


def run(root):
    start = time.monotonic()
    rows,static,schedule,mesh,mat,record = prepare(root)
    SplitManifest([record]).validate()
    counts={'states':0,'transitions':0,'repair_points':0,'csv_load_differences':0}
    def loader(_):
        previous_load = 0.
        previous_raw_q = previous_canonical_q = None
        for ordinal,row in enumerate(rows):
            _require(time.monotonic()-start<1200, '20 minute validation cap reached')
            bound = precision_bound_row(row,archive=root.name,schedule=schedule)
            decoded = decode_payload(root/row['payload_file'],bound,
                expected_nodes=len(mesh.xy),expected_elements=len(mesh.conn))
            before = [digest(a) for a in (decoded.u_node,decoded.d_node,decoded.history_gp)]
            load = decoded.imposed_displacement
            cls = RecoveredInitialKey if ordinal==0 else StateKey
            branch = 'initial' if ordinal==0 else 'load' if load>previous_load else 'unload' if load<previous_load else 'hold'
            key = cls(record.trajectory_id,record.condition_id,record.reference_id,record.mesh_id,
                      decoded.logical_cycle,decoded.logical_substep,ordinal,branch,load)
            state,receipt = adapt_native(decoded,key,mesh,mat,archive=root.name,source_commit=PRODUCER,
                source_timing=row['timing'],native_shape=static['shape'],native_derivative=static['reference_derivative'])
            _require(before==[digest(a) for a in (decoded.u_node,decoded.d_node,decoded.history_gp)], 'raw array changed')
            _require(np.array_equal(state.u.numpy(),decoded.u_node) and
                     np.array_equal(state.d.numpy(),decoded.d_node) and
                     np.array_equal(state.history[...,1].numpy(),decoded.history_gp[...,1]), 'u/d/alpha changed')
            if previous_raw_q is not None:
                raw_increment = np.maximum(decoded.history_gp[...,2]-previous_raw_q,0.)
                canonical_increment = np.maximum(state.history[...,2].numpy()-previous_canonical_q,0.)
                _require(np.array_equal(raw_increment,canonical_increment),
                         'canonicalization changes fatigue accumulation increment')
            receipt['alpha_increment_unchanged'] = ordinal > 0
            previous_raw_q = decoded.history_gp[...,2].copy()
            previous_canonical_q = state.history[...,2].numpy().copy()
            counts['repair_points'] += len(receipt['repairs'])
            counts['csv_load_differences'] += int(float(row['imposed_displacement'])!=load)
            emit('adapted',archive=root.name,key=row['state_key'],ordinal=ordinal,
                 raw_csv_load=row['imposed_displacement'],canonical_load=load,
                 raw_array_digests=before,initial=ordinal==0,**receipt)
            previous_load = load
            yield state
    for state in iter_trajectory(record,loader,mesh,mat):
        counts['states'] += 1
        counts['transitions'] += int(state.key.ordinal>0)
    _require(counts['states']==record.expected_state_count and counts['transitions']==len(rows)-1, 'incomplete stream')
    emit('admitted',archive=root.name,**counts,elapsed_seconds=time.monotonic()-start,
         qualification_scope='synthetic archive learning, development conditions only',
         training_started=False,solver_started=False,originals_modified=False)
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('roots',nargs=2,type=Path);a=p.parse_args()
    torch.set_num_threads(2);torch.set_num_interop_threads(2)
    emit('environment',torch=torch.__version__,numpy=np.__version__,h5py=h5py.__version__,
         python=sys.version,hostname=socket.gethostname(),pid=os.getpid(),threads=torch.get_num_threads())
    records=[run(root) for root in a.roots]
    SplitManifest(records).validate()
    emit('complete',archives=len(records),test_conditions=0,rule=RULE)
