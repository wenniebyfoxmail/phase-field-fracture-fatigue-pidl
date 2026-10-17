# GPT Pro Planning Gate: Stage A3 Uncertainty-Aware Selection

## Adopted

- Use eight independently frozen, stratified-bootstrap field adapters.
- Compute weak systems per adapter; never select from an averaged field.
- Propagate target and library uncertainty through clipped inverse residual
  variance weights.
- Aggregate over adapters, weak windows, test functions, sections, and time
  blocks with separate low-noise and crack-tip support frequencies.
- Preserve crack-tip windows through quotas and a nonzero weight floor.
- Treat opened seeds as development only and predeclare confirmation seeds
  `67,79,101,131` before running them.

## Claim boundary

This is synthetic tooling development. It is not a real-road result, a neural
PIDL joint-training baseline, or causal mechanism evidence.
