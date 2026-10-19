# Independent code review — implementation v1

**MODIFY_AND_REREVIEW** for exact commit `ed7e2f774861b66cefaef3d67a5455fcab785218`. All17 manifest files verified against committed SHA256; manifest SHA256 `9484a56bbee450f626b68af24949d863385b5ba17aaf9f1818effb85ace56b80`. Scope is supported development library/API, source/audit metadata and proposed complete-method budget, not producer readiness or scientific performance. Frozen design remains unchanged.

## Required bounded fixes

1. **P2 — predictor integer indices:** `source/hybrid_incremental.py:207–209` sends `frozen_array(dofs)`, which coerces int64 to float64. Public predictors using normal integer indexing fail. Preserve immutable int64 and test real indexing.
2. **P2 — initializer identity:** `source/hybrid_incremental.py:204–218,268` allows an unidentified predictor to execute but certifies it as `NN_OFF`; fallback provenance also needs an actual initializer role separate from attempted model ID. Require a nonempty ID before work and record model/fallback/baseline roles explicitly. Exact ed7 algebraic reproduction received float64 DOFs, performed one NN call and returned model_id=NN_OFF.
3. **P2 — complete CPU accounting:** the124wall/1984core-hour proposal includes only120 numerical+4setup/IO, omitting host CPU during12GPU hours. Add an explicit conservative host envelope (e.g.12wall/192core-hours sequentially, totals136/2176) with <=16cores total. Do not silently count parallel host work as free.
4. **P2 — inventory terminology:** `tools/audit_hybrid_labels.py:65` and audit JSON call five seen c1 transitions `independent_complete_trajectories=1`. Separate seen_sequences1 from qualified_complete_trajectories0, preserving five candidate transitions/zero certified labels and old artifacts.

## Core findings and checks

No additional decisive core numerical/state/transaction finding in the supported contract. Reviewed complete nodal lower/box/hard-line handling, exact fixed elimination and active release; Gc/ell=w1 and thickness; final same-u/d/f damage reassembly/KKT and original-force residual; fixed accepted preimage trial history; one proposal and durable digest/version CAS. Old local-QP certificates are not reused after mechanics/f changes. The mock fixed-point test exercises this with >10joint iterations. The transaction correctly distinguishes pre-replace rollback from post-replace CommitUncertain; the future runner must halt and reconcile uncertain commits/crash locks before continuation.

Network features use accepted state plus current-load common predictor and nativeGP feature projections, not future outputs. Frozen/eval/no-grad contracts are present; no trained model was loaded. Existing labels were reviewed through JSON/source only:5known repaired c1 candidates,0new-backend certified labels, all f=1. No MAT arrays were reread. The proposed grouped four-trajectory comparison and NN-off/classical/NN strong baselines are appropriate; budget is explicitly unprofiled/unapproved.

Executed the authorized tests independently: **29passed in0.62s**, exit0. Ran only an additional exact-git-object algebraic predictor probe and manifest hashing. No new scientific arrays, checkpoint/model loading, training, project FEM solve, SSH or GPU work. Parent started v2 edits after initial exact snapshot inspection; later reproductions used ed7 git objects to keep this receipt bound to v1.

AfterR1–R4, focus-review changed source/negative tests/receipts only; no need to reopen the design. Producer readiness still requires exact state/data/operator parity and scientific criterion, qualified labels/model, actual resource capacity, external watchdog and durable recovery/cost runner, authorized execution card and exact runner review. Passing development tests or this review does not prove field improvement, convergence, acceleration, teacher validity or generalization.
