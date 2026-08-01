# Task 2 Report: Seal Single-Axis Case Configurations

## Changed Files

- `tests/test_toy_road_fem_handoff.py`
- `producer_handoffs/toy_to_road_independent_fem_20260731/FAMILY_INPUT_LOCK.json`
- `producer_handoffs/toy_to_road_independent_fem_20260731/T1_INPUT_LOCK.json`
- `producer_handoffs/toy_to_road_independent_fem_20260731/T2_INPUT_LOCK.json`
- `producer_handoffs/toy_to_road_independent_fem_20260731/T3_INPUT_LOCK.json`
- `producer_handoffs/toy_to_road_independent_fem_20260731/build_toy_road_case_config.m`
- `producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadConfigTest.m`
- `.superpowers/sdd/2026-07-31-toy-road-independent-fem/task-2-report.md`

`PARENT_LOCK.json` was not changed. The family lock reproduces it as the
fixed-parent baseline and preserves the distinct physical-source and
authoritative-analysis-bundle roles and immutable policy.

## RED Evidence

1. `py -3.12 -m pytest tests/test_toy_road_fem_handoff.py -q`

   Output: `6 failed, 3 passed in 0.26s`. Each failure was the expected
   `FileNotFoundError` for the absent `T1_INPUT_LOCK.json`, `T2_INPUT_LOCK.json`,
   or `T3_INPUT_LOCK.json`.

2. `matlab -batch "r=runtests('producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadConfigTest.m'); assertSuccess(r)"`

   Output: the three configuration tests failed with
   `MATLAB:UndefinedFunction: Undefined function 'build_toy_road_case_config'`;
   the two invalid-input tests observed that same missing implementation instead
   of the required `toyRoad:InvalidInputLock`.

3. The MATLAB test suite initially used the unavailable `hash` function. The
   root cause was a MATLAB runtime API gap, confirmed by the exact error
   `Undefined function 'hash' for input arguments of type 'char'`. A minimal
   Java `MessageDigest` SHA-256 check returned the known SHA-256 of `abc`:
   `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`.
   The builder now hashes the raw parent bytes with that available API.

4. After adding the cycle-boundary test, the upper-bound predicate was
   deliberately changed from `cycles > censorCap` to `cycles > censorCap + 1`.
   The MATLAB suite failed exactly at cycle 151 with actual
   `toyRoad:InvalidInputLock` versus expected `toyRoad:InvalidCycle`. The
   correct predicate was immediately restored before final verification.

## GREEN Evidence

1. `matlab -batch "r=runtests('producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadConfigTest.m'); assertSuccess(r)"`

   Output: `Totals: 7 Passed, 0 Failed, 0 Incomplete.`

2. `py -3.12 -m pytest tests/test_toy_road_fem_handoff.py -q`

   Output: `9 passed in 0.04s`.

## Commit

- `feat: lock independent FEM case configurations`

## Self-Review

- The parent file remains immutable; the family lock is hash-bound to its raw
  bytes and must be structurally identical before a case can be built.
- Each case lock has exactly one declared and allowed primary axis, a
  machine-readable parent/candidate diff, c150 cap, and locked values for T1,
  T2, or T3.
- The builder rejects unknown case IDs, parent-hash mismatches, second-axis
  changes, malformed locked values, and non-integer or out-of-range cycles.
- The returned configuration carries parent physics, physical-source role,
  authoritative analysis-bundle role, immutable policy, event contract, five
  substeps, c150 cap, and a cycle-amplitude function. No FEM solve is invoked.

## Concerns

- MATLAB in this environment does not provide `hash`; the implementation uses
  Java `MessageDigest` for SHA-256 instead. This is covered by the MATLAB suite.
- No computational FEM experiment was run; only JSON/configuration validation
  tests were executed, sequentially, after confirming no `matlab` process was
  active.

## Fix Round 1: Reviewer Findings

### RED Evidence

1. `py -3.12 -m pytest tests/test_toy_road_fem_handoff.py -q`

   Output: `2 failed, 8 passed in 0.28s`. The T1 test raised
   `KeyError: 'a0_over_L'`; the family-baseline contract lacked the approved
   `a0_over_L: 0.5` value.

2. `matlab -batch "r=runtests('producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadConfigTest.m'); assertSuccess(r)"`

   Output: T1 raised `MATLAB:nonExistentField` for `a0_over_L`. The four
   synchronized mutations of family geometry, `Gc`, `Pi_ratio`, and loading
   baselines, plus the injected second candidate axis, each failed because the
   builder did not throw the required `toyRoad:InvalidInputLock`.

### GREEN Evidence

1. `py -3.12 -m pytest tests/test_toy_road_fem_handoff.py -q`

   Output: `10 passed in 0.04s`.

2. `matlab -batch "r=runtests('producer_handoffs/toy_to_road_independent_fem_20260731/tests/toyRoadConfigTest.m'); assertSuccess(r)"`

   Output: `Totals: 12 Passed, 0 Failed, 0 Incomplete.`

### Implementation and Self-Review

- T1 now seals parent `a0_over_L: 0.5` and candidate `a0_over_L: 0.625`, in
  both the candidate and machine-readable diff, alongside tip `[0.125, 0]`.
- Family axis baselines are exact-schema validated: approved geometry, parent
  `Gc`, approved `Pi_ratio`, and the parent cap/amplitude loading block. The
  builder creates unchanged geometry, Pi ratio, and loading defaults directly
  from approved constants or `PARENT_LOCK.json`, never from mutable family
  values.
- Case diff and candidate structures now enforce exact field names at every
  level. A second axis or any additional axis-specific field is rejected with
  `toyRoad:InvalidInputLock` even when its duplicate machine-readable diff is
  altered to match.

### Concerns

- The MATLAB SHA-256 implementation continues to use Java `MessageDigest`
  because this MATLAB runtime lacks `hash`; the focused MATLAB suite remains
  green. No FEM computational solve was run.
