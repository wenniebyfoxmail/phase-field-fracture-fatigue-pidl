# G5 export review progress — 2026-10-13

Execution: no full export, D0, training, resume or FEM solve. G5 HOLD.

Independent method dialogue accepted common-centroid native P0 representation for bounded archive-imitation diagnostics, not conservative projection, teacher or physics closure. Its v1 Code Ready HOLD identified exclusion enforcement, exact input identity, actual FEM index/static verification, and finite checks after precision conversion. These were implemented in candidate v3; re-review is pending. Review transcript is in dialogue 01a12d15-9b60-7280-8248-18386d6ef741. Main dialogue remains sole executor.

| Preflight | Evidence / result | Qualification boundary |
|---|---|---|
| PINN state number | retained family exporter peak_step=1+5(c-1)+3 | s4=5c-1, not generic zero-start example |
| FEM sample payload | MATLAB whos: d_node 86756x1, history_gp 86408x4x4, raw/active GP 86408x4, state_metadata | sample schema only, not full field qualification |
| Input frames | FEM/PINN meshes both [-0.5,0.5] in x/y | full containment/mesh equality audit still pending |
| Retrieved FEM static | hash matches sealed manifest a7edb0e…985e | identity only |
| Python v3 | py_compile PASS | syntax only |
| raw reconstruction | original source vs 100 synthetic strain triples, max abs 8.89e-16 | formula unit check only |
| MATLAB v3 | checkcode exit0; FNDEF due to historical upload suffix, ISCL performance suggestion; no parse error | actual deployment filename must match function; no numerical execution |

Additional zero-strain and NaN-exclusion guard sanity PASS. A first v3 checkcode invocation had one extra closing parenthesis in the shell -batch expression; no candidate ran, invocation corrected and checkcode completed. This is not an FEM failure or numerical retry.

Candidate protocol: g5_same_state_export_protocol_20261013.md (v3 current identities). Mandatory remaining G5 items: actual mapping/containment, same-state history equality/export precision, old-three channel compatibility, explicit effective-load offset, both-producer event/censor masks, approved paired data lock and PINN-only feature implementation. No fail is rescued by pooled metrics. Method D0 card remains B0 zero correction vs B1 direct-field closed-form ridge; not the old POD repeat, no NN.

## Actual v3 outcome and single repair

Independent v3 Code Ready PASS received for geometry, U0.115 PINN export and four development FEM exports (Python 1135208…65ea; MATLAB cc846…a8e7). The first geometry audit then FAILED the old/native identity prerequisite before any mapping output was created. Full FEM/PINN exports were not started. G5 stays HOLD; no D0/NN/solve.

| Native64 versus legacy | Actual diagnostic | Decision |
|---|---|---|
| centers | maxabs 4.9148775993490545e-8, above 1e-12 | original identity FAIL retained |
| areas | maxabs 2.342048330272739e-8 | historical areas not native64 weights |
| legacy precision lineage | float32-node center AND area calculations replay exactly | precision-loss cause identified |
| native containment | 85112 vs old85113, one cell removed | new geometry-only domain, no fallback |

Receipt: local_archive/experiments/S04-E016/g5_export_20261013/geometry_v3_failure_receipt.json. Only repair is a fresh native64 mapping/weights with independently verified candidate triangle assignments; see g5_native64_mapping_amendment_20261013.md. v4 Python 334196…eb1c is independently being re-reviewed before execution. No threshold relaxation and no producer recomputation. Topic note/Roadmap and method dialogue updated. Remaining G5/D0 requirements are unchanged.
