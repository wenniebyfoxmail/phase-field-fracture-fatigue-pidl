# PIDL stateTiming substeps-0.25 until-fracture case

## Purpose

This case reruns the aligned PIDL cyclic 0.12 setup on Taobo with the same state-timing instrumentation as the one-peak case, but with several loading substeps per physical cycle.

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
- Loading schedule per physical cycle: `[0.25, 0.5, 0.75, 1.0, 0.0]`.
- Physical cycles requested: `Nphys=120`.
- Training/loading steps requested: `Nstep=600`.
- Early-stop rule: fracture must persist for 3 confirmation steps.

## Fracture result

- First fracture detection: loading index 408, about physical cycle 81.6.
- Confirmed stop: loading index 411, about physical cycle 82.2.
- Detection metric at onset: `alpha_bdy=0.9992`, `N_bdy>0.95=20`.
- Interpretation: fracture onset appears at nearly the same physical-cycle window as the one-peak run, but with additional substep timing information before onset.

## Local data map

- Raw Taobo archive: `./raw_data/taobo_archive/`
- State-timing snapshots: `./raw_data/taobo_archive/pidl_state_timing/`
- State-timing summary: `./raw_data/taobo_archive/pidl_state_timing/pidl_state_timing_summary.csv`
- Gradient-balance scratch: `./raw_data/taobo_archive/gradient_balance/energy_gradient_balance.csv`
- Best per-index models: `./raw_data/taobo_archive/best_models/`
- Intermediate optimization checkpoints: `./raw_data/taobo_archive/intermediate_models/`

## State snapshots retained

The archive contains baseline and scheduled state-timing exports up to the stopped run. The exact fracture-confirmation indices 408-411 were detected and logged; the nearest scheduled state-timing exports around the event are before the event window because the next scheduled export was not reached before early stop.

Use the run log and best-model outputs for exact event-index confirmation, and use `pidl_state_timing/` for the retained optimization/state snapshots.

The retained state-timing payload is 102 `.npz` snapshots plus `pidl_state_timing_summary.csv`.

## Remote provenance

- Taobo launch root: `/mnt/data2/drtao/wennie/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640`
- Taobo archive root: `/mnt/data2/drtao/pidl_archives/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/substeps025`
- Original PID: `3457227`
