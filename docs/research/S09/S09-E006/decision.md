# S09-E006 decision

## Verdict

**The frozen joint feasibility criterion passed.**  Among the two predeclared
balanced arms, `balanced_beta_0p25` passed both necessary clauses and is the
selected development configuration.  `balanced_beta_1p0` failed the
displacement guard despite a larger residual reduction.

| Final metric | data only | beta=0.25 | beta=1.0 |
|---|---:|---:|---:|
| aggregate displacement `R` | 0.362862 | 0.388727 | 0.448671 |
| mean residual / affine | 25.4582 | 10.1019 | 3.2080 |
| mean residual / data only | 1.0000 | **0.3968** | **0.1260** |
| worst state displacement / data only | 1.0000 | **1.0969** | 1.3770 |
| residual clause | comparator | PASS | PASS |
| displacement clause | comparator | **PASS** | FAIL |
| joint feasibility | comparator | **PASS** | FAIL |

The exact data-only replay reproduced aggregate `R` exactly and all six
per-state displacement/residual values within their frozen elementwise
tolerances.  All arms started from identical model and optimizer hashes and
completed exactly 700 updates.

## What changed scientifically

E004 showed that a fixed scalar physics weight substantially reduced residual
but made displacement fitting much worse.  E005 then measured 10^4–10^5 raw
gradient-scale imbalance at the common checkpoint.  E006 intervened on that
measured bottleneck: it normalised the physics component relative to the data
gradient and projected opposing components before a single AdamW step.

The `beta=0.25` result demonstrates a feasible bounded trade-off under the
predeclared development rule: about 60.3% mean residual reduction with every
state remaining within 10% of its data-only displacement error.  Stronger
`beta=1.0` pressure produced about 87.4% residual reduction but exceeded the
accuracy guard at all three states.  This directly supports using explicit
multi-objective control rather than interpreting one arbitrary scalar loss as
a complete objective.

## Boundaries and next gate

The selected arm is not Pareto-dominant: its displacement error is higher than
data-only, and its residual remains about 10.10 times affine.  The three states
are reused development cases, and only one seed was run.  Therefore the result
does not establish exact equilibrium, fracture evolution, prediction,
independent generalisation or road validity.

After independent Evidence Ready review, the smallest next experiment is a
fresh fixed-damage holdout test of the frozen `beta=0.25` method.  Damage-state
evolution PINO should remain blocked until that holdout result is acceptable
and the required old-state/history semantics are available.
