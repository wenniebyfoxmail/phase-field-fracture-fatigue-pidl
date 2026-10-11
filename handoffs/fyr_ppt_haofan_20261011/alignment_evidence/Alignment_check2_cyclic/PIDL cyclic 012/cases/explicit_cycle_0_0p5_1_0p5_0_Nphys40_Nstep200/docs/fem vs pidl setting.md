# FEM vs PIDL Setting: Phase 1 Claim Boundary

**Date**: 2026-05-19

**Scope**: Phase 1 toy-unit SENT comparison only. This note does not cover Phase 2 PCC scaling, MIT-8 supervision, or strict Carrara production runs except as context.

## 1. Can we say PIDL is trying to reproduce FEM?

Yes, but only with careful wording.

The defensible claim is:

> We use FEM as a reference solver and test whether PIDL can reproduce the macroscopic fatigue-life outcome and selected field-level diagnostics under a deliberately aligned Phase 1 setting.

The stronger claim is not defensible:

> PIDL reproduces the FEM fracture mechanism.

Why not: in Phase 1 the headline life can match while the local fields do not. Existing scorecards already show that baseline PIDL has strong `N_f` agreement but weak trajectory/localization agreement. Code-level comparison explains why: the two pipelines share a similar phase-field/fatigue model envelope, but differ in discretization, boundary enforcement, solver, fatigue update timing, and fracture-stop implementation.

Best paper wording:

> PIDL is evaluated against a FEM reference under a matched toy-unit SENT setting. The comparison tests whether a neural variational surrogate can recover the native FEM boundary-penetration life, while field diagnostics are used to identify where the surrogate departs from the FEM solution.

## 2. Does the Phase 1 setting satisfy a fair-comparison requirement?

Partly. It is fair for a methodological toy benchmark, not for claiming strict solver equivalence.

### What is aligned

| Item | FEM Phase 1 | PIDL Phase 1 | Status |
|---|---|---|---|
| Geometry | 1 x 1 SENT, notch from x=-0.5 to x=0 | same nominal domain and notch | aligned |
| Loading | vertical displacement, `R=0`, `Umax=0.12` family | same nominal amplitude and R=0 cycle abstraction | mostly aligned |
| Material scale | `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01` | `E=1`, `nu=0.3`, `w1=1`, `l0=0.01` | aligned after normalization |
| Phase-field model | AT1 | AT1 | aligned |
| Fatigue law | Carrara accumulator, asymptotic degradation, `alpha_T=0.5`, `p=2` | Carrara accumulator, asymptotic degradation, `alpha_T=0.5` | aligned at law level |
| Reference target | boundary penetration `d >= 0.95` | right-boundary `alpha > 0.95` with confirmation | similar concept, different implementation |

### What is not aligned

| Difference | FEM | PIDL | Why it matters |
|---|---|---|---|
| Discretization | Abaqus CPE4 quads, legacy `ell/h ~= 1` | gmsh triangles, NN nodal field | local peak `psi+`, crack-front shape, and `alpha_bar` can differ |
| Solver | staggered FE Newton for displacement and phase field | Deep Ritz NN optimization per cycle | different descent path and representation error |
| Boundary conditions | side edges satisfy traction-free naturally in FEM weak form | side traction-free is only weakly/naturally induced by Deep Ritz; top/bottom are hard ansatz | explains large PIDL V7 side-boundary residual |
| Horizontal Dirichlet constraint | GRIPHFiTH fixes `u_x` only at `bottom_left` and fixes/displaces `u_y` on bottom/top | default PIDL vertical-loading ansatz imposes `u_x=0` on both top and bottom because the correction bubble vanishes there and `cos(theta)=0` | this is a strict essential-BC mismatch for the GRIPHFiTH comparison; C4/exact-BC is a method variant, not the frozen baseline |
| Cycle resolution | multiple load steps per cycle in FEM | one peak solve per cycle; unload handled by resetting `psi_plus_prev` | fatigue increment timing is not identical |
| Irreversibility | FEM AT1 penalty uses default `tol_irrev=1e-3` unless overridden | PIDL uses `tol_ir=5e-3` | PIDL irreversibility penalty is weaker |
| Fracture detection | any external boundary node, excluding initial notch BC, with `d >= 0.95` | right-boundary nodes only; at least 3 nodes with `alpha > 0.95`; plus confirmation cycles | `N_f` is not extracted by identical rule |
| Mesh convergence | AT1+PENALTY reference is documented h-non-monotonic | PIDL is not a mesh-convergence study | absolute `N_f` has FEM-reference uncertainty |

Verdict:

> The setting is adequate for a controlled Phase 1 surrogate-vs-reference benchmark. It is not adequate for claiming that PIDL is a solver-equivalent reproduction of FEM.

## 3. What should we optimize in the research now?

The current strongest research story is not "PIDL matches FEM." It is more interesting:

> PIDL can match FEM-like fatigue life in a matched toy setting, but field-level audits reveal that the agreement can be produced by a different localization pathway. The research contribution is to expose, quantify, and reduce this macro-life / micro-field gap.

### Recommended research priorities

1. Separate the claims into three tiers.

| Tier | Claim | Evidence needed |
|---|---|---|
| Life-level | `N_f` agrees with FEM within tolerance | native `N_f`, cross-Umax, multiseed |
| Trajectory-level | crack-tip trajectory resembles FEM | `a(N)`, `x_tip_alpha95`, boundary damage counts |
| Field-level | local physics resembles FEM | `psi+`, `alpha_bar`, `f(alpha)`, symmetry V4, boundary residual V7, process-zone budget |

2. Stop treating `N_f` alone as success.

