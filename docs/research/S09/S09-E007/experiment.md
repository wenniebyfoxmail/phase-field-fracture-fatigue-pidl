---
storyline_id: S09
experiment_id: S09-E007
protocol_revision: v2-frozen-beta025-u0125-holdout
status: design_ready
primary_storyline: S09
related_experiments: [S09-E004, S09-E005, S09-E006, S04-E016]
claim_class: C1
evidence_domain: synthetic
---

# Frozen beta=0.25 fixed-damage cross-Umax holdout

## One bounded question

After selecting `beta=0.25` on the three U0.12 development states in S09-E006,
does the frozen checkpoint retain the same useful displacement/residual trade-off
against the frozen data-only checkpoint on the complete existing U0.125 native-Q4
peak trajectory, with no fitting, state selection, early stopping, or threshold
change after the U0.125 scientific payload is opened?

This is a post-selection fixed-damage holdout. It is not a certified blind
confirmation: Request 31 recorded `exposure_unknown_not_cleared` for the existing
U0.125 archive because access logs were incomplete and top-level event metadata
were visible. The model and `beta=0.25` were nevertheless frozen before this
protocol reads any U0.125 field value. The selected checkpoint is evaluated
without further updates on one existing, post-selection U0.125 synthetic
trajectory. Any measured fixed-damage trade-off is conditional on this
trajectory and the declared exposure limitation; it is not certified
independent blind confirmation.

## Frozen operator and physics

The function-space map is unchanged:

\[
  \mathcal G_\theta:\bigl(d_{\mathrm{peak}}(\cdot),U_{\max}\bigr)
  \longmapsto u_{\mathrm{peak}}(\cdot).
\]

Damage is supplied, not advanced. Physics is the existing native-Q4 plane-strain
AMOR free-DOF mechanical-equilibrium residual at that fixed damage state. The
experiment does not use the AT1 damage equation, fatigue-history update, damage
irreversibility, or temporal rollout and therefore is not a damage-evolution PINO.

## Frozen candidates and identity

No optimizer step is permitted.

| Role | Asset | SHA256 |
|---|---|---|
| selected candidate | S09-E006 `balanced_beta_0p25_final.pt` | `1abb0e73a576349924341a46209d158482123478448e8bee333c713a5ad18b2a` |
| honest comparator | S09-E006 `data_only_replay_final.pt` | `4bb51840da4fe6cfd845b436e4cea5a59a5ff02e32a59bc2b29eb9451a3ef804` |
| architecture/static reference | S09-E004 packet | `b37a63ccb0e7129ecc3fbe01fc356c93fccc1877b5f34e68fe93265f335109ed` |
| model-selection evidence | S09-E006 exact close commit | `fcf006df2a1155f52fec1dbecfa3207a856c1a58` |

The U0.125 archive is the pre-existing Request 31 same-family trajectory. It
must be copied read-only into a fresh S09-E007 evidence root only after design
review. Its complete source/archive identity, source commit, mesh, state timing,
payload hashes, and exposure limitation must be recorded before inference.

## Pre-field-read trajectory membership lock

Before any `d_node`, `u_node`, residual, or other scientific array is decoded,
source-side immutable metadata must lock the first cycle, authoritative final
producer cycle, expected contiguous cycle sequence, and exact Contract-B state
identity for every cycle. The source stop may come only from the producer's
immutable index, receipt, or event metadata; it may not be inferred from the
last file that the packet builder can load. Each expected cycle must have
exactly one committed substep-4 peak state and one payload hash. Any absent,
duplicate, unqualified, or unverifiable required cycle, or inability to
establish the authoritative stop, makes E007 inadmissible. No shorter inferred
horizon is allowed.

## Evaluation unit, origin, horizon, inputs, and target

- Unit: one complete U0.125 trajectory, with every qualified Contract-B cycle
  peak state included in native cycle order.
- Origin/horizon: same-state fixed-damage reconstruction; no temporal horizon.
- Allowed input: same-state committed `d_node`, actual imposed peak displacement,
  and the fixed mesh/operator graph.
- Target: same-state FEM `u_node` at substep 4 `post_history_commit`.
- Comparator: the frozen data-only checkpoint evaluated on identical states.
- Grouping: trajectory aggregate is primary; cyclewise values and early/middle/
  late thirds are diagnostics.
