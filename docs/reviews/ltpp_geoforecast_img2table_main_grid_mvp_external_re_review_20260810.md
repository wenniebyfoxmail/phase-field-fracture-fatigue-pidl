# External re-review — LTPP main-grid tooling MVP, 2026-08-10

## Verdict

`APPROVE_TOOLING_MVP`

The same external reviewer re-reviewed the revised, frozen protocol after the prior `REVISE_TOOLING_MVP_BEFORE_RUN` decision. The reviewer reported **no blocking issue** and approved only this sequence:

```text
frozen synthetic suite -> all tests pass -> one real run on eight seen development pages -> candidate/NO_CANDIDATE + purple review + structural metrics
```

## Approved boundary

The approval is strictly for the no-OCR image-geometry diagnostic. It does not approve crop authorization, control extraction, transform fitting, residual calculation, v2 final-control creation or disclosure, the v2 final gate, or 2-D model training.

The reviewer restated that the `20%` aspect and regularity tolerances, `±3 px` intersection tolerance, `0.96` span coverage, and line-length formula are frozen for this experiment only. A result cannot be used to relax them and rerun the same MVP.

Any apparent visual improvement remains `EXPLORATORY_MAIN_GRID_TOOLING_MVP__NOT_QUALIFIED` and cannot alter the v1 terminal negative result.

## Record

The decision was obtained in the named ChatGPT external-review conversation on 2026-08-10. This file records the decision boundary, not a registration result.
