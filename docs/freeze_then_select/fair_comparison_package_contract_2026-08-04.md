# Freeze-Then-Select fair comparison package contract

Date: 2026-08-04

## Methods

Exactly three independently produced method directories are required:

- `freeze_then_select`;
- `single_shot`;
- `joint_training`.

Each directory must contain:

- `RUN_PROVENANCE.json`;
- `selection_result.json`;
- `support_trials.csv`;
- `section_metrics.csv`.

The joint directory must additionally contain `FIELD_MODEL_PROVENANCE.json` and
declare a checkpoint SHA-256. The Freeze-Then-Select package must declare that
the field was frozen before selection and include its frozen-field SHA-256.

## Immutable comparison identity

All three provenance files must exactly match on:

- dataset snapshot SHA-256;
- observation-ID SHA-256;
- split-manifest SHA-256;
- candidate-library SHA-256;
- weak-window SHA-256;
- forecast cutoff index;
- holdout trajectory IDs.

A mismatch invalidates the comparison rather than becoming a caveat.

## Trial evidence

`support_trials.csv` must provide one row per trial and candidate with:

```text
trial_id, term, selected, coefficient, seed,
time_window_id, spatial_section_id, test_function_id
```

This supports stability checks across random seeds, temporal windows, spatial
sections, and weak test functions.

## Section evidence

`section_metrics.csv` must contain one row per whole holdout trajectory with:

```text
trajectory_id, method, final_iou_d050, final_tip_error,
event_time_error, forecast_rmse, fixed_final_iou_d050,
fixed_tip_error, fixed_event_time_error
```

The fixed-physics metrics must be identical across all method packages.

## Sealed support truth

Provide `SEALED_TRUTH.json` separately from training and selection:

```json
{
  "term_names": ["candidate_a", "candidate_b"],
  "declared_support": ["candidate_a"]
}
```

Selection code must not access this file. The comparison gate opens it only
after all three method packages are complete.

## Command

```bash
python SENS_tensile/run_freeze_select_comparison_gate.py \
  --freeze-then-select /path/to/freeze_then_select \
  --single-shot /path/to/single_shot \
  --joint-training /path/to/joint_training \
  --sealed-truth /path/to/SEALED_TRUTH.json \
  --output-dir /path/to/fair_comparison_gate
```

Exit code `0` means the packages are validly comparable. It does not by itself
mean Freeze-Then-Select improved reliability. The authoritative scientific flag
is `freeze_then_select_reliability_improved` in
`comparison_gate_report.json`.

## Reliability gate

The flag becomes true only when Freeze-Then-Select simultaneously:

- reaches support Jaccard at least 0.75 and exceeds both baselines;
- reaches support stability at least 0.70 and exceeds both baselines by 0.05;
- meets true/false frequency and sign-consistency gates;
- improves held-out weak residual by at least 5%;
- improves median IoU by 0.08 over fixed physics and 0.04 over each learned
  baseline, with at least 60% whole-section win rate;
- improves crack-tip error and does not worsen initiation-time error;
- has no catastrophic holdout-section regression.

## Evidence boundary

The gate reports only the declared factorial FEM/synthetic-road package. A pass
must not be generalized to real roads without a separately declared road-data
validation package.
