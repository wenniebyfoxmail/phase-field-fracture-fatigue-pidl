# FEM c83 teacher precision — conditional UV audit

2026-10-05; S04-E006-R001; numerical code c543b1d; Condor63, exit0. Scoped evidence review PASS.

## Judgment

**CONDITIONAL_UV_SCREEN_PASS; FULL_TEACHER_UNQUALIFIED.** At unchanged FEM c83s4 damage, geometry, BC and eta0, an FEM-seeded sparse AMOR solve reaches the original UV screen with a small measured field correction. The original failure of a residual screen alone does not establish large displacement/active-field error. No field-error acceptance threshold or physical-truth comparison was introduced.

| Quantity | Archived FEM field | UV re-equilibrated |
|---|---:|---:|
| Mass-normalized rho_u | 0.0413314797153 | 4.39608378e-11 |
| Damage box, all nodes | 0.0653447795124 | 0.0653461183506 |
| Damage box, common FEM free nodes | 0.0580730249427 | 0.0580745314226 |
| Elastic energy | 1.8033163293e-5 | 1.8031395252e-5 |
| Fracture energy | 0.0080470200572 | unchanged exactly |
| History penalty energy | 0 | 0 |

Common original1e-3 screen remains unchanged. Final independent NumPy–Torch free-force difference is5.72289e-12 under the original1e-9 consistency gate. Four active-set iterations, stable=true; internal residual6.82138e-15; minimum LU pivot ratio1.104408e-4. Internal residual normalization does not substitute for the scientific rho_u screen.

Measured corrections relative to the archived field:

- Total-domain nodal-mass RMS(delta u)/Us:9.65908623e-6 (0.0009659% of loading amplitude).
- GP-weighted tensor-strain relativeL2:2.78801675e-4 (0.02788%); engineering shear square carries1/2 weight.
- Active-driver GP-weighted relativeL2:6.35660027e-4 (0.06357%).
- Active-driver relativeL2 on original positive weighted-p99 support:6.35659796e-4. Fixed threshold4.48203950e-7; actual support area1.00007989%. Neither support nor denominator was selected from the corrected field.

Error and reference norms are preserved in summary.json. No nominal normalization fallback was triggered. These are corrections to one numerically screened conditional equilibrium, not maximum pointwise errors, unique-solution errors, physical-truth errors or mesh-convergence bounds.

## Why the full teacher is not qualified

The damage box screen remains failed, with a slight numerical increase after UV correction. Only UV was solved. Current damage, accepted prior and ORIGINAL target-point ftrial were unchanged; no updated fatigue fixed point, damage optimization or history commit was attempted. A raw residual-field agreement at one state does not validate a coupled transition or trajectory. The FEM remains a specified field-expression target, not a fully equilibrium-qualified teacher.

Archived source cdf4e337: phase Newton returns res_pf; then damage is clamped below by p_old and optionally above; post_iter_update recomputes UV residual but retains res_pf in its raw residual-sum stopping rule. That scalar is not automatically the endpoint box/KKT residual with target-point trial fatigue. This is a source-level timing distinction, not a measured explanation of the remaining damage residual and not proof that tolerance alone causes it.

## Decision / next gate

Do not spend the next experiment on displacement precision alone. Historical KKT work already exists; see the dated clarification below. Reuse its bound-aware method and first establish whether c83 has a native hard-irreversibility endpoint certificate with the correct accepted prior and final coefficients. The failed box screen is not proof of failure on that different feasible set. Intermediate phase-output -> clipping -> coefficient reconstruction is a localization question, not a reason to repeat the completed box audit. Preserve E004's stopped admission and all original thresholds.

S04-E005 is a separate user-requested cross-cycle task, ID01a10c2a-ee02-74f0-bbbd-9f75d97a9ed3. Its results are not supplied by this c83-only experiment and are not inferred from it.

## Evidence and boundaries

21 small tests pass locally and remotely. Six remote output hashes match retrieved originals. PID24500, CPUfloat64, one thread; scheduler allocated a GPU but numerical code did not use it. Logs/NPZ/figures and receipt: project root local_archive/experiments/S04-E006/runs/S04-E006-R001. Figure set is retrieved/output/audit/figures/teacher_precision.png/pdf with README_analysis.md; colors use declared log/symlog visualization scales. Default existing solver initialization unchanged unless the new explicit seed argument is given.

Design and exact-code reviews PASS; external review covers pasted implementation/results, not independent repository/archive execution. See evidence_review.md for final interpretation status.

## 2026-10-05 clarification: purpose, procedure, result, and earlier KKT

Purpose: quantify the correction required for the **U≈0.12 FEM cycle83 peak substep s4**, corresponding to PIDL target414 (cross-audit prior413), to pass the common UV residual screen. The comparison is archived versus UV-re-equilibrated **same-cycle** fields, not an inter-cycle error. E006 uses the qualified FEM accepted prior, not PIDL413 as FEM history.

Procedure: seed UV with the original FEM field on native Q4; freeze current damage, BC, accepted FEM damage prior and original target-point trial fatigue coefficient; solve UV only; check the existing normalized residual and independent-gradient gates; measure field corrections. No damage solve or history commit.

Result: conditional UV screen passes with the corrections in the table above. Full teacher qualification remains unestablished. Specifically, the failed box screen does **not** establish failure of FEM's hard-irreversibility KKT conditions.

Historical evidence checked against local archived analysis/code (paths relative to project root):

- `local_archive/after_strict_setting_alignment/fem/hard5_phase_subproblem_frozen_state_audit_20260731/analysis/decision.md` and `frozen_phase_summary.json`: U0.13 Request27, c4 unload -> c5 loading steps and 11 peak staggers; nodal hard bounds d_old<=d<=1, 251 precrack nodes excluded. Active-bound sign-filtered raw residual L2 is 7.778073749e-5 at step1 and 2.449224945e-5 at peak, both below 4e-4; all audited anchors/staggers pass. Independent reconstruction matches MEX to max relative L2 3.83e-15. Large ordinary residual here is largely a legitimate bound reaction.
- `local_archive/after_strict_setting_alignment/pidl_result/hard5_native_q4_direct_q4_step413_20261004/analysis/decision.md`: actual PIDL candidate Arm-A solve; B0-scaled box projected-map infinity norms used/candidate 0.071009/0.380987 fail 1e-3. Hard-lower-bound Arm B was not triggered. This is not an original FEM teacher certificate.
- E002/E003 already evaluated c83 mass/energy-normalized box projected gradients, including accepted-history controls; E006 repeats that diagnostic after UV correction. These use [0,1] with soft history penalty, not the old nodal hard-lower-bound feasible set. Neither the normalization nor the threshold is interchangeable with the old c5 audit; U0.13 and U≈0.12 are different trajectories.
- `local_archive/experiments/S04-E004/qp_certificate.json`: NOT_PRODUCED_A1_BLOCKED, producer_run_started=false, qp_solved=false. Full primal/dual/complementarity QP certification was not produced.

Remaining evidence gap in the checked artifacts: c83 under its own correct FEM hard-irreversibility constraints and coefficient timing. Reuse the old method before commissioning a new solver experiment. The historical c5 PASS and present box-screen failures remain valid within their respective contracts. This clarification changes neither the frozen protocol nor the measured E006 verdict.
