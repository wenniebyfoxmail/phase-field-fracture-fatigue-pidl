"""Read-only native-Q4 input identity audit; never enters an optimizer."""
import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import torch


def mesh_signature(xy, conn):
    h = hashlib.sha256()
    for a in (xy, conn):
        a = np.ascontiguousarray(a)
        h.update(str(a.dtype).encode('ascii'))
        h.update(np.asarray(a.shape, dtype=np.int64).tobytes())
        h.update(a.tobytes())
    return h.hexdigest()


def audit(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    for asset in manifest['files']:
        p = root / asset['name']
        if p.stat().st_size != asset['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError('Input fingerprint mismatch: ' + asset['name'])
    checkpoint = torch.load(root / 'checkpoint_step_413.pt', map_location='cpu', weights_only=False)
    with h5py.File(root / 'cycle_0083_s004_normalized.mat') as f:
        g = f['cycle_state']
        xy = np.asarray(g['node_coords']).T.astype(np.float32)
        conn = (np.asarray(g['connectivity_q4']).T - 1).astype(np.int64)
        uv = np.asarray(g['u_node']).T
        d = np.asarray(g['d_node']).reshape(-1)
    if mesh_signature(xy, conn) != checkpoint['mesh_state_signature']:
        raise ValueError('FEM and production mesh identity differ')
    for key, expected in [('history_storage', 'q4_gp4'), ('damage_history_storage', 'previous_accepted_nodal'), ('history_driver_mode', 'current_active')]:
        if checkpoint[key] != expected:
            raise ValueError('Wrong state semantics: ' + key)
    n, e = len(xy), len(conn)
    if (n, e) != (86756, 86408):
        raise ValueError('Unexpected native mesh size')
    if tuple(checkpoint['hist_alpha'].shape) != (n,) or any(tuple(checkpoint[k].shape) != (e, 4) for k in ('hist_fat', 'psi_plus_prev')):
        raise ValueError('Wrong history shape')
    for a in (xy, uv, d, *(checkpoint[k].numpy() for k in ('hist_alpha', 'hist_fat', 'psi_plus_prev'))):
        if not np.isfinite(a).all():
            raise ValueError('Nonfinite input')
    bottom, top = xy[:, 1] == -.5, xy[:, 1] == .5
    return dict(mesh_identity='exact float32-coordinate/int64-connectivity hash match',
                mesh_signature=checkpoint['mesh_state_signature'], nodes=n, elements=e,
                bottom_uv_max=float(abs(uv[bottom]).max()), top_u_max=float(abs(uv[top, 0]).max()),
                top_v_min=float(uv[top, 1].min()), top_v_max=float(uv[top, 1].max()),
                fem_damage_min=float(d.min()), fem_damage_max=float(d.max()),
                accepted_damage_min=float(checkpoint['hist_alpha'].min()),
                accepted_damage_max=float(checkpoint['hist_alpha'].max()),
                state_transition=manifest['state_transition'], training=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('inputs', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = audit(a.inputs)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
