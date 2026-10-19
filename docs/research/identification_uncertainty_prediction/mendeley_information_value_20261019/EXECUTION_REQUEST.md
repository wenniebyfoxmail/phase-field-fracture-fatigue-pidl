# Execution package — USER AUTHORISED CHECK AND PROCEED 2026-10-19

Owner: IU→Prediction; exploratory published-DIC information-value branch. 2026-10-19.

Code: `/Users/wenxiaofang/phase-field-fracture-with-pidl/research_hq/identification_uncertainty_prediction_20261006/mendeley_information_value_20261019/runner.py`; config: `config.producer.json`.
Exact source+producer-config SHA256: `54517159bf9202841828fbf2c814b2521d8178f756dc2d848bfa230aa6f638d8`.
Inputs pinned by metadata SHA256 in config; provenance is the existing S02-E006 extraction and official PT archive SHA256 `726f81fdc474688c7a454ed72f07acc6490c7f79c149829dde33c2ecd6aa9244`.
Data already held: 17925CSV/17897PT frames/19 release groups; only PT+existing metadata staged for this branch. Existing owner outputs untouched. No new files downloaded.

Proposed Taobo root (not created/checked): `/mnt/data2/drtao/wennie/IU-PUBLISHED-DIC-20261019-R001`. Single CPU thread; 0 GPU; 4h wall limit; 8GiB memory limit; <=8GiB outputs; no auto retry. No trained checkpoint from another owner used. No protected independent holdout opened; all release groups already development-exposed.

Planned commands on the approved producer, AFTER transfer/root/space/runtime verification and explicit approval:

```sh
ulimit -v 8388608
timeout 14400s python3 /mnt/data2/drtao/wennie/IU-PUBLISHED-DIC-20261019-R001/code/runner.py --config /mnt/data2/drtao/wennie/IU-PUBLISHED-DIC-20261019-R001/code/config.producer.json --output /mnt/data2/drtao/wennie/IU-PUBLISHED-DIC-20261019-R001/outputs --run --approved-package-sha256 54517159bf9202841828fbf2c814b2521d8178f756dc2d848bfa230aa6f638d8
```

`--approved-package-sha256` is an exact-package guard, never human permission. Local metadata prepare may be included in the same later authorisation; it has not been executed. Producer python environment must contain numpy, torch, matplotlib. Runtime compatibility and raw PT path integration are untested; do not claim Code Ready or launch before review of exact deployment. If runtime/config requires change, update this package and ask once for that final version. No automatic fallback producer or retry.

Expected deliverables/claim boundaries are in design.md. Four metadata-only unit tests passed; no tensor loading, model fitting, data staging or producer run in this task. Final request remains pending; SCB mail remains separately pending human send approval.


Current authority: user2026-10-19 explicitly authorised checking the implementation/package and proceeding when sound, while keeping SCB mail unsent. Routine cache/serialization fixes reviewed in implementation_review_20261019.md. Prior pending-approval language above is historical. Bounded producer execution authorised, no automatic retry or budget extension.
