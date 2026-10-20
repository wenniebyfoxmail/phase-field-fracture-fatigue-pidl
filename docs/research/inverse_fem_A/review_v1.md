# Independent code review v1 — bounded derivative preparation

- Channel/reviewer: independent read-only inherited Codex subagent
  `/root/q4_inverse_review`; specific model identity was not exposed.
- Exact reviewed implementation: `acb505005b7c5f4a8c047b587553ea51b9691aab`.
- Materials: new derivative module, focused tests, raw audit/inventory and
  implementation note; reused mechanical/history/kinematic/damage kernels and
  original backend parameter interface. Five reused files independently match
  `829508617534c6c5febc813899498a31053684df`.
- Actual checks: 16 focused tests independently passed in 0.16s; additional
  manufactured singular-operator check; raw MAT headers and first reaction rows
  in three old cases. No primal FEM/inversion/training/SSH/protected reads or
  reviewer file modifications.
- Verdict: **MODIFY_AND_REREVIEW** for C0/C1 synthetic derivative preparation.

## Finding preserved: P2 implicit derivative uniqueness

At reviewed lines 303–306, `propagate` accepted a solver result by its residual
alone. A fully damaged eta=0 one-Q4 patch without displacement constraints
has displacement null modes. The reviewer produced an operator with entries
around 7.1e-33 where both zero and constant-translation tangents passed for
identical zero source. A small linear residual does not prove uniqueness.

Required fix: explicit trusted regularity/conditioning evidence tied to the
exact scaled reduced operator, plus singular/malformed-evidence regression
coverage and retained residual verification. Fixes and the new E011 raw-tape
inventory require exact-commit focused rereview.

The inspected smooth-branch force/damage/history JVP, explicit E/Gc/alpha_T,
moving lower bound, history propagation and boundary/reaction terms appeared
consistent. This finding is not a negative physical or inverse-recovery result;
no such experiment occurred. Positive rereview, if obtained, is limited to
the prepared derivative layer, not an executable complete inverse pipeline.
