# Sidecar Run Ledger: True Adaptive Sampling

**Status**: active ledger  
**Branch**: true adaptive sampling / batch composition sidecar  
**Owner**: Mac-PIDL  
**Rule**: append-only

## Purpose

This file is the run ledger for the true adaptive sampling sidecar. It records what was run, under which code/config state, and what the short verdict was.

This is not the place for long interpretation. Keep each entry compact. If a run changes the branch-level conclusion, record that in:

- `docs/sidecar_true_adaptive_sampling_decisions.md`

The canonical branch spec lives in:

- `docs/sidecar_true_adaptive_sampling.md`

## Required fields for each entry

- date
- run label
- code state or commit
- sampler type
- seed
- `Umax`
- horizon
- archive or output path
- key metrics
- short verdict

## Template

Copy this block for each completed run.

```md
## YYYY-MM-DD · <run label>

- **Code state**: <commit or local working state>
- **Sampler**: <S1-static-tip / S2-detached-score / S3-hybrid>
- **Seed**: <seed>
- **Umax**: <value>
- **Horizon**: <N=... or cycle range>
- **Config summary**: <only branch-defining knobs>
- **Output**: <archive path / log / figure path>
- **Key metrics**: <V4 / V7 / alpha_bar_max / process-zone metrics / N_f if available>
- **Verdict**: <one sentence>
```

## Entries

## 2026-05-12 · branch initialization

- **Code state**: documentation only; no implementation run yet
- **Sampler**: none
- **Seed**: none
- **Umax**: none
- **Horizon**: none
- **Config summary**: sidecar spec created; run ledger and decision memo initialized
- **Output**: `docs/sidecar_true_adaptive_sampling.md`
- **Key metrics**: none
- **Verdict**: branch opened as a documentation-first sidecar; first intended implementation target is `S1-static-tip`

## 2026-05-13 · asamp_S1_rt0.05_np1_seed1_N5 (smoke, DONE)

- **Code state**: branch `claude/sidecar-adaptive-sampling` (worktree `tender-cartwright-7e0b03`); new files: `source/sidecar_sampling.py`, `SENS_tensile/run_sidecar_S1_tip_oversample_umax.py`; hooks in `source/input_data_from_mesh.py`, `source/model_train.py`, `SENS_tensile/config.py`, `SENS_tensile/main.py`. Files rsync'd to Taobo `~/projects/phase-field-pidl/` for the actual run (Mac CPU too slow).
- **Sampler**: `S1-static-tip` (1-to-4 red refinement + green closure on fine mesh near crack tip)
- **Seed**: 1
- **Umax**: 0.12
- **Horizon**: N=5
- **Config summary**: r_tip_sample=0.05, n_refine_passes=1, tip_xy=(0,0); pretrain reused from Mac baseline archive (coarse mesh untouched by design); all competing variants disabled (Williams / Fourier / exact-BC / tip_weight / spAlphaT / psi_hack / C6 reweight = off); symmetry_prior=False; PFF=AT1, vol-split, ν=0.18 (Phase 1 toy units)
- **Compute**: Taobo GPU 1 (CUDA_VISIBLE_DEVICES=1), peak ~4.5 GB / 21% util, wall = 29.5 min (5 cycles)
- **Output**: `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_..._N5_R0.0_Umax0.12_sidecarS1_rt0.05_np1/` (also symlinked from `~/projects/phase-field-pidl/SENS_tensile/`)
- **Refinement diagnostic**: elem 67276 → 81186 (+20.7%); rho_tip(r<0.05) 6.80% → 22.47% (3.3× density boost); area_drift = 0.00e+00 (exact integral conservation)
- **Cycle-by-cycle (S1 vs baseline N=300 same seed)**:
  | cycle | S1 ᾱ_max | Base ᾱ_max | Δ%    | S1 Kt | Base Kt | S1 f_min | Base f_min |
  |-------|----------|------------|-------|-------|---------|----------|------------|
  | 0     | 0.509    | 0.361      | +41%  | 8.74  | 7.53    | 0.982    | 1.000      |
  | 1     | 1.071    | 0.737      | +45%  | 8.85  | 7.58    | 0.405    | 0.654      |
  | 2     | 1.631    | 1.120      | +46%  | 8.91  | 7.59    | 0.220    | 0.381      |
  | 3     | 2.208    | 1.474      | +50%  | 8.75  | 7.53    | 0.136    | 0.257      |
  | 4     | 2.471    | 1.810      | +37%  | 9.15  | 7.53    | 0.113    | 0.187      |
