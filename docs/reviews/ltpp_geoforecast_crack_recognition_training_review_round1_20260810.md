# LTPP non-destructive recognition training review, round 1

Date: 2026-08-10  
Reviewer decision: `REVISE_BEFORE_TRAINING`  
Training authorized: `false`

## Reviewer disposition

The exact freeze and no-fit receipt were accepted as sufficient for the method,
input, target, architecture, and evaluator. The reviewer found only two
remaining execution-level blockers before the first optimizer step:

1. freeze and provide the SHA-256 of the exact Taobo training runner;
2. make the runner fail closed before every optimizer step unless it verifies
   the approved freeze/static-source/no-fit identities, Taobo producer,
   six folds, 37 maps, seven zero-crack IDs, frozen hyperparameters and
   threshold, final-epoch-only rule, and absence of any prior partial or
   completed attempt.

The reviewer further required an immutable one-use run ID or attempt receipt so
that a crash, failed gate, poor visual result, or partial training cannot trigger
an automatic restart, fold rerun, rescue fit, or reuse of the same authorization.

## Local decision

Adopt both requested blockers exactly. Implement one hash-addressed runner and
an atomic, permanent authorization claim created before the first optimizer
step. Do not train until the same reviewer explicitly returns
`APPROVE_ONE_TAOBO_TRAINING` for that runner hash.

Claim boundary remains current-map recognition on the frozen scanned-form
carrier only.
