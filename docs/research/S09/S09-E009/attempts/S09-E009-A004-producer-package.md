# Attempt S09-E009-A004-producer-package

- Status: `accepted`
- Created: 2026-10-17T22:54:34+01:00
- Closed: 2026-10-18T00:07:21+01:00
- Type: `implementation`
- Human decision required: False

## Motivation
Implement the reviewed four-arm producer loop, environment resolver, evaluator/evidence writer and one final run card without executing an optimizer step or contacting the producer.

## Trigger
Exact integration commit efeffbfa received RUNNER_INTEGRATION_READY_PASS.

## Current Claim Before Attempt
The no-training runner integration is reviewed, but the producer loop, resolved execution contract and complete evidence writer do not yet exist.

## GPT Pro Advice
- Required: True
- Advice path: `producer_package_review_round3_20261018.md`
- Advice sha256: ``

Round 3 returned PRODUCER_PACKAGE_READY_PASS. Pro independently ran 4 focused tests plus 21 narrow checks and closed both remaining F5 failure-observation issues; the local complete selected suite remained 101 passed.

## Adopted Decision
Accept exact commit bc1309c75a2309e8b5e0fa00d474605a333d0379 as the reviewed S09-E009 producer package.

## Rejected Or Modified Advice
No Round-3 finding was rejected or modified. The PASS is retained as code readiness only.

## Decision Rationale
Local no-training verification passed 101 tests. ChatGPT Pro independently reproduced four focused tests and 21 narrow checks, closed the two residual F5 issues, and returned PRODUCER_PACKAGE_READY_PASS.

## Success Criteria
- Resolved config is exact-identity bound; loop is 500x4 with no budget transfer; evaluator implements the frozen scorecard; writer emits the conditional manifest; local tests use mocks and zero real AdamW steps; exact changed layer passes focused review.

## Failure Criteria
- Any caller-spoofable execution identity
- schedule drift
- hidden optimizer step in tests
- fabricated conditional artifact
- incomplete scorecard/evidence
- or review blocker.

## Code Changes
- add: `source/s09_e009_producer.py` - Add exact-identity resolver, four-arm state machine, frozen evaluator, replay gate and conditional evidence writer
- add: `scripts/resolve_s09_e009_producer_config.py` - Add explicit no-step producer resolver entry point
- add: `scripts/run_s09_e009_producer.py` - Add explicit final-run entry point with execution flag
- add: `tests/test_s09_e009_producer.py` - Add mock-only producer package verification with AdamW.step sentinel
- add: `docs/research/S09/S09-E009/final_run_card.md` - Add the single frozen final preflight launch and interpretation card
- modify: `source/s09_e009_producer.py` - Bind consumed packet identity, keep replay hash diagnostic-only, validate the fixed scorecard, preserve actual failed-forward hard counts, and write checkpoint-bound failure receipts when one common artifact remains unreadable
- modify: `tests/test_s09_e009_producer.py` - Cover resolver round trips, runtime identity, nonfinite replay, nested scorecard consistency, actual inherited fail-fast at evaluation and first update, and persistent single-artifact read failure with zero AdamW.step calls
- modify: `docs/research/S09/S09-E009/final_run_card.md` - Record exact producer review commit and code-ready status while retaining a separate final execution action

## Input Assets
- `docs/research/S09/S09-E009/experiment.md` (frozen protocol; exists)
- `docs/research/S09/S09-E009/runner_integration_review.md` (approved integration gate; exists)

## Output Assets
- `source/s09_e009_producer.py` (producer resolver loop evaluator and writer; exists)
- `tests/test_s09_e009_producer.py` (no-training producer package verification; exists)
- `docs/research/S09/S09-E009/final_run_card.md` (single final execution card; exists)

## Tests
- pass: producer package no-training selected suite - 84 passed in 2.39s; all producer tests used mocks/fixtures, the real E008 packet update-0 evaluator reproduced all five replay scalars exactly, and AdamW.step remained fail-if-called.
- pass: Round-3 exact-candidate no-training suite - 101 passed in 2.27s on exact commit bc1309c75a2309e8b5e0fa00d474605a333d0379; actual predicate regressions cover initial evaluation and first update, with AdamW.step fail-if-called sentinel silent.
- pass: Round-3 focused residual suite - 4 passed, 21 deselected in 0.50s; failed-forward counts and persistent unreadable-artifact fallback both close without optimizer updates.
- pass: Round-3 syntax and whitespace checks - Both checks completed successfully on the exact reviewed candidate.

## Result Interpretation
The producer resolver, four-arm state machine, frozen evaluator and conditional evidence writer are code-ready at the reviewed exact commit. This is an engineering result; no producer run, training or scientific result occurred.

## Claim After Attempt
Exact commit bc1309c75a2309e8b5e0fa00d474605a333d0379 has PRODUCER_PACKAGE_READY_PASS and may enter a separate final execution action.

## Next Action
If final execution is explicitly authorised, use the frozen run card and exact reviewed commit for producer preflight and launch; otherwise do not access SSH, transfer files, train or open fresh holdout evidence.
