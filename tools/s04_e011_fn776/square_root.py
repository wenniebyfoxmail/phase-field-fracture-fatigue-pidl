"""Full-coordinate branch square-root Newton. Import performs no numeric work.

Torch is passed by the approved worker; no runtime dependencies import here.
All QR/Gram/solve/diagnostic/refinement work belongs to one prepaid 1552-unit
curvature slot. Nothing in this module is executed during static preparation.
"""


def direction(torch, basis, cells, B, weights, rho, gu, gv, scale, bulk, shear,
              value, gradient, probe, opt_check, hvp, log, capture, config):
    n = config['z_dimension']
    rank = config['rank']
    assert n == 776 and rank == 388 and basis.shape[1] == rank
    gp_count = weights.numel()
    bins = {}
    zero_correction = torch.zeros_like(gradient)
    signs = (gu[:, :, 0] + gv[:, :, 1]).reshape(-1) < 0
    zero_count = 0

    def qr(matrix):
        opt_check()
        # [A,e] is transformed together. The final column is NEVER pivoted.
        return torch.linalg.qr(matrix, mode='r').R

    def push(root):
        level = 0
        while level in bins:
            root = qr(torch.cat((bins.pop(level), root), dim=0))
            level += 1
        bins[level] = root

    with torch.no_grad():
        for start in range(0, gp_count, config['gp_chunk']):
            opt_check()
            indices = torch.arange(start, min(start + config['gp_chunk'], gp_count),
                                   device=basis.device)
            element, gp = indices // 4, indices % 4
            derivatives = torch.einsum('bjn,bnr->bjr', B[element, gp], basis[cells[element]])
            dx, dy = derivatives[:, 0], derivatives[:, 1]
            w, r = weights.reshape(-1)[indices], rho.reshape(-1)[indices]
            e11, e22 = gu[element, gp, 0], gv[element, gp, 1]
            trace = e11 + e22
            gamma = gu[element, gp, 1] + gv[element, gp, 0]
            # At EXACT zero choose compression tangent, not a smoothed branch.
            c = torch.where(trace > 0, r, torch.ones_like(r))
            sd = torch.sqrt(w * r * shear / scale)
            st = torch.sqrt(w * (r * shear / 3. + bulk * c) / scale)
            aug = basis.new_zeros((len(indices), 3, n + 1))
            aug[:, 0, :n:2], aug[:, 0, 1:n:2] = sd[:, None] * dx, -sd[:, None] * dy
            aug[:, 1, :n:2], aug[:, 1, 1:n:2] = st[:, None] * dx, st[:, None] * dy
            aug[:, 2, :n:2], aug[:, 2, 1:n:2] = sd[:, None] * dy, sd[:, None] * dx
            aug[:, 0, n] = sd * (e11 - e22)
            aug[:, 1, n] = st * trace
            aug[:, 2, n] = sd * gamma
            zero = trace == 0
            zero_count += int(zero.sum())
            if bool(zero.any()):
                trace_row = torch.stack((dx[zero], dy[zero]), dim=-1).reshape(-1, n)
                zero_correction += trace_row.T @ (
                    w[zero] * bulk / scale * (trace_row @ probe))
            push(qr(aug.reshape(-1, n + 1)))
            del aug, derivatives, dx, dy
        root = None
        # Highest bin is the oldest prefix; lower bins are later suffixes.
        for level in sorted(bins, reverse=True):
            root = bins[level] if root is None else qr(torch.cat((root, bins[level]), dim=0))
        assert root is not None and root.shape == (n + 1, n + 1)
        R, rhs = root[:n, :n].contiguous(), root[:n, n].contiguous()
        capture(R, rhs)  # Persist observables before finite/rank assertions.
        assert bool(torch.isfinite(root).all())
        # Local blocks may be rank deficient. Only the GLOBAL root is checked.
        assert bool(torch.all(R.diagonal() != 0)), 'global square-root factor zero diagonal'
        col_norm = torch.linalg.vector_norm(R, dim=0)
        assert bool(torch.isfinite(col_norm).all() and torch.all(col_norm > 0))
        W = R / col_norm[None, :]
        operator = lambda v: R.T @ (R @ v)
        analytic_gradient = R.T @ rhs
        analytic_value = float(.5 * root[:, n].square().sum())
        gradient_error = float((analytic_gradient - gradient).abs().max())
        gradient_tolerance = config['derivative_abs_tolerance'] + config['derivative_relative_tolerance'] * max(
            float(analytic_gradient.abs().max()), float(gradient.abs().max()))
        record = dict(stage='factor_controls', exact_zero_trace_count=zero_count,
                      negative_trace_count=int(signs.sum()), gp_count=gp_count,
                      raw_energy_abs_error=abs(analytic_value-value)*scale,
                      analytic_gradient_maxabs_error=gradient_error,
                      analytic_gradient_tolerance=gradient_tolerance,
                      min_abs_R_diagonal=float(R.diagonal().abs().min()))
        log(record)
        assert record['raw_energy_abs_error'] <= config['energy_abs_tolerance'], 'square-root energy mismatch'
        assert gradient_error <= gradient_tolerance, 'square-root gradient mismatch'

    opt_check()
    hp = hvp(probe)  # Paid independent original-function AD, at the SAME z.
    with torch.no_grad():
        predicted = operator(probe)
        expected = hp + zero_correction
        hp_error = float((predicted-expected).abs().max())
        hp_tolerance = config['derivative_abs_tolerance'] + config['derivative_relative_tolerance'] * max(
            float(predicted.abs().max()), float(expected.abs().max()))
        log(dict(stage='hvp_control', maxabs_error=hp_error, tolerance=hp_tolerance,
                 exact_zero_correction_inf=float(zero_correction.abs().max())))
        assert hp_error <= hp_tolerance, 'square-root/AD tangent mismatch after exact-zero correction'
        opt_check()
        H = R.T @ R  # Small diagnostic only; NEVER used to factor the direction.
        norm_H = float(torch.linalg.matrix_norm(H, ord=float('inf')))
        symmetry = float(torch.linalg.vector_norm(H-H.T) /
                         torch.linalg.vector_norm(H).clamp_min(torch.finfo(H.dtype).tiny))
        assert symmetry <= config['symmetry_scaled_tolerance']
        eig_raw = torch.linalg.eigvalsh(H)
        opt_check()
        eig_scaled = torch.linalg.eigvalsh(W.T @ W)
        # Gram-eigenvalue rounding can hide a small mode. Report unknown rather
        # than cut/rethreshold directions or use eigenvectors in the solve.
        def spectrum(values):
            low, high = float(values[0]), float(values[-1])
            return dict(gram_lambda_min=low, gram_lambda_max=high,
                        R_condition_estimate=(high/low)**.5 if low > 0 else None,
                        note='Gram-spectrum diagnostic; no rank truncation; rounding may obscure small modes')
        def triangular(matrix, target, upper):
            opt_check()
            return torch.linalg.solve_triangular(matrix, target[:, None], upper=upper).reshape(n)
        step = triangular(W, -rhs, True) / col_norm
        refinements = 0
        residuals = []
        while True:
            opt_check()
            residual = operator(step) + gradient
            norm_r = float(residual.abs().max())
            gradient_inf = float(gradient.abs().max())
            denominator = norm_H*float(step.abs().max()) + gradient_inf
            backward = norm_r / max(denominator, torch.finfo(H.dtype).tiny)
            residuals.append(dict(inf=norm_r, relative_to_gradient=norm_r/max(gradient_inf, torch.finfo(H.dtype).tiny),
                                  backward_error=backward))
            if (norm_r <= config['linear_relative_residual'] * gradient_inf and
                    backward <= config['linear_backward_tolerance']):
                break
            if refinements == config['max_linear_refinements']:
                log(dict(stage='linear_failure', residuals=residuals))
                raise RuntimeError('linear residual/refinement limit; no fallback')
            correction = triangular(W.T, -residual/col_norm, False)
            step += triangular(W, correction, True) / col_norm
            refinements += 1
        slope = float(gradient @ step)
        assert bool(torch.isfinite(step).all()) and slope < 0, 'non-descent Newton direction'
        info = dict(stage='direction_complete', zero_trace_count=zero_count,
                    negative_trace_count=int(signs.sum()), raw_spectrum=spectrum(eig_raw),
                    equilibrated_spectrum=spectrum(eig_scaled), symmetry_scaled_error=symmetry,
                    linear_residuals=residuals, refinements=refinements, slope=slope,
                    augmented_rhs='root[:776,776]; transformed jointly with A')
        log(info)
        return step, info, R, rhs, signs
