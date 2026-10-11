# FEM void-notch reverseBC case

This folder mirrors the OneDrive handoff:

`/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_cyclewise_mechanism_2026-05-28`

## Role

Use this as the closest available FEM **void-notch** reference under reverseBC
Umax=0.12. It is useful for checking how much the original void/slit notch
changes the fatigue-history and damage mechanism.

Do not treat it as the strict current standard reference. The current standard
reference is the soft-hist0 retained-material diffuse precrack case:

`Alignment check 2/FEM cyclic 012/cases/standard`

## Setting

- Run: `SENT_PIDL_12_reverseBC`.
- Material/fatigue: AT1 + AMOR + PENALTY, E=1, nu=0.3, Gc=0.01, ell=0.01,
  alpha_T=0.5, p=2.
- Loading/BC: reverseBC Umax=0.12, R=0, fix_X top+bottom, fix_Y bottom,
  disp_Y top.
- Mesh: `SENT_mesh.inp`, 77,730 Q4 elements, 77,900 nodes.
- Notch convention: original FEM void/slit notch convention, not the retained
  soft diffuse precrack.
- Available cycles: c1-c74.
- Event: N_f = 74 by the exported handoff.

## Alignment Caveat

This case is aligned with the current benchmark on material, Umax, and reverseBC
family, but not on the two settings that later proved important:

- initial crack convention: void/slit notch vs retained soft diffuse precrack;
- loading cadence/state export: this older handoff comes from the original
  `SENT_PIDL_12_reverseBC` run, documented as n_step=8 in the 2026-05-22
  handoff, while the current standard retained-state reference uses the
  soft-hist0 n_step/state-timing protocol.

Therefore compare it as a **notch-convention diagnostic**, not as the final
strict FEM/PIDL alignment target.

## Raw Data

- `raw_data/reverseBC_u12_cyclewise_mechanism_metrics.csv`
- `raw_data/reverseBC_u12_cyclewise_element_fields_c1_c74.mat`
- `raw_data/mesh_geometry.mat`
- `raw_data/README_reverseBC_u12_cyclewise_mechanism.md`
- `raw_data/export_reverseBC_cyclewise_mechanism.m`
