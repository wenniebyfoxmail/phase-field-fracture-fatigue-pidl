# S09-E016 factorised damage-increment readiness audit

Status: `DRAFT_ONLY_NOT_REVIEWED_NOT_AUTHORISED`

Primary storyline: S09 Neural Operator fracture-development representation.

This document is the current active D-step card. It defines a read-only audit
against already retrieved exposed-development arrays. It does not authorise a
run, training, new data access, FEM work, a new holdout, or producer use. The
project planning-review gate remains outstanding before this experiment can
enter `ready`.

## One mechanism question

Can the existing FEM target and A25/B25 damage increments be represented
stably as a nonnegative scalar amplitude times a normalised spatial shape,
with an explicit zero-increment state, so that a later short pilot can optimise
amplitude ordering and crack-tip localisation as separate objectives rather
than through the current direct `d_peak` head?

If the audit is computable and numerically stable, the next claim is only that
a factorised-head pilot is well posed on the exposed 16-cycle development set.
If it is not, the next work returns to data/state semantics or output
parameterisation. Neither outcome changes the E015 verdict.

## Frozen information set

Primary field source, already retrieved and verified:

```text
local_archive/experiments/S09-E015/runs/
  S09-E015-R001-output-trust-region-assay/run/all_state_fields.npz
```

Use only these existing arrays:

- `cycles`, `xy`, `nodal_weight`;
- `d_pre`, `target_peak`;
- `B25_step0__predicted_peak`, the retained B25 state from which E014-E015
  started.

Existing A25 evidence is available without a new run at:

```text
docs/research/S09/S09-E010/results/per_cycle_metrics.csv
docs/research/S09/S09-E010/results/field_visualisation/
  field_reconstruction_receipt.json
  S09-E010-R001-all-selected-cycles-fields.gif
  S09-E010-R001-cycle69-three-arm-increments.png
  S09-E010-R001-cycle73-final-fields.png
```

The table contains all 16 update-500 A25 amplitude, FEM amplitude, increment
error, false growth, spatial correlation and `L_judge` values. The figures are
claim-bearing display rasters. The raw A25 nodal arrays were not persisted.
Therefore the current no-compute D can define and cross-check A25 scalar
comparisons, but it cannot honestly claim an exact A25 shape factorisation.
If the later reviewed E016 implementation requires nodewise A25 shape metrics,
the smallest missing asset is a read-only A25 field export from the already
frozen checkpoint and packet; that export is a future authorised diagnostic,
not part of this planning turn.

The E015 CG/CL path arrays may be shown as secondary context, but they do not
vote on factorisation readiness. No packet reread, checkpoint forward, target
refresh, new mask, gradient, optimiser, or training step is part of this D.

## Concrete factorisation

For field `d_peak` and its matching `d_pre`, first define remaining capacity
and positive increment at node `i`:

```text
c_i = clip(1 - d_pre_i, 0, 1)
r_i = clip(d_peak_i - d_pre_i, 0, c_i)
```

On nodes with `c_i > epsilon_c`, transform the bounded increment to a
nonnegative hazard field:

```text
q_i = clip(r_i / c_i, 0, 1 - epsilon_q)
h_i = -log(1 - q_i)
```

Set `h_i=0` where capacity is numerically zero. Normalise the supplied nodal
weights once as `wbar_i = w_i / sum_j w_j`, then define

```text
A = sum_i wbar_i h_i
S_i = h_i / A
```

for a nonzero event. Thus `A >= 0`, `S_i >= 0`, and
`sum_i wbar_i S_i = 1`. Exact reconstruction is

```text
h_i = A S_i
Delta d_i = c_i * (1 - exp(-A S_i)).
```

This is the proposed head semantics for later work, not an implemented model:
`A_hat = softplus(a_theta)` and a weighted-softmax `S_hat` would provide
positivity and normalisation by construction; the exponential capacity map
would provide `d_pre <= d_peak <= 1` by construction.

### Zero-increment rule

If `A` is zero at numerical precision, record

```text
amplitude = 0
shape_valid = false
shape = all-zero sentinel
```

Do not substitute a uniform shape. Such a cycle remains in amplitude and
zero/nonzero accounting but is excluded from shape loss, shape correlation,
centroid and support-capture summaries. Growth-versus-stagnant pairs involving
an undefined target shape remain usable for amplitude ranking only.

`epsilon_c`, `epsilon_q`, and the zero-amplitude numerical tolerance must be
fixed by the implementation review from float64 reconstruction stability; they
are not scientific support thresholds.

## Read-only comparison table

For FEM target and every available baseline, report one row per cycle with:

- `A`, `log1p(A / A_scale)`, `shape_valid`, positive-node count, weighted mean
  `Delta d`, and maximum `Delta d`;
- amplitude ratio and log-amplitude error for A25 and B25 versus FEM;
- the existing 25-pair amplitude outcomes and `2W+T`;
- for B25, and for A25 only after an authorised node-field export, weighted
  half-L1 shape distance
  `0.5 * sum(wbar * abs(S_pred - S_FEM))`, weighted cosine similarity,
  target-support mass captured by the prediction, background spill, and
  weighted centroid offset in the existing `xy` coordinates;
