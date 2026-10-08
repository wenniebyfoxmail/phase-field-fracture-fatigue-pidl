# S04-E013 independent design review

- Source: ChatGPT Pro conversation `6ac3d374-50b4-83ed-893c-02fa7d0a71f4`
- Reviewed commit: `4c9291031a26e2ec04d057c43e4c9f7498aff091`
- Verdict: `NO-GO`
- Scope: supplied contract/audit only; no repository access, hash verification, or recomputation was claimed.

## Accepted structure

The two independent axes, four required peaks (`c20/c60/c82/c83`), and 12-state within-cycle matrix are appropriate for the prototype. No extra required cycles, tighter existing nondegenerate thresholds, new full-teacher criteria, or long-trajectory rerun is required.

Preparatory c60-reference and exporter implementation may proceed. Stage 0 closure and candidate training may not.

## Mandatory amendments

1. Freeze information separation across initialization, weights/optimizer state, budgets, stopping, checkpoint selection, and Stage 3 initial/history semantics; narrow diagnostic causal claims.
2. Make active-driver log, floor, null-field, correlation, shared FEM-support threshold, weighting, tie, and gate-scope rules executable.
3. Replace pooled/qualitative paired improvement with field-wise deterministic median, early/middle, and non-regression rules; make symmetry diagnostic-only unless a quantitative veto is prospectively frozen.
4. Freeze event detector, same-cycle/pre-event/own-event meanings, completion horizon, missing-event handling, own-history evolution, and export channels/timing.
5. Separate reference readiness, exporter readiness, paired-control asset readiness, and candidate-training authorization.

These amendments are instantiated in the amended `evaluation_contract.md` and `contract.json`. A new independent re-review is required before Stage 0 closure or candidate training.
