"""Approved producer only: frozen 388-column UV space, full 776-coordinate square-root Newton.

Import is inert. Numerical dependencies, payload reads and all construction are
inside run(), which the one-shot guard invokes only after human approval.
"""
from pathlib import Path
import json
import math
import sys
import time


class StopBudget(Exception):
    pass


class Stationary(Exception):
    pass


def run(contract, out, start):
    import numpy as np
    import torch
    from square_root import direction
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
    pc = contract['fn776']
    torch.cuda.reset_peak_memory_stats()
    paths = {row['role']: Path(row['path']) for row in contract['files']}
    allowances = contract['work_ledger']
    used = dict(curvature=0, controls=0, trials=0, final=0)
    hvp_calls = 0
    trace, accepted, timings = [], [], {}
    current_iteration = -1

    def save(name, value):
        (out / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

    def elapsed():
        return time.monotonic() - start

    def check_work():
        # The explicit authorization has no self wall-time or CUDA-memory ceiling.
        # Preserve this call-site hook so the fixed accounting structure is unchanged.
        return None

    def charge(phase, kind, cost):
        # Charged BEFORE work, including a failing/rejected call. No free setup,
        # callback, cached-HVP discount, pooled RHS or category reallocation.
        check_work()
        if used[phase] + cost > allowances[phase] or sum(used.values()) + cost > allowances['total']:
            raise StopBudget(phase + '_work_cap')
        used[phase] += cost
        with (out / 'work_ledger.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(phase=phase, kind=kind, cost=cost,
                                         used=sum(used.values()), elapsed_seconds=elapsed())) + '\n')

    def tensor(value):
        return torch.as_tensor(value, device=device, dtype=torch.float64)

    def selected_json(role):
        fields = next(row['decode_fields'] for row in contract['files'] if row['role'] == role)
        record = json.loads(paths[role].read_text())
        return {key: record[key] for key in fields}

    with np.load(paths['state'], allow_pickle=False) as payload:
        fields = next(row['decode_fields'] for row in contract['files'] if row['role'] == 'state')
        data = {key: payload[key] for key in fields}
    with np.load(paths['frozen_transform'], allow_pickle=False) as payload:
        # Never inspect/load r2's fitted z, UV weight or bias.
        transform_np = payload['transform']
    state = torch.load(paths['model'], map_location='cpu', weights_only=True)
    frozen, frozen_basis = selected_json('frozen_summary'), selected_json('frozen_basis')
    assert frozen['protocol'] == 'S04-E011-UVH-C1-r2'
    assert frozen['run_id'] == 'pf_s04e011_uvh_c1_r2_20261018'
    assert frozen_basis['rank'] == pc['rank'] == 388 and frozen_basis['columns'] == 401
    assert frozen_basis['rcond'] == contract['rcond'] == 1e-10
    assert transform_np.shape == (401, 388) and transform_np.dtype == np.float64
    assert np.isfinite(transform_np).all()
    assert data['nodes'].shape == (86756, 2) and data['cells'].shape == (86408, 4)
    assert np.issubdtype(data['cells'].dtype, np.integer)
    assert data['cells'].min() >= 0 and data['cells'].max() < 86756
    assert data['freeu'].ndim == 1 and np.issubdtype(data['freeu'].dtype, np.integer)
    assert len(np.unique(data['freeu'])) == len(data['freeu'])
    assert data['freeu'].min() >= 0 and data['freeu'].max() < 2 * 86756
    for key, value in data.items():
        assert np.isfinite(value).all(), key
    for key in ('u_fem', 'v_fem', 'd_fem'):
        assert data[key].shape == (86756,), key
    assert np.all((data['d_fem'] >= 0) & (data['d_fem'] <= 1))
    baseline = frozen['saved_PBD']
    assert baseline['block'] == 'U' and baseline['kind'] == 'energy'
    assert baseline['weight_regularizer'] == 0.0
    assert baseline['E_el'] == 0.005672469584399648
    scale = frozen['original']['E_el']
    assert scale == baseline['objective_scale'] == 0.010889692759145935
    assert frozen['head']['E_el'] == 0.006360077631691784

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

    def elastic(u, v):
        # Private uncharged primitive; reachable only inside charged wrappers.
        gu, gv = q4_gradient(u, cells, B), q4_gradient(v, cells, B)
        el, raw = strain_energy_with_split(
            gu[:, :, 0], gv[:, :, 1], .5 * (gu[:, :, 1] + gv[:, :, 0]), dg, mat, model)
        value = (weights * el).sum()
        if not bool(torch.isfinite(value)) or float(value.detach()) <= 0:
            raise RuntimeError('invalid elastic energy')
        return value, raw

    fem_u, fem_v = tensor(data['u_fem']), tensor(data['v_fem'])
    ref_grad = torch.stack((q4_gradient(fem_u, cells, B), q4_gradient(fem_v, cells, B)))

    def measure(u, v, phase):
        charge(phase, 'actual_field_energy_and_first_gradient', 1)
        uu, vv = u.detach().clone().requires_grad_(True), v.detach().clone().requires_grad_(True)
        value, raw = elastic(uu, vv)
        gu, gv = torch.autograd.grad(value, (uu, vv))
        force = torch.cat((gu, gv)).detach()
        error_grad = torch.stack((q4_gradient(uu.detach()-fem_u, cells, B),
                                  q4_gradient(vv.detach()-fem_v, cells, B)))
        h1 = (weights * error_grad.square().sum((0, 3))).sum() / (
            weights * ref_grad.square().sum((0, 3))).sum()
        uv_error = (mass * ((uu.detach()-fem_u)**2 + (vv.detach()-fem_v)**2)).sum()
        uv_norm = (mass * (fem_u**2 + fem_v**2)).sum()
        metrics = dict(E_el=float(value.detach()), free_u_l2=float(torch.linalg.vector_norm(force[free])),
                       uv_H1_rel=float(torch.sqrt(h1)), uv_mass_rel_L2=float(torch.sqrt(uv_error/uv_norm)))
        assert all(math.isfinite(v) for v in metrics.values())
        return metrics, raw.detach(), force

    field = make_field(state, device, contract['load'], 'legacy_nonsmooth')
    field.net = field.net.double()
    field.domain_extrema = field.domain_extrema.double()
    field.lmbda = tensor([contract['load']])
    field.theta = tensor([math.pi / 2])
    for parameter in field.net.parameters():
        parameter.requires_grad_(False)
    original = {key: value.detach().clone() for key, value in field.net.state_dict().items()}
    with torch.no_grad():
        features = field.net.encode(x)
        u0, v0, d0 = field.fieldCalculation(x)
    original_metrics, _, _ = measure(u0, v0, 'controls')  # Once, not a baseline solve.
    initial_error = abs(original_metrics['E_el'] - scale)
    assert initial_error <= pc['energy_abs_tolerance']
    design = (field.lmbda * (x[:, 1] + .5) * (.5 - x[:, 1]))[:, None] * torch.cat(
        (features, torch.ones((len(x), 1), device=device, dtype=torch.float64)), 1)
    transform = tensor(transform_np)
    basis = design @ transform  # No new SVD, cutoff, rank or fitted initial head.
    del features, state
    rank, size = pc['rank'], pc['z_dimension']
    assert size == rank * 2 == 776

    def physical(z):
        increment = basis @ z.reshape(rank, 2)
        return u0 + increment[:, 0], v0 + increment[:, 1]

    def objective_z(z, phase):
        charge(phase, 'z_energy_and_first_gradient', 1)
        zz = tensor(z).detach().clone().reshape(size).requires_grad_(True)
        value = elastic(*physical(zz))[0] / scale
        gradient = torch.autograd.grad(value, zz)[0]
        assert bool(torch.isfinite(gradient).all())
        record = dict(phase=phase, iteration=current_iteration, work_units=sum(used.values()),
                      normalized_energy=float(value.detach()), z_gradient_inf=float(gradient.abs().max()),
                      z_gradient_l2=float(torch.linalg.vector_norm(gradient)))
        trace.append(record)
        with (out / 'trace.jsonl').open('a') as stream:
            stream.write(json.dumps(record, allow_nan=False)+'\n')
        return float(value.detach()), gradient.detach()

    def hvp(at, direction):
        nonlocal hvp_calls
        charge('controls', 'one_current_original_Hessian_direction', 2)
        hvp_calls += 1
        # Each current-point HVP owns its forward + first derivative + directional second
        # derivative, charged together at 2. No additional uncharged evaluation.
        zz = tensor(at).detach().clone().requires_grad_(True)
        value = elastic(*physical(zz))[0] / scale
        gradient = torch.autograd.grad(value, zz, create_graph=True)[0]
        answer = torch.autograd.grad((gradient * direction).sum(), zz)[0].detach()
        assert bool(torch.isfinite(answer).all())
        return answer

    def gradient_close(actual, expected):
        error = float((actual-expected).abs().max())
        tolerance = pc['derivative_abs_tolerance'] + pc['derivative_relative_tolerance'] * max(
            float(actual.abs().max()), float(expected.abs().max()))
        assert error <= tolerance, 'gradient equivalence failed'
        return error

    def raw_field(z):
        check_work()
        delta = transform @ z.reshape(rank, 2)
        with torch.no_grad():
            field.net.output_layer.weight[:2].copy_(original['output_layer.weight'][:2] + delta[:-1].T)
            field.net.output_layer.bias[:2].copy_(original['output_layer.bias'][:2] + delta[-1])
            return field.fieldCalculation(x)

    def assert_frozen():
        for key, value in field.net.state_dict().items():
            if key in ('output_layer.weight', 'output_layer.bias'):
                assert torch.equal(value[2:], original[key][2:]), key
            else:
                assert torch.equal(value, original[key]), key

    def opt_check():
        check_work()

    def capture_factor(R, rhs):
        check_work()
        factor = dict(R=R.cpu().numpy(), rhs=rhs.cpu().numpy(), at_z=last_z.cpu().numpy(),
                      iteration=np.array(current_iteration), validation_state=np.array('unvalidated_root'))
        if current_iteration == 0:
            np.savez_compressed(out / 'initial_factor.npz', **factor)
        np.savez_compressed(out / 'latest_factor.npz', **factor)

    def log_control(record):
        record = dict(record, iteration=current_iteration, elapsed_seconds=elapsed())
        with (out / 'curvature_controls.jsonl').open('a') as stream:
            stream.write(json.dumps(record, allow_nan=False) + '\n')

    zero = torch.zeros(size, device=device, dtype=torch.float64)
    initial_value, initial_g = objective_z(zero, 'controls')
    assert abs(initial_value * scale-original_metrics['E_el']) <= pc['energy_abs_tolerance']
    probe = tensor(np.random.default_rng(pc['seed']).normal(size=size))
    probe *= pc['nonzero_probe_norm'] / torch.linalg.vector_norm(probe)
    probe_value, probe_g = objective_z(probe, 'controls')
    actual_u, actual_v, actual_d = raw_field(probe)
    actual, _, probe_force = measure(actual_u, actual_v, 'controls')
    expected_u, expected_v = physical(probe)
    assert float(torch.max(torch.abs(torch.stack((actual_u-expected_u, actual_v-expected_v))))) <= pc['field_abs_tolerance']
    assert abs(actual['E_el']-probe_value*scale) <= pc['energy_abs_tolerance']
    pulled = (basis.T @ torch.stack((probe_force[:len(x)], probe_force[len(x):]), 1) / scale).reshape(size)
    gradient_close(pulled, probe_g)
    assert_frozen()
    assert torch.equal(actual_d, d0)
    raw_field(zero)
    assert used['controls'] == 4  # original + zero + probe + actual probe.
    rho = (1-dg).square()
    assert bool(torch.all((dg >= 0) & (dg <= 1)))
    bulk, shear = mat.mat_lmbda + 2.*mat.mat_mu/3., mat.mat_mu
    last_z, last_value, last_gradient = zero.clone(), initial_value, initial_g.clone()
    previous_branches = None
    completed_directions = 0
    stop = 'initial_original_z_stationary'
    optimize_start = elapsed()
    try:
        if float(last_gradient.abs().max()) > pc['z_gradient_inf_threshold']:
            stop = 'max_outer_steps'
            for current_iteration in range(pc['max_outer_steps']):
                opt_check()
                # Deliberate independent same-point control, charged separately.
                checked_value, checked_g = objective_z(last_z, 'controls')
                assert abs(checked_value-last_value)*scale <= pc['energy_abs_tolerance']
                gradient_close(checked_g, last_gradient)
                opt_check()
                # Prepay the COMPLETE slot even if a later QR/check fails.
                charge('curvature', 'full_776_square_root_direction', pc['curvature_slot_units'])
                direction_probe = tensor(np.random.default_rng(pc['seed']+1000+current_iteration).normal(size=size))
                direction_probe /= torch.linalg.vector_norm(direction_probe)
                with torch.no_grad():
                    cu, cv = physical(last_z)
                    gu, gv = q4_gradient(cu, cells, B), q4_gradient(cv, cells, B)
                step, detail, R, rhs, branches = direction(
                    torch, basis, cells, B, weights, rho, gu, gv, scale, bulk, shear,
                    last_value, last_gradient, direction_probe, opt_check,
                    lambda vector: hvp(last_z, vector), log_control, capture_factor, pc)
                completed_directions += 1
                detail['stiffness_branch_changes'] = None if previous_branches is None else int((branches != previous_branches).sum())
                previous_branches = branches.clone()
                log_control(detail)
                del R, rhs, gu, gv
                slope = detail['slope']
                did_accept = False
                for backtrack in range(pc['max_backtracking_trials']):
                    opt_check()
                    alpha = 2.**(-backtrack)
                    candidate = last_z + alpha*step
                    value, gradient = objective_z(candidate, 'trials')
                    bound = last_value + pc['armijo_c1']*alpha*slope
                    did_accept = value <= bound
                    trial = dict(iteration=current_iteration, backtrack=backtrack, alpha=alpha,
                                 normalized_energy=value, armijo_bound=bound, accepted=did_accept,
                                 work_units=sum(used.values()), z_gradient_inf=float(gradient.abs().max()))
                    with (out / 'trials.jsonl').open('a') as stream:
                        stream.write(json.dumps(trial, allow_nan=False)+'\n')
                    if did_accept:
                        # Explicit acceptance happens BEFORE promotion. No callback
                        # evaluation and no promotion of a rejected/unconfirmed trial.
                        last_z, last_value, last_gradient = candidate.detach().clone(), value, gradient.clone()
                        accepted.append(dict(trial, z_gradient_l2=float(torch.linalg.vector_norm(gradient))))
                        save('accepted.json', accepted)
                        break
                if not did_accept:
                    raise RuntimeError('Armijo exhausted32 trials; terminal, no fallback')
                if float(last_gradient.abs().max()) <= pc['z_gradient_inf_threshold']:
                    stop = 'accepted_original_z_gradient_inf_le_1e-8'
                    break
                del step, candidate, gradient
    except StopBudget as reason:
        stop = str(reason)
    except Exception as error:
        stop = 'fatal_' + type(error).__name__ + ': ' + str(error)[:300]
        raise
    finally:
        timings['optimizer_seconds'] = elapsed()-optimize_start
        save('trace.json', trace)
        save('accepted.json', accepted)
        save('optimizer_terminal.json', dict(stop=stop, last_confirmed_energy=last_value,
             last_confirmed_z_gradient_inf=float(last_gradient.abs().max()),
             directions_completed=completed_directions, used=used.copy(),
             candidate_restore='last explicitly Armijo-confirmed point or original zero'))

    check_work()
    uh, vh, dh = raw_field(last_z)
    assert_frozen()
    assert torch.equal(dh, d0)
    head_metrics, rawh, head_force = measure(uh, vh, 'final')
    ub, vb = physical(last_z)
    basis_metrics, _, _ = measure(ub, vb, 'final')
    _, final_gz = objective_z(last_z, 'final')
    realization = abs(head_metrics['E_el']-basis_metrics['E_el'])
    realization_uv = float(torch.max(torch.abs(torch.stack((uh-ub, vh-vb)))))
    assert realization <= pc['energy_abs_tolerance'] and realization_uv <= pc['field_abs_tolerance']
    full_head_gradient = design.T @ torch.stack((head_force[:len(x)], head_force[len(x):]), 1) / scale
    actual_gz = (basis.T @ torch.stack((head_force[:len(x)], head_force[len(x):]), 1) / scale).reshape(size)
    final_z_gradient_error = gradient_close(actual_gz, final_gz)
    stationary = max(float(final_gz.abs().max()), float(actual_gz.abs().max())) <= pc['z_gradient_inf_threshold']
    uncertainty = max(frozen['numerical_energy_uncertainty'], initial_error, realization,
                      64*np.finfo(float).eps*scale)
    gap = baseline['E_el']-head_metrics['E_el']
    gain = gap/baseline['E_el']
    robust = gain >= contract['relative_gain_screen'] and gap > 10*uncertainty
    energy_verdict = ('optimization_witness' if robust else 'small_resolved_gain_below_screen' if gap > 10*uncertainty
                      else 'energy_regression' if -gap > 10*uncertainty else 'numerically_unresolved')
    work_ledger = dict(used=sum(used.values()), by_category=used.copy(),
                       caps={key: allowances[key] for key in used}, hvp_calls=hvp_calls,
                       actual_HVP_units=2*hvp_calls, complete_curvature_slots=used['curvature']//1552,
                       total_cap=25424, no_reallocation=True,
                       units_definition='Each complete curvature/TSQR/solve slot=1552 conservative proxy; E or E+gradient=1; HVP=2; no free construction/factor/refinement')
    metrics = dict(protocol=contract['protocol'], run_id=contract['run_id'],
         state='synthetic seen c1s4 conditional MCS outer9, U=.11999988; horizon0',
         original=original_metrics, saved_PBD=baseline, frozen_r2_head=frozen['head'], head=head_metrics,
         gain_over_saved_PBD=gain, gain_over_frozen_r2=(frozen['head']['E_el']-head_metrics['E_el'])/frozen['head']['E_el'],
         numerical_energy_uncertainty=uncertainty, initial_identity_energy_abs_error=initial_error,
         actual_basis_energy_difference=realization, actual_basis_displacement_maxabs=realization_uv,
         initial_z_gradient_inf=float(initial_g.abs().max()),
         retained_gradient_l2=float(torch.linalg.vector_norm(final_gz)), retained_gradient_inf=float(final_gz.abs().max()),
         actual_retained_gradient_l2=float(torch.linalg.vector_norm(actual_gz)),
         actual_retained_gradient_inf=float(actual_gz.abs().max()), final_z_gradient_maxabs_error=final_z_gradient_error,
         full_head_gradient_l2=float(torch.linalg.vector_norm(full_head_gradient)),
         full_head_gradient_inf=float(full_head_gradient.abs().max()), stationarity_screen=stationary,
         robust_directional_gain=robust, verdict='stationary' if stationary else 'nonstationary',
         energy_verdict=energy_verdict, stop=stop, work_ledger=work_ledger,
         history_commits=0, rollout_steps=0, hidden_updates=0, damage_updates=0, baseline_reevaluations=0,
         timings=timings, elapsed_before_serialization_seconds=elapsed(),
         max_gpu_reserved_bytes=torch.cuda.max_memory_reserved(),
         boundary='Fixed-space numerical stationarity diagnostic; energy improvement separate; no capacity/coupling/physical/teacher/generalization claim')
    save('summary.json', metrics)
    save('basis.json', frozen_basis)
    serialization_start = elapsed()
    check_work()
    np.savez_compressed(out / 'head.npz', uv_weight=field.net.output_layer.weight[:2].cpu().numpy(),
                        uv_bias=field.net.output_layer.bias[:2].cpu().numpy(), z=last_z.reshape(rank, 2).cpu().numpy(),
                        transform=transform_np)
    check_work()
    np.savez_compressed(out / 'fields.npz', nodes=data['nodes'], cells=data['cells'],
                        u=uh.cpu().numpy(), v=vh.cpu().numpy(), d=data['d_fem'], raw=rawh.cpu().numpy())
    check_work()
    make_figure(out, contract, data, uh.cpu().numpy(), vh.cpu().numpy(), metrics)
    timings['serialization_and_figure_seconds'] = elapsed()-serialization_start
    metrics['elapsed_after_serialization_seconds'] = elapsed()
    metrics['generated_bytes_before_final_summary'] = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    save('summary.json', metrics)
    check_work()
    return metrics


