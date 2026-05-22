# Successor Handoff: S2 Adaptive Sampling / `hist_alpha` Transport

**Date**: 2026-05-18  
**Branch to inspect**: `claude/sidecar-adaptive-sampling`  
**Latest relevant commit reviewed**: `6caf9ce` — `fix(sidecar-S2): v3 — explicit hist_alpha transport instead of NN re-eval`  
**Status**: S2 is not ready for N=100 acceptance yet. v3 is directionally correct but needs one conservative `hist_alpha` transfer patch before more expensive runs.

## Big Picture

The sidecar is testing whether changing sampling / mesh density near the crack tip improves PIDL local fatigue fields without changing the Deep Ritz + Carrara loss.

The important separation is:

- C6 / old `adaptive_sampling_dict`: residual-driven **loss reweighting**. Not part of true adaptive sampling.
- S1: static geometric refinement around `(0, 0)`. Mesh fixed after setup.
- S2a: tip-following refinement. Mesh can change as the alpha-based crack tip moves.
- S2b: score-driven refinement. Mesh can change based on detached residual density.

S2 must keep the physical objective unchanged. Any score or tip location may decide mesh density only; it must not enter the loss as a multiplicative weight.

## Evidence So Far

### S2 v2.1 Static-Regime Acceptance Passed

With nearest-element transport + hysteresis + cycle-0 `hist_alpha_init` fix, S2a/S2b matched S1 exactly over cycles 0-4:

| cycle | S1 alpha_bar_max | S2 v2.1 alpha_bar_max |
|---|---:|---:|
| 0 | 0.5092 | 0.5092 |
| 1 | 1.0712 | 1.0712 |
| 2 | 1.6308 | 1.6308 |
| 3 | 2.2080 | 2.2080 |
| 4 | 2.4709 | 2.4709 |

Interpretation: when the tip has not moved and hysteresis skips remeshing, S2 is mathematically equivalent to S1. This is a strong correctness gate.

### S1 N=300 3-Seed Reference

S1 did not significantly change `N_f` versus the seed-1 baseline, but it lifted local accumulated fatigue:

| seed | N_f | alpha_bar_max | x_tip |
|---|---:|---:|---:|
| 1 | 80, confirm 90 | 9.30 | 0.500 |
| 2 | 83, confirm 93 | 11.63 | 0.500 |
| 3 | 82, confirm 92 | 14.04 | 0.500 |
| baseline seed 1 | 84 | 9.21 | 0.500 |

Use same-cycle S1 mean/std as the reference for S2, not only `N_f`.

### S2a v2.1 N=100 Was Negative, But Not Method-Level

S2a v2.1 seed 1 reached fracture earlier (`N_f` around cycle 77, confirmed cycle 87), but `alpha_bar_max` stalled far below S1:

| cycle | S2a alpha_bar_max | S1 mean +/- std | delta |
|---|---:|---:|---:|
| 10 | 3.27 | 3.42 +/- 0.14 | -4% |
| 20 | 4.38 | 5.31 +/- 0.57 | -18% |
| 30 | 4.49 | 6.62 +/- 0.66 | -32% |
| 50 | 5.20 | 9.18 +/- 1.39 | -43% |
| 87 | 6.56 | 11.40 +/- 1.88 | -42% |

Interpretation: this should be treated as **implementation-negative / state-transfer failure**, not a method-level negative, because S2 dynamic remeshing was still mishandling the nodal irreversibility state.

## The Core Logic

There are three state variables that matter when S2 changes mesh:

1. `hist_fat` — element-wise fatigue accumulation.
2. `psi_plus_prev` — element-wise previous-cycle driver.
3. `hist_alpha` — node-wise irreversibility floor for phase-field alpha.

S1 never changes mesh after setup, so all three states live on one fixed discretization and accumulate naturally.

S2 changes mesh. Therefore it must transport all three states whenever it refines around a new tip/score region. If any state is rebuilt from the NN or smoothed through a coarse original mesh, S2 no longer tests adaptive sampling cleanly; it tests a confounded state-reset algorithm.

Known failure modes:

- v1: `hist_fat` / `psi_plus_prev` were aggregated to original mesh and expanded again. This smoothed sub-parent variation and reduced tip localization.
- v2.1: `hist_fat` transport was fixed, but dynamic-refine `hist_alpha` still came from `field_comp.fieldCalculation(new_inp)`. That can weaken the irreversibility floor at new/refined nodes.
- v3 (`6caf9ce`): `hist_alpha` now uses nearest-node transport instead of NN re-eval. Good direction, but current nearest-node midpoint handling is not conservative enough.

## Current v3 Review Finding

Commit `6caf9ce` implements:

```text
old nodal hist_alpha
  -> nearest_node_transport via cKDTree
  -> max(hist_alpha_init(new_inp))
  -> clamp [0, 1]
```