The Phase 1 baseline is the cautionary example: good life, weak field. Any method that improves `N_f` but worsens V4/V7/localization should be marked as "life-matching, field-divergent," not as a better surrogate.

3. Use FEM as reference, not oracle, unless explicitly supervised.

For pure PIDL methods, FEM should be used for evaluation. For MIT-8 or oracle-style methods, state clearly that FEM information is injected during training, so the question changes from "can PIDL discover FEM-like fields?" to "how much FEM supervision is needed to stabilize the surrogate?"

4. Add harmonized post-hoc fracture metrics.

For every Phase 1 comparison, report both native criteria and harmonized metrics:

| Metric | FEM | PIDL |
|---|---|---|
| Native stop | penetration `d >= 0.95` at outer boundary | `N_bdy(alpha>0.95) >= 3` plus confirmation |
| Boundary max | max boundary `d` | max right-boundary `alpha` |
| Boundary count | number of boundary nodes/elements `d >= 0.95` | `N_bdy(alpha>0.95)` |
| Tip position | max `x` with `d_elem >= 0.95` | `L_inf` or max damaged x with `alpha > 0.9` |
| Load/energy drop | `F_peak` or elastic energy drop | `E_el` history |

5. Make the paper's main result diagnostic, not triumphalist.

Suggested framing:

> Phase 1 demonstrates that a physics-informed neural variational model can recover FEM-scale fatigue life under a matched toy setting. However, targeted diagnostics reveal that matching life is not sufficient evidence of reproducing the FEM fracture process. The surrogate can reach the same boundary-failure event through different local fatigue accumulation and boundary-stress behavior.

6. Use Phase 2 to fix the reference problem, not only scale the PIDL.

Phase 1 FEM uses AT1+PENALTY and is documented h-non-monotonic. Phase 2 should lean on PF-CZM/Wu-style or publication-backed FEM references for the paper claim. In-house Phase 2 FEM data with no fracture should be used as supervision/diagnostic data, not as `N_f` oracle.

## 4. Practical decision rule

When writing or presenting:

- Safe: "PIDL is benchmarked against FEM."
- Safe: "PIDL attempts to reproduce FEM-level fatigue life under a matched Phase 1 setting."
- Safe: "PIDL matches the native FEM `N_f` in some Phase 1 runs, but field diagnostics reveal non-equivalent localization."
- Unsafe: "PIDL reproduces FEM."
- Unsafe: "PIDL reproduces the FEM crack mechanism."
- Unsafe: "`N_f` agreement proves the model is physically correct."

## 5. Bottom line

Phase 1 setting is good enough to support a surrogate benchmark and a nuanced research contribution. It is not good enough to support a simple reproduction claim.

The research should optimize toward:

1. preserving the life-level agreement,
2. improving trajectory and field-level agreement,
3. making the failure modes visible and named,
4. using Phase 2 to move from a toy AT1+PENALTY reference toward a publication-grounded or PF-CZM-based reference.

## 6. Should we modify the research setting?

Yes, but do it as controlled variants, not by silently changing the baseline.

The current baseline should stay frozen as the historical Phase 1 reference. Future changes should be framed as "alignment variants" that answer one specific question at a time.

### Priority alignment variants

| Variant | Change | Purpose | Risk |
|---|---|---|---|
| BC-aligned PIDL | strengthen side traction-free behavior via exact-BC ansatz or side-traction penalty | reduce V7 gap; test whether boundary residual causes field mismatch | may over-constrain NN and alter crack propagation |
| Fracture-criterion aligned post-hoc | compute FEM-style boundary penetration on PIDL fields and PIDL-style right-boundary count on FEM fields | separate physics mismatch from detector mismatch | needs careful field interpolation |
| Irreversibility aligned | set PIDL `tol_ir=1e-3` to match FEM AT1 penalty, or rerun FEM with `tol_irrev=5e-3` | isolate penalty-strength effect | expensive; may change optimizer stability |
| Loading-cycle aligned | add explicit loading/unloading substeps in PIDL for selected short runs | test whether one-peak-per-cycle abstraction changes `alpha_bar` path | much slower |
| Mesh/geometry aligned | put PIDL on the FEM mesh projection, or compare both on common element centroids post-hoc | reduce discretization confound | large plumbing cost |

Recommended order:

1. **Do not change the canonical baseline.** Keep it as the "life matches, field differs" reference.
2. **First run BC-aligned PIDL**, because V7 is a large and well-diagnosed gap.
3. **Then run fracture-criterion post-hoc**, because it is cheap and prevents `N_f` wording errors.
4. **Only then touch irreversibility / explicit cycling**, because those are slower and can create many new moving parts.

Research question after optimization:

> Which mismatch source actually controls the FEM/PIDL field gap: boundary residual, damage-front detector, irreversibility strength, cycle abstraction, or representational/localization capacity?

This is stronger than simply searching for a method with a good `N_f`.

## 7. PCC setting comparison

PCC is not currently an apples-to-apples FEM/PIDL reproduction setting. It has two separate lines:

1. **FEM PCC v3**: publication-facing Wu PF-CZM reference attempt.
2. **PIDL Phase 2A PCC**: units-transition smoke using the Phase 1 AT1/Carrara PIDL architecture.

### PCC FEM vs PIDL Phase 2A