- **Guardrail metrics (S1 cycle 4 NN, evaluated on unrefined mesh for fair vs-baseline)**:
  - V4 mirror tip-ROI RMS = 0.0210, max|skew| = 0.10 — small (baseline-class at N=5)
  - V7 far-side α @ x=+0.5: max = −8.4e-05 (≈0, no spurious damage). α @ x=-0.5 max = 1.0006 (initial slit endpoint, by-design).
  - Dirichlet BC: top |v-0.12| = 0.0000 (exact), bottom v ≈ 0 (clamped per ansatz)
  - Tip α: max 1.0002, mean 0.089 (concentrated, not diffuse)
  - No NaN, no divergence, monotonic ᾱ growth
- **Verdict**: **STRONGLY POSITIVE smoke**. ᾱ_max +37%-50% lift vs baseline at every cycle 0-4 — the target gap closes in the correct direction. Kt stays elevated (8.7-9.2 vs base 7.5-7.6, +17%) — tip stress concentration **preserved (mildly sharpened), NOT collapsed** as in Direction 3 `tipw` (Kt 7.5→1.43 cycle 2) or C6 reweight (Kt→1924 cycle 1). f_min reaches lower (faster fatigue degradation) — consistent with sharper tip α. Guardrails pass at this horizon. Per sidecar promotion rule (Stage S1 success criterion: "ᾱ_max lift without catastrophic training behavior + no major V4/V7 regression"), **S1 qualifies for promotion**. Caveats: N=5 is short — full N=50/100 needed to confirm trajectory holds + check N_f doesn't blow up; multi-seed needed for spread. **Update (see N=50 entry below): smoke lift is real but does NOT persist linearly — peaks early then narrows mid-cycle.**

## 2026-05-13 · asamp_S1_rt0.05_np1_N50 (production, 3 seeds DONE)

- **Code state**: same as smoke entry (no code changes). Branch `claude/sidecar-adaptive-sampling`.
- **Sampler**: `S1-static-tip` r_tip_sample=0.05, n_refine_passes=1, tip_xy=(0,0)
- **Seeds**: 1, 2, 3
- **Umax**: 0.12
- **Horizon**: N=50
- **Config summary**: identical stack to smoke. All competing variants disabled.
- **Compute**: Taobo GPUs 2/3/4 (parallel), wall ~2.5-3 h per seed, ~3.0 min/cycle median
- **Output**: `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_..._Seed_{1,2,3}_..._N50_..._sidecarS1_rt0.05_np1/`
- **Cycle-49 result vs baseline N=300 seed=1**:
  | source | ᾱ_max | Kt    | x_tip   |
  |--------|-------|-------|---------|
  | baseline | 7.719 | 10.36 | +0.217 |
  | S1 seed=1 | 7.232 | 10.60 | +0.227 |
  | S1 seed=2 | 9.516 | 10.02 | +0.214 |
  | S1 seed=3 | 10.492 | 10.24 | +0.215 |
  | S1 mean   | 9.080 ± 1.37 | 10.29 | +0.219 |
- **Trajectory shape (S1 3-seed mean vs baseline same-cycle)**:
  | window | S1 mean lift | comment |
  |--------|-------------|---------|
  | cycle 0-4   | +34%–+50% | smoke result reproduced; large early advantage |
  | cycle 10-29 | +5%       | baseline catches up — S1 lead nearly vanishes mid-cycle |
  | cycle 30-49 | +12%–+18% | S1 pulls ahead again as crack moves into propagation phase |
