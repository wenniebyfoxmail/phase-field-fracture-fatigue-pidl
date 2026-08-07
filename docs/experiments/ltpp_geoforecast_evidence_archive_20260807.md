# LTPP GeoForecast evidence archive — 2026-08-07

## Purpose

This document is the compact Git-tracked index for the LTPP annotation and
forecasting work completed on 2026-08-05 through 2026-08-07. Source code,
protocols, reviews, tests, and concise decisions belong in Git. Bulky source
images, GeoJSON packets, posterior samples, recognition panels, and registration
renders remain under the parent repository's `local_archive/` tree.

The archive preserves negative results. It does not promote any failed route or
turn the adjudicated scan annotations into physical ground truth.

## Canonical labelled packet

Local payload root:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805`

Contents and credibility:

- `primary/`: 37 locked AI-primary maps; supporting annotation evidence.
- `secondary/`: 37 locked human-secondary maps; supporting annotation evidence.
- `adjudication_queue.json`: 139/139 reviewed dispositions; canonical decision
  history for the frozen packet.
- `adjudicated/geojson/`: 37 final states, 249 geometries, including 232 crack
  geometries; canonical current-map labels within the declared scan frame.
- `adjudicated_transitions/`: 31 leakage-safe transitions; canonical transition
  carrier for the completed benchmark.
- `frozen_baselines/`: persistence, scalar-growth, and local-tip controls;
  canonical benchmark evidence.
- `hierarchical_state_space/`: terminal negative challenger; negative evidence.

Verified receipt hashes:

| Receipt | SHA-256 |
|---|---|
| adjudicated manifest | `6a9422bdcef707fa861b05ad0c817d6deaa4e4ad03ea636c46c5820f8b01f4ad` |
| transition manifest | `1c38725d23a9cdaea69e3f71b5eaaa6469d02371c85de7a3b2061ba79e92e918` |
| baseline manifest | `e70564d3e06c81517268c0974845759e7a307769ee3478534cd8f08b8bee2b55` |
| state-space decision | `a71e2c87068fc400e12b6e200a6d34c4719545b71819f6f52cdf82650353ecce` |

## Completed evidence tracks

| Track | Decision | Raw payload | Canonical Git summary |
|---|---|---|---|
| dual-blind annotation and scalar benchmark | `RELIABILITY_NEGATIVE__PERSISTENCE_REMAINS_CONTROL` | canonical labelled packet above | `docs/ltpp_geoforecast_algorithm_plan_20260805.md` |
| enriched source-available inputs | `PRIMARY_NEGATIVE__ORACLE_DIAGNOSTIC_COMPLETE` | `local_archive/real_road_acquisition/ltpp_geoforecast_enriched_posterior_v1_20260806/` | `docs/experiments/ltpp_geoforecast_enriched_input_track.md` |
| load-only ESAL increment | `PRIMARY_NEGATIVE__LOAD_ONLY_COMPLETE` | `local_archive/real_road_acquisition/ltpp_geoforecast_load_only_posterior_v1_20260806/` | `docs/experiments/ltpp_geoforecast_load_only_incremental_track_20260806.md` |
| current-map crack recognition | `RECOGNITION_GATE_FAILED` | `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b0_v1_20260806/` and `...b1_v1_20260807/` | `docs/experiments/ltpp_geoforecast_crack_recognition_track.md` |
| two-dimensional registration | `SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL` | `local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_audit_v1_20260806/` | `docs/experiments/ltpp_geoforecast_spatial_registration_track.md` |
| natural-evolution metadata audit | `PASS_NO_DOCUMENTED_MAINTENANCE__ONE_TERMINAL_CENSORING_EXCEPTION` | `local_archive/real_road_acquisition/ltpp_natural_evolution_episode_audit_v1_20260806/` | `docs/experiments/ltpp_geoforecast_natural_episode_audit_20260806.md` |

Additional verified result hashes:

| Result | SHA-256 |
|---|---|
| enriched-input sealed evaluation | `f3a18f4fc9bdd186da8d1e42fad44d688030e5569f17f36a720f76e53e26c6d2` |
| load-only sealed evaluation | `c0f0d2006661b514e332c3446fa8257f536d69010006fd8e8dd2998cb7d4ba03` |
| recognition B0 metrics | `e4757d61011ad151e7e2fcec03b917f5ee01658e8f4bf70b5ec66c86dacdc1e9` |
| recognition B1 metrics | `7d9ae5bca02a37fa2db1cc533225532d75bc477f89c8242d8f661da7df3ea242` |
| spatial-registration v1 audit | `925ceeaa7dd86a7b457067544f162ecdc7492a0ce95a974c859046c88d5b7666` |

## Verification status at archive time

- All `tests/test_ltpp_*.py` tests passed: `38 passed` using the project
  Miniconda Python with the frozen LTPP PyMC environment on `PYTHONPATH`.
- All archived LTPP Python entry points passed byte-code compilation.
- The spatial-registration v1 package passes the whole-directory research
  figure sidecar validator.
- The recognition B0 and B1 packages contain 37 documented four-panel audit
  figures each, but their whole-directory validator currently fails because
  intermediate gold/prediction mask PNGs do not have individual sidecars. This
  is a documentation-packaging limitation, not a metric recomputation or a
  reason to alter the frozen negative recognition result.

## Claim boundary

The archive supports the existence of a six-section, 37-state, 31-transition
human-adjudicated small-sample benchmark and the reported frozen negative
results. It does not support reliable two-dimensional crack evolution,
automatic replacement of human annotation, causal effects of traffic or FWD,
or generalization to ordinary road photographs or the full LTPP database.

The current labels are canonical observations of the scanned maps. They are
not independently surveyed material-point crack geometry. Registration failure
therefore blocks spatial-position and continuation-tip claims while leaving the
separately evaluated scalar-length results intact.

## Recovery and next action

To recover the work on another machine, check out the Git commit containing
this index and restore the named `local_archive` directories without changing
their paths. Verify the listed SHA-256 receipts before running any code.

No further architecture sweep, threshold search, row deletion, or registration
rescue is authorized inside the closed tracks. A new attempt requires its own
dated preregistration or amendment and must preserve the negative evidence
listed here.
