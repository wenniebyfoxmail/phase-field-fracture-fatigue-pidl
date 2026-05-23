# Sidecar Decision Memo: True Adaptive Sampling

**Status**: active memo  
**Branch**: true adaptive sampling / batch composition sidecar  
**Owner**: Mac-PIDL  
**Rule**: append-only

## Purpose

This file records branch-level decisions. Use it when we decide to promote, pause, retire, or redefine the sidecar.

Do not use this file as a run log. Per-run facts belong in:

- `docs/sidecar_true_adaptive_sampling_runs.md`

The canonical branch spec lives in:

- `docs/sidecar_true_adaptive_sampling.md`

## What belongs here

- opening the branch
- changing the hypothesis
- changing what counts as a valid implementation
- promoting one stage to the next
- pausing the branch
- retiring the branch

## Entry template

```md
## YYYY-MM-DD · <decision label>

- **Decision**: <promote / pause / retire / redefine / open>
- **Based on**: <run ids, files, or discussion anchors>
- **Reason**: <2-5 concise bullets or short paragraph>
- **Implication**: <what changes next>
```

## Entries

## 2026-05-12 · sidecar opened

- **Decision**: open
- **Based on**: `docs/sidecar_true_adaptive_sampling.md`
- **Reason**: this branch is the cleanest next test of the sampling-dilution hypothesis because it keeps the base Deep Ritz + Carrara objective fixed while changing collocation density or batch composition only.
- **Implication**: the first implementation target should be `S1-static-tip`; no weighted-energy variant should be treated as part of this sidecar unless the branch definition is explicitly revised.

## 2026-05-13 · S1 smoke clears promotion bar

- **Decision**: promote S1 to a longer-horizon production run + multi-seed reproducibility
- **Based on**: `docs/sidecar_true_adaptive_sampling_runs.md` entry `asamp_S1_rt0.05_np1_seed1_N5`
- **Reason**:
  - ᾱ_max lift **+37% to +50%** vs baseline at every cycle 0-4, with **no catastrophic training** (no NaN, no Kt collapse, no field explosion).
  - Kt **preserved and slightly elevated** (8.7-9.2 vs base 7.5-7.6, +17%) — qualitatively opposite to Direction 3 (`tipw`, Kt 7.5→1.43 collapse) and C6 reweight (Kt→1924 far-edge explosion). Confirms the sidecar hypothesis that the failure mode of weighted-loss variants was the LOSS REWEIGHTING, not the goal of emphasising the tip; pure sampling does NOT trip the same pathology.
  - Guardrails clean at this horizon: V4 tip-ROI mirror RMS = 0.021, V7 far-side α ≈ 0, Dirichlet BCs exact, tip α concentrated (max 1.0, mean 0.089 in |x|,|y|<0.05).
  - Mesh-refinement integrator-side check: area conservation 0 drift, CCW preserved, +20.7% elements (67k→81k).
- **Implication**:
  - Promote to **N=50 production** at Umax=0.12 seed=1 to verify trajectory + first N_f.
  - Add **2 reproducibility seeds** (seed=2, seed=3) at the promoted horizon.
  - Hold S2 (detached-score resampling) and S3 (hybrid) until S1 production trajectory confirms — per sidecar spec, S2 only worth building if S1 signal is real on a longer horizon.
  - Do NOT yet stack with C4 / Fourier / Williams — sidecar Rule 4 (clean comparison stack) until S1-alone is validated; composition with C4+Fourier is a follow-up question, not part of the S1 verdict.
  - Keep alert for N_f overshoot: if S1 dramatically accelerates fatigue (e.g. N_f drops far below baseline 85), that could be a sign the increased density also amplifies the tip-overdrive failure mode that produced the baseline localization gap in the first place — still informative, but reframes "lift" as "different equilibrium" rather than "better field realism".

## 2026-05-13 · S1 N=50 production — modest positive, not transformative

