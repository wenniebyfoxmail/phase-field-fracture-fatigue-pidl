# D3 candidate preparation and exact-diff review — 2026-10-20

Status: implementation candidate prepared; no producer or real-image algorithm
execution. Local author review plus separate numerical formulations, **not an
independent-agent review** or a physical validation. No training or new labels.
Continue the existing E049/D3 record; author reply is not a dependency.

## Binding

- Implementation SHA256 `27ad7b5c23f77f626bebd7e6659c26258bea6be327989bd9dbc21584db4cf8ed`.
- Test SHA256 `4f1599473329d278a058dfdd888d30c079e8629245bb744c0edfba50c5d64059`.
- Protocol SHA256 `cbbb14a6e9e3916a4439a1a3d61ff4d7e3a3d75ba0fe83fedcfb7374b623a105`.
- Final local identity-only contract SHA256 `de8eaddfd6187bd163e4caf77ef69782368ca5822dc06ccf9f9e22044d83e0de`.
- Contract location: parent `local_archive/experiments/S03-E049-MD03/
  D3_controlled_opening_20261020/preparation/contract_v2.json`. Exactly9existing
  input files hashed,3source TIFF identities checked; no NPZ/TIFF decode.
- New code/tests/protocol are additive; old E049/D3 scripts, masks, half-depth
  and scores are untouched. Documentation is the only existing tracked change.

## Checks actually performed

`python -m unittest discover -s tests -p test_md03_controlled_opening.py -v`:
25tests pass, final unittest runtime0.059s (software checks, not scientific cost).
Tests generate artificial arrays only. They compare known2px step vs internal
controls, dark paint without motion, translation/brightness, smooth linear
field, fractional sampling, zero/occluded/repeated/unrelated texture, validity
holes/search edges, forward/reverse signs, unknown preservation, all15common
denominator, matched stencil count, manifest parameter/input/code drift and
non-overwrite behaviour. Independent NumPy NCC and closed-form coefficients
check the numerical formulations separately from OpenCV/OLS.

First unit invocation had2assertion failures: the independent intercept check
reversed left/right coefficient order, and its exact-identity assertion ignored
finite-window parabola bias (~.0081px). Corrected the checker coefficients and
declared .02px software tolerance for that identity fixture; no real-data/QC
threshold changed. Subsequent22tests, then expanded25tests pass. This is not a
scientific retry or altered measured criterion.

Final entrypoint review found the internal worker checked fewer admission fields
than the parent. Before any real execution it was changed to recheck the entire
decision/output/input contract and matching parent start receipt. The25tests
were repeated successfully. Identity-only contract_v2 binds that final code;
the earlier contract.json is retained as a superseded preparation snapshot,
not a run or retry. No thresholds, input images or observer outputs changed.

The real local contract then validated against final code/protocol, still
without image decoding. No run/worker/renderer on the real archives was invoked.
No remote admission/SSH, new source access, manual/AI annotation or email action.

## Exact change review

| Risk | Reviewed implementation / retained limitation |
|---|---|
| Wrong sign/coordinate | n=(+x), right-minus-left intercept; reverse starts at matched B point and checks d_forward+d_reverse; saved A→B matrix direction and interpolation support tested |
| Unequal comparison | Each central/internal arm uses identical6offsets,31px/±4NCC,reverse checks and5declared transforms; internal supports stay on their designated side |
| Unknown as zero / selective support | Raw diagnostics retained; quality failure yields null J; visibility always unknown; envelope requires all15estimates, missing values leave holes |
| Hidden result selection | Same4prior columns×21rows on both pairs; x2782 explicitly prior algorithm-selected, no new hotspot/width/forecast-error choice |
| Guessed independent reference | No author endpoint/channel targets or new labels; internal stencils not certified crack-free; positive E only within-control specificity |
| Old evidence rewrite | New isolated output root/freshRunID, exclusive JSON creation, exact9input hashes pre/post, no old code modification |
| Run authority/resource | Mac admission and worker refused; exact decision/host/manifest/output required, one child with600s hard timeout, STOP per gauge, no fallback/retry; memory<2GB is an estimate, not an enforced cap |
| Claim leakage | Two exposed intervals from one beam; no forecasting/known future loads, no physical aperture/mm or independent validation claim |

Real OpenCV matching quality/coverage, runtime/RSS, artifact visual layout and
physical interpretability remain **unmeasured**. The renderer is implemented
and statically checked, not claimed visually validated. Its real output needs
visual QA after an exact approved producer execution. Related limits include
nearby cracks in internal arms, continuous nonlinear deformation, 3D/perspective
effects, unknown actual crack normal, and repeated texture that still matches
consistently. No numerical QC screen alone eliminates those alternatives.

## Decision

Prepared for review of one complete producer comparison under
[the protocol](controlled_opening_protocol.md); no new real-image result exists.
Before execution: choose/approve exact producer host, archive root, RunID and
manifest, then perform normal resource admission once. The local contract's
absolute Mac archive root is not a remotely usable path. No author reply needed.
