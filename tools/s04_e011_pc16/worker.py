"""Approved producer only: frozen 388-column UV space, invertible PC16 metric.

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
    limits, pc = contract['budget'], contract['pc16']
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.set_per_process_memory_fraction(
        limits['gpu_reserved_bytes'] / torch.cuda.get_device_properties(0).total_memory)
    paths = {row['role']: Path(row['path']) for row in contract['files']}
    allowances = contract['work_ledger']
    used = dict(hvp=0, controls=0, optimization=0, final=0)
    hvp_calls = 0
    trace, accepted, timings = [], [], {}

    def save(name, value):
        (out / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

    def elapsed():
        return time.monotonic() - start

    def check_work():
        if elapsed() >= limits['work_seconds']:
            raise StopBudget('science_deadline_840s')
        if torch.cuda.max_memory_reserved() > limits['gpu_reserved_bytes']:
            raise RuntimeError('GPU reserved memory cap')

    def charge(phase, kind, cost):
        # Charged BEFORE work, including a failing/rejected call. No free setup,
        # callback, cached-HVP discount, pooled RHS or category reallocation.
        check_work()
        if phase == 'optimization' and elapsed() >= limits['opt_no_new_eval_seconds']:
            raise StopBudget('optimization_deadline_600s')
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
    rank, size, k = pc['rank'], pc['z_dimension'], pc['sketch_columns']
    assert size == rank * 2 == 776 and k == 16

    def physical(z):
        increment = basis @ z.reshape(rank, 2)
        return u0 + increment[:, 0], v0 + increment[:, 1]

    def objective_z(z, phase):
        charge(phase, 'z_energy_and_first_gradient', 1)
        zz = tensor(z).detach().clone().reshape(size).requires_grad_(True)
        value = elastic(*physical(zz))[0] / scale
        gradient = torch.autograd.grad(value, zz)[0]
        assert bool(torch.isfinite(gradient).all())
        return float(value.detach()), gradient.detach()

    def hvp(direction):
        nonlocal hvp_calls
        charge('hvp', 'one_initial_Hessian_direction', 2)
        hvp_calls += 1
        # Each HVP owns its forward + first derivative + directional second
        # derivative, charged together at 2. No additional uncharged evaluation.
        zz = torch.zeros(size, device=device, dtype=torch.float64, requires_grad=True)
        value = elastic(*physical(zz))[0] / scale
        gradient = torch.autograd.grad(value, zz, create_graph=True)[0]
        answer = torch.autograd.grad((gradient * direction).sum(), zz)[0].detach()
        assert bool(torch.isfinite(answer).all())
        return answer

    construction_start = elapsed()
    # CPU NumPy Generator explicitly defines the frozen seed/sketch sequence.
    rng = np.random.default_rng(pc['seed'])
    omega = tensor(rng.normal(size=(size, k)))
    Y = torch.stack([hvp(omega[:, j]) for j in range(k)], 1)
    check_work()
    factor_start = elapsed()
    Q, R = torch.linalg.qr(Y, mode='reduced')
    ident = torch.eye(k, device=device, dtype=torch.float64)
    # This detects numerical QR rank failure; it never drops a direction.
    rank_resolution = torch.finfo(torch.float64).eps * size * torch.linalg.vector_norm(Y)
    assert bool(torch.all(R.diagonal().abs() > rank_resolution)), 'QR rank failure'
    orth_error = float(torch.linalg.vector_norm(Q.T @ Q - ident) / torch.linalg.vector_norm(ident))
    assert orth_error <= pc['Q_orthogonality_scaled_tolerance']
    HQ = torch.stack([hvp(Q[:, j]) for j in range(k)], 1)
    check_work()
    S_raw = Q.T @ HQ
    tiny = torch.finfo(torch.float64).tiny
    symmetry_error = float(torch.linalg.vector_norm(S_raw-S_raw.T) /
                           torch.linalg.vector_norm(S_raw).clamp_min(tiny))
    assert symmetry_error <= pc['factor_scaled_tolerance'], 'projected Hessian asymmetry'
    S = .5 * (S_raw + S_raw.T)  # Only after unsymmetrized check.
    check_work()
    eigenvalues, eigenvectors = torch.linalg.eigh(S)
    assert bool(torch.isfinite(eigenvalues).all() and torch.all(eigenvalues > 0)), 'nonpositive curvature'
    inverse_root = (eigenvectors * eigenvalues.rsqrt()) @ eigenvectors.T
    square_root = (eigenvectors * eigenvalues.sqrt()) @ eigenvectors.T
    assert bool(torch.isfinite(inverse_root).all() and torch.isfinite(square_root).all())
    whitening_error = float(torch.linalg.vector_norm(inverse_root @ S @ inverse_root-ident) /
                            torch.linalg.vector_norm(ident))
    factor_inverse_error = float(torch.linalg.vector_norm(inverse_root @ square_root-ident) /
                                 torch.linalg.vector_norm(ident))
    assert max(whitening_error, factor_inverse_error) <= pc['factor_scaled_tolerance']
    timings['QR_and_projected_HVP_and_eigh_seconds'] = elapsed() - factor_start
    check_work()

    def apply_c(vector, inverse=False):
        small = square_root if inverse else inverse_root
        return vector + Q @ ((small - ident) @ (Q.T @ vector))

    # Exactly two additional, predetermined operator directions, no replacements.
    probes = tensor(np.random.default_rng(pc['seed'] + 1).normal(size=(size, 2)))
    probes = probes / torch.linalg.vector_norm(probes, dim=0)
    hp, hq = hvp(probes[:, 0]), hvp(probes[:, 1])
    left, right = float(probes[:, 0] @ hq), float(probes[:, 1] @ hp)
    ad_sym_error = abs(left-right)
    assert ad_sym_error <= pc['derivative_abs_tolerance'] + pc['derivative_relative_tolerance'] * max(abs(left), abs(right))
    curvatures = []
    inverse_errors = []
    for j, response in enumerate((hp, hq)):
        vector = probes[:, j]
        curvature = float(vector @ response)
        tolerance = pc['derivative_abs_tolerance'] + pc['derivative_relative_tolerance'] * float(torch.linalg.vector_norm(response))
        assert curvature >= -tolerance, 'material negative curvature'
        curvatures.append(curvature)
        inverse_errors.append(float(torch.linalg.vector_norm(apply_c(apply_c(vector), inverse=True)-vector)))
        inverse_errors.append(float(torch.linalg.vector_norm(apply_c(apply_c(vector, inverse=True))-vector)))
    # Full subspace and identity-complement action, without a 776x776 matrix.
    subspace_error = float(torch.linalg.vector_norm(apply_c(Q)-Q @ inverse_root) /
                           torch.linalg.vector_norm(Q))
    complement = probes[:, 0] - Q @ (Q.T @ probes[:, 0])
    complement_error = float(torch.linalg.vector_norm(apply_c(complement)-complement))
    assert max(inverse_errors + [subspace_error, complement_error]) <= pc['factor_scaled_tolerance']
    assert hvp_calls == allowances['hvp_calls'] == 34 and used['hvp'] == 68
    timings['construction_total_seconds'] = elapsed() - construction_start
    check_work()

    def objective_y(y, phase):
        charge(phase, 'y_energy_and_first_gradient', 1)
        yy = tensor(y).detach().clone().reshape(size).requires_grad_(True)
        zz = apply_c(yy)
        value = elastic(*physical(zz))[0] / scale
        # A single reverse traversal produces both original-z and transformed-y
        # first gradients. They belong to this one energy+gradient evaluation.
        gz, gy = torch.autograd.grad(value, (zz, yy))
        assert bool(torch.isfinite(gz).all() and torch.isfinite(gy).all())
        record = dict(work_units=sum(used.values()), phase=phase, normalized_energy=float(value.detach()),
                      z_gradient_l2=float(torch.linalg.vector_norm(gz)), z_gradient_inf=float(gz.abs().max()),
                      y_gradient_l2=float(torch.linalg.vector_norm(gy)), y_gradient_inf=float(gy.abs().max()))
        trace.append(record)
        return record, gz.detach(), gy.detach()

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

    zero = torch.zeros(size, device=device, dtype=torch.float64)
    probe = tensor(np.random.default_rng(pc['seed']).normal(size=size))
    probe *= pc['nonzero_probe_norm'] / torch.linalg.vector_norm(probe)
    controls = []
    for z in (zero, probe):
        y = apply_c(z, inverse=True)
        fz, gz = objective_z(z, 'controls')
        record, same_gz, gy = objective_y(y, 'controls')
        uz, vz = physical(z)
        uy, vy = physical(apply_c(y))
        displacement_error = float(torch.max(torch.abs(torch.stack((uz-uy, vz-vy)))))
        energy_error = abs(fz-record['normalized_energy']) * scale
        assert displacement_error <= pc['field_abs_tolerance'] and energy_error <= pc['energy_abs_tolerance']
        gz_error = gradient_close(same_gz, gz)
        chain_error = gradient_close(gy, apply_c(gz))
        if len(controls) == 0:
            assert abs(fz*scale-original_metrics['E_el']) <= pc['energy_abs_tolerance']
            initial_gz = gz.clone()
        else:
            actual_u, actual_v, actual_d = raw_field(z)
            actual, _, force = measure(actual_u, actual_v, 'controls')
            actual_uv_error = float(torch.max(torch.abs(torch.stack((actual_u-uz, actual_v-vz)))))
            assert actual_uv_error <= pc['field_abs_tolerance']
            assert abs(actual['E_el']-fz*scale) <= pc['energy_abs_tolerance']
            actual_gz = (basis.T @ torch.stack((force[:len(x)], force[len(x):]), 1) / scale).reshape(size)
            gradient_close(actual_gz, gz)
            assert_frozen()
            assert torch.equal(actual_d, d0)
            raw_field(zero)  # Restore ORIGINAL UV head before optimization.
        controls.append(dict(displacement_maxabs=displacement_error, energy_abs=energy_error,
                             z_gradient_maxabs_error=gz_error, chain_gradient_maxabs_error=chain_error))
    direction = tensor(np.random.default_rng(pc['seed']).normal(size=size))
    direction /= torch.linalg.vector_norm(direction)
    fd = []
    for step in (1e-5, 1e-6, 1e-7):
        plus, _ = objective_z(zero+step*direction, 'controls')
        minus, _ = objective_z(zero-step*direction, 'controls')
        fd.append(abs((plus-minus)/(2*step)-float(initial_gz @ direction)))
    assert min(fd) <= pc['derivative_abs_tolerance'] + pc['derivative_relative_tolerance'] * abs(float(initial_gz @ direction))
    assert used['controls'] == 12 and used['controls'] <= 16
    save('conditioning.json', dict(method='fixed initial-Hessian PC16, full 776-coordinate invertible map',
         rank=rank, z_dimension=size, sketch_columns=k, sketch_seed=pc['seed'], operator_probe_seed=pc['seed']+1,
         hvp_calls=hvp_calls, Q_orthogonality_scaled_error=orth_error, S_symmetry_scaled_error=symmetry_error,
         subspace_whitening_scaled_error=whitening_error, factor_inverse_scaled_error=factor_inverse_error,
         C_inverse_probe_errors=inverse_errors, C_subspace_error=subspace_error, C_complement_error=complement_error,
         AD_symmetry_abs_error=ad_sym_error, probe_curvatures=curvatures, projected_eigenvalues=eigenvalues.cpu().tolist(),
         coordinate_controls=controls, retained_FD_abs_errors=fd, timings=timings,
         physical_basis='exact frozen r2 transform; no SVD/rethresholding', baseline_reevaluations=0))

    last_y, last_z = np.zeros(size), np.zeros(size)
    last_value = original_metrics['E_el'] / scale
    last_gz_inf = float(initial_gz.abs().max())

    def objective(y):
        record, _, gy = objective_y(y, 'optimization')
        return record['normalized_energy'], gy.cpu().numpy()

    def callback(y):
        nonlocal last_y, last_z, last_value, last_gz_inf
        record, _, _ = objective_y(y, 'optimization')  # Counts callback separately.
        value = record['normalized_energy']
        assert value <= last_value + 1e-10 * max(1., abs(last_value))
        last_y = np.asarray(y).copy()
        last_z = apply_c(tensor(last_y)).cpu().numpy()
        last_value, last_gz_inf = value, record['z_gradient_inf']
        accepted.append(dict(work_units=sum(used.values()), normalized_energy=value,
                             z_gradient_inf=last_gz_inf, z_gradient_l2=record['z_gradient_l2']))
        if last_gz_inf <= pc['z_gradient_inf_threshold']:
            raise Stationary('accepted_original_z_gradient_inf_le_1e-8')

    optimize_start = elapsed()
    stop = 'initial_original_z_stationary'
    if last_gz_inf > pc['z_gradient_inf_threshold']:
        try:
            result = minimize(objective, last_y, jac=True, method='L-BFGS-B', callback=callback,
                              options=dict(maxfun=308, maxiter=308, maxls=pc['maxls'], maxcor=pc['maxcor'],
                                           ftol=pc['ftol'], gtol=pc['library_y_gtol']))
            stop = str(result.message)  # Never replace last callback endpoint with result.x.
        except (StopBudget, Stationary) as reason:
            stop = str(reason)
    timings['optimization_seconds'] = elapsed()-optimize_start
    save('trace.json', trace)
    save('accepted.json', accepted)

    # Only the last callback-confirmed accepted point, or original zero, survives.
    uh, vh, dh = raw_field(tensor(last_z))
    assert_frozen()
    assert torch.equal(dh, d0)
    head_metrics, rawh, head_force = measure(uh, vh, 'final')
    ub, vb = physical(tensor(last_z))
    basis_metrics, _, _ = measure(ub, vb, 'final')
    _, final_gz = objective_z(last_z, 'final')
    final_gy = apply_c(final_gz)
    realization = abs(head_metrics['E_el']-basis_metrics['E_el'])
    realization_uv = float(torch.max(torch.abs(torch.stack((uh-ub, vh-vb)))))
    assert realization <= pc['energy_abs_tolerance'] and realization_uv <= pc['field_abs_tolerance']
    full_head_gradient = design.T @ torch.stack((head_force[:len(x)], head_force[len(x):]), 1) / scale
    uncertainty = max(frozen['numerical_energy_uncertainty'], initial_error, realization,
                      64*np.finfo(float).eps*scale)
    gap = baseline['E_el']-head_metrics['E_el']
    gain = gap/baseline['E_el']
    robust = gain >= contract['relative_gain_screen'] and gap > 10*uncertainty
    verdict = ('optimization_witness' if robust else 'small_resolved_gain_below_screen' if gap > 10*uncertainty
               else 'energy_regression' if -gap > 10*uncertainty else 'numerically_unresolved')
    work_ledger = dict(used=sum(used.values()), by_category=used.copy(), caps={key: allowances[key] for key in used},
                       hvp_calls=hvp_calls, hvp_units=used['hvp'], total_cap=400,
                       units_definition='E or E+first-gradient=1; standalone-gradient=1; each HVP=2; no free setup')
    metrics = dict(protocol=contract['protocol'], run_id=contract['run_id'],
         state='synthetic seen c1s4 conditional MCS outer9, U=.11999988; horizon 0',
         original=original_metrics, saved_PBD=baseline, frozen_r2_head=frozen['head'], head=head_metrics,
         gain_over_saved_PBD=gain, gain_over_frozen_r2=(frozen['head']['E_el']-head_metrics['E_el'])/frozen['head']['E_el'],
         frozen_r2_retained_gradient_l2=frozen['retained_gradient_l2'],
         numerical_energy_uncertainty=uncertainty, initial_identity_energy_abs_error=initial_error,
         actual_basis_energy_difference=realization, actual_basis_displacement_maxabs=realization_uv,
         retained_gradient_l2=float(torch.linalg.vector_norm(final_gz)), retained_gradient_inf=float(final_gz.abs().max()),
         transformed_y_gradient_l2=float(torch.linalg.vector_norm(final_gy)), transformed_y_gradient_inf=float(final_gy.abs().max()),
         full_head_gradient_l2=float(torch.linalg.vector_norm(full_head_gradient)), full_head_gradient_inf=float(full_head_gradient.abs().max()),
         stationarity_screen=float(final_gz.abs().max()) <= pc['z_gradient_inf_threshold'],
         robust_directional_gain=robust, verdict=verdict, stop=stop, work_ledger=work_ledger,
         history_commits=0, rollout_steps=0, hidden_updates=0, damage_updates=0, baseline_reevaluations=0,
         timings=timings, elapsed_before_serialization_seconds=elapsed(),
         max_gpu_reserved_bytes=torch.cuda.max_memory_reserved(),
         boundary='Finite-budget same-space solver diagnostic; no capacity, coupling, teacher or physical validation')
    save('summary.json', metrics)
    save('basis.json', frozen_basis)
    serialization_start = elapsed()
    np.savez_compressed(out / 'head.npz', uv_weight=field.net.output_layer.weight[:2].cpu().numpy(),
                        uv_bias=field.net.output_layer.bias[:2].cpu().numpy(), z=last_z.reshape(rank, 2), y=last_y,
                        transform=transform_np)
    np.savez_compressed(out / 'pc16_factors.npz', Q=Q.cpu().numpy(), S=S.cpu().numpy(),
                        inverse_root=inverse_root.cpu().numpy(), square_root=square_root.cpu().numpy())
    np.savez_compressed(out / 'fields.npz', nodes=data['nodes'], cells=data['cells'],
                        u=uh.cpu().numpy(), v=vh.cpu().numpy(), d=data['d_fem'], raw=rawh.cpu().numpy())
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
    fig, grid = plt.subplots(2, 4, figsize=(14, 7), layout='constrained')
    for row, candidate, key, channel in ((0, u, 'u_fem', 'u'), (1, v, 'v_fem', 'v')):
        reference = data[key]
        low, high = min(reference.min(), candidate.min()), max(reference.max(), candidate.max())
        for ax, values, title in ((grid[row, 0], reference, 'Supplied FEM '+channel),
                                  (grid[row, 1], candidate, 'PC16 actual '+channel)):
            im = ax.scatter(data['nodes'][:, 0], data['nodes'][:, 1], c=values, s=.3, vmin=low, vmax=high, rasterized=True)
            ax.set(title=title, xlabel='native x', ylabel='native y', aspect='equal')
        fig.colorbar(im, ax=list(grid[row, :2]), label=channel+' native displacement')
        diff = candidate-reference
        bound = float(np.abs(diff).max()) or 1e-30
        im = grid[row, 2].scatter(data['nodes'][:, 0], data['nodes'][:, 1], c=diff, s=.3,
                                  cmap='coolwarm', vmin=-bound, vmax=bound, rasterized=True)
        grid[row, 2].set(title='PC16 minus FEM '+channel, xlabel='native x', ylabel='native y', aspect='equal')
        fig.colorbar(im, ax=grid[row, 2], label='signed '+channel+' difference')
    labels = ['PBD saved', 'r2 saved', 'PC16 actual']
    records = [metrics['saved_PBD'], metrics['frozen_r2_head'], metrics['head']]
    grid[0, 3].bar(labels, [r['E_el']/metrics['saved_PBD']['E_el'] for r in records])
    grid[0, 3].axhline(1-contract['relative_gain_screen'], color='r', linestyle='--', label='1-1e-4 screen')
    grid[0, 3].set(title='Same elastic energy / saved PBD', ylabel='ratio', ylim=(0, None))
    grid[0, 3].legend(fontsize=7)
    grid[1, 3].bar(labels, [r['free_u_l2'] for r in records])
    grid[1, 3].set(title='Free displacement residual', ylabel='native L2', ylim=(0, None))
    fig.suptitle('Synthetic seen c1s4, horizon 0; '+contract['run_id'])
    fig.savefig(out / 'decision.png', dpi=160)
    plt.close(fig)
    (out / 'decision.md').write_text(
        '# PC16 c1s4 decision figure\n\nSource: '+contract['run_id']+
        '; exact same-run fields.npz and summary.json, frozen r2 summary scalar comparators.\n\n'
        'All nodes at fixed c1s4; u and v each share a candidate/reference scale. '
        'Signed differences use a symmetric channel scale; native nondimensional units. '
        'PBD/r2 field endpoints are not reread or reevaluated; their saved scalars appear at right. '
        'Energy bars start at zero and show the prospective 1e-4 screen; uncertainty and exact scalars '
        'are in summary.json. Single synthetic seen state, no independent-unit variation.\n\n'
        f"Actual PBD gain={metrics['gain_over_saved_PBD']:.12g}; verdict={metrics['verdict']}; "
        f"original-z stationary={metrics['stationarity_screen']}.\n\n"
        'What this figure means: compare actual candidate energy with the saved PBD bar; '
        'the sign and resolution of the stored gain control the bounded witness. '
        'Field/residual costs do not vote or rescue a primary miss. '
        'It cannot establish an optimum, capacity limit, coupled evolution or a physical teacher.\n')
    (out / 'README_analysis.md').write_text(
        '# PC16 fixed-d UV head\n\nQuestion: can one paid, fixed PC16 coordinate map lower the '
        'same elastic energy below saved PBD inside the shared budget?\n\n'
        'Read the right energy panel first, then the full u/v maps and signed differences, then '
        'the residual bar. The source is the exact candidate readout and frozen r2 scalar summary. '
        'The primary is the declared resolved PBD gain; field metrics and z-gradient diagnose costs '
        'and closure. No baseline was reoptimized or reevaluated. An unresolved original-z gradient '
        'prevents an optimum/capacity conclusion even when energy improves. '
        'This single synthetic state supplies no physical/teacher/forecast/generalisation evidence. '
        'A valid negative preserves component improvements and the unclosed solver question.\n')