- **Decision**: keep S1 as a documented partial-positive sidecar; do NOT add another S1-only horizon; redirect next effort toward stacking (S1 + C4 / S1 + Fourier) before considering S2.
- **Based on**: `docs/sidecar_true_adaptive_sampling_runs.md` entry `asamp_S1_rt0.05_np1_N50` (3 seeds, Taobo GPUs 2/3/4, all completed cleanly).
- **Reason**:
  - Smoke +37–+50% lift at cycle 0-4 was **not a stable trajectory feature** — it narrows to +5% over cycle 10-29 then recovers to +12-18% over cycle 30-49. The "promote on smoke" decision was correct as a gate but over-extrapolated the effect size; the production trajectory is the binding measurement.
  - Cycle-49 3-seed mean ᾱ_max = 9.08 vs baseline 7.72 → **+18% mean lift** — directionally positive, mechanism clean, but quantitatively smaller than C4-alone (~+170% vs baseline at N=100) or C4+Fourier (~+200% vs baseline at N=100).
  - 3-seed spread = **15%** (1.37 / 9.08) is roughly 10× looser than C4+Fourier (~1.4% at N=100). Refinement appears to disturb optimizer conditioning enough that seed → ᾱ_max sensitivity is high. Production paper claims using S1 alone would need this caveat foregrounded.
  - Crack-tip propagation rate ≈ baseline (x_tip 0.214-0.227 vs base 0.217 at cycle 49). The +18% lift is in peak intensity at the tip, not in propagation kinetics — confirms the original "sampling dilution near tip" hypothesis but bounds its practical magnitude.
  - Guardrails (V4 / V7 / Dirichlet / Kt) all clean at N=50. No pathology like Direction 3 or C6 — sampling mechanism remains qualitatively safe.
- **Implication**:
  - **Sidecar declared "modest positive, branch closed for solo work"**. Sufficient evidence collected to write a ~½-page §4.7 paragraph: "Sampling dilution explains a portion of the PIDL-FEM gap, but the dominant lever is representation-side (C4 exact BC + Fourier σ=30), not sampling-side."
  - **Skip S2** (detached cycle-wise importance resampling) and **skip S3** (hybrid) as separate work — S2 buys us at most the gap between static r=0.05 prior and an adaptive-but-similar prior, which is bounded above by the +18% we just measured. Not worth ~3-4 days of dev for a likely ≤ +5% increment.
  - **Next productive question (NOT this sidecar)**: does S1 (mesh-side) stack with C4+Fourier (representation-side)? Run a 1-seed N=50 smoke of S1 + C4 + Fourier-σ30; if cycle-49 ᾱ_max > 30 (above C4+Fourier N=100 baseline 27.93), then promote. If S1 adds nothing on top, retire entirely.
  - **Reproducibility note**: 15% S1 spread means any future stack run NEEDS multi-seed. Do not present a 1-seed S1 stack number in the paper.
  - **Open follow-up**: investigate WHY S1 spread is so much wider than C4+Fourier — suspected cause is LBFGS conditioning on a non-uniform mesh (some triangles 4× smaller than neighbours → larger gradient-magnitude variance per parameter). If real, this is a methodological note for any future mesh-side adaptive sampling work.

## 2026-05-13 · S2 reopened — override prior "skip S2" decision

- **Decision**: **reopen** sidecar S2 (tip-following + score-driven). Override the 2026-05-13 "skip S2" decision above.
- **Based on**: re-reading of S1 N=50 trajectory ("S1 mean lift" table in `runs.md`) and user discussion 2026-05-13.
- **Reason**:
  - Prior "skip S2" reasoning assumed the +18% N=50 ceiling was the upper bound for any geometric-prior variant. That bound was tied to **a single failure mode** (static refinement at (0,0) becomes misaligned as the tip propagates), not to the sampling-dilution hypothesis itself.
  - At N=50 the tip moves to x≈0.22; the S1 r=0.05 zone at (0,0) becomes irrelevant past cycle ~10. S2's tip-following directly addresses this misalignment — the failure mode is by design.
  - S1's mid-cycle narrowing (+50% → +5% at cycle 10-29) is consistent with this: the static prior provides early lift, then the tip leaves the refined zone, then the lift bleeds back only because ᾱ_max can still grow in the static zone.
