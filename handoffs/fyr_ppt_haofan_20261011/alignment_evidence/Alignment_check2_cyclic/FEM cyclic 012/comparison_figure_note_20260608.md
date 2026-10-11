# FEM cyclic 012 comparison figure note - 2026-06-08

## Scope

This folder now contains two FEM comparison layers:

1. Separate phase-field timeline figures for each FEM case.
2. Loading-step comparison figures tracking the protocol mechanism metrics.

The current FEM cases included in the loading-step comparison are:

- `standard`
- `n_step_2`
- `n_step_3`
- `n_step_10`
- `peak_only`

## Per-case phase-field figures

Each case has its own figure under:

```text
cases/<case>/figures/phase_field_motion/
```

The figure is not a combined cross-case plot. It shows the initial state and the key snapshots after the crack front starts moving for that case.

The plotted cycles are recorded in:

```text
cases/<case>/figures/phase_field_motion/<case>_phase_field_motion_plotted_cycles_20260608.csv
```

Crack motion was detected from the full FEM field as the first stored cycle where the rightmost `d >= 0.95` front advanced by more than 0.02 from the initial front. With that rule:

- `standard`: first motion c9; final plotted event c69.
- `n_step_2`: first motion c9; final plotted event c70.
- `n_step_3`: first motion c9; final plotted event c70.
- `n_step_10`: first motion c9; final plotted event c69.
- `peak_only`: no propagation detected; plotted c1, c61, c120 as the no-propagation control.

## FEM loading-step comparison

The main protocol comparison figure is:

```text
figures/protocol_comparison/fem_loading_step_protocol_metrics_20260608.png
figures/protocol_comparison/fem_loading_step_protocol_metrics_20260608.pdf
```

Supporting comparison outputs are:

```text
figures/protocol_comparison/fem_loading_step_event_ratios_20260608.png
figures/protocol_comparison/fem_loading_step_event_ratios_20260608.pdf
figures/protocol_comparison/fem_nstep10_vs_standard_protocol_metrics_20260608.png
figures/protocol_comparison/fem_nstep10_vs_standard_protocol_metrics_20260608.pdf
figures/protocol_comparison/fem_loading_step_protocol_metrics_long_20260608.csv
figures/protocol_comparison/fem_loading_step_event_ratios_20260608.csv
figures/protocol_comparison/fem_loading_step_c69_ratios_20260608.csv
figures/protocol_comparison/fem_loading_step_phase_front_metrics_20260608.csv
```

Metrics tracked from the protocol, using the available FEM handoff fields, are:

- damage energy `E_d` and incremental `Delta E_d` from c1
- crack-front x position at `d >= 0.95`
- right-boundary `d >= 0.95` count
- fatigue history `alpha_bar_elem` max and p99
- fatigue degradation `f_fatigue` minimum
- active tensile driver proxy `psi_plus_elem` p99
- near-tip y-width at `d >= 0.5`

The FEM handoff does not contain all PIDL protocol variables directly. In particular, `psi_raw`, `g_alpha`, and `psi_active = g(alpha) * psi_raw` are not available as separate FEM fields here, so the FEM plots use the exported FEM equivalent/proxy `psi_plus_elem`.

## Current interpretation

The standard, n-step 2, n-step 3, and n-step 10 FEM cases are very close in damage energy, crack-front progression, and final event metrics. Peak-only is a clear no-propagation control.

For "most aligned FEM vs standard FEM", the current best FEM-side comparison is:

```text
figures/protocol_comparison/fem_nstep10_vs_standard_protocol_metrics_20260608.png
```

At the final event, n-step 10 is essentially aligned with standard for the main quantities: `E_d` ratio is about 1.0008, `psi_plus_elem_p99` ratio is about 1.0085, and the `d >= 0.95` front reaches the same right-boundary event state.

