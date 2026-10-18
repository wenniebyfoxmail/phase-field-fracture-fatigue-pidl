"""One prospective c1s4 fixed-d UV-head solve. Import performs no I/O or work."""
from pathlib import Path
import json
import math
import os
import sys
import time


class StopBudget(Exception):
    pass


def run(contract, out, start):
    # Called only by guard.py AFTER explicit execution approval and preflight.
    import numpy as np
    import torch
    from scipy.linalg import svd
    from scipy.optimize import minimize
    root = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(root / 'source'), str(root / 'SENS_tensile')]
    from run_native_q4_one_step_matrix import make_field
    from q4_quadrature import q4_shape_data, q4_gradient, q4_interpolate
    from compute_energy import strain_energy_with_split
    from material_properties import MaterialProperties
    from pff_model import PFFModel

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.manual_seed(1)
    torch.use_deterministic_algorithms(True)
    device = torch.device('cuda:0')
    torch.cuda.reset_peak_memory_stats()
    limits = contract['budget']
    torch.cuda.set_per_process_memory_fraction(
        limits['gpu_reserved_bytes'] / torch.cuda.get_device_properties(0).total_memory)
    count = 0
    trace = []
    paths = {v['role']: Path(v['path']) for v in contract['files']}

    def save(name, value):
        (out / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

    def elapsed():
        return time.monotonic() - start

    def check_work():
        if elapsed() >= limits['work_seconds']:
            raise StopBudget('work_deadline')
        if torch.cuda.max_memory_reserved() > limits['gpu_reserved_bytes']:
            raise RuntimeError('GPU reserved memory cap')

    def tensor(value):
        return torch.as_tensor(value, device=device, dtype=torch.float64)

    # np.load is deliberately restricted to these three scientific payloads.
    with np.load(paths['state'], allow_pickle=False) as a:
        fields = next(v['decode_fields'] for v in contract['files'] if v['role'] == 'state')
        data = {k: a[k] for k in fields}
    with np.load(paths['baseline_fields'], allow_pickle=False) as a:
        baseline = {k: a[k] for k in ('u', 'v', 'd')}
    baseline_record = json.loads(paths['baseline_result'].read_text())
    state = torch.load(paths['model'], map_location='cpu', weights_only=True)
    assert data['nodes'].shape == (86756, 2)
    assert data['cells'].shape == (86408, 4)
    assert np.issubdtype(data['cells'].dtype, np.integer)
    assert data['cells'].min() >= 0 and data['cells'].max() < 86756
    assert data['freeu'].ndim == 1 and np.issubdtype(data['freeu'].dtype, np.integer)
    assert len(np.unique(data['freeu'])) == len(data['freeu'])
    assert data['freeu'].min() >= 0 and data['freeu'].max() < 2 * 86756
    for k, value in data.items():
        assert np.isfinite(value).all(), k
    for k, value in baseline.items():
        assert value.shape == (86756,) and np.isfinite(value).all(), k
    assert np.array_equal(baseline['d'], data['d_fem'])
    assert np.all((data['d_fem'] >= 0) & (data['d_fem'] <= 1))
    assert baseline_record['block'] == 'U' and baseline_record['kind'] == 'energy'
    assert baseline_record['weight_regularizer'] == 0.0
    assert baseline_record['E_el'] == 0.005672469584399648
    x = tensor(data['nodes'])
    cells = torch.as_tensor(data['cells'], device=device, dtype=torch.long)
    free = torch.as_tensor(data['freeu'], device=device, dtype=torch.long)
    N, B, weights = q4_shape_data(x, cells)
    assert bool(torch.all(weights > 0))
    d = tensor(data['d_fem'])
    dg = q4_interpolate(d, cells, N)
    mat = MaterialProperties(1., .3, 1., .01)
    model = PFFModel('AT1', 'volumetric', .005, residual_stiffness=0.)
    mass = torch.zeros(len(x), device=device, dtype=torch.float64)
    for j in range(4):
        mass.scatter_add_(0, cells[:, j], (weights * N[:, j]).sum(1))
    assert bool(torch.all(mass > 0))

    def energy(u, v, *, optimizing=False):
        nonlocal count
        check_work()
        if count >= limits['evaluations']:
            raise StopBudget('evaluation_cap')
        if optimizing and (count >= limits['evaluations'] - 8 or
                           elapsed() >= limits['opt_no_new_eval_seconds']):
            raise StopBudget('optimization_cap_or_deadline')
        count += 1  # Every objective/readout/FD trial uses the same counter.
        gu, gv = q4_gradient(u, cells, B), q4_gradient(v, cells, B)
        el, raw = strain_energy_with_split(
            gu[:, :, 0], gv[:, :, 1], .5 * (gu[:, :, 1] + gv[:, :, 0]), dg, mat, model)
        result = (weights * el).sum()
        if not bool(torch.isfinite(result)) or float(result.detach()) <= 0:
            raise RuntimeError('invalid elastic energy')
        return result, raw

    def measure(u, v):
        uu, vv = u.detach().clone().requires_grad_(True), v.detach().clone().requires_grad_(True)
        e, raw = energy(uu, vv)
        gu, gv = torch.autograd.grad(e, (uu, vv))
        force = torch.cat((gu, gv))
        ref_grad = torch.stack((q4_gradient(tensor(data['u_fem']), cells, B),
                                q4_gradient(tensor(data['v_fem']), cells, B)))
        error_grad = torch.stack((q4_gradient(uu.detach()-tensor(data['u_fem']), cells, B),
                                  q4_gradient(vv.detach()-tensor(data['v_fem']), cells, B)))
        h1 = (weights * error_grad.square().sum((0, 3))).sum() / (
            weights * ref_grad.square().sum((0, 3))).sum()
        uv_error = (mass * ((uu.detach()-tensor(data['u_fem']))**2 +
                            (vv.detach()-tensor(data['v_fem']))**2)).sum()
        uv_norm = (mass * (tensor(data['u_fem'])**2+tensor(data['v_fem'])**2)).sum()
        return dict(E_el=float(e), free_u_l2=float(torch.linalg.vector_norm(force[free])),
                    uv_H1_rel=float(torch.sqrt(h1)), uv_mass_rel_L2=float(torch.sqrt(uv_error/uv_norm))), raw.detach(), force.detach()

    field = make_field(state, device, contract['load'], 'legacy_nonsmooth')
    field.net = field.net.double()
    # Match PBD make_smooth's float64 UV lift, not the float32 control arm.
    field.domain_extrema = field.domain_extrema.double()
    field.lmbda = tensor([contract['load']])
    field.theta = tensor([math.pi / 2])
    for parameter in field.net.parameters():
        parameter.requires_grad_(False)
    original = {k: v.detach().clone() for k, v in field.net.state_dict().items()}
    with torch.no_grad():
        features = field.net.encode(x)
        u0, v0, _ = field.fieldCalculation(x)
    original_metrics, raw0, _ = measure(u0, v0)
    assert abs(original_metrics['E_el'] - baseline_record['objective_scale']) <= 1e-10
    fem_u, fem_v = tensor(data['u_fem']), tensor(data['v_fem'])
    fem_metrics, rawf, force = measure(fem_u, fem_v)
    assert float((force - tensor(data['ru_fem'])).abs().max()) <= 1e-10
    assert fem_metrics['free_u_l2'] < 1e-8
    base_metrics, rawb, _ = measure(tensor(baseline['u']), tensor(baseline['v']))
    base_discrepancy = abs(base_metrics['E_el'] - baseline_record['E_el'])
    assert base_discrepancy <= 1e-10
    check_work()

    # Additive retained-SVD increments preserve ALL original coefficients,
    # including discarded directions. rcond is fixed; no rank/cutoff sweep.
    design = (field.lmbda * (x[:, 1] + .5) * (.5 - x[:, 1]))[:, None] * torch.cat(
        (features, torch.ones((len(x), 1), device=device, dtype=torch.float64)), 1)
    h = design.cpu().numpy()
    wm = mass.cpu().numpy()
    left, singular, right = svd(h * np.sqrt(wm[:, None]), full_matrices=False,
                                check_finite=True, lapack_driver='gesdd')
    del left
    keep = singular > contract['rcond'] * singular[0]
    assert keep.any()
    transform_np = right[keep].T / singular[keep]
    transform = tensor(transform_np)
    basis = design @ transform
    rank = int(keep.sum())
    save('basis.json', dict(rank=rank, columns=h.shape[1], rcond=contract['rcond'],
                            singular_values=singular.tolist(),
                            retained_condition=float(singular[0] / singular[keep][-1]),
                            omitted_directions='unchanged original head coefficients'))
    del h, right, features
    check_work()
    last = np.zeros((rank, 2), dtype=np.float64)
    scale = original_metrics['E_el']
    accepted = []

    def objective(z, optimizing=True):
        zz = tensor(np.asarray(z).reshape(rank, 2)).requires_grad_(True)
        uv = basis @ zz
        e, _ = energy(u0 + uv[:, 0], v0 + uv[:, 1], optimizing=optimizing)
        scaled = e / scale
        gradient = torch.autograd.grad(scaled, zz)[0]
        assert bool(torch.isfinite(gradient).all())
        value = float(scaled.detach())
        trace.append(dict(evaluation=count, normalized_energy=value,
                          projected_gradient_l2=float(torch.linalg.vector_norm(gradient))))
        return value, gradient.detach().cpu().numpy().ravel()

    # Fixed one-direction derivative contract; not another optimization arm.
    z0 = last.ravel()
    _, g0 = objective(z0, optimizing=False)
    direction = np.random.default_rng(1).normal(size=z0.shape)
    direction /= np.linalg.norm(direction)
    fd = []
    for step in (1e-5, 1e-6, 1e-7):
        a, _ = objective(z0 + step * direction, optimizing=False)
        b, _ = objective(z0 - step * direction, optimizing=False)
        fd.append(abs((a - b) / (2 * step) - float(g0 @ direction)))
    assert min(fd) <= 1e-8 + 1e-4 * abs(float(g0 @ direction))
    save('derivative_contract.json', dict(absolute_errors=fd, direction_seed=1))
    last_value = 1.0

    def callback(z):
        nonlocal last, last_value
        value, _ = objective(z)
        assert value <= last_value + 1e-10 * max(1., abs(last_value))
        last = np.asarray(z).reshape(rank, 2).copy()
        last_value = value
        accepted.append(dict(evaluations=count, normalized_energy=value))

    stop = 'optimizer_return'
    try:
        result = minimize(objective, z0, jac=True, method='L-BFGS-B', callback=callback,
                          options=dict(maxfun=400, maxiter=400, maxls=20, maxcor=10,
                                       ftol=1e-14, gtol=1e-8))
        # Only callback-confirmed accepted points survive. Never use a trial x.
        stop = str(result.message)
    except StopBudget as reason:
        stop = str(reason)
    save('trace.json', trace)
    save('accepted.json', accepted)

    # Actual network realization is authoritative, rather than cached basis.
    delta = transform @ tensor(last)
    with torch.no_grad():
        field.net.output_layer.weight[:2].add_(delta[:-1].T)
        field.net.output_layer.bias[:2].add_(delta[-1])
        uh, vh, _ = field.fieldCalculation(x)
    for key, value in field.net.state_dict().items():
        if key not in ('output_layer.weight', 'output_layer.bias'):
            assert torch.equal(value, original[key]), key
        else:
            assert torch.equal(value[2:], original[key][2:]), key
    head_metrics, rawh, head_force = measure(uh, vh)
    uv_basis = basis @ tensor(last)
    basis_metrics, _, _ = measure(u0 + uv_basis[:, 0], v0 + uv_basis[:, 1])
    realization = abs(head_metrics['E_el'] - basis_metrics['E_el'])
    realization_uv = float(torch.max(torch.abs(torch.stack(
        (uh-u0-uv_basis[:, 0], vh-v0-uv_basis[:, 1])))))
    assert realization_uv <= 1e-9 and realization <= 1e-10
    _, final_gradient = objective(last.ravel(), optimizing=False)
    full_head_gradient = design.T @ torch.stack((head_force[:len(x)], head_force[len(x):]), 1) / scale
    uncertainty = max(base_discrepancy, realization, 64 * np.finfo(float).eps * scale)
    gain = (baseline_record['E_el'] - head_metrics['E_el']) / baseline_record['E_el']
    robust = gain >= contract['relative_gain_screen'] and (
        baseline_record['E_el'] - head_metrics['E_el']) > 10 * uncertainty
    resolved_positive = baseline_record['E_el'] - head_metrics['E_el'] > 10 * uncertainty
    resolved_negative = head_metrics['E_el'] - baseline_record['E_el'] > 10 * uncertainty
    verdict = ('optimization_witness' if robust else
               'small_resolved_gain_below_screen' if resolved_positive else
               'energy_regression' if resolved_negative else 'numerically_unresolved')
    metrics = dict(protocol=contract['protocol'], run_id=contract['run_id'],
                   state='c1s4 conditional MCS outer9, U=.11999988',
                   original=original_metrics, saved_PBD=baseline_record,
                   PBD_identity_readout=base_metrics, FEM=fem_metrics, head=head_metrics,
                   gain_over_saved_PBD=gain, numerical_energy_uncertainty=uncertainty,
                   actual_basis_energy_difference=realization,
                   actual_basis_displacement_maxabs=realization_uv,
                   retained_gradient_l2=float(np.linalg.norm(final_gradient)),
                   full_head_gradient_l2=float(torch.linalg.vector_norm(full_head_gradient)),
                   full_head_gradient_inf=float(full_head_gradient.abs().max()),
                   robust_directional_gain=robust, stationarity_screen=float(np.abs(final_gradient).max()) <= 1e-8,
                   verdict=verdict,
                   stop=stop, evaluations=count, history_commits=0, rollout_steps=0,
                   hidden_updates=0, damage_updates=0, elapsed_seconds=elapsed(),
                   max_gpu_reserved_bytes=torch.cuda.max_memory_reserved(),
                   boundary='Frozen-feature conditional diagnostic, not full-network capacity or coupled/physical qualification')
    save('summary.json', metrics)
    np.savez_compressed(out / 'head.npz', uv_weight=field.net.output_layer.weight[:2].cpu().numpy(),
                        uv_bias=field.net.output_layer.bias[:2].cpu().numpy(), z=last,
                        transform=transform_np)
    np.savez_compressed(out / 'fields.npz', nodes=data['nodes'], cells=data['cells'],
                        u=uh.cpu().numpy(), v=vh.cpu().numpy(), d=data['d_fem'],
                        raw=rawh.cpu().numpy())
    # Decision figure comes from these exact readouts; no extra optimization.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    centers = data['nodes'][data['cells']].mean(1)
    g = (1. - dg).square()
    act = [(weights * g * raw).sum(1) / weights.sum(1) for raw in (rawf, rawb, rawh)]
    arrays = [a.cpu().numpy() for a in act]
    fig, grid = plt.subplots(2, 4, figsize=(14, 6.7))
    axes = grid[0]
    emin, emax = min(a.min() for a in arrays), max(a.max() for a in arrays)
    for ax, values, label in zip(axes[:3], arrays, ('FEM fixed-d reference', 'Saved PBD U endpoint', 'Actual UV head')):
        im = ax.scatter(centers[:, 0], centers[:, 1], c=values, s=.5, vmin=emin, vmax=emax, rasterized=True)
        ax.set(title=label, xlabel='x', ylabel='y', aspect='equal')
    fig.colorbar(im, ax=list(axes[:3]), label='GP-mean active energy')
    axes[3].bar(['PBD', 'head'], [1., head_metrics['E_el'] / baseline_record['E_el']])
    axes[3].axhline(1. - contract['relative_gain_screen'], color='r', linestyle='--')
    axes[3].set(title='Same elastic energy / saved PBD', ylabel='ratio')
    differences = [arrays[1]-arrays[0], arrays[2]-arrays[0], arrays[2]-arrays[1]]
    vmax = max(float(np.max(np.abs(a))) for a in differences) or 1e-30
    for ax, values, label in zip(grid[1, :3], differences,
                                 ('PBD minus FEM', 'Head minus FEM', 'Head minus PBD')):
        diff_im = ax.scatter(centers[:, 0], centers[:, 1], c=values, s=.5,
                             cmap='coolwarm', vmin=-vmax, vmax=vmax, rasterized=True)
        ax.set(title=label, xlabel='x', ylabel='y', aspect='equal')
    fig.colorbar(diff_im, ax=list(grid[1, :3]), label='signed GP-mean active difference')
    grid[1, 3].bar(['PBD', 'head'], [base_metrics['free_u_l2'], head_metrics['free_u_l2']])
    grid[1, 3].set(title='Free displacement residual', yscale='log')
    fig.suptitle('Synthetic seen c1s4, horizon 0; '+contract['run_id'])
    fig.savefig(out / 'decision.png', dpi=160)
    plt.close(fig)
    (out / 'decision.md').write_text(
        '# c1s4 same-energy UV head decision figure\n\n'
        'Source: '+contract['run_id']+'; exact same-run summary.json and fields.npz. '
        'Synthetic seen c1s4, U=.11999988, horizon0; no independent physical units.\n\n'
        'Top: fixed-d FEM, saved PBD U endpoint and actual head active fields on '
        'one common scale, followed by same elastic energy / saved PBD and the '
        'prospective directional screen. Bottom: signed PBD-FEM, head-FEM and '
        'head-PBD differences on a common symmetric scale, then free-u residual. '
        'All cells shown; x/y are native coordinates.\n\n'
        f'Actual gain={gain:.12g}; verdict={verdict}. Scalars in summary.json '
        'are authoritative. Energy gain may coexist with spatial or residual cost; '
        'this is no coupled evolution, capacity or physical-teacher result.\n')
    (out / 'README_analysis.md').write_text(
        '# c1s4 fixed-d UV head\n\nQuestion: lower same elastic energy than saved PBD?\n'
        'Read decision.png from FEM to PBD to actual head, then the energy ratio. '
        'Shared active-field scale; all cells shown, no selected patch. summary.json is authoritative. '
        'No independent-unit variation from this single synthetic state. '
        'Only a robust actual-energy gain witnesses an optimization opportunity. '
        'No full-network capacity, coupled evolution, teacher or physical conclusion.\n')
    check_work()
    return metrics