| Item | FEM PCC v3 | PIDL Phase 2A |
|---|---|---|
| Goal | Wu PF-CZM concrete reference / trajectory export | test whether PIDL infrastructure survives PCC scaling |
| Geometry | 100 x 100 mm SENT | normalized toy domain mapped to 100 x 100 mm |
| Initial notch | `a0 = 5 mm`, `a0/W = 0.05` | toy mesh reuse, `a0 = 50 mm`, `a0/W = 0.5` |
| Mesh | PCC quad mesh, `h_tip ~= ell/5 = 0.4 mm` | Phase 1 gmsh toy mesh |
| Material | PCC: `E=30 GPa`, `nu=0.18`, `G_f=0.10 N/mm`, `ell=2 mm`, `f_t=3 MPa` | same physical constants after nondimensional scaling |
| Phase-field kernel | Wu PF-CZM | AT1 or AT2 PIDL kernel, default AT1 |
| Fatigue threshold | `alpha_T=5 N/mm^2` | normalized `alpha_T ~= 100` |
| Loading | calibrated `sigma_nom = 0.75 f_t`, `uy=7.5e-3 mm` | intact-bar displacement-equivalent label, not cracked-SENT calibrated |
| Cycles / result | explicit 3000 cycles, no fracture; trajectory data available | smoke/long PIDL run; not a Baktheer anchor |
| Valid comparison | `d`, `psi+`, `alpha_bar`, `f(alpha)` trajectory magnitudes | infrastructure behavior and qualitative scaling |
| Invalid comparison | FEM `N_f` oracle | direct PIDL-vs-FEM `N_f` claim |

### PCC verdict

PCC Phase 2A does **not** satisfy a reproduction setting. It is a scaling smoke.

Safe claim:

> Phase 2A tests PIDL behavior under PCC-normalized material and fatigue scales. It is compared qualitatively against available Wu PF-CZM FEM trajectories, but not used as a direct `N_f` reproduction benchmark.

Unsafe claim:

> Phase 2A PIDL reproduces PCC FEM or Baktheer fatigue life.

The main blockers are:

1. geometry mismatch: `a0/W=0.5` vs `0.05`,
2. kernel mismatch: AT1/Carrara vs Wu PF-CZM,
3. loading mismatch: intact-bar displacement-equivalent vs calibrated cracked-SENT nominal stress,
4. FEM v3 has no fracture in 3000 cycles, so it is not an `N_f` oracle.

### How to make PCC a fairer research setting

Minimal path:

1. Keep Phase 2A as infrastructure smoke only.
2. Use FEM PCC v3 trajectory as supervision/diagnostic data, not as life target.
3. Add a PCC PIDL geometry that matches FEM PCC: `100 x 100 mm`, `a0/W=0.05`, `ell/W=0.02`.
4. Calibrate PIDL loading by cracked-SENT nominal stress, not intact-bar displacement label.
5. If the paper needs PCC life claims, use Wu 2017 / Baktheer 2024 publication data rather than in-house FEM `N_f`.

Ambitious path:

1. Implement PIDL Wu PF-CZM kernel.
2. Use the FEM PCC mesh/centroids or a matched PIDL mesh.
3. Train with trajectory supervision first, then test extrapolation without supervision.
4. Compare against publication-backed PCC fatigue curves, not the retracted in-house `N_f` estimate.

## 8. Current research recommendation

For the paper and thesis narrative, the cleanest setup is:

1. **Phase 1**: keep as controlled toy benchmark.
   Claim: life-level agreement is possible, but field-level diagnostics reveal non-equivalence.

2. **Phase 1 alignment variants**: run targeted fixes.
   First target BC/V7, then criterion harmonization, then irreversibility/cycle abstraction.

3. **Phase 2A PCC**: label as scaling smoke.
   Claim: PCC scaling moves PIDL into a very high-cycle, deep-subcritical regime; this probes robustness, not direct reproduction.

4. **Phase 2 PCC reference**: cite Wu/Baktheer and use in-house FEM trajectories only as diagnostic/supervision.
   Do not resurrect the retracted `N_f ~= 1500-2500` in-house claim.

Best one-sentence research framing:

> We are not merely asking whether PIDL can match a FEM fatigue life; we are asking which parts of the FEM fracture process a neural variational surrogate can and cannot reproduce under controlled alignment, and what additional structure is required to close the life-field gap.

## 9. Controlled Alignment Variants: May 19 Audit

### 9.1 Boundary alignment experiments already done

We have already tested boundary-alignment ideas. The result is not a simple
"BC alignment solved it" story.

| Variant | Runner / evidence | What it aligned | Outcome |
|---|---|---|---|
| Soft side traction penalty (`Strac`) | `SENS_tensile/run_side_traction_soft_umax.py`, `validation_v4_v7_all_methods.csv` | Penalizes `sigma_xx` and `sigma_xy` on `x=+-0.5` query points | Short diagnostic only; production row still V7 FAIL (`rel_sxx=1.38`, `rel_sxy=1.197`) |
| Soft symmetry + Strac | `run_side_traction_soft_umax.py` | V4 symmetry plus side traction penalty | V7 improves relative to raw failures but remains WARN/unstable |
| A1 mirror alpha | `run_mirror_alpha_umax.py`, Windows Request 5/6 | Removes alpha ratchet asymmetry post-hoc | V4 passes by construction, but creates a severe left-edge stress spike |
| A1 + Strac combo | `run_mirror_strac_combo_umax.py`, N=5 smoke | Tests whether Strac rescues A1's edge spike | N=5 smoke V7 PASS, but only a smoke; not production evidence |
| C4 exact-BC | `run_exact_bc_umax.py` | Hard-encodes plane-strain lifting and side-distance gating so side traction vanishes by construction | V7 PASS; `alpha_bar_max` improves to 23.05 at N=100 |
| C4 + Fourier sigma=30 | `run_exact_bc_fourier_umax.py`, `advisor_method_evolution_en.md` | C4 fixes side BC, Fourier adds spectral capacity | Best current architectural stack: 3-seed N=100 mean `alpha_bar_max=27.50`, V7 PASS |
| C4-linear diagnostic | `run_C4linear_fourier_umax.py` | Replaces side^2 gating with side^1 to reduce over-constraint | Created as diagnostic for C4 over-constraint; use as next ablation if propagation suppression is the question |