- **Reproducibility**: 3-seed spread on ᾱ_max @ cycle 49 = **15%** (1.37 / 9.08). For reference, C4+Fourier σ=30 3-seed @ N=100 has 1.4% spread. S1 is **10× looser**.
- **Crack propagation**: S1 ≈ baseline (x_tip 0.214-0.227 vs base 0.217 at cycle 49); the +18% mean lift is in PEAK INTENSITY at the tip, not in propagation rate.
- **Absolute scale**: S1 N=50 mean ᾱ_max = 9.08; C4+Fourier σ=30 N=100 ᾱ_max = **27.93**. S1 alone closes the gap to baseline but does NOT approach the strongest May campaign result.
- **Verdict**: **MODEST POSITIVE, NOT TRANSFORMATIVE**. Sidecar hypothesis confirmed (sampling dilution explains some gap) but the effect size is small, transient in mid-cycle, and seed-dependent. S1 alone is NOT a replacement for C4+Fourier. Two productive follow-ups: (a) does S1 stack with C4 / Fourier — relevant to sidecar-spec "S3 hybrid" once promoted; (b) why the seed spread is so much looser than the architectural mitigations — possible signal that refinement disturbs LBFGS conditioning. Reproducibility issue should be flagged in any §4.7 paper paragraph that uses S1.

## 2026-05-14 · asamp_S1_rt0.05_np1_N300_resume (3 seeds, DONE)

- **Code state**: commit `888c3f2` (S1 only). Resume from N=50 archives by renaming `_N50_` → `_N300_` so the in-archive checkpoint loader picks up at cycle 50 (commit history at `model_train.py:310-348`).
- **Sampler**: same as N=50 run (S1, r=0.05, n_passes=1)
- **Seeds**: 1, 2, 3
- **Umax**: 0.12
- **Horizon**: N=300 nominal (all 3 seeds fractured before cycle 100, run stopped after confirmation window)
- **Compute**: Taobo GPUs 2/3/5 (parallel resume from N=50 ckpt), wall ~2–3 h per seed for cycles 50–N_f
- **Output**: `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_..._Seed_{1,2,3}_..._N300_..._sidecarS1_rt0.05_np1/`
- **N_f result (first detection / confirmation cycle)**:
  | seed | N_f detect | N_f confirm | ᾱ_max @ N_f | Kt @ N_f | x_tip @ N_f |
  |------|------------|-------------|--------------|----------|-------------|
  | 1 | 80 | 90 | 9.30 | 851 | 0.500 |
  | 2 | 83 | 93 | 11.63 | 973 | 0.500 |
  | 3 | 82 | 92 | 14.04 | 1092 | 0.500 |
  | baseline (1 seed) | 84 | — | 9.21 | — | 0.500 |
- **3-seed cycle-by-cycle reference** (stored at `SENS_tensile/S1_sidecar_3seed_reference.csv`, full 91 rows):
  | cycle | ᾱ_max mean ± std | Kt mean ± std | x_tip mean ± std |
  |-------|------------------|----------------|--------------------|
  | 0 | 0.500 ± 0.079 | 8.74 ± 0.38 | 0.0009 ± 0.0000 |
  | 4 | 2.428 ± 0.348 | 8.96 ± 0.34 | 0.0022 ± 0.0008 |
  | 10 | 3.415 ± 0.139 | 10.21 ± 0.31 | 0.0228 ± 0.0009 |
  | 20 | 5.308 ± 0.568 | 8.53 ± 0.06 | 0.0612 ± 0.0008 |
  | 40 | 8.131 ± 1.096 | 9.30 ± 0.07 | 0.1605 ± 0.0040 |
  | 50 | 9.177 ± 1.386 | 10.43 ± 0.11 | 0.2259 ± 0.0052 |
  | 60 | 9.980 ± 1.621 | 12.23 ± 0.25 | 0.2980 ± 0.0065 |
  | 80 | 11.032 ± 1.851 | 240 ± 304     | 0.4660 ± 0.0244 |
- **Visual check (S1 seed=1, alpha snapshots saved at plot_every=20)**:
  `SENS_tensile/hl_8_..._Seed_1_..._N300_..._sidecarS1_rt0.05_np1/diagnostics/tip_tracking_evidence_cycle_{0000,0020,0040,0060,0080}.png` — confirms `get_crack_tip` selects α-front (not boundary noise): candidates 2 → 167 → 299 → 490 → 771 as crack propagates; center (= previous-cycle tip) always trails current tip by ≤ one cycle's L∞ step.
- **Verdict**: S1 fracture trajectory ≈ baseline. **N_f matches baseline within 1–4 cycles** (no systematic acceleration/delay). ᾱ_max at fracture is +27% mean lift vs baseline, consistent with cycle-49 lift, but with **20% spread** across seeds → reproducibility concern stays. Crack always exits at right boundary (x_tip = 0.500). **This reference is the comparison target for all subsequent S2 production runs.**

