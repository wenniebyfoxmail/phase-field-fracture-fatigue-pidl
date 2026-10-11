# PIDL cyclic 012 comparison figure note - 2026-06-08

## Scope

This folder now contains:

1. Separate PIDL phase-field timeline figures for each case with available alpha snapshots.
2. A standard FEM vs aligned PIDL baseline/control comparison figure.

The PIDL cases with per-case phase-field timelines are:

- `one_peak_femmesh_softHist0_N100`
- `explicit_cycle_0_0p5_1_0p5_0_Nphys40_Nstep200`
- `stateTiming_substeps025_untilFrac_Nphys120_Nstep600`

The latest until-fracture state-timing cases include training/state artefacts.
The one-peak until-fracture case is documented as an instrumented baseline;
the FEM-like substep until-fracture case is the current loading-step/timing
control used for the propagated phase-field timeline set where available.

## Per-case phase-field figures

Each case has its own figure under:

```text
cases/<case>/figures/phase_field_motion/
```

The figure is not a combined cross-case plot. It shows the initial alpha field and the available snapshots after the crack front starts moving.

The plotted snapshots are recorded in:

```text
cases/<case>/figures/phase_field_motion/<case>_phase_field_motion_plotted_snapshots_20260608.csv
```

Crack motion was detected from the alpha snapshots as the first stored snapshot where the rightmost `alpha >= 0.95` front advanced by more than 0.02 from the initial front. Because PIDL snapshots are sparse, this is the first available stored motion snapshot, not necessarily the exact training step where motion begins.

With that rule:

- `one_peak_femmesh_softHist0_N100`: first available motion snapshot 20; final plotted snapshot 85.
- `explicit_cycle_0_0p5_1_0p5_0_Nphys40_Nstep200`: first available motion snapshot 60; final plotted snapshot 180.
- `stateTiming_substeps025_untilFrac_Nphys120_Nstep600`: first available
  stored motion is around idx 408 (about physical cycle 81.6), with confirmed
  boundary event around idx 411 (about physical cycle 82.2).

## Standard FEM vs aligned PIDL comparison

The main comparison figure is:

```text
figures/protocol_comparison/standard_fem_vs_aligned_pidl_protocol_metrics_20260608.png
figures/protocol_comparison/standard_fem_vs_aligned_pidl_protocol_metrics_20260608.pdf
```

Supporting CSV outputs are:

```text
figures/protocol_comparison/standard_fem_vs_pidl_energy_metrics_20260608.csv
figures/protocol_comparison/standard_fem_phase_front_metrics_20260608.csv
figures/protocol_comparison/pidl_one_peak_phase_front_metrics_20260608.csv
figures/protocol_comparison/pidl_femlike_substep_phase_front_metrics_20260608.csv
```

This comparison uses:

- FEM standard damage energy and front trajectory from the organized FEM case.
- PIDL one-peak FEM-mesh baseline energy from `femmesh_pidl_vs_soft_hist0_incremental_energy_c1_ref.csv`.
- PIDL one-peak alpha snapshots for front motion.
- PIDL FEM-like substep snapshots from
  `stateTiming_substeps025_untilFrac_Nphys120_Nstep600` as the current
  substep/control trajectory.

## Current interpretation

The aligned PIDL one-peak baseline has a similar qualitative front-advance trend but lower accumulated damage-energy growth than FEM. In the stable post-c10 energy window, the PIDL/FEM incremental `Delta E_d` ratio rises toward roughly 0.25 near the final standard FEM event.

For "most aligned PIDL baseline/control vs standard FEM", use:

```text
figures/protocol_comparison/standard_fem_vs_aligned_pidl_protocol_metrics_20260608.png
```

For "most aligned FEM loading-step control vs standard FEM", use the FEM-side note and figure:

```text
../FEM cyclic 012/figures/protocol_comparison/fem_nstep10_vs_standard_protocol_metrics_20260608.png
```

## Caveat

PIDL and FEM do not expose identical raw variables in the organized handoff folders. This note and the comparison figures therefore separate what is directly available:

- FEM-side mechanism proxies use `d`, `alpha_bar_elem`, `f_fatigue_elem`, `psi_plus_elem`, and FEM energies.
- PIDL-side front motion uses alpha snapshots.
- PIDL-side energy comparison uses the existing FEM-mesh energy comparison CSV for the one-peak baseline.
