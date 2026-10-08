# S04-E013 coverage decision

Status: Stage 1 planning passed and the supervised runner is implemented; candidate producer training remains blocked pending exact-commit Code Ready review.

The FEM side is ready for the native-fidelity matrix: S04-E010 contains c20/c60/c82/c83 at s2/s4/s5 with qualified state identity and the correct accepted prior. The read-only PIDL control side now has the matching c20/c60/c82/c83 x s2/s4/s5 matrix plus the c85s4 own-event row, including nodal displacement and native-Q4 mechanism fields. This closes the paired-control asset gap while preserving the rule that late-state evidence cannot substitute for early or middle states.

The strict UV route now has an admitted conditional c60 result in addition to the existing c20, c82, and c83 assets. The c60 admission is displacement-only with accepted damage, prior and fatigue frozen. The paired eta-zero control export is registered as `PAIRED_CONTROL_ASSETS_READY`. These asset admissions do not by themselves close Stage 0 scientifically or authorize candidate training.

The proposed algorithmic sequence is therefore:

1. close c60 strict-reference and paired control-export gaps;
2. run a supervised displacement capacity ceiling on the admitted fixed-damage states;
3. run the same architecture and evaluation under an unsupervised fixed-damage UV objective;
4. only then run a free trajectory against the 12-state native-fidelity matrix.

This order identifies the first failed capability and prevents large late-stage differences from obscuring early-state failure. It also preserves the S04-E012 boundary: the UV-derived reference is not a damage/history teacher and cannot support full FEM reproduction by itself.


## Independent design review disposition

The review bound to commit `4c9291031a26e2ec04d057c43e4c9f7498aff091` returned `NO-GO`. It accepted the two-axis structure and the c20/c60/c82/c83 x s2/s4/s5 scope, but required executable information-separation, null/support metrics, field-wise paired promotion, event/export semantics, and distinct Stage 0 readiness states. Those rules are now instantiated in the amended contract. Preparatory c60-reference and exporter implementation is allowed; Stage 0 closure and candidate training remain blocked pending independent re-review and actual asset closure.

## Stage 0 implementation update

The first c60 attempt (`S04-E013-R001-c60-uv`) failed in the PowerShell launcher before producing a summary. The launcher-only retry (`S04-E013-R002-c60-uv`, Condor `82.0`) completed with exit code 0. It reduced `rho_u` from `1.2857766593003994` to `4.816938699465251e-11`, with displacement mass RMS / `Us = 6.872576107117729e-4` and native-Q4 strain relative L2 `4.748005459472791e-3`. All retrieved arrays are finite; locked input identities, fixed-state invariants, zero training/damage/history updates, and weak-gradient agreement passed. Damage was not solved and its diagnostic did not improve, so this result supports only a conditional c60 UV reference and retains `full_teacher=NOT_QUALIFIED`.

The first combined Code Ready review found no c60-producer blocker but returned `NO-GO` for the paired exporter because accepted-state lineage and step-424 first-event/confirmation evidence were incomplete. Commit `19a5c13d5dcc2d1888528621dc6ff459c59dbe3d` fail-closed binds the exact aaf13fd settings, mesh, source snapshot, log and save order; hashes model/current/prior files; and independently rechecks steps 423--427 against the production detector. The renewed exact-commit review returned `Code Ready PASS` with no blocking corrections. Taobo run `S04-E013-R003-paired-export` produced all 13 rows; remote and post-retrieval local verification agree on hashes, finite arrays, zero model/checkpoint damage mismatch and event metadata.

## Stage 0 Evidence review disposition

The external supplied-evidence review bound to documentation commit `165afdf` and producer commit `19a5c13d5dcc2d1888528621dc6ff459c59dbe3d` returned `Evidence PASS`, with no blocking correction for the requested asset admissions. It admitted c60s4 only as `CONDITIONAL_UV_REFERENCE_ADMITTED` and registered all 13 R003 rows as `PAIRED_CONTROL_ASSETS_READY`. The review did not independently access or recompute the archive.

Candidate training, candidate Evidence Ready, route promotion and Stage 0 scientific closure remain separate gates and are not authorized by this verdict. `FULL_FEM_REPRODUCTION`, `QUALIFIED_FEM_TEACHER` and c60 `full_teacher` remain `NOT_QUALIFIED`. Full boundary and review link: [stage0_evidence_review.md](stage0_evidence_review.md).

## Stage 1 authorization update

The first training-plan review returned `NO-GO` and required a narrower finite-budget reproducibility estimand, a non-duplicated mass-sampling loss, separate fit/residual interpretation, and deterministic implementation constants. Those changes were frozen before implementation. The second review returned `PLAN PASS`, authorizing the runner and local non-training checks only.

The implementation uses four states by three seeds, separate networks, exact reference hashes, a final-checkpoint-only rule, and a 12/12 conjunctive gate. A valid failure is `SUPERVISED_CAPACITY_FAIL_FIXED_PROCEDURE`, not proof of theoretical architectural insufficiency. All four reference files pass the local hash, shape, boundary, Q4-strain and reference-residual validation. Mac training was not run.

The next gate is independent exact-commit `Code Ready` review. Until it passes, `CANDIDATE_TRAINING_AUTHORIZED=false` and no Taobo producer run may start. Full contract and external disposition: [stage1_training_authorization.md](stage1_training_authorization.md).
