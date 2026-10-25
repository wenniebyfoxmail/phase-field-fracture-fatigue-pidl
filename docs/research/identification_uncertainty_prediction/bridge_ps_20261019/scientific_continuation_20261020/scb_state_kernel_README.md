# SCB conditional state kernel — development delivery, 2026-10-25

Purpose: implement the existing SCB state-information comparison, rather than repeat the Mendeley runs or metadata preparation. This is development capability, not an SCB result, receipt of data, or scientific execution authority. Work mode: daily iteration; original B owner and SCB case remain canonical. No independent review was requested or performed.

## Actual implementation

`scb_state_kernel.py` accepts qualified normalized numeric records and the existing six metadata tables. It implements whole-mother-core leave-one-out and one fixed alpha10 linear rate model:

`mu_arm(N+H) = a_obs(N) + H * beta_arm^T phi_arm(N)` (intercept unpenalized).

| Arm | Information and treatment |
|---|---|
| G | Same current observed length, most recent observed length secant, sin/cos of origin load phase, source-bound geometry/current load/origin-known planned-load covariates |
| C | Full G plus source-bound current global/local relative DIC statistics |
| H | Complete C plus own local-history residuals; the two chronological local-response slopes use the actual three observed cycle timestamps, not fixed offsets |
| D | Complete C plus the training-side residual belonging to a matched different mother core; same residualizer, coordinate scale and penalty as H |
| P / S | Same current-length persistence / same observed length secant |

For each outer core and H, all fits use only development cores. Rows first receive inverse-core-count weights, summing to equal mass per core. Standardization is also core-weighted. H/D have the same extra dimension; their **entire** shared transform is `[C mean/scale, own training innovation mean/scale]`, so the C coordinates and ridge penalty do not change by arm. Coefficients can change during joint fitting; no claim of orthogonal/causally identified innovations is made. The shared `m(C)` is a training-side alpha10 ridge onto the two local-history slopes. D reuses the selected donor's innovation at the donor's C, not a future label or a held core's history.

Donor eligibility excludes the query's mother core, uses only the fit-side pool, matches an origin-known geometry/load-plan support stratum and circular phase tolerance, then minimizes standardized G distance with deterministic core/test/origin ties. The maximum distance and its development/source basis are currently unbound. No support is explicit: unavailable D predictions are retained as `DONOR_UNSUPPORTED`; any incomplete D core mean is null, not a mean over a silently easier subset. C/H origins and their state primary remain present. Unsupported training-side donors make the entire D fit unavailable for that fold; actual solve counts then fall below the fully-supported planning count.

For every outer core/H, C alone is cross-fitted over development cores to estimate a common **mm-scale residual RMS**, equal-weight by core. `sigma=max(C cross-fit RMS, predeclared positive floor)`. The floor/basis are pending actual reference/development evidence. The identical sigma is assigned to G/C/H/D/P/S. It mixes process, reference and model error; it is not identified R or Q, and reference variance is not added twice. Gaussian CRPS uses its closed form. This unconstrained conditional Gaussian/point-estimate family is an engineering probe, not a physical posterior or a calibrated-coverage claim.

Outputs contain every planned origin/H/arm mean, sigma, independent reference, CRPS, increment MAE, status and reason; per-core means and per-core primary contrasts; equal-core per-H summaries; fixed-primary-H `CRPS(H)-CRPS(C)`; source/reference access, fold/core, transforms and donor provenance. There is no model, weight, alpha or H search. Qualify unreadable/late observations and reference coverage upstream; the kernel refuses missing planned references/prefixes rather than interpolating or dropping them.

## Normalized input boundary

These are **our adapter target fields, not author CSV headers**. Current source-specific headers, stereo processing and feature extraction are not inferred. Where valid author DIC/statistic exports exist, use those first. Raw stereo-DIC extraction remains separate processing work whose format and cost require the actual files.

- The six metadata tables stay at the original SCB case's `state_interface_preparation_20261020/received_metadata.json` and keep their existing columns.
- `response_rows`: `test_id, cycle, roi_id, current_length_mm, response {declared feature:value}, response_asset_id, geometry_asset_id, feature_pipeline_id, source_max_cycle`.
- `origin_covariates`: `test_id, origin_cycle, roi_id, values {declared G-extra feature:value}, available_at_cycle, load_plan_asset_id, geometry_asset_id, matching_stratum`.
- `reference_values`: `reference_id, length_mm, reference_source_asset_id`. Future values travel separately from features; model/scale reference reads have explicit allowed-core scopes.

