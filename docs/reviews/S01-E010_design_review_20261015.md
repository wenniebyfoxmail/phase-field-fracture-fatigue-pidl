# S01-E010 independent design review — 2026-10-15

Verdict: design PASS. Reviewer e008_independent_review, gpt-6.1-sol, Medium. Reviewed frozen design commit `202ff7386ebade72a4f41da8f747c10cb6d49ec0`, containing experiment.md, run_config.json and data_lock.json. No design blocking finding. This review covers the design only; no implementation, code PASS, fitted result or execution approval is implied. Read-only numerical support/oracle checks remain pending and are mandatory before fitting.

The single-correction intervention in each three-location fit bank directly measures E003-relative new targets minus lost old targets minus the correction's own admitted FP role. This handles duplicate valid boxes and operating-budget displacement. Original rows remain immutable; the final joint policy must still meet old-hit retention >=95%, netTP>=1 and macro-location recall delta>0 at the same 1FP/image budget. Singleton effects are not additive.

Implementation review requirements:

- Derive FP_c from the same canonical greedy assignment, never maxIoU<0.5: a valid duplicate may be FP.
- Keep fit-only labels, baseline cutoff, scaler and sign-stratum weights separate from held GT and the full-bank diagnostic oracle.
- Process score ties atomically and account for cross-image prefix displacement. Any shortcut must match canonical counterfactual evaluation exactly.
- Equal sign-mass ridge predicts a score under that weighted distribution; it is not a naturally calibrated expected utility. Test the frozen predU>0 decision without claiming calibration or tuning a new threshold.
- Verify positive and negative fit support and the fixed full-bank oracle before any fit; otherwise stop under the frozen rule. They cannot replace the final learned pooled comparison.

At most four 589-parameter linear systems and one learned pooled comparison, within the frozen CPU/time/RSS limits, are reasonable. No solve/fit, learned prediction, SSH, transmission, push or raw pixel access was performed for this review.

Next authorised stage must be requested separately: implement and test this exact design, obtain independent code review, then prepare the exact source-transfer/public-branch/R001 execution approval version. Fresh locations remain sealed.
