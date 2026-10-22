"""Native-Q4 physical readouts of saved fields, never a network-coordinate AD.

The geometry/shape gradients are precomputed in WindowProblem. Only independent
nodal leaves are differentiated for assembled internal force. Fatigue and old
damage are detached coefficients; no optimizer or history commit is present.
"""
from __future__ import annotations

import math
import torch

from compute_energy import raw_strain_energy_density, strain_energy_with_split
from fatigue_history import compute_fatigue_degrad, update_fatigue_history
from q4_quadrature import q4_gradient, q4_interpolate


def _number(value):
    return float(value.detach().cpu())


def weighted_error(value, reference, weights, scale):
    """GP-weighted scalar or vector error; vector components sum, never average."""
    if (not math.isfinite(scale) or scale <= 0 or value.shape != reference.shape
            or value.shape[:2] != weights.shape or value.ndim not in (2, 3)
            or not all(bool(torch.isfinite(x).all()) for x in (value, reference, weights))
            or bool(torch.any(weights <= 0))):
        raise ValueError('invalid native GP values, support, weights or physical scale')
    delta = value - reference
    squared = delta.square() if delta.ndim == 2 else delta.square().sum(-1)
    magnitude = delta.abs() if delta.ndim == 2 else torch.linalg.vector_norm(delta, dim=-1)
    rms = _number(torch.sqrt((weights * squared).sum() / weights.sum()))
    maximum = _number(magnitude.max())
    integral = (weights * delta).sum() if delta.ndim == 2 else (weights[..., None] * delta).sum((0, 1))
    return dict(absolute_rms=rms, normalized_rms=rms / scale,
                absolute_max=maximum, normalized_max=maximum / scale,
                signed_integral_difference=integral.detach().cpu().tolist(), scale=scale,
                weighting='native detJ; squared vector components summed before GP reduction')


def _gp_fields(problem, u, v, d):
    conn, shape, deriv = problem.cells, problem.native_shape, problem.native_dshape
    gu, gv, gd = [q4_gradient(value, conn, deriv) for value in (u, v, d)]
    dg = q4_interpolate(d, conn, shape)
    e11, e22, e12 = gu[..., 0], gv[..., 1], .5 * (gu[..., 1] + gv[..., 0])
    elastic, _ = strain_energy_with_split(e11, e22, e12, dg, problem.mat, problem.model)
    raw = raw_strain_energy_density(e11, e22, e12, problem.mat, problem.model)
    g, _ = problem.model.Edegrade(dg)
    return dict(damage=dg, grad_u=gu, grad_v=gv, grad_d=gd,
                raw=raw, active=g * raw, elastic_density=elastic)


def energy_and_reaction(problem, fields, old_damage, coefficient):
    """Energies and R=+dE/d(nodal displacement), unit out-of-plane thickness."""
    with torch.enable_grad():
        u, v, d = [fields[name].detach().to(problem.native_x).reshape(-1).clone().requires_grad_(True)
                   for name in ('u', 'v', 'd')]
        gp = _gp_fields(problem, u, v, d)
        weights = problem.native_weights
        f = coefficient.detach().to(weights)
        if f.shape != weights.shape:
            raise ValueError('fatigue coefficient must use complete native GP support')
        oldgp = q4_interpolate(old_damage.detach().to(d), problem.cells, problem.native_shape)
        damage_fn, _, cw = problem.model.damageFun(gp['damage'])
        fracture = f * problem.mat.w1 / cw * (damage_fn + problem.mat.l0**2 * gp['grad_d'].square().sum(-1))
        irreversibility = .5 * problem.mat.w1 * problem.model.irrPenalty() * torch.relu(oldgp - gp['damage']).square()
        recovery = .5 * problem.penalty['recovery_penalty_coefficient'] * torch.relu(-gp['damage']).square()
        densities = dict(elastic=gp['elastic_density'], fracture=fracture,
                         irreversibility=irreversibility, negative_damage_recovery=recovery)
        values = {name: (density * weights).sum() for name, density in densities.items()}
        total = sum(values.values())
        if not bool(torch.isfinite(total)):
            raise ValueError('nonfinite diagnostic energy')
        force_u, force_v = torch.autograd.grad(total, (u, v))
    y = problem.native_x[:, 1]
    top, bottom = y == y.max(), y == y.min()
    if not bool(top.any() and bottom.any()) or bool((top & bottom).any()):
        raise ValueError('invalid reaction boundary support')
    reactions = {name: [_number(force_u[mask].sum()), _number(force_v[mask].sum())]
                 for name, mask in (('top_xy', top), ('bottom_xy', bottom))}
    reactions['top_plus_bottom_xy'] = [a + b for a, b in zip(reactions['top_xy'], reactions['bottom_xy'])]
    free = ~(top | bottom)
    reactions['free_nodal_force_l2'] = _number(torch.linalg.vector_norm(torch.cat((force_u[free], force_v[free]))))
    reactions['all_nodes_force_sum_xy'] = [_number(force_u.sum()), _number(force_v.sum())]
    energies = {name: _number(value) for name, value in values.items()}
    energies['penalty_total'] = energies['irreversibility'] + energies['negative_damage_recovery']
    energies['total'] = _number(total)
    return dict(energy=energies, reaction=reactions)


