# Freeze-Then-Select FEM producer request

Date: 2026-08-04

## Current status: HOLD

This is a provisional `3 x 2 x 2` synthetic factorial specification, not a
request to run immediately and not a claim that twelve trajectories are
universally sufficient. The current locked GRIPHFiTH staggered solver failed its
strict fixed-point qualification and is not an approved teacher. Do not run this
corpus on Windows, Taobo, or CSD3 until producer qualification and independent
experimental-design review are complete.

## Provisional production design after qualification

Generate one frozen factorial package with 12 compatible trajectories:

- three genuinely different physical load spectra;
- two temperature-material parameter levels;
- two moisture-material parameter levels;
- one fixed geometry and precrack;
- at least one declared right-censored trajectory.

The 12 trajectories must cover every `3 x 2 x 2` combination. Temperature and
moisture must alter documented material/fatigue parameters, not only metadata.

## Required files

- `freeze_select_fem_factorial.csv` or `.parquet`;
- `FROZEN_EXPORT_MANIFEST.json` based on the adjacent template;
- producer log containing command, runtime, commit, dirty status, and machine;
- source hashes for solver, configuration, and export code.

Every element/time row must satisfy the base frozen schema and add:

- `actual_fatigue_increment`;
- `nominal_fixed_physics_increment`;
- `load_spectrum_id`;
- `temperature_level`;
- `moisture_level`;
- `geometry_id`;
- `precrack_id`;
- `increment_state_timing`.

Use the transient increment at the declared update timing. Do not reconstruct it
from post-refresh `psi_plus_prev_elem`, and do not map `alpha_bar` to damage `d`.

## Producer-side gate

Run from the shared repository root:

```bash
python SENS_tensile/run_freeze_select_producer_gate.py \
  --snapshot /path/to/freeze_select_fem_factorial.parquet \
  --manifest /path/to/FROZEN_EXPORT_MANIFEST.json \
  --output-dir /path/to/freeze_select_producer_gate
```

Exit code `0` and `producer_gate_report.json` with `passed: true` are required.
Do not launch PIDL or joint-selection comparison when the producer gate fails.

## Handoff evidence

Return the snapshot, manifest, gate report, decision file, producer log, and
SHA-256 values. A local file path or OneDrive presence is not proof of cross-
machine availability; the shared repository path/ref or immutable transfer hash
must be stated explicitly.

After the producer gate passes, build the three method packages exactly as
specified in `docs/freeze_then_select/fair_comparison_package_contract_2026-08-04.md`.
The joint package is not accepted without a real checkpoint hash and
`FIELD_MODEL_PROVENANCE.json`.

## Claim boundary

This factorial package remains a synthetic environmental proxy. It must not be
called real-road data. Passing the gate qualifies inputs only; it does not prove
support recovery, causal mechanisms, or improved crack prediction.