- **Implication**:
  - Build S2a (tip_following): cycle-wise re-refinement using the current `_x_tip_history[-1]` as `tip_xy`. Pure geometry, no score.
  - Build S2b (score_driven) in parallel: detached score `|E_el_e| + |E_d_e|` → top-K elements → next cycle's refinement mask. Detached so it is sampling-only, not loss reweight (sidecar Rule 1).
  - Hold S1 N=100 / N=300 production until S2 N=5 smoke clears acceptance bar (≥ S1 cycle 4 ᾱ_max).
  - Expert review will be requested at each design commit; explicit acceptance criteria recorded per stage.

## 2026-05-14 · S2 v2 — transport replaced with nearest-element after v1 smoke failure

- **Decision**: redesign S2 per-cycle state transport. Drop `aggregate_to_original`+`remap_element_field` (round-trip on ORIGINAL mesh) for `hist_fat`/`psi_plus_prev`. Replace with **centroid-nearest transport directly between consecutive refined meshes** (`sidecar_sampling.py:nearest_element_transport`, scipy.spatial.cKDTree). Add **hysteresis** on tip motion to skip re-refinement when |Δtip|_L1 < `hysteresis_fraction × r_tip_sample` (default 0.25 × 0.05 = 0.0125).
- **Based on**: `runs.md` entry `asamp_S2_v2` (P0+P1 fixed, still -16…-18% vs S1 N=5).
- **Reason**:
  - v1 transport (aggregate → expand) does area-weighted MEAN over each parent's children. For a peaked quantity like `hist_fat` with one tip-side child holding 10 and others holding 0, the parent value becomes 2.5; on expand, all 4 children get 2.5 — sub-parent locality erased. This is a structural failure of the transport choice, not a numerical bug.
  - Centroid-nearest preserves sub-parent variation: each new-mesh element inherits the closest old-mesh value. For overlapping refined meshes (only the tip neighbourhood differs cycle-to-cycle), most elements are identity-mapped, and the tip child keeps its peak value.
  - Hysteresis on tip motion avoids burning compute on re-refinements that produce essentially the same mask (during stationary-tip cycles). Empirically the tip is stationary for the first ~10 cycles at Umax=0.12, so hysteresis preserves cycle 0's refinement for those.
  - Unit-tested: identity transport returns the array bit-exact; peak preservation across overlapping refined meshes confirmed; integrals preserved.
  - Density-aggregation for the S2b score is retained — score is point-evaluated (not cumulative), so the density mean over children IS the correct quantity for parent-level top-K selection.
- **Implication**:
  - First N=5 smoke of v2 narrowed the gap to -7% (down from -18% in v1). Direction is right; the remaining gap is no longer transport.
  - Diagnostic: 3-seed S1 reference now sets cycle 4 = 2.43 ± 0.35. v2 cycle 4 = 2.308 is just inside one std below the mean. NOT a flat negative result; one more fix needed before accepting.

## 2026-05-15 · S2 v2.1 — hist_alpha_init fix closes the last gap

- **Decision**: on the first S2 mesh swap (`_S2_state['n_swaps'] == 1`), use `hist_alpha_init(inp, matprop, pffmodel, crack_dict)` (crack-geometry init) for `hist_alpha`. On subsequent swaps, NN re-evaluation is correct.
- **Based on**: v2 cycle 4 was bit-stable in the SKIP-only regime (cycles 1-4 reuse cycle-0 mesh with nearest-transport never invoked), so the -7% had to live in cycle 0 mechanics alone. v2 set cycle-0 `hist_alpha` via `field_comp.fieldCalculation(inp)` at the pretrain NN state — α≈0 everywhere, NOT α=1 at the initial slit. S1's prep_input_data → `hist_alpha_init` path produces α=1 at initial crack nodes, which is what the irreversibility penalty needs.
- **Reason**:
  - v2.1 N=5 cycle 0 ᾱ_max = 0.5092 — bit-exact match to S1 cycle 0 (was 0.470 in v2).
  - Cycles 1-4 follow the same exact-match (1.0712, 1.6308, 2.2080, 2.4709) since hysteresis SKIPs and the only difference between v2.1 and S1 in this regime is the cycle-0 initial state. With that fixed, S2 v2.1 ≡ S1 in static-tip regime to 4 decimals.
