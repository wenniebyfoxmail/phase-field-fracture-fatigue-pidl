---
storyline_id: S09
experiment_id: S09-E008
protocol_revision: v0-design-draft-transition-stage0
status: analysis
primary_storyline: S09
related_experiments: [S09-E001, S09-E005, S09-E006, S09-E007]
claim_class: C1
evidence_domain: synthetic
---

# Stage-0 damage/history transition neural operator

## 2026-10-16 P1 outcome

The exact reviewed P1 run completed with `execution_status=succeeded` and
`retrieval_status=verified`, but the frozen formal P1 verdict is negative.
Validity passed; capacity, detectable-growth and near-stagnant clauses failed.
The result and mechanism analysis are recorded in
[`runs/S09-E008-P1-R001-stage0a-memorisation/run.md`](runs/S09-E008-P1-R001-stage0a-memorisation/run.md)
and [`p1_run_analysis_20261016.md`](p1_run_analysis_20261016.md).

This outcome does not amend the used P1 protocol or rescue its verdict. Any
new loss decomposition, multi-objective rule, architecture, budget or criterion
belongs to a separately identified and reviewed diagnostic Experiment.

## Purpose and claim boundary

S09-E007 closed the last fixed-damage selection gate. S09-E008 changes the
learned object from a same-state displacement reconstruction to a causal state
transition. The first aim is to prove that a mixed nodal/GP operator can advance
qualified damage and fatigue-history state without future-field leakage, while
using FEM-consistent constraints and a deliberately relaxed development gate.

This draft does not authorise data unsealing, implementation, training or a
scientific claim. Numerical thresholds below are prototype development gates,
not publication accuracy or constitutive tolerances.

## Corrected temporal contract

The producer index distinguishes:

- `c_k_s00`: `pre_cycle_committed`, aliasing `c_{k-1}_s05` for `k>1`;
- `c_k_s01..s05`: committed states after each prescribed substep;
- `s04`: peak load; `s05`: unloaded post-cycle state.

A peak-to-peak map alone cannot autonomously roll because the state after the
unload/history update is missing. The programme is therefore split:

### Stage 0A: one-cycle peak transition

\[
\mathcal T^{\mathrm{peak}}_\theta:
(S^{\mathrm{pre}}_k,\,\mathbf U_k)
\longmapsto
(d^{\mathrm{peak}}_k,\,h^{\mathrm{peak}}_k,\,u^{\mathrm{peak}}_k),
\]

where

\[
S^{\mathrm{pre}}_k=(d^{s00}_k,h^{s00}_k),\qquad
h=(H,\bar\alpha,q_{\mathrm{prev}},f)_{\mathrm{GP}},
\]

and `U_k` is the complete prescribed s01--s05 load path, not merely cycle
number. Stage 0A advances damage/history from the causal pre-cycle state to the
peak. It is a damage/history transition candidate but cannot claim autonomous
cycle rollout.

### Stage 0B: rollout-capable cycle transition (deferred amendment)

\[
\mathcal T^{\mathrm{cycle}}_\theta:
(S^{\mathrm{pre}}_k,\,\mathbf U_k)
\longmapsto
\bigl(u^{\mathrm{peak}}_k,d^{\mathrm{peak}}_k,h^{\mathrm{peak}}_k,
      S^{\mathrm{post}}_k\bigr),
\]

with `S_post_k=(d^{s05}_k,h^{s05}_k)` and the identity
`S_pre_{k+1}=S_post_k` checked against the producer alias. Only Stage 0B output
may feed the next cycle. A later multi-substep operator may replace the two-head
contract, but that is outside the first wiring experiment.

Any Stage 0B implementation must enforce the within-cycle ordering

\[
d^{\mathrm{pre}}\le d^{\mathrm{peak}}\le d^{\mathrm{post}}\le1,
\quad
\bar\alpha^{\mathrm{pre}}\le\bar\alpha^{\mathrm{peak}}
\le\bar\alpha^{\mathrm{post}},
\quad
f^{\mathrm{post}}\le f^{\mathrm{peak}}\le f^{\mathrm{pre}},
\]

