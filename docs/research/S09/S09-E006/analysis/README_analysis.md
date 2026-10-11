# S09-E006 analysis figures

## Scientific question

Does either predeclared gradient-balanced arm reduce mean development
equilibrium residual by at least 50% while keeping every development state's
displacement-error increase within 10% of a concurrently reproduced data-only
trajectory?

## Evidence and reading order

Source: retrieved R002 `metrics.json`, `updates.csv`, `replay_checks.json` and
`receipt.json` from exact execution commit `ae01790c10c644657fe9a8aea2f1087505144959`.

Read `pareto_rescue_decision.png` left to right:

1. Panel A shows every state's displacement error relative to data-only and the
   1.10 per-state limit.
2. Panel B shows every state's force residual relative to data-only; black
   diamonds are arm means and the dashed line is the 0.50 mean limit.
3. Panel C places each arm against both clauses.  Only the lower-left shaded
   rectangle is jointly feasible.

The exact numerical authority is `decision_table.csv` and `summary.json` in
the local analysis folder.  The decision PNG SHA-256 is
`7e8ddb68abdbb8805d5c64463909b965e830aaa05ede7b1252cb21f2a40b7522`.

## Interpretation

The data-only replay passed all seven identity comparisons.  `beta=0.25`
reduced mean residual to 0.3968 of data-only while its worst per-state
displacement ratio was 1.0969, so both primary clauses passed.  `beta=1.0`
reduced residual farther, to 0.1260 of data-only, but its worst displacement
ratio was 1.3770 and therefore failed the accuracy clause.

The selected arm still has mean residual 10.10 times the affine reference; it
does not satisfy exact equilibrium.  Its aggregate displacement `R=0.38873`
is also worse than data-only `R=0.36286`, though within the predeclared
per-state guardrail.  The result is a bounded feasible trade-off on three
reused development states, not dominance over data-only.

During training, `beta=0.25` encountered 204/700 raw-gradient conflicts and 68
global clips; `beta=1.0` encountered 226/700 conflicts and 119 clips.  These
are trajectory diagnostics and do not vote on the primary criterion.

Allowed conclusion: one predeclared gradient-balanced arm achieved the frozen
development-set joint feasibility criterion for this fixed-damage operator.
Blocked conclusions include exact equilibrium, damage/fatigue evolution,
independent generalisation, superiority over other PINO methods and real-road
validity.
