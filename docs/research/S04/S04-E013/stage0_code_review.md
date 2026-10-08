# S04-E013 Stage 0 Code Ready review

## Review of commit 913bd479b1eeb1b2b1f3390b5d1d0df342790ab7

Date: 2026-10-08. Reviewer: ChatGPT Pro, read-only supplied-evidence review. The reviewer did not access the repository or independently recompute the archive.

Verdict: `NO-GO` for the combined producer approval. No blocker was identified for the c60 conditional UV producer. The paired exporter had two blocking identity gaps:

1. labels and file existence did not prove that network/current/prior files belonged to the locked aaf13fd run and had post-fit/post-commit accepted-state timing;
2. step 424 was labelled as the own first event without fail-closed evidence for first occurrence and completion of the original three subsequent confirmation steps.

The review explicitly accepted the c60 s3-history plus original c60s4-active-driver fatigue construction, the step mapping, own `step-1` prior rule, `5e-6` model/checkpoint consistency guard, and the absence of an archived MATLAB bridge for the conditional c60 UV-only reference. It did not authorize candidate training.

## Corrections prepared after review

The exporter now requires and hashes the exact aaf13fd archive settings, mesh, producer source snapshot and production log. It validates the locked native-Q4, eta-zero, physics-only, recovery-offset and five-substep settings. It verifies hashes for the producer runner, training/save-order source, field computation and config inside the source snapshot. Together with filename-to-step hashes in the output manifest, this binds the old files to the recorded save order:

`fit -> recompute current model damage -> commit hist_alpha -> save trained_1NN_<step>.pt -> save checkpoint_step_<step>.pt`.

The exporter now validates the original detector region (`x > 0.48`), rather than inaccurately calling it only `x=+0.5`. The locked production log has exactly one onset at step 424, no reset, and confirmation completion at step 427. The exporter also reloads checkpoints 423--427, recomputes accepted-damage boundary counts, and requires detector metadata `(false at 423; onset 424; remaining 3,2,1,0 through 427)` with at least three qualifying nodes throughout onset and the three subsequent consecutive confirmation steps.

Two negative tests now require a model/checkpoint damage mismatch and inconsistent confirmation metadata to fail closed.

## Runtime reconstruction diagnostic

A Mac CPU reconstruction of c82s4 differed from the archived checkpoint by maximum absolute damage `1.519918441772461e-05` and therefore correctly failed the unchanged `5e-6` guard. A read-only reconstruction on Taobo GPU 0 using the original aaf13fd source, mesh, model and checkpoint produced maximum absolute, RMS and p99 errors all exactly `0.0`. The formal exporter must therefore run in the original CUDA producer environment; the threshold was not relaxed after observing the CPU result.

The corrected commit requires a new exact-commit Code Ready review before either formal producer execution.
