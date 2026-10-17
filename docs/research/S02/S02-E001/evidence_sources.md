# Evidence sources

This audit reused existing locked evidence; it did not recompute scientific
metrics or open a new holdout.

## Tier A

- Four-trajectory factorial manifest and state/event identities:
  `local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/factorial_loco_temporal_dataset_20260729/RUN_MANIFEST.json`
- Complete-trajectory LOTO and leakage lock:
  `local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/factorial_loco_temporal_dataset_20260729/within_hard5_factorial_loco_split_lock_v1.json`
- Cross-Umax event semantics and short-horizon protocol:
  `docs/experiments/cross_umax_short_horizon_forecast_preregistration_20260818.md`
- Cross-Umax secant and uncertainty result:
  `docs/experiments/cross_umax_short_horizon_forecast_result_20260818.md`
- Autonomous timing negative result:
  `docs/experiments/cross_umax_autonomous_timing_track.md`
- State-conditioned transition negative result:
  `docs/experiments/cross_umax_state_conditioned_transition_track.md`
- Matched temporal model corrected decision:
  `local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/temporal_architecture_study_20260718/multi_origin_reanalysis_20260720/analysis/decision.md`
- D1 data-only lock and current model boundary:
  `docs/experiments/at1_fatigue_mesh_pino_d1_final_prelaunch_lock_20260826.md`

## Tier B

- Road coverage audit and machine table:
  `docs/real_road_trajectory_coverage_matrix.md` and
  `docs/real_road_trajectory_coverage_matrix.csv`
- Six-section acquisition gate:
  `docs/ltpp_geoforecast_multisection_gate_20260805.md`
- Leakage-safe transition receipt:
  `local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805/adjudicated_transitions/transition_manifest.json`
- Persistence, local-tip and hierarchical state-space terminal decision:
  `docs/ltpp_geoforecast_algorithm_plan_20260805.md`

## Interpretation boundary

The paths above are source evidence, not a new data freeze. Exact reuse in a
future Run requires rechecking file availability, repository identity and the
applicable external dataset/holdout hash policy.
