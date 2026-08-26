# Hard-5 LOAO GNO prelaunch amendment

**Date:** 2026-08-26
**Status:** `V3_IMPLEMENTED__FINAL_POST_COMMIT_REVIEW_PENDING__NO_LAUNCH`
**Supersedes:** the sampling and evaluation clauses in
`hard5_loao_gno_preregistration_20260826.md` and frozen release `6926ea7`.

## Reason

An independent method/code gate found that raw Umax, concatenated statistics,
flat global buckets and PIDL-as-primary could confound the intended
cross-amplitude test. No worker or training job had started. This amendment is
therefore pre-result and does not use any GNO outcome.

## Frozen amended representation and training population

- The fourth protocol feature is fixed by design as `(Umax - 0.12) / 0.01`,
  giving exactly `[-1, 0, 1]` for U0.11/U0.12/U0.13. Any other ID/value pair
  fails closed.
- State and residual normalization uses only cycles strictly before first hit.
  First and second moments are computed per trajectory, then averaged equally
  across the two training trajectories.
- Training origins are strictly before each training trajectory's first hit.
  A rollout may cross first hit, retaining exactly three positive origins per
  trajectory for rollout three; post-hit origins are prohibited.
- Sampling alternates transition/ordinary bucket, selects an eligible training
  trajectory uniformly, then selects an origin uniformly within that
  trajectory/bucket. Gradient calibration is also trajectory-equal.

## Frozen amended evaluation

- All opportunity evaluation is pre-event: every origin is strictly less than
  the held-out first-hit cycle. Event distance remains posthoc reporting only.
- The primary event-centred field population contains exactly three origins
  (`first_hit-3` through `first_hit-1`) and three targets per origin. It contains
  exactly nine rows per method for `gno_data`, `persistence`, and
  `constrained_linear`, at identical origins, targets and the full native FEM
  domain. Constrained linear repeats the latest observed physical increment
  under damage/history irreversibility, fatigue non-increase and field bounds.
- Within each seed, field metrics are reduced by the median across the nine
  event-centred rows; fold summaries are the median across three seeds. The
  primary field estimand is U0.12, an interpolation because training uses the
  two endpoints U0.11 and U0.13. GNO must beat both controls on derived-active
  log-MAE and absolute FEM-p99 IoU, and its absolute support-area ratio must lie
  in `[0.5, 2.0]`.
- The transition population contains exactly the same nine origin/target pairs:
  three negative and six positive rows per seed. Each fold passes transition
  only when seed-median recall is at least `4/6` and seed-median false warnings
  are at most `1/3`; at least two folds must pass. Overall PASS requires both
  the U0.12 event-field gate and this transition gate.
- U0.11 and U0.13 are endpoint-extrapolation secondary evidence and cannot be
  pooled to rescue or overturn the U0.12 primary verdict.
- The single matched-cycle GNO/control table is a secondary diagnostic and is
  not the field primary gate. PIDL remains a mapped, timing-unverified secondary comparison. Its values are
  parsed only after training and it never enters optimization, model selection,
  or the aggregate primary gate. Its frozen bytes are hash-verified preflight.

## Frozen aggregation and stop rules

The aggregate analyzer and its negative tests are direct hashed dependencies of
the matrix lock. It requires exactly nine unique fold/seed jobs, complete and
archive-verified receipts, exact payload/manifest/provenance hashes, finite
metrics, fixed fold classes and exact primary/secondary method sets. Missing,
duplicate, non-finite, hash-mismatched or role-mismatched inputs fail closed.

The v3 release is acyclic: a tracked commit contains the code and matrix lock;
only after that exact commit passes independent review may an external,
untracked `RELEASE_AUTHORIZATION.json` bind the reviewed commit, matrix SHA,
dataset hashes, exact nine-job list, producer and claim boundary. The runner
requires the authorization file plus its externally computed SHA before it
creates an output directory. Each job copies that authorization and binds it
through runtime provenance, run manifest and completion receipt. The analyzer
requires exact equality across all nine jobs, the exact held-out complement,
the frozen pre-hit/statistics/sampling contract, and an exact 14-file payload
allowlist. The completion receipt is excluded from its own payload hash map.

The old `6926ea7` launch packet is superseded and must never be reused. Any
future execution requires a fresh v3 run ID and fresh output/archive roots.

No training may launch until targeted tests, real-data checks, refreshed code
and matrix hashes, a clean pushed commit, live Taobo CUDA/ownership checks, and a
second independent review all pass.

## Claim boundary

The result remains processed GRIPHFiTH archive imitation only:
`teacher_qualified=false`, `damage_fixed_point_gate=fail`,
`physics_loss_weight=0`, and `physical_validation=false`. A pass is not physical
truth, a calibrated warning system, a road forecast, or a Bayesian posterior.