def make_figure(out, contract, data, u, v, metrics):
    """Exact candidate field and frozen scalar comparators; no target evaluation."""
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, grid = plt.subplots(2, 4, figsize=(16, 8), layout='constrained')
    for row, candidate, key, channel in ((0, u, 'u_fem', 'u'), (1, v, 'v_fem', 'v')):
        reference = data[key]
        low, high = min(reference.min(), candidate.min()), max(reference.max(), candidate.max())
        for ax, values, title in ((grid[row, 0], reference, 'Supplied FEM '+channel),
                                  (grid[row, 1], candidate, 'FN776 actual '+channel)):
            im = ax.scatter(data['nodes'][:, 0], data['nodes'][:, 1], c=values, s=.3, vmin=low, vmax=high, rasterized=True)
            ax.set(title=title, xlabel='native x', ylabel='native y', aspect='equal')
        fig.colorbar(im, ax=list(grid[row, :2]), label=channel+' native displacement')
        diff = candidate-reference
        bound = float(np.abs(diff).max()) or 1e-30
        im = grid[row, 2].scatter(data['nodes'][:, 0], data['nodes'][:, 1], c=diff, s=.3,
                                  cmap='coolwarm', vmin=-bound, vmax=bound, rasterized=True)
        grid[row, 2].set(title='FN776 minus FEM '+channel, xlabel='native x', ylabel='native y', aspect='equal')
        fig.colorbar(im, ax=grid[row, 2], label='signed '+channel+' difference')
    labels = ['PBD saved', 'r2 saved', 'FN776 actual']
    records = [metrics['saved_PBD'], metrics['frozen_r2_head'], metrics['head']]
    grid[0, 3].bar(labels, [r['E_el']/metrics['saved_PBD']['E_el'] for r in records])
    grid[0, 3].axhline(1-contract['relative_gain_screen'], color='r', linestyle='--', label='1-1e-4 screen')
    grid[0, 3].set(title='Elastic energy / saved PBD', ylabel='ratio', ylim=(0, None))
    grid[0, 3].legend(fontsize=7)
    points = json.loads((out / 'accepted.json').read_text())
    gradient_values = [metrics['initial_z_gradient_inf']] + [r['z_gradient_inf'] for r in points]
    grid[1, 3].semilogy(range(len(gradient_values)), [max(v, 1e-30) for v in gradient_values], label='basis original z')
    grid[1, 3].scatter([len(gradient_values)-1], [max(metrics['actual_retained_gradient_inf'], 1e-30)],
                       marker='x', color='red', label='actual network z')
    grid[1, 3].axhline(1e-8, color='red', linestyle='--', label='1e-8 stationarity')
    grid[1, 3].set(title='Original-z stationarity', xlabel='confirmed accepted updates', ylabel='gradient infinity norm')
    grid[1, 3].legend(fontsize=7)
    for ax in grid[:, 3]:
        ax.tick_params(axis='x', labelrotation=15, labelsize=8)
    fig.suptitle('Synthetic seen c1s4, horizon 0; '+contract['run_id'])
    fig.savefig(out / 'decision.png', dpi=160)
    plt.close(fig)
    (out / 'decision.md').write_text(
        '# FN776 c1s4 decision figure\n\nSource: '+contract['run_id']+
        '; exact same-run fields.npz and summary.json, frozen r2 summary scalar comparators.\n\n'
        'All nodes at fixed c1s4; u and v each share a candidate/reference scale. '
        'Signed differences use a symmetric channel scale; native nondimensional units. '
        'PBD/r2 field endpoints are not reread or reevaluated; their saved scalars appear at right. '
        'Energy bars start at zero and show the prospective 1e-4 screen; uncertainty and exact scalars '
        'are in summary.json. Single synthetic seen state, no independent-unit variation.\n\n'
        f"Actual PBD gain={metrics['gain_over_saved_PBD']:.12g}; verdict={metrics['verdict']}; "
        f"original-z stationary={metrics['stationarity_screen']}.\n\n"
        'What this figure means: inspect the lower-right original-z curve and actual-network marker against1e-8; then compare candidate energy with saved PBD; '
        'stationarity and the sign/resolution of energy gain are reported separately. '
        'Field/residual costs do not vote or rescue a primary miss. '
        'It cannot establish an optimum, capacity limit, coupled evolution or a physical teacher.\n')
    (out / 'README_analysis.md').write_text(
        '# FN776 fixed-d UV head\n\nQuestion: can one paid, full square-root Newton solve reach '
        'the original-z stationarity threshold inside the shared budget?\n\n'
        'Read the original-z stationarity panel first, then energy, full u/v maps and signed differences. The source is the exact candidate readout and frozen r2 scalar summary. '
        'The primary numerical question is original-z stationarity; saved-PBD energy improvement is separate. No baseline was reoptimized or reevaluated. An unresolved original-z gradient '
        'prevents an optimum/capacity conclusion even when energy improves. '
        'This single synthetic state supplies no physical/teacher/forecast/generalisation evidence. '
        'A valid negative preserves component improvements and the unclosed solver question.\n')