The payload has exactly these three tables. Metadata/provenance joins enforce original test/core/ROI, source IDs, mm geometry, actual history timestamps, phase, source maximum cycle, origin-known plan and future-reference identities. This verifies declared consistency, not the physical truth of independence or registration; a source qualification record must substantiate those facts.

The new `minimum_source_bindings.json` is in the existing reception directory. Its four unresolved rows request: (1) mother-core/entity map; (2) images or valid DIC with common ROI/calibration; (3) frame-cycle-load-phase and origin-known plan; (4) independent future crack length with resolution and permission. No artificial row is written into received data. Actual core/test/origin counts and full scientific costs remain null.

A future authorized producer must bind manifest `files` with `asset_id, relative_path, bytes, sha256, permission_reference`, one normalized-payload path, and a source qualification record. Logical asset IDs can be direct files or explicitly documented lineage via `asset_evidence` (evidence file ID plus `direct_file`/`documented_lineage`); receiving an author's DIC export does not falsely imply receiving the raw camera files. Common pipeline/registration/ROI identities must be bound in `processing_qualification`. Files must resolve inside the existing SCB case and match bytes/hash before the numerical payload opens.

## Real-run boundary

Default `scb_state_config.json` deliberately leaves source columns/units, real H, phase/matching limits, sigma floor, reference effect delta and budget unbound, and real execution disabled. `inspect_real_case` returns `REFUSED_UNBOUND_OR_UNAUTHORIZED_REAL_EXECUTION`, with zero numerical payload reads and zero fits. It neither checks email nor acquires any data.

The real CLI requires one actual consolidated data-use/CPU-budget authorization for the dataset, permissions and approved Linux hostname, plus qualified sources and source-side H/delta choices. Mac real fitting is rejected. A future CPU run uses one affinity/thread, an address-space backstop no larger than8GiB, absolute job timeout, source/output caps and retained failures. This implementation is **not permission to run** and does not borrow an old1800-second balance. The real producer path is not claimed exercised by the artificial development benchmark.

## One fixed development benchmark

Use only the command declared before implementation in the canonical SCB case:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /Users/wenxiaofang/miniconda3/envs/phasefield-pinn/bin/python -B /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/mendeley-info-value-20261019/docs/research/identification_uncertainty_prediction/bridge_ps_20261019/scientific_continuation_20261020/benchmark_scb_state_kernel.py --case /Users/wenxiaofang/phase-field-fracture-with-pidl/research_hq/identification_uncertainty_prediction_20261006/scb_request_design_20261019
```

One all-artificial representative route: four fake mother cores, two fake origins each, one fake10cycle horizon, known constant growth. It has an analytic conditional-mean and Gaussian-CRPS oracle,32 tiny closed-form solves and48 six-arm output rows. Necessary truth constraints are checked on the same fixture without another study. The existing real received_metadata hash is unchanged. Final benchmark passed in0.035s; these are development values and timing, **not SCB performance or physical specimen counts**. Before final delivery, G's phase coordinates were made explicit and the same affected end-to-end benchmark was rerun; no additional suite, historic run or independent review was added. Passing ends this development validation.

Result: original SCB case `benchmark_result_20261025.json`. Implementation/method/source-dependency/next-decision record: `KERNEL_IMPLEMENTATION_20261025.md` at the same case. Do not put benchmark fixtures in the real reception directory.

## Next physical decision

Use the already requested source package, not a wider search or an unsolicited email. Once its actual list, permissions, independent reference and scale are known, source-adapt and quantify one complete CPU/DIC/storage/reference budget, then present **one** dataset-use + full-comparison decision. Primary H and delta must be fixed on development/source evidence before outer scoring;500cycles and six independent cores are not defaults.

| Actual outcome | Route impact |
|---|---|
| H improves C and matched D beyond reference resolving ability, survives per-core and failure-trajectory inspection and simpler G/P/S comparisons | Advance the bounded predictive-state component; do not claim unique physical memory |
| Measured load/phase/registration explains the apparent H effect, or a simpler G/P/S is sufficient | Simplify to the measured driver/current baseline |
| H does not beat C/D, gain appears only in DIC but not independent future length, or grouped failures persist | Preserve negative result and stop time-mechanism expansion |
| Entity/synchronization/reference/permission is missing or D lacks common support | Keep the relevant mechanism contrast inconclusive; no fake target, subset rescue or new model menu |

The G/C/H/D intervention is distinct from original observation-UQ A/B/C. State gains do not establish observation-UQ benefits. Existing R003 warning breach, R005 C27-A25 zero benefit and adverse cells remain unchanged.