Interpretation:

> Boundary alignment is a real lever, but the exact implementation matters.
> Soft penalties are not reliable enough to carry the paper claim. C4-style
> by-construction alignment is the strongest boundary result, but it is still
> an architectural method variant, not a proof that PIDL and FEM mechanisms are
> identical.

### 9.2 Manav-style alignment rule

The original PIDL and FEniCSx Phase 1 comparison aligns the variational boundary
value problem, not the numerical method.

| Item | Original PIDL | FEniCSx FEM |
|---|---|---|
| Top/bottom displacement | Hard-coded in `field_computation.py` via the `(y-y0)(yL-y)` bubble plus affine loading term | Dirichlet BC on top and bottom facets |
| Side boundaries | Natural/free through the energy minimization; not pointwise enforced | Natural traction-free boundary in weak form |
| Damage initial crack | AT1 profile around the initial notch | Same AT1 profile interpolated onto FE space |
| Solver | Deep Ritz neural minimization | Staggered FE solve |

This is the useful principle:

> Strictly align the physical problem. Allow solver/discretization differences
> to remain method-dependent, then audit whether those differences dominate the
> outcome.

### 9.3 What must be strictly aligned

These should be treated as part of the problem definition. If they differ, we
are no longer asking PIDL to reproduce the same reference problem.

| Must align | Why |
|---|---|
| Geometry, notch length, domain scale, and initial crack profile | Controls stress concentration and crack path |
| Material parameters and nondimensionalization | Controls threshold and process-zone scale |
| Phase-field kernel (`AT1/AT2/PF-CZM`), degradation law, `c_w`, residual stiffness | Changes nucleation and propagation physics |
| Strain-energy split | Changes the tensile driver `psi+` |
| Essential Dirichlet BC and loading amplitude/history | Defines the boundary value problem |
| Fatigue law, `alpha_T`, `p`, accumulation rule, and R ratio | Defines the cycle-to-cycle damage clock |
| Reporting metrics and post-hoc fracture criteria | Prevents detector mismatch from masquerading as physics |

Audit status for the frozen Phase 1 baseline:

> Material, geometry, AT1/AMOR, Carrara law, `alpha_T`, and nominal loading are
> aligned closely enough for a toy benchmark. Essential BCs are not strictly
> identical in the GRIPHFiTH comparison because FEM frees horizontal motion
> except one anchor while default PIDL fixes horizontal displacement on the top
> and bottom through its hard ansatz. Therefore the honest claim is
> "matched/aligned benchmark with named BC and cycle-abstraction mismatches,"
> not "strictly identical boundary-value problem."

### 9.4 What is method-dependent

These can differ, but each difference should be named and audited.

| Method-dependent | Boundary |
|---|---|
| FE mesh vs NN trial space / collocation points | OK as method difference; compare on common post-hoc probes |
| Newton/staggered solver vs neural optimizer | Core method difference |
| Hard ansatz vs weak/natural BC enforcement | Acceptable if it represents the same continuum BC, but V7 shows it can dominate |
| Fourier/Williams/enriched features | PIDL representation choice, not FEM alignment requirement |
| Supervision from FEM fields | Changes the question from pure reproduction to supervised correction |
| Stop-condition implementation | Method-specific at runtime; must be harmonized post-hoc for claims |

### 9.5 How to do variants 2, 3, and 4

Variant 2: fracture-criterion aligned post-hoc.

Use the existing local files:

- PIDL baseline archive:
  `SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12/`
- FEM handoff:
  `/Users/wenxiaofang/Downloads/_pidl_handoff_v2/post_process/SENT_PIDL_12_timeseries.csv`
- FEM snapshot:
  `/Users/wenxiaofang/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/u12_cycle_0082.mat`
- FEM mesh:
  `/Users/wenxiaofang/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/mesh_geometry.mat`

Compute both native and crossed criteria:

| Criterion | On FEM | On PIDL |
|---|---|---|
| FEM-style penetration | native `d >= 0.95` at external boundary excluding initial notch | evaluate PIDL alpha on comparable boundary probes and apply same threshold |
| PIDL-style right-boundary count | apply right-boundary `d >= 0.95` count on FEM projected field | native `N_bdy(alpha > 0.95) >= 3` plus confirmation |
| Common soft metric | max boundary damage and boundary-count curve | same |

May 19 first audit result, baseline `u=0.12`:

| Method | Native right-boundary count first hit | FEM-style external-boundary first hit | Note |
|---|---:|---:|---|
| PIDL baseline archive | 80 | 80 | archive stops at 90 because runtime uses confirmation cycles after first hit |
| FEM snapshots | 82 | 82 | only snapshots at N=1, 40, 70, 82; boundary-layer hit appears at N=82 |

Result:

> For the baseline `u=0.12` pair, detector mismatch is small. Crossed criteria
> move the event by at most about two cycles on the available snapshots. The
> larger FEM/PIDL difference is therefore not primarily a stop-rule artifact.

Output file:

- `SENS_tensile/alignment_criteria_u012_baseline.csv`

Script:

```bash
python SENS_tensile/posthoc_alignment_criteria.py --cycles all
```

Variant 3: irreversibility aligned.

Cheapest first step is PIDL-side only:

```bash
python run_tolir_umax.py 0.12 --n-cycles 100 --seed 1 --tol-ir 1e-3
```

Implemented runner:

- `SENS_tensile/run_tolir_umax.py`

Taobo launch, 2026-05-19:

- GPU 2, PID `698671`
- log: `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/run_align_tolir_u012_N100_seed1.log`
- archive: `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_tolir0.001_baseline`

