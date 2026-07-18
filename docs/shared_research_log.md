# Shared Research Log

**Purpose**: 跨机公共研究纪要。只记录有长期保留价值的 finding、decision、retraction、blocker。

**边界规则（2026-05-05 起生效）**：
- 日常任务派发/ack/progress/done **不再写这里**
- 这些内容走 `docs/handovers/*_inbox.md` / `*_outbox.md`
- 本文件只收：重要发现、架构决策、结果撤回、持久性阻塞

**历史归档**: `docs/archive/shared_research_log_2026-04_to_2026-05-05.md`

## Format rules

1. Entries ordered **newest first** (reverse chronological).
2. Every entry starts with: `## YYYY-MM-DD · <Agent-Name>`
3. Tag the kind: `[finding]`, `[decision]`, `[retraction]`, `[blocker]`
4. Include commit SHA + branch when relevant.
5. Keep entries concise; link to full memory files by name for detail.
6. Append-only: 修正旧 entry 通过新 entry 标注，不改历史文本。
7. Before pushing, git pull first to catch concurrent edits.

## Agent identifiers (current)

| Agent | Machine | Primary role |
|---|---|---|
| Mac-PIDL    | macOS (user's laptop) | Interactive dev; PIDL training (CPU/MPS); analysis; writing |
| Windows-PIDL | Windows (CPU-bound) | PIDL training + performance optimization |
| Windows-FEM  | Windows (GRIPHFiTH) | FEM reference runs; Fortran source of truth |

---

## Canonical facts (carried over, still valid)

- **run_baseline_umax.py bug FIXED** (commit 6040cbb + guard 427ebe7): 所有 non-u=0.12 baseline results from May-4 INVALID. Clean reruns in progress.
- **u=0.14 N_f=127 RETRACTED**: resume artifact, not real physics.
- **u=0.12 seed=1/2 N_f=82 BIT-EXACT**: VALID, unaffected by bug.
- **Oracle runs (Windows, run_e2_reverse_umax.py)**: all VALID, unaffected by bug.
- **Phase 2 PCC FEM smoke**: completed, α_T=0.094 placeholder → N_f≫10⁵. ~~Blocked on Holmen 1982 calibration.~~ **UNBLOCKED 2026-05-06**: fib MC 2010 §5.1.11 + Lee & Barr 2004 (in `references/`) provide modern S-N relations sufficient for α_T calibration; Holmen 1982 not strictly needed.
- **α-3 XFEM-jump CLOSED OUT 2026-05-06**: smoke modal=0.500 MARGINAL (commit 9f2ac69 left 5 path options for Mac to decide). Mac decision: **NOT pursuing α-3 production** — Path C supervised-α gave better trajectory metrics (Finding 6: a-N RMS 0.026 vs pure-physics 0.087, 3.4× closer to FEM); v3.16 strategic redirect away from ᾱ_max gap closure as primary target. α-3 design spec retained in memory as future work; not Phase 1 paper material.

---

## Entries

## 2026-07-18 · Mac-PIDL [finding+decision]

**Temporal memory improves ordinary rollout but fails the late FEM transition; no promotion**

On branch `codex/temporal-graph-transformer`, the sealed 18-run core matrix
(six parameter-matched families × seeds 1/2/3) and 14 formal ablations
completed on Taobo. Transformer had the best c67-c76 validation composite
(0.549 +/- 0.074; diagonal SSM 0.565 +/- 0.075; Markov 0.698 +/- 0.171) and
reduced short h5 error, but did not improve mean next-cycle error. TCN was
stronger at h10-h20. Every family missed the sharp FEM c87 raw-driver
redistribution and became a diffuse c89 failure: FEM-p99 IoU about 0.01 and
support-area ratio about 97. A c87 observation reset restored high overlap,
localising the failure to missing transition/state information rather than
insufficient temporal-block capacity.

Decision: do not promote Transformer or diagonal SSM, do not expand the
single-trajectory architecture sweep, and retain the code only as a
quarantined within-trajectory diagnostic. Any next rung requires multiple
compatible FEM trajectories and a newly sealed trajectory-held-out test.
c77-c89 is explicitly reused evaluation and cannot support a virgin-test or
generalisation claim. Full local package:
`local_archive/.../temporal_architecture_study_20260718/decision.md`.

## 2026-07-18 · Mac-PIDL [decision+implementation]

**Leakage-safe temporal mesh-operator diagnostic is isolated and quarantined**

Branch `codex/temporal-graph-transformer`, based on `a861da8`. A standalone,
opt-in operator compares parameter-matched Markov, GRU, LSTM, TCN, causal
temporal-only Transformer, and stable diagonal SSM blocks behind one shared
fine/coarse graph encoder and directional irreversible decoder. No existing
runner, config default, training loop, or active checkpoint contract changes;
the feature branch is safe during running trainings and must not be merged or
pulled by a producer except for this study.

The protocol is sealed before GPU work: normalisation and training windows use
c1-c67 only; context/checkpoint selection uses c67-c76; c77-c89 is explicitly
a reused evaluation benchmark, not a virgin locked test. Cycle number,
`cycle/89`, cycle-to-failure, and future loading are forbidden. The single
physical trajectory limits every output to a quarantined within-trajectory
diagnostic. Remote execution starts with a six-family two-step smoke, followed
by the minimum matched three-seed matrix; FEM active-support/localisation gates
remain primary over whole-domain MSE or event timing.

## 2026-07-15 · Mac-PIDL [decision]

**Graph architecture matrix approved: independent UV/damage branches plus damage-only latent coupling**

The eta0 channel ablation separates timing from mechanism quality: alpha-only
penetrates at c80 and fails timing; UV-only penetrates at c87 but loses the
all-channel model's active-driver localization; all-channel s=0.05 retains the
best energetic localization but penetrates at c79. This supports a coupled but
asymmetric representation hypothesis rather than further tuning one shared
output scale.

Decision: run four matched physics-only cases after remote smoke gates. Three
channel-separated cases keep `s_uv=0.05` and vary
`s_alpha={0.005,0.01,0.02}`. One damage-only latent case uses scale 0.05 and a
fixed detached FEM-independent soft corridor. All retain eta0, Formal 8x400,
graph 2x32, hard recovery, seed 1, and the existing fatigue/history law. FEM
remains the physical reference; same-cycle and own-event validation stay
separate. Event timing alone cannot promote a model.

## 2026-07-11 · Mac-PIDL [decision+implementation]

**Opt-in physics-trained Graph-PIDL architecture gate**

Branch `codex/m2s-framework-validation`. Following the completed eta=1e-3
micro-run (code-path pass, event timing shifted from step444 to step554), the
representation branch is separated from residual stiffness. An opt-in
`MeshGraphNet` replaces only the coordinate MLP and is trained by the unchanged
variational/fatigue objective with eta=0; FEM remains the external mechanism
reference and provides no field labels. Runtime FE connectivity is rebound for
coarse and fine meshes. Existing MLP runs are unaffected unless
`--graph-pidl` is supplied. Legacy c69 is excluded from the scientific test.
Taobo will run a training-path smoke before any trajectory run.

## 2026-06-29 · Mac-PIDL [retraction+implementation]

**Eight-step cyclic protocol now accepts absolute displacement steps**

Branch `codex/m2s-framework-validation`.  The first eight-step Taobo ablation
used the legacy `--substeps` interface with normalized factors
`0.25,0.5,0.75,1,0.75,0.5,0.25,0`.  For `Umax=0.12` this generated the intended
physical displacement sequence, but the interface and provenance were
semantically ambiguous for FEM/PIDL alignment.  That run was stopped and should
be treated as an aborted diagnostic, not formal eight-step evidence.

`SENS_tensile/run_fem_mesh_probe_driver_umax.py` now supports
`--displacement-steps` as the preferred alignment interface.  The protocol
source is the absolute displacement list, e.g.
`0.03,0.06,0.09,0.12,0.09,0.06,0.03,0`; any normalized factors are written only
as derived internal compatibility data for legacy oracle helpers.  Settings and
logs now print displacement steps and peak/unload displacement values directly.

## 2026-06-29 · Mac-PIDL [decision+implementation]

**Variable-substep peak/unload mapping for cyclic recovery diagnostics**

Branch `codex/m2s-framework-validation`.  Updated
`SENS_tensile/run_fem_mesh_probe_driver_umax.py` so retained cyclic diagnostics
no longer assume `peak = n_substeps - 2`.  The runner now identifies the peak
substep as the first maximum load factor and the unloaded state as the final
substep.  This matters for eight-substep protocols such as
`[0.25,0.5,0.75,1,0.75,0.5,0.25,0]`, where the old hard-coded rule would have
mislabelled the 0.25 unload-ramp state as peak.

Added `--diag-full-physical-cycles` to save all substeps for selected cycles,
so unloading-path ablations can inspect intermediate descending-load states
rather than only peak and final unload.  Default behavior for the existing
five-substep baseline remains unchanged.

## 2026-06-29 · Mac-PIDL [decision+implementation]

**Opt-in hard-alpha zero-load recovery discriminator for Alignment Check 2**

Branch `codex/m2s-framework-validation`.  Added an opt-in runner path to
`SENS_tensile/run_fem_mesh_probe_driver_umax.py`:
`--hard-alpha-recovery-step --hard-alpha-target 1.0`.  It prepends a single
`U=0` recovery training step before the normal retained substep schedule and
sets only the current NN alpha head to the hard target before that step.  The
stored histories remain at the state0 baseline until the recovery step commits:
`hist_alpha` is not set to 1, `hist_fat=0`, `f_fatigue=1`, and
`psi_plus_prev=0`.

Default behavior is unchanged.  With this flag, explicit five-substep state
mapping is shifted by one PIDL step: step0 is `U0_hard_alpha_recovery`,
`cN_peak -> 1+5*(N-1)+3`, and `cN_unloaded -> 1+5*(N-1)+4`.  The existing
`pre_step0_baseline_diagnostics.npz` now records the initial-alpha protocol
metadata so the audit can verify whether pretraining polluted the state0
histories.  Runtime element diagnostics also now save `hist_alpha_elem` and
`alpha_minus_hist_alpha_elem` so the recovery post-commit state can be audited
without reconstructing this field from checkpoints.  Mac verification was
limited to `py_compile`, `git diff --check`, and runner `--help`; no PIDL
training was run on Mac.

## 2026-06-26 · Mac-PIDL [decision+implementation]

**Opt-in FEM-like irreversibility penalty quadrature for Alignment Check 2**

Branch `codex/m2s-framework-validation`, commit `9547f27`.  Added an opt-in
PIDL loss path for the irreversibility penalty:
`numr_dict["irreversibility_penalty"] = {"enable": True, "mode": "fem_gp_tri3"}`.
When enabled on FEM-mesh/T_conn runs, each triangle checks local recovery at
the standard three-point triangle quadrature locations before averaging
`ReLU(-(alpha_q - hist_alpha_q))^2`.  Default remains legacy/off, so existing
and running trainings keep the old `ReLU(-mean_node_delta)^2` behavior.

The strict FEM-mesh probe runner now accepts
`--history-driver-reduction-mode fem_gp_tri3_g_mean` and `--fem-irr-penalty`
for producer-side smoke/production tests.  Element diagnostics now save both
`E_hist_legacy_elem` and `E_hist_fem_gp_tri3_elem`, while `E_hist_elem` remains
the actual penalty used by the current run.  Mac verification was limited to
`py_compile`, `git diff --check`, runner `--help`, and tensor-level formula
sanity; no PIDL training was run on Mac.

## 2026-06-13 · Mac-PIDL [decision+implementation]

**Opt-in lagged-stiffness solver discriminator for Alignment Check 2**

Branch `codex/m2s-framework-validation`.  Added two explicit PIDL discriminator
modes to `run_fem_mesh_oracle_field_umax.py`: `lagged_g_stiffness`, where the
Deep Ritz solver and fatigue-history driver both use `g(hist_alpha_previous)`,
and `lagged_g_solver_only`, where only the solver stiffness uses
`g(hist_alpha_previous)` while the post-solve fatigue update recomputes the
driver from current alpha.  Defaults and existing runners are unchanged; the
hook is inactive unless `fatigue_dict["lagged_stiffness"]["enable"]` is set.

Purpose: separate "previous-alpha stiffness in the solver" from the older
`lagged_g` post-update history-driver test, which did not alter the variational
solve.  This is safe during existing trainings because it is opt-in and does
not change the default `current_active` path.

## 2026-05-31 · Mac-PIDL [finding+implementation]

**M2S next-stage feasibility package completed**

Added `SENS_tensile/run_m2s_next_stage_feasibility.py` on branch
`codex/m2s-framework-validation`.  The package builds leave-one-trajectory-out
RUL/crack/state holdout metrics and sparse/noisy virtual-sensor degradation
curves, excluding cycle index from all inputs.  Outputs are local under
`_analysis_m2s_next_stage_20260531/`: holdout summary CSV, sparse/noisy summary
CSV, true-vs-predicted RUL figure, observation-quality figure, cycle feature
table, prediction tables, and short report.

Data used: three strict soft-hist0/reverseBC full-field cadence handoffs
(`n_step=2/3/10`) plus the legacy five-Umax scalar FEM reductions in
`~/Downloads/_pidl_handoff_v2/post_process`.  Main result: on the legacy
five-Umax scalar holdout, damage-only RUL is poor (`MAE≈82-86` cycles), while
state-driver proxies improve to `MAE≈35` cycles (`R2≈0.82`).  On the strict
cadence full-field subset, all feature tiers remain near-trivial
(`MAE≈0.8-1.2` cycles) because the trajectories are too similar.  Sparse/noisy
mixed damage sensors on the strict field subset degrade from `MAE≈11.9` cycles
with 4 clean sensors to `MAE≈1.55` cycles with 64 clean sensors; 64 sensors with
0.10 damage noise still give `MAE≈2.88` cycles.

Guardrail: this is a feasibility rung, not real deployment validation.  It gives
evidence that multi-trajectory holdout splits are the right next M2S benchmark
and that hidden state-driver proxies can matter in the scalar five-Umax stress
test, but it does not yet prove strict full-field hidden-state superiority.  The
production next step is to export strict soft-hist0/reverseBC full-field
trajectories across `Umax`, `alpha_T`, and precrack severity and rerun the same
package on that stricter family.

## 2026-05-31 · Mac-PIDL [finding+implementation]

**M2S synthetic framework validation rung completed on latest FEM truth**

Added `SENS_tensile/run_m2s_synthetic_validation.py` on branch
`codex/m2s-framework-validation`.  The script treats the latest soft-hist0
reverseBC FEM trajectory (`N_f=69`, c1-c69, 45000 elements) as truth and tests
remaining-life prediction from three observation levels without using cycle
index: `figure_damage`, `damage_field`, and `state_driver_raw_active`.

Result on Taobo: ridge LOOCV MAE was `0.333` cycles for figure-like damage
features, `0.214` cycles for richer damage-field reductions, and `1.40` cycles
for the high-dimensional state-driver set.  Nearest-neighbor MAE was about
`1.3-1.45` cycles for all sets.  The framework is therefore feasible at the
single-trajectory synthetic M2S rung, but the benchmark is too easy: monotonic
damage geometry almost directly encodes remaining life.  Hidden fields should
not be claimed to add independent value until a multi-trajectory holdout
benchmark breaks that one-to-one damage/RUL ordering.  Full record:
`docs/m2s_framework_validation_2026-05-31.md`.

## 2026-05-31 · Mac-PIDL [finding+implementation]

**Strict FEM-mesh inverse `alpha_T` retry closed: scalar inversion is not identifiable**

Added and launched `SENS_tensile/run_fem_mesh_inverse_alphaT_umax.py` on branch
`codex/inverse-femmesh-soft-hist0` commit `215c3bd`.  Target was the latest fair
reference, `SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC` (`N_f=69`),
against the strict FEM-mesh soft-hist0 PIDL baseline.  Only `alpha_T` was
trainable (`init=0.25`, bounds `[0.05,2.0]`); `E_irrev/tol_ir=5e-3` and all
forward physics settings were fixed.

Result: the inverse run collapsed `alpha_T` to the lower bound `0.05` from about
`j=5`, detected boundary fracture at `j=11`, and confirmed at `j=14`, far earlier
than FEM c69.  This is parameter compensation, not material recovery.

Raw/active diagnostic confirmed the comparison trap: at c10/j9 raw `psi+` tip2
was `8.06x` FEM but active `g(alpha)psi+` tip2 was only `0.057x`; at c15/j14 raw
was `4.46x` but active was `0.259x`.  Therefore raw `psi+` amplitude alone is not
the bottleneck.  The remaining mechanism is active/degraded driver plus local
history feedback.  Full record: `docs/inverse_problem_experiments_2026-05-31.md`.

## 2026-05-30 · Mac-PIDL [finding+implementation]

**Additive local patch weak/negative; FBPINN-chain discriminator prepared**

The strict FEM-mesh additive local patch matrix finished:

| case | detect/confirmed | c69 alpha_bar max | c69 Kt | final alpha_bar max |
|---|---:|---:|---:|---:|
| all-output patch | j81/j84 | 8.67 | 15.16 | 9.96 |
| alpha-only patch | j80/j83 | 8.83 | 15.76 | 9.36 |
| uv-only patch | j81/j84 | 2.82 | 15.15 | 2.82 |

Remote c69/event reductions show all/alpha-only are baseline-like and still
fracture through right-boundary saturation; uv-only suppresses fatigue history.
The additive one-patch design is therefore closed as weak/negative.

Definition correction: saved PIDL `psi_plus_elem` is already the active fatigue
driver `g(alpha)*psi0`, not raw undegraded `psi0`.  New diagnostics now save
both `psi_raw_elem` and `psi_active_elem`.

Prepared the next strict representation discriminator:

```text
SENS_tensile/run_fem_mesh_fbpinn_umax.py
```

It uses a chain of overlapping local subdomain networks along x=0.00 -> 0.45
with smooth partition blending:

```text
raw_output = (1-beta)*global_MLP + beta*local_subdomain_mix
```

so local nets carry the raw field inside their process-zone windows instead of
being small additive corrections.  Artifact:
`docs/fbpinn_chain_discriminator_2026-05-30.md`.

## 2026-05-30 · Mac-PIDL [implementation]

**Strict FEM-mesh local-patch discriminator prepared**

Added a compact-support crack-tip patch representation for the next field-level
test after head-staging closed negative:

```text
raw_output = global_MLP(x,y) + chi(r) * local_patch_MLP(local_coords)
chi(r) = max(1 - r^2/wr^2, 0)^2
```

The default runner is `SENS_tensile/run_fem_mesh_local_patch_umax.py` with
strict FEM-mesh soft-hist0 controls, `wr=0.10`, `output_mode=all`, a 3x80 local
patch, and per-cycle `patch-only warm-up -> joint RPROP`.  The physics loss,
fatigue law, history timing, and event criterion are unchanged.  The local patch
is registered under `field_comp.net.local_patch_net`, so normal
`trained_1NN_*.pt` files contain patch weights.  Common-probe and element-field
posthoc tools now reconstruct local-patch archives from `model_settings.txt`.

Gate: compare c20/c40/c69 and matched-event states to FEM standard/n_step10 via
damage, `alpha_bar`, raw/active `psi+`, `Delta E_d`, and alpha/residual fields.
Artifact: `docs/local_patch_discriminator_2026-05-30.md`.

## 2026-05-30 · Mac-PIDL [finding]

**Strict FEM-mesh head-staging discriminator closed: optimiser ordering is not the field-gap mechanism**

Four PIDL variants were run on the strict FEM-mesh soft-hist0 setup:

| branch | schedule | outcome |
|---|---|---|
| staged-alpha | uv750 -> alpha750 -> joint10000 | event j80/j83 |
| alpha-head-only | uv0 -> alpha1500 -> joint10000 | event j80/j83 |
| uv-head-only | uv1500 -> alpha0 -> joint10000 | event j81/j84 |
| head-stages-only | uv750 -> alpha750 -> joint0 | no fracture by j99 |

Common-probe gate vs FEM n_step10 c69: joint-solve branches keep `alpha_bar` tip2 at about 0.35-0.37x FEM and active `psi+` tip2 at about 0.003-0.023x FEM. Event states raise `Delta E_d` only to about 0.40-0.44x FEM and still show active-driver collapse. The no-joint branch produces huge nonpropagating history (`alpha_bar` tip2 >4x FEM at j99) with raw `psi+` tip2 ~0.06x and negative incremental `E_d` vs FEM.

Decision: close head-staging as a useful negative discriminator. Final joint elastic-damage relaxation is necessary, but optimiser ordering/output-head windows do not repair the local active-driver/history feedback. Next discriminator should strengthen representation/local authority (FBPINN/domain-decomposed tip patch or revived discontinuity/jump-head with fixed tip tracking), not add more head-stage schedules.

## 2026-05-05 · Mac-PIDL [finding]

**u=0.14 pure-physics 5-seed sweep: systematic underestimate (mean −24%) + high variance (std=4.2) — OOD boundary confirmed**

FEM N_f = 39.

| seed | N_f (first) | error |
|---|---|---|
| 1 | 28 | −28% |
| 2 | 36 | −8% |
| 3 | 26 | −33% |
| 4 | 33 | −15% |
| 5 | 25 | −36% |
| **mean** | **29.6** | **−24%** |
| **std** | **4.2** | — |

All 5 seeds underestimate FEM. Range = 25–36 (span 11 cycles). This is not seed noise around the correct answer — it is a systematic bias combined with high variance. Pattern A regime (boundary α saturation compresses N_f before tip accumulator builds) is the leading mechanism.

**OOD boundary conclusion**: PIDL pure-physics reliable for Umax ≤ 0.13 (≤+7% vs FEM, low seed variance). Umax = 0.14 is outside reliable range (−24% bias, std=4.2). Paper should report this as the identified OOD boundary.

**u=0.12 seed=3 also completed**: N_f=82, same as seeds 1+2. u=0.12 is fully deterministic across seeds (zero variance at training Umax).

## 2026-05-05 · Mac-PIDL [finding]

**FEM-1 mesh convergence result: N_f_fine=77 vs N_f_coarse=82 (Δ=-6.1%, borderline outside 5% gate)**

| Mesh | Tool | Quads | h_tip | ℓ/h_tip | N_f |
|---|---|---|---|---|---|
| Coarse baseline | Abaqus (SENT_mesh.inp) | 77,730 | ≈0.004 mm uniform | ≈2.5 | 82 |
| Fine | gmsh (SENT_pidl_fine_lh5.inp) | 10,261 graded | 0.002 mm | 5 | 77 |

Strict 5% gate: FAIL by 1.1pp. However this is a mixed-tool comparison (Abaqus uniform vs gmsh graded), which introduces node-placement noise. Qualitative shape, K_initial, fracture pattern all match.

**Paper decision pending**: (a) use safe "6.1% spread within mixed-tool noise" caveat; or (b) request gmsh-only h-sweep (mesh_C/M/F variants already in GRIPHFiTH mirror) for clean same-tool convergence proof. Audit Hit 16 status: partially closed (evidence of convergence), phrasing still to confirm.

## 2026-05-05 · Mac-PIDL [finding]

**FEM mesh inventory across campaigns — PIDL series is ℓ/h≈1 (coarse), not community standard**

Three distinct mesh campaigns exist in GRIPHFiTH:

| Campaign | Mesh file | ℓ | h_tip | ℓ/h_tip | Quads |
|---|---|---|---|---|---|
| PIDL series (u=0.08–0.14) | SENT_mesh.inp (Abaqus, Mac-supplied) | 0.01 mm | ~0.01 mm | **~1** | 77,730 |
| Carrara strict-repro (AMOR+MIEHE Basquin sweep) | SENT_carrara_quad.inp | 0.004 mm | 0.0008 mm | **5** | 31,041 |
| PCC concrete smoke (Handoff F) | SENT_pcc_concrete_quad.inp | 5 mm | 1 mm | **5** | 1,107 |

**Key implication**: the PIDL-series FEM reference data (all N_f values used for PIDL/FEM comparison) comes from ℓ/h≈1, which is coarser than the Carrara/community standard of ℓ/h=5. The mesh was kept for back-compat with PIDL training data.

**Paper action item**: need mesh-convergence check — run PIDL-series at Umax=0.12 with ℓ/h=5 mesh, verify N_f within 5%. If it passes, state "legacy mesh retained for PIDL back-compat; convergence verified at representative Umax". If N_f shifts >5%, must decide whether to retrain PIDL with new mesh or caveat.

**Audit Hit 16 status**: still open, this finding confirms it's a real gap.
