# BRIDGE-PS-v1.0 exact implementation review v1

2026-10-19, Europe/London. Independent read-only Codex reviewer `/root/bridge_exact_review`, distinct from the implementation owner. Verdict: **MODIFY_AND_REREVIEW — two bounded controller/provenance fixes required**. Scientific interface/algebra checks below pass within the stated artificial scope, but the prepared job has an avoidable owned-file rename race and lacks explicit end-time provenance. This is neither production-runtime validation nor execution permission nor scientific success.

## Exact material and access

- Implementation commit: `2ef6eec513742a5225d14f99779f1aa0ab61695f`.
- Worktree: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/mendeley-info-value-20261019`.
- Reviewed package: `docs/research/identification_uncertainty_prediction/bridge_ps_20261019`.
- Canonical package-lock digest, recomputed using `contract.package_id`: `bf4b810267e54dc540232c6fa91c85f1137592f0e83b19dd611c7c523c43467e`.
- All 17 lock-listed files matched their hashes. Working source delta against the exact reviewed commit was empty; `git status --short` was empty at review.
- Design source: `569cc865a9090e050042c7daf037cd2f0e535bba`; copied full design and plan read.
- Vendored R002 source hash `262b8ddb79f81896e6dcb6717e4722f479a6bca65a3dc84e33a322097e555d1a` independently matched `git show 5ea77160e8bb72a1b3b7a2d91d9bcf09282f5011:docs/research/identification_uncertainty_prediction/response_state_value_20261019/runner.py`.
- Scope: text/code and metadata JSON only, including frozen 1144-case identity list, 19 exposed released groups, H10/H40, 180-file manifest, source hash records. No saved NPZ/PT/scientific CSV/XLSX was opened; no SSH, resource preflight, real fit, real forward, new holdout, external message, or implementation change occurred. This review report is the only authored artifact.

## Checks actually performed

1. Read `state.py`, `worker.py`, `contract.py`, `supervise.py`, `verify.py`, `analysis.py`, lock builder, production config, implementation note, execution card, full design and test sources. Compared the feature/ridge/loader/score interface with immutable R002 source text.
2. Ran `python3 -m unittest discover -s <package> -p 'test_*.py'`: **30 tests passed** on the Mac. Floating-point matmul RuntimeWarnings remained visible; they were not suppressed. Thus this is not a warning-free runtime receipt.
3. Ran `worker.py --check`: returned `METADATA_CONTRACT_CHECKED_NO_SCIENTIFIC_ARRAY_IO`, 19 groups / 1144 origins / 2288 horizon cases and `production_authority:false`. This command is a metadata contract check, not a source-data availability check or real preflight.
4. Independently tested hand-authored 7-row / 36-column algebra, unequal group sizes A=2/B=3/C=2, and constant columns (including a transformed global-mean coordinate). Checked equal total group weights and used non-BLAS `einsum` contractions for the generalized normal-equation residual. Maximum function difference and maximum normal-equation residual were both `8.881784197001252e-16`, below unchanged `1e-11`. RuntimeWarnings were retained here too. This is synthetic algebra only, not benchmark fitting.

## Blocking fixes

1. **[P2] `supervise.size` has an unhandled top-level archive-rename race.** Its top-level `if p.is_file(): return p.stat().st_size` is outside the FileNotFoundError guard used for directory children. The worker deliberately renames `results.tar.gz.partial` to `results.tar.gz` while the controller polls both. If the old name disappears between `is_file` and `stat`, the controller first-stops a valid completed or completing job. I reproduced this using only artificial patched Path probes: `is_file=True`, then `stat` raising `FileNotFoundError`; the exception escapes `size`. Handle disappearing top-level files as an expected owned atomic rename, retain the archive-size checks on the surviving name/next observation, and add this exact synthetic race regression. No real filesystem/prod job was required.
2. **[P2] Explicit UTC end timestamp is missing from the complete and stopped run records.** Worker provenance saves `started_at_utc`; controller receipts save only elapsed monotonic seconds. The execution card asks for start/end provenance, and no `ended_at_utc` is persisted. Add explicit UTC start/end timestamps to the controller receipt on both complete and stop paths (including cases failing before the worker), keeping monotonic wall seconds for budget enforcement. This is a provenance repair, not a scientific change or a request to launch a timing probe.

These items were identified before changing the frozen target; the implementation owner separately flagged the same two candidate risks for assessment. The race reproduction and code-path findings are my independent checks.

## Decisive implementation findings

### Fold-local information, current prefix, and donors

`features` reproduces C_RAW/H_RAW/H_REL coordinate order against the immutable R002 composer and builds the 12-dimensional history differences from only the declared three observed stages. C_REL drops current global means as designed. H_INNOV/H_DONOR retain the exact first 20 C_RAW columns; predictor prefix means/scales are locked to the same training-side current estimator and match the raw comparator. Remaining-column normalization is fitted on that same training side.

The input residualizer uses fixed alpha 10, equal total released-group weights and only the relevant inner-fit or outer-development inputs. Query inputs do not estimate means/scales/m; query histories do not affect the donor arm. Nearest donors use only the corresponding training pool, exclude the recipient's entire released group even for training recipients, and resolve equal squared distances by `(group, origin_stage, frozen case index)`. No targets are used for donor matching. Synthetic contamination and tie checks passed.

### Penalty and equivalence

The implemented transform changes each old local mean to local-minus-global while retaining the global coordinate. With raw scale Dq and transformed scale Dz, the stored generalized penalty is `Dz^-1 T Dq^2 T^T Dz^-1`. Coefficients are transformed by `Dz (T^-1)^T Dq^-1`; transformed means preserve the original intercept. The intercept is unpenalized. This is a coefficient/penalty transformation with zero additional solves, not an extra tuned arm. Artificial function, objective, and normal-equation checks pass, including unequal group sizes and constant-column scale-floor handling.

Runtime separately compares saved H_RAW and pullback predictions, and per-case scores, with strict discrepancy `<1e-11`. Three R002 arm replays compare source-identified coarse predictions, training normalizers and recomputed scores with the same strict threshold. Source artifacts are hash checked before any real solve. No fallback regenerates a missing source artifact.

### Selection, counts, scoring, plots

All six arms use the original three inner alpha values and same group split. B* receives only inner-validation losses for P/S/C_RAW/C_REL; its chosen method is frozen before held scoring. Exact-tie order is P, S, C_REL, C_RAW. Outer labels affect held evaluation, not selection or training normalizers.

Loop accounting is 19 x 2 x 6 x (3+1) = 912 main solves, plus 19 x 2 x 2 = 76 input solves. Caps are checked before extra solve. Nine main scored methods (six learned, P, S, pullback) produce 20592 rows and B* adds 2288 copied rows. Counts require 228 learned archives plus 38 pullback archives; input-evidence and reweighting archives are additional evidence files, not miscounted predictor archives.

The post-run score verifier reconstructs all native predictions from saved coarse outputs, independently applies the direct full/band NMAE formula, checks source normalizers/case membership and B* row copying, verifies donor membership/group exclusion, and checks expected counts. It does not refit or run coefficients forward. It does not independently rederive every saved input-estimator parameter, donor distance, inner loss or diagnostic column; those are covered by reviewed code and artificial tests, not an independent scientific-data recomputation. Its final wording must keep that distinction.

Output contracts preserve both channels, signed increments, centered errors, fixed-band loss, signed masses, explicit undefined ratio for exactly zero reference, and local peak/error positions. Plots reconstruct saved outputs only. All group/H cells get an origin-to-H curve and midpoint plus explicitly post-hoc worst-H_INNOV examples, with common reference/prediction and error scales within each channel. Full group/H scores are saved. No plot silently converts release steps to cycles or displacement to crack truth. Reweighting remains empirical benchmark sensitivity, not a population CI.

### Authority, first stop, and budgets

Default worker and controller paths require exact package approval before any scientific loader or launch. Default-path tests guard both `numpy.load` and `Popen`. Source/config/manifest/lock binding prevents unnoticed code or budget edits under the same approved digest. Worker requires an immediate-parent controller identity and fresh output directory; controller exclusively creates the run claim and denies reuse. A receipt/flag never creates human authority.

Controller gives its owned worker 1800 seconds across input checks, modeling, independent score verification, plots and archive; sets one-thread BLAS/OpenMP and empty CUDA visibility; applies 8 GiB address-space cap and polls worker RSS/HWM, generated outputs/tmp/cache/logs <=4 GiB and archive <=4 GiB. It kills only the owned child process group on error. Worker has no subprocess launch in the reviewed path. Warnings become errors before real preflight; model/identity/nonfinite/replay/equivalence errors stop the worker and retain a STOPPED_NO_RETRY receipt. No retry/resume/machine-switch path exists.

## Residual limitations and handoff

- Linux resource/process-controller integration, actual input availability, dependency compatibility, real-array replay/equivalence and total time/RSS/storage remain **unmeasured**. The Mac warnings are a material residual runtime uncertainty. Do not suppress them, relax the threshold, or treat fixture success as permission to ignore a later producer stop.
- `contract.approval` requires a nonempty implementation-commit field but does not programmatically compare that descriptive string with the Git commit. The exact approved package digest does bind runtime bytes, so this is not an unidentified-code execution gap in the reviewed card. The final human approval/card/provenance must explicitly carry the full commit above and this digest; do not claim that the commit string itself was mechanically verified at runtime.
- Group physical independence and physical clock remain unknown; shared native current-field anchor and exposed development cohort limit the interpretation. No state sufficiency, independent fatigue memory, calibrated physical UQ, autonomous rollout or road prediction claim is admitted by this review.
- Any change to the lock-listed implementation/config/protocol requires a new digest and focused difference review. Only the two controller/provenance fixes above are requested; scientific implementation findings carry forward if unchanged. The next permissible action under the current delegated scope is repair the two bounded controller/provenance issues, seal the new exact snapshot, and obtain a focused difference rereview, **not** SSH or execute it.
