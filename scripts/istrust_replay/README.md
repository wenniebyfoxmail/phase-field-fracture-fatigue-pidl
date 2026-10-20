# ISTRUST sixth-epoch replay

Owner/protocol: docs/research/S02/S02-E007/experiment.md. This wrapper imports the pinned author's architecture and preprocessing. It patches only filename iteration order in a temporary source copy, retains target/split semantics, and runs no training or observation-noise experiments.

`replay.py`: ordered manifest, original preprocessing, strict normalization comparison, six sixth-epoch checkpoint pairs, fixed original MC dropout, complete CSV/NPZ outputs and unchanged model-state checks.

`controller.py`: verified public asset intake, bounded producer process group, time/RSS/storage enforcement, first-stop persistence, no retries. `setup_environment.py`: isolated historical numerical packages, without model/data evaluation. `test_replay.py`: lightweight manifest and process-lifecycle checks; the manifest tests use the previously audited local filename inventory.

Author source/data and checkpoints are external locked assets, not added to Git. Preserve the author's LICENSE and attribution in every source snapshot. See the protocol for the Python-version difference, retrospective evaluation population, A003 handling, target offset and interpretation of the historical plotted bands.
