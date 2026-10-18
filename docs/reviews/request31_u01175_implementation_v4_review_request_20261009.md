# Request 31 U0.1175 implementation v4 re-review request

## Requested verdict

Perform a read-only review of the exact immutable v4 candidate and return one:

- `PASS_REQUEST31_U01175_IMPLEMENTATION`
- `MODIFY_AND_REREVIEW`
- `FAIL_HOLD`

This review cannot launch FEM. Do not create an approval JSON unless the exact
v4 manifest passes. Even a PASS only permits a fresh, nonce-bound production
preflight; the long run remains separately gated.

## Why v4 exists

Independent review returned `MODIFY_AND_REREVIEW` for v3. The scientific scope
was not changed. v4 only repairs:

1. actual production path precedence after the canonical producer re-adds its
   parent `Sources` path;
2. exact approval binding to status + manifest + frozen run ID;
3. shared UUID nonce, UTC ordering and a 15-minute preflight freshness limit;
4. complete raw review evidence rather than hash summaries alone.

v3 is superseded and cannot be approved.

## Frozen scientific and parent identity

- Umax: exactly `0.1175`.
- Run ID: `hard5_u01175_stage0b_43d36a6de8a9431a803a17ad019a5bb9`.
- first-hit search: c1--c160 only.
- no hit through c160: right-censor and stop at c160.
- hit at or before c160: exactly three confirmation cycles, absolute cap c163.
- parent commit: `862992a60edc7f59335365beacb5c71fc8592a7a`.
- parent snapshot:
  `C:\q4runs\request31_phaseA_snapshots\hard5_stage0b_862992a60edc7f59_b5c39464cd4091f6`.
- parent manifest SHA256:
  `33443ef261ae529c6f57814d518fc4a5c905d94286bf835a83a06cd9733d522c`.
- post-test parent state: exact commit, dirty count 0, same manifest SHA256.

Physics, mesh/order, state0, MEX binaries, tolerances, update order and Contract
A/B remain inherited and unchanged.

## Exact v4 candidate

- Windows root:
  `C:\q4runs\request31_u01175_derived_snapshot_20261009_v4`
- files covered: 15, excluding the manifest itself
- manifest SHA256:
  `72fbb67d9e052c5b1ee451c80e3ad82224e4a1e31386510e7f588048e55e49ce`
- diff-contract SHA256:
  `13ab323962e674d0ffc4f5c2553c88bd392da46d3bdc7a5e1cc569b2fdb18f05`

The complete candidate and raw evidence are available locally at:

`local_archive/experiments/S04-E016/request31_u01175_implementation_review_20261009_v4/`

Review these original files, not only this summary:

- `request31_u01175_derived_snapshot_20261009_v4/DERIVED_SHA256SUMS.txt`
- `request31_u01175_derived_snapshot_20261009_v4/diff_contract.json`
- `request31_u01175_implementation_review_20261009_v4/implementation_test_receipt.json`
- `request31_u01175_implementation_review_20261009_v4/validate_only.stdout.log`
- `request31_u01175_implementation_review_20261009_v4/validate_only.stderr.log`
- `request31_u01175_implementation_review_20261009_v4/powershell_gate_test_receipt.json`
- `request31_u01175_implementation_review_20261009_v4/powershell_gate_tests.stdout.log`
- `request31_u01175_implementation_review_20261009_v4/powershell_gate_tests.stderr.log`

## Path-precedence repair

`run_request31_u01175` injects `run_request31_u01175_producer` into the
unchanged canonical case runner. The wrapper preserves the canonical
`static_state` capture callback but first calls
`request31_reassert_event_policy`. This callback occurs after the canonical
producer's parent-path initialization and before fatigue cycling. It places the
v4 `Sources` directory first and fails closed unless `which` resolves exactly:

`C:\q4runs\request31_u01175_derived_snapshot_20261009_v4\Sources\+phase_field\+audit\evaluate_penetration_event.m`

The no-solve regression reproduces the canonical producer's path-addition
order, verifies that the parent evaluator initially wins, invokes the same
reassertion helper, then verifies that the exact v4 evaluator wins.

## Authorization and preflight contract

Approval must contain exact:

- `status = PASS_REQUEST31_U01175_IMPLEMENTATION`
- `derived_manifest_sha256`
- frozen `run_id`
- canonical UUID `launch_nonce`
- non-future UTC `reviewed_at_utc`

The executable preflight writer copies the same nonce and records exact
manifest/run ID, non-future UTC `checked_at_utc`, zero MATLAB count, absent
output root, free bytes and the unchanged `30870077440`-byte gate. The launcher
requires:

- all status/manifest/run-ID/nonce fields match;
- `checked_at_utc >= reviewed_at_utc`;
- preflight age no more than 15 minutes;
- neither timestamp is future;
- receipt and immediate live process/output/storage gates all pass.

## Validate-only results

MATLAB implementation tests: **11/11 PASS**.

- receipt SHA256:
  `ee210ae75a9f8f89a3b00739aa5c3e53bac47f97a3ad006fa055da00e84251a6`
- stdout SHA256:
  `4916c7ab349ae0149ca8958596cc458e89f171b6c63423df4d7d063c4600ee42`
- empty stderr SHA256:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

PowerShell authorization tests: **10/10 PASS**. They include valid acceptance
plus rejection of approval wrong/missing run ID, missing/expired/future
preflight timestamp, wrong preflight run ID, wrong nonce, preflight earlier
than approval, and future approval.

- receipt SHA256:
  `ba695395e9f3c32a86077c07b5bcfad3e2209e4186dae7a77e28fcf76d22959c`
- stdout SHA256:
  `92709a9348a3b01a859d346a7d47e34909115f826351fa41a38f71867a0c0d77`
- empty stderr SHA256:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

No solve or c1 smoke ran. Scientific payload created: false. Final live state:
MATLAB 0, production output absent, free bytes `34001334272`.

## Reviewer questions

1. Does the wrapper reassert the exact reviewed evaluator at a point that is
   genuinely after all relevant parent path mutations and before event use?
2. Does the regression test reproduce the material production path sequence
   without starting a solve?
3. Are approval and preflight bound to status, exact manifest, exact run ID,
   one nonce, ordered UTC timestamps and a 15-minute freshness window?
4. Does the launcher repeat volatile process/output/storage gates immediately
   before spawn?
5. Is any behaviour outside the permitted implementation delta changed?

If passing, cite manifest SHA256
`72fbb67d9e052c5b1ee451c80e3ad82224e4a1e31386510e7f588048e55e49ce`
and the frozen run ID in the verdict. Do not launch from the review itself.
