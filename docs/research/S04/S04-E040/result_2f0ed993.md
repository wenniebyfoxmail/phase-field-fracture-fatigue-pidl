# S04-E040 feasible-damage producer result — 2f0ed993

## Status and provenance

- Run ID: `pf_s04e040_feasible_damage_2f0ed993_20261025T203658Z`.
- Package commit: `2f0ed993ac9a432853668c01b073dbbe1ce70544`; reviewed numerical runtime: `5aaa317ed55175e80acb581d922eb6a1a4cb6d49`.
- The producer recorded the pinned package receipt, the four frozen inputs, physical GPU 5, and `post_cuda_preflight_settle_attempts=1`.
- The user-systemd service exited successfully. All 15 candidate physical steps were accepted and the read-only analyser paired the full continuous 15-step accepted prefix with S04-E037 R001 original.
- Archive root: `/mnt/data2/drtao/pidl_archives/pf_s04e040_feasible_damage_2f0ed993_20261025T203658Z`.

This is a matched PIDL-versus-PIDL trajectory comparison. It is not a FEM-agreement or physical-validity result.

## Objective boundary

The reference objective records `log10(E_el + E_d + shadow_E_irr) + weighted_L2`; the feasible-damage candidate records `log10(E_el + E_d) + weighted_L2`. Scalar loss values are therefore not compared as though they were the same objective. The comparison below uses shared physical fields and energy components.

## Field comparison

All relative L2 values use the analyser's strict common mesh/support pairing.

| phase | damage d rel. L2 | strain norm rel. L2 | raw psi+ rel. L2 | fatigue A rel. L2 |
| --- | ---: | ---: | ---: | ---: |
| step 1, first 0.03 load | 1.84% | 7.92% | 15.93% | 7.61% |
| step 2, 0.06 load | 12.09% | 84.79% | 97.53% | 148.92% |
| step 14, Umax=0.12 | 16.10% | 85.94% | 97.78% | 280.68% |
| step 15, unload | 16.30% | zero field | zero field | 280.68% |

The first nontrivial local-field separation is already visible at step 1 in psi+ (15.93%) while fatigue is still 7.61%. By step 2, local strain and psi+ have become very different before the fatigue history has accumulated over cycles: the candidate's weighted mean raw psi+ is 0.02495 versus 0.41021 for R001, and its maximum is 13.72 versus 638.71. The mean strain is only 2.1% lower at that step, but its local norm has 84.79% relative-L2 mismatch and its maximum is 4.53 versus 30.81. Thus the changed representation suppresses local concentration rather than merely shifting the global mean.

The fatigue difference then persists and grows: at Umax the candidate mean trial fatigue is 0.02156 versus 0.01448 (1.489 times R001), even though its mean raw psi+ is only 0.09595 versus 1.85760. This is evidence that history accumulation amplifies an earlier local-field mismatch; it is not evidence that fatigue was the first source of the mismatch.

## Constraint and activation diagnostics

The candidate has zero node and TRI3 irreversibility violations at every accepted state. However, at the first actual optimizer update of every one of the 15 physical steps, all reported free mass is in the map's dead branch (`dead_free_mass_fraction=1.0`, `open_free_mass_fraction=0.0`). Candidate damage changes very little: weighted mean d is 0.007065 at step 1, 0.007065 at step 2, and 0.007091 at step 14, compared with 0.007184, 0.007868, and 0.008420 in R001.

This is consistent with the nonnegative ReLU-based feasible map being inactive at the state from which each step begins. It supplies an exact hard lower bound without an irreversibility energy penalty, but here it also leaves essentially no first-update damage sensitivity. This diagnostic is a mechanism-level inference from the recorded branch fractions; it does not by itself identify every later optimizer effect.

## Time

The full matched 15-step prefix took 277.25 s for the candidate and 214.73 s for R001: 62.52 s longer, or 1.291 times the reference duration. Step durations vary substantially, so this is an end-to-end result for this run rather than a general performance claim.

## Decision implication

The run establishes that the hard-feasibility route can complete all 15 states with exact irreversibility and without adding an irreversibility penalty to the energy objective. It does not improve agreement with the standard PIDL trajectory: local strain and psi+ depart sharply from step 2, and fatigue accumulation subsequently amplifies the difference. A next design should retain the hard lower-bound constraint but use a projected/active-set constrained damage update (or another representation with a usable outward boundary derivative), rather than treating the inactive ReLU branch as the damage optimizer.