Compare against the frozen baseline using `N_f`, `alpha_bar_max`, V4, V7, and
trajectory metrics. FEM-side rerun with `tol_irrev=5e-3` is possible, but it is
more expensive and should wait until the PIDL sensitivity is nontrivial.

Variant 4: loading-cycle aligned.

Current PIDL fatigue runs solve one peak state per cycle and model unloading
through the fatigue history update. GRIPHFiTH has a step loop inside each cycle.
To test whether this matters, create a short PIDL runner with explicit substeps:

```text
cycle k:
  lambda = R * Umax
  lambda = 0.5 * Umax
  lambda = Umax
  lambda = 0.5 * Umax
  lambda = R * Umax
  update alpha_bar consistently across substeps
```

Start with N=5 or N=10 only. The diagnostic is not `N_f`; it is whether the
`alpha_bar` slope, `psi+` localization, and boundary metrics move toward FEM.

Implemented gated support:

- `source/model_train.py` keeps default one-peak-per-cycle behavior unchanged.
- When `fatigue_dict["explicit_cycle_substeps"]` is set, `psi_plus_prev`
  advances substep-to-substep instead of resetting after every training step.
- `SENS_tensile/run_explicit_cycle_umax.py` creates the explicit substep
  displacement vector and tags the archive with physical cycles and training
  steps.

Smoke command:

```bash
python run_explicit_cycle_umax.py 0.12 --n-cycles 5 --seed 1
```

Taobo launch, 2026-05-19:

- GPU 3, PID `698672`
- log: `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/run_align_explicit_cycle_u012_N5_seed1.log`
- archive: `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_Ncyc5_Nstep25_R0.0_Umax0.12_explicitCycle_0-0.5-1-0.5-0`

Do not run this as production before reading the N=5/N=10 slope diagnostics.

Variant 5: GRIPHFiTH essential-BC aligned.

Baseline PIDL fixes horizontal displacement on both top and bottom through the
top-bottom bubble in the displacement ansatz. GRIPHFiTH fixes only one
horizontal anchor:

```matlab
'fix_X', bottom_left, ...
'fix_Y', bottom, ...
'disp_Y', top
```

Implemented runner:

- `SENS_tensile/run_fem_anchor_bc_umax.py`

It keeps the vertical BC hard (`v=0` bottom, `v=Umax` top) but changes the
horizontal ansatz so `u=0` only at `(x_min, y_min)`. This is a strict
essential-BC alignment diagnostic; it does not impose side traction-free
exactly and does not add Fourier/Williams/enrichment.

Taobo launch, 2026-05-19:

- GPU 4, PID `854354`
- log: `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/run_align_femAnchorBC_u012_N120_seed1.log`
- archive: `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N120_R0.0_Umax0.12_femAnchorBC`

## 10. Intact-Bar Label

`intact-bar label` means the Phase 2A runner converts a stress ratio into a
prescribed displacement using the formula for an uncracked uniform bar:

```text
u_top = (sigma_target / E) * H
```

So `disp_ratio_intact=0.75` means:

> choose the displacement that would produce `sigma = 0.75 f_t` if the specimen
> had no crack.

It does **not** mean the cracked SENT specimen actually realizes
`S_max = 0.75 f_t`. Because the crack increases compliance, the realized nominal
stress is lower unless separately calibrated. Therefore Phase 2A loading should
be written as "intact-bar displacement-equivalent", not as a calibrated Baktheer
stress ratio.

## 11. Mesh/Probe and Reaction Audits

These are post-hoc audits. They do not require GPU training.

### 11.1 Mesh/probe alignment

Meaning:

> Do not compare FEM-fine peak fields directly against PIDL-native peak fields
> and call the difference "physics." First evaluate both methods on a common
> probe set.

Implemented script:

- `SENS_tensile/posthoc_mesh_probe_alignment.py`

Current implementation:

- loads FEM snapshots at `u=0.12`, cycles `1, 40, 70, 82`,
- maps every FEM element centroid into the containing PIDL triangle,
- area-averages FEM fields onto PIDL elements,
- compares FEM-projected vs PIDL-native fields on the same PIDL elements.

Fields:

- damage: FEM `d_elem` vs PIDL `alpha_elem`,
- driver: FEM `psi_elem` vs PIDL degraded `psi_plus`,
- fatigue accumulator: FEM `alpha_bar_elem` vs PIDL `hist_fat`,
- fatigue degradation: FEM `f_alpha_elem` vs Carrara `f(PIDL hist_fat)`.

Output:

- `SENS_tensile/alignment_mesh_probe_u012_baseline.csv`

Key May 19 baseline finding:

> On common PIDL probes, `alpha_bar` and `f` are reasonably close in the
> right-boundary band, but local `psi+` diverges by many orders of magnitude
> near the crack/tip at late cycles.

Examples from `u=0.12` baseline:

| Cycle | Field / metric | FEM projected to PIDL | PIDL native | PIDL/FEM |
|---:|---|---:|---:|---:|
| 40 | `psi_plus` tip `2l0` mean | `8.21e1` | `1.03e-3` | `1.25e-5` |
| 70 | `psi_plus` tip `2l0` mean | `1.31e2` | `3.95e-4` | `3.01e-6` |
| 82 | `psi_plus` right-band mean | `1.15e1` | `3.85e-5` | `3.34e-6` |
| 82 | `alpha_bar` right-band mean | `6.76e-1` | `6.83e-1` | `1.01` |
| 82 | `f` right-band mean | `7.29e-1` | `7.44e-1` | `1.02` |

Interpretation:

