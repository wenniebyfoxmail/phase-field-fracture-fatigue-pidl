# PIDL State-Timing Diagnostic

Date: 2026-05-31

## Purpose

This diagnostic tests whether the early FEM/PIDL gap enters through:

1. the fitted NN field before history refresh,
2. the fatigue/history refresh itself,
3. the one-peak-per-cycle PIDL timing abstraction.

It is deliberately stricter than another architecture experiment: same strict
FEM-mesh soft-hist0 setup, with extra state exports around c0/c1/c2/c3.

## New Export

`source/model_train.py` now supports:

```python
fatigue_dict["state_timing_export"] = {
    "enable": True,
    "cycles": "0,1,2,3",
    "write_fields": True,
    "dir": "pidl_state_timing",
}
```

For each selected step/cycle it writes:

- `pre_fit`
- `post_fit_pre_history_refresh`
- `post_history_refresh_pre_prev_reset`

The summary CSV is:

```text
pidl_state_timing/pidl_state_timing_summary.csv
```

The optional field files are:

```text
pidl_state_timing/pidl_state_cycle_XXXX_<stage>.npz
```

Each row/file includes element-level alpha, hist_alpha, alpha_bar/hist_fat,
f_fatigue, psi_active, psi_raw, history_driver, psi_prev, and E_el/E_d/E_hist
plus max/p99/p999/integral/location reductions.

## Gradient-Balance Probe

The same runner can print/export gradient norms for:

```text
log(E_el), log(E_d), log(E_hist), log(E_el + E_d + E_hist)
```

This is diagnostic only. It uses `torch.autograd.grad`, so it does not alter the
optimizer gradients, loss weights, or physics objective.

Enable it with:

```bash
--gradient-balance --gradient-cycles auto
```

The CSV is:

```text
gradient_balance/energy_gradient_balance.csv
```

The key columns are `logE_el_gmax`, `logE_d_gmax`, `logE_hist_gmax` and their
`gmean`, `grms`, and `gnorm` counterparts. Very different magnitudes mean the
optimizer is not feeling the three energy terms equally, even when the scalar
energies look similar.

## Runner

Strict one-peak-per-cycle diagnostic:

```bash
python SENS_tensile/run_fem_mesh_state_timing_umax.py 0.12 \
  --n-cycles 4 \
  --mesh-file meshed_geom_fem_soft_hist0.msh \
  --tag softHist0_stateTiming \
  --gradient-balance \
  --compile
```

FEM-like substep/history update variant:

```bash
python SENS_tensile/run_fem_mesh_state_timing_umax.py 0.12 \
  --n-cycles 4 \
  --mesh-file meshed_geom_fem_soft_hist0.msh \
  --tag softHist0_stateTiming_substeps \
  --substeps 0.25,0.5,0.75,1,0 \
  --gradient-balance \
  --compile
```

For substeps, `--state-cycles auto` exports the first four physical cycles worth
of training steps. The CSV contains both `training_step` and `physical_cycle`.

## Pretrain Controls

The default remains unchanged. Diagnostic runners can now use:

```bash
--pretrain-mode default
--pretrain-mode short --pretrain-rprop-epochs 1000
--pretrain-mode off
```

Pretraining is not part of the fatigue law. It initializes the NN near the
analytic precrack field so the first cyclic solve does not start from a random
alpha/u/v field. It can, however, bias c0/c1 if the trained initial alpha is
hotter than the analytic/FEM initial state, so short/off are diagnostic levers.
