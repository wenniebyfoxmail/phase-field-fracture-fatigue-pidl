# S04-E011 multi-cycle causal diagnostics

These scripts reproduce the offline diagnostics used to separate displacement
and damage contributions in the paired Hard-5 Q4/T3 run. They do not train a
network or evolve fatigue/history state.

The state contract is fixed:

- FEM: converged peak solution for physical cycle `c` after the final
  staggered iterate.
- PIDL: accepted peak checkpoint/model at global step `5*c-1`, evaluated at
  `U=0.12`.
- Q4 replay: native bilinear Q4 with 2x2 Gauss integration.
- T3 replay: paired affine triangles with the frozen three-point rule.

Run the stages in this order:

1. `export_fem_nodal_trajectory.m(BASE, OUTDIR, CYCLES)` on the FEM producer.
2. `export_pidl_nodal_trajectory.py` for each topology on a GPU producer; the
   shell wrapper requires all paths and `CUDA_VISIBLE_DEVICES` through the
   environment.
3. `run_multicycle_cross_replay.py --analysis-root ... --handoff ...`.
4. `run_multicycle_fixed_damage_equilibrium.py --analysis-root ... --handoff ...`.
5. `summarize_multicycle_fixed_damage_equilibrium.py --analysis-root ... --handoff ...`.

The analysis root must contain the retrieved nodal exports and the selected
c83 direct diagnostics in the layout written by S04-E011. Generated tables,
figures, logs, and result blobs remain in `local_archive/` and are not tracked.

The fixed-damage solve is a causal displacement-equilibrium intervention. It
does not make FEM a ground truth and does not remove the committed-fatigue
versus trial-fatigue or joint Deep-Ritz versus staggered/Picard differences.
The `eta=1e-6` arm is a sensitivity calculation; the frozen experiment uses
`eta=0`.
