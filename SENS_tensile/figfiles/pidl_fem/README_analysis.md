# Legacy PIDL/FEM S-N comparison — Figure A3

## Question and evidence

`fig_A3_SN_comparison.png` compares the archived five-point PIDL 8x400
seed-1 series with the archived GRIPHFiTH FEM series over
`U_max = 0.08`--`0.12`.  It is rendered by
`SENS_tensile/generate_figs_pidl_fem.py`; the interpretation and state-label
limits are recorded in
`docs/pidl_fem_clear_comparison_board_2026-07-07.md`.

The image was visually inspected on 2026-10-18: the axes, five paired markers,
seed-range error bar, fitted curves, and embedded value table are readable.
It uses linear `U_max` and log-scale `N_f`; it is not a field comparison.

## Allowed reading

For these archived packages, PIDL has a lower plotted `N_f` at every shown
load amplitude and a similar fitted S-N exponent.  This supports only the
historical scalar/event-scale comparison.  It does not establish matched
damage, history, active-driver, process-zone, or physical behaviour.

## Reproducibility boundary

The five PIDL arrays remain locally available, but the FEM CSV inputs formerly
expected at `~/Downloads/post_process/` were absent during this recovery.
Therefore the script passed syntax validation but Figure A3 was not rerun, and
no new PDF was produced.  This PNG is retained as a historical supporting
visual; a future claim-bearing reuse requires recovering the exact FEM CSVs,
rerendering, and rechecking the accompanying comparison contract.
