# Alignment check 2

This folder collects the Umax=0.12 cyclic FEM/PIDL alignment evidence.
It is organized as a research archive: case-local raw evidence remains inside
the FEM and PIDL case folders, while the manifest files below define which
outputs should be treated as canonical.

## Start here

- `manifest/cases.csv`: case inventory and interpretation status.
- `manifest/canonical_outputs.md`: canonical figures, tables, and notes to use
  when writing or presenting this alignment check.
- `comparisons/`: focused cross-solver deep-dive outputs that are not raw
  case archives.
- `FEM cyclic 012/README.md`: FEM loading-step case summary.
- `PIDL cyclic 012/README.md`: PIDL loading-step and state-timing case summary.

## Current reading

- FEM loading-step cases that retain an unload/end-of-cycle state
  (`standard`, `n_step_2`, `n_step_3`, `n_step_10`) are closely aligned with
  each other and fracture around c69-c70.
- FEM `peak_only` is a no-propagation control by c120.
- PIDL one-peak and FEM-like substep until-fracture runs fracture in the same
  physical-cycle window, around c82.
- The FEM/PIDL field and energy paths are still not solver-equivalent. The
  aligned PIDL baseline has lower accumulated damage-energy growth than FEM.

## Archive policy

- Keep case-local `raw_data/`, `logs/`, and `docs/` as provenance.
- Treat root-level `figures/` and `analysis/` as generated summaries unless
  they are listed in `manifest/canonical_outputs.md`.
- Large PIDL training/model artefacts are intentionally left in place for now.
- Verified duplicate FEM handoff copies under
  `FEM cyclic 012/analysis/request21_fem_nstep/source_handoff/` were removed on
  2026-06-08 because identical copies remain in `FEM cyclic 012/cases/*/raw_data/`.
