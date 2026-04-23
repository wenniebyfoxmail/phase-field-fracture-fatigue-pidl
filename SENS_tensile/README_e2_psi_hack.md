# E2 — ψ⁺ hard-code sanity test (Apr 23 2026)

**Goal**: verify whether PIDL's ᾱ_max ceiling (~10) is caused by insufficient
ψ⁺_raw concentration at the crack tip (versus FEM's ~10⁴ concentration).

**Mechanism**: Force-multiply ψ⁺ in a Gaussian neighborhood of the crack tip
by a large factor (default 1000×), simulating FEM-like stress concentration.
This only affects the fatigue accumulator (not the Deep Ritz training loss
directly). If ᾱ_max breaks 10 → mechanism confirmed. If still capped → deeper
issue.

## Code hooks (committed)

- `source/compute_energy.py::get_psi_plus_per_elem` — new optional
  `psi_hack_dict` parameter; applies Gaussian scale multiplier when enabled
- `source/model_train.py` — reads `fatigue_dict['psi_hack']` and forwards
- `SENS_tensile/config.py::fatigue_dict['psi_hack']` — config entry,
  default `enable: False`

Archive directory auto-tagged with `_psiHack_m{mult}_r{r_hack}`.

## How to run (warm-start from baseline cycle 50)

### Step 1 — Edit `config.py`: switch to baseline + enable psi_hack

In `SENS_tensile/config.py` `fatigue_dict`, set:

```python
"accum_type": "carrara",            # was "golahmar" (Dir 6.2)
"spatial_alpha_T": {"enable": False, ...},  # was enable=True (Dir 6.1)
"psi_hack": {
    "enable": True,                  # ★ activate E2
    "x_tip": 0.0, "y_tip": 0.0,
    "r_hack": 0.02,
    "multiplier": 1000.0,
},
```

All other settings stay at 8×400 / seed=1 / Umax=0.12 / carrara_asy / aT0.5.

### Step 2 — Warm-start from baseline cycle 50

Baseline archive:
```
hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N700_R0.0_Umax0.12
```

With the config changes above, auto-built archive path for E2 will be:
```
hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_psiHack_m1000_r0.02
```
(note: `N300` from current `n_cycles`, not `N700`. If you want N700 to match,
set `n_cycles: 700` in config.)

To resume from baseline cycle 50:

```bash
cd "upload code/SENS_tensile"

# 1) Make target dir (config will create it; but do it explicitly to warm-start)
BASE="hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N700_R0.0_Umax0.12"
E2="hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_psiHack_m1000_r0.02"
mkdir -p "$E2/best_models" "$E2/intermediate_models"

# 2) Copy baseline cycle 0..50 checkpoints (resume will auto-pick the highest)
cp "$BASE/best_models/checkpoint_step_"{0..50}.pt  "$E2/best_models/" 2>/dev/null
cp "$BASE/best_models/trained_1NN_"{0..50}.pt      "$E2/best_models/" 2>/dev/null
# history .npy so restore has something to hydrate from
cp "$BASE/best_models/"*.npy                        "$E2/best_models/" 2>/dev/null
cp "$BASE/alpha_snapshots/"*.npy                    "$E2/alpha_snapshots/" 2>/dev/null

# 3) Launch (will auto-resume from cycle 50, apply psi_hack starting cycle 51)
python main.py 8 400 1 TrainableReLU 1.0  2>&1 | tee "runs_e2_psi_hack_m1000_r0.02.log"
```

### Step 3 — Monitor (~20 cycles = ~1-2 hours on Mac CPU)

Watch `alpha_bar_vs_cycle.npy` in the E2 dir. Key signal:

| cycle | ᾱ_max (baseline, no hack) | ᾱ_max (E2, with hack) — expected |
|---|---|---|
| 50 | ~5.5 | 5.5 (same checkpoint) |
| 55 | ~6.5 | **>30** if mechanism confirmed |
| 60 | ~7.5 | **>80** if still growing |
| 65 | ~8.0 | **>150** if no ceiling |
| 70 | ~8.5 | **>300** if linear in cycles |

### Decision tree

- **ᾱ_max > 30 at cycle 55**: ψ⁺ concentration IS the bottleneck. Mechanism
  confirmed. Ch2 narrative anchored. Plan E1 Enriched S-N sweep as the
  architectural fix.
- **ᾱ_max still ≤ 10 at cycle 60**: ψ⁺ is NOT the sole bottleneck. Deeper
  architectural issue (NN training dynamics, degradation coupling, etc.).
  Memo + escalate.
- **ᾱ_max grows but hits a new plateau ~100**: ψ⁺ is PART of the bottleneck,
  but secondary cap exists. Document + continue E1.

### After finishing

Run `extract_f_mean.py` + `recompute_psi_peak.py` on the E2 archive to match
baseline post-processing format.

Update memory:
- `direction_6_2_golahmar_apr22.md` Apr 23 update section → add E2 results
- `finding_e2_psi_hack_{date}.md` → new memory file documenting the experiment

### To revert

1. `fatigue_dict['psi_hack']['enable'] = False` in config.py
2. Restore `accum_type: "golahmar"` + `spatial_alpha_T.enable: True` if you
   want to continue Dir 6.2/6.3 work afterwards
3. E2 archive dir can be deleted if not needed (large disk footprint)
