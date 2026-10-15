# Proposed design revision: physical raw-driver feasibility first

Date: 2026-10-15, Europe/London. S04 / S04-E016 design follow-up.
Status: **DESIGN DRAFT FOR INDEPENDENT REVIEW; NO FIT OR EXECUTION AUTHORITY**.
This is not an amendment that retrospectively changes D0/R002. A future fit
would need a separate Experiment ID/protocol and fresh Run ID, exact code review
and explicit user authorization. Do not reuse R002 or assume R003 is approved.
S04-E017 is already used by a historical multi-objective candidate; do not
silently overwrite it. Allocate the new ID only after design review.

## 1. One question and explicit scope reduction

Can a simple **single-output physical-scale raw-driver correction**, with a
fixed nonnegative output map, improve the worst complete-amplitude development
holdout over the same admissible baseline without sacrificing the early regime?

This first test does NOT learn new damage or history corrections. It knowingly
forgoes R002's late damage gain to avoid another three-output tradeoff before
raw learnability is established. The whole system remains external to frozen
PINN, same-state nominal-peak s4 post-history, horizon0, native P0 synthetic
archive imitation. No coupled solve, rollout, teacher/road validation or active
process-zone closure claim.

The estimand is the admitted native-cell mean `psi_raw_direct` in its original
archive units, not its log value, a FEM event time, true stress, reaction,
active driver or material energy integral. Native support/reduction remains
unchanged; this design cannot remove its mesh/query limitations.

The proposal changes target/selection/output contract together. It is a bounded
repair-package feasibility test, NOT an isolated causal ablation proving that
log loss alone caused R002's regressions.

## 2. What is retained and what changes

| Component | Retained | Proposed change |
|---|---|---|
| Data identity | paired lock cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c | none; source arrays/metadata remain immutable |
| Development support | .11/.115/.12/.13;357 real pre-event cycles;85112 native cells | none |
| Information | original signed PIN fields, current/past2, missing masks;32 causal features | no FEM/event/support feature; features stay log1p where already declared |
| Grouping/weights | whole-Umax nested holdouts;equal trajectories and C1-20/C21-40/C41+;native areas | none |
| Training rows | same2048 geometry-only systematic indices per cycle | none; no FEM-driven oversampling |
| Learned target | old three-channel transformed residual is historical | only physical raw residual; no expm1 output inversion |
| Model selection | all statistics training-only;alpha .01/1/100 | raw physical error only, with inner early-regime veto |
| Damage/history | original input/output records retained as historical | same pointwise-admissible baseline in both new arms; no learned correction |

U0.1175 and U0.125 stay closed. C0 is unavailable and is not invented. All
observed trajectories have already informed this design: subsequent outer
scores are **development diagnostics**, not untouched confirmation or four
independent material replicates. No claim that nested CV erases design exposure.

## 3. Bounded/nonnegative output contract

Define the prospective, explicitly named baseline V0 and sole candidate V1:

```text
V0.d(c,i)   = min(1, max(0, PIN.d(c,i)))
V0.ab(c,i)  = max(0, PIN.ab(c,i))
V0.raw(c,i) = max(0, PIN.raw(c,i))

V1.d  = V0.d                         [no learned damage head]
V1.ab = V0.ab                        [no learned history head]
V1.raw(c,i) = max(0, PIN.raw(c,i) + r_train * t_hat(X(c,i)))
```

The admitted PIN history/raw are already nonnegative, so their V0 maps are
identities. The damage projection is **not** a rewrite of PIN or R002 and is
not to be executed now. Both future arms use exactly the same map. Original B0
and R002 signed ranges remain reported; they are provenance, not a third fitted
arm. Call V0 an admissible-output control, not the untouched PINN.

These maps allow exact0/1 boundaries without arbitrary epsilon/logit offsets.
No upper cap on raw/history is justified; do not import FEM maxima or quantiles
as deployment caps. Damage is bounded; history/raw are nonnegative but may be
unbounded above. Delta itself may be signed. Raw is not a monotone state.

