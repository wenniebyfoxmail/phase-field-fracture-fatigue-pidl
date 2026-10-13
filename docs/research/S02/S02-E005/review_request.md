# S02-E005 Code Ready review request

Status: packet prepared; channel choice pending. No review dispatched or fit started.
Exact code/design snapshot: `c71ea39` on `codex/s02-e005-fatacrack-label-exploration-20261013` (pushed).
Scope: `scripts/s02_e005_fatacrack_history.py`, its three causality tests,
`experiment.md`, `data_lock.json`; external public source CSVs at
`local_archive/open_data/fatacrack_qualification_20261013/` and deterministic
`local_archive/experiments/S02-E005/prepare_v1/prepared.json`.
The committed protocol is normative; `preparation.json` is a compact receipt,
not a changed split or a fitted result. No source coordinates are declared calibrated.

Read-only reviewer should inspect the exact snapshot and independently check:

1. Current/historical feature construction never uses target/future response;
   fixed1000cycle semantics and the999step transition are preserved.
2. All10 official file identities, channel cycles/coordinates and the fixed ROI
   admit exactly379/107 origins, with fit265/74 and evaluation114/33.
3. Fit targets are observable by first evaluation origin; rolling evaluation
   does not refit or use future input, and normalization uses fit prefix only.
4. B0/B1 and M0/M1 share origins, target, split and metric; alpha1, constant-column
   handling, intercept and evaluation output are correct. No tuning, clipping,
   full-trajectory scaler, force-calibration assumption or sample independence claim.
5. Unit checks meaningfully challenge information leakage and gap handling;
   real fit is not accidentally executed during preparation/tests.
6. Result units/labels support only development-exposed published-label diagnostics,
   with two records and shared DIC noise. No physical/road/generalisation conclusion.

Return `REVIEW_PASS`, `MODIFY_AND_REREVIEW`, or `NOT_REVIEWABLE` for Code Ready,
with exact inspected commit, commands run, evidence access and blockers. Do not
edit files, run real fitting, choose additional arms or approve scientific success.
