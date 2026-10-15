# Raw physical-scale feasibility design — v2 for independent re-review

Date:2026-10-15, Europe/London. Owner:S04 / S04-E016 design follow-up.
Status: **DOCUMENT ONLY / NOT REVIEW-APPROVED / NO IMPLEMENTATION OR FIT**.
This dated v2 replaces the proposed v1 contract for future design review only.
v1 at410fffc, its independent review, original R002 outputs and data lock remain
unchanged. No new experiment, run, numerical result or model is created here.

## 1. Scope retained; three review corrections

Question: can a single-output physical raw-driver ridge correction improve the
worst complete-Umax development holdout, without early-regime loss, relative to
an identically pointwise-admissible control?

| Review item from `design_review_result_410fffc_20261015.md` | v2 resolution |
|---|---|
| h_train omitted although history remains in X | §3 specifies BOTH h/r, exact weights and independent inner/outer ownership |
| numerical error could be hidden as ordinary fallback | §4 terminates validity failures; only identified performance conditions reach normal fallback |
| tolerance/outcome and partial fallback ambiguous | §5 defines disjoint tolerance branches; all four folds included; any fallback prevents strict worst-fold gain |

Retain synthetic native-P0, nominal-peak s4 post-history, horizon0 imitation,
external correction with frozen PINN, and the admitted native-cell mean
`psi_raw_direct` in original archive units. This is not a log-value, active
driver, reaction, stress or energy-integral target. No mechanics, irreversibility,
teacher, forecast or reality-facing validity claim.

Retain paired lock
`cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c`,
85112 admitted cells; four development prefixes u011:c1-121,
u0115:c1-99,u012:c1-82,u013:c1-55,357 cycles. Retain native-area weighting,
whole-Umax nested grouping, equal case and C1-20/C21-40/C41+ weights,
2048 systematic geometry-only fit rows/cycle, full admitted-domain scoring,
and the unchanged32 PIN-only causal features (current/past2/missing masks,
geometry, load, physical cycle, current globals/9NN).

The viewed four trajectories are development evidence, not fresh confirmation
or independent material replicates. C0 unavailable; no fake history. U0.1175
and U0.125 remain closed. No new trajectory/solver, learned support/FEM event
input, f/active/H head, shared encoder, MOO or direct-data method comparison.
R002's jointly changed target/output/selector motivates a repair-package test,
not a causal ablation attributing any eventual gain to one changed component.

## 2. Exactly two prospective arms; output definition unchanged from v1

```text
V0.d   = min(1,max(0,PIN.d))
V0.ab  = max(0,PIN.ab)
V0.raw = max(0,PIN.raw)

V1.d   = V0.d
V1.ab  = V0.ab
V1.raw = max(0, PIN.raw + r_train*t_hat(X))
```

No learned d/history head. Both arms share the same maps; original signed
inputs and archives are not clipped or overwritten. Admitted PIN ab/raw are
already nonnegative, so their V0 maps are identities. V0 is an admissible-output
control, not untouched PINN. Do not apply these maps to old R002 results.

Damage is bounded[0,1]; ab/raw are nonnegative with no invented upper cap.
Exact boundaries are allowed; no epsilon-logit or target-derived cap. Projection
cannot increase pointwise squared d error to a reference in[0,1], and d/ab are
identical between arms, including early cycles. This analytic property is not
a new measured result. No running maximum, isotonic/future smoothing or claim
of temporal irreversibility, energetic balance or joint physical closure.
Never substitute f(mean history) for native mean f or products of mean parents
for a native mean active driver.

## 3. Complete input/label scaling and sole learned model

For EACH inner-training pair or outer-training triple T, independently define:

```text
a_i = native_area_i / sum(admitted native areas)
w(u,c) = 1 / [3 * n(u,stratum(c))]          for c in u's admitted prefix
h_T = (1/|T|) * sum_u_in_T sum_c w(u,c) sum_i a_i PIN.ab(u,c,i)
r_T = (1/|T|) * sum_u_in_T sum_c w(u,c) sum_i a_i PIN.raw(u,c,i)
```

h_train=h_T and r_train=r_T are full admitted-domain **training-PIN-only**
means, not fit-row means, FEM scales, heldout scales or previous outer-fit
statistics. Both must be finite and>1e-12; failure is terminal INVALID_INPUT,
not a replacement floor or normal fallback. Equal trajectory/stratum weighting
and actual retained cycle counts are unchanged. All three strata are nonempty
in the retained data.

