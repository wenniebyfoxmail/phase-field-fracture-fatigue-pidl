"""Descriptive target/history overlap audit. No optimizer and no pass threshold."""
import argparse
import json
from pathlib import Path
import sys
import h5py
import numpy as np
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'source'))
from q4_quadrature import q4_shape_data, q4_interpolate
from audit_inputs import audit


def measure(root):
    audit(root)
    torch.set_num_threads(1)
    checkpoint = torch.load(root/'checkpoint_step_413.pt', map_location='cpu', weights_only=False)
    with h5py.File(root/'cycle_0083_s004_normalized.mat') as f:
        g = f['cycle_state']
        xy = torch.tensor(np.asarray(g['node_coords']).T)
        conn = torch.tensor(np.asarray(g['connectivity_q4']).T.astype(np.int64)-1)
        target = torch.tensor(np.asarray(g['d_node']).reshape(-1))
    shape, _, det = q4_shape_data(xy, conn)
    accepted = checkpoint['hist_alpha'].double().clamp(0, 1)
    gap = (q4_interpolate(accepted, conn, shape)-q4_interpolate(target, conn, shape)).clamp_min(0)
    return dict(kind='descriptive pre-optimization state compatibility; no new pass threshold',
                target='FEM c83 s004 peak', accepted='PIDL step413 damage projected once to [0,1]',
                gp_healing_max=float(gap.max()),
                gp_healing_area_mean=float((gap*det).sum()/det.sum()),
                gp_healing_area_rms=float(((gap.square()*det).sum()/det.sum()).sqrt()),
                gp_positive_healing_area_fraction=float(((gap>0)*det).sum()/det.sum()),
                node_healing_max=float((accepted-target).clamp_min(0).max()),
                interpretation='Nonzero values describe target conflict with projected PIDL history; penalty magnitude and cross residual still require the frozen objective audit. Positive fraction has no noise tolerance and is descriptive only.')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('inputs', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = measure(a.inputs)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
