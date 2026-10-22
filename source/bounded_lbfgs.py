"""Small Armijo L-BFGS inner solver with explicit rollback and call budgets.

The callback returns (None, None) for an out-of-domain trial. Such calls count.
No epsilon, projection, history update, or objective replacement is performed.
Only accepted complete iterates are returned, including on a budget stop.
"""
import time
import torch


def minimize(evaluate, x0, *, max_calls, deadline, gradient_tolerance,
             memory=10, max_backtracks=20):
    if max_calls < 1 or gradient_tolerance <= 0:
        raise ValueError("invalid inner budget/tolerance")
    x = x0.detach().clone()
    calls, invalid, accepted = 0, 0, 0
    f, g = evaluate(x)
    calls += 1
    if f is None:
        raise ValueError("initial inner iterate outside objective domain")
    pairs = []
    trace = []
    reason = 'call_cap'
    while calls < max_calls:
        gi = float(g.abs().max())
        if gi <= gradient_tolerance:
            reason = 'gradient_tolerance'
            break
        if time.monotonic() >= deadline:
            reason = 'wall_cap'
            break
        q = g.clone()
        alphas = []
        for s, y, invys in reversed(pairs):
            a = invys * torch.dot(s, q)
            alphas.append(a)
            q = q - a * y
        scale = (torch.dot(pairs[-1][0], pairs[-1][1]) /
                 torch.dot(pairs[-1][1], pairs[-1][1])) if pairs else min(1., 1. / max(gi, 1.))
        r = scale * q
        for (s, y, invys), a in zip(pairs, reversed(alphas)):
            r = r + s * (a - invys * torch.dot(y, r))
        direction = -r
        slope = float(torch.dot(g, direction))
        if not torch.isfinite(direction).all() or not slope < 0:
            direction = -g / max(1., gi)
            slope = float(torch.dot(g, direction))
            pairs = []
        step, found = 1., False
        for _ in range(max_backtracks):
            if calls >= max_calls or time.monotonic() >= deadline:
                reason = 'call_cap' if calls >= max_calls else 'wall_cap'
                break
            trial = x + step * direction
            ft, gt = evaluate(trial)
            calls += 1
            if ft is None:
                invalid += 1
            elif ft <= f + 1e-4 * step * slope:
                s, y = trial - x, gt - g
                ys = torch.dot(y, s)
                if float(ys) > 1e-10 * float(y.norm()) * float(s.norm()) and float(ys) > 0:
                    pairs.append((s.detach(), y.detach(), (1. / ys).detach()))
                    pairs = pairs[-memory:]
                x, f, g = trial.detach(), ft, gt.detach()
                accepted += 1
                trace.append(dict(call=calls, loss=f, gradient_inf=float(g.abs().max()), step=step))
                found = True
                break
            step *= .5
        if not found:
            if calls < max_calls and time.monotonic() < deadline:
                reason = 'line_search_stalled'
            break
    return x, dict(calls=calls, invalid_trials=invalid, accepted_steps=accepted,
                   reason=reason, loss=f, gradient_inf=float(g.abs().max()), trace=trace)
