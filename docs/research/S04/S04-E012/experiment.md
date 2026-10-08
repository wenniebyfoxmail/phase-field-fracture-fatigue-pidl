---
storyline_id: S04
experiment_id: S04-E012
protocol_revision: 20261008-r0
status: formal-run-pass; evidence-review-pending
---
# Adopt the UV-rebalanced derived reference at c82s4/c83s4

## PIDL Experiment Gate

- Mechanism question: do the already-produced E008 c82s4 and E006 c83s4 fixed-damage/frozen-fatigue UV-polished fields satisfy the newly frozen strict-physics derived-reference contract when independently reassembled, with c82s5 retained as a no-solve control?
- Claim changed if success: the two polished fields may be used as **UV-rebalanced derived references** for the UV block, while `full_teacher` remains `NOT_QUALIFIED` and all damage/history/trajectory claims remain blocked.
- Claim changed if failure: do not adopt the existing polished arrays; identify the mismatch and design a fresh producer solve under a new run ID.
- Cheaper diagnostic first: reuse the identity-locked E006/E008 arrays and E010/E011 control metrics. Do not repeat a numerically identical solve.
- Minimal output asset: one three-row metrics table, one source manifest with hashes and parent links, one comparison figure, and one decision note.
- Registry destination: S04 storyline, experiment inventory, and `censor.md`.
- Decision: analysis-only adoption gate before any new solve.

## Frozen contract

1. `c82s4` parent is `S04-E008-R001`; `c83s4` parent is `S04-E006-R001`; `c82s5` parent is `S04-E010-R001`.
2. Reassemble original and polished UV force from the stored Q4 arrays and the common free-UV set. Verify both original and polished `rho_u` against the parent summaries at `rtol=1e-9, atol=1e-12`. The locked parent fields SHA and array keys define the adopted target; the parent target key and inherited qualification record must be emitted.
3. Verify each original raw UV L2 against E011. Adopt only when polished `rho_u <= 1e-3`.
4. Preserve the original accepted damage, accepted prior, original-target trial-fatigue meaning, mesh, BC, material parameters, `eta=0`, and the original 50-iteration maximum. This experiment performs no solve and does not mutate any parent asset.
5. Report original native raw UV L2, original archived phase scalar, and original reconstructed native sum. For the polished field, native phase residual and native joint acceptance are `NOT_EVALUATED` because no native phase reassembly was performed; do not reuse the original phase scalar after UV changed. A separate c83 hard-KKT recomputation does not change this label.
6. Report parent box and hard-KKT diagnostics, displacement/strain/active-driver changes, and keep original and polished arrays linked rather than copied or relabelled.
7. `c82s5` is read-only. It receives no polished field and no inferred correction.
8. Success qualifies the UV block of a derived reference only. The result is not a qualified FEM teacher, coupled equilibrium, true-solution error, mesh-convergence result, or trajectory result.
9. Directly assert the prescribed displacement on every essential UV DOF for both original and polished arrays at `atol=1e-12`, and require the complement to equal the locked free-UV set after blocked-to-interleaved conversion.
10. For c83 hard-KKT, require exact `0 <= previous_damage <= target_damage <= 1`, finite and valid `free_damage`, the locked E003 prior qualification record, and exact equality between `qualified_fields.npz::fem_ftrial` and the independently locked E010 c83s4 target `fatigue` array. c82 hard-KKT remains parent-reported only and is not promoted to an E012 recomputation.

External planning basis: [S04-E011 independent evidence review](../S04-E011/evidence_review.md). The user approved continuing this recommended order.
