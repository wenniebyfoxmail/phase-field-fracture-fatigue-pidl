# Independent Codex numerical evidence review

Date: 2026-10-13. Reviewer: `/root/s02_e005_code_review`, same selected local read-only Codex channel. Verdict: **REVIEW_PASS for bounded numerical evidence**.

Returned runner and lock match reviewed source commit c71ea395c40e6d8600529b85f153ba4c2422abd0. Returned preparation matches independently reconstructed pre-fit rows. All 147 evaluation rows (F114/FF33), origins, exact horizon, controls and scalers checked.

Reviewer reproduced predictions from returned coefficients without refitting, and verified ridge normal-equation residual norms below 3e−14. MAEs match result.json: F M1−M0 +0.051506626973525885 mm; FF +0.0034857445403997517 mm; equal-record mean +0.027496185756962818 mm. Secant is better than both learned arms in both records. No numerical blocker remains.

The six-panel decision figure correctly displays all evaluated trajectories, increments, errors and primary sign. Exit receipt0 and UTC start/end20:55:49 support successful execution with coarse timing precision.

Local BLAS emitted spurious floating-point warnings despite finite results; reviewer repeated the matrix checks with non-BLAS einsum and floating-point exceptions enabled, reproducing predictions and normal equations without warnings. No real fit, new arm, file edit, remote access or external communication occurred during review.

Supported outcome: negative published-label history-increment diagnostic under frozen v1. Not supported: physical metrology, independent specimens, road transfer, untouched confirmatory testing or universal absence of historical information.
