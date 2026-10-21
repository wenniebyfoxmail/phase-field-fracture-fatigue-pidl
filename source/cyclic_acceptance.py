"""Fresh nodal acceptance for an explicitly declared cyclic problem.

This checks physical nodal forces, not gradients in network parameter space.
No projection is applied to the candidate and no history is committed here.
The fatigue coefficient is rebuilt from immutable old history and detached
before differentiating energy, matching the FEM coefficient residual.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import hashlib
import torch

from compute_energy import compute_energy, get_psi_plus_per_elem
from fatigue_history import compute_fatigue_degrad, update_fatigue_history


@dataclass(frozen=True)
class AcceptancePolicy:
    mode: str
    joint_tol: float
    u_tol: float
    bounds_tol: float
    active_tol: float
    bc_tol: float
    history_atol: float
    history_rtol: float

    @classmethod
    def from_dict(cls, config):
        policy = cls(**config)
        if policy.mode not in {'nodal_box_kkt', 'soft_penalty_equations'}:
            raise ValueError('acceptance mode must be explicit nodal_box_kkt or soft_penalty_equations')
        for key, value in vars(policy).items():
            if key == 'mode':
                continue
            if not math.isfinite(value) or value < 0 or (key in {'joint_tol', 'u_tol'} and value == 0):
                raise ValueError(f'invalid acceptance tolerance {key}={value}')
        if policy.active_tol > policy.bounds_tol:
            raise ValueError('active_tol cannot exceed bounds_tol')
        return policy


def nodal_box_residual(d, gradient, lower, upper, active_tol):
    """Normal-cone residual; infeasible points must separately fail bounds."""
    result = gradient.clone()
    at_lower, at_upper = d <= lower + active_tol, d >= upper - active_tol
    result = torch.where(at_lower, torch.minimum(result, torch.zeros_like(result)), result)
    result = torch.where(at_upper, torch.maximum(result, torch.zeros_like(result)), result)
    # Close but distinct bounds still have a feasible direction. Keep the raw
    # force in this ambiguous tolerance band; only exact equality collapses it.
    result = torch.where(at_lower & at_upper, gradient, result)
    return torch.where(upper == lower, torch.zeros_like(result), result)


def _maximum(value):
    return float(value.max().detach().cpu()) if value.numel() else 0.0


def assess_nodal_residuals(*, u_force, v_force, d_force, damage, lower,
                           free_u, free_v, free_d, bc_error, policy):
    """Shared transparent policy, also testable without a FEM/NN solve."""
    if not isinstance(policy, AcceptancePolicy):
        policy = AcceptancePolicy.from_dict(policy)
    if not all(torch.isfinite(x).all() for x in (u_force, v_force, d_force, damage, lower)):
        return {'accepted': False, 'reason': 'nonfinite_nodal_state_or_force'}
    if not math.isfinite(float(bc_error)):
        return {'accepted': False, 'reason': 'nonfinite_boundary_error'}
    if torch.any(lower > 1.0) or torch.any(lower < 0.0):
        return {'accepted': False, 'reason': 'empty_damage_interval'}
    lower_violation = _maximum(torch.relu(lower - damage))
    upper_violation = _maximum(torch.relu(damage - 1.0))
    physical_lower_violation = _maximum(torch.relu(-damage))
    ru = float(torch.linalg.vector_norm(torch.cat((u_force[free_u], v_force[free_v]))).detach().cpu())
    raw = float(torch.linalg.vector_norm(d_force[free_d]).detach().cpu())
    projected = nodal_box_residual(damage, d_force, lower, torch.ones_like(damage), policy.active_tol)
    kkt = float(torch.linalg.vector_norm(projected[free_d]).detach().cpu())
    rd = kkt if policy.mode == 'nodal_box_kkt' else raw
    score = max((ru + rd) / policy.joint_tol, ru / policy.u_tol)
    # Accepted damage is the next step's lower bound. Tiny values outside
    # [0,1] cannot be committed; no clipping is hidden in this audit.
    feasible = lower_violation <= policy.bounds_tol and upper_violation == 0.0 and physical_lower_violation == 0.0
    bc_ok = float(bc_error) <= policy.bc_tol
    return {
        'accepted': bool(feasible and bc_ok and score <= 1.0),
        'mode': policy.mode, 'u_residual_l2': ru, 'phase_raw_l2': raw,
        'phase_box_kkt_l2': kkt, 'selected_phase_l2': rd, 'joint_score': score,
        'lower_violation_inf': lower_violation, 'upper_violation_inf': upper_violation,
        'negative_damage_inf': physical_lower_violation,
        'bc_error_inf': float(bc_error), 'feasible': bool(feasible), 'bc_pass': bool(bc_ok),
    }


def make_final_residual_check(inp, T_conn, area_T, matprop, pffmodel, *,
                              free_u_mask, free_v_mask, free_d_mask,
                              prescribed_u, prescribed_v, prescribed_d, config, fatigue_dict,
                              irreversibility_penalty_cfg):
    """Build a fresh callback; prescribed fields may depend on state/load."""
    policy = AcceptancePolicy.from_dict(config)
    arity = int(T_conn.shape[1])
    storage = fatigue_dict.get('history_storage')
    if (arity, storage) not in {(4, 'q4_gp4'), (3, 'tri3_gp3')}:
        raise ValueError('fresh acceptance requires native Q4/GP4 or T3/GP3 history')
    if fatigue_dict.get('accum_type') != 'carrara' or fatigue_dict.get('loading_type') != 'cyclic':
        raise ValueError('fresh acceptance currently supports declared Carrara cyclic history only')
    if pffmodel.se_split != 'volumetric' or pffmodel.PFF_model != 'AT1':
        raise ValueError('S04-E036 acceptance is limited to AT1/Amor')
    geometry = inp.detach().to(dtype=torch.float64)
    area = area_T.detach().to(dtype=torch.float64)
    conn = T_conn.detach()
    n = geometry.shape[0]
    masks = [torch.as_tensor(m, dtype=torch.bool, device=geometry.device) for m in
             (free_u_mask, free_v_mask, free_d_mask)]
    if any(m.shape != (n,) for m in masks):
        raise ValueError('free masks must cover every nodal component')
    fu, fv, fd = masks

    def callback(state):
        token = state['state_token']
        leaf = [state[key].detach().reshape(-1).to(dtype=torch.float64).clone().requires_grad_(True)
                for key in ('u', 'v', 'd')]
        u, v, d = leaf
        oldd = state['old_damage'].detach().reshape(-1).to(dtype=torch.float64)
        if any(x.shape != (n,) for x in (*leaf, oldd)):
            raise ValueError('candidate/old damage must use the common nodal order')
        oldA = state['old_history'].detach().to(dtype=torch.float64)
        oldr = state['old_active_driver'].detach().to(dtype=torch.float64)
        expected_shape = (conn.shape[0], arity)
        if oldA.shape != expected_shape or oldr.shape != expected_shape:
            raise ValueError('old histories must use full native GP support')
        with torch.enable_grad():
            active = get_psi_plus_per_elem(
                geometry, u, v, d, matprop, pffmodel, area, conn,
                history_driver_reduction_dict=fatigue_dict.get('history_driver_reduction'),
            ).detach()
            A = update_fatigue_history(oldA, active, oldr, fatigue_dict)
            f = compute_fatigue_degrad(A, fatigue_dict).detach()
            parts = compute_energy(
                geometry, u, v, d, oldd, matprop, pffmodel, area, conn,
                f_fatigue=f, irreversibility_penalty_cfg=irreversibility_penalty_cfg,
            )
            force = torch.autograd.grad(sum(parts), leaf, create_graph=False)
        target_u = prescribed_u(state) if callable(prescribed_u) else prescribed_u
        target_v = prescribed_v(state) if callable(prescribed_v) else prescribed_v
        target_d = prescribed_d(state) if callable(prescribed_d) else prescribed_d
        target_u = torch.as_tensor(target_u, dtype=torch.float64, device=u.device).expand_as(u)
        target_v = torch.as_tensor(target_v, dtype=torch.float64, device=v.device).expand_as(v)
        target_d = torch.as_tensor(target_d, dtype=torch.float64, device=d.device).expand_as(d)
        bc_error = max(_maximum(abs(u[~fu] - target_u[~fu])), _maximum(abs(v[~fv] - target_v[~fv])),
                       _maximum(abs(d[~fd] - target_d[~fd])))
        metrics = assess_nodal_residuals(
            u_force=force[0], v_force=force[1], d_force=force[2], damage=d,
            lower=oldd, free_u=fu, free_v=fv, free_d=fd, bc_error=bc_error, policy=policy,
        )
        consistent = True
        for name, fresh in [('trial_history', A), ('active_driver', active), ('f_commit', f)]:
            supplied = state[name].detach().to(dtype=torch.float64)
            if supplied.shape != fresh.shape:
                raise ValueError(f'{name} native support mismatch')
            metrics[f'{name}_fresh_maxdelta'] = _maximum(abs(fresh - supplied))
            consistent &= bool(torch.allclose(fresh, supplied, atol=policy.history_atol,
                                             rtol=policy.history_rtol))
        fsolve = state['f_solve'].detach().to(dtype=torch.float64)
        if fsolve.shape != f.shape:
            raise ValueError('f_solve native support mismatch')
        metrics['f_solve_to_fresh_commit_maxdelta'] = _maximum(abs(f - fsolve))
        metrics['fresh_history_consistent'] = consistent
        metrics['energy_parts_fixed_f'] = [float(e.detach().cpu()) for e in parts]
        accepted = bool(metrics.pop('accepted') and consistent)
        return {'accepted': accepted, 'fresh_current_state': True,
                'state_token': token, 'metrics': metrics}
    return callback


def ordered_mesh_digest(inp, conn):
    """Portable fingerprint of solver-visible ordered XY and connectivity."""
    xy = inp.detach().cpu().numpy().astype('<f4', copy=False)
    cells = conn.detach().cpu().numpy().astype('<i8', copy=False)
    return hashlib.sha256(xy.tobytes(order='C') + cells.tobytes(order='C')).hexdigest()


def common_damage_mask(inp, conn, config):
    if config['ordered_mesh_sha256_f32_i64'] != ordered_mesh_digest(inp, conn):
        raise ValueError('common problem ordered mesh digest mismatch')
    indices = config['fixed_damage_nodes_zero_based']
    if not indices or any(type(i) is not int or i < 0 or i >= len(inp) for i in indices):
        raise ValueError('explicit fixed damage nodes must be nonempty valid integers')
    if len(set(indices)) != len(indices):
        raise ValueError('duplicate fixed damage nodes')
    mask = torch.zeros(len(inp), dtype=torch.bool, device=inp.device)
    mask[indices] = True
    if config['fixed_damage_value'] != 1.0:
        raise ValueError('canonical SENT precrack requires prescribed d=1')
    return mask


def install_sent_common_problem(*, inp, T_conn, field_comp, matprop, pffmodel,
                                irreversibility_penalty_cfg, config, fatigue_dict):
    """Bind the audited FEM material and essential phase BC, opt-in only."""
    expected = (1., .3, 1., .01, 0., 421875., 13781.25)
    actual = (matprop.mat_E, matprop.mat_nu, matprop.w1, matprop.l0,
              pffmodel.residual_stiffness, matprop.w1 * pffmodel.irrPenalty(),
              irreversibility_penalty_cfg.get('recovery_penalty_coefficient', 0.))
    if any(not math.isclose(float(a), b, rel_tol=1e-12, abs_tol=1e-12) for a, b in zip(actual, expected)):
        raise ValueError(f'common MAT_CHAR mismatch: actual={actual}, required={expected}')
    if pffmodel.PFF_model != 'AT1' or pffmodel.se_split != 'volumetric':
        raise ValueError('common problem requires AT1/Amor')
    expected_fatigue = dict(alpha_T=.5, degrad_type='asymptotic', accum_type='carrara',
                            loading_type='cyclic', history_driver_mode='current_active')
    if any(fatigue_dict.get(k) != v for k, v in expected_fatigue.items()):
        raise ValueError('common problem requires uniform Carrara alpha_T=.5, asymptotic p=2')
    if (fatigue_dict.get('spatial_alpha_T') or {}).get('enable', False):
        raise ValueError('common problem forbids spatial alpha_T')
    mask = common_damage_mask(inp, T_conn, config)
    field_comp.set_fixed_damage_boundary(inp, mask, 1.0)


def make_sent_final_residual_check(*, inp, T_conn, area_T, matprop, pffmodel,
                                   field_comp, irreversibility_penalty_cfg,
                                   config, fatigue_dict):
    """SENT top/bottom clamp used by the verified benchmark; no hidden d clipping."""
    # Match boundaries from mesh extrema, not an inferred nearest coordinate.
    y = inp[:, 1]
    bottom, top = y == y.min(), y == y.max()
    if not bool(bottom.any() and top.any()) or bool((bottom & top).any()):
        raise ValueError('invalid SENT top/bottom boundary sets')
    clamped = bottom | top
    fixed_damage = common_damage_mask(inp, T_conn, fatigue_dict['common_problem'])
    def prescribed_v(state):
        if 'displacement' not in state or not math.isfinite(float(state['displacement'])):
            raise ValueError('fresh boundary check needs this substep displacement')
        return top.to(dtype=torch.float64) * float(state['displacement'])
    return make_final_residual_check(
        inp, T_conn, area_T, matprop, pffmodel,
        free_u_mask=~clamped, free_v_mask=~clamped,
        free_d_mask=~fixed_damage, prescribed_u=0.0, prescribed_d=1.0,
        prescribed_v=prescribed_v, config=config, fatigue_dict=fatigue_dict,
        irreversibility_penalty_cfg=irreversibility_penalty_cfg,
    )