> The fatigue clock and degradation can look aligned at coarse/right-band
> probes while the instantaneous local tensile driver `psi+` is not aligned.
> This supports the life-field split: macro or band-mean agreement does not
> imply local fracture-driver equivalence.

### 11.2 Reaction force / loading calibration

Implemented script:

- `SENS_tensile/posthoc_reaction_force.py`

Method:

```text
reaction ≈ [E_el(Umax + eps) - E_el(Umax - eps)] / (2 eps)
```

using the same trained PIDL checkpoint and frozen damage field. Since the FEM
handoff does not include nodal reaction forces, the FEM comparison here uses
the linearized effective reaction proxy `2 E_el / Umax`. This is a calibration
proxy, not a replacement for true FEM nodal reactions.

Output:

- `SENS_tensile/alignment_reaction_force_u012_baseline.csv`

Key May 19 baseline finding:

| Cycle | PIDL `dE_el/dU` | FEM `2E_el/U` proxy | PIDL/FEM |
|---:|---:|---:|---:|
| 1 | `8.01e-2` | `7.68e-2` | `1.04` |
| 5 | `7.98e-2` | `7.66e-2` | `1.04` |
| 40 | `5.64e-2` | `5.99e-2` | `0.94` |
| 70 | `2.51e-2` | `3.19e-2` | `0.79` |
| 80 | `2.25e-4` | `1.73e-2` | `0.013` |
| 82 | `1.90e-4` | `1.20e-3` | `0.158` |

Interpretation:

> Early-cycle loading stiffness is well calibrated. The large FEM/PIDL mismatch
> is not caused by a gross global loading-scale error. The mismatch appears
> after localization: local `psi+` and late-cycle stiffness collapse diverge.

### 11.3 Why "FEM weak form" is still phase-field

FEM and PIDL are both solving a phase-field fracture model. The distinction is
not "FEM vs phase-field." The distinction is how boundary conditions enter the
displacement subproblem.

For the mechanical equilibrium part, FEM solves the weak form. On an unforced
free boundary, the boundary term is

```text
∫_{Γ_free} (σ n) · δu dΓ
```

and natural traction-free means `σ n = 0`. In a conforming FEM solve, this is
the natural boundary condition of the weak form: it is not imposed as a nodal
Dirichlet condition, but the variational solution satisfies it in the FE weak
sense.

PIDL/Deep Ritz also minimizes an energy, but the NN trial space, hard ansatz,
collocation/element gradient approximation, and optimizer can leave nonzero
pointwise side-boundary traction residuals. Therefore V7 audits whether the
PIDL solution actually satisfies the same natural boundary condition:

```text
target on x=±0.5: sigma_xx = 0 and sigma_xy = 0
```

Baseline May 19 V7:

- `rel_residual_sxx = 0.265`
- `rel_residual_sxy = 0.174`
- status: WARN

So V7 is not a new physics law. It is a check that the PIDL approximation is
respecting the free-side natural BC closely enough.

### 11.4 V7-global / dynamic audit

Pointwise V7 can overstate the practical effect of a localized side residual.
The global/dynamic question is:

> Does the side traction residual remain a small variational error in aggregate,
> or does it do enough boundary work to affect the fracture trajectory?

Implemented script:

- `SENS_tensile/posthoc_v7_global_audit.py`

Output:

- `SENS_tensile/.../best_models/v7_global_audit.csv`
- `SENS_tensile/.../best_models/v7_global_audit.png`

Metrics:

| Metric | Meaning |
|---|---|
| `both_rms_t_over_ref` | RMS side traction residual divided by bulk `max |sigma_yy|` |
| `both_cancellation_tn/ts` | `abs(signed mean) / mean abs`; near 0 means residual cancels globally |
| `both_abs_boundary_work_over_Eel` | approximate `int_Gamma |t.u| dGamma / E_el` |
| `both_signed_boundary_work_over_Eel` | signed version; detects cancellation in work |

May 19 baseline result:

| Cycle | RMS side traction / ref | abs boundary work / `E_el` | Note |
|---:|---:|---:|---|
| 1 | `0.032` | `0.139` | global residual small early |
| 40 | `0.027` | `0.151` | still small while energy/reaction match |
| 70 | `0.020` | `0.362` | residual remains RMS-small, work ratio grows |
| 80 | `0.033` | `2.526` | after localization, `E_el` collapses so work ratio becomes large |
| 82 | `0.031` | `2.536` | late-cycle residual may be dynamically relevant |

Interpretation:

> The baseline side residual is not globally large in RMS terms. Early-cycle
> V7 is likely a local approximation error rather than a global loading error.
> However, after localization the same residual can become large relative to
> the remaining elastic energy, so V7 should be tracked dynamically and compared
> across controlled variants.

### 11.5 Variant 5 audit: FEM-anchor BC

Variant 5 (`run_fem_anchor_bc_umax.py`) aligns the GRIPHFiTH essential BC:

```text
fix_X bottom_left, fix_Y bottom, disp_Y top
```

It does not add side-traction exactness, Fourier/Williams features, or
supervision. Taobo result:

- first boundary hit: cycle `93`
- confirmed stop: cycle `103`
- final `alpha_bar_max ≈ 15.7`, `f_min ≈ 0.0038`

Post-hoc outputs:

- `SENS_tensile/alignment_mesh_probe_u012_femAnchorBC.csv`
- `SENS_tensile/alignment_reaction_force_u012_femAnchorBC.csv`
- `SENS_tensile/alignment_v7_global_u012_femAnchorBC.csv`
- `SENS_tensile/alignment_compare_baseline_vs_femAnchorBC.csv`

Key comparisons against the frozen baseline:

