"""Read-only FEM target / frozen PIDL413 history audit; no network or optimizer."""
import argparse
import csv
import json
import os
from pathlib import Path
import sys
import time
from windows_runtime import configure
configure()
import h5py
import numpy as np
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'source'))
from compute_energy import compute_energy_per_elem
from fatigue_history import compute_fatigue_degrad
from material_properties import MaterialProperties
from pff_model import PFFModel
from q4_quadrature import q4_shape_data, q4_interpolate
from audit_inputs import audit

NAMES = ('elastic', 'fracture', 'irreversibility')
MAT = MaterialProperties(1., .3, 1., .01)
MODEL = PFFModel('AT1', 'volumetric', 5e-3, residual_stiffness=0.)
CFG = dict(fatigue_on=True, loading_type='cyclic', accum_type='carrara', degrad_type='asymptotic', alpha_T=.5, spatial_alpha_T={'enable': False})


def mass_data(xy, conn):
    shape, _, det = q4_shape_data(xy, conn)
    mass = torch.zeros(len(xy), dtype=xy.dtype, device=xy.device)
    local = torch.einsum('eg,gn->en', det, shape)
    mass.scatter_add_(0, conn.reshape(-1), local.reshape(-1))
    if not torch.all(mass > 0):
        raise ValueError('Nonpositive nodal lumped mass')
    return shape, det, mass/det.sum()


def energy_parts(xy, conn, uv, damage, accepted, fatigue):
    return tuple(x.sum() for x in compute_energy_per_elem(
        xy, uv[:, 0], uv[:, 1], damage, accepted, MAT, MODEL, None, conn,
        f_fatigue=fatigue, irreversibility_penalty_cfg={'enable':True, 'mode':'fem_gp_q4'}))


def residuals(gu, gd, d, mass, free, us, es):
    # Derivatives with respect to normalized physical nodal variables.
    g_u, g_d = gu*us/es, gd/es
    rho_u = (g_u[free].square()/mass[free, None]).sum().sqrt()
    projected = d - (d - g_d/mass).clamp(0, 1)
    rho_d = (mass*projected.square()).sum().sqrt()
    dual_d = (g_d.square()/mass).sum().sqrt()
    return float(rho_u), float(rho_d), float(dual_d), projected


def evaluate(xy, conn, uv, d, accepted, fatigue, us):
    # All target nodal DOFs are independent leaves, without network/clamp chain.
    uv = uv.detach().clone().requires_grad_(True)
    d = d.detach().clone().requires_grad_(True)
    accepted, fatigue = accepted.detach().clone(), fatigue.detach().clone()
    unchanged = (accepted.clone(), fatigue.clone())
    shape, det, mass = mass_data(xy, conn)
    height = float(xy[:,1].max()-xy[:,1].min())
    es = float(det.sum()) * MAT.mat_E * (us/height)**2  # unit thickness
    free = (xy[:,1] != xy[:,1].min()) & (xy[:,1] != xy[:,1].max())
    parts = energy_parts(xy, conn, uv, d, accepted, fatigue)
    gradients = []
    for part in parts:
        gu, gd = torch.autograd.grad(part, (uv,d), retain_graph=True, allow_unused=True)
        gradients.append((torch.zeros_like(uv) if gu is None else gu,
                          torch.zeros_like(d) if gd is None else gd))
    total_grad = torch.autograd.grad(sum(parts), (uv,d))
    if not all(torch.allclose(sum(g[j] for g in gradients), total_grad[j], rtol=1e-10, atol=1e-12) for j in (0,1)):
        raise RuntimeError('Component gradients do not sum to total')
    rows=[]; arrays={}
    for name, value, (gu,gd) in zip((*NAMES,'total'), (*parts,sum(parts)), (*gradients,total_grad)):
        ru,rd,dual,pd=residuals(gu,gd,d,mass,free,us,es)
        row=dict(component=name, energy=float(value.detach()), rho_u=ru,
                 box_projected_damage_residual=rd, unprojected_damage_dual_norm=dual)
        rows.append(row)
        arrays[name+'_grad_uv']=gu.detach().numpy();arrays[name+'_grad_damage']=gd.detach().numpy()
        if name=='total': arrays['projected_damage_residual']=pd.detach().numpy()
    gap=(q4_interpolate(accepted,conn,shape)-q4_interpolate(d,conn,shape)).clamp_min(0).detach()
    for a,b in zip(unchanged,(accepted,fatigue)):
        if not torch.equal(a,b): raise RuntimeError('Frozen history mutated')
    scalars=dict(energy_scale=es, nominal_displacement=us, area=float(det.sum()), thickness=1.,
                 free_uv_dofs=int(free.sum())*2, damage_dofs=len(d),
                 healing_gp_max=float(gap.max()), healing_gp_rms=float(((gap.square()*det).sum()/det.sum()).sqrt()),
                 residual_screen_threshold=.001, reference_status='REFERENCE_STATIONARY' if max(rows[-1]['rho_u'],rows[-1]['box_projected_damage_residual'])<=.001 else 'REFERENCE_NONSTATIONARY',
                 irreversibility_penalty_coefficient=MODEL.irrPenalty(),
                 note='Component projected residuals are diagnostic, nonadditive; history stays frozen; no FEM previous-state control available.')
    arrays.update(xy=xy.numpy(),conn=conn.numpy(),nodal_mass_fraction=mass.numpy(),free_uv_mask=free.numpy(),healing_gp=gap.numpy(),det_j=det.numpy(),target_damage=d.detach().numpy())
    if not all(np.isfinite(a).all() for a in arrays.values()) or not all(np.isfinite(float(v)) for row in rows for k,v in row.items() if k!='component'):
        raise RuntimeError('Nonfinite audit output')
    return rows,scalars,arrays


def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    start=time.time();identity=audit(a.inputs)
    if max(identity['bottom_uv_max'],identity['top_u_max'],abs(identity['top_v_min']-.11999988),abs(identity['top_v_max']-.11999988))>1e-12:raise ValueError('Target BC mismatch')
    ck=torch.load(a.inputs/'checkpoint_step_413.pt',map_location='cpu',weights_only=False)
    with h5py.File(a.inputs/'cycle_0083_s004_normalized.mat') as f:
        g=f['cycle_state'];xy=torch.tensor(np.asarray(g['node_coords']).T,dtype=torch.float64);conn=torch.tensor(np.asarray(g['connectivity_q4']).T.astype(np.int64)-1)
        uv=torch.tensor(np.asarray(g['u_node']).T,dtype=torch.float64);d=torch.tensor(np.asarray(g['d_node']).reshape(-1),dtype=torch.float64)
    # Preserve the production float32 fatigue-map evaluation; then promote for derivative audit.
    f0=compute_fatigue_degrad(ck['hist_fat'],CFG).detach().double()
    rows,summary,arrays=evaluate(xy,conn,uv,d,ck['hist_alpha'].clamp(0,1).double(),f0,.11999988)
    with (a.out/'residual_components.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary.update(input_identity=identity,math_dtype='float64',fatigue_dtype_origin='float32 checkpoint and production-map, promoted to float64',
                   pid=os.getpid(),elapsed_seconds=time.time()-start,training=False,optimizer_calls=0,history_commits=0,
                   torch_version=torch.__version__,finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2));np.savez_compressed(a.out/'residual_fields.npz',**arrays)
    print(json.dumps({'summary':summary,'components':rows},indent=2),flush=True)
if __name__=='__main__':main()