This is Level-1 transport from the earlier design ladder:

- L1: nearest-node transfer
- L2: lineage / edge transfer
- L3: barycentric element transfer

Current v3 = L1 + initial-crack floor. It does **not** include an NN-alpha max floor and does **not** know edge lineage.

Risk: a new midpoint on an old edge with endpoint histories `[0, 1]` can receive `0` depending on KDTree tie behavior. That is not acceptable for an irreversibility floor. Verified toy behavior:

```text
old [0, 1] -> midpoint gets 0
old [1, 0] -> midpoint gets 1
```

This means v3 may still create local weak floors at newly inserted midpoint nodes exactly where damage history should be conservative.

## Recommended Next Patch

Do not launch N=20/N=100 yet. Patch v3 first.

Minimum acceptable patch:

```python
with torch.no_grad():
    _, _, alpha_nn_new = field_comp.fieldCalculation(inp)

ha_nn = alpha_nn_new.detach().cpu().numpy().ravel()
ha_new_np = np.clip(
    np.maximum.reduce([ha_transferred, ha_floor, ha_nn]),
    0.0,
    1.0,
)
```

Important: NN alpha may only **raise** the transported `hist_alpha`; it must never replace it or lower it.

Better patch if time allows:

- Add conservative tie handling to `nearest_node_transport`: for all old nodes at the minimum distance within a tolerance, assign `max(values_old[tied_nodes])`.
- Even better: implement L2 lineage-based edge transfer in `refine_marked_elements`, so new midpoint nodes get `max(hist_alpha_endpoint_a, hist_alpha_endpoint_b)`.

The best longer-term solution is L2. It matches the current 1-to-4 refinement algorithm and avoids KDTree midpoint ambiguity.

## Acceptance Gates After Patch

Run in this order:

1. **N=5 S2a static-regime acceptance**  
   Must still match S1 to 4 decimals at cycles 0-4.

2. **First dynamic REFINE diagnostic**  
   Log line should show `hist_alpha max / p99 / mean` before -> after. Max and p99 should not drop materially. Small mean changes are expected when mesh density changes.

3. **N=20 S2a smoke**  
   Cycle 20 must not repeat the v2.1 `-18%` gap. This is cheaper than N=100 and catches most transport failures.

4. **N=100 S2a seed 1**  
   Use S1 reference. A reasonable gate from prior note: at cycle 50, `alpha_bar_max >= 7.79` (S1 mean 9.18 minus 1 std 1.39). If S2a still stays far below S1 after conservative `hist_alpha` transport, then it becomes a credible method-level negative.

Do not run S2b until S2a passes the dynamic-remesh state-transfer gates. S2b shares the same `hist_alpha` transport risk plus adds score-mask complexity.

## Files To Inspect

- `source/model_train.py`
  - S2 mutex guards near the top of `train()`.
  - S2 state dictionary around the fine-mesh setup.
  - S2 per-cycle REFINE/SKIP block.
  - `hist_alpha` sync after `field_comp.update_hist_alpha(inp)`.
  - S2b score aggregation after fatigue update.

- `source/sidecar_sampling.py`
  - `nearest_element_transport`
  - `nearest_node_transport`
  - `adaptive_refine_for_cycle`
  - `refine_marked_elements`

- `SENS_tensile/run_sidecar_S2_umax.py`
  - `--hysteresis-fraction`
  - `--plot-every`
  - S2 runner disables C6/tip-weight/S1.

- `SENS_tensile/plot_tip_tracking_evidence.py`
  - Diagnostic overlay for alpha candidates, selected tip, and tracking/refinement center.

## Suggested Command Shape

After patching:

```bash
cd "/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile"
python run_sidecar_S2_umax.py 0.12 --n-cycles 5 --seed 1 \
  --mode tip_following --r-tip 0.05 --n-passes 1 --plot-every 1
```

Then N=20:

```bash
python run_sidecar_S2_umax.py 0.12 --n-cycles 20 --seed 1 \
  --mode tip_following --r-tip 0.05 --n-passes 1 --plot-every 5
```

Only then consider N=100.

## Bottom Line

S2 should not be closed yet. The current negative result is not clean because dynamic remeshing still risks weakening the nodal irreversibility floor. The next successor should patch v3 into a conservative `hist_alpha` transfer first, then run N=5 and N=20 gates before spending a full N=100 run.

## 2026-05-19 Update: v3.2 Passes Transport, Failure Was Early Remesh Policy

Successor patch status:

- v3.2 implemented L2 edge-lineage `hist_alpha` transport plus NN-max floor.
- N=5 S2a seed 1 passed the static-regime gate exactly:
  `0.5092, 1.0712, 1.6308, 2.2080, 2.4709`.
