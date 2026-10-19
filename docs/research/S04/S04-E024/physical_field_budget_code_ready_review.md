# E024-D013 independent Code Ready review — CHANGES_REQUIRED

Reviewed source: `0c7d4584ea8d043ff9744b40d2137823fda7ee47`. Scientific code/design tree SHA256: `c3d24496c575b8e7b82dffd9dfd6def06d8117e3186b3827e13763bef704b87a`. Frozen design: `ecf1cc9f080a12f5579a234ecbc9f55191060e6e`. Review is independent static code/contract inspection plus artificial checks; no source fixes were made.

The core implementation preserves all568 coordinates, producer-dtype head quantization and local raw-network reconstruction, fixed original E023 guard ceilings and cumulative Q centre, all13 actual guards versus the labelled7-guard diagnostic, nonlinear driver/free-force-vector acceptance, ordered9 halvings/3models, supervised phase limits and no-optimizer saved-head replay. No parameter-norm ball or ridge was found. These observations do not resolve the blockers below or constitute scientific validation.

## Required changes

### B1 [P1] Reject nonfinite or malformed report values before certifying complete replay

Location: `SENS_tensile/summarize_s04_e024_field_budget.py:165`.

aggregate checks 13 guard values, but never checks budget_q or regional RMS for finiteness. Python json.loads admits NaN; NaN > eta is false. An artificial replay receipt with budget_q=NaN or strain_background.error_RMS=NaN is accepted and writes COMPARATIVE_FIELD_REPLAY_COMPLETE_NOT_APPLICATION_VALIDATION plus a NaN-containing CSV. The aggregate entry is therefore not fail-closed against unreadable physical budget/metric evidence.

Required: Validate the complete consumed physical-report schema and numeric domain before comparison/output. Reject NaN/Infinity and malformed q/components/region metrics; recompute q/ceiling consistency from recorded component integrals and immutable origin scales, handling explicit zero-scale semantics. Add negative tests proving no summary/complete receipt is emitted.

### B2 [P2] Bind replay evidence and enforce coherent integer compute counts

Location: `SENS_tensile/summarize_s04_e024_field_budget.py:120`.

aggregate trusts replayed_solvers/replayed_trials without nonnegative-integer or per-profile-sum checks, and ignores code_tree_sha256. Artificial receipts with -100 solves/-10 trials per state, fractional totals, profile counts 999 with aggregate counts zero, or a wrong code-tree hash all receive a complete verdict. Replay also does not bind its result to a hash of the numeric receipt/input manifest; matching source_commit text alone is insufficient to detect stale/mixed evidence.

Required: Validate exact state/profile schema/order; nonnegative integer per-profile and total counts within 3 solves/27 trials per profile, 12/108 per state and 36/324 total; require totals to equal profile sums and validated stop/accepted-step structure. Bind numeric and replay records to the current reviewed code tree and immutable numeric receipt/input-manifest hashes; verify those links before aggregate completion. Add malformed/stale-identity/count tests.

### B3 [P2] Persist and replay branch-change diagnostics for every visited trial

Location: `SENS_tensile/s04_e024_field_budget.py:269`.

The frozen plan line105 requires branch changes for every visited candidate. Trial events store coefficients, guards/Q, gains, mapping and timing, but no tensile/compressive GP branch-change diagnostic. physical_report computes branch_changed_GP_fraction only for original/final/historical reports, leaving rejected/intermediate visited heads without the required saved branch evidence.

Required: Emit a compact actual-field branch-change diagnostic for every visited quantized trial, including rejected trials, relative to the declared fixed origin (and current iterate if useful). Recompute and check it during no-optimizer replay; include a synthetic branch-changing rejected trial and tamper test. No extra real candidate or scientific computation is needed.

## Checks actually performed

- Independent rerun:49 passed,3 existing SciPy/NumPy NNLS matmul warnings retained. The full568 artificial known-solution check took0.8933s/11 iterations; observed process peakRSS422084608bytes. This is fixture cost, not a production estimate.
- Six additional pure artificial receipt probes reproduced the aggregate acceptance defects. Their passing pytest assertions mean the defects reproduced, not that the receipts are valid.
- Synthetic/log source and hashes are recorded in the JSON report. Logs: `nontraining_6.log` and `nontraining_7.log` under the existing physical_field_budget_code_ready_v1 local archive. Probe source and the append-only attempt-ledger snapshot are preserved there.
- Shared nontraining attempt ledger including earlier failures and this review: 19.996175s of300s. No warnings or failed attempts were deleted.

## Authority and next action

`scientific_execution_authorized=false`. No real endpoint, real NN/FEM forward, three-state head solve, optimizer training, SSH, installation, upload or push occurred. Real conditioning, native full-domain runtime, benefits and application tolerance remain unknown. Preserve this initial CHANGES_REQUIRED report, repair the three findings, then obtain focused exact-source re-review. A later Code Ready PASS would still require separate final human approval before scientific execution.
