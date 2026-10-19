# Fixed-alpha output-correction calibration — disabled implementation candidate

Purpose: test whether a training-selected global/centered output correction is useful beyond strong simple shrinkage/ablation. This continues the response-state-information question at the output-estimation interface; it does not test input identifiability, physical memory or causal contributions. The sealed mechanism diagnostic remains sealed, including missing plots. Source design fe54ab36df890551f13e0e515ab50c2ad69c97c8, STOPPED.md SHA334d050d2fb1924f5d9f6c4c647e04844c1a1ee9189b4d731581c98f7b655d8b. Current step: implementation and independent code/package review only; no scientific data/producer access, true fit/forward or launch.

## Frozen scientific contract

All19 exposed released groups,1144 origins, H10/H40, two channels, all3 C30 labels, no new data/case exclusion. Both base predictors and m use alpha10: a new fixed-alpha family, NOT R003 selected-alpha exact replay. Native target training preserves float32(target-current) then original16×16 pooling; native scoring subtracts target32 from float64 prediction. Feature means/std use training origins, ridge objective equally weights training groups, target normalizer uses training-origin amplitude mean/floor1e−6 exactly as the base source. Inner17groups, final18groups; future validation targets enter only the evaluator. Outer future targets cannot choose models/scales/weights. No cross-outer learned-state/prediction reuse. The adapter's immutable raw-derived target cache is NOT an estimated-state cache; every model/normalizer is estimated on its exact permitted index set.

U25 uniform pairs(k/24,k/24); A25 grid{0,.25,.5,.75,1}²; C27=U+global-only/spatial-only. Shared pair across both channels, separately selected per outer group/H on18 inner held-group means. Tie order: loss,total correction,anisotropy,lexical pair. Seven arms: current/history/global-only/spatial-only/selected U/C/A. Primary equal-group/equal-H native balanced loss(C)-loss(A). Same25 candidates do NOT imply equal complexity. A cannot be called necessary if a fixed corner is equally good/better; keep all corner/negative results, not a post-outcome filter. U/A grids are not nested. No significance/independence/physical-angle/road claim.

Correction d is one float64 native-prediction difference; g=spatial mean(d) per channel, s=d−g. Interior weights use pC+λg*g+λs*s, identical in scorer and decoder. For exact fixed endpoints(0,0)/(1,1), use pC/pH directly to preserve baseline bits (this arithmetic rule is prospective and shared by every candidate family). No bitwise-zero centered-mean assertion. Saved G/S diagnostics separately subtract prediction-current and float32(target-current), then cast/center; never add them as native-error shares or impose Jensen bounds. Native per-channel full/band, sign/mass and published-grid peak descriptors retain zero/undefined denominators and no physical tolerance.

Actual loop counts:19×2×19=722 training sets;1444 predictor+722 residualizer=2166 solves.41184 inner origin/H rows×45distinct pairs=1,853,280 native loss triples;2288 outer rows×7arms=16016 scores. Solve counters increment before each actual attempt (including a first failed solve), and score counters in the actual score path and are checked against independently derived geometry, not filled from expected values. Query prediction accepts current/history observations only, never future targets. Old outer predictions cannot produce legal inner OOF; this worker does not load those archives. Future actual availability/hash/schema verification remains unperformed.

## Runtime and transitive source

engine.py is the shared actual nested execution path used by artificial fixtures; producer_data.py is a future-only PT/native adapter; evidence.py streams exact loss triples and complete external fields; figures.py is the fixed new-package renderer. r002_base.py, legacy_state.py and runtime_guard.py are byte-identical reused source modules, with original identities recorded in the package lock. The old state.Fits caps/donor/replay worker are NOT used; feature construction is reused, with a new counted fixed-alpha ridge path. Its einsum Gram/prediction contractions avoid optional BLAS product dispatch without filtering warnings; this is not a bitwise R003 replay.

supervise.py reuses the reviewed lifetime guard: fatal destructor/thread/atexit events persist atomically, all worker stderr/nonzero exit stops, controller waits for process exit and a clean PID-bound seal. The complete worker including data checks/scoring/figures/hash inventories/uncompressed tar is bounded; controller checks storage/wall again after final hashing. Root must be fresh, code must be its sealed code child, exclusive run claim disallows retry. No old receipt is overwritten. Case/fold/normalizer provenance and the first failure persist before exception propagation. Startup failures have an explicit no-case dependency stage. Resource checks are sampled at0.25seconds, not a hard OS RSS cap; an8GiB AS backstop is separate from the2GiB sampled RSS cap.

Scientific/Python warnings remain errors, unexpected dependency logs and any stderr remain fatal. New future figure policy uses Agg, bundled DejaVuSans and a pinned Matplotlib version. Before font-manager import, only its exact known cache-build WARNING log is sent to an owned dependency log; other warning/error records raise. Nothing reads stderr back to whitelist it, no scientific warning is ignored, and this cannot generate old missing figures. All caches/temp files use the new root. Only artificial render fixtures have exercised this policy locally; Linux dependency/font/runtime feasibility is unknown.

