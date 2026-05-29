# FEM Request 21 Cadence Interpretation

Date: 2026-05-30

## Question

Does the remaining soft-hist0 FEM/PIDL gap mainly come from FEM using a
different within-cycle load/history-refresh cadence?

## Source

Windows-FEM completed Request 21 and pushed the summary in
`docs/handovers/windows_fem_outbox.md`.

Verified run-level results:

| FEM variant | Retained load factors | Penetration cycle |
|---|---|---:|
| Request 19 peak-only | `[1]` | no penetration by c120 |
| Request 21 n_step=2 | `[1, 0]` | 70 |
| Request 21 n_step=3 | `[0.5, 1, 0]` | 70 |
| Soft-hist0 standard | `[0.25, 0.5, 0.75, 1, 0]` | 69 |
| Request 21 n_step=10 | `[0.2, 0.4, 0.6, 0.8, 1, 0]` | 69 |

Generated figure:

```text
_analysis_fem_mechanism_20260528/figures/fem_request21_cadence_summary_20260530.png
```

After retrying OneDrive hydration, the field CSV/MAT payloads were readable on
Mac and the field reductions were regenerated from the exported element fields:

```text
_analysis_fem_mechanism_20260528/request21_fem_nstep/fem_request21_field_reductions_long.csv
_analysis_fem_mechanism_20260528/request21_fem_nstep/fem_request21_selected_cycle_ratios.csv
_analysis_fem_mechanism_20260528/request21_fem_nstep/fem_request21_c69_summary.csv
_analysis_fem_mechanism_20260528/request21_fem_nstep/fem_request21_event_summary.csv
_analysis_fem_mechanism_20260528/figures/fem_request21_field_reductions_20260530.png
_analysis_fem_mechanism_20260528/figures/fem_request21_c69_ratio_heatmap_20260530.png
_analysis_fem_mechanism_20260528/figures/fem_request21_event_ratio_heatmap_20260530.png
```

## Reading

The large effect is not the number of positive substeps.  The large effect is
whether the cyclic solve retains the unload/end-of-cycle state.  Peak-only
does not penetrate by c120, but all variants with unload retained fracture at
c69-c70.

Therefore, after the Request 20 state-timing correction, the remaining
FEM/PIDL late-cycle field gap is unlikely to be explained mainly by FEM using
more positive substeps than PIDL.  A matched PIDL substep diagnostic may still
be useful, but it is no longer the highest-probability explanation for the
order-of-magnitude active-driver gap.

The hydrated field reductions support this reading.  Up to c40, n_step=2/3/10
track the standard soft-hist0 FEM closely in `alpha_bar`, active `psi_plus`,
tip position, and common near-tip integrals.  By c69, n_step=10 is almost
identical to the standard run (`E_d` ratio 1.001, `psi_plus` max ratio 1.000,
common `2ell` near-tip `psi_plus` integral ratio 1.022, and the same
`x_tip_d095=0.999`).  n_step=2/3 are at c69 one cycle before their penetration
event, so their `x_tip_d095` is still 0.953; the late near-tip integral ratios
then compare different local windows and should not be overread as a pure
physics difference.

The matched-event comparison removes that timing trap.  Comparing each variant
at its own final/event cycle to standard c69 gives near identity in the active
driver and tip position:

| Variant | Event cycle | `E_d` ratio | `max(psi+)` ratio | `2ell psi+` ratio | `x_tip_d095` ratio |
|---|---:|---:|---:|---:|---:|
| n_step=2 | 70 | 0.996 | 1.002 | 1.023 | 1.000 |
| n_step=3 | 70 | 0.998 | 1.002 | 1.022 | 1.000 |
| n_step=10 | 69 | 1.001 | 1.000 | 1.022 | 1.000 |

The main remaining small differences are in `alpha_bar` percentiles, not in
whether the active driver or crack-tip event exists.

## Implication For PIDL

The current stronger hypothesis remains:

```text
PIDL alpha/damage evolves into a field that relaxes active psi_plus too much.
Then alpha_bar accumulation falls behind FEM, and the gap grows by feedback.
```

That is a representation/localization/optimization-path issue, not just a
cycle-indexing or substep-count issue.

## Caveat

The c69 ratio heatmap compares all variants at the same cycle, not at matched
event phase.  This is useful for a fixed-cycle audit, but n_step=2/3 fracture at
c70 whereas standard/n_step=10 fracture at c69.  For late near-tip integrals,
use both views:

```text
fixed cycle c69: shows where the one-cycle lag appears
matched event cycle: needed before claiming a true local-integral difference
```

## Next Step

1. Use n_step=10 as the closest cadence control for strict FEM/PIDL comparison:
   it matches standard FEM almost exactly while also using a denser retained
   load cadence.
2. Deprioritize PIDL substep emulation as the main explanation, and focus on
   branch-restart/staged-alpha/local-first representation diagnostics.
3. Keep both fixed-cycle and matched-event tables in future comparisons so
   cycle timing does not masquerade as a field-shape difference.
