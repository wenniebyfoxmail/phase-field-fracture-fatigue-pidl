# S04-E011-S2SO/r1 — separate joint sum and outer displacement stopping

This dated diagnostic amendment preserves all prior S04-E011 verdicts. Question:
at the same native FEM c1s2 predecessor/start/predictor, fixed fresh, constrained
damage, inner u1e-8 and inner d4e-6, does joint-sum or outer-u stopping account
for the previously observed 55.89610% active-field contrast? Synthetic C1
numerical-control diagnostic; no physical/teacher/multicycle qualification.

## Cheapest decisive test and source identity

Use exact stop-policy prefix replay, not a new FEM solve. Source Run
`pf_s04e011_s2uj_20261017_v1`, producer commit
`383a77827d3f60be6bcc0326c6923451df94a96d`, retrieved 97 files/1716819024 bytes;
source evidence commit72d539a. Recheck complete retrieval hashes/sizes and the
prior independent-review identity. The only changed values are stopping
thresholds. Inspect exact retrieved controller/case/stop/mechanical/phase
sources: joint_tol/outer_u_tol must affect only the post-complete-block stop
decision and its diagnostic scalars, never a direction, inner solve, raw input,
history, predictor or budget. If this condition fails, do not execute replay;
prepare an independently reviewed fresh producer diagnostic instead.

Source U1J1 contains all actual complete outer1..19, before its first joint
acceptance. U1J0 is an independent native first-block anchor. Verify identical
predecessor, start, predictor and first complete u/d/raw/Ru/Rd/history234.
For every used source point, independently recompute native Q4/2x2GP raw,
Ru, feasible Rd and history234 from frozen prehistory and bounds. Preserve
86,756nodes/86,408Q4, AT1/Amor, E1,nu.3,ell.01,Gc.01,alphaT.5,eta0,native p2,
Udisp=.05999988. Reuse the source input/material/operator and field audit
helpers; no solve, update, interpolation, history commit or next substep.

## Four policies

- S0 joint sum4e-4; S1 joint sum4e-6.
- V0 outer u4e-4; V1 outer u1e-8.
- C(S,V)=max((freshRu+freshRd_feasible)/joint_tol, freshRu/outer_u_tol).
- Accept the FIRST actual complete point with C<=1, mandatory outer>=1.
  Initial outer0 remains observation-only. Replay the original exact-stagnation
  and assembly/outer budget stops as well; never extend beyond an observed
  point, impute a missing endpoint or call a failed inner trial complete.
- Source caps20 complete outer/250mechanical+250phase, inclusive observations,
  unchanged. Source accepted endpoint provides an upper observed horizon,
  not permission to extrapolate. Missing first crossing => inconclusive cell.

These are derived policy endpoints on an actual native path, NOT four freshly
executed Windows arms. If only stopping thresholds change and no earlier
policy/stagnation/budget exit exists, deterministic prefix invariance identifies
the counterfactual endpoint exactly within this recorded numerical path.
Source controls/source policy_C remain immutable; derived C has its own table.

## Estimand and outcome map

Report all four first-stop indices, Ru/Rd and each normalized stop component,
actual u/d changes, GP/Jacobian weighted active-field conditional contrasts.
Keep the original independently replayed S2DJ00 scale_reference norm for
55.89610%; new strict-phase first-block baseline norm gives75.72134% for the
same vector. Scalars use unaveraged GP values; Q4 weighted cell means only for
display. Evaluation unit is this single FEM c1s2 PRE-COMMIT path, not a cycle
sample; no uncertainty/generalization estimate is manufactured from outer count.

This is a descriptive attribution test with no fitted dominance threshold.
If one tightened gate alone reproduces the strict endpoint and the other does
not, report that conditional distinction. If BOTH singleton-tight policies
produce the same endpoint, report redundant sufficient stopping restrictions
on this path: no unique dominant gate and no50/50 physical attribution.
Neither endpoint norm nor nonlinear L2 gaps are additive causal percentages.
If both singleton policies miss or select distinct endpoints, report them and
the actual residual/budget bottleneck; do not add budget or rescue an arm.

## Review, execution and minimum evidence

Independent read-only exact-code/protocol/source review before claim-bearing
analysis. Offline Mac evaluation only, no training/native FEM solve, no SSH
launch or remote mutation. Fresh analysis Run ID
`pf_s04e011_s2so_replay_20261017_v1`; record analysis commit, source Run,
command/runtime/timestamp/PID and explicit inherited producer provenance.
Tests must distinguish separate S/V crossings, mandatory complete block,
threshold equality, and missing horizon without imputation.

Required: source-only dataflow certificate, full retrieval verification,
fresh frozen-state native replay, exact-prefix identity, policy/crossing and
conditional-field CSV/JSON, README_analysis, at least one decision plot with
both thresholds/first crossing and one exact endpoint field comparison,
sidecars and rendered inspection, independent numerical/narrative review.
Update compact result/manifest, experiment/track/registry then frontier;
mesh对齐.md plus its one current Roadmap line. Copy selected PNGs into vault
attachments/S04/2026-10-17 and embed with source/Run caption.

The next decision is whether the strict path is controlled by one gate or
whether separate tolerances coincide in their selected path prefix; a redundant
result does not license deleting either check in other states. No c83/newNN/
120-cycle, fatigue-f<1, physical truth, unique equilibrium or teacher claim.
Spatial/Carrara alignment still leaves committed-f versus trial-f and joint
Deep-Ritz versus staggered/Picard differences.