| Audit | Cycle | Baseline | FEM-anchor BC | Change |
|---|---:|---:|---:|---:|
| reaction ratio vs FEM proxy | 1 | `1.04` | `0.99` | better early loading calibration |
| reaction ratio vs FEM proxy | 40 | `0.94` | `1.05` | better/slightly high |
| reaction ratio vs FEM proxy | 70 | `0.79` | `1.29` | BC variant is stiffer than FEM |
| V7-global RMS traction / ref | 40 | `0.0267` | `0.0062` | `4.3x` lower |
| V7-global RMS traction / ref | 82 | `0.0306` | `0.0125` | `2.4x` lower |
| V7 abs boundary work / `E_el` | 82 | `2.536` | `0.224` | `11.3x` lower |
| `psi+` tip `2l0` mean, PIDL/FEM | 82 | `1.89e-6` | `4.64e-6` | `2.46x` better but still tiny |
| `alpha_bar` right-band mean, PIDL/FEM | 82 | `1.011` | `0.993` | both close |
| `f` right-band mean, PIDL/FEM | 82 | `1.021` | `1.018` | both close |

Interpretation:

> Essential-BC alignment is not a cosmetic change. It strongly reduces the
> global side-boundary residual and delays boundary hit from the baseline
> `~80` to `93`. However, it does not close the local `psi+` gap: tip-zone
> `psi+` improves only about `2-2.5x`, while the remaining FEM/PIDL gap is still
> many orders of magnitude. Therefore BC mismatch is a real contributor to the
> trajectory, but not the root cause of the local driver deficit.

### 11.6 Symmetry comparison: FEM reference vs FEM-anchor PIDL

FEM-side reference found in `docs/FEM.md` §5:

- setup: PIDL-series FEM baseline mesh, `u=0.12`, cycle `82`
- script/source: `Scripts/fatigue_fracture/fem7_mirror_damage.m`
- important caveat: Abaqus/GRIPHFiTH auto mesh is not fully mirror-coincident, so nearest-neighbor pairing contains mesh-position noise

FEM V4 reference:

| FEM pairing method | n_pairs | alpha_bar RMS | relative RMS |
|---|---:|---:|---:|
| exact mesh-coincident, `TOL=1e-7` | `262` | `8.07e-3` | `2.98e-5` |
| nearest-neighbor, `dist <= 1e-4` | `2498` | `4.00` | `1.48e-2` |

Fair comparison target is the exact-pair number `2.98e-5`, not the NN number.
The NN number is mostly mesh-discretization noise because only a small subset
of elements have exact mirror partners.

PIDL fem-anchor BC symmetry audit:

- output: `SENS_tensile/..._femAnchorBC/femAnchorBC_alpha_symmetry_audit.csv`
- method: compare reconstructed PIDL alpha field against `alpha(x,-y)` on a
  regular grid under the same fem-anchor ansatz

| Cycle | ROI | relative RMS alpha skew |
|---:|---|---:|
| 40 | right band | `3.65e-5` |
| 70 | right band | `4.78e-5` |
| 82 | full | `4.71e-2` |
| 82 | right band | `5.86e-2` |
| 82 | crack corridor | `1.51e-1` |
| 93 | full | `6.34e-2` |
| 93 | right band | `1.13e-1` |
| 93 | crack corridor | `2.05e-1` |

Interpretation:

> FEM-anchor BC improves global loading and V7 residual, but it does not recover
> FEM-level mirror symmetry. Early right-band symmetry is briefly near the FEM
> exact-pair scale, but the crack corridor is already asymmetric (`3.7e-2`) by
> c40 and grows to `1.5e-1` by c82. Against the fair FEM target `2.98e-5`, the
> c82 PIDL full/right-band/corridor skew is roughly `1.6e3x / 2.0e3x / 5.1e3x`
> larger. Therefore the new BC variant is not a strict FEM reproduction; it is
> a controlled alignment that isolates BC effects while leaving the
> localization/symmetry representation gap exposed.

## 12. May 27 Cross-Repository Setting Audit

This audit compares the executable PIDL settings in
`SENS_tensile/config.py`, `SENS_tensile/field_computation.py`, and the current
runner scripts against the GRIPHFiTH/FEM inputs in
`Scripts/fatigue_fracture/INPUT_SENT_PIDL*.m` and the PCC inputs. The purpose is
to make the phase-specific comparison explicit: the Phase 1 toy setting is a
controlled benchmark, while the Phase 2 PCC work is not yet an apples-to-apples
FEM/PIDL reproduction.

### 12.1 Phase map

| Phase | Purpose | FEM setting | PIDL setting | Comparison status |
|---|---|---|---|---|
| Monotonic SENS / brittle | original PIDL-style monotonic check | SENS tensile, `AT1 + AMOR + PENALTY` | original PIDL monotonic schedule | fairly aligned |
| Phase 1 toy SENT fatigue | main FEM-vs-PIDL benchmark | normalized SENT, `AT1 + AMOR + PENALTY` | normalized SENT, `AT1 + volumetric`, Carrara fatigue | aligned enough for life benchmark, not strict solver equivalence |
| Phase 1 alignment variants | diagnose mismatch sources | reverseBC, mesh studies, AT2 variants | exact BC, FEM-anchor BC, symmetry, Fourier, oracle, etc. | controlled ablations |
| Phase 2A PCC PIDL | units-transition smoke | not a direct FEM reference | toy geometry reused with PCC-scaled material | not apples-to-apples |
| Phase 2 PCC FEM | concrete reference attempt | PCC geometry/material, AT2 or Wu PF-CZM | PIDL does not yet match kernel/geometry | trajectory/reference only |

### 12.2 Phase 1 toy SENT: aligned items and mismatches

