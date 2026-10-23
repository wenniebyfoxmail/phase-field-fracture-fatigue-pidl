# D4 post-hoc scoring and figures

This is a prepared scoring entry point, not a result. It reads future F1 fields
only in the separate score process. The physics runner and its input schema are
unchanged. Actual saved-network replay, full mesh calculations and plots run on
an authorized GPU producer; Mac is limited to the artificial fixture below.

```text
python tools/s04_e036/score_mechanism_matrix.py --inventory score_inputs.json \
  --authority score_authority.json --out NEW_SCORE_OUTPUT --device cuda:0
```

The authority uses the existing execution envelope, with `mechanism_phase:"score"`,
`manifest_sha256` bound to **score_inputs.json**, a finite positive
`job_wall_seconds` equal to the inventory, and `cumulative_resource_limit:null`.
It binds the current implementation lock including the scorer and all replay
dependencies, and the established Stage A semantic reuse artifacts. The owner
uses an external per-job watchdog. Nothing retries automatically or starts an
optimizer/FEM solve. A fresh directory is required; `completion.json` appears
only after JSON and all figures are written. Partial output is not completion.

The inventory has exactly:

```text
schema: "s04_e036_mechanism_score_inputs_v1"
physics_manifest: {path, sha256}
target_manifest: {path, sha256}  # same four-state standard F1 manifest used by fit
job_wall_seconds: <finite positive owner setting>
cases:
  c1s2 | c1s4 | c83s2 | c83s4:
    matrix: {Lplus: record|null, L0: record|null, Cplus: record|null, C0: record|null}
    target_fit: record|null
    C0_continuation: record|null
```

Each record has exactly `status`, `attempt`, `implementation_lock`, `phase_inputs`,
`endpoint`, `snapshots`, `failure`:

- `status` is `complete`, `failed` or `running`. A not-yet-started/missing phase is
  null, never removed from the four-state inventory. Complete needs an endpoint;
  failed needs its actual hash-bound failure JSON. Finite snapshots of failed or
  running phases remain diagnostic only and do not enter factorial summaries.
- `attempt` and `implementation_lock` are `{path,sha256}` refs to the actual
  producer receipts. The producer lock hash must match its saved authority.
  Scientific replay dependencies must equal the scorer's current source bytes;
  the producer does not need to have contained this newly added scorer.
- `phase_inputs` is null for matrix, the target manifest ref for target-fit, or
  the actual four-state C0 source manifest ref for continuation. Continuation
  must name the exact C0 prefix scored here, not another run's endpoint.
- Each snapshot is `{completion:{path,sha256},bundle:{path,sha256},
  fields:{path,sha256},network:{path,sha256}}`. `endpoint` is one identical entry
  in `snapshots`, or null for an unfinished phase. `snapshots` enumerates **all**
  published completion files under that attempt's case/arm directory, including
  plateau/f-fixed events, initial states and intermediate/final checkpoints.
  Duplicate work coordinates are retained. This prevents selected learning curves.
- `failure` is null or a `{path,sha256}` ref inside the actual attempt directory.

All file paths in this inventory resolve relative to its directory. Native
producer admissions/phase input files keep their existing reference semantics.
No relocation may rewrite a hashed file; preserve referenced files or prepare
the binding inventory with accessible absolute paths. Within a snapshot the four
artifacts must remain together. Producer output paths retain `case/arm/...` below
their attempt file, so all snapshots can be checked for completeness.

For each endpoint the scorer independently loads network.pt, compares it exactly
with bundle.pt, checks fields.npz and receipt hashes, rebuilds the actual mapped
network, and reproduces saved fields/history/f exactly. The original native64
old d/A/r, mesh/common problem, canonical theta0, physics manifest, case and
phase must agree. The fresh physical acceptance and C must reproduce. Matrix
contrasts additionally require first_2000, float32 NN/float64 physics, 2000 RPROP,
zero LBFGS and zero history commits. The target uses the standard admitted F1
u tolerance 1e-6/joint 4e-4 and the exact same native predecessor. Fit must bind
that same target snapshot; it is explicitly marked target-used.