## 2026-05-13 · asamp_S2_v1 (smoke, CRASHED at end of cycle 0)

- **Code state**: commit `f623264` (S2 v1: aggregate-to-original + expand). PRE-bug-fix.
- **Sampler**: `S2-{tipfol,scored}` per-cycle mesh swap via parent-index expand/aggregate
- **Seeds**: 1
- **Umax / Horizon**: 0.12 / N=5
- **Crash**: IndexError at `model_train.py:716` — `_psi0[_nominal_mask]` shape mismatch. `_nominal_mask` was built once from ORIGINAL mesh (67276 elem) before the loop; S2 swap on cycle 0 produced 81186 elem; Kt-logging boolean index hit `dim is 81186 but corresponding boolean dimension is 67276`. Reported by expert review of `f623264`. Reproduced exactly on Taobo: both S2a (GPU 0) and S2b (GPU 1) crashed at end of cycle 0 after 9 min training.
- **Verdict**: P0 design bug, captured in commit `5ee76f4` along with P1 (score-aggregation density bug, see below).

## 2026-05-13 · asamp_S2_v2 (smoke, P0+P1 fixed)

- **Code state**: commit `5ee76f4` (`_nominal_mask` rebuilt after swap + score density-aggregated). v1 transport unchanged (still aggregate→expand on original mesh).
- **Sampler**: S2a tip_following / S2b score_driven, r_tip=0.05, target_fraction=0.07, n_passes=1
- **Seeds**: 1 (both modes)
- **Compute**: Taobo GPUs 0/1
- **Cycle-by-cycle (S1 ref = `asamp_S1_rt0.05_np1_seed1_N5`)**:
  | cycle | S1 ᾱ | S2a ᾱ | S2b ᾱ | S2a Kt | S2b Kt |
  |-------|------|-------|-------|--------|--------|
  | 0 | 0.509 | 0.470 | 0.470 | 9.05 | 9.05 |
  | 1 | 1.071 | 0.925 | 0.894 | 9.06 | 8.72 |
  | 2 | 1.631 | 1.277 | 1.250 | 8.74 | 8.44 |
  | 3 | 2.208 | 1.712 | 1.650 | 9.06 | 8.54 |
  | 4 | 2.471 | 2.015 | 2.068 | 8.91 | 8.44 |
- **Observation**: per-cycle re-aggregation + re-expansion (round-trip on ORIGINAL mesh) destroys sub-parent variation in `hist_fat`/`psi_plus_prev`. The tip child of a refined parent accumulates ᾱ fast; the area-weighted mean over all 4 children washes that locality out. Cycle 4 ᾱ_max ≈ -16 to -18% vs S1 — the very locality the refinement was meant to resolve is what we destroy each cycle.
- **Verdict**: **Mechanism wrong**, fixes don't address the structural transport issue. Expert flagged in next review. Drove v2 design.

## 2026-05-14 · asamp_S2_v2 (smoke, transport replaced)

- **Code state**: commit `218efaa` (nearest-element transport via scipy.spatial.cKDTree + hysteresis on tip motion; aggregate-to-original kept ONLY for score, not for hist_fat). Spec: `sidecar_sampling.py:nearest_element_transport`, `model_train.py:540-660`. `--hysteresis-fraction` default = 0.25.
- **Sampler**: S2a tip_following / S2b score_driven, r_tip=0.05, target_fraction=0.07, hysteresis=0.0125 (= 0.25 × 0.05)
- **Seeds**: 1 (both modes)
- **Compute**: Taobo GPUs 0/1, wall ~45 min total
- **REFINE/SKIP pattern**: cycle 0 always REFINE (init); cycles 1-4 all SKIP (|Δtip| L¹ stayed < 0.0125, x_tip max = 0.0026). swaps=1, skips=4 throughout.
- **Cycle-by-cycle**:
  | cycle | S1 ᾱ | S2 v1 | **S2 v2** | v2 vs S1 |
  |-------|------|-------|-----------|-----------|
  | 0 | 0.509 | 0.470 | 0.470 | -7.7% |
  | 1 | 1.071 | 0.925 | 0.946 | -12% |
  | 2 | 1.631 | 1.277 | 1.427 | -13% |
  | 3 | 2.208 | 1.712 | 1.874 | -15% |
  | 4 | 2.471 | 2.015 | **2.308** | **-7%** |