Supply BOTH scales to the unchanged feature transform: history uses
log1p(PIN.ab/h_T), raw and active_proxy use r_T as already declared. Current,
lagged, global and neighbor features use this same training-set pair. Removing
history OUTPUT does not remove history INPUT or its scale. Scales are fixed
when evaluating that model on an inner validation or outer heldout trajectory.

Only learned label is `t=(FEM.raw-PIN.raw)/r_T`. X and scalar t have training-fit-
row weighted means/std, with native sample areas renormalized per cycle and
unchanged case/stratum weights. Use stable streamed moments/normalized Gram;
finite std<1e-12 maps to1, not nonfinite std. Intercept unpenalized; alpha set
{.01,1,100}. Reconstruct t_hat from standardized prediction before the output
map. No expm1 target inverse. This is physical-residual ridge followed by a
fixed nonnegative map, not a constrained nonlinear optimizer.

Evaluate physical MSE on FINAL mapped outputs, not latent residuals or the
unmapped raw sum. Input-feature log transforms remain; physical target and
model-selection errors do not use log loss. No new feature, importance mask,
NN, variable output head or empirical loss-weight search.

## 4. Error routing BEFORE selection — no numerical fallback

These branches have priority over performance decisions:

| Condition at any required inner/outer stage | Required action |
|---|---|
| wrong source/state/support/shape identity, invalid weights/scales or violation of original source-admission bounds | terminate entire diagnostic as INVALID_INPUT; retain evidence |
| nonfinite input/intermediate/moments/normalizer/Gram/coefficient/prediction/error/ratio, solver exception or overflow | terminate entire diagnostic as INVALID_NUMERICS; do not try another alpha as a recovery |
| mapped V0/V1 violates d in[0,1] or ab/raw>=0, or V1.d/ab differs from V0 | terminate as INVALID_IMPLEMENTATION |
| finite baseline physical MSE denominator<=1e-24 for any required all-cycle or early ratio, inner or outer | terminate INCONCLUSIVE_UNIDENTIFIED; do not add a floor, exclude a fold/alpha or emit a successful V0 fallback |
| time/memory/output cap or missing required evidence | stop/freeze as INCONCLUSIVE_INCOMPLETE; no automatic retry |

Check finiteness BEFORE AND AFTER maps: max(0,-Inf) must never hide an invalid
latent value. A finite negative UNMAPPED raw sum is allowed and is mapped to0;
it is not a validity failure. Bounds apply to final output, not signed Delta.
Original source admission allows signed PIN.d: never apply final-output[0,1]
bounds to that input or silently change the32-feature contract.
An invalid alpha is never silently removed from the grid. Partial existing
metrics may be retained as partial only, not as a completed method comparison.
Future implementation must preserve warnings and demonstrate numerical checks;
warnings or failures cannot authorize normal baseline fallback.

Zero-baseline equality can be recorded, but does not identify a ratio or change
the terminal unidentified status. This makes inner/outer denominator handling
uniform and explicitly supersedes v1's candidate-ineligibility wording.

## 5. Metric, eligibility, fallback and complete tolerance partition

For u,stratum s,V, M(u,s,V) is full admitted native-area physical raw MSE,
equally averaged over cycles within s. Define:

```text
E(u,V) = [M(u,early,V)+M(u,middle,V)+M(u,late,V)]/3
R(u) = sqrt(E(u,V1)/E(u,V0))
G(u) = sqrt(M(u,early,V1)/M(u,early,V0))
Q = max_u R(u)                         over ALL FOUR outer trajectories
eps = 1e-10                            dimensionless numerical tie only
```

**Inner selection:** apply §4 first. For each alpha, compute all three inner
validation R/G values in physical units after the output map. Alpha is
performance-eligible only if EVERY inner G<=1+eps. Minimize the largest inner R
among eligible alphas; exact equal objective values choose larger alpha.
This exact ranking rule is separate from the eps directional/tie predicates.

Choose a learned alpha only if that minimum worst-inner R<1-eps. Otherwise,
with all validity/identifiability checks satisfied, choose V0 for the WHOLE
outer trajectory. Record whether no eligible alpha or no strict inner gain
caused fallback. Do not inspect outer targets to make this choice. If selected,
refit the chosen family on the three outer-training trajectories; do not
reuse an inner normalizer. No per-cell/per-cycle or early-only switching.