- the inherited target-support-minus-background observable and its 25-pair
  outcomes as a secondary bridge to E013-E015.

The target support remains the already used development label
`target_peak - d_pre > 1e-15`. It is an audit/learning label and is never an
operator input or output correction. Shape metrics must also be shown without
this binary mask through half-L1, cosine and centroid, so the support threshold
does not control the conclusion.

## Existing reusable implementation

- `source/s09_e013_local_ranking_objective.py::weighted_amplitude` and
  `local_support_score` provide the frozen amplitude and support/background
  observables.
- `source/s09_e014_producer.py::_scores_from_fields` provides the fixed 25-pair
  global/local outcome accounting.
- `source/s09_e015_producer.py::_cycle_increment_rows` provides finite,
  positive-node, weighted-mean and maximum-increment rows.
- `scripts/plot_s09_e010_field_snapshots.py` provides the existing field
  plotting conventions and its `reconstruct_fields` function is the reusable
  read-only A25/B25/B0 export path. Calling it would perform model forwards and
  is deliberately outside this planning-only D.
- `local_archive/experiments/S09-E015/make_visualizations.py` contains the
  existing unstructured-mesh rasterisation used for the human-check figures;
  it is visualisation reuse only and is not yet a reviewed analysis entrypoint.

The smallest new implementation should be one pure analysis module plus one
CLI that reads the existing NPZ and writes the minimum assets below. No model
runtime is needed.

## Cheapest diagnostic and minimum delivery

E016 is itself the cheaper diagnostic before any factorised-head training.
Its minimum claim-bearing delivery is:

1. `factorisation_cycle_table.csv` with all 16 cycles, FEM/B25 factorisation
   rows, and existing A25 scalar rows; an A25 shape block is conditional on a
   separately authorised node-field export;
2. `factorisation_decision.md` with numerical validity and route selection;
3. one figure with FEM/A25/B25 amplitude by cycle and FEM/B25 normalised
   shapes for the existing selected cycles `1, 69, 73`; add exact A25 shapes
   only if the separate node-field export is later authorised;
4. `factorisation_arrays.npz` containing reconstructed `A`, `S`, and residuals;
5. one `README_analysis.md` covering the figure set and claim boundary.

No per-file hash forest is required. A path/file-count/size receipt and the Git
commit of the analysis code are sufficient unless a later result is promoted.

## Route after the audit

This D uses validity and routing conditions rather than a high scientific
prediction threshold.

### Prepare a short pilot

Prepare, but do not launch, an E017 pilot card when all of the following are
true:

- all 16 FEM/B25 field increments, capacities and weights are finite, the cycle
  identities are complete, and the existing A25 scalar rows align to them;
- every nonzero field has finite `A` and a normalised `S`, while every zero
  field follows the explicit undefined-shape rule;
- float64 factorisation round trips reproduce the clipped source increments
  to the reviewed numerical tolerance;
- the amplitude, shape, support-capture and centroid objectives are computable
  on enough nonzero cycles to form the existing growth/stagnant comparisons.

The pilot is still justified when A25/B25 is poor; poor amplitude or location
is the baseline the pilot is meant to repair. The audit should route the pilot
as follows:

- materially varying FEM shapes: separate amplitude and spatial heads;
- nearly invariant FEM shapes with varying amplitude: shared/template shape
  plus amplitude head as the smaller pilot;
- a mixture of zero and nonzero cycles: retain the explicit event/amplitude
  branch and condition shape loss only on valid shapes.

### Repair data or representation first

Do not prepare training if cycle/state identities are inconsistent, nodal
weights are invalid, target increments materially violate irreversibility or
capacity, factorisation cannot round trip, most required comparison shapes are
undefined, or a few near-zero-capacity nodes dominate the normalised shape.
These outcomes request a state-semantics, weighting, or transform repair; they
are not evidence that neural operators cannot learn crack development.

## Later E017 objective vector, for planning only

A later short exposed-development pilot should keep separate records for:

1. amplitude reconstruction and 25-pair amplitude ranking;
2. normalised-shape distance and target-support/background localisation;
3. full `Delta d` reconstruction and bounded/irreversible output checks;
4. the existing `beta=0.25` native-Q4 AMOR free-displacement equilibrium
   residual;
5. the other already exposed state fields needed by the operator mapping.

Gradient balancing or a constrained multi-objective method must not be chosen
until the E016 scale table is available. The equilibrium term remains limited
PINO physics; damage stationarity, history complementarity and the full
incremental variational inequality remain outside the claim.

## Five-question gate record

1. Mechanism: is explicit amplitude/shape factorisation numerically well posed
   for the existing FEM and A25/B25 increments?
2. Claim change: only readiness or non-readiness of a later short pilot.
3. Cheaper diagnostic: this read-only NPZ audit; no training is warranted first.
4. Minimum asset: one cycle table, one decision note, one selected-cycle figure
   set, factorisation arrays, and its reading guide.
5. Checklist handoff: append the completed verdict to the existing S09
   Obsidian owner and replace the single S09 Roadmap line; do not create another
   storyline or duplicate roadmap endpoint.

