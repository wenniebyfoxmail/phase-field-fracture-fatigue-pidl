# Successor Handoff: Local Crack-Tip Network PIDL Branch

**Date**: 2026-05-23  
**Source branch/commit**: `claude/sidecar-adaptive-sampling` at `d64aaf8` plus pre-existing dirty docs only  
**Intended next worktree**: new PIDL worktree/branch for `tip-local-net` experiment  

## Current State

FEM has passed the important `psi` sanity checks and should be treated as the working reference. The remaining PIDL gap is field-level localization: PIDL can get broadly plausible `N_f`, but it under-resolves FEM-like crack-tip fatigue-history and phase-field concentration.

## What We Tried Already

- **S1 static process-zone oversampling**: refine/oversample fixed ball around initial tip `(0,0)`, `r_tip=0.05`. It lifted early `alpha_bar_max` by `+37%` to `+50%`, but long-horizon effect was modest and seed-sensitive.
- **S2 dynamic tip-following remesh**: moving refinement helped conceptually, but repeated remesh/transport perturbs optimizer/history. `hysteresis_fraction=1.0` fixed premature remesh and matched S1 until the first necessary remesh, then a smaller gap reappeared.
- **v3.2 history transport**: conservative `hist_alpha` edge-lineage transport + NN-max floor; diagnostics show history is not simply being reset.
- **v4 add-only refinement**: most physically sensible mesh-side direction because it avoids repeated rebuild/transfer of the wake, but it still does not change the NN approximation space.
- **adaptive `lambda_hist`**: diagnostic only. Post-refine gradients showed `||grad E_hist||≈2182` vs `||grad E_el||≈4.57`, `||grad E_d||≈8.43`; useful evidence of conditioning imbalance, but not a clean main method because it changes effective loss weighting.

## Decision for Next Branch

Try a **local crack-tip correction network**, not a larger global net. Keep the physical loss unchanged.

Suggested ansatz:

```text
u(x,y)     = u_global(x,y)     + w_tip(x,y) * u_tip((x-x_tip)/r_tip, (y-y_tip)/r_tip)
v(x,y)     = v_global(x,y)     + w_tip(x,y) * v_tip((x-x_tip)/r_tip, (y-y_tip)/r_tip)
alpha(x,y) = alpha_global(x,y) + w_tip(x,y) * alpha_tip((x-x_tip)/r_tip, (y-y_tip)/r_tip)
```

where `w_tip` is a smooth compact/tapered window near the current tip. The global net handles the smooth bulk; the local net handles the sharp process zone.

## Implementation Pointers

- Start from `source/network.py` and `source/construct_model.py`.
- Field evaluation flows through `field_comp.fieldCalculation(inp)` and `source/model_train.py`; this is the integration point for adding a correction head without changing the energy code.
- Existing related mechanisms to inspect: `source/williams_features.py`, `source/enriched_ansatz.py`, `source/sidecar_sampling.py`, and S1 runner `SENS_tensile/run_sidecar_S1_tip_oversample_umax.py`.
- Add a config dict, e.g. `tip_local_net_dict`, and keep it mutually exclusive with Williams/Fourier/enriched ansatz at first.
- First experiment should be **fixed S1 mesh only**, not dynamic S2/v4. This isolates representation from remesh/transport.

## First Experiment

- Case: `Umax=0.12`, seed 1.
- Mesh/sampling: S1 static refinement, `r_tip=0.05`, `n_refine_passes=1`.
- Horizon: N=20 smoke, then N=40 if stable.
- Compare against baseline, S1, and FEM field snapshots.
- Do not optimize for exact FEM `psi_peak`; that is mesh-sensitive.

## Success Metrics

- `alpha` line profile along the crack path.
- integrated `psi` / `alpha_bar` in a tip/process-zone band.
- localization width of phase field.
- crack-tip position trajectory.
- far-field `psi` sanity.
- no Kt collapse/explosion, no far-side spurious damage.

## Important Caveats

- Do not claim FEM is mathematically perfect at the crack-tip peak; claim it is sane/reference-quality for our purpose.
- Do not use loss reweighting as the main improvement unless explicitly labelled diagnostic.
- Avoid dynamic remesh in the first tip-net test; otherwise representation gains and transport disturbance are confounded.
- Current worktree still has unrelated pre-existing dirty files: `docs/sidecar_true_adaptive_sampling_decisions.md` and `docs/sidecar_true_adaptive_sampling_runs.md`. Do not assume they belong to this handoff unless explicitly reviewed.