For a reference d in[0,1], interval projection cannot increase pointwise
squared damage error. This is an analytic property, not a new measured result.
Together with identical V0/V1 damage/history, it gives exact non-degradation
for those channels relative to V0, including C1-20. A finite-precision unit
check is still required before any future implementation is used.

**Not guaranteed:** cross-cycle irreversibility, force balance, energy balance,
or joint damage/history/driver consistency. Do not apply a running maximum,
isotonic smoother or future-cycle projection. A physical state-evolution claim
would first require a qualified temporal reference and separate protocol.
No f/active/H output head, `f(mean history)` closure or product-of-means active
target is added. Pointwise admissibility is necessary, not physical sufficiency.

## 4. Sole learned candidate, fully specified at design level

For each inner/outer training set compute r_train using the unchanged full-area
training-PIN raw mean and the original case/stratum weights. Fail if it is not
finite or <=1e-12; do not read a holdout to select a replacement scale.

Fit scalar target `t=(FEM.raw-PIN.raw)/r_train` with the existing streamed
weighted linear ridge architecture. Fit-row X means/std and scalar t mean/std
are training-only, weighted as before; std<1e-12 maps to1. Intercept remains
unpenalized. Normalize weighted Gram mass to1; alpha in{.01,1,100}. Reconstruct
t_hat from its standardized prediction before applying the fixed V1 output
map. This is a physical-residual ridge followed by a nonnegative output map,
not a claim to solve a constrained nonlinear least-squares optimum.

Scale division conditions the fit; all selection and primary errors use the
final mapped output in original raw units. No physical-target log loss,
negative penalty, new feature, learned gate, NN, optimizer sweep or FEM-support
weight is introduced. Direct data-only imitation and shared-NN comparisons
are deferred: this test cannot establish superiority to those methods.

## 5. Physical primary metric and early-regime rule

For trajectory u and stratum s, `M(u,s,V)` is full-domain native-area mean
squared error in physical raw units, averaged equally over cycles in that
stratum. Define:

```text
E(u,V) = [M(u,early,V)+M(u,middle,V)+M(u,late,V)]/3
R(u) = sqrt(E(u,V1)/E(u,V0))
PRIMARY Q = max over four outer trajectories of R(u)   [lower is better]
EARLY G(u) = sqrt(M(u,early,V1)/M(u,early,V0))
```

Single diagnostic direction criterion: Q<1, with the early no-sacrifice
condition G(u)<=1 in every outer trajectory. Worst-trajectory aggregation
follows the cross-Umax objective; no good fold or late gain can offset a harmed
fold/early regime. Early preservation is required by the user's intended safe
correction, not a diagnostic vote to rescue raw failure. d/ab are unchanged
between arms, so they do not enter a weighted multi-task score.

`1e-10` in dimensionless ratios is a numerical tie tolerance only: Q must be
<1-1e-10 for a directional gain; G<=1+1e-10 is a numerical non-regression.
Do not label this a practically meaningful margin, statistical confidence or
physical validation. No justified material/reference uncertainty or clinical-
style noninferiority margin exists here; do not invent10% improvement or allow
5% early damage as a convenience. Gains inside tolerance are ties.

Preserve the original unidentified-primary-denominator stop at E(V0)<=1e-24.
An early MSE denominator<=1e-24 is also reported as unidentified: no floor is
added to manufacture G. In inner validation, such a group cannot establish
learned-candidate eligibility; in an outer fold the guard/decision is
inconclusive. Exact control equality is still reported as such.

### Nested selection and fallback (no outer repair)

For each outer fold, use only its three training trajectories in inner
whole-trajectory validation. For each alpha:

1. Evaluate the final mapped candidate over all85112 cells per inner trajectory.
2. Reject alpha if an inner early G>1+1e-10, its denominator is unidentified,
   or any finite/bounds check fails.
3. Among eligible alphas minimize the maximum inner all-cycle physical R;
   exact objective ties choose larger alpha.
