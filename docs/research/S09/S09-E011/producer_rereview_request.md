# S09-E011 focused producer rereview

The numerical objective, fixed pairs, `gamma_R=4096`, zero-step A002 result,
two-arm budget and criteria are unchanged from commit `0234c689`. This rereview
is limited to the five execution-closure findings in the first review.

## Implemented repairs

1. The clean-tree check covers the full `source/` dependency closure plus the
   E011 runner, protocol and run config. A temporary Git regression test dirties
   inherited `s09_e009_four_arm.py` and proves rejection.
2. Shared success rereads canonical per-arm receipts and on-disk logs, checks
   500 train/gradient rows and all seven evaluations, reruns the frozen E010
   evaluation validator, reloads checkpoint semantics and recomputes every
   declared hash. The producer now writes and hashes an amplitude trajectory,
   all-cycle common-scale reference/control/ranking delta-d figure and raw field
   arrays before it can publish success.
3. Optimizer steps increment immediately after `AdamW.step`; logged steps,
   evaluation coverage and checkpoint publication remain separate. An arm
   receipt-close exception carries current progress. Attempt roots and an
   admission-start record are created before model/audit work. Any later failure
   writes `failure_receipt.json`, whose documented precedence supersedes a
   success-looking receipt left by an interrupted close.
4. The CLI consumes the canonical run config and protocol. Their SHA256 values,
   exact code/output/archive roots, `GPUServer8`, `CUDA_VISIBLE_DEVICES=5`, and
   the physical GPU UUID are frozen and checked. The executing repo root must be
   the exact module tree.
5. The one-hour deadline is checked before and after evaluations, zero-step
   audit, checkpointing, field reconstruction/plotting, evidence hashing and
   both archive/output success publication steps.

The misleading diagnostic field name was changed from
`rank_margin_derivative_along_displacement` to
`ranking_loss_change_along_displacement`. The protocol also states that A001 is
an immutable historical v1 STOP and is not retrospectively relabelled by v2.

## Validation

- `python -m py_compile` passed for the E011 producer, objective and runner.
- Focused E011 suite: 11 passed.
- E009/E010/E011 regression selection: 78 passed.
- `git diff --check` passed.

Requested verdict: `PASS_EXACT_COMMIT` or a concrete remaining blocker. A pass
authorizes only the already-approved single Taobo run; it does not authorize a
retry, parameter scan, new head, fresh holdout or broader scientific claim.
