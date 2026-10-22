"""S04-E035: frozen-history main-solve L2 intervention; GPU producer only."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'SENS_tensile')]
import numpy as np
import torch
from construct_model import construct_model
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
from compute_energy import compute_energy, get_psi_plus_per_elem
from fatigue_history import compute_fatigue_degrad, update_fatigue_history
from fit import fit_with_early_stopping
from optim import get_optimizer

EXPERIMENT_ID = "S04-E035"
ARMS = (("L2_1e-5", 1e-5), ("L2_zero", 0.))
STEPS = (4, 5, 199, 200, 414, 415)
FACTORS = (.25, .5, .75, 1., 0.)
FAT = dict(loading_type='cyclic', accum_type='carrara',
           degrad_type='asymptotic', alpha_T=.5)
IRR = dict(enable=True, mode='fem_gp_tri3')
REDUCTION = dict(enable=True, mode='fem_gp_tri3_g_mean')


def load(path, device):
    return torch.load(path, map_location=device, weights_only=False)


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def flat_grads(named, coefficient, physical_grads):
    """Full-coordinate gradients, including biases and activation parameters.

    Use independently differentiated physical gradients (never subtraction
    from a rounded float32 total). Compare canonical 1e-5 L2 signs at the
    SAME parameter vector, even in the zero-L2 arm. Actual optimizer .grad
    buffers are read only and are also reported separately.
    """
    phys, reg, actual = [], [], []
    for (name, p), physical in zip(named, physical_grads, strict=True):
        g = torch.zeros_like(p) if p.grad is None else p.grad.detach()
        r = 2e-5 * p.detach() if 'weight' in name else torch.zeros_like(p)
        physical = torch.zeros_like(p) if physical is None else physical.detach()
        phys.append(physical.reshape(-1))
        reg.append(r.reshape(-1))
        actual.append(g.reshape(-1))
    gp, gr = torch.cat(phys), torch.cat(reg)
    gt = gp + gr
    ga = torch.cat(actual)
    return dict(grad_logE_l2=float(gp.norm()), grad_L2_l2=float(gr.norm()),
                grad_regularized_l2=float(gt.norm()),
                grad_actual_objective_l2=float(ga.norm()),
                actual_sign_change_fraction=float((gp.sign() != ga.sign()).float().mean()),
                sign_change_fraction=float((gp.sign() != gt.sign()).float().mean()),
                nonzero_opposite_fraction=float(((gp * gt) < 0).float().mean()),
                physical_zero_fraction=float((gp == 0).float().mean()))


class TimeCap(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--arm-seconds', type=float, default=240.)
    parser.add_argument('--total-seconds', type=float, default=3300.)
    args = parser.parse_args()
    assert 0 < args.arm_seconds <= 240 and 0 < args.total_seconds <= 3300
    assert torch.cuda.is_available(), 'Never train on Mac/CPU'
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    device = 'cuda'
    torch.set_num_threads(4)
    extrema = torch.tensor([[-.5, .5], [-.5, .5]], device=device)
    pff, mat, net = construct_model(
        dict(PFF_model='AT1', se_split='volumetric', tol_ir=5e-3,
             residual_stiffness=0.),
        dict(mat_E=1., mat_nu=.3, w1=1., l0=.01),
        dict(hidden_layers=8, neurons=400, seed=1,
             activation='TrainableReLU', init_coeff=1., compile=False),
        extrema, device)
    field = FieldComputation(net.to(device), extrema, torch.tensor(0., device=device),
                             torch.tensor([np.pi/2], device=device), l0=.01)
    inp, conn, area, _ = prep_input_data(
        mat, pff, dict(x_init=[-.5], y_init=[0], L_crack=[.5], angle_crack=[0]),
        dict(gradient_type='numerical'),
        str(ROOT / 'SENS_tensile/meshed_geom_fem_soft_hist0.msh'), device)
    assert inp.shape == (45591, 2) and conn.shape == (90000, 3)
    out = torch.zeros((len(inp), 1), device=device)
    named = list(net.named_parameters())
    best = args.baseline / 'best_models'
    settings = (args.baseline / 'model_settings.txt').read_text()
    for token in ('umax: 0.12', 'mesh_tag: hard_d1_u0_recovery',
                  'recovery_step_offset: 1', 'fem_gp_tri3_g_mean'):
        assert token in settings, token
    dump(args.output / 'manifest.json', dict(
        experiment=EXPERIMENT_ID, protocol='r1', source_commit=args.source_commit,
        baseline=str(args.baseline), steps=STEPS, torch=torch.__version__,
        device=torch.cuda.get_device_name(0), arm_seconds=args.arm_seconds,
        total_seconds=args.total_seconds, initialization='shared archived previous-step network',
        history='frozen previous-step postcommit; no trajectory rollout',
        run_ids=[f'{EXPERIMENT_ID}-R{i:03d}' for i in range(1, len(STEPS)*len(ARMS)+1)]))
    np.savez_compressed(args.output / 'mesh.npz', xy=inp.cpu().numpy(),
                        triangles=conn.cpu().numpy(), area=area.cpu().numpy())
    results = []

    for step in STEPS:
        ckpt = load(best / f'checkpoint_step_{step-1}.pt', device)
        assert ckpt['history_driver_mode'] == 'current_active'
        assert not ckpt['lagged_stiffness_enabled'] and not ckpt['_frac_detected']
        history = ckpt['hist_alpha'].detach().clone()
        histfat = ckpt['hist_fat'].detach().clone()
        prevpsi = ckpt['psi_plus_prev'].detach().clone()
        fatigue = compute_fatigue_degrad(histfat, FAT)
        initial = load(best / f'trained_1NN_{step-1}.pt', device)
        field.lmbda = torch.tensor(.12 * FACTORS[(step-1) % 5], device=device)

        def evaluate(folder, label, coefficient):
            net.zero_grad(set_to_none=True)
            u, v, d = field.fieldCalculation(inp)
            energies = compute_energy(inp, u, v, d, history, mat, pff, area, conn,
                                      fatigue, irreversibility_penalty_cfg=IRR)
            loge = torch.log10(sum(energies))
            reg = sum((p.square().sum() for n, p in named if 'weight' in n))
            physical_grads = torch.autograd.grad(
                loge, [p for _,p in named], allow_unused=True, retain_graph=True)
            (loge + coefficient * reg).backward()
            metrics = flat_grads(named, coefficient, physical_grads)
            metrics.update(dict(E_el=float(energies[0].detach()),
                                E_d=float(energies[1].detach()),
                                E_irr=float(energies[2].detach()), logE=float(loge.detach()),
                                canonical_L2=float(1e-5 * reg.detach())))
            with torch.no_grad():
                delta = d - history
                qdelta = delta[conn] @ torch.tensor(
                    [[4.,1.,1.], [1.,4.,1.], [1.,1.,4.]], device=device) / 6
                psi = get_psi_plus_per_elem(
                    inp, u, v, d, mat, pff, area, conn,
                    history_driver_reduction_dict=REDUCTION)
                newfat = update_fatigue_history(histfat, psi, prevpsi, FAT)
                newf = compute_fatigue_degrad(newfat, FAT)
                metrics.update(dict(d_min=float(d.min()), d_max=float(d.max()),
                                    node_retreat_max=float((-delta).clamp_min(0).max()),
                                    gp_retreat_max=float((-qdelta).clamp_min(0).max()),
                                    gp_retreat_fraction=float((qdelta < -1e-6).float().mean()),
                                    damage_below0_fraction=float((d < 0).float().mean()),
                                    damage_above1_fraction=float((d > 1).float().mean())))
                np.savez_compressed(folder / f'{label}.npz',
                    u=u.cpu().numpy(), v=v.cpu().numpy(), d=d.cpu().numpy(),
                    hist_alpha=history.cpu().numpy(), psi_active=psi.cpu().numpy(),
                    trial_histfat=newfat.cpu().numpy(), trial_f=newf.cpu().numpy())
            net.zero_grad(set_to_none=True)
            return metrics

        # Fixed order; pair receives equal caps, not leftover budget.
        for arm, coefficient in ARMS:
            if time.monotonic() - started + args.arm_seconds + 10 > args.total_seconds:
                dump(args.output / 'budget_stop.json', dict(elapsed=time.monotonic()-started,
                                                          next_step=step, next_arm=arm))
                return
            folder = args.output / f'step_{step:03d}_{arm}'
            folder.mkdir()
            net.load_state_dict(initial, strict=True)
            beginning = evaluate(folder, 'initial', coefficient)
            optimizer = get_optimizer(field.parameters(), 'RPROP')
            original_step = optimizer.step
            trace, updates = [], [0]
            armstart = time.monotonic()
            deadline = min(armstart + args.arm_seconds, started + args.total_seconds)

            def instrumented_step(*a, **kw):
                if updates[0] % 50 == 0:
                    # Independent same-vector graph; autograd.grad preserves
                    # the actual .grad buffers that RPROP will consume.
                    u_probe, v_probe, d_probe = field.fieldCalculation(inp)
                    terms = compute_energy(inp, u_probe, v_probe, d_probe,
                        history, mat, pff, area, conn, fatigue,
                        irreversibility_penalty_cfg=IRR)
                    physical = torch.autograd.grad(torch.log10(sum(terms)),
                        [p for _,p in named], allow_unused=True)
                    trace.append(dict(update=updates[0], seconds=time.monotonic()-armstart,
                                      **flat_grads(named, coefficient, physical)))
                result = original_step(*a, **kw)
                updates[0] += 1
                if time.monotonic() >= deadline:
                    raise TimeCap
                return result

            optimizer.step = instrumented_step
            class Writer:
                def __init__(self):
                    self.rows = []
                def add_scalars(self, _tag, data, epoch):
                    self.rows.append(dict(epoch=epoch, loss=data['loss'], logE=data['loss_E']))
            writer = Writer()
            reason = 'early_stopping_or_epoch_cap'
            try:
                fit_with_early_stopping(
                    field, [(inp, out)], conn, area, history, mat, pff, coefficient,
                    num_epochs=10000, optimizer=optimizer, min_delta=5e-7,
                    writer=writer, training_dict={'save_model_every_n': 0},
                    f_fatigue=fatigue, irreversibility_penalty_cfg=IRR)
            except TimeCap:
                reason = 'wall_cap'
            if updates[0] == 10000:
                reason = 'epoch_cap'
            elapsed = time.monotonic() - armstart
            final = evaluate(folder, 'final', coefficient)
            torch.save(net.state_dict(), folder / 'final.pt')
            receipt = dict(run_id=f'{EXPERIMENT_ID}-R{len(results)+1:03d}',
                           step=step, cycle=(step-1)//5+1,
                           substep=(step-1)%5+1, load=float(field.lmbda), arm=arm,
                           coefficient=coefficient, updates=updates[0],
                           optimization_seconds=elapsed, stop_reason=reason,
                           initial=beginning, final=final)
            dump(folder / 'receipt.json', receipt)
            dump(folder / 'loss_trace.json', writer.rows)
            dump(folder / 'gradient_trace.json', trace)
            results.append(receipt)
            dump(args.output / 'results.json', results)
            print(json.dumps(receipt, allow_nan=False), flush=True)
            assert torch.equal(history, ckpt['hist_alpha'])
            assert torch.equal(histfat, ckpt['hist_fat'])
    dump(args.output / 'completed.json', dict(elapsed_seconds=time.monotonic()-started,
                                            arms=len(results), status='succeeded'))


if __name__ == '__main__':
    main()