- Missing data: any missing/noncontiguous required state, unknown cycle/substep,
  nonfinite array, mesh mismatch, boundary mismatch, or failed producer flag
  makes the experiment inadmissible. No state may be dropped after inspection.

## Immutable inference specification

Both checkpoints use the exact E004/E006 inference semantics implemented by
`source/s09_equilibrium_operator.py`, `source/s09_fem_physics.py`,
`source/s09_q4_quadrature.py`, and the evaluation path in
`SENS_tensile/run_s09_equilibrium_operator.py`. Those semantics were frozen at
E004 commit `11fd75d70b18165d6214d50c90adc9c9b522a5` and required unchanged by
E006.

- Node features are ordered `[d_node, x, y, boundary_flag, load/0.12]` in
  native node order. `load` is the actual imposed substep-4 displacement and is
  the sole scalar loading value supplied to the model.
- Coordinates, Q4 connectivity, directed native graph, 24 by 24 occupied coarse
  graph, lumped areas, node/component order, width 32, rank 8, and two local
  integral blocks remain exact.
- Prediction uses float32 in `eval()` under `torch.no_grad()`. No fitting,
  adaptation, batch-statistic update, state-dependent calibration, or
  U0.125-derived normalization is permitted.
- Frozen checkpoint buffers supply `load_scale=0.12` and the two-component
  correction scale. Output reconstruction is
  `load * [affine_normalized + t(1-t)*raw*correction_scale]`, hard-imposing the
  top/bottom Dirichlet values.
- Scoring uses native ordering and the unchanged native-Q4 2 by 2 Gauss,
  plane-strain AMOR residual assembly, free-DOF mask, affine reference, and RMS
  over both free displacement components.
- Target `u_node` is scoring-only. Target displacement, target residual, later
  cycles, and any U0.125 statistic cannot influence a prediction.

## Necessary validity gates

1. U0.125 archive and every payload are hash inventoried before scientific read.
2. Producer family, source identity, 86,756-node/86,408-Q4 mesh/order, material,
   Umax=0.125, five-substep cadence, and Contract-B timing match Request 31.
3. All trajectory Contract-B peak states are contiguous through the declared
   producer stop; all are finite, converged, and have exact top/bottom displacement
   boundary values within the predeclared builder tolerances.
4. Neither checkpoint, source, criterion, state set, nor analysis code changes
   after the first U0.125 field value is read.
5. Inference records zero optimizer steps and exact checkpoint hashes.

Failure of a validity gate is `inadmissible`, not a performance failure.

The evaluator must verify that both state dictionaries load strictly into the
same architecture and that every required prediction, residual, and metric is
finite. A deterministic checkpoint/evaluator computation failure on otherwise
valid source data is `evaluation_failure`, not a source-validity failure.

## Metrics

For checkpoint `m`, cycle `j`, and lumped nodal areas `w`, define

\[
  E^u_{m,j}=\|u_{m,j}-u_j\|_w,
  \qquad
  E^f_{m,j}=\operatorname{RMS}_{\mathrm{free}}
  r_u(u_{m,j};d_j).
\]

The trajectory displacement ratio uses sums of errors, rather than the mean of
cyclewise ratios:

\[
  Q_u=\frac{\sum_j E^u_{\beta=.25,j}}
            {\sum_j E^u_{\mathrm{data},j}}.
\]

The trajectory equilibrium ratio is

\[
  Q_f=\frac{\frac1J\sum_j E^f_{\beta=.25,j}/E^f_{\mathrm{affine},j}}
            {\frac1J\sum_j E^f_{\mathrm{data},j}/E^f_{\mathrm{affine},j}}.
\]

Affine denominators are recomputed state by state and must be positive and
finite. Report cyclewise displacement and residual ratios, quantiles, worst
cycle, early/middle/late thirds, absolute-to-affine values, boundary error,
runtime, and peak memory as diagnostics.

Every per-state affine residual denominator and both aggregate comparator
denominators

\[
D_u=\sum_j E^u_{\mathrm{data},j},\qquad
D_f=\frac1J\sum_j E^f_{\mathrm{data},j}/E^f_{\mathrm{affine},j}
\]

must be strictly positive and finite. No epsilon substitution, clipping,
fallback metric, or omitted cycle is permitted. An individual cyclewise
candidate/data ratio is reported as undefined when its data-only denominator
is zero; this does not invalidate a defined all-cycle primary ratio.

## One joint primary criterion