4. Select a learned alpha only if its worst inner R<1-1e-10. Otherwise choose
   V0 for the **whole outer trajectory**, before seeing outer values. Record
   fallback explicitly; it is no learned benefit, not a successful correction.

If learned alpha is selected, refit once on the three outer training cases.
No per-cell or per-cycle FEM-dependent switching. If an outer early guard
fails, record it; do not switch that outer result back to V0, retune alpha,
zero only early Delta, drop cycles, or change a loss after seeing the failure.
All four outer results are collected within the fixed diagnostic; no adaptive
extra arm/retry follows. All-fallback means no eligible learned correction;
it must not be described as proof that NN could not work.

## 6. Unique smallest future validation package — NOT approved to execute

- Exactly V0 versus V1; one scalar raw ridge family, three predeclared alphas
  inside nested selection, four outer whole-amplitude folds. Identical inner
  pairs may reuse a fit, with independent training-only statistics. No B1 rerun.
- Reuse the existing admitted data, feature code, stream/guard/report design;
  implement the new target and selector only after design review. R002's old
  code approval does not cover this change.
- Prospective cap stays jointly300s /2GiB peak RSS /100MiB including logs,
  receipts and plotting, Mac CPU4/noGPU for closed-form analysis only.
  No solver/training loop, no expansion, automatic retry or producer fallback.
- Before any fit: finalize a separate Experiment ID/protocol; review exact code
  and data identity; toy-check projection/damage equality, physical-unit
  scaling, heldout perturbation isolation, early-veto/tie/fallback, streaming
  equivalence and full-pipeline working set. Obtain fresh user run approval.
- Save percycle physical error/range/violation summaries, inner eligibility and
  selected/fallback decisions, models and provenance. Stream comparisons; do
  not require all predicted spatial cycles resident or saved.
- Export fixed U0.115/C20 V0/V1/FEM raw snapshots (same fixed example as R002).
  Figures: all four physical R and early G vs1; fixed native C20 fields/error
  with common units/scales. README and exact CSV remain authoritative.
- Pointwise maps do not authorize claims about unmeasured temporal consistency.
  Report this limitation rather than imposing a new monotonicity algorithm.

Outcome routing is fixed before any execution:

| Prospective result | Bounded interpretation | Only next decision |
|---|---|---|
| bad identity/finite/bounds | uninterpretable implementation/input result | repair before interpreting accuracy |
| no eligible alpha/all fallback | no demonstrated safe affine correction | retain V0; review information/representation, no NN escalation |
| Q>=1 or outer early guard worsens | package does not improve without early harm | preserve result; no outer retuning or automatic retry |
| Q<1 and all early guards hold | directional development improvement in physical raw imitation | independent evidence review; not NN/confirmation release |
| cap/incomplete evidence/undefined denominator | inconclusive | freeze; no retry without fresh approval |

No attainable practical margin has yet been established. Thus even the best
outcome only justifies reviewing whether a new representation probe is useful;
it cannot establish process-zone recovery or physical deployment readiness.
Review must specifically challenge whether the worst-fold/early rules are
feasible and whether this single-channel diagnostic is sufficient to answer
the next decision, rather than accumulating more acceptance metrics.

## 7. Independent review request and authority separation

Reviewer: existing chat `多目标优化学习 FEM–PINN Delta`
(`01a12d15-9b60-7280-8248-18386d6ef741`), read-only design review.
Main chat remains sole future implementation/execution owner. No message has
been sent for this revision. The exact send text is prepared separately for
the user's per-send approval; references are local shared documents, no
attachments or remote transfer.

Design approval would permit a later discussion of implementation, not a fit.
Code approval would not replace explicit user run approval. U0.1175/.125,
teacher/physics and multi-objective training remain closed.

Evidence motivating this proposal: `d0_R002_readonly_cause_audit_20261015.md`,
R002 produced at3f78309, audit calculator/record at4167b64. No new numerical
experiment or counterfactual was executed while drafting this revision.