- **Closes ~60% of v1 gap** (-18% → -7%). hysteresis works exactly as designed (cycle 0 REFINE then 4 SKIPs since tip is stationary). Remaining gap traced to cycle 0's `hist_alpha` re-evaluation via NN (gives α≈0 everywhere from pretrain state) instead of `hist_alpha_init(crack_geometry)` (α=1 at initial crack nodes). The irreversibility penalty was inactive at the initial slit on cycle 0 → energy balance shifted → ᾱ_max bleeds for all 5 cycles.
- **Verdict**: Mechanically much better than v1, but cycle 0 hist_alpha init is the remaining wart. Drove v2.1.

## 2026-05-15 · asamp_S2_v2.1 (smoke, hist_alpha_init fix)

- **Code state**: commit `04f7969`. On `_S2_state['n_swaps'] == 1` (first swap), use `hist_alpha_init(inp, matprop, pffmodel, crack_dict)` from `utils.py:73`; otherwise NN re-eval. Same nearest-element transport + hysteresis as v2.
- **Sampler**: identical to v2
- **Seeds**: 1 (both modes)
- **Compute**: Taobo GPUs 0/1
- **Cycle-by-cycle**:
  | cycle | S1 ᾱ | **S2a v2.1** | S2a Kt | S1 Kt |
  |-------|------|--------------|--------|--------|
  | 0 | 0.5092 | **0.5092** | 8.74 | 8.74 |
  | 1 | 1.0712 | **1.0712** | 8.85 | 8.85 |
  | 2 | 1.6308 | **1.6308** | 8.91 | 8.91 |
  | 3 | 2.2080 | **2.2080** | 8.75 | 8.75 |
  | 4 | 2.4709 | **2.4709** | 9.15 | 9.15 |
- **S2a == S2b == S1 to 4 decimals at every cycle.** Verifies the v2 + v2.1 design is mathematically equivalent to S1 in the static-tip regime. Hysteresis SKIPs cycles 1-4 (no transport invoked), so the test isolates cycle-0 mechanics: with `hist_alpha_init` the initial condition matches S1 exactly; the rest follows.
- **Verdict**: **Acceptance gate PASSED**. S2 v2.1 is a strict superset of S1's behaviour: equivalent in static-tip regime, capable of dynamic refinement when tip moves past hysteresis. Ready to promote to N=100 production where tip actually propagates.

## 2026-05-15 · asamp_S2a_tipfol_N100_seed1 (production, in flight)

- **Code state**: commits `888c3f2` … `8936928` (= up to runner `--plot-every`)
- **Sampler**: S2a `tip_following`, r_tip=0.05, n_passes=1, hysteresis_fraction=0.25
- **Seeds**: 1 (per expert: launch seed=2/3 only after first dynamic REFINE confirms healthy)
- **Umax / Horizon**: 0.12 / N=100
- **Compute**: Taobo GPU 2 (PID 582689), launch 2026-05-15 17:23 CST, `--plot-every 10` for diagnostics
- **Output**: `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_..._N100_..._sidecarS2_tipfol_rt0.05_np1/`
- **Acceptance gates (from expert)**:
  1. cycle 4 ᾱ_max ≈ S1 ref (2.43 ± 0.35) — confirms implementation matches v2.1 smoke
  2. REFINE/SKIP pattern: SKIP while |Δtip|<0.0125 then REFINE when tip moves past threshold. First dynamic REFINE expected ~cycle 10 (S1 ref x_tip = 0.0228 at cycle 10, well past hysteresis)
  3. cycle 50/100 ᾱ_max ≥ S1 ref at same cycle (S1 cycle 50 = 9.18 ± 1.39); cycle 80+ Kt jump (fracture) at or near S1 N_f = 80-83
- **Status**: cycle 1 done, ᾱ_max = 1.0712 (= S1 cycle 1 exact), Kt = 8.85 ✓
- **Monitor**: background task `bvp7xf9ch` watching for 2nd REFINE log line (= first dynamic refine); ETA ~25 min from launch

## 2026-05-18/19 · asamp_S2a_v3.2_transport_and_hysteresis_diagnostics

