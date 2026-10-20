# Independent focused rereview v4 — offline interfaces

- Date: 2026-10-20, Europe/London.
- Reviewer: independent read-only Codex subagent `/root/q4_inverse_review`;
  model identity unavailable and not asserted.
- Exact reviewed code/test/config commit:
  **`fa2e50427c2e48b54d547dd6e4597f5b63628c70`**.
- Verdict: **REVIEW_PASS — bounded offline-interface preparation**.
- Scope: focused `4c0c78b5..fa2e5042` repairs; previous c525455c baseline and
  v3 sparse/source review carry forward, without broad reruns.

## Findings resolved and independently checked

Each sensitivity tape requires a finite copied global material direction at
construction. Omitted per-step parameters reuse it; a changed explicit direction
rejects before solving or committing. Caller mutation cannot change the tuple,
and the public property is read-only.

Strong lower/upper activity now requires the correct signed multiplier margin.
Wrong-sign multipliers outside the declared weak band reject even when broader
primal tolerances admit them. Both lower and upper cases have regression checks.

The reviewer independently inspected the focused delta and ran only the new
interface suite: **18 passed in 0.17s**. No further actionable finding was
reported within this delta. Local focused verification also passed 18 in0.18s.
The unchanged baseline's 19 independently passing checks are reused, not rerun.

## Limits and execution

No reviewer file changes, primal FEM, native-size solve, trajectory replay,
inversion, remote work or protected-data access occurred. Native performance,
bound usefulness, complete-path switch uniqueness, numerical source-state
identity and material recovery remain unverified. The initial/reaction contract
binds inspected source/header evidence; it does not establish whole-array or
cached-versus-fresh numerical equivalence. Review is not scientific validation
or authorization for execution.
