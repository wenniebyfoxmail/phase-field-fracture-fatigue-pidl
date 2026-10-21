"""Published-setting single-seed static shear solve reusing the project's NN, energy and fits.

FEM fields are not used as NN inputs or supervision.
Uses the independently retained author T3 mesh. No FEM field is a training input.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'SENS_tensile'), str(ROOT / 'source')]


import torch
from field_computation import FieldComputation


def initial_crack_mask(x):
    """Geometric original segment only; never constrain a future crack path."""
    return (x[:, 1].abs() < 1e-10) & (x[:, 0] >= -.5-1e-10) & (x[:, 0] <= 1e-10)


class ShearFieldComputation(FieldComputation):
    def fieldCalculation(self, inp):
        guard=getattr(self,'resource_guard',None)
        if guard is not None: guard()
        u, v, alpha = super().fieldCalculation(inp)
        self.latest_fields=(u.detach(),v.detach(),alpha.detach(),self.lmbda.detach())
        if guard is not None: guard()
        return u, v, alpha


def split_quads(nodes, quads):
    import numpy as np
    triangles = np.stack([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]], axis=1).reshape(-1, 3)
    xy = nodes[triangles]
    e1, e2 = xy[:, 1] - xy[:, 0], xy[:, 2] - xy[:, 0]
    signed = (e1[:, 0]*e2[:, 1]-e1[:, 1]*e2[:, 0]) / 2
    negative = signed < 0
    triangles[negative] = triangles[negative][:, [0, 2, 1]]
    assert np.all(np.abs(signed) > 0)
    return triangles, np.abs(signed)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh', type=Path, required=True, help='Independent author T3 mesh; never FEM field input')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--epochs', type=int, default=10000)
    p.add_argument('--hours', type=float, default=6)
    args = p.parse_args()
    import numpy as np
    import torch
    from construct_model import construct_model
    from field_computation import FieldComputation
    from compute_energy import compute_energy, compute_energy_per_elem, gradients, get_psi_plus_per_elem
    from fit import fit, fit_with_early_stopping
    from optim import get_optimizer
    from utils import hist_alpha_init
    assert torch.cuda.is_available(), 'GPU producer required'
    assert not args.output.exists(), 'Fresh output directory required'
    args.output.mkdir(parents=True)
    torch.set_num_threads(4)
    start = time.monotonic()
    torch.cuda.set_per_process_memory_fraction(min(1.,20*1024**3/torch.cuda.get_device_properties(0).total_memory))
    def resource_guard():
        assert time.monotonic()-start < args.hours*3600, 'PIDL wall budget reached'
        assert torch.cuda.memory_allocated() <= 20*1024**3 and torch.cuda.memory_reserved() <= 20*1024**3, 'CUDA memory limit'
        assert torch.cuda.mem_get_info()[0] >= 4*1024**3, 'GPU physical headroom below4GiB'
    resource_guard()
    from utils import parse_mesh
    X,Y,tri,area = parse_mesh(str(args.mesh), 'numerical')
    nodes = np.column_stack([X,Y]); tri=np.asarray(tri,dtype=np.int64)
    assert np.all(area>0) and abs(float(np.sum(area))-1.) < 1e-6
    assert np.allclose(nodes.min(axis=0),[-.5,-.5]) and np.allclose(nodes.max(axis=0),[.5,.5])
    x = torch.tensor(nodes,dtype=torch.float32,device='cuda')
    conn = torch.tensor(tri,dtype=torch.long,device='cuda')
    areas = torch.tensor(area,dtype=torch.float32,device='cuda')
    domain = torch.tensor([[-.5, .5], [-.5, .5]], device='cuda')
    network = dict(model_type='MLP', hidden_layers=8, neurons=400, seed=1, activation='TrainableReLU', init_coeff=3.0)
    pff, mat, net = construct_model(dict(PFF_model='AT1', se_split='volumetric', tol_ir=.005, residual_stiffness=0.),
        dict(mat_E=1., mat_nu=.3, w1=1., l0=.01), network, domain, 'cuda')
    net = net.to('cuda')
    field = ShearFieldComputation(net, domain, torch.tensor([0.], device='cuda'), torch.tensor([0.], device='cuda'))
    field.resource_guard=resource_guard
    crack = dict(x_init=[-.5], y_init=[0.], L_crack=[.5], angle_crack=[0.])
    history = hist_alpha_init(x, mat, pff, crack).detach()
    schedule=np.round(np.r_[np.arange(1,8)*.03,np.arange(24,41)*.01],8)
    assert len(schedule)==24 and schedule[-1]==.4
    top = torch.isclose(x[:, 1], torch.tensor(.5, device='cuda'))
    bottom = torch.isclose(x[:, 1], torch.tensor(-.5, device='cuda'))
    free_u = ~(top | bottom)
    cfg = None  # Original centroid negative-part penalty; no GP3 override
    # Initial state is the explicit material/profile state, before NN fitting.
    np.savez_compressed(args.output/'mesh.npz', nodes=nodes, triangles=tri, area=area)
    np.savez_compressed(args.output/'state_000.npz', alpha=history.cpu().numpy(), u=np.zeros(len(nodes)), v=np.zeros(len(nodes)), U=0., step=0, timing='initial_unloaded_before_any_solve')
    (args.output/'settings.json').write_text(json.dumps(dict(network=network, pff='AT1', split='AMOR', fatigue=False,
        material=dict(E=1., nu=.3, Gc=.01, ell=.01, eta=0.), schedule=schedule.tolist(),
        contract='manav-published-static-seed1', hard_initial_crack=False, irreversibility_tolerance=.005, irreversibility_quadrature=cfg, weight_decay=1e-5,
        max_epochs=args.epochs, hours=args.hours, torch=torch.__version__, gpu=torch.cuda.get_device_name(),
        pretraining='same mesh first loaded state; first step uses 1 LBFGS epoch then RPROP',
        interpretation='exploratory; independent author T3 versus FEM Q4; analytic NN initialization versus FEM recovery; single seed'), indent=2))
    training = [(x, torch.zeros(len(x),1,device='cuda'))]
    with (args.output/'trajectory.csv').open('w', newline='') as f:
        writer = None
        for step, U in enumerate(schedule, 1):
            step_start=time.monotonic()
            stage='before_fit'
            try:
                assert time.monotonic()-start < args.hours*3600, 'PIDL budget reached'
                field.lmbda = torch.tensor([float(U)], device='cuda')
                stage='first_LBFGS_or_RPROP'
                if step == 1:
                    fit(field, training, conn, areas, history, mat, pff, 1e-5, 1,
                        torch.optim.LBFGS(field.parameters(),lr=.5,max_iter=20000,max_eval=20000000,history_size=250,line_search_fn='strong_wolfe',tolerance_change=np.finfo(float).eps,tolerance_grad=np.finfo(float).eps), irreversibility_penalty_cfg=cfg)
                losses = fit_with_early_stopping(field, training, conn, areas, history, mat, pff,
                    1e-5, args.epochs, get_optimizer(field.parameters(),'RPROP'), 5e-6,
                    irreversibility_penalty_cfg=cfg)
                stage='post_fit_diagnostics_pre_history_update'
                with torch.no_grad():
                    u,v,alpha=field.fieldCalculation(x)
                u=u.detach().requires_grad_(True); v=v.detach().requires_grad_(True); alpha=alpha.detach()
                eel,ed,eh=compute_energy(x,u,v,alpha,history,mat,pff,areas,conn,irreversibility_penalty_cfg=cfg)
                assert all(torch.isfinite(z) for z in (eel,ed,eh)), 'Nonfinite energy'
                force_u,force_v=torch.autograd.grad(eel,(u,v))
                strain=gradients(x,u.detach(),v.detach(),alpha,areas,conn)[:3]
                energies=compute_energy_per_elem(x,u.detach(),v.detach(),alpha,history,mat,pff,areas,conn,irreversibility_penalty_cfg=cfg)
                psi_active=get_psi_plus_per_elem(x,u.detach(),v.detach(),alpha,mat,pff,areas,conn)
                psi_raw=get_psi_plus_per_elem(x,u.detach(),v.detach(),torch.zeros_like(alpha),mat,pff,areas,conn)
                cpu=lambda z:z.detach().cpu().numpy()
                residual=torch.sqrt((force_u[free_u]**2).sum()+(force_v[free_u]**2).sum())
                row=dict(step=step,U=float(U),Rx_top=float(force_u[top].sum()),Rx_bottom=float(force_u[bottom].sum()),
                    E_el=float(eel),E_d=float(ed),E_hist=float(eh),res_u=float(residual),
                    alpha_min=float(alpha.min()),alpha_max=float(alpha.max()),max_healing=float((history-alpha).max()),
                    epochs=len(losses),stop_reason=('epoch_limit' if len(losses)==args.epochs else 'loss_change_10_steps'),seconds=time.monotonic()-start,step_seconds=time.monotonic()-step_start,
                    cuda_allocated_bytes=torch.cuda.memory_allocated(),cuda_reserved_bytes=torch.cuda.memory_reserved())
                np.savez_compressed(args.output/f'state_{step:03d}.npz',u=cpu(u),v=cpu(v),alpha=cpu(alpha),hist_alpha=cpu(history),
                    eps_xx=cpu(strain[0]),eps_yy=cpu(strain[1]),eps_xy=cpu(strain[2]),
                    E_el_elem=cpu(energies[0]),E_d_elem=cpu(energies[1]),E_hist_elem=cpu(energies[2]),
                    psi_active=cpu(psi_active),psi_raw=cpu(psi_raw),force_u=cpu(force_u),force_v=cpu(force_v),
                    U=U,step=step,timing='post_solve_pre_history_update')
                torch.save(dict(network=net.state_dict(),hist_alpha=cpu(history),U=float(U),step=step),args.output/f'model_{step:03d}.pt')
                if writer is None:
                    writer=csv.DictWriter(f,fieldnames=list(row)); writer.writeheader()
                writer.writerow(row); f.flush()
                print(json.dumps(row),flush=True)
                assert row['alpha_min'] >= -.005 and row['alpha_max'] <= 1.005 and row['max_healing'] <= .005, 'PIDL damage validity failed; candidate retained'
                assert all(torch.isfinite(z).all() for z in (u,v,alpha,force_u,force_v)), 'Nonfinite candidate'
                # Preserve the existing soft-penalty history policy, no hidden max/clip.
                stage='post_candidate_history_update'
                history=alpha.clone()
            except Exception as failure:
                # Retain the last actually evaluated iterate; never refit/re-evaluate.
                record=dict(step=step,U=float(U),stage=stage,reason=str(failure),
                    seconds=time.monotonic()-start,step_seconds=time.monotonic()-step_start)
                latest=getattr(field,'latest_fields',None)
                if latest is not None:
                    lu,lv,la,lU=latest
                    np.savez_compressed(args.output/f'failed_state_{step:03d}.npz',
                        u=lu.cpu().numpy(),v=lv.cpu().numpy(),alpha=la.cpu().numpy(),
                        evaluated_U=lU.cpu().numpy(),requested_U=float(U),step=step,
                        hist_alpha=history.cpu().numpy(),timing='unaccepted_last_evaluated_iterate',
                        stage=stage,rejection_reason=str(failure))
                torch.save(dict(network=net.state_dict(),U=float(U),step=step,stage=stage),args.output/f'failed_model_{step:03d}.pt')
                (args.output/'failure.json').write_text(json.dumps(record,indent=2))
                raise
    (args.output/'COMPLETED.txt').write_text('All prescribed states solved; numerical validity still requires analysis.\n')


if __name__ == '__main__':
    main()