- **Code state**: branch `claude/sidecar-adaptive-sampling`, HEAD `3e78f92` plus local diagnostic prints and the hysteresis default patch. v3.2 changes `hist_alpha` transport from nearest-node/NN re-eval to conservative L2 edge-lineage transport plus an NN-max floor. Diagnostic prints only report `hist_fat` transport and per-cycle `Δhist_fat`; they do not change the physics loss.
- **Sampler**: S2a `tip_following`, `r_tip=0.05`, `n_passes=1`, seed 1, `Umax=0.12`.
- **Static-regime gate**: N=5 v3.2 passed exactly against S1 seed 1:
  | cycle | S1/S2 v3.2 ᾱ_max | Kt |
  |-------|------------------:|---:|
  | 0 | 0.5092 | 8.74 |
  | 1 | 1.0712 | 8.85 |
  | 2 | 1.6308 | 8.91 |
  | 3 | 2.2080 | 8.75 |
  | 4 | 2.4709 | 9.15 |
- **Diagnostic A — old hysteresis (`hysteresis_fraction=0.25`, threshold 0.0125)**:
  - Log: `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/diag_S2a_v32_N20_histfat_gpu2_20260518.log`
  - First dynamic REFINE at cycle 8 preserved history values:
    `hist_fat old max=2.6524@(+0.0043,-0.0007) -> new max=2.6524@(+0.0043,-0.0007)`.
  - But global ᾱ_max flattened after remesh:
    | cycle | S1 seed1 ᾱ_max | S2 v3.2 h=0.25 ᾱ_max |
    |-------|----------------:|----------------------:|
    | 7 | 2.6524 | 2.6524 |
    | 8 | 2.8793 | 2.6524 |
    | 9 | 3.0978 | 2.6524 |
    | 10 | 3.2782 | 2.6524 |
    | 19 | 4.5003 | 3.0310 |
  - Interpretation: not a `hist_alpha` or `hist_fat` reset. The remesh happened while the tracked tip was still inside the original refined ball (`x_tip≈0.014` vs `r_tip=0.05`), and the mesh/optimizer path changed too early.
- **Diagnostic B — root+tip union refinement (`h=0.25`, root zone kept refined)**:
  - Log: `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/union_S2a_v32_N20_root_tip_gpu4_20260519.log`
  - Result: negative. Keeping both root and current-tip zones refined did **not** restore accumulation; final cycle 19 stayed near `ᾱ_max=2.6552`.
  - Interpretation: the plateau was not caused by losing root-zone density.
- **Diagnostic C — conservative hysteresis (`hysteresis_fraction=1.0`, threshold 0.05)**:
  - Log: `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hyst1_S2a_v32_N20_gpu5_20260519.log`
  - Key behavior: cycles 8, 10, and 15 SKIP-REFINE while the tip remains inside the existing refined ball. First dynamic remesh is delayed until cycle 18, when `x_tip≈0.0500`.
  - Result: exact S1 match through cycle 17; small post-remesh gap after cycle 18:
    | cycle | S1 seed1 ᾱ_max | S2 v3.2 h=1.0 ᾱ_max | note |
    |-------|----------------:|---------------------:|------|
    | 7 | 2.6524 | 2.6524 | exact |
    | 8 | 2.8793 | 2.8793 | exact |
    | 9 | 3.0978 | 3.0978 | exact |
    | 10 | 3.2782 | 3.2782 | exact |
    | 11 | 3.4317 | 3.4317 | exact |
    | 17 | 4.2465 | 4.2465 | exact, before first dynamic remesh |
    | 18 | 4.3820 | 4.2475 | -3.1%, first dynamic remesh |
    | 19 | 4.5003 | 4.2489 | -5.6%, still far better than h=0.25 |
- **Verdict**: **S2 v3.2 transport is healthy; the major bad N20 result was an over-eager remesh policy.** Production default changed from `hysteresis_fraction=0.25` to `1.0`. Root+tip union is not the fix. `h=1.0` eliminates the c8 plateau and matches S1 exactly until the first truly necessary remesh at c18; after that remesh a small gap reappears. Next gate: run a clean N100 S2a seed 1 with the new default and monitor whether the post-remesh gap remains bounded or compounds.

## 2026-05-20 · asamp_S2a_N40_adaptive_lambda_hist (launched)

