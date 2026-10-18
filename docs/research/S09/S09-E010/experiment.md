---
storyline_id: S09
experiment_id: S09-E010
protocol_revision: v2-support-amplitude-balanced-three-arm-screen
status: design-ready-local-implementation-only
primary_storyline: S09
related_experiments: [S09-E008, S09-E009]
---

# Support- and amplitude-balanced damage objective for the Stage-0A operator

## One bounded question

On the same exposed 16-cycle synthetic development packet and under the same
500-update endpoint, does adding separately normalised active-support and
cycle-amplitude directions to the existing damage anchor improve
growth-versus-stagnant amplitude ranking relative to an exact E009 `A25`
replay, without materially losing the damage, equilibrium and judgement gains
already present in `A25`?

This is an adaptive development experiment. It tests the combined addition of
two supervised directions. It cannot attribute an effect separately to support
or amplitude, establish a general interaction with physics, qualify a holdout,
or support rollout, FEM-truth or real-road claims.

## Operator and physics boundary

The learned mapping is unchanged:

`G_theta: (d_s00(x), [H, alpha_bar, q_prev, f]_s00(x_gp), complete s00..s05 prescribed-displacement path, fixed mesh/material/boundary data)`
`-> (d_s04(x), [H, alpha_bar, q_prev, f]_s04(x_gp), u_s04(x))`.

It remains a discrete field-to-field state transition on one fixed native
mesh. The only equation residual is the unchanged native-Q4 AMOR mechanical
equilibrium residual on free displacement degrees of freedom at the predicted
peak state,

`L_P = mean_free(R_u(u_peak_pred, d_peak_pred)^2) / C_P`.

The residual differentiates through predicted displacement and damage. It does
not enforce damage stationarity, the fatigue-history evolution equation, or
the complete incremental variational inequality. The `beta=0.25` arm is
therefore a limited PINO development arm; the matched `beta=0` arm is its
non-physics control.

## Why this intervention is admissible

E009 completed validly but returned
`COMPONENT_SIGNAL_OR_MIXED_TRADEOFF`: `A25` improved growth MAE and
near-stagnant false growth while amplitude AUC stayed at 0.68 and median spatial
alignment stayed unresolved. A target-only diagnostic on the same packet found
that positive damage increments occupy 1.8796--3.4684% of weighted nodal area,
while 14/16 cycles place at least 97.7% of squared target energy in the top 1%
of nodes. This concentration motivates a support-aware objective. It does not
show that background nodes dominated the realised loss or parameter gradients.

The support threshold is frozen at `tau_s=1e-15` damage units. A read-only
sensitivity check found no mask change between strict positivity, `1e-15`, and
`1e-14`; the smallest positive saved increment is
`2.581268532253489e-14`. Thus the threshold separates the exact zero background
from all positive saved increments without selecting a favourable subset.

## Frozen data, state and budget

- Reuse the exact S09-E009 packet-manifest identity
  `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6`,
  cycle order, information set, architecture, float64 dtype, hard constraints,
  scales, evaluator and random/data-order policy.
- Construct the same original pre-E009 initial model once, then copy complete
  parameters and buffers to all arms. Each arm receives its own new empty AdamW
  state with the frozen E009 hyperparameters.
- Run 500 updates per arm, with a total cap of 1,500 optimiser updates. Evaluate
  at updates 0, 16, 64, 128, 256, 496 and 500; update 500 is the sole decision
  endpoint.
- Apply exactly one global L2 clip at norm 1.0 to each complete merged direction
  before one AdamW step. No per-objective clipping, checkpoint selection, seed
  sweep, weight sweep, extra arm or unused-budget transfer is allowed.
- Record wall time per arm because equal update counts need not have equal cost.

## Existing and added supervised quantities

For cycle `c` and node `i`, let `w_i` be the frozen nodal weight,
`t_i=d_peak_true,i-d_pre,i`, `p_i=d_peak_pred,i-d_pre,i`, and
`s_d=0.006896013386826084` damage units. The original terms remain unchanged:

- `L_D = l_d + l_dr`, projected full-field damage MSE plus raw damage-increment
  MSE;
- `L_U=l_u`;
- `L_H=l_h+l_hr`;
- `L_P`, the equilibrium residual above.

The added terms use the projected damage increment because the targeted
amplitude AUC, `G`, `F` and spatial score are evaluated from that same quantity:

