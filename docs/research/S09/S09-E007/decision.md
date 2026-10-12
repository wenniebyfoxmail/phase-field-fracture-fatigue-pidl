# S09-E007 decision

## Verdict

**Positive under the frozen fixed-damage holdout criterion.** The frozen
`beta=0.25` candidate retained the required aggregate displacement/equilibrium
trade-off against the frozen data-only comparator on all 73 peak states of the
existing U0.125 trajectory.

| Primary metric | Frozen limit | Result | Clause |
|---|---:|---:|---|
| trajectory equilibrium ratio `Q_f` | <= 0.50 | **0.4423481004** | PASS |
| trajectory displacement ratio `Q_u` | <= 1.10 | **0.9498598441** | PASS |
| conjunction | both | **positive** | PASS |

Relative to data-only, the candidate reduced the aggregate displacement error
by about 5.01% and the mean affine-normalised equilibrium residual by about
55.77%. This is the first new cross-Umax holdout result after selecting
`beta=0.25`; no training or adaptation occurred on U0.125.

## Diagnostics that qualify the positive result

- Early/middle/late thirds had `Q_f = 0.56055 / 0.37943 / 0.31168` and
  `Q_u = 0.94062 / 0.89708 / 1.01067`. The early third would not satisfy the
  aggregate equilibrium threshold by itself, but thirds are diagnostics and do
  not vote under the frozen protocol.
- Cyclewise displacement ratio was above one for cycles 59--73; the worst was
  1.04864 at cycle 69. Thus the candidate does not improve displacement at
  every cycle even though its full-trajectory sum is lower.
- The mean candidate residual remains 19.3206 times the affine reference
  (data-only: 43.6775). The result is a relative improvement, not exact or even
  near-zero equilibrium.
- The U0.125 archive is post-selection and has
  `exposure_unknown_not_cleared`; this is not certified blind confirmation.

## Allowed conclusion

On one complete, non-blind, post-selection synthetic U0.125 trajectory, the
frozen operator

\[
\mathcal G_\theta:(d_{\mathrm{peak}}(\cdot),U_{\max})
\longmapsto u_{\mathrm{peak}}(\cdot)
\]

met the prespecified aggregate displacement/equilibrium criterion against the
frozen data-only comparator. This supports advancing to the separately frozen
S09-E008 Stage-0 transition design.

## Blocked conclusions and next gate

Damage is supplied from the same FEM state. The result does not establish
crack/fatigue evolution, autonomous forecasting, blind confirmation, exact
equilibrium, seed robustness, cross-mesh transfer, FEM truth or real-road
validity. It also does not establish cyclewise displacement dominance.

The next experiment should implement the causal transition candidate already
specified in `pino_stage0_next_gate.md`:

\[
(d_n,\bar\alpha_n,f_n,U_{n+1})\mapsto
(d_{n+1},\bar\alpha_{n+1},u_{n+1}),
\]

beginning with qualified old-state/history semantics and the smallest
multi-objective physics set. S09-E007 provides permission to design that gate;
it is not itself a damage-evolution PINO result.