- **Code state**: branch `claude/sidecar-adaptive-sampling` plus local adaptive-λ patch. The default physics loss is unchanged unless `fatigue_dict["adaptive_lambda_hist"]["enable"] = True`; the N40 runner enables it explicitly.
- **Motivation**: Wang-style PINN gradient-pathology diagnostic at S2 cycle 29 showed post-REFINE `E_hist` parameter-gradient norm dominating the physical terms:
  `grad_l2(E_el)=4.57`, `grad_l2(E_d)=8.43`, `grad_l2(E_hist)=2182`. This suggests the post-remesh optimizer is dominated by the irreversibility penalty rather than the elastic/dissipation physics terms.
- **Mechanism**: after each S2 REFINE, compute
  `lambda_hat = max(||grad E_el||_2, ||grad E_d||_2) / ||grad E_hist||_2`, clipped to `[1e-3, 1]`, then use `log10(E_el + E_d + lambda_hist * E_hist)` for subsequent fit cycles. With the cycle-29 diagnostic numbers, the first update would be about `3.86e-3`.
- **Run**: Taobo GPU3, PID `1515969`, log `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/S2a_v32_N40_adapthist_gpu3_20260520_065714.log`.
- **Archive**: `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N40_R0.0_Umax0.12_sidecarS2_tipfol_rt0.05_np1_adapthist/`.
- **Warm start**: copied from the completed N20 `hyst1_diag` archive and patched `checkpoint_step_19.pt` with `_S2_state` so S2 resumes safely on the current refined mesh. Startup confirmed: restored `40761` nodes / `81300` elements, `swaps=2`, `skips=17`, `tip_at_refine=(0.05004344880580902, 0.0)`, then continued `step 20/39`.
- **Watch points**: first adaptive λ update should occur at the next REFINE, expected near cycle 29. Check the log for `[AdaptiveLambdaHist cycle 29]` and then compare `alpha_bar_max` trajectory against the concurrent fixed-λ N100 diagnostic and the N20 `h=1.0` reference.

## 2026-05-24 · baseline vs v4 scheduled adaptive_lambda_hist N20 (launched)

- **Code state**: commit `af5a533` on branch `claude/sidecar-adaptive-sampling`. This adds scheduled adaptive-λ updates so the same gradient-balancing diagnostic can run on both fixed baseline mesh and v4 add-only refinement. Default config remains unchanged unless the runner passes `--adaptive-lambda-hist`.
- **Mechanism**: at the start of each eligible cycle, compute parameter-gradient norms for `E_el`, `E_d`, and `E_hist`; set
  `lambda_hat = max(||grad E_el||_2, ||grad E_d||_2) / ||grad E_hist||_2`, clipped to `[1e-3, 1]`; then fit with `log10(E_el + E_d + lambda_hist * E_hist)`.
- **Run root**: fresh clone at `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533/`; archives redirected to `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533-runs/`.
- **Baseline N20**: Taobo GPU4, PID `1922288`, log `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533/SENS_tensile/logs/baseline_N20_adapthist_gpu4_20260524_055926.log`.
  Archive: `.../hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N20_R0.0_Umax0.12_baseline_adapthist/`.
- **v4 add-only N20**: Taobo GPU5, PID `1922289`, log `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533/SENS_tensile/logs/v4_N20_adapthist_gpu5_20260524_055926.log`.
  Archive: `.../hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N20_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_adapthist_sched1/`.
- **Watch points**: compare `lambda_hist_vs_cycle.npy`, `alpha_bar_max_vs_cycle.npy`, and final fracture/tip trajectory against fixed-λ baseline and fixed-λ v4. If scheduled adaptive λ only helps v4 after remesh but hurts baseline, it is an optimizer-remesh rescue, not a new physical model.
- **Startup correction**: both jobs reached the end of pretrain, then failed because the fresh clone was missing `meshed_geom2.msh` (`FileNotFoundError`). This is an environment/setup miss, not an adaptive-λ result.

## 2026-05-24 · hard irreversibility baseline vs v4 N20 (launched)

- **Code state**: commit `41e0bf1` on branch `claude/sidecar-adaptive-sampling`. Adds a diagnostic hard constraint:
  `alpha = hist_alpha + (1 - hist_alpha) * alpha_free`, with `E_hist` soft-penalty weight set to `0`. The physical terms stay `E_el + E_d` with `lambda_el=lambda_d=1`.