| Item | FEM / GRIPHFiTH | PIDL | Match? |
|---|---|---|---|
| domain | nominal `[-0.5,0.5]^2` SENT | `domain_extrema = [[-0.5,0.5],[-0.5,0.5]]` | yes |
| crack/notch | left-edge crack/notch from `x=-0.5` to `x=0`, separated Abaqus notch | `crack_dict`: `x_init=-0.5`, `L_crack=0.5`, angle `0` | nominally yes |
| mesh/discretization | imported Abaqus quads, `SENT_mesh.inp`; reference series uses 77,730 quads | Gmsh triangular meshes `meshed_geom1.msh`, `meshed_geom2.msh`; NN trial space | method difference |
| stress state | plane strain | plane-strain energy assumptions in validation code | yes |
| material | `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01` | `mat_E=1`, `mat_nu=0.3`, `w1=1`, `l0=0.01` | normalized match |
| phase-field model | `AT1` | `AT1` | yes |
| split | `AMOR` | `se_split='volumetric'` | yes |
| irreversibility | FEM `PENALTY` | PIDL `tol_ir=5e-3` plus alpha constraint | not identical |
| fatigue law | Carrara accumulator, asymptotic degradation | `accum_type='carrara'`, `degrad_type='asymptotic'` | yes |
| fatigue parameters | `alpha_T=0.5`, `p=2.0` | `alpha_T=0.5`, square asymptotic law; `n_power=2.0` for variants | yes |
| loading | cyclic, `R=0`, vertical `uy_final=0.08-0.14`, FEM substeps | cyclic abstraction, `R_ratio=0`, `disp_max=Umax`, one peak solve per cycle by default | nominal amplitude match; path differs |
| failure event | boundary penetration, `d >= 0.95` | right-boundary `alpha > 0.95` with count/confirmation | similar concept, different implementation |

The most important essential-BC mismatch is horizontal displacement. FEM baseline
fixes `u_x` only at the bottom-left anchor, fixes `u_y` on the bottom, and
prescribes `u_y` on the top. The default PIDL vertical-loading ansatz fixes
`u=0` on both top and bottom because the correction bubble vanishes there and
`cos(theta)=0`. This is why both directions of diagnostic exist:

- FEM `INPUT_SENT_PIDL_12_reverseBC.m`: clamp `u_x` on top and bottom to mimic
  old PIDL.
- PIDL `run_fem_anchor_bc_umax.py`: use a FEM-anchor ansatz to mimic GRIPHFiTH's
  single horizontal anchor.

### 12.3 Loading-cycle comparison

FEM Phase 1 resolves the loading branch inside each cycle, usually with
`n_step=8`, `loading='cyclic'`, `discretization='loading'`, `R=0`, and
`uy_final=Umax`. PIDL baseline uses `disp_cyclic = ones(n_cycles) * disp_max`;
each training step is the peak state of one cycle, with unloading represented
through the fatigue-history update/reset logic. Therefore `Umax` and `R` are
aligned, but intra-cycle fatigue timing is not identical.

For claims, this means `N_f` agreement is life-level evidence, not evidence that
the two solvers followed the same fatigue-history path.

### 12.4 Monotonic SENS / brittle setting

The monotonic SENS check is a separate phase. FEM
`Scripts/brittle_fracture/INPUT_SENS_tensile.m` uses:

- `AT1 + AMOR + PENALTY`
- `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`
- bottom `u=v=0`, top `u=0`, `v=lambda`
- crack prescribed through `non_hom_pf`
- monotonic loading to `uy_final=0.2` in 40 uniform steps

This is intended to match the original PIDL monotonic reference more closely
than the cyclic fatigue SENT runs. PIDL's monotonic schedule is non-uniform:
`linspace(0,0.075,4) + linspace(0.1,0.2,21)`, with the zero removed.

### 12.5 Phase 2 PCC is not apples-to-apples

| Item | FEM PCC v3 | PIDL Phase 2A |
|---|---|---|
| goal | concrete FEM reference attempt | units-transition smoke |
| geometry | `100 x 100 mm` SENT, `a0=5 mm`, `a0/W=0.05` | toy half-width notch, `a0/W=0.5` |
| mesh | PCC quad mesh, `h_tip ~= ell/5 = 0.4 mm` | Phase 1 PIDL toy mesh |
| material | `E=30 GPa`, `nu=0.18`, `Gc=0.10 N/mm`, `ell=2 mm`, `ft=3 MPa` | same physical constants after nondimensional scaling |
| kernel | Wu `PF_CZM` in v3, or `AT2 + MIEHE` in v2 | AT1 or AT2 PIDL kernel, default AT1 |
| fatigue threshold | `alpha_T=5 N/mm^2` physical | normalized `alpha_T ~= 100` |
| loading | `uy=7.5e-3 mm`, intended `sigma_max=0.75 ft` | intact-bar displacement-equivalent label, not cracked-SENT calibrated |

Therefore Phase 2A PIDL should be described as a scaling/infrastructure smoke,
not as a reproduction of FEM PCC or Baktheer fatigue life. The FEM PCC outputs
can be used as trajectory diagnostics or supervision targets, but not as a clean
`N_f` oracle for the current PIDL Phase 2A setup.

### 12.6 Safe wording

Safe:

> PIDL is benchmarked against a FEM reference under a deliberately aligned toy
> SENT setting. The comparison evaluates whether PIDL can recover FEM-scale
> fatigue life, while field diagnostics test where the surrogate departs from
> FEM.

Unsafe:

> PIDL reproduces FEM.

Best short summary:

> Phase 1 is a fair surrogate benchmark with named BC, cycle-abstraction, mesh,
> and stop-rule mismatches. Phase 2A is a PCC scaling smoke, not a direct
> FEM/PIDL reproduction setting.
