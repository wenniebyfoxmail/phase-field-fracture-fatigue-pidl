# ISTRUST sixth-epoch replay

Owner/protocol: docs/research/S02/S02-E007/experiment.md. This wrapper imports the pinned author's architecture and preprocessing. It patches only filename iteration order in a temporary source copy, retains target/split semantics, and runs no training or observation-noise experiments.

`replay.py`: ordered manifest, original preprocessing, strict normalization comparison, six sixth-epoch checkpoint pairs, fixed original MC dropout, complete CSV/NPZ outputs and unchanged model-state checks.

`controller.py`: verified public asset intake, bounded producer process group, time/RSS/storage enforcement, first-stop persistence, no retries. `setup_environment.py`: isolated historical numerical packages, without model/data evaluation. `test_replay.py`: lightweight manifest and process-lifecycle checks; the manifest tests use the previously audited local filename inventory.

Author source/data and checkpoints are external locked assets, not added to Git. Preserve the author's LICENSE and attribution in every source snapshot. See the protocol for the Python-version difference, retrospective evaluation population, A003 handling, target offset and interpretation of the historical plotted bands.

Protocol 1.2 uses `download_ranges.py` for 32 independently validated public byte ranges, capped at 10 MiB/s total and four CPU cores. Acquisition may consume 90 minutes of the unchanged four-hour batch budget. No retry; exact canonical ZIP SHA-256 is checked before extraction. `test_download_ranges.py` exercises synthetic assembly, rejected/short ranges and owned-child cleanup.

Protocol1.3 corrected the zero-forward R001 CUDA admission stop. `gpu_admission.py` verifies the visible physical UUID through the CUDA driver before torch import/scalar allocation, while permitting the numeric mask required by pinned torch1.13. The subsequently authorized R004–R006 batch completed; its receipt and aggregate-only reproduction conclusion are in `docs/research/S02/S02-E007/README_analysis.md`. The original failure and frozen protocol are historical records, not a pending launch instruction.

## Current validation policy — 2026-10-22

There is no active execution card or benchmark run; the baseline is delivered and its authority consumed. Do not rerun this model, historical tests, experiments or a smoke ladder to reconfirm the completed result. Do not add per-commit or metadata reviews. The original explicitly selected local code review remains a completed historical review, not a recurring requirement.

Within a future separately authorized task, use one existing fixed benchmark for the main function and declared comparison; deliver when it passes. Fix and rerun only failed items within the unchanged stop/retry authority. Documentation, wording, paths and metadata need only direct consistency checks. Do not relabel the complete historical test suite as a benchmark. No benchmark, review, helper or scientific run is commissioned by this documentation update; source/data identities, scientific criteria, budgets and protected inputs remain unchanged.
