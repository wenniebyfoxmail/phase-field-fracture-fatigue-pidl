# Joint backtracking grid — completed 2026-10-13

Purpose: localize outer20–30 changes and distinguish coupled full-step sensitivity from an admissible residual-decreasing joint step; include earlier mechanism states. [Frozen protocol](../endpoint_backtrack_protocol_20261013.md).

Producer CITPC12 one CPU thread, UTC11:17:15.6102486. Run pf_s04e011_backtrack_grid_e8c57e3_20261013T111601Z; source commit e8c57e35161183b911151601411d33120f5fbaac independently reviewed PASS, 5buildertests PASS, producer checkcode no syntax errors. Windowsroot C:\Users\xw436\jobs\E011_BT_e8c57e3_20261013T111601Z; wrapper/launcher/worker23708/5480/39452. Runner SHA25643e6cb00e90eae66cb06273c4270d670499a76365cebdb75c317d7c39ccf90ac. Local receipts under same run id in local_archive/experiments/S04-E011/runs/.

Sequence83,1,20,60,76,82; hashes locked and expected archived stopping iterations recorded before firstsolve. Eachstate onlys3→s4, frozen accepted history/damage, eta0 nativeQ4 GP4, U.11999988, no history commits. Cap10outer/7trials. First c83 originalbaseline20 and prior tightdirectionreference passed; all six states have now completed; terminal results below supersede the launch snapshot.

Offline localization: final damage-change centroid(.477510,−.001994), free-u mass-dual centroid(.482252,−.001904), both near rightboundary. Largest1%unweighted damage-change nodes contain99.890%unweighted free-u residualsquare. Exact active twofactor integral terms+1.56060e-4(raw) and−2.84734e-4(degradation) cancel to net−1.28673e-4.

Native free mechanical force replay agrees with11 native endpoints to~1.6e-16 maxabs. At fixedu30, d20 produces residual.0160069 versus actuald30 residual.000366884; atfixedu20,d30 gives.00126606. Damage-induced forcechange atfixedu30 hasnorm.0162015. This is conditional constitutive replay, not resolved equilibria or proof of entire discrepancy causality.

Assets: previous tight run localization/summary.json,metrics.csv,outer_spatial_maps.png withsidecar; new producer accepted endpoints and trial receipts retrieved and verified. No tightened convergedteacher claimed; fixed committed-f/trial-f and joint Deep-Ritz/staggered differences remain.


## Terminal result — 2026-10-13

All six original baselines passed reproduction admission; c83 first direction also matched the previous tight outer21. Producer finished UTC11:56:32; fresh process verification found no matching live process or failure. Retrieval: 100 files, 1,432,464,259 bytes, all SHA256/size checks passed. Independent numerical review recomputed 64 complete endpoints and checked 105 trial decisions; PASS. Rejected full-field trial MATs remain on the producer; local trial_trace and scalar receipts are present.

| cycle | accepted / trials | min lambda | final / baseline M | active relative L2 before → after | absolute gap ratio |
|---|---:|---:|---:|---:|---:|
| 1 | 10/10 | 1 | .120816 | .250046 → .229768 | .924783 |
| 20 | 10/10 | 1 | .379200 | .467973 → .389639 | .831123 |
| 60 | 10/10 | 1 | .557017 | .669415 → .587988 | .878459 |
| 76 | 10/19 | .5 | .794346 | .620651 → .540281 | .875713 |
| 82 | 10/19 | .5 | .713051 | .566949 → .432945 | .779355 |
| 83 | 8/37 | .03125 | .880994 | .476394 → .553544 | 1.180070 |

c83 stopped NO_ADMISSIBLE_DESCENT_WITHIN_TRIAL_BUDGET after seven rejected trials at attempt9; all others exhausted10 updates. All six missed M<=4e-6. At c83, M decreased11.9% but absolute active disagreement increased18.0%. At matched8 completed block updates, damped active relL2 .553544 vs undamped .815565, and M2.64823e-4 vs3.49285e-4: damping mitigates drift but does not close it. Trial costs differ, so this is not equal-compute performance.

At c1/c20/c60 lambda remained1: improvements belong to the combined tighter-inner/extra-outer control, not uniquely damping. Earliest sampled damping activation is c76; exact onset between c60/c76 is unidentified. c82→c83 response changes sign, not evidence that trajectory disagreement first appears at c83. These are independent original-s3 restarts, not a propagated repaired trajectory. Selected states all have zero right-marker penetration count; current paired FEM first detection is c84, not the older canonical c83 lineage.

Mechanistic interpretation: u equilibrium at fixed d is invalidated by the subsequent d-induced stiffness change near the right front. Conditional force replay demonstrates strong compensation, not solved counterfactual causality. Active=g(d)*raw contains two opposing channels. A residual decrease need not improve agreement with an unqualified PIDL endpoint. Fixed committed-f/trial-f and joint Deep-Ritz/staggered differences remain; no teacher or physical-truth qualification.

Next discriminator, not executed: use saved c1/c83 states to separate phase residual before/after nodal projection and raw/history refresh, and check coupled/trial-f tangent directional consistency. Both phase residual floor and cross-block coupling need investigation before selecting a damage/coupled-Newton repair; no automatic extra outer budget or full-trajectory rerun.