`scores.json` and per-state JSON contain Q/J/G and channel/max errors using the
same native nodal mass/Q4 fit metric, native GP raw/active/A/f/gradient errors,
fixed-f and fresh-f energy/force gaps, physical acceptance/C, dtype, work, source
hashes, and available parameter-gradient/clamp diagnostics from the endpoint.
Native GP errors use detJ weights; raw/active/A use scale alphaT=.5 and f uses 1.
Reaction is signed assembled dE/du on top/bottom at detached f, with the existing
fixed characteristic force scale. It is never estimated as 2E/U.

For any lower-is-better metric y, state-level descriptive contrasts are:

```text
clamp main effect   = ((Cplus-Lplus) + (C0-L0))/2
remove-L2 effect   = ((L0-Lplus) + (C0-Cplus))/2
interaction        = (C0-Cplus) - (L0-Lplus)
```

These use only completed equal-work prefixes. Finite physically rejected states
can describe optimization error but are labelled as unaccepted diagnostics.
Clamp changes the composite function family. A four-state mean is emitted only
if all four prescribed states have all four completed matrix arms. No selected
subset becomes an overall result. Missing F1 targets remain explicitly unscored.
C0 continuation and witness are reported separately, with their actual work and
precision. The achieved original-map fit error is an observed approximation
upper bound in that family at the seen target; its physical feasibility is
separate. Fit program stop is not proof of capacity sufficiency; failed fitting
is not proof of capacity insufficiency. Tightening is not inferred as an error
floor, and this score does not promote fixed-state results to full-cycle recovery.

Four PNG/PDF figures and same-stem Markdown sidecars are emitted:

- `mechanism_d`: four state rows; F1, Lplus-2000, C0-2000, and both signed errors.
  Full-domain shared color limits include out-of-bounds values. Triangles only
  interpolate the Q4 nodal field visually; they do not alter physical metrics.
- `mechanism_active`: same panels; all native Q4 GP values at their actual GP
  locations, without element averaging. Physical and signed color limits are
  separately shared across all states/methods.
- `mechanism_C_work`, `mechanism_J_work`: separate columns for first-2000 RPROP,
  C0 continuation RPROP and float64 LBFGS closure evaluations. They do not equate
  a closure to an update or a solver/precision change to an isolated dtype effect.

## Fixed preparation benchmark

```text
/Users/wenxiaofang/miniconda3/bin/python3 -m pytest tests/test_e036_mechanism_scoring.py -q
```

One representative complete fixture supplies all four states/arms, witness and
continuation on a single artificial Q4. It uses real PT/NPZ/JSON serialization,
hash binding, exact saved-field readback, Q4/force metrics, contrasts, and figure
export. A fake four-value field realization replaces the project NN; producer
authorization and actual F1 admissions are mocked. There is no network forward,
optimizer update or FEM solve. Expected: known constant-d J, zero raw-energy gap
under unchanged displacement, nonzero active/reaction gaps, correct effect sign,
missing-state/arm aggregation suppression, and all PNG/PDF/sidecars. Existing
runner tests are reused, not rerun; no added regression/smoke/review ladder.

## Actual case partitions (2026-10-23)

Use `--case c1s2` (or another declared case) with an authority carrying the same
`requested_case`. This loads that case's actual production manifest, even when
unselected predecessors are explicitly null. All four output slots remain
present; unselected cases are marked deferred and cannot enter an overall
four-state effect. The target manifest must still be the exact one bound by
that case's fit attempt. Different production or target manifests are never
rewritten into a fictitious common attempt. A postprocessing source snapshot
may replace only this scorer; retain the original 68291a0a production bytes of
every dependency, including `score_paired_windows.py`, for its existing checks.

This change only routes the existing scoring body. Direct AST comparison with
68291a0a confirms all ten scoring, replay, reduction and plotting helpers are
unchanged; no scientific benchmark was rerun for this control-only change.
