# PIDL stateTiming one-peak until-fracture case

## Purpose

This case reruns the aligned PIDL cyclic 0.12 setup on Taobo with state-timing snapshots enabled, stopping only after fracture is detected and confirmed.

## Solver and alignment

- Solver family: PIDL / Deep Ritz neural phase-field fatigue.
- Alignment target: latest FEM-aligned PIDL setting for cyclic 0.12.
- Geometry and mesh: FEM-derived soft-history-0 mesh.
- Phase-field model: AT1.
- Fatigue/history mode: fatigue on, Carrara asymmetric, `aT=0.5`.
- History update: active degraded history, post-fit update.
- Pretrain: off.
- Seed: 1.

## Loading

- Boundary condition: reverseBC displacement loading.
- Maximum displacement: `Umax=0.12`.
- Load ratio: `R=0.0`.
- Loading schedule: one peak per physical cycle.
- Physical cycles requested: `Nphys=100`.
- Training/loading steps requested: `Nstep=100`.
- Early-stop rule: fracture must persist for 3 confirmation cycles.

## Fracture result

- First fracture detection: cycle 82.
- Confirmed stop: cycle 85.
- Detection metric at onset: `alpha_bdy=1.0000`, `N_bdy>0.95=20`.
- Interpretation: fracture onset is retained in the raw outputs and the run stopped after confirmation.

## Local data map

- Raw Taobo archive: `./raw_data/taobo_archive/`
- State-timing snapshots: `./raw_data/taobo_archive/pidl_state_timing/`
- State-timing summary: `./raw_data/taobo_archive/pidl_state_timing/pidl_state_timing_summary.csv`
- Gradient-balance scratch: `./raw_data/taobo_archive/gradient_balance/energy_gradient_balance.csv`
- Best per-cycle models: `./raw_data/taobo_archive/best_models/`
- Intermediate optimization checkpoints: `./raw_data/taobo_archive/intermediate_models/`

## State snapshots retained

The local archive contains `pre_fit`, `post_fit_pre_history_refresh`, and `post_history_refresh_pre_prev_reset` snapshots for cycles:

`0, 1, 2, 3, 20, 40, 60, 69, 78, 79, 80, 81, 82, 83, 84, 85`

This gives baseline, pre-onset, first-fracture, and confirmed-fracture states for plotting and training-optimization checks.

The retained state-timing payload is 48 `.npz` snapshots plus `pidl_state_timing_summary.csv`.

## Remote provenance

- Taobo launch root: `/mnt/data2/drtao/wennie/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640`
- Taobo archive root: `/mnt/data2/drtao/pidl_archives/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/one_peak`
- Original PID: `3457226`
