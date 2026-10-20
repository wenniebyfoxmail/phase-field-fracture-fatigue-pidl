# Independent focused rereview v2 — derivative preparation

- Date: 2026-10-20, Europe/London.
- Channel/reviewer: independent read-only inherited Codex subagent
  `/root/q4_inverse_review`; specific model identity unavailable, not asserted.
- Exact reviewed source/config/tests/audit commit:
  **`c525455cfc53f1bf753b4cbb94ad1a8696181b0e`**.
- Verdict: **REVIEW_PASS**, bounded to C0/C1 derivative preparation.
- Material inspected: full delta from `acb50500`, including regularity contract,
  derivative fixes, tests, supplemental raw audit, inventory and preserved v1.

## Reviewer findings and actual independent checks

The v1 uniqueness/null-mode finding is resolved: nonempty tangent systems require
exact-operator regularity evidence with positive scaling, finite ordered
singular values and prospective absolute/conditioning thresholds, before the
solver callback. The separate linear residual audit is retained. The original
fully damaged counterexample and invalid evidence are regression-tested.

Nominal-switch changes are limited to labeled one-sided mode; strict classical
mode still rejects switches. Both trace directions have finite-difference
coverage. Geometry and operator index/active arrays are immutable.

- Focused suite independently executed: **19 passed in 0.23s**.
- Independent listing: 600 snapshot names and 120 peak files.
- First/middle/final header/scalar spot-check: cycle/substep, commit flags and
  all six required state shapes/dtypes agree with the inventory. This does not
  independently numerically replay all 600 arrays.
- No reviewer writes, primal FEM, stepping, inversion, training, SSH or protected
  reads. No remaining actionable finding within the bounded contract.

## Limits retained

Regularity evidence trusts a separately reviewed numerical provider; the record
alone does not authenticate claimed singular values. Native-size sparse provider
is unimplemented (dense helper limited to256); full-path constitutive/constraint
switching strategy is not yet reviewed. Original E011 snapshots are not repaired
fresh-joint truth. Initial/recovery identity, reaction boundary/sign/timing and
changed-model compatibility remain to be bound before numerical application.

This review does not establish parameter identifiability/recovery, full-path
differentiability, teacher/physical/road validity or any execution authority.