Both clauses are necessary for the bounded trade-off claim:

\[
  Q_f \le 0.50 \quad\text{and}\quad Q_u \le 1.10.
\]

The thresholds are carried forward unchanged from S09-E006: at least 50%
residual reduction while spending at most a 10% aggregate displacement penalty.
Using a complete trajectory makes an aggregate displacement guard more stable
than requiring every one of many correlated cycle states to fall below 1.10;
the maximum and upper-tail cyclewise ratios remain mandatory diagnostics and
cannot rescue or overturn the aggregate verdict.

## Criterion feasibility and outcome map

S09-E006 achieved `Q_f=0.396805` and worst-development-state displacement ratio
`1.096920` on three U0.12 states. Therefore the fixed thresholds are attainable
but close enough to the observed boundary to discriminate transfer. No U0.125
field value was used for this calibration.

The exhaustive table below is authoritative; no discretionary relabelling or
repair choice is permitted after results become visible.

## Exhaustive outcome and immediate disposition

| Condition | E007 decision | Immediate disposition |
|---|---|---|
| source, identity, membership, or protocol gate fails | `inadmissible` | repair only data/export/identity defects; no scientific conclusion |
| valid and both thresholds pass | `positive` | advance to S09-E008 Stage-0 transition design |
| only `Q_u` fails | `negative_displacement` | open new development work on displacement-constrained optimisation; do not tune on U0.125 |
| only `Q_f` fails | `negative_equilibrium` | audit residual convention and damage-regime support |
| both fail | `negative_both` | stop this fixed-damage rescue and redirect to state-sufficient transition formulation |
| valid inputs but a primary ratio is mathematically undefined | `inconclusive` | audit numerical definability; make no threshold claim |
| checkpoint/evaluator computation fails | `evaluation_failure` | preserve failure evidence; no positive claim or model-selection retry |

Discussion may propose later experiments, but cannot change this E007 decision
or immediate disposition after results are visible.

## Operational lock and unsealing order

1. `DESIGN_READY` authorizes source metadata acquisition, hash inventory, and
   bounded read-only copying only.
2. Lock trajectory membership from non-field source metadata. Implement and
   test the packet builder/evaluator using E004 or synthetic fixtures only.
3. Obtain exact-commit `CODE_READY`, freezing evaluator, checkpoint identities,
   source manifest, thresholds, decision logic, and execution assets.
4. Record the first decoding of any U0.125 scientific array as the permanent
   unsealing event. If source validation requires decoding a scientific field,
   it is already this event.
5. Perform exactly one guarded full-trajectory inference.

After unsealing, no scientifically motivated code or metric repair, candidate
selection, or retry is allowed in E007. A purely operational retry is allowed
only if zero U0.125 prediction or metric was produced, immutable inputs/code
are unchanged, and independent review explicitly classifies it as
non-scientific; otherwise preserve the failure and stop.

## Stop rule, minimum evidence, and blocked conclusions

Exactly one read-only evaluation of both frozen checkpoints on the full qualified
U0.125 trajectory is allowed. No training, threshold amendment, selected-cycle
subset, beta sweep, architecture change, or retry after scientific values are
visible is permitted inside E007.

Minimum evidence: data-lock/lineage report, compact holdout packet manifest,
reviewed evaluator commit, execution receipt, every-cycle metrics, exact decision
table, decision figure showing both primary ratios and cyclewise variation, field
views for the deterministic first/middle/final cycle, README_analysis, verified
retrieval, independent Evidence Ready review, and dated S09/Obsidian claim impact.

Early/middle/late diagnostics use `numpy.array_split` on the locked ordinal
cycle sequence. Field views use ordinals `0`, `(J-1)//2`, and `J-1`, fixed
before scoring. Consecutive cycles are correlated and are never presented as
independent samples or used for a generalisation confidence interval.

No outcome may establish exact equilibrium, Pareto dominance, independent blind
confirmation, damage/fatigue evolution, autonomous forecasting, seed robustness,
cross-mesh transfer, FEM physical truth, or real-road validity.

## Producer routing

U0.125 acquisition is read-only from the existing CITPC12 archive. Do not start,
stop, attach to, or alter any current MATLAB process. Packet construction and
static validation may occur on Mac. Full native-mesh inference runs on Taobo
GPUServer8 after exact-commit Code Ready review; Mac runs only audit/import/unit
checks and plotting.
