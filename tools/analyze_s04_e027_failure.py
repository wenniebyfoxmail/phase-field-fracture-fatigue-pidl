"""Saved-field algebra only. No model inference, PT reads, optimizer or FEM solve."""
import argparse
import csv
import json
import sys
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
import s04_e027 as m
from q4_quadrature import q4_interpolate, q4_gradient


def analyze(case, dest):
    dest.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT / 'docs/research/S04/S04-E027/data_lock.json').read_text())
    a = m.load_reference(Path(lock['root']), lock)
    p = m.Problem(a)
    z = np.load(case / 'retrieved/output/predictions.npz')
    assert np.array_equal(z['reference'], a['ref'])
    ref = p.parts(*p.ref.unbind(1))
    mask, w = p.gp_zone, p.w[p.gp_zone]
    rms = lambda x: float(torch.sqrt((w*x[mask].square()).sum()/w.sum()))
    norm = rms(ref[4])
    gref = (1-q4_interpolate(p.ref[:, 2], p.conn, p.N)).square()
    milestones = json.loads((case / 'retrieved/output/milestones.json').read_text())
    rows = []
    for v in milestones:
        if v.get('reused_from'): continue
        d, s = v['diagnostics'], v['scores']
        rows.append(dict(arm=v['arm'], step=v['step'], active=s['active_error'], uv_Z=s['zone_uv_RMS_Us'], d_Z=s['zone_d_RMS'], raw_Z=s['zone_raw_RMSE'],
            L_U=d['losses']['L_U'], L_D=d['losses']['L_D'], L_mech=d['losses']['L_mech'],
            grad_sup=d['parameter_gradient_l2']['L_sup'], weighted_mech_over_sup=d['parameter_gradient_l2']['C_mech_weighted']/d['parameter_gradient_l2']['L_sup']))
    breakdown = {}
    for arm in ['P', 'S', 'C']:
        q = torch.as_tensor(z[arm], dtype=torch.float64)
        raw = p.parts(*q.unbind(1))[3]
        g = (1-q4_interpolate(q[:, 2], p.conn, p.N)).square()
        # Exact decomposition of product difference, not retrained counterfactuals.
        terms = [(raw-ref[3])*gref, ref[3]*(g-gref), (raw-ref[3])*(g-gref)]
        total = raw*g-ref[4]
        algebra_gap = float((sum(terms)-total).abs().max())
        scale = max(1., *(float(t.abs().max()) for t in terms), float(total.abs().max()))
        assert algebra_gap <= 32*torch.finfo(torch.float64).eps*scale
        uv = torch.stack([q4_gradient(q[:, j]-p.ref[:, j], p.conn, p.B) for j in [0, 1]])
        dot = lambda x, y: float((w*x[mask]*y[mask]).sum()/w.sum())
        hybrid_forces = {}
        for label, uvsrc, dsrc in [('own', q, q), ('own_uv_FEM_d', q, p.ref), ('FEM_uv_own_d', p.ref, q)]:
            hybrid = torch.cat((uvsrc[:, :2], dsrc[:, 2:3]), 1).detach().requires_grad_(True)
            hybrid_forces[label] = float(torch.linalg.vector_norm(p.force(hybrid)[p.free]).detach())
        breakdown[arm] = dict(active_error=rms(total)/norm, algebra_identity_max_gap=algebra_gap, hybrid_free_force=hybrid_forces,
            raw_only_with_FEM_damage=rms(terms[0])/norm,
            damage_only_with_FEM_uv=rms(terms[1])/norm,
            product_cross=rms(terms[2])/norm,
            pair_inner_products_normalized=[[dot(x,y)/norm**2 for y in terms] for x in terms],
            full_uv_gradient_error_RMS=float(torch.sqrt((p.w*uv.square().sum((0,3))).sum()/p.w.sum())),
            zone_uv_gradient_error_RMS=float(torch.sqrt((w*uv.square().sum((0,3))[mask]).sum()/w.sum())),
            damage_projection_max=float((torch.clamp(q[:, 2], min=p.previous, max=torch.ones_like(p.previous))-q[:, 2]).abs().max()))
    fixed = p.fixed_d
    geom = (p.xy[:,0] <= 1e-12) & (p.xy[:,0]>=-.5-1e-12) & (p.xy[:,1].abs()<=1e-12)
    assert torch.equal(fixed, geom)
    assert (p.previous[fixed] == 1).all() and (p.ref[fixed,2] == 1).all()
    assert ((p.previous >= 0) & (p.previous <= 1)).all()
    # Reject substituting U0 or the target as the current predecessor lower.
    bound = dict(state='c20s4 pre-solve lower equals committed c20s3', fixed_nodes=int(fixed.sum()),
        fixed_mask_equal_SENT_geometric_line=True, previous_min=float(p.previous.min()), previous_max=float(p.previous.max()),
        current_target_increment_max=float((p.ref[:,2]-p.previous).max()),
        target_differs_from_lower_nodes=int((p.ref[:,2]!=p.previous).sum()),
        strict_lower_gp_gap=float(torch.relu(p.old_gp-q4_interpolate(p.ref[:,2],p.conn,p.N)).max()),
        forbidden_lower='U0 initial or current target; use only locked c20s3 lower', history_commit=0)
    result = dict(scope='post-hoc endpoint algebra on already exposed scored outputs; not causal optimizer experiment',
        source_case=str(case), milestones=rows, endpoint_breakdown=breakdown, current_state_bound=bound,
        missing=['Initial and 1000-step nodal fields are not stored in predictions.npz; no PT inference reconstructed',
                 'Stored parameter gradients are norms only; angles, parameter-block directions, Adam-preconditioned updates and intermediate damage fields unavailable'],
        training=False, pt_read=False, new_data=False)
    (dest/'diagnosis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with (dest/'milestones.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--case',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();torch.set_num_threads(1);analyze(args.case,args.out)