**Outer evaluation:** apply the frozen choice, evaluate/retain every fold.
Outer regression is an observed result, never permission to switch to V0,
retune, drop early cycles or omit a fold. Validity/undefined/cap branches stop
as §4 specifies. Otherwise use the following disjoint decision order:

| Priority | Complete-data condition | Diagnostic outcome |
|---|---|---|
| 1 | ANY outer G>1+eps | EARLY_REGRESSION, regardless of Q |
| 2 | all G<=1+eps AND Q>1+eps | RAW_REGRESSION |
| 3 | all G<=1+eps AND Q<1-eps | DIRECTIONAL_DEVELOPMENT_GAIN |
| 4 | all G<=1+eps AND 1-eps<=Q<=1+eps | NUMERICAL_TIE / no strict worst-fold gain |

Both Q boundary equalities fall into TIE; G=1+eps is eligible. eps is not a
physical/noninferiority tolerance, statistical uncertainty or practical margin.
No10% goal or5% allowed early loss is invented. Damage/history cannot buy a
raw pass; log-space gains cannot rescue physical failure. Reference uncertainty
and a meaningful physical margin remain unqualified, so this is diagnostic.

If ANY outer fold used normal fallback, V1=V0 in that fold, hence R=G=1 there
and Q>=1. Strict whole-design improvement is then impossible by construction.
Other folds may still have measurable gain or harm: report them ALL, with
fallback flags, then use the same outcome order. Partial fallback is not
automatically a tie if another fold regresses. All-fallback gives Q=G=1 and
TIE, with the additional label NO_SELECTED_LEARNED_CORRECTION, never success.

## 6. Unique minimum package retained; test specifications only

Still only V0/V1, one raw ridge family, the same three nested alphas and four
outer whole-Umax folds; reusable inner pairs have independent training-owned
statistics. No new arm, clipping ablation, old B1 rerun or producer acquisition.
Prospective combined cap stays300s/2GiB/100MiB, Mac CPU4/noGPU for closed-form
analysis only. This proposed cap does NOT authorize execution or a training loop.

Before a future fit, specify a new Experiment/protocol and Run ID (do not reuse
S04-E017's historical candidate or R002), then exact implementation/resource
review and explicit user run approval. Do not implement or execute tests now.
The future toy/engineering checklist must cover:

- BOTH training-owned h/r with heldout perturbation isolation; physical-unit
  target/reconstruction; streamed/dense equivalence and working-set checks;
- zero predicted raw residual maps to V0.raw; a zero-residual target fixture
  respects constant-target std handling; d/ab identity is relative to V0,
  NOT to unprojected signed PIN d;
- nonnegative projection never increases squared error to a nonnegative
  reference; d interval projection does likewise for reference in[0,1];
- pre/post-map NaN, Inf (including -Inf), mapped-bounds and solver failures
  select TERMINAL_INVALID, never normal fallback;
- unidentified inner/outer denominators select terminal INCONCLUSIVE, never a
  fabricated finite ratio or performance veto;
- G=1+eps is eligible, G>1+eps is not; Q=1-eps and Q=1+eps are ties;
- partial fallback includes all four folds and cannot give strict worst-fold
  gain; other-fold harm is still reported as harm; all-fallback is no gain;
- all selection/scored physical errors use final mapped predictions; outer
  failure cannot revise a frozen choice.

These are acceptance-test SPECIFICATIONS, not implemented/passed tests. Future
evidence remains percycle physical MSE/ranges/violations, inner eligibility and
fallback decisions, all four R/G, models and receipts, and fixed U0.115/C20
V0/V1/FEM raw snapshots. Decision figures show all-fold physical R and early G
vs1 plus fixed native C20 fields/errors; CSV and README authoritative. Retain
no full predicted trajectory in memory merely to plot. Pointwise output bounds
still do not establish unmeasured temporal/mechanical consistency.

## 7. Authority and next action

v1 review at5591543 records revision-required, not design/code/run approval.
This v2 is self-contained for the proposed metric, scales and selection/error
rules; v1 remains historical, not a competing fallback rule. No new method or
data claim is admitted. Main chat sole owner; method chat read-only reviewer.
Teacher/physics, U0.1175/U0.125, NN/MOO and coupled rollout remain closed.

Next action ONLY: prepare the exact v2 review message for per-send user
approval. Neither its preparation, later sending, nor a design endorsement
authorizes implementation or fitting. No message has been sent for v2.