- Diagnostic N=20 with the old hysteresis policy (`hysteresis_fraction=0.25`,
  threshold `0.0125`) showed that `hist_alpha` and `hist_fat` were preserved
  through REFINE, but the first dynamic remesh at cycle 8 flattened
  `alpha_bar_max` near `2.6524`.
- Root+tip union refinement was tested and did **not** fix the plateau:
  final c19 stayed near `2.6552`.

Root cause now looks like **over-eager remeshing**, not state loss. At cycle 8
the crack tip had moved only `x_tip≈0.014`, still well inside the original
`r_tip=0.05` refined ball. Rebuilding the mesh that early perturbed the
history/optimizer path and prevented the expected S1-like accumulation.

New successful diagnostic:

```text
S2a N20 seed1, r_tip=0.05, hysteresis_fraction=1.0
c8  alpha_bar_max=2.8793  (matches S1)
c9  alpha_bar_max=3.0978  (matches S1)
c10 alpha_bar_max=3.2782  (matches S1)
c17 alpha_bar_max=4.2465  (matches S1, before first dynamic remesh)
c18 alpha_bar_max=4.2475  (first dynamic remesh at x_tip≈0.0500; S1=4.3820)
c19 alpha_bar_max=4.2489  (S1=4.5003; -5.6%)
```

Implementation decision:

- Change the S2 default to `hysteresis_fraction=1.0`.
- Interpretation: remesh only after the tracked tip has moved about one refine
  radius from the last refinement center. This keeps the mesh stable while the
  active tip is still inside the existing high-density patch.
- Keep `--hysteresis-fraction` as a CLI override for diagnostics.
- Do not use root+tip union as the production fix; it added elements but did
  not restore `alpha_bar_max`.
- Remaining caveat: after the first truly necessary remesh (cycle 18 in the
  N20 diagnostic), a small gap appears. This is much smaller than the old
  `h=0.25` failure but should be monitored in the next clean N100 run.

Current Taobo diagnostic logs:

- Good hysteresis run:
  `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hyst1_S2a_v32_N20_gpu5_20260519.log`
- Negative root+tip run:
  `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/union_S2a_v32_N20_root_tip_gpu4_20260519.log`

## 2026-05-20 Update: N40 Adaptive `lambda_hist` Started

We added a narrow diagnostic intervention based on the Wang 2020 gradient
pathology takeaway: after S2 REFINE, the irreversibility penalty gradient can
dominate the physical gradients even when the raw loss values look comparable.

Observed at fixed-`lambda_hist` S2a N100 cycle 29:

```text
E_el   grad_l2 = 4.566485e+00
E_d    grad_l2 = 8.425419e+00
E_hist grad_l2 = 2.182388e+03
```

Patch summary:

- `source/fit.py`: optional `hist_loss_weight` parameter, default `1.0`.
- `source/model_train.py`: when `fatigue_dict["adaptive_lambda_hist"]["enable"]`
  is true, each S2 REFINE computes
  `lambda_hat = max(||grad E_el||2, ||grad E_d||2) / ||grad E_hist||2`,
  clips it to `[1e-3, 1]`, prints the update, and uses the new weight in
  subsequent fit cycles.
- `SENS_tensile/run_sidecar_S2_umax.py`: new CLI flags
  `--adaptive-lambda-hist`, `--lambda-hist-min`, `--lambda-hist-max`,
  `--lambda-hist-smooth`, `--lambda-hist-initial`.
- Default behavior remains fixed `lambda_hist=1.0`; only the new runner flag
  changes the physics loss.

Current active runs on Taobo:

1. Fixed-`lambda_hist` N100 diagnostic:
   - PID `1470732`, GPU5
   - Log:
     `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/S2a_v32_N100_hyst1_resume_gradnorm_gpu5_20260520.log`
   - It has already printed the cycle-29 gradient diagnostic above and
     continued past cycle 31.

2. Adaptive-`lambda_hist` N40:
   - PID `1515969`, GPU3
   - Log:
     `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/S2a_v32_N40_adapthist_gpu3_20260520_065714.log`
   - Archive:
     `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N40_R0.0_Umax0.12_sidecarS2_tipfol_rt0.05_np1_adapthist/`
   - Warm-started from completed N20 `hyst1_diag`; `checkpoint_step_19.pt`
     was patched with `_S2_state` so S2 resumes on the current refined mesh.
   - Startup confirmed:
     `restored current mesh: 40761 nodes, 81300 elem | swaps=2 skips=17 |
     tip_at_refine=(0.05004344880580902, 0.0)`, then
     `continue step 20/39`.

Next check:

- Tail the adaptive log until the next REFINE, expected around cycle 29.
- Look for `[AdaptiveLambdaHist cycle 29]`. With the fixed-run gradient
  numbers, the first unclipped value would be about `3.86e-3`.
- Then compare cycle 29-39 `alpha_bar_max`, `x_tip`, and `Kt` against the
  fixed-`lambda_hist` N100 diagnostic over the same cycle range.