`m_i = 1[t_i > tau_s]`, with `tau_s=1e-15`;

`L_S = sum_i w_i m_i ((p_i-t_i)/s_d)^2 / sum_i w_i m_i`;

`A(z) = sum_i w_i |z_i| / sum_i w_i`;

`L_A = ((A(p)-A(t))/s_d)^2`.

The mask and target amplitude are training targets only. They cannot become
model inputs, inference-time masks, output rescaling, prediction masking, case
selection, checkpoint selection or evaluation filtering. Full-field evaluation
remains unchanged. The legacy raw-increment term remains present, so the
projected additions do not remove supervision before the hard damage
projection.

All 16 frozen examples have non-empty support and positive target amplitude.
An empty support, zero target amplitude, non-finite denominator, packet drift or
shape mismatch is therefore `EXECUTION_INVALID`, rather than a silently skipped
example. A zero or near-zero finite gradient for an added term contributes a
declared zero direction and is logged.

## Multi-objective gradient rule

Let `a=g_D=grad(L_D)`, `n=||a||`, `epsilon=1e-12`, and let
`j in {S,A,U,H,P}`. For each auxiliary gradient:

`b_j = n*g_j/||g_j||` when `||g_j||>epsilon`, otherwise `b_j=0`;

`q_j = b_j - min(a^T b_j,0)/n^2 * a`.

The support and amplitude coefficients are frozen at `gamma_S=gamma_A=1.0`
with no schedule. The balanced direction is

`G_B(beta) = a + q_S + q_A + q_U + q_H + beta*q_P`.

This uses the unchanged full-field damage gradient as the primary anchor. Each
added direction is norm-matched to that anchor and has any first-order conflict
with it removed. The rule does not guarantee that support, amplitude,
displacement, history and physics improve simultaneously after AdamW; their
realised changes remain measured outcomes. If `||g_D||<=epsilon`, stop the
balanced arm as `METHOD_INAPPLICABLE` under the same anchor-stationary meaning
used in E009.

## Three arms and permitted comparisons

1. `A25_exact_e009_replay`: the exact E009 damage-anchor rule
   `a+q_U+q_H+0.25*q_P`, with no `L_S` or `L_A` contribution.
2. `B25_support_amplitude_beta0p25`: `G_B(0.25)`.
3. `B0_support_amplitude_beta0`: `G_B(0)`; `g_P` is evaluated and logged from
   the same state but contributes zero.

Interpret only:

- `B25` versus exact `A25`: effect of the combined support-and-amplitude
  intervention at fixed physics coefficient;
- `B25` versus `B0`: incremental effect of the existing equilibrium direction
  under the balanced anchor.

The design does not separately identify `L_S` and `L_A`; adding a fourth arm
after results are visible is prohibited.

## Exact-replay validity gate

The `A25` control must reproduce the frozen E009 A25 start identity, optimiser
policy, schedule and update-500 endpoint. For each finite continuous scalar
`G`, `F`, `L_judge`, `L_D`, `L_U`, `L_H`, `L_P`, the six atomic losses,
amplitude ratio, amplitude Pearson/Spearman, spatial median and pairwise-field
median, require

`abs(new-reference) <= 1e-12 + 1e-9*abs(reference)`.

Amplitude AUC value and win/tie/loss counts, NA statuses, cycle membership,
hard-constraint counts and projection counts must match exactly. Replay failure,
shared-identity failure, non-finite values, missing update-500 evidence or any
hard-constraint violation makes cross-arm performance `EXECUTION_INVALID`.

## Primary criterion and graded outcome hierarchy

The smallest decisive target is regime ranking. Define

`Delta_AUC = AUC_B25 - AUC_A25`.

The primary criterion is `Delta_AUC >= 0.08` at update 500. It must be evaluated
from the exact integer pair counts as
`(2*W_B25 + T_B25) - (2*W_A25 + T_A25) >= 4`, rather than by a direct
floating-point subtraction at the boundary. AUC is computed from
the same frozen 5 growth by 5 near-stagnant comparisons. Growth is the positive
label, predicted weighted-mean absolute damage increment is the score, and a
growth score above a stagnant score is a win; ties count one half. A difference
of 0.08 corresponds to two full pair-order improvements, or the equivalent four
half-pair changes. It is larger than one discrete pair and well below the
available 0.32 headroom from the E009 value 0.68 to the analytic ceiling 1.00.
It is a deterministic development effect threshold, not a
population-significance statement.