and the frozen `f(alpha_bar)` law at both outputs. Constraints for `H` and
`q_prev` remain blocked until their producer update semantics are qualified.
This revision authorises design and bounded implementation of Stage 0A/P0/P1
only. Stage 0B heads, their joint supervision, and P2 evaluation require a
separate reviewed amendment.

No same-cycle target field, target-derived event flag, later cycle, or held-out
normalisation may enter either input.

## Native supports and minimum architecture

- `d` and `u` remain nodal fields on 86,756 native nodes.
- `H, alpha_bar, q_prev, f` remain on the native 86,408 Q4 elements by four
  Gauss points. They are not silently nearest-neighbour rasterised into nodal
  truth.
- A nodal graph backbone reuses the qualified local/coarse operator path.
- GP history is encoded on its own support. Fixed Q4 shape functions and
  connectivity provide node-to-GP and GP-to-node messages; a GP head predicts
  history increments on the original support.
- The node head predicts `u_peak` and raw damage increment. Hard displacement
  lifting enforces peak Dirichlet values. Damage is reconstructed as
  `d_next = clamp(d_old + delta_d_raw, d_old, 1)` while retaining raw proposals,
  projection rate and saturation rate.
- Zero damage/history increment must be representable. Absolute cycle index is
  excluded.

The source audit must also prove state sufficiency: every producer variable
needed to advance s00 to s04 must either be present in `S_pre`, supplied as a
prescribed control or frozen material/solver constant, or be causally
reconstructible from those quantities. Field names alone are insufficient.

Stage 0 uses width 32 and the existing two local plus one coarse path as the
smallest viable backbone. A larger architecture is permitted only in a new
revision after a demonstrated capacity bottleneck.

## Data capability and split gate

Before implementation or training, a source audit must verify every required
payload hash and decoded identity for complete s00--s05 paths; exact alias
relations; native mesh/order; history labels, units and update timing; finite
fields; material and load path; and equality of `c_k_s00` with the referenced
prior `s05` bytes/fields where declared.

U0.125 is already exposed and may be development-only. Existing U0.115 states
were used in earlier training and are also development-only. A confirmation or
generalisation claim requires a different complete Umax trajectory whose
scientific fields remain sealed through design/code freeze. Random cycle or
state splits are forbidden. If no such trajectory exists, Stage 0 may stop at a
development prototype and must acquire a new complete trajectory before P3.

## Physics and multi-objective ladder

Validity constraints remain strict even when performance criteria are relaxed.
Physics objectives enter one at a time:

1. exact native mesh and hard displacement boundary;
2. damage range and irreversibility relative to the causal pre-state;
3. `alpha_bar_next >= alpha_bar_old`, nonincreasing Carrara `f`, and consistency
   of `f(alpha_bar)` under the producer's frozen law;
4. native-Q4 plane-strain AMOR free-DOF mechanical equilibrium at peak,
   conditioned on predicted `u_peak` and `d_peak`;
5. only after exact staggered semantics and teacher residual qualification: AT1
   phase-field stationarity/projected KKT on predicted damage.

Hard constraints are reported separately from residual objectives. Training
uses explicit objectives for nodal state data, GP-history data and equilibrium.
Raw unnormalised losses are never added directly. Stage 0 starts with
training-set scaling plus gradient-norm balancing and conflict projection,
carrying forward the S09-E005/E006 evidence. Per-objective gradients, projection
frequency, post-projection alignment and effective ratios are logged. A fixed
raw scalar sum is a diagnostic ablation, not the default.

## Relaxed but discriminating staged gates

### P0: state-contract and differentiation smoke

All shapes/supports/times/hashes are exact; forward/backward is finite; hard BC
error is within the existing numerical tolerance; zero increment is
representable; projected outputs satisfy bounds/irreversibility/monotonicity;
no target or future field is reachable from model inputs. Passing P0 means only
that the architecture and contracts run.

