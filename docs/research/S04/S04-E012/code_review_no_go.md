---
review_type: independent-code-ready-review
reviewer: ChatGPT Pro
reviewed_at_local: 2026-10-08
source_chat: https://chatgpt.com/c/6ac3d374-50b4-83ed-893c-02fa7d0a71f4
reviewed_commit: 389ca261b374e0a8af5010f65a596f569aa48f38
verdict: NO-GO
---
# S04-E012 independent Code Ready review

This is a normalized record of the review of the supplied implementation contract. The reviewer did not read the repository or archives and did not recompute the arrays.

## Verdict

The reviewed commit is **Code Ready NO-GO**. The UV formula, zero-based blocked-to-interleaved mapping, C-order force flattening, mass repetition, `rho_u` scale, c82/c83 hard-KKT provenance asymmetry, and narrowly scoped `RuntimeWarning` handling were accepted. The verdict did not claim that the E006/E008 parent arrays are wrong and did not request a new solve.

Two fail-closed evidence groups were missing from the supplied contract:

1. Prove that the adopted original/polished arrays are the qualified target, retain the same fixed damage, and satisfy every prescribed displacement DOF. A parent qualification may be inherited only through explicit evidence and the exact locked parent array.
2. For the c83 hard-KKT recomputation, prove the role and identity of the E003 accepted prior, original-target frozen `ftrial`, and `free_damage`; require finite arrays and exact `0 <= d_prev <= d_target <= 1`.

## Accepted implementation points

- The blocked MATLAB order `[all ux, all uy]` maps to interleaved order by `(j % nnode) * 2 + j // nnode`, provided the source indices are already zero-based.
- `force.ravel(order="C")` is correct for a `(nnode,2)` force array ordered `(fx,fy)`.
- Interleaved nodal mass must use `repeat(mass,2)`. The physical area used in `Es=area*Us^2` must not be doubled.
- c82 parent-reported hard values, c83 recomputed hard values, and the c82s5 parent control may coexist if their provenance remains explicit. They may not be described as one uniform independent hard-KKT recomputation.
- c82 does not need a fatigue array to reassemble the fixed-damage UV partial derivative. Its E012 damage/hard evidence remains parent-reported.
- A narrowly scoped macOS `matmul` warning suppression is acceptable when all fields, assembly results, scales, and final metrics remain fail-closed finite checks.
- `full_teacher=NOT_QUALIFIED` and separate adoption/UV/hard/native-joint gates are required. c82s5 derived fields remain `NOT_APPLICABLE`.

## Required rerun record

The read-only adoption receipt must retain commit and code hash, all input hashes and array keys, parent target keys, original and polished BC errors, fixed-damage and c83 strict-feasibility gates, UV normalization and parent comparisons, hard provenance, original native components, polished native-joint `NOT_EVALUATED`, field-change norm definitions, warning policy, and zero solve/training/history counts.

The remediation is limited to assertions and evidence fields. Because code changes are required, the corrected runner must receive a new commit and a new Code Ready review before formal execution.
