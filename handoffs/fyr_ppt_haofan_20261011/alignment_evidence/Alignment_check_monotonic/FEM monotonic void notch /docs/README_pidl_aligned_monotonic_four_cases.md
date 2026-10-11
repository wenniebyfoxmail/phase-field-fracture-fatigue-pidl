# PIDL-Aligned Monotonic Four-Case FEM Handoff

Generated on Windows-FEM, 2026-06-03.

Purpose: provide the four PIDL-aligned monotonic FEM outputs for Mac-side comparison:

- `umax012_fatigue_on`: u_max=0.12, fatigue on, old 8 linear steps ending at 0.12.
- `umax012_fatigue_off`: u_max=0.12, fatigue off (`alpha_T=1e10`), old 8 linear steps ending at 0.12.
- `umax020_fatigue_off`: u_max=0.20, fatigue off (`alpha_T=1e10`), explicit Manvas/Mac steps.
- `umax020_fatigue_on`: u_max=0.20, fatigue on, explicit Manvas/Mac steps.

The explicit Manvas/Mac displacement sequence is:
`0.025, 0.050, 0.075, 0.100, 0.105, 0.110, 0.115, 0.120, 0.125, 0.130, 0.135, 0.140, 0.145, 0.150, 0.155, 0.160, 0.165, 0.170, 0.175, 0.180, 0.185, 0.190, 0.195, 0.200`.

Common setting: `SENT_pidl_fine_lh5.inp`, reverseBC, `AT1 + AMOR + PENALTY`, `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`, `res_stiff=1e-6`, plane strain, `fix_X` top+bottom, `fix_Y` bottom, `disp_Y` top.

Each case folder contains the scalar histories, crack summary, convergence logs, checkpoint, `peak_load_c1.vtk`, final `fields_*.vtk`, and `psi_fields/cycle_0001.mat` when present.

Use `monotonic_four_case_summary.csv` as the quick index.
