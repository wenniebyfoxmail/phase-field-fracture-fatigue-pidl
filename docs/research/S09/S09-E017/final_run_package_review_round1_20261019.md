# S09-E017 final run package review round 1

Date: 2026-10-19  
Reviewer: ChatGPT Pro, Haofan account  
Reviewed commit: `2a8e29937dacf02110303ce0d3365b98f50efad3`  
Verdict: `E017_FINAL_RUN_PACKAGE_REVISE`

## Reviewed package identity

- Archive: `/tmp/S09-E017-final-run-package-review-2a8e2993-v2.zip`
- Size: `131295` bytes
- Archive SHA256: `0911e40c4d80826b215291cf6fa60503bf424d6ab8e64afef107ac27e076790f`
- Manifest SHA256: `526dd29c657ff9776849e233f36707929f6c9f4e5e8b2b450ba906d07b194820`
- Review conversation: `https://chatgpt.com/c/6ad699fe-97f0-832f-99f9-18f138f206a2`

The reviewer verified the archive and manifest hashes, archive integrity, all
20 manifest item sizes and hashes, and the internal patch/snapshot postimages.
The archive contained no duplicate member, path traversal or symlink. It did
not contain Git commit/tree objects, so the reviewer did not independently
recompute the Git commit identity; this limitation did not affect the REVISE
verdict.

## Blocking findings

### B1 — no real E017 adapter or authorised-path implementation

The wrapper still raises `PermissionError` after the authority check. The
package declares symbols and an `ExecutionAdapter` protocol, but it has no
implementation that can strictly load the B25 checkpoint, map the old
Stage0A model to isolated E017 damage heads, bridge the E017 config to the old
runtime validator, connect A/S/R/P losses through PCGrad to one AdamW step, or
convert the old evaluator output to the E017 evidence contract.

This is the primary blocker. The present `ArtificialAdapter` demonstrates call
ordering only. Its integer counter increments do not establish real Torch,
autograd, AdamW, parameter-freeze or head-isolation behaviour.

### B2 — trainable/frozen isolation and update budget are declarative

The current checks require expected name prefixes but do not reject additional
trainable parameters, empty/incomplete frozen inventories, or empty object-ID
evidence. Adapter-owned counters are only checked as non-negative integers, so
64 callbacks do not prove exactly 64 optimiser steps. Evaluation-side mutation,
post-step frozen-state invariance, the 1800-second wall cap and 20-GiB memory cap
are not enforced at the real operation boundaries.

### B3 — complete evidence validation and retrieval closure are not wired

The producer does not call the reviewed full gradient validator. The fixture
accepts empty `pairwise_geometry` and `projection_log`, and does not record the
withheld F_AMP shape gradient. Raw NA/imputation, latent/effective amplitude and
shape, field arrays, shared-scale figures, trajectories, analysis README and
retrieval verification are not produced by a real path.

Two persistence defects were identified: canonical JSON sorting changes the
decision-vector key order while the validator assumes `A/S/R/P` order, and the
inventory digest returned by `close_inventory()` is ignored rather than bound
to and reread from the completion receipt.

### B4 — first-stop loses the current arm's completed evidence

Metrics and gradients remain in memory until an arm completes all 64 updates.
If F_AMP stops at update 4, its completed updates 1–3 and evaluations 0/1 are
not written, although the receipt reports three completed updates. Generic
exceptions also lose the true arm/update location, and a second failure during
finalisation could obscure the first stop reason.

The repair must persist verified records at explicit completion boundaries,
retain the last complete state, record the exact first reason and location, and
handle finalisation failure without adding retry or resume.

### B5 — review package is not dependency-closed

The reported test set reads
`runner_integration_config_draft_20261019.json`, which was not in the archive.
The declared real import chain also depends on local packet, runtime, model,
physics, multiobjective and E010 evaluator modules that were absent. AST symbol
checks do not prove those dependencies resolve. A revised review package must
include the minimal transitive internal source/config dependencies or remove
unused dependencies; no real scientific assets are needed.

## Positive findings retained

- The tracked config remains disabled and the wrapper fails closed.
- The authority check precedes scientific-module import resolution.
- The evidence writer uses exclusive creation and rejects overwrite.
- The artificial state machine schedules all three arms, 64 callbacks per arm,
  and evaluations at 0/1/4/16/32/64 without retry, resume, budget transfer or
  early selection.
- The submitted local result `111 passed in 0.55s` remains local test evidence;
  the reviewer did not independently run or certify it.

These findings support only the disabled boundary, artificial scheduling
scaffold and partial static validators. They do not support Code Ready for the
real 192-update experiment.

## Local hygiene note

After the reviewed commit, a separate local Ruff check found 71 style findings,
mostly line length plus two type-comparison rules, and `git show --check` found
two trailing blank-line warnings. These do not change B1–B5, but the revised
candidate should close them before resubmission.

## Decision and next gate

Status is `REVISE__NO_EXECUTION`. Do not resolve scientific bindings, read the
packet/checkpoint/FEM arrays, run a model, construct an optimiser, use autograd,
connect to the producer or launch training.

The next gate is a narrow real-head-adapter design amendment. It must freeze:

1. a checkpoint-preserving split of the current joint node decoder so
   D_DIRECT can train damage parameters without changing displacement outputs;
2. the exact shared latent feature supplied to the factorised amplitude scalar
   head and pointwise shape-logit head;
3. zero-step mappings for D_DIRECT, exact B25 amplitude replay for F_AMP, and
   the predeclared epsilon-seeded F_AMP_SHAPE initial shape;
4. the E017-to-Stage0A config bridge and strict checkpoint load rules;
5. real parameter inventories, A/S/R/P-gradient-to-PCGrad-to-AdamW wiring,
   operation-bound counters, failure-safe streaming evidence and
   receipt/inventory retrieval verification.

This amendment must be independently reviewed before a revised real adapter is
implemented. The science mapping, arms, 64-update budget, beta `0.25` physics,
holdout boundary and no-retry rule remain unchanged.