- **Acceptance gate (expert)**: cycle 4 ᾱ_max within 1-2% of S1 ref. **Passed by far stronger margin** (0% gap, bit-exact). Promote to N=100 production seed=1 to test dynamic regime.
- **Implication**:
  - S2 v2.1 is a strict superset of S1: equivalent in static-tip regime, adaptive when tip moves past hysteresis.
  - **Launch S2a N=100 seed=1 only.** Expert: defer seed=2/3 until first dynamic REFINE event confirms the moving-tip path is healthy (predicted ~cycle 10 from S1 ref x_tip = 0.023 at cycle 10).
  - Hold S2b N=100 entirely until S2a single-seed verdict is in — S2b adds the score-mask variable on top of the dynamic mechanism, harder to interpret in isolation.
  - Cancel the prior plan to launch S1 + C4 + Fourier stack until S2a-alone trajectory is collected — order of evidence: confirm dynamic mechanism first, then stack questions.

## 2026-05-19 · S2 v3.2 — redefine dynamic remesh hysteresis

- **Decision**: redefine the S2a production policy from `hysteresis_fraction=0.25` to `hysteresis_fraction=1.0`. Keep the CLI override for diagnostics. Do not promote root+tip union refinement.
- **Based on**: `docs/sidecar_true_adaptive_sampling_runs.md` entry `asamp_S2a_v3.2_transport_and_hysteresis_diagnostics`, especially the paired N20 Taobo diagnostics:
  - `diag_S2a_v32_N20_histfat_gpu2_20260518.log` (`h=0.25`)
  - `hyst1_S2a_v32_N20_gpu5_20260519.log` (`h=1.0`)
  - `union_S2a_v32_N20_root_tip_gpu4_20260519.log` (root+tip negative control)
- **Reason**:
  - v3.2 conservative `hist_alpha` transport and nearest-element `hist_fat` transport preserve history through REFINE; the old plateau is not a reset bug.
  - With `h=0.25`, the first dynamic remesh fires at cycle 8 when the tip has moved only `x_tip≈0.014`, still deep inside the existing `r_tip=0.05` refined ball. That over-eager mesh rebuild flattens `alpha_bar_max` at `~2.6524`.
  - With `h=1.0`, S2 skips that premature remesh and matches S1 seed 1 exactly through cycle 17. The first dynamic remesh occurs at cycle 18 when `x_tip≈0.0500`; after that, the N20 smoke ends with a small c19 gap (`4.2489` vs S1 `4.5003`, -5.6%) rather than the old c19 failure (`3.0310`, -32.7%).
  - Root+tip union keeps the root zone refined but still plateaus (`c19≈2.6552`), so the fix is mesh stability, not adding a second refinement zone.
- **Implication**:
  - Production S2a should remesh only when the tracked tip has moved about one refine radius from the last refinement center.
  - The next valid production run is a clean N100 S2a seed 1 with the new default (`h=1.0`), watching whether the post-remesh gap remains bounded or compounds after multiple dynamic remeshes.
  - S2b remains on hold until S2a h=1.0 clears the dynamic-remesh gate.

## 2026-05-20 · adaptive λ_hist opened as a diagnostic intervention

- **Decision**: open a narrow N40 S2a experiment with adaptive `λ_hist`; do not change the default S2 objective.
- **Based on**: post-REFINE gradient-norm diagnostic from the fixed-λ S2a N100 resume at cycle 29:
  `||grad E_hist||_2=2.18e3` vs `||grad E_el||_2=4.57` and `||grad E_d||_2=8.43`.
- **Reason**:
  - The dynamic-remesh gap appears immediately after REFINE even when history transport is mostly preserved, so optimizer conditioning is now a plausible bottleneck.
  - The Wang 2020 takeaway is about gradient imbalance, not raw loss magnitudes; balancing the `E_hist` gradient directly is the least invasive test.
  - `λ_hist` is clipped to `[1e-3, 1]`, so it can only reduce an over-dominant history penalty and cannot amplify it beyond the original physics.
- **Implication**:
  - Run only N40 first, warm-started from the validated N20 `h=1.0` checkpoint, and inspect the first adaptive update around cycle 29 before promoting any longer horizon.
  - Treat this as a diagnostic branch layered on S2a, not a replacement for the clean fixed-λ S2a production baseline.