- **Run root**: rsynced worktree at `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-41e0bf1/`; archives redirected to `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-41e0bf1-runs/`. Both `meshed_geom1.msh` and `meshed_geom2.msh` copied from the main Taobo project before launch.
- **Baseline N20 hard-irreversibility**: Taobo GPU4, PID `1949049`, log `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-41e0bf1/SENS_tensile/logs/baseline_N20_hardirr_gpu4_20260524_061842.log`.
  Archive: `.../hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N20_R0.0_Umax0.12_baseline_hardirr/`.
- **v4 add-only N20 hard-irreversibility**: Taobo GPU5, PID `1949050`, log `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-41e0bf1/SENS_tensile/logs/v4_N20_hardirr_gpu5_20260524_061842.log`.
  Archive: `.../hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N20_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_hardirr/`.
- **Startup verified**: logs show `irreversibility = hard transform | E_hist weight = 0` and `[HardIrreversibility] floor set (coarse pretrain)`.
- **Watch points**: if this improves baseline and v4 field/fracture behavior, the soft irreversibility penalty was materially distorting optimization. If it worsens crack growth, the hard transform may overconstrain early damage and needs a smoother slack/reparameterization.

## 2026-05-24 · hard irreversibility with sigmoid alpha_free N5 smoke (launched)

- **Code state**: commit `6525a9f` changes the hard-irreversibility branch so the free alpha is strictly bounded:
  `alpha_free = sigmoid(raw_alpha)`, `alpha = hist_alpha + (1 - hist_alpha) * alpha_free`. This replaces the first N20 attempt's use of `NonsmoothSigmoid(raw_alpha)`, which produced NaNs.
- **Run root**: rsynced worktree at `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f/`; archives redirected to `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f-runs/`.
- **Baseline N5 hard-irreversibility**: Taobo GPU5, PID `1853757`, log `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f/SENS_tensile/logs/baseline_N5_hardirr_sigmoid_gpu5_20260525_054706.log`.
  Archive: `.../hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N5_R0.0_Umax0.12_baseline_hardirr/`.
- **v4 add-only N5 hard-irreversibility**: Taobo GPU6, PID `1853758`, log `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f/SENS_tensile/logs/v4_N5_hardirr_sigmoid_gpu6_20260525_054706.log`.
  Archive: `.../hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N5_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_hardirr/`.
- **Startup verified**: both logs show hard transform enabled and coarse pretrain floor set; GPUs 5/6 active.
- **Result**: both N5 smokes completed without NaNs.
  | cycle | baseline ᾱ_max | v4 ᾱ_max |
  |-------|----------------:|---------:|
  | 0 | 0.74229 | 0.74772 |
  | 1 | 1.4833 | 1.5096 |
  | 2 | 2.2494 | 2.2685 |
  | 3 | 3.0214 | 3.0212 |
  | 4 | 3.7819 | 3.7747 |
- **Interpretation**: strict `sigmoid(raw_alpha)` fixes the NaN failure of the first hard-constraint attempt. Over N5, hard baseline and hard v4 are essentially identical; this is expected because v4 only refines at cycle 0 and the tip has not moved far enough to exercise dynamic remesh behavior.

## 2026-05-24 · hard irreversibility sigmoid N20 resume (launched)

- **Basis**: resumed separately from the successful N5 sigmoid-hard archives above by copying each N5 archive to the corresponding N20 archive name, preserving `checkpoint_step_4.pt`, `trained_1NN_4.pt`, and history `.npy` files. This is a true resume, not a restart.
- **Baseline N20 hard-irreversibility**: Taobo GPU5, PID `2214391`, log `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f/SENS_tensile/logs/baseline_N20_hardirr_sigmoid_resume_gpu5_20260525_061852.log`.
  Archive: `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f-runs/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N20_R0.0_Umax0.12_baseline_hardirr/`.
- **v4 add-only N20 hard-irreversibility**: Taobo GPU6, PID `2214392`, log `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f/SENS_tensile/logs/v4_N20_hardirr_sigmoid_resume_gpu6_20260525_061852.log`.
  Archive: `gpu-taobo:/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f-runs/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N20_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_hardirr/`.
- **Startup verified**: both logs show `[Checkpoint] 从 step 4 恢复，继续 step 5/19`; v4 also restored the current refined mesh (`40704` nodes, `81186` elements, `swaps=1`, `skips=4`).
