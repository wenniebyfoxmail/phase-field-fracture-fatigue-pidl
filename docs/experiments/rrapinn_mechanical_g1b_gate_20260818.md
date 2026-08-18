# Mechanical-only residual G1b preregistration

Date: 2026-08-18
Status: `locked offline diagnostic / no training authorization`

## Current objective

Test whether the Formal PIDL free-DOF mechanical first variation can be
computed reproducibly enough to support a later tail-risk utility. This gate
does not test optimization benefit.

The eventual A/B question is:

> With every Formal PIDL setting held fixed, does adding only an interior
> mechanical-equilibrium tail loss reduce localized physical imbalance and FEM
> field-error tails without worsening first detect?

Control A is Formal PIDL. Candidate B is A plus the mechanical residual-tail
loss. Damage retains the same Formal energy and penalty semantics and is not
presented as a KKT residual.

## Five-question gate

1. **Mechanism:** validate the genuine free mechanical residual independently
   of the old element-energy proxy.
2. **Claim change:** pass permits G2 risk-utility implementation; fail keeps all
   training blocked.
3. **Cheaper diagnostic:** frozen U0.12/c82 checkpoint plus synthetic smooth
   fields, no optimizer.
4. **Minimal output:** manifest, analytic/autograd comparison CSV, boundary
   strata CSV, convergence CSV and decision note.
5. **Registry:** update the canonical track, attempt ledger and one inventory
   row after completion.

## Frozen provenance

- physics commit: `b6d56102daa7d45a6c196b72055010170e5f39fb`;
- `source/compute_energy.py` git blob:
  `201cf4f455b7987806185b6c7e6ff33eff53108c`;
- `source/fit.py` git blob:
  `3f45d739b4950cb6a4454e2045e1ff0c6e37402a`;
- `SENS_tensile/field_computation.py` git blob:
  `0d4826524d5f14486e91dc5c3ba151113a038834`;
- `SENS_tensile/meshed_geom_fem_soft_hist0.msh` git blob:
  `db0265ada3c8f06a21d30121781723d270f881cb`;
- evaluated model/state: Formal U0.12 c82 step409 with step408 frozen
  fatigue/history assets already hash-locked by G1.

The runner must independently resolve `git rev-parse HEAD` and all four blobs.
The commit CLI label alone is not evidence. Record Python, PyTorch, dtype,
device, script hash and free-DOF mask hash. Any mismatch is fail-closed.

## Residual definition

With damage and fatigue degradation fixed and detached:

`Pi_mech(u,v; d_fixed,f_fixed) = E_el(u,v,d_fixed)`

and for each displacement node:

`R_i = [dPi_mech/du_i, dPi_mech/dv_i]`.

`E_d` is constant with respect to displacement and may be included only in a
documented equivalence check. `E_hist` and the old element-energy magnitude
proxy are forbidden from the mechanical residual.

The risk path may later update shared-network parameters through `u,v`, but it
must have zero direct gradient to the detached damage output. This means
"no explicit added damage residual," not "damage predictions cannot change."

## Primary analytic cross-check

Independently assemble nodal force components from element stress and linear
triangle shape gradients. Compare analytic assembly with autograd on all
eligible free components using

`e_i = ||R_auto_i-R_asm_i|| / max(||R_asm_i||, eps_force)`,

where `eps_force = 1e-12 * max(weighted_RMS(||R_asm||), 1)` is frozen by the
formula, not selected from results.

Pass requires all of:

- weighted p99 `e_i <= 1e-6`;
- denominator-safe maximum `e_i <= 1e-4`;
- relative weighted L2 vector difference `<= 1e-6`;
- deterministic analytic/autograd directional-inner-product difference
  `<= 1e-6`;
- whole-domain translational balance, including constrained reactions,
  `||sum_i R_i|| / sum_i ||R_i|| <= 1e-8`.

## Auxiliary finite-difference checks

- A smooth synthetic state with no volumetric branch flips must show decreasing
  error over the predeclared sequence
  `{1e-3,3e-4,1e-4,3e-5,1e-5,3e-6,1e-6}` and cross `5e-4`.
  Because the branch-fixed synthetic energy is quadratic, central differences
  may already be roundoff-limited at the largest step. In that case all steps
  being below `5e-4` satisfies the convergence condition; strict monotonicity
  below `1e-8` is not required. This clarification is locked before execution.
- The real c82 state reports the same sequence plus the number of elements
  whose volumetric split differs between positive and negative perturbations.
- No single posthoc-selected step can override the analytic primary gate.
- A branch-frozen calculation may diagnose the old G1 mismatch but is not pass
  evidence for the real functional.

## Population and scaling audit

Construct nodal lumped dual areas `A_i=sum_(e contains i) A_e/3`.

- top/bottom Dirichlet components: excluded;
- interior free nodes: primary population with area measure;
- free nodes on outer side boundaries: separate stratum, because their natural
  boundary condition has a length measure;
- corners: separate diagnostic stratum.

For later G2 only, the candidate intensive residual is

`r_i = ||R_i|| / (A_i*S_mech)`,

with fixed `S_mech = E_ref*Umax/L_ref^2`, using `E_ref=1`, `L_ref=1` and the
cycle amplitude Umax even at unloaded substeps. Epoch-wise RMS normalization is
forbidden.

G1b reports area-weighted mean, p95, CVaR95, p99, CVaR99 and worst-1%-area
mass for the primary population, plus the separate side/corner strata. FEM is
not used.

## Stop and handoff

Stop on provenance mismatch, analytic/autograd failure, non-finite residual,
boundary-mask leakage, non-positive dual area, translation-balance failure or
failure to isolate the damage path. Passing G1b authorizes only G2 unit-level
implementation; it does not authorize Taobo or any training command.
