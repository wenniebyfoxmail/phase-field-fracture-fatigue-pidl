# S04-E013 Stage 1 exact-commit Code Ready review

Review date: 2026-10-08
Final verdict: `CODE READY PASS`
Reviewed commit: `769396f93ae5258eb984e1585d4274f7990afb11`
External review conversation: <https://chatgpt.com/c/6ac816d7-8430-8329-98bb-a23484959fad>

## Review history

The first exact-commit review of `5767e6c543acc44ca36da339afe51a0276cf5593` returned `NO-GO`. It found the training core consistent with the frozen plan, but identified four evidence-admission blockers:

1. the aggregator trusted stored gate outcomes instead of recomputing them;
2. it did not require the full checkpoint, prediction, receipt and identity package;
3. it did not distinguish malformed evidence as `INADMISSIBLE`; and
4. tests did not cover decision-changing corruption paths.

Commit `769396f93ae5258eb984e1585d4274f7990afb11` closed those paths without changing the states, seeds, architecture, optimizer, budget, checkpoint rule, metrics or thresholds. The reviewer inspected the pinned GitHub sources and returned `CODE READY PASS`, with no new producer-blocking defect in scope.

## Authorized action

The PASS authorizes preparation and launch of only the frozen 12-run Stage 1 Taobo CUDA matrix, using fresh run identities and receipts and the reviewed commit exactly. Formal runs must use the locked four references, three seeds, `/mnt/data2/drtao/.../<run_id>` roots, one explicit GPU, and the runner's final-only evidence package.

## Boundary

The review did not independently execute the reported 37 tests, verify local hashes or run the four reference validations. It did not inspect a Taobo result. Therefore:

- `CANDIDATE_TRAINING_AUTHORIZED = true` for Stage 1 at reviewed commit `769396f` only;
- `SUPERVISED_CAPACITY_PASS = NOT_YET_ESTABLISHED`;
- Stage 2 and all route promotion remain unauthorized;
- `FULL_FEM_REPRODUCTION` and `QUALIFIED_FEM_TEACHER` remain `NOT_QUALIFIED`;
- completed execution, fail-closed aggregation and a separate Evidence review are still required.