For a *balanced local repair*, the primary criterion must pass and all four
protected ratios against the contemporaneous exact `A25` control must hold:

- `G_B25/G_A25 <= 1.05`;
- `F_B25/F_A25 <= 1.05`;
- `L_P,B25/L_P,A25 <= 1.10`;
- `L_judge,B25/L_judge,A25 <= 1.05`.

These limits preserve the E009 component, equilibrium and aggregate judgement
behaviour while allowing a small development tolerance. They do not require
every secondary diagnostic to improve.

Choose the highest applicable state:

1. `EXECUTION_INVALID` or `METHOD_INAPPLICABLE` precedes performance.
2. `NO_TARGETED_RANKING_SIGNAL`: valid execution but
   `Delta_AUC < 0.08`.
3. `TARGETED_RANKING_SIGNAL_WITH_TRADEOFF`: `Delta_AUC >= 0.08`, but at least
   one protected ratio fails.
4. `BALANCED_LOCAL_REPAIR_SIGNAL`: primary and all four protected ratios pass.
5. `ORIGINAL_RELATIVE_REPAIR_SIGNAL`: in addition, the unchanged E009
   replay-relative clauses pass using the frozen E009 `R` reference:
   `Q_damage<=0.80`, both `G/R` and `F/R<=1.05`, `AUC>=0.80`,
   `L_P/R<=1.10`, and `L_judge/R<=1.05`.
6. `NOMINATE_CONFIRMATORY_P1`: all conditions of
   `ORIGINAL_RELATIVE_REPAIR_SIGNAL`, including the primary criterion and all
   four contemporaneous-`A25` protected ratios, and additionally
   `G_B25 <= 0.0005017354462152066 - (1e-12 + 1e-9*0.0005017354462152066)`.

Levels 5--6 may be evaluated only after the exact `A25` replay gate passes;
they do not retrospectively change E009. A level-2 result may still contain
useful component movements, which must be reported and used to choose repair,
but secondary metrics cannot rescue the primary ranking claim.

## Secondary diagnostic axes

- Report `B25/B0` changes in `L_P`, `G`, `F`, `L_judge`, `L_D/L_U/L_H` and
  amplitude AUC as the conditional physics effect; no one ratio is a second
  primary claim.
- Report median fixed-support spatial correlation, pairwise predicted-field
  correlation, amplitude ratio/Pearson/Spearman, all six atomic losses, all new
  losses and gradient geometry. Spatial improvement does not replace the AUC
  criterion.
- Preserve the E009 zero-denominator, AUC tie, fixed-support spatial NA and
  incomplete-execution rules. Any undefined primary AUC is invalid; undefined
  descriptive correlations remain JSON `null` with their frozen status.

## Deterministic implementation preflight before any optimiser run

The implementation candidate must, without an optimiser step:

1. reproduce the support-mask sensitivity receipt and all 16 non-empty masks;
2. match `L_S` and `L_A` to direct NumPy/Torch calculations on synthetic and
   frozen examples;
3. show finite values and gradients, the intended parameter reach, and the
   declared zero-gradient handling;
4. recover the exact legacy A25 direction when the two additions are disabled;
5. recover the same balanced direction in `B0/B25` except for the declared
   `0.25*q_P` contribution;
6. verify one global clip and no target-derived inference path;
7. exercise every threshold boundary and fail-closed receipt branch.

Only after exact-commit code review may a producer run card be prepared. This
protocol does not itself authorise training.

## Minimum evidence and visualization

- Complete per-arm train/gradient logs, update-500 checkpoints, termination
  receipts, environment and identity records, exact-replay predicate trace and
  per-cycle metrics.
- One decision table and figure generated from the exact scored outputs. The
  figure must show all 16 true and predicted cycle amplitudes for `A25`, `B25`
  and `B0`, label growth/near-stagnant/other cycles, display AUC and the four
  protected ratios, and retain common axes. No selected example may replace the
  all-cycle view.
- Report execution, retrieval, scientific verdict and research disposition as
  separate fields. Record the result in the S09 evidence record and existing
  Obsidian task note.

## Blocked conclusions

No outcome establishes separate causality for support versus amplitude,
gradient-background domination, architecture or state sufficiency,
cross-trajectory/cross-mesh generalisation, autonomous rollout, phase-field
damage-equation satisfaction, complete PINO validity, FEM truth or real-road
applicability.