Runtime source files and frozen metadata text are independently hash-bound in package_lock.json; each name must be a simple local basename. Third-party package versions are in config.json/requirements.txt; future versions are checked after authority, source resolution is checked before data loading. Python/platform/wheels/BLAS behavior and producer availability remain unverified. No external source path is imported implicitly. Metadata copies were hash-bound, not used to access scientific cases/targets during preparation.

## Evidence delivery and quantitative resource proposal — NOT APPROVED

The original100MiB cap is insufficient for this complete uncompressed-copy contract: inner triples44,478,720 + outer bases18,743,296 bytes already need126,444,032bytes for working copy+tar, before metadata/figures/models. Do not assume favorable compression. For self-contained seven-arm native field/error reconstruction and direct outer score recomputation, add current anchors149,946,368bytes and outer native references299,892,736bytes. These are exact float32 native arrays; all seven predictions are reconstructed without a model forward from these anchors, two float64 coarse bases and saved exact weights. engine.decoded_fields/evidence.read_fields are the authoritative decoder; fields/targets and both-channel errors are available for EVERY outer case, not just selected figures. This is a proposed evidence-storage expansion, not a new information set or permission to read/copy those arrays now.

Raw array total513,061,120bytes (~489.29MiB); no full inner prediction/coefficient cache is persisted. Inner native balanced/full/band scores are streamed with exact case/fold/candidate/training-normalizer and model hashes. Outer final models/scales, every arm/case score, sign/mass/peak denominator information, complete group/H results, selected weights and self-contained fields are retained. Independent reviewers can recompute outer native scores and saved inner aggregation; recomputing every unsaved inner residual would require separately authorized refitting. Do not claim it was done.

Proposed complete storage quotas, implemented by resource_contract.py:

| Category | MiB cap | Includes |
|---|---:|---|
| raw arrays |490| inner45×3 loss triples, two outer bases, current anchors, outer native targets |
| final models |16| all38 final current/history/m models and scales |
| metadata |32| all score CSV/JSON/JSONL, provenance/index/selection/context/receipts |
| figures |24| exactly3 PNG≤8MiB each, sidecars in metadata |
| logs |16| worker/controller/fatal/font dependency output |
| cache |64| Python bytecode, Torch/XDG/Matplotlib caches |
| code |8| complete source, lock, frozen metadata/requirements |
| temporary |16| non-archive tmp and atomic publications; raw arrays created exclusively without a second complete array copy |
| archive |700| uncompressed tar OR its in-progress partial; every existing copy counts |

Category sums1366MiB; total envelope proposed1536MiB (1.5GiB), leaving170MiB headroom. An extra archive/copy outside this envelope is forbidden; no output is moved outside the root to hide cost. Arrays use exclusive preallocated memmaps; any partial or failed artifact is counted and retained. Archive contains code and all scientific outputs; final lifecycle receipts/logs and delivery_manifest remain alongside it and are also counted. Budget1200wall seconds,1CPU thread,RSS2GiB,0GPU is still UNMEASURED; storage proposal1.5GiB/archive700MiB is UNAPPROVED. Category caps and total cap are enforced prospectively, not measured feasibility claims. If insufficient, stop and return; never truncate cases, thin evidence, alter metric or retry.

Three fixed figures+sidecars: all-group/H primary heatmap; seven-arm loss curves across ALL group/H cells; complete reference/seven-prediction/signed-error panels for both channels at the worst primary group/H and its worst A-loss origin (lexical/lowest-index ties). All groups/H/C30 failures additionally remain in complete tables with per-group/H worst-case IDs; the decoder supplies complete fields for any such case. One selected failure figure is descriptive, not representative evidence.

Only pending resource decision for HQ: accept/reject the quantified full-evidence storage revision and unmeasured1200s/2GiB proposal before a later launch package can be admitted. Actual scientific execution/data access still require a separate exact decision and code/runtime readiness, not implied by that resource decision. This candidate's config enabled=false, approved_budget=null and run_root=null; even a supplied receipt cannot enable it. Enabling would require a new reviewed config/lock identity. No receipt or scientific RunID has been invented.

Current reviewable command (EXPECTED TO REFUSE before scientific I/O):

```sh
/Users/wenxiaofang/miniconda3/bin/python3 supervise.py --config config.json --approval-receipt HQ_APPROVAL_NOT_CREATED.json
```

Preparation verification uses only test_package.py artificial fixtures: actual small-group fits/scoring/streams, target poisoning/leak rejection, all seven fields and native metric oracle, selectors/ties, counts, budget/size races, first-failure/no-overwrite, actual lifetime subprocesses and actual artificial Agg/font figures. No actual cohort/targets were loaded; no runtime feasibility can be extrapolated from these tiny fixtures. R003's ResourceWarning contract defect and the sealed arithmetic first stops remain recorded and untouched.