def native_readout(problem, fields, old, f_solve, saved_history, saved_f_commit):
    """Fresh current-field trial history from an immutable committed predecessor."""
    if problem.model.PFF_model != 'AT1' or problem.model.se_split != 'volumetric':
        raise ValueError('diagnostics require the declared AT1/Amor problem')
    old = {name: value.detach().to(problem.native_x).clone() for name, value in old.items()}
    with torch.no_grad():
        gp = _gp_fields(problem, *(fields[name].detach().to(problem.native_x) for name in ('u', 'v', 'd')))
        A = update_fatigue_history(old['history'], gp['active'], old['active_driver'], problem.fatigue)
        f = compute_fatigue_degrad(A, problem.fatigue).detach()
        gp.update(history=A, f_commit=f, f_solve=f_solve.detach().to(A))
        gp = {name: value.detach() for name, value in gp.items() if name != 'elastic_density'}
    solve = energy_and_reaction(problem, fields, old['damage'], f_solve)
    commit = energy_and_reaction(problem, fields, old['damage'], f)
    summary = dict(f_solve=solve, fresh_f_commit=commit,
        native_gp_summary={name: dict(minimum=_number(value.min()), maximum=_number(value.max()),
            weighted_mean=_number((value * problem.native_weights).sum() / problem.native_weights.sum()))
            for name,value in gp.items() if value.ndim == 2},
        coefficient_timing='saved f_solve vs fresh trial f_commit; native float64 audits with fixed/detached coefficients; optimizer float32 casts are separately reported',
        history_timing='A_old + max(active(current final field)-active_old,0), rebuilt once from own old state; no commit',
        old_damage_timing='own predecessor damage; never replaced by target predecessor',
        energy_units='nondimensional benchmark energy, unit out-of-plane thickness; no network regularizer',
        reaction_convention='signed R=+dE/d(nodal displacement), imposed force on body, xy components, unit thickness; not 2E/U',
        saved_history_fresh_maxdelta=_number((saved_history.to(A) - A).abs().max()),
        f_solve_fresh_commit_maxdelta=_number((f_solve.to(f) - f).abs().max()),
        saved_f_commit_fresh_maxdelta=_number((saved_f_commit.to(f) - f).abs().max()))
    return dict(gp=gp, old=old, summary=summary)


def physical_gap(problem, candidate, reference):
    """Fixed physical scales; these are not reference-relative errors/noise floors."""
    weights = problem.native_weights
    height = _number(problem.native_x[:, 1].max() - problem.native_x[:, 1].min())
    if not math.isfinite(height) or height <= 0:
        raise ValueError('invalid domain-height gradient scale')
    scales = dict(raw=.5, active=.5, history=.5, f_commit=1., f_solve=1., damage=1.,
                  grad_u=.12 / height, grad_v=.12 / height, grad_d=1. / problem.mat.l0)
    gp_errors = {name: weighted_error(candidate['gp'][name], reference['gp'][name], weights, scale)
                 for name, scale in scales.items()}
    old_delta = {name: _number((candidate['old'][name] - reference['old'][name]).abs().max())
                 for name in ('damage', 'history', 'active_driver')}
    energies, reactions, reaction_errors = {}, {}, {}
    width = _number(problem.native_x[:, 0].max() - problem.native_x[:, 0].min())
    force_scale = float(problem.mat.mat_E) * (.12 / height) * width
    if not math.isfinite(force_scale) or force_scale <= 0:
        raise ValueError('invalid fixed characteristic force')
    for timing in ('f_solve', 'fresh_f_commit'):
        first, second = candidate['summary'][timing], reference['summary'][timing]
        energies[timing] = {name: first['energy'][name] - second['energy'][name] for name in first['energy']}
        reactions[timing] = {name: [a - b for a, b in zip(first['reaction'][name], second['reaction'][name])]
                             for name in ('top_xy', 'bottom_xy', 'top_plus_bottom_xy')}
        reaction_errors[timing] = {}
        for name, delta in reactions[timing].items():
            rms = math.sqrt(sum(value * value for value in delta) / 2.)
            reaction_errors[timing][name] = dict(signed_xy=delta, absolute_component_rms=rms,
                normalized_component_rms=rms / force_scale, force_scale=force_scale,
                scale_definition='E*(Umax/domain_height)*domain_width*unit_thickness; fixed scale, not relative error')
    return dict(native_gp_errors=gp_errors, candidate=candidate['summary'], reference=reference['summary'],
                energy_signed_difference=energies, reaction_signed_difference=reactions,
                reaction_errors=reaction_errors,
                old_state_maxdelta=old_delta, same_old_state_exact=all(value == 0. for value in old_delta.values()),
                same_old_damage_exact=old_delta['damage'] == 0.,
                domain_height=height, gp_weight_sum=_number(weights.sum()),
                gradient_scaling='displacement gradients divided by Umax/domain_height; damage gradient multiplied by ell',
                interpretation='Own-state comparison including propagated histories; fixed normalization is not relative error or a reference-error floor')