### P1: bounded memorisation on development windows

Use exactly 16 U0.125 transitions selected once by the deterministic
development-only rule below. One seed, at most 1,000 updates. Selection and all
scales are written to the receipt before model initialisation.

For cycle `k`, define the teacher damage increment and its area-weighted scale

\[
\Delta d_k=d^{s04}_k-d^{s00}_k,\qquad
g_k={\sum_i a_i |\Delta d_{k,i}|\over\sum_i a_i},
\]

using the frozen nodal lumped areas. Let `eta` be the maximum, over eligible
cycles, of the same weighted mean after replacing each absolute increment by
the sum of the two stored floating-point half-ULPs. This is an export-resolution
convention, not a solver-error estimate. Let `D` be the median `g_k` in the
upper quartile of all eligible cycles. Define detectable growth as
`g_k >= D` and near-stagnation as `g_k <= max(10 eta, 0.05 D)`.

Partition cycles into the fixed chronological bands 1--24, 25--49 and 50--73.
Within each band, rank by `(g_k, cycle_id)`. Select the two smallest and two
largest cycles from every band, then add the two globally smallest and two
globally largest unselected cycles, breaking ties by cycle id. The selected 16
must contain at least four detectable-growth and four near-stagnant cycles;
otherwise data capability is `P1_NOT_READY` and the rule is not repaired after
inspection.

Acceptance uses a fixed data metric, separate from adaptive training weights.
For the selected set, freeze before initialisation the teacher RMS scales for
damage increment, each of the four GP-history increments and each displacement
component. Each scale is floored by its corresponding stored-float half-ULP
RMS. Let `E_d`, `E_h,j` and `E_u,c` be native-support, area-weighted MSE divided
by the square of those frozen scales. The judgement loss is

\[
L_{\mathrm{judge}}={1\over3}\left(E_d+{1\over4}\sum_{j=1}^4E_{h,j}
 +{1\over2}\sum_{c=1}^2E_{u,c}\right).
\]

Its initial value is recorded immediately after deterministic initialisation;
its final value is evaluated on the same 16 examples and fixed scales.
Gradient-balancing weights never enter `L_judge`.

Necessary clauses:

- `L_judge_final <= 0.20 L_judge_initial`;
- on the selected detectable-growth group, the mean area-weighted
  damage-increment MAE is below the persistence/zero-increment baseline
  `mean(g_k)`; this denominator must be strictly positive;
- on the selected near-stagnant group, false growth
  `mean_k sum_i a_i max(predicted_Delta_d_i - Delta_d_i,0)/sum_i a_i`
  is no larger than `0.25 D`;
- finite outputs/gradients and zero constraint violations.

Failure is decomposed by clause; one total `FAIL` must not erase wiring,
capacity, growth or stability information.

### P2: autonomous three-cycle development rollout (not authorised here)

Requires the separately reviewed Stage 0B amendment. That amendment must freeze
the starting cycles, peak and post heads, autoregressive reference/predicted
increment definitions, persistence denominator and aggregation before P2 can
run. No P2 threshold in this document authorises execution.

### P3: sealed complete-trajectory confirmation

Only after data capability identifies a field-sealed complete Umax trajectory,
freeze the model/config/threshold and evaluate once. P3 thresholds, seeds and
comparators must be reviewed before opening that trajectory. Persistence and a
constrained-linear increment baseline are mandatory.

## Stop rules

- No scientific run before `DESIGN_READY`, exact-commit `CODE_READY`, and data
  capability PASS for the named stage.
- Do not repair state timing, formulas, thresholds or subsets after relevant
  scientific fields/results are visible inside an experiment.
- P0/P1 failure first opens a diagnosis experiment; it does not authorise a
  larger model, more updates or random scalar-loss tuning.
- AT1/KKT remains blocked until the exact producer residual is reproduced on
  known states and its old/new/fixed-variable semantics are reviewed.
- A development pass does not authorise transition-generalisation or real-road
  claims.
