---
storyline_id: S04
experiment_id: S04-E016
protocol_revision: v3-resume-equivalence
claim_class: C1
evidence_domain: synthetic
status: frozen_before_execution
producer: CITPC12
---
# Amendment v3: bounded c64/s4 restart equivalence

## One question

Can the exact frozen c64/s3 step checkpoint reproduce the already frozen
c64/s4 post-history-commit state when resumed on the same Windows host, MATLAB
R2025b Update 5, canonical source snapshot, mesh, configuration, and loading
schedule, while explicitly skipping fresh zero-load recovery?

Passing supports only restart-state equivalence for this one state. It does not
complete the trajectory, validate Contract A/B, qualify FEM as a teacher, or
authorize Delta training.

## Frozen identity

- Run ID:
  `hard5_u01175_resume_eq_c64s4_5dc9e99a2fa0456092b68ed5be67543c`
- Canonical commit: `862992a60edc7f59335365beacb5c71fc8592a7a`
- Source checkpoint: c64/s3 `step_checkpoint.mat`, SHA256
  `3605dc9a1eb170e97e33bd64df8661f4263abd97fc6c0f467252ae1e435cfbfc`
- Frozen target: `c0064_s04.mat`, SHA256
  `9c8e6e095e67c206162308d99657bfdb5dbdf241308ea984e2f3bf1caff37b45`
- Allowed information: the frozen c64/s3 checkpoint, canonical configuration,
  code and mesh. The frozen c64/s4 target is used only after candidate capture
  for scoring.
- Origin: c64/s3 post-history-commit. Horizon: one load step. Target: c64/s4
  post-history-commit.

## Validity gates

1. Source, checkpoint and target hashes match the freeze.
2. Output root is fresh and the frozen failed-run tree remains unchanged.
3. Resume loads cycle 64 / completed step 3 with the no-event detector state.
4. Fresh recovery and initial-state emission are forbidden.
5. Exactly one candidate state, c64/s4, is captured; the callback stops the
   solver before s5 or long continuation.
6. MATLAB returns a machine-readable receipt and no target-owned process
   remains.

## One primary criterion

For `d_node`, `history_gp`, `strain_en_degr_gp`, `strain_en_undgr_gp`, and
`u_node`, every field must satisfy both:

```text
scaled max absolute error <= 1e-12
relative L2 error           <= 1e-12
```

State identity, cycle/substep/timing, load metadata, history channel labels,
energy derivation, and detector state must be exactly equal under `isequaln`.
Convergence booleans and iteration counts must be exact; equilibrium and phase
residuals use the same scaled absolute `1e-12` tolerance.

The tolerance is frozen before execution. It is intentionally tight because
the producer, host, runtime, mesh, origin state and one-step operation are held
fixed. No post-result relaxation is allowed.

## Outcome map and stop rule

```text
validity failure        -> INADMISSIBLE; repair the probe only
validity pass + primary pass -> PASS_RESTART_EQUIVALENCE_C64_S04
validity pass + primary fail -> FAIL_RESTART_EQUIVALENCE_C64_S04
missing scored state    -> INCONCLUSIVE
```

Stop immediately after c64/s4 capture. Even a pass does not authorize a long
continuation. It advances only to a separate short end-of-cycle infrastructure
smoke that exercises the safe logger, checkpoint writer and terminal receipt.

## Minimum evidence

- exact candidate manifest and independent implementation review;
- validate-only receipt;
- run receipt with process/runtime identity;
- candidate c64/s4 state;
- per-field comparison JSON;
- compact decision table comparing every primary field with its threshold;
- dated update to `experiment.md`, Windows outbox and Obsidian ledger.

