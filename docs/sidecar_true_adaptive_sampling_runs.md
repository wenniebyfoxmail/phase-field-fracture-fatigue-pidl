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
