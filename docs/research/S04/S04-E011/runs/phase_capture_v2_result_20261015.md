# Native c1/c83 projection and tangent capture — completed 2026-10-15 BST

Four approved v2 files were uploaded byte-for-byte to CITPC12/AD\xw436, C:\Users\xw436\jobs\E011_PT_20261014_v2. Launch source ce7085e1d0fc0abc80b36b818396552266bef5a6, runner c517e9b1b3fe087164c85fc7029c2eba0691a550c0bcfac42c83ba90b1271d56. Producer MATLABR2025b CPU single thread; wrapper22100. UTC2026-10-14T23:40:49.513Z →23:43:45, BST2026-10-15 00:40:49→00:43:45, about176seconds. Fresh completion marker states4/history_commits0 and no MATLAB processes remained. 13 files,246934739bytes, all remote/local SHA256 and sizes verified. Original production and v1 evidence preserved.

Inputs: c1s4 peak baseline outer3 / last accepted numerical iterate13; c83s4 peak baseline20 / last accepted28. Each independently retains its original accepted s3 history/lower damage, same mesh/material and U=.11999988, eta0, nativeQ4 GP4. One unaccepted block direction per state; u1e-8/d4e-6, inner cap250, phase regularization shift0 in the log. No load step or history propagation. c83 last direction reproduced saved rejected trial09_01 within1e-10. Native captures are diagnostics, not repaired trajectories or qualified teachers.

## State-consistent residuals

| saved peak | cached phase rawR | returned preclip rawR | clipped feasible phaseR | final raw-refresh phaseR | free-u after damage |
|---|---:|---:|---:|---:|---:|
| c1 outer3 |9.6913e-7|5.0740e-7|1.06868e-5|1.06868e-5|7.93519e-5|
| c1 outer13 |1.9933e-6|7.1040e-5|1.06292e-5|1.06292e-5|2.88016e-6|
| c83 outer20 |3.2730e-6|8.8901e-6|2.56122e-5|2.56122e-5|2.40464e-4|
| c83 outer28 |3.8712e-6|1.8436e-6|2.56170e-5|2.56170e-5|2.69206e-4|

Preclip fields have78,797–81,830 bound violations; their low rawR or bound-filteredR cannot be called feasible convergence. Raw phaseR after clipping is~.00735–.00758 and includes legitimate bound reactions; the table instead reports the declared nodal feasible diagnostic after clipping. No state reaches the combined4e-6 screen.

Measured bottlenecks: Newton returns an updated field after testing the old residual. At c1-last the cached1.99e-6 passes phase tolerance while actual returned7.10e-5 does not. GP soft-penalty solutions are then nodally clipped; this restores feasibility but does not solve the resulting nodal constrained stationarity problem. Clipping raises the feasible-filtered metric at c1 baseline and both c83 points; at c1-last it reduces7.10e-5 to1.06e-5, so do not claim uniform worsening. All clipped endpoints retain~1.06e-5/c1 or2.56e-5/c83. This is a budget/state observation, not an irreducible floor.

Final raw refresh contributes phase vector deltas≤2.50e-13 here. It is small in this transition, not proof that fatigue/history is globally unimportant. History slots2:4 remain trial copies, not committed states: at c83-last clipping changes accumulator max .11477, active driver .13769, fatigue factor .008984 (distinct units). At c1 f=1 and the factor change is0. No undefined outputslot1 interpretation.

Fresh mechanical freeR after the u solve, before damage changes, is3.48–3.81e-15 at all states. After damage it becomes2.88e-6–2.69e-4. c1-last mechanical mass-dual centroidx=.00288 near initial tip; c83-lastx=.47506 near right front. c1-last99.942% squared feasible phaseR lies atx<=0, centroidx=−.28386 in the initial crack wake. At c83 phase imbalance is spread through the wake (left share59.66%), while mechanical imbalance is concentrated near the right front. Clipping corrections are broad; their largest node is not always the mechanical hotspot. Exact geometry shares/centroids in compact CSV; co-location alone is not a causal proof.

## Native tangent and finite-step evidence

16 native phase evaluations, 60 native directional merit evaluations and Ku/Kd*direction products independently reproduced. Native product/source-equivalent maximum difference6.59e-18, native FD merit difference≤2.60e-17. Equivalence is specific to the four tested states/directions. Fixed-raw native Picard Kdd differs from the trial-f residual directional derivative by15.12% at c83 baseline and17.79% at c83-last, epsilon1e-5; complete chain discrepancy1.73e-7/2.62e-7. GP fatigue/penalty/recovery/AMOR switches are0 for these checks. This is residual-Jacobian inconsistency under a Picard/frozen-coefficient tangent, not a claim that the physical model is invalid. Joint diagonal-only comparisons additionally omit cross coupling and must not be called Kdd-only error.

c83-last native u-only merit secant−2.37629e-4, damage-only+2.36253e-4, joint−1.37508e-6 at1e-5; all recorded branches stable. Strong cancellation leaves a weak joint descent direction.

**The earlier stall has a finite-grid boundary.** Original seven trials ended at1/64. Native diagnostic joint step1e-4 (156.25times smaller) gives M=2.64823240007e-4, decrease1.371951716e-10 from2.64823377202e-4. It satisfies the same sufficient-decrease bound2.64823e-12. Relative improvement5.18063e-7 (~.0000518%) is tiny. At1e-3/1e-2 merit increases; bound/AMOR branch changes are recorded. Smaller steps were evaluated, not accepted or propagated. No claim of global non-descent, successful convergence or sufficient budget extension.

## Decision and next controllable test

Execution succeeded, retrieval verified, diagnostic evidence supports cache/state mismatch and the difference between GP penalty solve plus nodal clipping and a stationary constrained endpoint. It also confirms specific trial-f tangent omissions and weak coupled descent. It does not identify the sole cause of the full FEM/PIDL field gap or qualify a teacher. Fixed committed-f vs trial-f and joint Deep-Ritz vs staggered/Picard remain.

Chosen next lever, not executed: a genuine nodal-bound constrained damage solve with fresh residual stopping, first at fixed saved c1 u/raw and s3 history (f=1 removes fatigue-chain ambiguity), compared with this captured native/clipped output. Primary existing phase-feasible4e-6 screen and identical input/history/budget must be frozen before execution; then c83 can test trial-f consistency and coupled control. Do not merely append many outer iterations or a full120-cycle rerun. Better monitoring alone cannot be claimed to repair the constrained solve.

Evidence endpoint: local_archive/experiments/S04-E011/runs/pf_s04e011_phase_capture_20261014_v2, receipts/retrieved/analysis. Tables and two inspected figures with sidecars; independent numerical/source/claim reviewPASS. Compact source/table evidence remains local until separately authorized for external publication.
