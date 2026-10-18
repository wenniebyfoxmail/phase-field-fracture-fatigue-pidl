"""Independent E028 repair: admissible damage and a bounded active-field anchor.

E027 source and outputs are unchanged. No import-time IO or optimizer steps.
"""
import torch
import s04_e027 as legacy

PROTOCOL = 'S04-E028/v1-active-anchor-current-lower-20261018'
STEPS = 200
GRAD_FRACTION = .25


def validate_current_lower(problem):
    p = problem
    line = ((p.xy[:, 0] >= -.5-1e-12) & (p.xy[:, 0] <= 1e-12)
            & (p.xy[:, 1].abs() <= 1e-12))
    if not torch.equal(line, p.fixed_d) or int(line.sum()) != 251:
        raise ValueError('fixed damage must be the exact 251 current native precrack nodes')
    if not bool(((p.previous >= 0) & (p.previous <= 1)).all()):
        raise ValueError('current c20s3 lower outside unit box')
    if not bool((p.previous[line] == 1).all()) or not bool((p.ref[line, 2] == 1).all()):
        raise ValueError('current prescribed damage/lower mismatch')


def project_damage(candidate, lower, fixed):
    """In-forward nodal projection; lower is immutable c20s3, never target/U0."""
    legacy.finite(candidate, 'damage before projection')
    if candidate.shape != lower.shape or fixed.shape != lower.shape or fixed.dtype != torch.bool:
        raise ValueError('same-node damage/lower/fixed mask required')
    if not bool(((lower >= 0) & (lower <= 1)).all()) or not bool((lower[fixed] == 1).all()):
        raise ValueError('invalid physical lower')
    d = torch.clamp(candidate, min=lower, max=torch.ones_like(lower))
    return torch.where(fixed | (lower == 1), torch.ones_like(d), d)


def fields(model, problem):
    q = legacy.fields(model, problem.xy)
    return torch.cat((q[:, :2], project_damage(q[:, 2], problem.previous, problem.fixed_d)[:, None]), 1)


def active_loss(problem, q):
    """Same native GP4/Z support and denominator as the frozen error channel."""
    active = problem.parts(*q.unbind(1))[4]
    with torch.no_grad():
        ref = problem.parts(*problem.ref.unbind(1))[4]
    w, mask = problem.w[problem.gp_zone], problem.gp_zone
    denominator = (w*ref[mask].square()).sum()
    if not bool(torch.isfinite(denominator)) or denominator <= 1e-24*w.sum():
        raise ValueError('active denominator NA')
    return (w*(active[mask]-ref[mask]).square()).sum()/denominator


def vector_gradient(loss, params):
    grads = torch.autograd.grad(loss, params, retain_graph=True, allow_unused=True)
    return tuple(torch.zeros_like(p) if g is None else legacy.finite(g, 'component gradient') for p, g in zip(params, grads))


def capped_weight(base_norm, anchor_norm):
    """Detached per-update coefficient: anchor norm <= .25 supervision norm."""
    b, a = base_norm.detach(), anchor_norm.detach()
    legacy.finite(b, 'base norm');legacy.finite(a, 'anchor norm')
    if b < 0 or a < 0: raise ValueError('negative gradient norm')
    if a == 0: return a.new_zeros(())
    return torch.minimum(a.new_ones(()), GRAD_FRACTION*b/a)


def objective(problem, model, q, ids, repair):
    lu, ld = problem.supervised_components(q, ids)
    sup = lu+ld
    anchor = active_loss(problem, q)
    params = tuple(model.parameters())
    gs, ga = vector_gradient(sup, params), vector_gradient(anchor, params)
    ns = torch.sqrt(sum(x.square().sum() for x in gs))
    na = torch.sqrt(sum(x.square().sum() for x in ga))
    weight = capped_weight(ns, na) if repair else na.new_zeros(())
    dot = sum((x*y).sum() for x, y in zip(gs, ga))
    cosine = float((dot/(ns*na)).detach()) if ns > 0 and na > 0 else None
    log = dict(L_U=float(lu.detach()), L_D=float(ld.detach()), L_active=float(anchor.detach()),
        active_weight=float(weight), grad_supervision=float(ns.detach()), grad_active=float(na.detach()),
        weighted_active_grad=float((weight*na).detach()), gradient_cosine=cosine,
        mechanical_weight=0., controller='pre-Adam Euclidean parameter norm cap, not update-size guarantee')
    return legacy.finite(sup+weight*anchor, 'objective'), log


def component_scores(problem, q):
    scores = problem.score(q)
    with torch.no_grad():
        delta = q.detach()-problem.ref
        for name, mask in [('global', torch.ones_like(problem.zone)), ('zone', problem.zone)]:
            w = problem.mass[mask]
            for j, key in [(0, 'u'), (1, 'v')]:
                scores[f'{name}_{key}_RMS_Us'] = float(torch.sqrt((w*delta[mask,j].square()).sum()/w.sum())/legacy.US)
        dg = legacy.q4_interpolate(q.detach()[:,2],problem.conn,problem.N)
        scores['gp_healing'] = float(torch.relu(problem.old_gp-dg).max())
        scores['lower_violation'] = float(torch.relu(problem.previous-q.detach()[:,2]).max())
        scores['negative_violation'] = float(torch.relu(-q.detach()[:,2]).max())
    return scores


def representation_stats(model, problem):
    with torch.no_grad():
        raw_d = legacy.fields(model, problem.xy)[:, 2]
        variable = (~problem.fixed_d) & (problem.previous < 1)
        count = int(variable.sum())
        return dict(variable_free_nodes=count, variable_free_fraction=float(variable.double().mean()),
            below_lower_count=int(((raw_d < problem.previous) & variable).sum()),
            below_lower_fraction_of_variable=float((raw_d[variable] < problem.previous[variable]).double().mean()) if count else None,
            above_upper_fraction_of_variable=float((raw_d[variable] > 1).double().mean()) if count else None,
            note='legacy candidate before projection; saturated outside bounds has zero local damage gradient')


def check_physical(problem, q):
    legacy.finite(q, 'physical fields')
    d = q[:,2]
    if bool((d < problem.previous-1e-10).any()) or bool((d > 1+1e-10).any()):
        raise ValueError('physical lower/unit bound violated')
    if not bool((d[problem.fixed_d] == 1).all()):
        raise ValueError('precrack equality violated')
