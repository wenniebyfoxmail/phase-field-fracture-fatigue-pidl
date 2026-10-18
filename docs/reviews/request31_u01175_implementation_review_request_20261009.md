# Request 31 U0.1175 implementation re-review request

> **SUPERSEDED — DO NOT REVIEW OR APPROVE.** Independent review returned
> `MODIFY_AND_REREVIEW` because v3 did not prove overlay precedence after the
> canonical production path mutations and its approval/preflight binding was
> incomplete. Use
> `request31_u01175_implementation_v4_review_request_20261009.md` instead.

## Requested verdict

Please perform a read-only implementation review of the exact derived overlay
identified below and return exactly one verdict:

- `PASS_REQUEST31_U01175_IMPLEMENTATION`
- `MODIFY_AND_REREVIEW`
- `FAIL_HOLD`

This review does **not** authorise a long FEM run. A pass only permits a fresh
production preflight bound to the accepted manifest. Production remains
fail-closed until a separate approval JSON and that preflight both pass.

## Scientific scope already frozen

- One interpolation-confirmation trajectory only: `Umax = 0.1175`.
- First-hit discovery is permitted through c160 only.
- No hit through c160 means right-censor and stop at c160.
- A first hit at or before c160 receives exactly three confirmation cycles,
  with an absolute ceiling of c163.
- c161--c163 may confirm an existing hit but cannot create a new first hit.
- Physics, mesh/order, canonical state0, MEX binaries, tolerances, nonlinear
  update order, and Contract A/B capture semantics must remain inherited from
  the frozen parent.
- No U0.115 replay, no U0.125 opening, no second amplitude, and no training.

## Frozen parent identity

- commit: `862992a60edc7f59335365beacb5c71fc8592a7a`
- snapshot ID: `hard5_stage0b_862992a60edc7f59_b5c39464cd4091f6`
- Windows snapshot:
  `C:\q4runs\request31_phaseA_snapshots\hard5_stage0b_862992a60edc7f59_b5c39464cd4091f6`
- parent snapshot manifest SHA256:
  `33443ef261ae529c6f57814d518fc4a5c905d94286bf835a83a06cd9733d522c`
- qualification manifest SHA256:
  `b5c39464cd4091f67abff3944b23acf11a6d2cf7ada4be0e78c2de4c375fa33e`

The canonical snapshot remained clean and unchanged. The amendment is a
separate MATLAB-path overlay.

## Authoritative candidate

- Windows derived root:
  `C:\q4runs\request31_u01175_derived_snapshot_20261009_v3`
- derived manifest SHA256:
  `fbe2b9cc2fb8d71c01b5a58b0af50e09dd6f0084df0873278406992f55e17de5`
- files covered by the manifest: 9 (the manifest file itself is excluded)
- diff-contract SHA256:
  `de3656917d9e073f4fc7412c6cf502ec0077eb69e7eb524b6ce34c5d09f2de60`

Individual file SHA256 values:

| File | SHA256 |
|---|---|
| `diff_contract.json` | `de3656917d9e073f4fc7412c6cf502ec0077eb69e7eb524b6ce34c5d09f2de60` |
| `launch_request31_u01175.ps1` | `4dc662b5f1ba779da52dd6f66c7725eb6a3bba1d976b24e98bdbfe8b402acda5` |
| `parent_lock.json` | `8bdf15462d58cb1a82ebd63fe11d31ee3fc98c65d422c8a1ce0f35a0dac82aa9` |
| `README.md` | `e00b580185872e21a88b5e1d971aff3be41121e2d72090136b934c6b4ecf682e` |
| `Scripts/fatigue_fracture/build_request31_u01175_config.m` | `1680659f92775cbebc9fbc39a3d727f4034fbf390f175b821169ba3c44b308a8` |
| `Scripts/fatigue_fracture/load_request31_frozen_base.m` | `9a4e053425337a255d75d8ec2349fb2ee7d5aae7d62fa2b4edaa686f8198d98a` |
| `Scripts/fatigue_fracture/run_request31_u01175.m` | `2f808b54c957865a3cfdc5b1d16906147f119e68926706fb95e0fb34bbf3958a` |
| `Sources/+phase_field/+audit/evaluate_penetration_event.m` | `c2eb33d216f594ff0b48a6fe614b5856e7bbf24ec4acd4383f82fa4e251d27c5` |
| `Tests/run_request31_amendment_tests.m` | `11e0fdac36a96d3446f40728e25b15e1c5d9360338d4b2f8d2bb4a3758f185e1` |

For the two overridden canonical behaviours:

- canonical builder SHA256:
  `7cfe4e283541a4d0ef292a6ed071015e8aff39df54de54b6b3f9b7431f67a8dd`
- derived builder SHA256:
  `1680659f92775cbebc9fbc39a3d727f4034fbf390f175b821169ba3c44b308a8`
- canonical event-policy SHA256:
  `9558740339d9409c54f73ad69ba00812b007e721fd4e82fd41bc8f3243bf19e0`
- derived event-policy SHA256:
  `c2eb33d216f594ff0b48a6fe614b5856e7bbf24ec4acd4383f82fa4e251d27c5`

## Validate-only evidence

- review root:
  `C:\q4runs\request31_u01175_implementation_review_20261009_v3`
- receipt status: `PASS_READY_FOR_IMPLEMENTATION_REREVIEW`
- passed tests: 9/9
- receipt SHA256:
  `786169461D7662E54AC84DF1E17C3B38578F7D45B79FDBCA551FCB4E1B0C0A52`
- stdout SHA256:
  `9091F0DAB9F527E83C23DE9CE570BF71F1CE1D7E3B5325DD1D6B215F465F1D9C`
- stderr was empty; SHA256:
  `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

The passing tests cover:

1. exact U0.1175 admission and fixed run ID;
2. rejection of any other amplitude;
3. no-hit right-censor/stop at c160;
4. first hit at c160 followed by c161--c163 confirmation and stop at c163;
5. early first hit followed by exactly three confirmation cycles;
6. a potential first hit at c161 being ignored;
7. rejection of cycle c164;
8. retention of Contract A/B and `post_history_commit` timing;
9. MATLAB path resolution to the derived event policy before the parent.

No c1 numerical smoke was run. This omission is deliberate at this review
stage: validate-only plus pure stop-policy tests exercise the complete code
delta without creating scientific payload. If the reviewer finds a numerical
c1 smoke necessary, return `MODIFY_AND_REREVIEW` and state the exact additional
assertion required.

## Superseded candidates

- v1 is quarantined: MATLAB batch-argument quoting failed and it produced no
  valid test receipt.
- v2 is quarantined: seven policy tests passed, but one static assertion
  searched the runner instead of the solver and correctly ended as
  `BLOCKED_TEST_FAILURE`.
- Only v3 and its exact manifest are reviewable or eligible for later approval.

## Reviewer questions

1. Does the derived event policy implement the c160 discovery ceiling and
   conditional c163 confirmation tail without admitting a new late event?
2. Does the fixed builder admit only the preregistered U0.1175 case and run ID?
3. Are the parent/overlay path rules sufficient to preserve the canonical
   physics and Contract A/B timing while overriding only the intended builder
   and event policy?
4. Does the PowerShell launcher fail closed unless approval and fresh
   preflight receipts bind the exact v3 manifest and run ID?
5. Is any material behaviour changed outside the frozen amendment scope?

On `PASS_REQUEST31_U01175_IMPLEMENTATION`, cite the derived manifest SHA256 in
the verdict. A pass does not itself launch MATLAB/FEM.
