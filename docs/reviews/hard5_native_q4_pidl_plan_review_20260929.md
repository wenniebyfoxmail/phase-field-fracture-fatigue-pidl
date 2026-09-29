# Hard-5 native-Q4 PIDL plan review (2026-09-29)

Status: `INDEPENDENT_PLAN_REVIEW_COMPLETE__IMPLEMENTATION_PENDING_EXACT_COMMIT_REVIEW`

Scope: read-only review of the proposed Hard-5, Umax=0.12 FEM/PIDL mesh-alignment calculation before implementation and producer launch.

## Evidence checked

- Exact-peak package: `hard5_u012_exact_peak_native_q4_c76_c82_c83_20260824_v2.1`.
- Frozen FEM source archive in that package, commit `cdf4e33710455606421806dfe6ff84ae09378d6b`.
- Native Q4 Abaqus mesh and c76/c82/c83 Gauss-point state files.
- Existing PIDL triangular integration and element-level Carrara state flow.

## Adopted findings

1. Use the 86,756-node, 86,408-element Q4 connectivity directly. Do not split Q4 elements for training; a split is allowed only for plotting.
2. Use the GRIPHFiTH four-point order `(+,+), (-,+), (+,-), (-,-)` and integrate displacement gradients, damage interpolation/gradient, elastic energy, fracture energy, and irreversibility penalty with the same Q4 operator.
3. Store and checkpoint `alpha_bar`, `psi_plus_prev`, and `f` as `[element,4]` arrays. Keep nodal `alpha` and interpolate it to the four Gauss points.
4. Retain the penalty formulation. The frozen solver selected `AT1_PENALTY_FATIGUE`; a tensile-history `H=max(H_old,psi_raw)` variable does not belong to this canonical run.
5. Use c83 as first FEM event detection and c86 as confirmation. Compare c76/c82/c83 only at the exact peak s4 post-convergence/post-damage-commit/post-history-commit/post-cyclemax state.

## Claim boundary

The implementation can align the spatial operator and Carrara Gauss-point commit state. It does not make the PINN and FEM fully identical: FEM uses a staggered/Picard solve and evaluates trial `alpha_bar/f` inside its phase trial, whereas the current Deep-Ritz loop fixes committed `f` during one load-step solve and updates it afterward. This timing difference must remain explicit in every result report.

## Rejected alternatives

- Q4-to-T3 splitting as the primary calculation, because it changes both the gradient and integration operator.
- Adding a tensile-history `H` field, because that would reproduce a different formulation from the frozen canonical FEM run.
- Treating a completed training process or matching event cycle alone as scientific validation.

## Required gates before production

- Exact Q4 mesh identity and positive Jacobians.
- Constant/linear Q4 patch and area tests.
- Direct replay of archived c76/c82/c83 nodal fields through the new operator against archived GP damage, strain, `psi_raw`, and active driver.
- GP state update and checkpoint shape tests.
- Exact-commit read-only review after implementation.
- Taobo GPU preflight and a bounded one-cycle smoke in a fresh attributable directory.
